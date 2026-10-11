"""Publication-oriented figures generated from reviewed result tables."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


COLORS = {"annual": "#1f4e79", "wet": "#2a9d8f", "dry": "#d97706"}
METHOD_COLORS = {"MK": "#4c78a8", "HR-MMK-3": "#f58518", "PW-MK": "#54a24b", "TFPW-MK": "#b279a2"}


def _finish(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def create_all_figures(
    output_dir: Path,
    *,
    metadata: pd.DataFrame,
    network_series: pd.DataFrame,
    network_results: pd.DataFrame,
    station_results: pd.DataFrame,
    bootstrap: pd.DataFrame,
    method_simulation: pd.DataFrame,
    fdr_simulation: pd.DataFrame,
    alpha: float,
) -> None:
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})

    fig, axes = plt.subplots(3, 1, figsize=(7.2, 8.2), sharex=False)
    for axis, period in zip(axes, ("annual", "wet", "dry")):
        series = network_series[network_series["period"] == period].sort_values("year")
        row = network_results[(network_results["period"] == period) & (network_results["method"] == "MK")].iloc[0]
        axis.plot(series["year"], series["network_mean_mm"], marker="o", ms=3, lw=1.2, color=COLORS[period])
        axis.plot(series["year"], row["intercept"] + row["slope"] * series["year"], ls="--", lw=1.4, color="#222222")
        axis.set_title(f"{period.title()}: Sen slope {row['slope']:.2f} mm/year; MK p={row['p_value']:.3f}", loc="left")
        axis.set_ylabel("Gauge mean (mm)")
        axis.grid(axis="y", alpha=0.25)
    axes[-1].set_xlabel("Period label (dry season ends in label year)")
    fig.suptitle("Equal-weight gauge-network rainfall totals", fontweight="bold")
    fig.tight_layout()
    _finish(fig, output_dir / "network_trends.png")

    fig, axis = plt.subplots(figsize=(6.3, 5.8))
    known = metadata[metadata["elevation_m"].notna()]
    missing = metadata[metadata["elevation_m"].isna()]
    scatter = axis.scatter(known["longitude"], known["latitude"], c=known["elevation_m"], cmap="viridis", s=55, edgecolor="white", linewidth=0.7)
    axis.scatter(missing["longitude"], missing["latitude"], color="#9ca3af", marker="x", s=50, linewidth=1.5, label="Elevation not supplied")
    for row in metadata.itertuples(index=False):
        axis.annotate(str(row.station_id), (row.longitude, row.latitude), xytext=(4, 3), textcoords="offset points", fontsize=7)
    axis.set_xlabel("Longitude (degrees east)")
    axis.set_ylabel("Latitude (degrees north)")
    axis.set_xlim(metadata["longitude"].min() - 0.03, metadata["longitude"].max() + 0.10)
    axis.set_ylim(metadata["latitude"].min() - 0.05, metadata["latitude"].max() + 0.08)
    axis.set_title("Rain-gauge locations (schematic; no administrative basemap)", loc="left", fontweight="bold")
    fig.colorbar(scatter, ax=axis, label="Elevation (m; missing shown uncoloured)")
    axis.legend(loc="lower left", fontsize=8, frameon=False)
    axis.grid(alpha=0.2)
    fig.tight_layout()
    _finish(fig, output_dir / "station_locations.png")

    station_ci = bootstrap[bootstrap["scope"] == "station"].copy()
    fig, axes = plt.subplots(1, 3, figsize=(11.0, 5.8), sharey=True)
    station_order = sorted(station_ci["key"].astype(str).unique())
    positions = np.arange(len(station_order))
    for axis, period in zip(axes, ("annual", "wet", "dry")):
        subset = station_ci[station_ci["period"] == period].set_index("key").reindex(station_order)
        x = subset["estimate"].to_numpy()
        low = subset["ci_low"].to_numpy()
        high = subset["ci_high"].to_numpy()
        axis.errorbar(x, positions, xerr=[x - low, high - x], fmt="o", color=COLORS[period], ecolor="#7a7a7a", capsize=2, ms=4)
        axis.axvline(0, color="#333333", lw=0.8)
        axis.set_title(period.title())
        axis.set_xlabel("Sen slope (mm/year)")
        axis.grid(axis="x", alpha=0.2)
    axes[0].set_yticks(positions, station_order)
    axes[0].invert_yaxis()
    fig.suptitle("Station trends with 95% residual-block bootstrap intervals", fontweight="bold")
    fig.tight_layout()
    _finish(fig, output_dir / "station_slope_intervals.png")

    type_i = method_simulation[method_simulation["metric"] == "type_i_error"]
    fig, axis = plt.subplots(figsize=(7.0, 4.6))
    for method, group in type_i.groupby("method", sort=False):
        group = group.sort_values("phi")
        axis.plot(group["phi"], group["estimate"], marker="o", label=method, color=METHOD_COLORS.get(method))
        axis.fill_between(group["phi"], group["ci_low"], group["ci_high"], color=METHOD_COLORS.get(method), alpha=0.1)
    axis.axhline(alpha, color="#222222", ls="--", label=f"Nominal {alpha:.2f}")
    axis.set(xlabel="AR(1) phi", ylabel="Empirical Type I error", ylim=(0, max(0.15, float(type_i["ci_high"].max()) * 1.1)))
    axis.set_title("Scenario calibration for a short record", loc="left", fontweight="bold")
    axis.legend(ncol=3, fontsize=8)
    axis.grid(alpha=0.2)
    fig.tight_layout()
    _finish(fig, output_dir / "simulation_type_i.png")

    power = method_simulation[method_simulation["metric"] == "power"]
    fig, axes = plt.subplots(1, len(sorted(power["standardized_slope"].unique())), figsize=(11.0, 3.7), sharey=True)
    axes = np.atleast_1d(axes)
    for axis, (slope, subset) in zip(axes, power.groupby("standardized_slope", sort=True)):
        for method, group in subset.groupby("method", sort=False):
            group = group.sort_values("phi")
            axis.plot(group["phi"], group["estimate"], marker="o", label=method, color=METHOD_COLORS.get(method))
        axis.set_title(f"Slope={slope:g} SD/year")
        axis.set_xlabel("AR(1) phi")
        axis.grid(alpha=0.2)
    axes[0].set_ylabel("Empirical power")
    axes[-1].legend(fontsize=8)
    fig.suptitle("Scenario power by method", fontweight="bold")
    fig.tight_layout()
    _finish(fig, output_dir / "simulation_power.png")

    fig, axis = plt.subplots(figsize=(6.6, 4.2))
    positions = np.arange(len(fdr_simulation))
    axis.bar(positions, fdr_simulation["fdr"], color=[METHOD_COLORS.get(method, "#777777") for method in fdr_simulation["method"]])
    axis.errorbar(positions, fdr_simulation["fdr"], yerr=[fdr_simulation["fdr"] - fdr_simulation["ci_low"], fdr_simulation["ci_high"] - fdr_simulation["fdr"]], fmt="none", ecolor="#222222", capsize=3)
    axis.axhline(alpha, color="#222222", ls="--")
    axis.set_xticks(positions, fdr_simulation["method"], rotation=20, ha="right")
    axis.set_ylabel("FDR = mean FDP (complete null)")
    axis.set_title("BH behavior in the prespecified correlated scenario", loc="left", fontweight="bold")
    axis.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    _finish(fig, output_dir / "simulation_fdr.png")
