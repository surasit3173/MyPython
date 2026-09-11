"""
================================================================================
 Ensemble Saturation & Bias Correction Framework for CMIP6 Precipitation
================================================================================
 Implements:
   - Quantile Delta Mapping (QDM) bias correction
   - Ensemble Saturation Analysis (bootstrap, n=1→N)
   - Extreme Precipitation Analysis (P95/P99, GEV return levels)
   - Saturation behavior under extreme conditions
   - Seasonal stratification (wet / dry)
   - Publication-quality figures (≥300 dpi)

 Scientific basis:
   - QDM:  Cannon et al. (2015), Clim. Dyn. 45:2145–2160
   - GEV:  Coles (2001), Springer
   - Ensemble saturation: Tebaldi & Knutti (2007), Phil.Trans.R.Soc.A 365:2053-75

 Author : <your name>
 Journal target : Q2–Q3 (e.g., J. Hydrol., Theor. Appl. Climatol.)
================================================================================
"""

# ─────────────────────────────────────────────────────────────────────────────
# 1. IMPORTS
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import warnings
import logging
import os
import time
from pathlib import Path
from itertools import combinations

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.lines import Line2D
import matplotlib.patches as mpatches
import seaborn as sns
from scipy import stats
from scipy.stats import (
    ks_2samp, genextreme, norm, percentileofscore
)
from scipy.interpolate import interp1d
from joblib import Parallel, delayed

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# 2. GLOBAL CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
RANDOM_SEED   = 42
N_BOOTSTRAP   = 1000          # bootstrap iterations for saturation analysis
CONVERGENCE_ε = 0.005         # marginal RMSE improvement threshold (mm)
STABILITY_W   = 5             # rolling window for ensemble-mean stability test
EXTREME_Q     = [0.90, 0.95, 0.99]   # extreme quantile thresholds
RETURN_PERIODS= [2, 5, 10, 20, 50, 100]  # years for GEV return levels
DPI           = 300
FIG_EXT       = "png"
WET_MONTHS    = [5, 6, 7, 8, 9, 10]   # May–Oct (Thai wet season example)
DRY_MONTHS    = [11, 12, 1, 2, 3, 4]  # Nov–Apr

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)
(OUTPUT_DIR / "figures").mkdir(exist_ok=True)
(OUTPUT_DIR / "tables").mkdir(exist_ok=True)

rng = np.random.default_rng(RANDOM_SEED)

# Matplotlib style ─ clean, journal-ready
plt.rcParams.update({
    "font.family"       : "DejaVu Sans",
    "font.size"         : 10,
    "axes.titlesize"    : 11,
    "axes.labelsize"    : 10,
    "legend.fontsize"   : 9,
    "xtick.labelsize"   : 9,
    "ytick.labelsize"   : 9,
    "axes.spines.top"   : False,
    "axes.spines.right" : False,
    "axes.linewidth"    : 0.8,
    "figure.dpi"        : DPI,
    "savefig.dpi"       : DPI,
    "savefig.bbox"      : "tight",
    "lines.linewidth"   : 1.5,
})

PALETTE = {
    "obs"     : "#1f4e79",   # dark blue
    "raw"     : "#c00000",   # red
    "bc"      : "#375623",   # dark green
    "ci"      : "#70ad47",   # light green (CI fill)
    "extreme" : "#7030a0",   # purple
    "neutral" : "#595959",   # grey
}

# ─────────────────────────────────────────────────────────────────────────────
# 3. SYNTHETIC DATA GENERATOR  (replace with real loader for production)
# ─────────────────────────────────────────────────────────────────────────────

def generate_synthetic_data(
    n_models: int = 10,
    hist_years: int = 30,
    future_years: int = 30,
    station_id: str = "STN_PKK",
    wet_months: list[int] = WET_MONTHS,
    dry_months: list[int] = DRY_MONTHS,
) -> tuple[pd.Series, dict[str, pd.Series], dict[str, pd.Series]]:
    """
    Generate synthetic daily precipitation time-series that mimic
    typical CMIP6 wet-dry bias patterns (over-estimation of wet-day
    frequency, under-estimation of heavy tails).

    Returns
    -------
    obs_hist   : observed historical series (pd.Series, DatetimeIndex)
    raw_hist   : dict {model_name: raw historical series}
    raw_future : dict {model_name: raw future series}
    """
    rng_local = np.random.default_rng(RANDOM_SEED)

    n_hist   = hist_years   * 365
    n_future = future_years * 365

    hist_dates   = pd.date_range("1981-01-01", periods=n_hist,   freq="D")
    future_dates = pd.date_range("2011-01-01", periods=n_future, freq="D")

    # ── Observed: gamma-distributed, seasonal modulation ──────────────────
    def seasonal_scale(dates, wet_m, base_scale=3.0, wet_scale=8.0):
        return np.where(dates.month.isin(wet_m), wet_scale, base_scale)

    obs_shape = 0.8
    obs_scale = seasonal_scale(hist_dates, wet_months)
    obs_raw   = rng_local.gamma(obs_shape, obs_scale, size=n_hist)
    obs_raw   = np.where(rng_local.uniform(size=n_hist) < 0.45, 0.0, obs_raw)
    obs_hist  = pd.Series(obs_raw, index=hist_dates, name=station_id)

    raw_hist   = {}
    raw_future = {}

    for m in range(1, n_models + 1):
        mname = f"CMIP6_M{m:02d}"
        # Model bias: wet-day freq overestimate + scale bias
        model_shape = obs_shape * rng_local.uniform(0.7, 1.3)
        bias_factor = rng_local.uniform(1.1, 1.8)

        # Historical raw
        raw_h = rng_local.gamma(
            model_shape,
            seasonal_scale(hist_dates, wet_months) * bias_factor,
            size=n_hist
        )
        # Reduce dry-day frequency to simulate drizzle bias
        dry_prob = rng_local.uniform(0.25, 0.35)
        raw_h = np.where(rng_local.uniform(size=n_hist) < dry_prob, 0.0, raw_h)
        raw_hist[mname] = pd.Series(raw_h, index=hist_dates, name=mname)

        # Future raw: add warming trend (+10–25 % in extremes, slight mean change)
        trend_factor  = rng_local.uniform(1.05, 1.25)
        raw_f = rng_local.gamma(
            model_shape * 1.02,
            seasonal_scale(future_dates, wet_months) * bias_factor * trend_factor,
            size=n_future
        )
        raw_f = np.where(rng_local.uniform(size=n_future) < dry_prob * 0.95, 0.0, raw_f)
        raw_future[mname] = pd.Series(raw_f, index=future_dates, name=mname)

    log.info("Synthetic data generated: %d models, hist=%d days, future=%d days",
             n_models, n_hist, n_future)
    return obs_hist, raw_hist, raw_future


# ─────────────────────────────────────────────────────────────────────────────
# 4. QUANTILE DELTA MAPPING (QDM)
# ─────────────────────────────────────────────────────────────────────────────

