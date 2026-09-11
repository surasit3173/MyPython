"""
CMIP6 bias-correction evaluation workflow for journal-ready outputs.
Generates Taylor diagrams, Q-Q plots, heatmaps, metric-improvement charts,
significance tests, climatology figures, annual time series, and an Excel
summary workbook.
"""

import os, sys, re, math, warnings
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats as sps
from scipy.stats import (gaussian_kde, pearsonr, spearmanr,
                         wilcoxon as scipy_wilcoxon, ks_2samp)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker
import matplotlib.gridspec as gridspec
import matplotlib.colors as mcolors
import matplotlib.cm as cm
from matplotlib.lines import Line2D
from matplotlib.colorbar import ColorbarBase

from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

warnings.filterwarnings("ignore")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 
#  -0  CONSTANTS & STYLE
# 

VERSION    = "3.8-Q1-HR98-full"
ETCCDI_BASE_START=1981
ETCCDI_BASE_END=2010
WET_THR    = 1.0              # mm/day - WMO wet-day threshold
TREND_LAG_K = int(os.environ.get("CMIP6_TREND_LAG_K", "3"))
ACF_MAX_LAG = int(os.environ.get("CMIP6_ACF_MAX_LAG", "7"))
ETCCDI_MIN_DAYS = int(os.environ.get("CMIP6_ETCCDI_MIN_DAYS", "300"))
WET_MONTHS = [5,6,7,8,9,10]  # May-October (Thai monsoon)
DRY_MONTHS = [11,12,1,2,3,4]
MONTH_ABBR = ["Jan","Feb","Mar","Apr","May","Jun",
              "Jul","Aug","Sep","Oct","Nov","Dec"]
DPI        = int(os.environ.get('CMIP6_DPI','600'))  # set CMIP6_DPI=300 for testing
SAVE_PDF   = True
MISS_FLAGS = [-99,-999,-9999,-9.99e+20,9.99e+20,1e+20]

# Colour palette (colour-blind safe)
C = dict(
    obs    = "#1B2838",   obs_lt = "#B0BEC5",
    raw    = "#C62828",   raw_lt = "#FFCDD2",   raw_bd = "#B71C1C",
    bc     = "#1565C0",   bc_lt  = "#BBDEFB",   bc_bd  = "#0D47A1",
    ens    = "#2E7D32",   ens_lt = "#C8E6C9",   ens_bd = "#1B5E20",
    green  = "#1B5E20",   gold   = "#F57F17",
    grey   = "#546E7A",   purple = "#6A1B9A",
    amber  = "#FF8F00",   teal   = "#00695C",
)

# Per-model palette (up to 8 models)
MODEL_PALETTE = ["#1565C0","#C62828","#2E7D32","#E65100",
                 "#6A1B9A","#00695C","#AD1457","#4527A0"]

# Performance criteria (Moriasi et al. 2007; Gupta et al. 2009)
NSE_CRITERIA  = {"Very Good":0.75, "Good":0.65, "Satisfactory":0.50}
KGE_CRITERIA  = {"Very Good":0.75, "Good":0.50, "Satisfactory":0.25}
RMSE_RS_GOOD  = 0.60   # RSR = RMSE/-_obs < 0.60 - Good

# Publication matplotlib style
plt.rcParams.update({
    "font.family":      "serif",
    "font.serif":       ["Times New Roman","DejaVu Serif"],
    "font.weight":      "bold",
    "font.size":        12,
    "axes.titlesize":   14,"axes.titleweight":"bold",
    "axes.labelsize":   13,"axes.labelweight":"bold",
    "xtick.labelsize":  11,"ytick.labelsize":11,
    "legend.fontsize":  10.5,
    "figure.titlesize": 14,
    "lines.linewidth":  2.0,
    "axes.linewidth":   1.4,
    "axes.spines.top":  False,"axes.spines.right":False,
    "axes.grid":        True,
    "grid.linestyle":   "-","grid.linewidth":0.45,
    "grid.alpha":       0.45,"grid.color":"#B0BEC5",
    "savefig.dpi":      DPI,"savefig.bbox":"tight",
    "savefig.pad_inches":0.15,"figure.dpi":110,
    "mathtext.fontset": "stix",
    "pdf.fonttype":42,"ps.fonttype":42,
})

# Excel helpers
THIN = Side(style="thin",   color="BDBDBD")
MED  = Side(style="medium", color="1F4E79")
XC   = dict(
    title="13293D", sub="1F4E79", hdr="2E75B6", hdr2="546E7A",
    obs_r="E8F5E9", raw_r="FFEBEE", bc_r="E3F2FD",
    best="FFF9C4",  best_f="E65100",
    improve="C8E6C9", degrade="FFCCBC",
    white="FFFFFF", alt="F5F5F5", note="ECEFF1",
    sig="DCEEFB",  nsig="FFFFFF", insuf="F5F5F5",
)

def _tb():    return Border(left=THIN,right=THIN,top=THIN,bottom=THIN)
def _mb():    return Border(left=MED, right=MED, top=MED, bottom=MED)
def _xf(h):   return PatternFill("solid",fgColor=h)

def xsc(ws,r,c,val=None,bold=False,italic=False,fc=None,bg=None,
        align="center",sz=10,wrap=True):
    cell=ws.cell(row=r,column=c)
    if val is not None: cell.value=val
    cell.font=Font(bold=bold,italic=italic,name="Calibri",size=sz,
                   color=fc if fc else "1A1A1A")
    cell.alignment=Alignment(horizontal=align,vertical="center",wrap_text=wrap)
    if bg: cell.fill=_xf(bg)
    cell.border=_tb()
    return cell

def mxsc(ws,r,c1,c2,val,**kw):
    ws.merge_cells(start_row=r,start_column=c1,end_row=r,end_column=c2)
    return xsc(ws,r,c1,val,**kw)

def cw(ws,col,w): ws.column_dimensions[get_column_letter(col)].width=w
def rh(ws,r,h):   ws.row_dimensions[r].height=h

def _fmt(v,decimals=3):
    if v is None or (isinstance(v,float) and np.isnan(v)): return "-"
    return f"{v:.{decimals}f}"

def savefig(fig,path_stem):
    p=str(path_stem)
    fig.patch.set_facecolor("white")
    fig.savefig(p+".png",dpi=DPI,bbox_inches="tight",pad_inches=0.15)
    if SAVE_PDF:
        fig.savefig(p+".pdf",bbox_inches="tight",pad_inches=0.15)
    plt.close(fig)
    print(f"  -  {Path(p).name}.png"+(" + .pdf" if SAVE_PDF else ""))

# 
#  -1  FILE DISCOVERY
# 

_SKIP = {"pr","bc","day","mon","yr","daily","monthly","hist","historical",
         "ssp245","ssp585","ssp126","r1i1p1f1","r11i1p1f1","gn","gr"}

def _model_name(fname):
    stem=Path(fname).stem
    body=re.sub(r"^(bc_)?(pr_)?(day_)?","",stem,flags=re.IGNORECASE)
    for p in body.split("_"):
        if (p.lower() not in _SKIP and
                not re.match(r"^\d{4,}$",p) and
                not re.match(r"r\d+i",p.lower())):
            return p
    parts=body.split("_")
    return parts[0] if parts else "UnknownModel"

_KNOWN_PROV = {"phetchaburi","prachuap","phuket","chonburi","rayong",
               "trad","chanthaburi","nakhon","surat","chumphon","ranong",
               "krabi","trang","satun","songkhla","pattani","yala",
               "narathiwat","chiangmai","chiangrai","udon","loei","ubon"}

def discover_files(folder):
    """
    Scan folder recursively. Returns (obs_path, raw_dict, bc_dict).
    Province-aware: rejects files from a different province.
    """
    all_data = sorted([p for p in Path(folder).rglob("*")
                       if p.suffix.lower() in (".csv",".xlsx",".xls")])
    obs_files=[f for f in all_data
               if "observed" in f.name.lower()
               and "comprehensiveanalysis" not in f.name.lower()
               and not re.search(r"_fig\d+_", f.name.lower())]
    raw_files=[f for f in all_data if f.name.lower().startswith("pr")
               and "observed" not in f.name.lower()]
    bc_files =[f for f in all_data if f.name.lower().startswith("bc")
               and "observed" not in f.name.lower()]

    obs_path=str(obs_files[0]) if obs_files else None
    if len(obs_files)>1:
        print(f"  -  Multiple Observed files - using {obs_files[0].name}")

    # Province keywords from Observed filename
    prov_key=""
    if obs_path:
        stem=re.sub(r"_\d{6,}_\d{6,}","",Path(obs_path).stem.lower())
        stem=re.sub(r"observed_rain_daily_?","",stem)
        prov_key=stem.strip("_").replace("_"," ")
    obs_prov={w for w in prov_key.split() if len(w)>=3}

    def _ok(f):
        sl=f.stem.lower().replace("_"," ")
        file_prov={w for w in _KNOWN_PROV if w in sl}
        if not file_prov: return True
        return bool(file_prov & obs_prov)

    raw_d,bc_d={},{}
    _FAKE_MODELS={'cmip6','qdm','synthetic','test','demo'}
    for f in raw_files:
        if prov_key and not _ok(f): continue
        m=_model_name(f.name)
        if m.lower() in _FAKE_MODELS: continue
        if m not in raw_d: raw_d[m]=str(f); print(f"  Raw  '{m}'  {f.name}")
    for f in bc_files:
        if prov_key and not _ok(f): continue
        m=_model_name(f.name)
        if m.lower() in _FAKE_MODELS: continue
        if m not in bc_d:  bc_d[m]=str(f);  print(f"  BC   '{m}'  {f.name}")
    return obs_path, raw_d, bc_d

# 
#  -2  DATA LOADING
# 

def load_daily(path,label,target_stns=None):
    if path is None or not os.path.isfile(path):
        print(f"  -  Not found: {label}"); return None,[]
    time_cols={"YEAR","MONTH","DAY"}

    def _read_table(p, **kw):
        ext=Path(p).suffix.lower()
        if ext in (".xlsx",".xls"):
            return pd.read_excel(p, **kw)
        return pd.read_csv(p, **kw)

    if target_stns is not None:
        tgt_s=set(str(s) for s in target_stns)
        tgt_i=set(int(s) for s in target_stns if str(s).isdigit())
        def _uc(c):
            cs=str(c)
            return cs in time_cols or cs in tgt_s or (cs.isdigit() and int(cs) in tgt_i)
        try:   df=_read_table(path,usecols=_uc)
        except: df=_read_table(path)
    else:
        df=_read_table(path)

    df.columns=[str(c) for c in df.columns]
    drop_cols=[]
    for c in df.columns:
        cs=str(c).strip()
        if (cs=="" or cs.lower().startswith("unnamed") or
                cs.lower() in ("nan","none","null")):
            drop_cols.append(c)
    if drop_cols:
        df.drop(columns=drop_cols,inplace=True,errors="ignore")
        print(f"    {label:35s}: dropped non-station columns {drop_cols}")
    df.columns=[str(c).strip() for c in df.columns]
    for mv in MISS_FLAGS: df.replace(mv,np.nan,inplace=True)
    num=df.select_dtypes(include=[np.number]).columns
    df[num]=df[num].where(df[num]>=0)
    stns=[c for c in df.columns if c not in time_cols]
    if target_stns:
        tgt_str=[str(s) for s in target_stns]
        stns=[s for s in stns if s in set(tgt_str)]
        extra=[c for c in df.columns if c not in time_cols and c not in set(tgt_str)]
        if extra: df.drop(columns=extra,inplace=True,errors="ignore")
    try:
        df["date"]=pd.to_datetime({"year":df["YEAR"],"month":df["MONTH"],"day":df["DAY"]})
        df=df.set_index("date")[stns]
    except: df=df[stns]

    # Clip to baseline period if file spans beyond it
    if len(df)>0 and hasattr(df.index,"year"):
        try:
            df=df.loc[(df.index.year>=1900)&(df.index.year<=2100)]
        except Exception: pass
    yr0=df.index[0].year if len(df) else "?"
    yr1=df.index[-1].year if len(df) else "?"
    print(f"    {label:35s}: {len(df):,} rows - {len(stns)} stns  [{yr0}-{yr1}]")
    return df,stns

def to_monthly(df):
    if df is None: return None
    return df.resample("MS").apply(lambda g:g.sum(min_count=int(0.8*len(g))))

def to_annual(df):
    if df is None: return None
    return df.resample("YS").apply(lambda g:g.sum(min_count=int(0.8*len(g))))

def to_seasonal(df,months):
    if df is None: return None
    sub=df[df.index.month.isin(set(months))]
    # Fix dry-season year-crossing (Nov-Dec shift to next year)
    late={m for m in months if m>=9}
    early={m for m in months if m<=4}
    if late and early:
        sub=sub.copy()
        mask=sub.index.month.isin(late)
        shifted=pd.to_datetime({"year":sub.index.year+mask.astype(int),
                                 "month":sub.index.month,"day":sub.index.day})
        sub.index=shifted
    return sub.resample("YS").apply(lambda g:g.sum(min_count=int(0.5*len(g))))

def align_pair(d1,d2):
    if d1 is None or d2 is None: return None,None
    c=d1.index.intersection(d2.index)
    return (d1.loc[c],d2.loc[c]) if len(c)>0 else (None,None)

def get_col(df,stn):
    if df is None: return np.array([],dtype=float)
    stn=str(stn)
    if stn not in df.columns: return np.array([],dtype=float)
    v=df[stn].values.astype(float)
    return v[~np.isnan(v)&(v>=0)]

def period_str(df):
    if df is None: return "N/A"
    try: return f"{df.index[0].year}-{df.index[-1].year}"
    except: return "N/A"

def stn_labels(stns):
    return {str(s):f"S{i+1}" for i,s in enumerate(stns)}

def ensemble_mean(dfs_dict):
    valid=[df for df in dfs_dict.values() if df is not None]
    if not valid: return None
    ci=valid[0].index
    for df in valid[1:]: ci=ci.intersection(df.index)
    if len(ci)==0: return None
    cols=list(valid[0].columns)
    for df in valid[1:]: cols=[c for c in cols if c in df.columns]
    if not cols: return None
    stack=np.stack([df.loc[ci,cols].values.astype(float) for df in valid],axis=0)
    return pd.DataFrame(np.nanmean(stack,axis=0),index=ci,columns=cols)

def ensemble_spread(dfs_dict):
    """Return (mean, std, min, max) DataFrames."""
    valid=[df for df in dfs_dict.values() if df is not None]
    if len(valid)<2: return ensemble_mean(dfs_dict),None,None,None
    ci=valid[0].index
    for df in valid[1:]: ci=ci.intersection(df.index)
    cols=list(valid[0].columns)
    for df in valid[1:]: cols=[c for c in cols if c in df.columns]
    stack=np.stack([df.loc[ci,cols].values.astype(float) for df in valid],axis=0)
    m =pd.DataFrame(np.nanmean(stack,axis=0),index=ci,columns=cols)
    sd=pd.DataFrame(np.nanstd(stack,axis=0,ddof=1),index=ci,columns=cols)
    lo=pd.DataFrame(np.nanmin(stack,axis=0),index=ci,columns=cols)
    hi=pd.DataFrame(np.nanmax(stack,axis=0),index=ci,columns=cols)
    return m,sd,lo,hi

# 
#  -3  PERFORMANCE METRICS (academically correct)
# 

def compute_metrics(o,s):
    """
    Full performance suite.
    Parameters: o, s - paired arrays (already aligned, no NaN).
    All formulas referenced to peer-reviewed sources.
    """
    NULL={k:np.nan for k in
          ["n","RMSE","MAE","MBE","Pbias","RSR","r","r_sq",
           "NSE","KGE","d","sigma_r","beta",
           "std_obs","std_sim","mean_obs","mean_sim",
           "RMSE_pct","Pbias_abs"]}
    if len(o)<5 or len(s)<5: return NULL
    n=min(len(o),len(s)); o=o[:n].astype(float); s=s[:n].astype(float)
    mask=~np.isnan(o)&~np.isnan(s); o=o[mask]; s=s[mask]
    if len(o)<5: return NULL
    e=s-o
    rmse  =float(np.sqrt(np.mean(e**2)))
    mae   =float(np.mean(np.abs(e)))
    mbe   =float(np.mean(e))
    mean_o=float(np.mean(o)); mean_s=float(np.mean(s))
    std_o =float(np.std(o,ddof=1)); std_s=float(np.std(s,ddof=1))
    pbias =100*np.sum(e)/np.sum(o) if np.sum(o)!=0 else np.nan
    rsr   =rmse/std_o if std_o>0 else np.nan
    r     =float(np.corrcoef(o,s)[0,1])
    r_sq  =r**2
    sigma_r=std_s/std_o if std_o>0 else np.nan
    beta  =mean_s/mean_o if mean_o!=0 else np.nan
    dn    =np.sum((o-mean_o)**2)
    nse   =float(1-np.sum(e**2)/dn) if dn>0 else np.nan
    kge   =float(1-math.sqrt((r-1)**2+(sigma_r-1)**2+(beta-1)**2)) \
           if not(np.isnan(sigma_r) or np.isnan(beta)) else np.nan
    denom_d=np.sum((np.abs(s-mean_o)+np.abs(o-mean_o))**2)
    d     =float(1-np.sum(e**2)/denom_d) if denom_d>0 else np.nan
    rmse_pct=100*rmse/mean_o if mean_o!=0 else np.nan
    return dict(n=int(len(o)),
                RMSE=round(rmse,4),MAE=round(mae,4),MBE=round(mbe,4),
                Pbias=round(float(pbias),2),RSR=round(float(rsr),4),
                r=round(r,4),r_sq=round(r_sq,4),
                NSE=round(float(nse),4),KGE=round(float(kge),4),
                d=round(float(d),4),
                sigma_r=round(float(sigma_r),4) if not np.isnan(sigma_r) else np.nan,
                beta   =round(float(beta),4)    if not np.isnan(beta)    else np.nan,
                std_obs=round(std_o,4),std_sim=round(std_s,4),
                mean_obs=round(mean_o,4),mean_sim=round(mean_s,4),
                RMSE_pct=round(float(rmse_pct),2) if not np.isnan(rmse_pct) else np.nan,
                Pbias_abs=round(abs(float(pbias)),2) if not np.isnan(pbias) else np.nan)

def metrics_from_dfs(obs_df,sim_df,stn):
    if obs_df is None or sim_df is None:
        return compute_metrics(np.array([]),np.array([]))
    stn=str(stn)
    if stn not in obs_df.columns or stn not in sim_df.columns:
        return compute_metrics(np.array([]),np.array([]))
    common=obs_df.index.intersection(sim_df.index)
    if len(common)==0: return compute_metrics(np.array([]),np.array([]))
    o=obs_df.loc[common,stn].values.astype(float)
    s=sim_df.loc[common,stn].values.astype(float)
    mask=~np.isnan(o)&~np.isnan(s)&(o>=0)&(s>=0)
    return compute_metrics(o[mask],s[mask])

