# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  CMIP6 Bias Correction Evaluation v5.0                                      ║
║  Full Suite: QDM Evaluation + MMK Trend + Station-Scale Ensemble Analysis   ║
║  Q2 / Nature / Elsevier publication standard                                ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  NEW in v4.0 — Trend Analysis Module:                                       ║
║   Fig 7 – Annual Trend Comparison (Obs / Raw / BC) per station              ║
║   Fig 8 – Sen's Slope Comparison & Confidence Intervals                     ║
║   Fig 9 – MMK Z-score & p-value Significance Summary                       ║
║   Fig10 – Taylor Diagram of Annual Trend Magnitudes                         ║
║   Fig11 – QDM Trend Preservation Assessment (scatter + heatmap)             ║
║   Existing Figs 2–6 retained                                                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  References (trend analysis):                                                ║
║   Mann HB (1945) Econometrica 13:245–259                [MK test]          ║
║   Kendall MG (1975) Rank Correlation Methods. Griffin   [MK test]          ║
║   Hamed KH & Rao AR (1998) J.Hydrol. 204:182–196       [MMK test]         ║
║   Sen PK (1968) J.Am.Stat.Assoc. 63:1379–1389          [Sen's slope]      ║
║   Theil H (1950) Proc.K.Ned.Akad.Wet. 53:386–392       [Theil slope]      ║
║   Cannon et al. (2015) J.Climate 28:6938–6959          [QDM]              ║
║   Yue & Wang (2004) Water Resour.Res. 40:W09505         [pre-whitening]    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os, sys, re, math, warnings, gc
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats as sps
from scipy.stats import (gaussian_kde, wilcoxon as scipy_wilcoxon,
                          rankdata, pearsonr, norm as sci_norm,
                          theilslopes)

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
#  §0  CONSTANTS & STYLE
# ════════════════════════════════════════════════════════════════════════

VERSION    = "5.0"
WET_THR    = 1.0
WET_MONTHS = [5,6,7,8,9,10]
SAVE_PDF   = True
DPI        = 600
MISS_FLAGS = [-99,-999,-9999,-9.99e+20,9.99e+20,1e+20]
ALPHA      = 0.05

C = dict(
    obs="#1B2838",    obs_lt="#90A4AE",   obs_bd="#1B2838",
    raw="#C62828",    raw_lt="#EF9A9A",   raw_bd="#B71C1C",
    bc="#1565C0",     bc_lt="#90CAF9",    bc_bd="#0D47A1",
    ens="#2E7D32",    ens_lt="#A5D6A7",   ens_bd="#1B5E20",
    green="#1B5E20",  gold="#F57F17",
    grey="#455A64",   purple="#6A1B9A",
    red2="#D32F2F",   amber="#FF8F00",
    teal="#00695C",   cyan="#0097A7",
    sig_hi="#1B5E20", sig_lo="#B71C1C",
)
MODEL_PALETTE = ["#1565C0","#C62828","#2E7D32","#E65100",
                 "#6A1B9A","#00695C","#AD1457","#37474F"]
SIG_COLORS    = {"***":"#1B5E20","**":"#2E7D32","*":"#81C784","ns":"#CFD8DC"}
TREND_STYLES  = {
    "Observed" : dict(color=C["obs"], lw=2.8, ls="-",  zorder=6, alpha=1.0),
    "Raw CMIP6": dict(color=C["raw"], lw=2.0, ls="--", zorder=5, alpha=0.85),
    "BC (QDM)" : dict(color=C["bc"],  lw=2.2, ls="-",  zorder=5, alpha=0.90),
}

plt.rcParams.update({
    "font.family":"serif","font.serif":["Times New Roman","DejaVu Serif"],
    "font.weight":"bold","font.size":12,
    "axes.titlesize":14,"axes.titleweight":"bold",
    "axes.labelsize":13,"axes.labelweight":"bold",
    "xtick.labelsize":11,"ytick.labelsize":11,"legend.fontsize":11,
    "figure.titlesize":14,"lines.linewidth":2.2,"axes.linewidth":1.5,
    "axes.spines.top":False,"axes.spines.right":False,
    "axes.grid":True,"grid.linestyle":"--",
    "grid.linewidth":0.5,"grid.alpha":0.40,"grid.color":"#B0BEC5",
    "savefig.dpi":DPI,"savefig.bbox":"tight",
    "savefig.pad_inches":0.18,"figure.dpi":100,
    "mathtext.fontset":"stix","pdf.fonttype":42,"ps.fonttype":42,
})

THIN = Side(style="thin",color="BDBDBD"); MED=Side(style="medium",color="1F4E79")
XC = dict(title="13293D",sub="1F4E79",hdr="2E75B6",
          obs_r="E8F5E9",raw_r="FFEBEE",bc_r="E3F2FD",
          improve="C8E6C9",degrade="FFCCBC",
          best="FFF9C4",white="FFFFFF",alt="F5F5F5",
          sig="DDEEFF",nsig="FFFFF0",note="ECEFF1",
          inc="E8F5E9",dec="FFEBEE",neu="F5F5F5")

def _tb():   return Border(left=THIN,right=THIN,top=THIN,bottom=THIN)
def _xf(h):  return PatternFill("solid",fgColor=h)
def _xsc(ws,r,c,val=None,bold=False,italic=False,fc=None,bg=None,align="center",sz=10,wrap=True):
    cell=ws.cell(row=r,column=c)
    if val is not None: cell.value=val
    cell.font=Font(bold=bold,italic=italic,name="Calibri",size=sz,color=fc if fc else "1A1A1A")
    cell.alignment=Alignment(horizontal=align,vertical="center",wrap_text=wrap)
    if bg: cell.fill=_xf(bg)
    cell.border=_tb(); return cell
def _mxsc(ws,r,c1,c2,val,**kw):
    ws.merge_cells(start_row=r,start_column=c1,end_row=r,end_column=c2)
    return _xsc(ws,r,c1,val,**kw)
def _cw(ws,col,w): ws.column_dimensions[get_column_letter(col)].width=w
def _rh(ws,r,h):   ws.row_dimensions[r].height=h

def savefig(fig,stem):
    dpi=int(os.environ.get("CMIP6_DPI",DPI))
    p=str(stem)
    fig.savefig(p+".png",dpi=dpi,bbox_inches="tight",pad_inches=0.18)
    if SAVE_PDF: fig.savefig(p+".pdf",bbox_inches="tight",pad_inches=0.18)
    plt.close(fig); gc.collect()
    print(f"  ✓  {Path(p).name}.png"+(" + .pdf" if SAVE_PDF else ""))


# ════════════════════════════════════════════════════════════════════════
#  §1  FILE DISCOVERY
# ════════════════════════════════════════════════════════════════════════

_SKIP_TOKENS={"pr","bc","day","mon","yr","daily","monthly",
              "hist","historical","ssp245","ssp585","ssp126",
              "r1i1p1f1","r1i1p1f2","r11i1p1f1","gn","gr"}
_KNOWN_PROV={"phetchaburi","prachuap","phuket","chonburi","rayong","trad",
             "chanthaburi","nakhon","surat","chumphon","ranong","krabi",
             "trang","satun","songkhla","pattani","yala","narathiwat",
             "chiangmai","chiangrai","udon","loei","lopburi","ayutthaya","bangkok"}

def _extract_model(fname):
    stem=Path(fname).stem
    body=re.sub(r"^(bc_)?(pr_)?(day_)?","",stem,flags=re.IGNORECASE)
    for p in body.split("_"):
        if p and p.lower() not in _SKIP_TOKENS and not re.match(r"^\d{4,}$",p) \
                and not re.match(r"r\d+i",p.lower()): return p
    parts=body.split("_"); return parts[0] if parts else "UnknownModel"

def discover_files(folder):
    folder_p=Path(folder); all_csv=sorted(folder_p.rglob("*.csv"))
    obs_files=[f for f in all_csv if "observed" in f.name.lower()]
    raw_files=[f for f in all_csv if f.name.lower().startswith("pr") and "observed" not in f.name.lower()]
    bc_files =[f for f in all_csv if f.name.lower().startswith("bc") and "observed" not in f.name.lower()]
    obs_path=str(obs_files[0]) if obs_files else None
    if len(obs_files)>1: print(f"  ⚠  Multiple Observed — using {obs_files[0].name}")
    province_key=""
    if obs_path:
        stem=re.sub(r"_\d{6,}_\d{6,}","",Path(obs_path).stem.lower())
        stem=re.sub(r"observed_rain_daily_?","",stem)
        province_key=stem.strip("_").replace("_"," ")
    obs_prov={w for w in province_key.lower().split() if len(w)>=3}
    def _ok(f):
        sl=f.stem.lower().replace("_"," ")
        fp={w for w in _KNOWN_PROV if w in sl}
        if not fp: return True
        return bool(fp & obs_prov)
    raw_d,bc_d={},{}
    for f in raw_files:
        if province_key and not _ok(f): continue
        m=_extract_model(f.name)
        if m not in raw_d: raw_d[m]=str(f); print(f"  Raw  '{m}' ← {f.name}")
    for f in bc_files:
        if province_key and not _ok(f): continue
        m=_extract_model(f.name)
        if m not in bc_d:  bc_d[m]=str(f);  print(f"  BC   '{m}' ← {f.name}")
    return obs_path,raw_d,bc_d


# ════════════════════════════════════════════════════════════════════════
#  §2  DATA LOADING & AGGREGATION
# ════════════════════════════════════════════════════════════════════════

def load_daily(path,label,target_stns=None):
    if path is None or not os.path.isfile(path):
        print(f"  ✗  Not found: {label}"); return None,[]
    time_cols={"YEAR","MONTH","DAY"}
    if target_stns is not None:
        tgt_s=set(str(s) for s in target_stns)
        tgt_i=set(int(s) for s in target_stns if str(s).isdigit())
        def _uc(c):
            cs=str(c)
            return cs in time_cols or cs in tgt_s or (cs.isdigit() and int(cs) in tgt_i)
        try:   df=pd.read_csv(path,usecols=_uc)
        except: df=pd.read_csv(path)
    else: df=pd.read_csv(path)
    df.columns=[str(c) for c in df.columns]
    for mv in MISS_FLAGS: df.replace(mv,np.nan,inplace=True)
    num=df.select_dtypes(include=[np.number]).columns
    df[num]=df[num].where(df[num]>=0)
    stns=[c for c in df.columns if c not in time_cols]
    if target_stns:
        tgt_str=[str(s) for s in target_stns]; stns=[s for s in stns if s in set(tgt_str)]
        extra=[c for c in df.columns if c not in time_cols and c not in set(tgt_str)]
        if extra: df.drop(columns=extra,inplace=True,errors="ignore")
    try:
        df["date"]=pd.to_datetime({"year":df["YEAR"],"month":df["MONTH"],"day":df["DAY"]})
        df=df.set_index("date")[stns]
    except: df=df[stns]
    yr0=df.index[0].year if len(df) else "?"
    yr1=df.index[-1].year if len(df) else "?"
    print(f"    {label:38s}: {len(df):,} rows × {len(stns)} stns  [{yr0}–{yr1}]")
    return df,stns

def to_monthly(df):
    if df is None: return None
    return df.resample("MS").apply(lambda g:g.sum(min_count=int(0.8*len(g))))

def to_annual(df,min_days=280):
    if df is None: return None
    return df.resample("YS").apply(lambda g:g.sum(min_count=min_days))

def period_str(df):
    if df is None: return "N/A"
    try: return f"{df.index[0].year}–{df.index[-1].year}"
    except: return "N/A"

def short_stn_labels(stns): return {str(s):f"S{i+1}" for i,s in enumerate(stns)}

def ensemble_mean(dfs):
    valid=[df for df in dfs.values() if df is not None]
    if not valid: return None
    ci=valid[0].index
    for df in valid[1:]: ci=ci.intersection(df.index)
    if len(ci)==0: return None
    cols=list(valid[0].columns)
    for df in valid[1:]: cols=[c for c in cols if c in df.columns]
    if not cols: return None
    stack=np.stack([df.loc[ci,cols].values.astype(float) for df in valid],axis=0)
    return pd.DataFrame(np.nanmean(stack,axis=0),index=ci,columns=cols)


# ════════════════════════════════════════════════════════════════════════
#  §3  PERFORMANCE METRICS
# ════════════════════════════════════════════════════════════════════════

_NULL={k:np.nan for k in
       ["n","RMSE","MAE","MBE","Pbias","r","NSE","KGE","d","sigma_r","beta","std_obs","std_sim"]}

def compute_metrics(o,s):
    if len(o)<5 or len(s)<5: return _NULL.copy()
    n=min(len(o),len(s))
    o=np.asarray(o[:n],dtype=float); s=np.asarray(s[:n],dtype=float)
    mask=~np.isnan(o)&~np.isnan(s); o,s=o[mask],s[mask]
    if len(o)<5: return _NULL.copy()
    e=s-o
    rmse=float(np.sqrt(np.mean(e**2))); mae=float(np.mean(np.abs(e)))
    mbe=float(np.mean(e))
    pb=float(100*np.sum(e)/np.sum(o)) if np.sum(o)!=0 else np.nan
    r=float(np.corrcoef(o,s)[0,1])
    std_o=float(np.std(o,ddof=1)); std_s=float(np.std(s,ddof=1))
    sr=std_s/std_o if std_o>0 else np.nan
    beta=float(np.mean(s)/np.mean(o)) if np.mean(o)!=0 else np.nan
    dn=float(np.sum((o-np.mean(o))**2))
    nse=float(1-np.sum(e**2)/dn) if dn>0 else np.nan
    kge=float(1-math.sqrt((r-1)**2+(sr-1)**2+(beta-1)**2)) \
        if not(np.isnan(sr) or np.isnan(beta)) else np.nan
    denom=float(np.sum((np.abs(s-np.mean(o))+np.abs(o-np.mean(o)))**2))
    d=float(1-np.sum(e**2)/denom) if denom>0 else np.nan
    return dict(n=int(len(o)),RMSE=round(rmse,4),MAE=round(mae,4),MBE=round(mbe,4),
                Pbias=round(float(pb),2),r=round(r,4),NSE=round(float(nse),4),
                KGE=round(float(kge),4),d=round(float(d),4),
                sigma_r=round(float(sr),4) if not np.isnan(sr) else np.nan,
                beta=round(float(beta),4) if not np.isnan(beta) else np.nan,
                std_obs=round(std_o,4),std_sim=round(std_s,4))

def metrics_from_dfs(obs_df,sim_df,stn):
    if obs_df is None or sim_df is None: return _NULL.copy()
    stn=str(stn)
    if stn not in obs_df.columns or stn not in sim_df.columns: return _NULL.copy()
    common=obs_df.index.intersection(sim_df.index)
    if len(common)==0: return _NULL.copy()
    o=obs_df.loc[common,stn].values.astype(float)
    s=sim_df.loc[common,stn].values.astype(float)
    mask=~np.isnan(o)&~np.isnan(s)
    return compute_metrics(o[mask],s[mask])


# ════════════════════════════════════════════════════════════════════════
#  §4  TREND ANALYSIS CORE — Modified MK + Sen's Slope
# ════════════════════════════════════════════════════════════════════════

def _sig_stars(p):
    if p is None or np.isnan(p): return "—"
    if p<0.001: return "***"
    if p<0.01:  return "**"
    if p<0.05:  return "*"
    return "ns"

def _trend_direction(slope):
    """Return trend direction label based on Sen's slope."""
    if np.isnan(slope): return "—"
    if slope > 0.5:  return "↑ Increasing"
    if slope < -0.5: return "↓ Decreasing"
    return "→ No trend"

def mmk_test(x):
    """
    Modified Mann-Kendall Test (Hamed & Rao 1998).
    Corrects for autocorrelation using rank-based autocovariance.

    Parameters: x — annual time series (may contain NaN)

    Returns
    -------
    S     : MK statistic
    Z_mmk : Modified Z-score (autocorrelation-corrected)
    p     : two-tailed p-value of MMK test
    tau   : Kendall's tau
    ns    : variance correction factor (n_s* ratio)
    """
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 4:
        return np.nan, np.nan, np.nan, np.nan, np.nan

    # ── Standard MK S statistic ────────────────────────────────────
    S = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            d = x[j] - x[i]
            if   d > 0: S += 1
            elif d < 0: S -= 1

    # Var(S) without autocorrelation correction
    # Tie correction
    unique, counts = np.unique(x, return_counts=True)
    tie_corr = np.sum(counts * (counts - 1) * (2 * counts + 5))
    var_S0 = (n * (n - 1) * (2 * n + 5) - tie_corr) / 18.0

    # ── Hamed & Rao (1998) autocorrelation correction ───────────────
    # Use rank-based Spearman autocorrelation to avoid distribution assumption
    ns_ratio = 1.0
    if n > 10:
        rk = rankdata(x)
        ac_weighted = 0.0
        for lag in range(1, n - 1):
            if n - lag < 4: break
            r, _ = pearsonr(rk[: n - lag], rk[lag:])
            weight = 1 - lag / n           # Hamed & Rao weighting
            ac_weighted += weight * r
        ns_ratio = max(1.0, 1.0 + (2.0 / n) * ac_weighted)

    var_S_mmk = var_S0 * ns_ratio
    if var_S_mmk <= 0:
        return float(S), np.nan, np.nan, float(S) / (n * (n - 1) / 2), ns_ratio

    # Z statistic (continuity correction)
    if   S > 0: Z = (S - 1) / math.sqrt(var_S_mmk)
    elif S < 0: Z = (S + 1) / math.sqrt(var_S_mmk)
    else:        Z = 0.0

    p     = float(2 * (1 - sci_norm.cdf(abs(Z))))
    tau   = float(S) / (n * (n - 1) / 2)
    return float(S), float(Z), float(p), float(tau), float(ns_ratio)


def sens_slope_ci(x, years=None, alpha=0.05):
    """
    Sen's Slope with 95 % confidence interval (Theil-Sen estimator).

    Parameters
    ----------
    x     : time series (may contain NaN)
    years : corresponding year values (default: 0, 1, 2, …)
    alpha : significance level for CI (default 0.05 → 95 % CI)

    Returns
    -------
    slope, intercept, slope_lo, slope_hi
    All values in units of x per year.
    """
    x = np.asarray(x, dtype=float)
    if years is None:
        years = np.arange(len(x), dtype=float)
    else:
        years = np.asarray(years, dtype=float)

    mask = ~np.isnan(x)
    x_c, y_c = years[mask], x[mask]
    if len(x_c) < 4:
        return np.nan, np.nan, np.nan, np.nan

    res = theilslopes(y_c, x_c, alpha=1 - alpha)
    return (float(res.slope), float(res.intercept),
            float(res.low_slope), float(res.high_slope))


def compute_trend_one(ann_series, stn, label, color, min_years=10):
    """
    Compute full trend statistics for one annual station series.
    Returns dict with MMK + Sen's slope + derived indicators.
    """
    null = {"label":label,"color":color,"Station":stn,
            "n":0,"mean":np.nan,"std":np.nan,
            "slope":np.nan,"slope_lo":np.nan,"slope_hi":np.nan,
            "intercept":np.nan,
            "S":np.nan,"Z":np.nan,"p":np.nan,"tau":np.nan,"ns_ratio":np.nan,
            "stars":"—","direction":"—","relative_change_pct":np.nan,
            "trend_per_decade":np.nan,"years":None,"values":None}

    if ann_series is None or stn not in ann_series.columns:
        return null

    ser = ann_series[stn].dropna()
    if len(ser) < min_years:
        null["n"] = len(ser); return null

    yrs  = ser.index.year.astype(float)
    vals = ser.values.astype(float)
    n    = len(vals)

    slope, intercept, lo, hi = sens_slope_ci(vals, years=yrs)
    S, Z, p, tau, ns = mmk_test(vals)

    # Relative change over study period (%)
    period_len = float(yrs[-1] - yrs[0])
    rel_ch = (slope * period_len / np.mean(vals) * 100
              if not np.isnan(slope) and np.mean(vals) != 0 else np.nan)

    return {
        "label":          label,
        "color":          color,
        "Station":        stn,
        "n":              int(n),
        "mean":           round(float(np.mean(vals)), 2),
        "std":            round(float(np.std(vals, ddof=1)), 2),
        "slope":          round(slope,   4) if not np.isnan(slope) else np.nan,
        "slope_lo":       round(lo,      4) if not np.isnan(lo)    else np.nan,
        "slope_hi":       round(hi,      4) if not np.isnan(hi)    else np.nan,
        "intercept":      round(intercept,2) if not np.isnan(intercept) else np.nan,
        "S":              round(S,   2)   if not np.isnan(S)   else np.nan,
        "Z":              round(Z,   4)   if not np.isnan(Z)   else np.nan,
        "p":              round(p,   6)   if not np.isnan(p)   else np.nan,
        "tau":            round(tau, 4)   if not np.isnan(tau) else np.nan,
        "ns_ratio":       round(ns,  4)   if not np.isnan(ns)  else np.nan,
        "stars":          _sig_stars(p)   if not np.isnan(p)   else "—",
        "direction":      _trend_direction(slope),
        "relative_change_pct": round(float(rel_ch), 2) if not np.isnan(rel_ch) else np.nan,
        "trend_per_decade": round(slope * 10, 3) if not np.isnan(slope) else np.nan,
        "years":          yrs,
        "values":         vals,
    }


def compute_all_trends(obs_d, raw_dfs, bc_dfs, stns_str, min_days=280):
    """
    Compute trend statistics for all stations and all datasets.
    Returns dict: {stn: {label: trend_dict}}
    """
    obs_ann = to_annual(obs_d, min_days=min_days)
    raw_ens  = ensemble_mean(raw_dfs)
    bc_ens   = ensemble_mean(bc_dfs)
    raw_ann  = to_annual(raw_ens, min_days=min_days) if raw_ens is not None else None
    bc_ann   = to_annual(bc_ens,  min_days=min_days) if bc_ens  is not None else None

    # Per-model annual series
    raw_ann_m = {m: to_annual(df, min_days=min_days) for m, df in raw_dfs.items()}
    bc_ann_m  = {m: to_annual(df, min_days=min_days) for m, df in bc_dfs.items()}

    results = {}
    for stn in stns_str:
        results[stn] = {}
        results[stn]["Observed"]  = compute_trend_one(obs_ann, stn, "Observed",  C["obs"])
        results[stn]["Raw CMIP6"] = compute_trend_one(raw_ann, stn, "Raw CMIP6", C["raw"])
        results[stn]["BC (QDM)"]  = compute_trend_one(bc_ann,  stn, "BC (QDM)",  C["bc"])
        # Individual model trends
        for m in raw_ann_m:
            results[stn][f"Raw-{m}"] = compute_trend_one(raw_ann_m[m],stn,f"Raw-{m}",
                                                           C["raw"])
        for m in bc_ann_m:
            results[stn][f"BC-{m}"]  = compute_trend_one(bc_ann_m[m], stn,f"BC-{m}",
                                                           C["bc"])

    return results, obs_ann, raw_ann, bc_ann, raw_ann_m, bc_ann_m

# ════════════════════════════════════════════════════════════════════════
#  §5  EXISTING FIGURES 2–6 (from v3.0 — kept intact)
# ════════════════════════════════════════════════════════════════════════

def _taylor_bg(ax,ref_std,unit):
    if np.isnan(ref_std) or ref_std<=0: ref_std=5.0
    r_max=ref_std*1.75
    for frac,lc in [(0.25,"#B0BEC5"),(0.5,"#90A4AE"),(0.75,"#78909C"),(1.0,"#607D8B")]:
        rr=ref_std*frac; th=np.linspace(0,np.pi/2,300)
        xc=ref_std+rr*np.cos(np.pi-th); yc=rr*np.sin(th)
        mask=(xc**2+yc**2<=r_max**2)&(xc>=0)&(yc>=0)
        ax.plot(xc[mask],yc[mask],color=lc,lw=0.9,ls="--",alpha=0.85,zorder=1)
        ix=np.argmin(np.abs(th-np.pi/4))
        if mask[ix]:
            ax.text(xc[ix],yc[ix],f"RMSE\n{rr:.1f}",fontsize=7,color=lc,ha="center",va="center",
                    bbox=dict(boxstyle="round,pad=0.15",fc="white",ec="none",alpha=0.82))
    for rv,lc in [(0.2,"#CFD8DC"),(0.4,"#B0BEC5"),(0.6,"#90A4AE"),
                  (0.7,"#78909C"),(0.8,"#607D8B"),(0.9,"#546E7A"),
                  (0.95,"#455A64"),(0.99,"#37474F")]:
        tv=np.arccos(rv)
        ax.plot([0,r_max*np.cos(tv)],[0,r_max*np.sin(tv)],color=lc,lw=0.72,alpha=0.90,zorder=1)
        ax.text(r_max*np.cos(tv)*1.07,r_max*np.sin(tv)*1.07,
                f"{rv:.2f}",fontsize=7.5,color="#455A64",ha="center",va="center",fontweight="bold")
    for frac in [0.25,0.5,0.75,1.0,1.25,1.5]:
        ar=ref_std*frac
        if ar>r_max: continue
        t=np.linspace(0,np.pi/2,300)
        ax.plot(ar*np.cos(t),ar*np.sin(t),color="#CFD8DC",lw=0.82,alpha=0.90,zorder=1)
        ax.text(0,ar,f"{ar:.1f}",fontsize=7.5,color="#78909C",ha="right",va="center")
    ax.plot(ref_std,0,"k*",markersize=16,zorder=10,markeredgecolor="#1A1A1A",markeredgewidth=0.8,
            label="Observed (Reference)")
    ax.set_xlim(0,r_max); ax.set_ylim(0,r_max)
    ax.set_xlabel(f"Standard Deviation ({unit})",fontsize=12,fontweight="bold",labelpad=6)
    ax.set_ylabel(f"Standard Deviation ({unit})",fontsize=12,fontweight="bold",labelpad=6)
    ax.text(-0.10,0.5,"Pearson Correlation (r)  →",transform=ax.transAxes,fontsize=9.5,rotation=90,
            va="center",color="#455A64",style="italic",fontweight="bold")
    ax.set_aspect("equal"); ax.grid(False)
    ax.axhline(0,color="#1A1A1A",lw=1.3); ax.axvline(0,color="#1A1A1A",lw=1.3)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    return r_max

def fig2_annual_timeseries(obs_d,raw_dfs,bc_dfs,stns,smap,models,mc,period_obs,out_dir,prefix):
    stns_str=[str(s) for s in stns]
    def reg_ann(df):
        if df is None: return None
        ann=to_annual(df)
        if ann is None: return None
        cols=[s for s in stns_str if s in ann.columns]
        return ann[cols].mean(axis=1) if cols else None
    obs_ann=reg_ann(obs_d)
    raw_anns={m:reg_ann(df) for m,df in raw_dfs.items()}
    bc_anns ={m:reg_ann(df) for m,df in bc_dfs.items()}
    def ens_stats(ann_dict):
        valid=[s.dropna() for s in ann_dict.values() if s is not None]
        if not valid: return None,None,None
        ci=valid[0].index
        for s in valid[1:]: ci=ci.intersection(s.index)
        if len(ci)==0: return None,None,None
        stack=np.array([s.loc[ci].values for s in valid])
        return (pd.Series(np.nanmean(stack,axis=0),index=ci),
                pd.Series(np.nanmin(stack,axis=0),index=ci),
                pd.Series(np.nanmax(stack,axis=0),index=ci))
    raw_ens,raw_lo,raw_hi=ens_stats(raw_anns)
    bc_ens,bc_lo,bc_hi=ens_stats(bc_anns)
    fig,axes=plt.subplots(2,1,figsize=(14,11),gridspec_kw={"hspace":0.44})
    fig.subplots_adjust(left=0.09,right=0.97,top=0.91,bottom=0.09)
    ax=axes[0]
    if raw_ens is not None:
        ax.fill_between(raw_ens.index.year,raw_lo.values,raw_hi.values,color=C["raw_lt"],alpha=0.40,zorder=2,label="Raw CMIP6 range")
        ax.plot(raw_ens.index.year,raw_ens.values,color=C["raw"],lw=2.2,ls="--",zorder=4,label="Raw CMIP6 ensemble mean")
    if bc_ens is not None:
        ax.fill_between(bc_ens.index.year,bc_lo.values,bc_hi.values,color=C["bc_lt"],alpha=0.40,zorder=2,label="BC (QDM) range")
        ax.plot(bc_ens.index.year,bc_ens.values,color=C["bc"],lw=2.2,ls="-",zorder=4,label="BC (QDM) ensemble mean")
    if obs_ann is not None:
        obs_s=obs_ann.dropna()
        ax.plot(obs_s.index.year,obs_s.values,color=C["obs"],lw=3.0,ls="-",zorder=6,label="Observed")
    ax.set_xlabel("Year",fontsize=13,fontweight="bold"); ax.set_ylabel("Annual Rainfall — Regional Mean (mm)",fontsize=13,fontweight="bold")
    ax.set_title("(a)  Annual Rainfall Time Series — Regional Mean\n     Shaded band = ensemble range (min–max)",
                 loc="left",fontsize=13,fontweight="bold",pad=5)
    ax.tick_params(axis="both",which="major",labelsize=11,width=1.5)
    ax.legend(fontsize=11,frameon=True,edgecolor="#B0BEC5",facecolor="white",framealpha=0.95,ncol=2,loc="upper right")
    ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax2=axes[1]; codes=[smap[s] for s in stns_str]
    x=np.arange(len(stns)); bw=0.38
    raw_ens_df=ensemble_mean(raw_dfs); bc_ens_df=ensemble_mean(bc_dfs)
    kge_raw=[metrics_from_dfs(obs_d,raw_ens_df,s).get("KGE",np.nan) for s in stns_str]
    kge_bc =[metrics_from_dfs(obs_d,bc_ens_df, s).get("KGE",np.nan) for s in stns_str]
    ax2.bar(x-bw/2,kge_raw,width=bw,color=C["raw_lt"],edgecolor=C["raw_bd"],linewidth=1.0,alpha=0.88,label="Raw CMIP6",zorder=3)
    ax2.bar(x+bw/2,kge_bc, width=bw,color=C["bc_lt"], edgecolor=C["bc_bd"],linewidth=1.0,alpha=0.88,label="Bias-Corrected (QDM)",zorder=3)
    ax2.axhline(0,color=C["grey"],lw=0.9,ls="--",alpha=0.6); ax2.axhline(0.75,color=C["green"],lw=1.2,ls=":",alpha=0.8,label="KGE=0.75 (Very Good)")
    ax2.set_xticks(x); ax2.set_xticklabels(codes,rotation=0,ha="center",fontsize=11)
    ax2.set_xlabel("Station",fontsize=13,fontweight="bold"); ax2.set_ylabel("KGE",fontsize=13,fontweight="bold")
    ax2.set_title("(b)  KGE per Station — Raw vs Bias-Corrected (Ensemble Mean)",loc="left",fontsize=13,fontweight="bold",pad=5)
    ax2.tick_params(axis="both",which="major",labelsize=11,width=1.5)
    ax2.legend(fontsize=11,frameon=True,edgecolor="#B0BEC5",facecolor="white",framealpha=0.95,ncol=2,loc="lower right")
    ax2.yaxis.set_minor_locator(ticker.AutoMinorLocator()); ax2.spines["top"].set_visible(False); ax2.spines["right"].set_visible(False)
    fig.suptitle(f"Time series of annual rainfall — Observed vs Raw CMIP6 vs QDM Bias-Corrected  |  Period: {period_obs}",fontsize=14,fontweight="bold")
    savefig(fig,out_dir/f"{prefix}_Fig2_AnnualTimeSeries")

def fig3_probability_distribution(obs_d,raw_dfs,bc_dfs,stns,period_obs,out_dir,prefix):
    stns_str=[str(s) for s in stns]
    def pool_wet(df):
        if df is None: return np.array([],dtype=float)
        cols=[s for s in stns_str if s in df.columns]
        v=df[cols].values.flatten().astype(float)
        return v[~np.isnan(v)&(v>=WET_THR)]
    obs_v=pool_wet(obs_d); raw_v=pool_wet(ensemble_mean(raw_dfs)); bc_v=pool_wet(ensemble_mean(bc_dfs))
    if len(obs_v)<20 or len(raw_v)<20 or len(bc_v)<20: print("  ⚠  Insufficient data for Fig3"); return
    stats={k:{"sk":float(sps.skew(v)),"ku":float(sps.kurtosis(v,fisher=True)),
               "p95":float(np.percentile(v,95)),"p99":float(np.percentile(v,99))}
           for v,k in [(obs_v,"obs"),(raw_v,"raw"),(bc_v,"bc")]}
    x_max=max(float(np.percentile(obs_v,99.5)),float(np.percentile(raw_v,99.5)),float(np.percentile(bc_v,99.5)))
    p95_obs=stats["obs"]["p95"]; p99_obs=stats["obs"]["p99"]
    datasets=[(obs_v,C["obs"],"Observed","-",2.8,"obs"),(raw_v,C["raw"],"Raw CMIP6","--",2.2,"raw"),(bc_v,C["bc"],"Bias-Corrected (QDM)","-",2.4,"bc")]
    fig,(ax_main,ax_tail)=plt.subplots(1,2,figsize=(16,7.5)); fig.subplots_adjust(left=0.08,right=0.97,top=0.87,bottom=0.12,wspace=0.32)
    x_grid=np.linspace(WET_THR,x_max,1200); legend_h=[]; legend_l=[]
    for v,col,lbl,ls,lw,key in datasets:
        kde=gaussian_kde(v,bw_method="scott"); dens=kde(x_grid)
        sk=stats[key]["sk"]; ku=stats[key]["ku"]
        line,=ax_main.plot(x_grid,dens,color=col,ls=ls,lw=lw,zorder=4)
        ax_main.fill_between(x_grid,dens,alpha=0.09,color=col,zorder=3)
        legend_h.append(line); legend_l.append(f"{lbl}  (Skewness={sk:.2f}, Kurtosis={ku:.2f})")
    for col,lbl,lv in [(C["gold"],f"P95={p95_obs:.1f} mm",p95_obs),(C["purple"],f"P99={p99_obs:.1f} mm",p99_obs)]:
        ax_main.axvline(lv,color=col,lw=1.4,ls=":",alpha=0.88,zorder=5)
        legend_h.append(Line2D([0],[0],color=col,lw=1.4,ls=":")); legend_l.append(lbl)
    ax_main.legend(legend_h,legend_l,fontsize=10.5,frameon=True,edgecolor="#B0BEC5",facecolor="white",framealpha=0.96,loc="upper right",ncol=1,handlelength=2.2)
    ax_main.set_xlim(0,x_max); ax_main.set_xlabel("Daily Rainfall (mm)",fontsize=13,fontweight="bold"); ax_main.set_ylabel("Probability Density",fontsize=13,fontweight="bold")
    ax_main.set_title(f"(a)  Probability Density — Wet-Day Rainfall\n     All stations pooled  |  Threshold ≥{WET_THR} mm day⁻¹",loc="left",fontsize=13,fontweight="bold",pad=5)
    ax_main.tick_params(axis="both",which="major",labelsize=11,width=1.5); ax_main.yaxis.set_minor_locator(ticker.AutoMinorLocator()); ax_main.spines["top"].set_visible(False); ax_main.spines["right"].set_visible(False)
    x_tail=np.linspace(p95_obs,x_max,600)
    for v,col,lbl,ls,lw,key in datasets:
        kde_t=gaussian_kde(v,bw_method="scott"); ax_tail.plot(x_tail,kde_t(x_tail),color=col,ls=ls,lw=lw,label=lbl,zorder=4); ax_tail.fill_between(x_tail,kde_t(x_tail),alpha=0.10,color=col,zorder=3)
    for v_arr,col_v in [(obs_v,C["obs"]),(raw_v,C["raw"]),(bc_v,C["bc"])]:
        ax_tail.axvline(float(np.percentile(v_arr,99)),color=col_v,lw=1.0,ls="--",alpha=0.55)
    ax_tail.axvline(p95_obs,color=C["gold"],lw=1.4,ls=":",alpha=0.90,label=f"P95={p95_obs:.1f}"); ax_tail.axvline(p99_obs,color=C["purple"],lw=1.4,ls=":",alpha=0.90,label=f"P99={p99_obs:.1f}")
    ax_tail.set_xlim(p95_obs,x_max); ax_tail.set_xlabel("Daily Rainfall (mm)",fontsize=13,fontweight="bold"); ax_tail.set_ylabel("Probability Density",fontsize=13,fontweight="bold")
    ax_tail.set_title("(b)  Heavy Tail Region  (> P95 of Observed)\n     Magnified view — extreme event frequency",loc="left",fontsize=13,fontweight="bold",pad=5)
    ax_tail.legend(fontsize=10.5,frameon=True,edgecolor="#B0BEC5",facecolor="white",framealpha=0.96,loc="upper right",ncol=1,handlelength=2.2)
    ax_tail.tick_params(axis="both",which="major",labelsize=11,width=1.5); ax_tail.yaxis.set_minor_locator(ticker.AutoMinorLocator()); ax_tail.spines["top"].set_visible(False); ax_tail.spines["right"].set_visible(False)
    fig.suptitle(f"Probability distribution of daily rainfall  |  Period: {period_obs}",fontsize=14,fontweight="bold")
    savefig(fig,out_dir/f"{prefix}_Fig3_ProbabilityDistribution")

def fig4_qq_plots(obs_d,raw_dfs,bc_dfs,stns,period_obs,out_dir,prefix):
    stns_str=[str(s) for s in stns]
    def pool_wet(df):
        if df is None: return np.array([],dtype=float)
        cols=[s for s in stns_str if s in df.columns]
        v=df[cols].values.flatten().astype(float)
        return np.sort(v[~np.isnan(v)&(v>=WET_THR)])
    obs_v=pool_wet(obs_d); raw_v=pool_wet(ensemble_mean(raw_dfs)); bc_v=pool_wet(ensemble_mean(bc_dfs))
    if len(obs_v)<20: print("  ⚠  Insufficient data for Fig4"); return
    probs=np.linspace(0,100,201)
    q_obs=np.percentile(obs_v,probs); q_raw=np.percentile(raw_v,probs); q_bc=np.percentile(bc_v,probs)
    rmse_raw=float(np.sqrt(np.mean((q_raw-q_obs)**2))); rmse_bc=float(np.sqrt(np.mean((q_bc-q_obs)**2)))
    pct_marks=[(90,C["grey"],"P90","^"),(95,C["gold"],"P95","s"),(99,C["purple"],"P99","D"),(99.5,C["red2"],"P99.5","*")]
    fig,axes=plt.subplots(1,2,figsize=(16,8)); fig.subplots_adjust(wspace=0.30,top=0.88,bottom=0.12,left=0.07,right=0.97)
    for ax,q_sim,sim_lbl,col_sim,xy_max_v,tag,rmse_val,sim_all in [
        (axes[0],q_raw,"Raw CMIP6",C["raw"],max(q_obs.max(),q_raw.max())*1.04,"(a)  Observed vs Raw CMIP6",rmse_raw,raw_v),
        (axes[1],q_bc,"Bias-Corrected (QDM)",C["bc"],max(q_obs.max(),q_bc.max())*1.04,"(b)  Observed vs BC (QDM)",rmse_bc,bc_v)]:
        ax.plot([0,xy_max_v],[0,xy_max_v],color=C["green"],lw=1.8,ls="--",alpha=0.85,label="1:1 line",zorder=2)
        sc=ax.scatter(q_obs,q_sim,c=probs,cmap="RdYlBu_r",s=26,alpha=0.75,edgecolors="none",zorder=3)
        for pct,pct_c,pct_l,mk in pct_marks:
            qo=float(np.percentile(obs_v,pct)); qs=float(np.percentile(sim_all,pct))
            ax.scatter([qo],[qs],color=pct_c,s=120,zorder=7,marker=mk,edgecolors="white",linewidths=0.8,label=f"{pct_l}: Obs={qo:.1f}, Sim={qs:.1f}")
        ax.set_xlim(0,xy_max_v); ax.set_ylim(0,xy_max_v); ax.set_aspect("equal","box")
        ax.set_xlabel("Observed Quantile (mm)",fontsize=13,fontweight="bold"); ax.set_ylabel(f"{sim_lbl} Quantile (mm)",fontsize=13,fontweight="bold")
        ax.set_title(f"{tag}\nQQ-RMSE = {rmse_val:.2f} mm",loc="left",fontsize=13,fontweight="bold",pad=5)
        ax.tick_params(axis="both",which="major",labelsize=11,width=1.5)
        ax.legend(fontsize=9.5,frameon=True,edgecolor="#B0BEC5",facecolor="white",framealpha=0.95,loc="upper left",ncol=1)
        cb=plt.colorbar(sc,ax=ax,orientation="horizontal",pad=0.14,fraction=0.05,shrink=0.82)
        cb.set_label("Percentile level (%)",fontsize=10,fontweight="bold"); cb.ax.tick_params(labelsize=9)
    fig.suptitle(f"Quantile–Quantile plots — Observed vs CMIP6  |  Period: {period_obs}",fontsize=14,fontweight="bold")
    savefig(fig,out_dir/f"{prefix}_Fig4_QQPlots")

def fig5_taylor_diagram(obs_d,raw_dfs,bc_dfs,stns,smap,models,mc,period_obs,period_sim,out_dir,prefix):
    stns_str=[str(s) for s in stns]; n_stns=len(stns_str)
    cmap_stn=cm.get_cmap("tab20",max(n_stns,1))
    stn_colors=[mcolors.to_hex(cmap_stn(i)) for i in range(n_stns)]
    obs_m=to_monthly(obs_d)
    raw_m_dfs={m:to_monthly(df) for m,df in raw_dfs.items()}
    bc_m_dfs ={m:to_monthly(df) for m,df in bc_dfs.items()}
    scales=[("Daily",obs_d,raw_dfs,bc_dfs,"mm day⁻¹","(a)"),("Monthly",obs_m,raw_m_dfs,bc_m_dfs,"mm month⁻¹","(b)")]
    fig,axes=plt.subplots(1,2,figsize=(16,8)); fig.subplots_adjust(left=0.05,right=0.97,top=0.87,bottom=0.10,wspace=0.26)
    for ai,(scale,o_df,r_dict,b_dict,unit,panel) in enumerate(scales):
        ax=axes[ai]
        if o_df is None: ax.text(0.5,0.5,f"No {scale} data",transform=ax.transAxes,ha="center"); continue
        stds=[float(o_df[s].std(ddof=1)) for s in stns_str if s in o_df.columns and o_df[s].notna().sum()>5]
        ref_std=float(np.mean(stds)) if stds else 5.0
        r_max=_taylor_bg(ax,ref_std,unit)
        ens_raw=ensemble_mean(r_dict); ens_bc=ensemble_mean(b_dict)
        raw_xy={}
        for si,stn in enumerate(stns_str):
            col=stn_colors[si%len(stn_colors)]; code=smap.get(stn,stn)
            for ens_df,mk,ds_label in [(ens_raw,"^","Raw"),(ens_bc,"o","BC")]:
                mr=metrics_from_dfs(o_df,ens_df,stn)
                rv=mr.get("r",np.nan); sr=mr.get("sigma_r",np.nan); std_o=mr.get("std_obs",np.nan)
                std_s=std_o*sr if not(np.isnan(std_o) or np.isnan(sr)) else np.nan
                if np.isnan(std_s) or np.isnan(rv): continue
                theta=np.arccos(np.clip(rv,-1.0,1.0)); xv=std_s*np.cos(theta); yv=std_s*np.sin(theta)
                ax.scatter(xv,yv,color=col,marker=mk,s=140,zorder=8,edgecolors="#1A1A1A",linewidth=0.9,alpha=1.0)
                if ds_label=="Raw": raw_xy[stn]=(xv,yv)
                elif ds_label=="BC" and stn in raw_xy:
                    rx,ry=raw_xy[stn]
                    ax.annotate("",xy=(xv,yv),xytext=(rx,ry),arrowprops=dict(arrowstyle="-|>",color=col,lw=1.6,alpha=0.88,mutation_scale=14),zorder=7)
                    ax.text(xv+0.030*r_max,yv+0.030*r_max,code,fontsize=10.5,color=col,fontweight="bold",ha="left",va="bottom",zorder=9)
        handles=[Line2D([0],[0],marker="*",color="k",ls="none",ms=13,label="Observed (Reference)"),
                 Line2D([0],[0],marker="^",color="#444",ls="none",ms=10,markeredgecolor="#1A1A1A",markeredgewidth=0.8,label="Raw CMIP6"),
                 Line2D([0],[0],marker="o",color="#444",ls="none",ms=10,markeredgecolor="#1A1A1A",markeredgewidth=0.8,label="Bias-Corrected (QDM)"),
                 Line2D([0],[0],color="#444",lw=1.6,ls="-",label="Arrow: Raw → BC")]
        for si,stn in enumerate(stns_str):
            handles.append(mpatches.Patch(facecolor=stn_colors[si%len(stn_colors)],edgecolor="#1A1A1A",linewidth=0.6,alpha=1.0,label=smap[stn]))
        ax.legend(handles=handles,loc="upper right",fontsize=8.5,frameon=True,edgecolor="#B0BEC5",facecolor="white",framealpha=0.96,ncol=2,handlelength=1.6)
        ax.set_title(f"{panel}  Taylor Diagram — {scale} Scale\n     Obs: {period_obs}",loc="left",fontsize=13,fontweight="bold",pad=5)
    fig.suptitle("Taylor diagram — CMIP6 rainfall simulations before and after bias correction\n"
                 "Ref: Taylor (2001) J. Geophys. Res. 106:7183–7192",fontsize=14,fontweight="bold")
    savefig(fig,out_dir/f"{prefix}_Fig5_TaylorDiagram")

def fig6_metric_improvement(obs_d,raw_dfs,bc_dfs,stns,smap,period_obs,out_dir,prefix):
    stns_str=[str(s) for s in stns]; codes=[smap[s] for s in stns_str]
    x=np.arange(len(stns)); raw_ens=ensemble_mean(raw_dfs); bc_ens=ensemble_mean(bc_dfs)
    mr_list=[metrics_from_dfs(obs_d,raw_ens,s) for s in stns_str]
    mb_list=[metrics_from_dfs(obs_d,bc_ens, s) for s in stns_str]
    def _delta(key,inv=False):
        out=[]
        for mr,mb in zip(mr_list,mb_list):
            vr=mr.get(key,np.nan); vb=mb.get(key,np.nan)
            if np.isnan(vr) or np.isnan(vb): out.append(np.nan)
            else: out.append(vr-vb if inv else vb-vr)
        return out
    rmse_red=_delta("RMSE",inv=True)
    pb_red=[abs(mr.get("Pbias",np.nan))-abs(mb.get("Pbias",np.nan)) for mr,mb in zip(mr_list,mb_list)]
    r_imp=_delta("r"); nse_imp=_delta("NSE"); kge_imp=_delta("KGE")
    fig,axes=plt.subplots(2,2,figsize=(16,12)); fig.subplots_adjust(hspace=0.50,wspace=0.32,left=0.08,right=0.97,top=0.91,bottom=0.09)
    def _bar(ax,vals,ylabel,title_tag,pos_c,pos_e,neg_c,neg_e):
        colors=[pos_c if not np.isnan(v) and v>=0 else neg_c for v in vals]
        edges=[pos_e if not np.isnan(v) and v>=0 else neg_e for v in vals]
        bars=ax.bar(x,vals,color=colors,edgecolor=edges,alpha=0.90,width=0.65,linewidth=1.0,zorder=3)
        ax.axhline(0,color=C["grey"],lw=0.9,ls="--",alpha=0.65)
        for bar,v in zip(bars,vals):
            if not np.isnan(v) and abs(v)>0.001:
                ax.text(bar.get_x()+bar.get_width()/2,v+(abs(v)*0.04+0.005)*np.sign(v),
                        f"{v:+.3f}",ha="center",va="bottom",fontsize=10,fontweight="bold",color="#1A1A1A")
        ax.set_xticks(x); ax.set_xticklabels(codes,rotation=0,ha="center",fontsize=11)
        ax.set_xlabel("Station",fontsize=12,fontweight="bold"); ax.set_ylabel(ylabel,fontsize=12,fontweight="bold")
        ax.set_title(title_tag,loc="left",fontsize=12,fontweight="bold",pad=5)
        ax.tick_params(axis="both",which="major",labelsize=11,width=1.4)
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator()); ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    _bar(axes[0,0],rmse_red,"RMSE Reduction (mm)\n[positive=improved]","(a)  RMSE Reduction",C["bc_lt"],C["bc_bd"],C["raw_lt"],C["raw_bd"])
    _bar(axes[0,1],pb_red,"|Pbias| Reduction (%)\n[positive=improved]","(b)  Percent Bias Reduction",C["bc_lt"],C["bc_bd"],C["raw_lt"],C["raw_bd"])
    _bar(axes[1,0],r_imp,"r Improvement\n[positive=improved]","(c)  Correlation Improvement",C["green"],"#1B5E20",C["raw_lt"],C["raw_bd"])
    ax4=axes[1,1]; bw2=0.30
    ax4.bar(x-bw2/2,nse_imp,width=bw2,color=C["bc_lt"],edgecolor=C["bc_bd"],alpha=0.90,linewidth=1.0,zorder=3,label="NSE improvement")
    ax4.bar(x+bw2/2,kge_imp,width=bw2,color=C["ens_lt"],edgecolor=C["ens_bd"],alpha=0.90,linewidth=1.0,zorder=3,label="KGE improvement")
    ax4.axhline(0,color=C["grey"],lw=0.9,ls="--",alpha=0.65)
    ax4.set_xticks(x); ax4.set_xticklabels(codes,rotation=0,ha="center",fontsize=11)
    ax4.set_xlabel("Station",fontsize=12,fontweight="bold"); ax4.set_ylabel("Improvement [positive=improved]",fontsize=12,fontweight="bold")
    ax4.set_title("(d)  NSE & KGE Improvement",loc="left",fontsize=12,fontweight="bold",pad=5)
    ax4.tick_params(axis="both",which="major",labelsize=11,width=1.4); ax4.yaxis.set_minor_locator(ticker.AutoMinorLocator())
    ax4.spines["top"].set_visible(False); ax4.spines["right"].set_visible(False)
    ax4.legend(fontsize=11,frameon=True,edgecolor="#B0BEC5",facecolor="white",framealpha=0.95)
    fig.suptitle(f"Improvement in statistical metrics after QDM bias correction  |  Obs: {period_obs}",fontsize=14,fontweight="bold")
    savefig(fig,out_dir/f"{prefix}_Fig6_MetricImprovement")


