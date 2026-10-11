from __future__ import annotations

import json
import math
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent / "mplconfig"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.colors import TwoSlopeNorm
import numpy as np
import pandas as pd


WORKSPACE = Path(__file__).resolve().parent
DATA_ROOT = WORKSPACE / "data_rar" / "Data_Uttaradit"
OUT = WORKSPACE / "audit_corrected"
FIG = OUT / "figures"

MODELS = [
    "ACCESS-ESM1-5", "CanESM5", "CESM2", "EC-Earth3",
    "FGOALS-g3", "MIROC6", "MRI-ESM2-0",
]
SCENARIOS = ["ssp245", "ssp585"]
WINDOWS = {
    "Near-term": (2021, 2040),
    "Mid-term": (2041, 2060),
    "Long-term": (2081, 2100),
}
LEGACY_WINDOWS = {
    "Near": (2021, 2050),
    "Mid": (2041, 2070),
    "Late": (2071, 2100),
}
INDEX_ORDER = [
    "PRCPTOT", "SDII", "Rx1day", "Rx5day", "CDD", "CWD",
    "R10mm", "R20mm", "R50mm", "R95p", "R99p",
]
INDEX_UNITS = {
    "PRCPTOT": "mm yr-1", "SDII": "mm wet-day-1", "Rx1day": "mm",
    "Rx5day": "mm", "CDD": "days", "CWD": "days",
    "R10mm": "days yr-1", "R20mm": "days yr-1", "R50mm": "days yr-1",
    "R95p": "mm yr-1", "R99p": "mm yr-1",
}
INDEX_DESCRIPTIONS = {
    "PRCPTOT": "Annual wet-day precipitation total (daily precipitation >= 1 mm)",
    "SDII": "Mean precipitation on wet days",
    "Rx1day": "Annual maximum 1-day precipitation",
    "Rx5day": "Annual maximum consecutive 5-day precipitation",
    "CDD": "Annual maximum consecutive days with precipitation < 1 mm",
    "CWD": "Annual maximum consecutive days with precipitation >= 1 mm",
    "R10mm": "Annual count of days with precipitation >= 10 mm",
    "R20mm": "Annual count of days with precipitation >= 20 mm",
    "R50mm": "Annual count of days with precipitation >= 50 mm",
    "R95p": "Annual precipitation above the observed wet-day 95th percentile",
    "R99p": "Annual precipitation above the observed wet-day 99th percentile",
}


def locate(model: str, variant: str, experiment: str) -> Path:
    prefix = "bc_pr_day" if variant == "bc" else "pr_day"
    matches = sorted((DATA_ROOT / model).glob(f"{prefix}_{model}_{experiment}_*.csv"))
    if len(matches) != 1:
        raise RuntimeError((model, variant, experiment, [str(p) for p in matches]))
    return matches[0]


def load_daily(path: Path, stations: list[str]) -> pd.DataFrame:
    requested = {"YEAR", "MONTH", "DAY", *stations}
    df = pd.read_csv(path, usecols=lambda c: str(c).strip() in requested, low_memory=False)
    df.columns = [str(c).strip() for c in df.columns]
    dates = pd.to_datetime(
        {"year": df["YEAR"], "month": df["MONTH"], "day": df["DAY"]},
        errors="coerce",
    )
    values = df[stations].apply(pd.to_numeric, errors="coerce")
    values.index = pd.DatetimeIndex(dates)
    values = values.loc[~values.index.isna()].sort_index()
    if values.index.has_duplicates:
        raise ValueError(f"duplicate dates in {path}")
    return values


def longest_run(mask: np.ndarray) -> int:
    best = run = 0
    for value in np.asarray(mask, dtype=bool):
        run = run + 1 if value else 0
        best = max(best, run)
    return int(best)


def thresholds_from_observations(obs: pd.DataFrame) -> dict[str, tuple[float, float]]:
    result = {}
    for station in obs.columns:
        wet = obs[station].dropna()
        wet = wet[wet >= 1.0]
        result[station] = (float(np.percentile(wet, 95)), float(np.percentile(wet, 99)))
    return result


