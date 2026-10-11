"""
figures.py
==========
Publication-quality figures (600 dpi PNG + vector PDF, colorblind-safe Okabe-Ito,
Times New Roman with graceful fallback, thin grid, fully-labelled axes).
"""
from __future__ import annotations
import logging
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

from . import config as C

log = logging.getLogger("figures")
MONTH_ABBR = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]


def _setup_style():
    fams = {f.name for f in fm.fontManager.ttflist}
    family = C.FONT_FAMILY if C.FONT_FAMILY in fams else "DejaVu Serif"
    if family != C.FONT_FAMILY:
        log.warning("Font '%s' unavailable; using '%s'", C.FONT_FAMILY, family)
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": [family],
        "font.size": 11,
        "axes.titlesize": 12,
        "axes.labelsize": 11,
        "axes.linewidth": 0.8,
        "axes.grid": True,
        "grid.linewidth": 0.4,
        "grid.alpha": 0.4,
        "grid.color": "#bbbbbb",
        "legend.frameon": False,
        "figure.dpi": 120,
        "savefig.dpi": C.DPI,
        "savefig.bbox": "tight",
    })


def _save(fig, name):
    for ext in ("png", "pdf"):
        fig.savefig(C.FIG / f"{name}.{ext}", dpi=C.DPI)
    plt.close(fig)
    log.info("saved %s.{png,pdf}", name)


# --------------------------------------------------------------------------- #
def fig01_climatology(monthly: pd.DataFrame):
    g = monthly.groupby("month")["rain_mm"]
    m, sd = g.mean(), g.std(ddof=1)
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    months = np.arange(1, 13)
    ax.bar(months, m.reindex(months).values, yerr=sd.reindex(months).values,
           color=C.C_ACCENT, edgecolor="black", linewidth=0.6, capsize=3,
           error_kw=dict(linewidth=0.8))
    ax.set_xticks(months)
    ax.set_xticklabels(["J","F","M","A","M","J","J","A","S","O","N","D"])
    ax.set_xlabel("Month")
    ax.set_ylabel("Mean monthly rainfall (mm)")
    ax.set_title("Monthly Rainfall Climatology (1981-2014)")
    _save(fig, "FIGURE_01_monthly_climatology")


def fig02_annual_series(annual: pd.Series):
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.plot(annual.index, annual.values, "-o", color=C.C_MAIN, ms=3, lw=1.0)
    z = np.polyfit(annual.index, annual.values, 1)
    ax.plot(annual.index, np.polyval(z, annual.index), "--",
            color=C.C_ELNINO, lw=1.2, label=f"OLS trend ({z[0]:+.2f} mm/yr)")
    ax.set_xlabel("Year"); ax.set_ylabel("Annual rainfall (mm)")
    ax.set_title("Annual Areal Rainfall - Prachuap Khiri Khan")
    ax.legend()
    _save(fig, "FIGURE_02_annual_timeseries")


def fig03_nino(nino_monthly: pd.DataFrame):
    d = nino_monthly.dropna(subset=["Nino34"]).copy()
    d["t"] = pd.to_datetime(dict(year=d.year, month=d.month, day=1))
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.plot(d["t"], d["Nino34"], color=C.C_MAIN, lw=0.8)
    ax.axhline(C.ONI_ELNINO, color=C.C_ELNINO, lw=0.8, ls="--")
    ax.axhline(C.ONI_LANINA, color=C.C_LANINA, lw=0.8, ls="--")
    ax.fill_between(d["t"], C.ONI_ELNINO, d["Nino34"],
                    where=d["Nino34"] >= C.ONI_ELNINO, color=C.C_ELNINO, alpha=.5)
    ax.fill_between(d["t"], C.ONI_LANINA, d["Nino34"],
                    where=d["Nino34"] <= C.ONI_LANINA, color=C.C_LANINA, alpha=.5)
    ax.set_xlabel("Year"); ax.set_ylabel("Nino-3.4 SST anomaly (degC)")
    ax.set_title("Nino-3.4 SST Anomaly")
    _save(fig, "FIGURE_03_nino34_timeseries")


def fig_scatter(x: pd.Series, y: pd.Series, xl, yl, title, name):
    d = pd.concat([x.rename("x"), y.rename("y")], axis=1, join="inner").dropna()
    fig, ax = plt.subplots(figsize=(5.2, 4.6))
    ax.scatter(d["x"], d["y"], s=28, color=C.C_ACCENT, edgecolor="black", lw=.5)
    if len(d) > 2:
        z = np.polyfit(d["x"], d["y"], 1)
        xs = np.linspace(d["x"].min(), d["x"].max(), 50)
        ax.plot(xs, np.polyval(z, xs), "--", color=C.C_ELNINO, lw=1.2)
    ax.set_xlabel(xl); ax.set_ylabel(yl); ax.set_title(title)
    _save(fig, name)


