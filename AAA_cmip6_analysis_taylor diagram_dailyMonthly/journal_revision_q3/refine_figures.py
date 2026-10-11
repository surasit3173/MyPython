from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np
import pandas as pd


ROOT = Path("C:/MyPython/AAA_cmip6_analysis_taylor diagram_dailyMonthly")
DATA = ROOT / "cmip6bc_q1_notiers_work" / "cmip6bc" / "data"
RESULTS = ROOT / "qdm_p_np_publication_out_q3_final"
OUT = ROOT / "journal_revision_q3" / "figures_q1"
REVISION2 = ROOT / "journal_revision_q3" / "revision2_analysis"

MM = 1 / 25.4
WIDTH = 160 * MM
FONT = "Palatino Linotype"

INK = "#252525"
MUTED = "#666666"
GRID = "#D6D6D6"
RAW = "#5A5A5A"
CAL = "#0072B2"
VAL = "#D55E00"
NP_A = "#4C9BC4"
NP_M = "#009E73"
P_A = "#E69F00"
P_M = "#CC79A7"
METHOD_COLORS = [RAW, NP_A, NP_M, P_A, P_M]


def style() -> None:
    plt.rcParams.update(
        {
            "font.family": FONT,
            "font.size": 10.5,
            "axes.titlesize": 11.5,
            "axes.labelsize": 10.5,
            "xtick.labelsize": 9.0,
            "ytick.labelsize": 9.0,
            "legend.fontsize": 9.5,
            "axes.edgecolor": INK,
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "xtick.major.width": 0.8,
            "ytick.major.width": 0.8,
            "xtick.major.size": 3,
            "ytick.major.size": 3,
            "axes.grid": True,
            "axes.unicode_minus": False,
            "grid.color": GRID,
            "grid.linewidth": 0.55,
            "grid.alpha": 0.75,
            "grid.linestyle": ":",
            "legend.frameon": False,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
            "savefig.dpi": 600,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.04,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def panel_title(ax, tag: str, title: str) -> None:
    ax.set_title(f"({tag})  {title}", loc="left", fontweight="bold", pad=7)


def save_all(fig: plt.Figure, stem: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{stem}.png", dpi=600)
    fig.savefig(OUT / f"{stem}.tif", dpi=600, pil_kwargs={"compression": "tiff_lzw"})
    fig.savefig(OUT / f"{stem}.pdf")
    plt.close(fig)
    print(f"saved {stem}: PNG/TIFF 600 dpi + vector PDF")


def load_observed() -> pd.DataFrame:
    path = DATA / "Observed_Rain_daily_198101_201412_Prachuap_Khiri_Khan.csv"
    raw = pd.read_csv(path)
    idx = pd.to_datetime(dict(year=raw.YEAR, month=raw.MONTH, day=raw.DAY))
    obs = raw.drop(columns=["YEAR", "MONTH", "DAY"]).apply(pd.to_numeric, errors="coerce")
    obs.index = idx
    return obs.mask(obs < 0).clip(lower=0)


def figure1_framework() -> None:
    fig, ax = plt.subplots(figsize=(WIDTH, WIDTH * 0.48), layout="constrained")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    blue_fill, blue_edge = "#E5F1F8", CAL
    orange_fill, orange_edge = "#FBEBDD", VAL
    gray_fill, gray_edge = "#F2F2F2", "#747474"

    def box(x, y, w, h, title, subtitle, fill, edge):
        patch = FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.35,rounding_size=1.2",
            linewidth=1.15, facecolor=fill, edgecolor=edge, zorder=2
        )
        ax.add_patch(patch)
        ax.text(x + w / 2, y + h * 0.66, title, ha="center", va="center",
                fontsize=11.5, fontweight="bold", color=INK)
        ax.text(x + w / 2, y + h * 0.31, subtitle, ha="center", va="center",
                fontsize=9.8, color=INK, linespacing=1.05)

    def arrow(start, end, color=INK):
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=12,
                                     linewidth=1.15, color=color, zorder=4))

    ax.text(25, 97.5, "CALIBRATION", ha="center", va="top", color=CAL,
            fontsize=10.5, fontweight="bold")
    ax.text(75, 97.5, "INDEPENDENT VALIDATION", ha="center", va="top", color=VAL,
            fontsize=10.5, fontweight="bold")

    box(4, 73, 42, 18, "Observed + CMIP6", "1981-2000", blue_fill, blue_edge)
    box(54, 73, 42, 18, "CMIP6 + withheld observations", "2001-2014", orange_fill, orange_edge)
    box(4, 48, 42, 17, "Estimate transfer functions", "wet-day adjustment + QDM", blue_fill, blue_edge)
    box(54, 48, 42, 17, "Apply frozen functions", "no re-estimation", orange_fill, orange_edge)
    box(20, 25, 60, 14, "Paired evaluation", "raw versus corrected, model x station", gray_fill, gray_edge)
    box(20, 8, 60, 12, "Uncertainty and robustness", "validation-year bootstrap + cap sensitivity", gray_fill, gray_edge)

    arrow((25, 73), (25, 65.5))
    arrow((75, 73), (75, 65.5))
    arrow((46.5, 56.5), (53.5, 56.5), color="#4B4B4B")
    ax.text(50, 60.1, "FREEZE", ha="center", va="bottom", fontsize=8.8,
            fontweight="bold", color=MUTED)
    arrow((25, 48), (39.5, 39.5))
    arrow((75, 48), (60.5, 39.5))
    arrow((50, 25), (50, 20.5))

    ax.add_patch(FancyBboxPatch((10, 0.5), 80, 4.8, boxstyle="round,pad=0.25",
                                linewidth=0, facecolor="#FFF4E8", zorder=1))
    ax.text(50, 2.9, "Validation observations never enter transfer-function estimation.",
            ha="center", va="center", fontsize=9.4, fontweight="bold", color="#8A3A12")
    save_all(fig, "Figure1_framework")