class QDM:
    """
    Quantile Delta Mapping bias correction.

    Preserves the model-simulated relative change (delta) at each quantile
    while correcting the distributional shape to match observations.

    Algorithm (Cannon et al. 2015):
        BC_future(t) = F_obs^{-1}[F_hist(raw_future(t))] × δ(t)

    where δ(t) = raw_future(t) / F_hist^{-1}[F_future(raw_future(t))]
    is the quantile-specific relative change (ratio).

    Parameters
    ----------
    n_quantiles : number of quantile nodes for interpolation
    wet_day_threshold : minimum value treated as a precipitation event (mm)
    """

    def __init__(self, n_quantiles: int = 500, wet_day_threshold: float = 0.1):
        self.n_quantiles       = n_quantiles
        self.wet_threshold     = wet_day_threshold
        self._quantiles        = np.linspace(0, 1, n_quantiles)
        self._obs_quantiles    = None
        self._hist_quantiles   = None
        self._is_fitted        = False

    # ── Private helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _empirical_quantiles(x: np.ndarray, q: np.ndarray) -> np.ndarray:
        """Vectorised percentile computation on wet-day values."""
        return np.quantile(x, q)

    @staticmethod
    def _build_cdf_inverse(data: np.ndarray, n_q: int) -> interp1d:
        """Return an interpolating function F^{-1}(p) from sorted data."""
        sorted_data = np.sort(data)
        probs       = np.linspace(0, 1, len(sorted_data))
        return interp1d(probs, sorted_data,
                        bounds_error=False,
                        fill_value=(sorted_data[0], sorted_data[-1]))

    @staticmethod
    def _build_cdf(data: np.ndarray) -> interp1d:
        """Return an interpolating function F(x) from sorted data."""
        sorted_data = np.sort(data)
        probs       = np.linspace(0, 1, len(sorted_data))
        return interp1d(sorted_data, probs,
                        bounds_error=False,
                        fill_value=(0.0, 1.0))

    # ── Public interface ─────────────────────────────────────────────────────

    def fit(self, obs: np.ndarray, hist_raw: np.ndarray) -> "QDM":
        """
        Calibrate the mapping using the historical period.

        Parameters
        ----------
        obs      : observed precipitation array (mm/day)
        hist_raw : raw model historical precipitation array (mm/day)
        """
        # Work only on wet days to avoid drizzle contamination
        obs_wet  = obs[obs  >= self.wet_threshold]
        hist_wet = hist_raw[hist_raw >= self.wet_threshold]

        # Handle edge-case: insufficient wet days
        if len(obs_wet) < 10 or len(hist_wet) < 10:
            raise ValueError("Insufficient wet-day observations for QDM calibration.")

        self._obs_quantiles  = self._empirical_quantiles(obs_wet,  self._quantiles)
        self._hist_quantiles = self._empirical_quantiles(hist_wet, self._quantiles)

        # Build CDF/CDF-inverse objects
        self._F_obs_inv  = self._build_cdf_inverse(obs_wet,  self.n_quantiles)
        self._F_hist_inv = self._build_cdf_inverse(hist_wet, self.n_quantiles)
        self._F_hist     = self._build_cdf(hist_wet)
        self._is_fitted  = True
        return self

    def transform(self, raw_future: np.ndarray) -> np.ndarray:
        """
        Apply QDM to future raw model output.

        Returns bias-corrected future precipitation (mm/day).
        """
        if not self._is_fitted:
            raise RuntimeError("Call fit() before transform().")

        bc = np.zeros_like(raw_future, dtype=float)
        wet_mask = raw_future >= self.wet_threshold

        if wet_mask.sum() == 0:
            return bc

        x_wet = raw_future[wet_mask]

        # Step 1: compute quantile rank of each future value in historical CDF
        tau_t = np.clip(self._F_hist(x_wet), 0.0, 1.0)

        # Step 2: compute historical quantile at same rank
        x_hist_at_tau = np.clip(self._F_hist_inv(tau_t), 1e-6, None)

        # Step 3: quantile-specific relative delta (ratio)
        delta = x_wet / x_hist_at_tau

        # Step 4: map historical quantile through observed CDF-inverse → bc base
        bc_base = self._F_obs_inv(tau_t)

        # Step 5: apply delta to preserve future signal
        bc_wet  = bc_base * delta
        bc[wet_mask] = np.clip(bc_wet, 0.0, None)

        return bc

    def fit_transform(self, obs, hist_raw, raw_future):
        """Convenience wrapper: fit on historical, transform future."""
        return self.fit(obs, hist_raw).transform(raw_future)

    def validate(self, obs: np.ndarray, hist_raw: np.ndarray) -> dict:
        """
        In-sample validation: apply QDM to historical period and compare
        against observations.  Returns performance metrics dict.
        """
        if not self._is_fitted:
            raise RuntimeError("Call fit() before validate().")
        bc_hist = self.transform(hist_raw)
        return compute_metrics(obs, hist_raw, bc_hist)


# ─────────────────────────────────────────────────────────────────────────────
# 5. PERFORMANCE METRICS
# ─────────────────────────────────────────────────────────────────────────────

