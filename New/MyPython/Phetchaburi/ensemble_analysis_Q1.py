"""
===============================================================================
  Multi-Model Ensemble Analysis  — Version 3.0
  Observed vs Raw CMIP6 (per-model) vs Bias-Corrected/QDM (per-model)
  + Multi-Model Ensemble Mean
  Descriptive Statistics + Model Performance + Regional Average + Figures
  มาตรฐาน Nature / Elsevier / Q2
-------------------------------------------------------------------------------
  Changes v3.0:
    A. Province name extracted from filename suffix (e.g. "_Phetchaburi.csv")
    B. All filenames must share the SAME province suffix – validation check
    C. Figure titles: "Figure N." labels removed
    D. Figure 2 & 3: Station labels on X-axis, rotated 45°
    E. Excel Province column uses extracted province name
    F. NEW: Regional Average Comparison sheet
       - Average across ALL stations for each dataset
       - % Error Reduction table (QDM vs Raw)
       - Multi-model CMIP6 ranking by composite score
    G. Per-model Raw + BC analysis (not just single raw/bc pair)
    H. Output saved to timestamped subfolder
===============================================================================
"""

import os, sys, math, warnings, re
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from scipy import stats as sps

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker
import matplotlib.gridspec as gridspec
from matplotlib.lines  import Line2D
from matplotlib.colors import Normalize
import matplotlib.cm    as cm

from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils   import get_column_letter

warnings.filterwarnings("ignore")

# ═══════════════════════════════════════════════════════════════════════════
# 0.  GLOBAL STYLE
# ═══════════════════════════════════════════════════════════════════════════
FS = dict(title=14, label=12, tick=11, legend=11, annot=10, note=8)

plt.rcParams.update({
    "font.family":        "serif",
    "font.serif":         ["Times New Roman", "DejaVu Serif"],
    "font.size":          FS["label"],
    "axes.titlesize":     FS["title"],
    "axes.labelsize":     FS["label"],
    "xtick.labelsize":    FS["tick"],
    "ytick.labelsize":    FS["tick"],
    "legend.fontsize":    FS["legend"],
    "figure.titlesize":   FS["title"] + 1,
    "lines.linewidth":    1.8,
    "axes.linewidth":     0.9,
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.grid":          True,
    "grid.linestyle":     "--",
    "grid.linewidth":     0.4,
    "grid.alpha":         0.45,
    "grid.color":         "#B0BEC5",
    "savefig.dpi":        300,
    "savefig.bbox":       "tight",
    "savefig.pad_inches": 0.15,
    "figure.dpi":         120,
    "mathtext.fontset":   "stix",
})

C = dict(
    obs    = "#2C3E50",
    raw    = "#C0392B",
    bc     = "#2980B9",
    obs_lt = "#BDC3C7",
    raw_lt = "#F5B7B1",
    bc_lt  = "#AED6F1",
    green  = "#1E8449",
    gold   = "#D4AC0D",
    grey   = "#626567",
    ref    = "#566573",
)

DS_LABELS = ["Observed", "Raw CMIP6", "Bias-Corrected (QDM)"]
DS_COLORS = [C["obs"],   C["raw"],    C["bc"]]
DS_LT     = [C["obs_lt"],C["raw_lt"], C["bc_lt"]]

WET_THR = 1.0

# ── Excel colours ──────────────────────────────────────────────────────────
XC = dict(
    title="13293D", sub="1F4E79", hdr="2E75B6",
    obs_h="1B5E20", raw_h="B71C1C", bc_h="0D47A1",
    obs_r="E8F5E9", raw_r="FFEBEE", bc_r="E3F2FD",
    best="FFF9C4",  best_f="E65100",
    improve="C8E6C9", degrade="FFCCBC",
    note="ECEFF1",  white="FFFFFF",
    rank1="FFD700", rank2="C0C0C0", rank3="CD7F32",
    reg_hdr="1565C0", reg_r="E3F2FD",
)
THIN = Side(style="thin",   color="BDBDBD")
MED  = Side(style="medium", color="1F4E79")
def tb():       return Border(left=THIN, right=THIN, top=THIN,  bottom=THIN)
def tb_thick(): return Border(left=MED,  right=MED,  top=MED,   bottom=MED)
def xfill(h):   return PatternFill("solid", fgColor=h)

def xsc(ws, r, c, val=None, bold=False, italic=False,
        fc=None, bg=None, align="center", sz=10,
        num_fmt=None, wrap=True, border=None):
    cell = ws.cell(row=r, column=c)
    if val is not None: cell.value = val
    cell.font = Font(bold=bold, italic=italic, name="Calibri", size=sz,
                     color=fc if fc else "1A1A1A")
    cell.alignment = Alignment(horizontal=align, vertical="center",
                                wrap_text=wrap)
    if bg:     cell.fill = xfill(bg)
    if border: cell.border = border
    if num_fmt: cell.number_format = num_fmt
    return cell

def mxsc(ws, r, c1, c2, val, **kw):
    ws.merge_cells(start_row=r, start_column=c1, end_row=r, end_column=c2)
    return xsc(ws, r, c1, val, **kw)

def cw(ws, col, width):
    ws.column_dimensions[get_column_letter(col)].width = width

# ═══════════════════════════════════════════════════════════════════════════
# 1.  FILE DISCOVERY  (multi-model)
# ═══════════════════════════════════════════════════════════════════════════

def extract_province(fname):
    """Extract province from filename like 'xxx_Phetchaburi.csv' → 'Phetchaburi'"""
    m = re.search(r'_([A-Za-z][A-Za-z0-9]+)\.csv$', fname, re.IGNORECASE)
    return m.group(1) if m else None

def find_csvs_multi(folder):
    """
    Returns:
        obs_path  : str  – single Observed file
        raw_dict  : {model_name: path}  – raw CMIP6 per model
        bc_dict   : {model_name: path}  – bias-corrected per model
        province  : str
    """
    all_csv = sorted(Path(folder).glob("*.csv"))

    # collect province names from all files
    provinces = set()
    for f in all_csv:
        p = extract_province(f.name)
        if p:
            provinces.add(p)

    if len(provinces) == 0:
        sys.exit("  ✗  ไม่พบชื่อจังหวัดในชื่อไฟล์ CSV")
    if len(provinces) > 1:
        sys.exit(f"  ✗  ชื่อจังหวัดในไฟล์ไม่ตรงกัน: {provinces}\n"
                 "     ไฟล์ทั้งหมดต้องลงท้ายด้วยชื่อเดียวกัน")
    province = list(provinces)[0]
    print(f"  จังหวัด/พื้นที่ศึกษา: {province}")

    obs_files = [f for f in all_csv if "observed" in f.name.lower()]
    raw_files  = [f for f in all_csv if f.name.lower().startswith("pr_")]
    bc_files   = [f for f in all_csv if f.name.lower().startswith("bc_")]

    if not obs_files:
        sys.exit("  ✗  ไม่พบไฟล์ Observed")
    obs_path = str(obs_files[0])

    def model_name(fname):
        """Extract model name from filename, e.g. pr_day_CanESM5_... → CanESM5"""
        # Try pattern: pr_day_MODELNAME_...  or  bc_pr_day_MODELNAME_...
        m = re.search(r'(?:bc_)?pr_day_([^_]+)_', fname, re.IGNORECASE)
        if m: return m.group(1)
        # fallback: strip prefix/suffix
        stem = Path(fname).stem
        parts = stem.split("_")
        return parts[2] if len(parts) > 2 else stem

    raw_dict = {model_name(f.name): str(f) for f in raw_files}
    bc_dict  = {model_name(f.name): str(f) for f in bc_files}

    print(f"  Raw CMIP6 models : {list(raw_dict.keys())}")
    print(f"  BC/QDM models    : {list(bc_dict.keys())}")

    return obs_path, raw_dict, bc_dict, province

# ═══════════════════════════════════════════════════════════════════════════
# 2.  DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════
MISS = [-99, -999, -9999, -9.99e+20, 9.99e+20, 1e+20]

def load_daily(path, label):
    if path is None or not os.path.isfile(path):
        print(f"  ✗  ไม่พบ {label}"); return None, []
    df = pd.read_csv(path)
    for mv in MISS: df.replace(mv, np.nan, inplace=True)
    num = df.select_dtypes(include=[np.number]).columns
    df[num] = df[num].where(df[num] >= 0)
    stns = [c for c in df.columns if c not in ("YEAR","MONTH","DAY")]
    try:
        df["date"] = pd.to_datetime(
            {"year": df["YEAR"], "month": df["MONTH"], "day": df["DAY"]})
        df = df.set_index("date")[stns]
    except:
        df = df[stns]
    return df, stns

def to_monthly(d):
    if d is None: return None
    return d.resample("MS").apply(lambda g: g.sum(min_count=int(0.8*len(g))))

def gcol(df, stn):
    if df is None or stn not in df.columns: return np.array([], dtype=float)
    v = df[stn].values.astype(float)
    return v[~np.isnan(v) & (v >= 0)]

def wet_only(arr): return arr[arr >= WET_THR]

def period_str(df):
    if df is None: return "N/A"
    try: return f"{df.index[0].year}–{df.index[-1].year}"
    except: return "N/A"

def align_daily(df1, df2, stn):
    if df1 is None or df2 is None: return np.array([]), np.array([])
    if stn not in df1.columns or stn not in df2.columns:
        return np.array([]), np.array([])
    common = df1.index.intersection(df2.index)
    return (df1.loc[common, stn].values.astype(float),
            df2.loc[common, stn].values.astype(float))

# ═══════════════════════════════════════════════════════════════════════════
# 3.  STATISTICS
# ═══════════════════════════════════════════════════════════════════════════
LOWER_BETTER  = {"RMSE", "MAE", "MBE", "Pbias (%)"}
HIGHER_BETTER = {"r", "NSE", "KGE", "d (IoA)"}
RANK_METRICS  = ["RMSE", "MAE", "NSE", "KGE", "r", "d (IoA)", "Pbias (%)"]