def figure2_observed(obs: pd.DataFrame) -> None:
    cal = obs.loc["1981":"2000"]
    val = obs.loc["2001":"2014"]
    regional = obs.mean(axis=1)

    fig = plt.figure(figsize=(WIDTH, WIDTH * 0.68), layout="constrained")
    gs = fig.add_gridspec(2, 2, height_ratios=[1.02, 0.90], hspace=0.10, wspace=0.10)

    ax = fig.add_subplot(gs[0, 0])
    for frame, color in [(cal, CAL), (val, VAL)]:
        monthly_by_station = frame.resample("MS").sum(min_count=25)
        clim_by_station = monthly_by_station.groupby(monthly_by_station.index.month).mean()
        lower = clim_by_station.quantile(0.25, axis=1)
        upper = clim_by_station.quantile(0.75, axis=1)
        ax.fill_between(clim_by_station.index, lower, upper, color=color, alpha=0.12,
                        linewidth=0, zorder=1)
    for frame, color, label, marker, ls in [
        (regional.loc["1981":"2000"], CAL, "Calibration (1981-2000)", "o", "-"),
        (regional.loc["2001":"2014"], VAL, "Validation (2001-2014)", "s", "--"),
    ]:
        monthly = frame.resample("MS").sum(min_count=25)
        clim = monthly.groupby(monthly.index.month).mean()
        ax.plot(clim.index, clim, color=color, marker=marker, linestyle=ls,
                markersize=4.2, markeredgecolor="white", markeredgewidth=0.55,
                linewidth=1.7, label=label)
    ax.set_xlim(0.7, 12.3)
    ax.set_xticks(range(1, 13))
    ax.set_xlabel("Month")
    ax.set_ylabel("Rainfall (mm/month)")
    panel_title(ax, "a", "Monthly climatology")

    ax = fig.add_subplot(gs[0, 1])
    annual = regional.resample("YS").sum(min_count=300)
    years = annual.index.year.to_numpy()
    colors = [CAL if y <= 2000 else VAL for y in years]
    ax.bar(years, annual.to_numpy(float), width=0.78, color=colors,
           edgecolor="white", linewidth=0.35, zorder=3)
    ax.axvline(2000.5, color=INK, linewidth=1.0, linestyle=(0, (5, 3)))
    ax.set_xlim(1980, 2015)
    ax.set_ylim(bottom=0)
    ax.set_xticks([1981, 1990, 2000, 2010])
    ax.set_xlabel("Year")
    ax.set_ylabel("Annual rainfall (mm)")
    panel_title(ax, "b", "Annual rainfall")

    ax = fig.add_subplot(gs[1, :])
    stations = list(obs.columns)
    wet_cal = np.array([(cal[s] >= 1.0).mean() for s in stations]) * 100
    wet_val = np.array([(val[s] >= 1.0).mean() for s in stations]) * 100
    x = np.arange(len(stations))
    for i in x:
        change_color = VAL if wet_val[i] >= wet_cal[i] else CAL
        ax.plot([i, i], [wet_cal[i], wet_val[i]], color=change_color, lw=1.25, zorder=1)
    ax.scatter(x, wet_cal, s=31, color=CAL, edgecolor="white", linewidth=0.55,
               zorder=3, label="Calibration")
    ax.scatter(x, wet_val, s=31, color=VAL, marker="s", edgecolor="white",
               linewidth=0.55, zorder=3, label="Validation")
    ax.set_xticks(x)
    ax.set_xticklabels(stations, rotation=30, ha="right", fontsize=8.2)
    ax.set_ylabel("Wet-day frequency (%)")
    ax.set_xlabel("Rain-gauge station")
    ax.set_ylim(10, 70)
    panel_title(ax, "c", "Station-level wet-day frequency")
    fig.legend(handles=[
        Line2D([0], [0], color=CAL, marker="o", lw=1.7, markersize=4.2,
               markeredgecolor="white", label="Calibration (1981-2000)"),
        Line2D([0], [0], color=VAL, marker="s", lw=1.7, linestyle="--", markersize=4.2,
               markeredgecolor="white", label="Validation (2001-2014)"),
    ], loc="outside upper center", ncol=2, columnspacing=1.5, handlelength=2.0)
    save_all(fig, "Figure2_observed_periods")


