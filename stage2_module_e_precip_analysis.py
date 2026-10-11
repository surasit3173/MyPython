"""
Stage 2 - Module E (v2): Multi-scale Precipitation Analysis
Nature-quality figures — fixed all overlaps and inconsistencies
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
from matplotlib.lines import Line2D
from matplotlib.ticker import MultipleLocator
from matplotlib.patches import Rectangle
from scipy import stats

warnings.filterwarnings("ignore", category=FutureWarning)


# ================================================================
# 1. Plot style — Nature standard
# ================================================================
mpl.rcParams.update({
    "font.family":       "serif",
    "font.serif":        ["Times New Roman", "Times", "DejaVu Serif"],
    "mathtext.fontset":  "stix",
    "font.size":         8,
    "axes.labelsize":    8.5,
    "axes.titlesize":    9,
    "xtick.labelsize":   7.5,
    "ytick.labelsize":   7.5,
    "legend.fontsize":   7.5,
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
    "savefig.pad_inches": 0.05,
    "pdf.fonttype":      42,
    "ps.fonttype":       42,
    "legend.frameon":    True,
    "legend.framealpha": 0.95,
    "legend.edgecolor":  "0.7",
    "legend.fancybox":   False,
    "legend.borderpad":  0.35,
    "legend.labelspacing": 0.3,
    "legend.handlelength": 1.5,
    "legend.handletextpad": 0.5,
})

MM       = 1 / 25.4
W_SINGLE = 89  * MM
W_DOUBLE = 183 * MM

# Nature colorblind-safe palette
CLR_OBS   = "#1A1A1A"      # near-black
CLR_AGE   = "#C1440E"      # warm red
CLR_1TO1  = "#1F6FB4"      # blue
CLR_WET   = "#2E9E8A"      # teal
CLR_DRY   = "#E5A03A"      # amber

WET_THRESHOLD = 1.0
WET_MONTHS = [5, 6, 7, 8, 9, 10]
DRY_MONTHS = [11, 12, 1, 2, 3, 4]


# ================================================================
# 2. Paths (auto-detect + absolute)
# ================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUT_DIR  = os.path.join(BASE_DIR, "outputs", "module_e")
FIG_DIR  = os.path.join(OUT_DIR, "figures")
TAB_DIR  = os.path.join(OUT_DIR, "tables")
os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(TAB_DIR, exist_ok=True)


def _find_file(candidates):
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


OBS_FILE = _find_file([
    os.path.join(DATA_DIR, "observed_precip10sta.csv"),
    os.path.join(BASE_DIR, "observed_precip10sta.csv"),
])
AGE_DAILY_FILE = _find_file([
    os.path.join(DATA_DIR, "agera5_precip_station_daily_arco.csv"),
])

YEAR_START, YEAR_END = 1979, 2007

STATIONS = {
    352201: "Nong Khai",        353201: "Loei",
    354201: "Udon Thani",       356201: "Sakon Nakhon",
    357201: "Nakhon Phanom",    381201: "Khon Kaen",
    383201: "Mukdahan",         387401: "Kosum Phisai",
    403201: "Chaiyaphum",       405201: "Roi Et",
    407501: "Ubon Ratchathani", 431201: "Nakhon Ratchasima",
    431401: "Chok Chai",        432201: "Surin",
    432401: "Tha Tum",          436401: "Nang Rong",
}


# ================================================================
# 3. Safe save
# ================================================================
def safe_save(fig, path):
    path = os.path.abspath(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass
    try:
        fig.savefig(path)
    except OSError as e:
        print(f"   ⚠️  Save failed: {path} — {e}")
        alt = path.replace(".png", "_alt.png").replace(".pdf", "_alt.pdf")
        fig.savefig(alt)


# ================================================================
# 4. Loaders (same as v1, condensed)
# ================================================================
def load_observed():
    if OBS_FILE is None:
        print("⚠️  ไม่พบไฟล์ observed")
        return None
    print(f"📂 โหลด observed: {os.path.basename(OBS_FILE)}")

    if OBS_FILE.endswith((".xlsx", ".xls")):
        xl = pd.ExcelFile(OBS_FILE)
        df = None
        for sh in xl.sheet_names:
            tmp = pd.read_excel(OBS_FILE, sheet_name=sh)
            if len(tmp) > 100:
                df = tmp
                break
    else:
        df = pd.read_csv(OBS_FILE)

    df.columns = [str(c).strip() for c in df.columns]
    cols_lower = [c.lower() for c in df.columns]

    has_long = (any(c in cols_lower for c in ("date", "datetime", "time", "day"))
                and any(c in cols_lower for c in ("stncode", "stn", "station")))
    stn_cols = [c for c in df.columns if c.isdigit() and len(c) == 6]

    if has_long:
        date_col = next(c for c in df.columns
                        if c.lower() in ("date", "datetime", "time", "day"))
        stn_col  = next(c for c in df.columns
                        if c.lower() in ("stncode", "stn", "station"))
        prec_col = next((c for c in df.columns
                         if c.lower() in ("precip", "precipitation",
                                          "rain", "rainfall")), None)
        if prec_col is None:
            num_cols = [c for c in df.columns
                        if pd.api.types.is_numeric_dtype(df[c])
                        and c not in (date_col, stn_col)]
            prec_col = num_cols[0]
        obs = df.rename(columns={date_col: "date",
                                 stn_col: "stncode",
                                 prec_col: "precip"})
        obs["stncode"] = obs["stncode"].astype(int)
    elif len(stn_cols) >= 5:
        print(f"   format: WIDE ({len(stn_cols)} stations)")
        date_col = df.columns[0]
        df["date"] = pd.to_datetime(df[date_col], errors="coerce")
        obs = df.melt(id_vars=["date"], value_vars=stn_cols,
                      var_name="stncode", value_name="precip")
        obs["stncode"] = obs["stncode"].astype(int)
    else:
        raise ValueError(f"ไม่รู้จักรูปแบบ")

    obs = obs[["stncode", "date", "precip"]].dropna()
    obs["date"] = pd.to_datetime(obs["date"])
    obs = obs[(obs["date"].dt.year >= YEAR_START) &
              (obs["date"].dt.year <= YEAR_END)]
    print(f"   {len(obs):,} rows | {obs['stncode'].nunique()} stations")
    return obs


def load_agera5():
    if AGE_DAILY_FILE is None:
        return None
    print(f"📂 โหลด AgERA5: {os.path.basename(AGE_DAILY_FILE)}")
    df = pd.read_csv(AGE_DAILY_FILE, parse_dates=["time"])
    df = df.rename(columns={"time": "date", "precip_mm_day": "precip"})
    df["stncode"] = df["stncode"].astype(int)
    df = df[["stncode", "date", "precip"]].dropna()
    df = df[(df["date"].dt.year >= YEAR_START) &
            (df["date"].dt.year <= YEAR_END)]
    print(f"   {len(df):,} rows | {df['stncode'].nunique()} stations")
    return df


def merge_daily(obs, age):
    m = obs.merge(age, on=["stncode", "date"],
                  suffixes=("_obs", "_age"), how="inner")
    m = m.rename(columns={"precip_obs": "obs", "precip_age": "agera5"})
    m["obs"] = m["obs"].astype(float)
    m["agera5"] = m["agera5"].astype(float)
    common = sorted(set(obs["stncode"]) & set(age["stncode"]))
    m = m[m["stncode"].isin(common)]
    return m, common


# ================================================================
# 5. Metrics (same as v1)
# ================================================================
def continuous_metrics(obs, age):
    obs = np.asarray(obs, dtype=float)
    age = np.asarray(age, dtype=float)
    mask = ~(np.isnan(obs) | np.isnan(age))
    obs, age = obs[mask], age[mask]
    if len(obs) < 10:
        return None
    m_obs, m_age = float(obs.mean()), float(age.mean())
    bias = m_age - m_obs
    rmse = float(np.sqrt(np.mean((age - obs) ** 2)))
    mae  = float(np.mean(np.abs(age - obs)))
    if obs.std() > 0 and age.std() > 0:
        r, p = stats.pearsonr(obs, age)
    else:
        r, p = np.nan, np.nan
    pbias = 100 * bias / m_obs if m_obs > 0 else np.nan
    nse = (1 - np.sum((age - obs) ** 2) / np.sum((obs - m_obs) ** 2)
           if np.sum((obs - m_obs) ** 2) > 0 else np.nan)
    return {
        "n": len(obs), "mean_obs": m_obs, "mean_age": m_age,
        "sd_obs": float(obs.std()), "sd_age": float(age.std()),
        "bias": float(bias), "pbias_pct": float(pbias),
        "rmse": rmse, "mae": mae,
        "r": float(r), "r2": float(r**2) if not np.isnan(r) else np.nan,
        "p_value": float(p), "nse": float(nse),
    }


def categorical_metrics(obs, age, thr=WET_THRESHOLD):
    obs = np.asarray(obs, dtype=float)
    age = np.asarray(age, dtype=float)
    m = ~(np.isnan(obs) | np.isnan(age))
    obs, age = obs[m], age[m]
    H = int(np.sum((obs >= thr) & (age >= thr)))
    M = int(np.sum((obs >= thr) & (age <  thr)))
    F = int(np.sum((obs <  thr) & (age >= thr)))
    C = int(np.sum((obs <  thr) & (age <  thr)))
    pod = H / (H + M) if (H + M) > 0 else np.nan
    far = F / (H + F) if (H + F) > 0 else np.nan
    csi = H / (H + M + F) if (H + M + F) > 0 else np.nan
    acc = (H + C) / (H + M + F + C) if (H + M + F + C) > 0 else np.nan
    bs  = (H + F) / (H + M) if (H + M) > 0 else np.nan
    return {"hits": H, "misses": M, "false_alarms": F, "correct_neg": C,
            "pod": float(pod), "far": float(far), "csi": float(csi),
            "accuracy": float(acc), "bias_score": float(bs)}


def consecutive_days(series, threshold=1.0, wet=True):
    arr = np.asarray(series, dtype=float)
    mask = (arr >= threshold) if wet else (arr < threshold)
    max_s, cur = 0, 0
    for m in mask:
        if m:
            cur += 1
            max_s = max(max_s, cur)
        else:
            cur = 0
    return max_s


# ================================================================
# 6. Aggregation
# ================================================================
def to_monthly(daily_df):
    df = daily_df.copy()
    df["year"]  = df["date"].dt.year
    df["month"] = df["date"].dt.month
    monthly = (df.groupby(["stncode", "year", "month"])
                 .agg(obs=("obs", "sum"), agera5=("agera5", "sum"),
                      n=("obs", "count"))
                 .reset_index())
    monthly = monthly[monthly["n"] >= 25].drop(columns="n")
    monthly["date"] = pd.to_datetime(
        dict(year=monthly["year"], month=monthly["month"], day=1))
    return monthly


def to_seasonal(daily_df):
    df = daily_df.copy()
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month

    wet = df[df["month"].isin(WET_MONTHS)]
    wet_agg = (wet.groupby(["stncode", "year"])
                   .agg(obs_wet=("obs", "sum"), agera5_wet=("agera5", "sum"),
                        n_wet=("obs", "count"))
                   .reset_index())
    wet_agg = wet_agg[wet_agg["n_wet"] >= 178].drop(columns="n_wet")

    nov_dec = df[df["month"].isin([11, 12])].copy()
    nov_dec["dry_year"] = nov_dec["year"]
    jan_apr = df[df["month"].isin([1, 2, 3, 4])].copy()
    jan_apr["dry_year"] = jan_apr["year"] - 1
    dry = pd.concat([nov_dec, jan_apr], ignore_index=True)
    dry_agg = (dry.groupby(["stncode", "dry_year"])
                   .agg(obs_dry=("obs", "sum"), agera5_dry=("agera5", "sum"),
                        n_dry=("obs", "count"))
                   .reset_index()
                   .rename(columns={"dry_year": "year"}))
    dry_agg = dry_agg[dry_agg["n_dry"] >= 178].drop(columns="n_dry")
    return wet_agg, dry_agg


# ================================================================
# 7. Helpers
# ================================================================
def add_panel_letter(ax, letter, xoff=-0.14, yoff=1.05):
    ax.text(xoff, yoff, letter, transform=ax.transAxes,
            fontsize=11, fontweight="bold", family="serif",
            ha="left", va="bottom", clip_on=False)


def metric_box(ax, text, loc="lower right", pad=0.03):
    """Standard metric box with white background"""
    ha = "right" if "right" in loc else "left"
    va = "bottom" if "lower" in loc else "top"
    x = 1 - pad if ha == "right" else pad
    y = pad if va == "bottom" else 1 - pad
    ax.text(x, y, text, transform=ax.transAxes,
            ha=ha, va=va, fontsize=7,
            bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                      edgecolor="0.7", lw=0.5, alpha=0.95),
            zorder=10)


# ================================================================
# 8. Fig E1 — Daily scatter (Nature quality)
# ================================================================
def plot_daily_scatter(merged):
    print("🎨 Fig E1: Daily scatter ...")
    obs = merged["obs"].values
    age = merged["agera5"].values
    m = continuous_metrics(obs, age)

    fig, ax = plt.subplots(figsize=(W_SINGLE * 1.4, 95 * MM))
    plt.subplots_adjust(left=0.15, right=0.98, top=0.94, bottom=0.16)

    vmax = np.percentile(obs, 99.5)
    hb = ax.hexbin(obs, age, gridsize=55, bins="log", cmap="Blues",
                   mincnt=1, linewidths=0, extent=(0, vmax, 0, vmax))
    cb = fig.colorbar(hb, ax=ax, pad=0.02, fraction=0.045)
    cb.set_label("log$_{10}$(count)", fontsize=7.5)
    cb.ax.tick_params(labelsize=7)

    ax.plot([0, vmax], [0, vmax], "--", color=CLR_1TO1,
            lw=1.0, label="1:1 line", zorder=4)
    coef = np.polyfit(obs, age, 1)
    xfit = np.linspace(0, vmax, 50)
    ax.plot(xfit, np.polyval(coef, xfit), "-", color=CLR_AGE,
            lw=1.3, label=f"OLS fit ($y = {coef[0]:.2f}x + {coef[1]:.2f}$)",
            zorder=5)

    ax.set_xlim(0, vmax); ax.set_ylim(0, vmax)
    ax.set_aspect("equal")
    ax.set_xlabel("Observed precipitation (mm day$^{-1}$)")
    ax.set_ylabel("AgERA5 precipitation (mm day$^{-1}$)")

    # ✅ Metric box in scientific notation
    txt = (f"$n$ = {m['n']:,}\n"
           f"$r$ = {m['r']:.3f}\n"
           f"RMSE = {m['rmse']:.2f}\n"
           f"PBIAS = {m['pbias_pct']:+.1f}%")
    metric_box(ax, txt, "lower right")

    ax.legend(loc="upper left", fontsize=7.5, framealpha=0.95)
    ax.xaxis.set_minor_locator(MultipleLocator(vmax / 20))
    ax.yaxis.set_minor_locator(MultipleLocator(vmax / 20))

    safe_save(fig, os.path.join(FIG_DIR, "fig_e1_daily_scatter.png"))
    safe_save(fig, os.path.join(FIG_DIR, "fig_e1_daily_scatter.pdf"))
    plt.close(fig)


# ================================================================
# 9. Fig E2 — Daily time series (FIXED title overlap)
# ================================================================
def plot_daily_timeseries(merged, common):
    print("🎨 Fig E2: Daily time series ...")

    reg = merged.groupby("date")[["obs", "agera5"]].mean().reset_index()
    reg = reg.sort_values("date").reset_index(drop=True)

    fig = plt.figure(figsize=(W_DOUBLE, 110 * MM))
    gs = GridSpec(2, 1, figure=fig,
                  height_ratios=[1, 1],
                  hspace=0.30,
                  left=0.075, right=0.98,
                  top=0.94, bottom=0.09)

    # ---- Panel a: full ----
    ax = fig.add_subplot(gs[0, 0])
    obs_ma = reg["obs"].rolling(30, min_periods=15).mean()
    age_ma = reg["agera5"].rolling(30, min_periods=15).mean()

    ax.plot(reg["date"], obs_ma, "-", color=CLR_OBS, lw=0.8,
            label="Observed (30-day MA)")
    ax.plot(reg["date"], age_ma, "-", color=CLR_AGE, lw=0.8,
            alpha=0.9, label="AgERA5 (30-day MA)")

    ax.set_ylabel("Precipitation (mm day$^{-1}$)")
    ax.set_xlabel("Year")
    ax.legend(loc="upper right", ncol=2, fontsize=7.5,
              bbox_to_anchor=(1.0, 1.15))
    ax.xaxis.set_major_locator(mpl.dates.YearLocator(5))
    ax.xaxis.set_minor_locator(mpl.dates.YearLocator(1))
    add_panel_letter(ax, "a", xoff=-0.06, yoff=1.10)

    r, _ = stats.pearsonr(reg["obs"], reg["agera5"])
    rmse = np.sqrt(np.mean((reg["agera5"] - reg["obs"]) ** 2))
    metric_box(ax, f"$r$ = {r:.3f}, RMSE = {rmse:.2f} mm day$^{{-1}}$",
               "lower left")

    # ---- Panel b: zoom ----
    ax = fig.add_subplot(gs[1, 0])
    y0 = 2005
    sel = reg[(reg["date"] >= f"{y0}-01-01") &
              (reg["date"] < f"{y0+1}-01-01")].copy()

    ax.plot(sel["date"], sel["obs"], "-", color=CLR_OBS, lw=0.8,
            label="Observed")
    ax.plot(sel["date"], sel["agera5"], "-", color=CLR_AGE, lw=0.8,
            label="AgERA5")

    ax.set_ylabel("Precipitation (mm day$^{-1}$)")
    ax.set_xlabel("Month")
    ax.legend(loc="upper right", ncol=2, fontsize=7.5,
              bbox_to_anchor=(1.0, 1.15))
    ax.xaxis.set_major_locator(mpl.dates.MonthLocator())
    ax.xaxis.set_major_formatter(mpl.dates.DateFormatter("%b"))
    ax.xaxis.set_minor_locator(mpl.dates.MonthLocator(bymonthday=15))
    add_panel_letter(ax, "b", xoff=-0.06, yoff=1.10)

    # ✅ FIX: show year as text OUTSIDE axes (above)
    ax.text(0.5, 1.03, f"Zoom: {y0}", transform=ax.transAxes,
            ha="center", va="bottom", fontsize=8, style="italic")

    safe_save(fig, os.path.join(FIG_DIR, "fig_e2_daily_timeseries.png"))
    safe_save(fig, os.path.join(FIG_DIR, "fig_e2_daily_timeseries.pdf"))
    plt.close(fig)


# ================================================================
# 10. Fig E3 — Daily boxplot (FIXED shade)
# ================================================================
def plot_daily_boxplot(merged):
    print("🎨 Fig E3: Daily boxplot ...")
    df = merged.copy()
    df["month"] = df["date"].dt.month

    fig, axes = plt.subplots(1, 2, figsize=(W_DOUBLE, 78 * MM),
                             sharey=True)
    plt.subplots_adjust(wspace=0.06, left=0.075, right=0.98,
                        top=0.86, bottom=0.16)

    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # ✅ FIX: wet season shade = May-Oct
    # positions 5..10 (with minor offset)
    for ax, (col, clr, label, letter) in zip(
        axes,
        [("obs", CLR_OBS, "Observed", "a"),
         ("agera5", CLR_AGE, "AgERA5", "b")]
    ):
        # shade wet season FIRST (behind everything)
        ax.axvspan(4.5, 10.5, color="0.92", alpha=0.7, zorder=0)

        data = [df.loc[df["month"] == m, col].dropna().values
                for m in range(1, 13)]
        ax.boxplot(data, positions=np.arange(1, 13), widths=0.6,
                   patch_artist=True, showfliers=False,
                   medianprops=dict(color="black", lw=1.0),
                   whiskerprops=dict(color=clr, lw=0.8),
                   capprops=dict(color=clr, lw=0.8),
                   boxprops=dict(facecolor=clr, alpha=0.42,
                                 edgecolor=clr, lw=0.8))

        ax.set_xticks(np.arange(1, 13))
        ax.set_xticklabels(month_names, fontsize=7.5)
        ax.set_xlabel("Month")
        ax.set_title(label, pad=12, fontsize=9.5)
        add_panel_letter(ax, letter, xoff=-0.10, yoff=1.03)

    axes[0].set_ylabel("Daily precipitation (mm day$^{-1}$)")
    # ✅ Wet season label — moved to top, with white halo
    axes[0].text(7.5, axes[0].get_ylim()[1] * 0.96,
                 "Wet season", ha="center", va="top",
                 fontsize=8, style="italic", color="0.35",
                 bbox=dict(boxstyle="round,pad=0.15",
                           facecolor="white", edgecolor="none", alpha=0.7),
                 zorder=5)

    safe_save(fig, os.path.join(FIG_DIR, "fig_e3_daily_boxplot.png"))
    safe_save(fig, os.path.join(FIG_DIR, "fig_e3_daily_boxplot.pdf"))
    plt.close(fig)


# ================================================================
# 11. Fig E4 — Wet-day frequency
# ================================================================
def plot_wetday_frequency(merged):
    print("🎨 Fig E4: Wet-day frequency ...")

    bins = [1, 5, 10, 20, 50, np.inf]
    labels = ["1–5", "5–10", "10–20", "20–50", ">50"]
    obs, age = merged["obs"].values, merged["agera5"].values

    def freq(v):
        return [int(((v >= bins[i]) & (v < bins[i+1])).sum())
                for i in range(len(bins) - 1)]

    obs_c, age_c = freq(obs), freq(age)

    fig, ax = plt.subplots(figsize=(W_SINGLE * 1.5, 80 * MM))
    plt.subplots_adjust(left=0.14, right=0.98, top=0.88, bottom=0.18)

    x = np.arange(len(labels))
    w = 0.38
    ax.bar(x - w/2, obs_c, w, color=CLR_OBS, edgecolor="black",
           linewidth=0.4, label="Observed")
    ax.bar(x + w/2, age_c, w, color=CLR_AGE, edgecolor="black",
           linewidth=0.4, label="AgERA5")

    ymax = max(max(obs_c), max(age_c)) * 1.15
    ax.set_ylim(0, ymax)

    for i, (o, a) in enumerate(zip(obs_c, age_c)):
        ax.text(i - w/2, o + ymax * 0.02, f"{o:,}",
                ha="center", va="bottom", fontsize=6.5)
        ax.text(i + w/2, a + ymax * 0.02, f"{a:,}",
                ha="center", va="bottom", fontsize=6.5)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_xlabel("Precipitation intensity class (mm day$^{-1}$)")
    ax.set_ylabel("Number of wet days")
    ax.set_title("Wet-day frequency distribution", pad=6, fontsize=9.5)
    # ✅ Legend outside plot area
    ax.legend(loc="upper right", fontsize=7.5,
              bbox_to_anchor=(1.0, 1.0))
    ax.yaxis.set_major_formatter(
        mpl.ticker.FuncFormatter(lambda v, _: f"{int(v):,}"))

    safe_save(fig, os.path.join(FIG_DIR, "fig_e4_wetday_frequency.png"))
    safe_save(fig, os.path.join(FIG_DIR, "fig_e4_wetday_frequency.pdf"))
    plt.close(fig)


# ================================================================
# 12. Fig E5 — POE curve
# ================================================================
def plot_poe_curve(merged):
    print("🎨 Fig E5: POE curve ...")
    obs = merged["obs"].dropna().values
    age = merged["agera5"].dropna().values
    obs, age = obs[obs >= 0], age[age >= 0]

    fig, ax = plt.subplots(figsize=(W_SINGLE * 1.5, 82 * MM))
    plt.subplots_adjust(left=0.14, right=0.98, top=0.90, bottom=0.16)

    for v, clr, label in [(obs, CLR_OBS, "Observed"),
                          (age, CLR_AGE, "AgERA5")]:
        vs = np.sort(v)[::-1]
        poe = 100 * np.arange(1, len(vs) + 1) / (len(vs) + 1)
        ax.plot(vs, poe, "-", color=clr, lw=1.3, label=label)

    ax.set_yscale("log")
    ax.set_xscale("log")
    ax.set_xlim(0.5, 500)
    ax.set_ylim(0.001, 100)
    ax.set_xlabel("Precipitation (mm day$^{-1}$)")
    ax.set_ylabel("Probability of exceedance (%)")
    ax.set_title("Probability of exceedance", pad=6, fontsize=9.5)
    ax.legend(loc="upper right", fontsize=7.5)
    ax.grid(True, which="both", color="0.9", lw=0.5, ls=":")

    safe_save(fig, os.path.join(FIG_DIR, "fig_e5_poe_curve.png"))
    safe_save(fig, os.path.join(FIG_DIR, "fig_e5_poe_curve.pdf"))
    plt.close(fig)


# ================================================================
# 13. Fig E6 — Monthly time series
# ================================================================
def plot_monthly_timeseries(monthly):
    print("🎨 Fig E6: Monthly time series ...")
    reg = monthly.groupby("date")[["obs", "agera5"]].mean().reset_index()
    reg = reg.sort_values("date").reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(W_DOUBLE, 72 * MM))
    plt.subplots_adjust(left=0.075, right=0.98, top=0.90, bottom=0.16)

    ax.plot(reg["date"], reg["obs"], "o-", color=CLR_OBS,
            ms=2.5, lw=0.8, mfc="white", mec=CLR_OBS, mew=0.6,
            label="Observed")
    ax.plot(reg["date"], reg["agera5"], "s--", color=CLR_AGE,
            ms=2.5, lw=0.8, mfc="white", mec=CLR_AGE, mew=0.6,
            label="AgERA5")

    r, _ = stats.pearsonr(reg["obs"], reg["agera5"])
    rmse = np.sqrt(np.mean((reg["agera5"] - reg["obs"]) ** 2))
    metric_box(ax, f"$r$ = {r:.3f}\nRMSE = {rmse:.1f} mm month$^{{-1}}$",
               "upper right")

    ax.set_xlabel("Year")
    ax.set_ylabel("Monthly precipitation (mm month$^{-1}$)")
    ax.set_title("Regional mean monthly precipitation (1979–2007)",
                 pad=6, fontsize=9.5)
    ax.legend(loc="upper left", ncol=2, fontsize=7.5)
    ax.xaxis.set_major_locator(mpl.dates.YearLocator(5))
    ax.xaxis.set_minor_locator(mpl.dates.YearLocator(1))

    safe_save(fig, os.path.join(FIG_DIR, "fig_e6_monthly_timeseries.png"))
    safe_save(fig, os.path.join(FIG_DIR, "fig_e6_monthly_timeseries.pdf"))
    plt.close(fig)


# ================================================================
# 14. Fig E7 — Monthly climatology (FIXED label position)
# ================================================================
def plot_monthly_climatology(monthly):
    print("🎨 Fig E7: Monthly climatology ...")
    df = monthly.copy()
    df["month"] = df["date"].dt.month

    clim = (df.groupby("month")
              .agg(mean_obs=("obs", "mean"), mean_age=("agera5", "mean"),
                   sd_obs=("obs", "std"), sd_age=("agera5", "std"))
              .reset_index())

    fig, ax = plt.subplots(figsize=(W_SINGLE * 1.8, 78 * MM))
    plt.subplots_adjust(left=0.13, right=0.98, top=0.88, bottom=0.18)

    # Wet season shading
    ax.axvspan(4.5, 10.5, color="0.94", alpha=0.6, zorder=0)

    x = clim["month"].values
    ax.errorbar(x - 0.10, clim["mean_obs"], yerr=clim["sd_obs"],
                fmt="o-", color=CLR_OBS, ms=5, lw=1.2,
                capsize=2.5, capthick=0.7, mfc="white", mec=CLR_OBS,
                mew=1.0, label="Observed", zorder=5)
    ax.errorbar(x + 0.10, clim["mean_age"], yerr=clim["sd_age"],
                fmt="s--", color=CLR_AGE, ms=5, lw=1.2,
                capsize=2.5, capthick=0.7, mfc="white", mec=CLR_AGE,
                mew=1.0, label="AgERA5", zorder=5)

    ax.set_xticks(x)
    ax.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    ax.set_xlabel("Month")
    ax.set_ylabel("Precipitation (mm month$^{-1}$)")
    ax.set_title("Monthly precipitation climatology", pad=6, fontsize=9.5)
    ax.legend(loc="upper left", fontsize=7.5)

    # ✅ Wet season label INSIDE shaded region but with white halo
    ymax = ax.get_ylim()[1]
    ax.text(7.5, ymax * 0.97, "Wet season",
            ha="center", va="top", fontsize=8, style="italic",
            color="0.35", zorder=6,
            bbox=dict(boxstyle="round,pad=0.15",
                      facecolor="white", edgecolor="none", alpha=0.75))

    safe_save(fig, os.path.join(FIG_DIR, "fig_e7_monthly_clim.png"))
    safe_save(fig, os.path.join(FIG_DIR, "fig_e7_monthly_clim.pdf"))
    plt.close(fig)


# ================================================================
# 15. Fig E8 — Monthly metrics bar chart
# ================================================================
def plot_monthly_metrics(metrics_df, unit, fname_prefix):
    print(f"🎨 Fig {fname_prefix}: metrics bar chart ...")
    df = metrics_df[metrics_df["stncode"] != 0].copy()
    df = df.sort_values("r", ascending=True).reset_index(drop=True)

    fig, axes = plt.subplots(1, 3, figsize=(W_DOUBLE, 84 * MM),
                             sharey=True)
    plt.subplots_adjust(wspace=0.06, left=0.20, right=0.98,
                        top=0.86, bottom=0.16)

    ypos = np.arange(len(df))

    # ---- Panel a: r ----
    ax = axes[0]
    ax.barh(ypos, df["r"], color=CLR_1TO1, edgecolor="black",
            linewidth=0.4, height=0.7)
    for i, v in enumerate(df["r"]):
        ax.text(v + 0.01, i, f"{v:.2f}", va="center", ha="left",
                fontsize=7)
    ax.set_yticks(ypos)
    ax.set_yticklabels(df["station"], fontsize=7.5)
    ax.set_xlabel("Pearson $r$")
    ax.set_xlim(0, 1.0)
    ax.xaxis.set_minor_locator(MultipleLocator(0.1))
    ax.set_title("Correlation", pad=6, fontsize=9.5)
    add_panel_letter(ax, "a", xoff=-0.42, yoff=1.03)

    # ---- Panel b: RMSE ----
    ax = axes[1]
    ax.barh(ypos, df["rmse"], color=CLR_AGE, edgecolor="black",
            linewidth=0.4, height=0.7)
    for i, v in enumerate(df["rmse"]):
        ax.text(v + max(df["rmse"]) * 0.02, i, f"{v:.1f}",
                va="center", ha="left", fontsize=7)
    ax.set_xlabel(f"RMSE ({unit})")
    ax.set_title("RMSE", pad=6, fontsize=9.5)
    add_panel_letter(ax, "b", xoff=-0.10, yoff=1.03)

    # ---- Panel c: PBIAS ----
    ax = axes[2]
    colors = ["#C1440E" if v < 0 else "#1F6FB4"
              for v in df["pbias_pct"]]
    ax.barh(ypos, df["pbias_pct"], color=colors, edgecolor="black",
            linewidth=0.4, height=0.7)
    ax.axvline(0, color="black", lw=0.8)
    xr = max(abs(df["pbias_pct"])) * 1.35
    ax.set_xlim(-xr, xr)
    for i, v in enumerate(df["pbias_pct"]):
        off = xr * 0.04
        ax.text(v + (off if v > 0 else -off), i, f"{v:+.0f}%",
                va="center", ha="left" if v > 0 else "right",
                fontsize=7)
    ax.set_xlabel("PBIAS (%)")
    ax.set_title("Percent bias", pad=6, fontsize=9.5)
    add_panel_letter(ax, "c", xoff=-0.10, yoff=1.03)

    safe_save(fig, os.path.join(FIG_DIR, f"{fname_prefix}.png"))
    safe_save(fig, os.path.join(FIG_DIR, f"{fname_prefix}.pdf"))
    plt.close(fig)


# ================================================================
# 16. Fig E9 — Seasonal comparison (FIXED legend + scale)
# ================================================================
def plot_seasonal_comparison(wet_agg, dry_agg, common):
    """Fig E9: Seasonal comparison — Nature quality (v2.2 FINAL)"""
    print("🎨 Fig E9: Seasonal comparison ...")

    wet_stn = (wet_agg.groupby("stncode")
                 .agg(obs=("obs_wet", "mean"), age=("agera5_wet", "mean"))
                 .reset_index())
    dry_stn = (dry_agg.groupby("stncode")
                 .agg(obs=("obs_dry", "mean"), age=("agera5_dry", "mean"))
                 .reset_index())

    wet_stn["station"] = wet_stn["stncode"].map(STATIONS)
    dry_stn["station"] = dry_stn["stncode"].map(STATIONS)

    # Sort by observed wet total (same order both panels)
    wet_stn = wet_stn.sort_values("obs", ascending=True).reset_index(drop=True)
    order = wet_stn["stncode"].values
    dry_stn = (dry_stn.set_index("stncode").reindex(order).reset_index())
    dry_stn["station"] = dry_stn["stncode"].map(STATIONS)

    # ✅ Reserve MORE bottom space for shared legend
    fig, axes = plt.subplots(1, 2, figsize=(W_DOUBLE, 100 * MM))
    plt.subplots_adjust(wspace=0.48, left=0.14, right=0.98,
                        top=0.90, bottom=0.18)   # ← bottom เพิ่มเป็น 0.18

    from matplotlib.patches import Patch

    for ax, (df, season_label, letter) in zip(
        axes,
        [(wet_stn, "Wet season (May–Oct)", "a"),
         (dry_stn, "Dry season (Nov–Apr)", "b")]
    ):
        ypos = np.arange(len(df))
        h = 0.38
        xmax_data = max(df["obs"].max(), df["age"].max())
        x_axis_max = xmax_data * 1.18
        ax.set_xlim(0, x_axis_max)

        ax.barh(ypos - h/2, df["obs"], h, color=CLR_OBS,
                edgecolor="black", linewidth=0.4, zorder=3)
        ax.barh(ypos + h/2, df["age"], h, color=CLR_AGE,
                edgecolor="black", linewidth=0.4, zorder=3)

        # PBIAS separator
        x_sep = xmax_data * 1.04
        ax.axvline(x_sep, color="0.75", lw=0.6, linestyle="-", zorder=2)

        # PBIAS values
        for i, (o, a) in enumerate(zip(df["obs"], df["age"])):
            pct = 100 * (a - o) / o if o > 0 else np.nan
            color = "#C1440E" if pct < 0 else "#1F6FB4"
            ax.text(x_sep + xmax_data * 0.03, i, f"{pct:+.0f}%",
                    va="center", ha="left", fontsize=7,
                    color=color, fontweight="normal")

        # PBIAS header
        ax.text(x_sep + xmax_data * 0.03, len(df) - 0.3, "PBIAS",
                va="bottom", ha="left", fontsize=6.5,
                color="0.35", style="italic")

        ax.set_yticks(ypos)
        ax.set_yticklabels(df["station"], fontsize=7.5)
        ax.set_xlabel(r"Seasonal precipitation (mm season$^{-1}$)")
        ax.set_title(season_label, pad=8, fontsize=9.5)
        ax.set_ylim(-0.6, len(df) - 0.1)

        # ✅ Panel letter at top-left (no conflict with title)
        add_panel_letter(ax, letter, xoff=-0.16, yoff=1.05)

    # ✅ SHARED legend at figure bottom (no collision possible)
    shared_handles = [
        Patch(facecolor=CLR_OBS, edgecolor="black",
              linewidth=0.4, label="Observed"),
        Patch(facecolor=CLR_AGE, edgecolor="black",
              linewidth=0.4, label="AgERA5"),
    ]
    fig.legend(handles=shared_handles,
               loc="lower center",
               bbox_to_anchor=(0.5, 0.005),
               ncol=2,
               fontsize=8,
               frameon=False,
               handlelength=1.5,
               columnspacing=2.5,
               handletextpad=0.6)

    safe_save(fig, os.path.join(FIG_DIR, "fig_e9_seasonal_comparison.png"))
    safe_save(fig, os.path.join(FIG_DIR, "fig_e9_seasonal_comparison.pdf"))
    plt.close(fig)
# ================================================================
# 17. Fig E10 — Seasonal metrics (FIXED title overlap)
# ================================================================
def plot_seasonal_metrics(metrics_wet, metrics_dry):
    print("🎨 Fig E10: Seasonal metrics ...")

    wet_r = metrics_wet[metrics_wet["stncode"] == 0].iloc[0]
    dry_r = metrics_dry[metrics_dry["stncode"] == 0].iloc[0]

    fig, axes = plt.subplots(1, 3, figsize=(W_DOUBLE, 78 * MM))
    plt.subplots_adjust(wspace=0.38, left=0.09, right=0.98,
                        top=0.82, bottom=0.16)

    seasons = ["Dry", "Wet"]
    colors = [CLR_DRY, CLR_WET]

    # ---- Panel a: r ----
    ax = axes[0]
    vals = [dry_r["r"], wet_r["r"]]
    ax.bar([0, 1], vals, color=colors, edgecolor="black",
           linewidth=0.5, width=0.55)
    ax.set_ylim(0, max(vals) * 1.25)
    for i, v in enumerate(vals):
        ax.text(i, v + max(vals) * 0.03, f"{v:.3f}",
                ha="center", va="bottom", fontsize=8)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(seasons)
    ax.set_ylabel("Pearson $r$")
    ax.set_title("Correlation", pad=10, fontsize=9.5)
    add_panel_letter(ax, "a", xoff=-0.18, yoff=1.10)

    # ---- Panel b: RMSE ----
    ax = axes[1]
    vals = [dry_r["rmse"], wet_r["rmse"]]
    ax.bar([0, 1], vals, color=colors, edgecolor="black",
           linewidth=0.5, width=0.55)
    ax.set_ylim(0, max(vals) * 1.20)
    for i, v in enumerate(vals):
        ax.text(i, v + max(vals) * 0.03, f"{v:.1f}",
                ha="center", va="bottom", fontsize=8)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(seasons)
    ax.set_ylabel("RMSE (mm season$^{-1}$)")
    ax.set_title("RMSE", pad=10, fontsize=9.5)
    add_panel_letter(ax, "b", xoff=-0.10, yoff=1.10)

    # ---- Panel c: PBIAS ----
    ax = axes[2]
    vals = [dry_r["pbias_pct"], wet_r["pbias_pct"]]
    # ✅ All positive — same color logic
    bar_colors = ["#C1440E" if v < 0 else "#1F6FB4" for v in vals]
    ax.bar([0, 1], vals, color=bar_colors, edgecolor="black",
           linewidth=0.5, width=0.55)
    ax.set_ylim(0, max(vals) * 1.30)
    for i, v in enumerate(vals):
        ax.text(i, v + max(vals) * 0.03, f"{v:+.1f}%",
                ha="center", va="bottom", fontsize=8)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(seasons)
    ax.set_ylabel("PBIAS (%)")
    ax.set_title("Percent bias", pad=10, fontsize=9.5)
    add_panel_letter(ax, "c", xoff=-0.10, yoff=1.10)

    safe_save(fig, os.path.join(FIG_DIR, "fig_e10_seasonal_metrics.png"))
    safe_save(fig, os.path.join(FIG_DIR, "fig_e10_seasonal_metrics.pdf"))
    plt.close(fig)


# ================================================================
# 18. Main
# ================================================================
def main():
    print("=" * 70)
    print("Stage 2 - Module E (v2): Multi-scale Precipitation Analysis")
    print("=" * 70)

    obs = load_observed()
    age = load_agera5()
    if obs is None or age is None:
        return

    merged, common = merge_daily(obs, age)
    if len(merged) == 0:
        return

    print(f"\n📊 จำนวนสถานีที่ตรงกัน: {len(common)}")

    # ---- 1. Daily ----
    print("\n" + "=" * 70)
    print("📌 1. DAILY ANALYSIS")
    print("=" * 70)

    daily_rows = []
    for stn in common:
        sub = merged[merged["stncode"] == stn]
        m = continuous_metrics(sub["obs"].values, sub["agera5"].values)
        m["stncode"] = int(stn)
        m["station"] = STATIONS.get(stn, str(stn))
        daily_rows.append(m)

    daily_all = continuous_metrics(merged["obs"].values,
                                    merged["agera5"].values)
    daily_all["stncode"] = 0
    daily_all["station"] = "ALL STATIONS"
    daily_rows.append(daily_all)

    daily_metrics = pd.DataFrame(daily_rows)
    cols = ["stncode", "station", "n", "mean_obs", "mean_age",
            "sd_obs", "sd_age", "bias", "pbias_pct",
            "rmse", "mae", "r", "r2", "nse"]
    daily_metrics = daily_metrics[cols]
    daily_metrics.to_csv(os.path.join(TAB_DIR, "table_e1_daily_metrics.csv"),
                          index=False, float_format="%.3f")

    cat_rows = []
    for stn in common:
        sub = merged[merged["stncode"] == stn]
        c = categorical_metrics(sub["obs"].values, sub["agera5"].values)
        c["stncode"] = int(stn)
        c["station"] = STATIONS.get(stn, str(stn))
        cat_rows.append(c)
    cat_all = categorical_metrics(merged["obs"].values, merged["agera5"].values)
    cat_all["stncode"] = 0
    cat_all["station"] = "ALL STATIONS"
    cat_rows.append(cat_all)

    cat_df = pd.DataFrame(cat_rows)[[
        "stncode", "station", "hits", "misses", "false_alarms",
        "correct_neg", "pod", "far", "csi", "accuracy", "bias_score"]]
    cat_df.to_csv(os.path.join(TAB_DIR, "table_e2_daily_categorical.csv"),
                   index=False, float_format="%.3f")

    cdd_rows = []
    for stn in common:
        sub = merged[merged["stncode"] == stn].sort_values("date")
        cdd_rows.append({
            "stncode": int(stn),
            "station": STATIONS.get(stn, str(stn)),
            "CDD_obs": consecutive_days(sub["obs"].values, wet=False),
            "CDD_age": consecutive_days(sub["agera5"].values, wet=False),
            "CWD_obs": consecutive_days(sub["obs"].values, wet=True),
            "CWD_age": consecutive_days(sub["agera5"].values, wet=True),
        })
    pd.DataFrame(cdd_rows).to_csv(
        os.path.join(TAB_DIR, "table_e3_consecutive_days.csv"), index=False)

    plot_daily_scatter(merged)
    plot_daily_timeseries(merged, common)
    plot_daily_boxplot(merged)
    plot_wetday_frequency(merged)
    plot_poe_curve(merged)

    # ---- 2. Monthly ----
    print("\n" + "=" * 70)
    print("📌 2. MONTHLY ANALYSIS")
    print("=" * 70)

    monthly = to_monthly(merged)
    print(f"   {len(monthly):,} station-months")

    monthly_rows = []
    for stn in common:
        sub = monthly[monthly["stncode"] == stn]
        m = continuous_metrics(sub["obs"].values, sub["agera5"].values)
        m["stncode"] = int(stn)
        m["station"] = STATIONS.get(stn, str(stn))
        monthly_rows.append(m)

    monthly_all = continuous_metrics(monthly["obs"].values,
                                      monthly["agera5"].values)
    monthly_all["stncode"] = 0
    monthly_all["station"] = "ALL STATIONS"
    monthly_rows.append(monthly_all)

    monthly_metrics = pd.DataFrame(monthly_rows)[cols]
    monthly_metrics.to_csv(os.path.join(TAB_DIR, "table_e4_monthly_metrics.csv"),
                            index=False, float_format="%.3f")

    monthly["month"] = monthly["date"].dt.month
    clim = (monthly.groupby("month")
                   .agg(mean_obs=("obs", "mean"), mean_age=("agera5", "mean"),
                        sd_obs=("obs", "std"), sd_age=("agera5", "std"))
                   .reset_index())
    clim["bias"] = clim["mean_age"] - clim["mean_obs"]
    clim["pbias_pct"] = 100 * clim["bias"] / clim["mean_obs"]
    clim["month_name"] = clim["month"].map(
        {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
         7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"})
    clim.to_csv(os.path.join(TAB_DIR, "table_e5_monthly_climatology.csv"),
                index=False, float_format="%.3f")

    plot_monthly_timeseries(monthly)
    plot_monthly_climatology(monthly)
    plot_monthly_metrics(monthly_metrics, "mm month$^{-1}$",
                         "fig_e8_monthly_metrics")

    # ---- 3. Seasonal ----
    print("\n" + "=" * 70)
    print("📌 3. SEASONAL ANALYSIS (Wet/Dry)")
    print("=" * 70)

    wet_agg, dry_agg = to_seasonal(merged)
    print(f"   Wet: {len(wet_agg)} station-years | Dry: {len(dry_agg)} station-years")

    def seasonal_metrics(agg_df, obs_col, age_col, season):
        rows = []
        for stn in sorted(agg_df["stncode"].unique()):
            sub = agg_df[agg_df["stncode"] == stn]
            m = continuous_metrics(sub[obs_col].values, sub[age_col].values)
            if m is None:
                continue
            m["stncode"] = int(stn)
            m["station"] = STATIONS.get(stn, str(stn))
            m["season"] = season
            rows.append(m)
        m_all = continuous_metrics(agg_df[obs_col].values, agg_df[age_col].values)
        m_all["stncode"] = 0
        m_all["station"] = "ALL STATIONS"
        m_all["season"] = season
        rows.append(m_all)
        return pd.DataFrame(rows)

    wet_metrics = seasonal_metrics(wet_agg, "obs_wet", "agera5_wet", "Wet")
    dry_metrics = seasonal_metrics(dry_agg, "obs_dry", "agera5_dry", "Dry")
    seasonal_df = pd.concat([wet_metrics, dry_metrics], ignore_index=True)
    seasonal_df = seasonal_df[["season"] + cols]
    seasonal_df.to_csv(os.path.join(TAB_DIR, "table_e6_seasonal_metrics.csv"),
                        index=False, float_format="%.3f")

    for label, agg, obs_c, age_c in [("wet", wet_agg, "obs_wet", "agera5_wet"),
                                      ("dry", dry_agg, "obs_dry", "agera5_dry")]:
        stn_tbl = (agg.groupby("stncode")
                      .agg(obs_mean=(obs_c, "mean"), age_mean=(age_c, "mean"),
                           obs_std=(obs_c, "std"), age_std=(age_c, "std"))
                      .reset_index())
        stn_tbl["station"] = stn_tbl["stncode"].map(STATIONS)
        stn_tbl["season"] = label.capitalize()
        stn_tbl["bias"] = stn_tbl["age_mean"] - stn_tbl["obs_mean"]
        stn_tbl["pbias_pct"] = 100 * stn_tbl["bias"] / stn_tbl["obs_mean"]
        stn_tbl.to_csv(
            os.path.join(TAB_DIR, f"table_e7_seasonal_{label}_means.csv"),
            index=False, float_format="%.2f")

    plot_seasonal_comparison(wet_agg, dry_agg, common)
    plot_seasonal_metrics(wet_metrics, dry_metrics)

    # ---- Summary ----
    print("\n" + "=" * 70)
    print("📊 สรุปผล")
    print("=" * 70)

    d_all = daily_metrics[daily_metrics["stncode"] == 0].iloc[0]
    print(f"\n📌 Daily (n = {int(d_all['n']):,}):")
    print(f"   Mean obs = {d_all['mean_obs']:.3f} | "
          f"Mean AgERA5 = {d_all['mean_age']:.3f} mm/day")
    print(f"   Bias = {d_all['bias']:+.3f} ({d_all['pbias_pct']:+.1f}%) | "
          f"RMSE = {d_all['rmse']:.3f} | r = {d_all['r']:.3f}")
    print(f"   POD = {cat_all['pod']:.3f} | FAR = {cat_all['far']:.3f} | "
          f"CSI = {cat_all['csi']:.3f}")

    m_all = monthly_metrics[monthly_metrics["stncode"] == 0].iloc[0]
    print(f"\n📌 Monthly (n = {len(monthly):,}):")
    print(f"   r = {m_all['r']:.3f} | RMSE = {m_all['rmse']:.1f} mm/month | "
          f"PBIAS = {m_all['pbias_pct']:+.1f}%")

    wet_all = wet_metrics[wet_metrics["stncode"] == 0].iloc[0]
    dry_all = dry_metrics[dry_metrics["stncode"] == 0].iloc[0]
    print(f"\n📌 Seasonal:")
    print(f"   Wet — r = {wet_all['r']:.3f} | RMSE = {wet_all['rmse']:.1f} | "
          f"PBIAS = {wet_all['pbias_pct']:+.1f}%")
    print(f"   Dry — r = {dry_all['r']:.3f} | RMSE = {dry_all['rmse']:.1f} | "
          f"PBIAS = {dry_all['pbias_pct']:+.1f}%")

    print(f"\n📁 Tables : {os.path.abspath(TAB_DIR)}")
    print(f"📁 Figures: {os.path.abspath(FIG_DIR)}")
    print("=" * 70)


if __name__ == "__main__":
    main()