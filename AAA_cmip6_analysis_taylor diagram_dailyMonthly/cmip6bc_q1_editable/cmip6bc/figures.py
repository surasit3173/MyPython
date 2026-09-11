"""
figures.py — Figures 3-7 for the manuscript.

House style follows Burapha Science Journal: figures are drawn in the
journal body font, sized to the 160 mm text column so that they are placed
at 1:1 without rescaling, and all labelling is in English.

    Figure 1  study area and rain-gauge network            (prepared separately)
    Figure 2  calibration-independent validation framework (this script)
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
from matplotlib.lines import Line2D

import io_layer
from provenance import Provenance

# ── palette: Okabe-Ito, safe under colour-vision deficiency ──────────────
MODEL_COLOURS = ["#1F77B4", "#D55E00", "#009E73", "#CC79A7", "#E69F00"]
C_CAL, C_VAL = "#1F77B4", "#D55E00"
C_RAW, C_QDM = "#B23A48", "#1F5FA9"
C_REF, C_GRID = "#30343B", "#C9CED6"
C_GOOD, C_BAD, C_NEUT = "#3B7F5C", "#B23A48", "#7A7F87"

MM = 1 / 25.4
CFG: dict = {}
W = 160 * MM
FS = 11.0


def apply_style(fig_cfg: dict) -> None:
    """Journal house style. Font family is resolved from the config list."""
    global W, FS
    fams = list(fig_cfg.get("font_family", ["Cordia New", "Garuda", "DejaVu Sans"]))
    FS = float(fig_cfg.get("base_font_pt", 11.0))
    W = float(fig_cfg.get("width_mm", 160)) * MM

    import matplotlib.font_manager as fm
    have = {f.name for f in fm.fontManager.ttflist}
    chosen = next((f for f in fams if f in have), None)
    print(f"    font requested {fams[0]!r} -> using {chosen or fams[-1]!r}")
    if chosen and chosen != fams[0]:
        print(f"    note: {fams[0]!r} is not installed here; {chosen!r} is its "
              f"metric-compatible substitute. Re-running on a machine with "
              f"{fams[0]!r} reproduces the figures in that font with no other change.")

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": fams + ["DejaVu Sans"],
        "mathtext.fontset": "dejavusans",
        "font.size": FS,
        "axes.titlesize": FS * 0.88, "axes.labelsize": FS * 0.88,
        "xtick.labelsize": FS * 0.80, "ytick.labelsize": FS * 0.80,
        "axes.unicode_minus": False,
        "legend.fontsize": FS * 0.78, "legend.frameon": False,
        "legend.handlelength": 1.5, "legend.handletextpad": 0.45,
        "legend.borderaxespad": 0.3, "legend.labelspacing": 0.35,
        "axes.linewidth": 0.85, "axes.edgecolor": "#3A3A3A",
        "axes.facecolor": "white", "figure.facecolor": "white",
        "xtick.direction": "out", "ytick.direction": "out",
        "xtick.major.width": 0.9, "ytick.major.width": 0.9,
        "xtick.major.size": 3.0, "ytick.major.size": 3.0,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.linestyle": ":", "grid.linewidth": 0.55,
        "grid.alpha": 0.50, "grid.color": C_GRID,
        "lines.linewidth": 1.35, "lines.solid_capstyle": "round",
        "savefig.dpi": int(fig_cfg.get("dpi", 600)),
        "savefig.bbox": "tight", "savefig.pad_inches": 0.03,
        "figure.dpi": 110, "pdf.fonttype": 42, "ps.fonttype": 42,
    })


def ptitle(ax, tag, text="", pad=5):
    """Panel label in journal style: bold tag, regular descriptor, small."""
    ax.set_title(f"({tag}) " + (text if text else ""), loc="left",
                 fontsize=FS * 0.88, fontweight="bold", pad=pad)


def newfig(h_frac, wpad=0.045, hpad=0.045, wsp=0.06, hsp=0.08):
    """Constrained layout keeps panels from colliding at any font size."""
    fig = plt.figure(figsize=(W, h_frac * W), layout="constrained")
    fig.get_layout_engine().set(w_pad=wpad, h_pad=hpad, wspace=wsp, hspace=hsp)
    return fig


def nice_upper(values, step=25.0, pad=0.10):
    vmax = float(np.nanmax(np.asarray(values, float)))
    return float(np.ceil(vmax * (1 + pad) / step) * step)


def quiet_axes(ax):
    ax.spines["left"].set_color("#4B4F58")
    ax.spines["bottom"].set_color("#4B4F58")
    ax.tick_params(colors="#343941", labelcolor="#343941")


def save(fig, d: Path, stem: str):
    for ext in ("png", "pdf"):
        fig.savefig(d / f"{stem}.{ext}", facecolor="white")
    plt.close(fig)
    print(f"    -> {stem}.png / .pdf")


def model_legend(fig, models, y=0.0, ncol=5):
    """'outside' placement so constrained layout reserves the row."""
    h = [Line2D([], [], marker="o", ls="", markersize=5.0,
                markerfacecolor=MODEL_COLOURS[i % 5], markeredgecolor="white",
                markeredgewidth=0.4, label=m)
         for i, m in enumerate(sorted(models))]
    fig.legend(handles=h, loc="outside lower center", ncol=ncol,
               columnspacing=1.8, fontsize=FS * 0.78)


def load_pairs(metrics, variant, period, a="raw", b="QDM"):
    d = metrics[(metrics.variant == variant) & (metrics.period == period)]
    A = d[d.dataset == a].set_index(["model", "station"]).sort_index()
    B = d[d.dataset == b].set_index(["model", "station"]).sort_index()
    ix = A.index.intersection(B.index)
    return A.loc[ix], B.loc[ix]


def paired_scatter(ax, x, y, models, lower_is_better, absolute=False,
                   ticks=None):
    """Raw on x, QDM on y. Axes carry only 'Raw'/'QDM'; the metric name
    lives in the panel title, which keeps the panels uncluttered."""
    x = np.abs(np.asarray(x, float)) if absolute else np.asarray(x, float)
    y = np.abs(np.asarray(y, float)) if absolute else np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y, models = x[ok], y[ok], np.asarray(models)[ok]
    lo, hi = float(min(x.min(), y.min())), float(max(x.max(), y.max()))
    pad = 0.08 * (hi - lo if hi > lo else 1.0)
    lo, hi = lo - pad, hi + pad
    good = ([lo, hi, hi], [lo, hi, lo]) if lower_is_better else ([lo, hi, lo], [lo, hi, hi])
    bad = ([lo, hi, lo], [lo, hi, hi]) if lower_is_better else ([lo, hi, hi], [lo, hi, lo])
    ax.fill(*good, color=C_GOOD, alpha=0.07, lw=0, zorder=0)
    ax.fill(*bad, color=C_BAD, alpha=0.055, lw=0, zorder=0)
    ax.plot([lo, hi], [lo, hi], color=C_REF, lw=1.0, ls=(0, (5, 3)), zorder=2)
    for i, m in enumerate(sorted(set(models))):
        s = models == m
        ax.scatter(x[s], y[s], s=21, facecolor=MODEL_COLOURS[i % 5],
                   edgecolor="white", linewidth=0.4, alpha=0.95, zorder=3)
    n = int((y < x).sum() if lower_is_better else (y > x).sum())
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi); ax.set_aspect("equal")
    ax.set_xlabel("Raw"); ax.set_ylabel("QDM")
    if ticks:
        ax.set_xticks(ticks); ax.set_yticks(ticks)
    else:
        ax.locator_params(nbins=5)
    ax.text(0.045, 0.955, f"{n}/{len(x)} improved", transform=ax.transAxes,
            va="top", fontsize=FS * 0.78,
            bbox=dict(boxstyle="round,pad=0.30", fc="white", ec="#C8C8C8", lw=0.6))


# ═══════════════════════════════════════════════════════════════════════════
#  Figure 2 — calibration / independent validation framework
# ═══════════════════════════════════════════════════════════════════════════

def figure2(cfg, d: Path):
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
    cal, val = cfg["periods"]["calibration"], cfg["periods"]["validation"]

    fig = plt.figure(figsize=(W, 0.54 * W), layout="constrained")
    fig.get_layout_engine().set(w_pad=0.04, h_pad=0.04)
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.axis("off")

    def box(x, y, w, h, title, lines, fc, ec):
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                                    boxstyle="round,pad=0.6,rounding_size=1.6",
                                    linewidth=1.15, facecolor=fc, edgecolor=ec,
                                    zorder=2))
        ax.text(x + w / 2, y + h - 3.2, title, ha="center", va="top",
                fontsize=FS * 0.90, fontweight="bold", color="#1A1A1A", zorder=3)
        for k, ln in enumerate(lines):
            ax.text(x + w / 2, y + h - 9.0 - k * 5.2, ln, ha="center", va="top",
                    fontsize=FS * 0.78, color="#2A2A2A", zorder=3)

    def arrow(x1, y1, x2, y2):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                     mutation_scale=11, linewidth=1.1,
                                     color="#3A3A3A", zorder=4))

    BLUE_F, BLUE_E = "#DCE9F6", "#3E6E9E"
    ORAN_F, ORAN_E = "#FBE3D4", "#C4622D"
    GREY_F, GREY_E = "#EFEFEF", "#6E6E6E"

    box(3, 78, 43, 20, "Calibration  %d\u2013%d" % (cal[0], cal[1]),
        ["Observed rainfall", "CMIP6 historical simulations"], BLUE_F, BLUE_E)
    box(54, 78, 43, 20, "Independent validation  %d\u2013%d" % (val[0], val[1]),
        ["CMIP6 historical simulations", "observations withheld"], ORAN_F, ORAN_E)

    box(3, 50, 43, 19, "Estimate transfer function",
        ["quantile mapping and", "wet-day threshold"], BLUE_F, BLUE_E)
    box(54, 50, 43, 19, "Apply frozen transfer function",
        ["no parameter re-estimation"], ORAN_F, ORAN_E)

    box(23, 26, 54, 16, "Raw versus corrected simulations",
        ["individual models, then monthly ensemble"], GREY_F, GREY_E)
    box(23, 6, 54, 15, "Performance assessment",
        ["distribution, extremes, timing", "year-block bootstrap"], GREY_F, GREY_E)

    arrow(24.5, 78, 24.5, 69.5)
    arrow(75.5, 78, 75.5, 69.5)
    arrow(46.5, 59.5, 53.5, 59.5)
    ax.text(50, 63.2, "parameters\nfrozen", ha="center", va="bottom",
            fontsize=FS * 0.70, style="italic", color="#3A3A3A", zorder=5,
            linespacing=1.15)
    arrow(24.5, 50, 40, 42.5)
    arrow(75.5, 50, 60, 42.5)
    arrow(50, 26, 50, 21.5)

    ax.text(50, 1.0, "Observations from %d\u2013%d are never used to estimate, "
            "update or re-fit any parameter." % (val[0], val[1]),
            ha="center", va="bottom", fontsize=FS * 0.76, style="italic",
            color="#8A3A12", zorder=6)
    save(fig, d, "Figure2_framework")


# ═══════════════════════════════════════════════════════════════════════════
#  Figure 3
# ═══════════════════════════════════════════════════════════════════════════

def figure3(obs, cfg, d: Path):
    cal, val = cfg["periods"]["calibration"], cfg["periods"]["validation"]
    thr = float(cfg["data"]["wet_threshold_mm"])
    yr = obs.index.year
    mcal = (yr >= cal[0]) & (yr <= cal[1])
    mval = (yr >= val[0]) & (yr <= val[1])
    reg = obs.mean(axis=1)

    fig = newfig(0.78, wpad=0.055, hpad=0.055, wsp=0.10, hsp=0.16)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.0])

    ax = fig.add_subplot(gs[0, 0])
    clim_values = []
    for mask, c, lab, ls, mk in ((mcal, C_CAL, f"{cal[0]}–{cal[1]}", "-", "o"),
                                 (mval, C_VAL, f"{val[0]}–{val[1]}", (0, (5, 2)), "s")):
        s = reg[mask].resample("MS").sum(min_count=25)
        clim = s.groupby(s.index.month).mean()
        clim_values.extend(clim.values)
        ax.plot(clim.index, clim.values, color=c, ls=ls, marker=mk,
                markersize=4.6, markeredgecolor="white", markeredgewidth=0.6,
                label=lab)
    ax.set_xticks(range(1, 13, 2))
    ax.set_xlabel("Month"); ax.set_ylabel("Rainfall (mm month$^{-1}$)")
    ax.set_ylim(0, nice_upper(clim_values, 25))
    ax.legend(loc="upper left", fontsize=FS * 0.78, title="Period",
              title_fontsize=FS * 0.76)
    quiet_axes(ax)
    ptitle(ax, "a", "Monthly climatology")

    ax = fig.add_subplot(gs[0, 1])
    ann = reg.resample("YS").sum(min_count=300)
    yrs = ann.index.year.to_numpy()
    ax.bar(yrs, ann.to_numpy(float),
           color=[C_CAL if y <= cal[1] else C_VAL for y in yrs],
           edgecolor="white", linewidth=0.4, width=0.80, zorder=3)
    ax.axvline(cal[1] + 0.5, color=C_REF, lw=1.1, ls=(0, (5, 3)), zorder=4)
    ax.set_xlabel("Year"); ax.set_ylabel("Annual rainfall (mm)")
    ax.set_ylim(0, nice_upper(ann.to_numpy(float), 250)); ax.set_xlim(1979.2, 2015.8)
    ax.set_xticks([1980, 1990, 2000, 2010])
    y_text = ax.get_ylim()[1] * 0.94
    ax.text(1990.5, y_text, "Calibration", color=C_CAL, ha="center", va="top",
            fontsize=FS * 0.78, fontweight="bold")
    ax.text(2008.0, y_text, "Validation", color=C_VAL, ha="center", va="top",
            fontsize=FS * 0.78, fontweight="bold")
    quiet_axes(ax)
    ptitle(ax, "b", "Annual rainfall")

    ax = fig.add_subplot(gs[1, :])
    wf_c = {s: float((obs[s][mcal] >= thr).mean()) for s in obs.columns}
    wf_v = {s: float((obs[s][mval] >= thr).mean()) for s in obs.columns}
    vals = list(wf_c.values()) + list(wf_v.values())
    lo = max(0.0, float(np.floor((min(vals) - 0.04) / 0.05) * 0.05))
    hi = min(1.0, float(np.ceil((max(vals) + 0.04) / 0.05) * 0.05))
    ax.plot([lo, hi], [lo, hi], color=C_REF, lw=1.0, ls=(0, (5, 3)), zorder=2,
            label="1:1")
    ax.scatter(list(wf_c.values()), list(wf_v.values()), s=46, marker="o",
               facecolor=C_QDM, edgecolor="white", linewidth=0.7, alpha=0.96,
               zorder=3)
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi); ax.set_aspect("equal")
    ax.locator_params(nbins=5)
    ax.set_xlabel("Calibration"); ax.set_ylabel("Validation")
    ax.legend(loc="upper left", fontsize=FS * 0.76)
    ax.text(0.985, 0.035, f"n = {len(obs.columns)} stations",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=FS * 0.76, color="#343941")
    quiet_axes(ax)
    ptitle(ax, "c", "Wet-day frequency")

    save(fig, d, "Figure3_observed_periods")


# ═══════════════════════════════════════════════════════════════════════════
#  Figure 4
# ═══════════════════════════════════════════════════════════════════════════

def figure4(metrics, d: Path):
    a, b = load_pairs(metrics, "primary", "validation")
    models = a.index.get_level_values("model").to_numpy()
    specs = [("PBIAS", "|PBIAS| (%)", True, True, None),
             ("KS_D", "KS statistic $D$", True, False, [0.1, 0.2, 0.3, 0.4]),
             ("q99_relbias_pct", "|$q_{99}$ bias| (%)", True, True, [0, 50, 100, 150]),
             ("mRMSE", "RMSE (mm mo$^{-1}$)", True, False, [50, 100, 150, 200]),
             ("mNSE", "NSE", False, False, [-4, -3, -2, -1, 0]),
             ("mKGE", "KGE", False, False, [-0.2, 0.0, 0.2, 0.4, 0.6])]
    fig = newfig(0.84, wpad=0.055, hpad=0.055, wsp=0.11, hsp=0.17)
    gs = fig.add_gridspec(2, 3)
    for k, (col, lab, low, ab, tk) in enumerate(specs):
        ax = fig.add_subplot(gs[k // 3, k % 3])
        paired_scatter(ax, a[col].to_numpy(float), b[col].to_numpy(float),
                       models, low, absolute=ab, ticks=tk)
        ptitle(ax, "abcdef"[k], lab)
    model_legend(fig, set(models), y=-0.012)
    save(fig, d, "Figure4_raw_vs_QDM")


# ═══════════════════════════════════════════════════════════════════════════
#  Figure 5 — models as rows, stations as columns (wide, legible cells)
# ═══════════════════════════════════════════════════════════════════════════

def figure5(metrics, d: Path):
    a, b = load_pairs(metrics, "primary", "validation")
    panels = [("mRMSE", "$\\Delta$ RMSE (mm month$^{-1}$)", False),
              ("q99_relbias_pct", "$\\Delta$ |$q_{99}$ relative bias| (%)", True),
              ("PBIAS", "$\\Delta$ |PBIAS| (%)", True)]
    fig = newfig(0.76, wpad=0.055, hpad=0.055, hsp=0.18)
    gs = fig.add_gridspec(3, 1)
    for k, (col, lab, ab) in enumerate(panels):
        x = a[col].abs() if ab else a[col]
        y = b[col].abs() if ab else b[col]
        delta = (y - x).unstack("station")          # rows = model, cols = station
        delta.columns = delta.columns.astype(str)
        M = delta.to_numpy(float)
        lim = float(np.nanmax(np.abs(M)))
        ax = fig.add_subplot(gs[k, 0])
        im = ax.imshow(M, cmap="RdBu_r", vmin=-lim, vmax=lim, aspect="auto",
                       interpolation="nearest")
        ax.set_xticks(range(M.shape[1]))
        ax.set_xticklabels(delta.columns, fontsize=FS * 0.74,
                           rotation=45 if k == 2 else 0, ha="right")
        if k < 2:
            ax.set_xticklabels([])
        ax.set_yticks(range(M.shape[0]))
        ax.set_yticklabels(delta.index, fontsize=FS * 0.76)
        ax.set_xticks(np.arange(-0.5, M.shape[1], 1), minor=True)
        ax.set_yticks(np.arange(-0.5, M.shape[0], 1), minor=True)
        ax.grid(which="minor", color="white", lw=0.9)
        ax.grid(which="major", visible=False)
        ax.tick_params(which="minor", length=0)
        for i in range(M.shape[0]):
            for j in range(M.shape[1]):
                if np.isfinite(M[i, j]):
                    ax.text(j, i, f"{M[i, j]:.0f}", ha="center", va="center",
                            fontsize=FS * 0.66,
                            color="white" if abs(M[i, j]) > 0.62 * lim else "#242424")
        cb = fig.colorbar(im, ax=ax, fraction=0.024, pad=0.012, aspect=10)
        cb.ax.tick_params(labelsize=FS * 0.70, length=2)
        cb.outline.set_linewidth(0.6)
        quiet_axes(ax)
        ptitle(ax, "abc"[k], lab, pad=5)
        if k == 2:
            ax.set_xlabel("Station", labelpad=4)
    save(fig, d, "Figure5_station_model_variability")


# ═══════════════════════════════════════════════════════════════════════════
#  Figure 6 — stacked full-width panels
# ═══════════════════════════════════════════════════════════════════════════

def figure6(metrics, mme, d: Path):
    sel = ((metrics.variant == "primary") & (metrics.period == "validation")
           & (metrics.dataset.isin(["raw", "QDM"])))
    allm = metrics.loc[sel, "mRMSE"].dropna().to_numpy(float)
    alle = mme[(mme.variant == "primary") & (mme.period == "validation")
               & (mme.dataset.isin(["raw", "QDM"]))]["mRMSE"].dropna().to_numpy(float)
    both = np.concatenate([allm, alle])
    ylo, yhi = float(both.min()), float(both.max())
    ypad = 0.09 * (yhi - ylo)
    ylim = (ylo - ypad, yhi + ypad)

    fig = newfig(0.72, wpad=0.055, hpad=0.055, hsp=0.15)
    gs = fig.add_gridspec(2, 1)
    for k, dsname in enumerate(("raw", "QDM")):
        m = metrics[(metrics.variant == "primary") & (metrics.period == "validation")
                    & (metrics.dataset == dsname)]
        e = mme[(mme.variant == "primary") & (mme.period == "validation")
                & (mme.dataset == dsname)].set_index("station")
        stations = sorted(m.station.unique())
        data = [m[m.station == s]["mRMSE"].dropna().to_numpy(float) for s in stations]
        ax = fig.add_subplot(gs[k, 0])
        bp = ax.boxplot(data, widths=0.56, patch_artist=True, showfliers=True,
                        medianprops=dict(color="#1A1A1A", lw=1.2),
                        flierprops=dict(marker="o", markersize=3.0,
                                        markerfacecolor="none",
                                        markeredgecolor="#585858",
                                        markeredgewidth=0.6))
        for p in bp["boxes"]:
            p.set(facecolor="#D8E6F3", edgecolor="#41627F", linewidth=0.9)
        for p in bp["whiskers"] + bp["caps"]:
            p.set(color="#41627F", linewidth=0.8)
        ax.scatter(range(1, len(stations) + 1),
                   [e.loc[s, "mRMSE"] for s in stations], s=44, marker="D",
                   facecolor=C_RAW, edgecolor="white", linewidth=0.7, zorder=5,
                   label="Unweighted MME")
        ax.set_xticks(range(1, len(stations) + 1))
        ax.set_xticklabels([str(s) for s in stations], fontsize=FS * 0.76)
        ax.set_ylabel("RMSE (mm month$^{-1}$)")
        ax.grid(axis="x", visible=False)
        ax.margins(x=0.02)
        ax.set_ylim(*ylim)          # shared scale: raw and QDM directly comparable
        quiet_axes(ax)
        if k == 0:
            ax.legend(loc="upper left", fontsize=FS * 0.78)
        else:
            ax.set_xlabel("Station", labelpad=3)
        ptitle(ax, "ab"[k],
               "Raw simulations" if k == 0 else "QDM-corrected simulations")
    save(fig, d, "Figure6_spread_vs_MME")


# ═══════════════════════════════════════════════════════════════════════════
#  Figure 7
# ═══════════════════════════════════════════════════════════════════════════

def figure7(metrics, d: Path):
    a, b = load_pairs(metrics, "primary", "validation")
    models = a.index.get_level_values("model").to_numpy()

    def comps(x):
        n = x["mn"].to_numpy(float); k = np.sqrt((n - 1) / n)
        return (x["msd_obs"].to_numpy(float) * k, x["msd_sim"].to_numpy(float) * k,
                x["mr"].to_numpy(float),
                (x["mmean_sim"] - x["mmean_obs"]).to_numpy(float))

    so_a, ss_a, r_a, bi_a = comps(a)
    so_b, ss_b, r_b, bi_b = comps(b)
    T = lambda so, ss, r, bi: (bi ** 2, (ss - r * so) ** 2, so ** 2 * (1 - r ** 2))
    dT = [tb - ta for ta, tb in zip(T(so_a, ss_a, r_a, bi_a), T(so_b, ss_b, r_b, bi_b))]
    d_rmse = b["mRMSE"].to_numpy(float) - a["mRMSE"].to_numpy(float)

    fig = newfig(0.55, wpad=0.055, hpad=0.055, wsp=0.13)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.0, 1.0, 1.02])

    ax = fig.add_subplot(gs[0, 0])
    xx = np.linspace(-0.03, 0.72, 40)
    ax.plot(xx, xx, color=C_REF, lw=1.1, ls=(0, (5, 3)), zorder=2)
    ax.scatter(r_a, ss_a / so_a, s=21, facecolor=C_RAW, edgecolor="white",
               linewidth=0.4, label="Raw", zorder=3)
    ax.scatter(r_b, ss_b / so_b, s=21, facecolor=C_QDM, edgecolor="white",
               linewidth=0.4, label="QDM", zorder=3)
    ax.axhline(1.0, color="#9E9E9E", lw=0.8, ls=":", zorder=1)
    ax.text(0.335, 0.175, "RMSE-optimal\n$\\sigma_s/\\sigma_o = r$",
            fontsize=FS * 0.74, color=C_REF, ha="left", va="bottom")
    ax.set_xlim(-0.03, 0.72); ax.set_ylim(0, 2.35)
    ax.set_xticks([0.0, 0.2, 0.4, 0.6])
    ax.set_xlabel("Monthly correlation $r$")
    ax.set_ylabel("Dispersion ratio $\\sigma_s/\\sigma_o$")
    ax.legend(loc="upper right", ncol=1, fontsize=FS * 0.78)
    quiet_axes(ax)
    ptitle(ax, "a", "Dispersion ratio")

    ax = fig.add_subplot(gs[0, 1])
    dx = (ss_b / so_b) - (ss_a / so_a)
    ok = np.isfinite(dx) & np.isfinite(d_rmse)
    for i, m in enumerate(sorted(set(models))):
        s = (models == m) & ok
        ax.scatter(dx[s], d_rmse[s], s=21, facecolor=MODEL_COLOURS[i % 5],
                   edgecolor="white", linewidth=0.4, zorder=3)
    from scipy.stats import spearmanr
    rho, pv = spearmanr(dx[ok], d_rmse[ok])
    sl, ic = np.polyfit(dx[ok], d_rmse[ok], 1)
    xs = np.linspace(dx[ok].min(), dx[ok].max(), 30)
    ax.plot(xs, sl * xs + ic, color=C_REF, lw=1.2, zorder=2)
    ax.axhline(0, color="#9E9E9E", lw=0.8, ls=":")
    ax.axvline(0, color="#9E9E9E", lw=0.8, ls=":")
    ax.set_xlabel("$\\Delta$ dispersion ratio")
    ax.set_ylabel("$\\Delta$ RMSE (mm month$^{-1}$)")
    ax.text(0.045, 0.94,
            f"$\\rho$ = {rho:.2f}" +
            (", $p$ < 0.001" if pv < 1e-3 else f", $p$ = {pv:.3f}"),
            transform=ax.transAxes, va="top", ha="left", fontsize=FS * 0.76,
            bbox=dict(boxstyle="round,pad=0.30", fc="white", ec="#C8C8C8", lw=0.6))
    quiet_axes(ax)
    ptitle(ax, "b", "Effect on RMSE")

    ax = fig.add_subplot(gs[0, 2])
    # The decomposition is exact for every pair.  Means are reported because
    # they are additive across the three terms, so the plotted components sum
    # exactly to the plotted total; medians are not additive and would show
    # components that do not add up.
    tot = dT[0] + dT[1] + dT[2]
    med = [float(np.nanmean(t)) for t in dT] + [float(np.nanmean(tot))]
    q1 = [float(np.nanpercentile(t, 25)) for t in dT] + [float(np.nanpercentile(tot, 25))]
    q3 = [float(np.nanpercentile(t, 75)) for t in dT] + [float(np.nanpercentile(tot, 75))]
    labels = ["Bias", "Dispersion", "Phase", "Total"]
    order = [3, 2, 1, 0]                       # Bias, Phase, Dispersion, Total
    med_o = [med[i] for i in order]
    q1_o = [q1[i] for i in order]
    q3_o = [q3[i] for i in order]
    lab_o = [labels[i] for i in order]
    cols = [C_NEUT if i == 3 else (C_GOOD if med[i] < 0 else C_BAD) for i in order]
    # how often is the dispersion term the largest of the three? a
    # distribution-free statement that does not rely on any summary statistic
    dom = int(((np.abs(dT[1]) > np.abs(dT[0])) &
               (np.abs(dT[1]) > np.abs(dT[2]))).sum())
    yp = np.arange(4)
    ax.barh(yp, med_o, height=0.60, color=cols, edgecolor="white",
            linewidth=0.7, zorder=3)
    ax.errorbar(med_o, yp, xerr=[np.array(med_o) - np.array(q1_o),
                                 np.array(q3_o) - np.array(med_o)],
                fmt="none", ecolor="#4A4A4A", elinewidth=1.0, capsize=2.6,
                zorder=4)
    ax.axvline(0, color=C_REF, lw=1.0)
    span = float(np.nanmax(q3_o) - np.nanmin(q1_o))
    for yi, v in zip(yp, med_o):
        ax.text(v + (0.03 * span if v >= 0 else -0.03 * span), yi + 0.20,
                f"{v:+,.0f}", va="bottom",
                ha="left" if v >= 0 else "right", fontsize=FS * 0.74,
                fontweight="bold")
    ax.set_yticks(yp); ax.set_yticklabels(lab_o, fontsize=FS * 0.82)
    ax.set_xlabel("$\\Delta$ MSE (10$^3$ mm$^2$ month$^{-2}$)")
    ax.text(0.97, 0.055, f"dispersion largest in {dom}/{len(dT[0])}",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=FS * 0.72,
            bbox=dict(boxstyle="round,pad=0.28", fc="white", ec="#C8C8C8", lw=0.6))
    ax.grid(axis="y", visible=False)
    ax.margins(x=0.18, y=0.22)
    ax.set_xticks([-2000, 0, 2000, 4000, 6000])
    ax.set_xticklabels(["-2", "0", "2", "4", "6"])
    ax.set_xlim(-3200, 7600)
    ax.tick_params(axis="x", labelsize=FS * 0.80)
    quiet_axes(ax)
    ptitle(ax, "c", "$\\Delta$MSE decomposition")

    model_legend(fig, set(models), y=-0.015)
    save(fig, d, "Figure7_mechanism")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))
    apply_style(cfg.get("figures", {}))
    out = Path(cfg["paths"]["out_dir"]); fd = out / "figures"
    fd.mkdir(parents=True, exist_ok=True)

    metrics = pd.read_csv(out / "evaluation_station_metrics.csv")
    mme = pd.read_excel(out / "evaluation_results.xlsx", "E03_MME_monthly")
    ds = io_layer.build_dataset(cfg, Provenance(cfg, args.config))

    print("=" * 78); print("  figures.py — Figures 3-7"); print("=" * 78)
    figure2(cfg, fd)
    figure3(ds.observed.df, cfg, fd)
    figure4(metrics, fd)
    figure5(metrics, fd)
    figure6(metrics, mme, fd)
    figure7(metrics, fd)
    print(f"\n  done -> {fd}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
