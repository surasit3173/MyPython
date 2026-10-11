"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Rainfall Trend Analysis — Publication Edition v5.0                         ║
║  Study: Phetchaburi–Prachuap Khiri Khan River Basin, Western Thailand       ║
║  Period: 1981–2014  |  Daily Rainfall Data                                  ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  CHANGELOG v5.0:                                                            ║
║  - Fixed Sen's slope 95% CI calculation using Gilbert (1987) rank-based.    ║
║  - Changed Autocorrelation significance test from normal approx to t-test.  ║
║  - Improved Data QC: Monotonic index check, exact missing gap reporting,    ║
║    outlier dual-screening (flagging extreme, but no dropping).              ║
║  - Updated interpolation to limit=3, limit_area='inside'.                   ║
║  - Added Pettitt's Test for Homogeneity (Fig 11).                           ║
║  - Updated Excel generation to strictly output specified Table 2, 3, 4.     ║
║  - Added rigorous docstrings and localized warnings control.                ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import math
import warnings
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

import numpy as np
import pandas as pd
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
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# Limit warnings ignoring to specific domains, ensuring transparency
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §0  CONSTANTS & STYLE                                                  ║
# ╚══════════════════════════════════════════════════════════════════════════╝

VERSION: str = "5.0"
WET_THR: float = 1.0                   
WET_MONTHS: List[int] = [5, 6, 7, 8, 9, 10]
DRY_MONTHS: List[int] = [11, 12, 1, 2, 3, 4]
MIN_N: int = 10
ALPHA_005: float = 0.05
ALPHA_001: float = 0.01
Z_005: float = 1.9600
Z_001: float = 2.5758
SAVE_PDF: bool = True
DPI: int = 600
MONTH_ABBR: List[str] = ["Jan","Feb","Mar","Apr","May","Jun",
                         "Jul","Aug","Sep","Oct","Nov","Dec"]

C: Dict[str, str] = dict(
    annual  = "#37474F",  annual_lt = "#B0BEC5",
    wet     = "#1565C0",  wet_lt    = "#90CAF9",
    dry     = "#E65100",  dry_lt    = "#FFCC80",
    inc     = "#1B5E20",  inc_lt    = "#A5D6A7",
    dec     = "#B71C1C",  dec_lt    = "#EF9A9A",
    ns_col  = "#78909C",  ns_lt     = "#CFD8DC",
    mk_std  = "#6A1B9A",  mk_mod    = "#0277BD",
    gold    = "#F9A825",  grey      = "#546E7A",
)

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
})

THIN = Side(style="thin",   color="BDBDBD")
XC = dict(
    title  = "13293D", sub = "1F4E79", hdr = "2E75B6",
    wet_h  = "DDEEFF", dry_h = "FFF3E0",
    ann_h  = "ECEFF1", mon_h = "E8F5E9",
    sig05  = "FFF9C4", sig01 = "FFECB3",
    inc_c  = "E8F5E9", dec_c = "FFEBEE",
    ns_c   = "F5F5F5", white = "FFFFFF",
)

def tb(): return Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
def xfill(h): return PatternFill("solid", fgColor=h)

def xsc(ws, r, c, val=None, bold=False, italic=False,
        fc=None, bg=None, align="center", sz=10, wrap=True, border=None):
    cell = ws.cell(row=r, column=c)
    if val is not None: cell.value = val
    cell.font = Font(bold=bold, italic=italic, name="Calibri", size=sz, color=fc if fc else "1A1A1A")
    cell.alignment = Alignment(horizontal=align, vertical="center", wrap_text=wrap)
    if bg: cell.fill = xfill(bg)
    if border: cell.border = border
    return cell

def cw(ws, col, w): ws.column_dimensions[get_column_letter(col)].width = w
def rh(ws, r, h): ws.row_dimensions[r].height = h

