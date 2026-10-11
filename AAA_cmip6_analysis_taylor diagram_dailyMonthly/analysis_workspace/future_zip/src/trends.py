# -*- coding: utf-8 -*-
"""
src/trends.py — Trend-test suite.

Carries forward all v2.1 methodological corrections (see
CHANGELOG_v2.0_to_v2.1.md):
  - MMK (Hamed & Rao, 1998) always runs on the RAW series (never on data
    already passed through TFPW — that double-corrects for autocorrelation).
  - Pettitt (1979) always runs on the RAW series (via `pyhomogeneity`, since
    `pymannkendall` has no Pettitt implementation at all).
  - All three trend tests (MK, TFPW-MK, MMK-HR) are always computed and
    reported together; the PRIMARY test is chosen by a pre-registered,
    transparent rule (TFPW-MK if lag-1 autocorrelation is significant,
    else Original MK).
  - Percent-change-per-decade is guarded against near-zero seasonal medians.
  - FDR and bootstrap field significance are run PER SEASON FAMILY, not pooled.

LIMITATION (stated, not hidden): TFPW here is the original Yue & Wang (2002)
formulation, not variance-corrected VCTFPW (Wang & Swail, 2001; Collaud Coen
et al., 2020). TFPW-MK is a conservative cross-check, not a stand-alone
variance-corrected estimate.
"""

import numpy as np
from scipy.stats import theilslopes, norm, median_abs_deviation, percentileofscore
from statsmodels.tsa.stattools import acf
import pymannkendall as mk
import pyhomogeneity as hg

import config


# =============================================================================
# CORE ESTIMATORS
# =============================================================================

def theil_sen(x, y):
    slope, intercept, lo, hi = theilslopes(y, x, alpha=0.05)
    return slope, intercept, lo, hi


def detrend_series(x, y, slope, intercept):
    return y - (slope * x + intercept)


def lag1_autocorr(y):
    return acf(y, nlags=1, fft=False)[1]


def autocorr_significant(r1, n, alpha=0.05):
    critical = norm.ppf(1 - alpha / 2) / np.sqrt(n)
    return abs(r1) > critical, critical


def tfpw(y, x):
    """Trend-Free Pre-Whitening (Yue & Wang, 2002). See module limitation note."""
    slope, intercept, _, _ = theil_sen(x, y)
    trend = slope * x + intercept
    detrended = y - trend

    r1 = lag1_autocorr(detrended)

    pw = np.copy(detrended)
    for i in range(1, len(detrended)):
        pw[i] = detrended[i] - r1 * detrended[i - 1]

    return pw + trend, r1


def pettitt_test(x_years, y_values):
    """
    Pettitt (1979) change-point test, via pyhomogeneity (pymannkendall has
    NO Pettitt implementation — see CHANGELOG_v2.0_to_v2.1.md item 1).

    CRITICAL FIX (v2.6 -> v2.7, reproducibility): pyhomogeneity's default
    `sim=20000` computes the p-value by MONTE CARLO SIMULATION, which is
    stochastic — re-running the identical input gives a DIFFERENT p-value
    each time (verified: 5 runs of the same synthetic series gave p in
    [0.421, 0.431], not a single repeatable value). This directly violates
    the mandatory reproducibility/auditability requirement (identical input
    must give identical output). `sim=0` uses Pettitt's own (1979)
    closed-form asymptotic approximation, p = 2*exp(-6*U^2/(n^3+n^2)),
    which is fully deterministic (verified: 5 runs of the same input give
    the exact same p-value to full float precision).

    SECOND BUG FOUND WHILE VERIFYING THE FIRST FIX: this asymptotic formula
    is only a valid approximation when the change-point signal (U) is
    reasonably large relative to n. For a weak/absent signal (U near 0) the
    raw formula EXCEEDS 1 (verified: U=0, n=34 -> raw p=2.0; U=10, n=34 ->
    raw p=1.97) — mathematically impossible for a probability, and
    confirmed present in real output (12 of 36 station-season rows showed
    p>1 before this fix). `pyhomogeneity` does not clip this itself. Fixed
    by capping at the valid upper bound: p = min(1.0, raw_p).
    """
    _, cp_idx, raw_p, _, _ = hg.pettitt_test(y_values, alpha=config.ALPHA, sim=0)
    p = min(1.0, float(raw_p))
    cp_year = int(x_years[cp_idx]) if cp_idx is not None and 0 <= cp_idx < len(x_years) else None
    return p, cp_year


def mk_test(y):
    return mk.original_test(y)


def mmk_test(y):
    """
    Hamed & Rao (1998) — must be applied to the RAW series.

    KNOWN STATISTICAL PITFALL (found in this project's real data, station
    500202, Annual/Wet series): the Hamed-Rao effective-sample-size variance
    correction can produce a NEGATIVE corrected variance (`var_s < 0`) when
    the series has a short record combined with a specific pattern of
    predominantly negative lag-k autocorrelations. This is a known,
    documented edge case of the method (not a bug in this code, not a data
    error) — `np.sqrt(negative)` then yields NaN for both z and p. Downstream
    code must treat `p_MMK_HR = NaN` as "this cross-check is not usable for
    this series" and must NOT silently coerce NaN into "not significant"
    (NaN < alpha evaluates to False in numpy/pandas, which would misreport
    an invalid test as a negative finding).
    """
    return mk.hamed_rao_modification_test(y)


