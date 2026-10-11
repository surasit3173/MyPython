"""
Stage 2 - Module D: Validation of AgERA5 precipitation
against station observations (1979-2007)

Inputs:
  - data/observed_precip.csv                    (monthly, 15 stations, 1961-2008)
  - ฝนรายวันอีสาน10สถานี 1961 2014 obs.xlsx     (daily, 10 stations, 1961-2014)
  - data/agera5_precip_station_daily_arco.csv   (from download_fao_precip_arco.py)
  - data/agera5_precip_station_monthly_arco.csv

Outputs:
  - outputs/module_d/tables/*.csv
  - outputs/module_d/figures/fig{1..6}_*.{png}

Q4 journal level: Times New Roman, 300+ dpi, standard validation metrics
"""

# ================================================================
# 0. Imports
# ================================================================
import os
import sys
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D
from matplotlib.ticker import MultipleLocator
from scipy import stats

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

CLR_OBS = "#1A1A1A"
CLR_AGE = "#C1440E"
CLR_1TO1 = "#1F6FB4"
WET_THRESHOLD = 1.0   # mm/day for daily wet-day detection


# ================================================================
# 2. Paths & config
# ================================================================
BASE_DIR = "."
DATA_DIR = os.path.join(BASE_DIR, "data")
OUT_DIR  = os.path.join(BASE_DIR, "outputs", "module_d")
FIG_DIR  = os.path.join(OUT_DIR, "figures")
TAB_DIR  = os.path.join(OUT_DIR, "tables")
os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(TAB_DIR, exist_ok=True)

# ⚠️ ตรวจสอบ path เหล่านี้ให้ตรงกับไฟล์จริง
OBS_MONTHLY_CSV = os.path.join(DATA_DIR, "observed_precip.csv")
OBS_DAILY_XLSX  = os.path.join(BASE_DIR, "ฝนรายวันอีสาน10สถานี 1961 2014 obs.xlsx")
AGE_DAILY_CSV   = os.path.join(DATA_DIR, "agera5_precip_station_daily_arco.csv")
AGE_MONTHLY_CSV = os.path.join(DATA_DIR, "agera5_precip_station_monthly_arco.csv")

# ช่วง overlap ระหว่าง AgERA5 (1979-2007) กับ observations
YEAR_START, YEAR_END = 1979, 2007

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


# ================================================================
# 3. Loaders
# ================================================================
def load_observed_monthly():
    """อ่าน observed monthly CSV (wide format) → long"""
    if not os.path.exists(OBS_MONTHLY_CSV):
        print(f"⚠️  ไม่พบ {OBS_MONTHLY_CSV}")
        return None

    print(f"📂 โหลด observed monthly: {os.path.basename(OBS_MONTHLY_CSV)}")
    df = pd.read_csv(OBS_MONTHLY_CSV)
    df.columns = [c.strip() for c in df.columns]

    # ตรวจคอลัมน์ YEAR, MONTH
    if "YEAR" not in df.columns or "MONTH" not in df.columns:
        raise ValueError(f"ต้องมีคอลัมน์ YEAR, MONTH — พบ {list(df.columns)}")

    # Melt to long
    stn_cols = [c for c in df.columns if c not in ("YEAR", "MONTH")]
    obs = df.melt(id_vars=["YEAR", "MONTH"],
                  value_vars=stn_cols,
                  var_name="stncode",
                  value_name="obs")
    obs["stncode"] = obs["stncode"].astype(int)
    obs["date"] = pd.to_datetime(
        dict(year=obs["YEAR"], month=obs["MONTH"], day=1))
    obs = obs[["stncode", "date", "obs"]].dropna(subset=["obs"])

    # Filter to overlap period
    obs = obs[(obs["date"].dt.year >= YEAR_START) &
              (obs["date"].dt.year <= YEAR_END)]
    print(f"   {len(obs):,} ค่า | {obs['stncode'].nunique()} สถานี | "
          f"{obs['date'].dt.year.min()}-{obs['date'].dt.year.max()}")
    return obs


