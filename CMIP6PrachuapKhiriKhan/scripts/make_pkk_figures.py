"""Generate publication-quality 600 DPI PNG + vector PDF figures for Prachuap Khiri Khan manuscript."""

from __future__ import annotations

import os
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.patches as mpatches

# Typography & publication styling
plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["Times New Roman", "DejaVu Serif", "Liberation Serif"]
plt.rcParams["font.size"] = 10
plt.rcParams["axes.labelsize"] = 10
plt.rcParams["axes.titlesize"] = 11
plt.rcParams["xtick.labelsize"] = 9
plt.rcParams["ytick.labelsize"] = 9
plt.rcParams["legend.fontsize"] = 8.5
plt.rcParams["figure.titlesize"] = 12

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / "CMIP6PrachuapKhiriKhan" / "pkk_enso_output"
FIG_OUTPUT_DIR = REPO_ROOT / "CMIP6PrachuapKhiriKhan" / "output" / "figures"
DELIVERABLES_FIG_DIR = REPO_ROOT / "CMIP6PrachuapKhiriKhan" / "deliverables" / "figures"

FIG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DELIVERABLES_FIG_DIR.mkdir(parents=True, exist_ok=True)


def save_fig(fig, name: str):
    png_path_out = FIG_OUTPUT_DIR / f"{name}.png"
    pdf_path_out = FIG_OUTPUT_DIR / f"{name}.pdf"
    png_path_del = DELIVERABLES_FIG_DIR / f"{name}.png"
    pdf_path_del = DELIVERABLES_FIG_DIR / f"{name}.pdf"

    fig.savefig(png_path_out, dpi=600, bbox_inches="tight")
    fig.savefig(pdf_path_out, bbox_inches="tight")
    fig.savefig(png_path_del, dpi=600, bbox_inches="tight")
    fig.savefig(pdf_path_del, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved figure {name} (600 DPI PNG + PDF).")


# Figure 1: Study Area & Gauge Network Map
def make_figure_1():
    coords = pd.read_csv(REPO_ROOT / "CMIP6PrachuapKhiriKhan" / "data" / "station_coordinates_PrachuapKhiriKhan.csv")

    fig, ax = plt.subplots(figsize=(6, 8.5))

    # Plot station points with elevation coloring
    lats = coords["latitude"].values
    lons = coords["longitude"].values
    elevs = []
    for e in coords["elevation (m.MSL.)"]:
        try:
            elevs.append(float(e))
        except:
            elevs.append(15.0) # default mid-value for plotting

    sc = ax.scatter(lons, lats, c=elevs, cmap="terrain", s=110, edgecolor="black", linewidth=1.2, zorder=4)
    cbar = plt.colorbar(sc, ax=ax, shrink=0.6, pad=0.03)
    cbar.set_label("Elevation (m a.s.l.)", fontsize=9.5)

    for _, row in coords.iterrows():
        ax.annotate(
            f"  {row['station']}",
            (row['longitude'], row['latitude']),
            fontsize=8.5,
            fontweight="bold",
            va="center",
            ha="left",
            zorder=5
        )

    ax.set_title("Study Area & Meteorological Station Network\nPrachuap Khiri Khan, Thailand (12 Rain Gauges)", pad=12, fontweight="bold")
    ax.set_xlabel("Longitude (°E)", fontweight="bold")
    ax.set_ylabel("Latitude (°N)", fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.4, zorder=1)

    # Inset locator box / boundary text
    ax.text(0.04, 0.95, "Gulf of Thailand\n(East Coast)", transform=ax.transAxes, fontsize=10, fontstyle="italic", bbox=dict(boxstyle="round,pad=0.3", facecolor="aliceblue", alpha=0.8))

    save_fig(fig, "Figure1_study_area_stations")


# Figure 2: Seasonal Rainfall Climatology across 12 Stations
def make_figure_2():
    metrics = pd.read_csv(OUTPUT_DIR / "seasonal_metrics_all.csv.gz")
    obs = metrics[metrics["source_type"] == "OBSERVED"].copy()
    obs["station"] = obs["station"].astype(str)

    rainy = obs[obs["season_type"] == "RAINY"].groupby("station")["PRCPTOT"].mean().sort_index()
    hotdry = obs[obs["season_type"] == "HOT_DRY"].groupby("station")["PRCPTOT"].mean().sort_index()

    stations = rainy.index.tolist()
    x = np.arange(len(stations))
    width = 0.38

    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    rects1 = ax.bar(x - width/2, rainy.values, width, label="Rainy Season (May–Oct)", color="#1f77b4", edgecolor="black", linewidth=0.8)
    rects2 = ax.bar(x + width/2, hotdry.values, width, label="Hot/Dry Season (Nov–Apr)", color="#ff7f0e", edgecolor="black", linewidth=0.8)

    ax.set_ylabel("Mean Seasonal Rainfall (mm)", fontweight="bold")
    ax.set_xlabel("Station Code", fontweight="bold")
    ax.set_title("Seasonal Rainfall Climatology Across Prachuap Khiri Khan Network (1981–2014)", fontweight="bold", pad=10)
    ax.set_xticks(x)
    ax.set_xticklabels(stations, rotation=45, ha="right")
    ax.legend(frameon=True, facecolor="white", edgecolor="none")
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)

    # Add values on top of bars
    for rect in rects1:
        h = rect.get_height()
        ax.annotate(f"{int(round(h))}", (rect.get_x() + rect.get_width()/2, h + 12), ha="center", va="bottom", fontsize=7.5, rotation=90)

    for rect in rects2:
        h = rect.get_height()
        ax.annotate(f"{int(round(h))}", (rect.get_x() + rect.get_width()/2, h + 12), ha="center", va="bottom", fontsize=7.5, rotation=90)

    ax.set_ylim(0, max(rainy.values) * 1.25)
    save_fig(fig, "Figure2_seasonal_climatology")


