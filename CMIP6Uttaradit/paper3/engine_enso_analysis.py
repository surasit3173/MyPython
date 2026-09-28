import os
import json
import glob
import numpy as np
import pandas as pd
from scipy import stats

# Set random seed for reproducibility
np.random.seed(20260830)

STATIONS = ['351001', '351002', '351003', '351004', '351005', '351006', '351007', '351008', '351009', '351010', '351011', '351012', '351201']
MODELS = ['ACCESS-ESM1-5', 'CanESM5', 'CESM2', 'EC-Earth3', 'FGOALS-g3', 'MIROC6', 'MRI-ESM2-0']

def calc_consecutive_days(arr, condition_val, op='ge'):
    """Calculates max length of consecutive days matching condition."""
    if op == 'ge':
        is_cond = (arr >= condition_val).astype(int)
    else:
        is_cond = (arr < condition_val).astype(int)
    max_len = 0
    curr_len = 0
    for val in is_cond:
        if val == 1:
            curr_len += 1
            if curr_len > max_len:
                max_len = curr_len
        else:
            curr_len = 0
    return max_len

def calc_rx5day(series):
    """Calculates maximum 5-day consecutive precipitation sum."""
    if len(series) < 5:
        return series.sum()
    r5 = series.rolling(window=5).sum()
    return r5.max()

def calc_seasonal_indices(daily_df, percentiles_dict=None):
    """
    Given daily_df with column 'DATE' and station columns, compute seasonal ETCCDI indices.
    Returns a DataFrame with columns: season_id, station, PRCPTOT, wet_day_freq, SDII, Rx1day, Rx5day, R20mm, R50mm, R95p, R99p, CDD, CWD
    """
    daily_df = daily_df.copy()
    daily_df['DATE'] = pd.to_datetime(daily_df['DATE'])

    if percentiles_dict is None:
        percentiles_dict = {}
        for stn in STATIONS:
            wet_vals = daily_df[daily_df[stn] >= 1.0][stn].dropna()
            percentiles_dict[stn] = {
                'p95': np.percentile(wet_vals, 95) if len(wet_vals) > 0 else 0,
                'p99': np.percentile(wet_vals, 99) if len(wet_vals) > 0 else 0
            }

    paper3_dir = os.path.dirname(__file__)
    class_df = pd.read_csv(os.path.join(paper3_dir, "enso_season_classification.csv"))

    results = []

    for idx, row in class_df.iterrows():
        s_id = row['season_id']
        s_start = pd.to_datetime(row['season_start'])
        s_end = pd.to_datetime(row['season_end'])

        sub = daily_df[(daily_df['DATE'] >= s_start) & (daily_df['DATE'] <= s_end)]
        if len(sub) == 0:
            continue

        for stn in STATIONS:
            vals = sub[stn].values
            vals_clean = np.nan_to_num(vals, nan=0.0)

            n_days = len(vals_clean)
            wet_days = vals_clean[vals_clean >= 1.0]
            n_wet = len(wet_days)

            prcptot = float(np.sum(vals_clean))
            wet_freq = float((n_wet / n_days) * 100.0) if n_days > 0 else 0.0
            sdii = float(prcptot / n_wet) if n_wet > 0 else 0.0
            rx1day = float(np.max(vals_clean)) if len(vals_clean) > 0 else 0.0
            rx5day = float(calc_rx5day(pd.Series(vals_clean)))
            r20mm = int(np.sum(vals_clean >= 20.0))
            r50mm = int(np.sum(vals_clean >= 50.0))

            p95_thresh = percentiles_dict[stn]['p95']
            p99_thresh = percentiles_dict[stn]['p99']

            r95p = float(np.sum(vals_clean[vals_clean > p95_thresh]))
            r99p = float(np.sum(vals_clean[vals_clean > p99_thresh]))

            cdd = int(calc_consecutive_days(vals_clean, 1.0, op='lt'))
            cwd = int(calc_consecutive_days(vals_clean, 1.0, op='ge'))

            results.append({
                "season_id": s_id,
                "climate_year": row['climate_year'],
                "season_type": row['season_type'],
                "ENSO_phase": row['ENSO_phase'],
                "station": stn,
                "PRCPTOT": round(prcptot, 2),
                "wet_day_freq": round(wet_freq, 2),
                "SDII": round(sdii, 2),
                "Rx1day": round(rx1day, 2),
                "Rx5day": round(rx5day, 2),
                "R20mm": r20mm,
                "R50mm": r50mm,
                "R95p": round(r95p, 2),
                "R99p": round(r99p, 2),
                "CDD": cdd,
                "CWD": cwd
            })

    res_df = pd.DataFrame(results)
    return res_df, percentiles_dict

