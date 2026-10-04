#!/usr/bin/env python3
import os
import sys
import argparse
import yaml
import json
import datetime
import pandas as pd
import numpy as np

# Ensure package root is in sys.path
package_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

from src.data_loader import load_rainfall_data, parse_docx_metadata, binarize_rainfall
from src.markov_engine import compute_first_order_markov, compute_second_order_markov, model_order_selection_aic_bic
from src.spell_analysis import compute_spells, compute_spell_statistics
from src.spatial_temporal import evaluate_subperiod_stability, compute_spatial_heterogeneity
from src.exporters import export_analysis_tables, generate_publication_figures


def run_pipeline(config_path):
    print(f"Loading configuration from: {config_path}")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Resolve relative paths relative to package root if needed
    input_csv = os.path.join(package_root, config['input_rainfall_csv']) if not os.path.isabs(config['input_rainfall_csv']) else config['input_rainfall_csv']
    input_docx = os.path.join(package_root, config['input_metadata_docx']) if not os.path.isabs(config['input_metadata_docx']) else config['input_metadata_docx']

    project_name = config.get('project_name', 'default_run')
    output_dir = os.path.join(package_root, config.get('output_base_dir', 'outputs'), project_name)
    os.makedirs(output_dir, exist_ok=True)

    print(f"Loading rainfall data from: {input_csv}")
    df, station_cols = load_rainfall_data(
        input_csv,
        year_col=config.get('year_col', 'YEAR'),
        month_col=config.get('month_col', 'MONTH'),
        day_col=config.get('day_col', 'DAY'),
        date_col=config.get('date_col', None),
        station_cols=config.get('station_cols', None)
    )

    # Filter date range if specified
    start_yr = config.get('analysis_start_year')
    end_yr = config.get('analysis_end_year')
    if start_yr and end_yr:
        df = df[(df['DATE'].dt.year >= start_yr) & (df['DATE'].dt.year <= end_yr)].reset_index(drop=True)

    print(f"Data period: {df['DATE'].min().strftime('%Y-%m-%d')} to {df['DATE'].max().strftime('%Y-%m-%d')}")
    print(f"Stations ({len(station_cols)}): {station_cols}")

    # Parse station metadata if file exists
    meta_df = None
    if os.path.exists(input_docx):
        try:
            meta_df = parse_docx_metadata(input_docx)
            print("Successfully parsed station metadata.")
        except Exception as e:
            print(f"Warning: Could not parse metadata file: {e}")

    # Binarize rainfall into dry (0) and wet (1)
    threshold = config.get('wet_threshold_mm', 0.1)
    binary_df = binarize_rainfall(df, station_cols, threshold=threshold)

    # Run Markov Chain & Model Selection Analysis per station
    markov_records = []
    spells_records = []

    for sta in station_cols:
        series = binary_df[sta]
        m1 = compute_first_order_markov(series)
        m2 = compute_second_order_markov(series)
        ic = model_order_selection_aic_bic(series)
        sp = compute_spells(series)

        dry_stats = compute_spell_statistics(sp['dry_spells'])
        wet_stats = compute_spell_statistics(sp['wet_spells'])

        markov_records.append({
            'station_id': sta,
            'n_valid_days': int(series.notnull().sum()),
            'n00': m1['n00'], 'n01': m1['n01'], 'n10': m1['n10'], 'n11': m1['n11'],
            'p00': m1['p00'], 'p01': m1['p01'], 'p10': m1['p10'], 'p11': m1['p11'],
            'pi0': m1['pi0'], 'pi1': m1['pi1'],
            'best_order_aic': ic['best_order_aic'],
            'best_order_bic': ic['best_order_bic']
        })

        spells_records.append({
            'station_id': sta,
            'dry_count': dry_stats['count'], 'dry_mean': dry_stats['mean'], 'dry_std': dry_stats['std'],
            'dry_median': dry_stats['median'], 'dry_max': dry_stats['max'],
            'wet_count': wet_stats['count'], 'wet_mean': wet_stats['mean'], 'wet_std': wet_stats['std'],
            'wet_median': wet_stats['median'], 'wet_max': wet_stats['max'],
            'E_dry_theoretical': 1.0 / m1['p01'] if m1['p01'] > 0 else np.nan,
            'E_wet_theoretical': 1.0 / m1['p10'] if m1['p10'] > 0 else np.nan
        })

    markov_df = pd.DataFrame(markov_records)
    spells_df = pd.DataFrame(spells_records)

    # Evaluate Subperiod Stability if configured
    stability_df = None
    subperiods = config.get('temporal_subperiods')
    if subperiods and 'period1' in subperiods and 'period2' in subperiods:
        p1 = tuple(subperiods['period1'])
        p2 = tuple(subperiods['period2'])
        stability_df = evaluate_subperiod_stability(df, station_cols, threshold=threshold, period1_range=p1, period2_range=p2)

    # Spatial Heterogeneity Metrics
    spatial_metrics = compute_spatial_heterogeneity(markov_df)

    # Export Tables & Figures
    print(f"Exporting analysis tables to: {output_dir}")
    export_analysis_tables(output_dir, markov_df, spells_df, stability_df, meta_df=meta_df)

    dpi = config.get('figure_dpi', 300)
    print("Generating publication figures...")
    generate_publication_figures(output_dir, markov_df, spells_df, stability_df, meta_df=meta_df, dpi=dpi)

    # Write provenance/run metadata
    run_meta = {
        'timestamp': datetime.datetime.now().isoformat(),
        'project_name': project_name,
        'station_count': len(station_cols),
        'start_date': df['DATE'].min().strftime('%Y-%m-%d'),
        'end_date': df['DATE'].max().strftime('%Y-%m-%d'),
        'wet_threshold_mm': threshold,
        'spatial_metrics': spatial_metrics
    }
    with open(os.path.join(output_dir, 'run_provenance.json'), 'w') as f:
        json.dump(run_meta, f, indent=2)

    print(f"Pipeline execution completed successfully for project '{project_name}'.")
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run APST Markov Rainfall Analysis Pipeline")
    parser.add_argument('--config', type=str, default='config/config_example.yaml', help="Path to config file")
    args = parser.parse_args()

    sys.exit(run_pipeline(args.config))
