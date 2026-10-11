import unittest

import numpy as np
import pandas as pd

from paper3core.qdm import crossfit_qdm, midrank_probabilities


class QDMTests(unittest.TestCase):
    def test_tied_target_values_receive_empirical_midrank(self):
        """Catches assigning every tie the last plotting position in its run."""
        probabilities = midrank_probabilities(np.array([10.0, 10.0, 10.0, 20.0]))
        np.testing.assert_allclose(probabilities, [0.375, 0.375, 0.375, 0.875])

    def test_target_observations_do_not_change_their_crossfit_outputs(self):
        """Catches target-fold observations leaking into QDM calibration."""
        dates = pd.date_range("2001-01-01", periods=40, freq="D")
        climate_year = pd.Series(np.repeat([2001, 2002], 20), index=dates)
        model = pd.Series(np.linspace(0.0, 20.0, 40), index=dates)
        observed = pd.Series(np.linspace(0.0, 30.0, 40), index=dates)
        blocks = [(2001, 2001), (2002, 2002)]

        baseline, _ = crossfit_qdm(
            observed, model, climate_year=climate_year, blocks=blocks,
            wet_threshold=1.0, group_by_month=False,
        )
        modified = observed.copy()
        modified.loc[climate_year == 2001] = 9999.0
        changed, _ = crossfit_qdm(
            modified, model, climate_year=climate_year, blocks=blocks,
            wet_threshold=1.0, group_by_month=False,
        )

        np.testing.assert_allclose(
            baseline.loc[climate_year == 2001],
            changed.loc[climate_year == 2001],
            equal_nan=True,
        )

    def test_sparse_month_uses_declared_adjacent_month_calibration_pool(self):
        """Catches silently lowering the wet-day evidence gate for dry months."""
        dates = pd.date_range("2000-01-01", "2009-12-31", freq="D")
        observed = pd.Series(2.0, index=dates)
        model = pd.Series(1.5, index=dates)
        january = dates.month == 1
        observed.loc[january] = 0.0
        model.loc[january] = 0.0
        observed.loc[january & (dates.day <= 1)] = 2.0
        model.loc[january & (dates.day <= 1)] = 1.5
        climate_year = pd.Series(dates.year, index=dates)

        _, diagnostics = crossfit_qdm(
            observed,
            model,
            climate_year=climate_year,
            blocks=[(2000, 2004), (2005, 2009)],
            min_wet_days=20,
            sparse_month_fallback="adjacent_3_month_pool",
        )
        january_rows = diagnostics[diagnostics["month"] == 1]
        self.assertTrue(january_rows["sparse_fallback_used"].all())
        self.assertTrue((january_rows["calibration_months"] == "12,1,2").all())


if __name__ == "__main__":
    unittest.main()
