"""
etccdi.py — Calculate all 11 ETCCDI extreme precipitation indices.

Indices calculated per ETCCDI Expert Team definitions:
  PRCPTOT, SDII, Rx1day, Rx5day, CDD, CWD,
  R10mm, R20mm, R50mm, R95p, R99p

Wet day threshold: >= 1.0 mm/day (from config)
Percentile baseline: 1981–2010 wet-day pool
Completeness threshold: >= 90% of calendar days (from config)

For CDD/CWD: run lengths are NOT computed across NaN gaps.
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


# ─── Percentile Baseline ─────────────────────────────────────────────────────

def compute_baseline_percentiles(df: pd.DataFrame) -> dict:
    """
    Compute P95 and P99 from wet-day precipitation in the 1981–2010 baseline.

    Uses all wet days (PRECIP >= WET_DAY_THR) in baseline years.
    Percentile method: numpy linear interpolation (equivalent to Excel PERCENTILE).

    Returns dict with keys: 'wet_days', 'p95', 'p99', 'baseline_years'
    """
    baseline_df = df[
        (df["YEAR"] >= BASELINE_START) & (df["YEAR"] <= BASELINE_END)
    ].copy()

    wet_days = baseline_df.loc[
        baseline_df["PRECIP"] >= WET_DAY_THR, "PRECIP"
    ].dropna().values

    if len(wet_days) == 0:
        raise ValueError("No wet days found in baseline period. Check data.")

    p95 = float(np.percentile(wet_days, 95, method="linear"))
    p99 = float(np.percentile(wet_days, 99, method="linear"))

    result = {
        "baseline_start": BASELINE_START,
        "baseline_end":   BASELINE_END,
        "wet_days":       int(len(wet_days)),
        "p95":            round(p95, 4),
        "p99":            round(p99, 4),
    }
    print(f"[ETCCDI] Baseline {BASELINE_START}–{BASELINE_END}: "
          f"{len(wet_days)} wet days, P95 = {p95:.3f} mm, P99 = {p99:.3f} mm")
    return result


# ─── Run-length Helper ────────────────────────────────────────────────────────

def _max_run_length(series: pd.Series, condition_func) -> int:
    """
    Compute the maximum run length of consecutive days satisfying condition_func.
    NaN values break any run (runs are not bridged across missing observations).

    Args:
        series: pd.Series of daily precipitation values (may contain NaN)
        condition_func: callable that takes a scalar and returns bool or np.nan

    Returns:
        Maximum run length (int), or 0 if no run exists.
    """
    max_run = 0
    current_run = 0
    for val in series:
        if pd.isna(val):
            current_run = 0  # break run on missing observation
            continue
        if condition_func(val):
            current_run += 1
            max_run = max(max_run, current_run)
        else:
            current_run = 0
    return max_run


def _has_gap(series: pd.Series) -> bool:
    """Return True if series contains any NaN values."""
    return series.isna().any()


# ─── Per-Year ETCCDI ─────────────────────────────────────────────────────────

def compute_annual_index(yr_df: pd.DataFrame, year: int,
                         p95: float, p99: float) -> dict:
    """
    Compute all 11 ETCCDI indices for a single year's daily data.

    Args:
        yr_df:  DataFrame subset for one year (columns: DATE, PRECIP)
        year:   Calendar year (int)
        p95:    95th percentile threshold from 1981–2010 baseline (mm)
        p99:    99th percentile threshold from 1981–2010 baseline (mm)

    Returns:
        dict with one value per index (or np.nan if invalid)
    """
    prec = yr_df["PRECIP"]

    # ── Completeness check ────────────────────────────────────────────────────
    import calendar
    expected_days = 366 if calendar.isleap(year) else 365
    available = len(yr_df)
    completeness = available / expected_days

    if completeness < COMPLETENESS:
        warnings.warn(
            f"Year {year}: completeness {completeness:.1%} < {COMPLETENESS:.0%}. "
            "All indices set to NaN."
        )
        return {idx: np.nan for idx in INDICES}

    # ── Has missing values within available rows? ─────────────────────────────
    has_missing = prec.isna().any()

    # ── Wet/dry day masks ─────────────────────────────────────────────────────
    wet_mask = prec >= WET_DAY_THR           # True = wet day
    dry_mask = (prec < WET_DAY_THR) & prec.notna()  # True = dry day

    # ── PRCPTOT ───────────────────────────────────────────────────────────────
    prcptot = prec[wet_mask].sum()

    # ── SDII ──────────────────────────────────────────────────────────────────
    n_wet = wet_mask.sum()
    sdii  = prcptot / n_wet if n_wet > 0 else np.nan

    # ── Rx1day ────────────────────────────────────────────────────────────────
    rx1day = prec.max() if prec.notna().any() else np.nan

    # ── Rx5day ────────────────────────────────────────────────────────────────
    # Rolling 5-day sum; min_periods=5 ensures no partial sums
    roll5  = prec.rolling(window=5, min_periods=5).sum()
    rx5day = roll5.max() if roll5.notna().any() else np.nan

    # ── CDD / CWD ─────────────────────────────────────────────────────────────
    if has_missing:
        # Missing observations break run lengths
        cdd = _max_run_length(prec, lambda v: v < WET_DAY_THR)
        cwd = _max_run_length(prec, lambda v: v >= WET_DAY_THR)
    else:
        cdd = _max_run_length(prec, lambda v: v < WET_DAY_THR)
        cwd = _max_run_length(prec, lambda v: v >= WET_DAY_THR)

    # ── R10mm, R20mm, R50mm ───────────────────────────────────────────────────
    r10mm = int((prec >= R10_THR).sum())
    r20mm = int((prec >= R20_THR).sum())
    r50mm = int((prec >= R50_THR).sum())

    # ── R95p, R99p ────────────────────────────────────────────────────────────
    # Sum of precipitation on days exceeding P95 / P99 threshold
    r95p = float(prec[prec > p95].sum())
    r99p = float(prec[prec > p99].sum())

    return {
        "PRCPTOT": round(float(prcptot), 1),
        "SDII":    round(float(sdii), 2),
        "Rx1day":  round(float(rx1day), 1),
        "Rx5day":  round(float(rx5day), 1),
        "CDD":     int(cdd),
        "CWD":     int(cwd),
        "R10mm":   r10mm,
        "R20mm":   r20mm,
        "R50mm":   r50mm,
        "R95p":    round(r95p, 1),
        "R99p":    round(r99p, 1),
    }


# ─── Full Pipeline ────────────────────────────────────────────────────────────

def compute_all_etccdi(df: pd.DataFrame, valid_years: dict) -> pd.DataFrame:
    """
    Compute annual ETCCDI for all years 1961–2019.

    Args:
        df:          Full daily DataFrame (DATE, YEAR, PRECIP)
        valid_years: dict {year: bool} from QC

    Returns:
        DataFrame with columns [Year, PRCPTOT, SDII, ..., R99p]
    """
    baseline = compute_baseline_percentiles(df)
    p95 = baseline["p95"]
    p99 = baseline["p99"]

    records = []
    for year in range(START_YEAR, END_YEAR + 1):
        yr_df = df[df["YEAR"] == year].copy()
        if len(yr_df) == 0:
            print(f"[ETCCDI] WARNING: No data for year {year}.")
            rec = {idx: np.nan for idx in INDICES}
            rec["Year"] = year
            records.append(rec)
            continue

        if not valid_years.get(year, False):
            print(f"[ETCCDI] Year {year} marked invalid by QC. Setting all indices to NaN.")
            rec = {idx: np.nan for idx in INDICES}
            rec["Year"] = year
            records.append(rec)
            continue

        idx_vals = compute_annual_index(yr_df, year, p95, p99)
        idx_vals["Year"] = year
        records.append(idx_vals)

    df_etccdi = pd.DataFrame(records)[["Year"] + INDICES]
    print(f"[ETCCDI] Computed {len(df_etccdi)} annual records.")
    return df_etccdi, baseline


# ─── Save Outputs ─────────────────────────────────────────────────────────────

def save_etccdi_outputs(df_etccdi: pd.DataFrame, baseline: dict) -> None:
    """Save annual ETCCDI CSV, XLSX, and baseline table."""
    data_dir   = OUTPUT_ROOT / "data"
    tables_dir = OUTPUT_ROOT / "tables"
    data_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    # CSV
    csv_path = data_dir / "annual_ETCCDI_1961_2019.csv"
    df_etccdi.to_csv(csv_path, index=False)
    print(f"[ETCCDI] Annual CSV saved to {csv_path}")

    # XLSX — TABLE_03
    xlsx_path = tables_dir / "TABLE_03_ETCCDI_ANNUAL.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        df_etccdi.to_excel(writer, sheet_name="Annual_ETCCDI", index=False)
    print(f"[ETCCDI] TABLE_03_ETCCDI_ANNUAL.xlsx saved to {xlsx_path}")

    # TABLE_02 — Percentile Baseline
    df_baseline = pd.DataFrame([{
        "Baseline":         f"{baseline['baseline_start']}–{baseline['baseline_end']}",
        "Wet_days":         baseline["wet_days"],
        "P95_threshold_mm": baseline["p95"],
        "P99_threshold_mm": baseline["p99"],
    }])
    baseline_path = tables_dir / "TABLE_02_PERCENTILE_BASELINE.xlsx"
    with pd.ExcelWriter(baseline_path, engine="openpyxl") as writer:
        df_baseline.to_excel(writer, sheet_name="Percentile_Baseline", index=False)
    print(f"[ETCCDI] TABLE_02_PERCENTILE_BASELINE.xlsx saved to {baseline_path}")
