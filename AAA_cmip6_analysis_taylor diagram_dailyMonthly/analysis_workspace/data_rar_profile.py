from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent / "data_rar" / "Data_Uttaradit"
MODELS = [
    "ACCESS-ESM1-5",
    "CanESM5",
    "CESM2",
    "EC-Earth3",
    "FGOALS-g3",
    "MIROC6",
    "MRI-ESM2-0",
]
OVERLAP_STATIONS = [
    "351001",
    "351002",
    "351003",
    "351004",
    "351005",
    "351006",
    "351007",
    "351008",
    "351009",
    "351010",
    "351011",
    "351012",
    "351201",
]
PERIODS = {
    "near": (2021, 2040),
    "mid": (2041, 2060),
    "late": (2081, 2100),
}


def model_file(model: str, corrected: bool, experiment: str) -> Path:
    prefix = "bc_pr_day" if corrected else "pr_day"
    matches = sorted((ROOT / model).glob(f"{prefix}_{model}_{experiment}_*.csv"))
    if len(matches) != 1:
        raise RuntimeError((model, corrected, experiment, matches))
    return matches[0]


def date_index(df: pd.DataFrame) -> pd.DatetimeIndex:
    dates = pd.to_datetime(
        {"year": df["YEAR"], "month": df["MONTH"], "day": df["DAY"]},
        errors="coerce",
    )
    return pd.DatetimeIndex(dates)


def meaningful_station_columns(df: pd.DataFrame) -> list[str]:
    return [
        str(c)
        for c in df.columns
        if str(c) not in {"YEAR", "MONTH", "DAY"}
        and not str(c).startswith("Unnamed:")
    ]


def load_rain(path: Path, station_subset: list[str] | None = None) -> tuple[pd.DatetimeIndex, pd.DataFrame]:
    df = pd.read_csv(path, low_memory=False)
    stations = meaningful_station_columns(df)
    if station_subset is not None:
        stations = [c for c in station_subset if c in stations]
    dates = date_index(df)
    values = df.loc[:, stations].apply(pd.to_numeric, errors="coerce")
    values.index = dates
    return dates, values


def series_digest(values: np.ndarray) -> str:
    arr = np.ascontiguousarray(values, dtype=np.float64)
    return hashlib.sha256(arr.view(np.uint8)).hexdigest()


def describe_file(path: Path) -> dict:
    df = pd.read_csv(path, low_memory=False)
    if not {"YEAR", "MONTH", "DAY"}.issubset(df.columns):
        return {
            "path": str(path),
            "bytes": path.stat().st_size,
            "rows": int(len(df)),
            "columns_total": int(len(df.columns)),
            "columns": df.columns.astype(str).tolist(),
            "null_cells": int(df.isna().sum().sum()),
            "exact_duplicate_rows": int(df.duplicated().sum()),
        }
    stations = meaningful_station_columns(df)
    dates = date_index(df)
    values = df.loc[:, stations].apply(pd.to_numeric, errors="coerce")
    expected = (
        pd.date_range(dates.min(), dates.max(), freq="D")
        if dates.notna().all() and len(dates)
        else pd.DatetimeIndex([])
    )
    flat = values.to_numpy(dtype=float, copy=False)
    finite = flat[np.isfinite(flat)]
    digests = [series_digest(values[c].to_numpy(dtype=float)) for c in stations]
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "rows": int(len(df)),
        "columns_total": int(len(df.columns)),
        "station_columns": int(len(stations)),
        "unnamed_columns": [str(c) for c in df.columns if str(c).startswith("Unnamed:")],
        "unnamed_all_null": bool(
            all(df[c].isna().all() for c in df.columns if str(c).startswith("Unnamed:"))
        ),
        "date_min": None if dates.isna().all() else str(dates.min().date()),
        "date_max": None if dates.isna().all() else str(dates.max().date()),
        "invalid_dates": int(dates.isna().sum()),
        "duplicate_dates": int(pd.Index(dates).duplicated().sum()),
        "missing_calendar_dates": int(len(expected.difference(dates))),
        "extra_or_duplicate_rows_vs_calendar": int(len(df) - len(expected)),
        "numeric_nulls": int(np.isnan(flat).sum()),
        "negative_values": int((finite < 0).sum()),
        "zero_rate": float((finite == 0).mean()) if finite.size else None,
        "min": float(finite.min()) if finite.size else None,
        "q999": float(np.quantile(finite, 0.999)) if finite.size else None,
        "max": float(finite.max()) if finite.size else None,
        "unique_station_series": int(len(set(digests))),
        "duplicate_station_series": int(len(stations) - len(set(digests))),
    }


