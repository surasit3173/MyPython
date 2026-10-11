"""
===============================================================================
  Research Gap Analysis: Model Selection After Bias Correction
  "Which CMIP6 Model Performs Best After QDM Bias Correction?"
  Multi-Model, Multi-Station, Multi-Scale Evaluation
  มาตรฐานวารสาร Q1–Q3
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ไฟล์ Input (ในโฟลเดอร์เดียวกับ script):
    • Observed  → ชื่อไฟล์มีคำว่า "Observed"
    • Raw CMIP6 → ชื่อขึ้นต้นด้วย "pr_"   เช่น pr_day_ACCESS-ESM1-5_daily.csv
    • BC/QDM    → ชื่อขึ้นต้นด้วย "bc_"   เช่น bc_pr_day_ACCESS-ESM1-5_daily.csv

  Output:
    Output_ModelSelection_<basename>.xlsx   (8 sheets)
    Output_ModelSelection_Fig1_PerformanceHeatmap.png
    Output_ModelSelection_Fig2_RankingRadar.png
    Output_ModelSelection_Fig3_BestModelSummary.png
    Output_ModelSelection_Fig4_EnsembleMean.png
    Output_ModelSelection_Fig5_ConsistencyMap.png
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [FIX LOG v2]
  Fix-1 : extract_model – รองรับ pr_day_MODEL_ และ bc_pr_day_MODEL_ ถูกต้อง
  Fix-2 : DPI = 600 ทุก figure
  Fix-3 : ลบสัญลักษณ์เหรียญ (🥇🥈🥉) ออกจากทุก figure
  Fix-4 : แกน X ทุก figure ใช้ rotation=0 (แนวนอน), ขยาย figsize
  Fix-5 : Skill Score Ensemble = 1 − ΣE_ens / ΣE_clim (aggregate ถูกต้อง)
  Fix-6 : Composite Score ใช้ Weighted composite (KGE=0.30, NSE=0.25, …)
  Fix-7 : เพิ่มการวิเคราะห์ Seasonal (ฤดูฝน พ.ค.–ต.ค.)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  อ้างอิง:
    Gleckler et al. (2008) J. Geophys. Res.  [Relative Performance Index]
    Reichler & Kim (2008) Bull. AMS          [Model Skill Score]
    Gupta et al. (2009) J. Hydrol.           [KGE]
    Nash & Sutcliffe (1970) J. Hydrol.       [NSE]
    Cannon et al. (2015) J. Climate          [QDM]
    Knutti et al. (2017) Nat. Clim. Chang.   [Model selection]
    Eyring et al. (2016) Geosci. Model Dev.  [CMIP6]
===============================================================================
"""

import os, sys, re, math, warnings, itertools
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats as sps
from scipy.stats import gaussian_kde

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker
import matplotlib.gridspec as gridspec
import matplotlib.colors as mcolors
from matplotlib.lines  import Line2D
from matplotlib.colors import Normalize, LinearSegmentedColormap, BoundaryNorm
import matplotlib.cm    as cm
from mpl_toolkits.axes_grid1 import make_axes_locatable

from openpyxl import Workbook
from openpyxl.styles import (PatternFill, Font, Alignment, Border, Side,
                              GradientFill)
from openpyxl.utils   import get_column_letter
from openpyxl.formatting.rule import ColorScaleRule

warnings.filterwarnings("ignore")

# ═══════════════════════════════════════════════════════════════════════════
# 0.  GLOBAL STYLE
# ═══════════════════════════════════════════════════════════════════════════
plt.rcParams.update({
    "font.family":        "serif",
    "font.serif":         ["Times New Roman", "DejaVu Serif"],
    "font.size":          11,
    "axes.titlesize":     12,
    "axes.labelsize":     11,
    "xtick.labelsize":    10,
    "ytick.labelsize":    10,
    "legend.fontsize":    10,
    "figure.titlesize":   13,
    "lines.linewidth":    1.8,
    "axes.linewidth":     0.9,
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.grid":          True,
    "grid.linestyle":     "--",
    "grid.linewidth":     0.4,
    "grid.alpha":         0.45,
    "grid.color":         "#B0BEC5",
    "savefig.dpi":        600,          # FIX-2: DPI=600
    "savefig.bbox":       "tight",
    "savefig.pad_inches": 0.15,
    "figure.dpi":         120,
    "mathtext.fontset":   "stix",
})

# Colour palette – one colour per model (up to 12 models)
MODEL_PALETTE = [
    "#1565C0","#C62828","#2E7D32","#E65100","#6A1B9A",
    "#00695C","#AD1457","#4527A0","#0277BD","#558B2F",
    "#4E342E","#37474F",
]
WET_THR = 1.0

# FIX-7: Wet season months (May–Oct = Thai monsoon season)
WET_MONTHS = [5, 6, 7, 8, 9, 10]

# ── Excel helpers ──────────────────────────────────────────────────────────
XC = dict(
    title="13293D", sub="1F4E79", hdr="2E75B6",
    best="FFF9C4",  best_f="E65100",
    improve="C8E6C9", degrade="FFCCBC",
    note="ECEFF1",  white="FFFFFF", alt="F5F5F5",
    rank1="FFD700", rank2="D7D7D7", rank3="CD7F32",
)
THIN = Side(style="thin",   color="BDBDBD")
MED  = Side(style="medium", color="1F4E79")
def tb():  return Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
def tbt(): return Border(left=MED,  right=MED,  top=MED,  bottom=MED)
def xfill(h): return PatternFill("solid", fgColor=h)

def xsc(ws, r, c, val=None, bold=False, italic=False,
        fc=None, bg=None, align="center", sz=10,
        wrap=True, border=None, num_fmt=None):
    cell = ws.cell(row=r, column=c)
    if val is not None: cell.value = val
    cell.font = Font(bold=bold, italic=italic, name="Calibri", size=sz,
                     color=fc if fc else "1A1A1A")
    cell.alignment = Alignment(horizontal=align, vertical="center",
                                wrap_text=wrap)
    if bg:      cell.fill = xfill(bg)
    if border:  cell.border = border
    if num_fmt: cell.number_format = num_fmt
    return cell

def mxsc(ws, r, c1, c2, val, **kw):
    ws.merge_cells(start_row=r, start_column=c1, end_row=r, end_column=c2)
    return xsc(ws, r, c1, val, **kw)

def cw(ws, col, w):
    ws.column_dimensions[get_column_letter(col)].width = w

# ═══════════════════════════════════════════════════════════════════════════
# 1.  FILE DISCOVERY  ← multi-model aware
# ═══════════════════════════════════════════════════════════════════════════

def discover_files(folder: str):
    """
    Returns:
        obs_path   : str
        raw_models : dict  {model_name: path}
        bc_models  : dict  {model_name: path}

    FIX-1: Robust model name extraction that handles:
        pr_day_MODEL_...       → MODEL
        pr_MODEL_...           → MODEL
        bc_pr_day_MODEL_...    → MODEL
        bc_pr_MODEL_...        → MODEL
        bc_MODEL_...           → MODEL
    """
    all_csv = list(Path(folder).glob("*.csv"))

    # Observed
    obs_files = [f for f in all_csv if "observed" in f.name.lower()]
    obs_path  = str(obs_files[0]) if obs_files else None
    if len(obs_files) > 1:
        print(f"  WARNING  Multiple Observed files - using {obs_files[0].name}")

    # Raw CMIP6
    raw_files = [f for f in all_csv if f.name.lower().startswith("pr")]
    # BC/QDM
    bc_files  = [f for f in all_csv if f.name.lower().startswith("bc")]

    # FIX-1: Improved extract_model - strips all known prefixes before model name
    def extract_model(fname, kind):
        """
        kind = 'raw' or 'bc'
        Strips leading tokens (pr, day, bc, pr, day) until a token that is
        NOT one of the known prefix words is found – that is the model name.
        """
        stem = Path(fname).stem.lower()

        # Normalise separators (hyphens in model names like ACCESS-ESM1-5 must survive)
        # Split only on underscores
        parts = Path(fname).stem.split("_")

        # Known prefix tokens (case-insensitive)
        PREFIX_TOKENS = {"pr", "bc", "day", "mon", "yr", "daily", "monthly"}

        model_parts = []
        skip = True
        for part in parts:
            if skip and part.lower() in PREFIX_TOKENS:
                continue
            else:
                skip = False
                model_parts.append(part)

        if not model_parts:
            return "Model"

        # The first non-prefix token is the model name.
        # However, some model names look like "ACCESS" from "ACCESS-ESM1-5"
        # where hyphens become underscores in some conventions.
        # We take parts[0] but also try to pick up a second part if the
        # first part looks like an abbreviation (all-caps, <=8 chars).
        model_name = model_parts[0]

        # Heuristic: if next part looks like continuation of model name
        # (starts with digit or is a known suffix like ESM, CM, etc.), join them.
        if len(model_parts) > 1:
            next_p = model_parts[1]
            # Join if next part starts with a digit OR is short alphabetic suffix
            if (next_p and (next_p[0].isdigit() or
                            (next_p.isalpha() and len(next_p) <= 4) or
                            re.match(r'^[A-Za-z]{1,4}\d', next_p))):
                model_name = f"{model_parts[0]}-{model_parts[1]}"

        return model_name if model_name else "Model"

    raw_models = {}
    for f in raw_files:
        mname = extract_model(f.name, 'raw')
        if mname in raw_models:
            print(f"  WARNING  Duplicate Raw model '{mname}' - skipping {f.name}")
        else:
            raw_models[mname] = str(f)

    bc_models = {}
    for f in bc_files:
        mname = extract_model(f.name, 'bc')
        if mname in bc_models:
            print(f"  WARNING  Duplicate BC model '{mname}' - skipping {f.name}")
        else:
            bc_models[mname] = str(f)

    # Warn about missing pairs
    raw_set, bc_set = set(raw_models), set(bc_models)
    for m in raw_set - bc_set:
        print(f"  WARNING  No BC file for model '{m}' - will analyse Raw only")
    for m in bc_set - raw_set:
        print(f"  WARNING  No Raw file for model '{m}' - will analyse BC only")

    return obs_path, raw_models, bc_models

# ═══════════════════════════════════════════════════════════════════════════
# 2.  DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════
MISS = [-99, -999, -9999, -9.99e+20, 9.99e+20, 1e+20]

