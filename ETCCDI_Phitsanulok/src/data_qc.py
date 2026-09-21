"""
data_qc.py — Data quality control and audit for daily precipitation records.

Performs a comprehensive audit of the raw CSV file and produces:
  - DATA_AUDIT_REPORT.md
  - TABLE_01_DATA_QUALITY.xlsx

No imputation is performed. Missing values are documented only.
"""
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (
    RAW_DATA_PATH, AUDIT_DIR, OUTPUT_ROOT,
    STATION_ID, START_YEAR, END_YEAR,
    COMPLETENESS, SUSPECT_VAL,
)


# ─── Helper ─────────────────────────────────────────────────────────────────

def _expected_days(year: int) -> int:
    """Return the number of calendar days in year (accounting for leap year)."""
    start = date(year, 1, 1)
    end   = date(year, 12, 31)
    return (end - start).days + 1


def _is_leap(year: int) -> bool:
    import calendar
    return calendar.isleap(year)


# ─── Load ────────────────────────────────────────────────────────────────────

def load_raw(path: Path = RAW_DATA_PATH) -> pd.DataFrame:
    """Load the raw daily precipitation CSV.

    Expected columns: YEAR, MONTH, DAY, <station_id>
    Returns a DataFrame with a 'DATE' column (datetime64) and 'PRECIP' column.
    """
    df = pd.read_csv(path, dtype={"YEAR": int, "MONTH": int, "DAY": int})
    df.columns = df.columns.str.strip()

    # Identify precipitation column (station ID or similar)
    precip_col = str(STATION_ID)
    if precip_col not in df.columns:
        # Fallback: use the 4th column
        precip_col = df.columns[3]

    df = df.rename(columns={precip_col: "PRECIP"})
    df["DATE"] = pd.to_datetime(
        df[["YEAR", "MONTH", "DAY"]].rename(
            columns={"YEAR": "year", "MONTH": "month", "DAY": "day"}
        )
    )
    df = df[["DATE", "YEAR", "MONTH", "DAY", "PRECIP"]].copy()
    return df


# ─── Audit Functions ─────────────────────────────────────────────────────────

def audit_raw(df: pd.DataFrame) -> dict:
    """Run full audit on loaded DataFrame. Returns audit dictionary."""

    results = {}

    # 1. Basic counts
    results["total_rows"] = len(df)
    results["date_min"]   = df["DATE"].min()
    results["date_max"]   = df["DATE"].max()
    results["year_min"]   = int(df["YEAR"].min())
    results["year_max"]   = int(df["YEAR"].max())
    results["n_years"]    = results["year_max"] - results["year_min"] + 1

    # 2. Expected total days 1961–2019
    expected_total = sum(_expected_days(y) for y in range(START_YEAR, END_YEAR + 1))
    results["expected_total_days"] = expected_total
    results["actual_total_rows"]   = len(df)

    # 3. Duplicate dates
    dup_mask = df["DATE"].duplicated(keep=False)
    results["n_duplicate_dates"] = int(dup_mask.sum())
    results["duplicate_dates"]   = df.loc[dup_mask, "DATE"].tolist()

    # 4. Missing calendar dates
    full_range = pd.date_range(
        start=date(START_YEAR, 1, 1),
        end=date(END_YEAR, 12, 31),
        freq="D",
    )
    missing_dates = full_range.difference(df["DATE"])
    results["n_missing_dates"] = len(missing_dates)
    results["missing_dates"]   = missing_dates.tolist()

    # 5. PRECIP data type issues
    # Try to convert PRECIP to numeric
    df["PRECIP_num"] = pd.to_numeric(df["PRECIP"], errors="coerce")
    results["n_nonnumeric"] = int(df["PRECIP_num"].isna().sum() - df["PRECIP"].isna().sum())

    # 6. Missing precipitation values (NaN after numeric conversion)
    results["n_missing_precip"] = int(df["PRECIP_num"].isna().sum())
    results["missing_precip_dates"] = df.loc[df["PRECIP_num"].isna(), "DATE"].tolist()

    # 7. Negative precipitation
    neg_mask = df["PRECIP_num"] < 0
    results["n_negative"] = int(neg_mask.sum())
    results["negative_dates"] = df.loc[neg_mask, "DATE"].tolist()

    # 8. Suspect (extreme) values
    sus_mask = df["PRECIP_num"] > SUSPECT_VAL
    results["n_suspect"] = int(sus_mask.sum())
    results["suspect_records"] = df.loc[sus_mask, ["DATE", "PRECIP_num"]].to_dict("records")

    # 9. Per-year completeness
    year_stats = []
    for yr in range(START_YEAR, END_YEAR + 1):
        yr_df = df[df["YEAR"] == yr].copy()
        expected = _expected_days(yr)
        available = len(yr_df)
        missing_d = expected - available
        # count invalid (NaN or negative)
        invalid = int(yr_df["PRECIP_num"].isna().sum()) + int((yr_df["PRECIP_num"] < 0).sum())
        completeness_pct = (available / expected) * 100
        valid_annual = completeness_pct >= (COMPLETENESS * 100)
        year_stats.append({
            "Year":             yr,
            "Leap_year":        _is_leap(yr),
            "Expected_days":    expected,
            "Available_days":   available,
            "Missing_days":     missing_d,
            "Invalid_values":   invalid,
            "Completeness_pct": round(completeness_pct, 2),
            "Valid":            valid_annual,
        })
    results["year_stats"] = year_stats

    return results, df


# ─── Save Outputs ─────────────────────────────────────────────────────────────

