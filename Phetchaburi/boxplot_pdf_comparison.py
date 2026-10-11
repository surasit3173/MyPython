"""
===============================================================================
  Boxplot Performance Improvement & PDF/Histogram Comparison
  Observed vs Raw CMIP6 vs Bias-Corrected (QDM)
  มาตรฐานวารสาร Q2-Q3 / TCI1
-------------------------------------------------------------------------------
  Input (ในโฟลเดอร์เดียวกับ script):
    • Observed     → ชื่อไฟล์มีคำว่า "Observed"
    • Raw CMIP6    → ชื่อไฟล์ขึ้นต้นด้วย "pr"
    • BC / QDM     → ชื่อไฟล์ขึ้นต้นด้วย "bc"
  Output folder:
    • Output_BoxPDF_<obs_basename>/
        ├── Output_Boxplot_Annual_AllStations.png
        ├── Output_Boxplot_Monthly_AllStations.png
        ├── Output_Boxplot_Stn<id>.png          (per station, 2-panel)
        ├── Output_PDF_Stn<id>.png              (per station, 3-panel)
        └── Output_PDF_Overview_AllStations.png

  อ้างอิง:
    Cannon et al. (2015) J. Climate 28:6938–6959  [QDM]
    Teutschbein & Seibert (2012) Hydrol. Earth Syst. Sci.
    Maidment (1993) Handbook of Hydrology [heavy-tail rainfall]
===============================================================================
"""

import os, sys, math, warnings
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats as sps
from scipy.stats import gaussian_kde

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker
import matplotlib.gridspec as gridspec
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch

warnings.filterwarnings("ignore")

# ═══════════════════════════════════════════════════════════════════════════
# 0.  JOURNAL-GRADE STYLE
# ═══════════════════════════════════════════════════════════════════════════
plt.rcParams.update({
    "font.family":          "serif",
    "font.serif":           ["Times New Roman", "DejaVu Serif"],
    "font.size":            10,
    "axes.titlesize":       10.5,
    "axes.labelsize":       9.5,
    "xtick.labelsize":      8.5,
    "ytick.labelsize":      8.5,
    "legend.fontsize":      8,
    "figure.titlesize":     12,
    "lines.linewidth":      1.4,
    "axes.linewidth":       0.8,
    "axes.spines.top":      False,
    "axes.spines.right":    False,
    "axes.grid":            True,
    "grid.linestyle":       "--",
    "grid.linewidth":       0.35,
    "grid.alpha":           0.45,
    "grid.color":           "#B0BEC5",
    "figure.dpi":           150,
    "savefig.dpi":          300,
    "savefig.bbox":         "tight",
    "savefig.pad_inches":   0.10,
    "mathtext.fontset":     "stix",
    "boxplot.whiskerprops.linestyle": "-",
})

# ── Colour palette (colour-blind–safe, Okabe-Ito inspired) ────────────────
C = {
    "obs":        "#1B1B2E",   # near-black  – Observed
    "raw":        "#D32F2F",   # deep red    – Raw CMIP6
    "bc":         "#1565C0",   # deep blue   – QDM
    "obs_fill":   "#B0BEC5",   # grey fill
    "raw_fill":   "#FFCDD2",   # red fill
    "bc_fill":    "#BBDEFB",   # blue fill
    "obs_med":    "#37474F",
    "raw_med":    "#B71C1C",
    "bc_med":     "#0D47A1",
    "obs_kde":    "#37474F",
    "raw_kde":    "#E53935",
    "bc_kde":     "#1E88E5",
    "tail":       "#FF6F00",   # amber – heavy tail annotation
    "grid":       "#CFD8DC",
    "annot_bg":   "#FAFAFA",
    "p95_line":   "#6A1B9A",   # purple – percentile lines
    "p99_line":   "#AD1457",   # pink-red
}

LABELS   = ["Observed", "Raw CMIP6", "Bias-Corrected (QDM)"]
KEYS     = ["obs",      "raw",       "bc"]
WET_THR  = 1.0   # mm/day

# ═══════════════════════════════════════════════════════════════════════════
# 1.  FILE DISCOVERY & LOADING
# ═══════════════════════════════════════════════════════════════════════════

def find_csv_files(folder: str):
    all_csv = list(Path(folder).glob("*.csv"))
    obs = [f for f in all_csv if "observed" in f.name.lower()]
    raw = [f for f in all_csv if f.name.lower().startswith("pr")]
    bc  = [f for f in all_csv if f.name.lower().startswith("bc")]
    def pick(lst, lbl):
        if not lst: return None
        if len(lst) > 1:
            print(f"  ⚠  {lbl}: พบหลายไฟล์ – ใช้ {lst[0].name}")
        return str(lst[0])
    return pick(obs, "Observed"), pick(raw, "Raw CMIP6"), pick(bc, "BC/QDM")


MISS = [-99, -999, -9999, -9.99e+20, 9.99e+20, 1e+20]