def load_daily(path, label):
    if path is None or not os.path.isfile(path):
        print(f"  X  Not found: {label}"); return None, []
    df = pd.read_csv(path)
    for mv in MISS: df.replace(mv, np.nan, inplace=True)
    num = df.select_dtypes(include=[np.number]).columns
    df[num] = df[num].where(df[num] >= 0)
    stns = [c for c in df.columns if c not in ("YEAR","MONTH","DAY")]
    try:
        df["date"] = pd.to_datetime(
            {"year":df["YEAR"],"month":df["MONTH"],"day":df["DAY"]})
        df = df.set_index("date")[stns]
    except:
        df = df[stns]
    return df, stns

def to_monthly(d):
    if d is None: return None
    return d.resample("MS").apply(
        lambda g: g.sum(min_count=int(0.8*len(g))))

def to_annual(d):
    if d is None: return None
    return d.resample("YS").apply(
        lambda g: g.sum(min_count=int(0.8*len(g))))

# FIX-7: Seasonal (wet season) extraction
def to_seasonal_wet(d):
    """Extract wet season (May-Oct) daily data, then aggregate to seasonal totals."""
    if d is None: return None
    wet = d[d.index.month.isin(WET_MONTHS)]
    # Group by year-season: each year's wet season sum
    return wet.resample("YS").apply(
        lambda g: g.sum(min_count=int(0.6*len(g))))

def align_pair(df1, df2):
    if df1 is None or df2 is None: return None, None
    common = df1.index.intersection(df2.index)
    if len(common) == 0: return None, None
    return df1.loc[common], df2.loc[common]

def gcol(df, stn):
    if df is None or stn not in df.columns:
        return np.array([], dtype=float)
    v = df[stn].values.astype(float)
    return v[~np.isnan(v) & (v >= 0)]

def period_str(df):
    if df is None: return "N/A"
    try: return f"{df.index[0].year}-{df.index[-1].year}"
    except: return "N/A"

def short_labels(stns):
    return {str(s): f"S{i+1}" for i, s in enumerate(stns)}

# ═══════════════════════════════════════════════════════════════════════════
# 3.  PERFORMANCE METRICS  (full suite)
# ═══════════════════════════════════════════════════════════════════════════

METRICS_LIST = ["RMSE","MAE","MBE","Pbias (%)","r","NSE","KGE","d","RPI"]
LOWER_BETTER = {"RMSE","MAE","MBE","Pbias (%)","RPI"}
HIGHER_BETTER= {"r","NSE","KGE","d"}

# FIX-6: Weighted composite (Knutti et al. 2017 recommendation)
COMPOSITE_WEIGHTS = {
    "KGE":      0.30,
    "NSE":      0.25,
    "RMSE":     0.15,
    "r":        0.10,
    "d":        0.10,
    "Pbias (%)":0.05,
    "RPI":      0.05,
}

def compute_metrics(obs_arr, sim_arr, model, stn, scale, dataset="Raw"):
    """Full metrics suite including Relative Performance Index (RPI)."""
    null = {k:np.nan for k in
            ["Model","Dataset","Station","Scale","N"] + METRICS_LIST}
    null.update({"Model":model,"Dataset":dataset,"Station":stn,"Scale":scale})

    o = obs_arr[~np.isnan(obs_arr)].astype(float)
    s = sim_arr[~np.isnan(sim_arr)].astype(float)
    n = min(len(o), len(s))
    if n < 5: return null

    o, s = o[:n], s[:n]
    mask  = ~np.isnan(o) & ~np.isnan(s)
    o, s  = o[mask], s[mask]
    if len(o) < 5: return null

    res   = s - o
    rmse  = float(np.sqrt(np.mean(res**2)))
    mae   = float(np.mean(np.abs(res)))
    mbe   = float(np.mean(res))
    pbias = float(100*np.sum(res)/np.sum(o)) if np.sum(o) else np.nan
    r     = float(np.corrcoef(o,s)[0,1])
    d_nse = np.sum((o-np.mean(o))**2)
    nse   = float(1 - np.sum(res**2)/d_nse) if d_nse else np.nan
    alpha = float(np.std(s,ddof=1)/np.std(o,ddof=1)) if np.std(o,ddof=1) else np.nan
    beta  = float(np.mean(s)/np.mean(o)) if np.mean(o) else np.nan
    kge   = float(1-math.sqrt((r-1)**2+(alpha-1)**2+(beta-1)**2)) \
            if not (np.isnan(alpha) or np.isnan(beta)) else np.nan
    d_ioa = np.sum((np.abs(s-np.mean(o))+np.abs(o-np.mean(o)))**2)
    ioa   = float(1 - np.sum(res**2)/d_ioa) if d_ioa else np.nan

    return {"Model":model,"Dataset":dataset,"Station":stn,"Scale":scale,
            "N":len(o),
            "RMSE":round(rmse,3),"MAE":round(mae,3),"MBE":round(mbe,3),
            "Pbias (%)":round(pbias,2),"r":round(r,4),
            "NSE":round(float(nse),4),"KGE":round(float(kge),4),
            "d":round(float(ioa),4),
            "RPI":np.nan}

def add_rpi(metric_rows):
    """
    Relative Performance Index (Gleckler et al. 2008):
    RPI_m = (E_m - E_ref) / E_ref  where E_ref = median RMSE across all models.
    """
    stns   = sorted(set(r["Station"] for r in metric_rows))
    scales = sorted(set(r["Scale"]   for r in metric_rows))
    for stn in stns:
        for scale in scales:
            sub  = [r for r in metric_rows
                    if r["Station"]==stn and r["Scale"]==scale]
            rmse_vals = [r["RMSE"] for r in sub if not np.isnan(r["RMSE"])]
            if not rmse_vals: continue
            e_ref = float(np.median(rmse_vals))
            for r in sub:
                if e_ref and not np.isnan(r["RMSE"]):
                    r["RPI"] = round((r["RMSE"] - e_ref) / e_ref, 4)
    return metric_rows

# FIX-5: Correct Skill Score – aggregate version
def skill_score_aggregate(obs_arr, sim_arr):
    """
    Skill Score (Reichler & Kim 2008) – aggregate formulation:
    SS = 1 - SUM(E_sim) / SUM(E_clim)
    where E = squared error contribution per observation.
    This is the correct approach for ensemble/aggregate evaluation.
    """
    mask = ~np.isnan(obs_arr) & ~np.isnan(sim_arr)
    o = obs_arr[mask].astype(float)
    s = sim_arr[mask].astype(float)
    if len(o) < 10:
        return np.nan
    e_sim  = np.sum((s - o)**2)
    e_clim = np.sum((o - np.mean(o))**2)
    return float(1.0 - e_sim / e_clim) if e_clim > 0 else np.nan

# Per-station skill score (for individual model rows)
def skill_score(obs_arr, sim_arr):
    """MSE-based skill score vs climatological mean for a single series."""
    mask = ~np.isnan(obs_arr) & ~np.isnan(sim_arr)
    o = obs_arr[mask].astype(float)
    s = sim_arr[mask].astype(float)
    if len(o) < 10:
        return np.nan
    mse_model = np.mean((s - o)**2)
    mse_clim  = np.mean((o - np.mean(o))**2)
    return float(1.0 - mse_model / mse_clim) if mse_clim > 0 else np.nan

# ═══════════════════════════════════════════════════════════════════════════
# 4.  COMPOSITE RANKING  – FIX-6: Weighted composite score
# ═══════════════════════════════════════════════════════════════════════════

RANK_METRICS = ["RMSE","NSE","KGE","r","d","Pbias (%)","RPI"]

def composite_ranking(metric_rows, dataset_filter=None):
    """
    FIX-6: Weighted composite score.
    WEIGHTS = KGE:0.30, NSE:0.25, RMSE:0.15, r:0.10, d:0.10,
              Pbias(%):0.05, RPI:0.05
    Returns DataFrame sorted by rank (highest score = best).
    """
    if dataset_filter:
        rows = [r for r in metric_rows if r["Dataset"]==dataset_filter]
    else:
        rows = metric_rows

    models = sorted(set(r["Model"] for r in rows))
    data   = {}
    for m in models:
        sub = [r for r in rows if r["Model"]==m]
        row = {"Model": m}
        for met in RANK_METRICS:
            vals = [r[met] for r in sub
                    if not (isinstance(r[met],float) and np.isnan(r[met]))]
            row[met] = float(np.mean(vals)) if vals else np.nan
        data[m] = row

    df = pd.DataFrame(list(data.values())).set_index("Model")

    # Normalise each metric to [0, 1]
    norm_score = pd.DataFrame(index=df.index, columns=RANK_METRICS, dtype=float)
    for m in RANK_METRICS:
        vals = df[m].values.astype(float)
        rng  = np.nanmax(vals) - np.nanmin(vals)
        if rng == 0:
            norm_score[m] = 1.0
        elif m in LOWER_BETTER:
            norm_score[m] = (np.nanmax(vals) - vals) / rng
        else:
            norm_score[m] = (vals - np.nanmin(vals)) / rng

    # FIX-6: Weighted sum (weights from COMPOSITE_WEIGHTS, keys mapped to RANK_METRICS)
    total_weight = sum(COMPOSITE_WEIGHTS.get(m, 0) for m in RANK_METRICS)
    weighted_sum = pd.Series(0.0, index=df.index)
    for m in RANK_METRICS:
        w = COMPOSITE_WEIGHTS.get(m, 0) / total_weight
        weighted_sum += norm_score[m].fillna(0.0) * w

    df["Composite Score"] = weighted_sum
    df["Rank"] = df["Composite Score"].rank(
        ascending=False, na_option="bottom").fillna(len(df)+1).astype(int)
    return df.sort_values("Rank")

# ═══════════════════════════════════════════════════════════════════════════
# 5.  ENSEMBLE MEAN
# ═══════════════════════════════════════════════════════════════════════════

def ensemble_mean_df(model_dfs: dict):
    """Compute ensemble mean from dict of {model: DataFrame}."""
    valid = [df for df in model_dfs.values() if df is not None]
    if not valid: return None
    common = valid[0].index
    for df in valid[1:]:
        common = common.intersection(df.index)
    if len(common) == 0: return None
    stack = np.stack([df.loc[common].values.astype(float)
                      for df in valid], axis=0)
    mean_v = np.nanmean(stack, axis=0)
    cols   = valid[0].columns
    return pd.DataFrame(mean_v, index=common, columns=cols)

