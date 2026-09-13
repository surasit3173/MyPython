#!/usr/bin/env python3
import os
import sys
import argparse
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_loader import load_config
from data_loader import load_observations, load_gcm_model
from enso_classifier import parse_noaa_oni, classify_management_seasons
from precipitation_indices import compute_seasonal_indices
from statistics import analyze_enso_responses, compute_observational_distance_metrics
from table_generator import generate_tables
from figure_generator import generate_figures
from report_generator import generate_reports

def main():
    parser = argparse.ArgumentParser(description="Result-Agnostic Reusable ENSO Analysis Pipeline")
    parser.add_argument("--config", required=True, help="Path to YAML configuration file")
    args = parser.parse_args()

    cfg = load_config(args.config)
    output_dir = cfg["output"]["dir"]
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "tables"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "figures"), exist_ok=True)

    print(f"=== RUNNING ENSO PIPELINE FOR REGION: {cfg['region']['name']} ===")

    # 1. Load Observations
    obs_df, stations = load_observations(cfg["observations"]["path"])

    # 2. ENSO Classification
    df_oni = parse_noaa_oni(
        cfg["enso"]["source_path"],
        threshold_c=cfg["enso"]["threshold_c"],
        persistence_windows=cfg["enso"]["persistence_windows"]
    )
    df_seasons = classify_management_seasons(
        df_oni,
        date_start=cfg["observations"]["date_start"],
        date_end=cfg["observations"]["date_end"]
    )
    df_seasons.to_csv(os.path.join(output_dir, "tables", "enso_seasons.csv"), index=False)

    # 3. Compute Observed Indices
    df_obs_ind = compute_seasonal_indices(obs_df, df_seasons, stations)
    df_obs_ind["season_type"] = df_obs_ind["season_type"] if "season_type" in df_obs_ind else df_obs_ind.index
    obs_sum = analyze_enso_responses(
        df_obs_ind, "OBSERVED", "OBSERVED",
        min_n_inference=cfg["statistics"]["minimum_n_for_inference"]
    )

    all_summaries = [obs_sum]
    gcm_models = cfg["gcm_data"]["models"]

    for model in gcm_models:
        df_raw, df_bc = load_gcm_model(
            cfg["gcm_data"]["dir"], model, suffix=cfg["gcm_data"]["suffix"]
        )

        df_raw_ind = compute_seasonal_indices(df_raw, df_seasons, stations)
        raw_sum = analyze_enso_responses(
            df_raw_ind, "RAW_CMIP6", model,
            min_n_inference=cfg["statistics"]["minimum_n_for_inference"]
        )
        all_summaries.append(raw_sum)

        df_bc_ind = compute_seasonal_indices(df_bc, df_seasons, stations)
        bc_sum = analyze_enso_responses(
            df_bc_ind, "QDM_CMIP6", model,
            min_n_inference=cfg["statistics"]["minimum_n_for_inference"]
        )
        all_summaries.append(bc_sum)

    df_all_sum = pd.concat(all_summaries, ignore_index=True)
    df_all_sum.to_csv(os.path.join(output_dir, "tables", "enso_response_summary.csv"), index=False)

    df_dist = compute_observational_distance_metrics(df_all_sum, gcm_models)
    df_dist.to_csv(os.path.join(output_dir, "tables", "observational_distance.csv"), index=False)

    # 4. Generate Tables, Figures, and Reports
    generate_tables(output_dir, cfg)
    generate_figures(output_dir, cfg)
    generate_reports(output_dir, cfg)

    print(f"=== ENSO PIPELINE COMPLETED FOR REGION: {cfg['region']['name']} ===")

if __name__ == "__main__":
    main()