def load_daily(csv_path, label):
    if csv_path is None or not os.path.isfile(csv_path):
        print(f"  ✗  ไม่พบไฟล์ {label}")
        return None, []
    df = pd.read_csv(csv_path)
    for mv in MISS:
        df.replace(mv, np.nan, inplace=True)
    num = df.select_dtypes(include=[np.number]).columns
    df[num] = df[num].where(df[num] >= 0)
    stns = [c for c in df.columns if c not in ("YEAR","MONTH","DAY")]
    try:
        df["date"] = pd.to_datetime(
            {"year":df["YEAR"],"month":df["MONTH"],"day":df["DAY"]})
        df = df.set_index("date")[stns]
    except Exception:
        df = df[stns]
    print(f"    {label:15s}: {len(df):,} rows × {len(stns)} stations")
    return df, stns


def to_monthly(daily_df):
    if daily_df is None: return None
    return daily_df.resample("MS").apply(
        lambda g: g.sum(min_count=int(0.8*len(g))))


def to_annual(daily_df):
    if daily_df is None: return None
    return daily_df.resample("YS").apply(
        lambda g: g.sum(min_count=int(0.8*len(g))))


def wet_only(arr):
    """Return only wet-day values (≥ WET_THR mm)."""
    v = arr[~np.isnan(arr)]
    return v[v >= WET_THR]