def load_observed_daily():
    """อ่าน observed daily Excel (10 สถานี) — รองรับหลายรูปแบบ"""
    if not os.path.exists(OBS_DAILY_XLSX):
        print(f"⚠️  ไม่พบ {OBS_DAILY_XLSX}")
        return None

    print(f"📂 โหลด observed daily: {os.path.basename(OBS_DAILY_XLSX)}")

    # ลองอ่านทุก sheet แล้วเลือก sheet ที่ดูเหมือนข้อมูล
    xl = pd.ExcelFile(OBS_DAILY_XLSX)
    print(f"   sheets: {xl.sheet_names}")

    df = None
    for sheet in xl.sheet_names:
        try:
            tmp = pd.read_excel(OBS_DAILY_XLSX, sheet_name=sheet)
            if len(tmp) > 100:   # ต้องมีข้อมูลมากพอ
                df = tmp
                print(f"   ใช้ sheet: '{sheet}' ({len(tmp):,} แถว)")
                break
        except Exception:
            continue

    if df is None:
        raise ValueError("ไม่พบ sheet ที่มีข้อมูลใน Excel")

    df.columns = [str(c).strip() for c in df.columns]

    # ----- ตรวจสอบรูปแบบ (long หรือ wide) -----
    cols_lower = [c.lower() for c in df.columns]

    # Pattern 1: Long (date + stncode + precip)
    has_long = any(c in cols_lower for c in ("date", "datetime", "time", "day")) \
               and any(c in cols_lower for c in ("stncode", "stn", "station"))
    # Pattern 2: Wide (date + station columns)
    stn_like_cols = [c for c in df.columns if c.isdigit() and len(c) == 6]
    has_wide = len(stn_like_cols) >= 5

    if has_long:
        print("   รูปแบบ: LONG")
        date_col = next(c for c in df.columns
                        if c.lower() in ("date", "datetime", "time", "day"))
        stn_col  = next(c for c in df.columns
                        if c.lower() in ("stncode", "stn", "station"))
        prec_col = next((c for c in df.columns
                         if c.lower() in ("precip", "precipitation",
                                          "rain", "rainfall")), None)
        if prec_col is None:
            # หาคอลัมน์ที่เป็นตัวเลขเท่านั้น
            num_cols = [c for c in df.columns
                        if pd.api.types.is_numeric_dtype(df[c])
                        and c not in (date_col, stn_col)]
            prec_col = num_cols[0]

        obs = df.rename(columns={date_col: "date",
                                 stn_col: "stncode",
                                 prec_col: "obs"})[["date", "stncode", "obs"]]
        obs["stncode"] = obs["stncode"].astype(int)

    elif has_wide:
        print(f"   รูปแบบ: WIDE ({len(stn_like_cols)} สถานี)")
        # หาคอลัมน์วันที่
        date_col = next((c for c in df.columns
                         if c.lower() in ("date", "datetime", "time", "day",
                                          "year", "วันที่")),
                        df.columns[0])
        # ถ้าเป็น YEAR+MONTH+DAY ให้รวม
        if "YEAR" in df.columns or "year" in cols_lower:
            year_col = next(c for c in df.columns if c.lower() == "year")
            month_col = next((c for c in df.columns
                              if c.lower() == "month"), None)
            day_col = next((c for c in df.columns
                            if c.lower() in ("day", "date")), None)
            if month_col and day_col:
                df["date"] = pd.to_datetime(
                    dict(year=df[year_col],
                         month=df[month_col],
                         day=df[day_col]),
                    errors="coerce")
        else:
            df["date"] = pd.to_datetime(df[date_col], errors="coerce")

        obs = df.melt(id_vars=["date"],
                      value_vars=stn_like_cols,
                      var_name="stncode",
                      value_name="obs")
        obs["stncode"] = obs["stncode"].astype(int)
        obs = obs[["date", "stncode", "obs"]]
    else:
        raise ValueError(
            f"ไม่รู้จักรูปแบบ Excel\n"
            f"   คอลัมน์: {list(df.columns)[:10]}\n"
            f"   ต้องมีอย่างน้อย: date + station columns (6 หลัก)"
        )

    obs["date"] = pd.to_datetime(obs["date"], errors="coerce")
    obs = obs.dropna(subset=["date", "obs"])
    obs = obs[(obs["date"].dt.year >= YEAR_START) &
              (obs["date"].dt.year <= YEAR_END)]
    print(f"   {len(obs):,} ค่า | {obs['stncode'].nunique()} สถานี | "
          f"{obs['date'].dt.year.min()}-{obs['date'].dt.year.max()}")
    return obs


