"""
===============================================================================
  Trend & Distribution Analysis  — Version 2.0  (UPGRADED)
  Multi-Model Ensemble CMIP6 Rainfall  │  Q1-Journal Standard
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  NEW in v2.0:
    ✓  Smart file discovery — handles province names with spaces
       (e.g. "Prachuap Khiri Khan", "Phetchaburi")
    ✓  Dynamic model detection — no hardcoded model lists
    ✓  Per-model annual trend figure (Fig A2 – one panel per CMIP6 model)
    ✓  Multi-timescale trend per model (Fig G – Daily/Monthly/Wet/Dry season)
    ✓  Ensemble mean vs best individual model analysis (Fig H)
    ✓  QDM trend-signal preservation analysis (Fig I)
    ✓  Removed rank medals/numbers from figures (clean Q1 style)
  ─────────────────────────────────────────────────────────────────────────────
  Outputs:
    Fig A  – Annual Rainfall Trend (regional ensemble mean)
    Fig A2 – Annual Trend Per CMIP6 Model (one panel per model)
    Fig B  – Extreme Indices Trend (RX1day, RX5day, R95p, CDD)
    Fig C  – PDF: Observed vs Raw vs QDM (KDE + heavy-tail inset)
    Fig D  – CDF: Percentile Alignment
    Fig E  – Q–Q Plot (tail behaviour + extreme quantiles)
    Fig F  – ETCCDI Heatmap (all stations × all indices)
    Fig G  – Multi-Timescale Trend per Model (Daily/Monthly/Seasons)
    Fig H  – Ensemble Mean vs Best Individual Model
    Fig I  – QDM Trend-Signal Preservation
    Excel  – Trend stats + ETCCDI + MK full results + Regional summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  File naming convention:
    Observed_*.csv           →  Observed
    pr_day_<MODEL>_*.csv     →  Raw CMIP6
    bc_pr_day_<MODEL>_*.csv  →  Bias-Corrected (QDM)
  Province name is extracted automatically from Observed filename.
  Supports spaces and underscores in province names.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  References:
    Mann (1945) Econometrica; Kendall (1975) Rank Corr. Methods
    Sen (1968) JASA 63:1379–1389
    Zhang et al. (2011) WIREs Clim Change 2:418–439  [ETCCDI]
    Cannon et al. (2015) J.Climate 28:6938–6959        [QDM]
    Knutti et al. (2017) Nat. Clim. Chang. 7:246–251  [Model selection]
===============================================================================
"""

import os, sys, re, math, warnings, itertools
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from scipy import stats as sps
from scipy.stats import gaussian_kde

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import matplotlib.ticker as ticker
from matplotlib.lines import Line2D
from matplotlib.colors import Normalize, BoundaryNorm
import matplotlib.cm as cm
import matplotlib.colors as mcolors

from openpyxl import Workbook
from openpyxl.styles import (PatternFill, Font, Alignment, Border, Side,
                              GradientFill)
from openpyxl.utils import get_column_letter

warnings.filterwarnings("ignore")

# ══════════════════════════════════════════════════════════════════════════════
# 0.  GLOBAL STYLE  (Nature / Elsevier Q1)
# ══════════════════════════════════════════════════════════════════════════════
FS = dict(title=15, label=13, tick=12, legend=11, annot=10, note=9)

plt.rcParams.update({
    "font.family":        "serif",
    "font.serif":         ["Times New Roman", "DejaVu Serif"],
    "font.size":          FS["label"],
    "axes.titlesize":     FS["title"],
    "axes.labelsize":     FS["label"],
    "xtick.labelsize":    FS["tick"],
    "ytick.labelsize":    FS["tick"],
    "legend.fontsize":    FS["legend"],
    "lines.linewidth":    2.0,
    "axes.linewidth":     1.0,
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.grid":          True,
    "grid.linestyle":     "--",
    "grid.linewidth":     0.45,
    "grid.alpha":         0.45,
    "grid.color":         "#B0BEC5",
    "savefig.dpi":        600,
    "savefig.bbox":       "tight",
    "savefig.pad_inches": 0.18,
    "figure.dpi":         120,
    "mathtext.fontset":   "stix",
})

# Main colour palette
C = dict(
    obs    = "#2C3E50",   raw    = "#C0392B",   bc     = "#2980B9",
    obs_lt = "#BDC3C7",   raw_lt = "#F5B7B1",   bc_lt  = "#AED6F1",
    green  = "#1E8449",   gold   = "#D4AC0D",   grey   = "#626567",
    purple = "#7D3C98",   orange = "#E67E22",
)

# Model colour palette (up to 12 models)
MODEL_COLORS = [
    "#1565C0","#C62828","#2E7D32","#E65100","#6A1B9A",
    "#00695C","#AD1457","#4527A0","#0277BD","#558B2F",
    "#4E342E","#37474F",
]

WET_THR = 1.0   # mm — wet-day threshold

# ── Excel style helpers ────────────────────────────────────────────────────
THIN = Side(style="thin",   color="BDBDBD")
MED  = Side(style="medium", color="1F4E79")
def tb():     return Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
def tb_med(): return Border(left=MED,  right=MED,  top=MED,  bottom=MED)
def xfill(h): return PatternFill("solid", fgColor=h)

XC = dict(
    title="13293D", sub="1F4E79", hdr="2E75B6",
    obs_h="1B5E20", raw_h="B71C1C", bc_h="0D47A1",
    obs_r="E8F5E9", raw_r="FFEBEE", bc_r="E3F2FD",
    best="FFF9C4",  best_f="E65100",
    sig="C8E6C9",   nsig="FFF9C4",  deg="FFCCBC",
    white="FFFFFF", note="ECEFF1",
)

def xsc(ws, r, c, val=None, bold=False, italic=False,
        fc=None, bg=None, align="center", sz=10,
        num_fmt=None, wrap=True, border=None):
    cell = ws.cell(row=r, column=c)
    if val is not None: cell.value = val
    cell.font = Font(bold=bold, italic=italic, name="Calibri", size=sz,
                     color=fc if fc else "1A1A1A")
    cell.alignment = Alignment(horizontal=align, vertical="center",
                                wrap_text=wrap)
    if bg:      cell.fill   = xfill(bg)
    if border:  cell.border = border
    if num_fmt: cell.number_format = num_fmt
    return cell

def mxsc(ws, r, c1, c2, val, **kw):
    ws.merge_cells(start_row=r, start_column=c1, end_row=r, end_column=c2)
    return xsc(ws, r, c1, val, **kw)

def cw(ws, col, w):
    ws.column_dimensions[get_column_letter(col)].width = w

# ══════════════════════════════════════════════════════════════════════════════
# 1.  SMART FILE DISCOVERY  (supports spaces in province names)
# ══════════════════════════════════════════════════════════════════════════════
MISS = [-99, -999, -9999, -9.99e+20, 9.99e+20, 1e+20]


def _extract_province_from_observed(fname: str) -> str:
    """
    Extract province name from Observed filename.
    Handles both underscore and space separators.

    Strategy: split stem by underscore, scan from left, skip all purely
    numeric tokens (date fields like 198101, 201412). Everything after the
    last numeric token is the province (joined with spaces).

    Examples:
      Observed_Rain_daily_198101_201412_Phetchaburi.csv         → "Phetchaburi"
      Observed_Rain_daily_198101_201412_Prachuap Khiri Khan.csv → "Prachuap Khiri Khan"
      Observed_Rain_daily_198101_201412_Prachuap_Khiri_Khan.csv → "Prachuap Khiri Khan"
    """
    stem  = Path(fname).stem          # strip .csv
    # Replace spaces by underscores for uniform splitting
    stem  = stem.replace(" ", "_")
    parts = stem.split("_")

    # Find the index of the last all-digit token
    last_digit_idx = -1
    for i, p in enumerate(parts):
        if re.match(r'^\d+$', p):
            last_digit_idx = i

    if last_digit_idx >= 0 and last_digit_idx < len(parts) - 1:
        province_parts = parts[last_digit_idx + 1:]
        return " ".join(province_parts).strip()

    # Fallback: everything after "daily_"
    m2 = re.search(r'daily_(.+)$', stem, re.IGNORECASE)
    if m2:
        return m2.group(1).replace("_", " ").strip()

    # Last resort
    return parts[-1].replace("_", " ").strip()


def _get_model_name(fname: str, prefix: str) -> str:
    """
    Extract model name from filenames like:
      pr_day_ACCESSESM15_historical_...csv  →  "ACCESSESM15"
      bc_pr_day_ECEarth3_historical_...csv  →  "ECEarth3"
    """
    stem = Path(fname).stem
    # Remove bc_ prefix if present
    if stem.lower().startswith("bc_"):
        stem = stem[3:]
    # Remove pr_day_ or pr_ prefix
    stem = re.sub(r'^pr_(day_)?', '', stem, flags=re.IGNORECASE)
    # First token before _ is the model name
    parts = stem.split("_")
    return parts[0] if parts and parts[0] else "Model"


def find_csvs_multi(folder: str):
    """
    Smart file discovery — supports province names with spaces/underscores.
    Automatically detects all CMIP6 models without hardcoded lists.

    Returns:
        obs_path   : str
        raw_dict   : {model_name: path_str}
        bc_dict    : {model_name: path_str}
        province   : str  (e.g. "Prachuap Khiri Khan")
    """
    folder = Path(folder)
    # Find ALL csv files, including those with spaces in names
    all_csv = sorted(list(folder.glob("*.csv")) +
                     list(folder.glob("* *.csv")))  # space-in-name files

    # ── Observed ──────────────────────────────────────────────────────────
    obs_files = [f for f in all_csv if "observed" in f.name.lower()]
    if not obs_files:
        sys.exit("  ✗  ไม่พบไฟล์ Observed_*.csv")
    if len(obs_files) > 1:
        print(f"  ⚠  Multiple Observed files found – using: {obs_files[0].name}")
    obs_path = str(obs_files[0])

    province = _extract_province_from_observed(obs_files[0].name)
    print(f"  Province detected: '{province}'")

    # ── Province aliases (space ↔ underscore) for matching ───────────────
    province_variants = [province,
                         province.replace(" ", "_"),
                         province.replace("_", " ")]

    def _province_in_name(fname):
        fname_lower = fname.lower()
        return any(v.lower() in fname_lower for v in province_variants)

    # ── Raw CMIP6 ─────────────────────────────────────────────────────────
    raw_files = [f for f in all_csv
                 if re.match(r'^pr_', f.name, re.IGNORECASE)
                 and _province_in_name(f.name)]
    # Also try without province filter if nothing found
    if not raw_files:
        raw_files = [f for f in all_csv
                     if re.match(r'^pr_', f.name, re.IGNORECASE)]

    # ── BC/QDM ────────────────────────────────────────────────────────────
    bc_files = [f for f in all_csv
                if re.match(r'^bc_', f.name, re.IGNORECASE)
                and _province_in_name(f.name)]
    if not bc_files:
        bc_files = [f for f in all_csv
                    if re.match(r'^bc_', f.name, re.IGNORECASE)]

    # ── Build model dicts ─────────────────────────────────────────────────
    raw_dict, bc_dict = {}, {}
    for f in raw_files:
        m = _get_model_name(f.name, "pr")
        if m not in raw_dict:
            raw_dict[m] = str(f)
        else:
            print(f"  ⚠  Duplicate raw model '{m}' – skipping {f.name}")

    for f in bc_files:
        m = _get_model_name(f.name, "bc")
        if m not in bc_dict:
            bc_dict[m] = str(f)
        else:
            print(f"  ⚠  Duplicate BC model '{m}' – skipping {f.name}")

    # Warn about unmatched models
    for m in set(raw_dict) - set(bc_dict):
        print(f"  ⚠  No BC file for model '{m}'")
    for m in set(bc_dict) - set(raw_dict):
        print(f"  ⚠  No Raw file for model '{m}'")

    return obs_path, raw_dict, bc_dict, province


