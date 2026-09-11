"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  CMIP6 Bias Correction Evaluation — Publication Figures & Tables            ║
║  Figure 2–6  +  Table 1–3  |  มาตรฐาน Q2–Q4 / Nature / Elsevier           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Figure 2  – Annual Rainfall Time Series (1981–2014)                        ║
║  Figure 3  – Probability Distribution of Daily Rainfall                     ║
║  Figure 4  – Quantile–Quantile Plots                                        ║
║  Figure 5  – Taylor Diagram (Daily / Monthly / Wet Season)                  ║
║  Figure 6  – Improvement of Statistical Metrics (Bar chart)                 ║
║  Table 1   – CMIP6 Models Used                                              ║
║  Table 2   – Statistical Metrics Formulas                                   ║
║  Table 3   – Comparison of Statistical Metrics (Raw vs QDM)                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Input (auto-discovered, same folder as script OR via sys.argv[1]):         ║
║    Observed : *Observed*.csv  (YEAR, MONTH, DAY + StationID columns)       ║
║    Raw CMIP6: pr_<MODEL>_*.csv                                              ║
║    Bias-Corr: bc_<MODEL>_*.csv                                              ║
║                                                                              ║
║  Output (same folder as input):                                              ║
║    Output_Fig2_AnnualTimeSeries.png / .pdf                                  ║
║    Output_Fig3_ProbabilityDistribution.png / .pdf                           ║
║    Output_Fig4_QQPlots.png / .pdf                                           ║
║    Output_Fig5_TaylorDiagram.png / .pdf                                     ║
║    Output_Fig6_MetricImprovement.png / .pdf                                 ║
║    Output_Tables_BiasCorrection.xlsx  (3 sheets)                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  อ้างอิง:                                                                   ║
║    Taylor (2001) J. Geophys. Res. 106:7183–7192        [Taylor Diagram]    ║
║    Gupta et al. (2009) J. Hydrol. 377:80–91            [KGE]               ║
║    Nash & Sutcliffe (1970) J. Hydrol. 10:282–290       [NSE]               ║
║    Willmott (1981) Phys. Geogr. 2:184–194              [d / IoA]           ║
║    Cannon et al. (2015) J. Climate 28:6938–6959        [QDM]               ║
║    Karl et al. (1999) Int. J. Climatol. 19:405–420     [ETCCDI]            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import re
import math
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats as sps
from scipy.stats import gaussian_kde, wilcoxon

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker
import matplotlib.gridspec as gridspec
import matplotlib.colors as mcolors
from matplotlib.lines import Line2D
import matplotlib.cm as cm

from openpyxl import Workbook
from openpyxl.styles import (
    PatternFill, Font, Alignment, Border, Side
)
from openpyxl.utils import get_column_letter

warnings.filterwarnings("ignore")

# ════════════════════════════════════════════════════════════════════════════
#  §0  GLOBAL CONSTANTS & PUBLICATION STYLE
# ════════════════════════════════════════════════════════════════════════════

VERSION      = "1.0"
WET_THR      = 1.0            # mm/day — WMO wet-day threshold
WET_MONTHS   = [5,6,7,8,9,10] # May–October (Thai monsoon)
DRY_MONTHS   = [11,12,1,2,3,4]
MONTH_ABBR   = ["Jan","Feb","Mar","Apr","May","Jun",
                "Jul","Aug","Sep","Oct","Nov","Dec"]
SAVE_PDF     = True
DPI          = 600            # Publication resolution
MISS_FLAGS   = [-99,-999,-9999,-9.99e+20,9.99e+20,1e+20]

# Colour-blind–safe palette
C = dict(
    obs    = "#1B2838",   obs_lt = "#BDC3C7",
    raw    = "#C62828",   raw_lt = "#FFCDD2",   raw_bd = "#B71C1C",
    bc     = "#1565C0",   bc_lt  = "#BBDEFB",   bc_bd  = "#0D47A1",
    ens    = "#2E7D32",   ens_lt = "#C8E6C9",
    green  = "#1E8449",   gold   = "#F57F17",
    grey   = "#546E7A",   purple = "#6A1B9A",
    red2   = "#E53935",
)

# Per-model palette (up to 8 models, colour-blind safe)
MODEL_PALETTE = [
    "#1565C0","#C62828","#2E7D32","#E65100",
    "#6A1B9A","#00695C","#AD1457","#4527A0",
]

# Publication-grade matplotlib style
plt.rcParams.update({
    "font.family":        "serif",
    "font.serif":         ["Times New Roman", "DejaVu Serif"],
    "font.weight":        "bold",
    "font.size":          12,
    "axes.titlesize":     14,
    "axes.titleweight":   "bold",
    "axes.labelsize":     13,
    "axes.labelweight":   "bold",
    "xtick.labelsize":    11,
    "ytick.labelsize":    11,
    "legend.fontsize":    11,
    "figure.titlesize":   14,
    "lines.linewidth":    2.0,
    "axes.linewidth":     1.4,
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.grid":          True,
    "grid.linestyle":     "--",
    "grid.linewidth":     0.45,
    "grid.alpha":         0.45,
    "grid.color":         "#B0BEC5",
    "savefig.dpi":        DPI,
    "savefig.bbox":       "tight",
    "savefig.pad_inches": 0.15,
    "figure.dpi":         120,
    "mathtext.fontset":   "stix",
    "pdf.fonttype":       42,
    "ps.fonttype":        42,
})

# Excel style constants
XC = dict(
    title  = "13293D",  sub    = "1F4E79",  hdr    = "2E75B6",
    obs_r  = "E8F5E9",  raw_r  = "FFEBEE",  bc_r   = "E3F2FD",
    improve= "C8E6C9",  degrade= "FFCCBC",
    best   = "FFF9C4",  best_f = "E65100",
    white  = "FFFFFF",  alt    = "F5F5F5",
    note   = "ECEFF1",  rank1  = "FFD700",
)
THIN = Side(style="thin",   color="BDBDBD")
MED  = Side(style="medium", color="1F4E79")

def _tb():    return Border(left=THIN,right=THIN,top=THIN,bottom=THIN)
def _xfill(h): return PatternFill("solid", fgColor=h)

def _xsc(ws, r, c, val=None, bold=False, italic=False,
         fc=None, bg=None, align="center", sz=10, wrap=True):
    cell = ws.cell(row=r, column=c)
    if val is not None:
        cell.value = val
    cell.font = Font(bold=bold, italic=italic, name="Calibri", size=sz,
                     color=fc if fc else "1A1A1A")
    cell.alignment = Alignment(horizontal=align, vertical="center",
                                wrap_text=wrap)
    if bg:
        cell.fill = _xfill(bg)
    cell.border = _tb()
    return cell

def _mxsc(ws, r, c1, c2, val, **kw):
    ws.merge_cells(start_row=r, start_column=c1, end_row=r, end_column=c2)
    return _xsc(ws, r, c1, val, **kw)

def _cw(ws, col, w):
    ws.column_dimensions[get_column_letter(col)].width = w

def _rh(ws, r, h):
    ws.row_dimensions[r].height = h


def savefig(fig, path_stem: Path):
    """Save PNG (DPI=600) + optional PDF."""
    png_path = str(path_stem) + ".png"
    fig.savefig(png_path, dpi=DPI, bbox_inches="tight", pad_inches=0.15)
    if SAVE_PDF:
        fig.savefig(str(path_stem) + ".pdf", bbox_inches="tight",
                    pad_inches=0.15)
    plt.close(fig)
    print(f"  ✓  {Path(png_path).name}" + (" + .pdf" if SAVE_PDF else ""))


# ════════════════════════════════════════════════════════════════════════════
#  §1  FILE DISCOVERY
# ════════════════════════════════════════════════════════════════════════════

_SKIP_TOKENS = {
    "pr","bc","day","mon","yr","daily","monthly",
    "hist","historical","ssp245","ssp585","ssp126",
    "r1i1p1f1","r1i1p1f2","r11i1p1f1","gn","gr",
}


def _extract_model(fname: str) -> str:
    """
    Extract CMIP6 model name from filename.
    Handles: pr_MODEL_*, bc_MODEL_*, pr_day_MODEL_*, bc_pr_day_MODEL_*
    """
    stem  = Path(fname).stem
    body  = re.sub(r"^(bc_)?(pr_)?(day_)?", "", stem, flags=re.IGNORECASE)
    parts = [p for p in body.split("_") if p]
    for p in parts:
        p_lo = p.lower()
        if (p_lo not in _SKIP_TOKENS and
                not re.match(r"^\d{4,}$", p) and
                not re.match(r"r\d+i", p_lo)):
            return p
    return parts[0] if parts else "UnknownModel"


def discover_files(folder: str):
    """
    Scan folder (and one level of subfolders) for CSV files.

    Returns
    -------
    obs_path   : str
    raw_models : dict  {model_name: path}
    bc_models  : dict  {model_name: path}
    """
    folder_p = Path(folder)
    all_csv  = sorted(folder_p.rglob("*.csv"))

    obs_files = [f for f in all_csv if "observed" in f.name.lower()]
    raw_files = [f for f in all_csv
                 if f.name.lower().startswith("pr")
                 and "observed" not in f.name.lower()]
    bc_files  = [f for f in all_csv
                 if f.name.lower().startswith("bc")
                 and "observed" not in f.name.lower()]

    # Province-aware: prefer files whose name contains the same province keyword
    obs_path = str(obs_files[0]) if obs_files else None
    if len(obs_files) > 1:
        print(f"  ⚠  Multiple Observed files — using {obs_files[0].name}")

    # Extract province keyword from Observed filename for matching
    province_key = ""
    if obs_path:
        stem = Path(obs_path).stem.lower()
        # Strip date block e.g. _198101_201412
        stem = re.sub(r"_\d{6,}_\d{6,}", "", stem)
        stem = re.sub(r"observed_rain_daily_?", "", stem)
        province_key = stem.strip("_").replace("_", " ")

    # Known province keywords (to detect files that explicitly name a province)
    _KNOWN_PROVINCES = {
        "phetchaburi","prachuap","phuket","chonburi","rayong","trad",
        "chanthaburi","nakhon","surat","chumphon","ranong","krabi",
        "trang","satun","songkhla","pattani","yala","narathiwat",
        "bangkok","chiangmai","chiangrai","khon","udon","nong","ubon",
        "roi","loei","lopburi","ayutthaya","kanchanaburi","ratchaburi",
    }
    # Province words from the Observed file
    _obs_prov_words = {w for w in province_key.lower().split() if len(w) >= 3}

    def _match_province(f: Path) -> bool:
        """
        Accept file if:
          (a) No known province keyword in filename → local data, accept.
          (b) Its name shares at least one province word with the Observed file.
        Reject if it has a different province keyword (e.g. Phetchaburi when obs is Prachuap).
        """
        if not province_key:
            return True
        stem_lo = f.stem.lower().replace("_", " ")
        # Province keywords present in this filename
        file_provinces = {w for w in _KNOWN_PROVINCES if w in stem_lo}
        if not file_provinces:
            return True   # no province label → accept (same-folder convention)
        return bool(file_provinces & _obs_prov_words)

    raw_models: dict = {}
    for f in raw_files:
        if province_key and not _match_province(f):
            continue
        m = _extract_model(f.name)
        if m not in raw_models:
            raw_models[m] = str(f)
            print(f"  Raw  '{m}' ← {f.name}")

    bc_models: dict = {}
    for f in bc_files:
        if province_key and not _match_province(f):
            continue
        m = _extract_model(f.name)
        if m not in bc_models:
            bc_models[m] = str(f)
            print(f"  BC   '{m}' ← {f.name}")

    return obs_path, raw_models, bc_models


# ════════════════════════════════════════════════════════════════════════════
#  §2  DATA LOADING & AGGREGATION
# ════════════════════════════════════════════════════════════════════════════

