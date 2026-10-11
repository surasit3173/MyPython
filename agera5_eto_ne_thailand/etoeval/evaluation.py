"""Evaluation of AgERA5 against station references.

Contents
--------
* :func:`metrics` - MBE, PBIAS, MAE, RMSE, Pearson r, OLS line (estimated on
  observed, as in Soulis et al., 2025), R2 and KGE with components.
* :func:`add_anomalies` - deseasonalised anomalies on a common sample.
* :func:`block_bootstrap_ci` - moving-block bootstrap confidence intervals that
  respect serial dependence of monthly series.
* :func:`shapley_eto` - exact Shapley decomposition of the ETo difference into
  contributions of the five Penman-Monteith inputs.
* :func:`effective_rain_usda_scs`, :func:`net_irrigation_requirement` and
  :func:`shapley_nir` - propagation to the reference-crop irrigation demand.
* :func:`cross_validate_adjustment` - monthly scaling / regression bias
  adjustment validated leave-one-year-block-out and leave-one-station-out.

Notes
-----
Sign convention: MBE = mean(estimate - observation); positive values mean
AgERA5 overestimates. This differs from Soulis et al. (2025), where positive
MBE denoted underestimation and MBE was normalised by the observed mean.

References
----------
Gupta, H.V., Kling, H., Yilmaz, K.K., Martinez, G.F. (2009). Decomposition of the
    mean squared error and NSE performance criteria. J. Hydrol. 377, 80-91.
Kling, H., Fuchs, M., Paulin, M. (2012). Runoff conditions in the upper Danube
    basin under an ensemble of climate change scenarios. J. Hydrol. 424-425, 264-277.
Kuensch, H.R. (1989). The jackknife and the bootstrap for general stationary
    observations. Ann. Stat. 17, 1217-1241.
Shapley, L.S. (1953). A value for n-person games. In: Contributions to the
    Theory of Games II, Princeton University Press, 307-317.
Smith, M. (1992). CROPWAT: A computer program for irrigation planning and
    management. FAO Irrigation and Drainage Paper 46. FAO, Rome.
Soulis, K. et al. (2025). Assessing AgERA5 and MERRA-2 global climate datasets
    for small-scale agricultural applications. Atmosphere 16, 263.
Teutschbein, C., Seibert, J. (2012). Bias correction of regional climate model
    simulations for hydrological climate-change impact studies. J. Hydrol.
    456-457, 12-29.
"""
from __future__ import annotations

from collections.abc import Callable
from itertools import combinations
from math import factorial

import numpy as np
import pandas as pd

from . import fao56

PM_INPUTS: tuple[str, ...] = ("tmax", "tmin", "ea", "u2", "rs")


def metrics(obs: np.ndarray | pd.Series, est: np.ndarray | pd.Series, anomalies: bool = False) -> dict[str, float]:
    """Paired evaluation metrics.

    Parameters
    ----------
    obs, est : array_like
        Observed (station) and estimated (AgERA5) values; pairs with a NaN in
        either series are dropped.
    anomalies : bool, default False
        If True the series are anomalies with near-zero means, so PBIAS and the
        KGE bias/variability ratios are undefined and returned as NaN; the
        standard-deviation ratio is reported instead.

    Returns
    -------
    dict
        n, mbe, pbias, mae, rmse, r, r2, slope, intercept, sd_ratio, kge,
        kge_beta, kge_gamma.
    """
    o = np.asarray(obs, dtype=float)
    e = np.asarray(est, dtype=float)
    ok = np.isfinite(o) & np.isfinite(e)
    o, e = o[ok], e[ok]
    n = int(o.size)
    out: dict[str, float] = {"n": float(n)}
    if n < 3:
        return out | {k: np.nan for k in ("mbe", "pbias", "mae", "rmse", "r", "r2", "slope", "intercept",
                                          "sd_ratio", "kge", "kge_beta", "kge_gamma")}
    diff = e - o
    r = float(np.corrcoef(o, e)[0, 1]) if np.std(o) > 0 and np.std(e) > 0 else np.nan
    slope, intercept = np.polyfit(o, e, 1)
    out.update({
        "mbe": float(diff.mean()), "mae": float(np.abs(diff).mean()), "rmse": float(np.sqrt((diff**2).mean())),
        "r": r, "r2": r**2 if np.isfinite(r) else np.nan, "slope": float(slope), "intercept": float(intercept),
        "sd_ratio": float(e.std(ddof=1) / o.std(ddof=1)),
    })
    if anomalies or abs(o.mean()) < 1e-9:
        out.update({"pbias": np.nan, "kge": np.nan, "kge_beta": np.nan, "kge_gamma": np.nan})
    else:
        beta = float(e.mean() / o.mean())
        gamma = float((e.std(ddof=1) / e.mean()) / (o.std(ddof=1) / o.mean()))
        out.update({"pbias": float(100.0 * diff.sum() / o.sum()), "kge_beta": beta, "kge_gamma": gamma,
                    "kge": float(1.0 - np.sqrt((r - 1.0) ** 2 + (beta - 1.0) ** 2 + (gamma - 1.0) ** 2))})
    return out