def annual_indices(daily: pd.DataFrame, thresholds: dict[str, tuple[float, float]],
                   dataset: str, model: str, scenario: str) -> pd.DataFrame:
    rows: list[dict] = []
    for station in daily.columns:
        p95, p99 = thresholds[station]
        series = daily[station].dropna().astype(float)
        for year, block in series.groupby(series.index.year):
            values = block.to_numpy(dtype=float)
            wet = values >= 1.0
            n_wet = int(wet.sum())
            wet_total = float(values[wet].sum())
            rx5 = float(pd.Series(values).rolling(5, min_periods=5).sum().max())
            computed = {
                "PRCPTOT": wet_total,
                "SDII": wet_total / n_wet if n_wet else np.nan,
                "Rx1day": float(np.max(values)) if values.size else np.nan,
                "Rx5day": rx5,
                "CDD": longest_run(~wet),
                "CWD": longest_run(wet),
                "R10mm": int((values >= 10.0).sum()),
                "R20mm": int((values >= 20.0).sum()),
                "R50mm": int((values >= 50.0).sum()),
                "R95p": float(values[values > p95].sum()),
                "R99p": float(values[values > p99].sum()),
            }
            n_days = int(values.size)
            for index, value in computed.items():
                rows.append({
                    "dataset": dataset,
                    "model": model,
                    "scenario": scenario,
                    "station": station,
                    "year": int(year),
                    "days_in_year": n_days,
                    "index": index,
                    "value": float(value),
                })
    return pd.DataFrame(rows)


def metric_pair(model: pd.Series, obs: pd.Series) -> dict[str, float]:
    aligned = pd.concat([model.rename("m"), obs.rename("o")], axis=1, sort=True).dropna()
    m = aligned["m"].to_numpy(dtype=float)
    o = aligned["o"].to_numpy(dtype=float)
    r = float(np.corrcoef(m, o)[0, 1]) if len(m) > 1 else np.nan
    rmse = float(np.sqrt(np.mean((m - o) ** 2)))
    mae = float(np.mean(np.abs(m - o)))
    pbias = float(100.0 * (m.sum() - o.sum()) / o.sum()) if o.sum() else np.nan
    denom = float(np.sum((o - o.mean()) ** 2))
    nse = float(1.0 - np.sum((m - o) ** 2) / denom) if denom else np.nan
    alpha = float(np.std(m, ddof=1) / np.std(o, ddof=1)) if np.std(o, ddof=1) else np.nan
    beta = float(np.mean(m) / np.mean(o)) if np.mean(o) else np.nan
    kge = float(1.0 - np.sqrt((r - 1) ** 2 + (alpha - 1) ** 2 + (beta - 1) ** 2))
    return {"n": len(m), "r": r, "rmse": rmse, "mae": mae, "pbias_pct": pbias,
            "nse": nse, "kge": kge}


