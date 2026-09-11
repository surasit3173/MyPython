"""
===============================================================================
  CDF Comparison & Q–Q Plot
  Observed vs Raw CMIP6 vs Bias-Corrected (QDM)
  มาตรฐานวารสาร Q2-Q3 / TCI1
-------------------------------------------------------------------------------
  Input (ในโฟลเดอร์เดียวกับ script):
    • Observed     → ชื่อไฟล์มีคำว่า "Observed"
    • Raw CMIP6    → ชื่อไฟล์ขึ้นต้นด้วย "pr"
    • BC / QDM     → ชื่อไฟล์ขึ้นต้นด้วย "bc"
  Output folder:
    • Output_CDF_QQ_<obs_basename>/
        ├── Output_CDF_Stn<id>.png            (per station – 3 panel)
        ├── Output_QQ_Stn<id>.png             (per station – 2 panel)
        ├── Output_CDF_Overview_AllStations.png
        └── Output_QQ_Overview_AllStations.png
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

warnings.filterwarnings("ignore")

# ═══════════════════════════════════════════════════════════════════════════
# 0.  JOURNAL STYLE
# ═══════════════════════════════════════════════════════════════════════════
plt.rcParams.update({
    "font.family":        "serif",
    "font.serif":         ["Times New Roman", "DejaVu Serif"],
    "font.size":          10,
    "axes.titlesize":     10.5,
    "axes.labelsize":     9.5,
    "xtick.labelsize":    8.5,
    "ytick.labelsize":    8.5,
    "legend.fontsize":    8.5,
    "figure.titlesize":   12,
    "lines.linewidth":    1.6,
    "axes.linewidth":     0.8,
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.grid":          True,
    "grid.linestyle":     "--",
    "grid.linewidth":     0.35,
    "grid.alpha":         0.45,
    "grid.color":         "#B0BEC5",
    "figure.dpi":         150,
    "savefig.dpi":        300,
    "savefig.bbox":       "tight",
    "savefig.pad_inches": 0.12,
    "mathtext.fontset":   "stix",
})

# ── Colour palette (Okabe-Ito colour-blind safe) ──────────────────────────
C = {
    "obs":       "#1B2838",   # near-black
    "raw":       "#C62828",   # deep red
    "bc":        "#1565C0",   # deep blue
    "obs_lt":    "#90A4AE",   # light grey (fill / scatter)
    "raw_lt":    "#EF9A9A",   # light red
    "bc_lt":     "#90CAF9",   # light blue
    "p50":       "#2E7D32",   # green  – median line
    "p95":       "#6A1B9A",   # purple – P95
    "p99":       "#AD1457",   # crimson – P99
    "ref":       "#455A64",   # 1:1 line
    "annot_bg":  "#FAFAFA",
    "tail_bg":   "#FFF8E1",
    "tail_edge": "#FF8F00",
}

WET_THR  = 1.0          # mm/day
PCTS_CDF = [50, 90, 95, 99]   # percentile markers on CDF
PCT_MARKS_QQ = [75, 90, 95, 99]   # annotated quantile thresholds on Q-Q

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
    return pick(obs,"Observed"), pick(raw,"Raw CMIP6"), pick(bc,"BC/QDM")


MISS_FLAGS = [-99, -999, -9999, -9.99e+20, 9.99e+20, 1e+20]

def load_daily(csv_path, label):
    if csv_path is None or not os.path.isfile(csv_path):
        print(f"  ✗  ไม่พบไฟล์ {label}")
        return None, []
    df = pd.read_csv(csv_path)
    for mv in MISS_FLAGS:
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


def gcol(df, stn):
    if df is None or stn not in df.columns:
        return np.array([], dtype=float)
    v = df[stn].values.astype(float)
    return v[~np.isnan(v) & (v >= 0)]


def wet_only(arr):
    return arr[arr >= WET_THR]

# ═══════════════════════════════════════════════════════════════════════════
# 2.  SHARED HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def style_ax(ax, xlabel="", ylabel="", title="", title_loc="left"):
    ax.set_xlabel(xlabel, labelpad=5)
    ax.set_ylabel(ylabel, labelpad=5)
    if title:
        ax.set_title(title, loc=title_loc,
                     fontsize=10, fontweight="bold", pad=5)
    ax.tick_params(axis="both", which="major", length=4, width=0.7)
    ax.tick_params(axis="both", which="minor", length=2, width=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def annot_box(ax, text, x=0.03, y=0.97, fs=7.5, ha="left"):
    ax.text(x, y, text, transform=ax.transAxes,
            va="top", ha=ha, fontsize=fs, family="monospace",
            linespacing=1.55,
            bbox=dict(boxstyle="round,pad=0.40", facecolor=C["annot_bg"],
                      edgecolor="#B0BEC5", linewidth=0.55, alpha=0.93),
            zorder=9)


def shared_legend_fig(fig, extra_handles=None,
                      loc="lower center", ncol=3, y=-0.02):
    handles = [
        Line2D([0],[0], color=C["obs"], lw=2.0, label="Observed"),
        Line2D([0],[0], color=C["raw"], lw=1.8, label="Raw CMIP6"),
        Line2D([0],[0], color=C["bc"],  lw=1.8, label="Bias-Corrected (QDM)"),
    ]
    if extra_handles:
        handles += extra_handles
    leg = fig.legend(handles=handles, loc=loc, ncol=ncol,
                     fontsize=8.5, frameon=True, edgecolor="#B0BEC5",
                     framealpha=0.95, bbox_to_anchor=(0.5, y),
                     handlelength=2.0)
    leg.get_frame().set_linewidth(0.6)


def ks_test_str(obs, sim):
    """KS-test p-value string."""
    if len(obs) < 5 or len(sim) < 5:
        return "KS: N/A"
    stat, p = sps.ks_2samp(obs, sim)
    stars = "***" if p < 0.001 else ("**" if p < 0.01 else
            ("*" if p < 0.05 else "ns"))
    return f"KS D={stat:.3f}  p={p:.4f} {stars}"

# ═══════════════════════════════════════════════════════════════════════════
# 3.  CDF – PER STATION  (3-panel)
# ═══════════════════════════════════════════════════════════════════════════

def plot_cdf_station(stn, obs_d, raw_d, bc_d,
                     period_obs, period_sim, out_path):
    """
    3-panel CDF per station:
      Panel A – All-day ECDF (linear scale)
      Panel B – Wet-day ECDF (linear scale, zoomed on heavy tail)
      Panel C – Wet-day ECDF (log x-axis, tail focus)
    """
    obs_w = wet_only(obs_d)
    raw_w = wet_only(raw_d) if len(raw_d) else np.array([])
    bc_w  = wet_only(bc_d)  if len(bc_d)  else np.array([])

    fig, axes = plt.subplots(1, 3, figsize=(14, 5.2),
                              gridspec_kw={"wspace": 0.32},
                              constrained_layout=False)
    fig.subplots_adjust(left=0.06, right=0.97,
                        top=0.87, bottom=0.13, wspace=0.34)

    datasets_all  = [("Observed", obs_d, C["obs"]),
                     ("Raw CMIP6", raw_d, C["raw"]),
                     ("Bias-Corrected (QDM)", bc_w, C["bc"])]
    datasets_wet  = [("Observed", obs_w, C["obs"]),
                     ("Raw CMIP6", raw_w, C["raw"]),
                     ("Bias-Corrected (QDM)", bc_w, C["bc"])]

    def draw_ecdf(ax, datasets, xscale="linear",
                  mark_pcts=True, title=""):
        for lbl, arr, col in datasets:
            if len(arr) < 5: continue
            vs = np.sort(arr)
            pp = np.arange(1, len(vs)+1) / len(vs) * 100
            ax.plot(vs, pp, color=col, lw=1.8, alpha=0.90, label=lbl)

        # percentile markers on Observed
        if mark_pcts and len(obs_w) > 5:
            obs_arr = datasets[0][1]
            if len(obs_arr) < 5: obs_arr = obs_w
            obs_s = np.sort(obs_arr)
            obs_p = np.arange(1, len(obs_s)+1) / len(obs_s) * 100
            marker_styles = {50: ("-", C["p50"]),
                             90: ("--", C["p95"]),
                             95: ("--", C["p95"]),
                             99: (":",  C["p99"])}
            for pct, (ls, col) in marker_styles.items():
                if pct not in PCTS_CDF: continue
                pv = np.interp(pct, obs_p, obs_s)
                ax.axhline(pct, color=col, lw=0.75, ls=ls, alpha=0.65)
                ax.axvline(pv,  color=col, lw=0.75, ls=ls, alpha=0.65)
                ax.text(pv, pct+1.5, f"P{pct}\n{pv:.0f}mm",
                        fontsize=6.5, color=col, va="bottom", ha="center",
                        fontweight="bold")

        if xscale == "log":
            ax.set_xscale("log")
            ax.xaxis.set_major_formatter(ticker.ScalarFormatter())
        ax.set_ylim(0, 101)
        ax.yaxis.set_major_locator(ticker.MultipleLocator(10))
        ax.yaxis.set_minor_locator(ticker.MultipleLocator(5))
        ax.xaxis.set_minor_locator(ticker.AutoMinorLocator())
        style_ax(ax, title=title,
                 ylabel="Cumulative Probability (%)",
                 xlabel="Daily Rainfall (mm)")

    # ── Panel A: All values ────────────────────────────────────────────
    draw_ecdf(axes[0],
              [("Observed", obs_d, C["obs"]),
               ("Raw CMIP6", raw_d, C["raw"]),
               ("Bias-Corrected (QDM)", bc_d, C["bc"])],
              mark_pcts=False,
              title=f"(a)  ECDF — All Days — Stn {stn}")

    # wet freq annotation
    wf_obs = len(obs_w)/len(obs_d)*100 if len(obs_d) else 0
    wf_raw = len(raw_w)/len(raw_d)*100 if len(raw_d) else 0
    wf_bc  = len(bc_d[bc_d>=WET_THR])/len(bc_d)*100 if len(bc_d) else 0
    annot_box(axes[0],
              f"Wet-day freq (≥{WET_THR} mm)\n"
              f"OBS: {wf_obs:.1f}%\n"
              f"RAW: {wf_raw:.1f}%\n"
              f"QDM: {wf_bc:.1f}%", fs=7.5)

    # ── Panel B: Wet days only (linear) ───────────────────────────────
    draw_ecdf(axes[1], datasets_wet, xscale="linear",
              mark_pcts=True,
              title=f"(b)  ECDF — Wet Days — Stn {stn}")
    axes[1].set_xlabel(f"Daily Rainfall (mm)  [wet days ≥{WET_THR} mm]")

    # KS-test annotation
    ks_raw = ks_test_str(obs_w, raw_w)
    ks_bc  = ks_test_str(obs_w, bc_w)
    annot_box(axes[1],
              f"KS-test (vs Observed)\n"
              f"RAW : {ks_raw}\n"
              f"QDM : {ks_bc}", fs=7.2)

    # ── Panel C: Wet days (log x) – tail focus ─────────────────────────
    draw_ecdf(axes[2], datasets_wet, xscale="log",
              mark_pcts=True,
              title=f"(c)  ECDF — Log Scale (tail) — Stn {stn}")
    axes[2].set_xlabel(f"Daily Rainfall (mm)  [log scale]")

    # tail quantile table annotation
    if len(obs_w) > 5:
        lines = ["Quantile (mm)    OBS   RAW   QDM"]
        for pct in [75, 90, 95, 99]:
            pv_o = np.percentile(obs_w, pct) if len(obs_w)>5 else np.nan
            pv_r = np.percentile(raw_w, pct) if len(raw_w)>5 else np.nan
            pv_b = np.percentile(bc_w,  pct) if len(bc_w)>5  else np.nan
            lines.append(
                f"P{pct:2d}          "
                f"{pv_o:5.1f} {pv_r:5.1f} {pv_b:5.1f}")
        annot_box(axes[2], "\n".join(lines), x=0.03, y=0.50, fs=7.0)

    # ── Main title ─────────────────────────────────────────────────────
    fig.suptitle(
        f"Cumulative Distribution Function (CDF) Comparison — Station {stn}\n"
        f"Prachuap Khiri Khan Province, Thailand  "
        f"│  Obs: {period_obs}  │  Sim: {period_sim}",
        fontsize=11, fontweight="bold")

    extra = [
        Line2D([0],[0], color=C["p50"], lw=1.0, ls="-",  label="P50 (Obs)"),
        Line2D([0],[0], color=C["p95"], lw=1.0, ls="--", label="P95 (Obs)"),
        Line2D([0],[0], color=C["p99"], lw=1.0, ls=":",  label="P99 (Obs)"),
    ]
    shared_legend_fig(fig, extra_handles=extra, ncol=6, y=-0.04)

    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ═══════════════════════════════════════════════════════════════════════════
# 4.  Q–Q PLOT – PER STATION  (2-panel)
# ═══════════════════════════════════════════════════════════════════════════

def plot_qq_station(stn, obs_d, raw_d, bc_d,
                    period_obs, period_sim, out_path):
    """
    2-panel Q–Q plot per station:
      Panel A – Full range Q–Q  (OBS quantiles vs RAW & QDM)
      Panel B – Tail Q–Q  (P75–P100): extreme quantile alignment
    """
    obs_w = wet_only(obs_d)
    raw_w = wet_only(raw_d) if len(raw_d) else np.array([])
    bc_w  = wet_only(bc_d)  if len(bc_d)  else np.array([])

    # common probability grid
    n_pts   = min(len(obs_w), 500)
    probs   = np.linspace(0, 100, n_pts)

    def get_q(arr, p_grid):
        if len(arr) < 5:
            return np.full_like(p_grid, np.nan)
        return np.percentile(arr, p_grid)

    q_obs = get_q(obs_w, probs)
    q_raw = get_q(raw_w, probs)
    q_bc  = get_q(bc_w,  probs)

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(12, 5.5),
                                    gridspec_kw={"wspace": 0.30})
    fig.subplots_adjust(left=0.07, right=0.97,
                        top=0.87, bottom=0.13)

    def draw_qq(ax, q_obs, q_raw, q_bc, probs,
                p_start=0, title="",
                xlabel="Observed Quantiles (mm)",
                ylabel="Model Quantiles (mm)"):
        mask = probs >= p_start
        qo  = q_obs[mask]
        qr  = q_raw[mask]
        qb  = q_bc[mask]
        pp  = probs[mask]

        x_max = np.nanmax(qo) * 1.08

        # 1:1 reference line
        ref = np.linspace(0, x_max*1.05, 300)
        ax.plot(ref, ref, color=C["ref"], lw=1.1, ls="--",
                alpha=0.70, zorder=1, label="1:1 Reference")

        # coloured probability gradient for scatter
        scatter_kw = dict(s=14, alpha=0.70, zorder=3,
                          edgecolors="none", linewidths=0)

        # RAW scatter coloured by probability
        sc_r = ax.scatter(qo, qr, c=pp,
                          cmap="YlOrRd", vmin=pp.min(), vmax=100,
                          **scatter_kw, label="Raw CMIP6")
        # QDM scatter
        sc_b = ax.scatter(qo, qb, c=pp,
                          cmap="Blues", vmin=pp.min(), vmax=100,
                          **scatter_kw, label="Bias-Corrected (QDM)")

        # smoothed lines
        ax.plot(qo, qr, color=C["raw"], lw=1.4, alpha=0.55, zorder=2)
        ax.plot(qo, qb, color=C["bc"],  lw=1.6, alpha=0.75, zorder=4)

        # annotate extreme percentile thresholds
        for pct, col in [(75, C["p50"]), (90, "#F57F17"),
                          (95, C["p95"]), (99, C["p99"])]:
            if pct < p_start: continue
            idx = np.argmin(np.abs(pp - pct))
            pv  = qo[idx]
            ax.axvline(pv, color=col, lw=0.75, ls=":",
                       alpha=0.70, zorder=5)
            ax.text(pv, ax.get_ylim()[1]*0.98 if ax.get_ylim()[1]>0 else 1,
                    f" P{pct}", fontsize=6.5, color=col,
                    va="top", rotation=90, alpha=0.90)

        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
        ax.xaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        style_ax(ax, xlabel=xlabel, ylabel=ylabel, title=title)
        ax.set_aspect("equal", adjustable="datalim")

        # stats annotation
        if len(qo) > 2 and len(qr) > 2 and len(qb) > 2:
            # R² of QQ line vs 1:1
            mask2 = ~np.isnan(qr) & ~np.isnan(qo)
            r2_raw = np.corrcoef(qo[mask2], qr[mask2])[0,1]**2 \
                     if mask2.sum()>2 else np.nan
            mask3 = ~np.isnan(qb) & ~np.isnan(qo)
            r2_bc  = np.corrcoef(qo[mask3], qb[mask3])[0,1]**2 \
                     if mask3.sum()>2 else np.nan

            # mean absolute quantile error
            maqe_raw = np.nanmean(np.abs(qr - qo))
            maqe_bc  = np.nanmean(np.abs(qb - qo))

            annot_box(ax,
                      f"Quantile Alignment (vs Obs)\n"
                      f"          R²      MAQE(mm)\n"
                      f"RAW   {r2_raw:.4f}  {maqe_raw:6.2f}\n"
                      f"QDM   {r2_bc:.4f}  {maqe_bc:6.2f}",
                      x=0.03, y=0.97, fs=7.5)

        return sc_r, sc_b

    # ── Panel A: Full range ────────────────────────────────────────────
    sc_r, sc_b = draw_qq(axL, q_obs, q_raw, q_bc, probs,
                          p_start=0,
                          title=f"(a)  Q–Q Plot (Full Range) — Stn {stn}")

    # ── Panel B: Tail (P75–P100) ───────────────────────────────────────
    draw_qq(axR, q_obs, q_raw, q_bc, probs,
            p_start=75,
            title=f"(b)  Q–Q Plot (Upper Tail: P75–P100) — Stn {stn}",
            xlabel="Observed Quantiles (mm)  [P75–P100]",
            ylabel="Model Quantiles (mm)  [P75–P100]")

    # tail bias annotation (panel B)
    if len(obs_w) > 5 and len(raw_w) > 5 and len(bc_w) > 5:
        lines_t = ["Extreme Quantile Bias (mm)"]
        lines_t.append(f"{'Pct':>4}  {'Obs':>6}  {'Raw':>6}  "
                       f"{'QDM':>6}  {'ΔRaw':>7}  {'ΔQDM':>7}")
        for pct in [90, 95, 99, 99.5]:
            pv_o = np.percentile(obs_w, pct)
            pv_r = np.percentile(raw_w, pct) if len(raw_w)>5 else np.nan
            pv_b = np.percentile(bc_w,  pct) if len(bc_w)>5  else np.nan
            dr   = pv_r - pv_o
            db   = pv_b - pv_o
            lines_t.append(
                f"P{pct:4.1f}  {pv_o:6.1f}  {pv_r:6.1f}  "
                f"{pv_b:6.1f}  {dr:+7.1f}  {db:+7.1f}")
        axR.text(0.97, 0.03, "\n".join(lines_t),
                 transform=axR.transAxes, va="bottom", ha="right",
                 fontsize=7.0, family="monospace",
                 bbox=dict(boxstyle="round,pad=0.40",
                           facecolor=C["tail_bg"],
                           edgecolor=C["tail_edge"],
                           linewidth=0.7, alpha=0.93),
                 zorder=9)

    # ── Main title ─────────────────────────────────────────────────────
    fig.suptitle(
        f"Quantile–Quantile (Q–Q) Plot — Station {stn}\n"
        f"Prachuap Khiri Khan Province, Thailand  "
        f"│  Obs: {period_obs}  │  Sim: {period_sim}",
        fontsize=11, fontweight="bold")

    extra = [
        Line2D([0],[0], color=C["ref"], lw=1.2, ls="--",
               label="1:1 Reference"),
        Line2D([0],[0], color=C["p95"], lw=1.0, ls=":",
               label="P95/P99 threshold"),
    ]
    shared_legend_fig(fig, extra_handles=extra, ncol=5, y=-0.04)

    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ═══════════════════════════════════════════════════════════════════════════
# 5.  CDF OVERVIEW – ALL STATIONS
# ═══════════════════════════════════════════════════════════════════════════

def plot_cdf_overview(all_data, stns, period_obs, period_sim, out_path):
    """2-row × ceil(n/2) overview: Row0=full ECDF, Row1=tail log ECDF."""
    n  = len(stns)
    nc = min(4, n)
    nr_stn = math.ceil(n / nc)
    fig, axes = plt.subplots(2 * nr_stn, nc,
                             figsize=(nc * 4.0, 4.0 * 2 * nr_stn))
    if n == 1:
        axes = axes.reshape(2 * nr_stn, 1)

    def get_ax(row_type, si):
        stn_row  = si // nc
        stn_col  = si % nc
        return axes[stn_row * 2 + row_type, stn_col]

    for si, stn in enumerate(stns):
        d     = all_data[stn]
        obs_w = wet_only(d["obs"])
        raw_w = wet_only(d["raw"])
        bc_w  = wet_only(d["bc"])

        for row_type, (xscale, arr_pairs) in enumerate([
            ("linear", [("OBS", obs_w, C["obs"]),
                        ("RAW", raw_w, C["raw"]),
                        ("QDM", bc_w,  C["bc"])]),
            ("log",    [("OBS", obs_w, C["obs"]),
                        ("RAW", raw_w, C["raw"]),
                        ("QDM", bc_w,  C["bc"])]),
        ]):
            ax = get_ax(row_type, si)
            for lbl, arr, col in arr_pairs:
                if len(arr) < 5: continue
                vs = np.sort(arr)
                pp = np.arange(1, len(vs)+1)/len(vs)*100
                ax.plot(vs, pp, color=col, lw=1.4, alpha=0.88, label=lbl)

            # P95 marker
            if len(obs_w) > 5:
                p95 = np.percentile(obs_w, 95)
                ax.axvline(p95, color=C["p95"], lw=0.8, ls="--", alpha=0.75)
                ax.axhline(95,  color=C["p95"], lw=0.6, ls=":", alpha=0.55)

            if xscale == "log" and len(obs_w) > 5:
                ax.set_xscale("log")
                ax.xaxis.set_major_formatter(ticker.ScalarFormatter())

            ax.set_ylim(0, 101)
            ax.set_title(
                f"Stn {stn}\n"
                f"{'ECDF (linear)' if xscale=='linear' else 'ECDF (log-tail)'}",
                fontsize=7.5, fontweight="bold", pad=2)
            ax.set_ylabel("CDF (%)", fontsize=7, labelpad=2)
            ax.tick_params(labelsize=6.5)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.grid(True, lw=0.3, ls="--", alpha=0.45)

            # KS annotation
            if len(obs_w)>5 and len(raw_w)>5 and len(bc_w)>5 and row_type==0:
                stat_r, p_r = sps.ks_2samp(obs_w, raw_w)
                stat_b, p_b = sps.ks_2samp(obs_w, bc_w)
                ax.text(0.97, 0.03,
                        f"KS D\nRAW:{stat_r:.3f}\nQDM:{stat_b:.3f}",
                        transform=ax.transAxes,
                        va="bottom", ha="right", fontsize=6.0,
                        family="monospace",
                        bbox=dict(boxstyle="round,pad=0.25",
                                  facecolor=C["annot_bg"],
                                  edgecolor="#B0BEC5", lw=0.5, alpha=0.90))

    # hide unused
    for si in range(n, nc * nr_stn):
        for rt in range(2):
            get_ax(rt, si).set_visible(False)

    fig.suptitle(
        "CDF Comparison Overview — All Stations\n"
        f"Observed vs Raw CMIP6 vs Bias-Corrected (QDM)  "
        f"│  Obs: {period_obs}  │  Sim: {period_sim}\n"
        "Top row: linear scale  │  Bottom row: log scale (tail focus)",
        fontsize=11, fontweight="bold", y=1.01)

    handles = [
        Line2D([0],[0], color=C["obs"], lw=1.8, label="Observed"),
        Line2D([0],[0], color=C["raw"], lw=1.6, label="Raw CMIP6"),
        Line2D([0],[0], color=C["bc"],  lw=1.6, label="Bias-Corrected (QDM)"),
        Line2D([0],[0], color=C["p95"], lw=1.0, ls="--", label="P95 (Obs)"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=4,
               fontsize=8.5, frameon=True, edgecolor="#B0BEC5",
               bbox_to_anchor=(0.5, -0.01))

    plt.tight_layout(rect=[0, 0.03, 1, 1])
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}  [CDF OVERVIEW]")


# ═══════════════════════════════════════════════════════════════════════════
# 6.  Q–Q OVERVIEW – ALL STATIONS
# ═══════════════════════════════════════════════════════════════════════════

def plot_qq_overview(all_data, stns, period_obs, period_sim, out_path):
    """2-row × ceil(n/2) overview: Row0=full QQ, Row1=tail QQ."""
    n  = len(stns)
    nc = min(4, n)
    nr_stn = math.ceil(n / nc)
    fig, axes = plt.subplots(2 * nr_stn, nc,
                             figsize=(nc * 4.0, 4.2 * 2 * nr_stn))
    if n == 1:
        axes = axes.reshape(2 * nr_stn, 1)

    def get_ax(row_type, si):
        return axes[si // nc * 2 + row_type, si % nc]

    for si, stn in enumerate(stns):
        d     = all_data[stn]
        obs_w = wet_only(d["obs"])
        raw_w = wet_only(d["raw"])
        bc_w  = wet_only(d["bc"])

        n_pts  = min(len(obs_w), 300)
        probs  = np.linspace(0, 100, n_pts)

        def gq(arr, p):
            if len(arr) < 5: return np.full_like(p, np.nan)
            return np.percentile(arr, p)

        q_obs = gq(obs_w, probs)
        q_raw = gq(raw_w, probs)
        q_bc  = gq(bc_w,  probs)

        for row_type, p_start in enumerate([0, 75]):
            ax = get_ax(row_type, si)
            mask = probs >= p_start
            qo, qr, qb = q_obs[mask], q_raw[mask], q_bc[mask]
            pp = probs[mask]

            x_max = np.nanmax(qo) * 1.05 if len(qo[~np.isnan(qo)]) else 1
            ref   = np.linspace(0, x_max, 200)
            ax.plot(ref, ref, color=C["ref"], lw=1.0, ls="--",
                    alpha=0.70, zorder=1)

            ax.scatter(qo, qr, c=pp, cmap="Reds_r", s=10,
                       alpha=0.65, edgecolors="none", zorder=3)
            ax.scatter(qo, qb, c=pp, cmap="Blues",  s=10,
                       alpha=0.65, edgecolors="none", zorder=4)
            ax.plot(qo, qr, color=C["raw"], lw=1.2, alpha=0.50, zorder=2)
            ax.plot(qo, qb, color=C["bc"],  lw=1.4, alpha=0.80, zorder=5)

            ax.set_title(
                f"Stn {stn}\n"
                f"{'Q–Q (full)' if p_start==0 else 'Q–Q (tail P75+)'}",
                fontsize=7.5, fontweight="bold", pad=2)
            ax.set_xlabel("Obs Q (mm)", fontsize=7, labelpad=2)
            ax.set_ylabel("Model Q (mm)", fontsize=7, labelpad=2)
            ax.tick_params(labelsize=6.5)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.set_aspect("equal", adjustable="datalim")
            ax.set_xlim(left=0); ax.set_ylim(bottom=0)
            ax.grid(True, lw=0.3, ls="--", alpha=0.45)

            # R² mini-annotation
            mask2 = ~np.isnan(qr) & ~np.isnan(qo)
            mask3 = ~np.isnan(qb) & ~np.isnan(qo)
            if mask2.sum() > 2 and mask3.sum() > 2:
                r2r = np.corrcoef(qo[mask2], qr[mask2])[0,1]**2
                r2b = np.corrcoef(qo[mask3], qb[mask3])[0,1]**2
                ax.text(0.03, 0.97,
                        f"R²\nRAW:{r2r:.3f}\nQDM:{r2b:.3f}",
                        transform=ax.transAxes,
                        va="top", fontsize=6.0, family="monospace",
                        bbox=dict(boxstyle="round,pad=0.25",
                                  facecolor=C["annot_bg"],
                                  edgecolor="#B0BEC5", lw=0.5, alpha=0.90))

    for si in range(n, nc * nr_stn):
        for rt in range(2):
            get_ax(rt, si).set_visible(False)

    fig.suptitle(
        "Q–Q Plot Overview — All Stations\n"
        f"Observed vs Raw CMIP6 vs Bias-Corrected (QDM)  "
        f"│  Obs: {period_obs}  │  Sim: {period_sim}\n"
        "Top row: full range  │  Bottom row: upper tail (P75–P100)",
        fontsize=11, fontweight="bold", y=1.01)

    handles = [
        Line2D([0],[0], color=C["obs"], lw=1.8, label="Observed"),
        Line2D([0],[0], color=C["raw"], lw=1.6, label="Raw CMIP6"),
        Line2D([0],[0], color=C["bc"],  lw=1.6, label="Bias-Corrected (QDM)"),
        Line2D([0],[0], color=C["ref"], lw=1.0, ls="--", label="1:1 Reference"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=4,
               fontsize=8.5, frameon=True, edgecolor="#B0BEC5",
               bbox_to_anchor=(0.5, -0.01))

    plt.tight_layout(rect=[0, 0.03, 1, 1])
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}  [Q-Q OVERVIEW]")


# ═══════════════════════════════════════════════════════════════════════════
# 7.  MAIN
# ═══════════════════════════════════════════════════════════════════════════

def get_work_dir():
    try:    return str(Path(os.path.abspath(__file__)).parent)
    except: return os.getcwd()


def main():
    print("=" * 70)
    print("  CDF Comparison & Q–Q Plot")
    print("  Observed vs Raw CMIP6 vs Bias-Corrected (QDM)")
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

    print("  กำลังโหลดข้อมูล ...")
    obs_df, stns = load_daily(obs_path, "Observed")
    raw_df, _    = load_daily(raw_path, "Raw CMIP6")
    bc_df,  _    = load_daily(bc_path,  "BC/QDM")

    def period(df):
        if df is None: return "N/A"
        try:    return f"{df.index[0].year}–{df.index[-1].year}"
        except: return "N/A"

    period_obs = period(obs_df)
    period_sim = period(raw_df) if raw_df is not None else period(bc_df)
    print(f"  สถานี {len(stns)} สถานี  │  Obs: {period_obs}  │  Sim: {period_sim}")

    base_name = Path(obs_path).stem
    fig_dir   = Path(work_dir) / f"Output_CDF_QQ_{base_name}"
    fig_dir.mkdir(exist_ok=True)
    print(f"  Output   : {fig_dir}")
    print("-" * 70)

    # ── Build station data ─────────────────────────────────────────────
    all_data = {}
    for stn in stns:
        stn = str(stn)
        all_data[stn] = {
            "obs": gcol(obs_df, stn),
            "raw": gcol(raw_df, stn),
            "bc":  gcol(bc_df,  stn),
        }

    n_stns = len(stns)

    # ── Per-station CDF ────────────────────────────────────────────────
    print(f"\n  [1/4] CDF รายสถานี ({n_stns} ไฟล์) ...")
    for stn in stns:
        stn = str(stn)
        d   = all_data[stn]
        out = fig_dir / f"Output_CDF_Stn{stn}.png"
        plot_cdf_station(stn, d["obs"], d["raw"], d["bc"],
                         period_obs, period_sim, str(out))

    # ── Per-station Q-Q ────────────────────────────────────────────────
    print(f"\n  [2/4] Q–Q Plot รายสถานี ({n_stns} ไฟล์) ...")
    for stn in stns:
        stn = str(stn)
        d   = all_data[stn]
        out = fig_dir / f"Output_QQ_Stn{stn}.png"
        plot_qq_station(stn, d["obs"], d["raw"], d["bc"],
                        period_obs, period_sim, str(out))

    # ── Overviews ──────────────────────────────────────────────────────
    stns_str = [str(s) for s in stns]

    print("\n  [3/4] CDF Overview (All Stations) ...")
    plot_cdf_overview(all_data, stns_str, period_obs, period_sim,
                      str(fig_dir / "Output_CDF_Overview_AllStations.png"))

    print("\n  [4/4] Q–Q Overview (All Stations) ...")
    plot_qq_overview(all_data, stns_str, period_obs, period_sim,
                     str(fig_dir / "Output_QQ_Overview_AllStations.png"))

    n_out = len(list(fig_dir.glob("*.png")))
    print()
    print("=" * 70)
    print(f"  เสร็จสิ้น – {n_out} ไฟล์รูปภาพ")
    print(f"  บันทึกใน: {fig_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
