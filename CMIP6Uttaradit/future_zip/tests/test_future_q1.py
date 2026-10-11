"""
Known-answer and guard tests for src/future_q1.py.

Run:  pytest -q tests/test_future_q1.py
These tests use only tiny synthetic inputs (no large data needed) except the
optional end-to-end test, which is skipped unless TFPW_TEST_SOURCE / TFPW_TEST_GIS
point at a staged data folder.
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src import future_q1 as F
from src.geo import lonlat_to_utm


# --------------------------------------------------------------------------- #
# Pure-function known-answer tests
# --------------------------------------------------------------------------- #
def test_bh_fdr_matches_bh1995_example():
    # Benjamini & Hochberg (1995) worked example -> 4 rejections at alpha=0.05
    p = np.array([0.0001, 0.0004, 0.0019, 0.0095, 0.0201, 0.0278, 0.0298,
                  0.0344, 0.0459, 0.3240, 0.4262, 0.5719, 0.6528, 0.7590, 1.0])
    rej = F._fdr_bh(p, 0.05)
    assert int(rej.sum()) == 4


def test_bh_fdr_handles_nan_and_empty():
    assert F._fdr_bh(np.array([np.nan, np.nan]), 0.05).sum() == 0
    assert F._fdr_bh(np.array([]), 0.05).size == 0


def test_sign_agreement():
    assert F._sign_agreement(pd.Series([1.0, 1.0, 1.0, -1.0])) == 0.75
    assert F._sign_agreement(pd.Series([-2.0, -1.0, -5.0])) == 1.0
    assert np.isnan(F._sign_agreement(pd.Series([np.nan, np.nan])))


def test_deg_min_formatter():
    assert F._deg_min(99.6, True) == "99\u00b036\u2032E"
    assert F._deg_min(12.0, False) == "12\u00b000\u2032N"
    # rounding minute carry
    assert F._deg_min(99.99999, True) == "100\u00b000\u2032E"


def test_utm_roundtrip():
    e, n = lonlat_to_utm(99.6, 12.0, 99.0)
    lon, lat = F.utm_to_lonlat(e, n, 99.0)
    assert abs(float(lon) - 99.6) < 1e-6
    assert abs(float(lat) - 12.0) < 1e-6


def test_looks_projected():
    assert F._looks_projected((516097.0, 1210999.0, 612334.0, 1397914.0))
    assert not F._looks_projected((99.1, 11.0, 100.0, 12.6))


def test_column_alias_resolver():
    assert F._find_col(["station ", "latitude", "longitude"], F.COORD_ID_ALIASES) == "station "
    assert F._find_col(["สถานี", "ละติจูด", "ลองจิจูด"], F.COORD_LAT_ALIASES) == "ละติจูด"


def test_index_computation_known_values():
    # a controlled daily series: 10 wet days of 5 mm + 1 day of 60 mm in 2015
    idx = pd.date_range("2015-01-01", periods=20, freq="D")
    vals = np.zeros(20)
    vals[:10] = 5.0
    vals[10] = 60.0
    s = pd.Series(vals, index=idx)
    th = {"p95": 50.0, "p99": 55.0}
    out = F._station_yearly_indices(s, th)
    row = out.iloc[0]
    assert row["PRCPTOT"] == pytest.approx(110.0)      # 10*5 + 60
    assert row["R50mm"] == 1
    assert row["Rx1day"] == pytest.approx(60.0)
    assert row["R95p"] == pytest.approx(60.0)           # only the 60mm day > p95


def test_scenario_and_model_token_detection():
    assert F._scenario_from_name(Path("bc_pr_day_CESM2_ssp585_x.csv")) == "ssp585"
    assert F._scenario_from_name(Path("observed_rain.csv")) is None
    assert F._has_model_token(Path("pr_day_CESM2_historical_r11i1p1f1.csv"))
    assert not F._has_model_token(Path("Observed_Rain_daily.xlsx"))


def test_model_name_from_cmip6_filename():
    # model parsed from CMIP6 pattern beats a messy parent-folder name
    p = Path("/x/EC-Earth3_CSV_FILE/bc_pr_day_EC-Earth3_ssp245_r1i1p1f1_gr.csv")
    assert F._model_from_name(p, "ssp245") == "EC-Earth3"
    p2 = Path("/x/MRI-ESM2-0/pr_day_MRI-ESM2-0_historical_r1i1p1f1_gn.csv")
    assert F._model_from_name(p2, None) == "MRI-ESM2-0"
    # fallback: parent folder with generic suffix stripped
    p3 = Path("/x/CanESM5_data/rain_ssp585_series.csv")
    assert F._model_from_name(p3, "ssp585") == "CanESM5"


# --------------------------------------------------------------------------- #
# Optional end-to-end test (needs staged data)
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(
    not (os.environ.get("TFPW_TEST_SOURCE") and os.environ.get("TFPW_TEST_GIS")),
    reason="set TFPW_TEST_SOURCE and TFPW_TEST_GIS to run the end-to-end test")
def test_end_to_end_cube_known_answer():
    src = Path(os.environ["TFPW_TEST_SOURCE"])
    gis = Path(os.environ["TFPW_TEST_GIS"])
    cube = F.compute_yearly_index_cube(src, gis)
    summ = F.summarize_projections(cube["yearly"], cube["baseline"])
    reg = summ["regional"]
    row = reg[(reg["index"] == "PRCPTOT") & (reg["scenario"] == "ssp585")
              & (reg["window"] == "Late")]
    assert not row.empty
    # regression guard: value established by validated run
    assert row["regional_delta_pct_mean"].iloc[0] == pytest.approx(-28.802, abs=0.05)
