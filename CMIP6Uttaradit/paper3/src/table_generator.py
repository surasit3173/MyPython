import os
import pandas as pd

def generate_tables(output_dir, cfg):
    """Generate publication Tables 1-6 dynamically from output CSVs."""
    tables_dir = os.path.join(output_dir, "tables")

    # Table 1: Data and analytical configuration
    t1_data = [
        {"Parameter": "Region Name", "Value": cfg["region"]["name"]},
        {"Parameter": "Country", "Value": cfg["region"]["country"]},
        {"Parameter": "Observation Period", "Value": f"{cfg['observations']['date_start']}-{cfg['observations']['date_end']}"},
        {"Parameter": "GCM Count", "Value": len(cfg["gcm_data"]["models"])},
        {"Parameter": "ENSO Index Source", "Value": "NOAA CPC ERSSTv6 ONI"},
        {"Parameter": "ENSO Threshold", "Value": f"|ONI| >= {cfg['enso']['threshold_c']}°C for >= {cfg['enso']['persistence_windows']} windows"}
    ]
    pd.DataFrame(t1_data).to_csv(os.path.join(tables_dir, "Table_01_Data_and_Analytical_Configuration.csv"), index=False)

    # Table 2: ENSO classification & sample sizes
    seasons_csv = os.path.join(tables_dir, "enso_seasons.csv")
    if os.path.exists(seasons_csv):
        df_s = pd.read_csv(seasons_csv)
        t2 = df_s.groupby(["season_type", "enso_phase"]).size().reset_index(name="sample_size")
        t2.to_csv(os.path.join(tables_dir, "Table_02_ENSO_Classification_Sample_Sizes.csv"), index=False)

    # Table 3 & 4: Observed vs Raw vs QDM responses
    summary_csv = os.path.join(tables_dir, "enso_response_summary.csv")
    if os.path.exists(summary_csv):
        df_sum = pd.read_csv(summary_csv)
        df_sum.to_csv(os.path.join(tables_dir, "Table_03_Observed_ENSO_Responses.csv"), index=False)
        df_sum.to_csv(os.path.join(tables_dir, "Table_04_Raw_vs_QDM_Responses.csv"), index=False)

    # Table 5: Observational Distance Diagnostics
    dist_csv = os.path.join(tables_dir, "observational_distance.csv")
    if os.path.exists(dist_csv):
        df_dist = pd.read_csv(dist_csv)
        df_dist.to_csv(os.path.join(tables_dir, "Table_05_Observational_Distance_Diagnostics.csv"), index=False)

    # Table 6: Uncertainty & Interpretation
    if os.path.exists(summary_csv):
        df_sum = pd.read_csv(summary_csv)
        t6 = df_sum[["season_type", "variable", "model", "p_val_el_vs_la", "diagnostic_only"]].copy()
        t6.to_csv(os.path.join(tables_dir, "Table_06_Uncertainty_and_Interpretation.csv"), index=False)
