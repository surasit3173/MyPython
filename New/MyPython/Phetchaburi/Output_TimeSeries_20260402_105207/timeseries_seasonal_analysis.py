"""
================================================================================
  Time Series & Seasonal Cycle Analysis
  Observed vs Raw CMIP6 vs Bias-Corrected (QDM) – Multi-Model Ensemble
  Journal Standard Q2 | Hydrology & Climate Science
--------------------------------------------------------------------------------
  Input  (same folder as this script):
    • Observed   → filename contains "Observed"  (case-insensitive)
    • Raw CMIP6  → filename starts with "pr"     (multiple = multiple models)
    • BC / QDM   → filename starts with "bc"     (multiple = multiple models)

  Columns: YEAR  MONTH  DAY  <stn1>  <stn2>  ...

  Output (saved to Output_TimeSeries_<timestamp>/):
    ├── Fig1_TimeSeries_Annual_AllModels.png
    ├── Fig2_TimeSeries_Monthly_AllModels.png
    ├── Fig3_SeasonalCycle_SpatialMean.png
    ├── Fig4_SeasonalCycle_PerStation_Grid.png
    └── Fig5_MonthlyAnomaly_BiasReduction.png

  References:
    Cannon et al. (2015) J. Climate 28:6938–6959  [QDM]
    Teutschbein & Seibert (2012) Hydrol. Earth Syst. Sci. 16:1337–1371
    IPCC AR6 WGI Chapter 10 (2021) – Regional Climate Change
================================================================================
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.lines import Line2D

warnings.filterwarnings("ignore")

# ══════════════════════════════════════════════════════════════════════════════
# 0.  JOURNAL STYLE  (Q2 standard – Times New Roman, 300 dpi)
# ══════════════════════════════════════════════════════════════════════════════
plt.rcParams.update({
    "font.family":        "serif",
    "font.serif":         ["Times New Roman", "DejaVu Serif"],
    "font.size":          9,
    "axes.titlesize":     9.5,
    "axes.labelsize":     9,
    "xtick.labelsize":    8,
    "ytick.labelsize":    8,
    "legend.fontsize":    7.5,
    "figure.titlesize":   11,
    "lines.linewidth":    1.3,
    "axes.linewidth":     0.7,
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.grid":          True,
    "grid.linestyle":     "--",
    "grid.linewidth":     0.3,
    "grid.alpha":         0.45,
    "grid.color":         "#B0BEC5",
    "figure.dpi":         150,
    "savefig.dpi":        300,
    "savefig.bbox":       "tight",
    "savefig.pad_inches": 0.12,
    "mathtext.fontset":   "stix",
    "xtick.major.size":   3.5,
    "ytick.major.size":   3.5,
    "xtick.minor.size":   2.0,
    "ytick.minor.size":   2.0,
})

# ── Colour palette (Okabe-Ito colour-blind safe) ──────────────────────────────
C_OBS      = "#1A1A2E"      # near-black  – Observed
C_ENS_RAW  = "#C62828"      # deep red    – Ensemble Mean Raw
C_ENS_BC   = "#1565C0"      # deep blue   – Ensemble Mean BC

# Individual model colours (cycling palette)
PALETTE_RAW = ["#EF9A9A", "#EF5350", "#B71C1C", "#FF8A65", "#FFCC02"]
PALETTE_BC  = ["#90CAF9", "#42A5F5", "#0D47A1", "#80CBC4", "#A5D6A7"]

MONTH_ABBR = ["Jan","Feb","Mar","Apr","May","Jun",
              "Jul","Aug","Sep","Oct","Nov","Dec"]

MISS_VALS = [-99, -999, -9999, -9.99e+20, 9.99e+20, 1e+20]

# ══════════════════════════════════════════════════════════════════════════════
# 1.  FILE DISCOVERY
# ══════════════════════════════════════════════════════════════════════════════

def find_csv_files(folder: str):
    """Return obs_path (str|None), raw_paths (list), bc_paths (list)."""
    all_csv = sorted(Path(folder).glob("*.csv"))
    obs_lst = [f for f in all_csv if "observed" in f.name.lower()]
    raw_lst = [f for f in all_csv if f.name.lower().startswith("pr")]
    bc_lst  = [f for f in all_csv if f.name.lower().startswith("bc")]

    obs_path = str(obs_lst[0]) if obs_lst else None
    if len(obs_lst) > 1:
        print(f"  ⚠  Observed: found {len(obs_lst)} files – using {obs_lst[0].name}")

    print(f"  Observed  : {Path(obs_path).name if obs_path else '(not found)'}")
    if raw_lst:
        print(f"  Raw CMIP6 : {len(raw_lst)} file(s) → " + ", ".join(f.name for f in raw_lst))
    else:
        print("  Raw CMIP6 : (not found)")
    if bc_lst:
        print(f"  BC/QDM    : {len(bc_lst)} file(s) → " + ", ".join(f.name for f in bc_lst))
    else:
        print("  BC/QDM    : (not found)")

    return obs_path, [str(f) for f in raw_lst], [str(f) for f in bc_lst]


def extract_model_name(filepath: str) -> str:
    """Extract CMIP6 model name from filename."""
    stem  = Path(filepath).stem
    parts = stem.split("_")
    skip  = {"pr", "day", "bc", "historical", "gn", "19810101", "20141231",
              "Phetchaburi", "phetchaburi"}
    for p in parts:
        if p not in skip and not p.startswith("r") and len(p) > 2:
            return p
    return stem[:20]

# ══════════════════════════════════════════════════════════════════════════════
# 2.  DATA LOADING & AGGREGATION
# ══════════════════════════════════════════════════════════════════════════════

def load_daily(csv_path: str, label: str):
    """Load daily CSV → DataFrame (date-indexed), station columns."""
    if not csv_path or not os.path.isfile(csv_path):
        print(f"  ✗  File not found: {label}")
        return None, []
    df = pd.read_csv(csv_path)
    for mv in MISS_VALS:
        df.replace(mv, np.nan, inplace=True)
    num = df.select_dtypes(include=[np.number]).columns
    df[num] = df[num].where(df[num] >= 0)
    stns = [c for c in df.columns if c.upper() not in ("YEAR", "MONTH", "DAY")]
    try:
        df["date"] = pd.to_datetime(
            {"year": df["YEAR"], "month": df["MONTH"], "day": df["DAY"]})
        df = df.set_index("date")[stns]
    except Exception as e:
        print(f"  ⚠  date parse error ({e}); using integer index")
        df = df[stns]
    print(f"    {label:35s}: {len(df):,} rows × {len(stns)} stations")
    return df, stns


def load_all_models(paths: list, prefix: str) -> dict:
    """Load multiple model files → {model_name: daily_df}."""
    out = {}
    for p in paths:
        name = extract_model_name(p)
        df, _ = load_daily(p, f"{prefix} [{name}]")
        if df is not None:
            out[name] = df
    return out


def ensemble_mean_daily(models_dict: dict):
    """Pixel-wise ensemble mean across all models (NaN-safe)."""
    if not models_dict:
        return None
    dfs = list(models_dict.values())
    common_idx  = dfs[0].index
    common_stns = list(dfs[0].columns)
    for df in dfs[1:]:
        common_idx  = common_idx.intersection(df.index)
        common_stns = [s for s in common_stns if s in df.columns]
    aligned = [df.loc[common_idx, common_stns] for df in dfs]
    stack   = np.stack([a.values for a in aligned], axis=0)
    mean    = np.nanmean(stack, axis=0)
    return pd.DataFrame(mean, index=common_idx, columns=common_stns)


def spatial_mean(df) -> pd.Series:
    """Average all station columns to one time series."""
    if df is None:
        return None
    return df.mean(axis=1)


def to_monthly(df):
    if df is None:
        return None
    return df.resample("MS").apply(
        lambda g: g.sum(min_count=max(1, int(0.8 * len(g)))))


def to_annual(df):
    if df is None:
        return None
    return df.resample("YS").apply(
        lambda g: g.sum(min_count=max(1, int(0.8 * len(g)))))


def period_str(df):
    if df is None:
        return "N/A"
    try:
        return f"{df.index[0].year}–{df.index[-1].year}"
    except Exception:
        return "N/A"

# ══════════════════════════════════════════════════════════════════════════════
# 3.  SHARED HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _style_ax(ax, ylabel="", xlabel="", title=""):
    ax.set_ylabel(ylabel, labelpad=5)
    ax.set_xlabel(xlabel, labelpad=4)
    if title:
        ax.set_title(title, loc="left", fontweight="bold", pad=6)
    ax.yaxis.set_minor_locator(ticker.AutoMinorLocator(4))
    ax.tick_params(which="both", direction="out")


def _footnote(fig, text, y=0.003):
    fig.text(0.01, y, text, fontsize=6.0, color="#546E7A",
             ha="left", va="bottom", fontstyle="italic")


def _add_legend(fig_or_ax, handles, ncol=3, loc="lower center",
                bbox=(0.5, -0.02), fontsize=7.5):
    if hasattr(fig_or_ax, "legend"):
        fig_or_ax.legend(handles=handles, loc=loc, ncol=ncol,
                         fontsize=fontsize, framealpha=0.92,
                         edgecolor="#90A4AE",
                         bbox_to_anchor=bbox)
    else:
        fig_or_ax.legend(handles=handles, loc=loc, ncol=ncol,
                         fontsize=fontsize, framealpha=0.92,
                         edgecolor="#90A4AE")


def _obs_handle():
    return Line2D([0], [0], color=C_OBS, lw=1.8, label="Observed")

def _ens_raw_handle():
    return Line2D([0], [0], color=C_ENS_RAW, lw=1.6, ls="--",
                  label="Ensemble Mean (CMIP6 Raw)")

def _ens_bc_handle():
    return Line2D([0], [0], color=C_ENS_BC, lw=1.6, ls="-.",
                  label="Ensemble Mean (Bias-Corrected)")


# ══════════════════════════════════════════════════════════════════════════════
# 4.  FIG 1 – ANNUAL TIME SERIES  (one panel per model + ensemble mean)
# ══════════════════════════════════════════════════════════════════════════════

def plot_annual_timeseries(obs_d, raw_models, bc_models,
                           ens_raw_d, ens_bc_d,
                           period_obs, out_path, stns):
    """
    Annual total rainfall time series.
    Layout: top panels = individual models (raw vs bc);
            bottom panel = Ensemble Mean comparison.
    Spatial mean across all stations per year.
    """
    model_names = sorted(set(list(raw_models.keys()) + list(bc_models.keys())))
    n_models    = len(model_names)
    n_panels    = n_models + 1          # individual models + ensemble panel
    n_cols      = 1
    n_rows      = min(n_panels, 5)      # cap at 5 rows

    fig_h = max(9, n_rows * 2.6 + 1.5)
    fig, axes = plt.subplots(n_rows, n_cols,
                             figsize=(14, fig_h),
                             sharex=False)
    if n_rows == 1:
        axes = [axes]

    # ── Helper: annual spatial-mean series ───────────────────────────────────
    def ann_sp(df):
        if df is None:
            return None
        annual = to_annual(df)
        if annual is None:
            return None
        return annual.mean(axis=1)

    obs_ann = ann_sp(obs_d)

    # ── Per-model panels ──────────────────────────────────────────────────────
    for mi, mname in enumerate(model_names[:n_rows - 1]):
        ax = axes[mi]

        raw_ann = ann_sp(raw_models.get(mname))
        bc_ann  = ann_sp(bc_models.get(mname))

        # Plot obs
        if obs_ann is not None:
            ax.plot(obs_ann.index.year, obs_ann.values,
                    color=C_OBS, lw=1.8, zorder=5, label="Observed")
        # Plot raw
        if raw_ann is not None:
            ax.plot(raw_ann.index.year, raw_ann.values,
                    color=PALETTE_RAW[mi % len(PALETTE_RAW)],
                    lw=1.3, ls="--", alpha=0.85,
                    label=f"Raw [{mname}]")
        # Plot bc
        if bc_ann is not None:
            ax.plot(bc_ann.index.year, bc_ann.values,
                    color=PALETTE_BC[mi % len(PALETTE_BC)],
                    lw=1.3, ls="-.", alpha=0.85,
                    label=f"BC/QDM [{mname}]")

        _style_ax(ax,
                  ylabel="Annual Total Rainfall (mm)",
                  title=f"({chr(97+mi)})  Model: {mname}")
        ax.set_ylim(bottom=0)
        ax.legend(loc="upper right", fontsize=7, framealpha=0.88,
                  edgecolor="#90A4AE")
        ax.xaxis.set_major_locator(ticker.MultipleLocator(5))
        ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))

    # ── Bottom panel: Ensemble Mean ───────────────────────────────────────────
    ax_ens = axes[n_rows - 1]
    ens_raw_ann = ann_sp(ens_raw_d)
    ens_bc_ann  = ann_sp(ens_bc_d)

    if obs_ann is not None:
        ax_ens.plot(obs_ann.index.year, obs_ann.values,
                    color=C_OBS, lw=2.0, zorder=6, label="Observed")

    # Ensemble spread shading (if multi-model)
    if len(raw_models) > 1:
        raw_anns = [ann_sp(df) for df in raw_models.values() if df is not None]
        _shade_spread(ax_ens, raw_anns, C_ENS_RAW, alpha=0.15)
    if len(bc_models) > 1:
        bc_anns = [ann_sp(df) for df in bc_models.values() if df is not None]
        _shade_spread(ax_ens, bc_anns, C_ENS_BC, alpha=0.15)

    if ens_raw_ann is not None:
        ax_ens.plot(ens_raw_ann.index.year, ens_raw_ann.values,
                    color=C_ENS_RAW, lw=1.8, ls="--",
                    label="Ensemble Mean (CMIP6 Raw)")
    if ens_bc_ann is not None:
        ax_ens.plot(ens_bc_ann.index.year, ens_bc_ann.values,
                    color=C_ENS_BC, lw=1.8, ls="-.",
                    label="Ensemble Mean (Bias-Corrected)")

    _style_ax(ax_ens,
              ylabel="Annual Total Rainfall (mm)",
              xlabel="Year",
              title=f"({chr(97 + n_rows - 1)})  Ensemble Mean Comparison  |  All Models")
    ax_ens.set_ylim(bottom=0)
    ax_ens.legend(loc="upper right", fontsize=7.5, framealpha=0.92,
                  edgecolor="#90A4AE")
    ax_ens.xaxis.set_major_locator(ticker.MultipleLocator(5))
    ax_ens.xaxis.set_minor_locator(ticker.MultipleLocator(1))

    # Super title
    n_stn = len(stns)
    fig.suptitle(
        f"Annual Total Rainfall Time Series — Spatial Mean ({n_stn} Stations)  |  {period_obs}",
        fontsize=11, fontweight="bold", y=1.002)

    _footnote(fig,
              "Spatial mean of annual total rainfall across all stations. "
              "Shaded area (lower panel) = model spread (min–max). "
              "Dashed = Raw CMIP6; Dash-dot = Bias-Corrected (QDM). "
              "Reference: Cannon et al. (2015); Teutschbein & Seibert (2012).")

    plt.tight_layout(rect=[0, 0.03, 1, 1])
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


def _shade_spread(ax, series_list, color, alpha=0.15):
    """Shade min–max envelope for a list of annual time series."""
    valid = [s for s in series_list if s is not None and len(s) > 0]
    if len(valid) < 2:
        return
    common = valid[0].index
    for s in valid[1:]:
        common = common.intersection(s.index)
    if len(common) == 0:
        return
    mat = np.stack([s.loc[common].values for s in valid], axis=0)
    lo  = np.nanmin(mat, axis=0)
    hi  = np.nanmax(mat, axis=0)
    ax.fill_between(common.year, lo, hi, color=color, alpha=alpha, zorder=2)


# ══════════════════════════════════════════════════════════════════════════════
# 5.  FIG 2 – MONTHLY TIME SERIES  (12-monthly totals over entire record)
# ══════════════════════════════════════════════════════════════════════════════

def plot_monthly_timeseries(obs_d, raw_models, bc_models,
                            ens_raw_d, ens_bc_d,
                            period_obs, out_path, stns):
    """
    Monthly total rainfall time series (spatial mean).
    Layout: Ensemble Mean panel (main) + one panel per individual model.
    """
    model_names = sorted(set(list(raw_models.keys()) + list(bc_models.keys())))
    n_models    = len(model_names)
    n_panels    = min(n_models + 1, 5)

    fig_h = max(10, n_panels * 2.8 + 1.5)
    fig, axes = plt.subplots(n_panels, 1,
                             figsize=(15, fig_h),
                             sharex=False)
    if n_panels == 1:
        axes = [axes]

    def mon_sp(df):
        if df is None:
            return None
        m = to_monthly(df)
        if m is None:
            return None
        return m.mean(axis=1)

    obs_mon = mon_sp(obs_d)

    # ── Ensemble Mean panel (first) ───────────────────────────────────────────
    ax0 = axes[0]
    if obs_mon is not None:
        ax0.plot(obs_mon.index, obs_mon.values,
                 color=C_OBS, lw=1.5, alpha=0.80, zorder=5,
                 label="Observed")

    ens_raw_mon = mon_sp(ens_raw_d)
    ens_bc_mon  = mon_sp(ens_bc_d)

    if ens_raw_mon is not None:
        ax0.plot(ens_raw_mon.index, ens_raw_mon.values,
                 color=C_ENS_RAW, lw=1.5, ls="--", alpha=0.88,
                 label="Ensemble Mean (CMIP6 Raw)")
    if ens_bc_mon is not None:
        ax0.plot(ens_bc_mon.index, ens_bc_mon.values,
                 color=C_ENS_BC, lw=1.5, ls="-.", alpha=0.88,
                 label="Ensemble Mean (Bias-Corrected)")

    _style_ax(ax0,
              ylabel="Monthly Rainfall (mm)",
              title="(a)  Ensemble Mean Comparison — Monthly Time Series")
    ax0.set_ylim(bottom=0)
    ax0.legend(loc="upper right", fontsize=7.5, framealpha=0.90,
               edgecolor="#90A4AE")
    ax0.xaxis.set_major_locator(
        matplotlib.dates.YearLocator(5))
    ax0.xaxis.set_major_formatter(
        matplotlib.dates.DateFormatter("%Y"))

    # ── Per-model panels ──────────────────────────────────────────────────────
    for mi, mname in enumerate(model_names[:n_panels - 1]):
        ax = axes[mi + 1]
        if obs_mon is not None:
            ax.plot(obs_mon.index, obs_mon.values,
                    color=C_OBS, lw=1.5, alpha=0.75, label="Observed")

        raw_mon = mon_sp(raw_models.get(mname))
        bc_mon  = mon_sp(bc_models.get(mname))

        if raw_mon is not None:
            ax.plot(raw_mon.index, raw_mon.values,
                    color=PALETTE_RAW[mi % len(PALETTE_RAW)],
                    lw=1.2, ls="--", alpha=0.80,
                    label=f"Raw [{mname}]")
        if bc_mon is not None:
            ax.plot(bc_mon.index, bc_mon.values,
                    color=PALETTE_BC[mi % len(PALETTE_BC)],
                    lw=1.2, ls="-.", alpha=0.80,
                    label=f"BC/QDM [{mname}]")

        _style_ax(ax,
                  ylabel="Monthly Rainfall (mm)",
                  title=f"({chr(98 + mi)})  Model: {mname}")
        ax.set_ylim(bottom=0)
        ax.legend(loc="upper right", fontsize=7, framealpha=0.88,
                  edgecolor="#90A4AE")
        ax.xaxis.set_major_locator(matplotlib.dates.YearLocator(5))
        ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y"))

    axes[-1].set_xlabel("Year", labelpad=4)

    n_stn = len(stns)
    fig.suptitle(
        f"Monthly Rainfall Time Series — Spatial Mean ({n_stn} Stations)  |  {period_obs}",
        fontsize=11, fontweight="bold", y=1.002)

    _footnote(fig,
              "Monthly total rainfall averaged across all stations. "
              "Dashed = Raw CMIP6; Dash-dot = Bias-Corrected (QDM).")

    plt.tight_layout(rect=[0, 0.03, 1, 1])
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


import matplotlib.dates


# ══════════════════════════════════════════════════════════════════════════════
# 6.  FIG 3 – SEASONAL CYCLE  (spatial mean, all models + ensemble)
# ══════════════════════════════════════════════════════════════════════════════

def _seasonal_cycle(df):
    """Compute long-term monthly mean (spatial average) → array of 12 values."""
    if df is None:
        return None
    mon = to_monthly(df)
    if mon is None:
        return None
    sp  = mon.mean(axis=1)                   # spatial mean
    return sp.groupby(sp.index.month).mean() # monthly climatology


def plot_seasonal_cycle(obs_d, raw_models, bc_models,
                        ens_raw_d, ens_bc_d,
                        period_obs, out_path, stns):
    """
    Fig 3: Seasonal Cycle – long-term monthly mean rainfall.
    Bar (Observed) + Lines (models + ensemble mean).
    Two-panel layout:
      (a) All individual models + ensemble mean
      (b) Ensemble Mean only (clean comparison)
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6.5),
                                   sharey=True)

    x = np.arange(1, 13)
    obs_sc = _seasonal_cycle(obs_d)

    # ── Panel (a): All models ─────────────────────────────────────────────────
    # Observed bars
    if obs_sc is not None:
        ax1.bar(x, obs_sc.values, width=0.45, color="#CFD8DC",
                edgecolor=C_OBS, linewidth=0.7, label="Observed",
                zorder=3, align="center")

    # Individual raw models (thin, muted)
    raw_scs = {}
    for mi, (mname, df) in enumerate(raw_models.items()):
        sc = _seasonal_cycle(df)
        if sc is not None:
            raw_scs[mname] = sc
            ax1.plot(x, sc.values,
                     color=PALETTE_RAW[mi % len(PALETTE_RAW)],
                     lw=0.9, ls="--", alpha=0.65, marker="o",
                     markersize=2.5, zorder=4,
                     label=f"Raw [{mname}]")

    # Individual BC models (thin, muted)
    bc_scs = {}
    for mi, (mname, df) in enumerate(bc_models.items()):
        sc = _seasonal_cycle(df)
        if sc is not None:
            bc_scs[mname] = sc
            ax1.plot(x, sc.values,
                     color=PALETTE_BC[mi % len(PALETTE_BC)],
                     lw=0.9, ls="-.", alpha=0.65, marker="s",
                     markersize=2.5, zorder=4,
                     label=f"BC/QDM [{mname}]")

    # Ensemble Mean lines (bold)
    ens_raw_sc = _seasonal_cycle(ens_raw_d)
    ens_bc_sc  = _seasonal_cycle(ens_bc_d)

    if ens_raw_sc is not None:
        ax1.plot(x, ens_raw_sc.values,
                 color=C_ENS_RAW, lw=2.2, ls="--",
                 marker="D", markersize=5, zorder=6,
                 label="Ensemble Mean (CMIP6 Raw)")
    if ens_bc_sc is not None:
        ax1.plot(x, ens_bc_sc.values,
                 color=C_ENS_BC, lw=2.2, ls="-.",
                 marker="^", markersize=5, zorder=6,
                 label="Ensemble Mean (Bias-Corrected)")

    ax1.set_xticks(x)
    ax1.set_xticklabels(MONTH_ABBR)
    _style_ax(ax1,
              ylabel="Mean Monthly Rainfall (mm)",
              xlabel="Month",
              title="(a)  All Models + Ensemble Mean")
    ax1.set_ylim(bottom=0)
    ax1.legend(loc="upper left", fontsize=7, framealpha=0.90,
               edgecolor="#90A4AE", ncol=1)

    # Wet-season shading (May–Oct)
    for ax in (ax1, ax2):
        ax.axvspan(4.55, 10.45, alpha=0.07, color="#1565C0", zorder=0)
        ax.text(7.5, ax1.get_ylim()[1] * 0.93, "Wet Season",
                fontsize=7, color="#1565C0", ha="center", fontstyle="italic")

    # ── Panel (b): Ensemble Mean only (clean) ────────────────────────────────
    if obs_sc is not None:
        ax2.bar(x, obs_sc.values, width=0.45, color="#CFD8DC",
                edgecolor=C_OBS, linewidth=0.7, label="Observed",
                zorder=3, align="center")
    if ens_raw_sc is not None:
        ax2.plot(x, ens_raw_sc.values,
                 color=C_ENS_RAW, lw=2.3, ls="--",
                 marker="D", markersize=6, zorder=5,
                 label="Ensemble Mean (CMIP6 Raw)")
    if ens_bc_sc is not None:
        ax2.plot(x, ens_bc_sc.values,
                 color=C_ENS_BC, lw=2.3, ls="-.",
                 marker="^", markersize=6, zorder=5,
                 label="Ensemble Mean (Bias-Corrected)")

    # Annotate bias reduction arrows for peak months
    if obs_sc is not None and ens_raw_sc is not None and ens_bc_sc is not None:
        peak_m = int(obs_sc.idxmax())
        ov = obs_sc.loc[peak_m]
        rv = ens_raw_sc.loc[peak_m]
        bv = ens_bc_sc.loc[peak_m]
        ax2.annotate("",
                     xy=(peak_m, bv), xytext=(peak_m, rv),
                     arrowprops=dict(arrowstyle="->", color="#FF6F00",
                                     lw=1.4),
                     zorder=7)
        ax2.text(peak_m + 0.15, (rv + bv) / 2,
                 f"ΔBias\n{abs(rv-bv):.0f} mm",
                 fontsize=6.5, color="#FF6F00", va="center")

    ax2.set_xticks(x)
    ax2.set_xticklabels(MONTH_ABBR)
    _style_ax(ax2,
              ylabel="",
              xlabel="Month",
              title="(b)  Ensemble Mean — Clean Comparison")
    ax2.set_ylim(bottom=0)
    ax2.legend(loc="upper left", fontsize=7.5, framealpha=0.92,
               edgecolor="#90A4AE")

    n_stn = len(stns)
    fig.suptitle(
        f"Seasonal Cycle of Monthly Rainfall — Spatial Mean ({n_stn} Stations)  |  {period_obs}",
        fontsize=11, fontweight="bold")

    _footnote(fig,
              "Bar = Observed long-term monthly mean; Lines = model climatology. "
              "Orange arrow (panel b) = bias reduction at peak rainfall month. "
              "Shaded = May–Oct wet season.  "
              "Reference: Teutschbein & Seibert (2012); IPCC AR6 WGI Ch.10.")

    plt.tight_layout(rect=[0, 0.04, 1, 0.96])
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ══════════════════════════════════════════════════════════════════════════════
# 7.  FIG 4 – SEASONAL CYCLE PER STATION  (small-multiples grid)
# ══════════════════════════════════════════════════════════════════════════════

