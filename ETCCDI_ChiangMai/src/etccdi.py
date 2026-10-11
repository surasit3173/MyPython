"""
etccdi.py — Calculate all 11 ETCCDI extreme precipitation indices for Chiang Mai.

Indices calculated per ETCCDI Expert Team definitions and project execution rules:
  PRCPTOT, SDII, Rx1day, Rx5day, CDD, CWD,
  R10mm, R20mm, R50mm, R95p, R99p

Cross-Year Convention:
  - Five-day totals and dry/wet spell lengths evaluated on the continuous daily series.
  - Assigned to the calendar year of the final day.
  - Spells / windows crossing the calendar year boundary are not artificially truncated.
  - Missing observations terminate a spell / window.

Percentile Estimator:
  - Hyndman-Fan Type 8 (np.percentile method="median_unbiased").
  - Baseline period: 1981–2010 (primary), wet days (P >= 1.0 mm).
"""

import sys
import warnings
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (
    OUTPUT_ROOT, AUDIT_DIR,
    START_YEAR, END_YEAR,
    BASELINE_START, BASELINE_END,
    WET_DAY_THR, R10_THR, R20_THR, R50_THR,
    COMPLETENESS, INDICES, UNITS,
)


def compute_baseline_percentiles(df: pd.DataFrame, base_start: int = BASELINE_START, base_end: int = BASELINE_END) -> dict:
    """
    Compute P95 and P99 from wet-day precipitation in baseline period using Hyndman-Fan Type 8.
    """
    baseline_df = df[
        (df["YEAR"] >= base_start) & (df["YEAR"] <= base_end)
    ].copy()

    wet_days = baseline_df.loc[
        baseline_df["PRECIP"] >= WET_DAY_THR, "PRECIP"
    ].dropna().values

    if len(wet_days) == 0:
        raise ValueError(f"No wet days found in baseline period {base_start}-{base_end}.")

    # Hyndman-Fan Type 8 = np.percentile(..., method="median_unbiased")
    p95 = float(np.percentile(wet_days, 95, method="median_unbiased"))
    p99 = float(np.percentile(wet_days, 99, method="median_unbiased"))

    result = {
        "baseline_start": base_start,
        "baseline_end": base_end,
        "baseline_period": f"{base_start}–{base_end}",
        "wet_days": int(len(wet_days)),
        "p95": round(p95, 4),
        "p99": round(p99, 4),
    }
    return result


