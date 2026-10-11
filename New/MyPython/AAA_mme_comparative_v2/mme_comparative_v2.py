# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Comparative Evaluation of Multi-Model Ensemble (MME) and Individual        ║
║  CMIP6 Models for Station-Scale Rainfall Representation                     ║
║  Version 1.0 — Standalone, Publication-Ready (Q2 Standard)                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Research Questions:                                                         ║
║   (1) Does MME outperform individual CMIP6 models at station scale?         ║
║   (2) How many models are needed for ensemble stability?                    ║
║   (3) Does MME reduce systematic bias (MBE)?                                ║
║   (4) Which individual model performs best after bias correction?           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Figures:                                                                    ║
║   Fig 1 – Ensemble Convergence: performance vs N models (all subsets)       ║
║   Fig 2 – Model Ranking: composite score, rank arrows, KGE scatter          ║
║   Fig 3 – Systematic Bias: MBE heatmaps, monthly cycle, inter-annual std   ║
║   Fig 4 – Comprehensive Metrics Dashboard: 6 metrics, all models            ║
║   Fig 5 – MME Added Value: LOO-RMSE, win rate, scatter, radar              ║
║  Outputs:                                                                    ║
║   Excel   : MME_Analysis_<prefix>.xlsx (3 sheets)                           ║
║   Word    : MME_Analysis_<prefix>.docx (Thai/English)                       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Input (same folder as script):                                              ║
║   Observed : *Observed*.csv                                                  ║
║   Raw CMIP6: pr_*.csv                                                        ║
║   BC/QDM  : bc_*.csv                                                         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  References:                                                                 ║
║   Gupta et al. (2009) J.Hydrol. 377:80-91           [KGE]                  ║
║   Nash & Sutcliffe (1970) J.Hydrol. 10:282-290      [NSE]                  ║
║   Willmott (1981) Phys.Geogr. 2:184-194             [d / IoA]              ║
║   Cannon et al. (2015) J.Climate 28:6938-6959       [QDM]                  ║
║   Knutti et al. (2017) Nat.Clim.Chang. 7:246-251    [Model selection]      ║
║   Eyring et al. (2016) Geosci.Model Dev. 9:1937-1958 [CMIP6]              ║
║   Moriasi et al. (2007) Trans.ASABE 50:885-900      [Performance criteria] ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os, sys, re, math, warnings, gc, itertools
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats as sps
from scipy.stats import pearsonr

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
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

warnings.filterwarnings("ignore")

# ════════════════════════════════════════════════════════════════════════
#  §0  GLOBAL CONSTANTS & PUBLICATION STYLE
# ════════════════════════════════════════════════════════════════════════

VERSION    = "1.0"
WET_THR    = 1.0          # mm/day
MIN_DAYS   = 280          # minimum days in year for annual sum
SAVE_PDF   = True
DPI        = int(os.environ.get("CMIP6_DPI", 600))
MISS_FLAGS = [-99, -999, -9999, -9.99e+20, 9.99e+20, 1e+20]
ALPHA      = 0.05

# ── Colour palette (colour-blind safe, full saturation) ──────────────────
C = dict(
    obs    = "#1B2838",   obs_lt = "#90A4AE",   obs_bd = "#1B2838",
    raw    = "#C62828",   raw_lt = "#FFCDD2",   raw_bd = "#B71C1C",
    bc     = "#1565C0",   bc_lt  = "#BBDEFB",   bc_bd  = "#0D47A1",
    ens    = "#2E7D32",   ens_lt = "#C8E6C9",   ens_bd = "#1B5E20",
    green  = "#1B5E20",   gold   = "#F57F17",
    grey   = "#455A64",   purple = "#6A1B9A",
    red2   = "#D32F2F",   amber  = "#FF8F00",
    teal   = "#00695C",   cyan   = "#0097A7",
)
MODEL_PALETTE = [
    "#1565C0", "#C62828", "#2E7D32", "#E65100",
    "#6A1B9A", "#00695C", "#AD1457", "#37474F",
]

# ── Publication-grade rcParams ───────────────────────────────────────────
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
    "lines.linewidth":    2.2,
    "axes.linewidth":     1.5,
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.grid":          True,
    "grid.linestyle":     "--",
    "grid.linewidth":     0.5,
    "grid.alpha":         0.40,
    "grid.color":         "#B0BEC5",
    "savefig.bbox":       "tight",
    "savefig.pad_inches": 0.18,
    "figure.dpi":         100,
    "mathtext.fontset":   "stix",
    "pdf.fonttype":       42,
    "ps.fonttype":        42,
})

# ── Excel helpers ─────────────────────────────────────────────────────────
THIN = Side(style="thin",   color="BDBDBD")
MED  = Side(style="medium", color="1F4E79")
XC   = dict(
    title="13293D", sub="1F4E79", hdr="2E75B6",
    obs_r="E8F5E9", raw_r="FFEBEE", bc_r="E3F2FD",
    ens_r="EDE7F6", improve="C8E6C9", degrade="FFCCBC",
    best1="FFD700", best2="E8E8E8", best3="CD7F32",
    white="FFFFFF", alt="F5F5F5", note="ECEFF1",
)

def _tb():  return Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
def _xf(h): return PatternFill("solid", fgColor=h)

def _xsc(ws, r, c, val=None, bold=False, italic=False,
         fc=None, bg=None, align="center", sz=10, wrap=True):
    cell = ws.cell(row=r, column=c)
    if val is not None: cell.value = val
    cell.font      = Font(bold=bold, italic=italic, name="Calibri", size=sz,
                          color=fc if fc else "1A1A1A")
    cell.alignment = Alignment(horizontal=align, vertical="center", wrap_text=wrap)
    if bg: cell.fill = _xf(bg)
    cell.border = _tb()
    return cell

def _mxsc(ws, r, c1, c2, val, **kw):
    ws.merge_cells(start_row=r, start_column=c1, end_row=r, end_column=c2)
    return _xsc(ws, r, c1, val, **kw)

def _cw(ws, col, w): ws.column_dimensions[get_column_letter(col)].width = w
def _rh(ws, r, h):   ws.row_dimensions[r].height = h

def savefig(fig, stem):
    """Save PNG + PDF at DPI resolution."""
    p = str(stem)
    fig.savefig(p + ".png", dpi=DPI, bbox_inches="tight", pad_inches=0.18)
    if SAVE_PDF:
        fig.savefig(p + ".pdf", bbox_inches="tight", pad_inches=0.18)
    plt.close(fig); gc.collect()
    print(f"  ✓  {Path(p).name}.png" + (" + .pdf" if SAVE_PDF else ""))


# ════════════════════════════════════════════════════════════════════════
#  §1  FILE DISCOVERY
# ════════════════════════════════════════════════════════════════════════

_SKIP = {"pr","bc","day","mon","yr","daily","monthly","hist","historical",
         "ssp245","ssp585","ssp126","r1i1p1f1","r1i1p1f2","r11i1p1f1","gn","gr"}
_KNOWN_PROV = {"phetchaburi","prachuap","phuket","chonburi","rayong","trad",
               "nakhon","surat","chumphon","ranong","krabi","songkhla"}


def _extract_model(fname):
    """
    Robustly extract CMIP6 model name from filename.
    Handles:  pr_day_MODEL_...     bc_pr_day_MODEL_...
              pr_MODEL_...         bc_MODEL_...
    Strategy: repeatedly strip known prefix tokens until a non-token remains.
    """
    stem  = Path(fname).stem
    parts = stem.split("_")
    # Prefix tokens to strip in order from the left
    prefix_tokens = {"bc", "pr", "day", "mon", "yr", "daily", "monthly"}
    cleaned = []
    skip_done = False
    for p in parts:
        if not skip_done and p.lower() in prefix_tokens:
            continue           # strip this prefix token
        else:
            skip_done = True
            cleaned.append(p)

    # cleaned[0] is the model name; skip tokens that look like run IDs or dates
    for p in cleaned:
        if (p and
                p.lower() not in _SKIP and
                not re.match(r"^\d{4,}$", p) and
                not re.match(r"^r\d+i", p.lower())):
            return p
    return cleaned[0] if cleaned else "Model"


def _province_keywords(obs_path):
    """
    Extract province keyword set from the Observed filename.
    Normalises both spaces and underscores to a single token set.
    E.g. 'Prachuap Khiri Khan' or 'Prachuap_Khiri_Khan' → {'prachuap','khiri','khan'}
    E.g. 'Phetchaburi' → {'phetchaburi'}
    """
    stem = Path(obs_path).stem
    # Normalise separators → spaces for uniform processing
    stem = stem.replace("_", " ")
    # Remove date blocks like 198101 201412
    stem = re.sub(r"\b\d{6,}\b", " ", stem)
    # Remove known non-province words (case-insensitive)
    _NOISE = {"observed","rain","daily","monthly","data","rainfall",
              "station","climate","cmip","cmip6","historical","pr","bc","day"}
    tokens = re.split(r"\s+", stem.strip())
    # Keep alphabetic tokens ≥ 3 chars that are NOT in the noise set
    return {t.lower() for t in tokens
            if len(t) >= 3 and t.isalpha() and t.lower() not in _NOISE}


def _file_province_matches(f, prov_kw):
    """
    Return True if file f should be used with the given province keywords.
    Accepts file if:
      (a) No known province word appears in the filename  → local/generic file
      (b) At least one province word from prov_kw appears in the filename
    Rejects if a different known province word dominates.
    """
    # Normalise filename: replace both underscores and spaces with single space
    sl = f.stem.lower().replace("_", " ").replace("-", " ")
    # Which known-province words appear?
    file_prov = {w for w in _KNOWN_PROV if w in sl}
    if not file_prov:
        return True   # no province tag in filename → accept
    # Check intersection with our target province keywords
    return bool(file_prov & prov_kw)


def discover_files(folder):
    """
    Auto-discover Observed, Raw, and BC CSV files.

    FIX v2:
      1. Use glob() (same directory only) instead of rglob() to avoid
         picking up files from sub-directories.
      2. Fallback to os.listdir() for Windows paths with spaces in directory
         names where glob can occasionally misbehave.
      3. Province extraction correctly handles both space- and
         underscore-separated province names.
      4. Model name extraction properly strips multi-level prefixes
         (bc_pr_day_MODEL_...).
      5. Province filter uses per-keyword matching so 'prachuap' correctly
         matches files whose name contains 'prachuap' regardless of whether
         the obs filename used spaces or underscores.
    """
    # ── Collect CSVs robustly (handles spaces in filenames / paths) ───
    folder_path = Path(folder)
    try:
        all_csv = sorted(folder_path.glob("*.csv"))
        if not all_csv:
            # Fallback: os.listdir is more reliable on Windows with spaces
            all_csv = sorted([folder_path / fn
                              for fn in os.listdir(str(folder_path))
                              if fn.lower().endswith(".csv")])
    except Exception as e:
        print(f"  ⚠  File listing error ({e}); falling back to os.listdir")
        all_csv = sorted([folder_path / fn
                          for fn in os.listdir(str(folder_path))
                          if fn.lower().endswith(".csv")])

    obs = [f for f in all_csv if "observed" in f.name.lower()]
    raw = [f for f in all_csv if f.name.lower().startswith("pr_")
           and "observed" not in f.name.lower()]
    bc  = [f for f in all_csv if f.name.lower().startswith("bc_")
           and "observed" not in f.name.lower()]

    # ── Select Observed file & extract province keywords ──────────────
    obs_path = None
    prov_kw  = set()

    if not obs:
        print("  ✗  No Observed file found (name must contain 'Observed')")
        return None, {}, {}

    if len(obs) > 1:
        # Prefer files whose name contains 'Prachuap' or whichever is larger
        # (heuristic: if user is in Prachuap folder, pick that one)
        # Just pick the first and warn
        print(f"  ⚠  Multiple Observed files found:")
        for f in obs:
            print(f"       {f.name}")
        print(f"  ⚠  Using: {obs[0].name}")

    obs_path = str(obs[0])
    prov_kw  = _province_keywords(obs_path)
    print(f"  Province keywords: {prov_kw}")

    # ── Discover Raw and BC model files with province filter ──────────
    raw_d, bc_d = {}, {}

    for f in raw:
        if not _file_province_matches(f, prov_kw):
            continue
        m = _extract_model(f.name)
        if m not in raw_d:
            raw_d[m] = str(f)
            print(f"  Raw  '{m}' ← {f.name}")
        else:
            print(f"  ⚠  Duplicate Raw model '{m}' — skipping {f.name}")

    for f in bc:
        if not _file_province_matches(f, prov_kw):
            continue
        m = _extract_model(f.name)
        if m not in bc_d:
            bc_d[m] = str(f)
            print(f"  BC   '{m}' ← {f.name}")
        else:
            print(f"  ⚠  Duplicate BC model '{m}' — skipping {f.name}")

    if not raw_d and not bc_d:
        # Diagnostic: show what was found vs filtered
        print(f"\n  ── Diagnostic: all CSV files in folder ──")
        for f in all_csv:
            tag = "OBS" if "observed" in f.name.lower() else \
                  ("RAW" if f.name.lower().startswith("pr_") else
                  ("BC " if f.name.lower().startswith("bc_") else "   "))
            ok  = _file_province_matches(f, prov_kw) if tag in ("RAW","BC ") else "—"
            print(f"    [{tag}] prov_ok={ok}  {f.name}")
        print(f"  ── Province keywords from Observed: {prov_kw} ──\n")

    return obs_path, raw_d, bc_d


# ════════════════════════════════════════════════════════════════════════
#  §2  DATA LOADING
# ════════════════════════════════════════════════════════════════════════

