import unittest

import pandas as pd

from paper3core.inference import infer_joint_phases


class EventLevelInferenceTests(unittest.TestCase):
    def test_joint_inference_resamples_seasons_and_keeps_neutral_shared(self):
        rows = []
        for year, phase, values in [
            (2000, "NEUTRAL", [10.0, 20.0]),
            (2001, "NEUTRAL", [10.0, 20.0]),
            (2002, "EL_NINO", [12.0, 24.0]),
            (2003, "EL_NINO", [12.0, 24.0]),
            (2004, "LA_NINA", [8.0, 16.0]),
            (2005, "LA_NINA", [8.0, 16.0]),
        ]:
            for station, value in zip(["A", "B"], values, strict=True):
                rows.append(
                    {"climate_year": year, "enso_phase": phase, "station": station, "value": value}
                )
        result = infer_joint_phases(
            pd.DataFrame(rows),
            source_kind="observed",
            minimum_seasons=2,
            bootstrap_repetitions=99,
            permutation_repetitions=99,
            seed=42,
        )
        self.assertAlmostEqual(result["responses"]["EL_NINO"]["response_pct"], 20.0)
        self.assertAlmostEqual(result["responses"]["LA_NINA"]["response_pct"], -20.0)
        self.assertAlmostEqual(result["asymmetry"]["phase_contrast_pct"], -40.0)
        self.assertAlmostEqual(result["asymmetry"]["neutral_centered_asymmetry_pct"], 0.0)
        self.assertEqual(result["resampling_unit"], "management-season climate year")


if __name__ == "__main__":
    unittest.main()

