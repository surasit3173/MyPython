#!/usr/bin/env python3
"""
Sen's Slope Estimation Module
=============================
Non-parametric estimate of the magnitude of monotonic trend.
"""

import numpy as np

def sens_slope(x):
    """
    Calculates Sen's slope estimator.
    slope = median((x_j - x_k) / (j - k)) for all 1 <= k < j <= n.
    """
    x = np.asarray(x, dtype=np.float64)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 2:
        return 0.0

    slopes = []
    for k in range(n - 1):
        for j in range(k + 1, n):
            slopes.append((x[j] - x[k]) / float(j - k))

    if len(slopes) == 0:
        return 0.0

    return float(np.median(slopes))