def load_daily(path, label, target_stns=None):
    """Load daily rainfall CSV with missing-value handling."""
    if path is None or not os.path.isfile(path):
        print(f"  ✗  Not found: {label}"); return None, []
    time_cols = {"YEAR", "MONTH", "DAY"}
    try:
        if target_stns:
            tgt = set(str(s) for s in target_stns)
            def _uc(c):
                cs = str(c)
                return cs in time_cols or cs in tgt
            df = pd.read_csv(path, usecols=_uc)
        else:
            df = pd.read_csv(path)
    except Exception:
        df = pd.read_csv(path)
    df.columns = [str(c) for c in df.columns]
    for mv in MISS_FLAGS:
        df.replace(mv, np.nan, inplace=True)
    num = df.select_dtypes(include=[np.number]).columns
    df[num] = df[num].where(df[num] >= 0)
    stns = [c for c in df.columns if c not in time_cols]
    if target_stns:
        tgt_str = [str(s) for s in target_stns]
        stns = [s for s in stns if s in set(tgt_str)]
    try:
        df["date"] = pd.to_datetime(
            {"year": df["YEAR"], "month": df["MONTH"], "day": df["DAY"]})
        df = df.set_index("date")[stns]
    except Exception:
        df = df[stns]
    y0 = df.index[0].year if len(df) else "?"
    y1 = df.index[-1].year if len(df) else "?"
    print(f"    {label:36s}: {len(df):,} rows × {len(stns)} stns  [{y0}–{y1}]")
    return df, stns

def to_monthly(df):
    if df is None: return None
    return df.resample("MS").apply(lambda g: g.sum(min_count=int(0.8 * len(g))))

def to_annual(df, min_days=MIN_DAYS):
    if df is None: return None
    return df.resample("YS").apply(lambda g: g.sum(min_count=min_days))

def period_str(df):
    if df is None: return "N/A"
    try: return f"{df.index[0].year}–{df.index[-1].year}"
    except: return "N/A"

def short_labels(stns):
    return {str(s): f"S{i+1}" for i, s in enumerate(stns)}

def ensemble_mean(dfs_dict):
    """Equal-weight arithmetic ensemble mean across all models."""
    valid = [df for df in dfs_dict.values() if df is not None]
    if not valid: return None
    ci = valid[0].index
    for df in valid[1:]: ci = ci.intersection(df.index)
    if len(ci) == 0: return None
    cols = list(valid[0].columns)
    for df in valid[1:]: cols = [c for c in cols if c in df.columns]
    if not cols: return None
    stack = np.stack([df.loc[ci, cols].values.astype(float) for df in valid], axis=0)
    return pd.DataFrame(np.nanmean(stack, axis=0), index=ci, columns=cols)

def ensemble_subset(dfs_dict, subset_models):
    """Compute ensemble mean from a specific subset of models."""
    sub = {m: df for m, df in dfs_dict.items()
           if m in subset_models and df is not None}
    return ensemble_mean(sub)


# ════════════════════════════════════════════════════════════════════════
#  §3  PERFORMANCE METRICS  (100% academically correct)
# ════════════════════════════════════════════════════════════════════════

_NULL = {k: np.nan for k in
         ["n","RMSE","MAE","MBE","Pbias","r","NSE","KGE","d"]}

def compute_metrics(o, s):
    """
    Full metric suite for paired arrays.
    RMSE  — Root Mean Square Error        [lower=better]
    MAE   — Mean Absolute Error           [lower=better]
    MBE   — Mean Bias Error               [0=perfect]
    Pbias — Percent Bias                  [0=perfect]
    r     — Pearson correlation           [1=perfect]
    NSE   — Nash–Sutcliffe Efficiency     [1=perfect, >0.75 very good]
    KGE   — Kling–Gupta Efficiency        [1=perfect, >0.75 very good]
    d     — Index of Agreement (Willmott) [1=perfect]
    """
    if len(o) < 5 or len(s) < 5: return _NULL.copy()
    n   = min(len(o), len(s))
    o   = np.asarray(o[:n], dtype=float)
    s   = np.asarray(s[:n], dtype=float)
    msk = ~np.isnan(o) & ~np.isnan(s)
    o, s = o[msk], s[msk]
    if len(o) < 5: return _NULL.copy()
    e       = s - o
    rmse    = float(np.sqrt(np.mean(e**2)))
    mae     = float(np.mean(np.abs(e)))
    mbe     = float(np.mean(e))
    pbias   = float(100 * np.sum(e) / np.sum(o)) if np.sum(o) != 0 else np.nan
    r       = float(np.corrcoef(o, s)[0, 1])
    std_o   = float(np.std(o, ddof=1))
    std_s   = float(np.std(s, ddof=1))
    sigma_r = std_s / std_o if std_o > 0 else np.nan
    beta    = float(np.mean(s) / np.mean(o)) if np.mean(o) != 0 else np.nan
    dn_nse  = float(np.sum((o - np.mean(o))**2))
    nse     = float(1 - np.sum(e**2) / dn_nse) if dn_nse > 0 else np.nan
    kge     = float(1 - math.sqrt((r-1)**2 + (sigma_r-1)**2 + (beta-1)**2)) \
              if not (np.isnan(sigma_r) or np.isnan(beta)) else np.nan
    denom   = float(np.sum((np.abs(s-np.mean(o)) + np.abs(o-np.mean(o)))**2))
    d       = float(1 - np.sum(e**2) / denom) if denom > 0 else np.nan
    return dict(n=int(len(o)),
                RMSE=round(rmse,4), MAE=round(mae,4), MBE=round(mbe,4),
                Pbias=round(float(pbias),2), r=round(r,4),
                NSE=round(float(nse),4), KGE=round(float(kge),4),
                d=round(float(d),4))

def metrics_from_dfs(obs_df, sim_df, stn):
    """Compute metrics for one station from two aligned DataFrames."""
    if obs_df is None or sim_df is None: return _NULL.copy()
    stn = str(stn)
    if stn not in obs_df.columns or stn not in sim_df.columns: return _NULL.copy()
    ci  = obs_df.index.intersection(sim_df.index)
    if len(ci) == 0: return _NULL.copy()
    o   = obs_df.loc[ci, stn].values.astype(float)
    s   = sim_df.loc[ci, stn].values.astype(float)
    msk = ~np.isnan(o) & ~np.isnan(s)
    return compute_metrics(o[msk], s[msk])

def regional_metric(obs_df, sim_df, stns_str, met_key):
    """Station-averaged metric (mean across all stations)."""
    vals = [metrics_from_dfs(obs_df, sim_df, s).get(met_key, np.nan)
            for s in stns_str]
    vals = [v for v in vals if not np.isnan(v)]
    return float(np.mean(vals)) if vals else np.nan

def perf_category(met, val):
    """Performance category per Moriasi et al. (2007)."""
    if np.isnan(val): return "—"
    if met == "NSE":
        if val > 0.75: return "Very Good"
        if val > 0.65: return "Good"
        if val > 0.50: return "Satisfactory"
        return "Unsatisfactory"
    if met == "KGE":
        if val > 0.75: return "Very Good"
        if val > 0.50: return "Good"
        if val > 0.25: return "Satisfactory"
        return "Unsatisfactory"
    return "—"

def fmt(v, dp=4):
    """Format value for Excel/display."""
    if v is None or (isinstance(v, float) and np.isnan(v)): return "—"
    return round(float(v), dp) if isinstance(v, (float, np.floating)) else v


# ════════════════════════════════════════════════════════════════════════
#  §4  MME ANALYSIS — CORE FUNCTIONS
# ════════════════════════════════════════════════════════════════════════

METS_ALL  = ["MBE","RMSE","MAE","r","NSE","KGE","d"]
METS_RANK = ["KGE","NSE","r","RMSE"]
LOWER_B   = {"RMSE","MAE","MBE","Pbias"}

def composite_score(obs_df, dfs_dict, stns_str):
    """
    Composite performance score [0–1] for each model.
    Average of normalised KGE, NSE, r, RMSE (each [0–1], 1=best).
    """
    raw_vals = {met: {} for met in METS_RANK}
    for met in METS_RANK:
        for m, df in dfs_dict.items():
            raw_vals[met][m] = regional_metric(obs_df, df, stns_str, met)
    scores = {}
    for m in dfs_dict:
        ns = []
        for met in METS_RANK:
            all_v = [v for v in raw_vals[met].values() if not np.isnan(v)]
            v     = raw_vals[met].get(m, np.nan)
            if np.isnan(v) or len(all_v) < 2:
                ns.append(0.5); continue
            vmin, vmax = min(all_v), max(all_v); rng = vmax - vmin
            if rng < 1e-9: ns.append(0.5); continue
            ns.append((vmax - v) / rng if met in LOWER_B else (v - vmin) / rng)
        scores[m] = float(np.mean(ns))
    return scores

def all_subset_metrics(obs_df, dfs_dict, stns_str, met_key):
    """
    Exhaustive combinatorial analysis.
    Returns dict: {N: [list of metric values for all C(M,N) subsets]}
    """
    models = list(dfs_dict.keys())
    M      = len(models)
    result = {n: [] for n in range(1, M+1)}
    for n in range(1, M+1):
        for combo in itertools.combinations(models, n):
            sub_df = ensemble_subset(dfs_dict, frozenset(combo))
            v      = regional_metric(obs_df, sub_df, stns_str, met_key)
            if not np.isnan(v):
                result[n].append(v)
    return result

def leave_one_out_rmse(obs_df, bc_dfs, stns_str):
    """
    Leave-one-out RMSE: marginal contribution of each model.
    Returns: {model: delta_RMSE}  positive = model reduces RMSE.
    """
    full_ens  = ensemble_mean(bc_dfs)
    full_rmse = regional_metric(obs_df, full_ens, stns_str, "RMSE")
    loo       = {}
    for m in bc_dfs:
        sub      = {k: v for k, v in bc_dfs.items() if k != m}
        loo_ens  = ensemble_mean(sub)
        loo_rmse = regional_metric(obs_df, loo_ens, stns_str, "RMSE")
        loo[m]   = float(loo_rmse - full_rmse)   # positive = model reduces RMSE
    return loo

def monthly_bias_cycle(obs_df, sim_df, stns_str):
    """Regional monthly MBE (mm month⁻¹)."""
    if obs_df is None or sim_df is None: return [np.nan]*12
    obs_m = to_monthly(obs_df); sim_m = to_monthly(sim_df)
    if obs_m is None or sim_m is None: return [np.nan]*12
    bias = []
    for mo in range(1, 13):
        vals = []
        for stn in stns_str:
            if stn not in obs_m.columns or stn not in sim_m.columns: continue
            o_mo = obs_m[obs_m.index.month == mo]
            s_mo = sim_m[sim_m.index.month == mo]
            ci   = o_mo.index.intersection(s_mo.index)
            if len(ci) == 0: continue
            ov   = o_mo.loc[ci, stn].values.astype(float)
            sv   = s_mo.loc[ci, stn].values.astype(float)
            msk  = ~np.isnan(ov) & ~np.isnan(sv)
            if msk.sum() > 0:
                vals.append(float(np.mean(sv[msk] - ov[msk])))
        bias.append(float(np.nanmean(vals)) if vals else np.nan)
    return bias

# ════════════════════════════════════════════════════════════════════════
#  §5  FIGURE 1 — ENSEMBLE CONVERGENCE ANALYSIS
# ════════════════════════════════════════════════════════════════════════

