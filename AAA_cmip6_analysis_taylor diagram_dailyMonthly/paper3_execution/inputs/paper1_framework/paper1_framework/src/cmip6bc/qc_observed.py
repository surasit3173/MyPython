"""Observed zero-quality control.

Six independent diagnostics per station-month, three-tier classification, and a
strict conversion rule.  Rainfall is NEVER imputed and a zero is NEVER turned
into a gap unless the surrounding gauge network contradicts it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _zero_run_lengths(x: np.ndarray) -> np.ndarray:
    out = np.zeros(len(x), dtype=int)
    is_zero = (x == 0.0)
    i = 0
    while i < len(x):
        if not is_zero[i]:
            i += 1
            continue
        j = i
        while j < len(x) and is_zero[j]:
            j += 1
        out[i:j] = j - i
        i = j
    return out


def diagnose(obs: pd.DataFrame, p: dict) -> pd.DataFrame:
    """obs: DatetimeIndex x station columns (mm/day)."""
    stations = list(obs.columns)
    ym = [obs.index.year, obs.index.month]
    monthly = obs.groupby(ym).sum(min_count=1)
    monthly.index.names = ["year", "month"]
    annual = obs.groupby(obs.index.year).sum(min_count=1)

    runs = pd.DataFrame({s: _zero_run_lengths(obs[s].fillna(-1).to_numpy(float))
                         for s in stations}, index=obs.index)
    run_max = runs.groupby(ym).max()
    run_max.index.names = ["year", "month"]

    own_clim = monthly.groupby(level="month").median()
    own_ann_med = annual.median()
    reg_ann_med = annual.median(axis=1)

    rows = []
    for (y, m), row in monthly.iterrows():
        for s in stations:
            total = float(row[s])
            others = row.drop(labels=[s]).astype(float)
            neigh_med = float(others.median())
            neigh_frac = float((others > p["neighbour_wet_mm"]).mean())
            clim = float(own_clim.loc[m, s])
            run = int(run_max.loc[(y, m), s])
            ann = float(annual.loc[y, s])

            I1 = total == 0.0
            I2 = neigh_med >= p["neighbour_median_mm"]
            I3 = neigh_frac >= p["neighbour_frac"]
            I4 = clim >= p["own_clim_mm"]
            I5 = run >= p["zero_run_days"]
            I6 = (ann < p["annual_deficit_frac"] * own_ann_med[s]
                  and ann < p["annual_deficit_frac"] * reg_ann_med[y])
            n_ind = int(I2) + int(I3) + int(I4) + int(I5) + int(I6)

            if not I1:
                cls, why = "not_zero", ""
            elif (not I4) and (not I2) and clim < p["confirmed_dry_clim_mm"]:
                cls = "confirmed_zero"
                why = (f"climatologically dry month at this gauge "
                       f"(own median {clim:.1f} mm) and the region was dry "
                       f"(neighbour median {neigh_med:.1f} mm)")
            elif (I2 or I3) and n_ind >= p["min_indicators"]:
                # A neighbour-based contradiction is MANDATORY: within-station
                # diagnostics alone cannot separate real drought from a gap.
                cls = "probable_missing"
                why = "indicators fired: " + ", ".join(
                    n for n, v in [("I2_region_wet", I2), ("I3_neighbours_wet", I3),
                                   ("I4_month_normally_wet", I4),
                                   ("I5_long_zero_run", I5),
                                   ("I6_annual_deficit", I6)] if v)
            else:
                cls = "uncertain"
                why = ("no neighbour contradiction (region also dry)"
                       if not (I2 or I3)
                       else f"{n_ind} indicator(s); below evidence threshold")

            rows.append(dict(
                station=s, year=int(y), month=int(m),
                monthly_total_mm=round(total, 2),
                neighbour_median_mm=round(neigh_med, 2),
                neighbour_frac_wet=round(neigh_frac, 3),
                own_clim_median_mm=round(clim, 2), max_zero_run_days=run,
                annual_total_mm=round(ann, 1),
                I1_exact_zero=I1, I2_region_wet=I2, I3_neighbours_wet=I3,
                I4_month_normally_wet=I4, I5_long_zero_run=I5,
                I6_annual_deficit=I6, n_indicators=n_ind,
                classification=cls, reason=why,
                metadata_checked="", metadata_note=""))
    return pd.DataFrame(rows)


def apply_flags(obs: pd.DataFrame, diag: pd.DataFrame,
                classes=("probable_missing",)) -> tuple[pd.DataFrame, int]:
    """Set flagged station-months to NaN.  No value is ever filled in."""
    out = obs.copy()
    n = 0
    sel = diag[diag["classification"].isin(classes)]
    ym = pd.MultiIndex.from_arrays([out.index.year, out.index.month])
    for r in sel.itertuples():
        mask = (ym.get_level_values(0) == r.year) & (ym.get_level_values(1) == r.month)
        n += int(mask.sum() - out.loc[mask, r.station].isna().sum())
        out.loc[mask, r.station] = np.nan
    return out, n


def summary(diag: pd.DataFrame) -> pd.DataFrame:
    c = diag["classification"].value_counts()
    return pd.DataFrame({"classification": c.index, "station_months": c.values})
