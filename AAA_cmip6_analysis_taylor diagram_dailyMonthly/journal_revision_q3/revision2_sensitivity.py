from __future__ import annotations

import copy
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy import stats


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "cmip6bc_q1_notiers_work" / "cmip6bc"
BASELINE = ROOT / "qdm_p_np_publication_out_q3_final"
OUT = ROOT / "journal_revision_q3" / "revision2_analysis"
sys.path.insert(0, str(ENGINE))

import io_layer  # noqa: E402
import metrics  # noqa: E402
import qdm_parametric_nonparametric as qdm  # noqa: E402
from provenance import Provenance  # noqa: E402


ALL_METHODS = (
    "QDM_NP_annual",
    "QDM_NP_monthly",
    "QDM_P_annual",
    "QDM_P_monthly",
)


def configure_engine() -> None:
    qdm.io_layer = io_layer
    qdm.M = metrics
    qdm.Provenance = Provenance


def fit_distribution_aicc(
    x: np.ndarray,
    min_n: int,
    max_n: int = qdm.MAX_PARAMETRIC_FIT_N,
) -> qdm.FittedDist | None:
    x = qdm.finite_positive(x)
    if x.size < min_n or np.nanstd(x) <= 0:
        return None
    if x.size > max_n:
        sx = np.sort(x)
        pos = np.linspace(0, sx.size - 1, max_n).round().astype(int)
        x_fit = sx[pos]
    else:
        x_fit = x

    best = None
    for name in qdm.DISTS:
        dist = getattr(stats, name)
        try:
            if name in {"gamma", "weibull_min", "lognorm"}:
                params = dist.fit(x_fit, floc=0)
                n_params = len(params) - 1
            else:
                params = dist.fit(x_fit)
                n_params = len(params)
            logpdf = dist.logpdf(x, *params)
            if not np.all(np.isfinite(logpdf)):
                continue
            aic = float(2 * n_params - 2 * np.sum(logpdf))
            denominator = x.size - n_params - 1
            if denominator <= 0:
                continue
            aicc = aic + (2 * n_params * (n_params + 1)) / denominator
            ks = stats.kstest(x, name, args=params)
            fitted = qdm.FittedDist(
                name=name,
                params=tuple(float(p) for p in params),
                aic=float(aicc),
                ks_d=float(ks.statistic),
                ks_p=float(ks.pvalue),
                n=int(x.size),
                n_params=n_params,
            )
            if best is None or (fitted.aic, fitted.n_params, fitted.name) < (
                best.aic,
                best.n_params,
                best.name,
            ):
                best = fitted
        except Exception:
            continue
    return best