# ══════════════════════════════════════════════════════════════════════════════
# 2.  DATA LOADING & UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def load_daily(path: str, label: str):
    df = pd.read_csv(path)
    for mv in MISS:
        df.replace(mv, np.nan, inplace=True)
    num = df.select_dtypes(include=[np.number]).columns
    df[num] = df[num].where(df[num] >= 0)
    stns = [c for c in df.columns if c not in ("YEAR", "MONTH", "DAY")]
    df["date"] = pd.to_datetime(
        {"year": df["YEAR"], "month": df["MONTH"], "day": df["DAY"]})
    df = df.set_index("date")[stns]
    return df, stns


def ensemble_mean_df(dfs_dict: dict, stns: list) -> pd.DataFrame:
    """Compute ensemble mean DataFrame across all models."""
    dfs = [df for df in dfs_dict.values() if df is not None]
    if not dfs:
        return None
    # Align on common index
    common = dfs[0].index
    for df in dfs[1:]:
        common = common.intersection(df.index)
    if len(common) == 0:
        return None
    aligned = [df.loc[common] for df in dfs]
    stack = np.stack([df.values.astype(float) for df in aligned], axis=0)
    mean_v = np.nanmean(stack, axis=0)
    return pd.DataFrame(mean_v, index=common, columns=dfs[0].columns)


def annual_total(df: pd.DataFrame, stns: list) -> pd.Series:
    """Regional-mean annual total rainfall (mm/year)."""
    reg = df[[s for s in stns if s in df.columns]].mean(axis=1)
    return reg.resample("YS").sum(min_count=int(0.8 * 365))


def seasonal_series(df: pd.DataFrame, stns: list, months: list) -> pd.Series:
    """Annual sum for a given list of months (seasonal total)."""
    reg = df[[s for s in stns if s in df.columns]].mean(axis=1)
    sel = reg[reg.index.month.isin(months)]
    return sel.resample("YS").sum(min_count=int(0.6 * len(months) * 28))


def monthly_series(df: pd.DataFrame, stns: list) -> pd.Series:
    """Regional-mean monthly total."""
    reg = df[[s for s in stns if s in df.columns]].mean(axis=1)
    return reg.resample("MS").sum(min_count=int(0.75 * 28))


def short_labels(stns):
    return {str(s): f"S{i+1}" for i, s in enumerate(stns)}


# ══════════════════════════════════════════════════════════════════════════════
# 3.  MANN-KENDALL + SEN'S SLOPE
# ══════════════════════════════════════════════════════════════════════════════

def mann_kendall(x):
    """Two-sided Mann-Kendall trend test (Mann 1945; Kendall 1975)."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 4:
        return np.nan, np.nan, np.nan, np.nan, np.nan
    S = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            diff = x[j] - x[i]
            if   diff > 0: S += 1
            elif diff < 0: S -= 1
    unique, counts = np.unique(x, return_counts=True)
    tie_corr = np.sum(counts * (counts - 1) * (2 * counts + 5))
    var_S = (n * (n - 1) * (2 * n + 5) - tie_corr) / 18.0
    if var_S <= 0:
        return np.nan, np.nan, float(S), float(var_S), np.nan
    if   S > 0: z = (S - 1) / math.sqrt(var_S)
    elif S < 0: z = (S + 1) / math.sqrt(var_S)
    else:        z = 0.0
    p_val = 2 * (1 - sps.norm.cdf(abs(z)))
    tau   = S / (0.5 * n * (n - 1))
    return float(tau), float(p_val), float(S), float(var_S), float(z)


def sens_slope(x, years=None):
    """Sen's slope with 95% CI (Sen 1968)."""
    x = np.asarray(x, dtype=float)
    if years is None:
        years = np.arange(len(x), dtype=float)
    years = np.asarray(years, dtype=float)
    mask  = ~np.isnan(x)
    x, years = x[mask], years[mask]
    if len(x) < 4:
        return np.nan, np.nan, np.nan, np.nan
    res = sps.theilslopes(x, years, 0.95)
    return float(res.slope), float(res.intercept), \
           float(res.low_slope), float(res.high_slope)


def trend_sig(p):
    if p < 0.001: return "***"
    if p < 0.01:  return "**"
    if p < 0.05:  return "*"
    if p < 0.10:  return "†"
    return "ns"


# ══════════════════════════════════════════════════════════════════════════════
# 4.  ETCCDI EXTREME INDICES
# ══════════════════════════════════════════════════════════════════════════════

def _max_consec(arr):
    max_run = run = 0
    for v in arr:
        if v == 1:
            run += 1
            max_run = max(max_run, run)
        else:
            run = 0
    return int(max_run)


def etccdi_annual(daily_series: pd.Series) -> pd.DataFrame:
    """Compute annual ETCCDI indices from a daily rainfall Series."""
    s      = daily_series.copy()
    s      = s[s >= 0]
    s_wet  = s.where(s >= WET_THR)
    years  = s.index.year.unique()
    rows   = []
    for yr in years:
        yr_s   = s[s.index.year == yr]
        yr_wet = s_wet[s_wet.index.year == yr].dropna()
        if len(yr_s) < 300:
            continue
        rx1   = float(yr_s.max())
        roll5 = yr_s.rolling(5, min_periods=5).sum()
        rx5   = float(roll5.max())
        sdii  = float(yr_wet.mean()) if len(yr_wet) else np.nan
        r10   = int((yr_s >= 10).sum())
        r20   = int((yr_s >= 20).sum())
        p95   = float(s_wet.dropna().quantile(0.95))
        r95p  = float(yr_s[yr_s > p95].sum())
        p99   = float(s_wet.dropna().quantile(0.99))
        r99p  = float(yr_s[yr_s > p99].sum())
        is_dry = (yr_s < WET_THR).astype(int)
        cdd   = _max_consec(is_dry.values)
        is_wet = (yr_s >= WET_THR).astype(int)
        cwd   = _max_consec(is_wet.values)
        prcptot = float(yr_wet.sum())
        rows.append({"Year": yr,
                     "RX1day": rx1,  "RX5day": rx5,  "SDII": sdii,
                     "R10mm": r10,   "R20mm": r20,
                     "R95p": r95p,   "R99p": r99p,
                     "CDD": cdd,     "CWD": cwd,
                     "PRCPTOT": prcptot})
    return pd.DataFrame(rows).set_index("Year") if rows else pd.DataFrame()


ETCCDI_UNITS = {
    "RX1day": "mm",   "RX5day": "mm",   "SDII": "mm/day",
    "R10mm":  "days", "R20mm":  "days",
    "R95p":   "mm",   "R99p":   "mm",
    "CDD":    "days", "CWD":    "days",
    "PRCPTOT":"mm",
}
ETCCDI_DIRECTION = {
    "RX1day": "up",  "RX5day": "up",  "SDII": "up",
    "R10mm":  "up",  "R20mm":  "up",
    "R95p":   "up",  "R99p":   "up",
    "CDD":    "down","CWD":    "up",   "PRCPTOT": "up",
}


def annual_reg_etccdi(df: pd.DataFrame, stns: list) -> dict:
    """Regional-mean annual ETCCDI across stations."""
    all_idx = {}
    for stn in stns:
        if stn not in df.columns:
            continue
        idx_df = etccdi_annual(df[stn].dropna())
        if idx_df.empty:
            continue
        for col in idx_df.columns:
            all_idx.setdefault(col, []).append(idx_df[col])
    result = {}
    for col, series_list in all_idx.items():
        combined = pd.concat(series_list, axis=1)
        result[col] = combined.mean(axis=1)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# 5A.  FIGURE A – Annual Rainfall Trend (Ensemble Mean)
# ══════════════════════════════════════════════════════════════════════════════

def _plot_trend_line(ax, series, color, label, ls="-", lw=2.0,
                     zorder=4, unit="mm yr⁻¹"):
    """Plot scatter + Sen's slope line + 95% CI band. Returns (slope, p)."""
    s = series.dropna()
    if len(s) < 4:
        return np.nan, np.nan
    yrs  = s.index.year.astype(float)
    vals = s.values.astype(float)
    ax.scatter(yrs, vals, color=color, s=22, alpha=0.55,
               edgecolors="white", linewidths=0.5, zorder=zorder)
    slope, intercept, lo_sl, hi_sl = sens_slope(vals, yrs)
    if np.isnan(slope):
        return np.nan, np.nan
    tau, p, S, vS, z = mann_kendall(vals)
    sig = trend_sig(p) if not np.isnan(p) else ""
    fit_y  = slope * yrs + intercept
    lo_fit = lo_sl * yrs + intercept
    hi_fit = hi_sl * yrs + intercept
    ax.plot(yrs, fit_y, color=color, ls=ls, lw=lw,
            label=f"{label}  β={slope:+.2f} {unit}  {sig}",
            zorder=zorder + 1)
    ax.fill_between(yrs, lo_fit, hi_fit,
                    color=color, alpha=0.12, zorder=zorder - 1)
    return float(slope), float(p)