def compute_metrics(
    obs: np.ndarray,
    raw: np.ndarray,
    bc: np.ndarray,
    wet_threshold: float = 0.1,
) -> dict:
    """
    Compute standard bias-correction validation metrics.

    Metrics
    -------
    RMSE   : root-mean-square error (mm)
    MAE    : mean absolute error (mm)
    Bias   : mean bias (model − obs, mm)
    rBias  : relative bias (%)
    KS_stat: Kolmogorov–Smirnov statistic (CDF distance)
    KS_p   : KS p-value
    P_wet  : wet-day frequency
    Q95    : 95th-percentile value
    Q99    : 99th-percentile value
    """
    def _wet(arr):
        return arr[arr >= wet_threshold]

    obs_w = _wet(obs)
    raw_w = _wet(raw)
    bc_w  = _wet(bc)

    # Align lengths for paired metrics (daily matching)
    n = min(len(obs), len(raw), len(bc))

    def rmse(a, b):
        return float(np.sqrt(np.mean((a[:n] - b[:n]) ** 2)))

    def mae(a, b):
        return float(np.mean(np.abs(a[:n] - b[:n])))

    def bias(a, b):
        return float(np.mean(b[:n] - a[:n]))

    ks_raw = ks_2samp(obs_w, raw_w)
    ks_bc  = ks_2samp(obs_w, bc_w)

    return {
        "RMSE_raw"    : rmse(obs, raw),
        "RMSE_bc"     : rmse(obs, bc),
        "MAE_raw"     : mae(obs, raw),
        "MAE_bc"      : mae(obs, bc),
        "Bias_raw"    : bias(obs, raw),
        "Bias_bc"     : bias(obs, bc),
        "rBias_raw"   : 100 * bias(obs, raw) / (np.mean(obs[:n]) + 1e-9),
        "rBias_bc"    : 100 * bias(obs, bc)  / (np.mean(obs[:n]) + 1e-9),
        "KS_raw"      : ks_raw.statistic,
        "KS_raw_p"    : ks_raw.pvalue,
        "KS_bc"       : ks_bc.statistic,
        "KS_bc_p"     : ks_bc.pvalue,
        "Pwet_obs"    : float(np.mean(obs >= wet_threshold)),
        "Pwet_raw"    : float(np.mean(raw >= wet_threshold)),
        "Pwet_bc"     : float(np.mean(bc  >= wet_threshold)),
        "Q95_obs"     : float(np.quantile(obs_w, 0.95)),
        "Q95_raw"     : float(np.quantile(raw_w, 0.95)),
        "Q95_bc"      : float(np.quantile(bc_w,  0.95)),
        "Q99_obs"     : float(np.quantile(obs_w, 0.99)),
        "Q99_raw"     : float(np.quantile(raw_w, 0.99)),
        "Q99_bc"      : float(np.quantile(bc_w,  0.99)),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 6. EXTREME PRECIPITATION ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

class ExtremePrecipitationAnalyzer:
    """
    Analyzes extreme precipitation characteristics using:
      - Non-parametric percentile thresholds (P90, P95, P99)
      - Parametric GEV (Generalized Extreme Value) return level estimation
      - Ensemble spread under extreme conditions

    Parameters
    ----------
    return_periods : list of return periods (years) for GEV analysis
    block_size     : block maxima period (default 365 = annual maxima)
    """

    def __init__(
        self,
        return_periods: list[int] = RETURN_PERIODS,
        block_size: int = 365,
    ):
        self.return_periods = return_periods
        self.block_size     = block_size

    # ── Block maxima extraction ──────────────────────────────────────────────

    def block_maxima(self, series: pd.Series) -> np.ndarray:
        """Extract annual (block) maxima from daily precipitation series."""
        return (
            series.resample("YE").max()
                  .dropna()
                  .values
        )

    # ── GEV fitting via L-moments (MLE fallback) ────────────────────────────

    def fit_gev(self, maxima: np.ndarray) -> tuple[float, float, float]:
        """
        Fit GEV distribution to block maxima via Maximum Likelihood Estimation.

        Returns (shape ξ, location μ, scale σ).
        Negative shape (ξ < 0): Weibull type (bounded upper tail)
        Zero shape (ξ ≈ 0):    Gumbel type
        Positive shape (ξ > 0): Fréchet type (heavy upper tail)
        """
        shape, loc, scale = genextreme.fit(maxima, loc=np.median(maxima))
        return float(shape), float(loc), float(scale)

    def return_levels(
        self, shape: float, loc: float, scale: float
    ) -> dict[int, float]:
        """
        Compute GEV return levels for specified return periods.

        RL(T) = μ + σ/ξ × [1 − (−ln(1 − 1/T))^{−ξ}]  for ξ ≠ 0
        RL(T) = μ − σ × ln(−ln(1 − 1/T))               for ξ = 0
        """
        rl = {}
        for T in self.return_periods:
            p = 1.0 - 1.0 / T
            rl[T] = float(genextreme.ppf(p, shape, loc=loc, scale=scale))
        return rl

    def return_level_confidence(
        self,
        maxima: np.ndarray,
        n_boot: int = 500,
        ci: float = 0.90,
    ) -> dict[int, tuple[float, float]]:
        """
        Bootstrap confidence intervals for GEV return levels.

        Returns dict {T: (lower_ci, upper_ci)}.
        """
        rng_b = np.random.default_rng(RANDOM_SEED + 1)
        boot_rl = {T: [] for T in self.return_periods}

        for _ in range(n_boot):
            sample = rng_b.choice(maxima, size=len(maxima), replace=True)
            try:
                sh, lo, sc = self.fit_gev(sample)
                for T in self.return_periods:
                    p  = 1.0 - 1.0 / T
                    rl = float(genextreme.ppf(p, sh, loc=lo, scale=sc))
                    boot_rl[T].append(rl)
            except Exception:
                pass

        alpha = (1.0 - ci) / 2.0
        return {
            T: (float(np.quantile(v, alpha)), float(np.quantile(v, 1 - alpha)))
            for T, v in boot_rl.items() if len(v) > 0
        }

    # ── Ensemble spread under extremes ───────────────────────────────────────

    def ensemble_extreme_spread(
        self,
        obs_series: pd.Series,
        ensemble_dict: dict[str, pd.Series],
        quantile_thresh: float = 0.95,
        n_boot: int = N_BOOTSTRAP,
    ) -> pd.DataFrame:
        """
        Quantify ensemble uncertainty at extreme quantile levels.

        For each ensemble size n (1 → N), compute:
          - Multi-model mean of Q_{quantile_thresh}
          - Standard deviation (ensemble spread)
          - RMSE vs observed quantile

        Returns DataFrame with columns:
            n_models, mean_extreme, std_extreme, rmse_extreme
        """
        obs_q   = float(np.quantile(
            obs_series.values[obs_series.values >= 0.1], quantile_thresh
        ))
        models  = list(ensemble_dict.keys())
        N       = len(models)
        rng_b   = np.random.default_rng(RANDOM_SEED + 2)
        rows    = []

        for n in range(1, N + 1):
            q_vals = []
            for _ in range(n_boot):
                sel = rng_b.choice(models, size=n, replace=False if n <= N else True)
                q_n = np.mean([
                    np.quantile(
                        ensemble_dict[m].values[ensemble_dict[m].values >= 0.1],
                        quantile_thresh
                    )
                    for m in sel
                ])
                q_vals.append(q_n)
            q_arr = np.array(q_vals)
            rows.append({
                "n_models"     : n,
                "mean_extreme" : float(np.mean(q_arr)),
                "std_extreme"  : float(np.std(q_arr)),
                "rmse_extreme" : float(np.sqrt(np.mean((q_arr - obs_q) ** 2))),
                "ci_lower"     : float(np.quantile(q_arr, 0.05)),
                "ci_upper"     : float(np.quantile(q_arr, 0.95)),
                "obs_q"        : obs_q,
            })

        return pd.DataFrame(rows)

    # ── Full extreme summary table ───────────────────────────────────────────

    def summarize(
        self,
        label: str,
        series: pd.Series,
    ) -> dict:
        """Return key extreme statistics for a single precipitation series."""
        vals = series.values[series.values >= 0.1]
        maxima = self.block_maxima(series)

        if len(maxima) < 5:
            log.warning("Fewer than 5 annual maxima for %s; GEV results unreliable.", label)
            return {}

        sh, lo, sc = self.fit_gev(maxima)
        rl_dict    = self.return_levels(sh, lo, sc)

        row = {
            "label"   : label,
            "P90"     : float(np.quantile(vals, 0.90)),
            "P95"     : float(np.quantile(vals, 0.95)),
            "P99"     : float(np.quantile(vals, 0.99)),
            "P_max"   : float(vals.max()),
            "GEV_xi"  : sh,
            "GEV_mu"  : lo,
            "GEV_sigma": sc,
        }
        for T, v in rl_dict.items():
            row[f"RL_{T}yr"] = v

        return row


# ─────────────────────────────────────────────────────────────────────────────
# 7. ENSEMBLE SATURATION ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

class EnsembleSaturationAnalyzer:
    """
    Determines the optimal number of CMIP6 ensemble members via
    bootstrap-based saturation analysis.

    Algorithm:
      For n = 1 → N:
        Repeat n_bootstrap times:
          Randomly draw n models (without replacement when n ≤ N)
          Compute ensemble mean precipitation
          Compute RMSE vs observed, ensemble SD
        Record mean RMSE, SD, 90 % CI

    Saturation detection:
      - ΔRMSE < ε  for STABILITY_W consecutive steps → saturation at n*
      - Alternatively, relative improvement < 1 % of max improvement

    Parameters
    ----------
    n_bootstrap   : bootstrap resampling iterations
    convergence_ε : marginal RMSE improvement threshold (mm)
    stability_w   : window length for stability criterion
    n_jobs        : parallel workers (-1 = all cores)
    """

    def __init__(
        self,
        n_bootstrap:    int   = N_BOOTSTRAP,
        convergence_ε:  float = CONVERGENCE_ε,
        stability_w:    int   = STABILITY_W,
        n_jobs:         int   = -1,
    ):
        self.n_bootstrap   = n_bootstrap
        self.ε             = convergence_ε
        self.stability_w   = stability_w
        self.n_jobs        = n_jobs
        self.results_      = None
        self.saturation_n_ = None

    # ── Single bootstrap step (parallelisable) ──────────────────────────────

    @staticmethod
    def _bootstrap_step(
        models_dict: dict[str, np.ndarray],
        obs_arr:     np.ndarray,
        n:           int,
        n_boot:      int,
        seed:        int,
    ) -> dict:
        """Compute bootstrap statistics for ensemble size n."""
        rng_b  = np.random.default_rng(seed)
        keys   = list(models_dict.keys())
        N      = len(keys)
        rmses  = np.zeros(n_boot)
        sds    = np.zeros(n_boot)

        for b in range(n_boot):
            sel_keys = rng_b.choice(keys, size=n, replace=(n > N))
            ens_arr  = np.stack([models_dict[k] for k in sel_keys], axis=0)
            ens_mean = ens_arr.mean(axis=0)
            n_shared = min(len(obs_arr), len(ens_mean))
            rmses[b] = np.sqrt(np.mean((ens_mean[:n_shared] - obs_arr[:n_shared]) ** 2))
            sds[b]   = ens_arr.std(axis=0).mean()

        return {
            "n_models"  : n,
            "rmse_mean" : float(rmses.mean()),
            "rmse_std"  : float(rmses.std()),
            "sd_mean"   : float(sds.mean()),
            "ci_5"      : float(np.quantile(rmses, 0.05)),
            "ci_95"     : float(np.quantile(rmses, 0.95)),
        }

    # ── Main saturation runner ───────────────────────────────────────────────

    def run(
        self,
        obs:         pd.Series,
        models_dict: dict[str, pd.Series],
        label:       str = "all",
    ) -> pd.DataFrame:
        """
        Run full ensemble saturation analysis.

        Parameters
        ----------
        obs         : observed precipitation series
        models_dict : {model_name: model_series}
        label       : tag for logging

        Returns
        -------
        DataFrame with columns: n_models, rmse_mean, rmse_std, sd_mean, ci_5, ci_95
        """
        obs_arr   = obs.values
        model_arr = {k: v.values for k, v in models_dict.items()}
        N         = len(models_dict)
        log.info("[Saturation] %s — %d models, %d bootstrap draws", label, N, self.n_bootstrap)

        # Parallel bootstrap across ensemble sizes
        results = Parallel(n_jobs=self.n_jobs)(
            delayed(self._bootstrap_step)(
                model_arr, obs_arr, n, self.n_bootstrap, RANDOM_SEED + n
            )
            for n in range(1, N + 1)
        )

        df = pd.DataFrame(results).sort_values("n_models").reset_index(drop=True)
        df["delta_rmse"] = df["rmse_mean"].diff().abs().fillna(np.inf)
        df["improvement_pct"] = (
            (df["rmse_mean"].iloc[0] - df["rmse_mean"]) /
            (df["rmse_mean"].iloc[0] + 1e-9) * 100
        )
        self.results_ = df

        # Detect saturation point
        self.saturation_n_ = self._detect_saturation(df)
        log.info("[Saturation] %s — optimal ensemble size: n* = %d", label, self.saturation_n_)
        return df

    def _detect_saturation(self, df: pd.DataFrame) -> int:
        """
        Two-criterion saturation detection:
          1. Primary  : |ΔRMSE| < ε for `stability_w` consecutive steps
          2. Fallback : relative improvement < 1 % of total improvement

        Returns the first ensemble size satisfying either criterion.
        """
        rmse  = df["rmse_mean"].values
        delta = df["delta_rmse"].values
        N     = len(rmse)

        # Criterion 1: rolling stability
        for i in range(self.stability_w, N):
            window = delta[i - self.stability_w + 1: i + 1]
            if np.all(window < self.ε):
                return int(df["n_models"].iloc[i - self.stability_w + 1])

        # Criterion 2: relative improvement threshold
        total_improvement = rmse[0] - rmse[-1]
        for i in range(1, N):
            if (rmse[i - 1] - rmse[i]) < 0.01 * total_improvement:
                return int(df["n_models"].iloc[i])

        return int(df["n_models"].iloc[-1])


# ─────────────────────────────────────────────────────────────────────────────
# 8. SEASONAL STRATIFICATION UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def season_mask(series: pd.Series, months: list[int]) -> pd.Series:
    """Return subset of series matching specified calendar months."""
    return series[series.index.month.isin(months)]


def stratify_by_season(
    obs: pd.Series,
    models_dict: dict[str, pd.Series],
) -> tuple[dict, dict]:
    """
    Split observed and model series into wet/dry seasons.

    Returns
    -------
    wet_data : {"obs": Series, "models": {name: Series}}
    dry_data : {"obs": Series, "models": {name: Series}}
    """
    wet = {
        "obs"   : season_mask(obs, WET_MONTHS),
        "models": {k: season_mask(v, WET_MONTHS) for k, v in models_dict.items()},
    }
    dry = {
        "obs"   : season_mask(obs, DRY_MONTHS),
        "models": {k: season_mask(v, DRY_MONTHS) for k, v in models_dict.items()},
    }
    return wet, dry


# ─────────────────────────────────────────────────────────────────────────────
# 9. VISUALIZATION MODULE
# ─────────────────────────────────────────────────────────────────────────────

class PublicationFigures:
    """
    Factory for all publication-quality matplotlib figures.
    All figures saved to OUTPUT_DIR/figures/ at DPI resolution.
    """

    @staticmethod
    def _savefig(fig: plt.Figure, name: str) -> Path:
        path = OUTPUT_DIR / "figures" / f"{name}.{FIG_EXT}"
        fig.savefig(path, dpi=DPI, bbox_inches="tight")
        plt.close(fig)
        log.info("Figure saved: %s", path)
        return path

    # ── 9.1 CDF Comparison ──────────────────────────────────────────────────

    @staticmethod
    def cdf_comparison(
        obs: pd.Series,
        raw_dict: dict[str, pd.Series],
        bc_dict:  dict[str, pd.Series],
        title: str = "Empirical CDF Comparison",
        fname: str = "fig01_cdf_comparison",
    ) -> Path:
        """Plot empirical CDFs: Observed vs Raw ensemble vs BC ensemble."""
        fig, ax = plt.subplots(figsize=(7, 5))

        # Pooled wet-day values
        obs_wet = obs.values[obs.values >= 0.1]

        def ecdf(data):
            x = np.sort(data)
            y = np.linspace(0, 1, len(x))
            return x, y

        # Raw ensemble (individual thin lines + mean)
        raw_all = []
        for v in raw_dict.values():
            w = v.values[v.values >= 0.1]
            raw_all.append(np.sort(w))
            x, y = ecdf(w)
            ax.plot(x, y, color=PALETTE["raw"], alpha=0.15, linewidth=0.6)

        # BC ensemble (individual thin lines + mean)
        bc_all = []
        for v in bc_dict.values():
            w = v.values[v.values >= 0.1]
            bc_all.append(np.sort(w))
            x, y = ecdf(w)
            ax.plot(x, y, color=PALETTE["bc"], alpha=0.15, linewidth=0.6)

        # Ensemble means (pooled)
        raw_pool = np.concatenate([v.values[v.values >= 0.1] for v in raw_dict.values()])
        bc_pool  = np.concatenate([v.values[v.values >= 0.1] for v in bc_dict.values()])

        x_raw, y_raw = ecdf(raw_pool)
        x_bc,  y_bc  = ecdf(bc_pool)
        x_obs, y_obs = ecdf(obs_wet)

        ax.plot(x_raw, y_raw, color=PALETTE["raw"],  lw=2,   label="Raw CMIP6 (ensemble mean)")
        ax.plot(x_bc,  y_bc,  color=PALETTE["bc"],   lw=2,   label="QDM-corrected (ensemble mean)")
        ax.plot(x_obs, y_obs, color=PALETTE["obs"],  lw=2.5, label="Observed", zorder=5)

        # Mark 95th and 99th percentile positions
        for q, ls in zip([0.95, 0.99], ["--", ":"]):
            qv = np.quantile(obs_wet, q)
            ax.axvline(qv, color=PALETTE["extreme"], lw=1.0, ls=ls,
                       label=f"P{int(q*100)} obs = {qv:.1f} mm")

        ax.set_xlim(0, np.quantile(obs_wet, 0.999) * 1.05)
        ax.set_xlabel("Daily Precipitation (mm)")
        ax.set_ylabel("Cumulative Probability")
        ax.set_title(title, fontweight="bold")
        ax.legend(frameon=False, loc="lower right", fontsize=8)
        ax.grid(True, alpha=0.25)

        return PublicationFigures._savefig(fig, fname)

    # ── 9.2 Q-Q Plot ────────────────────────────────────────────────────────

    @staticmethod
    def qq_plot(
        obs:     pd.Series,
        raw_dict: dict[str, pd.Series],
        bc_dict:  dict[str, pd.Series],
        title: str = "Q–Q Plot: Model vs Observed",
        fname: str = "fig02_qq_plot",
    ) -> Path:
        """Q-Q plot comparing raw and bias-corrected ensemble against observed."""
        fig, axes = plt.subplots(1, 2, figsize=(10, 5), sharey=False)
        quantiles = np.linspace(0.01, 0.99, 200)

        obs_wet = obs.values[obs.values >= 0.1]
        obs_q   = np.quantile(obs_wet, quantiles)
        maxval  = np.quantile(obs_wet, 0.999)

        for ax, data_dict, color, label_prefix in [
            (axes[0], raw_dict, PALETTE["raw"], "Raw"),
            (axes[1], bc_dict,  PALETTE["bc"],  "QDM-BC"),
        ]:
            for v in data_dict.values():
                w = v.values[v.values >= 0.1]
                mod_q = np.quantile(w, quantiles)
                ax.scatter(obs_q, mod_q, s=3, alpha=0.25, color=color)

            # Pooled ensemble quantiles
            pool = np.concatenate([v.values[v.values >= 0.1] for v in data_dict.values()])
            pool_q = np.quantile(pool, quantiles)
            ax.plot(obs_q, pool_q, color=color, lw=2, label=f"{label_prefix} ensemble")
            ax.plot([0, maxval], [0, maxval], "k--", lw=1, alpha=0.6, label="1:1 line")

            # Annotate extreme tails
            for q_mark in [0.95, 0.99]:
                xv = float(np.quantile(obs_wet, q_mark))
                yv = float(np.quantile(pool, q_mark))
                ax.annotate(
                    f"P{int(q_mark*100)}",
                    xy=(xv, yv), xytext=(xv + 2, yv + 3),
                    fontsize=7, color=PALETTE["extreme"],
                    arrowprops=dict(arrowstyle="->", color=PALETTE["extreme"], lw=0.6),
                )

            ax.set_xlim(0, maxval * 1.05)
            ax.set_ylim(0, maxval * 1.05)
            ax.set_xlabel("Observed Quantiles (mm)")
            ax.set_ylabel("Model Quantiles (mm)")
            ax.set_title(f"{label_prefix} CMIP6", fontweight="bold")
            ax.legend(frameon=False, fontsize=8)
            ax.grid(True, alpha=0.25)

        fig.suptitle(title, fontweight="bold", y=1.01)
        return PublicationFigures._savefig(fig, fname)

    # ── 9.3 Saturation Curve ─────────────────────────────────────────────────

    @staticmethod
    def saturation_curve(
        df_raw:  pd.DataFrame,
        df_bc:   pd.DataFrame,
        sat_n_raw: int,
        sat_n_bc:  int,
        title: str = "Ensemble Saturation Curve",
        fname: str = "fig03_saturation_curve",
    ) -> Path:
        """
        Dual-panel saturation curve showing RMSE vs ensemble size
        for raw (left) and bias-corrected (right) ensembles.
        """
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        for ax, df, color, sat_n, label in [
            (axes[0], df_raw, PALETTE["raw"],  sat_n_raw, "Raw CMIP6"),
            (axes[1], df_bc,  PALETTE["bc"],   sat_n_bc,  "QDM-corrected"),
        ]:
            x = df["n_models"].values
            y = df["rmse_mean"].values
            ci5  = df["ci_5"].values
            ci95 = df["ci_95"].values

            ax.fill_between(x, ci5, ci95, color=color, alpha=0.18,
                            label="90 % bootstrap CI")
            ax.plot(x, y, color=color, lw=2, marker="o", ms=3, label=f"RMSE ({label})")

            # Mark saturation point
            sat_row = df[df["n_models"] == sat_n].iloc[0]
            ax.axvline(sat_n, color=PALETTE["extreme"], lw=1.5, ls="--",
                       label=f"n* = {sat_n}")
            ax.scatter([sat_n], [sat_row["rmse_mean"]],
                       color=PALETTE["extreme"], zorder=6, s=60)
            ax.annotate(
                f"  n* = {sat_n}\n  RMSE = {sat_row['rmse_mean']:.3f}",
                xy=(sat_n, sat_row["rmse_mean"]),
                xytext=(sat_n + 0.5, sat_row["rmse_mean"] * 1.05),
                fontsize=8, color=PALETTE["extreme"],
            )

            ax.set_xlabel("Number of Ensemble Members")
            ax.set_ylabel("RMSE (mm/day)")
            ax.set_title(f"{label}", fontweight="bold")
            ax.legend(frameon=False, fontsize=8)
            ax.grid(True, alpha=0.25)
            ax.set_xlim(0.5, x.max() + 0.5)

        fig.suptitle(title, fontweight="bold", y=1.01)
        return PublicationFigures._savefig(fig, fname)

    # ── 9.4 Ensemble Spread Evolution ────────────────────────────────────────

    @staticmethod
    def ensemble_spread(
        df_raw: pd.DataFrame,
        df_bc:  pd.DataFrame,
        fname: str = "fig04_ensemble_spread",
    ) -> Path:
        """Plot ensemble standard deviation vs ensemble size (uncertainty reduction)."""
        fig, ax = plt.subplots(figsize=(7, 5))

        for df, color, label in [
            (df_raw, PALETTE["raw"], "Raw CMIP6"),
            (df_bc,  PALETTE["bc"],  "QDM-corrected"),
        ]:
            ax.plot(df["n_models"], df["sd_mean"], color=color, lw=2,
                    marker="s", ms=3, label=label)

        ax.set_xlabel("Number of Ensemble Members")
        ax.set_ylabel("Mean Ensemble Spread (SD, mm/day)")
        ax.set_title("Uncertainty Reduction with Ensemble Size", fontweight="bold")
        ax.legend(frameon=False)
        ax.grid(True, alpha=0.25)
        return PublicationFigures._savefig(fig, fname)

    # ── 9.5 Seasonal Saturation Comparison ──────────────────────────────────

    @staticmethod
    def seasonal_saturation(
        df_wet_raw: pd.DataFrame, df_wet_bc: pd.DataFrame,
        df_dry_raw: pd.DataFrame, df_dry_bc: pd.DataFrame,
        sat_nw_raw: int, sat_nw_bc: int,
        sat_nd_raw: int, sat_nd_bc: int,
        fname: str = "fig05_seasonal_saturation",
    ) -> Path:
        """Four-panel seasonal saturation curves."""
        fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=False)
        configs = [
            (axes[0, 0], df_wet_raw, PALETTE["raw"],  sat_nw_raw, "Wet Season – Raw"),
            (axes[0, 1], df_wet_bc,  PALETTE["bc"],   sat_nw_bc,  "Wet Season – QDM-BC"),
            (axes[1, 0], df_dry_raw, PALETTE["raw"],  sat_nd_raw, "Dry Season – Raw"),
            (axes[1, 1], df_dry_bc,  PALETTE["bc"],   sat_nd_bc,  "Dry Season – QDM-BC"),
        ]

        for ax, df, color, sat_n, title in configs:
            x = df["n_models"].values
            ax.fill_between(x, df["ci_5"], df["ci_95"],
                            color=color, alpha=0.18, label="90 % CI")
            ax.plot(x, df["rmse_mean"], color=color, lw=2, marker="o", ms=3)
            ax.axvline(sat_n, color=PALETTE["extreme"], lw=1.5, ls="--",
                       label=f"n* = {sat_n}")
            ax.set_title(title, fontweight="bold")
            ax.set_xlabel("Ensemble Size")
            ax.set_ylabel("RMSE (mm/day)")
            ax.legend(frameon=False, fontsize=8)
            ax.grid(True, alpha=0.25)

        fig.suptitle("Seasonal Ensemble Saturation Analysis", fontweight="bold", y=1.01)
        plt.tight_layout()
        return PublicationFigures._savefig(fig, fname)

    # ── 9.6 Extreme Precipitation – Return Level Plot ────────────────────────

    @staticmethod
    def return_level_plot(
        extreme_analyzer: ExtremePrecipitationAnalyzer,
        obs:     pd.Series,
        raw_pool: pd.Series,
        bc_pool:  pd.Series,
        fname: str = "fig06_return_levels",
    ) -> Path:
        """GEV return level plot with 90 % bootstrap CI."""
        fig, ax = plt.subplots(figsize=(8, 5))
        Ts = RETURN_PERIODS
        log_T = np.log10(Ts)

        for series, color, label in [
            (obs,      PALETTE["obs"],  "Observed"),
            (raw_pool, PALETTE["raw"],  "Raw CMIP6"),
            (bc_pool,  PALETTE["bc"],   "QDM-corrected"),
        ]:
            maxima = extreme_analyzer.block_maxima(series)
            if len(maxima) < 5:
                continue
            sh, lo, sc = extreme_analyzer.fit_gev(maxima)
            rl   = extreme_analyzer.return_levels(sh, lo, sc)
            rl_v = [rl[T] for T in Ts]
            ci   = extreme_analyzer.return_level_confidence(maxima, n_boot=300)

            ax.plot(log_T, rl_v, color=color, lw=2, marker="o", ms=5, label=label)
            lo_v = [ci[T][0] if T in ci else v for T, v in zip(Ts, rl_v)]
            hi_v = [ci[T][1] if T in ci else v for T, v in zip(Ts, rl_v)]
            ax.fill_between(log_T, lo_v, hi_v, color=color, alpha=0.15)

        ax.set_xticks(log_T)
        ax.set_xticklabels([str(T) for T in Ts])
        ax.set_xlabel("Return Period (years)")
        ax.set_ylabel("Return Level (mm/day)")
        ax.set_title("GEV Return Level Estimates (Annual Block Maxima)", fontweight="bold")
        ax.legend(frameon=False)
        ax.grid(True, alpha=0.25)
        return PublicationFigures._savefig(fig, fname)

    # ── 9.7 Extreme Ensemble Saturation Curve ────────────────────────────────

    @staticmethod
    def extreme_saturation_curve(
        df_q95: pd.DataFrame,
        df_q99: pd.DataFrame,
        sat_n_q95: int,
        sat_n_q99: int,
        fname: str = "fig07_extreme_saturation",
    ) -> Path:
        """Saturation curves restricted to extreme-day subsets (P95/P99)."""
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        for ax, df, sat_n, label, color in [
            (axes[0], df_q95, sat_n_q95, "P95 Extreme Days", PALETTE["extreme"]),
            (axes[1], df_q99, sat_n_q99, "P99 Extreme Days", PALETTE["neutral"]),
        ]:
            x = df["n_models"].values
            ax.fill_between(x, df["ci_lower"], df["ci_upper"],
                            color=color, alpha=0.2, label="90 % CI")
            ax.plot(x, df["rmse_extreme"], color=color, lw=2, marker="o", ms=3,
                    label="RMSE (extreme)")
            ax.axvline(sat_n, color=PALETTE["raw"], lw=1.5, ls="--",
                       label=f"n* = {sat_n}")

            # Observed reference line
            obs_q_val = df["obs_q"].iloc[0]
            ax.axhline(0, color="grey", lw=0.8, ls=":")

            ax.set_xlabel("Number of Ensemble Members")
            ax.set_ylabel("RMSE of Extreme Quantile (mm)")
            ax.set_title(label, fontweight="bold")
            ax.legend(frameon=False, fontsize=8)
            ax.grid(True, alpha=0.25)

        fig.suptitle("Ensemble Saturation under Extreme Precipitation Conditions",
                     fontweight="bold", y=1.01)
        return PublicationFigures._savefig(fig, fname)

    # ── 9.8 Bias Correction Performance Dashboard ────────────────────────────

    @staticmethod
    def bc_performance_dashboard(
        metrics_df: pd.DataFrame,
        fname: str = "fig08_bc_performance_dashboard",
    ) -> Path:
        """Bar chart dashboard for key bias correction metrics."""
        fig, axes = plt.subplots(2, 3, figsize=(13, 7))
        metric_pairs = [
            ("RMSE_raw",  "RMSE_bc",  "RMSE (mm/day)"),
            ("MAE_raw",   "MAE_bc",   "MAE (mm/day)"),
            ("Bias_raw",  "Bias_bc",  "Mean Bias (mm/day)"),
            ("KS_raw",    "KS_bc",    "KS Statistic"),
            ("Q95_raw",   "Q95_bc",   "P95 Wet-Day Precip (mm)"),
            ("Q99_raw",   "Q99_bc",   "P99 Wet-Day Precip (mm)"),
        ]
        obs_vals = {
            "RMSE": None, "MAE": None, "Bias": None,
            "KS": None,
            "Q95": float(metrics_df["Q95_obs"].mean()),
            "Q99": float(metrics_df["Q99_obs"].mean()),
        }

        for ax, (raw_col, bc_col, ylabel) in zip(axes.flat, metric_pairs):
            stations = metrics_df["station"].values if "station" in metrics_df else ["STN"]
            x = np.arange(len(stations))
            w = 0.35
            ax.bar(x - w/2, metrics_df[raw_col], w,
                   color=PALETTE["raw"], alpha=0.8, label="Raw")
            ax.bar(x + w/2, metrics_df[bc_col],  w,
                   color=PALETTE["bc"],  alpha=0.8, label="QDM-BC")

            # Reference line for Q95/Q99
            key = ylabel.split()[0]
            if key in obs_vals and obs_vals[key] is not None:
                ax.axhline(obs_vals[key], color=PALETTE["obs"], lw=1.5,
                           ls="--", label="Observed")

            ax.set_xticks(x)
            ax.set_xticklabels(stations, fontsize=8)
            ax.set_ylabel(ylabel)
            ax.legend(frameon=False, fontsize=7)
            ax.grid(True, alpha=0.2, axis="y")

        fig.suptitle("Bias Correction Performance — Before vs After QDM",
                     fontweight="bold", y=1.01)
        plt.tight_layout()
        return PublicationFigures._savefig(fig, fname)


