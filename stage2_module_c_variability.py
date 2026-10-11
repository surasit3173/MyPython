"""
Stage 2 - Module C (v2): Temporal Variability & Decomposition
ETo + Precipitation, 15 stations, NE Thailand, 1979-2007

Analyses:
  1. Decadal comparison (3 decades)
  2. Standardized anomaly
  3. Seasonal decomposition (trend + seasonal + residual)
  4. ETo-Precip correlation (raw + detrended)
  5. Dry/wet year classification (quintile-based)

Q4 journal level - Times New Roman, 400 dpi, no overlap
"""

# ================================================================
# 0. Imports
# ================================================================
import os
import sys
import warnings
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from matplotlib.ticker import MultipleLocator
from matplotlib.colors import ListedColormap
from scipy import stats

warnings.filterwarnings("ignore", category=FutureWarning)


# ================================================================
# 1. Plot style
# ================================================================
mpl.rcParams.update({
    "font.family":       "serif",
    "font.serif":        ["Times New Roman", "Times", "DejaVu Serif"],
    "mathtext.fontset":  "stix",
    "font.size":         9,
    "axes.labelsize":    9.5,
    "axes.titlesize":    9.5,
    "xtick.labelsize":   8.5,
    "ytick.labelsize":   8.5,
    "legend.fontsize":   8,
    "axes.linewidth":    0.8,
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "xtick.major.size":  3.5,
    "ytick.major.size":  3.5,
    "xtick.direction":   "out",
    "ytick.direction":   "out",
    "figure.dpi":        200,
    "savefig.dpi":       400,
    "savefig.bbox":      "tight",
    "savefig.pad_inches": 0.06,
    "pdf.fonttype":      42,
    "lines.linewidth":   1.0,
    "lines.markersize":  4,
})

MM       = 1 / 25.4
W_SINGLE = 89  * MM
W_DOUBLE = 183 * MM

CLR_ETO  = "#C1440E"
CLR_PREC = "#1F6FB4"
CLR_POS  = "#1F6FB4"
CLR_NEG  = "#C1440E"

DECADES = [
    ("1979\u20131988", 1979, 1988, "#F2A65A"),
    ("1989\u20131998", 1989, 1998, "#D97B29"),
    ("1999\u20132007", 1999, 2007, "#8C4A15"),
]

QUINTILE_LABELS = ["Very dry", "Dry", "Normal", "Wet", "Very wet"]
QUINTILE_COLORS = ["#8C1F0E", "#D97B29", "#F5F0DC", "#5C9BC4", "#0D4A78"]


# ================================================================
# 2. Paths & config
# ================================================================
BASE_DIR = "."
DATA_DIR = os.path.join(BASE_DIR, "data")
OUT_DIR  = os.path.join(BASE_DIR, "outputs", "module_c")
FIG_DIR  = os.path.join(OUT_DIR, "figures")
TAB_DIR  = os.path.join(OUT_DIR, "tables")
os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(TAB_DIR, exist_ok=True)

ETO_DAILY_CSV  = os.path.join(DATA_DIR, "agera5_eto_station_daily_arco.csv")
PREC_DAILY_CSV = os.path.join(DATA_DIR, "agera5_precip_station_daily_arco.csv")

STATIONS = {
    352201: "Nong Khai",        353201: "Loei",
    356201: "Sakon Nakhon",     357201: "Nakhon Phanom",
    381201: "Khon Kaen",        383201: "Mukdahan",
    387401: "Kosum Phisai",     403201: "Chaiyaphum",
    405201: "Roi Et",           407501: "Ubon Ratchathani",
    431201: "Nakhon Ratchasima", 431401: "Chok Chai",
    432201: "Surin",            432401: "Tha Tum",
    436401: "Nang Rong",
}

YEAR_START, YEAR_END = 1979, 2007


# ================================================================
# 3. Loaders & aggregation
# ================================================================
def load_daily(path, var_name):
    if not os.path.exists(path):
        print(f"\u26a0\ufe0f  \u0e44\u0e21\u0e48\u0e1e\u0e1a {path}")
        return None
    df = pd.read_csv(path, parse_dates=["time"])
    df = df.rename(columns={"time": "date"})
    col = [c for c in df.columns if c.startswith(var_name)][0]
    df = df.rename(columns={col: var_name})
    df["stncode"] = df["stncode"].astype(int)
    return df[["stncode", "date", var_name]].dropna()