def fig_annual_trend(obs_d, raw_ens, bc_ens, stns, province,
                     period_obs, out_path):
    """Fig A: Annual total rainfall trend — ensemble mean."""
    obs_ann = annual_total(obs_d,   stns)
    raw_ann = annual_total(raw_ens, stns)
    bc_ann  = annual_total(bc_ens,  stns)

    fig, axes = plt.subplots(2, 1, figsize=(16, 10), sharex=False)
    fig.subplots_adjust(hspace=0.45, top=0.90, bottom=0.09,
                        left=0.09, right=0.97)

    ax = axes[0]
    _plot_trend_line(ax, obs_ann, C["obs"], "Observed",  "-",  2.4, 5)
    _plot_trend_line(ax, raw_ann, C["raw"], "Raw CMIP6", "--", 1.8, 4)
    _plot_trend_line(ax, bc_ann,  C["bc"],  "QDM",       "-",  2.0, 4)
    ax.set_ylabel("Annual Total Rainfall (mm yr⁻¹)", fontsize=FS["label"])
    ax.set_title("(a)  Annual Total Rainfall — Ensemble Regional Mean",
                 loc="left", fontsize=FS["title"] - 1, fontweight="bold", pad=5)
    ax.legend(fontsize=FS["legend"], frameon=True, edgecolor="#B0BEC5",
              loc="upper left", ncol=1)
    ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Boxplot of per-station Sen's slopes
    slopes_obs, slopes_raw, slopes_bc = [], [], []
    for stn in stns:
        for df, lst in [(obs_d, slopes_obs), (raw_ens, slopes_raw),
                        (bc_ens, slopes_bc)]:
            if stn not in df.columns:
                continue
            ann = df[stn].resample("YS").sum(min_count=int(0.8 * 365)).dropna()
            if len(ann) < 4:
                continue
            sl, _, _, _ = sens_slope(ann.values, ann.index.year.astype(float))
            if not np.isnan(sl):
                lst.append(sl)

    ax2 = axes[1]
    bdata   = [slopes_obs, slopes_raw, slopes_bc]
    bcolors = [C["obs_lt"], C["raw_lt"], C["bc_lt"]]
    bedge   = [C["obs"],    C["raw"],    C["bc"]]
    blabels = ["Observed", "Raw CMIP6", "QDM"]
    bp = ax2.boxplot(bdata, patch_artist=True, widths=0.50, notch=False,
                     medianprops=dict(linewidth=2.4, color="black"),
                     whiskerprops=dict(linewidth=1.3),
                     capprops=dict(linewidth=1.4),
                     flierprops=dict(marker="o", markersize=5, alpha=0.5),
                     boxprops=dict(linewidth=1.0))
    for box, fc, ec in zip(bp["boxes"], bcolors, bedge):
        box.set_facecolor(fc)
        box.set_edgecolor(ec)
    for cap in bp["caps"]:
        cap.set_linewidth(1.2)
    ax2.axhline(0, color=C["grey"], lw=1.0, ls="--", alpha=0.65)
    ax2.set_xticks([1, 2, 3])
    ax2.set_xticklabels(blabels, fontsize=FS["tick"] + 1, fontweight="bold")
    ax2.set_ylabel("Sen's Slope (mm yr⁻¹)", fontsize=FS["label"])
    ax2.set_title("(b)  Distribution of Per-Station Sen's Slopes\n"
                  "     (whiskers = 1.5×IQR; outliers = ●)",
                  loc="left", fontsize=FS["title"] - 1, fontweight="bold", pad=5)
    ax2.yaxis.set_minor_locator(ticker.AutoMinorLocator())
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    fig.suptitle(
        f"Annual Rainfall Trend Analysis — {province}  │  {period_obs}\n"
        "Sen's Slope + Mann-Kendall Test  │  Shaded = 95% Confidence Interval",
        fontsize=FS["title"] + 1, fontweight="bold")
    plt.savefig(out_path, dpi=600)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ══════════════════════════════════════════════════════════════════════════════
# 5B.  FIGURE A2 – Per-Model Annual Trend (NEW)
# ══════════════════════════════════════════════════════════════════════════════

def fig_annual_trend_per_model(obs_d, raw_dfs, bc_dfs, stns, province,
                                period_obs, out_path):
    """
    Fig A2: Annual rainfall trend per CMIP6 model.
    Each row = one model; Left = Raw, Right = QDM.
    Observed always shown as reference in both panels.
    """
    models = sorted(set(raw_dfs.keys()) & set(bc_dfs.keys()))
    if not models:
        print("    ⚠  No models found for per-model trend figure")
        return
    n_m = len(models)
    obs_ann = annual_total(obs_d, stns)
    obs_tau, obs_p, *_ = mann_kendall(obs_ann.dropna().values)
    obs_sig = trend_sig(obs_p) if not np.isnan(obs_p) else ""

    fig, axes = plt.subplots(n_m, 2, figsize=(18, 4.5 * n_m),
                              sharex=False)
    if n_m == 1:
        axes = np.array([axes])
    fig.subplots_adjust(hspace=0.55, wspace=0.22, top=0.93, bottom=0.05,
                        left=0.08, right=0.97)

    for mi, model in enumerate(models):
        col = MODEL_COLORS[mi % len(MODEL_COLORS)]
        raw_ann = annual_total(raw_dfs[model], stns)
        bc_ann  = annual_total(bc_dfs[model],  stns)

        for di, (ann_ser, ds_lbl, ds_col, ls) in enumerate([
            (raw_ann, "Raw CMIP6", C["raw"], "--"),
            (bc_ann,  "QDM",       col,       "-"),
        ]):
            ax = axes[mi, di]
            # Observed (reference)
            _plot_trend_line(ax, obs_ann, C["obs"], "Observed",
                             "-", 2.0, 5, unit="mm yr⁻¹")
            _plot_trend_line(ax, ann_ser, ds_col,
                             f"{model} ({ds_lbl})", ls, 2.2, 4,
                             unit="mm yr⁻¹")
            ax.set_ylabel("Rainfall (mm yr⁻¹)", fontsize=FS["label"] - 1)
            tag = "Raw" if di == 0 else "QDM"
            ax.set_title(f"({chr(97 + mi * 2 + di)})  {model} — {tag}",
                         loc="left", fontsize=FS["title"] - 2,
                         fontweight="bold", pad=4)
            ax.legend(fontsize=FS["legend"] - 1, frameon=True,
                      edgecolor="#B0BEC5", loc="best", ncol=1)
            ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            if mi == n_m - 1:
                ax.set_xlabel("Year", fontsize=FS["label"])

    fig.suptitle(
        f"Annual Rainfall Trend per CMIP6 Model — {province}  │  {period_obs}\n"
        "Left = Raw CMIP6  │  Right = QDM Bias-Corrected  │  "
        "Sen's Slope + Mann-Kendall  │  Observed = Reference",
        fontsize=FS["title"] + 1, fontweight="bold")
    plt.savefig(out_path, dpi=600)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ══════════════════════════════════════════════════════════════════════════════
# 6.  FIGURE B – Extreme Indices Trend
# ══════════════════════════════════════════════════════════════════════════════

