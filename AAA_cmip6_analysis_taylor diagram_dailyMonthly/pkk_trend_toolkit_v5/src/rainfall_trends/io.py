"""Fail-closed observational input loading."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import pandas as pd


class InputContractError(ValueError):
    """Raised when observational inputs violate the declared contract."""


def load_rainfall(
    path: str | Path,
    *,
    layout: str,
    date_columns: Sequence[str] = ("Year", "Month", "Day"),
    date_column: str = "date",
    station_column: str = "station_id",
    value_column: str = "rain_mm",
) -> pd.DataFrame:
    source = Path(path)
    if not source.is_file():
        raise InputContractError(f"Rainfall file does not exist: {source}")
    if layout not in {"wide", "long"}:
        raise InputContractError("layout must be 'wide' or 'long'")
    try:
        raw = pd.read_csv(source)
    except Exception as exc:
        raise InputContractError(f"Cannot read rainfall CSV {source}: {exc}") from exc
    if raw.empty:
        raise InputContractError("Rainfall CSV is empty")

    if layout == "wide":
        date_fields = list(date_columns)
        missing = [field for field in date_fields if field not in raw.columns]
        if missing:
            raise InputContractError(f"Missing date columns: {missing}")
        station_fields = [str(field) for field in raw.columns if field not in date_fields]
        if not station_fields:
            raise InputContractError("Wide rainfall CSV has no station columns")
        parsed_dates = pd.to_datetime(
            {
                "year": raw[date_fields[0]],
                "month": raw[date_fields[1]],
                "day": raw[date_fields[2]],
            },
            errors="coerce",
        )
        if parsed_dates.isna().any():
            rows = (parsed_dates.isna().to_numpy().nonzero()[0] + 2).tolist()
            raise InputContractError(f"Invalid calendar date at CSV rows {rows[:10]}")
        working = raw.copy()
        working["__date__"] = parsed_dates
        long = working.melt(
            id_vars=["__date__"],
            value_vars=[field for field in raw.columns if field not in date_fields],
            var_name="__station__",
            value_name="__rain__",
        )
    else:
        required = [date_column, station_column, value_column]
        missing = [field for field in required if field not in raw.columns]
        if missing:
            raise InputContractError(f"Missing long-format columns: {missing}")
        parsed_dates = pd.to_datetime(raw[date_column], errors="coerce")
        if parsed_dates.isna().any():
            rows = (parsed_dates.isna().to_numpy().nonzero()[0] + 2).tolist()
            raise InputContractError(f"Invalid calendar date at CSV rows {rows[:10]}")
        long = pd.DataFrame(
            {
                "__date__": parsed_dates,
                "__station__": raw[station_column],
                "__rain__": raw[value_column],
            }
        )

    station_ids = long["__station__"].astype("string").str.strip()
    if station_ids.isna().any() or (station_ids == "").any():
        raise InputContractError("Station identifiers must be non-empty")
    numeric = pd.to_numeric(long["__rain__"], errors="coerce")
    invalid_text = long["__rain__"].notna() & numeric.isna()
    if invalid_text.any():
        raise InputContractError("Rainfall contains non-numeric values")
    finite = numeric.notna() & ~numeric.map(lambda value: bool(pd.notna(value) and float("-inf") < value < float("inf")))
    if finite.any():
        raise InputContractError("Rainfall contains non-finite values")
    if (numeric.dropna() < 0).any():
        raise InputContractError("Rainfall cannot be negative")

    result = pd.DataFrame(
        {
            "date": pd.to_datetime(long["__date__"]).dt.normalize(),
            "station_id": station_ids.astype(str),
            "rain_mm": numeric.astype(float),
        }
    ).sort_values(["date", "station_id"], kind="stable", ignore_index=True)
    duplicated = result.duplicated(["date", "station_id"], keep=False)
    if duplicated.any():
        examples = result.loc[duplicated, ["date", "station_id"]].head(10).astype(str).to_dict("records")
        raise InputContractError(f"Rainfall contains duplicate station-day rows: {examples}")
    return result


def load_station_metadata(
    path: str | Path,
    *,
    station_column: str,
    latitude_column: str,
    longitude_column: str,
    elevation_column: str,
) -> pd.DataFrame:
    source = Path(path)
    if not source.is_file():
        raise InputContractError(f"Station metadata file does not exist: {source}")
    try:
        raw = pd.read_csv(source)
    except Exception as exc:
        raise InputContractError(f"Cannot read station metadata CSV {source}: {exc}") from exc
    required = [station_column, latitude_column, longitude_column, elevation_column]
    missing = [field for field in required if field not in raw.columns]
    if missing:
        raise InputContractError(f"Missing station metadata columns: {missing}")
    result = raw[required].rename(
        columns={
            station_column: "station_id",
            latitude_column: "latitude",
            longitude_column: "longitude",
            elevation_column: "elevation_m",
        }
    ).copy()
    result["station_id"] = result["station_id"].astype("string").str.strip().astype(str)
    for field in ("latitude", "longitude"):
        result[field] = pd.to_numeric(result[field], errors="coerce")
        if result[field].isna().any() or (~result[field].map(lambda value: float("-inf") < value < float("inf"))).any():
            raise InputContractError(f"Station metadata field {field} must be finite numeric")
    raw_elevation = result["elevation_m"].astype("string").str.strip()
    explicit_missing = raw_elevation.isna() | raw_elevation.str.upper().isin({"", "NA", "N/A", "NS", "NAN"})
    result["elevation_m"] = pd.to_numeric(raw_elevation.mask(explicit_missing), errors="coerce")
    invalid_elevation = ~explicit_missing & result["elevation_m"].isna()
    if invalid_elevation.any():
        bad = sorted(raw_elevation[invalid_elevation].dropna().unique().tolist())
        raise InputContractError(f"Unrecognized elevation values: {bad}")
    finite_elevation = result["elevation_m"].dropna().map(lambda value: float("-inf") < value < float("inf"))
    if not finite_elevation.all():
        raise InputContractError("Station metadata field elevation_m must be finite when supplied")
    if result["station_id"].duplicated().any():
        duplicated = sorted(result.loc[result["station_id"].duplicated(False), "station_id"].unique())
        raise InputContractError(f"Duplicate station identifiers: {duplicated}")
    if (~result["latitude"].between(-90, 90)).any() or (~result["longitude"].between(-180, 180)).any():
        raise InputContractError("Station coordinates fall outside valid latitude/longitude ranges")
    return result.sort_values("station_id", kind="stable", ignore_index=True)


def validate_station_keys(observations: pd.DataFrame, metadata: pd.DataFrame) -> None:
    observed = set(observations["station_id"].astype(str))
    declared = set(metadata["station_id"].astype(str))
    unknown = sorted(observed - declared)
    missing = sorted(declared - observed)
    if unknown or missing:
        details: list[str] = []
        if unknown:
            details.append(f"unknown in rainfall={unknown}")
        if missing:
            details.append(f"missing from rainfall={missing}")
        raise InputContractError("Station key mismatch: " + "; ".join(details))
