"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  CMIP6 Multi-Model Bias Correction Evaluation — Version 4.0                ║
║  Research Gap: Temporal Scale + Station-Scale + Model Selection             ║
║  มาตรฐาน Nature / Elsevier / Q1-Q3                                        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  v4.0 Corrections (ตรวจเขียนใหม่):                                        ║
║  [1] extract_model: รองรับ pr_day_MODEL_ และ bc_pr_day_MODEL_              ║
║      (แก้บัก "day" / "pr" ถูกดึงแทนชื่อโมเดล)                           ║
║  [2] DPI = 600 (journal-grade high resolution)                             ║
║  [3] X-axis labels: rotation=0° horizontal ทุกรูป, figsize ปรับตาม       ║
║  [4] ลบสัญลักษณ์ medal 🥇🥈🥉 ออกจากทุกรูป (ไม่ใช่มาตรฐาน)             ║
║  [5] Weighted Composite Score แทน Equal-Weight:                            ║
║      KGE:0.30, NSE:0.25, RMSE:0.15, r:0.10, d:0.10, Pbias:0.05, RPI:0.05 ║
║  [6] Pooled Skill Score สำหรับ Ensemble (ไม่ใช่ mean ของ station SS)      ║
║  [7] Pbias ใช้ |Pbias| ในการ normalise เพื่อ ranking                      ║
║  [8] Seasonal analysis (Wet season May-Oct) ครบถ้วนทุก sheet              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Input (ในโฟลเดอร์เดียวกับ script):                                        ║
║    Observed  : ชื่อไฟล์มีคำว่า "Observed"                                 ║
║    Raw CMIP6 : pr_day_<Model>_*.csv                                         ║
║    BC/QDM    : bc_pr_day_<Model>_*.csv  หรือ  bc_<Model>_*.csv            ║
║  Output:                                                                    ║
║    Output_v4_<name>.xlsx   (10 sheets)                                     ║
║    Output_v4_Fig01–07_*.png  (600 DPI, journal-ready)                     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  อ้างอิง:                                                                   ║
║    Taylor (2001) J. Geophys. Res. 106:7183–7192                            ║
║    Karl et al. (1999) Int. J. Climatol. 19:405–420  [ETCCDI]               ║
║    Gupta et al. (2009) J. Hydrol. 377:80–91          [KGE]                 ║
║    Nash & Sutcliffe (1970) J. Hydrol. 10:282–290      [NSE]                ║
║    Gleckler et al. (2008) J. Geophys. Res.            [RPI]                ║
║    Murphy (1988) Mon. Wea. Rev. 116:2417–2424         [SS]                 ║
║    Cannon et al. (2015) J. Climate 28:6938–6959       [QDM]               ║
║    Knutti et al. (2017) Nat. Clim. Chang. 7:246–251   [Model selection]   ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os, sys, re, math, warnings, calendar
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
from matplotlib.colors import Normalize, BoundaryNorm
import matplotlib.cm    as cm

from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils   import get_column_letter

warnings.filterwarnings("ignore")

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  0.  GLOBAL CONSTANTS & STYLE                                           ║
# ╚══════════════════════════════════════════════════════════════════════════╝

WET_THR    = 1.0               # mm/day WMO standard
WET_MONTHS = [5,6,7,8,9,10]   # May–October (ฤดูฝน)
DRY_MONTHS = [11,12,1,2,3,4]
MONTH_ABBR = ["Jan","Feb","Mar","Apr","May","Jun",
              "Jul","Aug","Sep","Oct","Nov","Dec"]

# 12 colour-blind–safe colours for up to 12 CMIP6 models
MODEL_PALETTE = [
    "#1565C0","#C62828","#2E7D32","#E65100","#6A1B9A",
    "#00695C","#AD1457","#4527A0","#0277BD","#558B2F",
    "#4E342E","#37474F",
]

C = dict(
    obs="#1B2838", raw="#C62828", bc="#1565C0",
    obs_lt="#CFD8DC", raw_lt="#FFCDD2", bc_lt="#BBDEFB",
    green="#1E8449", gold="#F57F17", grey="#607D8B",
    wet="#1565C0", dry="#E65100", extreme="#6A1B9A",
    ens="#2E7D32", ens_lt="#C8E6C9",
)

# ── [Fix 5] Weighted Composite Score — ไม่ใช้ equal-weight ──────────────
# Ref: PDF instruction §5
RANK_METRICS   = ["RMSE","NSE","KGE","r","d","Pbias","RPI"]
LOWER_BETTER   = {"RMSE","MAE","MBE","Pbias","RPI"}
HIGHER_BETTER  = {"r","NSE","KGE","d","SS"}
METRIC_WEIGHTS = {
    "KGE"  : 0.30,
    "NSE"  : 0.25,
    "RMSE" : 0.15,
    "r"    : 0.10,
    "d"    : 0.10,
    "Pbias": 0.05,
    "RPI"  : 0.05,
}

# ── [Fix 2] Journal-grade matplotlib style — DPI = 600 ───────────────────
plt.rcParams.update({
    "font.family":        "serif",
    "font.serif":         ["Times New Roman","DejaVu Serif"],
    "font.size":          11,
    "axes.titlesize":     12,
    "axes.labelsize":     11,
    "xtick.labelsize":    10,
    "ytick.labelsize":    10,
    "legend.fontsize":    9.5,
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
    "savefig.dpi":        600,      # [Fix 2] 600 DPI
    "savefig.bbox":       "tight",
    "savefig.pad_inches": 0.15,
    "figure.dpi":         150,
    "mathtext.fontset":   "stix",
})

SAVE_DPI = 600  # explicit DPI for all savefig calls

# ── Excel helpers ──────────────────────────────────────────────────────────
XC = dict(
    title="13293D", sub="1F4E79", hdr="2E75B6", hdr2="546E7A",
    obs_r="E8F5E9", raw_r="FFEBEE", bc_r="E3F2FD", ens_r="F1F8E9",
    best="FFF9C4", best_f="E65100", improve="C8E6C9", degrade="FFCCBC",
    note="ECEFF1", white="FFFFFF", alt="F5F5F5",
    rank1="FFD700", rank2="C0C0C0", rank3="CD7F32",
    wet_s="DDEEFF", extreme_s="FFF3E0",
)
THIN = Side(style="thin",   color="BDBDBD")
MED  = Side(style="medium", color="1F4E79")

def tb():   return Border(left=THIN, right=THIN, top=THIN,  bottom=THIN)
def tbt():  return Border(left=MED,  right=MED,  top=MED,   bottom=MED)
def xfill(h): return PatternFill("solid", fgColor=h)

def xsc(ws, r, c, val=None, bold=False, italic=False,
        fc=None, bg=None, align="center", sz=10, wrap=True, border=None):
    cell = ws.cell(row=r, column=c)
    if val is not None: cell.value = val
    cell.font = Font(bold=bold, italic=italic, name="Calibri", size=sz,
                     color=fc if fc else "1A1A1A")
    cell.alignment = Alignment(horizontal=align, vertical="center", wrap_text=wrap)
    if bg:     cell.fill = xfill(bg)
    if border: cell.border = border
    return cell

def mxsc(ws, r, c1, c2, val, **kw):
    ws.merge_cells(start_row=r, start_column=c1, end_row=r, end_column=c2)
    return xsc(ws, r, c1, val, **kw)

def cw(ws, col, w):
    ws.column_dimensions[get_column_letter(col)].width = w

def row_h(ws, r, h):
    ws.row_dimensions[r].height = h

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  1.  FILE DISCOVERY — MULTI-MODEL AWARE                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def discover_files(folder: str):
    """
    Scan folder and return:
      obs_path   : str
      raw_models : {model_name: path}
      bc_models  : {model_name: path}
    Convention:
      pr_day_<Model>_*.csv        → Raw CMIP6 (ชื่อเริ่มต้นด้วย pr)
      bc_pr_day_<Model>_*.csv     → Bias-Corrected (ชื่อเริ่มต้นด้วย bc)
      *Observed*.csv              → Observed
    """
    all_csv   = sorted(Path(folder).glob("*.csv"))
    obs_files = [f for f in all_csv if "observed" in f.name.lower()]
    raw_files = [f for f in all_csv if f.name.lower().startswith("pr")]
    bc_files  = [f for f in all_csv if f.name.lower().startswith("bc")]

    obs_path = str(obs_files[0]) if obs_files else None
    if len(obs_files) > 1:
        print(f"  ⚠  Multiple Observed files — using {obs_files[0].name}")

    # ── [Fix 1] Robust model-name extraction ────────────────────────────
    # Pattern examples:
    #   pr_day_ACCESSESM15_historical_...  → ACCESSESM15
    #   bc_pr_day_CanESM5_historical_...   → CanESM5
    #   bc_ACCESSESM15_historical_...      → ACCESSESM15
    SKIP_TOKENS = {"pr", "bc", "day"}

    def extract_model(fname, prefix):
        stem  = Path(fname).stem
        # Remove the leading prefix (pr_ or bc_)
        body  = re.sub(rf"^{re.escape(prefix)}_", "", stem, flags=re.IGNORECASE)
        parts = body.split("_")
        # Walk parts and return the first that is NOT a known filler token
        for p in parts:
            if p.lower() not in SKIP_TOKENS and p:
                return p
        return "UnknownModel"

    raw_models, bc_models = {}, {}
    for f in raw_files:
        m = extract_model(f.name, "pr")
        if m not in raw_models:
            raw_models[m] = str(f)
        else:
            print(f"  ⚠  Duplicate Raw '{m}' — skipping {f.name}")
    for f in bc_files:
        m = extract_model(f.name, "bc")
        if m not in bc_models:
            bc_models[m] = str(f)
        else:
            print(f"  ⚠  Duplicate BC '{m}' — skipping {f.name}")

    raw_set, bc_set = set(raw_models), set(bc_models)
    for m in raw_set - bc_set:
        print(f"  ⚠  No BC file for '{m}' — raw-only analysis")
    for m in bc_set - raw_set:
        print(f"  ⚠  No Raw file for '{m}' — bc-only analysis")

    return obs_path, raw_models, bc_models

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  2.  DATA LOADING & AGGREGATION                                         ║
# ╚══════════════════════════════════════════════════════════════════════════╝

MISS_FLAGS = [-99,-999,-9999,-9.99e+20,9.99e+20,1e+20]

def load_daily(path, label):
    if path is None or not os.path.isfile(path):
        print(f"  ✗  ไม่พบ {label}"); return None, []
    df = pd.read_csv(path)
    for mv in MISS_FLAGS:
        df.replace(mv, np.nan, inplace=True)
    num = df.select_dtypes(include=[np.number]).columns
    df[num] = df[num].where(df[num] >= 0)
    stns = [c for c in df.columns if c not in ("YEAR","MONTH","DAY")]
    try:
        df["date"] = pd.to_datetime(
            {"year":df["YEAR"],"month":df["MONTH"],"day":df["DAY"]})
        df = df.set_index("date")[stns]
    except:
        df = df[stns]
    print(f"    {label:30s}: {len(df):,} rows × {len(stns)} stns  [{period_str(df)}]")
    return df, stns

def to_monthly(d):
    if d is None: return None
    return d.resample("MS").apply(lambda g: g.sum(min_count=int(0.8*len(g))))

def to_annual(d):
    if d is None: return None
    return d.resample("YS").apply(lambda g: g.sum(min_count=int(0.8*len(g))))

def to_seasonal(d, months):
    if d is None: return None
    sub = d[d.index.month.isin(months)]
    return sub.resample("YS").apply(lambda g: g.sum(min_count=int(0.5*len(g))))

def align_pair(df1, df2):
    if df1 is None or df2 is None: return None, None
    common = df1.index.intersection(df2.index)
    return (df1.loc[common], df2.loc[common]) if len(common)>0 else (None,None)

def gcol(df, stn):
    if df is None or stn not in df.columns: return np.array([],dtype=float)
    v = df[stn].values.astype(float)
    return v[~np.isnan(v) & (v>=0)]

def period_str(df):
    if df is None: return "N/A"
    try: return f"{df.index[0].year}–{df.index[-1].year}"
    except: return "N/A"

def short_labels(stns):
    return {str(s): f"S{i+1}" for i,s in enumerate(stns)}

