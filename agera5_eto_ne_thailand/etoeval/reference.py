"""Station-based FAO-56 Penman-Monteith reference ETo with structural uncertainty.

The station reference is not a single "truth". Two choices that cannot be
resolved from the archive are propagated as ensemble members:

1. Wind-speed unit of the TMD archive (m s-1 or knots) - not documented in the
   files supplied.
2. Angstrom-Prescott coefficients used to estimate Rs from sunshine duration
   (FAO-56 defaults vs Glover and McCulloch, 1958), because no pyranometer
   record is available for calibration.

The resulting 2 x 2 = 4 members define the reference uncertainty envelope
against which AgERA5 is judged.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from . import fao56, homogeneity
from .data import Config

logger = logging.getLogger(__name__)

WIND_FACTORS: dict[str, float] = {"m s-1": 1.0, "knot": fao56.KNOT_TO_MS}


def iterative_wind_break_masking(
    monthly: pd.DataFrame,
    q_threshold: float,
    min_shift_pct: float,
    n_sim: int,
    seed: int,
    max_iter: int = 10,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Iteratively detect and mask large station-specific breaks in wind records.

    At each iteration the relative SNHT is run on all stations; among breaks
    with BH-FDR q < ``q_threshold`` and |relative shift| >= ``min_shift_pct``,
    the most significant one (largest T0) is acted upon by masking the shorter
    segment. Screening is then repeated on the updated network, so that a
    corrected station no longer contaminates the reference of the others.

    Parameters
    ----------
    monthly : pandas.DataFrame
        QC-ed station-month table containing ``wind_raw``.
    q_threshold : float
        BH-FDR threshold.
    min_shift_pct : float
        Minimum absolute relative shift (%) to act on a break.
    n_sim : int
        Monte Carlo replicates for SNHT.
    seed : int
        Random seed.
    max_iter : int, default 10
        Safety limit on iterations.

    Returns
    -------
    masked : pandas.DataFrame
        Copy with masked wind values set to NaN and ``wind_segment_masked``.
    decisions : pandas.DataFrame
        One row per action (iteration, station, break year, shift, segment).
    final_screen : pandas.DataFrame
        Wind screening table on the final masked network.

    Notes
    -----
    Keeping the longer segment rather than adjusting the shorter one avoids an
    unverifiable correction factor in the absence of station metadata. Breaks
    that are significant but smaller than ``min_shift_pct`` are reported only.
    """
    out = monthly.copy()
    out["wind_segment_masked"] = False
    actions: list[dict[str, object]] = []
    screen = homogeneity.screen_station_network(out, {"wind_raw": True}, n_sim=n_sim, seed=seed)
    for it in range(1, max_iter + 1):
        cand = screen[(screen["snht_rel_q"] < q_threshold) & (screen["rel_shift_pct"].abs() >= min_shift_pct)]
        if cand.empty:
            break
        r = cand.sort_values("snht_rel_T0", ascending=False).iloc[0]
        code, brk = int(r["stncode"]), int(r["snht_rel_break_after"])
        sel = out["stncode"] == code
        n_before = int(out.loc[sel & (out["year"] <= brk), "wind_raw"].notna().sum())
        n_after = int(out.loc[sel & (out["year"] > brk), "wind_raw"].notna().sum())
        mask = sel & ((out["year"] > brk) if n_before >= n_after else (out["year"] <= brk))
        n_masked = int(out.loc[mask, "wind_raw"].notna().sum())
        out.loc[mask, "wind_segment_masked"] = out.loc[mask, "wind_raw"].notna() | out.loc[mask, "wind_segment_masked"]
        out.loc[mask, "wind_raw"] = np.nan
        actions.append({"iteration": it, "stncode": code, "break_after": brk, "snht_T0": float(r["snht_rel_T0"]),
                        "snht_q": float(r["snht_rel_q"]), "rel_shift_pct": float(r["rel_shift_pct"]),
                        "masked_segment": f"{brk + 1}-end" if n_before >= n_after else f"start-{brk}",
                        "months_masked": n_masked})
        logger.info("Wind break masked: %s after %s (shift %.1f%%)", code, brk, r["rel_shift_pct"])
        screen = homogeneity.screen_station_network(out, {"wind_raw": True}, n_sim=n_sim, seed=seed)
    return out, pd.DataFrame(actions), screen