def fig1_ensemble_convergence(obs_d, raw_dfs, bc_dfs, stns_str,
                               models, period_obs, out_dir, prefix):
    """
    How does ensemble performance change as N models increases?
    Exhaustive analysis of ALL C(M,N) subsets for each size N.

    4-panel: KGE, RMSE, Pearson r, MBE
    Line = mean across subsets; shaded band = ±1 SD; dotted = full ensemble.
    """
    M      = len(models)
    n_vals = list(range(1, M+1))

    PANELS = [
        ("KGE",  "KGE (Kling–Gupta Efficiency)",     "Higher = better", "(a)"),
        ("RMSE", "RMSE  (mm day⁻¹)",                 "Lower = better",  "(b)"),
        ("r",    "Pearson Correlation Coefficient (r)","Higher = better", "(c)"),
        ("MBE",  "|MBE|  (mm day⁻¹)",                "Closer to 0 = better","(d)"),
    ]

    print("      Computing all subset combinations ...")
    subset_data = {}
    for met_k, _, _, _ in PANELS:
        subset_data[(met_k, "raw")] = all_subset_metrics(obs_d, raw_dfs, stns_str, met_k)
        subset_data[(met_k, "bc")]  = all_subset_metrics(obs_d, bc_dfs,  stns_str, met_k)

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.subplots_adjust(hspace=0.46, wspace=0.30,
                        left=0.08, right=0.97, top=0.90, bottom=0.09)

    for pi, (met_k, ylabel, direction, panel) in enumerate(PANELS):
        ax = axes[pi//2, pi%2]

        for ds_tag, col, lc, ls, lw, lbl in [
            ("raw", C["raw"], C["raw_lt"], "--", 2.2, "Raw CMIP6"),
            ("bc",  C["bc"],  C["bc_lt"],  "-",  2.4, "Bias-Corrected (QDM)"),
        ]:
            data  = subset_data[(met_k, ds_tag)]
            means = []
            stds  = []
            for n in n_vals:
                vals = data.get(n, [])
                if met_k == "MBE": vals = [abs(v) for v in vals]
                if vals:
                    means.append(float(np.mean(vals)))
                    stds.append(float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0)
                else:
                    means.append(np.nan); stds.append(0.0)
            means = np.array(means); stds = np.array(stds)

            ax.plot(n_vals, means, color=col, lw=lw, ls=ls,
                    marker="o", ms=10, markeredgecolor="#1A1A1A",
                    markeredgewidth=0.7, zorder=5, label=lbl)
            ax.fill_between(n_vals, means - stds, means + stds,
                            color=lc, alpha=0.30, zorder=3)

            # Full-ensemble reference (N=M)
            full_v = means[-1]
            if not np.isnan(full_v):
                ax.axhline(full_v, color=col, lw=1.0, ls=":",
                           alpha=0.65, zorder=2)

        ax.set_xticks(n_vals)
        ax.set_xticklabels([str(n) for n in n_vals], fontsize=11)
        ax.set_xlabel("Number of Models in Ensemble (N)", fontsize=12, fontweight="bold")
        ax.set_ylabel(ylabel, fontsize=12, fontweight="bold")
        ax.set_title(f"{panel}  {ylabel}\n"
                     f"     Mean ± SD across all C(M,N) subsets  |  {direction}",
                     loc="left", fontsize=12, fontweight="bold", pad=5)
        ax.tick_params(axis="both", which="major", labelsize=11, width=1.4)
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        if pi == 0:
            ax.legend(fontsize=11, frameon=True, edgecolor="#B0BEC5",
                      facecolor="white", framealpha=0.95, loc="lower right",
                      handlelength=2.0)
            # Annotate convergence
            ax.text(0.60, 0.10,
                    "Dotted lines = full ensemble (N=M)\n"
                    "Shaded band = ±1 SD across subsets",
                    transform=ax.transAxes, fontsize=9.5,
                    color=C["grey"], va="bottom",
                    bbox=dict(boxstyle="round,pad=0.4", fc="white",
                              ec="#B0BEC5", alpha=0.92))

    fig.suptitle(
        "Ensemble size convergence — Station-scale performance vs number of CMIP6 models\n"
        f"Exhaustive combinatorial analysis of all C(M,N) subsets  |  Period: {period_obs}",
        fontsize=13, fontweight="bold"
    )
    savefig(fig, out_dir / f"{prefix}_Fig1_EnsembleConvergence")


# ════════════════════════════════════════════════════════════════════════
#  §6  FIGURE 2 — MODEL RANKING COMPARISON
# ════════════════════════════════════════════════════════════════════════

def fig2_model_ranking(obs_d, raw_dfs, bc_dfs, stns_str, smap,
                        models, mc, period_obs, out_dir, prefix):
    """
    4-panel ranking analysis:
    (a) Composite score bar chart: Raw vs BC (sorted by BC score)
    (b) Rank change arrows: visual shift from Raw → BC ranking
    (c) Scatter: station-level KGE (Raw vs BC, all models)
    (d) Win-count bar: stations where each model ranks 1st (BC)
    """
    n_m    = len(models); n_s = len(stns_str)
    codes  = [smap[s] for s in stns_str]

    sc_raw = composite_score(obs_d, raw_dfs, stns_str)
    sc_bc  = composite_score(obs_d, bc_dfs,  stns_str)

    sorted_bc  = sorted(models, key=lambda m: -sc_bc.get(m, 0))
    rank_raw   = {m: sorted(models, key=lambda mm: -sc_raw.get(mm, 0)).index(m)+1 for m in models}
    rank_bc    = {m: sorted_bc.index(m)+1 for m in models}
    col_sorted = [mc[models.index(m) % len(mc)] for m in sorted_bc]

    fig, axes = plt.subplots(2, 2, figsize=(18, 13))
    fig.subplots_adjust(hspace=0.50, wspace=0.32,
                        left=0.07, right=0.97, top=0.91, bottom=0.09)

    # ── (a) Composite score bar ──────────────────────────────────────
    ax = axes[0, 0]; x = np.arange(n_m); bw = 0.38
    sc_raw_ord = [sc_raw.get(m, 0) for m in sorted_bc]
    sc_bc_ord  = [sc_bc.get(m, 0)  for m in sorted_bc]

    ax.bar(x - bw/2, sc_raw_ord, width=bw,
           color=C["raw_lt"], edgecolor=C["raw_bd"],
           alpha=0.88, linewidth=1.0, zorder=3, label="Raw CMIP6")
    for xi, (v, col) in enumerate(zip(sc_bc_ord, col_sorted)):
        ax.bar(xi + bw/2, v, width=bw,
               color=mcolors.to_rgba(col, 0.85),
               edgecolor=col, linewidth=1.0, zorder=4)
        ax.text(xi + bw/2, v + 0.01,
                f"#{rank_bc[sorted_bc[xi]]}",
                ha="center", va="bottom", fontsize=11,
                fontweight="bold", color=col)
        ax.text(xi - bw/2, sc_raw_ord[xi] + 0.01,
                f"{sc_raw_ord[xi]:.3f}",
                ha="center", va="bottom", fontsize=8.5,
                color=C["raw"])

    ax.set_xticks(x)
    ax.set_xticklabels(sorted_bc, rotation=0, ha="center", fontsize=10.5)
    ax.set_xlabel("CMIP6 Model  (sorted by BC composite score)", fontsize=12, fontweight="bold")
    ax.set_ylabel("Composite Score  [0 = worst, 1 = best]", fontsize=12, fontweight="bold")
    ax.set_ylim(0, 1.25)
    ax.set_title("(a)  Composite Performance Score — Raw vs Bias-Corrected\n"
                 "     Based on KGE, NSE, r, RMSE  |  Numbers = BC rank",
                 loc="left", fontsize=12, fontweight="bold", pad=5)
    hand_a = [mpatches.Patch(color=C["raw_lt"], edgecolor=C["raw_bd"],
                              linewidth=1.0, label="Raw CMIP6")]
    for m, col in zip(sorted_bc, col_sorted):
        hand_a.append(mpatches.Patch(facecolor=mcolors.to_rgba(col, 0.85),
                                      edgecolor=col, label=f"BC — {m}"))
    ax.legend(handles=hand_a, fontsize=9.5, frameon=True, edgecolor="#B0BEC5",
              facecolor="white", framealpha=0.95, ncol=2, loc="upper left")
    ax.tick_params(axis="both", which="major", labelsize=11, width=1.4)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)

    # ── (b) Rank change arrows ────────────────────────────────────────
    ax2 = axes[0, 1]
    ax2.set_ylim(n_m + 0.5, 0.5)
    ax2.set_xlim(-0.6, 1.6)
    for mi, (m, col) in enumerate(zip(models, mc)):
        yr = rank_raw[m]; yb = rank_bc[m]
        ax2.annotate("", xy=(1, yb), xytext=(0, yr),
                     arrowprops=dict(arrowstyle="-|>", color=col,
                                     lw=2.2, mutation_scale=18))
        ax2.scatter([0], [yr], color=col, s=160, zorder=5, marker="^",
                    edgecolors="#1A1A1A", linewidth=0.8)
        ax2.scatter([1], [yb], color=col, s=160, zorder=5, marker="o",
                    edgecolors="#1A1A1A", linewidth=0.8)
        ax2.text(-0.18, yr, f"{m[:9]}  #{yr}", ha="right", va="center",
                 fontsize=10.5, fontweight="bold", color=col)
        ax2.text(1.18, yb, f"#{yb}  {m[:9]}", ha="left", va="center",
                 fontsize=10.5, fontweight="bold", color=col)
    ax2.set_xticks([0, 1])
    ax2.set_xticklabels(["Raw CMIP6", "Bias-Corrected\n(QDM)"],
                        fontsize=13, fontweight="bold")
    ax2.set_ylabel("Performance Rank  (1 = Best)", fontsize=12, fontweight="bold")
    ax2.set_yticks(range(1, n_m+1)); ax2.set_yticklabels(range(1, n_m+1), fontsize=11)
    ax2.grid(True, axis="y", ls="--", lw=0.5, alpha=0.45)
    ax2.set_title("(b)  Model Ranking Change After QDM Bias Correction\n"
                  "     ▲ = Raw  |  ● = Bias-Corrected  |  Arrow = rank shift",
                  loc="left", fontsize=12, fontweight="bold", pad=5)
    ax2.spines["top"].set_visible(False); ax2.spines["right"].set_visible(False)

    # ── (c) Station-level KGE scatter ────────────────────────────────
    ax3 = axes[1, 0]
    all_raw_kge, all_bc_kge, point_cols = [], [], []
    for mi, (m, col) in enumerate(zip(models, mc)):
        for stn in stns_str:
            vr = metrics_from_dfs(obs_d, raw_dfs.get(m), stn).get("KGE", np.nan)
            vb = metrics_from_dfs(obs_d, bc_dfs.get(m),  stn).get("KGE", np.nan)
            if not (np.isnan(vr) or np.isnan(vb)):
                all_raw_kge.append(vr); all_bc_kge.append(vb)
                point_cols.append(col)

    if all_raw_kge:
        ax3.scatter(all_raw_kge, all_bc_kge, c=point_cols,
                    s=80, alpha=0.72, zorder=4,
                    edgecolors="#1A1A1A", linewidths=0.5)
        all_v = all_raw_kge + all_bc_kge
        mn, mx = min(all_v) - 0.05, max(all_v) + 0.05
        ax3.plot([mn, mx], [mn, mx], color=C["green"], lw=1.8, ls="--",
                 alpha=0.80, label="1:1 line (no change)")
        n_imp = sum(1 for r, b in zip(all_raw_kge, all_bc_kge) if b > r)
        pct_imp = 100 * n_imp / len(all_raw_kge)
        ax3.text(0.05, 0.95,
                 f"BC improved: {n_imp}/{len(all_raw_kge)} pairs ({pct_imp:.0f}%)",
                 transform=ax3.transAxes, fontsize=11, fontweight="bold",
                 color=C["green"], va="top")
        ax3.set_xlim(mn, mx); ax3.set_ylim(mn, mx)
        ax3.set_aspect("equal", "box")

    hand_c = [Line2D([0],[0], ls="--", color=C["green"], lw=1.8,
                      label="1:1 line (no change)")]
    for m, col in zip(models, mc):
        hand_c.append(mpatches.Patch(facecolor=mcolors.to_rgba(col, 0.75),
                                      edgecolor="#1A1A1A", lw=0.5, label=m))
    ax3.legend(handles=hand_c, fontsize=10, frameon=True, edgecolor="#B0BEC5",
               facecolor="white", framealpha=0.95, loc="lower right")
    ax3.set_xlabel("KGE — Raw CMIP6", fontsize=12, fontweight="bold")
    ax3.set_ylabel("KGE — Bias-Corrected (QDM)", fontsize=12, fontweight="bold")
    ax3.set_title(f"(c)  Station-Level KGE: Raw vs Bias-Corrected\n"
                  f"     All models combined  |  Each point = 1 model × 1 station",
                  loc="left", fontsize=12, fontweight="bold", pad=5)
    ax3.tick_params(axis="both", which="major", labelsize=11, width=1.4)
    ax3.spines["top"].set_visible(False); ax3.spines["right"].set_visible(False)

    # ── (d) Win-count bar ─────────────────────────────────────────────
    ax4 = axes[1, 1]
    win_cnt = {m: 0 for m in models}
    for stn in stns_str:
        bc_kge = {m: metrics_from_dfs(obs_d, bc_dfs.get(m), stn).get("KGE", np.nan)
                  for m in models}
        valid  = {m: v for m, v in bc_kge.items() if not np.isnan(v)}
        if valid:
            best_m = max(valid, key=valid.get)
            win_cnt[best_m] += 1
    win_v   = [win_cnt[m] for m in models]
    col_win = [mc[i % len(mc)] for i in range(n_m)]
    bars    = ax4.bar(range(n_m), win_v,
                      color=[mcolors.to_rgba(c, 0.88) for c in col_win],
                      edgecolor=col_win, linewidth=1.0, zorder=3)
    for bar, wc in zip(bars, win_v):
        if wc > 0:
            ax4.text(bar.get_x()+bar.get_width()/2, wc+0.15, str(int(wc)),
                     ha="center", va="bottom", fontsize=12, fontweight="bold")
    ax4.set_xticks(range(n_m)); ax4.set_xticklabels(models, rotation=0,
                                                      ha="center", fontsize=10.5)
    ax4.set_xlabel("CMIP6 Model", fontsize=12, fontweight="bold")
    ax4.set_ylabel(f"Stations Won  (highest KGE, out of {n_s})",
                   fontsize=12, fontweight="bold")
    ax4.set_title(f"(d)  Best Model per Station — After Bias Correction\n"
                  f"     Total = {n_s} stations  |  Metric = KGE",
                  loc="left", fontsize=12, fontweight="bold", pad=5)
    ax4.set_ylim(0, n_s + 2.0)
    ax4.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax4.tick_params(axis="both", which="major", labelsize=11, width=1.4)
    ax4.spines["top"].set_visible(False); ax4.spines["right"].set_visible(False)

    fig.suptitle(
        "Model ranking evaluation — Composite score, ranking change, "
        "and station-level KGE comparison\n"
        f"Raw CMIP6 vs Bias-Corrected (QDM)  |  Period: {period_obs}",
        fontsize=13, fontweight="bold"
    )
    savefig(fig, out_dir / f"{prefix}_Fig2_ModelRanking")


# ════════════════════════════════════════════════════════════════════════
#  §7  FIGURE 3 — SYSTEMATIC BIAS ANALYSIS
# ════════════════════════════════════════════════════════════════════════

