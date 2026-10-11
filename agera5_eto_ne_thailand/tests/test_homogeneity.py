"""Break detection on synthetic series with a known step."""
import numpy as np
import pandas as pd

from etoeval import homogeneity


def test_snht_and_pettitt_detect_known_step() -> None:
    rng = np.random.default_rng(0)
    x = rng.normal(0, 1, 30)
    x[18:] += 2.5
    sn = homogeneity.snht_test(x, n_sim=999, seed=1)
    pt = homogeneity.pettitt_test(x)
    assert sn.position in (16, 17, 18) and sn.p_value < 0.01
    assert pt.position in (16, 17, 18) and pt.p_value < 0.05


def test_snht_no_break_is_not_significant() -> None:
    x = np.random.default_rng(3).normal(0, 1, 30)
    assert homogeneity.snht_test(x, n_sim=999, seed=1).p_value > 0.05


def test_relative_series_removes_shared_signal() -> None:
    years = np.arange(1980, 2010)
    common = np.linspace(0, 1, years.size)
    ann = pd.DataFrame({c: 2.0 * np.exp(common) for c in (1, 2, 3, 4)}, index=years)
    ann[1] = ann[1] * np.where(years > 1995, 1.5, 1.0)
    rel = homogeneity.relative_series(ann, 1, multiplicative=True)
    assert abs((rel.loc[1996:].mean() - rel.loc[:1995].mean()) - np.log(1.5)) < 1e-9


def test_bh_monotone_and_bounded() -> None:
    q = homogeneity.benjamini_hochberg(np.array([0.001, 0.04, 0.03, 0.5, np.nan]))
    assert np.isnan(q[-1]) and np.all(q[:-1] <= 1) and q[0] <= q[2] <= q[1]
