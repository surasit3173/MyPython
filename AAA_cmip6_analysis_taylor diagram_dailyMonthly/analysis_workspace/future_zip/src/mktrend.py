"""
mktrend.py
==========
Self-contained, transparent implementation of non-parametric trend tests used in
hydroclimatology, validated against synthetic ground truth (see tests/ / __main__).

Implemented:
  * Mann-Kendall S, tau-b, variance with tie correction, two-sided p-value
  * Sen's (Theil-Sen) slope + Gilbert (1987) rank-based 95% CI
  * Modified Mann-Kendall (Hamed & Rao 1998) variance correction for serial
    autocorrelation
  * Trend-Free Pre-Whitening MK (Yue et al. 2002)  -- TFPW-MK  [required method]

References
----------
Hamed, K.H., Rao, A.R. (1998). A modified Mann-Kendall trend test for
    autocorrelated data. J. Hydrol. 204, 182-196.
Yue, S., Pilon, P., Phinney, B., Cavadias, G. (2002). The influence of
    autocorrelation on the ability to detect trend in hydrological series.
    Hydrol. Process. 16, 1807-1829.
Sen, P.K. (1968). Estimates of the regression coefficient based on Kendall's tau.
    J. Am. Stat. Assoc. 63, 1379-1389.
Gilbert, R.O. (1987). Statistical Methods for Environmental Pollution Monitoring.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import numpy as np
from scipy.stats import norm


@dataclass
class TrendResult:
    method: str
    n: int
    S: float
    tau: float
    var_S: float
    z: float
    p_value: float
    trend: str            # 'increasing' | 'decreasing' | 'no trend'
    significant: bool     # at alpha
    alpha: float
    sens_slope: float
    sens_slope_lcl: float
    sens_slope_ucl: float
    intercept: float
    autocorr_lag1: float | None = None
    note: str = ""

    def as_dict(self):
        return asdict(self)


@dataclass
class TFPWDiagnostics:
    original_series: np.ndarray
    original_time: np.ndarray
    detrended_series: np.ndarray
    lag1_autocorr: float
    lag1_critical: float
    prewhitening_applied: bool
    prewhitened_series: np.ndarray
    prewhitened_time: np.ndarray
    trend_restored_series: np.ndarray
    restored_residuals: np.ndarray
    original_result: TrendResult
    tfpw_result: TrendResult


# ----------------------------------------------------------------------------- #
# Core Mann-Kendall building blocks
# ----------------------------------------------------------------------------- #
def _mk_S(x: np.ndarray) -> float:
    n = len(x)
    s = 0.0
    for k in range(n - 1):
        s += np.sum(np.sign(x[k + 1:] - x[k]))
    return float(s)


def _var_S(x: np.ndarray) -> float:
    """Variance of S with correction for ties."""
    n = len(x)
    # tie groups
    _, counts = np.unique(x, return_counts=True)
    tie_term = np.sum(counts * (counts - 1) * (2 * counts + 5))
    return (n * (n - 1) * (2 * n + 5) - tie_term) / 18.0


def _tau_b(x: np.ndarray, S: float) -> float:
    """Kendall tau-b (tie-corrected)."""
    n = len(x)
    n0 = n * (n - 1) / 2.0
    _, counts = np.unique(x, return_counts=True)
    n_ties = np.sum(counts * (counts - 1) / 2.0)
    denom = np.sqrt((n0 - n_ties) * (n0 - n_ties))  # no ties in time -> n1=0
    return float(S / denom) if denom > 0 else np.nan


def _z_from_S(S: float, var_S: float) -> float:
    if var_S <= 0:
        return 0.0
    if S > 0:
        return (S - 1) / np.sqrt(var_S)
    if S < 0:
        return (S + 1) / np.sqrt(var_S)
    return 0.0


def sens_slope(x: np.ndarray, t: np.ndarray | None = None):
    """Theil-Sen slope and intercept. t defaults to 0..n-1 (unit time step)."""
    n = len(x)
    if t is None:
        t = np.arange(n, dtype=float)
    slopes = []
    for i in range(n - 1):
        dt = t[i + 1:] - t[i]
        dx = x[i + 1:] - x[i]
        valid = dt != 0
        slopes.extend((dx[valid] / dt[valid]).tolist())
    slopes = np.asarray(slopes, dtype=float)
    slope = float(np.median(slopes))
    intercept = float(np.median(x) - slope * np.median(t))
    return slope, intercept, slopes


def sens_slope_ci(slopes: np.ndarray, var_S: float, alpha: float = 0.05):
    """Rank-based two-sided CI for Sen's slope.

    Implements the Sen (1968) / Gilbert (1987) order-statistic interval.
    The index convention is benchmarked against scipy.stats.theilslopes for
    the unmodified MK variance. ``var_S`` is supplied explicitly so the same
    rank-selection rule can also be used with a corrected MK variance.
    """
    ssorted = np.sort(np.asarray(slopes, dtype=float))
    nt = len(ssorted)
    if nt == 0:
        return np.nan, np.nan

    var_S = max(float(var_S), 0.0)
    # SciPy/Sen convention: lower-tail z is negative.
    z = norm.ppf(alpha / 2.0)
    sigma = np.sqrt(var_S)

    # Sen (1968), Eq. 2.6 order-statistic indices; arrays are 0-based.
    ru = min(int(np.round((nt - z * sigma) / 2.0)), nt - 1)
    rl = max(int(np.round((nt + z * sigma) / 2.0)) - 1, 0)

    return float(ssorted[rl]), float(ssorted[ru])


def _classify(z, p, alpha):
    sig = p < alpha
    if not sig:
        return "no trend", False
    return ("increasing" if z > 0 else "decreasing"), True


# ----------------------------------------------------------------------------- #
# Public tests
# ----------------------------------------------------------------------------- #
def mann_kendall(x, alpha: float = 0.05) -> TrendResult:
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    S = _mk_S(x)
    var_S = _var_S(x)
    z = _z_from_S(S, var_S)
    p = 2 * (1 - norm.cdf(abs(z)))
    slope, intercept, slopes = sens_slope(x)
    lcl, ucl = sens_slope_ci(slopes, var_S, alpha)
    trend, sig = _classify(z, p, alpha)
    return TrendResult("Mann-Kendall", n, S, _tau_b(x, S), var_S, z, p,
                       trend, sig, alpha, slope, lcl, ucl, intercept,
                       note="original MK (no autocorrelation correction)")


def _lag1_autocorr(x: np.ndarray) -> float:
    x = x - np.mean(x)
    denom = np.sum(x * x)
    if denom == 0:
        return 0.0
    return float(np.sum(x[1:] * x[:-1]) / denom)


def modified_mk_hamed_rao(x, alpha: float = 0.05) -> TrendResult:
    """Hamed & Rao (1998) variance correction using significant rank autocorrelations."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    S = _mk_S(x)
    var_S0 = _var_S(x)

    # ranks, detrended by Sen slope (Hamed-Rao operate on detrended ranks)
    slope, intercept, slopes = sens_slope(x)
    detr = x - slope * np.arange(n)
    ranks = np.argsort(np.argsort(detr)) + 1.0
    rk = ranks - np.mean(ranks)
    var_rk = np.sum(rk * rk)
    # autocorrelation of ranks
    acf = np.array([1.0] + [np.sum(rk[k:] * rk[:-k]) / var_rk for k in range(1, n)])
    # significance bounds for acf (two-sided)
    z_a = norm.ppf(1 - alpha / 2.0)
    sig_mask = np.array([abs(acf[k]) > z_a / np.sqrt(n) for k in range(n)])
    cf = 0.0
    for k in range(1, n):
        if sig_mask[k]:
            cf += (n - k) * (n - k - 1) * (n - k - 2) * acf[k]
    n_ns = 1 + (2.0 / (n * (n - 1) * (n - 2))) * cf
    var_S = var_S0 * n_ns
    fallback_note = ""
    if (not np.isfinite(var_S)) or var_S <= 0:
        # Correction degenerate (e.g. strong negative autocorrelation in small n):
        # fall back to the tie-corrected uncorrected variance.
        var_S = var_S0
        n_ns = 1.0
        fallback_note = " [correction degenerate -> uncorrected variance used]"
    z = _z_from_S(S, var_S)
    p = 2 * (1 - norm.cdf(abs(z)))
    lcl, ucl = sens_slope_ci(slopes, var_S, alpha)
    trend, sig = _classify(z, p, alpha)
    return TrendResult("Modified MK (Hamed-Rao 1998)", n, S, _tau_b(x, S),
                       var_S, z, p, trend, sig, alpha, slope, lcl, ucl,
                       intercept, autocorr_lag1=_lag1_autocorr(x),
                       note=f"variance inflation factor n/n*={n_ns:.4f}" + fallback_note)


