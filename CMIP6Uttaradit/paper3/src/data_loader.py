import os
import glob
import pandas as pd

def load_observations(obs_path):
    """Load observed daily rainfall data."""
    if not os.path.exists(obs_path):
        raise FileNotFoundError(f"Observed data file not found: {obs_path}")
    df = pd.read_csv(obs_path)
    stations = [str(c) for c in df.columns if c.upper() not in ["YEAR", "MONTH", "DAY", "DATE"]]
    df["date"] = pd.to_datetime(df[["YEAR", "MONTH", "DAY"]])
    return df, stations

def load_gcm_model(gcm_dir, model_name, suffix="19810101-20141231"):
    """Load Raw and QDM historical GCM daily rainfall data recursively."""
    all_csvs = glob.glob(os.path.join(gcm_dir, "**", "*.csv"), recursive=True) + glob.glob(os.path.join(gcm_dir, "*.csv"))

    # Restrict to historical period
    hist_csvs = [f for f in all_csvs if "historical" in os.path.basename(f) or "19810101-20141231" in os.path.basename(f)]

    raw_files = [f for f in hist_csvs if model_name in f and not os.path.basename(f).startswith("bc_")]
    bc_files = [f for f in hist_csvs if model_name in f and os.path.basename(f).startswith("bc_")]

    if not raw_files or not bc_files:
        raise FileNotFoundError(f"Could not locate historical Raw and QDM files for model {model_name} in {gcm_dir}")

    df_raw = pd.read_csv(raw_files[0])
    df_bc = pd.read_csv(bc_files[0])
    return df_raw, df_bc