def load_daily(path: str, label: str,
               target_stns: list = None) -> tuple:
    """
    Load daily CSV.  All station columns normalised to str (fixes int↔str bug).

    Parameters
    ----------
    target_stns : list of str station IDs (usecols filter for memory efficiency)
    """
    if path is None or not os.path.isfile(path):
        print(f"  ✗  Not found: {label}"); return None, []

    time_cols = {"YEAR", "MONTH", "DAY"}

    if target_stns is not None:
        tgt_set = set(str(s) for s in target_stns)
        tgt_int = set(int(s) for s in target_stns if str(s).isdigit())

        def _col_filter(col):
            c = str(col)
            return (c in time_cols or c in tgt_set or
                    (c.isdigit() and int(c) in tgt_int))
        try:
            df = pd.read_csv(path, usecols=_col_filter)
        except Exception:
            df = pd.read_csv(path)
    else:
        df = pd.read_csv(path)

    # Normalise all column names to str
    df.columns = [str(c) for c in df.columns]

    for mv in MISS_FLAGS:
        df.replace(mv, np.nan, inplace=True)
    num_cols = df.select_dtypes(include=[np.number]).columns
    df[num_cols] = df[num_cols].where(df[num_cols] >= 0)

    stns = [c for c in df.columns if c not in time_cols]

    # Keep only target stations (if given)
    if target_stns is not None:
        tgt_str = [str(s) for s in target_stns]
        stns = [s for s in stns if s in set(tgt_str)]
        extra = [c for c in df.columns
                 if c not in time_cols and c not in set(tgt_str)]
        if extra:
            df.drop(columns=extra, inplace=True, errors="ignore")

    try:
        df["date"] = pd.to_datetime(
            {"year": df["YEAR"], "month": df["MONTH"], "day": df["DAY"]}
        )
        df = df.set_index("date")[stns]
    except Exception:
        df = df[stns]

    yr_lo = df.index[0].year if len(df) else "?"
    yr_hi = df.index[-1].year if len(df) else "?"
    print(f"    {label:35s}: {len(df):,} rows × {len(stns)} stns  [{yr_lo}–{yr_hi}]")
    return df, stns


def to_monthly(df):
    if df is None: return None
    return df.resample("MS").apply(
        lambda g: g.sum(min_count=int(0.8 * len(g)))
    )


def to_annual(df):
    if df is None: return None
    return df.resample("YS").apply(
        lambda g: g.sum(min_count=int(0.8 * len(g)))
    )


def to_seasonal_wet(df):
    """Wet-season (May–Oct) annual totals."""
    if df is None: return None
    sub = df[df.index.month.isin(WET_MONTHS)]
    return sub.resample("YS").apply(
        lambda g: g.sum(min_count=int(0.5 * len(g)))
    )


def align_dfs(df1, df2):
    """Align two DataFrames on common DatetimeIndex."""
    if df1 is None or df2 is None: return None, None
    common = df1.index.intersection(df2.index)
    if len(common) == 0: return None, None
    return df1.loc[common], df2.loc[common]


def get_col(df, stn: str) -> np.ndarray:
    """Return non-NaN, non-negative values of a station column as float array."""
    if df is None: return np.array([], dtype=float)
    stn = str(stn)
    if stn not in df.columns: return np.array([], dtype=float)
    v = df[stn].values.astype(float)
    return v[~np.isnan(v) & (v >= 0)]


def period_str(df) -> str:
    if df is None: return "N/A"
    try:
        return f"{df.index[0].year}–{df.index[-1].year}"
    except Exception:
        return "N/A"


def short_stn_labels(stns: list) -> dict:
    return {str(s): f"S{i+1}" for i, s in enumerate(stns)}


def ensemble_mean(model_dfs: dict) -> pd.DataFrame:
    """Equal-weight ensemble mean of model DataFrames."""
    valid = [df for df in model_dfs.values() if df is not None]
    if not valid: return None
    common_idx = valid[0].index
    for df in valid[1:]:
        common_idx = common_idx.intersection(df.index)
    if len(common_idx) == 0: return None
    cols = list(valid[0].columns)
    for df in valid[1:]:
        cols = [c for c in cols if c in df.columns]
    if not cols: return None
    stack = np.stack(
        [df.loc[common_idx, cols].values.astype(float) for df in valid],
        axis=0
    )
    return pd.DataFrame(
        np.nanmean(stack, axis=0), index=common_idx, columns=cols
    )


def ensemble_spread(model_dfs: dict) -> tuple:
    """Return (ensemble_mean, lower_bound, upper_bound) for annual totals."""
    valid = [df for df in model_dfs.values() if df is not None]
    if len(valid) < 2: return None, None, None
    common_idx = valid[0].index
    for df in valid[1:]:
        common_idx = common_idx.intersection(df.index)
    cols = list(valid[0].columns)
    for df in valid[1:]:
        cols = [c for c in cols if c in df.columns]
    stack = np.stack(
        [df.loc[common_idx, cols].values.astype(float) for df in valid],
        axis=0
    )
    ens_mean = pd.DataFrame(np.nanmean(stack, axis=0), index=common_idx, columns=cols)
    ens_lo   = pd.DataFrame(np.nanmin(stack,  axis=0), index=common_idx, columns=cols)
    ens_hi   = pd.DataFrame(np.nanmax(stack,  axis=0), index=common_idx, columns=cols)
    return ens_mean, ens_lo, ens_hi


# ════════════════════════════════════════════════════════════════════════════
#  §3  PERFORMANCE METRICS  (academically correct)
# ════════════════════════════════════════════════════════════════════════════

def compute_metrics(o: np.ndarray, s: np.ndarray) -> dict:
    """
    Compute full performance metric suite for paired arrays.

    Metrics
    -------
    RMSE    : Root Mean Square Error
    MAE     : Mean Absolute Error
    MBE     : Mean Bias Error
    Pbias   : Percent Bias (%)
    r       : Pearson correlation coefficient
    NSE     : Nash–Sutcliffe Efficiency  [Nash & Sutcliffe 1970]
    KGE     : Kling–Gupta Efficiency     [Gupta et al. 2009]
    d       : Index of Agreement         [Willmott 1981]
    sigma_r : Standard deviation ratio (sim/obs)
    beta    : Mean ratio (sim/obs)
    """
    null = {k: np.nan for k in
            ["n","RMSE","MAE","MBE","Pbias","r","NSE",
             "KGE","d","sigma_r","beta","std_obs","std_sim"]}
    if len(o) < 5 or len(s) < 5:
        return null
    n = min(len(o), len(s))
    o = np.asarray(o[:n], dtype=float)
    s = np.asarray(s[:n], dtype=float)
    mask = ~np.isnan(o) & ~np.isnan(s)
    o, s = o[mask], s[mask]
    if len(o) < 5:
        return null

    e       = s - o
    rmse    = float(np.sqrt(np.mean(e ** 2)))
    mae     = float(np.mean(np.abs(e)))
    mbe     = float(np.mean(e))
    pbias   = float(100 * np.sum(e) / np.sum(o)) if np.sum(o) != 0 else np.nan
    r       = float(np.corrcoef(o, s)[0, 1])
    std_o   = float(np.std(o, ddof=1))
    std_s   = float(np.std(s, ddof=1))
    sigma_r = std_s / std_o if std_o > 0 else np.nan
    beta    = float(np.mean(s) / np.mean(o)) if np.mean(o) != 0 else np.nan
    dn_nse  = float(np.sum((o - np.mean(o)) ** 2))
    nse     = float(1 - np.sum(e ** 2) / dn_nse) if dn_nse > 0 else np.nan
    kge     = float(1 - math.sqrt(
        (r - 1) ** 2 + (sigma_r - 1) ** 2 + (beta - 1) ** 2
    )) if not (np.isnan(sigma_r) or np.isnan(beta)) else np.nan
    denom_d = float(np.sum(
        (np.abs(s - np.mean(o)) + np.abs(o - np.mean(o))) ** 2
    ))
    d = float(1 - np.sum(e ** 2) / denom_d) if denom_d > 0 else np.nan

    return {
        "n":       int(len(o)),
        "RMSE":    round(rmse,   3),
        "MAE":     round(mae,    3),
        "MBE":     round(mbe,    3),
        "Pbias":   round(pbias,  2),
        "r":       round(r,      4),
        "NSE":     round(float(nse), 4),
        "KGE":     round(float(kge), 4),
        "d":       round(float(d),   4),
        "sigma_r": round(float(sigma_r), 4) if not np.isnan(sigma_r) else np.nan,
        "beta":    round(float(beta),    4) if not np.isnan(beta)    else np.nan,
        "std_obs": round(std_o, 3),
        "std_sim": round(std_s, 3),
    }


def metrics_from_dfs(obs_df, sim_df, stn: str) -> dict:
    """Compute metrics for one station from aligned DataFrames."""
    if obs_df is None or sim_df is None:
        return compute_metrics(np.array([]), np.array([]))
    stn = str(stn)
    if stn not in obs_df.columns or stn not in sim_df.columns:
        return compute_metrics(np.array([]), np.array([]))
    common = obs_df.index.intersection(sim_df.index)
    if len(common) == 0:
        return compute_metrics(np.array([]), np.array([]))
    o = obs_df.loc[common, stn].values.astype(float)
    s = sim_df.loc[common, stn].values.astype(float)
    return compute_metrics(o, s)


# ════════════════════════════════════════════════════════════════════════════
#  §4  FIGURE 2 — ANNUAL RAINFALL TIME SERIES
# ════════════════════════════════════════════════════════════════════════════

