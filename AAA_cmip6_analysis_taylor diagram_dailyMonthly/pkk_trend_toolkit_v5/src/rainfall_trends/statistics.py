"""Mann-Kendall family statistics and multiplicity control."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
from scipy.stats import norm, rankdata


class StatisticsError(ValueError):
    """Raised when a declared statistical procedure is undefined."""


@dataclass(frozen=True)
class TrendResult:
    method: str
    n: int
    s: float
    tau: float
    slope: float
    intercept: float
    z: float
    p_value: float
    phi1: float = np.nan
    var_s: float = np.nan
    adjusted_var_s: float = np.nan
    correction_factor: float = 1.0
    significant_lags: tuple[int, ...] = ()


def sen_slope(values: Sequence[float], times: Sequence[float] | None = None) -> tuple[float, float]:
    y, t = _validated_series(values, times)
    slopes: list[float] = []
    for i in range(len(y) - 1):
        slopes.extend(((y[i + 1 :] - y[i]) / (t[i + 1 :] - t[i])).tolist())
    slope = float(np.median(np.asarray(slopes, dtype=float)))
    intercept = float(np.median(y - slope * t))
    return slope, intercept


def mann_kendall(values: Sequence[float], times: Sequence[float] | None = None) -> TrendResult:
    y, t = _validated_series(values, times)
    n = len(y)
    s = float(sum(np.sign(y[i + 1 :] - y[i]).sum() for i in range(n - 1)))
    _, counts = np.unique(y, return_counts=True)
    ties = counts[counts > 1]
    var_s = float((n * (n - 1) * (2 * n + 5) - np.sum(ties * (ties - 1) * (2 * ties + 5))) / 18)
    z, p_value = _z_and_p(s, var_s)
    slope, intercept = sen_slope(y, t)
    tau = s / (0.5 * n * (n - 1))
    return TrendResult(
        method="MK",
        n=n,
        s=s,
        tau=float(tau),
        slope=slope,
        intercept=intercept,
        z=z,
        p_value=p_value,
        var_s=var_s,
        adjusted_var_s=var_s,
    )


def variance_correction_factor(n: int, autocorrelations: Mapping[int, float]) -> float:
    if n < 3:
        raise StatisticsError("At least three observations are required")
    weighted = 0.0
    for lag, rho in autocorrelations.items():
        if lag < 1 or lag >= n:
            raise StatisticsError(f"Invalid autocorrelation lag {lag} for n={n}")
        weighted += (n - lag) * (n - lag - 1) * (n - lag - 2) * float(rho)
    return float(1 + 2 * weighted / (n * (n - 1) * (n - 2)))


def hamed_rao(
    values: Sequence[float],
    times: Sequence[float] | None = None,
    *,
    max_lag: int = 3,
    acf_alpha: float = 0.05,
) -> TrendResult:
    y, t = _validated_series(values, times)
    base = mann_kendall(y, t)
    slope, intercept = sen_slope(y, t)
    residuals = y - (intercept + slope * t)
    ranks = rankdata(residuals, method="average")
    centered = ranks - ranks.mean()
    denominator = float(np.dot(centered, centered))
    threshold = float(norm.ppf(1 - acf_alpha / 2) / np.sqrt(len(y)))
    selected: dict[int, float] = {}
    if denominator > 0:
        for lag in range(1, min(max_lag, len(y) - 1) + 1):
            rho = float(np.dot(centered[:-lag], centered[lag:]) / denominator)
            if abs(rho) > threshold:
                selected[lag] = rho
    factor = variance_correction_factor(len(y), selected)
    if factor <= 0:
        raise StatisticsError(
            f"HR-MMK-{max_lag} produced a non-positive signed variance correction factor ({factor:.6g})"
        )
    adjusted = base.var_s * factor
    z, p_value = _z_and_p(base.s, adjusted)
    return TrendResult(
        method=f"HR-MMK-{max_lag}",
        n=base.n,
        s=base.s,
        tau=base.tau,
        slope=base.slope,
        intercept=base.intercept,
        z=z,
        p_value=p_value,
        phi1=_lag1(residuals),
        var_s=base.var_s,
        adjusted_var_s=adjusted,
        correction_factor=factor,
        significant_lags=tuple(selected),
    )


def pw_mk(values: Sequence[float], times: Sequence[float] | None = None) -> TrendResult:
    y, t = _validated_series(values, times)
    slope, intercept = sen_slope(y, t)
    phi = _lag1(y)
    whitened = y[1:] - phi * y[:-1]
    tested = mann_kendall(whitened, t[1:])
    return TrendResult(
        method="PW-MK",
        n=tested.n,
        s=tested.s,
        tau=tested.tau,
        slope=slope,
        intercept=intercept,
        z=tested.z,
        p_value=tested.p_value,
        phi1=phi,
        var_s=tested.var_s,
        adjusted_var_s=tested.adjusted_var_s,
    )


def tfpw_mk(values: Sequence[float], times: Sequence[float] | None = None) -> TrendResult:
    y, t = _validated_series(values, times)
    slope, intercept = sen_slope(y, t)
    residuals = y - (intercept + slope * t)
    phi = _lag1(residuals)
    whitened_residuals = residuals[1:] - phi * residuals[:-1]
    restored = intercept + slope * t[1:] + whitened_residuals
    tested = mann_kendall(restored, t[1:])
    return TrendResult(
        method="TFPW-MK",
        n=tested.n,
        s=tested.s,
        tau=tested.tau,
        slope=slope,
        intercept=intercept,
        z=tested.z,
        p_value=tested.p_value,
        phi1=phi,
        var_s=tested.var_s,
        adjusted_var_s=tested.adjusted_var_s,
    )


def bh_adjust(p_values: Sequence[float], alpha: float = 0.05) -> tuple[np.ndarray, np.ndarray]:
    if not 0 < alpha < 1:
        raise StatisticsError("alpha must be in (0, 1)")
    p = np.asarray(p_values, dtype=float)
    invalid = (~np.isnan(p)) & ((p < 0) | (p > 1))
    if invalid.any():
        raise StatisticsError("p-values must be in [0, 1] or NaN")
    valid_index = np.flatnonzero(~np.isnan(p))
    q = np.full(p.shape, np.nan, dtype=float)
    reject = np.zeros(p.shape, dtype=bool)
    if len(valid_index) == 0:
        return q, reject
    order_local = np.argsort(p[valid_index], kind="stable")
    ordered_index = valid_index[order_local]
    ordered_p = p[ordered_index]
    m = len(ordered_p)
    adjusted = ordered_p * m / np.arange(1, m + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    adjusted = np.minimum(adjusted, 1.0)
    q[ordered_index] = adjusted
    reject[valid_index] = q[valid_index] <= alpha
    return q, reject


def _validated_series(
    values: Sequence[float], times: Sequence[float] | None
) -> tuple[np.ndarray, np.ndarray]:
    y = np.asarray(values, dtype=float)
    if y.ndim != 1 or len(y) < 3:
        raise StatisticsError("At least three one-dimensional observations are required")
    if not np.isfinite(y).all():
        raise StatisticsError("values must be finite")
    t = np.arange(len(y), dtype=float) if times is None else np.asarray(times, dtype=float)
    if t.ndim != 1 or len(t) != len(y) or not np.isfinite(t).all():
        raise StatisticsError("times must be a finite one-dimensional array matching values")
    if not np.all(np.diff(t) > 0):
        raise StatisticsError("times must be strictly increasing")
    return y, t


def _z_and_p(s: float, variance: float) -> tuple[float, float]:
    if variance <= 0 or s == 0:
        return 0.0, 1.0
    z = (s - 1) / np.sqrt(variance) if s > 0 else (s + 1) / np.sqrt(variance)
    return float(z), float(2 * norm.sf(abs(z)))


def _lag1(values: np.ndarray) -> float:
    if len(values) < 3:
        return 0.0
    centered = values - values.mean()
    denominator = float(np.dot(centered[:-1], centered[:-1]))
    if denominator == 0:
        return 0.0
    return float(np.clip(np.dot(centered[:-1], centered[1:]) / denominator, -0.99, 0.99))
