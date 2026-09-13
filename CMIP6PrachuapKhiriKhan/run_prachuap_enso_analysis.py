#!/usr/bin/env python3
"""
Complete ENSO-Precipitation Analysis Pipeline for Prachuap Khiri Khan Province
Independent Numerical Analysis Package (NO Uttaradit Numerical Dependency)
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
import seaborn as sns

# Ensure output directories exist
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
TABLES_DIR = os.path.join(OUTPUT_DIR, "tables")
FIGURES_DIR = os.path.join(OUTPUT_DIR, "figures")
MANIFESTS_DIR = os.path.join(OUTPUT_DIR, "manifests")
LOGS_DIR = os.path.join(OUTPUT_DIR, "logs")

for d in [OUTPUT_DIR, TABLES_DIR, FIGURES_DIR, MANIFESTS_DIR, LOGS_DIR]:
    os.makedirs(d, exist_ok=True)

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
                continue # Incomplete season (ends April 2015, obs end Dec 2014)

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
    # Ensure date index
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

            # PRCPTOT: Total seasonal precipitation
            prcptot = np.sum(vals)

            # Rx1day: Maximum 1-day precipitation
            rx1day = np.max(vals) if len(vals) > 0 else 0.0

            # Rx5day: Maximum 5-day consecutive precipitation sum
            if len(vals) >= 5:
                rx5day = np.max(pd.Series(vals).rolling(5).sum().dropna().to_numpy())
            else:
                rx5day = rx1day

            # Wet days (>= 1.0 mm)
            wet_vals = vals[vals >= 1.0]
            sdii = np.mean(wet_vals) if len(wet_vals) > 0 else 0.0

            # R95p & R99p: Precipitation from days exceeding 95th / 99th percentile
            p95_val = p95_dict[sta]
            p99_val = p99_dict[sta]
            r95p = np.sum(vals[vals > p95_val])
            r99p = np.sum(vals[vals > p99_val])

            # CWD (Max consecutive wet days >= 1.0 mm)
            # CDD (Max consecutive dry days < 1.0 mm)
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
# 3. STATISTICAL INFERENCE & ANOMALY CALCULATIONS
# ------------------------------------------------------------------------------

def analyze_enso_responses(df_indices, source_type, model_name="OBSERVED"):
    """Compute phase averages, anomalies, percentage changes, asymmetry, and statistical tests."""
    indices = ["PRCPTOT", "Rx1day", "Rx5day", "SDII", "R95p", "R99p", "CWD", "CDD"]

    summary_rows = []
    asym_rows = []

    for stype in ["RAINY", "HOT_DRY"]:
        sub_s = df_indices[df_indices["season_type"] == stype]

        # Mean across stations for each climate year and phase to evaluate regional/domain response
        # Also compute per-station metrics
        phases = ["EL_NINO", "LA_NINA", "NEUTRAL", "TRANSITION_UNCLASSIFIED"]

        for idx in indices:
            # Regional (station-averaged) series per season
            regional_by_year = sub_s.groupby(["climate_year", "enso_phase"])[idx].mean().reset_index()

            el_data = regional_by_year[regional_by_year["enso_phase"] == "EL_NINO"][idx].to_numpy()
            la_data = regional_by_year[regional_by_year["enso_phase"] == "LA_NINA"][idx].to_numpy()
            neu_data = regional_by_year[regional_by_year["enso_phase"] == "NEUTRAL"][idx].to_numpy()

            n_el, n_la, n_neu = len(el_data), len(la_data), len(neu_data)

            mean_el = np.mean(el_data) if n_el > 0 else np.nan
            mean_la = np.mean(la_data) if n_la > 0 else np.nan
            mean_neu = np.mean(neu_data) if n_neu > 0 else np.nan

            # Anomalies relative to Neutral climatology
            anom_el = mean_el - mean_neu if pd.notna(mean_el) and pd.notna(mean_neu) else np.nan
            anom_la = mean_la - mean_neu if pd.notna(mean_la) and pd.notna(mean_neu) else np.nan

            pct_el = (anom_el / mean_neu * 100.0) if pd.notna(anom_el) and mean_neu != 0 else np.nan
            pct_la = (anom_la / mean_neu * 100.0) if pd.notna(anom_la) and mean_neu != 0 else np.nan

            # Statistical tests (El Nino vs Neutral, La Nina vs Neutral, El Nino vs La Nina)
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

            # Asymmetry quantification: Absolute Asymmetry = |Anom_EL + Anom_LA|, Relative = (Anom_EL + Anom_LA) / mean_neu
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

# ------------------------------------------------------------------------------
# 4. MAIN EXECUTION PIPELINE
# ------------------------------------------------------------------------------

def main():
    print("=== STARTING PRACHUAP KHIRI KHAN ENSO ANALYSIS PIPELINE ===")

    # Path setup
    obs_path = os.path.join(BASE_DIR, "data", "Observed_Rain_daily_198101_201412_PrachuapKhiriKhan.csv")
    coords_path = os.path.join(BASE_DIR, "data", "station_coordinates_PrachuapKhiriKhan.csv")
    oni_html_path = os.path.join(os.path.dirname(BASE_DIR), "AAA_cmip6_analysis_taylor diagram_dailyMonthly", "paper3_execution", "inputs", "enso", "noaa_cpc_oni_ersstv6_2026-09-01.html")
    gcm_dir = os.path.join(os.path.dirname(BASE_DIR), "AAA_cmip6_analysis_taylor diagram_dailyMonthly")

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

    # Save ENSO sample sizes summary
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
        # Find raw & bc files
        raw_pattern = os.path.join(gcm_dir, f"pr_day_{model}_*_Prachuap Khiri Khan.csv")
        bc_pattern = os.path.join(gcm_dir, f"bc_pr_day_{model}_*_Prachuap Khiri Khan.csv")

        raw_files = glob.glob(raw_pattern)
        bc_files = glob.glob(bc_pattern)

        if not raw_files or not bc_files:
            print(f"  WARNING: Missing files for GCM {model}, skipping...")
            continue

        # Process RAW
        df_raw = pd.read_csv(raw_files[0])
        df_raw_ind = compute_seasonal_indices(df_raw, df_seasons, stations, p95_dict, p99_dict)
        df_raw_ind["source_type"] = "RAW_CMIP6"
        df_raw_ind["model"] = model
        all_indices_list.append(df_raw_ind)

        raw_sum, raw_as = analyze_enso_responses(df_raw_ind, "RAW_CMIP6", model)
        all_summaries.append(raw_sum)
        all_asym.append(raw_as)

        # Process QDM
        df_bc = pd.read_csv(bc_files[0])
        df_bc_ind = compute_seasonal_indices(df_bc, df_seasons, stations, p95_dict, p99_dict)
        df_bc_ind["source_type"] = "QDM_CMIP6"
        df_bc_ind["model"] = model
        all_indices_list.append(df_bc_ind)

        bc_sum, bc_as = analyze_enso_responses(df_bc_ind, "QDM_CMIP6", model)
        all_summaries.append(bc_sum)
        all_asym.append(bc_as)

        print(f"  Completed GCM: {model}")

    # Combine all summaries
    df_all_summaries = pd.concat(all_summaries, ignore_index=True)
    df_all_asym = pd.concat(all_asym, ignore_index=True)
    df_all_indices = pd.concat(all_indices_list, ignore_index=True)

    df_all_summaries.to_csv(os.path.join(TABLES_DIR, "enso_response_summary.csv"), index=False)
    df_all_asym.to_csv(os.path.join(TABLES_DIR, "enso_asymmetry_summary.csv"), index=False)
    df_all_indices.to_csv(os.path.join(TABLES_DIR, "all_source_seasonal_indices.csv"), index=False)

    # 4. QDM Relative Change / Preservation Metric (PE_ENSO)
    print("\n4. Calculating QDM Relative Change Metric (PE_ENSO = 100 * (QDM - Raw) / Raw)...")
    pe_rows = []
    for model in gcm_models:
        raw_m = df_all_summaries[(df_all_summaries["source_type"] == "RAW_CMIP6") & (df_all_summaries["model"] == model)]
        qdm_m = df_all_summaries[(df_all_summaries["source_type"] == "QDM_CMIP6") & (df_all_summaries["model"] == model)]

        merged = pd.merge(raw_m, qdm_m, on=["season_type", "variable"], suffixes=("_RAW", "_QDM"))
        for _, r in merged.iterrows():
            stype = r["season_type"]
            var = r["variable"]

            # Anomaly relative change
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

    # Highlight persistent episode periods
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

        # Filter for OBSERVED, Ensemble Raw, Ensemble QDM
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

    # 6. RUN MANIFEST & VERIFICATION REPORT
    print("\n6. Generating Run Manifest & Provenance Record...")
    manifest = {
        "project": "CMIP6PrachuapKhiriKhan",
        "task": "ENSO Precipitation Analysis - Numerical Evidence Package",
        "analysis_period": [1981, 2014],
        "stations_count": len(stations),
        "stations_list": stations,
        "models_count": len(gcm_models),
        "models_list": gcm_models,
        "enso_source": "NOAA CPC ONI ERSSTv6",
        "uttaradit_numerical_dependency": "NONE",
        "files_generated": [
            "output/tables/enso_classification_summary.csv",
            "output/tables/enso_episode_catalog.csv",
            "output/tables/enso_phase_sample_sizes.csv",
            "output/tables/observed_seasonal_indices.csv",
            "output/tables/all_source_seasonal_indices.csv",
            "output/tables/enso_response_summary.csv",
            "output/tables/enso_asymmetry_summary.csv",
            "output/tables/qdm_relative_change_pe_enso.csv",
            "output/figures/Figure1_ENSO_Classification_Timeline.png",
            "output/figures/Figure2_Seasonal_PRCPTOT_ENSO_Response.png",
            "output/figures/Figure3_QDM_Bias_Correction_ENSO_Shift.png"
        ]
    }
    with open(os.path.join(MANIFESTS_DIR, "enso_run_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    print("\n=== PRACHUAP KHIRI KHAN ENSO PIPELINE COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    main()