def fig2_annual_timeseries(obs_d, raw_dfs: dict, bc_dfs: dict,
                            stns: list, smap: dict,
                            models: list, mc: list,
                            period_obs: str, out_dir: Path, prefix: str):
    """
    Figure 2: Annual Rainfall Time Series (1981–2014)
    Regional mean (all stations) with:
      - Observed: thick black line
      - Raw CMIP6: red dashed + individual model lines + ensemble spread shading
      - Bias-Corrected: blue solid + ensemble spread shading
    """
    stns_str = [str(s) for s in stns]

    # Compute regional-mean annual totals
    def regional_annual(df):
        if df is None: return None
        ann = to_annual(df)
        if ann is None: return None
        cols = [s for s in stns_str if s in ann.columns]
        if not cols: return None
        return ann[cols].mean(axis=1)

    obs_ann  = regional_annual(obs_d)
    raw_ann  = {m: regional_annual(df) for m, df in raw_dfs.items()}
    bc_ann   = {m: regional_annual(df) for m, df in bc_dfs.items()}

    # Ensemble statistics
    def ens_stats(ann_dict: dict):
        series = [s.dropna() for s in ann_dict.values() if s is not None]
        if not series: return None, None, None
        common = series[0].index
        for s in series[1:]: common = common.intersection(s.index)
        if len(common) == 0: return None, None, None
        stack = np.array([s.loc[common].values for s in series])
        return (pd.Series(np.nanmean(stack, axis=0), index=common),
                pd.Series(np.nanmin(stack,  axis=0), index=common),
                pd.Series(np.nanmax(stack,  axis=0), index=common))

    raw_ens, raw_lo, raw_hi = ens_stats(raw_ann)
    bc_ens,  bc_lo,  bc_hi  = ens_stats(bc_ann)

    fig, axes = plt.subplots(2, 1, figsize=(14, 11),
                              gridspec_kw={"hspace": 0.42})
    fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.09)

    # ── Panel (a): All-station regional mean ────────────────────────────
    ax = axes[0]

    # Ensemble spread shading
    def _plot_spread(ax, ens, lo, hi, col, lt, lbl):
        if ens is None: return
        yrs = ens.index.year
        ax.fill_between(yrs, lo.values, hi.values,
                        color=lt, alpha=0.35, zorder=2,
                        label=f"{lbl} range")
        ax.plot(yrs, ens.values,
                color=col, lw=2.2, ls="--" if "Raw" in lbl else "-",
                zorder=4, label=f"{lbl} ensemble mean")

    _plot_spread(ax, raw_ens, raw_lo, raw_hi, C["raw"], C["raw_lt"], "Raw CMIP6")
    _plot_spread(ax, bc_ens,  bc_lo,  bc_hi,  C["bc"],  C["bc_lt"],  "Bias-Corrected (QDM)")

    # Individual model lines (thin, semi-transparent)
    for m, col in zip(models, mc):
        if raw_ann.get(m) is not None:
            s = raw_ann[m].dropna()
            ax.plot(s.index.year, s.values,
                    color=col, lw=0.9, ls="--", alpha=0.55, zorder=3)
        if bc_ann.get(m) is not None:
            s = bc_ann[m].dropna()
            ax.plot(s.index.year, s.values,
                    color=col, lw=0.9, ls="-", alpha=0.55, zorder=3)

    # Observed
    if obs_ann is not None:
        obs_s = obs_ann.dropna()
        ax.plot(obs_s.index.year, obs_s.values,
                color=C["obs"], lw=2.8, ls="-", zorder=6,
                label="Observed")

    ax.set_xlabel("Year", fontsize=13, fontweight="bold")
    ax.set_ylabel("Annual Rainfall (mm)", fontsize=13, fontweight="bold")
    ax.set_title(
        "(a)  Regional Mean Annual Rainfall — All Stations",
        loc="left", fontsize=13, fontweight="bold", pad=5
    )
    ax.tick_params(axis="both", which="major", labelsize=11, width=1.5)
    ax.legend(fontsize=10, frameon=True, edgecolor="#B0BEC5",
              facecolor="white", framealpha=0.9,
              loc="upper right", ncol=2)
    ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    # ── Panel (b): Per-station KGE improvement ──────────────────────────
    ax2 = axes[1]
    codes = [smap[s] for s in stns_str]
    n_s   = len(stns)
    x     = np.arange(n_s)
    bw    = 0.38

    kge_raw = []
    kge_bc  = []
    for stn in stns_str:
        o_v = get_col(obs_d, stn)
        r_v = get_col(raw_dfs.get(list(raw_dfs.keys())[0]) if raw_dfs else None, stn)
        b_v = get_col(bc_dfs.get(list(bc_dfs.keys())[0]) if bc_dfs else None, stn)
        # Use ensemble BC/Raw for per-station metrics
        raw_ens_df = ensemble_mean(raw_dfs)
        bc_ens_df  = ensemble_mean(bc_dfs)
        mr = metrics_from_dfs(obs_d, raw_ens_df, stn)
        mb = metrics_from_dfs(obs_d, bc_ens_df,  stn)
        kge_raw.append(mr.get("KGE", np.nan))
        kge_bc.append(mb.get("KGE", np.nan))

    b1 = ax2.bar(x - bw/2, kge_raw, width=bw,
                 color=C["raw_lt"], edgecolor=C["raw_bd"],
                 linewidth=0.9, alpha=0.88, label="Raw CMIP6", zorder=3)
    b2 = ax2.bar(x + bw/2, kge_bc, width=bw,
                 color=C["bc_lt"], edgecolor=C["bc_bd"],
                 linewidth=0.9, alpha=0.88, label="Bias-Corrected (QDM)", zorder=3)

    ax2.axhline(0, color="#607D8B", lw=0.9, ls="--", alpha=0.7)
    ax2.axhline(0.75, color=C["green"], lw=1.0, ls=":",
                alpha=0.7, label="KGE = 0.75 (Very Good)")
    ax2.set_xticks(x)
    ax2.set_xticklabels(codes, rotation=0, ha="center", fontsize=11)
    ax2.set_xlabel("Station", fontsize=13, fontweight="bold")
    ax2.set_ylabel("KGE  (Kling–Gupta Efficiency)", fontsize=13, fontweight="bold")
    ax2.set_title(
        "(b)  KGE per Station — Ensemble Mean: Raw vs Bias-Corrected",
        loc="left", fontsize=13, fontweight="bold", pad=5
    )
    ax2.tick_params(axis="both", which="major", labelsize=11, width=1.5)
    ax2.legend(fontsize=10, frameon=True, edgecolor="#B0BEC5",
               facecolor="white", framealpha=0.9, loc="lower right", ncol=3)
    ax2.yaxis.set_minor_locator(ticker.AutoMinorLocator())

    fig.suptitle(
        f"Time series of annual rainfall during {period_obs} "
        "for observed data, raw CMIP6 simulations,\n"
        "and QDM bias-corrected rainfall",
        fontsize=13, fontweight="bold"
    )
    savefig(fig, out_dir / f"{prefix}_Fig2_AnnualTimeSeries")


# ════════════════════════════════════════════════════════════════════════════
#  §5  FIGURE 3 — PROBABILITY DISTRIBUTION
# ════════════════════════════════════════════════════════════════════════════

def fig3_probability_distribution(obs_d, raw_dfs: dict, bc_dfs: dict,
                                   stns: list, period_obs: str,
                                   out_dir: Path, prefix: str):
    """
    Figure 3: Probability Distribution of Daily Rainfall
    Layout: 1×2 — (a) full KDE with legend below, (b) heavy-tail inset panel.
    No legend overlap; both panels are clean and publication-ready.
    """
    stns_str = [str(s) for s in stns]

    def pool_wet(df):
        if df is None: return np.array([], dtype=float)
        cols = [s for s in stns_str if s in df.columns]
        v = df[cols].values.flatten().astype(float)
        return v[~np.isnan(v) & (v >= WET_THR)]

    obs_v = pool_wet(obs_d)
    raw_ens_df = ensemble_mean(raw_dfs)
    bc_ens_df  = ensemble_mean(bc_dfs)
    raw_v = pool_wet(raw_ens_df)
    bc_v  = pool_wet(bc_ens_df)

    if len(obs_v) < 20 or len(raw_v) < 20 or len(bc_v) < 20:
        print("  ⚠  Insufficient wet-day data for Fig 3"); return

    # Compute statistics once
    stats = {}
    for v, key in [(obs_v, "obs"), (raw_v, "raw"), (bc_v, "bc")]:
        stats[key] = {
            "sk": float(sps.skew(v)),
            "ku": float(sps.kurtosis(v, fisher=True)),
            "p95": float(np.percentile(v, 95)),
            "p99": float(np.percentile(v, 99)),
        }

    x_max = max(float(np.percentile(obs_v, 99.5)),
                float(np.percentile(raw_v, 99.5)),
                float(np.percentile(bc_v,  99.5)))

    # Dataset definitions: (values, color, label, linestyle, linewidth)
    datasets = [
        (obs_v, C["obs"], "Observed",             "-",  2.6, "obs"),
        (raw_v, C["raw"], "Raw CMIP6",            "--", 2.1, "raw"),
        (bc_v,  C["bc"],  "Bias-Corrected (QDM)", "-",  2.3, "bc"),
    ]

    # ── Figure layout: 1×2 ─────────────────────────────────────────────
    fig, (ax_main, ax_tail) = plt.subplots(1, 2, figsize=(16, 7.5))
    fig.subplots_adjust(left=0.08, right=0.97, top=0.87,
                        bottom=0.13, wspace=0.32)

    # ── Panel (a): Full PDF ─────────────────────────────────────────────
    x_grid = np.linspace(WET_THR, x_max, 1200)
    legend_lines = []
    for v, col, lbl, ls, lw, key in datasets:
        kde  = gaussian_kde(v, bw_method="scott")
        dens = kde(x_grid)
        sk   = stats[key]["sk"]
        ku   = stats[key]["ku"]
        line, = ax_main.plot(x_grid, dens, color=col, ls=ls, lw=lw, zorder=4)
        ax_main.fill_between(x_grid, dens, alpha=0.07, color=col, zorder=3)
        legend_lines.append((line, f"{lbl}\n(Skewness = {sk:.2f}, Kurtosis = {ku:.2f})"))

    # Percentile markers on main panel (vertical lines)
    p95_obs = stats["obs"]["p95"]
    p99_obs = stats["obs"]["p99"]
    ax_main.axvline(p95_obs, color=C["gold"],   lw=1.2, ls=":", alpha=0.80,
                    zorder=5, label=f"P95 (Obs) = {p95_obs:.1f} mm")
    ax_main.axvline(p99_obs, color=C["purple"], lw=1.2, ls=":", alpha=0.80,
                    zorder=5, label=f"P99 (Obs) = {p99_obs:.1f} mm")

    ax_main.set_xlabel("Daily Rainfall (mm)", fontsize=13, fontweight="bold")
    ax_main.set_ylabel("Probability Density",  fontsize=13, fontweight="bold")
    ax_main.set_title(
        "(a)  Full Distribution — Wet-Day Rainfall"
        f"\n     All stations pooled  |  Threshold ≥ {WET_THR} mm day⁻¹",
        loc="left", fontsize=13, fontweight="bold", pad=5
    )
    ax_main.set_xlim(0, x_max)
    ax_main.tick_params(axis="both", which="major", labelsize=11, width=1.5)
    ax_main.yaxis.set_minor_locator(ticker.AutoMinorLocator())

    # Legend: KDE lines + percentile lines, placed at upper right — no overlap
    legend_handles = [ln for ln, _ in legend_lines]
    legend_labels  = [lb for _, lb in legend_lines]
    # Add percentile markers to legend
    legend_handles.append(
        Line2D([0],[0], color=C["gold"],   lw=1.2, ls=":",
               label=f"P95 (Obs) = {p95_obs:.1f} mm"))
    legend_labels.append(f"P95 (Obs) = {p95_obs:.1f} mm")
    legend_handles.append(
        Line2D([0],[0], color=C["purple"], lw=1.2, ls=":",
               label=f"P99 (Obs) = {p99_obs:.1f} mm"))
    legend_labels.append(f"P99 (Obs) = {p99_obs:.1f} mm")

    ax_main.legend(
        legend_handles, legend_labels,
        fontsize=10.5, frameon=True, edgecolor="#B0BEC5",
        facecolor="white", framealpha=0.95,
        loc="upper right", ncol=1,
        handlelength=2.0, borderpad=0.8,
    )
    ax_main.spines["top"].set_visible(False)
    ax_main.spines["right"].set_visible(False)

    # ── Panel (b): Heavy-tail zoom (> P95 of Observed) ─────────────────
    x_tail = np.linspace(p95_obs, x_max, 600)
    for v, col, lbl, ls, lw, key in datasets:
        kde_t = gaussian_kde(v, bw_method="scott")
        dens_t = kde_t(x_tail)
        ax_tail.plot(x_tail, dens_t, color=col, ls=ls, lw=lw,
                     label=lbl, zorder=4)
        ax_tail.fill_between(x_tail, dens_t, alpha=0.09, color=col, zorder=3)

    # Mark P95 and P99 of each dataset for comparison
    marker_styles = [("obs", C["obs"], "Obs"),
                     ("raw", C["raw"], "Raw"),
                     ("bc",  C["bc"],  "BC")]
    for v_arr, col_v, short_lbl in [
        (obs_v, C["obs"], "Obs"),
        (raw_v, C["raw"], "Raw"),
        (bc_v,  C["bc"],  "BC"),
    ]:
        p99v = float(np.percentile(v_arr, 99))
        ax_tail.axvline(p99v, color=col_v, lw=1.0, ls="--", alpha=0.55)

    ax_tail.axvline(p95_obs, color=C["gold"],   lw=1.3, ls=":", alpha=0.85,
                    label=f"P95 (Obs) = {p95_obs:.1f} mm")
    ax_tail.axvline(p99_obs, color=C["purple"], lw=1.3, ls=":", alpha=0.85,
                    label=f"P99 (Obs) = {p99_obs:.1f} mm")

    ax_tail.set_xlim(p95_obs, x_max)
    ax_tail.set_xlabel("Daily Rainfall (mm)", fontsize=13, fontweight="bold")
    ax_tail.set_ylabel("Probability Density",  fontsize=13, fontweight="bold")
    ax_tail.set_title(
        "(b)  Heavy Tail  (> P95 of Observed)\n"
        "     Magnified view of extreme rainfall frequency",
        loc="left", fontsize=13, fontweight="bold", pad=5
    )
    ax_tail.tick_params(axis="both", which="major", labelsize=11, width=1.5)
    ax_tail.yaxis.set_minor_locator(ticker.AutoMinorLocator())
    # Separate, non-overlapping legend for tail panel
    ax_tail.legend(
        fontsize=10.5, frameon=True, edgecolor="#B0BEC5",
        facecolor="white", framealpha=0.95,
        loc="upper right", ncol=1,
        handlelength=2.0, borderpad=0.8,
    )
    ax_tail.spines["top"].set_visible(False)
    ax_tail.spines["right"].set_visible(False)

    fig.suptitle(
        f"Probability distribution of daily rainfall for observed data, "
        "raw CMIP6 simulations, and bias-corrected rainfall\n"
        f"Wet-day threshold ≥ {WET_THR} mm day⁻¹  |  Period: {period_obs}",
        fontsize=13, fontweight="bold"
    )
    savefig(fig, out_dir / f"{prefix}_Fig3_ProbabilityDistribution")


