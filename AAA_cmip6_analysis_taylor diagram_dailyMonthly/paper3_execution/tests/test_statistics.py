import unittest

import pandas as pd

from paper3core.statistics import (
    benjamini_hochberg,
    classify_preservation,
    model_response,
    observed_response,
)


class HierarchicalStatisticsTests(unittest.TestCase):
    def test_observed_response_weights_each_station_once(self):
        rows = []
        for year, phase, a, b in [
            (2000, "NEUTRAL", 10.0, 20.0),
            (2001, "NEUTRAL", 10.0, 20.0),
            (2002, "EL_NINO", 12.0, 24.0),
            (2003, "EL_NINO", 14.0, 28.0),
        ]:
            rows.extend(
                {"climate_year": year, "enso_phase": phase, "station": station, "value": value}
                for station, value in [("A", a), ("B", b)]
            )
        estimate, entities = observed_response(
            pd.DataFrame(rows), phase="EL_NINO", minimum_seasons=2
        )
        self.assertAlmostEqual(estimate["response_pct"], 30.0)
        self.assertEqual(len(entities), 2)

    def test_model_response_collapses_duplicate_grid_signatures_before_model(self):
        rows = []
        for year, phase, multiplier in [
            (2000, "NEUTRAL", 1.0),
            (2001, "NEUTRAL", 1.0),
            (2002, "EL_NINO", 2.0),
            (2003, "EL_NINO", 2.0),
        ]:
            rows.extend(
                [
                    {"model": "M", "grid_signature": "g1", "station": "A", "climate_year": year, "enso_phase": phase, "value": 10.0 * multiplier},
                    {"model": "M", "grid_signature": "g1", "station": "B", "climate_year": year, "enso_phase": phase, "value": 10.0 * multiplier},
                    {"model": "M", "grid_signature": "g2", "station": "C", "climate_year": year, "enso_phase": phase, "value": 10.0 if phase == "NEUTRAL" else 40.0},
                ]
            )
        estimate, model_rows, grid_rows = model_response(
            pd.DataFrame(rows), phase="EL_NINO", minimum_seasons=2
        )
        self.assertAlmostEqual(estimate["response_pct"], 200.0)
        self.assertEqual(len(model_rows), 1)
        self.assertEqual(len(grid_rows), 2)

    def test_preservation_classification_has_near_zero_gate(self):
        self.assertEqual(classify_preservation(2.0, 8.0, near_zero=5.0)["category"], "INDETERMINATE_RAW_NEAR_ZERO")
        self.assertEqual(classify_preservation(-20.0, 10.0, near_zero=5.0)["category"], "REVERSED")
        self.assertEqual(classify_preservation(20.0, 10.0, near_zero=5.0)["category"], "ATTENUATED")
        self.assertEqual(classify_preservation(20.0, 30.0, near_zero=5.0)["category"], "AMPLIFIED")
        self.assertEqual(classify_preservation(20.0, 21.0, near_zero=5.0)["category"], "PRESERVED")

    def test_bh_adjustment_is_monotone_in_sorted_p_values(self):
        adjusted = benjamini_hochberg([0.01, 0.04, 0.03])
        self.assertAlmostEqual(adjusted[0], 0.03)
        self.assertAlmostEqual(adjusted[1], 0.04)
        self.assertAlmostEqual(adjusted[2], 0.04)


if __name__ == "__main__":
    unittest.main()

