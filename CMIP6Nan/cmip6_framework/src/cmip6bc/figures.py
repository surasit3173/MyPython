"""Publication figures for Paper 1 and Paper 2.

Every figure obeys journal column widths, embeds TrueType fonts in the PDF, and
receives a unique number from a central registry so that duplicate figure
numbers are structurally impossible.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import warnings

import numpy as np
import pandas as pd

# colour-blind safe
COL = {"obs": "#111111", "raw": "#C1272D", "qm": "#0072B2",
       "detqm": "#E69F00", "qdm": "#009E73", "grey": "#7F7F7F"}
METHOD_LABEL = {"raw": "Raw GCM", "qm": "QM/EQM", "detqm": "DetQM", "qdm": "QDM"}
# Publication labels: figures must never expose internal column names.
PRETTY = {"wet_day_pct": "Wet days", "PRCPTOT": "PRCPTOT",
          "SDII": "SDII", "q50": "$q_{50}$", "q90": "$q_{90}$",
          "q95": "$q_{95}$", "q99": "$q_{99}$", "Rx1day": "Rx1day",
          "Rx5day": "Rx5day", "R10mm": "R10mm", "R20mm": "R20mm",
          "R50mm": "R50mm", "R95p": "R95p", "R99p": "R99p",
          "CDD": "CDD", "CWD": "CWD", "acf1_daily": "ACF(1)\ndaily",
          "acf1_occurrence": "ACF(1)\noccurrence",
          "P_wet_given_wet": "$P(W|W)$", "P_wet_given_dry": "$P(W|D)$",
          "mean_wet_spell": "Mean wet\nspell", "mean_dry_spell": "Mean dry\nspell",
          "p90_dry_spell": "$p_{90}$ dry\nspell", "rx1_over_rx5": "Rx1/Rx5"}


# Width and lettering of the active target journal, set by init().
SCEN_LABEL = {"ssp245": "SSP2-4.5", "ssp585": "SSP5-8.5"}
# Axis-label offset in axes coordinates. Fixing it keeps the y labels of every
# panel figure on the same vertical line, whatever the width of the tick text.
YLABEL_X = -0.145

PROFILE = {"figure_width_in": 7.2, "base_font_pt": 8,
           "max_figure_height_in": None}


def width_in(cfg) -> float:
    """Width the figure will occupy on the page of the target journal."""
    return float(PROFILE["figure_width_in"])


def init(cfg, journal: str = None) -> None:
    """Set the plotting style for a target journal.

    Figures are drawn at their printed width, so the point size written into the
    file is the point size a reader sees; a figure drawn wide and then reduced
    would lose that guarantee.
    """
    f = cfg.raw["figures"]
    prof = (cfg.raw.get("journals", {}) or {}).get(journal or "", {})
    PROFILE.update({"figure_width_in": prof.get("figure_width_in",
                                                f["double_column_in"]),
                    "base_font_pt": prof.get("base_font_pt", 8),
                    "max_figure_height_in": prof.get("max_figure_height_in")})
    b = float(PROFILE["base_font_pt"])
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": list(f["font_family"]),
        "font.size": b, "axes.titlesize": b + 1, "axes.labelsize": b,
        "xtick.labelsize": b - 0.5, "ytick.labelsize": b - 0.5,
        "legend.fontsize": b - 0.5,
        "axes.linewidth": 0.7, "lines.linewidth": 1.1,
        "savefig.dpi": int(f["dpi"]), "figure.dpi": 110,
        "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
        "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
        "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.4,
    })


def _fit_width(fig, target_in: float, tol: float = 0.004,
               passes: int = 6) -> None:
    """Make the saved figure exactly the width the journal accepts.

    A tight bounding box grows past the requested figure size whenever a label
    or a legend spills outside the axes, and a figure that is wider than the
    column is reduced by the typesetter, which shrinks its lettering below the
    size stated in the caption. Two figures in one paper reduced by different
    amounts end up with different text sizes, which is what this prevents.

    Only the width is scaled; scaling both dimensions chases a legend anchored
    in figure coordinates and collapses the plot. A legend whose text is itself
    wider than the target cannot be squeezed by scaling, so the caller is told
    rather than left with a figure that silently misses the target.
    """
    for _ in range(passes):
        try:
            got = fig.get_tightbbox(fig.canvas.get_renderer()).width
        except Exception:                                      # pragma: no cover
            return
        if got <= 0 or abs(got - target_in) / target_in <= tol:
            return
        w, h = fig.get_size_inches()
        fig.set_size_inches(max(w * target_in / got, 1.0), h)
    warnings.warn(f"figure width settled at {got:.2f} in against a target of "
                  f"{target_in:.2f} in; a legend or label is wider than the "
                  f"column and cannot be scaled away")


SEQ_BAND = dict(color="#000000", alpha=0.06, zorder=0)
SEQ_RULE = dict(color="#666666", lw=0.7, ls=(0, (3, 2)), zorder=1)
SEQ_LABEL = "sequence-dependent"


def _seq_band(ax, positions):
    """Shade the contiguous block of sequence-dependent indices.

    One encoding is used in every figure that distinguishes this group, so a
    reader learns it once. Mixing a shaded band in one figure with hatched bars
    in another and a dotted divider in a third would make the same distinction
    look like three different ones.
    """
    if not positions:
        return
    ax.axvspan(min(positions) - 0.5, max(positions) + 0.5, **SEQ_BAND)
    ax.axvline(min(positions) - 0.5, **SEQ_RULE)


def _seq_handle():
    return plt.Rectangle((0, 0), 1, 1, facecolor="#000000", alpha=0.06,
                         edgecolor="#666666", linestyle=(0, (3, 2)),
                         linewidth=0.7)


def _tint(colour: str, amount: float = 0.72) -> tuple:
    """A pale version of a colour, for bars that also carry a hatch.

    A hatch on a white fill disappears when the bar is short; a hatch on a tint
    of the same colour stays legible and still reads as a different class.
    """
    import matplotlib.colors as mcolors
    r, g, b = mcolors.to_rgb(colour)
    return (r + (1 - r) * amount, g + (1 - g) * amount, b + (1 - b) * amount)


def _fit_legend(fig, handles, labels, target_in: float, y=0.0):
    """Lay the legend out in as few rows as fit within the figure width."""
    n = len(labels)
    # Try one row, then balanced rows. Dropping one column at a time leaves an
    # orphan entry on the second row, which reads as an afterthought.
    import math
    for rows in range(1, n + 1):
        ncol = math.ceil(n / rows)
        leg = fig.legend(handles, labels, frameon=False, ncol=ncol,
                         loc="lower center", bbox_to_anchor=(0.5, y),
                         handlelength=1.4, columnspacing=1.4,
                         handletextpad=0.5)
        fig.canvas.draw()
        w = leg.get_window_extent().width / fig.dpi
        if w <= target_in * 0.98 or rows == n:
            return leg
        leg.remove()
    return None


class Registry:
    """Hands out figure numbers; refuses to issue the same number twice."""

    def __init__(self, outdir: Path, prefix: str):
        self.outdir = Path(outdir)
        self.outdir.mkdir(parents=True, exist_ok=True)
        self.prefix = prefix
        self._n = 0
        self.index = []

    def save(self, fig, slug: str, caption: str) -> dict:
        self._n += 1
        name = f"{self.prefix}_Figure_{self._n:02d}_{slug}"
        _fit_width(fig, PROFILE["figure_width_in"])
        for ext in ("png", "pdf"):
            fig.savefig(self.outdir / f"{name}.{ext}")
        plt.close(fig)
        rec = {"figure": self._n, "file": name, "slug": slug, "caption": caption}
        self.index.append(rec)
        return rec

    def write_index(self) -> Path:
        p = self.outdir / f"{self.prefix}_FIGURE_INDEX.csv"
        pd.DataFrame(self.index).to_csv(p, index=False)
        return p


def window_order(cfg, present):
    """Chronological order taken from the configuration, never alphabetical."""
    cfgw = list(cfg.future_windows)
    return [w for w in cfgw if w in set(present)] + \
           [w for w in dict.fromkeys(present) if w not in set(cfgw)]


def _fig(cfg, width="double", h=2.6):
    f = cfg.raw["figures"]
    w = f["double_column_in"] if width == "double" else f["single_column_in"]
    return plt.subplots(figsize=(w, h))


# ---------------------------------------------------------------------------
# Shared / Paper 1
# ---------------------------------------------------------------------------
def fig_study_area(cfg, coords, boundary_rings, area, reg: Registry, warn=""):
    fig, ax = _fig(cfg, "single", 3.6)
    if boundary_rings:
        for xs, ys in boundary_rings:
            ax.plot(xs, ys, color="#333333", lw=0.9, zorder=2)
    ax.scatter(coords.longitude, coords.latitude, s=22, c="#0072B2",
               edgecolor="white", linewidth=0.5, zorder=4)
    for r in coords.itertuples():
        ax.annotate(r.station, (r.longitude, r.latitude), fontsize=5,
                    xytext=(2.5, 2.5), textcoords="offset points")
    ax.set_xlabel("Longitude ($^\\circ$E)")
    ax.set_ylabel("Latitude ($^\\circ$N)")
    ax.set_title(f"{area}: {len(coords)} rain-gauge network")
    ax.set_aspect("equal", adjustable="datalim")
    if warn:
        ax.text(0.5, -0.16, warn, transform=ax.transAxes, ha="center",
                fontsize=6, color=COL["raw"])
    return reg.save(fig, "study_area",
                    f"Location of the {len(coords)} rain gauges used in this study "
                    f"({area}). Station identifiers follow the national gauge network.")


# Figures 2 and 3 must be directly comparable, so they share one y-limit that
# is fixed the first time either is drawn.
_SHARED_YLIM = {}


def fig_hist_validation(cfg, perf, reg: Registry, period_label, slug, methods,
                        keys=None, marginal_n=None, note=None, ylim_share=True):
    """Grouped |bias| by metric and method.

    `marginal_n` separates the metrics quantile mapping controls from those it
    does not, so the figure itself states the distinction rather than leaving it
    to the caption.
    """
    keys = keys or ["wet_day_pct", "PRCPTOT", "SDII", "q95",
                    "Rx1day", "Rx5day", "CDD", "CWD"]
    keys = [k for k in keys if f"{k}_bias_pct" in perf.columns]
    fig, ax = _fig(cfg, "double", 2.8)
    x = np.arange(len(keys))
    w = 0.8 / len(methods)
    for i, m in enumerate(methods):
        sub = perf[perf.method == m]
        vals = [sub[f"{k}_bias_pct"].abs().mean() for k in keys]
        ax.bar(x + i * w - 0.4 + w / 2, vals, width=w, label=METHOD_LABEL.get(m, m),
               color=COL.get(m, COL["grey"]), edgecolor="white", linewidth=0.4)
    ax.set_xticks(x)
    ax.set_xticklabels([PRETTY.get(k, k) for k in keys], rotation=0, fontsize=6.5)
    ax.set_ylabel("Mean absolute bias (%)")
    if marginal_n:
        ax.axvline(marginal_n - 0.5, color="#444444", lw=0.8, ls=":")
        top = ax.get_ylim()[1]
        ax.text((marginal_n - 1) / 2, top * 0.97,
                "marginal / pointwise distribution",
                ha="center", va="top", fontsize=6.5, style="italic")
        ax.text((marginal_n + len(keys) - 1) / 2, top * 0.97,
                "sequence-dependent\n(not explicitly corrected)", ha="center",
                va="top", fontsize=6.5, style="italic")
    if ylim_share:
        cur = ax.get_ylim()[1]
        _SHARED_YLIM["top"] = max(_SHARED_YLIM.get("top", 0), cur)
        ax.set_ylim(0, _SHARED_YLIM["top"])
    if note:
        ax.annotate(note, xy=(1.0, 1.0), xycoords="axes fraction",
                    xytext=(-2, -3), textcoords="offset points",
                    ha="right", va="top", fontsize=6, color="#444444")
    ax.legend(ncol=len(methods), frameon=False, loc="upper center",
              bbox_to_anchor=(0.5, -0.12))
    return reg.save(fig, slug,
                    f"Mean absolute bias relative to observed rain-gauge data over "
                    f"{period_label}, averaged across stations and GCMs. Lower is better.")


def fig_qq(cfg, obs, raw, bc_dict, reg: Registry, slug, title):
    fig, ax = _fig(cfg, "single", 3.2)
    q = np.linspace(1, 99.9, 200)
    o = np.percentile(obs[obs >= 1], q)
    ax.plot(o, np.percentile(raw[raw >= 1], q), color=COL["raw"], label="Raw GCM")
    for m, v in bc_dict.items():
        ax.plot(o, np.percentile(v[v >= 1], q), color=COL.get(m, COL["grey"]),
                label=METHOD_LABEL.get(m, m))
    lim = [0, max(o.max(), 1) * 1.15]
    ax.plot(lim, lim, ls="--", lw=0.7, color="#555555", label="1:1")
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xlabel("Observed wet-day rainfall (mm d$^{-1}$)")
    ax.set_ylabel("Simulated (mm d$^{-1}$)")
    ax.set_title(title)
    ax.legend(frameon=False)
    return reg.save(fig, slug,
                    "Quantile-quantile comparison of wet-day rainfall, pooled across "
                    "stations and GCMs, for the independent validation period.")


def fig_future_change(cfg, regional, reg: Registry, indices, slug, title, caption):
    windows = window_order(cfg, regional["window"])
    scen = list(dict.fromkeys(regional["scenario"]))
    fig, axes = plt.subplots(1, len(scen), sharey=True,
                             figsize=(width_in(cfg), 3.0))
    axes = np.atleast_1d(axes)
    x = np.arange(len(indices))
    w = 0.8 / len(windows)
    cmap = ["#9ecae1", "#4292c6", "#08519c"]
    for ax, sc in zip(axes, scen):
        for i, win in enumerate(windows):
            sub = regional[(regional.scenario == sc) & (regional.window == win)]
            med = [float(sub[sub["index"] == k]["median"].mean()) if
                   (sub["index"] == k).any() else np.nan for k in indices]
            lo = [float(sub[sub["index"] == k]["q25"].mean()) if
                  (sub["index"] == k).any() else np.nan for k in indices]
            hi = [float(sub[sub["index"] == k]["q75"].mean()) if
                  (sub["index"] == k).any() else np.nan for k in indices]
            pos = x + i * w - 0.4 + w / 2
            ax.bar(pos, med, width=w, color=cmap[i % 3], edgecolor="white",
                   linewidth=0.4, label=win)
            ax.errorbar(pos, med, yerr=[np.array(med) - np.array(lo),
                                        np.array(hi) - np.array(med)],
                        fmt="none", ecolor="#333333", elinewidth=0.6, capsize=1.5)
        ax.axhline(0, color="#000000", lw=0.6)
        ax.set_xticks(x); ax.set_xticklabels(indices, rotation=40, ha="right")
        ax.set_title(sc.upper().replace("SSP", "SSP"))
    axes[0].set_ylabel("Change relative to model baseline (%)")
    axes[-1].legend(frameon=False, title="Horizon")
    fig.suptitle(title, y=1.02)
    return reg.save(fig, slug, caption)


def fig_agreement(cfg, agreement, reg: Registry, indices, slug, title, caption):
    scen = list(dict.fromkeys(agreement["scenario"]))
    windows = window_order(cfg, agreement["window"])
    fig, axes = plt.subplots(1, len(scen), sharey=True,
                             figsize=(width_in(cfg), 2.9))
    axes = np.atleast_1d(axes)
    thr = cfg.agreement_threshold
    for ax, sc in zip(axes, scen):
        mat = np.full((len(indices), len(windows)), np.nan)
        for j, win in enumerate(windows):
            sub = agreement[(agreement.scenario == sc) & (agreement.window == win)]
            for i, k in enumerate(indices):
                s = sub[sub["index"] == k]["agreement_fraction"]
                if len(s):
                    mat[i, j] = s.mean()
        im = ax.imshow(mat, cmap="viridis", vmin=0.5, vmax=1.0, aspect="auto")
        ax.set_xticks(range(len(windows))); ax.set_xticklabels(windows)
        ax.set_yticks(range(len(indices))); ax.set_yticklabels(indices)
        ax.set_title(sc.upper())
        ax.grid(False)
        for i in range(len(indices)):
            for j in range(len(windows)):
                if np.isfinite(mat[i, j]):
                    ax.text(j, i, f"{mat[i,j]:.2f}", ha="center", va="center",
                            fontsize=5.5,
                            color="white" if mat[i, j] < 0.85 else "black",
                            fontweight="bold" if mat[i, j] >= thr else "normal")
    fig.colorbar(im, ax=axes, shrink=0.85, label="Agreement fraction")
    fig.suptitle(title, y=1.03)
    return reg.save(fig, slug, caption)


def fig_ensemble_spread(cfg, model_changes, reg: Registry, index_name,
                        slug, title, caption):
    scen = list(dict.fromkeys(model_changes["scenario"]))
    windows = window_order(cfg, model_changes["window"])
    fig, axes = plt.subplots(1, len(scen), sharey=True,
                             figsize=(width_in(cfg), 2.7))
    axes = np.atleast_1d(axes)
    for ax, sc in zip(axes, scen):
        data, labels = [], []
        for win in windows:
            sub = model_changes[(model_changes.scenario == sc) &
                                (model_changes.window == win) &
                                (model_changes["index"] == index_name)]
            v = sub.groupby("model")["change_pct"].mean().to_numpy()
            data.append(v[np.isfinite(v)]); labels.append(win)
        bp = ax.boxplot(data, labels=labels, widths=0.55, showmeans=True,
                        patch_artist=True)
        for b in bp["boxes"]:
            b.set(facecolor="#cfe3f2", edgecolor="#08519c", linewidth=0.7)
        for k in ("whiskers", "caps", "medians"):
            for e in bp[k]:
                e.set(color="#08519c", linewidth=0.7)
        for i, v in enumerate(data, start=1):
            ax.scatter(np.full(len(v), i) + np.random.default_rng(1).normal(0, .03, len(v)),
                       v, s=7, color="#C1272D", zorder=4)
        ax.axhline(0, color="black", lw=0.6)
        ax.set_title(sc.upper())
    axes[0].set_ylabel(f"{index_name} change (%)")
    fig.suptitle(title, y=1.03)
    return reg.save(fig, slug, caption)


# ---------------------------------------------------------------------------
# Paper 2
# ---------------------------------------------------------------------------
def fig_signal_preservation(cfg, pe, reg: Registry, stats, slug, title, caption):
    methods = [m for m in ("qm", "detqm", "qdm") if m in set(pe.method)]
    fig, ax = _fig(cfg, "double", 2.9)
    x = np.arange(len(stats))
    w = 0.8 / len(methods)
    for i, m in enumerate(methods):
        sub = pe[pe.method == m]
        med = [sub[sub.statistic == s]["PE_pct"].median() for s in stats]
        q1 = [sub[sub.statistic == s]["PE_pct"].quantile(.25) for s in stats]
        q3 = [sub[sub.statistic == s]["PE_pct"].quantile(.75) for s in stats]
        pos = x + i * w - 0.4 + w / 2
        ax.bar(pos, med, width=w, color=COL[m], edgecolor="white", linewidth=0.4,
               label=METHOD_LABEL[m])
        ax.errorbar(pos, med, yerr=[np.array(med) - np.array(q1),
                                    np.array(q3) - np.array(med)],
                    fmt="none", ecolor="#333333", elinewidth=0.6, capsize=1.5)
    ax.axhline(0, color="black", lw=0.7)
    ax.set_xticks(x); ax.set_xticklabels(stats, rotation=35, ha="right")
    ax.set_ylabel("Signal-preservation error (%)")
    ax.set_title(title)
    ax.legend(frameon=False, ncol=3)
    return reg.save(fig, slug, caption)


def fig_method_uncertainty(cfg, spread, reg: Registry, slug, title, caption):
    fig, ax = _fig(cfg, "double", 2.7)
    piv = spread.pivot_table(index="index", columns="scenario",
                             values="method_share_pct")
    idx = np.arange(len(piv.index))
    cols = list(piv.columns)
    w = 0.8 / max(len(cols), 1)
    for i, c in enumerate(cols):
        ax.bar(idx + i * w - 0.4 + w / 2, piv[c].to_numpy(), width=w,
               label=str(c).upper(), edgecolor="white", linewidth=0.4)
    ax.axhline(50, ls="--", lw=0.7, color="#555555")
    ax.set_xticks(idx); ax.set_xticklabels(piv.index, rotation=35, ha="right")
    ax.set_ylabel("Method share of total spread (%)")
    ax.set_title(title); ax.legend(frameon=False)
    return reg.save(fig, slug, caption)


def fig_wetday_intensity(cfg, perf, reg: Registry, slug, title, caption):
    methods = [m for m in ("raw", "qm", "detqm", "qdm") if m in set(perf.method)]
    fig, axes = plt.subplots(1, 2, figsize=(width_in(cfg), 2.6))
    for ax, col, lab in zip(axes,
                            ["wet_day_pct_bias_pct", "SDII_bias_pct"],
                            ["Wet-day frequency bias (%)", "SDII bias (%)"]):
        data = [perf[perf.method == m][col].dropna().to_numpy() for m in methods]
        bp = ax.boxplot(data, labels=[METHOD_LABEL[m] for m in methods],
                        widths=0.55, patch_artist=True, showfliers=False)
        for b, m in zip(bp["boxes"], methods):
            b.set(facecolor=COL.get(m, COL["grey"]), alpha=0.55,
                  edgecolor="#222222", linewidth=0.7)
        for k in ("whiskers", "caps", "medians"):
            for e in bp[k]:
                e.set(color="#222222", linewidth=0.7)
        ax.axhline(0, color="black", lw=0.7)
        ax.set_ylabel(lab)
        ax.tick_params(axis="x", rotation=20)
    fig.suptitle(title, y=1.03)
    return reg.save(fig, slug, caption)


def fig_temporal(cfg, tbias, reg: Registry, methods, slug, title, caption):
    """Sequencing statistics: the dimension quantile mapping cannot correct."""
    keys = ["acf1_occurrence", "P_wet_given_wet", "mean_wet_spell",
            "mean_dry_spell", "p90_dry_spell", "rx1_over_rx5"]
    keys = [k for k in keys if f"{k}_bias_pct" in tbias.columns]
    labels = {"acf1_occurrence": "ACF(1) occ.", "P_wet_given_wet": "P(W|W)",
              "mean_wet_spell": "mean wet spell", "mean_dry_spell": "mean dry spell",
              "p90_dry_spell": "p90 dry spell", "rx1_over_rx5": "Rx1/Rx5"}
    fig, ax = _fig(cfg, "double", 2.8)
    x = np.arange(len(keys))
    w = 0.8 / len(methods)
    for i, m in enumerate(methods):
        sub = tbias[tbias.method == m]
        v = [sub[f"{k}_bias_pct"].abs().mean() for k in keys]
        ax.bar(x + i * w - 0.4 + w / 2, v, width=w, label=METHOD_LABEL.get(m, m),
               color=COL.get(m, COL["grey"]), edgecolor="white", linewidth=0.4)
    ax.axhline(10, ls="--", lw=0.7, color="#555555")
    ax.set_xticks(x); ax.set_xticklabels([PRETTY.get(k, labels[k]) for k in keys],
                                         rotation=0, fontsize=6.5)
    ax.set_ylabel("Mean absolute bias (%)")
    ax.set_title(title)
    ax.legend(frameon=False, ncol=len(methods))
    return reg.save(fig, slug, caption)


def fig_variance_decomposition(cfg, vd, reg: Registry, slug, title, caption):
    piv = vd.groupby("index")[["model_share_pct", "method_share_pct",
                               "residual_share_pct"]].mean()
    piv = piv.sort_values("method_share_pct", ascending=False)
    fig, ax = _fig(cfg, "double", 2.9)
    idx = np.arange(len(piv))
    bottom = np.zeros(len(piv))
    for col, c, lab in [("model_share_pct", "#0072B2", "GCM"),
                        ("method_share_pct", "#D55E00", "BC method"),
                        ("residual_share_pct", "#BBBBBB", "Interaction / residual")]:
        ax.bar(idx, piv[col].to_numpy(), bottom=bottom, color=c, label=lab,
               edgecolor="white", linewidth=0.4)
        bottom += piv[col].to_numpy()
    ax.set_xticks(idx); ax.set_xticklabels(piv.index, rotation=40, ha="right")
    ax.set_ylabel("Share of projection variance (%)")
    ax.set_ylim(0, 100)
    ax.set_title(title); ax.legend(frameon=False, ncol=3)
    return reg.save(fig, slug, caption)


def _rings(geom):
    if geom["type"] == "Polygon":
        return [np.asarray(r, float) for r in geom["coordinates"]]
    out = []
    for poly in geom["coordinates"]:
        out += [np.asarray(r, float) for r in poly]
    return out


def _point_in_ring(x, y, ring):
    inside = np.zeros(x.shape, bool)
    px, py = ring[:, 0], ring[:, 1]
    for i in range(len(ring) - 1):
        x1, y1, x2, y2 = px[i], py[i], px[i + 1], py[i + 1]
        cond = ((y1 > y) != (y2 > y))
        with np.errstate(divide="ignore", invalid="ignore"):
            xint = (x2 - x1) * (y - y1) / (y2 - y1 + 1e-30) + x1
        inside ^= cond & (x < xint)
    return inside


def _idw(px, py, vals, gx, gy, power=2.0):
    d = np.sqrt((gx[..., None] - px) ** 2 + (gy[..., None] - py) ** 2)
    d = np.maximum(d, 1e-9)
    w = 1.0 / d ** power
    return (w * vals).sum(-1) / w.sum(-1)


def fig_spatial_maps(cfg, ens, coords, geom, reg: Registry, index_name,
                     slug, title, caption, n=180):
    """Station-level change interpolated inside the VERIFIED boundary, hatched
    where the continuous agreement fraction falls below the threshold."""
    rings = _rings(geom)
    outer = max(rings, key=lambda r: len(r))
    x0, y0 = outer[:, 0].min(), outer[:, 1].min()
    x1, y1 = outer[:, 0].max(), outer[:, 1].max()
    pad = 0.03 * max(x1 - x0, y1 - y0)
    gx, gy = np.meshgrid(np.linspace(x0 - pad, x1 + pad, n),
                         np.linspace(y0 - pad, y1 + pad, n))
    mask = _point_in_ring(gx, gy, outer)

    scen = list(dict.fromkeys(ens["scenario"]))
    wins = window_order(cfg, ens["window"])
    sub_all = ens[ens["index"] == index_name]
    vmax = float(np.nanpercentile(np.abs(sub_all["median"]), 95)) or 1.0
    fig, axes = plt.subplots(len(scen), len(wins), sharex=True, sharey=True,
                             figsize=(width_in(cfg),
                                      3.1 * len(scen)))
    axes = np.atleast_2d(axes)
    cs = coords.set_index("station")
    thr = cfg.agreement_threshold
    im = None
    for i, sc in enumerate(scen):
        for j, wn in enumerate(wins):
            ax = axes[i, j]
            p = sub_all[(sub_all.scenario == sc) & (sub_all.window == wn)]
            p = p.assign(station=p.station.astype(str))
            p = p[p.station.isin(cs.index)]
            if len(p) < 3:
                ax.axis("off"); continue
            px = cs.loc[p.station, "longitude"].to_numpy(float)
            py = cs.loc[p.station, "latitude"].to_numpy(float)
            surf = _idw(px, py, p["median"].to_numpy(float), gx, gy)
            agr = _idw(px, py, p["agreement_fraction"].to_numpy(float), gx, gy)
            im = ax.pcolormesh(gx, gy, np.ma.array(surf, mask=~mask),
                               cmap="BrBG", vmin=-vmax, vmax=vmax,
                               shading="auto")
            ax.contourf(gx, gy, np.ma.array(np.where(agr < thr, 1.0, np.nan),
                                            mask=~mask),
                        levels=[0.5, 1.5], colors="none", hatches=["////"])
            for r in rings:
                ax.plot(r[:, 0], r[:, 1], color="#222222", lw=0.8)
            ax.scatter(px, py, s=7, c="k", zorder=5)
            ax.set_aspect("equal", adjustable="box")
            if i == 0:
                ax.set_title(wn)
            if j == 0:
                ax.set_ylabel(f"{sc.upper()}\nLatitude ($^\\circ$N)")
            if i == len(scen) - 1:
                ax.set_xlabel("Longitude ($^\\circ$E)")
    if im is not None:
        cb = fig.colorbar(im, ax=axes, shrink=0.8)
        cb.set_label(f"{index_name} change (%)")
    fig.suptitle(title, y=1.01)
    return reg.save(fig, slug, caption)


def fig_station_change_map(cfg, ens, coords, geom, reg: Registry, index_name,
                           slug, title, caption):
    """Gauge-level change as symbols on the verified boundary.

    Deliberately NOT an interpolated surface: the raw model fields resolve only
    a handful of distinct series across the province, so a continuous field
    would imply spatial resolution the data do not have. Marker colour is the
    median change, marker size the inter-model agreement, and gauges below the
    agreement threshold are drawn open.
    """
    rings = _rings(geom)
    outer = max(rings, key=lambda r: len(r))
    scen = list(dict.fromkeys(ens["scenario"]))
    wins = window_order(cfg, ens["window"])
    sub_all = ens[ens["index"] == index_name]
    vmax = float(np.nanpercentile(np.abs(sub_all["median"]), 95)) or 1.0
    thr = cfg.agreement_threshold
    cs = coords.set_index("station")
    fig, axes = plt.subplots(len(scen), len(wins), sharex=True, sharey=True,
                             figsize=(width_in(cfg),
                                      3.0 * len(scen)))
    axes = np.atleast_2d(axes)
    sc_h = None
    for i, sc in enumerate(scen):
        for j, wn in enumerate(wins):
            ax = axes[i, j]
            p = sub_all[(sub_all.scenario == sc) & (sub_all.window == wn)]
            p = p.assign(station=p.station.astype(str))
            p = p[p.station.isin(cs.index)]
            if not len(p):
                # a quarantined scenario-horizon: state why, do not draw an
                # empty province that reads as "no change"
                ax.axis("off")
                ax.text(0.5, 0.5, f"{wn}\nexcluded\n(Gate H)", ha="center",
                        va="center", fontsize=7, style="italic",
                        color="#777777", transform=ax.transAxes)
                continue
            for r in rings:
                ax.plot(r[:, 0], r[:, 1], color="#333333", lw=0.8, zorder=1)
            if len(p):
                px = cs.loc[p.station, "longitude"].to_numpy(float)
                py = cs.loc[p.station, "latitude"].to_numpy(float)
                v = p["median"].to_numpy(float)
                a = p["agreement_fraction"].to_numpy(float)
                size = 18 + 90 * (a - 0.5) / 0.5
                rob = a >= thr
                sc_h = ax.scatter(px[rob], py[rob], c=v[rob], s=size[rob],
                                  cmap="BrBG", vmin=-vmax, vmax=vmax,
                                  edgecolor="black", linewidth=0.5, zorder=4)
                ax.scatter(px[~rob], py[~rob], c=v[~rob], s=size[~rob],
                           cmap="BrBG", vmin=-vmax, vmax=vmax,
                           edgecolor="#888888", linewidth=0.5, alpha=0.55,
                           zorder=3)
            ax.set_aspect("equal", adjustable="box")
            if i == 0:
                ax.set_title(wn, fontsize=8)
            if j == 0:
                ax.set_ylabel(f"{sc.upper()}\nLatitude ($^\\circ$N)")
            if i == len(scen) - 1:
                ax.set_xlabel("Longitude ($^\\circ$E)")
    if sc_h is not None:
        cb = fig.colorbar(sc_h, ax=axes, shrink=0.75)
        cb.set_label(f"{index_name} change (%)")
    handles = [plt.Line2D([], [], marker="o", ls="", markersize=4,
                          markerfacecolor="#cccccc", markeredgecolor="black",
                          label=f"agreement $\\geq$ {thr:.0%}"),
               plt.Line2D([], [], marker="o", ls="", markersize=4, alpha=0.55,
                          markerfacecolor="#cccccc", markeredgecolor="#888888",
                          label=f"agreement < {thr:.0%}")]
    fig.legend(handles=handles, frameon=False, fontsize=6.5, ncol=2,
               loc="lower center", bbox_to_anchor=(0.45, -0.02))
    fig.suptitle(title, y=1.01)
    return reg.save(fig, slug, caption)


# ---------------------------------------------------------------------------
# Single-window manuscript figures: scenario panels, no horizon legend
# ---------------------------------------------------------------------------
# Indices whose value depends on the ordering of wet and dry days. Quantile
# mapping does not reorder days, so these are drawn open and hatched to keep
# them visually separate from corrected projections.
DIAGNOSTIC_INDICES = {"CDD", "CWD", "Rx5day"}


def fig_scenario_change(cfg, regional, reg: Registry, panels, slug, title,
                        caption, ylabel=None):
    """One panel per scenario; bars are indices.

    `panels` is a list of (panel_title, [index, ...], diagnostic_flag) so that
    indices which quantile mapping does not correct can be drawn open and
    labelled, instead of looking like corrected projections.
    """
    scen = list(dict.fromkeys(regional["scenario"]))
    nrow = len(panels)
    fig, axes = plt.subplots(nrow, len(scen), squeeze=False,
                             figsize=(width_in(cfg),
                                      2.7 * nrow))
    base = cfg.period("baseline")
    for pi, (ptitle, idxs, diag) in enumerate(panels):
        lo, hi = [], []
        for sc in scen:
            sub = regional[regional.scenario == sc]
            for k in idxs:
                r = sub[sub["index"] == k]
                if len(r):
                    lo.append(float(r["q25"].iloc[0])); hi.append(float(r["q75"].iloc[0]))
        pad = 0.12 * (max(hi + [1]) - min(lo + [0]) or 1)
        ylim = (min(lo + [0]) - pad, max(hi + [0]) + pad)
        for si, sc in enumerate(scen):
            ax = axes[pi][si]
            sub = regional[regional.scenario == sc].set_index("index")
            x = np.arange(len(idxs))
            med = [float(sub.loc[k, "median"]) if k in sub.index else np.nan for k in idxs]
            q1 = [float(sub.loc[k, "q25"]) if k in sub.index else np.nan for k in idxs]
            q3 = [float(sub.loc[k, "q75"]) if k in sub.index else np.nan for k in idxs]
            agr = [float(sub.loc[k, "agreement_fraction"]) if k in sub.index else np.nan
                   for k in idxs]
            thr = cfg.agreement_threshold
            for xi, (m, a, k) in enumerate(zip(med, agr, idxs)):
                robust = np.isfinite(a) and a >= thr
                is_diag = diag or k in DIAGNOSTIC_INDICES
                ax.bar(xi, m, width=0.62,
                       facecolor="none" if is_diag
                                 else ("#1B7F5F" if robust else "#9ecec0"),
                       edgecolor="#1B7F5F",
                       hatch="////" if is_diag else None,
                       linewidth=1.0 if robust else 0.7)
            ax.errorbar(x, med, yerr=[np.array(med) - np.array(q1),
                                      np.array(q3) - np.array(med)],
                        fmt="none", ecolor="#222222", elinewidth=0.7, capsize=2)
            for xi, a in enumerate(agr):
                if np.isfinite(a):
                    ax.annotate(f"{a:.2f}", (xi, ylim[0]), xytext=(0, 3),
                                textcoords="offset points", ha="center",
                                fontsize=6, color="#444444",
                                fontweight="bold" if a >= thr else "normal")
            ax.axhline(0, color="black", lw=0.7)
            ax.set_xticks(x)
            ax.set_xticklabels([PRETTY.get(k, k) for k in idxs], fontsize=7)
            ax.tick_params(axis="x", pad=2)
            ax.set_ylim(*ylim)
            if si == 0:
                ax.set_ylabel(ylabel or f"Change relative to\n{base[0]}\u2013{base[1]} (%)")
            else:
                ax.tick_params(labelleft=False)
            if pi == 0:
                ax.set_title(sc.upper().replace("SSP245", "SSP2-4.5")
                             .replace("SSP585", "SSP5-8.5"), fontsize=8)
            if si == 0 and ptitle:
                ax.annotate(ptitle, xy=(0.0, 1.0), xycoords="axes fraction",
                            xytext=(2, -4), textcoords="offset points",
                            ha="left", va="top", fontsize=6.5, style="italic")
    if any(p[2] or (set(p[1]) & DIAGNOSTIC_INDICES) for p in panels):
        h = [plt.Rectangle((0, 0), 1, 1, facecolor="#1B7F5F", edgecolor="#1B7F5F",
                           label=f"agreement $\\geq$ {cfg.agreement_threshold:.0%}"),
             plt.Rectangle((0, 0), 1, 1, facecolor="#9ecec0", edgecolor="#1B7F5F",
                           label=f"agreement < {cfg.agreement_threshold:.0%}"),
             plt.Rectangle((0, 0), 1, 1, facecolor="none", edgecolor="#1B7F5F",
                           hatch="////", label="diagnostic only")]
        fig.legend(handles=h, frameon=False, fontsize=6.5, ncol=3,
                   loc="lower center", bbox_to_anchor=(0.5, -0.06))
    fig.suptitle(title, y=1.01)
    return reg.save(fig, slug, caption)


def fig_idw_with_stations(cfg, ens, coords, geom, reg: Registry, index_name,
                          slug, title, caption):
    """IDW surface of the gauge-level ensemble median, with the gauges drawn on
    top so the reader can see that the surface is an interpolation of point
    results rather than a resolved model field."""
    rings = _rings(geom)
    scen = list(dict.fromkeys(ens["scenario"]))
    sub_all = ens[ens["index"] == index_name]
    vmax = float(np.nanpercentile(np.abs(sub_all["median"]), 98)) or 1.0
    thr = cfg.agreement_threshold
    cs = coords.set_index("station")
    b = [min(r[:, 0].min() for r in rings), min(r[:, 1].min() for r in rings),
         max(r[:, 0].max() for r in rings), max(r[:, 1].max() for r in rings)]
    n = 220
    gx = np.linspace(b[0], b[2], n); gy = np.linspace(b[1], b[3], n)
    mask = _poly_mask(rings, gx, gy)
    fig, axes = plt.subplots(1, len(scen), squeeze=False, sharey=True,
                             figsize=(width_in(cfg), 3.6))
    im = None
    for si, sc in enumerate(scen):
        ax = axes[0][si]
        p = sub_all[sub_all.scenario == sc].assign(
            station=lambda d: d.station.astype(str))
        p = p[p.station.isin(cs.index)]
        px = cs.loc[p.station, "longitude"].to_numpy(float)
        py = cs.loc[p.station, "latitude"].to_numpy(float)
        v = p["median"].to_numpy(float)
        a = p["agreement_fraction"].to_numpy(float)
        GX, GY = np.meshgrid(gx, gy)
        surf = _idw(px, py, v, GX, GY, 2.0)
        im = ax.imshow(np.ma.array(surf, mask=~mask), origin="lower",
                       extent=[b[0], b[2], b[1], b[3]], cmap="BrBG",
                       vmin=-vmax, vmax=vmax, interpolation="bilinear", zorder=1)
        for r in rings:
            ax.plot(r[:, 0], r[:, 1], color="#111111", lw=1.0, zorder=4)
        size = 16 + 80 * np.clip((a - 0.5) / 0.5, 0, 1)
        rob = a >= thr
        ax.scatter(px[rob], py[rob], s=size[rob], facecolor="#111111",
                   edgecolor="white", linewidth=0.6, zorder=5)
        ax.scatter(px[~rob], py[~rob], s=size[~rob], facecolor="none",
                   edgecolor="#111111", linewidth=0.8, zorder=5)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("Longitude ($^\\circ$E)")
        ax.set_title(sc.upper().replace("SSP245", "SSP2-4.5")
                     .replace("SSP585", "SSP5-8.5"), fontsize=8)
        ax.grid(False)
        if si == 0:
            ax.set_ylabel("Latitude ($^\\circ$N)")
    cb = fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.82)
    cb.set_label(f"{index_name} change (%)")
    h = [plt.Line2D([], [], marker="o", ls="", markersize=5, color="#111111",
                    markeredgecolor="white", label=f"agreement $\\geq$ {thr:.0%}"),
         plt.Line2D([], [], marker="o", ls="", markersize=5,
                    markerfacecolor="none", markeredgecolor="#111111",
                    label=f"agreement < {thr:.0%}")]
    fig.legend(handles=h, frameon=False, fontsize=6.5, ncol=2,
               loc="lower center", bbox_to_anchor=(0.45, -0.02))
    fig.suptitle(title, y=1.02)
    return reg.save(fig, slug, caption)


def _poly_mask(rings, gx, gy):
    from matplotlib.path import Path as MPath
    X, Y = np.meshgrid(gx, gy)
    pts = np.column_stack([X.ravel(), Y.ravel()])
    inside = np.zeros(len(pts), bool)
    for r in rings:
        inside |= MPath(r).contains_points(pts)
    return inside.reshape(X.shape)


# ---------------------------------------------------------------------------
# Paper 2: method comparison
# ---------------------------------------------------------------------------
METHOD_COLOUR = {"raw": "#C1272D", "qm": "#0072B2", "detqm": "#E69F00",
                 "qdm": "#009E73"}


def fig_method_mab(cfg, perf, reg: Registry, period, methods, indices,
                   slug, caption, marginal_n=None):
    """Mean absolute bias by index and method on a logarithmic scale.

    The raw model and the corrected series differ by two orders of magnitude
    over the calibration period, so a linear axis would compress every
    corrected bar to the baseline and hide the differences between methods.
    """
    sub = perf[perf.period == period]
    keys = [k for k in indices if f"{k}_bias_pct" in sub.columns]
    fig, ax = _fig(cfg, "double", 3.0)
    x = np.arange(len(keys))
    w = 0.8 / len(methods)
    for i, m in enumerate(methods):
        d = sub[sub.method == m]
        v = [max(float(d[f"{k}_bias_pct"].abs().mean()), 1e-3) for k in keys]
        ax.bar(x + i * w - 0.4 + w / 2, v, width=w,
               label=METHOD_LABEL.get(m, m), color=METHOD_COLOUR.get(m, "#888888"),
               edgecolor="white", linewidth=0.3)
    # A logarithmic axis is used only when the values actually span decades.
    # Fixing the limits at 0.005 to 600 leaves three empty decades whenever the
    # corrected series is not near-perfect, which is the case out of sample.
    allv = [v for i, m in enumerate(methods)
            for v in [float(sub[sub.method == m][f"{k}_bias_pct"].abs().mean())
                      for k in keys] if np.isfinite(v) and v > 0]
    span = max(allv) / max(min(allv), 1e-9)
    if span > 50:
        ax.set_yscale("log")
        ax.set_ylim(10 ** np.floor(np.log10(min(allv))) / 2,
                    10 ** np.ceil(np.log10(max(allv))) * 1.6)
    else:
        ax.set_ylim(0, max(allv) * 1.22)
    ax.set_xticks(x)
    ax.set_xticklabels([PRETTY.get(k, k) for k in keys], rotation=30,
                       ha="right")
    ax.set_ylabel("Mean absolute bias (%)")
    ax.yaxis.set_label_coords(YLABEL_X, 0.5)
    handles, labels = ax.get_legend_handles_labels()
    if marginal_n:
        _seq_band(ax, list(range(marginal_n, len(keys))))
        ax.set_xlim(-0.62, len(keys) - 0.38)
        handles.append(_seq_handle()); labels.append(SEQ_LABEL)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    _fit_legend(fig, handles, labels, PROFILE["figure_width_in"])
    return reg.save(fig, slug, caption)


def fig_pe(cfg, summary, reg: Registry, panels, slug, caption, scenarios=None):
    """Signal-preservation error by index, method and scenario.

    Rows are index groups and columns are scenarios. The group name is written
    once above its row rather than inside each panel, because a long group name
    repeated in a narrow panel overflows and collides with its neighbour. Tick
    labels are rotated whenever the panel is too narrow to set them upright,
    which is decided from the panel width and the longest label rather than
    fixed in advance.

    Reads the canonical summary frame written by the analysis step, so the bars
    are the same numbers as the main tables by construction.
    """
    scen = scenarios or list(dict.fromkeys(summary.scenario))
    methods = [m for m in ("qm", "detqm", "qdm") if m in set(summary.method)]
    fig_w = PROFILE["figure_width_in"]
    widest = max(len(PRETTY.get(k, k)) for _, idxs in panels for k in idxs)
    n_cat = max(len(idxs) for _, idxs in panels)
    # room per category in a single panel, in character widths at the tick size
    per_cat_chars = (fig_w / len(scen)) * 72 / (plt.rcParams["xtick.labelsize"]
                                                * 0.62) / n_cat
    rotate = per_cat_chars < widest + 1.5

    # rows may hold different index sets, so only the y axis is shared
    fig, axes = plt.subplots(len(panels), len(scen), squeeze=False,
                             sharey="row",
                             figsize=(fig_w, (2.9 if rotate else 2.5)
                                      * len(panels)))
    for pi, (ptitle, idxs) in enumerate(panels):
        blk = summary[summary["index"].isin(idxs)]
        lo = float(np.nanmin(blk["q25"])); hi = float(np.nanmax(blk["q75"]))
        pad = 0.16 * ((hi - lo) or 1.0)
        for si, sc in enumerate(scen):
            ax = axes[pi][si]
            x = np.arange(len(idxs))
            w = 0.78 / len(methods)
            for i, m in enumerate(methods):
                med, q1, q3 = [], [], []
                for k in idxs:
                    r = summary[(summary["index"] == k) & (summary.method == m)
                                & (summary.scenario == sc)]
                    med.append(float(r["median"].iloc[0]) if len(r) else np.nan)
                    q1.append(float(r["q25"].iloc[0]) if len(r) else np.nan)
                    q3.append(float(r["q75"].iloc[0]) if len(r) else np.nan)
                pos = x + i * w - 0.39 + w / 2
                ax.bar(pos, med, width=w, color=METHOD_COLOUR[m],
                       edgecolor="white", linewidth=0.3,
                       label=METHOD_LABEL[m] if (pi == 0 and si == 0)
                       else None)
                ax.errorbar(pos, med,
                            yerr=[np.array(med) - np.array(q1),
                                  np.array(q3) - np.array(med)],
                            fmt="none", ecolor="#333333", elinewidth=0.6,
                            capsize=1.5)
            _seq_band(ax, [i for i, k in enumerate(idxs)
                           if k in DIAGNOSTIC_INDICES])
            ax.axhline(0, color="black", lw=0.9)
            ax.set_xlim(-0.62, len(idxs) - 0.38)
            ax.set_ylim(lo - pad, hi + pad)
            ax.set_xticks(x)
            ax.set_xticklabels([PRETTY.get(k, k) for k in idxs],
                               rotation=30 if rotate else 0,
                               ha="right" if rotate else "center")
            if si == 0:
                ax.set_ylabel("Signal-preservation\nerror (%)")
                ax.yaxis.set_label_coords(YLABEL_X, 0.5)
            # scenario in the corner; the group name goes above the row
            ax.annotate(SCEN_LABEL.get(sc, sc), xy=(0.99, 0.97),
                        xycoords="axes fraction", ha="right", va="top",
                        fontsize=plt.rcParams["font.size"] - 0.5,
                        style="italic")
    h, l = axes[0][0].get_legend_handles_labels()
    if any(k in DIAGNOSTIC_INDICES for _, ii in panels for k in ii):
        h.append(_seq_handle()); l.append(SEQ_LABEL)
    # extra vertical padding leaves room for the row title above each row
    fig.tight_layout(rect=(0, 0.06, 1, 0.955), h_pad=3.2)
    # row titles are placed from the final axes positions; computing them before
    # the layout pass puts them inside the plot area
    for pi, (ptitle, _) in enumerate(panels):
        if not ptitle:
            continue
        a0 = axes[pi][0].get_position(); a1 = axes[pi][-1].get_position()
        fig.text((a0.x0 + a1.x1) / 2, a0.y1 + 0.008, ptitle, ha="center",
                 va="bottom", style="italic",
                 fontsize=plt.rcParams["font.size"])
    _fit_legend(fig, h, l, PROFILE["figure_width_in"])
    return reg.save(fig, slug, caption)


def fig_pe_synthesis(cfg, summary, reg: Registry, indices, slug, caption,
                     scenarios=None):
    """Every index and method side by side, one panel per scenario."""
    scen = scenarios or list(dict.fromkeys(summary.scenario))
    methods = [m for m in ("qm", "detqm", "qdm") if m in set(summary.method)]
    keys = [k for k in indices if k in set(summary["index"])]
    # sixteen categories will not label legibly in a half-width panel, so the
    # scenarios are stacked and each gets the full figure width; both panels
    # carry the same categories, so sharing the x axis is safe here
    fig, axes = plt.subplots(len(scen), 1, squeeze=False, sharex=True,
                             sharey=True,
                             figsize=(width_in(cfg), 2.35 * len(scen) + 0.9))
    off = {m: (i - 1) * 0.22 for i, m in enumerate(methods)}
    marks = {"qm": "o", "detqm": "s", "qdm": "^"}
    blk = summary[summary["index"].isin(keys)]
    lo = float(np.nanmin(blk["q25"])); hi = float(np.nanmax(blk["q75"]))
    pad = 0.12 * ((hi - lo) or 1.0)
    for si, sc in enumerate(scen):
        ax = axes[si][0]
        x = np.arange(len(keys))
        for m in methods:
            med, q1, q3 = [], [], []
            for k in keys:
                r = summary[(summary["index"] == k) & (summary.method == m)
                            & (summary.scenario == sc)]
                med.append(float(r["median"].iloc[0]) if len(r) else np.nan)
                q1.append(float(r["q25"].iloc[0]) if len(r) else np.nan)
                q3.append(float(r["q75"].iloc[0]) if len(r) else np.nan)
            ax.errorbar(x + off[m], med,
                        yerr=[np.array(med) - np.array(q1),
                              np.array(q3) - np.array(med)],
                        fmt=marks[m], ms=4, color=METHOD_COLOUR[m],
                        ecolor=METHOD_COLOUR[m], elinewidth=0.8, capsize=2,
                        lw=0, label=METHOD_LABEL[m] if si == 0 else None)
        _seq_band(ax, [i for i, k in enumerate(keys)
                       if k in DIAGNOSTIC_INDICES])
        ax.set_xlim(-0.6, len(keys) - 0.4)
        ax.axhline(0, color="black", lw=0.9)
        ax.set_ylim(lo - pad, hi + pad)
        ax.set_ylabel("Signal-preservation\nerror (%)")
        ax.yaxis.set_label_coords(YLABEL_X, 0.5)
        lab = sc.upper().replace("SSP245", "SSP2-4.5").replace("SSP585", "SSP5-8.5")
        ax.annotate(lab, xy=(0.0, 1.0), xycoords="axes fraction",
                    xytext=(2, -3), textcoords="offset points", ha="left",
                    va="top", fontsize=7.5, style="italic")
    axes[-1][0].set_xticks(np.arange(len(keys)))
    axes[-1][0].set_xticklabels([PRETTY.get(k, k) for k in keys],
                                rotation=30, ha="right")
    h, l = axes[0][0].get_legend_handles_labels()
    if any(k in DIAGNOSTIC_INDICES for k in keys):
        # the shaded band means something, so it belongs in the legend
        h.append(_seq_handle()); l.append(SEQ_LABEL)
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    _fit_legend(fig, h, l, PROFILE["figure_width_in"])
    return reg.save(fig, slug, caption)