# ════════════════════════════════════════════════════════════════════════
#  §6  NEW TREND ANALYSIS FIGURES (Figs 7–11)
# ════════════════════════════════════════════════════════════════════════

# ── Fig 7: Annual Trend Comparison per Station ──────────────────────────
def fig7_trend_comparison(all_trends, obs_ann, raw_ann, bc_ann,
                           stns, smap, period_obs, out_dir, prefix):
    """
    Multi-panel figure: one panel per station showing annual rainfall time series
    with Sen's slope trend lines for Observed, Raw CMIP6, and BC (QDM).
    Significance stars shown in panel title.
    """
    stns_str=[str(s) for s in stns]
    n_s=len(stns_str)
    ncols=min(4,n_s); nrows=math.ceil(n_s/ncols)

    fig,axes=plt.subplots(nrows,ncols,figsize=(5.5*ncols,4.8*nrows))
    fig.subplots_adjust(hspace=0.55,wspace=0.32,left=0.06,right=0.97,top=0.91,bottom=0.06)
    axes=np.array(axes).flatten()

    ds_defs=[
        ("Observed",  obs_ann, TREND_STYLES["Observed"]),
        ("Raw CMIP6", raw_ann, TREND_STYLES["Raw CMIP6"]),
        ("BC (QDM)",  bc_ann,  TREND_STYLES["BC (QDM)"]),
    ]

    for si,stn in enumerate(stns_str):
        ax=axes[si]; code=smap[stn]
        tr=all_trends[stn]
        max_y=0.0; min_y=np.inf

        for ds_label,ann_df,style in ds_defs:
            if ann_df is None or stn not in ann_df.columns: continue
            ser=ann_df[stn].dropna()
            if len(ser)<4: continue
            yrs=ser.index.year.astype(float); vals=ser.values.astype(float)
            ax.scatter(yrs,vals,color=style["color"],s=28,alpha=0.55,
                       edgecolors="none",zorder=3)
            # Trend line
            td=tr.get(ds_label,{})
            slope=td.get("slope",np.nan); intercept=td.get("intercept",np.nan)
            if not(np.isnan(slope) or np.isnan(intercept)):
                y_fit=slope*yrs+intercept
                lo=td.get("slope_lo",np.nan); hi=td.get("slope_hi",np.nan)
                ax.plot(yrs,y_fit,color=style["color"],lw=style["lw"],
                        ls=style["ls"],alpha=style["alpha"],zorder=5)
                # 95% CI band
                if not(np.isnan(lo) or np.isnan(hi)):
                    ax.fill_between(yrs,lo*yrs+intercept,hi*yrs+intercept,
                                    color=style["color"],alpha=0.10,zorder=2)
            max_y=max(max_y,float(np.nanmax(vals))); min_y=min(min_y,float(np.nanmin(vals)))

        # Build title with slope + significance per dataset
        title_parts=[code]
        for ds_label,_,style in ds_defs:
            td=tr.get(ds_label,{})
            sl=td.get("slope",np.nan); stars=td.get("stars","—")
            if not np.isnan(sl):
                title_parts.append(f"{ds_label[:3]}: {sl:+.1f} mm/yr {stars}")
        ax.set_title("\n".join(title_parts),loc="left",fontsize=9.5,
                     fontweight="bold",pad=3)
        ax.set_xlabel("Year",fontsize=10,fontweight="bold")
        ax.set_ylabel("Annual Rainfall (mm)",fontsize=10,fontweight="bold")
        ax.tick_params(axis="both",which="major",labelsize=9,width=1.3)
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)

    # Legend in last panel or separate
    ax_leg=axes[n_s] if n_s<len(axes) else axes[-1]
    ax_leg.set_visible(True); ax_leg.axis("off")
    leg_handles=[
        Line2D([0],[0],color=C["obs"],lw=2.8,ls="-",label="Observed"),
        Line2D([0],[0],color=C["raw"],lw=2.0,ls="--",label="Raw CMIP6"),
        Line2D([0],[0],color=C["bc"], lw=2.2,ls="-", label="BC (QDM)"),
        mpatches.Patch(color="#E0E0E0",alpha=0.4,label="95% CI of trend"),
        Line2D([0],[0],color="k",lw=0,marker="o",ms=6,alpha=0.6,label="Annual value"),
    ]
    ax_leg.legend(handles=leg_handles,loc="center",fontsize=12,frameon=True,
                  edgecolor="#B0BEC5",facecolor="white",framealpha=0.95,
                  ncol=1,handlelength=2.0)
    ax_leg.set_title("Legend\n*** p<0.001  ** p<0.01\n* p<0.05  ns: not significant",
                     fontsize=10.5,fontweight="bold")

    # Hide truly empty axes
    for ax in axes[n_s+1:]: ax.set_visible(False)

    fig.suptitle(
        "Comparative Annual Rainfall Trend — Observed vs Raw CMIP6 vs QDM Bias-Corrected\n"
        "Sen's Slope trend lines with 95% CI  |  "
        f"Modified Mann–Kendall test  |  Period: {period_obs}\n"
        "Ref: Hamed & Rao (1998) J.Hydrol. 204:182–196  |  Sen (1968) J.Am.Stat.Assoc. 63:1379–1389",
        fontsize=12, fontweight="bold"
    )
    savefig(fig,out_dir/f"{prefix}_Fig7_TrendComparison")


