import unittest

import pandas as pd

from paper3core.metrics import seasonal_metrics


class SeasonalMetricTests(unittest.TestCase):
    def test_primary_metrics_use_only_complete_common_calendar_season(self):
        """Catches partial-season totals and spell metrics built on dropped dates."""
        dates = pd.date_range("2001-05-01", "2001-10-31", freq="D")
        values = [0.0, 2.0, 5.0] + [0.0] * (len(dates) - 3)
        frame = pd.DataFrame({"A": values}, index=dates)
        result = seasonal_metrics(frame, climate_years=[2001], wet_threshold=1.0)
        row = result.iloc[0]

        self.assertEqual(row.PRCPTOT, 7.0)
        self.assertAlmostEqual(row.wet_day_frequency_pct, 200.0 / 184.0)
        self.assertAlmostEqual(row.SDII, 3.5)
        self.assertEqual(row.Rx1day, 5.0)
        self.assertEqual(row.CDD, 181)


if __name__ == "__main__":
    unittest.main()