def add_anomalies(df: pd.DataFrame, cols: list[str], group: str = "stncode") -> pd.DataFrame:
    """Deseasonalised anomalies computed on the common valid sample.

    Parameters
    ----------
    df : pandas.DataFrame
        Must contain ``group``, ``month`` and ``cols``.
    cols : list of str
        Columns to deseasonalise (e.g. ``["obs", "est"]``).
    group : str, default "stncode"
        Grouping column (climatology per group and calendar month).

    Returns
    -------
    pandas.DataFrame
        Copy with ``<col>_anom`` columns. The climatology is computed only over
        rows where all ``cols`` are finite, so both series are deseasonalised
        with identical sampling and anomalies are not biased by missing months.
    """
    out = df.copy()
    common = out[cols].notna().all(axis=1)
    for c in cols:
        clim = out[common].groupby([group, "month"])[c].mean().rename(f"{c}_clim")
        out = out.merge(clim, left_on=[group, "month"], right_index=True, how="left")
        out[f"{c}_anom"] = out[c].where(common) - out[f"{c}_clim"]
        out = out.drop(columns=f"{c}_clim")
    return out


def block_bootstrap_ci(
    df: pd.DataFrame,
    stat: Callable[[pd.DataFrame], float],
    block: int,
    n_boot: int,
    seed: int,
    group: str = "stncode",
    level: float = 0.95,
) -> tuple[float, float]:
    """Moving-block bootstrap confidence interval of a statistic.

    Parameters
    ----------
    df : pandas.DataFrame
        Paired data sorted in time within each ``group``.
    stat : callable
        Function mapping a resampled DataFrame to a scalar.
    block : int
        Block length [rows], e.g. 12 months to preserve within-year dependence.
    n_boot : int
        Number of bootstrap replicates.
    seed : int
        Random seed.
    group : str, default "stncode"
        Blocks are drawn within each group (stratified resampling).
    level : float, default 0.95
        Confidence level.

    Returns
    -------
    tuple of float
        Percentile interval (lower, upper).
    """
    rng = np.random.default_rng(seed)
    groups = [g.reset_index(drop=True) for _, g in df.groupby(group)]
    vals = np.empty(n_boot)
    for b in range(n_boot):
        parts: list[pd.DataFrame] = []
        for g in groups:
            n = len(g)
            L = min(block, n)
            starts = rng.integers(0, n - L + 1, size=int(np.ceil(n / L)))
            idx = np.concatenate([np.arange(s, s + L) for s in starts])[:n]
            parts.append(g.iloc[idx])
        vals[b] = stat(pd.concat(parts, ignore_index=True))
    a = (1.0 - level) / 2.0
    return float(np.nanquantile(vals, a)), float(np.nanquantile(vals, 1.0 - a))


