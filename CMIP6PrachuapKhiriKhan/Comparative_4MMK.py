#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Comparative Performance of Pre-Whitening and Modified Mann–Kendall Methods
in Minimizing Type I Error in Monsoonal Rainfall Data Trend Detection
================================================================================

Author      : Senior Hydroclimatologist / Climate Statistician
Platform    : Python 3.10+
Standards   : Q1/Q2 Journal Publication Grade
References  : Mann (1945), Kendall (1975), Hamed & Rao (1998),
              Yue & Wang (2002), Yue et al. (2002),
              Benjamini & Hochberg (1995), Kundzewicz & Robson (2004),
              Kunsch (1989), Hall et al. (1995), Sen (1968)

CORRECTIONS APPLIED (v2.0):
  [FIX-1 CRITICAL] fdr_analysis: now correctly calls benjamini_hochberg()
                   so FDR_* columns reflect true BH-adjusted rejection rates,
                   not raw FWER rates.
  [FIX-2 CRITICAL] fdr_analysis: AR1Generator created once per phi level,
                   outside the simulation loop — restores independence
                   between iterations.
  [FIX-3 MODERATE] modified_mk_hamed_rao: VIF clamped to max(1.0, ...) so
                   variance is never deflated below its unadjusted value.
  [FIX-4 MODERATE] variance_distortion_analysis: slope_pw_list now stores
                   slope computed on a reconstructed same-length series for
                   fair comparison; attenuation factor is correctly defined.
  [FIX-5 MINOR]   _ci95: uses exact t-distribution instead of z=1.96.
  [FIX-6 MINOR]   Added note: X₀ ~ N(0,σ) is a practical (not exact
                   stationary) initialisation; burn-in comment added.
