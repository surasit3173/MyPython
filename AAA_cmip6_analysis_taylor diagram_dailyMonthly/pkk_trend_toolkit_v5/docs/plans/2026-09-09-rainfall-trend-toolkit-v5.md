# Reusable Rainfall Trend Toolkit Version 5 Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fail-closed and reusable rainfall-trend package, verify its statistical methods with tests and independent checks, run the Prachuap Khiri Khan data, and generate traceable results, figures, a workbook, and two DOCX manuscripts from one run manifest.

**Architecture:** Area-specific choices live in a JSON configuration file. The `rainfall_trends` package owns ingestion, quality control, aggregation, inference, simulation, plotting, output manifests, and manuscript generation through explicit functions without import-time side effects. One CLI run writes an immutable run directory keyed by the input and configuration fingerprints; every table, figure, workbook, and manuscript reads that run's results.

**Tech Stack:** Python 3.12, NumPy, pandas, SciPy, matplotlib, python-docx, pytest, and `@oai/artifact-tool` for the final Excel workbook.

## Global Constraints

- Production execution must fail when observational inputs are absent or malformed. Synthetic data are available only through a separate explicit simulation command.
- Support wide daily CSV input with `Year`, `Month`, `Day`, and station columns, plus long input with configurable field names.
- Use complete calendar years, May to October wet seasons, and November to April hydrological dry seasons. Calculate and report station-period completeness before inclusion.
- Analyze every eligible station. Apply Benjamini-Hochberg separately within each declared period and method family and retain raw p-values and adjusted q-values.
- Name the variance-corrected test `HR-MMK-3` and document it as a prespecified three-lag Hamed-Rao variant, not a full all-lag implementation.
- Preserve signed Hamed-Rao variance correction. Reject non-positive correction factors rather than silently clamping them.
- Bootstrap detrended residual blocks on the original time axis with a deterministic seed.
- Compute Monte Carlo false discovery proportion as `V / max(R, 1)` per replicate. Report FDR, FWER, rejection share, Monte Carlo standard error, and interval.
- Keep findings, uncertainty, method disagreement, and recommendations distinct in the manuscripts.
- Do not overwrite the supplied legacy code, archive, data, or DOCX.

---

### Task 1: Input contract and complete-period aggregation

**Files:**
- Create: `src/rainfall_trends/config.py`
- Create: `src/rainfall_trends/io.py`
- Create: `src/rainfall_trends/aggregation.py`
- Create: `tests/test_input_and_aggregation.py`
- Create: `configs/prachuap.json`

**Interfaces:**
- Consumes: observational rainfall path, station metadata path, and `AnalysisConfig`.
- Produces: validated station-day table, metadata table, quality summary, and annual/wet/dry station-period table with expected days, valid days, completeness, and inclusion flag.

- [ ] **Step 1: Add the focused failing tests**

  Test absent rainfall path raises `InputContractError`; wide CSV becomes one row per station-day; invalid dates, duplicate dates, duplicate station IDs, negative rainfall, and unknown station keys fail; 1981 and 2015 dry edge periods fail completeness while 1982-2014 remain eligible for a complete 1981-2014 source.

- [ ] **Step 2: Verify the relevant failure**

  Run: `python -m pytest tests/test_input_and_aggregation.py -q`
  Expected: collection succeeds and tests fail because public input/aggregation functions do not exist.

- [ ] **Step 3: Implement the minimum behavior**

  Implement explicit schema mapping, wide-to-long conversion, key/range validation, and expected-day calendars for each period. Store rainfall as numeric millimetres and station IDs as strings.

- [ ] **Step 4: Verify the focused pass**

  Run the same focused command. Expected: all input and aggregation tests pass.

- [ ] **Step 5: Run the affected integration check**

  Load the supplied CSVs and assert 12 stations, 149016 station-days, 34 complete annual periods per station, 34 complete wet periods per station, and 33 complete dry periods per station.

### Task 2: Trend inference and multiplicity

**Files:**
- Create: `src/rainfall_trends/statistics.py`
- Create: `tests/test_statistics.py`
- Create: `validation/independent_checks.py`

**Interfaces:**
- Consumes: numeric values with explicit time coordinates.
- Produces: `TrendResult` records for MK, HR-MMK-3, PW-MK, and TFPW-MK plus BH q-values.

- [ ] **Step 1: Add the focused failing tests**

  Use literal hand-checked vectors for increasing, decreasing, tied, constant, gapped-time, and short series. Test the Eq. 30 correction factor from fixed detrended rank autocorrelations, significant-lag filtering limited to lags 1-3, non-positive-factor rejection, and BH adjusted p-values including NaNs.

- [ ] **Step 2: Verify the relevant failure**

  Run: `python -m pytest tests/test_statistics.py -q`. Expected: failures identify the absent statistical API.

- [ ] **Step 3: Implement the minimum behavior**

  Implement tie-corrected MK, calendar-aware Sen slope, Hamed-Rao Eq. 29-30 after Sen detrending and rank ACF, raw and trend-free prewhitening, and monotone BH q-values.

- [ ] **Step 4: Verify the focused pass**

  Run the same focused command. Expected: every deterministic statistical test passes.

- [ ] **Step 5: Run the affected integration check**

  Compare standard MK and HR-MMK-3 against independent reference calculations and a separately installed reference package where definitions match; record exact agreements and definition differences.

### Task 3: Residual bootstrap and calibrated simulations

