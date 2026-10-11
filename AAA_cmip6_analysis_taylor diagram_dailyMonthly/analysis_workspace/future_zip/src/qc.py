# -*- coding: utf-8 -*-
"""
src/qc.py — WMO-style quality control and hydrological-year seasonal
aggregation. Drop-not-fill throughout: incomplete periods are EXCLUDED,
never imputed or interpolated (project-wide no-imputation standard).

===============================================================================
CRITICAL FIX (v2.3 -> v2.4): structural (calendar-boundary) completeness
===============================================================================
Found by direct audit against the real 1981-2014 record: the Dry season
(hydrological year, Nov(Y-1)-Apr(Y)) was returning N=35 valid years instead
of the correct N=33.

Root cause: `build_valid_dry_years` (and, by the same latent logic,
`build_valid_annual_years`) checked QC only on the (year/water_year, month)
groups that actually EXIST as rows in the dataframe. If an entire calendar
month is missing from the source file altogether (not "missing some days
within a present month", but the month-row never appears at all), that
absence produces NO row in the groupby — so it can never contribute a
"False" to the `.all()` / `.mean()` QC check. The missing month is invisible
to the completeness test, so the surrounding year is wrongly counted valid.

This bites specifically at the two ends of the hydrological-year (water-year)
range: the file starts 1981-01-01 and ends 2014-12-31.
  - water_year 1981 requires Nov+Dec 1980 (before the file starts) + Jan-Apr
    1981. Nov/Dec 1980 do not exist in the file AT ALL -> water_year 1981 is
    structurally a 4-month "season", not 6, and must be EXCLUDED.
  - water_year 2015 requires Nov+Dec 2014 (present) + Jan-Apr 2015 (after the
    file ends). Jan-Apr 2015 do not exist -> water_year 2015 is structurally
    a 2-month "season" and must be EXCLUDED.
  - Correct range: water_year 1982 .. 2014 = 33 complete hydrological years.

Verified directly (not assumed):
    df[(water_year==1981) & month in DRY_MONTHS]['month'].unique() -> [1,2,3,4]      (missing 11,12)
    df[(water_year==2015) & month in DRY_MONTHS]['month'].unique() -> [11,12]        (missing 1,2,3,4)

FIX: every `build_valid_*_years` function now first computes which
candidate years are STRUCTURALLY possible at all — i.e., their full
required calendar-month span (accounting for the hydrological-year
rollover) falls entirely within the dataset's actual min/max date — using
only the shared `date` column (station-agnostic, since a missing month is a
file-level fact, not a per-station one). Only years that pass this
structural test are then subjected to the existing per-station WMO daily/
monthly QC. This generalizes correctly to ANY season definition (via
`config.WET_MONTHS` / `config.DRY_MONTHS` / `config.HYDRO_YEAR_ROLLOVER_MONTHS`)
and to a NEW study area whose record does not start on 1 January or end on
31 December (area-agnostic reuse requirement) — the structural check is
computed from config + the data's own dates, nothing is hard-coded.

Additionally, the Wet season's valid-year list previously borrowed the
ANNUAL season's QC gate (`mean() >= COMPLETENESS_THRESHOLD` over ALL 12
months), not a check of the 6 Wet months specifically. A year could pass
the (weaker, mismatched) Annual gate while still missing/failing one of its
own Wet months. `build_valid_wet_years` now performs the same dedicated,
season-specific QC as Dry (structural completeness + per-month WMO QC),
so every season (Annual/Wet/Dry) is validated on its own actual
requirements. This did not change any output for the current 1981-2014
Prachuap dataset (no wet month is ever entirely missing in this file — see
CHANGELOG_v2.3_to_v2.4.md for the verification), but is required for
methodological correctness and for safe reuse with other datasets.
===============================================================================
"""

import numpy as np
import pandas as pd

import config


# =============================================================================
# WMO DAILY/MONTHLY QC (unchanged from v2.3)
# =============================================================================

def longest_nan_run(x):
    is_nan = x.isna().astype(int)
    groups = (is_nan != is_nan.shift()).cumsum()
    run_lengths = is_nan.groupby(groups).sum()
    if len(run_lengths) == 0:
        return 0
    return run_lengths.max()


def qc_monthly(series):
    """WMO-style monthly QC (WMO-No. 1203)."""
    total_missing = series.isna().sum()
    consecutive_missing = longest_nan_run(series)
    if total_missing > config.MAX_MONTHLY_MISSING:
        return False
    if consecutive_missing > config.MAX_CONSECUTIVE_MISSING:
        return False
    return True


# =============================================================================
# STRUCTURAL (CALENDAR-BOUNDARY) COMPLETENESS — the v2.4 fix
# =============================================================================

def _required_calendar_months(year_value, months, rollover_months, is_water_year):
    """
    Map a season's month list to the actual (calendar_year, month) pairs
    required for one 'year_value' (a plain calendar year, or a hydrological/
    water year), honouring the rollover-months definition. Returns the pairs
    sorted chronologically so the first/last entries give the season's true
    start and end month — this is what lets the same logic handle a season
    that wraps across a calendar-year boundary (e.g. Nov-Apr) as well as one
    that does not (e.g. May-Oct, or Jan-Dec).
    """
    pairs = []
    for m in months:
        cy = year_value - 1 if (is_water_year and m in rollover_months) else year_value
        pairs.append((cy, m))
    pairs.sort()
    return pairs