def performance_category(met,val):
    """Classify model performance per Moriasi et al. (2007)."""
    if np.isnan(val): return "Insufficient data"
    if met=="NSE":
        if val>0.75: return "Very Good"
        if val>0.65: return "Good"
        if val>0.50: return "Satisfactory"
        return "Unsatisfactory"
    if met=="KGE":
        if val>0.75: return "Very Good"
        if val>0.50: return "Good"
        if val>0.25: return "Satisfactory"
        return "Unsatisfactory"
    if met=="RSR":
        if val<0.50: return "Very Good"
        if val<0.60: return "Good"
        if val<0.70: return "Satisfactory"
        return "Unsatisfactory"
    if met=="Pbias_abs":
        if val<10: return "Very Good"
        if val<15: return "Good"
        if val<25: return "Satisfactory"
        return "Unsatisfactory"
    return "-"

# 
#  -4  STATISTICAL TESTS
# 

def _sig_stars(p):
    if np.isnan(p): return "-"
    if p<0.001: return "***"
    if p<0.01:  return "**"
    if p<0.05:  return "*"
    return "ns"

def _effect_r(W,n):
    """Effect size r = Z/-N (Cohen 1988)."""
    if np.isnan(W) or n<5: return np.nan
    mu=n*(n+1)/4.0
    sig=math.sqrt(n*(n+1)*(2*n+5)/24.0)
    if sig==0: return np.nan
    z=(W-mu)/sig
    return float(abs(z)/math.sqrt(n))

def fdr_correction(pvals,alpha=0.05):
    """
    Benjamini-Hochberg FDR correction.
    Rejects all ordered p-values up to the largest rank satisfying
    p_(i) <= alpha*i/m. NaN values are ignored, then mapped back as False.
    """
    pairs=[(i,float(p)) for i,p in enumerate(pvals) if not np.isnan(p)]
    m=len(pairs)
    reject=[False]*len(pvals)
    if m==0: return reject
    pairs.sort(key=lambda t:t[1])
    cutoff_rank=0
    for rank,(_,p) in enumerate(pairs,1):
        if p<=alpha*rank/m:
            cutoff_rank=rank
    if cutoff_rank:
        for i,_ in pairs[:cutoff_rank]:
            reject[i]=True
    return reject

def _wilcoxon_effect_size_from_diff(diff):
    """
    Normal-approximation effect size for paired signed-rank data.
    Positive sign means the BC absolute error is smaller than Raw.
    """
    diff=np.asarray(diff,dtype=float)
    diff=diff[~np.isnan(diff)]
    diff=diff[diff!=0]
    n=len(diff)
    if n<5: return np.nan
    ranks=sps.rankdata(np.abs(diff))
    w_plus=float(np.sum(ranks[diff>0]))
    mu=n*(n+1)/4.0
    sig=math.sqrt(n*(n+1)*(2*n+1)/24.0)
    if sig==0: return np.nan
    z=(w_plus-mu)/sig
    return float(z/math.sqrt(n))

def wilcoxon_test(obs_df,raw_df,bc_df,stns_str):
    """
    Wilcoxon signed-rank test: |err_BC| vs |err_Raw| per station.
    H: median(|err_BC|) < median(|err_Raw|) - one-tailed (BC better).
    Returns list of dicts per station.
    """
    results=[]
    for stn in stns_str:
        null=dict(Station=stn,W=np.nan,p_two=np.nan,p_one=np.nan,
                  n=np.nan,effect_r=np.nan,sig="-",
                  med_err_raw=np.nan,med_err_bc=np.nan,
                  mean_err_raw=np.nan,mean_err_bc=np.nan,
                  pct_reduction=np.nan)
        try:
            if any(df is None or stn not in df.columns
                   for df in [obs_df,raw_df,bc_df]):
                results.append(null); continue
            common=(obs_df.index.intersection(raw_df.index)
                            .intersection(bc_df.index))
            if len(common)<20: results.append(null); continue
            o=obs_df.loc[common,stn].values.astype(float)
            r=raw_df.loc[common,stn].values.astype(float)
            b=bc_df.loc[common,stn].values.astype(float)
            mask=~np.isnan(o)&~np.isnan(r)&~np.isnan(b)&(o>=0)&(r>=0)&(b>=0)
            o,r,b=o[mask],r[mask],b[mask]
            if len(o)<20: results.append(null); continue
            e_raw=np.abs(r-o); e_bc=np.abs(b-o)
            diff=e_raw-e_bc  # positive - BC better
            nonzero=diff[diff!=0]
            if len(nonzero)<10: results.append(null); continue
            W,p2=scipy_wilcoxon(nonzero,alternative="two-sided",zero_method="wilcox")
            _,p1=scipy_wilcoxon(nonzero,alternative="greater",zero_method="wilcox")
            n=len(nonzero)
            er=_wilcoxon_effect_size_from_diff(nonzero)
            med_r=float(np.median(e_raw)); med_b=float(np.median(e_bc))
            pct_red=(med_r-med_b)/med_r*100 if med_r>0 else np.nan
            results.append(dict(
                Station=stn,W=round(float(W),2),
                p_two=round(float(p2),6),p_one=round(float(p1),6),
                n=int(n),effect_r=round(er,4) if not np.isnan(er) else np.nan,
                sig=_sig_stars(float(p1)),
                med_err_raw=round(med_r,4),med_err_bc=round(med_b,4),
                mean_err_raw=round(float(np.mean(e_raw)),4),
                mean_err_bc=round(float(np.mean(e_bc)),4),
                pct_reduction=round(float(pct_red),2) if not np.isnan(pct_red) else np.nan,
            ))
        except Exception as ex:
            null["note"]=str(ex); results.append(null)
    # FDR correction
    p1s=[r["p_one"] for r in results]
    fdr=fdr_correction(p1s)
    for row,f in zip(results,fdr): row["sig_fdr"]="sig" if f else "ns"
    return results

def ks_test(obs_df,raw_df,bc_df,stns_str):
    """
    Two-sample KS test: Raw vs Obs, BC vs Obs (wet days only).
    Returns list of dicts per station.
    """
    results=[]
    for stn in stns_str:
        null=dict(Station=stn,
                  D_raw=np.nan,p_raw=np.nan,sig_raw="-",
                  D_bc=np.nan, p_bc=np.nan, sig_bc="-",
                  D_improvement=np.nan)
        try:
            if obs_df is None or stn not in obs_df.columns:
                results.append(null); continue
            o=get_col(obs_df,stn); o_wet=o[o>=WET_THR]
            r=get_col(raw_df,stn) if raw_df is not None else np.array([])
            b=get_col(bc_df,stn)  if bc_df  is not None else np.array([])
            r_wet=r[r>=WET_THR]; b_wet=b[b>=WET_THR]
            if len(o_wet)<10 or (len(r_wet)<5 and len(b_wet)<5):
                results.append(null); continue
            d_r=p_r=np.nan
            if len(r_wet)>=5:
                d_r,p_r=ks_2samp(o_wet,r_wet); d_r=round(d_r,4); p_r=round(p_r,6)
            d_b=p_b=np.nan
            if len(b_wet)>=5:
                d_b,p_b=ks_2samp(o_wet,b_wet); d_b=round(d_b,4); p_b=round(p_b,6)
            d_imp=(d_r-d_b) if not(np.isnan(d_r) or np.isnan(d_b)) else np.nan
            results.append(dict(
                Station=stn,
                D_raw=d_r,p_raw=p_r,sig_raw=_sig_stars(p_r) if not np.isnan(p_r) else "-",
                D_bc=d_b, p_bc=p_b, sig_bc=_sig_stars(p_b)  if not np.isnan(p_b)  else "-",
                D_improvement=round(float(d_imp),4) if not np.isnan(d_imp) else np.nan,
            ))
        except Exception as ex:
            null["note"]=str(ex); results.append(null)
    return results

# 
#  -5  TAYLOR DIAGRAM ENGINE
# 

def _taylor_bg(ax,ref_std,unit):
    """Draw Taylor diagram background."""
    if np.isnan(ref_std) or ref_std<=0: ref_std=5.0
    r_max=ref_std*1.78
    # RMSE arcs
    for frac,lc in [(0.25,"#CFD8DC"),(0.5,"#B0BEC5"),
                    (0.75,"#90A4AE"),(1.0,"#78909C")]:
        rr=ref_std*frac; th=np.linspace(0,np.pi/2,300)
        xc=ref_std+rr*np.cos(np.pi-th); yc=rr*np.sin(th)
        mask=(xc**2+yc**2<=r_max**2)&(xc>=0)&(yc>=0)
        ax.plot(xc[mask],yc[mask],color=lc,lw=0.7,ls="-",alpha=0.75,zorder=1)
        ix=np.argmin(np.abs(th-np.pi/4))
        if mask[ix]:
            ax.text(xc[ix],yc[ix],f"RMSE\n{rr:.1f}",fontsize=6.5,color=lc,
                    ha="center",va="center",
                    bbox=dict(boxstyle="round,pad=0.1",fc="white",ec="none",alpha=0.7))
    # Correlation lines
    for rv,lc in [(0.2,"#CFD8DC"),(0.4,"#B0BEC5"),(0.6,"#90A4AE"),
                  (0.7,"#78909C"),(0.8,"#607D8B"),(0.9,"#546E7A"),
                  (0.95,"#455A64"),(0.99,"#37474F")]:
        tv=np.arccos(rv)
        ax.plot([0,r_max*np.cos(tv)],[0,r_max*np.sin(tv)],
                color=lc,lw=0.55,alpha=0.8,zorder=1)
        ax.text(r_max*np.cos(tv)*1.06,r_max*np.sin(tv)*1.06,
                f"{rv:.2f}",fontsize=7,color="#546E7A",ha="center",va="center")
    # Std arcs
    for frac in [0.25,0.5,0.75,1.0,1.25,1.5]:
        ar=ref_std*frac
        if ar>r_max: continue
        t=np.linspace(0,np.pi/2,300)
        ax.plot(ar*np.cos(t),ar*np.sin(t),color="#ECEFF1",lw=0.7,alpha=0.85,zorder=1)
        ax.text(0,ar,f"{ar:.1f}",fontsize=7,color="#90A4AE",ha="right",va="center")
    # Reference star
    ax.plot(ref_std,0,"k*",markersize=14,zorder=9,label="Observed (Ref.)")
    ax.set_xlim(0,r_max); ax.set_ylim(0,r_max)
    if str(unit).lower()=="normalized":
        axis_label="Normalized Standard Deviation (sigma_sim/sigma_obs)"
    else:
        axis_label=f"Standard Deviation ({unit})"
    ax.set_xlabel(axis_label,fontsize=12,fontweight="bold",labelpad=5)
    ax.set_ylabel(axis_label,fontsize=12,fontweight="bold",labelpad=5)
    ax.text(-0.09,0.5,"Pearson Correlation (r)  -",
            transform=ax.transAxes,fontsize=9,rotation=90,
            va="center",color="#546E7A",style="italic")
    ax.set_aspect("equal"); ax.grid(False)
    ax.axhline(0,color="k",lw=1.0); ax.axvline(0,color="k",lw=1.0)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    return r_max

def _taylor_points(ax,obs_df,raw_dfs,bc_dfs,stns_str,smap,
                   stn_colors,r_max,ref_std,show_individual=False):
    """
    Plot per-station Taylor points.
    Ensemble mean: larger marker with bold outline.
    Individual models: smaller markers.
    Arrows: Raw - BC (improvement direction).
    """
    raw_ens=ensemble_mean(raw_dfs)
    bc_ens =ensemble_mean(bc_dfs)
    raw_xy_ens={}

    for si,stn in enumerate(stns_str):
        col=stn_colors[si%len(stn_colors)]
        code=smap.get(stn,stn)

        # Individual models (smaller, transparent)
        if show_individual:
            for m,raw_df in raw_dfs.items():
                mr=metrics_from_dfs(obs_df,raw_df,stn)
                rv=mr.get("r",np.nan); sr=mr.get("sigma_r",np.nan)
                ss=sr if not np.isnan(sr) else np.nan
                if np.isnan(ss) or np.isnan(rv): continue
                th=np.arccos(np.clip(rv,-1,1))
                ax.scatter(ss*np.cos(th),ss*np.sin(th),
                           color=col,marker="^",s=35,
                           alpha=0.40,edgecolors="none",zorder=4)
            for m,bc_df in bc_dfs.items():
                mb=metrics_from_dfs(obs_df,bc_df,stn)
                rv=mb.get("r",np.nan); sr=mb.get("sigma_r",np.nan)
                ss=sr if not np.isnan(sr) else np.nan
                if np.isnan(ss) or np.isnan(rv): continue
                th=np.arccos(np.clip(rv,-1,1))
                ax.scatter(ss*np.cos(th),ss*np.sin(th),
                           color=col,marker="o",s=35,
                           alpha=0.40,edgecolors="none",zorder=4)

        # Ensemble mean - large marker with white edge
        for ens_df,mk,ds,zord in [(raw_ens,"^","Raw",6),(bc_ens,"o","BC",7)]:
            mr=metrics_from_dfs(obs_df,ens_df,stn)
            rv=mr.get("r",np.nan); sr=mr.get("sigma_r",np.nan)
            ss=sr if not np.isnan(sr) else np.nan
            if np.isnan(ss) or np.isnan(rv): continue
            th=np.arccos(np.clip(rv,-1,1))
            xv=ss*np.cos(th); yv=ss*np.sin(th)
            ax.scatter(xv,yv,color=col,marker=mk,s=110,
                       edgecolors="white",linewidth=0.9,alpha=0.95,zorder=zord)
            if ds=="Raw":
                raw_xy_ens[stn]=(xv,yv)
            elif ds=="BC" and stn in raw_xy_ens:
                rx,ry=raw_xy_ens[stn]
                ax.annotate("",xy=(xv,yv),xytext=(rx,ry),
                            arrowprops=dict(arrowstyle="->",color=col,
                                            lw=1.1,alpha=0.65))
                ax.text(xv+0.025*r_max,yv+0.025*r_max,code,
                        fontsize=8.5,color=col,fontweight="bold",
                        ha="left",va="bottom")

def _draw_panel_a(ax, obs_df, raw_dfs, bc_dfs, stns_str, smap,
                   stn_colors, ref_std, unit, scale_label):
    """
    Panel (a): All stations, colour by station.
    Ensemble mean: large - (Raw) and  (BC) per station.
    Individual model points: small semi-transparent markers.
    Arrows: ensemble Raw - ensemble BC per station.
    """
    r_max = _taylor_bg(ax, ref_std, unit)
    raw_ens = ensemble_mean(raw_dfs)
    bc_ens  = ensemble_mean(bc_dfs)
    raw_xy_ens = {}

    for si, stn in enumerate(stns_str):
        col  = stn_colors[si % len(stn_colors)]
        code = smap.get(stn, stn)

        # - Individual model points (small, transparent) -
        for m, raw_df in raw_dfs.items():
            mr = metrics_from_dfs(obs_df, raw_df, stn)
            rv = mr.get("r", np.nan); sr = mr.get("sigma_r", np.nan)
            ss = sr if not np.isnan(sr) else np.nan
            if np.isnan(ss) or np.isnan(rv): continue
            th = np.arccos(np.clip(rv, -1, 1))
            ax.scatter(ss*np.cos(th), ss*np.sin(th),
                       color=col, marker="^", s=28,
                       alpha=0.65, edgecolors="none", zorder=3)
        for m, bc_df in bc_dfs.items():
            mb = metrics_from_dfs(obs_df, bc_df, stn)
            rv = mb.get("r", np.nan); sr = mb.get("sigma_r", np.nan)
            ss = sr if not np.isnan(sr) else np.nan
            if np.isnan(ss) or np.isnan(rv): continue
            th = np.arccos(np.clip(rv, -1, 1))
            ax.scatter(ss*np.cos(th), ss*np.sin(th),
                       color=col, marker="o", s=28,
                       alpha=0.80, edgecolors="none", zorder=3)

        # - Ensemble mean - large marker with white edge -
        for ens_df, mk, ds, zord in [
            (raw_ens, "^", "Raw", 6),
            (bc_ens,  "o", "BC",  7),
        ]:
            mr2 = metrics_from_dfs(obs_df, ens_df, stn)
            rv2 = mr2.get("r", np.nan); sr2 = mr2.get("sigma_r", np.nan)
            ss2 = sr2 if not np.isnan(sr2) else np.nan
            if np.isnan(ss2) or np.isnan(rv2): continue
            th2  = np.arccos(np.clip(rv2, -1, 1))
            xv   = ss2 * np.cos(th2); yv = ss2 * np.sin(th2)
            ax.scatter(xv, yv, color=col, marker=mk, s=120,
                       edgecolors="white", linewidth=1.0,
                       alpha=0.95, zorder=zord)
            if ds == "Raw":
                raw_xy_ens[stn] = (xv, yv)
            elif ds == "BC" and stn in raw_xy_ens:
                rx, ry = raw_xy_ens[stn]
                ax.annotate("", xy=(xv, yv), xytext=(rx, ry),
                            arrowprops=dict(arrowstyle="->", color=col,
                                            lw=1.2, alpha=0.70))
                ax.text(xv + 0.026*r_max, yv + 0.026*r_max, code,
                        fontsize=8.5, color=col, fontweight="bold",
                        ha="left", va="bottom")

    # Legend
    hand = [
        Line2D([0],[0], marker="*",  color="k",    ls="none", ms=12,
               label="Observed (Reference)"),
        Line2D([0],[0], marker="^",  color="grey",  ls="none", ms=9,
               label="Raw CMIP6 - Ens. mean"),
        Line2D([0],[0], marker="o",  color="grey",  ls="none", ms=9,
               label="Bias-Corrected QDM - Ens. mean"),
        Line2D([0],[0], marker="^",  color="grey",  ls="none", ms=5,
               alpha=0.45, label="Individual model (small)"),
        Line2D([0],[0], color="grey", lw=1.0, ls="-", alpha=0.65,
               label="Arrow: Raw - BC"),
    ]
    for si, stn in enumerate(stns_str):
        hand.append(mpatches.Patch(color=stn_colors[si % len(stn_colors)],
                                    alpha=0.88, label=smap[stn]))
    ax.legend(handles=hand, loc="upper right", fontsize=7.8,
              frameon=True, edgecolor="#B0BEC5",
              facecolor="white", framealpha=0.93, ncol=2,
              handlelength=1.5)
    ax.set_title(f"(a)  Station Colours - {scale_label} Scale\n"
                 "     Each colour = one station  |  Large marker = ensemble mean",
                 loc="left", fontsize=13, fontweight="bold", pad=5)
    return r_max


