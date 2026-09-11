# PAPER 3 EXECUTION PLAN

This execution plan is structured according to the "EXECUTION ORDER" section of the `Paper3_ENSO_Master_Code_and_Manuscript_Execution_Specification.md` document.

## Phase 1 — Code Audit & Preparation
1. Inspect the existing `config/uttaradit.yaml`, `src/cmip6bc/metrics.py`, seasonal calculations, and QDM implementations.
2. Confirm the common station and model mappings, and observe the QC criteria.
3. **Blocker Resolution:** Resolve LFS permission issues to obtain all raw CMIP6 and observed data, extract `dataUttaradit.rar`, and set up the `data/` directory structure.
4. Verify the python environment (`.venv`) and its dependencies.

## Phase 2 — ENSO Source Acquisition
1. Implement a workaround for the HTTP 403 error to retrieve the pinned NOAA ONI data.
2. Save the raw source file and calculate its SHA-256 hash.
3. Build the `enso_episode_catalog.csv`.
4. Verify selected episodes against the NOAA historical classification.

## Phase 3 — Seasonal Engine Implementation
1. Add new modules (`src/cmip6bc/enso.py`, `src/cmip6bc/seasonal.py`, `config/paper3_enso.yaml`).
2. Implement the definitions for the **Rainy season (May–October)** and the **Hot/dry season (November–April of the following year)**.
3. Unit-test date assignments for cross-year seasons.
4. Generate the season catalogue.

## Phase 4 — ENSO Classification
1. Implement the season-specific classification rule (El Niño, Neutral, La Niña, Transition/Unclassified).
2. Generate the sample-size table and freeze the classification rule.
3. Run the classification sensitivity analysis.

## Phase 5 — Rainfall Analysis (Historical Base)
1. Compute seasonal metrics for the observed dataset (1995–2014).
2. Compute seasonal metrics for the raw CMIP6 data (1995–2014).
3. Apply the frozen QDM parameters.
4. Compute seasonal metrics for the QDM-corrected data.

## Phase 6 — ENSO Response & Signal Preservation
1. Calculate the ENSO responses (El Niño vs. Neutral, La Niña vs. Neutral).
2. Calculate the ENSO asymmetry (`A_LaNina - A_ElNino`).
3. Calculate direction agreement and magnitude error.
4. Calculate the ENSO signal-preservation error (QDM response relative to Raw model response).

## Phase 7 — Statistical Inference
1. Run pre-specified permutation/rank-based tests and bootstrap uncertainty calculations.
2. Ensure sample sizes (`n`) are reported for every comparison.
3. Flag any results with small sample sizes as diagnostic.

## Phase 8 — Synthesis & Gate Verification
1. Produce ensemble, station-level, and model-level summaries.
2. Produce interpretation-status tables based on acceptance gates.
3. Verify all conditions for Paper 3 Acceptance Gates (P3-A through P3-H).

## Phase 9 — Figure Generation
1. Generate Figure 1: Seasonal observed ENSO response.
2. Generate Figure 2: Raw vs. QDM ENSO response.
3. Generate Figure 3: ENSO asymmetry.
4. Generate Figure 4: Extreme rainfall response.
5. Generate Figure 5: Temporal diagnostics.
6. Generate Figure 6: Integrated synthesis heatmap.

## Phase 10 — Manuscript Generation
1. Compile the methods, results, and discussion sections based on the audited tables and verified evidence.
2. Write the Introduction and Abstract based on actual findings.
3. Format the manuscript according to the APST template (`≤15 pages`).

## Phase 11 — Final Audit & Export
1. Run the claim audit, table/figure numerical audit, source/provenance audit, and reference audit.
2. Generate final APST manuscript formats (.docx, .pdf, .md).
3. Generate supplementary files, the `paper3_manifest.json`, and SHA-256 hashes (`paper3_file_hashes.csv`).
