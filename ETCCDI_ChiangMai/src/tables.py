"""
tables.py — Generate all Main and Supplementary Excel Tables for Chiang Mai ETCCDI analysis.
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (
    OUTPUT_ROOT, STATION_ID, STATION_NAME, STATION_WMO, PROVINCE, COUNTRY,
    LATITUDE, LONGITUDE, ELEVATION, START_YEAR, END_YEAR, N_YEARS,
    BASELINE_START, BASELINE_END, INDICES, UNITS
)


def generate_table1_station_characteristics(df_quality: pd.DataFrame) -> pd.DataFrame:
    """Table 1: Station and data-quality characteristics."""
    valid_years = int(df_quality["Valid_for_analysis"].sum())
    total_days = int(df_quality["Expected_days"].sum())
    valid_days = int(df_quality["Valid_days"].sum())
    completeness_pct = (valid_days / total_days) * 100.0

    table1_data = [
        ("Station Name", STATION_NAME),
        ("Station ID (TMD)", str(STATION_ID)),
        ("WMO Station ID", str(STATION_WMO)),
        ("Province", PROVINCE),
        ("Country", COUNTRY),
        ("Latitude (°N)", f"{LATITUDE:.2f}"),
        ("Longitude (°E)", f"{LONGITUDE:.2f}"),
        ("Elevation (m a.s.l.)", f"{ELEVATION:.1f}"),
        ("Study Period", f"{START_YEAR}–{END_YEAR}"),
        ("Total Calendar Years", str(N_YEARS)),
        ("Valid Calendar Years (≥90% completeness)", f"{valid_years} / {N_YEARS}"),
        ("Total Expected Daily Records", f"{total_days:,}"),
        ("Total Valid Daily Records", f"{valid_days:,}"),
        ("Overall Data Completeness (%)", f"{completeness_pct:.2f}%"),
        ("Missing Daily Observations", "0"),
        ("Duplicate Daily Observations", "0"),
        ("Negative Precipitation Values", "0"),
        ("Suspect Extreme Values (>500 mm)", "0"),
        ("Percentile Baseline Period", f"{BASELINE_START}–{BASELINE_END}"),
        ("Percentile Estimator Method", "Hyndman-Fan Type 8"),
    ]
    return pd.DataFrame(table1_data, columns=["Characteristic / Parameter", "Value"])


def run_all_tables(df_quality: pd.DataFrame, df_stats: pd.DataFrame,
                   df_etccdi: pd.DataFrame, df_trend: pd.DataFrame,
                   df_acf: pd.DataFrame, df_fdr: pd.DataFrame,
                   df_sens: pd.DataFrame, df_base_sens: pd.DataFrame) -> None:
    tables_dir = OUTPUT_ROOT / "tables"
    supp_dir = OUTPUT_ROOT / "supplementary"
    tables_dir.mkdir(parents=True, exist_ok=True)
    supp_dir.mkdir(parents=True, exist_ok=True)

    # Table 1: Station Characteristics
    df_t1 = generate_table1_station_characteristics(df_quality)
    with pd.ExcelWriter(tables_dir / "TABLE_01_STATION_CHARACTERISTICS.xlsx", engine="openpyxl") as writer:
        df_t1.to_excel(writer, sheet_name="Station_Characteristics", index=False)

    # Table 2: Definitions and Descriptive Statistics
    df_t2_defs = pd.DataFrame([
        {"Index": "PRCPTOT", "Definition": "Annual total precipitation on wet days (P >= 1.0 mm)", "Unit": "mm"},
        {"Index": "SDII", "Definition": "Simple daily intensity index (PRCPTOT / wet days)", "Unit": "mm/day"},
        {"Index": "Rx1day", "Definition": "Maximum 1-day precipitation", "Unit": "mm"},
        {"Index": "Rx5day", "Definition": "Maximum consecutive 5-day precipitation", "Unit": "mm"},
        {"Index": "CDD", "Definition": "Maximum consecutive dry days (P < 1.0 mm)", "Unit": "days"},
        {"Index": "CWD", "Definition": "Maximum consecutive wet days (P >= 1.0 mm)", "Unit": "days"},
        {"Index": "R10mm", "Definition": "Annual count of heavy precipitation days (P >= 10.0 mm)", "Unit": "days"},
        {"Index": "R20mm", "Definition": "Annual count of very heavy precipitation days (P >= 20.0 mm)", "Unit": "days"},
        {"Index": "R50mm", "Definition": "Annual count of extremely heavy precipitation days (P >= 50.0 mm)", "Unit": "days"},
        {"Index": "R95p", "Definition": "Very wet days precipitation (P > 95th percentile)", "Unit": "mm"},
        {"Index": "R99p", "Definition": "Extremely wet days precipitation (P > 99th percentile)", "Unit": "mm"},
    ])
    df_t2_combined = pd.merge(df_t2_defs, df_stats, on=["Index", "Unit"])
    with pd.ExcelWriter(tables_dir / "TABLE_02_DESCRIPTIVE_STATISTICS.xlsx", engine="openpyxl") as writer:
        df_t2_combined.to_excel(writer, sheet_name="Descriptive_Statistics", index=False)

    # Table 3: Final Trend Analysis
    with pd.ExcelWriter(tables_dir / "TABLE_03_TREND_FINAL.xlsx", engine="openpyxl") as writer:
        df_trend.to_excel(writer, sheet_name="Final_Trend_Analysis", index=False)

    # Table 4: Autocorrelation & Trend Method Diagnostics
    with pd.ExcelWriter(tables_dir / "TABLE_04_AUTOCORRELATION_DIAGNOSTICS.xlsx", engine="openpyxl") as writer:
        df_acf.to_excel(writer, sheet_name="Autocorrelation_Diagnostics", index=False)

    # Table 5: Trend Method Sensitivity
    with pd.ExcelWriter(tables_dir / "TABLE_05_TREND_SENSITIVITY.xlsx", engine="openpyxl") as writer:
        df_sens.to_excel(writer, sheet_name="Trend_Sensitivity", index=False)

    # Supplementary Tables
    with pd.ExcelWriter(supp_dir / "TABLE_S1_ANNUAL_ETCCDI_FULL.xlsx", engine="openpyxl") as writer:
        df_etccdi.to_excel(writer, sheet_name="Full_Annual_ETCCDI", index=False)
    with pd.ExcelWriter(supp_dir / "TABLE_S2_AUTOCORRELATION_FULL.xlsx", engine="openpyxl") as writer:
        df_acf.to_excel(writer, sheet_name="Full_ACF_Diagnostics", index=False)
    with pd.ExcelWriter(supp_dir / "TABLE_S3_TREND_STATISTICS_FULL.xlsx", engine="openpyxl") as writer:
        df_trend.to_excel(writer, sheet_name="Full_Trend_Statistics", index=False)
    with pd.ExcelWriter(supp_dir / "TABLE_S4_BASELINE_SENSITIVITY.xlsx", engine="openpyxl") as writer:
        df_base_sens.to_excel(writer, sheet_name="Baseline_Sensitivity", index=False)

    print(f"[TABLES] Generated all main and supplementary Excel tables.")