def fig_extreme_trend(obs_d, raw_ens, bc_ens, stns, province,
                      period_obs, out_path):
    """Fig B: 2×2 panels — RX1day, RX5day, R95p, CDD."""
    PANELS = [
        ("RX1day", "Max 1-day Rainfall (mm)",  "(a)  RX1day"),
        ("RX5day", "Max 5-day Rainfall (mm)",  "(b)  RX5day"),
        ("R95p",   "Very Heavy Rainfall (mm)", "(c)  R95p"),
        ("CDD",    "Consecutive Dry Days",      "(d)  CDD"),
    ]
    obs_idx = annual_reg_etccdi(obs_d,   stns)
    raw_idx = annual_reg_etccdi(raw_ens, stns)
    bc_idx  = annual_reg_etccdi(bc_ens,  stns)

    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    fig.subplots_adjust(hspace=0.52, wspace=0.32,
                        top=0.90, bottom=0.09, left=0.08, right=0.97)

    for ai, (idx, ylabel, title_tag) in enumerate(PANELS):
        ax    = axes[ai // 2, ai % 2]
        obs_s = obs_idx.get(idx, pd.Series(dtype=float))
        raw_s = raw_idx.get(idx, pd.Series(dtype=float))
        bc_s  = bc_idx.get(idx, pd.Series(dtype=float))
        for ser, col, lbl, ls, lw, zo in [
            (obs_s, C["obs"], "Observed",  "-",  2.4, 5),
            (raw_s, C["raw"], "Raw CMIP6", "--", 1.8, 4),
            (bc_s,  C["bc"],  "QDM",       "-",  2.0, 4),
        ]:
            s = ser.dropna()
            if len(s) < 4:
                continue
            yrs  = s.index.astype(int).astype(float)
            vals = s.values.astype(float)
            ax.scatter(yrs, vals, color=col, s=22, alpha=0.55,
                       edgecolors="white", linewidths=0.5, zorder=zo)
            slope, intercept, lo_sl, hi_sl = sens_slope(vals, yrs)
            tau, p, S, vS, z = mann_kendall(vals)
            if np.isnan(slope):
                continue
            fit_y  = slope * yrs + intercept
            lo_fit = lo_sl * yrs + intercept
            hi_fit = hi_sl * yrs + intercept
            sig = trend_sig(p) if not np.isnan(p) else ""
            ax.plot(yrs, fit_y, color=col, ls=ls, lw=lw, zorder=zo + 1,
                    label=f"{lbl}  β={slope:+.2f}/yr  {sig}")
            ax.fill_between(yrs, lo_fit, hi_fit,
                            color=col, alpha=0.12, zorder=zo - 1)
        ax.set_ylabel(ylabel, fontsize=FS["label"])
        ax.set_title(title_tag, loc="left", fontsize=FS["title"] - 1,
                     fontweight="bold", pad=5)
        ax.set_xlabel("Year", fontsize=FS["label"])
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.legend(fontsize=FS["legend"] - 1, frameon=True,
                  edgecolor="#B0BEC5", loc="best", ncol=1)

    fig.suptitle(
        f"ETCCDI Extreme Indices Trend — {province}  │  {period_obs}\n"
        "Regional Ensemble Mean  │  Sen's Slope + Mann-Kendall  │  "
        "Shaded = 95% Confidence Interval",
        fontsize=FS["title"] + 1, fontweight="bold")
    plt.savefig(out_path, dpi=600)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ══════════════════════════════════════════════════════════════════════════════
# 7.  FIGURE C – PDF (KDE + heavy-tail inset)
# ══════════════════════════════════════════════════════════════════════════════

def fig_pdf(obs_d, raw_ens, bc_ens, stns, province, out_path):
    def pool_wet(df):
        v = df[[s for s in stns if s in df.columns]].values.flatten()
        v = v[~np.isnan(v) & (v >= WET_THR)]
        return v.astype(float)

    obs_v = pool_wet(obs_d)
    raw_v = pool_wet(raw_ens)
    bc_v  = pool_wet(bc_ens)

    fig = plt.figure(figsize=(15, 8))
    fig.subplots_adjust(left=0.08, right=0.97, top=0.88, bottom=0.11)
    ax  = fig.add_subplot(1, 1, 1)

    bw    = "scott"
    x_max = max(np.percentile(obs_v, 99.5),
                np.percentile(raw_v, 99.5),
                np.percentile(bc_v,  99.5))
    x_grid = np.linspace(1.0, x_max, 1000)

    for vals, col, lbl, ls, lw in [
        (obs_v, C["obs"], "Observed",  "-",  2.6),
        (raw_v, C["raw"], "Raw CMIP6", "--", 2.0),
        (bc_v,  C["bc"],  "QDM",       "-",  2.2),
    ]:
        kde  = gaussian_kde(vals, bw_method=bw)
        dens = kde(x_grid)
        sk   = float(sps.skew(vals))
        kurt = float(sps.kurtosis(vals))
        ax.plot(x_grid, dens, color=col, ls=ls, lw=lw,
                label=f"{lbl}  (Skew = {sk:.2f},  Kurtosis = {kurt:.2f})")
        ax.fill_between(x_grid, dens, alpha=0.08, color=col)

    ax.set_xlabel("Daily Rainfall (mm)", fontsize=FS["label"])
    ax.set_ylabel("Probability Density", fontsize=FS["label"])
    ax.set_title(f"Probability Density Function — Wet-Day Rainfall (≥{WET_THR} mm)"
                 "  │  All Stations Pooled",
                 loc="left", fontsize=FS["title"] - 1, fontweight="bold", pad=5)
    ax.set_xlim(0, x_max)
    ax.legend(fontsize=FS["legend"], frameon=True, edgecolor="#B0BEC5",
              loc="upper right")
    ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Heavy-tail inset
    p95_obs = float(np.percentile(obs_v, 95))
    x_tail  = np.linspace(p95_obs, x_max, 500)
    ax_ins  = ax.inset_axes([0.48, 0.35, 0.50, 0.56])
    for vals, col, lbl, ls, lw in [
        (obs_v, C["obs"], "Observed",  "-",  2.0),
        (raw_v, C["raw"], "Raw CMIP6", "--", 1.6),
        (bc_v,  C["bc"],  "QDM",       "-",  1.8),
    ]:
        kde    = gaussian_kde(vals, bw_method=bw)
        dens_t = kde(x_tail)
        ax_ins.plot(x_tail, dens_t, color=col, ls=ls, lw=lw, label=lbl)
        ax_ins.fill_between(x_tail, dens_t, alpha=0.09, color=col)
    p99_obs = float(np.percentile(obs_v, 99))
    ax_ins.axvline(p95_obs, color=C["gold"],   lw=1.1, ls=":",
                   label=f"P95 = {p95_obs:.1f} mm")
    ax_ins.axvline(p99_obs, color=C["purple"], lw=1.1, ls=":",
                   label=f"P99 = {p99_obs:.1f} mm")
    ax_ins.set_xlim(p95_obs, x_max)
    ax_ins.set_xlabel("mm (tail region)", fontsize=FS["annot"])
    ax_ins.set_ylabel("Density",          fontsize=FS["annot"])
    ax_ins.set_title("Heavy Tail  (> P95)", fontsize=FS["annot"],
                     fontweight="bold")
    ax_ins.tick_params(labelsize=FS["note"])
    ax_ins.spines["top"].set_visible(False)
    ax_ins.spines["right"].set_visible(False)
    ax_ins.legend(fontsize=FS["note"] - 1, frameon=True, edgecolor="#B0BEC5",
                  loc="upper right", ncol=1)

    fig.suptitle(
        f"Probability Density Function — Wet-Day Rainfall  │  {province}\n"
        "Kernel Density Estimation (Scott bandwidth)  │  Inset: Heavy-tail region (> P95)",
        fontsize=FS["title"] + 1, fontweight="bold")
    plt.savefig(out_path, dpi=600)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ══════════════════════════════════════════════════════════════════════════════
# 8.  FIGURE D – CDF Comparison
# ══════════════════════════════════════════════════════════════════════════════

def fig_cdf(obs_d, raw_ens, bc_ens, stns, province, out_path):
    def pool(df):
        v = df[[s for s in stns if s in df.columns]].values.flatten()
        return np.sort(v[~np.isnan(v) & (v >= 0)].astype(float))

    obs_v = pool(obs_d)
    raw_v = pool(raw_ens)
    bc_v  = pool(bc_ens)

    def empirical_cdf(arr):
        n = len(arr)
        return arr, np.arange(1, n + 1) / n

    fig, axes = plt.subplots(1, 2, figsize=(17, 7))
    fig.subplots_adjust(wspace=0.30, top=0.88, bottom=0.12,
                        left=0.07, right=0.97)
    SERIES = [
        (obs_v, C["obs"], "Observed",  "-",  2.6),
        (raw_v, C["raw"], "Raw CMIP6", "--", 2.0),
        (bc_v,  C["bc"],  "QDM",       "-",  2.2),
    ]
    tags = ["(a)  Full Empirical CDF — All Daily Values",
            "(b)  Upper Tail (P80–P100) — Extreme Percentile Alignment"]

    for panel, (ax, title_tag) in enumerate(zip(axes, tags)):
        for vals, col, lbl, ls, lw in SERIES:
            x, cdf = empirical_cdf(vals)
            ax.plot(x, cdf, color=col, ls=ls, lw=lw, label=lbl, alpha=0.88)
        obs_x, obs_cdf = empirical_cdf(obs_v)
        for pct, pcol in [(50, "#78909C"), (90, C["gold"]),
                           (95, C["orange"]), (99, C["purple"])]:
            idx = np.searchsorted(obs_cdf, pct / 100.0)
            if idx >= len(obs_x):
                idx = len(obs_x) - 1
            xv = obs_x[idx]
            ax.axvline(xv, color=pcol, lw=1.0, ls=":", alpha=0.75)
            ax.text(xv, 0.02 + 0.06 * (pct == 99) + 0.03 * (pct == 95),
                    f"P{pct} = {xv:.1f} mm",
                    rotation=90, va="bottom", ha="right",
                    fontsize=FS["note"], color=pcol, fontweight="bold")
        ax.set_xlabel("Daily Rainfall (mm)", fontsize=FS["label"])
        ax.set_ylabel("Cumulative Probability", fontsize=FS["label"])
        ax.set_title(title_tag, loc="left",
                     fontsize=FS["title"] - 2, fontweight="bold", pad=5)
        ax.set_ylim(0, 1)
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.legend(fontsize=FS["legend"], frameon=True, edgecolor="#B0BEC5",
                  loc="lower right")
        if panel == 1:
            lo = float(np.percentile(obs_v[obs_v >= 0], 80)) if len(obs_v) else 0
            hi = float(max(np.max(obs_v), np.max(raw_v), np.max(bc_v)))
            ax.set_xlim(lo, hi)
            ax.set_ylim(0.80, 1.0)

    fig.suptitle(
        f"Empirical Cumulative Distribution Function — {province}\n"
        "All Daily Values  │  Percentile markers: P50, P90, P95, P99 (Observed reference)",
        fontsize=FS["title"] + 1, fontweight="bold")
    plt.savefig(out_path, dpi=600)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ══════════════════════════════════════════════════════════════════════════════
# 9.  FIGURE E – Q-Q Plot
# ══════════════════════════════════════════════════════════════════════════════

def fig_qq(obs_d, raw_ens, bc_ens, stns, province, out_path):
    def pool_wet(df):
        v = df[[s for s in stns if s in df.columns]].values.flatten()
        return v[~np.isnan(v) & (v >= WET_THR)].astype(float)

    obs_v = pool_wet(obs_d)
    raw_v = pool_wet(raw_ens)
    bc_v  = pool_wet(bc_ens)

    probs  = np.linspace(0.001, 0.999, 500)
    obs_q  = np.quantile(obs_v, probs)
    raw_q  = np.quantile(raw_v, probs)
    bc_q   = np.quantile(bc_v,  probs)
    mn, mx = obs_q.min(), obs_q.max()

    fig, axes = plt.subplots(1, 2, figsize=(17, 8))
    fig.subplots_adjust(wspace=0.28, top=0.87, bottom=0.11,
                        left=0.08, right=0.97)

    for ax, (sim_q, col, lbl), title_tag in zip(
        axes,
        [(raw_q, C["raw"], "Raw CMIP6"),
         (bc_q,  C["bc"],  "QDM Bias-Corrected")],
        ["(a)  Raw CMIP6 vs Observed",
         "(b)  QDM Bias-Corrected vs Observed"]
    ):
        ax.plot([mn, mx], [mn, mx], color=C["grey"], lw=1.4, ls="--",
                label="1:1 Line", zorder=2)
        ax.scatter(obs_q, sim_q, color=col, s=18, alpha=0.55,
                   edgecolors="none", zorder=3)
        # Tail markers
        for pct, pcol, plbl in [(95, C["gold"],  "P95"),
                                  (99, C["orange"],"P99"),
                                  (99.5, C["purple"],"P99.5")]:
            i = int(pct / 100 * 500)
            if i >= len(obs_q): i = len(obs_q) - 1
            ax.scatter(obs_q[i], sim_q[i], color=pcol, s=80,
                       zorder=5, label=f"{plbl}: Obs={obs_q[i]:.1f},"
                                       f" Sim={sim_q[i]:.1f}", marker="^")
        # KS test
        ks_stat, ks_p = sps.ks_2samp(obs_v, raw_v if col == C["raw"] else bc_v)
        ax.text(0.04, 0.96,
                f"KS stat = {ks_stat:.3f}   p = {ks_p:.4f}",
                transform=ax.transAxes, fontsize=FS["annot"] + 1,
                va="top", ha="left",
                bbox=dict(boxstyle="round,pad=0.4", fc="white",
                          ec="#B0BEC5", alpha=0.85))
        ax.set_xlabel("Observed Quantile (mm)", fontsize=FS["label"])
        ax.set_ylabel(f"{lbl} Quantile (mm)",  fontsize=FS["label"])
        ax.set_title(title_tag, loc="left", fontsize=FS["title"] - 1,
                     fontweight="bold", pad=5)
        ax.legend(fontsize=FS["legend"] - 1, frameon=True,
                  edgecolor="#B0BEC5", loc="upper left")
        ax.set_xlim(0, mx * 1.05)
        ax.set_ylim(0, mx * 1.05)
        ax.set_aspect("equal", adjustable="box")
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    fig.suptitle(
        f"Quantile–Quantile Plot — Wet-Day Rainfall  │  {province}\n"
        "Triangles: P95, P99, P99.5 quantile pairs  │  KS test statistic shown",
        fontsize=FS["title"] + 1, fontweight="bold")
    plt.savefig(out_path, dpi=600)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ══════════════════════════════════════════════════════════════════════════════
# 10.  FIGURE F – ETCCDI Heatmap
# ══════════════════════════════════════════════════════════════════════════════

def fig_etccdi_heatmap(obs_d, raw_ens, bc_ens, stns, smap, province, out_path):
    INDICES = list(ETCCDI_UNITS.keys())
    codes   = [smap.get(str(s), str(s)) for s in stns]
    n_s     = len(stns)
    n_i     = len(INDICES)

    def compute_mean_matrix(df):
        mat = np.full((n_i, n_s), np.nan)
        for si, stn in enumerate(stns):
            if stn not in df.columns:
                continue
            idx_df = etccdi_annual(df[stn].dropna())
            if idx_df.empty:
                continue
            for ii, idx in enumerate(INDICES):
                if idx in idx_df.columns:
                    mat[ii, si] = float(idx_df[idx].mean())
        return mat

    mat_obs = compute_mean_matrix(obs_d)
    mat_raw = compute_mean_matrix(raw_ens)
    mat_bc  = compute_mean_matrix(bc_ens)

    fig, axes = plt.subplots(1, 3, figsize=(20, 8))
    fig.subplots_adjust(left=0.10, right=0.96, top=0.88,
                        bottom=0.12, wspace=0.35)
    titles  = ["(a) Observed", "(b) Raw CMIP6", "(c) QDM Bias-Corrected"]
    mats    = [mat_obs, mat_raw, mat_bc]
    cmaps_  = ["Blues", "Reds", "YlGnBu"]

    for ax, mat, title_tag, cmap_ in zip(axes, mats, titles, cmaps_):
        vmin = np.nanmin(mat)
        vmax = np.nanmax(mat)
        im = ax.imshow(mat, cmap=cmap_, vmin=vmin, vmax=vmax,
                       aspect="auto", interpolation="nearest")
        for ii in range(n_i):
            for si in range(n_s):
                v = mat[ii, si]
                if not np.isnan(v):
                    mid = (vmin + vmax) / 2
                    tc  = "white" if abs(v - mid) / (vmax - vmin + 1e-9) > 0.5 \
                          else "black"
                    ax.text(si, ii, f"{v:.1f}", ha="center", va="center",
                            fontsize=max(7, FS["note"] - 2),
                            color=tc, fontweight="bold")
        ax.set_xticks(range(n_s))
        ax.set_xticklabels(codes, rotation=0, ha="center",
                           fontsize=FS["tick"] - 1, fontweight="bold")
        ax.set_yticks(range(n_i))
        ax.set_yticklabels([f"{k} ({v})" for k, v in ETCCDI_UNITS.items()],
                           fontsize=FS["note"] + 1)
        ax.set_title(title_tag, fontsize=FS["title"] - 1, fontweight="bold", pad=6)
        plt.colorbar(im, ax=ax, orientation="horizontal",
                     pad=0.16, fraction=0.05, shrink=0.88)

    fig.suptitle(
        f"ETCCDI Extreme Climate Indices — Mean Annual Values  │  {province}\n"
        "All Stations  │  Obs vs Raw CMIP6 vs QDM Bias-Corrected",
        fontsize=FS["title"] + 1, fontweight="bold")
    plt.savefig(out_path, dpi=600)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ══════════════════════════════════════════════════════════════════════════════
# 11.  FIGURE G – Multi-Timescale Trend per Model (NEW)
# ══════════════════════════════════════════════════════════════════════════════

TIMESCALES = [
    ("Annual",        None,            "Annual Total (mm yr⁻¹)"),
    ("Monthly",       None,            "Monthly Total (mm mon⁻¹)"),
    ("Wet Season\n(May–Oct)",   [5,6,7,8,9,10], "Wet Season Total (mm)"),
    ("Dry Season\n(Nov–Apr)",   [11,12,1,2,3,4],"Dry Season Total (mm)"),
]


def _build_timescale_series(df, stns, months=None):
    """Build regional-mean series for a given timescale."""
    if months is None:
        # Annual
        return annual_total(df, stns)
    elif len(months) > 6:
        # Monthly
        return monthly_series(df, stns)
    else:
        return seasonal_series(df, stns, months)


def fig_multiscale_trend_per_model(obs_d, raw_dfs, bc_dfs, bc_ens,
                                    stns, province, period_obs, out_path):
    """
    Fig G: Multi-timescale trend per CMIP6 model.
    4 rows (timescales) × n_models columns (QDM only).
    Observed and ensemble QDM mean shown in every panel as references.
    """
    models  = sorted(set(raw_dfs.keys()) & set(bc_dfs.keys()))
    n_m     = len(models)
    if n_m == 0:
        return
    n_ts    = len(TIMESCALES)

    # Pre-compute ensemble QDM series per timescale
    ens_series = {}
    obs_series = {}
    for ts_name, months, ylabel in TIMESCALES:
        if months is None and ylabel.startswith("Monthly"):
            obs_series[ts_name] = monthly_series(obs_d, stns)
            ens_series[ts_name] = monthly_series(bc_ens, stns)
        elif months is None:
            obs_series[ts_name] = annual_total(obs_d, stns)
            ens_series[ts_name] = annual_total(bc_ens, stns)
        else:
            obs_series[ts_name] = seasonal_series(obs_d, stns, months)
            ens_series[ts_name] = seasonal_series(bc_ens, stns, months)

    fig, axes = plt.subplots(n_ts, n_m,
                              figsize=(5.5 * n_m, 5.0 * n_ts),
                              sharex=False)
    if n_m == 1:
        axes = axes.reshape(n_ts, 1)
    if n_ts == 1:
        axes = axes.reshape(1, n_m)
    fig.subplots_adjust(hspace=0.60, wspace=0.30,
                        top=0.93, bottom=0.05,
                        left=0.07, right=0.97)

    for ti, (ts_name, months, ylabel) in enumerate(TIMESCALES):
        obs_s = obs_series[ts_name]
        ens_s = ens_series[ts_name]

        for mi, model in enumerate(models):
            ax  = axes[ti, mi]
            col = MODEL_COLORS[mi % len(MODEL_COLORS)]
            bc_df = bc_dfs[model]
            if months is None and not ylabel.startswith("Monthly"):
                mod_s = annual_total(bc_df, stns)
            elif months is None:
                mod_s = monthly_series(bc_df, stns)
            else:
                mod_s = seasonal_series(bc_df, stns, months)

            # Observed
            _plot_trend_line(ax, obs_s, C["obs"], "Observed",
                             "-", 1.8, 5, unit="mm")
            # Ensemble QDM mean
            _plot_trend_line(ax, ens_s, C["bc"], "Ensemble QDM",
                             "--", 1.4, 3, unit="mm")
            # Individual model QDM
            _plot_trend_line(ax, mod_s, col, model,
                             "-", 2.0, 4, unit="mm")

            ax.set_ylabel(ylabel if mi == 0 else "",
                          fontsize=FS["label"] - 2)
            if ti == 0:
                ax.set_title(model, fontsize=FS["title"] - 2,
                             fontweight="bold", pad=4)
            if ti == n_ts - 1:
                ax.set_xlabel("Year", fontsize=FS["label"] - 2)
            ax.legend(fontsize=max(7, FS["legend"] - 3), frameon=True,
                      edgecolor="#B0BEC5", loc="best", ncol=1)
            ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)

        # Row label
        axes[ti, 0].text(-0.18, 0.5, ts_name,
                          transform=axes[ti, 0].transAxes,
                          rotation=90, va="center", ha="center",
                          fontsize=FS["label"], fontweight="bold",
                          color="#1F4E79")

    fig.suptitle(
        f"Multi-Timescale Rainfall Trend per CMIP6 Model (QDM) — {province}  │  {period_obs}\n"
        "Rows: Annual / Monthly / Wet Season (May–Oct) / Dry Season (Nov–Apr)\n"
        "Sen's Slope + Mann-Kendall  │  Obs = black, Ensemble QDM = blue dashed",
        fontsize=FS["title"] + 1, fontweight="bold")
    plt.savefig(out_path, dpi=600)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ══════════════════════════════════════════════════════════════════════════════
