#!/usr/bin/env python3
"""
Unit & Known-Answer Tests (Project 1: Prachuap Khiri Khan)
==========================================================
Tests critical statistical core functions against analytical solutions.
"""

import sys
import os
import unittest
import numpy as np

# Add src directory path explicitly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.statistics.mann_kendall import standard_mann_kendall
from src.statistics.sens_slope import sens_slope


class TestPrachuapUnit(unittest.TestCase):

    def test_mann_kendall_known_answer(self):
        """Analytical known answer test for MK test statistic."""
        x = np.array([1.2, 2.3, 3.1, 4.5, 5.6, 6.8, 7.9])
        res = standard_mann_kendall(x)
        self.assertEqual(res['S'], 21.0)
        self.assertAlmostEqual(res['Z'], 3.003757045930553, places=6)

    def test_sens_slope_known_answer(self):
        """Analytical known answer test for Sen's slope estimator."""
        x = np.array([10, 12, 15, 19, 24])
        slope = sens_slope(x)
        self.assertEqual(slope, 3.5)


if __name__ == '__main__':
    unittest.main()
