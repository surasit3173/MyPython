"""Read-only preflight profile for the Paper 3 Uttaradit input archive."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd


BASE = Path(__file__).resolve().parent
DATA_ROOT = BASE / "paper3_inputs" / "data_archive" / "dataUttaradit"
FRAMEWORK_ROOT = BASE / "paper3_inputs" / "framework" / "paper1_framework"
OUT_CSV = BASE / "paper3_preflight_inventory.csv"
OUT_JSON = BASE / "paper3_preflight_summary.json"

OBS_STATIONS = [
    "351001", "351002", "351003", "351004", "351005", "351006",
    "351007", "351008", "351009", "351010", "351011", "351012",
    "351201",
]


def classify_name(path: Path) -> tuple[str, str, str]:
    name = path.name
    source_type = "observed" if name.startswith("Observed_") else (
        "legacy_bc" if name.startswith("bc_") else "raw_cmip6"
    )
    scenario_match = re.search(r"_(historical|ssp\d+)_", name)
    scenario = scenario_match.group(1) if scenario_match else "observed"
    model = "observed"
    if source_type != "observed":
        prefix = "bc_pr_day_" if source_type == "legacy_bc" else "pr_day_"
        rest = name.removeprefix(prefix)
        model = rest.split(f"_{scenario}_", 1)[0]
    return source_type, model, scenario


def profile_csv(path: Path) -> dict:
    source_type, model, scenario = classify_name(path)
    header = list(pd.read_csv(path, nrows=0).columns)
    unnamed = [str(c) for c in header if str(c).startswith("Unnamed:")]
    station_columns = [
        str(c) for c in header
        if str(c) not in {"YEAR", "MONTH", "DAY"} and not str(c).startswith("Unnamed:")
    ]
    selected = [c for c in OBS_STATIONS if c in station_columns]
    usecols = ["YEAR", "MONTH", "DAY", *selected]
    frame = pd.read_csv(path, usecols=usecols)
    dates = pd.to_datetime(
        dict(year=frame["YEAR"], month=frame["MONTH"], day=frame["DAY"]),
        errors="coerce",
    )
    valid_dates = pd.DatetimeIndex(dates.dropna())
    duplicate_dates = int(valid_dates.duplicated().sum())
    missing_dates = pd.DatetimeIndex([])
    if len(valid_dates):
        complete = pd.date_range(valid_dates.min(), valid_dates.max(), freq="D")
        missing_dates = complete.difference(valid_dates)
    missing_only_feb29 = bool(
        len(missing_dates)
        and all(d.month == 2 and d.day == 29 for d in missing_dates)
    )
    if not len(missing_dates):
        calendar = "gregorian_complete"
    elif missing_only_feb29:
        calendar = "noleap"
    else:
        calendar = "internal_gaps"

    values = frame[selected].apply(pd.to_numeric, errors="coerce") if selected else pd.DataFrame()
    array = values.to_numpy(dtype=float) if selected else np.empty((len(frame), 0))
    finite = np.isfinite(array)
    unique_series = 0
    if selected:
        canonical = np.nan_to_num(array.T, nan=-9.96921e36, posinf=9.96922e36, neginf=-9.96923e36)
        unique_series = int(np.unique(canonical, axis=0).shape[0])

    return {
        "relative_path": str(path.relative_to(DATA_ROOT)),
        "source_type": source_type,
        "model": model,
        "scenario": scenario,
        "rows": int(len(frame)),
        "station_columns_total": int(len(station_columns)),
        "uttaradit_station_columns": int(len(selected)),
        "trailing_empty_columns": int(len(unnamed)),
        "first_date": str(valid_dates.min().date()) if len(valid_dates) else "",
        "last_date": str(valid_dates.max().date()) if len(valid_dates) else "",
        "invalid_dates": int(dates.isna().sum()),
        "duplicate_dates": duplicate_dates,
        "missing_calendar_dates": int(len(missing_dates)),
        "missing_non_feb29_dates": int(sum(not (d.month == 2 and d.day == 29) for d in missing_dates)),
        "calendar_inferred": calendar,
        "missing_rain_values": int(np.isnan(array).sum()),
        "nonfinite_rain_values": int((~finite).sum()),
        "tiny_negative_rain_values": int(((array[finite] < 0) & (array[finite] >= -1e-6)).sum()) if finite.any() else 0,
        "material_negative_rain_values": int((array[finite] < -1e-6).sum()) if finite.any() else 0,
        "zero_rain_pct": round(float(100 * (array[finite] == 0).mean()), 4) if finite.any() else np.nan,
        "min_rain_mm": round(float(array[finite].min()), 6) if finite.any() else np.nan,
        "max_rain_mm": round(float(array[finite].max()), 6) if finite.any() else np.nan,
        "unique_uttaradit_series": unique_series,
    }


csv_files = sorted(DATA_ROOT.rglob("*.csv"))
profiles = [profile_csv(path) for path in csv_files]
profile_frame = pd.DataFrame(profiles)
profile_frame.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

coord_path = DATA_ROOT / "station_coordinates.xlsx"
coord_book = pd.ExcelFile(coord_path)
coord_info = []
for sheet in coord_book.sheet_names:
    table = pd.read_excel(coord_path, sheet_name=sheet)
    normalized = {str(c).strip().lower(): c for c in table.columns}
    station_col = next((normalized[k] for k in normalized if "station" in k), None)
    lat_col = next((normalized[k] for k in normalized if k in {"lat", "latitude"}), None)
    lon_col = next((normalized[k] for k in normalized if k in {"lon", "lng", "longitude"}), None)
    stations = set()
    if station_col is not None:
        stations = set(table[station_col].dropna().astype(str).str.replace(r"\.0$", "", regex=True))
    coord_info.append({
        "sheet": sheet,
        "rows": int(len(table)),
        "columns": list(map(str, table.columns)),
        "duplicate_station_ids": int(table[station_col].duplicated().sum()) if station_col is not None else None,
        "observed_station_coverage": int(len(stations.intersection(OBS_STATIONS))),
        "missing_lat": int(table[lat_col].isna().sum()) if lat_col is not None else None,
        "missing_lon": int(table[lon_col].isna().sum()) if lon_col is not None else None,
    })

# Run the supplied observed-data QC logic without modifying the source data.
sys.path.insert(0, str(FRAMEWORK_ROOT / "src"))
from cmip6bc.qc_observed import apply_flags, diagnose as diagnose_observed  # noqa: E402
import yaml  # noqa: E402

cfg = yaml.safe_load((FRAMEWORK_ROOT / "config" / "uttaradit.yaml").read_text(encoding="utf-8"))
obs = pd.read_csv(DATA_ROOT / "Observed_Rain_daily_198101_201412_Uttaradit.csv")
obs.index = pd.to_datetime(dict(year=obs.pop("YEAR"), month=obs.pop("MONTH"), day=obs.pop("DAY")))
obs.columns = obs.columns.astype(str)
qc = diagnose_observed(obs, cfg["observed_qc"])
qc_counts = {str(k): int(v) for k, v in qc["classification"].value_counts().items()}
probable = qc.loc[
    qc["classification"].eq("probable_missing"),
    ["station", "year", "month", "monthly_total_mm", "neighbour_median_mm", "n_indicators"],
].to_dict(orient="records")
obs_qc, _ = apply_flags(obs, qc)


def complete_station_seasons(data: pd.DataFrame, starts: range, season: str) -> dict:
    total = complete = 0
    incomplete_rows = []
    for start in starts:
        if season == "RAIN":
            first, last = pd.Timestamp(start, 5, 1), pd.Timestamp(start, 10, 31)
            season_id = f"{start}_RAIN"
        else:
            first, last = pd.Timestamp(start, 11, 1), pd.Timestamp(start + 1, 4, 30)
            season_id = f"{start}_{str(start + 1)[-2:]}_HOT_DRY"
        block = data.loc[first:last]
        expected_days = len(pd.date_range(first, last, freq="D"))
        for station in data.columns:
            total += 1
            n_valid = int(block[station].notna().sum())
            if n_valid == expected_days:
                complete += 1
            else:
                incomplete_rows.append({
                    "season_id": season_id,
                    "station": str(station),
                    "n_valid": n_valid,
                    "expected_days": expected_days,
                })
    return {
        "station_seasons_total": total,
        "station_seasons_complete": complete,
        "station_seasons_incomplete": total - complete,
        "incomplete_examples": incomplete_rows,
    }


season_completeness = {
    "rainy_1995_2014": complete_station_seasons(obs_qc, range(1995, 2015), "RAIN"),
    "hot_dry_1995_2013": complete_station_seasons(obs_qc, range(1995, 2014), "HOT_DRY"),
}

obs_rows = profile_frame[profile_frame.source_type == "observed"]
raw_rows = profile_frame[profile_frame.source_type == "raw_cmip6"]
bc_rows = profile_frame[profile_frame.source_type == "legacy_bc"]

summary = {
    "csv_files": int(len(profile_frame)),
    "observed_copies": int(len(obs_rows)),
    "raw_cmip6_files": int(len(raw_rows)),
    "legacy_bc_files": int(len(bc_rows)),
    "models": sorted(raw_rows.model.unique().tolist()),
    "scenarios": sorted(raw_rows.scenario.unique().tolist()),
    "raw_model_scenario_pairs": int(raw_rows[["model", "scenario"]].drop_duplicates().shape[0]),
    "raw_files_with_internal_date_gaps": int((raw_rows.calendar_inferred == "internal_gaps").sum()),
    "raw_files_with_duplicate_dates": int((raw_rows.duplicate_dates > 0).sum()),
    "raw_files_with_missing_values": int((raw_rows.missing_rain_values > 0).sum()),
    "raw_files_with_tiny_negative_values": int((raw_rows.tiny_negative_rain_values > 0).sum()),
    "raw_files_with_material_negative_values": int((raw_rows.material_negative_rain_values > 0).sum()),
    "raw_files_with_trailing_empty_column": int((raw_rows.trailing_empty_columns > 0).sum()),
    "raw_unique_series_min": int(raw_rows.unique_uttaradit_series.min()),
    "raw_unique_series_max": int(raw_rows.unique_uttaradit_series.max()),
    "coordinate_sheets": coord_info,
    "boundary_components": sorted(p.name for p in (DATA_ROOT / "gis").glob("boundary.*")),
    "observed_qc_class_counts": qc_counts,
    "observed_probable_missing_station_months": probable,
    "observed_primary_period_completeness_after_qc": season_completeness,
}
OUT_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

print(json.dumps(summary, indent=2, ensure_ascii=False))