def historical_skill(obs: pd.DataFrame, stations: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    detail = []
    for model in MODELS:
        raw = load_daily(locate(model, "raw", "historical"), stations)
        bc = load_daily(locate(model, "bc", "historical"), stations)
        for station in stations:
            for variant, values in (("Raw", raw), ("Bias-corrected", bc)):
                daily = metric_pair(values[station], obs[station])
                vm = values[station].resample("MS").sum(min_count=1)
                om = obs[station].resample("MS").sum(min_count=1)
                monthly = metric_pair(vm, om)
                for scale, metrics in (("Daily", daily), ("Monthly", monthly)):
                    detail.append({"model": model, "station": station,
                                   "variant": variant, "scale": scale, **metrics})
    detail_df = pd.DataFrame(detail)
    summary_rows = []
    for (scale, variant), block in detail_df.groupby(["scale", "variant"], sort=False):
        row = {"scale": scale, "variant": variant, "n_model_station_pairs": len(block)}
        for metric in ("r", "rmse", "mae", "pbias_pct", "nse", "kge"):
            row[f"median_{metric}"] = float(block[metric].median())
            row[f"q25_{metric}"] = float(block[metric].quantile(0.25))
            row[f"q75_{metric}"] = float(block[metric].quantile(0.75))
        summary_rows.append(row)
    summary = pd.DataFrame(summary_rows)
    paired = detail_df.pivot(index=["model", "station", "scale"], columns="variant")
    improvement_rows = []
    for scale, block in paired.groupby(level="scale"):
        improvement_rows.append({
            "scale": scale,
            "fraction_lower_rmse": float((block[("rmse", "Bias-corrected")] < block[("rmse", "Raw")]).mean()),
            "fraction_lower_abs_pbias": float((block[("pbias_pct", "Bias-corrected")].abs() < block[("pbias_pct", "Raw")].abs()).mean()),
            "fraction_higher_r": float((block[("r", "Bias-corrected")] > block[("r", "Raw")]).mean()),
            "fraction_higher_kge": float((block[("kge", "Bias-corrected")] > block[("kge", "Raw")]).mean()),
        })
    summary = summary.merge(pd.DataFrame(improvement_rows), on="scale", how="left")
    return detail_df, summary


def period_mean(frame: pd.DataFrame, start: int, end: int) -> pd.DataFrame:
    return (frame[frame["year"].between(start, end)]
            .groupby(["dataset", "model", "scenario", "station", "index"], as_index=False)
            .agg(period_mean=("value", "mean"), n_years=("year", "nunique"),
                 min_days=("days_in_year", "min"), max_days=("days_in_year", "max")))


def change_table(annual: pd.DataFrame, windows: dict[str, tuple[int, int]],
                 obs_baseline: tuple[int, int]) -> pd.DataFrame:
    obs = annual[(annual["dataset"] == "Observed") &
                 annual["year"].between(*obs_baseline)]
    obs_base = (obs.groupby(["station", "index"], as_index=False)["value"]
                .mean().rename(columns={"value": "obs_baseline"}))
    hist = annual[(annual["dataset"] == "BC_HIST") &
                  annual["year"].between(*obs_baseline)]
    model_base = (hist.groupby(["model", "station", "index"], as_index=False)["value"]
                  .mean().rename(columns={"value": "model_baseline"}))

    rows = []
    future = annual[annual["dataset"] == "BC_FUTURE"]
    for window, (start, end) in windows.items():
        current = (future[future["year"].between(start, end)]
                   .groupby(["model", "scenario", "station", "index"], as_index=False)["value"]
                   .mean().rename(columns={"value": "future_mean"}))
        current["window"] = window
        rows.append(current)
    station = pd.concat(rows, ignore_index=True)
    station = station.merge(obs_base, on=["station", "index"], how="left")
    station = station.merge(model_base, on=["model", "station", "index"], how="left")
    for label, base in (("obs", "obs_baseline"), ("model", "model_baseline")):
        station[f"delta_{label}_abs"] = station["future_mean"] - station[base]
        station[f"delta_{label}_pct"] = np.where(
            station[base].abs() > 1e-9,
            100.0 * station[f"delta_{label}_abs"] / station[base], np.nan)

    model_rows = []
    for keys, block in station.groupby(["model", "scenario", "window", "index"], sort=False):
        model, scenario, window, index = keys
        future_regional = float(block["future_mean"].mean())
        obs_regional = float(block["obs_baseline"].mean())
        model_regional = float(block["model_baseline"].mean())
        model_rows.append({
            "model": model, "scenario": scenario, "window": window, "index": index,
            "future_regional": future_regional,
            "obs_baseline_regional": obs_regional,
            "model_baseline_regional": model_regional,
            "delta_obs_abs": future_regional - obs_regional,
            "delta_model_abs": future_regional - model_regional,
            "delta_obs_pct": 100.0 * (future_regional - obs_regional) / obs_regional if abs(obs_regional) > 1e-9 else np.nan,
            "delta_model_pct": 100.0 * (future_regional - model_regional) / model_regional if abs(model_regional) > 1e-9 else np.nan,
            "mean_station_delta_obs_pct": float(block["delta_obs_pct"].mean()),
            "mean_station_delta_model_pct": float(block["delta_model_pct"].mean()),
        })
    model_df = pd.DataFrame(model_rows)

    ensemble_rows = []
    for keys, block in model_df.groupby(["scenario", "window", "index"], sort=False):
        scenario, window, index = keys
        row = {"scenario": scenario, "window": window, "index": index, "model_count": len(block)}
        for baseline in ("obs", "model"):
            abs_values = block[f"delta_{baseline}_abs"]
            pct_values = block[f"delta_{baseline}_pct"]
            pos = int((abs_values > 0).sum())
            neg = int((abs_values < 0).sum())
            agreement = max(pos, neg) / len(block)
            median_abs = float(abs_values.median())
            direction = "increase" if median_abs > 0 else "decrease" if median_abs < 0 else "no-change"
            robust = agreement >= 6 / 7
            row.update({
                f"{baseline}_median_abs": median_abs,
                f"{baseline}_q25_abs": float(abs_values.quantile(0.25)),
                f"{baseline}_q75_abs": float(abs_values.quantile(0.75)),
                f"{baseline}_median_pct": float(pct_values.median()),
                f"{baseline}_q25_pct": float(pct_values.quantile(0.25)),
                f"{baseline}_q75_pct": float(pct_values.quantile(0.75)),
                f"{baseline}_agreement": agreement,
                f"{baseline}_direction": direction,
                f"{baseline}_robust": robust,
                f"{baseline}_classification": f"robust {direction}" if robust else "ambiguous",
            })
        row["sign_reversal"] = row["obs_direction"] != row["model_direction"]
        row["classification_changed"] = row["obs_classification"] != row["model_classification"]
        row["baseline_sensitivity_pp"] = row["obs_median_pct"] - row["model_median_pct"]
        ensemble_rows.append(row)
    ensemble = pd.DataFrame(ensemble_rows)
    return station, model_df, ensemble


def residual_bias(annual: pd.DataFrame, baseline=(1995, 2014)) -> tuple[pd.DataFrame, pd.DataFrame]:
    obs = (annual[(annual["dataset"] == "Observed") & annual["year"].between(*baseline)]
           .groupby(["station", "index"], as_index=False)["value"].mean()
           .rename(columns={"value": "obs_mean"}))
    hist = (annual[(annual["dataset"] == "BC_HIST") & annual["year"].between(*baseline)]
            .groupby(["model", "station", "index"], as_index=False)["value"].mean()
            .rename(columns={"value": "bc_hist_mean"}))
    detail = hist.merge(obs, on=["station", "index"], how="left")
    detail["bias_abs"] = detail["bc_hist_mean"] - detail["obs_mean"]
    detail["bias_pct"] = np.where(detail["obs_mean"].abs() > 1e-9,
                                  100.0 * detail["bias_abs"] / detail["obs_mean"], np.nan)
    model_regional = (detail.groupby(["model", "index"], as_index=False)
                      .agg(bc_hist=("bc_hist_mean", "mean"), obs=("obs_mean", "mean")))
    model_regional["bias_abs"] = model_regional["bc_hist"] - model_regional["obs"]
    model_regional["bias_pct"] = np.where(model_regional["obs"].abs() > 1e-9,
                                          100.0 * model_regional["bias_abs"] / model_regional["obs"], np.nan)
    summary = (model_regional.groupby("index", as_index=False)
               .agg(median_regional_bias_pct=("bias_pct", "median"),
                    q25_regional_bias_pct=("bias_pct", lambda s: s.quantile(0.25)),
                    q75_regional_bias_pct=("bias_pct", lambda s: s.quantile(0.75)),
                    max_abs_regional_bias_pct=("bias_pct", lambda s: s.abs().max()),
                    median_regional_bias_abs=("bias_abs", "median")))
    return detail, summary


def change_preservation(annual: pd.DataFrame, baseline=(1995, 2014)) -> pd.DataFrame:
    rows = []
    for variant, hist_name, future_name in (
        ("Raw", "RAW_HIST", "RAW_FUTURE"),
        ("Bias-corrected", "BC_HIST", "BC_FUTURE"),
    ):
        hist = (annual[(annual["dataset"] == hist_name) & annual["year"].between(*baseline)]
                .groupby(["model", "station", "index"], as_index=False)["value"].mean()
                .rename(columns={"value": "baseline"}))
        future = annual[annual["dataset"] == future_name]
        for window, (start, end) in WINDOWS.items():
            current = (future[future["year"].between(start, end)]
                       .groupby(["model", "scenario", "station", "index"], as_index=False)["value"].mean()
                       .rename(columns={"value": "future"}))
            merged = current.merge(hist, on=["model", "station", "index"], how="left")
            for keys, block in merged.groupby(["model", "scenario", "index"], sort=False):
                model, scenario, index = keys
                b = float(block["baseline"].mean())
                f = float(block["future"].mean())
                rows.append({"variant": variant, "model": model, "scenario": scenario,
                             "window": window, "index": index,
                             "delta_abs": f - b,
                             "delta_pct": 100.0 * (f - b) / b if abs(b) > 1e-9 else np.nan})
    frame = pd.DataFrame(rows)
    wide = frame.pivot(index=["model", "scenario", "window", "index"],
                       columns="variant", values=["delta_abs", "delta_pct"]).reset_index()
    wide.columns = ["_".join([str(x) for x in col if str(x)]) if isinstance(col, tuple) else col
                    for col in wide.columns]
    wide["sign_preserved"] = np.sign(wide["delta_abs_Raw"]) == np.sign(wide["delta_abs_Bias-corrected"])
    wide["abs_pct_difference"] = (wide["delta_pct_Bias-corrected"] - wide["delta_pct_Raw"]).abs()
    return wide


def setup_plotting():
    plt.rcParams.update({
        "font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
        "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
        "xtick.labelsize": 8, "ytick.labelsize": 8,
        "axes.spines.top": False, "axes.spines.right": False,
        "figure.facecolor": "white", "axes.facecolor": "white",
        "savefig.dpi": 400,
    })


def fig_baseline_sensitivity(ensemble: pd.DataFrame):
    setup_plotting()
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.35), sharex=True, sharey=True)
    marker_map = {"Near-term": "o", "Mid-term": "s", "Long-term": "^"}
    all_vals = pd.concat([ensemble["obs_median_pct"], ensemble["model_median_pct"]]).replace([np.inf, -np.inf], np.nan).dropna()
    limit = max(50, float(np.nanpercentile(np.abs(all_vals), 95)) * 1.15)
    limit = min(limit, 220)
    for ax, scenario in zip(axes, SCENARIOS):
        sub = ensemble[(ensemble["scenario"] == scenario) & (ensemble["index"] != "R50mm")]
        for window, block in sub.groupby("window"):
            ax.scatter(block["obs_median_pct"], block["model_median_pct"],
                       marker=marker_map[window], s=38,
                       facecolor="black" if scenario == "ssp585" else "white",
                       edgecolor="black", linewidth=0.8, zorder=3)
        reversed_rows = sub[sub["sign_reversal"]]
        ax.scatter(reversed_rows["obs_median_pct"], reversed_rows["model_median_pct"],
                   marker="x", s=28, color="0.35", linewidth=0.9, zorder=4)
        ax.axhline(0, color="0.55", lw=0.7)
        ax.axvline(0, color="0.55", lw=0.7)
        ax.plot([-limit, limit], [-limit, limit], color="0.25", lw=0.8, ls="--")
        ax.set_xlim(-limit, limit); ax.set_ylim(-limit, limit)
        ax.grid(True, color="0.9", lw=0.5)
        ax.set_title("SSP2-4.5" if scenario == "ssp245" else "SSP5-8.5")
        ax.set_aspect("equal", adjustable="box")
    axes[0].set_ylabel("Change vs model historical baseline (%)")
    for ax in axes:
        ax.set_xlabel("Change vs observed baseline (%)")
    handles = [Line2D([0], [0], marker=m, color="none", markeredgecolor="black",
                      markerfacecolor="white", label=w, markersize=6)
               for w, m in marker_map.items()]
    handles.append(Line2D([0], [0], marker="x", color="none", markeredgecolor="0.35",
                          label="Sign reversal", markersize=6))
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 1.02), ncol=4, frameon=False)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIG / "FIGURE_02_baseline_sensitivity.png", bbox_inches="tight")
    plt.close(fig)