def load_agera5_daily():
    if not os.path.exists(AGE_DAILY_CSV):
        print(f"⚠️  ไม่พบ {AGE_DAILY_CSV}")
        print(f"   → รัน download_fao_precip_arco.py ก่อน")
        return None
    print(f"📂 โหลด AgERA5 daily...")
    df = pd.read_csv(AGE_DAILY_CSV, parse_dates=["time"])
    df = df.rename(columns={"time": "date", "precip_mm_day": "agera5"})
    df["stncode"] = df["stncode"].astype(int)
    df = df[["stncode", "date", "agera5"]].dropna()
    print(f"   {len(df):,} ค่า | {df['stncode'].nunique()} สถานี")
    return df


def load_agera5_monthly():
    """โหลด AgERA5 monthly — ถ้าไม่มีไฟล์ จะ aggregate จาก daily เอง"""
    if os.path.exists(AGE_MONTHLY_CSV):
        print(f"📂 โหลด AgERA5 monthly...")
        df = pd.read_csv(AGE_MONTHLY_CSV, parse_dates=["date"])
        df = df.rename(columns={"precip_mm_month": "agera5"})
        df["stncode"] = df["stncode"].astype(int)
        return df[["stncode", "date", "agera5"]].dropna()

    # Fallback: aggregate from daily
    print(f"   ไม่พบ monthly CSV — aggregate จาก daily")
    daily = load_agera5_daily()
    if daily is None:
        return None
    daily["year"]  = daily["date"].dt.year
    daily["month"] = daily["date"].dt.month
    monthly = (daily.groupby(["stncode", "year", "month"])
                    .agg(agera5=("agera5", "sum"),
                         n=("agera5", "count"))
                    .reset_index())
    monthly = monthly[monthly["n"] >= 25].drop(columns="n")
    monthly["date"] = pd.to_datetime(
        dict(year=monthly["year"], month=monthly["month"], day=1))
    return monthly[["stncode", "date", "agera5"]]


# ================================================================
# 4. Metrics
# ================================================================
def continuous_metrics(obs, age):
    obs = np.asarray(obs, dtype=float)
    age = np.asarray(age, dtype=float)
    m = ~(np.isnan(obs) | np.isnan(age))
    obs, age = obs[m], age[m]
    n = len(obs)
    if n < 10:
        return None
    m_obs = obs.mean()
    bias  = age.mean() - m_obs
    rmse  = np.sqrt(np.mean((age - obs) ** 2))
    mae   = np.mean(np.abs(age - obs))
    if obs.std() > 0 and age.std() > 0:
        r, p = stats.pearsonr(obs, age)
    else:
        r, p = np.nan, np.nan
    pbias = 100 * bias / m_obs if m_obs > 0 else np.nan
    nse = 1 - np.sum((age - obs) ** 2) / np.sum((obs - m_obs) ** 2) \
          if np.sum((obs - m_obs) ** 2) > 0 else np.nan
    return {
        "n": int(n),
        "mean_obs": float(m_obs), "mean_age": float(age.mean()),
        "sd_obs":   float(obs.std()), "sd_age": float(age.std()),
        "bias": float(bias), "pbias_pct": float(pbias),
        "rmse": float(rmse), "mae": float(mae),
        "r": float(r), "r2": float(r**2), "p_value": float(p),
        "nse": float(nse),
    }