def make_monthly(daily_df, var_name):
    df = daily_df.copy()
    df["year"]  = df["date"].dt.year
    df["month"] = df["date"].dt.month
    monthly = (df.groupby(["stncode", "year", "month"])
                 .agg(value=(var_name, "sum"),
                      n=(var_name, "count"))
                 .reset_index())
    monthly = monthly[monthly["n"] >= 25].drop(columns="n")
    monthly["date"] = pd.to_datetime(
        dict(year=monthly["year"], month=monthly["month"], day=1))
    return monthly.rename(columns={"value": var_name})


def make_annual(monthly_df, var_name):
    df = monthly_df.copy()
    n_months = (df.groupby(["stncode", "year"])["date"]
                  .count().reset_index()
                  .rename(columns={"date": "n_months"}))
    annual = (df.groupby(["stncode", "year"])
                .agg(value=(var_name, "sum"))
                .reset_index()
                .rename(columns={"value": var_name}))
    annual = annual.merge(n_months[n_months["n_months"] == 12],
                          on=["stncode", "year"], how="inner")
    return annual.drop(columns="n_months")


# ================================================================
# 4. Analysis functions
# ================================================================
def decadal_stats(annual_df, var_name):
    rows = []
    for label, y0, y1, _ in DECADES:
        sub = annual_df[(annual_df["year"] >= y0) &
                        (annual_df["year"] <= y1)]
        for stn in sorted(sub["stncode"].unique()):
            s = sub[sub["stncode"] == stn][var_name].values
            if len(s) == 0:
                continue
            rows.append({
                "stncode": stn,
                "station": STATIONS.get(stn, str(stn)),
                "decade": label,
                "n_years": len(s),
                "mean": float(np.mean(s)),
                "sd":   float(np.std(s, ddof=1)) if len(s) > 1 else np.nan,
                "cv":   float(100 * np.std(s, ddof=1) / np.mean(s))
                        if len(s) > 1 and np.mean(s) != 0 else np.nan,
            })
    # Regional aggregate
    for label, y0, y1, _ in DECADES:
        sub = annual_df[(annual_df["year"] >= y0) &
                        (annual_df["year"] <= y1)]
        regional = sub.groupby("year")[var_name].mean()
        rows.append({
            "stncode": 0,
            "station": "REGIONAL",
            "decade": label,
            "n_years": len(regional),
            "mean": float(regional.mean()),
            "sd":   float(regional.std(ddof=1)),
            "cv":   float(100 * regional.std(ddof=1) / regional.mean()),
        })
    return pd.DataFrame(rows)


def decadal_change(decadal_df, var_name):
    rows = []
    for stn in sorted(decadal_df["stncode"].unique()):
        sub = decadal_df[decadal_df["stncode"] == stn]
        if len(sub) < 3:
            continue
        m1 = sub[sub["decade"] == DECADES[0][0]]["mean"].values[0]
        m3 = sub[sub["decade"] == DECADES[2][0]]["mean"].values[0]
        pct = 100 * (m3 - m1) / m1 if m1 != 0 else np.nan
        rows.append({
            "stncode": int(stn),
            "station": STATIONS.get(stn, str(stn)) if stn != 0 else "REGIONAL",
            "mean_1979_1988": m1,
            "mean_1999_2007": m3,
            "delta": m3 - m1,
            "pct_change": pct,
        })
    return pd.DataFrame(rows)


def anomaly_analysis(annual_df, var_name):
    rows = []
    for stn in sorted(annual_df["stncode"].unique()):
        sub = annual_df[annual_df["stncode"] == stn].sort_values("year")
        v = sub[var_name].values
        mu, sd = np.mean(v), np.std(v, ddof=1)
        anom = (v - mu) / sd if sd > 0 else np.zeros_like(v)
        for year, val, a in zip(sub["year"].values, v, anom):
            rows.append({
                "stncode": int(stn),
                "station": STATIONS.get(stn, str(stn)),
                "year": int(year),
                var_name: float(val),
                "anomaly": float(a),
            })
    return pd.DataFrame(rows)