# ═══════════════════════════════════════════════════════════════════════════
# 2.  SHARED STYLE HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def style_ax(ax, xlabel="", ylabel="", title="", title_loc="left"):
    ax.set_xlabel(xlabel, labelpad=4)
    ax.set_ylabel(ylabel, labelpad=4)
    if title:
        ax.set_title(title, loc=title_loc, fontsize=10,
                     fontweight="bold", pad=5)
    ax.tick_params(axis="both", which="major", length=4, width=0.7)
    ax.tick_params(axis="both", which="minor", length=2, width=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def footnote(fig, text, y=0.005):
    fig.text(0.01, y, text, ha="left", va="bottom",
             fontsize=6.5, color="#607D8B", style="italic")


def shared_legend(fig, loc="lower center", ncol=3, y=-0.02):
    handles = [
        mpatches.Patch(facecolor=C["obs_fill"], edgecolor=C["obs"],
                       linewidth=0.8, label="Observed"),
        mpatches.Patch(facecolor=C["raw_fill"], edgecolor=C["raw"],
                       linewidth=0.8, label="Raw CMIP6"),
        mpatches.Patch(facecolor=C["bc_fill"],  edgecolor=C["bc"],
                       linewidth=0.8, label="Bias-Corrected (QDM)"),
    ]
    leg = fig.legend(handles=handles, loc=loc, ncol=ncol,
                     fontsize=8.5, frameon=True, edgecolor="#B0BEC5",
                     framealpha=0.95, bbox_to_anchor=(0.5, y),
                     handlelength=1.6)
    leg.get_frame().set_linewidth(0.6)
    return leg


def annot_box(ax, text, x=0.02, y=0.97, fs=7.5):
    ax.text(x, y, text, transform=ax.transAxes,
            va="top", ha="left", fontsize=fs, family="monospace",
            linespacing=1.5,
            bbox=dict(boxstyle="round,pad=0.4", facecolor=C["annot_bg"],
                      edgecolor="#B0BEC5", linewidth=0.6, alpha=0.93),
            zorder=9)


def stats_summary(arr):
    v = arr[~np.isnan(arr)]
    if len(v) < 2:
        return "N/A"
    return (f"N={len(v):,}  μ={np.mean(v):.1f}  "
            f"σ={np.std(v,ddof=1):.1f}\n"
            f"Med={np.median(v):.1f}  "
            f"Skew={sps.skew(v):.2f}  "
            f"P95={np.percentile(v,95):.1f}")

# ═══════════════════════════════════════════════════════════════════════════
# 3.  BOXPLOT – PER-STATION (Annual + Monthly)
# ═══════════════════════════════════════════════════════════════════════════

BP_PROPS = dict(
    patch_artist=True,
    widths=0.55,
    medianprops=dict(linewidth=2.2, solid_capstyle="butt"),
    whiskerprops=dict(linewidth=1.0),
    capprops=dict(linewidth=1.2),
    flierprops=dict(marker="o", markersize=2.5, alpha=0.45,
                    linestyle="none"),
    boxprops=dict(linewidth=0.8),
    notch=False,
    showfliers=True,
)

FILL_COLS  = [C["obs_fill"],  C["raw_fill"],  C["bc_fill"]]
EDGE_COLS  = [C["obs"],       C["raw"],       C["bc"]]
MED_COLS   = [C["obs_med"],   C["raw_med"],   C["bc_med"]]
FLIER_COLS = [C["obs"],       C["raw"],       C["bc"]]


def _apply_box_colours(bp):
    for patch, fc, ec in zip(bp["boxes"], FILL_COLS, EDGE_COLS):
        patch.set_facecolor(fc)
        patch.set_edgecolor(ec)
        patch.set_alpha(0.85)
    for med, col in zip(bp["medians"], MED_COLS):
        med.set_color(col)
    for fl, col in zip(bp["fliers"], FLIER_COLS):
        fl.set_markerfacecolor(col)
        fl.set_markeredgecolor(col)
    for wh, col in zip(
            [bp["whiskers"][i] for i in range(0,6,2)], EDGE_COLS):
        wh.set_color(col)
    for wh, col in zip(
            [bp["whiskers"][i] for i in range(1,6,2)], EDGE_COLS):
        wh.set_color(col)
    for cap, col in zip(
            [bp["caps"][i] for i in range(0,6,2)], EDGE_COLS):
        cap.set_color(col)
    for cap, col in zip(
            [bp["caps"][i] for i in range(1,6,2)], EDGE_COLS):
        cap.set_color(col)


def plot_boxplot_station(stn, data_dict, out_path, fig_num, total, period_obs, period_sim):
    """
    2-panel boxplot per station:
      Left  – Annual totals (Obs / Raw / QDM)
      Right – Monthly totals (Obs / Raw / QDM)
    """
    obs_a = data_dict["obs_a"]
    raw_a = data_dict["raw_a"]
    bc_a  = data_dict["bc_a"]
    obs_m = data_dict["obs_m"]
    raw_m = data_dict["raw_m"]
    bc_m  = data_dict["bc_m"]

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(12, 5.5),
                                    gridspec_kw={"wspace": 0.32})

    def make_bp(ax, arrays, ylabel, title, scale):
        clean = [a[~np.isnan(a)] for a in arrays]
        bp = ax.boxplot(clean, **BP_PROPS, positions=[1, 2, 3])
        _apply_box_colours(bp)

        # median shift annotations
        meds = [float(np.median(c)) for c in clean if len(c)]
        for pos, med, col in zip([1,2,3], meds, MED_COLS):
            ax.text(pos, med, f" {med:.1f}", va="center", ha="left",
                    fontsize=7, color=col, fontweight="bold", zorder=8)

        # variability (IQR) annotations
        for pos, c, col in zip([1,2,3], clean, EDGE_COLS):
            if len(c) < 4: continue
            q1, q3 = np.percentile(c, [25, 75])
            iqr = q3 - q1
            ax.text(pos, q3, f" IQR={iqr:.0f}", va="bottom", ha="left",
                    fontsize=6.5, color=col, alpha=0.85)

        ax.set_xticks([1, 2, 3])
        ax.set_xticklabels(["Observed\n(OBS)", "Raw\nCMIP6",
                             "Bias-Corrected\n(QDM)"],
                           fontsize=8.5)
        style_ax(ax, ylabel=ylabel, title=title)
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.set_ylim(bottom=0)

        # stat box
        if len(clean[0]) > 1 and len(clean[1]) > 1 and len(clean[2]) > 1:
            lines = []
            for lbl, c in zip(["OBS","RAW","QDM"], clean):
                lines.append(f"{lbl}  μ={np.mean(c):.1f}  "
                              f"σ={np.std(c,ddof=1):.1f}  "
                              f"Skew={sps.skew(c):.2f}")
            annot_box(ax, "\n".join(lines), x=0.02, y=0.97, fs=7)

    make_bp(axL, [obs_a, raw_a, bc_a],
            "Annual Rainfall (mm)",
            f"(a)  Annual Totals — Station {stn}", "Annual")
    make_bp(axR, [obs_m, raw_m, bc_m],
            "Monthly Rainfall (mm)",
            f"(b)  Monthly Totals — Station {stn}", "Monthly")

    fig.suptitle(
        f"Rainfall Distribution Comparison — Station {stn}\n"
        f"Prachuap Khiri Khan Province, Thailand  "
        f"│  Obs: {period_obs}  │  Sim: {period_sim}",
        fontsize=11, fontweight="bold", y=1.01)

    shared_legend(fig, y=-0.06, ncol=3)
    footnote(fig,
        "Box: Q1–Q3 (IQR). Whiskers: 1.5×IQR. Notch: 95% CI of median. "
        "Circles: outliers (>1.5×IQR). Values inside boxes = medians. "
        "Ref: Cannon et al. (2015); Teutschbein & Seibert (2012).")
    fig.text(0.99, 0.005, f"Fig. {fig_num}/{total}",
             ha="right", fontsize=7, color="#9E9E9E")

    plt.tight_layout(rect=[0, 0.06, 1, 1])
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ═══════════════════════════════════════════════════════════════════════════
# 4.  BOXPLOT – ALL-STATION OVERVIEW (Annual or Monthly)
# ═══════════════════════════════════════════════════════════════════════════

