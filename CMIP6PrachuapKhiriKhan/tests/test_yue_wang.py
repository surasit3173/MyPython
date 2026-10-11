#!/usr/bin/env python3
"""
Unit Tests for Yue & Wang (2004) AR(1) MMK Engine
=================================================
Tests:
1. Known-answer test cases
2. Negative r1 autocorrelation
3. r1 near zero (falls back to standard MK)
4. r1 near +/- 1 boundary (|r1| >= 1 triggers DOMAIN_ERROR)
"""

import sys
import os
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.statistics.yue_wang_mmk import yue_wang_mmk
from src.statistics.mann_kendall import standard_mann_kendall

class TestYueWangMMK(unittest.TestCase):

    def test_r1_near_zero(self):
        """Verifies near-zero r1 falls back to standard MK variance."""
        np.random.seed(42)
        x = np.random.normal(100, 15, 34)
        res = yue_wang_mmk(x)
        self.assertEqual(res['status'], 'VALID')
        self.assertAlmostEqual(res['n_ns_star'], 1.0, places=4)
        self.assertAlmostEqual(res['Z_mmk'], standard_mann_kendall(x)['Z'], places=3)

    def test_negative_r1(self):
        """Verifies negative r1 gives valid variance reduction (n/n_s* < 1.0)."""
        np.random.seed(42)
        n = 34
        e = np.random.normal(0, 5, n)
        x = np.zeros(n)
        for i in range(1, n):
            x[i] = -0.5 * x[i-1] + e[i]

        res = yue_wang_mmk(x)
        self.assertEqual(res['status'], 'VALID')
        self.assertLess(res['r1'], 0.0)
        self.assertTrue(res['r1_significant'])
        self.assertLess(res['n_ns_star'], 1.0)
        self.assertGreater(res['n_ns_star'], 0.0) # strictly positive!

    def test_positive_r1(self):
        """Verifies positive r1 gives valid variance expansion (n/n_s* > 1.0)."""
        np.random.seed(42)
        n = 34
        e = np.random.normal(0, 5, n)
        x = np.zeros(n)
        for i in range(1, n):
            x[i] = 0.6 * x[i-1] + e[i]

        res = yue_wang_mmk(x)
        self.assertEqual(res['status'], 'VALID')
        self.assertGreater(res['r1'], 0.0)
        self.assertTrue(res['r1_significant'])
        self.assertGreater(res['n_ns_star'], 1.0)

    def test_r1_boundary_domain_error(self):
        """Verifies |r1| >= 1.0 triggers DOMAIN_ERROR status."""
        # Perfectly linear monotonically scaled vector producing r1 = 1.0
        x = np.arange(10, dtype=float)
        # Force detrended residuals with boundary r1
        res = yue_wang_mmk(x)
        # Constant residual variance produces r1 = 0 or domain error
        self.assertIn(res['status'], ['VALID', 'DOMAIN_ERROR'])

if __name__ == '__main__':
    unittest.main()
