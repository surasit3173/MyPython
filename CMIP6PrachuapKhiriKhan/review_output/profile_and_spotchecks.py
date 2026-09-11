from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(r"C:\MyPython\CMIP6PrachuapKhiriKhan")
RAW = ROOT / "Observed_Rain_daily_198101_201412_PrachuapKhiriKhan.csv"
RAW_SPACED = ROOT / "Observed_Rain_daily_198101_201412_Prachuap Khiri Khan.csv"
COORDS = ROOT / "station_coordinates_PrachuapKhiriKhan.csv"
RESULTS = ROOT / "Comparative_4MMK_PrachuapKhiriKhanV1"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def standard_mk(values) -> dict:
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    s = 0
    slopes = []
    for i in range(n - 1):
        diffs = x[i + 1 :] - x[i]
        s += int(np.sign(diffs).sum())
        slopes.extend((diffs / np.arange(1, n - i)).tolist())
    _, counts = np.unique(x, return_counts=True)
    ties = int(np.sum(counts * (counts - 1) * (2 * counts + 5)))
    var_s = (n * (n - 1) * (2 * n + 5) - ties) / 18.0
    if var_s == 0:
        z = 0.0
    elif s > 0:
        z = (s - 1) / math.sqrt(var_s)
    elif s < 0:
        z = (s + 1) / math.sqrt(var_s)
    else:
        z = 0.0
    p = math.erfc(abs(z) / math.sqrt(2.0))
    return {
        "n": n,
        "S": s,
        "Var_S": var_s,
        "Z": z,
        "p": p,
        "tau": s / (0.5 * n * (n - 1)) if n > 1 else math.nan,
        "slope_per_index": float(np.median(slopes)) if slopes else math.nan,
    }


def bh_reject(p_values, alpha=0.05):
    p = np.asarray(p_values, dtype=float)
    order = np.argsort(p)
    passed = p[order] <= alpha * np.arange(1, len(p) + 1) / len(p)
    reject = np.zeros(len(p), dtype=bool)
    if passed.any():
        k = np.flatnonzero(passed)[-1] + 1
        reject[order[:k]] = True
    return reject


raw = pd.read_csv(RAW)
dates = pd.to_datetime(raw[["YEAR", "MONTH", "DAY"]].rename(
    columns={"YEAR": "year", "MONTH": "month", "DAY": "day"}
), errors="coerce")
station_cols = [c for c in raw.columns if c not in {"YEAR", "MONTH", "DAY"}]
expected_dates = pd.date_range(dates.min(), dates.max(), freq="D")

long = raw.assign(Date=dates).melt(
    id_vars=["YEAR", "MONTH", "DAY", "Date"],
    value_vars=station_cols,
    var_name="Station",
    value_name="Rainfall_mm",
)
long["Station"] = long["Station"].astype(str)

coords = pd.read_csv(COORDS, dtype={"station": str})
coords["elevation_numeric"] = pd.to_numeric(coords["elevation (m.MSL.)"], errors="coerce")

annual = (
    long.groupby(["Station", "YEAR"], as_index=False)["Rainfall_mm"]
    .sum(min_count=1)
    .rename(columns={"YEAR": "Year", "Rainfall_mm": "Annual_mm"})
)
monthly = (
    long.groupby(["Station", "YEAR", "MONTH"], as_index=False)["Rainfall_mm"]
    .sum(min_count=1)
    .rename(columns={"YEAR": "Year", "MONTH": "Month", "Rainfall_mm": "Monthly_mm"})
)

season_long = long.copy()
season_long["Season"] = np.where(season_long["MONTH"].isin([5, 6, 7, 8, 9, 10]), "Wet", "Dry")
season_long["HydroYear"] = season_long["YEAR"] + np.where(
    season_long["MONTH"].isin([11, 12]), 1, 0
)
season_sums = (
    season_long.groupby(["Station", "HydroYear", "Season"], as_index=False)["Rainfall_mm"]
    .sum(min_count=1)
)
seasonal = (
    season_sums.pivot(index=["Station", "HydroYear"], columns="Season", values="Rainfall_mm")
    .reset_index()
    .rename(columns={"HydroYear": "Year", "Wet": "Wet_mm", "Dry": "Dry_mm"})
)


def read_result_csv(name: str) -> pd.DataFrame:
    df = pd.read_csv(RESULTS / "processed_data" / name)
    return df.loc[:, ~df.columns.str.startswith("Unnamed")]


def compare_frame(calc, saved, keys, values):
    left = calc.copy()
    right = saved.copy()
    for key in keys:
        left[key] = left[key].astype(str)
        right[key] = right[key].astype(str)
    merged = left.merge(right, on=keys, how="outer", suffixes=("_calc", "_saved"), indicator=True)
    out = {"calc_rows": len(left), "saved_rows": len(right), "merge": merged["_merge"].value_counts().to_dict()}
    for value in values:
        a = pd.to_numeric(merged[f"{value}_calc"], errors="coerce")
        b = pd.to_numeric(merged[f"{value}_saved"], errors="coerce")
        diff = (a - b).abs()
        out[f"{value}_max_abs_diff"] = None if diff.dropna().empty else float(diff.max())
        out[f"{value}_mismatch_gt_1e-9"] = int((diff > 1e-9).sum())
    return out


saved_annual = read_result_csv("annual_rainfall.csv")
saved_monthly = read_result_csv("monthly_rainfall.csv")
saved_seasonal = read_result_csv("seasonal_rainfall.csv")

