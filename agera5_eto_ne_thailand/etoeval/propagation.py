"""Propagation of AgERA5 input errors through FAO-56 PM, and error stationarity.

Adapted from the error-propagation framework of Tran et al. (2026), who
propagated the ERA5 ensemble spread through FAO-56 with Monte Carlo (Latin
Hypercube, N = 500) and first-order Taylor expansion. AgERA5 provides no
ensemble, so here the error model is *empirical*: the "nominal" errors
(AgERA5 minus station, which also contain station and representativeness
errors) of the five PM inputs are characterised per calendar month by a mean
vector (systematic part) and a covariance matrix (random part).

Two questions are addressed:

1. Does a first-order Taylor expansion reproduce (a) the actual ETo
   difference and (b) the Monte Carlo spread? (Tran et al. found good
   agreement in central quantiles.)
2. Does ignoring the covariance between input errors (independent sampling)
   bias the propagated ETo uncertainty? Correlated errors of radiation and
   humidity under cloud can partly compensate in PM.

The module also tests the temporal stationarity of the error series: a
break that occurs in the same year at most stations points to the product
(e.g. a change in the assimilated observing system), whereas a
station-specific break points to the station record.

References
----------
Heuvelink, G.B.M. (1998). Error propagation in environmental modelling with
    GIS. Taylor & Francis, London.
McKay, M.D., Beckman, R.J., Conover, W.J. (1979). A comparison of three
    methods for selecting values of input variables in the analysis of output
    from a computer code. Technometrics 21, 239-245.
Tran, B.N. et al. (2026). Evaluating reanalysis datasets as meteorological
    input for estimating reference evapotranspiration in Africa and Southwest
    Asia. Hydrol. Sci. J. 71, 654-672. doi:10.1080/02626667.2025.2600682
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm, qmc

from . import fao56, homogeneity
from .evaluation import PM_INPUTS

# Finite-difference steps for the gradient (FAO-56 units).
FD_STEP: dict[str, float] = {"tmax": 0.05, "tmin": 0.05, "ea": 0.005, "u2": 0.01, "rs": 0.05}


def _eto(x: dict[str, np.ndarray], ra: np.ndarray, z: np.ndarray) -> np.ndarray:
    ea = np.clip(x["ea"], 0.05, None)
    return fao56.eto_penman_monteith(x["tmax"], x["tmin"], ea, np.clip(x["u2"], 0.0, None),
                                     np.clip(x["rs"], 0.0, None), ra, z, 0.0)


def gradient(inputs: pd.DataFrame, ra: np.ndarray, z: np.ndarray) -> pd.DataFrame:
    """Central finite-difference gradient of PM-ETo with respect to each input.

    Parameters
    ----------
    inputs : pandas.DataFrame
        Columns ``tmax, tmin, ea, u2, rs`` (expansion point, here the station
        values).
    ra, z : numpy.ndarray
        Extraterrestrial radiation and elevation per row.

    Returns
    -------
    pandas.DataFrame
        ``g_<var>`` = dETo/dvar [mm day-1 per unit of the input].
    """
    base = {k: inputs[k].to_numpy(float) for k in PM_INPUTS}
    out: dict[str, np.ndarray] = {}
    for k in PM_INPUTS:
        h = FD_STEP[k]
        up = dict(base, **{k: base[k] + h})
        dn = dict(base, **{k: base[k] - h})
        out[f"g_{k}"] = (_eto(up, ra, z) - _eto(dn, ra, z)) / (2.0 * h)
    return pd.DataFrame(out, index=inputs.index)


def taylor_decomposition(station: pd.DataFrame, agera5: pd.DataFrame, ra: np.ndarray, z: np.ndarray) -> pd.DataFrame:
    """First-order Taylor attribution of the ETo difference.

    Returns
    -------
    pandas.DataFrame
        ``lin_<var>`` = g_var x (AgERA5 - station) [mm day-1], their sum
        ``lin_total`` and the exact difference ``delta``; the residual
        ``delta - lin_total`` measures the linearisation error.
    """
    g = gradient(station, ra, z)
    out = pd.DataFrame(index=station.index)
    for k in PM_INPUTS:
        out[f"lin_{k}"] = g[f"g_{k}"].to_numpy() * (agera5[k].to_numpy(float) - station[k].to_numpy(float))
    out["lin_total"] = out[[f"lin_{k}" for k in PM_INPUTS]].sum(axis=1)
    st = {k: station[k].to_numpy(float) for k in PM_INPUTS}
    ag = {k: agera5[k].to_numpy(float) for k in PM_INPUTS}
    out["delta"] = _eto(ag, ra, z) - _eto(st, ra, z)
    return out


def fit_error_model(errors: pd.DataFrame, group: str = "month", min_n: int = 30) -> dict[int, tuple[np.ndarray, np.ndarray]]:
    """Empirical mean vector and covariance of input errors per group.

    Parameters
    ----------
    errors : pandas.DataFrame
        Columns ``month`` (or ``group``) and ``e_<var>`` = AgERA5 - station for
        the five PM inputs (rows with any NaN are dropped).
    group : str, default "month"
        Grouping column (calendar month pools all stations and years).
    min_n : int, default 30
        Minimum complete rows per group.

    Returns
    -------
    dict
        group value -> (mean vector, covariance matrix), variable order
        ``PM_INPUTS``.
    """
    cols = [f"e_{k}" for k in PM_INPUTS]
    model: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    for key, g in errors.dropna(subset=cols).groupby(group):
        if len(g) < min_n:
            continue
        x = g[cols].to_numpy(float)
        model[int(key)] = (x.mean(axis=0), np.cov(x, rowvar=False))
    return model


def _lhs_normal(n: int, cov: np.ndarray, rng_seed: int, correlated: bool) -> np.ndarray:
    d = cov.shape[0]
    u = qmc.LatinHypercube(d=d, seed=rng_seed).random(n)
    zs = norm.ppf(np.clip(u, 1e-12, 1 - 1e-12))
    if correlated:
        # Cholesky on a slightly regularised matrix (numerical safety).
        L = np.linalg.cholesky(cov + 1e-12 * np.eye(d))
        return zs @ L.T
    return zs * np.sqrt(np.diag(cov))


def monte_carlo_propagation(
    station: pd.DataFrame,
    ra: np.ndarray,
    z: np.ndarray,
    months: np.ndarray,
    model: dict[int, tuple[np.ndarray, np.ndarray]],
    n_samples: int = 500,
    seed: int = 20261005,
) -> pd.DataFrame:
    """Monte Carlo (LHS) and Taylor propagation of random input errors.

    For every row, ``n_samples`` error vectors are drawn from N(0, Sigma_m)
    of the row's calendar month (zero mean: random part only, as in Tran et
    al., 2026), added to the station inputs and propagated through PM.

    Parameters
    ----------
    station : pandas.DataFrame
        Station inputs ``tmax, tmin, ea, u2, rs``.
    ra, z : numpy.ndarray
        Extraterrestrial radiation and elevation per row.
    months : numpy.ndarray
        Calendar month per row (selects the error model).
    model : dict
        Output of :func:`fit_error_model`.
    n_samples : int, default 500
        Monte Carlo sample size (Tran et al. found N = 500 sufficient).
    seed : int
        Base seed; each row uses ``seed + row index`` for reproducibility.

    Returns
    -------
    pandas.DataFrame
        Per row: ``eto_station``, ``sd_mc_corr``, ``sd_mc_indep`` (Monte Carlo
        standard deviations with correlated / independent errors),
        ``sd_taylor_corr``, ``sd_taylor_indep`` (sqrt(g' Sigma g)) and the
        normalised versions ``snorm_*`` = sd / eto_station.

    Notes
    -----
    Sampled wind speed and vapour pressure are truncated at small positive
    values to remain physical; this truncation, together with PM
    non-linearity, is what separates Monte Carlo from Taylor results.
    """
    g = gradient(station, ra, z)[[f"g_{k}" for k in PM_INPUTS]].to_numpy()
    base = station[list(PM_INPUTS)].to_numpy(float)
    rows: list[dict[str, float]] = []
    for i in range(len(station)):
        m = int(months[i])
        if m not in model or not np.all(np.isfinite(base[i])):
            rows.append({k: np.nan for k in ("eto_station", "sd_mc_corr", "sd_mc_indep", "sd_taylor_corr", "sd_taylor_indep")})
            continue
        _, cov = model[m]
        res: dict[str, float] = {}
        x0 = {k: np.array([base[i, j]]) for j, k in enumerate(PM_INPUTS)}
        res["eto_station"] = float(_eto(x0, np.array([ra[i]]), np.array([z[i]]))[0])
        for tag, corr in (("corr", True), ("indep", False)):
            eps = _lhs_normal(n_samples, cov, seed + i, corr)
            xs = {k: base[i, j] + eps[:, j] for j, k in enumerate(PM_INPUTS)}
            res[f"sd_mc_{tag}"] = float(np.std(_eto(xs, np.full(n_samples, ra[i]), np.full(n_samples, z[i])), ddof=1))
            c = cov if corr else np.diag(np.diag(cov))
            res[f"sd_taylor_{tag}"] = float(np.sqrt(g[i] @ c @ g[i]))
        rows.append(res)
    out = pd.DataFrame(rows, index=station.index)
    for c in ("sd_mc_corr", "sd_mc_indep", "sd_taylor_corr", "sd_taylor_indep"):
        out[c.replace("sd_", "snorm_")] = out[c] / out["eto_station"]
    return out


def error_stationarity(
    paired: pd.DataFrame,
    variable: str,
    multiplicative: bool,
    min_months: int = 10,
    n_sim: int = 5000,
    seed: int = 20261005,
) -> pd.DataFrame:
    """Single-break tests on annual error series (AgERA5 vs station).

    Parameters
    ----------
    paired : pandas.DataFrame
        Columns stncode, year, month, obs, est.
    variable : str
        Label stored in the output.
    multiplicative : bool
        Use the log ratio log(est/obs) (positive variables: wind, radiation,
        rainfall, ETo) instead of the difference est - obs.
    min_months : int, default 10
        Minimum valid months for an annual mean error.
    n_sim : int
        Monte Carlo replicates for SNHT.
    seed : int
        Random seed.

    Returns
    -------
    pandas.DataFrame
        One row per station: SNHT and Pettitt break years and p-values, with
        BH-FDR q-values across stations, and the mean error before/after.

    Notes
    -----
    The error series is itself a relative series (product minus station), so
    the shared climate signal cancels. Interpretation rests on network
    coherence of break years (see module docstring).
    """
    d = paired.dropna(subset=["obs", "est"]).copy()
    if multiplicative:
        d = d[(d["obs"] > 0) & (d["est"] > 0)]
        d["err"] = np.log(d["est"] / d["obs"])
    else:
        d["err"] = d["est"] - d["obs"]
    cnt = d.groupby(["stncode", "year"])["err"].count()
    ann = d.groupby(["stncode", "year"])["err"].mean().where(cnt >= min_months).dropna()
    rows: list[dict[str, object]] = []
    for code, s in ann.groupby(level="stncode"):
        s = s.droplevel("stncode")
        row: dict[str, object] = {"stncode": int(code), "variable": variable, "n_years": int(s.size)}
        if s.size >= 15:
            sn = homogeneity.snht_test(s.to_numpy(), n_sim=n_sim, seed=seed)
            pt = homogeneity.pettitt_test(s.to_numpy())
            row.update({"snht_break_after": int(s.index[sn.position]), "snht_p": sn.p_value,
                        "pettitt_break_after": int(s.index[pt.position]), "pettitt_p": pt.p_value,
                        "err_before": sn.mean_before, "err_after": sn.mean_after})
        rows.append(row)
    out = pd.DataFrame(rows)
    if "snht_p" in out:
        out["snht_q"] = homogeneity.benjamini_hochberg(out["snht_p"].to_numpy())
        out["pettitt_q"] = homogeneity.benjamini_hochberg(out["pettitt_p"].to_numpy())
    return out
