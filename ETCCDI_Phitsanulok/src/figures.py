"""
figures.py — Publication-quality figures for ETCCDI Phitsanulok analysis.

Produces 6 figures at 300 dpi (PNG):
  FIGURE_01 — Annual data completeness bar chart
  FIGURE_02 — 11-panel ETCCDI time series with Sen's slope
  FIGURE_03 — Trend heatmap
  FIGURE_04 — Sen's slope forest plot with 95% CI
  FIGURE_05 — ACF diagnostic plots for all 11 indices
  FIGURE_06 — Distribution (standardized boxplot/violin)

All figures use DejaVu Serif font, publication-ready styling.
No 3D effects. No unnecessary decoration.
"""
import sys
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.lines import Line2D
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (
    OUTPUT_ROOT, INDICES, UNITS, FIG_DPI, FIG_FORMAT,
    FIG_FONT, ALPHA, START_YEAR, END_YEAR,
    ACF_MAX_LAG, ACF_SIG_FACTOR,
)

# ─── Global Matplotlib Style ─────────────────────────────────────────────────
matplotlib.rcParams.update({
    "font.family":        FIG_FONT,
    "font.size":          9,
    "axes.titlesize":     10,
    "axes.labelsize":     9,
    "xtick.labelsize":    8,
    "ytick.labelsize":    8,
    "legend.fontsize":    8,
    "figure.dpi":         FIG_DPI,
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.linewidth":     0.8,
    "xtick.major.size":   3,
    "ytick.major.size":   3,
    "lines.linewidth":    1.0,
})

FIGURES_DIR = OUTPUT_ROOT / "figures"

# Colour palette
COL_DATA   = "#2c3e50"
COL_TREND  = "#c0392b"
COL_CI     = "#e74c3c"
COL_POS    = "#1a7fc1"  # positive trend
COL_NEG    = "#c0392b"  # negative trend
COL_NS     = "#95a5a6"  # non-significant
COL_BARS   = "#3498db"


# ─── Helper ──────────────────────────────────────────────────────────────────

def _get_fig_dir() -> Path:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    return FIGURES_DIR