# ════════════════════════════════════════════════════════════════════════════
#  §6  FIGURE 4 — QUANTILE–QUANTILE PLOTS
# ════════════════════════════════════════════════════════════════════════════

def fig4_qq_plots(obs_d, raw_dfs: dict, bc_dfs: dict,
                  stns: list, period_obs: str,
                  out_dir: Path, prefix: str):
    """
    Figure 4: Q–Q Plots
    Side-by-side: (a) Observed vs Raw, (b) Observed vs Bias-Corrected.
    Pooled wet-day values, 200 quantile levels.
    """
    stns_str = [str(s) for s in stns]

    def pool_wet(df):
        if df is None: return np.array([], dtype=float)
        cols = [s for s in stns_str if s in df.columns]
        v = df[cols].values.flatten().astype(float)
        return np.sort(v[~np.isnan(v) & (v >= WET_THR)])

    obs_v = pool_wet(obs_d)
    raw_v = pool_wet(ensemble_mean(raw_dfs))
    bc_v  = pool_wet(ensemble_mean(bc_dfs))

    if len(obs_v) < 20 or len(raw_v) < 20 or len(bc_v) < 20:
        print("  ⚠  Insufficient data for Fig 4"); return

    probs  = np.linspace(0, 100, 201)
    q_obs  = np.percentile(obs_v, probs)
    q_raw  = np.percentile(raw_v, probs)
    q_bc   = np.percentile(bc_v,  probs)

    def _qq_rmse(qo, qs):
        return float(np.sqrt(np.mean((qs - qo) ** 2)))

    rmse_raw = _qq_rmse(q_obs, q_raw)
    rmse_bc  = _qq_rmse(q_obs, q_bc)

    xy_max_raw = max(q_obs.max(), q_raw.max()) * 1.04
    xy_max_bc  = max(q_obs.max(), q_bc.max())  * 1.04

    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    fig.subplots_adjust(wspace=0.30, top=0.88, bottom=0.12,
                        left=0.07, right=0.97)

    percentile_marks = [
        (90, C["grey"],   "P90",    "^"),
        (95, C["gold"],   "P95",    "s"),
        (99, C["purple"], "P99",    "D"),
        (99.5, C["red2"], "P99.5",  "*"),
    ]

    for ax, q_sim, sim_lbl, col_sim, xy_max, tag, rmse_val in [
        (axes[0], q_raw, "Raw CMIP6",            C["raw"], xy_max_raw,
         "(a)  Observed vs Raw CMIP6",   rmse_raw),
        (axes[1], q_bc,  "Bias-Corrected (QDM)", C["bc"],  xy_max_bc,
         "(b)  Observed vs Bias-Corrected (QDM)", rmse_bc),
    ]:
        # 1:1 reference line
        ax.plot([0, xy_max], [0, xy_max], color=C["green"],
                lw=1.6, ls="--", alpha=0.8,
                label="1:1 line (perfect agreement)", zorder=2)

        # Q–Q scatter (colour-coded by quantile level)
        scatter = ax.scatter(
            q_obs, q_sim,
            c=probs, cmap="RdYlBu_r", s=22, alpha=0.70,
            edgecolors="none", zorder=3
        )

        # Extreme quantile markers
        for pct, pct_col, pct_lbl, mk in percentile_marks:
            qo_v = float(np.percentile(obs_v, pct))
            qs_v = float(np.percentile(
                raw_v if "Raw" in sim_lbl else bc_v, pct
            ))
            ax.scatter([qo_v], [qs_v], color=pct_col, s=100, zorder=7,
                       marker=mk, edgecolors="white", linewidths=0.7,
                       label=f"{pct_lbl}: Obs={qo_v:.1f}, {sim_lbl[:3]}={qs_v:.1f}")

        ax.set_xlim(0, xy_max); ax.set_ylim(0, xy_max)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("Observed Quantile (mm)", fontsize=13, fontweight="bold")
        ax.set_ylabel(f"{sim_lbl} Quantile (mm)", fontsize=13, fontweight="bold")
        ax.set_title(
            f"{tag}\nQQ-RMSE = {rmse_val:.2f} mm",
            loc="left", fontsize=13, fontweight="bold", pad=5
        )
        ax.tick_params(axis="both", which="major", labelsize=11, width=1.5)
        ax.xaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.legend(fontsize=9, frameon=True, edgecolor="#B0BEC5",
                  facecolor="white", framealpha=0.92,
                  loc="upper left", ncol=1, handlelength=1.4)

        # Colour bar
        cb = plt.colorbar(scatter, ax=ax, orientation="horizontal",
                          pad=0.14, fraction=0.05, shrink=0.82)
        cb.set_label("Percentile level (%)", fontsize=10, fontweight="bold")
        cb.ax.tick_params(labelsize=9)

    fig.suptitle(
        "Quantile–Quantile plots comparing rainfall distributions "
        "between observed data and\nCMIP6 simulations before and after bias correction"
        f"  |  Period: {period_obs}",
        fontsize=13, fontweight="bold"
    )
    savefig(fig, out_dir / f"{prefix}_Fig4_QQPlots")


# ════════════════════════════════════════════════════════════════════════════
#  §7  FIGURE 5 — TAYLOR DIAGRAM
# ════════════════════════════════════════════════════════════════════════════

def _draw_taylor_background(ax, ref_std: float, unit: str) -> float:
    """Draw Taylor diagram polar background (RMSE arcs, correlation arcs).
    Lines are tuned for print clarity at DPI=600."""
    if np.isnan(ref_std) or ref_std <= 0:
        ref_std = 5.0
    r_max = ref_std * 1.75

    # RMSE arcs (centred on reference point at (ref_std, 0))
    for frac, lc in [(0.25, "#B0BEC5"), (0.5, "#90A4AE"),
                     (0.75, "#78909C"), (1.0,  "#607D8B")]:
        rr    = ref_std * frac
        theta = np.linspace(0, np.pi / 2, 300)
        xc    = ref_std + rr * np.cos(np.pi - theta)
        yc    = rr * np.sin(theta)
        mask  = (xc ** 2 + yc ** 2 <= r_max ** 2) & (xc >= 0) & (yc >= 0)
        ax.plot(xc[mask], yc[mask], color=lc, lw=0.85, ls="--",
                alpha=0.85, zorder=1)
        idx = np.argmin(np.abs(theta - np.pi / 4))
        if mask[idx]:
            ax.text(xc[idx], yc[idx], f"RMSE\n{rr:.1f}",
                    fontsize=7, color=lc, ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.15",
                              fc="white", ec="none", alpha=0.80))

    # Correlation lines from origin
    for rv, lc in [(0.2, "#CFD8DC"), (0.4, "#B0BEC5"), (0.6, "#90A4AE"),
                   (0.7, "#78909C"), (0.8, "#607D8B"), (0.9, "#546E7A"),
                   (0.95, "#455A64"), (0.99, "#37474F")]:
        tv = np.arccos(rv)
        ax.plot([0, r_max * np.cos(tv)],
                [0, r_max * np.sin(tv)],
                color=lc, lw=0.70, alpha=0.90, zorder=1)
        ax.text(r_max * np.cos(tv) * 1.065,
                r_max * np.sin(tv) * 1.065,
                f"{rv:.2f}", fontsize=7.5, color="#455A64",
                ha="center", va="center", fontweight="bold")

    # Standard deviation arcs
    for frac in [0.25, 0.5, 0.75, 1.0, 1.25, 1.5]:
        ar = ref_std * frac
        if ar > r_max: continue
        t = np.linspace(0, np.pi / 2, 300)
        ax.plot(ar * np.cos(t), ar * np.sin(t),
                color="#CFD8DC", lw=0.80, alpha=0.90, zorder=1)
        ax.text(0, ar, f"{ar:.1f}", fontsize=7.5,
                color="#78909C", ha="right", va="center")

    # Reference point (Observed)
    ax.plot(ref_std, 0, "k*", markersize=16, zorder=10,
            markeredgecolor="#1A1A1A", markeredgewidth=0.8,
            label="Observed (Reference)")
    ax.set_xlim(0, r_max); ax.set_ylim(0, r_max)
    ax.set_xlabel(f"Standard Deviation ({unit})",
                  fontsize=12, fontweight="bold", labelpad=6)
    ax.set_ylabel(f"Standard Deviation ({unit})",
                  fontsize=12, fontweight="bold", labelpad=6)
    ax.text(-0.09, 0.5, "Pearson Correlation (r)  →",
            transform=ax.transAxes, fontsize=9.5, rotation=90,
            va="center", color="#455A64", style="italic", fontweight="bold")
    ax.set_aspect("equal"); ax.grid(False)
    ax.axhline(0, color="#1A1A1A", lw=1.2)
    ax.axvline(0, color="#1A1A1A", lw=1.2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return r_max


def fig5_taylor_diagram(obs_d, raw_dfs: dict, bc_dfs: dict,
                         stns: list, smap: dict,
                         models: list, mc: list,
                         period_obs: str, period_sim: str,
                         out_dir: Path, prefix: str):
    """
    Figure 5: Taylor Diagram — Daily and Monthly only (no Wet Season).
    Layout: 1×2, same figure size/DPI/font as Fig4 QQ-plots.
    Improvements vs original:
      - Markers: larger (s=140), full saturation (alpha=1.0), dark edge outline
      - Arrows: thicker (lw=1.6), higher opacity
      - Station labels: larger (fontsize=10.5), bold
      - Background lines: slightly stronger for print clarity
      - Legend: clean, compact, outside cluster area
      - Station colours: tab20 full saturation (no fading)
    """
    stns_str   = [str(s) for s in stns]
    n_stns     = len(stns_str)
    cmap_stn   = cm.get_cmap("tab20", max(n_stns, 1))
    # Full-saturation station colours (no alpha fading)
    stn_colors = [mcolors.to_hex(cmap_stn(i)) for i in range(n_stns)]

    # ── Pre-compute monthly aggregations ─────────────────────────────────
    obs_m    = to_monthly(obs_d)
    raw_m_dfs = {m: to_monthly(df) for m, df in raw_dfs.items()}
    bc_m_dfs  = {m: to_monthly(df) for m, df in bc_dfs.items()}

    # Only Daily and Monthly
    scales = [
        ("Daily",   obs_d,  raw_dfs,   bc_dfs,   "mm day⁻¹",   "(a)"),
        ("Monthly", obs_m,  raw_m_dfs, bc_m_dfs, "mm month⁻¹", "(b)"),
    ]

    # ── Figure: same size as Fig4 (16×8) ─────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    fig.subplots_adjust(left=0.05, right=0.97,
                        top=0.87, bottom=0.10, wspace=0.26)

    for ai, (scale, o_df, r_dict, b_dict, unit, panel) in enumerate(scales):
        ax = axes[ai]

        if o_df is None:
            ax.text(0.5, 0.5, f"No {scale} data",
                    transform=ax.transAxes, ha="center", fontsize=12)
            continue

        # ── Reference std: mean across stations from Observed ─────────────
        stds = []
        for stn in stns_str:
            if stn in o_df.columns:
                v = o_df[stn].dropna().values
                if len(v) > 5:
                    stds.append(float(np.std(v, ddof=1)))
        ref_std = float(np.mean(stds)) if stds else 5.0

        # ── Draw Taylor background ────────────────────────────────────────
        r_max = _draw_taylor_background(ax, ref_std, unit)

        # ── Ensemble mean DataFrames ──────────────────────────────────────
        ens_raw = ensemble_mean(r_dict)
        ens_bc  = ensemble_mean(b_dict)

        raw_xy = {}   # stn → (x, y) for Raw ensemble point

        for si, stn in enumerate(stns_str):
            col  = stn_colors[si % len(stn_colors)]
            code = smap.get(stn, stn)

            for ens_df, marker, ds_label in [
                (ens_raw, "^", "Raw"),
                (ens_bc,  "o", "BC"),
            ]:
                mr = metrics_from_dfs(o_df, ens_df, stn)
                rv     = mr.get("r",       np.nan)
                sr     = mr.get("sigma_r", np.nan)
                std_o  = mr.get("std_obs", np.nan)
                std_s  = std_o * sr if not (np.isnan(std_o) or np.isnan(sr)) else np.nan

                if np.isnan(std_s) or np.isnan(rv):
                    continue

                theta = np.arccos(np.clip(rv, -1.0, 1.0))
                xv    = std_s * np.cos(theta)
                yv    = std_s * np.sin(theta)

                # ── Large, fully opaque markers with dark edge ─────────────
                ax.scatter(
                    xv, yv,
                    color=col,
                    marker=marker,
                    s=140,                    # larger than original (was 95)
                    zorder=8,
                    edgecolors="#1A1A1A",     # dark edge for contrast on paper
                    linewidth=0.9,
                    alpha=1.0,               # full saturation
                )

                if ds_label == "Raw":
                    raw_xy[stn] = (xv, yv)
                elif ds_label == "BC" and stn in raw_xy:
                    rx, ry = raw_xy[stn]
                    # ── Arrow: Raw → Corrected (thicker, more visible) ────
                    ax.annotate(
                        "", xy=(xv, yv), xytext=(rx, ry),
                        arrowprops=dict(
                            arrowstyle="-|>",
                            color=col,
                            lw=1.6,           # thicker (was 1.0)
                            alpha=0.85,       # higher opacity (was 0.60)
                            mutation_scale=14,
                        ),
                        zorder=7,
                    )
                    # ── Station label: larger, bolder ─────────────────────
                    lx = xv + 0.030 * r_max
                    ly = yv + 0.030 * r_max
                    ax.text(lx, ly, code,
                            fontsize=10.5, color=col,   # was 8.5
                            fontweight="bold",
                            ha="left", va="bottom",
                            zorder=9)

        # ── Legend ────────────────────────────────────────────────────────
        # Type markers
        handles = [
            Line2D([0],[0], marker="*",  color="k",    ls="none",
                   ms=13, label="Observed (Reference)"),
            Line2D([0],[0], marker="^",  color="#444444", ls="none",
                   ms=10, markeredgecolor="#1A1A1A", markeredgewidth=0.8,
                   label="Raw CMIP6 (ensemble mean)"),
            Line2D([0],[0], marker="o",  color="#444444", ls="none",
                   ms=10, markeredgecolor="#1A1A1A", markeredgewidth=0.8,
                   label="Bias-Corrected QDM (ensemble mean)"),
            Line2D([0],[0], color="#444444", lw=1.6, ls="-",
                   label="Arrow: Raw → Corrected"),
        ]
        # Station colour patches
        for si, stn in enumerate(stns_str):
            handles.append(
                mpatches.Patch(
                    facecolor=stn_colors[si % len(stn_colors)],
                    edgecolor="#1A1A1A", linewidth=0.6,
                    alpha=1.0, label=smap[stn]
                )
            )
        ax.legend(
            handles=handles,
            loc="upper right",
            fontsize=8.5,
            frameon=True, edgecolor="#B0BEC5",
            facecolor="white", framealpha=0.95,
            ncol=2, handlelength=1.6,
            borderpad=0.7,
        )

        ax.set_title(
            f"{panel}  Taylor Diagram — {scale} Scale\n"
            f"     Raw CMIP6 (▲) vs Bias-Corrected QDM (●)  |  "
            f"Obs: {period_obs}  |  Sim: {period_sim}",
            loc="left", fontsize=13, fontweight="bold", pad=5
        )

    fig.suptitle(
        "Taylor diagram showing the performance of CMIP6 rainfall simulations "
        "before and after bias correction\n"
        f"Each colour represents one station  |  "
        f"Ref: Taylor (2001) J. Geophys. Res. 106:7183–7192",
        fontsize=13, fontweight="bold"
    )
    savefig(fig, out_dir / f"{prefix}_Fig5_TaylorDiagram")


