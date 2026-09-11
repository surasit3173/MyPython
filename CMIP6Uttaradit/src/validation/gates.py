#!/usr/bin/env python3
"""
Validation Gates & Firewall Module (Project 2: Uttaradit)
=========================================================
Implements Gate 1 (Input), Gate 2 (Config), Gate 3 (Stat), Gate 4 (Output/Provenance).
Triggers STOP_BLOCKED on validation failure. Zero synthetic fallbacks allowed.
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


def validate_gate_1_uttaradit_inputs(config_dict, base_dir):
    """Gate 1: Input Data & GCM Directory Validation."""
    data_cfg = config_dict.get('data', {})
    obs_filename = data_cfg.get('observed_csv')
    coords_filename = data_cfg.get('station_coords_csv')

    obs_path = os.path.join(base_dir, obs_filename) if obs_filename else None
    coords_path = os.path.join(base_dir, coords_filename) if coords_filename else None

    # 1. File existence
    if not obs_path or not os.path.exists(obs_path):
        raise StopBlockedException(f"GATE 1 FAIL: Observed rainfall CSV not found at '{obs_path}'. Production synthetic fallback prohibited.")

    if not coords_path or not os.path.exists(coords_path):
        raise StopBlockedException(f"GATE 1 FAIL: Station coordinates CSV not found at '{coords_path}'.")

    # 2. GCM Directories Check
    gcms = config_dict.get('gcms', [])
    gcms_dir = os.path.join(base_dir, data_cfg.get('gcms_dir', 'Data_Uttaradit'))
    for gcm in gcms:
        gcm_folder = os.path.join(gcms_dir, gcm)
        if not os.path.exists(gcm_folder):
            raise StopBlockedException(f"GATE 1 FAIL: Missing required GCM directory for '{gcm}' at '{gcm_folder}'.")

    # 3. Read & Validate Observed Data
    df_obs = pd.read_csv(obs_path)
    expected_stations = data_cfg.get('expected_observed_stations_count', 13)
    station_cols = [c for c in df_obs.columns if c not in ['YEAR', 'MONTH', 'DAY', 'Date', 'date']]
    if len(station_cols) != expected_stations:
        raise StopBlockedException(f"GATE 1 FAIL: Station count mismatch! Expected {expected_stations}, got {len(station_cols)}.")

    return True, df_obs, obs_path, coords_path


def validate_gate_2_config(config_dict):
    """Gate 2: Configuration Parameter Validation."""
    if not config_dict.get('project', {}).get('name'):
        raise StopBlockedException("GATE 2 FAIL: Missing project name in configuration.")

    if config_dict.get('project', {}).get('synthetic_fallback_enabled', False):
        raise StopBlockedException("GATE 2 FAIL: Production mode requires 'synthetic_fallback_enabled: false'.")

    return True
