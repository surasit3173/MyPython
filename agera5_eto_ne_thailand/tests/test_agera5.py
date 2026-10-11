"""Point extraction and unit handling on a synthetic AgERA5-like file."""
import zipfile
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from etoeval import agera5


def _field() -> xr.DataArray:
    lat = np.round(np.arange(14.0, 15.01, 0.1), 2)
    lon = np.round(np.arange(102.0, 103.01, 0.1), 2)
    vals = 300.0 + 10 * lat[:, None] + 1 * lon[None, :]  # plane in K -> bilinear and IDW well defined
    return xr.DataArray(vals, coords={"lat": lat, "lon": lon}, dims=("lat", "lon"), attrs={"units": "K"})


def test_point_values_plane() -> None:
    da = _field()
    near, bil, idw = agera5.point_values(da, 14.53, 102.47)
    assert near == pytest.approx(300 + 10 * 14.5 + 102.5)
    assert bil == pytest.approx(300 + 10 * 14.53 + 102.47, abs=1e-9)
    assert abs(idw - bil) < 1.0


def test_bilinear_renormalises_over_missing_cells() -> None:
    da = _field().copy()
    da[5, 5] = np.nan
    _, bil, _ = agera5.point_values(da, 14.52, 102.52)
    assert np.isfinite(bil)


def test_unit_conversion() -> None:
    assert agera5._convert_units("tmax_c", np.array([303.15]), "K")[0] == pytest.approx(30.0)
    assert agera5._convert_units("vp_kpa", np.array([25.0]), "hPa")[0] == pytest.approx(2.5)
    assert agera5._convert_units("rs_mj", np.array([2.0e7]), "J m-2 d-1")[0] == pytest.approx(20.0)


def test_date_from_filename() -> None:
    d = agera5._date_from_name("Temperature-Air-2m-Max-24h_C3S-glob-agric_AgERA5_19790101_final-v2.0.nc")
    assert str(d.date()) == "1979-01-01"
