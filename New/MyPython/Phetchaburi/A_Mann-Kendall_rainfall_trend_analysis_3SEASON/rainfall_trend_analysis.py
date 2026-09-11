"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Rainfall Trend Analysis — Publication Edition v1.0                         ║
║  Study Area : Phetchaburi–Prachuap Khiri Khan River Basin, Western Thailand ║
║  Period     : 1981–2014 (Daily rainfall data)                               ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Analysis Workflow (following Hamed & Rao 1998):                            ║
║  Step 1  : Data Preprocessing & Quality Control                             ║
║              – Missing value detection & linear interpolation               ║
║              – Outlier detection (IQR method)                               ║
║              – Temporal aggregation (Annual / Wet / Cool-dry / Hot)         ║
║  Step 2  : Descriptive Statistics                                           ║
║              – Mean, Max, Min, Std Dev, CV, Wet-day count                  ║
║  Step 3  : Autocorrelation (Lag-1) Assessment                               ║
║              – Determines whether Modified MK is required                   ║
║  Step 4  : Modified Mann–Kendall Trend Test (Hamed & Rao 1998)             ║
║              – Accounts for serial autocorrelation in climate data          ║
║              – Effective sample size adjustment                             ║
║              – Significance at α = 0.05 and α = 0.01                      ║
║  Step 5  : Sen's Slope Estimator (Sen 1968)                                ║
║              – Magnitude of change (mm/year)                               ║
║              – 95% confidence interval (rank-based)                        ║
║  Step 6  : Outputs (Publication-Quality Figures + Excel Tables)            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Seasons (standard Thai hydro-climatology):                                 ║
║    Wet      : May–October     (WET_MONTHS = [5,6,7,8,9,10])               ║
║    Cool-dry : November–February (COOL_DRY = [11,12,1,2])                  ║
║    Hot      : March–April     (HOT_MONTHS = [3,4])                        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Output files (prefix = Output_MK_<basename>_):                            ║
║    Fig1_TimeSeries_Annual.png/.pdf                                          ║
║    Fig2_TimeSeries_Seasonal.png/.pdf                                        ║
║    Fig3_SenSlope_Summary.png/.pdf                                           ║
║    Fig4_Significance_Map.png/.pdf                                           ║
║    Fig5_Autocorrelation.png/.pdf                                            ║
║    Fig6_Descriptive_Heatmap.png/.pdf                                        ║
║    Results_MannKendall.xlsx   (5 sheets)                                   ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  References:                                                                ║
║    Mann (1945) Econometrica 13:245–259                                      ║
║    Kendall (1975) Rank Correlation Methods. Griffin, London.               ║
║    Sen (1968) JASA 63:1379–1389          [Sen's Slope]                     ║
║    Hamed & Rao (1998) J. Hydrol. 204:182–196  [Modified MK]               ║
║    Gilbert (1987) Statistical Methods for Environmental Pollution          ║
║    Yue & Wang (2004) Water Resour. Res. 40:W08307                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import math
import warnings
import itertools
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats as sps
from scipy.stats import norm as scipy_norm

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.ticker as ticker
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
from matplotlib.lines import Line2D
import matplotlib.cm as cm

from openpyxl import Workbook
from openpyxl.styles import (PatternFill, Font, Alignment,
                              Border, Side)
from openpyxl.utils import get_column_letter

warnings.filterwarnings("ignore")

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §0  GLOBAL CONSTANTS & PUBLICATION STYLE                               ║
# ╚══════════════════════════════════════════════════════════════════════════╝

# Temporal scales
WET_MONTHS   = [5, 6, 7, 8, 9, 10]     # May–October (monsoon)
COOL_DRY     = [11, 12, 1, 2]          # November–February
HOT_MONTHS   = [3, 4]                  # March–April
WET_THR      = 1.0                     # WMO wet-day threshold (mm/day)

# Statistical thresholds
ALPHA_005 = 0.05
ALPHA_001 = 0.01
Z_005     = 1.9600    # two-tailed
Z_001     = 2.5758

# Output settings
SAVE_PDF  = True
DPI       = 600
MIN_N     = 10        # minimum years for trend analysis

MONTH_ABBR = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]

# Colour palette (colour-blind safe)
C = dict(
    obs    = "#1B2838",   obs_lt = "#B0BEC5",
    wet    = "#1565C0",   wet_lt = "#BBDEFB",
    dry    = "#2E7D32",   dry_lt = "#C8E6C9",
    hot    = "#E65100",   hot_lt = "#FFE0B2",
    inc    = "#1B5E20",   dec    = "#B71C1C",
    ns_col = "#78909C",
    gold   = "#F57F17",   purple = "#6A1B9A",
    green  = "#2E7D32",   grey   = "#607D8B",
)

# Publication-grade matplotlib style
plt.rcParams.update({
    "font.family":        "serif",
    "font.serif":         ["Times New Roman", "DejaVu Serif"],
    "font.size":          12,
    "axes.titlesize":     13,
    "axes.labelsize":     12,
    "xtick.labelsize":    11,
    "ytick.labelsize":    11,
    "legend.fontsize":    10.5,
    "figure.titlesize":   13,
    "lines.linewidth":    2.0,
    "axes.linewidth":     1.0,
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.grid":          True,
    "grid.linestyle":     "--",
    "grid.linewidth":     0.4,
    "grid.alpha":         0.40,
    "grid.color":         "#B0BEC5",
    "savefig.dpi":        DPI,
    "savefig.bbox":       "tight",
    "savefig.pad_inches": 0.15,
    "figure.dpi":         100,
    "mathtext.fontset":   "stix",
    "pdf.fonttype":       42,
    "ps.fonttype":        42,
})

# Excel helpers
THIN = Side(style="thin",   color="BDBDBD")
MED  = Side(style="medium", color="1F4E79")
XC   = dict(
    title  = "13293D", sub    = "1F4E79", hdr    = "2E75B6",
    inc_c  = "E8F5E9", dec_c  = "FFEBEE", ns_c   = "F5F5F5",
    sig05  = "FFF9C4", sig01  = "FFECB3",
    white  = "FFFFFF", alt    = "F0F4F8",
    wet_h  = "DDEEFF", dry_h  = "DFF0D8", hot_h  = "FFF3CD",
)


def tb():  return Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
def xfill(h): return PatternFill("solid", fgColor=h)


def xsc(ws, r, c, val=None, bold=False, italic=False,
        fc=None, bg=None, align="center", sz=10,
        wrap=True, border=None, num_fmt=None):
    cell = ws.cell(row=r, column=c)
    if val is not None: cell.value = val
    cell.font      = Font(bold=bold, italic=italic, name="Calibri",
                          size=sz, color=fc if fc else "1A1A1A")
    cell.alignment = Alignment(horizontal=align, vertical="center",
                                wrap_text=wrap)
    if bg:      cell.fill   = xfill(bg)
    if border:  cell.border = border
    if num_fmt: cell.number_format = num_fmt
    return cell


def mxsc(ws, r, c1, c2, val, **kw):
    ws.merge_cells(start_row=r, start_column=c1,
                   end_row=r,   end_column=c2)
    return xsc(ws, r, c1, val, **kw)


def cw(ws, col, w):
    ws.column_dimensions[get_column_letter(col)].width = w


