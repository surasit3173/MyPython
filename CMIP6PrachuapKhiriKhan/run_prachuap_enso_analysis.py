#!/usr/bin/env python3
"""
Complete ENSO-Precipitation Analysis Pipeline for Prachuap Khiri Khan Province
Independent Numerical Analysis Package (NO Uttaradit Numerical Dependency)
Strict Data Isolation & Data-Driven Recomputation
"""

import os
import sys
import glob
import json
import hashlib
import numpy as np
import pandas as pd
import scipy.stats as stats
import matplotlib.pyplot as plt

# Base paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
INPUTS_DIR = os.path.join(BASE_DIR, "inputs")
GCM_INPUTS_DIR = os.path.join(INPUTS_DIR, "gcm")
ENSO_INPUTS_DIR = os.path.join(INPUTS_DIR, "enso")

OUTPUT_DIR = os.path.join(BASE_DIR, "output")
TABLES_DIR = os.path.join(OUTPUT_DIR, "tables")
FIGURES_DIR = os.path.join(OUTPUT_DIR, "figures")
MANIFESTS_DIR = os.path.join(OUTPUT_DIR, "manifests")
LOGS_DIR = os.path.join(OUTPUT_DIR, "logs")

for d in [OUTPUT_DIR, TABLES_DIR, FIGURES_DIR, MANIFESTS_DIR, LOGS_DIR]:
    os.makedirs(d, exist_ok=True)

def compute_sha256(filepath):
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

# ------------------------------------------------------------------------------
# 1. ENSO CLASSIFICATION & SEASONAL PROCESSING
# ------------------------------------------------------------------------------

def parse_noaa_oni(oni_html_path):
    """Parse frozen NOAA CPC ERSSTv6 ONI HTML table."""
    tables = pd.read_html(oni_html_path)
    selected = None
    for table in tables:
        if table.shape[1] >= 13 and str(table.iloc[0, 0]).strip() == "Year":
            selected = table.copy()
            break
    if selected is None:
        raise ValueError("NOAA ONI table not found in HTML")

    selected.columns = [str(v).strip() for v in selected.iloc[0]]
    selected = selected.iloc[1:].copy()
    selected["Year"] = pd.to_numeric(selected["Year"], errors="coerce")
    selected = selected.dropna(subset=["Year"])
    selected["Year"] = selected["Year"].astype(int)

    seasons_list = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
    rows = []
    for record in selected.itertuples(index=False):
        yr = int(record[0])
        for month, season_name in enumerate(seasons_list, start=1):
            val = pd.to_numeric(record[month], errors="coerce")
            if pd.isna(val): continue
            rows.append({"date": pd.Timestamp(year=yr, month=month, day=1), "season": season_name, "oni_c": float(val)})

    df_oni = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)

    # Persistence rule: >= 5 consecutive overlapping 3-month windows >= +0.5 or <= -0.5
    vals = df_oni["oni_c"].to_numpy()
    cand = np.where(vals >= 0.5, 1, np.where(vals <= -0.5, -1, 0))
    ep = np.zeros(len(cand), dtype=int)

    i, n = 0, len(cand)
    while i < n:
        if cand[i] == 0:
            i += 1
            continue
        j = i
        while j < n and cand[j] == cand[i]:
            j += 1
        if (j - i) >= 5:
            ep[i:j] = cand[i]
        i = j

    df_oni["episode_sign"] = ep
    df_oni["episode_phase"] = df_oni["episode_sign"].map({-1: "LA_NINA", 0: "NEUTRAL", 1: "EL_NINO"})
    return df_oni