def _seasonal_cycle_stn(df, stn):
    """Monthly climatology for a single station."""
    if df is None:
        return None
    stn = str(stn)
    if stn not in df.columns:
        return None
    mon = df[stn].resample("MS").apply(
        lambda g: g.sum(min_count=max(1, int(0.8 * len(g)))))
    return mon.groupby(mon.index.month).mean()


def plot_seasonal_cycle_per_station(stns, obs_d, raw_models, bc_models,
                                    ens_raw_d, ens_bc_d,
                                    period_obs, out_path):
    """
    Fig 4: Per-station seasonal cycle – small multiples grid.
    Each cell shows: Observed bar + Ensemble Mean Raw (dashed) + Ensemble Mean BC (dash-dot).
    """
    n     = len(stns)
    ncols = min(5, n)
    nrows = (n + ncols - 1) // ncols

    fig_w = ncols * 3.4
    fig_h = nrows * 3.2 + 1.4

    fig, axes = plt.subplots(nrows, ncols, figsize=(fig_w, fig_h),
                             squeeze=False)
    x = np.arange(1, 13)

    for idx, stn in enumerate(stns):
        row = idx // ncols
        col = idx % ncols
        ax  = axes[row][col]
        stn = str(stn)

        obs_sc = _seasonal_cycle_stn(obs_d, stn)
        ens_r  = _seasonal_cycle_stn(ens_raw_d, stn)
        ens_b  = _seasonal_cycle_stn(ens_bc_d,  stn)

        if obs_sc is not None:
            ax.bar(x, obs_sc.values, width=0.5,
                   color="#CFD8DC", edgecolor=C_OBS,
                   linewidth=0.6, zorder=3)
        if ens_r is not None:
            ax.plot(x, ens_r.values, color=C_ENS_RAW,
                    lw=1.5, ls="--", marker="o",
                    markersize=2.8, zorder=5)
        if ens_b is not None:
            ax.plot(x, ens_b.values, color=C_ENS_BC,
                    lw=1.5, ls="-.", marker="^",
                    markersize=2.8, zorder=5)

        ax.set_title(f"Stn {stn}", fontsize=7.5, fontweight="bold", pad=3)
        ax.set_xticks(x[::2])
        ax.set_xticklabels(MONTH_ABBR[::2], fontsize=5.8)
        ax.set_ylabel("Rainfall (mm)" if col == 0 else "",
                      fontsize=6.5)
        ax.set_ylim(bottom=0)
        ax.tick_params(labelsize=6)
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator(2))
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(True, axis="y", ls="--", lw=0.25, alpha=0.4)
        # Wet-season tint
        ax.axvspan(4.55, 10.45, alpha=0.07, color="#1565C0", zorder=0)

    # Hide empty cells
    for idx in range(n, nrows * ncols):
        axes[idx // ncols][idx % ncols].set_visible(False)

    # Shared legend
    handles = [
        mpatches.Patch(facecolor="#CFD8DC", edgecolor=C_OBS,
                       label="Observed"),
        Line2D([0], [0], color=C_ENS_RAW, lw=1.5, ls="--",
               marker="o", markersize=4,
               label="Ensemble Mean (CMIP6 Raw)"),
        Line2D([0], [0], color=C_ENS_BC, lw=1.5, ls="-.",
               marker="^", markersize=4,
               label="Ensemble Mean (Bias-Corrected)"),
    ]
    fig.legend(handles=handles,
               loc="lower center", ncol=3, fontsize=7.5,
               framealpha=0.92, edgecolor="#90A4AE",
               bbox_to_anchor=(0.5, -0.01))

    fig.suptitle(
        f"Seasonal Cycle of Monthly Rainfall — Per Station  |  {period_obs}",
        fontsize=10, fontweight="bold", y=1.003)

    _footnote(fig,
              "Bar = Observed; Dashed = Ensemble Mean Raw; Dash-dot = Ensemble Mean BC. "
              "Shaded = May–Oct wet season.")

    plt.tight_layout(rect=[0, 0.05, 1, 1])
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ══════════════════════════════════════════════════════════════════════════════
# 8.  FIG 5 – MONTHLY ANOMALY & BIAS REDUCTION  (heat-map style)
# ══════════════════════════════════════════════════════════════════════════════

def plot_monthly_bias_reduction(stns, obs_d, ens_raw_d, ens_bc_d,
                                period_obs, out_path):
    """
    Fig 5: Monthly relative bias (%) per station — Raw vs BC.
    Heatmap: rows = station, cols = month.
    Side-by-side: Raw bias | BC bias | Bias Reduction.
    """
    n_stn   = len(stns)
    n_month = 12

    # Build matrices: relative bias (%) = (sim - obs) / obs * 100
    raw_bias = np.full((n_stn, n_month), np.nan)
    bc_bias  = np.full((n_stn, n_month), np.nan)

    for si, stn in enumerate(stns):
        stn = str(stn)
        obs_sc = _seasonal_cycle_stn(obs_d, stn)
        raw_sc = _seasonal_cycle_stn(ens_raw_d, stn)
        bc_sc  = _seasonal_cycle_stn(ens_bc_d,  stn)

        for mi, month in enumerate(range(1, 13)):
            if obs_sc is None or month not in obs_sc.index:
                continue
            ov = obs_sc.loc[month]
            if ov == 0 or np.isnan(ov):
                continue
            if raw_sc is not None and month in raw_sc.index:
                raw_bias[si, mi] = (raw_sc.loc[month] - ov) / ov * 100
            if bc_sc is not None and month in bc_sc.index:
                bc_bias[si, mi]  = (bc_sc.loc[month] - ov) / ov * 100

    reduction = raw_bias - bc_bias   # positive = bias reduced

    # ── Plot ─────────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 3, figsize=(18, max(5, n_stn * 0.55 + 2.5)))

    vlim = 100
    cmap_bias = "RdBu_r"
    cmap_red  = "RdYlGn"

    titles = [
        "Raw CMIP6 Bias (%)\n(Ensemble Mean vs Observed)",
        "Bias-Corrected Bias (%)\n(Ensemble Mean vs Observed)",
        "Bias Reduction (%)\n(Raw − BC; positive = improvement)",
    ]
    mats   = [raw_bias, bc_bias, reduction]
    cmaps  = [cmap_bias, cmap_bias, cmap_red]
    vlims  = [(-vlim, vlim), (-vlim, vlim), (-vlim, vlim)]

    for ax, mat, title, cmap, (vmin, vmax) in zip(axes, mats, titles, cmaps, vlims):
        im = ax.imshow(mat, aspect="auto", cmap=cmap,
                       vmin=vmin, vmax=vmax,
                       interpolation="nearest")
        ax.set_xticks(range(n_month))
        ax.set_xticklabels(MONTH_ABBR, fontsize=7.5)
        ax.set_yticks(range(n_stn))
        ax.set_yticklabels([f"Stn {s}" for s in stns], fontsize=7)
        ax.set_title(title, fontsize=8.5, fontweight="bold", pad=6)
        ax.set_xlabel("Month", fontsize=8)

        # Cell annotations
        for i in range(n_stn):
            for j in range(n_month):
                val = mat[i, j]
                if not np.isnan(val):
                    txt_col = "white" if abs(val) > 60 else "black"
                    ax.text(j, i, f"{val:.0f}",
                            ha="center", va="center",
                            fontsize=5.5, color=txt_col)

        cb = fig.colorbar(im, ax=ax, orientation="vertical",
                          shrink=0.80, pad=0.02)
        cb.ax.tick_params(labelsize=7)
        cb.set_label("%", fontsize=7.5)

    fig.suptitle(
        f"Monthly Relative Bias and Bias Reduction — Per Station  |  {period_obs}",
        fontsize=11, fontweight="bold")

    _footnote(fig,
              "Relative bias (%) = (Ensemble Mean − Observed) / Observed × 100. "
              "Bias Reduction = Raw Bias − BC Bias (positive values = improvement after bias correction). "
              "Ensemble Mean computed across all available CMIP6 models.")

    plt.tight_layout(rect=[0, 0.04, 1, 0.96])
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ══════════════════════════════════════════════════════════════════════════════
# 9.  MAIN
# ══════════════════════════════════════════════════════════════════════════════

def get_work_dir():
    return os.path.dirname(os.path.abspath(__file__))


def main():
    sep = "=" * 74
    print(sep)
    print("  Time Series & Seasonal Cycle Analysis")
    print("  Observed vs Raw CMIP6 vs Bias-Corrected (QDM) | Journal Q2")
    print(sep)

    work_dir = (sys.argv[1].strip('"').strip("'")
                if len(sys.argv) > 1 else get_work_dir())
    print(f"  Working directory : {work_dir}\n")

    # 1. Discover ─────────────────────────────────────────────────────────────
    obs_path, raw_paths, bc_paths = find_csv_files(work_dir)
    if obs_path is None:
        sys.exit("  ✗  Observed file not found – please check the folder.")
    print()

    # 2. Load ─────────────────────────────────────────────────────────────────
    print("  Loading data ...")
    obs_d, stns  = load_daily(obs_path, "Observed")
    raw_models   = load_all_models(raw_paths, "Raw CMIP6")
    bc_models    = load_all_models(bc_paths,  "BC/QDM")

    print(f"\n  Stations   : {len(stns)}")
    print(f"  Raw models : {len(raw_models)} → {list(raw_models.keys())}")
    print(f"  BC  models : {len(bc_models)} → {list(bc_models.keys())}")

    # 3. Ensemble Mean ─────────────────────────────────────────────────────────
    print("\n  Computing Ensemble Mean ...")
    ens_raw_d = ensemble_mean_daily(raw_models)
    ens_bc_d  = ensemble_mean_daily(bc_models)

    period_obs = period_str(obs_d)
    period_sim = period_str(ens_raw_d) if ens_raw_d is not None else period_str(ens_bc_d)
    print(f"  Period – Obs: {period_obs}  |  Sim: {period_sim}")

    # 4. Output folder ─────────────────────────────────────────────────────────
    ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
    fig_dir = Path(work_dir) / f"Output_TimeSeries_{ts}"
    fig_dir.mkdir(exist_ok=True)
    print(f"\n  Output folder : {fig_dir}")
    print("-" * 74)

    stns_str = [str(s) for s in stns]

    # 5. Figures ───────────────────────────────────────────────────────────────
    print("\n  [1/5] Fig 1 – Annual Time Series ...")
    plot_annual_timeseries(
        obs_d, raw_models, bc_models, ens_raw_d, ens_bc_d,
        period_obs,
        str(fig_dir / "Fig1_TimeSeries_Annual_AllModels.png"),
        stns_str)

    print("\n  [2/5] Fig 2 – Monthly Time Series ...")
    plot_monthly_timeseries(
        obs_d, raw_models, bc_models, ens_raw_d, ens_bc_d,
        period_obs,
        str(fig_dir / "Fig2_TimeSeries_Monthly_AllModels.png"),
        stns_str)

    print("\n  [3/5] Fig 3 – Seasonal Cycle (Spatial Mean) ...")
    plot_seasonal_cycle(
        obs_d, raw_models, bc_models, ens_raw_d, ens_bc_d,
        period_obs,
        str(fig_dir / "Fig3_SeasonalCycle_SpatialMean.png"),
        stns_str)

    print("\n  [4/5] Fig 4 – Seasonal Cycle per Station ...")
    plot_seasonal_cycle_per_station(
        stns_str, obs_d, raw_models, bc_models, ens_raw_d, ens_bc_d,
        period_obs,
        str(fig_dir / "Fig4_SeasonalCycle_PerStation_Grid.png"))

    print("\n  [5/5] Fig 5 – Monthly Bias Reduction Heatmap ...")
    plot_monthly_bias_reduction(
        stns_str, obs_d, ens_raw_d, ens_bc_d,
        period_obs,
        str(fig_dir / "Fig5_MonthlyBiasReduction_Heatmap.png"))

    # Done ─────────────────────────────────────────────────────────────────────
    n_out = len(list(fig_dir.glob("*.png")))
    print()
    print(sep)
    print(f"  ✓  Complete – {n_out} figures saved")
    print(f"  Output : {fig_dir}")
    print(sep)


if __name__ == "__main__":
    main()