def desc_stats(arr, label, stn, scale):
    v = arr[~np.isnan(arr)] if len(arr) else np.array([])
    if len(v) < 2:
        return {k: np.nan for k in
                ["Dataset","Station","Scale","N","Mean","Std","CV (%)","Min",
                 "P10","P25","P50","P75","P90","P95","P99","Max",
                 "Skewness","Kurtosis","Wet-day freq (%)"]}
    wet = wet_only(v) if scale == "Daily" else v[v > 0]
    return {
        "Dataset": label, "Station": stn, "Scale": scale,
        "N":               len(v),
        "Mean":            float(np.mean(v)),
        "Std":             float(np.std(v, ddof=1)),
        "CV (%)":          float(np.std(v,ddof=1)/np.mean(v)*100) if np.mean(v) else np.nan,
        "Min":             float(np.min(v)),
        "P10":             float(np.percentile(v,10)),
        "P25":             float(np.percentile(v,25)),
        "P50":             float(np.percentile(v,50)),
        "P75":             float(np.percentile(v,75)),
        "P90":             float(np.percentile(v,90)),
        "P95":             float(np.percentile(v,95)),
        "P99":             float(np.percentile(v,99)),
        "Max":             float(np.max(v)),
        "Skewness":        float(sps.skew(v)),
        "Kurtosis":        float(sps.kurtosis(v, fisher=True)),
        "Wet-day freq (%)": float(len(wet)/len(v)*100) if scale=="Daily" else np.nan,
    }

def perf_metrics(obs, sim, label, stn, scale):
    def _empty():
        return {k: np.nan for k in
                ["Dataset","Station","Scale","N_pairs",
                 "RMSE","MAE","MBE","Pbias (%)","r","NSE","KGE",
                 "KGE_r","KGE_alpha","KGE_beta","d (IoA)"]}
    if hasattr(obs, "index") and hasattr(sim, "index"):
        common = obs.index.intersection(sim.index)
        o = obs.reindex(common).values.astype(float)
        s = sim.reindex(common).values.astype(float)
    else:
        n  = min(len(obs), len(sim))
        o, s = np.asarray(obs[:n], float), np.asarray(sim[:n], float)
    mask = ~np.isnan(o) & ~np.isnan(s)
    o, s = o[mask], s[mask]
    if len(o) < 5: return _empty()
    res   = s - o
    rmse  = float(np.sqrt(np.mean(res**2)))
    mae   = float(np.mean(np.abs(res)))
    mbe   = float(np.mean(res))
    pbias = float(100*np.sum(res)/np.sum(o)) if np.sum(o) else np.nan
    r_val = float(np.corrcoef(o, s)[0,1])
    d_nse = np.sum((o - np.mean(o))**2)
    nse   = float(1 - np.sum(res**2)/d_nse) if d_nse else np.nan
    alpha = float(np.std(s,ddof=1)/np.std(o,ddof=1)) if np.std(o,ddof=1) else np.nan
    beta  = float(np.mean(s)/np.mean(o)) if np.mean(o) else np.nan
    kge   = float(1 - math.sqrt((r_val-1)**2+(alpha-1)**2+(beta-1)**2)) \
            if not (np.isnan(alpha) or np.isnan(beta)) else np.nan
    d_ioa = np.sum((np.abs(s-np.mean(o))+np.abs(o-np.mean(o)))**2)
    ioa   = float(1 - np.sum(res**2)/d_ioa) if d_ioa else np.nan
    return {"Dataset":label, "Station":stn, "Scale":scale, "N_pairs":len(o),
            "RMSE":round(rmse,3), "MAE":round(mae,3), "MBE":round(mbe,3),
            "Pbias (%)":round(pbias,2), "r":round(r_val,4),
            "NSE":round(float(nse),4), "KGE":round(float(kge),4),
            "KGE_r":round(r_val,4), "KGE_alpha":round(float(alpha),4),
            "KGE_beta":round(float(beta),4), "d (IoA)":round(float(ioa),4)}

def improvement_rows(raw_list, bc_list):
    out = []
    for m in RANK_METRICS:
        rv = [x[m] for x in raw_list if not (isinstance(x[m],float) and np.isnan(x[m]))]
        bv = [x[m] for x in bc_list  if not (isinstance(x[m],float) and np.isnan(x[m]))]
        if not rv or not bv: continue
        rm, bm = float(np.mean(rv)), float(np.mean(bv))
        abs_i  = (abs(rm)-abs(bm)) if m in LOWER_BETTER else (bm-rm)
        rel_i  = abs_i/abs(rm)*100 if rm!=0 else np.nan
        direction = "Improved" if abs_i > 0 else "Degraded"
        best_stn, best_val = "—", np.nan
        for rr, bb in zip(raw_list, bc_list):
            if rr["Station"] != bb["Station"]: continue
            rv1, bv1 = rr[m], bb[m]
            if np.isnan(rv1) or np.isnan(bv1): continue
            imp1 = (abs(rv1)-abs(bv1)) if m in LOWER_BETTER else (bv1-rv1)
            if np.isnan(best_val) or imp1 > best_val:
                best_val, best_stn = imp1, rr["Station"]
        out.append({
            "Metric":              m,
            "Raw CMIP6 (Avg)":     round(rm,4),
            "QDM Corrected (Avg)": round(bm,4),
            "Abs Improvement":     round(abs_i,4),
            "% Improvement":       round(rel_i,2) if not np.isnan(rel_i) else np.nan,
            "Direction":           direction,
            "Best Station":        best_stn,
        })
    return out

def compute_ranking(raw_rows, bc_rows):
    rows = []
    for label, lst in [("Raw CMIP6",raw_rows),("Bias-Corrected (QDM)",bc_rows)]:
        row = {"Model": label}
        for m in RANK_METRICS:
            vals = [x[m] for x in lst
                    if not (isinstance(x[m],float) and np.isnan(x[m]))]
            row[m] = float(np.mean(vals)) if vals else np.nan
        rows.append(row)
    df = pd.DataFrame(rows).set_index("Model")
    score = pd.DataFrame(index=df.index, columns=RANK_METRICS, dtype=float)
    for m in RANK_METRICS:
        vals = df[m].values.astype(float)
        rng  = np.nanmax(vals) - np.nanmin(vals)
        if rng == 0: score[m] = 1.0
        elif m in LOWER_BETTER:
            score[m] = (np.nanmax(vals)-vals)/rng
        else:
            score[m] = (vals-np.nanmin(vals))/rng
    df["Composite Score"] = score.mean(axis=1)
    df["Rank"] = df["Composite Score"].rank(ascending=False).astype(int)
    return df

def compute_model_ranking(model_perf_dict):
    """
    model_perf_dict: {model_name: {"raw": [perf_rows], "bc": [perf_rows]}}
    Returns DataFrame ranked by composite score (QDM performance).
    """
    rows = []
    for model, d in model_perf_dict.items():
        # Use BC performance for ranking
        for prefix, lst in [("Raw", d["raw"]), ("QDM", d["bc"])]:
            row = {"Model": model, "Type": prefix}
            for m in RANK_METRICS:
                vals = [x[m] for x in lst
                        if not (isinstance(x[m],float) and np.isnan(x[m]))]
                row[m] = float(np.mean(vals)) if vals else np.nan
            rows.append(row)
    df = pd.DataFrame(rows)

    # Score each model's QDM performance
    qdf = df[df["Type"]=="QDM"].copy().set_index("Model")
    score_cols = {m: np.nan for m in RANK_METRICS}
    for m in RANK_METRICS:
        vals = qdf[m].values.astype(float)
        rng  = np.nanmax(vals) - np.nanmin(vals) if len(vals) > 1 else 0
        if rng == 0:
            qdf[f"score_{m}"] = 1.0
        elif m in LOWER_BETTER:
            qdf[f"score_{m}"] = (np.nanmax(vals)-vals)/rng
        else:
            qdf[f"score_{m}"] = (vals-np.nanmin(vals))/rng
    score_cols_names = [f"score_{m}" for m in RANK_METRICS]
    qdf["Composite Score (QDM)"] = qdf[score_cols_names].mean(axis=1)
    qdf["Rank (QDM)"] = qdf["Composite Score (QDM)"].rank(ascending=False).astype(int)

    # Also rank raw
    rdf = df[df["Type"]=="Raw"].copy().set_index("Model")
    for m in RANK_METRICS:
        vals = rdf[m].values.astype(float)
        rng  = np.nanmax(vals) - np.nanmin(vals) if len(vals) > 1 else 0
        if rng == 0:
            rdf[f"score_{m}"] = 1.0
        elif m in LOWER_BETTER:
            rdf[f"score_{m}"] = (np.nanmax(vals)-vals)/rng
        else:
            rdf[f"score_{m}"] = (vals-np.nanmin(vals))/rng
    rdf["Composite Score (Raw)"] = rdf[score_cols_names].mean(axis=1)
    rdf["Rank (Raw)"] = rdf["Composite Score (Raw)"].rank(ascending=False).astype(int)

    return df, qdf, rdf

# ═══════════════════════════════════════════════════════════════════════════
# 4.  REGIONAL AVERAGE COMPUTATION
# ═══════════════════════════════════════════════════════════════════════════

def compute_regional_avg(df_dict, stns):
    """
    df_dict: {label: dataframe}
    Returns dict {label: regional_mean_series}
    """
    result = {}
    for label, df in df_dict.items():
        if df is None: continue
        valid_stns = [s for s in stns if s in df.columns]
        if not valid_stns: continue
        result[label] = df[valid_stns].mean(axis=1)
    return result

def regional_perf(obs_reg, sim_reg_dict, stns, scale):
    """Compute performance for regional average time series."""
    rows = []
    for label, sim_s in sim_reg_dict.items():
        common = obs_reg.index.intersection(sim_s.index)
        o = obs_reg.reindex(common).values.astype(float)
        s = sim_s.reindex(common).values.astype(float)
        mask = ~np.isnan(o) & ~np.isnan(s)
        o, s = o[mask], s[mask]
        if len(o) < 5:
            rows.append({"Dataset": label, "Station": "Regional Avg",
                         "Scale": scale})
            continue
        rows.append(perf_metrics(o, s, label, "Regional Avg", scale))
    return rows

def error_reduction_table(raw_rows_list, bc_rows_list):
    """
    Compute % error reduction for each metric, multi-model ensemble.
    raw_rows_list, bc_rows_list: flat lists of perf dicts for ALL stations ALL models.
    """
    out = []
    for m in RANK_METRICS:
        rv = [x[m] for x in raw_rows_list
              if not (isinstance(x.get(m, np.nan), float) and np.isnan(x.get(m, np.nan)))]
        bv = [x[m] for x in bc_rows_list
              if not (isinstance(x.get(m, np.nan), float) and np.isnan(x.get(m, np.nan)))]
        if not rv or not bv: continue
        rm, bm = float(np.mean(rv)), float(np.mean(bv))
        abs_i  = (abs(rm)-abs(bm)) if m in LOWER_BETTER else (bm-rm)
        rel_i  = abs_i/abs(rm)*100 if rm!=0 else np.nan
        direction = "Improved" if abs_i > 0 else "Degraded"
        # narrative
        if m in LOWER_BETTER:
            narrative = (f"QDM reduced {m} by {rel_i:.1f}% "
                         f"(from {rm:.3f} to {bm:.3f})"
                         if not np.isnan(rel_i) else "N/A")
        else:
            narrative = (f"QDM increased {m} by {rel_i:.1f}% "
                         f"(from {rm:.3f} to {bm:.3f})"
                         if not np.isnan(rel_i) else "N/A")
        out.append({
            "Metric":              m,
            "Raw CMIP6 Ensemble": round(rm,4),
            "QDM Ensemble":        round(bm,4),
            "Abs Improvement":     round(abs_i,4),
            "% Error Reduction":   round(rel_i,2) if not np.isnan(rel_i) else np.nan,
            "Direction":           direction,
            "Summary Statement":   narrative,
        })
    return out