def run_analysis():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    utt_dir = os.path.join(repo_root, "CMIP6Uttaradit")
    paper3_dir = os.path.join(utt_dir, "paper3")

    # 1. Compute Observed Seasonal Metrics
    obs_path = os.path.join(utt_dir, "Observed_Rain_daily_198101_201412_Uttaradit.csv")
    obs_df = pd.read_csv(obs_path)
    obs_df['DATE'] = pd.to_datetime(obs_df[['YEAR', 'MONTH', 'DAY']])

    obs_seasonal, obs_percentiles = calc_seasonal_indices(obs_df)
    obs_seasonal['source_type'] = 'OBSERVED'
    obs_seasonal['model'] = 'OBSERVED'
    obs_seasonal.to_csv(os.path.join(paper3_dir, "seasonal_observed.csv"), index=False)

    # 2. Compute Raw CMIP6 and QDM CMIP6 Seasonal Metrics
    raw_seasonals = []
    qdm_seasonals = []

    gcm_dir = os.path.join(utt_dir, "Data_Uttaradit")

    for model in MODELS:
        m_dir = os.path.join(gcm_dir, model)
        raw_files = glob.glob(os.path.join(m_dir, "pr_day_*_historical_*.csv"))
        qdm_files = glob.glob(os.path.join(m_dir, "bc_pr_day_*_historical_*.csv"))

        if len(raw_files) > 0:
            raw_df = pd.read_csv(raw_files[0])
            raw_df['DATE'] = pd.to_datetime(raw_df[['YEAR', 'MONTH', 'DAY']])
            r_seas, _ = calc_seasonal_indices(raw_df, percentiles_dict=obs_percentiles)
            r_seas['source_type'] = 'RAW_CMIP6'
            r_seas['model'] = model
            raw_seasonals.append(r_seas)

        if len(qdm_files) > 0:
            qdm_df = pd.read_csv(qdm_files[0])
            qdm_df['DATE'] = pd.to_datetime(qdm_df[['YEAR', 'MONTH', 'DAY']])
            q_seas, _ = calc_seasonal_indices(qdm_df, percentiles_dict=obs_percentiles)
            q_seas['source_type'] = 'QDM'
            q_seas['model'] = model
            qdm_seasonals.append(q_seas)

    raw_df_all = pd.concat(raw_seasonals, ignore_index=True)
    qdm_df_all = pd.concat(qdm_seasonals, ignore_index=True)

    raw_df_all.to_csv(os.path.join(paper3_dir, "seasonal_raw_cmip6.csv"), index=False)
    qdm_df_all.to_csv(os.path.join(paper3_dir, "seasonal_qdm.csv"), index=False)

    all_seasonal = pd.concat([obs_seasonal, raw_df_all, qdm_df_all], ignore_index=True)

    indices = ["PRCPTOT", "wet_day_freq", "SDII", "Rx1day", "Rx5day", "R20mm", "R50mm", "R95p", "R99p", "CDD", "CWD"]

    responses = []
    grouped = all_seasonal.groupby(['source_type', 'model', 'season_type', 'ENSO_phase', 'station'])[indices].mean().reset_index()

    for (stype, mdl, stype_name, stn), df_group in grouped.groupby(['source_type', 'model', 'season_type', 'station']):
        neutral_sub = df_group[df_group['ENSO_phase'] == 'NEUTRAL']
        if len(neutral_sub) == 0:
            continue
        neutral_row = neutral_sub.iloc[0]

        for phase in ['EL_NINO', 'LA_NINA']:
            phase_sub = df_group[df_group['ENSO_phase'] == phase]
            if len(phase_sub) == 0:
                continue
            phase_row = phase_sub.iloc[0]

            for idx_name in indices:
                val_neu = float(neutral_row[idx_name])
                val_phase = float(phase_row[idx_name])

                abs_diff = val_phase - val_neu
                pct_diff = (abs_diff / val_neu * 100.0) if abs(val_neu) > 1e-5 else 0.0

                responses.append({
                    "source_type": stype,
                    "model": mdl,
                    "season_type": stype_name,
                    "station": stn,
                    "ENSO_phase": phase,
                    "index": idx_name,
                    "neutral_value": round(val_neu, 3),
                    "phase_value": round(val_phase, 3),
                    "abs_response": round(abs_diff, 3),
                    "pct_response": round(pct_diff, 2)
                })

    resp_df = pd.DataFrame(responses)

    resp_df[resp_df['source_type'] == 'OBSERVED'].to_csv(os.path.join(paper3_dir, "enso_response_observed.csv"), index=False)
    resp_df[resp_df['source_type'] == 'RAW_CMIP6'].to_csv(os.path.join(paper3_dir, "enso_response_raw.csv"), index=False)
    resp_df[resp_df['source_type'] == 'QDM'].to_csv(os.path.join(paper3_dir, "enso_response_qdm.csv"), index=False)

    # ENSO Asymmetry: ASYM = A_LaNina - A_ElNino
    asymmetry_records = []
    for (stype, mdl, stype_name, stn, idx_name), df_sub in resp_df.groupby(['source_type', 'model', 'season_type', 'station', 'index']):
        ln_sub = df_sub[df_sub['ENSO_phase'] == 'LA_NINA']
        en_sub = df_sub[df_sub['ENSO_phase'] == 'EL_NINO']
        if len(ln_sub) > 0 and len(en_sub) > 0:
            a_ln_abs = float(ln_sub['abs_response'].iloc[0])
            a_en_abs = float(en_sub['abs_response'].iloc[0])
            asym_abs = a_ln_abs - a_en_abs

            a_ln_pct = float(ln_sub['pct_response'].iloc[0])
            a_en_pct = float(en_sub['pct_response'].iloc[0])
            asym_pct = a_ln_pct - a_en_pct

            asymmetry_records.append({
                "source_type": stype,
                "model": mdl,
                "season_type": stype_name,
                "station": stn,
                "index": idx_name,
                "A_LaNina_pct": round(a_ln_pct, 2),
                "A_ElNino_pct": round(a_en_pct, 2),
                "ASYM_pct": round(asym_pct, 2),
                "A_LaNina_abs": round(a_ln_abs, 3),
                "A_ElNino_abs": round(a_en_abs, 3),
                "ASYM_abs": round(asym_abs, 3)
            })

    asym_df = pd.DataFrame(asymmetry_records)
    asym_df.to_csv(os.path.join(paper3_dir, "enso_asymmetry.csv"), index=False)

    # QDM Signal Preservation Error (PE_ENSO) & Magnitude Errors
    preservation_records = []
    mag_err_records = []
    dir_agree_records = []

    obs_resp = resp_df[resp_df['source_type'] == 'OBSERVED']
    raw_resp = resp_df[resp_df['source_type'] == 'RAW_CMIP6']
    qdm_resp = resp_df[resp_df['source_type'] == 'QDM']

    for (stype_name, phase, stn, idx_name), obs_sub in obs_resp.groupby(['season_type', 'ENSO_phase', 'station', 'index']):
        r_obs = float(obs_sub['pct_response'].iloc[0])
        r_obs_abs = float(obs_sub['abs_response'].iloc[0])

        raw_m = raw_resp[(raw_resp['season_type'] == stype_name) & (raw_resp['ENSO_phase'] == phase) & (raw_resp['station'] == stn) & (raw_resp['index'] == idx_name)]
        qdm_m = qdm_resp[(qdm_resp['season_type'] == stype_name) & (qdm_resp['ENSO_phase'] == phase) & (qdm_resp['station'] == stn) & (qdm_resp['index'] == idx_name)]

        raw_pcts = raw_m['pct_response'].values
        qdm_pcts = qdm_m['pct_response'].values

        if len(raw_pcts) > 0:
            same_dir_raw = np.sum(np.sign(raw_pcts) == np.sign(r_obs))
            agree_raw = same_dir_raw / len(raw_pcts)
        else:
            agree_raw = 0

        if len(qdm_pcts) > 0:
            same_dir_qdm = np.sum(np.sign(qdm_pcts) == np.sign(r_obs))
            agree_qdm = same_dir_qdm / len(qdm_pcts)
        else:
            agree_qdm = 0

        dir_agree_records.append({
            "season_type": stype_name,
            "ENSO_phase": phase,
            "station": stn,
            "index": idx_name,
            "observed_pct_response": r_obs,
            "raw_dir_agreement": round(agree_raw, 2),
            "qdm_dir_agreement": round(agree_qdm, 2)
        })

        for mdl in MODELS:
            r_raw_sub = raw_m[raw_m['model'] == mdl]
            r_qdm_sub = qdm_m[qdm_m['model'] == mdl]

            if len(r_raw_sub) > 0 and len(r_qdm_sub) > 0:
                r_raw = float(r_raw_sub['pct_response'].iloc[0])
                r_qdm = float(r_qdm_sub['pct_response'].iloc[0])

                pe_enso = 100.0 * (r_qdm - r_raw) / r_raw if abs(r_raw) > 1e-4 else 0.0

                preservation_records.append({
                    "model": mdl,
                    "season_type": stype_name,
                    "ENSO_phase": phase,
                    "station": stn,
                    "index": idx_name,
                    "R_RAW_pct": round(r_raw, 2),
                    "R_QDM_pct": round(r_qdm, 2),
                    "PE_ENSO_pct": round(pe_enso, 2)
                })

                mag_raw = abs(r_raw - r_obs)
                mag_qdm = abs(r_qdm - r_obs)

                mag_err_records.append({
                    "model": mdl,
                    "season_type": stype_name,
                    "ENSO_phase": phase,
                    "station": stn,
                    "index": idx_name,
                    "mag_err_raw": round(mag_raw, 2),
                    "mag_err_qdm": round(mag_qdm, 2),
                    "delta_mag_err": round(mag_qdm - mag_raw, 2)
                })

    pd.DataFrame(preservation_records).to_csv(os.path.join(paper3_dir, "enso_signal_preservation.csv"), index=False)
    pd.DataFrame(mag_err_records).to_csv(os.path.join(paper3_dir, "enso_magnitude_error.csv"), index=False)
    pd.DataFrame(dir_agree_records).to_csv(os.path.join(paper3_dir, "enso_direction_agreement.csv"), index=False)

    # Statistical Inference & Diagnostics
    stat_records = []

    for stype_name in ['RAINY', 'HOT_DRY']:
        obs_sub_stype = obs_seasonal[obs_seasonal['season_type'] == stype_name]

        for phase in ['EL_NINO', 'LA_NINA']:
            phase_vals = obs_sub_stype[obs_sub_stype['ENSO_phase'] == phase]
            neu_vals = obs_sub_stype[obs_sub_stype['ENSO_phase'] == 'NEUTRAL']

            n_phase = len(phase_vals['season_id'].unique())
            n_neu = len(neu_vals['season_id'].unique())

            is_diagnostic = (n_phase < 3 or n_neu < 3)

            for idx_name in indices:
                p_arr = phase_vals.groupby('season_id')[idx_name].mean().values
                n_arr = neu_vals.groupby('season_id')[idx_name].mean().values

                if len(p_arr) >= 2 and len(n_arr) >= 2:
                    u_stat, p_val = stats.mannwhitneyu(p_arr, n_arr, alternative='two-sided')
                else:
                    p_val = np.nan

                stat_records.append({
                    "season_type": stype_name,
                    "ENSO_phase": phase,
                    "index": idx_name,
                    "n_phase": n_phase,
                    "n_neutral": n_neu,
                    "mean_phase": round(float(np.mean(p_arr)), 2) if len(p_arr) > 0 else np.nan,
                    "mean_neutral": round(float(np.mean(n_arr)), 2) if len(n_arr) > 0 else np.nan,
                    "p_value_mw": round(float(p_val), 4) if not np.isnan(p_val) else np.nan,
                    "status": "DIAGNOSTIC" if is_diagnostic else "VERIFIED"
                })

    pd.DataFrame(stat_records).to_csv(os.path.join(paper3_dir, "enso_statistics.csv"), index=False)
    print("ENSO Analysis Engine executed successfully. All outputs generated.")

if __name__ == "__main__":
    run_analysis()
