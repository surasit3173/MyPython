#!/usr/bin/env python3
"""
ETCCDI 11 Extreme Precipitation Indices Calculation Module (Project 2: Uttaradit)
=================================================================================
Implements the 11 locked ETCCDI indices:
1. PRCPTOT 2. SDII 3. Rx1day 4. Rx5day 5. CDD 6. CWD
7. R10mm 8. R20mm 9. R50mm 10. R95p 11. R99p
Wet day threshold = 1.0 mm/day. R50mm study-specific threshold preserved.
"""

import numpy as np
import pandas as pd


def calculate_uttaradit_etccdi_11(df_daily, date_col='date', val_col='precipitation_mm', baseline_years=(1995, 2014)):
    """
    Calculates 11 ETCCDI extreme precipitation indices for daily time series.
    """
    df = df_daily.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df['year'] = df[date_col].dt.year

    # Baseline percentiles (1995-2014)
    base_mask = (df['year'] >= baseline_years[0]) & (df['year'] <= baseline_years[1])
    base_wet_days = df[base_mask & (df[val_col] >= 1.0)][val_col].values
    
    p95 = float(np.percentile(base_wet_days, 95)) if len(base_wet_days) > 0 else 0.0
    p99 = float(np.percentile(base_wet_days, 99)) if len(base_wet_days) > 0 else 0.0

    results = []
    for year, group in df.groupby('year'):
        vals = group[val_col].values
        wet_vals = vals[vals >= 1.0]

        prcptot = float(np.sum(wet_vals))
        sdii = float(prcptot / len(wet_vals)) if len(wet_vals) > 0 else 0.0
        rx1day = float(np.max(vals)) if len(vals) > 0 else 0.0
        rx5day = float(pd.Series(vals).rolling(window=5).sum().max()) if len(vals) >= 5 else rx1day

        r10mm = int(np.sum(vals >= 10.0))
        r20mm = int(np.sum(vals >= 20.0))
        r50mm = int(np.sum(vals >= 50.0))

        r95p = float(np.sum(wet_vals[wet_vals > p95])) if len(wet_vals) > 0 else 0.0
        r99p = float(np.sum(wet_vals[wet_vals > p99])) if len(wet_vals) > 0 else 0.0

        # CWD & CDD
        is_wet = (vals >= 1.0).astype(int)
        is_dry = (vals < 1.0).astype(int)

        def max_consec(arr):
            if len(arr) == 0 or np.sum(arr) == 0:
                return 0
            cum = (arr != pd.Series(arr).shift()).cumsum()
            return int(pd.Series(arr).groupby(cum).sum().max())

        cwd = max_consec(is_wet)
        cdd = max_consec(is_dry)

        results.append({
            'year': int(year),
            'PRCPTOT': prcptot,
            'SDII': sdii,
            'Rx1day': rx1day,
            'Rx5day': rx5day,
            'CDD': cdd,
            'CWD': cwd,
            'R10mm': r10mm,
            'R20mm': r20mm,
            'R50mm': r50mm,
            'R95p': r95p,
            'R99p': r99p
        })

    return pd.DataFrame(results)
