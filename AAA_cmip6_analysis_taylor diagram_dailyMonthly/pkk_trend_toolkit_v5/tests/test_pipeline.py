from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from rainfall_trends.pipeline import (
    PipelineError,
    apply_bh_families,
    build_run_id,
    validate_existing_run,
)


def test_run_id_is_deterministic_and_content_sensitive(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    rainfall = tmp_path / "rain.csv"
    metadata = tmp_path / "stations.csv"
    config.write_text('{"area_name":"Example"}', encoding="utf-8")
    rainfall.write_text("a\n1\n", encoding="utf-8")
    metadata.write_text("b\n2\n", encoding="utf-8")
    first = build_run_id("Example Area", config, [rainfall, metadata])
    second = build_run_id("Example Area", config, [rainfall, metadata])
    assert first == second
    rainfall.write_text("a\n3\n", encoding="utf-8")
    assert build_run_id("Example Area", config, [rainfall, metadata]) != first
    assert first.startswith("example-area_")


def test_station_and_network_bh_families_are_declared() -> None:
    station = pd.DataFrame(
        {
            "station_id": ["A", "B", "A", "B"],
            "period": ["annual", "annual", "wet", "wet"],
            "method": ["MK"] * 4,
            "p_value": [0.01, 0.04, 0.01, 0.20],
        }
    )
    got_station = apply_bh_families(station, alpha=0.05)
    assert got_station["family"].tolist() == ["station|annual|MK"] * 2 + ["station|wet|MK"] * 2
    assert got_station["q_value"].tolist() == pytest.approx([0.02, 0.04, 0.02, 0.20])

    network = station.iloc[[0, 2]].drop(columns="station_id")
    got_network = apply_bh_families(network, alpha=0.05, network=True)
    assert got_network["family"].tolist() == ["network|MK", "network|MK"]
    assert got_network["q_value"].tolist() == pytest.approx([0.01, 0.01])


def test_existing_run_rejects_modified_output(tmp_path: Path) -> None:
    output = tmp_path / "table.csv"
    output.write_text("x\n1\n", encoding="utf-8")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    (tmp_path / "run_manifest.json").write_text(
        json.dumps({"outputs": {"table.csv": {"sha256": digest}}}), encoding="utf-8"
    )
    validate_existing_run(tmp_path)
    output.write_text("x\n2\n", encoding="utf-8")
    with pytest.raises(PipelineError, match="hash mismatch"):
        validate_existing_run(tmp_path)