def fig_change_heatmap(ensemble: pd.DataFrame):
    setup_plotting()
    columns = [(s, w) for s in SCENARIOS for w in WINDOWS]
    matrix = np.full((len(INDEX_ORDER), len(columns)), np.nan)
    robust = np.zeros_like(matrix, dtype=bool)
    for i, index in enumerate(INDEX_ORDER):
        for j, (scenario, window) in enumerate(columns):
            row = ensemble[(ensemble["scenario"] == scenario) &
                           (ensemble["window"] == window) &
                           (ensemble["index"] == index)].iloc[0]
            matrix[i, j] = row["model_median_pct"]
            robust[i, j] = bool(row["model_robust"])
    display = np.clip(matrix, -100, 100)
    fig, ax = plt.subplots(figsize=(7.1, 4.45))
    im = ax.imshow(display, cmap="RdBu", norm=TwoSlopeNorm(vmin=-100, vcenter=0, vmax=100), aspect="auto")
    ax.set_yticks(range(len(INDEX_ORDER)), INDEX_ORDER)
    labels = []
    for scenario, window in columns:
        labels.append(("245" if scenario == "ssp245" else "585") + "\n" + window.replace("-term", ""))
    ax.set_xticks(range(len(columns)), labels)
    for i in range(len(INDEX_ORDER)):
        for j in range(len(columns)):
            value = matrix[i, j]
            star = "*" if robust[i, j] else ""
            text = f"{value:+.0f}{star}" if np.isfinite(value) else "–"
            color = "white" if abs(display[i, j]) > 55 else "black"
            ax.text(j, i, text, ha="center", va="center", color=color, fontsize=7.2,
                    fontweight="bold" if robust[i, j] else "normal")
    ax.axvline(2.5, color="black", lw=1.1)
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("Median change vs model historical baseline (%)")
    ax.set_title("Audited regional changes across seven CMIP6 models")
    ax.set_xlabel("Scenario and projection window")
    ax.text(0, -0.16, "* at least 6 of 7 models agree on the sign; R50mm percentages are denominator-sensitive.",
            transform=ax.transAxes, fontsize=7.3, va="top")
    fig.tight_layout()
    fig.savefig(FIG / "FIGURE_03_change_heatmap.png", bbox_inches="tight")
    plt.close(fig)


