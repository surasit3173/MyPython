"""Grid-signature and hierarchical aggregation helpers."""

from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd


def grid_signatures(frame: pd.DataFrame) -> dict[str, str]:
    """Return a deterministic identity for each distinct model daily series."""
    signatures = {}
    for column in frame.columns:
        values = frame[column].to_numpy(dtype="<f8", copy=True)
        finite = np.isfinite(values)
        values[~finite] = 0.0
        values[values == 0.0] = 0.0  # canonicalize negative zero
        digest = hashlib.sha256(finite.tobytes() + values.tobytes()).hexdigest()
        signatures[str(column)] = f"grid_{digest[:16]}"
    return signatures