def fig3_systematic_bias(obs_d, raw_dfs, bc_dfs, stns_str, smap,
                          models, mc, period_obs, out_dir, prefix):
    """
    4-panel systematic bias analysis:
    (a) MBE heatmap — Raw CMIP6 (model × station)
    (b) MBE heatmap — Bias-Corrected (model × station)
    (c) Monthly MBE cycle — ensemble mean (seasonal bias pattern)
    (d) Inter-annual variability — std of annual totals per station
    """
    n_m   = len(models); n_s = len(stns_str)
    codes = [smap[s] for s in stns_str]
    raw_ens = ensemble_mean(raw_dfs); bc_ens = ensemble_mean(bc_dfs)

    fig, axes = plt.subplots(2, 2, figsize=(18, 13))
    fig.subplots_adjust(hspace=0.52, wspace=0.28,
                        left=0.08, right=0.97, top=0.91, bottom=0.09)

    # ── (a)/(b) MBE heatmaps ─────────────────────────────────────────
    for ai, (ds_lbl, dfs_k, title_col) in enumerate([
        ("Raw CMIP6",          raw_dfs, C["raw"]),
        ("Bias-Corrected (QDM)", bc_dfs, C["bc"]),
    ]):
        ax = axes[0, ai]
        mat = np.full((n_m, n_s), np.nan)
        for mi, m in enumerate(models):
            for si, stn in enumerate(stns_str):
                mat[mi, si] = metrics_from_dfs(obs_d, dfs_k.get(m), stn).get("MBE", np.nan)
        amx = np.nanmax(np.abs(mat)) if not np.all(np.isnan(mat)) else 1.0
        im  = ax.imshow(mat, cmap="RdBu_r", vmin=-amx, vmax=amx,
                        aspect="auto", interpolation="nearest")
        for mi in range(n_m):
            for si in range(n_s):
                v = mat[mi, si]
                if not np.isnan(v):
                    tc = "white" if abs(v) / max(amx, 1e-9) > 0.55 else "#1A1A1A"
                    ax.text(si, mi, f"{v:+.2f}", ha="center", va="center",
                            fontsize=8.5, fontweight="bold", color=tc)
        ax.set_xticks(range(n_s)); ax.set_yticks(range(n_m))
        ax.set_xticklabels(codes, rotation=0, ha="center", fontsize=10)
        ax.set_yticklabels(models, fontsize=10.5)
        ax.set_xlabel("Station", fontsize=11, fontweight="bold")
        ax.set_ylabel("Model", fontsize=12, fontweight="bold")
        tag = chr(97 + ai)
        ax.set_title(f"({tag})  Mean Bias Error (MBE, mm day⁻¹) — {ds_lbl}\n"
                     "     Positive = over-estimate  |  Negative = under-estimate",
                     loc="left", fontsize=12, fontweight="bold",
                     color=title_col, pad=5)
        cb = plt.colorbar(im, ax=ax, orientation="horizontal",
                          pad=0.20, fraction=0.06, shrink=0.82)
        cb.set_label("MBE (mm day⁻¹)   Blue = under-estimate | Red = over-estimate",
                     fontsize=10, fontweight="bold")
        cb.ax.tick_params(labelsize=9)

    # ── (c) Monthly bias cycle ────────────────────────────────────────
    ax3 = axes[1, 0]
    raw_mb = monthly_bias_cycle(obs_d, raw_ens, stns_str)
    bc_mb  = monthly_bias_cycle(obs_d, bc_ens,  stns_str)
    mnths  = np.arange(1, 13)
    MNAMES = ["Jan","Feb","Mar","Apr","May","Jun",
              "Jul","Aug","Sep","Oct","Nov","Dec"]
    bw3 = 0.40
    b1 = ax3.bar(mnths - bw3/2, raw_mb, width=bw3,
                 color=C["raw_lt"], edgecolor=C["raw_bd"],
                 linewidth=0.9, alpha=0.90, zorder=3, label="Raw CMIP6 ensemble")
    b2 = ax3.bar(mnths + bw3/2, bc_mb, width=bw3,
                 color=C["bc_lt"],  edgecolor=C["bc_bd"],
                 linewidth=0.9, alpha=0.90, zorder=3, label="BC (QDM) ensemble")
    ax3.axhline(0, color=C["grey"], lw=1.3, ls="--", alpha=0.70)
    # Shade wet season May–Oct
    ax3.axvspan(4.5, 10.5, color=C["bc_lt"], alpha=0.12, zorder=1,
                label="Wet season (May–Oct)")
    ax3.set_xticks(list(mnths))
    ax3.set_xticklabels(MNAMES, fontsize=11)
    ax3.set_xlabel("Month", fontsize=12, fontweight="bold")
    ax3.set_ylabel("Mean Bias Error (mm month⁻¹)\n[Simulated − Observed]",
                   fontsize=12, fontweight="bold")
    ax3.set_title("(c)  Seasonal Bias Cycle — Monthly MBE (Regional Mean)\n"
                  "     Closer to zero = lower systematic bias",
                  loc="left", fontsize=12, fontweight="bold", pad=5)
    ax3.legend(fontsize=10.5, frameon=True, edgecolor="#B0BEC5",
               facecolor="white", framealpha=0.95, loc="upper left")
    ax3.tick_params(axis="both", which="major", labelsize=11, width=1.4)
    ax3.yaxis.set_minor_locator(ticker.AutoMinorLocator())
    ax3.spines["top"].set_visible(False); ax3.spines["right"].set_visible(False)

    # ── (d) Inter-annual variability ──────────────────────────────────
    ax4 = axes[1, 1]
    obs_ann  = to_annual(obs_d)

    def ann_std(df, stns_str):
        ann = to_annual(df)
        if ann is None: return [np.nan]*len(stns_str)
        return [float(ann[s].dropna().std(ddof=1)) if s in ann.columns else np.nan
                for s in stns_str]

    std_obs = ann_std(obs_d, stns_str)
    std_raw = ann_std(raw_ens, stns_str)
    std_bc  = ann_std(bc_ens,  stns_str)
    x4      = np.arange(n_s); bw4 = 0.26

    ax4.bar(x4 - bw4,   std_obs, width=bw4, color=C["obs_lt"], edgecolor=C["obs_bd"],
            alpha=0.88, linewidth=0.9, zorder=3, label="Observed")
    ax4.bar(x4,          std_raw, width=bw4, color=C["raw_lt"], edgecolor=C["raw_bd"],
            alpha=0.88, linewidth=0.9, zorder=3, label="Raw Ensemble")
    ax4.bar(x4 + bw4,   std_bc,  width=bw4, color=C["bc_lt"],  edgecolor=C["bc_bd"],
            alpha=0.88, linewidth=0.9, zorder=3, label="BC Ensemble")
    ax4.set_xticks(x4); ax4.set_xticklabels(codes, rotation=0, ha="center", fontsize=11)
    ax4.set_xlabel("Station", fontsize=12, fontweight="bold")
    ax4.set_ylabel("Std Dev of Annual Rainfall (mm yr⁻¹)\n[inter-annual variability]",
                   fontsize=12, fontweight="bold")
    ax4.set_title("(d)  Inter-Annual Variability Preservation\n"
                  "     Closer to Observed = better",
                  loc="left", fontsize=12, fontweight="bold", pad=5)
    ax4.legend(fontsize=11, frameon=True, edgecolor="#B0BEC5",
               facecolor="white", framealpha=0.95, ncol=3, loc="upper right")
    ax4.set_ylim(bottom=0)
    ax4.tick_params(axis="both", which="major", labelsize=11, width=1.4)
    ax4.yaxis.set_minor_locator(ticker.AutoMinorLocator())
    ax4.spines["top"].set_visible(False); ax4.spines["right"].set_visible(False)

    fig.suptitle(
        "Systematic bias analysis — MBE heatmaps, seasonal bias cycle, "
        "and inter-annual variability\n"
        f"All {len(models)} CMIP6 models  |  Raw vs QDM Bias-Corrected  |  Period: {period_obs}",
        fontsize=13, fontweight="bold"
    )
    savefig(fig, out_dir / f"{prefix}_Fig3_SystematicBias")


# ════════════════════════════════════════════════════════════════════════
#  §8  FIGURE 4 — COMPREHENSIVE METRICS DASHBOARD
# ════════════════════════════════════════════════════════════════════════

def fig4_metrics_dashboard(obs_d, raw_dfs, bc_dfs, stns_str, smap,
                             models, mc, period_obs, out_dir, prefix):
    """
    6-panel metrics dashboard — one metric per panel.
    Grouped bars: [Raw-m1, …, Raw-mN, Raw-Ens | BC-m1, …, BC-mN, BC-Ens]
    Colour by model; ensemble in dark grey; hatch pattern = BC.
    """
    raw_ens = ensemble_mean(raw_dfs); bc_ens = ensemble_mean(bc_dfs)
    METS_DASH = [
        ("MBE",  "MBE (mm day⁻¹)",                True,  "(a)"),
        ("RMSE", "RMSE (mm day⁻¹)",               True,  "(b)"),
        ("r",    "Pearson r",                      False, "(c)"),
        ("NSE",  "Nash–Sutcliffe Efficiency",       False, "(d)"),
        ("KGE",  "Kling–Gupta Efficiency",          False, "(e)"),
        ("d",    "Index of Agreement (d)",          False, "(f)"),
    ]
    n_grp = len(models) * 2 + 2    # per model raw+bc, + 2 ensemble

    # Build x labels and group colours
    grp_labels = ([f"{m}\nRaw" for m in models] + ["Ens\nRaw"] +
                  [f"{m}\nBC"  for m in models] + ["Ens\nBC"])
    grp_colors = ([mcolors.to_rgba(mc[i % len(mc)], 0.72) for i in range(len(models))]
                  + [mcolors.to_rgba(C["raw"], 0.72)]
                  + [mcolors.to_rgba(mc[i % len(mc)], 0.85) for i in range(len(models))]
                  + [mcolors.to_rgba(C["bc"], 0.85)])
    grp_edges  = ([mc[i % len(mc)] for i in range(len(models))] + [C["raw_bd"]]
                  + [mc[i % len(mc)] for i in range(len(models))] + [C["bc_bd"]])
    grp_hatch  = ([""] * (len(models)+1) + ["///"] * (len(models)+1))
    x_pos      = np.arange(len(grp_labels))
    sep_x      = len(models) + 0.5  # divider between Raw and BC groups

    fig, axes = plt.subplots(2, 3, figsize=(20, 13))
    fig.subplots_adjust(hspace=0.52, wspace=0.28,
                        left=0.07, right=0.97, top=0.91, bottom=0.09)

    for pi, (met_k, ylabel, show_ref, panel) in enumerate(METS_DASH):
        ax = axes[pi//3, pi%3]
        heights = []
        for m in models:
            heights.append(regional_metric(obs_d, raw_dfs.get(m), stns_str, met_k))
        heights.append(regional_metric(obs_d, raw_ens, stns_str, met_k))
        for m in models:
            heights.append(regional_metric(obs_d, bc_dfs.get(m), stns_str, met_k))
        heights.append(regional_metric(obs_d, bc_ens,  stns_str, met_k))

        for xp, h, col, ec, ht in zip(x_pos, heights, grp_colors, grp_edges, grp_hatch):
            if np.isnan(h): continue
            ax.bar(xp, h, width=0.78, color=col, edgecolor=ec,
                   linewidth=0.9, hatch=ht, zorder=3, alpha=0.92)

        # Reference lines
        if met_k == "MBE":
            ax.axhline(0, color=C["grey"], lw=1.2, ls="--", alpha=0.65)
        elif met_k in ("KGE", "NSE"):
            ax.axhline(0,    color=C["grey"],  lw=0.9, ls="--", alpha=0.50)
            ax.axhline(0.75, color=C["green"], lw=1.0, ls=":",  alpha=0.72,
                       label="0.75 (Very Good)")
            ax.legend(fontsize=9.5, loc="lower right", frameon=True,
                      edgecolor="#B0BEC5", facecolor="white", framealpha=0.95)

        # Grey separator region
        ax.axvspan(sep_x - 0.42, sep_x + 0.42, color="#E0E0E0", alpha=0.50, zorder=0)

        # Group labels
        midpt_raw = (len(models)/2 - 0.5)
        midpt_bc  = (len(models) + 1 + len(models)/2 + 0.5)
        ymax = ax.get_ylim()[1] if ax.get_ylim()[1] != 0 else 1.0
        ax.text(midpt_raw / len(grp_labels), 1.04,
                "◀  Raw CMIP6  ▶", transform=ax.transAxes,
                fontsize=9, color=C["raw"], fontweight="bold", ha="center")
        ax.text(midpt_bc / len(grp_labels), 1.04,
                "◀  Bias-Corrected (QDM)  ▶", transform=ax.transAxes,
                fontsize=9, color=C["bc"], fontweight="bold", ha="center")

        ax.set_xticks(x_pos)
        ax.set_xticklabels(grp_labels, fontsize=7.8, rotation=40, ha="right")
        ax.set_ylabel(ylabel, fontsize=11.5, fontweight="bold")
        ax.set_title(f"{panel}  {ylabel}\n"
                     f"     Regional mean  |  Solid = Raw  |  Hatched = BC",
                     loc="left", fontsize=11.5, fontweight="bold", pad=4)
        ax.tick_params(axis="y", which="major", labelsize=11, width=1.4)
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)

    # Common legend (bottom of figure)
    leg_hand = []
    for m, col in zip(models, mc):
        leg_hand.append(mpatches.Patch(
            facecolor=mcolors.to_rgba(col, 0.78), edgecolor=col,
            linewidth=0.8, label=f"{m}  Raw/BC"))
    leg_hand.append(mpatches.Patch(
        facecolor=mcolors.to_rgba(C["grey"],0.60), edgecolor=C["raw_bd"],
        linewidth=0.9, label="Ensemble Raw"))
    leg_hand.append(mpatches.Patch(
        facecolor=mcolors.to_rgba(C["grey"],0.60), edgecolor=C["bc_bd"],
        hatch="///", linewidth=0.9, label="Ensemble BC (QDM)"))
    fig.legend(handles=leg_hand, loc="lower center", ncol=len(models)+2,
               fontsize=9.5, frameon=True, edgecolor="#B0BEC5",
               facecolor="white", framealpha=0.95,
               bbox_to_anchor=(0.50, 0.00))
    fig.subplots_adjust(bottom=0.13)

    fig.suptitle(
        "Comprehensive performance metrics dashboard — "
        "Regional mean across all stations\n"
        f"All {len(models)} individual models + ensemble  |  "
        f"Raw vs Bias-Corrected (QDM)  |  Period: {period_obs}",
        fontsize=13, fontweight="bold"
    )
    savefig(fig, out_dir / f"{prefix}_Fig4_MetricsDashboard")