# 12.  FIGURE H – Ensemble Mean vs Best Individual Model (NEW)
# ══════════════════════════════════════════════════════════════════════════════

def fig_ensemble_vs_best(obs_d, bc_dfs, bc_ens, stns, province,
                          period_obs, out_path):
    """
    Fig H: Ensemble mean vs best individual model performance.
    Compares KGE, RMSE, annual trend reproduction across all stations.
    """
    from scipy.stats import pearsonr

    models = sorted(bc_dfs.keys())
    if not models:
        return
    n_m  = len(models)
    stns_str = [str(s) for s in stns]

    def kge(obs, sim):
        mask = ~np.isnan(obs) & ~np.isnan(sim)
        o, s = obs[mask], sim[mask]
        if len(o) < 4:
            return np.nan
        r = float(np.corrcoef(o, s)[0, 1])
        alpha = float(np.std(s, ddof=1) / np.std(o, ddof=1)) \
                if np.std(o, ddof=1) else np.nan
        beta  = float(np.mean(s) / np.mean(o)) if np.mean(o) else np.nan
        if np.isnan(alpha) or np.isnan(beta):
            return np.nan
        return float(1 - math.sqrt((r - 1)**2 + (alpha - 1)**2 + (beta - 1)**2))

    def rmse(obs, sim):
        mask = ~np.isnan(obs) & ~np.isnan(sim)
        o, s = obs[mask], sim[mask]
        return float(np.sqrt(np.mean((s - o)**2))) if len(o) >= 4 else np.nan

    # Per-station KGE and RMSE for each model + ensemble
    all_entries = {}
    for m in models:
        all_entries[m] = {"kge": [], "rmse": []}
    all_entries["Ensemble"] = {"kge": [], "rmse": []}

    for stn in stns_str:
        if stn not in obs_d.columns:
            continue
        obs_ann = obs_d[stn].resample("YS").sum(min_count=int(0.8 * 365))
        for m in models:
            df = bc_dfs[m]
            if stn not in df.columns:
                continue
            common = obs_d.index.intersection(df.index)
            if len(common) < 50:
                continue
            o = obs_d.loc[common, stn].values.astype(float)
            s = df.loc[common, stn].values.astype(float)
            all_entries[m]["kge"].append(kge(o, s))
            all_entries[m]["rmse"].append(rmse(o, s))

        if bc_ens is not None and stn in bc_ens.columns:
            common = obs_d.index.intersection(bc_ens.index)
            if len(common) >= 50:
                o = obs_d.loc[common, stn].values.astype(float)
                s = bc_ens.loc[common, stn].values.astype(float)
                all_entries["Ensemble"]["kge"].append(kge(o, s))
                all_entries["Ensemble"]["rmse"].append(rmse(o, s))

    # Summary metrics
    keys_plot  = models + ["Ensemble"]
    mean_kge   = [np.nanmean(all_entries[k]["kge"])  for k in keys_plot]
    mean_rmse  = [np.nanmean(all_entries[k]["rmse"]) for k in keys_plot]
    colors_plot = MODEL_COLORS[:n_m] + ["#37474F"]

    fig, axes = plt.subplots(1, 3, figsize=(20, 7))
    fig.subplots_adjust(left=0.06, right=0.97, top=0.87,
                        bottom=0.15, wspace=0.35)

    # Panel (a): Mean KGE bar chart
    ax = axes[0]
    xpos = np.arange(len(keys_plot))
    bars = ax.bar(xpos, mean_kge, color=colors_plot, alpha=0.85,
                  edgecolor="white", linewidth=0.8, zorder=3)
    # Best model (highest KGE)
    best_idx  = int(np.nanargmax(mean_kge[:-1]))  # exclude ensemble
    ens_kge   = mean_kge[-1]
    for i, (bar, v) in enumerate(zip(bars, mean_kge)):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.005,
                f"{v:.3f}", ha="center", va="bottom",
                fontsize=FS["annot"], fontweight="bold")
    ax.axhline(ens_kge, color="#37474F", lw=1.6, ls="--",
               label=f"Ensemble KGE = {ens_kge:.3f}", zorder=4)
    ax.set_xticks(xpos)
    ax.set_xticklabels(keys_plot, rotation=0, ha="center",
                       fontsize=FS["tick"] - 1, fontweight="bold")
    ax.set_ylabel("Mean KGE (across all stations)", fontsize=FS["label"])
    ax.set_title("(a)  Mean KGE — Individual Models vs Ensemble",
                 loc="left", fontsize=FS["title"] - 1, fontweight="bold", pad=5)
    ax.legend(fontsize=FS["legend"] - 1, frameon=True, edgecolor="#B0BEC5")
    ax.set_ylim(min(0, np.nanmin(mean_kge) - 0.05),
                max(mean_kge) + 0.12)
    ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Panel (b): Mean RMSE bar chart
    ax2 = axes[1]
    bars2 = ax2.bar(xpos, mean_rmse, color=colors_plot, alpha=0.85,
                    edgecolor="white", linewidth=0.8, zorder=3)
    ens_rmse = mean_rmse[-1]
    for bar, v in zip(bars2, mean_rmse):
        ax2.text(bar.get_x() + bar.get_width() / 2, v + 0.1,
                 f"{v:.2f}", ha="center", va="bottom",
                 fontsize=FS["annot"], fontweight="bold")
    ax2.axhline(ens_rmse, color="#37474F", lw=1.6, ls="--",
                label=f"Ensemble RMSE = {ens_rmse:.2f}", zorder=4)
    ax2.set_xticks(xpos)
    ax2.set_xticklabels(keys_plot, rotation=0, ha="center",
                        fontsize=FS["tick"] - 1, fontweight="bold")
    ax2.set_ylabel("Mean RMSE (mm d⁻¹, across all stations)",
                   fontsize=FS["label"])
    ax2.set_title("(b)  Mean RMSE — Individual Models vs Ensemble",
                  loc="left", fontsize=FS["title"] - 1, fontweight="bold", pad=5)
    ax2.legend(fontsize=FS["legend"] - 1, frameon=True, edgecolor="#B0BEC5")
    ax2.yaxis.set_minor_locator(ticker.AutoMinorLocator())
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    # Panel (c): Boxplot of per-station KGE
    ax3 = axes[2]
    data_box = [all_entries[k]["kge"] for k in keys_plot]
    bp = ax3.boxplot(data_box, patch_artist=True, widths=0.55, notch=False,
                     medianprops=dict(linewidth=2.4, color="black"),
                     whiskerprops=dict(linewidth=1.3),
                     capprops=dict(linewidth=1.4),
                     flierprops=dict(marker="o", markersize=5, alpha=0.5),
                     boxprops=dict(linewidth=1.0))
    for box, col in zip(bp["boxes"], colors_plot):
        box.set_facecolor(mcolors.to_rgba(col, 0.55))
        box.set_edgecolor(col)
    ax3.axhline(0, color=C["grey"], lw=0.9, ls="--", alpha=0.6)
    ax3.set_xticks(range(1, len(keys_plot) + 1))
    ax3.set_xticklabels(keys_plot, rotation=0, ha="center",
                        fontsize=FS["tick"] - 1, fontweight="bold")
    ax3.set_ylabel("KGE (per station distribution)", fontsize=FS["label"])
    ax3.set_title("(c)  KGE Distribution — Individual vs Ensemble\n"
                  "     (whiskers = 1.5×IQR; circles = outliers)",
                  loc="left", fontsize=FS["title"] - 1, fontweight="bold", pad=5)
    ax3.yaxis.set_minor_locator(ticker.AutoMinorLocator())
    ax3.spines["top"].set_visible(False)
    ax3.spines["right"].set_visible(False)

    fig.suptitle(
        f"Ensemble Mean vs Best Individual Model — QDM Bias-Corrected  │  {province}  │  {period_obs}\n"
        "Question: Does ensemble mean outperform the best individual CMIP6 model after QDM?",
        fontsize=FS["title"] + 1, fontweight="bold")
    plt.savefig(out_path, dpi=600)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ══════════════════════════════════════════════════════════════════════════════
