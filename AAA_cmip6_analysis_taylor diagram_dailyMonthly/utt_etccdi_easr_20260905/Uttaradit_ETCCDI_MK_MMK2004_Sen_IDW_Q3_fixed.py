#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Uttaradit Extreme Precipitation Trend Analysis
================================================

Publication-oriented analysis for:

    Spatiotemporal Trends of ETCCDI-Based Extreme Precipitation Indices
    in Uttaradit Province, Thailand

Core scope ONLY
----------------
1. 11 extreme-precipitation indices:
   PRCPTOT, SDII, Rx1day, Rx5day, CDD, CWD,
   R10mm, R20mm, R50mm, R95p, R99p

2. Two periods:
   - Observed: 1981-2014
   - Future:   2021-2050

3. Trend methods:
   - Standard Mann-Kendall (MK)
   - Yue & Wang (2004) effective-sample-size modified MK (MMK-2004)
   - Sen's slope + 95% CI

4. Future spatial change:
   - model-consistent baseline: 1995-2014
   - SSP2-4.5 and SSP5-8.5
   - 7-model median at each station
   - IDW interpolation for visualization

Explicitly excluded
--------------------
Pettitt, FDR, Bonferroni, pre-whitening, TFPW, seasonal trends,
monthly trends, Taylor diagrams, and non-target indices.

IMPORTANT TERMINOLOGY
---------------------
The requested "MMK 2004" is not a 2004 Hamed & Rao method.
The appropriate citation is:

Yue, S., & Wang, C. Y. (2004). The Mann-Kendall test modified by
effective sample size to detect trend in serially correlated
hydrological series. Water Resources Management, 18, 201-218.
doi:10.1023/B:WARM.0000043140.61082.60

The implementation below follows the Yue & Wang (2004) effective
sample size / variance-correction approach:
- estimate Sen slope;
- detrend the series using that slope;
- estimate serial correlation from the detrended series;
- use the full lag structure in the effective-sample-size correction;
- adjust Var(S) by n/n*;
- calculate the corrected Z and two-sided p-value.

The standard MK result is retained as a transparent reference.
The Sen slope itself is NOT changed by MMK; MMK changes inference
about significance through the variance correction.

Data assumptions
----------------
Observed CSV:
    YEAR, MONTH, DAY, <station columns>

CMIP6 CSV:
    YEAR, MONTH, DAY, <station columns>

The archive supplied with this project contains 63 station columns
for the CMIP6 files, but the analysis automatically intersects those
columns with the observed rainfall file and station_coordinates.xlsx.
The intended Uttaradit network is therefore data-driven rather than
hard-coded.

Expected archive layout after extraction
-----------------------------------------
dataUttaradit/
    Observed_Rain_daily_198101_201412_Uttaradit.csv
    station_coordinates.xlsx
    GCM raindata/
        ACCESS-ESM1-5/
            bc_pr_day_...historical....csv
            bc_pr_day_...ssp245....csv
            bc_pr_day_...ssp585....csv
        CanESM5/
            ...
        CESM2/
            ...
        EC-Earth3_CSV_FILE/
            ...
        FGOALS-g3/
            ...
        MIROC6/
            ...
        MRI-ESM2-0/
            ...

Outputs
-------
output_utt_trend/
    results/
        observed_trend_1981_2014.csv
        future_trend_2021_2050.csv
        future_change_2021_2050.csv
        observed_indices_1981_2014.csv
        future_indices_2021_2050.csv
        station_coordinates_used.csv
        qc_observed.csv
        qc_models.csv
        summary_by_index.csv
        summary_by_model_scenario.csv
        README_results.txt
        Uttaradit_Trend_Analysis.xlsx
    figures/
        observed_trends_1981_2014_<index>.png
        future_trends_2021_2050_<scenario>_<index>.png
        future_change_IDW_2021_2050_<scenario>_<index>.png
        observed_trend_heatmap.png
        future_trend_heatmap_<scenario>.png

Dependencies
------------
numpy
pandas
scipy
matplotlib
openpyxl
(optional) geopandas for province boundary plotting
(optional) rarfile + UnRAR/WinRAR/7-Zip if passing the .rar archive
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import re
import shutil
import sys
import warnings
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.lines import Line2D
from matplotlib.path import Path as MplPath
import matplotlib.patheffects as patheffects
import shapefile


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

VERSION = "2.0.0"


@dataclass(frozen=True)
class AnalysisConfig:
    """Locked scientific settings for the Uttaradit analysis."""

    obs_start: int = 1981
    obs_end: int = 2014
    baseline_start: int = 1995
    baseline_end: int = 2014
    future_start: int = 2021
    future_end: int = 2050
    alpha: float = 0.05
    min_trend_n: int = 10
    annual_completeness: float = 0.90
    wet_day_threshold_mm: float = 1.0
    r10_threshold_mm: float = 10.0
    r20_threshold_mm: float = 20.0
    r50_threshold_mm: float = 50.0
    p95: float = 95.0
    p99: float = 99.0
    idw_power: float = 2.0


CONFIG = AnalysisConfig()
ALPHA = CONFIG.alpha
MIN_YEARS = CONFIG.min_trend_n
MIN_ANNUAL_COMPLETENESS = CONFIG.annual_completeness
OBS_START, OBS_END = CONFIG.obs_start, CONFIG.obs_end
BASELINE_START, BASELINE_END = CONFIG.baseline_start, CONFIG.baseline_end
FUTURE_START, FUTURE_END = CONFIG.future_start, CONFIG.future_end
WET_THRESHOLD = CONFIG.wet_day_threshold_mm
R10_THRESHOLD = CONFIG.r10_threshold_mm
R20_THRESHOLD = CONFIG.r20_threshold_mm
R50_THRESHOLD = CONFIG.r50_threshold_mm
P95, P99 = CONFIG.p95, CONFIG.p99

INDICES = [
    "PRCPTOT",
    "SDII",
    "Rx1day",
    "Rx5day",
    "CDD",
    "CWD",
    "R10mm",
    "R20mm",
    "R50mm",
    "R95p",
    "R99p",
]

INDEX_UNITS = {
    "PRCPTOT": "mm",
    "SDII": "mm day-1",
    "Rx1day": "mm",
    "Rx5day": "mm",
    "CDD": "days",
    "CWD": "days",
    "R10mm": "days",
    "R20mm": "days",
    "R50mm": "days",
    "R95p": "mm",
    "R99p": "mm",
}

SLOPE_UNITS = {
    "PRCPTOT": "mm year-1",
    "SDII": "mm day-1 year-1",
    "Rx1day": "mm year-1",
    "Rx5day": "mm year-1",
    "CDD": "days year-1",
    "CWD": "days year-1",
    "R10mm": "days year-1",
    "R20mm": "days year-1",
    "R50mm": "days year-1",
    "R95p": "mm year-1",
    "R99p": "mm year-1",
}

SCENARIOS = {
    "ssp245": "SSP2-4.5",
    "ssp585": "SSP5-8.5",
}

EXPECTED_MODELS = [
    "ACCESS-ESM1-5",
    "CanESM5",
    "CESM2",
    "EC-Earth3",
    "FGOALS-g3",
    "MIROC6",
    "MRI-ESM2-0",
]

EXPECTED_STATIONS = {
    "351001", "351002", "351003", "351004", "351005", "351006",
    "351007", "351008", "351009", "351010", "351011", "351012",
    "351201",
}

MISS_FLAGS = [-99.9, -99.99, -999.0, -999.9, -9999.0]


# ---------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------

EXECUTION_LOG: List[str] = []


def log(msg: str) -> None:
    text = str(msg)
    EXECUTION_LOG.append(text)
    print(text, flush=True)


def safe_float(x, default=np.nan) -> float:
    try:
        v = float(x)
        return v if np.isfinite(v) else default
    except (TypeError, ValueError):
        return default


def trend_label(z: float, p: float, alpha: float = ALPHA) -> str:
    if not np.isfinite(z) or not np.isfinite(p):
        return "Insufficient data"
    if p < alpha:
        if z > 0:
            return "Increasing"
        if z < 0:
            return "Decreasing"
    return "No significant trend"


def significance_code(p: float, alpha: float = ALPHA) -> str:
    if not np.isfinite(p):
        return "NA"
    return "*" if p < alpha else "ns"


def normalize_station_id(value) -> str:
    s = str(value).strip()
    if re.fullmatch(r"\d+\.0", s):
        s = s[:-2]
    return s


def canonical_model_name(name: str) -> str:
    s = name.strip()
    aliases = {
        "EC-Earth3_CSV_FILE": "EC-Earth3",
        "EC-Earth3_CSV": "EC-Earth3",
        "EC-Earth3": "EC-Earth3",
    }
    return aliases.get(s, s)


def parse_model_from_filename(path: Path) -> Optional[str]:
    stem = path.stem
    for model in EXPECTED_MODELS:
        if model.lower() in stem.lower():
            return model
    if "EC-Earth3" in stem:
        return "EC-Earth3"
    return None


def parse_scenario_from_filename(path: Path) -> Optional[str]:
    stem = path.stem.lower()
    if "ssp245" in stem or "ssp2-4.5" in stem:
        return "ssp245"
    if "ssp585" in stem or "ssp5-8.5" in stem:
        return "ssp585"
    return None


# ---------------------------------------------------------------------
# Archive handling
# ---------------------------------------------------------------------

def prepare_input_root(input_path: Path) -> Path:
    """
    Accept either an extracted data directory or dataUttaradit.rar.

    RAR extraction requires an installed external extractor supported by
    the rarfile package. If unavailable, the error is explicit.
    """
    input_path = input_path.expanduser().resolve()

    if input_path.is_dir():
        return input_path

    if input_path.suffix.lower() != ".rar":
        raise FileNotFoundError(
            f"Input must be a directory or .rar archive: {input_path}"
        )

    extracted = input_path.with_name(input_path.stem + "_extracted")
    marker = extracted / ".extraction_complete"

    if marker.exists():
        return extracted

    try:
        import rarfile
    except ImportError as exc:
        raise RuntimeError(
            "RAR input detected, but package 'rarfile' is not installed. "
            "Install it with: pip install rarfile"
        ) from exc

    extracted.mkdir(parents=True, exist_ok=True)

    try:
        with rarfile.RarFile(str(input_path)) as rf:
            rf.extractall(str(extracted))
    except Exception as exc:
        raise RuntimeError(
            "RAR extraction failed. The Python rarfile package also needs "
            "a working external extractor (UnRAR, WinRAR, 7-Zip, etc.). "
            f"Original error: {exc}"
        ) from exc

    marker.write_text("complete\n", encoding="utf-8")
    return extracted


def locate_data_root(root: Path) -> Path:
    candidates = [root, root / "dataUttaradit"]
    for p in candidates:
        if (p / "Observed_Rain_daily_198101_201412_Uttaradit.csv").exists():
            return p

    matches = list(root.rglob("Observed_Rain_daily_198101_201412_Uttaradit.csv"))
    if matches:
        return matches[0].parent

    raise FileNotFoundError(
        "Could not locate Observed_Rain_daily_198101_201412_Uttaradit.csv"
    )


# ---------------------------------------------------------------------
# Data loading and QC
# ---------------------------------------------------------------------

def load_daily_csv(path: Path) -> pd.DataFrame:
    """
    Load a daily rainfall CSV with YEAR/MONTH/DAY columns.

    Missing-value sentinels are converted to NaN. Invalid dates, duplicate
    calendar records, duplicate normalized station IDs, non-numeric values,
    and negative precipitation are rejected explicitly rather than silently
    repaired. Extreme but finite non-negative rainfall is retained.
    """
    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]

    required = {"YEAR", "MONTH", "DAY"}
    if not required.issubset(df.columns):
        raise ValueError(
            f"{path.name}: required columns YEAR, MONTH, DAY not found."
        )

    station_cols = [c for c in df.columns if c not in required]
    # Some station archives carry a trailing spreadsheet export column such
    # as ``Unnamed: 31``.  Drop it only when it is explicitly empty; a
    # non-empty unexpected column remains visible and is validated normally.
    empty_export_cols = [
        c for c in station_cols
        if str(c).strip().lower().startswith("unnamed") and df[c].isna().all()
    ]
    if empty_export_cols:
        station_cols = [c for c in station_cols if c not in empty_export_cols]
    if not station_cols:
        raise ValueError(f"{path.name}: no station rainfall columns found.")

    normalized = [normalize_station_id(c) for c in station_cols]
    duplicates = sorted({s for s in normalized if normalized.count(s) > 1})
    if duplicates:
        raise ValueError(
            f"{path.name}: duplicate normalized station columns: {duplicates}"
        )

    station_data = df.loc[:, station_cols].copy()
    station_data.columns = normalized
    for flag in MISS_FLAGS:
        station_data = station_data.mask(station_data == flag)

    for station in station_data.columns:
        raw = station_data[station]
        numeric = pd.to_numeric(raw, errors="coerce")
        invalid_nonmissing = raw.notna() & numeric.isna()
        if invalid_nonmissing.any():
            examples = raw.loc[invalid_nonmissing].head(5).tolist()
            raise ValueError(
                f"{path.name}: non-numeric rainfall in station {station}; "
                f"examples={examples}"
            )
        if (numeric < 0).any():
            count = int((numeric < 0).sum())
            raise ValueError(
                f"{path.name}: {count} negative rainfall values in station "
                f"{station}; values were not changed automatically."
            )
        station_data[station] = numeric

    dt = pd.to_datetime(
        {
            "year": pd.to_numeric(df["YEAR"], errors="coerce"),
            "month": pd.to_numeric(df["MONTH"], errors="coerce"),
            "day": pd.to_numeric(df["DAY"], errors="coerce"),
        },
        errors="coerce",
    )

    if dt.isna().any():
        raise ValueError(
            f"{path.name}: {int(dt.isna().sum())} invalid calendar dates."
        )

    out = station_data.copy()
    out.index = pd.DatetimeIndex(dt)
    out.index.name = "date"

    if out.index.duplicated().any():
        duplicated = out.index[out.index.duplicated(keep=False)]
        sample = [str(v.date()) for v in duplicated[:5]]
        raise ValueError(
            f"{path.name}: duplicate daily dates detected; examples={sample}"
        )

    out = out.sort_index()

    return out