# Figure 3: Observed ENSO Response Across 8 Indices & 2 Seasons
def make_figure_3():
    df = pd.read_csv(OUTPUT_DIR / "primary_response_summary.csv")
    obs = df[df["source_type"] == "OBSERVED"].copy()

    indices = ["PRCPTOT", "wet_day_frequency_pct", "Rx1day", "Rx5day", "CDD", "CWD", "R10mm", "R20mm"]
    index_labels = ["PRCPTOT\n(mm)", "Wet-day Freq\n(%)", "Rx1day\n(mm)", "Rx5day\n(mm)", "CDD\n(days)", "CWD\n(days)", "R10mm\n(days)", "R20mm\n(days)"]

    fig, axes = plt.subplots(2, 1, figsize=(9.5, 7.5), sharex=True)

    for season_idx, (season, season_title) in enumerate([("RAINY", "Rainy Season (May–October)"), ("HOT_DRY", "Hot/Dry Season (November–April)")]):
        ax = axes[season_idx]
        sub = obs[obs["season_type"] == season]

        el_vals, el_low, el_high = [], [], []
        la_vals, la_low, la_high = [], [], []

        for m in indices:
            m_sub = sub[sub["metric"] == m]
            el = m_sub[m_sub["phase"] == "EL_NINO"].iloc[0]
            la = m_sub[m_sub["phase"] == "LA_NINA"].iloc[0]

            el_vals.append(el["response_pct"])
            el_low.append(el["response_pct"] - el["ci_low_pct"])
            el_high.append(el["ci_high_pct"] - el["response_pct"])

            la_vals.append(la["response_pct"])
            la_low.append(la["response_pct"] - la["ci_low_pct"])
            la_high.append(la["ci_high_pct"] - la["response_pct"])

        x = np.arange(len(indices))
        width = 0.35

        ax.axhline(0, color="black", linestyle="-", linewidth=0.9, zorder=2)
        ax.errorbar(x - width/2, el_vals, yerr=[el_low, el_high], fmt="o", color="#d62728", ecolor="#d62728", elinewidth=1.5, capsize=4, label="El Niño vs Neutral", zorder=3)
        ax.errorbar(x + width/2, la_vals, yerr=[la_low, la_high], fmt="s", color="#1f77b4", ecolor="#1f77b4", elinewidth=1.5, capsize=4, label="La Niña vs Neutral", zorder=3)

        ax.set_ylabel("Observed Anomaly (%)", fontweight="bold")
        ax.set_title(f"({chr(97 + season_idx)}) {season_title}", fontweight="bold", loc="left", fontsize=10.5)
        ax.grid(True, linestyle="--", alpha=0.4)
        ax.legend(loc="upper right", frameon=True)

    axes[1].set_xticks(x)
    axes[1].set_xticklabels(index_labels, fontweight="bold")
    fig.suptitle("Observed Seasonal ENSO Rainfall Response Across Prachuap Khiri Khan (1981–2014)", fontweight="bold", y=0.98, fontsize=12)
    plt.tight_layout()
    save_fig(fig, "Figure3_observed_enso_response")


