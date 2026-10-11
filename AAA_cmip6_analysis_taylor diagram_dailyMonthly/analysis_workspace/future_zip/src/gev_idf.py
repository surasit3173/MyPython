"""
gev_idf.py
==========
Non-stationary extreme-value engine for the Observed_Trend_GEV_IDF analysis.
Dependency-light (numpy/scipy). Provides:

  fit_gev()            stationary GEV MLE (own xi sign convention, Coles 2001)
  fit_gev_ns()         non-stationary GEV: location mu(t) = mu0 + mu1 * covariate
  return_level()       GEV return level z_T (Coles 2001)
  return_level_ci()    delta-method 95% CI on a return level
  nonstationarity_test() likelihood-ratio test stationary vs covariate model
  fit_gpd() / gpd_return_level()  peaks-over-threshold (GPD) complement
  idf_table()          multi-duration IDF from D-day annual maxima

Convention: xi > 0 heavy-tailed (Frechet), xi < 0 bounded (Weibull), xi = 0
Gumbel. scipy.genextreme uses c = -xi; helpers below use xi directly.
"""
from __future__ import annotations
import numpy as np
from scipy import optimize, stats


# --------------------------------------------------------------------------- #
# GEV core (block maxima)
# --------------------------------------------------------------------------- #
def _gev_logpdf(x, mu, sig, xi):
    if sig <= 0:
        return np.full_like(x, -1e12, dtype=float)
    z = (x - mu) / sig
    if abs(xi) < 1e-8:
        return -np.log(sig) - z - np.exp(-z)
    t = 1.0 + xi * z
    out = np.full_like(x, -1e12, dtype=float)
    ok = t > 0
    out[ok] = -np.log(sig) - (1 + 1 / xi) * np.log(t[ok]) - t[ok] ** (-1 / xi)
    return out


def _nll(params, x, cov=None):
    if cov is None:
        mu, logsig, xi = params
        mu_t = mu
    else:
        mu0, mu1, logsig, xi = params
        mu_t = mu0 + mu1 * cov
    lp = _gev_logpdf(x, mu_t, np.exp(logsig), xi)
    s = -np.sum(lp)
    return s if np.isfinite(s) else 1e12


def fit_gev(x, cov=None):
    """MLE fit. If cov is given, location is mu0 + mu1*cov (non-stationary)."""
    x = np.asarray(x, float)
    sig0 = max(np.std(x) * np.sqrt(6) / np.pi, 1e-3)
    mu0 = np.mean(x) - 0.5772 * sig0
    p0 = [mu0, np.log(sig0), 0.1] if cov is None else [mu0, 0.0, np.log(sig0), 0.1]
    best = None
    for method in ("Nelder-Mead", "Powell"):
        r = optimize.minimize(_nll, p0, args=(x, cov), method=method,
                              options=dict(maxiter=8000, xatol=1e-8, fatol=1e-8)
                              if method == "Nelder-Mead" else dict(maxiter=8000))
        if best is None or r.fun < best.fun:
            best = r
    ll = -best.fun
    k = len(best.x)
    n = x.size
    out = dict(loglik=ll, aic=2 * k - 2 * ll, bic=k * np.log(n) - 2 * ll,
               n=n, params=best.x)
    if cov is None:
        out.update(mu=best.x[0], sigma=np.exp(best.x[1]), xi=best.x[2])
    else:
        out.update(mu0=best.x[0], mu1=best.x[1], sigma=np.exp(best.x[2]),
                   xi=best.x[3])
    return out


def return_level(mu, sig, xi, T):
    """GEV return level for return period T (years), Coles (2001)."""
    y = -np.log(1.0 - 1.0 / T)
    if abs(xi) < 1e-8:
        return mu - sig * np.log(y)
    return mu - (sig / xi) * (1.0 - y ** (-xi))


def _num_hessian(f, p, eps=1e-4):
    p = np.asarray(p, float); n = p.size
    H = np.zeros((n, n))
    fp = f(p)
    for i in range(n):
        for j in range(n):
            pi = p.copy(); pj = p.copy(); pij = p.copy()
            hi = eps * max(abs(p[i]), 1); hj = eps * max(abs(p[j]), 1)
            pi[i] += hi; pj[j] += hj; pij[i] += hi; pij[j] += hj
            H[i, j] = (f(pij) - f(pi) - f(pj) + fp) / (hi * hj)
    return H