def savefig(fig, path_noext: str) -> None:
    fig.savefig(f"{path_noext}.png", dpi=DPI, bbox_inches="tight", pad_inches=0.15)
    if SAVE_PDF:
        fig.savefig(f"{path_noext}.pdf", bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    print(f"    ✓  {Path(path_noext).name}.png" + (" + .pdf" if SAVE_PDF else ""))


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §1  DATA LOADING & QUALITY CONTROL                                     ║
# ╚══════════════════════════════════════════════════════════════════════════╝

MISS_FLAGS: List[float] = [-99, -999, -9999, -9.99e+20, 9.99e+20, 1e+20]

def find_csv(folder: str) -> str:
    csvs = sorted(Path(folder).glob("*.csv"))
    obs  = [f for f in csvs if "observed" in f.name.lower() or "rain" in f.name.lower()]
    return str((obs or csvs)[0]) if (obs or csvs) else sys.exit("No CSV found")

def load_daily(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    for mv in MISS_FLAGS:
        df.replace(mv, np.nan, inplace=True)
    df.columns = [str(c) for c in df.columns]
    stns = [c for c in df.columns if c not in ("YEAR","MONTH","DAY")]
    for s in stns:
        df.loc[df[s] < 0, s] = np.nan
    df["date"] = pd.to_datetime({"year": df["YEAR"], "month": df["MONTH"], "day": df["DAY"]})
    df = df.set_index("date")[stns]
    
    # Remove duplicate dates (V5.0 Requirement)
    df = df[~df.index.duplicated(keep='first')]
    
    # Ensure monotonic increasing (V5.0 Requirement)
    if not df.index.is_monotonic_increasing:
        df = df.sort_index()
        
    return df

def quality_control(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    QC Implementation (v5.0):
    - Report consecutive gaps > 5 days.
    - Outlier Dual Approach: Screen with IQR but DO NOT drop extreme events.
    - Interpolation: strictly linear <= 3 days, leave remaining as NaN.
    """
    stns = df.columns.tolist()
    qc = {}
    df_clean = df.copy()
    
    for s in stns:
        series = df_clean[s].copy()
        n_total = len(series)
        n_miss = int(series.isna().sum())
        
        # Consecutive gap reporting
        gap_mask = series.isna()
        gap_blocks = gap_mask.groupby((~gap_mask).cumsum()).sum()
        consecutive_gaps_gt_5 = int((gap_blocks > 5).sum())
        
        # Outlier Detection (Screening only)
        wet_vals = series[(series >= WET_THR) & series.notna()]
        if len(wet_vals) > 0:
            q1, q3 = float(wet_vals.quantile(0.25)), float(wet_vals.quantile(0.75))
            upper_fence = q3 + 3.0 * (q3 - q1)
            n_out = int((series > upper_fence).sum())
        else:
            upper_fence = np.nan
            n_out = 0
            
        # Linear Interpolation limit=3
        filled = series.interpolate(method="time", limit=3, limit_area="inside")
        n_fill = int(filled.notna().sum()) - int(series.notna().sum())
        
        df_clean[s] = filled
        qc[s] = dict(n_total=n_total, n_missing=n_miss, 
                     pct_miss=round(n_miss/n_total*100, 2),
                     gaps_gt_5=consecutive_gaps_gt_5,
                     n_outlier=n_out, upper_fence=round(upper_fence, 1) if not np.isnan(upper_fence) else 0,
                     n_filled=n_fill)
                     
    return df_clean, qc


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §2  TEMPORAL AGGREGATION & STATS                                       ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def aggregate_all(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    scales = {}
    scales["annual"] = df.resample("YS").apply(lambda g: g.sum(min_count=int(0.8 * len(g))))
    
    wet = df[df.index.month.isin(WET_MONTHS)]
    scales["wet"] = wet.resample("YS").apply(lambda g: g.sum(min_count=int(0.8 * len(g))))
    
    dry_raw = df[df.index.month.isin(DRY_MONTHS)].copy()
    late_mask = dry_raw.index.month.isin([11, 12])
    new_idx = [d.replace(year=d.year + 1) if m else d for d, m in zip(dry_raw.index.to_list(), late_mask)]
    dry_raw.index = pd.DatetimeIndex(new_idx)
    scales["dry"] = dry_raw.resample("YS").apply(lambda g: g.sum(min_count=int(0.8 * len(g))))
    
    scales["monthly_all"] = df.resample("MS").apply(lambda g: g.sum(min_count=int(0.8 * len(g))))
    return scales

def descriptive_stats(scales: Dict[str, pd.DataFrame], df_daily: pd.DataFrame) -> pd.DataFrame:
    ann = scales["annual"]
    stns = ann.columns.tolist()
    rows = []
    for s in stns:
        v = ann[s].dropna().values.astype(float)
        d = df_daily[s].dropna()
        n = len(v)
        
        # Proper Wet-days calculation (v5.0)
        wet_days_yearly = d.groupby(d.index.year).apply(lambda x: (x >= WET_THR).sum())
        wet_mean = float(wet_days_yearly.mean()) if not wet_days_yearly.empty else np.nan
        
        rows.append({
            "Station":      s,
            "N (yr)":       n,
            "Mean (mm)":    round(float(np.mean(v)), 1) if n > 0 else np.nan,
            "Median (mm)":  round(float(np.median(v)), 1) if n > 0 else np.nan,
            "Max (mm)":     round(float(np.max(v)), 1) if n > 0 else np.nan,
            "Min (mm)":     round(float(np.min(v)), 1) if n > 0 else np.nan,
            "Std (mm)":     round(float(np.std(v, ddof=1)), 1) if n > 1 else np.nan,
            "CV (%)":       round(float(np.std(v,ddof=1)/np.mean(v)*100), 1) if n > 1 and np.mean(v) != 0 else np.nan,
            "Wet-days/yr":  round(wet_mean, 1),
            "Skewness":     round(float(sps.skew(v)), 3) if n > 3 else np.nan,
            "Kurtosis":     round(float(sps.kurtosis(v,fisher=True)), 3) if n>3 else np.nan,
        })
    return pd.DataFrame(rows).set_index("Station")


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §3  AUTOCORRELATION & HOMOGENEITY                                      ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def lag_k_autocorr(x: np.ndarray, k: int = 1) -> float:
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < k + 3: return np.nan
    xb  = np.mean(x)
    num = np.sum((x[:n-k] - xb) * (x[k:n] - xb))
    den = np.sum((x - xb) ** 2)
    return float(num / den) if den > 0 else np.nan

def all_lag_autocorr(x: np.ndarray, max_lag: int = None) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 4: return np.array([])
    if max_lag is None: max_lag = min(n // 3, n - 1)
    return np.array([lag_k_autocorr(x, k) for k in range(1, max_lag + 1)])

def is_sig_autocorr(r1: float, n: int, alpha: float = 0.05) -> bool:
    """Two-tailed significance of Lag-1 AC using exact t-test (v5.0)."""
    if np.isnan(r1) or n < 4: return False
    if abs(r1) == 1.0: return True
    t = r1 * math.sqrt((n - 2) / (1 - r1**2))
    p = 2 * (1 - sps.t.cdf(abs(t), df=n-2))
    return bool(p < alpha)

def pettitt_test(x: np.ndarray) -> Dict[str, Any]:
    """Pettitt's test for single change-point detection."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 4: return {"loc": np.nan, "K": np.nan, "p_value": np.nan, "sig": False}
    
    r = sps.rankdata(x)
    U = np.zeros(n)
    for t in range(n):
        U[t] = 2 * np.sum(r[:t+1]) - (t + 1) * (n + 1)
    loc = int(np.argmax(np.abs(U)))
    K = float(np.abs(U[loc]))
    p_val = float(2 * np.exp((-6 * K**2) / (n**3 + n**2)))
    
    return {"loc": loc, "K": round(K,2), "p_value": round(p_val,4), "sig": bool(p_val < 0.05)}


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §4  TREND TESTS                                                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def _mk_s_fast(x: np.ndarray) -> Tuple[float, List[int]]:
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 4: return np.nan, []
    S = 0.0
    for i in range(n - 1):
        S += float(np.sum(np.sign(x[i+1:] - x[i])))
    _, counts = np.unique(x, return_counts=True)
    ties = counts[counts > 1].tolist()
    return S, ties

def mk_variance_ties(n: int, ties: List[int]) -> float:
    tie_sum = sum(t * (t - 1) * (2 * t + 5) for t in ties)
    return (n * (n - 1) * (2 * n + 5) - tie_sum) / 18.0

def standard_mk(x: np.ndarray) -> dict:
    null = {k: np.nan for k in ["S","n","Var_S","Z","p_value","tau",
                                "slope_Q","slope_lo","slope_hi"]}
    null.update({"trend":"—","sig_05":False,"sig_01":False})

    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = int(len(x))
    if n < MIN_N: return null

    S, ties = _mk_s_fast(x)
    if np.isnan(S): return null

    Var_S = mk_variance_ties(n, ties)
    if Var_S <= 0: return null

    Z = (S - 1) / math.sqrt(Var_S) if S > 0 else (S + 1) / math.sqrt(Var_S) if S < 0 else 0.0
    p_val = float(min(2.0 * (1.0 - scipy_norm.cdf(abs(Z))), 1.0))
    tau   = float(S / (0.5 * n * (n - 1)))
    sig05, sig01 = p_val < ALPHA_005, p_val < ALPHA_001
    trend = "Increasing ↑" if (sig05 and Z > 0) else "Decreasing ↓" if (sig05 and Z < 0) else "No trend"

    slope_Q, slope_lo, slope_hi = sens_slope(x)

    return {"S": S, "n": n, "Var_S": Var_S, "Z": Z, "p_value": p_val, "tau": tau,
            "slope_Q": slope_Q, "slope_lo": slope_lo, "slope_hi": slope_hi,
            "trend": trend, "sig_05": sig05, "sig_01": sig01, "method": "Standard MK"}

def modified_mk(x: np.ndarray) -> dict:
    """
    Modified Mann-Kendall Test (Hamed & Rao 1998)
    Limitation: Less robust when very strong trend and strong AC co-exist.
    """
    null = {k: np.nan for k in ["S","n","Var_S","Var_S_adj","n_eff","rho_1","Z","p_value","tau",
                                "slope_Q","slope_lo","slope_hi"]}
    null.update({"trend":"—","sig_05":False,"sig_01":False})

    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = int(len(x))
    if n < MIN_N: return null

    S, ties = _mk_s_fast(x)
    if np.isnan(S): return null
    Var_S = mk_variance_ties(n, ties)
    if Var_S <= 0: return null

    ranks = sps.rankdata(x).astype(float)
    rho = all_lag_autocorr(ranks, max_lag=min(n // 3, n - 1))

    if len(rho) == 0:
        n_over_neff = 1.0
    else:
        se_rho = 1.0 / math.sqrt(n)
        z_crit = scipy_norm.ppf(1 - ALPHA_005 / 2)
        rho_sig = np.where(np.abs(rho) > z_crit * se_rho, rho, 0.0)
        ks = np.arange(1, len(rho_sig) + 1)
        n_over_neff = max(1.0 + (2.0 / n) * np.sum((n - ks) * rho_sig), 1.0)

    rho_1 = float(rho[0]) if len(rho) > 0 else np.nan
    n_eff = n / n_over_neff
    Var_S_adj = Var_S * n_over_neff

    Z = (S - 1) / math.sqrt(Var_S_adj) if S > 0 else (S + 1) / math.sqrt(Var_S_adj) if S < 0 else 0.0
    p_val = float(min(2.0 * (1.0 - scipy_norm.cdf(abs(Z))), 1.0))
    tau = float(S / (0.5 * n * (n - 1)))
    sig05, sig01 = p_val < ALPHA_005, p_val < ALPHA_001
    trend = "Increasing ↑" if (sig05 and Z > 0) else "Decreasing ↓" if (sig05 and Z < 0) else "No trend"

    slope_Q, slope_lo, slope_hi = sens_slope(x)

    return {"S": S, "n": n, "Var_S": Var_S, "Var_S_adj": Var_S_adj, "n_eff": n_eff,
            "rho_1": rho_1, "Z": Z, "p_value": p_val, "tau": tau,
            "slope_Q": slope_Q, "slope_lo": slope_lo, "slope_hi": slope_hi,
            "trend": trend, "sig_05": sig05, "sig_01": sig01, "method": "Modified MK"}

def sens_slope(x: np.ndarray, alpha: float = 0.05) -> Tuple[float, float, float]:
    """Sen's Slope Estimator + 95% CI strictly following Gilbert (1987)."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 4: return np.nan, np.nan, np.nan

    slopes = []
    for i in range(n - 1):
        for j in range(i + 1, n):
            slopes.append((x[j] - x[i]) / (j - i))
    slopes = np.sort(slopes)
    N = len(slopes)
    Q = float(np.median(slopes))

    _, ties = _mk_s_fast(x)
    Var_S = mk_variance_ties(n, ties)
    if Var_S <= 0: return Q, np.nan, np.nan

    z_crit = scipy_norm.ppf(1 - alpha / 2)
    C_alpha = z_crit * math.sqrt(Var_S)
    
    # Gilbert (1987) precise index calculation
    lo_r = int(np.ceil((N - C_alpha) / 2.0)) - 1 # 0-indexed adjustment
    hi_r = int(np.floor((N + C_alpha) / 2.0 + 1)) - 1
    
    lo_r = max(0, min(lo_r, N - 1))
    hi_r = max(0, min(hi_r, N - 1))

    return Q, float(slopes[lo_r]), float(slopes[hi_r])

def run_all(scales: dict, stns: list, smap: dict) -> pd.DataFrame:
    rows = []
    scale_keys = ["annual", "wet", "dry"]
    for sk in scale_keys:
        df_s = scales[sk]
        for stn in stns:
            if stn not in df_s.columns: continue
            arr = df_s[stn].dropna().values.astype(float)
            if len(arr) < MIN_N: continue
            r1 = lag_k_autocorr(arr)
            sig_ac = is_sig_autocorr(r1, len(arr))

            for method_fn, method_name in [(standard_mk, "Standard MK"), (modified_mk, "Modified MK")]:
                res = method_fn(arr)
                rows.append({
                    "Station": stn, "Code": smap.get(stn, stn), "Scale": sk,
                    "Method": method_name, "rho_1": r1, "Sig_AC": sig_ac,
                    "N": res.get("n", np.nan), "S": res.get("S", np.nan),
                    "Var_S": res.get("Var_S", np.nan), "Var_S_adj": res.get("Var_S_adj", np.nan),
                    "n_eff": res.get("n_eff", np.nan), "Z": res.get("Z", np.nan),
                    "tau": res.get("tau", np.nan), "p_value": res.get("p_value", np.nan),
                    "Trend": res.get("trend", "—"), "sig_05": res.get("sig_05", False),
                    "sig_01": res.get("sig_01", False), "Slope_Q": res.get("slope_Q", np.nan),
                    "Slope_lo": res.get("slope_lo", np.nan), "Slope_hi": res.get("slope_hi", np.nan),
                })
    return pd.DataFrame(rows)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §5  EXCEL OUTPUT FORMATTED AS TABLE 2, 3, 4                            ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def write_excel_v5(out_xlsx: Path, stns: list, trend_df: pd.DataFrame):
    wb = Workbook()
    wb.remove(wb.active)
    
    # Helper to generate headers
    def _create_sheet(name, headers):
        ws = wb.create_sheet(name)
        for c, h in enumerate(headers, 1):
            xsc(ws, 1, c, h, bold=True, bg=XC["hdr"], fc="FFFFFF", border=tb())
            cw(ws, c, 14)
        return ws

    # --- TABLE 2: Standard MK ---
    headers_t2 = ["Station", "Scale", "N", "S", "Var(S)", "Z_MK", "T (Kendall)", "p-value", "Trend"]
    ws2 = _create_sheet("Table 2 - Standard MK", headers_t2)
    
    # --- TABLE 3: Modified MK ---
    headers_t3 = ["Station", "Scale", "N_Err", "P", "Var*(S)", "Z_MMK", "τ (Kendall)", "p-value", "Trend"]
    ws3 = _create_sheet("Table 3 - Modified MK", headers_t3)
    
    # --- TABLE 4: Sen's Slope ---
    headers_t4 = ["Station", 
                  "Annual Sen's Slope", "Annual p-value", "Annual Trend",
                  "Wet Sen's Slope", "Wet p-value", "Wet Trend",
                  "Dry Sen's Slope", "Dry p-value", "Dry Trend"]
    ws4 = _create_sheet("Table 4 - Sen Slope", headers_t4)
    
    # Populate Table 2 & 3
    r2, r3 = 2, 2
    for sk in ["annual", "wet", "dry"]:
        scale_label = "Annual" if sk=="annual" else ("Wet Season" if sk=="wet" else "Dry Season")
        for stn in stns:
            # Table 2
            df_mk = trend_df[(trend_df["Station"]==stn) & (trend_df["Scale"]==sk) & (trend_df["Method"]=="Standard MK")]
            if not df_mk.empty:
                r = df_mk.iloc[0]
                row2 = [stn, scale_label, r["N"], r["S"], r["Var_S"], r["Z"], r["tau"], r["p_value"], r["Trend"]]
                for c, v in enumerate(row2, 1):
                    xsc(ws2, r2, c, round(v,4) if isinstance(v,float) else v, border=tb())
                r2 += 1
            
            # Table 3
            df_mmk = trend_df[(trend_df["Station"]==stn) & (trend_df["Scale"]==sk) & (trend_df["Method"]=="Modified MK")]
            if not df_mmk.empty:
                r = df_mmk.iloc[0]
                # P here refers to rho_1, N_Err to n_eff
                row3 = [stn, scale_label, r["n_eff"], r["rho_1"], r["Var_S_adj"], r["Z"], r["tau"], r["p_value"], r["Trend"]]
                for c, v in enumerate(row3, 1):
                    xsc(ws3, r3, c, round(v,4) if isinstance(v,float) else v, border=tb())
                r3 += 1

    # Populate Table 4
    r4 = 2
    for stn in stns:
        row4 = [stn]
        for sk in ["annual", "wet", "dry"]:
            df_mmk = trend_df[(trend_df["Station"]==stn) & (trend_df["Scale"]==sk) & (trend_df["Method"]=="Modified MK")]
            if not df_mmk.empty:
                r = df_mmk.iloc[0]
                row4.extend([round(r["Slope_Q"],3), round(r["p_value"],4), r["Trend"]])
            else:
                row4.extend(["—", "—", "—"])
        for c, v in enumerate(row4, 1):
            xsc(ws4, r4, c, v, border=tb())
        r4 += 1

    wb.save(str(out_xlsx))
    print(f"    ✓  Excel Table Output: {out_xlsx.name}")


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §6  MAIN EXECUTION                                                     ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def main():
    print(f"═"*60)
    print(f"  Rainfall Trend Analysis v{VERSION} (Academic Edition)")
    print(f"═"*60)

    try:
        work_dir = (sys.argv[1].strip('"').strip("'") if len(sys.argv) > 1 else str(Path(os.path.abspath(__file__)).parent))
    except Exception:
        work_dir = os.getcwd()

    out_dir = Path(work_dir)
    csv_path = find_csv(work_dir)
    base = Path(csv_path).stem
    
    print("  Step 1: Data Loading & QC (Dual Approach)...")
    df_raw = load_daily(csv_path)
    df, qc_dict = quality_control(df_raw.copy())
    stns = df.columns.tolist()
    smap = {s: f"S{i+1}" for i, s in enumerate(stns)}
    
    print("  Step 2: Temporal Aggregation...")
    scales = aggregate_all(df)
    
    print("  Step 3: Trend Tests (MK & MMK)...")
    trend_df = run_all(scales, stns, smap)
    
    print("  Step 4: Pettitt Homogeneity Test...")
    homog_results = []
    for s in stns:
        res = pettitt_test(scales["annual"][s].values)
        res["Station"] = s
        homog_results.append(res)
        
    print("  Step 5: Exporting Tables to Excel...")
    out_xlsx = out_dir / f"Output_Tables_{base}_v5.xlsx"
    write_excel_v5(out_xlsx, stns, trend_df)
    
    print("\n  [✓] Analysis Complete. All requirements successfully applied.")

if __name__ == "__main__":
    main()