"""Publication figures.

Conventions: no title inside figures (captions carry the title), panel labels
(a), (b), ... in the upper-left corner, Okabe-Ito colour-blind-safe palette,
units on every axis, 300 dpi PNG plus vector PDF.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import TwoSlopeNorm  # noqa: E402

from .data import Station  # noqa: E402

OKABE_ITO: list[str] = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#000000"]
MONTH_LABELS: list[str] = list("JFMAMJJASOND")
METHOD_COLOURS: dict[str, str] = {"nearest": "#0072B2", "bilinear": "#E69F00", "idw": "#009E73"}
VAR_LABELS: dict[str, str] = {
    "tmax": "Tmax (\u00b0C)", "tmin": "Tmin (\u00b0C)", "ea": "e$_a$ (kPa)", "u2": "u$_2$ (m s$^{-1}$)",
    "rs": "R$_s$ (MJ m$^{-2}$ d$^{-1}$)", "eto": "ETo (mm d$^{-1}$)", "pr": "P (mm month$^{-1}$)",
}


def _style() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
        "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7, "axes.spines.top": False,
        "axes.spines.right": False, "savefig.dpi": 300, "figure.dpi": 100,
    })


def _label(ax: plt.Axes, i: int, text: str = "") -> None:
    """Panel letter (plus optional short heading) above the axes, never over data."""
    ax.set_title(f"({chr(97 + i)}) {text}".strip(), loc="left", fontsize=7.5, fontweight="bold", pad=3)


def _panel_heading(ax: plt.Axes, i: int, name: str) -> None:
    """Panel letter and station name above the plotting area (never over data)."""
    ax.set_title(f"({chr(97 + i)}) {name}", loc="left", fontsize=7.5, fontweight="bold", pad=3)


def _save(fig: plt.Figure, path: Path) -> list[Path]:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path.with_suffix(".png"), bbox_inches="tight")
    fig.savefig(path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)
    return [path.with_suffix(".png"), path.with_suffix(".pdf")]


def _station_axes(n: int, ncols: int = 4, w: float = 7.2, h_row: float = 1.75) -> tuple[plt.Figure, np.ndarray]:
    nrows = int(np.ceil((n + 1) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(w, h_row * nrows), constrained_layout=True)
    return fig, np.atleast_1d(axes).ravel()


def plot_wind_homogeneity(unmasked: pd.DataFrame, masked: pd.DataFrame, actions: pd.DataFrame,
                          stations: tuple[Station, ...], path: Path) -> list[Path]:
    """Annual mean wind (archive units) with masked segments and detected breaks."""
    _style()
    fig, axes = _station_axes(len(stations))
    for i, s in enumerate(stations):
        ax = axes[i]
        def ann(df: pd.DataFrame) -> pd.Series:
            g = df[df["stncode"] == s.code].groupby("year")["wind_raw"]
            return g.mean().where(g.count() >= 10)
        a_all, a_keep = ann(unmasked), ann(masked)
        ax.plot(a_all.index, a_all.values, color="0.6", lw=1.0, ls="--", marker="o", ms=2, label="masked segment")
        ax.plot(a_keep.index, a_keep.values, color=OKABE_ITO[0], lw=1.2, marker="o", ms=2.5, label="retained")
        for _, r in actions[actions["stncode"] == s.code].iterrows():
            ax.axvline(r["break_after"] + 0.5, color=OKABE_ITO[3], lw=0.9)
        ax.set_xlim(1978, 2008)
        if i % 4 == 0:
            ax.set_ylabel("Annual mean wind\n(archive units)")
        _panel_heading(ax, i, s.name)
    leg = axes[len(stations)]
    leg.axis("off")
    leg.plot([], [], color=OKABE_ITO[0], marker="o", ms=2.5, label="Retained annual mean")
    leg.plot([], [], color="0.6", ls="--", marker="o", ms=2, label="Masked segment")
    leg.plot([], [], color=OKABE_ITO[3], label="Accepted relative break")
    leg.legend(loc="center", frameon=False)
    for ax in axes[len(stations) + 1:]:
        ax.axis("off")
    return _save(fig, path)


def plot_reference_envelope(ref: pd.DataFrame, stations: tuple[Station, ...], path: Path) -> list[Path]:
    """Monthly climatology of station PM-ETo for each reference-ensemble member."""
    _style()
    fig, axes = _station_axes(len(stations))
    members = sorted(ref["member"].unique())
    colours = {m: OKABE_ITO[j] for j, m in enumerate(members)}
    for i, s in enumerate(stations):
        ax = axes[i]
        clim = ref[ref["stncode"] == s.code].groupby(["member", "month"])["eto_mm_day"].mean().unstack("member")
        ax.fill_between(clim.index, clim.min(axis=1), clim.max(axis=1), color="0.85", lw=0)
        for m in members:
            ax.plot(clim.index, clim[m], color=colours[m], lw=1.0)
        ax.set_xticks(range(1, 13), MONTH_LABELS)
        ax.set_ylim(2.0, 7.0)
        if i % 4 == 0:
            ax.set_ylabel("ETo (mm d$^{-1}$)")
        _panel_heading(ax, i, s.name)
    leg = axes[len(stations)]
    leg.axis("off")
    for m in members:
        unit, ang = m.split("|")
        ang_lab = {"FAO56": "FAO-56 \u00c5ngstr\u00f6m", "GloverMcCulloch": "Glover\u2013McCulloch"}[ang]
        leg.plot([], [], color=colours[m], label=f"wind in {unit.replace('ms-1', 'm s$^{-1}$')}s, {ang_lab}".replace("knots", "knots").replace("m s$^{-1}$s", "m s$^{-1}$"))
    leg.fill_between([], [], [], color="0.85", label="Ensemble range")
    leg.legend(loc="center", frameon=False)
    for ax in axes[len(stations) + 1:]:
        ax.axis("off")
    return _save(fig, path)


def plot_reference_sensitivity(sens: pd.DataFrame, path: Path) -> list[Path]:
    """Monthly effect (%) of each structural choice on station PM-ETo.

    ``sens`` columns: month, factor, median, lo, hi (across stations).
    """
    _style()
    fig, ax = plt.subplots(figsize=(3.5, 2.4), constrained_layout=True)
    for j, (fac, g) in enumerate(sens.groupby("factor", sort=False)):
        off = (j - 0.5) * 0.18
        ax.errorbar(g["month"] + off, g["median"], yerr=[g["median"] - g["lo"], g["hi"] - g["median"]],
                    fmt="o", ms=3, lw=0.9, capsize=1.5, color=OKABE_ITO[j], label=fac)
    ax.axhline(0, color="0.5", lw=0.6)
    ax.set_xticks(range(1, 13), MONTH_LABELS)
    ax.set_xlabel("Month")
    ax.set_ylabel("Change in station ETo (%)")
    ax.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=1)
    return _save(fig, path)


def plot_input_metrics(m: pd.DataFrame, path: Path) -> list[Path]:
    """Station-wise nominal accuracy of PM inputs (adapted from Tran et al., 2026, Fig. 7).

    ``m`` columns: variable, method, stncode, r2, mbe, pbias, rmse.
    """
    _style()
    variables = [v for v in ("tmax", "tmin", "ea", "u2", "rs") if v in set(m["variable"])]
    cols = [("r2", "r$^2$ (\u2013)"), ("mbe", "Bias"), ("pbias", "PBIAS (%)"), ("rmse", "RMSE")]
    methods = [x for x in ("nearest", "bilinear", "idw") if x in set(m["method"])]
    fig, axes = plt.subplots(len(variables), 4, figsize=(7.2, 1.35 * len(variables)), constrained_layout=True, squeeze=False)
    rng = np.random.default_rng(1)
    k = 0
    for i, v in enumerate(variables):
        for j, (c, lab) in enumerate(cols):
            ax = axes[i, j]
            for x, meth in enumerate(methods):
                vals = m[(m["variable"] == v) & (m["method"] == meth)][c].to_numpy(float)
                ax.scatter(x + rng.uniform(-0.12, 0.12, vals.size), vals, s=9, color=METHOD_COLOURS[meth], alpha=0.85, lw=0)
                ax.plot([x - 0.25, x + 0.25], [np.nanmean(vals)] * 2, color="k", lw=1.0)
            if c in ("mbe", "pbias"):
                ax.axhline(0, color="0.5", lw=0.6, ls="--")
            ax.set_xticks(range(len(methods)), methods if i == len(variables) - 1 else [""] * len(methods))
            if j == 0:
                ax.set_ylabel(VAR_LABELS[v])
            _label(ax, k, lab if i == 0 else "")
            k += 1
    return _save(fig, path)


def plot_bias_heatmaps(bias: pd.DataFrame, stations: tuple[Station, ...], path: Path) -> list[Path]:
    """Mean bias by station (south to north) and calendar month (Hovmoller-style).

    ``bias`` columns: variable, stncode, month, mbe.
    """
    _style()
    order = [s.code for s in sorted(stations, key=lambda s: s.lat)]
    names = {s.code: s.name for s in stations}
    variables = [v for v in ("eto", "rs", "ea", "u2", "tmax", "tmin") if v in set(bias["variable"])]
    ncols = 3
    nrows = int(np.ceil(len(variables) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(7.2, 2.1 * nrows), constrained_layout=True, squeeze=False)
    for i, v in enumerate(variables):
        ax = axes.ravel()[i]
        tab = bias[bias["variable"] == v].pivot_table(index="stncode", columns="month", values="mbe").reindex(order)
        lim = float(np.nanmax(np.abs(tab.to_numpy()))) or 1.0
        im = ax.imshow(tab.to_numpy(), aspect="auto", cmap="RdBu_r", norm=TwoSlopeNorm(0.0, -lim, lim), origin="lower")
        ax.set_xticks(range(12), MONTH_LABELS)
        ax.set_yticks(range(len(order)), [names[c] for c in order] if i % ncols == 0 else [""] * len(order))
        cb = fig.colorbar(im, ax=ax, shrink=0.9, pad=0.02)
        cb.set_label(f"Bias, {VAR_LABELS[v]}")
        _label(ax, i)
    for ax in axes.ravel()[len(variables):]:
        ax.axis("off")
    return _save(fig, path)


def plot_annual_scatter(ann: pd.DataFrame, path: Path) -> list[Path]:
    """Station-year annual totals, observed vs AgERA5 per extraction method
    (adapted from Soulis et al., 2025, Figs 3-4).

    ``ann`` columns: variable ('pr' | 'eto'), method, obs, est.
    """
    _style()
    variables = [v for v in ("pr", "eto") if v in set(ann["variable"])]
    methods = [x for x in ("nearest", "bilinear", "idw") if x in set(ann["method"])]
    fig, axes = plt.subplots(len(variables), len(methods), figsize=(7.2, 2.3 * len(variables)), constrained_layout=True, squeeze=False)
    k = 0
    for i, v in enumerate(variables):
        d = ann[ann["variable"] == v]
        lo = float(np.nanmin(d[["obs", "est"]].to_numpy())) * 0.95
        hi = float(np.nanmax(d[["obs", "est"]].to_numpy())) * 1.05
        for j, meth in enumerate(methods):
            ax = axes[i, j]
            g = d[d["method"] == meth].dropna(subset=["obs", "est"])
            ax.scatter(g["obs"], g["est"], s=7, color=METHOD_COLOURS[meth], alpha=0.7, lw=0)
            ax.plot([lo, hi], [lo, hi], color="k", lw=0.7, ls="--")
            if len(g) > 2:
                b, a = np.polyfit(g["obs"], g["est"], 1)
                ax.plot([lo, hi], [a + b * lo, a + b * hi], color=OKABE_ITO[3], lw=1.0)
                r2 = np.corrcoef(g["obs"], g["est"])[0, 1] ** 2
                rmse = np.sqrt(np.mean((g["est"] - g["obs"]) ** 2))
                sign = "+" if a >= 0 else "\u2212"
                ax.text(0.97, 0.03, f"y = {b:.2f}x {sign} {abs(a):.0f}\nr$^2$ = {r2:.2f}\nRMSE = {rmse:.0f} mm",
                        transform=ax.transAxes, ha="right", va="bottom", fontsize=6.5)
            ax.set_xlim(lo, hi)
            ax.set_ylim(lo, hi)
            ax.set_aspect("equal")
            unit = "P" if v == "pr" else "ETo"
            ax.set_xlabel(f"Station annual {unit} (mm)")
            ax.set_ylabel(f"AgERA5 ({meth}) annual {unit} (mm)")
            _label(ax, k)
            k += 1
    return _save(fig, path)


def plot_seasonal_cycle(ref_clim: pd.DataFrame, ag_clim: pd.DataFrame, stations: tuple[Station, ...], path: Path) -> list[Path]:
    """Station reference envelope vs AgERA5 native and AgERA5-input PM climatologies.

    ``ref_clim``: stncode, month, lo, hi. ``ag_clim``: stncode, month, native, pm.
    """
    _style()
    fig, axes = _station_axes(len(stations))
    for i, s in enumerate(stations):
        ax = axes[i]
        r = ref_clim[ref_clim["stncode"] == s.code].sort_values("month")
        a = ag_clim[ag_clim["stncode"] == s.code].sort_values("month")
        ax.fill_between(r["month"], r["lo"], r["hi"], color="0.8", lw=0)
        ax.plot(a["month"], a["native"], color=OKABE_ITO[3], lw=1.2)
        ax.plot(a["month"], a["pm"], color=OKABE_ITO[0], lw=1.0, ls="--")
        ax.set_xticks(range(1, 13), MONTH_LABELS)
        if i % 4 == 0:
            ax.set_ylabel("ETo (mm d$^{-1}$)")
        _panel_heading(ax, i, s.name)
    leg = axes[len(stations)]
    leg.axis("off")
    leg.fill_between([], [], [], color="0.8", label="Station reference envelope")
    leg.plot([], [], color=OKABE_ITO[3], label="AgERA5 v2.0 native ETo")
    leg.plot([], [], color=OKABE_ITO[0], ls="--", label="PM from AgERA5 monthly inputs")
    leg.legend(loc="center", frameon=False)
    for ax in axes[len(stations) + 1:]:
        ax.axis("off")
    return _save(fig, path)


def plot_attribution(summary: pd.DataFrame, path: Path) -> list[Path]:
    """Seasonal mean input contributions to the ETo difference: Shapley vs first-order Taylor.

    ``summary`` columns: season, method ('Shapley' | 'Taylor'), variable, mean, lo, hi.
    """
    _style()
    seasons = list(dict.fromkeys(summary["season"]))
    variables = ["tmax", "tmin", "ea", "u2", "rs"]
    fig, axes = plt.subplots(1, len(seasons), figsize=(7.2, 2.4), constrained_layout=True, sharey=True, squeeze=False)
    for i, sea in enumerate(seasons):
        ax = axes[0, i]
        for j, (meth, mk) in enumerate((("Shapley", "o"), ("Taylor", "s"))):
            g = summary[(summary["season"] == sea) & (summary["method"] == meth)].set_index("variable").reindex(variables)
            x = np.arange(len(variables)) + (j - 0.5) * 0.25
            ax.errorbar(x, g["mean"], yerr=[g["mean"] - g["lo"], g["hi"] - g["mean"]], fmt=mk, ms=3.5, lw=0.9,
                        capsize=1.5, color=OKABE_ITO[j], label=meth if i == 0 else None)
        ax.axhline(0, color="0.5", lw=0.6)
        ax.set_xticks(range(len(variables)), ["Tmax", "Tmin", "e$_a$", "u$_2$", "R$_s$"])
        if i == 0:
            ax.set_ylabel("Contribution to \u0394ETo (mm d$^{-1}$)")
        _panel_heading(ax, i, f"{sea} season")
    axes[0, 0].legend(frameon=False, loc="lower left")
    return _save(fig, path)


def plot_propagation(mc: pd.DataFrame, path: Path) -> list[Path]:
    """Normalised ETo uncertainty from random input errors by calendar month.

    ``mc`` columns: month and median snorm_* columns.
    """
    _style()
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.4), constrained_layout=True)
    series = [("snorm_mc_corr", "Monte Carlo, correlated errors", OKABE_ITO[0], "-"),
              ("snorm_mc_indep", "Monte Carlo, independent errors", OKABE_ITO[1], "-"),
              ("snorm_taylor_corr", "Taylor, correlated errors", OKABE_ITO[0], ":"),
              ("snorm_taylor_indep", "Taylor, independent errors", OKABE_ITO[1], ":")]
    for col, lab, c, ls in series:
        axes[0].plot(mc["month"], 100 * mc[col], color=c, ls=ls, lw=1.2, marker="o", ms=2.5, label=lab)
    axes[0].set_xticks(range(1, 13), MONTH_LABELS)
    axes[0].set_ylabel("\u03c3$_{norm}$ of ETo (%)")
    axes[0].legend(frameon=False, fontsize=6.5)
    axes[1].plot(mc["month"], mc["snorm_taylor_corr"] / mc["snorm_mc_corr"], color=OKABE_ITO[0], marker="o", ms=2.5, label="correlated")
    axes[1].plot(mc["month"], mc["snorm_taylor_indep"] / mc["snorm_mc_indep"], color=OKABE_ITO[1], marker="o", ms=2.5, label="independent")
    axes[1].axhline(1, color="0.5", lw=0.6, ls="--")
    axes[1].set_xticks(range(1, 13), MONTH_LABELS)
    axes[1].set_ylabel("\u03c3$_{Taylor}$ / \u03c3$_{MC}$ (\u2013)")
    axes[1].legend(frameon=False)
    for i, ax in enumerate(axes):
        _label(ax, i)
    return _save(fig, path)


def plot_nir_and_adjustment(nir: pd.DataFrame, cv: pd.DataFrame, path: Path) -> list[Path]:
    """(a) Station-wise split of the annual NIR difference into ETo and rainfall parts;
    (b) RMSE of monthly ETo before and after leave-one-station-out adjustment.

    ``nir`` columns: station, phi_eto, phi_p, delta (mm yr-1).
    ``cv`` columns: station, method, rmse_raw, rmse_adj.
    """
    _style()
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6), constrained_layout=True)
    x = np.arange(len(nir))
    axes[0].bar(x - 0.2, nir["phi_eto"], width=0.4, color=OKABE_ITO[3], label="ETo part")
    axes[0].bar(x + 0.2, nir["phi_p"], width=0.4, color=OKABE_ITO[0], label="Rainfall part")
    axes[0].scatter(x, nir["delta"], color="k", s=12, zorder=3, label="Total difference")
    axes[0].axhline(0, color="0.5", lw=0.6)
    axes[0].set_xticks(x, nir["station"], rotation=45, ha="right")
    axes[0].set_ylabel("\u0394NIR, AgERA5 \u2212 station (mm yr$^{-1}$)")
    axes[0].legend(frameon=False, fontsize=6.5)
    for j, (meth, g) in enumerate(cv.groupby("method")):
        xx = np.arange(len(g)) + (j - 0.5) * 0.3
        axes[1].scatter(xx, g["rmse_raw"], marker="o", facecolor="none", edgecolor="0.4", s=16, label="raw" if j == 0 else None)
        axes[1].scatter(xx, g["rmse_adj"], marker="o", color=OKABE_ITO[j + 1], s=16, label=f"{meth} (LOSO)")
        for a, b, xi in zip(g["rmse_raw"], g["rmse_adj"], xx):
            axes[1].plot([xi, xi], [a, b], color="0.7", lw=0.6)
    axes[1].set_xticks(np.arange(cv["station"].nunique()), cv["station"].unique(), rotation=45, ha="right")
    axes[1].set_ylabel("RMSE of monthly ETo (mm d$^{-1}$)")
    axes[1].legend(frameon=False, fontsize=6.5)
    for i, ax in enumerate(axes):
        _label(ax, i)
    return _save(fig, path)
