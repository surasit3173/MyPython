"""
================================================================================
  Time Series & Seasonal Cycle Analysis  –  v3
  Observed  vs  Raw CMIP6  vs  Bias-Corrected (QDM)
  Multi-Model Ensemble | Journal Standard Q2
--------------------------------------------------------------------------------
  Input  (same folder as this script):
    • Observed  → filename contains "Observed"   (case-insensitive)
    • Raw CMIP6 → filename starts with "pr"      (multiple = multi-model)
    • BC/QDM    → filename starts with "bc"      (multiple = multi-model)

  Columns: YEAR  MONTH  DAY  <stn1>  <stn2>  ...

  Output (Output_TimeSeries_<timestamp>/):
    Fig1_TimeSeries_Annual_EnsFirst.png
    Fig2_TimeSeries_Monthly_EnsFirst.png
    Fig3a_SeasonalCycle_AllModels.png
    Fig3b_SeasonalCycle_EnsembleMean.png
    Fig4_SeasonalCycle_PerStation_Grid.png
    Fig5_MonthlyBiasReduction_3Panel.png
    Fig5a_MonthlyBias_Raw.png
    Fig5b_MonthlyBias_BC.png
    Fig5c_MonthlyBiasReduction.png
    Statistics_Summary.xlsx

  References:
    Cannon et al. (2015) J. Climate 28:6938–6959
    Teutschbein & Seibert (2012) HESS 16:1337–1371
    IPCC AR6 WGI Ch.10 (2021)
================================================================================
"""

import os, sys, warnings
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from openpyxl import Workbook
from openpyxl.styles import (Font, PatternFill, Alignment, Border, Side,
                              GradientFill)
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import ColorScaleRule, DataBarRule
import warnings
warnings.filterwarnings("ignore")

# ══════════════════════════════════════════════════════════════════════════════
# 0.  GLOBAL STYLE  (Q2 journal)
# ══════════════════════════════════════════════════════════════════════════════
FS = dict(
    fig_title = 13,
    ax_title  = 11,
    ax_label  = 10.5,
    tick      = 9.5,
    legend    = 9,
    annot     = 8.5,
    stn_title = 10,    # per-station grid titles
    stn_label = 9,
    stn_tick  = 8,
)

plt.rcParams.update({
    "font.family":        "serif",
    "font.serif":         ["Times New Roman", "DejaVu Serif"],
    "font.size":          FS["tick"],
    "axes.titlesize":     FS["ax_title"],
    "axes.labelsize":     FS["ax_label"],
    "xtick.labelsize":    FS["tick"],
    "ytick.labelsize":    FS["tick"],
    "legend.fontsize":    FS["legend"],
    "figure.titlesize":   FS["fig_title"],
    "lines.linewidth":    1.4,
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
    "savefig.pad_inches": 0.15,
    "mathtext.fontset":   "stix",
    "xtick.major.size":   4.0,
    "ytick.major.size":   4.0,
    "xtick.minor.size":   2.5,
    "ytick.minor.size":   2.5,
    "xtick.direction":    "out",
    "ytick.direction":    "out",
})

# Colour palette (Okabe-Ito colour-blind safe)
C_OBS     = "#1A1A2E"
C_ENS_RAW = "#C62828"
C_ENS_BC  = "#1565C0"
PAL_RAW   = ["#EF5350","#FF7043","#AB47BC","#26A69A","#FFA726"]
PAL_BC    = ["#42A5F5","#26C6DA","#66BB6A","#FFCA28","#8D6E63"]

MONTH_ABBR = ["Jan","Feb","Mar","Apr","May","Jun",
              "Jul","Aug","Sep","Oct","Nov","Dec"]
MISS_VALS  = [-99,-999,-9999,-9.99e+20,9.99e+20,1e+20]

# ══════════════════════════════════════════════════════════════════════════════
# 1.  FILE DISCOVERY & LOADING
# ══════════════════════════════════════════════════════════════════════════════

def find_csv_files(folder):
    all_csv = sorted(Path(folder).glob("*.csv"))
    obs_lst = [f for f in all_csv if "observed" in f.name.lower()]
    raw_lst = [f for f in all_csv if f.name.lower().startswith("pr")]
    bc_lst  = [f for f in all_csv if f.name.lower().startswith("bc")]
    obs_path = str(obs_lst[0]) if obs_lst else None
    print(f"  Observed  : {Path(obs_path).name if obs_path else '(not found)'}")
    print(f"  Raw CMIP6 : {len(raw_lst)} file(s)")
    print(f"  BC/QDM    : {len(bc_lst)} file(s)")
    return obs_path, [str(f) for f in raw_lst], [str(f) for f in bc_lst]

def extract_model_name(filepath):
    stem  = Path(filepath).stem
    parts = stem.split("_")
    skip  = {"pr","day","bc","historical","gn","19810101","20141231",
              "Phetchaburi","phetchaburi"}
    for p in parts:
        if p not in skip and not p.startswith("r") and len(p) > 2:
            return p
    return stem[:20]

def load_daily(csv_path, label):
    if not csv_path or not os.path.isfile(csv_path):
        return None, []
    df = pd.read_csv(csv_path)
    for mv in MISS_VALS:
        df.replace(mv, np.nan, inplace=True)
    num = df.select_dtypes(include=[np.number]).columns
    df[num] = df[num].where(df[num] >= 0)
    stns = [c for c in df.columns if c.upper() not in ("YEAR","MONTH","DAY")]
    try:
        df["date"] = pd.to_datetime(
            {"year":df["YEAR"],"month":df["MONTH"],"day":df["DAY"]})
        df = df.set_index("date")[stns]
    except Exception:
        df = df[stns]
    print(f"    {label:35s}: {len(df):,} rows × {len(stns)} stns")
    return df, stns

def load_all_models(paths, prefix):
    out = {}
    for p in paths:
        name = extract_model_name(p)
        df, _ = load_daily(p, f"{prefix} [{name}]")
        if df is not None:
            out[name] = df
    return out

def ensemble_mean_daily(models_dict):
    if not models_dict:
        return None
    dfs = list(models_dict.values())
    idx  = dfs[0].index
    cols = list(dfs[0].columns)
    for df in dfs[1:]:
        idx  = idx.intersection(df.index)
        cols = [c for c in cols if c in df.columns]
    aligned = [df.loc[idx, cols] for df in dfs]
    stack   = np.stack([a.values for a in aligned], axis=0)
    return pd.DataFrame(np.nanmean(stack, axis=0), index=idx, columns=cols)

# ══════════════════════════════════════════════════════════════════════════════
# 2.  TEMPORAL AGGREGATION
# ══════════════════════════════════════════════════════════════════════════════

def to_monthly(df):
    if df is None: return None
    return df.resample("MS").apply(
        lambda g: g.sum(min_count=max(1, int(0.8*len(g)))))

def to_annual(df):
    if df is None: return None
    return df.resample("YS").apply(
        lambda g: g.sum(min_count=max(1, int(0.8*len(g)))))

def spatial_mean_annual(df):
    if df is None: return None
    a = to_annual(df)
    return a.mean(axis=1) if a is not None else None