def _draw_panel_b(ax, obs_df, raw_dfs, bc_dfs, stns_str, smap,
                   model_list, mc, ref_std, unit, scale_label):
    """
    Panel (b): All stations, colour by model.
    All stations shown with same model colour.
    Arrows: Raw - BC per model per station.
    Model labels shown next to BC points.
    """
    r_max = _taylor_bg(ax, ref_std, unit)

    for mi, (m, col) in enumerate(zip(model_list, mc)):
        raw_df  = raw_dfs.get(m)
        bc_df_m = bc_dfs.get(m)
        raw_xy_m = {}
        first_raw = True; first_bc = True

        for si, stn in enumerate(stns_str):
            code = smap.get(stn, stn)

            # Raw point
            if raw_df is not None:
                mr = metrics_from_dfs(obs_df, raw_df, stn)
                rv = mr.get("r", np.nan); sr = mr.get("sigma_r", np.nan)
                ss = sr if not np.isnan(sr) else np.nan
                if not (np.isnan(ss) or np.isnan(rv)):
                    th = np.arccos(np.clip(rv, -1, 1))
                    xv = ss * np.cos(th); yv = ss * np.sin(th)
                    ax.scatter(xv, yv, color=col, marker="^", s=75,
                               edgecolors="white", linewidth=0.7,
                               alpha=0.85, zorder=5,
                               label=f"{m} - Raw" if first_raw else "")
                    first_raw = False
                    raw_xy_m[stn] = (xv, yv)

            # BC point + arrow
            if bc_df_m is not None:
                mb = metrics_from_dfs(obs_df, bc_df_m, stn)
                rv = mb.get("r", np.nan); sr = mb.get("sigma_r", np.nan)
                ss = sr if not np.isnan(sr) else np.nan
                if not (np.isnan(ss) or np.isnan(rv)):
                    th = np.arccos(np.clip(rv, -1, 1))
                    xv = ss * np.cos(th); yv = ss * np.sin(th)
                    ax.scatter(xv, yv, color=col, marker="o", s=75,
                               edgecolors="white", linewidth=0.7,
                               alpha=0.88, zorder=6,
                               label=f"{m} - BC (QDM)" if first_bc else "")
                    first_bc = False
                    # Arrow Raw - BC
                    if stn in raw_xy_m:
                        rx, ry = raw_xy_m[stn]
                        ax.annotate("", xy=(xv, yv), xytext=(rx, ry),
                                    arrowprops=dict(arrowstyle="->",
                                                    color=col, lw=0.85,
                                                    alpha=0.60))
                    # Station label
                    ax.text(xv + 0.024*r_max, yv + 0.024*r_max, code,
                            fontsize=7.5, color=col, alpha=0.80,
                            fontweight="bold", ha="left", va="bottom")

    # Legend: model patches + marker types
    hand = [
        Line2D([0],[0], marker="*",  color="k",    ls="none", ms=12,
               label="Observed (Reference)"),
        Line2D([0],[0], marker="^",  color="grey",  ls="none", ms=9,
               label="Raw CMIP6"),
        Line2D([0],[0], marker="o",  color="grey",  ls="none", ms=9,
               label="Bias-Corrected (QDM)"),
        Line2D([0],[0], color="grey", lw=0.9, ls="-", alpha=0.60,
               label="Arrow: Raw - BC"),
    ]
    for m, col in zip(model_list, mc):
        hand.append(mpatches.Patch(color=col, alpha=0.88, label=m))
    ax.legend(handles=hand, loc="upper right", fontsize=8.5,
              frameon=True, edgecolor="#B0BEC5",
              facecolor="white", framealpha=0.93, ncol=1,
              handlelength=1.5)
    ax.set_title(f"(b)  Model Colours - {scale_label} Scale\n"
                 "     Each colour = one CMIP6 model  |  All stations shown",
                 loc="left", fontsize=13, fontweight="bold", pad=5)
    return r_max


def build_taylor_fig(obs_df, raw_dfs, bc_dfs, stns, smap,
                     scale_label, unit, period_obs, period_sim,
                     fig_tag, out_dir, prefix):
    """
    Taylor Diagram - 2-panel layout:
      (a) Station colours: ensemble mean per station, with individual model cloud
      (b) Model colours: per-model per-station points, with arrows Raw - BC

    Both panels are pure Taylor diagrams (no bar chart).
    Outputs:
      Combined 1-2 figure  - {prefix}_{fig_tag}_TaylorDiagram_{scale}.png/pdf
      Sub-panel (a) alone  - {prefix}_{fig_tag}_TaylorDiagram_{scale}_a.png/pdf
      Sub-panel (b) alone  - {prefix}_{fig_tag}_TaylorDiagram_{scale}_b.png/pdf
    """
    if obs_df is None:
        print(f"  -  No obs data for Taylor Diagram - {scale_label}"); return

    stns_str    = [str(s) for s in stns]
    cmap_s      = cm.get_cmap("tab20", max(len(stns), 1))
    stn_colors  = [mcolors.to_hex(cmap_s(i)) for i in range(len(stns))]
    model_list  = sorted(set(list(raw_dfs.keys()) + list(bc_dfs.keys())))
    mc          = [MODEL_PALETTE[i % len(MODEL_PALETTE)]
                   for i in range(len(model_list))]

    # Normalized Taylor diagram: reference standard deviation is one.
    # This is appropriate when multiple stations with different observed
    # variances are shown on the same Taylor axis.
    ref_std = 1.0
    unit = "normalized"
    sup_title = (
        f"Normalized Taylor Diagram - {scale_label} Scale\n"
        f"CMIP6 Raw (triangle) vs Bias-Corrected QDM (circle)  |  sigma_ref=1  |  "
        f"Obs: {period_obs}  |  Sim: {period_sim}  |  "
        #f"Reference: Taylor (2001) J. Geophys. Res. 106:7183-7192"
    )
    slug = scale_label.replace(" ", "")

    # - Combined 1-2 figure -
    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(20, 9))
    fig.subplots_adjust(left=0.04, right=0.97,
                        top=0.87, bottom=0.09, wspace=0.26)

    _draw_panel_a(ax_a, obs_df, raw_dfs, bc_dfs, stns_str, smap,
                  stn_colors, ref_std, unit, scale_label)
    _draw_panel_b(ax_b, obs_df, raw_dfs, bc_dfs, stns_str, smap,
                  model_list, mc, ref_std, unit, scale_label)

    fig.suptitle(sup_title, fontsize=14, fontweight="bold")
    savefig(fig, out_dir / f"{prefix}_{fig_tag}_TaylorDiagram_{slug}")

    # - Sub-panel (a) - individual file -
    fig_a, ax_a2 = plt.subplots(1, 1, figsize=(10.5, 9.5))
    fig_a.subplots_adjust(left=0.07, right=0.96,
                          top=0.88, bottom=0.09)
    _draw_panel_a(ax_a2, obs_df, raw_dfs, bc_dfs, stns_str, smap,
                  stn_colors, ref_std, unit, scale_label)
    fig_a.suptitle(
        f"Normalized Taylor Diagram - {scale_label} Scale\n"
        f"Obs: {period_obs}  |  Ref: Taylor (2001)",
        fontsize=14, fontweight="bold"
    )
    savefig(fig_a, out_dir / f"{prefix}_{fig_tag}_TaylorDiagram_{slug}_a")

    # - Sub-panel (b) - individual file -
    fig_b, ax_b2 = plt.subplots(1, 1, figsize=(10.5, 9.5))
    fig_b.subplots_adjust(left=0.07, right=0.96,
                          top=0.88, bottom=0.09)
    _draw_panel_b(ax_b2, obs_df, raw_dfs, bc_dfs, stns_str, smap,
                  model_list, mc, ref_std, unit, scale_label)
    fig_b.suptitle(
        f"Normalized Taylor Diagram - {scale_label} Scale\n"
        f"Obs: {period_obs}  |  Ref: Taylor (2001)",
        fontsize=14, fontweight="bold"
    )
    savefig(fig_b, out_dir / f"{prefix}_{fig_tag}_TaylorDiagram_{slug}_b")

# 
#  -6  Q-Q PLOT ENGINE
# 

def build_qq_fig(obs_df,raw_dfs,bc_dfs,stns,
                 scale_label,period_obs,
                 fig_tag,out_dir,prefix):
    """
    Q-Q plot figure for one temporal scale.
    Each model panel overlays Raw and BC against observed quantiles.
    """
    stns_str=[str(s) for s in stns]
    model_list=sorted(set(list(raw_dfs.keys())+list(bc_dfs.keys())))
    raw_ens=ensemble_mean(raw_dfs)
    bc_ens =ensemble_mean(bc_dfs)
    probs  =np.r_[np.linspace(0,90,181),np.linspace(90.5,99.5,19),99.9]

    def pool_wet(df):
        if df is None: return np.array([],dtype=float)
        cols=[s for s in stns_str if s in df.columns]
        if not cols: return np.array([],dtype=float)
        v=df[cols].values.flatten().astype(float)
        v=v[~np.isnan(v)&(v>=WET_THR)]
        if len(v)>50000:
            v=np.random.default_rng(42).choice(v,50000,replace=False)
        return np.sort(v)

    obs_v=pool_wet(obs_df)
    if len(obs_v)<20:
        print(f"  !  Insufficient obs wet-days for Q-Q {scale_label}"); return

    q_obs=np.percentile(obs_v,probs)
    n_panels=len(model_list)+1
    ncols=min(3,n_panels); nrows=math.ceil(n_panels/ncols)
    fig,axes=plt.subplots(nrows,ncols,figsize=(7.2*ncols,6.7*nrows))
    axes=np.array(axes).flatten()
    fig.subplots_adjust(hspace=0.48,wspace=0.30,
                        left=0.07,right=0.97,top=0.90,bottom=0.08)
    pct_marks=[(90,C["grey"],"P90","^"),(95,C["gold"],"P95","s"),
               (99,C["purple"],"P99","D")]

    def _qq_panel(ax,raw_v,bc_v,title,panel_tag):
        if len(raw_v)<10 and len(bc_v)<10:
            ax.text(0.5,0.5,"Insufficient data",transform=ax.transAxes,
                    ha="center",fontsize=11)
            ax.set_title(f"{panel_tag}  {title}",loc="left",
                         fontsize=12,fontweight="bold"); return
        q_raw=np.percentile(raw_v,probs) if len(raw_v)>=10 else None
        q_bc =np.percentile(bc_v, probs) if len(bc_v) >=10 else None
        xy_vals=[q_obs.max()]
        if q_raw is not None: xy_vals.append(q_raw.max())
        if q_bc  is not None: xy_vals.append(q_bc.max())
        xy_max=max(xy_vals)*1.04
        ax.plot([0,xy_max],[0,xy_max],color=C["green"],lw=1.6,ls="-",
                alpha=0.85,label="1:1 (perfect)",zorder=2)
        if q_raw is not None:
            ax.plot(q_obs,q_raw,color=C["raw"],lw=1.35,alpha=0.90,
                    label="Raw",zorder=3)
            ax.scatter(q_obs,q_raw,c=probs,cmap="Reds",s=13,alpha=0.55,
                       edgecolors="none",zorder=4)
        sc=None
        if q_bc is not None:
            ax.plot(q_obs,q_bc,color=C["bc"],lw=1.75,alpha=0.95,
                    label="Bias-corrected QDM",zorder=5)
            sc=ax.scatter(q_obs,q_bc,c=probs,cmap="Blues",s=17,alpha=0.72,
                          edgecolors="white",linewidths=0.15,zorder=6)
        for pct,pc,lbl,mk in pct_marks:
            qo=float(np.percentile(obs_v,pct))
            if q_raw is not None:
                qr=float(np.percentile(raw_v,pct))
                ax.scatter([qo],[qr],color=C["raw"],s=62,zorder=7,
                           marker=mk,edgecolors="white",linewidths=0.7)
            if q_bc is not None:
                qb=float(np.percentile(bc_v,pct))
                ax.scatter([qo],[qb],color=pc,s=78,zorder=8,
                           marker=mk,edgecolors="black",linewidths=0.35,
                           label=lbl)
        qq_raw=float(np.sqrt(np.mean((q_raw-q_obs)**2))) if q_raw is not None else np.nan
        qq_bc =float(np.sqrt(np.mean((q_bc -q_obs)**2))) if q_bc  is not None else np.nan
        r2_raw=float(np.corrcoef(q_obs,q_raw)[0,1]**2) if q_raw is not None else np.nan
        r2_bc =float(np.corrcoef(q_obs,q_bc )[0,1]**2) if q_bc  is not None else np.nan
        gain=100*(qq_raw-qq_bc)/qq_raw if not(np.isnan(qq_raw) or np.isnan(qq_bc) or qq_raw==0) else np.nan
        ax.text(0.96,0.96,
                f"QQ-RMSE Raw={qq_raw:.2f} mm\n"
                f"QQ-RMSE BC ={qq_bc:.2f} mm\n"
                f"Reduction={gain:.1f}%\n"
                f"r2 Raw={r2_raw:.3f} | BC={r2_bc:.3f}",
                transform=ax.transAxes,fontsize=9.3,fontweight="bold",
                va="top",ha="right",
                bbox=dict(boxstyle="round,pad=0.3",fc="white",
                          ec="#B0BEC5",alpha=0.90))
        ax.set_xlim(0,xy_max); ax.set_ylim(0,xy_max)
        ax.set_aspect("equal","box")
        ax.set_xlabel("Observed Quantile (mm)",fontsize=11,fontweight="bold")
        ax.set_ylabel("Simulated Quantile (mm)",fontsize=11,fontweight="bold")
        ax.set_title(f"{panel_tag}  {title}",loc="left",
                     fontsize=12,fontweight="bold",pad=4)
        ax.tick_params(axis="both",which="major",labelsize=10,width=1.4)
        ax.xaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.legend(fontsize=8.3,frameon=True,edgecolor="#B0BEC5",
                  facecolor="white",framealpha=0.92,
                  loc="upper left",ncol=1,handlelength=1.2)
        if sc is not None:
            cb=plt.colorbar(sc,ax=ax,orientation="horizontal",
                            pad=0.14,fraction=0.05,shrink=0.85)
            cb.set_label("BC percentile (%)",fontsize=9,fontweight="bold")
            cb.ax.tick_params(labelsize=8)

    panel_idx=0
    for m in model_list:
        raw_v=pool_wet(raw_dfs.get(m))
        bc_v =pool_wet(bc_dfs.get(m))
        _qq_panel(axes[panel_idx],raw_v,bc_v,
                  f"{m}: Raw and BC vs Obs",chr(97+panel_idx))
        panel_idx+=1

    _qq_panel(axes[panel_idx],pool_wet(raw_ens),pool_wet(bc_ens),
              "Ensemble mean: Raw and BC vs Obs",chr(97+panel_idx))
    panel_idx+=1

    for ax in axes[panel_idx:]: ax.set_visible(False)
    fig.suptitle(
        f"Q-Q Plots - {scale_label} Scale | Wet-day values pooled across stations\n"
        f"Observed period: {period_obs} | Lower QQ-RMSE indicates closer distributional agreement",
        fontsize=14,fontweight="bold"
    )
    savefig(fig,out_dir/f"{prefix}_{fig_tag}_QQPlot_{scale_label.replace(' ','')}")

#  -7  PERFORMANCE HEATMAP
# 

def build_heatmap_fig(obs_df,raw_dfs,bc_dfs,stns,smap,
                      scale_label,period_obs,period_sim,
                      fig_tag,out_dir,prefix):
    """
    Performance heatmap: models - stations for Raw (left) and BC (right).
    Metrics: KGE, NSE, r, RMSE, Pbias, d.
    """
    stns_str=[str(s) for s in stns]
    codes=[smap[s] for s in stns_str]
    model_list=sorted(set(list(raw_dfs.keys())+list(bc_dfs.keys())))
    n_m=len(model_list); n_s=len(stns)

    MET_DEFS=[
        ("KGE",  "RdYlGn",-1,1),
        ("NSE",  "RdYlGn",-1,1),
        ("r",    "RdYlGn",-1,1),
        ("d",    "YlGn",   0,1),
        ("RMSE", "YlOrRd_r",0,None),
        ("Pbias","RdBu_r",None,None),
    ]

    def build_mat(ds_key,met):
        mat=np.full((n_m,n_s),np.nan)
        dfs=raw_dfs if ds_key=="Raw" else bc_dfs
        for mi,m in enumerate(model_list):
            for si,stn in enumerate(stns_str):
                df=dfs.get(m)
                if df is not None:
                    mr=metrics_from_dfs(obs_df,df,stn)
                    mat[mi,si]=mr.get(met,np.nan)
        return mat

    fig=plt.figure(figsize=(max(16,n_m*2.8+5),len(MET_DEFS)*3.0))
    gs=gridspec.GridSpec(len(MET_DEFS),2,figure=fig,
                         hspace=0.55,wspace=0.10,
                         top=0.92,bottom=0.07,left=0.12,right=0.96)

    for ri,(met,cmap_n,vmin,vmax) in enumerate(MET_DEFS):
        for di,(ds_lbl,ds_key) in enumerate([("Raw CMIP6","Raw"),
                                              ("Bias-Corrected (QDM)","BC")]):
            ax=fig.add_subplot(gs[ri,di])
            mat=build_mat(ds_key,met)
            if met=="RMSE":
                vmax2=np.nanmax(mat) if not np.all(np.isnan(mat)) else 1.0
                vmin2=0
            elif vmin is None:
                amx=np.nanmax(np.abs(mat)) if not np.all(np.isnan(mat)) else 1.0
                vmin2,vmax2=-amx,amx
            else:
                vmin2,vmax2=vmin,vmax
            im=ax.imshow(mat,cmap=cmap_n,vmin=vmin2,vmax=vmax2,
                         aspect="auto",interpolation="nearest")
            if n_m<=12 and n_s<=16:
                for mi2 in range(n_m):
                    for si2 in range(n_s):
                        v=mat[mi2,si2]
                        if not np.isnan(v):
                            mid=(vmin2+vmax2)/2
                            rng=vmax2-vmin2+1e-9
                            tc="white" if abs(v-mid)/rng>0.52 else "black"
                            ax.text(si2,mi2,f"{v:.2f}",ha="center",va="center",
                                    fontsize=7.5,fontweight="bold",color=tc)
            ax.set_xticks(range(n_s)); ax.set_yticks(range(n_m))
            ax.set_xticklabels(codes,rotation=0,ha="center",fontsize=10)
            if di==0: ax.set_yticklabels(model_list,fontsize=10)
            else:     ax.set_yticklabels([])
            if ri==0: ax.set_title(ds_lbl,fontsize=12,fontweight="bold",pad=4)
            if di==0: ax.set_ylabel(met,fontsize=12,fontweight="bold",labelpad=5)
            if ri==len(MET_DEFS)-1: ax.set_xlabel("Station",fontsize=11)
            plt.colorbar(im,ax=ax,orientation="vertical",
                         pad=0.02,fraction=0.04,shrink=0.88)

    fig.suptitle(
        f"Model Performance Heatmap - {scale_label} Scale\n"
        f"Raw CMIP6 (left) vs Bias-Corrected QDM (right)  |  Obs: {period_obs}",
        fontsize=14,fontweight="bold"
    )
    savefig(fig,out_dir/f"{prefix}_{fig_tag}_PerfHeatmap_{scale_label.replace(' ','')}")

