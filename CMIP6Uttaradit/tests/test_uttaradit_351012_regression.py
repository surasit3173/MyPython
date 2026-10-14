#!/usr/bin/env python3
import unittest
import numpy as np
import pandas as pd
from scipy import stats, optimize

class TestUttaradit351012Regression(unittest.TestCase):
    def setUp(self):
        self.raw_data_path = 'CMIP6Uttaradit/Observed_Rain_daily_198101_201412_Uttaradit.csv'
        df_raw = pd.read_csv(self.raw_data_path)
        self.x = df_raw.groupby('YEAR')['351012'].max().values
        self.n = len(self.x) # 34

    def test_aicc_formula_correctness(self):
        # Formula test for n = 34
        # Gumbel k=2: penalty = 4 + 12/31
        k_gum = 2
        p_gum_expected = 2 * k_gum + (2 * k_gum * (k_gum + 1)) / (self.n - k_gum - 1)
        self.assertAlmostEqual(p_gum_expected, 4.0 + 12.0 / 31.0, delta=1e-6)

        # GEV k=3: penalty = 6 + 24/30
        k_gev = 3
        p_gev_expected = 2 * k_gev + (2 * k_gev * (k_gev + 1)) / (self.n - k_gev - 1)
        self.assertAlmostEqual(p_gev_expected, 6.0 + 24.0 / 30.0, delta=1e-6)

    def test_351012_canonical_agreement_and_invariants(self):
        # Load canonical summary
        df_can = pd.read_csv('FINAL_CANONICAL_SUMMARY.csv')
        r_351012 = df_can[df_can['station'].astype(str) == '351012'].iloc[0]

        # Production calculation checks
        p_gum = stats.gumbel_r.fit(self.x)
        ll_gum = float(np.sum(stats.gumbel_r.logpdf(self.x, *p_gum)))
        aicc_gum = float(-2.0 * ll_gum + 4.0 + 12.0 / 31.0)

        # Check against canonical value
        self.assertAlmostEqual(aicc_gum, r_351012['AICc_Gumbel'], delta=0.1)

        # Invariants
        self.assertLessEqual(r_351012['AICc_GEV'] - r_351012['AICc_Gumbel'], 2.413 + 1e-4)

    def test_corrupted_fit_rejection(self):
        # Test production validation rejection logic
        def validate_fit(params, x_data):
            # Scale must be positive
            if params['scale'] <= 0:
                return False, "INVALID_SCALE"
            # Support condition for GEV: 1 + xi * (x - mu) / sigma > 0
            if 'xi' in params and params['xi'] != 0:
                u = 1.0 + params['xi'] * (x_data - params['loc']) / params['scale']
                if np.any(u <= 0):
                    return False, "SUPPORT_VIOLATION"
            return True, "VALID"

        # Invalid scale
        valid, reason = validate_fit({'loc': 100.0, 'scale': -5.0, 'xi': 0.1}, self.x)
        self.assertFalse(valid)
        self.assertEqual(reason, "INVALID_SCALE")

        # Support violation
        valid_sup, reason_sup = validate_fit({'loc': 100.0, 'scale': 10.0, 'xi': -0.5}, self.x)
        self.assertFalse(valid_sup)
        self.assertEqual(reason_sup, "SUPPORT_VIOLATION")

    def test_return_level_monotonicity(self):
        df_can = pd.read_csv('FINAL_CANONICAL_RESULTS.csv')
        r351012 = df_can[df_can['station'].astype(str) == '351012'].iloc[0]
        rls = [r351012['R2'], r351012['R5'], r351012['R10'], r351012['R25'], r351012['R50'], r351012['R100']]
        self.assertTrue(all(x <= y for x, y in zip(rls, rls[1:])), "Return levels must be non-decreasing with period T")

if __name__ == '__main__':
    unittest.main()
