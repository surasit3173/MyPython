"""
main.py -- Master pipeline orchestrator for ETCCDI Chiang Mai analysis.

Run from project root:
    python main.py

Produces all outputs from raw CSV -> manuscript tables, figures, and DOCX.
"""
import sys
import time
import json
import warnings
import pandas as pd
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC_DIR))

from config import (
    RAW_DATA_PATH, OUTPUT_ROOT, AUDIT_DIR,
    START_YEAR, END_YEAR, N_YEARS, INDICES,
    STATION_NAME, STATION_ID, STATION_WMO,
)
import data_qc
import etccdi
import statistics as stats_mod
import autocorrelation
import trend as trend_mod
import sensitivity
import figures as figs_mod
import tables as tables_mod
import independent_verify
import manuscript

warnings.filterwarnings("ignore", category=RuntimeWarning)


def _save_pipeline_state(state: dict) -> None:
    cache_path = OUTPUT_ROOT / "pipeline_state.json"
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, default=str)
    print(f"[MAIN] Pipeline state saved to {cache_path}")


def main():
    t0 = time.time()
    print("=" * 70)
    print(f"ETCCDI Extreme Precipitation Analysis — {STATION_NAME}, Thailand")
    print(f"Station: WMO {STATION_WMO} | TMD {STATION_ID}")
    print(f"Period: {START_YEAR}–{END_YEAR} | Indices: {len(INDICES)}")
    print("=" * 70)

    # PHASE 1: Data QC
    print("\n[PHASE 1] Data quality control & forensic audit...")
    df_clean, valid_years = data_qc.run_qc()

    # PHASE 2: ETCCDI Calculations
    print("\n[PHASE 2] Computing 11 ETCCDI indices...")
    df_etccdi, baseline = etccdi.compute_all_etccdi(df_clean, valid_years)
    df_base_sens = etccdi.compute_baseline_sensitivity(df_clean, valid_years)
    etccdi.save_etccdi_outputs(df_etccdi, baseline, df_base_sens)

    # PHASE 3: Descriptive Statistics
    print("\n[PHASE 3] Computing descriptive statistics...")
    df_stats = stats_mod.run_statistics(df_etccdi)

    # PHASE 4: Autocorrelation Diagnostics
    print("\n[PHASE 4] Residual autocorrelation diagnostics...")
    df_acf = autocorrelation.run_autocorrelation(df_etccdi)

    # PHASE 5: Trend Analysis
    print("\n[PHASE 5] Trend analysis & FDR adjustment...")
    df_trend, df_fdr = trend_mod.run_trend(df_etccdi, df_acf)

    # PHASE 6: Sensitivity Analysis
    print("\n[PHASE 6] Trend sensitivity analysis...")
    df_sens = sensitivity.run_sensitivity_analysis(df_etccdi)

    # PHASE 7: Main and Supplementary Tables
    print("\n[PHASE 7] Generating all Excel tables...")
    df_quality = pd.read_excel(OUTPUT_ROOT / "tables" / "TABLE_01_DATA_QUALITY.xlsx")
    tables_mod.run_all_tables(
        df_quality=df_quality,
        df_stats=df_stats,
        df_etccdi=df_etccdi,
        df_trend=df_trend,
        df_acf=df_acf,
        df_fdr=df_fdr,
        df_sens=df_sens,
        df_base_sens=df_base_sens,
    )

    # PHASE 8: Publication Figures
    print("\n[PHASE 8] Generating 300 DPI publication figures...")
    figs_mod.run_all_figures(
        df_daily=df_clean,
        df_quality=df_quality,
        df_etccdi=df_etccdi,
        df_trend=df_trend,
        df_acf=df_acf,
    )

    # PHASE 9: Independent Verification & Reproducibility Check
    print("\n[PHASE 9] Running independent verification and reproducibility checks...")
    v_pass = independent_verify.run_independent_verification()
    r_pass = independent_verify.run_reproducibility_check()

    # PHASE 10: Manuscript Generation
    print("\n[PHASE 10] Generating full Q3 manuscript DOCX...")
    manuscript.create_manuscript(
        df_etccdi=df_etccdi,
        df_stats=df_stats,
        df_trend=df_trend,
        df_acf=df_acf,
        df_fdr=df_fdr,
        df_sens=df_sens,
        df_base_sens=df_base_sens,
        baseline=baseline,
    )

    state = {
        "station": STATION_NAME,
        "n_years_etccdi": len(df_etccdi),
        "valid_years": int(sum(valid_years.values())),
        "baseline_p95": baseline["p95"],
        "baseline_p99": baseline["p99"],
        "independent_verify_pass": v_pass,
        "reproducibility_pass": r_pass,
        "overall_status": "PASS" if (v_pass and r_pass) else "FAIL",
    }
    _save_pipeline_state(state)

    elapsed = time.time() - t0
    print(f"\n{'='*70}")
    print(f"Pipeline completed successfully in {elapsed:.1f} seconds.")
    print(f"Overall Status: {state['overall_status']}")
    print(f"Outputs in: {OUTPUT_ROOT.resolve()}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