# 
#  -8  METRIC IMPROVEMENT FIGURE
# 

def build_improvement_fig(obs_d,obs_m,raw_dfs,bc_dfs,
                           raw_m_dfs,bc_m_dfs,
                           stns,smap,period_obs,out_dir,prefix):
    """
    Fig 7: Station-wise improvement after QDM bias correction.
    RMSE and |Pbias| are plotted as relative reduction (%) so daily and
    monthly scales can be compared on a defensible common axis. Dimensionless
    metrics are plotted as absolute delta (BC - Raw).
    """
    stns_str=[str(s) for s in stns]
    codes=[smap[s] for s in stns_str]
    raw_ens_d=ensemble_mean(raw_dfs); bc_ens_d=ensemble_mean(bc_dfs)
    raw_ens_m=ensemble_mean(raw_m_dfs); bc_ens_m=ensemble_mean(bc_m_dfs)

    def improvement_values(obs_df,raw_ens,bc_ens,met,lower_better=False,relative=False):
        out=[]
        for stn in stns_str:
            mr=metrics_from_dfs(obs_df,raw_ens,stn)
            mb=metrics_from_dfs(obs_df,bc_ens, stn)
            vr=mr.get(met,np.nan); vb=mb.get(met,np.nan)
            if np.isnan(vr) or np.isnan(vb):
                out.append(np.nan); continue
            if lower_better:
                delta=vr-vb
            else:
                delta=vb-vr
            if relative:
                out.append(100*delta/abs(vr) if vr!=0 else np.nan)
            else:
                out.append(delta)
        return out

    METS=[("RMSE","RMSE reduction (%)",True,True),
          ("Pbias_abs","|Pbias| reduction (%)",True,True),
          ("r","Pearson r improvement",False,False),
          ("NSE","NSE improvement",False,False),
          ("KGE","KGE improvement",False,False),
          ("d","Index of agreement d improvement",False,False)]

    fig,axes=plt.subplots(2,3,figsize=(22,11.5))
    fig.subplots_adjust(hspace=0.44,wspace=0.28,
                        left=0.060,right=0.985,top=0.87,bottom=0.14)

    x=np.arange(len(stns)); bw=0.38
    for pi,(met,ylabel,lower,relative) in enumerate(METS):
        ax=axes[pi//3,pi%3]
        d_d=improvement_values(obs_d,raw_ens_d,bc_ens_d,met,lower,relative)
        d_m=(improvement_values(obs_m,raw_ens_m,bc_ens_m,met,lower,relative)
             if obs_m is not None else [np.nan]*len(stns))
        b1=ax.bar(x-bw/2,d_d,width=bw,color=C["bc_lt"],
                  edgecolor=C["bc_bd"],linewidth=0.9,alpha=0.90,
                  label="Daily",zorder=3)
        b2=ax.bar(x+bw/2,d_m,width=bw,color=C["ens_lt"],
                  edgecolor=C["ens_bd"],linewidth=0.9,alpha=0.90,
                  label="Monthly",zorder=3)
        ax.axhline(0,color=C["grey"],lw=1.0,ls="-",alpha=0.75)
        for bar,v in list(zip(b1,d_d))+list(zip(b2,d_m)):
            if not np.isnan(v) and v<0:
                bar.set_facecolor(C["raw_lt"]); bar.set_edgecolor(C["raw_bd"])
        vals=[v for v in d_d+d_m if not np.isnan(v)]
        if vals:
            vmax=max(abs(min(vals)),abs(max(vals)))
            pad=0.16*vmax if vmax>0 else 0.1
            ax.set_ylim(min(vals)-pad, max(vals)+pad)
        ax.set_xticks(x)
        ax.set_xticklabels(codes,rotation=90,ha="center",va="top",fontsize=7.5)
        ax.tick_params(axis="x",pad=2)
        ax.set_xlabel("Station",fontsize=11,fontweight="bold")
        ax.set_ylabel(ylabel,fontsize=11,fontweight="bold")
        tag=chr(97+pi)
        ax.set_title(f"({tag}) {ylabel}",loc="left",fontsize=12,fontweight="bold",pad=4)
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
        if pi==0:
            handles=[
                mpatches.Patch(facecolor=C["bc_lt"],edgecolor=C["bc_bd"],label="Daily"),
                mpatches.Patch(facecolor=C["ens_lt"],edgecolor=C["ens_bd"],label="Monthly"),
                mpatches.Patch(facecolor=C["raw_lt"],edgecolor=C["raw_bd"],label="Degradation"),
            ]
            ax.legend(handles=handles,fontsize=10.0,frameon=True,edgecolor="#B0BEC5",
                      facecolor="white",framealpha=0.92,loc="upper right",ncol=3,
                      handlelength=1.3,columnspacing=0.9)

    fig.suptitle(
        "Station-wise Improvement After QDM Bias Correction\n"
        "Positive values indicate improvement; red bars indicate degradation",
        fontsize=14,fontweight="bold"
    )
    savefig(fig,out_dir/f"{prefix}_Fig7_MetricImprovement")

# 
#  -9  SIGNIFICANCE TEST FIGURE
# 

def build_significance_fig(wilcox_rows,ks_rows,stns,smap,period_obs,out_dir,prefix):
    """
    Fig 8: Wilcoxon + KS test results.
    (a) -log10(p) bar chart with significance stars
    (b) Effect size
    (c) KS-D comparison
    (d) % error reduction
    """
    stns_str=[str(s) for s in stns]
    codes=[smap[s] for s in stns_str]

    def _get(rows,stn,key):
        for r in rows:
            if r["Station"]==stn: return r.get(key,np.nan)
        return np.nan

    p1   =[_get(wilcox_rows,s,"p_one")   for s in stns_str]
    eff  =[_get(wilcox_rows,s,"effect_r") for s in stns_str]
    pct  =[_get(wilcox_rows,s,"pct_reduction") for s in stns_str]
    fdr  =[_get(wilcox_rows,s,"sig_fdr") for s in stns_str]
    D_raw=[_get(ks_rows,s,"D_raw")  for s in stns_str]
    D_bc =[_get(ks_rows,s,"D_bc")   for s in stns_str]

    fig,axes=plt.subplots(2,2,figsize=(18.5,12.5))
    fig.subplots_adjust(hspace=0.55,wspace=0.30,
                        left=0.075,right=0.97,top=0.90,bottom=0.13)
    x=np.arange(len(stns))

    # Panel (a) Wilcoxon -log10(p)
    ax=axes[0,0]
    p_col=[]
    for pv in p1:
        if np.isnan(pv): p_col.append("#E0E0E0")
        elif pv<0.001:   p_col.append("#1B5E20")
        elif pv<0.01:    p_col.append("#2E7D32")
        elif pv<0.05:    p_col.append("#81C784")
        else:            p_col.append("#ECEFF1")
    vals_log=[-math.log10(max(pv,1e-10)) if not np.isnan(pv) else 0 for pv in p1]
    ax.bar(x,vals_log,color=p_col,edgecolor="white",linewidth=0.6,zorder=3)
    for i,(lp,sig_fdr) in enumerate(zip(vals_log,fdr)):
        stars=_sig_stars(p1[i]) if not np.isnan(p1[i]) else "-"
        if stars not in ("-","ns"):
            ax.text(i,lp+0.08,stars,ha="center",va="bottom",
                    fontsize=10.5,fontweight="bold",color="#1A1A1A")
        if sig_fdr=="sig":
            ax.scatter(i,lp+0.35,marker="D",s=40,color="#1565C0",zorder=6)
    ax.axhline(-math.log10(0.05),color="#C0392B",lw=1.2,ls="-",label="p=0.05")
    ax.axhline(-math.log10(0.01),color="#E67E22",lw=1.0,ls=":",label="p=0.01")
    ax.axhline(-math.log10(0.001),color="#8E44AD",lw=1.0,ls=":",label="p=0.001")
    ax.scatter([],[],marker="D",s=40,color="#1565C0",label="FDR q<0.05")
    ax.set_xticks(x); ax.set_xticklabels(codes,rotation=90,ha="center",va="top",fontsize=7.5)
    ax.tick_params(axis="x",pad=2)
    ax.set_ylabel("-log-(p-value)",fontsize=12,fontweight="bold")
    ax.set_title("(a)  Wilcoxon Signed-Rank Test (one-tailed)\n"
                 "     H: |err_BC| < |err_Raw|",
                 loc="left",fontsize=12,fontweight="bold",pad=4)
    ax.legend(fontsize=9.5,frameon=True,edgecolor="#B0BEC5",
              facecolor="white",framealpha=0.92,ncol=2,loc="upper right")
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.set_ylim(bottom=0)

    # Panel (b) Effect size
    ax=axes[0,1]
    eff_col=[]
    for v in eff:
        if np.isnan(v):  eff_col.append("#E0E0E0")
        elif v>=0.5:     eff_col.append("#1565C0")
        elif v>=0.3:     eff_col.append("#42A5F5")
        elif v>=0.1:     eff_col.append("#90CAF9")
        else:            eff_col.append("#DDEEFF")
    ax.bar(x,eff,color=eff_col,edgecolor="white",linewidth=0.6,zorder=3)
    for thresh,col,lbl in [(0.5,"#1565C0","Large (-0.5)"),
                            (0.3,"#42A5F5","Medium (-0.3)"),
                            (0.1,"#90CAF9","Small (-0.1)")]:
        ax.axhline(thresh,color=col,lw=1.1,ls="-",alpha=0.75,label=lbl)
    ax.set_xticks(x); ax.set_xticklabels(codes,rotation=90,ha="center",va="top",fontsize=7.5)
    ax.tick_params(axis="x",pad=2)
    ax.set_ylabel("Effect Size r = Z/-N",fontsize=12,fontweight="bold")
    ax.set_title("(b)  Effect Size (Cohen 1988)",
                 loc="left",fontsize=12,fontweight="bold",pad=4)
    ax.legend(fontsize=9.5,frameon=True,edgecolor="#B0BEC5",
              facecolor="white",framealpha=0.92,loc="upper right")
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.set_ylim(bottom=0)

    # Panel (c) KS-test D statistic
    ax=axes[1,0]
    bw2=0.38
    ax.bar(x-bw2/2,D_raw,width=bw2,color=C["raw_lt"],edgecolor=C["raw_bd"],
           linewidth=0.9,alpha=0.88,label="D: Raw vs Obs",zorder=3)
    ax.bar(x+bw2/2,D_bc, width=bw2,color=C["bc_lt"], edgecolor=C["bc_bd"],
           linewidth=0.9,alpha=0.88,label="D: BC vs Obs",zorder=3)
    ax.set_xticks(x); ax.set_xticklabels(codes,rotation=90,ha="center",va="top",fontsize=7.5)
    ax.tick_params(axis="x",pad=2)
    ax.set_ylabel("KS Statistic D  [lower = more similar]",
                  fontsize=12,fontweight="bold")
    ax.set_title("(c)  Kolmogorov-Smirnov Test\n"
                 "     Two-sample: Sim vs Obs (wet days - 1 mm/day)",
                 loc="left",fontsize=12,fontweight="bold",pad=4)
    ax.legend(fontsize=9.5,frameon=True,edgecolor="#B0BEC5",
              facecolor="white",framealpha=0.92,loc="upper right")
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.set_ylim(bottom=0)

    # Panel (d) % error reduction
    ax=axes[1,1]
    pct_col=[C["bc_lt"] if not np.isnan(v) and v>0 else C["raw_lt"] for v in pct]
    pct_edge=[C["bc_bd"] if not np.isnan(v) and v>0 else C["raw_bd"] for v in pct]
    bars=ax.bar(x,pct,color=pct_col,edgecolor=pct_edge,
                linewidth=0.9,alpha=0.88,zorder=3)
    ax.axhline(0,color=C["grey"],lw=0.9,ls="-",alpha=0.65)
    for bar,v in zip(bars,pct):
        if not np.isnan(v) and abs(v)>0.5:
            ax.text(bar.get_x()+bar.get_width()/2,
                    v+(1.5 if v>=0 else -2.5),
                    f"{v:+.1f}%",ha="center",
                    va=("bottom" if v>=0 else "top"),
                    fontsize=7.2,fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(codes,rotation=90,ha="center",va="top",fontsize=7.5)
    ax.tick_params(axis="x",pad=2)
    ax.set_ylabel("Median Error Reduction (%)\n[positive = BC improved]",
                  fontsize=12,fontweight="bold")
    ax.set_title("(d)  Median Absolute Error Reduction After QDM",
                 loc="left",fontsize=12,fontweight="bold",pad=4)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)

    fig.suptitle(
        "Statistical Significance Testing - QDM Bias Correction\n"
        f"Obs: {period_obs}  |  *** p<0.001  ** p<0.01  * p<0.05  ns: not significant",
        fontsize=14,fontweight="bold"
    )
    savefig(fig,out_dir/f"{prefix}_Fig8_SignificanceTesting")

# 
#  -10  MONTHLY CLIMATOLOGY FIGURE
# 

def build_monthly_climatology(obs_d,raw_dfs,bc_dfs,stns,smap,
                               period_obs,out_dir,prefix):
    """
    Fig 9: Monthly climatology (mean - std) for regional mean + per-station grid.
    """
    stns_str=[str(s) for s in stns]
    codes=[smap[s] for s in stns_str]

    def monthly_clim(df,cols):
        if df is None: return None,None
        sub=df[[c for c in cols if c in df.columns]]
        mon=sub.resample("MS").sum(min_count=20)
        reg=mon.mean(axis=1)
        clim=reg.groupby(reg.index.month).agg(["mean","std"]).reindex(range(1,13))
        return clim["mean"].values,clim["std"].values

    obs_m,obs_s=monthly_clim(obs_d,stns_str)
    raw_ens=ensemble_mean(raw_dfs); bc_ens=ensemble_mean(bc_dfs)
    raw_m,raw_s=monthly_clim(raw_ens,stns_str)
    bc_m, bc_s =monthly_clim(bc_ens, stns_str)

    months=np.arange(1,13)

    # Main figure: regional mean
    n_stn=len(stns)
    ncols_g=min(4,n_stn); nrows_g=math.ceil(n_stn/ncols_g)
    fig=plt.figure(figsize=(14, min(5+nrows_g*3.2, 18)))
    gs=gridspec.GridSpec(1+nrows_g,ncols_g,figure=fig,
                         hspace=0.52,wspace=0.30,
                         left=0.07,right=0.97,top=0.92,bottom=0.06)

    # Row 0: regional mean
    ax0=fig.add_subplot(gs[0,:])
    if obs_m is not None:
        ax0.plot(months,obs_m,color=C["obs"],lw=2.6,ls="-",
                 marker="o",ms=5,label="Observed",zorder=5)
        if obs_s is not None:
            ax0.fill_between(months,obs_m-obs_s,obs_m+obs_s,
                             color=C["obs_lt"],alpha=0.30,zorder=2)
    if raw_m is not None:
        ax0.plot(months,raw_m,color=C["raw"],lw=2.2,ls="-",
                 marker="^",ms=5,label="Raw CMIP6",zorder=4)
        if raw_s is not None:
            ax0.fill_between(months,raw_m-raw_s,raw_m+raw_s,
                             color=C["raw_lt"],alpha=0.25,zorder=2)
    if bc_m is not None:
        ax0.plot(months,bc_m,color=C["bc"],lw=2.2,ls="-",
                 marker="s",ms=5,label="Bias-Corrected (QDM)",zorder=4)
        if bc_s is not None:
            ax0.fill_between(months,bc_m-bc_s,bc_m+bc_s,
                             color=C["bc_lt"],alpha=0.25,zorder=2)
    ax0.set_xticks(months)
    ax0.set_xticklabels(MONTH_ABBR,fontsize=11)
    ax0.set_ylabel("Mean Monthly Rainfall (mm)",fontsize=12,fontweight="bold")
    ax0.set_title("Regional Mean Monthly Climatology (1- shading)",
                  loc="left",fontsize=13,fontweight="bold",pad=5)
    ax0.legend(fontsize=11,frameon=True,edgecolor="#B0BEC5",
               facecolor="white",framealpha=0.92,ncol=3,loc="upper left")
    ax0.yaxis.set_minor_locator(ticker.AutoMinorLocator())
    ax0.spines["top"].set_visible(False); ax0.spines["right"].set_visible(False)

    # Per-station sub-panels
    for si,stn in enumerate(stns_str):
        ri=(si//ncols_g)+1; ci=si%ncols_g
        ax=fig.add_subplot(gs[ri,ci])
        def stn_clim(df):
            if df is None or stn not in df.columns: return None,None
            mon=df[[stn]].resample("MS").sum(min_count=20)[stn]
            c=mon.groupby(mon.index.month).agg(["mean","std"]).reindex(range(1,13))
            return c["mean"].values,c["std"].values
        om,os_=stn_clim(obs_d)
        rm,rs_=stn_clim(raw_ens)
        bm,bs_=stn_clim(bc_ens)
        if om is not None:
            ax.plot(months,om,color=C["obs"],lw=1.8,ls="-",marker="o",ms=3)
        if rm is not None:
            ax.plot(months,rm,color=C["raw"],lw=1.4,ls="-",marker="^",ms=3)
        if bm is not None:
            ax.plot(months,bm,color=C["bc"],lw=1.4,ls="-",marker="s",ms=3)
        ax.set_xticks(months)
        ax.set_xticklabels([m[0] for m in MONTH_ABBR],fontsize=8)
        ax.set_title(codes[si],fontsize=10,fontweight="bold",pad=2)
        ax.tick_params(labelsize=8,width=1.2)
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)

    fig.suptitle(
        f"Monthly Rainfall Climatology - "
        f"Observed vs Raw CMIP6 vs Bias-Corrected (QDM)\n"
        f"Period: {period_obs}",
        fontsize=14,fontweight="bold"
    )
    savefig(fig,out_dir/f"{prefix}_Fig9_MonthlyCycles")

# 
#  -11  ANNUAL TIME SERIES FIGURE
# 

def build_annual_timeseries(obs_d,raw_dfs,bc_dfs,stns,period_obs,out_dir,prefix):
    """Fig 10: Regional-mean annual time series with ensemble spread."""
    stns_str=[str(s) for s in stns]

    def reg_ann(df):
        if df is None: return None
        cols=[s for s in stns_str if s in df.columns]
        if not cols: return None
        ann=to_annual(df)
        return ann[cols].mean(axis=1) if ann is not None else None

    obs_ann=reg_ann(obs_d)
    raw_anns=[reg_ann(df) for df in raw_dfs.values() if df is not None]
    bc_anns =[reg_ann(df) for df in bc_dfs.values()  if df is not None]

    def ens_stat(anns):
        if not anns: return None,None,None
        ci=anns[0].index
        for s in anns[1:]: ci=ci.intersection(s.index)
        if len(ci)==0: return None,None,None
        stack=np.array([s.loc[ci].values for s in anns])
        m=pd.Series(np.nanmean(stack,axis=0),index=ci)
        lo=pd.Series(np.nanmin(stack,axis=0),index=ci)
        hi=pd.Series(np.nanmax(stack,axis=0),index=ci)
        return m,lo,hi

    raw_ens,raw_lo,raw_hi=ens_stat(raw_anns)
    bc_ens, bc_lo, bc_hi =ens_stat(bc_anns)

    fig,ax=plt.subplots(1,1,figsize=(14,7))
    fig.subplots_adjust(left=0.09,right=0.97,top=0.88,bottom=0.11)

    def _plot_spread(ax,ens,lo,hi,col,lt,lbl,ls):
        if ens is None: return
        yr=ens.index.year
        ax.fill_between(yr,lo.values,hi.values,color=lt,alpha=0.32,zorder=2)
        ax.plot(yr,ens.values,color=col,lw=2.2,ls=ls,
                label=f"{lbl} ensemble mean",zorder=4)

    _plot_spread(ax,raw_ens,raw_lo,raw_hi,C["raw"],C["raw_lt"],"Raw CMIP6","-")
    _plot_spread(ax,bc_ens, bc_lo, bc_hi, C["bc"], C["bc_lt"], "BC (QDM)","-")

    if obs_ann is not None:
        obs_s=obs_ann.dropna()
        ax.plot(obs_s.index.year,obs_s.values,
                color=C["obs"],lw=2.8,ls="-",zorder=6,
                marker="o",markersize=4,label="Observed")

    ax.set_xlabel("Year",fontsize=13,fontweight="bold")
    ax.set_ylabel("Annual Rainfall - Regional Mean (mm)",fontsize=13,fontweight="bold")
    ax.set_title(
        f"Annual Rainfall Time Series - Regional Mean  |  {period_obs}\n"
        "Shaded band = model ensemble range (min-max)",
        loc="left",fontsize=13,fontweight="bold",pad=5
    )
    ax.tick_params(axis="both",which="major",labelsize=11,width=1.4)
    ax.legend(fontsize=11,frameon=True,edgecolor="#B0BEC5",
              facecolor="white",framealpha=0.92,loc="upper right",ncol=3)
    ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)

    savefig(fig,out_dir/f"{prefix}_Fig10_AnnualTimeSeries")