def _save_fig(fig: plt.Figure, filename: str) -> None:
    fig_dir = _get_fig_dir()
    out_path = fig_dir / filename
    fig.savefig(out_path, dpi=FIG_DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[FIG] {filename} saved to {out_path}")


def _trend_color(trend_label: str) -> str:
    if trend_label is None or pd.isna(trend_label):
        return COL_NS
    tl = str(trend_label).lower()
    if "significant" in tl and "increasing" in tl:
        return COL_POS
    if "significant" in tl and "decreasing" in tl:
        return COL_NEG
    return COL_NS


# ─── FIGURE 01: Data Coverage ────────────────────────────────────────────────

def plot_figure01(df_quality: pd.DataFrame) -> None:
    """Annual data completeness bar chart 1961–2019."""
    fig, ax = plt.subplots(figsize=(10, 3.5))

    years       = df_quality["Year"].values
    completeness = df_quality["Completeness_%"].values

    # Color bars by completeness
    colors = ["#27ae60" if c >= 100 else ("#f39c12" if c >= 90 else "#e74c3c")
              for c in completeness]

    ax.bar(years, completeness, color=colors, width=0.8, edgecolor="white", linewidth=0.3)
    ax.axhline(y=90, color="#c0392b", linestyle="--", linewidth=0.9, label="90% threshold")
    ax.axhline(y=100, color="#27ae60", linestyle="--", linewidth=0.9, label="100%")

    ax.set_xlabel("Year")
    ax.set_ylabel("Completeness (%)")
    ax.set_title(
        "Figure 1. Annual data completeness of daily precipitation record\n"
        "WMO Station 48378 (Phitsanulok, Thailand), 1961–2019",
        fontsize=9, loc="left",
    )
    ax.set_xlim(START_YEAR - 0.5, END_YEAR + 0.5)
    ax.set_ylim(0, 105)
    ax.legend(loc="lower right", frameon=False)

    # Patch legend
    green_patch  = mpatches.Patch(color="#27ae60", label="100% complete")
    orange_patch = mpatches.Patch(color="#f39c12", label="90–99% complete")
    red_patch    = mpatches.Patch(color="#e74c3c", label="<90% complete")
    ax.legend(handles=[green_patch, orange_patch, red_patch],
              loc="lower right", frameon=False, fontsize=8)

    fig.tight_layout()
    _save_fig(fig, "FIGURE_01_DATA_COVERAGE.png")


# ─── FIGURE 02: 11-Panel ETCCDI Time Series ─────────────────────────────────

def plot_figure02(df_etccdi: pd.DataFrame, df_trend: pd.DataFrame) -> None:
    """Multi-panel time series for all 11 ETCCDI indices with Sen's slope."""
    panel_labels = list("abcdefghijk")
    n_panels = len(INDICES)
    n_cols = 3
    n_rows = int(np.ceil(n_panels / n_cols))  # 4 rows × 3 cols = 12 (last cell empty)

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(11, 14))
    axes = axes.flatten()

    trend_dict = {}
    if df_trend is not None and not df_trend.empty:
        for _, row in df_trend.iterrows():
            trend_dict[row["Index"]] = row

    years = df_etccdi["Year"].values

    for i, idx in enumerate(INDICES):
        ax = axes[i]
        y  = df_etccdi[idx].values
        valid_mask = ~np.isnan(y)
        x_valid = years[valid_mask]
        y_valid = y[valid_mask]

        # Scatter + bar
        ax.bar(x_valid, y_valid, color=COL_DATA, alpha=0.45, width=0.7)
        ax.plot(x_valid, y_valid, "o-", color=COL_DATA, markersize=2.5,
                linewidth=0.7, alpha=0.9)

        # Sen's slope line
        if idx in trend_dict:
            tr = trend_dict[idx]
            slope     = tr.get("Sen_slope", np.nan)
            intercept = tr.get("Intercept", np.nan)
            p_fdr     = tr.get("p_FDR", np.nan)
            ci_low    = tr.get("CI_low", np.nan)
            ci_high   = tr.get("CI_high", np.nan)
            trend_lbl = tr.get("Trend", "")

            if not np.isnan(slope) and len(x_valid) > 0:
                x_line = np.array([x_valid.min(), x_valid.max()])
                y_line = slope * x_line + intercept
                ax.plot(x_line, y_line, "-", color=COL_TREND,
                        linewidth=1.5, label=f"Sen's slope = {slope:.4f} {UNITS[idx]}/yr")

                # CI shading (approximate: CI on slope only)
                if not np.isnan(ci_low) and not np.isnan(ci_high):
                    y_lo = ci_low  * x_line + intercept
                    y_hi = ci_high * x_line + intercept
                    ax.fill_between(x_line, y_lo, y_hi, alpha=0.12, color=COL_CI)

                # Significance annotation
                if not np.isnan(p_fdr):
                    sig_text = f"p_FDR = {p_fdr:.3f}"
                    if p_fdr < 0.05:
                        sig_text += " *"
                    ax.annotate(sig_text, xy=(0.97, 0.95), xycoords="axes fraction",
                                ha="right", va="top", fontsize=7,
                                color=COL_TREND if p_fdr < 0.05 else COL_NS)

        label = f"({panel_labels[i]}) {idx}"
        unit  = UNITS.get(idx, "")
        ax.set_title(label, fontsize=9, loc="left", pad=2)
        ax.set_ylabel(unit, fontsize=8)
        ax.set_xlabel("Year" if i >= (n_panels - n_cols) else "", fontsize=8)
        ax.set_xlim(START_YEAR - 1, END_YEAR + 1)
        ax.tick_params(axis="both", labelsize=7)

    # Hide unused panels
    for j in range(n_panels, len(axes)):
        axes[j].set_visible(False)

    fig.suptitle(
        "Figure 2. Annual time series of 11 ETCCDI extreme precipitation indices\n"
        "Phitsanulok Station (WMO 48378), 1961–2019. Red line = Sen's slope; shaded area = 95% CI.",
        fontsize=9, y=1.002,
    )
    fig.tight_layout(rect=[0, 0, 1, 1])
    _save_fig(fig, "FIGURE_02_ETCCDI_TIME_SERIES.png")


# ─── FIGURE 03: Trend Heatmap ────────────────────────────────────────────────

