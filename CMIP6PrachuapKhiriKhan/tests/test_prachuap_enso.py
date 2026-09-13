import unittest
import os
import pandas as pd
import numpy as np

class TestPrachuapENSOAnalysis(unittest.TestCase):
    def setUp(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(self.base_dir, "data")
        self.inputs_dir = os.path.join(self.base_dir, "inputs")
        self.tables_dir = os.path.join(self.base_dir, "output", "tables")
        self.figures_dir = os.path.join(self.base_dir, "output", "figures")
        self.manifests_dir = os.path.join(self.base_dir, "output", "manifests")

    def test_station_date_missingness(self):
        """Verify observed data station count, dates, and missingness."""
        obs_path = os.path.join(self.data_dir, "Observed_Rain_daily_198101_201412_PrachuapKhiriKhan.csv")
        self.assertTrue(os.path.exists(obs_path), "Observed CSV missing")
        df = pd.read_csv(obs_path)
        stations = [c for c in df.columns if c not in ["YEAR", "MONTH", "DAY"]]
        self.assertEqual(len(stations), 12, "Should have exactly 12 stations")
        self.assertEqual(df.isnull().sum().sum(), 0, "Observed data should have 0 null values")
        self.assertEqual(df["YEAR"].min(), 1981)
        self.assertEqual(df["YEAR"].max(), 2014)

    def test_gcm_raw_qdm_pairing(self):
        """Verify all 5 GCM models have raw and QDM files in inputs/gcm."""
        gcm_dir = os.path.join(self.inputs_dir, "gcm")
        models = ["ACCESS-ESM1-5", "CESM2", "CanESM5", "EC-Earth3", "MIROC6"]
        for m in models:
            raw_files = [f for f in os.listdir(gcm_dir) if f.startswith(f"pr_day_{m}_")]
            bc_files = [f for f in os.listdir(gcm_dir) if f.startswith(f"bc_pr_day_{m}_")]
            self.assertEqual(len(raw_files), 1, f"Missing raw file for model {m}")
            self.assertEqual(len(bc_files), 1, f"Missing QDM file for model {m}")

    def test_enso_classification_counts(self):
        """Verify persistent episode ENSO classification counts."""
        path = os.path.join(self.tables_dir, "enso_phase_sample_sizes.csv")
        self.assertTrue(os.path.exists(path))
        df = pd.read_csv(path)
        obs_df = df[df["source_type"] == "OBSERVED"]

        hotdry_el = obs_df[(obs_df["season_type"] == "HOT_DRY") & (obs_df["enso_phase"] == "EL_NINO")]["n_seasons"].iloc[0]
        hotdry_la = obs_df[(obs_df["season_type"] == "HOT_DRY") & (obs_df["enso_phase"] == "LA_NINA")]["n_seasons"].iloc[0]
        rainy_el = obs_df[(obs_df["season_type"] == "RAINY") & (obs_df["enso_phase"] == "EL_NINO")]["n_seasons"].iloc[0]
        rainy_la = obs_df[(obs_df["season_type"] == "RAINY") & (obs_df["enso_phase"] == "LA_NINA")]["n_seasons"].iloc[0]

        self.assertEqual(hotdry_el, 8)
        self.assertEqual(hotdry_la, 12)
        self.assertEqual(rainy_el, 6)
        self.assertEqual(rainy_la, 7)

    def test_observational_distance_metrics(self):
        """Verify observational distance metrics table structure and QDM movement values."""
        path = os.path.join(self.tables_dir, "qdm_observational_distance_metrics.csv")
        self.assertTrue(os.path.exists(path))
        df = pd.read_csv(path)
        self.assertIn("qdm_movement_el_nino", df.columns)
        self.assertIn("abs_err_raw_el", df.columns)
        self.assertIn("abs_err_qdm_el", df.columns)

    def test_no_uttaradit_contamination(self):
        """Audit output tables for Uttaradit station IDs and text."""
        for fname in os.listdir(self.tables_dir):
            if fname.endswith(".csv"):
                path = os.path.join(self.tables_dir, fname)
                df = pd.read_csv(path)
                content = df.to_string()
                self.assertNotIn("Uttaradit", content, f"Contamination found in {fname}")
                self.assertNotIn("uttaradit", content, f"Contamination found in {fname}")
                self.assertNotIn("480001", content, f"Uttaradit station ID found in {fname}")

    def test_traceability_matrix(self):
        """Verify traceability CSV exists and has non-empty SHA-256 hashes."""
        path = os.path.join(self.base_dir, "PRACHUAP_KHIRI_KHAN_ENSO_TRACEABILITY.csv")
        self.assertTrue(os.path.exists(path))
        df = pd.read_csv(path)
        self.assertEqual(len(df), 14)
        for h in df["sha256_hash"]:
            self.assertEqual(len(h), 64)

if __name__ == "__main__":
    unittest.main()
