#!/usr/bin/env python3
import os
import sys
import yaml
import pandas as pd
import numpy as np

package_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

from src.data_loader import load_rainfall_data, binarize_rainfall
from src.markov_engine import compute_first_order_markov

def validate_analysis():
    print("Running Scientific Validation Audit...")

    config_path = os.path.join(package_root, 'config/config_example.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    csv_path = os.path.join(package_root, config['input_rainfall_csv'])
    df, station_cols = load_rainfall_data(csv_path)

    threshold = config.get('wet_threshold_mm', 0.1)
    binary_df = binarize_rainfall(df, station_cols, threshold=threshold)

    failures = []

    # 1. Invariant Check: P00 + P01 == 1.0 and P10 + P11 == 1.0
    for sta in station_cols:
        series = binary_df[sta]
        m = compute_first_order_markov(series)

        if not np.isclose(m['p00'] + m['p01'], 1.0):
            failures.append(f"Station {sta}: P00 + P01 = {m['p00'] + m['p01']} != 1.0")
        if not np.isclose(m['p10'] + m['p11'], 1.0):
            failures.append(f"Station {sta}: P10 + P11 = {m['p10'] + m['p11']} != 1.0")

        # Check probability bounds [0, 1]
        for key in ['p00', 'p01', 'p10', 'p11', 'pi0', 'pi1']:
            val = m[key]
            if not (0.0 <= val <= 1.0):
                failures.append(f"Station {sta}: {key} = {val} out of bounds [0, 1]")

    if failures:
        print("VALIDATION FAILED with errors:")
        for err in failures:
            print(" -", err)
        return 1
    else:
        print("VALIDATION PASSED: All probability invariants and boundary conditions hold.")
        return 0

if __name__ == '__main__':
    sys.exit(validate_analysis())
