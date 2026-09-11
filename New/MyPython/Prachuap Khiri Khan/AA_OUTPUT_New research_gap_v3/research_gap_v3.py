"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Research Gap Analysis  —  Version 3.1  (Bug-Fix + Significance Testing)    ║
║  "Does QDM Bias Correction Improve Station-Scale Rainfall Representation?"   ║
║  Multi-Model | Multi-Station | Multi-Scale (Daily / Monthly / Wet-Season)   ║
║  มาตรฐาน Nature / Elsevier / Q1–Q4 / TCI1                                  ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Fixes & Improvements over v2:                                               ║
║  [1] ROBUST model-name extraction — handles pr_day_MODEL_*.csv AND          ║
║       bc_pr_day_MODEL_*.csv nested-prefix patterns   [BUG FIX v3.1]        ║
║  [2] DPI=600, vector PDF output alongside PNG for publication                ║
║  [3] NO emoji medals in any figure — replaced with text rank labels          ║
║  [4] X-axis labels at 0° (horizontal) — wider figures, no overlap           ║
║  [5] CORRECT Skill Score: SS=1−ΣE_model/ΣE_clim (not mean of per-station)  ║
║  [6] Seasonal analysis added (Wet Season May–Oct) alongside Daily/Monthly    ║
║  [7] Distance-Decay Relationship (Physical Consistency test)                 ║
║  [8] Mantel Test (statistical Distance vs. Correlation matrix comparison)    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Input (same folder as script):                                              ║
║    Observed  → filename contains "observed" (case-insensitive)               ║
║    Raw CMIP6 → pr_*.csv  (e.g. pr_day_ACCESS-ESM1-5_hist.csv)               ║
║    BC/QDM    → bc_*.csv  (e.g. bc_day_ACCESS-ESM1-5_hist.csv)               ║
║    Coords    → station_coordinates.csv  [optional, enables Distance-Decay]   ║
║               Columns: StationID, Latitude, Longitude                        ║
║                                                                              ║
║  Output (same folder):                                                       ║
║    Output_RGv3_<name>.xlsx                (10 sheets)                       ║
║    Output_RGv3_<name>_Fig*.png / .pdf     (figures + sub-panels)            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  References:                                                                 ║
║    Taylor (2001) J. Geophys. Res. 106:7183–7192                             ║
║    Karl et al. (1999) Int. J. Climatol. 19:405–420   [ETCCDI]               ║
║    Gupta et al. (2009) J. Hydrol. 377:80–91           [KGE]                 ║
║    Nash & Sutcliffe (1970) J. Hydrol. 10:282–290      [NSE]                 ║
║    Gleckler et al. (2008) J. Geophys. Res. 113        [SS/RPI]              ║
║    Cannon et al. (2015) J. Climate 28:6938–6959       [QDM]                 ║
║    Mantel (1967) Cancer Res. 27:209–220               [Mantel Test]          ║
║    Maraun & Widmann (2018) Statistical Downscaling                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os, sys, re, math, warnings
import numpy as np
import pandas as pd
from pathlib import Path
from itertools import combinations
from scipy import stats as sps
from scipy.stats import gaussian_kde, pearsonr, spearmanr, wilcoxon as scipy_wilcoxon

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker
import matplotlib.gridspec as gridspec
import matplotlib.colors as mcolors
from matplotlib.lines  import Line2D
from matplotlib.colors import Normalize
import matplotlib.cm    as cm

from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils   import get_column_letter

warnings.filterwarnings("ignore")

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  0.  GLOBAL CONSTANTS & PUBLICATION STYLE                               ║
# ╚══════════════════════════════════════════════════════════════════════════╝

WET_THR    = 1.0           # mm/day — WMO wet-day threshold
WET_MONTHS = [5,6,7,8,9,10]  # May–October
DRY_MONTHS = [11,12,1,2,3,4]
MONTH_ABBR = ["Jan","Feb","Mar","Apr","May","Jun",
              "Jul","Aug","Sep","Oct","Nov","Dec"]
N_MANTEL   = 999           # permutations for Mantel test
SAVE_PDF   = True          # also save vector PDF alongside PNG
DPI        = 600           # publication-grade resolution

# ── CMIP6 temporal-resolution tokens to skip in model-name extraction ──────
_SKIP_TOKENS = {
    "day","mon","yr","6hr","3hr","1hr","fx","clim",
    "daily","monthly","annual","seasonal","hist","historical",
    "ssp245","ssp585","ssp126","rcp45","rcp85",
}

# ── Publication-grade Matplotlib style (Times New Roman, no emoji) ─────────
plt.rcParams.update({
    "font.family":          "serif",
    "font.serif":           ["Times New Roman", "DejaVu Serif"],
    "font.size":            12,
    "axes.titlesize":       13,
    "axes.labelsize":       12,
    "xtick.labelsize":      11,
    "ytick.labelsize":      11,
    "legend.fontsize":      10.5,
    "figure.titlesize":     14,
    "lines.linewidth":      1.8,
    "axes.linewidth":       0.9,
    "axes.spines.top":      False,
    "axes.spines.right":    False,
    "axes.grid":            True,
    "grid.linestyle":       "--",
    "grid.linewidth":       0.4,
    "grid.alpha":           0.45,
    "grid.color":           "#B0BEC5",
    "savefig.dpi":          DPI,
    "savefig.bbox":         "tight",
    "savefig.pad_inches":   0.15,
    "figure.dpi":           120,
    "mathtext.fontset":     "stix",
    "pdf.fonttype":         42,   # TrueType in PDF (editable in Illustrator)
    "ps.fonttype":          42,
})

# Colour palette (colour-blind safe)
C = dict(
    obs    = "#1B2838",   obs_lt = "#BDC3C7",
    raw    = "#C62828",   raw_lt = "#FFCDD2",
    bc     = "#1565C0",   bc_lt  = "#BBDEFB",
    green  = "#1E8449",   gold   = "#F57F17",
    grey   = "#607D8B",   purple = "#6A1B9A",
    wet    = "#1565C0",   dry    = "#E65100",
)
DS_LABELS = ["Observed", "Raw CMIP6", "Bias-Corrected (QDM)"]
DS_COLORS = [C["obs"],   C["raw"],    C["bc"]]
DS_LT     = [C["obs_lt"],C["raw_lt"], C["bc_lt"]]

# ── Excel style helpers ────────────────────────────────────────────────────
XC = dict(
    title  = "13293D", sub    = "1F4E79", hdr    = "2E75B6",
    obs_r  = "E8F5E9", raw_r  = "FFEBEE", bc_r   = "E3F2FD",
    best   = "FFF9C4", best_f = "E65100",
    improve= "C8E6C9", degrade= "FFCCBC",
    note   = "ECEFF1", white  = "FFFFFF", alt    = "F5F5F5",
    wet_s  = "DDEEFF", ext_s  = "FFF3E0",
)
THIN = Side(style="thin",   color="BDBDBD")
MED  = Side(style="medium", color="1F4E79")

def tb():  return Border(left=THIN, right=THIN, top=THIN,  bottom=THIN)
def xfill(h): return PatternFill("solid", fgColor=h)

def xsc(ws, r, c, val=None, bold=False, italic=False,
        fc=None, bg=None, align="center", sz=10, wrap=True, border=None):
    cell = ws.cell(row=r, column=c)
    if val is not None: cell.value = val
    cell.font = Font(bold=bold, italic=italic, name="Calibri", size=sz,
                     color=fc if fc else "1A1A1A")
    cell.alignment = Alignment(horizontal=align, vertical="center",
                                wrap_text=wrap)
    if bg:     cell.fill = xfill(bg)
    if border: cell.border = border
    return cell

def mxsc(ws, r, c1, c2, val, **kw):
    ws.merge_cells(start_row=r, start_column=c1, end_row=r, end_column=c2)
    return xsc(ws, r, c1, val, **kw)

def cw(ws, col, w):
    ws.column_dimensions[get_column_letter(col)].width = w


def savefig(fig, path_noext, tight=True):
    """Save figure as both PNG (DPI=600) and PDF (vector)."""
    kw = dict(bbox_inches="tight" if tight else None,
              pad_inches=0.15)
    fig.savefig(f"{path_noext}.png", dpi=DPI, **kw)
    if SAVE_PDF:
        fig.savefig(f"{path_noext}.pdf", **kw)
    plt.close(fig)
    print(f"    ✓  {Path(path_noext).name}.png" +
          (" + .pdf" if SAVE_PDF else ""))

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  1.  FILE DISCOVERY — ROBUST MULTI-MODEL AWARE                          ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def _extract_model_name(filepath: str, prefix: str) -> str:
    """
    Robustly extract CMIP6 model name from filename.

    Handles ALL patterns including nested prefixes:
      pr_ACCESS_daily.csv                          → ACCESS
      pr_day_ACCESS-ESM1-5_hist.csv               → ACCESS-ESM1-5
      bc_day_EC-Earth3_ssp245.csv                  → EC-Earth3
      bc_MIROC6_daily_1981_2014.csv                → MIROC6
      bc_pr_day_ACCESS-ESM1-5_historical_...csv   → ACCESS-ESM1-5  [FIX]
      bc_pr_day_CanESM5_historical_...csv          → CanESM5        [FIX]

    Strategy:
      1. Strip the primary prefix (pr_ or bc_) case-insensitively.
      2. BC files may have an additional nested "pr_" sub-prefix
         (e.g. bc_pr_day_MODEL_...). Strip that too so "pr" is not
         mistaken for the model name.
      3. Skip known CMIP6 temporal/experiment tokens in _SKIP_TOKENS.
      4. Return the first remaining token — that is the model name.
    """
    stem = Path(filepath).stem

    # Step 1: Strip primary prefix (pr_ or bc_)
    body = re.sub(rf"^{re.escape(prefix)}_?", "", stem, flags=re.IGNORECASE)

    # Step 2: BC files with nested "pr_" sub-prefix  (bc_pr_day_MODEL_...)
    if prefix.lower() == "bc":
        body = re.sub(r"^pr_?", "", body, flags=re.IGNORECASE)

    # Step 3: Tokenise and skip known non-model tokens
    parts = [p for p in body.split("_") if p]   # drop empty strings
    for part in parts:
        if part.lower() not in _SKIP_TOKENS:
            return part

    # Fallback
    return parts[0] if parts else "UnknownModel"


def discover_files(folder: str):
    """
    Scan folder and return:
        obs_path   : str   — single Observed file
        raw_models : dict  — {model_name: path}
        bc_models  : dict  — {model_name: path}

    Naming rules:
        Observed  : *observed* (case-insensitive)
        Raw CMIP6 : pr_*.csv
        BC/QDM    : bc_*.csv
    """
    all_csv = sorted(Path(folder).glob("*.csv"))

    obs_files = [f for f in all_csv if "observed" in f.name.lower()]
    raw_files = [f for f in all_csv if f.name.lower().startswith("pr")]
    bc_files  = [f for f in all_csv if f.name.lower().startswith("bc")]

    obs_path = None
    if not obs_files:
        print("  ✗  ไม่พบไฟล์ Observed")
    else:
        if len(obs_files) > 1:
            print(f"  ⚠  Observed: พบหลายไฟล์ — ใช้ {obs_files[0].name}")
        obs_path = str(obs_files[0])

    raw_models: dict = {}
    for f in raw_files:
        name = _extract_model_name(str(f), "pr")
        if name in raw_models:
            print(f"  ⚠  ชื่อ Raw model '{name}' ซ้ำ — ข้าม {f.name}")
        else:
            raw_models[name] = str(f)
            print(f"    Raw  '{name}' ← {f.name}")

    bc_models: dict = {}
    for f in bc_files:
        name = _extract_model_name(str(f), "bc")
        if name in bc_models:
            print(f"  ⚠  ชื่อ BC model '{name}' ซ้ำ — ข้าม {f.name}")
        else:
            bc_models[name] = str(f)
            print(f"    BC   '{name}' ← {f.name}")

    # Warn about missing pairs
    for m in set(raw_models) - set(bc_models):
        print(f"  ⚠  ไม่พบ BC สำหรับ '{m}' — วิเคราะห์ Raw เท่านั้น")
    for m in set(bc_models) - set(raw_models):
        print(f"  ⚠  ไม่พบ Raw สำหรับ '{m}' — วิเคราะห์ BC เท่านั้น")

    return obs_path, raw_models, bc_models


def load_station_coordinates(folder: str, stns: list) -> pd.DataFrame | None:
    """
    Try to read station_coordinates.csv  (StationID, Latitude, Longitude).
    Returns DataFrame indexed by station code, or None if not found.
    """
    coord_path = Path(folder) / "station_coordinates.csv"
    if not coord_path.exists():
        print(f"  ℹ  ไม่พบ {coord_path.name} — ข้ามการวิเคราะห์ Distance-Decay")
        return None
    try:
        df = pd.read_csv(coord_path)
        df.columns = [c.strip() for c in df.columns]
        id_col = next((c for c in df.columns
                       if "station" in c.lower() or "id" in c.lower()), df.columns[0])
        lat_col = next((c for c in df.columns if "lat" in c.lower()), None)
        lon_col = next((c for c in df.columns
                        if "lon" in c.lower() or "lng" in c.lower()), None)
        if lat_col is None or lon_col is None:
            print("  ⚠  station_coordinates.csv: ไม่พบคอลัมน์ Lat/Lon")
            return None
        df = df[[id_col, lat_col, lon_col]].copy()
        df.columns = ["StationID", "Lat", "Lon"]
        df["StationID"] = df["StationID"].astype(str)
        df = df.set_index("StationID")
        # Keep only stations present in data
        df = df.loc[df.index.isin([str(s) for s in stns])]
        print(f"  ✓  โหลดพิกัดสถานี {len(df)} แห่ง จาก {coord_path.name}")
        return df
    except Exception as e:
        print(f"  ⚠  อ่าน station_coordinates.csv ไม่ได้: {e}")
        return None

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  2.  DATA LOADING & TEMPORAL AGGREGATION                                ║
# ╚══════════════════════════════════════════════════════════════════════════╝

MISS_FLAGS = [-99, -999, -9999, -9.99e+20, 9.99e+20, 1e+20]

def load_daily(path: str, label: str):
    if path is None or not os.path.isfile(path):
        print(f"  ✗  ไม่พบ {label}"); return None, []
    df = pd.read_csv(path)
    for mv in MISS_FLAGS: df.replace(mv, np.nan, inplace=True)
    num = df.select_dtypes(include=[np.number]).columns
    df[num] = df[num].where(df[num] >= 0)
    stns = [c for c in df.columns if c not in ("YEAR","MONTH","DAY")]
    try:
        df["date"] = pd.to_datetime(
            {"year": df["YEAR"], "month": df["MONTH"], "day": df["DAY"]})
        df = df.set_index("date")[stns]
    except Exception:
        df = df[stns]
    print(f"    {label:22s}: {len(df):,} rows × {len(stns)} stns  [{_period(df)}]")
    return df, stns


def _period(df):
    if df is None: return "N/A"
    try:   return f"{df.index[0].year}–{df.index[-1].year}"
    except: return "N/A"


def to_monthly(d):
    if d is None: return None
    return d.resample("MS").apply(lambda g: g.sum(min_count=int(0.8*len(g))))


def to_annual(d):
    if d is None: return None
    return d.resample("YS").apply(lambda g: g.sum(min_count=int(0.8*len(g))))


def to_seasonal(d, months):
    """Annual totals for the given calendar months (e.g. wet season)."""
    if d is None: return None
    sub = d[d.index.month.isin(months)]
    return sub.resample("YS").apply(lambda g: g.sum(min_count=int(0.6*len(g))))


def align_dfs(df1, df2):
    if df1 is None or df2 is None: return None, None
    common = df1.index.intersection(df2.index)
    return (df1.loc[common], df2.loc[common]) if len(common) > 0 else (None, None)


def gcol(df, stn):
    if df is None or stn not in df.columns: return np.array([], dtype=float)
    v = df[stn].values.astype(float)
    return v[~np.isnan(v) & (v >= 0)]


def short_labels(stns):
    return {str(s): f"S{i+1}" for i, s in enumerate(stns)}


def ensemble_mean(dfs_dict: dict):
    """Multi-model ensemble mean DataFrame."""
    valid = [df for df in dfs_dict.values() if df is not None]
    if not valid: return None
    common = valid[0].index
    for df in valid[1:]: common = common.intersection(df.index)
    if len(common) == 0: return None
    stack = np.stack([df.loc[common].values.astype(float) for df in valid], axis=0)
    return pd.DataFrame(np.nanmean(stack, axis=0),
                        index=common, columns=valid[0].columns)

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  3.  PERFORMANCE METRICS  (academically correct)                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def _perf(o: np.ndarray, s: np.ndarray) -> dict:
    """
    Core performance metrics for paired (same-length) arrays.
    If arrays have different lengths, truncate to the shorter one.
    If either is empty, return NaN dict immediately.
    """
    null = {k: np.nan for k in ["n","r","sigma_r","beta","RMSE","MAE",
                                  "MBE","Pbias","NSE","KGE","d","SS"]}
    # Guard: mismatched or empty arrays → return nulls
    if len(o) == 0 or len(s) == 0:
        return null
    n_common = min(len(o), len(s))
    o = np.asarray(o[:n_common], dtype=float)
    s = np.asarray(s[:n_common], dtype=float)
    mask = ~np.isnan(o) & ~np.isnan(s)
    o, s = o[mask].astype(float), s[mask].astype(float)
    if len(o) < 5: return null
    res    = s - o
    rmse   = float(np.sqrt(np.mean(res**2)))
    mae    = float(np.mean(np.abs(res)))
    mbe    = float(np.mean(res))
    pb     = float(100*np.sum(res)/np.sum(o)) if np.sum(o) else np.nan
    r      = float(np.corrcoef(o, s)[0,1])
    dn_nse = np.sum((o - np.mean(o))**2)
    nse    = float(1 - np.sum(res**2)/dn_nse) if dn_nse else np.nan
    sig_r  = float(np.std(s, ddof=1)/np.std(o, ddof=1)) if np.std(o, ddof=1) else np.nan
    beta_v = float(np.mean(s)/np.mean(o)) if np.mean(o) else np.nan
    kge    = float(1 - math.sqrt((r-1)**2+(sig_r-1)**2+(beta_v-1)**2)) \
             if not (np.isnan(sig_r) or np.isnan(beta_v)) else np.nan
    d_denom= np.sum((np.abs(s-np.mean(o)) + np.abs(o-np.mean(o)))**2)
    d      = float(1 - np.sum(res**2)/d_denom) if d_denom else np.nan
    # Skill Score (Gleckler 2008): individual station SS
    mse_m  = float(np.mean(res**2))
    mse_c  = float(np.mean((np.mean(o)-o)**2))  # climatology = observed mean
    ss     = float(1 - mse_m/mse_c) if mse_c else np.nan
    return {"n":len(o),"r":r,"sigma_r":sig_r,"beta":beta_v,
            "RMSE":round(rmse,3),"MAE":round(mae,3),"MBE":round(mbe,3),
            "Pbias":round(pb,2),"NSE":round(float(nse),4),
            "KGE":round(float(kge),4),"d":round(float(d),4),
            "SS":round(ss,4),
            "std_obs":round(float(np.std(o,ddof=1)),3),
            "std_sim":round(float(np.std(s,ddof=1)),3)}


