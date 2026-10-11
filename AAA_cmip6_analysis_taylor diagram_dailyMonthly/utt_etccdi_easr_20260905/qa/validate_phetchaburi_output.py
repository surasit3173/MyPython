"""Independent QA checks for the Phetchaburi portable run."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path(sys.argv[1]).resolve() if len(sys.argv) == 2 else ROOT / "outputs" / "phetchaburi_full"
RESULTS = OUTPUT / "results"


def read(name: str) -> pd.DataFrame:
    path = RESULTS / name
    assert path.is_file() and path.stat().st_size > 0, f"missing/empty: {path}"
    return pd.read_csv(path)


def main() -> None:
    metadata = json.loads((RESULTS / "analysis_metadata.json").read_text(encoding="utf-8"))
    assert metadata["province_name"] == "Phetchaburi"
    assert metadata["station_count"] == 13
    observed = read("observed_trend.csv")
    future = read("future_trend.csv")
    changes = read("future_change.csv")
    coordinates = read("station_coordinates_used.csv")
    manifest = read("cmip6_file_manifest.csv")
    qc = read("qc_models.csv")

    assert len(observed) == 13 * 11
    assert len(future) == 7 * 2 * 13 * 11
    assert len(changes) == 7 * 2 * 13 * 11
    assert len(coordinates) == 13
    assert len(manifest) == 21
    assert not manifest.duplicated(["Model", "Dataset_period"]).any()
    assert set(manifest["Status"]) == {"OK"}
    assert qc["completeness_pct"].ge(90.0).all()
    assert not observed.duplicated(["Station", "Index"]).any()
    assert not future.duplicated(["Model", "Scenario", "Station", "Index"]).any()
    assert not changes.duplicated(["Model", "Scenario", "Station", "Index"]).any()

    # One observed SDII series has no wet day in 2010; standard MK remains
    # valid, while MMK is explicitly marked IRREGULAR_ANNUAL_YEARS.
    invalid_mmk = observed[~np.isfinite(observed["p_MMK2004"])]
    assert len(invalid_mmk) == 1
    assert set(invalid_mmk["MMK_status"]) == {"IRREGULAR_ANNUAL_YEARS"}
    finite_p = pd.concat([observed["p_MMK2004"], future["p_MMK2004"]]).dropna()
    assert finite_p.between(0.0, 1.0).all()
    for frame in (observed, future):
        assert frame["p_MK"].between(0.0, 1.0).all()
        assert (frame["Sen_CI95_low"] <= frame["Sen_slope"]).all()
        assert (frame["Sen_slope"] <= frame["Sen_CI95_high"]).all()
    assert np.allclose(changes["Absolute_change"], changes["Future_mean"] - changes["Baseline_mean"])

    figure_count = len(list((OUTPUT / "figures").glob("*.png")))
    assert figure_count == 33
    workbook = RESULTS / "Phetchaburi_Trend_Analysis.xlsx"
    assert ZipFile(workbook).testzip() is None
    print("PETCHABURI_OUTPUT_QA_OK")
    print(f"rows observed={len(observed)} future={len(future)} changes={len(changes)} figures={figure_count}")
    print(f"mmk_unavailable_rows={len(invalid_mmk)} status=IRREGULAR_ANNUAL_YEARS")
    print(f"model_qc_min_completeness_pct={qc['completeness_pct'].min():.6f}")


if __name__ == "__main__":
    main()
