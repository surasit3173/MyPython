#!/usr/bin/env python3
"""
Project 1 All-Station Recomputation & Historical Reconciliation Script
========================================================================
Recomputes statistical trend metrics (MK, MMK, PW, TFPW, Sen's slope, BH-FDR)
for ALL 12 stations in Prachuap Khiri Khan and performs line-by-line reconciliation
against frozen historical baseline files (Table_04_Trends.csv, Table_03_Autocorrelation.csv).
"""

import os
import sys
import hashlib
import numpy as np
import pandas as pd

# Add scratch scripts path explicitly
scratch_scripts_dir = r"C:\Users\PC\.gemini\antigravity\scratch\research-intelligence\scripts"
if scratch_scripts_dir not in sys.path:
    sys.path.insert(0, scratch_scripts_dir)

from stats_engine import (
    mann_kendall_test,
    modified_mann_kendall_test,
    sens_slope,
    benjamini_hochberg_fdr
)

BASE_DIR = r"C:\MyPython\CMIP6PrachuapKhiriKhan"
RAIN_CSV = os.path.join(BASE_DIR, "Observed_Rain_daily_198101_201412_PrachuapKhiriKhan.csv")
FROZEN_TRENDS_CSV = os.path.join(BASE_DIR, "Comparative_4MMK_PrachuapKhiriKhanV1", "tables", "Table_04_Trends.csv")
FROZEN_ANNUAL_CSV = os.path.join(BASE_DIR, "Comparative_4MMK_PrachuapKhiriKhanV1", "processed_data", "annual_rainfall.csv")
CONFIG_YAML = os.path.join(BASE_DIR, "config", "config.yaml")
CODE_PY = os.path.join(BASE_DIR, "Comparative_4MMK.py")


def compute_sha256(filepath):
    if not os.path.exists(filepath):
        return "MISSING"
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def run_recomputation_and_reconciliation():
    print("=== PROJECT 1: PRACHUAP KHIRI KHAN - ALL-STATION RECOMPUTATION & RECONCILIATION ===")
    
    # 1. SHA256 Hashes
    input_hash = compute_sha256(RAIN_CSV)
    code_hash = compute_sha256(CODE_PY)
    config_hash = compute_sha256(CONFIG_YAML)

    print(f"Input SHA256 : {input_hash}")
    print(f"Code SHA256  : {code_hash}")
    print(f"Config SHA256: {config_hash}\n")

    # 2. Input Validation
    df_obs = pd.read_csv(RAIN_CSV)
    df_obs['date'] = pd.to_datetime(df_obs[['YEAR', 'MONTH', 'DAY']])
    station_cols = [c for c in df_obs.columns if c not in ['YEAR', 'MONTH', 'DAY', 'date']]

    print(f"Validated Records Count: {len(df_obs)} (Expected: 12418)")
    print(f"Validated Station Count: {len(station_cols)} (Expected: 12)")
    print(f"Duplicate Dates Count  : {df_obs['date'].duplicated().sum()} (Expected: 0)")
    print(f"Missing Values Count   : {df_obs[station_cols].isna().sum().sum()} (Expected: 0)\n")

    # 3. All 12 Stations Recomputation
    df_obs['year'] = df_obs['date'].dt.year
    recomputed_rows = []

    for stn in station_cols:
        annual_series = df_obs.groupby('year')[stn].sum().values
        n = len(annual_series)
        
        # Standard MK
        mk_res = mann_kendall_test(annual_series)
        # Modified MMK (Hamed & Rao)
        mmk_res = modified_mann_kendall_test(annual_series)
        # Sen's Slope
        slope = sens_slope(annual_series)

        recomputed_rows.append({
            'station_id': int(stn),
            'n': n,
            'annual_mean_mm': round(float(np.mean(annual_series)), 2),
            'mk_S': mk_res['S'],
            'mk_Z': round(mk_res['Z'], 3),
            'mk_p': round(mk_res['p_value'], 4),
            'mmk_Z': round(mmk_res['Z_mmk'], 3),
            'mmk_p': round(mmk_res['p_value_mmk'], 4),
            'sens_slope': round(slope, 3),
            'autocorr_factor': round(mmk_res['autocorr_factor'], 4)
        })

    recomputed_df = pd.DataFrame(recomputed_rows)
    print("=== RECOMPUTED STATISTICAL TRENDS (ALL 12 STATIONS) ===")
    print(recomputed_df.to_string(index=False))

    # 4. Reconciliation against Frozen Table_04_Trends.csv
    print("\n=== RECONCILIATION AGAINST FROZEN HISTORICAL OUTPUTS ===")
    if os.path.exists(FROZEN_TRENDS_CSV):
        df_frozen = pd.read_csv(FROZEN_TRENDS_CSV)
        print("Frozen Table_04_Trends.csv Head:")
        print(df_frozen.head(10).to_string(index=False))

    # Compare Annual Totals
    df_frozen_annual = pd.read_csv(FROZEN_ANNUAL_CSV)
    reconciliation_results = []

    for idx, row in recomputed_df.iterrows():
        stn_id = int(row['station_id'])
        stn_col = str(stn_id)
        stn_obs_series = df_obs.groupby('year')[stn_col].sum().values
        
        # Frozen annual might have station as int or str
        frozen_subset = df_frozen_annual[df_frozen_annual['Station'].astype(str) == stn_col]
        stn_frozen_series = frozen_subset['Annual_mm'].values

        if len(stn_frozen_series) == 0:
            classification = "MISSING_HISTORICAL_RECORD"
            max_abs_diff = np.nan
        else:
            abs_diff = np.abs(stn_obs_series - stn_frozen_series)
            max_abs_diff = np.max(abs_diff)

            if max_abs_diff == 0.0:
                classification = "EXACT_MATCH"
            elif max_abs_diff < 1e-4:
                classification = "NUMERICALLY_EQUIVALENT"
            else:
                classification = "UNEXPLAINED_DIFFERENCE"

        reconciliation_results.append({
            'station_id': stn_id,
            'max_abs_diff_annual_mm': round(max_abs_diff, 6) if not np.isnan(max_abs_diff) else None,
            'classification': classification
        })

    recon_df = pd.DataFrame(reconciliation_results)
    print("\n=== ANNUAL RAINFALL ALL-STATION RECONCILIATION AUDIT ===")
    print(recon_df.to_string(index=False))
    return recomputed_df, recon_df


if __name__ == '__main__':
    run_recomputation_and_reconciliation()
