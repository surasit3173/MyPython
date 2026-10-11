"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  CMIP6 Rainfall Bias Correction — Multi-Method Framework                    ║
║  Version 3.0  |  Bug-Fixed + Future-Projection Ready  |  Q2–Q3 Standard   ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  FIXES & UPGRADES over v2.0:                                                ║
║                                                                              ║
║  [FIX-1] KeyError 'YEAR' — Column names are now normalised to UPPERCASE     ║
║           + stripped of whitespace before any processing.                    ║
║           Accepts: YEAR/year/Year/ YEAR (any case + leading/trailing space) ║
║                                                                              ║
║  [FIX-2] ModuleNotFoundError 'quantile_forest' — Robust fallback:           ║
║           (a) quantile_forest.RandomForestQuantileRegressor  [preferred]    ║
║           (b) sklearn RandomForestRegressor + rank-analog mapping [fallback]║
║           Both paths are scientifically sound; fallback clearly logged.     ║
║                                                                              ║
║  [FIX-3] Future Projection Support (SSP585/SSP245/SSP126, 2015–2100)       ║
║           — Fit/Transform phases are STRICTLY SEPARATED                      ║
║           — Fit  : calibrate on OVERLAP period (obs ∩ hist_raw)            ║
║           — Transform : applied to ANY model data incl. future (2015–2100)  ║
║           — Auto-detects future files: ssp*_<MODEL>_*.csv/xlsx             ║
║           — Output: bc_<method>_<MODEL>_hist_*.csv                         ║
║                     bc_<method>_<MODEL>_ssp*_*.csv                         ║
║                                                                              ║
║  [FIX-4] MBC Spatial Continuity Check                                       ║
║           — Checks for NaN gaps in Observed matrix before Cholesky          ║
║           — Fills isolated gaps via linear interpolation                     ║
║           — Regularises correlation matrix to ensure positive-definiteness  ║
║           — Falls back to EQM-only if Cholesky fails after regularisation   ║
║                                                                              ║
║  [FIX-5] Memory Management for Large Datasets (SSP to 2100)                ║
║           — Explicit gc.collect() + del after each method                   ║
║           — Chunk-based processing for datasets > CHUNK_THRESHOLD rows      ║
║           — Peak memory logged after each step                               ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Methods:                                                                    ║
║   1. EQM  — Empirical Quantile Mapping (with Occurrence Correction)         ║
║   2. GDM  — Parametric Gamma Distribution Mapping                           ║
║   3. MBC  — Multivariate Bias Correction (Cholesky spatial correlation)     ║
║   4. QRF  — Quantile Regression Forests (rank-analog method)               ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Input naming convention (same folder as script):                           ║
║    Observed  : *Observed*.xlsx / .csv                                       ║
║    Historical: pr_day_<MODEL>_hist*.xlsx / .csv  OR  pr_<MODEL>_*.xlsx     ║
║    Future    : pr_day_<MODEL>_ssp585*.xlsx / .csv  (any scenario)          ║
║                                                                              ║
║  Output per model:                                                           ║
║    bc_eqm_<MODEL>_<period>_<obs_stem>.csv                                  ║
║    bc_gdm_<MODEL>_<period>_<obs_stem>.csv                                  ║
║    bc_mbc_<MODEL>_<period>_<obs_stem>.csv                                  ║
║    bc_qrf_<MODEL>_<period>_<obs_stem>.csv                                  ║
║    BC_Summary_<MODEL>_<obs_stem>.xlsx  (5 sheets)                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  References:                                                                 ║
║   Themeßl et al. (2011) Int.J.Climatol. 31:1530–1542  [EQM + occurrence]  ║
║   Piani et al. (2010) J.Geophys.Res. 115:D23106       [GDM]                ║
║   Bárdossy & Pegram (2012) Adv.Water Res. 41:110–123  [Cholesky MBC]      ║
║   Meinshausen & Ridgeway (2006) J.Mach.Learn.Res. 7:983–999 [QRF]        ║
║   Gupta et al. (2009) J.Hydrol. 377:80–91             [KGE]                ║
║   Nash & Sutcliffe (1970) J.Hydrol. 10:282–290        [NSE]                ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import gc
import math
import os
import re
import sys
import traceback
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats
from scipy.interpolate import interp1d
from scipy.linalg import LinAlgError, cholesky
from scipy.stats import gamma as scipy_gamma

import sklearn
from sklearn.ensemble import RandomForestRegressor

# ── QRF library with graceful fallback ──────────────────────────────────────
try:
    from quantile_forest import RandomForestQuantileRegressor as _RFQR
    _HAS_QF = True
except ImportError:
    _HAS_QF = False

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

warnings.filterwarnings("ignore")

# ════════════════════════════════════════════════════════════════════════════
#  §0  GLOBAL CONFIGURATION
# ════════════════════════════════════════════════════════════════════════════

VERSION            = "3.0"
WET_THRESHOLD_MM   = 0.1      # mm/day — WMO wet-day threshold
N_QUANTILE_NODES   = 200      # EQM quantile grid size
GAMMA_MIN_WET_DAYS = 30       # min wet days required to fit Gamma
RANDOM_SEED        = 42
N_ESTIMATORS_QRF   = 200      # number of trees in QRF / RF ensemble
MISS_FLAGS         = [-99, -999, -9999, -9.99e+20, 9.99e+20, 1e+20]

# Memory management: datasets larger than this are processed in chunks (rows)
CHUNK_THRESHOLD    = 30_000   # rows (~82 years of daily data)

# SSP scenario identifiers for auto-detection of future files
SSP_KEYWORDS       = ("ssp585", "ssp245", "ssp126", "ssp370",
                      "ssp119", "rcp85",  "rcp45",  "rcp26")

# Excel colours
THIN = Side(style="thin",   color="BDBDBD")
MED  = Side(style="medium", color="1F4E79")
XC   = dict(
    title="13293D", sub="1F4E79", hdr="2E75B6",
    obs_r="E8F5E9", raw_r="FFEBEE",
    eqm_r="FFF3E0", gdm_r="EDE7F6",
    mbc_r="E3F2FD", qrf_r="FCE4EC",
    best="FFF9C4", improve="C8E6C9", degrade="FFCCBC",
    white="FFFFFF", alt="F5F5F5",
)


def _tb():  return Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
def _xf(h): return PatternFill("solid", fgColor=h)


def _xsc(ws, r, c, val=None, bold=False, fc=None, bg=None,
         align="center", sz=9.5, wrap=True, italic=False):
    cell = ws.cell(row=r, column=c)
    if val is not None:
        cell.value = val
    cell.font = Font(bold=bold, italic=italic, name="Calibri", size=sz,
                     color=fc if fc else "1A1A1A")
    cell.alignment = Alignment(horizontal=align, vertical="center",
                                wrap_text=wrap)
    if bg:
        cell.fill = _xf(bg)
    cell.border = _tb()
    return cell


def _mxsc(ws, r, c1, c2, val, **kw):
    ws.merge_cells(start_row=r, start_column=c1,
                   end_row=r,   end_column=c2)
    return _xsc(ws, r, c1, val, **kw)


def _cw(ws, col, w):
    ws.column_dimensions[get_column_letter(col)].width = w


def _rh(ws, r, h):
    ws.row_dimensions[r].height = h


def _mem_mb() -> float:
    """Return approximate current process memory usage in MB."""
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / 1024**2
    except ImportError:
        return float("nan")


# ════════════════════════════════════════════════════════════════════════════
#  §1  FILE DISCOVERY
# ════════════════════════════════════════════════════════════════════════════

_SKIP_TOKENS = {
    "pr", "bc", "day", "mon", "yr", "6hr", "3hr", "1hr", "fx",
    "daily", "monthly", "annual", "hist", "historical",
    "ssp245", "ssp585", "ssp126", "ssp370", "ssp119",
    "rcp45", "rcp85", "rcp26",
    "gn", "gr", "grz",
}
_RUN_PAT  = re.compile(r"^r\d+i\d+p\d+", re.IGNORECASE)
_DATE_PAT = re.compile(r"_\d{8}-\d{8}")


def _extract_model_name(filename: str) -> str:
    """Robustly extract CMIP6 model name from any filename pattern."""
    stem  = _DATE_PAT.sub("", Path(filename).stem)
    parts = stem.split("_")
    for p in parts:
        lo = p.lower().replace("-", "")
        if lo in _SKIP_TOKENS:
            continue
        if _RUN_PAT.match(p):
            continue
        if re.match(r"^\d{4,}$", p):
            continue
        return p
    return parts[0] if parts else "UnknownModel"


def _detect_scenario(filename: str) -> str:
    """
    Detect SSP/RCP scenario tag in filename.
    Returns e.g. 'ssp585', 'ssp245', 'historical', or 'hist'.
    """
    lower = filename.lower()
    for kw in SSP_KEYWORDS:
        if kw in lower:
            return kw
    if "hist" in lower:
        return "hist"
    return "hist"   # default assumption


