"""
metrics.py — performance metrics, grouped by evidential status.

GROUP A — construction-dependent diagnostics
    Quantities the correction algorithm is built to reproduce.  Agreement
    here is a design property, not evidence of skill, and must never be
    reported as validation of the method.
        · calibration-period wet-day frequency

GROUP B — independent validation metrics, by what they actually measure
    RMSE, NSE and KGE do not measure temporal correspondence: a series can
    match the observations in timing yet score poorly because its variance
    differs, and vice versa.  They are therefore grouped as error-based
    performance, separately from the correlation family.
        B1 systematic bias            PBIAS, MBE, monthly PBIAS
        B2 distributional fidelity    wet-day frequency and intensity, PSS,
                                      KS-D, quantile relative bias, Rx1day,
                                      Rx5day, R95pTOT
        B3 error-based performance    monthly RMSE, MAE, NSE, KGE, d
        B4 temporal correspondence    monthly r, climatology r,
                                      monthly-anomaly r, annual r

Moriasi et al. (2007) performance classes are deliberately NOT applied.
They were derived for event-matched monthly streamflow from hydrological
models and carry no meaning for free-running GCM daily rainfall.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

METRIC_GROUP = {
    "wet_freq_cal": "A_construction_dependent",
    # B1 — systematic bias
    "PBIAS": "B1_systematic_bias", "MBE": "B1_systematic_bias",
    "mPBIAS": "B1_systematic_bias", "mean_mm_day": "B1_systematic_bias",
    # B2 — distributional fidelity
    "wet_freq": "B2_distributional_fidelity",
    "wetfreq_bias": "B2_distributional_fidelity",
    "SDII": "B2_distributional_fidelity",
    "SDII_relbias_pct": "B2_distributional_fidelity",
    "PSS": "B2_distributional_fidelity", "KS_D": "B2_distributional_fidelity",
    "q50_relbias_pct": "B2_distributional_fidelity",
    "q90_relbias_pct": "B2_distributional_fidelity",
    "q95_relbias_pct": "B2_distributional_fidelity",
    "q99_relbias_pct": "B2_distributional_fidelity",
    "Rx1day": "B2_distributional_fidelity", "Rx5day": "B2_distributional_fidelity",
    "R95pTOT": "B2_distributional_fidelity",
    "Rx1day_relbias_pct": "B2_distributional_fidelity",
    "n_days_above_obs_hist_max": "B2_distributional_fidelity",
    # B3 — error-based performance (not a measure of timing)
    "mRMSE": "B3_error_based", "mMAE": "B3_error_based",
    "mNSE": "B3_error_based", "mKGE": "B3_error_based", "md": "B3_error_based",
    # B4 — temporal correspondence
    "mr": "B4_temporal_correspondence", "clim_r": "B4_temporal_correspondence",
    "monthly_anom_r": "B4_temporal_correspondence",
    "annual_r": "B4_temporal_correspondence",
}


# ═══════════════════════════════════════════════════════════════════════════
#  Paired metrics (monthly / annual series)
# ═══════════════════════════════════════════════════════════════════════════

def paired_metrics(o: np.ndarray, s: np.ndarray, prefix: str = "") -> dict:
    m = np.isfinite(o) & np.isfinite(s)
    o, s = o[m], s[m]
    out = {f"{prefix}{k}": np.nan for k in
           ("RMSE", "MAE", "MBE", "PBIAS", "r", "NSE", "KGE", "d", "RSR",
            "sd_obs", "sd_sim", "sd_ratio", "mean_obs", "mean_sim", "n")}
    if o.size < 5:
        return out
    e = s - o
    mo, ms = o.mean(), s.mean()
    so, ss = o.std(ddof=1), s.std(ddof=1)
    out[f"{prefix}RMSE"] = float(np.sqrt(np.mean(e ** 2)))
    out[f"{prefix}MAE"] = float(np.mean(np.abs(e)))
    out[f"{prefix}MBE"] = float(np.mean(e))
    out[f"{prefix}PBIAS"] = float(100 * e.sum() / o.sum()) if o.sum() else np.nan
    r = float(np.corrcoef(o, s)[0, 1]) if so > 0 and ss > 0 else np.nan
    out[f"{prefix}r"] = r
    den = np.sum((o - mo) ** 2)
    out[f"{prefix}NSE"] = float(1 - np.sum(e ** 2) / den) if den > 0 else np.nan
    if so > 0 and mo != 0 and np.isfinite(r):
        out[f"{prefix}KGE"] = float(
            1 - np.sqrt((r - 1) ** 2 + (ss / so - 1) ** 2 + (ms / mo - 1) ** 2))
    dd = np.sum((np.abs(s - mo) + np.abs(o - mo)) ** 2)
    out[f"{prefix}d"] = float(1 - np.sum(e ** 2) / dd) if dd > 0 else np.nan
    out[f"{prefix}RSR"] = float(out[f"{prefix}RMSE"] / so) if so > 0 else np.nan
    # components needed for the exact MSE decomposition used in Figure 4:
    #   MSE = bias^2 + (sigma_s - r*sigma_o)^2 + sigma_o^2 (1 - r^2)
    out[f"{prefix}sd_obs"] = float(so)
    out[f"{prefix}sd_sim"] = float(ss)
    out[f"{prefix}sd_ratio"] = float(ss / so) if so > 0 else np.nan
    out[f"{prefix}mean_obs"] = float(mo)
    out[f"{prefix}mean_sim"] = float(ms)
    out[f"{prefix}n"] = int(o.size)
    return out


# ═══════════════════════════════════════════════════════════════════════════
#  Distributional
# ═══════════════════════════════════════════════════════════════════════════

def perkins_skill_score(o_wet: np.ndarray, s_wet: np.ndarray,
                        bin_width: float = 1.0) -> float:
    if o_wet.size < 10 or s_wet.size < 10:
        return np.nan
    hi = float(max(o_wet.max(), s_wet.max()))
    edges = np.arange(0, hi + bin_width, bin_width)
    po, _ = np.histogram(o_wet, bins=edges, density=False)
    ps, _ = np.histogram(s_wet, bins=edges, density=False)
    po = po / po.sum()
    ps = ps / ps.sum()
    return float(np.sum(np.minimum(po, ps)))


def ks_statistic(a: np.ndarray, b: np.ndarray) -> float:
    from scipy.stats import ks_2samp
    if a.size < 10 or b.size < 10:
        return np.nan
    return float(ks_2samp(a, b).statistic)


# ═══════════════════════════════════════════════════════════════════════════
#  Full metric set for one (observed, simulated) daily pair
# ═══════════════════════════════════════════════════════════════════════════

def full_metrics(obs_d: pd.Series, sim_d: pd.Series, wet_thr: float,
                 obs_hist_max: float, quantiles=(0.5, 0.9, 0.95, 0.99)) -> dict:
    ix = obs_d.index.intersection(sim_d.index)
    o = obs_d.loc[ix].to_numpy(dtype=float)
    s = sim_d.loc[ix].to_numpy(dtype=float)
    fin = np.isfinite(o) & np.isfinite(s)
    o, s = o[fin], s[fin]
    ixf = ix[fin]
    out: dict = {"n_days": int(o.size)}
    if o.size < 100:
        return out

    ow, sw = o[o >= wet_thr], s[s >= wet_thr]

    # b1 amount
    out["mean_mm_day"] = float(s.mean())
    out["obs_mean_mm_day"] = float(o.mean())
    out["MBE"] = float(s.mean() - o.mean())
    out["PBIAS"] = float(100 * (s.sum() - o.sum()) / o.sum()) if o.sum() else np.nan

    # b2 occurrence
    out["wet_freq"] = float(np.mean(s >= wet_thr))
    out["obs_wet_freq"] = float(np.mean(o >= wet_thr))
    out["wetfreq_bias"] = out["wet_freq"] - out["obs_wet_freq"]

    # b3 intensity
    out["SDII"] = float(sw.mean()) if sw.size else np.nan
    out["obs_SDII"] = float(ow.mean()) if ow.size else np.nan
    out["SDII_relbias_pct"] = (100 * (out["SDII"] - out["obs_SDII"]) / out["obs_SDII"]
                               if out["obs_SDII"] else np.nan)

    # b4 distribution
    out["PSS"] = perkins_skill_score(ow, sw)
    out["KS_D"] = ks_statistic(ow, sw)
    for q in quantiles:
        qo = float(np.quantile(ow, q)) if ow.size > 20 else np.nan
        qs = float(np.quantile(sw, q)) if sw.size > 20 else np.nan
        out[f"q{int(q*100)}_relbias_pct"] = (100 * (qs - qo) / qo
                                             if qo and np.isfinite(qo) else np.nan)

    # b5 upper tail
    so = pd.Series(s, index=ixf)
    oo = pd.Series(o, index=ixf)
    out["Rx1day"] = float(so.resample("YS").max().mean())
    out["obs_Rx1day"] = float(oo.resample("YS").max().mean())
    out["Rx5day"] = float(so.rolling(5, min_periods=5).sum().resample("YS").max().mean())
    out["obs_Rx5day"] = float(oo.rolling(5, min_periods=5).sum().resample("YS").max().mean())
    p95 = float(np.quantile(ow, 0.95)) if ow.size > 20 else np.nan
    if np.isfinite(p95):
        out["R95pTOT"] = float(pd.Series(np.where(s > p95, s, 0.0), index=ixf)
                               .resample("YS").sum().mean())
        out["obs_R95pTOT"] = float(pd.Series(np.where(o > p95, o, 0.0), index=ixf)
                                   .resample("YS").sum().mean())
    out["n_days_above_obs_hist_max"] = int(np.sum(s > obs_hist_max)) \
        if np.isfinite(obs_hist_max) else 0
    out["Rx1day_relbias_pct"] = (100 * (out["Rx1day"] - out["obs_Rx1day"])
                                 / out["obs_Rx1day"] if out["obs_Rx1day"] else np.nan)

    # b6 temporal aggregation
    om = oo.resample("MS").sum(min_count=25)
    sm = so.resample("MS").sum(min_count=25)
    mm = paired_metrics(om.to_numpy(dtype=float), sm.to_numpy(dtype=float), "m")
    out.update(mm)

    oc = om.groupby(om.index.month).mean()
    sc = sm.groupby(sm.index.month).mean()
    out["clim_r"] = float(np.corrcoef(oc.to_numpy(dtype=float),
                                     sc.to_numpy(dtype=float))[0, 1])
    oa = (om - om.groupby(om.index.month).transform("mean")).to_numpy(dtype=float)
    sa = (sm - sm.groupby(sm.index.month).transform("mean")).to_numpy(dtype=float)
    k = np.isfinite(oa) & np.isfinite(sa)
    out["monthly_anom_r"] = (float(np.corrcoef(oa[k], sa[k])[0, 1])
                             if k.sum() > 5 else np.nan)
    oy = oo.resample("YS").sum(min_count=300).to_numpy(dtype=float)
    sy = so.resample("YS").sum(min_count=300).to_numpy(dtype=float)
    k = np.isfinite(oy) & np.isfinite(sy)
    out["annual_r"] = float(np.corrcoef(oy[k], sy[k])[0, 1]) if k.sum() > 5 else np.nan
    out["annual_sd_ratio"] = (float(np.nanstd(sy, ddof=1) / np.nanstd(oy, ddof=1))
                              if np.nanstd(oy, ddof=1) > 0 else np.nan)
    return out


# ═══════════════════════════════════════════════════════════════════════════
#  Inference
# ═══════════════════════════════════════════════════════════════════════════

def benjamini_hochberg(pvals: np.ndarray, alpha: float = 0.05):
    """
    Correct BH step-up.  The naive per-hypothesis check rejects only those
    p_(i) <= alpha*i/m individually and therefore under-rejects: it misses
    every hypothesis ranked below the largest passing rank.
    Returns (reject_flags, q_values).
    """
    p = np.asarray(pvals, dtype=float)
    m = p.size
    q = np.full(m, np.nan)
    rej = np.zeros(m, dtype=bool)
    ok = np.isfinite(p)
    if ok.sum() == 0:
        return rej, q
    idx = np.where(ok)[0]
    order = idx[np.argsort(p[idx])]
    n = order.size
    ranks = np.arange(1, n + 1)
    praw = p[order]
    qraw = np.minimum.accumulate((praw * n / ranks)[::-1])[::-1]
    q[order] = np.minimum(qraw, 1.0)
    passing = np.where(praw <= alpha * ranks / n)[0]
    if passing.size:
        rej[order[: passing.max() + 1]] = True
    return rej, q


def year_block_bootstrap(obs_m: np.ndarray, raw_m: np.ndarray, qdm_m: np.ndarray,
                         n_rep: int, rng: np.random.Generator) -> dict:
    """
    Moving-block bootstrap with whole calendar years as blocks.

    Daily and monthly rainfall are strongly autocorrelated; resampling
    individual months or days would treat dependent observations as
    independent and shrink the confidence intervals artificially.
    Inputs are (n_years, 12) monthly totals.
    """
    ny = obs_m.shape[0]
    if ny < 5:
        return {}
    pick = rng.integers(0, ny, size=(n_rep, ny))
    O = obs_m[pick].reshape(n_rep, -1)
    R = raw_m[pick].reshape(n_rep, -1)
    Q = qdm_m[pick].reshape(n_rep, -1)

    def _rmse(a, b):
        return np.sqrt(np.nanmean((b - a) ** 2, axis=1))

    def _pbias(a, b):
        return 100 * (np.nansum(b - a, axis=1) / np.nansum(a, axis=1))

    def _nse(a, b):
        num = np.nansum((b - a) ** 2, axis=1)
        den = np.nansum((a - np.nanmean(a, axis=1, keepdims=True)) ** 2, axis=1)
        return 1 - num / den

    out = {}
    for name, fn, better in (("mRMSE", _rmse, "lower"),
                             ("mPBIAS_abs", lambda a, b: np.abs(_pbias(a, b)), "lower"),
                             ("mNSE", _nse, "higher")):
        d = fn(O, Q) - fn(O, R)
        lo, hi = np.nanpercentile(d, [2.5, 97.5])
        # two-sided p from the bootstrap distribution of the difference
        p = 2 * min(float(np.mean(d <= 0)), float(np.mean(d >= 0)))
        out[name] = dict(delta=float(np.nanmean(d)), ci_low=float(lo),
                         ci_high=float(hi), p_value=min(p, 1.0),
                         improvement_direction=better)
    return out
