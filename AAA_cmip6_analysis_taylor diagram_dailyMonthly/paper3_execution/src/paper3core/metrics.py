"""Complete-season precipitation metrics on the common 365-day calendar."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .calendar import extract_complete_seasons, max_consecutive_spell, rolling_sum_max


def _expected_index(season_type: str, climate_year: int) -> pd.DatetimeIndex:
    if season_type == "RAINY":
        start, end = f"{climate_year}-05-01", f"{climate_year}-10-31"
    elif season_type == "HOT_DRY":
        start, end = f"{climate_year}-11-01", f"{climate_year + 1}-04-30"
    else:
        raise ValueError(f"unknown season type: {season_type}")
    dates = pd.date_range(start, end, freq="D")
    return dates[~((dates.month == 2) & (dates.day == 29))]


def seasonal_metrics(
    frame: pd.DataFrame,
    *,
    climate_years,
    wet_threshold: float = 1.0,
    percentile_thresholds: dict[str, dict[str, float]] | None = None,
    include_incomplete: bool = False,
) -> pd.DataFrame:
    """Calculate primary and secondary metrics for audited station-seasons."""
    frame = frame.astype(float).sort_index()
    keep = ~((frame.index.month == 2) & (frame.index.day == 29))
    frame = frame.loc[keep]
    audit = extract_complete_seasons(frame, climate_years=climate_years)
    rows = []
    for record in audit.itertuples(index=False):
        if not record.complete and not include_incomplete:
            continue
        dates = _expected_index(record.season_type, record.climate_year)
        series = frame[record.station].reindex(dates)
        values = series.to_numpy(dtype=float)
        valid = values[np.isfinite(values)]
        if valid.size == 0:
            continue
        wet = valid[valid >= wet_threshold]
        thresholds = (percentile_thresholds or {}).get(str(record.station), {})
        p95 = float(thresholds.get("p95", np.nan))
        p99 = float(thresholds.get("p99", np.nan))
        row = {
            "station": str(record.station),
            "season_type": record.season_type,
            "climate_year": int(record.climate_year),
            "season_start": record.season_start,
            "season_end": record.season_end,
            "expected_days": int(record.expected_days),
            "valid_days": int(record.valid_days),
            "complete": bool(record.complete),
            "PRCPTOT": float(wet.sum()),
            "wet_day_frequency_pct": float(100.0 * wet.size / valid.size),
            "SDII": float(wet.mean()) if wet.size else 0.0,
            "Rx1day": float(np.max(valid)),
            "CDD": max_consecutive_spell(series, wet=False, wet_threshold=wet_threshold),
            "Rx5day": rolling_sum_max(series, window=5),
            "CWD": max_consecutive_spell(series, wet=True, wet_threshold=wet_threshold),
            "R10mm": int((valid >= 10.0).sum()),
            "R20mm": int((valid >= 20.0).sum()),
            "R50mm": int((valid >= 50.0).sum()),
            "R95p": float(wet[wet > p95].sum()) if np.isfinite(p95) else np.nan,
            "R99p": float(wet[wet > p99].sum()) if np.isfinite(p99) else np.nan,
            "q50": float(np.percentile(wet, 50)) if wet.size >= 10 else np.nan,
            "q90": float(np.percentile(wet, 90)) if wet.size >= 10 else np.nan,
            "q95": float(np.percentile(wet, 95)) if wet.size >= 10 else np.nan,
            "q99": float(np.percentile(wet, 99)) if wet.size >= 10 else np.nan,
        }
        rows.append(row)
    return pd.DataFrame(rows)


def observed_percentile_thresholds(
    observed: pd.DataFrame,
    *,
    start_year: int = 1981,
    end_year: int = 2010,
    wet_threshold: float = 1.0,
) -> dict[str, dict[str, float]]:
    """Observed wet-day percentile thresholds for comparable ETCCDI metrics."""
    subset = observed[(observed.index.year >= start_year) & (observed.index.year <= end_year)]
    thresholds = {}
    for station in subset.columns:
        values = subset[station].to_numpy(dtype=float)
        wet = values[np.isfinite(values) & (values >= wet_threshold)]
        thresholds[str(station)] = {
            "p95": float(np.percentile(wet, 95)) if wet.size >= 10 else np.nan,
            "p99": float(np.percentile(wet, 99)) if wet.size >= 10 else np.nan,
        }
    return thresholds