**Files:**
- Create: `src/rainfall_trends/bootstrap.py`
- Create: `src/rainfall_trends/simulation.py`
- Create: `tests/test_bootstrap_and_simulation.py`

**Interfaces:**
- Consumes: explicit time series, seed, block length, replicate count, AR(1) parameter grid, standardized slope grid, station count, and spatial innovation correlation.
- Produces: Sen-slope intervals, Type I error/power rows, and complete-null FDR rows with uncertainty.

- [ ] **Step 1: Add the focused failing tests**

  Test bootstrap determinism, fixed time coordinates, exact output count, positive-trend recovery, stationary AR(1) variance, reproducible simulation, correct global-null FDP, and BH identity on known p-value matrices.

- [ ] **Step 2: Verify the relevant failure**

  Run: `python -m pytest tests/test_bootstrap_and_simulation.py -q`. Expected: failures name the missing public functions.

- [ ] **Step 3: Implement the minimum behavior**

  Resample detrended residual blocks and reconstruct values on the original times. Simulate stationary Gaussian AR(1) series in vectorized batches, with optional equicorrelated innovations across stations.

- [ ] **Step 4: Verify the focused pass**

  Run the same focused command. Expected: deterministic bootstrap and simulation tests pass.

- [ ] **Step 5: Run the affected integration check**

  With phi=0 and a fixed seed, verify Type I error is compatible with the nominal level within its Monte Carlo interval; record that scenario evidence does not establish universal calibration.

### Task 4: Reusable CLI and Prachuap production run

**Files:**
- Create: `src/rainfall_trends/pipeline.py`
- Create: `src/rainfall_trends/cli.py`
- Create: `run_analysis.py`
- Create: `tests/test_pipeline.py`
- Create: `README.md`
- Create: `MAJOR_REVISION_CHANGELOG.md`

**Interfaces:**
- Consumes: `run_analysis.py --config <json> --output-root <directory>`.
- Produces: immutable `runs/<area>_<fingerprint>/` containing CSV tables, figures, validation logs, and `run_manifest.json`; exits non-zero without producing results when validation fails.

- [ ] **Step 1: Add the focused failing tests**

  Test fail-closed CLI exit, deterministic run ID, all-station output coverage, declared BH families, manifest hashes, and refusal to overwrite a mismatched existing run.

- [ ] **Step 2: Verify the relevant failure**

  Run: `python -m pytest tests/test_pipeline.py -q`. Expected: failures identify the absent CLI/pipeline behavior.

- [ ] **Step 3: Implement the minimum behavior**

  Orchestrate input validation, period construction, four-method inference, q-values, bootstrap, simulation, figures, checksums, and environment capture without module-import writes.

- [ ] **Step 4: Verify the focused pass**

  Run the same focused command. Expected: all pipeline tests pass.

- [ ] **Step 5: Run the affected integration check**

  Run Prachuap configuration and independently reconcile station counts, eligible years, core Standard MK values, output row counts, hashes, and declared iteration counts.

### Task 5: Results workbook and visual QA

**Files:**
- Create: `tools/build_results_workbook.mjs`
- Produce: `runs/<run_id>/Prachuap_Rainfall_Trend_Results.xlsx`

**Interfaces:**
- Consumes: final CSV tables and manifest from one immutable run.
- Produces: an Excel workbook with Summary, Data Quality, Network Results, Station Results, Bootstrap CI, Method Simulation, FDR Simulation, and Sources sheets.

- [ ] **Step 1: Author the workbook from reviewed CSVs**

  Use `@oai/artifact-tool`, typed numeric cells, explicit units/formats, compact scientific tables, frozen headers on long sheets, and source URLs in the Sources sheet.

- [ ] **Step 2: Verify calculations and presentation**

  Inspect representative ranges, scan for formula errors, render every sheet, and confirm headers, units, values, tables, and charts are readable without clipping.

### Task 6: Two manuscripts generated from the same run

**Files:**
- Create: `src/rainfall_trends/manuscripts.py`
- Produce: `runs/<run_id>/Article_1_Method_Comparison.docx`
- Produce: `runs/<run_id>/Article_2_Prachuap_Rainfall_Trends.docx`

**Interfaces:**
- Consumes: final run manifest, result tables, and figure paths.
- Produces: one methodological manuscript and one applied manuscript. Every reported number is loaded from the run outputs rather than copied as a constant.

- [ ] **Step 1: Generate structured manuscripts**

  Article 1 reports the short-record calibration-power trade-off and FDR behavior. Article 2 reports data quality, complete periods, network and station estimates, q-values, bootstrap intervals, method sensitivity, limitations, and reproducibility.

- [ ] **Step 2: Render and inspect**

  Run the canonical DOCX renderer for each document, inspect every PNG page, correct pagination/table/figure defects, and rerender until clean.

- [ ] **Step 3: Cross-document assertion**

  Extract DOCX text and verify each headline numeric claim exists in its controlling CSV/manifest and that station count, time window, method labels, and iteration counts agree.

## Externally Observable Decisions

- The original supplied files remain unchanged; version 5 is delivered as a new package.
- The primary applied result table reports all four methods. HR-MMK-3 is the prespecified dependence-aware method, while cross-method disagreement is explicitly labelled as sensitivity rather than concealed.
- Multiplicity families are period-by-method across the 12 stations; network tests are adjusted across the three periods within method.
- The area configuration defaults to equal station weighting. Spatial representativeness is a limitation, not an inferred provincial areal mean.
- Existing run directories are immutable. Repeating an identical configuration reuses the same run ID only when every recorded output hash matches.

