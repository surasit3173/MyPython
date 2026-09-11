"""
changepoint.py
==============
Abrupt-shift (regime-shift) detection for annual hydroclimatic series.
Dependency-free (numpy/scipy only) so it is reusable anywhere. Provides:

  pettitt()            non-parametric single change-point (median shift), Pettitt 1979
  bayesian_cp()        Bayesian single change-point via conjugate Normal-Gamma
                       marginal likelihood -> posterior over the change year + Bayes factor
  sequential_mk()      Sneyers (1990) progressive/retrograde MK -> approximate onset year
  model_selection()    OLS AIC/BIC for null / trend / step / trend+step
  field_significance() AR(1)-surrogate Monte-Carlo test that the across-station
                       cluster of change points exceeds chance (Wilks-type)

All detectors take a 1-D array ordered in time and a matching `years` array.
"""
from __future__ import annotations
import numpy as np
from scipy import stats
from scipy.special import gammaln


# --------------------------------------------------------------------------- #
# 1) Pettitt test
# --------------------------------------------------------------------------- #
def pettitt(x):
    x = np.asarray(x, float)
    n = x.size
    ranks = stats.rankdata(x)
    U = 2.0 * np.cumsum(ranks)[:-1] - np.arange(1, n) * (n + 1)
    Kt = np.abs(U)
    k = int(np.argmax(Kt))
    K = float(Kt[k])
    p = 2.0 * np.exp(-6.0 * K ** 2 / (n ** 3 + n ** 2))
    return dict(cp_index=k, p_value=min(1.0, p), K=K)


# --------------------------------------------------------------------------- #
# 2) Bayesian single change-point (conjugate Normal-Gamma marginal likelihood)
# --------------------------------------------------------------------------- #
def _seg_log_evidence(y, kappa0=0.01, alpha0=1.0, beta0=1.0, mu0=0.0):
    """Log marginal likelihood of a Gaussian segment under a Normal-Gamma prior."""
    m = y.size
    if m == 0:
        return 0.0
    ybar = y.mean()
    s = float(((y - ybar) ** 2).sum())
    kappa_n = kappa0 + m
    alpha_n = alpha0 + m / 2.0
    beta_n = beta0 + 0.5 * s + 0.5 * (kappa0 * m / kappa_n) * (ybar - mu0) ** 2
    return (gammaln(alpha_n) - gammaln(alpha0)
            + alpha0 * np.log(beta0) - alpha_n * np.log(beta_n)
            + 0.5 * (np.log(kappa0) - np.log(kappa_n))
            - 0.5 * m * np.log(2.0 * np.pi))


def bayesian_cp(x, min_seg=3):
    """Posterior over the change-point position + Bayes factor vs no-change.

    Data are standardised so the weakly-informative prior is scale-free.
    Returns most-probable index, its posterior prob, a 90% credible index range,
    and the Bayes factor BF10 (evidence for one change vs none).
    """
    x = np.asarray(x, float)
    z = (x - x.mean()) / (x.std(ddof=0) + 1e-12)
    n = z.size
    logM0 = _seg_log_evidence(z)
    pos = np.arange(min_seg, n - min_seg + 1)         # change AFTER index k-1
    logM = np.array([_seg_log_evidence(z[:k]) + _seg_log_evidence(z[k:])
                     for k in pos])
    # posterior over positions (uniform prior)
    w = logM - logM.max()
    post = np.exp(w) / np.exp(w).sum()
    kbest = int(pos[np.argmax(post)])
    # 90% credible interval over positions
    order = np.argsort(post)[::-1]
    cum = np.cumsum(post[order])
    keep = order[:np.searchsorted(cum, 0.90) + 1]
    lo, hi = int(pos[keep].min()), int(pos[keep].max())
    # Bayes factor: average evidence over change positions vs no-change
    logM_avg = logM.max() + np.log(np.exp(logM - logM.max()).mean())
    bf10 = float(np.exp(logM_avg - logM0))
    return dict(cp_index=kbest - 1, post_prob=float(post.max()),
                ci_index=(lo - 1, hi - 1), bayes_factor=bf10)


