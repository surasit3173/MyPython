#!/usr/bin/env python3
"""
Trend Execution Pipeline Module
===============================
Orchestrates statistical calculations across all stations and periods.
Attaches explicit status (VALID, INVALID_INPUT, DOMAIN_ERROR, NOT_COMPUTED) to every result.
"""

import numpy as np
import pandas as pd
from ..statistics.sens_slope import sens_slope
from ..statistics.mann_kendall import standard_mann_kendall
from ..statistics.yue_wang_mmk import yue_wang_mmk
from ..aggregation.seasonal_aggregator import aggregate_rainfall_series

def run_trend_analysis_pipeline(data_info, config):
    """Runs complete trend analysis pipeline across stations and periods."""
    df_obs = data_info['df_obs']
    station_cols = data_info['station_cols']
    alpha = config['analysis']['alpha']
    r1_alpha = config['analysis']['r1_significance_alpha']

    results = []

    for stn in station_cols:
        try:
            stn_id = int(float(stn))
        except ValueError:
            stn_id = stn
        aggregated = aggregate_rainfall_series(df_obs, stn)

        for period_name, p_df in aggregated.items():
            series = p_df['precip_mm'].values
            n_obs = len(series)

            mean_val = float(np.mean(series)) if n_obs > 0 else 0.0

            # 1. Sen's Slope
            slope = sens_slope(series)

            # 2. Standard MK
            mk_res = standard_mann_kendall(series)

            # 3. Yue & Wang (2004) AR(1) MMK (Primary)
            yw_res = yue_wang_mmk(series, alpha=alpha, r1_alpha=r1_alpha)

            # Determine overall status
            if mk_res['status'] == 'DOMAIN_ERROR' or yw_res['status'] == 'DOMAIN_ERROR':
                status = 'DOMAIN_ERROR'
            elif mk_res['status'] == 'NOT_COMPUTED' or yw_res['status'] == 'NOT_COMPUTED':
                status = 'NOT_COMPUTED'
            else:
                status = 'VALID'

            results.append({
                'station_id': stn_id,
                'period': period_name,
                'n_obs': n_obs,
                'mean_precip_mm': round(mean_val, 2),
                'sen_slope': round(slope, 3),
                'std_mk_S': mk_res['S'],
                'std_mk_var_S': round(mk_res['var_S'], 2),
                'std_mk_Z': round(mk_res['Z'], 3),
                'std_mk_p': round(mk_res['p_value'], 4),
                'primary_method': 'yue_wang_2004',
                'yw_r1': round(yw_res['r1'], 4) if not np.isnan(yw_res['r1']) else None,
                'yw_r1_significant': yw_res['r1_significant'],
                'yw_n_ns_star': round(yw_res['n_ns_star'], 4) if not np.isnan(yw_res['n_ns_star']) else None,
                'yw_var_S_mod': round(yw_res['var_S_mod'], 2) if not np.isnan(yw_res['var_S_mod']) else None,
                'yw_mmk_Z': round(yw_res['Z_mmk'], 3) if not np.isnan(yw_res['Z_mmk']) else None,
                'yw_mmk_p': round(yw_res['p_value_mmk'], 4) if not np.isnan(yw_res['p_value_mmk']) else None,
                'status': status
            })

    return pd.DataFrame(results)
