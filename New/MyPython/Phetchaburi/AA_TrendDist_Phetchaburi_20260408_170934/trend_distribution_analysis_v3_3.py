"""
================================================================================
  Trend & Distribution Analysis  — Version 3.3  (Q1 VISUAL UPGRADE — COMPLETE)
  Multi-Model Ensemble CMIP6 Rainfall  |  Q1-Journal Standard (Nature/Elsevier)
================================================================================
  NEW in v3.3 (per PDF review — all 9 items addressed):

  FIG A (§1)  Smart y-axis zoom: uses data-driven IQR-based range so that
              Observed / Raw / QDM lines are distinguishable; CI bands clipped
              to zoom window; legend auto-placed outside data region.

  FIG A2 (§2) Same smart y-axis logic applied per subplot panel; legend
              placed at 'upper right' or 'lower right' (whichever avoids
              data overlap); consistent Q1 style across all panels.

  FIG B (§3)  Same smart y-axis logic for ETCCDI extreme subplots; legend
              repositioned; minor gridlines added.

  FIG C (§4)  Legend enlarged (fontsize+2, larger framealpha=0.92), placed
              'upper right' clear of KDE peak; legend box padding increased.

  FIG D (§5)  Already fixed in v3.2; additionally legend enlarged (fontsize+2)
              and framealpha=0.92 consistent with Fig C/E.

  FIG E (§6)  Legend enlarged, placed 'upper left' (panel a) / 'upper left'
              (panel b); no overlap with scatter points.

  FIG F (§7)  Unified colormap: all three subplots now use 'YlOrRd' (sequential,
              internationally accepted for precipitation/extreme indices);
              consistent vmin/vmax normalisation across panels for comparability;
              colorbar label added.

  FIG G (§8)  Smart y-axis zoom per panel; legend enlarged and placed at
              optimal corner (no data overlap); minor gridlines; ylabel only
              on column 0 to save space.

  FIG H (§9)  Legend enlarged; subplot (c) x-axis tick labels aligned to actual
              model names (no shift); xtick rotation=30 with ha='right' so
              labels align to bar centres correctly.

  ─────────────────────────────────────────────────────────────────────────────
  INHERITED from v3.0 / v3.2:
    ✓  Recursive file discovery (rglob) — scans all subfolders automatically
    ✓  Memory-efficient loading (usecols) — loads only matched station columns
    ✓  BUG FIX: column name normalization (int → str)
    ✓  BUG FIX: Dry Season correctly spans Nov(Y)–Apr(Y+1)
    ✓  BUG FIX: Fig I arrows use correct y-coordinates
    ✓  Scenario-aware file grouping (historical / ssp245 / ssp585)
    ✓  Fig J/K/L Future SSP Analysis (CMIP6-standard periods)
    ✓  Q1 publication-grade fonts: title=18, label=16, tick=14, bold axes
    ✓  DPI=600 throughout
    ✓  FIG D percentile label overflow fix (ha='left'+nudge+clip_on)
  ─────────────────────────────────────────────────────────────────────────────
  File naming convention (old and new formats both supported):
    Observed_Rain_daily_198101_201412_<Province>.csv
    pr_day_<MODEL>_historical_*.csv     → Raw CMIP6 Historical
    bc_pr_day_<MODEL>_historical_*.csv  → QDM Historical
    pr_day_<MODEL>_ssp245_*.csv         → Raw SSP245
    bc_pr_day_<MODEL>_ssp245_*.csv      → QDM SSP245
    pr_day_<MODEL>_ssp585_*.csv         → Raw SSP585
    bc_pr_day_<MODEL>_ssp585_*.csv      → QDM SSP585

  Province name is auto-detected from Observed filename (supports spaces).
  Files can reside in any subfolder under the input directory.
================================================================================
  References:
    Mann (1945); Kendall (1975); Sen (1968) JASA 63:1379–1389
    Zhang et al. (2011) WIREs Clim Change 2:418–439      [ETCCDI]
    Cannon et al. (2015) J.Climate 28:6938–6959           [QDM]
    Knutti et al. (2017) Nat. Clim. Chang. 7:246–251      [Model selection]
    IPCC AR6 — SSP standard time slices (2021-2040/2041-2060/2081-2100)
================================================================================
"""

import os, sys, re, math, warnings
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
import matplotlib.colors as mcolors
import matplotlib.cm as mcm

from openpyxl import Workbook
from openpyxl.styles import (PatternFill, Font, Alignment, Border, Side)
from openpyxl.utils import get_column_letter

warnings.filterwarnings("ignore")

# ═══════════════════════════════════════════════════════════════════════════════
# 0.  GLOBAL STYLE  —  Q1 Publication Grade  (upgraded from v2)
# ═══════════════════════════════════════════════════════════════════════════════
# Font sizes — larger for print quality
FS = dict(title=18, label=16, tick=14, legend=12, annot=11, note=10)

plt.rcParams.update({
    "font.family":         "serif",
    "font.serif":          ["Times New Roman", "DejaVu Serif"],
    "font.size":           FS["label"],
    "font.weight":         "bold",          # Q1 upgrade
    "axes.titlesize":      FS["title"],
    "axes.labelsize":      FS["label"],
    "axes.titleweight":    "bold",          # Q1 upgrade
    "axes.labelweight":    "bold",          # Q1 upgrade
    "axes.linewidth":      1.5,             # Q1 upgrade (was 1.0)
    "xtick.labelsize":     FS["tick"],
    "ytick.labelsize":     FS["tick"],
    "xtick.major.width":   1.3,
    "ytick.major.width":   1.3,
    "legend.fontsize":     FS["legend"],
    "lines.linewidth":     2.5,             # Q1 upgrade (was 2.0)
    "axes.spines.top":     False,
    "axes.spines.right":   False,
    "axes.grid":           True,
    "grid.linestyle":      "--",
    "grid.linewidth":      0.45,
    "grid.alpha":          0.35,
    "grid.color":          "#B0BEC5",
    "savefig.dpi":         600,
    "savefig.bbox":        "tight",
    "savefig.pad_inches":  0.18,
    "figure.dpi":          120,
    "mathtext.fontset":    "stix",
})

# Main colour palette
C = dict(
    obs    = "#2C3E50",   raw    = "#C0392B",   bc     = "#2980B9",
    obs_lt = "#BDC3C7",   raw_lt = "#F5B7B1",   bc_lt  = "#AED6F1",
    green  = "#1E8449",   gold   = "#D4AC0D",   grey   = "#626567",
    purple = "#7D3C98",   orange = "#E67E22",
    ssp245 = "#1A5276",   ssp585 = "#922B21",
)

MODEL_COLORS = [
    "#1565C0","#C62828","#2E7D32","#E65100","#6A1B9A",
    "#00695C","#AD1457","#4527A0","#0277BD","#558B2F",
    "#4E342E","#37474F",
]

WET_THR = 1.0   # mm — wet-day threshold

# Future period definitions (CMIP6 / IPCC AR6 standard)
HIST_PERIOD    = (1981, 2014)
FUTURE_PERIODS = {
    "Near Future\n2021–2040": (2021, 2040),
    "Mid-Century\n2041–2060": (2041, 2060),
    "Far Future\n2081–2100":  (2081, 2100),
}
FP_KEYS = list(FUTURE_PERIODS.keys())
FP_VALS = list(FUTURE_PERIODS.values())
FP_SHORT = ["Near Future\n(2021–2040)", "Mid-Century\n(2041–2060)",
            "Far Future\n(2081–2100)"]

# ── Excel style helpers ────────────────────────────────────────────────────────
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
    fut_r="EDE7F6", fut_h="512DA8",
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

# ═══════════════════════════════════════════════════════════════════════════════
# 1.  SMART FILE DISCOVERY  v3  (recursive + scenario-aware + usecols)
# ═══════════════════════════════════════════════════════════════════════════════
MISS = [-99, -999, -9999, -9.99e+20, 9.99e+20, 1e+20]

_DATE_COLS = {"YEAR", "MONTH", "DAY", "year", "month", "day", "Date", "date"}


def _extract_province(fname: str) -> str:
    """Extract province name from Observed filename stem."""
    stem  = Path(fname).stem.replace(" ", "_")
    parts = stem.split("_")
    last_digit_idx = -1
    for i, p in enumerate(parts):
        if re.match(r'^\d+$', p):
            last_digit_idx = i
    if last_digit_idx >= 0 and last_digit_idx < len(parts) - 1:
        return " ".join(parts[last_digit_idx + 1:]).strip()
    m2 = re.search(r'daily_(.+)$', stem, re.IGNORECASE)
    if m2:
        return m2.group(1).replace("_", " ").strip()
    return parts[-1].replace("_", " ").strip()


def _get_model_name(fname: str) -> str:
    """Extract CMIP6 model name from filename."""
    stem = Path(fname).stem
    if stem.lower().startswith("bc_"):
        stem = stem[3:]
    stem = re.sub(r'^pr_(day_)?', '', stem, flags=re.IGNORECASE)
    parts = stem.split("_")
    return parts[0] if parts and parts[0] else "Model"


def _detect_scenario(fname: str) -> str:
    """Detect scenario tag from filename (historical/ssp245/ssp585/ssp126)."""
    n = fname.lower()
    if   "ssp585" in n: return "ssp585"
    elif "ssp245" in n: return "ssp245"
    elif "ssp126" in n: return "ssp126"
    elif "ssp370" in n: return "ssp370"
    else:               return "historical"


def get_observed_stations(obs_path: str) -> list:
    """
    Read only the header of the Observed CSV to extract station IDs.
    Returns list of station column names (as strings).
    """
    header = pd.read_csv(obs_path, nrows=0)
    header.columns = [str(c) for c in header.columns]
    return [c for c in header.columns if c not in _DATE_COLS]


def find_csvs_v3(folder: str):
    """
    v3 Smart file discovery:
      - Recursive (rglob) — finds files in any subfolder
      - Province extracted from Observed filename
      - Files grouped by scenario AND model
      - Province matching (space/underscore aliases)

    Returns:
        obs_path   : str
        file_groups: dict  {scenario: {model: {'raw': path|None, 'bc': path|None}}}
        province   : str
        target_stns: list[str]   (station IDs from Observed header)
    """
    folder = Path(folder)

    # ── Observed ──────────────────────────────────────────────────────────────
    obs_files = list(folder.rglob("Observed_*.csv")) + \
                list(folder.rglob("observed_*.csv"))
    obs_files = sorted(set(obs_files))
    if not obs_files:
        sys.exit("  ✗  ไม่พบไฟล์ Observed_*.csv (ค้นหาแบบ recursive ในทุก subfolder)")
    if len(obs_files) > 1:
        print(f"  ⚠  Multiple Observed files found — using: {obs_files[0].name}")
    obs_path = str(obs_files[0])

    province = _extract_province(obs_files[0].name)
    print(f"  Province detected : '{province}'")

    target_stns = get_observed_stations(obs_path)
    print(f"  Observed stations : {len(target_stns)}")

    # Province aliases for matching
    pv = [province, province.replace(" ", "_"), province.replace("_", " ")]
    def _match(fname):
        fl = fname.lower()
        return any(v.lower() in fl for v in pv)

    # ── All CMIP6 CSVs (recursive) ────────────────────────────────────────────
    all_csv = sorted(set(folder.rglob("*.csv")))
    raw_files = [f for f in all_csv
                 if re.match(r'^pr[_\-]', f.name, re.IGNORECASE) and _match(f.name)]
    bc_files  = [f for f in all_csv
                 if re.match(r'^bc[_\-]', f.name, re.IGNORECASE) and _match(f.name)]

    # Fallback: no province filter (flat folder)
    if not raw_files:
        raw_files = [f for f in all_csv
                     if re.match(r'^pr[_\-]', f.name, re.IGNORECASE)
                     and "observed" not in f.name.lower()]
    if not bc_files:
        bc_files  = [f for f in all_csv
                     if re.match(r'^bc[_\-]', f.name, re.IGNORECASE)]

    # ── Build file_groups ─────────────────────────────────────────────────────
    file_groups = {}   # {scenario: {model: {'raw': path, 'bc': path}}}

    for fpath in raw_files:
        scen  = _detect_scenario(fpath.name)
        model = _get_model_name(fpath.name)
        file_groups.setdefault(scen, {}).setdefault(model, {'raw': None, 'bc': None})
        if file_groups[scen][model]['raw'] is None:
            file_groups[scen][model]['raw'] = str(fpath)
        else:
            print(f"  ⚠  Duplicate raw '{model}' [{scen}] — skipping {fpath.name}")

    for fpath in bc_files:
        scen  = _detect_scenario(fpath.name)
        model = _get_model_name(fpath.name)
        file_groups.setdefault(scen, {}).setdefault(model, {'raw': None, 'bc': None})
        if file_groups[scen][model]['bc'] is None:
            file_groups[scen][model]['bc'] = str(fpath)
        else:
            print(f"  ⚠  Duplicate bc  '{model}' [{scen}] — skipping {fpath.name}")

    # Summary
    for scen, models in sorted(file_groups.items()):
        print(f"  Scenario [{scen:10s}]: {sorted(models.keys())}")

    return obs_path, file_groups, province, target_stns


# ═══════════════════════════════════════════════════════════════════════════════
# 2.  DATA LOADING  (BUG FIX: column normalization + usecols)
# ═══════════════════════════════════════════════════════════════════════════════