# ════════════════════════════════════════════════════════════════════════════
#  §8  FIGURE 6 — METRIC IMPROVEMENT BAR CHART
# ════════════════════════════════════════════════════════════════════════════

def fig6_metric_improvement(obs_d, raw_dfs: dict, bc_dfs: dict,
                             stns: list, smap: dict,
                             period_obs: str, out_dir: Path, prefix: str):
    """
    Figure 6: Improvement of Statistical Metrics After Bias Correction.
    4-panel bar chart per station:
      (a) RMSE reduction        (b) Pbias reduction
      (c) r improvement         (d) NSE & KGE improvement
    """
    stns_str  = [str(s) for s in stns]
    codes     = [smap[s] for s in stns_str]
    n_s       = len(stns)
    x         = np.arange(n_s)

    raw_ens = ensemble_mean(raw_dfs)
    bc_ens  = ensemble_mean(bc_dfs)

    # Compute metrics per station for Raw and BC ensemble
    metrics_raw = []
    metrics_bc  = []
    for stn in stns_str:
        metrics_raw.append(metrics_from_dfs(obs_d, raw_ens, stn))
        metrics_bc.append(metrics_from_dfs(obs_d, bc_ens,  stn))

    def _delta(key, raw_list, bc_list, invert=False):
        """BC - Raw (positive = improvement for higher-is-better metrics)."""
        out = []
        for mr, mb in zip(raw_list, bc_list):
            vr = mr.get(key, np.nan)
            vb = mb.get(key, np.nan)
            if np.isnan(vr) or np.isnan(vb):
                out.append(np.nan)
            else:
                out.append(vr - vb if invert else vb - vr)
        return out

    rmse_red  = _delta("RMSE",  metrics_raw, metrics_bc, invert=True)  # lower→better
    pbias_red = [abs(mr.get("Pbias", np.nan)) - abs(mb.get("Pbias", np.nan))
                 for mr, mb in zip(metrics_raw, metrics_bc)]             # |Pbias| lower→better
    r_imp     = _delta("r",     metrics_raw, metrics_bc)
    nse_imp   = _delta("NSE",   metrics_raw, metrics_bc)
    kge_imp   = _delta("KGE",   metrics_raw, metrics_bc)

    def _val(lst, i):
        v = lst[i]
        return 0.0 if (isinstance(v, float) and np.isnan(v)) else v

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.subplots_adjust(hspace=0.48, wspace=0.32,
                        left=0.08, right=0.97, top=0.91, bottom=0.09)

    bar_kw = dict(width=0.65, linewidth=0.9, zorder=3)

    def _bar_panel(ax, values, ylabel, title_tag,
                   pos_col, pos_edge, neg_col, neg_edge, ref_line=None):
        colors = [pos_col if v >= 0 else neg_col for v in values]
        edges  = [pos_edge if v >= 0 else neg_edge for v in values]
        bars = ax.bar(x, values, color=colors, edgecolor=edges,
                      alpha=0.88, **bar_kw)
        ax.axhline(0, color="#546E7A", lw=0.9, ls="--", alpha=0.65)
        if ref_line is not None:
            ax.axhline(ref_line[0], color=ref_line[1], lw=1.0,
                       ls=":", alpha=0.75, label=ref_line[2])
            ax.legend(fontsize=10, loc="lower right")
        for bar, v in zip(bars, values):
            if not np.isnan(v) and abs(v) > 0.001:
                ax.text(bar.get_x() + bar.get_width() / 2,
                        v + (abs(v) * 0.04 + 0.005) * np.sign(v),
                        f"{v:+.3f}", ha="center", va="bottom",
                        fontsize=9.5, fontweight="bold", color="#1A1A1A")
        ax.set_xticks(x)
        ax.set_xticklabels(codes, rotation=0, ha="center", fontsize=11)
        ax.set_xlabel("Station", fontsize=12, fontweight="bold")
        ax.set_ylabel(ylabel, fontsize=12, fontweight="bold")
        ax.set_title(title_tag, loc="left", fontsize=12,
                     fontweight="bold", pad=5)
        ax.tick_params(axis="both", which="major", labelsize=11, width=1.4)
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    _bar_panel(axes[0, 0], rmse_red,
               "RMSE Reduction (mm)\n[positive = improved]",
               "(a)  RMSE Reduction After Bias Correction",
               C["bc_lt"], C["bc_bd"], C["raw_lt"], C["raw_bd"])

    _bar_panel(axes[0, 1], pbias_red,
               "|Pbias| Reduction (%)\n[positive = improved]",
               "(b)  Percent Bias Reduction",
               C["bc_lt"], C["bc_bd"], C["raw_lt"], C["raw_bd"])

    _bar_panel(axes[1, 0], r_imp,
               "Pearson r Improvement\n[positive = improved]",
               "(c)  Correlation Coefficient Improvement",
               C["green"], "#1B5E20", C["raw_lt"], C["raw_bd"],
               ref_line=(0.0, C["grey"], "No change"))

    # Panel (d): NSE & KGE grouped bars
    ax4 = axes[1, 1]
    bw2 = 0.30
    ax4.bar(x - bw2/2, nse_imp, width=bw2,
            color=C["bc_lt"],  edgecolor=C["bc_bd"],
            alpha=0.88, linewidth=0.9, zorder=3, label="NSE improvement")
    ax4.bar(x + bw2/2, kge_imp, width=bw2,
            color=C["ens_lt"], edgecolor=C["ens"],
            alpha=0.88, linewidth=0.9, zorder=3, label="KGE improvement")
    ax4.axhline(0, color="#546E7A", lw=0.9, ls="--", alpha=0.65)
    ax4.set_xticks(x)
    ax4.set_xticklabels(codes, rotation=0, ha="center", fontsize=11)
    ax4.set_xlabel("Station", fontsize=12, fontweight="bold")
    ax4.set_ylabel("Metric Improvement\n[positive = improved]",
                   fontsize=12, fontweight="bold")
    ax4.set_title("(d)  NSE & KGE Improvement",
                  loc="left", fontsize=12, fontweight="bold", pad=5)
    ax4.tick_params(axis="both", which="major", labelsize=11, width=1.4)
    ax4.yaxis.set_minor_locator(ticker.AutoMinorLocator())
    ax4.spines["top"].set_visible(False)
    ax4.spines["right"].set_visible(False)
    ax4.legend(fontsize=10.5, frameon=True, edgecolor="#B0BEC5",
               facecolor="white", framealpha=0.92)

    fig.suptitle(
        "Improvement in statistical performance metrics "
        "after bias correction using Quantile Delta Mapping\n"
        f"Positive values indicate improvement  |  Obs: {period_obs}",
        fontsize=13, fontweight="bold"
    )
    savefig(fig, out_dir / f"{prefix}_Fig6_MetricImprovement")


# ════════════════════════════════════════════════════════════════════════════
#  §9  EXCEL TABLES 1–3
# ════════════════════════════════════════════════════════════════════════════

# CMIP6 model metadata (extended with full institution details)
CMIP6_MODEL_INFO = {
    "ACCESS":     ("ACCESS-ESM1-5",   "CSIRO, Australia",
                   "~1.875°×1.25°",   "1981–2014",
                   "Ziehn et al. (2020) J. Adv. Model. Earth Syst. 12:e2019MS001992"),
    "ACCESS-ESM1-5": ("ACCESS-ESM1-5", "CSIRO, Australia",
                   "~1.875°×1.25°",   "1981–2014",
                   "Ziehn et al. (2020) J. Adv. Model. Earth Syst. 12:e2019MS001992"),
    "MIROC6":     ("MIROC6",           "MIROC, Japan",
                   "~1.406°×1.406°",  "1981–2014",
                   "Tatebe et al. (2019) Geosci. Model Dev. 12:2727–2765"),
    "MPI-ESM":    ("MPI-ESM1-2-HR",   "MPI-M, Germany",
                   "~0.938°×0.938°",  "1981–2014",
                   "Müller et al. (2018) J. Adv. Model. Earth Syst. 10:1383–1413"),
    "MPI-ESM1-2-HR": ("MPI-ESM1-2-HR", "MPI-M, Germany",
                   "~0.938°×0.938°",  "1981–2014",
                   "Müller et al. (2018) J. Adv. Model. Earth Syst. 10:1383–1413"),
    "CanESM5":    ("CanESM5",          "CCCma, Canada",
                   "~2.8°×2.8°",      "1981–2014",
                   "Swart et al. (2019) Geosci. Model Dev. 12:4823–4873"),
    "EC-Earth3":  ("EC-Earth3",        "EC-Earth Consortium, Europe",
                   "~0.703°×0.703°",  "1981–2014",
                   "Döscher et al. (2022) Geosci. Model Dev. 15:2973–3020"),
    "FGOALS-g3":  ("FGOALS-g3",        "LASG/IAP, China",
                   "~2.0°×2.0°",      "1981–2014",
                   "Li et al. (2020) J. Adv. Model. Earth Syst. 12:e2019MS002012"),
    "CESM2":      ("CESM2",            "NCAR, USA",
                   "~0.938°×1.25°",   "1981–2014",
                   "Danabasoglu et al. (2020) J. Adv. Model. Earth Syst. 12:e2019MS001916"),
}