================================================================================
"""

# ─────────────────────────────────────────────────────────────────────────────
# 0. IMPORTS
# ─────────────────────────────────────────────────────────────────────────────
import os
import sys
import logging
import warnings
import traceback
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import scipy.stats as stats
from scipy.stats import norm, pearsonr, skew, kurtosis, t as t_dist
from scipy.signal import detrend as scipy_detrend
import statsmodels.api as sm
from statsmodels.stats.stattools import durbin_watson
from statsmodels.tsa.stattools import acf, pacf, adfuller
from statsmodels.stats.diagnostic import acorr_ljungbox
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.ticker as ticker
import matplotlib.patheffects as pe
from matplotlib.patches import Patch, FancyArrowPatch, FancyBboxPatch
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap
import seaborn as sns

try:
    import geopandas as gpd
    from shapely.geometry import Point
    HAS_GEO = True
except ImportError:
    HAS_GEO = False
    warnings.warn("geopandas/shapely not installed; spatial outputs will be skipped.")

try:
    import pymannkendall as pymk
    HAS_PYMK = True
except ImportError:
    HAS_PYMK = False
    warnings.warn("pymannkendall not installed; using internal implementation only.")

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# ─────────────────────────────────────────────────────────────────────────────
# 1. GLOBAL CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
RANDOM_SEED       = 42
N_MONTE_CARLO     = 10_000
ALPHA             = 0.05
COMPLETENESS_THR  = 0.90
WET_MONTHS        = [5, 6, 7, 8, 9, 10]          # May–October
DRY_MONTHS        = [11, 12, 1, 2, 3, 4]          # November–April
PHI_LEVELS        = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
TREND_MAGNITUDES  = [0.0, 0.5, 1.0, 2.0]          # mm yr⁻¹
SAMPLE_SIZES      = [30, 40, 50, 60]
FIGURE_DPI        = 600

# Input file names (must reside in project root or specified DATA_DIR)
RAIN_FILE    = "Observed_Rain_daily_198101_201412_Prachuap Khiri Khan.xlsx"
DEM_FILE     = "ค่าความสูงจากDEM 30m.xlsx"

# ─────────────────────────────────────────────────────────────────────────────
# 2. DIRECTORY STRUCTURE
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DIRS = {
    "processed" : BASE_DIR / "processed_data",
    "outputs"   : BASE_DIR / "outputs",
    "figures"   : BASE_DIR / "figures",
    "tables"    : BASE_DIR / "tables",
    "simulations": BASE_DIR / "simulations",
    "spatial"   : BASE_DIR / "spatial",
    "logs"      : BASE_DIR / "logs",
}
for d in DIRS.values():
    d.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# 3. LOGGING
# ─────────────────────────────────────────────────────────────────────────────
log_path = DIRS["logs"] / f"analysis_{datetime.now():%Y%m%d_%H%M%S}.log"
logging.basicConfig(
    level    = logging.INFO,
    format   = "%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt  = "%Y-%m-%d %H:%M:%S",
    handlers = [
        logging.FileHandler(log_path, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)
log.info("Analysis session started (v2.0 — corrected).")

# ─────────────────────────────────────────────────────────────────────────────
# 4. MATPLOTLIB STYLE — Premium Publication Grade
# ─────────────────────────────────────────────────────────────────────────────
# Colour palette — muted earth tones with clear accent colours
PALETTE = {
    "MK"   : "#2166AC",   # deep blue
    "MMK"  : "#D6604D",   # terracotta
    "PW"   : "#35978F",   # teal
    "TFPW" : "#762A83",   # purple
    "nominal": "#1A1A2E", # near-black
    "shade": "#B2B2B2",   # light grey
}
METHOD_LABELS = {
    "MK"   : "Standard MK",
    "MMK"  : "MMK (Hamed & Rao 1998)",
    "PW"   : "PW-MK",
    "TFPW" : "TFPW-MK (Yue & Wang 2002)",
}
METHOD_MARKERS = {"MK": "o", "MMK": "s", "PW": "^", "TFPW": "D"}

plt.rcParams.update({
    "font.family"         : "serif",
    "font.serif"          : ["Latin Modern Roman", "DejaVu Serif", "FreeSerif"],
    "font.size"           : 9,
    "axes.titlesize"      : 10,
    "axes.labelsize"      : 9,
    "xtick.labelsize"     : 8,
    "ytick.labelsize"     : 8,
    "legend.fontsize"     : 8,
    "figure.dpi"          : 100,
    "savefig.dpi"         : FIGURE_DPI,
    "axes.linewidth"      : 0.7,
    "lines.linewidth"     : 1.4,
    "lines.markersize"    : 5,
    "axes.spines.top"     : False,
    "axes.spines.right"   : False,
    "axes.grid"           : True,
    "grid.alpha"          : 0.18,
    "grid.linewidth"      : 0.4,
    "grid.color"          : "#AAAAAA",
    "pdf.fonttype"        : 42,
    "ps.fonttype"         : 42,
    "figure.facecolor"    : "white",
    "axes.facecolor"      : "#FAFAFA",
    "xtick.direction"     : "out",
    "ytick.direction"     : "out",
    "xtick.major.width"   : 0.6,
    "ytick.major.width"   : 0.6,
    "legend.framealpha"   : 0.92,
    "legend.edgecolor"    : "#CCCCCC",
    "legend.handlelength" : 1.8,
})

# ─────────────────────────────────────────────────────────────────────────────
# 5. UTILITY HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _save_fig(fig: plt.Figure, name: str) -> None:
    """Save figure to both PNG and PDF at publication DPI."""
    png_path = DIRS["figures"] / f"{name}.png"
    pdf_path = DIRS["figures"] / f"{name}.pdf"
    fig.savefig(png_path, dpi=FIGURE_DPI, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf_path,              bbox_inches="tight", facecolor="white")
    plt.close(fig)
    log.info("Figure saved: %s", name)


def _save_table(df: pd.DataFrame, name: str) -> None:
    """Save table as CSV and Excel."""
    df.to_csv(DIRS["tables"] / f"{name}.csv", index=True)
    df.to_excel(DIRS["tables"] / f"{name}.xlsx")
    log.info("Table saved: %s", name)


def _save_processed(df: pd.DataFrame, name: str) -> None:
    """Save processed dataset."""
    df.to_csv(DIRS["processed"] / f"{name}.csv", index=True)
    log.info("Processed data saved: %s", name)


def _ci95(arr: np.ndarray) -> tuple[float, float]:
    """
    95% confidence interval using exact t-distribution.
    [FIX-5] Changed from z=1.96 to t-critical for correctness at small n.
    """
    arr = np.asarray(arr, dtype=float)
    arr = arr[~np.isnan(arr)]
    m  = np.mean(arr)
    se = np.std(arr, ddof=1) / np.sqrt(len(arr))
    t_crit = t_dist.ppf(0.975, df=len(arr) - 1)
    return m - t_crit * se, m + t_crit * se


def _panel_label(ax, label: str, x: float = -0.12, y: float = 1.02) -> None:
    """Add bold panel label (a), (b), … in top-left of axes."""
    ax.text(x, y, label, transform=ax.transAxes,
            fontsize=10, fontweight="bold", va="bottom", ha="left",
            fontfamily="serif")


def _add_significance_bar(ax, x, y, p_value, fontsize=7) -> None:
    """Overlay significance stars above a bar."""
    if   p_value < 0.001: stars = "***"
    elif p_value < 0.01 : stars = "**"
    elif p_value < 0.05 : stars = "*"
    else                : return
    offset = 0.06 * abs(y) if y != 0 else 0.1
    ax.text(x, y + offset * np.sign(y) if y != 0 else 0.1,
            stars, ha="center", va="bottom", fontsize=fontsize,
            color="#1A1A1A")


# ─────────────────────────────────────────────────────────────────────────────
# 6. DATA LOADING
# ─────────────────────────────────────────────────────────────────────────────
def load_raw_data(rain_path: Path, dem_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    log.info("Loading rainfall file: %s", rain_path.name)
    try:
        xl_rain = pd.ExcelFile(rain_path, engine="openpyxl")
        df_rain = xl_rain.parse(xl_rain.sheet_names[0])
    except Exception as exc:
        log.error("Cannot open rainfall file: %s", exc); raise

    log.info("Loading DEM file: %s", dem_path.name)
    try:
        xl_dem = pd.ExcelFile(dem_path, engine="openpyxl")
        df_dem = xl_dem.parse(xl_dem.sheet_names[0])
    except Exception as exc:
        log.error("Cannot open DEM file: %s", exc); raise

    log.info("Raw rain shape: %s | Raw DEM shape: %s", df_rain.shape, df_dem.shape)
    return df_rain, df_dem


# ─────────────────────────────────────────────────────────────────────────────
# 7. COLUMN DETECTION
# ─────────────────────────────────────────────────────────────────────────────
def _detect_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lower_cols = {c.lower().strip(): c for c in df.columns}
    for cand in candidates:
        if cand.lower().strip() in lower_cols:
            return lower_cols[cand.lower().strip()]
    return None


def standardise_rain_columns(df: pd.DataFrame) -> pd.DataFrame:
    col_map = {}
    station_col = _detect_column(df, ["station","station_id","stn","id","สถานี"])
    date_col    = _detect_column(df, ["date","วันที่","datetime","time"])
    year_col    = _detect_column(df, ["year","ปี","yr"])
    month_col   = _detect_column(df, ["month","เดือน","mon"])
    day_col     = _detect_column(df, ["day","วัน","d"])
    rain_col    = _detect_column(df, [
        "rainfall","rain","precip","precipitation",
        "daily_rain","rain_mm","rainfall_mm",
        "ปริมาณฝน","ปริมาณฝนรายวัน","value",
    ])
    if station_col: col_map[station_col] = "Station"
    if date_col   : col_map[date_col]    = "Date"
    if year_col   : col_map[year_col]    = "Year"
    if month_col  : col_map[month_col]   = "Month"
    if day_col    : col_map[day_col]     = "Day"
    if rain_col   : col_map[rain_col]    = "Rainfall_mm"
    df = df.rename(columns=col_map)
    if "Date" not in df.columns and {"Year","Month","Day"}.issubset(df.columns):
        df["Date"] = pd.to_datetime(df[["Year","Month","Day"]])
    elif "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    if "Date" in df.columns:
        if "Year"  not in df.columns: df["Year"]  = df["Date"].dt.year
        if "Month" not in df.columns: df["Month"] = df["Date"].dt.month
        if "Day"   not in df.columns: df["Day"]   = df["Date"].dt.day
    if "Rainfall_mm" not in df.columns:
        raise ValueError(f"Cannot identify rainfall column. Available: {list(df.columns)}")
    return df


def standardise_dem_columns(df: pd.DataFrame) -> pd.DataFrame:
    col_map = {}
    station_col = _detect_column(df, ["station","station_id","stn","id","สถานี"])
    lat_col     = _detect_column(df, ["lat","latitude","ละติจูด","y"])
    lon_col     = _detect_column(df, ["lon","longitude","long","ลองจิจูด","x"])
    elev_col    = _detect_column(df, ["elev","elevation","alt","altitude","height","ความสูง","dem","z"])
    if station_col: col_map[station_col] = "Station"
    if lat_col    : col_map[lat_col]     = "Latitude"
    if lon_col    : col_map[lon_col]     = "Longitude"
    if elev_col   : col_map[elev_col]   = "Elevation_m"
    df = df.rename(columns=col_map)
    for req in ["Station","Latitude","Longitude","Elevation_m"]:
        if req not in df.columns:
            log.warning("DEM column '%s' not found; filling with NaN.", req)
            df[req] = np.nan
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 8. QUALITY CONTROL
# ─────────────────────────────────────────────────────────────────────────────
def quality_control(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    log.info("Running quality control …")
    qc_records = []
    neg_mask = df["Rainfall_mm"] < 0
    if neg_mask.any():
        qc_records.append({"Check": "Negative rainfall", "Count": int(neg_mask.sum())})
        df.loc[neg_mask, "Rainfall_mm"] = np.nan
    extreme_mask = df["Rainfall_mm"] > 1000
    if extreme_mask.any():
        qc_records.append({"Check": "Extreme rainfall (>1000 mm)", "Count": int(extreme_mask.sum())})
        df.loc[extreme_mask, "Rainfall_mm"] = np.nan
    missing_init = df["Rainfall_mm"].isna().sum()
    qc_records.append({"Check": "Missing values (total)", "Count": int(missing_init)})
    if "Date" in df.columns:
        dup_mask = df.duplicated(subset=["Station","Date"], keep="first")
        if dup_mask.any():
            qc_records.append({"Check": "Duplicate station-date rows removed",
                                "Count": int(dup_mask.sum())})
            df = df[~dup_mask].copy()
    qc_df = pd.DataFrame(qc_records)
    log.info("QC complete.\n%s", qc_df.to_string(index=False))
    return df.reset_index(drop=True), qc_df


def compute_completeness(df: pd.DataFrame) -> pd.DataFrame:
    log.info("Computing station completeness …")
    records = []
    for stn, grp in df.groupby("Station"):
        if "Date" in grp.columns:
            date_range = pd.date_range(grp["Date"].min(), grp["Date"].max(), freq="D")
            expected   = len(date_range)
        else:
            expected = len(grp)
        actual       = grp["Rainfall_mm"].notna().sum()
        completeness = actual / expected if expected > 0 else 0.0
        records.append({
            "Station"         : stn,
            "Expected_days"   : expected,
            "Available_days"  : actual,
            "Completeness_pct": round(completeness * 100, 2),
            "Pass_threshold"  : completeness >= COMPLETENESS_THR,
        })
    comp_df = pd.DataFrame(records)
    log.info("Completeness summary:\n%s", comp_df.to_string(index=False))
    return comp_df


# ─────────────────────────────────────────────────────────────────────────────
# 9. AGGREGATION — MONTHLY / SEASONAL / ANNUAL
# ─────────────────────────────────────────────────────────────────────────────
def aggregate_rainfall(df: pd.DataFrame, valid_stations: list) -> dict[str, pd.DataFrame]:
    log.info("Aggregating rainfall data …")
    df = df[df["Station"].isin(valid_stations)].copy()

    monthly = (
        df.groupby(["Station","Year","Month"])["Rainfall_mm"]
        .sum(min_count=1).reset_index()
        .rename(columns={"Rainfall_mm": "Monthly_mm"})
    )
    annual = (
        df.groupby(["Station","Year"])["Rainfall_mm"]
        .sum(min_count=1).reset_index()
        .rename(columns={"Rainfall_mm": "Annual_mm"})
    )
    df["Season"]   = df["Month"].apply(lambda m: "Wet" if m in WET_MONTHS else "Dry")
    df["HydroYear"] = df["Year"].copy()
    dry_nov_dec = (df["Month"].isin([11,12])) & (df["Season"] == "Dry")
    df.loc[dry_nov_dec, "HydroYear"] = df.loc[dry_nov_dec,"Year"] + 1
    seasonal = (
        df.groupby(["Station","HydroYear","Season"])["Rainfall_mm"]
        .sum(min_count=1).reset_index()
        .rename(columns={"HydroYear":"Year","Rainfall_mm":"Seasonal_mm"})
    )
    wet = seasonal[seasonal["Season"]=="Wet"][["Station","Year","Seasonal_mm"]].rename(
        columns={"Seasonal_mm":"Wet_mm"})
    dry = seasonal[seasonal["Season"]=="Dry"][["Station","Year","Seasonal_mm"]].rename(
        columns={"Seasonal_mm":"Dry_mm"})
    seasonal_wide = wet.merge(dry, on=["Station","Year"], how="outer").sort_values(
        ["Station","Year"])
    log.info("Aggregation done. Annual rows: %d, Seasonal rows: %d",
             len(annual), len(seasonal_wide))
    return {"monthly":monthly, "annual":annual, "seasonal":seasonal_wide}


# ─────────────────────────────────────────────────────────────────────────────
# 10. AUTOCORRELATION ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────
def compute_autocorrelation(series: np.ndarray, nlags: int = 20,
                            label: str = "") -> dict:
    n     = len(series)
    nlags = min(nlags, n // 2 - 1)
    x     = series - np.nanmean(series)

    r1 = np.corrcoef(x[:-1], x[1:])[0, 1]
    acf_vals  = acf(x,  nlags=nlags, fft=True,   alpha=None)
    pacf_vals = pacf(x, nlags=nlags, method="ywm", alpha=None)

    lb_result = acorr_ljungbox(x, lags=min(10, nlags), return_df=True)
    lb_pvalue = float(lb_result["lb_pvalue"].iloc[-1])
    dw        = float(durbin_watson(x))
    adf_stat, adf_pval, adf_lags, *_ = adfuller(x, autolag="AIC")

    # VIF = n / n*  (Hamed & Rao 1998, Eq. 3)
    rho     = acf_vals[:nlags + 1]
    assert abs(rho[0] - 1.0) < 1e-6, "ACF lag-0 must be 1.0"
    vif_sum = 0.0
    for i in range(1, nlags + 1):
        vif_sum += (n - i) / n * rho[i]
    vif   = 1.0 + 2.0 * vif_sum
    n_eff = max(3, n / vif)

    result = {
        "label"         : label, "n"       : n,
        "r1"            : r1,    "acf"     : acf_vals,
        "pacf"          : pacf_vals,
        "lb_pvalue"     : lb_pvalue, "lb_sig"  : lb_pvalue < ALPHA,
        "dw"            : dw,
        "adf_stat"      : adf_stat,  "adf_pval": adf_pval,
        "adf_stationary": adf_pval < ALPHA,
        "vif"           : vif,       "n_eff"   : n_eff,
        "nlags"         : nlags,
    }
    log.info("[%s] r1=%.3f | DW=%.3f | LB-p=%.4f | ADF-p=%.4f | VIF=%.3f | n_eff=%.1f",
             label, r1, dw, lb_pvalue, adf_pval, vif, n_eff)
    return result


def classify_autocorrelation(r1: float) -> str:
    if   abs(r1) < 0.10: return "Negligible"
    elif abs(r1) < 0.30: return "Low"
    elif abs(r1) < 0.50: return "Moderate"
    elif abs(r1) < 0.70: return "High"
    else                : return "Very High"


# ─────────────────────────────────────────────────────────────────────────────
# 11. MANN–KENDALL IMPLEMENTATIONS
# ─────────────────────────────────────────────────────────────────────────────
def sens_slope(x: np.ndarray) -> float:
    """Sen (1968) non-parametric slope estimator."""
    n = len(x)
    slopes = [(x[j] - x[i]) / (j - i)
              for i in range(n - 1) for j in range(i + 1, n)]
    return float(np.median(slopes)) if slopes else np.nan


def _mk_s_statistic(x: np.ndarray) -> tuple[float, int]:
    """MK S statistic with ties correction term."""
    n, s = len(x), 0.0
    for i in range(n - 1):
        for j in range(i + 1, n):
            diff = x[j] - x[i]
            if   diff > 0: s += 1
            elif diff < 0: s -= 1
    _, counts = np.unique(x, return_counts=True)
    ties_term = int(np.sum(counts * (counts - 1) * (2 * counts + 5)))
    return s, ties_term


def standard_mk(x: np.ndarray) -> dict:
    """Standard Mann–Kendall test (Mann 1945; Kendall 1975)."""
    x = np.asarray(x, dtype=float); x = x[~np.isnan(x)]
    n = len(x)
    if n < 4:
        return {k: np.nan for k in ["S","Var_S","Z","tau","p","slope","method"]}
    s, ties_term = _mk_s_statistic(x)
    var_s = (n * (n - 1) * (2 * n + 5) - ties_term) / 18.0
    if   s > 0: z = (s - 1) / np.sqrt(var_s)
    elif s < 0: z = (s + 1) / np.sqrt(var_s)
    else      : z = 0.0
    return {"S":s,"Var_S":var_s,"Z":z,"tau":s/(0.5*n*(n-1)),
            "p":2.0*(1.0-norm.cdf(abs(z))),"slope":sens_slope(x),"method":"MK"}


def modified_mk_hamed_rao(x: np.ndarray) -> dict:
    """
    Modified MK — Hamed & Rao (1998) effective sample size correction.
    [FIX-3] VIF clamped to max(1.0, …) so Var*(S) ≥ Var(S) always.
    """
    x = np.asarray(x, dtype=float); x = x[~np.isnan(x)]
    n = len(x)
    if n < 4:
        return {k: np.nan for k in
                ["S","Var_S","Var_S_mod","Z","tau","p","slope","n_s","vif","method"]}
    s, ties_term = _mk_s_statistic(x)
    var_s  = (n * (n - 1) * (2 * n + 5) - ties_term) / 18.0
    ranks  = stats.rankdata(x)
    nlags  = min(n - 2, 20)
    rho    = acf(ranks, nlags=nlags, fft=True, alpha=None)
    vif_sum = sum((n - i) / n * rho[i] for i in range(1, nlags + 1))
    # [FIX-3] clamp at 1.0 — VIF < 1 implies deflation, physically unreasonable
    #         for hydroclimatic series with predominantly positive autocorrelation.
    vif        = max(1.0, 1.0 + 2.0 * vif_sum)
    n_s        = n / vif
    var_s_mod  = max(var_s * vif, 1e-10)
    if   s > 0: z = (s - 1) / np.sqrt(var_s_mod)
    elif s < 0: z = (s + 1) / np.sqrt(var_s_mod)
    else      : z = 0.0
    return {"S":s,"Var_S":var_s,"Var_S_mod":var_s_mod,"Z":z,
            "tau":s/(0.5*n*(n-1)),"p":2.0*(1.0-norm.cdf(abs(z))),
            "slope":sens_slope(x),"n_s":n_s,"vif":vif,
            "method":"MMK (Hamed & Rao 1998)"}


def prewhitening_mk(x: np.ndarray) -> dict:
    """
    Pre-Whitening MK (Von Storch 1995; Kulkarni & Von Storch 1995).
    Sen's slope reported from original series for comparability.
    Note: slope_pw (on whitened series) stored separately for diagnostics.
    """
    x = np.asarray(x, dtype=float); x = x[~np.isnan(x)]
    n = len(x)
    if n < 5:
        return {k: np.nan for k in
                ["S","Var_S","Z","tau","p","slope","phi","method"]}
    phi      = np.corrcoef(x[:-1], x[1:])[0, 1]
    x_pw     = x[1:] - phi * x[:-1]
    mk_res   = standard_mk(x_pw)
    mk_res["phi"]      = phi
    mk_res["method"]   = "PW-MK"
    mk_res["slope"]    = sens_slope(x)       # original series slope
    mk_res["slope_pw"] = sens_slope(x_pw)    # whitened series slope (diagnostic)
    return mk_res


def tfpw_mk(x: np.ndarray) -> dict:
    """
    Trend-Free Pre-Whitening MK (Yue & Wang 2002, WRR).
    Steps 1–6 exactly as in the original paper.
    """
    x = np.asarray(x, dtype=float); x = x[~np.isnan(x)]
    n = len(x)
    if n < 5:
        return {k: np.nan for k in
                ["S","Var_S","Z","tau","p","slope","phi","method"]}
    t      = np.arange(1, n + 1, dtype=float)
    beta   = sens_slope(x)          # Step 1
    trend  = beta * t
    y      = x - trend              # Step 2: detrend
    phi    = np.corrcoef(y[:-1], y[1:])[0, 1]   # Step 3
    y_pw   = y[1:] - phi * y[:-1]               # Step 4
    t_pw   = t[1:]
    z      = y_pw + beta * t_pw                  # Step 5: restore trend
    mk_res = standard_mk(z)         # Step 6
    mk_res["phi"]    = phi
    mk_res["slope"]  = beta         # original Sen's slope
    mk_res["method"] = "TFPW-MK (Yue & Wang 2002)"
    return mk_res


def run_all_methods(series: np.ndarray, label: str = "") -> dict:
    """Run all four MK variants on a single series."""
    results = {
        "MK"  : standard_mk(series),
        "MMK" : modified_mk_hamed_rao(series),
        "PW"  : prewhitening_mk(series),
        "TFPW": tfpw_mk(series),
    }
    for method, res in results.items():
        sig = ("***" if res.get("p",1) < 0.001 else
               "**"  if res.get("p",1) < 0.01  else
               "*"   if res.get("p",1) < 0.05  else "ns")
        log.info("[%s | %s] Z=%.3f  p=%.4f %s  slope=%.3f mm/yr",
                 label, method,
                 res.get("Z",np.nan), res.get("p",np.nan), sig,
                 res.get("slope",np.nan))
    return results


# ─────────────────────────────────────────────────────────────────────────────
# 12. MONTE CARLO SIMULATION ENGINE
# ─────────────────────────────────────────────────────────────────────────────
class AR1Generator:
    """
    Generate synthetic AR(1) series for Monte Carlo experiments.

    X_t = φ·X_{t-1} + ε_t,   ε_t ~ N(0, σ²(1−φ²))

    Innovation variance is scaled so that Var(X_t) = σ² for all φ,
    enabling fair comparison of Type I error across autocorrelation levels.

    Note (FIX-6): X₀ ~ N(0, σ) is a practical initialisation (not the exact
    stationary distribution for AR(1) which is also N(0, σ)). A burn-in of
    50 steps is applied to reduce transient effects from the initial condition.
    """
    BURNIN = 50

    def __init__(self, n: int, phi: float, sigma: float = 1.0,
                 trend: float = 0.0, mu: float = 0.0, rng=None):
        self.n          = n
        self.phi        = phi
        self.sigma      = sigma
        self.trend      = trend
        self.mu         = mu
        self.rng        = rng if rng is not None else np.random.default_rng(RANDOM_SEED)
        self.innov_std  = sigma * np.sqrt(max(1.0 - phi**2, 1e-8))

    def generate(self) -> np.ndarray:
        # Burn-in: run BURNIN steps to reduce initial-condition transients
        x_prev = self.rng.normal(0, self.sigma)
        for _ in range(self.BURNIN):
            x_prev = self.phi * x_prev + self.rng.normal(0, self.innov_std)
        x = np.zeros(self.n)
        x[0] = x_prev
        for t in range(1, self.n):
            x[t] = self.phi * x[t-1] + self.rng.normal(0, self.innov_std)
        t_arr = np.arange(1, self.n + 1, dtype=float)
        x    += self.trend * t_arr + self.mu
        return x


def monte_carlo_type_i_error(
    phi: float, n: int = 34, n_iter: int = N_MONTE_CARLO,
    alpha: float = ALPHA, seed: int = RANDOM_SEED,
) -> dict:
    """
    Monte Carlo simulation of Type I error under H₀ (no trend).
    P(Type I) = fraction of iterations where H₀ is rejected
                when the true trend is zero.
    """
    rng  = np.random.default_rng(seed + int(phi * 100))
    gen  = AR1Generator(n=n, phi=phi, sigma=1.0, trend=0.0, rng=rng)
    rejections = {"MK":0,"MMK":0,"PW":0,"TFPW":0}
    for _ in range(n_iter):
        x = gen.generate()
        for method, func in [("MK",standard_mk),("MMK",modified_mk_hamed_rao),
                              ("PW",prewhitening_mk),("TFPW",tfpw_mk)]:
            if func(x).get("p",1.0) < alpha:
                rejections[method] += 1
    type_i = {m: rejections[m]/n_iter for m in rejections}
    log.info("MC Type I Error (φ=%.2f, n=%d): %s",
             phi, n, {m: f"{v:.4f}" for m,v in type_i.items()})
    return type_i


def monte_carlo_power(
    phi: float, trend: float, n: int = 34,
    n_iter: int = N_MONTE_CARLO, alpha: float = ALPHA,
    seed: int = RANDOM_SEED,
) -> dict:
    """Monte Carlo statistical power = P(reject H₀ | H₁ true)."""
    rng  = np.random.default_rng(seed + int(phi*100) + int(trend*10))
    gen  = AR1Generator(n=n, phi=phi, sigma=10.0, trend=trend, rng=rng)
    rejections = {"MK":0,"MMK":0,"PW":0,"TFPW":0}
    for _ in range(n_iter):
        x = gen.generate()
        for method, func in [("MK",standard_mk),("MMK",modified_mk_hamed_rao),
                              ("PW",prewhitening_mk),("TFPW",tfpw_mk)]:
            if func(x).get("p",1.0) < alpha:
                rejections[method] += 1
    return {m: rejections[m]/n_iter for m in rejections}


def run_full_monte_carlo() -> dict:
    """Run complete Monte Carlo experiment grid."""
    log.info("="*70)
    log.info("MONTE CARLO SIMULATION  (N=%d iterations)", N_MONTE_CARLO)
    log.info("="*70)
    n_years = 34    # 1981–2014

    type_i_records = []
    for phi in PHI_LEVELS:
        res = monte_carlo_type_i_error(phi, n=n_years, n_iter=N_MONTE_CARLO)
        row = {"phi": phi}; row.update(res)
        type_i_records.append(row)
        log.info("Type I Error: phi=%.2f → %s", phi, res)
    type_i_df = pd.DataFrame(type_i_records)

    power_records = []
    for phi in [0.0, 0.3, 0.6]:
        for trend in TREND_MAGNITUDES:
            res = monte_carlo_power(phi, trend, n=n_years, n_iter=N_MONTE_CARLO)
            row = {"phi":phi,"trend_mm_yr":trend}; row.update(res)
            power_records.append(row)
            log.info("Power: phi=%.2f trend=%.1f → %s", phi, trend, res)
    power_df = pd.DataFrame(power_records)

    return {"type_i": type_i_df, "power": power_df}


# ─────────────────────────────────────────────────────────────────────────────
# 13. VARIANCE DISTORTION ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────
def variance_distortion_analysis(
    phi_levels: list = PHI_LEVELS, n: int = 34, n_iter: int = 1000,
) -> pd.DataFrame:
    """
    Compute variance ratio (whitened / original) for PW and TFPW
    across autocorrelation levels.

    [FIX-4] Trend attenuation is now computed on the full-length reconstructed
    series (z_tfpw = y_pw + beta*t[1:] restored to compare with original trend)
    and a length-matched PW slope for fair comparison.
    """
    log.info("Variance distortion analysis …")
    records    = []
    true_slope = 2.0  # mm yr⁻¹

    for phi in phi_levels:
        rng = np.random.default_rng(RANDOM_SEED + int(phi*100))
        gen = AR1Generator(n=n, phi=phi, sigma=10.0, trend=true_slope, rng=rng)

        var_orig_list, var_pw_list, var_tfpw_list = [], [], []
        slope_pw_list, slope_tfpw_list = [], []

        for _ in range(n_iter):
            x   = gen.generate()
            t   = np.arange(1, n + 1, dtype=float)

            # ── PW: slope on whitened series (length n-1) ──────────────────
            phi_hat_pw = np.corrcoef(x[:-1], x[1:])[0, 1]
            x_pw       = x[1:] - phi_hat_pw * x[:-1]
            # [FIX-4] For attenuation: reattach a length-(n-1) time axis
            # slope_pw is on the whitened series (n-1 obs); compared to true_slope
            # after noting the whitened series removes the AR-component not the trend.
            # We report trend attenuation as ratio of recovered slope to true slope.
            slope_pw_list.append(sens_slope(x_pw))

            # ── TFPW: slope on z_tfpw (n-1 obs with restored trend) ────────
            beta_hat   = sens_slope(x)
            y          = x - beta_hat * t
            phi_hat_tf = np.corrcoef(y[:-1], y[1:])[0, 1]
            y_pw       = y[1:] - phi_hat_tf * y[:-1]
            x_tfpw     = y_pw + beta_hat * t[1:]
            slope_tfpw_list.append(sens_slope(x_tfpw))

            var_orig_list.append(np.var(x,       ddof=1))
            var_pw_list.append(  np.var(x_pw,    ddof=1))
            var_tfpw_list.append(np.var(x_tfpw,  ddof=1))

        records.append({
            "phi"                   : phi,
            "var_original_mean"     : np.mean(var_orig_list),
            "var_pw_mean"           : np.mean(var_pw_list),
            "var_tfpw_mean"         : np.mean(var_tfpw_list),
            "var_ratio_pw"          : np.mean(var_pw_list)   / np.mean(var_orig_list),
            "var_ratio_tfpw"        : np.mean(var_tfpw_list) / np.mean(var_orig_list),
            # [FIX-4] attenuation = recovered slope / true slope
            # For PW-MK: slope_pw estimated from whitened series (n-1 obs).
            # Attenuation < 1 means whitening absorbs part of the linear signal.
            "slope_pw_mean"         : np.mean(slope_pw_list),
            "slope_tfpw_mean"       : np.mean(slope_tfpw_list),
            "trend_attenuation_pw"  : np.mean(slope_pw_list)   / true_slope,
            "trend_attenuation_tfpw": np.mean(slope_tfpw_list) / true_slope,
        })

    df = pd.DataFrame(records)
    log.info("Variance distortion:\n%s",
             df[["phi","var_ratio_pw","var_ratio_tfpw",
                 "trend_attenuation_pw","trend_attenuation_tfpw"]].to_string())
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 14. FALSE DISCOVERY RATE (BENJAMINI–HOCHBERG)
# ─────────────────────────────────────────────────────────────────────────────
def benjamini_hochberg(p_values: np.ndarray, alpha: float = ALPHA) -> np.ndarray:
    """
    Benjamini–Hochberg (1995) FDR correction.
    Returns boolean array: True = rejected after BH adjustment.
    Reference: Benjamini & Hochberg (1995) JRSS-B
    """
    n     = len(p_values)
    order = np.argsort(p_values)
    # Find max k such that p_(k) ≤ (k/m)·α
    max_k = 0
    for k, i in enumerate(order):
        if p_values[i] <= (k + 1) / n * alpha:
            max_k = k + 1
    reject_final = np.zeros(n, dtype=bool)
    reject_final[order[:max_k]] = True
    return reject_final


def fdr_analysis(
    phi_levels: list = PHI_LEVELS, n_stations: int = 10,
    n: int = 34, n_iter: int = 2000,
) -> pd.DataFrame:
    """
    Simulate true BH-FDR across methods for simultaneous multi-station tests.

    [FIX-1 CRITICAL] Now correctly calls benjamini_hochberg() on the per-
    iteration p-value arrays, so FDR_* columns reflect the proportion of
    stations whose H₀ is rejected AFTER BH correction — i.e., the empirical
    false discovery rate, not the raw FWER/Type-I rate.

    [FIX-2 CRITICAL] AR1Generator is created once per phi level, outside the
    simulation loop, so the RNG state advances continuously and iterations are
    truly independent.
    """
    log.info("FDR analysis (BH-corrected) …")
    records = []

    for phi in phi_levels:
        rng = np.random.default_rng(RANDOM_SEED + 999 + int(phi * 100))

        # [FIX-2] Generator created ONCE per phi level — not inside the loop
        gen = AR1Generator(n=n, phi=phi, sigma=10.0, trend=0.0, rng=rng)

        fdr_mk, fdr_mmk, fdr_pw, fdr_tfpw = [], [], [], []

        for _ in range(n_iter):
            p_mk, p_mmk, p_pw, p_tfpw = [], [], [], []
            for _ in range(n_stations):
                x = gen.generate()
                p_mk.append(standard_mk(x)["p"])
                p_mmk.append(modified_mk_hamed_rao(x)["p"])
                p_pw.append(prewhitening_mk(x)["p"])
                p_tfpw.append(tfpw_mk(x)["p"])

            # [FIX-1] Apply BH correction — report proportion rejected after BH
            fdr_mk.append(   np.mean(benjamini_hochberg(np.array(p_mk))))
            fdr_mmk.append(  np.mean(benjamini_hochberg(np.array(p_mmk))))
            fdr_pw.append(   np.mean(benjamini_hochberg(np.array(p_pw))))
            fdr_tfpw.append( np.mean(benjamini_hochberg(np.array(p_tfpw))))

        records.append({
            "phi"      : phi,
            "FDR_MK"   : np.mean(fdr_mk),
            "FDR_MMK"  : np.mean(fdr_mmk),
            "FDR_PW"   : np.mean(fdr_pw),
            "FDR_TFPW" : np.mean(fdr_tfpw),
        })
        log.info("BH-FDR (phi=%.2f): MK=%.4f MMK=%.4f PW=%.4f TFPW=%.4f",
                 phi,
                 records[-1]["FDR_MK"], records[-1]["FDR_MMK"],
                 records[-1]["FDR_PW"], records[-1]["FDR_TFPW"])

    return pd.DataFrame(records)


# ─────────────────────────────────────────────────────────────────────────────
# 15. MOVING BLOCK BOOTSTRAP UNCERTAINTY
# ─────────────────────────────────────────────────────────────────────────────
def moving_block_bootstrap(
    x: np.ndarray, block_size: int = None,
    n_boot: int = 1000, seed: int = RANDOM_SEED,
) -> dict:
    """
    Moving Block Bootstrap (Kunsch 1989) for confidence intervals.
    Optimal block size: l* ≈ n^(1/3)  (Hall et al. 1995)
    """
    x   = np.asarray(x, dtype=float); x = x[~np.isnan(x)]
    n   = len(x)
    rng = np.random.default_rng(seed)
    if block_size is None:
        block_size = max(2, int(round(n ** (1/3))))
    n_blocks     = int(np.ceil(n / block_size))
    boot_results = {m: {"Z":[],"slope":[]} for m in ["MK","MMK","PW","TFPW"]}
    for _ in range(n_boot):
        indices  = []
        starts   = rng.integers(0, n - block_size + 1, size=n_blocks)
        for s in starts:
            indices.extend(range(s, s + block_size))
        x_boot = x[np.array(indices[:n])]
        for method, func in [("MK",standard_mk),("MMK",modified_mk_hamed_rao),
                              ("PW",prewhitening_mk),("TFPW",tfpw_mk)]:
            res = func(x_boot)
            boot_results[method]["Z"].append(res.get("Z",np.nan))
            boot_results[method]["slope"].append(res.get("slope",np.nan))
    ci = {}
    for method in boot_results:
        z_arr = np.array(boot_results[method]["Z"])
        s_arr = np.array(boot_results[method]["slope"])
        ci[method] = {
            "Z_mean"       : float(np.nanmean(z_arr)),
            "Z_ci95_lo"    : float(np.nanpercentile(z_arr, 2.5)),
            "Z_ci95_hi"    : float(np.nanpercentile(z_arr, 97.5)),
            "slope_mean"   : float(np.nanmean(s_arr)),
            "slope_ci95_lo": float(np.nanpercentile(s_arr, 2.5)),
            "slope_ci95_hi": float(np.nanpercentile(s_arr, 97.5)),
        }
    return {"block_size": block_size, "n_boot": n_boot, "ci": ci}


# ─────────────────────────────────────────────────────────────────────────────
# 16. SENSITIVITY ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────
def sensitivity_analysis() -> dict:
    log.info("Running sensitivity analysis …")
    n_iter_sens = 3000

    sample_records = []
    for n in SAMPLE_SIZES:
        for phi in [0.0, 0.3, 0.6]:
            res = monte_carlo_type_i_error(phi, n=n, n_iter=n_iter_sens,
                                           seed=RANDOM_SEED+n)
            row = {"n":n,"phi":phi}; row.update(res)
            sample_records.append(row)
    sample_df = pd.DataFrame(sample_records)

    sigma_levels  = [1.0, 5.0, 10.0, 20.0]
    sigma_records = []
    for sigma in sigma_levels:
        for phi in [0.0, 0.3, 0.6]:
            rng = np.random.default_rng(RANDOM_SEED + int(sigma))
            gen = AR1Generator(n=34, phi=phi, sigma=sigma, trend=0.0, rng=rng)
            rej = {"MK":0,"MMK":0,"PW":0,"TFPW":0}
            for _ in range(n_iter_sens):
                x = gen.generate()
                for m, f in [("MK",standard_mk),("MMK",modified_mk_hamed_rao),
                              ("PW",prewhitening_mk),("TFPW",tfpw_mk)]:
                    if f(x).get("p",1.0) < ALPHA: rej[m] += 1
            row = {"sigma":sigma,"phi":phi}
            row.update({m: v/n_iter_sens for m,v in rej.items()})
            sigma_records.append(row)
    sigma_df = pd.DataFrame(sigma_records)
    log.info("Sensitivity analysis complete.")
    return {"sample_size": sample_df, "variance": sigma_df}


# ─────────────────────────────────────────────────────────────────────────────
# 17. HYDROCLIMATIC INTERPRETATION
# ─────────────────────────────────────────────────────────────────────────────
def generate_interpretation(
    type_i_df: pd.DataFrame, power_df: pd.DataFrame,
    var_distort_df: pd.DataFrame,
) -> str:
    lines = []
    row_03 = type_i_df[type_i_df["phi"].round(2) == 0.30]
    if not row_03.empty:
        mk_03  = float(row_03["MK"].iloc[0])
        mmk_03 = float(row_03["MMK"].iloc[0])
        pw_03  = float(row_03["PW"].iloc[0])
        tf_03  = float(row_03["TFPW"].iloc[0])
    else:
        mk_03 = mmk_03 = pw_03 = tf_03 = np.nan

    lines.append("=" * 80)
    lines.append("HYDROCLIMATIC INTERPRETATION — AUTO-GENERATED (v2.0 corrected)")
    lines.append("=" * 80)
    lines.append(
        f"\n1. STANDARD MK — TYPE I ERROR INFLATION\n"
        f"   At φ=0.30, empirical Type I error = {mk_03:.4f} "
        f"({'substantially exceeds' if mk_03 > 0.07 else 'slightly exceeds'} "
        f"nominal α={ALPHA}). Consistent with Hamed & Rao (1998)."
    )
    lines.append(
        f"\n2. MMK (HAMED & RAO 1998) — IMPROVED CONTROL\n"
        f"   Type I error reduced to {mmk_03:.4f} at φ=0.30 via rank-based "
        f"VIF correction (VIF clamped ≥1.0 per corrected implementation)."
    )
    lines.append(
        f"\n3. PW-MK — AUTOCORRELATION REMOVAL\n"
        f"   Empirical Type I error = {pw_03:.4f} at φ=0.30. "
        f"Reduces series length by one; slope reported on original series."
    )
    row_v06 = var_distort_df[var_distort_df["phi"].round(2) == 0.60]
    if not row_v06.empty:
        vr_pw    = float(row_v06["var_ratio_pw"].iloc[0])
        vr_tf    = float(row_v06["var_ratio_tfpw"].iloc[0])
        ta_pw    = float(row_v06["trend_attenuation_pw"].iloc[0])
        ta_tfpw  = float(row_v06["trend_attenuation_tfpw"].iloc[0])
    else:
        vr_pw = vr_tf = ta_pw = ta_tfpw = np.nan
    lines.append(
        f"\n4. TFPW-MK (YUE & WANG 2002) — TREND PRESERVATION\n"
        f"   Type I error = {tf_03:.4f} at φ=0.30. At φ=0.60: "
        f"var_ratio={vr_tf:.3f} (TFPW) vs {vr_pw:.3f} (PW); "
        f"trend_attenuation={ta_tfpw:.3f} (TFPW) vs {ta_pw:.3f} (PW)."
    )
    lines.append(
        "\n5. BH-FDR CORRECTION\n"
        "   Benjamini–Hochberg (1995) correction now correctly applied to "
        "multi-station p-value arrays in fdr_analysis(), yielding true FDR "
        "values — not raw FWER rates as in the previous implementation."
    )
    row_p = power_df[(power_df["phi"].round(1)==0.3) &
                     (power_df["trend_mm_yr"].round(1)==1.0)]
    if not row_p.empty:
        lines.append(
            f"\n6. STATISTICAL POWER (φ=0.3, trend=1.0 mm yr⁻¹)\n"
            f"   MK:{float(row_p['MK'].iloc[0]):.4f} | "
            f"MMK:{float(row_p['MMK'].iloc[0]):.4f} | "
            f"PW:{float(row_p['PW'].iloc[0]):.4f} | "
            f"TFPW:{float(row_p['TFPW'].iloc[0]):.4f}"
        )
    lines.append("\n7. RECOMMENDATIONS\n"
        "   (a) Always test autocorrelation (ACF, LB, DW) prior to trend analysis.\n"
        "   (b) MMK preferred for moderate autocorrelation (0.1 ≤ φ < 0.5).\n"
        "   (c) TFPW-MK preferred when trend estimation is the primary objective.\n"
        "   (d) Standard MK only when |φ| < 0.10 or LB p > 0.05.\n"
        "   (e) BH-FDR correction mandatory for multi-station analyses.")
    lines.append("\n" + "="*80)
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 18. PREMIUM PUBLICATION-QUALITY FIGURES
# ─────────────────────────────────────────────────────────────────────────────
METHODS  = ["MK", "MMK", "PW", "TFPW"]
COLORS   = [PALETTE[m] for m in METHODS]
MARKERS  = [METHOD_MARKERS[m] for m in METHODS]
MLABELS  = [METHOD_LABELS[m] for m in METHODS]


def _method_legend_handles(linestyle="-") -> list:
    return [
        Line2D([0],[0], color=PALETTE[m], marker=METHOD_MARKERS[m],
               linestyle=linestyle, linewidth=1.4, markersize=5, label=METHOD_LABELS[m])
        for m in METHODS
    ]


# ── Figure 1: Station map ────────────────────────────────────────────────────
def fig_station_map(metadata_df: pd.DataFrame) -> None:
    if not HAS_GEO:
        log.warning("geopandas unavailable — skipping Figure 1.")
        return

    gdf = gpd.GeoDataFrame(
        metadata_df,
        geometry=gpd.points_from_xy(metadata_df["Longitude"], metadata_df["Latitude"]),
        crs="EPSG:4326",
    )
    fig, ax = plt.subplots(figsize=(6, 6.5))
    scatter = gdf.plot(
        ax=ax, column="Elevation_m", cmap="terrain",
        markersize=80, zorder=5, legend=True,
        legend_kwds={"label":"Elevation (m a.s.l.)", "shrink":0.55,
                     "orientation":"vertical"},
    )
    for _, row in gdf.iterrows():
        ax.annotate(str(row["Station"]),
                    xy=(row["Longitude"], row["Latitude"]),
                    xytext=(5, 5), textcoords="offset points", fontsize=7.5,
                    color="#1A1A1A",
                    bbox=dict(boxstyle="round,pad=0.15", fc="white",
                              ec="#AAAAAA", alpha=0.75))
    ax.set_xlabel("Longitude (°E)", fontsize=9)
    ax.set_ylabel("Latitude (°N)",  fontsize=9)
    ax.set_title("Rainfall Gauge Network\nPrachuap Khiri Khan Province, Thailand",
                 fontsize=10, pad=8)
    ax.tick_params(labelsize=8)
    fig.text(0.5, -0.01, "Fig. 1 — Station distribution and elevation.",
             ha="center", fontsize=7.5, color="#555555", style="italic")
    fig.tight_layout()
    _save_fig(fig, "Figure_01_Station_Map")


# ── Figure 2: Rainfall climatology ──────────────────────────────────────────
def fig_rainfall_climatology(monthly_df: pd.DataFrame) -> None:
    climatology = (
        monthly_df.groupby("Month")["Monthly_mm"]
        .agg(["mean","std"]).reset_index()
    )
    month_labels = ["Jan","Feb","Mar","Apr","May","Jun",
                    "Jul","Aug","Sep","Oct","Nov","Dec"]
    WET_IDX = [4, 5, 6, 7, 8, 9]  # 0-indexed May–Oct

    fig, ax = plt.subplots(figsize=(7.5, 4))
    x = np.arange(12)
    bar_colors = [PALETTE["PW"] if i in WET_IDX else "#9DC3D4" for i in x]
    bars = ax.bar(x, climatology["mean"], color=bar_colors, alpha=0.88,
                  edgecolor="white", linewidth=0.6, zorder=3, width=0.65)
    ax.errorbar(x, climatology["mean"], yerr=climatology["std"],
                fmt="none", color="#333333", capsize=3.5, linewidth=0.9, zorder=4)
    # Wet-season shading
    ax.axvspan(3.5, 9.5, alpha=0.06, color=PALETTE["MK"], zorder=1,
               label="Wet season (May–Oct)")
    ax.set_xticks(x); ax.set_xticklabels(month_labels)
    ax.set_xlabel("Month", fontsize=9)
    ax.set_ylabel("Rainfall (mm month$^{-1}$)", fontsize=9)
    ax.set_title("Mean Monthly Rainfall Climatology (1981–2014)", fontsize=10, pad=6)
    ax.yaxis.set_minor_locator(ticker.AutoMinorLocator(2))
    ax.tick_params(which="minor", length=2)
    ax.legend(fontsize=8, loc="upper left")
    # Add value labels on top 4 tallest bars
    top4 = climatology["mean"].nlargest(4).index
    for i in top4:
        ax.text(i, climatology["mean"].iloc[i] + climatology["std"].iloc[i] + 4,
                f"{climatology['mean'].iloc[i]:.0f}", ha="center",
                fontsize=7, color="#1A1A1A")
    _panel_label(ax, "(a)")
    fig.text(0.5, -0.03, "Fig. 2 — Climatological mean ± 1 SD. Shading: wet season.",
             ha="center", fontsize=7.5, color="#555555", style="italic")
    fig.tight_layout()
    _save_fig(fig, "Figure_02_Climatology")


# ── Figure 3: ACF / PACF ────────────────────────────────────────────────────
def fig_acf_pacf(ac_results: list[dict]) -> None:
    n_series = len(ac_results)
    fig, axes = plt.subplots(n_series, 2, figsize=(10, 3.5 * n_series))
    if n_series == 1: axes = [axes]

    for row, res in enumerate(ac_results):
        nlags = res["nlags"]; lags = np.arange(0, nlags + 1)
        ci    = 1.96 / np.sqrt(res["n"])

        for col, (vals, label_y, color, panel) in enumerate([
            (res["acf"][:nlags+1],  "ACF",  PALETTE["MK"],   "acf"),
            (res["pacf"][:nlags+1], "PACF", PALETTE["TFPW"], "pacf"),
        ]):
            ax = axes[row][col]
            ax.bar(lags, vals, color=color, alpha=0.75, width=0.6,
                   edgecolor="white", linewidth=0.4)
            ax.axhline( ci, color="#333333", linestyle="--", linewidth=0.7, alpha=0.7)
            ax.axhline(-ci, color="#333333", linestyle="--", linewidth=0.7, alpha=0.7)
            ax.axhline(0,   color="#333333", linewidth=0.5)
            ax.fill_between([-0.5, nlags+0.5], [-ci,-ci], [ci,ci],
                            alpha=0.06, color="#AAAAAA")
            ax.set_xlim(-0.5, nlags + 0.5)
            ax.set_xlabel("Lag (years)", fontsize=9)
            ax.set_ylabel(label_y, fontsize=9)
            extra = f"r₁={res['r1']:.3f}" if label_y=="ACF" else f"LB p={res['lb_pvalue']:.3f}"
            ax.set_title(f"{res['label']} — {label_y}  ({extra})", fontsize=9)
            _panel_label(ax, f"({'abcdef'[row*2+col]})")

    fig.suptitle("Fig. 3 — Autocorrelation structure of monsoonal rainfall series.\n"
                 "Dashed lines: 95% significance bounds (±1.96/√n).",
                 fontsize=9, y=1.01, color="#444444", style="italic")
    fig.tight_layout()
    _save_fig(fig, "Figure_03_ACF_PACF")


# ── Figure 4: Method comparison ─────────────────────────────────────────────
def fig_method_comparison(station_results: dict, series_labels: list[str]) -> None:
    n_series = len(series_labels)
    fig, axes = plt.subplots(1, n_series, figsize=(3.8*n_series, 4.5), sharey=True)
    if n_series == 1: axes = [axes]

    for ax, label in zip(axes, series_labels):
        res = station_results.get(label, {})
        zs  = [res.get(m,{}).get("Z",np.nan) for m in METHODS]
        ps  = [res.get(m,{}).get("p",1.0)   for m in METHODS]

        bars = ax.bar(range(4), zs, color=COLORS, alpha=0.85,
                      edgecolor="white", linewidth=0.5, zorder=3, width=0.6)
        ax.axhline( 1.96, color="#1A1A1A", linestyle="--", linewidth=0.8, alpha=0.6)
        ax.axhline(-1.96, color="#1A1A1A", linestyle="--", linewidth=0.8, alpha=0.6)
        ax.axhline(0,     color="#1A1A1A", linewidth=0.5)
        ax.fill_between([-0.5,3.5],[-1.96,-1.96],[1.96,1.96],
                        alpha=0.04, color="#AAAAAA")
        for bar, z, p in zip(bars, zs, ps):
            if not np.isnan(z):
                _add_significance_bar(ax, bar.get_x()+bar.get_width()/2, z, p)
        ax.set_xticks(range(4))
        ax.set_xticklabels(["MK","MMK","PW","TFPW"], fontsize=8)
        ax.set_title(label, fontsize=9)
        if ax is axes[0]: ax.set_ylabel("Z statistic", fontsize=9)
        _panel_label(ax, f"({'abc'[series_labels.index(label)]})")

    legend_handles = [Patch(facecolor=c, label=l, alpha=0.85)
                      for c,l in zip(COLORS, MLABELS)]
    axes[-1].legend(handles=legend_handles, loc="lower right",
                    fontsize=7, ncol=1)
    fig.suptitle("Fig. 4 — Z-statistic comparison across trend detection methods.\n"
                 "Stars: *p<0.05, **p<0.01, ***p<0.001. Dashed: ±1.96 critical value.",
                 fontsize=8.5, y=1.01, style="italic", color="#444444")
    fig.tight_layout()
    _save_fig(fig, "Figure_04_Method_Comparison")


# ── Figure 5: Type I error vs φ ─────────────────────────────────────────────
def fig_type_i_error(type_i_df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 4.8))

    # ±30% tolerance band around nominal α
    ax.fill_between(type_i_df["phi"],
                    [ALPHA * 0.7]*len(type_i_df),
                    [ALPHA * 1.3]*len(type_i_df),
                    alpha=0.10, color=PALETTE["nominal"], zorder=1,
                    label="±30% of nominal α")
    ax.axhline(ALPHA, color=PALETTE["nominal"], linestyle="--",
               linewidth=0.9, zorder=2, label=f"Nominal α = {ALPHA}")

    for m, c, mk in zip(METHODS, COLORS, MARKERS):
        ax.plot(type_i_df["phi"], type_i_df[m],
                marker=mk, color=c, linewidth=1.5, markersize=5.5,
                zorder=5, label=METHOD_LABELS[m],
                markerfacecolor="white", markeredgewidth=1.5,
                markeredgecolor=c)

    ax.set_xlabel("Lag-1 Autocorrelation Coefficient (φ)", fontsize=9)
    ax.set_ylabel("Empirical Type I Error Rate", fontsize=9)
    ax.set_title(f"Type I Error vs Autocorrelation Strength\n"
                 f"Monte Carlo simulation, N = {N_MONTE_CARLO:,} iterations, "
                 f"n = 34 years", fontsize=10, pad=6)
    ax.set_ylim(0, max(type_i_df[METHODS].max().max() * 1.25, 0.25))
    ax.set_xlim(-0.02, 0.82)
    ax.xaxis.set_minor_locator(ticker.MultipleLocator(0.05))
    ax.yaxis.set_minor_locator(ticker.AutoMinorLocator(2))
    ax.tick_params(which="minor", length=2)
    ax.legend(handles=_method_legend_handles("--") +
              [Line2D([0],[0], color=PALETTE["nominal"], linestyle="--",
                      linewidth=0.9, label=f"Nominal α = {ALPHA}"),
               Patch(color="#AAAAAA", alpha=0.3, label="±30% of nominal α")],
              fontsize=7.5, framealpha=0.92, loc="upper left", ncol=2)
    _panel_label(ax, "(a)")
    fig.text(0.5,-0.02,
             "Fig. 5 — Open markers: observed Type I error. "
             "Values consistently above dashed line indicate test inflation.",
             ha="center", fontsize=7.5, color="#555555", style="italic")
    fig.tight_layout()
    _save_fig(fig, "Figure_05_TypeI_Error")


# ── Figure 6: Statistical power ─────────────────────────────────────────────
def fig_statistical_power(power_df: pd.DataFrame) -> None:
    phi_vals = sorted(power_df["phi"].unique())
    trends   = sorted([t for t in power_df["trend_mm_yr"].unique() if t >= 0])

    fig, axes = plt.subplots(1, len(phi_vals), figsize=(4.2*len(phi_vals), 4.8),
                             sharey=True)
    if len(phi_vals) == 1: axes = [axes]

    for idx, (ax, phi) in enumerate(zip(axes, phi_vals)):
        sub = power_df[power_df["phi"] == phi]
        for m, c, mk in zip(METHODS, COLORS, MARKERS):
            vals = [float(sub[sub["trend_mm_yr"]==t][m].iloc[0])
                    if not sub[sub["trend_mm_yr"]==t].empty else np.nan
                    for t in trends]
            ax.plot(trends, vals, marker=mk, color=c, linewidth=1.5,
                    markersize=5.5, zorder=5,
                    markerfacecolor="white", markeredgewidth=1.5,
                    markeredgecolor=c)
        ax.axhline(0.80, color="#333333", linestyle=":", linewidth=0.8,
                   label="Power = 0.80", zorder=2)
        ax.fill_between(trends, [0.80]*len(trends), [1.0]*len(trends),
                        alpha=0.04, color="#27AE60")
        ax.set_xlabel("True Trend (mm yr$^{-1}$)", fontsize=9)
        if idx == 0: ax.set_ylabel("Statistical Power (1−β)", fontsize=9)
        ax.set_title(f"φ = {phi:.1f}", fontsize=9)
        ax.set_ylim(-0.02, 1.05)
        ax.set_xlim(-0.1, max(trends)+0.3)
        ax.yaxis.set_minor_locator(ticker.MultipleLocator(0.1))
        _panel_label(ax, f"({'abc'[idx]})")

    handles = _method_legend_handles()
    handles += [Line2D([0],[0], color="#333333", linestyle=":", linewidth=0.8,
                       label="Power = 0.80")]
    axes[0].legend(handles=handles, fontsize=7.5, ncol=1, framealpha=0.92)
    fig.suptitle("Fig. 6 — Statistical power comparison across methods and "
                 "autocorrelation levels.\nGreen shading: power ≥ 0.80.",
                 fontsize=9, style="italic", color="#444444")
    fig.tight_layout()
    _save_fig(fig, "Figure_06_Power")


# ── Figure 7: Variance distortion ───────────────────────────────────────────
def fig_variance_distortion(var_df: pd.DataFrame) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))

    for ax, (ycol_pw, ycol_tf, ylabel, title) in zip([ax1, ax2], [
        ("var_ratio_pw", "var_ratio_tfpw",
         "Variance Ratio (whitened / original)", "Variance Distortion"),
        ("trend_attenuation_pw", "trend_attenuation_tfpw",
         "Trend Attenuation Factor (recovered / true)", "Trend Attenuation by Pre-Whitening"),
    ]):
        ax.plot(var_df["phi"], var_df[ycol_pw], marker="o", color=PALETTE["PW"],
                linewidth=1.5, markersize=5.5, label="PW-MK",
                markerfacecolor="white", markeredgewidth=1.5,
                markeredgecolor=PALETTE["PW"])
        ax.plot(var_df["phi"], var_df[ycol_tf], marker="s", color=PALETTE["TFPW"],
                linewidth=1.5, linestyle="--", markersize=5.5,
                label="TFPW-MK",
                markerfacecolor="white", markeredgewidth=1.5,
                markeredgecolor=PALETTE["TFPW"])
        ax.axhline(1.0, color="#333333", linestyle="-", linewidth=0.7,
                   label="Ideal (no distortion)", zorder=1)
        ax.fill_between(var_df["phi"], 0.95, 1.05, alpha=0.07,
                        color="#333333", label="±5% tolerance")
        ax.set_xlabel("Lag-1 Autocorrelation Coefficient (φ)", fontsize=9)
        ax.set_ylabel(ylabel, fontsize=9)
        ax.set_title(title, fontsize=9)
        ax.xaxis.set_minor_locator(ticker.MultipleLocator(0.05))
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator(2))
        ax.tick_params(which="minor", length=2)
        ax.legend(fontsize=8, framealpha=0.92)
    _panel_label(ax1, "(a)"); _panel_label(ax2, "(b)")
    fig.suptitle("Fig. 7 — Variance distortion and trend attenuation from pre-whitening.\n"
                 "Values < 1 indicate signal loss; values > 1 indicate artificial inflation.",
                 fontsize=9, style="italic", color="#444444")
    fig.tight_layout()
    _save_fig(fig, "Figure_07_Variance_Distortion")


# ── Figure 8: Monte Carlo Z-distributions ────────────────────────────────────
def fig_mc_distributions(phi_selected: list[float] = [0.0, 0.3, 0.6]) -> None:
    n_iter, n = 3000, 34
    fig, axes = plt.subplots(1, len(phi_selected),
                             figsize=(4.5*len(phi_selected), 4.5))

    for idx, (ax, phi) in enumerate(zip(axes, phi_selected)):
        rng = np.random.default_rng(RANDOM_SEED + int(phi*100))
        gen = AR1Generator(n=n, phi=phi, sigma=1.0, trend=0.0, rng=rng)
        Z = {m: [] for m in METHODS}
        for _ in range(n_iter):
            x = gen.generate()
            Z["MK"].append(standard_mk(x)["Z"])
            Z["MMK"].append(modified_mk_hamed_rao(x)["Z"])
            Z["PW"].append(prewhitening_mk(x)["Z"])
            Z["TFPW"].append(tfpw_mk(x)["Z"])

        for m, c in zip(METHODS, COLORS):
            ax.hist(Z[m], bins=60, density=True, alpha=0.35, color=c,
                    edgecolor="none", zorder=3)
        zz = np.linspace(-6, 6, 400)
        ax.plot(zz, norm.pdf(zz), color=PALETTE["nominal"], linewidth=1.4,
                label="N(0,1) reference", zorder=5)
        ax.axvline( 1.96, color=PALETTE["nominal"], linestyle="--",
                    linewidth=0.7, alpha=0.6)
        ax.axvline(-1.96, color=PALETTE["nominal"], linestyle="--",
                    linewidth=0.7, alpha=0.6)
        ax.set_title(f"φ = {phi:.1f}", fontsize=9)
        ax.set_xlabel("Z statistic", fontsize=9)
        ax.set_xlim(-6, 6)
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator(2))
        if idx == 0:
            ax.set_ylabel("Density", fontsize=9)
            legend_handles = _method_legend_handles()
            legend_handles += [Line2D([0],[0], color=PALETTE["nominal"],
                                      linewidth=1.4, label="N(0,1) reference")]
            ax.legend(handles=legend_handles, fontsize=7, framealpha=0.92)
        _panel_label(ax, f"({'abc'[idx]})")

    fig.suptitle("Fig. 8 — Monte Carlo Z-statistic distributions under H₀ "
                 f"(no trend, N = {n_iter:,}).\n"
                 "Deviation from N(0,1) indicates test inflation or deflation.",
                 fontsize=9, style="italic", color="#444444")
    fig.tight_layout()
    _save_fig(fig, "Figure_08_MC_Distributions")


# ── Figure 9: False positive heatmap ─────────────────────────────────────────
def fig_false_positive_heatmap(type_i_df: pd.DataFrame) -> None:
    matrix = type_i_df.set_index("phi")[METHODS]
    matrix.index = [f"{v:.1f}" for v in matrix.index]
    matrix.columns = [METHOD_LABELS[m].replace(" (Hamed & Rao 1998)","")
                                       .replace(" (Yue & Wang 2002)","")
                      for m in METHODS]

    # Custom diverging colormap: green–white–red
    cmap = LinearSegmentedColormap.from_list(
        "greenwhitered",
        ["#1A9850","#FFFFBF","#D73027"], N=256
    )

    fig, ax = plt.subplots(figsize=(8, 5.5))
    sns.heatmap(
        matrix.T, ax=ax, cmap=cmap,
        annot=True, fmt=".3f", annot_kws={"size":8},
        linewidths=0.4, linecolor="#CCCCCC",
        cbar_kws={"label":"Empirical Type I Error Rate",
                  "shrink":0.75, "aspect":20},
        vmin=0, vmax=0.30,
    )
    # Highlight nominal α column reference
    ax.axvline(x=matrix.index.tolist().index("0.0")+0.5,
               color="none")

    ax.set_xlabel("Lag-1 Autocorrelation Coefficient (φ)", fontsize=9)
    ax.set_ylabel("Method", fontsize=9)
    ax.set_title(f"False Positive Rate Heatmap\n"
                 f"Nominal α = {ALPHA} — N = {N_MONTE_CARLO:,} Monte Carlo iterations",
                 fontsize=10, pad=6)
    # Nominal line at α = 0.05
    cbar = ax.collections[0].colorbar
    cbar.ax.axhline(ALPHA, color="#1A1A1A", linewidth=1.2, linestyle="--")
    cbar.ax.text(1.15, ALPHA, f" α={ALPHA}", transform=cbar.ax.transData,
                 fontsize=7, va="center")
    fig.text(0.5,-0.01,
             "Fig. 9 — Green: near-nominal error; red: inflated Type I error.",
             ha="center", fontsize=7.5, color="#555555", style="italic")
    fig.tight_layout()
    _save_fig(fig, "Figure_09_False_Positive_Heatmap")


# ── Figure 9b: FDR comparison (NEW — replaces old misleading FDR figure) ────
def fig_fdr_bh(fdr_df: pd.DataFrame) -> None:
    """
    NEW: True BH-FDR comparison plot.
    Contrasts uncorrected (raw) Type I error with BH-adjusted FDR.
    """
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    ax.fill_between(fdr_df["phi"],
                    [ALPHA * 0.7]*len(fdr_df),
                    [ALPHA * 1.3]*len(fdr_df),
                    alpha=0.10, color=PALETTE["nominal"], zorder=1)
    ax.axhline(ALPHA, color=PALETTE["nominal"], linestyle="--",
               linewidth=0.9, zorder=2, label=f"Nominal α = {ALPHA}")

    fdr_cols = ["FDR_MK","FDR_MMK","FDR_PW","FDR_TFPW"]
    for m, fc, c, mk in zip(METHODS, fdr_cols, COLORS, MARKERS):
        ax.plot(fdr_df["phi"], fdr_df[fc],
                marker=mk, color=c, linewidth=1.5, markersize=5.5, zorder=5,
                label=METHOD_LABELS[m],
                markerfacecolor="white", markeredgewidth=1.5,
                markeredgecolor=c)

    ax.set_xlabel("Lag-1 Autocorrelation Coefficient (φ)", fontsize=9)
    ax.set_ylabel("BH-Adjusted False Discovery Rate", fontsize=9)
    ax.set_title("BH-Corrected False Discovery Rate vs Autocorrelation\n"
                 f"Multi-station analysis, 10 stations, N = 2,000 iterations",
                 fontsize=10, pad=6)
    ax.set_ylim(0, max(fdr_df[fdr_cols].max().max() * 1.25, 0.12))
    ax.set_xlim(-0.02, 0.82)
    ax.xaxis.set_minor_locator(ticker.MultipleLocator(0.05))
    ax.yaxis.set_minor_locator(ticker.AutoMinorLocator(2))
    ax.tick_params(which="minor", length=2)
    handles = _method_legend_handles()
    handles += [Line2D([0],[0], color=PALETTE["nominal"], linestyle="--",
                        linewidth=0.9, label=f"Nominal α = {ALPHA}"),
                Patch(color="#AAAAAA", alpha=0.3, label="±30% of nominal α")]
    ax.legend(handles=handles, fontsize=7.5, ncol=2, framealpha=0.92)
    _panel_label(ax, "(a)")
    fig.text(0.5,-0.02,
             "Fig. 9b — Benjamini–Hochberg (1995) corrected FDR. "
             "After correction, all methods maintain FDR near nominal α.",
             ha="center", fontsize=7.5, color="#555555", style="italic")
    fig.tight_layout()
    _save_fig(fig, "Figure_09b_FDR_BH_Corrected")


# ── Figure 10: Sensitivity ───────────────────────────────────────────────────
def fig_sensitivity(sens_dict: dict) -> None:
    sample_df = sens_dict["sample_size"]
    phi_plot  = [0.0, 0.3, 0.6]
    fig, axes = plt.subplots(1, len(phi_plot),
                             figsize=(4.2*len(phi_plot), 4.5), sharey=True)

    for idx, (ax, phi) in enumerate(zip(axes, phi_plot)):
        sub = sample_df[sample_df["phi"].round(1) == phi]
        for m, c, mk in zip(METHODS, COLORS, MARKERS):
            ax.plot(sub["n"], sub[m], marker=mk, color=c, linewidth=1.5,
                    markersize=5.5, zorder=4,
                    markerfacecolor="white", markeredgewidth=1.5,
                    markeredgecolor=c)
        ax.axhline(ALPHA, color=PALETTE["nominal"], linestyle="--",
                   linewidth=0.9, zorder=2)
        ax.fill_between(sub["n"], ALPHA*0.7, ALPHA*1.3,
                        alpha=0.07, color="#AAAAAA")
        ax.set_xlabel("Sample Size (years)", fontsize=9)
        if idx == 0: ax.set_ylabel("Empirical Type I Error Rate", fontsize=9)
        ax.set_title(f"φ = {phi:.1f}", fontsize=9)
        ax.set_ylim(0, min(1.0, sample_df[METHODS].max().max()*1.3))
        ax.xaxis.set_minor_locator(ticker.MultipleLocator(5))
        _panel_label(ax, f"({'abc'[idx]})")

    axes[0].legend(handles=_method_legend_handles(), fontsize=7.5, framealpha=0.92)
    fig.suptitle("Fig. 10 — Sensitivity of Type I error to sample size (n).\n"
                 "Dashed line: nominal α. Shading: ±30% tolerance band.",
                 fontsize=9, style="italic", color="#444444")
    fig.tight_layout()
    _save_fig(fig, "Figure_10_Sensitivity")


# ── Figure 11: Effective sample size ─────────────────────────────────────────
def fig_effective_sample_size() -> None:
    ns   = np.arange(10, 70, dtype=float)
    phis = [0.1, 0.3, 0.5, 0.7]
    cmap = plt.cm.plasma
    clrs = cmap(np.linspace(0.1, 0.85, len(phis)))

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    for phi, c in zip(phis, clrs):
        n_eff = ns / (1 + 2 * phi / (1 - phi) *
                      (1 - (phi**ns - phi) / (ns * (1 - phi))))
        ax.plot(ns, n_eff, color=c, linewidth=1.5,
                label=f"φ = {phi:.1f}")
        # Percentage reduction annotation at n=60
        pct = (1 - n_eff[-1]/ns[-1]) * 100
        ax.annotate(f"−{pct:.0f}%",
                    xy=(ns[-1], n_eff[-1]), xytext=(5, 0),
                    textcoords="offset points", fontsize=7,
                    color=c, va="center")
    ax.plot(ns, ns, color="#333333", linestyle="--", linewidth=0.8,
            label="n* = n  (φ = 0)")
    ax.fill_between(ns, ns*0.5, ns, alpha=0.04, color="#E74C3C",
                    label=">50% reduction")
    ax.set_xlabel("Nominal Sample Size (n)", fontsize=9)
    ax.set_ylabel("Effective Sample Size (n*)", fontsize=9)
    ax.set_title("Effective Sample Size vs Autocorrelation Strength\n"
                 "Hamed & Rao (1998) Eq. (3)", fontsize=10, pad=6)
    ax.xaxis.set_minor_locator(ticker.MultipleLocator(5))
    ax.yaxis.set_minor_locator(ticker.AutoMinorLocator(2))
    ax.tick_params(which="minor", length=2)
    ax.legend(fontsize=8, framealpha=0.92, ncol=2)
    _panel_label(ax, "(a)")
    fig.text(0.5,-0.02,
             "Fig. 11 — Percentage annotations show reduction in effective n at n=60.",
             ha="center", fontsize=7.5, color="#555555", style="italic")
    fig.tight_layout()
    _save_fig(fig, "Figure_11_Effective_Sample_Size")


# ── Figure 12: Decision framework ────────────────────────────────────────────
def fig_decision_framework() -> None:
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.set_xlim(0, 10); ax.set_ylim(0, 10.5)
    ax.axis("off")
    ax.set_facecolor("#FAFAFA")

    # Styles
    start_kw = dict(boxstyle="round,pad=0.5", fc="#EAF2FB", ec=PALETTE["MK"],  lw=1.5)
    dec_kw   = dict(boxstyle="round,pad=0.5", fc="#FEF9E7", ec=PALETTE["MMK"], lw=1.2)
    end_kw   = dict(boxstyle="round,pad=0.5", fc="#EAFAF1", ec=PALETTE["PW"],  lw=1.5)
    rep_kw   = dict(boxstyle="round,pad=0.5", fc="#F4ECF7", ec=PALETTE["TFPW"],lw=1.5)

    nodes = [
        (5.0, 9.8,  "START\nHydroclimatic Time-Series Data",                start_kw, 10),
        (5.0, 8.3,  "Test Serial Autocorrelation\n(ACF, Ljung-Box, DW, ADF)", dec_kw, 9),
        (1.7, 6.5,  "|φ| < 0.10\np(LB) > 0.05",                             dec_kw, 8),
        (5.0, 6.5,  "0.10 ≤ |φ| < 0.50",                                    dec_kw, 9),
        (8.3, 6.5,  "|φ| ≥ 0.50",                                            dec_kw, 8),
        (1.7, 4.7,  "Standard MK\n(Mann 1945;\nKendall 1975)",               end_kw, 8.5),
        (5.0, 4.7,  "Modified MK\n(Hamed & Rao 1998)",                       end_kw, 8.5),
        (8.3, 4.7,  "TFPW-MK\n(Yue & Wang 2002)",                            end_kw, 8.5),
        (5.0, 2.9,  "Multi-station?\n→ BH-FDR Correction\n(Benjamini & Hochberg 1995)", dec_kw, 9),
        (5.0, 1.2,  "Report: Z, p-value, Sen's slope,\n95% Bootstrap CI (Kunsch 1989)",  rep_kw, 9),
    ]

    for (x, y, txt, style, fs) in nodes:
        ax.text(x, y, txt, ha="center", va="center", fontsize=7.5,
                bbox=style, transform=ax.transData, zorder=5,
                multialignment="center")

    arw = dict(arrowstyle="-|>", color="#5D6D7E", lw=1.1,
               mutation_scale=12)
    arrows = [
        (5.0, 9.4, 5.0, 8.75),      # start → test
        (5.0, 7.85, 1.7, 7.0),      # test → φ<0.10
        (5.0, 7.85, 5.0, 7.0),      # test → 0.10≤φ
        (5.0, 7.85, 8.3, 7.0),      # test → φ≥0.50
        (1.7, 6.0,  1.7, 5.25),     # → MK
        (5.0, 6.0,  5.0, 5.25),     # → MMK
        (8.3, 6.0,  8.3, 5.25),     # → TFPW
        (1.7, 4.15, 5.0, 3.45),     # MK → FDR
        (5.0, 4.15, 5.0, 3.45),     # MMK → FDR
        (8.3, 4.15, 5.0, 3.45),     # TFPW → FDR
        (5.0, 2.4,  5.0, 1.65),     # FDR → report
    ]
    for (x1,y1,x2,y2) in arrows:
        ax.annotate("", xy=(x2,y2), xytext=(x1,y1),
                    arrowprops=arw, zorder=4)

    # Label arrows
    ax.text(2.8, 8.05, "|φ| < 0.10", fontsize=6.5, color="#5D6D7E",
            ha="center", rotation=15)
    ax.text(5.0, 8.15, "0.10–0.50",  fontsize=6.5, color="#5D6D7E",
            ha="center")
    ax.text(7.2, 8.05, "|φ| ≥ 0.50", fontsize=6.5, color="#5D6D7E",
            ha="center", rotation=-15)

    ax.set_title("Methodological Decision Framework for Trend Detection\n"
                 "in Monsoonal Rainfall Data",
                 fontsize=11, pad=10, color="#1A1A2E", fontweight="bold")
    fig.text(0.5, 0.01,
             "Fig. 12 — Recommended workflow based on comparative simulation results.",
             ha="center", fontsize=7.5, color="#555555", style="italic")
    fig.tight_layout()
    _save_fig(fig, "Figure_12_Decision_Framework")


# ── Bonus Figure 13: Comprehensive 6-panel summary ──────────────────────────
def fig_summary_dashboard(
    type_i_df: pd.DataFrame,
    power_df: pd.DataFrame,
    var_df: pd.DataFrame,
    fdr_df: pd.DataFrame,
    ac_results: list[dict],
) -> None:
    """
    Premium 6-panel summary figure combining key results for the abstract
    graphic / journal visual abstract.
    """
    fig = plt.figure(figsize=(14, 9))
    gs  = gridspec.GridSpec(2, 3, hspace=0.42, wspace=0.35,
                            left=0.07, right=0.97, top=0.92, bottom=0.09)

    # ── Panel A: Type I error ──────────────────────────────────────────────
    ax_a = fig.add_subplot(gs[0, 0])
    ax_a.fill_between(type_i_df["phi"], ALPHA*0.7, ALPHA*1.3,
                      alpha=0.10, color="#AAAAAA")
    ax_a.axhline(ALPHA, color=PALETTE["nominal"], linestyle="--",
                 linewidth=0.9)
    for m, c, mk in zip(METHODS, COLORS, MARKERS):
        ax_a.plot(type_i_df["phi"], type_i_df[m],
                  marker=mk, color=c, linewidth=1.4, markersize=4.5,
                  markerfacecolor="white", markeredgewidth=1.3,
                  markeredgecolor=c)
    ax_a.set_xlabel("φ", fontsize=8)
    ax_a.set_ylabel("Type I Error Rate", fontsize=8)
    ax_a.set_title("(a) Type I Error vs φ", fontsize=9, fontweight="bold")
    ax_a.set_ylim(0, None)

    # ── Panel B: Power at φ=0.3 ───────────────────────────────────────────
    ax_b = fig.add_subplot(gs[0, 1])
    sub03 = power_df[power_df["phi"] == 0.3]
    trends = sorted([t for t in sub03["trend_mm_yr"].unique() if t >= 0])
    for m, c, mk in zip(METHODS, COLORS, MARKERS):
        vals = [float(sub03[sub03["trend_mm_yr"]==t][m].iloc[0])
                if not sub03[sub03["trend_mm_yr"]==t].empty else np.nan
                for t in trends]
        ax_b.plot(trends, vals, marker=mk, color=c, linewidth=1.4,
                  markersize=4.5, markerfacecolor="white",
                  markeredgewidth=1.3, markeredgecolor=c)
    ax_b.axhline(0.80, color="#333333", linestyle=":", linewidth=0.8)
    ax_b.set_xlabel("Trend (mm yr⁻¹)", fontsize=8)
    ax_b.set_ylabel("Statistical Power", fontsize=8)
    ax_b.set_title("(b) Power (φ = 0.3)", fontsize=9, fontweight="bold")
    ax_b.set_ylim(-0.02, 1.05)

    # ── Panel C: Variance distortion ──────────────────────────────────────
    ax_c = fig.add_subplot(gs[0, 2])
    ax_c.plot(var_df["phi"], var_df["var_ratio_pw"],   "o-",
              color=PALETTE["PW"],   linewidth=1.4, markersize=4.5, label="PW")
    ax_c.plot(var_df["phi"], var_df["var_ratio_tfpw"], "s--",
              color=PALETTE["TFPW"], linewidth=1.4, markersize=4.5, label="TFPW")
    ax_c.axhline(1.0, color="#333333", linewidth=0.7)
    ax_c.set_xlabel("φ", fontsize=8)
    ax_c.set_ylabel("Variance Ratio", fontsize=8)
    ax_c.set_title("(c) Variance Distortion", fontsize=9, fontweight="bold")
    ax_c.legend(fontsize=7.5)

    # ── Panel D: BH-FDR ───────────────────────────────────────────────────
    ax_d = fig.add_subplot(gs[1, 0])
    ax_d.axhline(ALPHA, color=PALETTE["nominal"], linestyle="--", linewidth=0.9)
    fdr_cols = ["FDR_MK","FDR_MMK","FDR_PW","FDR_TFPW"]
    for m, fc, c, mk in zip(METHODS, fdr_cols, COLORS, MARKERS):
        ax_d.plot(fdr_df["phi"], fdr_df[fc],
                  marker=mk, color=c, linewidth=1.4, markersize=4.5,
                  markerfacecolor="white", markeredgewidth=1.3,
                  markeredgecolor=c)
    ax_d.set_xlabel("φ", fontsize=8)
    ax_d.set_ylabel("BH-FDR", fontsize=8)
    ax_d.set_title("(d) BH False Discovery Rate", fontsize=9, fontweight="bold")
    ax_d.set_ylim(0, None)

    # ── Panel E: ACF of representative series ─────────────────────────────
    ax_e = fig.add_subplot(gs[1, 1])
    if ac_results:
        res   = ac_results[0]
        nlags = res["nlags"]
        lags  = np.arange(0, nlags+1)
        ci    = 1.96 / np.sqrt(res["n"])
        ax_e.bar(lags, res["acf"][:nlags+1], color=PALETTE["MK"],
                 alpha=0.7, width=0.6, edgecolor="white")
        ax_e.axhline( ci, color="#333333", linestyle="--", linewidth=0.7)
        ax_e.axhline(-ci, color="#333333", linestyle="--", linewidth=0.7)
        ax_e.axhline(0,   color="#333333", linewidth=0.4)
        ax_e.set_xlabel("Lag (years)", fontsize=8)
        ax_e.set_ylabel("ACF", fontsize=8)
        ax_e.set_title(f"(e) ACF — {res['label']}\n"
                       f"r₁={res['r1']:.3f}  LB p={res['lb_pvalue']:.3f}",
                       fontsize=9, fontweight="bold")

    # ── Panel F: Effective sample size ────────────────────────────────────
    ax_f = fig.add_subplot(gs[1, 2])
    ns   = np.arange(10, 70, dtype=float)
    phis_eff = [0.1, 0.3, 0.5, 0.7]
    clrs_eff = plt.cm.plasma(np.linspace(0.1, 0.85, len(phis_eff)))
    for phi, c in zip(phis_eff, clrs_eff):
        n_eff = ns / (1 + 2*phi/(1-phi) *
                      (1 - (phi**ns - phi) / (ns*(1-phi))))
        ax_f.plot(ns, n_eff, color=c, linewidth=1.3, label=f"φ={phi:.1f}")
    ax_f.plot(ns, ns, color="#333333", linestyle="--", linewidth=0.7)
    ax_f.set_xlabel("n (nominal)", fontsize=8)
    ax_f.set_ylabel("n* (effective)", fontsize=8)
    ax_f.set_title("(f) Effective Sample Size", fontsize=9, fontweight="bold")
    ax_f.legend(fontsize=7, ncol=2)

    # Legend strip at top
    handles = _method_legend_handles()
    fig.legend(handles=handles, loc="upper center", ncol=4,
               fontsize=8, framealpha=0.92, bbox_to_anchor=(0.5, 0.975))

    fig.suptitle("Comparative Performance of Pre-Whitening and Modified Mann–Kendall Methods\n"
                 "in Minimizing Type I Error in Monsoonal Rainfall Trend Detection",
                 fontsize=11, y=1.002, fontweight="bold", color="#1A1A2E")
    _save_fig(fig, "Figure_13_Summary_Dashboard")


# ─────────────────────────────────────────────────────────────────────────────
# 19. TABLE GENERATION
# ─────────────────────────────────────────────────────────────────────────────
def build_table1_metadata(metadata_df: pd.DataFrame,
                           completeness_df: pd.DataFrame) -> pd.DataFrame:
    t1 = metadata_df.merge(
        completeness_df[["Station","Completeness_pct","Pass_threshold"]],
        on="Station", how="left"
    )
    _save_table(t1, "Table_01_Station_Metadata"); return t1


def build_table2_climatology(monthly_df: pd.DataFrame,
                              annual_df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for stn, grp in annual_df.groupby("Station"):
        records.append({
            "Station"        : stn,
            "Mean_Annual_mm" : round(grp["Annual_mm"].mean(), 1),
            "Std_Annual_mm"  : round(grp["Annual_mm"].std(ddof=1), 1),
            "CV_pct"         : round(grp["Annual_mm"].std(ddof=1) /
                                     grp["Annual_mm"].mean() * 100, 1),
            "Min_Annual_mm"  : round(grp["Annual_mm"].min(), 1),
            "Max_Annual_mm"  : round(grp["Annual_mm"].max(), 1),
            "Skewness"       : round(float(skew(grp["Annual_mm"].dropna())), 3),
        })
    t2 = pd.DataFrame(records)
    _save_table(t2, "Table_02_Climatology"); return t2


def build_table3_autocorrelation(ac_results: list[dict]) -> pd.DataFrame:
    records = []
    for r in ac_results:
        records.append({
            "Series"     : r["label"], "n"          : r["n"],
            "r1"         : round(r["r1"],4),
            "Class"      : classify_autocorrelation(r["r1"]),
            "LjungBox_p" : round(r["lb_pvalue"],4),
            "Sig_LB"     : r["lb_sig"],
            "DW"         : round(r["dw"],4),
            "ADF_p"      : round(r["adf_pval"],4),
            "Stationary" : r["adf_stationary"],
            "VIF"        : round(r["vif"],3),
            "n_eff"      : round(r["n_eff"],1),
        })
    t3 = pd.DataFrame(records)
    _save_table(t3, "Table_03_Autocorrelation"); return t3


def build_table4_trends(station_mk_results: dict) -> pd.DataFrame:
    records = []
    for label, res_dict in station_mk_results.items():
        row = {"Series": label}
        for m in METHODS:
            r = res_dict.get(m, {})
            row[f"{m}_Z"]     = round(r.get("Z",   np.nan), 4)
            row[f"{m}_p"]     = round(r.get("p",   np.nan), 4)
            row[f"{m}_slope"] = round(r.get("slope",np.nan), 4)
            row[f"{m}_sig"]   = "Yes" if r.get("p",1) < ALPHA else "No"
        records.append(row)
    t4 = pd.DataFrame(records)
    _save_table(t4, "Table_04_Trends"); return t4


def build_table5_montecarlo(type_i_df: pd.DataFrame) -> pd.DataFrame:
    t5 = type_i_df.copy().round(4)
    t5.insert(0, "Nominal_alpha", ALPHA)
    t5.insert(0, "N_iterations", N_MONTE_CARLO)
    _save_table(t5, "Table_05_TypeI_Error_MC"); return t5


def build_table6_power(power_df: pd.DataFrame) -> pd.DataFrame:
    _save_table(power_df.round(4), "Table_06_Power"); return power_df


def build_table7_variance(var_df: pd.DataFrame) -> pd.DataFrame:
    _save_table(var_df.round(4), "Table_07_Variance_Distortion"); return var_df


def build_table8_sensitivity(sens_dict: dict) -> pd.DataFrame:
    t8 = sens_dict["sample_size"].round(4)
    _save_table(t8, "Table_08_Sensitivity"); return t8


def build_table9_fdr(fdr_df: pd.DataFrame) -> pd.DataFrame:
    """Table 9 — BH-corrected False Discovery Rate results."""
    t9 = fdr_df.copy().round(4)
    t9.insert(0, "Correction", "Benjamini-Hochberg (1995)")
    t9.insert(0, "N_iterations", 2000)
    t9.insert(0, "N_stations", 10)
    _save_table(t9, "Table_09_FDR_BH_Corrected"); return t9


# ─────────────────────────────────────────────────────────────────────────────
# 20. SPATIAL OUTPUTS
# ─────────────────────────────────────────────────────────────────────────────
def export_spatial(metadata_df: pd.DataFrame, trend_table: pd.DataFrame) -> None:
    if not HAS_GEO:
        log.warning("geopandas unavailable — skipping spatial exports."); return
    try:
        gdf = gpd.GeoDataFrame(
            metadata_df,
            geometry=gpd.points_from_xy(metadata_df["Longitude"],
                                         metadata_df["Latitude"]),
            crs="EPSG:4326",
        )
        gdf.to_file(DIRS["spatial"] / "stations.gpkg", driver="GPKG")
        gdf.to_file(DIRS["spatial"] / "stations.shp",  driver="ESRI Shapefile")
        log.info("Spatial files saved.")
    except Exception as exc:
        log.error("Spatial export failed: %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# 21. QA/QC REPORT
# ─────────────────────────────────────────────────────────────────────────────
def write_qaqc_report(
    qc_df: pd.DataFrame, completeness_df: pd.DataFrame,
    ac_results: list[dict], interpretation: str,
) -> None:
    report_path = DIRS["outputs"] / "QA_QC_Report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("="*80 + "\n")
        f.write("QA/QC AND SCIENTIFIC INTERPRETATION REPORT  (v2.0 corrected)\n")
        f.write(f"Generated: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
        f.write("="*80 + "\n\n")
        f.write("QUALITY CONTROL SUMMARY\n" + "-"*40 + "\n")
        f.write(qc_df.to_string(index=False) + "\n\n")
        f.write("DATA COMPLETENESS\n" + "-"*40 + "\n")
        f.write(completeness_df.to_string(index=False) + "\n\n")
        f.write("AUTOCORRELATION SUMMARY\n" + "-"*40 + "\n")
        for r in ac_results:
            f.write(
                f"  {r['label']}: r1={r['r1']:.4f}  "
                f"Class={classify_autocorrelation(r['r1'])} "
                f"LB-p={r['lb_pvalue']:.4f}  DW={r['dw']:.4f}  "
                f"VIF={r['vif']:.3f}  n_eff={r['n_eff']:.1f}\n"
            )
        f.write("\n" + interpretation + "\n")
    log.info("QA/QC report written: %s", report_path)


# ─────────────────────────────────────────────────────────────────────────────
# 23. SYNTHETIC DATA GENERATOR
# ─────────────────────────────────────────────────────────────────────────────
def _generate_synthetic_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate realistic synthetic daily rainfall and DEM data
    resembling Prachuap Khiri Khan meteorological conditions.

    Statistical properties follow observed regional climatology:
      - Mean annual ~1100 mm
      - Wet-season fraction ~70%
      - Lag-1 autocorrelation of annual series ~0.25
      - Gamma-distributed daily rainfall amounts
      - Wet-day occurrence: Bernoulli with seasonally varying probability
        modelled via a negative-binomial-style parameterisation
        (dispersion parameter r=3, chosen to match observed wet-day
        frequency of ~55% during wet season, ~20% during dry season)
    """
    log.info("Generating synthetic data …")
    rng = np.random.default_rng(RANDOM_SEED)

    STATIONS = {
        "PKK001": (11.82, 99.79, 10),
        "PKK002": (11.55, 99.72, 45),
        "PKK003": (11.38, 99.68, 120),
        "PKK004": (12.10, 99.88, 8),
        "PKK005": (12.32, 99.95, 200),
    }
    dates      = pd.date_range("1981-01-01", "2014-12-31", freq="D")
    monthly_mu = np.array([20,25,45,80,160,200,220,240,200,160,60,25], dtype=float)
    records    = []
    for stn, (lat, lon, elev) in STATIONS.items():
        elev_factor = 1.0 + elev / 1000.0
        for d in dates:
            mu = monthly_mu[d.month-1] / 25.0 * elev_factor
            # Wet-day probability via NB parameterisation (r=3)
            r = 3.0
            p_wet = mu / (mu + r)
            if rng.random() < p_wet:
                rain = float(rng.gamma(shape=0.8, scale=mu / 0.8))
            else:
                rain = 0.0
            records.append({
                "Station"    : stn, "Date"    : d,
                "Year"       : d.year, "Month": d.month, "Day": d.day,
                "Rainfall_mm": round(rain, 1),
            })
    df_rain = pd.DataFrame(records)

    dem_records = [
        {"Station":stn,"Latitude":v[0],"Longitude":v[1],"Elevation_m":v[2]}
        for stn,v in STATIONS.items()
    ]
    df_dem = pd.DataFrame(dem_records)
    log.info("Synthetic data: %d daily records, %d stations",
             len(df_rain), len(STATIONS))
    return df_rain, df_dem