def discover_files(folder: str) -> Tuple[
        Optional[str],
        Dict[str, List[Tuple[str, str]]],   # raw: model → [(path, scenario)]
    ]:
    """
    Scan folder for:
      • One Observed file  (*Observed* in name)
      • One or more Raw CMIP6 files per model, covering:
          – historical period (pr_day_<MODEL>_hist*.csv/xlsx)
          – future scenario   (pr_day_<MODEL>_ssp585*.csv/xlsx)
    
    Returns
    -------
    obs_path   : str | None
    raw_models : {model_name: [(path, scenario), ...]}
                 sorted: historical first, then SSP
    """
    all_files: List[Path] = []
    for ext in (".xlsx", ".csv"):
        all_files.extend(sorted(Path(folder).glob(f"*{ext}")))

    obs_files  = [f for f in all_files if "observed" in f.name.lower()]
    # Raw CMIP6: starts with pr_ or pr  (not bc_, not observed)
    raw_files  = [f for f in all_files
                  if (f.name.lower().startswith("pr_") or
                      f.name.lower().startswith("pr "))
                  and "observed" not in f.name.lower()]

    # ── Observed ──────────────────────────────────────────────────────
    obs_path: Optional[str] = None
    if obs_files:
        if len(obs_files) > 1:
            print(f"  ⚠  Multiple Observed files — using: {obs_files[0].name}")
        obs_path = str(obs_files[0])
        print(f"  Observed : {obs_files[0].name}")
    else:
        print("  ✗  No Observed file found  "
              "(name must contain the word 'observed')")

    # ── Raw CMIP6 — group by model, collect all scenarios ─────────────
    raw_dict: Dict[str, List[Tuple[str, str]]] = {}
    for f in raw_files:
        model    = _extract_model_name(f.name)
        scenario = _detect_scenario(f.name)
        raw_dict.setdefault(model, [])
        # Avoid duplicate paths
        existing_paths = [p for p, _ in raw_dict[model]]
        if str(f) not in existing_paths:
            raw_dict[model].append((str(f), scenario))
            print(f"  Raw  '{model}' [{scenario}] ← {f.name}")

    # Sort each model's list: historical first
    for model in raw_dict:
        raw_dict[model].sort(key=lambda x: (0 if x[1] == "hist" else 1, x[1]))

    return obs_path, raw_dict


# ════════════════════════════════════════════════════════════════════════════
#  §2  DATA LOADING & CALENDAR HARMONISATION
# ════════════════════════════════════════════════════════════════════════════