def save_audit_report(results: dict) -> None:
    """Write DATA_AUDIT_REPORT.md."""
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = AUDIT_DIR / "DATA_AUDIT_REPORT.md"

    year_stats = results["year_stats"]
    n_invalid_years = sum(1 for ys in year_stats if not ys["Valid"])
    n_valid_years   = sum(1 for ys in year_stats if ys["Valid"])

    lines = [
        "# Data Audit Report",
        f"**Station**: WMO 48378 | ID {STATION_ID} | Phitsanulok, Thailand",
        f"**Study period**: {START_YEAR}–{END_YEAR}",
        "",
        "## 1. File Summary",
        f"- Input file: `{RAW_DATA_PATH}`",
        f"- Total data rows: {results['total_rows']:,}",
        f"- Date range in file: {results['date_min'].date()} to {results['date_max'].date()}",
        f"- Year range: {results['year_min']}–{results['year_max']}",
        f"- Expected total days (1961–2019): {results['expected_total_days']:,}",
        f"- Actual rows: {results['actual_total_rows']:,}",
        "",
        "## 2. Duplicate Dates",
        f"- Count: **{results['n_duplicate_dates']}**",
    ]
    if results["duplicate_dates"]:
        lines.append(f"  - Dates: {results['duplicate_dates']}")

    lines += [
        "",
        "## 3. Missing Calendar Dates",
        f"- Count: **{results['n_missing_dates']}**",
    ]
    if results["missing_dates"][:20]:
        lines.append(f"  - First 20: {[str(d.date()) for d in results['missing_dates'][:20]]}")

    lines += [
        "",
        "## 4. Precipitation Data Issues",
        f"- Non-numeric values: **{results['n_nonnumeric']}**",
        f"- Missing (NaN) values: **{results['n_missing_precip']}**",
        f"- Negative values: **{results['n_negative']}**",
        f"- Suspect values (>{SUSPECT_VAL} mm/day): **{results['n_suspect']}**",
    ]
    if results["suspect_records"]:
        lines.append("  - Suspect records:")
        for rec in results["suspect_records"]:
            lines.append(f"    - {rec['DATE'].date()}: {rec['PRECIP_num']} mm")

    lines += [
        "",
        "## 5. Annual Completeness",
        f"- Years meeting ≥90% completeness threshold: **{n_valid_years}** / {results['n_years']}",
        f"- Years NOT meeting threshold: **{n_invalid_years}**",
        "",
        "### Per-Year Table (first/last 5 shown here; full table in TABLE_01_DATA_QUALITY.xlsx)",
        "",
        "| Year | Expected | Available | Missing | Completeness% | Valid |",
        "|------|----------|-----------|---------|---------------|-------|",
    ]
    sample = year_stats[:5] + year_stats[-5:]
    for ys in sample:
        lines.append(
            f"| {ys['Year']} | {ys['Expected_days']} | {ys['Available_days']} | "
            f"{ys['Missing_days']} | {ys['Completeness_pct']:.2f} | {ys['Valid']} |"
        )

    # Check 2019 specifically
    yr2019 = next((ys for ys in year_stats if ys["Year"] == 2019), None)
    lines += [
        "",
        "## 6. Year 2019 Verification",
    ]
    if yr2019:
        lines += [
            f"- Expected days: {yr2019['Expected_days']}",
            f"- Available days: {yr2019['Available_days']}",
            f"- Missing days: {yr2019['Missing_days']}",
            f"- Completeness: {yr2019['Completeness_pct']:.2f}%",
            f"- Valid_annual_record: **{yr2019['Valid']}**",
        ]
    else:
        lines.append("- **WARNING**: 2019 not found in data!")

    lines += [
        "",
        "## 7. Audit Conclusion",
        "No imputation was performed. Missing values are documented above.",
        "Data used in ETCCDI calculations follows the ≥90% completeness rule per ETCCDI guidelines.",
    ]

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[QC] Audit report saved to {report_path}")


def save_table01(results: dict) -> None:
    """Write TABLE_01_DATA_QUALITY.xlsx."""
    tables_dir = OUTPUT_ROOT / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    df_ys = pd.DataFrame(results["year_stats"])
    df_ys = df_ys.rename(columns={
        "Year":             "Year",
        "Leap_year":        "Leap_year",
        "Expected_days":    "Expected_days",
        "Available_days":   "Available_days",
        "Missing_days":     "Missing_days",
        "Invalid_values":   "Invalid_values",
        "Completeness_pct": "Completeness_%",
        "Valid":            "Valid",
    })
    out_path = tables_dir / "TABLE_01_DATA_QUALITY.xlsx"
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df_ys.to_excel(writer, sheet_name="Data_Quality", index=False)
    print(f"[QC] TABLE_01_DATA_QUALITY.xlsx saved to {out_path}")


# ─── Main ────────────────────────────────────────────────────────────────────

def run_qc() -> pd.DataFrame:
    """Run full QC pipeline. Returns cleaned DataFrame for downstream use."""
    print("[QC] Loading raw data...")
    df_raw = load_raw()
    print(f"[QC] Loaded {len(df_raw):,} rows.")

    print("[QC] Running audit...")
    results, df_raw = audit_raw(df_raw)

    save_audit_report(results)
    save_table01(results)

    # Subset to PRECIP_num for downstream use
    df_clean = df_raw[["DATE", "YEAR", "MONTH", "DAY", "PRECIP_num"]].copy()
    df_clean = df_clean.rename(columns={"PRECIP_num": "PRECIP"})
    df_clean = df_clean.sort_values("DATE").reset_index(drop=True)

    # Store valid years list on module for use by etccdi.py
    year_stats = results["year_stats"]
    global VALID_YEARS
    VALID_YEARS = {ys["Year"]: ys["Valid"] for ys in year_stats}

    print("[QC] Data audit complete.")
    return df_clean, VALID_YEARS


VALID_YEARS: dict = {}  # populated by run_qc()