def fig_selected_profiles(ensemble: pd.DataFrame):
    setup_plotting()
    selected = ["PRCPTOT", "SDII", "Rx5day", "R99p", "CDD", "CWD"]
    fig, axes = plt.subplots(2, 3, figsize=(7.1, 4.9), sharex=True)
    x = np.arange(3)
    worder = list(WINDOWS)
    for ax, index in zip(axes.flat, selected):
        for scenario, ls, marker, shade in (("ssp245", "-", "o", "0.25"),
                                             ("ssp585", "--", "s", "0.62")):
            block = (ensemble[(ensemble["scenario"] == scenario) & (ensemble["index"] == index)]
                     .set_index("window").loc[worder])
            y = block["model_median_pct"].to_numpy(float)
            lo = block["model_q25_pct"].to_numpy(float)
            hi = block["model_q75_pct"].to_numpy(float)
            ax.fill_between(x, lo, hi, color=shade, alpha=0.16, lw=0)
            ax.plot(x, y, ls=ls, marker=marker, color=shade, lw=1.2, ms=4,
                    markerfacecolor=shade, label="SSP2-4.5" if scenario == "ssp245" else "SSP5-8.5")
            for xi, yi, is_robust in zip(x, y, block["model_robust"]):
                if not is_robust:
                    ax.plot(xi, yi, marker=marker, ms=4.5, markerfacecolor="white",
                            markeredgecolor=shade, ls="none")
        ax.axhline(0, color="0.55", lw=0.7)
        ax.grid(axis="y", color="0.9", lw=0.5)
        ax.set_title(index)
        ax.set_ylabel("Change (%)")
        ax.set_xticks(x, ["Near", "Mid", "Long"])
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 1.01), ncol=2, frameon=False)
    fig.text(0.5, 0.01, "Filled markers: >=6/7 model sign agreement; bands: interquartile range across models", ha="center", fontsize=7.5)
    fig.tight_layout(rect=(0, 0.035, 1, 0.95))
    fig.savefig(FIG / "FIGURE_04_selected_profiles.png", bbox_inches="tight")
    plt.close(fig)