def return_level_ci(fit, T, z=1.96):
    """Delta-method 95% CI on the stationary return level z_T (fast, but
    symmetric: unreliable for high xi / small n; prefer profile_rl_ci there)."""
    mu, logsig, xi = fit["mu"], np.log(fit["sigma"]), fit["xi"]
    p = np.array([mu, logsig, xi])
    H = _num_hessian(lambda q: _nll(q, fit["_x"]), p)
    try:
        cov = np.linalg.inv(H)
    except np.linalg.LinAlgError:
        return (np.nan, np.nan)

    def zT(q):
        return return_level(q[0], np.exp(q[1]), q[2], T)
    g = np.zeros(3)
    for i in range(3):
        dp = p.copy(); h = 1e-5 * max(abs(p[i]), 1); dp[i] += h
        g[i] = (zT(dp) - zT(p)) / h
    var = float(g @ cov @ g)
    se = np.sqrt(var) if var > 0 else np.nan
    zt = return_level(fit["mu"], fit["sigma"], fit["xi"], T)
    return (zt - z * se, zt + z * se)


def _profile_nll_zT(zT, x, T):
    """Negative profiled log-lik at fixed return level z_T (location replaced)."""
    yT = -np.log(1.0 - 1.0 / T)

    def inner(params):
        logsig, xi = params
        sig = np.exp(logsig)
        if abs(xi) < 1e-8:
            mu = zT + sig * np.log(yT)
        else:
            mu = zT + (sig / xi) * (1.0 - yT ** (-xi))
        val = -np.sum(_gev_logpdf(x, mu, sig, xi))
        return val if np.isfinite(val) else 1e12

    r = optimize.minimize(inner, [np.log(np.std(x) + 1e-6), 0.1],
                          method="Nelder-Mead",
                          options=dict(maxiter=4000, xatol=1e-7, fatol=1e-7))
    return r.fun


def profile_rl_ci(x, T, level=0.95):
    """Profile-likelihood CI on the return level z_T (Coles 2001 §4.3.2).

    Asymmetric, respects the physical lower bound, and is the recommended
    interval for long return periods / heavy tails where the delta method fails.
    """
    x = np.asarray(x, float)
    fit = fit_gev(x)
    zhat = return_level(fit["mu"], fit["sigma"], fit["xi"], T)
    ll_max = fit["loglik"]
    crit = stats.chi2.ppf(level, 1) / 2.0

    def dev(zT):
        return (ll_max - (-_profile_nll_zT(zT, x, T))) - crit

    scale = max(abs(zhat), 1.0)

    def find(direction):
        step = 0.08 * scale
        x_prev = float(zhat)
        for _ in range(300):
            x_new = x_prev + direction * step
            if direction < 0 and x_new <= 1e-6:
                return 1e-6
            if dev(x_new) > 0:
                try:
                    return float(optimize.brentq(dev, min(x_prev, x_new),
                                                 max(x_prev, x_new)))
                except Exception:                            # noqa: BLE001
                    return float(x_new)
            x_prev = x_new
            step *= 1.25
        return float(x_prev)

    return (find(-1), find(+1))


def bootstrap_rl_ci(x, T, B=500, kind="parametric", seed=0):
    """Percentile bootstrap CI on the return level z_T.

    kind='parametric' simulates from the fitted GEV (stable for small n);
    'nonparametric' resamples the observed maxima. Returns (lo, hi, mean, sd).
    """
    x = np.asarray(x, float)
    rng = np.random.default_rng(seed)
    fit = fit_gev(x)
    n = x.size
    vals = []
    for _ in range(B):
        if kind == "parametric":
            xb = stats.genextreme.rvs(c=-fit["xi"], loc=fit["mu"],
                                      scale=fit["sigma"], size=n, random_state=rng)
        else:
            xb = rng.choice(x, n, replace=True)
        fb = fit_gev(xb)
        vals.append(return_level(fb["mu"], fb["sigma"], fb["xi"], T))
    v = np.array(vals)
    v = v[np.isfinite(v)]
    return (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5)),
            float(v.mean()), float(v.std()))