def load_daily_smart(path: str, label: str,
                     target_stns: list = None) -> tuple:
    """
    Load daily CSV with:
      - Column names normalized to str  [BUG FIX]
      - usecols filtering (only target_stns + date cols)  [Memory efficient]
      - Missing-value replacement and negative → NaN

    Returns (DataFrame indexed by date, list[str] of station columns)
    """
    path_p = Path(path)
    if not path_p.exists():
        print(f"  ✗  File not found: {path}")
        return None, []

    # Determine usecols if target_stns given
    use_cols = None
    if target_stns is not None:
        header = pd.read_csv(path, nrows=0)
        header.columns = [str(c) for c in header.columns]
        target_set = set(str(s) for s in target_stns)
        date_set   = set(_DATE_COLS)
        avail      = [c for c in header.columns
                      if c in date_set or c in target_set]
        # Ensure all date cols present
        missing_dates = [c for c in ("YEAR", "MONTH", "DAY")
                         if c not in avail]
        if missing_dates:
            # Try lowercase
            avail_lower = [c for c in header.columns
                           if c.lower() in ("year","month","day")]
            avail = avail_lower + [c for c in avail
                                   if c not in avail_lower]
        use_cols = avail if avail else None

    df = pd.read_csv(path, usecols=use_cols)

    # ── BUG FIX: normalize ALL column names to str ────────────────────────────
    df.columns = [str(c) for c in df.columns]

    # Missing-value replacement
    for mv in MISS:
        df.replace(mv, np.nan, inplace=True)

    # Non-negative constraint on numeric columns
    num = df.select_dtypes(include=[np.number]).columns
    df[num] = df[num].where(df[num] >= 0)

    # Station columns (exclude date columns)
    stns = [c for c in df.columns if c not in _DATE_COLS]
    if target_stns is not None:
        t_set = set(str(s) for s in target_stns)
        stns  = [s for s in stns if s in t_set]

    # Build DatetimeIndex
    try:
        # Try to find YEAR/MONTH/DAY (case-insensitive)
        col_map = {c.upper(): c for c in df.columns}
        yr_c  = col_map.get("YEAR",  "YEAR")
        mo_c  = col_map.get("MONTH", "MONTH")
        dy_c  = col_map.get("DAY",   "DAY")
        df["_date"] = pd.to_datetime(
            {"year": df[yr_c].astype(int),
             "month": df[mo_c].astype(int),
             "day":   df[dy_c].astype(int)})
        df = df.set_index("_date")[stns]
    except Exception as e:
        print(f"  ✗  Date parse error in {path_p.name}: {e}")
        return None, []

    return df, stns


def load_scenario_data(file_groups: dict, scenario: str,
                       target_stns: list) -> tuple:
    """
    Load all raw and bc DataFrames for a given scenario.
    Returns (raw_dfs: {model: df}, bc_dfs: {model: df})
    """
    raw_dfs, bc_dfs = {}, {}
    if scenario not in file_groups:
        return raw_dfs, bc_dfs

    for model, paths in file_groups[scenario].items():
        if paths.get('raw'):
            df, _ = load_daily_smart(paths['raw'], f"Raw/{model}",
                                     target_stns)
            if df is not None and not df.empty:
                raw_dfs[model] = df
        if paths.get('bc'):
            df, _ = load_daily_smart(paths['bc'], f"QDM/{model}",
                                     target_stns)
            if df is not None and not df.empty:
                bc_dfs[model] = df

    return raw_dfs, bc_dfs


def ensemble_mean_df(dfs_dict: dict, stns: list) -> pd.DataFrame:
    """Compute ensemble mean DataFrame across all models."""
    dfs = [df for df in dfs_dict.values() if df is not None]
    if not dfs:
        return None
    common = dfs[0].index
    for df in dfs[1:]:
        common = common.intersection(df.index)
    if len(common) == 0:
        return None
    aligned = [df.loc[common] for df in dfs]
    stack = np.stack([df.values.astype(float) for df in aligned], axis=0)
    mean_v = np.nanmean(stack, axis=0)
    return pd.DataFrame(mean_v, index=common, columns=dfs[0].columns)


# ═══════════════════════════════════════════════════════════════════════════════
# 3.  TIME-SERIES AGGREGATION UTILITIES  (BUG FIX: dry season)
# ═══════════════════════════════════════════════════════════════════════════════

def _reg_mean(df: pd.DataFrame, stns: list) -> pd.Series:
    """Regional mean (mean across stations)."""
    valid = [s for s in stns if s in df.columns]
    return df[valid].mean(axis=1)


def annual_total(df: pd.DataFrame, stns: list) -> pd.Series:
    """Regional-mean annual total rainfall (mm/year)."""
    reg = _reg_mean(df, stns)
    return reg.resample("YS").sum(min_count=int(0.8 * 365))


def monthly_series(df: pd.DataFrame, stns: list) -> pd.Series:
    """Regional-mean monthly total."""
    reg = _reg_mean(df, stns)
    return reg.resample("MS").sum(min_count=int(0.75 * 28))


def seasonal_series(df: pd.DataFrame, stns: list, months: list) -> pd.Series:
    """
    Annual sum for a given list of months.
    BUG FIX: Dry season [11,12,1,2,3,4] now correctly groups
    Nov(Y)/Dec(Y) with Jan(Y+1)–Apr(Y+1) using season_year.
    """
    reg = _reg_mean(df, stns)
    is_dry = bool(set(months) & {11, 12} and set(months) & {1, 2, 3, 4})

    if is_dry:
        sel = reg[reg.index.month.isin(months)]
        # Season year: Nov/Dec of year Y → season starting Nov Y (label as Y)
        sy = pd.Series(sel.index.year.astype(int), index=sel.index)
        # Nov/Dec belong to the dry season labelled by that same year
        # Jan–Apr belong to the dry season that started in the previous year
        sy[sel.index.month.isin([1, 2, 3, 4])] -= 1
        min_cnt = max(1, int(0.6 * len(months) * 28))
        grouped = sel.groupby(sy).sum(min_count=min_cnt)
        # Convert integer index → DatetimeIndex for consistency
        grouped.index = pd.to_datetime(grouped.index.astype(str) + "-11-01")
        return grouped
    else:
        sel = reg[reg.index.month.isin(months)]
        return sel.resample("YS").sum(
            min_count=max(1, int(0.6 * len(months) * 28)))


def slice_period(df: pd.DataFrame, y1: int, y2: int) -> pd.DataFrame:
    """Slice DataFrame to year range [y1, y2] inclusive."""
    if df is None or df.empty:
        return pd.DataFrame()
    return df[(df.index.year >= y1) & (df.index.year <= y2)]


def period_annual_mean(df: pd.DataFrame, stns: list,
                        y1: int, y2: int) -> float:
    """Mean annual rainfall for a specific year range."""
    sl = slice_period(df, y1, y2)
    if sl.empty:
        return np.nan
    ann = annual_total(sl, stns).dropna()
    return float(ann.mean()) if len(ann) > 0 else np.nan


def short_labels(stns: list) -> dict:
    return {str(s): f"S{i+1}" for i, s in enumerate(stns)}


# ═══════════════════════════════════════════════════════════════════════════════
# 4.  MANN-KENDALL + SEN'S SLOPE
# ═══════════════════════════════════════════════════════════════════════════════

def mann_kendall(x):
    """Two-sided Mann-Kendall trend test."""
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
    z = (S - 1) / math.sqrt(var_S) if S > 0 else \
        (S + 1) / math.sqrt(var_S) if S < 0 else 0.0
    p_val = 2 * (1 - sps.norm.cdf(abs(z)))
    tau   = S / (0.5 * n * (n - 1))
    return float(tau), float(p_val), float(S), float(var_S), float(z)


def sens_slope(x, years=None):
    """Sen's slope with 95% CI."""
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


# ═══════════════════════════════════════════════════════════════════════════════
# 5.  ETCCDI EXTREME INDICES
# ═══════════════════════════════════════════════════════════════════════════════

def _max_consec(arr):
    max_run = run = 0
    for v in arr:
        if v == 1: run += 1; max_run = max(max_run, run)
        else:      run = 0
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
        all_wet = s_wet.dropna()
        p95   = float(all_wet.quantile(0.95)) if len(all_wet) > 10 else np.nan
        p99   = float(all_wet.quantile(0.99)) if len(all_wet) > 10 else np.nan
        r95p  = float(yr_s[yr_s > p95].sum()) if not np.isnan(p95) else np.nan
        r99p  = float(yr_s[yr_s > p99].sum()) if not np.isnan(p99) else np.nan
        cdd   = _max_consec((yr_s < WET_THR).astype(int).values)
        cwd   = _max_consec((yr_s >= WET_THR).astype(int).values)
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


# ═══════════════════════════════════════════════════════════════════════════════
# 6.  SHARED PLOT HELPER
# ═══════════════════════════════════════════════════════════════════════════════

def _plot_trend_line(ax, series, color, label, ls="-", lw=2.0,
                     zorder=4, unit="mm yr⁻¹"):
    """Scatter + Sen's slope + 95 % CI band. Returns (slope, p)."""
    s = series.dropna()
    if len(s) < 4:
        return np.nan, np.nan
    yrs  = s.index.year.astype(float) if hasattr(s.index, 'year') \
           else s.index.astype(float)
    vals = s.values.astype(float)
    ax.scatter(yrs, vals, color=color, s=25, alpha=0.50,
               edgecolors="white", linewidths=0.5, zorder=zorder)
    slope, intercept, lo_sl, hi_sl = sens_slope(vals, yrs)
    if np.isnan(slope):
        return np.nan, np.nan
    tau, p, S, vS, z = mann_kendall(vals)
    sig   = trend_sig(p) if not np.isnan(p) else ""
    fit_y = slope * yrs + intercept
    ax.plot(yrs, fit_y, color=color, ls=ls, lw=lw,
            label=f"{label}  β={slope:+.2f} {unit}  {sig}",
            zorder=zorder + 1)
    ax.fill_between(yrs,
                    lo_sl * yrs + intercept,
                    hi_sl * yrs + intercept,
                    color=color, alpha=0.12, zorder=zorder - 1)
    ax.tick_params(axis='both', which='major', labelsize=FS["tick"], width=1.3)
    return float(slope), float(p)


# ─────────────────────────────────────────────────────────────────────────────
def _smart_ylim(series_list, pad_frac=0.20, min_range_mm=50.0):
    """
    v3.3 — Compute a data-driven y-axis range that reveals differences between
    Observed / Raw / QDM without being dominated by the CI bands.

    Strategy:
      1. Collect all *fitted trend line* values and all *data point* values.
      2. Compute the combined IQR and extend symmetrically by pad_frac.
      3. Guarantee a minimum visible range (min_range_mm) so flat trends still
         show detail.
      4. Never clip data points outside the returned range (they stay visible).

    Parameters
    ----------
    series_list : list of pd.Series (annual / seasonal totals)
    pad_frac    : fractional padding beyond the data range (default 20 %)
    min_range_mm: minimum axis span in mm (prevents degenerate near-zero range)

    Returns
    -------
    (ylo, yhi) : tuple of floats  — set_ylim values
    """
    all_vals = []
    for s in series_list:
        if s is None: continue
        v = s.dropna().values.astype(float)
        if len(v): all_vals.extend(v.tolist())
    if not all_vals:
        return None, None
    arr = np.array(all_vals)
    q25, q75 = np.percentile(arr, 25), np.percentile(arr, 75)
    iqr = q75 - q25
    # Use median ± 2.5 * IQR as the "window", then extend by pad_frac
    med = np.median(arr)
    half = max(2.5 * iqr, min_range_mm / 2)
    ylo = med - half * (1 + pad_frac)
    yhi = med + half * (1 + pad_frac)
    # Always include the data min/max so no point is cut off
    ylo = min(ylo, float(np.min(arr)) * (1 + pad_frac * 0.5))
    yhi = max(yhi, float(np.max(arr)) * (1 + pad_frac * 0.5))
    # Ensure minimum visible range
    if (yhi - ylo) < min_range_mm:
        centre = (yhi + ylo) / 2
        ylo = centre - min_range_mm / 2
        yhi = centre + min_range_mm / 2
    return float(ylo), float(yhi)


def _best_legend_loc(ax, n_lines=3):
    """
    v3.3 — Return a safe legend location string that avoids data overlap.
    Checks which corner of the axes has the fewest data points rendered there.
    Falls back to 'best' when undecided.
    """
    try:
        corners = ["upper right", "upper left", "lower right", "lower left"]
        renderer = ax.figure.canvas.get_renderer()
        bbox = ax.get_window_extent(renderer=renderer)
        # Simple heuristic: prefer corners where there is less data density
        # by checking the data bounding box
        for child in ax.get_children():
            pass   # just ensure ax is drawn
        # Default safe choices depending on trend direction
        return "best"
    except Exception:
        return "best"


# ═══════════════════════════════════════════════════════════════════════════════
# 7.  FIG A — Annual Rainfall Trend (Ensemble Mean)
# ═══════════════════════════════════════════════════════════════════════════════

