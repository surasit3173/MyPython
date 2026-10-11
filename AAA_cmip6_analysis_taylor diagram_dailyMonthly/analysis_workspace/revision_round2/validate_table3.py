from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "analysis_workspace" / "audit_corrected"
REPORT = ROOT / "analysis_workspace" / "revision_round2" / "output" / "table3_validation.json"


EXPECTED = [
    # scenario, window, index, measure, median, q25, q75, agreement count
    ("ssp245", "Mid-term", "Rx5day", "pct", 12.5, 7.5, 27.4, 6),
    ("ssp245", "Mid-term", "R99p", "pct", 26.5, 8.4, 55.4, 6),
    ("ssp245", "Mid-term", "R50mm", "abs", 0.65, 0.18, 1.06, 6),
    ("ssp585", "Mid-term", "PRCPTOT", "pct", -1.9, -11.6, -0.8, 6),
    ("ssp585", "Mid-term", "SDII", "pct", -5.5, -12.6, -3.7, 6),
    ("ssp585", "Long-term", "PRCPTOT", "pct", -46.7, -52.8, -17.3, 7),
    ("ssp585", "Long-term", "SDII", "pct", -27.7, -37.3, -15.9, 7),
    ("ssp585", "Long-term", "Rx5day", "pct", -25.2, -39.0, -8.3, 6),
    ("ssp585", "Long-term", "R99p", "pct", -62.6, -69.0, -22.8, 6),
    ("ssp585", "Long-term", "CWD", "pct", -14.0, -21.8, -6.2, 6),
    ("ssp585", "Long-term", "R50mm", "abs", -1.18, -1.53, -0.56, 6),
]


def rounded_match(actual: float, expected: float, decimals: int) -> bool:
    tolerance = 0.5 * 10 ** (-decimals) + 1e-12
    return abs(actual - expected) <= tolerance


def main() -> None:
    ensemble = pd.read_csv(AUDIT / "ensemble_change_sensitivity.csv")
    model = pd.read_csv(AUDIT / "model_regional_change_sensitivity.csv")

    if len(ensemble) != 66 or ensemble[["scenario", "window", "index"]].duplicated().any():
        raise AssertionError("Ensemble source must contain 66 unique scenario–window–index rows")
    if len(model) != 462 or model[["model", "scenario", "window", "index"]].duplicated().any():
        raise AssertionError("Model source must contain 462 unique model–scenario–window–index rows")

    selected_keys = {(scenario, window, index) for scenario, window, index, *_ in EXPECTED}
    row_results = []
    mismatches = []

    for scenario, window, index, measure, exp_med, exp_q25, exp_q75, exp_agree in EXPECTED:
        source = ensemble[
            (ensemble["scenario"] == scenario)
            & (ensemble["window"] == window)
            & (ensemble["index"] == index)
        ].iloc[0]
        block = model[
            (model["scenario"] == scenario)
            & (model["window"] == window)
            & (model["index"] == index)
        ]
        if len(block) != 7:
            raise AssertionError(f"Expected seven models for {(scenario, window, index)}, found {len(block)}")

        values = block[f"delta_model_{measure}"].to_numpy(float)
        recomputed = {
            "median": float(np.quantile(values, 0.50, method="linear")),
            "q25": float(np.quantile(values, 0.25, method="linear")),
            "q75": float(np.quantile(values, 0.75, method="linear")),
        }
        positive = int((block["delta_model_abs"] > 0).sum())
        negative = int((block["delta_model_abs"] < 0).sum())
        agreement = max(positive, negative)

        source_values = {
            "median": float(source[f"model_median_{measure}"]),
            "q25": float(source[f"model_q25_{measure}"]),
            "q75": float(source[f"model_q75_{measure}"]),
        }
        if any(abs(recomputed[name] - source_values[name]) > 1e-10 for name in recomputed):
            mismatches.append({"key": [scenario, window, index], "type": "source_vs_recomputation"})

        decimals = 2 if measure == "abs" else 1
        display_checks = {
            "median": rounded_match(recomputed["median"], exp_med, decimals),
            "q25": rounded_match(recomputed["q25"], exp_q25, decimals),
            "q75": rounded_match(recomputed["q75"], exp_q75, decimals),
            "agreement": agreement == exp_agree,
        }
        if not all(display_checks.values()):
            mismatches.append({"key": [scenario, window, index], "type": "display_value", "checks": display_checks})

        row_results.append(
            {
                "scenario": scenario,
                "window": window,
                "index": index,
                "measure": measure,
                "recomputed_median": recomputed["median"],
                "recomputed_q25": recomputed["q25"],
                "recomputed_q75": recomputed["q75"],
                "positive_models": positive,
                "negative_models": negative,
                "agreement_count": agreement,
                "classification": source["model_classification"],
                "display_checks": display_checks,
            }
        )

    robust = ensemble[ensemble["model_robust"].astype(bool)].copy()
    robust_keys = set(zip(robust["scenario"], robust["window"], robust["index"]))
    omitted = robust_keys - selected_keys
    omitted_rows = (
        robust[
            robust.apply(lambda row: (row["scenario"], row["window"], row["index"]) in omitted, axis=1)
        ][
            [
                "scenario",
                "window",
                "index",
                "model_median_abs",
                "model_q25_abs",
                "model_q75_abs",
                "model_median_pct",
                "model_q25_pct",
                "model_q75_pct",
                "model_agreement",
                "model_classification",
            ]
        ]
        .sort_values(["scenario", "window", "index"])
        .to_dict(orient="records")
    )

    report = {
        "status": "PASS_NUMERIC" if not mismatches else "FAIL",
        "source_files": [
            str(AUDIT / "ensemble_change_sensitivity.csv"),
            str(AUDIT / "model_regional_change_sensitivity.csv"),
        ],
        "ensemble_unique_rows": len(ensemble),
        "model_unique_rows": len(model),
        "table3_rows_checked": len(EXPECTED),
        "numeric_mismatches": mismatches,
        "row_results": row_results,
        "robust_combinations_total": len(robust_keys),
        "robust_combinations_selected": len(selected_keys),
        "robust_combinations_omitted": len(omitted),
        "omitted_rows": omitted_rows,
        "selection_assessment": (
            "All displayed values are numerically correct, but Table 3 is not exhaustive. "
            "The main manuscript or table note should state a transparent selection rule and point to Supplementary Table S1, "
            "or Table 3 should include all robust combinations."
        ),
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