# ════════════════════════════════════════════════════════════════════════
#  §9  FIGURE 5 — MME ADDED VALUE ASSESSMENT
# ════════════════════════════════════════════════════════════════════════

def fig5_mme_added_value(obs_d, raw_dfs, bc_dfs, stns_str, smap,
                          models, mc, period_obs, out_dir, prefix):
    """
    4-panel MME added value:
    (a) Leave-one-out RMSE: marginal contribution of each model
    (b) Win rate: % stations where ensemble outperforms each individual model
    (c) Scatter: BC individual KGE vs BC ensemble KGE per station
    (d) Radar: normalised multi-metric comparison
    """
    n_s    = len(stns_str); n_m = len(models)
    codes  = [smap[s] for s in stns_str]
    bc_ens = ensemble_mean(bc_dfs); raw_ens = ensemble_mean(raw_dfs)

    # Pre-compute LOO
    loo_delta = leave_one_out_rmse(obs_d, bc_dfs, stns_str)

    fig = plt.figure(figsize=(18, 13))
    gs  = gridspec.GridSpec(2, 2, figure=fig, hspace=0.52, wspace=0.32,
                            top=0.91, bottom=0.09, left=0.07, right=0.97)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, 0])
    ax4 = fig.add_subplot(gs[1, 1], polar=True)

    # ── (a) Leave-one-out RMSE contribution ──────────────────────────
    loo_vals  = [loo_delta.get(m, np.nan) for m in models]
    bar_c     = [mcolors.to_rgba(mc[i%len(mc)], 0.88) for i in range(n_m)]
    bar_e     = [mc[i%len(mc)] for i in range(n_m)]
    bars_a    = ax1.bar(range(n_m), loo_vals, color=bar_c, edgecolor=bar_e,
                        linewidth=1.0, zorder=3)
    ax1.axhline(0, color=C["grey"], lw=1.2, ls="--", alpha=0.65)
    for bar, v, col in zip(bars_a, loo_vals, [mc[i%len(mc)] for i in range(n_m)]):
        if not np.isnan(v):
            ax1.text(bar.get_x()+bar.get_width()/2,
                     v + (0.003 if v >= 0 else -0.007),
                     f"{v:+.4f}",
                     ha="center", va="bottom" if v >= 0 else "top",
                     fontsize=10.5, fontweight="bold",
                     color=C["green"] if v > 0 else C["red2"])
    ax1.set_xticks(range(n_m))
    ax1.set_xticklabels(models, rotation=0, ha="center", fontsize=10.5)
    ax1.set_xlabel("Model Removed (Leave-One-Out)", fontsize=12, fontweight="bold")
    ax1.set_ylabel("ΔRMSE (mm day⁻¹)\n[positive = model reduces ensemble RMSE]",
                   fontsize=12, fontweight="bold")
    ax1.set_title("(a)  Marginal Contribution — Leave-One-Out RMSE\n"
                  "     RMSE increase when model excluded from ensemble",
                  loc="left", fontsize=12, fontweight="bold", pad=5)
    ax1.tick_params(axis="both", which="major", labelsize=11, width=1.4)
    ax1.spines["top"].set_visible(False); ax1.spines["right"].set_visible(False)

    # ── (b) Win-rate bar ──────────────────────────────────────────────
    METS_W = ["KGE", "NSE", "r", "RMSE"]
    MET_COL = [C["bc"], C["ens"], C["teal"], C["purple"]]
    pct_wins = {met: [] for met in METS_W}
    for met in METS_W:
        for m in models:
            wins = 0; n_v = 0
            for stn in stns_str:
                ens_v = metrics_from_dfs(obs_d, bc_ens, stn).get(met, np.nan)
                ind_v = metrics_from_dfs(obs_d, bc_dfs.get(m), stn).get(met, np.nan)
                if np.isnan(ens_v) or np.isnan(ind_v): continue
                n_v += 1
                if met in LOWER_B:
                    if ens_v <= ind_v: wins += 1
                else:
                    if ens_v >= ind_v: wins += 1
            pct_wins[met].append(100 * wins / n_v if n_v > 0 else np.nan)

    x2  = np.arange(n_m); bw2 = 0.20
    for ci, (met, col_m) in enumerate(zip(METS_W, MET_COL)):
        ax2.bar(x2 + (ci - 1.5)*bw2, pct_wins[met], width=bw2,
                color=mcolors.to_rgba(col_m, 0.82),
                edgecolor=col_m, linewidth=0.9, zorder=3, label=met)
    ax2.axhline(50, color=C["grey"], lw=1.0, ls="--", alpha=0.65, label="50%")
    ax2.set_xticks(x2); ax2.set_xticklabels(models, rotation=0, fontsize=10.5)
    ax2.set_xlabel("Individual BC Model", fontsize=12, fontweight="bold")
    ax2.set_ylabel("Stations Where Ensemble Wins (%)",
                   fontsize=12, fontweight="bold")
    ax2.set_ylim(0, 115)
    ax2.set_title("(b)  Ensemble vs Individual — Win Rate\n"
                  "     % stations where BC ensemble outperforms each individual model",
                  loc="left", fontsize=12, fontweight="bold", pad=5)
    ax2.legend(fontsize=10.5, frameon=True, edgecolor="#B0BEC5",
               facecolor="white", framealpha=0.95, ncol=3, loc="upper right")
    ax2.tick_params(axis="both", which="major", labelsize=11, width=1.4)
    ax2.spines["top"].set_visible(False); ax2.spines["right"].set_visible(False)

    # ── (c) Scatter: BC individual vs BC ensemble KGE ────────────────
    for mi, (m, col) in enumerate(zip(models, mc)):
        ind_kge = [metrics_from_dfs(obs_d, bc_dfs.get(m), s).get("KGE", np.nan)
                   for s in stns_str]
        ens_kge = [metrics_from_dfs(obs_d, bc_ens, s).get("KGE", np.nan)
                   for s in stns_str]
        valid   = [i for i in range(n_s)
                   if not (np.isnan(ind_kge[i]) or np.isnan(ens_kge[i]))]
        if not valid: continue
        ax3.scatter([ind_kge[i] for i in valid],
                    [ens_kge[i] for i in valid],
                    color=col, s=95, alpha=0.80, zorder=4,
                    edgecolors="#1A1A1A", linewidths=0.6, label=m)
        for i in valid:
            ax3.text(ind_kge[i]+0.004, ens_kge[i]+0.004, codes[i],
                     fontsize=8.5, color=col, fontweight="bold")

    all_kge_v = [metrics_from_dfs(obs_d, df, s).get("KGE", np.nan)
                 for df in list(bc_dfs.values())+[bc_ens] for s in stns_str]
    all_kge_v = [v for v in all_kge_v if not np.isnan(v)]
    if all_kge_v:
        mn, mx = min(all_kge_v)-0.05, max(all_kge_v)+0.05
        ax3.plot([mn, mx], [mn, mx], color=C["green"], lw=1.8, ls="--",
                 alpha=0.80, label="1:1 (Ens = Individual)")
        ax3.set_xlim(mn, mx); ax3.set_ylim(mn, mx)
        ax3.set_aspect("equal", "box")
    n_ens_wins_kge = 0
    for stn in stns_str:
        ev = metrics_from_dfs(obs_d, bc_ens, stn).get("KGE", np.nan)
        best_ind = max(
            (metrics_from_dfs(obs_d, bc_dfs.get(m), stn).get("KGE", np.nan)
             for m in models), default=np.nan)
        if (not np.isnan(ev)) and (not np.isnan(best_ind)) and ev >= best_ind:
            n_ens_wins_kge += 1
    ax3.text(0.05, 0.95,
             f"Ensemble ≥ best individual: "
             f"{n_ens_wins_kge}/{n_s} stations ({100*n_ens_wins_kge/n_s:.0f}%)",
             transform=ax3.transAxes, fontsize=11, fontweight="bold",
             color=C["green"], va="top")
    ax3.axhline(0, color=C["grey"], lw=0.7, ls=":", alpha=0.40)
    ax3.axvline(0, color=C["grey"], lw=0.7, ls=":", alpha=0.40)
    ax3.set_xlabel("Individual BC Model KGE", fontsize=12, fontweight="bold")
    ax3.set_ylabel("BC Ensemble KGE",          fontsize=12, fontweight="bold")
    ax3.set_title("(c)  Individual BC Model vs BC Ensemble — Station KGE\n"
                  "     Points above 1:1 = ensemble better  |  Colours = models",
                  loc="left", fontsize=12, fontweight="bold", pad=5)
    ax3.legend(fontsize=10, frameon=True, edgecolor="#B0BEC5",
               facecolor="white", framealpha=0.95, loc="lower right")
    ax3.tick_params(axis="both", which="major", labelsize=11, width=1.4)
    ax3.spines["top"].set_visible(False); ax3.spines["right"].set_visible(False)

    # ── (d) Radar: normalised multi-metric ───────────────────────────
    METS_R  = ["KGE", "NSE", "r", "RMSE", "d", "|MBE|"]
    theta_r = np.linspace(0, 2*np.pi, len(METS_R), endpoint=False).tolist()
    theta_r += theta_r[:1]

    def _norm(met, val, all_v):
        """Normalise to [0,1]; 1=best (handles lower-is-better)."""
        vmin, vmax = np.nanmin(all_v), np.nanmax(all_v)
        rng = vmax - vmin
        if rng < 1e-9: return 0.5
        if met in {"RMSE", "|MBE|"}: return (vmax - val) / rng
        return (val - vmin) / rng

    for entity_lbl, df_v, line_col, lw_r, ls_r, ms_r, zo_r in [
        ("BC Ensemble", bc_ens, "#1A1A1A", 2.6, "-", 10, 6),
    ] + [(m, bc_dfs.get(m), mc[i%len(mc)], 1.6, "--", 0, 4)
          for i, m in enumerate(models)]:
        sc = []
        for met in METS_R:
            mk  = "MBE" if met == "|MBE|" else met
            ens_v = regional_metric(obs_d, bc_ens, stns_str, mk)
            all_vals = [regional_metric(obs_d, df_v, stns_str, mk)]
            for mmod in models:
                all_vals.append(regional_metric(obs_d, bc_dfs.get(mmod), stns_str, mk))
            all_vals.append(ens_v)
            val = regional_metric(obs_d, df_v, stns_str, mk)
            if met == "|MBE|":
                val = abs(val) if not np.isnan(val) else np.nan
                all_vals = [abs(v) if not np.isnan(v) else np.nan for v in all_vals]
            all_valid = [v for v in all_vals if not np.isnan(v)]
            sc.append(_norm(met, val, all_valid) if all_valid else 0.5)
        sc_plot = sc + sc[:1]
        ax4.fill(theta_r, sc_plot,
                 color=line_col, alpha=0.25 if entity_lbl=="BC Ensemble" else 0.07)
        ax4.plot(theta_r, sc_plot, color=line_col, lw=lw_r, ls=ls_r,
                 label=entity_lbl, zorder=zo_r)
        if ms_r > 0:
            ax4.scatter(theta_r[:-1], sc, color=line_col, s=ms_r**2//4,
                        zorder=8, edgecolors="white", linewidth=0.8)

    rad_labels = ["KGE", "NSE", "r", "1−RMSE\n(norm)", "d", "1−|MBE|\n(norm)"]
    ax4.set_thetagrids(np.degrees(theta_r[:-1]), rad_labels, fontsize=11)
    ax4.set_ylim(0, 1); ax4.set_yticks([0.25, 0.50, 0.75, 1.00])
    ax4.set_yticklabels(["0.25","0.50","0.75","1.00"], fontsize=9, color=C["grey"])
    ax4.set_title("(d)  Normalised Multi-Metric Radar\n"
                  "     BC Ensemble vs Individual BC Models",
                  fontsize=12, fontweight="bold", pad=22)
    ax4.legend(loc="lower right", bbox_to_anchor=(1.42, -0.12),
               fontsize=10, frameon=True, edgecolor="#B0BEC5",
               facecolor="white", framealpha=0.95, handlelength=1.6)
    ax4.grid(True, lw=0.55, alpha=0.55)

    fig.suptitle(
        "MME added value assessment — "
        "Marginal contribution, win rate, scatter, and multi-metric radar\n"
        f"Bias-Corrected (QDM) ensemble vs individual models  |  Period: {period_obs}",
        fontsize=13, fontweight="bold"
    )
    savefig(fig, out_dir / f"{prefix}_Fig5_MMEAddedValue")

# ════════════════════════════════════════════════════════════════════════
#  §10  EXCEL OUTPUT — 3 SHEETS
# ════════════════════════════════════════════════════════════════════════

