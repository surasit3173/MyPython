"""
main.py -- Master pipeline orchestrator for ETCCDI Phitsanulok analysis.

Run from project root:
    python main.py

Produces all outputs from raw CSV -> manuscript tables, figures, and DOCX.
"""
import sys
import time
import json
import warnings
from pathlib import Path

# Ensure src is on path
SRC_DIR = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC_DIR))

from config import (
    RAW_DATA_PATH, OUTPUT_ROOT, AUDIT_DIR,
    START_YEAR, END_YEAR, N_YEARS, INDICES,
)
import data_qc
import etccdi
import statistics as stats_mod
import autocorrelation
import trend as trend_mod
import sensitivity
import figures as figs_mod
import tables as tables_mod

warnings.filterwarnings("ignore", category=RuntimeWarning)


# ─── Audit Cache ──────────────────────────────────────────────────────────────

def _save_pipeline_state(state: dict) -> None:
    """Save pipeline state for consistency checker."""
    cache_path = OUTPUT_ROOT / "pipeline_state.json"
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, default=str)
    print(f"[MAIN] Pipeline state saved to {cache_path}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    t0 = time.time()
    print("=" * 70)
    print("ETCCDI Extreme Precipitation Analysis — Phitsanulok, Thailand")
    print(f"Period: {START_YEAR}–{END_YEAR} | Indices: {len(INDICES)}")
    print("=" * 70)

    # ── PHASE 1: Verify input ────────────────────────────────────────────────
    print("\n[PHASE 1] Input verification...")
    if not RAW_DATA_PATH.exists():
        raise FileNotFoundError(
            f"Input data file not found: {RAW_DATA_PATH}\n"
            "Please ensure the file is in the correct location."
        )
    print(f"[MAIN] Input file verified: {RAW_DATA_PATH}")
    print(f"[MAIN] File size: {RAW_DATA_PATH.stat().st_size:,} bytes")

    # ── PHASE 2: Data QC ────────────────────────────────────────────────────
    print("\n[PHASE 2] Data quality control...")
    df_clean, valid_years = data_qc.run_qc()
    print(f"[MAIN] Clean data: {len(df_clean):,} rows | Valid years: {sum(valid_years.values())}/{len(valid_years)}")

    # Load quality table for figures
    qc_table_path = OUTPUT_ROOT / "tables" / "TABLE_01_DATA_QUALITY.xlsx"
    import pandas as pd
    df_quality = pd.read_excel(qc_table_path, sheet_name="Data_Quality")

    # PHASE 3: ETCCDI
    print("\n[PHASE 3] Computing 11 ETCCDI indices...")

    df_etccdi, baseline = etccdi.compute_all_etccdi(df_clean, valid_years)
    etccdi.save_etccdi_outputs(df_etccdi, baseline)

    # Verify: must have exactly N_YEARS rows
    if len(df_etccdi) != N_YEARS:
        raise AssertionError(
            f"ETCCDI table has {len(df_etccdi)} rows; expected {N_YEARS}."
        )
    print(f"[MAIN] ETCCDI: {len(df_etccdi)} annual observations [OK]")

    # Verify 2019
    row2019 = df_etccdi[df_etccdi["Year"] == 2019]
    if row2019.empty:
        raise AssertionError("Year 2019 missing from ETCCDI output!")
    print(f"[MAIN] 2019 PRCPTOT = {row2019['PRCPTOT'].values[0]} mm [OK]")

    # ── PHASE 4: Descriptive Statistics ─────────────────────────────────────
    print("\n[PHASE 4] Computing descriptive statistics...")
    df_stats = stats_mod.run_statistics(df_etccdi)

    # ── PHASE 5: Autocorrelation ─────────────────────────────────────────────
    print("\n[PHASE 5] Autocorrelation diagnostics...")
    df_acf = autocorrelation.run_autocorrelation(df_etccdi)
    print(f"[MAIN] ACF computed for {len(df_acf)} indices.")

    # ── PHASE 6: Trend Analysis ──────────────────────────────────────────────
    print("\n[PHASE 6] Trend analysis (MK / Hamed-Rao / Sen's slope)...")
    df_trend, df_fdr = trend_mod.run_trend(df_etccdi, df_acf)
    print(f"[MAIN] Trend results:")
    for _, row in df_trend.iterrows():
        print(f"  {row['Index']:8s}: tau={row['Kendall_tau']:+.3f}, "
              f"slope={row['Sen_slope']:+.4f} ({row.get('MK_method','?')}), "
              f"p_raw={row['p_raw']:.4f}, p_FDR={row['p_FDR']:.4f}, "
              f"[{row['Trend']}]")

    # ── PHASE 7: Sensitivity Analysis ───────────────────────────────────────
    print("\n[PHASE 7] Sensitivity analysis (3-model comparison)...")
    df_sens = sensitivity.run_sensitivity_analysis(df_etccdi)

    # ── PHASE 8: Tables ──────────────────────────────────────────────────────
    print("\n[PHASE 8] Generating all tables...")
    tables_mod.run_all_tables(
        df_quality=df_quality,
        df_stats=df_stats,
        df_etccdi=df_etccdi,
        df_trend=df_trend,
        df_acf=df_acf,
        df_fdr=df_fdr,
        df_sens=df_sens,
    )

    # ── PHASE 9: Figures ─────────────────────────────────────────────────────
    print("\n[PHASE 9] Generating publication figures...")
    figs_mod.run_all_figures(
        df_etccdi=df_etccdi,
        df_quality=df_quality,
        df_trend=df_trend,
        df_acf=df_acf,
    )

    # ── PHASE 10: Manuscript ─────────────────────────────────────────────────
    print("\n[PHASE 10] Generating manuscript...")
    try:
        from manuscript import generate_manuscript
        generate_manuscript(
            df_etccdi=df_etccdi,
            df_stats=df_stats,
            df_trend=df_trend,
            df_acf=df_acf,
            df_fdr=df_fdr,
            df_sens=df_sens,
            baseline=baseline,
        )
    except ImportError:
        print("[MAIN] manuscript.py not found. Skipping DOCX generation.")

    # ── Save pipeline state ───────────────────────────────────────────────────
    state = {
        "n_years_etccdi":  len(df_etccdi),
        "valid_years":     int(sum(valid_years.values())),
        "indices":         INDICES,
        "baseline_p95":    baseline["p95"],
        "baseline_p99":    baseline["p99"],
        "baseline_wet_days": baseline["wet_days"],
        "trend_summary": df_trend[["Index", "Sen_slope", "p_raw", "p_FDR", "Trend"]].to_dict("records"),
        "n_significant_raw": int((df_trend["p_raw"] < 0.05).sum()),
        "n_significant_fdr": int((df_trend["p_FDR"] < 0.05).sum()),
    }
    _save_pipeline_state(state)

    elapsed = time.time() - t0
    print(f"\n{'='*70}")
    print(f"Pipeline completed in {elapsed:.1f} seconds.")
    print(f"Outputs in: {OUTPUT_ROOT.resolve()}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