def plot_figure03(df_trend: pd.DataFrame) -> None:
    """Trend heatmap: rows=indices, cols=[Sen_slope, p_raw, p_FDR, direction]."""
    if df_trend is None or df_trend.empty:
        print("[FIG] No trend data for heatmap.")
        return

    fig, axes = plt.subplots(1, 4, figsize=(11, 5),
                             gridspec_kw={"width_ratios": [2.5, 1.5, 1.5, 1.5]})

    indices = df_trend["Index"].tolist()
    y_pos   = np.arange(len(indices))

    # Panel 1: Sen's slope (normalized for color, actual value as text)
    ax = axes[0]
    slopes = df_trend["Sen_slope"].values.astype(float)
    p_fdrs = df_trend["p_FDR"].values.astype(float)
    trends = df_trend["Trend"].values

    # Normalize slopes for color map
    abs_max = np.nanmax(np.abs(slopes))
    norm_slopes = slopes / abs_max if abs_max > 0 else slopes

    cmap = plt.cm.RdBu_r
    for j, (ns, s, p, t) in enumerate(zip(norm_slopes, slopes, p_fdrs, trends)):
        color = cmap(0.5 + ns * 0.45) if not np.isnan(ns) else (0.8, 0.8, 0.8, 1)
        rect  = plt.Rectangle([0, j - 0.4], 1, 0.8, color=color)
        ax.add_patch(rect)
        sig_str = "*" if (not np.isnan(p) and p < 0.05) else ""
        val_str = f"{s:.3f}{sig_str}" if not np.isnan(s) else "NA"
        ax.text(0.5, j, val_str, ha="center", va="center", fontsize=7.5,
                color="white" if abs(ns) > 0.5 else "black")

    ax.set_xlim(0, 1)
    ax.set_ylim(-0.5, len(indices) - 0.5)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(indices)
    ax.set_xticks([])
    ax.set_title("Sen's slope\n(unit/yr)", fontsize=8)
    ax.invert_yaxis()

    # Panel 2: p_raw
    _plot_p_panel(axes[1], df_trend["p_raw"].values, indices, "p-value\n(raw)")

    # Panel 3: p_FDR
    _plot_p_panel(axes[2], df_trend["p_FDR"].values, indices, "p-value\n(FDR-adjusted)")

    # Panel 4: Trend direction
    ax4 = axes[3]
    for j, t in enumerate(trends):
        t_str = str(t)
        if "Significant increasing" in t_str:
            color = COL_POS
            symbol = "▲"
        elif "Significant decreasing" in t_str:
            color = COL_NEG
            symbol = "▼"
        elif "increasing" in t_str.lower():
            color = "#7fb3d3"
            symbol = "△"
        else:
            color = "#f0a899"
            symbol = "▽"
        rect = plt.Rectangle([0, j - 0.4], 1, 0.8, color=color, alpha=0.7)
        ax4.add_patch(rect)
        ax4.text(0.5, j, symbol, ha="center", va="center", fontsize=11)

    ax4.set_xlim(0, 1)
    ax4.set_ylim(-0.5, len(indices) - 0.5)
    ax4.set_yticks(y_pos)
    ax4.set_yticklabels([])
    ax4.set_xticks([])
    ax4.set_title("Trend\ndirection", fontsize=8)
    ax4.invert_yaxis()

    # Legend
    legend_elements = [
        mpatches.Patch(color=COL_POS, label="▲ Significant increasing"),
        mpatches.Patch(color=COL_NEG, label="▼ Significant decreasing"),
        mpatches.Patch(color="#7fb3d3", label="△ Non-sig. increasing"),
        mpatches.Patch(color="#f0a899", label="▽ Non-sig. decreasing"),
    ]
    fig.legend(handles=legend_elements, loc="lower center",
               ncol=2, fontsize=8, frameon=False, bbox_to_anchor=(0.5, -0.04))

    fig.suptitle(
        "Figure 3. Trend analysis heatmap for 11 ETCCDI indices\n"
        "Phitsanulok (WMO 48378), 1961–2019. * FDR p < 0.05.",
        fontsize=9, y=1.01,
    )
    fig.tight_layout()
    _save_fig(fig, "FIGURE_03_TREND_HEATMAP.png")


def _plot_p_panel(ax, p_values, indices, title: str) -> None:
    """Helper: plot p-value panel in heatmap."""
    y_pos = np.arange(len(indices))
    for j, p in enumerate(p_values):
        pv = float(p) if not np.isnan(float(p)) else 1.0
        # Color: significant = red-ish, non-significant = grey
        intensity = max(0, 1 - pv / 0.10) if pv < 0.10 else 0
        color = (1 - intensity * 0.5, 1 - intensity * 0.7, 1 - intensity * 0.8, 1)
        rect  = plt.Rectangle([0, j - 0.4], 1, 0.8, color=color)
        ax.add_patch(rect)
        p_str = f"{pv:.3f}" if not np.isnan(p) else "NA"
        ax.text(0.5, j, p_str, ha="center", va="center", fontsize=7.5)

    ax.set_xlim(0, 1)
    ax.set_ylim(-0.5, len(indices) - 0.5)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([])
    ax.set_xticks([])
    ax.set_title(title, fontsize=8)
    ax.invert_yaxis()


# ─── FIGURE 04: Forest Plot ───────────────────────────────────────────────────