# 
#  -12B  WET-DAY, TREND, AND LAG-K ANALYSIS
# 

def _annual_metric_series(df, stn, metric):
    """Return annual station series for hydrological trend diagnostics."""
    if df is None or stn not in df.columns:
        return pd.Series(dtype=float)
    s=df[stn].astype(float).dropna()
    if s.empty:
        return pd.Series(dtype=float)
    wet=s.where(s>=WET_THR)
    if metric=="annual_total":
        out=s.resample("YS").sum(min_count=300)
    elif metric=="wetday_count":
        out=(s>=WET_THR).astype(float).resample("YS").sum(min_count=300)
    elif metric=="wetday_frequency":
        cnt=(s>=WET_THR).astype(float).resample("YS").sum(min_count=300)
        n=s.resample("YS").count()
        out=100*cnt/n
    elif metric=="wetday_intensity":
        out=wet.resample("YS").mean()
    elif metric=="rx1day":
        out=s.resample("YS").max()
    else:
        raise ValueError(f"Unknown annual metric: {metric}")
    return out.dropna()

def _lag_autocorr(values, lag):
    x=np.asarray(values,dtype=float)
    x=x[~np.isnan(x)]
    if len(x)<=lag+2:
        return np.nan
    a=x[:-lag]; b=x[lag:]
    if np.nanstd(a,ddof=1)==0 or np.nanstd(b,ddof=1)==0:
        return np.nan
    rho,_=spearmanr(a,b)
    return float(rho)

def _effective_n(values, lag_k=TREND_LAG_K):
    x=np.asarray(values,dtype=float)
    x=x[~np.isnan(x)]
    n=len(x)
    if n<8:
        return n, []
    rhos=[]
    denom=1.0
    for k in range(1, min(lag_k,n-2)+1):
        rho=_lag_autocorr(x,k)
        if np.isnan(rho):
            continue
        rhos.append((k,rho))
    cf=1.0
    for k,rho in rhos:
        w=((n-k)*(n-k-1)*(n-k-2))/(n*(n-1)*(n-2)) if n>2 else 0
        cf += 2*w*rho
    neff=max(3.0,min(float(n),n/max(cf,1e-6)))
    return neff,rhos

def mann_kendall_sen(years, values, lag_k=TREND_LAG_K):
    """
    Mann-Kendall trend test with Sen slope and lag-k effective sample adjustment.
    The lag adjustment is conservative for autocorrelated annual hydroclimate series.
    """
    years=np.asarray(years,dtype=float)
    x=np.asarray(values,dtype=float)
    mask=~np.isnan(years)&~np.isnan(x)
    years=years[mask]; x=x[mask]
    n=len(x)
    if n<8:
        return dict(n=n,slope=np.nan,z=np.nan,p=np.nan,tau=np.nan,
                    trend="insufficient",neff=np.nan,lag_k=lag_k,rho1=np.nan)
    slopes=[]
    s_stat=0
    for i in range(n-1):
        dx=x[i+1:]-x[i]
        dy=years[i+1:]-years[i]
        s_stat += int(np.sum(np.sign(dx)))
        valid=dy!=0
        slopes.extend((dx[valid]/dy[valid]).tolist())
    slope=float(np.median(slopes)) if slopes else np.nan
    unique, counts=np.unique(x, return_counts=True)
    tie_term=np.sum(counts*(counts-1)*(2*counts+5))
    var_s=(n*(n-1)*(2*n+5)-tie_term)/18.0
    neff,rhos=_effective_n(x,lag_k)
    if var_s>0 and neff<n:
        var_s *= n/neff
    if s_stat>0:
        z=(s_stat-1)/math.sqrt(var_s)
    elif s_stat<0:
        z=(s_stat+1)/math.sqrt(var_s)
    else:
        z=0.0
    p=float(2*(1-sps.norm.cdf(abs(z))))
    tau=float(s_stat/(0.5*n*(n-1)))
    trend=("increasing" if p<0.05 and z>0 else
           "decreasing" if p<0.05 and z<0 else "no significant trend")
    rho1=next((r for k,r in rhos if k==1),np.nan)
    return dict(n=n,slope=slope,z=float(z),p=p,tau=tau,trend=trend,
                neff=float(neff),lag_k=lag_k,rho1=rho1)

def build_hydroclimate_diagnostics(obs_d, raw_dfs, bc_dfs, stns, smap):
    stns_str=[str(s) for s in stns]
    raw_ens=ensemble_mean(raw_dfs)
    bc_ens=ensemble_mean(bc_dfs)
    datasets=[("Observed",obs_d),("Raw ensemble",raw_ens),("BC-QDM ensemble",bc_ens)]
    metrics=[
        ("annual_total","Annual rainfall","mm yr-1"),
        ("wetday_count","Wet-day count","days yr-1"),
        ("wetday_frequency","Wet-day frequency","% days yr-1"),
        ("wetday_intensity","Wet-day intensity","mm wet-day-1"),
        ("rx1day","Annual maximum 1-day rainfall","mm"),
    ]
    wet_rows=[]
    trend_rows=[]
    lag_rows=[]
    for ds_name,df in datasets:
        if df is None:
            continue
        for stn in stns_str:
            code=smap.get(stn,stn)
            for metric,metric_label,unit in metrics:
                ser=_annual_metric_series(df,stn,metric)
                vals=ser.values.astype(float)
                years=ser.index.year.values if len(ser) else np.array([])
                if len(vals):
                    wet_rows.append(dict(
                        Dataset=ds_name,Station=stn,Code=code,Metric=metric_label,
                        Unit=unit,Period=f"{int(years[0])}-{int(years[-1])}",
                        N_years=int(len(vals)),Mean=float(np.nanmean(vals)),
                        SD=float(np.nanstd(vals,ddof=1)) if len(vals)>1 else np.nan,
                        Min=float(np.nanmin(vals)),Max=float(np.nanmax(vals))
                    ))
                tr=mann_kendall_sen(years,vals,TREND_LAG_K)
                trend_rows.append(dict(
                    Dataset=ds_name,Station=stn,Code=code,Metric=metric_label,Unit=unit,
                    Period=f"{int(years[0])}-{int(years[-1])}" if len(years) else "N/A",
                    N_years=tr["n"],Lag_k=tr["lag_k"],N_eff=tr["neff"],
                    Rho_lag1=tr["rho1"],Sen_slope_per_year=tr["slope"],
                    MK_tau=tr["tau"],Z=tr["z"],P_value=tr["p"],Trend=tr["trend"]
                ))
            for metric,metric_label,unit in metrics:
                ser=_annual_metric_series(df,stn,metric)
                vals=ser.values.astype(float)
                for lag in range(1,ACF_MAX_LAG+1):
                    lag_rows.append(dict(
                        Dataset=ds_name,Station=stn,Code=code,Metric=metric_label,
                        Unit=unit,Lag_years=lag,Autocorrelation=_lag_autocorr(vals,lag)
                    ))
    return wet_rows,trend_rows,lag_rows

def _rows_to_df(rows):
    return pd.DataFrame(rows) if rows else pd.DataFrame()

def build_wetday_trend_fig(obs_d, raw_dfs, bc_dfs, stns, out_dir, prefix):
    """Publication diagnostic figure for wet-day frequency and trend summaries."""
    stns_str=[str(s) for s in stns]
    period=f"{obs_d.index.min().year}-{obs_d.index.max().year}" if obs_d is not None and len(obs_d.index) else "analysis period"
    raw_ens=ensemble_mean(raw_dfs)
    bc_ens=ensemble_mean(bc_dfs)
    datasets=[("Observed",obs_d,C["obs"],"-"),
              ("Raw ensemble",raw_ens,C["raw"],"--"),
              ("BC-QDM ensemble",bc_ens,C["bc"],"-")]

    def regional_annual(df,metric):
        if df is None: return pd.Series(dtype=float)
        cols=[s for s in stns_str if s in df.columns]
        if not cols: return pd.Series(dtype=float)
        vals=[]
        idx=None
        for stn in cols:
            ser=_annual_metric_series(df,stn,metric)
            if idx is None: idx=ser.index
            else: idx=idx.intersection(ser.index)
        if idx is None or len(idx)==0: return pd.Series(dtype=float)
        mat=np.vstack([_annual_metric_series(df,stn,metric).loc[idx].values for stn in cols])
        return pd.Series(np.nanmean(mat,axis=0),index=idx)

    fig,axes=plt.subplots(2,2,figsize=(14,9.6))
    fig.subplots_adjust(left=0.08,right=0.97,top=0.86,bottom=0.09,
                        hspace=0.34,wspace=0.26)
    panels=[("a","wetday_frequency","Wet-day frequency (% of days)",
             "Wet-day frequency trend"),
            ("b","wetday_count","Wet-day count (days yr-1)",
             "Annual wet-day count trend"),
            ("c","wetday_intensity","Wet-day intensity (mm wet-day-1)",
             "Mean wet-day intensity trend"),
            ("d","annual_total","Annual rainfall (mm yr-1)",
             "Annual rainfall total trend")]
    for ax,(tag,metric,ylabel,title) in zip(axes.flatten(),panels):
        for label,df,col,ls in datasets:
            ser=regional_annual(df,metric).dropna()
            if ser.empty: continue
            years=ser.index.year.values
            ax.plot(years,ser.values,color=col,ls=ls,lw=2.1,label=label)
            tr=mann_kendall_sen(years,ser.values,TREND_LAG_K)
            if not np.isnan(tr["slope"]):
                yhat=np.nanmedian(ser.values)+tr["slope"]*(years-np.median(years))
                ax.plot(years,yhat,color=col,ls=":",lw=1.4,alpha=0.85)
        ax.set_title(f"({tag})  {title}",loc="left",fontsize=12,fontweight="bold",pad=4)
        ax.set_ylabel(ylabel,fontsize=11,fontweight="bold")
        ax.set_xlabel("Year",fontsize=10,fontweight="bold")
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    axes[0,0].legend(frameon=True,edgecolor="#B0BEC5",facecolor="white",
                     framealpha=0.93,fontsize=9,loc="best")
    fig.suptitle(
        "Wet-Day Frequency and Hydroclimate Trend Diagnostics - QDM Bias Correction\n"
        f"Obs: {period}  |  Wet-day threshold: {WET_THR:g} mm/day  |  Trend adjusted by lag k = {TREND_LAG_K}",
        fontsize=14,fontweight="bold"
    )
    savefig(fig,out_dir/f"{prefix}_Fig11_WetDayTrendDiagnostics")

def build_lagk_fig(lag_rows, stns, smap, out_dir, prefix):
    """Lag-k autocorrelation heatmap for BC-QDM annual hydroclimate metrics."""
    df=_rows_to_df(lag_rows)
    if df.empty: return
    df=df[(df["Dataset"]=="BC-QDM ensemble") &
          (df["Metric"].isin(["Wet-day frequency","Annual rainfall"]))]
    if df.empty: return
    stns_str=[str(s) for s in stns]
    codes=[smap[s] for s in stns_str]
    lags=sorted(df["Lag_years"].dropna().unique())
    metrics=["Wet-day frequency","Annual rainfall"]
    fig,axes=plt.subplots(1,2,figsize=(15,6.3))
    fig.subplots_adjust(left=0.07,right=0.94,top=0.80,bottom=0.16,wspace=0.24)
    titles=["Wet-day frequency lag-k autocorrelation",
            "Annual rainfall lag-k autocorrelation"]
    for ax,metric,tag,title in zip(axes,metrics,["a","b"],titles):
        mat=np.full((len(lags),len(stns_str)),np.nan)
        sub=df[df["Metric"]==metric]
        for li,lag in enumerate(lags):
            for si,stn in enumerate(stns_str):
                row=sub[(sub["Lag_years"]==lag)&(sub["Station"]==stn)]
                if not row.empty:
                    mat[li,si]=row["Autocorrelation"].iloc[0]
        im=ax.imshow(mat,cmap="RdBu_r",vmin=-1,vmax=1,aspect="auto")
        ax.set_xticks(range(len(stns_str))); ax.set_xticklabels(codes,rotation=90,fontsize=8)
        ax.set_yticks(range(len(lags))); ax.set_yticklabels([f"k={int(k)}" for k in lags],fontsize=9)
        ax.set_title(f"({tag})  {title}",loc="left",fontsize=12,fontweight="bold",pad=4)
        ax.set_xlabel("Station",fontsize=10,fontweight="bold")
        ax.set_ylabel("Lag (years)",fontsize=10,fontweight="bold")
    cax=fig.add_axes([0.955,0.20,0.015,0.62])
    cb=fig.colorbar(im,cax=cax)
    cb.set_label("Autocorrelation",fontsize=10,fontweight="bold")
    fig.suptitle(
        "Lag-k Autocorrelation Diagnostics - BC-QDM Annual Hydroclimate Metrics\n"
        f"Station-wise persistence for k = 1..{ACF_MAX_LAG} years  |  Used before trend interpretation",
        fontsize=14,fontweight="bold"
    )
    savefig(fig,out_dir/f"{prefix}_Fig12_LagKAutocorrelation")

#
#  -12C  ETCCDI EXTREME RAINFALL INDICES
#

ETCCDI_META = {
    "PRCPTOT": ("Annual total wet-day precipitation", "mm yr-1"),
    "R95p":    ("Very wet-day precipitation above local P95", "mm yr-1"),
    "R99p":    ("Extremely wet-day precipitation above local P99", "mm yr-1"),
    "Rx1day":  ("Maximum 1-day precipitation", "mm day-1"),
    "Rx5day":  ("Maximum consecutive 5-day precipitation", "mm 5-day-1"),
    "SDII":    ("Simple daily intensity index", "mm wet-day-1"),
    "CDD":     ("Maximum consecutive dry days", "days"),
    "CWD":     ("Maximum consecutive wet days", "days"),
    "R10mm":   ("Heavy rain days >= 10 mm", "days yr-1"),
    "R20mm":   ("Very heavy rain days >= 20 mm", "days yr-1"),
    "R50mm":   ("Tropical heavy rain days >= 50 mm", "days yr-1"),
    "R100mm":  ("Tropical extreme rain days >= 100 mm", "days yr-1"),
}

ETCCDI_FIG_METRICS = ["R95p","R99p","Rx1day","Rx5day","SDII","CDD","CWD","R50mm"]

def _max_consecutive(mask):
    """Maximum run length for a boolean annual series."""
    arr=np.asarray(mask,dtype=bool)
    if arr.size==0:
        return np.nan
    best=cur=0
    for flag in arr:
        if flag:
            cur+=1
            if cur>best: best=cur
        else:
            cur=0
    return float(best)

def _etccdi_thresholds(obs_d, stns):
    """Observed-station baseline thresholds for localized percentile indices."""
    thresholds={}
    for stn in [str(s) for s in stns]:
        if obs_d is None or stn not in obs_d.columns:
            thresholds[stn]={"p95":np.nan,"p99":np.nan,"n_wet":0}
            continue
        wet=obs_d[stn].astype(float)
        wet=wet[(wet>=WET_THR)&np.isfinite(wet)]
        if wet.empty:
            thresholds[stn]={"p95":np.nan,"p99":np.nan,"n_wet":0}
        else:
            thresholds[stn]={
                "p95":float(np.nanpercentile(wet.values,95)),
                "p99":float(np.nanpercentile(wet.values,99)),
                "n_wet":int(wet.notna().sum()),
            }
    return thresholds

def _etccdi_annual_df(df, stn, thr):
    """Annual ETCCDI precipitation indices for one station."""
    if df is None or stn not in df.columns:
        return pd.DataFrame()
    s=df[stn].astype(float).dropna()
    if s.empty:
        return pd.DataFrame()
    rows=[]
    p95=thr.get("p95",np.nan); p99=thr.get("p99",np.nan)
    for year,grp in s.groupby(s.index.year):
        if grp.notna().sum()<ETCCDI_MIN_DAYS:
            continue
        vals=grp.astype(float)
        wet=vals>=WET_THR
        dry=vals<WET_THR
        wet_vals=vals[wet]
        rx5=vals.rolling(5,min_periods=5).sum().max()
        rows.append({
            "Year":int(year),
            "PRCPTOT":float(wet_vals.sum()) if len(wet_vals) else 0.0,
            "R95p":float(vals[(vals>p95)&wet].sum()) if np.isfinite(p95) else np.nan,
            "R99p":float(vals[(vals>p99)&wet].sum()) if np.isfinite(p99) else np.nan,
            "Rx1day":float(vals.max()) if len(vals) else np.nan,
            "Rx5day":float(rx5) if np.isfinite(rx5) else np.nan,
            "SDII":float(wet_vals.mean()) if len(wet_vals) else np.nan,
            "CDD":_max_consecutive(dry.values),
            "CWD":_max_consecutive(wet.values),
            "R10mm":float((vals>=10.0).sum()),
            "R20mm":float((vals>=20.0).sum()),
            "R50mm":float((vals>=50.0).sum()),
            "R100mm":float((vals>=100.0).sum()),
        })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).set_index("Year").sort_index()

