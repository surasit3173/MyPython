"""
figures.py — Publication-quality figures for Chiang Mai ETCCDI analysis.
Enhanced for Q3 Journal Submission (CMJS).
"""

import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from pathlib import Path
from scipy.stats import theilslopes

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
    p_col = "PRECIP" if "PRECIP" in df_daily.columns else "Precipitation_mm"
    df_m = df_daily.groupby(["YEAR", "MONTH"])[p_col].sum().reset_index()
    m_mean = df_m.groupby("MONTH")[p_col].mean()
    m_std = df_m.groupby("MONTH")[p_col].std()

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

        # Robust Theil-Sen fit
        res = theilslopes(y, years)
        slope = res.slope
        intercept = res.intercept
        y_line = slope * years + intercept

        ax.plot(years, y_line, color=COL_TREND, linewidth=1.2, linestyle="-")

        p_raw = t_info.get("P_raw", 1.0)
        slope_dec = t_info.get("Sen_slope_decade", 0.0)
        p_test = t_info.get("Primary_test", "Ordinary_MK")
        test_tag = "HR-MK" if "Hamed" in str(p_test) else "MK"

        label_txt = f"Slope: {slope_dec:+.2f} {unit}/dec\nP = {p_raw:.3f} ({test_tag})"
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

        res = theilslopes(y, years)
        slope = res.slope
        intercept = res.intercept
        y_line = slope * years + intercept

        ax.plot(years, y_line, color=COL_TREND, linewidth=1.2, linestyle="-")

        p_raw = t_info.get("P_raw", 1.0)
        slope_dec = t_info.get("Sen_slope_decade", 0.0)
        p_test = t_info.get("Primary_test", "Ordinary_MK")
        test_tag = "HR-MK" if "Hamed" in str(p_test) else "MK"

        label_txt = f"Slope: {slope_dec:+.2f} {unit}/dec\nP = {p_raw:.3f} ({test_tag})"
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


# ─── FIGURE 4: Decadal Sen's Slopes & 95% CIs (3 Panels) ─────────────────────

def plot_figure04(df_trend: pd.DataFrame) -> None:
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(11, 4.5))

    trend_dict = {row["Index"]: row for _, row in df_trend.iterrows()}

    # Panel (a): Precipitation accumulation (mm/decade)
    p_indices = ["PRCPTOT", "Rx1day", "Rx5day", "R95p", "R99p"][::-1]
    y1 = np.arange(len(p_indices))
    ax1.axvline(x=0, color="black", linestyle="--", linewidth=0.8, alpha=0.7)
    for j, idx in enumerate(p_indices):
        info = trend_dict[idx]
        slope = info["Sen_slope_decade"]
        ci_low = info["CI95_low"] * 10.0
        ci_high = info["CI95_high"] * 10.0
        ax1.plot([ci_low, ci_high], [y1[j], y1[j]], color=COL_DATA, linewidth=1.2)
        ax1.plot(slope, y1[j], "o", color=COL_DATA, markersize=5)
    ax1.set_yticks(y1)
    ax1.set_yticklabels(p_indices)
    ax1.set_xlabel("Sen's Slope (mm decade⁻¹)")
    ax1.set_title("(a) Precipitation Amount", loc="left")
    ax1.grid(True, linestyle=":", alpha=0.5)

    # Panel (b): Precipitation intensity (mm/day/decade)
    i_indices = ["SDII"]
    y2 = np.arange(len(i_indices))
    ax2.axvline(x=0, color="black", linestyle="--", linewidth=0.8, alpha=0.7)
    for j, idx in enumerate(i_indices):
        info = trend_dict[idx]
        slope = info["Sen_slope_decade"]
        ci_low = info["CI95_low"] * 10.0
        ci_high = info["CI95_high"] * 10.0
        ax2.plot([ci_low, ci_high], [y2[j], y2[j]], color=COL_DATA, linewidth=1.2)
        ax2.plot(slope, y2[j], "o", color=COL_DATA, markersize=5)
    ax2.set_yticks(y2)
    ax2.set_yticklabels(i_indices)
    ax2.set_xlabel("Sen's Slope (mm day⁻¹ decade⁻¹)")
    ax2.set_title("(b) Rainfall Intensity", loc="left")
    ax2.grid(True, linestyle=":", alpha=0.5)

    # Panel (c): Frequency and duration (days/decade)
    f_indices = ["CDD", "CWD", "R10mm", "R20mm", "R50mm"][::-1]
    y3 = np.arange(len(f_indices))
    ax3.axvline(x=0, color="black", linestyle="--", linewidth=0.8, alpha=0.7)
    for j, idx in enumerate(f_indices):
        info = trend_dict[idx]
        slope = info["Sen_slope_decade"]
        ci_low = info["CI95_low"] * 10.0
        ci_high = info["CI95_high"] * 10.0
        ax3.plot([ci_low, ci_high], [y3[j], y3[j]], color=COL_DATA, linewidth=1.2)
        ax3.plot(slope, y3[j], "o", color=COL_DATA, markersize=5)
    ax3.set_yticks(y3)
    ax3.set_yticklabels(f_indices)
    ax3.set_xlabel("Sen's Slope (days decade⁻¹)")
    ax3.set_title("(c) Frequency & Duration", loc="left")
    ax3.grid(True, linestyle=":", alpha=0.5)

    fig.tight_layout()
    _save_fig(fig, "Figure_4_Decadal_Sen_Slopes_CI.png")