def fig06_lag(lag_tab: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    colors = [C.C_ELNINO if s else C.C_NEUTRAL for s in lag_tab["significant"]]
    ax.bar(lag_tab["lag_months"], lag_tab["r"], color=colors,
           edgecolor="black", lw=.5)
    ax.axhline(0, color="black", lw=.8)
    ax.set_xlabel("Lag (months, Nino-3.4 leading)")
    ax.set_ylabel("Pearson r")
    ax.set_title("Lag Correlation: Monthly Rainfall vs Nino-3.4")
    _save(fig, "FIGURE_06_lag_correlation")


def fig07_boxplot(series_by_var: dict, phase_by_year: pd.Series):
    order = ["La Nina", "Neutral", "El Nino"]
    cmap = {"La Nina": C.C_LANINA, "Neutral": C.C_NEUTRAL, "El Nino": C.C_ELNINO}
    fig, axes = plt.subplots(1, len(series_by_var),
                             figsize=(4.2 * len(series_by_var), 4.2), sharey=False)
    if len(series_by_var) == 1:
        axes = [axes]
    for ax, (var, s) in zip(axes, series_by_var.items()):
        d = pd.concat([s.rename("v"), phase_by_year.rename("p")],
                      axis=1, join="inner").dropna()
        data = [d.loc[d["p"] == ph, "v"].values for ph in order]
        bp = ax.boxplot(data, labels=order, patch_artist=True, widths=.6)
        for patch, ph in zip(bp["boxes"], order):
            patch.set_facecolor(cmap[ph]); patch.set_alpha(.7)
        for med in bp["medians"]:
            med.set_color("black")
        ax.set_title(var); ax.set_ylabel("Rainfall (mm)")
        ax.tick_params(axis="x", rotation=15)
    fig.suptitle("ENSO Composite Rainfall Distribution")
    _save(fig, "FIGURE_07_enso_boxplot")


def fig_q1_dual_axis_climatology_shift(
    climatology_df: pd.DataFrame,
    name="Q1_FIGURE_01_dual_axis_climatology_shift",
    out_dir=None,
):
    """12-station dual-axis climatology figure for seasonality-shift review."""
    out_dir = out_dir or C.Q1
    stations = sorted(climatology_df["station"].unique())
    periods = list(dict.fromkeys(climatology_df["period"]))
    if len(periods) != 2:
        raise ValueError("Expected exactly two climatology periods for Q1 Figure 1.")

    fig, axes = plt.subplots(3, 4, figsize=(16.5, 11.0), sharex=True)
    axes = axes.ravel()
    months = np.arange(1, 13)
    width = 0.34
    bar_colors = ["#CAD8E6", "#4E79A7"]
    line_colors = ["#4E79A7", "#D55E00"]
    legend_handles = None

    for ax, station in zip(axes, stations):
        sub = climatology_df[climatology_df["station"] == station]
        early = sub[sub["period"] == periods[0]].set_index("month").reindex(months)
        late = sub[sub["period"] == periods[1]].set_index("month").reindex(months)
        ax2 = ax.twinx()
        bars1 = ax.bar(months - width / 2, early["mean_rain_mm"], width=width,
                       color=bar_colors[0], edgecolor="#333333", linewidth=0.5,
                       label=f"{periods[0]} mean monthly rainfall")
        bars2 = ax.bar(months + width / 2, late["mean_rain_mm"], width=width,
                       color=bar_colors[1], edgecolor="#333333", linewidth=0.5,
                       alpha=0.9, label=f"{periods[1]} mean monthly rainfall")
        line1, = ax2.plot(months, early["cumulative_pct"], color=line_colors[0],
                          lw=1.4, ls="--", marker="o", ms=2.8,
                          label=f"{periods[0]} cumulative %")
        line2, = ax2.plot(months, late["cumulative_pct"], color=line_colors[1],
                          lw=1.6, ls="-", marker="o", ms=2.8,
                          label=f"{periods[1]} cumulative %")
        ax2.set_ylim(0, 100)
        ax2.grid(False)
        peak1 = early["peak_month"].dropna()
        peak2 = late["peak_month"].dropna()
        peak_text = ""
        if not peak1.empty and not peak2.empty:
            m1 = MONTH_ABBR[int(peak1.iloc[0]) - 1]
            m2 = MONTH_ABBR[int(peak2.iloc[0]) - 1]
            peak_text = f"Peak {m1} -> {m2}"
        ax.set_title(f"Station {int(station)}", fontsize=11)
        if peak_text:
            ax.text(0.03, 0.94, peak_text, transform=ax.transAxes,
                    ha="left", va="top", fontsize=8,
                    bbox=dict(boxstyle="round", fc="white", ec="#cccccc",
                              alpha=0.85))
        ax.set_xticks(months)
        ax.set_xticklabels(MONTH_ABBR)
        if station in stations[::4]:
            ax.set_ylabel("Mean monthly rainfall (mm)")
        if station in stations[3::4]:
            ax2.set_ylabel("Cumulative rainfall (%)")
        if legend_handles is None:
            legend_handles = [bars1, bars2, line1, line2]

    for ax in axes[len(stations):]:
        ax.axis("off")

    fig.legend(legend_handles,
               [f"{periods[0]} mean monthly rainfall",
                f"{periods[1]} mean monthly rainfall",
                f"{periods[0]} cumulative %",
                f"{periods[1]} cumulative %"],
               loc="lower center", ncol=2, fontsize=9, bbox_to_anchor=(0.5, 0.02))
    fig.suptitle("Dual-Axis Climatology and Cumulative Percentage Shift by Station",
                 fontsize=14)
    fig.tight_layout(rect=(0, 0.06, 1, 0.96))
    _save_to(fig, name, out_dir)


def fig_q1_methodological_contrast(
    contrast: dict,
    name="Q1_FIGURE_02_methodological_contrast_station_500003",
    out_dir=None,
):
    """Original MK vs TFPW-MK contrast for a station-level case study."""
    out_dir = out_dir or C.Q1
    obs = contrast["observed"].copy()
    tfpw = contrast["tfpw"].copy()
    diag = contrast["diagnostics"]
    raw = diag.original_result
    tf = diag.tfpw_result

    fig, axes = plt.subplots(1, 2, figsize=(14.2, 5.1))

    raw_years = obs["year"].to_numpy(dtype=float)
    raw_t = raw_years - raw_years.min()
    raw_line, raw_low, raw_high = _sen_lines_median_anchor(
        obs["rain_mm"].to_numpy(dtype=float), raw_t,
        raw.sens_slope, raw.sens_slope_lcl, raw.sens_slope_ucl)
    axes[0].plot(raw_years, obs["rain_mm"], "-o", color=C.C_MAIN, ms=3, lw=1.0)
    axes[0].plot(raw_years, raw_line, "-", color="#8C2D04", lw=1.6)
    axes[0].fill_between(raw_years, raw_low, raw_high, color="#8C2D04", alpha=0.14)
    axes[0].set_title("Original MK on observed wet-season series")
    axes[0].set_xlabel("Year")
    axes[0].set_ylabel("Wet-season rainfall (mm)")
    axes[0].text(0.03, 0.97,
                 f"p = {raw.p_value:.3f}\nZ = {raw.z:.2f}\nSen = {raw.sens_slope:+.2f} mm/yr",
                 transform=axes[0].transAxes, ha="left", va="top", fontsize=8,
                 bbox=dict(boxstyle="round", fc="white", ec="#cccccc", alpha=0.9))

    tf_years = tfpw["year"].to_numpy(dtype=float)
    tf_t = tf_years - tf_years.min()
    tf_line, tf_low, tf_high = _sen_lines_median_anchor(
        tfpw["trend_restored_mm"].to_numpy(dtype=float), tf_t,
        tf.sens_slope, tf.sens_slope_lcl, tf.sens_slope_ucl)
    axes[1].plot(tf_years, tfpw["trend_restored_mm"], "-o",
                 color=C.C_ACCENT, ms=3, lw=1.0)
    axes[1].plot(tf_years, tf_line, "-", color=C.C_ELNINO, lw=1.6)
    axes[1].fill_between(tf_years, tf_low, tf_high, color=C.C_ELNINO, alpha=0.14)
    axr = axes[1].twinx()
    axr.bar(tf_years, tfpw["residual_mm"], width=0.75, color="#BDBDBD",
            alpha=0.35, edgecolor="none")
    axr.axhline(0, color="#7F7F7F", lw=0.8, ls=":")
    axr.set_ylabel("Residual after AR(1) removal (mm)")
    axr.grid(False)
    axes[1].set_title("TFPW-MK trend-restored series with residuals")
    axes[1].set_xlabel("Year")
    axes[1].set_ylabel("Trend-restored rainfall (mm)")
    axes[1].text(
        0.03, 0.97,
        (f"p = {tf.p_value:.3f}\nZ = {tf.z:.2f}\n"
         f"r1 = {diag.lag1_autocorr:.3f} (crit {diag.lag1_critical:.3f})\n"
         f"Pre-whitening: {'applied' if diag.prewhitening_applied else 'skipped'}"),
        transform=axes[1].transAxes, ha="left", va="top", fontsize=8,
        bbox=dict(boxstyle="round", fc="white", ec="#cccccc", alpha=0.9),
    )

    fig.suptitle(
        f"Methodological Contrast for Station {contrast['station']} ({contrast['timescale']} season)",
        fontsize=13,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    _save_to(fig, name, out_dir)


def _sen_lines_median_anchor(values, t, slope, lcl=None, ucl=None):
    """Construct Sen trend lines for plotting around a common median anchor.

    This is a graphical construction only.  It avoids mixing an intercept
    estimated on a transformed TFPW time origin with a plotting axis that
    starts at zero.  The statistical slope and its rank-based CI are unchanged.
    """
    values = np.asarray(values, dtype=float)
    t = np.asarray(t, dtype=float)
    t_med = float(np.median(t))
    x_med = float(np.median(values))
    center = x_med + float(slope) * (t - t_med)
    lower = None if lcl is None else x_med + float(lcl) * (t - t_med)
    upper = None if ucl is None else x_med + float(ucl) * (t - t_med)
    if lower is not None and upper is not None:
        lo = np.minimum(lower, upper)
        hi = np.maximum(lower, upper)
        lower, upper = lo, hi
    return center, lower, upper


def fig_trend(series: pd.Series, slope, intercept, lcl, ucl, title, name):
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    yrs = series.index.values.astype(float)
    t = yrs - yrs.min()
    ax.plot(yrs, series.values, "-o", color=C.C_MAIN, ms=3, lw=1.0,
            label="Observed")
    line, lower, upper = _sen_lines_median_anchor(
        series.values, t, slope, lcl, ucl)
    ax.plot(yrs, line, "-", color=C.C_ELNINO, lw=1.4,
            label=f"Sen slope {slope:+.2f} mm/yr")
    ax.fill_between(yrs, lower, upper,
                    color=C.C_ELNINO, alpha=.15, label="Slope 95% CI envelope")
    ax.set_xlabel("Year"); ax.set_ylabel("Rainfall (mm)"); ax.set_title(title)
    ax.legend()
    _save(fig, name)


def fig_r2_comparison(model_tab: pd.DataFrame):
    """Grouped bar of adjusted R2 per target for each predictor model."""
    targets = list(dict.fromkeys(model_tab["target"]))
    models = list(dict.fromkeys(model_tab["model"]))
    cmap = {models[0]: C.C_ELNINO}
    if len(models) > 1:
        cmap[models[1]] = C.C_LANINA
    if len(models) > 2:
        cmap[models[2]] = C.C_ACCENT
    x = np.arange(len(targets))
    w = 0.8 / max(len(models), 1)
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for i, mdl in enumerate(models):
        vals = [model_tab[(model_tab.target == t) & (model_tab.model == mdl)]
                ["adj_R2"].iloc[0] if not model_tab[
                    (model_tab.target == t) & (model_tab.model == mdl)].empty
                else np.nan for t in targets]
        ax.bar(x + i * w, vals, w, label=mdl,
               color=cmap.get(mdl, C.C_NEUTRAL), edgecolor="black", lw=.5)
    ax.set_xticks(x + w * (len(models) - 1) / 2)
    ax.set_xticklabels(targets)
    ax.set_ylabel("Adjusted $R^2$")
    ax.set_title("Variance Explained: Nino-3.4 vs DMI vs Combined")
    ax.legend(frameon=False, fontsize=8)
    _save(fig, "FIGURE_12_r2_comparison")


def _station_colors(stations):
    """Distinct colours for up to 12 stations (Okabe-Ito extended + tab)."""
    base = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9",
            "#F0E442", "#000000", "#999999", "#7F3C8D", "#11A579", "#3969AC"]
    return {s: base[i % len(base)] for i, s in enumerate(stations)}


def _taylor_panel(fig, rect, stats_df, title, smax, colors):
    """One Taylor diagram panel (normalised std: reference at radius 1)."""
    from mpl_toolkits.axisartist import floating_axes
    from mpl_toolkits.axisartist.grid_finder import FixedLocator, DictFormatter
    from matplotlib.projections import PolarAxes

    tr = PolarAxes.PolarTransform()
    rlocs = np.array([0, 0.2, 0.4, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0])
    tlocs = np.arccos(rlocs)
    gl1 = FixedLocator(tlocs)
    tf1 = DictFormatter({t: f"{r:g}" for t, r in zip(tlocs, rlocs)})
    ghelper = floating_axes.GridHelperCurveLinear(
        tr, extremes=(0, np.pi / 2, 0, smax),
        grid_locator1=gl1, tick_formatter1=tf1)
    ax = floating_axes.FloatingSubplot(fig, rect, grid_helper=ghelper)
    fig.add_subplot(ax)

    ax.axis["top"].set_axis_direction("bottom")
    ax.axis["top"].toggle(ticklabels=True, label=True)
    ax.axis["top"].major_ticklabels.set_axis_direction("top")
    ax.axis["top"].label.set_axis_direction("top")
    ax.axis["top"].label.set_text("Correlation")
    ax.axis["left"].set_axis_direction("bottom")
    ax.axis["left"].label.set_text("Std. dev. ratio")
    ax.axis["right"].set_axis_direction("top")
    ax.axis["right"].toggle(ticklabels=True)
    ax.axis["right"].major_ticklabels.set_axis_direction("left")
    ax.axis["bottom"].set_visible(False)
    ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.6)
    ax.set_title(title, pad=18)

    aux = ax.get_aux_axes(tr)
    # RMS-difference contours centred on the reference (r=1, theta=0)
    rs, ts = np.meshgrid(np.linspace(0, smax, 120), np.linspace(0, np.pi / 2, 120))
    rms = np.sqrt(1 + rs ** 2 - 2 * rs * np.cos(ts))
    cs = aux.contour(ts, rs, rms, levels=5, colors="#888888",
                     linewidths=0.6, linestyles="--")
    aux.clabel(cs, inline=True, fontsize=6, fmt="%.1f")
    # reference point (areal mean)
    aux.plot(0, 1.0, "k*", ms=12, label="Areal mean (ref.)", zorder=5)
    # stations
    for _, row in stats_df.iterrows():
        aux.plot(np.arccos(row["corr"]), row["std_ratio"], "o", ms=6,
                 color=colors[row["station"]], mec="black", mew=0.4,
                 label=str(int(row["station"])), zorder=4)
    return ax, aux