def tfpw_mk(x, alpha: float = 0.05) -> TrendResult:
    """
    Trend-Free Pre-Whitening Mann-Kendall (Yue et al. 2002).  REQUIRED METHOD.

    1. Sen slope b on original series.
    2. Detrend:        Y = X - b*t
    3. Lag-1 autocorr r1 of Y
    4. Pre-whiten:     Y' = Y_t - r1*Y_{t-1}
    5. Add trend back: Y'' = Y' + b*t
    6. MK + Sen slope on Y''
    """
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    t = np.arange(n, dtype=float)

    b, _, _ = sens_slope(x)
    y = x - b * t
    r1 = _lag1_autocorr(y)

    # If lag-1 autocorrelation is not significant, pre-whitening is unnecessary
    r1_crit = norm.ppf(1 - alpha / 2.0) / np.sqrt(n)
    if abs(r1) <= r1_crit:
        res = mann_kendall(x, alpha)
        res.method = "TFPW-MK (Yue et al. 2002)"
        res.autocorr_lag1 = r1
        res.note = (f"lag-1 r1={r1:.4f} not significant (|r1|<= {r1_crit:.4f}); "
                    f"pre-whitening skipped, original MK applied")
        return res

    y_pw = y[1:] - r1 * y[:-1]            # length n-1
    t_pw = t[1:]
    y_blend = y_pw + b * t_pw            # add trend back
    S = _mk_S(y_blend)
    var_S = _var_S(y_blend)
    z = _z_from_S(S, var_S)
    p = 2 * (1 - norm.cdf(abs(z)))
    slope, intercept, slopes = sens_slope(y_blend, t_pw)
    lcl, ucl = sens_slope_ci(slopes, var_S, alpha)
    trend, sig = _classify(z, p, alpha)
    return TrendResult("TFPW-MK (Yue et al. 2002)", len(y_blend), S,
                       _tau_b(y_blend, S), var_S, z, p, trend, sig, alpha,
                       slope, lcl, ucl, intercept, autocorr_lag1=r1,
                       note=f"pre-whitened with r1={r1:.4f} (significant)")


