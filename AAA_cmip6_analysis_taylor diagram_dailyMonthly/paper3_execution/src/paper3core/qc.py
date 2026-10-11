"""Network-aware audit of suspicious all-zero observed station-months."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _zero_run_lengths(values: np.ndarray) -> np.ndarray:
    output = np.zeros(len(values), dtype=int)
    is_zero = values == 0.0
    position = 0
    while position < len(values):
        if not is_zero[position]:
            position += 1
            continue
        stop = position
        while stop < len(values) and is_zero[stop]:
            stop += 1
        output[position:stop] = stop - position
        position = stop
    return output


def diagnose_zero_months(observed: pd.DataFrame, parameters: dict) -> pd.DataFrame:
    """Classify station-months without imputing any rainfall."""
    stations = list(observed.columns)
    year_month = [observed.index.year, observed.index.month]
    monthly = observed.groupby(year_month).sum(min_count=1)
    monthly.index.names = ["year", "month"]
    annual = observed.groupby(observed.index.year).sum(min_count=1)
    runs = pd.DataFrame(
        {
            station: _zero_run_lengths(observed[station].fillna(-1).to_numpy(float))
            for station in stations
        },
        index=observed.index,
    )
    run_max = runs.groupby(year_month).max()
    run_max.index.names = ["year", "month"]
    monthly_climatology = monthly.groupby(level="month").median()
    station_annual_median = annual.median()
    regional_annual_median = annual.median(axis=1)

    rows = []
    for (year, month), totals in monthly.iterrows():
        for station in stations:
            total = float(totals[station])
            neighbours = totals.drop(labels=[station]).astype(float)
            neighbour_median = float(neighbours.median())
            neighbour_fraction = float((neighbours > parameters["neighbour_wet_mm"]).mean())
            climatology = float(monthly_climatology.loc[month, station])
            longest_zero_run = int(run_max.loc[(year, month), station])
            annual_total = float(annual.loc[year, station])
            indicators = {
                "I1_exact_zero": total == 0.0,
                "I2_region_wet": neighbour_median >= parameters["neighbour_median_mm"],
                "I3_neighbours_wet": neighbour_fraction >= parameters["neighbour_frac"],
                "I4_month_normally_wet": climatology >= parameters["own_clim_mm"],
                "I5_long_zero_run": longest_zero_run >= parameters["zero_run_days"],
                "I6_annual_deficit": (
                    annual_total < parameters["annual_deficit_frac"] * station_annual_median[station]
                    and annual_total
                    < parameters["annual_deficit_frac"] * regional_annual_median[year]
                ),
            }
            n_indicators = sum(
                int(indicators[name])
                for name in indicators
                if name != "I1_exact_zero"
            )
            if not indicators["I1_exact_zero"]:
                classification = "not_zero"
            elif (
                not indicators["I4_month_normally_wet"]
                and not indicators["I2_region_wet"]
                and climatology < parameters["confirmed_dry_clim_mm"]
            ):
                classification = "confirmed_zero"
            elif (
                indicators["I2_region_wet"] or indicators["I3_neighbours_wet"]
            ) and n_indicators >= parameters["min_indicators"]:
                classification = "probable_missing"
            else:
                classification = "uncertain"
            rows.append(
                {
                    "station": str(station),
                    "year": int(year),
                    "month": int(month),
                    "monthly_total_mm": total,
                    "neighbour_median_mm": neighbour_median,
                    "neighbour_fraction_wet": neighbour_fraction,
                    "own_climatology_median_mm": climatology,
                    "max_zero_run_days": longest_zero_run,
                    "annual_total_mm": annual_total,
                    **indicators,
                    "n_indicators": int(n_indicators),
                    "classification": classification,
                }
            )
    return pd.DataFrame(rows)


def apply_zero_month_flags(
    observed: pd.DataFrame,
    diagnostics: pd.DataFrame,
    *,
    classes: tuple[str, ...] = ("probable_missing",),
) -> tuple[pd.DataFrame, int]:
    """Turn only pre-specified suspicious station-months into missing values."""
    output = observed.copy()
    changed = 0
    for row in diagnostics[diagnostics["classification"].isin(classes)].itertuples():
        mask = (output.index.year == row.year) & (output.index.month == row.month)
        changed += int(output.loc[mask, row.station].notna().sum())
        output.loc[mask, row.station] = np.nan
    return output, changed

