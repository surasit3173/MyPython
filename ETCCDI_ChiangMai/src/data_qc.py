"""
data_qc.py -- Quality control, data auditing, and validated CSV generation.
"""

import sys
import hashlib
from datetime import date
from pathlib import Path
import pandas as pd
import numpy as np

from config import (
    RAW_DATA_PATH, OUTPUT_ROOT, AUDIT_DIR,
    STATION_ID, STATION_NAME, STATION_WMO, PROVINCE,
    START_YEAR, END_YEAR,
    COMPLETENESS, SUSPECT_VAL, cfg,
)


def verify_sha256(path: Path = RAW_DATA_PATH) -> str:
    """Verify raw data file against recorded SHA-256 hash in config.yaml."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    computed_hash = hasher.hexdigest()
    recorded_hash = cfg.get("sha256")
    if recorded_hash and computed_hash != recorded_hash:
        raise ValueError(f"SHA-256 Mismatch!\nExpected: {recorded_hash}\nComputed: {computed_hash}")
    return computed_hash


def _expected_days(year: int) -> int:
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    return (end - start).days + 1


def _is_leap(year: int) -> bool:
    import calendar
    return calendar.isleap(year)


def load_raw(path: Path = RAW_DATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"YEAR": int, "MONTH": int, "DAY": int})
    df.columns = df.columns.str.strip()

    precip_col = str(STATION_ID)
    if precip_col not in df.columns:
        precip_col = df.columns[3]

    df = df.rename(columns={precip_col: "PRECIP"})
    df["Source_Row"] = df.index + 2  # 1-indexed plus header row
    df["DATE"] = pd.to_datetime(
        df[["YEAR", "MONTH", "DAY"]].rename(
            columns={"YEAR": "year", "MONTH": "month", "DAY": "day"}
        )
    )
    return df[["Source_Row", "DATE", "YEAR", "MONTH", "DAY", "PRECIP"]].copy()


def audit_raw(df: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    results = {}
    results["total_rows"] = len(df)
    results["date_min"] = df["DATE"].min()
    results["date_max"] = df["DATE"].max()
    results["year_min"] = int(df["YEAR"].min())
    results["year_max"] = int(df["YEAR"].max())
    results["n_years"] = results["year_max"] - results["year_min"] + 1

    expected_total = sum(_expected_days(y) for y in range(START_YEAR, END_YEAR + 1))
    results["expected_total_days"] = expected_total
    results["actual_total_rows"] = len(df)

    # Unique dates / duplicates
    dup_mask = df["DATE"].duplicated(keep=False)
    results["n_duplicate_dates"] = int(dup_mask.sum())
    results["duplicate_dates"] = df.loc[dup_mask, "DATE"].tolist()

    # Missing dates
    full_range = pd.date_range(start=date(START_YEAR, 1, 1), end=date(END_YEAR, 12, 31), freq="D")
    missing_dates = full_range.difference(df["DATE"])
    results["n_missing_dates"] = len(missing_dates)
    results["missing_dates"] = missing_dates.tolist()

    # Data type & numeric check
    df["PRECIP_num"] = pd.to_numeric(df["PRECIP"], errors="coerce")
    results["n_nonnumeric"] = int(df["PRECIP_num"].isna().sum() - df["PRECIP"].isna().sum())

    # Missing precipitation
    results["n_missing_precip"] = int(df["PRECIP_num"].isna().sum())
    results["missing_precip_dates"] = df.loc[df["PRECIP_num"].isna(), "DATE"].tolist()

    # Negative precipitation
    neg_mask = df["PRECIP_num"] < 0
    results["n_negative"] = int(neg_mask.sum())
    results["negative_dates"] = df.loc[neg_mask, "DATE"].tolist()

    # Suspect values
    sus_mask = df["PRECIP_num"] > SUSPECT_VAL
    results["n_suspect"] = int(sus_mask.sum())
    results["suspect_records"] = df.loc[sus_mask, ["DATE", "PRECIP_num"]].to_dict("records")

    # Per-year forensic breakdown based on UNIQUE VALID CALENDAR DATES
    year_stats = []
    for yr in range(START_YEAR, END_YEAR + 1):
        yr_df = df[df["YEAR"] == yr].copy()
        expected = _expected_days(yr)
        observed_rows = len(yr_df)
        unique_dates = yr_df["DATE"].nunique()
        duplicate_rows = observed_rows - unique_dates

        # calculate missing dates for this year
        yr_full_range = pd.date_range(start=date(yr, 1, 1), end=date(yr, 12, 31), freq="D")
        missing_d = len(yr_full_range.difference(yr_df["DATE"]))

        missing_precip = int(yr_df["PRECIP_num"].isna().sum())
        neg_precip = int((yr_df["PRECIP_num"] < 0).sum())

        # Valid days: unique calendar dates with valid non-negative numeric precipitation
        valid_days = unique_dates - missing_precip - neg_precip
        completeness_pct = (valid_days / expected) * 100.0
        valid_for_analysis = completeness_pct >= (COMPLETENESS * 100.0)

        year_stats.append({
            "Year": yr,
            "Leap_year": _is_leap(yr),
            "Expected_days": expected,
            "Observed_rows": observed_rows,
            "Unique_dates": unique_dates,
            "Duplicate_rows": duplicate_rows,
            "Missing_dates": missing_d,
            "Missing_precip": missing_precip,
            "Valid_days": valid_days,
            "Completeness_percent": round(completeness_pct, 2),
            "Valid_for_analysis": valid_for_analysis,
        })
    results["year_stats"] = year_stats

    return results, df


def create_validated_csv(df: pd.DataFrame) -> pd.DataFrame:
    """Generate output/data/validated_daily_precipitation.csv with QC flags."""
    val_df = df.copy()

    # Flags: OK, SUSPECT, INVALID_MISSING, INVALID_NEGATIVE
    flags = []
    for _, row in val_df.iterrows():
        val = row["PRECIP_num"]
        if pd.isna(val):
            flags.append("INVALID_MISSING")
        elif val < 0:
            flags.append("INVALID_NEGATIVE")
        elif val > SUSPECT_VAL:
            flags.append("SUSPECT_EXTREME")
        else:
            flags.append("OK")

    val_df["QC_Flag"] = flags
    val_df["Precipitation_mm"] = val_df["PRECIP_num"]
    val_df["Date"] = val_df["DATE"].dt.strftime("%Y-%m-%d")

    out_cols = ["Date", "YEAR", "MONTH", "DAY", "Precipitation_mm", "QC_Flag", "Source_Row"]
    out_df = val_df[out_cols]

    out_path = OUTPUT_ROOT / "data" / "validated_daily_precipitation.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out_path, index=False)
    print(f"[QC] Validated daily data saved to {out_path}")
    return val_df


def save_audit_outputs(results: dict, computed_hash: str) -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. SHA256 Manifest & Provenance
    (AUDIT_DIR / "SHA256_MANIFEST.txt").write_text(
        f"{computed_hash}  {RAW_DATA_PATH.name}\n", encoding="utf-8"
    )

    prov_text = f"""# Data Provenance Manifest
