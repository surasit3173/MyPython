"""Calendar-safe precipitation indices on a common 365-day calendar."""

from __future__ import annotations

import calendar as _calendar

import numpy as np
import pandas as pd


def _prepared(series: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    values = series.astype(float).sort_index()
    if values.index.has_duplicates:
        raise ValueError("daily series contains duplicate dates")
    keep = ~((values.index.month == 2) & (values.index.day == 29))
    values = values.loc[keep]
    serial = []
    for date in values.index:
        day = int(date.dayofyear)
        if _calendar.isleap(int(date.year)) and date.month > 2:
            day -= 1
        serial.append(int(date.year) * 365 + day)
    return np.asarray(serial, dtype=int), values.to_numpy(dtype=float)


def max_consecutive_spell(
    series: pd.Series, *, wet: bool, wet_threshold: float = 1.0
) -> int:
    """Maximum wet/dry run; missing or non-consecutive dates break a run."""
    serial, values = _prepared(series)
    best = run = 0
    previous = None
    for day, value in zip(serial, values, strict=True):
        consecutive = previous is not None and day == previous + 1
        if not consecutive:
            run = 0
        condition = np.isfinite(value) and (
            value >= wet_threshold if wet else value < wet_threshold
        )
        run = run + 1 if condition else 0
        best = max(best, run)
        previous = day
    return int(best)


def rolling_sum_max(series: pd.Series, *, window: int = 5) -> float:
    """Maximum rolling sum without crossing a date gap or missing value."""
    serial, values = _prepared(series)
    best = np.nan
    start = 0
    while start < len(values):
        end = start + 1
        while (
            end < len(values)
            and serial[end] == serial[end - 1] + 1
            and np.isfinite(values[end])
            and np.isfinite(values[end - 1])
        ):
            end += 1
        segment = values[start:end]
        if len(segment) >= window and np.isfinite(segment).all():
            sums = np.convolve(segment, np.ones(window, dtype=float), mode="valid")
            candidate = float(np.max(sums))
            best = candidate if not np.isfinite(best) else max(best, candidate)
        start = end
    return float(best)


def extract_complete_seasons(
    frame: pd.DataFrame, *, climate_years
) -> pd.DataFrame:
    """Audit expected/valid days for every station and management season."""
    frame = frame.astype(float).sort_index()
    if frame.index.has_duplicates:
        raise ValueError("daily frame contains duplicate dates")
    keep = ~((frame.index.month == 2) & (frame.index.day == 29))
    frame = frame.loc[keep]
    rows = []
    for climate_year in climate_years:
        definitions = (
            ("RAINY", f"{climate_year}-05-01", f"{climate_year}-10-31"),
            ("HOT_DRY", f"{climate_year}-11-01", f"{climate_year + 1}-04-30"),
        )
        for season_type, start, end in definitions:
            expected = pd.date_range(start, end, freq="D")
            expected = expected[~((expected.month == 2) & (expected.day == 29))]
            selected = frame.reindex(expected)
            for station in frame.columns:
                valid_days = int(selected[station].notna().sum())
                rows.append(
                    {
                        "station": str(station),
                        "season_type": season_type,
                        "climate_year": int(climate_year),
                        "season_start": pd.Timestamp(start),
                        "season_end": pd.Timestamp(end),
                        "expected_days": int(len(expected)),
                        "valid_days": valid_days,
                        "complete": bool(valid_days == len(expected)),
                    }
                )
    return pd.DataFrame(rows)