def categorical_metrics(obs, age, thr=WET_THRESHOLD):
    obs = np.asarray(obs, dtype=float)
    age = np.asarray(age, dtype=float)
    m = ~(np.isnan(obs) | np.isnan(age))
    obs, age = obs[m], age[m]

    obs_wet = obs >= thr
    age_wet = age >= thr

    H = int(np.sum(obs_wet & age_wet))
    M = int(np.sum(obs_wet & ~age_wet))
    F = int(np.sum(~obs_wet & age_wet))
    C = int(np.sum(~obs_wet & ~age_wet))
    total = H + M + F + C

    pod = H / (H + M) if (H + M) > 0 else np.nan
    far = F / (H + F) if (H + F) > 0 else np.nan
    csi = H / (H + M + F) if (H + M + F) > 0 else np.nan
    acc = (H + C) / total if total > 0 else np.nan
    bs  = (H + F) / (H + M) if (H + M) > 0 else np.nan
    return {"hits": H, "misses": M, "false_alarms": F, "correct_neg": C,
            "pod": float(pod), "far": float(far),
            "csi": float(csi), "accuracy": float(acc),
            "bias_score": float(bs)}


# ================================================================
# 5. Tables
# ================================================================
def table1_metrics_by_station(merged, unit, fname):
    """Table: continuous metrics per station"""
    print(f"📊 {fname} ...")
    rows = []
    for stn in sorted(merged["stncode"].unique()):
        sub = merged[merged["stncode"] == stn]
        m = continuous_metrics(sub["obs"].values, sub["agera5"].values)
        if m is None:
            continue
        m["stncode"] = stn
        m["station"] = STATIONS.get(stn, str(stn))
        rows.append(m)

    # Add ALL row
    m_all = continuous_metrics(merged["obs"].values, merged["agera5"].values)
    if m_all is not None:
        m_all["stncode"] = 0
        m_all["station"] = "ALL STATIONS"
        rows.append(m_all)

    cols = ["stncode", "station", "n", "mean_obs", "mean_age",
            "sd_obs", "sd_age", "bias", "pbias_pct",
            "rmse", "mae", "r", "r2", "nse"]
    df = pd.DataFrame(rows)[cols]
    df.to_csv(os.path.join(TAB_DIR, fname), index=False,
              float_format="%.3f")
    return df


def table2_categorical(merged, fname):
    print(f"📊 {fname} ...")
    rows = []
    for stn in sorted(merged["stncode"].unique()):
        sub = merged[merged["stncode"] == stn]
        m = categorical_metrics(sub["obs"].values, sub["agera5"].values)
        m["stncode"] = stn
        m["station"] = STATIONS.get(stn, str(stn))
        rows.append(m)
    m_all = categorical_metrics(merged["obs"].values, merged["agera5"].values)
    m_all["stncode"] = 0
    m_all["station"] = "ALL STATIONS"
    rows.append(m_all)

    cols = ["stncode", "station", "hits", "misses", "false_alarms",
            "correct_neg", "pod", "far", "csi", "accuracy", "bias_score"]
    df = pd.DataFrame(rows)[cols]
    df.to_csv(os.path.join(TAB_DIR, fname), index=False,
              float_format="%.3f")
    return df


