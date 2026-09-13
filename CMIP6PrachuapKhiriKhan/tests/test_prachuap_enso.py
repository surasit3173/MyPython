import unittest
import os
import pandas as pd
import numpy as np

class TestPrachuapENSOAnalysis(unittest.TestCase):
    def setUp(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.tables_dir = os.path.join(self.base_dir, "output", "tables")
        self.figures_dir = os.path.join(self.base_dir, "output", "figures")
        self.manifests_dir = os.path.join(self.base_dir, "output", "manifests")

    def test_output_files_exist(self):
        expected_tables = [
            "enso_classification_summary.csv",
            "enso_episode_catalog.csv",
            "enso_phase_sample_sizes.csv",
            "observed_seasonal_indices.csv",
            "all_source_seasonal_indices.csv",
            "enso_response_summary.csv",
            "enso_asymmetry_summary.csv",
            "qdm_relative_change_pe_enso.csv"
        ]
        for t in expected_tables:
            path = os.path.join(self.tables_dir, t)
            self.assertTrue(os.path.exists(path), f"Missing output table: {t}")

        expected_figures = [
            "Figure1_ENSO_Classification_Timeline.png",
            "Figure2_Seasonal_PRCPTOT_ENSO_Response.png",
            "Figure3_QDM_Bias_Correction_ENSO_Shift.png"
        ]
        for fig in expected_figures:
            path = os.path.join(self.figures_dir, fig)
            self.assertTrue(os.path.exists(path), f"Missing output figure: {fig}")

    def test_no_uttaradit_contamination(self):
        """Audit output tables for Uttaradit station IDs (e.g. 480000 series / Uttaradit text)."""
        for fname in os.listdir(self.tables_dir):
            if fname.endswith(".csv"):
                path = os.path.join(self.tables_dir, fname)
                df = pd.read_csv(path)
                content = df.to_string()
                self.assertNotIn("Uttaradit", content, f"Contamination found in {fname}")
                self.assertNotIn("uttaradit", content, f"Contamination found in {fname}")
                # Uttaradit station IDs start with 480...
                self.assertNotIn("480001", content, f"Uttaradit station ID found in {fname}")

    def test_enso_sample_sizes(self):
        path = os.path.join(self.tables_dir, "enso_phase_sample_sizes.csv")
        df = pd.read_csv(path)
        obs_df = df[df["source_type"] == "OBSERVED"]
        hotdry_el = obs_df[(obs_df["season_type"] == "HOT_DRY") & (obs_df["enso_phase"] == "EL_NINO")]["n_seasons"].iloc[0]
        rainy_el = obs_df[(obs_df["season_type"] == "RAINY") & (obs_df["enso_phase"] == "EL_NINO")]["n_seasons"].iloc[0]
        self.assertEqual(hotdry_el, 8)
        self.assertEqual(rainy_el, 6)

if __name__ == "__main__":
    unittest.main()