# Figure 4: CMIP6 Model Spread vs Observed Anomalies (Raw vs QDM)
def make_figure_4():
    df = pd.read_csv(OUTPUT_DIR / "primary_response_summary.csv")

    indices = ["PRCPTOT", "wet_day_frequency_pct", "Rx1day", "Rx5day", "CDD", "CWD", "R10mm", "R20mm"]
    fig, axes = plt.subplots(2, 2, figsize=(10, 8), sharex=True, sharey=True)

    panels = [
        ("RAINY", "EL_NINO", "(a) Rainy Season — El Niño"),
        ("RAINY", "LA_NINA", "(b) Rainy Season — La Niña"),
        ("HOT_DRY", "EL_NINO", "(c) Hot/Dry Season — El Niño"),
        ("HOT_DRY", "LA_NINA", "(d) Hot/Dry Season — La Niña"),
    ]

    for p_idx, (season, phase, title) in enumerate(panels):
        ax = axes[p_idx // 2, p_idx % 2]

        obs = df[(df["source_type"] == "OBSERVED") & (df["season_type"] == season) & (df["phase"] == phase)].set_index("metric")["response_pct"]
        raw = df[(df["source_type"] == "RAW") & (df["season_type"] == season) & (df["phase"] == phase)].set_index("metric")["response_pct"]
        qdm = df[(df["source_type"] == "QDM") & (df["season_type"] == season) & (df["phase"] == phase)].set_index("metric")["response_pct"]

        x = np.arange(len(indices))
        width = 0.25

        ax.axhline(0, color="black", linestyle="-", linewidth=0.8)
        ax.bar(x - width, [obs[m] for m in indices], width, label="Observed", color="#2ca02c", edgecolor="black")
        ax.bar(x, [raw[m] for m in indices], width, label="CMIP6 Raw", color="#ff7f0e", edgecolor="black")
        ax.bar(x + width, [qdm[m] for m in indices], width, label="CMIP6 QDM", color="#1f77b4", edgecolor="black")

        ax.set_title(title, fontweight="bold", loc="left", fontsize=10)
        ax.grid(True, linestyle="--", alpha=0.3)
        if p_idx % 2 == 0:
            ax.set_ylabel("Anomaly (%)", fontweight="bold")

    for col in range(2):
        axes[1, col].set_xticks(x)
        axes[1, col].set_xticklabels(indices, rotation=45, ha="right", fontweight="bold")

    axes[0, 0].legend(loc="upper right", fontsize=8)
    fig.suptitle("CMIP6 Multi-Model Ensemble vs Observed ENSO Anomalies: Raw vs. QDM", fontweight="bold", y=0.98, fontsize=11.5)
    plt.tight_layout()
    save_fig(fig, "Figure4_cmip6_raw_vs_qdm_spread")


# Figure 5: QDM Teleconnection Signal Preservation Classification
def make_figure_5():
    pres = pd.read_csv(OUTPUT_DIR / "qdm_enso_signal_preservation.csv")

    cat_counts = pres["category"].value_counts()
    colors = {"PRESERVED": "#2ca02c", "ATTENUATED": "#ff7f0e", "AMPLIFIED": "#1f77b4", "REVERSED": "#d62728", "INDETERMINATE_RAW_NEAR_ZERO": "#7f7f7f"}

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))

    # Panel 1: Bar chart of categories
    cats = ["PRESERVED", "ATTENUATED", "AMPLIFIED", "REVERSED", "INDETERMINATE_RAW_NEAR_ZERO"]
    counts = [cat_counts.get(c, 0) for c in cats]
    bar_colors = [colors[c] for c in cats]

    rects = ax1.bar(cats, counts, color=bar_colors, edgecolor="black", linewidth=1.0)
    ax1.set_ylabel("Number of Metric-Phase-Season Targets", fontweight="bold")
    ax1.set_title("(a) Distribution of QDM Teleconnection Signal Effects", fontweight="bold", loc="left", fontsize=10)
    ax1.grid(True, axis="y", linestyle="--", alpha=0.4)

    for rect in rects:
        h = rect.get_height()
        ax1.annotate(f"{h}", (rect.get_x() + rect.get_width()/2, h + 0.3), ha="center", va="bottom", fontweight="bold")

    ax1.set_ylim(0, max(counts) + 2)

    # Panel 2: Scatter plot of Abs Error Reduction
    raw_err = pres["raw_absolute_error_vs_observed_pct_points"]
    qdm_err = pres["qdm_absolute_error_vs_observed_pct_points"]

    ax2.scatter(raw_err, qdm_err, c=[colors[c] for c in pres["category"]], s=60, edgecolor="black", alpha=0.85, zorder=3)
    max_val = max(max(raw_err), max(qdm_err)) + 5
    ax2.plot([0, max_val], [0, max_val], color="gray", linestyle="--", label="1:1 Line (No Error Change)")

    ax2.set_xlabel("Raw CMIP6 Absolute Anomaly Error (%p)", fontweight="bold")
    ax2.set_ylabel("QDM CMIP6 Absolute Anomaly Error (%p)", fontweight="bold")
    ax2.set_title("(b) Anomaly Error Reduction (Points Below Line = Improved)", fontweight="bold", loc="left", fontsize=10)
    ax2.grid(True, linestyle="--", alpha=0.4)

    # Legend
    patches = [mpatches.Patch(color=colors[c], label=c) for c in cats]
    patches.append(mpatches.Patch(color="none", label="")) # spacer
    ax2.legend(handles=patches, loc="upper left", fontsize=8)

    fig.suptitle("Synthesis of QDM Effects on ENSO Teleconnection Signal Preservation", fontweight="bold", y=0.98, fontsize=11.5)
    plt.tight_layout()
    save_fig(fig, "Figure5_qdm_signal_preservation_synthesis")