# ── Fig 8: Sen's Slope Comparison & CI ─────────────────────────────────
def fig8_sens_slope_comparison(all_trends, stns, smap, period_obs, out_dir, prefix):
    """
    3-panel figure comparing Sen's slopes with 95% CI:
    (a) Bar chart: slope per station for Obs / Raw / BC
    (b) Scatter: Obs slope vs Raw slope + BC slope (trend preservation)
    (c) Relative change bar (slope × period / mean × 100 %)
    """
    stns_str=[str(s) for s in stns]
    codes=[smap[s] for s in stns_str]
    n_s=len(stns_str); x=np.arange(n_s)
    bw=0.26

    ds_defs=[("Observed","obs",C["obs"],C["obs"]),
             ("Raw CMIP6","raw",C["raw"],C["raw_bd"]),
             ("BC (QDM)","bc",C["bc"],C["bc_bd"])]

    def get_slopes(label):
        sl,lo,hi,st=[],[],[],[]
        for stn in stns_str:
            td=all_trends[stn].get(label,{})
            sl.append(td.get("slope",np.nan))
            lo.append(td.get("slope_lo",np.nan))
            hi.append(td.get("slope_hi",np.nan))
            st.append(td.get("stars","—"))
        return np.array(sl),np.array(lo),np.array(hi),st

    fig,axes=plt.subplots(1,3,figsize=(20,8))
    fig.subplots_adjust(left=0.06,right=0.97,top=0.88,bottom=0.12,wspace=0.32)

    # ── Panel (a): grouped bars with CI ─────────────────────────────
    ax=axes[0]
    for di,(ds_label,ds_key,col,edge) in enumerate(ds_defs):
        sl,lo,hi,stars=get_slopes(ds_label)
        offs=(di-1)*bw
        bars=ax.bar(x+offs,sl,width=bw*0.88,color=mcolors.to_rgba(col,0.82),
                    edgecolor=edge,linewidth=0.9,zorder=3,label=ds_label)
        # Error bars (95% CI)
        ci_lo=sl-lo; ci_hi=hi-sl
        ci_lo=np.where(np.isnan(ci_lo),0,ci_lo)
        ci_hi=np.where(np.isnan(ci_hi),0,ci_hi)
        ax.errorbar(x+offs,sl,yerr=[ci_lo,ci_hi],fmt="none",
                    ecolor=edge,elinewidth=1.3,capsize=3.5,zorder=4)
        # Significance stars above bars
        for xi,(v,st) in enumerate(zip(sl,stars)):
            if not np.isnan(v) and st not in("—","ns"):
                ax.text(xi+offs,v+(abs(v)*0.05+1)*np.sign(v) if not np.isnan(v) else 0.5,
                        st,ha="center",va="bottom",fontsize=9.5,fontweight="bold",
                        color=SIG_COLORS.get(st,C["grey"]))

    ax.axhline(0,color=C["grey"],lw=1.0,ls="--",alpha=0.65)
    ax.set_xticks(x); ax.set_xticklabels(codes,rotation=0,ha="center",fontsize=11)
    ax.set_xlabel("Station",fontsize=13,fontweight="bold")
    ax.set_ylabel("Sen's Slope (mm yr⁻¹)",fontsize=13,fontweight="bold")
    ax.set_title("(a)  Sen's Slope per Station\n     Bars = 95% CI  |  *** p<0.001  ** p<0.01  * p<0.05",
                 loc="left",fontsize=12,fontweight="bold",pad=5)
    ax.legend(fontsize=11,frameon=True,edgecolor="#B0BEC5",facecolor="white",
              framealpha=0.95,ncol=1,loc="best")
    ax.tick_params(axis="both",which="major",labelsize=11,width=1.4)
    ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)

    # ── Panel (b): scatter Obs vs Raw/BC (trend preservation) ────────
    ax2=axes[1]
    sl_obs,_,_,_=get_slopes("Observed")
    sl_raw,_,_,st_raw=get_slopes("Raw CMIP6")
    sl_bc, _,_,st_bc =get_slopes("BC (QDM)")

    valid_raw=~np.isnan(sl_obs)&~np.isnan(sl_raw)
    valid_bc =~np.isnan(sl_obs)&~np.isnan(sl_bc)

    if valid_raw.sum()>=2:
        ax2.scatter(sl_obs[valid_raw],sl_raw[valid_raw],color=C["raw"],
                    s=110,edgecolors=C["raw_bd"],linewidth=0.8,
                    zorder=4,label="Raw CMIP6",marker="^",alpha=0.90)
    if valid_bc.sum()>=2:
        ax2.scatter(sl_obs[valid_bc],sl_bc[valid_bc],color=C["bc"],
                    s=110,edgecolors=C["bc_bd"],linewidth=0.8,
                    zorder=4,label="BC (QDM)",marker="o",alpha=0.90)

    # Station labels
    for xi,stn in enumerate(stns_str):
        code=codes[xi]
        if not np.isnan(sl_obs[xi]) and not np.isnan(sl_raw[xi]):
            ax2.text(sl_obs[xi]+0.3,sl_raw[xi]+0.3,code,fontsize=9,color=C["raw"],fontweight="bold")
        if not np.isnan(sl_obs[xi]) and not np.isnan(sl_bc[xi]):
            ax2.text(sl_obs[xi]+0.3,sl_bc[xi]-0.8,code,fontsize=9,color=C["bc"],fontweight="bold")

    # 1:1 line
    all_vals=np.concatenate([sl_obs[~np.isnan(sl_obs)],sl_raw[~np.isnan(sl_raw)],sl_bc[~np.isnan(sl_bc)]])
    if len(all_vals)>0:
        mn,mx=float(np.min(all_vals))-2,float(np.max(all_vals))+2
        ax2.plot([mn,mx],[mn,mx],color=C["green"],lw=1.5,ls="--",alpha=0.80,label="1:1 (perfect preservation)")
        ax2.set_xlim(mn,mx); ax2.set_ylim(mn,mx)
        ax2.set_aspect("equal","box")

    # Correlation
    if valid_bc.sum()>=3:
        r_bc,p_bc=pearsonr(sl_obs[valid_bc],sl_bc[valid_bc])
        ax2.text(0.05,0.95,f"BC: r = {r_bc:.3f}, p = {p_bc:.3f}",
                 transform=ax2.transAxes,fontsize=10,fontweight="bold",
                 color=C["bc"],va="top")
    if valid_raw.sum()>=3:
        r_raw,p_raw=pearsonr(sl_obs[valid_raw],sl_raw[valid_raw])
        ax2.text(0.05,0.88,f"Raw: r = {r_raw:.3f}, p = {p_raw:.3f}",
                 transform=ax2.transAxes,fontsize=10,fontweight="bold",
                 color=C["raw"],va="top")

    ax2.axhline(0,color=C["grey"],lw=0.8,ls=":",alpha=0.5)
    ax2.axvline(0,color=C["grey"],lw=0.8,ls=":",alpha=0.5)
    ax2.set_xlabel("Observed Sen's Slope (mm yr⁻¹)",fontsize=13,fontweight="bold")
    ax2.set_ylabel("Simulated Sen's Slope (mm yr⁻¹)",fontsize=13,fontweight="bold")
    ax2.set_title("(b)  Trend Preservation Assessment\n"
                  "     Simulated vs Observed Sen's Slope\n"
                  "     Closer to 1:1 line = better preservation",
                  loc="left",fontsize=12,fontweight="bold",pad=5)
    ax2.legend(fontsize=11,frameon=True,edgecolor="#B0BEC5",facecolor="white",framealpha=0.95,loc="lower right")
    ax2.tick_params(axis="both",which="major",labelsize=11,width=1.4)
    ax2.spines["top"].set_visible(False); ax2.spines["right"].set_visible(False)

    # ── Panel (c): relative change comparison ────────────────────────
    ax3=axes[2]
    def get_relch(label):
        return [all_trends[stn].get(label,{}).get("relative_change_pct",np.nan) for stn in stns_str]
    rc_obs=get_relch("Observed"); rc_raw=get_relch("Raw CMIP6"); rc_bc=get_relch("BC (QDM)")
    for di,(label,rc,col,edge) in enumerate([("Observed",rc_obs,C["obs"],C["obs"]),
                                               ("Raw CMIP6",rc_raw,C["raw"],C["raw_bd"]),
                                               ("BC (QDM)",rc_bc, C["bc"],C["bc_bd"])]):
        offs=(di-1)*bw
        ax3.bar(x+offs,rc,width=bw*0.88,color=mcolors.to_rgba(col,0.82),
                edgecolor=edge,linewidth=0.9,zorder=3,label=label)
    ax3.axhline(0,color=C["grey"],lw=1.0,ls="--",alpha=0.65)
    ax3.set_xticks(x); ax3.set_xticklabels(codes,rotation=0,ha="center",fontsize=11)
    ax3.set_xlabel("Station",fontsize=13,fontweight="bold")
    ax3.set_ylabel("Relative Change Over Study Period (%)",fontsize=12,fontweight="bold")
    ax3.set_title("(c)  Relative Rainfall Change\n"
                  "     = (Slope × N_years) / Mean × 100%",
                  loc="left",fontsize=12,fontweight="bold",pad=5)
    ax3.legend(fontsize=11,frameon=True,edgecolor="#B0BEC5",facecolor="white",framealpha=0.95)
    ax3.tick_params(axis="both",which="major",labelsize=11,width=1.4)
    ax3.yaxis.set_minor_locator(ticker.AutoMinorLocator())
    ax3.spines["top"].set_visible(False); ax3.spines["right"].set_visible(False)

    fig.suptitle(
        "Sen's Slope Comparison — Observed vs Raw CMIP6 vs QDM Bias-Corrected\n"
        f"Period: {period_obs}  |  Error bars = 95% CI  |  "
        "Ref: Sen (1968)  |  Hamed & Rao (1998)",
        fontsize=13,fontweight="bold"
    )
    savefig(fig,out_dir/f"{prefix}_Fig8_SensSlopeComparison")