# ═══════════════════════════════════════════════════════════════════════════
# 5.  HELPER
# ═══════════════════════════════════════════════════════════════════════════

def short_labels(stns):
    return {str(s): f"S{i+1}" for i, s in enumerate(stns)}

MODEL_COLORS = [
    "#E63946","#2A9D8F","#E9C46A","#264653","#9B5DE5",
    "#F4A261","#43AA8B","#577590","#F72585","#480CA8",
]

# ═══════════════════════════════════════════════════════════════════════════
# 6.  FIGURE 1 – BOXPLOT DESC
# ═══════════════════════════════════════════════════════════════════════════

def fig_boxplot_desc(desc_daily_raw_data, stns, smap,
                     period_obs, period_sim, province, out_path):
    n    = len(stns)
    fig  = plt.figure(figsize=(18, 12))
    gs   = gridspec.GridSpec(3, 2, figure=fig, hspace=0.55, wspace=0.32,
                             top=0.91, bottom=0.09, left=0.06, right=0.97)
    BP_KW = dict(
        patch_artist=True, widths=0.22, notch=False,
        medianprops=dict(linewidth=2.2, color="black"),
        whiskerprops=dict(linewidth=1.0),
        capprops=dict(linewidth=1.2),
        flierprops=dict(marker="o", markersize=2, alpha=0.35, linestyle="none"),
        boxprops=dict(linewidth=0.7),
        showfliers=True,
    )
    fill_cols = [C["obs_lt"], C["raw_lt"], C["bc_lt"]]
    edge_cols = [C["obs"],    C["raw"],    C["bc"]]

    def draw_bp(ax, arrays_per_stn, ylabel, title_str, log=False):
        offsets = [-0.25, 0, 0.25]
        for si, (obs_a, raw_a, bc_a) in enumerate(arrays_per_stn):
            for di, arr in enumerate([obs_a, raw_a, bc_a]):
                arr = arr[~np.isnan(arr)]
                arr = arr[arr > 0] if log else arr
                if len(arr) < 4: continue
                pos = si + offsets[di]
                bp  = ax.boxplot([arr], positions=[pos], **BP_KW)
                bp["boxes"][0].set_facecolor(fill_cols[di])
                bp["boxes"][0].set_edgecolor(edge_cols[di])
                for wh in bp["whiskers"]: wh.set_color(edge_cols[di])
                for cp in bp["caps"]:     cp.set_color(edge_cols[di])
                for fl in bp["fliers"]:
                    fl.set_markerfacecolor(edge_cols[di])
                    fl.set_markeredgecolor(edge_cols[di])
        ax.set_xlim(-0.6, n - 0.4)
        ax.set_xticks(range(n))
        ax.set_xticklabels([smap[str(s)] for s in stns],
                           rotation=45, ha="right", fontsize=FS["tick"])
        ax.set_ylabel(ylabel, fontsize=FS["label"])
        ax.set_title(title_str, loc="left", fontsize=FS["title"],
                     fontweight="bold", pad=5)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        if log: ax.set_yscale("log")
        ax.set_ylim(bottom=0 if not log else None)

    def draw_bar_metric(ax, metric_key, ylabel, title_str, desc_daily):
        x  = np.arange(n)
        bw = 0.26
        for di, (lbl, col, lt) in enumerate(zip(DS_LABELS, edge_cols, fill_cols)):
            vals = []
            for stn in stns:
                sub = [r for r in desc_daily
                       if r["Station"]==str(stn) and r["Dataset"]==lbl]
                vals.append(sub[0][metric_key] if sub else np.nan)
            ax.bar(x+(di-1)*bw, vals, width=bw, color=lt, edgecolor=col,
                   linewidth=0.8, alpha=0.85, label=lbl, zorder=3)
        ax.set_xlim(-0.6, n-0.4); ax.set_xticks(x)
        ax.set_xticklabels([smap[str(s)] for s in stns],
                           rotation=45, ha="right", fontsize=FS["tick"])
        ax.set_ylabel(ylabel, fontsize=FS["label"])
        ax.set_title(title_str, loc="left", fontsize=FS["title"],
                     fontweight="bold", pad=5)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.set_ylim(bottom=0)

    def stn_arrays(_):
        return [(desc_daily_raw_data[str(s)]["obs"],
                 desc_daily_raw_data[str(s)]["raw"],
                 desc_daily_raw_data[str(s)]["bc"]) for s in stns]

    ax_a = fig.add_subplot(gs[0,0])
    draw_bp(ax_a, stn_arrays("daily_all"),
            "Daily Rainfall (mm)", "(a)  All-Day Daily Distribution")

    ax_b = fig.add_subplot(gs[0,1])
    draw_bp(ax_b, stn_arrays("daily_wet"),
            "Daily Rainfall (mm)  [log scale]",
            "(b)  Wet-Day Distribution  (≥1 mm)", log=True)

    ax_c = fig.add_subplot(gs[1,0])
    draw_bp(ax_c, stn_arrays("monthly"),
            "Monthly Rainfall (mm)", "(c)  Monthly Rainfall Distribution")

    desc_daily_list = []
    for stn in stns:
        d = desc_daily_raw_data[str(stn)]
        for lbl, arr in zip(DS_LABELS, [d["obs"],d["raw"],d["bc"]]):
            desc_daily_list.append(desc_stats(arr, lbl, str(stn), "Daily"))

    ax_d = fig.add_subplot(gs[1,1])
    draw_bar_metric(ax_d, "CV (%)", "Coefficient of Variation (%)",
                    "(d)  CV of Daily Rainfall", desc_daily_list)

    ax_e = fig.add_subplot(gs[2,0])
    draw_bar_metric(ax_e, "Skewness", "Skewness (Fisher–Pearson)",
                    "(e)  Skewness of Daily Rainfall", desc_daily_list)

    ax_f = fig.add_subplot(gs[2,1])
    draw_bar_metric(ax_f, "Wet-day freq (%)", "Wet-day Frequency (%)",
                    f"(f)  Wet-day Frequency  (≥{WET_THR} mm)",
                    desc_daily_list)

    handles = [mpatches.Patch(facecolor=lt, edgecolor=col, linewidth=0.8,
                               alpha=0.85, label=lbl)
               for lbl, col, lt in zip(DS_LABELS, edge_cols, fill_cols)]
    fig.legend(handles=handles, loc="lower center", ncol=3,
               fontsize=FS["legend"], frameon=True, edgecolor="#B0BEC5",
               bbox_to_anchor=(0.5,-0.01), handlelength=2.0, handleheight=1.2)

    fig.suptitle(
        f"Rainfall Distribution Comparison — Daily & Monthly Scale\n"
        f"Observed vs Raw CMIP6 vs Bias-Corrected (QDM)  "
        f"│  {province}  │  Obs: {period_obs}  │  Sim: {period_sim}",
        fontsize=FS["title"]+1, fontweight="bold")

    plt.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")

# ═══════════════════════════════════════════════════════════════════════════
# 7.  FIGURE 2 & 3 – PERFORMANCE METRICS  (shared X-axis, fixed labels)
# ═══════════════════════════════════════════════════════════════════════════

