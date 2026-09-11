import unittest

import pandas as pd

from paper3core.calendar import (
    extract_complete_seasons,
    max_consecutive_spell,
    rolling_sum_max,
)


class CalendarSafeMetricsTests(unittest.TestCase):
    def test_missing_day_breaks_spell_and_rolling_window(self):
        """Catches the defect where dropping NaNs stitches two wet runs together."""
        dates = list(pd.date_range("2001-01-01", periods=5, freq="D"))
        dates += list(pd.date_range("2001-01-07", periods=5, freq="D"))
        series = pd.Series(10.0, index=pd.DatetimeIndex(dates))

        self.assertEqual(max_consecutive_spell(series, wet=True), 5)
        self.assertEqual(rolling_sum_max(series, window=5), 50.0)

    def test_removed_february_29_is_adjacent_on_common_365_day_calendar(self):
        """Catches treating a deliberately removed leap day as a data gap."""
        dates = pd.to_datetime(
            ["2000-02-27", "2000-02-28", "2000-03-01", "2000-03-02", "2000-03-03"]
        )
        series = pd.Series(2.0, index=dates)

        self.assertEqual(max_consecutive_spell(series, wet=True), 5)
        self.assertEqual(rolling_sum_max(series, window=5), 10.0)

    def test_season_completeness_excludes_missing_day_but_not_february_29(self):
        """Catches partial seasons and artificial leap-day requirements."""
        dates = pd.date_range("2000-01-01", "2001-12-31", freq="D")
        frame = pd.DataFrame({"A": 1.0}, index=dates)
        complete = extract_complete_seasons(frame, climate_years=[2000])

        rainy = complete[complete.season_type == "RAINY"].iloc[0]
        hot_dry = complete[complete.season_type == "HOT_DRY"].iloc[0]
        self.assertEqual((rainy.expected_days, rainy.valid_days, rainy.complete), (184, 184, True))
        self.assertEqual((hot_dry.expected_days, hot_dry.valid_days, hot_dry.complete), (181, 181, True))

        frame.loc["2001-01-15", "A"] = float("nan")
        incomplete = extract_complete_seasons(frame, climate_years=[2000])
        hot_dry = incomplete[incomplete.season_type == "HOT_DRY"].iloc[0]
        self.assertEqual((hot_dry.valid_days, hot_dry.complete), (180, False))


if __name__ == "__main__":
    unittest.main()
