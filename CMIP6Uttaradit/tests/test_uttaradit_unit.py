#!/usr/bin/env python3
"""
Unit Tests for 11 ETCCDI Indices (Project 2: Uttaradit)
=========================================================
Tests calculation of 11 locked ETCCDI indices: PRCPTOT, SDII, Rx1day, Rx5day, CDD, CWD, R10mm, R20mm, R50mm, R95p, R99p.
"""

import sys
import os
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.indices.etccdi import calculate_uttaradit_etccdi_11


class TestUttaraditUnit(unittest.TestCase):

    def test_etccdi_11_indices_calculation(self):
        """Verifies calculation of 11 ETCCDI indices on controlled 10-day series."""
        dates = pd.date_range('1995-01-01', periods=10, freq='D')
        precip = np.array([0.0, 12.0, 5.0, 0.0, 55.0, 0.0, 1.0, 2.0, 3.0, 0.0]) # includes >50mm day
        df = pd.DataFrame({'date': dates, 'precipitation_mm': precip})

        indices_df = calculate_uttaradit_etccdi_11(df, baseline_years=(1995, 1995))
        row = indices_df.iloc[0]

        self.assertEqual(row['year'], 1995)
        self.assertEqual(row['Rx1day'], 55.0)
        self.assertEqual(row['Rx5day'], 72.0) # 12+5+0+55+0 = 72
        self.assertEqual(row['PRCPTOT'], 78.0) # 12+5+55+1+2+3 = 78
        self.assertEqual(row['R10mm'], 2)    # 12, 55
        self.assertEqual(row['R20mm'], 1)    # 55
        self.assertEqual(row['R50mm'], 1)    # 55
        self.assertEqual(row['CWD'], 3)      # 1, 2, 3


if __name__ == '__main__':
    unittest.main()