def fdr_bh(pvals, alpha=0.05):
    pvals = np.array(pvals)
    n = len(pvals)
    if n == 0:
        return np.array([], dtype=bool)

    idx = np.argsort(pvals)
    sorted_p = pvals[idx]
    thresh = alpha * np.arange(1, n + 1) / n
    passed = sorted_p <= thresh

    if not np.any(passed):
        return np.zeros(n, dtype=bool)

    k = np.max(np.where(passed))
    cutoff = sorted_p[k]
    return pvals <= cutoff


def bootstrap_field_significance(pvals, alpha=0.05, n_bootstrap=2000, rng=None):
    """
    Monte Carlo field significance under an independence-across-tests null.
    LIMITATION: does not model inter-gauge spatial cross-correlation.
    """
    if rng is None:
        rng = np.random.default_rng()

    pvals = np.asarray(pvals)
    n = len(pvals)
    if n == 0:
        return 0, np.nan

    observed = np.sum(pvals < alpha)

    simulated = np.empty(n_bootstrap)
    for b in range(n_bootstrap):
        rand_p = rng.uniform(0, 1, n)
        simulated[b] = np.sum(rand_p < alpha)

    p_field = 1 - (percentileofscore(simulated, observed) / 100)
    return observed, p_field


def percent_change_per_decade(slope, values):
    med = np.nanmedian(values)
    if np.isnan(med) or abs(med) < config.NEAR_ZERO_BASELINE_MM:
        return np.nan
    return (slope * 10 / med) * 100


def classify_trend_magnitude(pct):
    if pct is None or (isinstance(pct, float) and np.isnan(pct)):
        return "N/A (near-zero baseline)"
    apct = abs(pct)
    if apct < 5:
        return "Small"
    elif apct < 15:
        return "Moderate"
    else:
        return "Large"


def analyze_series(years, values):
    """
    Run the full corrected trend-test suite on one station-season series.
    Returns a dict of all results needed for the per-station table and figures.
    """
    slope, intercept, lo, hi = theil_sen(years, values)

    if config.USE_TFPW:
        values_pw, r1 = tfpw(values, years)
    else:
        detrended = detrend_series(years, values, slope, intercept)
        r1 = lag1_autocorr(detrended)
        values_pw = values

    ac_sig, critical = autocorr_significant(r1, len(values), alpha=config.ALPHA)

    mk_res = mk_test(values)             # original MK, RAW
    tfpwmk_res = mk_test(values_pw)      # TFPW-MK, PREWHITENED
    mmk_res = mmk_test(values)           # Hamed-Rao MMK, RAW

    mmk_valid = not (np.isnan(mmk_res.p) or mmk_res.var_s <= 0)

    if ac_sig:
        primary_res = tfpwmk_res
        primary_method = "TFPW-MK"
    else:
        primary_res = mk_res
        primary_method = "Original MK"

    # NOTE: NaN comparisons (`NaN < alpha`) evaluate to False in numpy/pandas,
    # which would silently misreport an invalid MMK-HR test as "not
    # significant". We explicitly exclude an invalid MMK-HR result from the
    # agreement comparison instead, and flag it as "MMK-HR invalid" rather
    # than folding it into "Agree".
    sig_flags = {
        "MK": mk_res.p < config.ALPHA,
        "TFPW-MK": tfpwmk_res.p < config.ALPHA,
    }
    if mmk_valid:
        sig_flags["MMK-HR"] = mmk_res.p < config.ALPHA

    if all(sig_flags.values()) or not any(sig_flags.values()):
        agreement_flag = "Agree"
    else:
        agreement_flag = "Disagree (" + ", ".join(k for k, v in sig_flags.items() if v) + " significant)"

    if not mmk_valid:
        agreement_flag += " [MMK-HR invalid: negative Hamed-Rao variance correction, known method edge case]"

    p_pettitt, cp_year = pettitt_test(years, values)
    abrupt_change = "Yes" if p_pettitt < config.ALPHA else "No"

    pct_decade = percent_change_per_decade(slope, values)
    magnitude = classify_trend_magnitude(pct_decade)

    interpretation = "Stable"
    if primary_res.p < config.ALPHA:
        if slope > 0:
            interpretation = "Increasing"
        elif slope < 0:
            interpretation = "Decreasing"

    return {
        "slope": slope, "intercept": intercept, "lo": lo, "hi": hi,
        "values_pw": values_pw, "r1": r1, "ac_sig": ac_sig, "ac_critical": critical,
        "mk_res": mk_res, "tfpwmk_res": tfpwmk_res, "mmk_res": mmk_res, "mmk_valid": mmk_valid,
        "primary_res": primary_res, "primary_method": primary_method,
        "agreement_flag": agreement_flag,
        "p_pettitt": p_pettitt, "cp_year": cp_year, "abrupt_change": abrupt_change,
        "pct_decade": pct_decade, "magnitude": magnitude,
        "interpretation": interpretation,
        "median_rain": np.nanmedian(values), "mad": median_abs_deviation(values),
    }