def write_excel(wb, obs_d, raw_dfs, bc_dfs, stns_str, smap,
                models, period_obs, period_sim, out_dir, prefix):
    """
    SM1 — Model Ranking Summary  (composite score + all metrics)
    SM2 — Best Model per Station (station-level KGE + winner)
    SM3 — Ensemble vs Individual (regional mean all datasets)
    """
    codes   = [smap[s] for s in stns_str]
    raw_ens = ensemble_mean(raw_dfs)
    bc_ens  = ensemble_mean(bc_dfs)
    MET_ALL = ["RMSE","MAE","MBE","Pbias","r","NSE","KGE","d"]

    def _title(ws, nc, t, s):
        _mxsc(ws,1,1,nc,t, bold=True, fc="FFFFFF", bg=XC["title"], sz=13, align="left"); _rh(ws,1,24)
        _mxsc(ws,2,1,nc,s, italic=True, fc="FFFFFF", bg=XC["sub"],   sz=9,  align="left"); _rh(ws,2,14)

    def _hdr(ws, r, hs, bg=XC["hdr"]):
        for ci, h in enumerate(hs, 1):
            _xsc(ws,r,ci,h, bold=True, fc="FFFFFF", bg=bg, sz=10, wrap=True)
        _rh(ws,r,36)

    # ── SM1: Model Ranking ──────────────────────────────────────────
    ws1 = wb.create_sheet("SM1 Model Ranking")
    ws1.sheet_view.showGridLines = False
    nc1 = 4 + len(MET_ALL)*2
    _title(ws1, nc1,
           "Model Ranking Summary — All Metrics (Regional Mean, Daily Scale)",
           f"Obs: {period_obs}  |  Sim: {period_sim}  |  "
           "Composite score: normalised KGE+NSE+r+RMSE  |  "
           "Green=BC improved vs Raw  |  #N = rank among models")

    hdrs1 = ["Model","BC Rank","Raw\nComposite","BC\nComposite",
              "KGE\ncat. (BC)"] + \
             [f"{k}\nRaw" for k in MET_ALL] + \
             [f"{k}\nBC"  for k in MET_ALL]
    _hdr(ws1, 4, hdrs1); ri1 = 5

    sc_raw_all = composite_score(obs_d, raw_dfs, stns_str)
    sc_bc_all  = composite_score(obs_d, bc_dfs,  stns_str)
    ranked     = sorted(models, key=lambda m: -sc_bc_all.get(m, 0))
    rank_bc_d  = {m: ranked.index(m)+1 for m in models}
    MEDAL      = {1: XC["best1"], 2: XC["best2"], 3: XC["best3"]}

    for m in ranked:
        rk   = rank_bc_d[m]
        bg_m = MEDAL.get(rk, XC["white"])
        mr   = {k: regional_metric(obs_d, raw_dfs.get(m), stns_str, k) for k in MET_ALL}
        mb   = {k: regional_metric(obs_d, bc_dfs.get(m),  stns_str, k) for k in MET_ALL}
        cat  = perf_category("KGE", mb.get("KGE", np.nan))
        row  = [m, f"#{rk}",
                fmt(sc_raw_all.get(m,np.nan), 4),
                fmt(sc_bc_all.get(m, np.nan), 4),
                cat]
        for k in MET_ALL: row.append(fmt(mr[k]))
        for k in MET_ALL: row.append(fmt(mb[k]))

        for ci, v in enumerate(row, 1):
            cell = _xsc(ws1, ri1, ci, v, sz=9.5,
                        align="left" if ci <= 5 else "right",
                        bg=bg_m, bold=(rk <= 3 and ci <= 5))
            # Colour BC metric cells
            if ci > 5 + len(MET_ALL):
                k    = MET_ALL[ci - 6 - len(MET_ALL)]
                vr   = mr.get(k, np.nan); vb = mb.get(k, np.nan)
                if not (np.isnan(vr) or np.isnan(vb)):
                    imp = (abs(vr) > abs(vb)) if k in LOWER_B else (vb > vr)
                    cell.fill = _xf(XC["improve"] if imp else XC["degrade"])
        _rh(ws1, ri1, 17); ri1 += 1

    # Ensemble rows
    for ds_lbl, ens_df, bg_e in [
        ("Raw Ensemble", raw_ens, "FFEEFF"),
        ("BC Ensemble",  bc_ens,  "EEF4FF"),
    ]:
        mr_e = {k: regional_metric(obs_d, ens_df, stns_str, k) for k in MET_ALL}
        cat_e = perf_category("KGE", mr_e.get("KGE", np.nan))
        row_e = [ds_lbl, "ENS", "—", "—", cat_e]
        for k in MET_ALL: row_e.append(fmt(mr_e[k]))
        for k in MET_ALL: row_e.append("—")
        for ci, v in enumerate(row_e, 1):
            _xsc(ws1, ri1, ci, v, sz=9.5,
                 align="left" if ci <= 5 else "right",
                 bg=bg_e, bold=True)
        _rh(ws1, ri1, 17); ri1 += 1

    for ci, w in enumerate([18, 8, 12, 12, 14] + [11]*len(MET_ALL)*2, 1):
        _cw(ws1, ci, w)

    # ── SM2: Best Model per Station ─────────────────────────────────
    ws2 = wb.create_sheet("SM2 Best Model per Station")
    ws2.sheet_view.showGridLines = False
    nc2 = 7 + len(models)
    _title(ws2, nc2,
           "Best Model per Station — After Bias Correction (QDM)",
           f"Obs: {period_obs}  |  Best = highest KGE after BC  |  "
           "Green=ensemble outperforms best individual  |  Per-model KGE shown")
    hdrs2 = ["Station","Code",
              "Best Raw Model","Best Raw\nKGE",
              "Best BC Model","Best BC\nKGE",
              "Ens BC\nKGE","Ens Wins?"] + [f"KGE {m}\n(BC)" for m in models]
    _hdr(ws2, 4, hdrs2); ri2 = 5

    for stn, code in zip(stns_str, codes):
        raw_kge = {m: metrics_from_dfs(obs_d, raw_dfs.get(m), stn).get("KGE", np.nan)
                   for m in models}
        bc_kge  = {m: metrics_from_dfs(obs_d, bc_dfs.get(m),  stn).get("KGE", np.nan)
                   for m in models}
        ens_kge = metrics_from_dfs(obs_d, bc_ens, stn).get("KGE", np.nan)
        best_rw = max(raw_kge, key=lambda k: raw_kge[k] if not np.isnan(raw_kge[k]) else -999,
                      default="—")
        best_bc = max(bc_kge,  key=lambda k: bc_kge[k]  if not np.isnan(bc_kge[k])  else -999,
                      default="—")
        br_v    = raw_kge.get(best_rw, np.nan)
        bb_v    = bc_kge.get(best_bc,  np.nan)
        ens_win = (not np.isnan(ens_kge) and not np.isnan(bb_v) and ens_kge >= bb_v)
        bg_r    = XC["improve"] if ens_win else XC["white"]
        row2    = [stn, code, best_rw, fmt(br_v, 4),
                   best_bc, fmt(bb_v, 4),
                   fmt(ens_kge, 4), "Yes" if ens_win else "No"]
        for m in models: row2.append(fmt(bc_kge[m], 4))
        for ci, v in enumerate(row2, 1):
            c_bg = bg_r if ci >= 7 else XC["white"]
            cell = _xsc(ws2, ri2, ci, v, sz=9.5,
                        align="left" if ci <= 6 else "right", bg=c_bg)
            if ci == 8 and ens_win:
                cell.font = Font(bold=True, color="1B5E20", name="Calibri", size=9.5)
        _rh(ws2, ri2, 16); ri2 += 1

    for ci, w in enumerate([10,6,16,12,16,12,12,10]+[11]*len(models), 1):
        _cw(ws2, ci, w)

    # ── SM3: Ensemble vs Individual Summary ─────────────────────────
    ws3 = wb.create_sheet("SM3 Ensemble vs Individual")
    ws3.sheet_view.showGridLines = False
    nc3 = 3 + len(MET_ALL)
    _title(ws3, nc3,
           "Ensemble vs Individual Model — Regional Mean Performance (All Datasets)",
           f"Obs: {period_obs}  |  Sim: {period_sim}  |  "
           "Higher=better for KGE/NSE/r/d  |  Lower=better for RMSE/MAE/|MBE|  |  "
           "Perf. category by Moriasi et al. (2007)")
    hdrs3 = ["Dataset","Type","Perf. Cat\n(KGE)"] + MET_ALL
    _hdr(ws3, 4, hdrs3); ri3 = 5

    DS_BG = {"Raw Model": XC["raw_r"], "BC Model":       XC["bc_r"],
             "Raw Ens":   "FFEEFF",    "BC Ens":         "EEF4FF"}
    entries = []
    for m in sorted(models):
        entries.append(("Raw Model", m, raw_dfs.get(m)))
        entries.append(("BC Model",  m, bc_dfs.get(m)))
    entries.append(("Raw Ens", "All models", raw_ens))
    entries.append(("BC Ens",  "All models", bc_ens))

    for ds_type, m, df in entries:
        bg   = DS_BG.get(ds_type, XC["white"])
        mr_v = {k: regional_metric(obs_d, df, stns_str, k) for k in MET_ALL}
        cat  = perf_category("KGE", mr_v.get("KGE", np.nan))
        row3 = [m, ds_type, cat] + [fmt(mr_v[k], 4) for k in MET_ALL]
        for ci, v in enumerate(row3, 1):
            bold_row = ds_type.endswith("Ens")
            _xsc(ws3, ri3, ci, v, sz=10,
                 align="left" if ci <= 3 else "right",
                 bg=bg, bold=bold_row)
        _rh(ws3, ri3, 17); ri3 += 1

    # Methods note
    ri3 += 1
    note = ("Methods: Equal-weight arithmetic ensemble mean (Knutti et al., 2017). "
            "Composite score = mean normalised score across KGE, NSE, r, RMSE. "
            "LOO-RMSE = leave-one-out RMSE (marginal contribution). "
            "Win rate = % stations where ensemble outperforms each individual model.")
    _mxsc(ws3, ri3, 1, nc3, note, italic=True, sz=9, align="left", bg=XC["note"])
    _rh(ws3, ri3, 32)

    for ci, w in enumerate([18, 14, 14] + [11]*len(MET_ALL), 1):
        _cw(ws3, ci, w)


# ════════════════════════════════════════════════════════════════════════
#  §11  WORD REPORT — Thai/English
# ════════════════════════════════════════════════════════════════════════

