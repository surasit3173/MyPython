"""
Stage 2 - Module F (compare): SPEI from AgERA5 vs Observed Precipitation
NE Thailand, 15 stations, 1979-2007

Computes SPEI two ways:
  (A) SPEI_agera5   = f(AgERA5 Precip,   AgERA5 ETo)
  (B) SPEI_observed = f(Observed Precip, AgERA5 ETo)

Figures:
  F1: SPEI time series (4 panels, both lines per panel)
  F2: SPEI-12 heatmap (AgERA5)
  F3: Drought frequency by decade (both)
  F4: Duration × severity (both)
  F5: Spatial SPEI-12 trend (both)
  F6: Timescale comparison (both)
  F7: Validation scatter (AgERA5 vs Observed, per timescale)

Q2 journal level - Times New Roman, 400 dpi
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

# ✅ Distinguish AgERA5 vs Observed
CLR_AGE   = "#C1440E"   # warm red — AgERA5 (solid)
CLR_OBS   = "#1F6FB4"   # deep blue — Observed (dashed)
CLR_POS   = "#88BBD7"
CLR_NEG   = "#C1440E"

SPEI_CATEGORIES = [
    ("Extremely dry",    -np.inf, -2.0, "#8C1F0E"),
    ("Severely dry",     -2.0,    -1.5, "#D97B29"),
    ("Moderately dry",   -1.5,    -1.0, "#F2C265"),
    ("Near normal",      -1.0,     1.0, "#F5F0DC"),
    ("Moderately wet",    1.0,     1.5, "#88BBD7"),
    ("Severely wet",      1.5,     2.0, "#3B7BB1"),
    ("Extremely wet",     2.0,   np.inf, "#0D4A78"),
]

SPEI_THEORETICAL = {
    "Extremely dry":  2.28, "Severely dry":   4.40,
    "Moderately dry": 9.19, "Near normal":   68.27,
    "Moderately wet": 9.19, "Severely wet":   4.40,
    "Extremely wet":  2.28,
}


# ================================================================
# 2. Paths
# ================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUT_DIR  = os.path.join(BASE_DIR, "outputs", "module_f_compare")
FIG_DIR  = os.path.join(OUT_DIR, "figures")
TAB_DIR  = os.path.join(OUT_DIR, "tables")
os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(TAB_DIR, exist_ok=True)

ETO_CSV      = os.path.join(DATA_DIR, "agera5_eto_station_daily_arco.csv")
PREC_AGE_CSV = os.path.join(DATA_DIR, "agera5_precip_station_daily_arco.csv")

OBS_PREC_CSV = None
for cand in [os.path.join(DATA_DIR, "observed_precip.csv"),
             os.path.join(BASE_DIR, "observed_precip.csv")]:
    if os.path.exists(cand):
        OBS_PREC_CSV = cand
        break

if OBS_PREC_CSV is None:
    print("❌ ไม่พบ observed_precip.csv")
    sys.exit(1)

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
    352201: (17.863, 102.752), 353201: (17.448, 101.732),
    354201: (17.383, 102.800), 356201: (17.151, 104.137),
    357201: (17.410, 104.782), 381201: (16.457, 102.790),
    383201: (16.542, 104.729), 387401: (16.241, 103.070),
    403201: (15.807, 102.030), 405201: (16.052, 103.664),
    407501: (15.242, 104.876), 431201: (14.963, 102.087),
    431401: (14.733, 102.170), 432201: (14.872, 103.500),
    432401: (15.315, 103.681), 436401: (14.627, 102.723),
}

STN_ABBR = {
    "Nakhon Ratchasima": "Nakhon Rat.", "Ubon Ratchathani": "Ubon Rat.",
    "Sakon Nakhon": "Sakon Nakh.", "Nakhon Phanom": "Nakhon Pha.",
    "Kosum Phisai": "Kosum Ph.",
}

SPATIAL_OFFSETS = {
    352201: (0, -15), 353201: (0, -15), 354201: (15, 5),
    356201: (15, -5), 357201: (15, -5), 381201: (0, -15),
    383201: (15, -5), 387401: (0, -15), 403201: (0, -15),
    405201: (15, -5), 407501: (15, -5), 431201: (-20, 10),
    431401: (25, -5), 436401: (10, -18), 432201: (-25, -10),
    432401: (15, -5),
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


def add_panel_letter(ax, letter, xoff=-0.14, yoff=1.05):
    ax.text(xoff, yoff, letter, transform=ax.transAxes,
            fontsize=12, fontweight="bold", family="serif",
            ha="left", va="bottom", clip_on=False)


# ================================================================
# 3. Data loading
# ================================================================
def load_eto_monthly():
    """โหลด AgERA5 ETo รายวัน → รายเดือน"""
    eto = pd.read_csv(ETO_CSV, parse_dates=["time"])
    eto = eto.rename(columns={"time": "date", "eto_mm_day": "eto"})
    eto["stncode"] = eto["stncode"].astype(int)
    eto["year"]  = eto["date"].dt.year
    eto["month"] = eto["date"].dt.month

    eto_m = (eto.groupby(["stncode", "year", "month"])
                .agg(eto=("eto", "sum"), n=("eto", "count"))
                .reset_index())
    eto_m = eto_m[eto_m["n"] >= 25].drop(columns="n")
    print(f"📂 ETo (AgERA5): {len(eto_m):,} station-months")
    return eto_m


def load_precip_agera5_monthly():
    """โหลด AgERA5 Precip รายวัน → รายเดือน"""
    prec = pd.read_csv(PREC_AGE_CSV, parse_dates=["time"])
    prec = prec.rename(columns={"time": "date", "precip_mm_day": "precip"})
    prec["stncode"] = prec["stncode"].astype(int)
    prec["year"]  = prec["date"].dt.year
    prec["month"] = prec["date"].dt.month

    prec_m = (prec.groupby(["stncode", "year", "month"])
                   .agg(precip=("precip", "sum"), n=("precip", "count"))
                   .reset_index())
    prec_m = prec_m[prec_m["n"] >= 25].drop(columns="n")
    print(f"📂 Precip (AgERA5): {len(prec_m):,} station-months")
    return prec_m


def load_precip_observed_monthly():
    """โหลด Observed Precip (wide format, monthly) → long"""
    print(f"📂 Precip (Observed): {os.path.basename(OBS_PREC_CSV)}")

    obs = pd.read_csv(OBS_PREC_CSV)
    obs.columns = [str(c).strip() for c in obs.columns]

    if "YEAR" not in obs.columns or "MONTH" not in obs.columns:
        raise ValueError(f"ต้องมี YEAR, MONTH — พบ {list(obs.columns)[:8]}")

    stn_cols = [c for c in obs.columns if c not in ("YEAR", "MONTH")]
    obs_long = obs.melt(
        id_vars=["YEAR", "MONTH"],
        value_vars=stn_cols,
        var_name="stncode",
        value_name="precip_obs",
    )
    obs_long["stncode"] = obs_long["stncode"].astype(int)
    obs_long = obs_long.rename(columns={"YEAR": "year", "MONTH": "month"})
    obs_long["year"]  = obs_long["year"].astype(int)
    obs_long["month"] = obs_long["month"].astype(int)
    obs_long = obs_long.dropna(subset=["precip_obs"])
    obs_long = obs_long[(obs_long["year"] >= YEAR_START) &
                         (obs_long["year"] <= YEAR_END)]

    print(f"   {len(obs_long):,} station-months | "
          f"{obs_long['year'].min()}–{obs_long['year'].max()}")
    print(f"   Stations: {len(obs_long['stncode'].unique())}")
    return obs_long


def merge_datasets(eto_m, prec_age_m, prec_obs_m):
    """Merge ทั้ง 3 dataset → water balance D สำหรับ 2 sources"""
    # 1. ETo + AgERA5 precip
    df_age = eto_m.merge(prec_age_m, on=["stncode", "year", "month"],
                          how="inner")
    df_age["D_age"] = df_age["precip"] - df_age["eto"]
    df_age["source"] = "AgERA5"
    # ✅ FIX: เพิ่มคอลัมน์ date
    df_age["date"] = pd.to_datetime(
        dict(year=df_age["year"], month=df_age["month"], day=1))

    # 2. ETo + Observed precip
    df_obs = eto_m.merge(prec_obs_m, on=["stncode", "year", "month"],
                          how="inner")
    df_obs["precip"] = df_obs["precip_obs"]
    df_obs["D_obs"] = df_obs["precip_obs"] - df_obs["eto"]
    df_obs["source"] = "Observed"
    # ✅ FIX: เพิ่มคอลัมน์ date
    df_obs["date"] = pd.to_datetime(
        dict(year=df_obs["year"], month=df_obs["month"], day=1))

    # Sort
    df_age = df_age.sort_values(["stncode", "year", "month"]).reset_index(drop=True)
    df_obs = df_obs.sort_values(["stncode", "year", "month"]).reset_index(drop=True)

    # Common stations only (ที่ทั้ง 2 dataset มี)
    common = sorted(set(df_age["stncode"]) & set(df_obs["stncode"]))
    df_age = df_age[df_age["stncode"].isin(common)]
    df_obs = df_obs[df_obs["stncode"].isin(common)]

    print(f"\n✅ Common stations: {len(common)}")
    print(f"   AgERA5 rows:   {len(df_age):,}")
    print(f"   Observed rows: {len(df_obs):,}")

    return df_age, df_obs, common


# ================================================================
# 4. SPEI computation
# ================================================================
def fit_spei_distribution(data):
    data = np.asarray(data, dtype=float)
    data = data[np.isfinite(data)]
    if len(data) < 10 or np.std(data) < 1e-6:
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
    data = np.asarray(data, dtype=float)
    if fit is None:
        return np.full_like(data, np.nan)
    with np.errstate(all="ignore"):
        F = fisk.cdf(data, fit["c"], loc=fit["loc"], scale=fit["scale"])
    F = np.clip(F, 1e-6, 1 - 1e-6)
    return stats.norm.ppf(F)


def compute_spei_for_series(series, month_labels, timescale=1):
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

    return np.clip(spei, -3.0, 3.0)


def compute_spei_both(df_age, df_obs):
    """คำนวณ SPEI สำหรับทั้ง AgERA5 และ Observed"""
    print(f"\n⏳ คำนวณ SPEI (AgERA5 + Observed) ที่ timescales {TIMESCALES} ...")
    results_age = []
    results_obs = []

    stns = sorted(set(df_age["stncode"]) & set(df_obs["stncode"]))

    for stn in stns:
        sub_age = (df_age[df_age["stncode"] == stn]
                     .sort_values(["year", "month"]).reset_index(drop=True))
        sub_obs = (df_obs[df_obs["stncode"] == stn]
                     .sort_values(["year", "month"]).reset_index(drop=True))

        # Align ให้ month labels ตรงกัน
        months_age = sub_age["month"].values
        months_obs = sub_obs["month"].values

        for k in TIMESCALES:
            spei_a = compute_spei_for_series(
                sub_age["D_age"].values, months_age, timescale=k)
            spei_o = compute_spei_for_series(
                sub_obs["D_obs"].values, months_obs, timescale=k)

            tmp_a = sub_age[["stncode", "year", "month", "date"]].copy()
            tmp_a["spei"] = spei_a
            tmp_a["timescale"] = k
            tmp_a["source"] = "AgERA5"
            results_age.append(tmp_a)

            tmp_o = sub_obs[["stncode", "year", "month", "date"]].copy()
            tmp_o["spei"] = spei_o
            tmp_o["timescale"] = k
            tmp_o["source"] = "Observed"
            results_obs.append(tmp_o)

        n_a = sum(int(np.isfinite(r["spei"]).sum()) for r in results_age[-4:])
        n_o = sum(int(np.isfinite(r["spei"]).sum()) for r in results_obs[-4:])
        print(f"   ✓ {stn} {STATIONS.get(stn, ''):<20s} "
              f"(A:{n_a}, O:{n_o})")

    spei_age = pd.concat(results_age, ignore_index=True).dropna(subset=["spei"])
    spei_obs = pd.concat(results_obs, ignore_index=True).dropna(subset=["spei"])

    print(f"   รวม: AgERA5 = {len(spei_age):,} | Observed = {len(spei_obs):,}")
    return spei_age, spei_obs


# ================================================================
# 5. Drought metrics (same as before)
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
        for src in spei_df["source"].unique():
            sub = spei_df[(spei_df["timescale"] == ts) &
                            (spei_df["source"] == src)].copy()
            sub["category"] = sub["spei"].apply(classify_spei)
            for stn in sorted(sub["stncode"].unique()):
                s = sub[sub["stncode"] == stn]
                n_tot = len(s)
                for cat, _, _, _ in SPEI_CATEGORIES:
                    n_cat = int((s["category"] == cat).sum())
                    rows.append({
                        "timescale": ts, "source": src,
                        "stncode": int(stn),
                        "station": STATIONS.get(stn, str(stn)),
                        "category": cat,
                        "count": n_cat,
                        "frequency_pct": 100 * n_cat / n_tot if n_tot else 0,
                        "n_total": n_tot,
                    })
    return pd.DataFrame(rows)


def drought_events(spei_df, threshold=-1.0):
    rows = []
    for ts in TIMESCALES:
        for src in spei_df["source"].unique():
            sub_src = spei_df[(spei_df["timescale"] == ts) &
                                (spei_df["source"] == src)]
            for stn in sorted(sub_src["stncode"].unique()):
                sub = (sub_src[sub_src["stncode"] == stn]
                         .sort_values("date").reset_index(drop=True))
                in_d = False
                start_idx = None
                sev = 0.0
                min_s = 0.0
                for i in range(len(sub)):
                    row = sub.iloc[i]
                    if row["spei"] <= threshold:
                        if not in_d:
                            in_d = True
                            start_idx = i
                            sev = 0.0
                            min_s = 0.0
                        sev += row["spei"]
                        min_s = min(min_s, row["spei"])
                    else:
                        if in_d:
                            rows.append({
                                "timescale": ts, "source": src,
                                "stncode": int(stn),
                                "station": STATIONS.get(stn, str(stn)),
                                "start": sub.iloc[start_idx]["date"],
                                "duration_months": int(i - start_idx),
                                "severity": float(sev),
                                "min_spei": float(min_s),
                            })
                            in_d = False
                if in_d:
                    rows.append({
                        "timescale": ts, "source": src,
                        "stncode": int(stn),
                        "station": STATIONS.get(stn, str(stn)),
                        "start": sub.iloc[start_idx]["date"],
                        "duration_months": int(len(sub) - start_idx),
                        "severity": float(sev),
                        "min_spei": float(min_s),
                    })
    return pd.DataFrame(rows)


def spei_trends(spei_df):
    rows = []
    for ts in TIMESCALES:
        for src in spei_df["source"].unique():
            sub_src = spei_df[(spei_df["timescale"] == ts) &
                                (spei_df["source"] == src)]
            for stn in sorted(sub_src["stncode"].unique()):
                s = (sub_src[sub_src["stncode"] == stn]
                       .sort_values("date"))
                v = s["spei"].values
                if len(v) < 10:
                    continue
                res = mk.original_test(v)
                slope, _, lo, hi = stats.theilslopes(v)
                rows.append({
                    "timescale": ts, "source": src,
                    "stncode": int(stn),
                    "station": STATIONS.get(stn, str(stn)),
                    "n": len(v), "trend": res.trend,
                    "tau": float(res.Tau), "p_value": float(res.p),
                    "slope_per_decade": float(slope) * 10,
                    "significant": bool(res.h),
                })
            # Regional
            reg = sub_src.groupby("date")["spei"].mean().sort_index()
            if len(reg) >= 10:
                v = reg.values
                res = mk.original_test(v)
                slope, _, _, _ = stats.theilslopes(v)
                rows.append({
                    "timescale": ts, "source": src,
                    "stncode": 0, "station": "REGIONAL",
                    "n": len(v), "trend": res.trend,
                    "tau": float(res.Tau), "p_value": float(res.p),
                    "slope_per_decade": float(slope) * 10,
                    "significant": bool(res.h),
                })
    return pd.DataFrame(rows)


# ================================================================
# 6. Figures
# ================================================================
def plot_fig1_timeseries(spei_age, spei_obs):
    """SPEI time series — AgERA5 (bar) + Observed (overlay dashed line)"""
    print("🎨 Fig F1: SPEI time series (with observed overlay) ...")

    fig, axes = plt.subplots(4, 1, figsize=(W_DOUBLE, 160 * MM),
                             sharex=True)
    plt.subplots_adjust(hspace=0.14, left=0.075, right=0.98,
                        top=0.94, bottom=0.08)

    for i, (ax, ts) in enumerate(zip(axes, TIMESCALES)):
        # AgERA5 — bars
        sub_a = spei_age[spei_age["timescale"] == ts]
        reg_a = sub_a.groupby("date")["spei"].mean().sort_index()
        colors_a = np.where(reg_a.values >= 0, CLR_POS, CLR_NEG)
        ax.bar(reg_a.index, reg_a.values, color=colors_a, width=25,
               edgecolor="none", alpha=0.7, zorder=2,
               label="AgERA5")

        # Observed — line
        sub_o = spei_obs[spei_obs["timescale"] == ts]
        reg_o = sub_o.groupby("date")["spei"].mean().sort_index()
        ax.plot(reg_o.index, reg_o.values, "--", color=CLR_OBS,
                lw=1.1, alpha=0.95, zorder=4,
                label="Observed")

        ax.axhline(0, color="black", lw=0.6, zorder=1)
        ax.axhline(-1, color="#D97B29", lw=0.7, ls=":", alpha=0.7, zorder=1)
        ax.axhline(-1.5, color="#8C1F0E", lw=0.7, ls=":", alpha=0.7, zorder=1)

        ax.set_ylabel(f"SPEI-{ts}")
        ax.set_ylim(-3.2, 3.2)
        ax.yaxis.set_major_locator(MultipleLocator(1))
        ax.yaxis.set_minor_locator(MultipleLocator(0.5))
        ax.tick_params(labelsize=8)

        # Correlation between AgERA5 and Observed at this timescale
        merged = reg_a.to_frame("a").join(reg_o.to_frame("o"), how="inner")
        if len(merged) > 10:
            r, _ = stats.pearsonr(merged["a"], merged["o"])
        else:
            r = np.nan

        ax.text(0.99, 0.96,
                f"SPEI-{ts}   $r$ = {r:.3f}",
                transform=ax.transAxes, ha="right", va="top",
                fontsize=8, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3",
                          facecolor="white", edgecolor="0.7",
                          lw=0.5, alpha=0.95),
                zorder=5)
        add_panel_letter(ax, chr(ord("a") + i), xoff=-0.055, yoff=1.02)

    # Legend on top panel
    axes[0].legend(loc="lower left", ncol=2, fontsize=8,
                   framealpha=0.95, bbox_to_anchor=(0.0, 1.15))

    axes[-1].set_xlabel("Year")
    axes[-1].xaxis.set_major_locator(mpl.dates.YearLocator(5))
    axes[-1].xaxis.set_minor_locator(mpl.dates.YearLocator(1))

    safe_save(fig, os.path.join(FIG_DIR, "fig_f1_timeseries_compare.png"))
    safe_save(fig, os.path.join(FIG_DIR, "fig_f1_timeseries_compare.pdf"))
    plt.close(fig)


def plot_fig2_heatmap(spei_age):
    """Heatmap — AgERA5 only (same as before)"""
    print("🎨 Fig F2: SPEI-12 heatmap (AgERA5) ...")

    sub = spei_age[spei_age["timescale"] == 12].copy()
    sub["year"] = sub["date"].dt.year

    heat = (sub.groupby(["stncode", "year"])["spei"]
              .mean().unstack(fill_value=np.nan))

    station_order = list(STATIONS.values())
    ordered = sorted(heat.index,
                     key=lambda x: station_order.index(STATIONS.get(x, "zzz"))
                     if STATIONS.get(x) in station_order else 99)
    heat = heat.reindex(ordered)

    fig, ax = plt.subplots(figsize=(W_DOUBLE, 95 * MM))
    plt.subplots_adjust(left=0.18, right=0.98, top=0.90, bottom=0.16)

    vmax = np.nanmax(np.abs(heat.values))
    vmax = max(np.ceil(vmax * 2) / 2, 2.0)

    im = ax.imshow(heat.values, aspect="auto", cmap="RdBu",
                   vmin=-vmax, vmax=vmax, interpolation="nearest")

    ax.set_xticks(np.arange(len(heat.columns)))
    ax.set_xticklabels(heat.columns, rotation=90, fontsize=7)
    ax.set_yticks(np.arange(len(heat.index)))
    ax.set_yticklabels([STATIONS.get(s, str(s)) for s in heat.index],
                       fontsize=8)

    ax.set_xlabel("Year")
    ax.set_title("Annual mean SPEI-12 (AgERA5, 1979–2007)",
                 pad=6, fontsize=9.5)

    cb = fig.colorbar(im, ax=ax, pad=0.02, fraction=0.035)
    cb.set_label("SPEI-12", fontsize=8)
    cb.ax.tick_params(labelsize=7.5)

    safe_save(fig, os.path.join(FIG_DIR, "fig_f2_spei12_heatmap.png"))
    safe_save(fig, os.path.join(FIG_DIR, "fig_f2_spei12_heatmap.pdf"))
    plt.close(fig)


def plot_fig3_frequency(freq_df):
    """Frequency by decade — AgERA5 vs Observed"""
    print("🎨 Fig F3: Drought frequency (AgERA5 vs Observed) ...")

    fig, axes = plt.subplots(1, 4, figsize=(W_DOUBLE, 92 * MM),
                             sharey=True)
    plt.subplots_adjust(wspace=0.08, left=0.075, right=0.98,
                        top=0.86, bottom=0.26)

    cats_show = ["Extremely dry", "Severely dry",
                 "Moderately dry", "Near normal"]
    colors_show = ["#8C1F0E", "#D97B29", "#F2C265", "#F5F0DC"]

    # Need decade info — use spei_df already computed
    # Here we assume freq_df has no decade; we'll recompute inline
    # For simplicity, iterate manually
    # --- Actually recompute from scratch ---
    # This function receives freq_df; but we need decade splits.
    # So we'll rely on a fresh computation done in main() that adds decade.

    # NOTE: freq_df here should already have "decade" column
    for i, (ax, ts) in enumerate(zip(axes, TIMESCALES)):
        sub = freq_df[freq_df["timescale"] == ts]
        x = np.arange(len(["1979–88", "1989–98", "1999–2007"]))
        decades = ["1979–88", "1989–98", "1999–2007"]
        width = 0.35

        for j, src in enumerate(["AgERA5", "Observed"]):
            sub_s = sub[sub["source"] == src]
            for k, cat in enumerate(cats_show):
                cat_data = sub_s[sub_s["category"] == cat]
                if len(cat_data) == 0:
                    continue
                # group by decade
                agg = cat_data.groupby("decade")["frequency_pct"].mean()
                vals = [agg.get(d, 0) for d in decades]
                # Stack
                bottom = np.zeros(len(decades))
                for prev_cat in cats_show[:k]:
                    prev_data = sub_s[sub_s["category"] == prev_cat]
                    if len(prev_data) == 0:
                        continue
                    prev_agg = prev_data.groupby("decade")["frequency_pct"].mean()
                    bottom += np.array([prev_agg.get(d, 0) for d in decades])

                offset = (j - 0.5) * width
                alpha = 0.9 if src == "AgERA5" else 0.55
                hatch = None if src == "AgERA5" else "///"
                ax.bar(x + offset, vals, width,
                       bottom=bottom, color=colors_show[k],
                       edgecolor="black", linewidth=0.3,
                       alpha=alpha, hatch=hatch)

        ax.set_xticks(x)
        ax.set_xticklabels(decades, rotation=20, fontsize=7)
        ax.set_xlabel("Decade", labelpad=4)
        ax.set_title(f"SPEI-{ts}", pad=6, fontsize=9.5)
        ax.set_ylim(0, 100)
        ax.yaxis.set_major_locator(MultipleLocator(20))
        add_panel_letter(ax, chr(ord("a") + i), xoff=-0.14, yoff=1.03)

    axes[0].set_ylabel("Frequency (%)")

    # Two legends: category (bottom) + source (top)
    cat_handles = [Patch(facecolor=c, edgecolor="black",
                         linewidth=0.3, label=l)
                   for l, c in zip(cats_show, colors_show)]
    src_handles = [
        Patch(facecolor="#888888", edgecolor="black",
              linewidth=0.3, label="AgERA5 (solid)"),
        Patch(facecolor="#888888", edgecolor="black",
              linewidth=0.3, alpha=0.55, hatch="///",
              label="Observed (hatch)"),
    ]

    leg1 = fig.legend(handles=cat_handles, loc="lower center",
                       bbox_to_anchor=(0.35, 0.005), ncol=4,
                       fontsize=8, frameon=False, handlelength=1.5)
    leg2 = fig.legend(handles=src_handles, loc="lower center",
                       bbox_to_anchor=(0.80, 0.005), ncol=1,
                       fontsize=7.5, frameon=False, handlelength=1.5)
    fig.add_artist(leg1)

    safe_save(fig, os.path.join(FIG_DIR, "fig_f3_frequency_compare.png"))
    safe_save(fig, os.path.join(FIG_DIR, "fig_f3_frequency_compare.pdf"))
    plt.close(fig)


def plot_fig4_events(events_df):
    """Duration × severity — top: AgERA5, bottom: Observed"""
    print("🎨 Fig F4: Drought events (AgERA5 vs Observed) ...")

    if len(events_df) == 0:
        return

    fig, axes = plt.subplots(2, 4, figsize=(W_DOUBLE, 130 * MM))
    plt.subplots_adjust(wspace=0.34, hspace=0.30,
                        left=0.075, right=0.98,
                        top=0.92, bottom=0.15)

    sc = None
    for j, src in enumerate(["AgERA5", "Observed"]):
        for i, ts in enumerate(TIMESCALES):
            ax = axes[j, i]
            sub = events_df[(events_df["timescale"] == ts) &
                              (events_df["source"] == src)]
            if len(sub) == 0:
                continue

            sc = ax.scatter(sub["duration_months"], sub["severity"],
                            c=sub["min_spei"], cmap="RdYlBu_r",
                            s=25, alpha=0.78,
                            edgecolors="black", linewidths=0.3,
                            vmin=-3, vmax=0)
            ax.axhline(0, color="0.6", lw=0.4, ls=":")
            ax.set_xlabel("Duration (months)")
            if i == 0:
                ax.set_ylabel(f"{src}\nSeverity ($\\sum$ SPEI)")
            ax.set_title(f"SPEI-{ts}", pad=4, fontsize=9)
            add_panel_letter(ax, chr(ord("a") + i + j * 4),
                              xoff=-0.20, yoff=1.03)

    if sc is not None:
        cbar_ax = fig.add_axes([0.30, 0.02, 0.40, 0.02])
        cb = fig.colorbar(sc, cax=cbar_ax, orientation="horizontal")
        cb.set_label("Minimum SPEI during event", fontsize=8)
        cb.ax.tick_params(labelsize=7)

    safe_save(fig, os.path.join(FIG_DIR, "fig_f4_events_compare.png"))
    safe_save(fig, os.path.join(FIG_DIR, "fig_f4_events_compare.pdf"))
    plt.close(fig)


def plot_fig5_spatial(spei_age, spei_obs):
    """Spatial trend — 2 panels (AgERA5 | Observed)"""
    print("🎨 Fig F5: Spatial trend comparison ...")

    def compute_trends(spei_df):
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
        return pd.DataFrame(rows)

    df_a = compute_trends(spei_age)
    df_o = compute_trends(spei_obs)

    vmax = max(abs(df_a["slope"].max()), abs(df_a["slope"].min()),
               abs(df_o["slope"].max()), abs(df_o["slope"].min()))
    vmax = max(np.ceil(vmax * 10) / 10, 0.1)

    fig, axes = plt.subplots(1, 2, figsize=(W_DOUBLE, 105 * MM))
    plt.subplots_adjust(wspace=0.15, left=0.075, right=0.98,
                        top=0.90, bottom=0.14)

    for ax, (df, title, letter) in zip(
        axes,
        [(df_a, "AgERA5", "a"),
         (df_o, "Observed Precip + AgERA5 ETo", "b")]
    ):
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

        for _, row in df.iterrows():
            stn = row["stncode"]
            dx, dy = SPATIAL_OFFSETS.get(stn, (0, -15))
            name = STATIONS.get(stn, str(stn))
            abbr = STN_ABBR.get(name, name)
            ax.annotate(abbr, xy=(row["lon"], row["lat"]),
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
        if letter == "a":
            ax.set_ylabel("Latitude (°N)")
        ax.set_title(title, pad=6, fontsize=9.5)
        ax.grid(True, color="0.9", lw=0.4, ls=":")
        add_panel_letter(ax, letter, xoff=-0.14, yoff=1.03)

    # Colorbar
    sm = ScalarMappable(cmap="RdBu", norm=Normalize(-vmax, vmax))
    sm.set_array([])
    cbar_ax = fig.add_axes([0.30, 0.02, 0.40, 0.02])
    cb = fig.colorbar(sm, cax=cbar_ax, orientation="horizontal")
    cb.set_label(r"SPEI-12 trend (dec$^{-1}$)", fontsize=8)
    cb.ax.tick_params(labelsize=7)

    safe_save(fig, os.path.join(FIG_DIR, "fig_f5_spatial_compare.png"))
    safe_save(fig, os.path.join(FIG_DIR, "fig_f5_spatial_compare.pdf"))
    plt.close(fig)


def plot_fig6_timescale_comparison(spei_age, spei_obs):
    """Timescale comparison — AgERA5 (solid) vs Observed (dashed)"""
    print("🎨 Fig F6: Timescale comparison (both sources) ...")

    fig, ax = plt.subplots(figsize=(W_DOUBLE, 90 * MM))
    plt.subplots_adjust(left=0.075, right=0.98, top=0.90, bottom=0.16)

    colors = ["#F2C265", "#E5A03A", "#C1440E", "#8C1F0E"]

    # AgERA5 — solid
    for ts, c in zip(TIMESCALES, colors):
        sub = spei_age[spei_age["timescale"] == ts]
        reg = sub.groupby("date")["spei"].mean().sort_index()
        ax.plot(reg.index, reg.values, "-", color=c, lw=1.0,
                alpha=0.9, label=f"AgERA5 SPEI-{ts}")

    # Observed — dashed, same colors
    for ts, c in zip(TIMESCALES, colors):
        sub = spei_obs[spei_obs["timescale"] == ts]
        reg = sub.groupby("date")["spei"].mean().sort_index()
        ax.plot(reg.index, reg.values, "--", color=c, lw=0.9,
                alpha=0.7, label=f"Observed SPEI-{ts}")

    ax.axhline(0, color="black", lw=0.6)
    ax.axhline(-1, color="0.5", lw=0.6, ls=":", alpha=0.7)
    ax.axhline(-1.5, color="0.3", lw=0.6, ls=":", alpha=0.7)

    ax.set_xlabel("Year")
    ax.set_ylabel("SPEI (regional mean)")
    ax.set_ylim(-3.2, 3.2)
    ax.yaxis.set_major_locator(MultipleLocator(1))
    ax.yaxis.set_minor_locator(MultipleLocator(0.5))
    ax.xaxis.set_major_locator(mpl.dates.YearLocator(5))
    ax.xaxis.set_minor_locator(mpl.dates.YearLocator(1))
    ax.set_title("SPEI timescales — AgERA5 (solid) vs Observed (dashed)",
                 pad=6, fontsize=9.5)
    ax.legend(loc="lower right", ncol=4, fontsize=6.5,
              framealpha=0.95)

    safe_save(fig, os.path.join(FIG_DIR, "fig_f6_timescale_compare.png"))
    safe_save(fig, os.path.join(FIG_DIR, "fig_f6_timescale_compare.pdf"))
    plt.close(fig)


def plot_fig7_validation(spei_age, spei_obs):
    """Scatter validation — AgERA5 vs Observed per timescale"""
    print("🎨 Fig F7: SPEI validation (AgERA5 vs Observed) ...")

    fig, axes = plt.subplots(1, 4, figsize=(W_DOUBLE, 80 * MM))
    plt.subplots_adjust(wspace=0.30, left=0.075, right=0.98,
                        top=0.86, bottom=0.18)

    for i, (ax, ts) in enumerate(zip(axes, TIMESCALES)):
        a = (spei_age[spei_age["timescale"] == ts]
                .groupby(["stncode", "date"])["spei"].mean()
                .rename("age").reset_index())
        o = (spei_obs[spei_obs["timescale"] == ts]
                .groupby(["stncode", "date"])["spei"].mean()
                .rename("obs").reset_index())

        m = a.merge(o, on=["stncode", "date"], how="inner")

        ax.scatter(m["obs"], m["age"], s=6, alpha=0.35,
                   c="#1F6FB4", edgecolors="none")

        # 1:1 line
        lim = 3.0
        ax.plot([-lim, lim], [-lim, lim], "--",
                color="black", lw=0.8, alpha=0.7)
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
        ax.set_aspect("equal")

        # Metrics
        if len(m) > 10:
            r, _ = stats.pearsonr(m["obs"], m["age"])
            rmse = np.sqrt(np.mean((m["age"] - m["obs"]) ** 2))
            bias = (m["age"] - m["obs"]).mean()
            txt = (f"$n$ = {len(m):,}\n"
                   f"$r$ = {r:.3f}\n"
                   f"RMSE = {rmse:.2f}\n"
                   f"Bias = {bias:+.2f}")
        else:
            txt = "insufficient"
        ax.text(0.03, 0.97, txt, transform=ax.transAxes,
                ha="left", va="top", fontsize=7,
                bbox=dict(boxstyle="round,pad=0.3",
                          facecolor="white", edgecolor="0.7",
                          lw=0.5, alpha=0.95))

        ax.set_xlabel(f"Observed SPEI-{ts}")
        if i == 0:
            ax.set_ylabel("AgERA5 SPEI")
        ax.set_title(f"SPEI-{ts}", pad=6, fontsize=9.5)
        add_panel_letter(ax, chr(ord("a") + i), xoff=-0.15, yoff=1.03)

    safe_save(fig, os.path.join(FIG_DIR, "fig_f7_validation.png"))
    safe_save(fig, os.path.join(FIG_DIR, "fig_f7_validation.pdf"))
    plt.close(fig)


# ================================================================
# 7. Main
# ================================================================
def main():
    print("=" * 70)
    print("Stage 2 - Module F (compare): AgERA5 vs Observed SPEI")
    print("=" * 70)

    # 1. Load
    eto_m = load_eto_monthly()
    prec_age_m = load_precip_agera5_monthly()
    prec_obs_m = load_precip_observed_monthly()

    # 2. Merge
    df_age, df_obs, common = merge_datasets(eto_m, prec_age_m, prec_obs_m)

    if len(common) == 0:
        print("❌ ไม่มีสถานีตรงกัน")
        return

    # 3. Compute SPEI both
    spei_age, spei_obs = compute_spei_both(df_age, df_obs)

    if len(spei_age) == 0 or len(spei_obs) == 0:
        print("❌ SPEI ว่างเปล่า")
        return

    # 4. Save tables
    print("\n💾 บันทึกตาราง ...")
    spei_age["station"] = spei_age["stncode"].map(STATIONS)
    spei_obs["station"] = spei_obs["stncode"].map(STATIONS)

    all_spei = pd.concat([
        spei_age.assign(source="AgERA5"),
        spei_obs.assign(source="Observed"),
    ], ignore_index=True)
    all_spei.to_csv(os.path.join(TAB_DIR, "table_spei_compare_full.csv"),
                    index=False, float_format="%.3f")

    # Trends
    trends = spei_trends(all_spei)
    trends.to_csv(os.path.join(TAB_DIR, "table_spei_compare_trends.csv"),
                  index=False, float_format="%.3f")

    # Frequency by decade
    freq = drought_frequency(all_spei)
    freq["decade"] = "all"
    all_spei_c = all_spei.copy()
    all_spei_c["year"] = all_spei_c["date"].dt.year
    all_spei_c["decade"] = pd.cut(all_spei_c["year"],
                                    bins=[1978, 1988, 1998, 2007],
                                    labels=["1979–88", "1989–98", "1999–2007"])
    all_spei_c["category"] = all_spei_c["spei"].apply(classify_spei)

    freq_by_dec = []
    for ts in TIMESCALES:
        for src in all_spei_c["source"].unique():
            sub = all_spei_c[(all_spei_c["timescale"] == ts) &
                              (all_spei_c["source"] == src)]
            cross = (sub.groupby(["decade", "category"])
                        .size().unstack(fill_value=0))
            totals = cross.sum(axis=1)
            pct = cross.div(totals, axis=0) * 100
            for dec in pct.index:
                for cat in pct.columns:
                    freq_by_dec.append({
                        "timescale": ts, "source": src,
                        "decade": str(dec),
                        "category": cat,
                        "frequency_pct": float(pct.loc[dec, cat]),
                    })
    freq_dec_df = pd.DataFrame(freq_by_dec)
    freq_dec_df.to_csv(os.path.join(TAB_DIR, "table_spei_frequency_decade.csv"),
                       index=False, float_format="%.2f")

    # Events
    events = drought_events(all_spei)
    events.to_csv(os.path.join(TAB_DIR, "table_spei_compare_events.csv"),
                  index=False, float_format="%.3f")

    # 5. Figures
    print()
    plot_fig1_timeseries(spei_age, spei_obs)
    plot_fig2_heatmap(spei_age)
    plot_fig3_frequency(freq_dec_df)
    plot_fig4_events(events)
    plot_fig5_spatial(spei_age, spei_obs)
    plot_fig6_timescale_comparison(spei_age, spei_obs)
    plot_fig7_validation(spei_age, spei_obs)

    # 6. Summary
    print("\n" + "=" * 70)
    print("📊 Verification & Summary")
    print("=" * 70)

    for source, spei_df in [("AgERA5", spei_age), ("Observed", spei_obs)]:
        print(f"\n📌 {source}:")
        print(f"   {'Timescale':<10s}  mean   std    "
              f"ExtD  SevD  ModD  Near")
        for ts in TIMESCALES:
            sub = spei_df[spei_df["timescale"] == ts]
            n = len(sub)
            cat = sub["spei"].apply(classify_spei)
            print(f"   SPEI-{ts:<2d}    "
                  f"{sub['spei'].mean():+.3f} {sub['spei'].std():.3f}  "
                  f"{(cat=='Extremely dry').mean()*100:5.2f} "
                  f"{(cat=='Severely dry').mean()*100:5.2f} "
                  f"{(cat=='Moderately dry').mean()*100:5.2f} "
                  f"{(cat=='Near normal').mean()*100:5.2f}")

    # Correlation
    print(f"\n📌 Correlation AgERA5 vs Observed (regional means):")
    for ts in TIMESCALES:
        a = spei_age[spei_age["timescale"] == ts]
        o = spei_obs[spei_obs["timescale"] == ts]
        ra = a.groupby("date")["spei"].mean().rename("a")
        ro = o.groupby("date")["spei"].mean().rename("o")
        m = pd.concat([ra, ro], axis=1).dropna()
        if len(m) > 10:
            r, _ = stats.pearsonr(m["a"], m["o"])
            print(f"   SPEI-{ts:<2d}: r = {r:.3f} (n = {len(m)})")

    # Regional trends
    print(f"\n📌 Regional SPEI-12 trends:")
    for src in ["AgERA5", "Observed"]:
        sub = trends[(trends["source"] == src) &
                       (trends["timescale"] == 12) &
                       (trends["stncode"] == 0)]
        if len(sub) > 0:
            r = sub.iloc[0]
            stars = ("***" if r["p_value"] < 0.001 else
                     "**"  if r["p_value"] < 0.01  else
                     "*"   if r["p_value"] < 0.05  else "n.s.")
            print(f"   {src:<10s}: slope = "
                  f"{r['slope_per_decade']:+.4f} dec⁻¹  "
                  f"p = {r['p_value']:.3f} ({stars})")

    print(f"\n📁 Tables : {os.path.abspath(TAB_DIR)}")
    print(f"📁 Figures: {os.path.abspath(FIG_DIR)}")
    print("=" * 70)


if __name__ == "__main__":
    main()