def savefig(fig, path_noext: str):
    """Save PNG (600 DPI) + vector PDF."""
    fig.savefig(f"{path_noext}.png", dpi=DPI,
                bbox_inches="tight", pad_inches=0.15)
    if SAVE_PDF:
        fig.savefig(f"{path_noext}.pdf",
                    bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    n = Path(path_noext).name
    print(f"    ✓  {n}.png" + (" + .pdf" if SAVE_PDF else ""))


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §1  DATA LOADING & PREPROCESSING                                       ║
# ╚══════════════════════════════════════════════════════════════════════════╝

MISS_FLAGS = [-99, -999, -9999, -9.99e+20, 9.99e+20, 1e+20]


def find_csv(folder: str):
    """Auto-discover the observed daily rainfall CSV in the folder."""
    csvs = sorted(Path(folder).glob("*.csv"))
    obs  = [f for f in csvs if "observed" in f.name.lower()
            or "rain" in f.name.lower()]
    if not obs:
        obs = csvs   # fallback: any CSV
    if not obs:
        sys.exit(f"  ✗  No CSV file found in {folder}")
    return str(obs[0])


def load_daily(path: str) -> pd.DataFrame:
    """
    Load daily rainfall CSV.
    Expected columns: YEAR, MONTH, DAY, <StationID1>, <StationID2>, ...
    Returns DataFrame indexed by DatetimeIndex.
    """
    df = pd.read_csv(path)
    # Normalise missing flags
    for mv in MISS_FLAGS:
        df.replace(mv, np.nan, inplace=True)
    # Normalise column names to str
    df.columns = [str(c) for c in df.columns]
    stns = [c for c in df.columns if c not in ("YEAR","MONTH","DAY")]
    # Set negative values to NaN (rainfall cannot be negative)
    for s in stns:
        df.loc[df[s] < 0, s] = np.nan
    # Build DatetimeIndex
    df["date"] = pd.to_datetime(
        {"year": df["YEAR"], "month": df["MONTH"], "day": df["DAY"]})
    df = df.set_index("date")[stns]
    return df


def quality_control(df: pd.DataFrame) -> tuple:
    """
    Quality Control (Step 2 in workflow):
      (a) Report missing values per station.
      (b) Detect outliers using IQR method (flag, do NOT remove).
      (c) Fill short gaps (≤5 consecutive days) by linear interpolation.
    Returns: (df_clean, qc_report_dict)
    """
    stns = df.columns.tolist()
    qc   = {}

    for s in stns:
        series = df[s].copy()
        n_total   = len(series)
        n_missing = int(series.isna().sum())

        # Outlier detection: IQR method (Tukey's fence)
        wet  = series[(series >= WET_THR) & series.notna()]
        q1, q3 = float(wet.quantile(0.25)), float(wet.quantile(0.75))
        iqr    = q3 - q1
        upper_fence = q3 + 3.0 * iqr    # 3×IQR for extreme outliers
        n_outlier = int((series > upper_fence).sum())

        # Fill short gaps (≤5 consecutive NaN) by linear interpolation
        series_filled = series.interpolate(
            method="time", limit=5, limit_direction="both")
        n_filled = int(series_filled.notna().sum()) - int(series.notna().sum())

        df[s] = series_filled
        qc[s] = {
            "n_total":    n_total,
            "n_missing":  n_missing,
            "pct_miss":   round(n_missing / n_total * 100, 2),
            "n_outlier":  n_outlier,
            "upper_fence":round(upper_fence, 1),
            "n_filled":   n_filled,
        }

    return df, qc


def aggregate_temporal(df: pd.DataFrame) -> dict:
    """
    Aggregate daily data into 4 temporal scales:
      'annual'   : calendar-year total
      'wet'      : May–October total per year
      'cool_dry' : November–February total per year
                   (shifted: Nov-Dec of year Y → grouped with year Y+1)
      'hot'      : March–April total per year

    Returns dict of {scale: DataFrame(year × station)}.
    Min-count = 80% of expected days in period.
    """
    scales = {}

    # Annual
    scales["annual"] = df.resample("YS").apply(
        lambda g: g.sum(min_count=int(0.8 * len(g))))

    # Wet season (May–Oct)
    sub_wet = df[df.index.month.isin(WET_MONTHS)]
    scales["wet"] = sub_wet.resample("YS").apply(
        lambda g: g.sum(min_count=int(0.8 * len(g))))

    # Cool-dry season: Nov–Feb spans two calendar years
    # Shift Nov-Dec to next year so they group with Jan-Feb
    df_cd = df[df.index.month.isin(COOL_DRY)].copy()
    # Advance Nov-Dec dates by 1 year
    mask_late = df_cd.index.month.isin([11, 12])
    new_idx = df_cd.index.to_list()
    new_idx = [d.replace(year=d.year + 1) if m else d
               for d, m in zip(new_idx, mask_late)]
    df_cd.index = pd.DatetimeIndex(new_idx)
    scales["cool_dry"] = df_cd.resample("YS").apply(
        lambda g: g.sum(min_count=int(0.8 * len(g))))

    # Hot season (Mar–Apr)
    sub_hot = df[df.index.month.isin(HOT_MONTHS)]
    scales["hot"] = sub_hot.resample("YS").apply(
        lambda g: g.sum(min_count=int(0.8 * len(g))))

    return scales


def descriptive_stats(df: pd.DataFrame, df_daily: pd.DataFrame) -> pd.DataFrame:
    """
    Compute descriptive statistics per station (Step 3):
      Mean, Max, Min, Std, CV (%), Wet-day count (annual mean),
      Skewness, Kurtosis.
    df      : annual total DataFrame (year × station)
    df_daily: daily DataFrame for wet-day computation
    """
    stns = df.columns.tolist()
    rows = []
    for s in stns:
        ann_vals = df[s].dropna().values.astype(float)
        daily_s  = df_daily[s].dropna()
        wet_days = daily_s[daily_s >= WET_THR]
        n_years  = len(ann_vals)

        rows.append({
            "Station":   s,
            "N_years":   n_years,
            "Mean (mm)": round(float(np.mean(ann_vals)), 1) if n_years > 0 else np.nan,
            "Max (mm)":  round(float(np.max(ann_vals)),  1) if n_years > 0 else np.nan,
            "Min (mm)":  round(float(np.min(ann_vals)),  1) if n_years > 0 else np.nan,
            "Std (mm)":  round(float(np.std(ann_vals, ddof=1)), 1) if n_years > 1 else np.nan,
            "CV (%)":    round(float(np.std(ann_vals, ddof=1) /
                                     np.mean(ann_vals) * 100), 1)
                         if n_years > 1 and np.mean(ann_vals) != 0 else np.nan,
            "Wet-days/yr": round(float(len(wet_days) / n_years), 1) if n_years > 0 else np.nan,
            "Skewness":  round(float(sps.skew(ann_vals)), 3) if n_years > 3 else np.nan,
            "Kurtosis":  round(float(sps.kurtosis(ann_vals, fisher=True)), 3)
                         if n_years > 3 else np.nan,
        })
    return pd.DataFrame(rows).set_index("Station")


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §2  AUTOCORRELATION (Lag-k)                                            ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def autocorrelation_lag1(x: np.ndarray) -> float:
    """
    Compute Lag-1 autocorrelation coefficient.
    Formula (Pearson):
       r₁ = Σ_{i=1}^{n-1} (xᵢ − x̄)(xᵢ₊₁ − x̄) / Σ_{i=1}^{n} (xᵢ − x̄)²
    """
    x = np.asarray(x, dtype=float)
    mask = ~np.isnan(x)
    x = x[mask]
    n = len(x)
    if n < 4:
        return np.nan
    xbar = np.mean(x)
    num  = np.sum((x[:n-1] - xbar) * (x[1:n] - xbar))
    den  = np.sum((x - xbar) ** 2)
    return float(num / den) if den > 0 else np.nan


def autocorrelations_all_lags(x: np.ndarray, max_lag: int = None) -> np.ndarray:
    """
    Compute autocorrelation for lags 1..max_lag.
    Used in Modified MK to compute effective sample size.
    Default max_lag = n//3 (Hamed & Rao 1998 recommendation).
    """
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 4:
        return np.array([])
    if max_lag is None:
        max_lag = min(n // 3, n - 1)
    xbar = np.mean(x)
    den  = np.sum((x - xbar) ** 2)
    rho  = np.zeros(max_lag)
    for k in range(1, max_lag + 1):
        num = np.sum((x[:n-k] - xbar) * (x[k:n] - xbar))
        rho[k-1] = float(num / den) if den > 0 else 0.0
    return rho


def is_significant_autocorr(r1: float, n: int,
                              alpha: float = 0.05) -> bool:
    """
    Two-tailed significance test for Lag-1 autocorrelation.
    Critical value ≈ ±z_{α/2} / √n (Pearson approximation).
    """
    if np.isnan(r1) or n < 4:
        return False
    z_crit = scipy_norm.ppf(1 - alpha / 2)
    se     = 1.0 / math.sqrt(n)
    return abs(r1) > z_crit * se


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §3  MODIFIED MANN–KENDALL TEST (Hamed & Rao 1998)                     ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def mk_s_statistic(x: np.ndarray) -> tuple:
    """
    Compute Mann-Kendall S statistic and tie counts.

    S = Σ_{i=1}^{n-1} Σ_{j=i+1}^{n} sgn(xⱼ − xᵢ)
    sgn(δ) = +1 if δ>0, 0 if δ=0, -1 if δ<0

    Returns: (S, tie_groups)  where tie_groups = list of group sizes
    """
    x = np.asarray(x, dtype=float)
    mask = ~np.isnan(x)
    x    = x[mask]
    n    = len(x)
    if n < 4:
        return np.nan, []

    # Vectorised S computation
    S = 0
    for i in range(n - 1):
        diff = x[i+1:] - x[i]
        S   += int(np.sum(np.sign(diff)))

    # Tie groups (for variance correction)
    _, counts = np.unique(x, return_counts=True)
    ties = counts[counts > 1].tolist()
    return float(S), ties


def mk_variance_ties(n: int, ties: list) -> float:
    """
    Variance of S with tie correction (standard Mann-Kendall).

    Var(S) = [n(n-1)(2n+5) − Σ_t tₚ(tₚ−1)(2tₚ+5)] / 18

    where tₚ is the size of the p-th tied group.
    """
    tie_sum = sum(t * (t - 1) * (2 * t + 5) for t in ties)
    return (n * (n - 1) * (2 * n + 5) - tie_sum) / 18.0


def modified_mk(x: np.ndarray,
                alpha_level: float = ALPHA_005,
                max_lag: int = None) -> dict:
    """
    Modified Mann–Kendall Trend Test (Hamed & Rao 1998).

    Corrects for serial autocorrelation by adjusting Var(S):
       Var*(S) = Var(S) × (n / n*)
    where n* (effective sample size) is:
       n / n* = 1 + 2 Σ_{k=1}^{n-1} (1 − k/n) ρ_k

    Parameters
    ----------
    x          : 1-D array of annual totals (chronological order)
    alpha_level: significance level for this call
    max_lag    : max autocorrelation lag (default n//3)

    Returns
    -------
    dict with keys:
        S, n, Var_S, Var_S_adj, n_eff, rho_1,
        Z, p_value, trend, slope_Q, slope_lo, slope_hi,
        sig_05, sig_01, significant
    """
    null = {k: np.nan for k in
            ["S","n","Var_S","Var_S_adj","n_eff","rho_1",
             "Z","p_value","trend","slope_Q","slope_lo","slope_hi",
             "sig_05","sig_01","significant"]}
    null["trend"] = "No trend"
    null["sig_05"] = False
    null["sig_01"] = False
    null["significant"] = False

    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < MIN_N:
        return null

    # ── Step 1: Compute S and tie groups ────────────────────────────────
    S, ties = mk_s_statistic(x)
    if np.isnan(S):
        return null

    # ── Step 2: Variance with tie correction ─────────────────────────────
    Var_S = mk_variance_ties(n, ties)
    if Var_S <= 0:
        return null

    # ── Step 3: Autocorrelation of RANKED data (Hamed & Rao 1998) ────────
    # Hamed & Rao use autocorrelations of the ranked series
    ranks = sps.rankdata(x).astype(float)
    rho   = autocorrelations_all_lags(ranks, max_lag=max_lag)

    # Compute n* (effective sample size correction factor)
    # n/n* = 1 + (2/n) Σ_{k=1}^{n-1} (n-k) ρ_k
    if len(rho) == 0:
        n_over_neff = 1.0
    else:
        max_k = len(rho)
        ks    = np.arange(1, max_k + 1)
        # Only use statistically significant autocorrelations (Hamed & Rao 1998)
        se_rho = 1.0 / math.sqrt(n)
        z_crit_rho = scipy_norm.ppf(1 - ALPHA_005 / 2)
        sig_mask = np.abs(rho) > z_crit_rho * se_rho
        rho_use  = np.where(sig_mask, rho, 0.0)
        n_over_neff = 1.0 + (2.0 / n) * np.sum((n - ks) * rho_use)
        n_over_neff = max(n_over_neff, 1.0)   # n* ≤ n always

    rho_1   = float(rho[0]) if len(rho) > 0 else np.nan
    n_eff   = n / n_over_neff
    # ── Step 4: Adjusted variance ─────────────────────────────────────────
    Var_S_adj = Var_S * n_over_neff   # = Var(S) × (n / n*)

    # ── Step 5: Z statistic ───────────────────────────────────────────────
    if S > 0:
        Z = (S - 1) / math.sqrt(Var_S_adj)
    elif S < 0:
        Z = (S + 1) / math.sqrt(Var_S_adj)
    else:
        Z = 0.0

    # Two-tailed p-value
    p_val = 2.0 * (1.0 - scipy_norm.cdf(abs(Z)))
    p_val = float(min(p_val, 1.0))

    # ── Step 6: Trend direction ───────────────────────────────────────────
    sig_05 = p_val < ALPHA_005
    sig_01 = p_val < ALPHA_001

    if sig_05:
        trend = "Increasing ↑" if Z > 0 else "Decreasing ↓"
    else:
        trend = "No trend"

    # ── Step 7: Sen's Slope ───────────────────────────────────────────────
    slope_Q, slope_lo, slope_hi = sens_slope(x)

    return {
        "S":           float(S),
        "n":           int(n),
        "Var_S":       round(float(Var_S),      2),
        "Var_S_adj":   round(float(Var_S_adj),  2),
        "n_eff":       round(float(n_eff),       2),
        "rho_1":       round(float(rho_1),       4) if not np.isnan(rho_1) else np.nan,
        "Z":           round(float(Z),           4),
        "p_value":     round(float(p_val),       6),
        "trend":       trend,
        "slope_Q":     round(float(slope_Q),     3) if not np.isnan(slope_Q) else np.nan,
        "slope_lo":    round(float(slope_lo),    3) if not np.isnan(slope_lo) else np.nan,
        "slope_hi":    round(float(slope_hi),    3) if not np.isnan(slope_hi) else np.nan,
        "sig_05":      sig_05,
        "sig_01":      sig_01,
        "significant": sig_05,
    }


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §4  SEN'S SLOPE ESTIMATOR (Sen 1968) + 95% CI                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def sens_slope(x: np.ndarray, alpha: float = 0.05) -> tuple:
    """
    Sen's Slope Estimator with rank-based 95% confidence interval.

    Slope: Q = median(Qᵢ)  where Qᵢ = (xⱼ − xᵢ) / (j − i), ∀ j > i

    Confidence interval (Gilbert 1987):
      C_α = z_{α/2} × √Var(S)
      Lower rank = (N − C_α) / 2
      Upper rank = (N + C_α) / 2 + 1
      (N = number of slope estimates)

    Returns: (slope, ci_lower, ci_upper)  [mm/year]
    """
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 4:
        return np.nan, np.nan, np.nan

    # Compute all pairwise slopes
    slopes = []
    for i in range(n - 1):
        for j in range(i + 1, n):
            slopes.append((x[j] - x[i]) / (j - i))
    slopes = np.array(sorted(slopes))
    N_slopes = len(slopes)

    slope_med = float(np.median(slopes))

    # 95% CI (rank-based, Gilbert 1987)
    _, ties = mk_s_statistic(x)
    Var_S   = mk_variance_ties(n, ties)
    if Var_S <= 0:
        return slope_med, np.nan, np.nan

    z_crit   = scipy_norm.ppf(1 - alpha / 2)
    C_alpha  = z_crit * math.sqrt(Var_S)
    lo_rank  = int(round((N_slopes - C_alpha) / 2.0))
    hi_rank  = int(round((N_slopes + C_alpha) / 2.0)) + 1

    lo_rank = max(0,          lo_rank)
    hi_rank = min(N_slopes-1, hi_rank)

    ci_lo = float(slopes[lo_rank])
    ci_hi = float(slopes[hi_rank])

    return slope_med, ci_lo, ci_hi


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §5  RUN ALL STATIONS × ALL TEMPORAL SCALES                             ║
# ╚══════════════════════════════════════════════════════════════════════════╝

SCALE_META = {
    "annual":   {"label": "Annual",   "unit": "mm yr⁻¹",   "color": C["obs"],
                 "months_desc": "January–December"},
    "wet":      {"label": "Wet Season",     "unit": "mm season⁻¹", "color": C["wet"],
                 "months_desc": "May–October"},
    "cool_dry": {"label": "Cool-Dry Season","unit": "mm season⁻¹", "color": C["dry"],
                 "months_desc": "November–February"},
    "hot":      {"label": "Hot Season",     "unit": "mm season⁻¹", "color": C["hot"],
                 "months_desc": "March–April"},
}


def run_trend_analysis(scales: dict, stns: list, smap: dict) -> pd.DataFrame:
    """
    Run Modified MK + Sen's Slope for all stations × all temporal scales.
    Returns a tidy DataFrame with one row per (station × scale).
    """
    rows = []
    for scale_key, df_scale in scales.items():
        meta = SCALE_META[scale_key]
        for stn in stns:
            stn = str(stn)
            if stn not in df_scale.columns:
                continue
            arr = df_scale[stn].dropna().values.astype(float)
            res = modified_mk(arr)
            rows.append({
                "Station":    stn,
                "Code":       smap.get(stn, stn),
                "Scale":      scale_key,
                "Scale_Label":meta["label"],
                "N_years":    res["n"],
                "S":          res["S"],
                "Var_S":      res["Var_S"],
                "Var_S_adj":  res["Var_S_adj"],
                "n_eff":      res["n_eff"],
                "rho_1":      res["rho_1"],
                "Z":          res["Z"],
                "p_value":    res["p_value"],
                "Trend":      res["trend"],
                "sig_05":     res["sig_05"],
                "sig_01":     res["sig_01"],
                "Slope_Q (mm/yr)":   res["slope_Q"],
                "Slope_CI_lo":       res["slope_lo"],
                "Slope_CI_hi":       res["slope_hi"],
            })
    return pd.DataFrame(rows)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §6  FIGURE 1 — Annual Rainfall Time Series (all stations)              ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def fig1_annual_timeseries(scales: dict, trend_df: pd.DataFrame,
                            stns: list, smap: dict,
                            period: str, out_dir: Path, prefix: str):
    """
    Figure 1: Annual rainfall time series per station.
    Overlaid: Sen's slope trend line + 95% CI band.
    Colour coding: significant trend = blue/red; ns = grey.
    """
    df_ann = scales["annual"]
    n_s    = len(stns)
    ncols  = min(4, n_s)
    nrows  = math.ceil(n_s / ncols)

    fig, axes = plt.subplots(nrows, ncols,
                             figsize=(5.5 * ncols, 4.0 * nrows),
                             squeeze=False)
    fig.subplots_adjust(hspace=0.50, wspace=0.30,
                        top=0.93, bottom=0.07,
                        left=0.06, right=0.97)

    for si, stn in enumerate(stns):
        stn  = str(stn)
        row  = si // ncols
        col  = si % ncols
        ax   = axes[row][col]

        series = df_ann[stn].dropna() if stn in df_ann.columns else None
        if series is None or len(series) < 4:
            ax.set_visible(False); continue

        yrs  = series.index.year.values.astype(float)
        vals = series.values.astype(float)

        # Retrieve trend results
        sub   = trend_df[(trend_df["Station"] == stn) &
                         (trend_df["Scale"] == "annual")]
        sig05 = bool(sub["sig_05"].values[0]) if len(sub) else False
        sig01 = bool(sub["sig_01"].values[0]) if len(sub) else False
        slope = float(sub["Slope_Q (mm/yr)"].values[0]) if len(sub) else np.nan
        lo    = float(sub["Slope_CI_lo"].values[0]) if len(sub) else np.nan
        hi    = float(sub["Slope_CI_hi"].values[0]) if len(sub) else np.nan
        trend_lbl = str(sub["Trend"].values[0]) if len(sub) else ""

        # Bar colour
        bar_col = (C["inc"]  if ("↑" in trend_lbl and sig05) else
                   C["dec"]  if ("↓" in trend_lbl and sig05) else
                   C["ns_col"])

        ax.bar(yrs, vals, width=0.75, color=bar_col, alpha=0.55,
               edgecolor="none", zorder=2)
        ax.plot(yrs, vals, color=bar_col, lw=1.4, alpha=0.85, zorder=3)

        # Sen's slope trend line
        if not np.isnan(slope):
            # Anchored at median
            y_bar = np.nanmedian(vals)
            x_bar = np.median(yrs)
            trend_line = slope * (yrs - x_bar) + y_bar
            ax.plot(yrs, trend_line, color="black", lw=2.2, ls="-",
                    zorder=5, label=f"Sen's β = {slope:+.1f} mm yr⁻¹")
            # 95% CI band
            if not (np.isnan(lo) or np.isnan(hi)):
                lo_line = lo * (yrs - x_bar) + y_bar
                hi_line = hi * (yrs - x_bar) + y_bar
                ax.fill_between(yrs, lo_line, hi_line,
                                color="grey", alpha=0.20, zorder=4,
                                label="95% CI")

        # Annotations
        sig_str = ("**" if sig01 else "*" if sig05 else "ns")
        code    = smap.get(stn, stn)
        z_val   = float(sub["Z"].values[0]) if len(sub) else np.nan
        p_val   = float(sub["p_value"].values[0]) if len(sub) else np.nan
        ax.set_title(
            f"({chr(97+si)})  {code}  [{stn}]\n"
            f"Z = {z_val:.2f}  p = {p_val:.4f}  {sig_str}",
            loc="left", fontsize=10.5, fontweight="bold", pad=4)
        ax.set_ylabel("mm yr⁻¹", fontsize=10)
        ax.set_xlabel("Year",    fontsize=10)
        ax.set_ylim(bottom=0)
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.legend(fontsize=8.5, frameon=True, edgecolor="#B0BEC5",
                  loc="upper right", handlelength=1.8)

    # Hide unused panels
    for si in range(len(stns), nrows * ncols):
        axes[si // ncols][si % ncols].set_visible(False)

    # Legend for colour meaning
    hand = [
        mpatches.Patch(color=C["inc"],    label="Increasing trend (sig.)"),
        mpatches.Patch(color=C["dec"],    label="Decreasing trend (sig.)"),
        mpatches.Patch(color=C["ns_col"], label="No significant trend"),
        Line2D([0],[0], color="black",   lw=2.2, label="Sen's slope"),
        mpatches.Patch(color="grey", alpha=0.35, label="95% CI of slope"),
    ]
    fig.legend(handles=hand, loc="lower center", ncol=5, fontsize=10,
               frameon=True, edgecolor="#B0BEC5",
               bbox_to_anchor=(0.5, 0.005))

    fig.suptitle(
        f"Figure 1.  Annual Rainfall Time Series and Sen's Slope Trend — {period}\n"
        "Modified Mann–Kendall Test  |  * p<0.05  ** p<0.01  ns: not significant",
        fontsize=12, fontweight="bold")

    savefig(fig, str(out_dir / f"{prefix}_Fig1_TimeSeries_Annual"))


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §7  FIGURE 2 — Seasonal Time Series (all scales, regional mean)        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def fig2_seasonal_timeseries(scales: dict, trend_df: pd.DataFrame,
                              stns: list, period: str,
                              out_dir: Path, prefix: str):
    """
    Figure 2: Regional-mean time series for all 4 temporal scales.
    4 panels (Annual, Wet, Cool-dry, Hot) in a 2×2 grid.
    Overlaid Sen's slope trend line + 95% CI from regional-mean trend.
    """
    stns = [str(s) for s in stns]
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.subplots_adjust(hspace=0.45, wspace=0.30,
                        top=0.92, bottom=0.09,
                        left=0.07, right=0.97)

    scale_order = ["annual","wet","cool_dry","hot"]
    panels      = ["(a)","(b)","(c)","(d)"]

    for pi, (sk, panel) in enumerate(zip(scale_order, panels)):
        ax   = axes[pi // 2][pi % 2]
        meta = SCALE_META[sk]
        df_s = scales[sk]

        # Regional mean across all stations
        cols    = [s for s in stns if s in df_s.columns]
        reg     = df_s[cols].mean(axis=1).dropna()
        if len(reg) < 4:
            ax.set_visible(False); continue

        yrs  = reg.index.year.values.astype(float)
        vals = reg.values.astype(float)

        # Run MK on regional mean
        res  = modified_mk(vals)
        slope= res["slope_Q"]
        lo   = res["slope_lo"]
        hi   = res["slope_hi"]
        sig05= res["sig_05"]
        sig01= res["sig_01"]
        Z    = res["Z"]
        p    = res["p_value"]

        col_line = (C["inc"] if (sig05 and Z > 0) else
                    C["dec"] if (sig05 and Z < 0) else
                    meta["color"])

        ax.fill_between(yrs, vals, alpha=0.25, color=meta["color"], zorder=2)
        ax.plot(yrs, vals, color=meta["color"], lw=2.0, alpha=0.90, zorder=3,
                label=f"Regional Mean ({meta['months_desc']})")

        if not np.isnan(slope):
            y_bar = np.nanmedian(vals)
            x_bar = np.median(yrs)
            tl = slope * (yrs - x_bar) + y_bar
            ax.plot(yrs, tl, color="black", lw=2.2, ls="-", zorder=5,
                    label=f"Sen's β = {slope:+.1f} {meta['unit'].split('⁻')[0]}/yr")
            if not (np.isnan(lo) or np.isnan(hi)):
                ll = lo * (yrs - x_bar) + y_bar
                hl = hi * (yrs - x_bar) + y_bar
                ax.fill_between(yrs, ll, hl, color="grey",
                                alpha=0.22, zorder=4, label="95% CI")

        sig_str = ("** p<0.01" if sig01 else "* p<0.05" if sig05 else "ns")
        ax.set_title(
            f"{panel}  {meta['label']} ({meta['months_desc']})\n"
            f"Z = {Z:.3f}  |  p = {p:.4f}  |  {sig_str}",
            loc="left", fontsize=12, fontweight="bold", pad=5)
        ax.set_ylabel(meta["unit"], fontsize=11)
        ax.set_xlabel("Year",       fontsize=11)
        ax.set_ylim(bottom=0)
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.legend(fontsize=9.5, frameon=True, edgecolor="#B0BEC5",
                  loc="upper right", handlelength=1.8)

    fig.suptitle(
        f"Figure 2.  Seasonal Rainfall Time Series and Trend — {period}\n"
        "Regional mean across all stations  |  "
        "Modified Mann–Kendall Test + Sen's Slope",
        fontsize=12, fontweight="bold")

    savefig(fig, str(out_dir / f"{prefix}_Fig2_TimeSeries_Seasonal"))


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §8  FIGURE 3 — Sen's Slope Summary (bar chart with CI)                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def fig3_sens_slope_summary(trend_df: pd.DataFrame, stns: list,
                             smap: dict, period: str,
                             out_dir: Path, prefix: str):
    """
    Figure 3: Sen's slope (mm/yr) per station × temporal scale.
    Bar chart with error bars (95% CI).
    Colour coding: sig. increasing = blue, sig. decreasing = red, ns = grey.
    """
    stns   = [str(s) for s in stns]
    codes  = [smap.get(s, s) for s in stns]
    scales = ["annual","wet","cool_dry","hot"]
    meta   = SCALE_META
    n_s    = len(stns)
    n_sc   = len(scales)

    fig, axes = plt.subplots(n_sc, 1, figsize=(max(14, n_s*1.1+4), 14),
                             sharex=True)
    fig.subplots_adjust(hspace=0.40, top=0.93, bottom=0.09,
                        left=0.07, right=0.97)

    x = np.arange(n_s)

    for pi, (sk, ax) in enumerate(zip(scales, axes)):
        m = meta[sk]
        slopes = []; lo_errs = []; hi_errs = []
        colors = []

        for stn in stns:
            sub = trend_df[(trend_df["Station"]==stn) &
                           (trend_df["Scale"]==sk)]
            if len(sub) == 0:
                slopes.append(np.nan)
                lo_errs.append(0)
                hi_errs.append(0)
                colors.append(C["ns_col"])
                continue
            sl  = float(sub["Slope_Q (mm/yr)"].values[0])
            lo  = float(sub["Slope_CI_lo"].values[0])
            hi  = float(sub["Slope_CI_hi"].values[0])
            s05 = bool(sub["sig_05"].values[0])
            Z   = float(sub["Z"].values[0])
            slopes.append(sl)
            # Error bar = distance from slope to CI bound
            lo_errs.append(abs(sl - lo) if not np.isnan(lo) else 0)
            hi_errs.append(abs(hi - sl) if not np.isnan(hi) else 0)
            colors.append(C["inc"] if (s05 and Z>0) else
                          C["dec"] if (s05 and Z<0) else
                          C["ns_col"])

        slopes_arr = np.array(slopes, dtype=float)
        lo_arr     = np.array(lo_errs, dtype=float)
        hi_arr     = np.array(hi_errs, dtype=float)

        # Bars with error bars
        for xi, (sl, lo_e, hi_e, col) in enumerate(
                zip(slopes_arr, lo_arr, hi_arr, colors)):
            if np.isnan(sl): continue
            ax.bar(xi, sl, width=0.65, color=col, alpha=0.80,
                   edgecolor="white", linewidth=0.5, zorder=3)
            ax.errorbar(xi, sl, yerr=[[lo_e],[hi_e]],
                        fmt="none", color="black",
                        capsize=5, capthick=1.5, lw=1.5, zorder=5)

        # Value labels on bars
        for xi, sl in enumerate(slopes_arr):
            if np.isnan(sl): continue
            y_off = 0.5 if sl >= 0 else -1.2
            ax.text(xi, sl + y_off, f"{sl:+.1f}",
                    ha="center", va="bottom" if sl >= 0 else "top",
                    fontsize=8.5, fontweight="bold", color="black")

        # Significance markers
        for xi, stn in enumerate(stns):
            sub = trend_df[(trend_df["Station"]==stn) &
                           (trend_df["Scale"]==sk)]
            if len(sub) == 0: continue
            s01 = bool(sub["sig_01"].values[0])
            s05 = bool(sub["sig_05"].values[0])
            sl  = float(sub["Slope_Q (mm/yr)"].values[0])
            if np.isnan(sl): continue
            sig_str = "**" if s01 else ("*" if s05 else "")
            if sig_str:
                y_star = sl + (1.5 if sl>=0 else -2.5)
                ax.text(xi, y_star, sig_str,
                        ha="center", fontsize=11,
                        fontweight="bold", color="black", zorder=6)

        ax.axhline(0, color="black", lw=0.9, ls="--", alpha=0.55)
        ax.set_ylabel(f"β (mm yr⁻¹)\n{m['label']}", fontsize=11)
        ax.set_title(
            f"({chr(97+pi)})  {m['label']} ({m['months_desc']})  — Sen's Slope",
            loc="left", fontsize=12, fontweight="bold", pad=4)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())

    axes[-1].set_xticks(x)
    axes[-1].set_xticklabels(codes, rotation=0, ha="center", fontsize=11)
    axes[-1].set_xlabel("Station", fontsize=12, labelpad=5)

    hand = [
        mpatches.Patch(color=C["inc"],    label="Increasing (p<0.05)"),
        mpatches.Patch(color=C["dec"],    label="Decreasing (p<0.05)"),
        mpatches.Patch(color=C["ns_col"], label="Not significant"),
        Line2D([0],[0], color="black", lw=1.8, marker="|",
               ms=8, label="95% CI"),
    ]
    fig.legend(handles=hand, loc="lower center", ncol=4, fontsize=10.5,
               frameon=True, edgecolor="#B0BEC5",
               bbox_to_anchor=(0.5, 0.005))

    fig.suptitle(
        f"Figure 3.  Sen's Slope Estimator — Annual and Seasonal Rainfall Trends\n"
        f"Error bars: 95% confidence interval  |  "
        "* p<0.05  ** p<0.01  (Modified Mann–Kendall Test)",
        fontsize=12, fontweight="bold")

    savefig(fig, str(out_dir / f"{prefix}_Fig3_SenSlope_Summary"))


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §9  FIGURE 4 — Significance Summary Heatmap                           ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def fig4_significance_heatmap(trend_df: pd.DataFrame, stns: list,
                               smap: dict, period: str,
                               out_dir: Path, prefix: str):
    """
    Figure 4: Significance heatmap (stations × temporal scales).
    Cell value = Z-statistic; colour = trend direction + significance.
    """
    stns   = [str(s) for s in stns]
    codes  = [smap.get(s, s) for s in stns]
    scales = ["annual","wet","cool_dry","hot"]
    labels = [SCALE_META[s]["label"] for s in scales]
    n_s    = len(stns); n_sc = len(scales)

    # Build matrices
    Z_mat     = np.full((n_sc, n_s), np.nan)
    p_mat     = np.full((n_sc, n_s), np.nan)
    slope_mat = np.full((n_sc, n_s), np.nan)
    sig_mat   = np.zeros((n_sc, n_s), dtype=int)   # 0=ns, 1=*sig05, 2=**sig01

    for si, stn in enumerate(stns):
        for sci, sk in enumerate(scales):
            sub = trend_df[(trend_df["Station"]==stn) &
                           (trend_df["Scale"]==sk)]
            if len(sub) == 0: continue
            Z_mat[sci, si]     = float(sub["Z"].values[0])
            p_mat[sci, si]     = float(sub["p_value"].values[0])
            slope_mat[sci, si] = float(sub["Slope_Q (mm/yr)"].values[0])
            if bool(sub["sig_01"].values[0]): sig_mat[sci, si] = 2
            elif bool(sub["sig_05"].values[0]): sig_mat[sci, si] = 1

    # ── Layout: main heatmap + colorbar + Z-stat panel ──────────────────
    fig = plt.figure(figsize=(max(14, n_s*1.1+4), 10))
    gs  = gridspec.GridSpec(2, 1, figure=fig,
                            height_ratios=[3, 1.4],
                            hspace=0.45, top=0.91, bottom=0.09,
                            left=0.12, right=0.97)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])

    # ── Panel A: Z-statistic heatmap ─────────────────────────────────────
    abs_max = np.nanmax(np.abs(Z_mat)) if not np.all(np.isnan(Z_mat)) else 3.0
    abs_max = max(abs_max, Z_001 + 0.5)   # ensure threshold lines are visible
    im = ax1.imshow(Z_mat, cmap="RdBu_r", vmin=-abs_max, vmax=abs_max,
                    aspect="auto", interpolation="nearest")
    cbar = plt.colorbar(im, ax=ax1, orientation="vertical",
                        pad=0.02, fraction=0.03, shrink=0.95)
    cbar.set_label("Z-statistic", fontsize=11)
    cbar.ax.axhline( Z_005, color="orange", lw=1.5, ls="--")
    cbar.ax.axhline(-Z_005, color="orange", lw=1.5, ls="--")
    cbar.ax.axhline( Z_001, color="red",    lw=1.5, ls="-")
    cbar.ax.axhline(-Z_001, color="red",    lw=1.5, ls="-")

    for sci in range(n_sc):
        for si in range(n_s):
            Z_v  = Z_mat[sci, si]
            p_v  = p_mat[sci, si]
            sl_v = slope_mat[sci, si]
            if np.isnan(Z_v): continue
            lp   = abs(Z_v) / abs_max
            tc   = "white" if lp > 0.70 else "black"
            sig_s= ("**" if sig_mat[sci,si]==2 else
                     "*"  if sig_mat[sci,si]==1 else "ns")
            cell_txt = (f"Z={Z_v:.2f}\n"
                        f"β={sl_v:+.1f}\n"
                        f"p={p_v:.3f} {sig_s}")
            ax1.text(si, sci, cell_txt,
                     ha="center", va="center", fontsize=8,
                     fontweight="bold" if sig_mat[sci,si]>0 else "normal",
                     color=tc, linespacing=1.4)

    ax1.set_xticks(range(n_s))
    ax1.set_xticklabels(codes, fontsize=11, rotation=0)
    ax1.set_yticks(range(n_sc))
    ax1.set_yticklabels(labels, fontsize=11)
    ax1.set_xlabel("Station", fontsize=12, labelpad=4)
    ax1.set_title(
        "(a)  Modified Mann–Kendall Z-Statistic Heatmap\n"
        "     Cell: Z-value | Sen's slope (mm/yr) | p-value | significance",
        loc="left", fontsize=12, fontweight="bold", pad=5)

    # ── Panel B: p-value bar chart ────────────────────────────────────────
    x   = np.arange(n_s)
    bw  = 0.20
    for sci, (sk, lbl) in enumerate(zip(scales, labels)):
        p_vals = [p_mat[sci, si] if not np.isnan(p_mat[sci, si]) else np.nan
                  for si in range(n_s)]
        offs   = (sci - n_sc/2 + 0.5) * bw
        col    = SCALE_META[sk]["color"]
        ax2.bar(x + offs, [-math.log10(p+1e-10) if not np.isnan(p) else 0
                            for p in p_vals],
                width=bw*0.90, color=col, alpha=0.80,
                edgecolor="white", linewidth=0.4, label=lbl, zorder=3)

    ax2.axhline(-math.log10(ALPHA_005), color="orange", lw=1.5, ls="--",
                label=f"α=0.05  (−log₁₀ = {-math.log10(ALPHA_005):.1f})")
    ax2.axhline(-math.log10(ALPHA_001), color="red",    lw=1.5, ls="-",
                label=f"α=0.01  (−log₁₀ = {-math.log10(ALPHA_001):.1f})")
    ax2.set_xticks(x)
    ax2.set_xticklabels(codes, rotation=0, ha="center", fontsize=11)
    ax2.set_ylabel("−log₁₀(p-value)\n[higher = more significant]", fontsize=11)
    ax2.set_xlabel("Station", fontsize=12, labelpad=4)
    ax2.set_title("(b)  p-Value Significance  |  Dashed: α=0.05  |  Solid: α=0.01",
                  loc="left", fontsize=12, fontweight="bold", pad=5)
    ax2.legend(fontsize=9.5, frameon=True, edgecolor="#B0BEC5",
               loc="upper right", ncol=4, handlelength=1.4)
    ax2.set_ylim(bottom=0)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    fig.suptitle(
        f"Figure 4.  Trend Significance — Modified Mann–Kendall Test  |  {period}\n"
        "Blue = increasing trend  |  Red = decreasing trend  |  "
        "* p<0.05  ** p<0.01",
        fontsize=12, fontweight="bold")

    savefig(fig, str(out_dir / f"{prefix}_Fig4_Significance_Heatmap"))


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §10 FIGURE 5 — Autocorrelation Diagnostics                             ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def fig5_autocorrelation(scales: dict, stns: list, smap: dict,
                          period: str, out_dir: Path, prefix: str):
    """
    Figure 5: Lag-1 autocorrelation summary + ACF plot for annual series.
    Panel (a): Lag-1 r₁ per station (bar) with significance band.
    Panel (b): Full ACF (lag 1–10) for regional mean annual series.
    """
    stns   = [str(s) for s in stns]
    codes  = [smap.get(s, s) for s in stns]
    df_ann = scales["annual"]
    n_s    = len(stns)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    fig.subplots_adjust(left=0.07, right=0.97, top=0.88,
                        bottom=0.12, wspace=0.30)

    # ── Panel A: Lag-1 r₁ per station ────────────────────────────────────
    r1_vals = []
    sig_r1  = []
    for stn in stns:
        if stn not in df_ann.columns:
            r1_vals.append(np.nan); sig_r1.append(False); continue
        arr = df_ann[stn].dropna().values.astype(float)
        r1  = autocorrelation_lag1(arr)
        sig = is_significant_autocorr(r1, len(arr))
        r1_vals.append(r1)
        sig_r1.append(sig)

    x = np.arange(n_s)
    bar_cols = [C["inc"] if (not np.isnan(r) and r>0 and s) else
                C["dec"] if (not np.isnan(r) and r<0 and s) else
                C["ns_col"] for r, s in zip(r1_vals, sig_r1)]
    ax1.bar(x, [r if not np.isnan(r) else 0 for r in r1_vals],
            width=0.65, color=bar_cols, alpha=0.85,
            edgecolor="white", linewidth=0.5, zorder=3)

    # Significance band (two-tailed, α=0.05)
    n_common = int(np.mean([len(df_ann[s].dropna()) for s in stns
                             if s in df_ann.columns]))
    z_crit_05 = scipy_norm.ppf(1 - ALPHA_005/2) / math.sqrt(n_common)
    ax1.axhline( z_crit_05, color="orange", lw=1.5, ls="--",
                 label=f"α=0.05 band (±{z_crit_05:.3f})")
    ax1.axhline(-z_crit_05, color="orange", lw=1.5, ls="--")
    ax1.axhline(0, color="black", lw=0.8, ls="-", alpha=0.5)

    for xi, (r, s) in enumerate(zip(r1_vals, sig_r1)):
        if np.isnan(r): continue
        ax1.text(xi, r + (0.015 if r>=0 else -0.025),
                 f"*{r:.2f}" if s else f"{r:.2f}",
                 ha="center", va="bottom" if r>=0 else "top",
                 fontsize=8.5, fontweight="bold" if s else "normal",
                 color="black")

    ax1.set_xticks(x)
    ax1.set_xticklabels(codes, rotation=0, ha="center", fontsize=11)
    ax1.set_ylabel("Lag-1 Autocorrelation (r₁)", fontsize=12)
    ax1.set_xlabel("Station", fontsize=12)
    ax1.set_ylim(-1, 1)
    ax1.set_title("(a)  Lag-1 Autocorrelation (r₁) — Annual Rainfall\n"
                  "     * = statistically significant (α=0.05)\n"
                  "     Dashed: significance threshold",
                  loc="left", fontsize=12, fontweight="bold", pad=5)
    ax1.legend(fontsize=10, frameon=True, edgecolor="#B0BEC5")
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    # ── Panel B: ACF for regional mean (lag 1–10) ─────────────────────────
    cols    = [s for s in stns if s in df_ann.columns]
    reg_ann = df_ann[cols].mean(axis=1).dropna().values.astype(float)
    n_reg   = len(reg_ann)
    max_lag_plot = min(10, n_reg // 3)

    rho_all = autocorrelations_all_lags(reg_ann, max_lag=max_lag_plot)
    lags    = np.arange(1, len(rho_all) + 1)

    # 95% confidence interval (Bartlett's formula, approximate)
    se_rho = 1.0 / math.sqrt(n_reg)
    z_crit_95 = scipy_norm.ppf(0.975)
    ci_band   = z_crit_95 * se_rho

    ax2.bar(lags, rho_all, width=0.65, color=C["obs"], alpha=0.75,
            edgecolor="white", linewidth=0.5, zorder=3)
    ax2.axhline( ci_band, color="red", lw=1.5, ls="--",
                 label=f"95% CI (±{ci_band:.3f})")
    ax2.axhline(-ci_band, color="red", lw=1.5, ls="--")
    ax2.axhline(0, color="black", lw=0.8, ls="-", alpha=0.5)

    # Mark significant lags
    for lag_i, rho_v in zip(lags, rho_all):
        if abs(rho_v) > ci_band:
            ax2.text(lag_i, rho_v + (0.02 if rho_v>=0 else -0.04),
                     f"r={rho_v:.2f}*",
                     ha="center", va="bottom" if rho_v>=0 else "top",
                     fontsize=9, fontweight="bold", color=C["dec"])

    ax2.set_xticks(lags)
    ax2.set_xlabel("Lag (years)", fontsize=12)
    ax2.set_ylabel("Autocorrelation Coefficient (rₖ)", fontsize=12)
    ax2.set_ylim(-1, 1)
    ax2.set_title("(b)  ACF — Regional Mean Annual Rainfall\n"
                  f"     Lag 1–{max_lag_plot}  |  "
                  "Determines need for Modified Mann–Kendall",
                  loc="left", fontsize=12, fontweight="bold", pad=5)
    ax2.legend(fontsize=10, frameon=True, edgecolor="#B0BEC5")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    fig.suptitle(
        f"Figure 5.  Autocorrelation Diagnostics — Annual Rainfall  |  {period}\n"
        "Significant autocorrelation → Modified Mann–Kendall Test required  "
        "(Hamed & Rao 1998)",
        fontsize=12, fontweight="bold")

    savefig(fig, str(out_dir / f"{prefix}_Fig5_Autocorrelation"))


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §11 FIGURE 6 — Descriptive Statistics Heatmap                          ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def fig6_descriptive_heatmap(desc_df: pd.DataFrame, stns: list,
                              smap: dict, period: str,
                              out_dir: Path, prefix: str):
    """
    Figure 6: Heatmap of descriptive statistics per station.
    Rows = statistics; Columns = stations.
    """
    stns   = [str(s) for s in stns]
    codes  = [smap.get(s, s) for s in stns]

    stats_to_plot = [
        ("Mean (mm)",    "Mean Annual\nRainfall (mm)",    "YlOrBr"),
        ("Std (mm)",     "Std Dev\n(mm)",                 "YlOrBr"),
        ("CV (%)",       "Coefficient of\nVariation (%)", "RdYlGn_r"),
        ("Wet-days/yr",  "Wet Days\n(per year)",          "Blues"),
        ("Max (mm)",     "Maximum Annual\nRainfall (mm)", "YlOrRd"),
        ("Skewness",     "Skewness",                      "PuOr_r"),
    ]

    n_stat = len(stats_to_plot)
    n_s    = len(stns)

    fig, axes = plt.subplots(n_stat, 1,
                             figsize=(max(12, n_s*1.1+3), 3.0*n_stat),
                             squeeze=False)
    fig.subplots_adjust(hspace=0.55, top=0.93, bottom=0.06,
                        left=0.18, right=0.97)

    for pi, (col_key, title_lbl, cmap_s) in enumerate(stats_to_plot):
        ax = axes[pi][0]
        if col_key not in desc_df.columns:
            ax.set_visible(False); continue

        vals = np.array([desc_df.loc[stn, col_key]
                         if stn in desc_df.index else np.nan
                         for stn in stns]).reshape(1, -1)

        vmin = float(np.nanmin(vals)) if not np.all(np.isnan(vals)) else 0
        vmax = float(np.nanmax(vals)) if not np.all(np.isnan(vals)) else 1

        # Symmetric for skewness
        if col_key == "Skewness":
            amax = max(abs(vmin), abs(vmax), 0.1)
            vmin, vmax = -amax, amax

        im = ax.imshow(vals, cmap=cmap_s, vmin=vmin, vmax=vmax,
                       aspect="auto", interpolation="nearest")
        plt.colorbar(im, ax=ax, orientation="vertical",
                     pad=0.01, fraction=0.025, shrink=0.95)

        for si in range(n_s):
            v = vals[0, si]
            if np.isnan(v): continue
            lp = (v - vmin) / (vmax - vmin + 1e-9)
            tc = "white" if (lp > 0.70 or lp < 0.30) else "black"
            ax.text(si, 0, f"{v:.1f}", ha="center", va="center",
                    fontsize=10, fontweight="bold", color=tc)

        ax.set_xticks(range(n_s))
        ax.set_xticklabels(codes, rotation=0, ha="center",
                           fontsize=11)
        ax.set_yticks([0])
        ax.set_yticklabels([title_lbl], fontsize=11)
        ax.set_xlabel("Station" if pi == n_stat-1 else "",
                      fontsize=12, labelpad=3)
        ax.set_title(f"({chr(97+pi)})  {title_lbl}",
                     loc="left", fontsize=11, fontweight="bold", pad=4)

    fig.suptitle(
        f"Figure 6.  Descriptive Statistics of Annual Rainfall — {period}\n"
        "Computed from daily observed rainfall data",
        fontsize=12, fontweight="bold")

    savefig(fig, str(out_dir / f"{prefix}_Fig6_Descriptive_Heatmap"))


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §12 EXCEL OUTPUT — 5 SHEETS                                            ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def write_excel(out_xlsx: Path, stns: list, smap: dict,
                trend_df: pd.DataFrame, desc_df: pd.DataFrame,
                qc_dict: dict, scales: dict,
                period: str):
    """
    Write 5 Excel sheets:
      S1 — Mann-Kendall Results (all stations × all scales)
      S2 — Sen's Slope with 95% CI
      S3 — Descriptive Statistics
      S4 — Data Quality Control Report
      S5 — Methods & References
    """
    stns   = [str(s) for s in stns]
    codes  = [smap.get(s, s) for s in stns]
    wb     = Workbook()
    wb.remove(wb.active)

    def _title(ws, nc, t1, t2=""):
        mxsc(ws,1,1,nc,t1,bold=True,fc="FFFFFF",bg=XC["title"],sz=12,align="left")
        ws.row_dimensions[1].height = 24
        if t2:
            mxsc(ws,2,1,nc,t2,italic=True,fc="FFFFFF",bg=XC["sub"],sz=9)
            ws.row_dimensions[2].height = 14

    def _hdr(ws, r, hdrs):
        for ci, h in enumerate(hdrs, 1):
            xsc(ws,r,ci,h,bold=True,fc="FFFFFF",bg=XC["hdr"],
                border=tb(),sz=10,wrap=True)
        ws.row_dimensions[r].height = 40

    alt = [PatternFill("solid",fgColor="E8F4FD"),
           PatternFill("solid",fgColor="FFFFFF")]

    # ── S1: Modified Mann-Kendall Results ───────────────────────────────
    ws1 = wb.create_sheet("S1 MannKendall Results")
    ws1.sheet_view.showGridLines = False
    ws1.freeze_panes = "E4"
    _title(ws1, 14,
           f"Modified Mann–Kendall Trend Test Results  |  {period}",
           "Hamed & Rao (1998) autocorrelation correction  |  "
           "* p<0.05  ** p<0.01  |  "
           "Z>0: increasing, Z<0: decreasing")

    hdr1 = ["Station","Code","Scale","N\n(years)","S\nStat.",
             "Var(S)","Var*(S)\n(adj.)","n_eff","ρ₁\n(Lag-1)",
             "Z","p-value","Trend\nDirection","Sig.\n(α=0.05)","Sig.\n(α=0.01)"]
    _hdr(ws1, 3, hdr1)

    scale_bg = {"annual":   XC["white"],
                "wet":      XC["wet_h"],
                "cool_dry": XC["dry_h"],
                "hot":      XC["hot_h"]}

    ri1 = 4
    for _, row in trend_df.iterrows():
        sk  = row["Scale"]
        bg  = scale_bg.get(sk, XC["white"])
        s05 = bool(row["sig_05"])
        s01 = bool(row["sig_01"])
        if   s01: bg = XC["sig01"]
        elif s05: bg = XC["sig05"]

        vals = [
            str(row["Station"]), str(row["Code"]), row["Scale_Label"],
            row["N_years"], row["S"], row["Var_S"], row["Var_S_adj"],
            row["n_eff"], row["rho_1"], row["Z"], row["p_value"],
            str(row["Trend"]),
            "**" if s01 else ("*" if s05 else "ns"),
            "**" if s01 else ("*" if s01 else ("*" if s05 else "ns")),
        ]
        for ci, v in enumerate(vals, 1):
            if isinstance(v, float) and np.isnan(v): v = "—"
            elif isinstance(v, float): v = round(v, 4)
            cell = xsc(ws1,ri1,ci,v,bg=bg,border=tb(),sz=9,
                       align="left" if ci<=3 else "right")
            if ci == 12 and "Increasing" in str(v):
                cell.font = Font(bold=True,color="1B5E20",name="Calibri",size=9)
            if ci == 12 and "Decreasing" in str(v):
                cell.font = Font(bold=True,color="B71C1C",name="Calibri",size=9)
            if ci in (13,14) and v not in ("ns","—"):
                cell.font = Font(bold=True,color="E65100",name="Calibri",size=9)
        ws1.row_dimensions[ri1].height = 15
        ri1 += 1

    for ci,w in enumerate([10,8,14,7,10,10,10,8,8,10,10,18,8,8],1): cw(ws1,ci,w)

    # ── S2: Sen's Slope Summary ─────────────────────────────────────────
    ws2 = wb.create_sheet("S2 Sens Slope")
    ws2.sheet_view.showGridLines = False
    _title(ws2, 10,
           f"Sen's Slope Estimator — Magnitude of Rainfall Trend  |  {period}",
           "Sen (1968) JASA 63:1379–1389  |  "
           "95% CI: Gilbert (1987) rank-based method  |  "
           "Positive β = increasing rainfall  |  units: mm/year")

    hdr2 = ["Station","Code","Scale","N\n(years)",
             "Sen's Slope β\n(mm yr⁻¹)",
             "95% CI Lower\n(mm yr⁻¹)",
             "95% CI Upper\n(mm yr⁻¹)",
             "Z","p-value","Trend"]
    _hdr(ws2, 3, hdr2)

    ri2 = 4
    for _, row in trend_df.iterrows():
        s05 = bool(row["sig_05"])
        s01 = bool(row["sig_01"])
        bg  = (XC["sig01"] if s01 else XC["sig05"] if s05 else XC["white"])
        sk  = row["Scale"]
        if not s05: bg = scale_bg.get(sk, XC["white"])
        vals = [str(row["Station"]), str(row["Code"]), row["Scale_Label"],
                row["N_years"],
                row["Slope_Q (mm/yr)"],
                row["Slope_CI_lo"],
                row["Slope_CI_hi"],
                row["Z"], row["p_value"], str(row["Trend"])]
        for ci, v in enumerate(vals, 1):
            if isinstance(v, float) and np.isnan(v): v = "—"
            elif isinstance(v, float): v = round(v, 3)
            cell = xsc(ws2,ri2,ci,v,bg=bg,border=tb(),sz=9,
                       align="left" if ci<=3 else "right")
            if ci == 5 and isinstance(v, float):
                fc_v = "1B5E20" if v>0 else "B71C1C"
                cell.font = Font(bold=s05, color=fc_v, name="Calibri", size=9)
        ws2.row_dimensions[ri2].height = 15
        ri2 += 1

    for ci,w in enumerate([10,8,14,7,14,14,14,10,10,18],1): cw(ws2,ci,w)

    # ── S3: Descriptive Statistics ──────────────────────────────────────
    ws3 = wb.create_sheet("S3 Descriptive Statistics")
    ws3.sheet_view.showGridLines = False
    _title(ws3, 10,
           f"Descriptive Statistics of Annual Rainfall  |  {period}",
           "Computed from daily observed rainfall  |  "
           f"Wet-day threshold: ≥{WET_THR} mm day⁻¹  |  "
           "CV = Coefficient of Variation (%)")
    hdr3 = ["Station","Code","N\n(years)",
             "Mean\n(mm yr⁻¹)",
             "Max\n(mm yr⁻¹)",
             "Min\n(mm yr⁻¹)",
             "Std Dev\n(mm)",
             "CV\n(%)",
             "Wet-days\n(yr⁻¹)",
             "Skewness"]
    _hdr(ws3, 3, hdr3)

    ri3 = 4
    for ni, stn in enumerate(stns, 1):
        bg_hex = "E8F4FD" if ni%2==0 else "FFFFFF"
        if stn not in desc_df.index:
            xsc(ws3,ri3,1,stn,bg=bg_hex,border=tb(),sz=9)
            ws3.row_dimensions[ri3].height = 15; ri3+=1; continue
        d = desc_df.loc[stn]
        code = smap.get(stn, stn)
        vals = [stn, code, d["N_years"], d["Mean (mm)"],
                d["Max (mm)"], d["Min (mm)"], d["Std (mm)"],
                d["CV (%)"], d["Wet-days/yr"], d["Skewness"]]
        for ci, v in enumerate(vals, 1):
            if isinstance(v, float) and np.isnan(v): v = "—"
            elif isinstance(v, float): v = round(v, 1)
            xsc(ws3,ri3,ci,v,bg=bg_hex,border=tb(),sz=9,
                align="left" if ci<=2 else "right")
        ws3.row_dimensions[ri3].height = 16
        ri3 += 1

    for ci,w in enumerate([10,8,8,12,12,12,10,8,10,10],1): cw(ws3,ci,w)

    # ── S4: QC Report ────────────────────────────────────────────────────
    ws4 = wb.create_sheet("S4 Quality Control")
    ws4.sheet_view.showGridLines = False
    _title(ws4, 8,
           "Data Quality Control Report",
           f"Period: {period}  |  "
           "Outlier detection: IQR method (upper fence = Q3 + 3×IQR)  |  "
           "Gap filling: linear interpolation (max 5 consecutive days)")
    hdr4 = ["Station","Code","Total Days","Missing\n(days)",
             "Missing\n(%)","Outliers\n(flagged)",
             "Upper Fence\n(mm)","Gaps Filled\n(days)"]
    _hdr(ws4, 3, hdr4)
    ri4 = 4
    for ni, stn in enumerate(stns, 1):
        bg_hex4 = "E8F4FD" if ni%2==0 else "FFFFFF"
        q  = qc_dict.get(stn, {})
        vals = [stn, smap.get(stn,stn), q.get("n_total","—"),
                q.get("n_missing","—"), q.get("pct_miss","—"),
                q.get("n_outlier","—"), q.get("upper_fence","—"),
                q.get("n_filled","—")]
        for ci, v in enumerate(vals, 1):
            cell = xsc(ws4,ri4,ci,v,bg=bg_hex4,border=tb(),sz=9,
                       align="left" if ci<=2 else "right")
            if ci==4 and isinstance(v,int) and v>0:
                cell.fill = xfill("FFCCBC")
        ws4.row_dimensions[ri4].height = 16
        ri4 += 1
    for ci,w in enumerate([10,8,10,10,10,12,14,12],1): cw(ws4,ci,w)

    # ── S5: Methods & References ─────────────────────────────────────────
    ws5 = wb.create_sheet("S5 Methods & References")
    ws5.sheet_view.showGridLines = False
    mxsc(ws5,1,1,3,
         "Statistical Methods & Full References",
         bold=True,fc="FFFFFF",bg=XC["title"],sz=13)
    ws5.row_dimensions[1].height = 26

    methods = [
        ("Modified Mann–Kendall Test",
         "Hamed & Rao (1998) J. Hydrol. 204:182–196",
         "Non-parametric trend test with serial autocorrelation correction. "
         "S statistic computed for all pairs. Var(S) adjusted using effective "
         "sample size n* = n / [1 + 2Σ(1−k/n)ρ_k]. "
         "Z = (S±1)/√Var*(S). Two-tailed p-value from standard normal. "
         "Significance: α=0.05 (|Z|>1.96) and α=0.01 (|Z|>2.58)."),
        ("Sen's Slope Estimator",
         "Sen (1968) JASA 63:1379–1389; Gilbert (1987)",
         "Slope: Q = median[(xⱼ−xᵢ)/(j−i)] for all j>i pairs. "
         "95% CI by rank-based method: Cα = z₀.₀₂₅ × √Var(S); "
         "CI bounds = sorted slopes at ranks (N−Cα)/2 and (N+Cα)/2+1."),
        ("Lag-1 Autocorrelation",
         "Pearson formula; see also Box & Jenkins (1976)",
         "r₁ = Σ(xᵢ−x̄)(xᵢ₊₁−x̄) / Σ(xᵢ−x̄)². "
         "Significant if |r₁| > z₀.₀₂₅/√n (two-tailed). "
         "If significant → Modified MK applied instead of standard MK."),
        ("Standard Mann–Kendall Test",
         "Mann (1945) Econometrica 13:245–259; Kendall (1975)",
         "S = Σ Σ sgn(xⱼ−xᵢ). "
         "Var(S) = [n(n−1)(2n+5) − Σtₚ(tₚ−1)(2tₚ+5)] / 18 (tie-corrected)."),
        ("Outlier Detection",
         "Tukey (1977) IQR fence",
         "Upper fence = Q3 + 3×IQR (extreme outlier threshold). "
         "Flagged but NOT removed. Linear interpolation for short gaps ≤5 days."),
        ("Season Definitions",
         "Thai hydro-climatological standard",
         "Wet: May–October | Cool-dry: November–February | Hot: March–April. "
         "Wet-day threshold: ≥1.0 mm/day (WMO standard)."),
        ("References",
         "",
         "Mann HB (1945) Econometrica 13:245–259.\n"
         "Kendall MG (1975) Rank Correlation Methods. Griffin, London.\n"
         "Sen PK (1968) JASA 63:1379–1389.\n"
         "Hamed KH, Rao AR (1998) J. Hydrol. 204:182–196.\n"
         "Gilbert RO (1987) Statistical Methods for Environmental Pollution. "
         "Van Nostrand Reinhold, New York.\n"
         "Yue S, Wang C (2004) Water Resour. Res. 40:W08307.\n"
         "Box GEP, Jenkins GM (1976) Time Series Analysis. Holden-Day.\n"
         "WMO (2008) Guide to Hydrological Practices. WMO-No. 168."),
    ]

    alt2 = [PatternFill("solid",fgColor="DEEAF1"),
            PatternFill("solid",fgColor="FFFFFF")]
    for ri, (met, ref, desc) in enumerate(methods, 3):
        fl = alt2[ri%2]
        for ci, v in enumerate([met, ref, desc], 1):
            cell = xsc(ws5,ri,ci,v,bold=(ci<=2),sz=9.5,align="left",border=tb())
            cell.fill = fl
            if ci==3:
                cell.alignment = Alignment(horizontal="left",
                                           vertical="top", wrap_text=True)
        ws5.row_dimensions[ri].height = 70
    for ci, w in enumerate([26, 40, 68], 1): cw(ws5, ci, w)

    wb.save(str(out_xlsx))
    print(f"  ✓  Excel saved: {out_xlsx.name}  (5 sheets)")


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §13 MAIN                                                               ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def short_labels(stns: list) -> dict:
    return {str(s): f"S{i+1}" for i, s in enumerate(stns)}


def main():
    SEP = "═" * 72
    print(SEP)
    print("  Rainfall Trend Analysis  v1.0  — Publication Edition")
    print("  Modified Mann–Kendall Test + Sen's Slope Estimator")
    print("  Workflow: Data QC → Descriptive Stats → Autocorrelation")
    print("            → Modified MK → Sen's Slope → Figures + Excel")
    print(SEP)

    # ── Working directory ───────────────────────────────────────────────
    try:
        work_dir = (sys.argv[1].strip('"').strip("'")
                    if len(sys.argv) > 1
                    else str(Path(os.path.abspath(__file__)).parent))
    except Exception:
        work_dir = os.getcwd()

    out_dir  = Path(work_dir)
    csv_path = find_csv(work_dir)
    base     = Path(csv_path).stem
    prefix   = f"Output_MK_{base}"

    print(f"  Input : {csv_path}")
    print(f"  Output: {work_dir}")
    print("-" * 72)

    # ════════════════════════════════════════════════════════════════════
    # Step 1: Load Data
    # ════════════════════════════════════════════════════════════════════
    print("\n  Step 1: Loading data ...")
    df_raw  = load_daily(csv_path)
    stns    = df_raw.columns.tolist()
    stns_str= [str(s) for s in stns]
    smap    = short_labels(stns_str)
    period  = (f"{df_raw.index[0].year}–{df_raw.index[-1].year}")
    print(f"  Stations  : {len(stns)}  ({', '.join(stns_str)})")
    print(f"  Period    : {period}  ({len(df_raw):,} daily records)")
    print(f"  Short code: {list(smap.values())}")

    # ════════════════════════════════════════════════════════════════════
    # Step 2: Quality Control
    # ════════════════════════════════════════════════════════════════════
    print("\n  Step 2: Data Quality Control ...")
    df, qc_dict = quality_control(df_raw.copy())
    for s, q in qc_dict.items():
        code = smap.get(s, s)
        print(f"    {code} [{s}]  missing={q['n_missing']}d "
              f"({q['pct_miss']}%)  outliers={q['n_outlier']}  "
              f"filled={q['n_filled']}d")

    # ════════════════════════════════════════════════════════════════════
    # Step 3: Temporal Aggregation
    # ════════════════════════════════════════════════════════════════════
    print("\n  Step 3: Temporal aggregation ...")
    scales = aggregate_temporal(df)
    for sk, df_s in scales.items():
        print(f"    {SCALE_META[sk]['label']:18s}: "
              f"{len(df_s)} years × {df_s.shape[1]} stations")

    # ════════════════════════════════════════════════════════════════════
    # Step 3b: Descriptive Statistics
    # ════════════════════════════════════════════════════════════════════
    print("\n  Step 3b: Descriptive statistics ...")
    desc_df = descriptive_stats(scales["annual"], df)
    print(desc_df[["Mean (mm)","Std (mm)","CV (%)","Wet-days/yr"]].to_string())

    # ════════════════════════════════════════════════════════════════════
    # Step 4: Autocorrelation Check (Lag-1)
    # ════════════════════════════════════════════════════════════════════
    print("\n  Step 4: Lag-1 Autocorrelation ...")
    print(f"  {'Station':10s}  {'Code':6s}  {'r₁':>8s}  "
          f"{'Sig.(α=0.05)':>14s}  {'→ Use Modified MK':>20s}")
    any_sig_ac = False
    for stn in stns_str:
        code = smap.get(stn, stn)
        arr  = scales["annual"][stn].dropna().values.astype(float) \
               if stn in scales["annual"].columns else np.array([])
        r1   = autocorrelation_lag1(arr)
        sig  = is_significant_autocorr(r1, len(arr))
        if sig: any_sig_ac = True
        flag = "Yes ✓" if sig else "No (standard MK also valid)"
        r1_s = f"{r1:.4f}" if not np.isnan(r1) else "N/A"
        print(f"  {stn:10s}  {code:6s}  {r1_s:>8s}  "
              f"{'Yes ***' if sig else 'No':>14s}  {flag:>20s}")

    if any_sig_ac:
        print("\n  ✓  Autocorrelation detected → Modified Mann–Kendall applied")
    else:
        print("\n  ✓  No significant autocorrelation → Standard MK is acceptable,")
        print("     but Modified MK is used for consistency")

    # ════════════════════════════════════════════════════════════════════
    # Step 4b: Modified Mann–Kendall + Sen's Slope (all stations × scales)
    # ════════════════════════════════════════════════════════════════════
    print(f"\n{'─'*72}")
    print("  Step 4b: Modified Mann–Kendall + Sen's Slope ...")
    trend_df = run_trend_analysis(scales, stns_str, smap)

    # Print summary table
    print(f"\n  {'Station':10s} {'Code':6s} {'Scale':14s} "
          f"{'Z':>8s} {'p':>8s} {'β (mm/yr)':>12s} {'Trend':>22s}")
    print("  " + "-"*70)
    for _, row in trend_df.iterrows():
        sig_s = (" **" if row["sig_01"] else " *" if row["sig_05"] else " ns")
        beta  = f"{row['Slope_Q (mm/yr)']:+.3f}" \
                if not np.isnan(row["Slope_Q (mm/yr)"]) else "—"
        print(f"  {row['Station']:10s} {row['Code']:6s} "
              f"{row['Scale_Label']:14s} "
              f"{row['Z']:>8.3f} {row['p_value']:>8.4f} "
              f"{beta:>12s}  {row['Trend']}{sig_s}")

    # Count significant trends
    n_sig05 = trend_df["sig_05"].sum()
    n_sig01 = trend_df["sig_01"].sum()
    n_total = len(trend_df)
    print(f"\n  Significant trends (p<0.05): {n_sig05}/{n_total}")
    print(f"  Significant trends (p<0.01): {n_sig01}/{n_total}")

    # ════════════════════════════════════════════════════════════════════
    # Step 5: Generate Figures
    # ════════════════════════════════════════════════════════════════════
    print(f"\n{'─'*72}")
    print("  Step 5: Generating publication figures (600 DPI) ...")

    print("\n  Figure 1: Annual Rainfall Time Series + Trend ...")
    fig1_annual_timeseries(scales, trend_df, stns_str, smap,
                            period, out_dir, prefix)

    print("\n  Figure 2: Seasonal Rainfall Time Series ...")
    fig2_seasonal_timeseries(scales, trend_df, stns_str, period,
                              out_dir, prefix)

    print("\n  Figure 3: Sen's Slope Summary ...")
    fig3_sens_slope_summary(trend_df, stns_str, smap, period,
                             out_dir, prefix)

    print("\n  Figure 4: Significance Heatmap ...")
    fig4_significance_heatmap(trend_df, stns_str, smap, period,
                               out_dir, prefix)

    print("\n  Figure 5: Autocorrelation Diagnostics ...")
    fig5_autocorrelation(scales, stns_str, smap, period, out_dir, prefix)

    print("\n  Figure 6: Descriptive Statistics Heatmap ...")
    fig6_descriptive_heatmap(desc_df, stns_str, smap, period,
                              out_dir, prefix)

    # ════════════════════════════════════════════════════════════════════
    # Step 6: Excel Output
    # ════════════════════════════════════════════════════════════════════
    print(f"\n{'─'*72}")
    out_xlsx = out_dir / f"Output_MK_{base}_Results.xlsx"
    print(f"  Step 6: Writing Excel → {out_xlsx.name} ...")
    write_excel(out_xlsx, stns_str, smap, trend_df, desc_df,
                qc_dict, scales, period)

    # ════════════════════════════════════════════════════════════════════
    # Final Summary
    # ════════════════════════════════════════════════════════════════════
    n_fig = len(list(out_dir.glob(f"{prefix}_Fig*.png")))
    print()
    print(SEP)
    print(f"  ✓  DONE — Rainfall Trend Analysis v1.0")
    print(f"  {'─'*62}")
    print(f"  Study area    : Phetchaburi–Prachuap Khiri Khan Basin")
    print(f"  Period        : {period}")
    print(f"  Stations      : {len(stns_str)}")
    print(f"  Method        : Modified Mann–Kendall (Hamed & Rao 1998)")
    print(f"  Temporal scales : Annual / Wet / Cool-dry / Hot")
    print(f"  Sig. (p<0.05) : {n_sig05}/{n_total} station×scale combinations")
    print(f"  Sig. (p<0.01) : {n_sig01}/{n_total} station×scale combinations")
    print(f"  Autocorr. flag: {'Yes (Modified MK essential)' if any_sig_ac else 'No'}")
    print(f"  Figures       : {n_fig} PNG" + (" + PDF" if SAVE_PDF else ""))
    print(f"  Excel         : {out_xlsx.name}  (5 sheets)")
    print(f"  Saved in      : {work_dir}")
    print(SEP)


if __name__ == "__main__":
    main()