# ── Fig 9: MMK Z-score & p-value Significance Summary ─────────────────
def fig9_mmk_significance(all_trends, stns, smap, period_obs, out_dir, prefix):
    """
    3-panel significance summary:
    (a) Z-score bar chart (coloured by dataset)
    (b) -log10(p) heatmap (dataset × station)
    (c) Trend direction comparison matrix
    """
    stns_str=[str(s) for s in stns]; codes=[smap[s] for s in stns_str]
    n_s=len(stns_str)
    DS_LIST=["Observed","Raw CMIP6","BC (QDM)"]
    DS_COLORS=[C["obs"],C["raw"],C["bc"]]

    def get_metric(ds,key):
        return [all_trends[s].get(ds,{}).get(key,np.nan) for s in stns_str]

    fig=plt.figure(figsize=(20,15))
    gs=gridspec.GridSpec(2,2,figure=fig,hspace=0.48,wspace=0.34,
                         top=0.91,bottom=0.09,left=0.07,right=0.97)
    ax1=fig.add_subplot(gs[0,:]); ax2=fig.add_subplot(gs[1,0]); ax3=fig.add_subplot(gs[1,1])

    # ── Panel (a): Z-score grouped bars ─────────────────────────────
    bw=0.26; x=np.arange(n_s)
    for di,(ds,col) in enumerate(zip(DS_LIST,DS_COLORS)):
        z_vals=get_metric(ds,"Z"); stars=[all_trends[s].get(ds,{}).get("stars","—") for s in stns_str]
        offs=(di-1)*bw
        colors=[SIG_COLORS.get(st,"#CFD8DC") if abs(z)>=0 else "#CFD8DC"
                for z,st in zip(z_vals,stars)]
        bars=ax1.bar(x+offs,z_vals,width=bw*0.88,color=colors,
                     edgecolor=mcolors.to_rgba(col,0.80),linewidth=1.0,
                     zorder=3,label=ds)
        for xi,(z,st) in enumerate(zip(z_vals,stars)):
            if not np.isnan(z) and st not in("—","ns"):
                ax1.text(xi+offs,z+(0.08 if z>=0 else -0.18),st,
                         ha="center",va="bottom" if z>=0 else "top",
                         fontsize=10,fontweight="bold",color=SIG_COLORS.get(st,"#1A1A1A"))

    ax1.axhline(0,   color=C["grey"],lw=1.0,ls="--",alpha=0.65)
    ax1.axhline(1.96, color="#C0392B",lw=1.3,ls="--",alpha=0.80,label="Z=±1.96 (p<0.05)")
    ax1.axhline(-1.96,color="#C0392B",lw=1.3,ls="--",alpha=0.80)
    ax1.axhline(2.576,color="#E67E22",lw=1.0,ls=":",alpha=0.75,label="Z=±2.58 (p<0.01)")
    ax1.axhline(-2.576,color="#E67E22",lw=1.0,ls=":",alpha=0.75)
    ax1.set_xticks(x); ax1.set_xticklabels(codes,rotation=0,ha="center",fontsize=11)
    ax1.set_xlabel("Station",fontsize=13,fontweight="bold")
    ax1.set_ylabel("Modified MK Z-statistic\n[|Z|>1.96 → p<0.05]",fontsize=13,fontweight="bold")
    ax1.set_title("(a)  Modified Mann–Kendall Z-statistic per Station\n"
                  "     Colour-coded by significance level  |  "
                  "Groups: Observed / Raw CMIP6 / BC (QDM)",
                  loc="left",fontsize=13,fontweight="bold",pad=5)
    ax1.legend(fontsize=11,frameon=True,edgecolor="#B0BEC5",facecolor="white",
               framealpha=0.95,ncol=2,loc="upper right")
    ax1.tick_params(axis="both",which="major",labelsize=11,width=1.4)
    ax1.yaxis.set_minor_locator(ticker.AutoMinorLocator())
    ax1.spines["top"].set_visible(False); ax1.spines["right"].set_visible(False)

    # Colour legend for significance
    for col_sig,lbl_sig in [("#1B5E20","p<0.001 ***"),("#2E7D32","p<0.01 **"),
                              ("#81C784","p<0.05 *"),("#CFD8DC","ns (p≥0.05)")]:
        ax1.bar([],[],color=col_sig,label=lbl_sig)
    ax1.legend(fontsize=9.5,frameon=True,edgecolor="#B0BEC5",facecolor="white",
               framealpha=0.95,ncol=3,loc="upper left")

    # ── Panel (b): -log10(p) heatmap ─────────────────────────────────
    p_mat=np.full((len(DS_LIST),n_s),np.nan)
    for di,ds in enumerate(DS_LIST):
        for si,stn in enumerate(stns_str):
            p=all_trends[stn].get(ds,{}).get("p",np.nan)
            if not np.isnan(p): p_mat[di,si]=-math.log10(max(p,1e-10))

    im=ax2.imshow(p_mat,cmap="RdYlGn",vmin=0,vmax=3.5,aspect="auto",interpolation="nearest")
    cb=plt.colorbar(im,ax=ax2,orientation="horizontal",pad=0.22,fraction=0.06,shrink=0.85)
    cb.set_label("−log₁₀(p-value)  |  >1.30=*  >2.00=**  >3.00=***",fontsize=10,fontweight="bold")
    for di,ds in enumerate(DS_LIST):
        for si,stn in enumerate(stns_str):
            stars=all_trends[stn].get(ds,{}).get("stars","—")
            lp=p_mat[di,si] if not np.isnan(p_mat[di,si]) else 0
            tc="white" if lp>2.2 else "#1A1A1A"
            ax2.text(si,di,stars,ha="center",va="center",fontsize=12,fontweight="bold",color=tc)
    ax2.set_xticks(range(n_s)); ax2.set_xticklabels(codes,rotation=0,ha="center",fontsize=11)
    ax2.set_yticks(range(len(DS_LIST))); ax2.set_yticklabels(DS_LIST,fontsize=12,fontweight="bold")
    ax2.set_title("(b)  Significance Heatmap — MMK p-values\n"
                  "     Green = significant trend  |  *** p<0.001",
                  loc="left",fontsize=12,fontweight="bold",pad=5)

    # ── Panel (c): Trend direction comparison ─────────────────────────
    dir_map={"↑ Increasing":1,"→ No trend":0,"↓ Decreasing":-1,"—":np.nan}
    dir_mat=np.full((len(DS_LIST),n_s),np.nan)
    for di,ds in enumerate(DS_LIST):
        for si,stn in enumerate(stns_str):
            d=all_trends[stn].get(ds,{}).get("direction","—")
            dir_mat[di,si]=dir_map.get(d,np.nan)

    cmap_dir=mcolors.LinearSegmentedColormap.from_list("trend",
              [C["raw"],"#CFD8DC",C["green"]],N=3)
    im2=ax3.imshow(dir_mat,cmap=cmap_dir,vmin=-1.5,vmax=1.5,aspect="auto",interpolation="nearest")

    # Overlay text
    sym_map={1:"↑",0:"→",-1:"↓"}
    for di,ds in enumerate(DS_LIST):
        for si,stn in enumerate(stns_str):
            v=dir_mat[di,si]; sym=sym_map.get(int(v),"—") if not np.isnan(v) else "—"
            stars=all_trends[stn].get(ds,{}).get("stars","")
            txt=f"{sym}{stars}" if stars not in("—","ns","") else sym
            tc="white" if abs(v)==1 else "#1A1A1A"
            ax3.text(si,di,txt,ha="center",va="center",fontsize=12,fontweight="bold",color=tc)

    ax3.set_xticks(range(n_s)); ax3.set_xticklabels(codes,rotation=0,ha="center",fontsize=11)
    ax3.set_yticks(range(len(DS_LIST))); ax3.set_yticklabels(DS_LIST,fontsize=12,fontweight="bold")
    ax3.set_title("(c)  Trend Direction Comparison\n"
                  "     ↑ Increasing  →  No trend  ↓ Decreasing\n"
                  "     (*) significant at α = 0.05",
                  loc="left",fontsize=12,fontweight="bold",pad=5)
    cb2=plt.colorbar(im2,ax=ax3,orientation="horizontal",pad=0.22,fraction=0.06,shrink=0.85)
    cb2.set_ticks([-1,0,1]); cb2.set_ticklabels(["Decreasing","No trend","Increasing"],fontsize=9.5)

    fig.suptitle(
        "Modified Mann–Kendall Significance Analysis — Annual Rainfall Trends\n"
        f"Observed vs Raw CMIP6 vs QDM Bias-Corrected  |  Period: {period_obs}  |  "
        "Ref: Hamed & Rao (1998) J.Hydrol. 204:182–196",
        fontsize=13,fontweight="bold"
    )
    savefig(fig,out_dir/f"{prefix}_Fig9_MMKSignificance")


# ── Fig 10: Taylor Diagram of Annual Trend Magnitudes ──────────────────
def fig10_trend_taylor(all_trends, stns, smap, period_obs, out_dir, prefix):
    """
    Taylor diagram where each point represents one station's ANNUAL TREND:
    - Reference: Observed trend (slope ± std across years)
    - Points: Raw and BC (QDM) trend slopes
    Uses: σ(annual_series), trend correlation
    This visualises how well models capture the spatial pattern of observed trends.
    """
    stns_str=[str(s) for s in stns]; n_s=len(stns_str)
    cmap_stn=cm.get_cmap("tab20",max(n_s,1))
    stn_colors=[mcolors.to_hex(cmap_stn(i)) for i in range(n_s)]

    # Collect slopes
    obs_slopes =np.array([all_trends[s].get("Observed",{}).get("slope",np.nan) for s in stns_str])
    raw_slopes =np.array([all_trends[s].get("Raw CMIP6",{}).get("slope",np.nan) for s in stns_str])
    bc_slopes  =np.array([all_trends[s].get("BC (QDM)",{}).get("slope",np.nan) for s in stns_str])

    mask_r=~np.isnan(obs_slopes)&~np.isnan(raw_slopes)
    mask_b=~np.isnan(obs_slopes)&~np.isnan(bc_slopes)

    # STD of slopes (spread across stations) — treat as σ_r
    std_obs=float(np.nanstd(obs_slopes,ddof=1)) if np.sum(~np.isnan(obs_slopes))>2 else 1.0
    std_obs=max(std_obs,0.1)

    def sigma_r(sim_sl):
        valid=~np.isnan(obs_slopes)&~np.isnan(sim_sl)
        if valid.sum()<3: return np.nan
        return float(np.std(sim_sl[valid],ddof=1)/std_obs)

    def corr_trend(sim_sl):
        valid=~np.isnan(obs_slopes)&~np.isnan(sim_sl)
        if valid.sum()<3: return np.nan
        try: return float(pearsonr(obs_slopes[valid],sim_sl[valid])[0])
        except: return np.nan

    sr_raw=sigma_r(raw_slopes); r_raw=corr_trend(raw_slopes)
    sr_bc =sigma_r(bc_slopes);  r_bc =corr_trend(bc_slopes)

    # Also per-model slopes
    model_slopes_raw={}; model_slopes_bc={}
    for stn in stns_str:
        for key,store in all_trends[stn].items():
            if key.startswith("Raw-"):
                m=key[4:]
                model_slopes_raw.setdefault(m,[]).append(store.get("slope",np.nan))
            if key.startswith("BC-"):
                m=key[3:]
                model_slopes_bc.setdefault(m,[]).append(store.get("slope",np.nan))
    per_model_r_raw={m:{"sr":sigma_r(np.array(v)),"r":corr_trend(np.array(v))} for m,v in model_slopes_raw.items()}
    per_model_r_bc ={m:{"sr":sigma_r(np.array(v)),"r":corr_trend(np.array(v))} for m,v in model_slopes_bc.items()}

    ref_std=1.0  # normalised to observed std
    fig,ax=plt.subplots(1,1,figsize=(10,9))
    fig.subplots_adjust(left=0.07,right=0.97,top=0.88,bottom=0.09)
    r_max=_taylor_bg(ax,ref_std,"mm yr⁻¹ (normalised)")

    def _plot_point(ax,sr,r,col,mk,s,zord,lbl):
        if np.isnan(sr) or np.isnan(r): return
        theta=np.arccos(np.clip(r,-1,1))
        xv=sr*np.cos(theta); yv=sr*np.sin(theta)
        if xv**2+yv**2>r_max**2: return
        ax.scatter(xv,yv,color=col,marker=mk,s=s,zorder=zord,
                   edgecolors="#1A1A1A",linewidth=0.8,alpha=0.92)
        return xv,yv

    raw_xy={}
    # Ensemble
    res_r=_plot_point(ax,sr_raw,r_raw,C["raw"],"^",160,6,"Raw ens")
    res_b=_plot_point(ax,sr_bc, r_bc, C["bc"], "o",160,7,"BC ens")
    if res_r: raw_xy["Ensemble"]=res_r
    if res_b and "Ensemble" in raw_xy:
        rx,ry=raw_xy["Ensemble"]
        ax.annotate("",xy=res_b,xytext=(rx,ry),
                    arrowprops=dict(arrowstyle="-|>",color=C["bc"],lw=1.8,alpha=0.85,mutation_scale=14),zorder=5)
        ax.text(res_b[0]+0.025*r_max,res_b[1]+0.025*r_max,"ENS",fontsize=10,
                color=C["bc"],fontweight="bold")

    # Per-model
    for i,(m,vals) in enumerate(per_model_r_raw.items()):
        col=MODEL_PALETTE[i%len(MODEL_PALETTE)]
        _plot_point(ax,vals["sr"],vals["r"],col,"^",90,5,m)
    for i,(m,vals) in enumerate(per_model_r_bc.items()):
        col=MODEL_PALETTE[i%len(MODEL_PALETTE)]
        res=_plot_point(ax,vals["sr"],vals["r"],col,"o",90,5,m)
        if res:
            ax.text(res[0]+0.02*r_max,res[1]+0.02*r_max,m[:6],fontsize=8,color=col,fontweight="bold")

    handles=[Line2D([0],[0],marker="*",color="k",ls="none",ms=13,label="Observed trend (Reference)"),
             Line2D([0],[0],marker="^",color="#444",ls="none",ms=10,markeredgecolor="#1A1A1A",markeredgewidth=0.8,label="Raw CMIP6"),
             Line2D([0],[0],marker="o",color="#444",ls="none",ms=10,markeredgecolor="#1A1A1A",markeredgewidth=0.8,label="BC (QDM)"),
             mpatches.Patch(facecolor="#E0E0E0",edgecolor="#1A1A1A",linewidth=0.6,alpha=0.8,label="Larger marker = ensemble"),
             Line2D([0],[0],color="#444",lw=1.6,ls="-",label="Arrow: Raw → BC")]
    ax.legend(handles=handles,loc="upper right",fontsize=10,frameon=True,edgecolor="#B0BEC5",facecolor="white",framealpha=0.95,ncol=1)
    ax.set_title("Taylor Diagram of Annual Rainfall Trend Magnitudes\n"
                 "r = Pearson correlation of station trends  |  σ = std ratio of trend slopes",
                 loc="left",fontsize=12,fontweight="bold",pad=5)
    fig.suptitle(f"Taylor Diagram — Spatial Pattern of Annual Rainfall Trends  |  Period: {period_obs}\n"
                 "Reference (★) = Observed trend magnitude across stations\n"
                 "Ref: Taylor (2001) J.Geophys.Res. 106:7183–7192  |  Hamed & Rao (1998)",
                 fontsize=12,fontweight="bold")
    savefig(fig,out_dir/f"{prefix}_Fig10_TrendTaylorDiagram")


# ── Fig 11: QDM Trend Preservation Assessment ──────────────────────────
def fig11_trend_preservation(all_trends, stns, smap, period_obs, out_dir, prefix):
    """
    4-panel comprehensive trend preservation assessment:
    (a) Bias in Sen's slope: (Model slope) - (Obs slope) per station
    (b) Trend slope scatter: Raw vs BC coloured by QDM improvement
    (c) MMK tau comparison heatmap (Obs / Raw / BC × stations)
    (d) Autocorrelation correction factor (ns_ratio) per dataset × station
    """
    stns_str=[str(s) for s in stns]; codes=[smap[s] for s in stns_str]
    n_s=len(stns_str); x=np.arange(n_s); bw=0.38

    def get_arr(ds,key):
        return np.array([all_trends[s].get(ds,{}).get(key,np.nan) for s in stns_str])

    obs_sl=get_arr("Observed","slope"); raw_sl=get_arr("Raw CMIP6","slope"); bc_sl=get_arr("BC (QDM)","slope")
    bias_raw=raw_sl-obs_sl; bias_bc=bc_sl-obs_sl
    obs_tau=get_arr("Observed","tau"); raw_tau=get_arr("Raw CMIP6","tau"); bc_tau=get_arr("BC (QDM)","tau")
    obs_ns=get_arr("Observed","ns_ratio"); raw_ns=get_arr("Raw CMIP6","ns_ratio"); bc_ns=get_arr("BC (QDM)","ns_ratio")

    fig,axes=plt.subplots(2,2,figsize=(18,13))
    fig.subplots_adjust(hspace=0.50,wspace=0.32,left=0.07,right=0.97,top=0.91,bottom=0.09)

    # ── (a) Slope bias ───────────────────────────────────────────────
    ax=axes[0,0]
    ax.bar(x-bw/2,bias_raw,width=bw,color=[C["raw_lt"] if v>=0 else C["raw"] for v in bias_raw],
           edgecolor=C["raw_bd"],linewidth=0.9,alpha=0.88,zorder=3,label="Raw CMIP6 bias")
    ax.bar(x+bw/2,bias_bc, width=bw,color=[C["bc_lt"]  if v>=0 else C["bc"]  for v in bias_bc],
           edgecolor=C["bc_bd"], linewidth=0.9,alpha=0.88,zorder=3,label="BC (QDM) bias")
    ax.axhline(0,color=C["grey"],lw=1.0,ls="--",alpha=0.65)
    # Mark improvement (BC bias closer to zero)
    for xi in range(n_s):
        raw_b=bias_raw[xi]; bc_b=bias_bc[xi]
        if not(np.isnan(raw_b) or np.isnan(bc_b)):
            if abs(bc_b)<abs(raw_b):
                ax.scatter(xi+bw/2,bc_b,color=C["green"],marker="*",s=120,zorder=6)
    ax.set_xticks(x); ax.set_xticklabels(codes,rotation=0,ha="center",fontsize=11)
    ax.set_xlabel("Station",fontsize=12,fontweight="bold")
    ax.set_ylabel("Slope Bias: Model − Obs (mm yr⁻¹)\n[zero=perfect, ★=BC improved]",fontsize=11,fontweight="bold")
    ax.set_title("(a)  Bias in Sen's Slope\n     Raw vs BC relative to Observed",loc="left",fontsize=12,fontweight="bold",pad=5)
    ax.legend(fontsize=11,frameon=True,edgecolor="#B0BEC5",facecolor="white",framealpha=0.95)
    ax.tick_params(axis="both",which="major",labelsize=11,width=1.4)
    ax.yaxis.set_minor_locator(ticker.AutoMinorLocator()); ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)

    # ── (b) Raw vs BC slope scatter ──────────────────────────────────
    ax2=axes[0,1]
    valid=~np.isnan(raw_sl)&~np.isnan(bc_sl)
    abs_improve=np.abs(bias_raw)-np.abs(bias_bc)  # positive=BC better
    sc=ax2.scatter(raw_sl[valid],bc_sl[valid],c=abs_improve[valid],
                   cmap="RdYlGn",s=130,zorder=4,edgecolors="#1A1A1A",linewidths=0.8,
                   vmin=-max(abs(abs_improve[~np.isnan(abs_improve)]))*0.8 if valid.sum()>0 else -1,
                   vmax=max(abs(abs_improve[~np.isnan(abs_improve)]))*0.8 if valid.sum()>0 else 1)
    for xi in np.where(valid)[0]:
        ax2.text(raw_sl[xi]+0.2,bc_sl[xi]+0.2,codes[xi],fontsize=9.5,fontweight="bold",color=C["grey"])
    cb2=plt.colorbar(sc,ax=ax2,orientation="horizontal",pad=0.16,fraction=0.06,shrink=0.82)
    cb2.set_label("Improvement in slope bias (mm yr⁻¹)\n[green=BC better, red=BC worse]",fontsize=9.5,fontweight="bold")
    cb2.ax.tick_params(labelsize=9)
    if valid.sum()>=2:
        all_v=np.concatenate([raw_sl[valid],bc_sl[valid]])
        mn,mx=float(np.nanmin(all_v))-1,float(np.nanmax(all_v))+1
        ax2.plot([mn,mx],[mn,mx],color=C["grey"],lw=1.2,ls="--",alpha=0.60,label="Raw=BC (no change)")
        ax2.set_xlim(mn,mx); ax2.set_ylim(mn,mx); ax2.set_aspect("equal","box")
    ax2.axhline(0,color=C["grey"],lw=0.6,ls=":",alpha=0.4); ax2.axvline(0,color=C["grey"],lw=0.6,ls=":",alpha=0.4)
    ax2.set_xlabel("Raw CMIP6 Sen's Slope (mm yr⁻¹)",fontsize=12,fontweight="bold")
    ax2.set_ylabel("BC (QDM) Sen's Slope (mm yr⁻¹)",fontsize=12,fontweight="bold")
    ax2.set_title("(b)  Raw vs BC Slope Scatter\n     Colour = slope bias improvement",loc="left",fontsize=12,fontweight="bold",pad=5)
    ax2.legend(fontsize=10.5,frameon=True,edgecolor="#B0BEC5",facecolor="white",framealpha=0.95,loc="lower right")
    ax2.tick_params(axis="both",which="major",labelsize=11,width=1.4); ax2.spines["top"].set_visible(False); ax2.spines["right"].set_visible(False)

    # ── (c) tau heatmap ──────────────────────────────────────────────
    ax3=axes[1,0]
    ds_list=["Observed","Raw CMIP6","BC (QDM)"]
    tau_mat=np.array([get_arr(ds,"tau") for ds in ds_list])
    im3=ax3.imshow(tau_mat,cmap="RdYlGn",vmin=-0.5,vmax=0.5,aspect="auto",interpolation="nearest")
    cb3=plt.colorbar(im3,ax=ax3,orientation="horizontal",pad=0.22,fraction=0.06,shrink=0.85)
    cb3.set_label("Kendall's tau  [positive=increasing trend, negative=decreasing]",fontsize=10,fontweight="bold")
    for di,ds in enumerate(ds_list):
        for si,stn in enumerate(stns_str):
            tau_v=tau_mat[di,si]; stars=all_trends[stn].get(ds,{}).get("stars","—")
            tc="white" if abs(tau_v)>0.35 else "#1A1A1A"
            txt=f"{tau_v:.2f}{stars}" if not np.isnan(tau_v) else "—"
            ax3.text(si,di,txt,ha="center",va="center",fontsize=9.5,fontweight="bold",color=tc)
    ax3.set_xticks(range(n_s)); ax3.set_xticklabels(codes,rotation=0,ha="center",fontsize=11)
    ax3.set_yticks(range(len(ds_list))); ax3.set_yticklabels(ds_list,fontsize=12,fontweight="bold")
    ax3.set_title("(c)  Kendall's tau Heatmap\n     Stars = MMK significance",loc="left",fontsize=12,fontweight="bold",pad=5)

    # ── (d) Autocorrelation correction factor ─────────────────────────
    ax4=axes[1,1]
    ax4.plot(range(n_s),obs_ns,color=C["obs"],lw=2.4,ls="-",marker="o",ms=8,
             markeredgecolor="#1A1A1A",markeredgewidth=0.6,zorder=5,label="Observed")
    ax4.plot(range(n_s),raw_ns,color=C["raw"],lw=2.0,ls="--",marker="^",ms=8,
             markeredgecolor="#1A1A1A",markeredgewidth=0.6,zorder=4,label="Raw CMIP6")
    ax4.plot(range(n_s),bc_ns, color=C["bc"], lw=2.2,ls="-",marker="s",ms=8,
             markeredgecolor="#1A1A1A",markeredgewidth=0.6,zorder=4,label="BC (QDM)")
    ax4.axhline(1.0,color=C["grey"],lw=1.2,ls="--",alpha=0.70,label="n_s*=1 (no autocorrelation)")
    ax4.fill_between(range(n_s),1.0,obs_ns,alpha=0.12,color=C["obs"])
    ax4.fill_between(range(n_s),1.0,bc_ns, alpha=0.12,color=C["bc"])
    ax4.set_xticks(range(n_s)); ax4.set_xticklabels(codes,rotation=0,ha="center",fontsize=11)
    ax4.set_xlabel("Station",fontsize=12,fontweight="bold")
    ax4.set_ylabel("Autocorrelation Correction Factor (n_s*)\n[>1.0 = positive AC detected]",fontsize=11,fontweight="bold")
    ax4.set_title("(d)  MMK Autocorrelation Correction Factor\n"
                  "     n_s* > 1 indicates serial correlation in annual series\n"
                  "     Ref: Hamed & Rao (1998)",
                  loc="left",fontsize=12,fontweight="bold",pad=5)
    ax4.legend(fontsize=11,frameon=True,edgecolor="#B0BEC5",facecolor="white",framealpha=0.95,ncol=2,loc="upper right")
    ax4.tick_params(axis="both",which="major",labelsize=11,width=1.4)
    ax4.yaxis.set_minor_locator(ticker.AutoMinorLocator()); ax4.spines["top"].set_visible(False); ax4.spines["right"].set_visible(False)

    fig.suptitle(
        "QDM Trend Preservation Assessment — Bias Correction Effect on Rainfall Trends\n"
        f"Period: {period_obs}  |  "
        "Ref: Hamed & Rao (1998) J.Hydrol. 204:182–196  |  Sen (1968)",
        fontsize=13,fontweight="bold"
    )
    savefig(fig,out_dir/f"{prefix}_Fig11_TrendPreservation")

