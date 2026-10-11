import unittest
import numpy as np
import pandas as pd
import os
import sys

# Ensure package root in path
pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if pkg_root not in sys.path:
    sys.path.insert(0, pkg_root)

from src.markov_engine import compute_first_order_markov, compute_second_order_markov, model_order_selection_aic_bic
from src.spell_analysis import compute_spells, compute_spell_statistics
from src.spatial_temporal import compare_proportions_ztest
from src.data_loader import binarize_rainfall


class TestMarkovPackage(unittest.TestCase):

    def test_first_order_markov_invariants(self):
        # Synthetic binary series: 0 1 0 1 1 0 0 1
        s = pd.Series([0, 1, 0, 1, 1, 0, 0, 1])
        m = compute_first_order_markov(s)

        self.assertAlmostEqual(m['p00'] + m['p01'], 1.0)
        self.assertAlmostEqual(m['p10'] + m['p11'], 1.0)
        self.assertAlmostEqual(m['pi0'] + m['pi1'], 1.0)
        self.assertTrue(0.0 <= m['p01'] <= 1.0)
        self.assertTrue(0.0 <= m['p11'] <= 1.0)

    def test_spell_analysis_no_missing_bridging(self):
        # Series with NaN gap: 0, 0, NaN, 0, 1, 1
        s = pd.Series([0, 0, np.nan, 0, 1, 1])
        sp = compute_spells(s)

        # Dry spells should be [2, 1] because NaN breaks the sequence
        self.assertEqual(sp['dry_spells'], [2, 1])
        self.assertEqual(sp['wet_spells'], [2])

    def test_binarize_rainfall(self):
        df = pd.DataFrame({
            'DATE': pd.date_range('2020-01-01', periods=4),
            'STA1': [0.0, 0.05, 0.1, 15.0]
        })
        b_df = binarize_rainfall(df, ['STA1'], threshold=0.1)
        self.assertEqual(b_df['STA1'].tolist(), [0.0, 0.0, 1.0, 1.0])

    def test_compare_proportions_ztest(self):
        z, pval = compare_proportions_ztest(50, 100, 60, 100)
        self.assertIsInstance(z, float)
        self.assertTrue(0.0 <= pval <= 1.0)

    def test_model_order_selection(self):
        s = pd.Series([0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0])
        ic = model_order_selection_aic_bic(s)
        self.assertIn(ic['best_order_aic'], [0, 1, 2])
        self.assertIn(ic['best_order_bic'], [0, 1, 2])


if __name__ == '__main__':
    unittest.main()