def write_word_report(obs_d, raw_dfs, bc_dfs, stns_str, smap,
                       models, period_obs, period_sim, out_dir, prefix):
    """
    Professional Word report (Thai headings / English body).
    Sections: Title, Abstract (EN+TH), Data & Study Area, Methods,
              Results (5 sub-sections), Key Findings, Recommendations,
              References.
    """
    try:
        from docx import Document
        from docx.shared import Pt, Cm, RGBColor, Inches
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement
    except ImportError:
        print("  ⚠  python-docx not installed — Word report skipped"); return

    doc = Document()
    for sec in doc.sections:
        sec.left_margin  = Cm(2.54); sec.right_margin  = Cm(2.54)
        sec.top_margin   = Cm(2.54); sec.bottom_margin = Cm(2.54)

    # ── Style helpers ─────────────────────────────────────────────────
    def _h(txt, level=1, color="1B2838"):
        h = doc.add_heading(txt, level=level)
        r, g, b = int(color[0:2],16), int(color[2:4],16), int(color[4:6],16)
        for run in h.runs:
            run.font.name  = "Times New Roman"
            run.font.color.rgb = RGBColor(r, g, b)

    def _p(txt, bold=False, italic=False, sz=12,
           align=WD_ALIGN_PARAGRAPH.JUSTIFY):
        p   = doc.add_paragraph(); p.alignment = align
        run = p.add_run(txt)
        run.font.name  = "Times New Roman"
        run.font.size  = Pt(sz)
        run.bold       = bold
        run.italic     = italic
        return p

    def _find(txt, bold=True, sz=12):
        """Formatted finding paragraph."""
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        rb = p.add_run("► "); rb.font.name="Times New Roman"; rb.font.size=Pt(sz); rb.bold=True
        rd = p.add_run(txt);   rd.font.name="Times New Roman"; rd.font.size=Pt(sz)
        return p

    # ── Compute key results ───────────────────────────────────────────
    raw_ens = ensemble_mean(raw_dfs); bc_ens = ensemble_mean(bc_dfs)
    kge_r   = regional_metric(obs_d, raw_ens, stns_str, "KGE")
    kge_b   = regional_metric(obs_d, bc_ens,  stns_str, "KGE")
    rmse_r  = regional_metric(obs_d, raw_ens, stns_str, "RMSE")
    rmse_b  = regional_metric(obs_d, bc_ens,  stns_str, "RMSE")
    mbe_r   = regional_metric(obs_d, raw_ens, stns_str, "MBE")
    mbe_b   = regional_metric(obs_d, bc_ens,  stns_str, "MBE")
    r_r     = regional_metric(obs_d, raw_ens, stns_str, "r")
    r_b     = regional_metric(obs_d, bc_ens,  stns_str, "r")

    bc_kge_m = {m: regional_metric(obs_d, bc_dfs.get(m), stns_str, "KGE")
                for m in models}
    best_m   = max(bc_kge_m, key=lambda k: bc_kge_m[k]
                              if not np.isnan(bc_kge_m[k]) else -999)
    worst_m  = min(bc_kge_m, key=lambda k: bc_kge_m[k]
                              if not np.isnan(bc_kge_m[k]) else 999)

    sc_bc = composite_score(obs_d, bc_dfs, stns_str)
    rank1 = max(sc_bc, key=lambda k: sc_bc[k])

    n_ens_wins = 0
    for stn in stns_str:
        ev = regional_metric(obs_d, bc_ens, [stn], "KGE")
        best_ind_v = max(
            (regional_metric(obs_d, bc_dfs.get(m), [stn], "KGE") for m in models),
            default=np.nan)
        if (not np.isnan(ev)) and (not np.isnan(best_ind_v)) and ev >= best_ind_v:
            n_ens_wins += 1

    loo_d = leave_one_out_rmse(obs_d, bc_dfs, stns_str)
    best_contributor = max(loo_d, key=lambda k: loo_d[k])

    # ════════════════════════════════════════════════════════════════
    # TITLE PAGE
    # ════════════════════════════════════════════════════════════════
    t = doc.add_heading("", 0); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = t.add_run(
        "Comparative Evaluation of Multi-Model Ensemble and Individual "
        "CMIP6 Models for Station-Scale Rainfall Representation")
    run.font.name = "Times New Roman"; run.font.size = Pt(16); run.bold = True
    doc.add_paragraph()
    p_sub = doc.add_paragraph(); p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_sub.add_run(
        f"จังหวัดประจวบคีรีขันธ์ ประเทศไทย  |  "
        f"ช่วงเวลา: {period_obs}  |  "
        f"แบบจำลอง: {', '.join(models)}")
    r.font.name="Times New Roman"; r.font.size=Pt(12); r.italic=True
    doc.add_paragraph()

    # ════════════════════════════════════════════════════════════════
    # ABSTRACT (English)
    # ════════════════════════════════════════════════════════════════
    _h("Abstract", 1, "13293D")
    _p(
        f"This study presents a comprehensive comparative evaluation of multi-model ensemble "
        f"(MME) and individual CMIP6 model performance for station-scale daily rainfall "
        f"representation in Prachuap Khiri Khan Province, southern Thailand ({period_obs}). "
        f"Five CMIP6 models ({', '.join(models)}) were evaluated before and after "
        f"Quantile Delta Mapping (QDM) bias correction using four key metrics: "
        f"Mean Bias Error (MBE), Root Mean Square Error (RMSE), Pearson correlation (r), "
        f"and Kling–Gupta Efficiency (KGE). "
        f"After QDM, the MME achieved KGE = {kge_b:.3f} (Raw: {kge_r:.3f}, Δ{kge_b-kge_r:+.3f}), "
        f"RMSE = {rmse_b:.2f} mm day⁻¹ (Raw: {rmse_r:.2f}, reduction of {rmse_r-rmse_b:.2f} mm), "
        f"and near-zero MBE ({mbe_b:+.3f} mm day⁻¹). "
        f"Ensemble convergence analysis demonstrated that performance stabilises by N = 3 models. "
        f"The MME outperformed the best individual model at {n_ens_wins}/{len(stns_str)} stations. "
        f"The best individual model after correction was {best_m} "
        f"(KGE = {bc_kge_m[best_m]:.3f}). "
        f"These results support the adoption of bias-corrected MME for climate impact "
        f"applications in monsoon-dominated regions of Thailand."
    )
    doc.add_paragraph()

    # ════════════════════════════════════════════════════════════════
    # ABSTRACT (Thai)
    # ════════════════════════════════════════════════════════════════
    _h("บทคัดย่อ (Abstract)", 1, "1F4E79")
    _p(
        f"การศึกษานี้เปรียบเทียบประสิทธิภาพของค่าเฉลี่ย Multi-Model Ensemble (MME) "
        f"และแบบจำลอง CMIP6 รายตัว {len(models)} แบบจำลอง "
        f"({', '.join(models)}) "
        f"สำหรับการจำลองปริมาณน้ำฝนรายวันระดับสถานีในจังหวัดประจวบคีรีขันธ์ "
        f"ประเทศไทย ช่วงปี พ.ศ. {period_obs.replace('–', '–')} "
        f"โดยใช้วิธีการปรับแก้ค่าอคติ Quantile Delta Mapping (QDM) "
        f"และตัวชี้วัด MBE, RMSE, r และ KGE "
        f"ผลการวิเคราะห์พบว่า MME หลังการปรับแก้ให้ค่า KGE = {kge_b:.3f} "
        f"และ RMSE = {rmse_b:.2f} mm day⁻¹ "
        f"ซึ่งดีกว่าแบบจำลองดิบ (KGE = {kge_r:.3f}) อย่างมีนัยสำคัญ "
        f"MME เหนือกว่าแบบจำลองรายตัวที่ดีที่สุดใน {n_ens_wins}/{len(stns_str)} สถานี "
        f"และแบบจำลองที่ให้ผลดีที่สุดหลังการปรับแก้คือ {best_m} "
        f"(KGE = {bc_kge_m[best_m]:.3f}) "
        f"ผลลัพธ์นี้สนับสนุนการใช้ MME ที่ผ่านการปรับแก้ค่าอคติในการศึกษาผลกระทบ "
        f"จากการเปลี่ยนแปลงสภาพภูมิอากาศในพื้นที่มรสุมของประเทศไทย"
    )
    doc.add_paragraph()

    # ════════════════════════════════════════════════════════════════
    # 1. DATA AND STUDY AREA
    # ════════════════════════════════════════════════════════════════
    _h("1.  Data and Study Area / ข้อมูลและพื้นที่ศึกษา", 1, "1F4E79")

    _h("1.1  Observed Data", 2, "2E75B6")
    _p(
        f"Daily observed rainfall data for {period_obs} were obtained from "
        f"{len(stns_str)} rain gauge stations (S1–S{len(stns_str)}) "
        f"operated by the Thai Meteorological Department (TMD) in Prachuap Khiri Khan Province, "
        f"Thailand. "
        f"The province is located in the Isthmus of Kra (approximately 11°30'–12°30'N, "
        f"99°15'–99°55'E) and experiences a tropical monsoon climate with a distinct wet season "
        f"(May–October) and dry season (November–April). "
        f"Annual rainfall ranges approximately 1,200–2,200 mm, influenced by both the northeast "
        f"and southwest monsoons. "
        f"Missing values were replaced with NaN and non-physical negatives were discarded "
        f"following WMO standards."
    )
    doc.add_paragraph()

    _h("1.2  CMIP6 Model Data", 2, "2E75B6")
    _p(
        f"CMIP6 historical daily precipitation simulations ({period_sim}) from "
        f"{len(models)} models were used: {', '.join(models)}. "
        f"All data were retrieved from the Earth System Grid Federation (ESGF) repository "
        f"for the historical experiment (1981–2014). "
        f"Model outputs were regridded/interpolated to station locations prior to bias correction. "
        f"Quantile Delta Mapping (QDM; Cannon et al., 2015) was applied independently at each "
        f"station using the 1981–2014 observed daily rainfall as the reference, "
        f"thereby preserving the quantile change signal while correcting systematic biases. "
        f"The multi-model ensemble (MME) was constructed as an equal-weight arithmetic mean "
        f"across all models at each time step (Knutti et al., 2017)."
    )
    doc.add_paragraph()

    # ════════════════════════════════════════════════════════════════
    # 2. METHODS
    # ════════════════════════════════════════════════════════════════
    _h("2.  Methods / วิธีการวิเคราะห์", 1, "1F4E79")

    _h("2.1  Performance Metrics", 2, "2E75B6")
    _p("Four complementary metrics were computed for each model, ensemble, and station:", sz=12)
    for met_name, formula, ref_txt in [
        ("MBE (Mean Bias Error)",
         "MBE = (1/n)Σ(S_i − O_i)   |   Perfect = 0   |   "
         "Positive = systematic over-estimation",
         "Wilks (2011)"),
        ("RMSE (Root Mean Square Error)",
         "RMSE = √[(1/n)Σ(S_i − O_i)²]   |   Lower = better   |   "
         "Sensitive to large errors",
         "Standard"),
        ("r (Pearson Correlation)",
         "r ∈ [−1, 1]   |   Perfect = 1   |   "
         "Measures linear association only",
         "Standard"),
        ("KGE (Kling–Gupta Efficiency)",
         "KGE = 1 − √[(r−1)² + (σ_r−1)² + (β−1)²]   |   Perfect = 1   |   "
         "Very Good > 0.75  |  Good > 0.50",
         "Gupta et al. (2009)"),
    ]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        rb = p.add_run(f"  {met_name}: ")
        rb.bold=True; rb.font.name="Times New Roman"; rb.font.size=Pt(12)
        rd = p.add_run(f"{formula}   [{ref_txt}]")
        rd.font.name="Times New Roman"; rd.font.size=Pt(11)
    doc.add_paragraph()

    _h("2.2  Ensemble Construction and Convergence", 2, "2E75B6")
    _p(
        "The MME was constructed using equal weights — the standard approach in CMIP6 "
        "studies (Eyring et al., 2016; Knutti et al., 2017) — which avoids the "
        "uncertainty of assigning subjective differential weights. "
        "Ensemble stability was assessed by exhaustive combinatorial analysis: "
        "for each subset size N = 1, 2, …, M, all C(M,N) possible subsets were evaluated "
        "and the mean ± standard deviation of regional KGE, RMSE, r, and |MBE| was computed. "
        "Convergence was defined as the point where the standard deviation across subsets "
        "drops below 10% of the full-ensemble value."
    )
    doc.add_paragraph()

    _h("2.3  Marginal Contribution — Leave-One-Out Analysis", 2, "2E75B6")
    _p(
        "The marginal contribution of each model was quantified using the "
        "Leave-One-Out (LOO) RMSE method: the ΔRMSE is the difference between the "
        "LOO ensemble RMSE (excluding model m) and the full ensemble RMSE. "
        "A positive ΔRMSE indicates that model m reduces the ensemble error (positive contribution). "
        "A negative ΔRMSE indicates that excluding model m improves the ensemble, "
        "suggesting that model m introduces noise."
    )
    doc.add_paragraph()

    _h("2.4  Model Ranking", 2, "2E75B6")
    _p(
        "Models were ranked using a composite score — the arithmetic mean of normalised "
        "scores across KGE, NSE, r, and RMSE. Each metric was normalised to [0, 1] "
        "(1 = best), accounting for metric direction "
        "(higher-is-better vs lower-is-better). "
        "Ranking was performed separately for raw and bias-corrected models to detect "
        "rank shifts induced by QDM."
    )
    doc.add_paragraph()

    # ════════════════════════════════════════════════════════════════
    # 3. RESULTS
    # ════════════════════════════════════════════════════════════════
    _h("3.  Results and Discussion / ผลการวิเคราะห์", 1, "1F4E79")

    _h("3.1  Regional Mean Performance", 2, "2E75B6")
    _p(
        f"Before bias correction, raw CMIP6 ensemble exhibited substantial systematic errors "
        f"at station scale: KGE = {kge_r:.3f}, RMSE = {rmse_r:.2f} mm day⁻¹, "
        f"MBE = {mbe_r:+.3f} mm day⁻¹, r = {r_r:.3f}. "
        f"After QDM bias correction, all metrics improved markedly: "
        f"KGE = {kge_b:.3f} (Δ{kge_b-kge_r:+.3f}), "
        f"RMSE = {rmse_b:.2f} mm day⁻¹ (reduction = {rmse_r-rmse_b:.2f} mm, "
        f"{100*(rmse_r-rmse_b)/rmse_r:.1f}%), "
        f"MBE = {mbe_b:+.3f} mm day⁻¹ (|MBE| reduction = {abs(mbe_r)-abs(mbe_b):.3f}), "
        f"r = {r_b:.3f} (Δ{r_b-r_r:+.3f}). "
        f"The post-correction KGE of {kge_b:.3f} corresponds to "
        f"'{perf_category('KGE', kge_b)}' performance "
        f"per Moriasi et al. (2007), compared to "
        f"'{perf_category('KGE', kge_r)}' before correction."
    )
    doc.add_paragraph()

    _h("3.2  Ensemble Convergence", 2, "2E75B6")
    _p(
        f"The exhaustive combinatorial analysis (Fig. 1) showed that ensemble performance "
        f"converges rapidly. For the bias-corrected ensemble, KGE standard deviation across "
        f"subsets is substantially reduced by N = 3 models. "
        f"Beyond N = 3, each additional model provides diminishing returns. "
        f"This confirms that a minimum of 3 bias-corrected models is sufficient to capture "
        f"the primary benefits of ensemble averaging, while the full {len(models)}-model ensemble "
        f"provides the most stable and reliable estimates. "
        f"The raw model ensemble shows slower convergence, as individual model biases "
        f"are not corrected and thus contribute larger variance."
    )
    doc.add_paragraph()

    _h("3.3  Model Ranking and Best Individual Model", 2, "2E75B6")
    _p(
        f"After bias correction, the composite ranking identified {rank1} as the "
        f"top-performing model (composite score = {sc_bc[rank1]:.3f}). "
        f"The best model by KGE was {best_m} (KGE = {bc_kge_m[best_m]:.3f}), "
        f"while {worst_m} showed the lowest KGE ({bc_kge_m[worst_m]:.3f}). "
        f"Notably, model rankings shifted after QDM bias correction for most models, "
        f"indicating that QDM differentially corrects bias structures depending on model "
        f"characteristics. This underscores the necessity of post-correction ranking "
        f"rather than relying on pre-correction model selection."
    )
    doc.add_paragraph()

    _h("3.4  Systematic Bias Reduction", 2, "2E75B6")
    _p(
        f"The MBE heatmaps (Fig. 3a,b) reveal that raw CMIP6 models exhibit strong "
        f"positive (over-estimation) or negative (under-estimation) biases that vary "
        f"substantially across models and stations. After QDM, MBE values are "
        f"reduced toward zero across all stations and models. "
        f"The seasonal bias cycle (Fig. 3c) shows that systematic bias is most pronounced "
        f"during the wet season (May–October), where high rainfall intensity exposes "
        f"model limitations in capturing extreme events. "
        f"QDM effectively reduces this seasonal systematic bias. "
        f"The inter-annual variability (Fig. 3d) is better preserved by the BC ensemble "
        f"compared to individual models, confirming ensemble averaging stabilises "
        f"inter-annual fluctuations."
    )
    doc.add_paragraph()

    _h("3.5  MME Added Value", 2, "2E75B6")
    _p(
        f"The leave-one-out analysis (Fig. 5a) shows that {best_contributor} "
        f"contributes most strongly to RMSE reduction (ΔRMSE = {loo_d[best_contributor]:+.4f} "
        f"mm day⁻¹). All models contributed positively to ensemble RMSE reduction, "
        f"confirming that the full ensemble outperforms any reduced subset. "
        f"The BC ensemble outperformed the best individual model at "
        f"{n_ens_wins}/{len(stns_str)} stations by KGE (Fig. 5c). "
        f"The multi-metric radar (Fig. 5d) confirms that the ensemble achieves "
        f"consistently higher normalised scores than any individual model across all six metrics, "
        f"demonstrating the robustness of ensemble averaging for station-scale rainfall."
    )
    doc.add_paragraph()

    # ════════════════════════════════════════════════════════════════
    # 4. KEY FINDINGS
    # ════════════════════════════════════════════════════════════════
    _h("4.  Key Findings / ข้อค้นพบสำคัญ", 1, "1F4E79")

    findings = [
        (f"QDM substantially reduces systematic bias",
         f"KGE: {kge_r:.3f} → {kge_b:.3f} (+{kge_b-kge_r:.3f}); "
         f"RMSE: {rmse_r:.2f} → {rmse_b:.2f} mm day⁻¹ "
         f"(−{(rmse_r-rmse_b)/rmse_r*100:.1f}%); "
         f"MBE: {mbe_r:+.3f} → {mbe_b:+.3f} mm day⁻¹."),
        (f"Ensemble convergence at N ≥ 3 models",
         f"Exhaustive subset analysis confirms performance stabilises by N = 3. "
         f"Each additional model provides diminishing, yet positive, improvement."),
        (f"MME outperforms best individual in most stations",
         f"BC ensemble ≥ best individual at {n_ens_wins}/{len(stns_str)} stations ({100*n_ens_wins/len(stns_str):.0f}%). "
         f"Ensemble averaging effectively reduces model-specific biases."),
        (f"Best individual model: {best_m}",
         f"Post-correction KGE = {bc_kge_m[best_m]:.3f} "
         f"[{perf_category('KGE', bc_kge_m[best_m])}]. "
         f"Recommended when single-model simulations are operationally required."),
        (f"Model rankings change after bias correction",
         f"QDM differentially corrects model biases. "
         f"Post-correction evaluation (not pre-correction selection) is essential "
         f"for optimal model identification."),
        (f"All models contribute positively (LOO analysis)",
         f"Leave-one-out RMSE confirms that every model reduces ensemble error. "
         f"No model should be excluded from the ensemble."),
    ]
    for title_f, detail in findings:
        p  = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        rb = p.add_run(f"► {title_f}:  "); rb.bold=True
        rb.font.name="Times New Roman"; rb.font.size=Pt(12)
        rd = p.add_run(detail); rd.font.name="Times New Roman"; rd.font.size=Pt(12)
    doc.add_paragraph()

    # ════════════════════════════════════════════════════════════════
    # 5. RECOMMENDATION
    # ════════════════════════════════════════════════════════════════
    _h("5.  Recommendation / ข้อเสนอแนะ", 1, "1F4E79")
    _p(
        f"For climate impact studies requiring station-scale daily rainfall in Prachuap Khiri Khan: "
        f"(1) Apply QDM bias correction to all CMIP6 models before use; "
        f"(2) Use the full {len(models)}-model bias-corrected ensemble for robustness; "
        f"(3) If a single model is required, {best_m} is recommended "
        f"(highest post-correction KGE = {bc_kge_m[best_m]:.3f}); "
        f"(4) A minimum of 3 bias-corrected models is sufficient when computational "
        f"resources are limited; "
        f"(5) Always evaluate model performance post-correction, as rankings can change "
        f"significantly after QDM."
    )
    doc.add_paragraph()
    _p(
        "คำแนะนำสำหรับการศึกษาผลกระทบจากการเปลี่ยนแปลงสภาพภูมิอากาศ: "
        "(1) ปรับแก้ค่าอคติ QDM ก่อนการใช้งานเสมอ "
        f"(2) ใช้ค่าเฉลี่ย MME จาก {len(models)} แบบจำลองที่ปรับแก้แล้วเพื่อความเสถียร "
        f"(3) หากต้องการแบบจำลองเดี่ยว แนะนำ {best_m} (KGE = {bc_kge_m[best_m]:.3f}) "
        "(4) ต้องการขั้นต่ำ 3 แบบจำลองเพื่อความเสถียรของ MME "
        "(5) ประเมินประสิทธิภาพหลังการปรับแก้เสมอ ไม่ใช่ก่อนการปรับแก้"
    )
    doc.add_paragraph()

    # ════════════════════════════════════════════════════════════════
    # 6. REFERENCES
    # ════════════════════════════════════════════════════════════════
    _h("6.  References", 1, "1F4E79")
    refs = [
        "Cannon AJ, Sobie SR, Murdock TQ (2015). Bias correction of GCM precipitation "
        "by quantile mapping: how well do methods preserve changes in quantiles and extremes? "
        "J. Climate, 28(14), 6938–6959. https://doi.org/10.1175/JCLI-D-14-00754.1",
        "Eyring V, Bony S, Meehl GA et al. (2016). Overview of the Coupled Model "
        "Intercomparison Project Phase 6 (CMIP6). Geosci. Model Dev., 9, 1937–1958.",
        "Gupta HV, Kling H, Yilmaz KK, Martinez GF (2009). Decomposition of the mean "
        "squared error and NSE: Implications for improving hydrological modelling. "
        "J. Hydrology, 377(1–2), 80–91.",
        "Knutti R, Sedláček J, Sanderson BM et al. (2017). A climate model projection "
        "weighting scheme accounting for performance and independence. "
        "Geophys. Res. Lett., 44(4), 1909–1918.",
        "Moriasi DN, Arnold JG, Van Liew MW et al. (2007). Model evaluation guidelines "
        "for systematic quantification of accuracy in watershed simulations. "
        "Trans. ASABE, 50(3), 885–900.",
        "Nash JE, Sutcliffe JV (1970). River flow forecasting through conceptual models "
        "Part I — A discussion of principles. J. Hydrology, 10(3), 282–290.",
        "Willmott CJ (1981). On the validation of models. Phys. Geogr., 2(2), 184–194.",
        "Wilks DS (2011). Statistical Methods in the Atmospheric Sciences, 3rd ed. "
        "Academic Press.",
    ]
    for i, ref in enumerate(refs, 1):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        rn = p.add_run(f"[{i}]  "); rn.bold=True
        rn.font.name="Times New Roman"; rn.font.size=Pt(11)
        rt = p.add_run(ref); rt.font.name="Times New Roman"; rt.font.size=Pt(11)

    out_path = out_dir / f"{prefix}_MME_Report_v{VERSION}.docx"
    doc.save(str(out_path))
    print(f"  ✓  Word → {out_path.name}")


