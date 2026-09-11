#!/usr/bin/env python3
"""
Hydrological & Annual Aggregation Module
========================================
Aggregates daily precipitation into annual, wet season (May-Oct), and dry season (Nov-Apr) totals.
"""

import pandas as pd

def aggregate_rainfall_series(df_obs, station_col):
    """
    Aggregates daily data for a station into Annual, Wet Season, and Dry Season series.
    Wet Season: Months 5..10 (May-Oct)
    Dry Season: Months 1..4 & 11..12 (Jan-Apr, Nov-Dec)
    """
    df = df_obs.copy()
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month

    # Annual
    annual_df = df.groupby('year')[station_col].sum().reset_index()
    annual_df = annual_df.rename(columns={station_col: 'precip_mm'})

    # Wet Season
    wet_mask = df['month'].isin([5, 6, 7, 8, 9, 10])
    wet_df = df[wet_mask].groupby('year')[station_col].sum().reset_index()
    wet_df = wet_df.rename(columns={station_col: 'precip_mm'})

    # Dry Season
    dry_mask = df['month'].isin([1, 2, 3, 4, 11, 12])
    dry_df = df[dry_mask].groupby('year')[station_col].sum().reset_index()
    dry_df = dry_df.rename(columns={station_col: 'precip_mm'})

    return {
        'Annual': annual_df,
        'Wet Season': wet_df,
        'Dry Season': dry_df
    }
