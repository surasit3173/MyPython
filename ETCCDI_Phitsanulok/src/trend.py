"""
trend.py — Mann–Kendall trend analysis, Sen's slope, and FDR correction.

Method selection rule (conservative, not outcome-driven):
  - If ACF lag-1 significant (|r1| > 2/sqrt(N)): use Hamed & Rao modified MK
  - Otherwise: use ordinary Mann–Kendall

Sen's slope = Theil-Sen estimator with 95% CI.
FDR correction: Benjamini–Hochberg on all 11 raw p-values.

Outputs:
  - output/statistics/trend_analysis.xlsx
  - output/tables/TABLE_05_TREND_ANALYSIS.xlsx
  - output/tables/TABLE_06_FDR_ANALYSIS.xlsx
"""
import sys
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (
    OUTPUT_ROOT, INDICES, UNITS, ALPHA, SEN_CI, MK_METHOD_AC
)


# ─── Import pymannkendall ─────────────────────────────────────────────────────
try:
    import pymannkendall as mk
    HAS_PYMANNKENDALL = True
except ImportError:
    HAS_PYMANNKENDALL = False
    warnings.warn(
        "pymannkendall not installed. Falling back to scipy.stats-based MK. "
        "Install via: pip install pymannkendall"
    )


# ─── Fallback MK (if pymannkendall unavailable) ───────────────────────────────

def _mk_ordinary_fallback(series: np.ndarray) -> dict:
    """Pure-numpy ordinary Mann–Kendall (two-tailed)."""
    n = len(series)
    s = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            diff = series[j] - series[i]
            if diff > 0:
                s += 1
            elif diff < 0:
                s -= 1

    # Variance with tie correction
    unique, counts = np.unique(series, return_counts=True)
    tie_sum = sum(c * (c - 1) * (2 * c + 5) for c in counts if c > 1)
    var_s = (n * (n - 1) * (2 * n + 5) - tie_sum) / 18.0

    if var_s == 0:
        return {"tau": 0.0, "p": 1.0, "trend": "no trend", "s": s}

    if s > 0:
        z = (s - 1) / np.sqrt(var_s)
    elif s < 0:
        z = (s + 1) / np.sqrt(var_s)
    else:
        z = 0.0

    p = 2 * (1 - stats.norm.cdf(abs(z)))
    tau = s / (0.5 * n * (n - 1))  # Kendall tau

    trend = "no trend"
    if p < ALPHA:
        trend = "increasing trend" if s > 0 else "decreasing trend"

    return {"tau": tau, "p": p, "trend": trend, "s": s, "z": z}


# ─── Sen's Slope ──────────────────────────────────────────────────────────────

def _sens_slope_ci(x: np.ndarray, y: np.ndarray, ci: float = SEN_CI) -> tuple:
    """
    Compute Sen's slope and confidence interval using scipy.stats.theilslopes.

    Returns: (slope, intercept, ci_low, ci_high)
    """
    result = stats.theilslopes(y, x, alpha=1 - ci)
    slope     = float(result.slope)
    intercept = float(result.intercept)
    ci_low    = float(result.low_slope)
    ci_high   = float(result.high_slope)
    return slope, intercept, ci_low, ci_high


# ─── FDR Correction ───────────────────────────────────────────────────────────

def _bh_fdr(p_values: list, alpha: float = ALPHA) -> list:
    """
    Benjamini–Hochberg FDR correction.

    Returns list of adjusted p-values in the same order as input.
    """
    n = len(p_values)
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    adjusted = [None] * n
    min_p_adj = 1.0
    for rank, (orig_i, p) in enumerate(reversed(indexed), start=1):
        rank_from_bottom = n - rank + 1  # 1-indexed rank from top (largest p first reversed)
        rank_from_top    = n - (rank - 1)  # simpler: rank from top
        p_adj = min(1.0, p * n / (n - rank + 1))
        min_p_adj = min(min_p_adj, p_adj)
        adjusted[orig_i] = min_p_adj

    return adjusted


def _bh_fdr_correct(p_values: list) -> list:
    """Standard BH FDR via scipy.stats.false_discovery_control (scipy >= 1.10)
    or manual implementation."""
    try:
        from scipy.stats import false_discovery_control
        adj = false_discovery_control(p_values, method="bh")
        return [float(a) for a in adj]
    except (ImportError, AttributeError):
        # Fallback to manual implementation
        return _bh_fdr(p_values)


# ─── Main Trend Analysis ──────────────────────────────────────────────────────

