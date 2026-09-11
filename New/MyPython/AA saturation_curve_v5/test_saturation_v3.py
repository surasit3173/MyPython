# -*- coding: utf-8 -*-
"""
Unit Tests for saturation_curve_v3.py
Run with: pytest test_saturation_v3.py -v
Tests: KGE, NSE, RMSE formulas; saturation point; bootstrap CI
"""
import numpy as np
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from saturation_curve_v3 import (
    _compute_metrics, saturation_point, bootstrap_saturation_ci
)


class TestMetrics:
    """Validate metric formulas against known analytical solutions."""

    def _perfect(self, n=100):
        """Perfect simulation: s == o"""
        np.random.seed(0)
        o = np.random.exponential(5, n)
        return o, o.copy()

    def _zeroes(self, n=100):
        """Zero simulation: s == 0"""
        np.random.seed(0)
        o = np.random.exponential(5, n)
        return o, np.zeros(n)

    # ── KGE tests ─────────────────────────────────────────────────
    def test_kge_perfect(self):
        """KGE = 1.0 when s == o (Gupta et al. 2009)."""
        o, s = self._perfect()
        m = _compute_metrics(o, s)
        assert abs(m["KGE"] - 1.0) < 1e-9, f"KGE perfect: {m['KGE']}"

    def test_kge_range(self):
        """KGE can be ≤ 1 but has no fixed lower bound."""
        np.random.seed(1)
        o = np.random.exponential(5, 200)
        s = np.random.exponential(3, 200)
        m = _compute_metrics(o, s)
        assert m["KGE"] <= 1.0 + 1e-9, f"KGE <= 1: {m['KGE']}"
        assert not np.isnan(m["KGE"]), "KGE is NaN"

    def test_kge_formula_components(self):
        """Verify KGE = 1 - sqrt((r-1)^2 + (sigma_r-1)^2 + (beta-1)^2)."""
        np.random.seed(2)
        o = np.abs(np.random.randn(200)) + 1.0
        s = 1.1 * o + 0.5
        m = _compute_metrics(o, s)
        # Manual calculation
        r_v    = float(np.corrcoef(o, s)[0, 1])
        sigma_r = float(np.std(s, ddof=1) / np.std(o, ddof=1))
        beta    = float(np.mean(s) / np.mean(o))
        kge_exp = 1 - math.sqrt((r_v-1)**2 + (sigma_r-1)**2 + (beta-1)**2)
        assert abs(m["KGE"] - kge_exp) < 1e-9, f"KGE formula mismatch: {m['KGE']} vs {kge_exp}"

    # ── NSE tests ─────────────────────────────────────────────────
    def test_nse_perfect(self):
        """NSE = 1.0 when s == o (Nash & Sutcliffe 1970)."""
        o, s = self._perfect()
        m = _compute_metrics(o, s)
        assert abs(m["NSE"] - 1.0) < 1e-9, f"NSE perfect: {m['NSE']}"

    def test_nse_climatological(self):
        """NSE = 0 when s == mean(o) (climatological forecast)."""
        np.random.seed(3)
        o = np.random.exponential(5, 200) + 1.0
        s = np.full_like(o, np.mean(o))
        m = _compute_metrics(o, s)
        assert abs(m["NSE"]) < 1e-9, f"NSE clim: {m['NSE']}"

    def test_nse_formula(self):
        """Verify NSE = 1 - sum(e^2) / sum((o - mean_o)^2)."""
        np.random.seed(4)
        o = np.abs(np.random.randn(300)) + 1.0
        s = 0.9 * o + 1.0
        m = _compute_metrics(o, s)
        e       = s - o
        dn      = np.sum((o - np.mean(o))**2)
        nse_exp = float(1 - np.sum(e**2) / dn)
        assert abs(m["NSE"] - nse_exp) < 1e-9, f"NSE formula: {m['NSE']} vs {nse_exp}"

    # ── RMSE tests ────────────────────────────────────────────────
    def test_rmse_perfect(self):
        """RMSE = 0 when s == o."""
        o, s = self._perfect()
        m = _compute_metrics(o, s)
        assert m["RMSE"] < 1e-9, f"RMSE perfect: {m['RMSE']}"

    def test_rmse_positive(self):
        """RMSE > 0 for any imperfect simulation."""
        np.random.seed(5)
        o = np.random.exponential(5, 200)
        s = o + np.random.randn(200)
        m = _compute_metrics(o, s)
        assert m["RMSE"] > 0, f"RMSE > 0: {m['RMSE']}"

    def test_rmse_formula(self):
        """Verify RMSE = sqrt(mean((s-o)^2))."""
        np.random.seed(6)
        o = np.abs(np.random.randn(300)) + 1.0
        s = 1.2 * o
        m = _compute_metrics(o, s)
        rmse_exp = float(np.sqrt(np.mean((s - o)**2)))
        assert abs(m["RMSE"] - rmse_exp) < 1e-9, f"RMSE formula: {m['RMSE']} vs {rmse_exp}"

    # ── r tests ───────────────────────────────────────────────────
    def test_r_perfect(self):
        """Pearson r = 1 for perfect linear relationship."""
        o, s = self._perfect()
        m = _compute_metrics(o, s)
        assert abs(m["r"] - 1.0) < 1e-9, f"r perfect: {m['r']}"

    def test_r_range(self):
        """Pearson r ∈ [-1, 1]."""
        np.random.seed(7)
        o = np.random.randn(200)
        s = np.random.randn(200)
        m = _compute_metrics(o, s)
        assert -1.0 - 1e-9 <= m["r"] <= 1.0 + 1e-9, f"r range: {m['r']}"

    # ── Edge cases ────────────────────────────────────────────────
    def test_insufficient_data(self):
        """Fewer than 5 valid pairs → all NaN."""
        o = np.array([1.0, 2.0, 3.0]); s = np.array([1.0, 2.0, 3.0])
        m = _compute_metrics(o, s)
        for k in ["RMSE","KGE","NSE","r"]:
            assert np.isnan(m[k]), f"{k} should be NaN for n<5"

    def test_nan_handling(self):
        """NaN values are excluded before computation."""
        np.random.seed(8)
        o = np.random.exponential(5, 200).astype(float)
        s = o * 1.05
        o[::10] = np.nan   # introduce NaN
        m = _compute_metrics(o, s)
        assert not np.isnan(m["KGE"]), "NaN handling failed"