def seasonal_decompose(monthly_df, var_name):
    """Manual additive decomposition"""
    ts = monthly_df.groupby("date")[var_name].mean().sort_index()
    ts = ts.asfreq("MS").interpolate()
    values = ts.values

    trend = (pd.Series(values, index=ts.index)
               .rolling(window=12, center=True, min_periods=6)
               .mean().values)
    detrended = values - trend
    months = ts.index.month

    seasonal_by_month = {}
    for m in range(1, 13):
        mask = (months == m) & ~np.isnan(detrended)
        seasonal_by_month[m] = np.mean(detrended[mask]) if mask.any() else 0.0
    seasonal = np.array([seasonal_by_month[m] for m in months])
    residual = values - trend - seasonal

    return pd.DataFrame({
        "date": ts.index,
        "observed": values,
        "trend": trend,
        "seasonal": seasonal,
        "residual": residual,
    })


def variance_components(decomp_df):
    obs = decomp_df["observed"].values
    trend = decomp_df["trend"].values
    seasonal = decomp_df["seasonal"].values
    residual = decomp_df["residual"].values

    mask = ~(np.isnan(trend) | np.isnan(residual))
    obs_c = obs[mask]
    tr_c  = trend[mask]
    se_c  = seasonal[mask]
    re_c  = residual[mask]

    var_total = np.var(obs_c, ddof=1)
    var_trend = np.var(tr_c, ddof=1)
    var_seasonal = np.var(se_c, ddof=1)
    var_residual = np.var(re_c, ddof=1)
    var_ts = np.var(tr_c + se_c, ddof=1)

    return {
        "var_observed":   float(var_total),
        "var_trend":      float(var_trend),
        "var_seasonal":   float(var_seasonal),
        "var_residual":   float(var_residual),
        "pct_trend":      float(100 * var_trend / var_total),
        "pct_seasonal":   float(100 * var_seasonal / var_total),
        "pct_trend_seas": float(100 * var_ts / var_total),
        "pct_residual":   float(100 * var_residual / var_total),
    }


def correlation_analysis(annual_eto, annual_prec):
    merged = annual_eto.merge(annual_prec, on=["stncode", "year"],
                              suffixes=("_eto", "_prec"))
    rows = []
    for stn in sorted(merged["stncode"].unique()):
        sub = merged[merged["stncode"] == stn].sort_values("year")
        eto  = sub["eto"].values
        prec = sub["prec"].values
        x = sub["year"].values

        r_raw, p_raw = stats.pearsonr(eto, prec)
        eto_dt  = eto  - np.polyval(np.polyfit(x, eto,  1), x)
        prec_dt = prec - np.polyval(np.polyfit(x, prec, 1), x)
        r_dt, p_dt = stats.pearsonr(eto_dt, prec_dt)

        rows.append({
            "stncode": int(stn),
            "station": STATIONS.get(stn, str(stn)),
            "n": len(sub),
            "r_raw": float(r_raw), "p_raw": float(p_raw),
            "r_detrended": float(r_dt), "p_detrended": float(p_dt),
        })

    # Regional
    reg = merged.groupby("year")[["eto", "prec"]].mean().reset_index()
    r_raw, p_raw = stats.pearsonr(reg["eto"], reg["prec"])
    x = reg["year"].values
    eto_dt  = reg["eto"].values  - np.polyval(np.polyfit(x, reg["eto"],  1), x)
    prec_dt = reg["prec"].values - np.polyval(np.polyfit(x, reg["prec"], 1), x)
    r_dt, p_dt = stats.pearsonr(eto_dt, prec_dt)
    rows.append({
        "stncode": 0, "station": "REGIONAL", "n": len(reg),
        "r_raw": float(r_raw), "p_raw": float(p_raw),
        "r_detrended": float(r_dt), "p_detrended": float(p_dt),
    })
    return pd.DataFrame(rows)


def wet_dry_classification(annual_prec):
    rows = []
    for stn in sorted(annual_prec["stncode"].unique()):
        sub = annual_prec[annual_prec["stncode"] == stn].sort_values("year")
        v = sub["prec"].values
        q = np.percentile(v, [20, 40, 60, 80])
        for year, val in zip(sub["year"].values, v):
            if   val < q[0]: cls = "Very dry"
            elif val < q[1]: cls = "Dry"
            elif val < q[2]: cls = "Normal"
            elif val < q[3]: cls = "Wet"
            else:            cls = "Very wet"
            rows.append({
                "stncode": int(stn),
                "station": STATIONS.get(stn, str(stn)),
                "year": int(year),
                "precip": float(val),
                "class": cls,
            })
    return pd.DataFrame(rows)


