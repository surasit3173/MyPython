"""Small, read-only synthetic probes for the supplied CMIP6 framework.

These probes do not reproduce the paper.  They isolate three implementation
behaviours found during static review so their consequences can be inspected.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
PKG_ROOT = (
    ROOT
    / "source_archive"
    / "framework_extracted"
    / "paper1_framework"
    / "src"
)
sys.path.insert(0, str(PKG_ROOT))

from cmip6bc.bc import apply, fit  # noqa: E402
from cmip6bc.metrics import annual_indices  # noqa: E402
from cmip6bc.temporal import temporal_metrics  # noqa: E402


def gap_stitch_probe() -> None:
    """A missing calendar gap should separate wet spells, not join them."""
    idx = pd.date_range("2001-01-01", periods=40, freq="D")
    values = np.zeros(40, dtype=float)
    values[:10] = 5.0
    values[10] = np.nan
    values[11:21] = 5.0
    result = temporal_metrics(pd.Series(values, index=idx), wet_thr=1.0)
    print(
        "GAP_STITCH",
        f"reported_max_wet_spell={result['max_wet_spell']}",
        "calendar_aware_expected=10",
    )


def noleap_probe() -> None:
    """Inserting Feb 29 into a no-leap run changes sequence indices."""
    idx = pd.to_datetime(
        ["2000-02-27", "2000-02-28", "2000-03-01", "2000-03-02", "2000-03-03"]
    )
    result = annual_indices(
        pd.Series([10.0] * 5, index=idx),
        wet_thr=1.0,
        wanted=("Rx5day", "CWD"),
    ).iloc[0]
    print(
        "NOLEAP_INSERT",
        f"reported_Rx5day={result['Rx5day']}",
        f"reported_CWD={int(result['CWD'])}",
        "native_calendar_expected_Rx5day=50.0",
        "native_calendar_expected_CWD=5",
    )


def qdm_tie_probe() -> None:
    """Equal target values should not receive the last tied empirical rank."""
    obs = np.linspace(2.0, 120.0, 60)
    mod = np.linspace(1.0, 60.0, 60)
    frozen = fit(
        obs,
        mod,
        station="S",
        model="M",
        method="qdm",
        wet_thr=0.0,
        frequency_adaptation=False,
        min_wet_days=30,
    )
    target = np.array([10.0] * 30 + [20.0] * 30)
    adjusted, _ = apply(frozen, target)
    # np.interp on duplicated x knots assigns the last plotting position in
    # each tied block.  Midrank positions are the tie-aware alternative.
    pp = (np.arange(1, 61, dtype=float) - 0.5) / 60.0
    assigned = np.interp(target, np.sort(target), pp)
    expected_midrank_first_block = np.mean(pp[:30])
    print(
        "QDM_TIES",
        f"assigned_rank_for_10={assigned[0]:.6f}",
        f"tie_midrank_for_10={expected_midrank_first_block:.6f}",
        f"adjusted_unique={np.unique(adjusted).tolist()}",
    )


if __name__ == "__main__":
    gap_stitch_probe()
    noleap_probe()
    qdm_tie_probe()
