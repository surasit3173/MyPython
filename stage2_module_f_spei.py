"""
Stage 2 - Module F: SPEI Drought Characterization (v2 FINAL)
NE Thailand, 15 stations, 1979-2007

SPEI (Standardized Precipitation-Evapotranspiration Index)
  - Vicente-Serrano et al. (2010), J. Climate
  - Water balance: D = P - ETo
  - Timescales: SPEI-1, SPEI-3, SPEI-6, SPEI-12
  - Log-logistic distribution fitted via MLE (scipy.stats.fisk)

Q2 journal level - Times New Roman, 600 dpi
All overlaps fixed, star markers colored, verification included
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
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from scipy import stats
from scipy.stats import fisk

try:
    import pymannkendall as mk
except ImportError:
    print("pip install pymannkendall")
    sys.exit(1)

warnings.filterwarnings("ignore", category=FutureWarning)


# ================================================================
# 1. Plot style — Q2 journal
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
    "xtick.direction":   "out",
    "ytick.direction":   "out",
    "figure.dpi":        200,
    "savefig.dpi":       400,
    "savefig.bbox":      "tight",
    "savefig.pad_inches": 0.06,
    "pdf.fonttype":      42,
})

MM       = 1 / 25.4
W_SINGLE = 89  * MM
W_DOUBLE = 183 * MM

SPEI_CATEGORIES = [
    ("Extremely dry",    -np.inf, -2.0, "#8C1F0E"),
    ("Severely dry",     -2.0,    -1.5, "#D97B29"),
    ("Moderately dry",   -1.5,    -1.0, "#F2C265"),
    ("Near normal",      -1.0,     1.0, "#F5F0DC"),
    ("Moderately wet",    1.0,     1.5, "#88BBD7"),
    ("Severely wet",      1.5,     2.0, "#3B7BB1"),
    ("Extremely wet",     2.0,   np.inf, "#0D4A78"),
]

# Theoretical SPEI distribution (for verification)
SPEI_THEORETICAL = {
    "Extremely dry":  2.28,
    "Severely dry":   4.40,
    "Moderately dry": 9.19,
    "Near normal":   68.27,
    "Moderately wet": 9.19,
    "Severely wet":   4.40,
    "Extremely wet":  2.28,
}


# ================================================================
# 2. Paths & config
# ================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUT_DIR  = os.path.join(BASE_DIR, "outputs", "module_f")
FIG_DIR  = os.path.join(OUT_DIR, "figures")
TAB_DIR  = os.path.join(OUT_DIR, "tables")
os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(TAB_DIR, exist_ok=True)

ETO_CSV  = os.path.join(DATA_DIR, "agera5_eto_station_daily_arco.csv")
PREC_CSV = os.path.join(DATA_DIR, "agera5_precip_station_daily_arco.csv")

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

STN_COORDS = {
    352201: (17.863, 102.752),  353201: (17.448, 101.732),
    354201: (17.383, 102.800),  356201: (17.151, 104.137),
    357201: (17.410, 104.782),  381201: (16.457, 102.790),
    383201: (16.542, 104.729),  387401: (16.241, 103.070),
    403201: (15.807, 102.030),  405201: (16.052, 103.664),
    407501: (15.242, 104.876),  431201: (14.963, 102.087),
    431401: (14.733, 102.170),  432201: (14.872, 103.500),
    432401: (15.315, 103.681),  436401: (14.627, 102.723),
}

# Abbreviated names for spatial plot
STN_ABBR = {
    "Nakhon Ratchasima": "Nakhon Rat.",
    "Ubon Ratchathani":  "Ubon Rat.",
    "Sakon Nakhon":      "Sakon Nakh.",
    "Nakhon Phanom":     "Nakhon Pha.",
    "Kosum Phisai":      "Kosum Ph.",
}

# Manual label offsets for spatial plot (prevent overlap)
SPATIAL_OFFSETS = {
    352201: (0, -15),    # Nong Khai
    353201: (0, -15),    # Loei
    354201: (15, 5),     # Udon Thani
    356201: (15, -5),    # Sakon Nakhon
    357201: (15, -5),    # Nakhon Phanom
    381201: (0, -15),    # Khon Kaen
    383201: (15, -5),    # Mukdahan
    387401: (0, -15),    # Kosum Phisai
    403201: (0, -15),    # Chaiyaphum
    405201: (15, -5),    # Roi Et
    407501: (15, -5),    # Ubon Ratchathani
    431201: (-20, 10),   # Nakhon Ratchasima (ไปซ้าย-บน)
    431401: (25, -5),    # Chok Chai (ไปขวา)
    436401: (10, -18),   # Nang Rong (ไปล่าง-ขวา)
    432201: (-25, -10),  # Surin (ไปซ้าย-ล่าง)
    432401: (15, -5),    # Tha Tum
}

TIMESCALES = [1, 3, 6, 12]
YEAR_START, YEAR_END = 1979, 2007


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
        alt = path.replace(".png", "_alt.png")
        fig.savefig(alt)


def add_panel_letter(ax, letter, xoff=-0.14, yoff=1.05):
    ax.text(xoff, yoff, letter, transform=ax.transAxes,
            fontsize=12, fontweight="bold", family="serif",
            ha="left", va="bottom", clip_on=False)


# ================================================================
# 3. Data loading
# ================================================================
def load_monthly_eto_precip():
    print("📂 โหลดข้อมูล ETo + Precip ...")

    eto = pd.read_csv(ETO_CSV, parse_dates=["time"])
    eto = eto.rename(columns={"time": "date", "eto_mm_day": "eto"})
    eto["stncode"] = eto["stncode"].astype(int)

    prec = pd.read_csv(PREC_CSV, parse_dates=["time"])
    prec = prec.rename(columns={"time": "date", "precip_mm_day": "precip"})
    prec["stncode"] = prec["stncode"].astype(int)

    common = sorted(set(eto["stncode"]) & set(prec["stncode"]))
    eto = eto[eto["stncode"].isin(common)]
    prec = prec[prec["stncode"].isin(common)]
    print(f"   Common stations: {len(common)}")

    # Monthly aggregation
    eto["year"] = eto["date"].dt.year
    eto["month"] = eto["date"].dt.month
    eto_m = (eto.groupby(["stncode", "year", "month"])
                .agg(eto=("eto", "sum"), n_eto=("eto", "count"))
                .reset_index())
    eto_m = eto_m[eto_m["n_eto"] >= 25].drop(columns="n_eto")

    prec["year"] = prec["date"].dt.year
    prec["month"] = prec["date"].dt.month
    prec_m = (prec.groupby(["stncode", "year", "month"])
                   .agg(precip=("precip", "sum"), n_prec=("precip", "count"))
                   .reset_index())
    prec_m = prec_m[prec_m["n_prec"] >= 25].drop(columns="n_prec")

    df = eto_m.merge(prec_m, on=["stncode", "year", "month"], how="inner")
    df = df.sort_values(["stncode", "year", "month"]).reset_index(drop=True)
    df["date"] = pd.to_datetime(
        dict(year=df["year"], month=df["month"], day=1))

    print(f"   {len(df):,} station-months | "
          f"{df['year'].min()}–{df['year'].max()}")
    return df


# ================================================================
# 4. SPEI distribution fitting (MLE via scipy.stats.fisk)
# ================================================================
def fit_spei_distribution(data):
    """Fit 3-parameter log-logistic via MLE (supports negative values)"""
    data = np.asarray(data, dtype=float)
    data = data[np.isfinite(data)]
    if len(data) < 10:
        return None
    if np.std(data) < 1e-6:
        return None

    try:
        c, loc, scale = fisk.fit(data)
        if not (np.isfinite(c) and 0.01 < c < 100):
            return None
        if not (np.isfinite(scale) and scale > 0):
            return None
        return {"c": float(c), "loc": float(loc), "scale": float(scale)}
    except Exception:
        return None


def spei_from_distribution(data, fit):
    """Convert water balance D → SPEI via standard normal"""
    data = np.asarray(data, dtype=float)
    if fit is None:
        return np.full_like(data, np.nan)
    c = fit["c"]
    loc = fit["loc"]
    scale = fit["scale"]
    with np.errstate(all="ignore"):
        F = fisk.cdf(data, c, loc=loc, scale=scale)
    F = np.clip(F, 1e-6, 1 - 1e-6)
    return stats.norm.ppf(F)


def compute_spei_for_series(series, month_labels, timescale=1):
    """Compute SPEI for a single station at one timescale"""
    n = len(series)
    spei = np.full(n, np.nan)

    if timescale == 1:
        D_k = series.copy()
        valid_idx = np.ones(n, dtype=bool)
    else:
        D_k = np.full(n, np.nan)
        for i in range(timescale - 1, n):
            D_k[i] = np.sum(series[i - timescale + 1:i + 1])
        valid_idx = np.arange(n) >= (timescale - 1)

    for m in range(1, 13):
        mask = (month_labels == m) & valid_idx & np.isfinite(D_k)
        if mask.sum() < 10:
            continue
        fit = fit_spei_distribution(D_k[mask])
        if fit is None:
            continue
        spei[mask] = spei_from_distribution(D_k[mask], fit)

    spei = np.clip(spei, -3.0, 3.0)
    return spei


def compute_all_spei(monthly_df):
    print(f"\n⏳ คำนวณ SPEI ที่ timescales {TIMESCALES} ...")
    results = []

    for stn in sorted(monthly_df["stncode"].unique()):
        sub = (monthly_df[monthly_df["stncode"] == stn]
                 .sort_values(["year", "month"]).reset_index(drop=True))
        D = sub["precip"].values - sub["eto"].values
        months = sub["month"].values

        n_valid = 0
        for k in TIMESCALES:
            spei = compute_spei_for_series(D, months, timescale=k)
            tmp = sub[["stncode", "year", "month", "date"]].copy()
            tmp["spei"] = spei
            tmp["timescale"] = k
            results.append(tmp)
            n_valid += int(np.isfinite(spei).sum())

        print(f"   ✓ {stn} {STATIONS.get(stn, ''):<20s} ({n_valid} valid)")

    out = pd.concat(results, ignore_index=True)
    n_before = len(out)
    out = out.dropna(subset=["spei"])
    print(f"   รวม {len(out):,} SPEI values (จาก {n_before:,})")
    return out


# ================================================================
# 5. Drought metrics
# ================================================================
def classify_spei(x):
    if pd.isna(x):    return None
    if x <= -2.0:     return "Extremely dry"
    if x <= -1.5:     return "Severely dry"
    if x <= -1.0:     return "Moderately dry"
    if x <   1.0:     return "Near normal"
    if x <   1.5:     return "Moderately wet"
    if x <   2.0:     return "Severely wet"
    return "Extremely wet"


def drought_frequency(spei_df):
    rows = []
    for ts in TIMESCALES:
        sub = spei_df[spei_df["timescale"] == ts].copy()
        sub["category"] = sub["spei"].apply(classify_spei)
        for stn in sorted(sub["stncode"].unique()):
            s = sub[sub["stncode"] == stn]
            n_total = len(s)
            for cat, _, _, _ in SPEI_CATEGORIES:
                n_cat = int((s["category"] == cat).sum())
                rows.append({
                    "timescale": ts,
                    "stncode": int(stn),
                    "station": STATIONS.get(stn, str(stn)),
                    "category": cat,
                    "count": n_cat,
                    "frequency_pct": 100 * n_cat / n_total if n_total else 0,
                    "n_total": n_total,
                })
    return pd.DataFrame(rows)


def drought_events(spei_df, threshold=-1.0):
    rows = []
    for ts in TIMESCALES:
        for stn in sorted(spei_df["stncode"].unique()):
            sub = (spei_df[(spei_df["timescale"] == ts) &
                            (spei_df["stncode"] == stn)]
                     .sort_values("date").reset_index(drop=True))
            in_drought = False
            start_idx = None
            severity = 0.0
            min_spei = 0.0

            for i in range(len(sub)):
                row = sub.iloc[i]
                if row["spei"] <= threshold:
                    if not in_drought:
                        in_drought = True
                        start_idx = i
                        severity = 0.0
                        min_spei = 0.0
                    severity += row["spei"]
                    min_spei = min(min_spei, row["spei"])
                else:
                    if in_drought:
                        rows.append({
                            "timescale": ts,
                            "stncode": int(stn),
                            "station": STATIONS.get(stn, str(stn)),
                            "start": sub.iloc[start_idx]["date"],
                            "duration_months": int(i - start_idx),
                            "severity": float(severity),
                            "min_spei": float(min_spei),
                        })
                        in_drought = False

            if in_drought:
                rows.append({
                    "timescale": ts,
                    "stncode": int(stn),
                    "station": STATIONS.get(stn, str(stn)),
                    "start": sub.iloc[start_idx]["date"],
                    "duration_months": int(len(sub) - start_idx),
                    "severity": float(severity),
                    "min_spei": float(min_spei),
                })
    return pd.DataFrame(rows)


def spei_trends(spei_df):
    rows = []
    for ts in TIMESCALES:
        sub = spei_df[spei_df["timescale"] == ts]
        for stn in sorted(sub["stncode"].unique()):
            s = sub[sub["stncode"] == stn].sort_values("date")
            v = s["spei"].values
            if len(v) < 10:
                continue
            res = mk.original_test(v)
            slope, _, lo, hi = stats.theilslopes(v)
            rows.append({
                "timescale": ts, "stncode": int(stn),
                "station": STATIONS.get(stn, str(stn)),
                "n": len(v), "trend": res.trend,
                "tau": float(res.Tau), "z": float(res.z),
                "p_value": float(res.p),
                "slope_per_year": float(slope),
                "slope_per_decade": float(slope) * 10,
                "slope_lo": float(lo), "slope_hi": float(hi),
                "significant": bool(res.h),
            })

        reg = sub.groupby("date")["spei"].mean().sort_index()
        if len(reg) >= 10:
            v = reg.values
            res = mk.original_test(v)
            slope, _, lo, hi = stats.theilslopes(v)
            rows.append({
                "timescale": ts, "stncode": 0, "station": "REGIONAL",
                "n": len(v), "trend": res.trend,
                "tau": float(res.Tau), "z": float(res.z),
                "p_value": float(res.p),
                "slope_per_year": float(slope),
                "slope_per_decade": float(slope) * 10,
                "slope_lo": float(lo), "slope_hi": float(hi),
                "significant": bool(res.h),
            })
    return pd.DataFrame(rows)


def verify_spei_distribution(spei_df):
    """Check SPEI distribution against theoretical"""
    print(f"\n📌 SPEI verification (compare to theoretical):")
    print(f"   {'Category':<20s} " +
          "  ".join(f"SPEI-{ts}" for ts in TIMESCALES))
    print(f"   {'-'*20} " + "  ".join("-"*7 for _ in TIMESCALES))

    for cat, _, _, _ in SPEI_CATEGORIES:
        line = f"   {cat:<20s} "
        for ts in TIMESCALES:
            sub = spei_df[spei_df["timescale"] == ts]
            n = len(sub)
            n_cat = (sub["spei"].apply(classify_spei) == cat).sum()
            pct = 100 * n_cat / n if n > 0 else 0
            line += f"{pct:6.2f}% "
        theo = SPEI_THEORETICAL[cat]
        line += f"  (theoretical: {theo:.2f}%)"
        print(line)

    print(f"\n   Mean / Std per timescale (should be 0 / 1):")
    for ts in TIMESCALES:
        sub = spei_df[spei_df["timescale"] == ts]
        print(f"   SPEI-{ts:2d}: mean = {sub['spei'].mean():+.4f}, "
              f"std = {sub['spei'].std():.4f}, n = {len(sub):,}")


# ================================================================
# 6. Figures
# ================================================================
def plot_fig1_timeseries(spei_df):
    print("🎨 Fig F1: SPEI time series ...")

    fig, axes = plt.subplots(4, 1, figsize=(W_DOUBLE, 155 * MM),
                             sharex=True)
    plt.subplots_adjust(hspace=0.14, left=0.075, right=0.98,
                        top=0.94, bottom=0.06)

    for i, (ax, ts) in enumerate(zip(axes, TIMESCALES)):
        sub = spei_df[spei_df["timescale"] == ts]
        reg = sub.groupby("date")["spei"].mean().sort_index()
        vals = reg.values
        colors = np.where(vals >= 0, "#3B7BB1", "#C1440E")
        ax.bar(reg.index, vals, color=colors, width=25,
               edgecolor="none", alpha=0.85)
        ax.axhline(0, color="black", lw=0.6)
        ax.axhline(-1, color="#D97B29", lw=0.7, ls="--", alpha=0.8)
        ax.axhline(-1.5, color="#8C1F0E", lw=0.7, ls="--", alpha=0.8)
        ax.set_ylabel(f"SPEI-{ts}")
        ax.set_ylim(-3.2, 3.2)
        ax.yaxis.set_major_locator(MultipleLocator(1))
        ax.yaxis.set_minor_locator(MultipleLocator(0.5))
        ax.tick_params(labelsize=8)
        ax.text(0.99, 0.96, f"SPEI-{ts}", transform=ax.transAxes,
                ha="right", va="top", fontsize=8.5,
                fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3",
                          facecolor="white", edgecolor="0.7",
                          lw=0.5, alpha=0.95))
        add_panel_letter(ax, chr(ord("a") + i), xoff=-0.055, yoff=1.02)

    axes[-1].set_xlabel("Year")
    axes[-1].xaxis.set_major_locator(mpl.dates.YearLocator(5))
    axes[-1].xaxis.set_minor_locator(mpl.dates.YearLocator(1))

    safe_save(fig, os.path.join(FIG_DIR, "fig_f1_spei_timeseries.png"))
    safe_save(fig, os.path.join(FIG_DIR, "fig_f1_spei_timeseries.pdf"))
    plt.close(fig)


def plot_fig2_heatmap(spei_df):
    print("🎨 Fig F2: SPEI-12 heatmap ...")

    sub = spei_df[spei_df["timescale"] == 12].copy()
    sub["year"] = sub["date"].dt.year

    heat = (sub.groupby(["stncode", "year"])["spei"]
              .mean().unstack(fill_value=np.nan))

    station_order = [
        "Nong Khai", "Loei", "Udon Thani", "Sakon Nakhon",
        "Nakhon Phanom", "Khon Kaen", "Mukdahan", "Kosum Phisai",
        "Chaiyaphum", "Roi Et", "Ubon Ratchathani",
        "Nakhon Ratchasima", "Chok Chai", "Surin", "Tha Tum",
        "Nang Rong",
    ]
    ordered_codes = sorted(
        heat.index,
        key=lambda x: station_order.index(STATIONS.get(x, "zzz"))
        if STATIONS.get(x) in station_order else 99)
    heat = heat.reindex(ordered_codes)

    fig, ax = plt.subplots(figsize=(W_DOUBLE, 95 * MM))
    plt.subplots_adjust(left=0.18, right=0.98, top=0.90, bottom=0.16)

    cmap = plt.cm.RdBu
    vmax = np.nanmax(np.abs(heat.values))
    vmax = np.ceil(vmax * 2) / 2
    vmax = max(vmax, 2.0)

    im = ax.imshow(heat.values, aspect="auto", cmap=cmap,
                   vmin=-vmax, vmax=vmax, interpolation="nearest")

    ax.set_xticks(np.arange(len(heat.columns)))
    ax.set_xticklabels(heat.columns, rotation=90, fontsize=7)
    ax.set_yticks(np.arange(len(heat.index)))
    ax.set_yticklabels([STATIONS.get(s, str(s)) for s in heat.index],
                       fontsize=8)

    ax.set_xlabel("Year")
    ax.set_title("Annual mean SPEI-12 by station (1979–2007)",
                 pad=6, fontsize=9.5)

    cb = fig.colorbar(im, ax=ax, pad=0.02, fraction=0.035)
    cb.set_label("SPEI-12", fontsize=8)
    cb.ax.tick_params(labelsize=7.5)
    cb.outline.set_linewidth(0.5)

    safe_save(fig, os.path.join(FIG_DIR, "fig_f2_spei12_heatmap.png"))
    safe_save(fig, os.path.join(FIG_DIR, "fig_f2_spei12_heatmap.pdf"))
    plt.close(fig)


def plot_fig3_frequency(spei_df):
    """Drought frequency by decade (FIXED legend overlap)"""
    print("🎨 Fig F3: Drought frequency ...")

    spei_df = spei_df.copy()
    spei_df["year"] = spei_df["date"].dt.year
    spei_df["decade"] = pd.cut(spei_df["year"],
                                bins=[1978, 1988, 1998, 2007],
                                labels=["1979–88", "1989–98", "1999–2007"])
    spei_df["category"] = spei_df["spei"].apply(classify_spei)

    fig, axes = plt.subplots(1, 4, figsize=(W_DOUBLE, 88 * MM),
                             sharey=True)
    # ✅ FIX: bottom จาก 0.20 → 0.26 เพื่อเว้นที่ให้ legend
    plt.subplots_adjust(wspace=0.08, left=0.075, right=0.98,
                        top=0.86, bottom=0.26)

    cats_show = ["Extremely dry", "Severely dry",
                 "Moderately dry", "Near normal"]
    colors_show = ["#8C1F0E", "#D97B29", "#F2C265", "#F5F0DC"]

    for i, (ax, ts) in enumerate(zip(axes, TIMESCALES)):
        sub = spei_df[spei_df["timescale"] == ts]
        cross = (sub.groupby(["decade", "category"])
                    .size().unstack(fill_value=0))
        totals = cross.sum(axis=1)
        pct = cross.div(totals, axis=0) * 100
        pct = pct.reindex(columns=cats_show, fill_value=0)

        bottom = np.zeros(len(pct))
        for cat, color in zip(cats_show, colors_show):
            vals = pct[cat].values if cat in pct.columns else np.zeros(len(pct))
            ax.bar(np.arange(len(pct)), vals, 0.65, bottom=bottom,
                   color=color, edgecolor="black", linewidth=0.3)
            bottom += vals

        ax.set_xticks(np.arange(len(pct)))
        ax.set_xticklabels(pct.index, rotation=20, fontsize=8)
        ax.set_xlabel("Decade", labelpad=4)
        ax.set_title(f"SPEI-{ts}", pad=6, fontsize=9.5)
        ax.set_ylim(0, 100)
        ax.yaxis.set_major_locator(MultipleLocator(20))
        add_panel_letter(ax, chr(ord("a") + i), xoff=-0.14, yoff=1.03)

    axes[0].set_ylabel("Frequency (%)")

    handles = [Patch(facecolor=c, edgecolor="black",
                     linewidth=0.3, label=l)
               for l, c in zip(cats_show, colors_show)]
    # ✅ FIX: legend อยู่ล่างสุดของ figure ไม่ทับ x-label
    fig.legend(handles=handles, loc="lower center",
               bbox_to_anchor=(0.5, 0.005), ncol=4, fontsize=8,
               frameon=False, handlelength=1.5, columnspacing=2.0)

    safe_save(fig, os.path.join(FIG_DIR, "fig_f3_drought_frequency.png"))
    safe_save(fig, os.path.join(FIG_DIR, "fig_f3_drought_frequency.pdf"))
    plt.close(fig)


def plot_fig4_events(events_df):
    print("🎨 Fig F4: Drought events duration × severity ...")

    if len(events_df) == 0:
        print("   ⚠️  ไม่มี drought events")
        return

    fig, axes = plt.subplots(1, 4, figsize=(W_DOUBLE, 85 * MM))
    plt.subplots_adjust(wspace=0.34, left=0.075, right=0.98,
                        top=0.88, bottom=0.22)

    sc = None
    for i, (ax, ts) in enumerate(zip(axes, TIMESCALES)):
        sub = events_df[events_df["timescale"] == ts]
        if len(sub) == 0:
            continue

        sc = ax.scatter(sub["duration_months"], sub["severity"],
                        c=sub["min_spei"], cmap="RdYlBu_r",
                        s=28, alpha=0.78,
                        edgecolors="black", linewidths=0.3,
                        vmin=-3, vmax=0)
        ax.axhline(0, color="0.6", lw=0.4, ls=":")
        ax.set_xlabel("Duration (months)")
        if i == 0:
            ax.set_ylabel(r"Severity ($\sum$ SPEI)")
        ax.set_title(f"SPEI-{ts}", pad=6, fontsize=9.5)
        add_panel_letter(ax, chr(ord("a") + i), xoff=-0.18, yoff=1.03)

    if sc is not None:
        cbar_ax = fig.add_axes([0.30, 0.02, 0.40, 0.02])
        cb = fig.colorbar(sc, cax=cbar_ax, orientation="horizontal")
        cb.set_label("Minimum SPEI during event", fontsize=8)
        cb.ax.tick_params(labelsize=7)

    safe_save(fig, os.path.join(FIG_DIR, "fig_f4_drought_events.png"))
    safe_save(fig, os.path.join(FIG_DIR, "fig_f4_drought_events.pdf"))
    plt.close(fig)


def plot_fig5_spatial(spei_df):
    """Spatial trend with COLORED stars + manual label offsets (FIXED)"""
    print("🎨 Fig F5: Spatial SPEI-12 trend ...")

    rows = []
    for stn in spei_df["stncode"].unique():
        sub = (spei_df[(spei_df["timescale"] == 12) &
                        (spei_df["stncode"] == stn)]
                 .sort_values("date"))
        v = sub["spei"].values
        if len(v) < 10:
            continue
        res = mk.original_test(v)
        slope, _, _, _ = stats.theilslopes(v)
        rows.append({
            "stncode": int(stn),
            "lat": STN_COORDS.get(stn, (np.nan, np.nan))[0],
            "lon": STN_COORDS.get(stn, (np.nan, np.nan))[1],
            "slope": slope * 10,
            "p_value": res.p,
            "significant": res.h,
        })
    df = pd.DataFrame(rows)

    fig, ax = plt.subplots(figsize=(W_SINGLE * 1.55, 108 * MM))
    plt.subplots_adjust(left=0.14, right=0.98, top=0.92, bottom=0.14)

    vmax = max(abs(df["slope"].max()), abs(df["slope"].min()))
    vmax = np.ceil(vmax * 10) / 10
    vmax = max(vmax, 0.1)

    # ✅ FIX: ใช้ scatter ตัวเดียว → marker ตาม significance + สีตาม trend
    for _, row in df.iterrows():
        marker = "*" if row["significant"] else "o"
        size = 320 if row["significant"] else 190
        ax.scatter(row["lon"], row["lat"],
                   c=[row["slope"]], cmap="RdBu",
                   vmin=-vmax, vmax=vmax,
                   s=size, marker=marker,
                   edgecolors="black",
                   linewidths=1.0 if row["significant"] else 0.6,
                   zorder=5 if row["significant"] else 4)

    # ✅ FIX: labels with manual offsets + white halo (no overlap)
    for _, row in df.iterrows():
        stn = row["stncode"]
        dx, dy = SPATIAL_OFFSETS.get(stn, (0, -15))
        name = STATIONS.get(stn, str(stn))
        abbr = STN_ABBR.get(name, name)
        ax.annotate(abbr,
                    xy=(row["lon"], row["lat"]),
                    xytext=(dx, dy), textcoords="offset points",
                    ha="center", va="center", fontsize=6.5,
                    color="0.15", zorder=8,
                    bbox=dict(boxstyle="round,pad=0.15",
                              facecolor="white", edgecolor="none",
                              alpha=0.9))

    ax.set_xlim(100.5, 106.0)
    ax.set_ylim(13.5, 18.5)
    ax.set_aspect("equal")
    ax.xaxis.set_major_locator(MultipleLocator(1))
    ax.yaxis.set_major_locator(MultipleLocator(1))
    ax.xaxis.set_minor_locator(MultipleLocator(0.5))
    ax.yaxis.set_minor_locator(MultipleLocator(0.5))
    ax.set_xlabel("Longitude (°E)")
    ax.set_ylabel("Latitude (°N)")
    ax.set_title("SPEI-12 trend (per decade)", pad=6, fontsize=9.5)
    ax.grid(True, color="0.9", lw=0.4, ls=":")

    # Colorbar via ScalarMappable (since we used scatter per-point)
    sm = ScalarMappable(cmap="RdBu", norm=Normalize(-vmax, vmax))
    sm.set_array([])
    cb = fig.colorbar(sm, ax=ax, pad=0.02, fraction=0.045)
    cb.set_label(r"Trend (SPEI dec$^{-1}$)", fontsize=8)
    cb.ax.tick_params(labelsize=7)

    # ✅ FIX: legend shows BOTH color and shape
    leg = [
        Line2D([], [], marker="o", ls="", mfc="#B0B0B0",
               mec="black", mew=0.6, ms=9,
               label="Not significant"),
        Line2D([], [], marker="*", ls="", mfc="#C1440E",
               mec="black", mew=1.0, ms=14,
               label=r"$p$ < 0.05 (star)"),
    ]
    ax.legend(handles=leg, loc="lower right", fontsize=7.5,
              framealpha=0.95, title="Significance",
              title_fontsize=7.5)

    safe_save(fig, os.path.join(FIG_DIR, "fig_f5_spatial_trend.png"))
    safe_save(fig, os.path.join(FIG_DIR, "fig_f5_spatial_trend.pdf"))
    plt.close(fig)


def plot_fig6_timescale_comparison(spei_df):
    """Timescale comparison with different linestyles (FIXED overlap)"""
    print("🎨 Fig F6: Timescale comparison ...")

    fig, ax = plt.subplots(figsize=(W_DOUBLE, 85 * MM))
    plt.subplots_adjust(left=0.075, right=0.98, top=0.90, bottom=0.16)

    # ✅ FIX: linestyle ต่างกัน + linewidth ต่างกัน
    colors = ["#F2C265", "#E5A03A", "#C1440E", "#8C1F0E"]
    linestyles = ["-", "--", "-.", ":"]
    linewidths = [0.9, 0.9, 1.0, 1.5]

    for ts, c, ls, lw in zip(TIMESCALES, colors, linestyles, linewidths):
        sub = spei_df[spei_df["timescale"] == ts]
        reg = sub.groupby("date")["spei"].mean().sort_index()
        ax.plot(reg.index, reg.values, ls, color=c, lw=lw,
                alpha=0.9, label=f"SPEI-{ts}")

    ax.axhline(0, color="black", lw=0.6)
    ax.axhline(-1, color="0.5", lw=0.6, ls="--", alpha=0.7)
    ax.axhline(-1.5, color="0.3", lw=0.6, ls="--", alpha=0.7)

    ax.set_xlabel("Year")
    ax.set_ylabel("SPEI (regional mean)")
    ax.set_ylim(-3.2, 3.2)
    ax.yaxis.set_major_locator(MultipleLocator(1))
    ax.yaxis.set_minor_locator(MultipleLocator(0.5))
    ax.xaxis.set_major_locator(mpl.dates.YearLocator(5))
    ax.xaxis.set_minor_locator(mpl.dates.YearLocator(1))
    ax.set_title("Comparison of SPEI timescales (regional mean)",
                 pad=6, fontsize=9.5)
    ax.legend(loc="lower right", ncol=4, fontsize=7.5,
              framealpha=0.95)

    safe_save(fig, os.path.join(FIG_DIR, "fig_f6_timescale_comparison.png"))
    safe_save(fig, os.path.join(FIG_DIR, "fig_f6_timescale_comparison.pdf"))
    plt.close(fig)


# ================================================================
# 7. Main
# ================================================================
def main():
    print("=" * 70)
    print("Stage 2 - Module F (v2): SPEI Drought Characterization")
    print("=" * 70)

    # 1. Load & aggregate
    monthly = load_monthly_eto_precip()

    # 2. Compute SPEI
    spei_df = compute_all_spei(monthly)

    if len(spei_df) == 0:
        print("\n❌ SPEI ว่างเปล่า — ตรวจสอบ fitting")
        return

    # 3. Save SPEI full table (pivot to wide)
    print("\n💾 บันทึกตาราง SPEI ...")
    spei_df = spei_df.copy()
    spei_df["station"] = spei_df["stncode"].map(STATIONS)

    spei_wide = spei_df.pivot_table(
        index=["stncode", "station", "date"],
        columns="timescale",
        values="spei",
        aggfunc="first"
    ).reset_index()

    spei_wide.columns = [
        f"spei_{c}" if isinstance(c, (int, np.integer)) else c
        for c in spei_wide.columns
    ]
    spei_wide = spei_wide.sort_values(["stncode", "date"]).reset_index(drop=True)
    spei_wide.to_csv(
        os.path.join(TAB_DIR, "table_f1_spei_full.csv"),
        index=False, float_format="%.3f")
    print(f"   ✅ table_f1_spei_full.csv ({len(spei_wide):,} แถว)")

    # 4. Frequency
    print("\n📊 Drought frequency ...")
    freq_df = drought_frequency(spei_df)
    freq_df.to_csv(
        os.path.join(TAB_DIR, "table_f2_drought_frequency.csv"),
        index=False, float_format="%.2f")
    print(f"   ✅ table_f2_drought_frequency.csv ({len(freq_df):,} แถว)")

    # 5. Events
    print("📊 Drought events catalog ...")
    events_df = drought_events(spei_df, threshold=-1.0)
    events_df.to_csv(
        os.path.join(TAB_DIR, "table_f3_drought_events.csv"),
        index=False, float_format="%.3f")
    print(f"   ✅ table_f3_drought_events.csv ({len(events_df):,} events)")

    if len(events_df) > 0:
        top_events = (events_df
                      .sort_values(["timescale", "min_spei"])
                      .groupby("timescale")
                      .head(10))
        top_events.to_csv(
            os.path.join(TAB_DIR, "table_f4_top_events.csv"),
            index=False, float_format="%.3f")
        print(f"   ✅ table_f4_top_events.csv ({len(top_events):,} events)")

    # 6. Trends
    print("📊 SPEI trends (Mann-Kendall) ...")
    trends_df = spei_trends(spei_df)
    trends_df.to_csv(
        os.path.join(TAB_DIR, "table_f5_spei_trends.csv"),
        index=False, float_format="%.3f")
    print(f"   ✅ table_f5_spei_trends.csv ({len(trends_df):,} แถว)")

    # 7. Figures
    print()
    plot_fig1_timeseries(spei_df)
    plot_fig2_heatmap(spei_df)
    plot_fig3_frequency(spei_df)
    plot_fig4_events(events_df)
    plot_fig5_spatial(spei_df)
    plot_fig6_timescale_comparison(spei_df)

    # 8. Verification + Summary
    print("\n" + "=" * 70)
    print("📊 Verification & Summary")
    print("=" * 70)

    verify_spei_distribution(spei_df)

    reg_trends = trends_df[trends_df["stncode"] == 0]
    print(f"\n📌 Regional SPEI trends:")
    for _, r in reg_trends.iterrows():
        stars = ("***" if r["p_value"] < 0.001 else
                 "**"  if r["p_value"] < 0.01  else
                 "*"   if r["p_value"] < 0.05  else "n.s.")
        print(f"   SPEI-{int(r['timescale']):2d}: "
              f"slope = {r['slope_per_decade']:+.4f} dec⁻¹  "
              f"p = {r['p_value']:.3f} ({stars})")

    if len(events_df) > 0:
        print(f"\n📌 Drought events (threshold ≤ -1):")
        for ts in TIMESCALES:
            sub = events_df[events_df["timescale"] == ts]
            if len(sub) == 0:
                continue
            dur_mean = sub["duration_months"].mean()
            sev_mean = sub["severity"].mean()
            print(f"   SPEI-{ts:2d}: {len(sub):4d} events | "
                  f"duration = {dur_mean:.1f} mo | "
                  f"severity = {sev_mean:+.2f}")

    print(f"\n📁 Tables : {os.path.abspath(TAB_DIR)}")
    print(f"📁 Figures: {os.path.abspath(FIG_DIR)}")
    print("=" * 70)


if __name__ == "__main__":
    main()