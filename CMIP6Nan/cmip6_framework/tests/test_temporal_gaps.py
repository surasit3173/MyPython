"""A real missing day must break a spell and must not be bridged.

Dropping missing values before computing runs silently joins the days either
side of a gap, which inflates spell lengths and the wet-wet transition
probability. These tests pin the intended behaviour.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from cmip6bc import temporal                                   # noqa: E402


def _series(values):
    idx = pd.date_range("2001-01-01", periods=len(values), freq="D")
    return pd.Series(values, index=idx)


def test_missing_day_breaks_a_wet_spell():
    # 40 wet, one missing, 40 wet: the longest real wet spell is 40, not 80
    v = [5.0] * 40 + [np.nan] + [5.0] * 40
    m = temporal.temporal_metrics(_series(v))
    assert m, "metrics should be computed for a series this long"
    assert m["max_wet_spell"] == 40, (
        f"a missing day bridged the spell: got {m['max_wet_spell']}")


def test_missing_day_breaks_a_dry_spell():
    v = [0.0] * 40 + [np.nan] + [0.0] * 40
    m = temporal.temporal_metrics(_series(v))
    assert m["max_dry_spell"] == 40, (
        f"a missing day bridged the spell: got {m['max_dry_spell']}")


def test_transition_probability_ignores_pairs_spanning_a_gap():
    # wet, missing, dry: no wet-to-dry transition may be counted across the gap
    v = ([5.0, np.nan, 0.0] * 30)
    m = temporal.temporal_metrics(_series(v))
    assert np.isnan(m["P_wet_given_wet"]) or m["P_wet_given_wet"] == 0.0, (
        f"a transition was counted across a gap: {m['P_wet_given_wet']}")


def test_complete_series_is_unaffected():
    v = [5.0] * 40 + [0.0] * 40
    m = temporal.temporal_metrics(_series(v))
    assert m["max_wet_spell"] == 40 and m["max_dry_spell"] == 40


if __name__ == "__main__":
    import traceback
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as e:
                fails += 1
                print(f"FAIL {name}: {e}")
            except Exception:
                fails += 1
                print(f"ERROR {name}"); traceback.print_exc()
    sys.exit(1 if fails else 0)