def table3_monthly_climatology(merged):
    """Monthly climatology — averaged across stations"""
    print("📊 Monthly climatology ...")
    df = merged.copy()
    df["month"] = df["date"].dt.month

    clim = (df.groupby("month")
              .agg(mean_obs=("obs", "mean"),
                   mean_age=("agera5", "mean"),
                   sd_obs=("obs", "std"),
                   sd_age=("agera5", "std"))
              .reset_index())
    clim["bias"] = clim["mean_age"] - clim["mean_obs"]
    clim["pbias_pct"] = 100 * clim["bias"] / clim["mean_obs"]
    clim["month_name"] = clim["month"].map(
        {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
         7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"})
    clim.to_csv(os.path.join(TAB_DIR, "table3_climatology_monthly.csv"),
                index=False, float_format="%.3f")
    return clim


# ================================================================
# 6. Figures
# ================================================================
def add_panel_letter(ax, letter, xoff=-0.20, yoff=1.05):
    ax.text(xoff, yoff, letter, transform=ax.transAxes,
            fontsize=13, fontweight="bold", family="serif",
            ha="left", va="bottom", clip_on=False)


def plot_scatter(merged, unit_label, fname, xmax=None):
    """Scatter hexbin density (single panel)"""
    print(f"🎨 {fname} ...")
    obs = merged["obs"].values
    age = merged["agera5"].values
    m = continuous_metrics(obs, age)
    if m is None:
        return

    fig, ax = plt.subplots(figsize=(W_SINGLE * 1.3, 90 * MM))
    plt.subplots_adjust(left=0.15, right=0.98, top=0.94, bottom=0.16)

    vmax = xmax or max(np.nanpercentile(obs, 99.5),
                       np.nanpercentile(age, 99.5))

    hb = ax.hexbin(obs, age, gridsize=50, bins="log", cmap="Blues",
                   mincnt=1, linewidths=0, extent=(0, vmax, 0, vmax))
    cb = fig.colorbar(hb, ax=ax, pad=0.02, fraction=0.045)
    cb.set_label("log(count)", fontsize=7.5)
    cb.ax.tick_params(labelsize=7)

    ax.plot([0, vmax], [0, vmax], "--", color=CLR_1TO1,
            lw=1.0, label="1:1 line", zorder=5)

    coef = np.polyfit(obs, age, 1)
    xfit = np.linspace(0, vmax, 50)
    ax.plot(xfit, np.polyval(coef, xfit), "-", color=CLR_AGE,
            lw=1.2, label=f"Fit ($y$={coef[0]:.2f}$x$+{coef[1]:.2f})", zorder=4)

    ax.set_xlim(0, vmax); ax.set_ylim(0, vmax)
    ax.set_aspect("equal")
    ax.set_xlabel(f"Observed precipitation ({unit_label})")
    ax.set_ylabel(f"AgERA5 precipitation ({unit_label})")

    txt = (f"$n$ = {m['n']:,}\n"
           f"$r$ = {m['r']:.3f}\n"
           f"RMSE = {m['rmse']:.2f}\n"
           f"Bias = {m['bias']:+.2f}\n"
           f"PBIAS = {m['pbias_pct']:+.1f}%")
    ax.text(0.98, 0.03, txt, transform=ax.transAxes,
            ha="right", va="bottom", fontsize=7.5,
            bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                      edgecolor="0.7", lw=0.5, alpha=0.95),
            zorder=6)

    ax.legend(loc="upper left", fontsize=7.5)

    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG_DIR, f"{fname}.{ext}"))
    plt.close(fig)


def plot_timeseries(merged, unit_label, fname, agg_func="mean"):
    """Regional mean time series"""
    print(f"🎨 {fname} ...")
    df = merged.copy()
    df["year"]  = df["date"].dt.year
    df["month"] = df["date"].dt.month

    monthly = (df.groupby(["year", "month"])
                 .agg(obs=("obs", agg_func), age=("agera5", agg_func))
                 .reset_index())
    monthly["date"] = pd.to_datetime(
        dict(year=monthly["year"], month=monthly["month"], day=1))
    monthly = monthly.sort_values("date").reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(W_DOUBLE, 70 * MM))
    plt.subplots_adjust(left=0.075, right=0.98, top=0.90, bottom=0.16)

    ax.plot(monthly["date"], monthly["obs"], "o-", color=CLR_OBS,
            ms=2.5, lw=0.8, mfc="white", mec=CLR_OBS, mew=0.7,
            label="Observed")
    ax.plot(monthly["date"], monthly["age"], "s--", color=CLR_AGE,
            ms=2.5, lw=0.8, mfc="white", mec=CLR_AGE, mew=0.7,
            label="AgERA5")

    r, _ = stats.pearsonr(monthly["obs"], monthly["age"])
    rmse = np.sqrt(np.mean((monthly["age"] - monthly["obs"]) ** 2))
    ax.text(0.99, 0.98, f"$r$ = {r:.3f}\nRMSE = {rmse:.2f}",
            transform=ax.transAxes, ha="right", va="top", fontsize=8,
            bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                      edgecolor="0.7", lw=0.5))

    ax.set_xlabel("Year")
    ax.set_ylabel(f"Precipitation ({unit_label})")
    ax.set_title("Regional mean monthly precipitation",
                 pad=6, fontsize=9.5)
    ax.xaxis.set_major_locator(mpl.dates.YearLocator(5))
    ax.xaxis.set_minor_locator(mpl.dates.YearLocator(1))
    ax.legend(loc="upper left", ncol=2, fontsize=7.5)

    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG_DIR, f"{fname}.{ext}"))
    plt.close(fig)