def method_label(name: str) -> str:
    return {
        "raw": "Raw",
        "QDM_NP_annual": "NP annual",
        "QDM_NP_monthly": "NP monthly",
        "QDM_P_annual": "P annual",
        "QDM_P_monthly": "P monthly",
    }[name]


def figure3_method_comparison(metrics: pd.DataFrame) -> None:
    methods = ["raw", "QDM_NP_annual", "QDM_NP_monthly", "QDM_P_annual", "QDM_P_monthly"]
    panels = [
        ("mRMSE", "Monthly RMSE", "RMSE (mm/month)", False),
        ("KS_D", "Distributional distance", "KS statistic D", False),
        ("q99_relbias_pct", "Upper-tail bias", "Absolute q99 relative bias (%)", True),
        ("mKGE", "Monthly KGE", "KGE", False),
    ]
    val = metrics[metrics.period.eq("validation")]
    fig, axes = plt.subplots(2, 2, figsize=(WIDTH, WIDTH * 0.73), layout="constrained")
    for tag, ax, (metric, title, xlabel, absolute) in zip("abcd", axes.ravel(), panels):
        arrays = []
        for method in methods:
            series = pd.to_numeric(val.loc[val.dataset.eq(method), metric], errors="coerce")
            if absolute:
                series = series.abs()
            arrays.append(series.dropna().to_numpy(float))
        raw_mean = float(np.nanmean(arrays[0]))
        bp = ax.boxplot(arrays, orientation="horizontal", patch_artist=True,
                        tick_labels=[method_label(m) for m in methods],
                        whis=(10, 90), showmeans=True, showfliers=True,
                        meanprops={"marker": "D", "markerfacecolor": "white", "markeredgecolor": INK,
                                   "markersize": 3.6, "markeredgewidth": 0.6},
                        flierprops={"marker": "o", "markerfacecolor": "none", "markeredgecolor": MUTED,
                                    "markersize": 2.6, "markeredgewidth": 0.55},
                        medianprops={"color": "white", "linewidth": 1.6},
                        whiskerprops={"color": INK, "linewidth": 0.9},
                        capprops={"color": INK, "linewidth": 0.9})
        for patch, color in zip(bp["boxes"], METHOD_COLORS):
            patch.set_facecolor(color)
            patch.set_alpha(0.88)
            patch.set_edgecolor(INK)
            patch.set_linewidth(0.8)
        ax.axvline(raw_mean, color=RAW, linewidth=0.9, linestyle=(0, (4, 3)),
                   alpha=0.8, zorder=0)
        ax.invert_yaxis()
        ax.grid(axis="y", visible=False)
        ax.set_xlabel(xlabel)
        panel_title(ax, tag, title)
    save_all(fig, "Figure3_method_comparison")


