"""
figures.py — Publication-quality figures for Chiang Mai ETCCDI analysis.
"""

import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (
    OUTPUT_ROOT, STATION_NAME, STATION_WMO, START_YEAR, END_YEAR,
    INDICES, UNITS, FIG_DPI, FIG_FORMAT,
)

# Set style
plt.rcParams["font.sans-serif"] = "DejaVu Sans"
plt.rcParams["font.size"] = 8
plt.rcParams["axes.labelsize"] = 8.5
plt.rcParams["axes.titlesize"] = 9
plt.rcParams["xtick.labelsize"] = 8
plt.rcParams["ytick.labelsize"] = 8
plt.rcParams["legend.fontsize"] = 8
plt.rcParams["figure.titlesize"] = 10

COL_DATA = "#2c3e50"
COL_TREND = "#c0392b"
COL_POS = "#27ae60"
COL_NEG = "#e74c3c"
COL_NS = "#7f8c8d"


def _save_fig(fig, filename: str) -> None:
    fig_dir = OUTPUT_ROOT / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    out_path = fig_dir / filename
    fig.savefig(out_path, dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"[FIG] Saved {out_path}")


# ─── FIGURE 1: Data Coverage & Seasonal Rainfall Regime ──────────────────────

def plot_figure01(df_daily: pd.DataFrame, df_quality: pd.DataFrame) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    # Panel (a): Annual completeness
    years = df_quality["Year"].values
    comp = df_quality["Completeness_percent"].values
    ax1.plot(years, comp, color=COL_DATA, linewidth=1.2, marker="o", markersize=2)
    ax1.axhline(y=90, color=COL_TREND, linestyle="--", linewidth=0.8, label="90% threshold")
    ax1.set_xlabel("Year")
    ax1.set_ylabel("Data Completeness (%)")
    ax1.set_ylim(80, 102)
    ax1.set_title("(a) Annual Data Completeness (1961–2019)", loc="left")
    ax1.legend(loc="lower right")

    # Panel (b): Seasonal regime (Mean monthly precipitation)
    df_m = df_daily.groupby(["YEAR", "MONTH"])["PRECIP"].sum().reset_index()
    m_mean = df_m.groupby("MONTH")["PRECIP"].mean()
    m_std = df_m.groupby("MONTH")["PRECIP"].std()

    months = np.arange(1, 13)
    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    ax2.bar(months, m_mean, yerr=m_std, capsize=3, color="#3498db", edgecolor=COL_DATA, alpha=0.7)
    ax2.set_xticks(months)
    ax2.set_xticklabels(month_labels)
    ax2.set_xlabel("Month")
    ax2.set_ylabel("Precipitation (mm)")
    ax2.set_title("(b) Mean Monthly Rainfall Regime", loc="left")

    fig.tight_layout()
    _save_fig(fig, "Figure_1_Data_Coverage_Seasonal_Regime.png")


# ─── FIGURE 2: Depth / Intensity Time Series ─────────────────────────────────

def plot_figure02(df_etccdi: pd.DataFrame, df_trend: pd.DataFrame) -> None:
    indices_fig2 = ["PRCPTOT", "SDII", "Rx1day", "Rx5day", "R95p", "R99p"]
    fig, axes = plt.subplots(3, 2, figsize=(10, 8), sharex=True)
    axes = axes.flatten()

    years = df_etccdi["Year"].values
    trend_dict = {row["Index"]: row for _, row in df_trend.iterrows()}

    for i, idx in enumerate(indices_fig2):
        ax = axes[i]
        y = df_etccdi[idx].values
        unit = UNITS.get(idx, "")
        t_info = trend_dict.get(idx, {})

        ax.plot(years, y, color=COL_DATA, linewidth=1.0, marker="o", markersize=2.5, alpha=0.8)

        # Plot Sen's slope line
        slope = t_info.get("Sen_slope_year", 0.0)
        p_raw = t_info.get("P_raw", 1.0)
        slope_dec = t_info.get("Sen_slope_decade", 0.0)

        mean_y = np.nanmean(y)
        mean_x = np.nanmean(years)
        intercept = mean_y - slope * mean_x
        y_line = slope * years + intercept

        ax.plot(years, y_line, color=COL_TREND, linewidth=1.2, linestyle="-")

        label_txt = f"Slope: {slope_dec:+.2f} {unit}/dec\np_raw = {p_raw:.3f} (ns)"
        ax.text(0.03, 0.92, label_txt, transform=ax.transAxes, va="top", fontsize=7.5,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8, edgecolor="none"))

        ax.set_ylabel(f"{idx} ({unit})")
        ax.set_title(f"({chr(97+i)}) {idx}", loc="left")
        ax.grid(True, linestyle=":", alpha=0.5)

    for ax in axes[-2:]:
        ax.set_xlabel("Year")

    fig.tight_layout()
    _save_fig(fig, "Figure_2_Depth_Intensity_Indices.png")


# ─── FIGURE 3: Frequency & Spell Time Series ──────────────────────────────────

