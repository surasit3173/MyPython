"""Metrics, Shapley efficiency, effective rainfall and cross-validation."""
import numpy as np
import pandas as pd
import pytest

from etoeval import evaluation as ev


def test_metrics_perfect_and_bias() -> None:
    o = np.linspace(1, 10, 50)
    m = ev.metrics(o, o)
    assert m["rmse"] == pytest.approx(0) and m["kge"] == pytest.approx(1)
    m2 = ev.metrics(o, o + 1.0)
    assert m2["mbe"] == pytest.approx(1.0) and m2["slope"] == pytest.approx(1.0)


def test_shapley_efficiency() -> None:
    rng = np.random.default_rng(2)
    n = 40
    st = pd.DataFrame({"tmax": rng.uniform(28, 36, n), "tmin": rng.uniform(16, 25, n), "ea": rng.uniform(1.8, 3.0, n),
                       "u2": rng.uniform(0.6, 2.5, n), "rs": rng.uniform(13, 23, n)})
    ag = st + rng.normal(0, [0.8, 0.8, 0.15, 0.4, 2.0], (n, 5))
    ra = np.full(n, 35.0)
    z = np.full(n, 150.0)
    sh = ev.shapley_eto(st, ag, ra, z)
    assert np.allclose(sh[[f"phi_{k}" for k in ev.PM_INPUTS]].sum(axis=1), sh["delta"], atol=1e-10)


def test_effective_rain_continuity_and_nir() -> None:
    p = np.array([0.0, 100.0, 250.0, 250.0001, 400.0])
    pe = ev.effective_rain_usda_scs(p)
    assert pe[0] == 0 and pe[1] == pytest.approx(100 * 105 / 125)
    assert pe[2] == pytest.approx(150.0) and pe[3] == pytest.approx(150.0, abs=1e-3)
    assert ev.net_irrigation_requirement(np.array([120.0]), np.array([400.0]))[0] == 0.0


def test_shapley_nir_efficiency() -> None:
    rng = np.random.default_rng(5)
    eo, po = rng.uniform(80, 180, 100), rng.uniform(0, 350, 100)
    ee, pe = eo * 1.1, po * 0.9
    s = ev.shapley_nir(eo, po, ee, pe)
    assert np.allclose(s["phi_eto"] + s["phi_p"], s["delta"])


def test_scaling_recovers_constant_factor_loso() -> None:
    rng = np.random.default_rng(1)
    rows = [{"stncode": c, "year": y, "month": m, "obs": v, "est": v * 1.2}
            for c in (1, 2, 3) for y in range(1990, 2000) for m in range(1, 13) for v in [rng.uniform(2, 6)]]
    out = ev.cross_validate_adjustment(pd.DataFrame(rows), "scaling", "loso")
    assert np.allclose(out["est_adj"], out["obs"])