def fig_taylor(taylor_df: pd.DataFrame, name="FIGURE_13_taylor_diagram"):
    """3-panel Taylor diagram (Annual / Wet / Dry): every gauge vs the areal
    mean, so spatial coherence of the rainfall signal is visible per timescale."""
    order = ["Annual", "Wet", "Dry"]
    stations = sorted(taylor_df["station"].unique())
    colors = _station_colors(stations)
    smax = float(min(max(taylor_df["std_ratio"].max() * 1.15, 1.25), 2.0))
    fig = plt.figure(figsize=(15, 5.4))
    last_aux = None
    for i, var in enumerate(order):
        sub = taylor_df[taylor_df["timescale"] == var]
        if sub.empty:
            continue
        _, last_aux = _taylor_panel(fig, int(f"13{i+1}"), sub, var, smax, colors)
    # single shared legend (stations + reference)
    handles, labels = last_aux.get_legend_handles_labels()
    fig.legend(handles, labels, loc="center right", fontsize=8,
               title="Gauge", ncol=1, bbox_to_anchor=(1.0, 0.5))
    fig.suptitle("Taylor Diagram — Station vs Areal-Mean Rainfall by Timescale",
                 fontsize=13)
    fig.tight_layout(rect=(0, 0, 0.9, 0.96))
    _save(fig, name)