def _season_date_span(year_value, months, rollover_months, is_water_year):
    """The [start, end] calendar-date span required for `year_value` to be a
    STRUCTURALLY complete season (before any per-station QC is even considered)."""
    pairs = _required_calendar_months(int(year_value), months, rollover_months, is_water_year)
    start_cy, start_m = pairs[0]
    end_cy, end_m = pairs[-1]
    start_date = pd.Timestamp(year=start_cy, month=start_m, day=1)
    end_date = pd.Timestamp(year=end_cy, month=end_m, day=1) + pd.offsets.MonthEnd(0)
    return start_date, end_date


def structurally_possible_years(df, year_col, months, rollover_months, is_water_year):
    """
    Candidate years/water-years whose FULL required calendar-month span lies
    entirely within the dataset's actual date range. This depends only on
    the shared `date` column (a missing month is a file-level fact, true for
    every station identically), so it is computed once, not per-station.
    """
    data_min, data_max = df["date"].min(), df["date"].max()
    possible = []
    for yv in sorted(df[year_col].unique()):
        start_date, end_date = _season_date_span(yv, months, rollover_months, is_water_year)
        if start_date >= data_min and end_date <= data_max:
            possible.append(yv)
    return possible


# =============================================================================
# PER-SEASON VALID-YEAR BUILDERS
# Each: (1) restricts candidates to structurally-possible years, THEN
#       (2) applies the existing per-station WMO monthly QC on top.
# Each returns (valid_years, n_structurally_possible) so the caller can use
# the season-correct denominator for the Completeness column, instead of a
# single blanket calendar-year count shared across all three seasons.
# =============================================================================

def build_valid_annual_years(df, st):
    possible = structurally_possible_years(df, "year", list(range(1, 13)), [], is_water_year=False)
    possible_set = set(possible)

    qc_flags = []
    for (yy, mm), g in df.groupby(["year", "month"]):
        if yy not in possible_set:
            continue
        qc_flags.append({"year": yy, "month": mm, "valid": qc_monthly(g[st])})
    qc_df = pd.DataFrame(qc_flags)

    valid_years = []
    if len(qc_df) > 0:
        for yy, g in qc_df.groupby("year"):
            if g["valid"].mean() >= config.COMPLETENESS_THRESHOLD:
                valid_years.append(yy)
    return valid_years, len(possible)


def build_valid_wet_years(df, st):
    possible = structurally_possible_years(df, "year", config.WET_MONTHS, [], is_water_year=False)
    possible_set = set(possible)

    wet_df = df[df["month"].isin(config.WET_MONTHS)]
    qc_flags = []
    for (yy, mm), g in wet_df.groupby(["year", "month"]):
        if yy not in possible_set:
            continue
        qc_flags.append({"year": yy, "month": mm, "valid": qc_monthly(g[st])})
    qc_df = pd.DataFrame(qc_flags)

    valid_years = []
    if len(qc_df) > 0:
        for yy, g in qc_df.groupby("year"):
            if config.STRICT_WET_QC:
                if g["valid"].all():
                    valid_years.append(yy)
            else:
                if g["valid"].mean() >= config.COMPLETENESS_THRESHOLD:
                    valid_years.append(yy)
    return valid_years, len(possible)


def build_valid_dry_years(df, st):
    possible = structurally_possible_years(
        df, "water_year", config.DRY_MONTHS, config.HYDRO_YEAR_ROLLOVER_MONTHS, is_water_year=True
    )
    possible_set = set(possible)

    dry_df = df[df["month"].isin(config.DRY_MONTHS)]
    qc_flags = []
    for (wy, mm), g in dry_df.groupby(["water_year", "month"]):
        if wy not in possible_set:
            continue
        qc_flags.append({"water_year": wy, "month": mm, "valid": qc_monthly(g[st])})
    qc_df = pd.DataFrame(qc_flags)

    valid_wy = []
    if len(qc_df) > 0:
        for wy, g in qc_df.groupby("water_year"):
            if config.STRICT_DRY_QC:
                if g["valid"].all():
                    valid_wy.append(wy)
            else:
                if g["valid"].mean() >= config.COMPLETENESS_THRESHOLD:
                    valid_wy.append(wy)
    return valid_wy, len(possible)


# =============================================================================
# SEASONAL AGGREGATION (drop-not-fill; min_count=1; no imputation)
# =============================================================================

def split_season(df, st, valid_years, valid_wet_years, valid_dry_years):
    annual_df = df[df["year"].isin(valid_years)]
    annual = annual_df.groupby("year")[st].sum(min_count=1)

    wet_df = df[(df["year"].isin(valid_wet_years)) & (df["month"].isin(config.WET_MONTHS))]
    wet = wet_df.groupby("year")[st].sum(min_count=1)

    dry_df = df[(df["water_year"].isin(valid_dry_years)) & (df["month"].isin(config.DRY_MONTHS))]
    dry = dry_df.groupby("water_year")[st].sum(min_count=1)

    return {"Annual": annual, "Wet": wet, "Dry": dry}


def check_completeness(series, n_structurally_possible):
    """
    Completeness = (years that passed QC and are present) / (years that
    were EVER structurally possible for this season, given the record's
    real date range) — a season-correct denominator, not a blanket
    calendar-year count shared across Annual/Wet/Dry.
    """
    valid_years = len(series.dropna())
    return valid_years / n_structurally_possible if n_structurally_possible > 0 else np.nan
