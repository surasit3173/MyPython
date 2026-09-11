from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from rainfall_trends.aggregation import build_period_totals
from rainfall_trends.io import (
    InputContractError,
    load_rainfall,
    load_station_metadata,
    validate_station_keys,
)


def test_missing_observation_file_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(InputContractError, match="does not exist"):
        load_rainfall(tmp_path / "absent.csv", layout="wide")


def test_wide_csv_normalizes_to_station_days(tmp_path: Path) -> None:
    source = tmp_path / "rain.csv"
    pd.DataFrame(
        {
            "Year": [2000, 2000],
            "Month": [1, 1],
            "Day": [1, 2],
            "500001": [1.0, 2.0],
            "500002": [3.0, 4.0],
        }
    ).to_csv(source, index=False)
    got = load_rainfall(source, layout="wide")
    assert list(got.columns) == ["date", "station_id", "rain_mm"]
    assert len(got) == 4
    assert set(got["station_id"]) == {"500001", "500002"}
    assert got["rain_mm"].sum() == 10.0


def test_long_csv_normalizes_with_explicit_schema(tmp_path: Path) -> None:
    source = tmp_path / "rain_long.csv"
    pd.DataFrame(
        {
            "observation_date": ["2000-01-01", "2000-01-01"],
            "gauge": ["A01", "A02"],
            "precipitation": [1.5, 2.5],
        }
    ).to_csv(source, index=False)
    got = load_rainfall(
        source,
        layout="long",
        date_column="observation_date",
        station_column="gauge",
        value_column="precipitation",
    )
    assert got.to_dict("records") == [
        {"date": pd.Timestamp("2000-01-01"), "station_id": "A01", "rain_mm": 1.5},
        {"date": pd.Timestamp("2000-01-01"), "station_id": "A02", "rain_mm": 2.5},
    ]


@pytest.mark.parametrize("bad_value", [-0.1, np.inf])
def test_invalid_rainfall_fails(tmp_path: Path, bad_value: float) -> None:
    source = tmp_path / "rain.csv"
    pd.DataFrame({"Year": [2000], "Month": [1], "Day": [1], "500001": [bad_value]}).to_csv(source, index=False)
    with pytest.raises(InputContractError):
        load_rainfall(source, layout="wide")


def test_bad_date_and_duplicate_station_day_fail(tmp_path: Path) -> None:
    bad_date = tmp_path / "bad_date.csv"
    pd.DataFrame({"Year": [2001], "Month": [2], "Day": [29], "500001": [1.0]}).to_csv(bad_date, index=False)
    with pytest.raises(InputContractError, match="date"):
        load_rainfall(bad_date, layout="wide")

    duplicate = tmp_path / "duplicate.csv"
    pd.DataFrame(
        {"Year": [2000, 2000], "Month": [1, 1], "Day": [1, 1], "500001": [1.0, 2.0]}
    ).to_csv(duplicate, index=False)
    with pytest.raises(InputContractError, match="duplicate"):
        load_rainfall(duplicate, layout="wide")


def test_metadata_aliases_and_unknown_keys(tmp_path: Path) -> None:
    path = tmp_path / "stations.csv"
    pd.DataFrame(
        {
            "Station_id": [500001, 500002],
            "Latitude": [11.1, 11.2],
            "Longitude": [99.5, 99.6],
            "elevation (m.MSL.)": [5, 10],
        }
    ).to_csv(path, index=False)
    metadata = load_station_metadata(
        path,
        station_column="Station_id",
        latitude_column="Latitude",
        longitude_column="Longitude",
        elevation_column="elevation (m.MSL.)",
    )
    assert list(metadata.columns) == ["station_id", "latitude", "longitude", "elevation_m"]
    obs = pd.DataFrame({"date": [pd.Timestamp("2000-01-01")], "station_id": ["999999"], "rain_mm": [1.0]})
    with pytest.raises(InputContractError, match="999999"):
        validate_station_keys(obs, metadata)


def test_dry_hydrological_edges_are_incomplete() -> None:
    dates = pd.date_range("1981-01-01", "1982-12-31", freq="D")
    obs = pd.DataFrame(
        {
            "date": dates,
            "station_id": "500001",
            "rain_mm": 1.0,
        }
    )
    totals = build_period_totals(obs)
    dry = totals[totals["period"] == "dry"].set_index("year")
    assert list(dry.index) == [1981, 1982, 1983]
    assert not bool(dry.loc[1981, "included"])
    assert bool(dry.loc[1982, "included"])
    assert not bool(dry.loc[1983, "included"])
    assert dry.loc[1982, "total_mm"] == dry.loc[1982, "expected_days"]


def test_real_inputs_have_expected_complete_period_counts() -> None:
    package_root = Path(__file__).resolve().parents[1]
    rain = load_rainfall(
        package_root / "data" / "observed_rain_daily.csv",
        layout="wide",
        date_columns=("YEAR", "MONTH", "DAY"),
    )
    metadata = load_station_metadata(
        package_root / "data" / "station_coordinates.csv",
        station_column="station",
        latitude_column="latitude",
        longitude_column="longitude",
        elevation_column="elevation (m.MSL.)",
    )
    validate_station_keys(rain, metadata)
    totals = build_period_totals(rain)
    assert rain.shape[0] == 149_016
    assert rain["station_id"].nunique() == 12
    counts = totals[totals["included"]].groupby(["station_id", "period"]).size().unstack()
    assert (counts["annual"] == 34).all()
    assert (counts["wet"] == 34).all()
    assert (counts["dry"] == 33).all()
