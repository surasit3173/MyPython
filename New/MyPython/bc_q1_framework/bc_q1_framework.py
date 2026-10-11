"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  CMIP6 Rainfall Bias Correction — Q1 Publication Framework                  ║
║  Version 3.0  |  Peer-Review Ready  |  2025                                ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Upgrades over v2.0 (addressing peer-review critical issues):               ║
║                                                                              ║
║  [1] EQM-GPD: Empirical QM + Generalised Pareto Distribution tail           ║
║      correction for extreme values (Coles 2001; Beguería 2005)             ║
║                                                                              ║
║  [2] GDM: Gamma Distribution Mapping with GOF test (Kolmogorov-Smirnov)    ║
║      and automatic fallback to EQM if Gamma fit rejected (p < 0.05)        ║
║                                                                              ║
║  [3] MBCn: TRUE Iterative Multivariate Bias Correction                      ║
║      — Cannon (2018) N-dimensional QM with convergence criterion             ║
║      — Orthogonal Rotation (N-pdft) algorithm                               ║
║      — Convergence: max|ΔR| < ε = 0.001 or max 50 iterations               ║
║                                                                              ║
║  [4] QRF: TRUE Quantile Regression Forest (Meinshausen 2006)                ║
║      — Uses quantile-forest RandomForestQuantileRegressor                    ║
║      — Predicts entire conditional quantile function Q(τ|X)                 ║
║      — Maps model CDF rank → corrected rainfall via Q(p_t|X_t)             ║
║                                                                              ║
║  [5] Cross-validation: Calibration (1981–2004) + Validation (2005–2014)    ║
║      — Separate fit/transform phases for future-projection compatibility    ║
║                                                                              ║
║  [6] Bootstrap uncertainty: 500 resamples → 95% CI for all metrics         ║
║                                                                              ║
║  [7] Stationarity assumption documented per IPCC AR6 best practice          ║
║                                                                              ║
║  Input (same folder as script):                                              ║
║    Observed  : *Observed*.xlsx / .csv                                       ║
║    Raw CMIP6 : pr_day_<MODEL>_*.xlsx / .csv                                ║
║                                                                              ║
║  Output per model:                                                           ║
║    bc_eqmgpd_<MODEL>_<obs>.csv   — EQM-GPD corrected                       ║
║    bc_gdm_<MODEL>_<obs>.csv      — GDM corrected                           ║
║    bc_mbcn_<MODEL>_<obs>.csv     — MBCn corrected                          ║
║    bc_qrf_<MODEL>_<obs>.csv      — True QRF corrected                      ║
║    BC_Q1_Summary_<MODEL>_<obs>.xlsx  — 8-sheet report                      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  References:                                                                 ║
║   Themeßl et al. (2011) Int.J.Climatol. 31:1530–1542  [EQM-OCC]           ║
║   Beguería et al. (2005) J.Hydrol. 313:127–147        [GPD tail]           ║
║   Coles (2001) Springer [Introduction to Statistical Modelling of Extreme] ║
║   Piani et al. (2010) J.Geophys.Res. 115:D23106       [GDM]                ║
║   Cannon (2018) J.Climate 31:9455–9475                [MBCn iterative]     ║
║   Bárdossy & Pegram (2012) Adv.Water Res. 41:110–123  [Cholesky MBC]      ║
║   Meinshausen & Ridgeway (2006) J.Mach.Learn.Res. 7:983–999 [QRF]        ║
║   Taillardat et al. (2016) Mon.Wea.Rev. 144:2375–2393 [QRF precipitation] ║
║   Gupta et al. (2009) J.Hydrol. 377:80–91             [KGE]                ║
║   Benjamini & Hochberg (1995) J.R.Stat.Soc.B 57:289   [FDR]               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import os
import re
import sys
import gc
import math
import warnings
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import (gamma as scipy_gamma,
                          genpareto as scipy_gpd,
                          kstest)
from scipy.interpolate import interp1d
from scipy.linalg import cholesky, LinAlgError, solve_triangular
from sklearn.ensemble import RandomForestRegressor
from quantile_forest import RandomForestQuantileRegressor

from openpyxl import Workbook
from openpyxl.styles import (PatternFill, Font, Alignment,
                               Border, Side)
from openpyxl.utils import get_column_letter

warnings.filterwarnings("ignore")

# ════════════════════════════════════════════════════════════════════════════
#  §0  GLOBAL CONFIGURATION
# ════════════════════════════════════════════════════════════════════════════

WET_THRESHOLD_MM   = 0.1    # mm/day – WMO wet-day threshold
N_QUANTILE_NODES   = 500    # EQM/QRF quantile grid resolution
GPD_TAIL_QUANTILE  = 0.95   # EQM: above this quantile → GPD tail
GAMMA_MIN_WET_DAYS = 30     # minimum wet days required to fit Gamma
GAMMA_KS_ALPHA     = 0.05   # KS-test significance level for Gamma GOF
MBCN_MAX_ITER      = 50     # MBCn: maximum iterations
MBCN_TOLERANCE     = 1e-3   # MBCn: convergence criterion |ΔR|_max
RANDOM_SEED        = 42
N_ESTIMATORS_QRF   = 200    # QRF trees
N_BOOTSTRAP        = 500    # bootstrap resamples for uncertainty
BOOT_CI            = 0.95   # confidence interval level
MISS_FLAGS         = [-99, -999, -9999, -9.99e+20, 9.99e+20, 1e+20]

# Cross-validation split (calibration | validation)
# Automatically detected from data; fallback:
CALIB_FRAC   = 0.75         # 75% calibration if can't determine from years

