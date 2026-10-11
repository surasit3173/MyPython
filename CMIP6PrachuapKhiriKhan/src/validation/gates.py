#!/usr/bin/env python3
"""
Validation Gates & Firewall Module (Project 1: Prachuap Khiri Khan)
====================================================================
Implements Gate 1 (Input), Gate 2 (Config), Gate 3 (Stat), Gate 4 (Output/Provenance).
Triggers STOP_BLOCKED on any critical validation failure. Zero synthetic fallbacks allowed.
"""

import os
import sys
import hashlib
import pandas as pd
import numpy as np


class StopBlockedException(Exception):
    """Raised when a validation gate fails and execution must STOP immediately."""
    pass


def compute_sha256(filepath):
    """Computes SHA256 hash of a file."""
    if not os.path.exists(filepath):
        return None
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def validate_gate_1_inputs(config_dict, base_dir):
    """Gate 1: Input Data Validation."""
    data_cfg = config_dict.get('data', {})
    rain_filename = data_cfg.get('rainfall_csv') or data_cfg.get('observed_csv')
    coords_filename = data_cfg.get('station_coords_csv')

    rain_path = os.path.join(base_dir, rain_filename) if rain_filename else None
    coords_path = os.path.join(base_dir, coords_filename) if coords_filename else None

    # 1. File existence
    if not rain_path or not os.path.exists(rain_path):
        raise StopBlockedException(f"GATE 1 FAIL: Rainfall CSV not found at '{rain_path}'. Production synthetic fallback prohibited.")

    if not coords_path or not os.path.exists(coords_path):
        raise StopBlockedException(f"GATE 1 FAIL: Station coordinates CSV not found at '{coords_path}'.")

    # 2. SHA256 Verification
    expected_sha256 = data_cfg.get('canonical_sha256')
    actual_sha256 = compute_sha256(rain_path)
    if expected_sha256 and actual_sha256 != expected_sha256:
        raise StopBlockedException(f"GATE 1 FAIL: Rainfall CSV SHA256 fingerprint mismatch! Expected {expected_sha256}, got {actual_sha256}.")

    # 3. Data Schema & Record Count Check
    df_rain = pd.read_csv(rain_path)
    expected_records = data_cfg.get('expected_records_count', 12418)
    if len(df_rain) != expected_records:
        raise StopBlockedException(f"GATE 1 FAIL: Record count mismatch! Expected {expected_records}, got {len(df_rain)}.")

    # 4. Duplicate Date Check
    if 'YEAR' in df_rain.columns and 'MONTH' in df_rain.columns and 'DAY' in df_rain.columns:
        date_series = pd.to_datetime(df_rain[['YEAR', 'MONTH', 'DAY']])
        if date_series.duplicated().any():
            raise StopBlockedException("GATE 1 FAIL: Duplicate timestamps detected in daily rainfall dataset.")

    # 5. Negative Rainfall Check
    station_cols = [c for c in df_rain.columns if c not in ['YEAR', 'MONTH', 'DAY', 'Date']]
    for stn in station_cols:
        if (df_rain[stn] < 0.0).any():
            raise StopBlockedException(f"GATE 1 FAIL: Negative rainfall values detected in station {stn}.")

    return True, df_rain, rain_path, coords_path


def validate_gate_2_config(config_dict):
    """Gate 2: Configuration Parameter Validation."""
    if not config_dict.get('project', {}).get('name'):
        raise StopBlockedException("GATE 2 FAIL: Missing project name in configuration.")

    stat_cfg = config_dict.get('statistical_analysis', {})
    if stat_cfg.get('alpha', 0.05) <= 0.0 or stat_cfg.get('alpha', 0.05) >= 1.0:
        raise StopBlockedException("GATE 2 FAIL: Invalid alpha value in config.")

    if config_dict.get('project', {}).get('synthetic_fallback_enabled', False):
        raise StopBlockedException("GATE 2 FAIL: Production mode requires 'synthetic_fallback_enabled: false'.")

    return True


def validate_gate_3_statistics(trend_df):
    """Gate 3: Statistical Bounds Validation."""
    if trend_df is None or len(trend_df) == 0:
        raise StopBlockedException("GATE 3 FAIL: Empty statistical outputs.")

    if 'p_value' in trend_df.columns:
        p_vals = trend_df['p_value'].values
        if (p_vals < 0.0).any() or (p_vals > 1.0).any() or np.isnan(p_vals).any():
            raise StopBlockedException("GATE 3 FAIL: Out-of-bounds or NaN p-values detected in results.")

    return True


def validate_gate_4_provenance(manifest_dict):
    """Gate 4: Output Provenance & Manifest Validation."""
    if not manifest_dict or 'config_sha256' not in manifest_dict or 'input_sha256' not in manifest_dict:
        raise StopBlockedException("GATE 4 FAIL: Missing provenance metadata or SHA256 hashes in manifest.")

    return True