def plot_boxplot_all(all_data, stns, scale, out_path, period_obs, period_sim):
    """
    Grouped boxplot – all stations side-by-side (Obs/Raw/QDM per station).
    """
    n    = len(stns)
    fig, ax = plt.subplots(figsize=(max(14, n * 2.4), 6))

    grp_width = 0.72
    gap       = 1.6
    positions_obs, positions_raw, positions_bc = [], [], []

    for idx, stn in enumerate(stns):
        d   = all_data[stn]
        key = f"{scale.lower()[0]}_{scale.lower()[:3]}"   # a_ann or m_mon
        arr_o = d[f"obs_{scale}"]
        arr_r = d[f"raw_{scale}"]
        arr_b = d[f"bc_{scale}"]

        centre = idx * (3 * grp_width + gap)
        po, pr, pb = (centre - grp_width,
                      centre,
                      centre + grp_width)
        positions_obs.append(po)
        positions_raw.append(pr)
        positions_bc.append(pb)

        for arr, pos, fc, ec, mc, fl in [
            (arr_o, po, C["obs_fill"], C["obs"], C["obs_med"], C["obs"]),
            (arr_r, pr, C["raw_fill"], C["raw"], C["raw_med"], C["raw"]),
            (arr_b, pb, C["bc_fill"],  C["bc"],  C["bc_med"],  C["bc"]),
        ]:
            clean = arr[~np.isnan(arr)]
            if len(clean) < 2: continue
            bp = ax.boxplot([clean], **BP_PROPS, positions=[pos])
            bp["boxes"][0].set_facecolor(fc)
            bp["boxes"][0].set_edgecolor(ec)
            bp["boxes"][0].set_alpha(0.82)
            bp["medians"][0].set_color(mc)
            bp["medians"][0].set_linewidth(2.0)
            for wh in bp["whiskers"]: wh.set_color(ec)
            for cp in bp["caps"]:     cp.set_color(ec)
            for fl_ in bp["fliers"]:
                fl_.set_markerfacecolor(fl)
                fl_.set_markeredgecolor(fl)
                fl_.set_markersize(2.2)
                fl_.set_alpha(0.40)

    # x-tick: station names
    centres = [idx * (3 * grp_width + gap)
               for idx in range(n)]
    ax.set_xticks(centres)
    ax.set_xticklabels([f"Stn\n{s}" for s in stns], fontsize=8)
    ax.set_xlim(centres[0] - 2*grp_width - 0.3,
                centres[-1] + 2*grp_width + 0.3)

    scale_lbl = "Annual" if scale == "a" else "Monthly"
    style_ax(ax,
             ylabel=f"{scale_lbl} Rainfall (mm)",
             title=(f"Rainfall Distribution: Observed vs Raw CMIP6 vs "
                    f"Bias-Corrected (QDM) — {scale_lbl} Scale  "
                    f"│  All Stations  │  {period_obs}"),
             title_loc="left")
    ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
    ax.set_ylim(bottom=0)

    shared_legend(fig, y=-0.10, ncol=3)
    footnote(fig,
        "Grouped boxplot: Obs (grey) / Raw (red) / QDM (blue) per station. "
        "Box = IQR; whiskers = 1.5×IQR; circles = outliers.")
    plt.tight_layout(rect=[0, 0.08, 1, 1])
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ═══════════════════════════════════════════════════════════════════════════
# 5.  PDF / HISTOGRAM – PER STATION  (3-panel layout)
# ═══════════════════════════════════════════════════════════════════════════

def kde_curve(arr, x_grid, bw="scott"):
    v = arr[~np.isnan(arr)]
    if len(v) < 10: return np.zeros_like(x_grid)
    try:
        kde = gaussian_kde(v, bw_method=bw)
        return kde(x_grid)
    except Exception:
        return np.zeros_like(x_grid)