def qc_daily(
    df: pd.DataFrame,
    expected_start: Optional[str] = None,
    expected_end: Optional[str] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    QC without deleting valid extreme rainfall.

    Short-gap interpolation is NOT used by default. For extreme indices,
    artificial rainfall can alter counts, spell lengths, percentile
    exceedances, and maxima. Missing values therefore remain NaN.

    Annual completeness is returned from ``annual_extreme_indices`` so its
    count definition is shared exactly with the index calculation gate.
    """
    out = df.copy()

    if expected_start:
        out = out.loc[out.index >= pd.Timestamp(expected_start)]
    if expected_end:
        out = out.loc[out.index <= pd.Timestamp(expected_end)]

    rows = []
    for station in out.columns:
        s = out[station]
        n = len(s)
        missing = int(s.isna().sum())
        valid = int(s.notna().sum())

        calendar_days = (
            len(pd.date_range(out.index.min(), out.index.max(), freq="D"))
            if len(out.index)
            else 0
        )
        missing_calendar_dates = calendar_days - len(out.index)

        rows.append(
            {
                "Station": normalize_station_id(station),
                "N_records": n,
                "N_valid": valid,
                "N_missing": missing,
                "Missing_pct": 100.0 * missing / max(n, 1),
                "Min_valid": float(s.min()) if valid else np.nan,
                "Max_valid": float(s.max()) if valid else np.nan,
                "Median_valid": float(s.median()) if valid else np.nan,
                "Mean_valid": float(s.mean()) if valid else np.nan,
                "Start_date": out.index.min().strftime("%Y-%m-%d") if len(out.index) else None,
                "End_date": out.index.max().strftime("%Y-%m-%d") if len(out.index) else None,
                "Missing_calendar_dates": int(missing_calendar_dates),
                "Status": "OK" if missing == 0 and missing_calendar_dates == 0 else "HAS_MISSING",
            }
        )

    return out, pd.DataFrame(rows)


def read_coordinates(path: Path) -> pd.DataFrame:
    """
    Read a coordinate workbook or CSV and normalize Station/Station_ID plus
    latitude, longitude, and optional elevation without deleting invalid rows.
    """
    chosen = None
    if Path(path).suffix.lower() == ".csv":
        tables = [pd.read_csv(path)]
    else:
        with pd.ExcelFile(path) as xl:
            tables = [pd.read_excel(xl, sheet_name=sheet) for sheet in xl.sheet_names]
    for tmp in tables:
        cols = {str(c).strip().lower(): c for c in tmp.columns}
        station_col = next(
            (cols[name] for name in ("station", "station_id", "stationid") if name in cols),
            None,
        )
        if station_col is not None and {"latitude", "longitude"}.issubset(cols):
            chosen = tmp.rename(
                columns={
                    station_col: "station",
                    cols["latitude"]: "latitude",
                    cols["longitude"]: "longitude",
                }
            )
            if "elevation" in cols:
                chosen = chosen.rename(columns={cols["elevation"]: "elevation"})
            break

    if chosen is None:
        raise ValueError(
            "Coordinate workbook must contain Station/Station_ID, latitude, longitude."
        )

    chosen["station"] = chosen["station"].map(normalize_station_id)
    chosen["latitude"] = pd.to_numeric(chosen["latitude"], errors="coerce")
    chosen["longitude"] = pd.to_numeric(chosen["longitude"], errors="coerce")
    if "elevation" in chosen.columns:
        chosen["elevation"] = pd.to_numeric(
            chosen["elevation"], errors="coerce"
        )

    if chosen[["station", "latitude", "longitude"]].isna().any().any():
        raise ValueError("Coordinate workbook contains missing station or coordinate values.")
    if chosen["station"].duplicated().any():
        duplicates = chosen.loc[chosen["station"].duplicated(keep=False), "station"].tolist()
        raise ValueError(f"Coordinate workbook has duplicate stations: {duplicates}")
    if (~np.isfinite(chosen["latitude"]) | ~np.isfinite(chosen["longitude"])).any():
        raise ValueError("Coordinate workbook contains non-finite coordinates.")
    if ((chosen["latitude"] < -90) | (chosen["latitude"] > 90)).any():
        raise ValueError("Coordinate workbook contains latitude outside [-90, 90].")
    if ((chosen["longitude"] < -180) | (chosen["longitude"] > 180)).any():
        raise ValueError("Coordinate workbook contains longitude outside [-180, 180].")
    return chosen.reset_index(drop=True)


def validate_station_network(observed: pd.DataFrame, coords: pd.DataFrame) -> List[str]:
    """Require the locked 13-station network in observed data and coordinates."""
    observed_ids = {normalize_station_id(c) for c in observed.columns}
    coord_ids = set(coords["station"].map(normalize_station_id))
    if observed_ids != EXPECTED_STATIONS:
        raise ValueError(
            "Observed station set does not match the locked Uttaradit network; "
            f"missing={sorted(EXPECTED_STATIONS - observed_ids)}, "
            f"unexpected={sorted(observed_ids - EXPECTED_STATIONS)}"
        )
    if coord_ids != EXPECTED_STATIONS:
        raise ValueError(
            "Coordinate station set does not match the locked Uttaradit network; "
            f"missing={sorted(EXPECTED_STATIONS - coord_ids)}, "
            f"unexpected={sorted(coord_ids - EXPECTED_STATIONS)}"
        )
    return sorted(EXPECTED_STATIONS)


# ---------------------------------------------------------------------
# ETCCDI-based indices
# ---------------------------------------------------------------------

def max_consecutive(mask: np.ndarray) -> float:
    if len(mask) == 0:
        return np.nan

    best = 0
    run = 0
    for value in mask:
        if bool(value):
            run += 1
            best = max(best, run)
        else:
            run = 0

    return float(best)


def rolling_rx5(values: np.ndarray) -> float:
    if len(values) < 5:
        return np.nan

    # NaN in any 5-day window invalidates that window.
    valid = np.isfinite(values)
    if not valid.all():
        arr = pd.Series(values)
        roll = arr.rolling(5, min_periods=5).sum().to_numpy()
        return float(np.nanmax(roll)) if np.isfinite(roll).any() else np.nan

    return float(np.max(np.convolve(values, np.ones(5), mode="valid")))


def station_thresholds_from_observed(
    observed_daily: pd.DataFrame,
) -> Dict[str, Tuple[float, float]]:
    """
    Station-specific P95/P99 thresholds from all observed wet days
    (1981-2014), then held fixed for both observed and future calculations.
    """
    thresholds = {}

    for station in observed_daily.columns:
        s = observed_daily[station].dropna()
        wet = s[s >= WET_THRESHOLD]

        if len(wet) < 10:
            thresholds[normalize_station_id(station)] = (np.nan, np.nan)
        else:
            thresholds[normalize_station_id(station)] = (
                float(np.percentile(wet, P95)),
                float(np.percentile(wet, P99)),
            )

    return thresholds


def annual_extreme_indices(
    daily: pd.DataFrame,
    thresholds: Dict[str, Tuple[float, float]],
    return_qc: bool = False,
) -> pd.DataFrame | Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Calculate exactly the 11 target indices for each station-year.

    ETCCDI-style definitions:
      PRCPTOT: total precipitation on wet days >= 1 mm
      SDII: PRCPTOT / number of wet days
      Rx1day: annual maximum daily precipitation
      Rx5day: annual maximum consecutive 5-day total
      CDD: maximum consecutive days < 1 mm
      CWD: maximum consecutive days >= 1 mm
      R10mm: count >= 10 mm
      R20mm: count >= 20 mm
      R50mm: count >= 50 mm (study-specific)
      R95p: annual total on days > observed P95
      R99p: annual total on days > observed P99

    A calendar year is the unit of aggregation.
    """
    if daily.empty:
        empty = pd.DataFrame(columns=["Station", "Year", *INDICES]).set_index(["Station", "Year"])
        return (empty, pd.DataFrame()) if return_qc else empty
    if not isinstance(daily.index, pd.DatetimeIndex):
        raise TypeError("Daily rainfall must have a DatetimeIndex.")

    rows: List[Dict[str, object]] = []
    qc_rows: List[Dict[str, object]] = []
    years = range(int(daily.index.year.min()), int(daily.index.year.max()) + 1)

    for station in daily.columns:
        sid = normalize_station_id(station)
        p95, p99 = thresholds.get(sid, (np.nan, np.nan))
        source = pd.to_numeric(daily[station], errors="coerce")

        for year in years:
            calendar = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
            original = source.loc[source.index.year == year]
            x = source.reindex(calendar).to_numpy(dtype=float)
            finite = np.isfinite(x)
            expected_days = len(calendar)
            n_observed = int(len(original))
            n_valid = int(finite.sum())
            completeness = n_valid / expected_days
            missing_days = expected_days - n_valid
            status = "OK"

            if n_observed == 0:
                status = "MISSING_YEAR"
            elif completeness < MIN_ANNUAL_COMPLETENESS:
                status = "INCOMPLETE_YEAR"
            elif not np.isfinite(p95) or not np.isfinite(p99):
                status = "THRESHOLD_UNAVAILABLE"

            qc_rows.append(
                {
                    "Station": sid,
                    "Year": year,
                    "n_expected_days": expected_days,
                    "n_observed_records": n_observed,
                    "n_valid": n_valid,
                    "completeness_pct": 100.0 * completeness,
                    "missing_days": missing_days,
                    "status": status,
                }
            )

            if status in {"MISSING_YEAR", "INCOMPLETE_YEAR"}:
                row = {idx: np.nan for idx in INDICES}
                row.update({"Station": sid, "Year": year, "Annual_status": status})
                rows.append(row)
                continue

            wet = x[finite & (x >= WET_THRESHOLD)]
            prcptot = float(wet.sum()) if len(wet) else 0.0
            sdii = float(wet.mean()) if len(wet) else np.nan
            rx1 = float(np.nanmax(x)) if finite.any() else np.nan
            rx5 = rolling_rx5(x)
            cdd = max_consecutive(finite & (x < WET_THRESHOLD))
            cwd = max_consecutive(finite & (x >= WET_THRESHOLD))
            r10 = float(np.sum(finite & (x >= R10_THRESHOLD)))
            r20 = float(np.sum(finite & (x >= R20_THRESHOLD)))
            r50 = float(np.sum(finite & (x >= R50_THRESHOLD)))
            r95 = float(np.sum(x[finite & (x > p95)])) if np.isfinite(p95) else np.nan
            r99 = float(np.sum(x[finite & (x > p99)])) if np.isfinite(p99) else np.nan

            rows.append(
                {
                    "Station": sid,
                    "Year": year,
                    "Annual_status": status,
                    "PRCPTOT": prcptot,
                    "SDII": sdii,
                    "Rx1day": rx1,
                    "Rx5day": rx5,
                    "CDD": cdd,
                    "CWD": cwd,
                    "R10mm": r10,
                    "R20mm": r20,
                    "R50mm": r50,
                    "R95p": r95,
                    "R99p": r99,
                }
            )

    out = pd.DataFrame(rows).set_index(["Station", "Year"]).sort_index()
    annual_qc = pd.DataFrame(qc_rows).sort_values(["Station", "Year"]).reset_index(drop=True)
    return (out, annual_qc) if return_qc else out


def indices_to_wide(
    index_df: pd.DataFrame,
    index_name: str,
) -> pd.DataFrame:
    if index_df.empty:
        return pd.DataFrame()

    s = index_df[index_name].copy()
    wide = s.unstack("Station")
    wide.index = pd.to_datetime(
        wide.index.astype(int).astype(str) + "-12-31"
    )
    wide.index.name = "date"
    return wide


# ---------------------------------------------------------------------
# Mann-Kendall and Sen's slope
# ---------------------------------------------------------------------

def mk_s_statistic(x: np.ndarray) -> Tuple[float, List[int]]:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)

    if n < 2:
        return np.nan, []

    s = 0
    for i in range(n - 1):
        s += int(np.sign(x[i + 1:] - x[i]).sum())

    _, counts = np.unique(x, return_counts=True)
    ties = [int(c) for c in counts if c > 1]

    return float(s), ties