# ═══════════════════════════════════════════════════════════════════════════
# 6.  FIGURE HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _wrap_labels(labels, max_len=14):
    """Wrap long model names for axis tick readability."""
    out = []
    for lb in labels:
        if len(lb) > max_len:
            # Try to break at a hyphen
            parts = lb.split("-")
            if len(parts) >= 2:
                mid = len(parts) // 2
                lb  = "-".join(parts[:mid]) + "\n" + "-".join(parts[mid:])
        out.append(lb)
    return out

# ═══════════════════════════════════════════════════════════════════════════
# 7.  FIGURE 1 – PERFORMANCE HEATMAP
# ═══════════════════════════════════════════════════════════════════════════

def fig_performance_heatmap(raw_rows, bc_rows, models, stns, smap,
                             period_obs, period_sim, out_path):
    """
    2-column heatmap: left=Raw, right=QDM.
    FIX-3: No medal symbols.
    FIX-4: x-axis rotation=0, wider figure.
    FIX-2: dpi=600.
    """
    show_metrics = ["NSE","KGE","r","RMSE","Pbias (%)"]
    stns_str     = [str(s) for s in stns]
    codes        = [smap[s] for s in stns_str]
    n_m          = len(models)
    n_s          = len(stns)

    # FIX-4: Wider figure for horizontal labels
    fig, axes = plt.subplots(
        len(show_metrics), 2,
        figsize=(max(16, n_m*2.2 + 6), 3.2*len(show_metrics)),
        gridspec_kw={"wspace":0.10, "hspace":0.60}
    )
    fig.subplots_adjust(left=0.12, right=0.95, top=0.91, bottom=0.08)

    cmaps = {"NSE":"RdYlGn","KGE":"RdYlGn","r":"YlGn",
             "RMSE":"RdYlGn_r","Pbias (%)":"RdBu_r"}
    vranges = {"NSE":(-1,1),"KGE":(-1,1),"r":(0,1),
               "RMSE":(None,None),"Pbias (%)":(None,None)}

    model_labels = _wrap_labels(models)

    def build_matrix(rows_list, met):
        mat = np.full((n_m, n_s), np.nan)
        for mi, mod in enumerate(models):
            for si, stn in enumerate(stns_str):
                sub = [r for r in rows_list
                       if r["Model"]==mod and r["Station"]==stn]
                if sub: mat[mi,si] = sub[0].get(met, np.nan)
        return mat

    for ri, met in enumerate(show_metrics):
        for di, (row_list, ds_label) in enumerate([
            (raw_rows,"Raw CMIP6"), (bc_rows,"Bias-Corrected (QDM)")
        ]):
            ax  = axes[ri, di]
            mat = build_matrix(row_list, met)
            vmin, vmax = vranges[met]
            if vmin is None:
                abs_max = np.nanmax(np.abs(mat)) if not np.all(np.isnan(mat)) else 1.0
                vmin, vmax = -abs_max, abs_max

            im = ax.imshow(mat, cmap=cmaps[met],
                           vmin=vmin, vmax=vmax,
                           aspect="auto", interpolation="nearest")

            for mi in range(n_m):
                for si in range(n_s):
                    val = mat[mi, si]
                    if not np.isnan(val):
                        mid_val = (vmin+vmax)/2 if vmin is not None else 0
                        tc = "white" if (abs(val-mid_val)/(abs(vmax-vmin)+1e-9)>0.5) \
                             else "black"
                        ax.text(si, mi, f"{val:.2f}",
                                ha="center", va="center",
                                fontsize=7.5, color=tc, fontweight="bold")

            # FIX-4: rotation=0 for x-axis
            ax.set_xticks(range(n_s))
            ax.set_yticks(range(n_m))
            ax.set_xticklabels(codes, rotation=0, ha="center", fontsize=9)
            if di == 0:
                ax.set_yticklabels(model_labels, fontsize=9)
                ax.set_ylabel(met, fontsize=11, fontweight="bold", labelpad=4)
            else:
                ax.set_yticklabels([])
            ax.set_xlabel("Station Code", fontsize=10, labelpad=3)
            ax.set_title(f"{ds_label}", fontsize=10,
                         fontweight="bold", pad=3, color="#1F4E79")

            plt.colorbar(im, ax=ax, orientation="vertical",
                         pad=0.02, fraction=0.04, shrink=0.85)

    fig.suptitle(
        "Model Performance Heatmap — All Models x All Stations\n"
        f"Raw CMIP6 (left)  vs  Bias-Corrected/QDM (right)  |  "
        f"Obs: {period_obs}  |  Sim: {period_sim}",
        fontsize=13, fontweight="bold")

    plt.savefig(out_path, dpi=600)   # FIX-2
    plt.close(fig)
    print(f"    OK  {Path(out_path).name}")

# ═══════════════════════════════════════════════════════════════════════════
# 8.  FIGURE 2 – RANKING RADAR + COMPOSITE SCORE BAR
# ═══════════════════════════════════════════════════════════════════════════

def fig_ranking_radar(rank_raw, rank_bc, models, model_colors,
                      period_obs, out_path):
    """
    FIX-3: No medal emojis in figure.
    FIX-4: x-axis rotation=0, wider figure.
    """
    n_m = len(models)
    # FIX-4: Wider figure
    fig = plt.figure(figsize=(max(20, n_m*2.4 + 10), 9))
    axL = fig.add_subplot(1, 2, 1)
    axR_polar = fig.add_subplot(1, 2, 2, polar=True)
    fig.subplots_adjust(left=0.06, right=0.97, top=0.87,
                        bottom=0.15, wspace=0.30)

    x   = np.arange(n_m)
    bw  = 0.38

    scores_raw = [rank_raw.loc[m,"Composite Score"]
                  if m in rank_raw.index else np.nan for m in models]
    scores_bc  = [rank_bc.loc[m,"Composite Score"]
                  if m in rank_bc.index else np.nan for m in models]

    b1 = axL.bar(x-bw/2, scores_raw, width=bw,
                 color="#EF9A9A", edgecolor="#C62828", linewidth=0.9,
                 alpha=0.85, label="Raw CMIP6", zorder=3)
    b2 = axL.bar(x+bw/2, scores_bc, width=bw,
                 color="#90CAF9", edgecolor="#1565C0", linewidth=0.9,
                 alpha=0.85, label="Bias-Corrected (QDM)", zorder=3)

    for bar, col in zip(b2, model_colors):
        bar.set_facecolor(mcolors.to_rgba(col, 0.75))
        bar.set_edgecolor(col)

    for b, sc in [(b1,scores_raw),(b2,scores_bc)]:
        for bar, v in zip(b, sc):
            if not np.isnan(v):
                axL.text(bar.get_x()+bar.get_width()/2,
                         v+0.01, f"{v:.3f}",
                         ha="center", va="bottom",
                         fontsize=9, fontweight="bold")

    # FIX-4: rotation=0
    axL.set_xticks(x)
    axL.set_xticklabels(_wrap_labels(models), rotation=0, ha="center", fontsize=9)
    axL.set_xlabel("CMIP6 Model", fontsize=11, labelpad=6)
    axL.set_ylabel("Composite Score (Weighted)\n(0=worst, 1=best)", fontsize=11)
    axL.set_ylim(0, 1.20)
    axL.set_title("(a)  Composite Score Before vs After QDM\n"
                  "     Weighted: KGE(0.30), NSE(0.25), RMSE(0.15), r(0.10)...",
                  loc="left", fontsize=11, fontweight="bold", pad=5)
    axL.spines["top"].set_visible(False)
    axL.spines["right"].set_visible(False)
    axL.legend(fontsize=10, frameon=True, edgecolor="#B0BEC5",
               loc="upper right")

    # Rank annotation as text (FIX-3: no medal emoji)
    for mi, m in enumerate(models):
        if m in rank_bc.index:
            rnk = int(rank_bc.loc[m, "Rank"])
            if rnk <= 3:
                axL.text(mi+bw/2, scores_bc[mi]+0.08,
                         f"#{rnk}", ha="center", fontsize=10,
                         fontweight="bold", color="#C62828")

    # Radar
    n_dim  = len(RANK_METRICS)
    angles = np.linspace(0, 2*np.pi, n_dim, endpoint=False).tolist()
    angles += angles[:1]

    axR_polar.set_thetagrids(np.degrees(angles[:-1]),
                              RANK_METRICS, fontsize=9.5)
    axR_polar.set_ylim(0, 1)
    axR_polar.set_yticks([0.25,0.50,0.75,1.00])
    axR_polar.set_yticklabels(["0.25","0.50","0.75","1.00"],
                               fontsize=8, color="#78909C")

    for model, col in zip(models, model_colors):
        if model not in rank_bc.index: continue
        row  = rank_bc.loc[model]
        vals = []
        for m_r in RANK_METRICS:
            v    = float(row.get(m_r, np.nan))
            allv = rank_bc[m_r].values.astype(float)
            rng  = np.nanmax(allv)-np.nanmin(allv)
            if np.isnan(v) or rng==0: vals.append(0.5)
            elif m_r in LOWER_BETTER:
                vals.append((np.nanmax(allv)-v)/rng)
            else:
                vals.append((v-np.nanmin(allv))/rng)
        vals += vals[:1]
        axR_polar.fill(angles, vals, color=col, alpha=0.18)
        axR_polar.plot(angles, vals, color=col, lw=1.8,
                       label=f"{model} (Rank {int(row['Rank'])})")

    axR_polar.set_title("(b)  Normalised Multi-Metric Radar\n"
                         "     After QDM Bias Correction",
                         fontsize=12, fontweight="bold", pad=20)
    axR_polar.legend(loc="lower right", bbox_to_anchor=(1.60,-0.12),
                     fontsize=9, frameon=True, edgecolor="#B0BEC5",
                     handlelength=1.6)
    axR_polar.grid(True, lw=0.5, alpha=0.55)

    fig.suptitle(
        "Model Ranking After Bias Correction (QDM) — Weighted Composite Score\n"
        f"Research Gap: Which CMIP6 model performs best after QDM?  |  "
        f"Obs: {period_obs}",
        fontsize=13, fontweight="bold")

    plt.savefig(out_path, dpi=600)   # FIX-2
    plt.close(fig)
    print(f"    OK  {Path(out_path).name}")

# ═══════════════════════════════════════════════════════════════════════════
# 9.  FIGURE 3 – BEST MODEL SUMMARY
# ═══════════════════════════════════════════════════════════════════════════