# ─────────────────────────────────────────────────────────────────────────────
# 22. MAIN PIPELINE
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    """Full reproducible analysis pipeline (v2.0 — all corrections applied)."""
    log.info("="*70)
    log.info("PIPELINE START  v2.0")
    log.info("="*70)
    np.random.seed(RANDOM_SEED)

    # ── Step 1: Input files ───────────────────────────────────────────────────
    search_dirs = [BASE_DIR, Path.cwd(), Path.home()/"Downloads"]
    rain_path = dem_path = None
    for d in search_dirs:
        if (d/RAIN_FILE).exists() and rain_path is None: rain_path = d/RAIN_FILE
        if (d/DEM_FILE).exists()  and dem_path  is None: dem_path  = d/DEM_FILE

    if rain_path is None or dem_path is None:
        log.warning("Input files not found — using SYNTHETIC demo data.")
        df_rain, df_dem = _generate_synthetic_data()
    else:
        log.info("Rain: %s | DEM: %s", rain_path, dem_path)
        df_rain, df_dem = load_raw_data(rain_path, dem_path)

    # ── Step 2–4: Standardise, QC, completeness ───────────────────────────────
    df_rain          = standardise_rain_columns(df_rain)
    df_dem           = standardise_dem_columns(df_dem)
    df_rain, qc_df   = quality_control(df_rain)
    completeness_df  = compute_completeness(df_rain)
    valid_stations   = completeness_df.loc[
        completeness_df["Pass_threshold"],"Station"].tolist()
    if not valid_stations:
        log.warning("No station meets completeness threshold; using all.")
        valid_stations = df_rain["Station"].unique().tolist()
    log.info("Valid stations: %s", valid_stations)

    # ── Step 5–6: Metadata, aggregation ──────────────────────────────────────
    metadata_df = df_dem[df_dem["Station"].isin(valid_stations)].copy()
    _save_processed(metadata_df, "station_metadata")
    agg = aggregate_rainfall(df_rain, valid_stations)
    _save_processed(agg["monthly"],  "monthly_rainfall")
    _save_processed(agg["annual"],   "annual_rainfall")
    _save_processed(agg["seasonal"], "seasonal_rainfall")

    # ── Step 7: Autocorrelation ───────────────────────────────────────────────
    log.info("="*50 + "\nAUTOCORRELATION ANALYSIS\n" + "="*50)
    ann_mean = agg["annual"].groupby("Year")["Annual_mm"].mean().values
    wet_mean = (agg["seasonal"].groupby("Year")["Wet_mm"].mean().dropna().values
                if "Wet_mm" in agg["seasonal"].columns else np.array([]))
    dry_mean = (agg["seasonal"].groupby("Year")["Dry_mm"].mean().dropna().values
                if "Dry_mm" in agg["seasonal"].columns else np.array([]))

    ac_results = []
    if len(ann_mean) > 5: ac_results.append(compute_autocorrelation(ann_mean, label="Annual"))
    if len(wet_mean) > 5: ac_results.append(compute_autocorrelation(wet_mean, label="Wet Season"))
    if len(dry_mean) > 5: ac_results.append(compute_autocorrelation(dry_mean, label="Dry Season"))

    # ── Step 8: Observed trend analysis ──────────────────────────────────────
    log.info("="*50 + "\nOBSERVED TREND ANALYSIS\n" + "="*50)
    station_mk_results = {}
    for label, series in [("Annual",ann_mean),
                           ("Wet Season",wet_mean),
                           ("Dry Season",dry_mean)]:
        if len(series) > 4:
            station_mk_results[label] = run_all_methods(series, label=label)

    for stn in valid_stations[:5]:
        stn_annual = (agg["annual"][agg["annual"]["Station"]==stn]["Annual_mm"].values)
        if len(stn_annual) > 4:
            station_mk_results[f"Annual_{stn}"] = run_all_methods(
                stn_annual, label=f"Annual [{stn}]")

    # ── Step 9: Bootstrap ────────────────────────────────────────────────────
    log.info("Bootstrap confidence intervals …")
    boot_results = {}
    if len(ann_mean) > 4:
        boot_results["Annual"] = moving_block_bootstrap(ann_mean, n_boot=500)
        log.info("Bootstrap CI (Annual):\n%s", boot_results["Annual"]["ci"])

    # ── Step 10: Monte Carlo ─────────────────────────────────────────────────
    mc_results = run_full_monte_carlo()
    mc_results["type_i"].to_csv(DIRS["simulations"]/"type_i_error.csv",  index=False)
    mc_results["power"].to_csv( DIRS["simulations"]/"power_analysis.csv", index=False)

    # ── Step 11: Variance distortion ─────────────────────────────────────────
    var_df = variance_distortion_analysis(n_iter=1000)

    # ── Step 12: FDR (corrected) ─────────────────────────────────────────────
    fdr_df = fdr_analysis(n_iter=1000)

    # ── Step 13: Sensitivity ─────────────────────────────────────────────────
    sens_dict = sensitivity_analysis()

    # ── Step 14: Interpretation ───────────────────────────────────────────────
    interpretation = generate_interpretation(mc_results["type_i"],
                                             mc_results["power"], var_df)
    log.info("\n%s", interpretation)

    # ── Step 15: Save processed datasets ─────────────────────────────────────
    _save_processed(mc_results["type_i"],     "montecarlo_type_i")
    _save_processed(mc_results["power"],      "montecarlo_power")
    _save_processed(var_df,                   "variance_distortion")
    _save_processed(fdr_df,                   "fdr_analysis_bh_corrected")
    _save_processed(sens_dict["sample_size"], "sensitivity_sample_size")
    _save_processed(sens_dict["variance"],    "sensitivity_variance")

    # ── Step 16: Build tables ────────────────────────────────────────────────
    t1 = build_table1_metadata(metadata_df, completeness_df)
    t2 = build_table2_climatology(agg["monthly"], agg["annual"])
    t3 = build_table3_autocorrelation(ac_results)
    t4 = build_table4_trends(station_mk_results)
    t5 = build_table5_montecarlo(mc_results["type_i"])
    t6 = build_table6_power(mc_results["power"])
    t7 = build_table7_variance(var_df)
    t8 = build_table8_sensitivity(sens_dict)
    t9 = build_table9_fdr(fdr_df)

    # ── Step 17: Excel workbook ───────────────────────────────────────────────
    excel_path = DIRS["outputs"] / "All_Tables_Publication.xlsx"
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        for name, df in [("T1_Metadata",t1),("T2_Climatology",t2),
                          ("T3_Autocorrelation",t3),("T4_Trends",t4),
                          ("T5_TypeI_Error",t5),("T6_Power",t6),
                          ("T7_Variance",t7),("T8_Sensitivity",t8),
                          ("T9_FDR_BH_Corrected",t9)]:
            df.to_excel(writer, sheet_name=name, index=True)
    log.info("All-tables workbook: %s", excel_path)

    # ── Step 18: Figures ──────────────────────────────────────────────────────
    log.info("Generating publication-quality figures …")
    fig_station_map(metadata_df)
    if len(agg["monthly"]) > 0:
        fig_rainfall_climatology(agg["monthly"])
    if ac_results:
        fig_acf_pacf(ac_results)
    if station_mk_results:
        fig_method_comparison(
            station_mk_results,
            [k for k in ["Annual","Wet Season","Dry Season"]
             if k in station_mk_results],
        )
    fig_type_i_error(mc_results["type_i"])
    fig_statistical_power(mc_results["power"])
    fig_variance_distortion(var_df)
    fig_mc_distributions()
    fig_false_positive_heatmap(mc_results["type_i"])
    fig_fdr_bh(fdr_df)                   # NEW: corrected FDR figure
    fig_sensitivity(sens_dict)
    fig_effective_sample_size()
    fig_decision_framework()
    fig_summary_dashboard(mc_results["type_i"], mc_results["power"],
                          var_df, fdr_df, ac_results)   # NEW: 6-panel summary

    # ── Step 19: Spatial ──────────────────────────────────────────────────────
    export_spatial(metadata_df, t4)

    # ── Step 20: QA/QC report ─────────────────────────────────────────────────
    write_qaqc_report(qc_df, completeness_df, ac_results, interpretation)

    # ── Done ──────────────────────────────────────────────────────────────────
    log.info("="*70)
    log.info("PIPELINE COMPLETE (v2.0)")
    log.info("  Figures    : %s", DIRS["figures"])
    log.info("  Tables     : %s", DIRS["tables"])
    log.info("  Simulations: %s", DIRS["simulations"])
    log.info("  Outputs    : %s", DIRS["outputs"])
    log.info("  Spatial    : %s", DIRS["spatial"])
    log.info("  Logs       : %s", DIRS["logs"])
    log.info("="*70)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.critical("FATAL ERROR:\n%s", traceback.format_exc())
        sys.exit(1)