def mk_variance(n: int, ties: Sequence[int]) -> float:
    if n < 2:
        return np.nan

    tie_term = sum(
        t * (t - 1) * (2 * t + 5)
        for t in ties
    )

    return (
        n * (n - 1) * (2 * n + 5) - tie_term
    ) / 18.0


def z_from_s(s: float, var_s: float) -> float:
    if not np.isfinite(s) or not np.isfinite(var_s):
        return np.nan

    # A completely tied annual series has S=0 and Var(S)=0. It is a valid
    # no-trend result, not insufficient data or a failed calculation.
    if var_s == 0 and s == 0:
        return 0.0
    if var_s <= 0:
        return np.nan

    if s > 0:
        return (s - 1.0) / math.sqrt(var_s)
    if s < 0:
        return (s + 1.0) / math.sqrt(var_s)
    return 0.0


def two_sided_p(z: float) -> float:
    if not np.isfinite(z):
        return np.nan
    return float(2.0 * stats.norm.sf(abs(z)))


def kendall_tau_from_s(s: float, n: int) -> float:
    if n < 2 or not np.isfinite(s):
        return np.nan
    return float(s / (0.5 * n * (n - 1)))


def sen_slope(x: np.ndarray) -> float:
    """
    Sen slope using equally spaced annual observations.

    For an annual series, time spacing is one year. Missing years must
    be removed before this function is called; the caller also records
    the actual first/last years so the analysis remains traceable.
    """
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)

    if n < 2:
        return np.nan

    slopes = []
    for i in range(n - 1):
        dx = x[i + 1:] - x[i]
        dt = np.arange(1, n - i, dtype=float)
        slopes.extend((dx / dt).tolist())

    return float(np.median(np.asarray(slopes, dtype=float)))


def sen_slope_with_years(years: np.ndarray, values: np.ndarray) -> float:
    years = np.asarray(years, dtype=float)
    values = np.asarray(values, dtype=float)

    good = np.isfinite(years) & np.isfinite(values)
    years = years[good]
    values = values[good]

    if len(values) < 2:
        return np.nan

    order = np.argsort(years)
    years = years[order]
    values = values[order]
    if np.unique(years).size != years.size:
        raise ValueError("Sen slope requires unique annual time coordinates.")

    slopes = []
    for i in range(len(values) - 1):
        dy = values[i + 1:] - values[i]
        dt = years[i + 1:] - years[i]
        good_dt = dt != 0
        slopes.extend((dy[good_dt] / dt[good_dt]).tolist())

    return float(np.median(np.asarray(slopes, dtype=float)))


def sen_confidence_interval(
    years: np.ndarray,
    values: np.ndarray,
    alpha: float = ALPHA,
) -> Tuple[float, float]:
    """
    Rank-based Sen slope CI following the standard Gilbert-style
    variance/order-statistic construction.

    This CI is for the slope magnitude and is independent of the
    Yue-Wang variance correction used for MMK significance.
    """
    years = np.asarray(years, dtype=float)
    values = np.asarray(values, dtype=float)

    good = np.isfinite(years) & np.isfinite(values)
    years = years[good]
    values = values[good]
    n = len(values)

    if n < 3:
        return np.nan, np.nan

    order = np.argsort(years)
    years = years[order]
    values = values[order]
    if np.unique(years).size != years.size:
        raise ValueError("Sen confidence interval requires unique annual years.")

    # SciPy implements the Sen (1968) order-statistic interval. Its alpha is
    # confidence level, while this pipeline stores alpha as a significance level.
    result = stats.theilslopes(values, years, alpha=1.0 - alpha)
    return float(result.low_slope), float(result.high_slope)


def lag_autocorrelation(x: np.ndarray, lag: int) -> float:
    x = np.asarray(x, dtype=float)
    if lag <= 0:
        return 1.0
    if len(x) <= lag:
        return np.nan
    if not np.isfinite(x).all():
        return np.nan
    centered = x - np.mean(x)
    denominator = float(np.sum(centered * centered))
    if denominator == 0:
        return 0.0
    return float(np.sum(centered[:-lag] * centered[lag:]) / denominator)


def detrend_by_sen(
    years: np.ndarray,
    values: np.ndarray,
) -> Tuple[np.ndarray, float]:
    years = np.asarray(years, dtype=float)
    values = np.asarray(values, dtype=float)

    beta = sen_slope_with_years(years, values)
    if not np.isfinite(beta):
        return np.full_like(values, np.nan, dtype=float), np.nan

    t0 = float(years[0])
    detrended = values - beta * (years - t0)
    return detrended, beta


def yue_wang_2004_factor(
    years: np.ndarray,
    values: np.ndarray,
) -> Dict[str, object]:
    """
    Yue & Wang (2004) effective-sample-size correction.

    The trend is first removed using Sen's slope. The autocorrelation
    structure is then estimated from the detrended series. The full
    lag structure is used:

        n/n* = 1 + 2 * sum_{k=1}^{n-1} (1-k/n) rho_k

    and

        Var*(S) = Var(S) * (n/n*).

    This is the Yue & Wang (2004) effective-sample-size formulation,
    not the Hamed & Rao (1998) rank-autocorrelation formulation.
    """
    years = np.asarray(years, dtype=float)
    values = np.asarray(values, dtype=float)

    good = np.isfinite(years) & np.isfinite(values)
    years = years[good]
    values = values[good]

    order = np.argsort(years)
    years = years[order]
    values = values[order]
    n = len(values)
    invalid = {
        "factor": np.nan,
        "n_eff": np.nan,
        "slope_detrend": np.nan,
        "lags_used": 0,
        "rho_sum": np.nan,
        "rho_1": np.nan,
        "status": "INSUFFICIENT_DATA",
    }
    if n < 3:
        return invalid
    if np.unique(years).size != years.size:
        invalid["status"] = "DUPLICATE_ANNUAL_YEAR"
        return invalid
    if not np.allclose(np.diff(years), 1.0):
        invalid["status"] = "IRREGULAR_ANNUAL_YEARS"
        return invalid

    detrended, beta = detrend_by_sen(years, values)

    if not np.isfinite(detrended).all():
        invalid.update({"slope_detrend": beta, "status": "INVALID_DETRENDED_SERIES"})
        return invalid

    if np.allclose(detrended, detrended[0], rtol=0.0, atol=1e-12):
        return {
            "factor": 1.0,
            "n_eff": float(n),
            "slope_detrend": float(beta),
            "lags_used": n - 1,
            "rho_sum": 0.0,
            "rho_1": 0.0,
            "status": "ZERO_VARIANCE_RESIDUALS",
        }

    rho_sum = 0.0
    lags_used = 0

    rho_1 = np.nan
    # Yue & Wang (2004): all lags in the ESS formulation.  The
    # autocorrelation estimator above is defined for every lag 1..n-1.
    for k in range(1, n):
        rho = lag_autocorrelation(detrended, k)
        if not np.isfinite(rho):
            invalid.update(
                {"slope_detrend": beta, "lags_used": lags_used, "rho_sum": rho_sum,
                 "rho_1": rho_1, "status": "UNDEFINED_AUTOCORRELATION"}
            )
            return invalid

        rho_sum += (1.0 - k / n) * rho
        lags_used += 1
        if k == 1:
            rho_1 = rho

    factor = 1.0 + 2.0 * rho_sum

    # A non-positive factor cannot define a valid variance.
    if not np.isfinite(factor) or factor <= 0:
        invalid.update(
            {"slope_detrend": beta, "lags_used": lags_used, "rho_sum": rho_sum,
             "rho_1": rho_1, "status": "NONPOSITIVE_ESS_FACTOR"}
        )
        return invalid

    n_eff = n / factor

    return {
        "factor": float(factor),
        "n_eff": float(n_eff),
        "slope_detrend": float(beta),
        "lags_used": int(lags_used),
        "rho_sum": float(rho_sum),
        "rho_1": float(rho_1),
        "status": "FACTOR_LT_ONE" if factor < 1.0 else "OK",
    }


def standard_mk(years: np.ndarray, values: np.ndarray) -> Dict[str, object]:
    years = np.asarray(years, dtype=float)
    values = np.asarray(values, dtype=float)

    good = np.isfinite(years) & np.isfinite(values)
    years = years[good]
    values = values[good]

    order = np.argsort(years)
    years = years[order]
    values = values[order]

    n = len(values)
    if n < MIN_YEARS:
        return {
            "N": n,
            "S": np.nan,
            "Var_S": np.nan,
            "Z": np.nan,
            "p": np.nan,
            "tau": np.nan,
            "slope": np.nan,
            "slope_lo": np.nan,
            "slope_hi": np.nan,
            "trend": "Insufficient data",
            "status": "INSUFFICIENT_DATA",
        }
    if np.unique(years).size != years.size:
        raise ValueError("Mann-Kendall requires unique annual time coordinates.")

    s, ties = mk_s_statistic(values)
    var_s = mk_variance(n, ties)
    z = z_from_s(s, var_s)
    p = two_sided_p(z)
    tau = kendall_tau_from_s(s, n)
    slope = sen_slope_with_years(years, values)
    lo, hi = sen_confidence_interval(years, values)

    return {
        "N": n,
        "S": s,
        "Var_S": var_s,
        "Z": z,
        "p": p,
        "tau": tau,
        "slope": slope,
        "slope_lo": lo,
        "slope_hi": hi,
        "trend": trend_label(z, p),
        "status": "NO_VARIATION" if var_s == 0 else "OK",
    }


def yue_wang_2004_mmk(
    years: np.ndarray,
    values: np.ndarray,
) -> Dict[str, object]:
    """
    Standard MK plus Yue & Wang (2004) ESS variance correction.
    """
    base = standard_mk(years, values)

    if not np.isfinite(base["S"]) or base["N"] < MIN_YEARS:
        base.update(
            {
                "Var_S_adj": np.nan,
                "ESS_factor_n_over_nstar": np.nan,
                "N_eff": np.nan,
                "lags_used": 0,
                "rho_sum": np.nan,
                "MMK_Z": np.nan,
                "MMK_p": np.nan,
                "MMK_trend": "Insufficient data",
                "MMK_status": base.get("status", "INSUFFICIENT_DATA"),
                "rho_1": np.nan,
            }
        )
        return base

    ess = yue_wang_2004_factor(years, values)
    factor = ess["factor"]

    if not np.isfinite(factor):
        base.update(
            {
                "Var_S_adj": np.nan,
                "ESS_factor_n_over_nstar": np.nan,
                "N_eff": np.nan,
                "lags_used": ess["lags_used"],
                "rho_sum": ess["rho_sum"],
                "MMK_Z": np.nan,
                "MMK_p": np.nan,
                "MMK_trend": "Invalid ESS correction",
                "MMK_status": ess["status"],
                "rho_1": ess["rho_1"],
            }
        )
        return base

    var_adj = float(base["Var_S"]) * factor
    z_mmk = z_from_s(float(base["S"]), var_adj)
    p_mmk = two_sided_p(z_mmk)

    base.update(
        {
            "Var_S_adj": var_adj,
            "ESS_factor_n_over_nstar": factor,
            "N_eff": ess["n_eff"],
            "lags_used": ess["lags_used"],
            "rho_sum": ess["rho_sum"],
            "MMK_Z": z_mmk,
            "MMK_p": p_mmk,
            "MMK_trend": trend_label(z_mmk, p_mmk),
            "MMK_status": ess["status"],
            "rho_1": ess["rho_1"],
        }
    )

    return base


# ---------------------------------------------------------------------
# Trend engine
# ---------------------------------------------------------------------