def fig_residual_bias(detail: pd.DataFrame):
    setup_plotting()
    model_regional = (detail.groupby(["model", "index"], as_index=False)
                      .agg(bc=("bc_hist_mean", "mean"), obs=("obs_mean", "mean")))
    model_regional["bias_pct"] = 100.0 * (model_regional["bc"] - model_regional["obs"]) / model_regional["obs"]
    data = [model_regional[model_regional["index"] == index]["bias_pct"].to_numpy(float)
            for index in INDEX_ORDER]
    fig, ax = plt.subplots(figsize=(7.0, 3.7))
    bp = ax.boxplot(data, orientation="horizontal", tick_labels=INDEX_ORDER, patch_artist=True,
                    medianprops={"color": "black", "linewidth": 1.2},
                    boxprops={"facecolor": "0.82", "edgecolor": "0.25"},
                    whiskerprops={"color": "0.35"}, capprops={"color": "0.35"},
                    flierprops={"marker": "o", "markersize": 3, "markerfacecolor": "white",
                                "markeredgecolor": "0.35"})
    ax.axvline(0, color="black", lw=0.8, ls="--")
    ax.grid(axis="x", color="0.9", lw=0.5)
    ax.set_xlabel("Bias-corrected historical minus observed baseline (%)")
    ax.set_title("Residual historical bias, 1995–2014 (seven-model regional summaries)")
    fig.tight_layout()
    fig.savefig(FIG / "FIGURE_05_residual_bias.png", bbox_inches="tight")
    plt.close(fig)


