from __future__ import annotations

import numpy as np
import pytest

import rainfall_trends.statistics as statistics_module
from rainfall_trends.statistics import (
    StatisticsError,
    bh_adjust,
    hamed_rao,
    mann_kendall,
    sen_slope,
    variance_correction_factor,
)


def test_standard_mk_increasing_and_constant() -> None:
    increasing = mann_kendall([1, 2, 3, 4, 5])
    assert increasing.s == 10
    assert increasing.tau == 1
    assert increasing.slope == 1
    assert increasing.z == pytest.approx(2.2045407685)
    assert increasing.p_value == pytest.approx(0.0274863361)

    constant = mann_kendall([4, 4, 4, 4])
    assert constant.s == 0
    assert constant.z == 0
    assert constant.p_value == 1
    assert constant.slope == 0


def test_sen_slope_uses_actual_time_coordinates() -> None:
    slope, intercept = sen_slope([0, 10, 20], [2000, 2005, 2010])
    assert slope == 2
    assert intercept == -4000


def test_tie_corrected_variance_literal() -> None:
    result = mann_kendall([1, 1, 2, 3])
    assert result.s == 5
    assert result.var_s == pytest.approx(7.666666666666667)
    assert result.z == pytest.approx(4 / np.sqrt(7.666666666666667))


def test_hr_eq30_factor_uses_signed_prespecified_lags() -> None:
    factor = variance_correction_factor(10, {1: 0.2, 2: -0.1, 3: 0.05})
    expected = 1 + 2 * (
        9 * 8 * 7 * 0.2 + 8 * 7 * 6 * -0.1 + 7 * 6 * 5 * 0.05
    ) / (10 * 9 * 8)
    assert factor == pytest.approx(expected)


def test_hr_rejects_nonpositive_variance_factor(monkeypatch: pytest.MonkeyPatch) -> None:
    assert variance_correction_factor(10, {1: -2.0}) < 0
    monkeypatch.setattr(statistics_module, "variance_correction_factor", lambda n, autocorrelations: -0.1)
    with pytest.raises(StatisticsError, match="non-positive"):
        hamed_rao([0, 10, 1, 9, 2, 8, 3, 7, 4, 6], max_lag=3, acf_alpha=0.99)


def test_bh_known_values_and_nan_preservation() -> None:
    q, reject = bh_adjust([0.001, 0.01, 0.04, 0.2, np.nan], alpha=0.05)
    assert q[:4] == pytest.approx([0.004, 0.02, 0.0533333333333, 0.2])
    assert np.isnan(q[4])
    assert reject.tolist() == [True, True, False, False, False]
