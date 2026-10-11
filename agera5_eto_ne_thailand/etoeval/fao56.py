"""FAO-56 Penman-Monteith reference evapotranspiration at the monthly time step.

All equations follow Allen et al. (1998), FAO Irrigation and Drainage Paper 56
(hereafter FAO-56). Equation numbers in comments refer to that publication.
Functions are vectorised over NumPy arrays and pandas Series.

References
----------
Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998). Crop evapotranspiration:
    Guidelines for computing crop water requirements. FAO Irrigation and Drainage
    Paper 56. FAO, Rome.
Glover, J., McCulloch, J.S.G. (1958). The empirical relation between solar
    radiation and hours of sunshine. Q. J. R. Meteorol. Soc. 84, 172-175.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]

SIGMA_MJ: float = 4.903e-9  # Stefan-Boltzmann constant [MJ K-4 m-2 day-1]
ALBEDO_REF: float = 0.23    # Albedo of the hypothetical grass reference [-]
GSC: float = 0.0820         # Solar constant [MJ m-2 min-1]
KNOT_TO_MS: float = 0.514444  # 1 international knot in m s-1


def _a(x: ArrayLike) -> FloatArray:
    return np.asarray(x, dtype=np.float64)


def sat_vapour_pressure(t_c: ArrayLike) -> FloatArray:
    """Saturation vapour pressure, FAO-56 Eq. 11.

    Parameters
    ----------
    t_c : array_like
        Air temperature [degC].

    Returns
    -------
    numpy.ndarray
        Saturation vapour pressure [kPa].
    """
    t = _a(t_c)
    return 0.6108 * np.exp(17.27 * t / (t + 237.3))


def slope_svp(t_c: ArrayLike) -> FloatArray:
    """Slope of the saturation vapour pressure curve, FAO-56 Eq. 13.

    Parameters
    ----------
    t_c : array_like
        Mean air temperature [degC].

    Returns
    -------
    numpy.ndarray
        Slope Delta [kPa degC-1].
    """
    t = _a(t_c)
    return 4098.0 * sat_vapour_pressure(t) / (t + 237.3) ** 2


def atmospheric_pressure(z_m: ArrayLike) -> FloatArray:
    """Atmospheric pressure from elevation, FAO-56 Eq. 7 [kPa]."""
    z = _a(z_m)
    return 101.3 * ((293.0 - 0.0065 * z) / 293.0) ** 5.26


def psychrometric_constant(p_kpa: ArrayLike) -> FloatArray:
    """Psychrometric constant, FAO-56 Eq. 8 [kPa degC-1]."""
    return 0.665e-3 * _a(p_kpa)


def mid_month_doy(month: ArrayLike) -> FloatArray:
    """Day of year representative of a month, FAO-56 Annex 2 (J = int(30.4 M - 15)).

    Parameters
    ----------
    month : array_like of int
        Calendar month 1..12.

    Returns
    -------
    numpy.ndarray
        Day of year of mid-month.
    """
    m = _a(month)
    return np.floor(30.4 * m - 15.0)


def _solar_geometry(lat_deg: ArrayLike, doy: ArrayLike) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
    phi = np.deg2rad(_a(lat_deg))
    j = _a(doy)
    dr = 1.0 + 0.033 * np.cos(2.0 * np.pi * j / 365.0)          # Eq. 23
    delta = 0.409 * np.sin(2.0 * np.pi * j / 365.0 - 1.39)      # Eq. 24
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(delta), -1.0, 1.0))  # Eq. 25
    return phi, dr, delta, ws


def extraterrestrial_radiation(lat_deg: ArrayLike, doy: ArrayLike) -> FloatArray:
    """Daily extraterrestrial radiation, FAO-56 Eq. 21 [MJ m-2 day-1].

    Parameters
    ----------
    lat_deg : array_like
        Latitude [decimal degrees, north positive].
    doy : array_like
        Day of year.

    Returns
    -------
    numpy.ndarray
        Extraterrestrial radiation Ra.
    """
    phi, dr, delta, ws = _solar_geometry(lat_deg, doy)
    return (24.0 * 60.0 / np.pi) * GSC * dr * (
        ws * np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.sin(ws)
    )


def daylight_hours(lat_deg: ArrayLike, doy: ArrayLike) -> FloatArray:
    """Maximum possible sunshine duration N, FAO-56 Eq. 34 [h]."""
    _, _, _, ws = _solar_geometry(lat_deg, doy)
    return 24.0 / np.pi * ws


@dataclass(frozen=True)
class AngstromCoefficients:
    """Angstrom-Prescott coefficients Rs = (a + b n/N) Ra.

    Attributes
    ----------
    name : str
        Label used in output tables.
    a : float
        Intercept [-].
    b : float
        Slope [-].
    """

    name: str
    a: float
    b: float


def angstrom_fao56() -> AngstromCoefficients:
    """FAO-56 default coefficients (a = 0.25, b = 0.50), FAO-56 Eq. 35 text."""
    return AngstromCoefficients("FAO56", 0.25, 0.50)


def angstrom_glover_mcculloch(lat_deg: float) -> AngstromCoefficients:
    """Glover and McCulloch (1958) latitude-dependent coefficients.

    a = 0.29 cos(phi), b = 0.52; proposed for latitudes below about 60 degrees.
    """
    return AngstromCoefficients("GloverMcCulloch", 0.29 * float(np.cos(np.deg2rad(lat_deg))), 0.52)


def solar_radiation_angstrom(n_h: ArrayLike, n_max_h: ArrayLike, ra: ArrayLike, coef: AngstromCoefficients) -> FloatArray:
    """Incoming shortwave radiation from sunshine duration, FAO-56 Eq. 35.

    Parameters
    ----------
    n_h : array_like
        Actual sunshine duration [h day-1] (monthly mean of daily values).
    n_max_h : array_like
        Maximum possible sunshine duration [h].
    ra : array_like
        Extraterrestrial radiation [MJ m-2 day-1].
    coef : AngstromCoefficients
        Coefficients a and b.

    Returns
    -------
    numpy.ndarray
        Rs [MJ m-2 day-1]. The relative sunshine n/N is clipped to [0, 1].
    """
    rel = np.clip(_a(n_h) / _a(n_max_h), 0.0, 1.0)
    return (coef.a + coef.b * rel) * _a(ra)


def clear_sky_radiation(ra: ArrayLike, z_m: ArrayLike) -> FloatArray:
    """Clear-sky solar radiation, FAO-56 Eq. 37 [MJ m-2 day-1]."""
    return (0.75 + 2e-5 * _a(z_m)) * _a(ra)


def net_longwave_radiation(tmax_c: ArrayLike, tmin_c: ArrayLike, ea_kpa: ArrayLike, rs: ArrayLike, rso: ArrayLike) -> FloatArray:
    """Net outgoing longwave radiation, FAO-56 Eq. 39 [MJ m-2 day-1].

    Notes
    -----
    Rs/Rso is clipped to [0.3, 1.0]; the lower bound keeps the cloudiness factor
    (1.35 Rs/Rso - 0.35) positive, consistent with FAO-56 guidance that the
    ratio is limited to <= 1.0 and is physically above ~0.25-0.3.
    """
    tk4 = ((_a(tmax_c) + 273.16) ** 4 + (_a(tmin_c) + 273.16) ** 4) / 2.0
    ratio = np.clip(_a(rs) / _a(rso), 0.3, 1.0)
    return SIGMA_MJ * tk4 * (0.34 - 0.14 * np.sqrt(np.clip(_a(ea_kpa), 0.0, None))) * (1.35 * ratio - 0.35)


def wind_to_2m(u_z: ArrayLike, z_m: float) -> FloatArray:
    """Convert wind speed measured at height z to 2 m, FAO-56 Eq. 47 [m s-1].

    Notes
    -----
    For z = 10 m the factor is 0.748. The logarithmic profile assumes a short
    grass surface; it does not correct for site exposure or obstruction.
    """
    return _a(u_z) * 4.87 / np.log(67.8 * z_m - 5.42)


def ea_from_rh_mean(rh_mean_pct: ArrayLike, tmax_c: ArrayLike, tmin_c: ArrayLike) -> FloatArray:
    """Actual vapour pressure from mean relative humidity, FAO-56 Eq. 19 [kPa].

    Notes
    -----
    FAO-56 ranks Eq. 19 below Eqs. 17-18 (RHmax/RHmin). It is used here because
    the TMD archive provides only monthly mean RH.
    """
    es = (sat_vapour_pressure(tmax_c) + sat_vapour_pressure(tmin_c)) / 2.0
    return _a(rh_mean_pct) / 100.0 * es


def soil_heat_flux_monthly(t_prev: ArrayLike, t_curr: ArrayLike, t_next: ArrayLike) -> FloatArray:
    """Monthly soil heat flux, FAO-56 Eq. 43 (Eq. 44 when the next month is missing).

    Returns
    -------
    numpy.ndarray
        G [MJ m-2 day-1]; NaN when the previous month is also missing.
    """
    tp, tc, tn = _a(t_prev), _a(t_curr), _a(t_next)
    g43 = 0.07 * (tn - tp)
    g44 = 0.14 * (tc - tp)
    return np.where(np.isfinite(g43), g43, g44)


def eto_penman_monteith(
    tmax_c: ArrayLike,
    tmin_c: ArrayLike,
    ea_kpa: ArrayLike,
    u2_ms: ArrayLike,
    rs_mj: ArrayLike,
    ra_mj: ArrayLike,
    z_m: ArrayLike,
    g_mj: ArrayLike = 0.0,
    albedo: float = ALBEDO_REF,
) -> FloatArray:
    """FAO-56 Penman-Monteith reference evapotranspiration, FAO-56 Eq. 6.

    Parameters
    ----------
    tmax_c, tmin_c : array_like
        Mean daily maximum and minimum air temperature [degC].
    ea_kpa : array_like
        Actual vapour pressure [kPa].
    u2_ms : array_like
        Wind speed at 2 m [m s-1].
    rs_mj : array_like
        Incoming shortwave radiation [MJ m-2 day-1].
    ra_mj : array_like
        Extraterrestrial radiation [MJ m-2 day-1].
    z_m : array_like
        Elevation above sea level [m].
    g_mj : array_like, default 0.0
        Soil heat flux [MJ m-2 day-1].
    albedo : float, default 0.23
        Reference-surface albedo.

    Returns
    -------
    numpy.ndarray
        ETo [mm day-1]. Negative values (physically implausible at monthly scale
        in the tropics) are returned unchanged so that QC can flag them.

    Notes
    -----
    Mean saturation vapour pressure is the average of e0(Tmax) and e0(Tmin)
    (FAO-56 Eq. 12), not e0(Tmean), to account for the non-linearity of Eq. 11.
    """
    tmax, tmin = _a(tmax_c), _a(tmin_c)
    tmean = (tmax + tmin) / 2.0
    es = (sat_vapour_pressure(tmax) + sat_vapour_pressure(tmin)) / 2.0
    delta = slope_svp(tmean)
    gamma = psychrometric_constant(atmospheric_pressure(z_m))
    rso = clear_sky_radiation(ra_mj, z_m)
    rn = (1.0 - albedo) * _a(rs_mj) - net_longwave_radiation(tmax, tmin, ea_kpa, rs_mj, rso)
    u2 = _a(u2_ms)
    num = 0.408 * delta * (rn - _a(g_mj)) + gamma * (900.0 / (tmean + 273.0)) * u2 * (es - _a(ea_kpa))
    den = delta + gamma * (1.0 + 0.34 * u2)
    return num / den