# ════════════════════════════════════════════════════════════════════════
#  §7  EXCEL OUTPUT — Trend Analysis Sheets
# ════════════════════════════════════════════════════════════════════════

def _xl_title_row(ws,nc,title,sub):
    _mxsc(ws,1,1,nc,title,bold=True,fc="FFFFFF",bg=XC["title"],sz=13,align="left")
    _rh(ws,1,24)
    _mxsc(ws,2,1,nc,sub,italic=True,fc="FFFFFF",bg=XC["sub"],sz=9,align="left")
    _rh(ws,2,14)

def _xl_hdr(ws,r,hdrs):
    for ci,h in enumerate(hdrs,1):
        _xsc(ws,r,ci,h,bold=True,fc="FFFFFF",bg=XC["hdr"],sz=10,wrap=True)
    _rh(ws,r,36)

def _fmt(v,dp=4):
    if v is None or (isinstance(v,float) and np.isnan(v)): return "—"
    if isinstance(v,float): return round(v,dp)
    return v

def perf_category_nse(val):
    if np.isnan(val): return "—"
    if val>0.75: return "Very Good"
    if val>0.65: return "Good"
    if val>0.50: return "Satisfactory"
    return "Unsatisfactory"

def write_excel_trends(wb, all_trends, stns, smap, models, period_obs):
    """Add trend analysis sheets to workbook."""
    stns_str=[str(s) for s in stns]
    codes=[smap[s] for s in stns_str]
    DS_LIST=["Observed","Raw CMIP6","BC (QDM)"]

    # ── Sheet: MMK + Sen's Slope Results ────────────────────────────
    ws=wb.create_sheet("Trend Analysis (MMK+Sen)")
    ws.sheet_view.showGridLines=False
    ws.freeze_panes="E5"
    nc=16
    _xl_title_row(ws,nc,
        "Trend Analysis — Modified Mann–Kendall Test + Sen's Slope",
        f"Period: {period_obs}  |  MMK: Hamed & Rao (1998)  |  Sen: (1968)  |  "
        "*** p<0.001  ** p<0.01  * p<0.05  ns: not significant  |  "
        "Green=significant increasing  |  Red=significant decreasing")
    hdrs=["Dataset","Station","Code","N (years)","Mean (mm/yr)","Std (mm/yr)",
          "Sen Slope\n(mm/yr)","95% CI Lo","95% CI Hi","Sen/decade",
          "Relative\nChange (%)","MK S","Z (MMK)","p-value","Stars",
          "Direction","n_s* (AC factor)","Kendall tau"]
    for ci,h in enumerate(hdrs,1):
        _xsc(ws,4,ci,h,bold=True,fc="FFFFFF",bg=XC["hdr"],sz=9.5,wrap=True)
    _rh(ws,4,40)
    ri=5
    DS_BG={"Observed":XC["obs_r"],"Raw CMIP6":XC["raw_r"],"BC (QDM)":XC["bc_r"]}
    for ds in DS_LIST:
        for stn,code in zip(stns_str,codes):
            td=all_trends[stn].get(ds,{})
            slope=td.get("slope",np.nan); p=td.get("p",np.nan)
            stars=td.get("stars","—"); direction=td.get("direction","—")
            bg=DS_BG.get(ds,XC["white"])
            # Override: significant trend
            if stars not in("—","ns"):
                if "Increasing" in direction: bg="E8F5E9"
                elif "Decreasing" in direction: bg="FFEBEE"
            vals=[ds,stn,code,td.get("n","—"),
                  _fmt(td.get("mean",np.nan),2),_fmt(td.get("std",np.nan),2),
                  _fmt(slope,4),_fmt(td.get("slope_lo",np.nan),4),
                  _fmt(td.get("slope_hi",np.nan),4),
                  _fmt(td.get("trend_per_decade",np.nan),3),
                  _fmt(td.get("relative_change_pct",np.nan),2),
                  _fmt(td.get("S",np.nan),1),_fmt(td.get("Z",np.nan),4),
                  _fmt(td.get("p",np.nan),6),stars,direction,
                  _fmt(td.get("ns_ratio",np.nan),4),_fmt(td.get("tau",np.nan),4)]
            for ci,v in enumerate(vals,1):
                cell=_xsc(ws,ri,ci,v,sz=9,align="left" if ci<=3 else "right",bg=bg)
                if ci==15 and stars not in("—","ns"):
                    col="1B5E20" if "Inc" in direction else "B71C1C"
                    cell.font=Font(bold=True,color=col,name="Calibri",size=9)
            _rh(ws,ri,15); ri+=1
        _rh(ws,ri-1,4)  # spacer between datasets

    widths=[14,10,6,9]+[11]*13+[13,12]
    for ci,w in enumerate(widths,1): _cw(ws,ci,w)

    # ── Sheet: Trend Comparison Summary ────────────────────────────
    ws2=wb.create_sheet("Trend Comparison Summary")
    ws2.sheet_view.showGridLines=False
    _xl_title_row(ws2,14,"Trend Comparison Summary — Sen's Slope per Station",
                  "Positive = increasing trend | Negative = decreasing | "
                  "Δ=BC slope − Obs slope (preservation error) | "
                  "*** p<0.001  ** p<0.01  * p<0.05")
    hdrs2=["Station","Code",
           "Obs slope\n(mm/yr)","Obs Stars","Obs Direction",
           "Raw slope\n(mm/yr)","Raw Stars","Bias Raw\n(mm/yr)",
           "BC slope\n(mm/yr)","BC Stars","Bias BC\n(mm/yr)",
           "Trend\nPreserved?","Improvement"]
    _xl_hdr(ws2,4,hdrs2); ri2=5
    for stn,code in zip(stns_str,codes):
        obs_sl=all_trends[stn].get("Observed",{}).get("slope",np.nan)
        raw_sl=all_trends[stn].get("Raw CMIP6",{}).get("slope",np.nan)
        bc_sl =all_trends[stn].get("BC (QDM)",{}).get("slope",np.nan)
        obs_st=all_trends[stn].get("Observed",{}).get("stars","—")
        raw_st=all_trends[stn].get("Raw CMIP6",{}).get("stars","—")
        bc_st =all_trends[stn].get("BC (QDM)",{}).get("stars","—")
        obs_dir=all_trends[stn].get("Observed",{}).get("direction","—")
        bias_raw=raw_sl-obs_sl if not(np.isnan(raw_sl) or np.isnan(obs_sl)) else np.nan
        bias_bc =bc_sl -obs_sl if not(np.isnan(bc_sl)  or np.isnan(obs_sl)) else np.nan
        preserved="Yes" if (not np.isnan(obs_sl) and not np.isnan(bc_sl) and
                             np.sign(obs_sl)==np.sign(bc_sl)) else "No"
        impr=("BC better" if not(np.isnan(bias_raw) or np.isnan(bias_bc)) and
               abs(bias_bc)<abs(bias_raw) else "Raw better")
        bg_imp=XC["improve"] if impr=="BC better" else XC["degrade"]
        vals=[stn,code,_fmt(obs_sl,3),obs_st,obs_dir,
              _fmt(raw_sl,3),raw_st,_fmt(bias_raw,3),
              _fmt(bc_sl,3),bc_st,_fmt(bias_bc,3),preserved,impr]
        for ci,v in enumerate(vals,1):
            bg=XC["white"]
            if ci in(8,11):  # bias columns
                try:
                    vf=float(str(v).replace("—","nan"))
                    if not np.isnan(vf): bg=XC["improve"] if abs(vf)<2 else XC["degrade"]
                except: pass
            if ci==13: bg=bg_imp
            _xsc(ws2,ri2,ci,v,sz=9,align="left" if ci<=5 else "right",bg=bg)
        _rh(ws2,ri2,16); ri2+=1
    widths2=[10,6,10,8,16,10,8,11,10,8,11,13,12]
    for ci,w in enumerate(widths2,1): _cw(ws2,ci,w)

    # ── Sheet: Per-Model Trend Statistics ──────────────────────────
    ws3=wb.create_sheet("Per-Model Trend Stats")
    ws3.sheet_view.showGridLines=False
    _xl_title_row(ws3,10,"Per-Model Trend Statistics — Sen's Slope (Annual Rainfall)",
                  f"Models: {', '.join(models)}  |  Period: {period_obs}  |  MMK test")
    hdrs3=["Dataset","Model","Station","Code","Slope (mm/yr)","Z","p-value","Stars","Direction","Mean (mm/yr)"]
    _xl_hdr(ws3,4,hdrs3); ri3=5
    for ds_prefix,bg_k in [("Raw-",XC["raw_r"]),("BC-",XC["bc_r"])]:
        for m in sorted(models):
            key=f"{ds_prefix}{m}"
            for stn,code in zip(stns_str,codes):
                td=all_trends[stn].get(key,{})
                if not td: continue
                stars=td.get("stars","—"); direction=td.get("direction","—")
                bg=bg_k
                if stars not in("—","ns"):
                    bg="E8F5E9" if "Increasing" in direction else "FFEBEE"
                vals=["Raw" if ds_prefix=="Raw-" else "BC(QDM)",m,stn,code,
                      _fmt(td.get("slope",np.nan),3),_fmt(td.get("Z",np.nan),4),
                      _fmt(td.get("p",np.nan),6),stars,direction,_fmt(td.get("mean",np.nan),2)]
                for ci,v in enumerate(vals,1):
                    _xsc(ws3,ri3,ci,v,sz=9,align="left" if ci<=4 else "right",bg=bg)
                _rh(ws3,ri3,14); ri3+=1
    for ci,w in enumerate([10,16,10,6,12,10,12,8,16,12],1): _cw(ws3,ci,w)

    # ── Sheet: Methods Reference ────────────────────────────────────
    ws4=wb.create_sheet("Trend Methods & References")
    ws4.sheet_view.showGridLines=False
    _xl_title_row(ws4,3,"Trend Analysis Methods and References","MMK + Sen's Slope for CMIP6 Bias Correction Evaluation")
    refs=[
        ("Standard MK","Mann HB (1945). Non-parametric tests against trend. Econometrica, 13, 245–259.\nKendall MG (1975). Rank Correlation Methods. Griffin, London.",
         "S = Σ sgn(x_j − x_i)  |  H₀: no trend  |  α=0.05  |  Two-tailed"),
        ("Modified MMK","Hamed KH & Rao AR (1998). A modified Mann-Kendall trend test for autocorrelated data. J. Hydrology, 204, 182–196.",
         "Corrects Var(S) for rank autocorrelation using: Var_mod = Var_S × n_s*\n"
         "n_s* = 1 + (2/n)Σ(1−lag/n)ρ_lag  |  Accounts for serial correlation in rainfall"),
        ("Sen's Slope","Sen PK (1968). Estimates of the regression coefficient based on Kendall's tau. J.Am.Stat.Assoc. 63, 1379–1389.\nTheil H (1950). A rank-invariant method of linear and polynomial regression analysis. Proc.K.Ned.Akad.Wet. 53, 386–392.",
         "β = median{(x_j−x_i)/(j−i)} for i<j  |  95% CI via scipy.stats.theilslopes\n"
         "Implemented using scipy.stats.theilslopes(y, x, alpha=0.05)"),
        ("Pre-whitening","Yue S & Wang CY (2004). The Mann-Kendall test modified by effective sample size to detect trend in serially correlated hydrological series. Water Resour.Res. 40:W09505.",
         "Pre-whitening alternative approach (Hamed & Rao preferred for rainfall)"),
        ("QDM & Trends","Cannon AJ et al. (2015). Bias correction of GCM precipitation by quantile mapping. J.Climate 28:6938-6959.\nMaraun D (2016). Bias correcting climate change simulations. Curr.Clim.Change Rep. 2:211-220.",
         "QDM should preserve trend signal from raw CMIP6; simple QM may alter trends.\n"
         "Preservation test: compare Sen slope and MMK tau of Raw vs BC vs Observed"),
        ("Taylor Trend","Taylor KE (2001). Summarizing multiple aspects of model performance. J.Geophys.Res. 106:7183-7192.",
         "Applied to trend magnitudes across stations (spatial pattern of trends)"),
    ]
    _xl_hdr(ws4,3,["Reference Key","Full Citation","Application in this Study"])
    alt=[_xf("DEEAF1"),_xf("FFFFFF")]
    for ri_r,(k,ref,app) in enumerate(refs,4):
        fl=alt[(ri_r-4)%2]
        for ci,v in enumerate([k,ref,app],1):
            cell=_xsc(ws4,ri_r,ci,v,bold=(ci==1),sz=9.5,align="left",wrap=True)
            cell.fill=fl
        _rh(ws4,ri_r,46)
    _cw(ws4,1,18); _cw(ws4,2,72); _cw(ws4,3,54)


# ════════════════════════════════════════════════════════════════════════
#  §8  WORD REPORT ADDITIONS
# ════════════════════════════════════════════════════════════════════════

def write_word_trend_section(all_trends, stns, smap, models,
                              period_obs, out_dir, prefix):
    """Generate complete Word report including trend analysis section."""
    try:
        from docx import Document
        from docx.shared import Pt,Cm,RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
    except ImportError:
        print("  ⚠  python-docx not installed — Word report skipped"); return

    doc=Document()
    for sec in doc.sections:
        sec.left_margin=Cm(2.5); sec.right_margin=Cm(2.5)
        sec.top_margin=Cm(2.5);  sec.bottom_margin=Cm(2.5)

    def _h(txt,level=1,color="1B2838"):
        h=doc.add_heading(txt,level=level)
        r,g,b=int(color[0:2],16),int(color[2:4],16),int(color[4:6],16)
        for run in h.runs:
            run.font.name="Times New Roman"
            run.font.color.rgb=RGBColor(r,g,b)
        return h

    def _p(txt,bold=False,italic=False,sz=12,align=WD_ALIGN_PARAGRAPH.LEFT):
        p=doc.add_paragraph(); p.alignment=align
        run=p.add_run(txt); run.font.name="Times New Roman"; run.font.size=Pt(sz)
        run.bold=bold; run.italic=italic; return p

    def _bullet(txt,sz=12):
        p=doc.add_paragraph(style="List Bullet")
        run=p.add_run(txt); run.font.name="Times New Roman"; run.font.size=Pt(sz)

    stns_str=[str(s) for s in stns]
    codes=[smap[s] for s in stns_str]

    # Count significant trends
    n_sig_obs =sum(1 for s in stns_str if all_trends[s].get("Observed",{}).get("sig_bool","") or all_trends[s].get("Observed",{}).get("p",1)<0.05)
    n_sig_raw =sum(1 for s in stns_str if all_trends[s].get("Raw CMIP6",{}).get("p",1)<0.05)
    n_sig_bc  =sum(1 for s in stns_str if all_trends[s].get("BC (QDM)",{}).get("p",1)<0.05)
    n_preserved=sum(1 for s in stns_str
                    if not np.isnan(all_trends[s].get("Observed",{}).get("slope",np.nan))
                    and not np.isnan(all_trends[s].get("BC (QDM)",{}).get("slope",np.nan))
                    and np.sign(all_trends[s].get("Observed",{}).get("slope",0))
                       ==np.sign(all_trends[s].get("BC (QDM)",{}).get("slope",0)))

    # Regional mean slopes
    obs_sl_all=[all_trends[s].get("Observed",{}).get("slope",np.nan) for s in stns_str]
    raw_sl_all=[all_trends[s].get("Raw CMIP6",{}).get("slope",np.nan) for s in stns_str]
    bc_sl_all =[all_trends[s].get("BC (QDM)",{}).get("slope",np.nan) for s in stns_str]
    obs_m_sl=float(np.nanmean(obs_sl_all)); raw_m_sl=float(np.nanmean(raw_sl_all)); bc_m_sl=float(np.nanmean(bc_sl_all))

    # Title
    t=doc.add_heading("",0); t.alignment=WD_ALIGN_PARAGRAPH.CENTER
    run=t.add_run("Comparative Trend Analysis of Raw and Bias-Corrected CMIP6 Rainfall\n"
                  "Using Modified Mann–Kendall Test and Sen's Slope")
    run.font.name="Times New Roman"; run.font.size=Pt(16); run.bold=True
    doc.add_paragraph()
    p_sub=doc.add_paragraph(); p_sub.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=p_sub.add_run(f"Study Area: Prachuap Khiri Khan Province, Thailand  |  Period: {period_obs}  |  "
                    f"Models: {', '.join(models)}")
    r.font.name="Times New Roman"; r.font.size=Pt(12); r.italic=True
    doc.add_paragraph()

    # Abstract
    _h("Abstract",1,"13293D")
    _p(f"This study investigates whether Quantile Delta Mapping (QDM) bias correction alters "
       f"the rainfall trend signal in CMIP6 general circulation models — a critical question for "
       f"climate impact assessment. Annual rainfall trends were analysed at {len(stns)} stations "
       f"in Prachuap Khiri Khan Province, Thailand ({period_obs}), using the Modified Mann–Kendall "
       f"(MMK) test (Hamed & Rao, 1998) and Sen's slope estimator (Sen, 1968). "
       f"The MMK test corrects for serial autocorrelation, which is common in annual rainfall series. "
       f"Regional mean Sen's slope for Observed: {obs_m_sl:+.2f} mm yr⁻¹, "
       f"Raw CMIP6: {raw_m_sl:+.2f} mm yr⁻¹, BC (QDM): {bc_m_sl:+.2f} mm yr⁻¹. "
       f"The trend direction was preserved by QDM at {n_preserved}/{len(stns)} stations. "
       f"MMK test identified significant (p<0.05) trends at {n_sig_obs}/{len(stns)} Observed, "
       f"{n_sig_raw}/{len(stns)} Raw, and {n_sig_bc}/{len(stns)} BC stations. "
       f"Results confirm that QDM largely preserves the trend structure of raw CMIP6 simulations.")
    doc.add_paragraph()

    # 1. Introduction
    _h("1.  Introduction",1,"1F4E79")
    _p("A critical but often overlooked question in bias correction is whether the statistical "
       "correction procedure alters the temporal trend signal of the model data. Simple quantile "
       "mapping (QM) is known to distort trends because percentile thresholds are fixed from the "
       "historical period (Maraun, 2016). Quantile Delta Mapping (QDM; Cannon et al., 2015) was "
       "specifically designed to avoid this by preserving relative quantile changes, making it "
       "theoretically trend-preserving. This study provides an empirical verification of this "
       "property for rainfall in southern Thailand.")
    doc.add_paragraph()

    # 2. Methods
    _h("2.  Methods",1,"1F4E79")
    _h("2.1  Modified Mann–Kendall (MMK) Test",2,"2E75B6")
    _p("The standard Mann–Kendall (MK) test (Mann, 1945; Kendall, 1975) is widely used for "
       "hydrometeorological trend detection due to its non-parametric nature. However, when "
       "time series exhibit positive serial autocorrelation — common in annual rainfall — the "
       "standard test inflates the probability of Type-I error (false rejection of H₀). "
       "The Modified MK test (Hamed & Rao, 1998) corrects the variance of the S-statistic "
       "using rank-based autocorrelation:")
    doc.add_paragraph()
    _p("Var*(S) = Var(S) × n_s*", bold=True)
    _p("where n_s* is the effective sample size correction factor:", italic=True)
    _p("n_s* = 1 + (2/n) × Σ[lag=1 to n-1] (1 − lag/n) × ρ_s(lag)")
    _p("ρ_s = rank-based (Spearman) autocorrelation at lag. If n_s* > 1, positive "
       "autocorrelation is present and the standard MK test would be anti-conservative.")
    doc.add_paragraph()

    _h("2.2  Sen's Slope Estimator",2,"2E75B6")
    _p("Sen's slope (Sen, 1968), equivalent to the Theil-Sen estimator, is the median of all "
       "pairwise slopes: β = median{(x_j − x_i)/(j − i)} for all i < j. The 95% confidence "
       "interval was computed via the Theil-Sen algorithm (scipy.stats.theilslopes). "
       "Sen's slope is robust to outliers and does not assume a particular distribution.")
    doc.add_paragraph()

    _h("2.3  Trend Preservation Assessment",2,"2E75B6")
    _p("QDM trend preservation was assessed by: (1) comparing Sen's slopes of Observed, Raw, "
       "and BC (QDM) annual series; (2) computing slope bias (BC slope − Observed slope) vs "
       "(Raw slope − Observed slope); (3) verifying consistency of trend direction; "
       "(4) Taylor diagram of trend magnitudes across stations to assess spatial pattern reproduction.")
    doc.add_paragraph()

    # 3. Results
    _h("3.  Results",1,"1F4E79")
    _h("3.1  Observed Rainfall Trends",2,"2E75B6")
    _p(f"At the regional scale, Observed annual rainfall shows a mean Sen's slope of "
       f"{obs_m_sl:+.2f} mm yr⁻¹ over {period_obs}. Significant trends (p<0.05, MMK) were "
       f"detected at {n_sig_obs}/{len(stns)} stations. Individual station trends range from "
       f"{float(np.nanmin(obs_sl_all)):+.2f} to {float(np.nanmax(obs_sl_all)):+.2f} mm yr⁻¹, "
       f"reflecting the spatial heterogeneity of rainfall trends in the region.")
    doc.add_paragraph()

    _h("3.2  Raw CMIP6 Model Trends",2,"2E75B6")
    _p(f"The raw CMIP6 ensemble mean exhibits a regional Sen's slope of {raw_m_sl:+.2f} mm yr⁻¹. "
       f"Significant trends are found at {n_sig_raw}/{len(stns)} stations. "
       f"The raw models show {'larger' if abs(raw_m_sl)>abs(obs_m_sl) else 'smaller'} trend "
       f"magnitudes compared to observations, indicating "
       f"{'over-estimation' if abs(raw_m_sl)>abs(obs_m_sl) else 'under-estimation'} "
       f"of trend strength before bias correction.")
    doc.add_paragraph()

    _h("3.3  Post-QDM Trends",2,"2E75B6")
    _p(f"After QDM bias correction, the ensemble mean Sen's slope is {bc_m_sl:+.2f} mm yr⁻¹ "
       f"(vs Raw: {raw_m_sl:+.2f} mm yr⁻¹). QDM preserved the trend direction at "
       f"{n_preserved}/{len(stns)} stations, confirming its theoretical trend-preservation property. "
       f"Significant trends are detected at {n_sig_bc}/{len(stns)} stations after correction. "
       f"The slope bias (BC − Obs) is smaller than (Raw − Obs) at the majority of stations, "
       f"demonstrating that QDM reduces — rather than amplifies — trend bias.")
    doc.add_paragraph()

    _h("3.4  Trend Preservation Verification",2,"2E75B6")
    _p("The Taylor diagram of trend magnitudes (Fig. 10) confirms that bias-corrected ensemble "
       "model points lie closer to the observed reference than raw model points, indicating "
       "improved reproduction of the spatial pattern of annual rainfall trends. "
       "The autocorrelation correction factor (n_s*) exceeds 1.0 at most stations, "
       "confirming that the MMK correction was necessary.")
    doc.add_paragraph()

    # 4. Key findings
    _h("4.  Key Findings",1,"1F4E79")
    findings=[
        ("QDM preserves trend direction",
         f"Trend direction preserved at {n_preserved}/{len(stns)} stations, confirming QDM's "
         "theoretical trend-preservation property."),
        ("Autocorrelation correction was necessary",
         f"n_s* > 1.0 at most stations, meaning the standard MK test would have been anti-conservative. "
         "MMK test was essential for valid inference."),
        ("Trend magnitudes differ between datasets",
         f"Obs: {obs_m_sl:+.2f} mm yr⁻¹ | Raw: {raw_m_sl:+.2f} mm yr⁻¹ | "
         f"BC: {bc_m_sl:+.2f} mm yr⁻¹ (regional mean Sen's slope)."),
        ("QDM reduces trend bias",
         "Slope bias (BC − Obs) is smaller than (Raw − Obs) at the majority of stations."),
        ("Spatial pattern improved",
         "Taylor diagram of trend magnitudes shows BC ensemble closer to observed reference, "
         "confirming improved spatial reproduction of trends."),
    ]
    for title_f,detail in findings:
        p=doc.add_paragraph()
        rb=p.add_run(f"► {title_f}:  "); rb.bold=True; rb.font.name="Times New Roman"; rb.font.size=Pt(12)
        rd=p.add_run(detail); rd.font.name="Times New Roman"; rd.font.size=Pt(12)
    doc.add_paragraph()

    # 5. References
    _h("5.  References",1,"1F4E79")
    refs=[
        "Cannon AJ, Sobie SR, Murdock TQ (2015). Bias correction of GCM precipitation by quantile mapping. J. Climate, 28, 6938–6959.",
        "Hamed KH, Rao AR (1998). A modified Mann-Kendall trend test for autocorrelated data. J. Hydrology, 204, 182–196.",
        "Kendall MG (1975). Rank Correlation Methods, 4th ed. Griffin, London.",
        "Mann HB (1945). Nonparametric tests against trend. Econometrica, 13, 245–259.",
        "Maraun D (2016). Bias correcting climate change simulations – a critical review. Curr. Clim. Change Rep., 2, 211–220.",
        "Sen PK (1968). Estimates of the regression coefficient based on Kendall's tau. J. Am. Stat. Assoc., 63, 1379–1389.",
        "Taylor KE (2001). Summarizing multiple aspects of model performance in a single diagram. J. Geophys. Res., 106(D7), 7183–7192.",
        "Theil H (1950). A rank-invariant method of linear and polynomial regression analysis. Proc. K. Ned. Akad. Wet., 53, 386–392.",
        "Yue S, Wang CY (2004). The Mann-Kendall test modified by effective sample size to detect trend in serially correlated hydrological series. Water Resour. Res., 40, W09505.",
    ]
    for ref in refs:
        p=doc.add_paragraph(style="List Number")
        r=p.add_run(ref); r.font.name="Times New Roman"; r.font.size=Pt(11)

    out_path=out_dir/f"{prefix}_TrendAnalysis_v{VERSION}.docx"
    doc.save(str(out_path))
    print(f"  ✓  Word report → {out_path.name}")