def fig_best_model_summary(bc_rows, raw_rows, models, stns, smap,
                            model_colors, period_obs, period_sim, out_path):
    """
    FIX-3: No medal emoji.
    FIX-4: x-axis rotation=0, wider figure.
    """
    stns_str = [str(s) for s in stns]
    codes    = [smap[s] for s in stns_str]
    n_s      = len(stns); n_m = len(models)

    best_model_per_stn = {}
    best_kge_per_stn   = {}
    for stn in stns_str:
        best_m, best_v = None, -np.inf
        for m in models:
            sub = [r for r in bc_rows if r["Model"]==m and r["Station"]==stn]
            if sub and not np.isnan(sub[0]["KGE"]):
                if sub[0]["KGE"] > best_v:
                    best_v, best_m = sub[0]["KGE"], m
        best_model_per_stn[stn] = best_m
        best_kge_per_stn[stn]   = best_v

    kge_gain = {}
    for m in models:
        kge_gain[m] = []
        for stn in stns_str:
            r_sub = [r for r in raw_rows if r["Model"]==m and r["Station"]==stn]
            b_sub = [r for r in bc_rows  if r["Model"]==m and r["Station"]==stn]
            if r_sub and b_sub and not (np.isnan(r_sub[0]["KGE"]) or
                                         np.isnan(b_sub[0]["KGE"])):
                kge_gain[m].append(b_sub[0]["KGE"] - r_sub[0]["KGE"])
            else:
                kge_gain[m].append(np.nan)

    win_count = {m: sum(1 for s in stns_str if best_model_per_stn.get(s)==m)
                 for m in models}

    # FIX-4: Wider figure
    fig, axes = plt.subplots(3, 1, figsize=(max(18, n_s*1.1 + 8), 16))
    fig.subplots_adjust(hspace=0.50, left=0.07, right=0.97,
                        top=0.91, bottom=0.07)

    x  = np.arange(n_s)

    # Panel (a)
    ax = axes[0]
    for si, stn in enumerate(stns_str):
        bm  = best_model_per_stn.get(stn)
        bv  = best_kge_per_stn.get(stn, np.nan)
        col = model_colors[models.index(bm)] if bm and bm in models else "#9E9E9E"
        ax.bar(si, bv, color=col, edgecolor="white",
               linewidth=0.6, alpha=0.88, zorder=3)
        ax.text(si, (bv or 0)+0.01, bm[:10] if bm else "-",
                ha="center", va="bottom", fontsize=8.5,
                fontweight="bold", color=col, rotation=0)  # FIX-4

    # FIX-4
    ax.set_xticks(x)
    ax.set_xticklabels(codes, rotation=0, ha="center", fontsize=10)
    ax.set_xlabel("Station Code", fontsize=11, labelpad=4)
    ax.set_ylabel("KGE (Best Model)", fontsize=11)
    ax.set_title("(a)  Best CMIP6 Model per Station After QDM\n"
                 "     (bar height = KGE of winner; label = model name)",
                 loc="left", fontsize=12, fontweight="bold", pad=5)
    ax.axhline(0, color="grey", lw=0.8, ls="--", alpha=0.6)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    handles_a = [mpatches.Patch(color=model_colors[i], alpha=0.85, label=m)
                 for i, m in enumerate(models)]
    ax.legend(handles=handles_a, fontsize=9, frameon=True,
              edgecolor="#B0BEC5", loc="lower right", ncol=min(n_m,4))

    # Panel (b)
    ax2 = axes[1]
    grp_w = 0.7
    bar_w = grp_w / n_m
    for mi, m in enumerate(models):
        offs = (mi - n_m/2 + 0.5) * bar_w
        gains = kge_gain[m]
        ax2.bar(x + offs, gains, width=bar_w*0.9,
                color=model_colors[mi], alpha=0.82,
                edgecolor="white", linewidth=0.4,
                label=m, zorder=3)

    ax2.axhline(0, color="grey", lw=0.9, ls="--", alpha=0.7)
    ax2.set_xticks(x)
    ax2.set_xticklabels(codes, rotation=0, ha="center", fontsize=10)  # FIX-4
    ax2.set_xlabel("Station Code", fontsize=11, labelpad=4)
    ax2.set_ylabel("DELTA KGE  (QDM minus Raw)", fontsize=11)
    ax2.set_title("(b)  KGE Gain After QDM per Model per Station\n"
                  "     (positive = QDM improved; negative = QDM degraded)",
                  loc="left", fontsize=12, fontweight="bold", pad=5)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.legend(fontsize=9.5, frameon=True, edgecolor="#B0BEC5",
               loc="upper right", ncol=min(n_m,4))

    # Panel (c) – FIX-3: No medal emoji; use rank labels instead
    ax3 = axes[2]
    wins = [win_count.get(m,0) for m in models]
    sorted_wins = sorted(enumerate(wins), key=lambda x: -x[1])

    bars3 = ax3.bar(_wrap_labels(models), wins,
                    color=model_colors[:n_m], alpha=0.85,
                    edgecolor="white", linewidth=0.6, zorder=3)
    for i, (bar, w) in enumerate(zip(bars3, wins)):
        ax3.text(bar.get_x()+bar.get_width()/2, w+0.05,
                 str(w), ha="center", va="bottom",
                 fontsize=11, fontweight="bold")

    ax3.set_ylabel("Number of Stations Won", fontsize=11)
    ax3.set_xlabel("CMIP6 Model", fontsize=11, labelpad=6)
    ax3.set_title("(c)  Model Win Count — Number of Stations Where Each Model Ranks Best\n"
                  "     (after QDM bias correction, by KGE)",
                  loc="left", fontsize=12, fontweight="bold", pad=5)
    # FIX-4: rotation=0
    ax3.tick_params(axis='x', rotation=0, labelsize=9)
    ax3.spines["top"].set_visible(False)
    ax3.spines["right"].set_visible(False)
    ax3.set_ylim(0, n_s+1.5)
    ax3.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    fig.suptitle(
        "Best Model Summary — Station-by-Station Analysis After QDM\n"
        f"Obs: {period_obs}  |  Sim: {period_sim}",
        fontsize=13, fontweight="bold")

    plt.savefig(out_path, dpi=600)   # FIX-2
    plt.close(fig)
    print(f"    OK  {Path(out_path).name}")

# ═══════════════════════════════════════════════════════════════════════════
# 10. FIGURE 4 – ENSEMBLE MEAN PERFORMANCE
# ═══════════════════════════════════════════════════════════════════════════

