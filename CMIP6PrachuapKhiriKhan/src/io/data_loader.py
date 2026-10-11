#!/usr/bin/env python3
"""
Data Loader Module
==================
Handles loading and schema extraction for rainfall data and metadata.
"""

import os
import pandas as pd
from ..validation.validators import validate_input_files, validate_rainfall_schema

def load_project_data(config, base_dir="."):
    """Loads and validates observed daily rainfall dataset and station coordinates."""
    obs_path, coords_path = validate_input_files(config, base_dir=base_dir)

    df_obs = pd.read_csv(obs_path)
    station_cols = validate_rainfall_schema(df_obs, config)

    df_coords = pd.read_csv(coords_path)

    return {
        'df_obs': df_obs,
        'station_cols': station_cols,
        'df_coords': df_coords,
        'obs_path': obs_path,
        'coords_path': coords_path
    }
