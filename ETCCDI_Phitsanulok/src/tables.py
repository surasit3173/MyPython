"""
tables.py — Generate manuscript tables (Tables 1–5 and S1–S5) as Excel files.

Main Tables:
  Table 1: Station/data characteristics
  Table 2: ETCCDI definitions + descriptive statistics
  Table 3: Trend analysis (core results)
  Table 4: Autocorrelation diagnostics + method selection
  Table 5: Summary of statistically significant changes

Supplementary:
  Table S1: Annual ETCCDI values 1961–2019 (full)
  Table S2: Full trend statistics
  Table S3: ACF diagnostics
  Table S4: FDR-adjusted results
  Table S5: Trend sensitivity
"""
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (
    OUTPUT_ROOT, INDICES, UNITS, ALPHA,
    START_YEAR, END_YEAR, N_YEARS,
    BASELINE_START, BASELINE_END,
    STATION_ID,
)

TABLES_DIR = OUTPUT_ROOT / "tables"


def _writer(filename: str) -> pd.ExcelWriter:
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    return pd.ExcelWriter(TABLES_DIR / filename, engine="openpyxl")


# ─── Table 1: Station Characteristics ────────────────────────────────────────

def make_table1(df_quality: pd.DataFrame) -> None:
    """Station/data characteristics table."""
    n_valid = int((df_quality["Valid"] == True).sum())
    total_days = int(df_quality["Available_days"].sum())
    completeness_mean = float(df_quality["Completeness_%"].mean())

    rows = [
        ("Station name",               "Phitsanulok"),
        ("Province",                   "Phitsanulok"),
        ("Country",                    "Thailand"),
        ("WMO station ID",             "48378"),
        ("TMD station ID",             str(STATION_ID)),
        ("Latitude (°N)",              "16.78"),
        ("Longitude (°E)",             "100.27"),
        ("Elevation (m a.s.l.)",       "45"),
        ("Record period",              f"{START_YEAR}–{END_YEAR}"),
        ("Number of years",            str(N_YEARS)),
        ("Total daily observations",   f"{total_days:,}"),
        ("Years with complete records (≥90%)", str(n_valid)),
        ("Mean annual completeness (%)", f"{completeness_mean:.1f}"),
        ("Wet-day threshold (mm/day)", "≥ 1.0"),
        ("Percentile baseline",        f"{BASELINE_START}–{BASELINE_END}"),
    ]
    df_t1 = pd.DataFrame(rows, columns=["Characteristic", "Value"])
    with _writer("TABLE_1_STATION_CHARACTERISTICS.xlsx") as w:
        df_t1.to_excel(w, sheet_name="Table_1", index=False)
    print("[TABLES] Table 1 saved.")


# ─── Table 2: ETCCDI Definitions + Descriptive Stats ─────────────────────────

ETCCDI_DEFS = {
    "PRCPTOT": "Annual total precipitation from wet days (P ≥ 1.0 mm)",
    "SDII":    "Simple Daily Intensity Index: PRCPTOT / number of wet days",
    "Rx1day":  "Maximum 1-day precipitation amount",
    "Rx5day":  "Maximum consecutive 5-day precipitation amount",
    "CDD":     "Maximum number of consecutive dry days (P < 1.0 mm)",
    "CWD":     "Maximum number of consecutive wet days (P ≥ 1.0 mm)",
    "R10mm":   "Number of days with precipitation ≥ 10 mm",
    "R20mm":   "Number of days with precipitation ≥ 20 mm",
    "R50mm":   "Number of days with precipitation ≥ 50 mm",
    "R95p":    "Annual total precipitation from very wet days (P > P95 of 1981–2010)",
    "R99p":    "Annual total precipitation from extremely wet days (P > P99 of 1981–2010)",
}


def make_table2(df_stats: pd.DataFrame) -> None:
    """ETCCDI definitions merged with descriptive statistics."""
    rows = []
    for idx in INDICES:
        row = {"Index": idx, "Unit": UNITS.get(idx, ""),
               "Definition": ETCCDI_DEFS.get(idx, "")}
        if df_stats is not None and not df_stats.empty:
            stat_row = df_stats[df_stats["Index"] == idx]
            if not stat_row.empty:
                sr = stat_row.iloc[0]
                row.update({
                    "N":      sr.get("N",      ""),
                    "Mean":   sr.get("Mean",   ""),
                    "Median": sr.get("Median", ""),
                    "SD":     sr.get("SD",     ""),
                    "Min":    sr.get("Min",    ""),
                    "Max":    sr.get("Max",    ""),
                    "CV_%":   sr.get("CV_%",   ""),
                })
        rows.append(row)
    df_t2 = pd.DataFrame(rows)
    with _writer("TABLE_2_ETCCDI_DEFINITIONS_STATS.xlsx") as w:
        df_t2.to_excel(w, sheet_name="Table_2", index=False)
    print("[TABLES] Table 2 saved.")


# ─── Table 3: Trend Analysis ─────────────────────────────────────────────────

def make_table3(df_trend: pd.DataFrame) -> None:
    """Core trend results table for manuscript."""
    if df_trend is None or df_trend.empty:
        print("[TABLES] No trend data for Table 3.")
        return

    cols = ["Index", "N", "Kendall_tau", "Sen_slope", "CI_low", "CI_high",
            "p_raw", "p_FDR", "Trend", "MK_method"]
    df_t3 = df_trend[[c for c in cols if c in df_trend.columns]].copy()
    # Add decade slope
    if "Sen_slope" in df_t3.columns:
        df_t3["Sen_slope_decade"] = (df_t3["Sen_slope"] * 10).round(4)

    with _writer("TABLE_3_TREND_ANALYSIS.xlsx") as w:
        df_t3.to_excel(w, sheet_name="Table_3", index=False)
    print("[TABLES] Table 3 saved.")