# ================================================================
# 5. Figures
# ================================================================
def add_panel_letter(ax, letter, xoff=-0.14, yoff=1.05):
    ax.text(xoff, yoff, letter, transform=ax.transAxes,
            fontsize=13, fontweight="bold", family="serif",
            ha="left", va="bottom", clip_on=False)


def plot_fig1_decadal(decadal_eto, decadal_prec):
    print("\U0001f3a8 Fig 1: Decadal boxplot ...")

    fig, axes = plt.subplots(1, 2, figsize=(W_DOUBLE, 82 * MM))
    plt.subplots_adjust(wspace=0.28, left=0.075, right=0.98,
                        top=0.90, bottom=0.16)

    rng = np.random.default_rng(42)

    for ax, (df, var, ylabel, letter) in zip(
        axes,
        [(decadal_eto,  "eto",  "Annual ETo (mm yr$^{-1}$)",           "a"),
         (decadal_prec, "prec", "Annual precipitation (mm yr$^{-1}$)", "b")]
    ):
        data = [df[df["decade"] == label]["mean"].values
                for label, _, _, _ in DECADES]
        colors = [c for _, _, _, c in DECADES]

        bp = ax.boxplot(data, positions=np.arange(3), widths=0.55,
                        patch_artist=True, showfliers=False,
                        medianprops=dict(color="black", lw=1.0),
                        whiskerprops=dict(color="black", lw=0.7),
                        capprops=dict(color="black", lw=0.7))
        for patch, c in zip(bp["boxes"], colors):
            patch.set_facecolor(c)
            patch.set_alpha(0.75)
            patch.set_edgecolor("black")
            patch.set_linewidth(0.6)

        # Individual stations
        for i, (label, _, _, _) in enumerate(DECADES):
            vals = df[df["decade"] == label]["mean"].values
            jitter = rng.uniform(-0.12, 0.12, size=len(vals))
            ax.scatter(i + jitter, vals, s=8, c="black",
                       alpha=0.5, edgecolors="none", zorder=4)

        ax.set_xticks(np.arange(3))
        ax.set_xticklabels([d[0] for d in DECADES], fontsize=8.5)
        ax.set_xlabel("Decade")
        ax.set_ylabel(ylabel)
        ax.set_title("Decadal means", pad=6, fontsize=9.5)
        ax.yaxis.set_minor_locator(MultipleLocator(
            10 if var == "eto" else 100))
        add_panel_letter(ax, letter)

    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG_DIR, f"fig1_decadal_boxplot.{ext}"))
    plt.close(fig)


def plot_fig2_anomaly(anom_eto, anom_prec):
    print("\U0001f3a8 Fig 2: Standardized anomalies ...")

    a_eto  = anom_eto.groupby("year")["anomaly"].mean().sort_index()
    a_prec = anom_prec.groupby("year")["anomaly"].mean().sort_index()

    fig, axes = plt.subplots(2, 1, figsize=(W_DOUBLE, 110 * MM),
                             sharex=True)
    plt.subplots_adjust(hspace=0.16, left=0.075, right=0.98,
                        top=0.94, bottom=0.09)

    for ax, (a, label, letter) in zip(
        axes,
        [(a_eto,  "ETo anomaly",           "a"),
         (a_prec, "Precipitation anomaly", "b")]
    ):
        vals = a.values
        years_here = a.index.values
        colors = np.where(vals >= 0, CLR_POS, CLR_NEG)

        ax.bar(years_here, vals, color=colors, edgecolor="black",
               linewidth=0.4, width=0.75, alpha=0.85)
        ax.axhline(0, color="black", lw=0.8)
        ax.axhline(1, color="0.4", lw=0.6, ls=":")
        ax.axhline(-1, color="0.4", lw=0.6, ls=":")

        coef = np.polyfit(years_here, vals, 1)
        xfit = np.linspace(years_here.min(), years_here.max(), 100)
        ax.plot(xfit, np.polyval(coef, xfit), "-", color="black",
                lw=1.4, zorder=5)

        r, p = stats.pearsonr(years_here, vals)
        # ✅ FIX: ใช้ raw string r"..." กับ \sigma
        txt = (f"Trend = {coef[0]*10:+.2f} " + r"$\sigma$" +
               f" dec$^{{-1}}$\n"
               f"$r$ = {r:.3f}, $p$ = {p:.3f}")
        ax.text(0.99, 0.05, txt,
                transform=ax.transAxes, ha="right", va="bottom",
                fontsize=7.5,
                bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                          edgecolor="0.7", lw=0.5, alpha=0.95))

        # ✅ FIX: raw string
        ax.set_ylabel(label + r" ($\sigma$)")
        ax.set_ylim(-3.2, 3.2)
        ax.xaxis.set_major_locator(MultipleLocator(5))
        ax.xaxis.set_minor_locator(MultipleLocator(1))
        ax.yaxis.set_minor_locator(MultipleLocator(0.5))
        add_panel_letter(ax, letter)

        if letter == "b":
            ax.set_xlabel("Year")

    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG_DIR, f"fig2_anomaly_timeseries.{ext}"))
    plt.close(fig)


