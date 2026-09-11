"""
figures.py — Figures 3-7 for the manuscript.

Numbering follows the revised article structure:

    Figure 1  study area and rain-gauge network            (prepared separately)
    Figure 2  calibration-independent validation framework (prepared separately)
    Figure 3  observed rainfall characteristics in the two periods
    Figure 4  raw versus QDM performance, independent validation
    Figure 5  variability of the correction effect across models and stations
    Figure 6  individual-model spread versus the unweighted MME
    Figure 7  mechanism underlying the change in error metrics

Every value plotted is read from the files written by evaluate.py, so the
figures cannot drift from evaluation_results.xlsx.

    python figures.py --config config.yaml
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

import io_layer
from provenance import Provenance

DPI = 600
MODEL_COLOURS = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00"]
C_CAL, C_VAL = "#1F5FA9", "#D55E00"
C_RAW, C_QDM, C_REF = "#B22222", "#1F5FA9", "#3A3A3A"
C_GOOD, C_BAD, C_NEUT = "#2E7D32", "#B22222", "#7A7A7A"
MODEL_SHORT = {
    "ACCESS-ESM1-5": "ACCESS",
    "CESM2": "CESM2",
    "CanESM5": "CanESM5",
    "EC-Earth3": "EC-Earth3",
    "MIROC6": "MIROC6",
}


def _register_cordia_new():
    """Make Cordia New available to Matplotlib even when the font cache is stale."""
    for font_dir in (Path("C:/Windows/Fonts"), Path.home() / "AppData/Local/Microsoft/Windows/Fonts"):
        if font_dir.exists():
            for font_path in font_dir.glob("cordia*.ttf"):
                font_manager.fontManager.addfont(str(font_path))


_register_cordia_new()

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Cordia New", "Arial", "DejaVu Sans"],
    "mathtext.fontset": "dejavusans", "font.size": 11,
    "axes.titlesize": 11, "axes.labelsize": 11,
    "xtick.labelsize": 9.5, "ytick.labelsize": 9.5,
    "legend.fontsize": 9.5, "legend.frameon": False,
    "axes.linewidth": 0.7, "xtick.direction": "out", "ytick.direction": "out",
    "axes.unicode_minus": False,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.linestyle": ":", "grid.linewidth": 0.45,
    "grid.alpha": 0.5, "grid.color": "#9E9E9E", "lines.linewidth": 1.1,
    "savefig.dpi": DPI, "savefig.bbox": "tight", "savefig.pad_inches": 0.05,
    "figure.dpi": 110, "pdf.fonttype": 42, "ps.fonttype": 42,
})
MM = 1 / 25.4
W2 = 190 * MM


def short_model(model):
    return MODEL_SHORT.get(str(model), str(model).replace("-historical", ""))


def ptitle(ax, tag, text="", size=10.8):
    ax.set_title(f"({tag})" + (f"  {text}" if text else ""), loc="left",
                 fontsize=size, fontweight="bold", pad=7)


def save(fig, d: Path, stem: str):
    fig.patch.set_facecolor("white")
    for ext in ("png", "pdf"):
        fig.savefig(d / f"{stem}.{ext}")
    plt.close(fig)
    print(f"    -> {stem}.png / .pdf")


def model_legend(fig, models, y=0.0, ncol=5):
    h = [Line2D([], [], marker="o", ls="", markersize=4.6,
                markerfacecolor=MODEL_COLOURS[i % 5], markeredgecolor="white",
                markeredgewidth=0.35, label=m)
         for i, m in enumerate(sorted(models))]
    return fig.legend(handles=h, loc="lower center", ncol=ncol,
                      bbox_to_anchor=(0.5, y), handletextpad=0.35,
                      columnspacing=1.1)


def load_pairs(metrics, variant, period, a="raw", b="QDM"):
    d = metrics[(metrics.variant == variant) & (metrics.period == period)]
    A = d[d.dataset == a].set_index(["model", "station"]).sort_index()
    B = d[d.dataset == b].set_index(["model", "station"]).sort_index()
    ix = A.index.intersection(B.index)
    return A.loc[ix], B.loc[ix]


def spearman_fallback(x, y):
    """Return Spearman rho and p-value when SciPy is unavailable."""
    try:
        from scipy.stats import spearmanr
        return spearmanr(x, y)
    except Exception:
        xr = pd.Series(x).rank(method="average").to_numpy(float)
        yr = pd.Series(y).rank(method="average").to_numpy(float)
        rho = float(np.corrcoef(xr, yr)[0, 1])
        return rho, np.nan


def paired_scatter(ax, x, y, models, lower_is_better, label, absolute=False):
    x = np.abs(np.asarray(x, float)) if absolute else np.asarray(x, float)
    y = np.abs(np.asarray(y, float)) if absolute else np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y, models = x[ok], y[ok], np.asarray(models)[ok]
    lo, hi = float(min(x.min(), y.min())), float(max(x.max(), y.max()))
    pad = 0.06 * (hi - lo if hi > lo else 1.0)
    lo, hi = lo - pad, hi + pad
    good = ([lo, hi, hi], [lo, hi, lo]) if lower_is_better else ([lo, hi, lo], [lo, hi, hi])
    bad = ([lo, hi, lo], [lo, hi, hi]) if lower_is_better else ([lo, hi, hi], [lo, hi, lo])
    ax.fill(*good, color=C_GOOD, alpha=0.06, lw=0, zorder=0)
    ax.fill(*bad, color=C_BAD, alpha=0.05, lw=0, zorder=0)
    ax.plot([lo, hi], [lo, hi], color=C_REF, lw=0.9, ls="--", zorder=2)
    for i, m in enumerate(sorted(set(models))):
        s = models == m
        ax.scatter(x[s], y[s], s=17, facecolor=MODEL_COLOURS[i % 5],
                   edgecolor="white", linewidth=0.35, alpha=0.92, zorder=3)
    n = int((y < x).sum() if lower_is_better else (y > x).sum())
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi); ax.set_aspect("equal")
    ax.set_xlabel(f"Raw — {label}"); ax.set_ylabel(f"QDM — {label}")
    ax.text(0.035, 0.955, f"{n}/{len(x)} improved", transform=ax.transAxes,
            va="top", fontsize=9,
            bbox=dict(boxstyle="round,pad=0.24", fc="white", ec="#BDBDBD", lw=0.5))


# ═══════════════════════════════════════════════════════════════════════════
#  Figure 3 — observed rainfall characteristics in the two periods
# ═══════════════════════════════════════════════════════════════════════════

def figure3(obs: pd.DataFrame, tiers: pd.DataFrame, cfg: dict, d: Path):
    cal, val = cfg["periods"]["calibration"], cfg["periods"]["validation"]
    thr = float(cfg["data"]["wet_threshold_mm"])
    yr = obs.index.year
    mcal = (yr >= cal[0]) & (yr <= cal[1])
    mval = (yr >= val[0]) & (yr <= val[1])
    reg = obs.mean(axis=1)

    fig = plt.figure(figsize=(W2, 0.42 * W2))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.05, 1.12, 1.0], wspace=0.62)

    ax = fig.add_subplot(gs[0, 0])
    for mask, c, lab, ls in ((mcal, C_CAL, f"Calibration {cal[0]}–{cal[1]}", "-"),
                             (mval, C_VAL, f"Validation {val[0]}–{val[1]}", "--")):
        s = reg[mask].resample("MS").sum(min_count=25)
        clim = s.groupby(s.index.month).mean()
        ax.plot(clim.index, clim.values, color=c, ls=ls, marker="o",
                markersize=3.4, label=lab)
    ax.set_xticks(range(1, 13, 2)); ax.set_xlabel("Month", labelpad=5)
    ax.set_ylabel("Rainfall (mm month$^{-1}$)")
    ax.legend(loc="upper left", handlelength=1.8, borderaxespad=0.2)
    ptitle(ax, "a", "Monthly climatology")

    ax = fig.add_subplot(gs[0, 1])
    ann = reg.resample("YS").sum(min_count=300)
    yrs = ann.index.year.to_numpy()
    cols = [C_CAL if y <= cal[1] else C_VAL for y in yrs]
    ax.bar(yrs, ann.to_numpy(float), color=cols, edgecolor="white",
           linewidth=0.4, width=0.78)
    ax.axvline(cal[1] + 0.5, color="k", lw=1.0, ls="--")
    ax.set_xlabel("Year", labelpad=5); ax.set_ylabel("Annual rainfall (mm)")
    ax.legend(handles=[Patch(facecolor=C_CAL, label="Calibration"),
                       Patch(facecolor=C_VAL, label="Validation")],
              loc="upper left", ncol=1, fontsize=9, borderaxespad=0.2)
    ax.set_ylim(0, 1750)
    ptitle(ax, "b", "Regional-mean annual rainfall")

    ax = fig.add_subplot(gs[0, 2])
    tier = dict(zip(tiers.station.astype(str), tiers.tier))
    wf_c = {s: float((obs[s][mcal] >= thr).mean()) for s in obs.columns}
    wf_v = {s: float((obs[s][mval] >= thr).mean()) for s in obs.columns}
    mk = {"A": "o", "B": "s", "C": "^"}
    fc = {"A": C_QDM, "B": "#7E9CBD", "C": "#BDBDBD"}
    for tname in ("A", "B", "C"):
        ss = [s for s in obs.columns if tier.get(str(s)) == tname]
        if ss:
            ax.scatter([wf_c[s] for s in ss], [wf_v[s] for s in ss], s=28,
                       marker=mk[tname], facecolor=fc[tname], edgecolor="k",
                       linewidth=0.45, label=f"Tier {tname}", zorder=3)
    lo, hi = 0.15, 0.70
    ax.plot([lo, hi], [lo, hi], color=C_REF, lw=0.9, ls="--", zorder=2)
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi); ax.set_aspect("equal")
    ax.set_xlabel("Wet-day frequency, calibration", labelpad=5)
    ax.set_ylabel("Wet-day frequency, validation", labelpad=6)
    ax.legend(loc="upper left", fontsize=9, borderaxespad=0.2)
    ptitle(ax, "c", "Wet-day frequency")

    fig.suptitle("Observed rainfall characteristics by analysis period",
                 y=0.995, fontsize=12, fontweight="bold")
    fig.subplots_adjust(left=0.065, right=0.985, bottom=0.16, top=0.83)
    save(fig, d, "Figure3_observed_periods")


# ═══════════════════════════════════════════════════════════════════════════
#  Figure 4 — raw versus QDM performance
# ═══════════════════════════════════════════════════════════════════════════

def figure4(metrics: pd.DataFrame, d: Path):
    a, b = load_pairs(metrics, "primary", "validation")
    models = a.index.get_level_values("model").to_numpy()
    specs = [("PBIAS", "|PBIAS| (%)", True, True),
             ("KS_D", "Kolmogorov–Smirnov $D$", True, False),
             ("q99_relbias_pct", "|$q_{99}$ rel. bias| (%)", True, True),
             ("mRMSE", "RMSE (mm month$^{-1}$)", True, False),
             ("mNSE", "NSE", False, False),
             ("mKGE", "KGE", False, False)]
    fig = plt.figure(figsize=(W2, 0.78 * W2))
    gs = fig.add_gridspec(2, 3, hspace=0.72, wspace=0.62)
    for k, (col, lab, low, ab) in enumerate(specs):
        ax = fig.add_subplot(gs[k // 3, k % 3])
        paired_scatter(ax, a[col].to_numpy(float), b[col].to_numpy(float),
                       models, low, lab, absolute=ab)
        ptitle(ax, "abcdef"[k])
    model_legend(fig, set(models), y=0.025)
    fig.suptitle("Raw versus QDM performance during independent validation",
                 y=0.985, fontsize=12, fontweight="bold")
    fig.subplots_adjust(left=0.075, right=0.985, bottom=0.155, top=0.90)
    save(fig, d, "Figure4_raw_vs_QDM")


# ═══════════════════════════════════════════════════════════════════════════
#  Figure 5 — variability across models and stations
# ═══════════════════════════════════════════════════════════════════════════

def figure5(metrics: pd.DataFrame, d: Path):
    a, b = load_pairs(metrics, "primary", "validation")
    panels = [("mRMSE", "$\\Delta$ RMSE (mm month$^{-1}$)", False),
              ("q99_relbias_pct", "$\\Delta$ |$q_{99}$ rel. bias| (%)", True),
              ("PBIAS", "$\\Delta$ |PBIAS| (%)", True)]
    fig = plt.figure(figsize=(W2, 0.58 * W2))
    gs = fig.add_gridspec(
        1, 6, width_ratios=[1, 0.035, 1, 0.035, 1, 0.035], wspace=0.42
    )
    for k, (col, lab, ab) in enumerate(panels):
        x = a[col].abs() if ab else a[col]
        y = b[col].abs() if ab else b[col]
        delta = (y - x).unstack("model")
        delta.index = delta.index.astype(str)
        M = delta.to_numpy(float)
        lim = float(np.nanmax(np.abs(M)))
        ax = fig.add_subplot(gs[0, 2 * k])
        cax = fig.add_subplot(gs[0, 2 * k + 1])
        im = ax.imshow(M, cmap="RdBu_r", vmin=-lim, vmax=lim, aspect="auto")
        ax.set_xticks(range(delta.shape[1]))
        ax.set_xticklabels([short_model(c) for c in delta.columns],
                           rotation=35, ha="right", fontsize=8.2)
        ax.set_yticks(range(delta.shape[0]))
        ax.set_yticklabels(delta.index, fontsize=8.2)
        if k > 0:
            ax.tick_params(axis="y", labelleft=False)
        ax.grid(False)
        ax.tick_params(axis="both", length=2.8, pad=2)
        for i in range(M.shape[0]):
            for j in range(M.shape[1]):
                if np.isfinite(M[i, j]):
                    ax.text(j, i, f"{M[i, j]:.0f}", ha="center", va="center",
                            fontsize=7.2,
                            color="white" if abs(M[i, j]) > 0.62 * lim else "#303030")
        cb = fig.colorbar(im, cax=cax)
        cb.ax.tick_params(labelsize=8.2, length=2.5, pad=2)
        ptitle(ax, "abc"[k], lab, size=10.5)
    fig.suptitle("Station and model variability in QDM performance change",
                 y=0.985, fontsize=12, fontweight="bold")
    fig.subplots_adjust(left=0.070, right=0.985, bottom=0.205, top=0.865)
    save(fig, d, "Figure5_station_model_variability")


# ═══════════════════════════════════════════════════════════════════════════
#  Figure 6 — individual-model spread versus the unweighted MME
# ═══════════════════════════════════════════════════════════════════════════

def figure6(metrics: pd.DataFrame, mme: pd.DataFrame, d: Path):
    fig = plt.figure(figsize=(W2, 0.52 * W2))
    gs = fig.add_gridspec(1, 2, wspace=0.28)
    yvals = metrics[(metrics.variant == "primary") & (metrics.period == "validation")
                    & (metrics.dataset.isin(["raw", "QDM"]))]["mRMSE"].dropna()
    ylo, yhi = float(yvals.min()), float(yvals.max())
    ypad = 0.12 * (yhi - ylo if yhi > ylo else 1.0)
    for k, dsname in enumerate(("raw", "QDM")):
        m = metrics[(metrics.variant == "primary") & (metrics.period == "validation")
                    & (metrics.dataset == dsname)]
        e = mme[(mme.variant == "primary") & (mme.period == "validation")
                & (mme.dataset == dsname)].set_index("station")
        stations = sorted(m.station.unique())
        data = [m[m.station == s]["mRMSE"].dropna().to_numpy(float) for s in stations]
        ax = fig.add_subplot(gs[0, k])
        bp = ax.boxplot(data, widths=0.55, patch_artist=True, showfliers=True,
                        medianprops=dict(color="#222222", lw=1.0),
                        flierprops=dict(marker="o", markersize=2.6,
                                        markerfacecolor="none",
                                        markeredgecolor="#606060",
                                        markeredgewidth=0.5))
        for p in bp["boxes"]:
            p.set(facecolor="#CFE0F2", edgecolor="#4A4A4A", linewidth=0.7)
        for p in bp["whiskers"] + bp["caps"]:
            p.set(color="#4A4A4A", linewidth=0.7)
        ax.scatter(range(1, len(stations) + 1),
                   [e.loc[s, "mRMSE"] for s in stations], s=30, marker="D",
                   facecolor=C_BAD, edgecolor="white", linewidth=0.5, zorder=4,
                   label="Unweighted MME")
        ax.set_xticks(range(1, len(stations) + 1))
        ax.set_xticklabels([str(s) for s in stations], rotation=55, ha="right",
                           fontsize=8.2)
        ax.set_ylim(ylo - ypad, yhi + ypad)
        ax.set_ylabel("RMSE (mm month$^{-1}$)")
        ax.grid(axis="x", visible=False)
        if k == 0:
            ax.legend(loc="upper left", borderaxespad=0.2)
        ptitle(ax, "ab"[k],
               "Raw simulations" if k == 0 else "QDM-corrected simulations")
    fig.suptitle("Individual-model spread and unweighted MME performance",
                 y=0.985, fontsize=12, fontweight="bold")
    fig.subplots_adjust(left=0.075, right=0.985, bottom=0.205, top=0.84)
    save(fig, d, "Figure6_spread_vs_MME")


# ═══════════════════════════════════════════════════════════════════════════
#  Figure 7 — mechanism
# ═══════════════════════════════════════════════════════════════════════════

def figure7(metrics: pd.DataFrame, d: Path):
    a, b = load_pairs(metrics, "primary", "validation")
    models = a.index.get_level_values("model").to_numpy()

    def comps(x):
        n = x["mn"].to_numpy(float)
        k = np.sqrt((n - 1) / n)
        return (x["msd_obs"].to_numpy(float) * k, x["msd_sim"].to_numpy(float) * k,
                x["mr"].to_numpy(float),
                (x["mmean_sim"] - x["mmean_obs"]).to_numpy(float))

    so_a, ss_a, r_a, bi_a = comps(a)
    so_b, ss_b, r_b, bi_b = comps(b)
    T = lambda so, ss, r, bi: (bi ** 2, (ss - r * so) ** 2, so ** 2 * (1 - r ** 2))
    dT = [tb - ta for ta, tb in zip(T(so_a, ss_a, r_a, bi_a), T(so_b, ss_b, r_b, bi_b))]
    d_rmse = b["mRMSE"].to_numpy(float) - a["mRMSE"].to_numpy(float)

    fig = plt.figure(figsize=(W2, 0.56 * W2))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.0, 1.08, 1.0], wspace=0.62)

    ax = fig.add_subplot(gs[0, 0])
    ax.scatter(r_a, ss_a / so_a, s=17, facecolor=C_RAW, edgecolor="white",
               linewidth=0.35, label="Raw", zorder=3)
    ax.scatter(r_b, ss_b / so_b, s=17, facecolor=C_QDM, edgecolor="white",
               linewidth=0.35, label="QDM", zorder=3)
    xx = np.linspace(-0.05, 0.78, 40)
    ax.plot(xx, xx, color=C_REF, lw=1.0, ls="--", zorder=2)
    ax.axhline(1.0, color="#9E9E9E", lw=0.7, ls=":")
    ax.text(0.49, 0.36, "RMSE-optimal\n$\\sigma_s/\\sigma_o = r$", fontsize=8.4,
            color=C_REF, ha="left", va="top", rotation=13, rotation_mode="anchor")
    ax.set_xlim(-0.05, 0.78); ax.set_ylim(0, 2.30)
    ax.set_xlabel("Monthly correlation $r$")
    ax.set_ylabel("Dispersion ratio $\\sigma_s/\\sigma_o$")
    ax.legend(loc="upper right", ncol=2, columnspacing=0.8, handletextpad=0.3,
              borderaxespad=0.2)
    ptitle(ax, "a", "Dispersion ratio")

    ax = fig.add_subplot(gs[0, 1])
    dx = (ss_b / so_b) - (ss_a / so_a)
    ok = np.isfinite(dx) & np.isfinite(d_rmse)
    for i, m in enumerate(sorted(set(models))):
        s = (models == m) & ok
        ax.scatter(dx[s], d_rmse[s], s=17, facecolor=MODEL_COLOURS[i % 5],
                   edgecolor="white", linewidth=0.35, zorder=3)
    rho, pv = spearman_fallback(dx[ok], d_rmse[ok])
    sl, ic = np.polyfit(dx[ok], d_rmse[ok], 1)
    xs = np.linspace(dx[ok].min(), dx[ok].max(), 30)
    ax.plot(xs, sl * xs + ic, color=C_REF, lw=1.1, zorder=2)
    ax.axhline(0, color="#9E9E9E", lw=0.7, ls=":")
    ax.axvline(0, color="#9E9E9E", lw=0.7, ls=":")
    ax.set_xlabel("$\\Delta$ dispersion ratio (QDM $-$ raw)")
    ax.set_ylabel("$\\Delta$ RMSE (mm month$^{-1}$)")
    ptxt = "" if np.isnan(pv) else (", $p$ < 0.001" if pv < 1e-3 else f", $p$ = {pv:.3f}")
    ax.text(0.035, 0.955, f"Spearman $\\rho$ = {rho:.2f}{ptxt}",
            transform=ax.transAxes, va="top", fontsize=9,
            bbox=dict(boxstyle="round,pad=0.28", fc="white", ec="#BDBDBD", lw=0.5))
    ptitle(ax, "b", "Dispersion vs RMSE change")

    ax = fig.add_subplot(gs[0, 2])
    labels = ["Bias\n$b^2$", "Dispersion\n$(\\sigma_s-r\\sigma_o)^2$",
              "Phase\n$\\sigma_o^2(1-r^2)$", "Total\n$\\Delta$MSE"]
    med = [float(np.nanmedian(t)) for t in dT]
    tot = dT[0] + dT[1] + dT[2]
    med.append(float(np.nanmedian(tot)))
    q1 = [float(np.nanpercentile(t, 25)) for t in dT] + [float(np.nanpercentile(tot, 25))]
    q3 = [float(np.nanpercentile(t, 75)) for t in dT] + [float(np.nanpercentile(tot, 75))]
    cols = [C_GOOD if v < 0 else C_BAD for v in med]
    cols[-1] = C_NEUT
    xp = np.arange(4)
    ax.bar(xp, med, width=0.6, color=cols, edgecolor="white", linewidth=0.6)
    ax.errorbar(xp, med, yerr=[np.array(med) - np.array(q1),
                               np.array(q3) - np.array(med)],
                fmt="none", ecolor=C_REF, elinewidth=0.9, capsize=2.4)
    ax.axhline(0, color=C_REF, lw=0.9)
    span = float(np.nanmax(q3) - np.nanmin(q1))
    for xi, v in zip(xp, med):
        ax.text(xi, v + (0.035 * span if v >= 0 else -0.035 * span), f"{v:+,.0f}",
                ha="center", va="bottom" if v >= 0 else "top", fontsize=8.8,
                fontweight="bold")
    ax.set_xticks(xp); ax.set_xticklabels(labels, fontsize=8.4)
    ax.set_ylabel("$\\Delta$ MSE contribution\n(mm$^2$ month$^{-2}$)", labelpad=8)
    ax.grid(axis="x", visible=False)
    ptitle(ax, "c", "$\\Delta$MSE components")

    model_legend(fig, set(models), y=0.025)
    fig.suptitle("Mechanism underlying validation-period error changes",
                 y=0.985, fontsize=12, fontweight="bold")
    fig.subplots_adjust(left=0.075, right=0.985, bottom=0.205, top=0.84)
    save(fig, d, "Figure7_mechanism")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))
    out = Path(cfg["paths"]["out_dir"])
    fd = out / "figures"
    fd.mkdir(parents=True, exist_ok=True)

    metrics = pd.read_csv(out / "evaluation_station_metrics.csv")
    mme = pd.read_excel(out / "evaluation_results.xlsx", "E03_MME_monthly")
    tiers = pd.read_csv(out / "qc_station_tiers.csv")
    ds = io_layer.build_dataset(cfg, Provenance(cfg, args.config))

    print("═" * 78)
    print("  figures.py — Figures 3-7")
    print("═" * 78)
    figure3(ds.observed.df, tiers, cfg, fd)
    figure4(metrics, fd)
    figure5(metrics, fd)
    figure6(metrics, mme, fd)
    figure7(metrics, fd)
    print(f"\n  ✓ {fd}  ({DPI} dpi PNG + vector PDF)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
