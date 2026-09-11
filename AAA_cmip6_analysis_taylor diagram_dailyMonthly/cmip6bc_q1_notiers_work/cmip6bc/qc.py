"""
qc.py — station quality control and season derivation.

Two things are kept separate on purpose:

  Quality control   completeness and homogeneity, applied as a pass/fail
                    gate before the analysis.  A station that fails is
                    reported and excluded; a station that passes enters the
                    analysis network on equal footing with every other.

  Record characteristics   wet-day frequency, intensity, maximum daily
                    rainfall and lag-1 autocorrelation.  These describe what
                    each record looks like.  They are computed and reported
                    for transparency but are NOT used to grade, rank or
                    exclude stations, because doing so would introduce a
                    quality classification that the research question does
                    not need and that would have to be defended separately.

Reporting the characteristics without grading on them is the honest middle
ground: a reader can see that records differ, and no station is quietly
downgraded on a threshold chosen after the fact.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ═══════════════════════════════════════════════════════════════════════════
#  Statistical tests (self-contained — no external dependency)
# ═══════════════════════════════════════════════════════════════════════════

def pettitt_test(x: np.ndarray) -> tuple[float, int, float]:
    """
    Pettitt (1979) non-parametric change-point test.

    Returns (K, change_point_index, approximate p-value).
    U_t is computed from ranks in O(n log n) rather than the O(n^2) double sum.
    """
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = x.size
    if n < 10:
        return np.nan, -1, np.nan
    ranks = pd.Series(x).rank(method="average").to_numpy()
    # U_t = 2 * cumsum(rank) - t * (n + 1)
    t = np.arange(1, n + 1)
    U = 2.0 * np.cumsum(ranks) - t * (n + 1)
    k = int(np.argmax(np.abs(U)))
    K = float(np.abs(U[k]))
    p = 2.0 * np.exp(-6.0 * K ** 2 / (n ** 3 + n ** 2))
    return K, k, float(min(p, 1.0))


def mann_kendall(x: np.ndarray) -> tuple[float, float]:
    """Mann-Kendall trend test with tie correction. Returns (Z, p)."""
    from scipy.stats import norm
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = x.size
    if n < 10:
        return np.nan, np.nan
    s = 0.0
    for i in range(n - 1):
        s += np.sum(np.sign(x[i + 1:] - x[i]))
    _, counts = np.unique(x, return_counts=True)
    tie = np.sum(counts * (counts - 1) * (2 * counts + 5))
    var = (n * (n - 1) * (2 * n + 5) - tie) / 18.0
    if var <= 0:
        return np.nan, np.nan
    z = (s - np.sign(s)) / np.sqrt(var) if s != 0 else 0.0
    p = 2.0 * (1.0 - norm.cdf(abs(z)))
    return float(z), float(p)


def lag1_autocorrelation(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    m = np.isfinite(x)
    x = x[m]
    if x.size < 30 or np.std(x) == 0:
        return np.nan
    return float(np.corrcoef(x[:-1], x[1:])[0, 1])


# ═══════════════════════════════════════════════════════════════════════════
#  Diagnostics
# ═══════════════════════════════════════════════════════════════════════════

def station_diagnostics(obs: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    wet_thr = float(cfg["data"]["wet_threshold_mm"])
    cal = cfg["periods"]["calibration"]
    val = cfg["periods"]["validation"]
    yr = obs.index.year
    m_cal = (yr >= cal[0]) & (yr <= cal[1])
    m_val = (yr >= val[0]) & (yr <= val[1])

    rows = []
    for s in obs.columns:
        v = obs[s].to_numpy(dtype=float)
        fin = np.isfinite(v)
        wet = v[fin & (v >= wet_thr)]
        annual = obs[s].resample("YS").sum(min_count=300)
        zero_frac = obs[s].resample("YS").apply(
            lambda g: float(np.mean(g.to_numpy(dtype=float) < wet_thr))
        )
        K_a, _, p_a = pettitt_test(annual.to_numpy(dtype=float))
        K_z, cz, p_z = pettitt_test(zero_frac.to_numpy(dtype=float))
        z_mk, p_mk = mann_kendall(annual.to_numpy(dtype=float))

        wf_cal = float(np.mean(v[m_cal & fin] >= wet_thr)) if (m_cal & fin).any() else np.nan
        wf_val = float(np.mean(v[m_val & fin] >= wet_thr)) if (m_val & fin).any() else np.nan
        wf_rel = abs(wf_val - wf_cal) / wf_cal if wf_cal and np.isfinite(wf_cal) else np.nan

        rows.append(dict(
            station=s,
            n_days=int(fin.sum()),
            missing_pct=round(100.0 * (1 - fin.mean()), 3),
            wet_freq=round(float(np.mean(v[fin] >= wet_thr)), 4),
            SDII=round(float(np.mean(wet)), 4) if wet.size else np.nan,
            sd_daily=round(float(np.std(v[fin], ddof=1)), 4),
            max_daily=round(float(np.nanmax(v)), 2),
            p99_wet=round(float(np.quantile(wet, 0.99)), 2) if wet.size > 20 else np.nan,
            lag1_acf=round(lag1_autocorrelation(v), 4),
            annual_mean=round(float(annual.mean()), 2),
            annual_sd=round(float(annual.std(ddof=1)), 2),
            wetfreq_cal=round(wf_cal, 4),
            wetfreq_val=round(wf_val, 4),
            wetfreq_rel_change=round(wf_rel, 4) if np.isfinite(wf_rel) else np.nan,
            pettitt_annual_p=round(p_a, 5),
            pettitt_zerofrac_p=round(p_z, 5),
            pettitt_zerofrac_cp_year=int(zero_frac.index[cz].year) if cz >= 0 else -1,
            MK_Z_annual=round(z_mk, 4) if np.isfinite(z_mk) else np.nan,
            MK_p_annual=round(p_mk, 5) if np.isfinite(p_mk) else np.nan,
        ))
    return pd.DataFrame(rows)


def qc_gate(diag: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """
    Standard quality control: completeness and homogeneity.

    Returns the diagnostics table with `passed_qc` and `qc_notes` added.
    Record characteristics are carried through unchanged and are never used
    as a pass/fail criterion.
    """
    q = cfg["data_quality_control"]
    max_missing = float(q["max_missing_pct"])
    alpha = float(q["homogeneity"]["pettitt_alpha"])

    out = diag.copy()
    passed, notes = [], []
    for _, r in diag.iterrows():
        fail = []
        if np.isfinite(r.missing_pct) and r.missing_pct > max_missing:
            fail.append(f"missing {r.missing_pct:.1f}% > {max_missing}%")
        if np.isfinite(r.pettitt_annual_p) and r.pettitt_annual_p < alpha:
            fail.append(f"Pettitt(annual) p={r.pettitt_annual_p:.3f} < {alpha}")
        passed.append(not fail)
        notes.append("; ".join(fail) or "passed")
    out["passed_qc"] = passed
    out["qc_notes"] = notes
    out["role"] = np.where(out["passed_qc"],
                           "retained in the analysis network",
                           "excluded before analysis")
    return out


# ═══════════════════════════════════════════════════════════════════════════
#  Season derivation — explicit, reproducible algorithm
# ═══════════════════════════════════════════════════════════════════════════

def derive_seasons(obs: pd.DataFrame, cfg: dict) -> dict:
    """
    method  : climatological_annual_cycle
    smooth  : centred circular 30-day rolling mean of the day-of-year
              climatology of the regional-mean daily rainfall
    wet     : longest contiguous (circular) run above the annual mean daily
              rainfall, extended symmetrically to min_duration_days if shorter
    """
    scfg = cfg["seasons"]
    win = int(str(scfg.get("smoothing", "rolling_30day")).split("_")[1].replace("day", ""))
    min_len = int(scfg.get("min_duration_days", 90))

    regional = obs.mean(axis=1)
    doy = regional.index.dayofyear.to_numpy()
    clim = np.array([np.nanmean(regional.to_numpy(dtype=float)[doy == d])
                     for d in range(1, 366)])
    clim = np.where(np.isfinite(clim), clim, np.nanmean(clim))

    pad = np.concatenate([clim[-win:], clim, clim[:win]])
    kern = np.ones(win) / win
    sm = np.convolve(pad, kern, mode="same")[win:win + 365]

    thr = float(np.mean(sm))
    above = sm > thr

    best_start, best_len, cur_start, cur_len = 0, 0, None, 0
    for i in range(2 * 365):
        j = i % 365
        if above[j]:
            if cur_start is None:
                cur_start = j
            cur_len += 1
            if cur_len > best_len:
                best_len, best_start = cur_len, cur_start
        else:
            cur_start, cur_len = None, 0
        if best_len >= 365:
            break
    best_len = min(best_len, 365)

    if best_len < min_len:
        extra = min_len - best_len
        best_start = (best_start - extra // 2) % 365
        best_len = min_len

    wet_doys = [((best_start + k) % 365) + 1 for k in range(best_len)]
    ref = pd.Timestamp("2001-01-01")
    wet_months = sorted({(ref + pd.Timedelta(days=d - 1)).month for d in wet_doys})

    return dict(
        method=scfg.get("method"),
        smoothing_window_days=win,
        threshold_mm_day=round(thr, 4),
        wet_start_doy=int(wet_doys[0]),
        wet_end_doy=int(wet_doys[-1]),
        wet_length_days=int(best_len),
        wet_months=wet_months,
        dry_months=[m for m in range(1, 13) if m not in wet_months],
    )