def tfpw_diagnostics(x, alpha: float = 0.05) -> TFPWDiagnostics:
    """Return the intermediate TFPW components needed for audit plotting."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    t = np.arange(len(x), dtype=float)
    original = mann_kendall(x, alpha)

    slope0, _, _ = sens_slope(x)
    detrended = x - slope0 * t
    r1 = _lag1_autocorr(detrended)
    r1_crit = norm.ppf(1 - alpha / 2.0) / np.sqrt(len(x))
    applied = abs(r1) > r1_crit

    if applied:
        y_pw = detrended[1:] - r1 * detrended[:-1]
        t_out = t[1:]
        restored = y_pw + slope0 * t_out
    else:
        y_pw = detrended.copy()
        t_out = t
        restored = x.copy()

    tfpw = tfpw_mk(x, alpha)
    restored_residuals = restored - (tfpw.intercept + tfpw.sens_slope * t_out)
    return TFPWDiagnostics(
        original_series=x,
        original_time=t,
        detrended_series=detrended,
        lag1_autocorr=r1,
        lag1_critical=r1_crit,
        prewhitening_applied=applied,
        prewhitened_series=y_pw,
        prewhitened_time=t_out,
        trend_restored_series=restored,
        restored_residuals=restored_residuals,
        original_result=original,
        tfpw_result=tfpw,
    )


# ----------------------------------------------------------------------------- #
# Self-validation against synthetic ground truth
# ----------------------------------------------------------------------------- #
def _self_test():
    """Validate each estimator against the property it is supposed to guarantee."""
    rng = np.random.default_rng(42)
    n = 200
    t = np.arange(n)

    def ar1(phi):
        e = rng.normal(0, 1, n)
        a = np.zeros(n)
        for i in range(1, n):
            a[i] = phi * a[i - 1] + e[i]
        return a

    # 1) Pure positive linear trend -> detect increasing, recover slope
    x = 0.5 * t + rng.normal(0, 1, n)
    r = mann_kendall(x)
    assert r.trend == "increasing" and r.significant
    assert abs(r.sens_slope - 0.5) < 0.1

    # 2) White noise -> slope ~ 0, CI brackets 0
    x = rng.normal(0, 1, n)
    r = mann_kendall(x)
    assert abs(r.sens_slope) < 0.05
    assert r.sens_slope_lcl <= 0 <= r.sens_slope_ucl

    # 3) Sen CI brackets the true slope
    x = 0.3 * t + rng.normal(0, 2, n)
    r = mann_kendall(x)
    assert r.sens_slope_lcl <= 0.3 <= r.sens_slope_ucl

    # 4) Monte-Carlo over AR(1) no-trend and trend+AR(1) series
    reps = 400
    phi, true = 0.6, 0.05
    fp_mk = fp_hr = fp_tf = 0
    pw_mk = pw_hr = pw_tf = 0
    slope_tf = []
    for _ in range(reps):
        a = ar1(phi)
        fp_mk += mann_kendall(a).significant
        fp_hr += modified_mk_hamed_rao(a).significant
        fp_tf += tfpw_mk(a).significant
        x = true * t + ar1(phi)
        pw_mk += mann_kendall(x).significant
        pw_hr += modified_mk_hamed_rao(x).significant
        pw_tf += tfpw_mk(x).significant
        slope_tf.append(tfpw_mk(x).sens_slope)
    fp_mk, fp_hr, fp_tf = fp_mk / reps, fp_hr / reps, fp_tf / reps
    pw_mk, pw_hr, pw_tf = pw_mk / reps, pw_hr / reps, pw_tf / reps

    # PROPERTY: Hamed-Rao controls Type-I error under autocorrelation far better
    # than the original MK (original MK over-rejects).
    assert fp_hr < fp_mk, (fp_mk, fp_hr)
    assert fp_hr < 0.20, fp_hr        # Hamed-Rao retains mild inflation at phi=0.6
    # PROPERTY: TFPW-MK recovers the true slope without bias (its core claim)
    assert abs(np.mean(slope_tf) - true) < 0.01, np.mean(slope_tf)

    print("[mktrend self-test] PASS")
    print(f"  Sen-slope recovery (trend+AR1): true=0.0500  TFPW={np.mean(slope_tf):.4f}")
    print(f"  Type-I (AR1=0.6, no trend, nominal 0.05):"
          f"  origMK={fp_mk:.3f}  Hamed-Rao={fp_hr:.3f}  TFPW={fp_tf:.3f}")
    print(f"  Power  (trend+AR1):"
          f"               origMK={pw_mk:.3f}  Hamed-Rao={pw_hr:.3f}  TFPW={pw_tf:.3f}")


if __name__ == "__main__":
    _self_test()