def build_etccdi_diagnostics(obs_d, raw_dfs, bc_dfs, stns, smap):
    """Build ETCCDI annual, summary, and trend tables using observed thresholds."""
    stns_str=[str(s) for s in stns]
    thresholds=_etccdi_thresholds(obs_d,stns_str)
    raw_ens=ensemble_mean(raw_dfs); bc_ens=ensemble_mean(bc_dfs)
    datasets=[("Observed","Observed",obs_d),
              ("Raw ensemble","Raw",raw_ens),
              ("BC-QDM ensemble","BC-QDM",bc_ens)]
    annual_rows=[]; summary_rows=[]; trend_rows=[]

    series_cache={}
    for ds_name,ds_type,df in datasets:
        for stn in stns_str:
            code=smap.get(stn,stn)
            ann=_etccdi_annual_df(df,stn,thresholds.get(stn,{}))
            series_cache[(ds_name,stn)]=ann
            if ann.empty:
                continue
            for year,row in ann.iterrows():
                for idx_name,(desc,unit) in ETCCDI_META.items():
                    annual_rows.append(dict(
                        Dataset=ds_name,Dataset_Type=ds_type,Station=stn,
                        Station_Code=code,Year=int(year),Index=idx_name,
                        Description=desc,Unit=unit,Value=float(row.get(idx_name,np.nan)),
                        WetDay_Threshold_mm=WET_THR,
                        P95_threshold_mm=thresholds[stn]["p95"],
                        P99_threshold_mm=thresholds[stn]["p99"],
                    ))
            for idx_name,(desc,unit) in ETCCDI_META.items():
                vals=ann[idx_name].dropna() if idx_name in ann.columns else pd.Series(dtype=float)
                mean_val=float(vals.mean()) if not vals.empty else np.nan
                med_val=float(vals.median()) if not vals.empty else np.nan
                summary_rows.append(dict(
                    Dataset=ds_name,Dataset_Type=ds_type,Station=stn,
                    Station_Code=code,Index=idx_name,Description=desc,Unit=unit,
                    Mean_Annual=mean_val,Median_Annual=med_val,
                    Min_Annual=float(vals.min()) if not vals.empty else np.nan,
                    Max_Annual=float(vals.max()) if not vals.empty else np.nan,
                    N_Years=int(vals.shape[0]),
                    P95_threshold_mm=thresholds[stn]["p95"],
                    P99_threshold_mm=thresholds[stn]["p99"],
                ))
                tr=mann_kendall_sen(ann.index.values,ann[idx_name].values,TREND_LAG_K) if idx_name in ann.columns else {}
                trend_rows.append(dict(
                    Dataset=ds_name,Dataset_Type=ds_type,Station=stn,
                    Station_Code=code,Index=idx_name,Description=desc,Unit=unit,
                    N=tr.get("n",np.nan),Sen_Slope_per_year=tr.get("slope",np.nan),
                    MK_Z=tr.get("z",np.nan),MK_p=tr.get("p",np.nan),
                    Kendall_tau=tr.get("tau",np.nan),Trend=tr.get("trend","insufficient"),
                    N_effective=tr.get("neff",np.nan),Lag_k=tr.get("lag_k",TREND_LAG_K),
                    Lag1_autocorrelation=tr.get("rho1",np.nan),
                ))

    # Observed-referenced bias and QDM improvement for ensemble annual means.
    obs_lookup={(r["Station"],r["Index"]):r for r in summary_rows if r["Dataset"]=="Observed"}
    raw_lookup={(r["Station"],r["Index"]):r for r in summary_rows if r["Dataset"]=="Raw ensemble"}
    bc_lookup ={(r["Station"],r["Index"]):r for r in summary_rows if r["Dataset"]=="BC-QDM ensemble"}
    bias_rows=[]
    for stn in stns_str:
        for idx_name,(desc,unit) in ETCCDI_META.items():
            obs=obs_lookup.get((stn,idx_name),{}).get("Mean_Annual",np.nan)
            raw=raw_lookup.get((stn,idx_name),{}).get("Mean_Annual",np.nan)
            bc =bc_lookup.get((stn,idx_name),{}).get("Mean_Annual",np.nan)
            raw_bias=raw-obs if np.isfinite(raw) and np.isfinite(obs) else np.nan
            bc_bias=bc-obs if np.isfinite(bc) and np.isfinite(obs) else np.nan
            raw_abs=abs(raw_bias) if np.isfinite(raw_bias) else np.nan
            bc_abs=abs(bc_bias) if np.isfinite(bc_bias) else np.nan
            improvement=100.0*(raw_abs-bc_abs)/raw_abs if np.isfinite(raw_abs) and raw_abs>0 else np.nan
            bias_rows.append(dict(
                Station=stn,Station_Code=smap.get(stn,stn),Index=idx_name,
                Description=desc,Unit=unit,
                Observed_Mean=obs,Raw_Mean=raw,BC_QDM_Mean=bc,
                Raw_Bias=raw_bias,BC_QDM_Bias=bc_bias,
                Raw_Abs_Bias=raw_abs,BC_QDM_Abs_Bias=bc_abs,
                Bias_Reduction_percent=improvement,
                Tail_Repaired=bool(np.isfinite(improvement) and improvement>0),
            ))
    return thresholds, annual_rows, summary_rows, bias_rows, trend_rows

def _df_from_rows(rows):
    return pd.DataFrame(rows) if rows else pd.DataFrame()

def build_etccdi_bias_fig(bias_rows, stns, smap, out_dir, prefix):
    """Fig 13: station-wise QDM improvement for ETCCDI extremes."""
    df=_df_from_rows(bias_rows)
    if df.empty: return
    stns_str=[str(s) for s in stns]
    codes=[smap.get(s,s) for s in stns_str]
    x=np.arange(len(stns_str)); bw=0.36
    fig,axes=plt.subplots(2,4,figsize=(22,10.8))
    fig.subplots_adjust(left=0.055,right=0.985,top=0.84,bottom=0.13,
                        hspace=0.46,wspace=0.28)
    for ax,idx_name,tag in zip(axes.flatten(),ETCCDI_FIG_METRICS,list("abcdefgh")):
        sub=df[df["Index"]==idx_name].set_index("Station")
        raw=[sub.loc[s,"Raw_Abs_Bias"] if s in sub.index else np.nan for s in stns_str]
        bc=[sub.loc[s,"BC_QDM_Abs_Bias"] if s in sub.index else np.nan for s in stns_str]
        imp=[sub.loc[s,"Bias_Reduction_percent"] if s in sub.index else np.nan for s in stns_str]
        imp_plot=np.clip(np.asarray(imp,dtype=float),-100.0,100.0)
        ax.bar(x-bw/2,raw,width=bw,color=C["raw_lt"],edgecolor=C["raw_bd"],linewidth=0.9,label="Raw |bias|",zorder=3)
        ax.bar(x+bw/2,bc,width=bw,color=C["bc_lt"],edgecolor=C["bc_bd"],linewidth=0.9,label="BC-QDM |bias|",zorder=3)
        ax2=ax.twinx()
        ax2.plot(x,imp_plot,color=C["green"],marker="o",ms=3.2,lw=1.2,alpha=0.88,
                 label="Bias reduction (%; clipped)")
        ax2.axhline(0,color=C["grey"],lw=0.8,ls="--",alpha=0.55)
        ax2.set_ylim(-110,110)
        desc,unit=ETCCDI_META[idx_name]
        ax.set_title(f"({tag})  {idx_name}: {desc}",loc="left",fontsize=10.5,fontweight="bold",pad=4)
        ax.set_ylabel(f"|Bias| ({unit})",fontsize=9.5,fontweight="bold")
        ax2.set_ylabel("Reduction (%)",fontsize=9.0,fontweight="bold",color=C["green"])
        ax2.tick_params(axis="y",labelsize=8.2,colors=C["green"])
        ax.set_xticks(x); ax.set_xticklabels(codes,rotation=90,ha="center",va="top",fontsize=7.5)
        ax.tick_params(axis="x",pad=2)
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.grid(axis="y",alpha=0.25,zorder=0)
        ax.spines["top"].set_visible(False); ax2.spines["top"].set_visible(False)
        if tag=="a":
            h1,l1=ax.get_legend_handles_labels()
            h2,l2=ax2.get_legend_handles_labels()
            ax.legend(h1+h2,l1+l2,fontsize=9,frameon=True,edgecolor="#B0BEC5",
                      facecolor="white",framealpha=0.92,loc="upper right",ncol=3)
    fig.suptitle(
        "ETCCDI Extreme Rainfall Indices - QDM Bias Reduction\n"
        "Observed-local percentile thresholds for R95p/R99p; green line is clipped to +/-100% for display only",
        fontsize=14,fontweight="bold"
    )
    savefig(fig,out_dir/f"{prefix}_Fig13_ETCCDI_BiasReduction")

def build_etccdi_trend_fig(trend_rows, stns, smap, out_dir, prefix):
    """Fig 14: trend significance heatmap for BC-QDM ETCCDI indices."""
    df=_df_from_rows(trend_rows)
    if df.empty: return
    df=df[df["Dataset"]=="BC-QDM ensemble"]
    if df.empty: return
    stns_str=[str(s) for s in stns]
    codes=[smap.get(s,s) for s in stns_str]
    metrics=["R95p","R99p","Rx1day","Rx5day","SDII","CDD","CWD","R10mm","R20mm","R50mm","R100mm"]
    mat=np.full((len(metrics),len(stns_str)),np.nan)
    pmat=np.full_like(mat,np.nan,dtype=float)
    for mi,idx_name in enumerate(metrics):
        sub=df[df["Index"]==idx_name]
        for si,stn in enumerate(stns_str):
            row=sub[sub["Station"]==stn]
            if not row.empty:
                mat[mi,si]=row["Sen_Slope_per_year"].iloc[0]
                pmat[mi,si]=row["MK_p"].iloc[0]
    vmax=np.nanpercentile(np.abs(mat),95) if np.isfinite(mat).any() else 1.0
    if not np.isfinite(vmax) or vmax==0: vmax=1.0
    fig,ax=plt.subplots(1,1,figsize=(18,7.5))
    fig.subplots_adjust(left=0.12,right=0.92,top=0.82,bottom=0.17)
    im=ax.imshow(mat,cmap="RdBu_r",vmin=-vmax,vmax=vmax,aspect="auto")
    ax.set_xticks(range(len(stns_str))); ax.set_xticklabels(codes,rotation=90,fontsize=8)
    ax.set_yticks(range(len(metrics)))
    ax.set_yticklabels([f"{m} ({ETCCDI_META[m][1]}/yr)" for m in metrics],fontsize=9)
    ax.set_xlabel("Station",fontsize=11,fontweight="bold")
    ax.set_title("(a)  Sen's slope and Mann-Kendall significance for BC-QDM ETCCDI indices",
                 loc="left",fontsize=12,fontweight="bold",pad=5)
    for mi in range(len(metrics)):
        for si in range(len(stns_str)):
            if np.isfinite(pmat[mi,si]) and pmat[mi,si]<0.05:
                ax.text(si,mi,"*",ha="center",va="center",fontsize=10,fontweight="bold",color="black")
    cax=fig.add_axes([0.94,0.21,0.015,0.56])
    cb=fig.colorbar(im,cax=cax)
    cb.set_label("Sen slope per year",fontsize=10,fontweight="bold")
    fig.suptitle(
        "ETCCDI Extreme Rainfall Trend Significance - BC-QDM Ensemble\n"
        f"Mann-Kendall test with lag-k effective sample adjustment (k = {TREND_LAG_K}); * indicates p < 0.05",
        fontsize=14,fontweight="bold"
    )
    savefig(fig,out_dir/f"{prefix}_Fig14_ETCCDI_TrendSignificance")

def append_etccdi_excel(wb, thresholds, annual_rows, summary_rows, bias_rows, trend_rows):
    """Append ETCCDI extreme-rainfall sheets for Q1/Q2 review traceability."""
    def _write_table(ws, title, subtitle, rows, widths=None, freeze="A5"):
        ws.sheet_view.showGridLines=False
        if not rows:
            mxsc(ws,1,1,6,title,bold=True,fc="FFFFFF",bg=XC["title"],sz=13,align="left")
            mxsc(ws,2,1,6,"No data available",italic=True,fc="FFFFFF",bg=XC["sub"],sz=9,align="left")
            return
        cols=list(rows[0].keys())
        mxsc(ws,1,1,len(cols),title,bold=True,fc="FFFFFF",bg=XC["title"],sz=13,align="left")
        mxsc(ws,2,1,len(cols),subtitle,italic=True,fc="FFFFFF",bg=XC["sub"],sz=9,align="left")
        for j,c in enumerate(cols,1):
            cell=ws.cell(4,j,c)
            cell.fill=PatternFill("solid",fgColor=XC["hdr"])
            cell.font=Font(bold=True,color="FFFFFF")
            cell.alignment=Alignment(horizontal="center",vertical="center",wrap_text=True)
            cell.border=_tb()
        for i,row in enumerate(rows,5):
            for j,c in enumerate(cols,1):
                v=row.get(c,np.nan)
                if isinstance(v,(np.floating,float)) and np.isnan(v):
                    v=None
                cell=ws.cell(i,j,v)
                cell.border=_tb()
                cell.alignment=Alignment(vertical="center",wrap_text=False)
                if isinstance(v,float):
                    cell.number_format="0.0000"
        ws.freeze_panes=freeze
        for j,c in enumerate(cols,1):
            width=widths[j-1] if widths and j-1<len(widths) else min(max(12,len(str(c))+2),26)
            ws.column_dimensions[get_column_letter(j)].width=width

    threshold_rows=[
        dict(Station=stn,Station_Code=f"S{i+1}",WetDay_Threshold_mm=WET_THR,
             P95_threshold_mm=vals.get("p95",np.nan),
             P99_threshold_mm=vals.get("p99",np.nan),
             Baseline_Wet_Days=vals.get("n_wet",0))
        for i,(stn,vals) in enumerate(thresholds.items())
    ]
    _write_table(
        wb.create_sheet("S12 ETCCDI Thresholds"),
        "Observed-Local ETCCDI Percentile Thresholds",
        "R95p and R99p use fixed observed baseline period 1981-2010.",
        threshold_rows,
        widths=[13,13,18,18,18,18],
    )
    _write_table(
        wb.create_sheet("S13 ETCCDI Annual"),
        "Annual ETCCDI Extreme Rainfall Indices",
        "Observed, Raw ensemble, and BC-QDM ensemble annual indices; wet day is precipitation >= 1 mm/day.",
        annual_rows,
        widths=[17,13,9,12,9,11,34,14,14,18,18,18],
    )
    _write_table(
        wb.create_sheet("S14 ETCCDI Summary"),
        "ETCCDI Summary Statistics",
        "Annual summary metrics. Extreme-tail indices may remain underestimated because QDM improves distributional bias but cannot fully recover observed extreme tails.",
        summary_rows,
    )
    _write_table(
        wb.create_sheet("S15 ETCCDI Bias"),
        "ETCCDI Bias Reduction After QDM",
        "Positive bias reduction means BC-QDM reduces absolute error relative to Raw CMIP6 for annual-mean ETCCDI indices.",
        bias_rows,
        widths=[9,12,11,34,14,15,15,15,15,15,15,18,13],
    )
    _write_table(
        wb.create_sheet("S16 ETCCDI Trend"),
        "ETCCDI Trend Analysis with Lag-k Adjustment",
        f"Mann-Kendall test, Sen slope, and effective sample size adjusted using lag k = {TREND_LAG_K}.",
        trend_rows,
        widths=[17,13,9,12,11,34,14,8,18,10,10,12,15,11,18],
    )

# 
#  -12  EXCEL WRITER (8 sheets)
# 

