from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import yaml


ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "cmip6bc_q1_notiers_work" / "cmip6bc"
sys.path.insert(0, str(PKG))

import io_layer  # noqa: E402
import qdm_parametric_nonparametric as qdm  # noqa: E402
from provenance import Provenance  # noqa: E402


def main() -> None:
    os.chdir(PKG)
    cfg = yaml.safe_load((PKG / "config.yaml").read_text(encoding="utf-8"))
    data = io_layer.build_dataset(cfg, Provenance(cfg, str(PKG / "config.yaml")))
    model, bundle = next(iter(data.raw.items()))
    changed_obs = data.observed.df.copy()
    years = cfg["periods"]["validation"]
    mask = (changed_obs.index.year >= years[0]) & (changed_obs.index.year <= years[1])
    rng = np.random.default_rng(20260828)
    changed_obs.loc[mask, :] = rng.uniform(0.0, 500.0, size=(int(mask.sum()), changed_obs.shape[1]))

    for method in qdm.METHODS:
        original, _ = qdm.correct_method(data.observed.df, bundle.df, cfg, model, method)
        perturbed, _ = qdm.correct_method(changed_obs, bundle.df, cfg, model, method)
        difference = np.nanmax(np.abs(original.to_numpy() - perturbed.to_numpy()))
        print(f"{method}: max_abs_difference={difference:.3e}")
        if not np.isfinite(difference) or difference != 0.0:
            raise AssertionError(f"validation-observation leakage detected for {method}")


if __name__ == "__main__":
    main()