# ─── FIGURE 5: Autocorrelation Diagnostics (Lags 1–10 Profile & Ljung-Box) ────

def plot_figure05(df_acf: pd.DataFrame) -> None:
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7))

    indices = df_acf["Index"].values
    bartlett_b = df_acf["Bartlett_bound"].values[0]

    # Panel (a): ACF Lags 1–10 Heatmap / Matrix
    acf_cols = [f"ACF{k}" for k in range(1, 11)]
    acf_matrix = df_acf[acf_cols].values

    im = ax1.imshow(acf_matrix, cmap="RdBu_r", vmin=-0.35, vmax=0.35, aspect="auto")
    ax1.set_yticks(np.arange(len(indices)))
    ax1.set_yticklabels(indices)
    ax1.set_xticks(np.arange(10))
    ax1.set_xticklabels([f"Lag {k}" for k in range(1, 11)])
    ax1.set_title("(a) Residual Autocorrelation Function (Lags 1–10)", loc="left")

    # Mark cells exceeding Bartlett bound
    for r in range(len(indices)):
        for c in range(10):
            val = acf_matrix[r, c]
            text_col = "white" if abs(val) > 0.20 else "black"
            if abs(val) > bartlett_b:
                ax1.text(c, r, f"{val:.2f}*", ha="center", va="center", color="yellow", fontweight="bold", fontsize=7.5)
            else:
                ax1.text(c, r, f"{val:.2f}", ha="center", va="center", color=text_col, fontsize=7)

    cbar = fig.colorbar(im, ax=ax1, fraction=0.02, pad=0.02)
    cbar.set_label("ACF Value (* = Exceeds Bartlett ±0.255)", fontsize=7.5)

    # Panel (b): Ljung-Box p-values
    x_pos = np.arange(len(indices))
    lb_pvals = df_acf["LjungBox_P"].values

    colors = ["#2980b9" if p >= 0.05 else "#e74c3c" for p in lb_pvals]
    ax2.bar(x_pos, lb_pvals, color=colors, alpha=0.85, width=0.55, edgecolor=COL_DATA)
    ax2.axhline(y=0.05, color=COL_TREND, linestyle="--", linewidth=1.0, label="α = 0.05 threshold")
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(indices, rotation=30, ha="right")
    ax2.set_ylabel("Ljung-Box p-value (Lags 1–5)")
    ax2.set_ylim(0, 1.05)
    ax2.set_title("(b) Ljung-Box Portmanteau Diagnostic Test", loc="left")
    ax2.legend(loc="upper right")
    ax2.grid(True, linestyle=":", alpha=0.5)

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