def plot_climatology(clim, unit_label, fname):
    print(f"🎨 {fname} ...")
    fig, ax = plt.subplots(figsize=(W_SINGLE * 1.7, 75 * MM))
    plt.subplots_adjust(left=0.13, right=0.98, top=0.90, bottom=0.20)

    x = clim["month"].values
    ax.errorbar(x - 0.10, clim["mean_obs"],
                yerr=clim["sd_obs"], fmt="o-", color=CLR_OBS,
                ms=5, lw=1.2, capsize=2.5, capthick=0.7,
                mfc="white", mec=CLR_OBS, mew=1.0,
                label="Observed")
    ax.errorbar(x + 0.10, clim["mean_age"],
                yerr=clim["sd_age"], fmt="s--", color=CLR_AGE,
                ms=5, lw=1.2, capsize=2.5, capthick=0.7,
                mfc="white", mec=CLR_AGE, mew=1.0,
                label="AgERA5")

    ax.set_xticks(x)
    ax.set_xticklabels(clim["month_name"])
    ax.set_xlabel("Month")
    ax.set_ylabel(f"Precipitation ({unit_label})")
    ax.set_title("Monthly precipitation climatology",
                 pad=6, fontsize=9.5)
    ax.legend(loc="upper left", fontsize=8)
    ax.yaxis.set_minor_locator(MultipleLocator(10))

    ax.axvspan(4.5, 9.5, color="0.94", alpha=0.7, zorder=0)
    ax.text(7, ax.get_ylim()[1] * 0.95, "Wet season",
            ha="center", va="top", fontsize=8, style="italic",
            color="0.35")

    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG_DIR, f"{fname}.{ext}"))
    plt.close(fig)


def plot_boxplot(merged, unit_label, fname):
    print(f"🎨 {fname} ...")
    df = merged.copy()
    df["month"] = df["date"].dt.month

    fig, axes = plt.subplots(1, 2, figsize=(W_DOUBLE, 78 * MM),
                             sharey=True)
    plt.subplots_adjust(wspace=0.08, left=0.075, right=0.98,
                        top=0.88, bottom=0.18)

    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    for ax, (col, clr, label, letter) in zip(
        axes,
        [("obs", CLR_OBS, "Observed", "a"),
         ("agera5", CLR_AGE, "AgERA5", "b")]
    ):
        data = [df.loc[df["month"] == m, col].dropna().values
                for m in range(1, 13)]
        ax.boxplot(data, positions=np.arange(1, 13), widths=0.6,
                   patch_artist=True, showfliers=False,
                   medianprops=dict(color="black", lw=1.0),
                   whiskerprops=dict(color=clr, lw=0.8),
                   capprops=dict(color=clr, lw=0.8),
                   boxprops=dict(facecolor=clr, alpha=0.35,
                                 edgecolor=clr, lw=0.8))
        ax.set_xticks(np.arange(1, 13))
        ax.set_xticklabels(month_names, rotation=0, fontsize=7.5)
        ax.set_xlabel("Month")
        ax.set_title(label, pad=6, fontsize=9.5)
        add_panel_letter(ax, letter)

    axes[0].set_ylabel(f"Precipitation ({unit_label})")

    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG_DIR, f"{fname}.{ext}"))
    plt.close(fig)


