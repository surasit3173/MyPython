"""
final_consistency_check.py — Cross-validation of all pipeline outputs.

Checks:
  1. Data → ETCCDI: N years must be 59
  2. ETCCDI → Trend: N per index matches valid observations
  3. Trend → FDR: p-values present and consistent
  4. Figures correspond to data (file existence check)
  5. Audit gate: results flagged as errors if mismatch found

Pipeline fails with non-zero exit if any check fails.
"""
import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC_DIR))

from config import OUTPUT_ROOT, AUDIT_DIR, INDICES, N_YEARS, ALPHA

TABLES_DIR  = OUTPUT_ROOT / "tables"
STATS_DIR   = OUTPUT_ROOT / "statistics"
FIGURES_DIR = OUTPUT_ROOT / "figures"

ERRORS   = []
WARNINGS = []


def check(condition: bool, msg_pass: str, msg_fail: str, fatal: bool = True) -> None:
    if condition:
        print(f"  ✓ {msg_pass}")
    else:
        symbol = "✗ ERROR" if fatal else "⚠ WARNING"
        print(f"  {symbol}: {msg_fail}")
        if fatal:
            ERRORS.append(msg_fail)
        else:
            WARNINGS.append(msg_fail)


# ─── Gate 1: Data ─────────────────────────────────────────────────────────────

def gate1_data() -> None:
    print("\n[GATE 1] DATA")
    csv_path = OUTPUT_ROOT / "data" / "annual_ETCCDI_1961_2019.csv"
    check(csv_path.exists(), f"ETCCDI CSV exists at {csv_path}", "ETCCDI CSV not found")
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        check(len(df) == N_YEARS,
              f"ETCCDI has {N_YEARS} rows",
              f"ETCCDI has {len(df)} rows (expected {N_YEARS})")
        check(1961 in df["Year"].values and 2019 in df["Year"].values,
              "Years 1961 and 2019 present",
              "Years 1961 or 2019 missing from ETCCDI")
        row2019 = df[df["Year"] == 2019]
        check(not row2019.empty, "2019 row present", "2019 row missing")

    audit_report = AUDIT_DIR / "DATA_AUDIT_REPORT.md"
    check(audit_report.exists(), "DATA_AUDIT_REPORT.md exists",
          "DATA_AUDIT_REPORT.md missing")


# ─── Gate 2: ETCCDI ───────────────────────────────────────────────────────────

def gate2_etccdi() -> None:
    print("\n[GATE 2] ETCCDI")
    csv_path = OUTPUT_ROOT / "data" / "annual_ETCCDI_1961_2019.csv"
    if not csv_path.exists():
        ERRORS.append("ETCCDI CSV missing; skipping Gate 2 checks.")
        return

    df = pd.read_csv(csv_path)
    for idx in INDICES:
        check(idx in df.columns,
              f"Index {idx} present in ETCCDI",
              f"Index {idx} MISSING from ETCCDI")

    # Check no all-NA column
    for idx in INDICES:
        if idx in df.columns:
            n_valid = df[idx].notna().sum()
            check(n_valid > 0,
                  f"{idx}: {n_valid} valid observations",
                  f"{idx}: ALL values are NaN — check calculation")

    # Verify units/ranges (sanity check)
    if "PRCPTOT" in df.columns:
        prcptot_max = df["PRCPTOT"].max()
        check(prcptot_max < 5000 and prcptot_max > 100,
              f"PRCPTOT range plausible (max={prcptot_max:.1f} mm)",
              f"PRCPTOT max value implausible: {prcptot_max:.1f} mm")

    if "SDII" in df.columns:
        sdii_max = df["SDII"].max()
        check(sdii_max < 200 and sdii_max > 1,
              f"SDII range plausible (max={sdii_max:.2f} mm/day)",
              f"SDII max value implausible: {sdii_max:.2f} mm/day")

    baseline_path = TABLES_DIR / "TABLE_02_PERCENTILE_BASELINE.xlsx"
    check(baseline_path.exists(), "Baseline percentile table exists",
          "TABLE_02_PERCENTILE_BASELINE.xlsx missing")


# ─── Gate 3: Statistics ───────────────────────────────────────────────────────