def run_trend_analysis(df_etccdi: pd.DataFrame, df_acf: pd.DataFrame) -> tuple:
    """
    Run trend analysis for all 11 ETCCDI indices.

    Method selection (per ACF diagnostics):
      - sig_lag1_primary == True → Hamed & Rao modified MK
      - Otherwise → ordinary MK

    Returns:
        (df_trend, df_fdr) as DataFrames
    """
    years = df_etccdi["Year"].values
    acf_lookup = {}
    if df_acf is not None and not df_acf.empty:
        for _, row in df_acf.iterrows():
            acf_lookup[row["Index"]] = bool(row.get("sig_lag1_primary", False))

    records = []
    p_raw_all = []

    for idx in INDICES:
        if idx not in df_etccdi.columns:
            continue
        # Use only rows where this index is not NaN
        mask = df_etccdi[idx].notna()
        x    = years[mask.values]
        y    = df_etccdi.loc[mask, idx].values
        n    = len(y)

        if n < 10:
            print(f"[TREND] {idx}: N={n}, too few observations. Skipping.")
            p_raw_all.append(np.nan)
            records.append({
                "Index": idx, "N": n,
                "Kendall_tau": np.nan, "Sen_slope": np.nan,
                "CI_low": np.nan, "CI_high": np.nan,
                "Sen_slope_decade": np.nan,
                "p_raw": np.nan, "p_FDR": np.nan,
                "Trend": "Insufficient data", "MK_method": "N/A",
            })
            continue

        use_corrected = acf_lookup.get(idx, False)
        mk_method_label = "ordinary_MK"

        # ── Run MK ────────────────────────────────────────────────────────────
        if HAS_PYMANNKENDALL:
            if use_corrected:
                if MK_METHOD_AC == "hamed_rao":
                    mk_result = mk.hamed_rao_modification_test(y)
                    mk_method_label = "Hamed_Rao_modified_MK"
                elif MK_METHOD_AC == "yue_wang":
                    mk_result = mk.yue_wang_modification_test(y)
                    mk_method_label = "Yue_Wang_modified_MK"
                else:
                    mk_result = mk.original_test(y)
                    mk_method_label = "ordinary_MK"
            else:
                mk_result = mk.original_test(y)
                mk_method_label = "ordinary_MK"

            tau  = float(mk_result.Tau)
            p_mk = float(mk_result.p)
        else:
            # Fallback
            fb = _mk_ordinary_fallback(y)
            tau  = fb["tau"]
            p_mk = fb["p"]
            mk_method_label = "ordinary_MK_fallback"

        # ── Sen's slope ───────────────────────────────────────────────────────
        slope, intercept, ci_low, ci_high = _sens_slope_ci(x, y)

        # ── Trend classification ──────────────────────────────────────────────
        # Note: classification uses raw p-value here; FDR adjustment applied later
        if p_mk < ALPHA:
            trend_label = "Significant increasing" if slope > 0 else "Significant decreasing"
        else:
            trend_label = "Non-significant increasing" if slope > 0 else "Non-significant decreasing"

        p_raw_all.append(p_mk)
        records.append({
            "Index":             idx,
            "N":                 n,
            "Kendall_tau":       round(tau, 4),
            "Sen_slope":         round(slope, 4),
            "Sen_slope_decade":  round(slope * 10, 4),
            "CI_low":            round(ci_low, 4),
            "CI_high":           round(ci_high, 4),
            "p_raw":             round(p_mk, 6),
            "Intercept":         round(intercept, 4),
            "Trend_raw":         trend_label,
            "MK_method":         mk_method_label,
        })

    # ── FDR adjustment ────────────────────────────────────────────────────────
    valid_p     = [(i, p) for i, p in enumerate(p_raw_all) if not np.isnan(p)]
    p_adj_array = [np.nan] * len(p_raw_all)
    if valid_p:
        idx_list  = [v[0] for v in valid_p]
        p_list    = [v[1] for v in valid_p]
        p_adj_fdr = _bh_fdr_correct(p_list)
        for orig_i, p_adj in zip(idx_list, p_adj_fdr):
            p_adj_array[orig_i] = p_adj

    for i, rec in enumerate(records):
        p_adj = p_adj_array[i]
        rec["p_FDR"] = round(float(p_adj), 6) if not np.isnan(p_adj) else np.nan
        # Reclassify using FDR-adjusted p
        slope = rec["Sen_slope"]
        if not np.isnan(p_adj) and p_adj < ALPHA:
            rec["Trend"] = "Significant increasing" if (not np.isnan(slope) and slope > 0) \
                           else "Significant decreasing"
        else:
            rec["Trend"] = "Non-significant increasing" if (not np.isnan(slope) and slope > 0) \
                           else "Non-significant decreasing"

    df_trend = pd.DataFrame(records)[[
        "Index", "N", "Kendall_tau", "Sen_slope", "Sen_slope_decade",
        "CI_low", "CI_high", "p_raw", "p_FDR", "Trend", "MK_method",
    ]]

    # FDR detail table
    df_fdr = df_trend[["Index", "N", "p_raw", "p_FDR", "Trend"]].copy()

    return df_trend, df_fdr


# ─── Save Outputs ─────────────────────────────────────────────────────────────

def save_trend_outputs(df_trend: pd.DataFrame, df_fdr: pd.DataFrame) -> None:
    """Save trend and FDR tables."""
    stats_dir  = OUTPUT_ROOT / "statistics"
    tables_dir = OUTPUT_ROOT / "tables"
    stats_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    # Statistics folder
    stats_path = stats_dir / "trend_analysis.xlsx"
    with pd.ExcelWriter(stats_path, engine="openpyxl") as writer:
        df_trend.to_excel(writer, sheet_name="Trend_Analysis", index=False)
    print(f"[TREND] trend_analysis.xlsx saved to {stats_path}")

    # TABLE_05
    t5_path = tables_dir / "TABLE_05_TREND_ANALYSIS.xlsx"
    with pd.ExcelWriter(t5_path, engine="openpyxl") as writer:
        df_trend.to_excel(writer, sheet_name="Trend_Analysis", index=False)
    print(f"[TREND] TABLE_05_TREND_ANALYSIS.xlsx saved to {t5_path}")

    # TABLE_06 FDR
    t6_path = tables_dir / "TABLE_06_FDR_ANALYSIS.xlsx"
    with pd.ExcelWriter(t6_path, engine="openpyxl") as writer:
        df_fdr.to_excel(writer, sheet_name="FDR_Analysis", index=False)
    print(f"[TREND] TABLE_06_FDR_ANALYSIS.xlsx saved to {t6_path}")


def run_trend(df_etccdi: pd.DataFrame, df_acf: pd.DataFrame) -> tuple:
    """Main entry point. Returns (df_trend, df_fdr)."""
    df_trend, df_fdr = run_trend_analysis(df_etccdi, df_acf)
    save_trend_outputs(df_trend, df_fdr)
    return df_trend, df_fdr