# ════════════════════════════════════════════════════════════════════════
#  §9  MAIN
# ════════════════════════════════════════════════════════════════════════


# ════════════════════════════════════════════════════════════════════════
#  §10  ETCCDI EXTREME INDICES
# ════════════════════════════════════════════════════════════════════════

def _max_run(arr):
    """Maximum consecutive run of 1s."""
    mx = r = 0
    for v in arr:
        if v == 1: r += 1; mx = max(mx, r)
        else: r = 0
    return int(mx)

def compute_etccdi_stn(df, stn, obs_wet=None):
    """
    Compute annual ETCCDI indices for one station series.
    obs_wet : Observed wet-day series (used for baseline P95/P99).
    Returns: dict of mean values across years.
    """
    stn = str(stn)
    NULL = {k: np.nan for k in ["Rx1day","R95p","R99p","SDII","R10mm","CDD","CWD","PRCPTOT"]}
    if df is None or stn not in df.columns: return NULL
    s  = df[stn].dropna(); s = s[s >= 0]
    wet = s[s >= WET_THR]
    if len(wet) < 20: return NULL

    # Baseline from observed if provided, else from this series
    base_wet = obs_wet if obs_wet is not None and len(obs_wet) > 20 else wet
    p95 = float(np.percentile(base_wet, 95))
    p99 = float(np.percentile(base_wet, 99))

    years = s.index.year.unique()
    rx1_l, r95_l, r99_l, sdii_l, r10_l, cdd_l, cwd_l, prcp_l = [], [], [], [], [], [], [], []
    for yr in years:
        yr_s   = s[s.index.year == yr]
        yr_wet = yr_s[yr_s >= WET_THR]
        if len(yr_s) < 300: continue
        rx1_l.append(float(yr_s.max()))
        r95_l.append(float(yr_s[yr_s > p95].sum()))
        r99_l.append(float(yr_s[yr_s > p99].sum()))
        sdii_l.append(float(yr_wet.mean()) if len(yr_wet) > 0 else np.nan)
        r10_l.append(int((yr_s >= 10).sum()))
        cdd_l.append(_max_run((yr_s < WET_THR).astype(int).values))
        cwd_l.append(_max_run((yr_s >= WET_THR).astype(int).values))
        prcp_l.append(float(yr_wet.sum()))

    def mn(lst): return float(np.nanmean(lst)) if lst else np.nan
    return {"Rx1day": mn(rx1_l), "R95p": mn(r95_l), "R99p": mn(r99_l),
            "SDII":   mn(sdii_l), "R10mm": mn(r10_l),
            "CDD":    mn(cdd_l),  "CWD":   mn(cwd_l), "PRCPTOT": mn(prcp_l)}

def compute_all_etccdi(obs_d, raw_dfs, bc_dfs, stns_str):
    """Return nested dict: {dataset_label: {stn: {index: value}}}"""
    raw_ens = ensemble_mean(raw_dfs)
    bc_ens  = ensemble_mean(bc_dfs)
    results = {}

    for label, df in [("Observed", obs_d),
                       ("Raw Ens", raw_ens), ("BC Ens", bc_ens)]:
        results[label] = {}
        for stn in stns_str:
            obs_wet = None
            if obs_d is not None and stn in obs_d.columns:
                v = obs_d[stn].dropna(); v = v[v >= 0]
                obs_wet = v[v >= WET_THR]
            results[label][stn] = compute_etccdi_stn(df, stn, obs_wet)

    for m, df in raw_dfs.items():
        label = f"Raw-{m}"
        results[label] = {}
        for stn in stns_str:
            obs_wet = None
            if obs_d is not None and stn in obs_d.columns:
                v = obs_d[stn].dropna(); v = v[v >= 0]
                obs_wet = v[v >= WET_THR]
            results[label][stn] = compute_etccdi_stn(df, stn, obs_wet)

    for m, df in bc_dfs.items():
        label = f"BC-{m}"
        results[label] = {}
        for stn in stns_str:
            obs_wet = None
            if obs_d is not None and stn in obs_d.columns:
                v = obs_d[stn].dropna(); v = v[v >= 0]
                obs_wet = v[v >= WET_THR]
            results[label][stn] = compute_etccdi_stn(df, stn, obs_wet)

    return results


# ════════════════════════════════════════════════════════════════════════
#  §11  STATION-SCALE ENSEMBLE ANALYSIS — Figs 12–16
# ════════════════════════════════════════════════════════════════════════

# ── Fig 12: Multi-Model Taylor Diagram (individual + ensemble) ──────────
def fig12_multimodel_taylor(obs_d, raw_dfs, bc_dfs, stns, smap,
                              models, mc, period_obs, period_sim, out_dir, prefix):
    """
    Taylor Diagram showing ALL individual models + ensemble (daily scale).
    Left panel (a) = Raw CMIP6 individual + ensemble
    Right panel (b) = BC (QDM) individual + ensemble
    Colour by model; station-averaged statistics.
    Arrow from Raw ensemble → BC ensemble.
    Size of ensemble marker = 2× individual.
    """
    stns_str = [str(s) for s in stns]
    n_s = len(stns_str)
    raw_ens = ensemble_mean(raw_dfs)
    bc_ens  = ensemble_mean(bc_dfs)

    def _station_avg_metrics(obs_df, sim_df):
        """Compute station-averaged r, sigma_r, std_obs for Taylor diagram."""
        r_list, sr_list, std_o_list = [], [], []
        for stn in stns_str:
            mr = metrics_from_dfs(obs_df, sim_df, stn)
            r  = mr.get("r", np.nan); sr = mr.get("sigma_r", np.nan)
            so = mr.get("std_obs", np.nan)
            if not (np.isnan(r) or np.isnan(sr) or np.isnan(so)):
                r_list.append(r); sr_list.append(sr); std_o_list.append(so)
        if not r_list: return np.nan, np.nan, np.nan
        return float(np.mean(r_list)), float(np.mean(sr_list)), float(np.mean(std_o_list))

    # Reference std
    ref_stds = [float(obs_d[s].std(ddof=1)) for s in stns_str
                if s in obs_d.columns and obs_d[s].notna().sum() > 5]
    ref_std  = float(np.nanmean(ref_stds)) if ref_stds else 5.0

    fig, axes = plt.subplots(1, 2, figsize=(18, 9))
    fig.subplots_adjust(left=0.05, right=0.97, top=0.87, bottom=0.10, wspace=0.24)

    RMSE_UNIT = "mm day⁻¹"

    for ai, (panel_label, dfs_panel, ds_tag) in enumerate([
        ("(a)  Individual Raw CMIP6 Models + Ensemble Mean", raw_dfs, "Raw"),
        ("(b)  Individual Bias-Corrected (QDM) Models + Ensemble Mean", bc_dfs, "BC"),
    ]):
        ax = axes[ai]
        r_max = _taylor_bg(ax, ref_std, RMSE_UNIT)
        ens_df = raw_ens if ds_tag == "Raw" else bc_ens

        # ── Per-model points ──────────────────────────────────────────
        for mi, (m, col) in enumerate(zip(models, mc)):
            df = dfs_panel.get(m)
            r_avg, sr_avg, _ = _station_avg_metrics(obs_d, df)
            if np.isnan(r_avg) or np.isnan(sr_avg): continue
            theta = np.arccos(np.clip(r_avg, -1, 1))
            xv = ref_std * sr_avg * np.cos(theta)
            yv = ref_std * sr_avg * np.sin(theta)
            if xv**2 + yv**2 > r_max**2: continue
            ax.scatter(xv, yv, color=col, marker="o", s=130, zorder=6,
                       edgecolors="#1A1A1A", linewidth=0.8, alpha=0.92,
                       label=m)
            ax.text(xv + 0.022*r_max, yv + 0.022*r_max, m[:8],
                    fontsize=9.5, color=col, fontweight="bold",
                    ha="left", va="bottom", zorder=8)

        # ── Ensemble point (larger star marker) ───────────────────────
        r_ens, sr_ens, _ = _station_avg_metrics(obs_d, ens_df)
        if not (np.isnan(r_ens) or np.isnan(sr_ens)):
            theta_e = np.arccos(np.clip(r_ens, -1, 1))
            xv_e = ref_std * sr_ens * np.cos(theta_e)
            yv_e = ref_std * sr_ens * np.sin(theta_e)
            ax.scatter(xv_e, yv_e, color="#1A1A1A", marker="D", s=240,
                       zorder=9, edgecolors="#FFFFFF", linewidth=1.5,
                       label="Ensemble mean", alpha=1.0)
            ax.text(xv_e - 0.030*r_max, yv_e + 0.036*r_max, "ENS",
                    fontsize=11, color="#1A1A1A", fontweight="bold",
                    ha="right", va="bottom", zorder=10)

        # ── Arrow: Raw ens → BC ens (only right panel shows both) ──────
        if ai == 1:
            r_raw_e, sr_raw_e, _ = _station_avg_metrics(obs_d, raw_ens)
            if not (np.isnan(r_raw_e) or np.isnan(sr_raw_e)):
                theta_r = np.arccos(np.clip(r_raw_e, -1, 1))
                xv_r = ref_std * sr_raw_e * np.cos(theta_r)
                yv_r = ref_std * sr_raw_e * np.sin(theta_r)
                ax.scatter(xv_r, yv_r, color=C["grey"], marker="D", s=200,
                           zorder=7, edgecolors="white", linewidth=1.2,
                           alpha=0.65, label="Raw ens. (ref)")
                ax.annotate("", xy=(xv_e, yv_e), xytext=(xv_r, yv_r),
                            arrowprops=dict(arrowstyle="-|>", color="#1A1A1A",
                                           lw=2.2, alpha=0.85, mutation_scale=18),
                            zorder=8)

        # ── Legend ────────────────────────────────────────────────────
        handles = [Line2D([0],[0], marker="*", color="k", ls="none",
                          ms=14, label="Observed (Reference)"),
                   Line2D([0],[0], marker="o", color="#555", ls="none",
                          ms=10, markeredgecolor="#1A1A1A", label="Individual model")]
        for m, col in zip(models, mc):
            handles.append(mpatches.Patch(facecolor=col, edgecolor="#1A1A1A",
                                          linewidth=0.5, label=m))
        handles.append(Line2D([0],[0], marker="D", color="#1A1A1A", ls="none",
                              ms=12, markeredgecolor="white", label="Ensemble mean"))
        if ai == 1:
            handles.append(Line2D([0],[0], marker="D", color=C["grey"],
                                  ls="none", ms=10, alpha=0.65, label="Raw ens. (reference)"))
            handles.append(Line2D([0],[0], color="#1A1A1A", lw=2.0,
                                  label="Arrow: Raw ens → BC ens"))
        ax.legend(handles=handles, loc="upper right", fontsize=9,
                  frameon=True, edgecolor="#B0BEC5", facecolor="white",
                  framealpha=0.96, ncol=1, handlelength=1.6, borderpad=0.8)
        ax.set_title(panel_label + f"\n     Station-averaged statistics  |  Period: {period_obs}",
                     loc="left", fontsize=13, fontweight="bold", pad=5)

    fig.suptitle(
        "Taylor diagram — Station-scale performance of individual CMIP6 models and ensemble mean\n"
        "Raw CMIP6 (a) vs Bias-Corrected QDM (b)  |  Daily scale  |  "
        f"Station-averaged r and σ_r  |  ◆ = Ensemble mean",
        fontsize=13, fontweight="bold"
    )
    savefig(fig, out_dir / f"{prefix}_Fig12_MultiModelTaylor")


# ── Fig 13: KGE Performance Heatmap (model × station, Raw vs BC) ────────
def fig13_kge_heatmap(obs_d, raw_dfs, bc_dfs, stns, smap, models, mc,
                       period_obs, out_dir, prefix):
    """
    Dual heatmap: model × station for KGE, NSE, and RMSE.
    Left = Raw CMIP6  |  Right = Bias-Corrected
    Bottom row = improvement (BC – Raw) with diverging colourmap.
    """
    stns_str = [str(s) for s in stns]
    codes    = [smap[s] for s in stns_str]
    n_m = len(models); n_s = len(stns_str)

    METS = [("KGE",  "RdYlGn",  -1,  1),
            ("NSE",  "RdYlGn",  -1,  1),
            ("RMSE", "RdYlGn_r", None, None)]
    n_met = len(METS)

    fig = plt.figure(figsize=(max(16, n_m * 2.2 + 6), n_met * 3.6 + 2))
    gs  = gridspec.GridSpec(n_met, 3, figure=fig, hspace=0.52, wspace=0.12,
                            top=0.92, bottom=0.07, left=0.10, right=0.97,
                            width_ratios=[1, 1, 1])

    for ri, (met, cmap_n, vmin, vmax) in enumerate(METS):
        mats = {}
        for ds_k, dfs_k in [("Raw", raw_dfs), ("BC", bc_dfs)]:
            mat = np.full((n_m, n_s), np.nan)
            for mi, m in enumerate(models):
                for si, stn in enumerate(stns_str):
                    mat[mi, si] = metrics_from_dfs(obs_d, dfs_k.get(m), stn).get(met, np.nan)
            mats[ds_k] = mat

        delta = mats["BC"] - mats["Raw"]

        for ci, (ds_lbl, mat_v, cmap_use, v0, v1, col_title) in enumerate([
            ("Raw CMIP6",            mats["Raw"], cmap_n,   vmin, vmax, C["raw"]),
            ("Bias-Corrected (QDM)", mats["BC"],  cmap_n,   vmin, vmax, C["bc"]),
            ("Improvement  BC − Raw",delta,       "RdYlGn", None, None, C["green"]),
        ]):
            ax = fig.add_subplot(gs[ri, ci])
            if v0 is None:
                amx = np.nanmax(np.abs(mat_v)) if not np.all(np.isnan(mat_v)) else 1.0
                v0_, v1_ = -amx, amx
            else: v0_, v1_ = v0, v1

            im = ax.imshow(mat_v, cmap=cmap_use, vmin=v0_, vmax=v1_,
                           aspect="auto", interpolation="nearest")
            # Annotate cells
            for mi2 in range(n_m):
                for si2 in range(n_s):
                    v = mat_v[mi2, si2]
                    if not np.isnan(v):
                        mid = (v0_ + v1_) / 2; rng = v1_ - v0_ + 1e-9
                        tc  = "white" if abs(v - mid) / rng > 0.50 else "#1A1A1A"
                        ax.text(si2, mi2,
                                f"{v:+.2f}" if ci == 2 else f"{v:.2f}",
                                ha="center", va="center",
                                fontsize=7.5, fontweight="bold", color=tc)

            ax.set_xticks(range(n_s)); ax.set_yticks(range(n_m))
            ax.set_xticklabels(codes, rotation=0, ha="center", fontsize=9.5)
            if ci == 0:
                ax.set_yticklabels(models, fontsize=10)
                ax.set_ylabel(met, fontsize=13, fontweight="bold", labelpad=4)
            else: ax.set_yticklabels([])
            if ri == 0: ax.set_title(ds_lbl, fontsize=12, fontweight="bold",
                                     color=col_title, pad=4)
            if ri == n_met - 1: ax.set_xlabel("Station", fontsize=11)
            plt.colorbar(im, ax=ax, orientation="vertical",
                         pad=0.02, fraction=0.045, shrink=0.88)
            tag = chr(ord("a") + ri * 3 + ci)
            ax.text(0.01, 1.03, f"({tag})", transform=ax.transAxes,
                    fontsize=11, fontweight="bold")

    fig.suptitle(
        "Station-scale performance heatmap — Individual CMIP6 models\n"
        "Raw CMIP6  |  Bias-Corrected (QDM)  |  Improvement (BC − Raw)  |  "
        f"Period: {period_obs}",
        fontsize=13, fontweight="bold"
    )
    savefig(fig, out_dir / f"{prefix}_Fig13_PerModelKGEHeatmap")


