"""Complete calendar and hydrological period aggregation."""

from __future__ import annotations

from datetime import date
from typing import Sequence

import pandas as pd


def build_period_totals(
    observations: pd.DataFrame,
    *,
    wet_months: Sequence[int] = (5, 6, 7, 8, 9, 10),
    dry_months: Sequence[int] = (11, 12, 1, 2, 3, 4),
    completeness_threshold: float = 1.0,
) -> pd.DataFrame:
    required = {"date", "station_id", "rain_mm"}
    if not required.issubset(observations.columns):
        raise ValueError(f"observations must contain {sorted(required)}")
    if not 0 < completeness_threshold <= 1:
        raise ValueError("completeness_threshold must be in (0, 1]")
    if observations.empty:
        raise ValueError("observations cannot be empty")
    obs = observations.copy()
    obs["date"] = pd.to_datetime(obs["date"], errors="raise").dt.normalize()
    obs["station_id"] = obs["station_id"].astype(str)
    if obs.duplicated(["station_id", "date"]).any():
        raise ValueError("observations contain duplicate station-day rows")
    start = obs["date"].min()
    end = obs["date"].max()
    stations = sorted(obs["station_id"].unique())

    def expected_dates(period: str, year: int) -> pd.DatetimeIndex:
        if period == "annual":
            dates = pd.date_range(date(year, 1, 1), date(year, 12, 31), freq="D")
        elif period == "wet":
            all_dates = pd.date_range(date(year, 1, 1), date(year, 12, 31), freq="D")
            dates = all_dates[all_dates.month.isin(tuple(wet_months))]
        elif period == "dry":
            all_dates = pd.date_range(date(year - 1, 1, 1), date(year, 12, 31), freq="D")
            months = set(int(month) for month in dry_months)
            dates = all_dates[
                ((all_dates.year == year - 1) & all_dates.month.isin([m for m in months if m >= 7]))
                | ((all_dates.year == year) & all_dates.month.isin([m for m in months if m < 7]))
            ]
        else:
            raise AssertionError(period)
        return dates

    classified: list[pd.DataFrame] = []
    annual = obs.assign(period="annual", year=obs["date"].dt.year)
    classified.append(annual)
    wet = obs[obs["date"].dt.month.isin(tuple(wet_months))].assign(
        period="wet", year=lambda frame: frame["date"].dt.year
    )
    classified.append(wet)
    dry_mask = obs["date"].dt.month.isin(tuple(dry_months))
    dry = obs[dry_mask].copy()
    dry["period"] = "dry"
    dry["year"] = dry["date"].dt.year + (dry["date"].dt.month >= 7).astype(int)
    classified.append(dry)
    values = pd.concat(classified, ignore_index=True)
    aggregated = (
        values.groupby(["station_id", "period", "year"], sort=True, observed=True)
        .agg(total_mm=("rain_mm", lambda series: series.sum(min_count=1)), valid_days=("rain_mm", "count"))
        .reset_index()
    )

    frames: list[pd.DataFrame] = []
    candidates = {
        "annual": range(start.year, end.year + 1),
        "wet": range(start.year, end.year + 1),
        "dry": range(start.year, end.year + 2),
    }
    for period, years in candidates.items():
        for year in years:
            dates = expected_dates(period, year)
            frames.append(
                pd.DataFrame(
                    {
                        "station_id": stations,
                        "period": period,
                        "year": year,
                        "period_start": dates.min(),
                        "period_end": dates.max(),
                        "expected_days": len(dates),
                        "source_window_complete": bool(dates.min() >= start and dates.max() <= end),
                    }
                )
            )
    grid = pd.concat(frames, ignore_index=True)
    result = grid.merge(aggregated, on=["station_id", "period", "year"], how="left", validate="one_to_one")
    result["valid_days"] = result["valid_days"].fillna(0).astype(int)
    result["completeness"] = result["valid_days"] / result["expected_days"]
    result["included"] = result["source_window_complete"] & (result["completeness"] >= completeness_threshold)
    order = pd.Categorical(result["period"], categories=["annual", "wet", "dry"], ordered=True)
    result = result.assign(_period_order=order).sort_values(
        ["station_id", "_period_order", "year"], kind="stable", ignore_index=True
    )
    return result.drop(columns="_period_order")