def fig_ensemble_mean(ens_raw_rows, ens_bc_rows, individual_bc_rows,
                      models, stns, smap, period_obs, period_sim, out_path):
    """
    FIX-5: Ensemble SS computed as aggregate 1 - ΣE_ens / ΣE_clim.
    FIX-4: x-axis rotation=0.
    """
    stns_str = [str(s) for s in stns]
    codes    = [smap[s] for s in stns_str]
    n_s      = len(stns)

    fig, axes = plt.subplots(3, 1, figsize=(max(16, len(models)*2+8), 14))
    fig.subplots_adjust(hspace=0.52, left=0.07, right=0.97,
                        top=0.91, bottom=0.07)

    # (a) KGE distribution boxplot
    ax = axes[0]
    kge_by_model = {}
    for m in models:
        kge_by_model[m] = [r["KGE"] for r in individual_bc_rows
                           if r["Model"]==m and not np.isnan(r["KGE"])]
    kge_by_model["Ensemble\nMean"] = [r["KGE"] for r in ens_bc_rows
                                       if not np.isnan(r["KGE"])]

    keys_plot  = models + ["Ensemble\nMean"]
    data_plot  = [kge_by_model.get(k, []) for k in keys_plot]
    colors_box = list(model_colors_global[:len(models)]) + ["#37474F"]
    display_labels = _wrap_labels(models) + ["Ensemble\nMean"]

    bp = ax.boxplot(data_plot,
                    positions=range(len(keys_plot)),
                    patch_artist=True, widths=0.6,
                    showmeans=True,
                    meanprops={"marker":"o","markerfacecolor":"white",
                               "markeredgecolor":"black","markersize":5},
                    flierprops={"marker":"d","markersize":4,"alpha":0.4})
    for patch, color in zip(bp['boxes'], colors_box):
        patch.set_facecolor(color); patch.set_alpha(0.7); patch.set_edgecolor(color)
    for median in bp['medians']:
        median.set(color="black", linewidth=2)
    for whisker in bp['whiskers']:
        whisker.set(color="#546E7A", linewidth=1, linestyle="--")
    for cap in bp['caps']:
        cap.set(color="#546E7A", linewidth=1)
    ax.axhline(0, color="grey", lw=0.8, ls="--", alpha=0.6)
    ax.set_xticks(range(len(display_labels)))
    ax.set_xticklabels(display_labels, fontsize=10, rotation=0)  # FIX-4
    ax.set_xlabel("Model", fontsize=11, labelpad=4)
    ax.set_ylabel("KGE After QDM (distribution across stations)", fontsize=11)
    ax.set_title("(a)  KGE Distribution — Individual Models vs Ensemble Mean\n"
                 "     (line=median; circle=mean; whiskers=1.5*IQR)",
                 loc="left", fontsize=12, fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # (b) Ensemble vs Best Individual per station
    ax2 = axes[1]
    x = np.arange(n_s)
    ens_kge  = []
    best_kge = []
    for stn in stns_str:
        e = next((r["KGE"] for r in ens_bc_rows if r["Station"]==stn), np.nan)
        ens_kge.append(e)
        best_val = max(
            (r["KGE"] for r in individual_bc_rows
             if r["Station"]==stn and not np.isnan(r["KGE"])),
            default=np.nan)
        best_kge.append(best_val)

    ax2.bar(x-0.22, ens_kge, width=0.40, color="#B0BEC5", edgecolor="#546E7A",
            linewidth=0.8, alpha=0.85, label="Ensemble Mean", zorder=3)
    ax2.bar(x+0.22, best_kge, width=0.40, color="#90CAF9", edgecolor="#1565C0",
            linewidth=0.8, alpha=0.85, label="Best Individual Model", zorder=3)
    ax2.axhline(0, color="grey", lw=0.8, ls="--", alpha=0.6)
    ax2.set_xticks(x)
    ax2.set_xticklabels(codes, rotation=0, ha="center", fontsize=10)  # FIX-4
    ax2.set_xlabel("Station Code", fontsize=11, labelpad=4)
    ax2.set_ylabel("KGE After QDM", fontsize=11)
    ax2.set_title("(b)  Ensemble Mean vs Best Individual Model — Per Station",
                  loc="left", fontsize=12, fontweight="bold")
    ax2.legend(fontsize=10, frameon=True, edgecolor="#B0BEC5", loc="lower right")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    # (c) Skill Score – FIX-5: aggregate formulation for Ensemble
    ax3 = axes[2]
    keys   = models + ["Ensemble\nMean"]
    labels = _wrap_labels(models) + ["Ensemble\nMean"]

    ss_by_model = {}
    for m in models:
        # Per-model: mean of per-station SS (acceptable for individual models)
        vals = [r.get("SS", np.nan) for r in individual_bc_rows if r["Model"]==m]
        ss_by_model[m] = float(np.nanmean(vals)) if vals else np.nan

    # FIX-5: Ensemble SS must be taken from ens_bc_rows which was computed
    # using the correct aggregate formula in main()
    ss_ens = np.nanmean([r.get("SS", np.nan) for r in ens_bc_rows])
    ss_by_model["Ensemble\nMean"] = ss_ens

    values = [ss_by_model.get(k, np.nan) for k in keys]
    x3     = np.arange(len(keys))
    colors3 = list(model_colors_global[:len(models)]) + ["#546E7A"]

    bars = ax3.bar(x3, values, color=colors3, alpha=0.85,
                   edgecolor="white", linewidth=0.6, zorder=3)
    ax3.axhline(0, color="grey", lw=0.8, ls="--", alpha=0.6)
    for bar in bars:
        v = bar.get_height()
        if not np.isnan(v):
            ax3.text(bar.get_x()+bar.get_width()/2, v+0.005,
                     f"{v:.3f}", ha="center", va="bottom",
                     fontsize=9, fontweight="bold")
    ax3.set_xticks(x3)
    ax3.set_xticklabels(labels, fontsize=10, rotation=0)  # FIX-4
    ax3.set_xlabel("Model", fontsize=11, labelpad=4)
    ax3.set_ylabel("Skill Score (SS)\nvs Climatological Mean", fontsize=11)
    ax3.set_title("(c)  Skill Score After QDM — Individual vs Ensemble Mean\n"
                  "     SS = 1 - SUM(E_model)/SUM(E_clim)  [aggregate; positive = better than climatology]",
                  loc="left", fontsize=12, fontweight="bold")
    ax3.spines["top"].set_visible(False)
    ax3.spines["right"].set_visible(False)

    fig.suptitle(
        "Ensemble Mean vs Individual Model Performance After QDM\n"
        f"Obs: {period_obs}  |  Sim: {period_sim}",
        fontsize=13, fontweight="bold")

    plt.savefig(out_path, dpi=600)   # FIX-2
    plt.close(fig)
    print(f"    OK  {Path(out_path).name}")

# ═══════════════════════════════════════════════════════════════════════════
# 11. FIGURE 5 – CONSISTENCY MAP
# ═══════════════════════════════════════════════════════════════════════════

def fig_consistency(bc_rows, raw_rows, models, stns, smap,
                    period_obs, out_path):
    """
    FIX-4: x-axis rotation=0, wider figure.
    """
    stns_str = [str(s) for s in stns]
    codes    = [smap[s] for s in stns_str]
    n_m, n_s = len(models), len(stns)

    rank_mat = np.full((n_m, n_s), np.nan)
    rpi_mat  = np.full((n_m, n_s), np.nan)
    for si, stn in enumerate(stns_str):
        stn_rows = [(m, next((r["KGE"] for r in bc_rows
                              if r["Model"]==m and r["Station"]==stn), np.nan))
                    for m in models]
        kges = np.array([v for _,v in stn_rows], dtype=float)
        valid = ~np.isnan(kges)
        if valid.sum() > 0:
            ranks = np.full(n_m, np.nan)
            sorted_idx = np.argsort(-kges[valid])
            valid_idx  = np.where(valid)[0]
            for ri2, idx in enumerate(sorted_idx):
                ranks[valid_idx[idx]] = ri2+1
            rank_mat[:, si] = ranks

        rmse_vals = np.array([next((r["RMSE"] for r in bc_rows
                                     if r["Model"]==m and r["Station"]==stn),
                                    np.nan) for m in models], dtype=float)
        e_ref = np.nanmedian(rmse_vals)
        if e_ref and not np.isnan(e_ref):
            for mi in range(n_m):
                if not np.isnan(rmse_vals[mi]):
                    rpi_mat[mi,si] = (rmse_vals[mi]-e_ref)/e_ref

    # FIX-4: Wider figure
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(max(18, n_m*2.5+8), 7))
    fig.subplots_adjust(left=0.08, right=0.95, top=0.87,
                        bottom=0.18, wspace=0.38)

    model_labels = _wrap_labels(models)

    # Panel (a)
    rank_max = n_m
    cmap_rank = plt.cm.get_cmap("RdYlGn_r", rank_max)
    im_a = axA.imshow(rank_mat, cmap=cmap_rank,
                      vmin=0.5, vmax=rank_max+0.5,
                      aspect="auto", interpolation="nearest")
    for mi in range(n_m):
        for si in range(n_s):
            v = rank_mat[mi, si]
            if not np.isnan(v):
                tc = "white" if v == 1 or v == rank_max else "black"
                axA.text(si, mi, f"{int(v)}", ha="center", va="center",
                         fontsize=10, fontweight="bold", color=tc)
    axA.set_xticks(range(n_s))
    axA.set_xticklabels(codes, rotation=0, ha="center", fontsize=10)  # FIX-4
    axA.set_yticks(range(n_m))
    axA.set_yticklabels(model_labels, fontsize=10)
    axA.set_xlabel("Station Code", fontsize=11, labelpad=4)
    axA.set_ylabel("Model", fontsize=11)
    axA.set_title("(a)  Model Rank per Station After QDM\n"
                  "     (1=best; green=good; red=worst)",
                  loc="left", fontsize=12, fontweight="bold", pad=5)
    cb_a = plt.colorbar(im_a, ax=axA, orientation="horizontal",
                         pad=0.22, fraction=0.06, shrink=0.8)
    cb_a.set_label("Rank (1=best)", fontsize=10)

    # Panel (b)
    abs_rpi_v = np.abs(rpi_mat[~np.isnan(rpi_mat)])
    abs_rpi = float(np.max(abs_rpi_v)) if len(abs_rpi_v) else 1.0
    im_b = axB.imshow(rpi_mat, cmap="RdYlGn_r",
                      vmin=-abs_rpi, vmax=abs_rpi,
                      aspect="auto", interpolation="nearest")
    for mi in range(n_m):
        for si in range(n_s):
            v = rpi_mat[mi, si]
            if not np.isnan(v):
                tc = "white" if abs(v) > abs_rpi*0.65 else "black"
                axB.text(si, mi, f"{v:+.2f}", ha="center", va="center",
                         fontsize=9, fontweight="bold", color=tc)
    axB.set_xticks(range(n_s))
    axB.set_xticklabels(codes, rotation=0, ha="center", fontsize=10)  # FIX-4
    axB.set_yticks(range(n_m))
    axB.set_yticklabels(model_labels, fontsize=10)
    axB.set_xlabel("Station Code", fontsize=11, labelpad=4)
    axB.set_ylabel("Model", fontsize=11)
    axB.set_title("(b)  Relative Performance Index (RPI) After QDM\n"
                  "     RPI = (RMSE_m - RMSE_ref)/RMSE_ref  (negative = better than median)",
                  loc="left", fontsize=12, fontweight="bold", pad=5)
    cb_b = plt.colorbar(im_b, ax=axB, orientation="horizontal",
                         pad=0.22, fraction=0.06, shrink=0.8)
    cb_b.set_label("RPI (negative = better)", fontsize=10)

    fig.suptitle(
        "Model Consistency Map — Rank & Relative Performance Index\n"
        f"After QDM Bias Correction  |  All Stations  |  Obs: {period_obs}",
        fontsize=13, fontweight="bold")

    plt.savefig(out_path, dpi=600)   # FIX-2
    plt.close(fig)
    print(f"    OK  {Path(out_path).name}")

# ═══════════════════════════════════════════════════════════════════════════
# 12. FIGURE 6 – SEASONAL (WET SEASON) ANALYSIS  [FIX-7: NEW]
# ═══════════════════════════════════════════════════════════════════════════

def fig_seasonal_analysis(bc_rows_seasonal, raw_rows_seasonal,
                           models, stns, smap, model_colors,
                           period_obs, period_sim, out_path):
    """
    FIX-7: Wet season (May–Oct) performance comparison.
    3-panel figure showing KGE, NSE, and RMSE for Raw vs QDM in wet season.
    """
    stns_str = [str(s) for s in stns]
    codes    = [smap[s] for s in stns_str]
    n_m, n_s = len(models), len(stns)

    metrics_show = ["KGE", "NSE", "RMSE"]
    fig, axes = plt.subplots(len(metrics_show), 1,
                             figsize=(max(16, n_m*2.5+8), 5*len(metrics_show)))
    fig.subplots_adjust(hspace=0.55, left=0.08, right=0.97,
                        top=0.91, bottom=0.07)

    for pi, met in enumerate(metrics_show):
        ax = axes[pi]
        x  = np.arange(n_m)
        bar_w = 0.38

        raw_means = []
        bc_means  = []
        for m in models:
            rv = [r[met] for r in raw_rows_seasonal
                  if r["Model"]==m and not np.isnan(r[met])]
            bv = [r[met] for r in bc_rows_seasonal
                  if r["Model"]==m and not np.isnan(r[met])]
            raw_means.append(float(np.mean(rv)) if rv else np.nan)
            bc_means.append(float(np.mean(bv)) if bv else np.nan)

        b1 = ax.bar(x-bar_w/2, raw_means, width=bar_w,
                    color="#EF9A9A", edgecolor="#C62828", alpha=0.82,
                    label="Raw CMIP6", zorder=3)
        b2 = ax.bar(x+bar_w/2, bc_means, width=bar_w,
                    color="#90CAF9", edgecolor="#1565C0", alpha=0.82,
                    label="Bias-Corrected (QDM)", zorder=3)

        for bar, col in zip(b2, model_colors):
            bar.set_facecolor(mcolors.to_rgba(col, 0.70))
            bar.set_edgecolor(col)

        for b, vals in [(b1, raw_means), (b2, bc_means)]:
            for bar, v in zip(b, vals):
                if not np.isnan(v):
                    ax.text(bar.get_x()+bar.get_width()/2,
                            v + (abs(v)*0.02 + 0.01) * np.sign(v),
                            f"{v:.3f}", ha="center", va="bottom",
                            fontsize=8.5, fontweight="bold")

        if met in LOWER_BETTER:
            ax.axhline(0, color="grey", lw=0.8, ls="--", alpha=0.6)
        else:
            ax.axhline(0, color="grey", lw=0.8, ls="--", alpha=0.4)
            ax.axhline(1, color="#1B5E20", lw=0.8, ls=":", alpha=0.5)

        ax.set_xticks(x)
        ax.set_xticklabels(_wrap_labels(models), rotation=0,
                           ha="center", fontsize=10)  # FIX-4
        ax.set_xlabel("CMIP6 Model", fontsize=11, labelpad=4)
        ax.set_ylabel(f"{met} (Mean across stations)", fontsize=11)
        ax.set_title(f"({chr(97+pi)})  Wet Season {met} — Raw vs QDM\n"
                     f"     May–October  |  Obs: {period_obs}",
                     loc="left", fontsize=12, fontweight="bold", pad=4)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        if pi == 0:
            ax.legend(fontsize=10, frameon=True, edgecolor="#B0BEC5",
                      loc="lower right")

    fig.suptitle(
        "Wet Season Performance Analysis (May-October)\n"
        f"Research Gap: Seasonal Model Skill After QDM  |  Obs: {period_obs}",
        fontsize=13, fontweight="bold")

    plt.savefig(out_path, dpi=600)   # FIX-2
    plt.close(fig)
    print(f"    OK  {Path(out_path).name}")

