"""Trend-preserving residual block bootstrap."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from .statistics import sen_slope


@dataclass(frozen=True)
class BootstrapResult:
    estimate: float
    ci_low: float
    ci_high: float
    reps: int
    block_length: int
    seed: int
    slopes: np.ndarray


def residual_block_bootstrap_sen(
    values: Sequence[float],
    times: Sequence[float] | None = None,
    *,
    reps: int,
    block_length: int,
    seed: int,
    alpha: float = 0.05,
) -> BootstrapResult:
    y = np.asarray(values, dtype=float)
    t = np.arange(len(y), dtype=float) if times is None else np.asarray(times, dtype=float)
    if y.ndim != 1 or t.ndim != 1 or len(y) != len(t) or len(y) < 3:
        raise ValueError("values and times must be matching one-dimensional arrays of length at least three")
    if not np.isfinite(y).all() or not np.isfinite(t).all() or not np.all(np.diff(t) > 0):
        raise ValueError("values must be finite and times finite and strictly increasing")
    if reps < 1 or block_length < 1 or block_length > len(y):
        raise ValueError("reps must be positive and block_length must lie in [1, n]")
    if not 0 < alpha < 1:
        raise ValueError("alpha must be in (0, 1)")
    estimate, intercept = sen_slope(y, t)
    fitted = intercept + estimate * t
    residuals = y - fitted
    residuals = residuals - residuals.mean()
    rng = np.random.default_rng(seed)
    slopes = np.empty(reps, dtype=float)
    n_blocks = int(np.ceil(len(y) / block_length))
    offsets = np.arange(block_length)
    for replicate in range(reps):
        starts = rng.integers(0, len(y), size=n_blocks)
        indices = ((starts[:, None] + offsets[None, :]) % len(y)).ravel()[: len(y)]
        reconstructed = fitted + residuals[indices]
        slopes[replicate] = sen_slope(reconstructed, t)[0]
    low, high = np.quantile(slopes, [alpha / 2, 1 - alpha / 2])
    return BootstrapResult(
        estimate=estimate,
        ci_low=float(low),
        ci_high=float(high),
        reps=reps,
        block_length=block_length,
        seed=seed,
        slopes=slopes,
    )
