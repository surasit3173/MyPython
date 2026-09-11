"""Canonical I/O: discovery, loading, unit checks, calendar harmonisation,
station mapping.  Used identically by every bias-correction method so that
model/station mapping can never differ between methods.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

TIME_COLS = ("YEAR", "MONTH", "DAY")
MISSING_FLAGS = (-99, -999, -9999, -9.99e20, 9.99e20, 1e20)

# Files produced by a previous, unverified bias correction must never be read.
LEGACY_BC_TOKENS = ("bc_", "_bc", "bias", "qdm", "corrected")

_VARIANT = re.compile(r"r\d+i\d+p\d+f\d+")
_GRID = re.compile(r"_(gn|gr|gr1|gr2)_")
_SCEN = re.compile(r"(ssp\d{3})")


@dataclass
class RawFile:
    path: Path
    model: str
    scenario: str          # 'historical' | 'ssp245' | ...
    variant: str
    grid: str

    def key(self):
        return (self.model, self.scenario)


def _parse_raw_name(p: Path):
    stem = p.stem
    variant = (_VARIANT.search(stem) or [""])[0] if _VARIANT.search(stem) else ""
    grid_m = _GRID.search(stem)
    grid = grid_m.group(1) if grid_m else ""
    scen_m = _SCEN.search(stem.lower())
    scenario = scen_m.group(1) if scen_m else (
        "historical" if "historical" in stem.lower() else "")
    parts = stem.split("_")
    model = ""
    for i, tok in enumerate(parts):
        if tok in ("day", "pr"):
            continue
        if tok.lower() in ("historical",) or _SCEN.fullmatch(tok.lower()):
            model = parts[i - 1] if i else ""
            break
    if not model and len(parts) > 2:
        model = parts[2]
    return model, scenario, variant, grid


def discover_raw(cmip6_dir, scenarios) -> list[RawFile]:
    """Find raw CMIP6 files.  Legacy bias-corrected files are refused."""
    cmip6_dir = Path(cmip6_dir)
    found, skipped = {}, []
    for p in sorted(cmip6_dir.rglob("*.csv")):
        low = p.name.lower()
        if any(t in low for t in LEGACY_BC_TOKENS):
            skipped.append(p.name)
            continue
        if not low.startswith("pr_day"):
            continue
        model, scenario, variant, grid = _parse_raw_name(p)
        if not model or scenario not in (["historical"] + list(scenarios)):
            continue
        rf = RawFile(p, model, scenario, variant, grid)
        if rf.key() in found:
            log.warning("duplicate %s/%s -> keeping %s",
                        model, scenario, found[rf.key()].path.name)
            continue
        found[rf.key()] = rf
    if skipped:
        log.info("refused %d legacy bias-corrected file(s) (provenance unverified)",
                 len(skipped))
    return sorted(found.values(), key=lambda r: (r.model, r.scenario))


def _read_daily(path, usecols=None) -> pd.DataFrame:
    df = pd.read_csv(path, usecols=usecols) if usecols else pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]
    drop = [c for c in df.columns
            if c.lower().startswith("unnamed") or c in ("", "nan", "None")]
    if drop:
        df = df.drop(columns=drop)
    for flag in MISSING_FLAGS:
        df = df.replace(flag, np.nan)
    return df


def _to_series_frame(df: pd.DataFrame, stations) -> pd.DataFrame:
    missing = [s for s in stations if s not in df.columns]
    if missing:
        raise KeyError(f"stations absent from file: {missing}")
    idx = pd.to_datetime(dict(year=df.YEAR, month=df.MONTH, day=df.DAY))
    out = df[list(stations)].astype(float)
    out.index = pd.DatetimeIndex(idx, name="date")
    out[out < 0] = np.nan                      # negative rainfall is impossible
    return out.sort_index()


def load_observed(path, stations=None) -> pd.DataFrame:
    df = _read_daily(path)
    if stations is None:
        stations = [c for c in df.columns
                    if c not in TIME_COLS and str(c).strip().isdigit()]
    return _to_series_frame(df, stations)


def load_raw(rf: RawFile, stations) -> pd.DataFrame:
    keep = set(TIME_COLS) | set(map(str, stations))
    df = _read_daily(rf.path, usecols=lambda c: str(c).strip() in keep)
    return _to_series_frame(df, stations)


def resolve_stations(observed_path, coord_path=None, explicit=None) -> list[str]:
    """Stations = observed columns  n  coordinate table (or an explicit list)."""
    obs = _read_daily(observed_path)
    obs_ids = [c for c in obs.columns
               if c not in TIME_COLS and str(c).strip().isdigit()]
    if explicit:
        return [str(s) for s in explicit if str(s) in set(obs_ids)]
    if coord_path is None:
        return obs_ids
    coords = load_coordinates(coord_path)
    keep = [s for s in obs_ids if s in set(coords["station"])]
    return keep or obs_ids


def load_coordinates(gis_dir) -> pd.DataFrame:
    gis_dir = Path(gis_dir)
    cands = sorted(list(gis_dir.rglob("*coord*.xlsx"))
                   + list(gis_dir.rglob("*coord*.csv"))
                   + list(gis_dir.rglob("*station*.xlsx"))
                   + list(gis_dir.rglob("*station*.csv")))
    if not cands:
        raise FileNotFoundError(f"no station-coordinate table under {gis_dir}")
    p = cands[0]
    df = pd.read_excel(p) if p.suffix.lower() in (".xlsx", ".xls") \
        else pd.read_csv(p)
    df.columns = [str(c).strip().lower() for c in df.columns]
    ren = {}
    for c in df.columns:
        if c.startswith("stat") or c in ("id", "code"):
            ren[c] = "station"
        elif c.startswith("lat"):
            ren[c] = "latitude"
        elif c.startswith("lon") or c.startswith("lng"):
            ren[c] = "longitude"
    df = df.rename(columns=ren)
    df["station"] = df["station"].astype(str).str.strip()
    df["_source"] = p.name
    return df[["station", "latitude", "longitude", "_source"]].dropna()


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------
def calendar_report(frame: pd.DataFrame) -> dict:
    """Classify a model calendar from the daily index.  Never silently mixed."""
    idx = frame.index
    years = idx.year.unique()
    leap_years = [y for y in years
                  if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0))]
    has_feb29 = bool(((idx.month == 2) & (idx.day == 29)).any())
    counts = pd.Series(1, index=idx).groupby(idx.year).sum()
    uniq = sorted(set(counts.values))
    if not has_feb29 and leap_years:
        cal = "365_day (noleap)"
    elif set(uniq) <= {360}:
        cal = "360_day"
    else:
        cal = "standard (Gregorian)"
    return {"calendar": cal, "days_per_year": uniq,
            "first": str(idx.min().date()), "last": str(idx.max().date()),
            "n_days": int(len(idx))}


def align_daily(frame: pd.DataFrame, y0: int, y1: int) -> pd.DataFrame:
    """Restrict to whole years and expose the real calendar as a DatetimeIndex.

    Missing calendar dates (e.g. 29 Feb under a no-leap model) are inserted as
    NaN so that any window operation sees real elapsed time; they are never
    filled.  Index metrics that count days therefore see 365 real model days in
    a no-leap leap year, which is documented in the manifest.
    """
    sub = frame[(frame.index.year >= y0) & (frame.index.year <= y1)]
    full = pd.date_range(f"{y0}-01-01", f"{y1}-12-31", freq="D")
    return sub.reindex(full)


def unit_check(frame: pd.DataFrame, label: str) -> dict:
    """Detect kg m-2 s-1 left unconverted (mean daily total would be ~1e-5)."""
    m = float(np.nanmean(frame.to_numpy(float)))
    annual = m * 365.25
    if annual < 1.0:
        verdict = "SUSPECT: looks like kg m-2 s-1, multiply by 86400"
    elif annual > 20000:
        verdict = "SUSPECT: implausibly large for daily rainfall in mm"
    else:
        verdict = "OK: consistent with mm/day"
    return {"series": label, "mean_daily_mm": round(m, 4),
            "implied_annual_mm": round(annual, 1), "verdict": verdict}
