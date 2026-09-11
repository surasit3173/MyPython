"""Independent numerical reconciliations for the frozen Paper 3 outputs."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
sys.path.insert(0, str(ROOT / "src"))

from paper3core.statistics import model_response, observed_response  # noqa: E402


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    config = yaml.safe_load((ROOT / "config" / "paper3_enso.yaml").read_text(encoding="utf-8"))
    minimum = config["enso"]["minimum_seasons_for_composite"]
    gates = pd.read_csv(OUTPUT / "PAPER3_ACCEPTANCE_GATES.csv")
    assert len(gates) == 8 and gates["pass"].astype(bool).all()
    print("RECONCILE gates=8/8 PASS")

    qdm = pd.read_csv(OUTPUT / "crossfit_qdm_diagnostics.csv")
    expected_qdm_rows = 7 * 13 * 7 * 12
    assert len(qdm) == expected_qdm_rows
    assert (qdm["n_target_observations_used"] == 0).all()
    fallback_count = int(qdm["sparse_fallback_used"].astype(bool).sum())
    assert 0 < fallback_count < len(qdm)
    print(f"RECONCILE qdm_rows={len(qdm)} target_observation_leak=0 sparse_fallback={fallback_count}")

    qc = pd.read_csv(OUTPUT / "observed_zero_qc_summary.csv").set_index("classification")
    assert int(qc.loc["probable_missing", "station_months"]) == 43
    assert int(qc.loc["probable_missing", "daily_values_set_missing"]) == 1308
    print("RECONCILE observed_qc probable_missing_months=43 daily_values=1308")

    sample = pd.read_csv(OUTPUT / "enso_phase_sample_sizes.csv")
    observed_sample = sample[sample["source_type"] == "OBSERVED"]
    totals = observed_sample.groupby("season_type")["n_seasons"].sum().to_dict()
    assert totals == {"HOT_DRY": 33, "RAINY": 34}
    print(f"RECONCILE complete_management_seasons={totals}")

    long = pd.read_csv(OUTPUT / "seasonal_metrics_long.csv.gz")
    saved = pd.read_csv(OUTPUT / "primary_response_summary.csv")
    comparisons = []
    for row in saved.itertuples(index=False):
        subset = long[
            (long["source_type"] == row.source_type)
            & (long["season_type"] == row.season_type)
            & (long["metric"] == row.metric)
        ]
        if row.source_type == "OBSERVED":
            point, _ = observed_response(subset, phase=row.phase, minimum_seasons=minimum)
        else:
            point, _, _ = model_response(subset, phase=row.phase, minimum_seasons=minimum)
        comparisons.append(
            {
                "source_type": row.source_type,
                "season_type": row.season_type,
                "metric": row.metric,
                "phase": row.phase,
                "saved_pct": row.response_pct,
                "recomputed_pct": point["response_pct"],
                "absolute_difference": abs(row.response_pct - point["response_pct"]),
            }
        )
    response_audit = pd.DataFrame(comparisons)
    assert response_audit["absolute_difference"].max() < 1.0e-10
    response_audit.to_csv(OUTPUT / "response_numerical_audit.csv", index=False)
    print(f"RECONCILE primary_responses=48 max_abs_diff={response_audit['absolute_difference'].max():.3g}")

    preservation = pd.read_csv(OUTPUT / "qdm_enso_signal_preservation.csv")
    assert np.allclose(
        preservation["shift_pct_points"],
        preservation["qdm_response_pct"] - preservation["raw_response_pct"],
        rtol=0,
        atol=1.0e-12,
    )
    assert (
        preservation["qdm_moved_toward_observed"].astype(bool)
        == (
            preservation["qdm_absolute_error_vs_observed_pct_points"]
            < preservation["raw_absolute_error_vs_observed_pct_points"]
        )
    ).all()
    print("RECONCILE preservation_rows=16 shift_and_observation_error=exact")

    figure_index = pd.read_csv(OUTPUT / "figures" / "Paper3_FIGURE_INDEX.csv")
    table_index = pd.read_csv(OUTPUT / "tables" / "Paper3_TABLE_INDEX.csv")
    assert figure_index["figure"].nunique() == 4 and len(figure_index) == 8
    assert table_index["table"].nunique() == 3 and len(table_index) == 3
    assert all(Path(path).exists() for path in figure_index["path"])
    print("RECONCILE registered_main_figures=4 registered_main_tables=3")

    checksum_rows = []
    for path in sorted(p for p in OUTPUT.rglob("*") if p.is_file() and p.name != "SHA256SUMS.json"):
        checksum_rows.append(
            {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": _sha256(path)}
        )
    (OUTPUT / "SHA256SUMS.json").write_text(
        json.dumps(checksum_rows, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"VALIDATION_COMPLETE files_hashed={len(checksum_rows)}")


if __name__ == "__main__":
    main()

