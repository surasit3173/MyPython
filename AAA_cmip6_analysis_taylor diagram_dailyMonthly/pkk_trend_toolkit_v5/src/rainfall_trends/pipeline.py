"""Immutable production pipeline orchestration."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sys
import tempfile
from typing import Callable

import numpy as np
import pandas as pd

from .aggregation import build_period_totals
from .bootstrap import residual_block_bootstrap_sen
from .config import AnalysisConfig
from .io import load_rainfall, load_station_metadata, validate_station_keys
from .simulation import simulate_complete_null_fdr, simulate_method_performance
from .statistics import StatisticsError, bh_adjust, hamed_rao, mann_kendall, pw_mk, tfpw_mk


class PipelineError(RuntimeError):
    """Raised when an analysis run cannot be created or verified."""


def build_run_id(area_name: str, config_path: str | Path, input_paths: list[str | Path]) -> str:
    digest = hashlib.sha256()
    for path in [Path(config_path), *[Path(item) for item in input_paths]]:
        if not path.is_file():
            raise PipelineError(f"Fingerprint input does not exist: {path}")
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    digest.update(b"rainfall-trends-v5.0.0")
    slug = re.sub(r"[^a-z0-9]+", "-", area_name.lower()).strip("-") or "analysis"
    return f"{slug}_{digest.hexdigest()[:12]}"


def apply_bh_families(results: pd.DataFrame, *, alpha: float, network: bool = False) -> pd.DataFrame:
    required = {"period", "method", "p_value"}
    if not required.issubset(results.columns):
        raise PipelineError(f"Results are missing BH fields: {sorted(required - set(results.columns))}")
    output = results.copy()
    output["q_value"] = np.nan
    output["reject_bh"] = False
    output["family"] = ""
    group_fields: str | list[str] = "method" if network else ["period", "method"]
    for key, index in output.groupby(group_fields, sort=False, dropna=False).groups.items():
        key_tuple = key if isinstance(key, tuple) else (key,)
        family = "network|" + str(key_tuple[0]) if network else "station|" + "|".join(map(str, key_tuple))
        q_values, rejected = bh_adjust(output.loc[index, "p_value"].to_numpy(), alpha=alpha)
        output.loc[index, "q_value"] = q_values
        output.loc[index, "reject_bh"] = rejected
        output.loc[index, "family"] = family
    return output


def validate_existing_run(run_dir: str | Path) -> None:
    directory = Path(run_dir)
    manifest_path = directory / "run_manifest.json"
    if not manifest_path.is_file():
        raise PipelineError(f"Existing run has no manifest: {directory}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PipelineError(f"Cannot read existing run manifest: {exc}") from exc
    for relative, record in manifest.get("outputs", {}).items():
        target = directory / relative
        if not target.is_file():
            raise PipelineError(f"Existing run output is missing: {relative}")
        actual = _sha256(target)
        if actual != record.get("sha256"):
            raise PipelineError(f"Existing run output hash mismatch: {relative}")


def run_analysis(config_path: str | Path, output_root: str | Path) -> Path:
    config_file = Path(config_path).resolve()
    config = AnalysisConfig.load(config_file)
    rainfall_path, metadata_path = config.resolved_paths(config_file)
    run_id = build_run_id(config.area_name, config_file, [rainfall_path, metadata_path])
    runs_root = Path(output_root).resolve() / "runs"
    run_dir = runs_root / run_id
    if run_dir.exists():
        validate_existing_run(run_dir)
        return run_dir
    runs_root.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{run_id}_", dir=runs_root))
    try:
        observations = load_rainfall(
            rainfall_path,
            layout=config.input_layout,
            date_columns=config.date_columns,
            date_column=config.date_column,
            station_column=config.station_column,
            value_column=config.value_column,
        )
        metadata = load_station_metadata(
            metadata_path,
            station_column=config.metadata_station_column,
            latitude_column=config.latitude_column,
            longitude_column=config.longitude_column,
            elevation_column=config.elevation_column,
        )
        validate_station_keys(observations, metadata)
        totals = build_period_totals(
            observations,
            wet_months=config.wet_months,
            dry_months=config.dry_months,
            completeness_threshold=config.completeness_threshold,
        )
        station_results = apply_bh_families(
            _station_trends(totals, config), alpha=config.alpha, network=False
        )
        network_series = _network_series(totals, len(metadata))
        network_results = apply_bh_families(
            _network_trends(network_series, config), alpha=config.alpha, network=True
        )
        bootstrap = _bootstrap_rows(totals, network_series, config)
        method_simulation = simulate_method_performance(
            n=int(network_series.groupby("period").size().min()),
            reps=config.monte_carlo_reps,
            phi_levels=config.phi_levels,
            standardized_slopes=config.standardized_slopes,
            alpha=config.alpha,
            max_lag=config.hr_max_lag,
            acf_alpha=config.acf_alpha,
            seed=config.seed + 100_000,
        )
        fdr_simulation = simulate_complete_null_fdr(
            n=int(network_series.groupby("period").size().min()),
            reps=config.fdr_reps,
            stations=len(metadata),
            phi=config.fdr_phi,
            spatial_rho=config.fdr_spatial_rho,
            alpha=config.alpha,
            max_lag=config.hr_max_lag,
            acf_alpha=config.acf_alpha,
            seed=config.seed + 200_000,
        )
        quality = _quality_summary(observations, metadata, totals)

        tables = temporary / "tables"
        figures = temporary / "figures"
        tables.mkdir()
        figures.mkdir()
        _write_csv(metadata, tables / "station_metadata.csv")
        _write_csv(quality, tables / "data_quality.csv")
        _write_csv(totals, tables / "period_totals.csv")
        _write_csv(network_series, tables / "network_series.csv")
        _write_csv(station_results, tables / "station_results.csv")
        _write_csv(network_results, tables / "network_results.csv")
        _write_csv(bootstrap, tables / "bootstrap_ci.csv")
        _write_csv(method_simulation, tables / "method_simulation.csv")
        _write_csv(fdr_simulation, tables / "fdr_simulation.csv")

        matplotlib_cache = Path(output_root).resolve() / ".matplotlib_cache"
        matplotlib_cache.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("MPLCONFIGDIR", str(matplotlib_cache))
        from .plots import create_all_figures

        create_all_figures(
            figures,
            metadata=metadata,
            network_series=network_series,
            network_results=network_results,
            station_results=station_results,
            bootstrap=bootstrap,
            method_simulation=method_simulation,
            fdr_simulation=fdr_simulation,
            alpha=config.alpha,
        )
        manifest = _build_manifest(
            temporary,
            run_id=run_id,
            config=config,
            config_file=config_file,
            rainfall_path=rainfall_path,
            metadata_path=metadata_path,
            observations=observations,
            metadata=metadata,
            totals=totals,
        )
        (temporary / "run_manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        temporary.rename(run_dir)
        return run_dir
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def _trend_methods(config: AnalysisConfig) -> list[tuple[str, Callable]]:
    return [
        ("MK", mann_kendall),
        (f"HR-MMK-{config.hr_max_lag}", lambda y, t: hamed_rao(y, t, max_lag=config.hr_max_lag, acf_alpha=config.acf_alpha)),
        ("PW-MK", pw_mk),
        ("TFPW-MK", tfpw_mk),
    ]


def _trend_record(scope: str, key: str, period: str, values: np.ndarray, years: np.ndarray, config: AnalysisConfig) -> list[dict]:
    rows: list[dict] = []
    for method_name, function in _trend_methods(config):
        try:
            result = function(values, years)
            record = asdict(result)
            record["significant_lags"] = ";".join(map(str, result.significant_lags))
            status = "ok"
        except StatisticsError as exc:
            record = {
                "method": method_name,
                "n": len(values),
                "s": np.nan,
                "tau": np.nan,
                "slope": np.nan,
                "intercept": np.nan,
                "z": np.nan,
                "p_value": np.nan,
                "phi1": np.nan,
                "var_s": np.nan,
                "adjusted_var_s": np.nan,
                "correction_factor": np.nan,
                "significant_lags": "",
            }
            status = f"undefined: {exc}"
        rows.append({"scope": scope, "key": key, "period": period, **record, "status": status})
    return rows


def _station_trends(totals: pd.DataFrame, config: AnalysisConfig) -> pd.DataFrame:
    eligible = totals[totals["included"]].copy()
    rows: list[dict] = []
    for (station, period), group in eligible.groupby(["station_id", "period"], sort=True):
        ordered = group.sort_values("year")
        rows.extend(
            _trend_record(
                "station", str(station), str(period), ordered["total_mm"].to_numpy(), ordered["year"].to_numpy(), config
            )
        )
    output = pd.DataFrame(rows).rename(columns={"key": "station_id"})
    return output


def _network_series(totals: pd.DataFrame, station_count: int) -> pd.DataFrame:
    eligible = totals[totals["included"]].copy()
    grouped = (
        eligible.groupby(["period", "year"], sort=True, observed=True)
        .agg(network_mean_mm=("total_mm", "mean"), stations_included=("station_id", "nunique"))
        .reset_index()
    )
    return grouped[grouped["stations_included"] == station_count].reset_index(drop=True)


def _network_trends(network_series: pd.DataFrame, config: AnalysisConfig) -> pd.DataFrame:
    rows: list[dict] = []
    for period, group in network_series.groupby("period", sort=True):
        ordered = group.sort_values("year")
        rows.extend(
            _trend_record(
                "network", "equal_station_mean", str(period), ordered["network_mean_mm"].to_numpy(), ordered["year"].to_numpy(), config
            )
        )
    return pd.DataFrame(rows).drop(columns="key")


def _stable_seed(base: int, *parts: str) -> int:
    token = "|".join(parts).encode("utf-8")
    return int((base + int(hashlib.sha256(token).hexdigest()[:8], 16)) % (2**32 - 1))


def _bootstrap_rows(totals: pd.DataFrame, network_series: pd.DataFrame, config: AnalysisConfig) -> pd.DataFrame:
    rows: list[dict] = []
    eligible = totals[totals["included"]]
    for (station, period), group in eligible.groupby(["station_id", "period"], sort=True):
        ordered = group.sort_values("year")
        seed = _stable_seed(config.seed, "station", str(station), str(period))
        result = residual_block_bootstrap_sen(
            ordered["total_mm"].to_numpy(),
            ordered["year"].to_numpy(),
            reps=config.bootstrap_reps,
            block_length=min(config.bootstrap_block_length, len(ordered)),
            seed=seed,
            alpha=config.alpha,
        )
        rows.append({"scope": "station", "key": str(station), "period": period, "estimate": result.estimate, "ci_low": result.ci_low, "ci_high": result.ci_high, "reps": result.reps, "block_length": result.block_length, "seed": seed})
    for period, group in network_series.groupby("period", sort=True):
        ordered = group.sort_values("year")
        seed = _stable_seed(config.seed, "network", str(period))
        result = residual_block_bootstrap_sen(
            ordered["network_mean_mm"].to_numpy(),
            ordered["year"].to_numpy(),
            reps=config.bootstrap_reps,
            block_length=min(config.bootstrap_block_length, len(ordered)),
            seed=seed,
            alpha=config.alpha,
        )
        rows.append({"scope": "network", "key": "equal_station_mean", "period": period, "estimate": result.estimate, "ci_low": result.ci_low, "ci_high": result.ci_high, "reps": result.reps, "block_length": result.block_length, "seed": seed})
    return pd.DataFrame(rows)


def _quality_summary(observations: pd.DataFrame, metadata: pd.DataFrame, totals: pd.DataFrame) -> pd.DataFrame:
    metrics: list[tuple[str, object, str]] = [
        ("station_count", metadata["station_id"].nunique(), "stations"),
        ("station_days", len(observations), "station-days"),
        ("start_date", observations["date"].min().date().isoformat(), "date"),
        ("end_date", observations["date"].max().date().isoformat(), "date"),
        ("missing_rainfall", observations["rain_mm"].isna().sum(), "station-days"),
        ("negative_rainfall", (observations["rain_mm"] < 0).sum(), "station-days"),
        ("duplicate_station_days", observations.duplicated(["station_id", "date"]).sum(), "station-days"),
        ("missing_elevation", metadata["elevation_m"].isna().sum(), "stations"),
    ]
    for period in ("annual", "wet", "dry"):
        subset = totals[(totals["period"] == period) & totals["included"]]
        metrics.append((f"complete_{period}_station_periods", len(subset), "station-periods"))
        metrics.append((f"complete_{period}_periods_per_station", int(subset.groupby("station_id").size().min()), "periods"))
    return pd.DataFrame(metrics, columns=["metric", "value", "unit"])


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False, encoding="utf-8-sig", float_format="%.12g")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _build_manifest(
    run_dir: Path,
    *,
    run_id: str,
    config: AnalysisConfig,
    config_file: Path,
    rainfall_path: Path,
    metadata_path: Path,
    observations: pd.DataFrame,
    metadata: pd.DataFrame,
    totals: pd.DataFrame,
) -> dict:
    outputs: dict[str, dict[str, object]] = {}
    for path in sorted(item for item in run_dir.rglob("*") if item.is_file() and item.name != "run_manifest.json"):
        relative = path.relative_to(run_dir).as_posix()
        outputs[relative] = {"sha256": _sha256(path), "bytes": path.stat().st_size}
    included = totals[totals["included"]]
    return {
        "schema_version": 1,
        "status": "analysis_complete",
        "run_id": run_id,
        "area_name": config.area_name,
        "method_definitions": {
            "primary_dependence_aware": f"HR-MMK-{config.hr_max_lag}",
            "sensitivity_methods": ["MK", "PW-MK", "TFPW-MK"],
            "multiplicity": "BH within station period-by-method families; network across periods within method",
            "network_estand": "equal-weight gauge-network mean, not a spatial areal mean",
            "bootstrap": "circular residual moving blocks reconstructed on the original year coordinates",
            "fdr": "mean replicate FDP V/max(R,1); under the complete null this equals FWER",
        },
        "parameters": asdict(config),
        "inputs": {
            "config": {"path": str(config_file), "sha256": _sha256(config_file)},
            "rainfall": {"path": str(rainfall_path), "sha256": _sha256(rainfall_path)},
            "station_metadata": {"path": str(metadata_path), "sha256": _sha256(metadata_path)},
        },
        "counts": {
            "stations": int(metadata["station_id"].nunique()),
            "station_days": int(len(observations)),
            "complete_station_periods": {period: int((included["period"] == period).sum()) for period in ("annual", "wet", "dry")},
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "outputs": outputs,
    }