def nonstationarity_test(x, cov):
    """Likelihood-ratio test: stationary GEV vs mu(t)=mu0+mu1*cov.

    Returns both fits, the LR statistic, its chi2(1) p-value, AIC/BIC of each,
    the mu1 coefficient and a significance verdict.
    """
    x = np.asarray(x, float); cov = np.asarray(cov, float)
    fs = fit_gev(x)
    fn = fit_gev(x, cov=cov)
    lr = 2.0 * (fn["loglik"] - fs["loglik"])
    p = float(stats.chi2.sf(lr, df=1)) if lr > 0 else 1.0
    # SE of mu1 from the non-stationary Hessian
    H = _num_hessian(lambda q: _nll(q, x, cov), fn["params"])
    try:
        var_mu1 = np.linalg.inv(H)[1, 1]
        se_mu1 = float(np.sqrt(var_mu1)) if var_mu1 > 0 else np.nan
    except Exception:                                        # noqa: BLE001
        se_mu1 = np.nan
    return dict(
        ll_stationary=round(fs["loglik"], 3), ll_nonstationary=round(fn["loglik"], 3),
        aic_stationary=round(fs["aic"], 2), aic_nonstationary=round(fn["aic"], 2),
        bic_stationary=round(fs["bic"], 2), bic_nonstationary=round(fn["bic"], 2),
        LR_stat=round(lr, 3), LR_p_value=round(p, 4),
        mu1=round(fn["mu1"], 4), mu1_se=round(se_mu1, 4),
        mu1_z=round(fn["mu1"] / se_mu1, 3) if se_mu1 and np.isfinite(se_mu1) else np.nan,
        xi=round(fn["xi"], 4),
        nonstationary=bool(p < 0.05),
        prefer_by_AIC=("non-stationary" if fn["aic"] < fs["aic"] else "stationary"),
        _fit_s=fs, _fit_n=fn)


# --------------------------------------------------------------------------- #
# GPD (peaks over threshold)
# --------------------------------------------------------------------------- #
def fit_gpd(values, threshold):
    """Fit GPD to exceedances over `threshold`. Returns xi, sigma, rate."""
    v = np.asarray(values, float)
    exceed = v[v > threshold] - threshold
    if exceed.size < 10:
        return None
    c, loc, scale = stats.genpareto.fit(exceed, floc=0)
    return dict(threshold=threshold, xi=float(c), sigma=float(scale),
                n_exceed=int(exceed.size))


def gpd_return_level(gpd, n_years, T, n_per_year):
    """POT return level for T years (Coles 2001). n_per_year = obs/yr (e.g. 365.25)."""
    u, sig, xi = gpd["threshold"], gpd["sigma"], gpd["xi"]
    zeta = gpd["n_exceed"] / (n_years * n_per_year)
    N = T * n_per_year * zeta            # expected exceedances in T years
    if abs(xi) < 1e-8:
        return u + sig * np.log(N)
    return u + (sig / xi) * (N ** xi - 1.0)


