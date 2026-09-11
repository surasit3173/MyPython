"""
etccdi.py
=========
ETCCDI extreme-precipitation indices, computed per station per calendar year.
Generic: pass any daily wide table (date index, one column per station) and a
list of station ids. Wet-day threshold and the R95p/R99p base period are
configurable so the module is reusable for other study areas.

Indices (WMO/ETCCDI definitions):
  Rx1day  annual maximum 1-day precipitation (mm)
  Rx3day  annual maximum consecutive 3-day precipitation (mm)
  Rx5day  annual maximum consecutive 5-day precipitation (mm)
  R95p    annual total precipitation on very wet days  (> base-period p95) (mm)
  R99p    annual total precipitation on extremely wet days (> p99)         (mm)
  CDD     annual maximum length of dry spell  (consecutive days < 1 mm)   (days)
  CWD     annual maximum length of wet spell  (consecutive days >= 1 mm)  (days)
  SDII    simple daily intensity index = wet-day total / wet-day count    (mm/day)
"""
from __future__ import annotations
import numpy as np
import pandas as pd

WET_THRESHOLD = 1.0          # mm; standard ETCCDI wet-day definition


def _max_consecutive(mask_by_year: pd.Series) -> int:
    """Longest run of True within a boolean series (one calendar year)."""
    best = run = 0
    for v in mask_by_year.values:
        run = run + 1 if v else 0
        best = max(best, run)
    return int(best)


def _rx_nday(s_year: pd.Series, n: int) -> float:
    if len(s_year) < n:
        return np.nan
    return float(s_year.rolling(n, min_periods=n).sum().max())


def compute_station_indices(daily: pd.Series, base_period=None,
                            wet=WET_THRESHOLD) -> pd.DataFrame:
    """Annual ETCCDI indices for one station (daily series, datetime index).

    base_period : (start_year, end_year) used for the R95p/R99p percentile
                  thresholds; defaults to the full record. Percentiles are taken
                  over wet days (precip >= wet) within the base period.
    """
    s = daily.dropna().astype(float)
    years = s.index.year
    if base_period is None:
        base = s
    else:
        b0, b1 = base_period
        base = s[(years >= b0) & (years <= b1)]
    wet_base = base[base >= wet]
    p95 = np.percentile(wet_base, 95) if len(wet_base) else np.nan
    p99 = np.percentile(wet_base, 99) if len(wet_base) else np.nan

    rows = []
    for y, sy in s.groupby(years):
        wetmask = sy >= wet
        nwet = int(wetmask.sum())
        wet_total = float(sy[wetmask].sum())
        rows.append(dict(
            year=int(y),
            Rx1day=float(sy.max()),
            Rx3day=_rx_nday(sy, 3),
            Rx5day=_rx_nday(sy, 5),
            R95p=float(sy[sy > p95].sum()) if np.isfinite(p95) else np.nan,
            R99p=float(sy[sy > p99].sum()) if np.isfinite(p99) else np.nan,
            CDD=_max_consecutive(~wetmask),
            CWD=_max_consecutive(wetmask),
            SDII=(wet_total / nwet) if nwet else np.nan,
        ))
    out = pd.DataFrame(rows).set_index("year")
    out.attrs["p95"] = p95
    out.attrs["p99"] = p99
    return out


INDEX_NAMES = ["Rx1day", "Rx3day", "Rx5day", "R95p", "R99p", "CDD", "CWD", "SDII"]
INDEX_UNITS = {"Rx1day": "mm", "Rx3day": "mm", "Rx5day": "mm", "R95p": "mm",
               "R99p": "mm", "CDD": "days", "CWD": "days", "SDII": "mm/day"}


def compute_all_stations(daily: pd.DataFrame, station_ids, base_period=None):
    """Return long-format DataFrame: station, year, <index columns>."""
    frames = []
    for sid in station_ids:
        idx = compute_station_indices(daily[sid], base_period)
        idx.insert(0, "station", sid)
        frames.append(idx.reset_index())
    return pd.concat(frames, ignore_index=True)