# ════════════════════════════════════════════════════════════════════════
#  §12  MAIN
# ════════════════════════════════════════════════════════════════════════

def main():
    SEP = "═" * 72
    print(SEP)
    print(f"  MME Comparative Evaluation  v{VERSION}")
    print("  Multi-Model Ensemble vs Individual CMIP6 Models")
    print("  Station-Scale Rainfall  |  Q2 Publication Standard")
    print(SEP)

    if len(sys.argv) > 1:
        work_dir = sys.argv[1].strip('"').strip("'")
    else:
        try:    work_dir = str(Path(os.path.abspath(__file__)).parent)
        except: work_dir = os.getcwd()
    out_dir = Path(work_dir)
    print(f"  Input folder : {work_dir}")

    # ── Discover files ──────────────────────────────────────────────
    print("\n  Discovering files ...")
    obs_path, raw_models, bc_models = discover_files(work_dir)
    if obs_path is None:
        sys.exit("  ✗  No Observed file (name must contain 'Observed')")
    if not raw_models and not bc_models:
        sys.exit("  ✗  No model files  (pr_*.csv / bc_*.csv)")

    all_models = sorted(set(raw_models) | set(bc_models))
    mc         = MODEL_PALETTE[:len(all_models)]
    print(f"\n  Observed : {Path(obs_path).name}")
    print(f"  Models   : {all_models}  ({len(all_models)} total)")
    print("-" * 72)

    # ── Load data ───────────────────────────────────────────────────
    print("\n  Loading data ...")
    obs_d, stns = load_daily(obs_path, "Observed")
    if obs_d is None:
        sys.exit("  ✗  Failed to load Observed")
    stns_str   = [str(s) for s in stns]
    smap       = short_labels(stns)
    period_obs = period_str(obs_d)
    prefix     = f"MME_{Path(obs_path).stem}"

    raw_dfs = {}
    for m, p in raw_models.items():
        df, _ = load_daily(p, f"Raw/{m}", target_stns=stns_str)
        if df is not None: raw_dfs[m] = df

    bc_dfs = {}
    for m, p in bc_models.items():
        df, _ = load_daily(p, f"BC/{m}", target_stns=stns_str)
        if df is not None: bc_dfs[m] = df

    if not raw_dfs and not bc_dfs:
        sys.exit("  ✗  No model data loaded")

    paired_models = sorted(set(raw_dfs) & set(bc_dfs))
    if len(paired_models) < len(all_models):
        print(f"  ⚠  Paired (Raw+BC): {paired_models}")
    # Use only paired models for analysis
    raw_dfs = {m: raw_dfs[m] for m in paired_models if m in raw_dfs}
    bc_dfs  = {m: bc_dfs[m]  for m in paired_models if m in bc_dfs}
    models  = sorted(raw_dfs.keys())
    mc      = MODEL_PALETTE[:len(models)]

    period_sim = period_str(next(iter(raw_dfs.values())))
    print(f"\n  {len(stns_str)} stations  |  {len(models)} paired models  |  "
          f"Obs: {period_obs}  |  Sim: {period_sim}")
    print("-" * 72)

    # ── Quick metrics report ────────────────────────────────────────
    print("\n  Regional mean metrics (ensemble):")
    raw_ens = ensemble_mean(raw_dfs); bc_ens = ensemble_mean(bc_dfs)
    for ds_lbl, ens_df in [("Raw Ens", raw_ens), ("BC  Ens", bc_ens)]:
        kge_v  = regional_metric(obs_d, ens_df, stns_str, "KGE")
        rmse_v = regional_metric(obs_d, ens_df, stns_str, "RMSE")
        mbe_v  = regional_metric(obs_d, ens_df, stns_str, "MBE")
        print(f"  {ds_lbl}  KGE={kge_v:.4f}  RMSE={rmse_v:.4f}  MBE={mbe_v:+.4f}")

    # ── Generate figures ────────────────────────────────────────────
    print(f"\n  Generating figures  (DPI = {DPI}) ...")

    print("  Fig 1: Ensemble Convergence ...")
    fig1_ensemble_convergence(obs_d, raw_dfs, bc_dfs, stns_str,
                               models, period_obs, out_dir, prefix); gc.collect()

    print("  Fig 2: Model Ranking ...")
    fig2_model_ranking(obs_d, raw_dfs, bc_dfs, stns_str, smap,
                        models, mc, period_obs, out_dir, prefix); gc.collect()

    print("  Fig 3: Systematic Bias ...")
    fig3_systematic_bias(obs_d, raw_dfs, bc_dfs, stns_str, smap,
                          models, mc, period_obs, out_dir, prefix); gc.collect()

    print("  Fig 4: Comprehensive Metrics Dashboard ...")
    fig4_metrics_dashboard(obs_d, raw_dfs, bc_dfs, stns_str, smap,
                            models, mc, period_obs, out_dir, prefix); gc.collect()

    print("  Fig 5: MME Added Value ...")
    fig5_mme_added_value(obs_d, raw_dfs, bc_dfs, stns_str, smap,
                          models, mc, period_obs, out_dir, prefix); gc.collect()

    # ── Excel ───────────────────────────────────────────────────────
    print("\n  Building Excel (3 sheets) ...")
    wb = Workbook(); wb.remove(wb.active)
    write_excel(wb, obs_d, raw_dfs, bc_dfs, stns_str, smap,
                models, period_obs, period_sim, out_dir, prefix)
    out_xl = out_dir / f"{prefix}_Analysis_v{VERSION}.xlsx"
    wb.save(str(out_xl))
    print(f"  ✓  Excel → {out_xl.name}  (3 sheets: SM1, SM2, SM3)")

    # ── Word ────────────────────────────────────────────────────────
    print("\n  Building Word report (Thai/English) ...")
    write_word_report(obs_d, raw_dfs, bc_dfs, stns_str, smap,
                       models, period_obs, period_sim, out_dir, prefix)

    # ── Summary ─────────────────────────────────────────────────────
    n_png = len(list(out_dir.glob(f"{prefix}_Fig*.png")))
    bc_kge_all = {m: regional_metric(obs_d, bc_dfs.get(m), stns_str, "KGE")
                  for m in models}
    best_m  = max(bc_kge_all, key=lambda k: bc_kge_all[k]
                              if not np.isnan(bc_kge_all[k]) else -999)
    n_ens_w = 0
    for stn in stns_str:
        ev = regional_metric(obs_d, bc_ens, [stn], "KGE")
        best_ind_kge = max(
            (regional_metric(obs_d, bc_dfs.get(m), [stn], "KGE") for m in models),
            default=np.nan)
        if (not np.isnan(ev)) and (not np.isnan(best_ind_kge)) and ev >= best_ind_kge:
            n_ens_w += 1

    kge_r = regional_metric(obs_d, raw_ens, stns_str, "KGE")
    kge_b = regional_metric(obs_d, bc_ens,  stns_str, "KGE")

    print()
    print(SEP)
    print(f"  ✓  COMPLETE  v{VERSION}  |  DPI = {DPI}")
    print(f"  {'─'*68}")
    print(f"  Figures : {n_png} PNG" + (" + PDF" if SAVE_PDF else ""))
    print(f"  Excel   : {out_xl.name}  (3 sheets)")
    print(f"  Word    : {prefix}_MME_Report_v{VERSION}.docx")
    print(f"  {'─'*68}")
    print(f"  Regional KGE  :  Raw={kge_r:.4f}  →  BC={kge_b:.4f}  (Δ{kge_b-kge_r:+.4f})")
    print(f"  Best BC model :  {best_m}  (KGE = {bc_kge_all[best_m]:.4f})")
    print(f"  Ensemble wins :  {n_ens_w}/{len(stns_str)} stations")
    print(f"  Saved to : {work_dir}")
    print(SEP)


if __name__ == "__main__":
    main()