def plot_figure04(df_trend: pd.DataFrame) -> None:
    """Sen's slope forest plot with 95% CI."""
    if df_trend is None or df_trend.empty:
        print("[FIG] No trend data for forest plot.")
        return

    # Group by unit to handle mixed units
    unit_groups = {}
    for idx in INDICES:
        unit = UNITS.get(idx, "")
        unit_groups.setdefault(unit, []).append(idx)

    n_groups = len(unit_groups)
    fig, axes = plt.subplots(1, n_groups, figsize=(11, 5),
                             gridspec_kw={"width_ratios": [len(v) for v in unit_groups.values()]})
    if n_groups == 1:
        axes = [axes]

    trend_lookup = {row["Index"]: row for _, row in df_trend.iterrows()}

    for ax_i, (unit, idx_list) in enumerate(unit_groups.items()):
        ax    = axes[ax_i]
        y_pos = np.arange(len(idx_list))

        for j, idx in enumerate(idx_list):
            if idx not in trend_lookup:
                continue
            row   = trend_lookup[idx]
            slope = float(row.get("Sen_slope", np.nan))
            ci_lo = float(row.get("CI_low",   np.nan))
            ci_hi = float(row.get("CI_high",  np.nan))
            trend = str(row.get("Trend", ""))
            p_fdr = float(row.get("p_FDR",    np.nan))

            color = _trend_color(trend)

            if not np.isnan(slope):
                # CI line
                if not np.isnan(ci_lo) and not np.isnan(ci_hi):
                    ax.plot([ci_lo, ci_hi], [j, j], "-",
                            color=color, linewidth=2, alpha=0.7)
                # Point estimate
                ax.plot(slope, j, "D", color=color,
                        markersize=6, zorder=5)

        # Zero reference line
        ax.axvline(x=0, color="black", linewidth=0.8, linestyle="--", alpha=0.6)

        ax.set_yticks(y_pos)
        ax.set_yticklabels(idx_list)
        ax.set_xlabel(f"Sen's slope ({unit}/yr)")
        ax.set_title(f"Unit: {unit}", fontsize=8)
        ax.set_ylim(-0.5, len(idx_list) - 0.5)
        ax.invert_yaxis()

    # Legend
    sig_inc  = Line2D([0], [0], marker="D", color="w", markerfacecolor=COL_POS, markersize=8, label="Significant increasing")
    sig_dec  = Line2D([0], [0], marker="D", color="w", markerfacecolor=COL_NEG, markersize=8, label="Significant decreasing")
    ns_line  = Line2D([0], [0], marker="D", color="w", markerfacecolor=COL_NS,  markersize=8, label="Non-significant")
    fig.legend(handles=[sig_inc, sig_dec, ns_line], loc="lower center",
               ncol=3, fontsize=8, frameon=False, bbox_to_anchor=(0.5, -0.05))

    fig.suptitle(
        "Figure 4. Sen's slope estimates with 95% confidence intervals for 11 ETCCDI indices\n"
        "Phitsanulok (WMO 48378), 1961–2019. Dashed line = zero slope reference.",
        fontsize=9, y=1.02,
    )
    fig.tight_layout()
    _save_fig(fig, "FIGURE_04_SENS_SLOPE_CI.png")


# ─── FIGURE 05: ACF Diagnostic ───────────────────────────────────────────────