def fig_per_station_trend(trend_df: pd.DataFrame,
                          name="FIGURE_14_per_station_trend_forest"):
    """Forest plot of Sen's slope (+/-95% CI) per station for each timescale.
    Significant trends (CI excluding zero) are highlighted."""
    order = ["Annual", "Wet", "Dry"]
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 5.2), sharey=True)
    for ax, var in zip(axes, order):
        sub = trend_df[trend_df["timescale"] == var].copy()
        sub = sub.sort_values("station").reset_index(drop=True)
        y = np.arange(len(sub))
        for yi, (_, r) in zip(y, sub.iterrows()):
            sig = r["significant"]
            col = C.C_ELNINO if sig else C.C_NEUTRAL
            ax.plot([r["ci95_low"], r["ci95_high"]], [yi, yi], "-",
                    color=col, lw=1.6 if sig else 1.0, alpha=0.9)
            ax.plot(r["sens_slope_mm_yr"], yi, "o", ms=6, color=col,
                    mec="black", mew=0.4)
        ax.axvline(0, color="black", lw=0.9, ls="--")
        ax.set_title(var)
        ax.set_xlabel("Sen's slope (mm yr$^{-1}$)")
        if ax is axes[0]:
            ax.set_yticks(y)
            ax.set_yticklabels([str(int(s)) for s in sub["station"]])
            ax.set_ylabel("Gauge")
    from matplotlib.lines import Line2D
    leg = [Line2D([0], [0], marker="o", color=C.C_ELNINO, lw=1.6,
                  label="Significant (p<0.05)", mec="black"),
           Line2D([0], [0], marker="o", color=C.C_NEUTRAL, lw=1.0,
                  label="Non-significant", mec="black")]
    fig.legend(handles=leg, loc="upper center", ncol=2, fontsize=9,
               bbox_to_anchor=(0.5, 0.04))
    fig.suptitle("Per-Station Rainfall Trend (TFPW-MK / Sen's slope, 95% CI)",
                 fontsize=13)
    fig.tight_layout(rect=(0, 0.06, 1, 0.96))
    _save(fig, name)


