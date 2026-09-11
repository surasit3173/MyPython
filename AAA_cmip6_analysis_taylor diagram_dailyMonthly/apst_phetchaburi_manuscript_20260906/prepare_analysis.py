from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "utt_etccdi_easr_20260905"
PRIMARY = PROJECT / "outputs" / "phetchaburi_final2" / "results"
SENSITIVITY = PROJECT / "outputs" / "phetchaburi_465002_reference_final" / "results"
OUT = Path(__file__).resolve().parent / "derived"

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


def bh_adjust(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    adjusted = np.full(values.shape, np.nan, dtype=float)
    finite = np.isfinite(values)
    p = values[finite]
    order = np.argsort(p)
    ranked = p[order] * len(p) / np.arange(1, len(p) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    q = np.empty_like(ranked)
    q[order] = np.minimum(ranked, 1.0)
    adjusted[finite] = q
    return adjusted


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def clean_float(value: float | int | np.floating, digits: int = 6) -> float | None:
    value = float(value)
    if not math.isfinite(value):
        return None
    return round(value, digits)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    observed = pd.read_csv(PRIMARY / "observed_trend.csv", dtype={"Station": str})
    future_trend = pd.read_csv(PRIMARY / "future_trend.csv", dtype={"Station": str})
    changes = pd.read_csv(PRIMARY / "future_change.csv", dtype={"Station": str})
    observed_indices = pd.read_csv(PRIMARY / "observed_indices.csv", dtype={"Station": str})
    future_indices = pd.read_csv(PRIMARY / "future_indices.csv", dtype={"Station": str})
    thresholds = pd.read_csv(PRIMARY / "station_thresholds.csv", dtype={"Station": str})
    coords_primary = pd.read_csv(PRIMARY / "station_coordinates_used.csv", dtype={"station": str})
    coords_sensitivity = pd.read_csv(SENSITIVITY / "station_coordinates_used.csv", dtype={"station": str})
    qc_models = pd.read_csv(PRIMARY / "qc_models.csv", low_memory=False)

    observed = observed.copy()
    observed["p_MK_BH"] = bh_adjust(pd.to_numeric(observed["p_MK"], errors="coerce").to_numpy())
    observed["Significant_MK_BH"] = observed["p_MK_BH"] < 0.05
    observed["Trend_MK_BH"] = "No significant trend"
    # Direction follows the standard MK statistic (Z_MK/Trend_MK).  Count
    # indices such as R50mm can have a zero Sen slope while their MK statistic
    # has a non-zero direction; using Sen_slope here would misclassify them.
    observed.loc[observed["Significant_MK_BH"] & (observed["Z_MK"] > 0), "Trend_MK_BH"] = "Increasing"
    observed.loc[observed["Significant_MK_BH"] & (observed["Z_MK"] < 0), "Trend_MK_BH"] = "Decreasing"

    observed_rows: list[dict[str, object]] = []
    for index in INDICES:
        block = observed.loc[observed["Index"] == index]
        raw = block["Trend_MK"].value_counts()
        fdr = block["Trend_MK_BH"].value_counts()
        unit = str(block["Sen_slope_unit"].iloc[0])
        observed_rows.append(
            {
                "Index": index,
                "Unit": str(block["Unit"].iloc[0]),
                "Sen_slope_unit": unit,
                "Increasing_MK": int(raw.get("Increasing", 0)),
                "Decreasing_MK": int(raw.get("Decreasing", 0)),
                "Not_significant_MK": int(raw.get("No significant trend", 0)),
                "Increasing_BH_FDR": int(fdr.get("Increasing", 0)),
                "Decreasing_BH_FDR": int(fdr.get("Decreasing", 0)),
                "Not_significant_BH_FDR": int(fdr.get("No significant trend", 0)),
                "Median_Sen_slope_per_year": clean_float(block["Sen_slope"].median()),
                "Median_Sen_slope_per_decade": clean_float(block["Sen_slope"].median() * 10),
            }
        )
    observed_summary = pd.DataFrame(observed_rows)
    observed_summary.to_csv(OUT / "table_observed_trends.csv", index=False)
    observed.to_csv(OUT / "observed_trend_with_bh_fdr.csv", index=False)

    model_summary = (
        changes.groupby(["Scenario", "Model", "Index"], as_index=False)["Relative_change_pct"]
        .median()
        .rename(columns={"Relative_change_pct": "Station_median_relative_change_pct"})
    )
    future_rows: list[dict[str, object]] = []
    for scenario in ["SSP2-4.5", "SSP5-8.5"]:
        for index in INDICES:
            vals = pd.to_numeric(
                model_summary.loc[
                    (model_summary["Scenario"] == scenario) & (model_summary["Index"] == index),
                    "Station_median_relative_change_pct",
                ],
                errors="coerce",
            ).dropna()
            q1, med, q3 = vals.quantile([0.25, 0.50, 0.75])
            future_rows.append(
                {
                    "Scenario": scenario,
                    "Index": index,
                    "N_models": int(vals.size),
                    "Median_relative_change_pct": clean_float(med),
                    "IQR_low_pct": clean_float(q1),
                    "IQR_high_pct": clean_float(q3),
                    "Min_pct": clean_float(vals.min()),
                    "Max_pct": clean_float(vals.max()),
                    "Positive_models": int((vals > 0).sum()),
                    "Negative_models": int((vals < 0).sum()),
                    "Zero_models": int((vals == 0).sum()),
                }
            )
    future_summary = pd.DataFrame(future_rows)
    future_summary.to_csv(OUT / "table_future_change_model_first.csv", index=False)
    model_summary.to_csv(OUT / "future_change_model_station_medians.csv", index=False)

    future_trend_rows: list[dict[str, object]] = []
    for scenario, block in future_trend.groupby("Scenario", sort=False):
        p = pd.to_numeric(block["p_MK"], errors="coerce")
        z = pd.to_numeric(block["Z_MK"], errors="coerce")
        sig = p < 0.05
        future_trend_rows.append(
            {
                "Scenario": scenario,
                "N_tests": int(len(block)),
                "Significant_MK": int(sig.sum()),
                "Significant_increasing_MK": int((sig & (z > 0)).sum()),
                "Significant_decreasing_MK": int((sig & (z < 0)).sum()),
            }
        )
    future_trend_summary = pd.DataFrame(future_trend_rows)
    future_trend_summary.to_csv(OUT / "future_within_window_mk_summary.csv", index=False)

    compare_files = [
        "observed_indices.csv",
        "observed_trend.csv",
        "future_indices.csv",
        "future_trend.csv",
        "future_change.csv",
        "station_thresholds.csv",
        "qc_models.csv",
        "qc_observed.csv",
        "future_model_agreement.csv",
        "summary_by_model_scenario.csv",
        "summary_by_index.csv",
    ]
    identity_rows = []
    for name in compare_files:
        primary_hash = sha256(PRIMARY / name)
        sensitivity_hash = sha256(SENSITIVITY / name)
        identity_rows.append(
            {
                "File": name,
                "Primary_SHA256": primary_hash,
                "Sensitivity_SHA256": sensitivity_hash,
                "Byte_identical": primary_hash == sensitivity_hash,
            }
        )
    identity = pd.DataFrame(identity_rows)
    identity.to_csv(OUT / "coordinate_sensitivity_file_identity.csv", index=False)

    primary_station = coords_primary.loc[coords_primary["station"] == "465002"].iloc[0]
    sensitivity_station = coords_sensitivity.loc[coords_sensitivity["station"] == "465002"].iloc[0]
    coordinate_distance_km = haversine_km(
        float(primary_station["latitude"]),
        float(primary_station["longitude"]),
        float(sensitivity_station["latitude"]),
        float(sensitivity_station["longitude"]),
    )

    min_model_completeness = None
    for candidate in ["completeness_pct", "Completeness_pct", "Completeness_percent", "Annual_completeness_pct"]:
        if candidate in qc_models.columns:
            vals = pd.to_numeric(qc_models[candidate], errors="coerce")
            if vals.notna().any():
                min_model_completeness = clean_float(vals.min())
                break

    p_mk = pd.to_numeric(observed["p_MK"], errors="coerce")
    p_mmk = pd.to_numeric(observed["p_MMK2004"], errors="coerce")
    mmk_finite = np.isfinite(p_mmk)
    report = {
        "data": {
            "stations": int(observed["Station"].nunique()),
            "indices": int(observed["Index"].nunique()),
            "models": int(changes["Model"].nunique()),
            "scenarios": sorted(changes["Scenario"].unique().tolist()),
            "observed_years": [int(observed_indices["Year"].min()), int(observed_indices["Year"].max())],
            "future_years": [int(future_indices["Year"].min()), int(future_indices["Year"].max())],
            "observed_index_rows": int(len(observed_indices)),
            "future_index_rows": int(len(future_indices)),
            "observed_trend_rows": int(len(observed)),
            "future_trend_rows": int(len(future_trend)),
            "future_change_rows": int(len(changes)),
            "minimum_model_annual_completeness_pct": min_model_completeness,
            "p95_threshold_range_mm": [clean_float(thresholds["P95_threshold_mm"].min()), clean_float(thresholds["P95_threshold_mm"].max())],
            "p99_threshold_range_mm": [clean_float(thresholds["P99_threshold_mm"].min()), clean_float(thresholds["P99_threshold_mm"].max())],
        },
        "observed_inference": {
            "standard_mk_significant_unadjusted": int((p_mk < 0.05).sum()),
            "standard_mk_significant_bh_fdr": int(observed["Significant_MK_BH"].sum()),
            "yue_wang_mmk_significant": int(((p_mmk < 0.05) & mmk_finite).sum()),
            "mk_mmk_same_conclusion": int(observed["MK_MMK_same_conclusion"].astype(str).str.lower().eq("true").sum()),
            "variance_factor_below_one": int((pd.to_numeric(observed["n_over_nstar"], errors="coerce") < 1).sum()),
            "mmk_nonfinite": int((~mmk_finite).sum()),
            "mmk_nonfinite_rows": observed.loc[~mmk_finite, ["Station", "Index", "MMK_status"]].to_dict("records"),
        },
        "coordinate_sensitivity": {
            "station": "465002",
            "primary_coordinate": [float(primary_station["latitude"]), float(primary_station["longitude"])],
            "reference_coordinate": [float(sensitivity_station["latitude"]), float(sensitivity_station["longitude"])],
            "haversine_distance_km": clean_float(coordinate_distance_km),
            "tabular_files_compared": len(compare_files),
            "all_tabular_files_byte_identical": bool(identity["Byte_identical"].all()),
        },
    }
    (OUT / "derived_results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