def plot_figure03(df_etccdi: pd.DataFrame, df_trend: pd.DataFrame) -> None:
    indices_fig3 = ["R10mm", "R20mm", "R50mm", "CDD", "CWD"]
    fig, axes = plt.subplots(3, 2, figsize=(10, 8), sharex=True)
    axes = axes.flatten()

    years = df_etccdi["Year"].values
    trend_dict = {row["Index"]: row for _, row in df_trend.iterrows()}

    for i, idx in enumerate(indices_fig3):
        ax = axes[i]
        y = df_etccdi[idx].values
        unit = UNITS.get(idx, "")
        t_info = trend_dict.get(idx, {})

        ax.plot(years, y, color=COL_DATA, linewidth=1.0, marker="o", markersize=2.5, alpha=0.8)

        slope = t_info.get("Sen_slope_year", 0.0)
        p_raw = t_info.get("P_raw", 1.0)
        slope_dec = t_info.get("Sen_slope_decade", 0.0)

        mean_y = np.nanmean(y)
        mean_x = np.nanmean(years)
        intercept = mean_y - slope * mean_x
        y_line = slope * years + intercept

        ax.plot(years, y_line, color=COL_TREND, linewidth=1.2, linestyle="-")

        label_txt = f"Slope: {slope_dec:+.2f} {unit}/dec\np_raw = {p_raw:.3f} (ns)"
        ax.text(0.03, 0.92, label_txt, transform=ax.transAxes, va="top", fontsize=7.5,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8, edgecolor="none"))

        ax.set_ylabel(f"{idx} ({unit})")
        ax.set_title(f"({chr(97+i)}) {idx}", loc="left")
        ax.grid(True, linestyle=":", alpha=0.5)

    axes[-1].set_visible(False)  # hide 6th panel
    axes[3].set_xlabel("Year")
    axes[4].set_xlabel("Year")

    fig.tight_layout()
    _save_fig(fig, "Figure_3_Frequency_Spell_Indices.png")


# ─── FIGURE 4: Decadal Sen's Slopes & 95% CIs ────────────────────────────────

def plot_figure04(df_trend: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))

    indices = df_trend["Index"].values[::-1]  # reverse for top-to-bottom
    slopes = df_trend["Sen_slope_decade"].values[::-1]
    ci_low = df_trend["CI95_low"].values[::-1] * 10.0
    ci_high = df_trend["CI95_high"].values[::-1] * 10.0

    y_pos = np.arange(len(indices))

    ax.axvline(x=0, color="black", linestyle="--", linewidth=0.8, alpha=0.7)

    for j in range(len(indices)):
        ax.plot([ci_low[j], ci_high[j]], [y_pos[j], y_pos[j]], color=COL_DATA, linewidth=1.2)
        ax.plot(slopes[j], y_pos[j], "o", color=COL_DATA, markersize=5)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(indices)
    ax.set_xlabel("Sen's Slope per Decade (units/decade) with 95% CI")
    ax.set_title("Decadal Trends and 95% Confidence Intervals for 11 ETCCDI Indices", loc="left")
    ax.grid(True, linestyle=":", alpha=0.5)

    fig.tight_layout()
    _save_fig(fig, "Figure_4_Decadal_Sen_Slopes_CI.png")


# ─── FIGURE 5: Autocorrelation Diagnostics ────────────────────────────────────

def plot_figure05(df_acf: pd.DataFrame) -> None:
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6), sharex=True)

    indices = df_acf["Index"].values
    x_pos = np.arange(len(indices))

    acf1_vals = df_acf["ACF1"].values
    bartlett_b = df_acf["Bartlett_bound"].values[0]

    ax1.bar(x_pos, acf1_vals, color="#34495e", alpha=0.8, width=0.5)
    ax1.axhline(y=bartlett_b, color=COL_TREND, linestyle="--", linewidth=0.8, label="Bartlett Bound (±1.96/√N)")
    ax1.axhline(y=-bartlett_b, color=COL_TREND, linestyle="--", linewidth=0.8)
    ax1.axhline(y=0, color="black", linewidth=0.5)
    ax1.set_ylabel("ACF Lag-1")
    ax1.set_title("(a) Residual Autocorrelation at Lag-1", loc="left")
    ax1.legend(loc="upper right")

    lb_pvals = df_acf["LjungBox_P"].values
    ax2.bar(x_pos, lb_pvals, color="#2980b9", alpha=0.8, width=0.5)
    ax2.axhline(y=0.05, color=COL_TREND, linestyle="--", linewidth=0.8, label="α = 0.05")
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(indices, rotation=30, ha="right")
    ax2.set_ylabel("Ljung-Box p-value")
    ax2.set_title("(b) Ljung-Box Portmanteau Test (Lags 1–5)", loc="left")
    ax2.legend(loc="upper right")

    fig.tight_layout()
    _save_fig(fig, "Figure_5_Autocorrelation_Diagnostics.png")


# ─── Main Orchestrator ────────────────────────────────────────────────────────

def run_all_figures(df_daily: pd.DataFrame, df_quality: pd.DataFrame,
                    df_etccdi: pd.DataFrame, df_trend: pd.DataFrame,
                    df_acf: pd.DataFrame) -> None:
    print("[FIG] Generating Figure 1...")
    plot_figure01(df_daily, df_quality)
    print("[FIG] Generating Figure 2...")
    plot_figure02(df_etccdi, df_trend)
    print("[FIG] Generating Figure 3...")
    plot_figure03(df_etccdi, df_trend)
    print("[FIG] Generating Figure 4...")
    plot_figure04(df_trend)
    print("[FIG] Generating Figure 5...")
    plot_figure05(df_acf)
    print("[FIG] All publication figures generated successfully.")