# --------------------------------------------------------------------------- #
# 3) Sequential Mann-Kendall (Sneyers 1990)
# --------------------------------------------------------------------------- #
def sequential_mk(x):
    x = np.asarray(x, float)
    n = x.size
    idx = np.arange(1, n + 1)
    E = idx * (idx - 1) / 4.0
    V = idx * (idx - 1) * (2 * idx + 5) / 72.0

    def _prog(seq):
        t = np.zeros(n)
        for i in range(1, n):
            t[i] = np.sum(seq[:i] < seq[i])
        tt = np.cumsum(t)
        with np.errstate(invalid="ignore", divide="ignore"):
            u = (tt - E) / np.sqrt(V)
        u[0] = 0.0
        return u

    u = _prog(x)
    ub = -_prog(x[::-1])[::-1]
    # crossings of u and ub inside the +/-1.96 band approximate the change onset
    diff = u - ub
    cross = np.where(np.sign(diff[:-1]) != np.sign(diff[1:]))[0]
    cross = [c for c in cross if abs(u[c]) < 1.96]      # within confidence band
    cp = int(cross[0]) if cross else int(np.argmin(np.abs(diff)))
    return dict(u_prog=u, u_retro=ub, cp_index=cp,
                crossings=[int(c) for c in cross])


# --------------------------------------------------------------------------- #
# 4) Step vs Trend model selection (AIC / BIC)
# --------------------------------------------------------------------------- #
def _ols_ic(y, X):
    n = y.size
    Xd = np.column_stack([np.ones(n), X]) if X.size else np.ones((n, 1))
    beta, *_ = np.linalg.lstsq(Xd, y, rcond=None)
    sse = float(((y - Xd @ beta) ** 2).sum())
    k = Xd.shape[1] + 1                                # +1 for variance
    ll = -0.5 * n * (np.log(2 * np.pi) + np.log(sse / n) + 1)
    aic = 2 * k - 2 * ll
    bic = k * np.log(n) - 2 * ll
    return aic, bic


def model_selection(x, cp_index):
    """Compare null / linear-trend / step / trend+step at the given break."""
    x = np.asarray(x, float)
    n = x.size
    t = np.arange(n, dtype=float)
    step = (t > cp_index).astype(float)
    models = {
        "null": np.empty((n, 0)),
        "trend": t[:, None],
        "step": step[:, None],
        "trend_step": np.column_stack([t, step]),
    }
    rows = {}
    for name, X in models.items():
        aic, bic = _ols_ic(x, X)
        rows[name] = (aic, bic)
    aics = np.array([rows[m][0] for m in models])
    daic = aics - aics.min()
    wts = np.exp(-0.5 * daic) / np.exp(-0.5 * daic).sum()
    best_aic = min(rows, key=lambda m: rows[m][0])
    best_bic = min(rows, key=lambda m: rows[m][1])
    out = {m: dict(AIC=round(rows[m][0], 2), BIC=round(rows[m][1], 2),
                   AIC_weight=round(float(w), 3))
           for m, w in zip(models, wts)}
    return out, best_aic, best_bic


# --------------------------------------------------------------------------- #
# 5) Field significance (AR(1) surrogate Monte-Carlo)
# --------------------------------------------------------------------------- #
def _ar1_coef(x):
    x = np.asarray(x, float) - np.mean(x)
    denom = np.sum(x[:-1] ** 2)
    return float(np.sum(x[:-1] * x[1:]) / denom) if denom > 0 else 0.0