def build_reference_ensemble(monthly: pd.DataFrame, cfg: Config, include_g: bool = True) -> pd.DataFrame:
    """Compute station PM-ETo for every wind-unit x Angstrom member.

    Parameters
    ----------
    monthly : pandas.DataFrame
        QC-ed (and wind-masked) station-month table.
    cfg : Config
        Configuration (stations, anemometer height, ensemble options).
    include_g : bool, default True
        Also compute ETo with monthly soil heat flux (FAO-56 Eq. 43/44) as a
        sensitivity column ``eto_g_mm_day``. The main estimate uses G = 0 to be
        method-consistent with AgERA5, whose daily ETo implies a monthly G of 0.

    Returns
    -------
    pandas.DataFrame
        Long table: stncode, year, month, member, wind_unit, angstrom, inputs
        (tmax, tmin, ea, u2, rs, ra, z) and eto_mm_day / eto_mm_month.
    """
    st = {s.code: s for s in cfg.stations}
    base = monthly.copy()
    base["lat"] = base["stncode"].map({c: s.lat for c, s in st.items()})
    base["z"] = base["stncode"].map(
        {c: (s.elevation_m if s.elevation_m is not None else cfg.assumed_elevation_m) for c, s in st.items()}
    )
    base["z_assumed"] = base["stncode"].map({c: s.elevation_m is None for c, s in st.items()})
    doy = fao56.mid_month_doy(base["month"])
    base["ra"] = fao56.extraterrestrial_radiation(base["lat"], doy)
    base["n_max"] = fao56.daylight_hours(base["lat"], doy)
    base["ea"] = fao56.ea_from_rh_mean(base["rh"], base["tmax"], base["tmin"])
    base["days"] = pd.to_datetime(dict(year=base["year"], month=base["month"], day=1)).dt.days_in_month
    tmean = (base["tmax"] + base["tmin"]) / 2.0
    base = base.sort_values(["stncode", "year", "month"])
    t_prev = tmean.groupby(base["stncode"]).shift(1)
    t_next = tmean.groupby(base["stncode"]).shift(-1)
    base["g"] = fao56.soil_heat_flux_monthly(t_prev, tmean, t_next)

    frames: list[pd.DataFrame] = []
    for unit in cfg.wind_units:
        for ang in cfg.angstrom_sets:
            m = base.copy()
            m["wind_unit"] = unit
            m["angstrom"] = ang
            m["member"] = f"{unit.replace(' ', '')}|{ang}"
            u10 = m["wind_raw"] * WIND_FACTORS[unit]
            m["u2"] = fao56.wind_to_2m(u10, cfg.anemometer_height_m)
            rs = np.full(len(m), np.nan)
            for code, s in st.items():
                sel = (m["stncode"] == code).to_numpy()
                coef = fao56.angstrom_fao56() if ang == "FAO56" else fao56.angstrom_glover_mcculloch(s.lat)
                rs[sel] = fao56.solar_radiation_angstrom(m.loc[sel, "sun"], m.loc[sel, "n_max"], m.loc[sel, "ra"], coef)
            m["rs"] = rs
            m["eto_mm_day"] = fao56.eto_penman_monteith(m["tmax"], m["tmin"], m["ea"], m["u2"], m["rs"], m["ra"], m["z"], 0.0)
            if include_g:
                m["eto_g_mm_day"] = fao56.eto_penman_monteith(
                    m["tmax"], m["tmin"], m["ea"], m["u2"], m["rs"], m["ra"], m["z"], m["g"]
                )
            m["eto_mm_month"] = m["eto_mm_day"] * m["days"]
            frames.append(m)
    out = pd.concat(frames, ignore_index=True)
    keep = ["stncode", "year", "month", "member", "wind_unit", "angstrom", "tmax", "tmin", "rh", "ea", "sun",
            "wind_raw", "u2", "rs", "ra", "n_max", "z", "z_assumed", "g", "days", "eto_mm_day", "eto_mm_month"]
    if include_g:
        keep.append("eto_g_mm_day")
    return out[keep]


def annual_totals(ref: pd.DataFrame, min_months: int = 12) -> pd.DataFrame:
    """Annual ETo totals per station, year and member (complete years only).

    Parameters
    ----------
    ref : pandas.DataFrame
        Output of :func:`build_reference_ensemble`.
    min_months : int, default 12
        Years with fewer valid months are excluded (no infilling).

    Returns
    -------
    pandas.DataFrame
        Columns stncode, year, member, eto_mm_year, n_months.
    """
    g = ref.groupby(["stncode", "year", "member"])["eto_mm_month"]
    out = pd.DataFrame({"eto_mm_year": g.sum(min_count=1), "n_months": g.count()}).reset_index()
    return out[out["n_months"] >= min_months]