def fig_performance(raw_rows, bc_rows, stns, smap, scale, title_suffix,
                    out_path, period_obs, period_sim, province):
    metrics = [
        ("RMSE (mm)",   "RMSE",      False, None),
        ("NSE",         "NSE",        True,  (0.50,0.65,0.75)),
        ("KGE",         "KGE",        True,  None),
        ("r (Pearson)", "r",          True,  None),
        ("Pbias (%)",   "Pbias (%)", False,  None),
        ("d (IoA)",     "d (IoA)",    True,  None),
    ]
    n  = len(stns)
    x  = np.arange(n)
    bw = 0.35

    def get_v(rows, stn, key):
        sub = [r for r in rows if r["Station"]==str(stn)]
        return sub[0][key] if sub else np.nan

    fig, axes = plt.subplots(3, 2, figsize=(18, 13))
    fig.subplots_adjust(hspace=0.55, wspace=0.30,
                        left=0.06, right=0.97, top=0.91, bottom=0.13)

    for ai, (ylabel, key, higher, nse_thrs) in enumerate(metrics):
        row, col = divmod(ai, 2)
        ax = axes[row, col]

        rv = np.array([get_v(raw_rows, s, key) for s in stns], dtype=float)
        bv = np.array([get_v(bc_rows,  s, key) for s in stns], dtype=float)

        ax.bar(x - bw/2, rv, width=bw,
               color=C["raw_lt"], edgecolor=C["raw"], linewidth=0.8,
               alpha=0.85, zorder=3, label="Raw CMIP6")
        ax.bar(x + bw/2, bv, width=bw,
               color=C["bc_lt"],  edgecolor=C["bc"],  linewidth=0.8,
               alpha=0.85, zorder=3, label="Bias-Corrected (QDM)")

        if key in ("NSE","KGE","r","d (IoA)"):
            ax.axhline(1.0, color=C["green"], lw=0.9, ls=":", alpha=0.7)
        if key == "Pbias (%)":
            ax.axhline(0.0, color=C["green"], lw=0.9, ls=":", alpha=0.7)
        if nse_thrs:
            for thr, lbl, _ in zip(nse_thrs,
                                    ["Sat.","Good","V. Good"],
                                    ["#F0E6FF","#FFF9C4","#C8E6C9"]):
                ax.axhline(thr, color="#9E9E9E", lw=0.7, ls="--", alpha=0.55)
                ax.text(n-0.5, thr+0.01, lbl,
                        fontsize=8, color="#757575", va="bottom")

        # ── X-axis: always show station labels rotated 45° ──
        ax.set_xticks(x)
        ax.set_xticklabels([smap[str(s)] for s in stns],
                           rotation=45, ha="right", fontsize=FS["tick"])
        ax.set_xlabel("Station", fontsize=FS["label"])
        ax.set_ylabel(ylabel, fontsize=FS["label"])
        ax.set_title(f"({chr(97+ai)})  {ylabel}",
                     loc="left", fontsize=FS["title"]-1,
                     fontweight="bold", pad=4)
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    handles = [
        mpatches.Patch(facecolor=C["raw_lt"], edgecolor=C["raw"],
                       linewidth=0.8, alpha=0.85, label="Raw CMIP6"),
        mpatches.Patch(facecolor=C["bc_lt"],  edgecolor=C["bc"],
                       linewidth=0.8, alpha=0.85, label="Bias-Corrected (QDM)"),
        Line2D([0],[0], color=C["green"], lw=0.9, ls=":", label="Perfect / Optimal"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=3,
               fontsize=FS["legend"], frameon=True, edgecolor="#B0BEC5",
               bbox_to_anchor=(0.5,-0.01), handlelength=2.0)

    fig.suptitle(
        f"Model Performance Metrics — {scale} Scale\n"
        f"Raw CMIP6 vs Bias-Corrected (QDM)  "
        f"│  {province}  │  Obs: {period_obs}  │  Sim: {period_sim}",
        fontsize=FS["title"]+1, fontweight="bold")

    plt.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")

# ═══════════════════════════════════════════════════════════════════════════
# 8.  FIGURE 4 – RANKING + RADAR
# ═══════════════════════════════════════════════════════════════════════════

def fig_ranking(imp_daily, imp_monthly, rank_df, out_path,
                period_obs, province):
    fig = plt.figure(figsize=(18, 7.5))
    fig.subplots_adjust(left=0.05, right=0.97, top=0.88,
                        bottom=0.14, wspace=0.32)
    ax1 = fig.add_subplot(1, 2, 1)
    ax2 = fig.add_subplot(1, 2, 2, polar=True)

    imp_d_d = {r["Metric"]: r for r in imp_daily}
    imp_m_d = {r["Metric"]: r for r in imp_monthly}
    metrics  = [m for m in RANK_METRICS if m in imp_d_d]
    x        = np.arange(len(metrics))
    bw       = 0.35

    vals_d = [imp_d_d.get(m,{}).get("% Improvement", np.nan) for m in metrics]
    vals_m = [imp_m_d.get(m,{}).get("% Improvement", np.nan) for m in metrics]

    b1 = ax1.bar(x-bw/2, vals_d, width=bw,
                 color=C["bc_lt"], edgecolor=C["bc"], linewidth=0.9,
                 alpha=0.85, label="Daily", zorder=3)
    b2 = ax1.bar(x+bw/2, vals_m, width=bw,
                 color="#FFD180", edgecolor=C["gold"], linewidth=0.9,
                 alpha=0.85, label="Monthly", zorder=3)
    ax1.axhline(0, color=C["grey"], lw=0.8, ls="--", alpha=0.7, zorder=2)

    for bars, vals, col in [(b1,vals_d,C["bc"]),(b2,vals_m,C["gold"])]:
        for bar, v in zip(bars, vals):
            if not np.isnan(v):
                va = "bottom" if v >= 0 else "top"
                dy = 0.8 if v >= 0 else -0.8
                ax1.text(bar.get_x()+bar.get_width()/2, v+dy,
                         f"{v:+.1f}%", ha="center", va=va,
                         fontsize=FS["annot"]-1, fontweight="bold", color=col)

    ax1.set_xticks(x)
    ax1.set_xticklabels(metrics, fontsize=FS["tick"], rotation=30, ha="right")
    ax1.set_ylabel("Relative Improvement (%)", fontsize=FS["label"])
    ax1.set_title(
        "(a)  QDM Bias Correction — Improvement over Raw CMIP6\n"
        "      (positive = improved; dashed = no change)",
        loc="left", fontsize=FS["title"]-1, fontweight="bold", pad=5)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1.legend(fontsize=FS["legend"], frameon=True,
               edgecolor="#B0BEC5", loc="upper right")

    n_met  = len(RANK_METRICS)
    angles = np.linspace(0, 2*np.pi, n_met, endpoint=False).tolist()
    angles += angles[:1]

    def norm_score(model):
        row = rank_df.loc[model]
        out = []
        for m in RANK_METRICS:
            v    = float(row.get(m, np.nan))
            allv = rank_df[m].values.astype(float)
            rng  = np.nanmax(allv) - np.nanmin(allv)
            if np.isnan(v) or rng == 0:
                out.append(0.5)
            elif m in LOWER_BETTER:
                out.append((np.nanmax(allv) - v) / rng)
            else:
                out.append((v - np.nanmin(allv)) / rng)
        out += out[:1]
        return out

    raw_scores = norm_score("Raw CMIP6")
    bc_scores  = norm_score("Bias-Corrected (QDM)")
    ax2.fill(angles, raw_scores, color=C["raw"], alpha=0.18)
    ax2.plot(angles, raw_scores, color=C["raw"], lw=1.8, ls="--",
             label="Raw CMIP6")
    ax2.fill(angles, bc_scores, color=C["bc"], alpha=0.30)
    ax2.plot(angles, bc_scores, color=C["bc"], lw=2.4, ls="-",
             label="Bias-Corrected (QDM)")

    ax2.set_thetagrids(np.degrees(angles[:-1]), RANK_METRICS,
                        fontsize=FS["tick"]+1)
    ax2.set_ylim(0, 1)
    ax2.set_yticks([0.25, 0.50, 0.75, 1.00])
    ax2.set_yticklabels(["0.25","0.50","0.75","1.00"],
                         fontsize=FS["annot"]-1, color="#78909C")
    ax2.set_title(
        "(b)  Normalised Performance Radar\n"
        "      (outer = better; QDM vs Raw CMIP6)",
        fontsize=FS["title"]-1, fontweight="bold", pad=18)
    ax2.legend(loc="lower right", bbox_to_anchor=(1.40,-0.12),
               fontsize=FS["legend"], frameon=True, edgecolor="#B0BEC5")
    ax2.grid(True, lw=0.5, alpha=0.55)

    for model, col in [("Raw CMIP6",C["raw"]),("Bias-Corrected (QDM)",C["bc"])]:
        cs = rank_df.loc[model,"Composite Score"]
        rk = int(rank_df.loc[model,"Rank"])
        ax2.text(0.02, 1.0-0.10*rk,
                 f"Rank {rk}: {model}\n  Composite Score = {cs:.4f}",
                 transform=ax2.transAxes,
                 fontsize=FS["annot"]-1, color=col, fontweight="bold",
                 bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                           edgecolor=col, linewidth=0.8, alpha=0.90))

    fig.suptitle(
        f"Model Ranking & Performance Improvement Summary\n"
        f"{province}  │  Obs: {period_obs}",
        fontsize=FS["title"]+1, fontweight="bold")

    plt.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")

# ═══════════════════════════════════════════════════════════════════════════
# 9.  FIGURE 5 – HEATMAP
# ═══════════════════════════════════════════════════════════════════════════

def fig_heatmap(raw_rows, bc_rows, stns, smap, out_path,
                period_obs, period_sim, province):
    show_annot = len(stns) <= 12
    metrics    = [("NSE",    (-0.5,1.0), "RdYlGn"),
                  ("KGE",    (-0.5,1.0), "RdYlGn"),
                  ("r",      (0.0, 1.0), "YlGn"),
                  ("d (IoA)",(0.0, 1.0), "YlGn")]
    n_met = len(metrics)
    n_stn = len(stns)
    stn_lbls = [smap[str(s)] for s in stns]

    fig, axes = plt.subplots(2, n_met, figsize=(n_met*4.2+1, 8.5),
                              gridspec_kw={"hspace":0.55,"wspace":0.25})
    fig.subplots_adjust(left=0.06, right=0.97, top=0.88, bottom=0.14)

    for di, (ds_label, row_list) in enumerate([
        ("Raw CMIP6",           raw_rows),
        ("Bias-Corrected (QDM)", bc_rows),
    ]):
        for mi, (met, (vmin,vmax), cmap_name) in enumerate(metrics):
            ax = axes[di, mi]
            vals = np.array(
                [next((r[met] for r in row_list if r["Station"]==str(s)),
                       np.nan) for s in stns],
                dtype=float).reshape(1,-1)
            im = ax.imshow(vals, aspect="auto",
                           cmap=plt.get_cmap(cmap_name),
                           norm=Normalize(vmin=vmin, vmax=vmax),
                           interpolation="nearest")
            cb = plt.colorbar(im, ax=ax, orientation="horizontal",
                              pad=0.22, fraction=0.07, shrink=0.85)
            cb.ax.tick_params(labelsize=FS["annot"]-1)
            cb.set_label(f"{met}", fontsize=FS["annot"])
            if show_annot:
                for ci, v in enumerate(vals[0]):
                    if not np.isnan(v):
                        txt_col = "white" if v < vmin+0.25*(vmax-vmin) else "black"
                        ax.text(ci, 0, f"{v:.3f}", ha="center", va="center",
                                fontsize=FS["annot"]+1, fontweight="bold",
                                color=txt_col)
            ax.set_xticks(range(n_stn))
            ax.set_xticklabels(stn_lbls, rotation=45, ha="right",
                               fontsize=FS["tick"])
            ax.set_yticks([])
            ds_short = "Raw" if "Raw" in ds_label else "QDM"
            ax.set_title(f"{ds_short} — {met}",
                         fontsize=FS["title"]-2, fontweight="bold", pad=4)

    for di, lbl in enumerate(["Raw CMIP6", "Bias-Corrected (QDM)"]):
        col = C["raw"] if "Raw" in lbl else C["bc"]
        axes[di,0].set_ylabel(lbl, fontsize=FS["label"],
                               fontweight="bold", color=col, labelpad=6)

    nse_patches = [
        mpatches.Patch(color="#4CAF50", label="Very Good  (NSE > 0.75)"),
        mpatches.Patch(color="#CDDC39", label="Good  (0.65–0.75)"),
        mpatches.Patch(color="#FFC107", label="Satisfactory  (0.50–0.65)"),
        mpatches.Patch(color="#F44336", label="Unsatisfactory  (< 0.50)"),
    ]
    fig.legend(handles=nse_patches, loc="lower center", ncol=4,
               fontsize=FS["legend"]-1, frameon=True, edgecolor="#B0BEC5",
               bbox_to_anchor=(0.5,-0.02), handlelength=1.6)

    fig.suptitle(
        f"Performance Metrics Heatmap — All Stations\n"
        f"Raw CMIP6 (top) vs Bias-Corrected/QDM (bottom)  "
        f"│  Daily Scale  │  {province}  │  Obs: {period_obs}",
        fontsize=FS["title"]+1, fontweight="bold")

    plt.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")