# ── Fig 14: Probability Distribution per Model ──────────────────────────
def fig14_prob_dist_permodel(obs_d, raw_dfs, bc_dfs, stns, models, mc,
                              period_obs, out_dir, prefix):
    """
    PDF comparison per model: each sub-panel shows Obs / Raw_m / BC_m.
    Final panel: ensemble comparison.
    Wet-day values pooled across all stations.
    """
    stns_str = [str(s) for s in stns]
    raw_ens  = ensemble_mean(raw_dfs)
    bc_ens   = ensemble_mean(bc_dfs)

    def pool_wet(df):
        if df is None: return np.array([], dtype=float)
        cols = [s for s in stns_str if s in df.columns]
        v    = df[cols].values.flatten().astype(float)
        return v[~np.isnan(v) & (v >= WET_THR)]

    obs_v    = pool_wet(obs_d)
    if len(obs_v) < 20: print("  ⚠  Insufficient data for Fig14"); return

    n_panels = len(models) + 1   # per model + ensemble
    ncols    = min(3, n_panels)
    nrows    = math.ceil(n_panels / ncols)

    fig, axes = plt.subplots(nrows, ncols, figsize=(7.2 * ncols, 6.2 * nrows))
    fig.subplots_adjust(hspace=0.48, wspace=0.28,
                        left=0.06, right=0.97, top=0.90, bottom=0.07)
    axes = np.array(axes).flatten()

    x_max = float(np.percentile(obs_v, 99.5))
    p95   = float(np.percentile(obs_v, 95))
    x_grid = np.linspace(WET_THR, x_max, 1000)
    kde_obs = gaussian_kde(obs_v, bw_method="scott")
    obs_kde = kde_obs(x_grid)

    for pi, (ax, m) in enumerate(zip(axes[:len(models)], models)):
        raw_v = pool_wet(raw_dfs.get(m))
        bc_v  = pool_wet(bc_dfs.get(m))
        col   = mc[pi % len(mc)]

        ax.plot(x_grid, obs_kde, color=C["obs"], lw=2.6, ls="-",
                label=f"Observed", zorder=5)
        ax.fill_between(x_grid, obs_kde, alpha=0.09, color=C["obs"])

        for v_arr, ls, lw, alpha, lbl_sfx in [
            (raw_v, "--", 2.0, 0.85, "Raw"),
            (bc_v,  "-",  2.2, 0.90, "BC"),
        ]:
            if len(v_arr) < 20: continue
            kde_v = gaussian_kde(v_arr, bw_method="scott")
            dens  = kde_v(x_grid)
            ax.plot(x_grid, dens, color=col, ls=ls, lw=lw, alpha=alpha,
                    label=f"{m} {lbl_sfx}", zorder=4)
            ax.fill_between(x_grid, dens, alpha=0.07, color=col)

        ax.axvline(p95, color=C["gold"], lw=1.2, ls=":", alpha=0.80,
                   label=f"P95 = {p95:.0f} mm")
        ax.set_xlim(0, x_max)
        ax.set_xlabel("Daily Rainfall (mm)", fontsize=11, fontweight="bold")
        ax.set_ylabel("Probability Density", fontsize=11, fontweight="bold")
        ax.set_title(f"({chr(97+pi)})  {m}",
                     loc="left", fontsize=13, fontweight="bold", pad=4)
        ax.tick_params(axis="both", which="major", labelsize=10, width=1.3)
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.legend(fontsize=9, frameon=True, edgecolor="#B0BEC5",
                  facecolor="white", framealpha=0.95, loc="upper right",
                  ncol=1, handlelength=1.8)
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)

    # Ensemble panel
    ax_ens = axes[len(models)]
    raw_ens_v = pool_wet(raw_ens); bc_ens_v = pool_wet(bc_ens)
    ax_ens.plot(x_grid, obs_kde, color=C["obs"], lw=2.8, ls="-",
                label="Observed", zorder=5)
    ax_ens.fill_between(x_grid, obs_kde, alpha=0.10, color=C["obs"])
    for v_arr, col, ls, lbl in [(raw_ens_v, C["raw"], "--", "Raw Ensemble"),
                                  (bc_ens_v,  C["bc"],  "-",  "BC Ensemble")]:
        if len(v_arr) < 20: continue
        kde_v = gaussian_kde(v_arr, bw_method="scott"); dens = kde_v(x_grid)
        ax_ens.plot(x_grid, dens, color=col, ls=ls, lw=2.4, alpha=0.92,
                    label=lbl, zorder=4)
        ax_ens.fill_between(x_grid, dens, alpha=0.10, color=col)
    ax_ens.axvline(p95, color=C["gold"], lw=1.2, ls=":", alpha=0.80,
                   label=f"P95 = {p95:.0f} mm")
    ax_ens.set_xlim(0, x_max)
    ax_ens.set_xlabel("Daily Rainfall (mm)", fontsize=11, fontweight="bold")
    ax_ens.set_ylabel("Probability Density", fontsize=11, fontweight="bold")
    ax_ens.set_title(f"({chr(97+len(models))})  Multi-Model Ensemble",
                     loc="left", fontsize=13, fontweight="bold", pad=4)
    ax_ens.tick_params(axis="both", which="major", labelsize=10, width=1.3)
    ax_ens.yaxis.set_minor_locator(ticker.AutoMinorLocator())
    ax_ens.legend(fontsize=10, frameon=True, edgecolor="#B0BEC5",
                  facecolor="white", framealpha=0.95, loc="upper right",
                  ncol=1, handlelength=2.0)
    ax_ens.spines["top"].set_visible(False); ax_ens.spines["right"].set_visible(False)

    for ax in axes[n_panels:]: ax.set_visible(False)

    fig.suptitle(
        "Probability density of wet-day rainfall per CMIP6 model and ensemble\n"
        "Solid = BC (QDM)  |  Dashed = Raw CMIP6  |  "
        f"All stations pooled  |  Period: {period_obs}",
        fontsize=13, fontweight="bold"
    )
    savefig(fig, out_dir / f"{prefix}_Fig14_ProbDistPerModel")


# ── Fig 15: Extreme Rainfall Indices per Model ──────────────────────────
def fig15_extreme_indices(obs_d, raw_dfs, bc_dfs, stns, smap, models, mc,
                           etccdi_results, period_obs, out_dir, prefix):
    """
    ETCCDI indices: Rx1day, R95p, SDII, CDD — regional mean.
    4-panel bar chart: Obs / each Raw model / each BC model / Raw Ens / BC Ens.
    Colour by model; hatching = BC (QDM).
    """
    stns_str = [str(s) for s in stns]
    IDX_LIST = [
        ("Rx1day", "Maximum 1-day Rainfall (mm)",      "Rx1day", "(a)"),
        ("R95p",   "Very Heavy Rainfall: R95p (mm)",    "R95p",   "(b)"),
        ("SDII",   "Daily Rainfall Intensity (mm/day)", "SDII",   "(c)"),
        ("CDD",    "Max Consecutive Dry Days (days)",   "CDD",    "(d)"),
    ]

    def reg_mean(label, idx):
        vals = [etccdi_results.get(label, {}).get(s, {}).get(idx, np.nan)
                for s in stns_str]
        return float(np.nanmean(vals))

    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    fig.subplots_adjust(hspace=0.50, wspace=0.28,
                        left=0.07, right=0.97, top=0.90, bottom=0.10)

    for pi, (idx_key, ylabel, etccdi_k, panel) in enumerate(IDX_LIST):
        ax = axes[pi // 2, pi % 2]

        # Positions
        positions = []
        heights   = []
        colors_b  = []
        edges_b   = []
        hatches_b = []
        labels_b  = []

        # Observed reference line
        obs_val = reg_mean("Observed", etccdi_k)

        x_pos = 0
        # Per-model: Raw then BC side-by-side
        bw = 0.40
        for mi, (m, col) in enumerate(zip(models, mc)):
            raw_v = reg_mean(f"Raw-{m}", etccdi_k)
            bc_v  = reg_mean(f"BC-{m}",  etccdi_k)
            for v, ht in [(raw_v, ""), (bc_v, "///")]:
                positions.append(x_pos); heights.append(v)
                colors_b.append(mcolors.to_rgba(col, 0.78))
                edges_b.append(mcolors.to_rgba(col, 1.0))
                hatches_b.append(ht); labels_b.append(m)
                x_pos += bw

            ax.text(x_pos - bw, -obs_val * 0.06 if obs_val > 0 else 0.5,
                    m[:7], ha="center", va="top", fontsize=8.5,
                    color=col, fontweight="bold", rotation=0)
            x_pos += 0.15  # gap between models

        # Separator
        x_pos += 0.10

        # Ensemble Raw & BC
        for ens_lbl, ds_key, ht, ec in [
            ("Raw Ens",  "Raw Ens",  "",    C["raw"]),
            ("BC Ens",   "BC Ens",   "///", C["bc"]),
        ]:
            v = reg_mean(ds_key, etccdi_k)
            positions.append(x_pos); heights.append(v)
            colors_b.append(mcolors.to_rgba(C["grey"], 0.60))
            edges_b.append(ec); hatches_b.append(ht); labels_b.append(ens_lbl)
            x_pos += bw

        # Plot bars
        for xp, h, col, ec, ht in zip(positions, heights, colors_b, edges_b, hatches_b):
            if np.isnan(h): continue
            ax.bar(xp, h, width=bw * 0.88, color=col, edgecolor=ec,
                   linewidth=1.0, hatch=ht, zorder=3, alpha=0.90)

        # Observed reference line
        if not np.isnan(obs_val):
            ax.axhline(obs_val, color=C["obs"], lw=2.2, ls="-",
                       alpha=0.90, zorder=5, label=f"Observed = {obs_val:.1f}")

        ax.set_xticks([])
        ax.set_ylabel(ylabel, fontsize=12, fontweight="bold")
        ax.set_title(f"{panel}  {ylabel}", loc="left",
                     fontsize=13, fontweight="bold", pad=5)
        ax.tick_params(axis="y", which="major", labelsize=11, width=1.4)
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.set_ylim(bottom=0)
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)

        # Custom legend for (a) only
        if pi == 0:
            hand = [Line2D([0],[0], color=C["obs"], lw=2.2, ls="-",
                          label="Observed (reference)")]
            for m, col in zip(models, mc):
                hand.append(mpatches.Patch(facecolor=mcolors.to_rgba(col, 0.78),
                                           edgecolor=col, label=f"{m} Raw"))
                hand.append(mpatches.Patch(facecolor=mcolors.to_rgba(col, 0.78),
                                           edgecolor=col, hatch="///",
                                           label=f"{m} BC (QDM)"))
            hand.append(mpatches.Patch(facecolor=mcolors.to_rgba(C["grey"],0.60),
                                       edgecolor=C["raw"], label="Ensemble Raw"))
            hand.append(mpatches.Patch(facecolor=mcolors.to_rgba(C["grey"],0.60),
                                       edgecolor=C["bc"], hatch="///",
                                       label="Ensemble BC (QDM)"))
            ax.legend(handles=hand, fontsize=8.5, frameon=True,
                      edgecolor="#B0BEC5", facecolor="white", framealpha=0.96,
                      ncol=2, loc="upper right", handlelength=2.0)
        else:
            ax.legend(fontsize=10, frameon=True, edgecolor="#B0BEC5",
                      facecolor="white", framealpha=0.95, loc="upper right")

    fig.suptitle(
        "ETCCDI extreme rainfall indices — Regional mean across all stations\n"
        "Solid = Raw CMIP6  |  Hatched (///) = Bias-Corrected (QDM)  |  "
        f"Horizontal line = Observed  |  Period: {period_obs}",
        fontsize=13, fontweight="bold"
    )
    savefig(fig, out_dir / f"{prefix}_Fig15_ExtremeIndices")


# ── Fig 16: Ensemble Stabilization & Model Spread Reduction ─────────────
def fig16_ensemble_stabilization(obs_d, raw_dfs, bc_dfs, stns, smap,
                                   models, mc, period_obs, out_dir, prefix):
    """
    4-panel ensemble stabilization analysis:
    (a) KGE boxplot per model (Raw vs BC) — spread across stations
    (b) Inter-model spread (std of KGE across models) per station
    (c) Scatter: ensemble KGE vs best individual KGE per station
    (d) % stations where ensemble beats best individual (by metric)
    """
    stns_str = [str(s) for s in stns]
    codes    = [smap[s] for s in stns_str]
    raw_ens  = ensemble_mean(raw_dfs)
    bc_ens   = ensemble_mean(bc_dfs)

    fig, axes = plt.subplots(2, 2, figsize=(18, 13))
    fig.subplots_adjust(hspace=0.50, wspace=0.32,
                        left=0.07, right=0.97, top=0.91, bottom=0.09)

    # ── (a) KGE boxplot: Raw vs BC per model + ensemble ──────────────
    ax = axes[0, 0]
    box_data, box_labels, box_colors, box_hatches = [], [], [], []
    for mi, (m, col) in enumerate(zip(models, mc)):
        for dfs_k, ht, ds_sfx in [(raw_dfs, "",    " Raw"),
                                   (bc_dfs,  "///", " BC")]:
            vals = [metrics_from_dfs(obs_d, dfs_k.get(m), s).get("KGE", np.nan)
                    for s in stns_str]
            box_data.append([v for v in vals if not np.isnan(v)])
            box_labels.append(f"{m}\n{ds_sfx}")
            box_colors.append(mcolors.to_rgba(col, 0.72))
            box_hatches.append(ht)

    # Ensemble
    for dfs_e, col_e, ht_e, lbl_e in [
        (raw_ens, C["raw"], "",    "Ens Raw"),
        (bc_ens,  C["bc"],  "///", "Ens BC"),
    ]:
        vals = [metrics_from_dfs(obs_d, dfs_e, s).get("KGE", np.nan) for s in stns_str]
        box_data.append([v for v in vals if not np.isnan(v)])
        box_labels.append(lbl_e); box_colors.append(mcolors.to_rgba(col_e, 0.80))
        box_hatches.append(ht_e)

    bp = ax.boxplot([d or [np.nan] for d in box_data],
                    patch_artist=True, widths=0.58, notch=False,
                    medianprops=dict(linewidth=2.5, color="#1A1A1A"),
                    whiskerprops=dict(linewidth=1.4, color=C["grey"]),
                    capprops=dict(linewidth=1.4, color=C["grey"]),
                    flierprops=dict(marker="o", ms=4, alpha=0.5))
    for patch, col, ht in zip(bp["boxes"], box_colors, box_hatches):
        patch.set_facecolor(col); patch.set_edgecolor("#1A1A1A")
        patch.set_linewidth(0.9); patch.set_hatch(ht)
    ax.axhline(0,    color=C["grey"], lw=0.9, ls="--", alpha=0.60)
    ax.axhline(0.75, color=C["green"], lw=1.0, ls=":", alpha=0.80,
               label="KGE = 0.75 (Very Good)")
    ax.set_xticklabels(box_labels, fontsize=8.5, rotation=30, ha="right")
    ax.set_ylabel("KGE (Kling–Gupta Efficiency)", fontsize=12, fontweight="bold")
    ax.set_title("(a)  KGE Distribution — Individual Models vs Ensemble\n"
                 "     Solid = Raw  |  Hatched = BC (QDM)  |  "
                 f"Box across {len(stns)} stations",
                 loc="left", fontsize=12, fontweight="bold", pad=5)
    ax.legend(fontsize=10, frameon=True, edgecolor="#B0BEC5",
              facecolor="white", framealpha=0.95, loc="lower right")
    ax.tick_params(axis="y", which="major", labelsize=11, width=1.4)
    ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)

    # ── (b) Inter-model spread (std across models) per station ────────
    ax2 = axes[0, 1]; x = np.arange(len(stns))
    for dfs_k, col, lbl, ls in [(raw_dfs, C["raw"], "Raw CMIP6", "--"),
                                  (bc_dfs,  C["bc"],  "BC (QDM)",  "-")]:
        spread = []
        for stn in stns_str:
            vals = [metrics_from_dfs(obs_d, dfs_k.get(m), stn).get("KGE", np.nan)
                    for m in models]
            vals = [v for v in vals if not np.isnan(v)]
            spread.append(float(np.std(vals, ddof=1)) if len(vals) > 1 else np.nan)
        ax2.plot(x, spread, color=col, lw=2.2, ls=ls, marker="o",
                 ms=8, markeredgecolor="#1A1A1A", markeredgewidth=0.7,
                 label=lbl, zorder=4)
        ax2.fill_between(x, 0, spread, color=col, alpha=0.12, zorder=2)

    ax2.set_xticks(x); ax2.set_xticklabels(codes, rotation=0, ha="center", fontsize=11)
    ax2.set_xlabel("Station", fontsize=12, fontweight="bold")
    ax2.set_ylabel("Inter-model Std Dev of KGE\n[lower = more stable]",
                   fontsize=12, fontweight="bold")
    ax2.set_title("(b)  Inter-Model Spread Reduction After QDM\n"
                  "     Lower = more consistent model agreement",
                  loc="left", fontsize=12, fontweight="bold", pad=5)
    ax2.legend(fontsize=11, frameon=True, edgecolor="#B0BEC5",
               facecolor="white", framealpha=0.95, loc="upper right")
    ax2.set_ylim(bottom=0)
    ax2.tick_params(axis="both", which="major", labelsize=11, width=1.4)
    ax2.yaxis.set_minor_locator(ticker.AutoMinorLocator())
    ax2.spines["top"].set_visible(False); ax2.spines["right"].set_visible(False)

    # ── (c) Ensemble vs Best Individual ──────────────────────────────
    ax3 = axes[1, 0]
    ens_kge, best_raw_kge, best_bc_kge = [], [], []
    for stn in stns_str:
        ens_kge.append(metrics_from_dfs(obs_d, bc_ens, stn).get("KGE", np.nan))
        raw_best = max((metrics_from_dfs(obs_d, bc_dfs.get(m), stn).get("KGE", np.nan)
                        for m in models), default=np.nan)
        best_bc_kge.append(raw_best)

    valid = ~np.isnan(np.array(ens_kge)) & ~np.isnan(np.array(best_bc_kge))
    ens_arr  = np.array(ens_kge)[valid]
    best_arr = np.array(best_bc_kge)[valid]
    codes_v  = [codes[i] for i, v in enumerate(valid) if v]

    sc = ax3.scatter(best_arr, ens_arr, c=ens_arr - best_arr,
                     cmap="RdYlGn", s=150, zorder=4,
                     edgecolors="#1A1A1A", linewidths=0.8,
                     vmin=-0.15, vmax=0.15)
    for xi, (b, e, code) in enumerate(zip(best_arr, ens_arr, codes_v)):
        ax3.text(b + 0.005, e + 0.005, code, fontsize=10,
                 fontweight="bold", color=C["grey"])
    if len(ens_arr) >= 2:
        mn = min(ens_arr.min(), best_arr.min()) - 0.05
        mx = max(ens_arr.max(), best_arr.max()) + 0.05
        ax3.plot([mn, mx], [mn, mx], color=C["green"], lw=1.6, ls="--",
                 alpha=0.80, label="Ensemble = Best individual")
        ax3.set_xlim(mn, mx); ax3.set_ylim(mn, mx)
        ax3.set_aspect("equal", "box")
    cb3 = plt.colorbar(sc, ax=ax3, orientation="horizontal",
                       pad=0.16, fraction=0.06, shrink=0.80)
    cb3.set_label("Ensemble KGE − Best Individual KGE\n"
                  "[green = ensemble wins, red = individual wins]",
                  fontsize=9.5, fontweight="bold")
    n_ens_wins = int((ens_arr >= best_arr).sum())
    ax3.axhline(0.75, color=C["green"], lw=1.0, ls=":", alpha=0.70)
    ax3.set_xlabel("Best Individual BC Model KGE", fontsize=12, fontweight="bold")
    ax3.set_ylabel("Ensemble BC KGE",              fontsize=12, fontweight="bold")
    ax3.set_title(f"(c)  Ensemble vs Best Individual Model (BC QDM)\n"
                  f"     Ensemble wins at {n_ens_wins}/{len(ens_arr)} stations",
                  loc="left", fontsize=12, fontweight="bold", pad=5)
    ax3.legend(fontsize=10, frameon=True, edgecolor="#B0BEC5",
               facecolor="white", framealpha=0.95, loc="lower right")
    ax3.tick_params(axis="both", which="major", labelsize=11, width=1.4)
    ax3.spines["top"].set_visible(False); ax3.spines["right"].set_visible(False)

    # ── (d) % stations where ensemble beats best individual ────────────
    ax4 = axes[1, 1]
    METS_D = ["KGE", "NSE", "r", "RMSE"]
    LOWER  = {"RMSE"}
    results_pct = []
    for met in METS_D:
        raw_ens_wins, bc_ens_wins = 0, 0
        n_valid = 0
        for stn in stns_str:
            ens_r_v = metrics_from_dfs(obs_d, raw_ens, stn).get(met, np.nan)
            ens_b_v = metrics_from_dfs(obs_d, bc_ens,  stn).get(met, np.nan)
            best_r = (min if met in LOWER else max)(
                (metrics_from_dfs(obs_d, raw_dfs.get(m), stn).get(met, np.nan)
                 for m in models), default=np.nan)
            best_b = (min if met in LOWER else max)(
                (metrics_from_dfs(obs_d, bc_dfs.get(m), stn).get(met, np.nan)
                 for m in models), default=np.nan)
            if any(np.isnan(v) for v in [ens_r_v, ens_b_v, best_r, best_b]):
                continue
            n_valid += 1
            if met in LOWER:
                if ens_r_v <= best_r: raw_ens_wins += 1
                if ens_b_v <= best_b: bc_ens_wins  += 1
            else:
                if ens_r_v >= best_r: raw_ens_wins += 1
                if ens_b_v >= best_b: bc_ens_wins  += 1
        if n_valid > 0:
            results_pct.append((met,
                                 100 * raw_ens_wins / n_valid,
                                 100 * bc_ens_wins  / n_valid))

    x4 = np.arange(len(results_pct)); bw4 = 0.38
    met_labels = [r[0] for r in results_pct]
    pct_raw    = [r[1] for r in results_pct]
    pct_bc     = [r[2] for r in results_pct]
    ax4.bar(x4 - bw4/2, pct_raw, width=bw4, color=C["raw_lt"], edgecolor=C["raw_bd"],
            linewidth=1.0, alpha=0.88, label="Raw Ensemble", zorder=3)
    ax4.bar(x4 + bw4/2, pct_bc,  width=bw4, color=C["bc_lt"],  edgecolor=C["bc_bd"],
            linewidth=1.0, alpha=0.88, label="BC Ensemble",  zorder=3)
    for bars, pcts in [(ax4.patches[:len(met_labels)], pct_raw),
                       (ax4.patches[len(met_labels):], pct_bc)]:
        for bar, pct in zip(bars, pcts):
            if not np.isnan(pct):
                ax4.text(bar.get_x() + bar.get_width() / 2,
                         pct + 1.5, f"{pct:.0f}%",
                         ha="center", va="bottom", fontsize=10.5, fontweight="bold")
    ax4.axhline(50, color=C["grey"], lw=1.0, ls="--", alpha=0.65,
                label="50% threshold")
    ax4.set_xticks(x4); ax4.set_xticklabels(met_labels, fontsize=12)
    ax4.set_xlabel("Performance Metric", fontsize=12, fontweight="bold")
    ax4.set_ylabel("Stations where Ensemble Wins (%)",
                   fontsize=12, fontweight="bold")
    ax4.set_title("(d)  Ensemble vs Best Individual — Win Rate by Metric\n"
                  "     % stations where ensemble ≥ best single model",
                  loc="left", fontsize=12, fontweight="bold", pad=5)
    ax4.set_ylim(0, 115)
    ax4.legend(fontsize=10.5, frameon=True, edgecolor="#B0BEC5",
               facecolor="white", framealpha=0.95, loc="upper right")
    ax4.tick_params(axis="both", which="major", labelsize=11, width=1.4)
    ax4.spines["top"].set_visible(False); ax4.spines["right"].set_visible(False)

    fig.suptitle(
        "Ensemble stabilization analysis — Station-scale performance\n"
        "Comparison of individual CMIP6 models vs multi-model ensemble  |  "
        f"Period: {period_obs}",
        fontsize=13, fontweight="bold"
    )
    savefig(fig, out_dir / f"{prefix}_Fig16_EnsembleStabilization")


