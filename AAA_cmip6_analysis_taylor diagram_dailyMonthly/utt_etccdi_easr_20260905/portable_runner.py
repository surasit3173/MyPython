#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Configuration-driven runner for the ETCCDI MK/MMK/Sen/IDW pipeline.

The supplied research script is retained as the scientific core.  This
runner makes the input paths, province name, station set, models, scenarios,
periods and thresholds explicit in a small JSON file, so the same validated
implementation can be used for another province without editing the analysis
algorithm.  It intentionally uses explicit CMIP6 file matching and fails
closed when a file is missing or ambiguous.

Typical commands::

    python portable_runner.py --config config_uttaradit.json \
        --input C:/dataUttaradit --output output_uttar   
    python portable_runner.py --config config_template.json \
        --input C:/dataOtherProvince --output output_other --validate-only

The input directory is expected to contain an observed daily CSV, a station
coordinate workbook, optional boundary shapefile components, and bias-
corrected CMIP6 daily CSVs.  The observed and CMIP6 files must contain
YEAR, MONTH, DAY and one column per station.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
CORE_PATH = ROOT / "Uttaradit_ETCCDI_MK_MMK2004_Sen_IDW_Q3_fixed.py"
DEFAULT_CONFIG = ROOT / "config_template.json"


def load_core():
    """Import the scientific core from the same extracted package."""
    if not CORE_PATH.is_file():
        raise FileNotFoundError(f"Scientific core is missing: {CORE_PATH}")
    spec = importlib.util.spec_from_file_location("etccdi_scientific_core", CORE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not import scientific core: {CORE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON configuration: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("Configuration root must be a JSON object.")
    return value


def _required(mapping: Mapping[str, Any], key: str, context: str) -> Any:
    if key not in mapping or mapping[key] in (None, ""):
        raise ValueError(f"Missing required configuration key: {context}.{key}")
    return mapping[key]


def normalise_station(value: Any) -> str:
    text = str(value).strip()
    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    return text


def resolve_input_path(input_root: Path, value: str, *, required: bool = True) -> Optional[Path]:
    """Resolve a relative path or a single glob under ``input_root``."""
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = input_root / candidate
    if any(char in str(candidate) for char in "*?["):
        matches = sorted(candidate.parent.glob(candidate.name))
        if len(matches) > 1:
            raise ValueError(f"Path pattern is ambiguous ({len(matches)} matches): {value}")
        candidate = matches[0] if matches else candidate
    candidate = candidate.resolve()
    if required and not candidate.is_file():
        raise FileNotFoundError(f"Configured input file not found: {candidate}")
    return candidate if candidate.is_file() else None


def resolve_input_dir(input_root: Path, value: str) -> Optional[Path]:
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = input_root / candidate
    candidate = candidate.resolve()
    if candidate.is_dir():
        return candidate
    if value in ("", "."):
        return input_root
    raise NotADirectoryError(f"Configured CMIP6 directory not found: {candidate}")


def configure_core(core, cfg: Mapping[str, Any], station_ids: Sequence[str]) -> None:
    """Apply user configuration to the core's explicitly named globals."""
    periods = cfg["periods"]
    scenarios = cfg["scenarios"]
    models = [str(item) for item in cfg["models"]]
    settings = dict(cfg.get("settings", {}))
    defaults = asdict(core.AnalysisConfig())
    unknown = sorted(set(settings) - set(defaults))
    if unknown:
        raise ValueError(f"Unknown settings in configuration: {unknown}")
    values = {key: settings.get(key, default) for key, default in defaults.items()}
    values.update(
        {
            "obs_start": int(periods["observed_start"]),
            "obs_end": int(periods["observed_end"]),
            "baseline_start": int(periods["baseline_start"]),
            "baseline_end": int(periods["baseline_end"]),
            "future_start": int(periods["future_start"]),
            "future_end": int(periods["future_end"]),
        }
    )
    core.CONFIG = core.AnalysisConfig(**values)
    core.VERSION = "2.1.0-portable"
    core.EXPECTED_MODELS = models
    core.EXPECTED_STATIONS = set(station_ids)
    core.SCENARIOS = {str(k): str(v) for k, v in scenarios.items()}

    # The core exposes these aliases for speed and for backwards-compatible
    # helper functions.  Keep them synchronized with AnalysisConfig.
    core.ALPHA = core.CONFIG.alpha
    core.MIN_YEARS = core.CONFIG.min_trend_n
    core.MIN_ANNUAL_COMPLETENESS = core.CONFIG.annual_completeness
    core.OBS_START, core.OBS_END = core.CONFIG.obs_start, core.CONFIG.obs_end
    core.BASELINE_START, core.BASELINE_END = core.CONFIG.baseline_start, core.CONFIG.baseline_end
    core.FUTURE_START, core.FUTURE_END = core.CONFIG.future_start, core.CONFIG.future_end
    core.WET_THRESHOLD = core.CONFIG.wet_day_threshold_mm
    core.R10_THRESHOLD = core.CONFIG.r10_threshold_mm
    core.R20_THRESHOLD = core.CONFIG.r20_threshold_mm
    core.R50_THRESHOLD = core.CONFIG.r50_threshold_mm
    core.P95, core.P99 = core.CONFIG.p95, core.CONFIG.p99

    # A few scientific helpers have defaults bound at import time.  Rebind
    # those defaults explicitly so a non-default alpha is not silently ignored.
    old_trend_label = core.trend_label
    old_sen_ci = core.sen_confidence_interval
    core.trend_label = lambda z, p, alpha=core.ALPHA: old_trend_label(z, p, alpha)
    core.sen_confidence_interval = lambda years, values, alpha=core.ALPHA: old_sen_ci(years, values, alpha)


def load_boundary_parts(core, path: Optional[Path], filter_config: Any, encoding: str = "utf-8") -> Optional[list[np.ndarray]]:
    """Read all polygon rings, optionally selecting records by DBF fields.

    The original Uttaradit reader intentionally selects PROV_CODE=53.  A
    portable runner must not assume that code or name for another province,
    so the filter is configured in JSON.  With no filter, all polygon records
    are used as a union, which is appropriate for a one-province shapefile.
    """
    if path is None:
        return None
    import shapefile

    reader = shapefile.Reader(str(path), encoding=encoding, encodingErrors="replace")
    records = []
    for shape_record in reader.iterShapeRecords():
        record = shape_record.record.as_dict()
        if filter_config:
            rules = filter_config if isinstance(filter_config, list) else [filter_config]
            matches = False
            for rule in rules:
                if not isinstance(rule, dict):
                    raise ValueError("boundary_filter entries must be objects")
                field = str(_required(rule, "field", "boundary_filter"))
                expected = str(_required(rule, "value", "boundary_filter"))
                actual = next((value for key, value in record.items() if str(key).upper() == field.upper()), None)
                if str(actual).strip().upper() == expected.strip().upper():
                    matches = True
                    break
            if not matches:
                continue
        records.append(shape_record.shape)
    if not records:
        raise ValueError(f"No polygon record matched boundary_filter in {path}")
    parts: list[np.ndarray] = []
    for shape in records:
        points = np.asarray(shape.points, dtype=float)
        starts = list(shape.parts) + [len(points)]
        for start, end in zip(starts[:-1], starts[1:]):
            ring = points[start:end, :2]
            if len(ring) >= 3 and np.isfinite(ring).all():
                parts.append(ring)
    if not parts:
        raise ValueError(f"Boundary shapefile has no valid polygon rings: {path}")
    return parts


def discover_model_files(core, input_root: Path, cfg: Mapping[str, Any]) -> Dict[Tuple[str, str], Path]:
    """Resolve configured CMIP6 files or fail-closed auto-discovery."""
    cmip6 = dict(cfg.get("cmip6", {}))
    explicit = cmip6.get("files")
    models = [str(item) for item in cfg["models"]]
    periods = ["historical", *cfg["scenarios"].keys()]
    found: Dict[Tuple[str, str], Path] = {}

    if explicit is not None:
        if not isinstance(explicit, dict):
            raise ValueError("cmip6.files must be an object keyed by model")
        for model in models:
            if model not in explicit:
                raise ValueError(f"cmip6.files is missing model {model}")
            model_map = explicit[model]
            for period in periods:
                if period not in model_map:
                    raise ValueError(f"cmip6.files is missing {model}/{period}")
                found[(model, period)] = resolve_input_path(input_root, str(model_map[period]))  # type: ignore[assignment]
        return found

    search_root = resolve_input_dir(input_root, str(cmip6.get("directory", ".")))
    if search_root is None:
        search_root = input_root
    candidates = sorted(search_root.rglob("*.csv"))
    for model in models:
        for period in periods:
            token = period.lower()
            matches = [
                path for path in candidates
                if path.stem.lower().startswith("bc_")
                and model.lower() in path.stem.lower()
                and token in path.stem.lower()
            ]
            if len(matches) != 1:
                names = [str(item) for item in matches]
                raise ValueError(
                    f"CMIP6 auto-discovery expected exactly one file for {model}/{period}, "
                    f"found {len(matches)}: {names}"
                )
            found[(model, period)] = matches[0]
    return found


def station_ids_from_inputs(core, observed: pd.DataFrame, coords: pd.DataFrame) -> list[str]:
    observed_ids = {normalise_station(c) for c in observed.columns}
    coord_ids = {normalise_station(c) for c in coords["station"]}
    missing = sorted(coord_ids - observed_ids)
    unexpected = sorted(observed_ids - coord_ids)
    if missing or unexpected:
        raise ValueError(
            "Observed and coordinate station sets do not match; "
            f"missing_from_observed={missing}, unexpected_in_observed={unexpected}"
        )
    if len(observed_ids) < 3:
        raise ValueError("At least three common stations are required for IDW visualization.")
    return sorted(observed_ids)


def filter_coordinates(coords: pd.DataFrame, input_cfg: Mapping[str, Any]) -> pd.DataFrame:
    """Restrict a shared coordinate workbook to the study-area stations."""
    requested = input_cfg.get("station_ids")
    prefix = input_cfg.get("station_prefix")
    if requested is None and prefix in (None, ""):
        return coords
    ids = coords["station"].map(normalise_station)
    if requested is not None:
        if not isinstance(requested, list) or not requested:
            raise ValueError("input.station_ids must be a non-empty list")
        wanted = {normalise_station(value) for value in requested}
        missing = sorted(wanted - set(ids))
        if missing:
            raise ValueError(f"Configured station_ids are absent from coordinates: {missing}")
        mask = ids.isin(wanted)
    else:
        mask = ids.str.startswith(str(prefix))
        if not mask.any():
            raise ValueError(f"No coordinate station matches input.station_prefix={prefix!r}")
    filtered = coords.loc[mask].copy().reset_index(drop=True)
    if filtered.empty:
        raise ValueError("Station filter selected zero coordinate rows")
    return filtered


def period_labels(cfg: Mapping[str, Any]) -> Tuple[str, str, str]:
    p = cfg["periods"]
    return (
        f"{int(p['observed_start'])}-{int(p['observed_end'])}",
        f"{int(p['baseline_start'])}-{int(p['baseline_end'])}",
        f"{int(p['future_start'])}-{int(p['future_end'])}",
    )


def write_validation_report(path: Path, cfg: Mapping[str, Any], station_ids: Sequence[str], files: Mapping[Tuple[str, str], Path]) -> None:
    obs_label, base_label, future_label = period_labels(cfg)
    lines = [
        f"# Portable ETCCDI validation: {cfg['province_name']}",
        "",
        "Validation completed without running annual indices.",
        "",
        f"- Stations: {len(station_ids)} ({', '.join(station_ids)})",
        f"- Observed period: {obs_label}",
        f"- Baseline period: {base_label}",
        f"- Future period: {future_label}",
        f"- CMIP6 files: {len(files)}",
        "- Status: PASS",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_analysis(cfg: Mapping[str, Any], input_root: Path, output_root: Path, *, no_figures: bool = False, validate_only: bool = False) -> int:
    core = load_core()
    input_root = input_root.expanduser().resolve()
    output_root = output_root.expanduser().resolve()
    if not input_root.is_dir():
        raise NotADirectoryError(f"Input directory not found: {input_root}")

    input_cfg = cfg.get("input", {})
    obs_path = resolve_input_path(input_root, str(_required(input_cfg, "observed_file", "input")))
    coord_path = resolve_input_path(input_root, str(_required(input_cfg, "coordinates_file", "input")))
    boundary_value = input_cfg.get("boundary_file")
    boundary_path = resolve_input_path(input_root, str(boundary_value), required=True) if boundary_value else None

    observed_raw = core.load_daily_csv(obs_path)
    coords = filter_coordinates(core.read_coordinates(coord_path), input_cfg)
    station_ids = station_ids_from_inputs(core, observed_raw, coords)
    configure_core(core, cfg, station_ids)
    cmip6_files = discover_model_files(core, input_root, cfg)
    expected_keys = {(model, period) for model in cfg["models"] for period in ("historical", *cfg["scenarios"].keys())}
    if set(cmip6_files) != expected_keys:
        raise ValueError("CMIP6 manifest does not match configured models/scenarios")

    obs_label, base_label, future_label = period_labels(cfg)
    result_dir = output_root / "results"
    figure_dir = output_root / "figures"
    result_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)
    core.EXECUTION_LOG.clear()
    core.log("=" * 78)
    core.log(f"{cfg['province_name']} portable ETCCDI analysis v{core.VERSION}")
    core.log(f"Observed: {obs_label} | Baseline: {base_label} | Future: {future_label}")
    core.log(f"Stations: {len(station_ids)} | Models: {len(cfg['models'])} | Scenarios: {len(cfg['scenarios'])}")

    core._require_period_endpoints(observed_raw, core.OBS_START, core.OBS_END, "Observed rainfall")
    observed_raw = core.select_station_columns(observed_raw, station_ids)
    observed, observed_profile = core.qc_daily(observed_raw, f"{core.OBS_START}-01-01", f"{core.OBS_END}-12-31")
    core._require_period_endpoints(observed, core.OBS_START, core.OBS_END, "Observed rainfall")
    thresholds = core.station_thresholds_from_observed(observed)
    threshold_df = core.thresholds_table(thresholds)
    core._validate_thresholds(threshold_df)
    manifest = core.build_cmip6_manifest(cmip6_files)
    manifest.to_csv(result_dir / "cmip6_file_manifest.csv", index=False)
    coords.to_csv(result_dir / "station_coordinates_used.csv", index=False)
    threshold_df.to_csv(result_dir / "station_thresholds.csv", index=False)

    observed_indices, observed_annual_qc = core.annual_extreme_indices(observed, thresholds, return_qc=True)
    observed_annual_qc.insert(0, "Dataset", "Observed")
    observed_qc = pd.concat([observed_annual_qc, observed_profile.assign(Dataset="Observed_profile")], ignore_index=True, sort=False)
    observed_qc.to_csv(result_dir / "qc_observed.csv", index=False)

    metadata = core.build_metadata(input_root, output_root)
    metadata.update({
        "province_name": cfg["province_name"],
        "observed_period": obs_label,
        "baseline_period": base_label,
        "future_period": future_label,
        "coordinate_file": str(coord_path),
        "observed_file": str(obs_path),
        "boundary_file_for_maps": str(boundary_path) if boundary_path else None,
        "station_count": len(station_ids),
    })

    if validate_only:
        write_validation_report(result_dir / "VALIDATION_REPORT.md", cfg, station_ids, cmip6_files)
        metadata["run_mode"] = "validate_only"
        (result_dir / "analysis_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
        core.log("VALIDATION PASSED")
        (result_dir / "execution_log.txt").write_text("\n".join(core.EXECUTION_LOG), encoding="utf-8")
        return 0

    observed_trend = core.analyze_index_dataframe(observed_indices, obs_label, model="Observed", scenario="Historical")
    observed_indices_long = core.indices_to_long(observed_indices, obs_label, "Observed", "Historical")
    future_trend_parts: list[pd.DataFrame] = []
    future_change_parts: list[pd.DataFrame] = []
    future_index_parts: list[pd.DataFrame] = []
    model_qc_parts: list[pd.DataFrame] = []

    for model in cfg["models"]:
        historical_raw = core.select_station_columns(core.load_daily_csv(cmip6_files[(model, "historical")]), station_ids)
        core._require_period_endpoints(historical_raw, core.OBS_START, core.OBS_END, f"{model} historical")
        historical, _ = core.qc_daily(historical_raw, f"{core.OBS_START}-01-01", f"{core.OBS_END}-12-31")
        historical_indices, historical_qc = core.annual_extreme_indices(historical, thresholds, return_qc=True)
        historical_qc.insert(0, "Dataset", "Historical")
        historical_qc.insert(1, "Model", model)
        historical_qc.insert(2, "Scenario", "Historical")
        model_qc_parts.append(historical_qc)

        for scenario_key, scenario_label in core.SCENARIOS.items():
            future_raw = core.select_station_columns(core.load_daily_csv(cmip6_files[(model, scenario_key)]), station_ids)
            core._require_period_endpoints(future_raw, core.FUTURE_START, core.FUTURE_END, f"{model} {scenario_label}")
            future, _ = core.qc_daily(future_raw, f"{core.FUTURE_START}-01-01", f"{core.FUTURE_END}-12-31")
            future_indices, future_qc = core.annual_extreme_indices(future, thresholds, return_qc=True)
            future_qc.insert(0, "Dataset", "Future")
            future_qc.insert(1, "Model", model)
            future_qc.insert(2, "Scenario", scenario_label)
            model_qc_parts.append(future_qc)
            future_trend_parts.append(core.analyze_index_dataframe(future_indices, future_label, model=model, scenario=scenario_label))
            future_change_parts.append(core.future_change_table(future_indices, historical_indices, model, scenario_label))
            future_index_parts.append(core.indices_to_long(future_indices, future_label, model, scenario_label))

    future_trend = pd.concat(future_trend_parts, ignore_index=True)
    change_df = pd.concat(future_change_parts, ignore_index=True)
    future_indices_long = pd.concat(future_index_parts, ignore_index=True)
    qc_models = pd.concat(model_qc_parts, ignore_index=True)
    agreement = core.model_agreement_summary(future_trend)
    summary_by_index = core.build_summary(observed_trend, future_trend, change_df)
    summary_by_index["Period"] = summary_by_index["Period"].replace({
        "1981-2014": obs_label,
        "2021-2050": future_label,
        "2021-2050 change": f"{future_label} change",
    })
    summary_by_model_scenario = future_trend.groupby(["Model", "Scenario", "Index"], as_index=False).agg(
        n_stations=("Station", "nunique"),
        median_sen_slope=("Sen_slope", "median"),
        median_mmk_z=("Z_MMK2004", "median"),
        median_mmk_p_descriptive_only=("p_MMK2004", "median"),
    )
    core.validate_result_tables(observed_trend, future_trend, change_df, station_ids)

    outputs = {
        "observed_indices.csv": observed_indices_long,
        "observed_trend.csv": observed_trend,
        "future_indices.csv": future_indices_long,
        "future_trend.csv": future_trend,
        "future_change.csv": change_df,
        "qc_models.csv": qc_models,
        "summary_by_index.csv": summary_by_index,
        "summary_by_model_scenario.csv": summary_by_model_scenario,
        "future_model_agreement.csv": agreement,
    }
    for filename, frame in outputs.items():
        frame.to_csv(result_dir / filename, index=False)
    metadata.update({
        "run_mode": "full_analysis",
        "observed_trend_rows": int(len(observed_trend)),
        "future_trend_rows": int(len(future_trend)),
        "future_change_rows": int(len(change_df)),
    })
    (result_dir / "analysis_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    core.write_excel_v2(
        result_dir / f"{cfg['province_name']}_Trend_Analysis.xlsx",
        metadata, coords, threshold_df, observed_indices_long, observed_trend,
        future_indices_long, future_trend, change_df, agreement, observed_qc,
        qc_models, manifest,
    )

    if not no_figures:
        core.setup_publication_style()
        boundary_parts = load_boundary_parts(
            core,
            boundary_path,
            input_cfg.get("boundary_filter"),
            str(input_cfg.get("boundary_encoding", "utf-8")),
        )
        for index_name in core.INDICES:
            core.plot_observed_trend_map(
                observed_trend, coords, index_name,
                figure_dir / f"observed_trend_{obs_label}_{index_name}.png",
                boundary_parts=boundary_parts,
            )
        for scenario_key in core.SCENARIOS:
            for index_name in core.INDICES:
                core.plot_future_idw_change(
                    change_df, coords, index_name, scenario_key,
                    figure_dir / f"future_change_IDW_{future_label}_{scenario_key}_{index_name}.png",
                    power=core.CONFIG.idw_power,
                    boundary_parts=boundary_parts,
                )

    readme = [
        f"{cfg['province_name']} ETCCDI trend analysis v{core.VERSION}",
        f"Observed period: {obs_label}.",
        f"Future trend period: {future_label}.",
        f"Future-change baseline: model-consistent {base_label}.",
        "Methods: standard MK, Yue-Wang 2004 detrended effective-sample-size MMK, and Sen slope with 95% CI.",
        "R95p/R99p use observed station-specific fixed wet-day thresholds.",
        "IDW is a station-referenced visualization of model-median change, not dynamical downscaling.",
    ]
    (result_dir / "README_results.txt").write_text("\n".join(readme) + "\n", encoding="utf-8")
    required = [
        "observed_indices.csv", "observed_trend.csv", "future_indices.csv", "future_trend.csv",
        "future_change.csv", "station_coordinates_used.csv", "station_thresholds.csv", "qc_observed.csv",
        "qc_models.csv", "cmip6_file_manifest.csv", "summary_by_index.csv", "summary_by_model_scenario.csv",
        "future_model_agreement.csv", f"{cfg['province_name']}_Trend_Analysis.xlsx", "analysis_metadata.json",
        "README_results.txt",
    ]
    missing = [name for name in required if not (result_dir / name).exists()]
    if missing:
        raise RuntimeError(f"Required outputs are missing: {missing}")
    core.log("SUCCESS")
    (result_dir / "execution_log.txt").write_text("\n".join(core.EXECUTION_LOG), encoding="utf-8")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Portable ETCCDI MK/MMK/Sen/IDW runner")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="JSON configuration file")
    parser.add_argument("--input", required=True, help="Input data directory")
    parser.add_argument("--output", default="output_portable", help="Output directory")
    parser.add_argument("--no-figures", action="store_true", help="Skip map generation")
    parser.add_argument("--validate-only", action="store_true", help="Validate inputs and manifest only")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    config_path = Path(args.config).expanduser().resolve()
    cfg = load_json(config_path)
    _required(cfg, "province_name", "root")
    for key in ("models", "scenarios", "periods", "input"):
        _required(cfg, key, "root")
    if not isinstance(cfg["models"], list) or not cfg["models"]:
        raise ValueError("models must be a non-empty list")
    if not isinstance(cfg["scenarios"], dict) or not cfg["scenarios"]:
        raise ValueError("scenarios must be a non-empty object")
    return run_analysis(
        cfg,
        Path(args.input),
        Path(args.output),
        no_figures=args.no_figures,
        validate_only=args.validate_only,
    )


if __name__ == "__main__":
    raise SystemExit(main())