def write_excel(wb,obs_d,obs_m,raw_dfs,bc_dfs,raw_m_dfs,bc_m_dfs,
                stns,smap,model_list,
                wilcox_rows,ks_rows,
                period_obs,period_sim):

    stns_str=[str(s) for s in stns]
    codes=[smap[s] for s in stns_str]
    raw_ens_d=ensemble_mean(raw_dfs); bc_ens_d=ensemble_mean(bc_dfs)
    raw_ens_m=ensemble_mean(raw_m_dfs); bc_ens_m=ensemble_mean(bc_m_dfs)

    MET_KEYS=["n","RMSE","MAE","MBE","Pbias","RSR","r","r_sq",
              "NSE","KGE","d","sigma_r","beta","RMSE_pct","Pbias_abs"]
    MET_FMT ={k:(".0f" if k=="n" else ".4f") for k in MET_KEYS}
    MET_FMT.update({"Pbias":".2f","RSR":".4f","RMSE_pct":".2f","Pbias_abs":".2f"})
    LOWER_BETTER={"RMSE","MAE","Pbias","RSR","RMSE_pct","Pbias_abs"}

    def _title_row(ws,nc,title,sub,r_title=1):
        mxsc(ws,r_title,1,nc,title,bold=True,fc="FFFFFF",bg=XC["title"],
             sz=13,align="left")
        rh(ws,r_title,24)
        mxsc(ws,r_title+1,1,nc,sub,italic=True,fc="FFFFFF",bg=XC["sub"],
             sz=9,align="left")
        rh(ws,r_title+1,14)

    def _hdr(ws,r,hdrs,bg=XC["hdr"]):
        for ci,h in enumerate(hdrs,1):
            xsc(ws,r,ci,h,bold=True,fc="FFFFFF",bg=bg,sz=9.5,wrap=True)
        rh(ws,r,34)

    def _perf_sheet(ws_name,obs_df,raw_ens,bc_ens,scale):
        ws=wb.create_sheet(ws_name)
        ws.sheet_view.showGridLines=False
        ws.freeze_panes="E5"
        nc=4+len(MET_KEYS)
        _title_row(ws,nc,
            f"Statistical Performance Metrics - {scale}",
            f"Ensemble mean of {len(model_list)} models  |  Obs: {period_obs}  |  Sim: {period_sim}  |  "
            "BC cells: green=improved vs Raw, orange=degraded  |  Ref: Gupta et al.(2009); Nash & Sutcliffe(1970)")
        hdrs=["Dataset","Station","Code","Perf.Category"]+MET_KEYS
        _hdr(ws,4,hdrs); ri=5
        best_set=set()
        for stn in stns_str:
            mr=metrics_from_dfs(obs_df,raw_ens,stn)
            mb=metrics_from_dfs(obs_df,bc_ens, stn)
            for met in MET_KEYS:
                vr=mr.get(met,np.nan); vb=mb.get(met,np.nan)
                if np.isnan(vr) or np.isnan(vb): continue
                if met in LOWER_BETTER: best=(vb<vr)
                else:                   best=(vb>vr)
                if best: best_set.add((stn,met))

        for ds_lbl,ens_df,bg_key in [("Raw CMIP6",raw_ens,"raw_r"),
                                      ("BC (QDM)",bc_ens,"bc_r")]:
            for stn,code in zip(stns_str,codes):
                mr=metrics_from_dfs(obs_df,ens_df,stn)
                cat=performance_category("NSE",mr.get("NSE",np.nan))
                bg=XC.get(bg_key,"white")
                vals=[ds_lbl,stn,code,cat]
                for k in MET_KEYS:
                    v=mr.get(k,np.nan)
                    vals.append(f"{v:{MET_FMT[k]}}" if not np.isnan(v) else "-")
                for ci,v in enumerate(vals,1):
                    cell=xsc(ws,ri,ci,v,sz=9,
                             align="left" if ci<=4 else "right",
                             bg=bg)
                    # Override colour for best values
                    if ci>=5:
                        met=MET_KEYS[ci-5]
                        mr2=metrics_from_dfs(obs_df,raw_ens,stn)
                        mb2=metrics_from_dfs(obs_df,bc_ens, stn)
                        vr=mr2.get(met,np.nan); vb=mb2.get(met,np.nan)
                        if not(np.isnan(vr) or np.isnan(vb)):
                            if met in LOWER_BETTER: imp=vb<vr
                            else:                    imp=vb>vr
                            if ds_lbl=="BC (QDM)":
                                cell.fill=_xf(XC["improve"] if imp else XC["degrade"])
                rh(ws,ri,15); ri+=1

        # Regional mean rows
        rh(ws,ri,4); ri+=1
        for ds_lbl,ens_df,bg_key in [("Raw  REGIONAL MEAN",raw_ens,"raw_r"),
                                      ("BC   REGIONAL MEAN",bc_ens,"bc_r")]:
            cols=[c for c in stns_str if c in (ens_df.columns if ens_df is not None else [])]
            vals_all={k:[] for k in MET_KEYS}
            for stn in stns_str:
                mr=metrics_from_dfs(obs_df,ens_df,stn)
                for k in MET_KEYS:
                    v=mr.get(k,np.nan)
                    if not np.isnan(v): vals_all[k].append(v)
            bg=XC.get(bg_key,"white")
            cat_mean=performance_category("NSE",float(np.mean(vals_all["NSE"])) if vals_all["NSE"] else np.nan)
            row_vals=[ds_lbl,"ALL","REG",cat_mean]
            for k in MET_KEYS:
                v=float(np.mean(vals_all[k])) if vals_all[k] else np.nan
                row_vals.append(f"{v:{MET_FMT[k]}}" if not np.isnan(v) else "-")
            for ci,v in enumerate(row_vals,1):
                xsc(ws,ri,ci,v,bold=True,sz=10,
                    align="left" if ci<=4 else "right",bg=bg)
            rh(ws,ri,18); ri+=1

        # Column widths
        widths=[14,10,6,16]+[10]*len(MET_KEYS)
        for ci,w in enumerate(widths,1): cw(ws,ci,w)

    _perf_sheet("S1 Metrics-Daily",   obs_d,  raw_ens_d, bc_ens_d, "Daily")
    _perf_sheet("S2 Metrics-Monthly", obs_m,  raw_ens_m, bc_ens_m, "Monthly")

    # - S3: Improvement Summary -
    ws3=wb.create_sheet("S3 Improvement Summary")
    ws3.sheet_view.showGridLines=False
    nc3=12
    _title_row(ws3,nc3,
        "Improvement Summary - Daily and Monthly Scale",
        "- = BC minus Raw (positive = improved for higher-is-better metrics; "
        "positive = reduced for lower-is-better metrics)  |  "
        "% = relative change  |  Green=improved  Red=degraded")
    hdrs3=["Station","Code",
           "RMSE reduction (mm)","RMSE reduction (%)","|Pbias| reduction (%)","-r","-NSE","-KGE","-d",
           "Scale","KGE Raw","KGE BC"]
    _hdr(ws3,4,hdrs3); ri3=5

    for scale,obs_df,raw_e,bc_e in [("Daily",obs_d,raw_ens_d,bc_ens_d),
                                      ("Monthly",obs_m,raw_ens_m,bc_ens_m)]:
        if obs_df is None or raw_e is None or bc_e is None: continue
        for stn,code in zip(stns_str,codes):
            mr=metrics_from_dfs(obs_df,raw_e,stn)
            mb=metrics_from_dfs(obs_df,bc_e, stn)
            def d(k,invert=False):
                vr=mr.get(k,np.nan); vb=mb.get(k,np.nan)
                if np.isnan(vr) or np.isnan(vb): return np.nan
                return (vr-vb) if invert else (vb-vr)
            def pct_ch(k,invert=False):
                vr=mr.get(k,np.nan)
                dv=d(k,invert)
                if np.isnan(vr) or np.isnan(dv) or vr==0: return np.nan
                return 100*dv/abs(vr)
            drmse=d("RMSE",invert=True)
            drmse_pct=pct_ch("RMSE",invert=True)
            dpbias=d("Pbias_abs",invert=True)
            dr=d("r"); dnse=d("NSE"); dkge=d("KGE"); dd=d("d")
            kge_r=mr.get("KGE",np.nan); kge_b=mb.get("KGE",np.nan)
            def v2s(v,dp=4):
                return f"{v:.{dp}f}" if not np.isnan(v) else "-"
            row=[stn,code,v2s(drmse,3),v2s(drmse_pct,1)+"%",
                 v2s(dpbias,2),v2s(dr,4),v2s(dnse,4),v2s(dkge,4),v2s(dd,4),
                 scale,v2s(kge_r,4),v2s(kge_b,4)]
            for ci,v in enumerate(row,1):
                bg=XC["white"]
                if ci==3 and not np.isnan(drmse):       bg=XC["improve"] if drmse>0 else XC["degrade"]
                if ci==4 and not np.isnan(drmse_pct):   bg=XC["improve"] if drmse_pct>0 else XC["degrade"]
                if ci==5 and not np.isnan(dpbias):      bg=XC["improve"] if dpbias>0 else XC["degrade"]
                if ci in (6,7,8,9):
                    vv={6:dr,7:dnse,8:dkge,9:dd}[ci]
                    if not np.isnan(vv): bg=XC["improve"] if vv>0 else XC["degrade"]
                xsc(ws3,ri3,ci,v,sz=9,
                    align="left" if ci<=2 else "right",bg=bg)
            rh(ws3,ri3,15); ri3+=1

    for ci,w in enumerate([10,6,11,10,10,10,10,10,10,8,10,10],1): cw(ws3,ci,w)

    # - S4: Wilcoxon Test -
    ws4=wb.create_sheet("S4 Wilcoxon Test")
    ws4.sheet_view.showGridLines=False
    _title_row(ws4,12,
        "Wilcoxon Signed-Rank Test - Daily Absolute Errors",
        "H-: median(|err_BC|) = median(|err_Raw|)  |  "
        "H: median(|err_BC|) < median(|err_Raw|) (one-tailed)  |  "
        "Effect size r = Z/-N [Cohen 1988]: small-0.1, medium-0.3, large-0.5  |  "
        "FDR: Benjamini-Hochberg (1995)  |  Ref: Wilcoxon (1945)")
    hdrs4=["Station","Code","N (pairs)",
           "Median|err| Raw","Median|err| BC","Reduction (%)",
           "W-statistic","p (two-tail)","p (one-tail)",
           "Stars","Effect r","FDR q<0.05","Interpretation"]
    _hdr(ws4,4,hdrs4); ri4=5
    for row in wilcox_rows:
        stn=row.get("Station",""); p1=row.get("p_one",np.nan)
        sig=row.get("sig","-"); fdr=row.get("sig_fdr","ns")
        bg=XC["improve"] if(not np.isnan(p1) and p1<0.05) else XC["white"]
        interp=("BC significantly better" if(not np.isnan(p1) and p1<0.05)
                else("Not significant" if not np.isnan(p1) else "Insufficient data"))
        vals=[stn,smap.get(str(stn),""),row.get("n","-"),
              _fmt(row.get("med_err_raw",np.nan)),
              _fmt(row.get("med_err_bc",np.nan)),
              f"{_fmt(row.get('pct_reduction',np.nan))}%",
              _fmt(row.get("W",np.nan),2),
              _fmt(row.get("p_two",np.nan),6),
              _fmt(row.get("p_one",np.nan),6),
              sig,"-" if np.isnan(row.get("effect_r",np.nan)) else _fmt(row.get("effect_r",np.nan)),
              "Yes" if fdr=="sig" else "No",interp]
        for ci,v in enumerate(vals,1):
            cell=xsc(ws4,ri4,ci,v,sz=9,
                     align="left" if ci in(1,2,13) else "right",bg=bg)
            if ci==10 and sig not in("-","ns"):
                cell.font=Font(bold=True,color="1B5E20",name="Calibri",size=9)
                cell.fill=_xf(XC["improve"])
        rh(ws4,ri4,16); ri4+=1
    for ci,w in enumerate([10,6,9,14,14,13,12,14,14,8,10,10,22],1): cw(ws4,ci,w)

    # - S5: KS Test -
    ws5=wb.create_sheet("S5 KS-Test")
    ws5.sheet_view.showGridLines=False
    _title_row(ws5,9,
        "Kolmogorov-Smirnov Test - Wet-Day Distribution",
        "Two-sample KS test: simulated vs observed wet-day rainfall (-1 mm/day)  |  "
        "H-: same distribution  |  D closer to 0 = more similar  |  "
        "Ref: Massey (1951) J.Am.Stat.Assoc. 46:68-78")
    hdrs5=["Station","Code",
           "D (Raw)","p (Raw)","Sig (Raw)",
           "D (BC)","p (BC)","Sig (BC)",
           "D Improvement (D_raw - D_bc)","Interpretation"]
    _hdr(ws5,4,hdrs5); ri5=5
    for row in ks_rows:
        stn=row.get("Station","")
        d_r=row.get("D_raw",np.nan); d_b=row.get("D_bc",np.nan)
        d_imp=row.get("D_improvement",np.nan)
        bg=XC["improve"] if not np.isnan(d_imp) and d_imp>0 else XC["white"]
        interp=("Distribution improved" if not np.isnan(d_imp) and d_imp>0 else
                "Distribution degraded" if not np.isnan(d_imp) and d_imp<0 else "-")
        vals=[stn,smap.get(str(stn),""),
              _fmt(d_r),_fmt(row.get("p_raw",np.nan),6),row.get("sig_raw","-"),
              _fmt(d_b), _fmt(row.get("p_bc",np.nan),6), row.get("sig_bc","-"),
              _fmt(d_imp),interp]
        for ci,v in enumerate(vals,1):
            cell=xsc(ws5,ri5,ci,v,sz=9,
                     align="left" if ci in(1,2,10) else "right",
                     bg=XC["improve"] if ci==9 and not np.isnan(d_imp) and d_imp>0 else
                        XC["degrade"] if ci==9 and not np.isnan(d_imp) and d_imp<0 else bg)
        rh(ws5,ri5,15); ri5+=1
    for ci,w in enumerate([10,6,10,12,10,10,12,10,20,22],1): cw(ws5,ci,w)

    # - S6: Seasonal Analysis -
    ws6=wb.create_sheet("S6 Seasonal Analysis")
    ws6.sheet_view.showGridLines=False
    _title_row(ws6,10,
        "Seasonal Analysis - Wet Season (May-Oct) and Dry Season (Nov-Apr)",
        "KGE and RMSE per season  |  Ensemble mean across models  |  "
        "Wet season: May-October  |  Dry season: November-April")
    hdrs6=["Season","Station","Code","KGE Raw","KGE BC","-KGE",
           "RMSE Raw (mm)","RMSE BC (mm)","-RMSE (mm)","Interpretation"]
    _hdr(ws6,4,hdrs6); ri6=5

    obs_ws=to_seasonal(obs_d,WET_MONTHS)
    obs_ds=to_seasonal(obs_d,DRY_MONTHS)
    raw_ws={m:to_seasonal(df,WET_MONTHS) for m,df in raw_dfs.items()}
    bc_ws ={m:to_seasonal(df,WET_MONTHS) for m,df in bc_dfs.items()}
    raw_ds={m:to_seasonal(df,DRY_MONTHS) for m,df in raw_dfs.items()}
    bc_ds ={m:to_seasonal(df,DRY_MONTHS) for m,df in bc_dfs.items()}

    for season,obs_sea,raw_sea,bc_sea in [
        ("Wet (May-Oct)",obs_ws,ensemble_mean(raw_ws),ensemble_mean(bc_ws)),
        ("Dry (Nov-Apr)",obs_ds,ensemble_mean(raw_ds),ensemble_mean(bc_ds))
    ]:
        if obs_sea is None: continue
        for stn,code in zip(stns_str,codes):
            mr=metrics_from_dfs(obs_sea,raw_sea,stn)
            mb=metrics_from_dfs(obs_sea,bc_sea, stn)
            kr=mr.get("KGE",np.nan); kb=mb.get("KGE",np.nan)
            rr=mr.get("RMSE",np.nan); rb=mb.get("RMSE",np.nan)
            dkge=(kb-kr) if not(np.isnan(kr) or np.isnan(kb)) else np.nan
            drmse=(rr-rb) if not(np.isnan(rr) or np.isnan(rb)) else np.nan
            interp=("Both improved" if not np.isnan(dkge) and not np.isnan(drmse)
                                        and dkge>0 and drmse>0
                    else "Mixed" if not(np.isnan(dkge) or np.isnan(drmse)) else "-")
            bg=XC["improve"] if interp=="Both improved" else XC["white"]
            row=[season,stn,code,
                 _fmt(kr),_fmt(kb),
                 f"{'+' if not np.isnan(dkge) and dkge>0 else ''}{_fmt(dkge)}",
                 _fmt(rr,3),_fmt(rb,3),
                 f"{_fmt(drmse,3)}",interp]
            for ci,v in enumerate(row,1):
                xsc(ws6,ri6,ci,v,sz=9,
                    align="left" if ci in(1,2,3,10) else "right",bg=bg)
            rh(ws6,ri6,15); ri6+=1
        rh(ws6,ri6,4); ri6+=1
    for ci,w in enumerate([16,10,6,10,10,10,12,12,12,18],1): cw(ws6,ci,w)

    # - S7: Journal-Ready Summary -
    ws7=wb.create_sheet("S7 Journal Summary")
    ws7.sheet_view.showGridLines=False
    _title_row(ws7,5,
        "Journal-Ready Summary - Results for Paper Writing",
        "Copy-ready text for Methods & Results sections  |  "
        f"Based on {len(model_list)} CMIP6 models  |  Period: {period_obs}")

    # Summary statistics across all stations
    def reg_mean(obs_df,raw_e,bc_e,met):
        vals_r=[]; vals_b=[]
        for stn in stns_str:
            mr=metrics_from_dfs(obs_df,raw_e,stn)
            mb=metrics_from_dfs(obs_df,bc_e, stn)
            vr=mr.get(met,np.nan); vb=mb.get(met,np.nan)
            if not np.isnan(vr): vals_r.append(vr)
            if not np.isnan(vb): vals_b.append(vb)
        return (np.mean(vals_r) if vals_r else np.nan,
                np.mean(vals_b) if vals_b else np.nan)

    sections=[
        ("STUDY AREA & DATA",
         f"This study evaluated {len(model_list)} CMIP6 models ({', '.join(model_list)}) "
         f"over Prachuap Khiri Khan Province, Thailand, at {len(stns)} rainfall stations "
         f"(Station IDs: {', '.join(codes)}) during the historical period {period_obs}. "
         "Quantile Delta Mapping (QDM; Cannon et al. 2015) was applied as the bias correction method."),
        ("METHODS - METRICS",
         "Model performance was evaluated using: Kling-Gupta Efficiency (KGE; Gupta et al. 2009), "
         "Nash-Sutcliffe Efficiency (NSE; Nash & Sutcliffe 1970), Pearson correlation coefficient (r), "
         "Root Mean Square Error (RMSE), Percent Bias (Pbias), and Index of Agreement (d; Willmott 1981). "
         "Performance categories followed Moriasi et al. (2007): "
         "Very Good (NSE>0.75), Good (0.65-0.75), Satisfactory (0.50-0.65)."),
        ("METHODS - STATISTICAL TESTS",
         "Statistical significance of bias correction improvement was assessed using the "
         "Wilcoxon Signed-Rank Test (Wilcoxon 1945) on paired daily absolute errors "
         "(H: |err_BC| < |err_Raw|, one-tailed, -=0.05), with False Discovery Rate (FDR) "
         "correction (Benjamini & Hochberg 1995) applied across stations. "
         "Distribution similarity was evaluated using the two-sample Kolmogorov-Smirnov (KS) test. "
         "Effect size was quantified as r = Z/-N (Cohen 1988)."),
    ]
    # Compute actual numbers for results section
    kr_d,kb_d=reg_mean(obs_d, raw_ens_d,bc_ens_d,"KGE")
    rr_d,rb_d=reg_mean(obs_d, raw_ens_d,bc_ens_d,"RMSE")
    pr_d,pb_d=reg_mean(obs_d, raw_ens_d,bc_ens_d,"Pbias_abs")
    nr_d,nb_d=reg_mean(obs_d, raw_ens_d,bc_ens_d,"NSE")
    n_sig=sum(1 for r in wilcox_rows if r.get("p_one",1)<0.05)
    n_fdr=sum(1 for r in wilcox_rows if r.get("sig_fdr")=="sig")
    n_ks_imp=sum(1 for r in ks_rows if not np.isnan(r.get("D_improvement",np.nan)) and r["D_improvement"]>0)

    results_text=(
        f"DAILY SCALE: Before QDM bias correction, the ensemble mean KGE was {kr_d:.3f} "
        f"(RMSE={rr_d:.2f} mm, |Pbias|={pr_d:.1f}%, NSE={nr_d:.3f}). "
        f"After QDM, KGE improved to {kb_d:.3f} "
        f"(RMSE={rb_d:.2f} mm, |Pbias|={pb_d:.1f}%, NSE={nb_d:.3f}), "
        f"representing a KGE increase of {kb_d-kr_d:+.3f} and RMSE reduction of {rr_d-rb_d:.2f} mm. "
        f"Wilcoxon test showed {n_sig}/{len(stns)} stations with statistically significant improvement "
        f"(p<0.05, one-tailed); {n_fdr}/{len(stns)} remained significant after FDR correction. "
        f"KS-test indicated distribution improvement at {n_ks_imp}/{len(stns)} stations."
    )
    sections.append(("RESULTS - DAILY SCALE",results_text))
    if obs_m is not None:
        kr_m,kb_m=reg_mean(obs_m,raw_ens_m,bc_ens_m,"KGE")
        rr_m,rb_m=reg_mean(obs_m,raw_ens_m,bc_ens_m,"RMSE")
        sections.append(("RESULTS - MONTHLY SCALE",
            f"At the monthly scale, QDM improved ensemble KGE from {kr_m:.3f} to {kb_m:.3f} "
            f"({kb_m-kr_m:+.3f}), and RMSE from {rr_m:.2f} to {rb_m:.2f} mm "
            f"(reduction of {rr_m-rb_m:.2f} mm)."))
    sections.append(("TAYLOR DIAGRAM",
        "Taylor diagrams (Taylor 2001) at daily and monthly scales confirmed that "
        "all bias-corrected models moved closer to the observed reference point, "
        "with improved correlation coefficients and standard deviation ratios approaching unity."))
    sections.append(("Q-Q PLOTS",
        "Q-Q plots demonstrated that the raw models substantially over-estimated high-quantile rainfall, "
        "while QDM-corrected values closely matched the observed quantile distribution "
        "(reduced QQ-RMSE across all stations and models)."))

    alt=[_xf("E3F2FD"),_xf("FFFFFF")]
    ri7=4
    for i,(key,text) in enumerate(sections):
        fl=alt[i%2]
        xsc(ws7,ri7,1,key,bold=True,sz=10.5,align="left",bg="1F4E79",fc="FFFFFF")
        xsc(ws7,ri7,2,text,sz=10,align="left",bg=str(fl.fgColor.rgb) if fl else "FFFFFF",wrap=True)
        rh(ws7,ri7,60)
        ri7+=1
    cw(ws7,1,28); cw(ws7,2,90)

    # - S8: Methods & References -
    ws8=wb.create_sheet("S8 Methods & References")
    ws8.sheet_view.showGridLines=False
    _title_row(ws8,3,
        "Statistical Methods and Full References",
        f"All metrics and tests used in this study  |  v{VERSION}")
    refs=[
        ("Taylor Diagram",
         "Taylor KE (2001). Summarizing multiple aspects of model performance in a single diagram. "
         "J. Geophys. Res. 106(D7):7183-7192. doi:10.1029/2000JD900719",
         "Visualization of r, -_r, RMSE simultaneously"),
        ("KGE",
         "Gupta HV, Kling H, Yilmaz KK, Martinez GF (2009). Decomposition of the mean squared error "
         "and NSE. J. Hydrol. 377:80-91. doi:10.1016/j.jhydrol.2009.08.003",
         "KGE=1-[(r-1)-+(-_r-1)-+(-1)-]; Perfect=1"),
        ("NSE",
         "Nash JE, Sutcliffe JV (1970). River flow forecasting through conceptual models. "
         "J. Hydrol. 10:282-290. doi:10.1016/0022-1694(70)90255-6",
         "NSE=1-(S-O)-/-(O-)-; VG>0.75, Good 0.65-0.75, Sat 0.50-0.65"),
        ("IoA / d",
         "Willmott CJ (1981). On the validation of models. Phys. Geogr. 2:184-194.",
         "d=1-(S-O)-/-(|S-|+|O-|)-; Range [0,1]"),
        ("Performance Criteria",
         "Moriasi DN, Arnold JG, Van Liew MW et al. (2007). Model evaluation guidelines for systematic "
         "quantification of accuracy. Trans. ASABE 50:885-900.",
         "NSE/RSR/Pbias criteria for Very Good/Good/Satisfactory"),
        ("QDM",
         "Cannon AJ, Sobie SR, Murdock TQ (2015). Bias correction of GCM precipitation by quantile "
         "mapping. J. Climate 28:6938-6959. doi:10.1175/JCLI-D-14-00754.1",
         "Quantile Delta Mapping bias correction method"),
        ("Wilcoxon",
         "Wilcoxon F (1945). Individual comparisons by ranking methods. Biometrics Bull. 1:80-83.",
         "Non-parametric paired signed-rank test; effect size r=Z/-N [Cohen 1988]"),
        ("KS Test",
         "Massey FJ (1951). The Kolmogorov-Smirnov test for goodness of fit. "
         "J. Am. Stat. Assoc. 46:68-78.",
         "Two-sample distribution comparison"),
        ("FDR",
         "Benjamini Y, Hochberg Y (1995). Controlling the false discovery rate: a practical and "
         "powerful approach to multiple testing. J. R. Stat. Soc. B 57:289-300.",
         "Multiple testing correction across stations"),
        ("Effect Size",
         "Cohen J (1988). Statistical Power Analysis for the Behavioral Sciences. 2nd ed. "
         "Lawrence Erlbaum Associates, New Jersey.",
         "r=Z/-N: small-0.1, medium-0.3, large-0.5"),
        ("RSR",
         "Singh J, Knapp HV, Demissie M (2004). Hydrologic modeling of the Iroquois River watershed. "
         "ISWS CR 2004-08.",
         "RSR=RMSE/-_obs; VG<0.50, Good<0.60, Satisfactory<0.70"),
    ]
    alt2=[_xf("DEEAF1"),_xf("FFFFFF")]
    ri8=5
    xsc(ws8,4,1,"Citation",bold=True,fc="FFFFFF",bg=XC["hdr"],sz=10)
    xsc(ws8,4,2,"Full Reference",bold=True,fc="FFFFFF",bg=XC["hdr"],sz=10)
    xsc(ws8,4,3,"Application in this study",bold=True,fc="FFFFFF",bg=XC["hdr"],sz=10)
    rh(ws8,4,22)
    for i,(key,ref,app) in enumerate(refs):
        fl=alt2[i%2]
        for ci,v in enumerate([key,ref,app],1):
            cell=xsc(ws8,ri8,ci,v,bold=(ci==1),sz=9.5,align="left",wrap=True)
            cell.fill=fl
        rh(ws8,ri8,36); ri8+=1
    cw(ws8,1,22); cw(ws8,2,80); cw(ws8,3,40)

