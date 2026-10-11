"""
Stage 2 - Module A (v3): Trend Analysis of ETo (1979-2007)
Publication-quality figures - FINAL VERSION
Q1 journal standard: Times New Roman, no overlap, unified scales
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.gridspec import GridSpec
from matplotlib.ticker import MultipleLocator, AutoMinorLocator, StrMethodFormatter
from scipy import stats

try:
    import pymannkendall as mk
except ImportError:
    print("pip install pymannkendall")
    sys.exit(1)

warnings.filterwarnings("ignore", category=FutureWarning)


# ================================================================
# 1. Plot style — Times New Roman, Q1 quality
# ================================================================
mpl.rcParams.update({
    "font.family":       "serif",
    "font.serif":        ["Times New Roman", "Times", "DejaVu Serif"],
    "mathtext.fontset":  "stix",
    "font.size":         9,
    "axes.labelsize":    9.5,
    "axes.titlesize":    10,
    "xtick.labelsize":   8.5,
    "ytick.labelsize":   8.5,
    "legend.fontsize":   8,
    "axes.linewidth":    0.8,
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "axes.labelpad":     4,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "xtick.major.size":  3.5,
    "ytick.major.size":  3.5,
    "xtick.minor.width": 0.6,
    "ytick.minor.width": 0.6,
    "xtick.minor.size":  2,
    "ytick.minor.size":  2,
    "xtick.direction":   "out",
    "ytick.direction":   "out",
    "lines.linewidth":   1.0,
    "lines.markersize":  4,
    "figure.dpi":        200,
    "savefig.dpi":       600,
    "savefig.bbox":      "tight",
    "savefig.pad_inches": 0.06,
    "pdf.fonttype":      42,
    "ps.fonttype":       42,
    "legend.frameon":    True,
    "legend.framealpha": 0.96,
    "legend.edgecolor":  "0.55",
    "legend.fancybox":   False,
    "legend.handlelength": 1.8,
    "legend.handletextpad": 0.5,
    "legend.borderpad":  0.4,
    "legend.labelspacing": 0.32,
})

MM       = 1 / 25.4
W_SINGLE = 89  * MM
W_DOUBLE = 183 * MM

CLR_SIG_DEC = "#C1440E"
CLR_SIG_INC = "#1F6FB4"
CLR_NS      = "#B8B8B8"
CLR_REG     = "#1A1A1A"
CLR_DRY     = "#E5A03A"
CLR_WET     = "#2E9E8A"


# ================================================================
# 2. Paths & stations
# ================================================================
DATA_DIR  = "data"
DAILY_CSV = os.path.join(DATA_DIR, "agera5_eto_station_daily_arco.csv")
OUT_DIR   = "outputs/module_a"
FIG_DIR   = os.path.join(OUT_DIR, "figures")
TAB_DIR   = os.path.join(OUT_DIR, "tables")
os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(TAB_DIR, exist_ok=True)

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

ALPHA = 0.05


# ================================================================
# 3. Load & aggregate — STRICT filters
# ================================================================
def load_and_aggregate():
    """
    Aggregate daily → annual / dry / wet with strict completeness rules:
      - Annual : ต้องมี ≥ 360 วัน + 12 เดือน
      - Wet    : ต้องมี ≥ 178 วัน + 6 เดือน (May–Oct)
      - Dry    : ต้องมี ≥ 178 วัน + 6 เดือน (Nov Y + Dec Y + Jan–Apr Y+1)
    """
    print("⏳ โหลดข้อมูลรายวัน...")
    df = pd.read_csv(DAILY_CSV, parse_dates=["time"])
    df["stncode"] = df["stncode"].astype(int)
    df["year"]    = df["time"].dt.year
    df["month"]   = df["time"].dt.month

    # ---- Annual ----
    ann = (df.groupby(["stncode", "year"])
             .agg(n_days=("eto_mm_day", "count"),
                  n_months=("month", "nunique"),
                  eto=("eto_mm_day", "sum"))
             .reset_index())
    ann = ann[(ann["n_days"] >= 360) & (ann["n_months"] == 12)]
    ann = ann.drop(columns=["n_days", "n_months"])
    ann = ann.rename(columns={"year": "period"})
    ann["season"] = "Annual"

    # ---- Wet: May–Oct ----
    wet = (df[df["month"].between(5, 10)]
             .groupby(["stncode", "year"])
             .agg(n_days=("eto_mm_day", "count"),
                  n_months=("month", "nunique"),
                  eto=("eto_mm_day", "sum"))
             .reset_index())
    wet = wet[(wet["n_days"] >= 178) & (wet["n_months"] == 6)]
    wet = wet.drop(columns=["n_days", "n_months"])
    wet = wet.rename(columns={"year": "period"})
    wet["season"] = "Wet"

    # ---- Dry: Nov(Y)+Dec(Y)+Jan(Y+1)+Feb(Y+1)+Mar(Y+1)+Apr(Y+1) ----
    nov_dec = df[df["month"].isin([11, 12])].copy()
    nov_dec["dry_year"] = nov_dec["year"]

    jan_apr = df[df["month"].between(1, 4)].copy()
    jan_apr["dry_year"] = jan_apr["year"] - 1

    dry = (pd.concat([nov_dec, jan_apr], ignore_index=True)
             .groupby(["stncode", "dry_year"])
             .agg(n_days=("eto_mm_day", "count"),
                  n_months=("month", "nunique"),
                  eto=("eto_mm_day", "sum"))
             .reset_index())
    # STRICT: ต้องมี 6 เดือน + 178 วัน → ตัดปี 2007 ที่ขาด Jan–Apr 2008
    dry = dry[(dry["n_days"] >= 178) & (dry["n_months"] == 6)]
    dry = dry.drop(columns=["n_days", "n_months"])
    dry = dry.rename(columns={"dry_year": "period"})
    dry["season"] = "Dry"

    df_all = pd.concat([ann, wet, dry], ignore_index=True)

    # Sanity check: แสดงช่วง period ของแต่ละ season
    for s in ["Annual", "Dry", "Wet"]:
        sub = df_all[df_all["season"] == s]
        print(f"   {s:>6}: {sub['period'].min()}–{sub['period'].max()} "
              f"({sub['period'].nunique()} ปี × {sub['stncode'].nunique()} stn = "
              f"{len(sub)} แถว)")

    return df_all


# ================================================================
# 4. MK test + Sen's slope
# ================================================================
def mann_kendall_test(x):
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) < 10:
        return None
    res = mk.original_test(x)
    slope, _, lo, hi = stats.theilslopes(x, alpha=1 - ALPHA)
    return {
        "n":            len(x),
        "tau":          float(res.Tau),
        "z":            float(res.z),
        "p_value":      float(res.p),
        "slope_mm_yr":  float(slope),
        "slope_lo":     float(lo),
        "slope_hi":     float(hi),
        "slope_mm_dec": float(slope) * 10,
        "trend":        res.trend,
        "significant":  bool(res.h),
    }


def analyze_trends(df_all, season_name):
    df_s = df_all[df_all["season"] == season_name].copy()
    rows = []
    for stn, grp in df_s.groupby("stncode"):
        grp = grp.sort_values("period")
        r = mann_kendall_test(grp["eto"].values)
        if r is None:
            continue
        r["stncode"] = int(stn)
        r["station"] = STATIONS.get(stn, str(stn))
        rows.append(r)

    regional = df_s.groupby("period")["eto"].mean().sort_index()
    r = mann_kendall_test(regional.values)
    r["stncode"] = 0
    r["station"] = "Regional mean"
    rows.append(r)

    df_res = pd.DataFrame(rows)
    df_res["season"] = season_name
    cols = ["season", "stncode", "station", "n", "slope_mm_yr",
            "slope_mm_dec", "slope_lo", "slope_hi",
            "tau", "z", "p_value", "trend", "significant"]
    return df_res[cols].sort_values("slope_mm_yr", ascending=False)


def p_to_stars(p):
    if p < 0.001:  return "***"
    if p < 0.01:   return "**"
    if p < 0.05:   return "*"
    return "n.s."


# ================================================================
# 5. Figure 1 — Annual trends
# ================================================================
def plot_fig1(df_all, results_annual):
    print("🎨 Figure 1 ...")

    df_a = df_all[df_all["season"] == "Annual"]
    regional = df_a.groupby("period")["eto"].mean().sort_index()
    years = regional.index.values
    vals  = regional.values
    rk    = mann_kendall_test(vals)

    coef = np.polyfit(years, vals, 1)
    yfit = np.polyval(coef, years)

    n     = len(years)
    resid = vals - yfit
    s_err = np.sqrt(np.sum(resid**2) / (n - 2))
    xbar  = years.mean()
    ssx   = np.sum((years - xbar)**2)
    tcrit = stats.t.ppf(0.975, n - 2)
    ci    = tcrit * s_err * np.sqrt(1/n + (years - xbar)**2 / ssx)

    fig = plt.figure(figsize=(W_DOUBLE, 85 * MM))
    gs  = GridSpec(1, 2, figure=fig, width_ratios=[1, 1.15],
                   wspace=0.30, left=0.07, right=0.985,
                   top=0.90, bottom=0.21)

    # ---- Panel a ----
    ax = fig.add_subplot(gs[0, 0])

    # ✅ FIX: เพิ่ม headroom ด้านบน-ล่างให้ legend ไม่ทับข้อมูล
    y_data_min = min(vals.min(), (yfit - ci).min())
    y_data_max = max(vals.max(), (yfit + ci).max())
    y_range    = y_data_max - y_data_min
    ax.set_ylim(y_data_min - 0.05 * y_range, y_data_max + 0.35 * y_range)

    ax.fill_between(years, yfit - ci, yfit + ci,
                    color=CLR_SIG_INC, alpha=0.18, lw=0, zorder=1,
                    label="95% CI of trend")
    ax.plot(years, vals, "o-", color=CLR_REG, lw=0.9, ms=3.5,
            mfc="white", mec=CLR_REG, mew=0.9, zorder=3,
            label="Regional mean ETo")
    ax.plot(years, yfit, "--", color=CLR_SIG_DEC, lw=1.4, zorder=2,
            label=f"Sen's slope = {rk['slope_mm_dec']:+.2f} mm dec$^{{-1}}$")

    ax.text(0.03, 0.05,
            f"Mann–Kendall: $p$ = {rk['p_value']:.3f} "
            f"({p_to_stars(rk['p_value'])})",
            transform=ax.transAxes, va="bottom", ha="left",
            fontsize=8.5,
            bbox=dict(boxstyle="round,pad=0.35",
                      facecolor="white", edgecolor="0.75", lw=0.6,
                      alpha=0.95))

    ax.set_xlabel("Year")
    ax.set_ylabel("Annual ETo (mm yr$^{-1}$)")
    ax.set_xlim(1977.5, 2008.5)
    ax.xaxis.set_major_locator(MultipleLocator(5))
    ax.xaxis.set_minor_locator(MultipleLocator(1))
    ax.yaxis.set_minor_locator(AutoMinorLocator(2))

    # Legend ที่มุมบน-ขวา พร้อม headroom
    ax.legend(loc="upper right", fontsize=7.8, borderaxespad=0.4)

    # ---- Panel b ----
    ax2 = fig.add_subplot(gs[0, 1])
    df_plot = results_annual[results_annual["station"] != "Regional mean"].copy()
    df_plot = df_plot.sort_values("slope_mm_dec", ascending=True).reset_index(drop=True)

    ypos   = np.arange(len(df_plot))
    colors = [CLR_SIG_INC if (row.significant and row.slope_mm_yr > 0)
              else CLR_SIG_DEC if (row.significant and row.slope_mm_yr < 0)
              else CLR_NS
              for _, row in df_plot.iterrows()]

    ax2.barh(ypos, df_plot["slope_mm_dec"], color=colors,
             height=0.72, edgecolor="black", linewidth=0.4, zorder=2)
    ax2.errorbar(df_plot["slope_mm_dec"], ypos,
                 xerr=[df_plot["slope_mm_dec"] - df_plot["slope_lo"] * 10,
                       df_plot["slope_hi"] * 10 - df_plot["slope_mm_dec"]],
                 fmt="none", ecolor="black", elinewidth=0.7,
                 capsize=2, capthick=0.7, zorder=3)
    ax2.axvline(0, color="black", lw=0.8, zorder=1)

    # ✅ FIX: ดาววางนอก error bar ไม่ให้ทับ
    for i, (_, row) in enumerate(df_plot.iterrows()):
        stars = p_to_stars(row["p_value"])
        if stars != "n.s.":
            x_star = row["slope_hi"] * 10 + 1.5
            ax2.text(x_star, i, stars,
                     ha="left", va="center", fontsize=10,
                     color="black", fontweight="bold", zorder=4)

    ax2.set_yticks(ypos)
    ax2.set_yticklabels(df_plot["station"], fontsize=8.5)
    ax2.set_xlabel("Sen's slope (mm dec$^{-1}$)")

    x_max_data = max(
        abs(df_plot["slope_mm_dec"]).max(),
        abs((df_plot["slope_mm_dec"] - (df_plot["slope_mm_dec"] - df_plot["slope_lo"]*10))).max(),
        abs((df_plot["slope_hi"]*10 - df_plot["slope_mm_dec"])).max(),
    )
    ax2.set_xlim(-x_max_data * 1.35, x_max_data * 1.35)
    ax2.xaxis.set_major_locator(MultipleLocator(10))
    ax2.xaxis.set_minor_locator(MultipleLocator(5))
    ax2.set_ylim(-0.6, len(df_plot) - 0.4)

    handles = [
        Patch(facecolor=CLR_SIG_INC, edgecolor="black", linewidth=0.4,
              label="Significant increase"),
        Patch(facecolor=CLR_SIG_DEC, edgecolor="black", linewidth=0.4,
              label="Significant decrease"),
        Patch(facecolor=CLR_NS, edgecolor="black", linewidth=0.4,
              label="Not significant"),
    ]
    ax2.legend(handles=handles, loc="lower right", fontsize=7.5,
               borderaxespad=0.6)

    fig.text(0.012, 0.965, "a", fontsize=14, fontweight="bold", family="serif")
    fig.text(0.485, 0.965, "b", fontsize=14, fontweight="bold", family="serif")

    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG_DIR, f"fig1_annual_trends.{ext}"))
    plt.close(fig)


# ================================================================
# 6. Figure 2 — Seasonal trends
# ================================================================
def plot_fig2(df_all, results_dry, results_wet):
    print("🎨 Figure 2 ...")

    fig = plt.figure(figsize=(W_DOUBLE, 85 * MM))
    gs  = GridSpec(1, 3, figure=fig, width_ratios=[1, 1, 0.85],
                   wspace=0.32, left=0.065, right=0.985,
                   top=0.88, bottom=0.20)

    specs = [
        ("Dry", results_dry, CLR_DRY, "Dry season (Nov–Apr)"),
        ("Wet", results_wet, CLR_WET, "Wet season (May–Oct)"),
    ]

    for i, (season, res, color, title) in enumerate(specs):
        ax = fig.add_subplot(gs[0, i])
        df_s = df_all[df_all["season"] == season]
        regional = df_s.groupby("period")["eto"].mean().sort_index()
        yrs  = regional.index.values
        vals = regional.values

        rk   = mann_kendall_test(vals)
        coef = np.polyfit(yrs, vals, 1)
        yfit = np.polyval(coef, yrs)

        n     = len(yrs)
        resid = vals - yfit
        s_err = np.sqrt(np.sum(resid**2) / (n - 2))
        xbar  = yrs.mean()
        ssx   = np.sum((yrs - xbar)**2)
        tcrit = stats.t.ppf(0.975, n - 2)
        ci    = tcrit * s_err * np.sqrt(1/n + (yrs - xbar)**2 / ssx)

        # ✅ FIX: headroom ด้านบนให้ annotation box
        y_data_min = min(vals.min(), (yfit - ci).min())
        y_data_max = max(vals.max(), (yfit + ci).max())
        y_range    = y_data_max - y_data_min
        ax.set_ylim(y_data_min - 0.05 * y_range, y_data_max + 0.30 * y_range)

        ax.fill_between(yrs, yfit - ci, yfit + ci, color=color,
                        alpha=0.20, lw=0, zorder=1)
        ax.plot(yrs, vals, "o-", color=color, lw=0.9, ms=3.5,
                mfc="white", mec=color, mew=0.9, zorder=3)
        ax.plot(yrs, yfit, "--", color="black", lw=1.2, zorder=2)

        ann_txt = (f"Sen's slope = {rk['slope_mm_dec']:+.2f} mm dec$^{{-1}}$\n"
                   f"Mann–Kendall $p$ = {rk['p_value']:.3f} "
                   f"({p_to_stars(rk['p_value'])})")
        ax.text(0.03, 0.97, ann_txt,
                transform=ax.transAxes, va="top", ha="left", fontsize=8,
                bbox=dict(boxstyle="round,pad=0.35",
                          facecolor="white", edgecolor="0.75", lw=0.6,
                          alpha=0.95))

        ax.set_xlabel("Year")
        if i == 0:
            ax.set_ylabel("Seasonal ETo (mm season$^{-1}$)")
        ax.set_xlim(1977.5, 2008.5)
        ax.xaxis.set_major_locator(MultipleLocator(5))
        ax.xaxis.set_minor_locator(MultipleLocator(1))
        ax.yaxis.set_minor_locator(AutoMinorLocator(2))
        ax.set_title(title, fontsize=9.5, pad=6)

        fig.text(0.015 + i * 0.335, 0.955,
                 chr(ord("a") + i), fontsize=14, fontweight="bold",
                 family="serif")

    # ---- Panel c ----
    ax3 = fig.add_subplot(gs[0, 2])
    labels = ["Annual", "Dry", "Wet"]
    rks = [mann_kendall_test(
              df_all[df_all["season"] == s]
                .groupby("period")["eto"].mean().sort_index().values)
           for s in labels]
    slopes = [r["slope_mm_dec"] for r in rks]
    lo_err = [(r["slope_mm_dec"] - r["slope_lo"] * 10) for r in rks]
    hi_err = [(r["slope_hi"] * 10 - r["slope_mm_dec"]) for r in rks]
    sigs   = [r["significant"] for r in rks]
    colors = [CLR_SIG_DEC if s else CLR_NS for s in sigs]

    xpos = np.arange(3)
    ax3.bar(xpos, slopes, color=colors, width=0.55,
            edgecolor="black", linewidth=0.5, zorder=2)
    ax3.errorbar(xpos, slopes, yerr=[lo_err, hi_err], fmt="none",
                 ecolor="black", elinewidth=0.9, capsize=3.5, capthick=0.9,
                 zorder=3)
    ax3.axhline(0, color="black", lw=0.8, zorder=1)

    # ✅ FIX: คำนวณ y_lim จาก error bar bounds จริง
    all_bounds = []
    for s, lo, hi in zip(slopes, lo_err, hi_err):
        all_bounds.extend([s - lo, s + hi])
    y_abs = max(abs(np.array(all_bounds))) * 1.18
    ax3.set_ylim(-y_abs, y_abs)

    # ✅ FIX: value label วางใน bar (สีขาว) สำหรับค่าที่ |slope| ≥ 2.5
    for x, s, sig in zip(xpos, slopes, sigs):
        if abs(s) >= 2.5:
            ax3.text(x, s * 0.5, f"{s:+.2f}",
                     ha="center", va="center", fontsize=9,
                     color="white", fontweight="bold", zorder=5)
        else:
            va = "bottom" if s > 0 else "top"
            off = y_abs * 0.03 * (1 if s > 0 else -1)
            ax3.text(x, s + off, f"{s:+.2f}",
                     ha="center", va=va, fontsize=8.5,
                     fontweight="bold" if sig else "normal")

    ax3.set_xticks(xpos)
    ax3.set_xticklabels(labels, fontsize=9)
    ax3.set_ylabel("Sen's slope (mm dec$^{-1}$)")
    ax3.yaxis.set_major_locator(MultipleLocator(10))
    ax3.yaxis.set_minor_locator(AutoMinorLocator(2))
    ax3.yaxis.set_major_formatter(StrMethodFormatter("{x:.0f}"))

    fig.text(0.685, 0.955, "c", fontsize=14, fontweight="bold", family="serif")

    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG_DIR, f"fig2_seasonal_trends.{ext}"))
    plt.close(fig)


# ================================================================
# Figure 3 — FINAL: annotation OUTSIDE axes, no overlap possible
# ================================================================
def plot_fig3(df_all, results_annual):
    print("🎨 Figure 3 (final) ...")
    df_a = df_all[df_all["season"] == "Annual"]
    sig_map  = results_annual.set_index("stncode")["significant"].to_dict()
    pval_map = results_annual.set_index("stncode")["p_value"].to_dict()

    # ---- Unified y-range with modest padding (annotation is outside now) ----
    y_min_data = df_a["eto"].min()
    y_max_data = df_a["eto"].max()
    y_range    = y_max_data - y_min_data
    y_min_global = y_min_data - y_range * 0.05
    y_max_global = y_max_data + y_range * 0.05

    ncol, nrow = 3, 5
    fig = plt.figure(figsize=(W_DOUBLE, 175 * MM))
    gs = GridSpec(nrow, ncol, figure=fig,
                  hspace=0.75, wspace=0.42,
                  left=0.085, right=0.985,
                  top=0.945, bottom=0.095)

    panel_letters = [chr(ord("a") + i) for i in range(15)]

    for idx, (stn, name) in enumerate(STATIONS.items()):
        row, col = idx // ncol, idx % ncol
        ax = fig.add_subplot(gs[row, col])
        df_s = df_a[df_a["stncode"] == stn].sort_values("period")
        yrs  = df_s["period"].values
        vals = df_s["eto"].values

        sig = sig_map.get(stn, False)
        line_color   = CLR_SIG_DEC if sig else CLR_REG
        marker_color = CLR_SIG_DEC if sig else "0.55"

        coef = np.polyfit(yrs, vals, 1)
        yfit = np.polyval(coef, yrs)

        ax.plot(yrs, vals, "o", color=marker_color, ms=2.8,
                mfc=marker_color, mec="none", alpha=0.85, zorder=2)
        ax.plot(yrs, yfit, "-", color=line_color,
                lw=1.2 if sig else 0.9, zorder=3)

        # ====================================================
        # ✅ KEY FIX: วาง annotation ABOVE axes (นอกกรอบ plot)
        #    ที่มุมขวาบน — ไม่มีทางทับข้อมูลเลย
        # ====================================================
        slope_dec = coef[0] * 10
        p_val = pval_map.get(stn, 1.0)
        stars = p_to_stars(p_val)
        ann_txt = f"{slope_dec:+.1f} mm dec$^{{-1}}$  {stars}"

        ax.text(0.99, 1.015, ann_txt,
                transform=ax.transAxes,
                va="bottom", ha="right",
                fontsize=7.4,
                fontweight="bold" if sig else "normal",
                color="black",
                clip_on=False)

        # ชื่อสถานีเป็น title — เว้น pad ให้ annotation มีที่
        ax.set_title(name, fontsize=8.5, pad=14,
                     fontweight="normal", family="serif")

        # ---- Axes ----
        ax.set_xlim(1977.5, 2008.5)
        ax.set_ylim(y_min_global, y_max_global)
        ax.xaxis.set_major_locator(MultipleLocator(10))
        ax.xaxis.set_minor_locator(MultipleLocator(5))
        ax.yaxis.set_major_locator(MultipleLocator(100))
        ax.yaxis.set_minor_locator(AutoMinorLocator(2))
        ax.tick_params(labelsize=7.5)

        if col == 0:
            ax.set_ylabel("ETo (mm yr$^{-1}$)", fontsize=8.5, labelpad=5)
        if row == nrow - 1:
            ax.set_xlabel("Year", fontsize=8.5, labelpad=3)

    # ====================================================
    # Panel letters — ใช้ fig.text หลัง layout สมบูรณ์
    # ====================================================
    fig.canvas.draw()
    for idx in range(15):
        ax = fig.axes[idx]
        bbox = ax.get_position()
        fig.text(
            bbox.x0 - 0.058,      # ห่างซ้ายของ axes
            bbox.y1 + 0.012,      # เหนือ axes
            panel_letters[idx],
            fontsize=11.5, fontweight="bold", family="serif",
            ha="left", va="bottom",
        )

    # ====================================================
    # Legend กลาง-ล่าง
    # ====================================================
    legend_handles = [
        plt.Line2D([], [], marker="o", linestyle="-",
                   color=CLR_REG, markerfacecolor="0.55",
                   markeredgecolor="none", markersize=4,
                   linewidth=0.9,
                   label="Not significant"),
        plt.Line2D([], [], marker="o", linestyle="-",
                   color=CLR_SIG_DEC, markerfacecolor=CLR_SIG_DEC,
                   markeredgecolor="none", markersize=4,
                   linewidth=1.2,
                   label="Significant decrease ($p$ < 0.05)"),
    ]
    fig.legend(handles=legend_handles,
               loc="lower center",
               bbox_to_anchor=(0.5, 0.008),
               ncol=2,
               fontsize=8,
               frameon=False,
               handlelength=2.0,
               columnspacing=2.5)

    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG_DIR, f"fig3_station_series.{ext}"))
    plt.close(fig)

# ================================================================
# 8. Main
# ================================================================
def main():
    print("=" * 70)
    print("Stage 2 - Module A (v3 FINAL): Trend Analysis")
    print("=" * 70)

    df_all = load_and_aggregate()

    print("\n🔬 Mann-Kendall + Sen's slope...")
    results_annual = analyze_trends(df_all, "Annual")
    results_dry    = analyze_trends(df_all, "Dry")
    results_wet    = analyze_trends(df_all, "Wet")
    results_all    = pd.concat(
        [results_annual, results_dry, results_wet], ignore_index=True)

    results_annual.to_csv(os.path.join(TAB_DIR, "trends_annual.csv"), index=False)
    results_dry.to_csv(os.path.join(TAB_DIR, "trends_dry.csv"), index=False)
    results_wet.to_csv(os.path.join(TAB_DIR, "trends_wet.csv"), index=False)
    results_all.to_csv(os.path.join(TAB_DIR, "trends_all.csv"), index=False)

    regional = results_all[results_all["stncode"] == 0].copy()
    regional.to_csv(os.path.join(TAB_DIR, "regional_trends.csv"), index=False)

    print()
    plot_fig1(df_all, results_annual)
    plot_fig2(df_all, results_dry, results_wet)
    plot_fig3(df_all, results_annual)

    print("\n" + "=" * 70)
    print("📊 Regional trends")
    print("=" * 70)
    print(regional[["season", "n", "slope_mm_dec",
                    "slope_lo", "slope_hi", "p_value",
                    "significant"]].round(3).to_string(index=False))

    print("\n📊 Significant per-station trends (p < 0.05)")
    sig = results_all[results_all["significant"] & (results_all["stncode"] != 0)]
    if len(sig) == 0:
        print("   ไม่มีสถานีใดมีแนวโน้มมีนัยสำคัญ")
    else:
        print(sig[["season", "station", "slope_mm_dec",
                   "p_value"]].round(3).to_string(index=False))

    print(f"\n📁 Figures: {os.path.abspath(FIG_DIR)}")
    print(f"📁 Tables : {os.path.abspath(TAB_DIR)}")


if __name__ == "__main__":
    main()