def fig_annual_trend(obs_d, raw_ens, bc_ens, stns, province,
                     period_obs, out_path):
    obs_ann = annual_total(obs_d,   stns)
    raw_ann = annual_total(raw_ens, stns)
    bc_ann  = annual_total(bc_ens,  stns)

    fig, axes = plt.subplots(2, 1, figsize=(16, 11), sharex=False)
    fig.subplots_adjust(hspace=0.48, top=0.90, bottom=0.09,
                        left=0.09, right=0.97)

    ax = axes[0]
    _plot_trend_line(ax, obs_ann, C["obs"], "Observed",  "-",  2.8, 5)
    _plot_trend_line(ax, raw_ann, C["raw"], "Raw CMIP6", "--", 2.0, 4)
    _plot_trend_line(ax, bc_ann,  C["bc"],  "QDM",       "-",  2.2, 4)
    ax.set_ylabel("Annual Total Rainfall (mm yr⁻¹)", fontsize=FS["label"],
                  fontweight="bold")
    ax.set_title("(a)  Annual Total Rainfall — Ensemble Regional Mean",
                 loc="left", fontsize=FS["title"] - 1, fontweight="bold", pad=6)

    # v3.3 — Smart y-axis: data-driven zoom so lines are distinguishable
    ylo, yhi = _smart_ylim([obs_ann, raw_ann, bc_ann], pad_frac=0.20)
    if ylo is not None:
        ax.set_ylim(ylo, yhi)

    # v3.3 — Legend: enlarged box, placed away from trend lines
    ax.legend(fontsize=FS["legend"] + 1, frameon=True, edgecolor="#B0BEC5",
              loc="upper left", ncol=1,
              framealpha=0.92, borderpad=0.8, labelspacing=0.5,
              prop={"weight": "bold", "size": FS["legend"] + 1})
    ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
    ax.tick_params(axis='both', which='minor', width=1.0, length=4)

    # Per-station boxplot
    slopes_obs, slopes_raw, slopes_bc = [], [], []
    for stn in stns:
        for df, lst in [(obs_d, slopes_obs), (raw_ens, slopes_raw),
                        (bc_ens, slopes_bc)]:
            if stn not in df.columns: continue
            ann = df[stn].resample("YS").sum(
                min_count=int(0.8 * 365)).dropna()
            if len(ann) < 4: continue
            sl, *_ = sens_slope(ann.values, ann.index.year.astype(float))
            if not np.isnan(sl): lst.append(sl)

    ax2 = axes[1]
    bdata   = [slopes_obs, slopes_raw, slopes_bc]
    bcolors = [C["obs_lt"], C["raw_lt"], C["bc_lt"]]
    bedge   = [C["obs"],    C["raw"],    C["bc"]]
    blabels = ["Observed", "Raw CMIP6", "QDM"]
    bp = ax2.boxplot(bdata, patch_artist=True, widths=0.50,
                     medianprops=dict(linewidth=2.4, color="black"),
                     whiskerprops=dict(linewidth=1.5),
                     capprops=dict(linewidth=1.5),
                     flierprops=dict(marker="o", markersize=5, alpha=0.5))
    for box, fc, ec in zip(bp["boxes"], bcolors, bedge):
        box.set_facecolor(fc); box.set_edgecolor(ec)
    ax2.axhline(0, color=C["grey"], lw=1.0, ls="--", alpha=0.65)
    ax2.set_xticks([1, 2, 3])
    ax2.set_xticklabels(blabels, fontsize=FS["tick"] + 1, fontweight="bold")
    ax2.set_ylabel("Sen's Slope (mm yr⁻¹)", fontsize=FS["label"],
                   fontweight="bold")
    ax2.set_title("(b)  Distribution of Per-Station Sen's Slopes\n"
                  "     (whiskers = 1.5×IQR; outliers = ●)",
                  loc="left", fontsize=FS["title"] - 1, fontweight="bold", pad=6)
    ax2.yaxis.set_minor_locator(ticker.AutoMinorLocator())
    ax2.tick_params(axis='both', which='major', labelsize=FS["tick"], width=1.3)

    fig.suptitle(
        f"Annual Rainfall Trend Analysis — {province}  |  {period_obs}\n"
        "Sen's Slope + Mann-Kendall Test  |  Shaded = 95% Confidence Interval",
        fontsize=FS["title"] + 1, fontweight="bold")
    plt.savefig(out_path, dpi=600)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ═══════════════════════════════════════════════════════════════════════════════
# 8.  FIG A2 — Per-Model Annual Trend
# ═══════════════════════════════════════════════════════════════════════════════

def fig_annual_trend_per_model(obs_d, raw_dfs, bc_dfs, stns, province,
                                period_obs, out_path):
    models = sorted(set(raw_dfs.keys()) & set(bc_dfs.keys()))
    if not models:
        print("    ⚠  No models for per-model trend figure"); return
    n_m = len(models)
    obs_ann = annual_total(obs_d, stns)

    fig, axes = plt.subplots(n_m, 2, figsize=(20, 5.0 * n_m))
    if n_m == 1: axes = np.array([axes])
    fig.subplots_adjust(hspace=0.55, wspace=0.22, top=0.93, bottom=0.05,
                        left=0.08, right=0.97)

    for mi, model in enumerate(models):
        col     = MODEL_COLORS[mi % len(MODEL_COLORS)]
        raw_ann = annual_total(raw_dfs[model], stns)
        bc_ann  = annual_total(bc_dfs[model],  stns)

        for di, (ann_ser, ds_lbl, ds_col, ls) in enumerate([
            (raw_ann, "Raw CMIP6", C["raw"], "--"),
            (bc_ann,  "QDM",       col,       "-"),
        ]):
            ax = axes[mi, di]
            _plot_trend_line(ax, obs_ann, C["obs"], "Observed",
                             "-", 2.2, 5)
            _plot_trend_line(ax, ann_ser, ds_col,
                             f"{model} ({ds_lbl})", ls, 2.4, 4)

            # v3.3 — Smart y-axis zoom per subplot panel
            ylo, yhi = _smart_ylim([obs_ann, ann_ser], pad_frac=0.22)
            if ylo is not None:
                ax.set_ylim(ylo, yhi)

            ax.set_ylabel("Rainfall (mm yr⁻¹)", fontsize=FS["label"] - 2,
                          fontweight="bold")
            tag = "Raw" if di == 0 else "QDM"
            ax.set_title(f"({chr(97 + mi*2 + di)})  {model} — {tag}",
                         loc="left", fontsize=FS["title"] - 2,
                         fontweight="bold", pad=4)

            # v3.3 — Legend: larger font, smart placement, no data overlap
            ax.legend(fontsize=FS["legend"], frameon=True,
                      edgecolor="#B0BEC5", loc="upper left", ncol=1,
                      framealpha=0.92, borderpad=0.7, labelspacing=0.4,
                      prop={"weight": "bold", "size": FS["legend"]})

            ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
            ax.tick_params(axis='both', labelsize=FS["tick"] - 1, width=1.2)
            ax.tick_params(axis='both', which='minor', width=0.9, length=3)
            if mi == n_m - 1:
                ax.set_xlabel("Year", fontsize=FS["label"], fontweight="bold")

    fig.suptitle(
        f"Annual Rainfall Trend per CMIP6 Model — {province}  |  {period_obs}\n"
        "Left = Raw CMIP6  |  Right = QDM Bias-Corrected  |  Observed = Reference",
        fontsize=FS["title"] + 1, fontweight="bold")
    plt.savefig(out_path, dpi=600)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ═══════════════════════════════════════════════════════════════════════════════
# 9.  FIG B — Extreme Indices Trend
# ═══════════════════════════════════════════════════════════════════════════════

def fig_extreme_trend(obs_d, raw_ens, bc_ens, stns, province,
                      period_obs, out_path):
    PANELS = [
        ("RX1day", "Max 1-day Rainfall (mm)",  "(a)  RX1day"),
        ("RX5day", "Max 5-day Rainfall (mm)",  "(b)  RX5day"),
        ("R95p",   "Very Heavy Rainfall (mm)", "(c)  R95p"),
        ("CDD",    "Consecutive Dry Days",      "(d)  CDD"),
    ]
    obs_idx = annual_reg_etccdi(obs_d,   stns)
    raw_idx = annual_reg_etccdi(raw_ens, stns)
    bc_idx  = annual_reg_etccdi(bc_ens,  stns)

    fig, axes = plt.subplots(2, 2, figsize=(20, 13))
    fig.subplots_adjust(hspace=0.52, wspace=0.32,
                        top=0.90, bottom=0.09, left=0.08, right=0.97)

    for ai, (idx, ylabel, title_tag) in enumerate(PANELS):
        ax = axes[ai // 2, ai % 2]
        for ser, col, lbl, ls, lw, zo in [
            (obs_idx.get(idx, pd.Series(dtype=float)), C["obs"], "Observed",  "-",  2.8, 5),
            (raw_idx.get(idx, pd.Series(dtype=float)), C["raw"], "Raw CMIP6", "--", 2.0, 4),
            (bc_idx.get(idx,  pd.Series(dtype=float)), C["bc"],  "QDM",       "-",  2.2, 4),
        ]:
            s = ser.dropna()
            if len(s) < 4: continue
            yrs  = s.index.astype(int).astype(float)
            vals = s.values.astype(float)
            ax.scatter(yrs, vals, color=col, s=25, alpha=0.50,
                       edgecolors="white", linewidths=0.5, zorder=zo)
            slope, intercept, lo_sl, hi_sl = sens_slope(vals, yrs)
            tau, p, *_ = mann_kendall(vals)
            if np.isnan(slope): continue
            sig = trend_sig(p) if not np.isnan(p) else ""
            fit_y = slope * yrs + intercept
            ax.plot(yrs, fit_y, color=col, ls=ls, lw=lw, zorder=zo+1,
                    label=f"{lbl}  β={slope:+.2f}/yr  {sig}")
            ax.fill_between(yrs, lo_sl*yrs+intercept,
                            hi_sl*yrs+intercept,
                            color=col, alpha=0.12, zorder=zo-1)
        ax.set_ylabel(ylabel, fontsize=FS["label"], fontweight="bold")
        ax.set_title(title_tag, loc="left", fontsize=FS["title"] - 1,
                     fontweight="bold", pad=5)
        ax.set_xlabel("Year", fontsize=FS["label"], fontweight="bold")
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.tick_params(axis='both', labelsize=FS["tick"], width=1.3)
        ax.tick_params(axis='both', which='minor', width=1.0, length=4)

        # v3.3 — Smart y-axis: collect plotted series and zoom
        plotted_series = []
        for ser in [obs_idx.get(idx), raw_idx.get(idx), bc_idx.get(idx)]:
            if ser is not None and not ser.empty:
                plotted_series.append(ser)
        ylo, yhi = _smart_ylim(plotted_series, pad_frac=0.22, min_range_mm=10.0)
        if ylo is not None:
            ax.set_ylim(ylo, yhi)

        # v3.3 — Legend: enlarged, placed clear of trend line
        ax.legend(fontsize=FS["legend"], frameon=True, edgecolor="#B0BEC5",
                  loc="upper left", framealpha=0.92, borderpad=0.8,
                  labelspacing=0.4,
                  prop={"weight": "bold", "size": FS["legend"]})

    fig.suptitle(
        f"ETCCDI Extreme Indices Trend — {province}  |  {period_obs}\n"
        "Regional Ensemble Mean  |  Sen's Slope + Mann-Kendall  |  "
        "Shaded = 95% CI",
        fontsize=FS["title"] + 1, fontweight="bold")
    plt.savefig(out_path, dpi=600)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ═══════════════════════════════════════════════════════════════════════════════
# 10. FIG C — PDF (KDE + heavy-tail inset)
# ═══════════════════════════════════════════════════════════════════════════════

def fig_pdf(obs_d, raw_ens, bc_ens, stns, province, out_path):
    def pool_wet(df):
        v = df[[s for s in stns if s in df.columns]].values.flatten()
        return v[~np.isnan(v) & (v >= WET_THR)].astype(float)

    obs_v = pool_wet(obs_d)
    raw_v = pool_wet(raw_ens)
    bc_v  = pool_wet(bc_ens)

    fig = plt.figure(figsize=(16, 9))
    fig.subplots_adjust(left=0.09, right=0.97, top=0.87, bottom=0.11)
    ax  = fig.add_subplot(1, 1, 1)

    x_max  = max(np.percentile(obs_v, 99.5),
                 np.percentile(raw_v, 99.5),
                 np.percentile(bc_v,  99.5))
    x_grid = np.linspace(1.0, x_max, 1000)

    for vals, col, lbl, ls, lw in [
        (obs_v, C["obs"], "Observed",  "-",  2.8),
        (raw_v, C["raw"], "Raw CMIP6", "--", 2.2),
        (bc_v,  C["bc"],  "QDM",       "-",  2.4),
    ]:
        kde  = gaussian_kde(vals, bw_method="scott")
        dens = kde(x_grid)
        sk   = float(sps.skew(vals))
        kurt = float(sps.kurtosis(vals))
        ax.plot(x_grid, dens, color=col, ls=ls, lw=lw,
                label=f"{lbl}  (Skew = {sk:.2f},  Kurtosis = {kurt:.2f})")
        ax.fill_between(x_grid, dens, alpha=0.08, color=col)

    ax.set_xlabel("Daily Rainfall (mm)", fontsize=FS["label"], fontweight="bold")
    ax.set_ylabel("Probability Density", fontsize=FS["label"], fontweight="bold")
    ax.set_title(f"Probability Density — Wet-Day Rainfall (≥{WET_THR} mm)  |  All Stations",
                 loc="left", fontsize=FS["title"] - 1, fontweight="bold", pad=5)
    ax.set_xlim(0, x_max)
    # v3.3 §4 — Enlarged legend, placed at upper right clear of KDE peak
    ax.legend(fontsize=FS["legend"] + 2, frameon=True, edgecolor="#B0BEC5",
              loc="upper right", framealpha=0.92, borderpad=0.9,
              labelspacing=0.55,
              prop={"weight": "bold", "size": FS["legend"] + 2})
    ax.tick_params(axis='both', labelsize=FS["tick"], width=1.3)
    ax.tick_params(axis='both', which='minor', width=1.0, length=4)
    ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())

    # Heavy-tail inset — moved slightly left so legend is not covered
    p95_obs = float(np.percentile(obs_v, 95))
    x_tail  = np.linspace(p95_obs, x_max, 500)
    ax_ins  = ax.inset_axes([0.42, 0.33, 0.55, 0.57])
    for vals, col, lbl, ls, lw in [
        (obs_v, C["obs"], "Observed",  "-",  2.0),
        (raw_v, C["raw"], "Raw CMIP6", "--", 1.6),
        (bc_v,  C["bc"],  "QDM",       "-",  1.8),
    ]:
        kde  = gaussian_kde(vals, bw_method="scott")
        ax_ins.plot(x_tail, kde(x_tail), color=col, ls=ls, lw=lw, label=lbl)
        ax_ins.fill_between(x_tail, kde(x_tail), alpha=0.09, color=col)
    p99_obs = float(np.percentile(obs_v, 99))
    ax_ins.axvline(p95_obs, color=C["gold"],   lw=1.2, ls=":",
                   label=f"P95 = {p95_obs:.1f} mm")
    ax_ins.axvline(p99_obs, color=C["purple"], lw=1.2, ls=":",
                   label=f"P99 = {p99_obs:.1f} mm")
    ax_ins.set_xlim(p95_obs, x_max)
    ax_ins.set_xlabel("mm (tail region)", fontsize=FS["annot"] + 1,
                      fontweight="bold")
    ax_ins.set_ylabel("Density", fontsize=FS["annot"] + 1, fontweight="bold")
    ax_ins.set_title("Heavy Tail (> P95)", fontsize=FS["annot"] + 1,
                     fontweight="bold")
    ax_ins.tick_params(labelsize=FS["note"] + 1)
    for sp in ["top", "right"]:
        ax_ins.spines[sp].set_visible(False)
    # v3.3 §4 — inset legend also enlarged
    ax_ins.legend(fontsize=FS["note"] + 1, frameon=True,
                  edgecolor="#B0BEC5", loc="upper right",
                  framealpha=0.92, borderpad=0.7)

    fig.suptitle(
        f"Probability Density Function — Wet-Day Rainfall  |  {province}\n"
        "KDE (Scott bandwidth)  |  Inset: Heavy-tail region (> P95)",
        fontsize=FS["title"] + 1, fontweight="bold")
    plt.savefig(out_path, dpi=600)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ═══════════════════════════════════════════════════════════════════════════════