def spatial_mean_monthly(df):
    if df is None: return None
    m = to_monthly(df)
    return m.mean(axis=1) if m is not None else None

def seasonal_cycle_spatial(df):
    """Long-term monthly mean – spatial average → Series index 1..12"""
    if df is None: return None
    m  = to_monthly(df)
    sp = m.mean(axis=1)
    return sp.groupby(sp.index.month).mean()

def seasonal_cycle_stn(df, stn):
    if df is None: return None
    stn = str(stn)
    if stn not in df.columns: return None
    m = df[stn].resample("MS").apply(
        lambda g: g.sum(min_count=max(1, int(0.8*len(g)))))
    return m.groupby(m.index.month).mean()

def period_str(df):
    if df is None: return "N/A"
    try: return f"{df.index[0].year}–{df.index[-1].year}"
    except: return "N/A"

# ══════════════════════════════════════════════════════════════════════════════
# 3.  SHARED PLOT HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _style_ax(ax, ylabel="", xlabel="", title=""):
    ax.set_ylabel(ylabel, labelpad=6, fontsize=FS["ax_label"])
    ax.set_xlabel(xlabel, labelpad=5, fontsize=FS["ax_label"])
    if title:
        ax.set_title(title, loc="left", fontweight="bold",
                     fontsize=FS["ax_title"], pad=7)
    ax.yaxis.set_minor_locator(ticker.AutoMinorLocator(4))
    ax.tick_params(which="both", direction="out",
                   labelsize=FS["tick"])
    ax.set_ylim(bottom=0)

def _wet_shade(ax, x_arr=None, is_monthly_idx=False):
    """Shade May–Oct wet season on month-based axes."""
    if x_arr is None:
        ax.axvspan(4.55, 10.45, alpha=0.07, color="#1565C0", zorder=0)
    else:
        ax.axvspan(x_arr[4]-0.45, x_arr[9]+0.45,
                   alpha=0.07, color="#1565C0", zorder=0)

def _obs_line():
    return Line2D([0],[0], color=C_OBS, lw=2.0, label="Observed")
def _ens_raw_line():
    return Line2D([0],[0], color=C_ENS_RAW, lw=1.8, ls="--",
                  label="Ensemble Mean (CMIP6 Raw)")
def _ens_bc_line():
    return Line2D([0],[0], color=C_ENS_BC, lw=1.8, ls="-.",
                  label="Ensemble Mean (Bias-Corrected)")

def _shade_spread(ax, series_list, color, alpha=0.12):
    valid = [s for s in series_list if s is not None and len(s)>0]
    if len(valid) < 2: return
    common = valid[0].index
    for s in valid[1:]:
        common = common.intersection(s.index)
    if len(common) == 0: return
    mat = np.stack([s.loc[common].values for s in valid])
    ax.fill_between(common.year, np.nanmin(mat,0), np.nanmax(mat,0),
                    color=color, alpha=alpha, zorder=2)

def _save(fig, path):
    plt.tight_layout()
    fig.savefig(path, dpi=300)
    plt.close(fig)
    print(f"    ✓  {Path(path).name}")

# ══════════════════════════════════════════════════════════════════════════════
# 4.  FIG 1  –  ANNUAL TIME SERIES  (Ensemble panel FIRST)
#     Panel order: (a) Ensemble Mean → (b,c,...) individual models
# ══════════════════════════════════════════════════════════════════════════════

def fig1_annual_timeseries(obs_d, raw_models, bc_models,
                           ens_raw_d, ens_bc_d, period_obs, out_path, stns):

    model_names = sorted(set(list(raw_models)+list(bc_models)))
    n_models    = len(model_names)
    n_panels    = min(n_models + 1, 5)

    fig, axes = plt.subplots(n_panels, 1,
                             figsize=(14, n_panels*3.0 + 1.0),
                             sharex=False)
    if n_panels == 1: axes = [axes]

    obs_ann     = spatial_mean_annual(obs_d)
    ens_raw_ann = spatial_mean_annual(ens_raw_d)
    ens_bc_ann  = spatial_mean_annual(ens_bc_d)

    # ── Panel (a): Ensemble Mean ─────────────────────────────────────────────
    ax = axes[0]
    if len(raw_models) > 1:
        _shade_spread(ax,
                      [spatial_mean_annual(df) for df in raw_models.values()],
                      C_ENS_RAW)
    if len(bc_models) > 1:
        _shade_spread(ax,
                      [spatial_mean_annual(df) for df in bc_models.values()],
                      C_ENS_BC)
    if obs_ann is not None:
        ax.plot(obs_ann.index.year, obs_ann.values,
                color=C_OBS, lw=2.0, zorder=6, label="Observed")
    if ens_raw_ann is not None:
        ax.plot(ens_raw_ann.index.year, ens_raw_ann.values,
                color=C_ENS_RAW, lw=1.9, ls="--",
                label="Ensemble Mean (CMIP6 Raw)", zorder=5)
    if ens_bc_ann is not None:
        ax.plot(ens_bc_ann.index.year, ens_bc_ann.values,
                color=C_ENS_BC, lw=1.9, ls="-.",
                label="Ensemble Mean (Bias-Corrected)", zorder=5)

    _style_ax(ax,
              ylabel="Annual Total Rainfall (mm)",
              title="(a)  Ensemble Mean — All Models")
    ax.legend(loc="upper right", fontsize=FS["legend"],
              framealpha=0.92, edgecolor="#90A4AE")
    ax.xaxis.set_major_locator(ticker.MultipleLocator(5))
    ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))

    # ── Panels (b, c, ...): Individual models ────────────────────────────────
    for mi, mname in enumerate(model_names[:n_panels-1]):
        ax = axes[mi+1]
        if obs_ann is not None:
            ax.plot(obs_ann.index.year, obs_ann.values,
                    color=C_OBS, lw=1.8, alpha=0.80, label="Observed")
        raw_ann = spatial_mean_annual(raw_models.get(mname))
        bc_ann  = spatial_mean_annual(bc_models.get(mname))
        if raw_ann is not None:
            ax.plot(raw_ann.index.year, raw_ann.values,
                    color=PAL_RAW[mi%len(PAL_RAW)], lw=1.5, ls="--",
                    alpha=0.88, label=f"Raw CMIP6 [{mname}]")
        if bc_ann is not None:
            ax.plot(bc_ann.index.year, bc_ann.values,
                    color=PAL_BC[mi%len(PAL_BC)], lw=1.5, ls="-.",
                    alpha=0.88, label=f"BC/QDM [{mname}]")
        _style_ax(ax,
                  ylabel="Annual Total Rainfall (mm)",
                  title=f"({chr(98+mi)})  Model: {mname}")
        ax.legend(loc="upper right", fontsize=FS["legend"],
                  framealpha=0.90, edgecolor="#90A4AE")
        ax.xaxis.set_major_locator(ticker.MultipleLocator(5))
        ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))

    axes[-1].set_xlabel("Year", fontsize=FS["ax_label"])

    fig.suptitle(
        f"Annual Total Rainfall Time Series — Spatial Mean ({len(stns)} Stations)  |  {period_obs}",
        fontsize=FS["fig_title"], fontweight="bold", y=1.003)

    _save(fig, out_path)