def plot_fig3_decomp(decomp_eto, decomp_prec):
    print("\U0001f3a8 Fig 3: Seasonal decomposition ...")

    fig = plt.figure(figsize=(W_DOUBLE, 145 * MM))
    gs = GridSpec(4, 2, figure=fig, hspace=0.20, wspace=0.22,
                  left=0.075, right=0.98, top=0.94, bottom=0.06)

    panels = [
        ("Observed", "observed", 0),
        ("Trend",    "trend",    1),
        ("Seasonal", "seasonal", 2),
        ("Residual", "residual", 3),
    ]

    letters = iter(["a", "b", "c", "d", "e", "f", "g", "h"])

    for col, (df, title, clr) in enumerate(
        [(decomp_eto,  "ETo",           CLR_ETO),
         (decomp_prec, "Precipitation", CLR_PREC)]
    ):
        for row, (label, col_name, _) in enumerate(panels):
            ax = fig.add_subplot(gs[row, col])
            v = df[col_name].values
            dates = df["date"].values

            if row == 0:
                ax.plot(dates, v, "-", color=clr, lw=0.7)
            elif row == 1:
                ax.plot(dates, v, "-", color="black", lw=1.2)
            elif row == 2:
                ax.plot(dates, v, "-", color=clr, lw=0.8, alpha=0.85)
                ax.axhline(0, color="0.6", lw=0.5)
            else:
                ax.bar(dates, v, color=clr, width=25, alpha=0.5,
                       edgecolor="none")
                ax.axhline(0, color="0.6", lw=0.5)

            ax.set_ylabel(label, fontsize=8.5)
            ax.tick_params(labelsize=7.5)
            ax.xaxis.set_major_locator(mpl.dates.YearLocator(5))
            ax.xaxis.set_minor_locator(mpl.dates.YearLocator(1))

            if row == 0:
                ax.set_title(title, pad=6, fontsize=10)

            letter = next(letters)
            add_panel_letter(ax, letter, xoff=-0.16, yoff=1.05)

    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG_DIR, f"fig3_decomposition.{ext}"))
    plt.close(fig)