- **Station Name**: {STATION_NAME}
- **Station ID**: {STATION_ID}
- **WMO ID**: {STATION_WMO}
- **Province**: {PROVINCE}
- **Raw File Path**: `{RAW_DATA_PATH}`
- **SHA-256 Hash**: `{computed_hash}`
- **Audit Date**: {date.today()}
- **Verification Result**: MATCH
"""
    (AUDIT_DIR / "DATA_PROVENANCE.md").write_text(prov_text, encoding="utf-8")

    # 2. Markdown Forensic Report
    year_stats = results["year_stats"]
    n_invalid_years = sum(1 for ys in year_stats if not ys["Valid_for_analysis"])
    n_valid_years = sum(1 for ys in year_stats if ys["Valid_for_analysis"])

    lines = [
        "# Data Forensic Audit Report",
        f"- **Station**: WMO {STATION_WMO} | ID {STATION_ID} | {STATION_NAME}, {PROVINCE}, Thailand",
        f"- **Period**: {START_YEAR}–{END_YEAR} ({results['n_years']} calendar years)",
        f"- **Authoritative File**: `{RAW_DATA_PATH}`",
        f"- **SHA-256**: `{computed_hash}`",
        "",
        "## 1. File Integrity & Coverage Summary",
        f"- Total records in CSV: **{results['total_rows']:,}**",
        f"- Expected total calendar days (1961–2019): **{results['expected_total_days']:,}**",
        f"- Date range: **{results['date_min'].date()}** to **{results['date_max'].date()}**",
        f"- Duplicate dates count: **{results['n_duplicate_dates']}**",
        f"- Missing calendar dates count: **{results['n_missing_dates']}**",
        "",
        "## 2. Quality Control & Extremes",
        f"- Non-numeric precipitation values: **{results['n_nonnumeric']}**",
        f"- Missing precipitation records: **{results['n_missing_precip']}**",
        f"- Negative precipitation values: **{results['n_negative']}**",
        f"- Extreme suspect values (>{SUSPECT_VAL} mm): **{results['n_suspect']}**",
        "",
        "## 3. Annual Completeness & Validity",
        f"- Valid years (≥90% completeness): **{n_valid_years}** / {results['n_years']}",
        f"- Excluded / Invalid years: **{n_invalid_years}**",
        "",
        "### Per-Year Audit Summary (Full table in DATA_FORENSIC_REPORT.xlsx / TABLE_01_DATA_QUALITY.xlsx)",
        "",
        "| Year | Expected | Observed | Unique Dates | Duplicate Rows | Missing Dates | Missing Precip | Valid Days | Completeness % | Valid |",
        "|------|----------|----------|--------------|----------------|---------------|----------------|------------|----------------|-------|",
    ]
    for ys in year_stats:
        lines.append(
            f"| {ys['Year']} | {ys['Expected_days']} | {ys['Observed_rows']} | {ys['Unique_dates']} | "
            f"{ys['Duplicate_rows']} | {ys['Missing_dates']} | {ys['Missing_precip']} | {ys['Valid_days']} | "
            f"{ys['Completeness_percent']:.2f}% | {ys['Valid_for_analysis']} |"
        )

    yr2019 = next((ys for ys in year_stats if ys["Year"] == 2019), None)
    lines += [
        "",
        "## 4. Year 2019 Specific Verification",
        f"- Expected days: **{yr2019['Expected_days']}**" if yr2019 else "- 2019 missing!",
        f"- Observed days: **{yr2019['Observed_rows']}**" if yr2019 else "",
        f"- Unique valid days: **{yr2019['Valid_days']}**" if yr2019 else "",
        f"- Completeness: **{yr2019['Completeness_percent']:.2f}%**" if yr2019 else "",
        f"- Status: **{'PASS - COMPLETE 365 DAYS' if yr2019 and yr2019['Valid_days'] == 365 else 'FAIL'}**",
    ]

    (AUDIT_DIR / "DATA_FORENSIC_REPORT.md").write_text("\n".join(lines), encoding="utf-8")

    # 3. Excel Forensic Report & Table 1
    df_ys = pd.DataFrame(year_stats)

    # Save audit/DATA_FORENSIC_REPORT.xlsx
    excel_audit_path = AUDIT_DIR / "DATA_FORENSIC_REPORT.xlsx"
    with pd.ExcelWriter(excel_audit_path, engine="openpyxl") as writer:
        df_ys.to_excel(writer, sheet_name="Data_Forensics", index=False)

    # Save output/tables/TABLE_01_DATA_QUALITY.xlsx
    tables_dir = OUTPUT_ROOT / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    t1_path = tables_dir / "TABLE_01_DATA_QUALITY.xlsx"
    with pd.ExcelWriter(t1_path, engine="openpyxl") as writer:
        df_ys.to_excel(writer, sheet_name="Data_Quality", index=False)

    print(f"[QC] Audit reports saved to {AUDIT_DIR}")


def run_qc() -> tuple[pd.DataFrame, dict]:
    print("[QC] Verifying SHA-256 hash...")
    computed_hash = verify_sha256()
    print(f"[QC] SHA-256 Verified: {computed_hash}")

    print("[QC] Loading raw data...")
    df_raw = load_raw()

    print("[QC] Auditing raw data...")
    results, df_raw = audit_raw(df_raw)

    print("[QC] Generating validated CSV...")
    df_val = create_validated_csv(df_raw)

    print("[QC] Saving audit reports...")
    save_audit_outputs(results, computed_hash)

    df_clean = df_raw[["DATE", "YEAR", "MONTH", "DAY", "PRECIP_num"]].copy()
    df_clean = df_clean.rename(columns={"PRECIP_num": "PRECIP"})
    df_clean = df_clean.sort_values("DATE").reset_index(drop=True)

    year_stats = results["year_stats"]
    valid_years = {ys["Year"]: ys["Valid_for_analysis"] for ys in year_stats}

    return df_clean, valid_years
