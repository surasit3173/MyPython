#!/usr/bin/env python3
"""
Validation Module for Fail-Closed Execution
===========================================
Strict schema, file presence, station metadata, and date range validators.
Prevents silent error recovery or synthetic data fallback.
"""

import os
import pandas as pd

class StopBlockedException(Exception):
    """Raised when validation gate fails and execution must stop."""
    pass

def validate_input_files(config, base_dir="."):
    """Validates existence of raw input files specified in config."""
    obs_path = os.path.join(base_dir, config['data']['observed_csv'])
    coords_path = os.path.join(base_dir, config['data']['station_coords_csv'])

    if not os.path.exists(obs_path):
        raise StopBlockedException(f"FAIL-CLOSED: Observed rainfall CSV not found at '{obs_path}'")
    if not os.path.exists(coords_path):
        raise StopBlockedException(f"FAIL-CLOSED: Station coordinates CSV not found at '{coords_path}'")

    return obs_path, coords_path

def validate_rainfall_schema(df_obs, config):
    """Validates date columns, missing values, duplicate dates, and station count."""
    date_cols = config['data']['date_columns']
    for col in date_cols:
        if col not in df_obs.columns:
            raise StopBlockedException(f"FAIL-CLOSED: Missing required date column '{col}' in input CSV.")

    # Check date construction
    try:
        df_obs['date'] = pd.to_datetime(df_obs[date_cols])
    except Exception as e:
        raise StopBlockedException(f"FAIL-CLOSED: Invalid date format in input CSV: {e}")

    # Duplicate dates check
    dup_count = df_obs['date'].duplicated().sum()
    if dup_count > 0:
        raise StopBlockedException(f"FAIL-CLOSED: Input dataset contains {dup_count} duplicate dates.")

    # Date range check
    min_year = df_obs['date'].dt.year.min()
    max_year = df_obs['date'].dt.year.max()
    exp_start, exp_end = config['data']['analysis_period']

    if min_year > exp_start or max_year < exp_end:
        raise StopBlockedException(
            f"FAIL-CLOSED: Data period [{min_year}, {max_year}] does not cover required analysis period [{exp_start}, {exp_end}]"
        )

    # Station columns check
    station_cols = [c for c in df_obs.columns if c not in date_cols and c != 'date']
    exp_count = config['data']['expected_station_count']

    if len(station_cols) != exp_count:
        raise StopBlockedException(
            f"FAIL-CLOSED: Observed station count {len(station_cols)} does not match expected count {exp_count} in config."
        )

    # Missing values check
    missing_count = df_obs[station_cols].isna().sum().sum()
    if missing_count > 0:
        raise StopBlockedException(f"FAIL-CLOSED: Input dataset contains {missing_count} missing observation values.")

    return station_cols