# ─── Table 4: Autocorrelation + Method ───────────────────────────────────────

def make_table4(df_acf: pd.DataFrame, df_trend: pd.DataFrame) -> None:
    """Autocorrelation diagnostics and MK method selection summary."""
    if df_acf is None or df_acf.empty:
        print("[TABLES] No ACF data for Table 4.")
        return

    trend_method = {}
    if df_trend is not None:
        for _, row in df_trend.iterrows():
            trend_method[row["Index"]] = row.get("MK_method", "")

    rows = []
    for _, row in df_acf.iterrows():
        idx = row["Index"]
        rows.append({
            "Index":              idx,
            "N":                  row["N"],
            "ACF_lag1":           row.get("ACF_lag1", np.nan),
            "ACF_lag2":           row.get("ACF_lag2", np.nan),
            "ACF_lag3":           row.get("ACF_lag3", np.nan),
            "sig_bound_95%":      row.get("sig_bound", np.nan),
            "sig_lag1":           row.get("sig_lag1_primary", False),
            "any_sig_lag1_to_5":  row.get("any_sig_lag1_to_5", False),
            "MK_method_selected": trend_method.get(idx, ""),
        })

    df_t4 = pd.DataFrame(rows)
    with _writer("TABLE_4_AUTOCORRELATION_METHOD.xlsx") as w:
        df_t4.to_excel(w, sheet_name="Table_4", index=False)
    print("[TABLES] Table 4 saved.")


# ─── Table 5: Significant Changes Summary ────────────────────────────────────

def make_table5(df_trend: pd.DataFrame) -> None:
    """Summary of statistically significant changes (FDR p < 0.05)."""
    if df_trend is None or df_trend.empty:
        print("[TABLES] No trend data for Table 5.")
        return

    sig_mask = df_trend["p_FDR"] < ALPHA
    df_sig = df_trend[sig_mask].copy()

    if df_sig.empty:
        # Create empty table with note
        df_t5 = pd.DataFrame([{
            "Note": f"No indices showed statistically significant trends at FDR p < {ALPHA}."
        }])
    else:
        df_t5 = df_sig[["Index", "Sen_slope", "Sen_slope_decade",
                         "CI_low", "CI_high", "p_raw", "p_FDR", "Trend"]].copy()
        df_t5["Unit"] = df_t5["Index"].map(UNITS)
        df_t5 = df_t5[["Index", "Unit", "Sen_slope", "Sen_slope_decade",
                        "CI_low", "CI_high", "p_raw", "p_FDR", "Trend"]]

    with _writer("TABLE_5_SIGNIFICANT_CHANGES.xlsx") as w:
        df_t5.to_excel(w, sheet_name="Table_5", index=False)
    print("[TABLES] Table 5 saved.")


# ─── Supplementary Tables ─────────────────────────────────────────────────────

def make_table_s1(df_etccdi: pd.DataFrame) -> None:
    """Supplementary Table S1: Full annual ETCCDI 1961–2019."""
    out = TABLES_DIR / "TABLE_S1_ANNUAL_ETCCDI_FULL.xlsx"
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        df_etccdi.to_excel(w, sheet_name="Annual_ETCCDI", index=False)
    print("[TABLES] Table S1 saved.")


def make_table_s2(df_trend: pd.DataFrame) -> None:
    """Supplementary Table S2: Full trend statistics."""
    if df_trend is None:
        return
    out = TABLES_DIR / "TABLE_S2_FULL_TREND_STATS.xlsx"
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        df_trend.to_excel(w, sheet_name="Full_Trend_Stats", index=False)
    print("[TABLES] Table S2 saved.")


def make_table_s3(df_acf: pd.DataFrame) -> None:
    """Supplementary Table S3: ACF diagnostics (all lags)."""
    if df_acf is None:
        return
    out = TABLES_DIR / "TABLE_S3_ACF_DIAGNOSTICS.xlsx"
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        df_acf.to_excel(w, sheet_name="ACF_Diagnostics", index=False)
    print("[TABLES] Table S3 saved.")


def make_table_s4(df_fdr: pd.DataFrame) -> None:
    """Supplementary Table S4: FDR analysis."""
    if df_fdr is None:
        return
    out = TABLES_DIR / "TABLE_S4_FDR_ANALYSIS.xlsx"
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        df_fdr.to_excel(w, sheet_name="FDR_Analysis", index=False)
    print("[TABLES] Table S4 saved.")


def make_table_s5(df_sens: pd.DataFrame) -> None:
    """Supplementary Table S5: Trend sensitivity analysis."""
    if df_sens is None:
        return
    out = TABLES_DIR / "TABLE_S5_TREND_SENSITIVITY.xlsx"
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        df_sens.to_excel(w, sheet_name="Trend_Sensitivity", index=False)
    print("[TABLES] Table S5 saved.")


# ─── Run All ──────────────────────────────────────────────────────────────────

def run_all_tables(df_quality: pd.DataFrame, df_stats: pd.DataFrame,
                   df_etccdi: pd.DataFrame, df_trend: pd.DataFrame,
                   df_acf: pd.DataFrame, df_fdr: pd.DataFrame,
                   df_sens: pd.DataFrame) -> None:
    """Generate all main and supplementary tables."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    make_table1(df_quality)
    make_table2(df_stats)
    make_table3(df_trend)
    make_table4(df_acf, df_trend)
    make_table5(df_trend)
    make_table_s1(df_etccdi)
    make_table_s2(df_trend)
    make_table_s3(df_acf)
    make_table_s4(df_fdr)
    make_table_s5(df_sens)
    print("[TABLES] All tables generated.")