def classify_seasons(df_oni, start_year=1981, end_year=2014):
    """Classify management seasons: Rainy (May-Oct) and Hot/Dry (Nov-Apr)."""
    windows = []
    for d in df_oni["date"]:
        p = d.to_period("M")
        windows.append(((p - 1).start_time, (p + 1).end_time))

    season_rows = []
    for cy in range(start_year, end_year + 1):
        r_start, r_end = pd.Timestamp(cy, 5, 1), pd.Timestamp(cy, 10, 31)
        hd_start, hd_end = pd.Timestamp(cy, 11, 1), pd.Timestamp(cy + 1, 4, 30)

        for stype, sstart, send in [("RAINY", r_start, r_end), ("HOT_DRY", hd_start, hd_end)]:
            if stype == "HOT_DRY" and cy == end_year:
                continue # Exclude incomplete season (ends April 2015, daily obs end Dec 2014)

            overlap = [wstart <= send and wend >= sstart for wstart, wend in windows]
            sub = df_oni[overlap]
            n_win = len(sub)
            n_el = (sub["episode_sign"] == 1).sum()
            n_la = (sub["episode_sign"] == -1).sum()
            if n_el > n_win / 2:
                phase = "EL_NINO"
            elif n_la > n_win / 2:
                phase = "LA_NINA"
            elif n_el == 0 and n_la == 0:
                phase = "NEUTRAL"
            else:
                phase = "TRANSITION_UNCLASSIFIED"

            season_rows.append({
                "season_type": stype,
                "climate_year": cy,
                "season_start": sstart.strftime("%Y-%m-%d"),
                "season_end": send.strftime("%Y-%m-%d"),
                "enso_phase": phase,
                "oni_mean_c": float(sub["oni_c"].mean()),
                "oni_min_c": float(sub["oni_c"].min()),
                "oni_max_c": float(sub["oni_c"].max()),
                "n_overlapping_windows": n_win,
                "n_el_nino_windows": int(n_el),
                "n_la_nina_windows": int(n_la),
                "n_neutral_windows": int(n_win - n_el - n_la),
                "classification_rule": "strict majority of overlapping persistent episode windows"
            })
    return pd.DataFrame(season_rows)


def generate_episode_catalog(df_oni):
    """Generate catalog of persistent ENSO episodes."""
    ordered = df_oni.sort_values("date").reset_index(drop=True)
    groups = ordered["episode_sign"].ne(ordered["episode_sign"].shift()).cumsum()
    rows = []
    counter = {1: 0, -1: 0}
    for _, group in ordered.groupby(groups):
        sign = int(group["episode_sign"].iloc[0])
        if sign == 0: continue
        counter[sign] += 1
        phase = "EL_NINO" if sign == 1 else "LA_NINA"
        prefix = "EN" if sign == 1 else "LN"
        rows.append({
            "episode_id": f"{prefix}_{counter[sign]:02d}",
            "phase": phase,
            "start_center_month": group["date"].min().strftime("%Y-%m"),
            "end_center_month": group["date"].max().strftime("%Y-%m"),
            "n_consecutive_overlapping_seasons": int(len(group)),
            "index_mean_c": float(group["oni_c"].mean()),
            "index_min_c": float(group["oni_c"].min()),
            "index_max_c": float(group["oni_c"].max()),
            "threshold_c": 0.5,
            "persistence_seasons": 5,
            "source": "NOAA_CPC_ONI_ERSSTv6"
        })
    return pd.DataFrame(rows)

# ------------------------------------------------------------------------------
# 2. PRECIPITATION INDICES CALCULATION
# ------------------------------------------------------------------------------

