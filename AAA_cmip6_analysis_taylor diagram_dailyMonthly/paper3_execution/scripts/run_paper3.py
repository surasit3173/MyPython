"""Execute the frozen Paper 3 ENSO/rainfall analysis end to end."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from paper3core.enso import (  # noqa: E402
    classify_management_seasons,
    episode_catalog,
    parse_noaa_oni_html,
)
from paper3core.hierarchy import grid_signatures  # noqa: E402
from paper3core.inference import infer_joint_phases  # noqa: E402
from paper3core.io import (  # noqa: E402
    climate_year_for_dates,
    common_365_index,
    discover_historical_files,
    load_daily,
    sha256_file,
    station_columns,
)
from paper3core.metrics import observed_percentile_thresholds, seasonal_metrics  # noqa: E402
from paper3core.qc import apply_zero_month_flags, diagnose_zero_months  # noqa: E402
from paper3core.qdm import crossfit_qdm  # noqa: E402
from paper3core.statistics import (  # noqa: E402
    benjamini_hochberg,
    classify_preservation,
    model_response,
    observed_response,
)


def _resolve_paths(config: dict) -> dict[str, Path]:
    return {
        key: (ROOT / value).resolve()
        for key, value in config["paths"].items()
    }


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


def _season_id(row: pd.Series) -> str:
    year = int(row["climate_year"])
    return f"{year}_RAIN" if row["season_type"] == "RAINY" else f"{year}_{str(year + 1)[-2:]}_HOT_DRY"


def prepare_enso(
    config: dict,
    paths: dict[str, Path],
    output: Path,
    climate_years: list[int],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    enso_config = config["enso"]
    observed_monthly = parse_noaa_oni_html(paths["observed_oni_html"])
    observed_monthly.to_csv(output / "observed_oni_monthly_frozen.csv", index=False)
    observed_index = observed_monthly.set_index("date")
    observed_catalog = episode_catalog(
        observed_index,
        source_name=enso_config["observed_version"],
        index_column="oni_c",
        threshold_c=enso_config["threshold_c"],
        persistence_seasons=enso_config["persistence_seasons"],
    )
    observed_catalog.to_csv(output / "enso_episode_catalog_observed.csv", index=False)
    observed_classes = classify_management_seasons(
        observed_index,
        climate_years=climate_years,
        index_column="oni_c",
    )
    observed_classes["model"] = "OBSERVED_ONI"
    observed_classes["index_source"] = enso_config["observed_version"]
    observed_classes["season_id"] = observed_classes.apply(_season_id, axis=1)
    observed_classes.to_csv(output / "season_classification_observed.csv", index=False)

    model_monthly = pd.read_csv(paths["model_nino34_csv"], parse_dates=["date"])
    model_classes = []
    model_catalogs = []
    for model, frame in model_monthly.groupby("model", sort=True):
        model_index = frame.set_index("date").sort_index()
        classes = classify_management_seasons(
            model_index,
            climate_years=climate_years,
            index_column="nino34_3month_c",
        )
        classes["model"] = model
        classes["member_id"] = str(frame["member_id"].iloc[0])
        classes["index_source"] = "model-specific CMIP6 historical tos Niño-3.4"
        classes["season_id"] = classes.apply(_season_id, axis=1)
        model_classes.append(classes)
        catalog = episode_catalog(
            model_index,
            source_name=f"{model} {frame['member_id'].iloc[0]} historical tos",
            index_column="nino34_3month_c",
            threshold_c=enso_config["threshold_c"],
            persistence_seasons=enso_config["persistence_seasons"],
        )
        catalog.insert(0, "model", model)
        catalog.insert(1, "member_id", str(frame["member_id"].iloc[0]))
        model_catalogs.append(catalog)
    model_classes_frame = pd.concat(model_classes, ignore_index=True)
    model_catalog_frame = pd.concat(model_catalogs, ignore_index=True)
    model_classes_frame.to_csv(output / "season_classification_models.csv", index=False)
    model_catalog_frame.to_csv(output / "enso_episode_catalog_models.csv", index=False)
    return observed_classes, model_classes_frame, observed_monthly


def _annotate_metrics(
    metrics: pd.DataFrame,
    *,
    source_type: str,
    model: str,
    signatures: dict[str, str],
    classification: pd.DataFrame,
) -> pd.DataFrame:
    output = metrics.copy()
    output.insert(0, "source_type", source_type)
    output.insert(1, "model", model)
    output.insert(3, "grid_signature", output["station"].map(signatures))
    merge_columns = [
        "season_type",
        "climate_year",
        "enso_phase",
        "index_mean_c",
        "index_min_c",
        "index_max_c",
        "n_overlapping_windows",
        "classification_rule",
    ]
    output = output.merge(
        classification[merge_columns],
        on=["season_type", "climate_year"],
        how="left",
        validate="many_to_one",
    )
    output["season_id"] = output.apply(_season_id, axis=1)
    return output


def rainfall_pipeline(
    config: dict,
    paths: dict[str, Path],
    output: Path,
    observed_classes: pd.DataFrame,
    model_classes: pd.DataFrame,
    climate_years: list[int],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[dict[str, object]]]:
    start_year, end_year = config["study"]["analysis_period"]
    stations = station_columns(paths["observed"])
    if len(stations) != config["study"]["station_count_expected"]:
        raise RuntimeError(f"expected 13 observed gauges, found {len(stations)}")
    observed_native, observed_report = load_daily(
        paths["observed"],
        stations=stations,
        start_year=start_year,
        end_year=end_year,
        drop_february_29=False,
    )
    qc_diagnostics = diagnose_zero_months(observed_native, config["observed_qc"])
    qc_diagnostics.to_csv(output / "observed_zero_qc_diagnostics.csv", index=False)
    observed_qc_native, changed = apply_zero_month_flags(
        observed_native,
        qc_diagnostics,
        classes=tuple(config["observed_qc"]["classes_set_to_missing"]),
    )
    qc_summary = (
        qc_diagnostics["classification"].value_counts().rename_axis("classification").reset_index(name="station_months")
    )
    qc_summary["daily_values_set_missing"] = 0
    qc_summary.loc[qc_summary["classification"] == "probable_missing", "daily_values_set_missing"] = changed
    qc_summary.to_csv(output / "observed_zero_qc_summary.csv", index=False)
    expected_common = common_365_index(start_year, end_year)
    observed = observed_qc_native.loc[
        ~(
            (observed_qc_native.index.month == 2)
            & (observed_qc_native.index.day == 29)
        )
    ].reindex(expected_common)
    observed.index.name = "date"
    observed_report["calendar_loaded_for_qc"] = "native_Gregorian"
    observed_report["calendar_used_for_analysis"] = "common_365"
    observed_report["leap_days_removed_after_qc"] = int(
        ((observed_native.index.month == 2) & (observed_native.index.day == 29)).sum()
    )
    observed.reset_index().to_csv(
        output / "observed_qc_common365.csv.gz", index=False, compression="gzip"
    )
    thresholds = observed_percentile_thresholds(
        observed,
        start_year=config["metrics"]["percentile_reference"][0],
        end_year=config["metrics"]["percentile_reference"][1],
        wet_threshold=config["metrics"]["wet_day_threshold_mm"],
    )
    _write_json(output / "observed_percentile_thresholds.json", thresholds)

    observed_metric = seasonal_metrics(
        observed,
        climate_years=climate_years,
        wet_threshold=config["metrics"]["wet_day_threshold_mm"],
        percentile_thresholds=thresholds,
    )
    all_metrics = [
        _annotate_metrics(
            observed_metric,
            source_type="OBSERVED",
            model="OBSERVED",
            signatures={station: f"gauge_{station}" for station in stations},
            classification=observed_classes,
        )
    ]

    qdm_diagnostics = []
    signature_rows = []
    provenance = [{"kind": "observed", **observed_report}]
    historical_files = discover_historical_files(paths["cmip6_raw"])
    if len(historical_files) != 7:
        raise RuntimeError(f"expected seven raw historical models, found {len(historical_files)}")
    climate_year = climate_year_for_dates(observed.index)
    qdm_dir = output / "crossfit_qdm_daily"
    qdm_dir.mkdir(exist_ok=True)

    for item in historical_files:
        raw, raw_report = load_daily(
            item.path,
            stations=stations,
            start_year=start_year,
            end_year=end_year,
        )
        raw_report.update(
            {
                "kind": "cmip6_raw",
                "model": item.model,
                "member_id": item.member_id,
                "grid_label": item.grid_label,
            }
        )
        provenance.append(raw_report)
        signatures = grid_signatures(raw)
        for station, signature in signatures.items():
            signature_rows.append(
                {
                    "model": item.model,
                    "member_id": item.member_id,
                    "grid_label": item.grid_label,
                    "station": station,
                    "grid_signature": signature,
                }
            )

        corrected = pd.DataFrame(index=raw.index, columns=stations, dtype=float)
        for station in stations:
            series, diagnostics = crossfit_qdm(
                observed[station],
                raw[station],
                climate_year=climate_year,
                blocks=[tuple(value) for value in config["bias_correction"]["climate_year_blocks"]],
                wet_threshold=config["bias_correction"]["wet_day_threshold_mm"],
                group_by_month=config["bias_correction"]["group_by_month"],
                min_wet_days=config["bias_correction"]["min_wet_days_per_month"],
                sparse_month_fallback=config["bias_correction"]["sparse_month_fallback"],
            )
            corrected[station] = series
            diagnostics.insert(0, "model", item.model)
            diagnostics.insert(1, "member_id", item.member_id)
            diagnostics.insert(2, "station", station)
            qdm_diagnostics.append(diagnostics)
        corrected.reset_index().to_csv(
            qdm_dir / f"qdm_crossfit_{item.model}_{item.member_id}_1981-2014.csv.gz",
            index=False,
            compression="gzip",
            float_format="%.6f",
        )

        class_table = model_classes[model_classes["model"] == item.model]
        raw_metric = seasonal_metrics(
            raw,
            climate_years=climate_years,
            wet_threshold=config["metrics"]["wet_day_threshold_mm"],
            percentile_thresholds=thresholds,
        )
        corrected_metric = seasonal_metrics(
            corrected,
            climate_years=climate_years,
            wet_threshold=config["metrics"]["wet_day_threshold_mm"],
            percentile_thresholds=thresholds,
        )
        all_metrics.append(
            _annotate_metrics(
                raw_metric,
                source_type="RAW",
                model=item.model,
                signatures=signatures,
                classification=class_table,
            )
        )
        all_metrics.append(
            _annotate_metrics(
                corrected_metric,
                source_type="QDM",
                model=item.model,
                signatures=signatures,
                classification=class_table,
            )
        )
        print(f"RAINFALL_DONE {item.model}", flush=True)

    signatures_frame = pd.DataFrame(signature_rows)
    signatures_frame.to_csv(output / "raw_grid_signatures.csv", index=False)
    qdm_frame = pd.concat(qdm_diagnostics, ignore_index=True)
    qdm_frame.to_csv(output / "crossfit_qdm_diagnostics.csv", index=False)
    metrics_frame = pd.concat(all_metrics, ignore_index=True)
    metrics_frame.to_csv(output / "seasonal_metrics_all.csv.gz", index=False, compression="gzip")
    return metrics_frame, qdm_frame, qc_summary, provenance


def response_analysis(
    config: dict,
    metrics: pd.DataFrame,
    output: Path,
    *,
    quick: bool,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    metric_names = config["metrics"]["primary"] + config["metrics"]["secondary"] + ["SDII"]
    metric_names = list(dict.fromkeys(metric_names))
    id_columns = [
        "source_type",
        "model",
        "station",
        "grid_signature",
        "season_type",
        "climate_year",
        "season_id",
        "enso_phase",
    ]
    long = metrics.melt(
        id_vars=id_columns,
        value_vars=metric_names,
        var_name="metric",
        value_name="value",
    )
    long.to_csv(output / "seasonal_metrics_long.csv.gz", index=False, compression="gzip")
    primary = set(config["metrics"]["primary"])
    minimum = config["enso"]["minimum_seasons_for_composite"]
    statistics_config = config["statistics"]
    bootstrap_repetitions = 199 if quick else statistics_config["bootstrap_repetitions"]
    permutation_repetitions = 199 if quick else statistics_config["permutation_repetitions"]
    base_seed = statistics_config["seed"]
    response_rows = []
    asymmetry_rows = []
    entity_rows = []
    model_rows_all = []
    grid_rows_all = []
    counter = 0

    for source_type in ("OBSERVED", "RAW", "QDM"):
        for season_type in ("RAINY", "HOT_DRY"):
            for metric in config["metrics"]["primary"]:
                subset = long[
                    (long["source_type"] == source_type)
                    & (long["season_type"] == season_type)
                    & (long["metric"] == metric)
                ].copy()
                result = infer_joint_phases(
                    subset,
                    source_kind="observed" if source_type == "OBSERVED" else "model",
                    minimum_seasons=minimum,
                    bootstrap_repetitions=bootstrap_repetitions,
                    permutation_repetitions=permutation_repetitions,
                    seed=base_seed + counter,
                    confidence_level=statistics_config["confidence_level"],
                )
                counter += 1
                for phase in ("EL_NINO", "LA_NINA"):
                    response_rows.append(
                        {
                            "source_type": source_type,
                            "season_type": season_type,
                            "metric": metric,
                            "phase": phase,
                            **result["responses"][phase],
                            "resampling_unit": result["resampling_unit"],
                            "bootstrap_repetitions": bootstrap_repetitions,
                            "permutation_repetitions": permutation_repetitions,
                        }
                    )
                    if source_type == "OBSERVED":
                        _, entities = observed_response(
                            subset,
                            phase=phase,
                            minimum_seasons=minimum,
                        )
                        entities.insert(0, "source_type", source_type)
                        entities.insert(1, "season_type", season_type)
                        entities.insert(2, "metric", metric)
                        entity_rows.append(entities)
                    else:
                        _, model_rows, grid_rows = model_response(
                            subset,
                            phase=phase,
                            minimum_seasons=minimum,
                        )
                        for frame in (model_rows, grid_rows):
                            frame.insert(0, "source_type", source_type)
                            frame.insert(1, "season_type", season_type)
                            frame.insert(2, "metric", metric)
                            if "phase" in frame:
                                frame["phase"] = phase
                            else:
                                frame.insert(3, "phase", phase)
                        model_rows_all.append(model_rows)
                        grid_rows_all.append(grid_rows)
                asymmetry_rows.append(
                    {
                        "source_type": source_type,
                        "season_type": season_type,
                        "metric": metric,
                        **result["asymmetry"],
                        "resampling_unit": result["resampling_unit"],
                        "bootstrap_repetitions": bootstrap_repetitions,
                        "permutation_repetitions": permutation_repetitions,
                    }
                )
                print(f"INFERENCE_DONE {source_type} {season_type} {metric}", flush=True)

    responses = pd.DataFrame(response_rows)
    responses["permutation_p_bh_primary"] = benjamini_hochberg(
        responses["permutation_p_pct"].to_numpy(dtype=float)
    )
    asymmetry = pd.DataFrame(asymmetry_rows)
    asymmetry["true_asymmetry_p_bh_primary"] = benjamini_hochberg(
        asymmetry["neutral_centered_asymmetry_pct_permutation_p"].to_numpy(dtype=float)
    )
    entity_frame = pd.concat(entity_rows, ignore_index=True)
    model_frame = pd.concat(model_rows_all, ignore_index=True)
    grid_frame = pd.concat(grid_rows_all, ignore_index=True)
    responses.to_csv(output / "primary_response_summary.csv", index=False)
    asymmetry.to_csv(output / "enso_asymmetry_primary.csv", index=False)
    entity_frame.to_csv(output / "observed_station_primary_responses.csv", index=False)
    model_frame.to_csv(output / "model_primary_responses.csv", index=False)
    grid_frame.to_csv(output / "grid_signature_primary_responses.csv", index=False)

    preservation_rows = []
    key_columns = ["season_type", "metric", "phase"]
    observed_response_table = responses[responses["source_type"] == "OBSERVED"].set_index(key_columns)
    raw_response_table = responses[responses["source_type"] == "RAW"].set_index(key_columns)
    qdm_response_table = responses[responses["source_type"] == "QDM"].set_index(key_columns)
    raw_models = model_frame[model_frame["source_type"] == "RAW"].set_index(key_columns + ["model"])
    qdm_models = model_frame[model_frame["source_type"] == "QDM"].set_index(key_columns + ["model"])
    for key in raw_response_table.index:
        raw_value = float(raw_response_table.loc[key, "response_pct"])
        qdm_value = float(qdm_response_table.loc[key, "response_pct"])
        observed_value = float(observed_response_table.loc[key, "response_pct"])
        classification = classify_preservation(
            raw_value,
            qdm_value,
            near_zero=config["preservation"]["near_zero_response_pct"],
            preserved_ratio=tuple(config["preservation"]["preserved_magnitude_ratio"]),
        )
        common_models = sorted(
            set(raw_models.loc[key].index).intersection(qdm_models.loc[key].index)
        )
        raw_signs = np.sign(raw_models.loc[key].loc[common_models, "response_pct"].to_numpy(float))
        qdm_signs = np.sign(qdm_models.loc[key].loc[common_models, "response_pct"].to_numpy(float))
        obs_sign = np.sign(observed_value)
        preservation_rows.append(
            {
                "season_type": key[0],
                "metric": key[1],
                "phase": key[2],
                "observed_response_pct": observed_value,
                "raw_response_pct": raw_value,
                "qdm_response_pct": qdm_value,
                "raw_absolute_error_vs_observed_pct_points": abs(raw_value - observed_value),
                "qdm_absolute_error_vs_observed_pct_points": abs(qdm_value - observed_value),
                "qdm_moved_toward_observed": bool(abs(qdm_value - observed_value) < abs(raw_value - observed_value)),
                "raw_model_direction_agreement_with_observed": float(np.mean(raw_signs == obs_sign)),
                "qdm_model_direction_agreement_with_observed": float(np.mean(qdm_signs == obs_sign)),
                "paired_model_sign_preservation_fraction": float(np.mean(raw_signs == qdm_signs)),
                "n_paired_models": len(common_models),
                **classification,
            }
        )
    preservation = pd.DataFrame(preservation_rows)
    preservation.to_csv(output / "qdm_enso_signal_preservation.csv", index=False)
    return responses, asymmetry, preservation, long


def build_audits(
    config: dict,
    paths: dict[str, Path],
    output: Path,
    metrics: pd.DataFrame,
    qdm_diagnostics: pd.DataFrame,
    responses: pd.DataFrame,
    asymmetry: pd.DataFrame,
    provenance: list[dict[str, object]],
    *,
    quick: bool,
) -> None:
    provenance_frame = pd.DataFrame(provenance)
    provenance_frame.to_csv(output / "rainfall_input_provenance.csv", index=False)
    phase_counts = (
        metrics[["source_type", "model", "season_type", "climate_year", "enso_phase"]]
        .drop_duplicates()
        .groupby(["source_type", "model", "season_type", "enso_phase"], as_index=False)
        .size()
        .rename(columns={"size": "n_seasons"})
    )
    phase_counts.to_csv(output / "enso_phase_sample_sizes.csv", index=False)

    allowed_phases = {"EL_NINO", "LA_NINA", "NEUTRAL", "TRANSITION_UNCLASSIFIED"}
    gates = [
        {
            "gate": "P3-A",
            "description": "Observed and model ENSO sources are frozen and traceable",
            "pass": bool(paths["observed_oni_html"].exists() and paths["model_nino34_manifest"].exists()),
        },
        {
            "gate": "P3-B",
            "description": "Only complete common-365 station-seasons enter metrics",
            "pass": bool(metrics["complete"].all() and (metrics["valid_days"] == metrics["expected_days"]).all()),
        },
        {
            "gate": "P3-C",
            "description": "All season ENSO labels use the frozen allowed vocabulary",
            "pass": bool(set(metrics["enso_phase"].dropna()).issubset(allowed_phases)),
        },
        {
            "gate": "P3-D",
            "description": "Common period contains 13 gauges and seven models",
            "pass": bool(metrics["station"].nunique() == 13 and metrics.loc[metrics["source_type"] == "RAW", "model"].nunique() == 7),
        },
        {
            "gate": "P3-E",
            "description": "Blocked cross-fitted QDM used no target observations",
            "pass": bool((qdm_diagnostics["n_target_observations_used"] == 0).all()),
        },
        {
            "gate": "P3-F",
            "description": "Both phase-vs-neutral primary responses exist",
            "pass": bool(len(responses) == 48 and responses["response_pct"].notna().all()),
        },
        {
            "gate": "P3-G",
            "description": "Phase contrast and true neutral-centred asymmetry are separated",
            "pass": bool(
                asymmetry["phase_contrast_pct"].notna().all()
                and asymmetry["neutral_centered_asymmetry_pct"].notna().all()
            ),
        },
        {
            "gate": "P3-H",
            "description": "Pre-specified event-level bootstrap and permutation inference completed",
            "pass": bool(
                (not quick)
                and (responses["bootstrap_repetitions"] == config["statistics"]["bootstrap_repetitions"]).all()
                and (responses["permutation_repetitions"] == config["statistics"]["permutation_repetitions"]).all()
            ),
        },
    ]
    gate_frame = pd.DataFrame(gates)
    gate_frame["status"] = np.where(gate_frame["pass"], "PASS", "FAIL")
    gate_frame.to_csv(output / "PAPER3_ACCEPTANCE_GATES.csv", index=False)

    manifest = {
        "config": str(ROOT / "config" / "paper3_enso.yaml"),
        "config_sha256": sha256_file(ROOT / "config" / "paper3_enso.yaml"),
        "analysis_mode": "quick_debug" if quick else "full_frozen",
        "observed_oni_sha256": sha256_file(paths["observed_oni_html"]),
        "model_nino34_manifest_sha256": sha256_file(paths["model_nino34_manifest"]),
        "hierarchy": "daily -> management season -> station -> unique raw-grid signature -> model -> ensemble",
        "resampling_unit": "management-season climate year; independently within model for model ensembles",
        "gates_passed": int(gate_frame["pass"].sum()),
        "gates_total": int(len(gate_frame)),
    }
    _write_json(output / "paper3_run_manifest.json", manifest)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(ROOT / "config" / "paper3_enso.yaml"))
    parser.add_argument("--quick", action="store_true", help="Use 199 bootstrap/permutation repetitions for debugging")
    args = parser.parse_args()
    config_path = Path(args.config).resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    paths = _resolve_paths(config)
    output = paths["output"]
    output.mkdir(parents=True, exist_ok=True)
    start_year, end_year = config["study"]["analysis_period"]
    climate_years = list(range(start_year, end_year + 1))

    observed_classes, model_classes, _ = prepare_enso(
        config, paths, output, climate_years
    )
    metrics, qdm_diagnostics, _, provenance = rainfall_pipeline(
        config,
        paths,
        output,
        observed_classes,
        model_classes,
        climate_years,
    )
    responses, asymmetry, _, _ = response_analysis(
        config, metrics, output, quick=args.quick
    )
    build_audits(
        config,
        paths,
        output,
        metrics,
        qdm_diagnostics,
        responses,
        asymmetry,
        provenance,
        quick=args.quick,
    )
    print(f"PAPER3_ANALYSIS_COMPLETE mode={'quick' if args.quick else 'full'} output={output}")


if __name__ == "__main__":
    main()
