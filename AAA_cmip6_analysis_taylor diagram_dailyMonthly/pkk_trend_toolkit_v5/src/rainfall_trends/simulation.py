"""Seeded scenario simulations for MK-family calibration and multiplicity."""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd
from scipy.stats import norm, rankdata


def simulate_ar1(
    *,
    n: int,
    reps: int,
    phi: float,
    standardized_slope: float = 0.0,
    seed: int,
) -> np.ndarray:
    if n < 3 or reps < 1:
        raise ValueError("n must be at least three and reps must be positive")
    if not -1 < phi < 1:
        raise ValueError("phi must be in (-1, 1) for a stationary AR(1) process")
    rng = np.random.default_rng(seed)
    series = np.empty((reps, n), dtype=float)
    series[:, 0] = rng.normal(size=reps)
    innovation_scale = np.sqrt(1 - phi**2)
    for index in range(1, n):
        series[:, index] = phi * series[:, index - 1] + innovation_scale * rng.normal(size=reps)
    centered_time = np.arange(n, dtype=float) - (n - 1) / 2
    return series + standardized_slope * centered_time


def false_discovery_proportion(rejected: np.ndarray, true_null: np.ndarray) -> np.ndarray:
    decisions = np.asarray(rejected, dtype=bool)
    nulls = np.asarray(true_null, dtype=bool)
    if decisions.ndim != 2 or nulls.ndim != 1 or decisions.shape[1] != len(nulls):
        raise ValueError("rejected must be replicate-by-test and true_null must match its test dimension")
    total_rejected = decisions.sum(axis=1)
    false_rejected = (decisions & nulls[None, :]).sum(axis=1)
    return false_rejected / np.maximum(total_rejected, 1)


def wilson_interval(successes: int, total: int, alpha: float = 0.05) -> tuple[float, float]:
    if total < 1 or successes < 0 or successes > total or not 0 < alpha < 1:
        raise ValueError("Wilson interval inputs are outside their valid ranges")
    p = successes / total
    z = float(norm.ppf(1 - alpha / 2))
    denominator = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denominator
    half = z * np.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denominator
    return float(max(0, center - half)), float(min(1, center + half))


def simulate_method_performance(
    *,
    n: int,
    reps: int,
    phi_levels: Sequence[float],
    standardized_slopes: Sequence[float],
    alpha: float,
    max_lag: int,
    acf_alpha: float,
    seed: int,
) -> pd.DataFrame:
    if reps < 1 or n < 4:
        raise ValueError("reps must be positive and n must be at least four")
    rows: list[dict[str, float | int | str]] = []
    scenario_rng = np.random.default_rng(seed)
    slopes = [0.0, *[float(value) for value in standardized_slopes]]
    for phi in phi_levels:
        for slope in slopes:
            scenario_seed = int(scenario_rng.integers(0, 2**32 - 1))
            series = simulate_ar1(
                n=n,
                reps=reps,
                phi=float(phi),
                standardized_slope=slope,
                seed=scenario_seed,
            )
            p_values, invalid = _vectorized_method_p_values(
                series, max_lag=max_lag, acf_alpha=acf_alpha
            )
            for method, p_matrix in p_values.items():
                p = p_matrix.ravel()
                successes = int(np.sum(np.isfinite(p) & (p <= alpha)))
                estimate = successes / reps
                low, high = wilson_interval(successes, reps, alpha=0.05)
                rows.append(
                    {
                        "method": method,
                        "metric": "type_i_error" if slope == 0 else "power",
                        "n": n,
                        "phi": float(phi),
                        "standardized_slope": slope,
                        "estimate": estimate,
                        "ci_low": low,
                        "ci_high": high,
                        "mcse": float(np.sqrt(estimate * (1 - estimate) / reps)),
                        "reps": reps,
                        "invalid_replicates": int(invalid.get(method, 0)),
                        "seed": scenario_seed,
                    }
                )
    return pd.DataFrame(rows)