def compute_seasonal_indices(df_daily, df_seasons, stations, p95_dict, p99_dict):
    """Compute PRCPTOT, Rx1day, Rx5day, R95p, R99p, CWD, CDD, SDII per season and station."""
    if "date" not in df_daily.columns:
        df_daily["date"] = pd.to_datetime(df_daily[["YEAR", "MONTH", "DAY"]])
    df_daily = df_daily.set_index("date").sort_index()

    results = []
    for _, srow in df_seasons.iterrows():
        stype = srow["season_type"]
        cy = srow["climate_year"]
        phase = srow["enso_phase"]
        sstart = pd.Timestamp(srow["season_start"])
        send = pd.Timestamp(srow["season_end"])

        sub = df_daily.loc[sstart:send]
        if sub.empty: continue

        for sta in stations:
            vals = sub[sta].to_numpy(dtype=float)

            prcptot = np.sum(vals)
            rx1day = np.max(vals) if len(vals) > 0 else 0.0

            if len(vals) >= 5:
                rx5day = np.max(pd.Series(vals).rolling(5).sum().dropna().to_numpy())
            else:
                rx5day = rx1day

            wet_vals = vals[vals >= 1.0]
            sdii = np.mean(wet_vals) if len(wet_vals) > 0 else 0.0

            p95_val = p95_dict[sta]
            p99_val = p99_dict[sta]
            r95p = np.sum(vals[vals > p95_val])
            r99p = np.sum(vals[vals > p99_val])

            wet_mask = (vals >= 1.0).astype(int)
            cwd, cdd = 0, 0
            curr_w, curr_d = 0, 0
            for w in wet_mask:
                if w == 1:
                    curr_w += 1
                    curr_d = 0
                    if curr_w > cwd: cwd = curr_w
                else:
                    curr_d += 1
                    curr_w = 0
                    if curr_d > cdd: cdd = curr_d

            results.append({
                "season_type": stype,
                "climate_year": cy,
                "enso_phase": phase,
                "station": sta,
                "PRCPTOT": prcptot,
                "Rx1day": rx1day,
                "Rx5day": rx5day,
                "SDII": sdii,
                "R95p": r95p,
                "R99p": r99p,
                "CWD": cwd,
                "CDD": cdd
            })

    return pd.DataFrame(results)

# ------------------------------------------------------------------------------
# 3. STATISTICAL INFERENCE, ANOMALY & OBSERVATIONAL DISTANCE METRICS
# ------------------------------------------------------------------------------

def analyze_enso_responses(df_indices, source_type, model_name="OBSERVED"):
    """Compute phase averages, anomalies, percentage changes, asymmetry, and MWU tests."""
    indices = ["PRCPTOT", "Rx1day", "Rx5day", "SDII", "R95p", "R99p", "CWD", "CDD"]

    summary_rows = []
    asym_rows = []

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
                if len(d1) < 2 or len(d2) < 2:
                    return np.nan, np.nan
                try:
                    res = stats.mannwhitneyu(d1, d2, alternative='two-sided')
                    return float(res.statistic), float(res.pvalue)
                except Exception:
                    return np.nan, np.nan

            u_el_neu, p_el_neu = run_mwu(el_data, neu_data)
            u_la_neu, p_la_neu = run_mwu(la_data, neu_data)
            u_el_la, p_el_la = run_mwu(el_data, la_data)

            low_n_flag = (n_el < 5) or (n_la < 5) or (n_neu < 5)

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
                "mwu_stat_el_vs_neu": u_el_neu,
                "p_val_el_vs_neu": p_el_neu,
                "mwu_stat_la_vs_neu": u_la_neu,
                "p_val_la_vs_neu": p_la_neu,
                "mwu_stat_el_vs_la": u_el_la,
                "p_val_el_vs_la": p_el_la,
                "low_n_flag": low_n_flag
            })

            if pd.notna(anom_el) and pd.notna(anom_la):
                asym_abs = float(anom_el + anom_la)
                asym_pct = (asym_abs / mean_neu * 100.0) if mean_neu != 0 else np.nan
                asym_rows.append({
                    "source_type": source_type,
                    "model": model_name,
                    "season_type": stype,
                    "variable": idx,
                    "anom_el_nino": anom_el,
                    "anom_la_nina": anom_la,
                    "asymmetry_sum_anom": asym_abs,
                    "asymmetry_pct": asym_pct,
                    "p_val_el_vs_la": p_el_la,
                    "significant_asymmetry_p05": (p_el_la < 0.05) if pd.notna(p_el_la) else False,
                    "low_n_flag": low_n_flag
                })

    return pd.DataFrame(summary_rows), pd.DataFrame(asym_rows)

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

                # El Nino Anomaly Distance
                obs_anom_el = obs_row["anom_el_nino"]
                raw_anom_el = raw_row["anom_el_nino"]
                qdm_anom_el = qdm_row["anom_el_nino"]

                dist_raw_el = abs(raw_anom_el - obs_anom_el)
                dist_qdm_el = abs(qdm_anom_el - obs_anom_el)
                movement_el = "TOWARD_OBSERVATION" if dist_qdm_el < dist_raw_el else ("AWAY_FROM_OBSERVATION" if dist_qdm_el > dist_raw_el else "NO_CHANGE")

                # La Nina Anomaly Distance
                obs_anom_la = obs_row["anom_la_nina"]
                raw_anom_la = raw_row["anom_la_nina"]
                qdm_anom_la = qdm_row["anom_la_nina"]

                dist_raw_la = abs(raw_anom_la - obs_anom_la)
                dist_qdm_la = abs(qdm_anom_la - obs_anom_la)
                movement_la = "TOWARD_OBSERVATION" if dist_qdm_la < dist_raw_la else ("AWAY_FROM_OBSERVATION" if dist_qdm_la > dist_raw_la else "NO_CHANGE")

                dist_rows.append({
                    "model": model,
                    "season_type": stype,
                    "variable": var,
                    "obs_anom_el": obs_anom_el,
                    "raw_anom_el": raw_anom_el,
                    "qdm_anom_el": qdm_anom_el,
                    "abs_err_raw_el": dist_raw_el,
                    "abs_err_qdm_el": dist_qdm_el,
                    "qdm_movement_el_nino": movement_el,
                    "obs_anom_la": obs_anom_la,
                    "raw_anom_la": raw_anom_la,
                    "qdm_anom_la": qdm_anom_la,
                    "abs_err_raw_la": dist_raw_la,
                    "abs_err_qdm_la": dist_qdm_la,
                    "qdm_movement_la_nina": movement_la
                })
    return pd.DataFrame(dist_rows)