# ═══════════════════════════════════════════════════════════════════════════
# 13. EXCEL OUTPUT
# ═══════════════════════════════════════════════════════════════════════════

def write_excel(wb, raw_rows, bc_rows, ens_raw_rows, ens_bc_rows,
                rank_raw, rank_bc,
                raw_rows_seasonal, bc_rows_seasonal,
                models, stns, smap,
                period_obs, period_sim, imp_rows):

    stns_str = [str(s) for s in stns]
    codes    = [smap[s] for s in stns_str]

    # ── Sheet 1: Research Gap Context ─────────────────────────────────
    ws = wb.create_sheet("Research Gap Context")
    ws.sheet_view.showGridLines = False
    mxsc(ws,1,1,4,
         "Research Gap: Which CMIP6 Model Performs Best After QDM Bias Correction?",
         bold=True,fc="FFFFFF",bg=XC["title"],sz=13,align="left")
    ws.row_dimensions[1].height=26
    gaps=[
        ("Gap 1","Model selection before vs after BC",
         "Most studies select GCMs before bias correction using ensemble mean or "
         "simple historical performance. This ignores that QDM can differentially "
         "improve models depending on their original bias structure."),
        ("Gap 2","No systematic evaluation post-QDM",
         "No standardised framework exists to assess whether model rankings are "
         "preserved after bias correction, or whether QDM changes the relative "
         "performance order of CMIP6 models."),
        ("Gap 3","Ensemble mean assumption",
         "Multi-model ensemble mean is often used as the best estimate, "
         "but it may not outperform the best individual model after correction."),
        ("Gap 4","Seasonal performance gap",
         "FIX-7: Wet season (May-Oct) skill of corrected models has rarely been "
         "evaluated systematically; seasonal bias can differ from annual statistics."),
        ("RQ1","Which model ranks highest after QDM?",
         "Metric: Weighted Composite Score (KGE=0.30, NSE=0.25, RMSE=0.15, ...)."),
        ("RQ2","Does model ranking change after QDM?",
         "Metric: Rank correlation between Pre-QDM and Post-QDM rankings."),
        ("RQ3","Does ensemble mean outperform best individual model?",
         "Metric: Ensemble mean KGE vs best individual KGE per station."),
        ("RQ4","Is there a consistent best model across all stations?",
         "Metric: Win count, Rank consistency matrix (Fig 5)."),
        ("RQ5","Which model performs best in wet season after QDM?",
         "FIX-7: Metric: KGE/NSE/RMSE for May-Oct subset after QDM."),
    ]
    alt=[PatternFill("solid",fgColor="E3F2FD"),PatternFill("solid",fgColor="FFFFFF")]
    for ri,(k,t,d) in enumerate(gaps,3):
        fl=alt[ri%2]
        for ci,v in enumerate([k,t,d],1):
            cell=xsc(ws,ri,ci,v,bold=(ci<=2),sz=9.5,align="left",border=tb())
            cell.fill=fl
            if ci==3: cell.alignment=Alignment(horizontal="left",
                                                vertical="top",wrap_text=True)
        ws.row_dimensions[ri].height=56
    for ci,w in enumerate([10,32,68],1): cw(ws,ci,w)

    # ── Sheet 2 & 3: Performance ──────────────────────────────────────
    def _perf_sheet(ws_name, row_list, label):
        ws2 = wb.create_sheet(ws_name)
        ws2.sheet_view.showGridLines = False
        ws2.freeze_panes = "E4"
        nc = 4+len(METRICS_LIST)
        mxsc(ws2,1,1,nc,
             f"Model Performance Metrics — {label}",
             bold=True,fc="FFFFFF",bg=XC["title"],sz=12,align="left")
        ws2.row_dimensions[1].height=22
        hdr=["Model","Station","Code","Scale"]+METRICS_LIST
        for ci,h in enumerate(hdr,1):
            xsc(ws2,3,ci,h,bold=True,fc="FFFFFF",bg=XC["hdr"],
                border=tb(),sz=9,wrap=True)
        ws2.row_dimensions[3].height=36
        best_set=set()
        stns_u=sorted(set(r["Station"] for r in row_list))
        for stn in stns_u:
            sr=[(i,r) for i,r in enumerate(row_list) if r["Station"]==stn]
            for m_k in METRICS_LIST:
                vals=[(i,r[m_k]) for i,r in sr
                      if not(isinstance(r[m_k],float) and np.isnan(r[m_k]))]
                if not vals: continue
                bi=(min(vals,key=lambda x:abs(x[1]))[0] if m_k in LOWER_BETTER
                    else max(vals,key=lambda x:x[1])[0])
                best_set.add((bi+4, hdr.index(m_k)+1))

        prev=None
        for ri,row in enumerate(row_list,4):
            stn=row.get("Station",""); mod=row.get("Model","")
            bg=XC["alt"] if ri%2==0 else XC["white"]
            for ci,key in enumerate(hdr,1):
                if key=="Code": val=smap.get(str(stn),"--")
                else: val=row.get(key,"")
                if isinstance(val,float) and np.isnan(val): val="--"
                elif isinstance(val,float): val=round(val,4)
                is_best=(ri,ci) in best_set
                cell=xsc(ws2,ri,ci,
                         f"* {val}" if is_best and val!="--" else val,
                         bg=XC["best"] if is_best else bg,
                         border=tb(),sz=9,
                         align="left" if ci<=4 else "right")
                if ci==1:
                    cell.font=Font(bold=True,name="Calibri",size=9,color="1A1A1A")
                if is_best:
                    cell.font=Font(bold=True,color=XC["best_f"],
                                   name="Calibri",size=9)
            ws2.row_dimensions[ri].height=15
            prev=stn
        widths=[14,10,6,8]+[11]*len(METRICS_LIST)
        for ci,w in enumerate(widths,1): cw(ws2,ci,w)

    _perf_sheet("Performance (Raw)",    raw_rows, "Raw CMIP6")
    _perf_sheet("Performance (QDM BC)", bc_rows,  "Bias-Corrected (QDM)")

    # ── Sheet 4: Seasonal Performance ──── FIX-7 ──────────────────────
    def _seasonal_sheet(ws_name, raw_list, bc_list, label):
        ws_s = wb.create_sheet(ws_name)
        ws_s.sheet_view.showGridLines = False
        mxsc(ws_s,1,1,4+len(METRICS_LIST),
             f"Wet Season (May-October) Performance — {label}",
             bold=True,fc="FFFFFF",bg=XC["title"],sz=12,align="left")
        ws_s.row_dimensions[1].height=22
        mxsc(ws_s,2,1,4+len(METRICS_LIST),
             "Seasonal analysis: monsoon wet season (May 1 - Oct 31) precipitation only.",
             italic=True,fc="FFFFFF",bg=XC["sub"],sz=8.5)
        ws_s.row_dimensions[2].height=14
        hdr=["Dataset","Model","Station","Code"]+METRICS_LIST
        for ci,h in enumerate(hdr,1):
            xsc(ws_s,3,ci,h,bold=True,fc="FFFFFF",bg=XC["hdr"],
                border=tb(),sz=9,wrap=True)
        ws_s.row_dimensions[3].height=30
        all_rows = [dict(r, Dataset="Raw") for r in raw_list] + \
                   [dict(r, Dataset="QDM") for r in bc_list]
        for ri, row in enumerate(all_rows, 4):
            bg = XC["alt"] if ri%2==0 else XC["white"]
            for ci, key in enumerate(hdr, 1):
                if key == "Code":
                    val = smap.get(str(row.get("Station","")), "--")
                else:
                    val = row.get(key, "")
                if isinstance(val, float) and np.isnan(val): val = "--"
                elif isinstance(val, float): val = round(val, 4)
                xsc(ws_s, ri, ci, val, bg=bg, border=tb(), sz=9,
                    align="left" if ci <= 4 else "right")
            ws_s.row_dimensions[ri].height = 15
        widths = [8,14,10,6] + [11]*len(METRICS_LIST)
        for ci, w in enumerate(widths, 1): cw(ws_s, ci, w)

    _seasonal_sheet("Performance (Seasonal)",
                    raw_rows_seasonal, bc_rows_seasonal,
                    "Wet Season May-Oct")

    # ── Sheet 5: Model Ranking ─────────────────────────────────────────
    ws5 = wb.create_sheet("Model Ranking")
    ws5.sheet_view.showGridLines = False
    mxsc(ws5,1,1,len(RANK_METRICS)+4,
         "Model Ranking — Weighted Composite Score Before and After QDM Bias Correction",
         bold=True,fc="FFFFFF",bg=XC["title"],sz=12,align="left")
    ws5.row_dimensions[1].height=22
    mxsc(ws5,2,1,len(RANK_METRICS)+4,
         "Weighted Composite Score: KGE(0.30), NSE(0.25), RMSE(0.15), r(0.10), "
         "d(0.10), Pbias(0.05), RPI(0.05). 0=worst, 1=best.",
         italic=True,fc="FFFFFF",bg=XC["sub"],sz=8.5)
    ws5.row_dimensions[2].height=14

    hdr5=["Rank (Post-QDM)","Model","Rank (Pre-QDM)"]+RANK_METRICS+["Composite\nScore (QDM)"]
    for ci,h in enumerate(hdr5,1):
        xsc(ws5,4,ci,h,bold=True,fc="FFFFFF",bg=XC["hdr"],border=tb(),sz=9,wrap=True)
    ws5.row_dimensions[4].height=36

    medal={1:XC["rank1"],2:XC["rank2"],3:XC["rank3"]}
    rank_label={1:"#1 Best",2:"#2",3:"#3"}  # FIX-3: no emoji
    for ri,(model,row) in enumerate(rank_bc.iterrows(),5):
        rnk_bc  = int(row["Rank"])
        rnk_raw = int(rank_raw.loc[model,"Rank"]) if model in rank_raw.index else "--"
        rbg = medal.get(rnk_bc, XC["white"])
        xsc(ws5,ri,1,rank_label.get(rnk_bc,f"#{rnk_bc}"),
            bg=rbg,bold=True,border=tb(),sz=10)
        xsc(ws5,ri,2,model,bg=rbg,bold=True,border=tb(),sz=10,align="left")
        xsc(ws5,ri,3,f"#{rnk_raw}",bg=rbg,border=tb(),sz=10)
        for ci,m in enumerate(RANK_METRICS,4):
            v=row.get(m,np.nan)
            xsc(ws5,ri,ci,round(float(v),4) if not np.isnan(float(v)) else "--",
                bg=rbg,border=tb(),sz=10)
        cs=row.get("Composite Score",np.nan)
        xsc(ws5,ri,len(hdr5),
            round(float(cs),4) if not np.isnan(float(cs)) else "--",
            bg=rbg,bold=True,border=tb(),sz=10)
        ws5.row_dimensions[ri].height=18
    widths=[14,16,12]+[11]*len(RANK_METRICS)+[13]
    for ci,w in enumerate(widths,1): cw(ws5,ci,w)

    # ── Sheet 6: Improvement Summary ──────────────────────────────────
    ws6 = wb.create_sheet("Improvement Summary")
    ws6.sheet_view.showGridLines = False
    mxsc(ws6,1,1,8,
         "Overall Performance Improvement — QDM vs Raw CMIP6 (All Models, All Stations)",
         bold=True,fc="FFFFFF",bg=XC["title"],sz=12,align="left")
    ws6.row_dimensions[1].height=22
    hdr6=["Metric","Raw Avg","QDM Avg","Delta Abs","% Improvement",
          "Direction","Best Model (QDM)","Best Station"]
    for ci,h in enumerate(hdr6,1):
        xsc(ws6,3,ci,h,bold=True,fc="FFFFFF",bg=XC["hdr"],border=tb(),sz=10,wrap=True)
    ws6.row_dimensions[3].height=30
    for ri,imp in enumerate(imp_rows,4):
        d=imp.get("Direction","")
        bg=XC["improve"] if d=="Improved" else XC["degrade"]
        for ci,k in enumerate(hdr6,1):
            val=imp.get(k,"")
            if isinstance(val,float) and np.isnan(val): val="--"
            elif isinstance(val,float): val=round(val,3)
            cell=xsc(ws6,ri,ci,val,bg=bg if ci>=4 else XC["white"],
                     border=tb(),sz=10)
            if k=="% Improvement" and isinstance(val,(int,float)):
                cell.value=f"{val:+.1f}%"
        ws6.row_dimensions[ri].height=18
    for ci,w in enumerate([14,11,11,11,14,12,18,12],1): cw(ws6,ci,w)

    # ── Sheet 7: Methods & References ─────────────────────────────────
    ws7 = wb.create_sheet("Methods & References")
    ws7.sheet_view.showGridLines = False
    mxsc(ws7,1,1,3,
         "Analytical Methods & References — Model Selection After Bias Correction",
         bold=True,fc="FFFFFF",bg=XC["title"],sz=13)
    ws7.row_dimensions[1].height=26
    refs=[
        ("KGE","Kling-Gupta Efficiency",
         "Gupta et al. (2009) J. Hydrol. 377:80-91. "
         "KGE=1-sqrt[(r-1)^2+(alpha-1)^2+(beta-1)^2]. Perfect: 1."),
        ("NSE","Nash-Sutcliffe Efficiency",
         "Nash & Sutcliffe (1970) J. Hydrol. 10:282-290. Perfect: 1."),
        ("RPI","Relative Performance Index",
         "Gleckler et al. (2008) J. Geophys. Res. 113:D06104. "
         "RPI=(E_m-E_ref)/E_ref where E_ref=median RMSE. Negative=better than median."),
        ("SS","Skill Score (Aggregate)",
         "Reichler & Kim (2008) Bull. AMS 89:303-311. "
         "SS=1-SUM(E_model)/SUM(E_clim). Positive=better than climatology. "
         "FIX-5: Ensemble SS uses aggregate sum, not mean of station SS."),
        ("Composite","Weighted Composite Score",
         "FIX-6: Weighted multi-metric score (0=worst, 1=best). "
         "Weights: KGE=0.30, NSE=0.25, RMSE=0.15, r=0.10, d=0.10, "
         "Pbias(%)=0.05, RPI=0.05. Based on Knutti et al. (2017)."),
        ("Seasonal","Wet Season Analysis",
         "FIX-7: May-October (monsoon) subset extracted from daily time series. "
         "Seasonal totals computed with min_count=0.6 completeness threshold."),
        ("QDM","Quantile Delta Mapping",
         "Cannon et al. (2015) J. Climate 28:6938-6959."),
        ("CMIP6","CMIP6 Framework",
         "Eyring et al. (2016) Geosci. Model Dev. 9:1937-1958."),
        ("Selection","Model Selection Rationale",
         "Knutti et al. (2017) Nat. Clim. Chang. 7:246-251. "
         "Models should be selected based on process fidelity, not just "
         "historical performance."),
    ]
    alt=[PatternFill("solid",fgColor="DEEAF1"),PatternFill("solid",fgColor="FFFFFF")]
    for ri,(a,b,d) in enumerate(refs,3):
        fl=alt[ri%2]
        for ci,v in enumerate([a,b,d],1):
            cell=xsc(ws7,ri,ci,v,bold=(ci<=2),sz=9,align="left",border=tb())
            cell.fill=fl
            if ci==3: cell.alignment=Alignment(horizontal="left",vertical="top",
                                                wrap_text=True)
        ws7.row_dimensions[ri].height=52
    for ci,w in enumerate([14,26,68],1): cw(ws7,ci,w)

