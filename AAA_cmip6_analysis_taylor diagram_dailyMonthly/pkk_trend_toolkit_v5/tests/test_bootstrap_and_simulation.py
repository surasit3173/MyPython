from __future__ import annotations

import numpy as np

from rainfall_trends.bootstrap import residual_block_bootstrap_sen
from rainfall_trends.simulation import (
    false_discovery_proportion,
    simulate_ar1,
    simulate_complete_null_fdr,
    simulate_method_performance,
    wilson_interval,
)


def test_residual_block_bootstrap_is_deterministic_and_tracks_trend() -> None:
    times = np.array([2000, 2001, 2003, 2004, 2007, 2008], dtype=float)
    values = 2.0 * times + np.array([0.0, 1.0, -1.0, 0.5, -0.5, 0.0])
    first = residual_block_bootstrap_sen(values, times, reps=100, block_length=2, seed=17)
    second = residual_block_bootstrap_sen(values, times, reps=100, block_length=2, seed=17)
    assert len(first.slopes) == 100
    assert np.array_equal(first.slopes, second.slopes)
    assert first.ci_low < 2 < first.ci_high


def test_stationary_ar1_is_seeded_and_near_unit_variance() -> None:
    a = simulate_ar1(n=200, reps=2000, phi=0.6, seed=9)
    b = simulate_ar1(n=200, reps=2000, phi=0.6, seed=9)
    assert np.array_equal(a, b)
    assert abs(float(a[:, 50:].var()) - 1.0) < 0.05
    lag1 = np.corrcoef(a[:, 50:-1].ravel(), a[:, 51:].ravel())[0, 1]
    assert abs(float(lag1) - 0.6) < 0.03


def test_false_discovery_proportion_is_per_replicate() -> None:
    rejected = np.array([[True, False, True], [False, False, False], [True, True, False]])
    true_null = np.array([True, False, True])
    got = false_discovery_proportion(rejected, true_null)
    assert got.tolist() == [1.0, 0.0, 0.5]
    assert got.mean() != rejected.mean()


def test_wilson_interval_contains_observed_rate() -> None:
    low, high = wilson_interval(50, 100)
    assert low < 0.5 < high


def test_method_simulation_and_fdr_are_seeded_and_well_formed() -> None:
    performance = simulate_method_performance(
        n=20,
        reps=200,
        phi_levels=[0.0],
        standardized_slopes=[0.05],
        alpha=0.05,
        max_lag=3,
        acf_alpha=0.05,
        seed=5,
    )
    assert set(performance["method"]) == {"MK", "HR-MMK-3", "PW-MK", "TFPW-MK"}
    assert set(performance["metric"]) == {"type_i_error", "power"}
    assert performance["estimate"].between(0, 1).all()
    assert (performance["reps"] == 200).all()

    fdr = simulate_complete_null_fdr(
        n=20,
        reps=200,
        stations=4,
        phi=0.0,
        spatial_rho=0.0,
        alpha=0.05,
        max_lag=3,
        acf_alpha=0.05,
        seed=6,
    )
    assert set(fdr["method"]) == {"MK", "HR-MMK-3", "PW-MK", "TFPW-MK"}
    assert np.allclose(fdr["fdr"], fdr["fwer"])
    assert (fdr["mean_rejection_share"] <= fdr["fwer"]).all()
