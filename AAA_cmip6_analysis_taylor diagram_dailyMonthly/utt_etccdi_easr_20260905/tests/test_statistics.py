"""Behavioral regression tests for the Uttaradit ETCCDI trend pipeline.

The target is the retained original until the revised replacement exists.  This
makes the exact test command a documented red/green check rather than a source
inspection exercise.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


TASK_ROOT = Path(__file__).resolve().parents[1]
REVISED = TASK_ROOT / "Uttaradit_ETCCDI_MK_MMK2004_Sen_IDW_Q3_fixed.py"
ORIGINAL = Path(
    r"C:\MyPython\CMIP6Uttaradit\Data_Uttaradit"
    r"\Uttaradit_ETCCDI_MK_MMK2004_Sen_IDW_Q3.py"
)
TARGET = REVISED if REVISED.exists() else ORIGINAL


def load_target():
    spec = importlib.util.spec_from_file_location("utt_pipeline_under_test", TARGET)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # Register the module before execution: dataclasses resolve postponed
    # annotations through sys.modules during class decoration.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


PIPELINE = load_target()


def complete_year(year: int, values: float | np.ndarray) -> pd.DataFrame:
    """Build a valid daily one-station annual fixture without production helpers."""
    dates = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
    if np.isscalar(values):
        values = np.full(len(dates), float(values))
    return pd.DataFrame({"S1": np.asarray(values, dtype=float)}, index=dates)


class TestETCCDIPipeline(unittest.TestCase):
    """Each test names the realistic defect that must be prevented."""

    def test_rx1day_is_calculated_for_a_complete_year(self):
        """Defect: an undefined finite-mask crashes every valid annual index run."""
        daily = complete_year(2001, 0.0)
        daily.loc[pd.Timestamp("2001-08-01"), "S1"] = 73.5
        result = PIPELINE.annual_extreme_indices(daily, {"S1": (10.0, 20.0)})
        self.assertAlmostEqual(float(result.loc[("S1", 2001), "Rx1day"]), 73.5)

    def test_percentile_indices_follow_fixed_wet_day_thresholds(self):
        """Defect: R95p/R99p must be annual sums strictly above supplied thresholds."""
        daily = complete_year(2001, 0.0)
        daily.loc[pd.Timestamp("2001-01-01"), "S1"] = 10.0
        daily.loc[pd.Timestamp("2001-01-02"), "S1"] = 11.0
        daily.loc[pd.Timestamp("2001-01-03"), "S1"] = 20.0
        daily.loc[pd.Timestamp("2001-01-04"), "S1"] = 21.0
        result = PIPELINE.annual_extreme_indices(daily, {"S1": (10.0, 20.0)})
        row = result.loc[("S1", 2001)]
        self.assertAlmostEqual(float(row["PRCPTOT"]), 62.0)
        self.assertAlmostEqual(float(row["SDII"]), 15.5)
        self.assertAlmostEqual(float(row["R95p"]), 52.0)
        self.assertAlmostEqual(float(row["R99p"]), 21.0)

    def test_missing_calendar_day_breaks_dry_spell(self):
        """Defect: absent calendar dates must not join separate CDD/CWD runs."""
        daily = complete_year(2001, 1.0)
        for day in ("2001-01-01", "2001-01-02", "2001-01-04", "2001-01-05"):
            daily.loc[pd.Timestamp(day), "S1"] = 0.0
        daily = daily.drop(pd.Timestamp("2001-01-03"))
        result = PIPELINE.annual_extreme_indices(daily, {"S1": (10.0, 20.0)})
        self.assertEqual(float(result.loc[("S1", 2001), "CDD"]), 2.0)

    def test_constant_series_is_a_valid_non_significant_mk_result(self):
        """Defect: tied constant annual indices were incorrectly called insufficient."""
        years = np.arange(1981, 2015, dtype=float)
        result = PIPELINE.standard_mk(years, np.full(len(years), 7.0))
        self.assertEqual(result["S"], 0.0)
        self.assertEqual(result["Z"], 0.0)
        self.assertEqual(result["p"], 1.0)
        self.assertEqual(result["trend"], "No significant trend")
        self.assertEqual(result["slope"], 0.0)

    def test_sen_slope_uses_actual_year_spacing(self):
        """Defect: removed annual years must not change a per-year Sen slope."""
        slope = PIPELINE.sen_slope_with_years(
            np.array([2000.0, 2001.0, 2004.0]),
            np.array([0.0, 1.0, 4.0]),
        )
        self.assertAlmostEqual(slope, 1.0)

    def test_sen_confidence_interval_matches_scipy_reference(self):
        """Defect: rank indexing must return the documented 95 percent CI bounds."""
        years = np.array([2000, 2001, 2002, 2004, 2005, 2007, 2008, 2010], dtype=float)
        values = np.array([2.0, 4.0, 3.0, 7.0, 8.0, 9.0, 13.0, 14.0])
        reference = stats.theilslopes(values, years, alpha=0.95)
        low, high = PIPELINE.sen_confidence_interval(years, values)
        self.assertAlmostEqual(low, float(reference.low_slope), places=12)
        self.assertAlmostEqual(high, float(reference.high_slope), places=12)

    def test_yue_wang_handles_zero_variance_detrended_residuals(self):
        """Defect: a perfect linear trend has zero residual variance, not invalid MMK output."""
        years = np.arange(1981, 2015, dtype=float)
        values = 2.5 * (years - years[0]) + 10.0
        result = PIPELINE.yue_wang_2004_mmk(years, values)
        self.assertEqual(result["ESS_factor_n_over_nstar"], 1.0)
        self.assertEqual(result["N_eff"], float(len(years)))
        self.assertAlmostEqual(result["MMK_p"], result["p"], places=14)

    def test_idw_aligns_station_values_by_station_identifier(self):
        """Defect: Series index alignment erased all station values before IDW."""
        coords = pd.DataFrame(
            {
                "station": ["A", "B", "C"],
                "latitude": [0.0, 0.0, 1.0],
                "longitude": [0.0, 1.0, 0.0],
            }
        )
        values = pd.Series({"A": 10.0, "B": 20.0, "C": 30.0})
        _, _, grid = PIPELINE.idw_grid(coords, values, nx=2, ny=2, padding=0.0)
        self.assertAlmostEqual(float(grid[0, 0]), 10.0, places=12)

    def test_idw_grid_can_cover_supplied_boundary_extent(self):
        """Defect: station-only bounds left valid northern polygon areas unfilled."""
        coords = pd.DataFrame(
            {
                "station": ["A", "B", "C"],
                "latitude": [0.0, 0.0, 1.0],
                "longitude": [0.0, 1.0, 0.0],
            }
        )
        values = pd.Series({"A": 10.0, "B": 20.0, "C": 30.0})
        _, lat, grid = PIPELINE.idw_grid(
            coords,
            values,
            nx=4,
            ny=4,
            padding=0.0,
            grid_bounds=(-0.5, 1.5, -1.0, 2.0),
        )
        self.assertAlmostEqual(float(lat.min()), -1.0, places=12)
        self.assertAlmostEqual(float(lat.max()), 2.0, places=12)
        self.assertTrue(np.isfinite(grid).all())

    def test_boundary_mask_removes_idw_values_outside_polygon(self):
        """Defect: a boundary shapefile must constrain map-only IDW surfaces."""
        lon, lat = np.meshgrid(np.array([0.0, 0.5, 1.0]), np.array([0.0, 0.5, 1.0]))
        grid = np.ones_like(lon)
        square = np.array([[0.0, 0.0], [0.75, 0.0], [0.75, 0.75], [0.0, 0.75]])
        result = PIPELINE.mask_grid_to_boundary(lon, lat, grid, [square])
        self.assertEqual(float(result[1, 1]), 1.0)
        self.assertTrue(np.isnan(result[2, 2]))

    def test_coordinate_reader_accepts_station_id_schema(self):
        """Defect: supplied Station_ID coordinate workbooks were rejected unnecessarily."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "coords.xlsx"
            pd.DataFrame(
                {
                    "Station_ID": [351001, 351002],
                    "latitude": [17.2, 17.3],
                    "longitude": [100.1, 100.2],
                    "Elevation": [50.0, 65.0],
                }
            ).to_excel(path, index=False)
            result = PIPELINE.read_coordinates(path)
        self.assertEqual(result["station"].tolist(), ["351001", "351002"])
        self.assertIn("elevation", result.columns)

    def test_coordinate_reader_accepts_csv_schema(self):
        """Defect: portable provincial datasets may provide coordinates as CSV."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "coords.csv"
            pd.DataFrame(
                {
                    "station": [465001, 465002],
                    "latitude": [13.1, 13.2],
                    "longitude": [99.8, 99.9],
                }
            ).to_csv(path, index=False)
            result = PIPELINE.read_coordinates(path)
        self.assertEqual(result["station"].tolist(), ["465001", "465002"])

    def test_duplicate_daily_dates_are_rejected_not_silently_dropped(self):
        """Defect: duplicate daily input was silently retained as an arbitrary first row."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rain.csv"
            pd.DataFrame(
                {
                    "YEAR": [2001, 2001],
                    "MONTH": [1, 1],
                    "DAY": [1, 1],
                    "351001": [1.0, 99.0],
                }
            ).to_csv(path, index=False)
            with self.assertRaises(ValueError):
                PIPELINE.load_daily_csv(path)

    def test_empty_export_column_is_removed_but_real_columns_remain(self):
        """Defect: trailing spreadsheet export columns inflated station manifests."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rain.csv"
            pd.DataFrame(
                {
                    "YEAR": [2001, 2001],
                    "MONTH": [1, 1],
                    "DAY": [1, 2],
                    "S1": [0.0, 1.0],
                    "Unnamed: 4": [np.nan, np.nan],
                }
            ).to_csv(path, index=False)
            loaded = PIPELINE.load_daily_csv(path)
        self.assertEqual(list(loaded.columns), ["S1"])

    def test_ambiguous_cmip6_match_is_rejected(self):
        """Defect: duplicate model-period input must never be chosen by traversal order."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model_dir = root / "ACCESS-ESM1-5"
            model_dir.mkdir()
            for suffix in ("a", "b"):
                (model_dir / f"bc_pr_day_ACCESS-ESM1-5_historical_{suffix}.csv").touch()
            with self.assertRaises(ValueError):
                PIPELINE.discover_bc_model_files(root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