def simulate_complete_null_fdr(
    *,
    n: int,
    reps: int,
    stations: int,
    phi: float,
    spatial_rho: float,
    alpha: float,
    max_lag: int,
    acf_alpha: float,
    seed: int,
) -> pd.DataFrame:
    if not 0 <= spatial_rho < 1:
        raise ValueError("spatial_rho must be in [0, 1)")
    if not -1 < phi < 1 or stations < 2 or n < 4 or reps < 1:
        raise ValueError("invalid complete-null simulation dimensions or phi")
    rng = np.random.default_rng(seed)
    series = np.empty((reps, stations, n), dtype=float)
    common_initial = rng.normal(size=(reps, 1))
    independent_initial = rng.normal(size=(reps, stations))
    series[:, :, 0] = np.sqrt(spatial_rho) * common_initial + np.sqrt(1 - spatial_rho) * independent_initial
    innovation_scale = np.sqrt(1 - phi**2)
    for index in range(1, n):
        common = rng.normal(size=(reps, 1))
        independent = rng.normal(size=(reps, stations))
        innovation = np.sqrt(spatial_rho) * common + np.sqrt(1 - spatial_rho) * independent
        series[:, :, index] = phi * series[:, :, index - 1] + innovation_scale * innovation
    flat = series.reshape(reps * stations, n)
    method_names = ["MK", f"HR-MMK-{max_lag}", "PW-MK", "TFPW-MK"]
    p_values = {method: np.empty(len(flat), dtype=float) for method in method_names}
    invalid = {method: 0 for method in method_names}
    batch_size = 4096
    for start in range(0, len(flat), batch_size):
        stop = min(start + batch_size, len(flat))
        batch_p, batch_invalid = _vectorized_method_p_values(
            flat[start:stop], max_lag=max_lag, acf_alpha=acf_alpha
        )
        for method in method_names:
            p_values[method][start:stop] = batch_p[method]
            invalid[method] += batch_invalid.get(method, 0)
    rows: list[dict[str, float | int | str]] = []
    for method, flat_p in p_values.items():
        p_matrix = flat_p.reshape(reps, stations)
        rejected = _bh_reject_matrix(p_matrix, alpha)
        fdp = false_discovery_proportion(rejected, np.ones(stations, dtype=bool))
        any_rejection = rejected.any(axis=1)
        fdr = float(fdp.mean())
        fwer = float(any_rejection.mean())
        low, high = wilson_interval(int(any_rejection.sum()), reps, alpha=0.05)
        rows.append(
            {
                "method": method,
                "n": n,
                "stations": stations,
                "phi": phi,
                "spatial_rho": spatial_rho,
                "alpha": alpha,
                "fdr": fdr,
                "fwer": fwer,
                "mean_rejection_share": float(rejected.mean()),
                "ci_low": low,
                "ci_high": high,
                "mcse": float(fdp.std(ddof=1) / np.sqrt(reps)) if reps > 1 else 0.0,
                "reps": reps,
                "invalid_series": int(invalid.get(method, 0)),
                "seed": seed,
            }
        )
    return pd.DataFrame(rows)


def _mk_p_values(series: np.ndarray) -> np.ndarray:
    data = np.asarray(series, dtype=float)
    if data.ndim != 2:
        raise ValueError("series must be a two-dimensional replicate-by-time array")
    n = data.shape[1]
    left, right = np.triu_indices(n, k=1)
    s = np.sign(data[:, right] - data[:, left]).sum(axis=1)
    # Gaussian simulations are continuous, so ties occur with probability zero.
    variance = n * (n - 1) * (2 * n + 5) / 18
    z = np.zeros(len(data), dtype=float)
    positive = s > 0
    negative = s < 0
    z[positive] = (s[positive] - 1) / np.sqrt(variance)
    z[negative] = (s[negative] + 1) / np.sqrt(variance)
    return 2 * norm.sf(np.abs(z))


def _sen_slopes(series: np.ndarray) -> np.ndarray:
    n = series.shape[1]
    left, right = np.triu_indices(n, k=1)
    return np.median((series[:, right] - series[:, left]) / (right - left), axis=1)