def metric_row(model_values: pd.Series, obs_values: pd.Series) -> dict:
    aligned = pd.concat([model_values.rename("m"), obs_values.rename("o")], axis=1).dropna()
    m = aligned["m"].to_numpy(dtype=float)
    o = aligned["o"].to_numpy(dtype=float)
    corr = float(np.corrcoef(m, o)[0, 1])
    std_m = float(np.std(m, ddof=1))
    std_o = float(np.std(o, ddof=1))
    crmse = float(np.sqrt(np.mean(((m - m.mean()) - (o - o.mean())) ** 2)))
    return {
        "n": int(len(aligned)),
        "corr": corr,
        "std_ratio": std_m / std_o,
        "crmse_norm": crmse / std_o,
        "mean_obs": float(o.mean()),
        "mean_model": float(m.mean()),
        "bias": float((m - o).mean()),
        "pbias_pct": float(100 * (m.sum() - o.sum()) / o.sum()),
        "rmse": float(np.sqrt(np.mean((m - o) ** 2))),
        "mae": float(np.mean(np.abs(m - o))),
    }


def historical_metrics() -> list[dict]:
    _, obs = load_rain(ROOT / "Observed_Rain_daily_198101_201412_Uttaradit.csv")
    obs_daily = obs.mean(axis=1)
    obs_monthly = obs.resample("MS").sum(min_count=1).mean(axis=1)
    obs_cycle = obs.groupby(obs.index.month).mean().mean(axis=1)
    obs_spatial = pd.Series(obs.mean(axis=0).to_numpy(dtype=float))
    obs_month_station = pd.Series(
        obs.groupby(obs.index.month).mean().to_numpy(dtype=float).ravel()
    )
    rows = []
    for model in MODELS:
        for corrected in (False, True):
            _, values = load_rain(model_file(model, corrected, "historical"), OVERLAP_STATIONS)
            daily = values.mean(axis=1)
            monthly = values.resample("MS").sum(min_count=1).mean(axis=1)
            cycle = values.groupby(values.index.month).mean().mean(axis=1)
            spatial = pd.Series(values.mean(axis=0).to_numpy(dtype=float))
            month_station = pd.Series(
                values.groupby(values.index.month).mean().to_numpy(dtype=float).ravel()
            )
            rows.append(
                {
                    "model": model,
                    "variant": "bc" if corrected else "raw",
                    "daily": metric_row(daily, obs_daily),
                    "monthly_total": metric_row(monthly, obs_monthly),
                    "monthly_climatology_daily_mean": metric_row(cycle, obs_cycle),
                    "spatial_climatology_daily_mean": metric_row(spatial, obs_spatial),
                    "month_station_climatology_daily_mean": metric_row(
                        month_station, obs_month_station
                    ),
                }
            )
    return rows


def historical_metrics_compact() -> list[dict]:
    compact = []
    for row in historical_metrics():
        out = {"model": row["model"], "variant": row["variant"]}
        for short_name, source_name in (
            ("daily", "daily"),
            ("monthly", "monthly_total"),
            ("season12", "monthly_climatology_daily_mean"),
            ("space13", "spatial_climatology_daily_mean"),
            ("month_station156", "month_station_climatology_daily_mean"),
        ):
            metric = row[source_name]
            out[short_name] = {
                "r": metric["corr"],
                "std_ratio": metric["std_ratio"],
                "ncrmse": metric["crmse_norm"],
                "pbias_pct": metric["pbias_pct"],
            }
        compact.append(out)
    return compact


def max_consecutive_dry(values: np.ndarray, threshold: float = 1.0) -> int:
    dry = np.asarray(values < threshold, dtype=np.int8)
    if dry.size == 0:
        return 0
    padded = np.concatenate(([0], dry, [0]))
    change = np.diff(padded)
    starts = np.where(change == 1)[0]
    ends = np.where(change == -1)[0]
    return int((ends - starts).max(initial=0))


def climate_indices(values: pd.DataFrame, start_year: int, end_year: int) -> dict:
    subset = values[(values.index.year >= start_year) & (values.index.year <= end_year)]
    annual_station_totals = subset.groupby(subset.index.year).sum(min_count=1)
    annual_station_rx1 = subset.groupby(subset.index.year).max()
    annual_station_r20 = (subset >= 20.0).groupby(subset.index.year).sum()
    cdd_values = []
    for year, block in subset.groupby(subset.index.year):
        for col in block.columns:
            cdd_values.append(max_consecutive_dry(block[col].to_numpy(dtype=float)))
    return {
        "years": int(subset.index.year.nunique()),
        "annual_total_mm": float(annual_station_totals.to_numpy(dtype=float).mean()),
        "rx1day_mm": float(annual_station_rx1.to_numpy(dtype=float).mean()),
        "r20_days_per_year": float(annual_station_r20.to_numpy(dtype=float).mean()),
        "cdd_days": float(np.mean(cdd_values)),
    }


def pct_change(new: float, base: float) -> float:
    return float(100.0 * (new - base) / base)