def plot_fig4_scatter(annual_eto, annual_prec, corr_df):
    print("\U0001f3a8 Fig 4: ETo vs Precip scatter ...")

    merged = annual_eto.merge(annual_prec, on=["stncode", "year"],
                              suffixes=("_eto", "_prec"))

    eto_anom = merged.copy()
    eto_anom["eto_z"] = (
        (merged["eto"] - merged.groupby("stncode")["eto"].transform("mean"))
        / merged.groupby("stncode")["eto"].transform("std"))
    eto_anom["prec_z"] = (
        (merged["prec"] - merged.groupby("stncode")["prec"].transform("mean"))
        / merged.groupby("stncode")["prec"].transform("std"))

    fig, axes = plt.subplots(1, 2, figsize=(W_DOUBLE, 85 * MM))
    plt.subplots_adjust(wspace=0.28, left=0.075, right=0.98,
                        top=0.90, bottom=0.16)

    # ---- Panel a ----
    ax = axes[0]
    x = merged["prec"].values
    y = merged["eto"].values

    hb = ax.hexbin(x, y, gridsize=40, bins="log", cmap="Blues",
                   mincnt=1, linewidths=0)
    fig.colorbar(hb, ax=ax, pad=0.02, fraction=0.045, label="log(count)")

    coef = np.polyfit(x, y, 1)
    xfit = np.linspace(x.min(), x.max(), 100)
    ax.plot(xfit, np.polyval(coef, xfit), "-", color=CLR_ETO, lw=1.4)

    r, p = stats.pearsonr(x, y)
    ax.text(0.98, 0.05,
            f"$r$ = {r:.3f}, $p$ = {p:.2e}\n"
            f"slope = {coef[0]:+.3f} mm mm$^{{-1}}$",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=7.5,
            bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                      edgecolor="0.7", lw=0.5, alpha=0.95))

    ax.set_xlabel("Annual precipitation (mm yr$^{-1}$)")
    ax.set_ylabel("Annual ETo (mm yr$^{-1}$)")
    ax.set_title("Annual totals (pooled)", pad=6, fontsize=9.5)
    add_panel_letter(ax, "a")

    # ---- Panel b ----
    ax = axes[1]
    xz = eto_anom["prec_z"].values
    yz = eto_anom["eto_z"].values

    hb2 = ax.hexbin(xz, yz, gridsize=40, bins="log", cmap="Reds",
                    mincnt=1, linewidths=0,
                    extent=(-3.5, 3.5, -3.5, 3.5))
    fig.colorbar(hb2, ax=ax, pad=0.02, fraction=0.045, label="log(count)")

    coef = np.polyfit(xz, yz, 1)
    xfit = np.linspace(-3.5, 3.5, 100)
    ax.plot(xfit, np.polyval(coef, xfit), "-", color=CLR_PREC, lw=1.4)
    ax.plot([-3.5, 3.5], [-3.5, 3.5], ":", color="0.5", lw=0.6)
    ax.axhline(0, color="0.7", lw=0.5)
    ax.axvline(0, color="0.7", lw=0.5)

    r, p = stats.pearsonr(xz, yz)
    ax.text(0.98, 0.05,
            f"$r$ = {r:.3f}, $p$ = {p:.2e}\n"
            f"$n$ = {len(xz):,}",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=7.5,
            bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                      edgecolor="0.7", lw=0.5, alpha=0.95))

    ax.set_xlim(-3.5, 3.5)
    ax.set_ylim(-3.5, 3.5)
    ax.set_aspect("equal")
    # ✅ FIX: raw string
    ax.set_xlabel(r"Precip anomaly ($\sigma$)")
    ax.set_ylabel(r"ETo anomaly ($\sigma$)")
    ax.set_title("Standardized anomalies", pad=6, fontsize=9.5)
    add_panel_letter(ax, "b")

    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG_DIR, f"fig4_eto_precip_scatter.{ext}"))
    plt.close(fig)


def plot_fig5_wetdry(class_df):
    """Fig 5: Wet/dry heatmap (FIXED dtype issue)"""
    print("\U0001f3a8 Fig 5: Wet/dry year classification ...")

    pivot = class_df.pivot_table(
        index="station", columns="year",
        values="class", aggfunc="first")

    station_order = [
        "Nong Khai", "Loei", "Sakon Nakhon", "Nakhon Phanom",
        "Khon Kaen", "Mukdahan", "Kosum Phisai", "Chaiyaphum",
        "Roi Et", "Ubon Ratchathani", "Nakhon Ratchasima",
        "Chok Chai", "Surin", "Tha Tum", "Nang Rong",
    ]
    pivot = pivot.reindex([s for s in station_order if s in pivot.index])

    # ✅ FIX: ใช้ map + astype(float) แทน replace()
    class_to_num = {label: float(i) for i, label in enumerate(QUINTILE_LABELS)}
    data_num = pivot.apply(lambda col: col.map(class_to_num)).astype(float).values

    if np.isnan(data_num).all():
        print("   \u26a0\ufe0f  \u0e02\u0e49\u0e2d\u0e21\u0e39\u0e25\u0e27\u0e48\u0e32\u0e07\u0e40\u0e1b\u0e25\u0e48\u0e32")
        return

    fig, ax = plt.subplots(figsize=(W_DOUBLE, 90 * MM))
    plt.subplots_adjust(left=0.16, right=0.98, top=0.90, bottom=0.20)

    cmap = ListedColormap(QUINTILE_COLORS)
    cmap.set_bad(color="#EEEEEE")

    data_masked = np.ma.masked_invalid(data_num)

    im = ax.imshow(data_masked, aspect="auto", cmap=cmap,
                   vmin=-0.5, vmax=4.5, interpolation="nearest")

    # Grid
    ax.set_xticks(np.arange(-0.5, len(pivot.columns), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(pivot.index),   1), minor=True)
    ax.grid(which="minor", color="white", linewidth=0.4)
    ax.tick_params(which="minor", length=0)

    ax.set_xticks(np.arange(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, rotation=90, fontsize=6.5)
    ax.set_yticks(np.arange(len(pivot.index)))
    ax.set_yticklabels(pivot.index, fontsize=7.5)

    ax.set_xlabel("Year")
    ax.set_title("Wet/dry year classification "
                 "(per station, quintile-based)",
                 pad=6, fontsize=9.5)

    handles = [Patch(facecolor=c, edgecolor="black", linewidth=0.3,
                     label=l)
               for l, c in zip(QUINTILE_LABELS, QUINTILE_COLORS)]
    ax.legend(handles=handles, loc="upper center",
              bbox_to_anchor=(0.5, -0.22), ncol=5,
              fontsize=8, frameon=False)

    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG_DIR, f"fig5_wetdry_heatmap.{ext}"))
    plt.close(fig)