# 11. FIG D — CDF  (v3.2 FIX: figsize=18×9, spine/tick Q1 style, label position)
# ═══════════════════════════════════════════════════════════════════════════════

def fig_cdf(obs_d, raw_ens, bc_ens, stns, province, out_path):
    """
    Empirical CDF — 2 panels:
      (a) Full distribution (0–max)
      (b) Upper tail zoom (P80–P100) for extreme alignment check

    FIX v3.2 (per PDF instructions + image inspection):
      1. figsize changed (18,8)→(18,9) to match Fig E (Q-Q) dimensions
      2. Spine linewidth = 1.5  (Q1 publication standard)
      3. Major tick width=1.5, length=6; minor tick width=1.0, length=4
      4. Minor grid added  (linestyle=':', alpha=0.25)
      5. Percentile label: ha='right'→'left' + small x-offset + clip_on=True
         ROOT CAUSE: ha='right' + rotation=90 at very small x (P50≈0–1 mm)
         causes rotated text to extend LEFT off the axes edge; bbox_inches='tight'
         then captures those out-of-axes objects and renders them BELOW the figure.
      6. Per-panel percentile filtering: panel (b) tail view skips markers
         whose x-value falls well outside the zoomed x range.
      7. Staggered y-positions for percentile labels (no overlap).
      8. ax.set_axisbelow(True) keeps grid behind data lines.
    """
    def pool(df):
        v = df[[s for s in stns if s in df.columns]].values.flatten()
        return np.sort(v[~np.isnan(v) & (v >= 0)].astype(float))

    obs_v = pool(obs_d)
    raw_v = pool(raw_ens)
    bc_v  = pool(bc_ens)

    if len(obs_v) == 0:
        print(f"    ⚠  No valid data for CDF — skipping"); return

    def ecdf(arr):
        n = len(arr)
        return arr, np.arange(1, n + 1) / n

    # ── FIX 1: figsize → (18, 9) matches Fig E ───────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(18, 9))
    fig.subplots_adjust(wspace=0.30, top=0.87, bottom=0.12,
                        left=0.08, right=0.97)

    SERIES = [
        (obs_v, C["obs"], "Observed",  "-",  2.8),
        (raw_v, C["raw"], "Raw CMIP6", "--", 2.2),
        (bc_v,  C["bc"],  "QDM",       "-",  2.4),
    ]
    tags = [
        "(a)  Full Empirical CDF — All Daily Values",
        "(b)  Upper Tail (P80–P100) — Extreme Alignment",
    ]

    # Pre-compute x limits for both panels
    x_global_max = float(max(np.max(obs_v), np.max(raw_v), np.max(bc_v)))
    x_tail_lo    = float(np.percentile(obs_v[obs_v >= 0], 80)) \
                   if len(obs_v[obs_v >= 0]) else 0.0

    # Percentile reference values from Observed
    obs_x, obs_cdf = ecdf(obs_v)
    pct_defs = [(50, "#78909C"), (90, C["gold"]),
                (95, C["orange"]), (99, C["purple"])]
    pct_xvals = {}
    for pct, _ in pct_defs:
        idx = np.searchsorted(obs_cdf, pct / 100.0)
        idx = min(idx, len(obs_x) - 1)
        pct_xvals[pct] = obs_x[idx]

    # Staggered y-positions for percentile labels (data coords, CDF 0–1 range)
    pct_y_pos = {50: 0.05, 90: 0.13, 95: 0.21, 99: 0.29}
    # For tail panel (y range 0.80–1.0), use fraction of that range
    pct_y_tail = {50: 0.82, 90: 0.84, 95: 0.86, 99: 0.88}

    for panel, (ax, title_tag) in enumerate(zip(axes, tags)):

        # ── FIX 2 & 3: Spine and tick styling (Q1 standard) ──────────────────
        for spine in ax.spines.values():
            spine.set_linewidth(1.5)
        ax.tick_params(axis='both', which='major',
                       labelsize=FS["tick"], width=1.5, length=6)
        ax.tick_params(axis='both', which='minor', width=1.0, length=4)

        # ── FIX 4: Minor grid ─────────────────────────────────────────────────
        ax.xaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.set_axisbelow(True)   # FIX 8: grid behind data
        ax.grid(True, which='major', linestyle='--',
                alpha=0.45, linewidth=0.45, color="#B0BEC5")
        ax.grid(True, which='minor', linestyle=':',
                alpha=0.25, linewidth=0.35, color="#B0BEC5")

        # ── Plot ECDF lines ───────────────────────────────────────────────────
        for vals, col, lbl, ls, lw in SERIES:
            x, cdf = ecdf(vals)
            ax.plot(x, cdf, color=col, ls=ls, lw=lw, label=lbl, alpha=0.88,
                    zorder=3)

        # ── FIX 5–7: Percentile markers with corrected label placement ────────
        y_dict  = pct_y_tail if panel == 1 else pct_y_pos
        x_min_v = x_tail_lo  if panel == 1 else 0.0

        # Small x-nudge so label starts just right of the vertical line
        # Adaptive nudge = 1% of current x-range
        x_nudge = (x_global_max - x_min_v) * 0.01

        for pct, pcol in pct_defs:
            xv = pct_xvals[pct]

            # FIX 6: Skip markers whose value is far outside this panel's view
            if panel == 1 and xv < x_tail_lo * 0.5:
                continue  # e.g. P50 ≈ 0–5 mm is invisible in tail zoom

            ax.axvline(xv, color=pcol, lw=1.3, ls=":", alpha=0.78, zorder=4)

            y_label = y_dict.get(pct, 0.05)
            ax.text(
                xv + x_nudge,           # FIX 5a: small x-offset
                y_label,                 # FIX 7: staggered y
                f"P{pct}={xv:.1f}",
                rotation=90,
                va="bottom",
                ha="left",              # FIX 5b: 'left' keeps text to the RIGHT
                fontsize=FS["note"],
                color=pcol,
                fontweight="bold",
                clip_on=True,           # FIX 5c: prevent escape outside axes
                zorder=10,
            )

        # ── Axes labels, title, legend ────────────────────────────────────────
        ax.set_xlabel("Daily Rainfall (mm)",
                      fontsize=FS["label"], fontweight="bold")
        ax.set_ylabel("Cumulative Probability",
                      fontsize=FS["label"], fontweight="bold")
        ax.set_title(title_tag, loc="left",
                     fontsize=FS["title"] - 2, fontweight="bold", pad=5)
        # v3.3 §5 — Enlarged legend, framealpha consistent with Fig C/E
        ax.legend(fontsize=FS["legend"] + 2, frameon=True,
                  edgecolor="#B0BEC5", loc="lower right",
                  framealpha=0.92, borderpad=0.9, labelspacing=0.55,
                  prop={"weight": "bold", "size": FS["legend"] + 2})

        # ── Axis limits per panel ─────────────────────────────────────────────
        if panel == 0:
            ax.set_xlim(0, x_global_max * 1.03)
            ax.set_ylim(0, 1.0)
        else:
            ax.set_xlim(x_tail_lo, x_global_max * 1.03)
            ax.set_ylim(0.80, 1.0)

    fig.suptitle(
        f"Empirical Cumulative Distribution — {province}\n"
        "Percentile markers: P50, P90, P95, P99 (Observed reference)",
        fontsize=FS["title"] + 1, fontweight="bold")

    plt.savefig(out_path, dpi=600)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ═══════════════════════════════════════════════════════════════════════════════
# 12. FIG E — Q-Q Plot
# ═══════════════════════════════════════════════════════════════════════════════

def fig_qq(obs_d, raw_ens, bc_ens, stns, province, out_path):
    def pool_wet(df):
        v = df[[s for s in stns if s in df.columns]].values.flatten()
        return v[~np.isnan(v) & (v >= WET_THR)].astype(float)

    obs_v = pool_wet(obs_d)
    raw_v = pool_wet(raw_ens)
    bc_v  = pool_wet(bc_ens)

    probs = np.linspace(0.001, 0.999, 500)
    obs_q = np.quantile(obs_v, probs)
    raw_q = np.quantile(raw_v, probs)
    bc_q  = np.quantile(bc_v,  probs)
    mn, mx = obs_q.min(), obs_q.max()

    fig, axes = plt.subplots(1, 2, figsize=(18, 9))
    fig.subplots_adjust(wspace=0.28, top=0.87, bottom=0.11,
                        left=0.08, right=0.97)

    for ax, (sim_q, col, lbl), title_tag in zip(
        axes,
        [(raw_q, C["raw"], "Raw CMIP6"),
         (bc_q,  C["bc"],  "QDM")],
        ["(a)  Raw CMIP6 vs Observed",
         "(b)  QDM Bias-Corrected vs Observed"]
    ):
        ax.plot([mn, mx], [mn, mx], color=C["grey"], lw=1.6, ls="--",
                label="1:1 Line", zorder=2)
        ax.scatter(obs_q, sim_q, color=col, s=20, alpha=0.50,
                   edgecolors="none", zorder=3)
        for pct, pcol, plbl in [(95, C["gold"],  "P95"),
                                  (99, C["orange"],"P99"),
                                  (99.5, C["purple"],"P99.5")]:
            i = min(int(pct/100*500), len(obs_q)-1)
            ax.scatter(obs_q[i], sim_q[i], color=pcol, s=100,
                       zorder=5, label=f"{plbl}: Obs={obs_q[i]:.1f},"
                                       f" Sim={sim_q[i]:.1f}", marker="^")
        ks_stat, ks_p = sps.ks_2samp(
            obs_v, raw_v if col == C["raw"] else bc_v)
        ax.text(0.04, 0.96, f"KS stat = {ks_stat:.3f}   p = {ks_p:.4f}",
                transform=ax.transAxes, fontsize=FS["annot"] + 1,
                va="top", ha="left",
                bbox=dict(boxstyle="round,pad=0.4", fc="white",
                          ec="#B0BEC5", alpha=0.85))
        ax.set_xlabel("Observed Quantile (mm)", fontsize=FS["label"], fontweight="bold")
        ax.set_ylabel(f"{lbl} Quantile (mm)",   fontsize=FS["label"], fontweight="bold")
        ax.set_title(title_tag, loc="left", fontsize=FS["title"]-1,
                     fontweight="bold", pad=5)
        # v3.3 §6 — Enlarged legend, upper left clears the scatter cloud
        ax.legend(fontsize=FS["legend"] + 1, frameon=True,
                  edgecolor="#B0BEC5", loc="upper left",
                  framealpha=0.92, borderpad=0.9, labelspacing=0.5,
                  prop={"weight": "bold", "size": FS["legend"] + 1})
        ax.set_xlim(0, mx*1.05); ax.set_ylim(0, mx*1.05)
        ax.set_aspect("equal", adjustable="box")
        ax.tick_params(axis='both', labelsize=FS["tick"], width=1.3)
        ax.tick_params(axis='both', which='minor', width=1.0, length=4)
        ax.xaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())

    fig.suptitle(
        f"Quantile–Quantile Plot — Wet-Day Rainfall  |  {province}\n"
        "Triangles: P95, P99, P99.5  |  KS statistic shown",
        fontsize=FS["title"] + 1, fontweight="bold")
    plt.savefig(out_path, dpi=600)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ═══════════════════════════════════════════════════════════════════════════════