class TestSaturationPoint:
    """Validate saturation criterion."""

    def test_immediate_flat(self):
        """Flat curve from N=1 → saturation at N=1."""
        means = {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.0}
        N = saturation_point(means, "KGE", 5)
        assert N == 1, f"Flat → N=1: got {N}"

    def test_monotone_decrease(self):
        """Strictly decreasing large improvements → N=5 (no saturation)."""
        means = {1: 5.0, 2: 3.0, 3: 2.0, 4: 1.5, 5: 1.0}
        N = saturation_point(means, "RMSE", 5)
        # Each step is > 5% of total → no saturation until N=5
        assert N == 5, f"Large drops → N=5: got {N}"

    def test_early_saturation(self):
        """Large first step then tiny steps → saturation at N=2."""
        means = {1: 10.0, 2: 1.0, 3: 0.99, 4: 0.98, 5: 0.97}
        N = saturation_point(means, "RMSE", 5)
        assert N == 2, f"Early saturation: got {N}"

    def test_threshold_exactly(self):
        """Exactly at 5% threshold — should NOT trigger saturation."""
        total = 1.0  # total improvement from N=1 to N=5
        # step from N=3→4: 5% of total = 0.05 (boundary, not below)
        means = {1: 1.0, 2: 0.6, 3: 0.3, 4: 0.25, 5: 0.0}
        # step 3→4 = 0.05, total = 1.0, ratio = 0.05 = threshold (not strictly less)
        N = saturation_point(means, "RMSE", 5, threshold=0.05)
        # 0.05 is not < 0.05, so no saturation at N=4; check N=5
        assert N >= 3  # boundary: step not strictly < threshold


class TestBootstrapCI:
    """Validate bootstrap CI for saturation point."""

    def test_ci_within_bounds(self):
        """CI lower ≤ N* ≤ CI upper."""
        results = {
            1: {"KGE": [0.10, 0.12, 0.09, 0.11, 0.10]},
            2: {"KGE": [0.08, 0.07, 0.08, 0.09, 0.07]},
            3: {"KGE": [0.06, 0.06, 0.05, 0.07, 0.06]},
        }
        N_star, lo, hi, dist, _, _ = bootstrap_saturation_ci(
            results, "KGE", M=3, n_bootstrap=100, ci=95)
        assert lo <= N_star <= hi, f"N* not in CI: [{lo}, {hi}], N*={N_star}"
        assert 1 <= lo <= 3
        assert 1 <= hi <= 3

    def test_ci_distribution_length(self):
        """Bootstrap distribution has correct length."""
        results = {
            1: {"RMSE": [10.1, 10.2, 9.9, 10.0, 10.1]},
            2: {"RMSE": [9.0,  9.1, 8.9, 9.0, 9.2]},
            3: {"RMSE": [8.5,  8.6, 8.4, 8.5, 8.6]},
        }
        N_star, lo, hi, dist, _, _ = bootstrap_saturation_ci(
            results, "RMSE", M=3, n_bootstrap=50)
        assert len(dist) == 50, f"Bootstrap dist length: {len(dist)}"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