# ═══════════════════════════════════════════════════════════════════════════
# 10.  FIGURE 6 – MULTI-MODEL CMIP6 RANKING (QDM performance)
# ═══════════════════════════════════════════════════════════════════════════

def fig_model_ranking(model_perf_dict, out_path, period_obs, province):
    """
    Bar chart + radar showing per-model composite scores (QDM performance)
    and raw vs QDM improvement per model.
    """
    models = list(model_perf_dict.keys())
    n_models = len(models)
    if n_models == 0: return

    # compute composite scores per model
    def model_avg(model, key, mtype="bc"):
        lst = model_perf_dict[model][mtype]
        vals = [x[key] for x in lst
                if not (isinstance(x.get(key,np.nan), float) and np.isnan(x.get(key,np.nan)))]
        return float(np.mean(vals)) if vals else np.nan

    # build summary matrix
    raw_means = {m: {k: model_avg(m,k,"raw") for k in RANK_METRICS} for m in models}
    bc_means  = {m: {k: model_avg(m,k,"bc")  for k in RANK_METRICS} for m in models}

    # composite score for QDM
    scores = {}
    for model in models:
        vals_all = {k: bc_means[model][k] for k in RANK_METRICS}
        # normalise across models
        sc = []
        for k in RANK_METRICS:
            all_v = [bc_means[m][k] for m in models
                     if not np.isnan(bc_means[m].get(k,np.nan))]
            if not all_v or np.isnan(vals_all[k]):
                sc.append(0.5); continue
            mn, mx = min(all_v), max(all_v)
            rng = mx - mn
            v = vals_all[k]
            if rng == 0: sc.append(1.0)
            elif k in LOWER_BETTER: sc.append((mx-v)/rng)
            else: sc.append((v-mn)/rng)
        scores[model] = float(np.mean(sc))

    sorted_models = sorted(scores, key=lambda m: scores[m], reverse=True)
    cols = [MODEL_COLORS[i % len(MODEL_COLORS)] for i in range(n_models)]

    fig = plt.figure(figsize=(18, 8))
    fig.subplots_adjust(left=0.06, right=0.97, top=0.88,
                        bottom=0.14, wspace=0.35)
    ax1 = fig.add_subplot(1, 2, 1)
    ax2 = fig.add_subplot(1, 2, 2, polar=True)

    # ── Panel A: composite score bar ──────────────────────────────────
    x      = np.arange(n_models)
    c_vals = [scores[m] for m in sorted_models]
    bars   = ax1.bar(x, c_vals, color=[MODEL_COLORS[i%len(MODEL_COLORS)]
                                        for i in range(n_models)],
                     edgecolor="white", linewidth=0.8, zorder=3, alpha=0.88)
    for bar, v in zip(bars, c_vals):
        ax1.text(bar.get_x()+bar.get_width()/2, v+0.01,
                 f"{v:.3f}", ha="center", va="bottom",
                 fontsize=FS["annot"], fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(sorted_models, rotation=30, ha="right",
                         fontsize=FS["tick"]+1)
    ax1.set_ylim(0, 1.05)
    ax1.set_ylabel("Composite Score (0=worst, 1=best)", fontsize=FS["label"])
    ax1.set_title("(a)  Multi-Model CMIP6 Ranking by QDM Performance\n"
                  "      (higher composite score = better fit to observations)",
                  loc="left", fontsize=FS["title"]-1, fontweight="bold", pad=5)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    for i, m in enumerate(sorted_models):
        rk = i+1
        medal = "🥇" if rk==1 else ("🥈" if rk==2 else ("🥉" if rk==3 else f"#{rk}"))
        ax1.text(i, -0.07, medal, ha="center", va="top",
                 fontsize=12, transform=ax1.get_xaxis_transform())

    # ── Panel B: radar per model ──────────────────────────────────────
    n_met  = len(RANK_METRICS)
    angles = np.linspace(0, 2*np.pi, n_met, endpoint=False).tolist()
    angles += angles[:1]

    for mi, model in enumerate(models):
        col = MODEL_COLORS[mi % len(MODEL_COLORS)]
        row_out = []
        for k in RANK_METRICS:
            v    = bc_means[model][k]
            all_v = [bc_means[m][k] for m in models
                     if not np.isnan(bc_means[m].get(k,np.nan))]
            if not all_v or np.isnan(v):
                row_out.append(0.5); continue
            mn, mx = min(all_v), max(all_v)
            rng = mx - mn
            if rng == 0: row_out.append(1.0)
            elif k in LOWER_BETTER: row_out.append((mx-v)/rng)
            else: row_out.append((v-mn)/rng)
        row_out += row_out[:1]
        ax2.fill(angles, row_out, color=col, alpha=0.10)
        ax2.plot(angles, row_out, color=col, lw=1.8, ls="-", label=model)

    ax2.set_thetagrids(np.degrees(angles[:-1]), RANK_METRICS,
                        fontsize=FS["tick"])
    ax2.set_ylim(0, 1)
    ax2.set_yticks([0.25, 0.50, 0.75, 1.00])
    ax2.set_yticklabels(["0.25","0.50","0.75","1.00"],
                         fontsize=FS["annot"]-2, color="#78909C")
    ax2.set_title("(b)  Per-Model Normalised Performance Radar\n"
                  "      (QDM-corrected; outer = better)",
                  fontsize=FS["title"]-1, fontweight="bold", pad=18)
    ax2.legend(loc="lower right", bbox_to_anchor=(1.45,-0.15),
               fontsize=FS["legend"]-1, frameon=True, edgecolor="#B0BEC5",
               title="CMIP6 Model", title_fontsize=FS["legend"]-1)
    ax2.grid(True, lw=0.5, alpha=0.55)

    fig.suptitle(
        f"Multi-Model CMIP6 Ranking — QDM Bias-Corrected Performance\n"
        f"{province}  │  Obs: {period_obs}",
        fontsize=FS["title"]+1, fontweight="bold")

    plt.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")

# ═══════════════════════════════════════════════════════════════════════════
# 11.  EXCEL SHEETS
# ═══════════════════════════════════════════════════════════════════════════

DESC_COLS = ["N","Mean","Std","CV (%)","Min","P10","P25","P50","P75",
             "P90","P95","P99","Max","Skewness","Kurtosis","Wet-day freq (%)"]
PERF_COLS = ["N_pairs","RMSE","MAE","MBE","Pbias (%)","r","NSE","KGE",
             "KGE_r","KGE_alpha","KGE_beta","d (IoA)"]


def _desc_sheet(wb, rows, scale, smap, province):
    ws = wb.create_sheet(f"Desc Stats ({scale})")
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "E5"
    nc = 4 + len(DESC_COLS)
    mxsc(ws,1,1,nc,
         f"Table 1.  Descriptive Statistics — {scale} Rainfall "
         "(Observed vs Raw CMIP6 vs Bias-Corrected/QDM)",
         bold=True,fc="FFFFFF",bg=XC["title"],sz=12,align="left")
    ws.row_dimensions[1].height = 22
    mxsc(ws,2,1,nc,
         f"Province/Region: {province}  │  Wet-day ≥{WET_THR} mm | "
         "CV=Coeff.of Variation | Px=Percentile | Skewness: Fisher-Pearson | "
         "Kurtosis: Fisher (normal=0)",
         italic=True,fc="FFFFFF",bg=XC["sub"],sz=8.5)
    ws.row_dimensions[2].height = 13
    hdr = ["Dataset","Station","Code","Scale"] + DESC_COLS
    for ci,h in enumerate(hdr,1):
        xsc(ws,4,ci,h,bold=True,fc="FFFFFF",bg=XC["hdr"],border=tb(),sz=9,wrap=True)
    ws.row_dimensions[4].height = 38
    ds_bg = {"Observed":XC["obs_r"],"Raw CMIP6":XC["raw_r"],"Bias-Corrected":XC["bc_r"]}
    ds_fc = {"Observed":XC["obs_h"],"Raw CMIP6":XC["raw_h"],"Bias-Corrected":XC["bc_h"]}
    prev = None
    for ri,row in enumerate(rows,5):
        ds = row.get("Dataset",""); stn = row.get("Station","")
        bg = ds_bg.get(ds,XC["white"])
        if stn!=prev and prev is not None: ws.row_dimensions[ri-1].height=4
        for ci,key in enumerate(hdr,1):
            if key == "Code": val = smap.get(str(stn),"—")
            else: val = row.get(key,"")
            if isinstance(val,float) and np.isnan(val): val="—"
            elif isinstance(val,float): val=round(val,2)
            cell=xsc(ws,ri,ci,val,bg=bg,border=tb(),sz=9,
                     align="left" if ci<=4 else "right")
            if ci==1:
                cell.font=Font(bold=True,color=ds_fc.get(ds,XC["title"]),
                               name="Calibri",size=9)
        ws.row_dimensions[ri].height = 15
        prev = stn
    widths = [18,9,6,8]+[9]*len(DESC_COLS)
    for ci,w in enumerate(widths,1): cw(ws,ci,w)


def _perf_sheet(wb, rows, scale, imp_rows, rank_df, smap, province):
    ws = wb.create_sheet(f"Performance ({scale})")
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "E7"
    nc = 4 + len(PERF_COLS)
    mxsc(ws,1,1,nc,
         f"Table 2.  Model Performance Metrics — {scale} Scale  │  {province}",
         bold=True,fc="FFFFFF",bg=XC["title"],sz=12,align="left")
    ws.row_dimensions[1].height = 22
    mxsc(ws,2,1,nc,
         "RMSE/MAE/MBE in mm | Pbias in % | r=Pearson | "
         "NSE=Nash–Sutcliffe | KGE=Kling–Gupta | d=Index of Agreement | "
         "★ = Best per station & metric",
         italic=True,fc="FFFFFF",bg=XC["sub"],sz=8.5)
    ws.row_dimensions[2].height = 13
    mxsc(ws,3,1,nc,
         "NSE criteria (Moriasi et al. 2007): Very Good>0.75 | Good 0.65–0.75 | "
         "Satisfactory 0.50–0.65 | Unsatisfactory<0.50",
         italic=True,fc=XC["sub"],bg=XC["note"],sz=8)
    ws.row_dimensions[3].height = 16
    grps = [(1,4,"ID"),(5,5,"N"),(6,9,"Error/Bias (lower=better)"),
            (10,10,"Corr."),(11,12,"Efficiency (higher=better)"),
            (13,15,"KGE components"),(16,16,"Agreement")]
    for c1,c2,lbl in grps:
        mxsc(ws,5,c1,c2,lbl,bold=True,fc="FFFFFF",bg=XC["hdr"],sz=9)
    ws.row_dimensions[5].height = 14
    hdr = ["Dataset","Station","Code","Scale"] + PERF_COLS
    for ci,h in enumerate(hdr,1):
        xsc(ws,6,ci,h,bold=True,fc="FFFFFF",bg=XC["title"],border=tb(),sz=9,wrap=True)
    ws.row_dimensions[6].height = 38
    stns_all = sorted(set(r["Station"] for r in rows))
    best_set = set()
    for stn in stns_all:
        sr = [(i,r) for i,r in enumerate(rows) if r["Station"]==stn]
        for m in PERF_COLS[1:]:
            vals = [(i,r[m]) for i,r in sr
                    if not(isinstance(r[m],float) and np.isnan(r[m]))]
            if not vals: continue
            bi = (min(vals,key=lambda x:abs(x[1]))[0] if m in LOWER_BETTER
                  else max(vals,key=lambda x:x[1])[0])
            best_set.add((bi+7, hdr.index(m)+1))
    ds_bg = {"Raw CMIP6":XC["raw_r"],"Bias-Corrected":XC["bc_r"]}
    ds_fc = {"Raw CMIP6":XC["raw_h"],"Bias-Corrected":XC["bc_h"]}
    prev = None
    for ri,row in enumerate(rows,7):
        ds = row.get("Dataset",""); stn = row.get("Station","")
        bg = ds_bg.get(ds,XC["white"])
        if stn!=prev and prev is not None: ws.row_dimensions[ri-1].height=4
        for ci,key in enumerate(hdr,1):
            if key=="Code": val=smap.get(str(stn),"—")
            else: val=row.get(key,"")
            if isinstance(val,float) and np.isnan(val): val="—"
            elif isinstance(val,float): val=round(val,4)
            is_best=(ri,ci) in best_set
            cell=xsc(ws,ri,ci,
                     f"★ {val}" if is_best and val not in ("","—") else val,
                     bg=XC["best"] if is_best else bg,
                     border=tb(),sz=9,
                     align="left" if ci<=4 else "right")
            if ci==1:
                cell.font=Font(bold=True,color=ds_fc.get(ds,XC["title"]),
                               name="Calibri",size=9)
            if is_best:
                cell.font=Font(bold=True,color=XC["best_f"],
                               name="Calibri",size=9)
        ws.row_dimensions[ri].height = 15
        prev = stn

    # ── Overall Performance Improvement Table ─────────────────────────
    sr = ws.max_row + 2
    mxsc(ws,sr,1,nc,
         "Table 3.  Overall Performance Improvement Summary — "
         "QDM vs Raw CMIP6  (averaged across all stations)",
         bold=True,fc="FFFFFF",bg=XC["sub"],sz=11)
    ws.row_dimensions[sr].height = 22; sr+=1
    imp_hdr = ["Metric","Raw CMIP6\n(Avg)","QDM Corrected\n(Avg)",
               "Absolute\nImprovement","% Improvement",
               "Direction","Best Station"]
    for ci,h in enumerate(imp_hdr,1):
        xsc(ws,sr,ci,h,bold=True,fc="FFFFFF",bg=XC["hdr"],border=tb(),sz=10,wrap=True)
    ws.row_dimensions[sr].height = 32; sr+=1
    for imp in imp_rows:
        d   = imp.get("Direction","")
        rbg = XC["improve"] if d=="Improved" else XC["degrade"]
        for ci,k in enumerate(imp_hdr,1):
            val=imp.get(k,"")
            if isinstance(val,float) and np.isnan(val): val="—"
            elif isinstance(val,float): val=round(val,3)
            cell=xsc(ws,sr,ci,val,bg=rbg,border=tb(),sz=10)
            if k in ("Direction","Best Station"):
                fc_col = XC["obs_h"] if d=="Improved" else XC["raw_h"]
                cell.font=Font(bold=True,color=fc_col,name="Calibri",size=10)
            if k=="% Improvement" and isinstance(val,(int,float)) and val not in ("—",):
                try: cell.value=f"{val:+.1f}%"
                except: pass
        ws.row_dimensions[sr].height = 18; sr+=1

    # ── Ranking block ─────────────────────────────────────────────────
    sr += 1
    mxsc(ws,sr,1,nc,
         "Table 4.  Model Ranking — Composite Score "
         "(normalised multi-metric rank, 0=worst → 1=best)",
         bold=True,fc="FFFFFF",bg=XC["sub"],sz=11)
    ws.row_dimensions[sr].height = 22; sr+=1
    rank_hdr = ["Rank","Model"]+RANK_METRICS+["Composite Score"]
    for ci,h in enumerate(rank_hdr,1):
        xsc(ws,sr,ci,h,bold=True,fc="FFFFFF",bg=XC["hdr"],border=tb(),sz=10)
    ws.row_dimensions[sr].height = 22; sr+=1
    medal={1:XC["rank1"],2:XC["rank2"],3:XC["rank3"]}
    for model,row in rank_df.sort_values("Rank").iterrows():
        rnk=int(row["Rank"]); rbg=medal.get(rnk,XC["white"])
        lbl=f"{'#1' if rnk==1 else ('#2' if rnk==2 else '#3')} Rank {rnk}"
        xsc(ws,sr,1,lbl,bg=rbg,bold=True,border=tb(),sz=10)
        xsc(ws,sr,2,model,bg=rbg,bold=True,border=tb(),sz=10,align="left")
        for ci,m in enumerate(RANK_METRICS,3):
            v = row.get(m,np.nan)
            xsc(ws,sr,ci,round(float(v),4) if not np.isnan(float(v)) else "—",
                bg=rbg,border=tb(),sz=10)
        cs = row.get("Composite Score",np.nan)
        xsc(ws,sr,len(rank_hdr),
            round(float(cs),4) if not np.isnan(float(cs)) else "—",
            bg=rbg,bold=True,border=tb(),sz=10)
        ws.row_dimensions[sr].height = 18; sr+=1
    widths = [18,9,6,8]+[10]*len(PERF_COLS)
    for ci,w in enumerate(widths,1): cw(ws,ci,w)


def _regional_sheet(wb, reg_perf_d, reg_perf_m, error_red_d, error_red_m,
                    model_df, qdf, rdf, province):
    """
    Regional Average Comparison sheet:
      - Regional perf (daily & monthly)
      - % Error Reduction table
      - Multi-model CMIP6 ranking
    """
    ws = wb.create_sheet("Regional Average")
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A4"
    nc = 12

    mxsc(ws,1,1,nc,
         f"Regional Average Comparison — {province}\n"
         "Spatial Mean across ALL Stations — Observed vs Raw CMIP6 Ensemble vs QDM Ensemble",
         bold=True,fc="FFFFFF",bg=XC["title"],sz=13,align="left")
    ws.row_dimensions[1].height = 28
    ws.row_dimensions[2].height = 6

    row_cur = 3

    # ── Section 1: Regional Performance (Daily) ───────────────────────
    mxsc(ws,row_cur,1,nc,
         "Section 1  │  Regional Performance Metrics — Daily Scale  "
         "(Spatial mean of all stations vs Observed mean)",
         bold=True,fc="FFFFFF",bg=XC["reg_hdr"],sz=11,align="left")
    ws.row_dimensions[row_cur].height = 20; row_cur+=1

    perf_hdr = ["Dataset","N_pairs","RMSE","MAE","MBE",
                "Pbias (%)","r","NSE","KGE","d (IoA)"]
    for ci,h in enumerate(perf_hdr,1):
        xsc(ws,row_cur,ci,h,bold=True,fc="FFFFFF",bg=XC["hdr"],border=tb(),sz=10)
    ws.row_dimensions[row_cur].height = 22; row_cur+=1

    ds_bg  = {"Raw CMIP6":XC["raw_r"], "Bias-Corrected (QDM)":XC["bc_r"],
               "Observed":XC["obs_r"]}
    ds_fc_ = {"Raw CMIP6":XC["raw_h"], "Bias-Corrected (QDM)":XC["bc_h"],
               "Observed":XC["obs_h"]}

    for r in reg_perf_d:
        ds = r.get("Dataset","")
        bg = ds_bg.get(ds, XC["white"])
        for ci,k in enumerate(perf_hdr,1):
            val = r.get(k,"—")
            if isinstance(val,float) and np.isnan(val): val="—"
            elif isinstance(val,float): val=round(val,4)
            cell=xsc(ws,row_cur,ci,val,bg=bg,border=tb(),sz=10)
            if ci==1:
                cell.font=Font(bold=True,color=ds_fc_.get(ds,XC["title"]),
                               name="Calibri",size=10)
        ws.row_dimensions[row_cur].height = 18; row_cur+=1

    row_cur+=1

    # ── Section 2: Regional Performance (Monthly) ─────────────────────
    mxsc(ws,row_cur,1,nc,
         "Section 2  │  Regional Performance Metrics — Monthly Scale",
         bold=True,fc="FFFFFF",bg=XC["reg_hdr"],sz=11,align="left")
    ws.row_dimensions[row_cur].height = 20; row_cur+=1
    for ci,h in enumerate(perf_hdr,1):
        xsc(ws,row_cur,ci,h,bold=True,fc="FFFFFF",bg=XC["hdr"],border=tb(),sz=10)
    ws.row_dimensions[row_cur].height = 22; row_cur+=1
    for r in reg_perf_m:
        ds = r.get("Dataset","")
        bg = ds_bg.get(ds, XC["white"])
        for ci,k in enumerate(perf_hdr,1):
            val = r.get(k,"—")
            if isinstance(val,float) and np.isnan(val): val="—"
            elif isinstance(val,float): val=round(val,4)
            cell=xsc(ws,row_cur,ci,val,bg=bg,border=tb(),sz=10)
            if ci==1:
                cell.font=Font(bold=True,color=ds_fc_.get(ds,XC["title"]),
                               name="Calibri",size=10)
        ws.row_dimensions[row_cur].height = 18; row_cur+=1

    row_cur+=1

    # ── Section 3: % Error Reduction (Daily) ─────────────────────────
    mxsc(ws,row_cur,1,nc,
         "Section 3  │  % Error Reduction — QDM vs Raw CMIP6 Ensemble  "
         "(Daily; averaged across all stations & models)",
         bold=True,fc="FFFFFF",bg=XC["reg_hdr"],sz=11,align="left")
    ws.row_dimensions[row_cur].height = 20; row_cur+=1
    err_hdr=["Metric","Raw CMIP6 Ensemble","QDM Ensemble",
             "Abs Improvement","% Error Reduction","Direction","Summary Statement"]
    for ci,h in enumerate(err_hdr,1):
        xsc(ws,row_cur,ci,h,bold=True,fc="FFFFFF",bg=XC["hdr"],border=tb(),sz=10,wrap=True)
    ws.row_dimensions[row_cur].height = 30; row_cur+=1
    for r in error_red_d:
        d   = r.get("Direction","")
        rbg = XC["improve"] if d=="Improved" else XC["degrade"]
        for ci,k in enumerate(err_hdr,1):
            val=r.get(k,"—")
            if isinstance(val,float) and np.isnan(val): val="—"
            elif isinstance(val,float): val=round(val,4)
            cell=xsc(ws,row_cur,ci,val,bg=rbg,border=tb(),sz=10,
                     align="left" if k=="Summary Statement" else "center")
            if k in ("Direction",):
                fc_col = XC["obs_h"] if d=="Improved" else XC["raw_h"]
                cell.font=Font(bold=True,color=fc_col,name="Calibri",size=10)
            if k=="% Error Reduction" and isinstance(val,(int,float)) and val not in ("—",):
                try: cell.value=f"{val:+.2f}%"
                except: pass
        ws.row_dimensions[row_cur].height = 20; row_cur+=1

    row_cur+=1

    # ── Section 4: Multi-Model CMIP6 Ranking (QDM) ────────────────────
    mxsc(ws,row_cur,1,nc,
         "Section 4  │  Multi-Model CMIP6 Ranking by QDM Performance\n"
         "(Normalised composite score: 0=worst, 1=best; ranked by QDM skill)",
         bold=True,fc="FFFFFF",bg=XC["reg_hdr"],sz=11,align="left")
    ws.row_dimensions[row_cur].height = 28; row_cur+=1

    rank_hdr2 = (["Rank","Model"] +
                 [f"QDM {m}" for m in RANK_METRICS] +
                 ["QDM Composite","Raw Composite","Improvement"])
    for ci,h in enumerate(rank_hdr2,1):
        xsc(ws,row_cur,ci,h,bold=True,fc="FFFFFF",bg=XC["hdr"],border=tb(),sz=10,wrap=True)
    ws.row_dimensions[row_cur].height = 30; row_cur+=1

    medal = {1:XC["rank1"], 2:XC["rank2"], 3:XC["rank3"]}
    for model in qdf.sort_values("Rank (QDM)").index:
        rnk = int(qdf.loc[model,"Rank (QDM)"])
        rbg = medal.get(rnk, XC["white"])
        xsc(ws,row_cur,1,f"Rank {rnk}",bg=rbg,bold=True,border=tb(),sz=10)
        xsc(ws,row_cur,2,model,bg=rbg,bold=True,border=tb(),sz=10,align="left")
        for ci2, m in enumerate(RANK_METRICS,3):
            v = qdf.loc[model,m]
            xsc(ws,row_cur,ci2,
                round(float(v),4) if not np.isnan(float(v)) else "—",
                bg=rbg,border=tb(),sz=10)
        qcs = qdf.loc[model,"Composite Score (QDM)"]
        rcs = rdf.loc[model,"Composite Score (Raw)"] if model in rdf.index else np.nan
        imp = qcs - rcs if not np.isnan(rcs) else np.nan
        xsc(ws,row_cur,3+len(RANK_METRICS),
            round(float(qcs),4) if not np.isnan(float(qcs)) else "—",
            bg=rbg,bold=True,border=tb(),sz=10)
        xsc(ws,row_cur,4+len(RANK_METRICS),
            round(float(rcs),4) if not np.isnan(float(rcs)) else "—",
            bg=rbg,border=tb(),sz=10)
        imp_str = f"{imp:+.4f}" if not np.isnan(imp) else "—"
        cell=xsc(ws,row_cur,5+len(RANK_METRICS),imp_str,
                 bg=rbg,border=tb(),sz=10,bold=True)
        if not np.isnan(imp):
            cell.font=Font(bold=True,
                           color=XC["obs_h"] if imp>=0 else XC["raw_h"],
                           name="Calibri",size=10)
        ws.row_dimensions[row_cur].height = 18; row_cur+=1

    # column widths
    cw(ws,1,10); cw(ws,2,20)
    for ci3 in range(3, 3+len(RANK_METRICS)+3): cw(ws,ci3,14)
    cw(ws, 3+len(RANK_METRICS)+3, 55)  # summary statement


def _stn_index_sheet(wb, stns, smap, period_obs, period_sim, province):
    ws = wb.create_sheet("Station Index")
    ws.sheet_view.showGridLines = False
    mxsc(ws,1,1,5,
         f"Station Index Table — {province}, Thailand",
         bold=True,fc="FFFFFF",bg=XC["title"],sz=12)
    ws.row_dimensions[1].height = 22
    mxsc(ws,2,1,5,
         f"Province: {province}  │  Observed period: {period_obs}  │  "
         f"Simulation period: {period_sim}  │  Wet-day threshold: ≥{WET_THR} mm day⁻¹",
         italic=True,fc="FFFFFF",bg=XC["sub"],sz=8.5)
    ws.row_dimensions[2].height = 13
    hdr = ["Code","Station ID","Province","Latitude (°N)","Longitude (°E)"]
    for ci,h in enumerate(hdr,1):
        xsc(ws,4,ci,h,bold=True,fc="FFFFFF",bg=XC["hdr"],border=tb(),sz=10)
    ws.row_dimensions[4].height = 22
    for ri,stn in enumerate(stns,5):
        code = smap[str(stn)]
        for ci,val in enumerate([code,str(stn),province,"—","—"],1):
            bg = XC["bc_r"] if ri%2==0 else XC["white"]
            xsc(ws,ri,ci,val,bg=bg,border=tb(),sz=10)
        ws.row_dimensions[ri].height = 16
    for ci,w in enumerate([8,12,24,16,16],1): cw(ws,ci,w)


def _method_sheet(wb, period_obs, period_sim, n_stns, province):
    ws = wb.create_sheet("Method & References")
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 26
    ws.column_dimensions["C"].width = 68
    mxsc(ws,1,1,3,
         "Statistical Methods, Performance Criteria & References",
         bold=True,fc="FFFFFF",bg=XC["title"],sz=13)
    ws.row_dimensions[1].height = 24
    rows_info = [
        ("Period","Study Period",
         f"Province: {province}  │  Observed: {period_obs}  │  "
         f"CMIP6/QDM: {period_sim}  │  Stations: {n_stns}  │  "
         f"Wet-day: ≥{WET_THR} mm day⁻¹"),
        ("RMSE","Root Mean Square Error","RMSE=√[Σ(sim−obs)²/n]  (mm)"),
        ("MAE","Mean Absolute Error","MAE=Σ|sim−obs|/n  (mm)"),
        ("MBE","Mean Bias Error","MBE=Σ(sim−obs)/n  (mm). Positive=overestimate"),
        ("Pbias","Percent Bias","Pbias=100·Σ(sim−obs)/Σobs  (%). Optimal: 0%"),
        ("r","Pearson Correlation","r∈[−1,1]. Perfect: r=1"),
        ("NSE","Nash–Sutcliffe Efficiency",
         "NSE=1−Σ(sim−obs)²/Σ(obs−obs̄)². Range(−∞,1]. "
         "VG>0.75 | Good 0.65–0.75 | Sat 0.50–0.65 | Unsat<0.50. "
         "Ref: Nash & Sutcliffe (1970) J. Hydrol. 10:282–290."),
        ("KGE","Kling–Gupta Efficiency",
         "KGE=1−√[(r−1)²+(α−1)²+(β−1)²]. α=σ_sim/σ_obs; β=μ_sim/μ_obs. "
         "Range(−∞,1]. Ref: Gupta et al. (2009) J. Hydrol. 377:80–91."),
        ("d","Index of Agreement (Willmott)",
         "d=1−Σ(sim−obs)²/Σ(|sim−obs̄|+|obs−obs̄|)². Range[0,1]. "
         "Ref: Willmott (1981) Phys. Geogr. 2:184–194."),
        ("Rank","Composite Score",
         "Normalised per metric: 0=worst, 1=best. "
         "Composite=mean of normalised scores. Higher=better overall."),
        ("QDM","Quantile Delta Mapping",
         "Ref: Cannon et al. (2015) J. Climate 28:6938–6959."),
        ("","Further References",
         "Teutschbein & Seibert (2012) Hydrol. Earth Syst. Sci. 16:3391–3314.\n"
         "Moriasi et al. (2007) Trans. ASABE 50:885–900.\n"
         "Maidment (1993) Handbook of Hydrology. McGraw-Hill."),
    ]
    alt = [PatternFill("solid",fgColor="DEEAF1"),
           PatternFill("solid",fgColor="FFFFFF")]
    for ri,(a,b,d) in enumerate(rows_info,3):
        fl = alt[ri%2]
        for ci,v in enumerate([a,b,d],1):
            cell=xsc(ws,ri,ci,v,bold=(ci<=2),sz=9,
                     align="center" if ci==1 else "left",border=tb())
            cell.fill = fl
            if ci==3:
                cell.alignment=Alignment(horizontal="left",vertical="top",
                                          wrap_text=True)
        ws.row_dimensions[ri].height = 48

# ═══════════════════════════════════════════════════════════════════════════
# 12.  MAIN
# ═══════════════════════════════════════════════════════════════════════════

def get_work_dir():
    try: return str(Path(os.path.abspath(__file__)).parent)
    except: return os.getcwd()

def main():
    sep = "=" * 72
    print(sep)
    print("  Multi-Model Ensemble Analysis  v3.0")
    print("  Obs vs Raw CMIP6 (per-model) vs QDM + Regional Average")
    print("  มาตรฐาน Nature / Elsevier / Q2")
    print(sep)

    work_dir = (sys.argv[1].strip('"').strip("'")
                if len(sys.argv) > 1 else get_work_dir())
    print(f"  โฟลเดอร์ input : {work_dir}")

    # ── province validation & file discovery ──────────────────────────
    obs_path, raw_dict, bc_dict, province = find_csvs_multi(work_dir)

    # ── output folder (timestamped, never overwrites) ─────────────────
    ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(work_dir) / f"Output_{province}_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"  โฟลเดอร์ output: {out_dir}")
    print("-"*72)

    # ── load observed ─────────────────────────────────────────────────
    print("  กำลังโหลดข้อมูล ...")
    obs_d, stns = load_daily(obs_path, "Observed")
    obs_m       = to_monthly(obs_d)
    stns_str    = [str(s) for s in stns]
    period_obs  = period_str(obs_d)
    print(f"  Observed: {len(stns)} สถานี  │  {period_obs}")

    # ── load all models ───────────────────────────────────────────────
    models_common = sorted(set(raw_dict.keys()) & set(bc_dict.keys()))
    if not models_common:
        sys.exit("  ✗  ไม่มี model ที่มีทั้ง Raw และ BC")
    print(f"  Models (paired): {models_common}")

    raw_dfs, bc_dfs = {}, {}
    period_sim = "N/A"
    for model in models_common:
        raw_dfs[model], _ = load_daily(raw_dict[model], f"Raw {model}")
        bc_dfs[model],  _ = load_daily(bc_dict[model],  f"BC  {model}")
        period_sim = period_str(raw_dfs[model])

    # ── ensemble mean (average across models) ────────────────────────
    def ensemble_mean_df(dfs_dict):
        """Average daily DF across all models."""
        dfs_list = [df for df in dfs_dict.values() if df is not None]
        if not dfs_list: return None
        aligned = pd.concat(dfs_list, axis=1, keys=range(len(dfs_list)))
        # multi-index: (model_idx, station)
        result = {}
        for stn in stns_str:
            try:
                cols = aligned.xs(stn, axis=1, level=1)
                result[stn] = cols.mean(axis=1)
            except Exception:
                result[stn] = pd.Series(dtype=float)
        return pd.DataFrame(result)

    raw_ens_d = ensemble_mean_df(raw_dfs)
    bc_ens_d  = ensemble_mean_df(bc_dfs)
    raw_ens_m = to_monthly(raw_ens_d)
    bc_ens_m  = to_monthly(bc_ens_d)

    smap = short_labels(stns_str)
    print(f"  Station codes: {smap}")
    print("-"*72)

    # ── compute statistics (ensemble mean for main analysis) ──────────
    print("  คำนวณสถิติ (Ensemble Mean) ...")
    desc_d, desc_m = [], []
    met_d_raw, met_d_bc = [], []
    met_m_raw, met_m_bc = [], []
    rd2 = {}

    for stn in stns_str:
        obs_v  = gcol(obs_d,    stn)
        raw_v  = gcol(raw_ens_d, stn)
        bc_v   = gcol(bc_ens_d,  stn)
        obs_ms = obs_m[stn].dropna() if obs_m is not None and stn in obs_m.columns \
                 else pd.Series(dtype=float)
        raw_ms = raw_ens_m[stn].dropna() \
                 if raw_ens_m is not None and stn in raw_ens_m.columns \
                 else pd.Series(dtype=float)
        bc_ms  = bc_ens_m[stn].dropna() \
                 if bc_ens_m is not None and stn in bc_ens_m.columns \
                 else pd.Series(dtype=float)

        rd2[stn] = {
            "obs":       obs_v,
            "raw":       raw_v,
            "bc":        bc_v,
            "daily_all": obs_v,
            "daily_wet": wet_only(obs_v),
            "monthly":   obs_ms.values.astype(float),
        }

        for lbl,arr in [("Observed",obs_v),("Raw CMIP6",raw_v),
                        ("Bias-Corrected",bc_v)]:
            desc_d.append(desc_stats(arr, lbl, stn, "Daily"))
        for lbl,arr in [("Observed",    obs_ms.values.astype(float)),
                        ("Raw CMIP6",   raw_ms.values.astype(float)),
                        ("Bias-Corrected", bc_ms.values.astype(float))]:
            desc_m.append(desc_stats(arr, lbl, stn, "Monthly"))

        o_r_d, r_d = align_daily(obs_d, raw_ens_d, stn)
        o_b_d, b_d = align_daily(obs_d, bc_ens_d,  stn)
        met_d_raw.append(perf_metrics(o_r_d, r_d, "Raw CMIP6",      stn, "Daily"))
        met_d_bc.append( perf_metrics(o_b_d, b_d, "Bias-Corrected", stn, "Daily"))
        met_m_raw.append(perf_metrics(obs_ms, raw_ms, "Raw CMIP6",      stn, "Monthly"))
        met_m_bc.append( perf_metrics(obs_ms, bc_ms,  "Bias-Corrected", stn, "Monthly"))
        print(f"    ✓  {stn}  ({smap[stn]})")

    # ── per-model performance (for multi-model ranking) ───────────────
    print("\n  คำนวณ per-model performance ...")
    model_perf = {}
    for model in models_common:
        raw_rows_m, bc_rows_m = [], []
        for stn in stns_str:
            o_r, r_r = align_daily(obs_d, raw_dfs[model], stn)
            o_b, b_b = align_daily(obs_d, bc_dfs[model],  stn)
            raw_rows_m.append(perf_metrics(o_r, r_r, f"Raw_{model}", stn, "Daily"))
            bc_rows_m.append( perf_metrics(o_b, b_b, f"QDM_{model}", stn, "Daily"))
        model_perf[model] = {"raw": raw_rows_m, "bc": bc_rows_m}
        print(f"    ✓  {model}")

    # ── improvement & ranking ─────────────────────────────────────────
    imp_d     = improvement_rows(met_d_raw, met_d_bc)
    imp_m     = improvement_rows(met_m_raw, met_m_bc)
    rank_df   = compute_ranking(met_d_raw, met_d_bc)
    model_df, qdf, rdf = compute_model_ranking(model_perf)

    print("\n  Composite Ranking (Ensemble):")
    for model, row in rank_df.sort_values("Rank").iterrows():
        print(f"    Rank {int(row['Rank'])} — {model}  "
              f"(Score = {row['Composite Score']:.4f})")

    print("\n  Multi-Model CMIP6 Ranking (QDM performance):")
    for model in qdf.sort_values("Rank (QDM)").index:
        print(f"    Rank {int(qdf.loc[model,'Rank (QDM)'])} — {model}  "
              f"(QDM Score = {qdf.loc[model,'Composite Score (QDM)']:.4f})")

    # ── regional average ──────────────────────────────────────────────
    print("\n  คำนวณ Regional Average ...")
    reg_daily  = compute_regional_avg({"Observed": obs_d,
                                        "Raw CMIP6": raw_ens_d,
                                        "Bias-Corrected (QDM)": bc_ens_d},
                                       stns_str)
    reg_monthly = compute_regional_avg({"Observed": obs_m,
                                         "Raw CMIP6": raw_ens_m,
                                         "Bias-Corrected (QDM)": bc_ens_m},
                                        stns_str)

    obs_reg_d = reg_daily.get("Observed")
    sim_reg_d = {k:v for k,v in reg_daily.items() if k!="Observed"}
    obs_reg_m = reg_monthly.get("Observed")
    sim_reg_m = {k:v for k,v in reg_monthly.items() if k!="Observed"}

    reg_perf_d = regional_perf(obs_reg_d, sim_reg_d, stns_str, "Daily")
    reg_perf_m = regional_perf(obs_reg_m, sim_reg_m, stns_str, "Monthly")

    # all raw/bc rows across all models (for ensemble error reduction)
    all_raw = [r for m in models_common for r in model_perf[m]["raw"]]
    all_bc  = [r for m in models_common for r in model_perf[m]["bc"]]
    error_red_d = error_reduction_table(all_raw, all_bc)
    error_red_m = error_reduction_table(all_raw, all_bc)  # same pool

    print("\n  % Error Reduction (Daily Ensemble):")
    for r in error_red_d:
        print(f"    {r['Metric']:12s}: {r.get('Summary Statement','')}")

    # ── interleave rows ───────────────────────────────────────────────
    perf_d_rows, perf_m_rows = [], []
    for r, b in zip(met_d_raw, met_d_bc): perf_d_rows += [r, b]
    for r, b in zip(met_m_raw, met_m_bc): perf_m_rows += [r, b]

    # ── Excel ─────────────────────────────────────────────────────────
    base_name = Path(obs_path).stem
    out_xlsx  = out_dir / f"Output_Ensemble_{base_name}.xlsx"
    print(f"\n  กำลังสร้าง Excel → {out_xlsx.name} ...")
    wb = Workbook(); wb.remove(wb.active)
    _stn_index_sheet(wb, stns_str, smap, period_obs, period_sim, province)
    _desc_sheet(wb, desc_d, "Daily",   smap, province)
    _desc_sheet(wb, desc_m, "Monthly", smap, province)
    _perf_sheet(wb, perf_d_rows, "Daily",   imp_d, rank_df, smap, province)
    _perf_sheet(wb, perf_m_rows, "Monthly", imp_m, rank_df, smap, province)
    _regional_sheet(wb, reg_perf_d, reg_perf_m, error_red_d, error_red_m,
                    model_df, qdf, rdf, province)
    _method_sheet(wb, period_obs, period_sim, len(stns_str), province)
    wb.save(str(out_xlsx))
    print("  ✓  Excel saved")

    # ── Figures ───────────────────────────────────────────────────────
    print("\n  กำลังสร้างรูปภาพ ...")
    fig_boxplot_desc(rd2, stns_str, smap, period_obs, period_sim, province,
        str(out_dir/f"Output_Ensemble_{base_name}_Fig1_BoxplotDesc.png"))

    fig_performance(met_d_raw, met_d_bc, stns_str, smap, "Daily",
                    "Daily",
        str(out_dir/f"Output_Ensemble_{base_name}_Fig2_Performance_Daily.png"),
        period_obs, period_sim, province)

    fig_performance(met_m_raw, met_m_bc, stns_str, smap, "Monthly",
                    "Monthly",
        str(out_dir/f"Output_Ensemble_{base_name}_Fig3_Performance_Monthly.png"),
        period_obs, period_sim, province)

    fig_ranking(imp_d, imp_m, rank_df,
        str(out_dir/f"Output_Ensemble_{base_name}_Fig4_Ranking.png"),
        period_obs, province)

    fig_heatmap(met_d_raw, met_d_bc, stns_str, smap,
        str(out_dir/f"Output_Ensemble_{base_name}_Fig5_Heatmap.png"),
        period_obs, period_sim, province)

    fig_model_ranking(model_perf,
        str(out_dir/f"Output_Ensemble_{base_name}_Fig6_ModelRanking.png"),
        period_obs, province)

    print()
    print(sep)
    print(f"  เสร็จสิ้น")
    print(f"  Excel 1 ไฟล์  │  รูปภาพ 6 ไฟล์")
    print(f"  บันทึกใน: {out_dir}")
    print(sep)

if __name__ == "__main__":
    main()
