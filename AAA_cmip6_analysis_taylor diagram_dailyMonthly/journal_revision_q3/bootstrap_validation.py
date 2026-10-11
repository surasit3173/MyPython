from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "cmip6bc_q1_notiers_work" / "cmip6bc"
RESULTS = ROOT / "qdm_p_np_publication_out_q3_final"
OUT = ROOT / "journal_revision_q3" / "statistics"
METHODS = ("QDM_NP_annual", "QDM_NP_monthly", "QDM_P_annual", "QDM_P_monthly")

sys.path.insert(0, str(PKG))
import io_layer  # noqa: E402
from provenance import Provenance  # noqa: E402


def read_corrected(path: Path, time_cfg: dict) -> pd.DataFrame:
    frame = pd.read_csv(path)
    idx = pd.to_datetime(
        dict(
            year=frame.pop(time_cfg["year_col"]),
            month=frame.pop(time_cfg["month_col"]),
            day=frame.pop(time_cfg["day_col"]),
        )
    )
    frame.index = idx
    frame.columns = frame.columns.astype(str)
    return frame.sort_index()


def monthly_matrix(series: pd.Series, years: list[int]) -> np.ndarray:
    values = series[(series.index.year >= years[0]) & (series.index.year <= years[1])]
    monthly = values.resample("MS").sum(min_count=25)
    table = monthly.to_frame("value")
    table["year"] = table.index.year
    table["month"] = table.index.month
    matrix = table.pivot(index="year", columns="month", values="value")
    matrix = matrix.reindex(index=range(years[0], years[1] + 1), columns=range(1, 13))
    return matrix.to_numpy(dtype=float)


