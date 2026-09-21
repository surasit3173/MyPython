"""
autocorrelation.py — Autocorrelation diagnostics for annual ETCCDI series.

For each of the 11 annual series, computes:
  - ACF at lags 1–10 (Pearson / statsmodels)
  - Significance bounds: ±2/sqrt(N)
  - Flag: significant_lag1 (primary criterion for MK method selection)

Saves:
  - output/statistics/autocorrelation_analysis.xlsx
"""
import sys
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (
    OUTPUT_ROOT, INDICES, ACF_MAX_LAG, ACF_SIG_FACTOR,
)


def compute_acf(series: np.ndarray, max_lag: int = ACF_MAX_LAG) -> np.ndarray:
    """
    Compute Pearson autocorrelation at lags 1..max_lag.

    Uses the biased estimator (divide by N, not N-k), which is standard
    for the Bartlett confidence interval.

    Returns:
        np.ndarray of shape (max_lag,), ACF[0] = lag-1, ACF[9] = lag-10
    """
    n = len(series)
    mean = np.mean(series)
    var  = np.sum((series - mean) ** 2) / n  # biased variance

    if var == 0:
        return np.zeros(max_lag)

    acf_vals = []
    for k in range(1, max_lag + 1):
        cov = np.sum((series[:n - k] - mean) * (series[k:] - mean)) / n
        acf_vals.append(cov / var)
    return np.array(acf_vals)


def run_acf_diagnostics(df_etccdi: pd.DataFrame) -> pd.DataFrame:
    """
    Compute ACF diagnostics for all 11 ETCCDI indices.

    Returns DataFrame with columns:
      Index, N, ACF_lag1..ACF_lag10, sig_bound_95, sig_lag1,
      sig_lag2, any_sig_lag1_to_5
    """
    records = []
    for idx in INDICES:
        if idx not in df_etccdi.columns:
            continue
        series = df_etccdi[idx].dropna().values
        n      = len(series)
        if n < 10:
            print(f"[ACF] {idx}: Insufficient data (N={n}). Skipping.")
            continue

        # Demean before ACF
        acf_vals = compute_acf(series, ACF_MAX_LAG)
        sig_bound = ACF_SIG_FACTOR / np.sqrt(n)

        rec = {
            "Index":     idx,
            "N":         n,
            "sig_bound": round(sig_bound, 4),
        }
        any_sig = False
        for lag_i, acf_val in enumerate(acf_vals, start=1):
            rec[f"ACF_lag{lag_i}"] = round(float(acf_val), 4)
            is_sig = abs(acf_val) > sig_bound
            rec[f"sig_lag{lag_i}"] = is_sig
            if lag_i <= 5 and is_sig:
                any_sig = True

        rec["sig_lag1_primary"] = bool(abs(acf_vals[0]) > sig_bound)
        rec["any_sig_lag1_to_5"] = any_sig
        records.append(rec)

    df_acf = pd.DataFrame(records)
    return df_acf


def save_acf_output(df_acf: pd.DataFrame) -> None:
    """Save autocorrelation_analysis.xlsx."""
    stats_dir = OUTPUT_ROOT / "statistics"
    stats_dir.mkdir(parents=True, exist_ok=True)
    out_path = stats_dir / "autocorrelation_analysis.xlsx"
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df_acf.to_excel(writer, sheet_name="ACF_Diagnostics", index=False)
    print(f"[ACF] autocorrelation_analysis.xlsx saved to {out_path}")


def run_autocorrelation(df_etccdi: pd.DataFrame) -> pd.DataFrame:
    """Main entry point. Returns ACF diagnostics DataFrame."""
    df_acf = run_acf_diagnostics(df_etccdi)
    save_acf_output(df_acf)
    return df_acf
