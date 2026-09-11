#!/usr/bin/env python3
"""
Safe Data Ingestion & Preprocessing Module (Project 1: Prachuap Khiri Khan)
===========================================================================
Reads observed daily rainfall CSV and station metadata without synthetic fallback.
Preserves stations with elevation = NS as UNVERIFIED/UNKNOWN.
"""

import os
import pandas as pd
import numpy as np
from src.validation.gates import StopBlockedException, compute_sha256


def load_prachuap_data(config_dict, base_dir):
    """
    Loads authentic observed rainfall CSV and station metadata.
    Does NOT attempt fallback to synthetic data.
    """
    data_cfg = config_dict['data']
    rain_path = os.path.join(base_dir, data_cfg['rainfall_csv'])
    coords_path = os.path.join(base_dir, data_cfg['station_coords_csv'])
    elev_path = os.path.join(base_dir, data_cfg['station_elevation_xlsx'])

    if not os.path.exists(rain_path):
        raise StopBlockedException(f"Missing rainfall file: {rain_path}")

    # Read Daily Rainfall CSV
    df_rain = pd.read_csv(rain_path)
    if 'YEAR' in df_rain.columns and 'MONTH' in df_rain.columns and 'DAY' in df_rain.columns:
        df_rain['date'] = pd.to_datetime(df_rain[['YEAR', 'MONTH', 'DAY']])

    # Read Station Coordinates
    df_coords = pd.read_csv(coords_path) if os.path.exists(coords_path) else None

    # Handle Station Elevation NS values
    if df_coords is not None and 'elevation (m.MSL.)' in df_coords.columns:
        # Keep NS as 'UNKNOWN' / NaN without silent numerical imputation
        df_coords['elevation_status'] = np.where(
            df_coords['elevation (m.MSL.)'].astype(str).str.upper() == 'NS',
            'UNKNOWN_UNVERIFIED',
            'VERIFIED'
        )

    return df_rain, df_coords, rain_path
