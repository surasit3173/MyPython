import tempfile
import unittest
from pathlib import Path

import pandas as pd

from paper3core.io import load_daily


class DailyLoadingTests(unittest.TestCase):
    def test_observed_native_calendar_can_be_qc_before_common365_conversion(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "observed.csv"
            dates = pd.date_range("2000-01-01", "2000-12-31", freq="D")
            pd.DataFrame(
                {
                    "YEAR": dates.year,
                    "MONTH": dates.month,
                    "DAY": dates.day,
                    "A": 0.0,
                }
            ).to_csv(path, index=False)
            native, native_report = load_daily(
                path,
                stations=["A"],
                start_year=2000,
                end_year=2000,
                drop_february_29=False,
            )
            common, common_report = load_daily(
                path,
                stations=["A"],
                start_year=2000,
                end_year=2000,
                drop_february_29=True,
            )
            self.assertEqual(len(native), 366)
            self.assertEqual(len(common), 365)
            self.assertEqual(native_report["leap_days_removed"], 0)
            self.assertEqual(common_report["leap_days_removed"], 1)


if __name__ == "__main__":
    unittest.main()