def future_changes() -> dict:
    model_rows = []
    monthly_rows = []
    for model in MODELS:
        _, hist = load_rain(model_file(model, True, "historical"), OVERLAP_STATIONS)
        base = climate_indices(hist, 1981, 2014)
        base_month = hist.groupby(hist.index.month).mean().mean(axis=1)
        for scenario in ("ssp245", "ssp585"):
            _, future = load_rain(model_file(model, True, scenario), OVERLAP_STATIONS)
            for period_name, (start_year, end_year) in PERIODS.items():
                current = climate_indices(future, start_year, end_year)
                model_rows.append(
                    {
                        "model": model,
                        "scenario": scenario,
                        "period": period_name,
                        "start_year": start_year,
                        "end_year": end_year,
                        **current,
                        "annual_total_change_pct": pct_change(
                            current["annual_total_mm"], base["annual_total_mm"]
                        ),
                        "rx1day_change_pct": pct_change(
                            current["rx1day_mm"], base["rx1day_mm"]
                        ),
                        "r20_change_pct": pct_change(
                            current["r20_days_per_year"], base["r20_days_per_year"]
                        ),
                        "cdd_change_pct": pct_change(
                            current["cdd_days"], base["cdd_days"]
                        ),
                    }
                )
            late = future[(future.index.year >= 2081) & (future.index.year <= 2100)]
            late_month = late.groupby(late.index.month).mean().mean(axis=1)
            for month in range(1, 13):
                monthly_rows.append(
                    {
                        "model": model,
                        "scenario": scenario,
                        "month": month,
                        "change_pct": pct_change(float(late_month.loc[month]), float(base_month.loc[month])),
                    }
                )
    frame = pd.DataFrame(model_rows)
    aggregates = []
    change_cols = [
        "annual_total_change_pct",
        "rx1day_change_pct",
        "r20_change_pct",
        "cdd_change_pct",
    ]
    for (scenario, period), block in frame.groupby(["scenario", "period"], sort=False):
        row = {"scenario": scenario, "period": period, "models": int(len(block))}
        for col in change_cols:
            row[col] = {
                "median": float(block[col].median()),
                "min": float(block[col].min()),
                "max": float(block[col].max()),
                "positive_models": int((block[col] > 0).sum()),
            }
        aggregates.append(row)
    monthly = pd.DataFrame(monthly_rows)
    monthly_aggregates = []
    for (scenario, month), block in monthly.groupby(["scenario", "month"]):
        monthly_aggregates.append(
            {
                "scenario": scenario,
                "month": int(month),
                "median_change_pct": float(block["change_pct"].median()),
                "min": float(block["change_pct"].min()),
                "max": float(block["change_pct"].max()),
                "positive_models": int((block["change_pct"] > 0).sum()),
            }
        )
    return {
        "baseline_by_model": [
            {
                "model": model,
                **climate_indices(
                    load_rain(model_file(model, True, "historical"), OVERLAP_STATIONS)[1],
                    1981,
                    2014,
                ),
            }
            for model in MODELS
        ],
        "model_changes": model_rows,
        "ensemble_changes": aggregates,
        "late_century_monthly_changes": monthly_aggregates,
    }


def dataset_summary() -> dict:
    csvs = sorted(ROOT.rglob("*.csv"))
    station = pd.read_csv(ROOT / "Station_ID_Elevation_Uttaradit.csv", dtype={"Station_ID": str})
    obs = pd.read_csv(ROOT / "Observed_Rain_daily_198101_201412_Uttaradit.csv", low_memory=False)
    obs_stations = meaningful_station_columns(obs)
    model_header = pd.read_csv(model_file(MODELS[0], False, "historical"), nrows=0)
    model_stations = meaningful_station_columns(model_header)
    station_ids = station["Station_ID"].astype(str).tolist()
    return {
        "root": str(ROOT),
        "csv_count": len(csvs),
        "model_csv_count": len(csvs) - 2,
        "models": MODELS,
        "experiments": ["historical", "ssp245", "ssp585"],
        "variants": ["raw", "bc"],
        "station_metadata": {
            "rows": int(len(station)),
            "columns": station.columns.astype(str).tolist(),
            "duplicate_ids": int(station["Station_ID"].duplicated().sum()),
            "null_cells": int(station.isna().sum().sum()),
            "latitude_range": [float(station["latitude"].min()), float(station["latitude"].max())],
            "longitude_range": [float(station["longitude"].min()), float(station["longitude"].max())],
            "elevation_range": [float(station["Elevation"].min()), float(station["Elevation"].max())],
        },
        "observed_station_count": len(obs_stations),
        "observed_stations": obs_stations,
        "model_station_count": len(model_stations),
        "observed_subset_of_metadata": set(obs_stations).issubset(station_ids),
        "model_ids_match_metadata": set(model_stations) == set(station_ids),
        "observed_subset_of_model": set(obs_stations).issubset(model_stations),
        "non_uttaradit_model_station_count": len(set(model_stations) - set(obs_stations)),
        "file_sizes": {str(p.relative_to(ROOT)): p.stat().st_size for p in csvs},
        "profiles": [describe_file(p) for p in csvs],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "section",
        choices=["summary", "metrics", "metrics_compact", "future"],
        help="Compact, read-only diagnostics printed as JSON.",
    )
    args = parser.parse_args()
    if args.section == "summary":
        result = dataset_summary()
    elif args.section == "metrics":
        result = historical_metrics()
    elif args.section == "metrics_compact":
        result = historical_metrics_compact()
    else:
        result = future_changes()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
