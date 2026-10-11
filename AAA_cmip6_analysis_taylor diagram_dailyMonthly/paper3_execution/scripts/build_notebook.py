"""Build the reader-facing reproducibility and numerical-audit notebook."""

from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "notebooks" / "Paper3_reproducible_analysis.ipynb"

notebook = nbf.v4.new_notebook()
notebook["metadata"].update(
    {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12"},
        "paper3_role": "reader-facing audit of frozen outputs",
    }
)
notebook["cells"] = [
    nbf.v4.new_markdown_cell(
        """# Paper 3 reproducible analysis and numerical audit

This notebook reads the frozen daily-to-season pipeline outputs, verifies the acceptance gates and sample hierarchy, and independently recomputes one headline response. The full daily analysis is executed by `scripts/run_paper3.py`; no hidden notebook state is required."""
    ),
    nbf.v4.new_code_cell(
        """from pathlib import Path
import json
import sys
import pandas as pd
import numpy as np
import yaml

ROOT = Path.cwd().resolve()
assert (ROOT / "config" / "paper3_enso.yaml").exists(), "Execute with paper3_execution as working directory"
sys.path.insert(0, str(ROOT / "src"))
from paper3core.statistics import observed_response

config = yaml.safe_load((ROOT / "config" / "paper3_enso.yaml").read_text(encoding="utf-8"))
OUTPUT = ROOT / "output"
config["study"]"""
    ),
    nbf.v4.new_markdown_cell("## Acceptance gates and frozen provenance"),
    nbf.v4.new_code_cell(
        """gates = pd.read_csv(OUTPUT / "PAPER3_ACCEPTANCE_GATES.csv")
display(gates[["gate", "description", "status"]])
assert len(gates) == 8 and (gates["status"] == "PASS").all()

manifest = json.loads((OUTPUT / "paper3_run_manifest.json").read_text(encoding="utf-8"))
assert manifest["analysis_mode"] == "full_frozen"
manifest"""
    ),
    nbf.v4.new_markdown_cell("## ENSO phase sample sizes"),
    nbf.v4.new_code_cell(
        """sample_sizes = pd.read_csv(OUTPUT / "enso_phase_sample_sizes.csv")
observed_samples = sample_sizes[sample_sizes["source_type"] == "OBSERVED"]
display(observed_samples)
assert observed_samples.groupby("season_type")["n_seasons"].sum().to_dict() == {"HOT_DRY": 33, "RAINY": 34}"""
    ),
    nbf.v4.new_markdown_cell("## Independent recomputation of a headline response"),
    nbf.v4.new_code_cell(
        """long = pd.read_csv(OUTPUT / "seasonal_metrics_long.csv.gz")
subset = long[
    (long["source_type"] == "OBSERVED")
    & (long["season_type"] == "RAINY")
    & (long["metric"] == "PRCPTOT")
]
recomputed, station_rows = observed_response(
    subset,
    phase="EL_NINO",
    minimum_seasons=config["enso"]["minimum_seasons_for_composite"],
)
saved = pd.read_csv(OUTPUT / "primary_response_summary.csv")
saved_value = saved.loc[
    (saved["source_type"] == "OBSERVED")
    & (saved["season_type"] == "RAINY")
    & (saved["metric"] == "PRCPTOT")
    & (saved["phase"] == "EL_NINO"),
    "response_pct",
].iloc[0]
print({"recomputed_pct": recomputed["response_pct"], "saved_pct": saved_value})
assert np.isclose(recomputed["response_pct"], saved_value, rtol=0, atol=1e-10)
display(station_rows.head())"""
    ),
    nbf.v4.new_markdown_cell("## Primary response, preservation, and asymmetry tables"),
    nbf.v4.new_code_cell(
        """responses = pd.read_csv(OUTPUT / "primary_response_summary.csv")
preservation = pd.read_csv(OUTPUT / "qdm_enso_signal_preservation.csv")
asymmetry = pd.read_csv(OUTPUT / "enso_asymmetry_primary.csv")
display(responses[["source_type", "season_type", "metric", "phase", "response_pct", "ci_low_pct", "ci_high_pct", "permutation_p_bh_primary"]])
display(preservation[["season_type", "metric", "phase", "category", "qdm_moved_toward_observed"]])
display(asymmetry[["source_type", "season_type", "metric", "phase_contrast_pct", "neutral_centered_asymmetry_pct"]])"""
    ),
    nbf.v4.new_markdown_cell("## Figure registry"),
    nbf.v4.new_code_cell(
        """figures = pd.read_csv(OUTPUT / "figures" / "Paper3_FIGURE_INDEX.csv")
display(figures)
assert len(figures) == 8 and (figures["bytes"] > 0).all()
assert figures["figure"].nunique() == 4"""
    ),
]

nbf.write(notebook, TARGET)
print(f"NOTEBOOK_BUILT {TARGET}")