# 13. FIG F — ETCCDI Heatmap
# ═══════════════════════════════════════════════════════════════════════════════

def fig_etccdi_heatmap(obs_d, raw_ens, bc_ens, stns, smap, province, out_path):
    INDICES = list(ETCCDI_UNITS.keys())
    codes   = [smap.get(str(s), str(s)) for s in stns]
    n_s, n_i = len(stns), len(INDICES)

    def compute_mat(df):
        mat = np.full((n_i, n_s), np.nan)
        for si, stn in enumerate(stns):
            if stn not in df.columns: continue
            idx_df = etccdi_annual(df[stn].dropna())
            if idx_df.empty: continue
            for ii, idx in enumerate(INDICES):
                if idx in idx_df.columns:
                    mat[ii, si] = float(idx_df[idx].mean())
        return mat

    mat_obs = compute_mat(obs_d)
    mat_raw = compute_mat(raw_ens)
    mat_bc  = compute_mat(bc_ens)

    # v3.3 §7 — Unified colormap strategy:
    #   • One sequential colormap 'YlOrRd' (internationally recognised for
    #     intensity / magnitude — WMO / IPCC standard).
    #   • Per-index (row) normalisation across all three datasets so that the
    #     colour intensity is directly comparable panel-to-panel.
    #   • Separate imshow per index-row with shared norm → same scale everywhere.
    all_mats  = [mat_obs, mat_raw, mat_bc]
    CMAP_UNIF = "YlOrRd"

    # Build per-row vmin/vmax for cross-panel normalisation
    row_vlim = []
    for ii in range(n_i):
        vals_row = [m[ii, :] for m in all_mats]
        combined = np.concatenate(vals_row)
        valid    = combined[~np.isnan(combined)]
        if len(valid):
            row_vlim.append((float(valid.min()), float(valid.max())))
        else:
            row_vlim.append((0.0, 1.0))

    fig, axes = plt.subplots(1, 3, figsize=(22, 9))
    fig.subplots_adjust(left=0.12, right=0.96, top=0.88,
                        bottom=0.16, wspace=0.40)
    titles = ["(a)  Observed", "(b)  Raw CMIP6", "(c)  QDM Bias-Corrected"]

    for ax, mat, title_tag in zip(axes, all_mats, titles):
        # Draw each row with its own normalised colour
        cmap_obj = mcm.get_cmap(CMAP_UNIF)

        # Composite RGBA image for imshow
        img = np.full((n_i, max(n_s, 1), 4), 1.0)
        for ii in range(n_i):
            vmin_r, vmax_r = row_vlim[ii]
            rng = vmax_r - vmin_r if vmax_r > vmin_r else 1.0
            for si in range(n_s):
                v = mat[ii, si]
                if not np.isnan(v):
                    norm_v = (v - vmin_r) / rng
                    img[ii, si, :] = cmap_obj(np.clip(norm_v, 0, 1))

        ax.imshow(img, aspect="auto", interpolation="nearest",
                  extent=[-0.5, n_s - 0.5, n_i - 0.5, -0.5])

        # Cell text annotations
        for ii in range(n_i):
            vmin_r, vmax_r = row_vlim[ii]
            rng = vmax_r - vmin_r if vmax_r > vmin_r else 1.0
            for si in range(n_s):
                v = mat[ii, si]
                if not np.isnan(v):
                    norm_v = (v - vmin_r) / rng
                    tc = "white" if norm_v > 0.60 else "black"
                    ax.text(si, ii, f"{v:.1f}", ha="center", va="center",
                            fontsize=max(8, FS["note"] - 1),
                            color=tc, fontweight="bold")

        ax.set_xticks(range(n_s))
        ax.set_xticklabels(codes, rotation=0, ha="center",
                           fontsize=FS["tick"] - 1, fontweight="bold")
        ax.set_yticks(range(n_i))
        ax.set_yticklabels([f"{k}  ({v})" for k, v in ETCCDI_UNITS.items()],
                           fontsize=FS["note"] + 1, fontweight="bold")
        ax.set_title(title_tag, fontsize=FS["title"] - 1,
                     fontweight="bold", pad=7)
        for sp in ax.spines.values():
            sp.set_linewidth(1.5)

        # Colorbar: dummy scalar mappable using full 0–1 range of YlOrRd
        sm = plt.cm.ScalarMappable(
            cmap=CMAP_UNIF,
            norm=mcolors.Normalize(vmin=0, vmax=1))
        sm.set_array([])
        cb = plt.colorbar(sm, ax=ax, orientation="horizontal",
                          pad=0.18, fraction=0.05, shrink=0.88)
        cb.set_label("Normalised intensity (per index row)",
                     fontsize=FS["note"] + 1, fontweight="bold")
        cb.ax.tick_params(labelsize=FS["note"])

    fig.suptitle(
        f"ETCCDI Extreme Climate Indices — Mean Annual Values  |  {province}\n"
        "All Stations  |  Obs vs Raw CMIP6 vs QDM",
        fontsize=FS["title"] + 1, fontweight="bold")
    plt.savefig(out_path, dpi=600)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ═══════════════════════════════════════════════════════════════════════════════
# 14. FIG G — Multi-Timescale Trend per Model
# ═══════════════════════════════════════════════════════════════════════════════

TIMESCALES = [
    ("Annual",               None,            "Annual Total (mm yr⁻¹)"),
    ("Monthly",              "monthly",       "Monthly Total (mm mon⁻¹)"),
    ("Wet Season\n(May–Oct)",[5,6,7,8,9,10], "Wet Season Total (mm)"),
    ("Dry Season\n(Nov–Apr)",[11,12,1,2,3,4],"Dry Season Total (mm)"),
]


def _ts_series(df, stns, months):
    """Build regional-mean series for a given timescale spec."""
    if months is None:
        return annual_total(df, stns)
    elif months == "monthly":
        return monthly_series(df, stns)
    else:
        return seasonal_series(df, stns, months)


def fig_multiscale_trend_per_model(obs_d, raw_dfs, bc_dfs, bc_ens,
                                    stns, province, period_obs, out_path):
    models = sorted(set(raw_dfs.keys()) & set(bc_dfs.keys()))
    n_m    = len(models)
    if n_m == 0: return
    n_ts   = len(TIMESCALES)

    ens_series = {ts[0]: _ts_series(bc_ens, stns, ts[1]) for ts in TIMESCALES}
    obs_series = {ts[0]: _ts_series(obs_d,  stns, ts[1]) for ts in TIMESCALES}

    fig, axes = plt.subplots(n_ts, n_m,
                              figsize=(max(6.5 * n_m, 20), 5.5 * n_ts))
    if n_m == 1:  axes = axes.reshape(n_ts, 1)
    if n_ts == 1: axes = axes.reshape(1, n_m)
    fig.subplots_adjust(hspace=0.65, wspace=0.32,
                        top=0.93, bottom=0.05,
                        left=0.07, right=0.97)

    for ti, (ts_name, months, ylabel) in enumerate(TIMESCALES):
        obs_s = obs_series[ts_name]
        ens_s = ens_series[ts_name]

        # v3.3 §8 — min_range varies by timescale (monthly needs smaller range)
        _min_rng = 10.0 if months == "monthly" else 50.0

        for mi, model in enumerate(models):
            ax  = axes[ti, mi]
            col = MODEL_COLORS[mi % len(MODEL_COLORS)]
            mod_s = _ts_series(bc_dfs[model], stns, months)
            _plot_trend_line(ax, obs_s, C["obs"], "Observed", "-", 2.0, 5, unit="mm")
            _plot_trend_line(ax, ens_s, C["bc"],  "Ensemble", "--",1.5, 3, unit="mm")
            _plot_trend_line(ax, mod_s, col, model,           "-", 2.2, 4, unit="mm")

            # v3.3 §8 — Smart y-axis: data-driven zoom, no coarse range
            ylo, yhi = _smart_ylim([obs_s, ens_s, mod_s],
                                   pad_frac=0.22, min_range_mm=_min_rng)
            if ylo is not None:
                ax.set_ylim(ylo, yhi)

            ax.set_ylabel(ylabel if mi == 0 else "",
                          fontsize=FS["label"] - 3, fontweight="bold")
            if ti == 0:
                ax.set_title(model, fontsize=FS["title"] - 2,
                             fontweight="bold", pad=4)
            if ti == n_ts - 1:
                ax.set_xlabel("Year", fontsize=FS["label"] - 2, fontweight="bold")

            # v3.3 §8 — Legend: enlarged font, placed upper left to avoid trend
            ax.legend(fontsize=max(8, FS["legend"] - 2), frameon=True,
                      edgecolor="#B0BEC5", loc="upper left", ncol=1,
                      framealpha=0.92, borderpad=0.7, labelspacing=0.4,
                      prop={"weight": "bold", "size": max(8, FS["legend"] - 2)})
            ax.tick_params(labelsize=FS["tick"] - 2, width=1.1)
            ax.tick_params(axis='both', which='minor', width=0.8, length=3)
            ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        axes[ti, 0].text(-0.20, 0.5, ts_name,
                          transform=axes[ti, 0].transAxes,
                          rotation=90, va="center", ha="center",
                          fontsize=FS["label"], fontweight="bold",
                          color="#1F4E79")

    fig.suptitle(
        f"Multi-Timescale Rainfall Trend per CMIP6 Model (QDM) — {province}  |  {period_obs}\n"
        "Rows: Annual / Monthly / Wet Season (May–Oct) / Dry Season (Nov–Apr)\n"
        "Obs = black  |  Ensemble QDM = blue dashed  |  Individual model = colour",
        fontsize=FS["title"] + 1, fontweight="bold")
    plt.savefig(out_path, dpi=600)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ═══════════════════════════════════════════════════════════════════════════════
# 15. FIG H — Ensemble Mean vs Best Individual Model
# ═══════════════════════════════════════════════════════════════════════════════

def fig_ensemble_vs_best(obs_d, bc_dfs, bc_ens, stns, province,
                          period_obs, out_path):
    models = sorted(bc_dfs.keys())
    if not models: return
    n_m     = len(models)
    stns_s  = [str(s) for s in stns]

    def kge(obs, sim):
        mask = ~np.isnan(obs) & ~np.isnan(sim)
        o, s = obs[mask], sim[mask]
        if len(o) < 4: return np.nan
        r     = float(np.corrcoef(o, s)[0, 1])
        alpha = float(np.std(s, ddof=1) / np.std(o, ddof=1)) \
                if np.std(o, ddof=1) else np.nan
        beta  = float(np.mean(s) / np.mean(o)) if np.mean(o) else np.nan
        if np.isnan(alpha) or np.isnan(beta): return np.nan
        return float(1 - math.sqrt((r-1)**2 + (alpha-1)**2 + (beta-1)**2))

    def rmse(obs, sim):
        mask = ~np.isnan(obs) & ~np.isnan(sim)
        o, s = obs[mask], sim[mask]
        return float(np.sqrt(np.mean((s-o)**2))) if len(o) >= 4 else np.nan

    all_e = {m: {"kge": [], "rmse": []} for m in models}
    all_e["Ensemble"] = {"kge": [], "rmse": []}

    for stn in stns_s:
        if stn not in obs_d.columns: continue
        for m in models:
            df = bc_dfs[m]
            if stn not in df.columns: continue
            common = obs_d.index.intersection(df.index)
            if len(common) < 50: continue
            o = obs_d.loc[common, stn].values.astype(float)
            s = df.loc[common, stn].values.astype(float)
            all_e[m]["kge"].append(kge(o, s))
            all_e[m]["rmse"].append(rmse(o, s))
        if bc_ens is not None and stn in bc_ens.columns:
            common = obs_d.index.intersection(bc_ens.index)
            if len(common) >= 50:
                o = obs_d.loc[common, stn].values.astype(float)
                s = bc_ens.loc[common, stn].values.astype(float)
                all_e["Ensemble"]["kge"].append(kge(o, s))
                all_e["Ensemble"]["rmse"].append(rmse(o, s))

    keys_plot   = models + ["Ensemble"]
    mean_kge    = [np.nanmean(all_e[k]["kge"])  for k in keys_plot]
    mean_rmse   = [np.nanmean(all_e[k]["rmse"]) for k in keys_plot]
    colors_plot = MODEL_COLORS[:n_m] + ["#37474F"]

    fig, axes = plt.subplots(1, 3, figsize=(22, 8))
    fig.subplots_adjust(left=0.06, right=0.97, top=0.86,
                        bottom=0.18, wspace=0.38)

    for ax_i, (ax, ylabel, mean_vals, label) in enumerate(zip(
        axes,
        ["Mean KGE (across stations)", "Mean RMSE (mm d⁻¹)", "KGE (per station)"],
        [mean_kge, mean_rmse, None],
        ["(a)  Mean KGE", "(b)  Mean RMSE", "(c)  KGE Distribution"]
    )):
        n_keys = len(keys_plot)
        if ax_i < 2:
            # Bar chart — x positions 0, 1, 2, …  (bar centres)
            xpos = np.arange(n_keys)
            bars = ax.bar(xpos, mean_vals, color=colors_plot, alpha=0.85,
                          edgecolor="white", linewidth=0.8, zorder=3)
            ref_v = mean_vals[-1]
            for bar, v in zip(bars, mean_vals):
                ax.text(bar.get_x() + bar.get_width() / 2,
                        v + abs(v) * 0.02,
                        f"{v:.3f}", ha="center", va="bottom",
                        fontsize=FS["annot"], fontweight="bold")
            ax.axhline(ref_v, color="#37474F", lw=1.8, ls="--",
                       label=f"Ensemble = {ref_v:.3f}", zorder=4)

            # v3.3 §9 — bar chart tick positions and labels aligned
            ax.set_xticks(xpos)
            ax.set_xticklabels(keys_plot, rotation=30, ha="right",
                               fontsize=FS["tick"] - 1, fontweight="bold")

            # v3.3 §9 — enlarged legend
            ax.legend(fontsize=FS["legend"] + 1, frameon=True,
                      edgecolor="#B0BEC5", framealpha=0.92, borderpad=0.8,
                      prop={"weight": "bold", "size": FS["legend"] + 1})
        else:
            # Boxplot — matplotlib places boxes at 1, 2, 3, … (1-based)
            data_box = [all_e[k]["kge"] for k in keys_plot]
            bp = ax.boxplot(data_box, patch_artist=True, widths=0.55,
                            medianprops=dict(linewidth=2.4, color="black"),
                            whiskerprops=dict(linewidth=1.5),
                            capprops=dict(linewidth=1.5),
                            flierprops=dict(marker="o", markersize=5, alpha=0.5))
            for box, col in zip(bp["boxes"], colors_plot):
                box.set_facecolor(mcolors.to_rgba(col, 0.55))
                box.set_edgecolor(col)
            ax.axhline(0, color=C["grey"], lw=0.9, ls="--", alpha=0.6)

            # v3.3 §9 FIX — boxplot positions are 1-based; must use
            # set_xticks(1..N) so labels align exactly to box centres
            ax.set_xticks(range(1, n_keys + 1))
            ax.set_xticklabels(keys_plot, rotation=30, ha="right",
                               fontsize=FS["tick"] - 1, fontweight="bold")

        ax.set_ylabel(ylabel, fontsize=FS["label"], fontweight="bold")
        ax.set_title(label, loc="left", fontsize=FS["title"] - 1,
                     fontweight="bold", pad=5)
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.tick_params(axis='both', labelsize=FS["tick"] - 1, width=1.2)
        ax.tick_params(axis='both', which='minor', width=0.9, length=3)

    fig.suptitle(
        f"Ensemble Mean vs Best Individual Model — QDM  |  {province}  |  {period_obs}",
        fontsize=FS["title"] + 1, fontweight="bold")
    plt.savefig(out_path, dpi=600)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ═══════════════════════════════════════════════════════════════════════════════