# ═══════════════════════════════════════════════════════════════════════════
# 14. COMPUTE IMPROVEMENT ROWS
# ═══════════════════════════════════════════════════════════════════════════

def compute_improvement(raw_rows, bc_rows, models, stns_str):
    out = []
    for met in ["KGE","NSE","RMSE","r","Pbias (%)"]:
        rv=[r[met] for r in raw_rows if not(isinstance(r[met],float) and np.isnan(r[met]))]
        bv=[r[met] for r in bc_rows  if not(isinstance(r[met],float) and np.isnan(r[met]))]
        if not rv or not bv: continue
        rm,bm=float(np.mean(rv)),float(np.mean(bv))
        abs_i=(abs(rm)-abs(bm)) if met in LOWER_BETTER else (bm-rm)
        rel_i=abs_i/abs(rm)*100 if rm else np.nan
        direction="Improved" if abs_i>0 else "Degraded"

        best_m, best_imp="--",-np.inf
        for m in models:
            mr=[r[met] for r in raw_rows if r["Model"]==m and
                not(isinstance(r[met],float) and np.isnan(r[met]))]
            mb=[r[met] for r in bc_rows  if r["Model"]==m and
                not(isinstance(r[met],float) and np.isnan(r[met]))]
            if not mr or not mb: continue
            imp=(abs(float(np.mean(mr)))-abs(float(np.mean(mb)))) if met in LOWER_BETTER \
                else (float(np.mean(mb))-float(np.mean(mr)))
            if imp > best_imp:
                best_imp,best_m=imp,m

        best_s, best_si="--",-np.inf
        for stn in stns_str:
            sr=[r[met] for r in raw_rows if r["Station"]==stn and
                not(isinstance(r[met],float) and np.isnan(r[met]))]
            sb=[r[met] for r in bc_rows  if r["Station"]==stn and
                not(isinstance(r[met],float) and np.isnan(r[met]))]
            if not sr or not sb: continue
            imp=(abs(float(np.mean(sr)))-abs(float(np.mean(sb)))) if met in LOWER_BETTER \
                else (float(np.mean(sb))-float(np.mean(sr)))
            if imp > best_si:
                best_si,best_s=imp,stn

        out.append({"Metric":met,"Raw Avg":round(rm,4),"QDM Avg":round(bm,4),
                    "Delta Abs":round(abs_i,4),
                    "% Improvement":round(rel_i,2) if not np.isnan(rel_i) else np.nan,
                    "Direction":direction,
                    "Best Model (QDM)":best_m,"Best Station":best_s})
    return out

# ═══════════════════════════════════════════════════════════════════════════
# 15. MAIN
# ═══════════════════════════════════════════════════════════════════════════
model_colors_global = MODEL_PALETTE