# ══════════════════════════════════════════════════════════════════════════════
# 5.  FIG 2  –  MONTHLY TIME SERIES  (Ensemble panel FIRST)
# ══════════════════════════════════════════════════════════════════════════════

def fig2_monthly_timeseries(obs_d, raw_models, bc_models,
                            ens_raw_d, ens_bc_d, period_obs, out_path, stns):

    model_names = sorted(set(list(raw_models)+list(bc_models)))
    n_models    = len(model_names)
    n_panels    = min(n_models + 1, 5)

    fig, axes = plt.subplots(n_panels, 1,
                             figsize=(15, n_panels*3.0 + 1.0),
                             sharex=False)
    if n_panels == 1: axes = [axes]

    obs_mon     = spatial_mean_monthly(obs_d)
    ens_raw_mon = spatial_mean_monthly(ens_raw_d)
    ens_bc_mon  = spatial_mean_monthly(ens_bc_d)

    # ── Panel (a): Ensemble Mean ─────────────────────────────────────────────
    ax = axes[0]
    if obs_mon is not None:
        ax.plot(obs_mon.index, obs_mon.values,
                color=C_OBS, lw=1.8, alpha=0.80, zorder=6, label="Observed")
    if ens_raw_mon is not None:
        ax.plot(ens_raw_mon.index, ens_raw_mon.values,
                color=C_ENS_RAW, lw=1.8, ls="--",
                label="Ensemble Mean (CMIP6 Raw)", zorder=5)
    if ens_bc_mon is not None:
        ax.plot(ens_bc_mon.index, ens_bc_mon.values,
                color=C_ENS_BC, lw=1.8, ls="-.",
                label="Ensemble Mean (Bias-Corrected)", zorder=5)
    _style_ax(ax,
              ylabel="Monthly Rainfall (mm)",
              title="(a)  Ensemble Mean — Monthly Time Series")
    ax.legend(loc="upper right", fontsize=FS["legend"],
              framealpha=0.92, edgecolor="#90A4AE")
    ax.xaxis.set_major_locator(mdates.YearLocator(5))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_minor_locator(mdates.YearLocator(1))

    # ── Panels (b, c, ...): Individual models ────────────────────────────────
    for mi, mname in enumerate(model_names[:n_panels-1]):
        ax = axes[mi+1]
        if obs_mon is not None:
            ax.plot(obs_mon.index, obs_mon.values,
                    color=C_OBS, lw=1.6, alpha=0.70, label="Observed")
        raw_mon = spatial_mean_monthly(raw_models.get(mname))
        bc_mon  = spatial_mean_monthly(bc_models.get(mname))
        if raw_mon is not None:
            ax.plot(raw_mon.index, raw_mon.values,
                    color=PAL_RAW[mi%len(PAL_RAW)], lw=1.3, ls="--",
                    alpha=0.85, label=f"Raw CMIP6 [{mname}]")
        if bc_mon is not None:
            ax.plot(bc_mon.index, bc_mon.values,
                    color=PAL_BC[mi%len(PAL_BC)], lw=1.3, ls="-.",
                    alpha=0.85, label=f"BC/QDM [{mname}]")
        _style_ax(ax,
                  ylabel="Monthly Rainfall (mm)",
                  title=f"({chr(98+mi)})  Model: {mname}")
        ax.legend(loc="upper right", fontsize=FS["legend"],
                  framealpha=0.90, edgecolor="#90A4AE")
        ax.xaxis.set_major_locator(mdates.YearLocator(5))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.xaxis.set_minor_locator(mdates.YearLocator(1))

    axes[-1].set_xlabel("Year", fontsize=FS["ax_label"])

    fig.suptitle(
        f"Monthly Rainfall Time Series — Spatial Mean ({len(stns)} Stations)  |  {period_obs}",
        fontsize=FS["fig_title"], fontweight="bold", y=1.003)

    _save(fig, out_path)

# ══════════════════════════════════════════════════════════════════════════════
# 6.  FIG 3a  –  SEASONAL CYCLE: All Models + Ensemble Mean
# ══════════════════════════════════════════════════════════════════════════════

def fig3a_seasonal_all_models(obs_d, raw_models, bc_models,
                              ens_raw_d, ens_bc_d, period_obs, out_path, stns):

    fig, ax = plt.subplots(figsize=(13, 6.5))
    x = np.arange(1, 13)

    obs_sc = seasonal_cycle_spatial(obs_d)
    if obs_sc is not None:
        ax.bar(x, obs_sc.values, width=0.40, color="#CFD8DC",
               edgecolor=C_OBS, linewidth=0.8,
               label="Observed", zorder=3, align="center")

    # Individual raw (muted thin lines)
    for mi, (mname, df) in enumerate(raw_models.items()):
        sc = seasonal_cycle_spatial(df)
        if sc is not None:
            ax.plot(x, sc.values, color=PAL_RAW[mi%len(PAL_RAW)],
                    lw=1.0, ls="--", alpha=0.60, marker="o",
                    markersize=3.0, zorder=4,
                    label=f"Raw CMIP6 [{mname}]")

    # Individual BC (muted thin lines)
    for mi, (mname, df) in enumerate(bc_models.items()):
        sc = seasonal_cycle_spatial(df)
        if sc is not None:
            ax.plot(x, sc.values, color=PAL_BC[mi%len(PAL_BC)],
                    lw=1.0, ls="-.", alpha=0.60, marker="s",
                    markersize=3.0, zorder=4,
                    label=f"BC/QDM [{mname}]")

    # Ensemble Mean (bold)
    ens_raw_sc = seasonal_cycle_spatial(ens_raw_d)
    ens_bc_sc  = seasonal_cycle_spatial(ens_bc_d)
    if ens_raw_sc is not None:
        ax.plot(x, ens_raw_sc.values, color=C_ENS_RAW, lw=2.4, ls="--",
                marker="D", markersize=6.5, zorder=6,
                label="Ensemble Mean (CMIP6 Raw)")
    if ens_bc_sc is not None:
        ax.plot(x, ens_bc_sc.values, color=C_ENS_BC, lw=2.4, ls="-.",
                marker="^", markersize=6.5, zorder=6,
                label="Ensemble Mean (Bias-Corrected)")

    _wet_shade(ax, x)
    ymax = ax.get_ylim()[1]
    ax.text(7.5, ymax*0.95, "Wet Season", fontsize=FS["annot"],
            color="#1565C0", ha="center", fontstyle="italic")

    ax.set_xticks(x)
    ax.set_xticklabels(MONTH_ABBR, fontsize=FS["tick"])
    _style_ax(ax,
              ylabel="Mean Monthly Rainfall (mm)",
              xlabel="Month",
              title=f"Seasonal Cycle of Monthly Rainfall — All Models + Ensemble Mean  |  {period_obs}")

    ax.legend(loc="upper left", fontsize=FS["legend"],
              framealpha=0.92, edgecolor="#90A4AE",
              ncol=2 if (len(raw_models)+len(bc_models))>4 else 1)

    fig.suptitle(
        f"Seasonal Cycle: All CMIP6 Models + Ensemble Mean — Spatial Mean ({len(stns)} Stations)",
        fontsize=FS["fig_title"], fontweight="bold")

    _save(fig, out_path)