def perf_from_df(obs_df, sim_df, stn: str) -> dict:
    if obs_df is None or sim_df is None: return _perf(np.array([]), np.array([]))
    if stn not in obs_df.columns or stn not in sim_df.columns:
        return _perf(np.array([]), np.array([]))
    common = obs_df.index.intersection(sim_df.index)
    if len(common) == 0: return _perf(np.array([]), np.array([]))
    return _perf(obs_df.loc[common, stn].values,
                 sim_df.loc[common, stn].values)


def ensemble_skill_score(obs_df, ens_df, stns: list) -> float:
    """
    CORRECT ensemble Skill Score (Gleckler et al. 2008):
       SS = 1 − ΣE_ensemble / ΣE_climatology
    where the sums are over ALL stations AND ALL time steps.
    This is the proper pooled definition, not mean(SS_per_station).
    """
    sum_mse_ens  = 0.0
    sum_mse_clim = 0.0
    n_total = 0
    for stn in stns:
        if obs_df is None or ens_df is None: continue
        if stn not in obs_df.columns or stn not in ens_df.columns: continue
        common = obs_df.index.intersection(ens_df.index)
        if len(common) == 0: continue
        o = obs_df.loc[common, stn].values.astype(float)
        s = ens_df.loc[common, stn].values.astype(float)
        mask = ~np.isnan(o) & ~np.isnan(s)
        o, s = o[mask], s[mask]
        if len(o) < 5: continue
        sum_mse_ens  += np.sum((s - o)**2)
        sum_mse_clim += np.sum((np.mean(o) - o)**2)
        n_total += len(o)
    if sum_mse_clim == 0 or n_total == 0: return np.nan
    return float(1 - sum_mse_ens / sum_mse_clim)

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  4.  SPATIAL STATISTICS                                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance in km between two geographic points."""
    R  = 6371.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)
    a  = math.sin(Δφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(Δλ/2)**2
    return 2*R*math.atan2(math.sqrt(a), math.sqrt(1-a))


def build_distance_matrix(coords_df: pd.DataFrame, stns: list) -> np.ndarray:
    """Return symmetric distance matrix (km) ordered by stns."""
    n   = len(stns)
    mat = np.full((n, n), np.nan)
    for i, s1 in enumerate(stns):
        for j, s2 in enumerate(stns):
            if i == j:
                mat[i, j] = 0.0
            elif s1 in coords_df.index and s2 in coords_df.index:
                mat[i, j] = haversine_km(
                    coords_df.loc[s1,"Lat"], coords_df.loc[s1,"Lon"],
                    coords_df.loc[s2,"Lat"], coords_df.loc[s2,"Lon"])
    return mat


def spatial_cv(annual_df, stns):
    """Coefficient of variation across stations per year."""
    if annual_df is None: return np.nan, np.nan
    cols = [s for s in stns if s in annual_df.columns]
    row_cv = annual_df[cols].apply(
        lambda row: np.std(row.dropna(),ddof=1)/np.mean(row.dropna())*100
        if len(row.dropna())>1 and np.mean(row.dropna())!=0 else np.nan, axis=1)
    return float(row_cv.mean()), float(row_cv.std(ddof=1))


def spatial_correlation_matrix(df, stns):
    """Pearson correlation matrix as a DataFrame (for Excel use)."""
    if df is None: return None
    cols = [s for s in stns if s in df.columns]
    return df[cols].dropna(how="all").corr(method="pearson")


def build_correlation_matrix(df, stns: list) -> np.ndarray:
    """Pearson correlation matrix from daily/monthly DataFrame."""
    if df is None: return np.full((len(stns), len(stns)), np.nan)
    cols = [s for s in stns if s in df.columns]
    corr = df[cols].corr(method="pearson")
    n    = len(stns)
    mat  = np.full((n, n), np.nan)
    for i, s1 in enumerate(stns):
        for j, s2 in enumerate(stns):
            if s1 in corr.index and s2 in corr.columns:
                mat[i, j] = corr.loc[s1, s2]
    return mat


def mantel_test(dist_mat: np.ndarray, corr_mat: np.ndarray,
                n_perm: int = N_MANTEL, seed: int = 42
                ) -> tuple[float, float]:
    """
    Mantel Test (Mantel 1967):
    Compare Distance Matrix vs Correlation Matrix via permutation.

    Returns
    -------
    mantel_r : Pearson r between upper-triangle vectors
    p_value  : two-tailed permutation p-value
    """
    rng  = np.random.default_rng(seed)
    n    = dist_mat.shape[0]
    idx  = np.triu_indices(n, k=1)
    dist_v = dist_mat[idx]
    corr_v = corr_mat[idx]
    mask = ~np.isnan(dist_v) & ~np.isnan(corr_v)
    dist_v, corr_v = dist_v[mask], corr_v[mask]
    if len(dist_v) < 3:
        return np.nan, np.nan
    obs_r, _ = pearsonr(dist_v, corr_v)
    # Permutation: shuffle rows AND columns simultaneously
    count = 0
    for _ in range(n_perm):
        perm = rng.permutation(n)
        perm_mat   = corr_mat[np.ix_(perm, perm)]
        perm_v     = perm_mat[idx]
        perm_v     = perm_v[mask]
        perm_r, _  = pearsonr(dist_v, perm_v)
        if abs(perm_r) >= abs(obs_r):
            count += 1
    p_value = (count + 1) / (n_perm + 1)
    return float(obs_r), float(p_value)

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  5.  EXTREME INDICES (ETCCDI)                                           ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def etccdi_annual(df, stn: str, label: str) -> dict:
    """Rx1day, R50p, R95p, R99p, SDII  (mean ± std across years)."""
    null = {k: np.nan for k in
            ["label","Rx1day","Rx1day_std","R50p","R50p_std",
             "R95p","R95p_std","R99p","R99p_std","SDII","SDII_std"]}
    null["label"] = label
    if df is None or stn not in df.columns: return null
    s   = df[stn].dropna(); s = s[s >= 0]
    wet = s[s >= WET_THR]
    if len(wet) < 30: return null
    p50, p95, p99 = (float(np.percentile(wet, p)) for p in (50, 95, 99))
    rx1  = s.groupby(s.index.year).max()
    r50  = s[s > p50].groupby(s[s > p50].index.year).sum()
    r95  = s[s > p95].groupby(s[s > p95].index.year).sum()
    r99  = s[s > p99].groupby(s[s > p99].index.year).sum()
    sdii = wet.groupby(wet.index.year).mean()
    def ms(ser):
        return (round(float(ser.mean()),2),
                round(float(ser.std(ddof=1)),2)) if not ser.empty else (np.nan,np.nan)
    rx1m, rx1s = ms(rx1)
    r50m, r50s = ms(r50)
    r95m, r95s = ms(r95)
    r99m, r99s = ms(r99)
    sdm,  sds  = ms(sdii)
    return {"label":label,
            "Rx1day":rx1m,"Rx1day_std":rx1s,
            "R50p":r50m,  "R50p_std":r50s,
            "R95p":r95m,  "R95p_std":r95s,
            "R99p":r99m,  "R99p_std":r99s,
            "SDII":sdm,   "SDII_std":sds}

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  6.  TAYLOR DIAGRAM                                                     ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def _draw_taylor_bg(ax, ref_std: float, unit: str) -> float:
    """Draw Taylor diagram background (RMSE arcs, correlation arcs, std arcs)."""
    if np.isnan(ref_std) or ref_std <= 0: ref_std = 5.0
    r_max = ref_std * 1.70

    # RMSE arcs (centred on reference point)
    for frac, col in [(0.25,"#CFD8DC"),(0.50,"#B0BEC5"),
                      (0.75,"#90A4AE"),(1.00,"#78909C")]:
        rr    = ref_std * frac
        theta = np.linspace(0, np.pi/2, 300)
        xc = ref_std + rr*np.cos(np.pi - theta)
        yc = rr*np.sin(theta)
        mask = (xc**2+yc**2 <= r_max**2) & (xc>=0) & (yc>=0)
        ax.plot(xc[mask], yc[mask], color=col, lw=0.7, ls="--", alpha=0.7, zorder=1)
        idx = np.argmin(np.abs(theta - np.pi/4))
        if mask[idx]:
            ax.text(xc[idx], yc[idx], f"RMSE\n{rr:.1f}", fontsize=7,
                    color=col, ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.1",fc="white",ec="none",alpha=0.7))

    # Correlation arcs
    for rv, lc in [(0.2,"#CFD8DC"),(0.4,"#B0BEC5"),(0.6,"#90A4AE"),
                   (0.7,"#78909C"),(0.8,"#607D8B"),(0.9,"#546E7A"),
                   (0.95,"#455A64"),(0.99,"#37474F")]:
        tv = np.arccos(rv)
        xv, yv = r_max*np.cos(tv), r_max*np.sin(tv)
        ax.plot([0,xv],[0,yv], color=lc, lw=0.5, alpha=0.75, zorder=1)
        ax.text(xv*1.05, yv*1.05, f"{rv:.2f}", fontsize=7.5,
                color="#546E7A", ha="center", va="center")

    # Std arcs
    for frac in [0.25,0.5,0.75,1.0,1.25,1.5]:
        arc_r = ref_std*frac
        if arc_r > r_max: continue
        theta = np.linspace(0,np.pi/2,300)
        ax.plot(arc_r*np.cos(theta), arc_r*np.sin(theta),
                color="#ECEFF1", lw=0.7, alpha=0.85, zorder=1)
        ax.text(0, arc_r, f"{arc_r:.1f}", fontsize=7,
                color="#90A4AE", ha="right", va="center")

    ax.plot(ref_std, 0, "k*", markersize=14, zorder=9, label="Observed (Reference)")
    ax.set_xlim(0, r_max); ax.set_ylim(0, r_max)
    ax.set_xlabel(f"Standard Deviation ({unit})", fontsize=12, labelpad=6)
    ax.set_ylabel(f"Standard Deviation ({unit})", fontsize=12, labelpad=6)
    ax.text(-0.10, 0.5, "Pearson Correlation (r) →",
            transform=ax.transAxes, fontsize=9, rotation=90,
            va="center", color="#546E7A", style="italic")
    ax.set_aspect("equal"); ax.grid(False)
    ax.axhline(0, color="black", lw=0.9); ax.axvline(0, color="black", lw=0.9)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    return r_max


def _compute_taylor_rows(obs_df, raw_df, bc_df, stns: list, scale_lbl: str):
    raw_rows, bc_rows = [], []
    for stn in stns:
        if obs_df is None or stn not in obs_df.columns: continue
        std_o = float(obs_df[stn].std(ddof=1)) if stn in obs_df.columns else np.nan
        mr = perf_from_df(obs_df, raw_df, stn)
        mb = perf_from_df(obs_df, bc_df,  stn)
        mr.update({"Station":stn,"Dataset":"Raw","std_obs":std_o,"Label":scale_lbl})
        mb.update({"Station":stn,"Dataset":"QDM","std_obs":std_o,"Label":scale_lbl})
        raw_rows.append(mr); bc_rows.append(mb)
    return raw_rows, bc_rows


def _plot_taylor_points(ax, raw_rows, bc_rows, smap, stn_colors, ref_std):
    """Plot Raw (triangle) and QDM (circle) points with arrows."""
    raw_xy = {}
    for i, (rr, bb) in enumerate(zip(raw_rows, bc_rows)):
        stn  = rr.get("Station","")
        code = smap.get(str(stn), stn)
        col  = stn_colors[i % len(stn_colors)]
        for row, mk, ds in [(rr,"^","Raw"),(bb,"o","QDM")]:
            rv    = row.get("r",       np.nan)
            sr    = row.get("sigma_r", np.nan)
            std_o = row.get("std_obs", np.nan)
            std_s = std_o*sr if not (np.isnan(std_o) or np.isnan(sr)) else np.nan
            if np.isnan(std_s) or np.isnan(rv): continue
            theta = np.arccos(np.clip(rv, -1, 1))
            xv    = std_s*np.cos(theta)
            yv    = std_s*np.sin(theta)
            ax.scatter(xv, yv, color=col, marker=mk, s=95, zorder=7,
                       edgecolors="white", linewidth=0.8, alpha=0.90)
            if ds == "Raw":
                raw_xy[stn] = (xv, yv)
            elif ds == "QDM" and stn in raw_xy:
                rx, ry = raw_xy[stn]
                ax.annotate("", xy=(xv,yv), xytext=(rx,ry),
                            arrowprops=dict(arrowstyle="->",
                                            color=col, lw=0.9, alpha=0.60))
                ax.text(xv+0.03*ref_std, yv+0.03*ref_std,
                        code, fontsize=8, color=col, fontweight="bold")
    handles = [
        Line2D([0],[0],marker="*",color="k",ls="none",ms=11,label="Observed (Ref.)"),
        Line2D([0],[0],marker="^",color="grey",ls="none",ms=9,label="Raw CMIP6"),
        Line2D([0],[0],marker="o",color="grey",ls="none",ms=9,label="Bias-Corrected (QDM)"),
        Line2D([0],[0],color="grey",lw=0.9,ls="-",alpha=0.6,
               label="Arrow: Raw → QDM"),
    ]
    return handles

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  7.  FIGURE BUILDERS                                                    ║
# ╚══════════════════════════════════════════════════════════════════════════╝

# ── Helper: horizontal x-labels with auto figure width ────────────────────
def _xtick_horizontal(ax, labels, fontsize=10):
    """Set horizontal (0°) x-axis tick labels. Returns required fig width."""
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=0, ha="center", fontsize=fontsize)


def _station_codes(stns, smap):
    return [smap[str(s)] for s in stns]


# ─── Fig 1: Taylor Diagrams (Daily / Monthly / Wet Season) ─────────────────
def fig1_taylor(obs_d, raw_d, bc_d,
                obs_m, raw_m, bc_m,
                obs_ws, raw_ws, bc_ws,
                stns, smap, models_raw, models_bc,
                period_obs, period_sim, out_dir, prefix) -> dict:
    """
    Taylor Diagram at three temporal scales.
    Each station = unique colour; ▲ Raw, ● QDM, arrow = improvement direction.
    """
    stns_str   = [str(s) for s in stns]
    cmap_stn   = cm.get_cmap("tab20", max(len(stns), 1))
    stn_colors = [mcolors.to_hex(cmap_stn(i)) for i in range(len(stns))]

    scales = [
        ("Daily",               obs_d,  raw_d,  bc_d,  "mm day$^{-1}$", "(a)"),
        ("Monthly",             obs_m,  raw_m,  bc_m,  "mm month$^{-1}$","(b)"),
        ("Wet Season (May-Oct)",obs_ws, raw_ws, bc_ws, "mm yr$^{-1}$",   "(c)"),
    ]

    all_rows = {}
    for sl, o, r, b, _, _ in scales:
        rr, bb = _compute_taylor_rows(o, r, b, stns_str, sl)
        all_rows[sl] = (rr, bb)

    # ── Combined 1×3 ──────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 3, figsize=(22, 8.5))
    fig.subplots_adjust(left=0.04, right=0.97, top=0.87, bottom=0.10, wspace=0.30)

    for ai, (sl, o, r, b, unit, pbl) in enumerate(scales):
        ax     = axes[ai]
        rr, bb = all_rows[sl]
        if not rr:
            ax.text(0.5,0.5,"No data",transform=ax.transAxes,ha="center"); continue
        ref_std = float(np.nanmean([x["std_obs"] for x in rr
                                     if not np.isnan(x.get("std_obs",np.nan))]))
        _draw_taylor_bg(ax, ref_std, unit)
        hand = _plot_taylor_points(ax, rr, bb, smap, stn_colors, ref_std)
        ax.legend(handles=hand, loc="upper right", fontsize=9,
                  frameon=True, edgecolor="#B0BEC5", framealpha=0.92,
                  handlelength=1.8)
        ax.set_title(f"{pbl}  Taylor Diagram — {sl}",
                     loc="left", fontsize=13, fontweight="bold", pad=6)

    fig.suptitle(
        "Taylor Diagram — Daily / Monthly / Wet-Season Scale\n"
        "Raw CMIP6 vs Bias-Corrected (QDM)  |  "
        f"Obs: {period_obs}  |  Sim: {period_sim}  |  Wet Season: May–October",
        fontsize=14, fontweight="bold")
    savefig(fig, out_dir/f"{prefix}_Fig1_Taylor_Combined")

    # Individual sub-panels
    for ai, (sl, o, r, b, unit, pbl) in enumerate(scales):
        rr, bb = all_rows[sl]
        if not rr: continue
        ref_std = float(np.nanmean([x["std_obs"] for x in rr
                                     if not np.isnan(x.get("std_obs",np.nan))]))
        fig_s, ax_s = plt.subplots(1, 1, figsize=(9.5, 9.0))
        _draw_taylor_bg(ax_s, ref_std, unit)
        hand = _plot_taylor_points(ax_s, rr, bb, smap, stn_colors, ref_std)
        ax_s.legend(handles=hand, loc="upper right", fontsize=10,
                    frameon=True, edgecolor="#B0BEC5", framealpha=0.93)
        ax_s.set_title(f"Taylor Diagram — {sl}\nObs: {period_obs}  |  Sim: {period_sim}",
                       loc="left", fontsize=12, fontweight="bold", pad=6)
        fig_s.suptitle(f"Taylor Diagram — {sl}\n"
                       "Raw CMIP6 (triangle) vs Bias-Corrected QDM (circle)",
                       fontsize=14, fontweight="bold")
        sfx = sl.split("(")[0].strip().replace(" ","_")
        savefig(fig_s, out_dir/f"{prefix}_Fig1{chr(97+ai)}_Taylor_{sfx}")

    return all_rows


# ─── Fig 2: Spatial Correlation Matrices ───────────────────────────────────
def fig2_spatial_corr(obs_m, raw_m, bc_m, stns, smap,
                       period_obs, period_sim, out_dir, prefix):
    stns_str = [str(s) for s in stns]
    codes    = [smap[s] for s in stns_str]

    obs_r, raw_r = align_dfs(obs_m, raw_m)
    obs_r, bc_r  = align_dfs(obs_m, bc_m)

    def corr_mat(df):
        if df is None: return None
        cols = [s for s in stns_str if s in df.columns]
        return df[cols].rename(columns=smap).corr(method="pearson")

    obs_C = corr_mat(obs_r)
    raw_C = corr_mat(raw_r)
    bc_C  = corr_mat(bc_r)

    def _draw_heatmap(ax, mat, title):
        if mat is None:
            ax.text(0.5,0.5,"No data",transform=ax.transAxes,ha="center"); return
        n  = len(mat)
        im = ax.imshow(mat.values, cmap="RdYlGn", vmin=-1, vmax=1,
                       aspect="auto", interpolation="nearest")
        if n <= 15:
            for i in range(n):
                for j in range(n):
                    v  = mat.values[i,j]
                    tc = "white" if abs(v) > 0.75 else "black"
                    ax.text(j,i,f"{v:.2f}",ha="center",va="center",
                            fontsize=7.5 if n>10 else 9.5,
                            fontweight="bold",color=tc)
        ax.set_xticks(range(n))
        ax.set_xticklabels(mat.columns, rotation=0, ha="center", fontsize=9)
        ax.set_yticks(range(n))
        ax.set_yticklabels(mat.index, fontsize=9)
        ax.set_title(title, loc="left", fontsize=12, fontweight="bold", pad=4)
        plt.colorbar(im, ax=ax, orientation="horizontal",
                     pad=0.20, fraction=0.06, shrink=0.8,
                     label="Pearson r")

    # Station-pair deviation panel
    pairs_df = None
    if obs_C is not None and raw_C is not None and bc_C is not None:
        rows = []
        for i in range(len(codes)):
            for j in range(i+1, len(codes)):
                ci, cj = codes[i], codes[j]
                if ci in obs_C.index and cj in obs_C.index:
                    ro = obs_C.loc[ci,cj]
                    rr = raw_C.loc[ci,cj] if ci in raw_C.index else np.nan
                    rb = bc_C.loc[ci,cj]  if ci in bc_C.index  else np.nan
                    rows.append({"pair":f"{ci}-{cj}","r_obs":ro,
                                 "err_raw":abs(rr-ro) if not np.isnan(rr) else np.nan,
                                 "err_bc": abs(rb-ro) if not np.isnan(rb) else np.nan})
        if rows:
            pairs_df = pd.DataFrame(rows).dropna()
            pairs_df = pairs_df.sort_values("err_raw", ascending=False)

    # Combined 2×3 figure
    fig = plt.figure(figsize=(20, 12))
    gs  = gridspec.GridSpec(2,3,figure=fig,hspace=0.48,wspace=0.35,
                            top=0.90,bottom=0.10,left=0.05,right=0.97)
    axA = fig.add_subplot(gs[0,0]); axB = fig.add_subplot(gs[0,1])
    axC = fig.add_subplot(gs[0,2]); axD = fig.add_subplot(gs[1,:])

    _draw_heatmap(axA, obs_C, "(a)  Observed")
    _draw_heatmap(axB, raw_C, "(b)  Raw CMIP6")
    _draw_heatmap(axC, bc_C,  "(c)  Bias-Corrected (QDM)")

    if pairs_df is not None and len(pairs_df) > 0:
        x  = np.arange(len(pairs_df)); bw = 0.40
        axD.bar(x-bw/2, pairs_df["err_raw"], width=bw,
                color=C["raw_lt"], edgecolor=C["raw"], linewidth=0.9,
                alpha=0.85, label="Raw CMIP6  |Δr|", zorder=3)
        axD.bar(x+bw/2, pairs_df["err_bc"], width=bw,
                color=C["bc_lt"],  edgecolor=C["bc"],  linewidth=0.9,
                alpha=0.85, label="Bias-Corrected (QDM)  |Δr|", zorder=3)
        axD.axhline(pairs_df["err_raw"].mean(), color=C["raw"], lw=1.2,
                    ls="--", alpha=0.7,
                    label=f"Raw mean = {pairs_df['err_raw'].mean():.3f}")
        axD.axhline(pairs_df["err_bc"].mean(),  color=C["bc"],  lw=1.2,
                    ls="--", alpha=0.7,
                    label=f"QDM mean = {pairs_df['err_bc'].mean():.3f}")
        axD.set_xticks(x)
        axD.set_xticklabels(pairs_df["pair"], rotation=0, ha="center", fontsize=8)
        axD.set_ylabel("|Correlation Deviation from Observed|", fontsize=11)
        axD.set_title("(d)  Absolute Deviation of Inter-Station Correlation from Observed",
                      loc="left", fontsize=12, fontweight="bold", pad=4)
        axD.legend(fontsize=10, frameon=True, edgecolor="#B0BEC5",
                   loc="upper right", ncol=2)
        axD.spines["top"].set_visible(False); axD.spines["right"].set_visible(False)
        axD.set_ylim(bottom=0)

    fig.suptitle(
        "Spatial Correlation Structure Analysis\n"
        f"Inter-station Pearson Correlation of Monthly Rainfall  |  {period_obs}",
        fontsize=14, fontweight="bold")
    savefig(fig, out_dir/f"{prefix}_Fig2_SpatialCorrelation")

    # Sub-panels
    for sfx, title, mat in [("a_Obs","Observed",obs_C),
                              ("b_Raw","Raw CMIP6",raw_C),
                              ("c_QDM","Bias-Corrected (QDM)",bc_C)]:
        fig_s, ax_s = plt.subplots(1,1,figsize=(8.5, 7.5))
        _draw_heatmap(ax_s, mat, title)
        fig_s.suptitle(f"Spatial Correlation — {title}\n{period_obs}",
                        fontsize=14, fontweight="bold")
        savefig(fig_s, out_dir/f"{prefix}_Fig2_{sfx}")

    return pairs_df


# ─── Fig 3: Distance-Decay Relationship + Mantel Test ──────────────────────
def fig3_distance_decay(obs_m, raw_m, bc_m, stns, smap,
                         coords_df, period_obs, period_sim,
                         out_dir, prefix):
    """
    (a) Scatter: Station-pair distance (km) vs Pearson r — Obs / Raw / QDM
        with exponential decay fit for Observed.
    (b) Mantel Test bar chart: r_Mantel and p-value for each dataset.

    Physical interpretation:
        Observed should show clear distance-decay (r decreases with distance).
        QDM should PRESERVE this structure. If QDM produces spatial noise,
        its decay curve will flatten or scatter widely.
    """
    if coords_df is None:
        print("  ℹ  ข้ามการวิเคราะห์ Distance-Decay (ไม่พบ station_coordinates.csv)")
        return None

    stns_str = [str(s) for s in stns]
    obs_r, raw_r = align_dfs(obs_m, raw_m)
    obs_r, bc_r  = align_dfs(obs_m, bc_m)

    dist_mat = build_distance_matrix(coords_df, stns_str)
    obs_cmat = build_correlation_matrix(obs_r, stns_str)
    raw_cmat = build_correlation_matrix(raw_r, stns_str)
    bc_cmat  = build_correlation_matrix(bc_r,  stns_str)

    n   = len(stns_str)
    idx = np.triu_indices(n, k=1)

    def pairs(cmat):
        d = dist_mat[idx]
        r = cmat[idx]
        mask = ~np.isnan(d) & ~np.isnan(r)
        return d[mask], r[mask]

    obs_d_v, obs_r_v = pairs(obs_cmat)
    raw_d_v, raw_r_v = pairs(raw_cmat)
    bc_d_v,  bc_r_v  = pairs(bc_cmat)

    # Exponential decay fit:  r = a·exp(-b·d)  (for Observed)
    def exp_decay_fit(dist_v, corr_v):
        if len(dist_v) < 3: return None, None
        try:
            from scipy.optimize import curve_fit
            def model(d, a, b): return a * np.exp(-b * d)
            p0  = [1.0, 0.01]
            popt, _ = curve_fit(model, dist_v, corr_v, p0=p0, maxfev=5000)
            return popt, model
        except Exception:
            return None, None

    popt_obs, model_fn = exp_decay_fit(obs_d_v, obs_r_v)

    # Mantel tests
    print("    Mantel Test (permutations={}) ...".format(N_MANTEL))
    mantel_results = {}
    for lbl, cmat in [("Observed", obs_cmat),
                       ("Raw CMIP6", raw_cmat),
                       ("QDM", bc_cmat)]:
        mr, mp = mantel_test(dist_mat, cmat)
        mantel_results[lbl] = {"r": mr, "p": mp}
        sig = "***" if mp<0.001 else ("**" if mp<0.01 else ("*" if mp<0.05 else "ns"))
        print(f"      {lbl:20s}  r={mr:.4f}  p={mp:.4f} {sig}")

    # ── Plot ──────────────────────────────────────────────────────────
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(16, 7))
    fig.subplots_adjust(left=0.07, right=0.97, top=0.87,
                        bottom=0.12, wspace=0.32)

    # Panel A: scatter
    alpha_sc = max(0.25, min(0.60, 30/max(len(obs_d_v),1)))
    for d_v, r_v, col, lt, lbl in [
        (obs_d_v, obs_r_v, C["obs"], C["obs_lt"], "Observed"),
        (raw_d_v, raw_r_v, C["raw"], C["raw_lt"], "Raw CMIP6"),
        (bc_d_v,  bc_r_v,  C["bc"],  C["bc_lt"],  "Bias-Corrected (QDM)"),
    ]:
        axA.scatter(d_v, r_v, color=lt, edgecolors=col,
                    linewidth=0.5, s=50, alpha=alpha_sc, zorder=3, label=lbl)

    # Decay fit line for Observed
    if popt_obs is not None and model_fn is not None and len(obs_d_v) > 0:
        d_fit = np.linspace(0, obs_d_v.max(), 300)
        axA.plot(d_fit, model_fn(d_fit, *popt_obs),
                 color=C["obs"], lw=2.2, ls="-", zorder=5,
                 label=f"Obs decay fit\n"
                       f"$r=%.3f\\cdot e^{{-%.4fd}}$" %
                       (popt_obs[0], popt_obs[1]))

    axA.axhline(0, color="grey", lw=0.8, ls=":", alpha=0.6)
    axA.set_xlabel("Inter-Station Distance (km)", fontsize=12)
    axA.set_ylabel("Pearson Correlation (r)", fontsize=12)
    axA.set_title("(a)  Distance-Decay Relationship\n"
                  "     (Physical consistency test: r decreases with distance)",
                  loc="left", fontsize=12, fontweight="bold", pad=5)
    axA.legend(fontsize=10, frameon=True, edgecolor="#B0BEC5", loc="upper right")
    axA.spines["top"].set_visible(False); axA.spines["right"].set_visible(False)

    # Panel B: Mantel r bar
    labels_M = list(mantel_results.keys())
    r_vals   = [mantel_results[k]["r"] for k in labels_M]
    p_vals   = [mantel_results[k]["p"] for k in labels_M]
    colors_M = [C["obs"], C["raw"], C["bc"]]
    bars = axB.bar(range(len(labels_M)), r_vals, color=colors_M,
                   alpha=0.85, edgecolor="white", linewidth=0.8, zorder=3)
    for xi, (pv, rv) in enumerate(zip(p_vals, r_vals)):
        sig = ("p<0.001***" if pv<0.001 else
               ("p<0.01**" if pv<0.01 else
                ("p<0.05*"  if pv<0.05 else
                 f"p={pv:.3f} ns")))
        axB.text(xi, rv + 0.01, f"r={rv:.3f}\n{sig}",
                 ha="center", va="bottom", fontsize=10, fontweight="bold")
    axB.axhline(0, color="grey", lw=0.8, ls=":", alpha=0.6)
    axB.set_xticks(range(len(labels_M)))
    axB.set_xticklabels(labels_M, rotation=0, ha="center", fontsize=11)
    axB.set_ylabel("Mantel r  (Distance vs Correlation)", fontsize=12)
    axB.set_title("(b)  Mantel Test Results\n"
                  "     r < 0: spatial decay preserved  |  r > 0: spatial structure lost",
                  loc="left", fontsize=12, fontweight="bold", pad=5)
    axB.spines["top"].set_visible(False); axB.spines["right"].set_visible(False)

    fig.suptitle(
        "Distance-Decay Relationship & Mantel Test\n"
        "Physical Consistency Test — Multi-dimensional assessment  |  "
        f"Obs: {period_obs}",
        fontsize=14, fontweight="bold")
    savefig(fig, out_dir/f"{prefix}_Fig3_DistanceDecay_Mantel")
    return mantel_results


# ─── Fig 4: Spatial Variability ────────────────────────────────────────────
def fig4_spatial_variability(obs_a, raw_a, bc_a, stns, smap,
                               period_obs, period_sim, out_dir, prefix):
    stns_str = [str(s) for s in stns]
    codes    = _station_codes(stns, smap)
    obs_r, raw_r = align_dfs(obs_a, raw_a)
    obs_r, bc_r  = align_dfs(obs_a, bc_a)

    def sp_ts(df):
        if df is None: return None
        cols = [s for s in stns_str if s in df.columns]
        out  = pd.DataFrame(index=df.index)
        out["mean"] = df[cols].mean(axis=1)
        out["std"]  = df[cols].std(axis=1, ddof=1)
        out["cv"]   = out["std"] / out["mean"] * 100
        def gini(row):
            v = row.dropna().values
            if len(v)<2: return np.nan
            v = np.sort(v); n=len(v); idx=np.arange(1,n+1)
            return float((2*np.sum(idx*v)-(n+1)*np.sum(v))/(n*np.sum(v)))
        out["gini"] = df[cols].apply(gini, axis=1)
        return out

    obs_sp = sp_ts(obs_r); raw_sp = sp_ts(raw_r); bc_sp = sp_ts(bc_r)

    fig, axes = plt.subplots(2,2,figsize=(16,11))
    fig.subplots_adjust(hspace=0.42,wspace=0.32,
                        left=0.07,right=0.97,top=0.91,bottom=0.09)

    # Panel a — station mean annual
    x   = np.arange(len(stns)); bw = 0.26
    for di, (df, col, lt, lbl) in enumerate([
        (obs_r, C["obs"],C["obs_lt"],"Observed"),
        (raw_r, C["raw"],C["raw_lt"],"Raw CMIP6"),
        (bc_r,  C["bc"], C["bc_lt"], "Bias-Corrected (QDM)")
    ]):
        if df is None: continue
        means = [df[s].mean() if s in df.columns else np.nan for s in stns_str]
        axes[0,0].bar(x+(di-1)*bw, means, width=bw, color=lt,
                      edgecolor=col, linewidth=0.9, alpha=0.85,
                      label=lbl, zorder=3)
    axes[0,0].set_xticks(x)
    _xtick_horizontal(axes[0,0], codes)
    axes[0,0].set_ylabel("Mean Annual Rainfall (mm)", fontsize=11)
    axes[0,0].set_title("(a)  Station Mean Annual Rainfall",
                         loc="left",fontsize=12,fontweight="bold",pad=4)
    axes[0,0].legend(fontsize=10,frameon=True,edgecolor="#B0BEC5",loc="upper right")
    axes[0,0].spines["top"].set_visible(False); axes[0,0].spines["right"].set_visible(False)
    axes[0,0].set_ylim(bottom=0)

    # Panels b, c, d — time series
    for (ax, key, ylabel, title) in [
        (axes[0,1],"cv","Spatial CV (%)","(b)  Spatial Coefficient of Variation"),
        (axes[1,0],"std","Spatial Std Dev (mm)","(c)  Spatial Standard Deviation"),
        (axes[1,1],"gini","Gini Coefficient [0=equal, 1=unequal]","(d)  Spatial Gini Coefficient"),
    ]:
        for sp, col, lbl, ls in [(obs_sp,C["obs"],"Observed","-"),
                                   (raw_sp,C["raw"],"Raw CMIP6","--"),
                                   (bc_sp, C["bc"], "Bias-Corrected (QDM)","-")]:
            if sp is None: continue
            yrs = [d.year for d in sp.index]
            ax.plot(yrs, sp[key], color=col, lw=1.8, ls=ls, alpha=0.88, label=lbl)
        ax.legend(fontsize=10,frameon=True,edgecolor="#B0BEC5")
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_title(title, loc="left", fontsize=12, fontweight="bold", pad=4)
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
        ax.xaxis.set_minor_locator(ticker.AutoMinorLocator())
        if key == "gini": ax.set_ylim(0,1)
        ax.set_xlabel("Year", fontsize=11)

    fig.suptitle("Spatial Variability Analysis\n"
                 f"Obs: {period_obs}",fontsize=14,fontweight="bold")
    savefig(fig, out_dir/f"{prefix}_Fig4_SpatialVariability")

    # Sub-panels
    for sfx, key, ylabel in [("cv","cv","Spatial CV (%)"),
                               ("std","std","Spatial Std Dev (mm)"),
                               ("gini","gini","Gini Coefficient")]:
        fig_s, ax_s = plt.subplots(1,1,figsize=(10,5.5))
        for sp, col, lbl, ls in [(obs_sp,C["obs"],"Observed","-"),
                                   (raw_sp,C["raw"],"Raw CMIP6","--"),
                                   (bc_sp, C["bc"], "Bias-Corrected (QDM)","-")]:
            if sp is None: continue
            yrs=[d.year for d in sp.index]
            ax_s.plot(yrs,sp[key],color=col,lw=1.8,ls=ls,alpha=0.88,label=lbl)
        ax_s.set_ylabel(ylabel,fontsize=12); ax_s.set_xlabel("Year",fontsize=12)
        ax_s.legend(fontsize=10,frameon=True,edgecolor="#B0BEC5")
        ax_s.spines["top"].set_visible(False); ax_s.spines["right"].set_visible(False)
        if sfx=="gini": ax_s.set_ylim(0,1)
        fig_s.suptitle(f"{ylabel}\n{period_obs}",fontsize=14,fontweight="bold")
        savefig(fig_s, out_dir/f"{prefix}_Fig4_{sfx}")


# ─── Fig 5: Distribution Alignment ─────────────────────────────────────────
def fig5_distribution(obs_d, raw_d, bc_d, stns, smap,
                       period_obs, period_sim, out_dir, prefix):
    stns_str = [str(s) for s in stns]
    codes    = _station_codes(stns, smap)
    n        = len(stns); x = np.arange(n); bw = 0.38

    def qq_rmse_fn(obs_arr, sim_arr):
        probs = np.linspace(1,99,100)
        wo = obs_arr[obs_arr>=WET_THR]; ws = sim_arr[sim_arr>=WET_THR]
        if len(wo)<10 or len(ws)<10: return np.nan
        return float(np.sqrt(np.mean((np.percentile(ws,probs)-np.percentile(wo,probs))**2)))

    def ks_stat(a, b):
        wa=a[a>=WET_THR]; wb=b[b>=WET_THR]
        if len(wa)<5 or len(wb)<5: return np.nan
        return float(sps.ks_2samp(wa, wb)[0])

    qq_r=[]; qq_b=[]; ks_r=[]; ks_b=[]
    tail_obs=[]; tail_raw=[]; tail_bc=[]
    skew_obs=[]; skew_raw=[]; skew_bc=[]

    for stn in stns_str:
        ov = gcol(obs_d,stn)
        rv = gcol(raw_d,stn) if raw_d is not None else np.array([])
        bv = gcol(bc_d, stn) if bc_d  is not None else np.array([])
        qq_r.append(qq_rmse_fn(ov,rv)); qq_b.append(qq_rmse_fn(ov,bv))
        ks_r.append(ks_stat(ov,rv));    ks_b.append(ks_stat(ov,bv))
        for arr, lst_t, lst_s in [(ov,tail_obs,skew_obs),
                                    (rv,tail_raw,skew_raw),
                                    (bv,tail_bc, skew_bc)]:
            w = arr[arr>=WET_THR]
            p50 = np.percentile(w,50) if len(w)>10 else 0
            lst_t.append(np.percentile(w,95)/p50 if p50>0 and len(w)>10 else np.nan)
            lst_s.append(float(sps.skew(w)) if len(w)>5 else np.nan)

    fig, axes = plt.subplots(2,2,figsize=(16,11))
    fig.subplots_adjust(hspace=0.45,wspace=0.30,
                        left=0.07,right=0.97,top=0.91,bottom=0.09)

    def bar_pair(ax, v_raw, v_bc, ylabel, title, ref_vals=None):
        ax.bar(x-bw/2, v_raw, width=bw, color=C["raw_lt"],
               edgecolor=C["raw"], linewidth=0.9, alpha=0.85,
               label="Raw CMIP6", zorder=3)
        ax.bar(x+bw/2, v_bc, width=bw, color=C["bc_lt"],
               edgecolor=C["bc"],  linewidth=0.9, alpha=0.85,
               label="Bias-Corrected (QDM)", zorder=3)
        if ref_vals is not None:
            ax.plot(x, ref_vals, "k^", ms=9, zorder=5,
                    label="Observed", alpha=0.85)
        ax.set_xticks(x); _xtick_horizontal(ax, codes)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_title(title, loc="left", fontsize=12, fontweight="bold", pad=4)
        ax.legend(fontsize=10, frameon=True, edgecolor="#B0BEC5", loc="upper right")
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.set_ylim(bottom=0)

    bar_pair(axes[0,0], qq_r, qq_b,
             "QQ-RMSE (mm) [lower = better quantile alignment]",
             "(a)  Quantile-Quantile RMSE")
    bar_pair(axes[0,1], ks_r, ks_b,
             "KS-test Statistic D [lower = more similar]",
             "(b)  Kolmogorov-Smirnov Test Statistic")
    bar_pair(axes[1,0], tail_raw, tail_bc,
             "Tail Index (P95/P50) [heavy-tail ratio]",
             "(c)  Tail Index (P95 / P50 of wet days)",
             ref_vals=tail_obs)
    bar_pair(axes[1,1], skew_raw, skew_bc,
             "Skewness (Fisher-Pearson)",
             "(d)  Skewness of Wet-Day Rainfall",
             ref_vals=skew_obs)
    axes[1,1].set_ylim(bottom=None)

    fig.suptitle("Distribution Alignment Assessment — Station Scale\n"
                 f"Obs: {period_obs}",fontsize=14,fontweight="bold")
    savefig(fig, out_dir/f"{prefix}_Fig5_DistributionAlignment")

    # Sub-panels
    for sfx, vr, vb, ylbl, ref in [
        ("QQ_RMSE", qq_r, qq_b, "QQ-RMSE (mm)", None),
        ("KS_test",  ks_r, ks_b, "KS-stat D",   None),
        ("TailIdx",  tail_raw, tail_bc, "Tail Index (P95/P50)", tail_obs),
        ("Skewness", skew_raw, skew_bc, "Skewness", skew_obs),
    ]:
        fig_s, ax_s = plt.subplots(1,1,figsize=(11,6))
        bar_pair(ax_s, vr, vb, ylbl, sfx, ref)
        if sfx == "Skewness": ax_s.set_ylim(bottom=None)
        fig_s.suptitle(f"{sfx}\n{period_obs}",fontsize=14,fontweight="bold")
        savefig(fig_s, out_dir/f"{prefix}_Fig5_{sfx}")

    return {"qq_raw":qq_r,"qq_bc":qq_b,
            "ks_raw":ks_r,"ks_bc":ks_b}


# ─── Fig 6: Trade-off Summary (Research Gap Answer) ────────────────────────
def fig6_tradeoff(met_d_raw, met_d_bc, stns, smap,
                   sp_metrics, dist_metrics, period_obs,
                   out_dir, prefix):
    stns_str = [str(s) for s in stns]
    codes    = _station_codes(stns, smap)
    n        = len(stns)

    kge_raw = [next((r["KGE"] for r in met_d_raw if r["Station"]==s),np.nan) for s in stns_str]
    kge_bc  = [next((r["KGE"] for r in met_d_bc  if r["Station"]==s),np.nan) for s in stns_str]
    kge_imp = [b-r if not(np.isnan(b) or np.isnan(r)) else np.nan
               for r,b in zip(kge_raw,kge_bc)]
    qq_imp  = dist_metrics.get("qq_improvement", [np.nan]*n)

    DIMS  = ["KGE","NSE","r","Spatial\ncorr.(1-err)","Distrib.\n(1-QQ_RMSE)"]
    n_dim = len(DIMS)
    angles= np.linspace(0,2*np.pi,n_dim,endpoint=False).tolist() + [0]

    def dim_scores(rows, sp_e, qq_m):
        def mn(lst): return float(np.nanmean([r for r in lst if not np.isnan(r)]))
        kge_m  = mn([r.get("KGE",np.nan) for r in rows])
        nse_m  = mn([r.get("NSE",np.nan) for r in rows])
        r_m    = mn([r.get("r",  np.nan) for r in rows])
        sp_sc  = 1-sp_e if not np.isnan(sp_e) else 0.5
        qq_sc  = 1-qq_m/100 if not np.isnan(qq_m) else 0.5
        def norm(v,lo,hi): return max(0,min(1,(v-lo)/(hi-lo))) if (hi>lo and not np.isnan(v)) else 0.5
        return [norm(kge_m,-1,1),norm(nse_m,-1,1),norm(r_m,0,1),
                norm(sp_sc,0,1),norm(qq_sc,0,1)]

    sp_r  = sp_metrics.get("mean_spatial_corr_err_raw",np.nan)
    sp_b  = sp_metrics.get("mean_spatial_corr_err_bc", np.nan)
    qq_rm = dist_metrics.get("mean_qq_rmse_raw",np.nan)
    qq_bm = dist_metrics.get("mean_qq_rmse_bc", np.nan)

    sc_r = dim_scores(met_d_raw, sp_r, qq_rm); sc_r += sc_r[:1]
    sc_b = dim_scores(met_d_bc,  sp_b, qq_bm); sc_b += sc_b[:1]

    fig = plt.figure(figsize=(18,13))
    gs  = gridspec.GridSpec(2,2,figure=fig,hspace=0.45,wspace=0.35,
                            top=0.90,bottom=0.10,left=0.06,right=0.97)
    axA = fig.add_subplot(gs[0,0])
    axB = fig.add_subplot(gs[0,1],polar=True)
    axC = fig.add_subplot(gs[1,:])

    # Panel A — scatter
    cmap_sc = cm.get_cmap("RdYlGn", n)
    for i,(ki,qi,code) in enumerate(zip(kge_imp,qq_imp,codes)):
        if np.isnan(ki) or np.isnan(qi): continue
        axA.scatter(qi,ki,color=cmap_sc(i),s=130,zorder=4,
                    edgecolors="white",linewidth=0.9)
        axA.text(qi+0.002,ki+0.002,code,fontsize=9.5,
                 fontweight="bold",color=cmap_sc(i))
    axA.axhline(0,color="grey",lw=0.9,ls="--",alpha=0.7)
    axA.axvline(0,color="grey",lw=0.9,ls="--",alpha=0.7)
    axA.text(0.25,0.92,"QDM helps both",transform=axA.transAxes,
             fontsize=10,color=C["green"],fontweight="bold",ha="center")
    axA.text(0.75,0.08,"Distribution OK\nStation perf. not",
             transform=axA.transAxes,fontsize=9,color=C["gold"],ha="center")
    axA.text(0.25,0.08,"QDM hurts both",transform=axA.transAxes,
             fontsize=10,color=C["raw"],fontweight="bold",ha="center")
    axA.set_xlabel("QQ-RMSE Reduction (mm)\n[positive = distribution more aligned to Obs]",fontsize=11)
    axA.set_ylabel("KGE Improvement\n[positive = better station-scale performance]",fontsize=11)
    axA.set_title("(a)  KGE Improvement vs Distribution Alignment",
                  loc="left",fontsize=12,fontweight="bold",pad=5)
    axA.spines["top"].set_visible(False); axA.spines["right"].set_visible(False)

    # Panel B — radar
    axB.fill(angles, sc_r, color=C["raw"], alpha=0.20)
    axB.plot(angles, sc_r, color=C["raw"], lw=1.9, ls="--", label="Raw CMIP6")
    axB.fill(angles, sc_b, color=C["bc"],  alpha=0.32)
    axB.plot(angles, sc_b, color=C["bc"],  lw=2.3, ls="-",  label="Bias-Corrected (QDM)")
    axB.set_thetagrids(np.degrees(angles[:-1]), DIMS, fontsize=10.5)
    axB.set_ylim(0,1)
    axB.set_yticks([0.25,0.50,0.75,1.00])
    axB.set_yticklabels(["0.25","0.50","0.75","1.00"],fontsize=8.5,color="#78909C")
    axB.set_title("(b)  Multi-Dimensional Performance Radar",
                  fontsize=12,fontweight="bold",pad=22)
    axB.legend(loc="lower right",bbox_to_anchor=(1.45,-0.12),
               fontsize=10,frameon=True,edgecolor="#B0BEC5")
    axB.grid(True,lw=0.5,alpha=0.55)

    # Panel C — improvement heatmap
    dim_names = ["KGE change","NSE change","r change",
                 "QQ-RMSE reduction","KS-stat reduction"]
    imp_matrix = np.array([
        [next((r["KGE"] for r in met_d_bc  if r["Station"]==s),np.nan) -
         next((r["KGE"] for r in met_d_raw if r["Station"]==s),np.nan),
         next((r["NSE"] for r in met_d_bc  if r["Station"]==s),np.nan) -
         next((r["NSE"] for r in met_d_raw if r["Station"]==s),np.nan),
         next((r["r"]   for r in met_d_bc  if r["Station"]==s),np.nan) -
         next((r["r"]   for r in met_d_raw if r["Station"]==s),np.nan),
         dist_metrics.get("qq_improvement",[np.nan]*n)[stns_str.index(s)],
         dist_metrics.get("ks_improvement",[np.nan]*n)[stns_str.index(s)],
        ] for s in stns_str], dtype=float)

    imp_norm = np.zeros_like(imp_matrix)
    for di in range(imp_matrix.shape[1]):
        col_v = imp_matrix[:,di]; am = np.nanmax(np.abs(col_v))
        imp_norm[:,di] = col_v/am if am>0 else col_v

    im = axC.imshow(imp_norm.T, cmap="RdYlGn", vmin=-1, vmax=1,
                    aspect="auto", interpolation="nearest")
    plt.colorbar(im, ax=axC, orientation="vertical",
                 pad=0.01, fraction=0.03,
                 label="Normalised Improvement\n(green = positive, red = negative)")
    for di, dn in enumerate(dim_names):
        for si, code in enumerate(codes):
            val = imp_matrix[si,di]
            if not np.isnan(val):
                tc = "white" if abs(imp_norm[si,di])>0.70 else "black"
                axC.text(si,di,f"{val:+.3f}",ha="center",va="center",
                         fontsize=9,fontweight="bold",color=tc)
    axC.set_xticks(range(n))
    _xtick_horizontal(axC, codes, fontsize=10)
    axC.set_yticks(range(len(dim_names)))
    axC.set_yticklabels(dim_names, fontsize=10.5)
    axC.set_xlabel("Station", fontsize=11, labelpad=5)
    axC.set_title("(c)  Per-Station, Per-Dimension Improvement After QDM",
                  loc="left", fontsize=12, fontweight="bold", pad=5)

    fig.suptitle("Multi-dimensional Performance Profile\n"
                 "Multi-dimensional assessment of QDM on station-scale rainfall and spatial structure  |  "
                 f"Obs: {period_obs}",fontsize=14,fontweight="bold")
    savefig(fig, out_dir/f"{prefix}_Fig6_TradeoffSummary")

    # Sub-panels
    for sfx, ax_fn in [("Scatter",None),("Radar",None),("Heatmap",None)]:
        fig_s = plt.figure(figsize=(10,8))
        if sfx=="Scatter":
            ax_s=fig_s.add_subplot(1,1,1)
            for i,(ki,qi,code) in enumerate(zip(kge_imp,qq_imp,codes)):
                if np.isnan(ki) or np.isnan(qi): continue
                ax_s.scatter(qi,ki,color=cmap_sc(i),s=140,zorder=4,
                             edgecolors="white",linewidth=0.9)
                ax_s.text(qi+0.002,ki+0.002,code,fontsize=10,
                          fontweight="bold",color=cmap_sc(i))
            ax_s.axhline(0,color="grey",lw=0.9,ls="--",alpha=0.7)
            ax_s.axvline(0,color="grey",lw=0.9,ls="--",alpha=0.7)
            ax_s.set_xlabel("QQ-RMSE Reduction (mm)",fontsize=12)
            ax_s.set_ylabel("KGE Improvement",fontsize=12)
            ax_s.spines["top"].set_visible(False); ax_s.spines["right"].set_visible(False)
        elif sfx=="Radar":
            ax_s=fig_s.add_subplot(1,1,1,polar=True)
            ax_s.fill(angles,sc_r,color=C["raw"],alpha=0.20)
            ax_s.plot(angles,sc_r,color=C["raw"],lw=1.9,ls="--",label="Raw CMIP6")
            ax_s.fill(angles,sc_b,color=C["bc"], alpha=0.32)
            ax_s.plot(angles,sc_b,color=C["bc"], lw=2.3,ls="-", label="QDM")
            ax_s.set_thetagrids(np.degrees(angles[:-1]),DIMS,fontsize=11)
            ax_s.set_ylim(0,1)
            ax_s.legend(loc="lower right",bbox_to_anchor=(1.45,-0.12),fontsize=11)
        else:
            ax_s=fig_s.add_subplot(1,1,1)
            im2=ax_s.imshow(imp_norm.T,cmap="RdYlGn",vmin=-1,vmax=1,
                            aspect="auto",interpolation="nearest")
            plt.colorbar(im2,ax=ax_s,orientation="vertical",pad=0.01,fraction=0.04)
            for di,dn in enumerate(dim_names):
                for si,code in enumerate(codes):
                    val=imp_matrix[si,di]
                    if not np.isnan(val):
                        tc="white" if abs(imp_norm[si,di])>0.70 else "black"
                        ax_s.text(si,di,f"{val:+.3f}",ha="center",va="center",
                                  fontsize=9,fontweight="bold",color=tc)
            ax_s.set_xticks(range(n)); _xtick_horizontal(ax_s,codes,fontsize=10)
            ax_s.set_yticks(range(len(dim_names)))
            ax_s.set_yticklabels(dim_names,fontsize=11)
        fig_s.suptitle(f"{sfx}\n{period_obs}",
                        fontsize=14,fontweight="bold")
        savefig(fig_s, out_dir/f"{prefix}_Fig6_{sfx}")

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  8.  EXCEL WRITER — 10 SHEETS                                           ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def write_excel(wb, stns, smap, models,
                met_d_raw, met_d_bc,
                met_m_raw, met_m_bc,
                met_ws_raw, met_ws_bc,
                sp_metrics, dist_metrics,
                extremes_obs, extremes_raw, extremes_bc,
                taylor_rows, mantel_results,
                period_obs, period_sim):
    stns_str = [str(s) for s in stns]
    codes    = [smap[s] for s in stns_str]

    def _title(ws, nc, title, sub):
        mxsc(ws,1,1,nc,title,bold=True,fc="FFFFFF",bg=XC["title"],sz=12,align="left")
        ws.row_dimensions[1].height=24
        mxsc(ws,2,1,nc,sub,italic=True,fc="FFFFFF",bg=XC["sub"],sz=8.5)
        ws.row_dimensions[2].height=13

    def _hdr(ws, r, hdrs, bg=XC["hdr"]):
        for ci,h in enumerate(hdrs,1):
            xsc(ws,r,ci,h,bold=True,fc="FFFFFF",bg=bg,border=tb(),sz=9,wrap=True)
        ws.row_dimensions[r].height=36

    # ── S1: Overview ──────────────────────────────────────────────────
    ws=wb.create_sheet("Overview")
    ws.sheet_view.showGridLines=False
    _title(ws,4,
           "Research Gap Analysis v3 — Does QDM Improve Station-Scale Representation?",
           f"Observed: {period_obs}  |  Models: {', '.join(models)}  |  "
           f"Stations: {len(stns)}  |  Sim: {period_sim}")
    items=[
        ("S2","Station Performance (Daily)","RMSE, NSE, KGE, r, d, Pbias — Raw vs QDM"),
        ("S3","Station Performance (Monthly)","Same metrics at monthly scale"),
        ("S4","Station Performance (Wet Season)","May–Oct seasonal metrics"),
        ("S5","Taylor Statistics","r, sigma_ratio, RMSE per scale — Taylor diagram data"),
        ("S6","Extreme Indices (ETCCDI)","Rx1day, R50p, R95p, R99p, SDII — Raw vs QDM"),
        ("S7","Spatial Correlation","Inter-station correlation matrices + deviation"),
        ("S8","Distance-Decay & Mantel","Mantel r, p-value for Obs/Raw/QDM"),
        ("S9","Distribution Alignment","QQ-RMSE, KS-test, Tail Index, Skewness"),
        ("S10","Key Findings & References","Research conclusions + full reference list"),
    ]
    alt=[PatternFill("solid",fgColor="E3F2FD"),PatternFill("solid",fgColor="FFFFFF")]
    for ri,(code,title_s,desc) in enumerate(items,4):
        fl=alt[ri%2]
        for ci,v in enumerate([code,title_s,desc],1):
            cell=xsc(ws,ri,ci,v,bold=(ci<=2),sz=10,align="left",border=tb())
            cell.fill=fl
            if ci==3: cell.alignment=Alignment(horizontal="left",vertical="center",wrap_text=True)
        ws.row_dimensions[ri].height=34
    for ci,w in enumerate([6,32,64],1): cw(ws,ci,w)

    # ── Generic performance sheet builder ─────────────────────────────
    def _perf_sheet(ws_name, raw_rows, bc_rows, scale_lbl, period_label):
        ws=wb.create_sheet(ws_name); ws.sheet_view.showGridLines=False
        ws.freeze_panes="E5"
        nc=14
        _title(ws,nc,
               f"Model Performance Metrics — {scale_lbl}  (Raw CMIP6 vs Bias-Corrected/QDM)",
               f"★ = best per station  |  Green = improved  |  Red = degraded  |  "
               f"NSE criteria: VG>0.75 | Good 0.65–0.75 | Sat 0.50–0.65")
        hdr=["Dataset","Station","Code","N","RMSE","MAE","MBE","Pbias (%)","r","NSE","KGE","d (IoA)","SS"]
        _hdr(ws,4,hdr)
        ds_bg={"Raw CMIP6":XC["raw_r"],"Bias-Corrected":XC["bc_r"]}
        ds_fc={"Raw CMIP6":"B71C1C","Bias-Corrected":"0D47A1"}

        # Identify best values per station+metric
        best_set=set()
        for stn in stns_str:
            sr=[(i,r) for i,r in enumerate(raw_rows+bc_rows) if r.get("Station")==stn]
            for met_k,lower in [("RMSE",True),("KGE",False),("NSE",False),("r",False)]:
                vals=[(i,r.get(met_k,np.nan)) for i,r in sr
                      if not np.isnan(r.get(met_k,np.nan))]
                if not vals: continue
                bi=(min(vals,key=lambda x:abs(x[1]))[0] if lower
                    else max(vals,key=lambda x:x[1])[0])
                best_set.add((bi+5, hdr.index(met_k)+1))

        prev=None
        for ri_idx, (ds_lbl, row_list) in enumerate([
                ("Raw CMIP6",raw_rows),("Bias-Corrected",bc_rows)]):
            for ri, row in enumerate(row_list, 5 + ri_idx*len(raw_rows)):
                stn=row.get("Station","")
                if stn!=prev and prev is not None:
                    ws.row_dimensions[ri-1].height=4
                bg=ds_bg.get(ds_lbl,XC["white"])
                vals=[ds_lbl,stn,smap.get(str(stn),""),row.get("n",np.nan),
                      row.get("RMSE",np.nan),row.get("MAE",np.nan),
                      row.get("MBE",np.nan),row.get("Pbias",np.nan),
                      row.get("r",np.nan),row.get("NSE",np.nan),
                      row.get("KGE",np.nan),row.get("d",np.nan),row.get("SS",np.nan)]
                for ci,v in enumerate(vals,1):
                    if isinstance(v,float) and np.isnan(v): v="—"
                    elif isinstance(v,float): v=round(v,4)
                    is_best=(ri,ci) in best_set
                    cell=xsc(ws,ri,ci,
                             f"* {v}" if is_best and v!="—" else v,
                             bg=XC["best"] if is_best else bg,border=tb(),sz=9,
                             align="left" if ci<=3 else "right")
                    if ci==1:
                        cell.font=Font(bold=True,color=ds_fc.get(ds_lbl,"1A1A1A"),
                                       name="Calibri",size=9)
                    if is_best:
                        cell.font=Font(bold=True,color=XC["best_f"],
                                       name="Calibri",size=9)
                ws.row_dimensions[ri].height=14
                prev=stn
        widths=[16,10,6,6]+[10]*9
        for ci,w in enumerate(widths,1): cw(ws,ci,w)

    _perf_sheet("S2 Performance (Daily)", met_d_raw, met_d_bc,
                "Daily Scale", period_obs)
    _perf_sheet("S3 Performance (Monthly)", met_m_raw, met_m_bc,
                "Monthly Scale", period_obs)
    _perf_sheet("S4 Performance (WetSeason)", met_ws_raw, met_ws_bc,
                "Wet Season (May-Oct)", period_obs)

    # ── S5: Taylor Statistics ─────────────────────────────────────────
    ws5=wb.create_sheet("S5 Taylor Stats"); ws5.sheet_view.showGridLines=False
    _title(ws5,12,
           "Taylor Diagram Statistics — r, sigma_ratio, RMSE, NSE, KGE per Scale",
           "r=Pearson  |  sigma_ratio=SD_sim/SD_obs  |  Perfect: r=1, sigma=1, RMSE=0")
    hdr5=["Scale","Dataset","Station","Code","N","r","sigma_ratio","RMSE","NSE","KGE","Pbias (%)"]
    _hdr(ws5,4,hdr5)
    ri5=5
    for scale_k,(rr,bb) in (taylor_rows.items() if taylor_rows else {}.items()):
        for row,ds_lbl,bg in [(rr,"Raw CMIP6",XC["raw_r"]),(bb,"Bias-Corrected",XC["bc_r"])]:
            for r in ([row] if isinstance(row,dict) else row):
                stn=r.get("Station","")
                vals=[scale_k,ds_lbl,stn,smap.get(str(stn),""),r.get("n",np.nan),
                      r.get("r",np.nan),r.get("sigma_r",np.nan),r.get("RMSE",np.nan),
                      r.get("NSE",np.nan),r.get("KGE",np.nan),r.get("Pbias",np.nan)]
                for ci,v in enumerate(vals,1):
                    if isinstance(v,float) and np.isnan(v): v="—"
                    elif isinstance(v,float): v=round(v,4)
                    xsc(ws5,ri5,ci,v,bg=bg,border=tb(),sz=9,
                        align="left" if ci<=4 else "right")
                ws5.row_dimensions[ri5].height=14; ri5+=1
    for ci,w in enumerate([14,16,10,6,6]+[10]*6,1): cw(ws5,ci,w)

    # ── S6: Extreme Indices ───────────────────────────────────────────
    ws6=wb.create_sheet("S6 Extreme Indices"); ws6.sheet_view.showGridLines=False
    nc6=14
    _title(ws6,nc6,
           "ETCCDI Extreme Rainfall Indices — Raw CMIP6 vs Bias-Corrected (QDM)",
           "Rx1day=ann.max 1-day  |  R50p=total>P50  |  R95p=total>P95  |  "
           "R99p=total>P99  |  SDII=wet-day intensity  |  "
           "Format: mean (±std) across years  |  Ref: Karl et al. (1999)")
    idx_keys=["Rx1day","R50p","R95p","R99p","SDII"]
    hdr6=["Dataset","Station","Code"]
    for k in idx_keys: hdr6+=[f"{k} mean",f"{k} std"]
    hdr6+=["DeltaRx1day","DeltaR95p"]
    _hdr(ws6,4,hdr6)
    ri6=5
    for stn,code in zip(stns_str,codes):
        eo=next((e for e in extremes_obs if e.get("Station")==stn),{})
        er=next((e for e in extremes_raw if e.get("Station")==stn),{})
        eb=next((e for e in extremes_bc  if e.get("Station")==stn),{})
        def fv(d,k): return round(float(d.get(k,np.nan)),2) \
                           if not np.isnan(d.get(k,np.nan)) else "—"
        drx=round(eb.get("Rx1day",np.nan)-er.get("Rx1day",np.nan),2) \
            if not(np.isnan(er.get("Rx1day",np.nan)) or np.isnan(eb.get("Rx1day",np.nan))) else "—"
        dr9=round(eb.get("R95p",np.nan)-er.get("R95p",np.nan),2) \
            if not(np.isnan(er.get("R95p",np.nan)) or np.isnan(eb.get("R95p",np.nan))) else "—"
        for ds_lbl,exd,rbg in [("Observed",eo,XC["obs_r"]),
                                 ("Raw CMIP6",er,XC["raw_r"]),
                                 ("Bias-Corrected",eb,XC["bc_r"])]:
            row=[ds_lbl,stn,code]
            for k in idx_keys: row+=[fv(exd,k),fv(exd,f"{k}_std")]
            row+=[drx if ds_lbl=="Bias-Corrected" else "—",
                  dr9 if ds_lbl=="Bias-Corrected" else "—"]
            for ci,v in enumerate(row,1):
                cell=xsc(ws6,ri6,ci,v,bg=rbg,border=tb(),sz=9,
                         align="left" if ci<=3 else "right")
                if ci>=len(row)-1 and isinstance(v,(int,float)) and v!="—":
                    if v<0: cell.fill=xfill(XC["improve"])
                    elif v>0: cell.fill=xfill(XC["degrade"])
            ws6.row_dimensions[ri6].height=14; ri6+=1
        ws6.row_dimensions[ri6-1].height=5
    for ci,w in enumerate([14,10,6]+[9,8]*5+[11,11],1): cw(ws6,ci,w)

    # ── S7: Spatial Correlation Summary ──────────────────────────────
    ws7=wb.create_sheet("S7 Spatial Correlation"); ws7.sheet_view.showGridLines=False
    _title(ws7,5,
           "Spatial Correlation Analysis — Deviation from Observed",
           "Mean |Dr| = mean absolute deviation of inter-station r from Observed. "
           "Lower = better spatial structure preservation.")
    hdr7=["Metric","Observed","Raw CMIP6","Bias-Corrected (QDM)","Improvement","Interpretation"]
    _hdr(ws7,4,hdr7)
    sp_data=[
        ("Mean |Delta_r|",
         np.nan,
         sp_metrics.get("mean_spatial_corr_err_raw",np.nan),
         sp_metrics.get("mean_spatial_corr_err_bc",np.nan)),
        ("Spatial CV (%) — mean",
         sp_metrics.get("spatial_cv_obs_mean",np.nan),
         sp_metrics.get("spatial_cv_raw_mean",np.nan),
         sp_metrics.get("spatial_cv_bc_mean",np.nan)),
    ]
    for ri7,(m,ov,rv,bv) in enumerate(sp_data,5):
        imp=round(float(rv)-float(bv),4) if not(np.isnan(rv) or np.isnan(bv)) else np.nan
        interp="Improved" if not np.isnan(imp) and imp>0 else "Degraded"
        bg=XC["improve"] if interp=="Improved" else XC["degrade"]
        for ci,v in enumerate([m,
                                 round(float(ov),4) if not np.isnan(ov) else "—",
                                 round(float(rv),4) if not np.isnan(rv) else "—",
                                 round(float(bv),4) if not np.isnan(bv) else "—",
                                 round(imp,4) if not np.isnan(imp) else "—",
                                 interp],1):
            xsc(ws7,ri7,ci,v,bg=bg if ci>=5 else XC["white"],
                border=tb(),sz=9,align="left" if ci==1 else "center")
        ws7.row_dimensions[ri7].height=18
    for ci,w in enumerate([30,12,12,16,14,24],1): cw(ws7,ci,w)

    # ── S8: Mantel Test ───────────────────────────────────────────────
    ws8=wb.create_sheet("S8 Distance-Decay & Mantel"); ws8.sheet_view.showGridLines=False
    _title(ws8,5,
           "Distance-Decay Relationship & Mantel Test",
           "Mantel r < 0: correlation DECREASES with distance (physically correct decay). "
           "p < 0.05: spatial structure is statistically significant. "
           "Ref: Mantel (1967) Cancer Res. 27:209-220.")
    hdr8=["Dataset","Mantel r","p-value","Significance","Interpretation"]
    _hdr(ws8,4,hdr8)
    sig_map={"Observed":"Physical baseline","Raw CMIP6":"Pre-correction spatial structure",
             "QDM":"Post-correction spatial structure"}
    for ri8,(ds,res) in enumerate((mantel_results or {}).items(),5):
        mr=res.get("r",np.nan); mp=res.get("p",np.nan)
        sig=("p<0.001 ***" if mp<0.001 else
             ("p<0.01 **"  if mp<0.01  else
              ("p<0.05 *"  if mp<0.05  else
               f"p={mp:.3f} ns"))) if not np.isnan(mp) else "—"
        interp=(("Decay preserved" if mr<-0.05 else "Weak decay") if not np.isnan(mr) else "—")
        bg=XC["improve"] if (not np.isnan(mr) and mr<0) else XC["degrade"]
        for ci,v in enumerate([ds,
                                 round(mr,4) if not np.isnan(mr) else "—",
                                 round(mp,4) if not np.isnan(mp) else "—",
                                 sig, interp],1):
            cell=xsc(ws8,ri8,ci,v,
                     bg=bg if ci>=4 else XC["white"],border=tb(),sz=9,
                     align="left" if ci in (1,4,5) else "center")
            if ci in (4,5):
                fc_v="1B5E20" if (not np.isnan(mr) and mr<0) else "B71C1C"
                cell.font=Font(bold=True,color=fc_v,name="Calibri",size=9)
        ws8.row_dimensions[ri8].height=18
    for ci,w in enumerate([22,10,10,16,28],1): cw(ws8,ci,w)

    # ── S9: Distribution Alignment ────────────────────────────────────
    ws9=wb.create_sheet("S9 Distribution Alignment"); ws9.sheet_view.showGridLines=False
    _title(ws9,8,
           "Distribution Alignment Assessment — QQ-RMSE & KS-test per Station",
           "QQ-RMSE: lower = better quantile alignment  |  "
           "KS D: lower = more similar distribution  |  "
           "Delta = QDM minus Raw (negative = improved)")
    hdr9=["Station","Code","QQ-RMSE Raw","QQ-RMSE QDM","Delta QQ-RMSE",
          "KS Raw","KS QDM","Delta KS"]
    _hdr(ws9,4,hdr9)
    qq_r=dist_metrics.get("qq_raw",[np.nan]*len(stns))
    qq_b=dist_metrics.get("qq_bc", [np.nan]*len(stns))
    ks_r=dist_metrics.get("ks_raw",[np.nan]*len(stns))
    ks_b=dist_metrics.get("ks_bc", [np.nan]*len(stns))
    for ri9,(stn,code) in enumerate(zip(stns_str,codes),5):
        idx_s=stns_str.index(stn)
        qr=qq_r[idx_s]; qb=qq_b[idx_s]; kr=ks_r[idx_s]; kb=ks_b[idx_s]
        dq=round(qb-qr,4) if not(np.isnan(qr) or np.isnan(qb)) else np.nan
        dk=round(kb-kr,4) if not(np.isnan(kr) or np.isnan(kb)) else np.nan
        bg=XC["alt"] if ri9%2==0 else XC["white"]
        vals=[stn,code,
              round(qr,3) if not np.isnan(qr) else "—",
              round(qb,3) if not np.isnan(qb) else "—",
              round(dq,4) if not np.isnan(dq) else "—",
              round(kr,4) if not np.isnan(kr) else "—",
              round(kb,4) if not np.isnan(kb) else "—",
              round(dk,4) if not np.isnan(dk) else "—"]
        for ci,v in enumerate(vals,1):
            cell=xsc(ws9,ri9,ci,v,bg=bg,border=tb(),sz=9,
                     align="left" if ci<=2 else "right")
            if ci in (5,8) and isinstance(v,(int,float)):
                cell.fill=xfill(XC["improve"] if v<0 else XC["degrade"])
                fc_v="1B5E20" if v<0 else "B71C1C"
                cell.font=Font(bold=True,color=fc_v,name="Calibri",size=9)
        ws9.row_dimensions[ri9].height=15
    for ci,w in enumerate([10,6]+[12]*6,1): cw(ws9,ci,w)

    # ── S10: Key Findings & References ───────────────────────────────
    ws10=wb.create_sheet("S10 Findings & References"); ws10.sheet_view.showGridLines=False
    mxsc(ws10,1,1,3,"Key Findings & References — Research Gap Analysis v3",
         bold=True,fc="FFFFFF",bg=XC["title"],sz=13)
    ws10.row_dimensions[1].height=26
    findings=[
        ("F1","Distribution Alignment",
         "QDM reduces QQ-RMSE and KS-statistic — statistical distribution closer to Observed. "
         "However, improvement in station-scale performance metrics (KGE, NSE) is station-dependent."),
        ("F2","Spatial Coherence",
         "Station-independent QDM may alter inter-station spatial correlation. "
         "Mantel Test quantifies whether the distance-decay structure is preserved or degraded."),
        ("F3","Distance-Decay",
         "Observed rainfall shows clear distance-decay: stations closer together have higher r. "
         "QDM should preserve this structure. If Mantel r degrades, spatial noise is introduced."),
        ("F4","Temporal Scales",
         "Monthly Taylor Diagram shows improved sigma_ratio (variability). "
         "Wet-season (May-Oct) metrics confirm seasonal bias reduction."),
        ("F5","Ensemble Skill Score",
         "SS = 1 - sum(MSE_ens)/sum(MSE_clim) across ALL stations (pooled). "
         "Positive SS means ensemble beats climatological forecast."),
        ("REC","Recommendation",
         "For spatial applications, supplement station-by-station QDM with spatial "
         "bias correction (MBCn, R2D2) to simultaneously correct distributional and "
         "spatial dependence structure. Ref: Cannon (2018); Vrac (2018)."),
    ]
    refs=[
        ("Taylor (2001)","J. Geophys. Res. 106:7183–7192","Taylor Diagram"),
        ("Karl et al. (1999)","Int. J. Climatol. 19:405–420","ETCCDI extreme indices"),
        ("Gupta et al. (2009)","J. Hydrol. 377:80–91","KGE"),
        ("Nash & Sutcliffe (1970)","J. Hydrol. 10:282–290","NSE"),
        ("Gleckler et al. (2008)","J. Geophys. Res. 113:D06104","Skill Score / RPI"),
        ("Cannon et al. (2015)","J. Climate 28:6938–6959","QDM bias correction"),
        ("Mantel (1967)","Cancer Res. 27:209–220","Mantel Test"),
        ("Maraun & Widmann (2018)","Statistical Downscaling. Cambridge UP.","BC evaluation"),
        ("Moriasi et al. (2007)","Trans. ASABE 50:885–900","NSE performance criteria"),
    ]
    alt=[PatternFill("solid",fgColor="E3F2FD"),PatternFill("solid",fgColor="FFFFFF")]
    for ri,(k,t,d) in enumerate(findings,3):
        fl=alt[ri%2]
        for ci,v in enumerate([k,t,d],1):
            cell=xsc(ws10,ri,ci,v,bold=(ci<=2),sz=9.5,align="left",border=tb())
            cell.fill=fl
            if ci==3: cell.alignment=Alignment(horizontal="left",vertical="top",wrap_text=True)
        ws10.row_dimensions[ri].height=64
    # References
    ri_ref=len(findings)+5
    mxsc(ws10,ri_ref,1,3,"References",bold=True,fc="FFFFFF",bg=XC["sub"],sz=11)
    ws10.row_dimensions[ri_ref].height=22; ri_ref+=1
    for ri,(auth,journal,topic) in enumerate(refs,ri_ref):
        fl=alt[ri%2]
        for ci,v in enumerate([auth,journal,topic],1):
            cell=xsc(ws10,ri,ci,v,bold=(ci==1),sz=9,align="left",border=tb())
            cell.fill=fl
        ws10.row_dimensions[ri].height=20
    for ci,w in enumerate([24,50,26],1): cw(ws10,ci,w)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  9.  SIGNIFICANCE TESTING — WILCOXON SIGNED-RANK TEST                  ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def _sig_stars(p: float) -> str:
    """Return significance stars string (or 'ns') for a p-value."""
    if np.isnan(p): return "—"
    if p < 0.001:   return "***"
    if p < 0.01:    return "**"
    if p < 0.05:    return "*"
    return "ns"


def _effect_size_r(w_stat: float, n: int) -> float:
    """
    Effect size r = Z / sqrt(n)  (Cohen 1988).
    Approximation: Z from Wilcoxon W assuming large-sample normal.
    Convention: small=0.1, medium=0.3, large=0.5
    """
    if np.isnan(w_stat) or n < 5: return np.nan
    mu    = n*(n+1)/4.0
    sigma = math.sqrt(n*(n+1)*(2*n+1)/24.0)
    if sigma == 0: return np.nan
    z = (w_stat - mu) / sigma
    return float(abs(z) / math.sqrt(n))


def _fdr_correction(p_values: list, alpha: float = 0.05) -> list:
    """
    Benjamini-Hochberg FDR correction (1995).
    Returns list of booleans: True = significant after FDR correction.
    """
    n   = len(p_values)
    if n == 0: return []
    indexed = sorted(enumerate(p_values), key=lambda x: x[1] if not np.isnan(x[1]) else 1.1)
    reject  = [False]*n
    for rank_i, (orig_idx, pv) in enumerate(indexed, 1):
        if np.isnan(pv): continue
        if pv <= alpha * rank_i / n:
            reject[orig_idx] = True
    return reject


def wilcoxon_daily_errors(obs_df, raw_df, bc_df, stns: list) -> list:
    """
    Part A: Wilcoxon Signed-Rank Test on DAILY absolute errors.

    For each station:
      e_raw_t = |raw_t - obs_t|
      e_bc_t  = |bc_t  - obs_t|
      d_t     = e_raw_t - e_bc_t    (positive → BC better)

    H0: median(d) = 0
    H1: median(d) > 0  (BC has smaller errors; one-tailed)

    Returns list of dicts per station.
    """
    results = []
    stns_str = [str(s) for s in stns]

    if obs_df is None:
        return [{"Station":s,"W":np.nan,"p_two":np.nan,"p_one":np.nan,
                 "n_pairs":np.nan,"effect_r":np.nan,"sig":"—",
                 "median_err_raw":np.nan,"median_err_bc":np.nan,
                 "mean_err_raw":np.nan,"mean_err_bc":np.nan}
                for s in stns_str]

    for stn in stns_str:
        null = {"Station":stn,"W":np.nan,"p_two":np.nan,"p_one":np.nan,
                "n_pairs":np.nan,"effect_r":np.nan,"sig":"—",
                "median_err_raw":np.nan,"median_err_bc":np.nan,
                "mean_err_raw":np.nan,"mean_err_bc":np.nan}
        try:
            if (raw_df is None or bc_df is None or
                    stn not in obs_df.columns or
                    stn not in raw_df.columns or
                    stn not in bc_df.columns):
                results.append(null); continue

            common = (obs_df.index
                      .intersection(raw_df.index)
                      .intersection(bc_df.index))
            if len(common) < 10:
                results.append(null); continue

            obs_v = obs_df.loc[common, stn].values.astype(float)
            raw_v = raw_df.loc[common, stn].values.astype(float)
            bc_v  = bc_df.loc[common,  stn].values.astype(float)
            mask  = ~np.isnan(obs_v) & ~np.isnan(raw_v) & ~np.isnan(bc_v)
            obs_v, raw_v, bc_v = obs_v[mask], raw_v[mask], bc_v[mask]

            if len(obs_v) < 10:
                results.append(null); continue

            e_raw = np.abs(raw_v - obs_v)
            e_bc  = np.abs(bc_v  - obs_v)
            diff  = e_raw - e_bc   # positive = BC better

            # Remove zero differences (tied pairs)
            nonzero = diff != 0
            diff_nz = diff[nonzero]
            if len(diff_nz) < 5:
                results.append(null); continue

            # scipy wilcoxon: tests H0: median(diff)=0
            # alternative='greater' = H1: median(diff)>0 (BC has smaller err)
            W, p_two = scipy_wilcoxon(diff_nz, alternative="two-sided",
                                       zero_method="wilcox")
            _, p_one = scipy_wilcoxon(diff_nz, alternative="greater",
                                      zero_method="wilcox")

            n_pairs  = int(len(diff_nz))
            eff_r    = _effect_size_r(float(W), n_pairs)
            results.append({
                "Station":       stn,
                "W":             float(W),
                "p_two":         float(p_two),
                "p_one":         float(p_one),
                "n_pairs":       n_pairs,
                "effect_r":      round(eff_r, 4) if not np.isnan(eff_r) else np.nan,
                "sig":           _sig_stars(float(p_one)),
                "median_err_raw": round(float(np.median(e_raw)), 4),
                "median_err_bc":  round(float(np.median(e_bc)),  4),
                "mean_err_raw":   round(float(np.mean(e_raw)),   4),
                "mean_err_bc":    round(float(np.mean(e_bc)),    4),
            })
        except Exception as ex:
            null["note"] = str(ex)
            results.append(null)

    # FDR correction across stations
    p_ones = [r["p_one"] for r in results]
    fdr    = _fdr_correction(p_ones, alpha=0.05)
    for r, sig_fdr in zip(results, fdr):
        r["sig_fdr"] = "sig" if sig_fdr else "ns"

    return results


def wilcoxon_extreme_indices(obs_df, raw_df, bc_df, stns: list) -> dict:
    """
    Part B: Wilcoxon Signed-Rank Test on ANNUAL EXTREME INDEX errors.

    For each station and each ETCCDI index (Rx1day, R50p, R95p, R99p, SDII):
      1. Compute annual index for Obs, Raw, BC
      2. e_raw_y = |Raw_y - Obs_y|
         e_bc_y  = |BC_y  - Obs_y|
         d_y     = e_raw_y - e_bc_y  (positive → BC better)
      3. Wilcoxon H1: median(d) > 0 (one-tailed)

    Returns nested dict: {station: {index: result_dict}}
    """
    stns_str  = [str(s) for s in stns]
    idx_names = ["Rx1day", "R50p", "R95p", "R99p", "SDII"]

    def _annual_index(df, stn):
        """Compute annual ETCCDI indices as a DataFrame (year × index)."""
        if df is None or stn not in df.columns:
            return None
        s   = df[stn].dropna(); s = s[s >= 0]
        wet = s[s >= WET_THR]
        if len(wet) < 20:
            return None
        p50, p95, p99 = (float(np.percentile(wet, p)) for p in (50, 95, 99))
        rows = {}
        for yr in s.index.year.unique():
            yr_s   = s[s.index.year == yr]
            yr_wet = yr_s[yr_s >= WET_THR]
            if len(yr_wet) < 5: continue
            rows[yr] = {
                "Rx1day": float(yr_s.max()),
                "R50p":   float(yr_s[yr_s > p50].sum()),
                "R95p":   float(yr_s[yr_s > p95].sum()),
                "R99p":   float(yr_s[yr_s > p99].sum()),
                "SDII":   float(yr_wet.mean()),
            }
        return pd.DataFrame(rows).T if rows else None

    all_results = {}
    for stn in stns_str:
        all_results[stn] = {}
        obs_ann = _annual_index(obs_df, stn)
        raw_ann = _annual_index(raw_df, stn)
        bc_ann  = _annual_index(bc_df,  stn)

        if obs_ann is None or raw_ann is None or bc_ann is None:
            for idx in idx_names:
                all_results[stn][idx] = {
                    "W":np.nan,"p_one":np.nan,"p_two":np.nan,
                    "n_years":np.nan,"effect_r":np.nan,"sig":"—",
                    "median_err_raw":np.nan,"median_err_bc":np.nan}
            continue

        # Align on common years
        common_y = (obs_ann.index
                    .intersection(raw_ann.index)
                    .intersection(bc_ann.index))
        if len(common_y) < 5:
            for idx in idx_names:
                all_results[stn][idx] = {
                    "W":np.nan,"p_one":np.nan,"p_two":np.nan,
                    "n_years":np.nan,"effect_r":np.nan,"sig":"—",
                    "median_err_raw":np.nan,"median_err_bc":np.nan}
            continue

        o_df = obs_ann.loc[common_y]
        r_df = raw_ann.loc[common_y]
        b_df = bc_ann.loc[common_y]

        for idx in idx_names:
            try:
                o_v = o_df[idx].values.astype(float)
                r_v = r_df[idx].values.astype(float)
                b_v = b_df[idx].values.astype(float)
                mask = ~np.isnan(o_v)&~np.isnan(r_v)&~np.isnan(b_v)
                o_v,r_v,b_v = o_v[mask],r_v[mask],b_v[mask]
                if len(o_v) < 5:
                    raise ValueError("too few years")
                e_raw = np.abs(r_v - o_v)
                e_bc  = np.abs(b_v - o_v)
                diff  = e_raw - e_bc
                nonzero = diff != 0
                diff_nz = diff[nonzero]
                if len(diff_nz) < 4:
                    raise ValueError("too few non-zero pairs")
                W, p_two = scipy_wilcoxon(diff_nz, alternative="two-sided",
                                           zero_method="wilcox")
                _, p_one = scipy_wilcoxon(diff_nz, alternative="greater",
                                          zero_method="wilcox")
                n_y  = int(len(diff_nz))
                eff_r= _effect_size_r(float(W), n_y)
                all_results[stn][idx] = {
                    "W":        float(W),
                    "p_two":    float(p_two),
                    "p_one":    float(p_one),
                    "n_years":  n_y,
                    "effect_r": round(eff_r,4) if not np.isnan(eff_r) else np.nan,
                    "sig":      _sig_stars(float(p_one)),
                    "median_err_raw": round(float(np.median(e_raw)),4),
                    "median_err_bc":  round(float(np.median(e_bc)),4),
                }
            except Exception:
                all_results[stn][idx] = {
                    "W":np.nan,"p_one":np.nan,"p_two":np.nan,
                    "n_years":np.nan,"effect_r":np.nan,"sig":"—",
                    "median_err_raw":np.nan,"median_err_bc":np.nan}

    # FDR correction per index across stations
    for idx in idx_names:
        p_vals = [all_results[s][idx]["p_one"] for s in stns_str]
        fdr    = _fdr_correction(p_vals)
        for s, is_sig in zip(stns_str, fdr):
            all_results[s][idx]["sig_fdr"] = "sig" if is_sig else "ns"

    return all_results


# ─── Fig 7: Significance Testing Results ───────────────────────────────────
def fig7_significance(daily_wilcoxon: list, extreme_wilcoxon: dict,
                       stns, smap, period_obs, out_dir, prefix):
    """
    4-panel significance testing summary figure.

    (a) p-value heatmap: daily error Wilcoxon across stations
        Colour: green=significant (p<0.05), white=ns, red=BC worse
    (b) p-value heatmap: extreme index Wilcoxon (indices × stations)
    (c) Effect size (Cohen r) bar chart: daily test per station
    (d) Summary: % stations showing significant improvement at each test
    """
    stns_str   = [str(s) for s in stns]
    codes      = [smap[s] for s in stns_str]
    idx_names  = ["Rx1day","R50p","R95p","R99p","SDII"]
    n_s        = len(stns)
    n_idx      = len(idx_names)

    # Build matrices
    p_daily   = np.array([r.get("p_one",np.nan) for r in daily_wilcoxon])
    eff_daily = np.array([r.get("effect_r",np.nan) for r in daily_wilcoxon])
    sig_fdr_d = [r.get("sig_fdr","ns") for r in daily_wilcoxon]

    p_ext   = np.full((n_idx, n_s), np.nan)
    eff_ext = np.full((n_idx, n_s), np.nan)
    sig_fdr_ext = [[None]*n_s for _ in range(n_idx)]
    for si, stn in enumerate(stns_str):
        for ii, idx in enumerate(idx_names):
            res = extreme_wilcoxon.get(stn,{}).get(idx,{})
            p_ext[ii,si]       = res.get("p_one",np.nan)
            eff_ext[ii,si]     = res.get("effect_r",np.nan)
            sig_fdr_ext[ii][si]= res.get("sig_fdr","ns")

    fig = plt.figure(figsize=(20, 16))
    gs  = gridspec.GridSpec(2, 2, figure=fig,
                            hspace=0.52, wspace=0.35,
                            top=0.91, bottom=0.08,
                            left=0.07, right=0.97)
    axA = fig.add_subplot(gs[0, 0])  # daily p-value strip
    axB = fig.add_subplot(gs[0, 1])  # extreme p-value heatmap
    axC = fig.add_subplot(gs[1, 0])  # effect size bar
    axD = fig.add_subplot(gs[1, 1])  # summary proportion

    # ── Panel A: Daily p-value strip ──────────────────────────────────
    # Colour-coded: green<0.001, lime<0.01, yellow<0.05, grey=ns
    p_colors = []
    for pv in p_daily:
        if np.isnan(pv): p_colors.append("#E0E0E0")
        elif pv < 0.001: p_colors.append("#1E8449")   # dark green ***
        elif pv < 0.01:  p_colors.append("#27AE60")   # green **
        elif pv < 0.05:  p_colors.append("#82E0AA")   # light green *
        else:            p_colors.append("#FDFEFE")   # white ns

    x = np.arange(n_s); bw = 0.6
    bars = axA.bar(x, -np.log10(np.where(np.isnan(p_daily), 1.0, p_daily)),
                   width=bw, color=p_colors, edgecolor="white",
                   linewidth=0.6, zorder=3)

    for i, (pv, code) in enumerate(zip(p_daily, codes)):
        sig = _sig_stars(pv)
        if sig != "—" and sig != "ns":
            yv = -np.log10(pv) + 0.05 if not np.isnan(pv) else 0.05
            axA.text(i, yv, sig, ha="center", va="bottom",
                     fontsize=10, fontweight="bold", color="#1A1A1A")

    axA.axhline(-np.log10(0.05),  color="#C0392B", lw=1.2, ls="--",
                label="p = 0.05")
    axA.axhline(-np.log10(0.01),  color="#E67E22", lw=1.0, ls=":",
                label="p = 0.01")
    axA.axhline(-np.log10(0.001), color="#8E44AD", lw=1.0, ls=":",
                label="p = 0.001")
    axA.set_xticks(x); axA.set_xticklabels(codes, rotation=0, ha="center", fontsize=10)
    axA.set_ylabel("-log$_{10}$(p-value)\n[higher = more significant]", fontsize=11)
    axA.set_xlabel("Station", fontsize=11, labelpad=5)
    axA.set_title("(a)  Wilcoxon Signed-Rank Test — Daily Absolute Errors\n"
                  "     H$_1$: |err$_{BC}$| < |err$_{Raw}$|  (one-tailed)  |  "
                  "Colour: dark green=***, green=**, light=*",
                  loc="left", fontsize=11, fontweight="bold", pad=5)
    axA.legend(fontsize=9, frameon=True, edgecolor="#B0BEC5",
               loc="upper right", ncol=3)
    axA.spines["top"].set_visible(False); axA.spines["right"].set_visible(False)
    axA.set_ylim(bottom=0)

    # FDR markers
    for i, (fdr_sig, code) in enumerate(zip(sig_fdr_d, codes)):
        if fdr_sig == "sig":
            axA.scatter(i, -np.log10(p_daily[i]) + 0.35 if not np.isnan(p_daily[i]) else 0.35,
                        marker="D", s=40, color="#1565C0", zorder=6)
    # FDR legend proxy
    axA.scatter([], [], marker="D", s=40, color="#1565C0",
                label="FDR significant (q<0.05)")
    axA.legend(fontsize=9, frameon=True, edgecolor="#B0BEC5",
               loc="upper right", ncol=2)

    # ── Panel B: Extreme Index p-value heatmap ─────────────────────────
    # Transform: -log10(p), cap at 4 for display
    log_p_ext = np.where(np.isnan(p_ext), np.nan,
                         np.clip(-np.log10(np.where(np.isnan(p_ext),1.0,p_ext)),0,4))
    im = axB.imshow(log_p_ext, cmap="RdYlGn", vmin=0, vmax=4,
                    aspect="auto", interpolation="nearest")
    cb = plt.colorbar(im, ax=axB, orientation="horizontal",
                      pad=0.20, fraction=0.06, shrink=0.85)
    cb.set_label("-log$_{10}$(p-value)  [>1.30=*, >2.00=**, >3.00=***]",
                 fontsize=9.5)

    for ii, idx in enumerate(idx_names):
        for si, code in enumerate(codes):
            pv  = p_ext[ii, si]
            sig = _sig_stars(pv)
            fdr = sig_fdr_ext[ii][si]
            lp  = log_p_ext[ii, si] if not np.isnan(log_p_ext[ii, si]) else 0
            tc  = "white" if lp > 2.5 else "black"
            txt = f"{sig}" if sig not in ("—","ns") else "ns"
            if fdr == "sig": txt += "+"  # FDR significant
            axB.text(si, ii, txt, ha="center", va="center",
                     fontsize=9.5, fontweight="bold", color=tc)

    axB.set_xticks(range(n_s))
    axB.set_xticklabels(codes, rotation=0, ha="center", fontsize=10)
    axB.set_yticks(range(n_idx))
    axB.set_yticklabels(idx_names, fontsize=11)
    axB.set_xlabel("Station", fontsize=11, labelpad=5)
    axB.set_title("(b)  Wilcoxon Signed-Rank Test — Extreme Index Errors\n"
                  "     Annual |BC-Obs| vs |Raw-Obs|  |  +: FDR significant",
                  loc="left", fontsize=11, fontweight="bold", pad=5)
    # Threshold lines
    axB.axhline(-0.5, color="white", lw=0.4)

    # ── Panel C: Effect size bar chart ─────────────────────────────────
    def eff_color(r):
        if np.isnan(r): return "#E0E0E0"
        if r >= 0.5:    return "#1565C0"   # large
        if r >= 0.3:    return "#2980B9"   # medium
        if r >= 0.1:    return "#85C1E9"   # small
        return "#D6EAF8"                   # negligible

    eff_cols = [eff_color(v) for v in eff_daily]
    bars_c = axC.bar(x, eff_daily, width=0.6, color=eff_cols,
                     edgecolor="white", linewidth=0.6, zorder=3)
    # Reference lines
    for val, lbl, col in [(0.5,"Large (0.5)","#1565C0"),
                           (0.3,"Medium (0.3)","#2980B9"),
                           (0.1,"Small (0.1)","#85C1E9")]:
        axC.axhline(val, color=col, lw=1.1, ls="--", alpha=0.75, label=lbl)

    for i, v in enumerate(eff_daily):
        if not np.isnan(v) and v > 0:
            axC.text(i, v+0.005, f"{v:.2f}", ha="center", va="bottom",
                     fontsize=9.5, fontweight="bold")

    axC.set_xticks(x); axC.set_xticklabels(codes, rotation=0, ha="center", fontsize=10)
    axC.set_ylabel("Effect Size  r = Z/sqrt(n)\n[Cohen 1988]", fontsize=11)
    axC.set_xlabel("Station", fontsize=11, labelpad=5)
    axC.set_title("(c)  Effect Size — Daily Error Wilcoxon Test\n"
                  "     r >= 0.5 large  |  >= 0.3 medium  |  >= 0.1 small",
                  loc="left", fontsize=11, fontweight="bold", pad=5)
    axC.legend(fontsize=9.5, frameon=True, edgecolor="#B0BEC5",
               loc="upper right", ncol=3, handlelength=1.6)
    axC.spines["top"].set_visible(False); axC.spines["right"].set_visible(False)
    axC.set_ylim(0, max(0.7, float(np.nanmax(eff_daily))+0.10) if n_s > 0 else 0.7)

    # ── Panel D: Summary proportion ────────────────────────────────────
    all_tests = (["Daily\nErrors"] +
                 [f"Extreme\n{i}" for i in idx_names])
    n_tests = len(all_tests)

    # Proportion with p_one < 0.05
    prop_p05  = [
        (np.sum(p_daily < 0.05) / np.sum(~np.isnan(p_daily))
         if np.sum(~np.isnan(p_daily)) > 0 else 0.0),
    ]
    for idx in idx_names:
        pv_arr = np.array([extreme_wilcoxon.get(s,{}).get(idx,{}).get("p_one",np.nan)
                           for s in stns_str])
        n_valid = np.sum(~np.isnan(pv_arr))
        prop_p05.append(float(np.sum(pv_arr < 0.05) / n_valid) if n_valid > 0 else 0.0)

    # FDR proportion
    prop_fdr = [
        (sum(1 for r in daily_wilcoxon if r.get("sig_fdr")=="sig") / n_s),
    ]
    for idx in idx_names:
        cnt = sum(1 for s in stns_str
                  if extreme_wilcoxon.get(s,{}).get(idx,{}).get("sig_fdr")=="sig")
        prop_fdr.append(cnt / n_s)

    xx = np.arange(n_tests); bw2 = 0.38
    axD.bar(xx-bw2/2, [v*100 for v in prop_p05], width=bw2,
            color="#1E8449", alpha=0.85, edgecolor="white",
            linewidth=0.6, label="p < 0.05 (uncorrected)", zorder=3)
    axD.bar(xx+bw2/2, [v*100 for v in prop_fdr], width=bw2,
            color="#2980B9", alpha=0.85, edgecolor="white",
            linewidth=0.6, label="FDR significant (q < 0.05)", zorder=3)
    axD.axhline(50, color="grey", lw=0.9, ls="--", alpha=0.6,
                label="50% threshold")

    for xi, (p05, fdr_v) in enumerate(zip(prop_p05, prop_fdr)):
        axD.text(xi-bw2/2, p05*100+1, f"{p05*100:.0f}%",
                 ha="center", va="bottom", fontsize=9.5, fontweight="bold",
                 color="#1E8449")
        axD.text(xi+bw2/2, fdr_v*100+1, f"{fdr_v*100:.0f}%",
                 ha="center", va="bottom", fontsize=9.5, fontweight="bold",
                 color="#2980B9")

    axD.set_xticks(xx)
    axD.set_xticklabels(all_tests, rotation=0, ha="center", fontsize=10)
    axD.set_ylabel("Stations with Significant Improvement (%)", fontsize=11)
    axD.set_xlabel("Test", fontsize=11, labelpad=5)
    axD.set_ylim(0, 110)
    axD.set_title("(d)  Proportion of Stations — Significant Improvement After QDM\n"
                  "     Uncorrected p<0.05 vs FDR-corrected q<0.05",
                  loc="left", fontsize=11, fontweight="bold", pad=5)
    axD.legend(fontsize=9.5, frameon=True, edgecolor="#B0BEC5", loc="upper right")
    axD.spines["top"].set_visible(False); axD.spines["right"].set_visible(False)

    fig.suptitle(
        "Statistical Significance Testing — "
        "Wilcoxon Signed-Rank Test (Non-Parametric, One-Tailed)\n"
        "H$_1$: QDM Bias Correction Significantly Reduces Errors vs Raw CMIP6  |  "
        f"Obs: {period_obs}  |  "
        "FDR = Benjamini-Hochberg correction",
        fontsize=13, fontweight="bold")

    savefig(fig, out_dir/f"{prefix}_Fig7_SignificanceTesting")

    # Individual sub-panels
    for sfx, title, draw_fn in [
        ("a_Daily_pvalues", "Daily Error Wilcoxon — p-value Strip",
         lambda ax_s: (
             ax_s.bar(x, -np.log10(np.where(np.isnan(p_daily),1.0,p_daily)),
                      width=bw, color=p_colors, edgecolor="white",
                      linewidth=0.6, zorder=3) or
             [ax_s.axhline(-np.log10(v), color=c, lw=1.2, ls="--", label=f"p={v}")
              for v,c in [(0.05,"#C0392B"),(0.01,"#E67E22"),(0.001,"#8E44AD")]] or
             (ax_s.set_xticks(x), ax_s.set_xticklabels(codes, rotation=0, ha="center", fontsize=11),
              ax_s.set_ylabel("-log10(p-value)", fontsize=12),
              ax_s.set_xlabel("Station", fontsize=12),
              ax_s.legend(fontsize=10, frameon=True, loc="upper right"),
              ax_s.spines["top"].set_visible(False),
              ax_s.spines["right"].set_visible(False),
              ax_s.set_ylim(bottom=0))
         )),
        ("b_Extreme_pvalues", "Extreme Index Wilcoxon — p-value Heatmap",
         lambda ax_s: (
             setattr(ax_s, "_im_result", ax_s.imshow(
                 log_p_ext, cmap="RdYlGn", vmin=0, vmax=4,
                 aspect="auto", interpolation="nearest")) or
             [ax_s.text(si, ii,
                        _sig_stars(p_ext[ii,si]) if _sig_stars(p_ext[ii,si]) not in ("—","ns")
                        else "ns",
                        ha="center", va="center", fontsize=10, fontweight="bold",
                        color="white" if log_p_ext[ii,si]>2.5 else "black")
              for ii in range(n_idx) for si in range(n_s)] or
             (ax_s.set_xticks(range(n_s)),
              ax_s.set_xticklabels(codes, rotation=0, ha="center", fontsize=11),
              ax_s.set_yticks(range(n_idx)),
              ax_s.set_yticklabels(idx_names, fontsize=11),
              ax_s.set_xlabel("Station", fontsize=12),
              plt.colorbar(ax_s._im_result, ax=ax_s, orientation="horizontal",
                           pad=0.20, fraction=0.06, shrink=0.85,
                           label="-log10(p-value)"))
         )),
    ]:
        try:
            fig_s, ax_s = plt.subplots(1, 1, figsize=(13, 6))
            draw_fn(ax_s)
            fig_s.suptitle(f"{title}\n{period_obs}",
                            fontsize=14, fontweight="bold")
            savefig(fig_s, out_dir/f"{prefix}_Fig7_{sfx}")
        except Exception:
            plt.close("all")


# ─── Excel Sheet S11: Significance Testing ─────────────────────────────────
def write_significance_sheet(wb, stns, smap,
                               daily_wilcoxon: list,
                               extreme_wilcoxon: dict,
                               period_obs: str):
    """
    Add S11 Significance Tests sheet to workbook.
    Part A: Daily error Wilcoxon per station
    Part B: Extreme index Wilcoxon per station × index
    """
    stns_str  = [str(s) for s in stns]
    codes     = [smap[s] for s in stns_str]
    idx_names = ["Rx1day","R50p","R95p","R99p","SDII"]

    ws = wb.create_sheet("S11 Significance Tests")
    ws.sheet_view.showGridLines = False

    # Title
    nc = 14
    mxsc(ws,1,1,nc,
         "Statistical Significance Testing — Wilcoxon Signed-Rank Test (Non-Parametric, One-Tailed)",
         bold=True,fc="FFFFFF",bg=XC["title"],sz=12,align="left")
    ws.row_dimensions[1].height = 24
    mxsc(ws,2,1,nc,
         f"H1: QDM errors < Raw errors (BC improves performance) | "
         f"alpha=0.05 | Obs period: {period_obs} | "
         "FDR correction: Benjamini-Hochberg (1995) | "
         "Effect size r=Z/sqrt(n) [Cohen 1988]: small=0.1, medium=0.3, large=0.5 | "
         "Ref: Wilcoxon (1945) Biometrics Bull. 1:80-83",
         italic=True,fc="FFFFFF",bg=XC["sub"],sz=8.5)
    ws.row_dimensions[2].height = 14

    # ── Part A: Daily ──────────────────────────────────────────────────
    mxsc(ws,4,1,nc,
         "Part A: Wilcoxon Signed-Rank Test on DAILY Absolute Errors  "
         "(|err_BC| vs |err_Raw|, paired by time step)",
         bold=True,fc="FFFFFF",bg=XC["hdr"],sz=10)
    ws.row_dimensions[4].height = 20

    hdr_a = ["Station","Code","n_pairs",
              "Median |err_Raw| (mm)","Median |err_BC| (mm)","Reduction (%)",
              "Mean |err_Raw| (mm)","Mean |err_BC| (mm)",
              "W-statistic","p-value (two-tailed)","p-value (one-tailed)",
              "Significance","Effect size r","FDR significant"]
    for ci,h in enumerate(hdr_a,1):
        xsc(ws,5,ci,h,bold=True,fc="FFFFFF",bg=XC["hdr"],border=tb(),sz=9,wrap=True)
    ws.row_dimensions[5].height = 46

    for ri, (r, stn, code) in enumerate(zip(daily_wilcoxon, stns_str, codes), 6):
        med_r = r.get("median_err_raw",np.nan)
        med_b = r.get("median_err_bc", np.nan)
        red   = round((med_r-med_b)/med_r*100,1)                 if not (np.isnan(med_r) or np.isnan(med_b) or med_r==0) else np.nan
        p1    = r.get("p_one",np.nan)
        eff_r = r.get("effect_r",np.nan)
        sig   = r.get("sig","—")
        fdr   = r.get("sig_fdr","ns")
        bg_row= XC["improve"] if (not np.isnan(p1) and p1<0.05) else XC["white"]

        vals = [stn, code,
                r.get("n_pairs",np.nan),
                round(med_r,4) if not np.isnan(med_r) else "—",
                round(med_b,4) if not np.isnan(med_b) else "—",
                f"{red:.1f}%" if not np.isnan(red) else "—",
                round(r.get("mean_err_raw",np.nan),4) if not np.isnan(r.get("mean_err_raw",np.nan)) else "—",
                round(r.get("mean_err_bc",np.nan),4)  if not np.isnan(r.get("mean_err_bc",np.nan))  else "—",
                round(r.get("W",np.nan),2) if not np.isnan(r.get("W",np.nan)) else "—",
                round(r.get("p_two",np.nan),6) if not np.isnan(r.get("p_two",np.nan)) else "—",
                round(p1,6) if not np.isnan(p1) else "—",
                sig, eff_r if not np.isnan(eff_r) else "—",
                "Yes" if fdr=="sig" else "No"]
        for ci,v in enumerate(vals,1):
            cell = xsc(ws,ri,ci,v,bg=bg_row,border=tb(),sz=9,
                       align="left" if ci<=2 else "right")
            if ci==12:  # significance column
                if sig not in ("—","ns"):
                    cell.font=Font(bold=True,color="1B5E20",name="Calibri",size=9)
                    cell.fill=xfill(XC["improve"])
            if ci==14:  # FDR
                if fdr=="sig":
                    cell.fill=xfill("DDEEFF")
                    cell.font=Font(bold=True,color="1565C0",name="Calibri",size=9)
        ws.row_dimensions[ri].height = 15

    # Widths Part A
    for ci,w in enumerate([10,6,8,16,16,12,16,16,12,18,18,12,12,12],1):
        cw(ws,ci,w)

    # ── Part B: Extreme Indices ────────────────────────────────────────
    row_b_start = 6 + len(stns) + 3
    mxsc(ws, row_b_start,1,nc,
         "Part B: Wilcoxon Signed-Rank Test on ANNUAL EXTREME INDEX Errors  "
         "(|BC_annual-Obs_annual| vs |Raw_annual-Obs_annual|, paired by year)",
         bold=True,fc="FFFFFF",bg=XC["hdr"],sz=10)
    ws.row_dimensions[row_b_start].height = 20

    hdr_b = ["Station","Code","Index","n_years",
              "Median |err_Raw|","Median |err_BC|",
              "W-statistic","p-value (one-tailed)",
              "Significance","Effect size r","FDR significant"]
    for ci,h in enumerate(hdr_b,1):
        xsc(ws,row_b_start+1,ci,h,bold=True,fc="FFFFFF",bg=XC["hdr"],
            border=tb(),sz=9,wrap=True)
    ws.row_dimensions[row_b_start+1].height = 36

    ri_b = row_b_start + 2
    for stn, code in zip(stns_str, codes):
        for idx in idx_names:
            res = extreme_wilcoxon.get(stn,{}).get(idx,{})
            p1  = res.get("p_one", np.nan)
            sig = res.get("sig","—")
            fdr = res.get("sig_fdr","ns")
            er  = res.get("effect_r",np.nan)
            mr  = res.get("median_err_raw",np.nan)
            mb  = res.get("median_err_bc", np.nan)
            bg_b = XC["improve"] if (not np.isnan(p1) and p1<0.05) else XC["white"]

            vals = [stn, code, idx,
                    res.get("n_years",np.nan),
                    round(mr,3) if not np.isnan(mr) else "—",
                    round(mb,3) if not np.isnan(mb) else "—",
                    round(res.get("W",np.nan),2) if not np.isnan(res.get("W",np.nan)) else "—",
                    round(p1,6) if not np.isnan(p1) else "—",
                    sig,
                    round(er,4) if not np.isnan(er) else "—",
                    "Yes" if fdr=="sig" else "No"]
            for ci,v in enumerate(vals,1):
                cell = xsc(ws,ri_b,ci,v,bg=bg_b,border=tb(),sz=9,
                           align="left" if ci<=3 else "right")
                if ci==9 and sig not in ("—","ns"):
                    cell.font=Font(bold=True,color="1B5E20",name="Calibri",size=9)
                    cell.fill=xfill(XC["improve"])
                if ci==11 and fdr=="sig":
                    cell.fill=xfill("DDEEFF")
                    cell.font=Font(bold=True,color="1565C0",name="Calibri",size=9)
            ws.row_dimensions[ri_b].height = 14
            ri_b += 1
        ws.row_dimensions[ri_b-1].height = 5  # spacer after each station

    # ── Interpretation summary ─────────────────────────────────────────
    ri_note = ri_b + 2
    mxsc(ws, ri_note,1,nc,
         "Interpretation Guide",
         bold=True,fc="FFFFFF",bg=XC["sub"],sz=10)
    ws.row_dimensions[ri_note].height = 20; ri_note += 1
    notes = [
        ("H0 / H1",
         "H0: median(|err_BC|) = median(|err_Raw|)  vs  "
         "H1: median(|err_BC|) < median(|err_Raw|)  [one-tailed, directional]"),
        ("Significance",
         "*** p<0.001  |  ** p<0.01  |  * p<0.05  |  ns: not significant (p>=0.05)"),
        ("Effect Size r",
         "r = Z/sqrt(n)  [Cohen 1988]: negligible <0.1 | small 0.1-0.3 | "
         "medium 0.3-0.5 | large >=0.5"),
        ("FDR",
         "Benjamini-Hochberg (1995) False Discovery Rate correction at q=0.05 "
         "controls Type-I error across multiple comparisons"),
        ("Why Wilcoxon?",
         "Rainfall data is skewed, zero-inflated, non-normal — "
         "parametric t-tests are inappropriate. "
         "Wilcoxon Signed-Rank test is the standard non-parametric alternative "
         "for paired comparisons. Ref: Wilcoxon (1945) Biometrics Bull. 1:80-83"),
    ]
    alt=[PatternFill("solid",fgColor="DEEAF1"),PatternFill("solid",fgColor="FFFFFF")]
    for ri_n,(k,v) in enumerate(notes, ri_note):
        fl=alt[ri_n%2]
        for ci,txt in enumerate([k,v],1):
            cell=xsc(ws,ri_n,ci,txt,bold=(ci==1),sz=9,align="left",border=tb())
            cell.fill=fl
            if ci==2: cell.alignment=Alignment(horizontal="left",vertical="top",wrap_text=True)
        ws.row_dimensions[ri_n].height=38

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  9.  MAIN                                                               ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def main():
    SEP = "═"*72
    print(SEP)
    print("  Research Gap Analysis  v3.1  (Bug-Fix Edition)")
    print("  \"Does QDM Improve Station-Scale Rainfall Representation?\"")
    print("  Multi-Model | Multi-Station | Daily / Monthly / Wet-Season")
    print("  มาตรฐาน Nature / Elsevier / Q1–Q4 / TCI1")
    print(SEP)

    try:
        work_dir = (sys.argv[1].strip('"').strip("'")
                    if len(sys.argv) > 1
                    else str(Path(os.path.abspath(__file__)).parent))
    except Exception:
        work_dir = os.getcwd()

    out_dir  = Path(work_dir)
    print(f"  โฟลเดอร์ : {work_dir}\n")

    # ── Discover files ──────────────────────────────────────────────────
    print("  ค้นหาไฟล์ ...")
    obs_path, raw_model_paths, bc_model_paths = discover_files(work_dir)
    if obs_path is None:
        sys.exit("  ✗  ไม่พบไฟล์ Observed — ยุติการทำงาน")

    all_models = sorted(set(raw_model_paths)|set(bc_model_paths))
    paired     = [m for m in all_models
                  if m in raw_model_paths and m in bc_model_paths]
    print(f"\n  Models (all): {all_models}")
    print(f"  Models (paired Raw+BC): {paired}")
    print("-"*72)

    # ── Load Observed ───────────────────────────────────────────────────
    print("\n  โหลดข้อมูล ...")
    obs_d, stns = load_daily(obs_path, "Observed")
    if obs_d is None: sys.exit("  ✗  โหลด Observed ล้มเหลว")

    stns_str   = [str(s) for s in stns]
    smap       = short_labels(stns)
    period_obs = _period(obs_d)
    base_name  = Path(obs_path).stem
    prefix     = f"Output_RGv3_{base_name}"

    # Select a representative model for single-model figures:
    # Priority: (1) paired model, (2) first model with BC, (3) first model with Raw.
    if paired:
        model_used = paired[0]
    elif bc_model_paths:
        model_used = sorted(bc_model_paths.keys())[0]
    elif raw_model_paths:
        model_used = sorted(raw_model_paths.keys())[0]
    else:
        model_used = None
    print(f"  Representative model for figures: {model_used}")

    raw_d, bc_d = None, None
    if model_used and model_used in raw_model_paths:
        raw_d, _ = load_daily(raw_model_paths[model_used], f"Raw/{model_used}")
    if model_used and model_used in bc_model_paths:
        bc_d,  _ = load_daily(bc_model_paths[model_used], f"BC/{model_used}")
    # If the representative model only has BC (no Raw), also load any available Raw
    if raw_d is None and raw_model_paths:
        first_raw = sorted(raw_model_paths.keys())[0]
        raw_d, _ = load_daily(raw_model_paths[first_raw], f"Raw/{first_raw}")
        print(f"  Using Raw/{first_raw} as Raw reference for single-model figures")

    # Load all models (for ensemble mean + multi-model Taylor)
    all_raw_dfs = {}
    all_bc_dfs  = {}
    for m in all_models:
        if m in raw_model_paths:
            df, _ = load_daily(raw_model_paths[m], f"Raw/{m}")
            all_raw_dfs[m] = df
        if m in bc_model_paths:
            df, _ = load_daily(bc_model_paths[m], f"BC/{m}")
            all_bc_dfs[m] = df

    period_sim = _period(raw_d) if raw_d is not None else "N/A"
    print(f"\n  {len(stns)} stns  |  Obs:{period_obs}  |  Sim:{period_sim}")

    # ── Temporal aggregations ───────────────────────────────────────────
    obs_m  = to_monthly(obs_d);  raw_m  = to_monthly(raw_d);   bc_m  = to_monthly(bc_d)
    obs_a  = to_annual(obs_d);   raw_a  = to_annual(raw_d);    bc_a  = to_annual(bc_d)
    obs_ws = to_seasonal(obs_d, WET_MONTHS)
    raw_ws = to_seasonal(raw_d, WET_MONTHS)
    bc_ws  = to_seasonal(bc_d,  WET_MONTHS)

    # Ensemble means
    ens_raw = ensemble_mean(all_raw_dfs)
    ens_bc  = ensemble_mean(all_bc_dfs)
    print(f"  Ensemble mean computed from {len(all_raw_dfs)} Raw models"
          f" and {len(all_bc_dfs)} BC models")

    # ── Station coordinates ─────────────────────────────────────────────
    coords_df = load_station_coordinates(work_dir, stns)

    # ── Performance metrics ─────────────────────────────────────────────
    print("\n  คำนวณ performance metrics ...")
    obs_d_c, raw_d_c = align_dfs(obs_d, raw_d)
    obs_d_c, bc_d_c  = align_dfs(obs_d, bc_d)
    obs_m_c, raw_m_c = align_dfs(obs_m, raw_m)
    obs_m_c, bc_m_c  = align_dfs(obs_m, bc_m)
    obs_ws_c, raw_ws_c = align_dfs(obs_ws, raw_ws)
    obs_ws_c, bc_ws_c  = align_dfs(obs_ws, bc_ws)

    met_d_raw,  met_d_bc  = [], []
    met_m_raw,  met_m_bc  = [], []
    met_ws_raw, met_ws_bc = [], []

    for stn in stns_str:
        std_d  = float(np.std(gcol(obs_d,  stn),ddof=1)) if len(gcol(obs_d, stn))>1 else np.nan
        std_m  = float(obs_m[stn].std(ddof=1))  if obs_m  is not None and stn in obs_m.columns  else np.nan
        std_ws = float(obs_ws[stn].std(ddof=1)) if obs_ws is not None and stn in obs_ws.columns else np.nan

        # Daily — use perf_from_df so arrays are ALWAYS aligned on the
        # common DatetimeIndex (avoids shape-mismatch when raw/bc is None).
        mr = perf_from_df(obs_d_c, raw_d_c, stn)
        mb = perf_from_df(obs_d_c, bc_d_c,  stn)
        mr.update({"Station": stn, "std_obs": std_d})
        mb.update({"Station": stn, "std_obs": std_d})
        met_d_raw.append(mr); met_d_bc.append(mb)

        # Monthly
        mr_m = perf_from_df(obs_m_c,raw_m_c,stn); mr_m.update({"Station":stn,"std_obs":std_m})
        mb_m = perf_from_df(obs_m_c,bc_m_c, stn); mb_m.update({"Station":stn,"std_obs":std_m})
        met_m_raw.append(mr_m); met_m_bc.append(mb_m)

        # Wet Season
        mr_ws = perf_from_df(obs_ws_c,raw_ws_c,stn); mr_ws.update({"Station":stn,"std_obs":std_ws})
        mb_ws = perf_from_df(obs_ws_c,bc_ws_c, stn); mb_ws.update({"Station":stn,"std_obs":std_ws})
        met_ws_raw.append(mr_ws); met_ws_bc.append(mb_ws)

        print(f"    {stn} ({smap[stn]})  "
              f"KGE_raw={mr.get('KGE',np.nan):.3f}  "
              f"KGE_qdm={mb.get('KGE',np.nan):.3f}")

    # Ensemble Skill Score (CORRECT pooled definition)
    ens_ss_raw = ensemble_skill_score(obs_d, ens_raw, stns_str)
    ens_ss_bc  = ensemble_skill_score(obs_d, ens_bc,  stns_str)
    print(f"\n  Ensemble Skill Score (pooled, Gleckler 2008):")
    print(f"    Raw Ensemble: SS = {ens_ss_raw:.4f}")
    print(f"    BC  Ensemble: SS = {ens_ss_bc:.4f}")

    # ── Spatial metrics ─────────────────────────────────────────────────
    print("\n  คำนวณ spatial metrics ...")
    obs_corr = spatial_correlation_matrix(obs_m, stns_str) if obs_m is not None else None
    raw_corr = spatial_correlation_matrix(raw_m, stns_str) if raw_m is not None else None
    bc_corr  = spatial_correlation_matrix(bc_m,  stns_str) if bc_m  is not None else None

    sp_err_raw, sp_err_bc = [], []
    if obs_corr is not None:
        for i in range(len(stns_str)):
            for j in range(i+1, len(stns_str)):
                s1, s2 = stns_str[i], stns_str[j]
                if s1 in obs_corr.index and s2 in obs_corr.index:
                    ro = obs_corr.loc[s1,s2]
                    if raw_corr is not None and s1 in raw_corr.index:
                        sp_err_raw.append(abs(raw_corr.loc[s1,s2]-ro))
                    if bc_corr is not None and s1 in bc_corr.index:
                        sp_err_bc.append(abs(bc_corr.loc[s1,s2]-ro))

    obs_a2, raw_a2 = align_dfs(obs_a, raw_a)
    obs_a2, bc_a2  = align_dfs(obs_a, bc_a)
    cv_obs_m, _ = spatial_cv(obs_a2, stns_str)
    cv_raw_m, _ = spatial_cv(raw_a2, stns_str)
    cv_bc_m,  _ = spatial_cv(bc_a2,  stns_str)

    sp_metrics = {
        "mean_spatial_corr_err_raw": float(np.mean(sp_err_raw)) if sp_err_raw else np.nan,
        "mean_spatial_corr_err_bc":  float(np.mean(sp_err_bc))  if sp_err_bc  else np.nan,
        "spatial_cv_obs_mean": cv_obs_m,
        "spatial_cv_raw_mean": cv_raw_m,
        "spatial_cv_bc_mean":  cv_bc_m,
    }

    # ── Distribution alignment ──────────────────────────────────────────
    print("\n  คำนวณ distribution alignment ...")
    def _qq_rmse(obs_arr, sim_arr):
        probs=np.linspace(1,99,100)
        wo=obs_arr[obs_arr>=WET_THR]; ws=sim_arr[sim_arr>=WET_THR]
        if len(wo)<10 or len(ws)<10: return np.nan
        return float(np.sqrt(np.mean((np.percentile(ws,probs)-np.percentile(wo,probs))**2)))

    def _ks(a,b):
        wa=a[a>=WET_THR]; wb=b[b>=WET_THR]
        return float(sps.ks_2samp(wa,wb)[0]) if len(wa)>=5 and len(wb)>=5 else np.nan

    qq_raw_l=[]; qq_bc_l=[]; ks_raw_l=[]; ks_bc_l=[]
    for stn in stns_str:
        ov=gcol(obs_d,stn)
        rv=gcol(raw_d,stn) if raw_d is not None else np.array([])
        bv=gcol(bc_d, stn) if bc_d  is not None else np.array([])
        qq_raw_l.append(_qq_rmse(ov,rv)); qq_bc_l.append(_qq_rmse(ov,bv))
        ks_raw_l.append(_ks(ov,rv));      ks_bc_l.append(_ks(ov,bv))

    dist_metrics = {
        "qq_raw": qq_raw_l, "qq_bc":  qq_bc_l,
        "ks_raw": ks_raw_l, "ks_bc":  ks_bc_l,
        "qq_improvement": [r-b for r,b in zip(qq_raw_l,qq_bc_l)],
        "ks_improvement": [r-b for r,b in zip(ks_raw_l,ks_bc_l)],
        "mean_qq_rmse_raw": float(np.nanmean(qq_raw_l)),
        "mean_qq_rmse_bc":  float(np.nanmean(qq_bc_l)),
        "mean_spatial_corr_err_raw": sp_metrics["mean_spatial_corr_err_raw"],
        "mean_spatial_corr_err_bc":  sp_metrics["mean_spatial_corr_err_bc"],
    }

    # ── Extreme indices ─────────────────────────────────────────────────
    print("\n  คำนวณ ETCCDI extreme indices ...")
    extremes_obs=[]; extremes_raw=[]; extremes_bc=[]
    for stn in stns_str:
        eo=etccdi_annual(obs_d, stn,"Observed"); eo["Station"]=stn; eo["Dataset"]="Observed"
        er=etccdi_annual(raw_d, stn,"Raw");      er["Station"]=stn; er["Dataset"]="Raw"
        eb=etccdi_annual(bc_d,  stn,"QDM");      eb["Station"]=stn; eb["Dataset"]="QDM"
        extremes_obs.append(eo)
        extremes_raw.append(er)
        extremes_bc.append(eb)
        print(f"    {stn}: Rx1day_raw={er.get('Rx1day',np.nan):.1f}  "
              f"Rx1day_qdm={eb.get('Rx1day',np.nan):.1f}")

    # ── Figures ─────────────────────────────────────────────────────────
    print(f"\n{'─'*72}")
    print("  สร้างรูปภาพ (PNG + PDF) ...")

    print("\n  Fig 1: Taylor Diagrams ...")
    taylor_rows = fig1_taylor(obs_d, raw_d, bc_d,
                               obs_m, raw_m, bc_m,
                               obs_ws, raw_ws, bc_ws,
                               stns, smap, all_raw_dfs, all_bc_dfs,
                               period_obs, period_sim, out_dir, prefix)

    print("\n  Fig 2: Spatial Correlation ...")
    fig2_spatial_corr(obs_m, raw_m, bc_m, stns, smap,
                      period_obs, period_sim, out_dir, prefix)

    print("\n  Fig 3: Distance-Decay & Mantel Test ...")
    mantel_results = fig3_distance_decay(obs_m, raw_m, bc_m, stns, smap,
                                          coords_df,
                                          period_obs, period_sim, out_dir, prefix)

    print("\n  Fig 4: Spatial Variability ...")
    fig4_spatial_variability(obs_a, raw_a, bc_a, stns, smap,
                              period_obs, period_sim, out_dir, prefix)

    print("\n  Fig 5: Distribution Alignment ...")
    dist_from_fig = fig5_distribution(obs_d, raw_d, bc_d, stns, smap,
                                       period_obs, period_sim, out_dir, prefix)
    # merge back
    dist_metrics.update(dist_from_fig)

    print("\n  Fig 6: Trade-off Summary (Research Gap Answer) ...")
    fig6_tradeoff(met_d_raw, met_d_bc, stns, smap,
                   sp_metrics, dist_metrics, period_obs,
                   out_dir, prefix)

    # ── Significance Testing (NEW in v3.1) ──────────────────────────────
    print(f"\n{'─'*72}")
    print("  คำนวณ Wilcoxon Signed-Rank Tests ...")

    print("\n  Part A: Wilcoxon — Daily Absolute Errors ...")
    daily_wilcoxon = wilcoxon_daily_errors(obs_d, raw_d, bc_d, stns)
    for r in daily_wilcoxon:
        sig = r.get("sig","—"); fdr = r.get("sig_fdr","ns")
        print(f"    {r['Station']:8s}  W={r.get('W',np.nan):.1f}  "
              f"p(1-tail)={r.get('p_one',np.nan):.4f}  "
              f"r={r.get('effect_r',np.nan):.3f}  {sig}"
              f"  FDR:{'sig' if fdr=='sig' else 'ns'}")

    print("\n  Part B: Wilcoxon — Extreme Index Errors ...")
    extreme_wilcoxon = wilcoxon_extreme_indices(obs_d, raw_d, bc_d, stns)
    idx_names = ["Rx1day","R50p","R95p","R99p","SDII"]
    print(f"    {'Station':10s} " +
          "  ".join(f"{i:>10s}" for i in idx_names))
    for stn in stns_str:
        row_str = f"    {stn:10s} "
        for idx in idx_names:
            res = extreme_wilcoxon.get(stn,{}).get(idx,{})
            p1  = res.get("p_one",np.nan)
            sig = res.get("sig","—")
            row_str += f"  p={p1:.3f}{sig:>4s}" if not np.isnan(p1) else f"  {'N/A':>10s}"
        print(row_str)

    print("\n  Fig 7: Significance Testing ...")
    fig7_significance(daily_wilcoxon, extreme_wilcoxon,
                      stns, smap, period_obs, out_dir, prefix)

    # ── Excel ────────────────────────────────────────────────────────────
    print(f"\n{'─'*72}")
    out_xlsx = out_dir / f"{prefix}.xlsx"
    print(f"  สร้าง Excel → {out_xlsx.name} ...")
    wb = Workbook(); wb.remove(wb.active)
    write_excel(wb, stns, smap, all_models,
                met_d_raw,  met_d_bc,
                met_m_raw,  met_m_bc,
                met_ws_raw, met_ws_bc,
                sp_metrics, dist_metrics,
                extremes_obs, extremes_raw, extremes_bc,
                taylor_rows, mantel_results or {},
                period_obs, period_sim)
    # Add S11 — significance sheet (NEW)
    write_significance_sheet(wb, stns, smap,
                              daily_wilcoxon, extreme_wilcoxon,
                              period_obs)
    wb.save(str(out_xlsx))
    print(f"  ✓  Excel saved  (11 sheets)")

    # ── Summary ──────────────────────────────────────────────────────────
    n_sig_stations = sum(1 for r in daily_wilcoxon if r.get("p_one",1)<0.05)
    n_fdr_stations = sum(1 for r in daily_wilcoxon if r.get("sig_fdr")=="sig")
    n_fig = len(list(out_dir.glob(f"{prefix}_Fig*.png")))
    print()
    print(SEP)
    print(f"  Ensemble Skill Score (pooled):  Raw={ens_ss_raw:.4f}  QDM={ens_ss_bc:.4f}")
    print(f"  Wilcoxon Daily (p<0.05)  : {n_sig_stations}/{len(stns)} stations significant")
    print(f"  Wilcoxon Daily (FDR q<0.05): {n_fdr_stations}/{len(stns)} stations significant")
    print(f"  รูปภาพ : {n_fig} PNG" + (" + PDF" if SAVE_PDF else ""))
    print(f"  Excel  : {out_xlsx.name}  (11 sheets)")
    print(f"  บันทึกใน: {work_dir}")
    print(SEP)


if __name__ == "__main__":
    main()
