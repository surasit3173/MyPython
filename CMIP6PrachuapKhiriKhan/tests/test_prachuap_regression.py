#!/usr/bin/env python3
"""
Regression Test Suite (Project 1: Prachuap Khiri Khan)
======================================================
Compares raw observational daily rainfall processing against frozen historical outputs
(Comparative_4MMK_PrachuapKhiriKhanV1/processed_data/annual_rainfall.csv).
"""

import sys
import os
import unittest
import pandas as pd
import numpy as np


class TestPrachuapRegression(unittest.TestCase):

    def setUp(self):
        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.rain_path = os.path.join(self.base_dir, 'data', 'Observed_Rain_daily_198101_201412_PrachuapKhiriKhan.csv')
        if not os.path.exists(self.rain_path):
            self.rain_path = os.path.join(self.base_dir, 'Observed_Rain_daily_198101_201412_PrachuapKhiriKhan.csv')
        self.frozen_annual_path = os.path.join(self.base_dir, 'Comparative_4MMK_PrachuapKhiriKhanV1', 'processed_data', 'annual_rainfall.csv')

    def test_annual_rainfall_regression_match(self):
        """Verifies annual rainfall processing matches frozen historical baseline to exact decimal precision."""
        self.assertTrue(os.path.exists(self.rain_path), f"Missing raw rain file: {self.rain_path}")
        if not os.path.exists(self.frozen_annual_path):
            self.skipTest(f"Frozen historical baseline file omitted from portable package: {self.frozen_annual_path}")

        df_obs = pd.read_csv(self.rain_path)
        df_frozen = pd.read_csv(self.frozen_annual_path)

        df_obs['date'] = pd.to_datetime(df_obs[['YEAR', 'MONTH', 'DAY']])
        df_obs['year'] = df_obs['date'].dt.year

        # Check for Station 500001
        st1_obs_annual = df_obs.groupby('year')['500001'].sum().values
        st1_frozen_annual = df_frozen[df_frozen['Station'] == 500001]['Annual_mm'].values

        np.testing.assert_allclose(st1_obs_annual, st1_frozen_annual, rtol=1e-5,
                                   err_msg="Regression Discrepancy: Observed annual rainfall does not match frozen historical baseline!")


if __name__ == '__main__':
    unittest.main()