def _table1_models(wb, models: list, period_sim: str):
    """Table 1: CMIP6 Models Used in the Study."""
    ws = wb.create_sheet("Table 1 — CMIP6 Models")
    ws.sheet_view.showGridLines = False

    _mxsc(ws, 1, 1, 5,
          "Table 1   CMIP6 Models Used in the Study",
          bold=True, fc="FFFFFF", bg=XC["title"], sz=13, align="left")
    _rh(ws, 1, 24)
    _mxsc(ws, 2, 1, 5,
          f"Bias correction method: Quantile Delta Mapping (QDM)  |  "
          f"Historical period: {period_sim}  |  "
          "Ref: Cannon et al. (2015) J. Climate 28:6938–6959",
          italic=True, fc="FFFFFF", bg=XC["sub"], sz=9, align="left")
    _rh(ws, 2, 14)

    hdrs = ["No.", "Model ID", "Institution / Country",
            "Horizontal Resolution", "Reference"]
    for ci, h in enumerate(hdrs, 1):
        _xsc(ws, 3, ci, h, bold=True, fc="FFFFFF",
             bg=XC["hdr"], sz=10, wrap=True)
    _rh(ws, 3, 34)

    alt = [_xfill("E3F2FD"), _xfill("FFFFFF")]
    for ri, m in enumerate(models, 4):
        info = CMIP6_MODEL_INFO.get(m)
        if info is None:
            row = [ri - 3, m, "—", "—", "—"]
        else:
            row = [ri - 3, info[0], info[1], info[2], info[4]]
        fl = alt[(ri - 4) % 2]
        for ci, v in enumerate(row, 1):
            cell = _xsc(ws, ri, ci, v, sz=10, align="left" if ci >= 2 else "center")
            cell.fill = fl
        _rh(ws, ri, 36)

    # QDM row
    ri_qdm = len(models) + 4
    _mxsc(ws, ri_qdm, 1, 5,
          "Bias Correction: Quantile Delta Mapping (QDM)  —  "
          "Cannon et al. (2015) J. Climate 28:6938–6959",
          bold=True, fc="FFFFFF", bg=XC["sub"], sz=10, align="left")
    _rh(ws, ri_qdm, 20)

    for ci, w in enumerate([5, 22, 30, 20, 60], 1):
        _cw(ws, ci, w)


def _table2_formulas(wb):
    """Table 2: Statistical Metrics Formulas."""
    ws = wb.create_sheet("Table 2 — Metric Formulas")
    ws.sheet_view.showGridLines = False

    _mxsc(ws, 1, 1, 4,
          "Table 2   Statistical Metrics Used for Bias Correction Evaluation",
          bold=True, fc="FFFFFF", bg=XC["title"], sz=13, align="left")
    _rh(ws, 1, 24)
    _mxsc(ws, 2, 1, 4,
          "O = observed  |  S = simulated  |  n = number of observations  |  "
          "overbar = mean  |  σ = standard deviation  |  "
          "Perfect: RMSE=0, MAE=0, MBE=0, Pbias=0, r=1, NSE=1, KGE=1, d=1",
          italic=True, fc="FFFFFF", bg=XC["sub"], sz=9, align="left")
    _rh(ws, 2, 14)

    hdrs = ["Metric", "Full Name", "Formula / Definition", "Reference"]
    for ci, h in enumerate(hdrs, 1):
        _xsc(ws, 3, ci, h, bold=True, fc="FFFFFF",
             bg=XC["hdr"], sz=10, wrap=True)
    _rh(ws, 3, 28)

    metrics = [
        ("RMSE",
         "Root Mean Square Error",
         "RMSE = √[ (1/n) Σ (Sᵢ − Oᵢ)² ]",
         "—"),
        ("MAE",
         "Mean Absolute Error",
         "MAE = (1/n) Σ |Sᵢ − Oᵢ|",
         "—"),
        ("MBE",
         "Mean Bias Error",
         "MBE = (1/n) Σ (Sᵢ − Oᵢ)",
         "—"),
        ("Pbias",
         "Percent Bias",
         "Pbias = 100 × Σ(Sᵢ − Oᵢ) / Σ Oᵢ  (%)",
         "Moriasi et al. (2007)"),
        ("r",
         "Pearson Correlation Coefficient",
         "r = Σ[(Oᵢ−Ō)(Sᵢ−S̄)] / [√Σ(Oᵢ−Ō)² · √Σ(Sᵢ−S̄)²]",
         "—"),
        ("NSE",
         "Nash–Sutcliffe Efficiency",
         "NSE = 1 − Σ(Sᵢ−Oᵢ)² / Σ(Oᵢ−Ō)²    Range: (−∞, 1]",
         "Nash & Sutcliffe (1970)"),
        ("KGE",
         "Kling–Gupta Efficiency",
         "KGE = 1 − √[(r−1)² + (σs/σo−1)² + (S̄/Ō−1)²]    Range: (−∞, 1]",
         "Gupta et al. (2009)"),
        ("d",
         "Index of Agreement (IoA)",
         "d = 1 − Σ(Sᵢ−Oᵢ)² / Σ(|Sᵢ−Ō|+|Oᵢ−Ō|)²    Range: [0, 1]",
         "Willmott (1981)"),
        ("σᵣ",
         "Standard Deviation Ratio",
         "σᵣ = σs / σo  (Taylor Diagram — variability component of KGE)",
         "Taylor (2001)"),
        ("β",
         "Bias Ratio (KGE component)",
         "β = S̄ / Ō  (mean ratio — long-term bias component of KGE)",
         "Gupta et al. (2009)"),
    ]

    alt = [_xfill("E8F5E9"), _xfill("FFFFFF")]
    for ri, (abbr, name, formula, ref) in enumerate(metrics, 4):
        fl = alt[(ri - 4) % 2]
        for ci, v in enumerate([abbr, name, formula, ref], 1):
            cell = _xsc(ws, ri, ci, v, bold=(ci == 1), sz=10,
                        align="left" if ci >= 2 else "center")
            cell.fill = fl
        _rh(ws, ri, 28)

    for ci, w in enumerate([8, 28, 62, 34], 1):
        _cw(ws, ci, w)


def _table3_comparison(wb, obs_d, raw_dfs: dict, bc_dfs: dict,
                        stns: list, smap: dict,
                        models: list, period_obs: str, period_sim: str):
    """Table 3: Comparison of Statistical Metrics — Raw vs Bias-Corrected."""
    ws = wb.create_sheet("Table 3 — Metric Comparison")
    ws.sheet_view.showGridLines = False

    stns_str = [str(s) for s in stns]
    raw_ens  = ensemble_mean(raw_dfs)
    bc_ens   = ensemble_mean(bc_dfs)

    nc = 18
    _mxsc(ws, 1, 1, nc,
          "Table 3   Comparison of Statistical Metrics Before and After "
          "QDM Bias Correction",
          bold=True, fc="FFFFFF", bg=XC["title"], sz=13, align="left")
    _rh(ws, 1, 24)
    _mxsc(ws, 2, 1, nc,
          f"Ensemble mean of {len(models)} CMIP6 models  |  "
          f"Observed: {period_obs}  |  Simulation: {period_sim}  |  "
          "★ = best value per station  |  "
          "Green = improved after QDM  |  Red = degraded",
          italic=True, fc="FFFFFF", bg=XC["sub"], sz=9, align="left")
    _rh(ws, 2, 14)

    MET_KEYS = ["RMSE","MAE","MBE","Pbias","r","NSE","KGE","d"]
    MET_FMT  = {
        "RMSE":  ".3f", "MAE":  ".3f", "MBE":  ".3f",
        "Pbias": ".2f", "r":    ".4f", "NSE":  ".4f",
        "KGE":   ".4f", "d":    ".4f",
    }
    LOWER_BETTER = {"RMSE","MAE","Pbias"}  # absolute value comparison

    # Header rows
    # Row 3: Dataset groups
    for ci, (lbl, col_s, col_e, bg) in enumerate([
        ("Station", 1, 2, XC["hdr"]),
        ("Raw CMIP6 Ensemble", 3, 10, "FFEBEE"),
        ("Bias-Corrected QDM Ensemble", 11, 18, "E3F2FD"),
    ], 0):
        if col_s == col_e:
            _xsc(ws, 3, col_s, lbl, bold=True,
                 fc="FFFFFF" if bg == XC["hdr"] else "1A1A1A",
                 bg=bg, sz=10, wrap=True)
        else:
            _mxsc(ws, 3, col_s, col_e, lbl, bold=True,
                  fc="FFFFFF" if bg == XC["hdr"] else "1A1A1A",
                  bg=bg, sz=10)
    _rh(ws, 3, 22)

    # Row 4: column headers
    hdrs = ["Station ID", "Code"] + MET_KEYS + MET_KEYS
    for ci, h in enumerate(hdrs, 1):
        bg = XC["hdr"] if ci <= 2 else ("FFEBEE" if ci <= 10 else "E3F2FD")
        _xsc(ws, 4, ci, h, bold=True,
             fc="FFFFFF" if ci <= 2 else "1A1A1A",
             bg=bg, sz=10, wrap=True)
    _rh(ws, 4, 28)

    for ri, stn in enumerate(stns_str, 5):
        code = smap.get(stn, stn)
        mr   = metrics_from_dfs(obs_d, raw_ens, stn)
        mb   = metrics_from_dfs(obs_d, bc_ens,  stn)

        bg_base = "FFFFFF" if (ri - 5) % 2 == 0 else "F5F5F5"
        _xsc(ws, ri, 1, stn,  sz=9, align="center", bg=bg_base)
        _xsc(ws, ri, 2, code, sz=9, align="center", bg=bg_base)

        for col_off, m_dict in [(0, mr), (8, mb)]:
            for ci_k, key in enumerate(MET_KEYS, 3):
                val = m_dict.get(key, np.nan)
                ci_abs = ci_k + col_off

                # Determine improvement colour
                if col_off == 8:  # BC column
                    raw_v = mr.get(key, np.nan)
                    bc_v  = mb.get(key, np.nan)
                    if not (np.isnan(raw_v) or np.isnan(bc_v)):
                        if key in LOWER_BETTER:
                            improved = abs(bc_v) < abs(raw_v)
                        else:
                            improved = bc_v > raw_v
                        bg = XC["improve"] if improved else XC["degrade"]
                    else:
                        bg = bg_base
                else:
                    bg = "FFEBEE"

                cell = _xsc(ws, ri, ci_abs,
                            f"{val:{MET_FMT[key]}}" if not np.isnan(val) else "—",
                            sz=9, align="right", bg=bg)
        _rh(ws, ri, 16)

    # Regional summary row
    ri_sum = len(stns_str) + 5
    _xsc(ws, ri_sum, 1, "Regional Mean",
         bold=True, sz=10, bg=XC["sub"], fc="FFFFFF")
    _xsc(ws, ri_sum, 2, "All",
         bold=True, sz=10, bg=XC["sub"], fc="FFFFFF")

    for col_off, ens_df in [(0, raw_ens), (8, bc_ens)]:
        for ci_k, key in enumerate(MET_KEYS, 3):
            vals = []
            for stn in stns_str:
                m_all = metrics_from_dfs(obs_d, ens_df, stn)
                v = m_all.get(key, np.nan)
                if not np.isnan(v):
                    vals.append(v)
            mean_v = float(np.mean(vals)) if vals else np.nan
            ci_abs = ci_k + col_off
            bg = "FFEBEE" if col_off == 0 else "E3F2FD"
            _xsc(ws, ri_sum, ci_abs,
                 f"{mean_v:{MET_FMT[key]}}" if not np.isnan(mean_v) else "—",
                 bold=True, sz=10, bg=bg)
    _rh(ws, ri_sum, 20)

    # Interpretation note
    ri_note = ri_sum + 2
    _mxsc(ws, ri_note, 1, nc,
          "Interpretation: RMSE, MAE, |MBE|, |Pbias| lower = better.  "
          "r, NSE, KGE, d higher = better (max = 1).  "
          "Green = improvement after QDM.  Red = degradation.",
          italic=True, sz=9, bg=XC["note"], align="left")
    _rh(ws, ri_note, 16)

    widths = [12, 6] + [9] * 16
    for ci, w in enumerate(widths, 1):
        _cw(ws, ci, w)


