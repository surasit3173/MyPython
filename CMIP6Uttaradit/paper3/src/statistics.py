import pandas as pd
import numpy as np
import scipy.stats as stats

def analyze_enso_responses(df_indices, source_type, model_name="OBSERVED", min_n_inference=3):
    """Compute phase averages, anomalies, percentage changes, asymmetry, and MWU tests."""
    indices = ["PRCPTOT", "Rx1day", "Rx5day", "SDII", "R95p", "R99p", "CWD", "CDD"]
    summary_rows = []

    for stype in ["RAINY", "HOT_DRY"]:
        sub_s = df_indices[df_indices["season_type"] == stype]

        for idx in indices:
            regional_by_year = sub_s.groupby(["climate_year", "enso_phase"])[idx].mean().reset_index()

            el_data = regional_by_year[regional_by_year["enso_phase"] == "EL_NINO"][idx].to_numpy()
            la_data = regional_by_year[regional_by_year["enso_phase"] == "LA_NINA"][idx].to_numpy()
            neu_data = regional_by_year[regional_by_year["enso_phase"] == "NEUTRAL"][idx].to_numpy()

            n_el, n_la, n_neu = len(el_data), len(la_data), len(neu_data)

            mean_el = np.mean(el_data) if n_el > 0 else np.nan
            mean_la = np.mean(la_data) if n_la > 0 else np.nan
            mean_neu = np.mean(neu_data) if n_neu > 0 else np.nan

            anom_el = mean_el - mean_neu if pd.notna(mean_el) and pd.notna(mean_neu) else np.nan
            anom_la = mean_la - mean_neu if pd.notna(mean_la) and pd.notna(mean_neu) else np.nan

            pct_el = (anom_el / mean_neu * 100.0) if pd.notna(anom_el) and mean_neu != 0 else np.nan
            pct_la = (anom_la / mean_neu * 100.0) if pd.notna(anom_la) and mean_neu != 0 else np.nan

            def run_mwu(d1, d2):
                if len(d1) < min_n_inference or len(d2) < min_n_inference:
                    return np.nan, np.nan
                try:
                    res = stats.mannwhitneyu(d1, d2, alternative='two-sided')
                    return float(res.statistic), float(res.pvalue)
                except Exception:
                    return np.nan, np.nan

            u_el_neu, p_el_neu = run_mwu(el_data, neu_data)
            u_la_neu, p_la_neu = run_mwu(la_data, neu_data)
            u_el_la, p_el_la = run_mwu(el_data, la_data)

            diagnostic_only = (n_el < min_n_inference) or (n_la < min_n_inference) or (n_neu < min_n_inference)

            summary_rows.append({
                "source_type": source_type,
                "model": model_name,
                "season_type": stype,
                "variable": idx,
                "n_el_nino": n_el,
                "n_la_nina": n_la,
                "n_neutral": n_neu,
                "mean_el_nino": mean_el,
                "mean_la_nina": mean_la,
                "mean_neutral": mean_neu,
                "anom_el_nino": anom_el,
                "anom_la_nina": anom_la,
                "pct_change_el_nino": pct_el,
                "pct_change_la_nina": pct_la,
                "mwu_stat_el_vs_la": u_el_la,
                "p_val_el_vs_la": p_el_la,
                "diagnostic_only": diagnostic_only
            })

    return pd.DataFrame(summary_rows)

def compute_observational_distance_metrics(df_summaries, gcm_models):
    """Compute MAE, RMSE, and Bias between Observed vs Raw and Observed vs QDM for ENSO anomalies."""
    obs_sub = df_summaries[df_summaries["source_type"] == "OBSERVED"]

    dist_rows = []
    for model in gcm_models:
        raw_m = df_summaries[(df_summaries["source_type"] == "RAW_CMIP6") & (df_summaries["model"] == model)]
        qdm_m = df_summaries[(df_summaries["source_type"] == "QDM_CMIP6") & (df_summaries["model"] == model)]

        for stype in ["RAINY", "HOT_DRY"]:
            for var in ["PRCPTOT", "Rx1day", "Rx5day", "SDII", "R95p", "R99p", "CWD", "CDD"]:
                obs_row = obs_sub[(obs_sub["season_type"] == stype) & (obs_sub["variable"] == var)].iloc[0]
                raw_row = raw_m[(raw_m["season_type"] == stype) & (raw_m["variable"] == var)].iloc[0]
                qdm_row = qdm_m[(qdm_m["season_type"] == stype) & (qdm_m["variable"] == var)].iloc[0]

                obs_anom_el = obs_row["anom_el_nino"]
                raw_anom_el = raw_row["anom_el_nino"]
                qdm_anom_el = qdm_row["anom_el_nino"]

                dist_raw_el = abs(raw_anom_el - obs_anom_el)
                dist_qdm_el = abs(qdm_anom_el - obs_anom_el)
                assessment_el = "closer" if dist_qdm_el < dist_raw_el else ("farther" if dist_qdm_el > dist_raw_el else "unchanged")

                dist_rows.append({
                    "model": model,
                    "season_type": stype,
                    "variable": var,
                    "obs_anom_el": obs_anom_el,
                    "raw_anom_el": raw_anom_el,
                    "qdm_anom_el": qdm_anom_el,
                    "dist_raw_el": dist_raw_el,
                    "dist_qdm_el": dist_qdm_el,
                    "assessment_el": assessment_el
                })
    return pd.DataFrame(dist_rows)