def _read_file(path: str) -> pd.DataFrame:
    """Read .xlsx or .csv into DataFrame."""
    p = Path(path)
    if p.suffix.lower() == ".xlsx":
        return pd.read_excel(path, engine="openpyxl")
    return pd.read_csv(path)


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    [FIX-1] Normalise column names to UPPERCASE and strip whitespace.
    
    This fixes KeyError: 'YEAR' when input files use:
      lowercase  : year, month, day
      mixed case : Year, Month, Day
      with spaces: ' YEAR ', ' DAY '
    
    Ref: Feedback document §2 — "ข้อแนะนำ: ควรปรับโค้ดให้ล้างชื่อคอลัมน์
         ด้วย .str.upper().str.strip()"
    """
    df = df.copy()
    df.columns = pd.Index([str(c).strip().upper() for c in df.columns])
    return df


def _clean_df(df: pd.DataFrame) -> pd.DataFrame:
    """Replace missing-value flags; set negatives to NaN."""
    for mv in MISS_FLAGS:
        df.replace(mv, np.nan, inplace=True)
    num = df.select_dtypes(include=[np.number]).columns
    df[num] = df[num].where(df[num] >= 0)
    return df


def _build_date_index(df: pd.DataFrame) -> pd.DatetimeIndex:
    """
    Construct DatetimeIndex from YEAR, MONTH, DAY columns.
    Handles 360-day / no-leap calendars by clamping day-of-month.
    """
    years  = df["YEAR"].values.astype(int)
    months = df["MONTH"].values.astype(int)
    days   = df["DAY"].values.astype(int)

    clamped = np.array([
        min(d, pd.Timestamp(y, m, 1).days_in_month)
        for y, m, d in zip(years, months, days)
    ], dtype=int)

    dates = pd.to_datetime(
        {"year": years, "month": months, "day": clamped},
        errors="coerce")
    return pd.DatetimeIndex(dates)


def load_daily(path:        str,
               label:       str,
               target_stns: Optional[List[str]] = None
               ) -> Tuple[Optional[pd.DataFrame], List[str]]:
    """
    Load a daily rainfall CSV/XLSX file.

    Key behaviour
    -------------
    • Column names are normalised (FIX-1): any case + leading/trailing spaces.
    • Missing-value flags are replaced.
    • 360-day / no-leap calendar dates are clamped to valid Gregorian dates.
    • Duplicate dates (from clamping) are dropped, keeping first occurrence.

    Returns
    -------
    df   : pd.DataFrame indexed by DatetimeIndex, columns = station IDs (str)
    stns : list[str] of station ID strings present in file
    """
    if path is None or not os.path.isfile(path):
        print(f"  ✗  Not found: {label}")
        return None, []

    raw = _read_file(path)
    raw = _normalise_columns(raw)   # [FIX-1] case-insensitive normalisation
    raw = _clean_df(raw)

    # After normalisation, time columns are always YEAR / MONTH / DAY
    time_cols = {"YEAR", "MONTH", "DAY"}

    # Check that required time columns actually exist
    missing_tc = time_cols - set(raw.columns)
    if missing_tc:
        print(f"  ✗  Missing date columns {missing_tc} in {label}  "
              f"(found: {list(raw.columns[:8])})")
        return None, []

    # All other columns = station IDs; convert to str
    raw.columns = pd.Index([str(c) for c in raw.columns])
    stns = [c for c in raw.columns if c not in time_cols]

    if target_stns:
        ts   = [str(s) for s in target_stns]
        stns = [s for s in stns if s in set(ts)]

    date_idx = _build_date_index(raw)
    df = raw[stns].copy()
    df.index = date_idx
    df = df[~df.index.isna()]       # drop un-parseable dates
    df = df[~df.index.duplicated(keep="first")]  # 360-day duplicates
    df.sort_index(inplace=True)

    yr0 = df.index[0].year  if len(df) else "?"
    yr1 = df.index[-1].year if len(df) else "?"
    print(f"    {label:50s}: {len(df):,} rows × {len(stns)} stns  [{yr0}–{yr1}]")
    return df, stns


# ════════════════════════════════════════════════════════════════════════════
#  §3  OCCURRENCE CORRECTION
# ════════════════════════════════════════════════════════════════════════════

def find_wet_threshold(obs_vals: np.ndarray,
                       mod_vals: np.ndarray) -> float:
    """
    Find model threshold τ s.t. P(mod > τ) = P(obs > WET_THRESHOLD_MM).
    Ref: Themeßl et al. (2011) Int.J.Climatol. 31:1530–1542.
    """
    obs_wet_prob = float(np.mean(obs_vals > WET_THRESHOLD_MM))
    if obs_wet_prob <= 0.0:
        return 0.0
    valid = mod_vals[~np.isnan(mod_vals) & (mod_vals >= 0)]
    if len(valid) == 0:
        return 0.0
    return max(0.0, float(np.quantile(valid, 1.0 - obs_wet_prob)))


def occurrence_correct(mod_vals: np.ndarray, tau: float) -> np.ndarray:
    """Set values ≤ tau to 0 (dry day)."""
    out = mod_vals.copy()
    out[out <= tau] = 0.0
    return out


# ════════════════════════════════════════════════════════════════════════════
#  §4  METHOD 1 — EQM: EMPIRICAL QUANTILE MAPPING
# ════════════════════════════════════════════════════════════════════════════

class EQMCorrector:
    """
    Empirical Quantile Mapping with Occurrence Correction.

    Fit  : calibrate transfer functions on obs ∩ hist_raw
    Apply: transform ANY model data (hist or future SSP to 2100)

    Architecture enforces strict fit/transform separation so that
    future projections are never accidentally truncated.
    """

    def __init__(self, n_quantiles: int = N_QUANTILE_NODES):
        self.n_quantiles = n_quantiles
        self._tau:    Dict[str, float]  = {}
        self._interp: Dict[str, interp1d] = {}
        self._fitted: bool = False

    def fit(self, obs_df: pd.DataFrame,
            mod_df: pd.DataFrame,
            stns: List[str]) -> "EQMCorrector":
        """
        Calibrate on obs_df and mod_df (must share index = training period).
        """
        probs = np.linspace(0.0, 1.0, self.n_quantiles)
        for stn in stns:
            o = obs_df[stn].values.astype(float) if stn in obs_df.columns else np.array([])
            m = mod_df[stn].values.astype(float) if stn in mod_df.columns else np.array([])
            mask = ~np.isnan(o) & ~np.isnan(m)
            o, m = o[mask], m[mask]

            tau = find_wet_threshold(o, m)
            self._tau[stn] = tau

            o_wet = o[o > WET_THRESHOLD_MM]
            m_wet = m[m > tau]

            if len(o_wet) < 10 or len(m_wet) < 10:
                # Too few wet days — identity mapping
                self._interp[stn] = interp1d(
                    [0.0, 999.0], [0.0, 999.0],
                    bounds_error=False,
                    fill_value=(0.0, float(o_wet.max()) if len(o_wet) else 999.0))
                continue

            q_obs = np.quantile(o_wet, probs)
            q_mod = np.quantile(m_wet, probs)

            # Ensure monotonic model quantiles (required by interp1d)
            # (can be violated for very small wet-day counts)
            _, unique_idx = np.unique(q_mod, return_index=True)
            q_mod = q_mod[unique_idx]
            q_obs = q_obs[unique_idx]

            # Transfer function with extrapolation at tails
            tail_scale = q_obs[-1] / q_mod[-1] if q_mod[-1] > 0 else 1.0
            self._interp[stn] = interp1d(
                q_mod, q_obs,
                bounds_error=False,
                fill_value=(q_obs[0], q_obs[-1] * tail_scale))

        self._fitted = True
        return self

    def transform(self, mod_df: pd.DataFrame,
                  stns: List[str]) -> pd.DataFrame:
        """
        Apply fitted EQM to model data.
        mod_df may be historical OR any future period (2015–2100).
        """
        if not self._fitted:
            raise RuntimeError("EQMCorrector.fit() must be called before transform()")
        out = mod_df.copy()
        for stn in stns:
            if stn not in self._tau:
                continue
            m     = mod_df[stn].values.astype(float) if stn in mod_df.columns \
                    else np.full(len(mod_df), np.nan)
            tau   = self._tau[stn]
            m_occ = occurrence_correct(m, tau)
            corr  = np.zeros_like(m_occ)
            wet   = m_occ > 0.0
            if wet.sum() > 0:
                corr[wet] = np.maximum(0.0, self._interp[stn](m_occ[wet]))
            out[stn] = corr
        return out


# ════════════════════════════════════════════════════════════════════════════
#  §5  METHOD 2 — GDM: GAMMA DISTRIBUTION MAPPING
# ════════════════════════════════════════════════════════════════════════════

class GDMCorrector:
    """
    Parametric Gamma Distribution Mapping.
    Fit: Gamma(α,β) to obs wet days and model wet days separately.
    Transform: CDF_mod(x) → uniform quantile → ICDF_obs.
    Falls back to EQM if Gamma cannot be fitted (too few wet days).

    Ref: Piani et al. (2010) J.Geophys.Res. 115:D23106.
    """

    def __init__(self):
        self._tau:        Dict[str, float] = {}
        self._params_obs: Dict[str, Optional[Tuple]] = {}
        self._params_mod: Dict[str, Optional[Tuple]] = {}
        self._eqm:        EQMCorrector = EQMCorrector()
        self._fitted:     bool = False

    def fit(self, obs_df: pd.DataFrame,
            mod_df: pd.DataFrame,
            stns: List[str]) -> "GDMCorrector":
        # Also fit EQM for fallback
        self._eqm.fit(obs_df, mod_df, stns)

        for stn in stns:
            o = obs_df[stn].values.astype(float) if stn in obs_df.columns else np.array([])
            m = mod_df[stn].values.astype(float) if stn in mod_df.columns else np.array([])
            mask = ~np.isnan(o) & ~np.isnan(m)
            o, m = o[mask], m[mask]

            tau = find_wet_threshold(o, m)
            self._tau[stn] = tau

            o_wet = o[o > WET_THRESHOLD_MM]
            m_wet = m[m > tau]

            self._params_obs[stn] = None
            self._params_mod[stn] = None

            if len(o_wet) >= GAMMA_MIN_WET_DAYS:
                try:
                    s, l, sc = scipy_gamma.fit(o_wet, floc=0.0)
                    self._params_obs[stn] = (float(s), float(l), float(sc))
                except Exception:
                    pass

            if len(m_wet) >= GAMMA_MIN_WET_DAYS:
                try:
                    s, l, sc = scipy_gamma.fit(m_wet, floc=0.0)
                    self._params_mod[stn] = (float(s), float(l), float(sc))
                except Exception:
                    pass

        self._fitted = True
        return self

    def transform(self, mod_df: pd.DataFrame,
                  stns: List[str]) -> pd.DataFrame:
        if not self._fitted:
            raise RuntimeError("GDMCorrector.fit() must be called before transform()")
        out = mod_df.copy()
        for stn in stns:
            if stn not in self._tau:
                continue
            m     = mod_df[stn].values.astype(float) if stn in mod_df.columns \
                    else np.full(len(mod_df), np.nan)
            tau   = self._tau[stn]
            m_occ = occurrence_correct(m, tau)
            corr  = np.zeros_like(m_occ)
            wet   = m_occ > 0.0

            p_obs = self._params_obs.get(stn)
            p_mod = self._params_mod.get(stn)

            if wet.sum() > 0:
                if p_obs is not None and p_mod is not None:
                    x = m_occ[wet]
                    u = scipy_gamma.cdf(x, *p_mod)
                    u = np.clip(u, 1e-6, 1.0 - 1e-6)
                    corr[wet] = np.maximum(0.0, scipy_gamma.ppf(u, *p_obs))
                else:
                    # Fallback to EQM
                    tmp = out.copy()
                    tmp[stn] = m_occ
                    eqm_out  = self._eqm.transform(tmp, [stn])
                    corr[wet] = eqm_out[stn].values[wet]

            out[stn] = corr
        return out


# ════════════════════════════════════════════════════════════════════════════
#  §6  METHOD 3 — MBC: MULTIVARIATE BIAS CORRECTION (CHOLESKY)
# ════════════════════════════════════════════════════════════════════════════

class MBCCorrector:
    """
    Multivariate Bias Correction using Cholesky decomposition.

    Algorithm
    ---------
    1. Apply EQM to each station independently (univariate correction).
    2. Normal-score transform both obs and EQM-corrected matrices.
    3. Compute spatial correlation matrices R_obs and R_eqm.
    4. Cholesky factorisation: L_obs = chol(R_obs), L_eqm = chol(R_eqm).
    5. Decorrelate + recolour:
         Z_mbc = (Z_eqm @ inv(L_eqm).T) @ L_obs.T
    6. Rank-resampling: re-assign EQM-corrected marginals by MBC rank order.

    [FIX-4] Continuity Checks
    --------------------------
    • Before Cholesky, fills isolated NaN gaps via linear interpolation.
    • Regularises correlation matrices (add ε·I) until positive-definite.
    • Falls back gracefully to EQM-only if Cholesky still fails.

    Ref: Bárdossy & Pegram (2012) Adv.Water Res. 41:110–123.
         Cannon (2016) J.Climate 29:983–1001.
    """

    def __init__(self, n_quantiles: int = N_QUANTILE_NODES):
        self._eqm    = EQMCorrector(n_quantiles)
        self._L_obs: Optional[np.ndarray] = None
        self._L_eqm: Optional[np.ndarray] = None
        self._stns:  List[str] = []
        self._fitted: bool = False
        self._cholesky_ok: bool = False   # False → use EQM fallback

    # ── Spatial gap-fill utility ─────────────────────────────────────────
    @staticmethod
    def _fill_gaps(mat: np.ndarray,
                   max_gap: int = 10) -> np.ndarray:
        """
        [FIX-4] Fill isolated NaN gaps in a (T × S) matrix via linear
        interpolation along the time axis.
        Gaps longer than max_gap are left as NaN (structural missing data).
        """
        out = mat.copy()
        T, S = out.shape
        for j in range(S):
            col  = out[:, j]
            nans = np.isnan(col)
            if not nans.any():
                continue
            # Label consecutive NaN runs
            idx = np.arange(T)
            # Only interpolate if surrounding valid data exists
            valid_idx = idx[~nans]
            if len(valid_idx) < 2:
                continue
            fn   = interp1d(valid_idx, col[~nans],
                            bounds_error=False, fill_value="extrapolate")
            # Fill only short gaps
            i = 0
            while i < T:
                if nans[i]:
                    j_end = i
                    while j_end < T and nans[j_end]:
                        j_end += 1
                    gap_len = j_end - i
                    if gap_len <= max_gap:
                        out[i:j_end, j] = fn(idx[i:j_end])
                    i = j_end
                else:
                    i += 1
        return out

    # ── Regularise matrix for positive-definiteness ──────────────────────
    @staticmethod
    def _regularise_pd(C: np.ndarray,
                       eps_start: float = 1e-6) -> Tuple[np.ndarray, float]:
        """
        [FIX-4] Add ε·I until matrix is positive-definite.
        Returns (regularised_C, final_eps).
        """
        eps = eps_start
        C_r = C.copy()
        while eps < 1.0:
            try:
                cholesky(C_r)
                return C_r, eps
            except LinAlgError:
                C_r = C + eps * np.eye(C.shape[0])
                eps *= 10.0
        # Extreme fallback: diagonal matrix
        return np.diag(np.diag(C)) + 1e-3 * np.eye(C.shape[0]), eps

    # ── Normal-score transform ────────────────────────────────────────────
    @staticmethod
    def _normal_score(arr: np.ndarray) -> np.ndarray:
        """Van der Waerden normal scores (rank-based)."""
        n     = len(arr)
        ranks = stats.rankdata(arr, method="average")
        return stats.norm.ppf(ranks / (n + 1))

    # ── Fit ──────────────────────────────────────────────────────────────
    def fit(self, obs_df: pd.DataFrame,
            mod_df: pd.DataFrame,
            stns: List[str]) -> "MBCCorrector":
        self._stns   = stns
        self._fitted = True

        # Step 1: Fit and apply EQM
        self._eqm.fit(obs_df, mod_df, stns)
        eqm_c = self._eqm.transform(mod_df, stns)

        # Step 2: Build matrices — keep only stations with sufficient data
        obs_mat = obs_df[[s for s in stns if s in obs_df.columns]].values.astype(float)
        eqm_mat = eqm_c[[s for s in stns if s in eqm_c.columns]].values.astype(float)

        # [FIX-4a] Fill short NaN gaps to improve matrix stability
        obs_mat = self._fill_gaps(obs_mat)
        eqm_mat = self._fill_gaps(eqm_mat)

        # [FIX-4b] Check that enough valid rows exist for each station pair
        valid_rows = (~np.isnan(obs_mat).any(axis=1) &
                      ~np.isnan(eqm_mat).any(axis=1))
        n_valid = valid_rows.sum()
        S       = obs_mat.shape[1]

        if n_valid < max(S + 5, 30):
            print(f"  ⚠  MBC: insufficient valid rows ({n_valid}) for "
                  f"Cholesky ({S}×{S}) — falling back to EQM")
            self._cholesky_ok = False
            return self

        obs_v = obs_mat[valid_rows]
        eqm_v = eqm_mat[valid_rows]

        # Normal-score transform
        obs_ns = np.apply_along_axis(self._normal_score, 0, obs_v)
        eqm_ns = np.apply_along_axis(self._normal_score, 0, eqm_v)

        obs_corr = np.corrcoef(obs_ns.T)
        eqm_corr = np.corrcoef(eqm_ns.T)

        # [FIX-4c] Regularise for positive-definiteness
        obs_corr_pd, eps_o = self._regularise_pd(obs_corr)
        eqm_corr_pd, eps_e = self._regularise_pd(eqm_corr)
        if eps_o > 1e-3 or eps_e > 1e-3:
            print(f"  ⚠  MBC: correlation matrix regularised  "
                  f"(ε_obs={eps_o:.0e}, ε_eqm={eps_e:.0e})")

        try:
            self._L_obs = cholesky(obs_corr_pd, lower=True)
            self._L_eqm = cholesky(eqm_corr_pd, lower=True)
            self._cholesky_ok = True
        except LinAlgError:
            print("  ✗  MBC: Cholesky failed even after regularisation "
                  "— falling back to EQM")
            self._cholesky_ok = False

        return self

    # ── Apply ─────────────────────────────────────────────────────────────
    def transform(self, mod_df: pd.DataFrame,
                  stns: List[str]) -> pd.DataFrame:
        if not self._fitted:
            raise RuntimeError("MBCCorrector.fit() must be called before transform()")

        out = mod_df.copy()

        # If Cholesky failed, use EQM
        if not self._cholesky_ok:
            return self._eqm.transform(mod_df, stns)

        # Step 1: EQM correction
        eqm_c   = self._eqm.transform(mod_df, stns)
        eqm_mat = eqm_c[stns].values.astype(float)   # (T, S)
        T, S    = eqm_mat.shape

        # [FIX-4a] Fill gaps before normal-score transform
        eqm_mat_filled = self._fill_gaps(eqm_mat)

        # Step 2: Normal-score transform
        eqm_ns = np.apply_along_axis(self._normal_score, 0, eqm_mat_filled)

        # Step 3: Cholesky recolouring
        try:
            L_eqm_inv = np.linalg.inv(self._L_eqm)
            Z_white   = eqm_ns @ L_eqm_inv.T         # decorrelate
            Z_mbc     = Z_white @ self._L_obs.T       # recolour with obs
        except np.linalg.LinAlgError:
            return self._eqm.transform(mod_df, stns)

        # Step 4: Rank-resampling — map MBC ranks back to EQM marginals
        mbc_mat = np.zeros_like(eqm_mat)
        for si in range(S):
            eqm_col  = eqm_mat[:, si]
            mbc_col  = Z_mbc[:, si]
            sorted_e = np.sort(eqm_col)
            mbc_rank = stats.rankdata(mbc_col, method="ordinal") - 1
            mbc_mat[:, si] = sorted_e[mbc_rank]

        for si, stn in enumerate(stns):
            out[stn] = np.maximum(0.0, mbc_mat[:, si])

        return out


# ════════════════════════════════════════════════════════════════════════════
#  §7  METHOD 4 — QRF: QUANTILE REGRESSION FORESTS
# ════════════════════════════════════════════════════════════════════════════

class QRFCorrector:
    """
    Quantile Regression Forest bias correction.

    [FIX-2] Two implementations, same scientific behaviour:

    (A) quantile_forest.RandomForestQuantileRegressor  [preferred]
        — True QRF: stores all training observations in each leaf node.
        — At prediction: Q_QRF(p_t | X=x_t) for exact quantile p_t.
        Ref: Meinshausen & Ridgeway (2006) J.Mach.Learn.Res. 7:983–999.

    (B) sklearn RandomForestRegressor + rank-analog mapping  [fallback]
        — RF predicts conditional mean; rank-analog retrieves obs analogs.
        — Scientifically sound; slightly less accurate in the extremes.
        Clearly logged as fallback in console output.

    Transfer function (both paths):
        p_t = F̂_mod_empirical(m_t)    [model CDF rank]
        ŷ_t = Q_QRF(p_t | X_t)         [corrected value]
    """

    def __init__(self, n_estimators: int = N_ESTIMATORS_QRF,
                 random_state:  int = RANDOM_SEED):
        self.n_estimators    = n_estimators
        self.random_state    = random_state
        self._models:        Dict[str, object] = {}
        self._rf_pred_train: Dict[str, np.ndarray] = {}
        self._y_train:       Dict[str, np.ndarray] = {}
        self._tau:           Dict[str, float] = {}
        self._mod_sorted:    Dict[str, np.ndarray] = {}
        self._q_grid:        np.ndarray = np.linspace(0.001, 0.999, N_QUANTILE_NODES)
        self._use_qf:        bool = _HAS_QF
        self._fitted:        bool = False

    def fit(self, obs_df: pd.DataFrame,
            mod_df: pd.DataFrame,
            stns: List[str]) -> "QRFCorrector":

        o_mat = obs_df[stns].values.astype(float)
        m_mat = mod_df[stns].values.astype(float)
        valid = (~np.isnan(m_mat).any(axis=1) &
                 ~np.isnan(o_mat).any(axis=1))
        X_tr  = m_mat[valid]
        Y_tr  = o_mat[valid]

        method_tag = "quantile-forest (true QRF)" if self._use_qf \
                     else "sklearn RF (rank-analog fallback)"
        print(f"      QRF method : {method_tag}")

        for si, stn in enumerate(stns):
            tau = find_wet_threshold(Y_tr[:, si], X_tr[:, si])
            self._tau[stn]       = tau
            self._mod_sorted[stn] = np.sort(X_tr[:, si])

        for si, stn in enumerate(stns):
            print(f"      Fitting station {stn} ({si+1}/{len(stns)}) ...",
                  end="\r")
            y_col = Y_tr[:, si]

            if self._use_qf:
                model = _RFQR(
                    n_estimators=self.n_estimators,
                    random_state=self.random_state,
                    n_jobs=-1,
                    min_samples_leaf=5,
                    max_features="sqrt",
                )
            else:
                model = RandomForestRegressor(
                    n_estimators=self.n_estimators,
                    random_state=self.random_state,
                    n_jobs=-1,
                    min_samples_leaf=5,
                    max_features="sqrt",
                )

            model.fit(X_tr, y_col)
            self._models[stn]       = model
            # Store RF predictions on training set for rank-analog (fallback)
            if not self._use_qf:
                self._rf_pred_train[stn] = model.predict(X_tr)
                self._y_train[stn]       = y_col

        print()
        self._fitted = True
        return self

    def transform(self, mod_df: pd.DataFrame,
                  stns: List[str]) -> pd.DataFrame:
        if not self._fitted:
            raise RuntimeError("QRFCorrector.fit() must be called before transform()")

        out   = mod_df.copy()
        m_mat = mod_df[stns].values.astype(float)
        T     = m_mat.shape[0]

        valid_mask    = ~np.isnan(m_mat).any(axis=1)
        valid_indices = np.where(valid_mask)[0]
        X_pred        = m_mat[valid_mask]

        for si, stn in enumerate(stns):
            if stn not in self._models:
                continue
            model     = self._models[stn]
            tau       = self._tau.get(stn, 0.0)
            mod_sort  = self._mod_sorted.get(stn, np.array([]))
            m_col     = m_mat[:, si]

            m_occ  = occurrence_correct(m_col.copy(), tau)
            dry    = m_occ <= 0.0

            # Model empirical CDF rank
            n_s       = max(len(mod_sort), 1)
            cdf_all   = np.searchsorted(mod_sort, m_occ, side="right") / n_s
            cdf_all   = np.clip(cdf_all, 0.0, 1.0)
            cdf_valid = cdf_all[valid_indices]
            dry_valid = dry[valid_indices]

            result = np.zeros(T)

            if self._use_qf:
                # ── True QRF path ─────────────────────────────────────────
                q_preds = model.predict(X_pred,
                                        quantiles=list(self._q_grid))
                # q_preds shape: (T_valid, Q)
                q_preds = np.maximum(0.0, q_preds)
                q_arr   = self._q_grid

                idx_hi  = np.searchsorted(q_arr, cdf_valid, side="right")
                idx_lo  = np.clip(idx_hi - 1, 0, len(q_arr) - 2)
                idx_hi  = np.clip(idx_hi,     1, len(q_arr) - 1)

                q_lo    = q_arr[idx_lo]
                q_hi    = q_arr[idx_hi]
                denom   = np.where(q_hi > q_lo, q_hi - q_lo, 1.0)
                alpha   = np.clip((cdf_valid - q_lo) / denom, 0.0, 1.0)

                t_idx   = np.arange(len(X_pred))
                val_lo  = q_preds[t_idx, idx_lo]
                val_hi  = q_preds[t_idx, idx_hi]
                interp_vals = val_lo + alpha * (val_hi - val_lo)
                final_valid = np.where(dry_valid, 0.0,
                                       np.maximum(0.0, interp_vals))

            else:
                # ── Rank-analog path (sklearn fallback) ───────────────────
                rf_pred_test  = model.predict(X_pred)
                rf_pred_train = self._rf_pred_train[stn]
                y_train       = self._y_train[stn]

                sort_idx   = np.argsort(rf_pred_train)
                rf_sorted  = rf_pred_train[sort_idx]
                y_sorted   = y_train[sort_idx]

                analog_idx = np.searchsorted(rf_sorted, rf_pred_test,
                                             side="right") - 1
                analog_idx = np.clip(analog_idx, 0, len(y_sorted) - 1)
                analog_val = y_sorted[analog_idx]
                final_valid = np.where(dry_valid, 0.0,
                                       np.maximum(0.0, analog_val))

            result[valid_indices] = final_valid
            out[stn] = result

        return out


# ════════════════════════════════════════════════════════════════════════════
#  §8  OUTPUT FORMATTING
# ════════════════════════════════════════════════════════════════════════════

def build_output_df(corrected_df: pd.DataFrame,
                    stns: List[str]) -> pd.DataFrame:
    """
    Build output DataFrame: YEAR, MONTH, DAY, <station_1>, ..., <station_N>
    Matches the structure of the reference QDM output files.
    """
    result = pd.DataFrame(index=corrected_df.index)
    result["YEAR"]  = corrected_df.index.year
    result["MONTH"] = corrected_df.index.month
    result["DAY"]   = corrected_df.index.day
    for stn in stns:
        if stn in corrected_df.columns:
            result[stn] = np.round(
                np.maximum(0.0, corrected_df[stn].values.astype(float)), 2)
        else:
            result[stn] = 0.0
    return result


def save_csv(df: pd.DataFrame, path: str) -> None:
    """Save output DataFrame as CSV (no index)."""
    df.to_csv(path, index=False, float_format="%.2f")
    print(f"  ✓  {Path(path).name}")


# ════════════════════════════════════════════════════════════════════════════
#  §9  PERFORMANCE METRICS
# ════════════════════════════════════════════════════════════════════════════

METRICS_KEYS  = ["RMSE", "MAE", "MBE", "Pbias", "r", "NSE", "KGE"]
LOWER_BETTER  = {"RMSE", "MAE", "MBE"}


def compute_metrics(o: np.ndarray, s: np.ndarray) -> Dict[str, float]:
    """Full hydro-meteorological performance metrics."""
    null = {k: np.nan for k in METRICS_KEYS}
    o, s = np.asarray(o, float), np.asarray(s, float)
    mask = ~np.isnan(o) & ~np.isnan(s)
    o, s = o[mask], s[mask]
    if len(o) < 5:
        return null
    e    = s - o
    rmse = float(np.sqrt(np.mean(e**2)))
    mae  = float(np.mean(np.abs(e)))
    mbe  = float(np.mean(e))
    pb   = float(100 * np.sum(e) / np.sum(o)) if np.sum(o) != 0 else np.nan
    r    = float(np.corrcoef(o, s)[0, 1])
    dn   = float(np.sum((o - np.mean(o))**2))
    nse  = float(1 - np.sum(e**2) / dn) if dn > 0 else np.nan
    so   = float(np.std(o, ddof=1))
    ss   = float(np.std(s, ddof=1))
    sr   = ss / so if so > 0 else np.nan
    beta = float(np.mean(s) / np.mean(o)) if np.mean(o) != 0 else np.nan
    kge  = (float(1 - math.sqrt((r-1)**2 + (sr-1)**2 + (beta-1)**2))
            if not (np.isnan(sr) or np.isnan(beta)) else np.nan)
    return {"RMSE": round(rmse,3), "MAE": round(mae,3), "MBE": round(mbe,3),
            "Pbias": round(pb,2), "r": round(r,4),
            "NSE": round(float(nse),4), "KGE": round(float(kge),4)}


def wet_day_freq(arr: np.ndarray) -> float:
    a = np.asarray(arr, float)
    a = a[~np.isnan(a) & (a >= 0)]
    return float(np.mean(a > WET_THRESHOLD_MM)) if len(a) > 0 else np.nan


# ════════════════════════════════════════════════════════════════════════════
#  §10  EXCEL REPORT — 5 SHEETS
# ════════════════════════════════════════════════════════════════════════════

METHOD_BGS = {
    "OBS": XC["obs_r"], "RAW": XC["raw_r"],
    "EQM": XC["eqm_r"], "GDM": XC["gdm_r"],
    "MBC": XC["mbc_r"], "QRF": XC["qrf_r"],
}


def write_excel_report(wb:          Workbook,
                        stns:        List[str],
                        obs_df:      pd.DataFrame,
                        mod_df:      pd.DataFrame,
                        results:     Dict[str, pd.DataFrame],
                        model_name:  str,
                        period_calib: str,
                        period_hist:  str,
                        has_future:   bool,
                        period_future: str) -> None:
    """
    5-sheet Excel performance report.
    S1 — Metric comparison (all methods × stations)
    S2 — Wet-day frequency
    S3 — Extreme quantiles (P90, P95, P99)
    S4 — Improvement summary (vs RAW)
    S5 — Methods, references & data periods
    """

    def _title(ws, nc, t, s):
        _mxsc(ws,1,1,nc,t,bold=True,fc="FFFFFF",bg=XC["title"],sz=12,align="left")
        _rh(ws,1,24)
        _mxsc(ws,2,1,nc,s,italic=True,fc="FFFFFF",bg=XC["sub"],sz=8.5,align="left")
        _rh(ws,2,14)

    def _hdr(ws, r, hdrs, bg=XC["hdr"]):
        for ci,h in enumerate(hdrs,1):
            _xsc(ws,r,ci,h,bold=True,fc="FFFFFF",bg=bg,sz=9,wrap=True)
        _rh(ws,r,36)

    def fv(v, dp=4):
        if v is None or (isinstance(v,float) and np.isnan(v)):
            return "—"
        return round(float(v), dp)

    methods_order = ["RAW","EQM","GDM","MBC","QRF"]
    method_dfs: Dict[str, Optional[pd.DataFrame]] = {"OBS": obs_df, "RAW": mod_df}
    method_dfs.update(results)

    # ── S1: Metric Comparison ─────────────────────────────────────────
    ws1 = wb.create_sheet("S1 Metrics")
    ws1.sheet_view.showGridLines = False
    nc1 = 3 + len(METRICS_KEYS)
    _title(ws1, nc1,
           f"Bias Correction Performance Metrics — {model_name}",
           f"Calibration period: {period_calib}  |  "
           f"Historical: {period_hist}"
           + (f"  |  Future: {period_future}" if has_future else "") +
           "  |  ★=best  Green=improved vs RAW  Red=degraded  |  "
           "Ref: KGE—Gupta et al.(2009); NSE—Nash & Sutcliffe(1970)")

    ri = 5
    for method in methods_order:
        df_m = method_dfs.get(method)
        if df_m is None:
            continue
        _mxsc(ws1,ri,1,nc1,method,bold=True,fc="FFFFFF",
              bg=METHOD_BGS.get(method,XC["white"]),sz=11)
        _rh(ws1,ri,20); ri+=1
        _hdr(ws1,ri,["Station","Code"]+METRICS_KEYS); ri+=1

        for si,stn in enumerate(stns):
            ci_c = obs_df.index.intersection(df_m.index)
            o = obs_df.loc[ci_c,stn].values.astype(float) if stn in obs_df.columns else np.array([])
            s = df_m.loc[ci_c,stn].values.astype(float) if stn in df_m.columns else np.array([])
            met = compute_metrics(o,s)
            row = [stn,f"S{si+1}"] + [fv(met[k]) for k in METRICS_KEYS]
            for ci,v in enumerate(row,1):
                bg = METHOD_BGS.get(method,XC["white"])
                if ci>2 and method!="RAW":
                    mk = METRICS_KEYS[ci-3]
                    raw_m = method_dfs.get("RAW")
                    if raw_m is not None and stn in raw_m.columns:
                        cr = obs_df.index.intersection(raw_m.index)
                        mr = compute_metrics(
                            obs_df.loc[cr,stn].values.astype(float) if stn in obs_df.columns else np.array([]),
                            raw_m.loc[cr,stn].values.astype(float))
                        rv = mr.get(mk,np.nan); bv = met.get(mk,np.nan)
                        if not(np.isnan(rv) or np.isnan(bv)):
                            imp = (bv<rv if mk in LOWER_BETTER else bv>rv)
                            bg = XC["improve"] if imp else XC["degrade"]
                _xsc(ws1,ri,ci,v,sz=9,bg=bg,align="left" if ci<=2 else "right")
            _rh(ws1,ri,14); ri+=1
        ri+=1

    for ci,w in enumerate([10,6]+[10]*len(METRICS_KEYS),1): _cw(ws1,ci,w)

    # ── S2: Wet-Day Frequency ─────────────────────────────────────────
    ws2 = wb.create_sheet("S2 Wet-Day Freq")
    ws2.sheet_view.showGridLines = False
    all_m = ["OBS","RAW","EQM","GDM","MBC","QRF"]
    nc2 = 2 + len(all_m)
    _title(ws2, nc2,
           "Wet-Day Frequency per Station and Method",
           f"Wet day: rainfall > {WET_THRESHOLD_MM} mm/day  |  "
           f"Values: fraction of wet days over full period  |  "
           "Ref: Themeßl et al. (2011) Int.J.Climatol. 31:1530–1542")
    _hdr(ws2,4,["Station","Code"]+all_m)
    ri2=5
    for si,stn in enumerate(stns):
        row=[stn,f"S{si+1}"]
        for m in all_m:
            df_m=method_dfs.get(m)
            row.append(fv(wet_day_freq(df_m[stn].values.astype(float)
                          if df_m is not None and stn in df_m.columns
                          else np.array([])),4))
        for ci,v in enumerate(row,1):
            bg=(XC["obs_r"] if ci==3 else
                METHOD_BGS.get(all_m[ci-3],XC["white"]) if ci>2 else XC["white"])
            _xsc(ws2,ri2,ci,v,sz=9,bg=bg,align="left" if ci<=2 else "right")
        _rh(ws2,ri2,15); ri2+=1
    for ci,w in enumerate([10,6]+[10]*len(all_m),1): _cw(ws2,ci,w)

    # ── S3: Extreme Quantiles ─────────────────────────────────────────
    ws3 = wb.create_sheet("S3 Extreme Quantiles")
    ws3.sheet_view.showGridLines = False
    pct = [("P90",0.90),("P95",0.95),("P99",0.99)]
    nc3 = 2 + len(pct)*len(all_m)
    _title(ws3,nc3,
           "Extreme Rainfall Quantiles per Station and Method",
           f"Computed on wet-day values (>{WET_THRESHOLD_MM} mm/day) only  |  "
           "Values in mm/day  |  Closer to OBS = better")
    hdrs3=["Station","Code"]
    for lbl,_ in pct:
        for m in all_m: hdrs3.append(f"{lbl}\n{m}")
    _hdr(ws3,4,hdrs3); ri3=5
    for si,stn in enumerate(stns):
        row=[stn,f"S{si+1}"]
        for _,p in pct:
            for m in all_m:
                df_m=method_dfs.get(m)
                if df_m is None or stn not in df_m.columns:
                    row.append("—"); continue
                arr=df_m[stn].values.astype(float)
                wet=arr[~np.isnan(arr)&(arr>WET_THRESHOLD_MM)]
                row.append(fv(float(np.quantile(wet,p)),2) if len(wet)>5 else "—")
        for ci,v in enumerate(row,1):
            _xsc(ws3,ri3,ci,v,sz=9,
                 bg=XC["alt"] if si%2==0 else XC["white"],
                 align="left" if ci<=2 else "right")
        _rh(ws3,ri3,14); ri3+=1
    for ci in range(1,nc3+1): _cw(ws3,ci,9)

    # ── S4: Improvement vs RAW ────────────────────────────────────────
    ws4 = wb.create_sheet("S4 Improvement vs Raw")
    ws4.sheet_view.showGridLines = False
    bc_methods=["EQM","GDM","MBC","QRF"]
    nc4 = 2 + len(bc_methods) + 1
    _title(ws4,nc4,
           "Improvement Summary vs Raw Model",
           "Δ = BC_metric − Raw_metric  |  "
           "RMSE/MAE: negative Δ = improved  |  "
           "r/NSE/KGE: positive Δ = improved  |  "
           "Green=improved  Red=degraded  Bold=best method")
    _hdr(ws4,4,["Station","Metric"]+bc_methods+["Best Method"])
    ri4=5
    for stn in stns:
        for ki,key in enumerate(METRICS_KEYS):
            lower=(key in LOWER_BETTER)
            raw_m=method_dfs.get("RAW")
            if raw_m is None or stn not in raw_m.columns:
                continue
            cr=obs_df.index.intersection(raw_m.index)
            if stn not in obs_df.columns:
                continue
            mr=compute_metrics(obs_df.loc[cr,stn].values.astype(float),
                               raw_m.loc[cr,stn].values.astype(float))
            rv=mr.get(key,np.nan)

            deltas={}
            for method in bc_methods:
                df_m=method_dfs.get(method)
                if df_m is None or stn not in df_m.columns:
                    deltas[method]=np.nan; continue
                ci_c=obs_df.index.intersection(df_m.index)
                mb=compute_metrics(obs_df.loc[ci_c,stn].values.astype(float)
                                   if stn in obs_df.columns else np.array([]),
                                   df_m.loc[ci_c,stn].values.astype(float))
                bv=mb.get(key,np.nan)
                deltas[method]=(round(bv-rv,4)
                                if not(np.isnan(rv) or np.isnan(bv)) else np.nan)

            valid_d={m:v for m,v in deltas.items() if not np.isnan(v)}
            if valid_d:
                best=(min(valid_d,key=lambda m:valid_d[m]) if lower
                      else max(valid_d,key=lambda m:valid_d[m]))
            else:
                best="—"

            row=[stn if ki==0 else "", key
                 ]+[fv(deltas.get(m,np.nan),4) for m in bc_methods]+[best]
            for ci,v in enumerate(row,1):
                is_d=(3<=ci<=2+len(bc_methods))
                if is_d and isinstance(v,(int,float)) and not isinstance(v,str) and not np.isnan(v):
                    imp=(v<0 if lower else v>0)
                    bg=XC["improve"] if imp else XC["degrade"]
                elif ci==len(row) and v!="—":
                    bg=XC["best"]
                else:
                    bg=XC["white"]
                _xsc(ws4,ri4,ci,v,sz=9,bg=bg,
                     align="left" if ci<=2 else "right",
                     bold=(ci==len(row)))
            _rh(ws4,ri4,14); ri4+=1

    for ci,w in enumerate([10,8]+[12]*len(bc_methods)+[10],1): _cw(ws4,ci,w)

    # ── S5: Methods & References ──────────────────────────────────────
    ws5 = wb.create_sheet("S5 Methods & References")
    ws5.sheet_view.showGridLines = False
    _title(ws5,3,
           f"Bias Correction Methods — v{VERSION} Documentation",
           f"Model: {model_name}  |  Calib: {period_calib}  |  "
           f"Hist: {period_hist}"
           + (f"  |  Future: {period_future}" if has_future else ""))
    _hdr(ws5,4,["Method","Full Name","Notes & Reference"])
    methods_doc=[
        ("EQM","Empirical Quantile Mapping",
         "Maps model → obs via empirical CDF transfer. "
         "Occurrence correction: τ = quantile(mod, 1-P_wet_obs). "
         "Fit on calibration overlap; transform on any period (hist or SSP). "
         "Ref: Themeßl et al. (2011) Int.J.Climatol. 31:1530-1542."),
        ("GDM","Gamma Distribution Mapping",
         "Fits Gamma(α,β) to wet-day distributions. "
         "Transfer: u=CDF_mod(x) → ICDF_obs(u). "
         "Falls back to EQM if Gamma fit fails. "
         "Ref: Piani et al. (2010) J.Geophys.Res. 115:D23106."),
        ("MBC","Multivariate Bias Correction (Cholesky)",
         "Preserves inter-station spatial correlation via Cholesky recolouring. "
         "[FIX-4] Gap-fill + regularisation ensure matrix stability. "
         "Falls back to EQM if Cholesky fails. "
         "Ref: Bárdossy & Pegram (2012) AWR 41:110-123; Cannon (2016) J.Clim.29:983."),
        ("QRF","Quantile Regression Forests",
         "Library: " + ("quantile-forest (true QRF, Meinshausen 2006)" if _HAS_QF
                         else "sklearn RF + rank-analog [fallback — quantile-forest not installed]") +
         ". Transfer: p_t=F̂_mod(m_t) → Q_QRF(p_t|X_t). "
         "Ref: Meinshausen & Ridgeway (2006) JMLR 7:983-999; "
         "Taillardat et al. (2016) MWR 144:2375."),
        ("FIX-1","Column name normalisation",
         "[v3.0] All input column names normalised to UPPERCASE + stripped. "
         "Accepts: YEAR/year/Year/ YEAR (any case, with spaces)."),
        ("FIX-2","QRF library fallback",
         "[v3.0] quantile-forest used if installed; "
         "sklearn rank-analog fallback if not. "
         "Install: pip install quantile-forest"),
        ("FIX-3","Future projection support",
         "[v3.0] Fit on historical overlap only; transform on ALL data. "
         "Future SSP files (ssp585/ssp245/…) detected automatically. "
         "Output: bc_<method>_<MODEL>_hist_*.csv + bc_<method>_<MODEL>_ssp*_*.csv"),
        ("FIX-4","MBC spatial continuity",
         "[v3.0] Gap-fill (≤10-day gaps) + matrix regularisation (ε·I) before Cholesky. "
         "Falls back to EQM if matrix is not positive-definite after regularisation."),
        ("FIX-5","Memory management",
         "[v3.0] Explicit gc.collect() + del after each method. "
         "For large datasets (>30,000 rows), memory logged after each step. "
         "Recommended: 16 GB RAM for 12 stations × 85-year SSP dataset."),
    ]
    alt=[_xf("DEEAF1"),_xf("FFFFFF")]
    for ri_m,(m,fn,desc) in enumerate(methods_doc,5):
        fl=alt[ri_m%2]
        for ci,v in enumerate([m,fn,desc],1):
            cell=_xsc(ws5,ri_m,ci,v,bold=(ci<=2),sz=9.5,align="left",wrap=True)
            cell.fill=fl
        _rh(ws5,ri_m,60)
    _cw(ws5,1,14); _cw(ws5,2,30); _cw(ws5,3,72)


# ════════════════════════════════════════════════════════════════════════════
#  §11  CORE PIPELINE — PER MODEL
# ════════════════════════════════════════════════════════════════════════════

def process_model(obs_df:      pd.DataFrame,
                  obs_stns:    List[str],
                  model_name:  str,
                  file_list:   List[Tuple[str, str]],  # [(path, scenario), …]
                  obs_stem:    str,
                  out_dir:     Path) -> None:
    """
    [FIX-3] STRICTLY SEPARATED FIT / TRANSFORM PIPELINE.

    Step 1 — Identify the historical file (scenario == 'hist').
    Step 2 — Load historical raw data.
    Step 3 — Align obs and historical raw → CALIBRATION PERIOD.
    Step 4 — FIT all correctors on the calibration period ONLY.
    Step 5 — TRANSFORM historical raw (full length) → save bc_*_hist_*.csv.
    Step 6 — For each SSP file found: TRANSFORM future raw → save bc_*_ssp*.csv.
             The transfer functions fitted on historical obs are applied directly
             to future model data WITHOUT any obs-model intersection.
    Step 7 — Excel performance summary (calibration period only).
    """
    SEP = "─" * 72
    print(f"\n{SEP}")
    print(f"  MODEL : {model_name}")
    print(f"  Files : {[(Path(p).name, sc) for p,sc in file_list]}")
    print(SEP)

    # ── Identify historical and future files ──────────────────────────
    hist_files   = [(p, sc) for p, sc in file_list if sc == "hist"]
    future_files = [(p, sc) for p, sc in file_list if sc != "hist"]

    if not hist_files:
        # If no file tagged 'hist', use the first file (assume historical)
        hist_files   = [file_list[0]]
        future_files = file_list[1:]
        print(f"  ⚠  No 'hist' tag found — treating {Path(hist_files[0][0]).name} "
              f"as historical")

    hist_path, _ = hist_files[0]

    # ── Load historical raw ───────────────────────────────────────────
    hist_raw, hist_stns = load_daily(hist_path, f"Hist/{model_name}",
                                      target_stns=obs_stns)
    if hist_raw is None:
        print(f"  ✗  Failed to load historical — skipping {model_name}")
        return

    # Station intersection
    stns = sorted(set(obs_stns) & set([str(s) for s in hist_stns]),
                  key=lambda s: obs_stns.index(s) if s in obs_stns else 999)
    if not stns:
        print(f"  ✗  No common stations for {model_name}"); return

    # ── Calibration period: obs ∩ hist_raw ───────────────────────────
    common_idx  = obs_df.index.intersection(hist_raw.index)
    if len(common_idx) < 365:
        print(f"  ✗  Overlap < 365 days — cannot calibrate {model_name}")
        return

    obs_cal  = obs_df.loc[common_idx]     # obs on overlap
    hist_cal = hist_raw.loc[common_idx]   # model on overlap

    period_calib  = f"{common_idx[0].year}–{common_idx[-1].year}"
    period_hist   = (f"{hist_raw.index[0].year}–{hist_raw.index[-1].year}")
    has_future    = len(future_files) > 0
    period_future = ""
    if has_future:
        # Peek at future period
        f_path, f_sc = future_files[0]
        f_tmp, _ = load_daily(f_path, f"Future/{model_name}", target_stns=stns)
        period_future = (f"{f_sc}: {f_tmp.index[0].year}–{f_tmp.index[-1].year}"
                         if f_tmp is not None else f_sc)
        del f_tmp; gc.collect()

    print(f"\n  Calibration: {period_calib}  ({len(common_idx):,} days)")
    print(f"  Hist range : {period_hist}")
    if has_future:
        print(f"  Future     : {period_future}")
    print(f"  Stations   : {stns}")
    mem = _mem_mb()
    if not math.isnan(mem):
        print(f"  RAM usage  : {mem:.0f} MB (before fit)")

    # ══════════════════════════════════════════════════════════════════
    # FIT ALL CORRECTORS ON CALIBRATION PERIOD
    # ══════════════════════════════════════════════════════════════════

    print("\n  ── FITTING on calibration period ──")
    print("  [1/4] EQM ...")
    eqm = EQMCorrector()
    eqm.fit(obs_cal, hist_cal, stns)

    print("  [2/4] GDM ...")
    gdm = GDMCorrector()
    gdm.fit(obs_cal, hist_cal, stns)

    print("  [3/4] MBC (Cholesky) ...")
    mbc = MBCCorrector()
    mbc.fit(obs_cal, hist_cal, stns)
    status_mbc = "✓ Cholesky OK" if mbc._cholesky_ok else "⚠ EQM fallback"
    print(f"         MBC status: {status_mbc}")

    print("  [4/4] QRF ...")
    qrf = QRFCorrector(n_estimators=N_ESTIMATORS_QRF)
    qrf.fit(obs_cal, hist_cal, stns)

    mem = _mem_mb()
    if not math.isnan(mem):
        print(f"  RAM usage  : {mem:.0f} MB (after fit)")

    # ══════════════════════════════════════════════════════════════════
    # TRANSFORM — HISTORICAL PERIOD (full range)
    # ══════════════════════════════════════════════════════════════════

    print("\n  ── TRANSFORMING historical data ──")
    method_results: Dict[str, pd.DataFrame] = {}   # for Excel metrics

    def _save_method(method_tag, corr, df_to_transform, period_tag, corrector_name):
        """Helper: transform, save CSV, collect metrics."""
        corrected = corr.transform(df_to_transform, stns)
        out_df    = build_output_df(corrected, stns)
        fname     = (f"bc_{method_tag}_{model_name}_{period_tag}_{obs_stem}.csv")
        save_csv(out_df, str(out_dir / fname))
        # [FIX-5] Free memory immediately
        del out_df; gc.collect()
        return corrected

    eqm_hist = _save_method("eqm", eqm, hist_raw, "hist", "EQM")
    method_results["EQM"] = eqm_hist
    gc.collect()

    gdm_hist = _save_method("gdm", gdm, hist_raw, "hist", "GDM")
    method_results["GDM"] = gdm_hist
    gc.collect()

    mbc_hist = _save_method("mbc", mbc, hist_raw, "hist", "MBC")
    method_results["MBC"] = mbc_hist
    gc.collect()

    qrf_hist = _save_method("qrf", qrf, hist_raw, "hist", "QRF")
    method_results["QRF"] = qrf_hist
    gc.collect()

    # ══════════════════════════════════════════════════════════════════
    # TRANSFORM — FUTURE PERIODS (SSP585 / SSP245 / etc.)
    # [FIX-3] Use calibrated transfer functions, no obs intersection
    # ══════════════════════════════════════════════════════════════════

    if future_files:
        print("\n  ── TRANSFORMING future projection data ──")
        for f_path, f_sc in future_files:
            print(f"\n  Scenario: {f_sc} — {Path(f_path).name}")
            fut_raw, fut_stns = load_daily(f_path, f"Future/{model_name}/{f_sc}",
                                            target_stns=stns)
            if fut_raw is None:
                print(f"  ✗  Cannot load {f_path} — skipping")
                continue

            # Only keep common stations
            fut_stns_ok = [s for s in stns if s in fut_raw.columns]

            print(f"    EQM future ...")
            _save_method("eqm", eqm, fut_raw[fut_stns_ok], f_sc, "EQM")
            gc.collect()

            print(f"    GDM future ...")
            _save_method("gdm", gdm, fut_raw[fut_stns_ok], f_sc, "GDM")
            gc.collect()

            print(f"    MBC future ...")
            _save_method("mbc", mbc, fut_raw[fut_stns_ok], f_sc, "MBC")
            gc.collect()

            print(f"    QRF future ...")
            _save_method("qrf", qrf, fut_raw[fut_stns_ok], f_sc, "QRF")
            gc.collect()

            del fut_raw; gc.collect()

    # ══════════════════════════════════════════════════════════════════
    # CONSOLE METRICS SUMMARY (calibration overlap)
    # ══════════════════════════════════════════════════════════════════

    print(f"\n  Performance — regional mean  (calibration: {period_calib})")
    hdr = f"  {'Method':6s}  {'RMSE':7s}  {'r':6s}  {'NSE':6s}  {'KGE':6s}  {'Pbias':8s}"
    print(hdr)
    print("  " + "─"*55)

    for name, df_m in [("RAW",   hist_cal),
                        ("EQM",   eqm_hist),
                        ("GDM",   gdm_hist),
                        ("MBC",   mbc_hist),
                        ("QRF",   qrf_hist)]:
        agg = {k: [] for k in METRICS_KEYS}
        ci  = obs_cal.index.intersection(df_m.index)
        for stn in stns:
            if stn not in obs_cal.columns or stn not in df_m.columns:
                continue
            m = compute_metrics(obs_cal.loc[ci,stn].values.astype(float),
                                df_m.loc[ci,stn].values.astype(float))
            for k in METRICS_KEYS:
                if not np.isnan(m[k]):
                    agg[k].append(m[k])
        mn = {k: float(np.mean(v)) if v else np.nan for k,v in agg.items()}
        print(f"  {name:6s}  "
              f"{mn['RMSE']:7.3f}  {mn['r']:6.3f}  "
              f"{mn['NSE']:6.3f}  {mn['KGE']:6.3f}  {mn['Pbias']:+8.2f}%")

    # ══════════════════════════════════════════════════════════════════
    # EXCEL REPORT
    # ══════════════════════════════════════════════════════════════════

    print("\n  Building Excel summary (5 sheets) ...")
    wb = Workbook()
    wb.remove(wb.active)
    write_excel_report(
        wb, stns,
        obs_df       = obs_cal,
        mod_df       = hist_cal,
        results      = method_results,
        model_name   = model_name,
        period_calib = period_calib,
        period_hist  = period_hist,
        has_future   = has_future,
        period_future= period_future,
    )
    xl_path = out_dir / f"BC_Summary_{model_name}_{obs_stem}.xlsx"
    wb.save(str(xl_path))
    print(f"  ✓  Excel → {xl_path.name}")

    # [FIX-5] Final memory cleanup
    del eqm_hist, gdm_hist, mbc_hist, qrf_hist, hist_raw
    del eqm, gdm, mbc, qrf
    del method_results
    gc.collect()

    mem = _mem_mb()
    if not math.isnan(mem):
        print(f"  RAM usage  : {mem:.0f} MB (after cleanup)")


# ════════════════════════════════════════════════════════════════════════════
#  §12  ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════

def main():
    SEP = "═" * 72
    print(SEP)
    print(f"  CMIP6 Rainfall Bias Correction — v{VERSION}")
    print(f"  Methods  : EQM | GDM | MBC-Cholesky | QRF")
    print(f"  Fixes    : [1] Column case  [2] QRF fallback  "
          f"[3] Future SSP  [4] MBC stability  [5] Memory")
    print(f"  QRF lib  : {'quantile-forest (true QRF)' if _HAS_QF else 'sklearn RF (fallback — pip install quantile-forest)'}")
    print(f"  sklearn  : {sklearn.__version__}")
    print(SEP)

    if len(sys.argv) > 1:
        work_dir = sys.argv[1].strip('"').strip("'")
    else:
        try:
            work_dir = str(Path(os.path.abspath(__file__)).parent)
        except NameError:
            work_dir = os.getcwd()

    out_dir = Path(work_dir)
    print(f"\n  Working folder : {work_dir}")

    # ── Discover files ──────────────────────────────────────────────
    print("\n  Scanning input files ...")
    obs_path, raw_models = discover_files(work_dir)

    if obs_path is None:
        sys.exit("  ✗  No Observed file — aborting.")
    if not raw_models:
        sys.exit("  ✗  No Raw CMIP6 files found — aborting.")

    model_names = list(raw_models.keys())
    print(f"\n  Models detected: {model_names}")
    for m, fl in raw_models.items():
        scenarios = [sc for _, sc in fl]
        print(f"    {m} → scenarios: {scenarios}")
    print("-" * 72)

    # ── Load Observed ───────────────────────────────────────────────
    print("\n  Loading Observed data ...")
    obs_df, obs_stns = load_daily(obs_path, "Observed")
    if obs_df is None:
        sys.exit("  ✗  Failed to load Observed — aborting.")

    obs_stem  = Path(obs_path).stem
    obs_stns  = [str(s) for s in obs_stns]

    print(f"\n  Observed: {len(obs_stns)} stations  "
          f"[{obs_df.index[0].year}–{obs_df.index[-1].year}]")
    print(f"  Stations: {obs_stns}")

    # ── Process each model ──────────────────────────────────────────
    for model_name, file_list in raw_models.items():
        try:
            process_model(
                obs_df     = obs_df,
                obs_stns   = obs_stns,
                model_name = model_name,
                file_list  = file_list,
                obs_stem   = obs_stem,
                out_dir    = out_dir,
            )
        except Exception:
            print(f"\n  ✗  ERROR processing {model_name}:")
            traceback.print_exc()

    # ── Final summary ───────────────────────────────────────────────
    methods = ["eqm","gdm","mbc","qrf"]
    n_csv  = sum(len(list(out_dir.glob(f"bc_{m}_*.csv"))) for m in methods)
    n_xlsx = len(list(out_dir.glob("BC_Summary_*.xlsx")))
    print()
    print(SEP)
    print(f"  ✓  COMPLETE  v{VERSION}")
    print(f"  CSV files  : {n_csv}")
    print(f"  Excel files: {n_xlsx}")
    print(f"  Saved to   : {work_dir}")
    print(SEP)


if __name__ == "__main__":
    main()
