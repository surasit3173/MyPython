"""
trend.py — Monotonic trend analysis for annual ETCCDI series.

Includes:
  - Ordinary Mann–Kendall (MK)
  - Hamed–Rao Modified Mann–Kendall (for autocorrelated series)
  - Theil–Sen estimator slope & 95% CI
  - Kendall's Tau
  - Benjamini–Hochberg False Discovery Rate (BH-FDR)
  - Zero-slope handling: |Sen_slope| <= 1e-6 classified as "No detectable trend"
"""

import sys
import numpy as np
import pandas as pd
from scipy import stats
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (
    OUTPUT_ROOT, INDICES, UNITS, ALPHA, SEN_CI,
    FDR_ALPHA, MK_METHOD_AC,
)

try:
    import pymannkendall as mk
    HAS_PYMANNKENDALL = True
except ImportError:
    HAS_PYMANNKENDALL = False


def _sens_slope_ci(x: np.ndarray, y: np.ndarray, alpha: float = 0.05) -> tuple[float, float, float, float]:
    """
    Compute Theil–Sen slope, intercept, and 95% confidence interval using scipy.stats.theilslopes.
    """
    res = stats.theilslopes(y, x, alpha=1 - alpha)
    slope = float(res.slope)
    intercept = float(res.intercept)
    ci_low = float(res.low_slope)
    ci_high = float(res.high_slope)
    return slope, intercept, ci_low, ci_high


def _bh_fdr_correct(p_values: list[float], alpha: float = FDR_ALPHA) -> list[float]:
    """
    Apply Benjamini–Hochberg False Discovery Rate (FDR) procedure.
    """
    p = np.array(p_values, dtype=float)
    n = len(p)
    if n == 0:
        return []

    sorted_indices = np.argsort(p)
    sorted_p = p[sorted_indices]

    adjusted = np.zeros(n)
    cummin_input = sorted_p * n / np.arange(1, n + 1)
    adjusted_sorted = np.minimum.accumulate(cummin_input[::-1])[::-1]
    adjusted_sorted = np.clip(adjusted_sorted, 0.0, 1.0)

    adjusted[sorted_indices] = adjusted_sorted
    return list(adjusted)


def run_trend_analysis(df_etccdi: pd.DataFrame, df_acf: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Run complete trend analysis across 11 indices.
    """
    years = df_etccdi["Year"].values

    # Map serial dependence flag from ACF diagnostics
    acf_map = dict(zip(df_acf["Index"], df_acf["Serial_dependence_flag"]))

    records = []
    p_raw_all = []

    for idx in INDICES:
        if idx not in df_etccdi.columns:
            continue
        mask = df_etccdi[idx].notna()
        x = years[mask.values]
        y = df_etccdi.loc[mask, idx].values
        n = len(y)

        if n < 10:
            continue

        is_autocorrelated = acf_map.get(idx, False)

        # 1. Primary MK test selection based on pre-specified rule
        if is_autocorrelated and HAS_PYMANNKENDALL:
            mk_res = mk.hamed_rao_modification_test(y)
            primary_method = "Hamed_Rao_modified_MK"
        elif HAS_PYMANNKENDALL:
            mk_res = mk.original_test(y)
            primary_method = "Ordinary_MK"
        else:
            # Fallback
            tau_val, p_val = stats.kendalltau(x, y)
            primary_method = "Ordinary_MK_scipy"
            mk_res = None

        if mk_res is not None:
            tau = float(mk_res.Tau)
            p_raw = float(mk_res.p)
        else:
            tau = float(tau_val)
            p_raw = float(p_val)

        # 2. Sen's slope & 95% CI
        slope, intercept, ci_low, ci_high = _sens_slope_ci(x, y, alpha=ALPHA)

        # 3. Classify direction & raw significance
        TOL = 1e-6
        if abs(slope) <= TOL:
            direction = "No detectable trend"
        elif slope > 0:
            direction = "Increasing"
        else:
            direction = "Decreasing"

        sig_raw = p_raw < ALPHA

        p_raw_all.append(p_raw)

        records.append({
            "Index": idx,
            "Unit": UNITS.get(idx, ""),
            "N": n,
            "Kendall_tau": round(tau, 4),
            "Sen_slope_year": round(slope, 4),
            "Sen_slope_decade": round(slope * 10, 4),
            "CI95_low": round(ci_low, 4),
            "CI95_high": round(ci_high, 4),
            "Primary_test": primary_method,
            "P_raw": round(p_raw, 6),
            "Direction": direction,
            "Sig_raw": sig_raw,
        })

    # Apply BH-FDR to 11 primary test p-values
    p_fdr_list = _bh_fdr_correct(p_raw_all, alpha=FDR_ALPHA)

    for i, rec in enumerate(records):
        p_fdr = p_fdr_list[i]
        rec["P_FDR"] = round(p_fdr, 6)
        sig_fdr = p_fdr < FDR_ALPHA
        rec["Significance"] = "Significant (p_FDR < 0.05)" if sig_fdr else "Non-significant"

    df_trend = pd.DataFrame(records)

    # Columns per Master Spec Section 20
    cols = [
        "Index", "Unit", "N", "Kendall_tau", "Sen_slope_year",
        "Sen_slope_decade", "CI95_low", "CI95_high", "Primary_test",
        "P_raw", "P_FDR", "Direction", "Significance"
    ]
    df_trend = df_trend[cols]

    # FDR summary table
    df_fdr = df_trend[["Index", "Unit", "N", "P_raw", "P_FDR", "Significance"]].copy()

    return df_trend, df_fdr


def save_trend_outputs(df_trend: pd.DataFrame, df_fdr: pd.DataFrame) -> None:
    stats_dir = OUTPUT_ROOT / "statistics"
    tables_dir = OUTPUT_ROOT / "tables"
    stats_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    out_stats = stats_dir / "FINAL_TREND_STATISTICS.xlsx"
    out_table = tables_dir / "TABLE_04_TREND_FINAL.xlsx"
    out_final_table = tables_dir / "FINAL_TREND_TABLE.xlsx"
    out_fdr = stats_dir / "FDR_ANALYSIS.xlsx"

    with pd.ExcelWriter(out_stats, engine="openpyxl") as writer:
        df_trend.to_excel(writer, sheet_name="Final_Trend_Statistics", index=False)
    with pd.ExcelWriter(out_table, engine="openpyxl") as writer:
        df_trend.to_excel(writer, sheet_name="Final_Trend_Analysis", index=False)
    with pd.ExcelWriter(out_fdr, engine="openpyxl") as writer:
        df_fdr.to_excel(writer, sheet_name="FDR_Analysis", index=False)
    with pd.ExcelWriter(out_final_table, engine="openpyxl") as writer:
        df_trend.to_excel(writer, sheet_name="Final_Trend_Table", index=False)

    print(f"[TREND] Trend analysis saved to {out_stats}, {out_table}, and {out_fdr}")


def run_trend(df_etccdi: pd.DataFrame, df_acf: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df_trend, df_fdr = run_trend_analysis(df_etccdi, df_acf)
    save_trend_outputs(df_trend, df_fdr)
    return df_trend, df_fdr