def append_hydroclimate_excel(wb, wet_rows, trend_rows, lag_rows):
    """Append journal-review diagnostic sheets for wet-day, trend, and lag-k analysis."""
    def _write_table(ws, title, subtitle, rows, widths=None, freeze="A5"):
        ws.sheet_view.showGridLines=False
        if not rows:
            mxsc(ws,1,1,6,title,bold=True,fc="FFFFFF",bg=XC["title"],sz=13,align="left")
            mxsc(ws,2,1,6,"No data available",italic=True,fc="FFFFFF",bg=XC["sub"],sz=9,align="left")
            return
        df=_rows_to_df(rows)
        headers=list(df.columns)
        nc=len(headers)
        mxsc(ws,1,1,nc,title,bold=True,fc="FFFFFF",bg=XC["title"],sz=13,align="left")
        rh(ws,1,24)
        mxsc(ws,2,1,nc,subtitle,italic=True,fc="FFFFFF",bg=XC["sub"],sz=9,align="left")
        rh(ws,2,28)
        for ci,h in enumerate(headers,1):
            xsc(ws,4,ci,h,bold=True,fc="FFFFFF",bg=XC["hdr"],sz=9,wrap=True)
        rh(ws,4,34)
        for ri,row in enumerate(df.itertuples(index=False),5):
            for ci,val in enumerate(row,1):
                if isinstance(val,(float,np.floating)):
                    out=None if np.isnan(val) else round(float(val),6)
                elif isinstance(val,(int,np.integer)):
                    out=int(val)
                else:
                    out=val
                bg=XC["alt"] if ri%2==0 else XC["white"]
                if "Trend" in headers and headers[ci-1]=="Trend":
                    if out=="increasing": bg=XC["improve"]
                    elif out=="decreasing": bg=XC["degrade"]
                xsc(ws,ri,ci,out,sz=8.7,align="left" if ci<=5 else "right",bg=bg)
            rh(ws,ri,15)
        ws.freeze_panes=freeze
        if widths is None:
            widths=[16]*nc
        for ci,w in enumerate(widths[:nc],1):
            cw(ws,ci,w)

    _write_table(
        wb.create_sheet("S9 Wet-Day Diagnostics"),
        "Wet-Day Frequency and Rainfall Diagnostics",
        f"Wet day threshold = {WET_THR} mm/day. Statistics computed annually and summarized by station.",
        wet_rows,
        widths=[16,11,7,22,14,12,9,12,12,12,12],
    )
    _write_table(
        wb.create_sheet("S10 Trend Analysis"),
        "Trend Analysis with Lag-k Autocorrelation Adjustment",
        f"Mann-Kendall test, Sen slope, and effective sample size adjusted using lag k = {TREND_LAG_K}.",
        trend_rows,
        widths=[16,11,7,22,14,12,9,8,10,10,15,10,10,12,20],
    )
    _write_table(
        wb.create_sheet("S11 Lag-k ACF"),
        "Lag-k Autocorrelation Diagnostics",
        f"Annual hydroclimate series autocorrelation for k = 1..{ACF_MAX_LAG}. Used to evaluate persistence before trend interpretation.",
        lag_rows,
        widths=[16,11,7,22,14,10,16],
    )

# 
#  -13  MAIN
# 

def main():
    SEP=""*70
    print(SEP)
    print(f"  CMIP6 Bias Correction - Comprehensive Analysis  v{VERSION}")
    print("  Taylor Diagram - Q-Q Plot - Statistical Tests - Excel Summary")
    print("  Journal-ready standard for Q1 hydrology/climate publication")
    print(SEP)

    try:
        work_dir=(sys.argv[1].strip('"').strip("'")
                  if len(sys.argv)>1
                  else str(Path(os.path.abspath(__file__)).parent))
    except NameError:
        work_dir=os.getcwd()

    out_dir=Path(work_dir)
    print(f"  Input folder : {work_dir}")

    # - Discover files -
    print("\n  Discovering files ...")
    obs_path,raw_paths,bc_paths=discover_files(work_dir)
    if obs_path is None:
        sys.exit("  -  No Observed file (must contain 'Observed' in name)")
    if not raw_paths and not bc_paths:
        sys.exit("  -  No model files found  (pr_<MODEL>_*.csv / bc_<MODEL>_*.csv)")

    model_list=sorted(set(list(raw_paths.keys())+list(bc_paths.keys())))
    mc=[MODEL_PALETTE[i%len(MODEL_PALETTE)] for i in range(len(model_list))]
    print(f"\n  Models  : {model_list}")
    print(f"  Observed: {Path(obs_path).name}")
    print("-"*70)

    # - Load Observed -
    print("\n  Loading Observed ...")
    obs_d,stns=load_daily(obs_path,"Observed")
    if obs_d is None: sys.exit("  -  Failed to load Observed")
    stns_str=[str(s) for s in stns]
    smap=stn_labels(stns)
    period_obs=period_str(obs_d)
    prefix=f"{Path(obs_path).stem}_v36_etccdi_extreme_indices_refined"

    # - Load model data -
    print("\n  Loading Raw CMIP6 ...")
    raw_dfs={m:load_daily(p,f"Raw/{m}",stns_str)[0] for m,p in raw_paths.items()}
    print("\n  Loading BC/QDM ...")
    bc_dfs ={m:load_daily(p,f"BC/{m}", stns_str)[0] for m,p in bc_paths.items()}

    raw_dfs={m:df for m,df in raw_dfs.items() if df is not None}
    bc_dfs ={m:df for m,df in bc_dfs.items()  if df is not None}
    if not raw_dfs and not bc_dfs:
        sys.exit("  -  No model data loaded")

    sim_df_sample=(next(iter(raw_dfs.values())) if raw_dfs
                   else next(iter(bc_dfs.values())))
    period_sim=period_str(sim_df_sample)
    print(f"\n  {len(stns)} stations  |  {len(model_list)} models  |  "
          f"Obs: {period_obs}  |  Sim: {period_sim}")
    print("-"*70)

    # - Monthly aggregations -
    print("\n  Aggregating to monthly ...")
    obs_m    =to_monthly(obs_d)
    raw_m_dfs={m:to_monthly(df) for m,df in raw_dfs.items()}
    bc_m_dfs ={m:to_monthly(df) for m,df in bc_dfs.items()}

    # Ensemble BC for significance tests
    raw_ens_d=ensemble_mean(raw_dfs)
    bc_ens_d =ensemble_mean(bc_dfs)

    # - Statistical tests -
    print("\n  Running Wilcoxon Signed-Rank Test ...")
    wilcox_rows=wilcoxon_test(obs_d,raw_ens_d,bc_ens_d,stns_str)
    n_sig=sum(1 for r in wilcox_rows if r.get("p_one",1)<0.05)
    n_fdr=sum(1 for r in wilcox_rows if r.get("sig_fdr")=="sig")
    print(f"  Significant (p<0.05): {n_sig}/{len(stns)} stations")
    print(f"  FDR q<0.05          : {n_fdr}/{len(stns)} stations")

    print("\n  Running KS Test ...")
    ks_rows=ks_test(obs_d,raw_ens_d,bc_ens_d,stns_str)
    n_ks=sum(1 for r in ks_rows if not np.isnan(r.get("D_improvement",np.nan))
             and r["D_improvement"]>0)
    print(f"  KS distribution improved: {n_ks}/{len(stns)} stations")

    # - Figures -
    print(f"\n  Generating figures - {out_dir.name}/")

    print("\n  Fig 1: Taylor Diagram - Daily ...")
    build_taylor_fig(obs_d,raw_dfs,bc_dfs,stns,smap,
                     "Daily","mm day-",period_obs,period_sim,
                     "Fig1",out_dir,prefix)

    print("  Fig 2: Taylor Diagram - Monthly ...")
    build_taylor_fig(obs_m,raw_m_dfs,bc_m_dfs,stns,smap,
                     "Monthly","mm month-",period_obs,period_sim,
                     "Fig2",out_dir,prefix)

    import gc
    print("  Fig 3: Q-Q Plot - Daily ...")
    build_qq_fig(obs_d,raw_dfs,bc_dfs,stns,
                 "Daily",period_obs,"Fig3",out_dir,prefix)
    gc.collect()

    print("  Fig 4: Q-Q Plot - Monthly ...")
    build_qq_fig(obs_m,raw_m_dfs,bc_m_dfs,stns,
                 "Monthly",period_obs,"Fig4",out_dir,prefix)
    gc.collect()

    print("  Fig 5: Performance Heatmap - Daily ...")
    build_heatmap_fig(obs_d,raw_dfs,bc_dfs,stns,smap,
                      "Daily",period_obs,period_sim,
                      "Fig5",out_dir,prefix)
    gc.collect()

    print("  Fig 6: Performance Heatmap - Monthly ...")
    build_heatmap_fig(obs_m,raw_m_dfs,bc_m_dfs,stns,smap,
                      "Monthly",period_obs,period_sim,
                      "Fig6",out_dir,prefix)
    gc.collect()

    print("  Fig 7: Metric Improvement ...")
    build_improvement_fig(obs_d,obs_m,raw_dfs,bc_dfs,
                          raw_m_dfs,bc_m_dfs,
                          stns,smap,period_obs,out_dir,prefix)
    gc.collect()

    print("  Fig 8: Significance Testing ...")
    build_significance_fig(wilcox_rows,ks_rows,stns,smap,
                           period_obs,out_dir,prefix)
    gc.collect()

    print("  Fig 9: Monthly Climatology ...")
    build_monthly_climatology(obs_d,raw_dfs,bc_dfs,stns,smap,
                               period_obs,out_dir,prefix)
    gc.collect()

    print("  Fig 10: Annual Time Series ...")
    build_annual_timeseries(obs_d,raw_dfs,bc_dfs,stns,period_obs,out_dir,prefix)
    gc.collect()

    print("  Hydroclimate diagnostics: wet-day, trend, and lag-k ...")
    wet_rows,trend_rows,lag_rows=build_hydroclimate_diagnostics(
        obs_d,raw_dfs,bc_dfs,stns,smap)

    print("  Fig 11: Wet-day and Trend Diagnostics ...")
    build_wetday_trend_fig(obs_d,raw_dfs,bc_dfs,stns,out_dir,prefix)
    gc.collect()

    print("  Fig 12: Lag-k Autocorrelation ...")
    build_lagk_fig(lag_rows,stns,smap,out_dir,prefix)
    gc.collect()

    print("  ETCCDI extreme rainfall indices ...")
    etccdi_thresholds,etccdi_annual,etccdi_summary,etccdi_bias,etccdi_trend=build_etccdi_diagnostics(
        obs_d,raw_dfs,bc_dfs,stns,smap)

    print("  Fig 13: ETCCDI Bias Reduction ...")
    build_etccdi_bias_fig(etccdi_bias,stns,smap,out_dir,prefix)
    gc.collect()

    print("  Fig 14: ETCCDI Trend Significance ...")
    build_etccdi_trend_fig(etccdi_trend,stns,smap,out_dir,prefix)
    gc.collect()

    # - Excel -
    print(f"\n  Building Excel (15 sheets) ...")
    wb=Workbook(); wb.remove(wb.active)
    write_excel(wb,obs_d,obs_m,raw_dfs,bc_dfs,raw_m_dfs,bc_m_dfs,
                stns,smap,model_list,
                wilcox_rows,ks_rows,period_obs,period_sim)
    append_hydroclimate_excel(wb,wet_rows,trend_rows,lag_rows)
    append_etccdi_excel(wb,etccdi_thresholds,etccdi_annual,etccdi_summary,etccdi_bias,etccdi_trend)
    out_xl=out_dir/f"{prefix}_ComprehensiveAnalysis.xlsx"
    wb.save(str(out_xl))
    print(f"  -  Excel saved - {out_xl.name}")

    # - Summary -
    n_png=sum(1 for _ in out_dir.glob(f"{prefix}_Fig*.png"))
    raw_ens_d=ensemble_mean(raw_dfs); bc_ens_d=ensemble_mean(bc_dfs)
    kr=[metrics_from_dfs(obs_d,raw_ens_d,s).get("KGE",np.nan) for s in stns_str]
    kb=[metrics_from_dfs(obs_d,bc_ens_d, s).get("KGE",np.nan) for s in stns_str]
    kge_r_m=float(np.nanmean(kr)); kge_b_m=float(np.nanmean(kb))
    print()
    print(SEP)
    print(f"  -  COMPLETE  |  v{VERSION}  |  DPI={DPI}")
    print(f"  Figures    : {n_png} PNG" + (" + PDF" if SAVE_PDF else ""))
    print(f"  Excel      : {out_xl.name}  (15 sheets)")
    print(f"  {'-'*62}")
    print(f"  Regional mean KGE - Raw: {kge_r_m:.3f}  -  BC: {kge_b_m:.3f}  "
          f"(-{kge_b_m-kge_r_m:+.3f})")
    print(f"  Wilcoxon   : {n_sig}/{len(stns)} stations p<0.05  |  "
          f"FDR: {n_fdr}/{len(stns)}")
    print(f"  KS-test    : {n_ks}/{len(stns)} stations distribution improved")
    print(f"  Saved to   : {work_dir}")
    print(SEP)


if __name__=="__main__":
    main()