def plot_figure05(df_etccdi: pd.DataFrame, df_acf: pd.DataFrame) -> None:
    """ACF diagnostic plots for all 11 indices (multi-panel)."""
    n_panels = len(INDICES)
    n_cols   = 3
    n_rows   = int(np.ceil(n_panels / n_cols))

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(11, 10))
    axes = axes.flatten()

    for i, idx in enumerate(INDICES):
        ax = axes[i]
        if idx not in df_etccdi.columns:
            ax.set_visible(False)
            continue

        series = df_etccdi[idx].dropna().values
        n      = len(series)
        if n < 5:
            ax.set_visible(False)
            continue

        # Compute ACF
        from autocorrelation import compute_acf
        acf_vals  = compute_acf(series, ACF_MAX_LAG)
        lags      = np.arange(1, ACF_MAX_LAG + 1)
        sig_bound = ACF_SIG_FACTOR / np.sqrt(n)

        # Bar chart of ACF
        colors = [COL_NEG if abs(v) > sig_bound else COL_DATA for v in acf_vals]
        ax.bar(lags, acf_vals, color=colors, width=0.6, alpha=0.75)

        # Significance bounds
        ax.axhline(y=sig_bound,  color=COL_TREND, linestyle="--", linewidth=0.9, alpha=0.8)
        ax.axhline(y=-sig_bound, color=COL_TREND, linestyle="--", linewidth=0.9, alpha=0.8)
        ax.axhline(y=0, color="black", linewidth=0.5)

        ax.set_title(f"({chr(97+i)}) {idx}", fontsize=8.5, loc="left")
        ax.set_xlabel("Lag (years)", fontsize=8)
        ax.set_ylabel("ACF", fontsize=8)
        ax.set_xlim(0.5, ACF_MAX_LAG + 0.5)
        ax.set_ylim(-1.05, 1.05)
        ax.set_xticks(lags)
        ax.tick_params(axis="both", labelsize=7)
        ax.text(0.97, 0.97, f"N = {n}", transform=ax.transAxes,
                ha="right", va="top", fontsize=7, color="grey")

    for j in range(n_panels, len(axes)):
        axes[j].set_visible(False)

    fig.suptitle(
        "Figure 5. Autocorrelation function (ACF) diagnostics for 11 ETCCDI annual series\n"
        "Phitsanulok (WMO 48378), 1961–2019. Dashed lines = 95% significance bounds (±2/√N).",
        fontsize=9, y=1.002,
    )
    fig.tight_layout()
    _save_fig(fig, "FIGURE_05_ACF_DIAGNOSTIC.png")


# ─── FIGURE 06: Distribution ─────────────────────────────────────────────────

def plot_figure06(df_etccdi: pd.DataFrame) -> None:
    """Standardized boxplot distribution for all 11 ETCCDI indices."""
    # Standardize for visualization only (z-scores)
    df_std = pd.DataFrame()
    df_std["Year"] = df_etccdi["Year"]
    for idx in INDICES:
        if idx in df_etccdi.columns:
            series = df_etccdi[idx].dropna()
            if series.std() > 0:
                df_std[idx] = (df_etccdi[idx] - series.mean()) / series.std()
            else:
                df_std[idx] = df_etccdi[idx] - series.mean()

    # Melt for seaborn-style plot
    df_melt = df_std[INDICES].melt(var_name="Index", value_name="Standardized_value")

    fig, ax = plt.subplots(figsize=(11, 5))

    # Manual boxplot to avoid seaborn dependency issues
    data_list = [df_std[idx].dropna().values for idx in INDICES if idx in df_std.columns]
    idx_labels = [idx for idx in INDICES if idx in df_std.columns]

    bp = ax.boxplot(data_list, tick_labels=idx_labels, patch_artist=True,
                    medianprops=dict(color="black", linewidth=1.2),
                    boxprops=dict(facecolor="#d0e8f7", linewidth=0.8),
                    whiskerprops=dict(linewidth=0.8),
                    capprops=dict(linewidth=0.8),
                    flierprops=dict(marker="o", markersize=2.5,
                                    markerfacecolor=COL_DATA, alpha=0.5),
                    widths=0.55)

    ax.axhline(y=0, color="grey", linewidth=0.7, linestyle="--", alpha=0.6)
    ax.set_xlabel("ETCCDI Index")
    ax.set_ylabel("Standardised value (z-score)")
    ax.set_title(
        "Figure 6. Distribution of 11 ETCCDI annual indices (standardised for visualisation only)\n"
        "Phitsanulok (WMO 48378), 1961–2019. Actual values used in all statistical analyses.",
        fontsize=9, loc="left",
    )
    ax.tick_params(axis="x", rotation=30)

    fig.tight_layout()
    _save_fig(fig, "FIGURE_06_ETCCDI_DISTRIBUTION.png")


# ─── Main ─────────────────────────────────────────────────────────────────────

def run_all_figures(df_etccdi: pd.DataFrame, df_quality: pd.DataFrame,
                    df_trend: pd.DataFrame, df_acf: pd.DataFrame) -> None:
    """Produce all 6 publication figures."""
    print("[FIG] Generating Figure 01 — Data Coverage...")
    plot_figure01(df_quality)

    print("[FIG] Generating Figure 02 — ETCCDI Time Series...")
    plot_figure02(df_etccdi, df_trend)

    print("[FIG] Generating Figure 03 — Trend Heatmap...")
    plot_figure03(df_trend)

    print("[FIG] Generating Figure 04 — Forest Plot...")
    plot_figure04(df_trend)

    print("[FIG] Generating Figure 05 — ACF Diagnostic...")
    plot_figure05(df_etccdi, df_acf)

    print("[FIG] Generating Figure 06 — Distribution...")
    plot_figure06(df_etccdi)

    print("[FIG] All figures generated.")