# ================================================================
# 6. Main
# ================================================================
def main():
    print("=" * 70)
    print("Stage 2 - Module C (v2): Temporal Variability & Decomposition")
    print("=" * 70)

    # ---- Load ----
    eto_daily  = load_daily(ETO_DAILY_CSV,  "eto")
    prec_daily = load_daily(PREC_DAILY_CSV, "prec")

    if eto_daily is None or prec_daily is None:
        print("\n\u274c \u0e02\u0e49\u0e2d\u0e21\u0e39\u0e25\u0e44\u0e21\u0e48\u0e04\u0e23\u0e1a")
        return

    # Filter period
    eto_daily  = eto_daily[(eto_daily["date"].dt.year  >= YEAR_START) &
                            (eto_daily["date"].dt.year  <= YEAR_END)]
    prec_daily = prec_daily[(prec_daily["date"].dt.year >= YEAR_START) &
                             (prec_daily["date"].dt.year <= YEAR_END)]

    # ---- Aggregate ----
    print("\n\u23f3 Aggregating daily \u2192 monthly \u2192 annual ...")
    eto_monthly  = make_monthly(eto_daily,  "eto")
    prec_monthly = make_monthly(prec_daily, "prec")
    eto_annual   = make_annual(eto_monthly,  "eto")
    prec_annual  = make_annual(prec_monthly, "prec")

    print(f"   ETo:  {len(eto_annual):,} station-years")
    print(f"   Prec: {len(prec_annual):,} station-years")

    # ---- 1. Decadal ----
    print("\n" + "=" * 70)
    print("\U0001f4cc 1. Decadal analysis")
    print("=" * 70)
    dec_eto  = decadal_stats(eto_annual,  "eto")
    dec_prec = decadal_stats(prec_annual, "prec")
    dec_eto.to_csv( os.path.join(TAB_DIR, "table1_decadal_eto.csv"),
                    index=False, float_format="%.2f")
    dec_prec.to_csv(os.path.join(TAB_DIR, "table2_decadal_prec.csv"),
                    index=False, float_format="%.2f")

    chg_eto  = decadal_change(dec_eto,  "eto")
    chg_prec = decadal_change(dec_prec, "prec")
    chg_eto.to_csv( os.path.join(TAB_DIR, "table3_decadal_change_eto.csv"),
                    index=False, float_format="%.2f")
    chg_prec.to_csv(os.path.join(TAB_DIR, "table3_decadal_change_prec.csv"),
                    index=False, float_format="%.2f")

    plot_fig1_decadal(dec_eto, dec_prec)

    # ---- 2. Anomaly ----
    print("\n" + "=" * 70)
    print("\U0001f4cc 2. Anomaly analysis")
    print("=" * 70)
    anom_eto  = anomaly_analysis(eto_annual,  "eto")
    anom_prec = anomaly_analysis(prec_annual, "prec")
    anom_eto.to_csv( os.path.join(TAB_DIR, "table4_anomaly_eto.csv"),
                     index=False, float_format="%.3f")
    anom_prec.to_csv(os.path.join(TAB_DIR, "table4_anomaly_prec.csv"),
                     index=False, float_format="%.3f")

    plot_fig2_anomaly(anom_eto, anom_prec)

    # ---- 3. Decomposition ----
    print("\n" + "=" * 70)
    print("\U0001f4cc 3. Seasonal decomposition")
    print("=" * 70)
    decomp_eto  = seasonal_decompose(eto_monthly,  "eto")
    decomp_prec = seasonal_decompose(prec_monthly, "prec")

    var_eto  = variance_components(decomp_eto)
    var_prec = variance_components(decomp_prec)

    var_df = pd.DataFrame([
        {"variable": "ETo",           **var_eto},
        {"variable": "Precipitation", **var_prec},
    ])
    var_df.to_csv(os.path.join(TAB_DIR, "table5_variance_components.csv"),
                  index=False, float_format="%.3f")

    decomp_eto.to_csv( os.path.join(TAB_DIR, "table6_decomp_eto.csv"),
                       index=False, float_format="%.3f")
    decomp_prec.to_csv(os.path.join(TAB_DIR, "table6_decomp_prec.csv"),
                       index=False, float_format="%.3f")

    plot_fig3_decomp(decomp_eto, decomp_prec)

    # ---- 4. Correlation ----
    print("\n" + "=" * 70)
    print("\U0001f4cc 4. ETo-Precip correlation")
    print("=" * 70)
    corr_df = correlation_analysis(eto_annual, prec_annual)
    corr_df.to_csv(os.path.join(TAB_DIR, "table7_correlation.csv"),
                   index=False, float_format="%.3f")

    plot_fig4_scatter(eto_annual, prec_annual, corr_df)

    # ---- 5. Wet/Dry ----
    print("\n" + "=" * 70)
    print("\U0001f4cc 5. Wet/Dry year classification")
    print("=" * 70)
    class_df = wet_dry_classification(prec_annual)
    class_df.to_csv(os.path.join(TAB_DIR, "table8_wetdry_class.csv"),
                    index=False, float_format="%.2f")

    counts = (class_df.groupby(["station", "class"]).size()
                      .unstack(fill_value=0))
    counts = counts.reindex(columns=QUINTILE_LABELS, fill_value=0)
    counts.to_csv(os.path.join(TAB_DIR, "table9_wetdry_counts.csv"))

    plot_fig5_wetdry(class_df)

    # ---- Summary ----
    print("\n" + "=" * 70)
    print("\U0001f4ca \u0e2a\u0e23\u0e38\u0e1b\u0e1c\u0e25")
    print("=" * 70)

    reg_eto_chg  = chg_eto[chg_eto["stncode"] == 0].iloc[0]
    reg_prec_chg = chg_prec[chg_prec["stncode"] == 0].iloc[0]

    print(f"\n\U0001f4cc Decadal change "
          f"({DECADES[0][0]} \u2192 {DECADES[2][0]}):")
    print(f"   ETo:    {reg_eto_chg['mean_1979_1988']:.1f} \u2192 "
          f"{reg_eto_chg['mean_1999_2007']:.1f} mm/yr "
          f"({reg_eto_chg['pct_change']:+.2f}%)")
    print(f"   Precip: {reg_prec_chg['mean_1979_1988']:.1f} \u2192 "
          f"{reg_prec_chg['mean_1999_2007']:.1f} mm/yr "
          f"({reg_prec_chg['pct_change']:+.2f}%)")

    print(f"\n\U0001f4cc Variance components:")
    print(f"   ETo:  Trend = {var_eto['pct_trend']:.1f}%, "
          f"Seasonal = {var_eto['pct_seasonal']:.1f}%, "
          f"Residual = {var_eto['pct_residual']:.1f}%")
    print(f"   Prec: Trend = {var_prec['pct_trend']:.1f}%, "
          f"Seasonal = {var_prec['pct_seasonal']:.1f}%, "
          f"Residual = {var_prec['pct_residual']:.1f}%")

    reg_corr = corr_df[corr_df["stncode"] == 0].iloc[0]
    print(f"\n\U0001f4cc ETo-Precip correlation (regional):")
    print(f"   Raw:       r = {reg_corr['r_raw']:+.3f} "
          f"(p = {reg_corr['p_raw']:.3f})")
    print(f"   Detrended: r = {reg_corr['r_detrended']:+.3f} "
          f"(p = {reg_corr['p_detrended']:.3f})")

    print(f"\n\U0001f4cc Wet/dry years (regional, average):")
    overall = (class_df.groupby("class").size()
                      / class_df["stncode"].nunique())
    for label in QUINTILE_LABELS:
        print(f"   {label:10s}: {overall.get(label, 0):.2f} \u0e1b\u0e35")

    print(f"\n\U0001f4c1 Tables : {os.path.abspath(TAB_DIR)}")
    print(f"\U0001f4c1 Figures: {os.path.abspath(FIG_DIR)}")
    print("=" * 70)


if __name__ == "__main__":
    main()