def plot_metrics_bars(table_df, unit_label, fname):
    print(f"🎨 {fname} ...")
    df = table_df[table_df["stncode"] != 0].copy()
    df = df.sort_values("r", ascending=True).reset_index(drop=True)

    fig, axes = plt.subplots(1, 3, figsize=(W_DOUBLE, 84 * MM),
                             sharey=True)
    plt.subplots_adjust(wspace=0.08, left=0.18, right=0.98,
                        top=0.88, bottom=0.16)

    ypos = np.arange(len(df))

    # --- r ---
    ax = axes[0]
    ax.barh(ypos, df["r"], color=CLR_1TO1, edgecolor="black",
            linewidth=0.4, height=0.7)
    for i, v in enumerate(df["r"]):
        ax.text(v + 0.01, i, f"{v:.2f}", va="center", ha="left",
                fontsize=6.8)
    ax.set_yticks(ypos)
    ax.set_yticklabels(df["station"], fontsize=7.5)
    ax.set_xlabel("Pearson $r$")
    ax.set_xlim(0, 1.0)
    ax.set_title("Correlation", pad=6, fontsize=9.5)
    add_panel_letter(ax, "a", xoff=-0.45)

    # --- RMSE ---
    ax = axes[1]
    ax.barh(ypos, df["rmse"], color=CLR_AGE, edgecolor="black",
            linewidth=0.4, height=0.7)
    for i, v in enumerate(df["rmse"]):
        ax.text(v + 0.1, i, f"{v:.1f}", va="center", ha="left",
                fontsize=6.8)
    ax.set_xlabel(f"RMSE ({unit_label})")
    ax.set_title("RMSE", pad=6, fontsize=9.5)
    add_panel_letter(ax, "b", xoff=-0.10)

    # --- PBIAS ---
    ax = axes[2]
    colors = ["#C1440E" if v < 0 else "#1F6FB4"
              for v in df["pbias_pct"]]
    ax.barh(ypos, df["pbias_pct"], color=colors, edgecolor="black",
            linewidth=0.4, height=0.7)
    ax.axvline(0, color="black", lw=0.8)
    for i, v in enumerate(df["pbias_pct"]):
        off = 1.5 if v > 0 else -1.5
        ax.text(v + off, i, f"{v:+.0f}%", va="center",
                ha="left" if v > 0 else "right", fontsize=6.8)
    ax.set_xlabel("PBIAS (%)")
    ax.set_title("Percent bias", pad=6, fontsize=9.5)
    add_panel_letter(ax, "c", xoff=-0.10)

    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG_DIR, f"{fname}.{ext}"))
    plt.close(fig)


# ================================================================
# 7. Process each dataset
# ================================================================
def process_monthly():
    print("\n" + "=" * 70)
    print("📌 Monthly validation (15 stations)")
    print("=" * 70)

    obs = load_observed_monthly()
    age = load_agera5_monthly()
    if obs is None or age is None:
        return None

    merged = obs.merge(age, on=["stncode", "date"], how="inner")
    print(f"   Merged: {len(merged):,} ค่า | "
          f"{merged['stncode'].nunique()} สถานี")

    # Tables
    t1 = table1_metrics_by_station(merged, "mm month$^{-1}$",
                                    "table1_monthly_continuous.csv")
    t3 = table3_monthly_climatology(merged)

    # Figures
    plot_scatter(merged, "mm month$^{-1}$", "fig1_scatter_monthly",
                 xmax=600)
    plot_timeseries(merged, "mm month$^{-1}$",
                    "fig2_timeseries_monthly", agg_func="mean")
    plot_climatology(t3, "mm month$^{-1}$", "fig3_climatology_monthly")
    plot_boxplot(merged, "mm month$^{-1}$", "fig4_boxplot_monthly")
    plot_metrics_bars(t1, "mm month$^{-1}$", "fig5_metrics_monthly")

    return {"merged": merged, "table1": t1, "clim": t3}