def _phi1_matrix(series: np.ndarray) -> np.ndarray:
    centered = series - series.mean(axis=1, keepdims=True)
    denominator = np.sum(centered[:, :-1] ** 2, axis=1)
    numerator = np.sum(centered[:, :-1] * centered[:, 1:], axis=1)
    phi = np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator > 0)
    return np.clip(phi, -0.99, 0.99)


def _vectorized_method_p_values(
    series: np.ndarray, *, max_lag: int, acf_alpha: float
) -> tuple[dict[str, np.ndarray], dict[str, int]]:
    data = np.asarray(series, dtype=float)
    n = data.shape[1]
    time = np.arange(n, dtype=float)
    result: dict[str, np.ndarray] = {"MK": _mk_p_values(data)}
    invalid: dict[str, int] = {"MK": 0, "PW-MK": 0, "TFPW-MK": 0}

    slopes = _sen_slopes(data)
    intercepts = np.median(data - slopes[:, None] * time[None, :], axis=1)
    residuals = data - intercepts[:, None] - slopes[:, None] * time[None, :]
    ranks = rankdata(residuals, method="average", axis=1)
    centered_ranks = ranks - ranks.mean(axis=1, keepdims=True)
    rank_denominator = np.sum(centered_ranks**2, axis=1)
    threshold = float(norm.ppf(1 - acf_alpha / 2) / np.sqrt(n))
    correction = np.ones(len(data), dtype=float)
    for lag in range(1, min(max_lag, n - 1) + 1):
        rho = np.divide(
            np.sum(centered_ranks[:, :-lag] * centered_ranks[:, lag:], axis=1),
            rank_denominator,
            out=np.zeros(len(data), dtype=float),
            where=rank_denominator > 0,
        )
        significant_rho = np.where(np.abs(rho) > threshold, rho, 0.0)
        correction += (
            2
            * (n - lag)
            * (n - lag - 1)
            * (n - lag - 2)
            * significant_rho
            / (n * (n - 1) * (n - 2))
        )
    left, right = np.triu_indices(n, k=1)
    s = np.sign(data[:, right] - data[:, left]).sum(axis=1)
    base_variance = n * (n - 1) * (2 * n + 5) / 18
    valid = correction > 0
    hr_z = np.full(len(data), np.nan, dtype=float)
    hr_z[valid & (s > 0)] = (s[valid & (s > 0)] - 1) / np.sqrt(base_variance * correction[valid & (s > 0)])
    hr_z[valid & (s < 0)] = (s[valid & (s < 0)] + 1) / np.sqrt(base_variance * correction[valid & (s < 0)])
    hr_z[valid & (s == 0)] = 0.0
    result[f"HR-MMK-{max_lag}"] = 2 * norm.sf(np.abs(hr_z))
    invalid[f"HR-MMK-{max_lag}"] = int((~valid).sum())

    raw_phi = _phi1_matrix(data)
    raw_whitened = data[:, 1:] - raw_phi[:, None] * data[:, :-1]
    result["PW-MK"] = _mk_p_values(raw_whitened)

    residual_phi = _phi1_matrix(residuals)
    whitened_residuals = residuals[:, 1:] - residual_phi[:, None] * residuals[:, :-1]
    restored = intercepts[:, None] + slopes[:, None] * time[None, 1:] + whitened_residuals
    result["TFPW-MK"] = _mk_p_values(restored)
    return result, invalid


def _bh_reject_matrix(p_values: np.ndarray, alpha: float) -> np.ndarray:
    p = np.asarray(p_values, dtype=float)
    safe = np.where(np.isfinite(p), p, 1.0)
    ordered = np.sort(safe, axis=1)
    m = p.shape[1]
    ranks = np.arange(1, m + 1)
    passing_rank = np.where(ordered <= alpha * ranks / m, ranks, 0).max(axis=1)
    cutoff = np.full(p.shape[0], -1.0)
    active = passing_rank > 0
    cutoff[active] = ordered[np.flatnonzero(active), passing_rank[active] - 1]
    return np.isfinite(p) & (p <= cutoff[:, None])
