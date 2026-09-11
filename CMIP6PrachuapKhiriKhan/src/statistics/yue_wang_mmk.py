#!/usr/bin/env python3
"""
Yue & Wang (2004) AR(1) Modified Mann-Kendall Module
====================================================
Primary publication-grade trend method for hydro-climate series.
Corrects for lag-1 autocorrelation persistence using the analytical Yue & Wang (2004) formula.
"""

import math
import numpy as np
from scipy.stats import norm
from .sens_slope import sens_slope
from .mann_kendall import standard_mann_kendall

def yue_wang_mmk(x, alpha=0.05, r1_alpha=0.05):
    """
    Yue & Wang (2004) AR(1) Modified Mann-Kendall Test.
    
    Trace:
    1. Base tie-corrected MK S and Var(S).
    2. Sen's slope beta for original series x.
    3. Detrend series: x_detrended[i] = x[i] - beta * i.
    4. Compute sample lag-1 autocorrelation r1 of detrended series.
    5. Check domain validity: |r1| < 1.0.
    6. Test significance of r1: |r1| > z_{1-alpha/2} / sqrt(n).
    7. If r1 is significant, compute Yue & Wang (2004) variance correction factor:
       n/n_s* = 1 + 2 * [r1^(n+1) - n*r1^2 + (n-1)*r1] / [n * (r1 - 1)^2].
       Else n/n_s* = 1.0.
    8. Var*(S) = Var(S) * (n/n_s*).
    9. Validate Var*(S) > 0.
    10. Calculate Z_mmk and two-sided p-value.
    """
    x = np.asarray(x, dtype=np.float64)
    x = x[~np.isnan(x)]
    n = len(x)
    mk_base = standard_mann_kendall(x)

    if n < 4:
        return {
            'S': mk_base['S'],
            'var_S_base': mk_base['var_S'],
            'r1': 0.0,
            'r1_significant': False,
            'n_ns_star': 1.0,
            'var_S_mod': mk_base['var_S'],
            'Z_mmk': mk_base['Z'],
            'p_value_mmk': mk_base['p_value'],
            'slope': 0.0,
            'n': n,
            'status': 'NOT_COMPUTED'
        }

    # 1. Sen's slope
    slope = sens_slope(x)
    t = np.arange(n)
    detrended = x - slope * t

    # 2. Lag-1 autocorrelation of detrended series
    denom = np.sum((detrended - np.mean(detrended)) ** 2)
    if denom == 0:
        return {
            'S': mk_base['S'],
            'var_S_base': mk_base['var_S'],
            'r1': 0.0,
            'r1_significant': False,
            'n_ns_star': 1.0,
            'var_S_mod': mk_base['var_S'],
            'Z_mmk': mk_base['Z'],
            'p_value_mmk': mk_base['p_value'],
            'slope': slope,
            'n': n,
            'status': 'VALID'
        }

    r1 = np.sum((detrended[:-1] - np.mean(detrended)) * (detrended[1:] - np.mean(detrended))) / denom

    # 3. Validate |r1| < 1.0
    if abs(r1) >= 1.0:
        return {
            'S': mk_base['S'],
            'var_S_base': mk_base['var_S'],
            'r1': float(r1),
            'r1_significant': False,
            'n_ns_star': np.nan,
            'var_S_mod': np.nan,
            'Z_mmk': np.nan,
            'p_value_mmk': np.nan,
            'slope': slope,
            'n': n,
            'status': 'DOMAIN_ERROR'
        }

    # 4. Significance test for r1
    z_crit = norm.ppf(1.0 - r1_alpha / 2.0)
    r1_threshold = z_crit / math.sqrt(n)
    is_r1_sig = abs(r1) > r1_threshold

    # 5. Yue & Wang (2004) Variance Correction Factor Formula
    if is_r1_sig:
        num = (r1 ** (n + 1)) - (n * (r1 ** 2)) + ((n - 1) * r1)
        den = n * ((r1 - 1.0) ** 2)
        n_ns_star = 1.0 + 2.0 * (num / den)
    else:
        n_ns_star = 1.0

    var_S_modified = mk_base['var_S'] * n_ns_star

    # 6. Validate Var*(S) > 0
    if var_S_modified <= 0:
        return {
            'S': mk_base['S'],
            'var_S_base': mk_base['var_S'],
            'r1': float(r1),
            'r1_significant': is_r1_sig,
            'n_ns_star': float(n_ns_star),
            'var_S_mod': float(var_S_modified),
            'Z_mmk': np.nan,
            'p_value_mmk': np.nan,
            'slope': slope,
            'n': n,
            'status': 'DOMAIN_ERROR'
        }

    # 7. Z and p-value calculation
    S = mk_base['S']
    if S > 0:
        Z_mod = (S - 1.0) / math.sqrt(var_S_modified)
    elif S < 0:
        Z_mod = (S + 1.0) / math.sqrt(var_S_modified)
    else:
        Z_mod = 0.0

    p_mod = 2.0 * (1.0 - norm.cdf(abs(Z_mod)))

    return {
        'S': float(S),
        'var_S_base': float(mk_base['var_S']),
        'r1': float(r1),
        'r1_significant': bool(is_r1_sig),
        'n_ns_star': float(n_ns_star),
        'var_S_mod': float(var_S_modified),
        'Z_mmk': float(Z_mod),
        'p_value_mmk': float(p_mod),
        'slope': float(slope),
        'n': n,
        'status': 'VALID'
    }