def analyze_index_series(
    series: pd.Series,
    period_label: str,
    station: str,
    index_name: str,
    model: str = "Observed",
    scenario: str = "Historical",
) -> Dict[str, object]:
    if isinstance(series.index, pd.DatetimeIndex):
        years = series.index.year.to_numpy(dtype=float)
    else:
        years = pd.to_numeric(series.index, errors="coerce").to_numpy(dtype=float)
    values = series.to_numpy(dtype=float)

    result = yue_wang_2004_mmk(years, values)

    valid_years = years[np.isfinite(years) & np.isfinite(values)]
    first_year = int(np.min(valid_years)) if len(valid_years) else np.nan
    last_year = int(np.max(valid_years)) if len(valid_years) else np.nan

    return {
        "Period": period_label,
        "Model": model,
        "Scenario": scenario,
        "Station": normalize_station_id(station),
        "Index": index_name,
        "Unit": INDEX_UNITS[index_name],
        "Sen_slope_unit": SLOPE_UNITS[index_name],
        "StartYear": first_year,
        "EndYear": last_year,
        "N": result["N"],
        "S": result["S"],
        "Var_S": result["Var_S"],
        "Var_S_adj_YueWang2004": result["Var_S_adj"],
        "Z_MK": result["Z"],
        "p_MK": result["p"],
        "Trend_MK": result["trend"],
        "Significant_MK": bool(np.isfinite(result["p"]) and result["p"] < ALPHA),
        "Z_MMK2004": result["MMK_Z"],
        "p_MMK2004": result["MMK_p"],
        "Trend_MMK2004": result["MMK_trend"],
        "Significant_MMK2004": bool(np.isfinite(result["MMK_p"]) and result["MMK_p"] < ALPHA),
        "Kendall_tau": result["tau"],
        "Sen_slope": result["slope"],
        "Sen_CI95_low": result["slope_lo"],
        "Sen_CI95_high": result["slope_hi"],
        "n_over_nstar": result["ESS_factor_n_over_nstar"],
        "n_effective": result["N_eff"],
        "ESS_lags_used": result["lags_used"],
        "ESS_weighted_rho_sum": result["rho_sum"],
        "MMK_rho1": result["rho_1"],
        "MK_status": result["status"],
        "MMK_status": result["MMK_status"],
        "MK_MMK_same_conclusion": (
            result["trend"] == result["MMK_trend"]
            if "trend" in result and "MMK_trend" in result
            else False
        ),
    }


def analyze_index_dataframe(
    index_df: pd.DataFrame,
    period_label: str,
    model: str = "Observed",
    scenario: str = "Historical",
) -> pd.DataFrame:
    rows = []

    if index_df.empty:
        return pd.DataFrame()

    for index_name in INDICES:
        if index_name not in index_df.columns:
            continue

        for station in sorted(index_df.index.get_level_values("Station").unique()):
            s = index_df.xs(station, level="Station")[index_name]
            s = s.sort_index()
            s.index = pd.Index(s.index.astype(int), name="Year")

            rows.append(
                analyze_index_series(
                    s,
                    period_label=period_label,
                    station=station,
                    index_name=index_name,
                    model=model,
                    scenario=scenario,
                )
            )

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------
# Future CMIP6 discovery
# ---------------------------------------------------------------------

def discover_bc_model_files(data_root: Path) -> Dict[Tuple[str, str], Path]:
    """
    Discover only supplied bias-corrected CMIP6 daily files.

    Raw model files are intentionally excluded from this paper.
    """
    files = list(data_root.rglob("*.csv"))
    found = {}

    for path in files:
        stem = path.stem.lower()

        if not stem.startswith("bc_"):
            continue

        model = parse_model_from_filename(path)
        if model is None:
            continue

        scenario = parse_scenario_from_filename(path)

        # Historical files are needed for the model-consistent baseline.
        period = "historical" if "historical" in stem else scenario
        if period not in {"historical", *SCENARIOS}:
            continue
        key = (model, period)
        if key in found:
            raise ValueError(
                "Ambiguous CMIP6 discovery for "
                f"model={model}, period={period}: {found[key]} and {path}"
            )
        found[key] = path

    return found


def select_station_columns(
    df: pd.DataFrame,
    station_ids: Sequence[str],
) -> pd.DataFrame:
    mapping = {normalize_station_id(c): c for c in df.columns}
    requested = [normalize_station_id(s) for s in station_ids]
    missing = sorted(set(requested) - set(mapping))
    if missing:
        raise ValueError(f"Required station columns are missing: {missing}")
    cols = [mapping[s] for s in requested]
    out = df.loc[:, cols].copy()
    out.columns = [normalize_station_id(c) for c in out.columns]
    return out


# ---------------------------------------------------------------------
# Future change
# ---------------------------------------------------------------------

def climatological_index_mean(
    index_df: pd.DataFrame,
    start_year: int,
    end_year: int,
) -> pd.DataFrame:
    """
    Return station x index mean for a year interval.
    """
    if index_df.empty:
        return pd.DataFrame()

    tmp = index_df.reset_index()
    tmp = tmp[
        (tmp["Year"] >= start_year)
        & (tmp["Year"] <= end_year)
    ]

    if tmp.empty:
        return pd.DataFrame()

    return tmp.groupby("Station")[INDICES].mean()


def future_change_table(
    future_index_df: pd.DataFrame,
    historical_index_df: pd.DataFrame,
    model: str,
    scenario: str,
) -> pd.DataFrame:
    fut = climatological_index_mean(
        future_index_df, FUTURE_START, FUTURE_END
    )
    base = climatological_index_mean(
        historical_index_df, BASELINE_START, BASELINE_END
    )

    stations = sorted(set(fut.index) & set(base.index))
    rows = []

    for station in stations:
        for index_name in INDICES:
            f = safe_float(fut.loc[station, index_name])
            b = safe_float(base.loc[station, index_name])

            absolute = f - b if np.isfinite(f) and np.isfinite(b) else np.nan

            # Percentage change is not used as the sole metric for R50mm.
            if np.isfinite(f) and np.isfinite(b) and b != 0:
                pct = 100.0 * absolute / b
            else:
                pct = np.nan

            rows.append(
                {
                    "Model": model,
                    "Scenario": scenario,
                    "Station": station,
                    "Index": index_name,
                    "Baseline_Period": f"{BASELINE_START}-{BASELINE_END}",
                    "Future_Period": f"{FUTURE_START}-{FUTURE_END}",
                    "Baseline_mean": b,
                    "Future_mean": f,
                    "Absolute_change": absolute,
                    "Relative_change_pct": pct,
                    "Unit": INDEX_UNITS[index_name],
                }
            )

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------
# IDW
# ---------------------------------------------------------------------