# 13.  FIGURE I – QDM Trend-Signal Preservation (NEW)
# ══════════════════════════════════════════════════════════════════════════════

def fig_qdm_trend_preservation(obs_d, raw_dfs, bc_dfs, bc_ens,
                                stns, province, period_obs, out_path):
    """
    Fig I: Does QDM preserve observed rainfall trend signals?
    Compares Sen's slope from Obs, Raw, QDM for all timescales + all models.
    """
    models  = sorted(set(raw_dfs.keys()) & set(bc_dfs.keys()))
    n_m     = len(models)
    if n_m == 0:
        return

    # Timescales to evaluate
    ts_defs = [
        ("Annual",       None),
        ("Wet\nSeason",  [5,6,7,8,9,10]),
        ("Dry\nSeason",  [11,12,1,2,3,4]),
    ]

    def get_slope(df, months):
        if months is None:
            s = annual_total(df, stns).dropna()
        else:
            s = seasonal_series(df, stns, months).dropna()
        if len(s) < 4:
            return np.nan
        sl, _, _, _ = sens_slope(s.values, s.index.year.astype(float))
        return sl

    def get_tau_p(df, months):
        if months is None:
            s = annual_total(df, stns).dropna()
        else:
            s = seasonal_series(df, stns, months).dropna()
        if len(s) < 4:
            return np.nan, np.nan
        tau, p, *_ = mann_kendall(s.values)
        return tau, p

    # Build slope matrices: [ts_idx, model_idx] for Raw and QDM
    obs_slopes  = []
    raw_slopes  = np.full((len(ts_defs), n_m), np.nan)
    bc_slopes   = np.full((len(ts_defs), n_m), np.nan)
    ens_slopes  = []
    obs_taus    = []

    for ti, (ts_name, months) in enumerate(ts_defs):
        obs_sl = get_slope(obs_d, months)
        obs_slopes.append(obs_sl)
        obs_tau, obs_p = get_tau_p(obs_d, months)
        obs_taus.append((obs_tau, obs_p))
        ens_sl = get_slope(bc_ens, months)
        ens_slopes.append(ens_sl)
        for mi, model in enumerate(models):
            raw_slopes[ti, mi] = get_slope(raw_dfs[model], months)
            bc_slopes[ti, mi]  = get_slope(bc_dfs[model],  months)

    fig, axes = plt.subplots(1, len(ts_defs), figsize=(20, 8))
    fig.subplots_adjust(left=0.07, right=0.97, top=0.87,
                        bottom=0.18, wspace=0.40)

    ts_labels   = [t[0] for t in ts_defs]
    model_colors_arr = MODEL_COLORS[:n_m]

    for ti, (ax, ts_name) in enumerate(zip(axes, ts_labels)):
        obs_sl = obs_slopes[ti]
        ens_sl = ens_slopes[ti]
        obs_tau, obs_p = obs_taus[ti]
        obs_sig = trend_sig(obs_p) if not np.isnan(obs_p) else ""

        x_raw = raw_slopes[ti, :]
        x_bc  = bc_slopes[ti,  :]

        # Scatter: Raw vs QDM slope per model
        for mi, (model, col) in enumerate(zip(models, model_colors_arr)):
            ax.scatter(x_raw[mi], x_bc[mi], color=col, s=120, zorder=4,
                       edgecolors="white", linewidths=0.8,
                       label=model)
            # Arrow from raw to QDM
            dx = x_bc[mi] - x_raw[mi]
            dy = 0
            if abs(dx) > 0.01:
                ax.annotate("", xy=(x_bc[mi], 0.05 * mi),
                            xytext=(x_raw[mi], 0.05 * mi),
                            arrowprops=dict(arrowstyle="->",
                                            color=col, lw=1.2),
                            zorder=3)

        # Reference lines
        ax.axvline(obs_sl, color=C["obs"], lw=2.2, ls="-",
                   label=f"Observed β = {obs_sl:+.2f} {obs_sig}")
        ax.axhline(obs_sl, color=C["obs"], lw=1.2, ls=":", alpha=0.55)
        ax.axvline(ens_sl, color=C["bc"], lw=1.8, ls="--",
                   label=f"Ensemble QDM β = {ens_sl:+.2f}")
        ax.axhline(0, color=C["grey"], lw=0.8, ls="--", alpha=0.5)
        ax.axvline(0, color=C["grey"], lw=0.8, ls="--", alpha=0.5)

        ax.set_xlabel("Raw CMIP6 Sen's Slope (mm yr⁻¹)", fontsize=FS["label"] - 1)
        if ti == 0:
            ax.set_ylabel("QDM Sen's Slope (mm yr⁻¹)", fontsize=FS["label"])
        ax.set_title(f"({chr(97 + ti)})  {ts_name} Rainfall",
                     loc="left", fontsize=FS["title"] - 1, fontweight="bold", pad=5)
        ax.legend(fontsize=max(8, FS["legend"] - 2), frameon=True,
                  edgecolor="#B0BEC5", loc="best", ncol=1)
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.xaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    # Bottom bar: slope preservation score
    ax_bar = fig.add_axes([0.07, 0.03, 0.90, 0.06])
    preserve_scores = []
    for mi, model in enumerate(models):
        # Score: how close QDM slope is to observed slope (for annual)
        obs_sl = obs_slopes[0]
        bc_sl  = bc_slopes[0, mi]
        raw_sl = raw_slopes[0, mi]
        if np.isnan(obs_sl) or np.isnan(bc_sl) or np.isnan(raw_sl):
            preserve_scores.append(np.nan)
            continue
        # Score = 1 - |QDM-Obs| / max(|Raw-Obs|, eps)
        denom  = max(abs(raw_sl - obs_sl), 1e-6)
        score  = max(0, 1 - abs(bc_sl - obs_sl) / denom)
        preserve_scores.append(score)
    x_b   = np.arange(n_m)
    colors_b = MODEL_COLORS[:n_m]
    ax_bar.bar(x_b, preserve_scores, color=colors_b, alpha=0.85,
               edgecolor="white", linewidth=0.6, zorder=3)
    for xi, v in enumerate(preserve_scores):
        if not np.isnan(v):
            ax_bar.text(xi, v + 0.02, f"{v:.2f}",
                        ha="center", va="bottom", fontsize=FS["note"],
                        fontweight="bold")
    ax_bar.axhline(1, color=C["obs"], lw=1.3, ls="--", alpha=0.7)
    ax_bar.set_xlim(-0.5, n_m - 0.5)
    ax_bar.set_ylim(0, 1.25)
    ax_bar.set_xticks(x_b)
    ax_bar.set_xticklabels(models, fontsize=FS["tick"] - 1, fontweight="bold")
    ax_bar.set_ylabel("Trend\nPreserv.\nScore", fontsize=FS["note"])
    ax_bar.set_title("Annual Trend Preservation Score after QDM  "
                     "(1 = perfect preservation of observed slope)",
                     loc="left", fontsize=FS["note"] + 1, fontweight="bold")
    ax_bar.spines["top"].set_visible(False)
    ax_bar.spines["right"].set_visible(False)
    ax_bar.grid(axis="y", ls="--", lw=0.4, alpha=0.5)

    fig.suptitle(
        f"QDM Trend-Signal Preservation — {province}  │  {period_obs}\n"
        "X-axis = Raw CMIP6 slope,  Y-axis = QDM slope (each point = one model)\n"
        "Vertical line = Observed slope (reference). QDM should move points closer to Observed.",
        fontsize=FS["title"] + 1, fontweight="bold")
    plt.savefig(out_path, dpi=600)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ══════════════════════════════════════════════════════════════════════════════
# 14.  EXCEL OUTPUT
# ══════════════════════════════════════════════════════════════════════════════

