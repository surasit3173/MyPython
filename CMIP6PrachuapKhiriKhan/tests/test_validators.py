#!/usr/bin/env python3
"""
Unit Tests for Fail-Closed Validation Gate
==========================================
Tests missing files and malformed schema handling.
"""

import sys
import os
import unittest
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.validation.validators import validate_input_files, validate_rainfall_schema, StopBlockedException

class TestValidators(unittest.TestCase):

    def test_missing_input_file_triggers_stop_blocked(self):
        """Verifies missing input file triggers StopBlockedException."""
        bad_config = {
            'data': {
                'observed_csv': 'NON_EXISTENT_FILE.csv',
                'station_coords_csv': 'NON_EXISTENT_COORDS.csv'
            }
        }
        with self.assertRaises(StopBlockedException):
            validate_input_files(bad_config, base_dir='.')

    def test_duplicate_dates_triggers_stop_blocked(self):
        """Verifies duplicate dates in dataset trigger StopBlockedException."""
        df_dup = pd.DataFrame({
            'YEAR': [1981, 1981],
            'MONTH': [1, 1],
            'DAY': [1, 1],
            '500001': [10.0, 12.0]
        })
        config = {
            'data': {
                'date_columns': ['YEAR', 'MONTH', 'DAY'],
                'expected_station_count': 1,
                'analysis_period': [1981, 1981]
            }
        }
        with self.assertRaises(StopBlockedException):
            validate_rainfall_schema(df_dup, config)

if __name__ == '__main__':
    unittest.main()