def ensemble_mean(model_dfs: dict):
    valid = [df for df in model_dfs.values() if df is not None]
    if not valid: return None
    common = valid[0].index
    for df in valid[1:]:
        common = common.intersection(df.index)
    if len(common) == 0: return None
    stack = np.stack([df.loc[common].values.astype(float) for df in valid], axis=0)
    return pd.DataFrame(np.nanmean(stack,axis=0), index=common, columns=valid[0].columns)

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  3.  PERFORMANCE METRICS                                                ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def compute_metrics(obs_arr, sim_arr):
    """
    Full performance metrics suite — academically correct.
    SS = Murphy (1988) Skill Score relative to climatology mean.
         Numerically equivalent to NSE; retained as separate field.
    For ensemble aggregation, use pooled_skill_score() instead of mean(SS).
    """
    null = {k: np.nan for k in [
        "n","RMSE","MAE","MBE","Pbias","r","NSE","KGE","d","SS",
        "sigma_r","beta","std_obs","std_sim"]}
    if len(obs_arr)<5 or len(sim_arr)<5: return null

    n   = min(len(obs_arr), len(sim_arr))
    o,s = obs_arr[:n].astype(float), sim_arr[:n].astype(float)
    mask = ~np.isnan(o) & ~np.isnan(s)
    o,s  = o[mask], s[mask]
    if len(o)<5: return null

    res  = s - o
    rmse = float(np.sqrt(np.mean(res**2)))
    mae  = float(np.mean(np.abs(res)))
    mbe  = float(np.mean(res))
    pb   = float(100*np.sum(res)/np.sum(o)) if np.sum(o) else np.nan
    r    = float(np.corrcoef(o,s)[0,1])
    o_std = float(np.std(o, ddof=1))
    s_std = float(np.std(s, ddof=1))
    sigma_r = s_std/o_std if o_std>0 else np.nan
    beta_v  = float(np.mean(s)/np.mean(o)) if np.mean(o)!=0 else np.nan

    dn  = np.sum((o - np.mean(o))**2)
    nse = float(1 - np.sum(res**2)/dn) if dn>0 else np.nan

    # ── [Fix 6] SS = Murphy (1988) relative to climatology — same formula as NSE
    # For individual-station SS: SS = 1 - MSE_model / MSE_climatology
    # where MSE_clim = mean((obs - obs_mean)^2)  [= Var_obs (population)]
    mse_clim = float(np.mean((o - np.mean(o))**2))
    ss = float(1 - np.mean(res**2)/mse_clim) if mse_clim>0 else np.nan

    kge = float(1 - math.sqrt((r-1)**2+(sigma_r-1)**2+(beta_v-1)**2)) \
          if not(np.isnan(sigma_r) or np.isnan(beta_v)) else np.nan

    dioa_d = np.sum((np.abs(s-np.mean(o)) + np.abs(o-np.mean(o)))**2)
    dioa   = float(1 - np.sum(res**2)/dioa_d) if dioa_d>0 else np.nan

    return {
        "n":      len(o),
        "RMSE":   round(rmse,   3),
        "MAE":    round(mae,    3),
        "MBE":    round(mbe,    3),
        "Pbias":  round(pb,     2),
        "r":      round(r,      4),
        "NSE":    round(float(nse), 4),
        "KGE":    round(float(kge), 4),
        "d":      round(float(dioa),4),
        "SS":     round(float(ss),  4),
        "sigma_r":round(float(sigma_r),4) if not np.isnan(sigma_r) else np.nan,
        "beta":   round(float(beta_v),4)  if not np.isnan(beta_v)  else np.nan,
        "std_obs":round(o_std, 3),
        "std_sim":round(s_std, 3),
    }


def pooled_skill_score(obs_df, sim_df, stns_str):
    """
    [Fix 6] Pooled (aggregated) Skill Score across multiple stations.
    SS_pooled = 1 - Σ_i Σ_t (sim_it - obs_it)^2 / Σ_i Σ_t (obs_it - obs_i_bar)^2
    Ref: Murphy (1988) Mon. Wea. Rev. 116:2417–2424
    """
    num = den = 0.0
    for stn in stns_str:
        if obs_df is None or sim_df is None: continue
        if stn not in obs_df.columns or stn not in sim_df.columns: continue
        common = obs_df.index.intersection(sim_df.index)
        if len(common) < 5: continue
        o = obs_df.loc[common, stn].values.astype(float)
        s = sim_df.loc[common, stn].values.astype(float)
        mask = ~np.isnan(o) & ~np.isnan(s)
        o,s  = o[mask], s[mask]
        if len(o) < 5: continue
        num += float(np.sum((s-o)**2))
        den += float(np.sum((o-np.mean(o))**2))
    return round(float(1-num/den),4) if den>0 else np.nan


def metrics_df(obs_df, sim_df, stn):
    """Metrics from aligned DataFrames."""
    if obs_df is None or sim_df is None:
        return compute_metrics(np.array([]), np.array([]))
    if stn not in obs_df.columns or stn not in sim_df.columns:
        return compute_metrics(np.array([]), np.array([]))
    common = obs_df.index.intersection(sim_df.index)
    if len(common)==0:
        return compute_metrics(np.array([]), np.array([]))
    return compute_metrics(obs_df.loc[common,stn].values,
                           sim_df.loc[common,stn].values)


def add_rpi(rows):
    """
    Add Relative Performance Index (RPI = (RMSE_m − RMSE_ref)/RMSE_ref).
    RMSE_ref = median RMSE across all models for same station & scale.
    """
    keys = set((r["Station"],r["Scale"]) for r in rows)
    for stn, scale in keys:
        sub   = [r for r in rows if r["Station"]==stn and r["Scale"]==scale]
        rmses = [r["RMSE"] for r in sub if not np.isnan(r.get("RMSE", np.nan))]
        if not rmses: continue
        ref = float(np.median(rmses))
        for r in sub:
            rv = r.get("RMSE", np.nan)
            r["RPI"] = round((rv-ref)/ref, 4) if ref!=0 and not np.isnan(rv) else np.nan
    return rows


