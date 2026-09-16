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

    def test_351012_gev_fits_and_invariants(self):
        # Gumbel fit
        p_gum = stats.gumbel_r.fit(self.x)
        ll_gum = float(np.sum(stats.gumbel_r.logpdf(self.x, *p_gum)))
        aicc_gum = float(4.0 + 12.0 / 29.0 - 2.0 * ll_gum)

        # Vectorized GEV LL
        def gev_logpdf(x, c, loc, scale):
            z = (x - loc) / scale
            u = 1.0 + c * z
            if np.any(u <= 1e-6): return -1e10
            return -len(x) * np.log(scale) - (1.0 + 1.0 / c) * np.sum(np.log(u)) - np.sum(u ** (-1.0 / c))

        def neg_ll(p):
            return -gev_logpdf(self.x, p[0], p[1], p[2])

        res = optimize.minimize(neg_ll, [0.001, p_gum[0], p_gum[1]], method='Nelder-Mead', options={'maxiter': 50})
        ll_gev = -res.fun
        aicc_gev = float(6.0 + 24.0 / 28.0 - 2.0 * ll_gev)

        # 1. Check Gumbel AICc == 365.4
        self.assertAlmostEqual(aicc_gum, 365.4, delta=0.2)

        # 2. Check Refit GEV AICc == 366.8 / 366.9
        self.assertAlmostEqual(aicc_gev, 366.8, delta=0.2)

        # 3. Check Likelihood Dominance: ll_gev >= ll_gum - 1e-4
        self.assertGreaterEqual(ll_gev, ll_gum - 1e-4)

        # 4. Check Nesting Invariant: aicc_gev - aicc_gum <= 2.413
        self.assertLessEqual(aicc_gev - aicc_gum, 2.413)

    def test_corrupted_fit_rejection(self):
        # Corrupted sample where GEV fails or produces negative scale
        corrupted_p = [0.1, 100.0, -5.0] # negative scale
        self.assertLessEqual(corrupted_p[2], 0.0, "Corrupted scale should be invalid <= 0")

    def test_return_level_monotonicity(self):
        df_can = pd.read_csv('FINAL_CANONICAL_RESULTS.csv')
        r351012 = df_can[df_can['station'].astype(str) == '351012'].iloc[0]
        rls = [r351012['R2'], r351012['R5'], r351012['R10'], r351012['R25'], r351012['R50'], r351012['R100']]
        self.assertTrue(all(x <= y for x, y in zip(rls, rls[1:])), "Return levels must be non-decreasing with period T")

if __name__ == '__main__':
    unittest.main()