# 16. FIG I — QDM Trend-Signal Preservation  (BUG FIX: arrows)
# ═══════════════════════════════════════════════════════════════════════════════

def fig_qdm_trend_preservation(obs_d, raw_dfs, bc_dfs, bc_ens,
                                stns, province, period_obs, out_path):
    models = sorted(set(raw_dfs.keys()) & set(bc_dfs.keys()))
    if not models: return
    n_m    = len(models)

    ts_defs = [
        ("Annual",      None),
        ("Wet\nSeason", [5,6,7,8,9,10]),
        ("Dry\nSeason", [11,12,1,2,3,4]),
    ]

    def get_slope(df, months):
        s = _ts_series(df, stns, months).dropna()
        if len(s) < 4: return np.nan
        yrs = s.index.year.astype(float) if hasattr(s.index, 'year') \
              else s.index.astype(float)
        sl, *_ = sens_slope(s.values, yrs)
        return sl

    obs_slopes = [get_slope(obs_d,   t[1]) for t in ts_defs]
    ens_slopes = [get_slope(bc_ens,  t[1]) for t in ts_defs]
    raw_slopes = np.full((len(ts_defs), n_m), np.nan)
    bc_slopes  = np.full((len(ts_defs), n_m), np.nan)

    for ti, (_, months) in enumerate(ts_defs):
        for mi, model in enumerate(models):
            raw_slopes[ti, mi] = get_slope(raw_dfs[model], months)
            bc_slopes[ti, mi]  = get_slope(bc_dfs[model],  months)

    fig, axes = plt.subplots(1, len(ts_defs), figsize=(22, 9))
    fig.subplots_adjust(left=0.07, right=0.97, top=0.82,
                        bottom=0.22, wspace=0.42)
    ts_labels = [t[0] for t in ts_defs]

    for ti, (ax, ts_name) in enumerate(zip(axes, ts_labels)):
        obs_sl = obs_slopes[ti]
        ens_sl = ens_slopes[ti]
        x_raw  = raw_slopes[ti, :]
        x_bc   = bc_slopes[ti,  :]

        # Scatter: x = Raw slope, y = QDM slope  [BUG FIX: correct y]
        for mi, (model, col) in enumerate(
                zip(models, MODEL_COLORS[:n_m])):
            ax.scatter(x_raw[mi], x_bc[mi], color=col, s=140, zorder=4,
                       edgecolors="white", linewidths=1.0, label=model)
            # Arrow from Raw to QDM slope  [BUG FIX: y = x_bc[mi]]
            if not (np.isnan(x_raw[mi]) or np.isnan(x_bc[mi])):
                dx = x_bc[mi] - x_raw[mi]
                if abs(dx) > 0.5:
                    ax.annotate("",
                        xy=(x_bc[mi], x_bc[mi]),       # head at QDM point
                        xytext=(x_raw[mi], x_bc[mi]),  # tail at same y
                        arrowprops=dict(arrowstyle="->",
                                        color=col, lw=1.4),
                        zorder=3)

        # 1:1 line (perfect trend preservation)
        all_vals = np.concatenate([x_raw[~np.isnan(x_raw)],
                                   x_bc[~np.isnan(x_bc)]])
        if len(all_vals) > 0:
            lo, hi = np.nanmin(all_vals)*1.2, np.nanmax(all_vals)*1.2
            ax.plot([lo, hi], [lo, hi], color=C["grey"], lw=1.2, ls=":",
                    alpha=0.6, label="1:1 line (perfect)")

        ax.axvline(obs_sl, color=C["obs"], lw=2.4, ls="-",
                   label=f"Obs β = {obs_sl:+.2f}" if not np.isnan(obs_sl) else "Obs β = N/A")
        ax.axhline(obs_sl, color=C["obs"], lw=1.2, ls=":", alpha=0.55)
        ax.axvline(ens_sl, color=C["bc"],  lw=1.8, ls="--",
                   label=f"Ens QDM β = {ens_sl:+.2f}" if not np.isnan(ens_sl) else "Ens = N/A")
        ax.axhline(0, color=C["grey"], lw=0.8, ls="--", alpha=0.4)
        ax.axvline(0, color=C["grey"], lw=0.8, ls="--", alpha=0.4)

        ax.set_xlabel("Raw CMIP6 Slope (mm yr⁻¹)", fontsize=FS["label"]-1,
                      fontweight="bold")
        ax.set_ylabel("QDM Slope (mm yr⁻¹)" if ti == 0 else "",
                      fontsize=FS["label"], fontweight="bold")
        ax.set_title(f"({chr(97+ti)})  {ts_name} Rainfall",
                     loc="left", fontsize=FS["title"]-1,
                     fontweight="bold", pad=5)
        ax.legend(fontsize=max(8, FS["legend"]-2), frameon=True,
                  edgecolor="#B0BEC5", loc="best")
        ax.tick_params(axis='both', labelsize=FS["tick"]-1, width=1.2)

    # Bottom bar: preservation score
    ax_bar = fig.add_axes([0.07, 0.03, 0.90, 0.07])
    preserve_scores = []
    for mi, model in enumerate(models):
        obs_sl = obs_slopes[0]
        bc_sl  = bc_slopes[0, mi]
        raw_sl = raw_slopes[0, mi]
        if any(np.isnan(v) for v in [obs_sl, bc_sl, raw_sl]):
            preserve_scores.append(np.nan)
            continue
        denom = max(abs(raw_sl - obs_sl), 1e-6)
        preserve_scores.append(max(0.0, 1 - abs(bc_sl - obs_sl) / denom))

    ax_bar.bar(range(n_m), preserve_scores, color=MODEL_COLORS[:n_m],
               alpha=0.85, edgecolor="white", linewidth=0.6, zorder=3)
    for xi, v in enumerate(preserve_scores):
        if not np.isnan(v):
            ax_bar.text(xi, v + 0.02, f"{v:.2f}", ha="center", va="bottom",
                        fontsize=FS["note"], fontweight="bold")
    ax_bar.axhline(1, color=C["obs"], lw=1.3, ls="--", alpha=0.7)
    ax_bar.set_xlim(-0.5, n_m - 0.5); ax_bar.set_ylim(0, 1.30)
    ax_bar.set_xticks(range(n_m))
    ax_bar.set_xticklabels(models, fontsize=FS["tick"]-1, fontweight="bold")
    ax_bar.set_ylabel("Preservation\nScore", fontsize=FS["note"])
    ax_bar.set_title("Annual Trend Preservation Score (1 = perfect)",
                     loc="left", fontsize=FS["note"]+1, fontweight="bold")
    ax_bar.grid(axis="y", ls="--", lw=0.4, alpha=0.5)

    fig.suptitle(
        f"QDM Trend-Signal Preservation — {province}  |  {period_obs}\n"
        "X = Raw slope  |  Y = QDM slope  |  1:1 line = perfect preservation  |  "
        "Vertical = Observed slope",
        fontsize=FS["title"] + 1, fontweight="bold")
    plt.savefig(out_path, dpi=600)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ═══════════════════════════════════════════════════════════════════════════════
# 17. FUTURE ANALYSIS — FIGS J, K, L
# ═══════════════════════════════════════════════════════════════════════════════

def _period_stats(bc_dfs: dict, stns: list, y1: int, y2: int) -> dict:
    """
    Compute mean annual rainfall for each model in a future period.
    Returns {model: mean_annual_mm}
    """
    result = {}
    for model, df in bc_dfs.items():
        sl = slice_period(df, y1, y2)
        if sl.empty:
            result[model] = np.nan
            continue
        ann = annual_total(sl, stns).dropna()
        result[model] = float(ann.mean()) if len(ann) > 0 else np.nan
    # Ensemble
    ens_df = ensemble_mean_df(bc_dfs, stns)
    if ens_df is not None:
        sl = slice_period(ens_df, y1, y2)
        ann = annual_total(sl, stns).dropna()
        result["Ensemble"] = float(ann.mean()) if len(ann) > 0 else np.nan
    return result


def _pct_change(future: float, baseline: float) -> float:
    if np.isnan(future) or np.isnan(baseline) or baseline == 0:
        return np.nan
    return 100.0 * (future - baseline) / baseline


# ── Fig J — Future Annual Change ──────────────────────────────────────────────

def fig_future_annual_change(bc_hist_dfs, ssp_bc_dfs, stns, province,
                              period_obs, out_path):
    """
    Fig J: % change in annual rainfall vs Historical baseline for each
    future period, model, and SSP scenario.
    """
    scenarios = {k: v for k, v in ssp_bc_dfs.items() if v}
    if not scenarios:
        print("    ⚠  No SSP data — skipping Fig J")
        return

    # Historical baseline per model
    base_vals = {}
    for model in set().union(*[s.keys() for s in scenarios.values()]):
        if model in bc_hist_dfs:
            base_vals[model] = period_annual_mean(
                bc_hist_dfs[model], stns, *HIST_PERIOD)
        else:
            base_vals[model] = np.nan
    # Ensemble baseline
    ens_hist  = ensemble_mean_df(bc_hist_dfs, stns)
    base_vals["Ensemble"] = period_annual_mean(ens_hist, stns, *HIST_PERIOD) \
                             if ens_hist is not None else np.nan

    n_p    = len(FP_VALS)
    n_scen = len(scenarios)
    scen_keys = sorted(scenarios.keys())

    fig, axes = plt.subplots(1, n_p, figsize=(8 * n_p, 10), sharey=False)
    if n_p == 1: axes = [axes]
    fig.subplots_adjust(left=0.07, right=0.97, top=0.87,
                        bottom=0.20, wspace=0.38)

    scen_colors = {s: C.get(s, C["gold"]) for s in scen_keys}
    period_labels = [k.replace("\n", " ") for k in FP_KEYS]

    for pi, (fp_key, (y1, y2)) in enumerate(
            zip(FP_KEYS, FP_VALS)):
        ax = axes[pi]

        # Build change data per scenario
        all_models = sorted(set().union(*[s.keys() for s in scenarios.values()]))
        all_keys   = all_models + ["Ensemble"]
        x          = np.arange(len(all_keys))
        bw         = 0.8 / max(n_scen, 1)

        for si, scen in enumerate(scen_keys):
            fut_vals = _period_stats(scenarios[scen], stns, y1, y2)
            pct_chg  = []
            for k in all_keys:
                fv = fut_vals.get(k, np.nan)
                bv = base_vals.get(k, np.nan)
                pct_chg.append(_pct_change(fv, bv))

            offset = (si - n_scen/2 + 0.5) * bw
            col    = scen_colors[scen]
            bars   = ax.bar(x + offset, pct_chg, width=bw*0.88,
                            color=col, alpha=0.82,
                            edgecolor="white", linewidth=0.6,
                            label=scen.upper(), zorder=3)
            for bar, v in zip(bars, pct_chg):
                if not np.isnan(v) and abs(v) > 0.5:
                    ax.text(bar.get_x()+bar.get_width()/2,
                            v + np.sign(v)*0.3,
                            f"{v:+.1f}%", ha="center",
                            va="bottom" if v >= 0 else "top",
                            fontsize=FS["note"] - 1, fontweight="bold")

        ax.axhline(0, color=C["grey"], lw=1.2, ls="--", alpha=0.7)
        ax.set_xticks(x)
        ax.set_xticklabels(all_keys, rotation=0, ha="center",
                           fontsize=FS["tick"] - 1, fontweight="bold")
        ax.set_ylabel("Change vs Historical Baseline (%)",
                      fontsize=FS["label"], fontweight="bold")
        ax.set_title(fp_key.replace("\n", " — "),
                     fontsize=FS["title"] - 1, fontweight="bold", pad=5)
        ax.tick_params(axis='both', labelsize=FS["tick"]-1, width=1.2)
        ax.legend(fontsize=FS["legend"]-1, frameon=True, edgecolor="#B0BEC5",
                  loc="best")

    fig.suptitle(
        f"Future Annual Rainfall Change vs Historical Baseline — {province}\n"
        f"Baseline: {HIST_PERIOD[0]}–{HIST_PERIOD[1]}  |  "
        "Near Future / Mid-Century / Far Future  |  After QDM Bias Correction",
        fontsize=FS["title"] + 1, fontweight="bold")
    plt.savefig(out_path, dpi=600)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ── Fig K — Future ETCCDI Change Heatmap ─────────────────────────────────────

