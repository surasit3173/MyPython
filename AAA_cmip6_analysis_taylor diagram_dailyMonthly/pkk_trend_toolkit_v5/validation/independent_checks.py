"""Independent, executable reconciliation of headline statistical results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pymannkendall as pymk

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from rainfall_trends.aggregation import build_period_totals
from rainfall_trends.io import load_rainfall
from rainfall_trends.statistics import bh_adjust, hamed_rao, mann_kendall


EXPECTED_STANDARD_MK = {
    "annual": {"n": 34, "slope": 0.8301724137931035, "p_value": 0.7443201094567846},
    "wet": {"n": 34, "slope": -1.381370098039216, "p_value": 0.5142225895753355},
    "dry": {"n": 33, "slope": 3.464423076923077, "p_value": 0.0826382021322849},
}


def independent_bh(p_values: list[float]) -> np.ndarray:
    p = np.asarray(p_values, dtype=float)
    order = np.argsort(p)
    ranked = p[order]
    adjusted_ranked = np.ones(len(p))
    running = 1.0
    for index in range(len(p) - 1, -1, -1):
        running = min(running, ranked[index] * len(p) / (index + 1))
        adjusted_ranked[index] = running
    adjusted = np.empty(len(p))
    adjusted[order] = adjusted_ranked
    return adjusted


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    observations = load_rainfall(
        PACKAGE_ROOT / "data" / "observed_rain_daily.csv",
        layout="wide",
        date_columns=("YEAR", "MONTH", "DAY"),
    )
    totals = build_period_totals(observations)
    eligible = totals[totals["included"]]
    network = (
        eligible.groupby(["period", "year"], observed=True)
        .agg(value=("total_mm", "mean"), stations=("station_id", "nunique"))
        .reset_index()
    )
    network = network[network["stations"] == 12]
    records: list[dict] = []
    all_required_pass = True
    for period, expected in EXPECTED_STANDARD_MK.items():
        group = network[network["period"] == period].sort_values("year")
        values = group["value"].to_numpy()
        years = group["year"].to_numpy()
        ours = mann_kendall(values, years)
        reference = pymk.original_test(values)
        checks = {
            "n": ours.n == expected["n"],
            "slope_literal": bool(np.isclose(ours.slope, expected["slope"], atol=1e-9)),
            "p_literal": bool(np.isclose(ours.p_value, expected["p_value"], atol=5e-6)),
            "s_reference": bool(np.isclose(ours.s, reference.s, atol=0)),
            "tau_reference": bool(np.isclose(ours.tau, reference.Tau, atol=1e-12)),
            "slope_reference": bool(np.isclose(ours.slope, reference.slope, atol=1e-12)),
            "p_reference": bool(np.isclose(ours.p_value, reference.p, atol=1e-12)),
        }
        all_required_pass = all_required_pass and all(checks.values())
        own_hr = hamed_rao(values, years, max_lag=3, acf_alpha=0.05)
        reference_hr = pymk.hamed_rao_modification_test(values, lag=3)
        records.append(
            {
                "period": period,
                "standard_mk": {"ours": {"n": ours.n, "s": ours.s, "tau": ours.tau, "slope": ours.slope, "p_value": ours.p_value}, "pymannkendall": {"s": float(reference.s), "tau": float(reference.Tau), "slope": float(reference.slope), "p_value": float(reference.p)}, "checks": checks},
                "hr_mmk_3": {"ours_p": own_hr.p_value, "pymannkendall_p": float(reference_hr.p), "absolute_difference": abs(own_hr.p_value - float(reference_hr.p)), "note": "Comparison is diagnostic; package definitions can differ in ACF normalization and significant-lag handling."},
            }
        )
    literal_p = [0.001, 0.01, 0.04, 0.2]
    our_q, _ = bh_adjust(literal_p)
    independent_q = independent_bh(literal_p)
    bh_pass = bool(np.allclose(our_q, independent_q, atol=1e-15))
    all_required_pass = all_required_pass and bh_pass
    report = {
        "verdict": "confirmed" if all_required_pass else "failed",
        "required_standard_mk_and_bh_pass": all_required_pass,
        "network_records": records,
        "bh_literal": {"ours": our_q.tolist(), "independent": independent_q.tolist(), "pass": bh_pass},
    }
    payload = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload)
    return 0 if all_required_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