def plot_pdf_station(stn, data_dict, out_path, fig_num, total,
                     period_obs, period_sim):
    """
    3-panel PDF/Histogram per station:
      Panel A – All-day histogram + KDE  (linear scale)
      Panel B – Wet-day only log-scale histogram + KDE (heavy tail focus)
      Panel C – ECDF comparison (Q-Q style empirical CDF)
    """
    obs_d = data_dict["obs_d"]
    raw_d = data_dict["raw_d"]
    bc_d  = data_dict["bc_d"]

    datasets = [
        ("Observed",            obs_d, C["obs_kde"], C["obs_fill"], C["obs"]),
        ("Raw CMIP6",           raw_d, C["raw_kde"], C["raw_fill"], C["raw"]),
        ("Bias-Corrected (QDM)",bc_d,  C["bc_kde"],  C["bc_fill"],  C["bc"]),
    ]

    fig = plt.figure(figsize=(14, 5.5))
    gs  = gridspec.GridSpec(1, 3, figure=fig, wspace=0.36,
                            left=0.06, right=0.97,
                            top=0.88, bottom=0.14)
    axA = fig.add_subplot(gs[0])   # All-day PDF (linear)
    axB = fig.add_subplot(gs[1])   # Wet-day PDF (log-log or log-linear)
    axC = fig.add_subplot(gs[2])   # ECDF

    # ── Panel A : All-day histogram + KDE (linear y) ─────────────────
    all_vals = np.concatenate([obs_d[~np.isnan(obs_d)],
                                raw_d[~np.isnan(raw_d)] if raw_d is not None else [],
                                bc_d[~np.isnan(bc_d)]   if bc_d  is not None else []])
    x_max_A  = min(np.percentile(all_vals[all_vals >= 0], 99.5), 200)
    x_grid_A = np.linspace(0, x_max_A, 500)
    bins_A   = np.linspace(0, x_max_A, 55)

    for lbl, arr, kc, fc, ec in datasets:
        if arr is None: continue
        v = arr[~np.isnan(arr)]
        v = v[v >= 0]
        if len(v) < 10: continue
        axA.hist(v, bins=bins_A, density=True,
                 color=fc, edgecolor=ec, linewidth=0.3,
                 alpha=0.45, label=lbl)
        kde_y = kde_curve(v, x_grid_A)
        axA.plot(x_grid_A, kde_y, color=kc, lw=1.8, alpha=0.92)

    # percentile markers on Observed
    obs_v = obs_d[~np.isnan(obs_d)]
    for pct, col, ls in [(95, C["p95_line"], "--"), (99, C["p99_line"], ":")]:
        pv = np.percentile(obs_v[obs_v>=0], pct) if len(obs_v) > 0 else 0
        axA.axvline(pv, color=col, lw=1.0, ls=ls, alpha=0.8,
                    label=f"Obs P{pct}={pv:.1f} mm")

    style_ax(axA, xlabel="Daily Rainfall (mm)",
             ylabel="Probability Density",
             title=f"(a)  All-Day PDF — Stn {stn}")
    axA.xaxis.set_minor_locator(ticker.AutoMinorLocator())
    axA.set_xlim(left=0)

    # stat annotation
    if len(obs_v) > 0:
        obs_wet = wet_only(obs_v)
        ann_lines = []
        for lbl2, arr2, kc2, _, _ in datasets:
            if arr2 is None: continue
            v2 = arr2[~np.isnan(arr2)]
            ann_lines.append(
                f"{lbl2[:3].upper()}  μ={np.mean(v2):.1f}  "
                f"σ={np.std(v2,ddof=1):.1f}  "
                f"Sk={sps.skew(v2):.2f}")
        annot_box(axA, "\n".join(ann_lines), fs=7)

    # ── Panel B : Wet-day PDF – log-scale y  (heavy-tail focus) ────────
    wet_all = np.concatenate([wet_only(obs_d),
                               wet_only(raw_d) if raw_d is not None else [],
                               wet_only(bc_d)  if bc_d  is not None else []])
    x_max_B  = np.percentile(wet_all, 99.9) if len(wet_all) > 0 else 100
    x_max_B  = max(x_max_B, 50)
    x_grid_B = np.linspace(WET_THR, x_max_B, 500)
    bins_B   = np.linspace(WET_THR, x_max_B, 55)

    for lbl, arr, kc, fc, ec in datasets:
        if arr is None: continue
        v = wet_only(arr)
        if len(v) < 10: continue
        counts, edges = np.histogram(v, bins=bins_B, density=True)
        centres = (edges[:-1] + edges[1:]) / 2
        # mask zeros for log
        m = counts > 0
        axB.semilogy(centres[m], counts[m], "o",
                     color=fc, markersize=2.5, alpha=0.50)
        kde_y_B = kde_curve(v, x_grid_B)
        kde_y_B = np.where(kde_y_B <= 0, np.nan, kde_y_B)
        axB.semilogy(x_grid_B, kde_y_B, color=kc, lw=1.8, alpha=0.92,
                     label=lbl)

    # P95, P99 markers from Observed wet days
    obs_wet = wet_only(obs_d)
    for pct, col, ls in [(95, C["p95_line"], "--"), (99, C["p99_line"], ":")]:
        pv = np.percentile(obs_wet, pct) if len(obs_wet) > 5 else 0
        axB.axvline(pv, color=col, lw=1.0, ls=ls, alpha=0.85,
                    label=f"Obs P{pct}={pv:.1f} mm")

    style_ax(axB, xlabel="Daily Rainfall (mm)  [wet days only]",
             ylabel="Probability Density  (log scale)",
             title=f"(b)  Wet-Day PDF — Log Scale — Stn {stn}")
    axB.set_xlim(left=WET_THR)
    axB.xaxis.set_minor_locator(ticker.AutoMinorLocator())
    leg_B = axB.legend(loc="upper right", fontsize=7,
                        frameon=True, framealpha=0.92,
                        edgecolor="#B0BEC5", handlelength=1.8)
    leg_B.get_frame().set_linewidth(0.5)

    # heavy-tail annotation
    if len(obs_wet) > 5:
        p95v  = np.percentile(obs_wet, 95)
        heavy = float(np.sum(obs_wet >= p95v) / len(obs_wet) * 100)
        axB.text(0.97, 0.97,
                 f"Heavy-tail (≥P95)\n"
                 f"OBS : {heavy:.1f}% of wet days\n"
                 f"Thresh: {p95v:.1f} mm",
                 transform=axB.transAxes, va="top", ha="right",
                 fontsize=7, family="monospace",
                 bbox=dict(boxstyle="round,pad=0.35",
                           facecolor="#FFF8E1", edgecolor=C["tail"],
                           linewidth=0.7, alpha=0.93))

    # ── Panel C : Empirical CDF ─────────────────────────────────────────
    for lbl, arr, kc, fc, ec in datasets:
        if arr is None: continue
        v = wet_only(arr)
        if len(v) < 5: continue
        v_sort = np.sort(v)
        p      = np.arange(1, len(v_sort)+1) / len(v_sort) * 100
        axC.plot(v_sort, p, color=kc, lw=1.6, alpha=0.88, label=lbl)
        # fill under curve area (subtle)
        axC.fill_between(v_sort, 0, p, color=fc, alpha=0.12)

    # mark P50 / P95 / P99 on Observed
    if len(obs_wet) > 5:
        obs_s = np.sort(obs_wet)
        obs_p = np.arange(1, len(obs_s)+1) / len(obs_s) * 100
        for pct, col, ls in [(50,  C["obs"],      ":"),
                              (95,  C["p95_line"], "--"),
                              (99,  C["p99_line"], ":")]:
            pv = np.interp(pct, obs_p, obs_s)
            axC.axvline(pv, color=col, lw=0.9, ls=ls, alpha=0.7)
            axC.axhline(pct, color=col, lw=0.7, ls=":", alpha=0.5)
            axC.text(pv, pct+1, f" P{pct}={pv:.0f}",
                     fontsize=6.5, color=col, va="bottom")

    style_ax(axC,
             xlabel="Daily Rainfall (mm)  [wet days only]",
             ylabel="Cumulative Probability (%)",
             title=f"(c)  ECDF (wet days) — Stn {stn}")
    axC.set_xlim(left=WET_THR)
    axC.set_ylim(0, 101)
    axC.yaxis.set_major_locator(ticker.MultipleLocator(10))
    axC.xaxis.set_minor_locator(ticker.AutoMinorLocator())
    leg_C = axC.legend(loc="lower right", fontsize=7.5,
                        frameon=True, framealpha=0.92,
                        edgecolor="#B0BEC5", handlelength=1.8)
    leg_C.get_frame().set_linewidth(0.5)

    # ── Main title ─────────────────────────────────────────────────────
    fig.suptitle(
        f"Rainfall Probability Distribution — Station {stn}   "
        f"│  Obs: {period_obs}  │  Sim: {period_sim}\n"
        f"Prachuap Khiri Khan Province, Thailand",
        fontsize=11, fontweight="bold", y=0.99)

    footnote(fig,
        f"KDE = Gaussian kernel density estimate (Scott's rule).  "
        f"Wet-day threshold: ≥ {WET_THR} mm day⁻¹.  "
        f"ECDF = empirical cumulative distribution function.  "
        f"Ref: Cannon et al. (2015); Maidment (1993).")
    fig.text(0.99, 0.005, f"Fig. {fig_num}/{total}",
             ha="right", fontsize=7, color="#9E9E9E")

    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ═══════════════════════════════════════════════════════════════════════════