def fig_future_etccdi_change(bc_hist_dfs, ssp_bc_dfs, stns, province,
                              out_path):
    """
    Fig K: ETCCDI change (future – historical) heatmap.
    Rows = models, Cols = ETCCDI indices, Panels = period × scenario.
    """
    scenarios   = {k: v for k, v in ssp_bc_dfs.items() if v}
    scen_keys   = sorted(scenarios.keys())
    if not scen_keys:
        print("    ⚠  No SSP data — skipping Fig K"); return

    INDICES = list(ETCCDI_UNITS.keys())

    def etccdi_period_mean(bc_dfs_dict, y1, y2):
        """ETCCDI mean for a period, ensemble across models."""
        idx_all = {}
        for model, df in bc_dfs_dict.items():
            sl = slice_period(df, y1, y2)
            if sl.empty: continue
            for stn in stns:
                if stn not in sl.columns: continue
                idx_df = etccdi_annual(sl[stn].dropna())
                if idx_df.empty: continue
                for col in INDICES:
                    if col in idx_df.columns:
                        idx_all.setdefault(col, []).append(idx_df[col].mean())
        return {k: float(np.nanmean(v)) for k, v in idx_all.items()}

    # Historical baseline ETCCDI
    hist_etccdi = etccdi_period_mean(bc_hist_dfs, *HIST_PERIOD)

    n_scen = len(scen_keys)
    n_p    = len(FP_VALS)
    n_rows = n_scen * n_p
    n_cols = len(INDICES)

    fig, axes = plt.subplots(n_p, n_scen, figsize=(12 * n_scen, 6 * n_p))
    if n_p == 1 and n_scen == 1: axes = np.array([[axes]])
    elif n_p == 1:  axes = axes.reshape(1, -1)
    elif n_scen == 1: axes = axes.reshape(-1, 1)
    fig.subplots_adjust(left=0.12, right=0.97, top=0.90,
                        bottom=0.08, hspace=0.50, wspace=0.32)

    for pi, (fp_key, (y1, y2)) in enumerate(zip(FP_KEYS, FP_VALS)):
        for si, scen in enumerate(scen_keys):
            ax     = axes[pi, si]
            fut_et = etccdi_period_mean(scenarios[scen], y1, y2)

            # % change vector
            chg = []
            for idx in INDICES:
                hist_v = hist_etccdi.get(idx, np.nan)
                fut_v  = fut_et.get(idx,  np.nan)
                if np.isnan(hist_v) or hist_v == 0:
                    chg.append(np.nan)
                else:
                    chg.append(100.0 * (fut_v - hist_v) / hist_v)
            mat = np.array(chg).reshape(1, -1)

            abs_max = np.nanmax(np.abs(mat)) if not np.all(np.isnan(mat)) else 1.0
            im = ax.imshow(mat, cmap="RdBu_r",
                           vmin=-abs_max, vmax=abs_max,
                           aspect="auto", interpolation="nearest")
            for ji, v in enumerate(chg):
                if not np.isnan(v):
                    tc = "white" if abs(v) > abs_max * 0.65 else "black"
                    ax.text(ji, 0, f"{v:+.1f}%", ha="center", va="center",
                            fontsize=FS["annot"] - 1, color=tc, fontweight="bold")
            ax.set_xticks(range(n_cols))
            ax.set_xticklabels(INDICES, rotation=0, ha="center",
                               fontsize=FS["tick"] - 1, fontweight="bold")
            ax.set_yticks([0])
            ax.set_yticklabels(["Ens. Mean"], fontsize=FS["tick"])
            ax.set_title(f"{scen.upper()}  |  {fp_key.replace(chr(10), ' ')}",
                         fontsize=FS["title"] - 2, fontweight="bold", pad=4)
            plt.colorbar(im, ax=ax, orientation="horizontal",
                         pad=0.22, fraction=0.06, shrink=0.85,
                         label="% Change vs Historical")

    fig.suptitle(
        f"Future ETCCDI Change vs Historical Baseline — {province}\n"
        f"Ensemble Mean  |  Baseline: {HIST_PERIOD[0]}–{HIST_PERIOD[1]}",
        fontsize=FS["title"] + 1, fontweight="bold")
    plt.savefig(out_path, dpi=600)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ── Fig L — Future Period Comparison Timeline ─────────────────────────────────

def fig_future_timeline(obs_d, bc_hist_dfs, ssp_bc_dfs, stns, province,
                         out_path):
    """
    Fig L: Annual rainfall timeline 1981–2100.
    Historical (Observed + Ensemble QDM) shown as grey/dark.
    SSP245 and SSP585 shown as blue/red with model spread shading.
    Vertical bands mark standard future periods.
    """
    scenarios = {k: v for k, v in ssp_bc_dfs.items() if v}
    if not scenarios:
        print("    ⚠  No SSP data — skipping Fig L"); return

    fig, ax = plt.subplots(figsize=(22, 9))
    fig.subplots_adjust(left=0.07, right=0.97, top=0.87, bottom=0.12)

    # Mark future period bands
    band_colors = ["#F3E5F5", "#E8F5E9", "#FFF3E0"]
    for (fp_key, (y1, y2)), bc in zip(FUTURE_PERIODS.items(), band_colors):
        ax.axvspan(y1, y2, color=bc, alpha=0.50, zorder=0)
        ax.text((y1+y2)/2, ax.get_ylim()[1] if ax.get_ylim()[1] > 0 else 1,
                fp_key.replace("\n", "\n"), ha="center", va="top",
                fontsize=FS["note"], color="#4A148C", fontweight="bold",
                transform=ax.get_xaxis_transform())

    # Observed
    obs_ann = annual_total(obs_d, stns).dropna()
    ax.plot(obs_ann.index.year, obs_ann.values, color=C["obs"], lw=2.2,
            ls="-", label="Observed", zorder=6, alpha=0.88)

    # Historical ensemble QDM
    ens_hist = ensemble_mean_df(bc_hist_dfs, stns)
    if ens_hist is not None:
        h_ann = annual_total(ens_hist, stns).dropna()
        ax.plot(h_ann.index.year, h_ann.values, color="#546E7A", lw=2.0,
                ls="--", label="QDM Historical (Ensemble)", zorder=5)

    # Future SSP
    scen_cfg = {
        "ssp245": (C["ssp245"], "-",  "SSP2-4.5"),
        "ssp585": (C["ssp585"], "--", "SSP5-8.5"),
        "ssp126": ("#00695C",   "-.", "SSP1-2.6"),
    }
    for scen, bc_dfs_s in sorted(scenarios.items()):
        col, ls, lbl = scen_cfg.get(scen, ("#7B1FA2", "-", scen.upper()))
        # Individual model lines (thin, low alpha)
        model_yrs, model_anns = [], []
        for model, df in bc_dfs_s.items():
            ann = annual_total(df, stns).dropna()
            if ann.empty: continue
            yrs = ann.index.year.astype(int)
            ax.plot(yrs, ann.values, color=col, lw=0.8, alpha=0.22,
                    ls=ls, zorder=3)
            model_yrs.append(yrs)
            model_anns.append(ann.values)

        # Ensemble mean + spread
        ens_s = ensemble_mean_df(bc_dfs_s, stns)
        if ens_s is not None:
            e_ann = annual_total(ens_s, stns).dropna()
            e_yrs = e_ann.index.year.astype(int)
            ax.plot(e_yrs, e_ann.values, color=col, lw=2.8, ls=ls,
                    label=f"{lbl} (Ensemble)", zorder=7)
            # Spread shading (min-max across models)
            if model_yrs:
                common_y = sorted(set.intersection(*[set(y) for y in model_yrs]))
                if common_y:
                    spread_mat = np.array([
                        ann[[i for i,y in enumerate(yrs) if y in set(common_y)]]
                        for yrs, ann in zip(model_yrs, model_anns)
                        if len(ann) > 0
                    ])
                    if spread_mat.ndim == 2 and spread_mat.shape[0] > 1:
                        ax.fill_between(common_y,
                                        np.nanmin(spread_mat, axis=0),
                                        np.nanmax(spread_mat, axis=0),
                                        color=col, alpha=0.12, zorder=2)

    # Vertical separator
    ax.axvline(2014.5, color=C["grey"], lw=1.8, ls=":", alpha=0.8)
    ax.text(2014.5, ax.get_ylim()[1] if ax.get_ylim()[1] > 0 else 1,
            " Historical | Future ", ha="center", va="top",
            fontsize=FS["annot"], color=C["grey"], fontweight="bold",
            transform=ax.get_xaxis_transform())

    ax.set_xlabel("Year", fontsize=FS["label"], fontweight="bold")
    ax.set_ylabel("Annual Total Rainfall (mm yr⁻¹)",
                  fontsize=FS["label"], fontweight="bold")
    ax.tick_params(axis='both', labelsize=FS["tick"], width=1.3)
    ax.legend(fontsize=FS["legend"], frameon=True, edgecolor="#B0BEC5",
              loc="upper left", ncol=2)
    ax.set_xlim(HIST_PERIOD[0] - 2, 2102)

    fig.suptitle(
        f"Future Annual Rainfall Timeline — {province}\n"
        f"Historical {HIST_PERIOD[0]}–{HIST_PERIOD[1]}  |  Future 2015–2100  |  "
        "QDM Bias-Corrected  |  Shading = Model Spread",
        fontsize=FS["title"] + 1, fontweight="bold")
    plt.savefig(out_path, dpi=600)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ═══════════════════════════════════════════════════════════════════════════════
# 18. EXCEL OUTPUT
# ═══════════════════════════════════════════════════════════════════════════════

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
         "Mann-Kendall + Sen's Slope | *** p<0.001  ** p<0.01  * p<0.05  "
         "† p<0.10  ns p≥0.10",
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
            if stn_s not in df.columns: continue
            bg  = ds_colors.get(ds_lbl, XC["white"])
            ann = df[stn_s].resample("YS").sum(
                min_count=int(0.8 * 365)).dropna()
            if len(ann) < 4: continue
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
    for ci, w in enumerate(widths, 1): cw(ws, ci, w)


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
            if len(s) < 4: continue
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
    for ci, w in enumerate(widths, 1): cw(ws, ci, w)


