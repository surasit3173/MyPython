"""Homogeneity screening of annual station series.

Two complementary single-break tests are applied:

* Pettitt (1979) rank test on the candidate series itself (absolute test).
  It responds to step changes but also to monotonic trends, so on its own it
  cannot separate climate change from inhomogeneity.
* Standard Normal Homogeneity Test (SNHT; Alexandersson, 1986) on a relative
  series (candidate minus or divided by a regional reference built from the
  other stations). A relative test removes the shared regional climate signal
  and therefore targets station-specific breaks. It cannot detect breaks that
  occur simultaneously at all stations (e.g. a network-wide instrument change).

Multiplicity across stations x variables is handled with the
Benjamini-Hochberg false discovery rate procedure.

References
----------
Alexandersson, H. (1986). A homogeneity test applied to precipitation data.
    J. Climatol. 6, 661-675.
Benjamini, Y., Hochberg, Y. (1995). Controlling the false discovery rate.
    J. R. Stat. Soc. B 57, 289-300.
Pettitt, A.N. (1979). A non-parametric approach to the change-point problem.
    Appl. Stat. 28, 126-135.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from numpy.typing import NDArray


@dataclass(frozen=True)
class BreakResult:
    """Result of a single-break test.

    Attributes
    ----------
    position : int
        Index of the last observation before the break (0-based).
    statistic : float
        Test statistic (Pettitt K or SNHT T0).
    p_value : float
        Approximate (Pettitt) or Monte Carlo (SNHT) p-value.
    mean_before, mean_after : float
        Means of the original series on each side of the break.
    """

    position: int
    statistic: float
    p_value: float
    mean_before: float
    mean_after: float


def pettitt_test(x: NDArray[np.float64]) -> BreakResult:
    """Pettitt rank-based change-point test.

    Parameters
    ----------
    x : numpy.ndarray
        Series without missing values, length n >= 10.

    Returns
    -------
    BreakResult
        Break position, K statistic and approximate two-sided p-value
        p = 2 exp(-6 K^2 / (n^3 + n^2)), capped at 1.
    """
    x = np.asarray(x, dtype=float)
    n = x.size
    if n < 10:
        raise ValueError("Pettitt test requires at least 10 values")
    sgn = np.sign(x[:, None] - x[None, :])
    u = np.array([sgn[: t + 1, t + 1 :].sum() for t in range(n - 1)])
    t_star = int(np.argmax(np.abs(u)))
    k = float(np.abs(u[t_star]))
    p = float(min(1.0, 2.0 * np.exp(-6.0 * k**2 / (n**3 + n**2))))
    return BreakResult(t_star, k, p, float(x[: t_star + 1].mean()), float(x[t_star + 1 :].mean()))


def _snht_t0(z: NDArray[np.float64]) -> tuple[int, float]:
    n = z.size
    k = np.arange(1, n)
    cs = np.cumsum(z)[:-1]
    z1 = cs / k
    z2 = (z.sum() - cs) / (n - k)
    t = k * z1**2 + (n - k) * z2**2
    i = int(np.argmax(t))
    return i, float(t[i])


def snht_test(x: NDArray[np.float64], n_sim: int = 5000, seed: int = 20261005) -> BreakResult:
    """Standard Normal Homogeneity Test with Monte Carlo p-value.

    Parameters
    ----------
    x : numpy.ndarray
        Series without missing values (typically a relative series).
    n_sim : int, default 5000
        Number of Monte Carlo replicates of i.i.d. Gaussian series of the same
        length used to approximate the null distribution of T0.
    seed : int
        Seed of the random generator (reproducibility).

    Returns
    -------
    BreakResult
        Break position, T0 and Monte Carlo p-value (with +1 correction).

    Notes
    -----
    The null hypothesis assumes serially independent values. Annual relative
    series usually have weak autocorrelation; positive autocorrelation would
    make the test liberal, which is acceptable for a screening role.
    """
    x = np.asarray(x, dtype=float)
    if x.std(ddof=1) == 0:  # constant series: no break can be identified
        return BreakResult(0, 0.0, 1.0, float(x.mean()), float(x.mean()))
    z = (x - x.mean()) / x.std(ddof=1)
    pos, t0 = _snht_t0(z)
    rng = np.random.default_rng(seed)
    sims = rng.standard_normal((n_sim, x.size))
    sims = (sims - sims.mean(axis=1, keepdims=True)) / sims.std(axis=1, ddof=1, keepdims=True)
    t_null = np.array([_snht_t0(s)[1] for s in sims])
    p = (1.0 + float((t_null >= t0).sum())) / (n_sim + 1.0)
    return BreakResult(pos, t0, p, float(x[: pos + 1].mean()), float(x[pos + 1 :].mean()))


def relative_series(annual: pd.DataFrame, candidate: int, multiplicative: bool) -> pd.Series:
    """Build a candidate-minus-reference series from the other stations.

    Parameters
    ----------
    annual : pandas.DataFrame
        Annual values, index = year, columns = station codes.
    candidate : int
        Station code of the candidate column.
    multiplicative : bool
        If True (positive variables such as wind, sunshine, pan evaporation) the
        relative series is log(candidate) - mean(log(reference stations));
        otherwise candidate - mean(reference stations) on anomalies.

    Returns
    -------
    pandas.Series
        Relative series on years where the candidate and at least two reference
        stations are available. Each reference is first centred (or scaled) on
        its own mean so that differences in station climatology cancel; the
        reference is the cross-station median.
    """
    others = [c for c in annual.columns if c != candidate]
    if multiplicative:
        logged = np.log(annual.where(annual > 0))
        anom = logged - logged.mean()
    else:
        anom = annual - annual.mean()
    ref = anom[others]
    # Median rather than mean: one strongly inhomogeneous neighbour must not
    # imprint its break on the reference of every other station.
    ref_med = ref.median(axis=1).where(ref.notna().sum(axis=1) >= 2)
    rel = anom[candidate] - ref_med
    return rel.dropna()


def benjamini_hochberg(p: NDArray[np.float64]) -> NDArray[np.float64]:
    """Benjamini-Hochberg adjusted p-values (q-values).

    Parameters
    ----------
    p : numpy.ndarray
        Raw p-values (NaN allowed and kept as NaN).

    Returns
    -------
    numpy.ndarray
        Adjusted p-values, monotone and capped at 1.
    """
    p = np.asarray(p, dtype=float)
    q = np.full_like(p, np.nan)
    ok = np.isfinite(p)
    pv = p[ok]
    m = pv.size
    if m == 0:
        return q
    order = np.argsort(pv)
    ranked = pv[order] * m / np.arange(1, m + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(m)
    out[order] = np.clip(ranked, 0.0, 1.0)
    q[ok] = out
    return q


def screen_station_network(
    monthly: pd.DataFrame,
    variables: dict[str, bool],
    min_months: int = 11,
    n_sim: int = 5000,
    seed: int = 20261005,
) -> pd.DataFrame:
    """Run absolute Pettitt and relative SNHT for every station and variable.

    Parameters
    ----------
    monthly : pandas.DataFrame
        Tidy station-month table (stncode, year, month and variable columns).
    variables : dict
        Mapping variable name -> multiplicative flag for the relative series.
    min_months : int, default 11
        Minimum valid months for a year to enter the annual mean.
    n_sim : int
        Monte Carlo replicates for SNHT.
    seed : int
        Random seed.

    Returns
    -------
    pandas.DataFrame
        One row per station x variable with break years, p-values, BH-FDR
        q-values (computed separately for each test family) and relative shift
        across the relative-test break.
    """
    rows: list[dict[str, object]] = []
    for var, mult in variables.items():
        cnt = monthly.groupby(["stncode", "year"])[var].count()
        ann = monthly.groupby(["stncode", "year"])[var].mean().where(cnt >= min_months).unstack("stncode")
        for code in ann.columns:
            s = ann[code].dropna()
            row: dict[str, object] = {"stncode": int(code), "variable": var, "n_years": int(s.size)}
            if s.size >= 15:
                pt = pettitt_test(s.to_numpy())
                row.update({"pettitt_break_after": int(s.index[pt.position]), "pettitt_p": pt.p_value,
                            "abs_mean_before": pt.mean_before, "abs_mean_after": pt.mean_after})
            rel = relative_series(ann, int(code), mult)
            if rel.size >= 15:
                sn = snht_test(rel.to_numpy(), n_sim=n_sim, seed=seed)
                yrs = rel.index.to_numpy()
                before = s.loc[s.index <= yrs[sn.position]].mean()
                after = s.loc[s.index > yrs[sn.position]].mean()
                row.update({"snht_rel_break_after": int(yrs[sn.position]), "snht_rel_T0": sn.statistic,
                            "snht_rel_p": sn.p_value, "rel_shift_pct": 100.0 * (after - before) / before
                            if mult else np.nan, "rel_shift_abs": after - before})
            rows.append(row)
    out = pd.DataFrame(rows)
    out["pettitt_q"] = benjamini_hochberg(out["pettitt_p"].to_numpy())
    out["snht_rel_q"] = benjamini_hochberg(out["snht_rel_p"].to_numpy())
    return out