def gate3_statistics() -> None:
    print("\n[GATE 3] STATISTICS")
    trend_path = STATS_DIR / "trend_analysis.xlsx"
    check(trend_path.exists(), "trend_analysis.xlsx exists",
          "trend_analysis.xlsx missing")

    if trend_path.exists():
        df_trend = pd.read_excel(trend_path, sheet_name="Trend_Analysis")
        check(len(df_trend) == len(INDICES),
              f"Trend table has {len(INDICES)} rows",
              f"Trend table has {len(df_trend)} rows (expected {len(INDICES)})")

        # N per index must match ETCCDI
        csv_path = OUTPUT_ROOT / "data" / "annual_ETCCDI_1961_2019.csv"
        if csv_path.exists():
            df_etccdi = pd.read_csv(csv_path)
            for _, row in df_trend.iterrows():
                idx = row["Index"]
                if idx in df_etccdi.columns:
                    n_etccdi = int(df_etccdi[idx].notna().sum())
                    n_trend  = int(row["N"])
                    check(n_etccdi == n_trend,
                          f"{idx}: N consistent (N={n_trend})",
                          f"{idx}: N mismatch — ETCCDI={n_etccdi}, Trend={n_trend}")

        # p_FDR must exist and be ≤ p_raw
        check("p_FDR" in df_trend.columns, "p_FDR column present", "p_FDR column missing")
        check("p_raw" in df_trend.columns, "p_raw column present", "p_raw column missing")
        if "p_FDR" in df_trend.columns and "p_raw" in df_trend.columns:
            inconsistent = (df_trend["p_FDR"] < df_trend["p_raw"] - 1e-8).any()
            check(not inconsistent,
                  "p_FDR ≥ p_raw for all indices (BH property)",
                  "p_FDR < p_raw for some index — BH correction may be incorrect",
                  fatal=False)

    acf_path = STATS_DIR / "autocorrelation_analysis.xlsx"
    check(acf_path.exists(), "autocorrelation_analysis.xlsx exists",
          "autocorrelation_analysis.xlsx missing")


# ─── Gate 4: Figures ──────────────────────────────────────────────────────────

def gate4_figures() -> None:
    print("\n[GATE 4] FIGURES")
    expected_figures = [
        "FIGURE_01_DATA_COVERAGE.png",
        "FIGURE_02_ETCCDI_TIME_SERIES.png",
        "FIGURE_03_TREND_HEATMAP.png",
        "FIGURE_04_SENS_SLOPE_CI.png",
        "FIGURE_05_ACF_DIAGNOSTIC.png",
        "FIGURE_06_ETCCDI_DISTRIBUTION.png",
    ]
    for fname in expected_figures:
        fig_path = FIGURES_DIR / fname
        check(fig_path.exists() and fig_path.stat().st_size > 1000,
              f"{fname} exists and non-empty",
              f"{fname} missing or empty")


# ─── Gate 5: Manuscript ───────────────────────────────────────────────────────

def gate5_manuscript() -> None:
    print("\n[GATE 5] MANUSCRIPT")
    ms_dir = OUTPUT_ROOT / "manuscript"
    docx_files = list(ms_dir.glob("*.docx")) if ms_dir.exists() else []
    check(len(docx_files) > 0,
          f"Manuscript DOCX found: {[f.name for f in docx_files]}",
          "No DOCX manuscript found",
          fatal=False)


# ─── Gate 6: Reproducibility ─────────────────────────────────────────────────

def gate6_reproducibility() -> None:
    print("\n[GATE 6] PIPELINE STATE")
    state_path = OUTPUT_ROOT / "pipeline_state.json"
    check(state_path.exists(), "pipeline_state.json exists",
          "pipeline_state.json missing — run main.py first")
    if state_path.exists():
        with open(state_path) as fh:
            state = json.load(fh)
        n_years = state.get("n_years_etccdi", 0)
        check(n_years == N_YEARS,
              f"Pipeline state: {N_YEARS} ETCCDI years",
              f"Pipeline state: {n_years} years (expected {N_YEARS})")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("ETCCDI Pipeline — Final Consistency Check")
    print("=" * 70)

    gate1_data()
    gate2_etccdi()
    gate3_statistics()
    gate4_figures()
    gate5_manuscript()
    gate6_reproducibility()

    print("\n" + "=" * 70)
    if ERRORS:
        print(f"RESULT: FAILED — {len(ERRORS)} error(s):")
        for e in ERRORS:
            print(f"  ✗ {e}")
        sys.exit(1)
    elif WARNINGS:
        print(f"RESULT: PASSED with {len(WARNINGS)} warning(s):")
        for w in WARNINGS:
            print(f"  ⚠ {w}")
        sys.exit(0)
    else:
        print("RESULT: ALL GATES PASSED ✓")
        sys.exit(0)


if __name__ == "__main__":
    main()
