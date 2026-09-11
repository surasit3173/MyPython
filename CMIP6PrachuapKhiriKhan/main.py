#!/usr/bin/env python3
"""
Main Execution Script — Portable Refactored Trend Analysis
===========================================================
Primary Trend Method: Yue & Wang (2004) AR(1) Modified Mann-Kendall.
Secondary Reference: Standard Mann-Kendall.
"""

import sys
import os
import yaml
import logging

from src.io.data_loader import load_project_data
from src.trends.trend_pipeline import run_trend_analysis_pipeline
from src.io.exporter import export_trend_results, export_validation_report
from src.plotting.figure_generator import generate_trend_summary_figure
from src.provenance.manifest_generator import generate_run_manifest

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(base_dir, "config.yaml")

    if not os.path.exists(cfg_path):
        print(f"FAIL-CLOSED ERROR: Configuration file not found at '{cfg_path}'")
        sys.exit(1)

    with open(cfg_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Logging setup
    logs_dir = os.path.join(base_dir, config['output']['logs_dir'])
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, "pipeline.log")

    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    logging.info(f"Starting pipeline execution: {config['project']['name']} v{config['project']['version']}")

    print("==============================================================================")
    print(f"  {config['project']['name']} (v{config['project']['version']})")
    print("==============================================================================")
    print(f"Config loaded from: {cfg_path}")
    print(f"Primary Trend Method: {config['analysis']['primary_method']} (Yue & Wang 2004 AR(1) MMK)")
    print(f"Secondary Reference : {config['analysis']['secondary_method']} (Standard Mann-Kendall)\n")

    # 1. Load and Validate Input Data (Fail-Closed)
    print("[1/5] Loading & validating input datasets...")
    data_info = load_project_data(config, base_dir=base_dir)
    print(f"      Validated {len(data_info['station_cols'])} stations across period {config['data']['analysis_period']}.")

    # 2. Run Trend Pipeline
    print("[2/5] Executing trend calculations (Yue & Wang 2004 AR(1) MMK)...")
    results_df = run_trend_analysis_pipeline(data_info, config)
    print(f"      Calculated {len(results_df)} trend results across Annual, Wet, and Dry seasons.")

    # 3. Export Results & Validation Report
    print("[3/5] Exporting result tables & validation report...")
    trend_path, summary_path = export_trend_results(results_df, config, base_dir=base_dir)
    report_path = export_validation_report(data_info, config, base_dir=base_dir)
    print(f"      Results saved to: {trend_path}")

    # 4. Generate Figures
    print("[4/5] Generating publication figures...")
    annual_summary = results_df[results_df['period'] == 'Annual'].copy()
    fig_path = generate_trend_summary_figure(annual_summary, config, base_dir=base_dir)
    print(f"      Figure saved to: {fig_path}")

    # 5. Generate Manifest
    print("[5/5] Generating audit manifest...")
    output_files = {
        "trend_results": trend_path,
        "station_summary": summary_path,
        "validation_report": report_path,
        "summary_figure": fig_path
    }
    manifest_path = generate_run_manifest(config, data_info, output_files, base_dir=base_dir)
    print(f"      Manifest saved to: {manifest_path}\n")

    print("==============================================================================")
    print("  EXECUTION SUCCESSFUL — ALL GATES PASSED")
    print("==============================================================================")

if __name__ == '__main__':
    main()
