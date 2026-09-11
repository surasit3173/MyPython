"""
test_leakage.py — falsifiable audit of the split-sample protocol.

The claim "no validation-period observation was used to fit the correction"
is not something a reader can verify by reading prose.  It can be verified
by experiment: corrupt the validation-period observations beyond recognition,
re-run the correction, and check the corrected series is bit-identical.

If any validation observation leaked into the transfer function, the outputs
would change and this test would fail.

    python test_leakage.py --config config.yaml
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd
import yaml

import io_layer
import qdm_core
from provenance import Provenance


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))
    rng = np.random.default_rng(int(cfg["reproducibility"]["random_seed"]))

    prov = Provenance(cfg, args.config)
    ds = io_layer.build_dataset(cfg, prov)
    val = cfg["periods"]["validation"]
    cal = cfg["periods"]["calibration"]

    obs_true = ds.observed.df
    m_val = (obs_true.index.year >= val[0]) & (obs_true.index.year <= val[1])
    m_cal = (obs_true.index.year >= cal[0]) & (obs_true.index.year <= cal[1])

    # corrupt validation observations completely
    obs_corrupt = obs_true.copy()
    noise = rng.uniform(0, 500, size=(int(m_val.sum()), obs_true.shape[1]))
    obs_corrupt.loc[obs_true.index[m_val], :] = noise

    print("=" * 78)
    print("  LEAKAGE AUDIT — validation observations replaced by U(0,500) noise")
    print("=" * 78)
    print(f"  calibration days untouched : {int(m_cal.sum()):,}")
    print(f"  validation days corrupted  : {int(m_val.sum()):,}")
    print(f"  observed mean, validation  : true {obs_true.loc[obs_true.index[m_val]].to_numpy(dtype=float).mean():.3f}"
          f"  -> corrupted {noise.mean():.3f} mm day⁻¹\n")

    all_ok = True
    for model, bundle in ds.raw.items():
        a, _ = qdm_core.correct_model(obs_true, bundle.df, cfg, model)
        b, _ = qdm_core.correct_model(obs_corrupt, bundle.df, cfg, model)
        for method in a:
            x = a[method].to_numpy(dtype=float)
            y = b[method].to_numpy(dtype=float)
            same_cal = np.allclose(x[m_cal[:len(x)]], y[m_cal[:len(y)]],
                                   equal_nan=True)
            # the whole series must be identical, calibration and validation
            same_all = np.allclose(x, y, equal_nan=True)
            maxdiff = float(np.nanmax(np.abs(x - y))) if x.size else 0.0
            status = "PASS" if same_all else "**FAIL**"
            if not same_all:
                all_ok = False
            print(f"  {model:16s} {method:4s}  max|Δ| = {maxdiff:.3e}   {status}")

    print()
    print("=" * 78)
    if all_ok:
        print("  ✓ PASS — corrected series are invariant to the validation")
        print("    observations.  The split-sample protocol holds.")
    else:
        print("  ✗ FAIL — validation observations influence the output.")
    print("=" * 78)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