def _eto_from(d: dict[str, np.ndarray], ra: np.ndarray, z: np.ndarray) -> np.ndarray:
    return fao56.eto_penman_monteith(d["tmax"], d["tmin"], d["ea"], d["u2"], d["rs"], ra, z, 0.0)


def shapley_eto(station: pd.DataFrame, agera5: pd.DataFrame, ra: np.ndarray, z: np.ndarray) -> pd.DataFrame:
    """Exact Shapley decomposition of ETo(AgERA5 inputs) - ETo(station inputs).

    Parameters
    ----------
    station, agera5 : pandas.DataFrame
        Aligned rows with columns ``tmax, tmin, ea, u2, rs`` in FAO-56 units.
    ra, z : numpy.ndarray
        Extraterrestrial radiation and elevation per row (station location).

    Returns
    -------
    pandas.DataFrame
        ``phi_<var>`` [mm day-1] per input and ``delta`` = total difference.
        By construction sum(phi) == delta (efficiency property).

    Notes
    -----
    The value function f(S) is PM-ETo computed with AgERA5 values for inputs
    in S and station values otherwise; f(empty) = station-input ETo and
    f(all) = AgERA5-input ETo. The Shapley value averages each input's marginal
    effect over all 2^5 coalitions, so interactions through the non-linear PM
    equation are shared fairly instead of depending on substitution order.
    """
    n = len(PM_INPUTS)
    st = {k: station[k].to_numpy(float) for k in PM_INPUTS}
    ag = {k: agera5[k].to_numpy(float) for k in PM_INPUTS}
    cache: dict[frozenset[str], np.ndarray] = {}

    def f(s: frozenset[str]) -> np.ndarray:
        if s not in cache:
            cache[s] = _eto_from({k: (ag[k] if k in s else st[k]) for k in PM_INPUTS}, ra, z)
        return cache[s]

    out: dict[str, np.ndarray] = {}
    for k in PM_INPUTS:
        others = [x for x in PM_INPUTS if x != k]
        phi = np.zeros(len(station))
        for size in range(n):
            w = factorial(size) * factorial(n - size - 1) / factorial(n)
            for comb in combinations(others, size):
                s = frozenset(comb)
                phi += w * (f(s | {k}) - f(s))
        out[f"phi_{k}"] = phi
    res = pd.DataFrame(out, index=station.index)
    res["delta"] = f(frozenset(PM_INPUTS)) - f(frozenset())
    return res


def effective_rain_usda_scs(p_month_mm: np.ndarray | pd.Series) -> np.ndarray:
    """Monthly effective rainfall, USDA Soil Conservation Service method (CROPWAT).

    Peff = P (125 - 0.2 P) / 125 for P <= 250 mm; Peff = 125 + 0.1 P otherwise.

    Parameters
    ----------
    p_month_mm : array_like
        Monthly rainfall total [mm].

    Returns
    -------
    numpy.ndarray
        Effective rainfall [mm month-1]; continuous at 250 mm (150 mm).
    """
    p = np.asarray(p_month_mm, dtype=float)
    return np.where(p <= 250.0, p * (125.0 - 0.2 * p) / 125.0, 125.0 + 0.1 * p)


def net_irrigation_requirement(eto_month_mm: np.ndarray | pd.Series, p_month_mm: np.ndarray | pd.Series,
                               kc: float = 1.0) -> np.ndarray:
    """Monthly net irrigation requirement of a crop with coefficient ``kc``.

    NIR = max(0, Kc ETo - Peff). With Kc = 1 it is the requirement of the
    FAO-56 reference grass, which avoids crop-calendar assumptions.
    """
    return np.maximum(0.0, kc * np.asarray(eto_month_mm, float) - effective_rain_usda_scs(p_month_mm))


