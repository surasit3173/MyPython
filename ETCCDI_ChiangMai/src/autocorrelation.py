"""
autocorrelation.py — Autocorrelation diagnostics for annual ETCCDI series.

Includes:
1. Theil-Sen slope & robust intercept detrending: residual = y - (slope * x + intercept)
2. Sample ACF lags 1–10
3. Dual-pathway Ljung-Box test (statsmodels vs manual chi2.sf)
4. Audit export: audit/FINAL_LJUNG_BOX_CROSSCHECK.xlsx & output/tables/FINAL_AUTOCORRELATION_TABLE.xlsx
"""

import sys
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (
    OUTPUT_ROOT, AUDIT_DIR, INDICES, ACF_MAX_LAG, ALPHA,
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


def compute_manual_ljung_box(acf_vals: np.ndarray, n: int, lag: int = 5) -> tuple[float, float]:
    """Compute Ljung-Box Q and P statistic using manual formula and chi2.sf."""
    q_val = 0.0
    for k in range(1, lag + 1):
        rk = acf_vals[k - 1]
        q_val += (rk ** 2) / (n - k)
    q_stat = n * (n + 2) * q_val
    p_val = float(stats.chi2.sf(q_stat, df=lag))
    return float(q_stat), p_val


def run_acf_diagnostics(df_etccdi: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    years = df_etccdi["Year"].values
    records = []
    lb_crosscheck_records = []

    for idx in INDICES:
        if idx not in df_etccdi.columns:
            continue
        mask = df_etccdi[idx].notna()
        x = years[mask.values]
        y = df_etccdi.loc[mask, idx].values
        n = len(y)

        if n < 10:
            continue

        # 1. Estimate Theil-Sen slope & robust intercept detrending
        sen_res = stats.theilslopes(y, x, alpha=0.95)
        slope = float(sen_res.slope)
        intercept = float(sen_res.intercept)
        residuals = y - (slope * x + intercept)

        # 2. Compute residual ACF lag 1-10
        acf_vals = compute_sample_acf(residuals, max_lag=10)
        bartlett_bound = round(1.96 / np.sqrt(n), 4)

        # 3. Ljung-Box test Pathway A (statsmodels)
        lb_sm = acorr_ljungbox(residuals, lags=[5], return_df=True)
        q_sm = float(lb_sm["lb_stat"].iloc[0])
        p_sm = float(lb_sm["lb_pvalue"].iloc[0])

        # 4. Ljung-Box test Pathway B (manual formula + scipy.stats.chi2.sf)
        q_man, p_man = compute_manual_ljung_box(acf_vals, n, lag=5)

        diff_q = abs(q_sm - q_man)
        diff_p = abs(p_sm - p_man)
        pass_lb = (diff_q <= 1e-4) and (diff_p <= 1e-4)

        lb_crosscheck_records.append({
            "Index": idx,
            "N": n,
            "Q_statsmodels": round(q_sm, 6),
            "Q_manual": round(q_man, 6),
            "Diff_Q": round(diff_q, 6),
            "P_statsmodels": round(p_sm, 6),
            "P_manual": round(p_man, 6),
            "Diff_P": round(diff_p, 6),
            "PASS_FAIL": "PASS" if pass_lb else "FAIL"
        })

        # 5. Check conditions for serial dependence
        lag1_5_exceed = any(abs(acf_vals[i]) > bartlett_bound for i in range(5))
        lb_reject = p_sm < ALPHA

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
            "LjungBox_Q5": round(q_sm, 4),
            "LjungBox_P5": round(p_sm, 6),
            "LjungBox_P": round(p_sm, 6),
            "Lag1_5_exceed": lag1_5_exceed,
            "LjungBox_reject": lb_reject,
            "Serial_dependence_flag": serial_dependence_flag,
            "Primary_method": primary_method,
        }
        records.append(rec)

    return pd.DataFrame(records), pd.DataFrame(lb_crosscheck_records)


def save_acf_output(df_acf: pd.DataFrame, df_lb_crosscheck: pd.DataFrame) -> None:
    stats_dir = OUTPUT_ROOT / "statistics"
    tables_dir = OUTPUT_ROOT / "tables"
    stats_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    out_stats = stats_dir / "AUTOCORRELATION.xlsx"
    out_table = tables_dir / "TABLE_03_AUTOCORRELATION.xlsx"
    out_final_table = tables_dir / "FINAL_AUTOCORRELATION_TABLE.xlsx"
    out_crosscheck = AUDIT_DIR / "FINAL_LJUNG_BOX_CROSSCHECK.xlsx"

    with pd.ExcelWriter(out_stats, engine="openpyxl") as writer:
        df_acf.to_excel(writer, sheet_name="Autocorrelation", index=False)
    with pd.ExcelWriter(out_table, engine="openpyxl") as writer:
        df_acf.to_excel(writer, sheet_name="Autocorrelation", index=False)
    with pd.ExcelWriter(out_final_table, engine="openpyxl") as writer:
        df_acf.to_excel(writer, sheet_name="Final_Autocorrelation", index=False)
    with pd.ExcelWriter(out_crosscheck, engine="openpyxl") as writer:
        df_lb_crosscheck.to_excel(writer, sheet_name="Ljung_Box_Crosscheck", index=False)

    print(f"[ACF] Autocorrelation diagnostics saved to {out_stats}, {out_final_table}, and {out_crosscheck}")


def run_autocorrelation(df_etccdi: pd.DataFrame) -> pd.DataFrame:
    df_acf, df_lb_crosscheck = run_acf_diagnostics(df_etccdi)
    save_acf_output(df_acf, df_lb_crosscheck)
    return df_acf
