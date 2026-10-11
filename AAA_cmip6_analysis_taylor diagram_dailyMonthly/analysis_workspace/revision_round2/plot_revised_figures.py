from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent / "mplconfig"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "analysis_workspace" / "audit_corrected"
OUT = Path(__file__).resolve().parent / "figures"

SCENARIOS = ["ssp245", "ssp585"]
WINDOWS = ["Near-term", "Mid-term", "Long-term"]


def setup_plotting() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "DejaVu Serif"],
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.dpi": 450,
        }
    )


def plot_baseline_sensitivity(frame: pd.DataFrame) -> None:
    setup_plotting()
    marker_map = {"Near-term": "o", "Mid-term": "s", "Long-term": "^"}
    color_map = {"Near-term": "#0072B2", "Mid-term": "#E69F00", "Long-term": "#009E73"}
    all_values = pd.concat([frame["obs_median_pct"], frame["model_median_pct"]])
    all_values = all_values.replace([np.inf, -np.inf], np.nan).dropna()
    limit = min(220.0, max(50.0, float(np.nanpercentile(np.abs(all_values), 95)) * 1.15))

    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.40), sharex=True, sharey=True)
    for ax, scenario in zip(axes, SCENARIOS):
        subset = frame[(frame["scenario"] == scenario) & (frame["index"] != "R50mm")]
        for window in WINDOWS:
            block = subset[subset["window"] == window]
            ax.scatter(
                block["obs_median_pct"],
                block["model_median_pct"],
                marker=marker_map[window],
                s=38,
                facecolor=color_map[window],
                edgecolor="white",
                linewidth=0.55,
                alpha=0.92,
                zorder=3,
            )
        reversals = subset[subset["sign_reversal"].astype(bool)]
        ax.scatter(
            reversals["obs_median_pct"],
            reversals["model_median_pct"],
            marker="x",
            s=32,
            color="#222222",
            linewidth=1.05,
            zorder=4,
        )
        ax.axhline(0, color="#777777", lw=0.7)
        ax.axvline(0, color="#777777", lw=0.7)
        ax.plot([-limit, limit], [-limit, limit], color="#444444", lw=0.8, ls="--")
        ax.set_xlim(-limit, limit)
        ax.set_ylim(-limit, limit)
        ax.grid(True, color="#E5E5E5", lw=0.5)
        ax.set_title("SSP2-4.5" if scenario == "ssp245" else "SSP5-8.5")
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("Change vs observed baseline (%)")
    axes[0].set_ylabel("Change vs model historical baseline (%)")

    handles = [
        Line2D(
            [0],
            [0],
            marker=marker_map[window],
            color="none",
            markeredgecolor="white",
            markerfacecolor=color_map[window],
            label=window,
            markersize=6.5,
        )
        for window in WINDOWS
    ]
    handles.append(
        Line2D([0], [0], marker="x", color="none", markeredgecolor="#222222", label="Sign reversal", markersize=6)
    )
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 1.02), ncol=4, frameon=False)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(OUT / "FIGURE_02_baseline_sensitivity_revised.png", bbox_inches="tight")
    plt.close(fig)


def plot_selected_profiles(frame: pd.DataFrame) -> None:
    setup_plotting()
    selected = ["PRCPTOT", "SDII", "Rx5day", "R99p", "CDD", "CWD"]
    styles = {
        "ssp245": {"label": "SSP2-4.5", "color": "#0072B2", "marker": "o", "ls": "-"},
        "ssp585": {"label": "SSP5-8.5", "color": "#D55E00", "marker": "s", "ls": "--"},
    }
    x = np.arange(3)
    fig, axes = plt.subplots(2, 3, figsize=(7.1, 4.9), sharex=True)
    for ax, index in zip(axes.flat, selected):
        for scenario in SCENARIOS:
            style = styles[scenario]
            block = frame[(frame["scenario"] == scenario) & (frame["index"] == index)]
            block = block.set_index("window").loc[WINDOWS]
            y = block["model_median_pct"].to_numpy(float)
            lo = block["model_q25_pct"].to_numpy(float)
            hi = block["model_q75_pct"].to_numpy(float)
            ax.fill_between(x, lo, hi, color=style["color"], alpha=0.15, lw=0)
            ax.plot(
                x,
                y,
                ls=style["ls"],
                marker=style["marker"],
                color=style["color"],
                lw=1.35,
                ms=4.3,
                markerfacecolor=style["color"],
                label=style["label"],
            )
            for xi, yi, robust in zip(x, y, block["model_robust"].astype(bool)):
                if not robust:
                    ax.plot(
                        xi,
                        yi,
                        marker=style["marker"],
                        ms=4.8,
                        markerfacecolor="white",
                        markeredgecolor=style["color"],
                        markeredgewidth=1.0,
                        ls="none",
                    )
        ax.axhline(0, color="#777777", lw=0.7)
        ax.grid(axis="y", color="#E5E5E5", lw=0.5)
        ax.set_title(index)
        ax.set_ylabel("Change (%)")
        ax.set_xticks(x, ["Near", "Mid", "Long"])
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 1.01), ncol=2, frameon=False)
    fig.text(
        0.5,
        0.01,
        "Filled markers: ≥6/7 model sign agreement; bands: interquartile range across models",
        ha="center",
        fontsize=7.5,
    )
    fig.tight_layout(rect=(0, 0.035, 1, 0.95))
    fig.savefig(OUT / "FIGURE_04_selected_profiles_revised.png", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(AUDIT / "ensemble_change_sensitivity.csv")
    if len(frame) != 66:
        raise ValueError(f"Expected 66 audited combinations, found {len(frame)}")
    plot_baseline_sensitivity(frame)
    plot_selected_profiles(frame)


if __name__ == "__main__":
    main()