def process_daily():
    print("\n" + "=" * 70)
    print("📌 Daily validation (10 stations)")
    print("=" * 70)

    obs = load_observed_daily()
    age = load_agera5_daily()
    if obs is None or age is None:
        return None

    # เก็บเฉพาะสถานีที่มีทั้ง 2 ฝั่ง
    common_stn = set(obs["stncode"].unique()) & set(age["stncode"].unique())
    obs = obs[obs["stncode"].isin(common_stn)]
    age = age[age["stncode"].isin(common_stn)]
    print(f"   สถานีที่ตรงกัน: {len(common_stn)}")

    merged = obs.merge(age, on=["stncode", "date"], how="inner")
    print(f"   Merged: {len(merged):,} ค่า | "
          f"{merged['stncode'].nunique()} สถานี | "
          f"{merged['date'].dt.year.min()}-{merged['date'].dt.year.max()}")

    # Tables
    t1 = table1_metrics_by_station(merged, "mm day$^{-1}$",
                                    "table2_daily_continuous.csv")
    t2 = table2_categorical(merged, "table3_daily_categorical.csv")

    # Figures
    plot_scatter(merged, "mm day$^{-1}$", "fig6_scatter_daily", xmax=80)
    plot_metrics_bars(t1, "mm day$^{-1}$", "fig7_metrics_daily")

    return {"merged": merged, "table1": t1, "table2": t2}


# ================================================================
# 8. Main
# ================================================================
def main():
    print("=" * 70)
    print("Stage 2 - Module D: Precipitation Validation")
    print("=" * 70)

    result_m = process_monthly()
    result_d = process_daily()

    # ---- Summary ----
    print("\n" + "=" * 70)
    print("📊 สรุปผลรวม")
    print("=" * 70)

    if result_m:
        all_row = result_m["table1"][result_m["table1"]["stncode"] == 0]
        if len(all_row):
            r = all_row.iloc[0]
            print(f"\n📌 Monthly (15 stations):")
            print(f"   n = {int(r['n']):,}")
            print(f"   Mean obs = {r['mean_obs']:.1f}  |  Mean age = {r['mean_age']:.1f} mm/month")
            print(f"   Bias = {r['bias']:+.2f} mm/month ({r['pbias_pct']:+.1f}%)")
            print(f"   RMSE = {r['rmse']:.2f}  |  MAE = {r['mae']:.2f} mm/month")
            print(f"   r = {r['r']:.3f}  |  NSE = {r['nse']:.3f}")

    if result_d:
        all_row = result_d["table1"][result_d["table1"]["stncode"] == 0]
        if len(all_row):
            r = all_row.iloc[0]
            print(f"\n📌 Daily (10 stations):")
            print(f"   n = {int(r['n']):,}")
            print(f"   Mean obs = {r['mean_obs']:.3f}  |  Mean age = {r['mean_age']:.3f} mm/day")
            print(f"   Bias = {r['bias']:+.3f} mm/day ({r['pbias_pct']:+.1f}%)")
            print(f"   RMSE = {r['rmse']:.3f}  |  MAE = {r['mae']:.3f} mm/day")
            print(f"   r = {r['r']:.3f}  |  NSE = {r['nse']:.3f}")

        cat_all = result_d["table2"][result_d["table2"]["stncode"] == 0]
        if len(cat_all):
            c = cat_all.iloc[0]
            print(f"\n   Categorical wet-day (≥ {WET_THRESHOLD} mm):")
            print(f"   POD = {c['pod']:.3f}  |  FAR = {c['far']:.3f}")
            print(f"   CSI = {c['csi']:.3f}  |  Accuracy = {c['accuracy']:.3f}")

    print(f"\n📁 Tables : {os.path.abspath(TAB_DIR)}")
    print(f"📁 Figures: {os.path.abspath(FIG_DIR)}")
    print("=" * 70)


if __name__ == "__main__":
    main()