# ─────────────────────────────────────────────────────────────────────────────
# 10. MAIN PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline(
    obs_hist:   pd.Series,
    raw_hist:   dict[str, pd.Series],
    raw_future: dict[str, pd.Series],
    station_id: str = "STN_PKK",
) -> dict:
    """
    Full bias correction + ensemble saturation + extreme analysis pipeline.

    Parameters
    ----------
    obs_hist   : observed daily precipitation (historical period)
    raw_hist   : {model: raw historical series}
    raw_future : {model: raw future series}
    station_id : station identifier for labelling

    Returns
    -------
    results : dict of key outputs for downstream use or reporting
    """

    t0 = time.time()
    log.info("═" * 65)
    log.info("  ENSEMBLE SATURATION FRAMEWORK  —  Station: %s", station_id)
    log.info("═" * 65)

    # ── Step 1: QDM Bias Correction ─────────────────────────────────────────
    log.info("[1/7] Applying QDM bias correction …")
    qdm_models = {}
    bc_future  = {}
    bc_hist_val= {}

    for mname, hist_raw_s in raw_hist.items():
        qdm = QDM(n_quantiles=500)
        # Align time indices before fitting
        common_idx = obs_hist.index.intersection(hist_raw_s.index)
        obs_arr    = obs_hist.loc[common_idx].values
        hist_arr   = hist_raw_s.loc[common_idx].values

        qdm.fit(obs_arr, hist_arr)
        qdm_models[mname]  = qdm
        bc_future[mname]   = pd.Series(
            qdm.transform(raw_future[mname].values),
            index=raw_future[mname].index,
            name=mname,
        )
        bc_hist_val[mname] = pd.Series(
            qdm.transform(hist_arr),
            index=common_idx,
            name=mname,
        )

    log.info("    QDM applied to %d models.", len(qdm_models))

    # ── Step 2: Bias Correction Validation Metrics ──────────────────────────
    log.info("[2/7] Computing validation metrics …")
    metric_rows = []
    for mname in raw_hist:
        common_idx = obs_hist.index.intersection(raw_hist[mname].index)
        m = compute_metrics(
            obs_hist.loc[common_idx].values,
            raw_hist[mname].loc[common_idx].values,
            bc_hist_val[mname].loc[common_idx].values,
        )
        m["station"] = station_id
        m["model"]   = mname
        metric_rows.append(m)

    metrics_df = pd.DataFrame(metric_rows)
    metrics_path = OUTPUT_DIR / "tables" / "table01_bc_metrics.csv"
    metrics_df.to_csv(metrics_path, index=False, float_format="%.4f")
    log.info("    Metrics table saved: %s", metrics_path)

    # ── Step 3: Full Ensemble Saturation (all-season) ────────────────────────
    log.info("[3/7] Running ensemble saturation analysis (all-season) …")
    sat_analyzer = EnsembleSaturationAnalyzer()

    df_sat_raw = sat_analyzer.run(obs_hist, raw_hist,   label="raw-all")
    sat_n_raw  = sat_analyzer.saturation_n_

    df_sat_bc  = sat_analyzer.run(obs_hist, bc_hist_val, label="bc-all")
    sat_n_bc   = sat_analyzer.saturation_n_

    # ── Step 4: Seasonal Saturation ──────────────────────────────────────────
    log.info("[4/7] Running seasonal saturation analysis …")
    wet_data, dry_data = stratify_by_season(obs_hist, raw_hist)
    wet_bc, dry_bc     = stratify_by_season(obs_hist, bc_hist_val)

    # Wet season
    df_wet_raw = sat_analyzer.run(wet_data["obs"], wet_data["models"], label="raw-wet")
    sat_nw_raw = sat_analyzer.saturation_n_
    df_wet_bc  = sat_analyzer.run(wet_bc["obs"],  wet_bc["models"],   label="bc-wet")
    sat_nw_bc  = sat_analyzer.saturation_n_

    # Dry season
    df_dry_raw = sat_analyzer.run(dry_data["obs"], dry_data["models"], label="raw-dry")
    sat_nd_raw = sat_analyzer.saturation_n_
    df_dry_bc  = sat_analyzer.run(dry_bc["obs"],  dry_bc["models"],   label="bc-dry")
    sat_nd_bc  = sat_analyzer.saturation_n_

    # ── Step 5: Extreme Precipitation Analysis ───────────────────────────────
    log.info("[5/7] Performing extreme precipitation analysis …")
    epa = ExtremePrecipitationAnalyzer()

    # Pool models for return-level diagnostics
    raw_pool_series = pd.concat(list(raw_hist.values()),    axis=0).dropna()
    bc_pool_series  = pd.concat(list(bc_hist_val.values()), axis=0).dropna()

    extreme_rows = []
    for label, series in [
        ("Observed",       obs_hist),
        ("Raw (pooled)",   raw_pool_series),
        ("QDM-BC (pooled)",bc_pool_series),
    ]:
        row = epa.summarize(label, series)
        if row:
            extreme_rows.append(row)

    extreme_df = pd.DataFrame(extreme_rows)
    extreme_path = OUTPUT_DIR / "tables" / "table02_extreme_metrics.csv"
    extreme_df.to_csv(extreme_path, index=False, float_format="%.3f")
    log.info("    Extreme metrics table saved: %s", extreme_path)

    # ── Step 6: Ensemble Saturation under Extreme Conditions ─────────────────
    log.info("[6/7] Ensemble saturation under extreme conditions (P95/P99) …")

    def detect_extreme_sat_n(df_ext: pd.DataFrame) -> int:
        """Simple elbow detection: first n where ΔRMSE < ε."""
        rmse = df_ext["rmse_extreme"].values
        for i in range(1, len(rmse)):
            if abs(rmse[i] - rmse[i-1]) < CONVERGENCE_ε:
                return int(df_ext["n_models"].iloc[i])
        return int(df_ext["n_models"].iloc[-1])

    df_ext_q95 = epa.ensemble_extreme_spread(
        obs_hist, bc_hist_val, quantile_thresh=0.95, n_boot=500
    )
    df_ext_q99 = epa.ensemble_extreme_spread(
        obs_hist, bc_hist_val, quantile_thresh=0.99, n_boot=500
    )

    sat_n_q95 = detect_extreme_sat_n(df_ext_q95)
    sat_n_q99 = detect_extreme_sat_n(df_ext_q99)

    log.info("    Extreme saturation: P95 n* = %d,  P99 n* = %d",
             sat_n_q95, sat_n_q99)

    # Save saturation summary table
    sat_summary = pd.DataFrame([{
        "station"         : station_id,
        "season"          : s,
        "type"            : t,
        "optimal_n"       : n,
        "final_rmse"      : rmse,
    }
    for s, t, n, rmse in [
        ("All",  "Raw",     sat_n_raw,  df_sat_raw.loc[df_sat_raw.n_models==sat_n_raw, "rmse_mean"].values[0]),
        ("All",  "QDM-BC",  sat_n_bc,   df_sat_bc.loc[df_sat_bc.n_models==sat_n_bc,   "rmse_mean"].values[0]),
        ("Wet",  "Raw",     sat_nw_raw, df_wet_raw.loc[df_wet_raw.n_models==sat_nw_raw,"rmse_mean"].values[0]),
        ("Wet",  "QDM-BC",  sat_nw_bc,  df_wet_bc.loc[df_wet_bc.n_models==sat_nw_bc,  "rmse_mean"].values[0]),
        ("Dry",  "Raw",     sat_nd_raw, df_dry_raw.loc[df_dry_raw.n_models==sat_nd_raw,"rmse_mean"].values[0]),
        ("Dry",  "QDM-BC",  sat_nd_bc,  df_dry_bc.loc[df_dry_bc.n_models==sat_nd_bc,  "rmse_mean"].values[0]),
        ("P95",  "QDM-BC",  sat_n_q95,  df_ext_q95.loc[df_ext_q95.n_models==sat_n_q95,"rmse_extreme"].values[0]),
        ("P99",  "QDM-BC",  sat_n_q99,  df_ext_q99.loc[df_ext_q99.n_models==sat_n_q99,"rmse_extreme"].values[0]),
    ]])
    sat_summary.to_csv(OUTPUT_DIR / "tables" / "table03_saturation_summary.csv",
                       index=False, float_format="%.4f")

    # ── Step 7: Generate All Figures ─────────────────────────────────────────
    log.info("[7/7] Generating publication figures …")
    figs = PublicationFigures()

    figs.cdf_comparison(obs_hist, raw_hist, bc_hist_val)
    figs.qq_plot(obs_hist, raw_hist, bc_hist_val)
    figs.saturation_curve(df_sat_raw, df_sat_bc, sat_n_raw, sat_n_bc)
    figs.ensemble_spread(df_sat_raw, df_sat_bc)
    figs.seasonal_saturation(
        df_wet_raw, df_wet_bc, df_dry_raw, df_dry_bc,
        sat_nw_raw, sat_nw_bc, sat_nd_raw, sat_nd_bc,
    )
    figs.return_level_plot(epa, obs_hist, raw_pool_series, bc_pool_series)
    figs.extreme_saturation_curve(df_ext_q95, df_ext_q99, sat_n_q95, sat_n_q99)
    figs.bc_performance_dashboard(metrics_df)

    elapsed = time.time() - t0
    log.info("═" * 65)
    log.info("  Pipeline complete in %.1f s", elapsed)
    log.info("  Outputs → %s", OUTPUT_DIR.resolve())
    log.info("═" * 65)

    return {
        "metrics_df"   : metrics_df,
        "extreme_df"   : extreme_df,
        "sat_summary"  : sat_summary,
        "sat_n_raw"    : sat_n_raw,
        "sat_n_bc"     : sat_n_bc,
        "sat_n_q95"    : sat_n_q95,
        "sat_n_q99"    : sat_n_q99,
        "bc_future"    : bc_future,
        "df_sat_raw"   : df_sat_raw,
        "df_sat_bc"    : df_sat_bc,
        "df_ext_q95"   : df_ext_q95,
        "df_ext_q99"   : df_ext_q99,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 11. ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    # ── Generate (or load) data ──────────────────────────────────────────────
    #
    # To use real data, replace generate_synthetic_data() with your own
    # CSV/NetCDF loader that returns identically-typed objects:
    #   obs_hist   → pd.Series with DatetimeIndex, values in mm/day
    #   raw_hist   → dict {model_name: pd.Series}
    #   raw_future → dict {model_name: pd.Series}
    #
    obs_hist, raw_hist, raw_future = generate_synthetic_data(
        n_models     = 10,
        hist_years   = 30,
        future_years = 30,
        station_id   = "STN_PKK",
    )

    # ── Run full pipeline ────────────────────────────────────────────────────
    results = run_pipeline(
        obs_hist   = obs_hist,
        raw_hist   = raw_hist,
        raw_future = raw_future,
        station_id = "STN_PKK",
    )

    # ── Print summary to console ─────────────────────────────────────────────
    print("\n" + "═" * 55)
    print("  SATURATION SUMMARY")
    print("═" * 55)
    print(results["sat_summary"].to_string(index=False))
    print("\n  EXTREME METRICS")
    print("─" * 55)
    ext = results["extreme_df"][["label", "P95", "P99",
                                  "RL_10yr", "RL_50yr", "RL_100yr"]]
    print(ext.to_string(index=False))
    print("═" * 55)
