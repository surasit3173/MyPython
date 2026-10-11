"""FAO-56 implementation against the worked examples of Allen et al. (1998)."""
import numpy as np
import pytest

from etoeval import fao56


def test_example17_bangkok_april_monthly_eto() -> None:
    """FAO-56 Example 17 (Bangkok, April, monthly data): ETo = 5.72 mm/day."""
    lat = 13 + 44 / 60
    j = fao56.mid_month_doy(4)
    ra = fao56.extraterrestrial_radiation(lat, j)
    n_max = fao56.daylight_hours(lat, j)
    rs = fao56.solar_radiation_angstrom(8.5, n_max, ra, fao56.angstrom_fao56())
    eto = fao56.eto_penman_monteith(34.8, 25.6, 2.85, 2.0, rs, ra, 2.0, 0.14 * (30.2 - 29.2))
    assert float(ra) == pytest.approx(38.06, abs=0.05)
    assert float(n_max) == pytest.approx(12.31, abs=0.03)
    assert float(eto) == pytest.approx(5.72, abs=0.02)


def test_example8_extraterrestrial_radiation() -> None:
    """FAO-56 Example 8: 20 deg S, 3 September -> Ra = 32.2 MJ m-2 d-1, N = 11.7 h."""
    assert float(fao56.extraterrestrial_radiation(-20.0, 246)) == pytest.approx(32.2, abs=0.1)
    assert float(fao56.daylight_hours(-20.0, 246)) == pytest.approx(11.7, abs=0.1)


def test_wind_height_conversion_10m() -> None:
    assert float(fao56.wind_to_2m(1.0, 10.0)) == pytest.approx(0.748, abs=0.001)


def test_soil_heat_flux_fallback() -> None:
    g = fao56.soil_heat_flux_monthly(np.array([20.0]), np.array([22.0]), np.array([np.nan]))
    assert float(g[0]) == pytest.approx(0.14 * 2.0)