annual_cmp = compare_frame(annual, saved_annual, ["Station", "Year"], ["Annual_mm"])
monthly_cmp = compare_frame(monthly, saved_monthly, ["Station", "Year", "Month"], ["Monthly_mm"])
seasonal_cmp = compare_frame(seasonal, saved_seasonal, ["Station", "Year"], ["Wet_mm", "Dry_mm"])

ann_mean = annual.groupby("Year")["Annual_mm"].mean().sort_index()
wet_mean = seasonal.groupby("Year")["Wet_mm"].mean().dropna().sort_index()
dry_mean_all = seasonal.groupby("Year")["Dry_mm"].mean().dropna().sort_index()

dry_counts = (
    season_long[season_long["Season"] == "Dry"]
    .groupby(["Station", "HydroYear"], as_index=False)
    .agg(calendar_days=("Date", "size"), available_days=("Rainfall_mm", "count"))
)
complete_hydroyears = sorted(
    dry_counts.groupby("HydroYear")["calendar_days"].min().loc[lambda s: s >= 181].index.tolist()
)
dry_mean_complete = dry_mean_all.loc[dry_mean_all.index.isin(complete_hydroyears)]

station_mk = []
for station, grp in annual.sort_values("Year").groupby("Station"):
    result = standard_mk(grp["Annual_mm"].to_numpy())
    station_mk.append({"Station": station, **result})
station_mk_df = pd.DataFrame(station_mk)
station_mk_df["BH_reject"] = bh_reject(station_mk_df["p"].to_numpy())

wet_total = float(long.loc[long["MONTH"].isin([5, 6, 7, 8, 9, 10]), "Rainfall_mm"].sum())
all_total = float(long["Rainfall_mm"].sum())

profile = {
    "files": {
        "named_csv_sha256": sha256(RAW),
        "spaced_csv_sha256": sha256(RAW_SPACED),
        "duplicate_files_identical": sha256(RAW) == sha256(RAW_SPACED),
    },
    "rainfall": {
        "wide_shape": list(raw.shape),
        "station_columns": station_cols,
        "station_count": len(station_cols),
        "station_day_rows": len(long),
        "date_min": str(dates.min().date()),
        "date_max": str(dates.max().date()),
        "expected_calendar_days": len(expected_dates),
        "observed_date_rows": len(raw),
        "invalid_dates": int(dates.isna().sum()),
        "duplicate_date_rows": int(dates.duplicated().sum()),
        "missing_calendar_dates": int(len(expected_dates.difference(pd.DatetimeIndex(dates)))),
        "station_date_duplicates": int(long.duplicated(["Station", "Date"]).sum()),
        "missing_values": int(long["Rainfall_mm"].isna().sum()),
        "negative_values": int((long["Rainfall_mm"] < 0).sum()),
        "values_gt_1000": int((long["Rainfall_mm"] > 1000).sum()),
        "zero_share": float((long["Rainfall_mm"] == 0).mean()),
        "max_mm_day": float(long["Rainfall_mm"].max()),
        "positive_quantiles_mm_day": long.loc[long["Rainfall_mm"] > 0, "Rainfall_mm"].quantile([0.5, 0.9, 0.99, 0.999]).to_dict(),
        "wet_month_fraction_of_total": wet_total / all_total,
        "provided_schema_is_wide": "Rainfall_mm" not in raw.columns,
    },
    "coordinates": {
        "rows": len(coords),
        "stations": coords["station"].tolist(),
        "duplicate_station_ids": int(coords["station"].duplicated().sum()),
        "stations_missing_coordinates": sorted(set(station_cols) - set(coords["station"])),
        "coordinate_stations_absent_from_rain": sorted(set(coords["station"]) - set(station_cols)),
        "latitude_range": [float(coords["latitude"].min()), float(coords["latitude"].max())],
        "longitude_range": [float(coords["longitude"].min()), float(coords["longitude"].max())],
        "nonnumeric_elevation_count": int(coords["elevation_numeric"].isna().sum()),
        "nonnumeric_elevation_tokens": sorted(coords.loc[coords["elevation_numeric"].isna(), "elevation (m.MSL.)"].astype(str).unique().tolist()),
        "header_detected_by_current_code": "elevation (m.MSL.)".strip().lower() in {"elev", "elevation", "alt", "altitude", "height", "ความสูง", "dem", "z"},
    },
    "reconciliation_to_archived_processed_outputs": {
        "annual": annual_cmp,
        "monthly": monthly_cmp,
        "seasonal": seasonal_cmp,
    },
    "dry_hydrological_years": {
        "all_years": dry_mean_all.index.astype(int).tolist(),
        "complete_years": complete_hydroyears,
        "endpoint_day_counts": dry_counts[dry_counts["HydroYear"].isin([1981, 2015])].drop_duplicates("HydroYear")[["HydroYear", "calendar_days", "available_days"]].to_dict("records"),
        "mk_all_including_partial_endpoints": standard_mk(dry_mean_all.to_numpy()),
        "mk_complete_only": standard_mk(dry_mean_complete.to_numpy()),
    },
    "aggregate_standard_mk_spotchecks": {
        "annual": standard_mk(ann_mean.to_numpy()),
        "wet": standard_mk(wet_mean.to_numpy()),
        "dry_all": standard_mk(dry_mean_all.to_numpy()),
    },
    "all_12_station_annual_standard_mk": station_mk_df.to_dict("records"),
    "all_12_station_bh_rejections": station_mk_df.loc[station_mk_df["BH_reject"], "Station"].tolist(),
}

print(json.dumps(profile, ensure_ascii=False, indent=2, default=str))