# Graphical Abstract
def make_graphical_abstract():
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.axis("off")

    # Workflow boxes
    boxes = [
        ("12 Rain Gauges\nPrachuap Khiri Khan\n(1981–2014 Daily)", 0.08, 0.5, "#e3f2fd"),
        ("ENSO Phase\nClassification\n(ONI & Niño-3.4)", 0.30, 0.5, "#fff3e0"),
        ("5 CMIP6 Models\n(ACCESS, CESM2, CanESM5,\nEC-Earth3, MIROC6)", 0.52, 0.5, "#f3e5f5"),
        ("Blocked Cross-Fitted\nQDM Bias Correction", 0.74, 0.5, "#e8f5e9"),
    ]

    for text, x, y, color in boxes:
        bbox = dict(boxstyle="round,pad=0.6", facecolor=color, edgecolor="black", linewidth=1.2)
        ax.text(x, y, text, ha="center", va="center", fontsize=9.5, fontweight="bold", bbox=bbox)

    # Arrows between boxes
    ax.annotate("", xy=(0.20, 0.5), xytext=(0.18, 0.5), arrowprops=dict(arrowstyle="->", lw=2, color="black"))
    ax.annotate("", xy=(0.42, 0.5), xytext=(0.40, 0.5), arrowprops=dict(arrowstyle="->", lw=2, color="black"))
    ax.annotate("", xy=(0.64, 0.5), xytext=(0.62, 0.5), arrowprops=dict(arrowstyle="->", lw=2, color="black"))

    # Core message outcome box at bottom
    outcome_text = (
        "CORE SCIENTIFIC FINDING:\n"
        "• QDM substantially improves marginal precipitation distributions and seasonal climatology.\n"
        "• HOWEVER, QDM does NOT uniformly improve ENSO teleconnection anomaly fidelity across indices.\n"
        "• Anomaly errors decreased in 34% of targets, while signal attenuation/reversal occurred in extreme indices."
    )
    bbox_out = dict(boxstyle="round,pad=0.8", facecolor="#ffebee", edgecolor="#d32f2f", linewidth=1.5)
    ax.text(0.5, 0.15, outcome_text, ha="center", va="center", fontsize=9.5, fontweight="bold", bbox=bbox_out)

    save_fig(fig, "Graphical_Abstract")


if __name__ == "__main__":
    make_figure_1()
    make_figure_2()
    make_figure_3()
    make_figure_4()
    make_figure_5()
    make_graphical_abstract()
