"""Create the four compact, publication-quality Paper 3 figures."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".matplotlib"))

import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, ListedColormap, TwoSlopeNorm


OUTPUT = ROOT / "output"
FIGURES = OUTPUT / "figures"
FIGURES.mkdir(parents=True, exist_ok=True)

mpl.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "font.size": 8,
        "axes.titlesize": 9,
        "axes.labelsize": 8,
        "legend.fontsize": 7,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "axes.linewidth": 0.7,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)

SOURCE_COLORS = {"OBSERVED": "#000000", "RAW": "#0072B2", "QDM": "#D55E00"}
PHASE_COLORS = {"EL_NINO": "#D55E00", "LA_NINA": "#0072B2"}
METRIC_LABELS = {
    "PRCPTOT": "PRCPTOT",
    "wet_day_frequency_pct": "Wet-day frequency",
    "Rx1day": "Rx1day",
    "CDD": "CDD",
}
PHASE_LABELS = {"EL_NINO": "El Niño", "LA_NINA": "La Niña"}
SEASON_LABELS = {"RAINY": "Rainy (May–Oct)", "HOT_DRY": "Hot/dry (Nov–Apr)"}


def _save(figure: plt.Figure, stem: str) -> None:
    figure.savefig(FIGURES / f"{stem}.png", dpi=600, bbox_inches="tight", facecolor="white")
    figure.savefig(FIGURES / f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    plt.close(figure)


def figure_1() -> None:
    monthly = pd.read_csv(OUTPUT / "observed_oni_monthly_frozen.csv", parse_dates=["date"])
    classes = pd.read_csv(
        OUTPUT / "season_classification_observed.csv",
        parse_dates=["season_start", "season_end"],
    )
    monthly = monthly[(monthly["date"].dt.year >= 1981) & (monthly["date"].dt.year <= 2014)]
    figure, axes = plt.subplots(
        3,
        1,
        figsize=(7.2, 4.9),
        gridspec_kw={"height_ratios": [2.4, 0.55, 0.55], "hspace": 0.28},
        sharex=True,
    )
    ax = axes[0]
    ax.axhspan(0.5, 3.0, color="#D55E00", alpha=0.08)
    ax.axhspan(-3.0, -0.5, color="#0072B2", alpha=0.08)
    ax.axhline(0.5, color="#D55E00", lw=0.7, ls="--")
    ax.axhline(-0.5, color="#0072B2", lw=0.7, ls="--")
    ax.axhline(0, color="0.45", lw=0.6)
    month_x = monthly["date"].dt.year + (monthly["date"].dt.month - 0.5) / 12.0
    ax.plot(month_x, monthly["oni_c"], color="0.2", lw=0.85)
    episode = monthly["episode_sign"].to_numpy(int)
    ax.scatter(
        month_x.loc[episode == 1],
        monthly.loc[episode == 1, "oni_c"],
        s=5,
        color="#D55E00",
        label="persistent El Niño",
        zorder=3,
    )
    ax.scatter(
        month_x.loc[episode == -1],
        monthly.loc[episode == -1, "oni_c"],
        s=5,
        color="#0072B2",
        label="persistent La Niña",
        zorder=3,
    )
    ax.set_ylabel("ONI (°C)")
    ax.set_xlim(1980.5, 2014.5)
    ax.set_title("(a) Frozen NOAA CPC ERSSTv6 ONI and persistent episode membership", loc="left")
    ax.legend(frameon=False, ncol=2, loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)

    phase_code = {"LA_NINA": -1, "NEUTRAL": 0, "EL_NINO": 1, "TRANSITION_UNCLASSIFIED": 2}
    cmap = ListedColormap(["#0072B2", "#E6E6E6", "#D55E00", "#CC79A7"])
    norm = BoundaryNorm([-1.5, -0.5, 0.5, 1.5, 2.5], cmap.N)
    for axis, season, panel in zip(axes[1:], ["RAINY", "HOT_DRY"], ["b", "c"], strict=True):
        table = classes[classes["season_type"] == season].sort_values("climate_year")
        # The Nov-Apr season labelled 2014 ends in April 2015 and is outside
        # the 1981-2014 daily analysis window.  Keep the classification file
        # complete, but plot only seasons eligible for the response analysis.
        if season == "HOT_DRY":
            table = table[table["climate_year"] <= 2013]
        values = np.asarray([[phase_code[value] for value in table["enso_phase"]]], dtype=float)
        axis.imshow(
            values,
            aspect="auto",
            cmap=cmap,
            norm=norm,
            extent=[table["climate_year"].min() - 0.5, table["climate_year"].max() + 0.5, 0, 1],
        )
        counts = table["enso_phase"].value_counts()
        label = ", ".join(
            f"{short}={int(counts.get(phase, 0))}"
            for phase, short in [("EL_NINO", "EN"), ("NEUTRAL", "N"), ("LA_NINA", "LN"), ("TRANSITION_UNCLASSIFIED", "T/U")]
        )
        axis.set_yticks([])
        axis.set_ylabel(SEASON_LABELS[season], rotation=0, ha="right", va="center")
        axis.set_title(f"({panel}) Management-season classification; {label}", loc="left", fontsize=8)
        for spine in axis.spines.values():
            spine.set_linewidth(0.5)
    axes[-1].set_xlabel("Climate-year start")
    axes[-1].set_xticks(np.arange(1981, 2015, 3))
    _save(figure, "Paper3_Figure_01_ENSO_classification")


def figure_2() -> None:
    responses = pd.read_csv(OUTPUT / "primary_response_summary.csv")
    responses = responses[responses["source_type"] == "OBSERVED"]
    figure, axes = plt.subplots(1, 2, figsize=(7.2, 3.5), sharex=False, sharey=True)
    for axis, season, panel in zip(axes, ["RAINY", "HOT_DRY"], ["a", "b"], strict=True):
        table = responses[responses["season_type"] == season]
        y_positions = np.arange(4)
        for offset, phase in [(-0.12, "EL_NINO"), (0.12, "LA_NINA")]:
            phase_table = table[table["phase"] == phase].set_index("metric").loc[list(METRIC_LABELS)]
            estimate = phase_table["response_pct"].to_numpy(float)
            low = phase_table["ci_low_pct"].to_numpy(float)
            high = phase_table["ci_high_pct"].to_numpy(float)
            axis.errorbar(
                estimate,
                y_positions + offset,
                xerr=np.vstack([estimate - low, high - estimate]),
                fmt="o",
                ms=4,
                capsize=2,
                lw=0.9,
                color=PHASE_COLORS[phase],
                label=PHASE_LABELS[phase],
            )
        axis.axvline(0, color="0.35", lw=0.7)
        axis.set_yticks(y_positions, [METRIC_LABELS[value] for value in METRIC_LABELS])
        axis.invert_yaxis()
        axis.grid(axis="x", color="0.9", lw=0.5)
        axis.set_xlabel("Phase response vs Neutral (%)")
        axis.set_title(f"({panel}) {SEASON_LABELS[season]}", loc="left")
        axis.spines[["top", "right"]].set_visible(False)
    axes[0].legend(frameon=False, loc="lower right")
    figure.suptitle("Observed ENSO-conditioned responses (95% event-bootstrap intervals)", y=1.01, fontsize=9)
    _save(figure, "Paper3_Figure_02_observed_responses")


def figure_3() -> None:
    responses = pd.read_csv(OUTPUT / "primary_response_summary.csv")
    categories = [(metric, phase) for metric in METRIC_LABELS for phase in ("EL_NINO", "LA_NINA")]
    labels = [f"{METRIC_LABELS[metric]} — {PHASE_LABELS[phase]}" for metric, phase in categories]
    figure, axes = plt.subplots(1, 2, figsize=(7.2, 5.0), sharey=True)
    offsets = {"OBSERVED": -0.18, "RAW": 0.0, "QDM": 0.18}
    for axis, season, panel in zip(axes, ["RAINY", "HOT_DRY"], ["a", "b"], strict=True):
        y = np.arange(len(categories))
        for source in ("OBSERVED", "RAW", "QDM"):
            source_table = responses[
                (responses["source_type"] == source) & (responses["season_type"] == season)
            ].set_index(["metric", "phase"]).loc[categories]
            estimate = source_table["response_pct"].to_numpy(float)
            low = source_table["ci_low_pct"].to_numpy(float)
            high = source_table["ci_high_pct"].to_numpy(float)
            axis.errorbar(
                estimate,
                y + offsets[source],
                xerr=np.vstack([estimate - low, high - estimate]),
                fmt="o",
                ms=3.5,
                capsize=1.5,
                lw=0.75,
                color=SOURCE_COLORS[source],
                label={"OBSERVED": "Observed", "RAW": "Raw CMIP6", "QDM": "Cross-fitted QDM"}[source],
            )
        axis.axvline(0, color="0.35", lw=0.7)
        axis.set_yticks(y, labels)
        axis.invert_yaxis()
        axis.grid(axis="x", color="0.9", lw=0.5)
        axis.set_xlabel("Phase response vs Neutral (%)")
        axis.set_title(f"({panel}) {SEASON_LABELS[season]}", loc="left")
        axis.spines[["top", "right"]].set_visible(False)
    axes[0].legend(frameon=False, loc="lower right")
    figure.suptitle("Observed, raw-CMIP6 and QDM ENSO responses", y=0.995, fontsize=9)
    _save(figure, "Paper3_Figure_03_raw_qdm_comparison")


def figure_4() -> None:
    preservation = pd.read_csv(OUTPUT / "qdm_enso_signal_preservation.csv")
    asymmetry = pd.read_csv(OUTPUT / "enso_asymmetry_primary.csv")
    categories = [(metric, phase) for metric in METRIC_LABELS for phase in ("EL_NINO", "LA_NINA")]
    row_labels = [f"{METRIC_LABELS[m]} — {PHASE_LABELS[p]}" for m, p in categories]
    preservation_codes = {
        "REVERSED": -2,
        "ATTENUATED": -1,
        "PRESERVED": 0,
        "AMPLIFIED": 1,
        "INDETERMINATE_RAW_NEAR_ZERO": 2,
        "INSUFFICIENT": 3,
    }
    short = {"REVERSED": "R", "ATTENUATED": "At", "PRESERVED": "P", "AMPLIFIED": "Am", "INDETERMINATE_RAW_NEAR_ZERO": "NZ", "INSUFFICIENT": "—"}
    matrix = np.full((len(categories), 2), np.nan)
    annotations = np.empty((len(categories), 2), dtype=object)
    for column, season in enumerate(["RAINY", "HOT_DRY"]):
        table = preservation[preservation["season_type"] == season].set_index(["metric", "phase"])
        for row, key in enumerate(categories):
            category = table.loc[key, "category"]
            matrix[row, column] = preservation_codes[category]
            annotations[row, column] = short[category]

    asym_columns = [(source, season) for season in ("RAINY", "HOT_DRY") for source in ("OBSERVED", "RAW", "QDM")]
    asym_matrix = np.full((len(METRIC_LABELS), len(asym_columns)), np.nan)
    for row, metric in enumerate(METRIC_LABELS):
        table = asymmetry[asymmetry["metric"] == metric].set_index(["source_type", "season_type"])
        asym_matrix[row] = [table.loc[key, "neutral_centered_asymmetry_pct"] for key in asym_columns]

    figure, axes = plt.subplots(1, 2, figsize=(7.2, 4.3), gridspec_kw={"width_ratios": [0.82, 1.45], "wspace": 0.52})
    preservation_cmap = ListedColormap(["#CC79A7", "#56B4E9", "#009E73", "#E69F00", "#BDBDBD", "#FFFFFF"])
    axes[0].imshow(matrix, aspect="auto", cmap=preservation_cmap, vmin=-2.5, vmax=3.5)
    axes[0].set_xticks([0, 1], ["Rainy", "Hot/dry"])
    axes[0].set_yticks(np.arange(len(categories)), row_labels)
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            axes[0].text(column, row, annotations[row, column], ha="center", va="center", fontsize=7)
    axes[0].set_title("(a) QDM preservation class", loc="left")
    axes[0].tick_params(length=0)
    axes[0].text(
        0,
        -0.17,
        "R reversed; At attenuated; P preserved; Am amplified; NZ raw response <5%",
        transform=axes[0].transAxes,
        fontsize=6.3,
        va="top",
    )

    limit = max(10.0, float(np.nanmax(np.abs(asym_matrix))))
    image = axes[1].imshow(
        asym_matrix,
        aspect="auto",
        cmap="RdBu_r",
        norm=TwoSlopeNorm(vmin=-limit, vcenter=0, vmax=limit),
    )
    axes[1].set_xticks(
        np.arange(len(asym_columns)),
        [f"{season.replace('_', '/')}\n{source.title()}" for source, season in asym_columns],
        rotation=40,
        ha="right",
    )
    axes[1].set_yticks(np.arange(len(METRIC_LABELS)), [METRIC_LABELS[value] for value in METRIC_LABELS])
    for row in range(asym_matrix.shape[0]):
        for column in range(asym_matrix.shape[1]):
            value = asym_matrix[row, column]
            axes[1].text(column, row, f"{value:.0f}", ha="center", va="center", fontsize=6.5, color="black")
    axes[1].set_title("(b) True neutral-centred asymmetry, A$_{La}$ + A$_{El}$ (%)", loc="left")
    axes[1].tick_params(length=0)
    colorbar = figure.colorbar(image, ax=axes[1], fraction=0.047, pad=0.03)
    colorbar.set_label("Asymmetry (%)")
    _save(figure, "Paper3_Figure_04_preservation_asymmetry")


def main() -> None:
    figure_1()
    figure_2()
    figure_3()
    figure_4()
    rows = []
    for number, stem in enumerate(
        [
            "Paper3_Figure_01_ENSO_classification",
            "Paper3_Figure_02_observed_responses",
            "Paper3_Figure_03_raw_qdm_comparison",
            "Paper3_Figure_04_preservation_asymmetry",
        ],
        start=1,
    ):
        for suffix in ("png", "pdf"):
            path = FIGURES / f"{stem}.{suffix}"
            rows.append({"figure": number, "format": suffix, "path": str(path), "bytes": path.stat().st_size})
    pd.DataFrame(rows).to_csv(FIGURES / "Paper3_FIGURE_INDEX.csv", index=False)
    print(f"FIGURES_COMPLETE {FIGURES}")


if __name__ == "__main__":
    main()