def _xl_trend_sheet(wb, obs_d, raw_ens, bc_ens, stns, smap, province):
    ws = wb.create_sheet("Annual Trend")
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "E4"

    nc = 12
    mxsc(ws, 1, 1, nc,
         f"Annual Rainfall Trend Statistics — {province}",
         bold=True, fc="FFFFFF", bg=XC["title"], sz=13, align="left")
    ws.row_dimensions[1].height = 24
    mxsc(ws, 2, 1, nc,
         "Mann-Kendall Test + Sen's Slope | Scales: Daily, Monthly, Seasonal, Annual | "
         "Significance: *** p<0.001  ** p<0.01  * p<0.05  † p<0.10  ns p≥0.10",
         italic=True, fc="FFFFFF", bg=XC["sub"], sz=8.5)
    ws.row_dimensions[2].height = 14

    hdr = ["Station", "Code", "Dataset", "Scale",
           "Sen's Slope", "Intercept", "Slope 95%CI Lo", "Slope 95%CI Hi",
           "Tau", "Z-stat", "p-value", "Significance"]
    for ci, h in enumerate(hdr, 1):
        xsc(ws, 3, ci, h, bold=True, fc="FFFFFF", bg=XC["hdr"],
            border=tb(), sz=9, wrap=True)
    ws.row_dimensions[3].height = 36

    ds_colors = {"Observed": XC["obs_r"], "Raw CMIP6": XC["raw_r"],
                 "QDM": XC["bc_r"]}
    r = 4
    for stn in stns:
        stn_s = str(stn)
        code  = smap.get(stn_s, stn_s)
        for ds_lbl, df in [("Observed", obs_d),
                            ("Raw CMIP6", raw_ens),
                            ("QDM", bc_ens)]:
            if stn_s not in df.columns:
                continue
            bg = ds_colors.get(ds_lbl, XC["white"])
            # Annual
            ann = df[stn_s].resample("YS").sum(min_count=int(0.8 * 365)).dropna()
            if len(ann) >= 4:
                sl, ic, lo, hi = sens_slope(ann.values,
                                             ann.index.year.astype(float))
                tau, p, S, vS, z = mann_kendall(ann.values)
                sig = trend_sig(p)
                row_v = [stn_s, code, ds_lbl, "Annual",
                         round(sl, 4), round(ic, 3),
                         round(lo, 4), round(hi, 4),
                         round(tau, 4), round(z, 3), round(p, 4), sig]
                for ci, v in enumerate(row_v, 1):
                    cell = xsc(ws, r, ci, v, bg=bg, border=tb(), sz=9,
                               align="left" if ci <= 4 else "right")
                    if ci == 12 and sig not in ("—", "ns"):
                        cell.fill = xfill(XC["sig"])
                        cell.font = Font(bold=True, color=XC["obs_h"],
                                         name="Calibri", size=9)
                ws.row_dimensions[r].height = 14
                r += 1
    widths = [12, 6, 12, 10, 12, 10, 14, 14, 10, 9, 9, 12]
    for ci, w in enumerate(widths, 1):
        cw(ws, ci, w)


def _xl_etccdi_sheet(wb, obs_d, raw_ens, bc_ens, stns, smap, province):
    ws = wb.create_sheet("ETCCDI Indices")
    ws.sheet_view.showGridLines = False
    mxsc(ws, 1, 1, 14,
         f"ETCCDI Extreme Climate Indices — {province}",
         bold=True, fc="FFFFFF", bg=XC["title"], sz=13, align="left")
    ws.row_dimensions[1].height = 24

    hdr = ["Index", "Unit", "Dataset", "Mean", "Std", "Min", "Max",
           "Sen Slope", "CI Lo", "CI Hi", "Tau", "Z", "p-val", "Sig"]
    for ci, h in enumerate(hdr, 1):
        xsc(ws, 3, ci, h, bold=True, fc="FFFFFF", bg=XC["hdr"],
            border=tb(), sz=9, wrap=True)
    ws.row_dimensions[3].height = 36

    ds_colors = {"Observed": XC["obs_r"], "Raw CMIP6": XC["raw_r"],
                 "QDM": XC["bc_r"]}
    rc = 4
    for ds_lbl, df in [("Observed", obs_d), ("Raw CMIP6", raw_ens),
                        ("QDM", bc_ens)]:
        bg = ds_colors.get(ds_lbl, XC["white"])
        idx_dict = annual_reg_etccdi(df, [str(s) for s in stns])
        for idx_name, series in idx_dict.items():
            s = series.dropna()
            if len(s) < 4:
                continue
            vals = s.values.astype(float)
            yrs  = s.index.astype(int).astype(float)
            sl, ic, lo, hi = sens_slope(vals, yrs)
            tau, p, S, vS, z = mann_kendall(vals)
            sig = trend_sig(p)
            row_v = [idx_name, ETCCDI_UNITS.get(idx_name, ""), ds_lbl,
                     round(float(np.mean(vals)), 3),
                     round(float(np.std(vals, ddof=1)), 3),
                     round(float(np.min(vals)), 3),
                     round(float(np.max(vals)), 3),
                     round(sl, 4) if not np.isnan(sl) else "—",
                     round(lo, 4) if not np.isnan(lo) else "—",
                     round(hi, 4) if not np.isnan(hi) else "—",
                     round(tau, 4) if not np.isnan(tau) else "—",
                     round(z, 3)  if not np.isnan(z)  else "—",
                     round(p, 4)  if not np.isnan(p)  else "—",
                     sig]
            for ci, v in enumerate(row_v, 1):
                cell = xsc(ws, rc, ci, v, bg=bg, border=tb(), sz=9,
                           align="left" if ci <= 3 else "right")
                if ci == 14 and sig not in ("—", "ns"):
                    cell.fill = xfill(XC["sig"])
                    cell.font = Font(bold=True, color=XC["obs_h"],
                                     name="Calibri", size=9)
            ws.row_dimensions[rc].height = 14
            rc += 1

    widths = [10, 7, 12, 9, 9, 9, 9, 10, 10, 10, 9, 8, 8, 10]
    for ci, w in enumerate(widths, 1):
        cw(ws, ci, w)


def _xl_per_model_trend(wb, obs_d, raw_dfs, bc_dfs, stns, smap, province):
    ws = wb.create_sheet("Per-Model Trend")
    ws.sheet_view.showGridLines = False
    mxsc(ws, 1, 1, 13,
         f"Per-Model Annual Trend Statistics — {province}",
         bold=True, fc="FFFFFF", bg=XC["title"], sz=13, align="left")
    ws.row_dimensions[1].height = 24

    hdr = ["Model", "Dataset", "Station", "Code", "Timescale",
           "Sen Slope", "IC Lo", "CI Hi",
           "Tau", "Z", "p-val", "Sig", "Trend Direction"]
    for ci, h in enumerate(hdr, 1):
        xsc(ws, 3, ci, h, bold=True, fc="FFFFFF", bg=XC["hdr"],
            border=tb(), sz=9, wrap=True)
    ws.row_dimensions[3].height = 36

    models = sorted(set(raw_dfs.keys()) & set(bc_dfs.keys()))
    ts_defs = [("Annual", None),
               ("Wet Season (May-Oct)", [5,6,7,8,9,10]),
               ("Dry Season (Nov-Apr)", [11,12,1,2,3,4])]

    rc = 4
    alt = [XC["raw_r"], XC["bc_r"]]
    for mi, model in enumerate(models):
        for di, (ds_lbl, df) in enumerate([("Raw CMIP6", raw_dfs[model]),
                                            ("QDM",        bc_dfs[model])]):
            bg = alt[di]
            for stn in stns:
                stn_s = str(stn)
                code  = smap.get(stn_s, stn_s)
                if stn_s not in df.columns:
                    continue
                for ts_name, months in ts_defs:
                    if months is None:
                        s = df[stn_s].resample("YS").sum(
                            min_count=int(0.8 * 365)).dropna()
                    else:
                        tmp = df[stn_s][df[stn_s].index.month.isin(months)]
                        s   = tmp.resample("YS").sum(
                            min_count=int(0.6 * len(months) * 28)).dropna()
                    if len(s) < 4:
                        continue
                    vals = s.values.astype(float)
                    yrs  = s.index.year.astype(float)
                    sl, ic, lo, hi = sens_slope(vals, yrs)
                    tau, p, S, vS, z = mann_kendall(vals)
                    sig = trend_sig(p)
                    direc = ("Increasing" if not np.isnan(sl) and sl > 0
                             else "Decreasing" if not np.isnan(sl)
                             else "—")
                    row_v = [model, ds_lbl, stn_s, code, ts_name,
                             round(sl, 4) if not np.isnan(sl) else "—",
                             round(lo, 4) if not np.isnan(lo) else "—",
                             round(hi, 4) if not np.isnan(hi) else "—",
                             round(tau, 4) if not np.isnan(tau) else "—",
                             round(z, 3)  if not np.isnan(z)  else "—",
                             round(p, 4)  if not np.isnan(p)  else "—",
                             sig, direc]
                    for ci, v in enumerate(row_v, 1):
                        cell = xsc(ws, rc, ci, v, bg=bg, border=tb(), sz=9,
                                   align="left" if ci <= 5 else "right")
                        if ci == 12 and sig not in ("—", "ns"):
                            cell.fill = xfill(XC["sig"])
                            cell.font = Font(bold=True, color=XC["obs_h"],
                                             name="Calibri", size=9)
                    ws.row_dimensions[rc].height = 14
                    rc += 1

    widths = [16, 12, 10, 6, 20, 11, 11, 11, 9, 8, 8, 8, 14]
    for ci, w in enumerate(widths, 1):
        cw(ws, ci, w)


def _xl_distribution(wb, obs_d, raw_ens, bc_ens, stns, smap, province):
    ws = wb.create_sheet("Distribution Stats")
    ws.sheet_view.showGridLines = False
    mxsc(ws, 1, 1, 12,
         f"Rainfall Distribution Statistics — {province}",
         bold=True, fc="FFFFFF", bg=XC["title"], sz=13, align="left")
    ws.row_dimensions[1].height = 24

    hdr = ["Station", "Code", "Dataset",
           "Mean (mm d⁻¹)", "Std", "P50", "P75", "P90", "P95", "P99",
           "Skewness", "KS stat (vs Obs)", "KS p-value"]
    for ci, h in enumerate(hdr, 1):
        xsc(ws, 3, ci, h, bold=True, fc="FFFFFF", bg=XC["hdr"],
            border=tb(), sz=9, wrap=True)
    ws.row_dimensions[3].height = 36

    ds_colors = {"Observed": XC["obs_r"], "Raw CMIP6": XC["raw_r"],
                 "QDM": XC["bc_r"]}
    rc = 4
    for stn in stns:
        stn_s = str(stn)
        code  = smap.get(stn_s, stn_s)
        obs_v = obs_d[stn_s].dropna().values.astype(float) \
                if stn_s in obs_d.columns else np.array([])
        obs_v = obs_v[obs_v >= WET_THR]
        for ds_lbl, df in [("Observed", obs_d), ("Raw CMIP6", raw_ens),
                            ("QDM", bc_ens)]:
            bg = ds_colors.get(ds_lbl, XC["white"])
            if stn_s not in df.columns:
                continue
            v = df[stn_s].dropna().values.astype(float)
            v = v[v >= WET_THR]
            if len(v) < 10:
                continue
            ks_s, ks_p = (sps.ks_2samp(obs_v, v) if ds_lbl != "Observed"
                          and len(obs_v) > 10
                          else (np.nan, np.nan))
            row_v = [stn_s, code, ds_lbl,
                     round(float(np.mean(v)), 3),
                     round(float(np.std(v, ddof=1)), 3),
                     round(float(np.percentile(v, 50)), 3),
                     round(float(np.percentile(v, 75)), 3),
                     round(float(np.percentile(v, 90)), 3),
                     round(float(np.percentile(v, 95)), 3),
                     round(float(np.percentile(v, 99)), 3),
                     round(float(sps.skew(v)), 3),
                     round(float(ks_s), 4) if not np.isnan(ks_s) else "—",
                     round(float(ks_p), 4) if not np.isnan(ks_p) else "—"]
            for ci, val in enumerate(row_v, 1):
                xsc(ws, rc, ci, val, bg=bg, border=tb(), sz=9,
                    align="left" if ci <= 3 else "right")
            ws.row_dimensions[rc].height = 14
            rc += 1

    widths = [12, 6, 12, 12, 10, 10, 10, 10, 10, 10, 10, 12, 12]
    for ci, w in enumerate(widths, 1):
        cw(ws, ci, w)