def haversine_km(
    lat1: np.ndarray,
    lon1: np.ndarray,
    lat2: float,
    lon2: float,
) -> np.ndarray:
    r = 6371.0088
    p1 = np.radians(lat1)
    p2 = math.radians(lat2)
    dlat = p2 - p1
    dlon = np.radians(lon2 - lon1)

    a = (
        np.sin(dlat / 2.0) ** 2
        + np.cos(p1) * math.cos(p2) * np.sin(dlon / 2.0) ** 2
    )
    return 2.0 * r * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def idw_grid(
    coords: pd.DataFrame,
    values: pd.Series,
    power: float = 2.0,
    nx: int = 300,
    ny: int = 300,
    padding: float = 0.03,
    grid_bounds: Optional[Tuple[float, float, float, float]] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    IDW spatial interpolation.

    This is a visualization of station-referenced change, not dynamical
    downscaling and not an independently observed gridded field.
    """
    tmp = coords.copy()
    station_col = next(
        (c for c in tmp.columns if str(c).strip().lower() in {"station", "station_id", "stationid"}),
        None,
    )
    if station_col is None:
        raise ValueError("IDW coordinates require a station identifier column.")
    if tmp[station_col].map(normalize_station_id).duplicated().any():
        raise ValueError("IDW cannot use duplicate station coordinates.")
    normalized_values = pd.Series(values.copy())
    normalized_values.index = normalized_values.index.map(normalize_station_id)
    if normalized_values.index.duplicated().any():
        raise ValueError("IDW cannot use duplicate station values.")
    tmp["_station"] = tmp[station_col].map(normalize_station_id)
    tmp["value"] = tmp["_station"].map(normalized_values)
    tmp = tmp.dropna(subset=["latitude", "longitude", "value"])

    if len(tmp) < 3:
        raise ValueError("At least 3 valid stations are required for IDW.")

    if grid_bounds is None:
        lat_min = float(tmp["latitude"].min())
        lat_max = float(tmp["latitude"].max())
        lon_min = float(tmp["longitude"].min())
        lon_max = float(tmp["longitude"].max())
    else:
        if len(grid_bounds) != 4 or not np.isfinite(grid_bounds).all():
            raise ValueError(
                "grid_bounds must be finite (lon_min, lon_max, lat_min, lat_max)."
            )
        lon_min, lon_max, lat_min, lat_max = map(float, grid_bounds)
        if lon_max <= lon_min or lat_max <= lat_min:
            raise ValueError(
                "grid_bounds must satisfy lon_max > lon_min and lat_max > lat_min."
            )

    dlat = max(lat_max - lat_min, 0.01)
    dlon = max(lon_max - lon_min, 0.01)

    lat = np.linspace(
        lat_min - padding * dlat,
        lat_max + padding * dlat,
        ny,
    )
    lon = np.linspace(
        lon_min - padding * dlon,
        lon_max + padding * dlon,
        nx,
    )

    grid_lon, grid_lat = np.meshgrid(lon, lat)

    flat_lat = grid_lat.ravel()
    flat_lon = grid_lon.ravel()

    slat = tmp["latitude"].to_numpy(float)
    slon = tmp["longitude"].to_numpy(float)
    sval = tmp["value"].to_numpy(float)

    out = np.empty_like(flat_lat, dtype=float)

    for i in range(len(flat_lat)):
        d = haversine_km(slat, slon, flat_lat[i], flat_lon[i])

        if np.any(d == 0):
            out[i] = sval[np.argmin(d)]
            continue

        w = 1.0 / np.power(d, power)
        out[i] = float(np.sum(w * sval) / np.sum(w))

    return grid_lon, grid_lat, out.reshape(grid_lat.shape)


def read_boundary_parts(shapefile_path: Path) -> List[np.ndarray]:
    """Load polygon rings from a GIS boundary without reading DBF attributes."""
    source = Path(shapefile_path)
    if not source.is_file():
        raise FileNotFoundError(f"Boundary shapefile not found: {source}")
    reader = shapefile.Reader(str(source), encoding="cp874")
    parts: List[np.ndarray] = []
    selected = [sr.shape for sr in reader.iterShapeRecords()
                if str(sr.record.as_dict().get("PROV_CODE", "")).strip() == "53"
                or str(sr.record.as_dict().get("PROV_NAME", "")).strip().upper() == "UTTARADIT"]
    if not selected:
        raise ValueError("No explicitly identified Uttaradit polygon in boundary file.")
    for feature in selected:
        points = np.asarray(feature.points, dtype=float)
        starts = list(feature.parts) + [len(points)]
        for start, end in zip(starts[:-1], starts[1:]):
            ring = points[start:end, :2]
            if len(ring) >= 3 and np.isfinite(ring).all():
                parts.append(ring)
    if not parts:
        raise ValueError(f"Boundary shapefile has no valid polygon rings: {source}")
    return parts


def mask_grid_to_boundary(
    grid_lon: np.ndarray,
    grid_lat: np.ndarray,
    grid: np.ndarray,
    boundary_parts: Sequence[np.ndarray],
) -> np.ndarray:
    """Mask an IDW grid outside the union of supplied polygon rings."""
    if grid_lon.shape != grid_lat.shape or grid.shape != grid_lon.shape:
        raise ValueError("Longitude, latitude, and IDW grid shapes must match.")
    points = np.column_stack([grid_lon.ravel(), grid_lat.ravel()])
    inside = np.zeros(len(points), dtype=bool)
    for ring in boundary_parts:
        vertices = np.asarray(ring, dtype=float)
        if not np.array_equal(vertices[0], vertices[-1]):
            vertices = np.vstack([vertices, vertices[0]])
        inside ^= MplPath(vertices, closed=True).contains_points(points, radius=1e-10)
    masked = np.asarray(grid, dtype=float).copy()
    masked.ravel()[~inside] = np.nan
    return masked


def draw_boundary(ax: plt.Axes, boundary_parts: Optional[Sequence[np.ndarray]]) -> None:
    """Draw all available polygon rings as a geographic reference."""
    if not boundary_parts:
        return
    for ring in boundary_parts:
        ring = np.asarray(ring, dtype=float)
        ax.plot(ring[:, 0], ring[:, 1], color="0.20", linewidth=0.65, zorder=3)


# ---------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------

def setup_publication_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9.5,
            "axes.titlesize": 10.5,
            "axes.labelsize": 9.5,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "legend.fontsize": 8.5,
            "figure.dpi": 150,
            "savefig.dpi": 600,
            "savefig.bbox": "tight",
            "axes.unicode_minus": False,
        }
    )


_STATION_LABEL_PREFERENCES = {
    # Values are in geographic degrees.  Multiple candidates are tried in
    # order, then screened against labels already placed in the same map.
    "465002": [
        (-0.010, -0.010, "right", "top"),
        (0.014, 0.012, "left", "bottom"),
        (-0.014, 0.012, "right", "bottom"),
    ],
    "465008": [
        (0.010, 0.010, "left", "bottom"),
        (0.010, -0.014, "left", "top"),
        (-0.012, 0.010, "right", "bottom"),
    ],
    "465009": [
        (0.010, -0.009, "left", "top"),
        (-0.012, -0.009, "right", "top"),
        (0.010, 0.012, "left", "bottom"),
    ],
    "465010": [
        (0.012, -0.014, "left", "top"),
        (-0.014, -0.014, "right", "top"),
        (0.012, 0.012, "left", "bottom"),
    ],
    "465011": [
        (0.012, 0.014, "left", "bottom"),
        (-0.014, 0.014, "right", "bottom"),
        (0.012, -0.014, "left", "top"),
    ],
    "465012": [
        (-0.012, 0.014, "right", "bottom"),
        (0.012, 0.014, "left", "bottom"),
        (-0.014, -0.014, "right", "top"),
    ],
}

_GENERIC_LABEL_CANDIDATES = [
    (0.008, 0.008, "left", "bottom"),
    (-0.008, 0.008, "right", "bottom"),
    (0.008, -0.008, "left", "top"),
    (-0.008, -0.008, "right", "top"),
    (0.014, 0.0, "left", "center"),
    (-0.014, 0.0, "right", "center"),
]


def _label_bbox(x: float, y: float, text: str, ha: str, va: str, fontsize: float) -> Tuple[float, float, float, float]:
    """Approximate a label's data-coordinate bounding box for collision tests."""
    width = 0.0052 * max(len(text), 6) * (fontsize / 6.8)
    height = 0.017 * (fontsize / 6.8)
    if ha == "left":
        x0, x1 = x, x + width
    elif ha == "right":
        x0, x1 = x - width, x
    else:
        x0, x1 = x - width / 2.0, x + width / 2.0
    if va == "bottom":
        y0, y1 = y, y + height
    elif va == "top":
        y0, y1 = y - height, y
    else:
        y0, y1 = y - height / 2.0, y + height / 2.0
    return x0, y0, x1, y1


def _boxes_overlap(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> bool:
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def _annotate_stations(ax: plt.Axes, frame: pd.DataFrame, fontsize: float) -> None:
    """Place station labels with deterministic collision avoidance and halo."""
    placed: List[Tuple[float, float, float, float]] = []
    ordered = frame.sort_values(["latitude", "longitude", "Station"], ascending=[False, True, True])
    for _, row in ordered.iterrows():
        station = normalize_station_id(row["Station"])
        text = station
        candidates = _STATION_LABEL_PREFERENCES.get(station, []) + _GENERIC_LABEL_CANDIDATES
        selected = candidates[0]
        selected_box = None
        for dx, dy, ha, va in candidates:
            x = float(row["longitude"]) + dx
            y = float(row["latitude"]) + dy
            box = _label_bbox(x, y, text, ha, va, fontsize)
            if not any(_boxes_overlap(box, other) for other in placed):
                selected = (dx, dy, ha, va)
                selected_box = box
                break
        if selected_box is None:
            dx, dy, ha, va = selected
            x = float(row["longitude"]) + dx
            y = float(row["latitude"]) + dy
            selected_box = _label_bbox(x, y, text, ha, va, fontsize)
        else:
            dx, dy, ha, va = selected
            x = float(row["longitude"]) + dx
            y = float(row["latitude"]) + dy
        placed.append(selected_box)
        ax.text(
            x,
            y,
            text,
            fontsize=fontsize,
            ha=ha,
            va=va,
            zorder=6,
            path_effects=[patheffects.withStroke(linewidth=2.0, foreground="white")],
        )


def plot_observed_trend_map(
    trend_df: pd.DataFrame,
    coords: pd.DataFrame,
    index_name: str,
    out_path: Path,
    boundary_parts: Optional[Sequence[np.ndarray]] = None,
) -> None:
    sub = trend_df[trend_df["Index"] == index_name].copy()
    sub["Station"] = sub["Station"].map(normalize_station_id)
    c = coords.copy()
    station_col = next((col for col in c.columns if str(col).strip().lower() in {"station", "station_id", "stationid"}), None)
    if station_col is None:
        raise ValueError("Station coordinates require a station identifier column for plotting.")
    c["Station"] = c[station_col].map(normalize_station_id)

    m = c.merge(
        sub[
            [
                "Station",
                "Z_MMK2004",
                "p_MMK2004",
                "Trend_MMK2004",
                "Sen_slope",
            ]
        ],
        on="Station",
        how="inner",
    )

    if m.empty:
        return

    fig, ax = plt.subplots(figsize=(6.8, 5.8))
    draw_boundary(ax, boundary_parts)

    inc = m["Trend_MMK2004"].eq("Increasing")
    dec = m["Trend_MMK2004"].eq("Decreasing")
    ns = m["Trend_MMK2004"].eq("No significant trend")

    ax.scatter(
        m.loc[ns, "longitude"],
        m.loc[ns, "latitude"],
        s=45,
        marker="o",
        facecolors="white",
        edgecolors="black",
        linewidths=0.8,
        zorder=4,
        label="No significant trend",
    )
    ax.scatter(
        m.loc[inc, "longitude"],
        m.loc[inc, "latitude"],
        s=65,
        marker="^",
        facecolors="black",
        edgecolors="black",
        linewidths=0.5,
        zorder=5,
        label="Increasing",
    )
    ax.scatter(
        m.loc[dec, "longitude"],
        m.loc[dec, "latitude"],
        s=65,
        marker="v",
        facecolors="black",
        edgecolors="black",
        linewidths=0.5,
        zorder=5,
        label="Decreasing",
    )

    _annotate_stations(ax, m, fontsize=7)

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(
        f"{index_name} | Observed trend, {OBS_START}-{OBS_END}\n"
        "Yue-Wang (2004) MMK"
    )

    ax.legend(
        loc="upper left",
        bbox_to_anchor=(1.01, 1.0),
        frameon=False,
    )

    ax.grid(alpha=0.18, linewidth=0.6)
    fig.savefig(out_path)
    plt.close(fig)


def plot_future_idw_change(
    change_df: pd.DataFrame,
    coords: pd.DataFrame,
    index_name: str,
    scenario: str,
    out_path: Path,
    power: float = 2.0,
    boundary_parts: Optional[Sequence[np.ndarray]] = None,
) -> None:
    scenario_label = SCENARIOS.get(scenario, scenario)
    sub = change_df[
        (change_df["Index"] == index_name)
        & (change_df["Scenario"] == scenario_label)
    ].copy()

    if sub.empty:
        return

    # Station-wise 7-model median, then IDW.
    station_values = (
        sub.groupby("Station")["Absolute_change"]
        .median()
        .rename("value")
    )

    c = coords.copy()
    station_col = next((col for col in c.columns if str(col).strip().lower() in {"station", "station_id", "stationid"}), None)
    if station_col is None:
        raise ValueError("Station coordinates require a station identifier column for plotting.")
    c["Station"] = c[station_col].map(normalize_station_id)
    station_values.index = station_values.index.map(normalize_station_id)

    merged = c.merge(
        station_values.reset_index(),
        on="Station",
        how="inner",
    )

    if len(merged) < 3:
        return

    grid_bounds = None
    if boundary_parts:
        boundary_vertices = np.vstack([np.asarray(ring, dtype=float) for ring in boundary_parts])
        grid_bounds = (
            float(boundary_vertices[:, 0].min()),
            float(boundary_vertices[:, 0].max()),
            float(boundary_vertices[:, 1].min()),
            float(boundary_vertices[:, 1].max()),
        )

    glon, glat, grid = idw_grid(
        merged[["Station", "latitude", "longitude"]],
        merged.set_index("Station")["value"],
        power=power,
        grid_bounds=grid_bounds,
    )
    if boundary_parts:
        grid = mask_grid_to_boundary(glon, glat, grid, boundary_parts)

    vmax = np.nanmax(np.abs(grid))
    if not np.isfinite(vmax) or vmax == 0:
        vmax = 1.0

    norm = TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax)

    fig, ax = plt.subplots(figsize=(7.0, 5.8))
    draw_boundary(ax, boundary_parts)
    im = ax.pcolormesh(
        glon,
        glat,
        grid,
        shading="auto",
        cmap="RdBu_r",
        norm=norm,
    )

    ax.scatter(
        merged["longitude"],
        merged["latitude"],
        s=30,
        facecolors="white",
        edgecolors="black",
        linewidths=0.7,
        zorder=5,
    )

    _annotate_stations(ax, merged, fontsize=6.8)

    cb = fig.colorbar(im, ax=ax, pad=0.02, shrink=0.88)
    cb.set_label(f"Absolute change ({INDEX_UNITS[index_name]})")

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(
        f"{index_name} | {SCENARIOS.get(scenario, scenario)}\n"
        f"2021-2050 minus {BASELINE_START}-{BASELINE_END} | "
        "7-model median + IDW"
    )
    ax.grid(alpha=0.15, linewidth=0.5)

    fig.savefig(out_path)
    plt.close(fig)


def plot_heatmap(
    trend_df: pd.DataFrame,
    period_label: str,
    out_path: Path,
    scenario: Optional[str] = None,
) -> None:
    sub = trend_df.copy()

    if scenario is not None:
        sub = sub[sub["Scenario"] == scenario]

    if sub.empty:
        return

    # For future model results, summarize by station using the median
    # Sen slope and majority direction across models.
    grouped = []
    for (station, index_name), g in sub.groupby(
        ["Station", "Index"]
    ):
        slopes = pd.to_numeric(g["Sen_slope"], errors="coerce")
        mmk_p = pd.to_numeric(g["p_MMK2004"], errors="coerce")
        mmk_z = pd.to_numeric(g["Z_MMK2004"], errors="coerce")

        med_slope = float(slopes.median())

        # Significance is represented by the direction of the median
        # model Z only for visualization; detailed model results remain
        # in the Excel/CSV outputs.
        med_z = float(mmk_z.median())

        if med_z > 0:
            val = 1
        elif med_z < 0:
            val = -1
        else:
            val = 0

        grouped.append(
            {
                "Station": station,
                "Index": index_name,
                "direction": val,
                "slope": med_slope,
            }
        )

    gdf = pd.DataFrame(grouped)
    pivot = gdf.pivot(
        index="Station",
        columns="Index",
        values="direction",
    )

    pivot = pivot.reindex(
        columns=[x for x in INDICES if x in pivot.columns]
    )

    fig, ax = plt.subplots(
        figsize=(11.0, max(5.0, 0.38 * len(pivot) + 2.5))
    )

    im = ax.imshow(
        pivot.to_numpy(dtype=float),
        aspect="auto",
        cmap="RdBu_r",
        vmin=-1,
        vmax=1,
    )

    ax.set_xticks(np.arange(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, rotation=45, ha="right")
    ax.set_yticks(np.arange(len(pivot.index)))
    ax.set_yticklabels(pivot.index)

    ax.set_xlabel("Extreme precipitation index")
    ax.set_ylabel("Station")
    ax.set_title(
        f"Trend-direction summary | {period_label}"
        + (
            f" | {SCENARIOS.get(scenario, scenario)}"
            if scenario
            else ""
        )
    )

    cbar = fig.colorbar(im, ax=ax, ticks=[-1, 0, 1], pad=0.02)
    cbar.ax.set_yticklabels(
        ["Decrease", "No trend / mixed", "Increase"]
    )

    fig.savefig(out_path)
    plt.close(fig)


# ---------------------------------------------------------------------
# Excel export
# ---------------------------------------------------------------------

def write_excel(
    path: Path,
    observed_trend: pd.DataFrame,
    future_trend: pd.DataFrame,
    change_df: pd.DataFrame,
    observed_indices: pd.DataFrame,
    future_indices: pd.DataFrame,
    coords: pd.DataFrame,
    qc_observed: pd.DataFrame,
    qc_models: pd.DataFrame,
    summary: pd.DataFrame,
) -> None:
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        observed_trend.to_excel(
            writer, sheet_name="Observed_Trend", index=False
        )
        future_trend.to_excel(
            writer, sheet_name="Future_Trend", index=False
        )
        change_df.to_excel(
            writer, sheet_name="Future_Change", index=False
        )
        observed_indices.to_excel(
            writer, sheet_name="Observed_Indices"
        )
        future_indices.to_excel(
            writer, sheet_name="Future_Indices"
        )
        coords.to_excel(
            writer, sheet_name="Stations", index=False
        )
        qc_observed.to_excel(
            writer, sheet_name="QC_Observed", index=False
        )
        qc_models.to_excel(
            writer, sheet_name="QC_Models", index=False
        )
        summary.to_excel(
            writer, sheet_name="Summary", index=False
        )

    # Basic publication-oriented formatting.
    from openpyxl import load_workbook
    from openpyxl.styles import Font, Alignment
    from openpyxl.utils import get_column_letter

    wb = load_workbook(path)

    for ws in wb.worksheets:
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions

        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(
                horizontal="center",
                vertical="center",
                wrap_text=True,
            )

        for col in range(1, ws.max_column + 1):
            letter = get_column_letter(col)
            max_len = 0
            for row in ws.iter_rows(
                min_col=col,
                max_col=col,
                values_only=True,
            ):
                val = row[0]
                max_len = max(max_len, len(str(val)) if val is not None else 0)
            ws.column_dimensions[letter].width = min(max(max_len + 2, 10), 28)

    wb.save(path)


# ---------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------

def build_summary(
    observed_trend: pd.DataFrame,
    future_trend: pd.DataFrame,
    change_df: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    def summarize(
        df: pd.DataFrame,
        period: str,
        group_cols: Sequence[str],
    ) -> None:
        if df.empty:
            return

        for keys, g in df.groupby(list(group_cols)):
            if not isinstance(keys, tuple):
                keys = (keys,)

            sig = pd.to_numeric(g["p_MMK2004"], errors="coerce") < ALPHA
            z = pd.to_numeric(g["Z_MMK2004"], errors="coerce")

            inc = int((sig & (z > 0)).sum())
            dec = int((sig & (z < 0)).sum())
            ns = int((~sig).sum())

            row = {
                "Period": period,
                "Index": g["Index"].iloc[0],
                "Increasing_MMK": inc,
                "Decreasing_MMK": dec,
                "No_significant_trend_MMK": ns,
                "Median_Sen_slope": float(
                    pd.to_numeric(g["Sen_slope"], errors="coerce").median()
                ),
            }

            for col, value in zip(group_cols, keys):
                row[col] = value

            rows.append(row)

    summarize(
        observed_trend,
        "1981-2014",
        ["Index"],
    )
    summarize(
        future_trend,
        "2021-2050",
        ["Model", "Scenario", "Index"],
    )

    if not change_df.empty:
        for (scenario, index_name), g in change_df.groupby(
            ["Scenario", "Index"]
        ):
            vals = pd.to_numeric(
                g["Absolute_change"], errors="coerce"
            )
            rows.append(
                {
                    "Period": "2021-2050 change",
                    "Scenario": scenario,
                    "Index": index_name,
                    "Median_future_minus_baseline": float(vals.median()),
                    "IQR_low": float(vals.quantile(0.25)),
                    "IQR_high": float(vals.quantile(0.75)),
                }
            )

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------
# Audit outputs and validation
# ---------------------------------------------------------------------

def indices_to_long(
    index_df: pd.DataFrame,
    period: str,
    model: str,
    scenario: str,
) -> pd.DataFrame:
    """Convert annual station-index values to an explicit auditable long form."""
    if index_df.empty:
        return pd.DataFrame(
            columns=["Period", "Model", "Scenario", "Station", "Year", "Annual_status", "Index", "Value", "Unit"]
        )
    tmp = index_df.reset_index()
    status_col = "Annual_status" if "Annual_status" in tmp.columns else None
    long = tmp.melt(
        id_vars=["Station", "Year"] + ([status_col] if status_col else []),
        value_vars=INDICES,
        var_name="Index",
        value_name="Value",
    )
    if status_col is None:
        long["Annual_status"] = "OK"
    long.insert(0, "Period", period)
    long.insert(1, "Model", model)
    long.insert(2, "Scenario", scenario)
    long["Unit"] = long["Index"].map(INDEX_UNITS)
    return long.sort_values(["Model", "Scenario", "Station", "Year", "Index"]).reset_index(drop=True)


def thresholds_table(thresholds: Dict[str, Tuple[float, float]]) -> pd.DataFrame:
    rows = [
        {
            "Station": station,
            "P95_threshold_mm": p95,
            "P99_threshold_mm": p99,
            "Wet_day_definition": "RR >= 1 mm",
            "Baseline_period": f"{OBS_START}-{OBS_END}",
        }
        for station, (p95, p99) in sorted(thresholds.items())
    ]
    return pd.DataFrame(rows)


def build_cmip6_manifest(files: Dict[Tuple[str, str], Path]) -> pd.DataFrame:
    """Read every selected CMIP6 file once for auditable date/station coverage."""
    rows = []
    for (model, period), path in sorted(files.items()):
        daily = load_daily_csv(path)
        rows.append(
            {
                "Model": model,
                "Dataset_period": period,
                "Scenario": SCENARIOS.get(period, "Historical"),
                "File": str(path),
                "Start_date": daily.index.min().strftime("%Y-%m-%d"),
                "End_date": daily.index.max().strftime("%Y-%m-%d"),
                "N_records": int(len(daily)),
                "N_station_columns": int(len(daily.columns)),
                "Status": "OK",
            }
        )
    return pd.DataFrame(rows)


def validate_cmip6_manifest(files: Dict[Tuple[str, str], Path]) -> None:
    expected = {(model, period) for model in EXPECTED_MODELS for period in ("historical", *SCENARIOS)}
    actual = set(files)
    if actual != expected:
        raise ValueError(
            "CMIP6 manifest is incomplete or unexpected; "
            f"missing={sorted(expected - actual)}, unexpected={sorted(actual - expected)}"
        )


def model_agreement_summary(future_trend: pd.DataFrame) -> pd.DataFrame:
    """Describe, but never infer a formal ensemble p-value from, model results."""
    rows = []
    if future_trend.empty:
        return pd.DataFrame()
    for (scenario, station, index_name), group in future_trend.groupby(["Scenario", "Station", "Index"]):
        p = pd.to_numeric(group["p_MMK2004"], errors="coerce")
        z = pd.to_numeric(group["Z_MMK2004"], errors="coerce")
        slope = pd.to_numeric(group["Sen_slope"], errors="coerce")
        sig_inc = int(((p < ALPHA) & (z > 0)).sum())
        sig_dec = int(((p < ALPHA) & (z < 0)).sum())
        nonsig = int((p.notna() & ~(p < ALPHA)).sum())
        direction = np.select([slope > 0, slope < 0], ["increasing", "decreasing"], default="zero_or_missing")
        sig_direction = np.select(
            [(p < ALPHA) & (z > 0), (p < ALPHA) & (z < 0)],
            ["significant_increasing", "significant_decreasing"],
            default="not_significant_or_missing",
        )
        n_models = int(group["Model"].nunique())
        sign_agreement = 100.0 * max(pd.Series(direction).value_counts().max(), 0) / max(n_models, 1)
        sig_agreement = 100.0 * max(pd.Series(sig_direction).value_counts().max(), 0) / max(n_models, 1)
        rows.append(
            {
                "Scenario": scenario,
                "Station": station,
                "Index": index_name,
                "n_models_available": n_models,
                "n_sig_increasing": sig_inc,
                "n_sig_decreasing": sig_dec,
                "n_non_sig": nonsig,
                "median_sen_slope": float(slope.median()),
                "median_Z": float(z.median()),
                "median_p_descriptive_only": float(p.median()),
                "sign_agreement_pct": sign_agreement,
                "sig_agreement_pct": sig_agreement,
            }
        )
    return pd.DataFrame(rows).sort_values(["Scenario", "Station", "Index"]).reset_index(drop=True)


def validate_result_tables(
    observed_trend: pd.DataFrame,
    future_trend: pd.DataFrame,
    change_df: pd.DataFrame,
    station_ids: Sequence[str],
) -> None:
    """Fail closed for duplicate keys, invalid probabilities, or missing combinations."""
    expected_observed = len(station_ids) * len(INDICES)
    expected_future = len(station_ids) * len(INDICES) * len(EXPECTED_MODELS) * len(SCENARIOS)
    if len(observed_trend) != expected_observed:
        raise ValueError(f"Observed trend row count {len(observed_trend)} != {expected_observed}.")
    if len(future_trend) != expected_future:
        raise ValueError(f"Future trend row count {len(future_trend)} != {expected_future}.")
    if len(change_df) != expected_future:
        raise ValueError(f"Future change row count {len(change_df)} != {expected_future}.")

    keys = {
        "observed trend": (observed_trend, ["Station", "Index"]),
        "future trend": (future_trend, ["Model", "Scenario", "Station", "Index"]),
        "future change": (change_df, ["Model", "Scenario", "Station", "Index"]),
    }
    for name, (frame, columns) in keys.items():
        if frame.duplicated(columns).any():
            raise ValueError(f"Duplicate {name} keys: {columns}")

    for name, frame in (("observed", observed_trend), ("future", future_trend)):
        for column in ("p_MK", "p_MMK2004"):
            p = pd.to_numeric(frame[column], errors="coerce")
            if ((p.dropna() < 0) | (p.dropna() > 1)).any():
                raise ValueError(f"{name} output has p-values outside [0, 1] in {column}.")
        finite_ci = frame[["Sen_slope", "Sen_CI95_low", "Sen_CI95_high"]].apply(pd.to_numeric, errors="coerce").dropna()
        if not finite_ci.empty and ((finite_ci["Sen_CI95_low"] > finite_ci["Sen_slope"]) | (finite_ci["Sen_slope"] > finite_ci["Sen_CI95_high"])).any():
            raise ValueError(f"{name} output has an invalid Sen confidence interval.")
        numeric = frame.select_dtypes(include=[np.number]).to_numpy(dtype=float)
        if np.isinf(numeric).any():
            raise ValueError(f"{name} output contains infinity.")


def write_excel_v2(
    path: Path,
    metadata: Dict[str, object],
    coords: pd.DataFrame,
    thresholds: pd.DataFrame,
    observed_indices: pd.DataFrame,
    observed_trend: pd.DataFrame,
    future_indices: pd.DataFrame,
    future_trend: pd.DataFrame,
    change_df: pd.DataFrame,
    agreement: pd.DataFrame,
    qc_observed: pd.DataFrame,
    qc_models: pd.DataFrame,
    manifest: pd.DataFrame,
) -> None:
    sheets = {
        "Metadata": pd.DataFrame({"Field": list(metadata), "Value": [json.dumps(v) if isinstance(v, (dict, list)) else v for v in metadata.values()]}),
        "Station Coordinates": coords,
        "Station Thresholds": thresholds,
        "Observed Indices": observed_indices,
        "Observed Trend": observed_trend,
        "Future Indices": future_indices,
        "Future Trend": future_trend,
        "Future Change": change_df,
        "Model Summary": agreement,
        "QC Observed": qc_observed,
        "QC Models": qc_models,
        "File Manifest": manifest,
    }
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name[:31], index=False)

    from openpyxl import load_workbook
    from openpyxl.styles import Alignment, Font
    from openpyxl.utils import get_column_letter

    book = load_workbook(path)
    for worksheet in book.worksheets:
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions
        for cell in worksheet[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        for col in range(1, worksheet.max_column + 1):
            letter = get_column_letter(col)
            width = max((len(str(cell.value)) if cell.value is not None else 0 for cell in worksheet[get_column_letter(col)]), default=10)
            worksheet.column_dimensions[letter].width = min(max(width + 2, 10), 32)
    book.save(path)


def build_metadata(input_root: Path, output_root: Path) -> Dict[str, object]:
    import matplotlib as mpl
    import openpyxl
    import scipy

    return {
        "script_version": VERSION,
        "execution_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "package_versions": {"numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__, "matplotlib": mpl.__version__, "openpyxl": openpyxl.__version__},
        "input_path": str(input_root),
        "output_path": str(output_root),
        "configuration": asdict(CONFIG),
        "models": EXPECTED_MODELS,
        "scenarios": SCENARIOS,
        "method": "Standard Mann-Kendall plus Yue-Wang 2004 detrended ESS MMK and Sen slope",
    }


# ---------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Uttaradit 11-index extreme precipitation trend analysis "
            "using MK + Yue-Wang (2004) MMK + Sen slope."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to extracted dataUttaradit directory or dataUttaradit.rar",
    )
    parser.add_argument(
        "--output",
        default="output_utt_trend",
        help="Output directory",
    )
    parser.add_argument(
        "--idw-power",
        type=float,
        default=2.0,
        help="IDW power parameter (default 2.0)",
    )
    parser.add_argument(
        "--no-figures",
        action="store_true",
        help="Skip figure generation",
    )
    args = parser.parse_args()

    setup_publication_style()

    input_path = Path(args.input)
    output_root = Path(args.output).resolve()
    result_dir = output_root / "results"
    fig_dir = output_root / "figures"

    result_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    log("=" * 78)
    log(f"Uttaradit Extreme Precipitation Trend Analysis v{VERSION}")
    log("Core: 11 indices | MK | Yue-Wang (2004) MMK | Sen slope")
    log("Observed: 1981-2014 | Future: 2021-2050")
    log("=" * 78)

    # -------------------------------------------------------------
    # Locate/extract archive
    # -------------------------------------------------------------
    prepared = prepare_input_root(input_path)
    data_root = locate_data_root(prepared)

    log(f"Data root: {data_root}")

    obs_path = (
        data_root
        / "Observed_Rain_daily_198101_201412_Uttaradit.csv"
    )

    coord_candidates = [
        data_root / "station_coordinates.xlsx",
        data_root / "gis" / "station_coordinates.xlsx",
    ]

    coord_path = next(
        (p for p in coord_candidates if p.exists()),
        None,
    )

    if coord_path is None:
        matches = list(
            data_root.rglob("station_coordinates.xlsx")
        )
        if matches:
            coord_path = matches[0]

    if coord_path is None:
        raise FileNotFoundError(
            "station_coordinates.xlsx not found."
        )

    # -------------------------------------------------------------
    # Observed data
    # -------------------------------------------------------------
    log("\n[1/8] Loading observed rainfall ...")
    obs_raw = load_daily_csv(obs_path)
    obs_raw = select_station_columns(
        obs_raw,
        [
            normalize_station_id(c)
            for c in obs_raw.columns
        ],
    )

    obs, qc_obs = qc_daily(
        obs_raw,
        expected_start=f"{OBS_START}-01-01",
        expected_end=f"{OBS_END}-12-31",
    )

    coords = read_coordinates(coord_path)

    observed_station_ids = {
        normalize_station_id(c) for c in obs.columns
    }
    coord_station_ids = set(coords["station"])

    station_ids = sorted(
        observed_station_ids & coord_station_ids
    )

    if len(station_ids) == 0:
        raise RuntimeError(
            "No common stations between observed rainfall and coordinates."
        )

    # Restrict observed to coordinate-supported stations.
    obs = select_station_columns(obs, station_ids)
    coords = coords[
        coords["station"].isin(station_ids)
    ].copy()

    log(f"Observed stations used: {len(station_ids)}")
    log(f"Stations: {', '.join(station_ids)}")

    # -------------------------------------------------------------
    # Observed ETCCDI-based indices
    # -------------------------------------------------------------
    log("\n[2/8] Computing the 11 observed extreme indices ...")
    thresholds = station_thresholds_from_observed(obs)

    obs_indices = annual_extreme_indices(
        obs,
        thresholds,
    )

    observed_trend = analyze_index_dataframe(
        obs_indices,
        period_label="1981-2014",
        model="Observed",
        scenario="Historical",
    )

    observed_trend.to_csv(
        result_dir / "observed_trend_1981_2014.csv",
        index=False,
    )
    obs_indices.to_csv(
        result_dir / "observed_indices_1981_2014.csv"
    )
    qc_obs.to_csv(
        result_dir / "qc_observed.csv",
        index=False,
    )

    log(
        f"Observed trend rows: {len(observed_trend)} "
        f"(expected up to {len(station_ids) * len(INDICES)})"
    )

    # -------------------------------------------------------------
    # Discover CMIP6 supplied bias-corrected files
    # -------------------------------------------------------------
    log("\n[3/8] Discovering supplied bias-corrected CMIP6 files ...")
    bc_files = discover_bc_model_files(data_root)

    for key, path in sorted(bc_files.items()):
        log(f"  {key}: {path.name}")

    models_found = sorted(
        {
            model
            for model, period in bc_files
            if period in {"historical", "ssp245", "ssp585"}
        }
    )

    log(
        f"Models discovered: {len(models_found)} -> "
        f"{', '.join(models_found)}"
    )

    # -------------------------------------------------------------
    # Future model calculations
    # -------------------------------------------------------------
    future_trend_parts = []
    change_parts = []
    qc_model_parts = []
    future_index_parts = []

    log("\n[4/8] Computing model historical baselines and future indices ...")

    model_hist_indices: Dict[str, pd.DataFrame] = {}
    model_future_indices: Dict[Tuple[str, str], pd.DataFrame] = {}

    for model in models_found:
        hist_path = bc_files.get((model, "historical"))

        if hist_path is None:
            log(f"  [SKIP] {model}: no historical BC file")
            continue

        log(f"  Historical BC: {model}")
        hist_raw = load_daily_csv(hist_path)
        hist = select_station_columns(hist_raw, station_ids)
        hist, qc_hist = qc_daily(
            hist,
            expected_start=f"{OBS_START}-01-01",
            expected_end=f"{OBS_END}-12-31",
        )
        qc_hist["Model"] = model
        qc_hist["Series"] = "Historical_BC"
        qc_model_parts.append(qc_hist)

        hist_indices = annual_extreme_indices(
            hist,
            thresholds,
        )
        model_hist_indices[model] = hist_indices

        for scenario in SCENARIOS:
            future_path = bc_files.get((model, scenario))
            if future_path is None:
                log(
                    f"  [SKIP] {model} {SCENARIOS[scenario]}: "
                    "future BC file not found"
                )
                continue

            log(f"  Future BC: {model} {SCENARIOS[scenario]}")

            fut_raw = load_daily_csv(future_path)
            fut = select_station_columns(fut_raw, station_ids)
            fut, qc_fut = qc_daily(
                fut,
                expected_start=f"{FUTURE_START}-01-01",
                expected_end=f"{FUTURE_END}-12-31",
            )
            qc_fut["Model"] = model
            qc_fut["Series"] = scenario
            qc_model_parts.append(qc_fut)

            fut_indices = annual_extreme_indices(
                fut,
                thresholds,
            )
            model_future_indices[(model, scenario)] = fut_indices

            # Future trend: 2021-2050 only.
            fut_trend = analyze_index_dataframe(
                fut_indices,
                period_label="2021-2050",
                model=model,
                scenario=SCENARIOS[scenario],
            )
            future_trend_parts.append(fut_trend)

            # Future minus model-consistent 1995-2014 baseline.
            change = future_change_table(
                fut_indices,
                hist_indices,
                model=model,
                scenario=SCENARIOS[scenario],
            )
            change_parts.append(change)

            # Long-format future indices for audit.
            if not fut_indices.empty:
                tmp = fut_indices.reset_index()
                tmp["Model"] = model
                tmp["Scenario"] = SCENARIOS[scenario]
                future_index_parts.append(tmp)

    future_trend = (
        pd.concat(future_trend_parts, ignore_index=True)
        if future_trend_parts
        else pd.DataFrame()
    )

    change_df = (
        pd.concat(change_parts, ignore_index=True)
        if change_parts
        else pd.DataFrame()
    )

    future_indices_long = (
        pd.concat(future_index_parts, ignore_index=True)
        if future_index_parts
        else pd.DataFrame()
    )

    qc_models = (
        pd.concat(qc_model_parts, ignore_index=True)
        if qc_model_parts
        else pd.DataFrame()
    )

    # -------------------------------------------------------------
    # Save numerical outputs
    # -------------------------------------------------------------
    log("\n[5/8] Writing numerical results ...")

    future_trend.to_csv(
        result_dir / "future_trend_2021_2050.csv",
        index=False,
    )
    change_df.to_csv(
        result_dir / "future_change_2021_2050.csv",
        index=False,
    )
    future_indices_long.to_csv(
        result_dir / "future_indices_2021_2050.csv",
        index=False,
    )
    qc_models.to_csv(
        result_dir / "qc_models.csv",
        index=False,
    )
    coords.to_csv(
        result_dir / "station_coordinates_used.csv",
        index=False,
    )

    # -------------------------------------------------------------
    # Summaries
    # -------------------------------------------------------------
    log("\n[6/8] Building summary tables ...")
    summary = build_summary(
        observed_trend,
        future_trend,
        change_df,
    )
    summary.to_csv(
        result_dir / "summary_by_index.csv",
        index=False,
    )

    if not future_trend.empty:
        future_model_summary = (
            future_trend.groupby(
                ["Model", "Scenario", "Index"],
                dropna=False,
            )
            .agg(
                Median_Sen_slope=("Sen_slope", "median"),
                Median_MMK_Z=("Z_MMK2004", "median"),
                Median_MMK_p=("p_MMK2004", "median"),
                N_series=("Station", "count"),
            )
            .reset_index()
        )
    else:
        future_model_summary = pd.DataFrame()

    future_model_summary.to_csv(
        result_dir / "summary_by_model_scenario.csv",
        index=False,
    )

    # -------------------------------------------------------------
    # Figures
    # -------------------------------------------------------------
    if not args.no_figures:
        log("\n[7/8] Generating publication figures ...")

        for index_name in INDICES:
            plot_observed_trend_map(
                observed_trend,
                coords,
                index_name,
                fig_dir / (
                    f"observed_trends_1981_2014_{index_name}.png"
                ),
            )

        plot_heatmap(
            observed_trend,
            "1981-2014",
            fig_dir / "observed_trend_heatmap.png",
        )

        if not future_trend.empty:
            for scenario in SCENARIOS:
                s = SCENARIOS[scenario]
                for index_name in INDICES:
                    plot_future_idw_change(
                        change_df,
                        coords,
                        index_name,
                        scenario,
                        fig_dir / (
                            f"future_change_IDW_2021_2050_"
                            f"{scenario}_{index_name}.png"
                        ),
                        power=args.idw_power,
                    )

                plot_heatmap(
                    future_trend,
                    "2021-2050",
                    fig_dir / (
                        f"future_trend_heatmap_{scenario}.png"
                    ),
                    scenario=s,
                )

    else:
        log("\n[7/8] Figures skipped by --no-figures")

    # -------------------------------------------------------------
    # Excel
    # -------------------------------------------------------------
    log("\n[8/8] Writing Excel workbook ...")

    write_excel(
        result_dir / "Uttaradit_Trend_Analysis.xlsx",
        observed_trend=observed_trend,
        future_trend=future_trend,
        change_df=change_df,
        observed_indices=obs_indices,
        future_indices=future_indices_long,
        coords=coords,
        qc_observed=qc_obs,
        qc_models=qc_models,
        summary=summary,
    )

    readme = result_dir / "README_results.txt"
    readme.write_text(
        "\n".join(
            [
                f"Uttaradit Extreme Precipitation Trend Analysis v{VERSION}",
                "",
                "Title:",
                "Spatiotemporal Trends of ETCCDI-Based Extreme "
                "Precipitation Indices in Uttaradit Province, Thailand",
                "",
                "Target indices:",
                ", ".join(INDICES),
                "",
                "Observed period: 1981-2014",
                "Future period: 2021-2050",
                "Future baseline: 1995-2014, model-consistent",
                "",
                "Trend methods:",
                "1) Standard Mann-Kendall",
                "2) Yue & Wang (2004) effective-sample-size MMK",
                "3) Sen's slope + 95% CI",
                "",
                "Future spatial visualization:",
                "7-model station-wise median change followed by IDW.",
                "",
                "Excluded:",
                "Pettitt, FDR, Bonferroni, PW, TFPW, seasonal trends, "
                "monthly trends, Taylor diagrams, non-target indices.",
                "",
                "R50mm is treated as a study-specific fixed-threshold index.",
                "",
                "Important:",
                "IDW maps visualize station-referenced change and are not "
                "independent gridded observations or dynamical downscaling.",
            ]
        ),
        encoding="utf-8",
    )

    # -------------------------------------------------------------
    # Console scientific QC
    # -------------------------------------------------------------
    log("\n" + "=" * 78)
    log("ANALYSIS COMPLETE")
    log("=" * 78)
    log(f"Observed trend rows: {len(observed_trend)}")
    log(f"Future trend rows:   {len(future_trend)}")
    log(f"Future change rows:  {len(change_df)}")

    if not observed_trend.empty:
        n_obs_sig = int(
            (
                pd.to_numeric(
                    observed_trend["p_MMK2004"],
                    errors="coerce",
                )
                < ALPHA
            ).sum()
        )
        log(
            f"Observed significant MMK-2004 trends: "
            f"{n_obs_sig}/{len(observed_trend)}"
        )

    if not future_trend.empty:
        n_fut_sig = int(
            (
                pd.to_numeric(
                    future_trend["p_MMK2004"],
                    errors="coerce",
                )
                < ALPHA
            ).sum()
        )
        log(
            f"Future significant MMK-2004 trends: "
            f"{n_fut_sig}/{len(future_trend)}"
        )

    log(f"Results: {result_dir}")
    log(f"Figures: {fig_dir}")
    log("=" * 78)

    return 0


def _require_period_endpoints(
    daily: pd.DataFrame,
    start_year: int,
    end_year: int,
    label: str,
) -> None:
    start = pd.Timestamp(year=start_year, month=1, day=1)
    end = pd.Timestamp(year=end_year, month=12, day=31)
    if daily.empty or daily.index.min() > start or daily.index.max() < end:
        raise ValueError(
            f"{label}: required period {start_year}-{end_year} is not covered; "
            f"available={daily.index.min() if len(daily) else None} to "
            f"{daily.index.max() if len(daily) else None}."
        )


def _validate_thresholds(table: pd.DataFrame) -> None:
    if len(table) != len(EXPECTED_STATIONS):
        raise ValueError("Station threshold table does not contain all 13 stations.")
    if table[["P95_threshold_mm", "P99_threshold_mm"]].isna().any().any():
        raise ValueError("At least one station lacks a valid P95/P99 threshold.")
    if (table["P99_threshold_mm"] < table["P95_threshold_mm"]).any():
        raise ValueError("P99 threshold is lower than P95 threshold for at least one station.")


def _write_validation_report(
    path: Path,
    station_ids: Sequence[str],
    manifest: pd.DataFrame,
    observed_qc: pd.DataFrame,
) -> None:
    complete_obs = int((observed_qc["status"] == "OK").sum())
    path.write_text(
        "\n".join(
            [
                "# Uttaradit pipeline validation report",
                "",
                "## Result",
                "",
                "VALIDATION PASSED",
                "",
                "## Verified inputs",
                "",
                f"- Stations: {len(station_ids)} ({', '.join(station_ids)})",
                f"- Observed period: {OBS_START}-{OBS_END}",
                f"- Observed station-year QC rows with status OK: {complete_obs}/{len(observed_qc)}",
                f"- CMIP6 manifest rows: {len(manifest)} (expected 21)",
                f"- Models: {', '.join(EXPECTED_MODELS)}",
                f"- Scenarios: {', '.join(SCENARIOS.values())}",
                f"- Future trend series expected after a full run: {len(EXPECTED_STATIONS) * len(INDICES) * len(EXPECTED_MODELS) * len(SCENARIOS)}",
            ]
        ),
        encoding="utf-8",
    )


def main_v2() -> int:
    parser = argparse.ArgumentParser(
        description="Auditable Uttaradit ETCCDI trend analysis using MK, Yue-Wang 2004 MMK, and Sen slope."
    )
    parser.add_argument("--input", required=True, help="Extracted data directory or .rar archive.")
    parser.add_argument("--output", default="output_utt_trend", help="Output directory.")
    parser.add_argument("--idw-power", type=float, default=CONFIG.idw_power, help="Positive IDW power.")
    parser.add_argument("--no-figures", action="store_true", help="Skip figure generation.")
    parser.add_argument("--validate-only", action="store_true", help="Validate inputs and manifest without calculating indices.")
    args = parser.parse_args()

    if not np.isfinite(args.idw_power) or args.idw_power <= 0:
        raise ValueError("--idw-power must be finite and > 0.")

    output_root = Path(args.output).expanduser().resolve()
    result_dir = output_root / "results"
    figure_dir = output_root / "figures"
    result_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    log("=" * 78)
    log(f"Uttaradit Extreme Precipitation Trend Analysis v{VERSION}")
    log("INPUT")
    prepared = prepare_input_root(Path(args.input))
    data_root = locate_data_root(prepared)
    obs_path = data_root / "Observed_Rain_daily_198101_201412_Uttaradit.csv"
    if not obs_path.exists():
        raise FileNotFoundError(f"Observed rainfall input not found: {obs_path}")
    coordinate_paths = [data_root / "station_coordinates.xlsx", data_root / "gis" / "station_coordinates.xlsx"]
    coord_path = next((path for path in coordinate_paths if path.exists()), None)
    if coord_path is None:
        matches = sorted(data_root.rglob("station_coordinates.xlsx"))
        if not matches:
            raise FileNotFoundError("station_coordinates.xlsx not found.")
        coord_path = matches[0]

    log("QC")
    observed_raw = load_daily_csv(obs_path)
    _require_period_endpoints(observed_raw, OBS_START, OBS_END, "Observed rainfall")
    coords = read_coordinates(coord_path)
    station_ids = validate_station_network(observed_raw, coords)
    observed_raw = select_station_columns(observed_raw, station_ids)
    observed, observed_profile = qc_daily(
        observed_raw, f"{OBS_START}-01-01", f"{OBS_END}-12-31"
    )
    _require_period_endpoints(observed, OBS_START, OBS_END, "Observed rainfall")

    log("STATIONS")
    log(f"Validated Uttaradit stations: {len(station_ids)}")
    thresholds = station_thresholds_from_observed(observed)
    threshold_df = thresholds_table(thresholds)
    _validate_thresholds(threshold_df)

    log("CMIP6 MANIFEST")
    cmip6_files = discover_bc_model_files(data_root)
    validate_cmip6_manifest(cmip6_files)
    manifest = build_cmip6_manifest(cmip6_files)
    manifest.to_csv(result_dir / "cmip6_file_manifest.csv", index=False)
    coords.to_csv(result_dir / "station_coordinates_used.csv", index=False)
    threshold_df.to_csv(result_dir / "station_thresholds.csv", index=False)

    observed_indices, observed_annual_qc = annual_extreme_indices(
        observed, thresholds, return_qc=True
    )
    observed_annual_qc.insert(0, "Dataset", "Observed")
    observed_qc = pd.concat(
        [
            observed_annual_qc,
            observed_profile.assign(Dataset="Observed_profile"),
        ],
        ignore_index=True,
        sort=False,
    )
    observed_qc.to_csv(result_dir / "qc_observed.csv", index=False)

    metadata = build_metadata(data_root, output_root)
    metadata["idw_power"] = args.idw_power
    metadata["coordinate_file"] = str(coord_path)
    metadata["observed_file"] = str(obs_path)
    boundary_candidates = sorted(data_root.rglob("*pbound.shp")) or sorted(data_root.rglob("*.shp"))
    boundary_path = boundary_candidates[0] if boundary_candidates else None
    metadata["boundary_file_for_maps"] = str(boundary_path) if boundary_path else None

    if args.validate_only:
        _write_validation_report(
            result_dir / "VALIDATION_REPORT.md", station_ids, manifest, observed_annual_qc
        )
        metadata["run_mode"] = "validate_only"
        (result_dir / "analysis_metadata.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        log("OUTPUT VALIDATION")
        log("VALIDATION PASSED")
        (result_dir / "execution_log.txt").write_text("\n".join(EXECUTION_LOG), encoding="utf-8")
        return 0

    log("OBSERVED INDICES")
    observed_trend = analyze_index_dataframe(
        observed_indices, "1981-2014", model="Observed", scenario="Historical"
    )
    observed_indices_long = indices_to_long(
        observed_indices, "1981-2014", "Observed", "Historical"
    )

    log("OBSERVED TREND")
    future_trend_parts: List[pd.DataFrame] = []
    future_change_parts: List[pd.DataFrame] = []
    future_index_parts: List[pd.DataFrame] = []
    model_qc_parts: List[pd.DataFrame] = []

    for model in EXPECTED_MODELS:
        log(f"FUTURE INDICES {model}")
        historical_raw = select_station_columns(load_daily_csv(cmip6_files[(model, "historical")]), station_ids)
        _require_period_endpoints(historical_raw, OBS_START, OBS_END, f"{model} historical")
        historical, historical_profile = qc_daily(
            historical_raw, f"{OBS_START}-01-01", f"{OBS_END}-12-31"
        )
        historical_indices, historical_qc = annual_extreme_indices(
            historical, thresholds, return_qc=True
        )
        historical_qc.insert(0, "Dataset", "Historical")
        historical_qc.insert(1, "Model", model)
        historical_qc.insert(2, "Scenario", "Historical")
        model_qc_parts.append(historical_qc)

        for scenario_key, scenario_label in SCENARIOS.items():
            future_raw = select_station_columns(load_daily_csv(cmip6_files[(model, scenario_key)]), station_ids)
            _require_period_endpoints(future_raw, FUTURE_START, FUTURE_END, f"{model} {scenario_label}")
            future, _ = qc_daily(
                future_raw, f"{FUTURE_START}-01-01", f"{FUTURE_END}-12-31"
            )
            future_indices, future_qc = annual_extreme_indices(
                future, thresholds, return_qc=True
            )
            future_qc.insert(0, "Dataset", "Future")
            future_qc.insert(1, "Model", model)
            future_qc.insert(2, "Scenario", scenario_label)
            model_qc_parts.append(future_qc)

            future_trend_parts.append(
                analyze_index_dataframe(
                    future_indices, "2021-2050", model=model, scenario=scenario_label
                )
            )
            future_change_parts.append(
                future_change_table(future_indices, historical_indices, model, scenario_label)
            )
            future_index_parts.append(
                indices_to_long(future_indices, "2021-2050", model, scenario_label)
            )

    future_trend = pd.concat(future_trend_parts, ignore_index=True)
    change_df = pd.concat(future_change_parts, ignore_index=True)
    future_indices_long = pd.concat(future_index_parts, ignore_index=True)
    qc_models = pd.concat(model_qc_parts, ignore_index=True)

    log("FUTURE TREND")
    agreement = model_agreement_summary(future_trend)
    summary_by_index = build_summary(observed_trend, future_trend, change_df)
    summary_by_model_scenario = (
        future_trend.groupby(["Model", "Scenario", "Index"], as_index=False)
        .agg(
            n_stations=("Station", "nunique"),
            median_sen_slope=("Sen_slope", "median"),
            median_mmk_z=("Z_MMK2004", "median"),
            median_mmk_p_descriptive_only=("p_MMK2004", "median"),
        )
    )

    log("FUTURE CHANGE")
    validate_result_tables(observed_trend, future_trend, change_df, station_ids)

    outputs = {
        "observed_indices_1981_2014.csv": observed_indices_long,
        "observed_trend_1981_2014.csv": observed_trend,
        "future_indices_2021_2050.csv": future_indices_long,
        "future_trend_2021_2050.csv": future_trend,
        "future_change_2021_2050.csv": change_df,
        "qc_models.csv": qc_models,
        "summary_by_index.csv": summary_by_index,
        "summary_by_model_scenario.csv": summary_by_model_scenario,
        "future_model_agreement.csv": agreement,
    }
    log("ENSEMBLE SUMMARY")
    for filename, frame in outputs.items():
        frame.to_csv(result_dir / filename, index=False)

    metadata["run_mode"] = "full_analysis"
    metadata["observed_trend_rows"] = int(len(observed_trend))
    metadata["future_trend_rows"] = int(len(future_trend))
    metadata["future_change_rows"] = int(len(change_df))
    (result_dir / "analysis_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    write_excel_v2(
        result_dir / "Uttaradit_Trend_Analysis.xlsx",
        metadata,
        coords,
        threshold_df,
        observed_indices_long,
        observed_trend,
        future_indices_long,
        future_trend,
        change_df,
        agreement,
        observed_qc,
        qc_models,
        manifest,
    )

    (result_dir / "README_results.txt").write_text(
        "\n".join(
            [
                f"Uttaradit Extreme Precipitation Trend Analysis v{VERSION}",
                "Observed period: 1981-2014.",
                "Future trend period: 2021-2050.",
                "Future-change baseline: model-consistent 1995-2014.",
                "Methods: standard MK, Yue-Wang 2004 detrended effective-sample-size MMK, and Sen slope with 95% CI.",
                "R50mm is a study-specific threshold index.",
                "R95p/R99p use observed station-specific fixed wet-day thresholds.",
                "Model-agreement fields are descriptive and are not formal ensemble significance tests.",
                "IDW, when figures are enabled, visualizes station-referenced change and is not downscaling.",
            ]
        ),
        encoding="utf-8",
    )

    if not args.no_figures:
        log("IDW")
        setup_publication_style()
        boundary_parts = read_boundary_parts(boundary_path) if boundary_path else None
        log(f"Boundary mask: {boundary_path if boundary_path else 'not available'}")
        for index_name in INDICES:
            plot_observed_trend_map(
                observed_trend, coords, index_name,
                figure_dir / f"observed_trends_1981_2014_{index_name}.png",
                boundary_parts=boundary_parts,
            )
        for scenario_key in SCENARIOS:
            for index_name in INDICES:
                plot_future_idw_change(
                    change_df, coords, index_name, scenario_key,
                    figure_dir / f"future_change_IDW_2021_2050_{scenario_key}_{index_name}.png",
                    power=args.idw_power,
                    boundary_parts=boundary_parts,
                )
        expected_figure_count = len(INDICES) * (1 + len(SCENARIOS))
        actual_figure_count = len(list(figure_dir.glob("*.png")))
        if actual_figure_count < expected_figure_count:
            raise RuntimeError(
                f"FAILED VALIDATION: expected {expected_figure_count} maps but found {actual_figure_count}."
            )
    else:
        log("IDW skipped by --no-figures")

    log("OUTPUT VALIDATION")
    required = [
        "observed_indices_1981_2014.csv", "observed_trend_1981_2014.csv",
        "future_indices_2021_2050.csv", "future_trend_2021_2050.csv",
        "future_change_2021_2050.csv", "station_coordinates_used.csv",
        "station_thresholds.csv", "qc_observed.csv", "qc_models.csv",
        "cmip6_file_manifest.csv", "summary_by_index.csv",
        "summary_by_model_scenario.csv", "Uttaradit_Trend_Analysis.xlsx",
        "analysis_metadata.json", "README_results.txt",
    ]
    absent = [name for name in required if not (result_dir / name).exists()]
    if absent:
        raise RuntimeError(f"FAILED VALIDATION: required outputs absent: {absent}")
    log("SUCCESS")
    (result_dir / "execution_log.txt").write_text("\n".join(EXECUTION_LOG), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_v2())
