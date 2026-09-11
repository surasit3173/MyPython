"""Strict, provenance-aware loading for observed and historical CMIP6 rain."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


TIME_COLUMNS = ("YEAR", "MONTH", "DAY")
MISSING_FLAGS = (-99, -999, -9999, -9.99e20, 9.99e20, 1e20)
RAW_PATTERN = re.compile(
    r"^pr_day_(?P<model>.+?)_historical_(?P<member>r\d+i\d+p\d+f\d+)_(?P<grid>gn|gr\d*)_"
)


@dataclass(frozen=True)
class HistoricalFile:
    path: Path
    model: str
    member_id: str
    grid_label: str


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def discover_historical_files(root: str | Path) -> list[HistoricalFile]:
    """Discover raw historical precipitation only; reject legacy corrected data."""
    found: dict[str, HistoricalFile] = {}
    for path in sorted(Path(root).rglob("pr_day_*historical*.csv")):
        if path.name.lower().startswith("bc_"):
            continue
        match = RAW_PATTERN.match(path.name)
        if match is None:
            raise ValueError(f"unparseable raw historical filename: {path.name}")
        item = HistoricalFile(
            path=path,
            model=match.group("model"),
            member_id=match.group("member"),
            grid_label=match.group("grid"),
        )
        if item.model in found:
            raise ValueError(f"duplicate historical raw file for {item.model}")
        found[item.model] = item
    return [found[key] for key in sorted(found)]


def station_columns(path: str | Path) -> list[str]:
    columns = [str(value).strip() for value in pd.read_csv(path, nrows=0).columns]
    return [value for value in columns if value not in TIME_COLUMNS and value.isdigit()]


def common_365_index(start_year: int, end_year: int) -> pd.DatetimeIndex:
    dates = pd.date_range(f"{start_year}-01-01", f"{end_year}-12-31", freq="D")
    return dates[~((dates.month == 2) & (dates.day == 29))]


def load_daily(
    path: str | Path,
    *,
    stations: list[str] | None,
    start_year: int,
    end_year: int,
    tiny_negative_tolerance_mm: float = 1.0e-9,
    drop_february_29: bool = True,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Load a daily table and enforce a complete common 365-day date axis.

    Only machine-rounding negatives in [-tolerance, 0) are normalized to zero.
    A material negative value aborts the run rather than being silently deleted.
    """
    path = Path(path)
    stations = station_columns(path) if stations is None else [str(s) for s in stations]
    keep = set(TIME_COLUMNS).union(stations)
    data = pd.read_csv(path, usecols=lambda value: str(value).strip() in keep)
    data.columns = [str(value).strip() for value in data.columns]
    missing = sorted(set(stations).difference(data.columns))
    if missing:
        raise KeyError(f"stations absent from {path.name}: {missing}")
    for flag in MISSING_FLAGS:
        data.loc[:, stations] = data.loc[:, stations].replace(flag, np.nan)
    dates = pd.to_datetime(
        {"year": data["YEAR"], "month": data["MONTH"], "day": data["DAY"]},
        errors="raise",
    )
    if dates.duplicated().any():
        raise ValueError(f"duplicate dates in {path.name}")
    frame = data.loc[:, stations].astype(float)
    frame.index = pd.DatetimeIndex(dates, name="date")
    frame = frame.sort_index()
    frame = frame[(frame.index.year >= start_year) & (frame.index.year <= end_year)]
    available_leap_days = int(((frame.index.month == 2) & (frame.index.day == 29)).sum())
    leap_days_removed = available_leap_days if drop_february_29 else 0
    if drop_february_29:
        frame = frame.loc[~((frame.index.month == 2) & (frame.index.day == 29))]

    values = frame.to_numpy(dtype=float)
    tiny = np.isfinite(values) & (values < 0.0) & (values >= -tiny_negative_tolerance_mm)
    material = np.isfinite(values) & (values < -tiny_negative_tolerance_mm)
    if material.any():
        minimum = float(np.nanmin(values))
        raise ValueError(f"material negative precipitation in {path.name}: min={minimum}")
    if tiny.any():
        values[tiny] = 0.0
        frame.loc[:, :] = values

    expected = (
        common_365_index(start_year, end_year)
        if drop_february_29
        else pd.date_range(f"{start_year}-01-01", f"{end_year}-12-31", freq="D")
    )
    absent_dates = expected.difference(frame.index)
    extra_dates = frame.index.difference(expected)
    if len(absent_dates) or len(extra_dates):
        raise ValueError(
            f"calendar mismatch in {path.name}: absent={len(absent_dates)}, extra={len(extra_dates)}"
        )
    frame = frame.reindex(expected)
    frame.index.name = "date"
    report = {
        "path": str(path),
        "sha256": sha256_file(path),
        "start": str(frame.index.min().date()),
        "end": str(frame.index.max().date()),
        "calendar_loaded": "common_365" if drop_february_29 else "native_Gregorian",
        "n_loaded_days": int(len(frame)),
        "n_stations": int(len(stations)),
        "leap_days_removed": leap_days_removed,
        "tiny_negatives_set_to_zero": int(tiny.sum()),
        "material_negatives": int(material.sum()),
        "missing_values": int(frame.isna().sum().sum()),
        "mean_daily_mm": float(np.nanmean(frame.to_numpy(dtype=float))),
    }
    return frame, report


def climate_year_for_dates(index: pd.DatetimeIndex) -> pd.Series:
    """Start-year label for May-Oct and Nov-Apr management seasons."""
    years = index.year.to_numpy(dtype=int)
    months = index.month.to_numpy(dtype=int)
    climate_year = np.where(months <= 4, years - 1, years)
    return pd.Series(climate_year, index=index, dtype=int, name="climate_year")
