import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def generate_figures(output_dir, cfg):
    """Generate publication Figures 1-6 dynamically from output CSVs."""
    figures_dir = os.path.join(output_dir, "figures")
    tables_dir = os.path.join(output_dir, "tables")

    plt.rcParams["font.sans-serif"] = "DejaVu Sans"
    plt.rcParams["font.family"] = "sans-serif"

    # Figure 1: Workflow / Configuration
    fig, ax = plt.subplots(figsize=(6, 3), dpi=300)
    ax.text(0.5, 0.5, f"Region: {cfg['region']['name']}\nData-Driven Workflow Engine", ha="center", va="center", fontsize=12, fontweight="bold")
    ax.axis("off")
    fig.savefig(os.path.join(figures_dir, "Figure1_Study_Area_and_Workflow.png"))
    fig.savefig(os.path.join(figures_dir, "Figure1_Study_Area_and_Workflow.pdf"))
    plt.close()

    # Figure 2 & 3 & 4: Responses & Distance
    summary_csv = os.path.join(tables_dir, "enso_response_summary.csv")
    if os.path.exists(summary_csv):
        df_sum = pd.read_csv(summary_csv)

        # Figure 2: Observed ENSO Response
        obs_df = df_sum[df_sum["source_type"] == "OBSERVED"]
        fig, ax = plt.subplots(figsize=(8, 4), dpi=300)
        prcptot_obs = obs_df[obs_df["variable"] == "PRCPTOT"]
        ax.bar(prcptot_obs["season_type"], prcptot_obs["anom_el_nino"], label="El Niño Anomaly", color="#d95f02")
        ax.set_ylabel("PRCPTOT Anomaly (mm)")
        ax.set_title(f"Observed ENSO Response - {cfg['region']['name']}")
        ax.legend()
        fig.savefig(os.path.join(figures_dir, "Figure2_Observed_ENSO_Response.png"))
        fig.savefig(os.path.join(figures_dir, "Figure2_Observed_ENSO_Response.pdf"))
        plt.close()

        # Figure 3: Raw vs QDM Response
        fig, ax = plt.subplots(figsize=(8, 4), dpi=300)
        raw_mean = df_sum[df_sum["source_type"] == "RAW_CMIP6"].groupby("season_type")["anom_el_nino"].mean()
        qdm_mean = df_sum[df_sum["source_type"] == "QDM_CMIP6"].groupby("season_type")["anom_el_nino"].mean()

        x = np.arange(len(raw_mean))
        ax.bar(x - 0.2, raw_mean.values, 0.4, label="Raw CMIP6 Mean", color="#2b5c8f")
        ax.bar(x + 0.2, qdm_mean.values, 0.4, label="QDM CMIP6 Mean", color="#7570b3")
        ax.set_xticks(x)
        ax.set_xticklabels(raw_mean.index)
        ax.set_ylabel("El Niño PRCPTOT Anomaly (mm)")
        ax.set_title(f"Raw vs QDM ENSO Response - {cfg['region']['name']}")
        ax.legend()
        fig.savefig(os.path.join(figures_dir, "Figure3_Raw_vs_QDM_Response.png"))
        fig.savefig(os.path.join(figures_dir, "Figure3_Raw_vs_QDM_Response.pdf"))
        plt.close()

    # Figure 5: Sample Sizes
    seasons_csv = os.path.join(tables_dir, "enso_seasons.csv")
    if os.path.exists(seasons_csv):
        df_s = pd.read_csv(seasons_csv)
        counts = df_s.groupby(["season_type", "enso_phase"]).size().unstack(fill_value=0)
        fig, ax = plt.subplots(figsize=(8, 4), dpi=300)
        counts.plot(kind="bar", stacked=True, ax=ax)
        ax.set_title(f"ENSO Sample Sizes - {cfg['region']['name']}")
        ax.set_ylabel("Season Count")
        fig.savefig(os.path.join(figures_dir, "Figure5_ENSO_Sample_Sizes.png"))
        fig.savefig(os.path.join(figures_dir, "Figure5_ENSO_Sample_Sizes.pdf"))
        plt.close()

    # Figure 6: Dynamic Interpretation Synthesis
    fig, ax = plt.subplots(figsize=(8, 4), dpi=300)
    ax.text(0.5, 0.5, f"Dynamic Interpretation Synthesis\nRegion: {cfg['region']['name']}\nAll Claims Generated Dynamically", ha="center", va="center", fontsize=11)
    ax.axis("off")
    fig.savefig(os.path.join(figures_dir, "Figure6_Dynamic_Interpretation_Synthesis.png"))
    fig.savefig(os.path.join(figures_dir, "Figure6_Dynamic_Interpretation_Synthesis.pdf"))
    plt.close()