# ══════════════════════════════════════════════════════════════════════════════
# 7.  FIG 3b  –  SEASONAL CYCLE: Ensemble Mean Only (clean)
# ══════════════════════════════════════════════════════════════════════════════

def fig3b_seasonal_ensemble(obs_d, ens_raw_d, ens_bc_d,
                             period_obs, out_path, stns):

    fig, ax = plt.subplots(figsize=(12, 6.0))
    x = np.arange(1, 13)

    obs_sc     = seasonal_cycle_spatial(obs_d)
    ens_raw_sc = seasonal_cycle_spatial(ens_raw_d)
    ens_bc_sc  = seasonal_cycle_spatial(ens_bc_d)

    if obs_sc is not None:
        ax.bar(x, obs_sc.values, width=0.42, color="#CFD8DC",
               edgecolor=C_OBS, linewidth=0.9,
               label="Observed", zorder=3, align="center")
    if ens_raw_sc is not None:
        ax.plot(x, ens_raw_sc.values, color=C_ENS_RAW, lw=2.5, ls="--",
                marker="D", markersize=7.0, zorder=5,
                label="Ensemble Mean (CMIP6 Raw)")
    if ens_bc_sc is not None:
        ax.plot(x, ens_bc_sc.values, color=C_ENS_BC, lw=2.5, ls="-.",
                marker="^", markersize=7.0, zorder=5,
                label="Ensemble Mean (Bias-Corrected)")

    # Bias reduction annotation at peak month
    if obs_sc is not None and ens_raw_sc is not None and ens_bc_sc is not None:
        peak_m = int(obs_sc.idxmax())
        ov = float(obs_sc.loc[peak_m])
        rv = float(ens_raw_sc.loc[peak_m])
        bv = float(ens_bc_sc.loc[peak_m])
        delta = abs(rv - bv)
        ax.annotate("", xy=(peak_m, bv), xytext=(peak_m, rv),
                    arrowprops=dict(arrowstyle="<->",
                                   color="#E65100", lw=1.8), zorder=7)
        ax.text(peak_m + 0.25, (rv+bv)/2,
                f"Bias reduction\n{delta:.0f} mm ({abs(rv-ov)/ov*100:.0f}% → {abs(bv-ov)/ov*100:.0f}%)",
                fontsize=FS["annot"], color="#E65100", va="center",
                fontweight="bold")

    _wet_shade(ax, x)
    ymax = ax.get_ylim()[1]
    ax.text(7.5, ymax*0.95, "Wet Season", fontsize=FS["annot"],
            color="#1565C0", ha="center", fontstyle="italic")

    ax.set_xticks(x)
    ax.set_xticklabels(MONTH_ABBR, fontsize=FS["tick"])
    _style_ax(ax,
              ylabel="Mean Monthly Rainfall (mm)",
              xlabel="Month",
              title=f"Seasonal Cycle of Monthly Rainfall — Ensemble Mean Comparison  |  {period_obs}")

    ax.legend(loc="upper left", fontsize=FS["legend"]+0.5,
              framealpha=0.92, edgecolor="#90A4AE")

    fig.suptitle(
        f"Seasonal Cycle: Ensemble Mean — Observed vs CMIP6 Raw vs Bias-Corrected  |  {len(stns)} Stations",
        fontsize=FS["fig_title"], fontweight="bold")

    _save(fig, out_path)

# ══════════════════════════════════════════════════════════════════════════════
# 8.  FIG 4  –  SEASONAL CYCLE PER STATION  (enlarged labels)
# ══════════════════════════════════════════════════════════════════════════════