def dataframe_to_markdown(frame: pd.DataFrame) -> str:
    display = frame.copy()
    headers = [str(c) for c in display.columns]
    rows = [[str(v) for v in row] for row in display.itertuples(index=False, name=None)]
    lines = ["| " + " | ".join(headers) + " |",
             "| " + " | ".join(["---"] * len(headers)) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def write_audit_markdown(summary: dict, skill: pd.DataFrame, residual: pd.DataFrame,
                         ensemble: pd.DataFrame, preservation: pd.DataFrame):
    lines = [
        "# Scientific audit of the Uttaradit CMIP6 precipitation-extreme workflow",
        "",
        "## Scope and reproducibility",
        "",
        f"- Observations: {summary['observed_start']}–{summary['observed_end']}, "
        f"{summary['station_count']} gauges; {summary['model_count']} CMIP6 models; "
        "SSP2-4.5 and SSP5-8.5.",
        "- Main corrected contrasts use one baseline (1995–2014) and three non-overlapping "
        "20-year windows (2021–2040, 2041–2060, 2081–2100).",
        "- Annual indices were independently recomputed from the supplied daily CSV files. "
        "A wet day is >=1 mm; station-specific R95p/R99p thresholds come from observed wet days "
        "during 1981–2014.",
        "",
        "## Code and result findings",
        "",
        "1. The index formulas are internally consistent with their stated ETCCDI-style definitions. "
        "R50mm is a study-specific threshold index rather than a core ETCCDI index.",
        "2. The archived main summaries compare future bias-corrected simulations directly with "
        "observations. Because historical bias remains, this estimand can change the magnitude and "
        "occasionally the direction of projected change. The manuscript therefore makes the "
        "model-consistent future-minus-bias-corrected-historical contrast primary and retains the "
        "observed-baseline contrast as sensitivity analysis.",
        "3. The archived 2021–2050 and 2041–2070 windows overlap by ten years. They are valid as "
        "climatological summaries but not independent periods. The manuscript uses non-overlapping "
        "AR6-style windows.",
        "4. The supplied trend self-test reports a false-positive rate of 0.383 for TFPW-MK under "
        "AR(1)=0.6 at nominal alpha=0.05. Consequently, per-window TFPW p-values are not used as "
        "confirmatory evidence in the manuscript.",
        "5. The >=80% model sign-agreement flag is a robustness screen (at least 6/7 models), not a "
        "statistical significance test. All manuscript captions use that terminology.",
        "6. Percentage changes for R50mm can be unstable because the baseline count is small. "
        "Absolute days per year are reported with any percentage only as secondary context.",
        "7. The archive contains bias-corrected files and code that consumes QDM evaluation outputs, "
        "but it does not contain the code/provenance needed to verify calibration and out-of-sample "
        "validation of the supplied corrected series. The manuscript describes them as supplied "
        "bias-corrected/QDM-labelled data and records this as a limitation.",
        "8. Equal station and equal model weights are used. Spatial representativeness and CMIP6 model "
        "genealogical dependence are not resolved and are treated as limitations.",
        "",
        "## Quantitative checks",
        "",
        f"- Baseline definition changed the sign for {int(ensemble['sign_reversal'].sum())} of "
        f"{len(ensemble)} scenario–window–index combinations and changed the three-class robustness "
        f"label for {int(ensemble['classification_changed'].sum())} combinations.",
        f"- Raw versus bias-corrected model-consistent changes retained the sign for "
        f"{100*preservation['sign_preserved'].mean():.1f}% of model–scenario–window–index cases; "
        f"the median absolute difference in relative change was "
        f"{preservation['abs_pct_difference'].replace([np.inf, -np.inf], np.nan).median():.1f} percentage points.",
        "- Historical skill and residual-bias tables below were calculated independently from daily "
        "data; they show that bias correction is most reliable for mean bias/distribution alignment "
        "and does not uniformly improve daily timing or RMSE.",
        "",
        "### Historical skill summary (median across 7 models × 13 gauges)",
        "",
        dataframe_to_markdown(skill.round(3)),
        "",
        "### Residual regional bias by index (1995–2014)",
        "",
        dataframe_to_markdown(residual.round(2)),
        "",
        "## Publication decision",
        "",
        "The data support an uncertainty/robustness article, but not a claim that every archived trend "
        "or observed-baseline percentage is confirmatory. The APST manuscript is therefore written "
        "around baseline sensitivity, residual bias, non-overlapping projection windows, and model "
        "sign agreement, with bounded hazard interpretation.",
    ]
    (OUT / "scientific_audit.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    obs_path = DATA_ROOT / "Observed_Rain_daily_198101_201412_Uttaradit.csv"
    header = pd.read_csv(obs_path, nrows=0)
    stations = [str(c) for c in header.columns if str(c) not in {"YEAR", "MONTH", "DAY"}]
    obs = load_daily(obs_path, stations)
    thresholds = thresholds_from_observations(obs)

    annual_parts = [annual_indices(obs, thresholds, "Observed", "Observed", "historical")]
    input_profiles = []
    for model in MODELS:
        for variant, dataset in (("raw", "RAW_HIST"), ("bc", "BC_HIST")):
            path = locate(model, variant, "historical")
            daily = load_daily(path, stations)
            input_profiles.append({"model": model, "variant": variant, "experiment": "historical",
                                   "start": str(daily.index.min().date()), "end": str(daily.index.max().date()),
                                   "rows": len(daily), "missing_cells": int(daily.isna().sum().sum()),
                                   "negative_cells": int((daily < 0).sum().sum())})
            annual_parts.append(annual_indices(daily, thresholds, dataset, model, "historical"))
        for scenario in SCENARIOS:
            for variant, dataset in (("raw", "RAW_FUTURE"), ("bc", "BC_FUTURE")):
                path = locate(model, variant, scenario)
                daily = load_daily(path, stations)
                input_profiles.append({"model": model, "variant": variant, "experiment": scenario,
                                       "start": str(daily.index.min().date()), "end": str(daily.index.max().date()),
                                       "rows": len(daily), "missing_cells": int(daily.isna().sum().sum()),
                                       "negative_cells": int((daily < 0).sum().sum())})
                annual_parts.append(annual_indices(daily, thresholds, dataset, model, scenario))
    annual = pd.concat(annual_parts, ignore_index=True)
    annual.to_csv(OUT / "annual_indices_audited.csv.gz", index=False, compression="gzip")
    pd.DataFrame(input_profiles).to_csv(OUT / "input_profiles.csv", index=False)

    skill_detail, skill_summary = historical_skill(obs, stations)
    skill_detail.to_csv(OUT / "historical_skill_detail.csv", index=False)
    skill_summary.to_csv(OUT / "historical_skill_summary.csv", index=False)

    station, model_changes, ensemble = change_table(annual, WINDOWS, (1995, 2014))
    station.to_csv(OUT / "station_change_sensitivity.csv", index=False)
    model_changes.to_csv(OUT / "model_regional_change_sensitivity.csv", index=False)
    ensemble.to_csv(OUT / "ensemble_change_sensitivity.csv", index=False)

    _, _, legacy = change_table(annual, LEGACY_WINDOWS, (1981, 2014))
    legacy.to_csv(OUT / "legacy_window_recomputation.csv", index=False)
    resid_detail, resid_summary = residual_bias(annual)
    resid_detail.to_csv(OUT / "residual_bias_detail.csv", index=False)
    resid_summary.to_csv(OUT / "residual_bias_summary.csv", index=False)
    preservation = change_preservation(annual)
    preservation.to_csv(OUT / "change_preservation_raw_vs_bc.csv", index=False)

    threshold_rows = [{"station": s, "p95_mm": v[0], "p99_mm": v[1]} for s, v in thresholds.items()]
    pd.DataFrame(threshold_rows).to_csv(OUT / "observed_thresholds.csv", index=False)
    registry = pd.DataFrame([{"index": i, "unit": INDEX_UNITS[i], "definition": INDEX_DESCRIPTIONS[i]}
                             for i in INDEX_ORDER])
    registry.to_csv(OUT / "index_registry.csv", index=False)

    fig_baseline_sensitivity(ensemble)
    fig_change_heatmap(ensemble)
    fig_selected_profiles(ensemble)
    fig_residual_bias(resid_detail)

    summary = {
        "observed_start": str(obs.index.min().date()),
        "observed_end": str(obs.index.max().date()),
        "station_count": len(stations),
        "model_count": len(MODELS),
        "scenario_count": len(SCENARIOS),
        "annual_rows": len(annual),
        "baseline": "1995-2014",
        "windows": WINDOWS,
        "sign_reversals": int(ensemble["sign_reversal"].sum()),
        "classification_changes": int(ensemble["classification_changed"].sum()),
        "change_signal_sign_preserved_fraction": float(preservation["sign_preserved"].mean()),
        "median_abs_change_difference_pp": float(preservation["abs_pct_difference"].replace([np.inf, -np.inf], np.nan).median()),
        "tfpw_self_test_type1_phi06": 0.383,
        "notes": [
            "TFPW p-values excluded from confirmatory manuscript claims.",
            "R50mm relative changes treated as denominator-sensitive.",
            "Bias-correction calibration/provenance not independently reproducible from supplied files.",
        ],
    }
    (OUT / "audit_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_audit_markdown(summary, skill_summary, resid_summary, ensemble, preservation)

    key = ensemble[ensemble["index"].isin(["PRCPTOT", "SDII", "Rx5day", "R99p", "CDD", "CWD", "R50mm"])]
    cols = ["scenario", "window", "index", "model_median_abs", "model_q25_abs", "model_q75_abs",
            "model_median_pct", "model_q25_pct", "model_q75_pct", "model_agreement",
            "model_classification", "obs_median_pct", "sign_reversal"]
    key[cols].to_csv(OUT / "manuscript_key_results.csv", index=False)


if __name__ == "__main__":
    main()
