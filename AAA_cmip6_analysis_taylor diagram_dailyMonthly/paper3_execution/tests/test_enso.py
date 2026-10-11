import unittest

import numpy as np
import pandas as pd

from paper3core.enso import (
    classify_management_seasons,
    parse_noaa_oni_html,
    persistent_episode_sign,
)


class ENSOClassificationTests(unittest.TestCase):
    def test_episode_requires_five_consecutive_overlapping_seasons(self):
        """Catches threshold-only labels that ignore the persistence rule."""
        dates = pd.date_range("2000-01-01", periods=12, freq="MS")
        index = pd.Series(
            [0.6, 0.7, 0.8, 0.7, 0.6, 0.4, 0.3, -0.6, -0.7, -0.8, -0.6, -0.4],
            index=dates,
        )
        signs = persistent_episode_sign(index, threshold=0.5, minimum_run=5)

        np.testing.assert_array_equal(signs.iloc[:5], np.ones(5, dtype=np.int8))
        np.testing.assert_array_equal(signs.iloc[5:], np.zeros(7, dtype=np.int8))

    def test_management_season_uses_strict_majority_episode_membership(self):
        """Catches classifying a season from its mean while ignoring membership."""
        dates = pd.date_range("2000-04-01", periods=8, freq="MS")
        index = pd.DataFrame(
            {
                "index_c": np.linspace(0.6, 1.3, 8),
                "episode_sign": np.ones(8, dtype=np.int8),
            },
            index=dates,
        )
        result = classify_management_seasons(index, climate_years=[2000])
        rainy = result[(result.season_type == "RAINY") & (result.climate_year == 2000)]

        self.assertEqual(rainy.iloc[0].enso_phase, "EL_NINO")
        self.assertEqual(int(rainy.iloc[0].n_overlapping_windows), 8)

    def test_noaa_v6_table_is_parsed_to_centred_months(self):
        """Catches a shifted ONI season-to-month mapping or wrong table selection."""
        path = (
            r"C:\MyPython\AAA_cmip6_analysis_taylor diagram_dailyMonthly"
            r"\paper3_execution\inputs\enso\noaa_cpc_oni_ersstv6_2026-09-01.html"
        )
        parsed = parse_noaa_oni_html(path)
        row = parsed.loc[parsed.date == pd.Timestamp("1982-10-01")].iloc[0]

        self.assertEqual(row.season, "SON")
        self.assertEqual(row.oni_c, 1.8)
        self.assertEqual(row.episode_sign, 1)


if __name__ == "__main__":
    unittest.main()