def _table_references(wb):
    """Add References sheet."""
    ws = wb.create_sheet("References")
    ws.sheet_view.showGridLines = False
    _mxsc(ws, 1, 1, 3, "References",
          bold=True, fc="FFFFFF", bg=XC["title"], sz=13, align="left")
    _rh(ws, 1, 24)

    refs = [
        ("Taylor (2001)",
         "Taylor KE. J. Geophys. Res. 2001; 106(D7):7183–7192",
         "Taylor Diagram methodology"),
        ("Gupta et al. (2009)",
         "Gupta HV, Kling H, Yilmaz KK, Martinez GF. "
         "J. Hydrol. 2009; 377:80–91",
         "Kling-Gupta Efficiency (KGE)"),
        ("Nash & Sutcliffe (1970)",
         "Nash JE, Sutcliffe JV. J. Hydrol. 1970; 10:282–290",
         "Nash-Sutcliffe Efficiency (NSE)"),
        ("Willmott (1981)",
         "Willmott CJ. Phys. Geogr. 1981; 2:184–194",
         "Index of Agreement (d)"),
        ("Cannon et al. (2015)",
         "Cannon AJ, Sobie SR, Murdock TQ. "
         "J. Climate 2015; 28:6938–6959",
         "Quantile Delta Mapping (QDM) bias correction"),
        ("Karl et al. (1999)",
         "Karl TR, Nicholls N, Ghazi A. "
         "Int. J. Climatol. 1999; 19:405–420",
         "ETCCDI climate indices"),
        ("Moriasi et al. (2007)",
         "Moriasi DN et al. Trans. ASABE 2007; 50:885–900",
         "Model performance criteria"),
        ("Murphy (1988)",
         "Murphy AH. Mon. Wea. Rev. 1988; 116:2417–2424",
         "Skill Score (SS) definition"),
        ("Ziehn et al. (2020)",
         "Ziehn T et al. J. Adv. Model. Earth Syst. 2020; 12:e2019MS001992",
         "ACCESS-ESM1-5 model description"),
        ("Tatebe et al. (2019)",
         "Tatebe H et al. Geosci. Model Dev. 2019; 12:2727–2765",
         "MIROC6 model description"),
        ("Müller et al. (2018)",
         "Müller WA et al. J. Adv. Model. Earth Syst. 2018; 10:1383–1413",
         "MPI-ESM1-2-HR model description"),
    ]

    hdrs = ["Citation Key", "Full Reference", "Application"]
    for ci, h in enumerate(hdrs, 1):
        _xsc(ws, 2, ci, h, bold=True, fc="FFFFFF", bg=XC["hdr"], sz=10)
    _rh(ws, 2, 22)

    alt = [_xfill("DEEAF1"), _xfill("FFFFFF")]
    for ri, (key, full, appl) in enumerate(refs, 3):
        fl = alt[(ri - 3) % 2]
        for ci, v in enumerate([key, full, appl], 1):
            cell = _xsc(ws, ri, ci, v, bold=(ci == 1), sz=9.5,
                        align="left")
            cell.fill = fl
        _rh(ws, ri, 24)

    for ci, w in enumerate([18, 78, 40], 1):
        _cw(ws, ci, w)


def write_excel_tables(obs_d, raw_dfs: dict, bc_dfs: dict,
                       stns: list, smap: dict,
                       models: list,
                       period_obs: str, period_sim: str,
                       out_dir: Path, prefix: str):
    """Write Tables 1–3 + References to Excel workbook."""
    wb = Workbook()
    wb.remove(wb.active)

    print("  Building Table 1 — CMIP6 Models ...")
    _table1_models(wb, models, period_sim)

    print("  Building Table 2 — Metric Formulas ...")
    _table2_formulas(wb)

    print("  Building Table 3 — Metric Comparison ...")
    _table3_comparison(wb, obs_d, raw_dfs, bc_dfs,
                       stns, smap, models, period_obs, period_sim)

    _table_references(wb)

    out_path = out_dir / f"{prefix}_Tables_BiasCorrection.xlsx"
    wb.save(str(out_path))
    print(f"  ✓  Excel saved → {out_path.name}")
import os
import sys
import re
import math
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats as sps
from scipy.stats import gaussian_kde, wilcoxon  # เพิ่ม Wilcoxon
import seaborn as sns  # เพิ่ม Seaborn สำหรับ Boxplot

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker
import matplotlib.gridspec as gridspec
from matplotlib.lines import Line2D

# [ ส่วนเดิมของคุณ: รันต่อจากนี้จนถึงฟังก์ชัน write_excel_tables ... ]
# หมายเหตุ: เพื่อความกระชับ ผมจะข้ามไปส่วนฟังก์ชันใหม่และการเรียกใช้ใน Main 
# แต่ในไฟล์ที่คุณจะนำไปใช้ ให้คงฟังก์ชันเดิม (Fig 2-6) ไว้ทั้งหมดครับ

# =============================================================================
# § NEW FUNCTION: STATISTICAL SIGNIFICANCE (Table 4 & Figure 7)
# =============================================================================

def run_significance_analysis(obs_d, raw_dfs, bc_dfs, stns, period, out_dir, prefix):
    """
    คำนวณ Wilcoxon Signed-Rank Test เพื่อเปรียบเทียบ Raw vs QDM
    และสร้าง Table 4 (Excel) พร้อม Figure 7 (Boxplot)
    """
    print("\n  Calculating Statistical Significance (Wilcoxon Test)...")
    data_list = []
    metrics_names = ['RMSE', 'MBE', 'NSE', 'KGE', 'r']
    y1, y2 = period

    # 1. รวบรวมข้อมูล Paired Metrics ระหว่าง Raw และ QDM
    for stn in [str(s) for s in stns]:
        # กรองช่วงเวลา Obs
        obs_sub = obs_d[(obs_d.index.year >= y1) & (obs_d.index.year <= y2)]
        obs_stn = obs_sub[stn].values
        
        for model in raw_dfs.keys():
            # --- Daily Metrics ---
            raw_d = raw_dfs[model][(raw_dfs[model].index.year >= y1) & (raw_dfs[model].index.year <= y2)][stn].values
            bc_d = bc_dfs[model][(bc_dfs[model].index.year >= y1) & (bc_dfs[model].index.year <= y2)][stn].values
            
            m_raw = compute_metrics(obs_stn, raw_d)
            m_bc = compute_metrics(obs_stn, bc_d)
            
            for name in metrics_names:
                data_list.append([stn, model, 'Daily', name, m_raw.get(name), m_bc.get(name)])

            # --- Monthly Metrics ---
            obs_m = obs_sub[stn].resample('MS').sum().values
            raw_m = raw_dfs[model][(raw_dfs[model].index.year >= y1) & (raw_dfs[model].index.year <= y2)][stn].resample('MS').sum().values
            bc_m = bc_dfs[model][(bc_dfs[model].index.year >= y1) & (bc_dfs[model].index.year <= y2)][stn].resample('MS').sum().values
            
            m_raw_m = compute_metrics(obs_m, raw_m)
            m_bc_m = compute_metrics(obs_m, bc_m)
            
            for name in metrics_names:
                data_list.append([stn, model, 'Monthly', name, m_raw_m.get(name), m_bc_m.get(name)])

    df_metrics = pd.DataFrame(data_list, columns=['Station', 'Model', 'TimeScale', 'Metric', 'Raw_Value', 'QDM_Value'])
    
    # 2. ทดสอบ Wilcoxon Signed-Rank Test (Non-parametric paired test)
    sig_results = []
    for ts in ['Daily', 'Monthly']:
        for mt in metrics_names:
            sub = df_metrics[(df_metrics['TimeScale'] == ts) & (df_metrics['Metric'] == mt)].dropna()
            if len(sub) < 5: continue
            
            try:
                # One-tailed Test: QDM ดีกว่า Raw จริงหรือไม่?
                if mt in ['RMSE', 'MBE']:
                    # H1: Error ลดลง (|QDM| < |Raw|)
                    stat, p = wilcoxon(np.abs(sub['QDM_Value']), np.abs(sub['Raw_Value']), alternative='less')
                else:
                    # H1: Efficiency เพิ่มขึ้น (QDM > Raw)
                    stat, p = wilcoxon(sub['QDM_Value'], sub['Raw_Value'], alternative='greater')
            except:
                stat, p = 0, 1.0

            stars = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
            sig_results.append([ts, mt, len(sub), p, stars, "Significant" if p < 0.05 else "Not Significant"])

    df_sig = pd.DataFrame(sig_results, columns=['TimeScale', 'Metric', 'N', 'p_value', 'Symbol', 'Result'])
    
    # บันทึก Table 4 (Excel)
    excel_path = out_dir / f"{prefix}_Table4_Wilcoxon_Significance.xlsx"
    with pd.ExcelWriter(excel_path) as writer:
        df_sig.to_excel(writer, index=False, sheet_name='Summary_Wilcoxon')
        df_metrics.to_excel(writer, index=False, sheet_name='Metric_Values')
    print(f"  ✓ Saved Table 4: {excel_path.name}")

    # 3. วาด Figure 7: Boxplot เปรียบเทียบประสิทธิภาพพร้อมสัญลักษณ์นัยสำคัญ
    plt.rcParams.update({'font.size': 12})
    target_plots = ['RMSE', 'NSE', 'KGE', 'r']
    
    for ts in ['Daily', 'Monthly']:
        fig, axes = plt.subplots(1, 4, figsize=(18, 5.5))
        for i, mt in enumerate(target_plots):
            ax = axes[i]
            d_sub = df_metrics[(df_metrics['TimeScale']==ts) & (df_metrics['Metric']==mt)]
            d_melt = d_sub.melt(value_vars=['Raw_Value', 'QDM_Value'], var_name='Type', value_name='Val')
            d_melt['Type'] = d_melt['Type'].replace({'Raw_Value':'Raw', 'QDM_Value':'QDM'})
            
            # ใช้สีจากตัวแปรสีเดิม (ถ้ามี) หรือกำหนดใหม่ให้ชัดเจน
            sns.boxplot(x='Type', y='Val', data=d_melt, ax=ax, palette=['#ff9999', '#66b3ff'], width=0.6, linewidth=1.5)
            ax.set_title(f"{mt} ({ts})", fontweight='bold', fontsize=14)
            ax.set_xlabel('')
            ax.grid(axis='y', linestyle='--', alpha=0.5)

            # ใส่สัญลักษณ์ดอกจัน (*) จากผลการทดสอบ
            s_row = df_sig[(df_sig['TimeScale']==ts) & (df_sig['Metric']==mt)]
            if not s_row.empty and s_row['Symbol'].values[0] != 'ns':
                y_max = d_melt['Val'].max()
                y_range = y_max - d_melt['Val'].min()
                ax.text(0.5, y_max + (y_range * 0.05), s_row['Symbol'].values[0], 
                        ha='center', fontsize=18, fontweight='bold', color='red')
                ax.set_ylim(top=y_max + (y_range * 0.25))

        plt.tight_layout()
        plt.savefig(out_dir / f"{prefix}_Fig7_Boxplot_Significance_{ts}.png", dpi=300)
        plt.close()
    print(f"  ✓ Saved Figure 7: Boxplots for Daily and Monthly")