def compute_continuous_series_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute continuous daily features across the entire daily record:
      - Continuous 5-day rolling sum (Rx5day candidates)
      - Continuous spell lengths for CWD (wet days P >= 1.0 mm)
      - Continuous spell lengths for CDD (dry days P < 1.0 mm)
    Assigned to the final day of the window/spell.
    Missing data terminates continuous spells / windows.
    """
    df_cont = df.copy().sort_values("DATE").reset_index(drop=True)
    prec = df_cont["PRECIP"].values

    # Continuous 5-day sum
    # rolling window 5, min_periods 5 (if any NaN in 5-day window, sum is NaN)
    roll5 = df_cont["PRECIP"].rolling(window=5, min_periods=5).sum().values
    df_cont["Roll5_sum"] = roll5

    # Continuous spell calculation
    n = len(df_cont)
    cwd_run = np.zeros(n, dtype=int)
    cdd_run = np.zeros(n, dtype=int)

    curr_cwd = 0
    curr_cdd = 0

    for i in range(n):
        p = prec[i]
        if pd.isna(p):
            curr_cwd = 0
            curr_cdd = 0
        else:
            if p >= WET_DAY_THR:
                curr_cwd += 1
                curr_cdd = 0
            else:
                curr_cdd += 1
                curr_cwd = 0
        cwd_run[i] = curr_cwd
        cdd_run[i] = curr_cdd

    df_cont["CWD_run"] = cwd_run
    df_cont["CDD_run"] = cdd_run

    return df_cont


def compute_all_etccdi(df: pd.DataFrame, valid_years: dict, base_start: int = BASELINE_START, base_end: int = BASELINE_END) -> tuple[pd.DataFrame, dict]:
    """
    Compute annual ETCCDI for all years 1961–2019.
    """
    baseline = compute_baseline_percentiles(df, base_start, base_end)
    p95 = baseline["p95"]
    p99 = baseline["p99"]

    df_cont = compute_continuous_series_features(df)

    records = []
    for year in range(START_YEAR, END_YEAR + 1):
        yr_df = df_cont[df_cont["YEAR"] == year].copy()

        import calendar
        expected_days = 366 if calendar.isleap(year) else 365
        observed_rows = len(yr_df)
        valid_days = yr_df["PRECIP"].notna().sum()
        completeness_pct = round((valid_days / expected_days) * 100.0, 2)
        is_valid = valid_years.get(year, True) and (completeness_pct >= COMPLETENESS * 100.0)

        if not is_valid:
            rec = {idx: np.nan for idx in INDICES}
            rec.update({
                "Year": year,
                "Valid_days": valid_days,
                "Completeness_percent": completeness_pct,
            })
            records.append(rec)
            continue

        prec = yr_df["PRECIP"]
        wet_mask = prec >= WET_DAY_THR

        prcptot = prec[wet_mask].sum()
        n_wet = wet_mask.sum()
        sdii = prcptot / n_wet if n_wet > 0 else np.nan

        rx1day = prec.max() if prec.notna().any() else np.nan
        rx5day = yr_df["Roll5_sum"].max() if yr_df["Roll5_sum"].notna().any() else np.nan

        cdd = int(yr_df["CDD_run"].max()) if len(yr_df) > 0 else 0
        cwd = int(yr_df["CWD_run"].max()) if len(yr_df) > 0 else 0

        r10mm = int((prec >= R10_THR).sum())
        r20mm = int((prec >= R20_THR).sum())
        r50mm = int((prec >= R50_THR).sum())

        r95p = float(prec[prec > p95].sum())
        r99p = float(prec[prec > p99].sum())

        rec = {
            "Year": year,
            "PRCPTOT": round(float(prcptot), 1),
            "SDII": round(float(sdii), 2),
            "Rx1day": round(float(rx1day), 1),
            "Rx5day": round(float(rx5day), 1),
            "CDD": cdd,
            "CWD": cwd,
            "R10mm": r10mm,
            "R20mm": r20mm,
            "R50mm": r50mm,
            "R95p": round(r95p, 1),
            "R99p": round(r99p, 1),
            "Valid_days": int(valid_days),
            "Completeness_percent": completeness_pct,
        }
        records.append(rec)

    cols = ["Year"] + INDICES + ["Valid_days", "Completeness_percent"]
    df_etccdi = pd.DataFrame(records)[cols]
    return df_etccdi, baseline


def compute_baseline_sensitivity(df: pd.DataFrame, valid_years: dict) -> pd.DataFrame:
    """
    Compare baseline periods: 1961–1990, 1971–2000, 1981–2010.
    Calculates P95, P99, mean annual R95p, mean annual R99p.
    """
    periods = [(1961, 1990), (1971, 2000), (1981, 2010)]
    sens_rows = []

    for b_start, b_end in periods:
        df_base_etccdi, base_info = compute_all_etccdi(df, valid_years, b_start, b_end)
        mean_r95 = df_base_etccdi["R95p"].mean()
        mean_r99 = df_base_etccdi["R99p"].mean()

        sens_rows.append({
            "Baseline_Period": f"{b_start}–{b_end}",
            "Baseline_Wet_Days": base_info["wet_days"],
            "P95_Threshold_mm": base_info["p95"],
            "P99_Threshold_mm": base_info["p99"],
            "Mean_R95p_mm": round(float(mean_r95), 2),
            "Mean_R99p_mm": round(float(mean_r99), 2),
            "Percentile_Estimator": "Hyndman-Fan Type 8",
        })

    return pd.DataFrame(sens_rows)


def save_etccdi_outputs(df_etccdi: pd.DataFrame, baseline: dict, df_base_sens: pd.DataFrame) -> None:
    data_dir = OUTPUT_ROOT / "data"
    tables_dir = OUTPUT_ROOT / "tables"
    stats_dir = OUTPUT_ROOT / "statistics"

    data_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    stats_dir.mkdir(parents=True, exist_ok=True)

    # Master Datasets
    csv_path = data_dir / "annual_ETCCDI_ChiangMai_1961_2019.csv"
    xlsx_path = data_dir / "annual_ETCCDI_ChiangMai_1961_2019.xlsx"
    df_etccdi.to_csv(csv_path, index=False)
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        df_etccdi.to_excel(writer, sheet_name="Annual_ETCCDI", index=False)

    # TABLE_03_ETCCDI_ANNUAL.xlsx
    t3_path = tables_dir / "TABLE_03_ETCCDI_ANNUAL.xlsx"
    with pd.ExcelWriter(t3_path, engine="openpyxl") as writer:
        df_etccdi.to_excel(writer, sheet_name="Annual_ETCCDI", index=False)

    # PERCENTILE_BASELINE.xlsx
    df_baseline_tbl = pd.DataFrame([{
        "Station": "Chiang Mai (327501 / WMO 48327)",
        "Baseline_Period": f"{baseline['baseline_start']}–{baseline['baseline_end']}",
        "Wet_Days_Count": baseline["wet_days"],
        "P95_Threshold_mm": baseline["p95"],
        "P99_Threshold_mm": baseline["p99"],
        "Percentile_Method": "Hyndman-Fan Type 8",
        "Wet_Day_Definition": "P >= 1.0 mm",
    }])

    pbase_stats_path = stats_dir / "PERCENTILE_BASELINE.xlsx"
    pbase_tbl_path = tables_dir / "TABLE_02_PERCENTILE_BASELINE.xlsx"
    with pd.ExcelWriter(pbase_stats_path, engine="openpyxl") as writer:
        df_baseline_tbl.to_excel(writer, sheet_name="Percentile_Baseline", index=False)
    with pd.ExcelWriter(pbase_tbl_path, engine="openpyxl") as writer:
        df_baseline_tbl.to_excel(writer, sheet_name="Percentile_Baseline", index=False)

    # TABLE_S_BASELINE_SENSITIVITY.xlsx
    bsens_stats_path = stats_dir / "TABLE_S_BASELINE_SENSITIVITY.xlsx"
    bsens_tbl_path = tables_dir / "TABLE_S_BASELINE_SENSITIVITY.xlsx"
    with pd.ExcelWriter(bsens_stats_path, engine="openpyxl") as writer:
        df_base_sens.to_excel(writer, sheet_name="Baseline_Sensitivity", index=False)
    with pd.ExcelWriter(bsens_tbl_path, engine="openpyxl") as writer:
        df_base_sens.to_excel(writer, sheet_name="Baseline_Sensitivity", index=False)

    print(f"[ETCCDI] Saved annual master datasets and baseline sensitivity tables.")