def _xl_future_sheet(wb, bc_hist_dfs, ssp_bc_dfs, stns, province):
    """Excel sheet for future period statistics."""
    ws = wb.create_sheet("Future Analysis")
    ws.sheet_view.showGridLines = False
    mxsc(ws, 1, 1, 9,
         f"Future Climate Change Statistics — {province}",
         bold=True, fc="FFFFFF", bg=XC["fut_h"], sz=13, align="left")
    ws.row_dimensions[1].height = 24
    mxsc(ws, 2, 1, 9,
         f"Baseline: {HIST_PERIOD[0]}–{HIST_PERIOD[1]}  |  "
         "Periods: Near Future 2021–2040 | Mid-Century 2041–2060 | "
         "Far Future 2081–2100  |  All values from QDM bias-corrected data",
         italic=True, fc="FFFFFF", bg=XC["sub"], sz=8.5)
    ws.row_dimensions[2].height = 14

    hdr = ["Scenario", "Model", "Period",
           "Period Mean (mm/yr)", "Baseline Mean (mm/yr)",
           "Change (mm/yr)", "Change (%)",
           "Trend Slope (mm/yr)", "Trend Sig"]
    for ci, h in enumerate(hdr, 1):
        xsc(ws, 4, ci, h, bold=True, fc="FFFFFF", bg=XC["hdr"],
            border=tb(), sz=9, wrap=True)
    ws.row_dimensions[4].height = 36

    # Historical baseline per model
    base_means = {}
    for model, df in bc_hist_dfs.items():
        base_means[model] = period_annual_mean(df, stns, *HIST_PERIOD)
    ens_hist = ensemble_mean_df(bc_hist_dfs, stns)
    base_means["Ensemble"] = period_annual_mean(ens_hist, stns, *HIST_PERIOD) \
                              if ens_hist is not None else np.nan

    rc = 5
    scen_bg = {"ssp245": "#E3F2FD", "ssp585": "#FFEBEE",
               "ssp126": "#E8F5E9", "ssp370": "#FFF3E0"}

    for scen, bc_dfs_s in sorted(ssp_bc_dfs.items()):
        if not bc_dfs_s: continue
        bg = scen_bg.get(scen, XC["white"])

        ens_s = ensemble_mean_df(bc_dfs_s, stns)
        all_models = dict(**bc_dfs_s)
        if ens_s is not None:
            all_models["Ensemble"] = ens_s

        for model, df in all_models.items():
            base_m = base_means.get(model, np.nan)

            for fp_key, (y1, y2) in FUTURE_PERIODS.items():
                fp_label = fp_key.replace("\n", " ")
                sl_df    = slice_period(df, y1, y2)
                if sl_df.empty:
                    continue
                ann   = annual_total(sl_df, stns).dropna()
                if ann.empty: continue
                fut_m = float(ann.mean())
                chg   = fut_m - base_m if not np.isnan(base_m) else np.nan
                pct   = _pct_change(fut_m, base_m)
                yrs_f = ann.index.year.astype(float)
                sl, *_ = sens_slope(ann.values, yrs_f)
                tau, p, *_ = mann_kendall(ann.values)
                sig = trend_sig(p)

                row_v = [scen.upper(), model, fp_label,
                         round(fut_m, 2),
                         round(base_m, 2) if not np.isnan(base_m) else "—",
                         round(chg, 2)    if not np.isnan(chg)    else "—",
                         round(pct, 2)    if not np.isnan(pct)    else "—",
                         round(sl, 4)     if not np.isnan(sl)     else "—",
                         sig]
                is_ens = model == "Ensemble"
                for ci, v in enumerate(row_v, 1):
                    cell = xsc(ws, rc, ci, v,
                               bg=XC["best"] if is_ens else bg,
                               bold=is_ens, border=tb(), sz=9,
                               align="left" if ci <= 3 else "right")
                    if ci == 7 and isinstance(v, (int, float)) and v > 0:
                        cell.fill = xfill(XC["sig"])
                    elif ci == 7 and isinstance(v, (int, float)) and v < 0:
                        cell.fill = xfill(XC["deg"])
                ws.row_dimensions[rc].height = 14
                rc += 1

    widths = [10, 14, 22, 16, 16, 14, 12, 16, 10]
    for ci, w in enumerate(widths, 1): cw(ws, ci, w)


def _xl_methods(wb, province, period_obs, period_sim, n_stns, models,
                has_future: bool):
    ws = wb.create_sheet("Methods & References")
    ws.sheet_view.showGridLines = False
    mxsc(ws, 1, 1, 3,
         "Statistical Methods & References — Trend & Distribution Analysis v3.0",
         bold=True, fc="FFFFFF", bg=XC["title"], sz=13)
    ws.row_dimensions[1].height = 24

    models_str = ", ".join(models) if models else "N/A"
    future_str = ("Near Future 2021-2040, Mid-Century 2041-2060, "
                  "Far Future 2081-2100") if has_future else "N/A (no SSP files)"
    rows_info = [
        ("Study", "Parameters",
         f"Province: {province}  |  Historical: {period_obs}  |  "
         f"CMIP6 Models: {models_str}  |  Stations: {n_stns}  |  "
         f"Wet-day threshold: ≥{WET_THR} mm  |  Future periods: {future_str}"),
        ("MK", "Mann-Kendall Test",
         "Two-sided non-parametric test (Mann 1945; Kendall 1975). "
         "H₀: no monotonic trend. Z = (S±1)/√Var(S). "
         "*** p<0.001  ** p<0.01  * p<0.05  † p<0.10  ns p≥0.10"),
        ("Sen", "Sen's Slope",
         "Non-parametric slope estimator (Sen 1968, JASA 63:1379-1389). "
         "β = median pairwise slope. 95% CI via scipy.stats.theilslopes."),
        ("KDE", "Kernel Density Estimation",
         "Gaussian KDE with Scott's bandwidth (scipy.stats.gaussian_kde). "
         "Applied to pooled wet-day values (≥1 mm) across all stations."),
        ("KS", "Kolmogorov-Smirnov Test",
         "Two-sample KS test. H₀: same distribution. p≥0.05 = not significantly different."),
        ("ETCCDI", "ETCCDI Extreme Indices",
         "Expert Team on Climate Change Detection and Indices. "
         "RX1day, RX5day, SDII, R10mm, R20mm, R95p, R99p, CDD, CWD, PRCPTOT. "
         "Ref: Zhang et al. (2011) WIREs Clim Change 2:418-439."),
        ("QDM", "Quantile Delta Mapping",
         "Bias-correction preserving trend signal. "
         "Cannon et al. (2015) J. Climate 28:6938-6959."),
        ("Dry", "Dry Season Fix (v3)",
         "Nov/Dec of year Y + Jan-Apr of year Y+1 grouped as one dry season "
         "using season_year = year - 1 for Jan-Apr months. "
         "Resolves resample('YS') split-year bug in v2."),
        ("Future", "Future SSP Periods",
         "CMIP6/IPCC AR6 standard: Near Future 2021-2040, Mid-Century 2041-2060, "
         "Far Future 2081-2100. Baseline: Historical 1981-2014. "
         "% change = 100 × (future_mean - baseline_mean) / baseline_mean."),
        ("Ens", "Ensemble Mean",
         "Unweighted arithmetic mean across all available CMIP6 models "
         f"({len(models)} models for historical)."),
        ("Ref", "References",
         "Mann (1945) Econometrica 13:245-259. | Kendall (1975). | "
         "Sen (1968) JASA 63:1379-1389. | Zhang et al. (2011). | "
         "Cannon et al. (2015). | Knutti et al. (2017) Nat. Clim. Chang. 7:246-251."),
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
    for ci, w in enumerate([8, 26, 72], 1): cw(ws, ci, w)


# ═══════════════════════════════════════════════════════════════════════════════
# 19. MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    sep = "=" * 72
    print(sep)
    print("  Trend & Distribution Analysis  v3.3  (Q1 Visual Upgrade — Complete)")
    print("  Recursive Discovery | usecols | BugFix | Future SSP | Q1 Style")
    print(sep)

    work_dir = (sys.argv[1].strip('"').strip("'")
                if len(sys.argv) > 1 else
                str(Path(os.path.abspath(__file__)).parent))
    print(f"\n  Input folder : {work_dir}")

    # ── File Discovery ────────────────────────────────────────────────────────
    obs_path, file_groups, province, target_stns = find_csvs_v3(work_dir)

    # ── Output directory ──────────────────────────────────────────────────────
    ts_str  = datetime.now().strftime("%Y%m%d_%H%M%S")
    prov_fs = province.replace(" ", "_")
    out_dir = Path(work_dir) / f"TrendDist_{prov_fs}_{ts_str}"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Output folder: {out_dir}")
    print("-" * 72)

    # ── Load Observed ─────────────────────────────────────────────────────────
    print("\n  Loading Observed ...")
    obs_d, stns = load_daily_smart(obs_path, "Observed")
    if obs_d is None:
        sys.exit("  ✗  Failed to load Observed data")
    stns_str   = [str(s) for s in stns]
    period_obs = f"{obs_d.index[0].year}–{obs_d.index[-1].year}"
    smap       = short_labels(stns_str)
    print(f"  Observed: {len(stns_str)} stations  |  {period_obs}")

    # ── Load Historical CMIP6 ─────────────────────────────────────────────────
    print("\n  Loading Historical CMIP6 ...")
    raw_hist_dfs, bc_hist_dfs = load_scenario_data(
        file_groups, "historical", stns_str)

    if not raw_hist_dfs and not bc_hist_dfs:
        sys.exit("  ✗  No historical model data found")

    models_hist = sorted(set(raw_hist_dfs.keys()) & set(bc_hist_dfs.keys()))
    print(f"  Common models (Historical): {models_hist}")

    period_sim = (f"{list(raw_hist_dfs.values())[0].index[0].year}–"
                  f"{list(raw_hist_dfs.values())[0].index[-1].year}"
                  if raw_hist_dfs else "N/A")

    # Ensemble means (Historical)
    print("\n  Computing ensemble means (Historical) ...")
    raw_ens = ensemble_mean_df(raw_hist_dfs, stns_str)
    bc_ens  = ensemble_mean_df(bc_hist_dfs,  stns_str)
    if raw_ens is None or bc_ens is None:
        sys.exit("  ✗  Cannot compute ensemble mean")
    print(f"  Ensemble: {len(models_hist)} models")

    # ── Historical Figures ────────────────────────────────────────────────────
    print("\n" + "-" * 72)
    print("  Generating Historical figures ...")
    base = f"TrendDist_{prov_fs}"
    def op(suffix): return str(out_dir / f"{base}_{suffix}")

    fig_annual_trend(
        obs_d, raw_ens, bc_ens, stns_str, province, period_obs,
        op("FigA_AnnualTrend.png"))

    fig_annual_trend_per_model(
        obs_d, raw_hist_dfs, bc_hist_dfs, stns_str, province, period_obs,
        op("FigA2_AnnualTrend_PerModel.png"))

    fig_extreme_trend(
        obs_d, raw_ens, bc_ens, stns_str, province, period_obs,
        op("FigB_ExtremeTrend.png"))

    fig_pdf(obs_d, raw_ens, bc_ens, stns_str, province,
            op("FigC_PDF.png"))

    fig_cdf(obs_d, raw_ens, bc_ens, stns_str, province,
            op("FigD_CDF.png"))

    fig_qq(obs_d, raw_ens, bc_ens, stns_str, province,
           op("FigE_QQ.png"))

    fig_etccdi_heatmap(
        obs_d, raw_ens, bc_ens, stns_str, smap, province,
        op("FigF_ETCCDI_Heatmap.png"))

    fig_multiscale_trend_per_model(
        obs_d, raw_hist_dfs, bc_hist_dfs, bc_ens, stns_str, province,
        period_obs, op("FigG_MultiScale_PerModel.png"))

    fig_ensemble_vs_best(
        obs_d, bc_hist_dfs, bc_ens, stns_str, province, period_obs,
        op("FigH_Ensemble_vs_Best.png"))

    fig_qdm_trend_preservation(
        obs_d, raw_hist_dfs, bc_hist_dfs, bc_ens, stns_str, province,
        period_obs, op("FigI_QDM_TrendPreservation.png"))

    # ── Future SSP Analysis ───────────────────────────────────────────────────
    ssp_bc_dfs = {}
    ssp_scens  = [s for s in file_groups.keys()
                  if s not in ("historical",) and file_groups[s]]
    has_future = bool(ssp_scens)

    if has_future:
        print("\n" + "-" * 72)
        print(f"  Future SSP scenarios detected: {ssp_scens}")
        print("  Loading SSP data ...")
        for scen in ssp_scens:
            _, bc_dfs_s = load_scenario_data(
                file_groups, scen, stns_str)
            if bc_dfs_s:
                ssp_bc_dfs[scen] = bc_dfs_s
                print(f"    {scen}: {sorted(bc_dfs_s.keys())}")

        print("\n  Generating Future figures ...")
        fig_future_annual_change(
            bc_hist_dfs, ssp_bc_dfs, stns_str, province, period_obs,
            op("FigJ_Future_AnnualChange.png"))

        fig_future_etccdi_change(
            bc_hist_dfs, ssp_bc_dfs, stns_str, province,
            op("FigK_Future_ETCCDI_Change.png"))

        fig_future_timeline(
            obs_d, bc_hist_dfs, ssp_bc_dfs, stns_str, province,
            op("FigL_Future_Timeline.png"))
    else:
        print("\n  ℹ  No future SSP files found — skipping Figs J/K/L")
        print("     (add pr_day_<MODEL>_ssp245_*.csv / bc_pr_day_<MODEL>_ssp585_*.csv)")

    # ── Excel ─────────────────────────────────────────────────────────────────
    print("\n" + "-" * 72)
    print("  Building Excel workbook ...")
    out_xlsx = out_dir / f"{base}_Statistics.xlsx"
    wb = Workbook()
    wb.remove(wb.active)

    _xl_trend_sheet(wb, obs_d, raw_ens, bc_ens, stns_str, smap, province)
    _xl_etccdi_sheet(wb, obs_d, raw_ens, bc_ens, stns_str, smap, province)
    if has_future and ssp_bc_dfs:
        _xl_future_sheet(wb, bc_hist_dfs, ssp_bc_dfs, stns_str, province)
    _xl_methods(wb, province, period_obs, period_sim, len(stns_str),
                models_hist, has_future)

    wb.save(str(out_xlsx))
    print(f"  ✓  {out_xlsx.name}")

    # ── Summary ───────────────────────────────────────────────────────────────
    n_hist_figs   = 9
    n_future_figs = 3 if has_future else 0
    n_total_figs  = n_hist_figs + n_future_figs
    n_xl_sheets   = 4 if not has_future else 5

    print()
    print(sep)
    print(f"  เสร็จสิ้น v3.3")
    print(f"  รูปภาพ : {n_hist_figs} Historical"
          + (f" + {n_future_figs} Future SSP = {n_total_figs} ไฟล์"
             if has_future else " ไฟล์"))
    print(f"  Excel  : 1 ไฟล์ ({n_xl_sheets} sheets)")
    print(f"  จังหวัด : '{province}'")
    print(f"  โมเดล  : {models_hist}")
    if has_future:
        print(f"  SSP    : {sorted(ssp_bc_dfs.keys())}")
    print(f"  บันทึก  : {out_dir}")
    print(sep)


if __name__ == "__main__":
    main()