# --------------------------------------------------------------------------- #
# IDF (multi-duration, from D-day annual maxima)
# --------------------------------------------------------------------------- #
def idf_table(maxima_by_duration: dict, return_periods, durations_hours: dict):
    """Build an IDF table from {duration_label: annual-maxima array}.

    For each duration a GEV is fitted; depth (mm) and intensity (mm/h) are
    reported per return period. durations_hours maps label -> hours.
    """
    import pandas as pd
    rows = []
    for label, am in maxima_by_duration.items():
        am = np.asarray(am, float)
        f = fit_gev(am); f["_x"] = am
        h = durations_hours[label]
        for T in return_periods:
            depth = return_level(f["mu"], f["sigma"], f["xi"], T)
            lo, hi = profile_rl_ci(am, T)            # profile-likelihood CI
            rows.append(dict(duration=label, duration_h=h, return_period_yr=T,
                             depth_mm=round(float(depth), 2),
                             intensity_mm_per_h=round(float(depth) / h, 3),
                             ci95_low_mm=round(float(lo), 2),
                             ci95_high_mm=round(float(hi), 2),
                             ci_method="profile-likelihood",
                             xi=round(f["xi"], 4)))
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Multi-distribution goodness-of-fit (Bangkok Table-3 style)
# --------------------------------------------------------------------------- #
def distribution_gof(maxima_by_duration: dict, durations_hours: dict,
                     return_periods):
    """Fit GEV, Gumbel, Log-Pearson III, Lognormal and Gamma to the annual
    maxima of each duration; report K-S and Chi-square statistics + p-values
    and the intensity (mm/h) at each return period, plus a best-fit summary.

    Additive helper — does not alter the GEV engine used elsewhere.
    """
    import pandas as pd
    from scipy import stats

    def _spec(dname, x):
        if dname == "GEV":
            p = stats.genextreme.fit(x); d = stats.genextreme
            return p, (lambda q: d.cdf(q, *p)), (lambda u: d.ppf(u, *p)), 3
        if dname == "Gumbel":
            p = stats.gumbel_r.fit(x); d = stats.gumbel_r
            return p, (lambda q: d.cdf(q, *p)), (lambda u: d.ppf(u, *p)), 2
        if dname == "Lognormal":
            p = stats.lognorm.fit(x, floc=0); d = stats.lognorm
            return p, (lambda q: d.cdf(q, *p)), (lambda u: d.ppf(u, *p)), 2
        if dname == "Gamma":
            p = stats.gamma.fit(x, floc=0); d = stats.gamma
            return p, (lambda q: d.cdf(q, *p)), (lambda u: d.ppf(u, *p)), 2
        if dname == "LogPearson3":
            p = stats.pearson3.fit(np.log(x)); d = stats.pearson3
            return (p, (lambda q: d.cdf(np.log(np.clip(q, 1e-9, None)), *p)),
                    (lambda u: np.exp(d.ppf(u, *p))), 3)
        raise ValueError(dname)

    names = ["GEV", "Gumbel", "LogPearson3", "Lognormal", "Gamma"]
    rows, best = [], []
    for label, am in maxima_by_duration.items():
        x = np.asarray(am, float); x = x[np.isfinite(x)]; n = x.size
        h = durations_hours[label]
        k = max(4, int(round(1 + np.log2(n))))           # Sturges bins
        res = {}
        for dn in names:
            try:
                p, cdf, ppf, m = _spec(dn, x)
                ks_s, ks_p = stats.kstest(x, cdf)
                edges = np.array(ppf(np.linspace(0, 1, k + 1)), float)
                edges[0], edges[-1] = -np.inf, np.inf
                obs, _ = np.histogram(x, bins=edges)
                exp = np.full(k, n / k)
                chi = float(np.sum((obs - exp) ** 2 / exp))
                dof = max(1, k - 1 - m)
                chi_p = float(stats.chi2.sf(chi, dof))
                inten = {T: float(ppf(1 - 1.0 / T)) / h for T in return_periods}
                res[dn] = dict(p=p, ks_s=ks_s, ks_p=ks_p, chi=chi, chi_p=chi_p,
                               inten=inten)
            except Exception:                              # noqa: BLE001
                res[dn] = None
        for dn in names:
            r = res[dn]
            if r is None:
                continue
            row = dict(duration=label, duration_h=h, distribution=dn,
                       parameters="; ".join(f"{v:.4g}" for v in r["p"]),
                       KS_stat=round(r["ks_s"], 3), KS_p=round(r["ks_p"], 3),
                       Chi2_stat=round(r["chi"], 3), Chi2_p=round(r["chi_p"], 3))
            for T in return_periods:
                row[f"i_{T}yr_mm_per_h"] = round(r["inten"][T], 3)
            rows.append(row)
        valid = {d: r for d, r in res.items() if r is not None}
        if valid:
            best.append(dict(
                duration=label,
                best_fit_by_KS=min(valid, key=lambda d: valid[d]["ks_s"]),
                KS_stat=round(min(valid.values(), key=lambda r: r["ks_s"])["ks_s"], 3),
                best_fit_by_Chi2=min(valid, key=lambda d: valid[d]["chi"]),
                n_years=n))
    return pd.DataFrame(rows), pd.DataFrame(best)
