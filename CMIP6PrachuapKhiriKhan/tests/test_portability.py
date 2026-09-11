#!/usr/bin/env python3
"""
Unit Tests for Pipeline Portability
===================================
Verifies that the codebase runs seamlessly on a second synthetic dataset structure
without any code modification (only config & input file change).
Synthetic data is used ONLY for unit-test mechanics; never as research output.
"""

import sys
import os
import shutil
import tempfile
import unittest
import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.io.data_loader import load_project_data
from src.trends.trend_pipeline import run_trend_analysis_pipeline

class TestPortability(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        
        # Create second synthetic dataset (Province B) for portability mechanics test
        dates = pd.date_range('2000-01-01', '2005-12-31', freq='D')
        np.random.seed(999)
        df_obs = pd.DataFrame({
            'YEAR': dates.year,
            'MONTH': dates.month,
            'DAY': dates.day,
            'STATION_A': np.random.normal(10, 2, len(dates)),
            'STATION_B': np.random.normal(15, 3, len(dates))
        })
        obs_file = os.path.join(self.test_dir, 'Observed_Rain_ProvinceB.csv')
        df_obs.to_csv(obs_file, index=False)

        df_coords = pd.DataFrame({
            'Station': ['STATION_A', 'STATION_B'],
            'Lat': [13.1, 13.2],
            'Lon': [99.8, 99.9]
        })
        coords_file = os.path.join(self.test_dir, 'coords_ProvinceB.csv')
        df_coords.to_csv(coords_file, index=False)

        self.config = {
            'project': {
                'name': 'ProvinceB_Test_Project',
                'version': '1.0.0',
                'seed': 42
            },
            'data': {
                'observed_csv': 'Observed_Rain_ProvinceB.csv',
                'station_coords_csv': 'coords_ProvinceB.csv',
                'date_columns': ['YEAR', 'MONTH', 'DAY'],
                'expected_station_count': 2,
                'analysis_period': [2000, 2005]
            },
            'analysis': {
                'primary_method': 'yue_wang_2004',
                'secondary_method': 'standard_mk',
                'alpha': 0.05,
                'r1_significance_alpha': 0.05
            },
            'output': {
                'output_dir': os.path.join(self.test_dir, 'output'),
                'tables_dir': os.path.join(self.test_dir, 'output/tables'),
                'figures_dir': os.path.join(self.test_dir, 'output/figures'),
                'manifests_dir': os.path.join(self.test_dir, 'output/manifests'),
                'logs_dir': os.path.join(self.test_dir, 'output/logs')
            }
        }

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_portability_second_dataset(self):
        """Verifies pipeline runs seamlessly on Province B config and dataset."""
        data_info = load_project_data(self.config, base_dir=self.test_dir)
        self.assertEqual(len(data_info['station_cols']), 2)

        results_df = run_trend_analysis_pipeline(data_info, self.config)
        self.assertEqual(len(results_df), 6) # 2 stations x 3 periods (Annual, Wet, Dry)
        self.assertTrue((results_df['status'] == 'VALID').all())

if __name__ == '__main__':
    unittest.main()
