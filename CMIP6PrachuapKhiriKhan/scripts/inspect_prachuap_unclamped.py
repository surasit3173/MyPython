#!/usr/bin/env python3
"""
Prachuap Khiri Khan 12 Stations Unclamped MMK Audit
====================================================
Evaluates all 12 stations under unclamped Hamed & Rao (1998) MMK.
Checks if any real station produces n/n_s* <= 0 or domain error.
"""

import sys
import os
import math
import numpy as np
import pandas as pd
from scipy.stats import norm

def sens_slope(x):
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    slopes = []
    for k in range(n - 1):
        for j in range(k + 1, n):
            slopes.append((x[j] - x[k]) / float(j - k))
    return float(np.median(slopes))

def mann_kendall_test(x):
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    S = 0.0
    for k in range(n - 1):
        S += np.sum(np.sign(x[k + 1:] - x[k]))
    unique_x, counts = np.unique(x, return_counts=True)
    g = len(unique_x)
    var_S = (n * (n - 1) * (2 * n + 5)) / 18.0
    if g < n:
        tie_sum = np.sum(counts * (counts - 1) * (2 * counts + 5))
        var_S -= tie_sum / 18.0
    if S > 0:
        Z = (S - 1.0) / math.sqrt(var_S) if var_S > 0 else 0.0
    elif S < 0:
        Z = (S + 1.0) / math.sqrt(var_S) if var_S > 0 else 0.0
    else:
        Z = 0.0
    p_value = 2.0 * (1.0 - norm.cdf(abs(Z)))
    return {'S': float(S), 'var_S': float(var_S), 'Z': float(Z), 'p_value': float(p_value), 'n': n}

def hamed_rao_unclamped(x, alpha=0.05, use_detrending=True):
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    mk_base = mann_kendall_test(x)

    if n < 4:
        return {**mk_base, 'n_ns_star': 1.0, 'var_S_mod': mk_base['var_S'], 'sig_lags': []}

    slope = sens_slope(x)

    if use_detrending:
        t = np.arange(n)
        series_for_ranks = x - slope * t
    else:
        series_for_ranks = x

    ranks = pd.Series(series_for_ranks).rank().values
    mean_rank = (n + 1) / 2.0
    denom_ss = np.sum((ranks - mean_rank) ** 2)

    z_crit = norm.ppf(1.0 - alpha / 2.0)
    rho_sum = 0.0
    sig_lags = []

    for i in range(1, n - 1):
        num = np.sum((ranks[:-i] - mean_rank) * (ranks[i:] - mean_rank))
        rho_i = num / denom_ss
        z_rho = rho_i * math.sqrt(n - i)
        is_sig = abs(z_rho) > z_crit

        weight = (n - i) * (n - i - 1) * (n - i - 2)
        contrib = weight * rho_i if is_sig else 0.0

        if is_sig:
            rho_sum += contrib
            sig_lags.append(i)

    norm_factor = 2.0 / (n * (n - 1) * (n - 2))
    raw_n_ns_star = 1.0 + norm_factor * rho_sum
    var_S_modified = mk_base['var_S'] * raw_n_ns_star

    S = mk_base['S']
    
    if var_S_modified > 0:
        if S > 0:
            Z_mod = (S - 1.0) / math.sqrt(var_S_modified)
        elif S < 0:
            Z_mod = (S + 1.0) / math.sqrt(var_S_modified)
        else:
            Z_mod = 0.0
        p_mod = 2.0 * (1.0 - norm.cdf(abs(Z_mod)))
    else:
        Z_mod = np.nan
        p_mod = np.nan

    return {
        'S': S,
        'var_S_base': mk_base['var_S'],
        'Z_mk': mk_base['Z'],
        'p_mk': mk_base['p_value'],
        'slope': slope,
        'sig_lags': sig_lags,
        'n_ns_star': raw_n_ns_star,
        'var_S_mod': var_S_modified,
        'Z_mmk': Z_mod,
        'p_mmk': p_mod
    }

def run_prachuap_audit():
    obs_csv = 'Observed_Rain_daily_198101_201412_PrachuapKhiriKhan.csv'
    df_obs = pd.read_csv(obs_csv)
    df_obs['date'] = pd.to_datetime(df_obs[['YEAR', 'MONTH', 'DAY']])
    df_obs['year'] = df_obs['date'].dt.year
    stn_cols = [c for c in df_obs.columns if c not in ['YEAR', 'MONTH', 'DAY', 'date', 'year']]

    records = []
    for stn in stn_cols:
        stn_id = int(float(stn))
        annual = df_obs.groupby('year')[stn].sum().values
        res_unclamped = hamed_rao_unclamped(annual, use_detrending=True)

        records.append({
            'station_id': stn_id,
            'N': len(annual),
            'Sen_Slope': round(res_unclamped['slope'], 3),
            'MK_Z': round(res_unclamped['Z_mk'], 3),
            'Sig_Lags': str(res_unclamped['sig_lags']),
            'Unclamped_n/n_s*': round(res_unclamped['n_ns_star'], 4),
            'Var*(S)': round(res_unclamped['var_S_mod'], 2) if not np.isnan(res_unclamped['var_S_mod']) else "DOMAIN_ERR",
            'Unclamped_Z_MMK': round(res_unclamped['Z_mmk'], 3) if not np.isnan(res_unclamped['Z_mmk']) else "DOMAIN_ERR",
            'Unclamped_p_MMK': round(res_unclamped['p_mmk'], 4) if not np.isnan(res_unclamped['p_mmk']) else "DOMAIN_ERR"
        })

    df_res = pd.DataFrame(records)
    print("=== PRACHUAP KHIRI KHAN 12 STATIONS UNCLAMPED MMK AUDIT ===")
    print(df_res.to_string(index=False))

if __name__ == '__main__':
    run_prachuap_audit()