# ------------------------------------------------------------------------------
# 4. MAIN EXECUTION PIPELINE
# ------------------------------------------------------------------------------

def main():
    print("=== STARTING PRACHUAP KHIRI KHAN ENSO ANALYSIS PIPELINE ===")

    # Path setup
    obs_path = os.path.join(DATA_DIR, "Observed_Rain_daily_198101_201412_PrachuapKhiriKhan.csv")
    coords_path = os.path.join(DATA_DIR, "station_coordinates_PrachuapKhiriKhan.csv")
    oni_html_path = os.path.join(ENSO_INPUTS_DIR, "noaa_cpc_oni_ersstv6_2026-09-01.html")

    # Load Observed Data & Coords
    obs = pd.read_csv(obs_path)
    stations = [c for c in obs.columns if c not in ["YEAR", "MONTH", "DAY"]]
    print(f"Loaded Observed Data: {obs.shape[0]} daily records, {len(stations)} stations.")

    # Calculate P95 and P99 threshold per station from Observed data
    obs["date"] = pd.to_datetime(obs[["YEAR", "MONTH", "DAY"]])
    obs_indexed = obs.set_index("date")
    p95_dict = {}
    p99_dict = {}
    for s in stations:
        wet = obs_indexed[s][obs_indexed[s] >= 1.0]
        p95_dict[s] = wet.quantile(0.95)
        p99_dict[s] = wet.quantile(0.99)

    # 1. ENSO Classification
    print("\n1. Classifying ENSO episodes and management seasons...")
    df_oni = parse_noaa_oni(oni_html_path)
    df_seasons = classify_seasons(df_oni, start_year=1981, end_year=2014)
    df_catalog = generate_episode_catalog(df_oni)

    # Save ENSO outputs
    df_seasons.to_csv(os.path.join(TABLES_DIR, "enso_classification_summary.csv"), index=False)
    df_catalog.to_csv(os.path.join(TABLES_DIR, "enso_episode_catalog.csv"), index=False)

    sample_sizes = df_seasons.groupby(["season_type", "enso_phase"]).size().reset_index(name="n_seasons")
    sample_sizes["source_type"] = "OBSERVED"
    sample_sizes["model"] = "OBSERVED"
    sample_sizes.to_csv(os.path.join(TABLES_DIR, "enso_phase_sample_sizes.csv"), index=False)

    print("ENSO Season Counts:")
    print(sample_sizes)

    # 2. Observed Rainfall Indices Calculation
    print("\n2. Computing Observed seasonal precipitation indices...")
    df_obs_indices = compute_seasonal_indices(obs, df_seasons, stations, p95_dict, p99_dict)
    df_obs_indices.to_csv(os.path.join(TABLES_DIR, "observed_seasonal_indices.csv"), index=False)

    obs_summary, obs_asym = analyze_enso_responses(df_obs_indices, "OBSERVED", "OBSERVED")

    # 3. GCM Models (Raw and QDM)
    gcm_models = ["ACCESS-ESM1-5", "CESM2", "CanESM5", "EC-Earth3", "MIROC6"]

    all_summaries = [obs_summary]
    all_asym = [obs_asym]
    all_indices_list = [df_obs_indices.assign(source_type="OBSERVED", model="OBSERVED")]

    print("\n3. Processing GCM Models (Raw & QDM)...")
    for model in gcm_models:
        raw_pattern = os.path.join(GCM_INPUTS_DIR, f"pr_day_{model}_*_Prachuap Khiri Khan.csv")
        bc_pattern = os.path.join(GCM_INPUTS_DIR, f"bc_pr_day_{model}_*_Prachuap Khiri Khan.csv")

        raw_files = glob.glob(raw_pattern)
        bc_files = glob.glob(bc_pattern)

        if not raw_files or not bc_files:
            raise FileNotFoundError(f"Missing required GCM files for model {model} in {GCM_INPUTS_DIR}")

        df_raw = pd.read_csv(raw_files[0])
        df_raw_ind = compute_seasonal_indices(df_raw, df_seasons, stations, p95_dict, p99_dict)
        df_raw_ind["source_type"] = "RAW_CMIP6"
        df_raw_ind["model"] = model
        all_indices_list.append(df_raw_ind)

        raw_sum, raw_as = analyze_enso_responses(df_raw_ind, "RAW_CMIP6", model)
        all_summaries.append(raw_sum)
        all_asym.append(raw_as)

        df_bc = pd.read_csv(bc_files[0])
        df_bc_ind = compute_seasonal_indices(df_bc, df_seasons, stations, p95_dict, p99_dict)
        df_bc_ind["source_type"] = "QDM_CMIP6"
        df_bc_ind["model"] = model
        all_indices_list.append(df_bc_ind)

        bc_sum, bc_as = analyze_enso_responses(df_bc_ind, "QDM_CMIP6", model)
        all_summaries.append(bc_sum)
        all_asym.append(bc_as)

        print(f"  Completed GCM: {model}")

    df_all_summaries = pd.concat(all_summaries, ignore_index=True)
    df_all_asym = pd.concat(all_asym, ignore_index=True)
    df_all_indices = pd.concat(all_indices_list, ignore_index=True)

    df_all_summaries.to_csv(os.path.join(TABLES_DIR, "enso_response_summary.csv"), index=False)
    df_all_asym.to_csv(os.path.join(TABLES_DIR, "enso_asymmetry_summary.csv"), index=False)
    df_all_indices.to_csv(os.path.join(TABLES_DIR, "all_source_seasonal_indices.csv"), index=False)

    # 4. PE_ENSO & Observational Distance Metrics
    print("\n4. Calculating PE_ENSO & Observational Distance Metrics...")
    pe_rows = []
    for model in gcm_models:
        raw_m = df_all_summaries[(df_all_summaries["source_type"] == "RAW_CMIP6") & (df_all_summaries["model"] == model)]
        qdm_m = df_all_summaries[(df_all_summaries["source_type"] == "QDM_CMIP6") & (df_all_summaries["model"] == model)]

        merged = pd.merge(raw_m, qdm_m, on=["season_type", "variable"], suffixes=("_RAW", "_QDM"))
        for _, r in merged.iterrows():
            stype = r["season_type"]
            var = r["variable"]

            anom_el_raw = r["anom_el_nino_RAW"]
            anom_el_qdm = r["anom_el_nino_QDM"]
            anom_la_raw = r["anom_la_nina_RAW"]
            anom_la_qdm = r["anom_la_nina_QDM"]

            pe_el = (100.0 * (anom_el_qdm - anom_el_raw) / abs(anom_el_raw)) if (pd.notna(anom_el_raw) and abs(anom_el_raw) > 1e-6) else np.nan
            pe_la = (100.0 * (anom_la_qdm - anom_la_raw) / abs(anom_la_raw)) if (pd.notna(anom_la_raw) and abs(anom_la_raw) > 1e-6) else np.nan

            pe_rows.append({
                "model": model,
                "season_type": stype,
                "variable": var,
                "anom_el_raw": anom_el_raw,
                "anom_el_qdm": anom_el_qdm,
                "pe_enso_el_nino_pct": pe_el,
                "anom_la_raw": anom_la_raw,
                "anom_la_qdm": anom_la_qdm,
                "pe_enso_la_nina_pct": pe_la,
                "flag_unstable_denominator": (abs(anom_el_raw) < 1.0 if pd.notna(anom_el_raw) else True)
            })

    df_pe = pd.DataFrame(pe_rows)
    df_pe.to_csv(os.path.join(TABLES_DIR, "qdm_relative_change_pe_enso.csv"), index=False)

    df_obs_dist = compute_observational_distance_metrics(df_all_summaries, gcm_models)
    df_obs_dist.to_csv(os.path.join(TABLES_DIR, "qdm_observational_distance_metrics.csv"), index=False)

    # 5. GENERATE PUBLICATION FIGURES
    print("\n5. Generating Publication Figures...")
    plt.rcParams["font.sans-serif"] = "DejaVu Sans"
    plt.rcParams["font.family"] = "sans-serif"

    # Figure 1: ENSO Classification Timeline & ONI Index
    fig, ax = plt.subplots(figsize=(10, 4.5), dpi=300)
    dates = df_oni["date"]
    oni_vals = df_oni["oni_c"]
    ax.plot(dates, oni_vals, color="gray", linewidth=1, label="ONI (°C)")
    ax.axhline(0.5, color="red", linestyle="--", linewidth=0.8, alpha=0.7)
    ax.axhline(-0.5, color="blue", linestyle="--", linewidth=0.8, alpha=0.7)
    ax.axhline(0, color="black", linewidth=0.5)

    el_mask = df_oni["episode_sign"] == 1
    la_mask = df_oni["episode_sign"] == -1
    ax.fill_between(dates, oni_vals, 0.5, where=el_mask & (oni_vals >= 0.5), color="red", alpha=0.4, label="El Niño Episode")
    ax.fill_between(dates, oni_vals, -0.5, where=la_mask & (oni_vals <= -0.5), color="blue", alpha=0.4, label="La Niña Episode")

    ax.set_title("NOAA CPC Oceanic Niño Index (ONI ERSSTv6) and Persistent ENSO Episodes (1981–2014)", fontsize=11, fontweight="bold")
    ax.set_ylabel("ONI Anomaly (°C)")
    ax.set_xlabel("Year")
    ax.legend(loc="upper right", frameon=True)
    ax.grid(True, linestyle=":", alpha=0.5)
    plt.tight_layout()
    fig.savefig(os.path.join(FIGURES_DIR, "Figure1_ENSO_Classification_Timeline.png"))
    fig.savefig(os.path.join(FIGURES_DIR, "Figure1_ENSO_Classification_Timeline.pdf"))
    plt.close()

    # Figure 2: Observed vs Raw vs QDM Seasonal PRCPTOT Response by ENSO Phase
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), dpi=300, sharey=True)
    stypes = ["RAINY", "HOT_DRY"]
    st_titles = ["Rainy Season (May–Oct)", "Hot/Dry Season (Nov–Apr)"]

    for i, stype in enumerate(stypes):
        ax = axes[i]
        df_sub = df_all_summaries[(df_all_summaries["season_type"] == stype) & (df_all_summaries["variable"] == "PRCPTOT")]

        obs_r = df_sub[df_sub["source_type"] == "OBSERVED"].iloc[0]
        raw_mean_el = df_sub[df_sub["source_type"] == "RAW_CMIP6"]["anom_el_nino"].mean()
        raw_mean_la = df_sub[df_sub["source_type"] == "RAW_CMIP6"]["anom_la_nina"].mean()
        qdm_mean_el = df_sub[df_sub["source_type"] == "QDM_CMIP6"]["anom_el_nino"].mean()
        qdm_mean_la = df_sub[df_sub["source_type"] == "QDM_CMIP6"]["anom_la_nina"].mean()

        x = np.arange(2)
        width = 0.25

        obs_vals = [obs_r["anom_el_nino"], obs_r["anom_la_nina"]]
        raw_vals = [raw_mean_el, raw_mean_la]
        qdm_vals = [qdm_mean_el, qdm_mean_la]

        ax.bar(x - width, obs_vals, width, label="Observed", color="#2b5c8f")
        ax.bar(x, raw_vals, width, label="Raw CMIP6 Ensemble", color="#d95f02")
        ax.bar(x + width, qdm_vals, width, label="QDM CMIP6 Ensemble", color="#7570b3")

        ax.axhline(0, color="black", linewidth=0.8, linestyle="--")
        ax.set_xticks(x)
        ax.set_xticklabels(["El Niño Anomaly", "La Niña Anomaly"], fontweight="bold")
        ax.set_title(st_titles[i], fontsize=11, fontweight="bold")
        ax.set_ylabel("Seasonal PRCPTOT Anomaly (mm)")
        ax.grid(True, linestyle=":", alpha=0.5)
        if i == 0: ax.legend(loc="upper left")

    plt.suptitle("Prachuap Khiri Khan Seasonal Precipitation Anomaly Response to ENSO", fontsize=13, fontweight="bold")
    plt.tight_layout()
    fig.savefig(os.path.join(FIGURES_DIR, "Figure2_Seasonal_PRCPTOT_ENSO_Response.png"))
    fig.savefig(os.path.join(FIGURES_DIR, "Figure2_Seasonal_PRCPTOT_ENSO_Response.pdf"))
    plt.close()

    # Figure 3: QDM Bias-Correction Effect on ENSO Precipitation Anomalies per Model
    fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
    df_prcptot_pe = df_pe[df_pe["variable"] == "PRCPTOT"]

    x = np.arange(len(gcm_models))
    width = 0.35

    rainy_pe = df_prcptot_pe[df_prcptot_pe["season_type"] == "RAINY"]["anom_el_qdm"].to_numpy() - df_prcptot_pe[df_prcptot_pe["season_type"] == "RAINY"]["anom_el_raw"].to_numpy()
    hotdry_pe = df_prcptot_pe[df_prcptot_pe["season_type"] == "HOT_DRY"]["anom_el_qdm"].to_numpy() - df_prcptot_pe[df_prcptot_pe["season_type"] == "HOT_DRY"]["anom_el_raw"].to_numpy()

    ax.bar(x - width/2, rainy_pe, width, label="Rainy Season El Niño Shift (QDM - Raw)", color="#1b9e77")
    ax.bar(x + width/2, hotdry_pe, width, label="Hot/Dry Season El Niño Shift (QDM - Raw)", color="#e7298a")

    ax.axhline(0, color="black", linewidth=0.8, linestyle="--")
    ax.set_xticks(x)
    ax.set_xticklabels(gcm_models, rotation=15, fontweight="bold")
    ax.set_ylabel("Absolute Anomaly Shift (mm)")
    ax.set_title("QDM Bias Correction Impact on El Niño Precipitation Anomalies by Model", fontsize=11, fontweight="bold")
    ax.legend()
    ax.grid(True, linestyle=":", alpha=0.5)
    plt.tight_layout()
    fig.savefig(os.path.join(FIGURES_DIR, "Figure3_QDM_Bias_Correction_ENSO_Shift.png"))
    fig.savefig(os.path.join(FIGURES_DIR, "Figure3_QDM_Bias_Correction_ENSO_Shift.pdf"))
    plt.close()

    # 6. TRACEABILITY MATRIX & MANIFEST GENERATION
    print("\n6. Generating Traceability Matrix & Run Manifest...")

    # Input hashes
    input_files = [
        obs_path, coords_path, oni_html_path
    ] + glob.glob(os.path.join(GCM_INPUTS_DIR, "*.csv"))

    input_hashes = {os.path.relpath(f, BASE_DIR): compute_sha256(f) for f in sorted(input_files)}

    traceability_rows = []
    for rel_path, fhash in input_hashes.items():
        if "Observed_Rain" in rel_path:
            target_csv = "observed_seasonal_indices.csv, enso_response_summary.csv"
            module = "compute_seasonal_indices, analyze_enso_responses"
            fig_tab = "Figure 2, Table 2"
        elif "noaa_cpc_oni" in rel_path:
            target_csv = "enso_classification_summary.csv, enso_episode_catalog.csv"
            module = "parse_noaa_oni, classify_seasons"
            fig_tab = "Figure 1, Table 1"
        elif "station_coordinates" in rel_path:
            target_csv = "observed_seasonal_indices.csv"
            module = "main"
            fig_tab = "Metadata"
        else:
            target_csv = "all_source_seasonal_indices.csv, qdm_relative_change_pe_enso.csv"
            module = "analyze_enso_responses, compute_observational_distance_metrics"
            fig_tab = "Figure 2, Figure 3, Table 3"

        traceability_rows.append({
            "source_file": rel_path,
            "sha256_hash": fhash,
            "code_module": module,
            "generated_csv": target_csv,
            "supported_table_figure": fig_tab
        })

    df_traceability = pd.DataFrame(traceability_rows)
    df_traceability.to_csv(os.path.join(BASE_DIR, "PRACHUAP_KHIRI_KHAN_ENSO_TRACEABILITY.csv"), index=False)

    manifest = {
        "project": "CMIP6PrachuapKhiriKhan",
        "task": "ENSO Precipitation Analysis - Numerical Evidence Package",
        "timestamp": pd.Timestamp.now().isoformat(),
        "uttaradit_numerical_dependency": "NONE",
        "input_hashes": input_hashes,
        "stations_count": len(stations),
        "models_count": len(gcm_models),
        "files_generated": [
            "PRACHUAP_KHIRI_KHAN_ENSO_TRACEABILITY.csv",
            "output/tables/enso_classification_summary.csv",
            "output/tables/enso_episode_catalog.csv",
            "output/tables/enso_phase_sample_sizes.csv",
            "output/tables/observed_seasonal_indices.csv",
            "output/tables/all_source_seasonal_indices.csv",
            "output/tables/enso_response_summary.csv",
            "output/tables/enso_asymmetry_summary.csv",
            "output/tables/qdm_relative_change_pe_enso.csv",
            "output/tables/qdm_observational_distance_metrics.csv",
            "output/figures/Figure1_ENSO_Classification_Timeline.png",
            "output/figures/Figure1_ENSO_Classification_Timeline.pdf",
            "output/figures/Figure2_Seasonal_PRCPTOT_ENSO_Response.png",
            "output/figures/Figure2_Seasonal_PRCPTOT_ENSO_Response.pdf",
            "output/figures/Figure3_QDM_Bias_Correction_ENSO_Shift.png",
            "output/figures/Figure3_QDM_Bias_Correction_ENSO_Shift.pdf"
        ]
    }
    with open(os.path.join(MANIFESTS_DIR, "enso_run_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    print("\n=== PRACHUAP KHIRI KHAN ENSO PIPELINE COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    main()