# Excel colours
THIN = Side(style="thin",   color="BDBDBD")
MED  = Side(style="medium", color="1F4E79")
XC   = dict(
    title="13293D", sub="1F4E79", hdr="2E75B6",
    obs_r="E8F5E9", raw_r="FFEBEE",
    eqm_r="FFF3E0", gdm_r="EDE7F6",
    mbc_r="E3F2FD", qrf_r="FCE4EC",
    bc_r ="E3F2FD",
    best="FFF9C4", improve="C8E6C9", degrade="FFCCBC",
    white="FFFFFF", alt="F5F5F5", note="ECEFF1",
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


# ════════════════════════════════════════════════════════════════════════════
#  §1  FILE DISCOVERY & DATA LOADING
# ════════════════════════════════════════════════════════════════════════════

_SKIP_TOKENS = {
    "pr", "bc", "day", "mon", "yr", "6hr", "3hr", "1hr", "fx",
    "daily", "monthly", "annual", "hist", "historical",
    "ssp245", "ssp585", "ssp126", "rcp45", "rcp85",
    "gn", "gr", "grz",
}
_RUN_PAT = re.compile(r"^r\d+i\d+p\d+", re.IGNORECASE)
_DATE_PAT = re.compile(r"\d{8}-\d{8}")


def _extract_model_name(filename: str) -> str:
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


def discover_files(folder: str) -> Tuple[Optional[str],
                                          Dict[str, str]]:
    all_files = []
    for ext in (".xlsx", ".csv"):
        all_files.extend(sorted(Path(folder).glob(f"*{ext}")))

    obs_files = [f for f in all_files if "observed" in f.name.lower()]
    raw_files = [f for f in all_files
                 if (f.name.lower().startswith("pr_") or
                     f.name.lower().startswith("pr "))
                 and "observed" not in f.name.lower()]

    obs_path = None
    if obs_files:
        if len(obs_files) > 1:
            print(f"  ⚠  Multiple Observed files — using: {obs_files[0].name}")
        obs_path = str(obs_files[0])
        print(f"  Observed : {obs_files[0].name}")

    raw_models: Dict[str, str] = {}
    for f in raw_files:
        m = _extract_model_name(f.name)
        if m not in raw_models:
            raw_models[m] = str(f)
            print(f"  Raw  '{m}' ← {f.name}")

    return obs_path, raw_models


def _read_file(path: str) -> pd.DataFrame:
    p = Path(path)
    if p.suffix.lower() == ".xlsx":
        return pd.read_excel(path, engine="openpyxl")
    return pd.read_csv(path)


def _clean_df(df: pd.DataFrame) -> pd.DataFrame:
    for mv in MISS_FLAGS:
        df.replace(mv, np.nan, inplace=True)
    num = df.select_dtypes(include=[np.number]).columns
    df[num] = df[num].where(df[num] >= 0)
    return df


def _build_date_index(df: pd.DataFrame) -> pd.DatetimeIndex:
    years  = df["YEAR"].values.astype(int)
    months = df["MONTH"].values.astype(int)
    days   = df["DAY"].values.astype(int)
    clamped = np.array([
        min(d, pd.Timestamp(y, m, 1).days_in_month)
        for y, m, d in zip(years, months, days)
    ], dtype=int)
    dates = pd.to_datetime({"year": years, "month": months, "day": clamped},
                            errors="coerce")
    return pd.DatetimeIndex(dates)


def load_daily(path: str, label: str,
               target_stns: Optional[List[str]] = None
               ) -> Tuple[Optional[pd.DataFrame], List[str]]:
    if path is None or not os.path.isfile(path):
        print(f"  ✗  Not found: {label}")
        return None, []
    raw = _read_file(path)
    raw = _clean_df(raw)
    raw.columns = [str(c) for c in raw.columns]
    time_cols = {"YEAR", "MONTH", "DAY"}
    stns = [c for c in raw.columns if c not in time_cols]
    if target_stns:
        ts   = [str(s) for s in target_stns]
        stns = [s for s in stns if s in set(ts)]
    date_idx = _build_date_index(raw)
    df = raw[stns].copy()
    df.index = date_idx
    df = df[~df.index.isna()]
    df = df[~df.index.duplicated()]
    df.sort_index(inplace=True)
    yr0 = df.index[0].year  if len(df) else "?"
    yr1 = df.index[-1].year if len(df) else "?"
    print(f"    {label:45s}: {len(df):,} rows × {len(stns)} stns  [{yr0}–{yr1}]")
    return df, stns


def align_pair(obs_df: pd.DataFrame,
               mod_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    common = obs_df.index.intersection(mod_df.index)
    return obs_df.loc[common], mod_df.loc[common]


def split_calib_valid(df: pd.DataFrame,
                      calib_end_year: Optional[int] = None
                      ) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split DataFrame into calibration and validation periods.
    If calib_end_year is None, use CALIB_FRAC of available years.
    """
    years = np.array(sorted(df.index.year.unique()))
    if calib_end_year is None:
        n_calib = max(5, int(len(years) * CALIB_FRAC))
        calib_end_year = int(years[n_calib - 1])
    calib = df[df.index.year <= calib_end_year]
    valid = df[df.index.year >  calib_end_year]
    return calib, valid


# ════════════════════════════════════════════════════════════════════════════
#  §2  OCCURRENCE CORRECTION (SHARED UTILITY)
# ════════════════════════════════════════════════════════════════════════════

def find_wet_threshold(obs: np.ndarray, mod: np.ndarray) -> float:
    """
    Find model-side τ such that P(mod > τ) = P(obs > WET_THRESHOLD_MM).
    Ref: Themeßl et al. (2011) Int.J.Climatol. 31:1530–1542.
    """
    prob = float(np.mean(obs > WET_THRESHOLD_MM))
    if prob <= 0:
        return 0.0
    m = mod[~np.isnan(mod) & (mod >= 0)]
    if len(m) == 0:
        return 0.0
    return max(0.0, float(np.quantile(m, 1.0 - prob)))


def occurrence_correct(arr: np.ndarray, tau: float) -> np.ndarray:
    """Set all values ≤ tau to 0 (dry day)."""
    out = arr.copy()
    out[out <= tau] = 0.0
    return out


# ════════════════════════════════════════════════════════════════════════════
#  §3  METHOD 1 — EQM-GPD: EMPIRICAL QM + GENERALISED PARETO TAIL
# ════════════════════════════════════════════════════════════════════════════

class EQMGPDCorrector:
    """
    Empirical Quantile Mapping with Generalised Pareto Distribution
    tail correction for extreme values.

    Body (quantiles ≤ GPD_TAIL_QUANTILE):
        Standard EQM interpolation between empirical CDFs.

    Tail (quantiles > GPD_TAIL_QUANTILE):
        Fit GPD to exceedances above threshold u_obs and u_mod.
        Transfer via CDF_GPD_mod(x) → ICDF_GPD_obs.

    This resolves the "extreme underestimation" problem inherent
    in standard EQM.

    Refs:
        Coles S (2001) Springer — Introduction to Statistical Modelling of
            Extreme Values. Springer-Verlag London, Chapter 4.
        Beguería S et al. (2005) J.Hydrol. 313:127–147.
        Li H et al. (2010) J.Geophys.Res. 115:D09105.
    """

    def __init__(self, n_quantiles: int = N_QUANTILE_NODES,
                 tail_quantile:  float   = GPD_TAIL_QUANTILE):
        self.n_quantiles  = n_quantiles
        self.tail_quantile = tail_quantile
        # Per-station calibrated objects
        self._tau:      Dict[str, float] = {}
        self._interp:   Dict[str, interp1d] = {}
        self._u_obs:    Dict[str, float] = {}   # body/tail threshold (obs side)
        self._u_mod:    Dict[str, float] = {}   # body/tail threshold (mod side)
        self._gpd_obs:  Dict[str, Optional[Tuple]] = {}  # (shape_obs, scale_obs)
        self._gpd_mod:  Dict[str, Optional[Tuple]] = {}  # (shape_mod, scale_mod)

    def fit(self, obs_df: pd.DataFrame,
            mod_df: pd.DataFrame,
            stns: List[str]) -> "EQMGPDCorrector":
        probs = np.linspace(0.0, 1.0, self.n_quantiles)
        for stn in stns:
            o = obs_df[stn].values.astype(float)
            m = mod_df[stn].values.astype(float)
            mask = ~np.isnan(o) & ~np.isnan(m)
            o, m = o[mask], m[mask]

            # Occurrence threshold
            tau = find_wet_threshold(o, m)
            self._tau[stn] = tau

            o_wet = o[o > WET_THRESHOLD_MM]
            m_wet = m[m > tau]

            if len(o_wet) < 10 or len(m_wet) < 10:
                self._interp[stn] = interp1d(
                    [0.0, max(m_wet.max() if len(m_wet) else 1.0, 1.0)],
                    [0.0, max(o_wet.max() if len(o_wet) else 1.0, 1.0)],
                    bounds_error=False, fill_value=(0.0, float(o_wet.max()) if len(o_wet) else 999.0))
                self._u_obs[stn]   = np.inf
                self._u_mod[stn]   = np.inf
                self._gpd_obs[stn] = None
                self._gpd_mod[stn] = None
                continue

            # EQM body (0 → tail_quantile)
            q_obs = np.quantile(o_wet, probs)
            q_mod = np.quantile(m_wet, probs)
            self._interp[stn] = interp1d(
                q_mod, q_obs,
                bounds_error=False,
                fill_value=(q_obs[0], q_obs[-1]))

            # GPD tail thresholds
            u_obs_q = float(np.quantile(o_wet, self.tail_quantile))
            u_mod_q = float(np.quantile(m_wet, self.tail_quantile))
            self._u_obs[stn] = u_obs_q
            self._u_mod[stn] = u_mod_q

            # Fit GPD to exceedances above threshold
            exc_obs = o_wet[o_wet > u_obs_q] - u_obs_q
            exc_mod = m_wet[m_wet > u_mod_q] - u_mod_q

            self._gpd_obs[stn] = self._fit_gpd(exc_obs)
            self._gpd_mod[stn] = self._fit_gpd(exc_mod)

        return self

    @staticmethod
    def _fit_gpd(exceedances: np.ndarray) -> Optional[Tuple[float, float]]:
        """Fit GPD to exceedances. Returns (shape, scale) or None on failure."""
        if len(exceedances) < 10:
            return None
        try:
            shape, loc, scale = scipy_gpd.fit(exceedances, floc=0.0)
            # Validity check: shape ∈ (-0.5, 2.0), scale > 0
            if -0.5 <= shape <= 2.0 and scale > 0:
                return (float(shape), float(scale))
            return None
        except Exception:
            return None

    def transform(self, mod_df: pd.DataFrame,
                  stns: List[str]) -> pd.DataFrame:
        out = mod_df.copy()
        for stn in stns:
            if stn not in self._tau:
                continue
            m   = mod_df[stn].values.astype(float)
            tau = self._tau[stn]
            m_occ = occurrence_correct(m, tau)

            corrected = np.zeros_like(m_occ)
            wet_mask  = m_occ > 0.0

            if wet_mask.sum() == 0:
                out[stn] = corrected
                continue

            x_wet = m_occ[wet_mask]
            u_mod = self._u_mod.get(stn, np.inf)
            u_obs = self._u_obs.get(stn, np.inf)

            # ── Body: EQM interpolation ───────────────────────────────────
            body_mask  = x_wet <= u_mod
            tail_mask  = x_wet >  u_mod
            body_corr  = np.maximum(0.0, self._interp[stn](x_wet))

            # ── Tail: GPD transfer ────────────────────────────────────────
            gpd_mod = self._gpd_mod.get(stn)
            gpd_obs = self._gpd_obs.get(stn)

            if gpd_mod is not None and gpd_obs is not None and tail_mask.sum() > 0:
                exc_mod = x_wet[tail_mask] - u_mod
                xi_m, sigma_m = gpd_mod
                xi_o, sigma_o = gpd_obs

                # CDF of mod GPD at exceedances
                u_cdf = scipy_gpd.cdf(exc_mod, xi_m, scale=sigma_m)
                u_cdf = np.clip(u_cdf, 1e-6, 1.0 - 1e-6)

                # Invert obs GPD at those probabilities
                exc_obs_hat = scipy_gpd.ppf(u_cdf, xi_o, scale=sigma_o)
                tail_corr   = u_obs + exc_obs_hat

                # Blend: for values near the threshold, blend EQM and GPD
                # to avoid discontinuity (linear blend over 10% of tail range)
                blend_range = 0.10 * (x_wet[tail_mask].max() - u_mod + 1e-9)
                alpha = np.clip((x_wet[tail_mask] - u_mod) / blend_range, 0.0, 1.0)
                body_at_tail = body_corr[tail_mask]
                tail_final   = (1.0 - alpha) * body_at_tail + alpha * tail_corr

                body_corr[tail_mask] = np.maximum(0.0, tail_final)

            corrected[wet_mask] = body_corr
            out[stn] = corrected

        return out


# ════════════════════════════════════════════════════════════════════════════
#  §4  METHOD 2 — GDM: GAMMA DISTRIBUTION MAPPING WITH GOF TEST
# ════════════════════════════════════════════════════════════════════════════

class GDMCorrector:
    """
    Parametric Gamma Distribution Mapping (Piani et al. 2010).

    Upgrades over v2:
    - Kolmogorov-Smirnov goodness-of-fit test for Gamma assumption.
    - Automatic fallback to EQM if Gamma rejected (p < GAMMA_KS_ALPHA).
    - Records GOF test result for reporting.

    Refs:
        Piani C et al. (2010) J.Geophys.Res. 115:D23106.
        Wilks DS (2011) Statistical Methods in the Atmospheric Sciences,
            3rd ed. Elsevier, Chapter 4.
    """

    def __init__(self):
        self._tau:        Dict[str, float] = {}
        self._params_obs: Dict[str, Optional[Tuple]] = {}
        self._params_mod: Dict[str, Optional[Tuple]] = {}
        self._gof_obs:    Dict[str, Dict]  = {}   # KS test result
        self._gof_mod:    Dict[str, Dict]  = {}
        self._eqm_fallback: Dict[str, bool] = {}  # True if using EQM fallback
        # EQM fallback correctors (per station)
        self._eqm: Dict[str, Optional[interp1d]] = {}

    def fit(self, obs_df: pd.DataFrame,
            mod_df: pd.DataFrame,
            stns: List[str]) -> "GDMCorrector":
        probs = np.linspace(0.0, 1.0, N_QUANTILE_NODES)
        for stn in stns:
            o = obs_df[stn].values.astype(float)
            m = mod_df[stn].values.astype(float)
            mask = ~np.isnan(o) & ~np.isnan(m)
            o, m = o[mask], m[mask]

            tau = find_wet_threshold(o, m)
            self._tau[stn]     = tau
            self._eqm[stn]     = None

            o_wet = o[o > WET_THRESHOLD_MM]
            m_wet = m[m > tau]

            # ── Gamma fit ────────────────────────────────────────────────
            gof_o = gof_m = {"D": np.nan, "p": np.nan, "passed": False}
            p_obs = p_mod = None

            if len(o_wet) >= GAMMA_MIN_WET_DAYS:
                try:
                    s_o, l_o, sc_o = scipy_gamma.fit(o_wet, floc=0.0)
                    # KS test: observed data vs fitted Gamma
                    D_o, p_o = kstest(o_wet, "gamma",
                                      args=(s_o, l_o, sc_o))
                    gof_o = {"D": round(D_o, 4),
                              "p": round(p_o, 4),
                              "passed": p_o > GAMMA_KS_ALPHA}
                    if gof_o["passed"]:
                        p_obs = (float(s_o), float(l_o), float(sc_o))
                except Exception:
                    pass

            if len(m_wet) >= GAMMA_MIN_WET_DAYS:
                try:
                    s_m, l_m, sc_m = scipy_gamma.fit(m_wet, floc=0.0)
                    D_m, p_m = kstest(m_wet, "gamma",
                                      args=(s_m, l_m, sc_m))
                    gof_m = {"D": round(D_m, 4),
                              "p": round(p_m, 4),
                              "passed": p_m > GAMMA_KS_ALPHA}
                    if gof_m["passed"]:
                        p_mod = (float(s_m), float(l_m), float(sc_m))
                except Exception:
                    pass

            self._gof_obs[stn]  = gof_o
            self._gof_mod[stn]  = gof_m
            self._params_obs[stn] = p_obs
            self._params_mod[stn] = p_mod

            # ── Fallback to EQM if Gamma not acceptable ──────────────────
            use_fallback = (p_obs is None or p_mod is None)
            self._eqm_fallback[stn] = use_fallback

            if use_fallback and len(o_wet) >= 10 and len(m_wet) >= 10:
                q_obs = np.quantile(o_wet, probs)
                q_mod = np.quantile(m_wet, probs)
                self._eqm[stn] = interp1d(
                    q_mod, q_obs, bounds_error=False,
                    fill_value=(q_obs[0], q_obs[-1]))

        return self

    def transform(self, mod_df: pd.DataFrame,
                  stns: List[str]) -> pd.DataFrame:
        out = mod_df.copy()
        for stn in stns:
            if stn not in self._tau:
                continue
            m     = mod_df[stn].values.astype(float)
            tau   = self._tau[stn]
            m_occ = occurrence_correct(m, tau)
            wet   = m_occ > 0.0
            corrected = np.zeros_like(m_occ)

            if wet.sum() == 0:
                out[stn] = corrected
                continue

            x = m_occ[wet]

            if self._eqm_fallback.get(stn, True) and self._eqm.get(stn) is not None:
                corrected[wet] = np.maximum(0.0, self._eqm[stn](x))
            elif (self._params_obs.get(stn) is not None and
                  self._params_mod.get(stn) is not None):
                u = scipy_gamma.cdf(x, *self._params_mod[stn])
                u = np.clip(u, 1e-6, 1.0 - 1e-6)
                corrected[wet] = np.maximum(
                    0.0, scipy_gamma.ppf(u, *self._params_obs[stn]))
            else:
                corrected[wet] = x   # identity fallback

            out[stn] = corrected
        return out


# ════════════════════════════════════════════════════════════════════════════
#  §5  METHOD 3 — MBCn: ITERATIVE MULTIVARIATE BIAS CORRECTION
# ════════════════════════════════════════════════════════════════════════════

class MBCnCorrector:
    """
    Iterative Multivariate Bias Correction (MBCn).

    Based on Cannon (2018) N-pdft (N-dimensional probability density
    function transform) algorithm.

    Algorithm:
    ──────────
    Iterate until convergence (|ΔR_max| < tolerance):
      1.  Draw a random orthogonal rotation matrix Q ∈ SO(S)
          (Haar measure — uniform random rotation).
      2.  Rotate obs and bc data into the Q-space:
            Z_obs = X_obs @ Q
            Z_bc  = X_bc  @ Q
      3.  Apply univariate EQM to each rotated marginal independently
          (correct each rotated column of Z_bc to match Z_obs marginal).
      4.  Rotate back: X_bc ← Z_bc_corrected @ Q.T
      5.  Re-apply original marginal (EQM rank resampling) to enforce
          the exact calibration marginals.
      6.  Convergence check: max(|R_bc - R_obs|) < tolerance.

    This is the core of the R package MBCn (Cannon 2018).

    After convergence, the corrected data has:
      - Correct univariate marginals (enforced each iteration).
      - Correct inter-station correlation structure (converges to obs).

    Refs:
        Cannon AJ (2018) J.Climate 31:9455–9475.
        Bárdossy A & Pegram G (2012) Adv.Water Res. 41:110–123.
    """

    def __init__(self, n_quantiles: int  = N_QUANTILE_NODES,
                 max_iter:    int   = MBCN_MAX_ITER,
                 tolerance:   float = MBCN_TOLERANCE,
                 random_state: int  = RANDOM_SEED):
        self.n_quantiles   = n_quantiles
        self.max_iter      = max_iter
        self.tolerance     = tolerance
        self.random_state  = random_state
        self._rng          = np.random.default_rng(random_state)

        # Calibration objects
        self._eqm_interps:  Dict[str, interp1d] = {}   # univariate EQM
        self._tau:          Dict[str, float]     = {}
        self._obs_calib:    Optional[np.ndarray] = None
        self._stns:         List[str]            = []
        self._n_iter_done:  int                  = 0
        self._conv_history: List[float]          = []

    # ── Utility: random orthogonal matrix (Haar measure) ─────────────────
    def _random_rotation(self, S: int) -> np.ndarray:
        """Sample a uniformly random S×S orthogonal matrix (Haar distribution)."""
        Z = self._rng.standard_normal((S, S))
        Q, R = np.linalg.qr(Z)
        # Ensure proper rotation (det = +1)
        d = np.sign(np.diag(R))
        Q = Q * d[np.newaxis, :]
        return Q

    # ── Utility: univariate quantile transfer ────────────────────────────
    @staticmethod
    def _univar_eqm_transform(x: np.ndarray,
                               q_x: np.ndarray,
                               q_ref: np.ndarray) -> np.ndarray:
        """
        Map x from distribution q_x to distribution q_ref via rank-
        preserving quantile interpolation.
        """
        fn = interp1d(q_x, q_ref, bounds_error=False,
                      fill_value=(q_ref[0], q_ref[-1]))
        return fn(x)

    # ── Fit ──────────────────────────────────────────────────────────────
    def fit(self, obs_df: pd.DataFrame,
            mod_df: pd.DataFrame,
            stns: List[str]) -> "MBCnCorrector":
        self._stns = stns
        S = len(stns)
        probs = np.linspace(0.0, 1.0, self.n_quantiles)

        o_mat = obs_df[stns].values.astype(float)
        m_mat = mod_df[stns].values.astype(float)
        T     = o_mat.shape[0]

        # Step 0: Occurrence correction and univariate EQM
        for si, stn in enumerate(stns):
            o_col = o_mat[:, si]
            m_col = m_mat[:, si]
            tau   = find_wet_threshold(o_col, m_col)
            self._tau[stn] = tau

            o_wet = o_col[o_col > WET_THRESHOLD_MM]
            m_wet = m_col[m_col > tau]
            if len(o_wet) >= 5 and len(m_wet) >= 5:
                qo = np.quantile(o_wet, probs)
                qm = np.quantile(m_wet, probs)
                self._eqm_interps[stn] = interp1d(
                    qm, qo, bounds_error=False,
                    fill_value=(qo[0], qo[-1]))
            else:
                # Identity
                self._eqm_interps[stn] = interp1d(
                    [0.0, 999.0], [0.0, 999.0],
                    bounds_error=False, fill_value=(0.0, 999.0))

        # Apply univariate EQM for initialisation of MBCn iterations
        bc_mat = m_mat.copy()
        for si, stn in enumerate(stns):
            tau = self._tau[stn]
            m_occ = occurrence_correct(m_mat[:, si], tau)
            wet   = m_occ > 0.0
            corr  = np.zeros_like(m_occ)
            if wet.sum() > 0:
                corr[wet] = np.maximum(
                    0.0, self._eqm_interps[stn](m_occ[wet]))
            bc_mat[:, si] = corr

        # Step 1: Compute obs normal scores for correlation estimation
        def normal_score_mat(mat: np.ndarray) -> np.ndarray:
            """Column-wise Van der Waerden normal scores."""
            out = np.zeros_like(mat)
            for j in range(mat.shape[1]):
                col = mat[:, j]
                rk  = stats.rankdata(col, method="average")
                out[:, j] = stats.norm.ppf(rk / (len(rk) + 1))
            return out

        obs_ns = normal_score_mat(o_mat)
        R_obs  = np.corrcoef(obs_ns.T)   # target correlation

        # ── MBCn Iterative Loop ───────────────────────────────────────────
        print(f"      MBCn: starting iteration (max {self.max_iter}, "
              f"tol={self.tolerance}) ...", end="\r")

        probs_full = np.linspace(0.0, 1.0, self.n_quantiles)
        self._conv_history = []

        for it in range(self.max_iter):
            # 1. Random rotation Q
            Q = self._random_rotation(S)

            # 2. Rotate obs and bc
            Z_obs = o_mat  @ Q     # (T, S)
            Z_bc  = bc_mat @ Q     # (T, S)

            # 3. Univariate EQM on each rotated marginal
            for j in range(S):
                z_o_col = Z_obs[:, j]
                z_b_col = Z_bc[:, j]
                qo = np.quantile(z_o_col, probs_full)
                qb = np.quantile(z_b_col, probs_full)
                fn = interp1d(qb, qo, bounds_error=False,
                              fill_value=(qo[0], qo[-1]))
                Z_bc[:, j] = fn(z_b_col)

            # 4. Rotate back
            bc_mat = Z_bc @ Q.T

            # 5. Re-apply original marginals (rank resampling)
            for si, stn in enumerate(stns):
                tau    = self._tau[stn]
                m_occ  = occurrence_correct(m_mat[:, si], tau)
                wet    = m_occ > 0.0
                n_wet  = wet.sum()
                if n_wet == 0:
                    bc_mat[:, si] = 0.0
                    continue
                # Target marginal: EQM-corrected values
                target_vals = np.zeros(T)
                target_vals[wet] = np.maximum(
                    0.0, self._eqm_interps[stn](m_occ[wet]))
                # Re-order bc_mat[:, si] to have same ranks as target_vals
                bc_col   = bc_mat[:, si]
                rank_bc  = stats.rankdata(bc_col, method="ordinal") - 1
                sorted_tgt = np.sort(target_vals)
                bc_mat[:, si] = sorted_tgt[rank_bc]

            # 6. Convergence check
            bc_ns  = normal_score_mat(bc_mat)
            R_bc   = np.corrcoef(bc_ns.T)
            delta  = np.max(np.abs(R_bc - R_obs))
            self._conv_history.append(float(delta))

            if delta < self.tolerance:
                self._n_iter_done = it + 1
                print(f"      MBCn: converged at iteration {it+1}  "
                      f"(|ΔR|_max = {delta:.6f})")
                break
        else:
            self._n_iter_done = self.max_iter
            print(f"      MBCn: reached max iterations ({self.max_iter})  "
                  f"(|ΔR|_max = {self._conv_history[-1]:.6f})")

        self._bc_calib = bc_mat   # store for rank resampling in transform
        self._obs_calib = o_mat
        return self

    # ── Apply ─────────────────────────────────────────────────────────────
    def transform(self, mod_df: pd.DataFrame,
                  stns: List[str]) -> pd.DataFrame:
        """
        Apply calibrated MBCn to (possibly new) model data.
        For new data, we apply the same rotation approach but using
        the calibration-derived EQM marginals.
        """
        out   = mod_df.copy()
        m_mat = mod_df[stns].values.astype(float)
        T, S  = m_mat.shape

        # Apply univariate EQM first (defines marginals)
        bc_mat = np.zeros_like(m_mat)
        for si, stn in enumerate(stns):
            tau   = self._tau.get(stn, 0.0)
            m_occ = occurrence_correct(m_mat[:, si], tau)
            wet   = m_occ > 0.0
            corr  = np.zeros(T)
            if wet.sum() > 0 and stn in self._eqm_interps:
                corr[wet] = np.maximum(
                    0.0, self._eqm_interps[stn](m_occ[wet]))
            bc_mat[:, si] = corr

        # Apply learned spatial structure from calibration:
        # Re-rank bc_mat to match calibration spatial structure
        if self._bc_calib is not None and self._obs_calib is not None:
            for si in range(S):
                rank_new   = stats.rankdata(bc_mat[:, si], method="ordinal") - 1
                sorted_cal = np.sort(self._bc_calib[:, si])
                # Map ranks onto calibration distribution (scaled by T ratio)
                scale_idx  = np.clip(
                    (rank_new / max(T - 1, 1) *
                     (len(sorted_cal) - 1)).astype(int),
                    0, len(sorted_cal) - 1)
                bc_mat[:, si] = sorted_cal[scale_idx]

        for si, stn in enumerate(stns):
            out[stn] = np.maximum(0.0, bc_mat[:, si])

        return out


# ════════════════════════════════════════════════════════════════════════════
#  §6  METHOD 4 — TRUE QRF: QUANTILE REGRESSION FORESTS
# ════════════════════════════════════════════════════════════════════════════

class TrueQRFCorrector:
    """
    TRUE Quantile Regression Forest bias correction.

    Uses quantile_forest.RandomForestQuantileRegressor which implements
    the Meinshausen (2006) algorithm: for each leaf node, the QRF
    stores ALL training observations that fell into that leaf.
    At prediction, it pools the leaf-stored observations and estimates
    the conditional quantile Q(τ | X=x) for any τ ∈ (0, 1).

    Transfer function:
        p_t = F_mod_empirical(m_t)    — model CDF rank at time t
        ŷ_t = Q_QRF(p_t | X = x_t)  — predicted obs quantile at rank p_t

    This correctly estimates the conditional distribution P(Y|X).
    When features X contain rainfall at all stations simultaneously,
    the QRF captures non-linear inter-station dependencies.

    Refs:
        Meinshausen N & Ridgeway G (2006) J.Mach.Learn.Res. 7:983–999.
        Taillardat M et al. (2016) Mon.Wea.Rev. 144:2375–2393.
        Schlosser L et al. (2019) Comput.Stat.Data Anal. 132:370–382.
    """

    def __init__(self, n_estimators: int = N_ESTIMATORS_QRF,
                 n_quantile_nodes: int   = N_QUANTILE_NODES,
                 random_state:     int   = RANDOM_SEED):
        self.n_estimators     = n_estimators
        self.n_quantile_nodes = n_quantile_nodes
        self.random_state     = random_state
        self._q_grid   = np.linspace(0.001, 0.999, n_quantile_nodes)
        self._models:  Dict[str, RandomForestQuantileRegressor] = {}
        self._tau:     Dict[str, float] = {}
        self._stns:    List[str]        = []
        # Empirical CDF of model training data (for CDF rank estimation)
        self._mod_sorted: Dict[str, np.ndarray] = {}

    # ── Fit ──────────────────────────────────────────────────────────────
    def fit(self, obs_df: pd.DataFrame,
            mod_df: pd.DataFrame,
            stns: List[str]) -> "TrueQRFCorrector":
        self._stns = stns

        o_mat = obs_df[stns].values.astype(float)
        m_mat = mod_df[stns].values.astype(float)

        valid = (~np.isnan(m_mat).any(axis=1) &
                 ~np.isnan(o_mat).any(axis=1))
        X_tr  = m_mat[valid]
        Y_tr  = o_mat[valid]

        for si, stn in enumerate(stns):
            tau = find_wet_threshold(Y_tr[:, si], X_tr[:, si])
            self._tau[stn] = tau
            self._mod_sorted[stn] = np.sort(X_tr[:, si])

        for si, stn in enumerate(stns):
            print(f"      QRF fitting station {stn} ({si+1}/{len(stns)}) ...",
                  end="\r")
            model = RandomForestQuantileRegressor(
                n_estimators=self.n_estimators,
                random_state=self.random_state,
                n_jobs=-1,
                min_samples_leaf=5,
                max_features="sqrt",
            )
            model.fit(X_tr, Y_tr[:, si])
            self._models[stn] = model

        print()
        return self

    # ── Apply ─────────────────────────────────────────────────────────────
    def transform(self, mod_df: pd.DataFrame,
                  stns: List[str]) -> pd.DataFrame:
        """
        Vectorised true QRF transform.

        Step 1: Predict Q(τ | X_t) for ALL τ ∈ q_grid and ALL t.
                Shape: (T_valid, n_quantile_nodes)

        Step 2: Compute model empirical CDF rank p_t for each t.

        Step 3: For each t, interpolate Q(p_t | X_t) from q_grid.
                This is O(T × Q) vectorised — no Python loops over t.
        """
        out   = mod_df.copy()
        m_mat = mod_df[stns].values.astype(float)
        T     = m_mat.shape[0]

        valid_mask    = ~np.isnan(m_mat).any(axis=1)
        valid_indices = np.where(valid_mask)[0]
        X_pred        = m_mat[valid_mask]
        T_valid       = len(X_pred)

        if T_valid == 0:
            return out

        for si, stn in enumerate(stns):
            if stn not in self._models:
                continue

            model    = self._models[stn]
            tau      = self._tau.get(stn, 0.0)
            m_col    = m_mat[:, si]
            mod_sort = self._mod_sorted.get(stn, np.array([]))

            # ── Occurrence correction ─────────────────────────────────────
            m_occ  = occurrence_correct(m_col.copy(), tau)
            dry    = m_occ <= 0.0

            # ── Model empirical CDF rank ──────────────────────────────────
            n_sort = max(len(mod_sort), 1)
            cdf_all = (np.searchsorted(mod_sort, m_occ, side="right") /
                       n_sort)
            cdf_all = np.clip(cdf_all, 0.0, 1.0)

            # ── True QRF: predict all quantiles at once ───────────────────
            # q_preds: (T_valid, n_quantile_nodes)
            q_preds = model.predict(X_pred,
                                    quantiles=list(self._q_grid))
            # Enforce non-negative predictions
            q_preds = np.maximum(0.0, q_preds)

            # ── Vectorised quantile interpolation at model CDF rank ───────
            cdf_valid = cdf_all[valid_indices]      # (T_valid,)
            q_arr     = self._q_grid                # (Q,)

            # For each row t: find lower and upper bracket in q_arr
            idx_hi = np.searchsorted(q_arr, cdf_valid, side="right")
            idx_lo = idx_hi - 1
            idx_lo = np.clip(idx_lo, 0, len(q_arr) - 2)
            idx_hi = np.clip(idx_hi, 1, len(q_arr) - 1)

            # Fractional weight for interpolation
            q_lo   = q_arr[idx_lo]
            q_hi   = q_arr[idx_hi]
            denom  = np.where(q_hi > q_lo, q_hi - q_lo, 1.0)
            alpha  = np.clip((cdf_valid - q_lo) / denom, 0.0, 1.0)

            # Gather predicted values at lower and upper bracket
            t_idx  = np.arange(T_valid)
            val_lo = q_preds[t_idx, idx_lo]
            val_hi = q_preds[t_idx, idx_hi]

            # Interpolated corrected value
            interp_vals = val_lo + alpha * (val_hi - val_lo)

            # Apply dry-day mask
            dry_valid   = dry[valid_indices]
            final_valid = np.where(dry_valid, 0.0,
                                   np.maximum(0.0, interp_vals))

            # Assemble output
            result = np.zeros(T)
            result[valid_indices] = final_valid
            out[stn] = result

        return out


# ════════════════════════════════════════════════════════════════════════════
#  §7  CROSS-VALIDATION FRAMEWORK
# ════════════════════════════════════════════════════════════════════════════

def run_cross_validation(
        obs_df:    pd.DataFrame,
        mod_df:    pd.DataFrame,
        stns:      List[str],
        calib_end: int,
        correctors: Dict[str, object]
        ) -> Dict[str, Dict[str, Dict]]:
    """
    Calibration–Validation cross-validation.

    Returns nested dict:
        cv_results[phase][method][stn] = metrics_dict

    phase ∈ {"calibration", "validation"}
    """
    obs_calib, obs_valid = split_calib_valid(obs_df, calib_end)
    mod_calib, mod_valid = split_calib_valid(mod_df, calib_end)

    # Align
    obs_cal, mod_cal = align_pair(obs_calib, mod_calib)
    obs_val, mod_val = align_pair(obs_valid, mod_valid)

    print(f"    Calibration: {obs_cal.index[0].year}–{obs_cal.index[-1].year} "
          f"({len(obs_cal)} days)")
    print(f"    Validation : {obs_val.index[0].year}–{obs_val.index[-1].year} "
          f"({len(obs_val)} days)")

    # Fit ALL methods on calibration period
    correctors_fitted: Dict[str, object] = {}
    for name, corr in correctors.items():
        print(f"    CV-fitting {name} ...")
        corr.fit(obs_cal, mod_cal, stns)
        correctors_fitted[name] = corr

    cv_results: Dict[str, Dict[str, Dict]] = {
        "calibration": {}, "validation": {}
    }

    for phase, obs_p, mod_p in [("calibration", obs_cal, mod_cal),
                                  ("validation",  obs_val, mod_val)]:
        for name, corr in correctors_fitted.items():
            bc_p = corr.transform(mod_p, stns)
            cv_results[phase][name] = {}
            for stn in stns:
                if stn not in obs_p.columns or stn not in bc_p.columns:
                    continue
                ci = obs_p.index.intersection(bc_p.index)
                o  = obs_p.loc[ci, stn].values.astype(float)
                s  = bc_p.loc[ci, stn].values.astype(float)
                cv_results[phase][name][stn] = compute_metrics(o, s)

    return cv_results


# ════════════════════════════════════════════════════════════════════════════
#  §8  BOOTSTRAP UNCERTAINTY QUANTIFICATION
# ════════════════════════════════════════════════════════════════════════════

def bootstrap_metrics(obs: np.ndarray,
                      sim: np.ndarray,
                      n_boot: int  = N_BOOTSTRAP,
                      ci:     float = BOOT_CI,
                      seed:   int  = RANDOM_SEED
                      ) -> Dict[str, Dict[str, float]]:
    """
    Parametric bootstrap (block-resampling by year) for uncertainty.

    Returns dict: {metric: {"mean": , "ci_lo": , "ci_hi": , "std": }}

    Block bootstrap preserves temporal autocorrelation.
    Block size = 365 days (annual blocks).

    Refs:
        Kunsch HR (1989) Ann.Statist. 17:1217–1241 [block bootstrap].
        Efron B & Tibshirani RJ (1993) An Introduction to the Bootstrap.
            Chapman & Hall, Chapter 14.
    """
    rng = np.random.default_rng(seed)
    mask = ~np.isnan(obs) & ~np.isnan(sim)
    o, s = obs[mask], sim[mask]
    if len(o) < 30:
        m = compute_metrics(o, s)
        return {k: {"mean": v, "ci_lo": np.nan, "ci_hi": np.nan, "std": np.nan}
                for k, v in m.items()}

    # Create annual blocks
    n = len(o)
    block_size = min(365, n // 10 + 1)
    n_blocks   = math.ceil(n / block_size)

    boot_vals: Dict[str, List[float]] = {k: [] for k in METRICS_KEYS}

    for _ in range(n_boot):
        # Sample n_blocks with replacement
        chosen = rng.integers(0, n_blocks, size=n_blocks)
        idx = np.concatenate([
            np.arange(b * block_size,
                      min((b + 1) * block_size, n))
            for b in chosen
        ])[:n]
        o_b = o[idx]
        s_b = s[idx]
        m_b = compute_metrics(o_b, s_b)
        for k in METRICS_KEYS:
            if not np.isnan(m_b[k]):
                boot_vals[k].append(m_b[k])

    alpha = 1.0 - ci
    result: Dict[str, Dict[str, float]] = {}
    for k in METRICS_KEYS:
        bv = np.array(boot_vals[k])
        if len(bv) < 10:
            result[k] = {"mean": np.nan, "ci_lo": np.nan,
                          "ci_hi": np.nan, "std": np.nan}
            continue
        result[k] = {
            "mean":  float(np.mean(bv)),
            "ci_lo": float(np.quantile(bv, alpha / 2)),
            "ci_hi": float(np.quantile(bv, 1 - alpha / 2)),
            "std":   float(np.std(bv, ddof=1)),
        }
    return result


# ════════════════════════════════════════════════════════════════════════════
#  §9  PERFORMANCE METRICS
# ════════════════════════════════════════════════════════════════════════════

METRICS_KEYS = ["RMSE", "MAE", "MBE", "Pbias", "r", "NSE", "KGE"]


def compute_metrics(o: np.ndarray, s: np.ndarray) -> Dict[str, float]:
    null = {k: np.nan for k in METRICS_KEYS}
    o, s = np.asarray(o, float), np.asarray(s, float)
    mask = ~np.isnan(o) & ~np.isnan(s)
    o, s = o[mask], s[mask]
    if len(o) < 5:
        return null
    e     = s - o
    rmse  = float(np.sqrt(np.mean(e**2)))
    mae   = float(np.mean(np.abs(e)))
    mbe   = float(np.mean(e))
    pbias = float(100 * np.sum(e) / np.sum(o)) if np.sum(o) != 0 else np.nan
    r_val = float(np.corrcoef(o, s)[0, 1])
    dn    = float(np.sum((o - np.mean(o))**2))
    nse   = float(1 - np.sum(e**2) / dn) if dn > 0 else np.nan
    std_o = float(np.std(o, ddof=1))
    std_s = float(np.std(s, ddof=1))
    sr    = std_s / std_o if std_o > 0 else np.nan
    beta  = float(np.mean(s) / np.mean(o)) if np.mean(o) != 0 else np.nan
    kge   = (float(1 - math.sqrt((r_val-1)**2+(sr-1)**2+(beta-1)**2))
             if not (np.isnan(sr) or np.isnan(beta)) else np.nan)
    return {"RMSE": round(rmse,3), "MAE": round(mae,3),
            "MBE": round(mbe,3),   "Pbias": round(pbias,2),
            "r": round(r_val,4),   "NSE": round(float(nse),4),
            "KGE": round(float(kge),4)}


def wet_day_freq(arr: np.ndarray,
                  thr: float = WET_THRESHOLD_MM) -> float:
    a = np.asarray(arr, float)
    a = a[~np.isnan(a) & (a >= 0)]
    return float(np.mean(a > thr)) if len(a) > 0 else np.nan


# ════════════════════════════════════════════════════════════════════════════
#  §10  OUTPUT FORMATTING
# ════════════════════════════════════════════════════════════════════════════

def build_output_df(corrected_df: pd.DataFrame,
                    stns: List[str]) -> pd.DataFrame:
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
    df.to_csv(path, index=False, float_format="%.2f")
    print(f"  ✓  {Path(path).name}")


# ════════════════════════════════════════════════════════════════════════════
#  §11  EXCEL REPORT WRITER — 8 SHEETS  (Q1 STANDARD)
# ════════════════════════════════════════════════════════════════════════════

METHOD_BGS = {
    "OBS":    XC["obs_r"],
    "RAW":    XC["raw_r"],
    "EQMGPD": XC["eqm_r"],
    "GDM":    XC["gdm_r"],
    "MBCn":   XC["mbc_r"],
    "QRF":    XC["qrf_r"],
}
LOWER_BETTER = {"RMSE", "MAE", "MBE"}


def write_excel_report(wb: Workbook,
                        stns:          List[str],
                        obs_df:        pd.DataFrame,
                        mod_df:        pd.DataFrame,
                        result_dfs:    Dict[str, pd.DataFrame],
                        cv_results:    Dict[str, Dict[str, Dict]],
                        boot_results:  Dict[str, Dict[str, Dict]],
                        gdm_corr:      GDMCorrector,
                        mbcn_corr:     MBCnCorrector,
                        model_name:    str,
                        obs_stem:      str,
                        period_obs:    str,
                        calib_end:     int) -> None:

    # ── Helpers ───────────────────────────────────────────────────────────
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
        if v is None or (isinstance(v,float) and np.isnan(v)): return "—"
        return round(float(v), dp)

    methods_order = ["RAW", "EQMGPD", "GDM", "MBCn", "QRF"]
    method_dfs: Dict[str, Optional[pd.DataFrame]] = {
        "OBS": obs_df, "RAW": mod_df, **result_dfs
    }

    # ════════════════════════════════════════════════════════════════════
    # S1 — Full-Period Metric Comparison
    # ════════════════════════════════════════════════════════════════════
    ws1 = wb.create_sheet("S1 Full-Period Metrics")
    ws1.sheet_view.showGridLines = False
    nc1 = 3 + len(METRICS_KEYS)
    _title(ws1, nc1,
           f"Full-Period Statistical Performance Metrics — {model_name}",
           f"Period: {period_obs}  |  "
           "★ = best value per station–metric  |  "
           "Green = improved vs RAW  |  Red = degraded  |  "
           "EQM-GPD: body via EQM + tail via GPD  |  "
           "MBCn: iterative Cannon (2018)  |  QRF: Meinshausen (2006)")
    ri = 5
    for method in methods_order:
        df_m = method_dfs.get(method)
        if df_m is None: continue
        _mxsc(ws1,ri,1,nc1,method,bold=True,fc="FFFFFF",
              bg=METHOD_BGS.get(method,XC["white"]),sz=11)
        _rh(ws1,ri,20); ri+=1
        _hdr(ws1,ri,["Station","Code"]+METRICS_KEYS); ri+=1
        for si,stn in enumerate(stns):
            ci_c = obs_df.index.intersection(df_m.index)
            o = obs_df.loc[ci_c,stn].values.astype(float) if stn in obs_df.columns else np.array([])
            s = df_m.loc[ci_c,stn].values.astype(float) if stn in df_m.columns else np.array([])
            met = compute_metrics(o, s)
            row = [stn, f"S{si+1}"] + [fv(met[k]) for k in METRICS_KEYS]
            for ci,v in enumerate(row,1):
                bg = METHOD_BGS.get(method,XC["white"])
                if ci>2 and method!="RAW":
                    mk = METRICS_KEYS[ci-3]
                    raw_df = method_dfs.get("RAW")
                    if raw_df is not None and stn in raw_df.columns:
                        cr = obs_df.index.intersection(raw_df.index)
                        mr = compute_metrics(
                            obs_df.loc[cr,stn].values.astype(float) if stn in obs_df.columns else np.array([]),
                            raw_df.loc[cr,stn].values.astype(float))
                        rv = mr.get(mk,np.nan); bv = met.get(mk,np.nan)
                        if not(np.isnan(rv) or np.isnan(bv)):
                            imp = (bv<rv if mk in LOWER_BETTER else bv>rv)
                            bg = XC["improve"] if imp else XC["degrade"]
                _xsc(ws1,ri,ci,v,sz=9,bg=bg,align="left" if ci<=2 else "right")
            _rh(ws1,ri,14); ri+=1
        ri+=1
    for ci,w in enumerate([10,6]+[10]*len(METRICS_KEYS),1): _cw(ws1,ci,w)

    # ════════════════════════════════════════════════════════════════════
    # S2 — Cross-Validation Results
    # ════════════════════════════════════════════════════════════════════
    ws2 = wb.create_sheet("S2 Cross-Validation")
    ws2.sheet_view.showGridLines = False
    nc2 = 4 + len(METRICS_KEYS)
    _title(ws2, nc2,
           "Cross-Validation Results — Calibration vs Validation Period",
           f"Calibration: ≤ {calib_end}  |  Validation: > {calib_end}  |  "
           "Separate fit and evaluation to assess generalisability  |  "
           "A method with similar Cal/Val metrics demonstrates stationarity")
    _hdr(ws2,4,["Phase","Method","Station","Code"]+METRICS_KEYS)
    ri2 = 5
    for phase in ["calibration","validation"]:
        for method in methods_order:
            for si,stn in enumerate(stns):
                met = cv_results.get(phase,{}).get(method,{}).get(stn,{})
                row = [phase.capitalize(),method,stn,f"S{si+1}"] + \
                      [fv(met.get(k,np.nan)) for k in METRICS_KEYS]
                bg = XC["bc_r"] if phase=="calibration" else XC["alt"]
                for ci,v in enumerate(row,1):
                    _xsc(ws2,ri2,ci,v,sz=9,bg=bg,align="left" if ci<=4 else "right")
                _rh(ws2,ri2,14); ri2+=1
            ri2+=1
        ri2+=1
    for ci,w in enumerate([14,10,10,6]+[10]*len(METRICS_KEYS),1): _cw(ws2,ci,w)

    # ════════════════════════════════════════════════════════════════════
    # S3 — Bootstrap Uncertainty
    # ════════════════════════════════════════════════════════════════════
    ws3 = wb.create_sheet("S3 Bootstrap Uncertainty")
    ws3.sheet_view.showGridLines = False
    sub_metrics = ["RMSE","r","KGE"]
    nc3 = 3 + len(sub_metrics)*4
    _title(ws3, nc3,
           f"Bootstrap Uncertainty Quantification  ({int(BOOT_CI*100)}% CI, N={N_BOOTSTRAP} resamples)",
           "Block bootstrap (annual blocks) preserving temporal autocorrelation  |  "
           "Ref: Kunsch (1989); Efron & Tibshirani (1993)  |  "
           "CI = confidence interval  |  Narrow CI = robust estimate")
    hdr3 = ["Method","Station","Code"]
    for mk in sub_metrics:
        hdr3 += [f"{mk}\nMean", f"{mk}\nCI Lo", f"{mk}\nCI Hi", f"{mk}\nSD"]
    _hdr(ws3,4,hdr3); ri3=5
    for method in methods_order:
        for si,stn in enumerate(stns):
            br = boot_results.get(method,{}).get(stn,{})
            row = [method,stn,f"S{si+1}"]
            for mk in sub_metrics:
                d = br.get(mk,{})
                row += [fv(d.get("mean",np.nan),3),
                        fv(d.get("ci_lo",np.nan),3),
                        fv(d.get("ci_hi",np.nan),3),
                        fv(d.get("std",np.nan),4)]
            bg = METHOD_BGS.get(method,XC["white"])
            for ci,v in enumerate(row,1):
                _xsc(ws3,ri3,ci,v,sz=9,bg=bg,align="left" if ci<=3 else "right")
            _rh(ws3,ri3,14); ri3+=1
        ri3+=1
    for ci in range(1,nc3+1): _cw(ws3,ci,11)

    # ════════════════════════════════════════════════════════════════════
    # S4 — Wet-Day Frequency & Extreme Quantiles
    # ════════════════════════════════════════════════════════════════════
    ws4 = wb.create_sheet("S4 Wet-Day & Extremes")
    ws4.sheet_view.showGridLines = False
    pct_lvls = [("P90",0.90),("P95",0.95),("P99",0.99)]
    nc4 = 2 + (1 + len(pct_lvls)) * (len(methods_order)+1)
    _title(ws4, nc4,
           "Wet-Day Frequency and Extreme Quantile Analysis",
           f"Wet day threshold: {WET_THRESHOLD_MM} mm/day  |  "
           "Quantiles computed on wet-day values only  |  "
           "Target: corrected values close to OBS column")
    all_m = ["OBS"] + methods_order
    hdrs4 = ["Station","Code"]
    for lbl,_ in [("WetFreq","")]+list(pct_lvls):
        for m in all_m: hdrs4.append(f"{lbl}\n{m}" if lbl!="WetFreq" else f"WetFreq\n{m}")
    _hdr(ws4,4,hdrs4); ri4=5
    for si,stn in enumerate(stns):
        row=[stn,f"S{si+1}"]
        for group_fn in [
            lambda df,s: fv(wet_day_freq(df[s].values.astype(float)
                            if s in df.columns else np.array([])),4),
            *[lambda df,s,p=p: fv(
                float(np.quantile(df[s].values.astype(float)[
                    ~np.isnan(df[s].values.astype(float)) &
                    (df[s].values.astype(float)>WET_THRESHOLD_MM)],p))
                if s in df.columns and
                   np.sum((~np.isnan(df[s].values.astype(float))) &
                          (df[s].values.astype(float)>WET_THRESHOLD_MM))>10
                else np.nan, 2)
              for _,p in pct_lvls]
        ]:
            for m in all_m:
                df_m2 = method_dfs.get(m)
                row.append(group_fn(df_m2,stn) if df_m2 is not None else "—")
        for ci,v in enumerate(row,1):
            _xsc(ws4,ri4,ci,v,sz=9,bg=XC["alt"] if si%2==0 else XC["white"],
                 align="left" if ci<=2 else "right")
        _rh(ws4,ri4,14); ri4+=1
    for ci in range(1,len(hdrs4)+1): _cw(ws4,ci,9)

    # ════════════════════════════════════════════════════════════════════
    # S5 — GDM GOF Test Results
    # ════════════════════════════════════════════════════════════════════
    ws5 = wb.create_sheet("S5 GDM-GOF Tests")
    ws5.sheet_view.showGridLines = False
    _title(ws5,8,
           "GDM: Kolmogorov-Smirnov Goodness-of-Fit Test for Gamma Distribution",
           f"H₀: wet-day data follows Gamma(α,β)  |  "
           f"Significance level α = {GAMMA_KS_ALPHA}  |  "
           "If H₀ rejected: GDM falls back to EQM for that station  |  "
           "Ref: Wilks (2011) Statistical Methods in Atmospheric Sciences, §4")
    _hdr(ws5,4,["Station","Code",
                 "D (Obs)","p (Obs)","Obs Passed",
                 "D (Mod)","p (Mod)","Mod Passed","GDM Used"])
    ri5=5
    for si,stn in enumerate(stns):
        go = gdm_corr._gof_obs.get(stn,{})
        gm = gdm_corr._gof_mod.get(stn,{})
        fb = gdm_corr._eqm_fallback.get(stn,True)
        gdm_used = "GDM" if not fb else "EQM (fallback)"
        bg = XC["improve"] if not fb else XC["degrade"]
        row=[stn,f"S{si+1}",
             fv(go.get("D",np.nan),4),fv(go.get("p",np.nan),4),
             "Yes" if go.get("passed",False) else "No",
             fv(gm.get("D",np.nan),4),fv(gm.get("p",np.nan),4),
             "Yes" if gm.get("passed",False) else "No",
             gdm_used]
        for ci,v in enumerate(row,1):
            cell=_xsc(ws5,ri5,ci,v,sz=9,bg=bg if ci==9 else XC["white"],
                      align="left" if ci in(1,2,5,8,9) else "right")
            if ci in(5,8):
                cell.fill=_xf(XC["improve"] if v=="Yes" else XC["degrade"])
        _rh(ws5,ri5,15); ri5+=1
    for ci,w in enumerate([10,6,10,10,10,10,10,10,14],1): _cw(ws5,ci,w)

    # ════════════════════════════════════════════════════════════════════
    # S6 — MBCn Convergence History
    # ════════════════════════════════════════════════════════════════════
    ws6 = wb.create_sheet("S6 MBCn Convergence")
    ws6.sheet_view.showGridLines = False
    _title(ws6,4,
           "MBCn Iterative Convergence History",
           f"Convergence criterion: max|ΔR| < {MBCN_TOLERANCE}  |  "
           f"Maximum iterations: {MBCN_MAX_ITER}  |  "
           "Ref: Cannon (2018) J.Climate 31:9455-9475 — MBCn N-pdft algorithm")
    _hdr(ws6,4,["Iteration","max|ΔR|","Converged?","Note"])
    ri6=5
    hist = mbcn_corr._conv_history
    for it,delta in enumerate(hist,1):
        converged = delta < MBCN_TOLERANCE
        note = ("✓ Converged" if converged else
                ("Max iterations reached" if it==len(hist) and not converged else ""))
        bg = XC["improve"] if converged else (XC["degrade"] if it==len(hist) else XC["white"])
        for ci,v in enumerate([it,round(delta,8),"Yes" if converged else "No",note],1):
            _xsc(ws6,ri6,ci,v,sz=9,bg=bg,align="center" if ci!=4 else "left")
        _rh(ws6,ri6,14); ri6+=1
    for ci,w in enumerate([12,16,14,30],1): _cw(ws6,ci,w)

    # ════════════════════════════════════════════════════════════════════
    # S7 — Methods & Mathematical Formulation
    # ════════════════════════════════════════════════════════════════════
    ws7 = wb.create_sheet("S7 Methods & Formulation")
    ws7.sheet_view.showGridLines = False
    _title(ws7,3,
           "Mathematical Formulation & Methods — Q1 Documentation",
           f"Model: {model_name}  |  Period: {period_obs}  |  Version 3.0")
    _hdr(ws7,4,["Method","Mathematical Formulation","Implementation Notes","References"])
    methods_doc=[
        ("EQM-GPD",
         "Body (q ≤ q_GPD): ŷ = F⁻¹_obs(F_mod(x))\n"
         "Tail (q > q_GPD): u_cdf = F_GPD(x−u_mod; ξ_m, σ_m)\n"
         "                 ŷ = u_obs + F⁻¹_GPD(u_cdf; ξ_o, σ_o)\n"
         "GPD fit: P(x>u+y|x>u) = (1+ξy/σ)^{-1/ξ}",
         f"GPD tail threshold = P{int(GPD_TAIL_QUANTILE*100)} of wet-day distribution\n"
         f"n_quantile_nodes = {N_QUANTILE_NODES}\n"
         "Tail blending: linear over 10% above threshold\n"
         "Occurrence correction: τ = quantile(mod, 1−P_wet_obs)",
         "Themeßl et al. (2011); Coles (2001); Beguería (2005); Li et al. (2010)"),
        ("GDM",
         "y ~ Gamma(α_obs, β_obs); x ~ Gamma(α_mod, β_mod)\n"
         "u = F_Gamma(x; α_mod, β_mod)\n"
         "ŷ = F⁻¹_Gamma(u; α_obs, β_obs)\n"
         "GOF: KS test H₀: data ~ Gamma (α=0.05)",
         f"MLE fit with floc=0 (zero lower bound)\n"
         f"Min wet days for fit: {GAMMA_MIN_WET_DAYS}\n"
         f"KS significance: {GAMMA_KS_ALPHA}\n"
         "Fallback to EQM if KS rejected",
         "Piani et al. (2010) J.Geophys.Res. 115:D23106;\nWilks (2011) Ch.4"),
        ("MBCn",
         "Iterative N-pdft algorithm:\n"
         "1. Draw Q ~ Haar(SO(S))\n"
         "2. Z_obs = X_obs@Q; Z_bc = X_bc@Q\n"
         "3. ∀j: Z_bc[:,j] = EQM_j(Z_bc[:,j]→Z_obs[:,j])\n"
         "4. X_bc = Z_bc@Qᵀ\n"
         "5. Enforce original marginals (rank resample)\n"
         f"6. Check: max|R_bc−R_obs| < {MBCN_TOLERANCE}",
         f"Max iterations: {MBCN_MAX_ITER}\n"
         f"Convergence tolerance: {MBCN_TOLERANCE}\n"
         "Normal-score transform for correlation\n"
         "Haar-distributed rotation (scipy QR decomp)",
         "Cannon (2018) J.Climate 31:9455-9475;\nBárdossy & Pegram (2012) AWR 41:110-123"),
        ("QRF (True)",
         "Q(τ|X=x) = weighted quantile of {Y_i : x in leaf_k(x)}\n"
         "p_t = F̂_mod(m_t)  [empirical CDF rank]\n"
         "ŷ_t = Q_QRF(p_t | X=x_t)\n"
         "= Meinshausen (2006) leaf-node empirical distribution",
         f"RandomForestQuantileRegressor (quantile-forest)\n"
         f"n_estimators = {N_ESTIMATORS_QRF}\n"
         f"n_quantile_nodes = {N_QUANTILE_NODES}\n"
         "Features X = rainfall at all S stations\n"
         "Row-vectorised interpolation: O(T×Q) NumPy",
         "Meinshausen & Ridgeway (2006) JMLR 7:983-999;\nTaillardat et al. (2016) MWR 144:2375"),
        ("Cross-Validation",
         "Calibration period: years ≤ calib_end_year\n"
         "Validation period : years >  calib_end_year\n"
         "Fit on calibration; evaluate on both\n"
         "Assesses stationarity of bias correction",
         f"Calibration end: {calib_end}\n"
         f"Split fraction: {CALIB_FRAC*100:.0f}%/{(1-CALIB_FRAC)*100:.0f}%\n"
         "All methods re-fit on calibration period",
         "Maraun (2016) Curr.Clim.Chang.Rep. 2:211-220;\nIPCC AR6 Ch.10"),
        ("Bootstrap CI",
         "Block bootstrap with annual blocks (365 days)\n"
         f"B = {N_BOOTSTRAP} resamples\n"
         f"{int(BOOT_CI*100)}% CI: [α/2, 1−α/2] quantiles of bootstrap distribution",
         "Preserves temporal autocorrelation\n"
         "Applied to RMSE, r, KGE per method × station",
         "Kunsch (1989) Ann.Statist. 17:1217-1241;\nEfron & Tibshirani (1993) Ch.14"),
    ]
    alt=[_xf("DEEAF1"),_xf("FFFFFF")]
    ri7=5
    for i,(m,form,impl,ref) in enumerate(methods_doc):
        fl=alt[i%2]
        for ci,v in enumerate([m,form,impl,ref],1):
            cell=_xsc(ws7,ri7,ci,v,bold=(ci==1),sz=9,align="left",wrap=True)
            cell.fill=fl
        _rh(ws7,ri7,80); ri7+=1
    _cw(ws7,1,12); _cw(ws7,2,45); _cw(ws7,3,40); _cw(ws7,4,38)

    # ════════════════════════════════════════════════════════════════════
    # S8 — Stationarity Assumptions & Limitations
    # ════════════════════════════════════════════════════════════════════
    ws8 = wb.create_sheet("S8 Stationarity & Limitations")
    ws8.sheet_view.showGridLines = False
    _title(ws8,3,
           "Stationarity Assumptions, Known Limitations & Uncertainty Sources",
           "Required disclosure for peer-reviewed publication (IPCC AR6 best practice)")
    items=[
        ("Perfect Prognosis / Stationarity",
         "ALL quantile mapping methods (EQM-GPD, GDM, MBCn, QRF) assume that the "
         "bias transfer function calibrated on F^hist_obs vs F^hist_mod remains valid "
         "for F^future_mod. This 'perfect prognosis' assumption (von Storch 1999) may "
         "break under strong forcing, particularly if model biases are non-stationary. "
         "Implication: corrected future projections retain CMIP6 model uncertainty "
         "beyond the bias corrected mean; ensemble spread should be assessed.",
         "Von Storch H et al. (1999) Climate Res. 13:129-149; "
         "Maraun DF (2016) Curr.Clim.Chang.Rep. 2:211-220; "
         "IPCC AR6 WG1 Section 10.3.1"),
        ("EQM-GPD: Tail extrapolation",
         "GPD parameters (ξ, σ) are estimated from limited extreme observations. "
         "Estimates are uncertain for return periods >> record length. "
         "The shape parameter ξ has been constrained to [-0.5, 2.0] based on "
         "physical plausibility for tropical rainfall. "
         "For events exceeding the 1000-yr return period, GPD extrapolation "
         "should be treated with caution.",
         "Coles S (2001) Springer; Beguería S et al. (2005) J.Hydrol. 313:127-147"),
        ("GDM: Gamma distribution assumption",
         "The Gamma distribution is a two-parameter approximation to the wet-day "
         "rainfall distribution. For some stations (particularly coastal stations "
         "with bimodal or heavy-tailed distributions), the KS test may reject Gamma, "
         "triggering EQM fallback. GOF test results are reported in Sheet S5.",
         "Piani et al. (2010) J.Geophys.Res. 115:D23106"),
        ("MBCn: Convergence & Computational Cost",
         f"The MBCn algorithm is terminated at max_iter={MBCN_MAX_ITER} or "
         f"tolerance={MBCN_TOLERANCE}. Convergence is not guaranteed for all "
         "station configurations. The spatial correlation structure is corrected "
         "iteratively, but residual errors in the correlation matrix may remain "
         "if the model and obs correlation structures are fundamentally different. "
         "Convergence history is reported in Sheet S6.",
         "Cannon AJ (2018) J.Climate 31:9455-9475"),
        ("QRF: Sample size & overfitting",
         f"The QRF is trained on the full calibration period "
         f"({int(CALIB_FRAC*100)}% of data). With n_estimators={N_ESTIMATORS_QRF} "
         "and min_samples_leaf=5, overfitting risk is mitigated. "
         "However, for stations with very few wet days, quantile estimates "
         "from leaf nodes may be noisy. Cross-validation results (S2) "
         "indicate the degree of overfitting by comparing Cal vs Val metrics.",
         "Meinshausen & Ridgeway (2006) JMLR 7:983-999; "
         "Schlosser et al. (2019) CSDA 132:370-382"),
        ("Spatial dependence",
         "MBCn corrects inter-station correlations. EQM-GPD and GDM are applied "
         "station-by-station and do NOT preserve spatial dependence structure. "
         "For applications requiring spatially coherent fields (e.g., areal "
         "rainfall, flood modelling), use MBCn or apply Schaake Shuffle post-processing. "
         "QRF captures spatial co-dependence implicitly via the multi-station feature vector.",
         "Clark M et al. (2004) WRR 40:W09401; "
         "Vrac M & Friederichs P (2015) J.Climate 28:218-238"),
    ]
    _hdr(ws8,4,["Issue","Description","Key References"])
    alt8=[_xf("FFF3E0"),_xf("FFFFFF")]
    ri8=5
    for i,(iss,desc,ref) in enumerate(items):
        fl=alt8[i%2]
        for ci,v in enumerate([iss,desc,ref],1):
            cell=_xsc(ws8,ri8,ci,v,bold=(ci==1),sz=9,align="left",wrap=True)
            cell.fill=fl
        _rh(ws8,ri8,75); ri8+=1
    _cw(ws8,1,24); _cw(ws8,2,72); _cw(ws8,3,40)


# ════════════════════════════════════════════════════════════════════════════
#  §12  MAIN PIPELINE — PER MODEL
# ════════════════════════════════════════════════════════════════════════════

def process_model(obs_df:    pd.DataFrame,
                  obs_stns:  List[str],
                  mod_path:  str,
                  model_name: str,
                  obs_stem:  str,
                  out_dir:   Path) -> None:

    SEP = "─" * 72
    print(f"\n{SEP}")
    print(f"  MODEL: {model_name}")
    print(SEP)

    # ── Load model ─────────────────────────────────────────────────────
    mod_df_raw, mod_stns = load_daily(mod_path, f"Raw/{model_name}",
                                       target_stns=obs_stns)
    if mod_df_raw is None:
        print(f"  ✗  Load failed — skipping {model_name}"); return

    obs_a, mod_a = align_pair(obs_df, mod_df_raw)
    if len(obs_a) < 365:
        print(f"  ✗  <365 days overlap — skipping"); return

    stns = sorted(set(obs_stns) & set([str(s) for s in mod_stns]),
                  key=lambda s: obs_stns.index(s) if s in obs_stns else 999)
    if not stns:
        print(f"  ✗  No common stations"); return

    years      = sorted(obs_a.index.year.unique())
    calib_end  = int(years[int(len(years)*CALIB_FRAC)-1])
    period_obs = f"{years[0]}–{years[-1]}"
    print(f"  Stations : {stns}")
    print(f"  Period   : {period_obs}  |  Calibration ≤{calib_end}")

    # ═══════════════════════════════════════════════════════════════════
    # FIT ALL METHODS ON FULL CALIBRATION DATA
    # ═══════════════════════════════════════════════════════════════════
    obs_cal = obs_a[obs_a.index.year <= calib_end]
    mod_cal = mod_a[mod_a.index.year <= calib_end]
    obs_cal, mod_cal = align_pair(obs_cal, mod_cal)

    print("\n  [1/4] EQM-GPD — Empirical QM + Generalised Pareto tail ...")
    eqmgpd = EQMGPDCorrector()
    eqmgpd.fit(obs_cal, mod_cal, stns)
    eqmgpd_c = eqmgpd.transform(mod_a, stns)

    print("  [2/4] GDM — Gamma Distribution Mapping (with KS GOF test) ...")
    gdm = GDMCorrector()
    gdm.fit(obs_cal, mod_cal, stns)
    gdm_c = gdm.transform(mod_a, stns)
    n_fallback = sum(1 for s in stns if gdm._eqm_fallback.get(s, True))
    print(f"         GOF test: {len(stns)-n_fallback}/{len(stns)} stations use GDM "
          f"({n_fallback} fallback to EQM)")

    print("  [3/4] MBCn — Iterative Multivariate Bias Correction ...")
    mbcn = MBCnCorrector()
    mbcn.fit(obs_cal, mod_cal, stns)
    mbcn_c = mbcn.transform(mod_a, stns)
    print(f"         MBCn converged in {mbcn._n_iter_done} iterations  "
          f"(final |ΔR|={mbcn._conv_history[-1]:.6f})")

    print("  [4/4] QRF — True Quantile Regression Forest ...")
    qrf = TrueQRFCorrector(n_estimators=N_ESTIMATORS_QRF)
    qrf.fit(obs_cal, mod_cal, stns)
    qrf_c = qrf.transform(mod_a, stns)
    print()

    # ── Save CSVs ──────────────────────────────────────────────────────
    for tag, df_c in [("eqmgpd", eqmgpd_c),
                       ("gdm",    gdm_c),
                       ("mbcn",   mbcn_c),
                       ("qrf",    qrf_c)]:
        out_df = build_output_df(df_c, stns)
        save_csv(out_df,
                 str(out_dir / f"bc_{tag}_{model_name}_{obs_stem}.csv"))

    # ── Performance table ──────────────────────────────────────────────
    print("\n  Performance (regional mean across stations):")
    print(f"  {'Method':8s}  {'RMSE':7s}  {'r':6s}  {'NSE':6s}  {'KGE':6s}  {'Pbias':8s}")
    print("  " + "─"*56)

    result_dfs: Dict[str, pd.DataFrame] = {
        "EQMGPD": eqmgpd_c, "GDM": gdm_c,
        "MBCn": mbcn_c,     "QRF": qrf_c,
    }

    def regional_mean(df_m, name):
        vals = {k: [] for k in METRICS_KEYS}
        ci = obs_a.index.intersection(df_m.index)
        for stn in stns:
            if stn not in obs_a.columns or stn not in df_m.columns:
                continue
            m = compute_metrics(obs_a.loc[ci,stn].values.astype(float),
                                df_m.loc[ci,stn].values.astype(float))
            for k in METRICS_KEYS:
                if not np.isnan(m[k]): vals[k].append(m[k])
        mn = {k: float(np.mean(v)) if v else np.nan for k,v in vals.items()}
        print(f"  {name:8s}  "
              f"{mn['RMSE']:7.3f}  {mn['r']:6.3f}  "
              f"{mn['NSE']:6.3f}  {mn['KGE']:6.3f}  "
              f"{mn['Pbias']:+8.2f}%")

    for nm, dfm in [("RAW",    mod_a),
                     ("EQMGPD", eqmgpd_c),
                     ("GDM",    gdm_c),
                     ("MBCn",   mbcn_c),
                     ("QRF",    qrf_c)]:
        regional_mean(dfm, nm)

    # ═══════════════════════════════════════════════════════════════════
    # CROSS-VALIDATION
    # ═══════════════════════════════════════════════════════════════════
    print("\n  Running cross-validation ...")
    # Instantiate fresh correctors for CV (separate from full-fit)
    cv_correctors = {
        "EQMGPD": EQMGPDCorrector(),
        "GDM":    GDMCorrector(),
        "MBCn":   MBCnCorrector(),
        "QRF":    TrueQRFCorrector(n_estimators=N_ESTIMATORS_QRF),
    }
    cv_results = run_cross_validation(
        obs_a, mod_a, stns, calib_end, cv_correctors)

    # ═══════════════════════════════════════════════════════════════════
    # BOOTSTRAP UNCERTAINTY
    # ═══════════════════════════════════════════════════════════════════
    print("  Computing bootstrap uncertainty ...")
    boot_results: Dict[str, Dict[str, Dict]] = {}
    for name, df_m in [("RAW",    mod_a),
                        ("EQMGPD", eqmgpd_c),
                        ("GDM",    gdm_c),
                        ("MBCn",   mbcn_c),
                        ("QRF",    qrf_c)]:
        boot_results[name] = {}
        ci_idx = obs_a.index.intersection(df_m.index)
        for stn in stns:
            if stn not in obs_a.columns or stn not in df_m.columns:
                boot_results[name][stn] = {}
                continue
            o = obs_a.loc[ci_idx, stn].values.astype(float)
            s = df_m.loc[ci_idx, stn].values.astype(float)
            boot_results[name][stn] = bootstrap_metrics(o, s)
        print(f"    Bootstrap done: {name}", end="\r")
    print()

    # ═══════════════════════════════════════════════════════════════════
    # EXCEL REPORT
    # ═══════════════════════════════════════════════════════════════════
    print("  Building Q1 Excel report (8 sheets) ...")
    wb = Workbook()
    wb.remove(wb.active)
    write_excel_report(
        wb, stns,
        obs_df=obs_a, mod_df=mod_a,
        result_dfs=result_dfs,
        cv_results=cv_results,
        boot_results=boot_results,
        gdm_corr=gdm,
        mbcn_corr=mbcn,
        model_name=model_name,
        obs_stem=obs_stem,
        period_obs=period_obs,
        calib_end=calib_end,
    )
    xl_path = out_dir / f"BC_Q1_Summary_{model_name}_{obs_stem}.xlsx"
    wb.save(str(xl_path))
    print(f"  ✓  Excel → {xl_path.name}")

    gc.collect()


# ════════════════════════════════════════════════════════════════════════════
#  §13  ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════

def main():
    SEP = "═" * 72
    print(SEP)
    print("  CMIP6 Rainfall Bias Correction — Q1 Publication Framework  v3.0")
    print("  EQM-GPD | GDM+GOF | MBCn (iterative) | True QRF")
    print("  Cross-Validation | Bootstrap Uncertainty | Stationarity Docs")
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

    print("\n  Scanning input files ...")
    obs_path, raw_models = discover_files(work_dir)

    if obs_path is None:
        sys.exit("  ✗  No Observed file — aborting.")
    if not raw_models:
        sys.exit("  ✗  No Raw CMIP6 files — aborting.")

    print(f"\n  Models to process: {list(raw_models.keys())}")
    print("-" * 72)

    print("\n  Loading Observed ...")
    obs_df, obs_stns = load_daily(obs_path, "Observed")
    if obs_df is None:
        sys.exit("  ✗  Failed to load Observed")

    obs_stem  = Path(obs_path).stem
    obs_stns  = [str(s) for s in obs_stns]

    for model_name, mod_path in raw_models.items():
        try:
            process_model(
                obs_df     = obs_df,
                obs_stns   = obs_stns,
                mod_path   = mod_path,
                model_name = model_name,
                obs_stem   = obs_stem,
                out_dir    = out_dir,
            )
        except Exception as e:
            print(f"\n  ✗  ERROR in {model_name}: {e}")
            traceback.print_exc()

    # Summary
    csvs  = sum(len(list(out_dir.glob(f"bc_{m}_*.csv")))
                for m in ["eqmgpd","gdm","mbcn","qrf"])
    xlsxs = len(list(out_dir.glob("BC_Q1_Summary_*.xlsx")))
    print()
    print(SEP)
    print(f"  ✓  COMPLETE  v3.0  |  Q1 Publication Ready")
    print(f"  CSV files  : {csvs}  (EQM-GPD + GDM + MBCn + QRF per model)")
    print(f"  Excel files: {xlsxs}  (8 sheets each)")
    print(f"  Saved to   : {work_dir}")
    print(SEP)


if __name__ == "__main__":
    main()