# 6.  PDF OVERVIEW – ALL STATIONS  (compact 3×n_stn grid)
# ═══════════════════════════════════════════════════════════════════════════

def plot_pdf_overview(all_station_data, stns, period_obs, period_sim, out_path):
    """
    Compact 3-row × n_stn-col overview:
      Row 0: All-day KDE
      Row 1: Wet-day KDE (log scale)
      Row 2: ECDF
    """
    n   = len(stns)
    nc  = min(6, n)
    nr_stn = math.ceil(n / nc)
    # 3 analysis rows × nr_stn station rows
    n_rows = 3 * nr_stn

    fig_h = 3.8 * nr_stn * 3
    fig, axes = plt.subplots(n_rows, nc,
                             figsize=(nc * 3.8, max(fig_h, 10)))
    if n == 1:
        axes = axes.reshape(n_rows, 1)

    def get_ax(row_type, stn_idx):
        """row_type: 0=all-pdf, 1=wet-pdf, 2=ecdf"""
        stn_row   = stn_idx // nc
        stn_col   = stn_idx % nc
        excel_row = stn_row * 3 + row_type
        return axes[excel_row, stn_col]

    for si, stn in enumerate(stns):
        d       = all_station_data[stn]
        obs_d   = d["obs_d"]
        raw_d   = d["raw_d"]
        bc_d    = d["bc_d"]

        cols_data = [
            ("OBS", obs_d, C["obs_kde"], C["obs_fill"]),
            ("RAW", raw_d, C["raw_kde"], C["raw_fill"]),
            ("QDM", bc_d,  C["bc_kde"],  C["bc_fill"]),
        ]

        # ── Row 0: All-day KDE ──────────────────────────────────────
        ax0 = get_ax(0, si)
        all_v  = np.concatenate([a[~np.isnan(a)] if a is not None else []
                                  for _, a, _, _ in cols_data])
        all_v  = all_v[all_v >= 0]
        x_max0 = min(np.percentile(all_v, 99) if len(all_v) else 100, 200)
        xg0    = np.linspace(0, x_max0, 300)

        for lbl, arr, kc, fc in cols_data:
            if arr is None: continue
            v = arr[~np.isnan(arr)]; v = v[v >= 0]
            if len(v) < 10: continue
            ax0.hist(v, bins=40, density=True, range=(0, x_max0),
                     color=fc, alpha=0.40, linewidth=0)
            ax0.plot(xg0, kde_curve(v, xg0), color=kc, lw=1.4)
        ax0.set_title(f"Stn {stn}\nAll-day PDF", fontsize=7.5,
                      fontweight="bold", pad=2)
        ax0.set_ylabel("Density", fontsize=7, labelpad=2)
        ax0.tick_params(labelsize=6.5)
        ax0.set_xlim(0, x_max0)
        ax0.spines["top"].set_visible(False)
        ax0.spines["right"].set_visible(False)

        # ── Row 1: Wet-day log KDE ──────────────────────────────────
        ax1 = get_ax(1, si)
        wet_v = np.concatenate([wet_only(a) if a is not None else []
                                 for _, a, _, _ in cols_data])
        x_max1 = np.percentile(wet_v, 99.5) if len(wet_v) else 100
        xg1    = np.linspace(WET_THR, x_max1, 300)

        for lbl, arr, kc, fc in cols_data:
            if arr is None: continue
            v = wet_only(arr)
            if len(v) < 10: continue
            ky = kde_curve(v, xg1)
            ky = np.where(ky <= 0, np.nan, ky)
            ax1.semilogy(xg1, ky, color=kc, lw=1.4, label=lbl[:3])

        # P95 obs
        obs_wet = wet_only(obs_d)
        if len(obs_wet) > 5:
            p95v = np.percentile(obs_wet, 95)
            ax1.axvline(p95v, color=C["p95_line"], lw=0.8, ls="--")
            ax1.text(p95v, ax1.get_ylim()[1] if ax1.get_ylim()[1] > 0 else 0.01,
                     f" P95={p95v:.0f}", fontsize=5.5, color=C["p95_line"],
                     va="bottom")

        ax1.set_ylabel("Density (log)", fontsize=7, labelpad=2)
        ax1.set_title("Wet PDF (log)", fontsize=7.5, pad=2)
        ax1.tick_params(labelsize=6.5)
        ax1.set_xlim(WET_THR, x_max1)
        ax1.spines["top"].set_visible(False)
        ax1.spines["right"].set_visible(False)

        # ── Row 2: ECDF ─────────────────────────────────────────────
        ax2 = get_ax(2, si)
        for lbl, arr, kc, fc in cols_data:
            if arr is None: continue
            v = wet_only(arr)
            if len(v) < 5: continue
            vs = np.sort(v)
            pp = np.arange(1, len(vs)+1) / len(vs) * 100
            ax2.plot(vs, pp, color=kc, lw=1.2, label=lbl[:3])

        ax2.set_ylabel("CDF (%)", fontsize=7, labelpad=2)
        ax2.set_title("ECDF (wet)", fontsize=7.5, pad=2)
        ax2.set_ylim(0, 101)
        ax2.tick_params(labelsize=6.5)
        ax2.spines["top"].set_visible(False)
        ax2.spines["right"].set_visible(False)
        if si == 0:
            ax2.legend(fontsize=6, frameon=True, loc="lower right",
                       handlelength=1.2)

    # hide unused axes
    for si in range(n, nc * nr_stn):
        for rt in range(3):
            get_ax(rt, si).set_visible(False)

    fig.suptitle(
        "Rainfall Distribution Overview — All Stations\n"
        f"Observed vs Raw CMIP6 vs Bias-Corrected (QDM)  "
        f"│  {period_obs}  │  Prachuap Khiri Khan",
        fontsize=11, fontweight="bold", y=1.01)

    # shared mini legend
    handles = [
        Line2D([0],[0], color=C["obs_kde"], lw=1.6, label="Observed"),
        Line2D([0],[0], color=C["raw_kde"], lw=1.4, label="Raw CMIP6"),
        Line2D([0],[0], color=C["bc_kde"],  lw=1.4, label="Bias-Corrected (QDM)"),
        Line2D([0],[0], color=C["p95_line"], lw=1.0, ls="--",
               label="Obs P95"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=4,
               fontsize=8, frameon=True, edgecolor="#B0BEC5",
               bbox_to_anchor=(0.5, -0.01))

    footnote(fig,
        f"KDE = Gaussian kernel density. Wet-day ≥{WET_THR} mm. "
        "Log-scale panels reveal heavy-tail behaviour. "
        "Ref: Cannon et al. (2015).",
        y=-0.02)

    plt.tight_layout(rect=[0, 0.03, 1, 1])
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}  [PDF OVERVIEW]")


