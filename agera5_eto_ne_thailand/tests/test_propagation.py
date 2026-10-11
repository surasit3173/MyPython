"""Taylor vs exact differences and Monte Carlo vs Taylor spread for small errors."""
import numpy as np
import pandas as pd
import pytest

from etoeval import propagation as pg
from etoeval.evaluation import PM_INPUTS


def _station(n: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    return pd.DataFrame({"tmax": rng.uniform(29, 35, n), "tmin": rng.uniform(18, 24, n), "ea": rng.uniform(2.0, 2.8, n),
                         "u2": rng.uniform(1.0, 2.0, n), "rs": rng.uniform(15, 21, n)})


def test_taylor_close_to_exact_for_small_perturbation() -> None:
    st = _station()
    ag = st + np.array([0.1, -0.1, 0.02, 0.05, 0.3])
    t = pg.taylor_decomposition(st, ag, np.full(len(st), 35.0), np.full(len(st), 150.0))
    assert np.max(np.abs(t["delta"] - t["lin_total"])) < 0.01


def test_mc_matches_taylor_for_small_gaussian_errors() -> None:
    st = _station(10)
    cov = np.diag([0.05, 0.05, 0.002, 0.01, 0.2]) ** 2 * 100
    model = {6: (np.zeros(5), cov)}
    mc = pg.monte_carlo_propagation(st, np.full(10, 35.0), np.full(10, 150.0), np.full(10, 6), model, n_samples=2000, seed=3)
    ratio = mc["sd_taylor_indep"] / mc["sd_mc_indep"]
    assert ratio.between(0.9, 1.1).all()


def test_error_model_requires_min_n() -> None:
    e = pd.DataFrame({"month": [1] * 10, **{f"e_{k}": np.zeros(10) for k in PM_INPUTS}})
    assert pg.fit_error_model(e, min_n=30) == {}
