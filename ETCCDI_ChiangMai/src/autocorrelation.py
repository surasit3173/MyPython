"""
autocorrelation.py — Autocorrelation diagnostics for annual ETCCDI series.

Process per Master Specification Section 15:
1. Estimate Theil-Sen slope
2. Remove the monotonic trend (residuals = y - slope * x - intercept)
3. Compute residual series
4. Calculate ACF lag 1–10
5. Compute Bartlett bound (±1.96 / sqrt(N))
6. Conduct Ljung-Box portmanteau test for lags 1–5

Decision Rule:
Flag serial dependence if:
- any of lags 1–5 exceeds the Bartlett bound
OR
- Ljung-Box rejects independence at alpha = 0.05
"""

import sys
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (
    OUTPUT_ROOT, INDICES, ACF_MAX_LAG, ALPHA,
)


def compute_sample_acf(residuals: np.ndarray, max_lag: int = 10) -> np.ndarray:
    n = len(residuals)
    mean = np.mean(residuals)
    var = np.sum((residuals - mean) ** 2) / n
    if var == 0:
        return np.zeros(max_lag)

    acf_vals = []
    for k in range(1, max_lag + 1):
        cov = np.sum((residuals[:n - k] - mean) * (residuals[k:] - mean)) / n
        acf_vals.append(cov / var)
    return np.array(acf_vals)


def run_acf_diagnostics(df_etccdi: pd.DataFrame) -> pd.DataFrame:
    years = df_etccdi["Year"].values
    records = []

    for idx in INDICES:
        if idx not in df_etccdi.columns:
            continue
        mask = df_etccdi[idx].notna()
        x = years[mask.values]
        y = df_etccdi.loc[mask, idx].values
        n = len(y)

        if n < 10:
            continue

        # 1. Estimate Theil-Sen slope & remove trend
        sen_res = stats.theilslopes(y, x, alpha=0.95)
        slope = float(sen_res.slope)
        intercept = float(sen_res.intercept)
        residuals = y - (slope * x + intercept)

        # 2. Compute residual ACF lag 1-10
        acf_vals = compute_sample_acf(residuals, max_lag=10)
        bartlett_bound = round(1.96 / np.sqrt(n), 4)

        # 3. Ljung-Box test for lags 1-5 on residuals
        lb_res = acorr_ljungbox(residuals, lags=[5], return_df=True)
        lb_pvalue = round(float(lb_res["lb_pvalue"].iloc[0]), 6)

        # 4. Check conditions
        lag1_5_exceed = any(abs(acf_vals[i]) > bartlett_bound for i in range(5))
        lb_reject = lb_pvalue < ALPHA

        serial_dependence_flag = lag1_5_exceed or lb_reject
        primary_method = "Hamed_Rao_modified_MK" if serial_dependence_flag else "Ordinary_MK"

        rec = {
            "Index": idx,
            "N": n,
            "Theil_Sen_slope": round(slope, 4),
            "ACF1": round(float(acf_vals[0]), 4),
            "ACF2": round(float(acf_vals[1]), 4),
            "ACF3": round(float(acf_vals[2]), 4),
            "ACF4": round(float(acf_vals[3]), 4),
            "ACF5": round(float(acf_vals[4]), 4),
            "ACF6": round(float(acf_vals[5]), 4),
            "ACF7": round(float(acf_vals[6]), 4),
            "ACF8": round(float(acf_vals[7]), 4),
            "ACF9": round(float(acf_vals[8]), 4),
            "ACF10": round(float(acf_vals[9]), 4),
            "Bartlett_bound": bartlett_bound,
            "LjungBox_P": lb_pvalue,
            "Lag1_5_exceed": lag1_5_exceed,
            "LjungBox_reject": lb_reject,
            "Serial_dependence_flag": serial_dependence_flag,
            "Primary_method": primary_method,
        }
        records.append(rec)

    return pd.DataFrame(records)


def save_acf_output(df_acf: pd.DataFrame) -> None:
    stats_dir = OUTPUT_ROOT / "statistics"
    tables_dir = OUTPUT_ROOT / "tables"
    stats_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    out_stats = stats_dir / "AUTOCORRELATION.xlsx"
    out_table = tables_dir / "TABLE_03_AUTOCORRELATION.xlsx"

    with pd.ExcelWriter(out_stats, engine="openpyxl") as writer:
        df_acf.to_excel(writer, sheet_name="Autocorrelation", index=False)
    with pd.ExcelWriter(out_table, engine="openpyxl") as writer:
        df_acf.to_excel(writer, sheet_name="Autocorrelation", index=False)

    print(f"[ACF] Autocorrelation diagnostics saved to {out_stats} and {out_table}")


def run_autocorrelation(df_etccdi: pd.DataFrame) -> pd.DataFrame:
    df_acf = run_acf_diagnostics(df_etccdi)
    save_acf_output(df_acf)
    return df_acf
