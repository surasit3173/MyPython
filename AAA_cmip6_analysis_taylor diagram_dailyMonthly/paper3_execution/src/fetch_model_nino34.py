"""Fetch exact-member CMIP6 SST and derive reproducible Niño-3.4 indices.

The script reads only public Pangeo CMIP6 Zarr stores listed in the frozen local
catalog snapshot.  It writes derived monthly index CSVs and a provenance
manifest; no full-field SST is retained.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import gcsfs
import numpy as np
import pandas as pd
import xarray as xr


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "inputs" / "pangeo-cmip6_catalog.csv"
OUT_DIR = ROOT / "inputs" / "enso"
START_YEAR = 1981
END_YEAR = 2014
BASE_START = 1981
BASE_END = 2010
THRESHOLD_C = 0.5
MIN_RUN = 5

# The precipitation filenames supply the exact source and variant labels.
# Ocean native grids can legitimately differ from atmospheric output grids.
MODEL_SPECS = {
    "ACCESS-ESM1-5": {"member_id": "r1i1p1f1", "pr_grid": "gn", "tos_grid": "gn"},
    "CanESM5": {"member_id": "r1i1p1f1", "pr_grid": "gn", "tos_grid": "gn"},
    "CESM2": {"member_id": "r11i1p1f1", "pr_grid": "gn", "tos_grid": "gn"},
    "EC-Earth3": {"member_id": "r1i1p1f1", "pr_grid": "gr", "tos_grid": "gn"},
    "FGOALS-g3": {"member_id": "r1i1p1f1", "pr_grid": "gn", "tos_grid": "gn"},
    "MIROC6": {"member_id": "r1i1p1f1", "pr_grid": "gn", "tos_grid": "gn"},
    "MRI-ESM2-0": {"member_id": "r1i1p1f1", "pr_grid": "gn", "tos_grid": "gn"},
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def select_one(catalog: pd.DataFrame, model: str, member: str, variable: str,
               table: str, grid: str) -> pd.Series:
    rows = catalog[
        (catalog["activity_id"] == "CMIP")
        & (catalog["source_id"] == model)
        & (catalog["experiment_id"] == "historical")
        & (catalog["member_id"] == member)
        & (catalog["variable_id"] == variable)
        & (catalog["table_id"] == table)
        & (catalog["grid_label"] == grid)
    ].copy()
    if len(rows) != 1:
        raise RuntimeError(
            f"Expected exactly one {model}/{member}/{table}/{variable}/{grid} store; "
            f"found {len(rows)}"
        )
    return rows.iloc[0]


def coordinate_names(dataset: xr.Dataset) -> tuple[str, str]:
    lat_candidates = ("latitude", "lat", "nav_lat")
    lon_candidates = ("longitude", "lon", "nav_lon")
    lat_name = next((name for name in lat_candidates if name in dataset), None)
    lon_name = next((name for name in lon_candidates if name in dataset), None)
    if lat_name is None or lon_name is None:
        raise RuntimeError(f"Latitude/longitude coordinates not found: {list(dataset.coords)}")
    return lat_name, lon_name


def datetime_index(values: np.ndarray) -> pd.DatetimeIndex:
    # Works for numpy datetimes and cftime calendars while preserving year/month.
    converted = []
    for value in values:
        if isinstance(value, np.datetime64):
            timestamp = pd.Timestamp(value)
            converted.append(pd.Timestamp(year=timestamp.year, month=timestamp.month, day=1))
        else:
            converted.append(
                pd.Timestamp(year=int(value.year), month=int(value.month), day=1)
            )
    return pd.DatetimeIndex(converted)


def persistent_episode_sign(index: pd.Series) -> pd.Series:
    candidate = pd.Series(
        np.where(index >= THRESHOLD_C, 1, np.where(index <= -THRESHOLD_C, -1, 0)),
        index=index.index,
        dtype="int8",
    )
    episode = pd.Series(0, index=index.index, dtype="int8")
    group_id = candidate.ne(candidate.shift()).cumsum()
    for _, positions in candidate.groupby(group_id).groups.items():
        locs = list(positions)
        sign = int(candidate.loc[locs[0]])
        if sign != 0 and len(locs) >= MIN_RUN:
            episode.loc[locs] = sign
    return episode


def derive_index(model: str, spec: dict[str, str], catalog: pd.DataFrame,
                 filesystem: gcsfs.GCSFileSystem) -> tuple[pd.DataFrame, dict[str, object]]:
    tos_row = select_one(
        catalog, model, spec["member_id"], "tos", "Omon", spec["tos_grid"]
    )
    area_row = select_one(
        catalog, model, spec["member_id"], "areacello", "Ofx", spec["tos_grid"]
    )

    print(f"OPEN {model} tos={tos_row.zstore}", flush=True)
    tos_dataset = xr.open_zarr(
        filesystem.get_mapper(tos_row.zstore), consolidated=True, chunks="auto"
    )
    area_dataset = xr.open_zarr(
        filesystem.get_mapper(area_row.zstore), consolidated=True, chunks="auto"
    )
    if str(tos_dataset.attrs.get("variant_label")) != spec["member_id"]:
        raise RuntimeError(f"Variant mismatch for {model}: {tos_dataset.attrs.get('variant_label')}")

    lat_name, lon_name = coordinate_names(tos_dataset)
    latitude = tos_dataset[lat_name]
    longitude_360 = tos_dataset[lon_name] % 360.0
    region_mask = (
        (latitude >= -5.0)
        & (latitude <= 5.0)
        & (longitude_360 >= 190.0)
        & (longitude_360 <= 240.0)
    )
    selected_cells = int(region_mask.sum().compute().item())
    if selected_cells < 2:
        raise RuntimeError(f"Too few Niño-3.4 ocean-grid cells for {model}: {selected_cells}")

    tos = tos_dataset["tos"].sel(time=slice(f"{START_YEAR}-01-01", f"{END_YEAR}-12-31"))
    area = area_dataset["areacello"]
    spatial_dims = tuple(dimension for dimension in tos.dims if dimension != "time")
    if set(area.dims) != set(spatial_dims):
        area = area.broadcast_like(tos.isel(time=0, drop=True))

    weights = area.where(region_mask).fillna(0.0)
    regional_tos = tos.where(region_mask).weighted(weights).mean(spatial_dims, skipna=True)
    regional_tos = regional_tos.compute()
    units = str(tos.attrs.get("units", ""))
    values = regional_tos.values.astype(float)
    if units.lower() in {"k", "kelvin"} or np.nanmedian(values) > 100.0:
        values = values - 273.15

    dates = datetime_index(regional_tos["time"].values)
    frame = pd.DataFrame({"date": dates, "sst_c": values}).set_index("date")
    if len(frame) != (END_YEAR - START_YEAR + 1) * 12:
        raise RuntimeError(f"Unexpected monthly count for {model}: {len(frame)}")
    if frame["sst_c"].isna().any():
        raise RuntimeError(f"Missing Niño-3.4 SST values for {model}")

    base = frame.loc[f"{BASE_START}-01-01":f"{BASE_END}-12-01"]
    climatology = base.groupby(base.index.month)["sst_c"].mean()
    frame["monthly_climatology_c"] = frame.index.month.map(climatology).astype(float)
    frame["anomaly_c"] = frame["sst_c"] - frame["monthly_climatology_c"]

    time_axis = np.arange(len(frame), dtype=float)
    slope, _ = np.polyfit(time_axis, frame["anomaly_c"].to_numpy(), 1)
    centered_time = time_axis - time_axis.mean()
    frame["anomaly_detrended_c"] = frame["anomaly_c"] - slope * centered_time
    frame["nino34_3month_c"] = frame["anomaly_detrended_c"].rolling(
        window=3, center=True, min_periods=3
    ).mean()
    frame["episode_sign"] = persistent_episode_sign(frame["nino34_3month_c"])
    frame["episode_phase"] = frame["episode_sign"].map(
        {-1: "LA_NINA", 0: "NO_PERSISTENT_EPISODE", 1: "EL_NINO"}
    )
    frame.insert(0, "model", model)
    frame.insert(1, "member_id", spec["member_id"])
    frame = frame.reset_index()

    metadata = {
        "model": model,
        "member_id": spec["member_id"],
        "pr_grid_label": spec["pr_grid"],
        "tos_grid_label": spec["tos_grid"],
        "tos_table_id": "Omon",
        "tos_version": str(tos_row.version),
        "tos_zstore": str(tos_row.zstore),
        "areacello_version": str(area_row.version),
        "areacello_zstore": str(area_row.zstore),
        "tos_tracking_id": str(tos_dataset.attrs.get("tracking_id", "")),
        "tos_variant_label": str(tos_dataset.attrs.get("variant_label", "")),
        "tos_units_original": units,
        "nino34_selected_grid_cells": selected_cells,
        "start": frame["date"].min().date().isoformat(),
        "end": frame["date"].max().date().isoformat(),
        "n_months": int(len(frame)),
        "climatology_period": f"{BASE_START}-{BASE_END}",
        "linear_trend_removed_c_per_month": float(slope),
        "threshold_c": THRESHOLD_C,
        "minimum_consecutive_overlapping_seasons": MIN_RUN,
    }
    tos_dataset.close()
    area_dataset.close()
    return frame, metadata


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    catalog = pd.read_csv(CATALOG)
    filesystem = gcsfs.GCSFileSystem(token="anon", access="read_only")
    all_frames: list[pd.DataFrame] = []
    manifest_rows: list[dict[str, object]] = []

    for model, spec in MODEL_SPECS.items():
        frame, metadata = derive_index(model, spec, catalog, filesystem)
        output = OUT_DIR / f"nino34_{model}_{spec['member_id']}_1981-2014.csv"
        frame.to_csv(output, index=False, float_format="%.6f")
        metadata["derived_csv"] = str(output)
        metadata["derived_csv_sha256"] = sha256_file(output)
        manifest_rows.append(metadata)
        all_frames.append(frame)
        print(
            f"DONE {model} months={len(frame)} cells={metadata['nino34_selected_grid_cells']} "
            f"sha256={metadata['derived_csv_sha256']}",
            flush=True,
        )

    combined = pd.concat(all_frames, ignore_index=True)
    combined_path = OUT_DIR / "model_nino34_monthly_1981-2014.csv"
    combined.to_csv(combined_path, index=False, float_format="%.6f")
    manifest = {
        "catalog_path": str(CATALOG),
        "catalog_sha256": sha256_file(CATALOG),
        "region": "Niño-3.4 (5S-5N, 170W-120W; 190E-240E)",
        "spatial_weighting": "CMIP6 areacello on each exact-member native ocean grid",
        "analysis_period": f"{START_YEAR}-{END_YEAR}",
        "climatology_period": f"{BASE_START}-{BASE_END}",
        "anomaly_method": "calendar-month climatology followed by centered linear-trend removal",
        "temporal_filter": "centered 3-month running mean",
        "episode_rule": f"abs(index) >= {THRESHOLD_C} C for >= {MIN_RUN} consecutive overlapping seasons",
        "combined_csv": str(combined_path),
        "combined_csv_sha256": sha256_file(combined_path),
        "datasets": manifest_rows,
    }
    manifest_path = OUT_DIR / "model_nino34_source_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"MANIFEST {manifest_path}", flush=True)


if __name__ == "__main__":
    main()