def metric_arrays(obs: np.ndarray, sim: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    finite = np.isfinite(obs) & np.isfinite(sim)
    n = finite.sum(axis=1)
    o = np.where(finite, obs, np.nan)
    s = np.where(finite, sim, np.nan)
    error = s - o
    rmse = np.sqrt(np.nanmean(error * error, axis=1))
    mo = np.nanmean(o, axis=1)
    ms = np.nanmean(s, axis=1)
    oc = o - mo[:, None]
    sc = s - ms[:, None]
    cov = np.nansum(oc * sc, axis=1) / np.maximum(n - 1, 1)
    so = np.sqrt(np.nansum(oc * oc, axis=1) / np.maximum(n - 1, 1))
    ss = np.sqrt(np.nansum(sc * sc, axis=1) / np.maximum(n - 1, 1))
    with np.errstate(divide="ignore", invalid="ignore"):
        corr = cov / (so * ss)
        kge = 1.0 - np.sqrt((corr - 1.0) ** 2 + (ss / so - 1.0) ** 2 + (ms / mo - 1.0) ** 2)
    kge[(n < 5) | ~np.isfinite(kge)] = np.nan
    return rmse, kge


def plus_one_p(delta: np.ndarray) -> float:
    values = delta[np.isfinite(delta)]
    if not values.size:
        return np.nan
    n_le = int(np.sum(values <= 0.0))
    n_ge = int(np.sum(values >= 0.0))
    return float(min(1.0, 2.0 * min((n_le + 1) / (values.size + 1), (n_ge + 1) / (values.size + 1))))


def bh_adjust(values: pd.Series) -> pd.Series:
    p = values.to_numpy(dtype=float)
    out = np.full(p.shape, np.nan)
    ok = np.isfinite(p)
    pv = p[ok]
    order = np.argsort(pv)
    ranked = pv[order]
    adjusted = ranked * len(ranked) / np.arange(1, len(ranked) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    restored = np.empty_like(adjusted)
    restored[order] = np.minimum(adjusted, 1.0)
    out[ok] = restored
    return pd.Series(out, index=values.index)


def main() -> None:
    cfg = yaml.safe_load((PKG / "config.yaml").read_text(encoding="utf-8"))
    os.chdir(PKG)
    ds = io_layer.build_dataset(cfg, Provenance(cfg, str(PKG / "config.yaml")))
    validation = cfg["periods"]["validation"]
    b = int(cfg["evaluate"]["bootstrap"]["n_replicates"])
    seed = int(cfg["reproducibility"]["random_seed"])
    corrected = {
        method: {
            model: read_corrected(
                RESULTS / "corrected" / f"bc_{model}_{method}.csv", cfg["time"]
            )
            for model in ds.raw
        }
        for method in METHODS
    }

    rows: list[dict] = []
    comparisons: list[dict] = []
    for model_index, (model, raw_bundle) in enumerate(ds.raw.items()):
        common = ds.observed.df.index.intersection(raw_bundle.df.index)
        for station_index, station in enumerate(ds.stations):
            obs_m = monthly_matrix(ds.observed.df.loc[common, station], validation)
            raw_m = monthly_matrix(raw_bundle.df.loc[common, station], validation)
            rng = np.random.default_rng(np.random.SeedSequence([seed, model_index, station_index]))
            draw = rng.integers(0, obs_m.shape[0], size=(b, obs_m.shape[0]))
            obs_b = obs_m[draw].reshape(b, -1)
            raw_b = raw_m[draw].reshape(b, -1)
            raw_rmse, raw_kge = metric_arrays(obs_b, raw_b)
            method_boot: dict[str, tuple[np.ndarray, np.ndarray]] = {}
            for method in METHODS:
                sim_m = monthly_matrix(corrected[method][model].loc[common, station], validation)
                sim_b = sim_m[draw].reshape(b, -1)
                sim_rmse, sim_kge = metric_arrays(obs_b, sim_b)
                method_boot[method] = (sim_rmse, sim_kge)
                for metric, raw_values, corrected_values in (
                    ("mRMSE", raw_rmse, sim_rmse),
                    ("mKGE", raw_kge, sim_kge),
                ):
                    delta = corrected_values - raw_values
                    point_raw = metric_arrays(obs_m.reshape(1, -1), raw_m.reshape(1, -1))[0 if metric == "mRMSE" else 1][0]
                    point_corrected = metric_arrays(obs_m.reshape(1, -1), sim_m.reshape(1, -1))[0 if metric == "mRMSE" else 1][0]
                    rows.append(
                        {
                            "model": model,
                            "station": station,
                            "method": method,
                            "metric": metric,
                            "raw": point_raw,
                            "corrected": point_corrected,
                            "delta_corrected_minus_raw": point_corrected - point_raw,
                            "ci_low": float(np.nanquantile(delta, 0.025)),
                            "ci_high": float(np.nanquantile(delta, 0.975)),
                            "p_two_sided": plus_one_p(delta),
                            "n_bootstrap": b,
                        }
                    )

            np_rmse, np_kge = method_boot["QDM_NP_monthly"]
            p_rmse, p_kge = method_boot["QDM_P_monthly"]
            for metric, delta in (
                ("mRMSE", p_rmse - np_rmse),
                ("mKGE", p_kge - np_kge),
            ):
                comparisons.append(
                    {
                        "model": model,
                        "station": station,
                        "comparison": "QDM_P_monthly minus QDM_NP_monthly",
                        "metric": metric,
                        "median_delta": float(np.nanmedian(delta)),
                        "ci_low": float(np.nanquantile(delta, 0.025)),
                        "ci_high": float(np.nanquantile(delta, 0.975)),
                        "p_two_sided": plus_one_p(delta),
                    }
                )

    detail = pd.DataFrame(rows)
    detail["p_fdr"] = detail.groupby(["method", "metric"], group_keys=False)["p_two_sided"].apply(bh_adjust)
    lower_better = detail.metric.eq("mRMSE")
    detail["point_improved"] = np.where(
        lower_better,
        detail.delta_corrected_minus_raw < 0,
        detail.delta_corrected_minus_raw > 0,
    )
    detail["ci_improved"] = np.where(lower_better, detail.ci_high < 0, detail.ci_low > 0)
    detail["ci_worsened"] = np.where(lower_better, detail.ci_low > 0, detail.ci_high < 0)
    detail["fdr_significant"] = detail.p_fdr < float(cfg["evaluate"]["fdr_alpha"])

    summary_rows = []
    for (method, metric), group in detail.groupby(["method", "metric"], sort=False):
        summary_rows.append(
            {
                "method": method,
                "metric": metric,
                "mean_raw": group.raw.mean(),
                "mean_corrected": group.corrected.mean(),
                "median_delta": group.delta_corrected_minus_raw.median(),
                "median_ci_low": group.ci_low.median(),
                "median_ci_high": group.ci_high.median(),
                "point_improved_n": int(group.point_improved.sum()),
                "ci_improved_n": int(group.ci_improved.sum()),
                "ci_worsened_n": int(group.ci_worsened.sum()),
                "ci_overlaps_zero_n": int((~group.ci_improved & ~group.ci_worsened).sum()),
                "fdr_significant_n": int(group.fdr_significant.sum()),
                "n_combinations": int(len(group)),
            }
        )

    OUT.mkdir(parents=True, exist_ok=True)
    detail.to_csv(OUT / "bootstrap_combination_results.csv", index=False)
    pd.DataFrame(summary_rows).to_csv(OUT / "bootstrap_summary.csv", index=False)
    comparison_df = pd.DataFrame(comparisons)
    comparison_df["p_fdr"] = comparison_df.groupby("metric", group_keys=False)["p_two_sided"].apply(bh_adjust)
    comparison_df.to_csv(OUT / "bootstrap_monthly_method_comparison.csv", index=False)
    print(pd.DataFrame(summary_rows).round(4).to_string(index=False))


if __name__ == "__main__":
    main()