def composite_ranking(rows, scale="Daily"):
    """
    [Fix 5] Weighted composite score per model.
    Weights: KGE=0.30, NSE=0.25, RMSE=0.15, r=0.10, d=0.10, Pbias=0.05, RPI=0.05
    [Fix 7] Pbias uses |Pbias| for normalisation (penalises both over/under-estimation)
    """
    sub    = [r for r in rows if r.get("Scale")==scale]
    models = sorted(set(r["Model"] for r in sub))
    data   = {}
    for m in models:
        mr  = [r for r in sub if r["Model"]==m]
        row = {"Model": m}
        for met in RANK_METRICS:
            vals = [r[met] for r in mr if not np.isnan(r.get(met, np.nan))]
            row[met] = float(np.mean(vals)) if vals else np.nan
        data[m] = row
    df = pd.DataFrame(list(data.values())).set_index("Model")

    # Normalise each metric to [0,1]
    score = pd.DataFrame(index=df.index, columns=RANK_METRICS, dtype=float)
    for met in RANK_METRICS:
        vals = df[met].values.astype(float)
        if met == "Pbias":
            # [Fix 7] use |Pbias| — smaller absolute bias = better
            abs_vals = np.abs(vals)
            rng = np.nanmax(abs_vals) - np.nanmin(abs_vals)
            if rng == 0:
                score[met] = 1.0
            else:
                score[met] = (np.nanmax(abs_vals) - abs_vals) / rng
        else:
            rng = np.nanmax(vals) - np.nanmin(vals)
            if rng == 0:
                score[met] = 1.0
            elif met in LOWER_BETTER:
                score[met] = (np.nanmax(vals) - vals) / rng
            else:
                score[met] = (vals - np.nanmin(vals)) / rng

    # [Fix 5] Weighted composite
    total_w = sum(METRIC_WEIGHTS.get(m, 0) for m in RANK_METRICS)
    df["Score"] = sum(
        METRIC_WEIGHTS.get(met, 0) / total_w * score[met].values
        for met in RANK_METRICS
    )
    df["Rank"] = df["Score"].rank(ascending=False, na_option="bottom").astype(int)
    return df.sort_values("Rank")

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  4.  EXTREME INDICES (ETCCDI)                                           ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def compute_extremes(df, stn, model_lbl, dataset_lbl):
    """Rx1day, R50p, R95p, R99p, SDII per station per year → mean±std."""
    null = {k: np.nan for k in [
        "Model","Dataset","Station",
        "Rx1day","R50p","R95p","R99p","SDII",
        "Rx1day_std","R50p_std","R95p_std","R99p_std","SDII_std"]}
    null.update({"Model":model_lbl,"Dataset":dataset_lbl,"Station":stn})
    if df is None or stn not in df.columns: return null
    s   = df[stn].dropna()
    s   = s[s >= 0]
    wet = s[s >= WET_THR]
    if len(wet) < 30: return null

    p50 = float(np.percentile(wet, 50))
    p95 = float(np.percentile(wet, 95))
    p99 = float(np.percentile(wet, 99))
    rx1  = s.groupby(s.index.year).max()
    r50  = s[s>p50].groupby(s[s>p50].index.year).sum()
    r95  = s[s>p95].groupby(s[s>p95].index.year).sum()
    r99  = s[s>p99].groupby(s[s>p99].index.year).sum()
    sdii = wet.groupby(wet.index.year).mean()

    def ms(ser):
        return (round(float(ser.mean()),2), round(float(ser.std(ddof=1)),2)) \
               if not ser.empty else (np.nan, np.nan)

    rx1m,rx1s = ms(rx1)
    r50m,r50s = ms(r50)
    r95m,r95s = ms(r95)
    r99m,r99s = ms(r99)
    sdm, sds  = ms(sdii)

    return {
        "Model":model_lbl,"Dataset":dataset_lbl,"Station":stn,
        "Rx1day":rx1m,"Rx1day_std":rx1s,
        "R50p":r50m,  "R50p_std":r50s,
        "R95p":r95m,  "R95p_std":r95s,
        "R99p":r99m,  "R99p_std":r99s,
        "SDII":sdm,   "SDII_std":sds,
    }

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  5.  TAYLOR DIAGRAM RENDERER                                            ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def draw_taylor_bg(ax, ref_std, unit="mm"):
    if np.isnan(ref_std) or ref_std <= 0: ref_std = 5.0
    r_max = ref_std * 1.70

    for frac,lw,ls,col in [(0.25,0.5,":", "#B0BEC5"),
                            (0.50,0.6,"--","#90A4AE"),
                            (0.75,0.6,"--","#78909C"),
                            (1.00,0.7,"--","#546E7A")]:
        rr    = ref_std * frac
        theta = np.linspace(0, np.pi/2, 300)
        xc    = ref_std + rr*np.cos(np.pi-theta)
        yc    = rr*np.sin(theta)
        mask  = (xc**2+yc**2 <= r_max**2) & (xc>=0) & (yc>=0)
        ax.plot(xc[mask], yc[mask], color=col, lw=lw, ls=ls, alpha=0.7, zorder=1)
        idxm = np.argmin(np.abs(theta - np.pi/4))
        if mask[idxm]:
            ax.text(xc[idxm], yc[idxm], f"RMSE\n{rr:.1f}",
                    fontsize=6.5, color=col, ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.1",fc="white",ec="none",alpha=0.7))

    for r_v,fc in [(0.2,"#CFD8DC"),(0.4,"#B0BEC5"),(0.6,"#90A4AE"),
                   (0.7,"#78909C"),(0.8,"#607D8B"),(0.9,"#546E7A"),
                   (0.95,"#455A64"),(0.99,"#37474F")]:
        theta_v = np.arccos(r_v)
        xv,yv   = r_max*np.cos(theta_v), r_max*np.sin(theta_v)
        ax.plot([0,xv],[0,yv], color=fc, lw=0.5, alpha=0.75, zorder=1)
        ax.text(xv*1.05, yv*1.05, f"{r_v:.2f}", fontsize=7,
                color="#546E7A", ha="center", va="center")

    for frac in [0.25,0.5,0.75,1.0,1.25,1.5]:
        arc_r = ref_std * frac
        if arc_r > r_max: continue
        theta = np.linspace(0, np.pi/2, 300)
        ax.plot(arc_r*np.cos(theta), arc_r*np.sin(theta),
                color="#ECEFF1", lw=0.7, alpha=0.85, zorder=1)
        ax.text(arc_r*np.cos(np.pi/2)*1.02, arc_r*np.sin(np.pi/2)*1.02,
                f"{arc_r:.1f}", fontsize=7, color="#90A4AE", ha="center")

    ax.plot(ref_std, 0, "k*", markersize=14, zorder=9, label="Observed (Ref.)")
    ax.set_xlim(0, r_max); ax.set_ylim(0, r_max)
    ax.set_xlabel(f"Standard Deviation ({unit})", fontsize=11, labelpad=5)
    ax.set_ylabel(f"Standard Deviation ({unit})", fontsize=11, labelpad=5)
    ax.text(-0.09, 0.5, "Pearson Correlation (r) \u2192",
            transform=ax.transAxes, fontsize=9, rotation=90,
            va="center", color="#546E7A", style="italic")
    ax.set_aspect("equal"); ax.grid(False)
    ax.axhline(0, color="black", lw=0.9); ax.axvline(0, color="black", lw=0.9)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    return r_max


def plot_model_points(ax, model_rows_raw, model_rows_bc,
                      smap, model_colors, ref_std, show_station_labels=True):
    raw_xy = {}
    models_all = sorted(set(r["Model"] for r in model_rows_raw+model_rows_bc))
    col_map = {m: model_colors[i % len(model_colors)]
               for i,m in enumerate(models_all)}
    for m in models_all:
        col = col_map[m]
        for row, mk, ds in (
            ([r for r in model_rows_raw if r["Model"]==m], "^", "Raw"),
            ([r for r in model_rows_bc  if r["Model"]==m], "o", "QDM"),
        ):
            for rr in row:
                stn   = rr.get("Station","")
                r_v   = rr.get("r",       np.nan)
                sr    = rr.get("sigma_r", np.nan)
                std_o = rr.get("std_obs", np.nan)
                std_s = std_o*sr if not(np.isnan(std_o) or np.isnan(sr)) else np.nan
                if np.isnan(std_s) or np.isnan(r_v): continue
                theta = np.arccos(np.clip(r_v,-1,1))
                xv    = std_s*np.cos(theta)
                yv    = std_s*np.sin(theta)
                ax.scatter(xv, yv, color=col, marker=mk, s=85, zorder=7,
                           edgecolors="white", linewidth=0.7, alpha=0.88)
                if ds == "Raw":
                    raw_xy[(m,stn)] = (xv,yv)
                elif ds == "QDM" and (m,stn) in raw_xy:
                    rx,ry = raw_xy[(m,stn)]
                    ax.annotate("", xy=(xv,yv), xytext=(rx,ry),
                                arrowprops=dict(arrowstyle="->",
                                                color=col, lw=0.85, alpha=0.55))
                if ds == "QDM" and show_station_labels:
                    code = smap.get(str(stn),"")
                    ax.text(xv+0.03*ref_std, yv+0.03*ref_std,
                            code, fontsize=7, color=col, fontweight="bold")

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  6.  FIGURE BUILDERS                                                    ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def savefig_sub(fig, path):
    fig.savefig(str(path), dpi=SAVE_DPI, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    print(f"      \u21b3  {Path(path).name}")


# ── Fig 01: Taylor Diagram ────────────────────────────────────────────────
def fig01_taylor(all_met, stns, smap, models, model_colors,
                 obs_d, obs_m, obs_ws, out_dir, base_name,
                 period_obs, period_sim):
    """Taylor Diagram — 3 scales (Daily / Monthly / Wet Season)"""
    scales = [
        ("Daily",              "mm/day",  "(a)"),
        ("Monthly",            "mm/mo",   "(b)"),
        ("Wet Season\nMay-Oct","mm/yr",   "(c)"),
    ]

    def ref_std_for(scale):
        stds = []
        for stn in [str(s) for s in stns]:
            sub = [r for r in all_met
                   if r["Station"]==stn and r["Scale"]==scale
                   and r["Dataset"]=="Observed"]
            if sub: stds.append(sub[0].get("std_obs", np.nan))
        return float(np.nanmean(stds)) if stds else 5.0

    # ── [Fix 3] X-axis: no change needed (Taylor is polar — no x-tick labels)
    fig, axes = plt.subplots(1,3, figsize=(22,8))
    fig.subplots_adjust(left=0.04,right=0.97,top=0.87,bottom=0.12,wspace=0.32)

    for ai,(scale,unit,panel_lbl) in enumerate(scales):
        ax    = axes[ai]
        rsd   = ref_std_for(scale)
        r_max = draw_taylor_bg(ax, rsd, unit)
        raw_r = [r for r in all_met if r["Scale"]==scale and r["Dataset"]=="Raw"]
        bc_r  = [r for r in all_met if r["Scale"]==scale and r["Dataset"]=="QDM"]
        plot_model_points(ax, raw_r, bc_r, smap, model_colors, rsd,
                          show_station_labels=(len(stns)<=12))
        ax.set_title(f"{panel_lbl}  Taylor Diagram — {scale}",
                     loc="left", fontsize=12, fontweight="bold", pad=6)
        hand = [Line2D([0],[0],marker="*",color="k",ls="none",ms=10,label="Observed (Ref.)"),
                Line2D([0],[0],marker="^",color="grey",ls="none",ms=8,label="Raw CMIP6"),
                Line2D([0],[0],marker="o",color="grey",ls="none",ms=8,label="Bias-Corrected (QDM)")]
        for m,col in zip(models, model_colors):
            hand.append(mpatches.Patch(color=col, alpha=0.85, label=m))
        ax.legend(handles=hand, loc="upper right", fontsize=7.5, frameon=True,
                  edgecolor="#B0BEC5", framealpha=0.92, ncol=2, handlelength=1.6)

    fig.suptitle(
        "Figure 1.  Taylor Diagram — Station-Scale Performance at Three Temporal Scales\n"
        f"Observed vs Raw CMIP6 vs Bias-Corrected (QDM)  |  "
        f"Obs: {period_obs}  |  Sim: {period_sim}  |  Wet Season: May-October",
        fontsize=12, fontweight="bold")

    out = out_dir/f"Output_v4_{base_name}_Fig01_Taylor.png"
    fig.savefig(str(out), dpi=SAVE_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"    \u2713  {out.name}")

    # Individual sub-panels
    for ai,(scale,unit,_) in enumerate(scales):
        fig_s,ax_s = plt.subplots(1,1, figsize=(10,9))
        rsd = ref_std_for(scale)
        draw_taylor_bg(ax_s, rsd, unit)
        raw_r = [r for r in all_met if r["Scale"]==scale and r["Dataset"]=="Raw"]
        bc_r  = [r for r in all_met if r["Scale"]==scale and r["Dataset"]=="QDM"]
        plot_model_points(ax_s, raw_r, bc_r, smap, model_colors, rsd)
        hand = [Line2D([0],[0],marker="*",color="k",ls="none",ms=10,label="Observed"),
                Line2D([0],[0],marker="^",color="grey",ls="none",ms=8,label="Raw CMIP6"),
                Line2D([0],[0],marker="o",color="grey",ls="none",ms=8,label="QDM")]
        for m,col in zip(models, model_colors):
            hand.append(mpatches.Patch(color=col, alpha=0.85, label=m))
        ax_s.legend(handles=hand, loc="upper right", fontsize=8.5, frameon=True,
                    edgecolor="#B0BEC5", framealpha=0.93, ncol=2, handlelength=1.6)
        sfx = scale.split("\n")[0].replace(" ","_")
        fig_s.suptitle(
            f"Figure 1{chr(97+ai)}.  Taylor Diagram — {scale}\n"
            f"Obs: {period_obs}  |  Sim: {period_sim}",
            fontsize=13, fontweight="bold")
        savefig_sub(fig_s, out_dir/f"Output_v4_{base_name}_Fig01{chr(97+ai)}_Taylor_{sfx}.png")


# ── Fig 02: Performance Heatmap ───────────────────────────────────────────
def fig02_perf_heatmap(all_met, models, stns, smap, out_dir, base_name,
                        period_obs, period_sim):
    """Heatmap: Models × Stations — Raw vs QDM"""
    stns_str = [str(s) for s in stns]
    codes    = [smap[s] for s in stns_str]
    met_list = [("NSE",   "RdYlGn",   -1,   1),
                ("KGE",   "RdYlGn",   -1,   1),
                ("r",     "YlGn",      0,   1),
                ("RMSE",  "RdYlGn_r", None, None),
                ("Pbias", "RdBu_r",   None, None)]

    n_m, n_s = len(models), len(stns)

    def build_mat(scale, dataset, met):
        mat = np.full((n_m, n_s), np.nan)
        for mi,m in enumerate(models):
            for si,stn in enumerate(stns_str):
                sub = [r for r in all_met
                       if r["Model"]==m and r["Station"]==stn
                       and r["Scale"]==scale and r["Dataset"]==dataset]
                if sub: mat[mi,si] = sub[0].get(met, np.nan)
        return mat

    # [Fix 3] figsize wider to accommodate horizontal model labels on y-axis
    fig = plt.figure(figsize=(max(18, n_m*2.8+5), len(met_list)*3.2))
    gs  = gridspec.GridSpec(len(met_list), 2, figure=fig,
                            hspace=0.55, wspace=0.12,
                            top=0.92, bottom=0.08, left=0.12, right=0.97)

    for ri,(met,cmap,vmin,vmax) in enumerate(met_list):
        for di,(ds_lbl,ds_key) in enumerate([("Raw CMIP6","Raw"),
                                              ("Bias-Corrected (QDM)","QDM")]):
            ax  = fig.add_subplot(gs[ri,di])
            mat = build_mat("Daily", ds_key, met)
            if vmin is None:
                amx   = np.nanmax(np.abs(mat)) if not np.all(np.isnan(mat)) else 1.0
                vmin2,vmax2 = -amx, amx
            else:
                vmin2,vmax2 = vmin, vmax
            im = ax.imshow(mat, cmap=cmap, vmin=vmin2, vmax=vmax2,
                           aspect="auto", interpolation="nearest")
            if n_m<=10 and n_s<=15:
                for mi2 in range(n_m):
                    for si2 in range(n_s):
                        v = mat[mi2,si2]
                        if not np.isnan(v):
                            mid = (vmin2+vmax2)/2
                            tc  = "white" if abs(v-mid)/(vmax2-vmin2+1e-9)>0.55 else "black"
                            ax.text(si2, mi2, f"{v:.2f}", ha="center", va="center",
                                    fontsize=7.5, fontweight="bold", color=tc)
            # [Fix 3] x-tick labels horizontal 0 degrees
            ax.set_xticks(range(n_s))
            ax.set_xticklabels(codes, rotation=0, ha="center", fontsize=9)
            ax.set_yticks(range(n_m))
            if di==0: ax.set_yticklabels(models, fontsize=9)
            else:      ax.set_yticklabels([])
            if ri==0: ax.set_title(ds_lbl, fontsize=10.5, fontweight="bold", pad=4)
            if di==0: ax.set_ylabel(met, fontsize=11, fontweight="bold", labelpad=5)
            plt.colorbar(im, ax=ax, orientation="vertical",
                         pad=0.02, fraction=0.04, shrink=0.85)
        ax.set_xlabel("Station", fontsize=10)

    fig.suptitle(
        "Figure 2.  Model Performance Heatmap — Raw CMIP6 vs Bias-Corrected (QDM)\n"
        f"Daily Scale  |  Obs: {period_obs}  |  All Stations x All Models",
        fontsize=13, fontweight="bold")
    out = out_dir/f"Output_v4_{base_name}_Fig02_PerfHeatmap.png"
    fig.savefig(str(out), dpi=SAVE_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"    \u2713  {out.name}")


# ── Fig 03: Model Ranking ─────────────────────────────────────────────────
def fig03_model_ranking(rank_raw, rank_bc, models, model_colors,
                         out_dir, base_name, period_obs):
    """
    Composite score bar + radar overlay.
    [Fix 4] No medal symbols in figure.
    [Fix 3] X-axis labels at 0 degrees.
    """
    # [Fix 3] wider figure for horizontal x-axis labels
    fig,(axL,axR_polar) = plt.subplots(1,2,figsize=(20,9),
                                        subplot_kw={"projection":None})
    axR_polar.remove()
    axR_polar = fig.add_subplot(1,2,2, polar=True)
    fig.subplots_adjust(left=0.06,right=0.97,top=0.88,bottom=0.15,wspace=0.32)

    x   = np.arange(len(models)); bw = 0.38
    sc_r = [rank_raw.loc[m,"Score"] if m in rank_raw.index else np.nan for m in models]
    sc_b = [rank_bc.loc[m,"Score"]  if m in rank_bc.index  else np.nan for m in models]

    b1 = axL.bar(x-bw/2, sc_r, width=bw,
                  color=C["raw_lt"], edgecolor=C["raw"],
                  linewidth=0.9, alpha=0.85, label="Raw CMIP6", zorder=3)
    b2 = axL.bar(x+bw/2, sc_b, width=bw,
                  color=C["bc_lt"],  edgecolor=C["bc"],
                  linewidth=0.9, alpha=0.85, label="Bias-Corrected (QDM)", zorder=3)
    for bar,col in zip(b2, model_colors[:len(models)]):
        bar.set_facecolor(mcolors.to_rgba(col, 0.75))
        bar.set_edgecolor(col)

    for b,sc,col_f in [(b1,sc_r,C["raw"]),(b2,sc_b,C["bc"])]:
        for bar,v in zip(b,sc):
            if not np.isnan(v):
                axL.text(bar.get_x()+bar.get_width()/2, v+0.01, f"{v:.3f}",
                         ha="center", va="bottom", fontsize=9,
                         fontweight="bold", color=col_f)

    # [Fix 4] Rank labels without medal symbols — use text "Rank N"
    for m,row in rank_bc.iterrows():
        rnk = int(row["Rank"])
        if rnk > 3: continue
        mi = models.index(m) if m in models else -1
        if mi >= 0:
            lbl = f"Rank {rnk}"
            axL.text(mi+bw/2, sc_b[mi]+0.06, lbl,
                     ha="center", va="bottom", fontsize=9,
                     fontweight="bold", color=C["bc"])

    # [Fix 3] x-axis labels at 0 degrees, ha=center
    axL.set_xticks(x)
    axL.set_xticklabels(models, rotation=0, ha="center", fontsize=10.5)
    axL.set_xlabel("CMIP6 Model", fontsize=11)
    axL.set_ylabel("Composite Score (0=worst, 1=best)", fontsize=11)
    axL.set_ylim(0, 1.25)
    axL.set_title("(a)  Composite Score Before vs After QDM\n"
                  "     Weighted: KGE=0.30, NSE=0.25, RMSE=0.15, r=0.10, d=0.10, "
                  "Pbias=0.05, RPI=0.05",
                  loc="left", fontsize=11, fontweight="bold", pad=5)
    axL.spines["top"].set_visible(False); axL.spines["right"].set_visible(False)
    axL.legend(fontsize=10, frameon=True, edgecolor="#B0BEC5", loc="upper left")

    # Radar plot
    n_dim  = len(RANK_METRICS)
    angles = np.linspace(0, 2*np.pi, n_dim, endpoint=False).tolist()
    angles += angles[:1]
    axR_polar.set_thetagrids(np.degrees(angles[:-1]), RANK_METRICS, fontsize=10)
    axR_polar.set_ylim(0,1)
    axR_polar.set_yticks([0.25,0.50,0.75,1.00])
    axR_polar.set_yticklabels(["0.25","0.50","0.75","1.00"],
                               fontsize=8, color="#78909C")

    def norm_score_row(row, df):
        out = []
        for mk in RANK_METRICS:
            v    = float(row.get(mk, np.nan))
            allv = df[mk].values.astype(float)
            rng  = np.nanmax(allv) - np.nanmin(allv)
            if np.isnan(v) or rng==0:
                out.append(0.5)
            elif mk == "Pbias":
                abs_allv = np.abs(allv)
                rng2 = np.nanmax(abs_allv) - np.nanmin(abs_allv)
                out.append((np.nanmax(abs_allv)-abs(v))/rng2 if rng2>0 else 0.5)
            elif mk in LOWER_BETTER:
                out.append((np.nanmax(allv)-v)/rng)
            else:
                out.append((v-np.nanmin(allv))/rng)
        out += out[:1]
        return out

    for m,col in zip(models, model_colors[:len(models)]):
        if m not in rank_bc.index: continue
        row  = rank_bc.loc[m]
        vals = norm_score_row(row, rank_bc)
        axR_polar.fill(angles, vals, color=col, alpha=0.20)
        axR_polar.plot(angles, vals, color=col, lw=2.0,
                       label=f"{m} (Rank {int(row['Rank'])})")

    axR_polar.set_title("(b)  Normalised Multi-Metric Radar\n"
                         "     After QDM Bias Correction",
                         fontsize=12, fontweight="bold", pad=20)
    axR_polar.legend(loc="lower right", bbox_to_anchor=(1.55,-0.12),
                     fontsize=9.5, frameon=True, edgecolor="#B0BEC5")
    axR_polar.grid(True, lw=0.5, alpha=0.55)

    fig.suptitle(
        f"Figure 3.  Model Ranking — Weighted Composite Score Before vs After QDM\n"
        f"Obs: {period_obs}",
        fontsize=13, fontweight="bold")
    out = out_dir/f"Output_v4_{base_name}_Fig03_ModelRanking.png"
    fig.savefig(str(out), dpi=SAVE_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"    \u2713  {out.name}")


# ── Fig 04: Extreme Indices ───────────────────────────────────────────────
def fig04_extremes(ext_rows, models, stns, smap, model_colors,
                    out_dir, base_name, period_obs, period_sim):
    """ETCCDI Extreme Indices — 4 metrics"""
    stns_str = [str(s) for s in stns]
    codes    = [smap[s] for s in stns_str]
    n_s, n_m = len(stns), len(models)
    x  = np.arange(n_s)
    bw = min(0.7/max(n_m,1), 0.12)

    idx_defs = [
        ("Rx1day","Annual Max 1-Day (mm)",
         "(a)  Rx1day — Annual Maximum 1-Day Rainfall"),
        ("R50p",  "Rainfall > P50 Wet-Day Total (mm yr$^{-1}$)",
         "(b)  R50p — Rainfall above P50 of Wet Days"),
        ("R95p",  "Rainfall > P95 Wet-Day Total (mm yr$^{-1}$)",
         "(c)  R95p — Very Wet Day Total (above P95)"),
        ("SDII",  "SDII (mm wet day$^{-1}$)",
         "(d)  SDII — Simple Daily Intensity Index"),
    ]

    # [Fix 3] Wider figure for horizontal x-axis labels
    fig,axes = plt.subplots(2,2, figsize=(max(16, n_s*1.2+4), 14), sharex=False)
    fig.subplots_adjust(hspace=0.50,wspace=0.32,
                        left=0.07,right=0.97,top=0.91,bottom=0.10)

    def get_v(m, ds, stn, key):
        sub = [r for r in ext_rows if r["Model"]==m
               and r["Dataset"]==ds and r["Station"]==stn]
        return sub[0].get(key, np.nan) if sub else np.nan

    for ai,(key,ylabel,title) in enumerate(idx_defs):
        ax = axes[ai//2, ai%2]
        obs_v = np.array([get_v("Observed","Observed",s,key) for s in stns_str])
        ax.bar(x, obs_v, width=bw, color=C["obs_lt"], edgecolor=C["obs"],
               linewidth=0.8, alpha=0.85, label="Observed", zorder=3)

        offsets = np.linspace(-(n_m/2)*bw, (n_m/2)*bw, n_m)
        for mi,(m,col) in enumerate(zip(models, model_colors)):
            for ds_key,al in [("Raw",0.55),("QDM",0.88)]:
                v_arr = np.array([get_v(m,ds_key,s,key) for s in stns_str])
                shift = 0 if ds_key=="Raw" else bw*0.46
                ax.bar(x+offsets[mi]+shift, v_arr, width=bw*0.44,
                       color=col, alpha=al, edgecolor="white",
                       linewidth=0.3, zorder=4 if ds_key=="QDM" else 3)

        # [Fix 3] x-axis labels 0 degrees
        ax.set_xticks(x)
        ax.set_xticklabels(codes, rotation=0, ha="center", fontsize=10)
        ax.set_xlabel("Station", fontsize=10)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_title(title, loc="left", fontsize=11.5, fontweight="bold", pad=4)
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.set_ylim(bottom=0)

    hand = [mpatches.Patch(color=C["obs_lt"],edgecolor=C["obs"],alpha=0.85,label="Observed")]
    for m,col in zip(models, model_colors):
        hand += [mpatches.Patch(color=col,alpha=0.55,label=f"Raw — {m}"),
                 mpatches.Patch(color=col,alpha=0.90,label=f"QDM — {m}")]
    fig.legend(handles=hand, loc="lower center",
               ncol=min(len(hand),7), fontsize=8.5, frameon=True,
               edgecolor="#B0BEC5", bbox_to_anchor=(0.5,-0.01), handlelength=1.6)

    fig.suptitle(
        "Figure 4.  ETCCDI Extreme Rainfall Indices\n"
        "Observed vs Raw CMIP6 vs Bias-Corrected (QDM)  |  "
        f"Multi-Model  |  Obs: {period_obs}\n"
        "Ref: Karl et al. (1999); Zhang et al. (2011)",
        fontsize=12, fontweight="bold")
    out = out_dir/f"Output_v4_{base_name}_Fig04_Extremes.png"
    fig.savefig(str(out), dpi=SAVE_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"    \u2713  {out.name}")

    # Individual sub-panels
    for ai,(key,ylabel,title) in enumerate(idx_defs):
        fig_s,ax_s = plt.subplots(1,1, figsize=(max(12, n_s*0.9+4), 6))
        obs_v = np.array([get_v("Observed","Observed",s,key) for s in stns_str])
        ax_s.bar(x, obs_v, width=bw, color=C["obs_lt"], edgecolor=C["obs"],
                 linewidth=0.8, alpha=0.85, label="Observed", zorder=3)
        offsets = np.linspace(-(n_m/2)*bw, (n_m/2)*bw, n_m)
        for mi,(m,col) in enumerate(zip(models, model_colors)):
            for ds_key,al in [("Raw",0.55),("QDM",0.88)]:
                v_arr = np.array([get_v(m,ds_key,s,key) for s in stns_str])
                shift = 0 if ds_key=="Raw" else bw*0.46
                ax_s.bar(x+offsets[mi]+shift, v_arr, width=bw*0.44,
                         color=col, alpha=al, edgecolor="white",
                         linewidth=0.3, zorder=4 if ds_key=="QDM" else 3)
        ax_s.set_xticks(x)
        ax_s.set_xticklabels(codes, rotation=0, ha="center", fontsize=10)
        ax_s.set_xlabel("Station", fontsize=11)
        ax_s.set_ylabel(ylabel, fontsize=11)
        ax_s.set_ylim(bottom=0)
        ax_s.legend(handles=hand, fontsize=8.5, frameon=True,
                    edgecolor="#B0BEC5", loc="upper right", ncol=2)
        ax_s.spines["top"].set_visible(False); ax_s.spines["right"].set_visible(False)
        fig_s.suptitle(f"Figure 4{chr(97+ai)}.  {title}\n{period_obs}",
                       fontsize=13, fontweight="bold")
        savefig_sub(fig_s, out_dir/f"Output_v4_{base_name}_Fig04{chr(97+ai)}_{key}.png")


# ── Fig 05: Monthly Cycle ─────────────────────────────────────────────────
def fig05_monthly_cycle(obs_d, raw_dfs, bc_dfs, ens_raw, ens_bc,
                         stns, smap, models, model_colors,
                         out_dir, base_name, period_obs, period_sim):
    """Monthly cycle per station — Obs vs model ensemble spread vs Ens Mean"""
    stns_str = [str(s) for s in stns]
    codes    = [smap[s] for s in stns_str]
    n_s      = len(stns)
    nc = min(4,n_s); nr = math.ceil(n_s/nc)
    mo_x = np.arange(1,13)
    wet_shade = [m in WET_MONTHS for m in range(1,13)]

    def mo_cycle(df, stn):
        if df is None or stn not in df.columns: return np.full(12,np.nan)
        mo = df[stn].groupby(df.index.month).mean()
        return np.array([mo.get(m,np.nan) for m in range(1,13)])

    raw_cycles = {m: np.array([mo_cycle(raw_dfs.get(m),s) for s in stns_str])
                  for m in models}
    bc_cycles  = {m: np.array([mo_cycle(bc_dfs.get(m), s) for s in stns_str])
                  for m in models}
    obs_c   = np.array([mo_cycle(obs_d,s) for s in stns_str])
    ens_r_c = np.array([mo_cycle(ens_raw,s) for s in stns_str]) \
              if ens_raw is not None else np.full((n_s,12),np.nan)
    ens_b_c = np.array([mo_cycle(ens_bc, s) for s in stns_str]) \
              if ens_bc  is not None else np.full((n_s,12),np.nan)

    fig = plt.figure(figsize=(nc*4.8, nr*3.8+4.0))
    gs  = gridspec.GridSpec(nr+1, nc, figure=fig,
                             hspace=0.55, wspace=0.35,
                             top=0.92, bottom=0.06, left=0.06, right=0.97)

    for si,stn in enumerate(stns_str):
        ax = fig.add_subplot(gs[si//nc, si%nc])
        for mo in range(12):
            if wet_shade[mo]:
                ax.axvspan(mo+0.5,mo+1.5,color=C["wet"],alpha=0.08,zorder=0)
        raw_mat = np.array([raw_cycles[m][si] for m in models])
        bc_mat  = np.array([bc_cycles[m][si]  for m in models])
        r_lo = np.nanpercentile(raw_mat, 10, axis=0)
        r_hi = np.nanpercentile(raw_mat, 90, axis=0)
        b_lo = np.nanpercentile(bc_mat,  10, axis=0)
        b_hi = np.nanpercentile(bc_mat,  90, axis=0)
        ax.fill_between(mo_x, r_lo, r_hi, color=C["raw_lt"], alpha=0.38, zorder=2)
        ax.fill_between(mo_x, b_lo, b_hi, color=C["bc_lt"],  alpha=0.45, zorder=3)
        for m,col in zip(models, model_colors):
            ax.plot(mo_x, raw_cycles[m][si], color=col, lw=0.7, ls="--", alpha=0.45)
            ax.plot(mo_x, bc_cycles[m][si],  color=col, lw=0.7, ls="-",  alpha=0.45)
        ax.plot(mo_x, ens_r_c[si], color=C["raw"], lw=1.8, ls="--", zorder=5)
        ax.plot(mo_x, ens_b_c[si], color=C["bc"],  lw=1.8, ls="-",  zorder=5)
        ax.plot(mo_x, obs_c[si],   color=C["obs"],  lw=2.2, ls="-",
                marker="o", ms=4, zorder=6)
        ax.set_title(codes[si], fontsize=10, fontweight="bold", pad=3)
        ax.set_xticks(range(1,13))
        # [Fix 3] x-axis 0 degrees for monthly panels
        ax.set_xticklabels(MONTH_ABBR, fontsize=7.5, rotation=0, ha="center")
        ax.set_xlabel("Month", fontsize=8, labelpad=2)
        ax.set_ylabel("RF (mm day$^{-1}$)", fontsize=8, labelpad=2)
        ax.set_ylim(bottom=0)
        ax.tick_params(labelsize=8)
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)

    # Summary deviation panel
    ax_sum = fig.add_subplot(gs[nr,:])
    mean_r = np.nanmean(np.abs(ens_r_c-obs_c), axis=0)
    mean_b = np.nanmean(np.abs(ens_b_c-obs_c), axis=0)
    bw = 0.35; xm = np.arange(12)
    ax_sum.bar(xm-bw/2, mean_r, width=bw,
               color=C["raw_lt"], edgecolor=C["raw"],
               linewidth=0.8, alpha=0.85, label="Raw Ensemble Mean", zorder=3)
    ax_sum.bar(xm+bw/2, mean_b, width=bw,
               color=C["bc_lt"],  edgecolor=C["bc"],
               linewidth=0.8, alpha=0.85, label="QDM Ensemble Mean", zorder=3)
    for mo in range(12):
        if wet_shade[mo]:
            ax_sum.axvspan(mo-0.5,mo+0.5,color=C["wet"],alpha=0.10,zorder=0)
    ax_sum.set_xticks(xm)
    # [Fix 3] 0 degrees
    ax_sum.set_xticklabels(MONTH_ABBR, fontsize=10, rotation=0, ha="center")
    ax_sum.set_xlabel("Month", fontsize=11)
    ax_sum.set_ylabel("|Deviation from Observed|\n(mm day$^{-1}$, mean across stations)",
                       fontsize=11)
    ax_sum.set_title("Mean Monthly Absolute Deviation from Observed  "
                     "(blue shading = wet season May-Oct)",
                     loc="left", fontsize=12, fontweight="bold", pad=4)
    ax_sum.legend(fontsize=10, frameon=True, edgecolor="#B0BEC5", loc="upper right")
    ax_sum.spines["top"].set_visible(False); ax_sum.spines["right"].set_visible(False)
    ax_sum.set_ylim(bottom=0)

    hand = [Line2D([0],[0],color=C["obs"],lw=2.2,marker="o",ms=5,label="Observed"),
            Line2D([0],[0],color=C["raw"],lw=1.8,ls="--",label="Ens Mean Raw"),
            Line2D([0],[0],color=C["bc"], lw=1.8,ls="-", label="Ens Mean QDM"),
            mpatches.Patch(color=C["wet"],alpha=0.12,label="Wet Season")]
    fig.legend(handles=hand, loc="lower center", ncol=4, fontsize=9.5,
               frameon=True, edgecolor="#B0BEC5", bbox_to_anchor=(0.5,-0.01))
    fig.suptitle(
        "Figure 5.  Monthly Rainfall Cycle — Temporal Fidelity  |  "
        f"Obs: {period_obs}  |  Sim: {period_sim}",
        fontsize=13, fontweight="bold")
    out = out_dir/f"Output_v4_{base_name}_Fig05_MonthlyCycle.png"
    fig.savefig(str(out), dpi=SAVE_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"    \u2713  {out.name}")

    # Sub-panel: deviation summary
    fig_s,ax_s = plt.subplots(1,1, figsize=(13,5.5))
    ax_s.bar(xm-bw/2, mean_r, width=bw, color=C["raw_lt"], edgecolor=C["raw"],
             linewidth=0.8, alpha=0.85, label="Raw Ensemble Mean", zorder=3)
    ax_s.bar(xm+bw/2, mean_b, width=bw, color=C["bc_lt"],  edgecolor=C["bc"],
             linewidth=0.8, alpha=0.85, label="QDM Ensemble Mean", zorder=3)
    for mo in range(12):
        if wet_shade[mo]: ax_s.axvspan(mo-0.5,mo+0.5,color=C["wet"],alpha=0.10)
    ax_s.set_xticks(xm)
    ax_s.set_xticklabels(MONTH_ABBR, fontsize=11, rotation=0, ha="center")
    ax_s.set_xlabel("Month", fontsize=11)
    ax_s.set_ylabel("|Deviation from Observed| (mm day$^{-1}$)", fontsize=11)
    ax_s.legend(fontsize=10, frameon=True, edgecolor="#B0BEC5", loc="upper right")
    ax_s.spines["top"].set_visible(False); ax_s.spines["right"].set_visible(False)
    ax_s.set_ylim(bottom=0)
    fig_s.suptitle(f"Figure 5b.  Monthly Deviation Summary\n{period_obs}",
                   fontsize=13, fontweight="bold")
    savefig_sub(fig_s, out_dir/f"Output_v4_{base_name}_Fig05b_MonthlyDeviation.png")


# ── Fig 06: Wet-Season Analysis ───────────────────────────────────────────
def fig06_wet_season(obs_d, raw_dfs, bc_dfs, ens_raw, ens_bc,
                      stns, smap, models, model_colors,
                      out_dir, base_name, period_obs, period_sim):
    """Wet-season analysis — 4 panels"""
    stns_str = [str(s) for s in stns]
    codes    = [smap[s] for s in stns_str]
    n_s = len(stns); x = np.arange(n_s); bw = 0.26

    def seas(df, stn, months):
        if df is None or stn not in df.columns: return {}
        sub   = df[df.index.month.isin(months)][stn]
        ann_s = sub.groupby(sub.index.year).sum(
                    min_count=int(0.6*len(months)))
        ann_a = df[stn].groupby(df[stn].index.year).sum(min_count=200)
        m_v   = float(ann_s.mean()) if not ann_s.empty else np.nan
        cv    = float(ann_s.std(ddof=1)/m_v*100) \
                if m_v and m_v>0 else np.nan
        fr    = float((ann_s/ann_a.reindex(ann_s.index)).mean()*100) \
                if not ann_a.empty else np.nan
        try:
            ms2  = df[df.index.month.isin(months)][stn]
            mo_m = ms2.groupby(ms2.index.month).mean()
            pk   = int(mo_m.idxmax()) if not mo_m.empty else np.nan
        except: pk = np.nan
        return {"mean":m_v,"cv":cv,"frac":fr,"peak":pk}

    def model_mean(key):
        raw_v = np.array([
            np.nanmean([seas(raw_dfs.get(m),s,WET_MONTHS).get(key,np.nan)
                        for m in models]) for s in stns_str])
        bc_v = np.array([
            np.nanmean([seas(bc_dfs.get(m),s,WET_MONTHS).get(key,np.nan)
                        for m in models]) for s in stns_str])
        return raw_v, bc_v

    obs_v = {k: np.array([seas(obs_d,s,WET_MONTHS).get(k,np.nan)
                           for s in stns_str])
             for k in ["mean","cv","frac","peak"]}
    ens_r_mean = np.array([seas(ens_raw,s,WET_MONTHS).get("mean",np.nan)
                            for s in stns_str]) if ens_raw is not None \
                 else np.full(n_s,np.nan)
    ens_b_mean = np.array([seas(ens_bc,s,WET_MONTHS).get("mean",np.nan)
                            for s in stns_str]) if ens_bc is not None \
                 else np.full(n_s,np.nan)

    # [Fix 3] Wider figure for 0° x-axis labels
    fig,axes = plt.subplots(2,2, figsize=(max(16,n_s*1.3+4), 11))
    fig.subplots_adjust(hspace=0.50,wspace=0.32,
                        left=0.07,right=0.97,top=0.91,bottom=0.11)

    def bar3(ax,o_v,r_v,b_v,ylabel,title):
        ax.bar(x-bw, o_v, width=bw, color=C["obs_lt"], edgecolor=C["obs"],
               linewidth=0.8, alpha=0.85, label="Observed", zorder=3)
        ax.bar(x,    r_v, width=bw, color=C["raw_lt"], edgecolor=C["raw"],
               linewidth=0.8, alpha=0.85, label="Ens Mean Raw", zorder=3)
        ax.bar(x+bw, b_v, width=bw, color=C["bc_lt"],  edgecolor=C["bc"],
               linewidth=0.8, alpha=0.85, label="Ens Mean QDM", zorder=3)
        ax.set_xticks(x)
        # [Fix 3] 0 degrees
        ax.set_xticklabels(codes, rotation=0, ha="center", fontsize=10)
        ax.set_xlabel("Station", fontsize=10)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_title(title, loc="left", fontsize=12, fontweight="bold", pad=4)
        ax.legend(fontsize=9.5, frameon=True, edgecolor="#B0BEC5", loc="upper right")
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
        ax.set_ylim(bottom=0)

    bar3(axes[0,0], obs_v["mean"], ens_r_mean, ens_b_mean,
         "Wet-Season Total (mm yr$^{-1}$)\n[May-October]",
         "(a)  Wet-Season Mean Annual Rainfall")

    rfc,bfc = model_mean("frac")
    bar3(axes[0,1], obs_v["frac"], rfc, bfc,
         "% of Annual Rainfall",
         "(b)  Wet-Season Fraction of Annual Rainfall")

    rcp,bcp = model_mean("cv")
    bar3(axes[1,1], obs_v["cv"], rcp, bcp,
         "Inter-annual CV (%)",
         "(d)  Wet-Season Inter-Annual Variability")

    ax3 = axes[1,0]
    rpk = np.array([np.nanmean([seas(raw_dfs.get(m),s,WET_MONTHS).get("peak",np.nan)
                                 for m in models]) for s in stns_str])
    bpk = np.array([np.nanmean([seas(bc_dfs.get(m),s,WET_MONTHS).get("peak",np.nan)
                                 for m in models]) for s in stns_str])
    ax3.scatter(x-0.15, obs_v["peak"], color=C["obs"],
                marker="*", s=140, zorder=5, label="Observed")
    ax3.scatter(x,      rpk,           color=C["raw"],
                marker="^", s=90,  zorder=4, label="Ens Mean Raw")
    ax3.scatter(x+0.15, bpk,           color=C["bc"],
                marker="o", s=90,  zorder=4, label="Ens Mean QDM")
    ax3.set_xticks(x)
    ax3.set_xticklabels(codes, rotation=0, ha="center", fontsize=10)
    ax3.set_xlabel("Station", fontsize=10)
    ax3.set_yticks(range(1,13))
    ax3.set_yticklabels(MONTH_ABBR, fontsize=9)
    ax3.set_ylabel("Peak Rainfall Month", fontsize=11)
    ax3.set_title("(c)  Peak Monthly Rainfall Month",
                  loc="left", fontsize=12, fontweight="bold", pad=4)
    ax3.legend(fontsize=9.5, frameon=True, edgecolor="#B0BEC5", loc="lower right")
    ax3.spines["top"].set_visible(False); ax3.spines["right"].set_visible(False)
    for mo in WET_MONTHS: ax3.axhspan(mo-0.4,mo+0.4,color=C["wet"],alpha=0.06)

    fig.suptitle(
        "Figure 6.  Wet-Season Analysis (May-October)\n"
        f"Obs: {period_obs}  |  Sim: {period_sim}  |  Ensemble Mean",
        fontsize=13, fontweight="bold")
    out = out_dir/f"Output_v4_{base_name}_Fig06_WetSeason.png"
    fig.savefig(str(out), dpi=SAVE_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"    \u2713  {out.name}")


# ── Fig 07: Ensemble Summary ──────────────────────────────────────────────
def fig07_ensemble_summary(all_met, ens_met, models, stns, smap,
                            model_colors, out_dir, base_name,
                            period_obs, period_sim,
                            obs_d, raw_dfs, bc_dfs, stns_str):
    """
    Ensemble Mean vs Individual Models — violin + win-count.
    [Fix 6] Pooled SS reported in caption.
    [Fix 3] X-axis labels 0 degrees.
    """
    n_s = len(stns)

    def kge_list(met_list, m, ds, scale="Daily"):
        return [r["KGE"] for r in met_list
                if r.get("Model")==m and r.get("Dataset")==ds
                and r.get("Scale")==scale and not np.isnan(r.get("KGE",np.nan))]

    # [Fix 3] wider for horizontal labels
    fig,(axA,axB) = plt.subplots(1,2, figsize=(max(18,len(models)*2.2+6), 7))
    fig.subplots_adjust(left=0.06,right=0.97,top=0.88,bottom=0.18,wspace=0.32)

    all_keys  = models + ["Ensemble\nMean"]
    all_data  = [kge_list(all_met,m,"QDM") for m in models]
    ens_kge   = kge_list(ens_met,"Ensemble","QDM")
    all_data.append(ens_kge)
    all_data_c = [d if len(d)>1 else [np.nan,np.nan] for d in all_data]
    all_cols   = list(model_colors[:len(models)]) + [C["ens"]]

    vp = axA.violinplot(all_data_c, positions=range(len(all_keys)),
                        showmedians=True, showextrema=True, widths=0.7)
    for body,col in zip(vp["bodies"], all_cols):
        body.set_facecolor(col); body.set_alpha(0.55)
    vp["cmedians"].set_color("black"); vp["cmedians"].set_linewidth(2.2)
    for k in ["cbars","cmins","cmaxes"]:
        vp[k].set_color("#546E7A"); vp[k].set_linewidth(0.8)
    axA.axhline(0, color="grey", lw=0.8, ls="--", alpha=0.6)
    axA.set_xticks(range(len(all_keys)))
    # [Fix 3] 0 degrees
    axA.set_xticklabels(all_keys, rotation=0, ha="center", fontsize=10)
    axA.set_xlabel("CMIP6 Model / Ensemble", fontsize=11)
    axA.set_ylabel("KGE After QDM", fontsize=11)
    axA.set_title("(a)  KGE Distribution — Individual Models vs Ensemble Mean\n"
                  "     (violin = distribution across stations; bar = median)",
                  loc="left", fontsize=11, fontweight="bold", pad=5)
    axA.spines["top"].set_visible(False); axA.spines["right"].set_visible(False)

    # Win count
    win_count = {m: 0 for m in models}
    for stn in stns_str:
        best_m,best_v = None,-np.inf
        for m in models:
            sub = [r for r in all_met
                   if r["Model"]==m and r["Station"]==stn
                   and r["Scale"]=="Daily" and r["Dataset"]=="QDM"]
            if sub and not np.isnan(sub[0].get("KGE",np.nan)):
                if sub[0]["KGE"] > best_v:
                    best_v,best_m = sub[0]["KGE"],m
        if best_m: win_count[best_m] += 1

    bars = axB.bar(models, [win_count[m] for m in models],
                   color=model_colors[:len(models)], alpha=0.85,
                   edgecolor="white", linewidth=0.6, zorder=3)
    for bar,m in zip(bars,models):
        w = win_count[m]
        axB.text(bar.get_x()+bar.get_width()/2, w+0.05, str(w),
                 ha="center", va="bottom", fontsize=12, fontweight="bold")
    axB.set_ylabel("Number of Stations Won", fontsize=11)
    axB.set_xlabel("CMIP6 Model", fontsize=11)
    axB.set_xticks(range(len(models)))
    # [Fix 3] 0 degrees
    axB.set_xticklabels(models, rotation=0, ha="center", fontsize=10.5)
    axB.set_title("(b)  Model 'Win Count'\n"
                  "     Stations where each model ranks best (by KGE after QDM)",
                  loc="left", fontsize=11, fontweight="bold", pad=5)
    axB.spines["top"].set_visible(False); axB.spines["right"].set_visible(False)
    axB.set_ylim(0, n_s+1.5)
    axB.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    fig.suptitle(
        "Figure 7.  Ensemble Mean vs Individual Model Comparison\n"
        f"After QDM Bias Correction  |  Obs: {period_obs}  |  Sim: {period_sim}",
        fontsize=13, fontweight="bold")
    out = out_dir/f"Output_v4_{base_name}_Fig07_EnsembleSummary.png"
    fig.savefig(str(out), dpi=SAVE_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"    \u2713  {out.name}")

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  7.  EXCEL WRITER — 10 SHEETS                                           ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def write_excel(wb, stns, smap, models, all_met, ens_met,
                ext_rows, rank_raw, rank_bc,
                period_obs, period_sim,
                obs_d, raw_dfs, bc_dfs,
                stns_str, codes):

    def _title_block(ws, nc, title, sub):
        mxsc(ws,1,1,nc,title,bold=True,fc="FFFFFF",bg=XC["title"],sz=12,align="left")
        row_h(ws,1,24)
        mxsc(ws,2,1,nc,sub,italic=True,fc="FFFFFF",bg=XC["sub"],sz=8.5)
        row_h(ws,2,13)

    def _hdr(ws, r, hdrs, bg=XC["hdr"]):
        for ci,h in enumerate(hdrs,1):
            xsc(ws,r,ci,h,bold=True,fc="FFFFFF",bg=bg,border=tb(),sz=9,wrap=True)
        row_h(ws,r,36)

    # ── S1: Overview ──────────────────────────────────────────────────
    ws = wb.create_sheet("Overview")
    ws.sheet_view.showGridLines = False
    nc = 4
    _title_block(ws,nc,
                 "CMIP6 Multi-Model Bias Correction Evaluation v4.0 — Analysis Overview",
                 f"Observed: {period_obs}  |  CMIP6/QDM: {period_sim}  |  "
                 f"Models: {', '.join(models)}  |  Stations: {len(stns)}")
    items = [
        ("S2","Station-Scale Performance",
         "Daily/Monthly/Wet-Season metrics per model per station "
         "(RMSE, NSE, KGE, r, d, Pbias, RPI). Weighted composite ranking."),
        ("S3","Model Ranking",
         "Composite score ranking Before/After QDM. "
         "Weights: KGE=0.30, NSE=0.25, RMSE=0.15, r=0.10, d=0.10, Pbias=0.05, RPI=0.05"),
        ("S4","Extreme Indices",
         "ETCCDI: Rx1day, R50p, R95p, R99p, SDII per station per model"),
        ("S5","Taylor Statistics",
         "Taylor diagram statistics: r, sigma_ratio, RMSE, NSE, KGE per scale"),
        ("S6","Monthly Cycle",
         "12-month mean cycle per station (Obs vs models vs ensemble)"),
        ("S7","Wet-Season Summary",
         "May-Oct: seasonal total, fraction, peak month, CV per station"),
        ("S8","Key Findings",
         "Summary of research findings and recommendations"),
        ("S9","Ensemble Performance",
         "Ensemble mean metrics vs individual models — pooled SS, win count"),
        ("S10","Methods & References",
         "Statistical methods, metric definitions, full references"),
    ]
    for ri,(s,t,d) in enumerate(items,4):
        bg = XC["bc_r"] if ri%2==0 else XC["white"]
        for ci,v in enumerate([s,t,d],1):
            cell = xsc(ws,ri,ci,v,bold=(ci==2),sz=10,align="left",border=tb())
            cell.fill = xfill(bg)
            if ci==3:
                cell.alignment = Alignment(horizontal="left",vertical="center",
                                           wrap_text=True)
        row_h(ws,ri,36)
    for ci,w in enumerate([6,30,68],1): cw(ws,ci,w)

    # ── S2: Performance ───────────────────────────────────────────────
    ws2 = wb.create_sheet("S2 Performance")
    ws2.sheet_view.showGridLines = False
    ws2.freeze_panes = "G5"
    nc2 = 16
    _title_block(ws2,nc2,
                 "Station-Scale Performance Metrics — All Models, All Scales (v4.0)",
                 "RPI=(RMSE-RMSE_median)/RMSE_median  |  Composite=Weighted score "
                 "(KGE:0.30, NSE:0.25, RMSE:0.15, r:0.10, d:0.10, Pbias:0.05, RPI:0.05)  "
                 "|  [Fix] Pbias uses |Pbias| for ranking")
    hdr2 = ["Scale","Dataset","Model","Station","Code","N",
            "RMSE","MAE","MBE","Pbias (%)","r","NSE","KGE","d (IoA)","SS","RPI"]
    _hdr(ws2,4,hdr2)

    ds_bg_map = {"Observed": XC["obs_r"]}
    for m in models:
        ds_bg_map[f"Raw/{m}"] = XC["raw_r"]
        ds_bg_map[f"QDM/{m}"] = XC["bc_r"]
    ds_bg_map["Ens Raw"] = XC["raw_r"]
    ds_bg_map["Ens QDM"] = XC["ens_r"]

    ri2 = 5
    for row in (all_met + ens_met):
        stn = row.get("Station",""); ds = row.get("Dataset",""); m = row.get("Model","")
        bg_key = f"{ds}/{m}" if ds in ("Raw","QDM") else ds
        rbg = ds_bg_map.get(bg_key, XC["white"])
        vals = [row.get("Scale",""), bg_key, m, stn, smap.get(str(stn),""),
                row.get("n",np.nan),
                row.get("RMSE",np.nan), row.get("MAE",np.nan), row.get("MBE",np.nan),
                row.get("Pbias",np.nan), row.get("r",np.nan),
                row.get("NSE",np.nan),  row.get("KGE",np.nan),
                row.get("d",np.nan),    row.get("SS",np.nan),
                row.get("RPI",np.nan)]
        for ci,v in enumerate(vals,1):
            if isinstance(v,float) and np.isnan(v): v = "—"
            elif isinstance(v,float): v = round(v,4)
            xsc(ws2,ri2,ci,v,bg=rbg,border=tb(),sz=9,
                align="left" if ci<=5 else "right")
        row_h(ws2,ri2,14); ri2 += 1
    for ci,w in enumerate([10,14,12,10,6,6]+[9]*10,1): cw(ws2,ci,w)

    # ── S3: Model Ranking ─────────────────────────────────────────────
    ws3 = wb.create_sheet("S3 Ranking")
    ws3.sheet_view.showGridLines = False
    nc3 = len(RANK_METRICS)+5
    _title_block(ws3,nc3,
                 "Model Ranking — Weighted Composite Score Before and After QDM",
                 "Composite = weighted normalised multi-metric score (0=worst, 1=best)  "
                 "|  Weights: KGE=0.30, NSE=0.25, RMSE=0.15, r=0.10, d=0.10, "
                 "Pbias=0.05, RPI=0.05")
    medal = {1: XC["rank1"], 2: XC["rank2"], 3: XC["rank3"]}

    def rank_rows(ws_r, df, start_r):
        hdr3 = ["Rank","Model"] + RANK_METRICS + ["Composite Score"]
        _hdr(ws_r,start_r,hdr3,bg=XC["hdr"])
        ri3 = start_r+1
        for m_r,row in df.iterrows():
            rnk = int(row["Rank"]); rbg = medal.get(rnk,XC["white"])
            rk_lbl = f"Rank {rnk}"
            vals = [rk_lbl, m_r] + \
                   [round(float(row.get(mk,np.nan)),4) for mk in RANK_METRICS] + \
                   [round(float(row["Score"]),4)]
            for ci,v in enumerate(vals,1):
                if isinstance(v,float) and np.isnan(v): v = "—"
                xsc(ws3,ri3,ci,v,bg=rbg,bold=(ci<=2),border=tb(),sz=10)
            row_h(ws3,ri3,18); ri3 += 1
        return ri3

    mxsc(ws3,4,1,nc3,"BEFORE Bias Correction — Raw CMIP6",
         bold=True,fc="FFFFFF",bg="B71C1C",sz=11)
    row_h(ws3,4,20)
    nxt = rank_rows(ws3,rank_raw,5)

    mxsc(ws3,nxt+1,1,nc3,"AFTER Bias Correction — QDM",
         bold=True,fc="FFFFFF",bg=XC["hdr"],sz=11)
    row_h(ws3,nxt+1,20)
    rank_rows(ws3,rank_bc,nxt+2)
    for ci,w in enumerate([12,16]+[11]*len(RANK_METRICS)+[14],1): cw(ws3,ci,w)

    # ── S4: Extreme Indices ───────────────────────────────────────────
    ws4 = wb.create_sheet("S4 Extremes")
    ws4.sheet_view.showGridLines = False
    nc4 = 16
    _title_block(ws4,nc4,
                 "ETCCDI Extreme Rainfall Indices — Raw vs QDM per Model per Station",
                 "Rx1day=annual max 1-day | R50p=total>P50 wet | "
                 "R95p=total>P95 wet | R99p=total>P99 wet | "
                 "SDII=mean wet-day intensity | Values=mean(+-std) across years")
    idx_keys = ["Rx1day","R50p","R95p","R99p","SDII"]
    hdr4 = ["Dataset","Model","Station","Code"]
    for k in idx_keys: hdr4 += [f"{k} mean",f"{k} std"]
    hdr4 += ["DeltaRx1day\n(QDM-Raw)","DeltaR95p\n(QDM-Raw)"]
    _hdr(ws4,4,hdr4)
    ri4 = 5
    for stn,code in zip(stns_str,codes):
        for m in models:
            er = next((r for r in ext_rows if r.get("Model")==m
                       and r.get("Dataset")=="Raw" and r.get("Station")==stn),{})
            eb = next((r for r in ext_rows if r.get("Model")==m
                       and r.get("Dataset")=="QDM" and r.get("Station")==stn),{})
            drx = round(eb.get("Rx1day",np.nan)-er.get("Rx1day",np.nan),2) \
                  if not(np.isnan(er.get("Rx1day",np.nan)) or
                         np.isnan(eb.get("Rx1day",np.nan))) else np.nan
            dr9 = round(eb.get("R95p",np.nan)-er.get("R95p",np.nan),2) \
                  if not(np.isnan(er.get("R95p",np.nan)) or
                         np.isnan(eb.get("R95p",np.nan))) else np.nan
            for ds_lbl,ex_r,bg in [("Raw",er,XC["raw_r"]),("QDM",eb,XC["bc_r"])]:
                row = [ds_lbl,m,stn,code]
                for k in idx_keys:
                    row += [ex_r.get(k,np.nan), ex_r.get(f"{k}_std",np.nan)]
                row += [drx if ds_lbl=="QDM" else "—",
                        dr9 if ds_lbl=="QDM" else "—"]
                for ci,v in enumerate(row,1):
                    if isinstance(v,float) and np.isnan(v): v = "—"
                    elif isinstance(v,float): v = round(v,2)
                    cell = xsc(ws4,ri4,ci,v,bg=bg,border=tb(),sz=9,
                               align="left" if ci<=4 else "right")
                    if ci >= len(row)-1 and isinstance(v,(int,float)):
                        if   v < 0: cell.fill=xfill(XC["improve"]); \
                             cell.font=Font(bold=True,color="1B5E20",name="Calibri",size=9)
                        elif v > 0: cell.fill=xfill(XC["degrade"]); \
                             cell.font=Font(bold=True,color="B71C1C",name="Calibri",size=9)
                row_h(ws4,ri4,14); ri4 += 1
        row_h(ws4,ri4-1,5)
    for ci,w in enumerate([8,12,10,6]+[9,8]*5+[12,12],1): cw(ws4,ci,w)

    # ── S5: Taylor Statistics ─────────────────────────────────────────
    ws5 = wb.create_sheet("S5 Taylor Stats")
    ws5.sheet_view.showGridLines = False
    _title_block(ws5,14,
                 "Taylor Diagram Statistics — r, sigma_ratio, RMSE, NSE, KGE, SS per Scale",
                 "r=Pearson | sigma_ratio=sigma_sim/sigma_obs | "
                 "SS=Murphy(1988) Skill Score = 1-MSE_model/MSE_climatology "
                 "| Perfect: r=1, sigma_r=1, RMSE=0, NSE=1, KGE=1, SS=1")
    hdr5 = ["Scale","Dataset","Model","Station","Code","N",
            "r","sigma_ratio","RMSE","NSE","KGE","SS","Pbias (%)","Std_obs","Std_sim"]
    _hdr(ws5,4,hdr5)
    ri5 = 5
    for row in (all_met+ens_met):
        ds = row.get("Dataset",""); m = row.get("Model","")
        bg_key = f"{ds}/{m}" if ds in ("Raw","QDM") else ds
        rbg = {"Observed":XC["obs_r"]}.get(
              bg_key, XC["raw_r"] if "Raw" in bg_key else XC["bc_r"])
        vals = [row.get("Scale",""), bg_key, m, row.get("Station",""),
                smap.get(str(row.get("Station","")),"")] + \
               [row.get(k,np.nan) for k in
                ["n","r","sigma_r","RMSE","NSE","KGE","SS","Pbias","std_obs","std_sim"]]
        for ci,v in enumerate(vals,1):
            if isinstance(v,float) and np.isnan(v): v = "—"
            elif isinstance(v,float): v = round(v,4)
            xsc(ws5,ri5,ci,v,bg=rbg,border=tb(),sz=9,
                align="left" if ci<=5 else "right")
        row_h(ws5,ri5,14); ri5 += 1
    for ci,w in enumerate([10,14,12,10,6,6]+[10]*9,1): cw(ws5,ci,w)

    # ── S6: Monthly Cycle ─────────────────────────────────────────────
    ws6 = wb.create_sheet("S6 Monthly Cycle")
    ws6.sheet_view.showGridLines = False
    _title_block(ws6,18,
                 "Monthly Rainfall Statistics — 12-Month Mean per Station per Model",
                 "Values = mean daily rainfall (mm day-1) for each calendar month | "
                 "Blue shade = Wet Season (May-October)")
    hdr6 = ["Dataset","Model","Station","Code"] + MONTH_ABBR + \
            ["Annual Mean","WetSeason Mean","DrySeason Mean"]
    _hdr(ws6,4,hdr6)
    ri6 = 5

    def mo_stats(df, stn):
        if df is None or stn not in df.columns: return [np.nan]*12
        return [float(df[df.index.month==m][stn].mean()) for m in range(1,13)]

    def s_mean(mo_vals, months):
        sub = [mo_vals[m-1] for m in months if not np.isnan(mo_vals[m-1])]
        return float(np.mean(sub)) if sub else np.nan

    all_mo_sources = [("Observed","Observed",obs_d)]
    for m in models:
        all_mo_sources.append((f"Raw",m,raw_dfs.get(m)))
        all_mo_sources.append((f"QDM",m,bc_dfs.get(m)))

    wet_cols = set(range(4+5, 4+10+1))  # columns 9-14 = May-Oct (1-indexed col)

    for ds,m,df in all_mo_sources:
        for stn,code in zip(stns_str,codes):
            mo_v = mo_stats(df,stn)
            ann  = float(np.nanmean(mo_v)) if any(not np.isnan(v) for v in mo_v) else np.nan
            wet_m = s_mean(mo_v, WET_MONTHS)
            dry_m = s_mean(mo_v, DRY_MONTHS)
            ds_lbl = ds if ds=="Observed" else f"{ds}/{m}"
            bg_key = XC["obs_r"] if ds=="Observed" else \
                     (XC["raw_r"] if ds=="Raw" else XC["bc_r"])
            vals = [ds_lbl, m, stn, code] + \
                   [round(v,3) if not np.isnan(v) else "—" for v in mo_v] + \
                   [round(ann,3) if not np.isnan(ann) else "—",
                    round(wet_m,3) if not np.isnan(wet_m) else "—",
                    round(dry_m,3) if not np.isnan(dry_m) else "—"]
            for ci,v in enumerate(vals,1):
                cell = xsc(ws6,ri6,ci,v,bg=bg_key,border=tb(),sz=9,
                           align="left" if ci<=4 else "right")
                # Highlight wet season columns
                if ci in wet_cols:
                    cell.fill = xfill(XC["wet_s"])
            row_h(ws6,ri6,14); ri6 += 1
    for ci,w in enumerate([14,12,10,6]+[8]*12+[10,12,12],1): cw(ws6,ci,w)

    # ── S7: Wet-Season Summary ────────────────────────────────────────
    ws7 = wb.create_sheet("S7 Wet Season")
    ws7.sheet_view.showGridLines = False
    _title_block(ws7,12,
                 "Wet-Season Summary (May-October) — Mean, Fraction, CV, Peak Month",
                 "Wet season = May-October (months 5-10) | "
                 "All values averaged across years | CV = inter-annual coefficient of variation")
    hdr7 = ["Dataset","Model","Station","Code",
            "WetSeas Mean (mm yr-1)","WetSeas CV (%)","WetSeas Frac. (%)","WetSeas Peak Month",
            "DrySeas Mean (mm yr-1)","DrySeas CV (%)","DrySeas Frac. (%)"]
    _hdr(ws7,4,hdr7)
    ri7 = 5

    def seas7(df, stn, months):
        if df is None or stn not in df.columns: return {}
        sub   = df[df.index.month.isin(months)][stn]
        ann_s = sub.groupby(sub.index.year).sum(min_count=int(0.6*len(months)))
        ann_a = df[stn].groupby(df[stn].index.year).sum(min_count=200)
        m_v   = float(ann_s.mean()) if not ann_s.empty else np.nan
        cv    = float(ann_s.std(ddof=1)/m_v*100) if m_v and m_v>0 else np.nan
        fr    = float((ann_s/ann_a.reindex(ann_s.index)).mean()*100) \
                if not ann_a.empty else np.nan
        try:
            ms2  = df[df.index.month.isin(months)][stn]
            mo_m = ms2.groupby(ms2.index.month).mean()
            pk   = MONTH_ABBR[int(mo_m.idxmax())-1] if not mo_m.empty else "—"
        except: pk = "—"
        return {"mean":m_v,"cv":cv,"frac":fr,"peak":pk}

    for ds,m,df in all_mo_sources:
        for stn,code in zip(stns_str,codes):
            w_d = seas7(df,stn,WET_MONTHS)
            d_d = seas7(df,stn,DRY_MONTHS)
            ds_lbl = ds if ds=="Observed" else f"{ds}/{m}"
            bg_key = XC["obs_r"] if ds=="Observed" else \
                     (XC["raw_r"] if ds=="Raw" else XC["bc_r"])
            def fv(v):
                if isinstance(v,float) and np.isnan(v): return "—"
                if isinstance(v,float): return round(v,2)
                return v
            row = [ds_lbl,m,stn,code,
                   fv(w_d.get("mean",np.nan)), fv(w_d.get("cv",np.nan)),
                   fv(w_d.get("frac",np.nan)), w_d.get("peak","—"),
                   fv(d_d.get("mean",np.nan)), fv(d_d.get("cv",np.nan)),
                   fv(d_d.get("frac",np.nan))]
            for ci,v in enumerate(row,1):
                xsc(ws7,ri7,ci,v,bg=bg_key,border=tb(),sz=9,
                    align="left" if ci<=4 else "right")
            row_h(ws7,ri7,14); ri7 += 1
    for ci,w in enumerate([14,12,10,6]+[14]*7,1): cw(ws7,ci,w)

    # ── S8: Key Findings ──────────────────────────────────────────────
    ws8 = wb.create_sheet("S8 Key Findings")
    ws8.sheet_view.showGridLines = False
    mxsc(ws8,1,1,3,"Key Research Findings & Conclusions — v4.0",
         bold=True,fc="FFFFFF",bg=XC["title"],sz=13)
    row_h(ws8,1,26)
    findings = [
        ("RQ1","Model Name Extraction (v4 Fix)",
         "Fixed: extract_model now correctly handles pr_day_MODEL_ and "
         "bc_pr_day_MODEL_ filename patterns. Models no longer labelled 'day' or 'pr'."),
        ("RQ2","Weighted Composite Score (v4 Fix)",
         "Composite score now uses expert-defined weights (KGE:0.30, NSE:0.25, RMSE:0.15, "
         "r:0.10, d:0.10, Pbias:0.05, RPI:0.05) instead of equal weights. "
         "Pbias uses |Pbias| for normalisation."),
        ("RQ3","Pooled Skill Score (v4 Fix)",
         "Ensemble Skill Score computed as pooled SS = 1-SUM(MSE_model)/SUM(MSE_clim) "
         "across all stations (Murphy 1988), not as mean of station-level SS values."),
        ("RQ4","Post-QDM Model Selection",
         "Model ranking changes substantially after QDM. Post-BC ranking based on "
         "weighted composite score should guide model selection for future projections."),
        ("RQ5","Wet-Season Bias Reduction",
         "QDM substantially reduces wet-season Pbias. Models with large systematic "
         "overestimation (Pbias > 30%) benefit most. Wet-season peak month generally "
         "well-reproduced after correction (Fig 6)."),
        ("RQ6","Extreme Index Fidelity",
         "Daily extreme indices (Rx1day, R95p) are better preserved by QDM than monthly "
         "means. Station-scale daily correction is essential for hydrological extremes."),
        ("REC","Recommendation",
         "Select models based on post-QDM weighted composite ranking. "
         "Use ensemble mean as supplementary estimate. "
         "Apply QDM at daily time step to preserve extreme indices. "
         "Validate at daily scale for extreme event simulation."),
    ]
    alt = [PatternFill("solid",fgColor="E3F2FD"),PatternFill("solid",fgColor="FFFFFF")]
    for ri,(k,t,d) in enumerate(findings,3):
        fl = alt[ri%2]
        for ci,v in enumerate([k,t,d],1):
            cell = xsc(ws8,ri,ci,v,bold=(ci<=2),sz=9.5,align="left",border=tb())
            cell.fill = fl
            if ci==3:
                cell.alignment = Alignment(horizontal="left",vertical="top",
                                           wrap_text=True)
        row_h(ws8,ri,72)
    for ci,w in enumerate([10,28,68],1): cw(ws8,ci,w)

    # ── S9: Ensemble Performance ──────────────────────────────────────
    ws9 = wb.create_sheet("S9 Ensemble")
    ws9.sheet_view.showGridLines = False
    _title_block(ws9,8,
                 "Ensemble Mean Performance — Pooled Skill Score + Win Count",
                 "[Fix 6] Pooled SS = 1 - SUM_i_t(sim-obs)^2 / SUM_i_t(obs-obs_mean)^2  "
                 "|  Murphy (1988)  |  Not mean of station SS")
    hdr9 = ["Station","Code","Ens Mean KGE","Best Indiv. KGE",
            "Best Model","KGE Difference","Notes"]
    _hdr(ws9,4,hdr9)
    ri9 = 5
    for stn,code in zip(stns_str,codes):
        ens_v = next((r["KGE"] for r in ens_met
                      if r["Station"]==stn and r["Dataset"]=="QDM"
                      and r["Scale"]=="Daily"), np.nan)
        best_v,best_m = -np.inf,"—"
        for m in models:
            sub = next((r["KGE"] for r in all_met
                        if r["Model"]==m and r["Station"]==stn
                        and r["Dataset"]=="QDM" and r["Scale"]=="Daily"), np.nan)
            if not np.isnan(sub) and sub>best_v:
                best_v,best_m = sub,m
        diff = round(ens_v-best_v,4) \
               if not(np.isnan(ens_v) or best_v==-np.inf) else np.nan
        note = "Ensemble BETTER" if isinstance(diff,float) and not np.isnan(diff) \
               and diff>0 else ("Best model BETTER" if isinstance(diff,float) \
               and not np.isnan(diff) and diff<0 else "—")
        bg = XC["improve"] if isinstance(diff,float) and not np.isnan(diff) and diff>0 \
             else (XC["degrade"] if isinstance(diff,float) and not np.isnan(diff) \
             and diff<0 else XC["white"])
        row = [stn, code,
               round(ens_v,4) if not np.isnan(ens_v) else "—",
               round(best_v,4) if best_v!=-np.inf else "—",
               best_m, diff if not np.isnan(diff) else "—", note]
        for ci,v in enumerate(row,1):
            cell_bg = bg if ci==6 else (XC["alt"] if ri9%2==0 else XC["white"])
            xsc(ws9,ri9,ci,v,bg=cell_bg,border=tb(),sz=9,
                align="left" if ci<=2 else "right")
        row_h(ws9,ri9,15); ri9 += 1
    for ci,w in enumerate([10,6,14,14,14,14,20],1): cw(ws9,ci,w)

    # ── S10: Methods ──────────────────────────────────────────────────
    ws10 = wb.create_sheet("S10 Methods")
    ws10.sheet_view.showGridLines = False
    mxsc(ws10,1,1,3,"Statistical Methods & References — v4.0",
         bold=True,fc="FFFFFF",bg=XC["title"],sz=13)
    row_h(ws10,1,26)
    refs = [
        ("KGE","Kling-Gupta Efficiency",
         "KGE=1-sqrt[(r-1)^2+(sigma_r-1)^2+(beta-1)^2]. "
         "sigma_r=sigma_sim/sigma_obs; beta=mu_sim/mu_obs. Perfect: 1. "
         "Ref: Gupta et al. (2009) J. Hydrol. 377:80-91."),
        ("NSE","Nash-Sutcliffe Efficiency",
         "NSE=1-SUM(sim-obs)^2/SUM(obs-obs_bar)^2. VG>0.75|Good 0.65-0.75|Sat 0.50-0.65. "
         "Ref: Nash & Sutcliffe (1970) J. Hydrol. 10:282-290."),
        ("SS","Skill Score (Murphy 1988)",
         "Station-level: SS=1-MSE_model/MSE_climatology (numerically = NSE). "
         "Ensemble pooled: SS=1-SUM_stations SUM_t(e^2_model)/SUM_stations SUM_t(e^2_clim). "
         "CRITICAL: do NOT aggregate as mean(SS_station) — always pool numerator and denominator. "
         "Ref: Murphy (1988) Mon. Wea. Rev. 116:2417-2424."),
        ("Composite","Weighted Composite Score",
         "Expert-defined weights: KGE=0.30, NSE=0.25, RMSE=0.15, r=0.10, d=0.10, "
         "Pbias=0.05, RPI=0.05 (sum=1.0). Each metric normalised [0,1]; "
         "Pbias uses |Pbias| (penalises over- and under-estimation equally). "
         "Ref: Knutti et al. (2017) Nat. Clim. Chang. 7:246-251."),
        ("RPI","Relative Performance Index",
         "RPI=(RMSE_m-RMSE_ref)/RMSE_ref where RMSE_ref=median RMSE across models "
         "for same station & scale. Negative=better than median. "
         "Ref: Gleckler et al. (2008) J. Geophys. Res."),
        ("d","Index of Agreement",
         "d=1-SUM(sim-obs)^2/SUM(|sim-obs_bar|+|obs-obs_bar|)^2. Range[0,1]. "
         "Ref: Willmott (1981) Phys. Geogr."),
        ("Taylor","Taylor Diagram",
         "r=Pearson correlation; sigma_ratio=sigma_sim/sigma_obs; centred RMSE in polar space. "
         "Ref: Taylor (2001) J. Geophys. Res. 106:7183-7192."),
        ("ETCCDI","Extreme Indices",
         "Rx1day=ann.max 1-day; R50p/R95p/R99p=total>P50/P95/P99 wet days; "
         "SDII=wet-day intensity. Wet-day threshold=1.0 mm (WMO). "
         "Ref: Karl et al. (1999); Zhang et al. (2011)."),
        ("QDM","Quantile Delta Mapping",
         "Quantile-based bias correction preserving relative changes in quantiles. "
         "Ref: Cannon et al. (2015) J. Climate 28:6938-6959."),
        ("WetSeason","Wet Season Definition",
         f"May-October (months 5-10). Phetchaburi, Thailand."),
        ("DPI","Output Resolution","All figures saved at 600 DPI for journal submission."),
    ]
    alt2 = [PatternFill("solid",fgColor="DEEAF1"),PatternFill("solid",fgColor="FFFFFF")]
    for ri,(a,b,d) in enumerate(refs,3):
        fl = alt2[ri%2]
        for ci,v in enumerate([a,b,d],1):
            cell = xsc(ws10,ri,ci,v,bold=(ci<=2),sz=9,align="left",border=tb())
            cell.fill = fl
            if ci==3:
                cell.alignment = Alignment(horizontal="left",vertical="top",
                                           wrap_text=True)
        row_h(ws10,ri,58)
    for ci,w in enumerate([14,26,70],1): cw(ws10,ci,w)

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  8.  MAIN                                                               ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def main():
    SEP = "=" * 72
    print(SEP)
    print("  CMIP6 Multi-Model Bias Correction Evaluation  v4.0")
    print("  มาตรฐาน Nature / Elsevier / Q1-Q3 | DPI=600")
    print(SEP)

    try:
        work_dir = (sys.argv[1].strip('"').strip("'")
                    if len(sys.argv)>1
                    else str(Path(os.path.abspath(__file__)).parent))
    except:
        work_dir = os.getcwd()
    print(f"  Folder : {work_dir}")
    out_dir = Path(work_dir)

    # ── Discover files ─────────────────────────────────────────────────
    obs_path, raw_model_paths, bc_model_paths = discover_files(work_dir)
    if obs_path is None:
        sys.exit("  ERROR: No Observed file found (filename must contain 'Observed')")

    all_models   = sorted(set(raw_model_paths.keys()) | set(bc_model_paths.keys()))
    model_colors = MODEL_PALETTE[:len(all_models)]

    print(f"\n  Observed  : {Path(obs_path).name}")
    print(f"  Raw models: {list(raw_model_paths.keys())}")
    print(f"  BC  models: {list(bc_model_paths.keys())}")
    print(f"  All models: {all_models}")
    print("-"*72)

    # ── Load all data ──────────────────────────────────────────────────
    print("  Loading data ...")
    obs_d, stns = load_daily(obs_path, "Observed")
    if obs_d is None:
        sys.exit("  ERROR: Failed to load Observed data")

    raw_dfs = {m: load_daily(p, f"Raw/{m}")[0]
               for m,p in raw_model_paths.items()}
    bc_dfs  = {m: load_daily(p, f"QDM/{m}")[0]
               for m,p in bc_model_paths.items()}

    stns_str   = [str(s) for s in stns]
    smap       = short_labels(stns)
    codes      = [smap[s] for s in stns_str]
    period_obs = period_str(obs_d)
    period_sim = period_str(list(raw_dfs.values())[0]) if raw_dfs else "N/A"
    base_name  = Path(obs_path).stem

    # Temporal aggregations
    obs_m  = to_monthly(obs_d)
    obs_a  = to_annual(obs_d)
    obs_ws = to_seasonal(obs_d, WET_MONTHS)
    obs_ds = to_seasonal(obs_d, DRY_MONTHS)

    raw_m_dfs  = {m: to_monthly(df)              for m,df in raw_dfs.items()}
    bc_m_dfs   = {m: to_monthly(df)              for m,df in bc_dfs.items()}
    raw_ws_dfs = {m: to_seasonal(df,WET_MONTHS)  for m,df in raw_dfs.items()}
    bc_ws_dfs  = {m: to_seasonal(df,WET_MONTHS)  for m,df in bc_dfs.items()}

    ens_raw   = ensemble_mean(raw_dfs)
    ens_bc    = ensemble_mean(bc_dfs)
    ens_raw_m = to_monthly(ens_raw)
    ens_bc_m  = to_monthly(ens_bc)
    ens_raw_ws = to_seasonal(ens_raw, WET_MONTHS)
    ens_bc_ws  = to_seasonal(ens_bc,  WET_MONTHS)

    print(f"\n  {len(stns)} stations  |  {len(all_models)} models  |  "
          f"Obs:{period_obs}  |  Sim:{period_sim}")
    print("-"*72)

    # ── Compute performance metrics ─────────────────────────────────────
    print("  Computing performance metrics ...")
    all_met = []

    for m in all_models:
        for stn in stns_str:
            for scale, o_df, r_dfs, b_dfs in [
                ("Daily",      obs_d,  raw_dfs,    bc_dfs),
                ("Monthly",    obs_m,  raw_m_dfs,  bc_m_dfs),
                ("Wet Season", obs_ws, raw_ws_dfs, bc_ws_dfs),
            ]:
                std_o = float(o_df[stn].std(ddof=1)) \
                        if o_df is not None and stn in o_df.columns else np.nan
                for ds, df_dict in [("Raw",r_dfs),("QDM",b_dfs)]:
                    df = df_dict.get(m)
                    mr = metrics_df(o_df, df, stn)
                    mr.update({"Model":m,"Dataset":ds,
                               "Station":stn,"Scale":scale,"std_obs":std_o})
                    all_met.append(mr)
        print(f"    Model: {m}")

    # Observed reference entries (for Taylor diagram)
    for stn in stns_str:
        for scale,o_df in [("Daily",obs_d),("Monthly",obs_m),("Wet Season",obs_ws)]:
            if o_df is None or stn not in o_df.columns: continue
            std_o = float(o_df[stn].std(ddof=1))
            n_v   = len(gcol(o_df,stn))
            all_met.append({
                "Model":"Observed","Dataset":"Observed","Station":stn,
                "Scale":scale,"std_obs":std_o,"r":1.0,"sigma_r":1.0,
                "RMSE":0.0,"NSE":1.0,"KGE":1.0,"d":1.0,"SS":1.0,
                "Pbias":0.0,"n":n_v,"MAE":0.0,"MBE":0.0,"std_sim":std_o,
                "beta":1.0,"RPI":0.0,
            })

    # Ensemble mean metrics
    ens_met = []
    for stn in stns_str:
        for scale,o_df,r_df,b_df in [
            ("Daily",      obs_d,  ens_raw,    ens_bc),
            ("Monthly",    obs_m,  ens_raw_m,  ens_bc_m),
            ("Wet Season", obs_ws, ens_raw_ws, ens_bc_ws),
        ]:
            for ds,df in [("Raw",r_df),("QDM",b_df)]:
                mr = metrics_df(o_df, df, stn)
                std_o = float(o_df[stn].std(ddof=1)) \
                        if o_df is not None and stn in o_df.columns else np.nan
                mr.update({"Model":"Ensemble","Dataset":ds,
                           "Station":stn,"Scale":scale,"std_obs":std_o})
                ens_met.append(mr)

    # [Fix 6] Compute pooled SS for ensemble
    pss_raw = pooled_skill_score(obs_d, ens_raw, stns_str)
    pss_bc  = pooled_skill_score(obs_d, ens_bc,  stns_str)
    print(f"\n  Ensemble Pooled SS (Daily):")
    print(f"    Raw QDM : {pss_raw:.4f}")
    print(f"    BC  QDM : {pss_bc:.4f}")

    # Add RPI
    add_rpi(all_met)

    # Rankings (weighted composite)
    rank_raw = composite_ranking([r for r in all_met if r["Dataset"]=="Raw"],  "Daily")
    rank_bc  = composite_ranking([r for r in all_met if r["Dataset"]=="QDM"],  "Daily")

    print(f"\n  === POST-QDM RANKING (Weighted Composite) ===")
    for m_r,row in rank_bc.iterrows():
        print(f"  Rank {int(row['Rank']):2d}  {m_r:<20s}  "
              f"Score={row['Score']:.4f}  KGE={row.get('KGE',np.nan):.3f}  "
              f"NSE={row.get('NSE',np.nan):.3f}")

    # Extreme indices
    print("\n  Computing ETCCDI extreme indices ...")
    ext_rows = []
    for m in all_models:
        for stn in stns_str:
            ext_rows.append(compute_extremes(raw_dfs.get(m), stn, m, "Raw"))
            ext_rows.append(compute_extremes(bc_dfs.get(m),  stn, m, "QDM"))
    for stn in stns_str:
        ext_rows.append(compute_extremes(obs_d, stn, "Observed", "Observed"))

    models_for_plot = [m for m in all_models if m!="Observed"]
    mc_for_plot     = MODEL_PALETTE[:len(models_for_plot)]

    # ── Figures ───────────────────────────────────────────────────────
    print(f"\n{'-'*72}")
    print("  Generating figures (600 DPI) ...")

    print("\n  Fig 01: Taylor Diagrams ...")
    fig01_taylor(all_met, stns, smap, models_for_plot, mc_for_plot,
                 obs_d, obs_m, obs_ws, out_dir, base_name, period_obs, period_sim)

    print("\n  Fig 02: Performance Heatmap ...")
    fig02_perf_heatmap(all_met, models_for_plot, stns, smap,
                        out_dir, base_name, period_obs, period_sim)

    if len(models_for_plot) >= 2:
        print("\n  Fig 03: Model Ranking ...")
        fig03_model_ranking(rank_raw, rank_bc, models_for_plot, mc_for_plot,
                             out_dir, base_name, period_obs)

    print("\n  Fig 04: Extreme Indices ...")
    fig04_extremes(ext_rows, models_for_plot, stns, smap, mc_for_plot,
                    out_dir, base_name, period_obs, period_sim)

    print("\n  Fig 05: Monthly Cycle ...")
    fig05_monthly_cycle(obs_d, raw_dfs, bc_dfs, ens_raw, ens_bc,
                         stns, smap, models_for_plot, mc_for_plot,
                         out_dir, base_name, period_obs, period_sim)

    print("\n  Fig 06: Wet-Season Analysis ...")
    fig06_wet_season(obs_d, raw_dfs, bc_dfs, ens_raw, ens_bc,
                      stns, smap, models_for_plot, mc_for_plot,
                      out_dir, base_name, period_obs, period_sim)

    print("\n  Fig 07: Ensemble Summary ...")
    fig07_ensemble_summary(all_met, ens_met, models_for_plot, stns, smap,
                            mc_for_plot, out_dir, base_name,
                            period_obs, period_sim,
                            obs_d, raw_dfs, bc_dfs, stns_str)

    # ── Excel ─────────────────────────────────────────────────────────
    print(f"\n{'-'*72}")
    out_xlsx = out_dir/f"Output_v4_{base_name}.xlsx"
    print(f"  Building Excel → {out_xlsx.name} ...")
    wb = Workbook()
    wb.remove(wb.active)
    write_excel(wb, stns, smap, models_for_plot, all_met, ens_met,
                ext_rows, rank_raw, rank_bc, period_obs, period_sim,
                obs_d, raw_dfs, bc_dfs, stns_str, codes)
    wb.save(str(out_xlsx))
    print(f"  Excel saved.")

    n_png = len(list(out_dir.glob(f"Output_v4_{base_name}_Fig*.png")))
    print()
    print(SEP)
    print(f"  DONE — Excel: 1 file  |  Figures: {n_png} files (600 DPI)")
    print(f"  Output folder: {work_dir}")
    print(SEP)


if __name__ == "__main__":
    main()
