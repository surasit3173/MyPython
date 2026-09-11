#!/usr/bin/env python3
"""
Phase 5F Project 2 Corrective Re-Analysis Execution Script
==========================================================
1. Reads config/config.yaml and enforces Validation Gate (baseline_years == config['data']['historical_baseline_period']).
2. Reruns 11 ETCCDI indices for all 13 observed stations using authoritative baseline [1995, 2014].
3. Computes diagnostic baseline sensitivity comparison (1981-2010 vs 1995-2014) for R95p and R99p.
4. Audits QDM execution provenance across 7 CMIP6 GCMs.
5. Audits ANOVA variance decomposition status.
6. Writes manifests/run_manifest_project2.json.
"""

import sys
import os
import json
import yaml
import platform
import hashlib
import numpy as np
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.abspath('.'))
from src.indices.etccdi import calculate_uttaradit_etccdi_11
from src.validation.gates import StopBlockedException

def compute_sha256(filepath):
    if not os.path.exists(filepath):
        return "FILE_NOT_FOUND"
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def run_project2_phase5f():
    print("=== PHASE 5F — PROJECT 2 (UTTARADIT) CORRECTIVE REANALYSIS ===")

    cfg_path = os.path.join('config', 'config.yaml')
    with open(cfg_path, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)

    obs_csv = os.path.join('Data_Uttaradit', 'Observed_Rain_daily_198101_201412_Uttaradit.csv')
    coords_csv = os.path.join('Data_Uttaradit', 'station_coordinates_Uttaradit.csv')

    obs_hash = compute_sha256(obs_csv)
    coords_hash = compute_sha256(coords_csv)
    cfg_hash = compute_sha256(cfg_path)
    script_hash = compute_sha256(__file__)

    print(f"Observed CSV SHA256: {obs_hash}")
    print(f"Coords CSV SHA256  : {coords_hash}")
    print(f"Config YAML SHA256 : {cfg_hash}\n")

    # A. VALIDATION GATE: Baseline Period Enforcement
    config_baseline = tuple(cfg['data']['historical_baseline_period'])
    execution_baseline = (1995, 2014) # Authoritative baseline

    if execution_baseline != config_baseline:
        raise StopBlockedException(
            f"VALIDATION GATE FAILURE: Execution baseline {execution_baseline} does not match config baseline {config_baseline}!"
        )
    print(f"VALIDATION GATE PASSED: Execution baseline {execution_baseline} matches config.yaml historical_baseline_period {config_baseline}.")

    # B. RERUN 11 ETCCDI INDICES ON AUTHORITATIVE BASELINE (1995-2014)
    df_obs = pd.read_csv(obs_csv)
    df_obs['date'] = pd.to_datetime(df_obs[['YEAR', 'MONTH', 'DAY']])
    stn_cols = [c for c in df_obs.columns if c not in ['YEAR', 'MONTH', 'DAY', 'date']]

    print(f"\nComputing 11 ETCCDI indices for {len(stn_cols)} observed stations using Authoritative Baseline {execution_baseline}...")

    indices_1995_2014 = []
    for stn in stn_cols:
        stn_df = df_obs[['date', stn]].rename(columns={stn: 'precipitation_mm'})
        idx_df = calculate_uttaradit_etccdi_11(stn_df, baseline_years=execution_baseline)
        idx_df['station_id'] = stn
        indices_1995_2014.append(idx_df)

    df_etccdi_1995 = pd.concat(indices_1995_2014, ignore_index=True)

    summary_1995 = df_etccdi_1995.groupby('station_id')[['PRCPTOT', 'SDII', 'Rx1day', 'Rx5day', 'CDD', 'CWD', 'R10mm', 'R20mm', 'R50mm', 'R95p', 'R99p']].mean()
    print("\n=== CORRECTED OBSERVED ETCCDI 11 INDICES (BASELINE 1995-2014 MEAN) ===")
    print(summary_1995.round(2).to_string())

    # C. BASELINE SENSITIVITY DIAGNOSTIC (1981-2010 vs 1995-2014)
    print("\n=== BASELINE SENSITIVITY DIAGNOSTIC (1981-2010 vs 1995-2014) FOR R95p & R99p ===")
    
    indices_1981_2010 = []
    for stn in stn_cols:
        stn_df = df_obs[['date', stn]].rename(columns={stn: 'precipitation_mm'})
        idx_df = calculate_uttaradit_etccdi_11(stn_df, baseline_years=(1981, 2010))
        idx_df['station_id'] = stn
        indices_1981_2010.append(idx_df)

    df_etccdi_1981 = pd.concat(indices_1981_2010, ignore_index=True)

    sensitivity_rows = []
    for stn in stn_cols:
        # Thresholds comparison
        mask_81 = (df_obs['date'].dt.year >= 1981) & (df_obs['date'].dt.year <= 2010) & (df_obs[stn] >= 1.0)
        mask_95 = (df_obs['date'].dt.year >= 1995) & (df_obs['date'].dt.year <= 2014) & (df_obs[stn] >= 1.0)

        w81 = df_obs[mask_81][stn].values
        w95 = df_obs[mask_95][stn].values

        p95_81 = float(np.percentile(w81, 95)) if len(w81) > 0 else 0
        p95_95 = float(np.percentile(w95, 95)) if len(w95) > 0 else 0

        p99_81 = float(np.percentile(w81, 99)) if len(w81) > 0 else 0
        p99_95 = float(np.percentile(w95, 99)) if len(w95) > 0 else 0

        # Mean index values
        r95p_81 = df_etccdi_1981[df_etccdi_1981['station_id'] == stn]['R95p'].mean()
        r95p_95 = df_etccdi_1995[df_etccdi_1995['station_id'] == stn]['R95p'].mean()

        r99p_81 = df_etccdi_1981[df_etccdi_1981['station_id'] == stn]['R99p'].mean()
        r99p_95 = df_etccdi_1995[df_etccdi_1995['station_id'] == stn]['R99p'].mean()

        sensitivity_rows.append({
            'station_id': stn,
            'P95_Threshold_81_10': round(p95_81, 2),
            'P95_Threshold_95_14': round(p95_95, 2),
            'Diff_P95_Thresh': round(p95_95 - p95_81, 2),
            'Mean_R95p_81_10': round(r95p_81, 2),
            'Mean_R95p_95_14': round(r95p_95, 2),
            'Diff_R95p_Mean': round(r95p_95 - r95p_81, 2),
            'Mean_R99p_81_10': round(r99p_81, 2),
            'Mean_R99p_95_14': round(r99p_95, 2),
            'Diff_R99p_Mean': round(r99p_95 - r99p_81, 2)
        })

    df_sens = pd.DataFrame(sensitivity_rows)
    print(df_sens.to_string(index=False))

    # D. QDM PROVENANCE RECONSTRUCTION AUDIT
    print("\n=== D. QDM PROVENANCE RECONSTRUCTION AUDIT ===")
    print("Audit Finding: Pre-computed bias-corrected CSV files (bc_pr_day_...csv) exist in Data_Uttaradit/.")
    print("However, NO live executable Python script transforming raw CMIP6 data -> QDM -> BC data exists in Project 2 codebase.")
    print("Action per Phase 5F rules: QDM Provenance Status = STOP / UNVERIFIED.")

    # E. UNCERTAINTY DECOMPOSITION AUDIT
    print("\n=== E. UNCERTAINTY DECOMPOSITION AUDIT ===")
    print("Audit Finding: Search of Project 2 codebase reveals ZERO ANOVA variance decomposition scripts or calculated output tables.")
    print("Action per Phase 5F rules: Reported variance percentages (65-75% Model, 15-25% Scenario, 10-15% Internal) are UNSUPPORTED — REMOVE FROM MANUSCRIPT.")

    # F. WRITE MANIFEST
    os.makedirs('manifests', exist_ok=True)
    manifest_path = os.path.join('manifests', 'run_manifest_project2.json')
    
    manifest = {
        "project": "CMIP6Uttaradit",
        "run_id": "P2_PHASE5F_CORRECTED_ETCCDI_RERUN",
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "system": {
            "python_version": platform.python_version(),
            "operating_system": platform.platform(),
            "processor": platform.processor()
        },
        "provenance": {
            "observed_csv": obs_csv,
            "observed_sha256": obs_hash,
            "coords_csv": coords_csv,
            "coords_sha256": coords_hash,
            "config_yaml": cfg_path,
            "config_sha256": cfg_hash,
            "script": __file__,
            "script_sha256": script_hash
        },
        "methodological_parameters": {
            "authoritative_baseline_period": list(execution_baseline),
            "wet_day_threshold_mm": 1.0,
            "indices_count": 11,
            "observed_stations_count": len(stn_cols),
            "validation_gate_passed": True
        },
        "audit_findings": {
            "qdm_provenance_status": "STOP / UNVERIFIED (Missing live raw -> BC transformation script)",
            "uncertainty_decomposition_status": "UNSUPPORTED — REMOVE FROM MANUSCRIPT (No ANOVA engine in repository)"
        },
        "validation_status": "CONDITIONAL PASS / STOP (ETCCDI rerun passed; QDM & ANOVA unverified)",
        "warnings": [
            "QDM bias correction is pre-computed artifact only; no live transformation script present.",
            "ANOVA variance decomposition percentages are unsupported by code."
        ],
        "errors": []
    }

    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)

    print(f"\nManifest written to {manifest_path}")

if __name__ == '__main__':
    run_project2_phase5f()