def _xl_methods(wb, province, period_obs, period_sim, n_stns, models):
    ws = wb.create_sheet("Methods & References")
    ws.sheet_view.showGridLines = False
    mxsc(ws, 1, 1, 3,
         "Statistical Methods, Indices & References  │  Trend & Distribution Analysis v2.0",
         bold=True, fc="FFFFFF", bg=XC["title"], sz=13)
    ws.row_dimensions[1].height = 24

    models_str = ", ".join(models) if models else "N/A"
    rows_info = [
        ("Study", "Study Parameters",
         f"Province: {province}  |  Obs: {period_obs}  |  Sim: {period_sim}  |  "
         f"Stations: {n_stns}  |  Wet-day threshold: ≥{WET_THR} mm  |  "
         f"CMIP6 Models: {models_str}"),
        ("MK", "Mann-Kendall Test",
         "Two-sided non-parametric trend test (Mann 1945; Kendall 1975). "
         "H₀: no monotonic trend. S statistic; var(S) with tie correction. "
         "Z = (S±1)/√var(S). Significance: *** p<0.001  ** p<0.01  * p<0.05  † p<0.10  ns p≥0.10"),
        ("Sen", "Sen's Slope",
         "Non-parametric slope estimator (Sen 1968, JASA 63:1379–1389). "
         "β = median of all pairwise slopes. 95% CI from scipy.stats.theilslopes."),
        ("KDE", "Kernel Density Estimation",
         "Gaussian KDE with Scott's bandwidth rule (scipy.stats.gaussian_kde). "
         "Applied to pooled wet-day values (≥1 mm) across all stations."),
        ("KS", "Kolmogorov-Smirnov Test",
         "Two-sample KS test (scipy.stats.ks_2samp). "
         "H₀: two samples drawn from same distribution. p≥0.05 = not significantly different."),
        ("KGE", "Kling-Gupta Efficiency",
         "KGE = 1 − √[(r−1)² + (α−1)² + (β−1)²] where r = correlation, "
         "α = std ratio, β = mean ratio. Perfect = 1. "
         "Ref: Gupta et al. (2009) J. Hydrol. 377:80–91."),
        ("ETCCDI", "ETCCDI Extreme Indices",
         "Expert Team on Climate Change Detection and Indices. "
         "RX1day = max 1-day; RX5day = max 5-day (mm); SDII = simple daily intensity (mm/wet-day); "
         "R10mm/R20mm = days ≥10/20 mm; R95p/R99p = precip > P95/P99 (mm); "
         "CDD = max consec. dry days; CWD = max consec. wet days; PRCPTOT = annual wet total. "
         "Ref: Zhang et al. (2011) WIREs Clim Change 2:418–439."),
        ("QDM", "Quantile Delta Mapping",
         "Bias-correction preserving quantile structure of future changes. "
         "Ref: Cannon et al. (2015) J. Climate 28:6938–6959."),
        ("Ens", "Ensemble Mean Evaluation",
         "Multi-model ensemble mean computed as unweighted arithmetic mean across "
         f"{len(models)} CMIP6 models. Evaluated vs best individual model using KGE and RMSE."),
        ("Trend", "Trend Preservation Score",
         "Score = max(0, 1 − |β_QDM − β_obs| / |β_raw − β_obs|). "
         "Score = 1: QDM perfectly reproduces observed slope. "
         "Score > 1 raw: QDM overshoots observed trend."),
        ("", "Key References",
         "Mann (1945) Econometrica 13:245-259.\n"
         "Kendall (1975) Rank Correlation Methods. Griffin, London.\n"
         "Sen (1968) JASA 63:1379–1389.\n"
         "Zhang et al. (2011) WIREs Clim Change 2:418–439.\n"
         "Cannon et al. (2015) J. Climate 28:6938–6959.\n"
         "Gupta et al. (2009) J. Hydrol. 377:80–91.\n"
         "Knutti et al. (2017) Nat. Clim. Chang. 7:246–251."),
    ]
    alt = [PatternFill("solid", fgColor="DEEAF1"),
           PatternFill("solid", fgColor="FFFFFF")]
    for ri, (a, b, d) in enumerate(rows_info, 3):
        fl = alt[ri % 2]
        for ci, v in enumerate([a, b, d], 1):
            cell = xsc(ws, ri, ci, v, bold=(ci <= 2), sz=9,
                       align="center" if ci == 1 else "left", border=tb())
            cell.fill = fl
            if ci == 3:
                cell.alignment = Alignment(horizontal="left", vertical="top",
                                            wrap_text=True)
        ws.row_dimensions[ri].height = 58

    for ci, w in enumerate([8, 26, 72], 1):
        cw(ws, ci, w)


# ══════════════════════════════════════════════════════════════════════════════
# 15.  MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    sep = "=" * 72
    print(sep)
    print("  Trend & Distribution Analysis  v2.0")
    print("  Multi-Model CMIP6  │  Smart Province Detection")
    print("  Mann-Kendall + Sen's Slope + ETCCDI + PDF/CDF/QQ")
    print("  Per-Model Trend  │  Ensemble vs Best  │  QDM Preservation")
    print("  มาตรฐาน Nature / Elsevier / Q1")
    print(sep)

    work_dir = (sys.argv[1].strip('"').strip("'")
                if len(sys.argv) > 1 else
                str(Path(os.path.abspath(__file__)).parent))
    print(f"\n  Input folder: {work_dir}")

    # ── File Discovery ────────────────────────────────────────────────────
    obs_path, raw_dict, bc_dict, province = find_csvs_multi(work_dir)
    print(f"  Province   : '{province}'")
    print(f"  Observed   : {Path(obs_path).name}")

    models_raw = sorted(raw_dict.keys())
    models_bc  = sorted(bc_dict.keys())
    models_common = sorted(set(models_raw) & set(models_bc))

    print(f"  Raw models ({len(models_raw)}): {models_raw}")
    print(f"  BC  models ({len(models_bc)}): {models_bc}")
    print(f"  Common     ({len(models_common)}): {models_common}")

    # ── Output directory ─────────────────────────────────────────────────
    ts_str  = datetime.now().strftime("%Y%m%d_%H%M%S")
    prov_fs = province.replace(" ", "_")
    out_dir = Path(work_dir) / f"TrendDist_{prov_fs}_{ts_str}"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Output     : {out_dir}")
    print("-" * 72)

    # ── Load data ─────────────────────────────────────────────────────────
    print("\n  Loading data ...")
    obs_d, stns = load_daily(obs_path, "Observed")
    stns_str    = [str(s) for s in stns]
    period_obs  = f"{obs_d.index[0].year}–{obs_d.index[-1].year}"
    print(f"  Observed: {len(stns)} stations  │  {period_obs}")

    raw_dfs, bc_dfs = {}, {}
    for m in models_common:
        raw_dfs[m], _ = load_daily(raw_dict[m], f"Raw/{m}")
        bc_dfs[m],  _ = load_daily(bc_dict[m],  f"QDM/{m}")
        print(f"    {m}: Raw {raw_dfs[m].index[0].year}–{raw_dfs[m].index[-1].year}")

    period_sim = (f"{list(raw_dfs.values())[0].index[0].year}–"
                  f"{list(raw_dfs.values())[0].index[-1].year}"
                  if raw_dfs else "N/A")

    # Ensemble means
    print("\n  Computing ensemble means ...")
    raw_ens = ensemble_mean_df(raw_dfs, stns_str)
    bc_ens  = ensemble_mean_df(bc_dfs,  stns_str)
    if raw_ens is None or bc_ens is None:
        sys.exit("  ✗  Cannot compute ensemble mean — check your files")
    print(f"  Ensemble: {len(models_common)} models")

    smap = short_labels(stns_str)

    # ── Figure generation ─────────────────────────────────────────────────
    print("\n" + "-" * 72)
    print("  Generating figures ...")
    base = f"TrendDist_{prov_fs}"

    def op(suffix):
        return str(out_dir / f"{base}_{suffix}")

    # Fig A – Annual trend (ensemble mean)
    fig_annual_trend(
        obs_d, raw_ens, bc_ens, stns_str, province, period_obs,
        op("FigA_AnnualTrend.png"))

    # Fig A2 – Per-model annual trend  [NEW]
    fig_annual_trend_per_model(
        obs_d, raw_dfs, bc_dfs, stns_str, province, period_obs,
        op("FigA2_AnnualTrend_PerModel.png"))

    # Fig B – Extreme indices trend
    fig_extreme_trend(
        obs_d, raw_ens, bc_ens, stns_str, province, period_obs,
        op("FigB_ExtremeTrend.png"))

    # Fig C – PDF
    fig_pdf(
        obs_d, raw_ens, bc_ens, stns_str, province,
        op("FigC_PDF.png"))

    # Fig D – CDF
    fig_cdf(
        obs_d, raw_ens, bc_ens, stns_str, province,
        op("FigD_CDF.png"))

    # Fig E – Q-Q Plot
    fig_qq(
        obs_d, raw_ens, bc_ens, stns_str, province,
        op("FigE_QQ.png"))

    # Fig F – ETCCDI Heatmap
    fig_etccdi_heatmap(
        obs_d, raw_ens, bc_ens, stns_str, smap, province,
        op("FigF_ETCCDI_Heatmap.png"))

    # Fig G – Multi-timescale trend per model  [NEW]
    fig_multiscale_trend_per_model(
        obs_d, raw_dfs, bc_dfs, bc_ens, stns_str, province, period_obs,
        op("FigG_MultiScale_Trend_PerModel.png"))

    # Fig H – Ensemble vs best individual model  [NEW]
    fig_ensemble_vs_best(
        obs_d, bc_dfs, bc_ens, stns_str, province, period_obs,
        op("FigH_Ensemble_vs_Best.png"))

    # Fig I – QDM trend preservation  [NEW]
    fig_qdm_trend_preservation(
        obs_d, raw_dfs, bc_dfs, bc_ens, stns_str, province, period_obs,
        op("FigI_QDM_TrendPreservation.png"))

    # ── Excel ─────────────────────────────────────────────────────────────
    print("\n" + "-" * 72)
    print("  Building Excel workbook ...")
    out_xlsx = out_dir / f"{base}_Statistics.xlsx"
    wb = Workbook()
    wb.remove(wb.active)

    _xl_trend_sheet(wb, obs_d, raw_ens, bc_ens, stns_str, smap, province)
    _xl_etccdi_sheet(wb, obs_d, raw_ens, bc_ens, stns_str, smap, province)
    _xl_per_model_trend(wb, obs_d, raw_dfs, bc_dfs, stns_str, smap, province)
    _xl_distribution(wb, obs_d, raw_ens, bc_ens, stns_str, smap, province)
    _xl_methods(wb, province, period_obs, period_sim, len(stns_str),
                models_common)

    wb.save(str(out_xlsx))
    print(f"  ✓  {out_xlsx.name}")

    print()
    print(sep)
    print(f"  เสร็จสิ้น — 9 รูปภาพ  │  1 Excel (5 sheets)")
    print(f"  จังหวัด: '{province}'  │  โมเดล: {models_common}")
    print(f"  บันทึกใน: {out_dir}")
    print(sep)


if __name__ == "__main__":
    main()