def main():
    sep = "=" * 72
    print(sep)
    print("  Research Gap: Model Selection After Bias Correction")
    print("  'Which CMIP6 Model Performs Best After QDM?'")
    print("  Multi-Model | Multi-Station | Daily + Monthly + Seasonal")
    print("  Standard: Q1-Q3 journal publication")
    print(sep)

    work_dir = (sys.argv[1].strip('"').strip("'")
                if len(sys.argv) > 1 else
                (str(Path(os.path.abspath(__file__)).parent)
                 if "__file__" in dir() else os.getcwd()))
    print(f"  Folder : {work_dir}")

    obs_path, raw_models, bc_models = discover_files(work_dir)
    if obs_path is None:
        sys.exit("  X  Observed file not found")
    print(f"  Observed : {Path(obs_path).name}")
    print(f"  Raw models ({len(raw_models)}): {list(raw_models.keys())}")
    print(f"  BC  models ({len(bc_models)}): {list(bc_models.keys())}")

    all_models = sorted(set(raw_models.keys()) | set(bc_models.keys()))
    model_colors = MODEL_PALETTE[:len(all_models)]
    print(f"  Models: {all_models}")
    print("-"*72)

    # ── Load Observed ───────────────────────────────────────────────────
    print("  Loading Observed ...")
    obs_d, stns = load_daily(obs_path, "Observed")
    if obs_d is None: sys.exit("  X  Failed to load Observed")
    stns_str   = [str(s) for s in stns]
    smap       = short_labels(stns)
    obs_m      = to_monthly(obs_d)
    obs_a      = to_annual(obs_d)
    obs_s      = to_seasonal_wet(obs_d)   # FIX-7: wet season obs
    period_obs = period_str(obs_d)

    # ── Load all model data ─────────────────────────────────────────────
    raw_daily = {}; raw_monthly = {}; raw_seasonal = {}
    bc_daily  = {}; bc_monthly  = {}; bc_seasonal  = {}

    print("  Loading Raw CMIP6 ...")
    for m, path in raw_models.items():
        df, _ = load_daily(path, f"Raw/{m}")
        raw_daily[m]    = df
        raw_monthly[m]  = to_monthly(df)
        raw_seasonal[m] = to_seasonal_wet(df)   # FIX-7
        print(f"    {m}: {period_str(df)}")

    print("  Loading BC/QDM ...")
    for m, path in bc_models.items():
        df, _ = load_daily(path, f"BC/{m}")
        bc_daily[m]    = df
        bc_monthly[m]  = to_monthly(df)
        bc_seasonal[m] = to_seasonal_wet(df)   # FIX-7
        print(f"    {m}: {period_str(df)}")

    period_sim = period_str(list(raw_daily.values())[0]) \
                 if raw_daily else period_str(list(bc_daily.values())[0])
    print("-"*72)

    # ── Compute metrics ─────────────────────────────────────────────────
    print("  Computing performance metrics (Daily + Monthly + Seasonal) ...")
    raw_rows_d, bc_rows_d = [], []
    raw_rows_m, bc_rows_m = [], []
    raw_rows_s, bc_rows_s = [], []   # FIX-7: seasonal rows

    for m in all_models:
        for stn in stns_str:

            # ── Daily ──────────────────────────────────────────────────
            for ds_dict, row_list, ds_label in [
                (raw_daily, raw_rows_d, "Raw"),
                (bc_daily,  bc_rows_d,  "QDM"),
            ]:
                df = ds_dict.get(m)
                if df is not None and obs_d is not None:
                    common = obs_d.index.intersection(df.index)
                    if len(common) > 0 and stn in obs_d.columns and stn in df.columns:
                        o_v = obs_d.loc[common, stn].values.astype(float)
                        s_v = df.loc[common, stn].values.astype(float)
                        mr  = compute_metrics(o_v, s_v, m, stn, "Daily", ds_label)
                        mr["SS"] = skill_score(o_v, s_v)
                    else:
                        mr = compute_metrics(np.array([]), np.array([]),
                                             m, stn, "Daily", ds_label)
                        mr["SS"] = np.nan
                else:
                    mr = compute_metrics(np.array([]), np.array([]),
                                         m, stn, "Daily", ds_label)
                    mr["SS"] = np.nan
                row_list.append(mr)

            # ── Monthly ────────────────────────────────────────────────
            for ds_dict, row_list, ds_label in [
                (raw_monthly, raw_rows_m, "Raw"),
                (bc_monthly,  bc_rows_m,  "QDM"),
            ]:
                df = ds_dict.get(m)
                if obs_m is not None and df is not None:
                    o_al, s_al = align_pair(obs_m, df)
                    if o_al is not None and stn in o_al.columns and stn in s_al.columns:
                        mr = compute_metrics(o_al[stn].values, s_al[stn].values,
                                             m, stn, "Monthly", ds_label)
                    else:
                        mr = compute_metrics(np.array([]),np.array([]),
                                             m,stn,"Monthly",ds_label)
                else:
                    mr = compute_metrics(np.array([]),np.array([]),
                                         m,stn,"Monthly",ds_label)
                row_list.append(mr)

            # ── Seasonal (Wet: May-Oct) ── FIX-7 ──────────────────────
            for ds_dict, row_list, ds_label in [
                (raw_seasonal, raw_rows_s, "Raw"),
                (bc_seasonal,  bc_rows_s,  "QDM"),
            ]:
                df = ds_dict.get(m)
                if obs_s is not None and df is not None:
                    o_al, s_al = align_pair(obs_s, df)
                    if o_al is not None and stn in o_al.columns and stn in s_al.columns:
                        mr = compute_metrics(o_al[stn].values, s_al[stn].values,
                                             m, stn, "Seasonal_Wet", ds_label)
                    else:
                        mr = compute_metrics(np.array([]),np.array([]),
                                             m,stn,"Seasonal_Wet",ds_label)
                else:
                    mr = compute_metrics(np.array([]),np.array([]),
                                         m,stn,"Seasonal_Wet",ds_label)
                row_list.append(mr)

        print(f"    OK  {m}")

    add_rpi(raw_rows_d); add_rpi(bc_rows_d)
    add_rpi(raw_rows_m); add_rpi(bc_rows_m)
    add_rpi(raw_rows_s); add_rpi(bc_rows_s)   # FIX-7

    # ── Ensemble mean ────────────────────────────────────────────────────
    print("  Computing ensemble mean ...")
    ens_raw_d = ensemble_mean_df(raw_daily)
    ens_bc_d  = ensemble_mean_df(bc_daily)

    ens_raw_rows, ens_bc_rows = [], []
    for stn in stns_str:
        for ens_df, row_list, ds_label in [
            (ens_raw_d, ens_raw_rows, "Raw"),
            (ens_bc_d,  ens_bc_rows,  "QDM"),
        ]:
            if ens_df is not None and obs_d is not None:
                common = obs_d.index.intersection(ens_df.index)
                if len(common) > 0 and stn in ens_df.columns and stn in obs_d.columns:
                    o_v = obs_d.loc[common, stn].values.astype(float)
                    s_v = ens_df.loc[common, stn].values.astype(float)
                    mr  = compute_metrics(o_v, s_v, "EnsembleMean",
                                          stn, "Daily", ds_label)
                    # Placeholder SS per station (will be overwritten by aggregate)
                    mr["SS"] = np.nan
                else:
                    mr = compute_metrics(np.array([]), np.array([]),
                                         "EnsembleMean", stn, "Daily", ds_label)
                    mr["SS"] = np.nan
            else:
                mr = compute_metrics(np.array([]), np.array([]),
                                     "EnsembleMean", stn, "Daily", ds_label)
                mr["SS"] = np.nan
            row_list.append(mr)

    # FIX-5: Aggregate Ensemble SS = 1 - ΣE_ens / ΣE_clim
    if ens_bc_d is not None:
        obs_all_list, sim_all_list = [], []
        for stn in stns_str:
            if stn not in obs_d.columns or stn not in ens_bc_d.columns:
                continue
            common = obs_d.index.intersection(ens_bc_d.index)
            if len(common) == 0:
                continue
            o = obs_d.loc[common, stn].values.astype(float)
            s = ens_bc_d.loc[common, stn].values.astype(float)
            mask = ~np.isnan(o) & ~np.isnan(s)
            if np.any(mask):
                obs_all_list.extend(o[mask])
                sim_all_list.extend(s[mask])

        if obs_all_list:
            obs_all = np.array(obs_all_list)
            sim_all = np.array(sim_all_list)
            # FIX-5: aggregate formula
            e_ens  = np.sum((sim_all - obs_all)**2)
            e_clim = np.sum((obs_all - np.mean(obs_all))**2)
            ss_ensemble = float(1.0 - e_ens / e_clim) if e_clim > 0 else np.nan
        else:
            ss_ensemble = np.nan

        for r in ens_bc_rows:
            r["SS"] = ss_ensemble

    # ── Rankings ─────────────────────────────────────────────────────────
    print("  Computing weighted composite rankings ...")
    rank_raw = composite_ranking(raw_rows_d, dataset_filter="Raw")
    rank_bc  = composite_ranking(bc_rows_d,  dataset_filter="QDM")

    print("\n  === POST-QDM RANKING (Weighted Composite) ===")
    for model, row in rank_bc.iterrows():
        print(f"  Rank {int(row['Rank']):2d}  {model:<22s}  "
              f"Score={row['Composite Score']:.4f}  "
              f"KGE={row.get('KGE',np.nan):.3f}  NSE={row.get('NSE',np.nan):.3f}")

    # ── Improvement summary ───────────────────────────────────────────────
    imp_rows = compute_improvement(raw_rows_d, bc_rows_d, all_models, stns_str)

    # ── Excel ─────────────────────────────────────────────────────────────
    base_name = Path(obs_path).stem
    out_xlsx  = Path(work_dir) / f"Output_ModelSelection_{base_name}.xlsx"
    print(f"\n  Creating Excel -> {out_xlsx.name} ...")
    wb = Workbook(); wb.remove(wb.active)
    write_excel(wb, raw_rows_d, bc_rows_d, ens_raw_rows, ens_bc_rows,
                rank_raw, rank_bc,
                raw_rows_s, bc_rows_s,
                all_models, stns, smap,
                period_obs, period_sim, imp_rows)
    wb.save(str(out_xlsx))
    print("  OK  Excel saved")

    # ── Figures ───────────────────────────────────────────────────────────
    global model_colors_global
    model_colors_global = model_colors

    print("\n  Creating figures ...")
    def op(s): return str(Path(work_dir)/f"Output_ModelSelection_{base_name}_{s}")

    fig_performance_heatmap(raw_rows_d, bc_rows_d, all_models, stns, smap,
                             period_obs, period_sim,
                             op("Fig1_PerformanceHeatmap.png"))

    fig_ranking_radar(rank_raw, rank_bc, all_models, model_colors,
                      period_obs, op("Fig2_RankingRadar.png"))

    fig_best_model_summary(bc_rows_d, raw_rows_d, all_models, stns, smap,
                            model_colors, period_obs, period_sim,
                            op("Fig3_BestModelSummary.png"))

    fig_ensemble_mean(ens_raw_rows, ens_bc_rows, bc_rows_d,
                      all_models, stns, smap,
                      period_obs, period_sim,
                      op("Fig4_EnsembleMean.png"))

    fig_consistency(bc_rows_d, raw_rows_d, all_models, stns, smap,
                    period_obs, op("Fig5_ConsistencyMap.png"))

    # FIX-7: Seasonal figure
    fig_seasonal_analysis(bc_rows_s, raw_rows_s, all_models, stns, smap,
                           model_colors, period_obs, period_sim,
                           op("Fig6_SeasonalWetSeason.png"))

    print()
    print(sep)
    print(f"  DONE — Excel 1 file  |  Figures 6 files")
    print(f"  Saved in: {work_dir}")
    print(sep)

if __name__ == "__main__":
    main()