def shapley_nir(eto_obs: np.ndarray, p_obs: np.ndarray, eto_est: np.ndarray, p_est: np.ndarray) -> pd.DataFrame:
    """Two-factor Shapley split of the NIR difference into ETo and rainfall parts.

    Returns
    -------
    pandas.DataFrame
        ``phi_eto``, ``phi_p`` and ``delta`` (= NIR_est - NIR_obs) per row.
        Opposite signs of phi_eto and phi_p indicate error compensation.
    """
    f = net_irrigation_requirement
    phi_e = 0.5 * ((f(eto_est, p_obs) - f(eto_obs, p_obs)) + (f(eto_est, p_est) - f(eto_obs, p_est)))
    phi_p = 0.5 * ((f(eto_obs, p_est) - f(eto_obs, p_obs)) + (f(eto_est, p_est) - f(eto_est, p_obs)))
    return pd.DataFrame({"phi_eto": phi_e, "phi_p": phi_p, "delta": f(eto_est, p_est) - f(eto_obs, p_obs)})


def _fit(train: pd.DataFrame, method: str) -> pd.DataFrame:
    rows = []
    for m, g in train.groupby("month"):
        g = g.dropna(subset=["obs", "est"])
        if method == "scaling" or len(g) < 8 or g["est"].std() == 0:
            fac = g["obs"].sum() / g["est"].sum() if g["est"].sum() > 0 else 1.0
            rows.append({"month": m, "a": 0.0, "b": fac})
        else:
            b, a = np.polyfit(g["est"], g["obs"], 1)
            rows.append({"month": m, "a": a, "b": b})
    return pd.DataFrame(rows)


def cross_validate_adjustment(paired: pd.DataFrame, method: str, scheme: str, block_years: int = 5,
                              non_negative: bool = True) -> pd.DataFrame:
    """Cross-validated monthly bias adjustment.

    Parameters
    ----------
    paired : pandas.DataFrame
        Columns stncode, year, month, obs, est.
    method : {"scaling", "linear"}
        Multiplicative factor per calendar month (linear scaling; Teutschbein &
        Seibert, 2012) or OLS obs = a + b est per calendar month.
    scheme : {"loyo_block", "loso"}
        ``loyo_block``: per station, consecutive blocks of ``block_years`` are
        held out in turn and the transfer function is fitted on the remaining
        years of the same station. ``loso``: the transfer function is fitted
        on the pooled other stations and applied to the held-out station
        (transfer to an ungauged location).
    block_years : int, default 5
        Length of held-out year blocks.
    non_negative : bool, default True
        Clip adjusted values at zero (rainfall, ETo).

    Returns
    -------
    pandas.DataFrame
        Input rows (validation predictions only) with ``est_adj`` and ``fold``.
    """
    if method not in ("scaling", "linear") or scheme not in ("loyo_block", "loso"):
        raise ValueError("unknown method or scheme")
    preds: list[pd.DataFrame] = []
    if scheme == "loso":
        for code in paired["stncode"].unique():
            test = paired[paired["stncode"] == code].copy()
            coef = _fit(paired[paired["stncode"] != code], method)
            test = test.merge(coef, on="month", how="left")
            test["est_adj"] = test["a"] + test["b"] * test["est"]
            test["fold"] = f"loso_{code}"
            preds.append(test.drop(columns=["a", "b"]))
    else:
        for code, g in paired.groupby("stncode"):
            years = np.sort(g["year"].unique())
            for k in range(0, years.size, block_years):
                held = years[k : k + block_years]
                test = g[g["year"].isin(held)].copy()
                coef = _fit(g[~g["year"].isin(held)], method)
                test = test.merge(coef, on="month", how="left")
                test["est_adj"] = test["a"] + test["b"] * test["est"]
                test["fold"] = f"{code}_{held[0]}-{held[-1]}"
                preds.append(test.drop(columns=["a", "b"]))
    out = pd.concat(preds, ignore_index=True)
    if non_negative:
        out["est_adj"] = out["est_adj"].clip(lower=0.0)
    return out