def fig_per_station_enso_corr(corr_df: pd.DataFrame,
                              name="FIGURE_15_per_station_enso_corr"):
    """Heatmap of station x timescale correlation with Nino-3.4; significant
    cells (p<0.05) are marked with an asterisk."""
    order = ["Annual", "Wet", "Dry"]
    stations = sorted(corr_df["station"].unique())
    M = np.full((len(stations), len(order)), np.nan)
    S = np.zeros_like(M, dtype=bool)
    for i, s in enumerate(stations):
        for j, v in enumerate(order):
            row = corr_df[(corr_df.station == s) & (corr_df.timescale == v)]
            if not row.empty:
                M[i, j] = row["r"].iloc[0]
                S[i, j] = bool(row["significant"].iloc[0])
    fig, ax = plt.subplots(figsize=(5.6, 7.2))
    vmax = np.nanmax(np.abs(M)) if np.isfinite(M).any() else 1.0
    im = ax.imshow(M, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_xticks(range(len(order))); ax.set_xticklabels(order)
    ax.set_yticks(range(len(stations)))
    ax.set_yticklabels([str(int(s)) for s in stations])
    ax.set_ylabel("Gauge"); ax.set_xlabel("Timescale")
    for i in range(len(stations)):
        for j in range(len(order)):
            if np.isfinite(M[i, j]):
                txt = f"{M[i, j]:.2f}" + ("*" if S[i, j] else "")
                ax.text(j, i, txt, ha="center", va="center", fontsize=8,
                        color="black")
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cb.set_label("Pearson r (rainfall vs Niño-3.4)")
    ax.set_title("Station–ENSO Correlation\n(* = significant, p<0.05)",
                 fontsize=12)
    _save(fig, name)


def fig_significant_trends(ps: dict, tfpw_detail: pd.DataFrame,
                           comparison: pd.DataFrame,
                           name="FIGURE_16_significant_station_trends"):
    """Small-multiple time series for every station x timescale that is
    significant under the primary TFPW-MK test, with the Sen slope line, its
    95% CI band, and all three methods' p-values annotated."""
    sig = tfpw_detail[tfpw_detail["significant"]].copy()
    sig = sig.sort_values(["timescale", "station"]).reset_index(drop=True)
    if sig.empty:
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.axis("off")
        ax.text(0.5, 0.5, "No station-timescale trend significant at "
                "alpha=0.05 (TFPW-MK).", ha="center", va="center")
        _save(fig, name)
        return
    tcol = {"Annual": C.C_MAIN, "Wet": C.C_LANINA, "Dry": C.C_ELNINO}
    n = len(sig)
    ncol = 3 if n >= 3 else n
    nrow = int(np.ceil(n / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(4.7 * ncol, 3.3 * nrow),
                             squeeze=False)
    comp_idx = comparison.set_index(["station", "timescale"])
    for k, (_, r) in enumerate(sig.iterrows()):
        ax = axes[k // ncol][k % ncol]
        s = ps[r["station"]][r["timescale"]].dropna().astype(float)
        yrs = s.index.values.astype(float)
        t = yrs - yrs.min()
        col = tcol.get(r["timescale"], C.C_MAIN)
        ax.plot(yrs, s.values, "-o", color=col, ms=3, lw=1.0, label="Observed")
        line, lower, upper = _sen_lines_median_anchor(
            s.values, t, r["sens_slope_mm_yr"], r["ci95_low"], r["ci95_high"])
        ax.plot(yrs, line, "-", color=C.C_ELNINO, lw=1.6,
                label=f"Sen {r['sens_slope_mm_yr']:+.2f} mm/yr")
        ax.fill_between(yrs, lower, upper,
                        color=C.C_ELNINO, alpha=.15,
                        label="Slope 95% CI envelope")
        # all-method p-values
        try:
            cr = comp_idx.loc[(r["station"], r["timescale"])]
            ann = (f"TFPW p={cr['TFPW_MK_p']:.3f}\n"
                   f"MK p={cr['Original_MK_p']:.3f}\n"
                   f"$r_1$={cr['lag1_autocorr']}")
            ax.text(0.03, 0.97, ann, transform=ax.transAxes, va="top",
                    ha="left", fontsize=7,
                    bbox=dict(boxstyle="round", fc="white", ec="#cccccc",
                              alpha=.85))
        except KeyError:
            pass
        ax.set_title(f"Station {int(r['station'])} — {r['timescale']}")
        ax.set_xlabel("Year"); ax.set_ylabel("Rainfall (mm)")
        ax.legend(fontsize=7, loc="lower right")
    for k in range(n, nrow * ncol):                # blank unused panels
        axes[k // ncol][k % ncol].axis("off")
    fig.suptitle("Significant Station Trends (TFPW-MK, α=0.05) in "
                 "Prachuap Khiri Khan Province", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    _save(fig, name)


def fig_etccdi_series(reg: pd.DataFrame, index_names, units,
                      name="ETCCDI_FIG_regional_series"):
    """8-panel regional-mean ETCCDI time series with Sen-slope trend lines."""
    from .mktrend import tfpw_mk
    ncol = 4
    nrow = int(np.ceil(len(index_names) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(3.6 * ncol, 3.0 * nrow),
                             squeeze=False)
    for k, idx in enumerate(index_names):
        ax = axes[k // ncol][k % ncol]
        s = reg[idx].dropna()
        yrs = s.index.values.astype(float)
        t = yrs - yrs.min()
        ax.plot(yrs, s.values, "-o", color=C.C_MAIN, ms=2.5, lw=0.9)
        r = tfpw_mk(s.values.astype(float), C.ALPHA)
        line, _, _ = _sen_lines_median_anchor(
            s.values, t, r.sens_slope)
        sig = r.significant
        ax.plot(yrs, line, "-", color=C.C_ELNINO if sig else C.C_NEUTRAL,
                lw=1.6 if sig else 1.1,
                label=f"{r.sens_slope:+.2f}{'*' if sig else ''} {units[idx]}/yr")
        ax.set_title(idx, fontsize=10)
        ax.set_xlabel("Year", fontsize=8)
        ax.set_ylabel(units[idx], fontsize=8)
        ax.legend(fontsize=7, loc="best")
        ax.tick_params(labelsize=7)
    for k in range(len(index_names), nrow * ncol):
        axes[k // ncol][k % ncol].axis("off")
    fig.suptitle("Regional-Mean ETCCDI Extreme-Precipitation Indices "
                 "(TFPW-MK Sen's slope; * p<0.05)", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    for ext in ("png", "pdf"):
        fig.savefig(C.EXTREMES / f"{name}.{ext}", dpi=C.DPI, bbox_inches="tight")
    plt.close(fig)
    log.info("saved %s.{png,pdf}", name)


def fig_changepoint_series(ps: dict, cp_table, name="CP_FIG_01_regime_shift_series"):
    """Small-multiple series for every station x timescale with a significant
    abrupt shift: observed data, pre/post mean levels, the break year, and the
    Pettitt/Bayes/BIC verdict annotated."""
    sig = cp_table[cp_table["pettitt_sig"]].copy()
    sig = sig.sort_values(["timescale", "station"]).reset_index(drop=True)
    if sig.empty:
        fig, ax = plt.subplots(figsize=(6, 3)); ax.axis("off")
        ax.text(.5, .5, "No significant abrupt shift (Pettitt, a=0.05).",
                ha="center", va="center"); _save_to(fig, name, C.CHANGEPOINT); return
    tcol = {"Annual": C.C_MAIN, "Wet": C.C_LANINA, "Dry": C.C_ELNINO}
    BREAK = "#6A0DAD"          # purple: distinct from all rainfall-series colours
    n = len(sig); ncol = 3 if n >= 3 else n
    nrow = int(np.ceil(n / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(4.8 * ncol, 3.3 * nrow),
                             squeeze=False)
    for k, (_, r) in enumerate(sig.iterrows()):
        ax = axes[k // ncol][k % ncol]
        s = ps[r["station"]][r["timescale"]].dropna().astype(float)
        yrs = s.index.values
        col = tcol.get(r["timescale"], C.C_MAIN)
        ax.plot(yrs, s.values, "-o", color=col, ms=3, lw=0.9, label="Observed")
        cy = r["pettitt_year"]
        pre = s[s.index <= cy]; post = s[s.index > cy]
        ax.hlines(pre.mean(), yrs.min(), cy, color="black", lw=1.6, zorder=4)
        ax.hlines(post.mean(), cy, yrs.max(), color="black", lw=1.6, zorder=4,
                  label="Pre/post mean")
        ax.axvline(cy, color=BREAK, ls="--", lw=1.6, label=f"Break {cy}")
        ax.axvspan(r["bayes_ci_low"], r["bayes_ci_high"], color=BREAK,
                   alpha=.12, zorder=0)
        ann = (f"Pettitt p={r['pettitt_p']:.3f}\nBF$_{{10}}$={r['bayes_factor']:.0f}"
               f"\nBIC: {r['best_model_BIC']}\nΔ={r['step_size']:+.0f}")
        ax.text(0.03, 0.97, ann, transform=ax.transAxes, va="top", ha="left",
                fontsize=7, bbox=dict(boxstyle="round", fc="white", ec="#ccc",
                                      alpha=.85))
        ax.set_title(f"Gauge {int(r['station'])} — {r['timescale']}")
        ax.set_xlabel("Year"); ax.set_ylabel("Rainfall (mm)")
        ax.legend(fontsize=6.5, loc="lower left")
    for k in range(n, nrow * ncol):
        axes[k // ncol][k % ncol].axis("off")
    fig.suptitle("Detected Regime Shifts (Pettitt break; Bayesian CI shaded; "
                 "BIC step/trend verdict)", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    _save_to(fig, name, C.CHANGEPOINT)


def fig_sequential_mk(ps, cp_table, picks, name="CP_FIG_02_sequential_mk"):
    """Sneyers progressive (u) vs retrograde (u') curves; their crossing marks
    the change onset. `picks` is a list of (station, timescale)."""
    from .changepoint import sequential_mk
    n = len(picks); ncol = 3 if n >= 3 else n
    nrow = int(np.ceil(n / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(4.8 * ncol, 3.3 * nrow),
                             squeeze=False)
    for k, (sid, var) in enumerate(picks):
        ax = axes[k // ncol][k % ncol]
        s = ps[sid][var].dropna().astype(float)
        yrs = s.index.values
        sm = sequential_mk(s.values)
        ax.plot(yrs, sm["u_prog"], "-", color=C.C_MAIN, lw=1.3, label="u(t) prog.")
        ax.plot(yrs, sm["u_retro"], "--", color=C.C_ELNINO, lw=1.3,
                label="u'(t) retro.")
        ax.axhline(1.96, color="#999", lw=.7, ls=":")
        ax.axhline(-1.96, color="#999", lw=.7, ls=":")
        ax.axhline(0, color="#ccc", lw=.6)
        for c in sm["crossings"]:
            ax.axvline(yrs[c], color="green", lw=1.0, alpha=.6)
        ax.set_title(f"Gauge {int(sid)} — {var}")
        ax.set_xlabel("Year"); ax.set_ylabel("standardised statistic")
        ax.legend(fontsize=7, loc="best")
    for k in range(n, nrow * ncol):
        axes[k // ncol][k % ncol].axis("off")
    fig.suptitle("Sequential Mann-Kendall (Sneyers): trend onset at u/u' crossing",
                 fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    _save_to(fig, name, C.CHANGEPOINT)


def _save_to(fig, name, out_dir):
    for ext in ("png", "pdf"):
        fig.savefig(out_dir / f"{name}.{ext}", dpi=C.DPI, bbox_inches="tight")
    plt.close(fig)
    log.info("saved %s.{png,pdf}", name)


def init():
    _setup_style()