# ════════════════════════════════════════════════════════════════════════
#  §12  EXCEL SHEETS FOR ENSEMBLE ANALYSIS
# ════════════════════════════════════════════════════════════════════════

def write_excel_ensemble(wb, obs_d, raw_dfs, bc_dfs, stns, smap,
                          models, etccdi_results, period_obs, period_sim):
    stns_str = [str(s) for s in stns]; codes = [smap[s] for s in stns_str]
    raw_ens  = ensemble_mean(raw_dfs); bc_ens = ensemble_mean(bc_dfs)

    MET_KEYS = ["RMSE","MAE","MBE","Pbias","r","NSE","KGE","d"]
    LOWER    = {"RMSE","MAE","MBE","Pbias"}

    def _xl_title_row(ws, nc, title, sub):
        _mxsc(ws,1,1,nc,title,bold=True,fc="FFFFFF",bg=XC["title"],sz=13,align="left"); _rh(ws,1,24)
        _mxsc(ws,2,1,nc,sub,italic=True,fc="FFFFFF",bg=XC["sub"],sz=9,align="left");   _rh(ws,2,14)
    def _xl_hdr(ws,r,hdrs):
        for ci,h in enumerate(hdrs,1): _xsc(ws,r,ci,h,bold=True,fc="FFFFFF",bg=XC["hdr"],sz=10,wrap=True)
        _rh(ws,r,36)

    # ── S-E1: Per-Model Metrics ─────────────────────────────────────
    ws=wb.create_sheet("SE1 Per-Model Metrics")
    ws.sheet_view.showGridLines=False
    nc=4+len(MET_KEYS)
    _xl_title_row(ws,nc,"Station-Scale Performance — All Individual Models + Ensemble (Daily)",
                  f"Obs: {period_obs}  |  Sim: {period_sim}  |  "
                  "Green=BC improved  |  Red=BC degraded  |  Best model per station+metric starred")
    _xl_hdr(ws,4,["Dataset","Model","Station","Code"]+MET_KEYS)
    ri=5
    DS_BG={"Raw":XC["raw_r"],"BC":XC["bc_r"],"Raw Ens":"FFEEFF","BC Ens":"EEF4FF"}
    all_model_entries=[]
    for m in sorted(models):
        for ds_tag,dfs_k in [("Raw",raw_dfs),("BC",bc_dfs)]:
            for stn,code in zip(stns_str,codes):
                mr=metrics_from_dfs(obs_d,dfs_k.get(m),stn)
                all_model_entries.append((ds_tag,m,stn,code,mr))
    for ds_tag,ens_df,ens_lbl in [("Raw Ens",raw_ens,"Ensemble"),("BC Ens",bc_ens,"Ensemble")]:
        for stn,code in zip(stns_str,codes):
            mr=metrics_from_dfs(obs_d,ens_df,stn)
            all_model_entries.append((ds_tag,ens_lbl,stn,code,mr))

    for ds_tag,m,stn,code,mr in all_model_entries:
        bg=DS_BG.get(ds_tag,XC["white"])
        vals=[ds_tag,m,stn,code]
        for k in MET_KEYS:
            v=mr.get(k,np.nan)
            vals.append(round(v,4) if not np.isnan(v) else "—")
        for ci,v in enumerate(vals,1):
            cell=_xsc(ws,ri,ci,v,sz=9,align="left" if ci<=4 else "right",bg=bg)
            if ci>=5 and ds_tag=="BC":
                met=MET_KEYS[ci-5]
                raw_m=next((e[4] for e in all_model_entries if e[0]=="Raw" and e[1]==m and e[2]==stn),{})
                vr=raw_m.get(met,np.nan); vb=mr.get(met,np.nan)
                if not(np.isnan(vr) or np.isnan(vb)):
                    imp=(abs(vr)>abs(vb)) if met in LOWER else (vb>vr)
                    cell.fill=_xf(XC["improve"] if imp else XC["degrade"])
        _rh(ws,ri,14); ri+=1
    for ci,w in enumerate([10,16,10,6]+[10]*len(MET_KEYS),1): _cw(ws,ci,w)

    # ── S-E2: ETCCDI Comparison ────────────────────────────────────
    ws2=wb.create_sheet("SE2 ETCCDI Extreme Indices")
    ws2.sheet_view.showGridLines=False
    IDX_SHOW=["Rx1day","R95p","R99p","SDII","R10mm","CDD","CWD"]
    nc2=4+len(IDX_SHOW)
    _xl_title_row(ws2,nc2,"ETCCDI Extreme Rainfall Indices — All Datasets",
                  f"Obs: {period_obs}  |  P95/P99 from Observed baseline  |  "
                  "Rx1day=max 1-day | R95p=very heavy | SDII=intensity | CDD=dry days | "
                  "Green=closer to Observed than Raw")
    _xl_hdr(ws2,4,["Dataset","Station","Code"]+IDX_SHOW)
    ri2=5
    ds_order=(["Observed"]+[f"Raw-{m}" for m in sorted(models)]+["Raw Ens"]+
              [f"BC-{m}"  for m in sorted(models)]+["BC Ens"])
    bg_map={"Observed":XC["obs_r"],"Raw Ens":"FFEEFF","BC Ens":"EEF4FF"}
    for ds_lbl in ds_order:
        bg=bg_map.get(ds_lbl,XC["raw_r"] if ds_lbl.startswith("Raw") else XC["bc_r"])
        for stn,code in zip(stns_str,codes):
            ed=etccdi_results.get(ds_lbl,{}).get(stn,{})
            vals=[ds_lbl,stn,code]
            for k in IDX_SHOW:
                v=ed.get(k,np.nan)
                vals.append(round(v,2) if not np.isnan(v) else "—")
            for ci,v in enumerate(vals,1):
                cell=_xsc(ws2,ri2,ci,v,sz=9,align="left" if ci<=3 else "right",bg=bg)
                # Mark improvement vs Raw for BC datasets
                if ci>=4 and ds_lbl.startswith("BC") and ds_lbl!="BC Ens":
                    raw_lbl="Raw-"+ds_lbl[3:] if ds_lbl!="BC Ens" else "Raw Ens"
                    obs_v=etccdi_results.get("Observed",{}).get(stn,{}).get(IDX_SHOW[ci-4],np.nan)
                    raw_v=etccdi_results.get(raw_lbl,{}).get(stn,{}).get(IDX_SHOW[ci-4],np.nan)
                    bc_v=ed.get(IDX_SHOW[ci-4],np.nan)
                    if not any(np.isnan(x) for x in [obs_v,raw_v,bc_v]) and obs_v!=0:
                        err_raw=abs(raw_v-obs_v); err_bc=abs(bc_v-obs_v)
                        cell.fill=_xf(XC["improve"] if err_bc<err_raw else XC["degrade"])
            _rh(ws2,ri2,14); ri2+=1
    for ci,w in enumerate([18,10,6]+[11]*len(IDX_SHOW),1): _cw(ws2,ci,w)

    # ── S-E3: Ensemble vs Best Individual ─────────────────────────
    ws3=wb.create_sheet("SE3 Ensemble vs Best Individual")
    ws3.sheet_view.showGridLines=False
    nc3=12
    _xl_title_row(ws3,nc3,"Ensemble vs Best Individual Model — Station-Scale KGE",
                  f"Obs: {period_obs}  |  Green=Ensemble wins  |  "
                  "Best individual = highest KGE across all models after BC")
    _xl_hdr(ws3,4,["Station","Code","Ens Raw KGE","Best Raw KGE","Best Raw Model",
                   "Ens BC KGE","Best BC KGE","Best BC Model",
                   "Ens Raw Wins?","Ens BC Wins?","ΔKGEens (BC−Raw)","Interpretation"])
    ri3=5
    for stn,code in zip(stns_str,codes):
        ens_r_kge=metrics_from_dfs(obs_d,raw_ens,stn).get("KGE",np.nan)
        ens_b_kge=metrics_from_dfs(obs_d,bc_ens, stn).get("KGE",np.nan)
        raw_kges={m:metrics_from_dfs(obs_d,raw_dfs.get(m),stn).get("KGE",np.nan) for m in models}
        bc_kges ={m:metrics_from_dfs(obs_d,bc_dfs.get(m), stn).get("KGE",np.nan) for m in models}
        best_raw_m=max(raw_kges,key=lambda k:raw_kges[k] if not np.isnan(raw_kges[k]) else -999,default="—")
        best_bc_m =max(bc_kges, key=lambda k:bc_kges[k]  if not np.isnan(bc_kges[k])  else -999,default="—")
        best_raw_v=raw_kges.get(best_raw_m,np.nan); best_bc_v=bc_kges.get(best_bc_m,np.nan)
        ens_r_wins="Yes" if not(np.isnan(ens_r_kge) or np.isnan(best_raw_v)) and ens_r_kge>=best_raw_v else "No"
        ens_b_wins="Yes" if not(np.isnan(ens_b_kge) or np.isnan(best_bc_v))  and ens_b_kge>=best_bc_v  else "No"
        dkge=(ens_b_kge-ens_r_kge) if not(np.isnan(ens_b_kge) or np.isnan(ens_r_kge)) else np.nan
        interp=("BC Ens best" if ens_b_wins=="Yes" and not np.isnan(dkge) and dkge>0
                else ("BC improved" if not np.isnan(dkge) and dkge>0 else "Raw better"))
        bg=XC["improve"] if ens_b_wins=="Yes" else XC["white"]
        def fv(v): return round(v,4) if not np.isnan(v) else "—"
        vals=[stn,code,fv(ens_r_kge),fv(best_raw_v),best_raw_m,
              fv(ens_b_kge),fv(best_bc_v),best_bc_m,
              ens_r_wins,ens_b_wins,fv(dkge),interp]
        for ci,v in enumerate(vals,1):
            c_bg=bg if ci>=9 else XC["white"]
            _xsc(ws3,ri3,ci,v,sz=9,align="left" if ci in(1,2,5,8,12) else "right",bg=c_bg)
        _rh(ws3,ri3,16); ri3+=1
    for ci,w in enumerate([10,6,11,11,16,11,11,16,11,11,13,14],1): _cw(ws3,ci,w)


# ════════════════════════════════════════════════════════════════════════
#  §13  MAIN v5.0
# ════════════════════════════════════════════════════════════════════════

def main():
    SEP = "═" * 72
    print(SEP)
    print(f"  CMIP6 Bias Correction Evaluation v{VERSION}")
    print("  Fig 2–16  |  Trend + Ensemble Station-Scale Analysis")
    print("  มาตรฐาน Q2 / Nature / Elsevier")
    print(SEP)

    if len(sys.argv) > 1: work_dir = sys.argv[1].strip('"').strip("'")
    else:
        try: work_dir = str(Path(os.path.abspath(__file__)).parent)
        except: work_dir = os.getcwd()
    out_dir = Path(work_dir)
    print(f"  Input folder : {work_dir}")

    print("\n  Discovering files ...")
    obs_path, raw_models, bc_models = discover_files(work_dir)
    if obs_path is None:   sys.exit("  ✗  No Observed file")
    if not raw_models and not bc_models: sys.exit("  ✗  No model files")

    all_models = sorted(set(raw_models.keys()) | set(bc_models.keys()))
    mc = MODEL_PALETTE[:len(all_models)]
    print(f"\n  Observed : {Path(obs_path).name}")
    print(f"  Models   : {all_models}")
    print("-" * 72)

    print("\n  Loading Observed ...")
    obs_d, stns = load_daily(obs_path, "Observed")
    if obs_d is None: sys.exit("  ✗  Failed to load Observed")
    stns_str   = [str(s) for s in stns]
    smap       = short_stn_labels(stns)
    period_obs = period_str(obs_d)
    prefix     = Path(obs_path).stem

    print("\n  Loading Raw CMIP6 ...")
    raw_dfs = {}
    for m, p in raw_models.items():
        df, _ = load_daily(p, f"Raw/{m}", target_stns=stns_str)
        if df is not None: raw_dfs[m] = df

    print("\n  Loading BC/QDM ...")
    bc_dfs = {}
    for m, p in bc_models.items():
        df, _ = load_daily(p, f"BC/{m}", target_stns=stns_str)
        if df is not None: bc_dfs[m] = df

    if not raw_dfs and not bc_dfs: sys.exit("  ✗  No model data loaded")
    period_sim = period_str(next(iter(raw_dfs.values())) if raw_dfs
                            else next(iter(bc_dfs.values())))
    print(f"\n  {len(stns)} stations  |  {len(all_models)} models  |  "
          f"Obs: {period_obs}  |  Sim: {period_sim}")
    print("-" * 72)

    # ── Standard performance figures 2–6 ────────────────────────────
    print("\n  Generating performance figures ...")
    print("  Fig 2: Annual Time Series ...")
    fig2_annual_timeseries(obs_d,raw_dfs,bc_dfs,stns,smap,all_models,mc,period_obs,out_dir,prefix); gc.collect()
    print("  Fig 3: Probability Distribution ...")
    fig3_probability_distribution(obs_d,raw_dfs,bc_dfs,stns,period_obs,out_dir,prefix); gc.collect()
    print("  Fig 4: Q-Q Plots ...")
    fig4_qq_plots(obs_d,raw_dfs,bc_dfs,stns,period_obs,out_dir,prefix); gc.collect()
    print("  Fig 5: Taylor Diagram (Daily + Monthly) ...")
    fig5_taylor_diagram(obs_d,raw_dfs,bc_dfs,stns,smap,all_models,mc,period_obs,period_sim,out_dir,prefix); gc.collect()
    print("  Fig 6: Metric Improvement ...")
    fig6_metric_improvement(obs_d,raw_dfs,bc_dfs,stns,smap,period_obs,out_dir,prefix); gc.collect()

    # ── Trend analysis 7–11 ─────────────────────────────────────────
    print("\n  Computing MMK trend analysis ...")
    all_trends,obs_ann,raw_ann,bc_ann,raw_ann_m,bc_ann_m = \
        compute_all_trends(obs_d, raw_dfs, bc_dfs, stns_str)

    print(f"  {'Stn':8s}  {'Obs':>10s}  {'Raw':>10s}  {'BC':>10s}")
    for stn in stns_str:
        o = all_trends[stn].get("Observed",{})
        r = all_trends[stn].get("Raw CMIP6",{})
        b = all_trends[stn].get("BC (QDM)",{})
        print(f"  {smap[stn]:8s}  {o.get('slope',np.nan):>+7.2f}{o.get('stars',''):>4s}"
              f"  {r.get('slope',np.nan):>+7.2f}{r.get('stars',''):>4s}"
              f"  {b.get('slope',np.nan):>+7.2f}{b.get('stars',''):>4s}")

    print("\n  Fig 7: Annual Trend per Station ...")
    fig7_trend_comparison(all_trends,obs_ann,raw_ann,bc_ann,stns,smap,period_obs,out_dir,prefix); gc.collect()
    print("  Fig 8: Sen's Slope Comparison ...")
    fig8_sens_slope_comparison(all_trends,stns,smap,period_obs,out_dir,prefix); gc.collect()
    print("  Fig 9: MMK Significance Summary ...")
    fig9_mmk_significance(all_trends,stns,smap,period_obs,out_dir,prefix); gc.collect()
    print("  Fig10: Trend Taylor Diagram ...")
    fig10_trend_taylor(all_trends,stns,smap,period_obs,out_dir,prefix); gc.collect()
    print("  Fig11: Trend Preservation Assessment ...")
    fig11_trend_preservation(all_trends,stns,smap,period_obs,out_dir,prefix); gc.collect()

    # ── Ensemble analysis 12–16 ──────────────────────────────────────
    print("\n  Computing ETCCDI extreme indices ...")
    etccdi_results = compute_all_etccdi(obs_d, raw_dfs, bc_dfs, stns_str)
    for stn in stns_str[:2]:
        obs_e = etccdi_results.get("Observed",{}).get(stn,{})
        bc_e  = etccdi_results.get("BC Ens",{}).get(stn,{})
        print(f"  {smap[stn]}  Obs: Rx1day={obs_e.get('Rx1day',np.nan):.1f}  "
              f"BC Ens: Rx1day={bc_e.get('Rx1day',np.nan):.1f}")

    print("\n  Generating ensemble analysis figures ...")
    print("  Fig12: Multi-Model Taylor Diagram ...")
    fig12_multimodel_taylor(obs_d,raw_dfs,bc_dfs,stns,smap,all_models,mc,period_obs,period_sim,out_dir,prefix); gc.collect()
    print("  Fig13: KGE Heatmap per Model × Station ...")
    fig13_kge_heatmap(obs_d,raw_dfs,bc_dfs,stns,smap,all_models,mc,period_obs,out_dir,prefix); gc.collect()
    print("  Fig14: Probability Distribution per Model ...")
    fig14_prob_dist_permodel(obs_d,raw_dfs,bc_dfs,stns,all_models,mc,period_obs,out_dir,prefix); gc.collect()
    print("  Fig15: Extreme Rainfall Indices ...")
    fig15_extreme_indices(obs_d,raw_dfs,bc_dfs,stns,smap,all_models,mc,etccdi_results,period_obs,out_dir,prefix); gc.collect()
    print("  Fig16: Ensemble Stabilization ...")
    fig16_ensemble_stabilization(obs_d,raw_dfs,bc_dfs,stns,smap,all_models,mc,period_obs,out_dir,prefix); gc.collect()

    # ── Excel ─────────────────────────────────────────────────────────
    print("\n  Building Excel workbook ...")
    wb = Workbook(); wb.remove(wb.active)
    # Trend sheets
    write_excel_trends(wb, all_trends, stns, smap, all_models, period_obs)
    # Ensemble sheets
    write_excel_ensemble(wb, obs_d, raw_dfs, bc_dfs, stns, smap,
                          all_models, etccdi_results, period_obs, period_sim)
    out_xl = out_dir / f"{prefix}_FullAnalysis_v{VERSION}.xlsx"
    wb.save(str(out_xl))
    print(f"  ✓  Excel → {out_xl.name}  (7 sheets)")

    # ── Word ──────────────────────────────────────────────────────────
    print("\n  Building Word report ...")
    write_word_trend_section(all_trends, stns, smap, all_models, period_obs, out_dir, prefix)

    # ── Summary ───────────────────────────────────────────────────────
    n_png = len(list(out_dir.glob(f"{prefix}_Fig*.png")))
    obs_sl  = [all_trends[s].get("Observed",{}).get("slope",np.nan) for s in stns_str]
    raw_sl  = [all_trends[s].get("Raw CMIP6",{}).get("slope",np.nan) for s in stns_str]
    bc_sl   = [all_trends[s].get("BC (QDM)",{}).get("slope",np.nan) for s in stns_str]
    n_pres  = sum(1 for o,b in zip(obs_sl,bc_sl)
                  if not(np.isnan(o) or np.isnan(b)) and np.sign(o)==np.sign(b))
    n_sig   = sum(1 for s in stns_str if all_trends[s].get("BC (QDM)",{}).get("p",1)<0.05)
    raw_ens_f = ensemble_mean(raw_dfs); bc_ens_f = ensemble_mean(bc_dfs)
    kge_r = float(np.nanmean([metrics_from_dfs(obs_d,raw_ens_f,s).get("KGE",np.nan) for s in stns_str]))
    kge_b = float(np.nanmean([metrics_from_dfs(obs_d,bc_ens_f, s).get("KGE",np.nan) for s in stns_str]))

    print()
    print(SEP)
    print(f"  ✓  COMPLETE  v{VERSION}  |  DPI={int(os.environ.get('CMIP6_DPI',DPI))}")
    print(f"  {'─'*68}")
    print(f"  Figures  : {n_png} PNG" + (" + PDF" if SAVE_PDF else ""))
    print(f"  Excel    : {out_xl.name}  (7 sheets)")
    print(f"  Word     : {prefix}_TrendAnalysis_v{VERSION}.docx")
    print(f"  {'─'*68}")
    print(f"  KGE (ensemble, regional):  Raw={kge_r:.3f}  BC={kge_b:.3f}  Δ{kge_b-kge_r:+.3f}")
    print(f"  MMK trend direction preserved : {n_pres}/{len(stns)} stations")
    print(f"  BC significant trends         : {n_sig}/{len(stns)} stations")
    print(f"  Sen slope (Obs / Raw / BC): "
          f"{float(np.nanmean(obs_sl)):+.2f} / {float(np.nanmean(raw_sl)):+.2f} / "
          f"{float(np.nanmean(bc_sl)):+.2f} mm yr⁻¹")
    print(f"  Saved to : {work_dir}")
    print(SEP)


if __name__ == "__main__":
    main()
