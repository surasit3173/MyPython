#!/usr/bin/env python3
"""
Standard Mann-Kendall Trend Test Module
=======================================
Calculates S statistic, tie-corrected Var(S), standardized Z, and two-sided p-value.
"""

import math
import numpy as np
from scipy.stats import norm

def standard_mann_kendall(x):
    """
    Standard Mann-Kendall test with tie correction.
    """
    x = np.asarray(x, dtype=np.float64)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 3:
        return {'S': 0.0, 'var_S': 1.0, 'Z': 0.0, 'p_value': 1.0, 'n': n, 'status': 'NOT_COMPUTED'}

    # 1. S statistic
    S = 0.0
    for k in range(n - 1):
        S += np.sum(np.sign(x[k + 1:] - x[k]))

    # 2. Tie correction
    unique_x, counts = np.unique(x, return_counts=True)
    g = len(unique_x)
    var_S = (n * (n - 1) * (2 * n + 5)) / 18.0

    if g < n:
        tie_sum = np.sum(counts * (counts - 1) * (2 * counts + 5))
        var_S -= tie_sum / 18.0

    if var_S <= 0:
        return {'S': float(S), 'var_S': 0.0, 'Z': 0.0, 'p_value': 1.0, 'n': n, 'status': 'DOMAIN_ERROR'}

    # 3. Z statistic with continuity correction
    if S > 0:
        Z = (S - 1.0) / math.sqrt(var_S)
    elif S < 0:
        Z = (S + 1.0) / math.sqrt(var_S)
    else:
        Z = 0.0

    p_val = 2.0 * (1.0 - norm.cdf(abs(Z)))

    return {
        'S': float(S),
        'var_S': float(var_S),
        'Z': float(Z),
        'p_value': float(p_val),
        'n': n,
        'status': 'VALID'
    }