def field_significance(series_list, alpha=0.05, n_mc=2000, seed=0):
    """Monte-Carlo field significance of the across-station change-point cluster.

    For each station the observed Pettitt significance is recorded. AR(1)
    surrogates (preserving each series' lag-1 autocorrelation, length and
    variance) are generated under the no-change null; the number of stations
    flagged significant is tallied per trial to build the null distribution.
    Returns observed count, expected count, the 95th percentile of the null and
    the field-significance p-value, plus a temporal-clustering p-value (are the
    detected years closer together than random?).
    """
    rng = np.random.default_rng(seed)
    obs_sig, obs_years_idx, params = [], [], []
    for x in series_list:
        x = np.asarray(x, float)
        r = pettitt(x)
        obs_sig.append(r["p_value"] < alpha)
        if r["p_value"] < alpha:
            obs_years_idx.append(r["cp_index"])
        params.append((x.size, _ar1_coef(x), x.std(ddof=1)))
    obs_count = int(np.sum(obs_sig))
    obs_spread = float(np.std(obs_years_idx)) if len(obs_years_idx) >= 2 else np.nan

    null_counts = np.zeros(n_mc, dtype=int)
    null_spreads = []
    for m in range(n_mc):
        years_idx = []
        cnt = 0
        for (n, phi, sd) in params:
            e = rng.standard_normal(n)
            y = np.zeros(n)
            for i in range(1, n):
                y[i] = phi * y[i - 1] + e[i]
            y = y / (y.std(ddof=1) + 1e-12) * sd
            r = pettitt(y)
            if r["p_value"] < alpha:
                cnt += 1
                years_idx.append(r["cp_index"])
        null_counts[m] = cnt
        if len(years_idx) >= 2:
            null_spreads.append(np.std(years_idx))
    field_p = float(np.mean(null_counts >= obs_count))
    exp_count = float(null_counts.mean())
    p95 = float(np.percentile(null_counts, 95))
    if np.isfinite(obs_spread) and null_spreads:
        cluster_p = float(np.mean(np.array(null_spreads) <= obs_spread))
    else:
        cluster_p = np.nan
    return dict(observed_significant=obs_count, expected_significant=round(exp_count, 2),
                null_p95=p95, field_p_value=round(field_p, 4),
                temporal_cluster_p=(round(cluster_p, 4)
                                    if np.isfinite(cluster_p) else None),
                n_monte_carlo=n_mc)


# --------------------------------------------------------------------------- #
# 6) Table builders (per station x timescale + spatial field significance)
# --------------------------------------------------------------------------- #
import pandas as pd                                          # noqa: E402


def analyze_series(x, years, alpha=0.05):
    """Run all detectors + model selection on one series; return a result row."""
    x = np.asarray(x, float)
    years = np.asarray(years)
    pt = pettitt(x)
    by = bayesian_cp(x)
    sm = sequential_mk(x)
    ms, best_aic, best_bic = model_selection(x, pt["cp_index"])
    k = pt["cp_index"]
    pre, post = x[:k + 1], x[k + 1:]
    step_size = float(post.mean() - pre.mean()) if post.size and pre.size else np.nan
    return dict(
        n=x.size,
        pettitt_year=int(years[pt["cp_index"]]), pettitt_p=round(pt["p_value"], 4),
        pettitt_sig=bool(pt["p_value"] < alpha),
        bayes_year=int(years[by["cp_index"]]),
        bayes_post_prob=round(by["post_prob"], 3),
        bayes_ci_low=int(years[by["ci_index"][0]]),
        bayes_ci_high=int(years[by["ci_index"][1]]),
        bayes_factor=round(by["bayes_factor"], 3),
        seqmk_onset_year=int(years[sm["cp_index"]]),
        pre_mean=round(float(pre.mean()), 2) if pre.size else np.nan,
        post_mean=round(float(post.mean()), 2) if post.size else np.nan,
        step_size=round(step_size, 2),
        best_model_AIC=best_aic, best_model_BIC=best_bic,
        w_null=ms["null"]["AIC_weight"], w_trend=ms["trend"]["AIC_weight"],
        w_step=ms["step"]["AIC_weight"], w_trend_step=ms["trend_step"]["AIC_weight"],
        verdict=_verdict(best_bic, pt["p_value"] < alpha),
    )


def _verdict(best_bic, pettitt_sig):
    if not pettitt_sig and best_bic in ("null", "trend"):
        return "no abrupt shift" if best_bic == "null" else "gradual trend"
    if best_bic == "step":
        return "abrupt step"
    if best_bic == "trend_step":
        return "trend + step"
    if best_bic == "trend":
        return "gradual trend"
    return "no abrupt shift"


def per_station_changepoints(ps: dict, alpha=0.05) -> pd.DataFrame:
    rows = []
    for sid, by_var in ps.items():
        for var, s in by_var.items():
            s = s.dropna().astype(float)
            r = analyze_series(s.values, s.index.values, alpha)
            r = dict(station=sid, timescale=var, **r)
            rows.append(r)
    return pd.DataFrame(rows)


def field_significance_by_timescale(ps: dict, alpha=0.05, n_mc=2000) -> pd.DataFrame:
    rows = []
    for var in ["Annual", "Wet", "Dry"]:
        series = [by_var[var].dropna().astype(float).values
                  for by_var in ps.values() if var in by_var]
        fs = field_significance(series, alpha=alpha, n_mc=n_mc)
        rows.append(dict(timescale=var, n_stations=len(series), **fs))
    return pd.DataFrame(rows)