def figure4_improvement_heatmap(summary: pd.DataFrame) -> None:
    methods = ["QDM_NP_annual", "QDM_NP_monthly", "QDM_P_annual", "QDM_P_monthly"]
    metrics = ["PBIAS", "KS_D", "q99_relbias_pct", "mRMSE", "mKGE", "mr"]
    labels = ["Absolute PBIAS", "KS statistic D", "Absolute q99 bias",
              "Monthly RMSE", "Monthly KGE", "Monthly correlation"]
    subset = summary[summary.period.eq("validation") & summary.metric.isin(metrics)]
    matrix = subset.pivot(index="metric", columns="method", values="pct_improved").reindex(metrics)[methods]

    cmap = LinearSegmentedColormap.from_list("improvement", ["#C75B39", "#FAFAFA", "#2166AC"])
    norm = TwoSlopeNorm(vmin=0, vcenter=50, vmax=100)
    fig, ax = plt.subplots(figsize=(WIDTH, WIDTH * 0.54), layout="constrained")
    im = ax.imshow(matrix.to_numpy(float), cmap=cmap, norm=norm, aspect="auto")
    ax.set_xticks(np.arange(4), ["NP\nannual", "NP\nmonthly", "P\nannual", "P\nmonthly"])
    ax.set_yticks(np.arange(6), labels)
    ax.tick_params(axis="both", length=0)
    ax.grid(False)
    ax.set_xticks(np.arange(-0.5, 4, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, 6, 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.5)
    ax.tick_params(which="minor", bottom=False, left=False)
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = float(matrix.iloc[i, j])
            color = "white" if value <= 20 or value >= 76 else INK
            ax.text(j, i, f"{value:.0f}%", ha="center", va="center",
                    color=color, fontsize=10.2, fontweight="bold")
    ax.axvline(1.5, color=INK, linewidth=1.5)
    ax.text(0.5, -0.78, "NON-PARAMETRIC", ha="center", va="center",
            fontsize=9.7, fontweight="bold", color=NP_M, clip_on=False)
    ax.text(2.5, -0.78, "PARAMETRIC", ha="center", va="center",
            fontsize=9.7, fontweight="bold", color=VAL, clip_on=False)
    cbar = fig.colorbar(im, ax=ax, orientation="horizontal", fraction=0.075, pad=0.16,
                        aspect=32, ticks=[0, 25, 50, 75, 100])
    cbar.set_label("Paired combinations with a favorable point change (%)")
    cbar.outline.set_linewidth(0.7)
    save_all(fig, "Figure4_improvement_heatmap")


def figure5_station_spatial() -> None:
    metrics = pd.read_csv(RESULTS / "station_metrics.csv", dtype={"station": str})
    validation = metrics[metrics.period.eq("validation")]
    raw = validation[validation.dataset.eq("raw")][["model", "station", "mKGE"]]
    np_monthly = validation[validation.dataset.eq("QDM_NP_monthly")][["model", "station", "mKGE"]]
    pairs = np_monthly.merge(raw, on=["model", "station"], suffixes=("_corrected", "_raw"))
    pairs["delta"] = pairs.mKGE_corrected - pairs.mKGE_raw
    model_order = ["ACCESS-ESM1-5", "CESM2", "CanESM5", "EC-Earth3", "MIROC6"]
    station_order = ["500202", "500301", "500008", "500001", "500009", "500003",
                     "500007", "500201", "500006", "500005", "500004", "500002"]
    heat = pairs.pivot(index="station", columns="model", values="delta").reindex(index=station_order, columns=model_order)

    fig = plt.figure(figsize=(WIDTH, WIDTH * 0.64), layout="constrained")
    gs = fig.add_gridspec(1, 2, width_ratios=[1.15, 1.20], wspace=0.18)

    ax = fig.add_subplot(gs[0, 0])
    cmap = LinearSegmentedColormap.from_list("skill_change", ["#C75B39", "#F7F7F7", "#2166AC"])
    vmax = max(0.30, float(np.nanmax(np.abs(heat.to_numpy(float)))))
    norm = TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax)
    im = ax.imshow(heat.to_numpy(float), cmap=cmap, norm=norm, aspect="auto")
    ax.set_xticks(np.arange(len(model_order)), ["ACCESS", "CESM2", "CanESM5", "EC3", "MIROC6"], rotation=35, ha="right")
    ax.set_yticks(np.arange(len(station_order)), station_order)
    ax.tick_params(axis="both", length=0, labelsize=7.3)
    ax.set_xlabel("CMIP6 model")
    ax.set_ylabel("Rain-gauge station")
    ax.set_xticks(np.arange(-0.5, len(model_order), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(station_order), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=0.9)
    ax.tick_params(which="minor", bottom=False, left=False)
    for i in range(heat.shape[0]):
        for j in range(heat.shape[1]):
            value = heat.iloc[i, j]
            ax.text(j, i, f"{value:+.2f}", ha="center", va="center", fontsize=6.0,
                    color="white" if abs(value) > 0.18 else INK)
    panel_title(ax, "a", "NP-monthly KGE change by model")
    cbar = fig.colorbar(im, ax=ax, orientation="horizontal", fraction=0.055, pad=0.16,
                        ticks=[-0.3, 0.0, 0.3])
    cbar.set_label("Corrected minus raw KGE")
    cbar.outline.set_linewidth(0.7)

    ax = fig.add_subplot(gs[0, 1])
    station_summary = pd.read_csv(REVISION2 / "station_spatial_summary.csv", dtype={"station": str})
    monthly = station_summary[station_summary.method.isin(["QDM_NP_monthly", "QDM_P_monthly"])].copy()
    pivot = monthly.pivot(index="station", columns="method", values="delta_mKGE")
    y = np.arange(len(station_order))
    np_values = pivot.loc[station_order, "QDM_NP_monthly"].to_numpy(float)
    p_values = pivot.loc[station_order, "QDM_P_monthly"].to_numpy(float)
    for yi, left, right in zip(y, np_values, p_values):
        ax.plot([left, right], [yi, yi], color="#B5B5B5", linewidth=1.0, zorder=1)
    ax.scatter(np_values, y, color=NP_M, edgecolor="white", linewidth=0.55,
               s=34, label="NP monthly", zorder=3)
    ax.scatter(p_values, y, color=P_M, marker="s", edgecolor="white",
               linewidth=0.55, s=34, label="P monthly", zorder=3)
    ax.axvline(0, color=INK, linewidth=0.9)
    ax.set_yticks(y, station_order)
    ax.invert_yaxis()
    ax.set_xlim(-0.12, 0.35)
    ax.set_xlabel("Mean corrected-minus-raw monthly KGE")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right")
    panel_title(ax, "b", "Station KGE response")
    save_all(fig, "Figure5_station_spatial_response")


def figure6_threshold_sensitivity() -> None:
    frame = pd.read_csv(REVISION2 / "wet_threshold_sensitivity.csv")
    frame = frame[frame.method.isin(["QDM_NP_monthly", "QDM_P_monthly"])].copy()
    threshold_map = {"0.1 mm": 0.1, "0.5 mm": 0.5, "1.0 mm (primary)": 1.0}
    frame["threshold"] = frame.scenario.map(threshold_map)
    panels = [
        ("mKGE", "Monthly KGE", "KGE", True),
        ("mRMSE", "Monthly RMSE", "RMSE (mm/month)", False),
        ("q99_relbias_pct", "Upper-tail bias", "Absolute q99 bias (%)", False),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(WIDTH, WIDTH * 0.34), layout="constrained")
    for tag, ax, (metric, title, ylabel, higher_better) in zip("abc", axes, panels):
        sub = frame[frame.metric.eq(metric)]
        x_values = np.array([0.1, 0.5, 1.0])
        raw_means, raw_lower, raw_upper = [], [], []
        roots = {"0.1 mm": REVISION2 / "wet_threshold_0.1",
                 "0.5 mm": REVISION2 / "wet_threshold_0.5",
                 "1.0 mm (primary)": RESULTS}
        for scenario in threshold_map:
            station_metrics = pd.read_csv(roots[scenario] / "station_metrics.csv")
            raw_values = station_metrics[(station_metrics.period == "validation") & (station_metrics.dataset == "raw")][metric].astype(float)
            if metric == "q99_relbias_pct":
                raw_values = raw_values.abs()
            raw_means.append(raw_values.mean())
            raw_lower.append(raw_values.quantile(0.25))
            raw_upper.append(raw_values.quantile(0.75))
        ax.fill_between(x_values, raw_lower, raw_upper, color=RAW, alpha=0.08, linewidth=0)
        ax.plot(x_values, raw_means, color=RAW, linestyle=(0, (4, 3)), linewidth=0.9,
                label="Raw mean")
        for method, color, marker, label in [
            ("QDM_NP_monthly", NP_M, "o", "NP monthly"),
            ("QDM_P_monthly", P_M, "s", "P monthly"),
        ]:
            values = sub[sub.method.eq(method)].sort_values("threshold")
            lows, highs = [], []
            for scenario in threshold_map:
                station_metrics = pd.read_csv(roots[scenario] / "station_metrics.csv")
                corrected = station_metrics[(station_metrics.period == "validation") & (station_metrics.dataset == method)][metric].astype(float)
                if metric == "q99_relbias_pct":
                    corrected = corrected.abs()
                lows.append(corrected.quantile(0.25))
                highs.append(corrected.quantile(0.75))
            ax.fill_between(x_values, lows, highs, color=color, alpha=0.10, linewidth=0)
            ax.plot(values.threshold, values.corrected_mean, color=color, marker=marker,
                    linewidth=1.65, markersize=4.8, markeredgecolor="white",
                    markeredgewidth=0.6, label=label)
        ax.axvline(1.0, color=INK, linewidth=0.85, linestyle=(0, (4, 3)))
        ax.set_xticks([0.1, 0.5, 1.0])
        ax.set_xlabel("Wet-day threshold (mm/day)")
        ax.set_ylabel(ylabel)
        panel_title(ax, tag, title)
    axes[0].legend(loc="lower right")
    save_all(fig, "Figure6_wet_threshold_sensitivity")


def main() -> None:
    style()
    obs = load_observed()
    metrics = pd.read_csv(RESULTS / "station_metrics.csv")
    summary = pd.read_csv(RESULTS / "summary.csv")
    figure1_framework()
    figure2_observed(obs)
    figure3_method_comparison(metrics)
    figure4_improvement_heatmap(summary)
    figure5_station_spatial()
    figure6_threshold_sensitivity()


if __name__ == "__main__":
    main()