def run_scenario(
    dataset,
    base_cfg: dict,
    name: str,
    methods: tuple[str, ...],
    wet_threshold: float | None = None,
    use_aicc: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cfg = copy.deepcopy(base_cfg)
    if wet_threshold is not None:
        cfg["data"]["wet_threshold_mm"] = float(wet_threshold)

    original_methods = qdm.METHODS
    original_fit = qdm.fit_distribution
    qdm.METHODS = methods
    if use_aicc:
        qdm.fit_distribution = fit_distribution_aicc

    try:
        outputs = {method: {} for method in methods}
        diagnostics = []
        for model, bundle in dataset.raw.items():
            for method in methods:
                corrected, diag = qdm.correct_method(
                    dataset.observed.df,
                    bundle.df,
                    cfg,
                    model,
                    method,
                )
                outputs[method][model] = corrected
                diagnostics.append(diag)
        station_metrics = qdm.evaluate_outputs(dataset, outputs, cfg)
        summary = qdm.summarise(station_metrics)
        diagnostics_df = pd.concat(diagnostics, ignore_index=True)
    finally:
        qdm.METHODS = original_methods
        qdm.fit_distribution = original_fit

    scenario_dir = OUT / name
    scenario_dir.mkdir(parents=True, exist_ok=True)
    station_metrics.to_csv(scenario_dir / "station_metrics.csv", index=False)
    summary.to_csv(scenario_dir / "summary.csv", index=False)
    diagnostics_df.to_csv(scenario_dir / "fit_diagnostics.csv", index=False)
    return station_metrics, summary, diagnostics_df


def select_validation(summary: pd.DataFrame, scenario: str) -> pd.DataFrame:
    keep = {"PBIAS", "KS_D", "q99_relbias_pct", "mRMSE", "mKGE", "clim_r"}
    out = summary[
        summary["period"].eq("validation") & summary["metric"].isin(keep)
    ].copy()
    out.insert(0, "scenario", scenario)
    return out


def calendar_audit(dataset, cfg: dict) -> pd.DataFrame:
    rows = []
    for model, bundle in dataset.raw.items():
        common = dataset.observed.df.index.intersection(bundle.df.index)
        for period, years in cfg["periods"].items():
            idx = common[(common.year >= years[0]) & (common.year <= years[1])]
            rows.append(
                {
                    "model": model,
                    "period": period,
                    "start": idx.min().date().isoformat(),
                    "end": idx.max().date().isoformat(),
                    "days": len(idx),
                    "feb29_days": int(((idx.month == 2) & (idx.day == 29)).sum()),
                    "duplicates": int(idx.duplicated().sum()),
                    "monotonic": bool(idx.is_monotonic_increasing),
                }
            )
    return pd.DataFrame(rows)


def station_spatial_summary() -> pd.DataFrame:
    station_metrics = pd.read_csv(BASELINE / "station_metrics.csv")
    stations = pd.read_csv(ENGINE / "data" / "stations.csv", dtype={"station": str})
    validation = station_metrics[station_metrics["period"].eq("validation")].copy()
    metrics_keep = ["mRMSE", "mKGE", "q99_relbias_pct", "KS_D"]
    rows = []
    for station, group in validation.groupby("station"):
        raw = group[group["dataset"].eq("raw")]
        for dataset_name in ALL_METHODS:
            corrected = group[group["dataset"].eq(dataset_name)]
            row = {"station": str(station), "method": dataset_name}
            for metric_name in metrics_keep:
                raw_mean = float(raw[metric_name].mean())
                corrected_mean = float(corrected[metric_name].mean())
                row[f"raw_{metric_name}"] = raw_mean
                row[f"corrected_{metric_name}"] = corrected_mean
                row[f"delta_{metric_name}"] = corrected_mean - raw_mean
            rows.append(row)
    result = pd.DataFrame(rows)
    stations.columns = [str(c).strip().lower() for c in stations.columns]
    station_col = "station" if "station" in stations.columns else stations.columns[0]
    stations = stations.rename(columns={station_col: "station"})
    stations["station"] = stations["station"].astype(str)
    return result.merge(stations, on="station", how="left", validate="many_to_one")


def main() -> None:
    configure_engine()
    OUT.mkdir(parents=True, exist_ok=True)
    config_path = ENGINE / "config.yaml"
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    os.chdir(ENGINE)
    dataset = io_layer.build_dataset(cfg, Provenance(cfg, str(config_path)))

    threshold_parts = []
    for threshold in (0.1, 0.5):
        _, summary, _ = run_scenario(
            dataset,
            cfg,
            f"wet_threshold_{threshold:.1f}",
            ALL_METHODS,
            wet_threshold=threshold,
        )
        threshold_parts.append(select_validation(summary, f"{threshold:.1f} mm"))
    baseline_summary = pd.read_csv(BASELINE / "summary.csv")
    threshold_parts.append(select_validation(baseline_summary, "1.0 mm (primary)"))
    pd.concat(threshold_parts, ignore_index=True).to_csv(
        OUT / "wet_threshold_sensitivity.csv", index=False
    )

    _, aicc_summary, aicc_diag = run_scenario(
        dataset,
        cfg,
        "aicc",
        ("QDM_P_annual", "QDM_P_monthly"),
        use_aicc=True,
    )
    select_validation(aicc_summary, "AICc").to_csv(
        OUT / "aicc_validation_summary.csv", index=False
    )
    selection_rows = []
    for method in ("QDM_P_annual", "QDM_P_monthly"):
        subset = aicc_diag[
            aicc_diag["method"].eq(method)
            & aicc_diag["period"].eq("validation")
            & ~aicc_diag["fallback_used"].fillna(False)
        ]
        for side in ("obs_dist", "mod_dist"):
            counts = subset.drop_duplicates(["model", "station", "group"])[side].value_counts()
            for distribution, count in counts.items():
                selection_rows.append(
                    {
                        "criterion": "AICc",
                        "method": method,
                        "side": side.replace("_dist", ""),
                        "distribution": distribution,
                        "count": int(count),
                    }
                )
    pd.DataFrame(selection_rows).to_csv(OUT / "aicc_selection_counts.csv", index=False)

    calendar_audit(dataset, cfg).to_csv(OUT / "calendar_audit.csv", index=False)
    station_spatial_summary().to_csv(OUT / "station_spatial_summary.csv", index=False)
    print(OUT)


if __name__ == "__main__":
    main()