# ═══════════════════════════════════════════════════════════════════════════
# 7.  MAIN
# ═══════════════════════════════════════════════════════════════════════════

def get_work_dir():
    try:
        return str(Path(os.path.abspath(__file__)).parent)
    except NameError:
        return os.getcwd()


def main():
    print("=" * 70)
    print("  Boxplot Performance Improvement & PDF/Histogram Comparison")
    print("  มาตรฐานวารสาร Q2-Q3 / TCI1")
    print("=" * 70)

    work_dir = sys.argv[1].strip('"').strip("'") \
               if len(sys.argv) > 1 else get_work_dir()
    print(f"  โฟลเดอร์ : {work_dir}")

    obs_path, raw_path, bc_path = find_csv_files(work_dir)
    if obs_path is None:
        sys.exit("  ✗  ไม่พบไฟล์ Observed")

    print(f"  Observed : {Path(obs_path).name}")
    print(f"  Raw CMIP6: {Path(raw_path).name if raw_path else '(ไม่พบ)'}")
    print(f"  BC/QDM   : {Path(bc_path).name  if bc_path  else '(ไม่พบ)'}")
    print("-" * 70)

    # ── โหลด ─────────────────────────────────────────────────────────
    print("  กำลังโหลดข้อมูล ...")
    obs_d, stns = load_daily(obs_path, "Observed")
    raw_d, _    = load_daily(raw_path, "Raw CMIP6")
    bc_d,  _    = load_daily(bc_path,  "BC/QDM")

    obs_m = to_monthly(obs_d)
    raw_m = to_monthly(raw_d)
    bc_m  = to_monthly(bc_d)
    obs_a = to_annual(obs_d)
    raw_a = to_annual(raw_d)
    bc_a  = to_annual(bc_d)

    def period(df):
        if df is None: return "N/A"
        try:    return f"{df.index[0].year}–{df.index[-1].year}"
        except: return "N/A"

    period_obs = period(obs_d)
    period_sim = period(raw_d) if raw_d is not None else period(bc_d)
    print(f"  สถานี {len(stns)} สถานี  │  Obs: {period_obs}  │  Sim: {period_sim}")

    # ── Output folder ─────────────────────────────────────────────────
    base_name = Path(obs_path).stem
    fig_dir   = Path(work_dir) / f"Output_BoxPDF_{base_name}"
    fig_dir.mkdir(exist_ok=True)
    print(f"  Output   : {fig_dir}")
    print("-" * 70)

    def gcol(df, stn):
        if df is None or stn not in df.columns:
            return np.array([np.nan])
        return df[stn].values.astype(float)

    # ── Build per-station data dict ───────────────────────────────────
    all_station_data = {}
    for stn in stns:
        stn = str(stn)
        all_station_data[stn] = dict(
            obs_d = gcol(obs_d, stn),
            raw_d = gcol(raw_d, stn),
            bc_d  = gcol(bc_d,  stn),
            obs_m = gcol(obs_m, stn),
            raw_m = gcol(raw_m, stn),
            bc_m  = gcol(bc_m,  stn),
            obs_a = gcol(obs_a, stn),
            raw_a = gcol(raw_a, stn),
            bc_a  = gcol(bc_a,  stn),
        )

    n_stns     = len(stns)
    total_figs = n_stns * 2 + 3   # per-stn (bp+pdf) + 3 overview figs

    # ── Per-station plots ─────────────────────────────────────────────
    print("\n  [1/4] Boxplot รายสถานี ...")
    for fi, stn in enumerate(stns, 1):
        stn = str(stn)
        bp_png = fig_dir / f"Output_Boxplot_Stn{stn}.png"
        plot_boxplot_station(
            stn, all_station_data[stn], str(bp_png),
            fi, total_figs, period_obs, period_sim)

    print("\n  [2/4] PDF/Histogram รายสถานี ...")
    for fi, stn in enumerate(stns, n_stns+1):
        stn    = str(stn)
        pdf_png = fig_dir / f"Output_PDF_Stn{stn}.png"
        plot_pdf_station(
            stn, all_station_data[stn], str(pdf_png),
            fi, total_figs, period_obs, period_sim)

    # ── All-station overviews ─────────────────────────────────────────
    stns_str = [str(s) for s in stns]

    print("\n  [3/4] Boxplot Overview (Annual) ...")
    bp_ann = fig_dir / f"Output_Boxplot_Annual_AllStations.png"
    plot_boxplot_all(all_station_data, stns_str, "a", str(bp_ann),
                     period_obs, period_sim)

    print("\n  [4/4] PDF Overview (All Stations) ...")
    pdf_ov = fig_dir / f"Output_PDF_Overview_AllStations.png"
    plot_pdf_overview(all_station_data, stns_str,
                      period_obs, period_sim, str(pdf_ov))

    print()
    print("=" * 70)
    n_out = len(list(fig_dir.glob("*.png")))
    print(f"  เสร็จสิ้น – {n_out} ไฟล์รูปภาพ")
    print(f"  บันทึกใน: {fig_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