def fig4_seasonal_per_station(stns, obs_d, ens_raw_d, ens_bc_d,
                               period_obs, out_path):

    n     = len(stns)
    ncols = min(5, n)
    nrows = (n + ncols - 1) // ncols

    # Larger figure per cell for bigger fonts
    cell_w, cell_h = 3.8, 3.6
    fig_w = ncols * cell_w
    fig_h = nrows * cell_h + 1.8

    fig, axes = plt.subplots(nrows, ncols, figsize=(fig_w, fig_h),
                             squeeze=False)
    x = np.arange(1, 13)

    for idx, stn in enumerate(stns):
        row = idx // ncols
        col = idx % ncols
        ax  = axes[row][col]
        stn = str(stn)

        obs_sc = seasonal_cycle_stn(obs_d,     stn)
        ens_r  = seasonal_cycle_stn(ens_raw_d, stn)
        ens_b  = seasonal_cycle_stn(ens_bc_d,  stn)

        if obs_sc is not None:
            ax.bar(x, obs_sc.values, width=0.45,
                   color="#CFD8DC", edgecolor=C_OBS,
                   linewidth=0.7, zorder=3)
        if ens_r is not None:
            ax.plot(x, ens_r.values, color=C_ENS_RAW,
                    lw=1.8, ls="--", marker="o",
                    markersize=3.5, zorder=5)
        if ens_b is not None:
            ax.plot(x, ens_b.values, color=C_ENS_BC,
                    lw=1.8, ls="-.", marker="^",
                    markersize=3.5, zorder=5)

        # Station title (enlarged, bold)
        ax.set_title(f"Station {stn}", fontsize=FS["stn_title"],
                     fontweight="bold", pad=5)

        # Axis labels (only left/bottom edge cells)
        ax.set_xticks(x[::2])
        ax.set_xticklabels(MONTH_ABBR[::2], fontsize=FS["stn_tick"])
        if col == 0:
            ax.set_ylabel("Rainfall (mm)", fontsize=FS["stn_label"],
                          labelpad=4)
        else:
            ax.set_ylabel("")
        ax.tick_params(axis="y", labelsize=FS["stn_tick"])
        ax.set_ylim(bottom=0)
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator(2))
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(True, axis="y", ls="--", lw=0.3, alpha=0.45)
        _wet_shade(ax, x)

    # Hide unused cells
    for idx in range(n, nrows*ncols):
        axes[idx//ncols][idx%ncols].set_visible(False)

    # Shared legend (larger)
    handles = [
        mpatches.Patch(facecolor="#CFD8DC", edgecolor=C_OBS,
                       label="Observed"),
        Line2D([0],[0], color=C_ENS_RAW, lw=1.8, ls="--",
               marker="o", markersize=5,
               label="Ensemble Mean (CMIP6 Raw)"),
        Line2D([0],[0], color=C_ENS_BC, lw=1.8, ls="-.",
               marker="^", markersize=5,
               label="Ensemble Mean (Bias-Corrected)"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=3,
               fontsize=FS["legend"]+1, framealpha=0.92,
               edgecolor="#90A4AE", bbox_to_anchor=(0.5, -0.01))

    fig.suptitle(
        f"Seasonal Cycle of Monthly Rainfall — Per Station  |  {period_obs}",
        fontsize=FS["fig_title"], fontweight="bold", y=1.003)

    plt.tight_layout(rect=[0, 0.05, 1, 1])
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")

# ══════════════════════════════════════════════════════════════════════════════
# 9.  FIG 5  –  MONTHLY BIAS REDUCTION  (3-panel combined + 3 singles)
# ══════════════════════════════════════════════════════════════════════════════

def _build_bias_matrices(stns, obs_d, ens_raw_d, ens_bc_d):
    """Returns raw_bias, bc_bias, reduction  (n_stn × 12) arrays."""
    n = len(stns)
    raw_bias = np.full((n, 12), np.nan)
    bc_bias  = np.full((n, 12), np.nan)
    for si, stn in enumerate(stns):
        stn = str(stn)
        obs_sc = seasonal_cycle_stn(obs_d,     stn)
        raw_sc = seasonal_cycle_stn(ens_raw_d, stn)
        bc_sc  = seasonal_cycle_stn(ens_bc_d,  stn)
        for mi, month in enumerate(range(1,13)):
            if obs_sc is None or month not in obs_sc.index: continue
            ov = float(obs_sc.loc[month])
            if ov == 0 or np.isnan(ov): continue
            if raw_sc is not None and month in raw_sc.index:
                raw_bias[si,mi] = (raw_sc.loc[month]-ov)/ov*100
            if bc_sc is not None and month in bc_sc.index:
                bc_bias[si,mi]  = (bc_sc.loc[month]-ov)/ov*100
    reduction = raw_bias - bc_bias
    return raw_bias, bc_bias, reduction

def _heatmap_panel(ax, mat, title, stns, vmin=-100, vmax=100, cmap="RdBu_r",
                   cbar_label="%", fig=None):
    n_stn, n_mon = mat.shape
    im = ax.imshow(mat, aspect="auto", cmap=cmap,
                   vmin=vmin, vmax=vmax, interpolation="nearest")
    ax.set_xticks(range(n_mon))
    ax.set_xticklabels(MONTH_ABBR, fontsize=FS["tick"])
    ax.set_yticks(range(n_stn))
    ax.set_yticklabels([f"Stn {s}" for s in stns], fontsize=FS["tick"])
    ax.set_title(title, fontsize=FS["ax_title"], fontweight="bold", pad=7)
    ax.set_xlabel("Month", fontsize=FS["ax_label"])
    # Cell text
    for i in range(n_stn):
        for j in range(n_mon):
            v = mat[i,j]
            if not np.isnan(v):
                txt_col = "white" if abs(v) > 65 else "black"
                ax.text(j, i, f"{v:.0f}", ha="center", va="center",
                        fontsize=7.5, color=txt_col, fontweight="normal")
    if fig is not None:
        cb = fig.colorbar(im, ax=ax, shrink=0.80, pad=0.02)
        cb.ax.tick_params(labelsize=FS["tick"]-1)
        cb.set_label(cbar_label, fontsize=FS["ax_label"]-1)
    return im

def fig5_bias_3panel(stns, obs_d, ens_raw_d, ens_bc_d, period_obs, out_path):
    raw_bias, bc_bias, reduction = _build_bias_matrices(stns, obs_d, ens_raw_d, ens_bc_d)
    n_stn = len(stns)
    fig_h = max(6, n_stn*0.65 + 3.0)

    fig, axes = plt.subplots(1, 3, figsize=(20, fig_h))

    _heatmap_panel(axes[0], raw_bias,
                   "(a)  Raw CMIP6 Bias (%)\n(Ensemble Mean vs Observed)",
                   stns, fig=fig)
    _heatmap_panel(axes[1], bc_bias,
                   "(b)  Bias-Corrected Bias (%)\n(Ensemble Mean vs Observed)",
                   stns, fig=fig)
    _heatmap_panel(axes[2], reduction,
                   "(c)  Bias Reduction (%)\n(Raw − BC; positive = improvement)",
                   stns, vmin=-100, vmax=100, cmap="RdYlGn", fig=fig)

    fig.suptitle(
        f"Monthly Relative Bias and Bias Reduction — Per Station  |  {period_obs}",
        fontsize=FS["fig_title"], fontweight="bold")

    _save(fig, out_path)
    return raw_bias, bc_bias, reduction

def _single_heatmap(mat, title, suptitle, stns, out_path,
                    vmin=-100, vmax=100, cmap="RdBu_r",
                    cbar_label="Relative Bias (%)"):
    n_stn = len(stns)
    fig_w = max(12, 14)
    fig_h = max(5, n_stn*0.65 + 2.5)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    im = _heatmap_panel(ax, mat, title, stns,
                        vmin=vmin, vmax=vmax, cmap=cmap, fig=fig,
                        cbar_label=cbar_label)
    fig.suptitle(suptitle, fontsize=FS["fig_title"], fontweight="bold")
    _save(fig, out_path)

# ══════════════════════════════════════════════════════════════════════════════
# 10.  STATISTICS SUMMARY  →  Excel
# ══════════════════════════════════════════════════════════════════════════════

def compute_all_stats(stns, obs_d, raw_models, bc_models,
                      ens_raw_d, ens_bc_d):
    """
    Returns dict of DataFrames:
      'annual_stats'     – annual mean/std/cv per station × dataset
      'seasonal_cycle'   – monthly climatology (spatial mean)
      'monthly_bias'     – raw_bias, bc_bias, reduction per station × month
      'performance'      – Bias%, RMSE, Pearson r per station × (Raw/BC)
    """

    # ── Annual descriptive stats ──────────────────────────────────────────────
    ann_records = []
    datasets = {"Observed": obs_d,
                "Ensemble Mean (Raw)": ens_raw_d,
                "Ensemble Mean (BC)":  ens_bc_d}
    # Add individual models
    for m, df in raw_models.items():
        datasets[f"Raw [{m}]"] = df
    for m, df in bc_models.items():
        datasets[f"BC [{m}]"] = df

    for ds_name, df in datasets.items():
        if df is None: continue
        ann = to_annual(df)
        if ann is None: continue
        for stn in stns:
            stn = str(stn)
            if stn not in ann.columns: continue
            v = ann[stn].dropna().values
            if len(v) < 2: continue
            ann_records.append({
                "Dataset":    ds_name,
                "Station":    stn,
                "N_years":    len(v),
                "Mean (mm)":  round(float(np.nanmean(v)), 1),
                "Std (mm)":   round(float(np.nanstd(v,ddof=1)), 1),
                "CV (%)":     round(float(np.nanstd(v,ddof=1)/np.nanmean(v)*100), 1),
                "Min (mm)":   round(float(np.nanmin(v)), 1),
                "Max (mm)":   round(float(np.nanmax(v)), 1),
                "Median (mm)":round(float(np.nanmedian(v)), 1),
            })
    df_ann = pd.DataFrame(ann_records)

    # ── Seasonal cycle (monthly climatology, spatial mean) ────────────────────
    sc_records = []
    for ds_name, df in datasets.items():
        if df is None: continue
        sc = seasonal_cycle_spatial(df)
        if sc is None: continue
        for mi, month in enumerate(range(1,13)):
            if month not in sc.index: continue
            sc_records.append({
                "Dataset":    ds_name,
                "Month":      MONTH_ABBR[mi],
                "Month_No":   month,
                "Mean (mm)":  round(float(sc.loc[month]), 2),
            })
    df_sc = pd.DataFrame(sc_records)

    # ── Monthly bias per station ──────────────────────────────────────────────
    raw_bias, bc_bias, reduction = _build_bias_matrices(stns, obs_d, ens_raw_d, ens_bc_d)
    bias_rows = []
    for si, stn in enumerate(stns):
        for mi, month in enumerate(range(1,13)):
            bias_rows.append({
                "Station":        str(stn),
                "Month":          MONTH_ABBR[mi],
                "Month_No":       month,
                "Raw_Bias (%)":   round(raw_bias[si,mi], 1) if not np.isnan(raw_bias[si,mi]) else "",
                "BC_Bias (%)":    round(bc_bias[si,mi], 1)  if not np.isnan(bc_bias[si,mi])  else "",
                "Bias_Reduction (%)": round(reduction[si,mi], 1) if not np.isnan(reduction[si,mi]) else "",
            })
    df_bias = pd.DataFrame(bias_rows)

    # ── Performance metrics: Bias%, RMSE, Pearson r per station ──────────────
    perf_rows = []
    for si, stn in enumerate(stns):
        stn = str(stn)
        obs_a = to_annual(obs_d)
        if obs_a is None or stn not in obs_a.columns: continue
        obs_v = obs_a[stn].dropna().values

        for ds_tag, df_sim in [("Ensemble Mean (Raw)", ens_raw_d),
                                ("Ensemble Mean (BC)",  ens_bc_d)]:
            if df_sim is None: continue
            sim_a = to_annual(df_sim)
            if sim_a is None or stn not in sim_a.columns: continue
            sim_v = sim_a[stn].dropna().values
            n = min(len(obs_v), len(sim_v))
            if n < 3: continue
            ov, sv = obs_v[:n], sim_v[:n]
            bias = (np.mean(sv)-np.mean(ov))/np.mean(ov)*100
            rmse = np.sqrt(np.mean((sv-ov)**2))
            nse  = 1 - np.sum((ov-sv)**2)/np.sum((ov-np.mean(ov))**2)
            r    = np.corrcoef(ov,sv)[0,1] if ov.std()>0 and sv.std()>0 else np.nan
            perf_rows.append({
                "Station":        stn,
                "Dataset":        ds_tag,
                "N_years":        n,
                "Bias (%)":       round(bias, 2),
                "RMSE (mm)":      round(rmse, 1),
                "NSE":            round(nse, 3),
                "Pearson_r":      round(r, 3),
                "R²":             round(r**2, 3) if not np.isnan(r) else "",
            })
    df_perf = pd.DataFrame(perf_rows)

    return df_ann, df_sc, df_bias, df_perf, raw_bias, bc_bias, reduction


def write_excel(df_ann, df_sc, df_bias, df_perf,
                raw_bias, bc_bias, reduction,
                stns, period_obs, out_path):
    """Write formatted Excel workbook with multiple sheets."""
    wb = Workbook()

    # ── Style definitions ─────────────────────────────────────────────────────
    def hdr_font(bold=True, sz=11): return Font(name="Arial", bold=bold, size=sz)
    def cell_font(sz=10):           return Font(name="Arial", size=sz)

    HDR_FILL_BLUE  = PatternFill("solid", fgColor="1565C0")
    HDR_FILL_RED   = PatternFill("solid", fgColor="C62828")
    HDR_FILL_GREY  = PatternFill("solid", fgColor="455A64")
    HDR_FILL_GREEN = PatternFill("solid", fgColor="2E7D32")
    HDR_FILL_AMB   = PatternFill("solid", fgColor="E65100")
    WHITE_FONT     = Font(name="Arial", bold=True, color="FFFFFF", size=11)
    CTR            = Alignment(horizontal="center", vertical="center", wrap_text=True)
    LEFT           = Alignment(horizontal="left",   vertical="center")
    thin  = Side(style="thin",   color="B0BEC5")
    thick = Side(style="medium", color="455A64")
    BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)

    def write_df(ws, df, hdr_fill, start_row=3, freeze=True):
        # Header
        for ci, col in enumerate(df.columns, 1):
            c = ws.cell(row=start_row, column=ci, value=col)
            c.font    = WHITE_FONT
            c.fill    = hdr_fill
            c.alignment = CTR
            c.border  = BORDER
        # Data
        for ri, row in df.iterrows():
            for ci, val in enumerate(row, 1):
                c = ws.cell(row=start_row+1+ri, column=ci,
                            value=None if val == "" else val)
                c.font      = cell_font()
                c.alignment = CTR if ci > 1 else LEFT
                c.border    = BORDER
                # Alternate row shading
                if ri % 2 == 0:
                    c.fill = PatternFill("solid", fgColor="F5F5F5")
        # Auto-width
        for ci, col in enumerate(df.columns, 1):
            max_len = max(len(str(col)),
                         max((len(str(df.iloc[ri][col]))
                              for ri in range(min(len(df),50))), default=0))
            ws.column_dimensions[get_column_letter(ci)].width = min(max_len+3, 28)
        if freeze:
            ws.freeze_panes = ws.cell(row=start_row+1, column=1)

    def sheet_title(ws, title, subtitle=""):
        ws.merge_cells("A1:P1")
        c = ws["A1"]
        c.value     = title
        c.font      = Font(name="Arial", bold=True, size=14, color="1A237E")
        c.alignment = CTR
        if subtitle:
            ws.merge_cells("A2:P2")
            d = ws["A2"]
            d.value     = subtitle
            d.font      = Font(name="Arial", size=10, color="546E7A", italic=True)
            d.alignment = CTR
        ws.row_dimensions[1].height = 26
        ws.row_dimensions[2].height = 18

    # ── Sheet 0: Cover ────────────────────────────────────────────────────────
    ws0 = wb.active
    ws0.title = "Cover"
    ws0.sheet_view.showGridLines = False
    ws0.column_dimensions["A"].width = 5
    ws0.column_dimensions["B"].width = 45
    ws0.column_dimensions["C"].width = 45

    info = [
        ("Report Title",   "Time Series & Seasonal Cycle — Statistical Summary"),
        ("Study Area",     "Phetchaburi Province, Thailand"),
        ("Period",         period_obs),
        ("Stations",       f"{len(stns)} stations: " + ", ".join(stns)),
        ("Data Sources",   "Observed (gauge), Raw CMIP6, Bias-Corrected (QDM)"),
        ("Generated",      datetime.now().strftime("%Y-%m-%d %H:%M")),
        ("Reference",      "Cannon et al. (2015) J.Clim; Teutschbein & Seibert (2012) HESS"),
    ]
    ws0.merge_cells("B2:C2")
    ws0["B2"].value     = "Statistical Summary Report"
    ws0["B2"].font      = Font(name="Arial", bold=True, size=18, color="1A237E")
    ws0["B2"].alignment = CTR
    ws0.row_dimensions[2].height = 36

    for ri, (k, v) in enumerate(info, 4):
        ws0.cell(ri, 2, k).font      = Font(name="Arial", bold=True, size=11)
        ws0.cell(ri, 2, k).fill      = PatternFill("solid", fgColor="E3F2FD")
        ws0.cell(ri, 2, k).border    = BORDER
        ws0.cell(ri, 2, k).alignment = LEFT
        ws0.cell(ri, 3, v).font      = Font(name="Arial", size=11)
        ws0.cell(ri, 3, v).border    = BORDER
        ws0.cell(ri, 3, v).alignment = LEFT
        ws0.row_dimensions[ri].height = 20

    # ── Sheet 1: Annual Descriptive Stats ─────────────────────────────────────
    ws1 = wb.create_sheet("1_Annual_Statistics")
    sheet_title(ws1, "Annual Rainfall Statistics — Per Station × Dataset",
                f"Period: {period_obs}  |  Units: mm/year")
    write_df(ws1, df_ann, HDR_FILL_BLUE)

    # Conditional format on Mean column (col D = index 4)
    ws1.conditional_formatting.add(
        f"D4:D{3+len(df_ann)+1}",
        ColorScaleRule(start_type="min", start_color="FFCDD2",
                       mid_type="percentile", mid_value=50, mid_color="FFFFFF",
                       end_type="max", end_color="BBDEFB"))

    # ── Sheet 2: Seasonal Cycle ────────────────────────────────────────────────
    ws2 = wb.create_sheet("2_Seasonal_Cycle")
    sheet_title(ws2, "Seasonal Cycle — Long-Term Monthly Mean Rainfall (Spatial Average)",
                f"Period: {period_obs}  |  Units: mm/month")
    write_df(ws2, df_sc, HDR_FILL_GREY)

    # ── Sheet 3: Monthly Bias ──────────────────────────────────────────────────
    ws3 = wb.create_sheet("3_Monthly_Bias_PerStation")
    sheet_title(ws3, "Monthly Relative Bias (%) — Ensemble Mean vs Observed  |  Per Station",
                "Bias (%) = (Ensemble Mean − Observed) / Observed × 100")
    write_df(ws3, df_bias, HDR_FILL_RED)

    # Colour scale on bias columns (E, F, G)
    n_rows = len(df_bias) + 4
    for col_letter in ["E","F"]:
        ws3.conditional_formatting.add(
            f"{col_letter}4:{col_letter}{n_rows}",
            ColorScaleRule(start_type="num",  start_value=-100, start_color="C62828",
                           mid_type="num",    mid_value=0,       mid_color="FFFFFF",
                           end_type="num",    end_value=100,     end_color="1565C0"))
    ws3.conditional_formatting.add(
        f"G4:G{n_rows}",
        ColorScaleRule(start_type="num",  start_value=-100, start_color="C62828",
                       mid_type="num",    mid_value=0,       mid_color="FFFFFF",
                       end_type="num",    end_value=100,     end_color="2E7D32"))

    # ── Sheet 4: Performance Metrics ─────────────────────────────────────────
    ws4 = wb.create_sheet("4_Performance_Metrics")
    sheet_title(ws4, "Model Performance Metrics — Annual Scale  |  Per Station",
                "Bias(%) = (sim−obs)/obs×100  |  RMSE (mm/yr)  |  NSE = Nash–Sutcliffe  |  r = Pearson")
    write_df(ws4, df_perf, HDR_FILL_GREEN)

    # NSE colour scale
    n_rows4 = len(df_perf) + 4
    ws4.conditional_formatting.add(
        f"G4:G{n_rows4}",
        ColorScaleRule(start_type="num",  start_value=-1,  start_color="FFCDD2",
                       mid_type="num",    mid_value=0.5,   mid_color="FFFFFF",
                       end_type="num",    end_value=1.0,   end_color="C8E6C9"))

    # ── Sheet 5: Pivot – Bias by Month ────────────────────────────────────────
    ws5 = wb.create_sheet("5_Bias_Pivot_Raw")
    sheet_title(ws5, "Monthly Raw Bias (%) — Station × Month Pivot Table",
                "Ensemble Mean (CMIP6 Raw) vs Observed  |  Positive = overestimation")
    _write_pivot(ws5, stns, raw_bias, "Raw Bias (%)", HDR_FILL_RED, BORDER, WHITE_FONT, CTR, LEFT, cell_font)

    ws6 = wb.create_sheet("6_Bias_Pivot_BC")
    sheet_title(ws6, "Monthly Bias-Corrected Bias (%) — Station × Month Pivot Table",
                "Ensemble Mean (Bias-Corrected) vs Observed")
    _write_pivot(ws6, stns, bc_bias, "BC Bias (%)", HDR_FILL_BLUE, BORDER, WHITE_FONT, CTR, LEFT, cell_font)

    ws7 = wb.create_sheet("7_BiasReduction_Pivot")
    sheet_title(ws7, "Monthly Bias Reduction (%) — Station × Month Pivot Table",
                "Bias Reduction = Raw Bias − BC Bias  |  Positive = improvement")
    _write_pivot(ws7, stns, reduction, "Bias Reduction (%)", HDR_FILL_GREEN,
                 BORDER, WHITE_FONT, CTR, LEFT, cell_font)
    # Colour scale on reduction
    n_stns = len(stns)
    ws7.conditional_formatting.add(
        f"C4:N{3+n_stns+1}",
        ColorScaleRule(start_type="num",  start_value=-100, start_color="C62828",
                       mid_type="num",    mid_value=0,       mid_color="FFFFFF",
                       end_type="num",    end_value=100,     end_color="2E7D32"))

    wb.save(out_path)
    print(f"    ✓  {Path(out_path).name}")


def _write_pivot(ws, stns, mat, value_label, hdr_fill,
                 BORDER, WHITE_FONT, CTR, LEFT, cell_font):
    """Write station×month pivot matrix starting row 3."""
    from openpyxl.styles import Font, Alignment

    # Header row
    ws.cell(3, 1, "Station").font      = WHITE_FONT
    ws.cell(3, 1, "Station").fill      = hdr_fill
    ws.cell(3, 1, "Station").alignment = CTR
    ws.cell(3, 1, "Station").border    = BORDER
    ws.column_dimensions["A"].width    = 14
    ws.column_dimensions["B"].width    = 5   # spacer
    for mi, mon in enumerate(MONTH_ABBR):
        c = ws.cell(3, mi+2, mon)
        c.font      = WHITE_FONT
        c.fill      = hdr_fill
        c.alignment = CTR
        c.border    = BORDER
        ws.column_dimensions[get_column_letter(mi+2)].width = 9
    # Avg column
    ws.cell(3, 14, "Annual\nMean").font      = WHITE_FONT
    ws.cell(3, 14, "Annual\nMean").fill      = hdr_fill
    ws.cell(3, 14, "Annual\nMean").alignment = CTR
    ws.cell(3, 14, "Annual\nMean").border    = BORDER
    ws.column_dimensions["N"].width = 12

    for si, stn in enumerate(stns):
        row = 4 + si
        c = ws.cell(row, 1, f"Stn {stn}")
        c.font      = Font(name="Arial", bold=True, size=10)
        c.alignment = LEFT
        c.border    = BORDER
        if si % 2 == 0:
            c.fill = PatternFill("solid", fgColor="F5F5F5")
        vals = []
        for mi in range(12):
            v = mat[si, mi]
            cell = ws.cell(row, mi+2, round(float(v),1) if not np.isnan(v) else "")
            cell.font      = cell_font()
            cell.alignment = CTR
            cell.border    = BORDER
            if si % 2 == 0:
                cell.fill = PatternFill("solid", fgColor="F5F5F5")
            if not np.isnan(v):
                vals.append(v)
        # Annual mean formula
        avg_cell = ws.cell(row, 14, round(float(np.nanmean(mat[si,:])),1)
                           if not np.all(np.isnan(mat[si,:])) else "")
        avg_cell.font      = Font(name="Arial", bold=True, size=10)
        avg_cell.alignment = CTR
        avg_cell.border    = BORDER

    ws.row_dimensions[3].height = 28


# ══════════════════════════════════════════════════════════════════════════════
# 11.  MAIN
# ══════════════════════════════════════════════════════════════════════════════

def get_work_dir():
    return os.path.dirname(os.path.abspath(__file__))

def main():
    sep = "=" * 76
    print(sep)
    print("  Time Series & Seasonal Cycle Analysis  –  v3")
    print("  Observed vs Raw CMIP6 vs Bias-Corrected (QDM) | Journal Q2")
    print(sep)

    work_dir = (sys.argv[1].strip('"').strip("'")
                if len(sys.argv) > 1 else get_work_dir())
    print(f"  Working directory : {work_dir}\n")

    obs_path, raw_paths, bc_paths = find_csv_files(work_dir)
    if obs_path is None:
        sys.exit("  ✗  Observed file not found.")
    print()

    print("  Loading data ...")
    obs_d, stns  = load_daily(obs_path, "Observed")
    raw_models   = load_all_models(raw_paths, "Raw CMIP6")
    bc_models    = load_all_models(bc_paths,  "BC/QDM")

    print(f"\n  Stations   : {len(stns)}")
    print(f"  Raw models : {len(raw_models)} → {list(raw_models.keys())}")
    print(f"  BC  models : {len(bc_models)} → {list(bc_models.keys())}")

    print("\n  Computing Ensemble Mean ...")
    ens_raw_d = ensemble_mean_daily(raw_models)
    ens_bc_d  = ensemble_mean_daily(bc_models)

    period_obs = period_str(obs_d)
    period_sim = period_str(ens_raw_d) if ens_raw_d is not None else period_str(ens_bc_d)
    print(f"  Period – Obs: {period_obs}  |  Sim: {period_sim}")

    ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
    fig_dir = Path(work_dir) / f"Output_TimeSeries_{ts}"
    fig_dir.mkdir(exist_ok=True)
    print(f"\n  Output folder : {fig_dir}")
    print("-" * 76)

    stns_str = [str(s) for s in stns]

    def out(name): return str(fig_dir / name)

    # ── Figures ───────────────────────────────────────────────────────────────
    print("\n  [1/9] Fig 1 – Annual Time Series (Ensemble first) ...")
    fig1_annual_timeseries(obs_d, raw_models, bc_models,
                           ens_raw_d, ens_bc_d, period_obs,
                           out("Fig1_TimeSeries_Annual_EnsFirst.png"), stns_str)

    print("\n  [2/9] Fig 2 – Monthly Time Series (Ensemble first) ...")
    fig2_monthly_timeseries(obs_d, raw_models, bc_models,
                            ens_raw_d, ens_bc_d, period_obs,
                            out("Fig2_TimeSeries_Monthly_EnsFirst.png"), stns_str)

    print("\n  [3/9] Fig 3a – Seasonal Cycle: All Models ...")
    fig3a_seasonal_all_models(obs_d, raw_models, bc_models,
                               ens_raw_d, ens_bc_d, period_obs,
                               out("Fig3a_SeasonalCycle_AllModels.png"), stns_str)

    print("\n  [4/9] Fig 3b – Seasonal Cycle: Ensemble Mean ...")
    fig3b_seasonal_ensemble(obs_d, ens_raw_d, ens_bc_d, period_obs,
                             out("Fig3b_SeasonalCycle_EnsembleMean.png"), stns_str)

    print("\n  [5/9] Fig 4 – Seasonal Cycle per Station ...")
    fig4_seasonal_per_station(stns_str, obs_d, ens_raw_d, ens_bc_d, period_obs,
                               out("Fig4_SeasonalCycle_PerStation_Grid.png"))

    print("\n  [6/9] Fig 5 – Bias Reduction 3-Panel Heatmap ...")
    raw_bias, bc_bias, reduction = fig5_bias_3panel(
        stns_str, obs_d, ens_raw_d, ens_bc_d, period_obs,
        out("Fig5_MonthlyBiasReduction_3Panel.png"))

    print("\n  [7/9] Fig 5a – Raw Bias Heatmap (single) ...")
    _single_heatmap(raw_bias,
                    "Raw CMIP6 Bias (%) — Ensemble Mean vs Observed",
                    f"Monthly Relative Bias: Ensemble Mean (CMIP6 Raw)  |  {period_obs}",
                    stns_str, out("Fig5a_MonthlyBias_Raw.png"),
                    cbar_label="Relative Bias (%)")

    print("\n  [8/9] Fig 5b – BC Bias Heatmap (single) ...")
    _single_heatmap(bc_bias,
                    "Bias-Corrected Bias (%) — Ensemble Mean vs Observed",
                    f"Monthly Relative Bias: Ensemble Mean (Bias-Corrected)  |  {period_obs}",
                    stns_str, out("Fig5b_MonthlyBias_BC.png"),
                    cbar_label="Relative Bias (%)")

    print("\n  [9/9] Fig 5c – Bias Reduction Heatmap (single) ...")
    _single_heatmap(reduction,
                    "Bias Reduction (%) = Raw Bias − BC Bias",
                    f"Monthly Bias Reduction: Raw → Bias-Corrected  |  {period_obs}",
                    stns_str, out("Fig5c_MonthlyBiasReduction.png"),
                    vmin=-100, vmax=100, cmap="RdYlGn",
                    cbar_label="Bias Reduction (%)")

    # ── Statistics Excel ───────────────────────────────────────────────────────
    print("\n  [Excel] Computing statistics and writing workbook ...")
    df_ann, df_sc, df_bias, df_perf, rb, bb, rd = compute_all_stats(
        stns_str, obs_d, raw_models, bc_models, ens_raw_d, ens_bc_d)
    xlsx_path = out("Statistics_Summary.xlsx")
    write_excel(df_ann, df_sc, df_bias, df_perf,
                rb, bb, rd, stns_str, period_obs, xlsx_path)

    # Done
    n_png  = len(list(fig_dir.glob("*.png")))
    n_xlsx = len(list(fig_dir.glob("*.xlsx")))
    print()
    print(sep)
    print(f"  ✓  Complete:  {n_png} figures  +  {n_xlsx} Excel workbook")
    print(f"  Output : {fig_dir}")
    print(sep)

if __name__ == "__main__":
    main()