# =============================================================================
#  MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    # ... [ ส่วนเดิมของคุณในการโหลดข้อมูล obs_d, raw_dfs, bc_dfs ... ]
    # (สมมติว่ารันผ่าน Figure 2-6 และ Tables 1-3 มาแล้ว)

    # ── Tables 1–3: Excel ────────────────────────────────────────────────
    print("\n  Excel Tables 1–3 ...")
    write_excel_tables(
        obs_d, raw_dfs, bc_dfs,
        stns, smap, all_models,
        period_obs, period_sim, out_dir, prefix
    )

    # ── New: Table 4 & Figure 7 (Wilcoxon Test) ──────────────────────────
    run_significance_analysis(
        obs_d, raw_dfs, bc_dfs, 
        stns, period_obs, out_dir, prefix
    )

    # ── Summary ──────────────────────────────────────────────────────────
    n_png = len(list(out_dir.glob(f"{prefix}_Fig*.png")))
    print(f"\nProcessing finished. Total Figures Generated: {n_png}")
    print("="*80)
# =============================================================================
# §NEW: STATISTICAL SIGNIFICANCE (Table 4 & Figure 7)
# =============================================================================

def run_significance_analysis(obs_d, raw_dfs, bc_dfs, stns, period, out_dir, prefix):
    """คำนวณ Wilcoxon Test และสร้าง Table 4 + Figure 7"""
    print("\n  Statistical Significance Analysis (Wilcoxon Test)...")
    data_list = []
    metrics_names = ['RMSE', 'MBE', 'NSE', 'KGE', 'r']
    y1, y2 = period

    # 1. รวบรวมข้อมูลรายคู่ (Paired Data) ระหว่าง Raw และ QDM
    for stn in [str(s) for s in stns]:
        obs_stn = obs_d[(obs_d.index.year >= y1) & (obs_d.index.year <= y2)][stn].values
        for model in raw_dfs.keys():
            # Daily
            raw_d = raw_dfs[model][(raw_dfs[model].index.year >= y1) & (raw_dfs[model].index.year <= y2)][stn].values
            bc_d = bc_dfs[model][(bc_dfs[model].index.year >= y1) & (bc_dfs[model.index.year <= y2])][stn].values
            
            m_raw = compute_metrics(obs_stn, raw_d)
            m_bc = compute_metrics(obs_stn, bc_d)
            for name in metrics_names:
                data_list.append([stn, model, 'Daily', name, m_raw.get(name), m_bc.get(name)])

            # Monthly
            obs_m = obs_d[(obs_d.index.year >= y1) & (obs_d.index.year <= y2)].resample('MS').sum()[stn].values
            raw_m = raw_dfs[model][(raw_dfs[model].index.year >= y1) & (raw_dfs[model].index.year <= y2)].resample('MS').sum()[stn].values
            bc_m = bc_dfs[model][(bc_dfs[model].index.year >= y1) & (bc_dfs[model].index.year <= y2)].resample('MS').sum()[stn].values
            
            mr_m = compute_metrics(obs_m, raw_m)
            mb_m = compute_metrics(obs_m, bc_m)
            for name in metrics_names:
                data_list.append([stn, model, 'Monthly', name, mr_m.get(name), mb_m.get(name)])

    df_metrics = pd.DataFrame(data_list, columns=['Station', 'Model', 'TimeScale', 'Metric', 'Raw_Value', 'QDM_Value'])
    
    # 2. ทำการทดสอบทางสถิติ (Wilcoxon Signed-Rank Test)
    sig_results = []
    for ts in ['Daily', 'Monthly']:
        for mt in metrics_names:
            sub = df_metrics[(df_metrics['TimeScale'] == ts) & (df_metrics['Metric'] == mt)].dropna()
            if len(sub) < 5: continue
            try:
                if mt in ['RMSE', 'MBE']:
                    # One-tailed: QDM error < Raw error
                    stat, p = wilcoxon(np.abs(sub['QDM_Value']), np.abs(sub['Raw_Value']), alternative='less')
                else:
                    # One-tailed: QDM efficiency > Raw efficiency
                    stat, p = wilcoxon(sub['QDM_Value'], sub['Raw_Value'], alternative='greater')
            except: stat, p = 0, 1.0

            stars = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
            sig_results.append([ts, mt, len(sub), p, stars])

    df_sig = pd.DataFrame(sig_results, columns=['TimeScale', 'Metric', 'N', 'p_value', 'Symbol'])
    
    # 3. บันทึก Table 4 (Excel)
    excel_path = out_dir / f"{prefix}_Table4_Significance.xlsx"
    with pd.ExcelWriter(excel_path) as writer:
        df_sig.to_excel(writer, index=False, sheet_name='Summary_Wilcoxon')
        df_metrics.to_excel(writer, index=False, sheet_name='Detailed_Metrics')
    print(f"  ✓  Table 4: {excel_path.name}")

    # 4. วาด Figure 7: Boxplot
    for ts in ['Daily', 'Monthly']:
        fig, axes = plt.subplots(1, 4, figsize=(18, 6))
        target_plots = ['RMSE', 'NSE', 'KGE', 'r']
        for i, mt in enumerate(target_plots):
            ax = axes[i]
            d_sub = df_metrics[(df_metrics['TimeScale']==ts) & (df_metrics['Metric']==mt)]
            d_melt = d_sub.melt(value_vars=['Raw_Value', 'QDM_Value'], var_name='Type', value_name='Val')
            d_melt['Type'] = d_melt['Type'].replace({'Raw_Value':'Raw', 'QDM_Value':'QDM'})
            
            import seaborn as sns
            sns.boxplot(x='Type', y='Val', data=d_melt, ax=ax, palette=[C['raw_lt'], C['bc_lt']], width=0.6)
            ax.set_title(mt, fontweight='bold')
            
            # ใส่เครื่องหมายนัยสำคัญบนกราฟ
            s_info = df_sig[(df_sig['TimeScale']==ts) & (df_sig['Metric']==mt)]
            if not s_info.empty and s_info['Symbol'].values[0] != 'ns':
                y_max = d_melt['Val'].max()
                ax.text(0.5, y_max, s_info['Symbol'].values[0], ha='center', fontsize=16, color='red', fontweight='bold')

        plt.tight_layout()
        savefig(fig, out_dir / f"{prefix}_Fig7_Significance_{ts}")
# ════════════════════════════════════════════════════════════════════════════
#  §10  MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    SEP = "═" * 70
    print(SEP)
    print("  CMIP6 Bias Correction Evaluation — Publication Figures & Tables")
    print("  Figure 2–6  |  Table 1–3  |  มาตรฐาน Q2–Q4 / Nature / Elsevier")
    print(SEP)

    # ── Determine working folder ─────────────────────────────────────────
    if len(sys.argv) > 1:
        work_dir = sys.argv[1].strip('"').strip("'")
    else:
        try:
            work_dir = str(Path(os.path.abspath(__file__)).parent)
        except NameError:
            work_dir = os.getcwd()

    print(f"  Input folder : {work_dir}")

    # ── Discover files ───────────────────────────────────────────────────
    print("\n  Discovering files ...")
    obs_path, raw_models, bc_models = discover_files(work_dir)

    if obs_path is None:
        sys.exit(
            "  ✗  No Observed file found.\n"
            "     File must contain 'Observed' in the name, e.g.:\n"
            "     Observed_Rain_daily_198101_201412_Prachuap_Khiri_Khan.csv"
        )

    all_models = sorted(set(raw_models.keys()) | set(bc_models.keys()))
    if not all_models:
        sys.exit(
            "  ✗  No CMIP6 model files found.\n"
            "     Expected naming:\n"
            "       Raw : pr_<MODEL>_*.csv\n"
            "       BC  : bc_<MODEL>_*.csv"
        )

    model_colors = MODEL_PALETTE[:len(all_models)]
    print(f"\n  Observed : {Path(obs_path).name}")
    print(f"  Models   : {all_models}")
    print(f"  Raw files: {list(raw_models.keys())}")
    print(f"  BC  files: {list(bc_models.keys())}")
    print("-" * 70)

    # ── Load Observed ────────────────────────────────────────────────────
    print("\n  Loading Observed ...")
    obs_d, stns = load_daily(obs_path, "Observed")
    if obs_d is None:
        sys.exit("  ✗  Failed to load Observed file.")

    stns_str   = [str(s) for s in stns]   # normalised to str
    smap       = short_stn_labels(stns)
    period_obs = period_str(obs_d)
    prefix     = Path(obs_path).stem  # use as output prefix

    # ── Load model data ──────────────────────────────────────────────────
    print("\n  Loading Raw CMIP6 ...")
    raw_dfs = {}
    for m, p in raw_models.items():
        df, _ = load_daily(p, f"Raw/{m}", target_stns=stns_str)
        if df is not None:
            raw_dfs[m] = df

    print("\n  Loading Bias-Corrected (QDM) ...")
    bc_dfs = {}
    for m, p in bc_models.items():
        df, _ = load_daily(p, f"BC/{m}", target_stns=stns_str)
        if df is not None:
            bc_dfs[m] = df

    if not raw_dfs and not bc_dfs:
        sys.exit("  ✗  No model data could be loaded.")

    all_loaded = list(raw_dfs.keys()) + list(bc_dfs.keys())
    period_sim = period_str(
        next(iter(raw_dfs.values())) if raw_dfs
        else next(iter(bc_dfs.values()))
    )
    print(f"\n  {len(stns)} stations  |  {len(all_models)} models  |  "
          f"Obs: {period_obs}  |  Sim: {period_sim}")
    print("-" * 70)

    # ── Output directory (same as input) ────────────────────────────────
    out_dir = Path(work_dir)

    # ── Figure 2: Annual Time Series ────────────────────────────────────
    print("\n  Fig 2: Annual Rainfall Time Series ...")
    fig2_annual_timeseries(
        obs_d, raw_dfs, bc_dfs,
        stns, smap, all_models, model_colors,
        period_obs, out_dir, prefix
    )

    # ── Figure 3: Probability Distribution ──────────────────────────────
    print("  Fig 3: Probability Distribution ...")
    fig3_probability_distribution(
        obs_d, raw_dfs, bc_dfs,
        stns, period_obs, out_dir, prefix
    )

    # ── Figure 4: Q–Q Plots ──────────────────────────────────────────────
    print("  Fig 4: Q–Q Plots ...")
    fig4_qq_plots(
        obs_d, raw_dfs, bc_dfs,
        stns, period_obs, out_dir, prefix
    )

    # ── Figure 5: Taylor Diagram ─────────────────────────────────────────
    print("  Fig 5: Taylor Diagram ...")
    fig5_taylor_diagram(
        obs_d, raw_dfs, bc_dfs,
        stns, smap, all_models, model_colors,
        period_obs, period_sim, out_dir, prefix
    )

    # ── Figure 6: Metric Improvement ────────────────────────────────────
    print("  Fig 6: Metric Improvement ...")
    fig6_metric_improvement(
        obs_d, raw_dfs, bc_dfs,
        stns, smap, period_obs, out_dir, prefix
    )

    # ── Tables 1–3: Excel ────────────────────────────────────────────────
    print("\n  Excel Tables 1–3 ...")
    write_excel_tables(
        obs_d, raw_dfs, bc_dfs,
        stns, smap, all_models,
        period_obs, period_sim, out_dir, prefix
    )
    run_significance_analysis(
        obs_d, raw_dfs, bc_dfs, 
        stns, (obs_d.index.year.min(), obs_d.index.year.max()), 
        out_dir, prefix
    # ── Summary ──────────────────────────────────────────────────────────
    n_png = len(list(out_dir.glob(f"{prefix}_Fig*.png")))
    print(f"\nProcessing finished. Total Figures: {n_png}")
    print(SEP)
    print(f"  ✓  COMPLETE  |  DPI={DPI}  |  PDF={'yes' if SAVE_PDF else 'no'}")
    print(f"  Figures    : {n_png} PNG" + (" + PDF" if SAVE_PDF else ""))
    print(f"  Excel      : {prefix}_Tables_BiasCorrection.xlsx")
    print(f"  Saved to   : {work_dir}")
    print(SEP)


if __name__ == "__main__":
    main()
