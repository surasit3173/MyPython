# Paper 3 research and execution record

## Frozen design

- Period: 1981–2014; common 365-day analysis calendar after native-calendar observed QC.
- Observations: 13 Uttaradit gauges; ENSO from frozen NOAA CPC ERSSTv6 ONI.
- Models: ACCESS-ESM1-5, CanESM5, CESM2, EC-Earth3, FGOALS-g3, MIROC6, and MRI-ESM2-0. Each model uses exact-member historical `tos` to derive its own Niño-3.4 sequence.
- Seasons: rainy May–October; hot/dry November–April labelled by the November start year.
- Persistent ENSO episode: |anomaly|≥0.5°C for at least five overlapping three-month windows; strict-majority season assignment; transition/mixed seasons excluded.
- Primary endpoints: PRCPTOT, wet-day frequency, Rx1day, and CDD.
- Inference: 5,000 event-level bootstrap repetitions; 4,999 event-label permutations; BH adjustment over 16 primary tests.
- Hierarchy: daily → management season → station → unique raw-grid signature → model → ensemble.

## Technical decisions and deviations

1. The initial QDM run stopped because some calendar-month training sets had fewer than 30 observed and model wet days. The threshold was retained. A configured calibration-only adjacent-three-month pool was implemented; targets remain in the original month. The final run used the fallback in 574/7,644 fits and used zero observations from target folds.
2. Observed zero screening was moved before leap-day deletion because QC on the common-365 calendar changed zero-run adjacency. Native-calendar QC classified 43 station-months as probable missing and set 1,308 daily values to missing; February 29 was dropped only afterward.
3. Station extracts sharing an identical raw precipitation series were collapsed by model-specific grid signature. The number of unique grids across the 13 stations was 2, 1, 3, 5, 2, 2, and 3 for ACCESS-ESM1-5, CanESM5, CESM2, EC-Earth3, FGOALS-g3, MIROC6, and MRI-ESM2-0, respectively.
4. A ±5 percentage-point raw-response gate precedes preservation ratios, preventing unstable amplification labels near zero.
5. Figure 1 retains the complete classification file but excludes hot/dry climate-year 2014 because that season ends in April 2015, outside the daily analysis period.

## Reproducibility evidence

- Full pipeline: `scripts/run_paper3.py`; analysis mode `full_frozen`; 8/8 acceptance gates passed.
- Tests: `python -m unittest discover -s paper3_execution/tests -v`; 17 tests passed.
- Notebook: `notebooks/Paper3_reproducible_analysis.ipynb`; executed top-to-bottom with isolated local IPython/Jupyter directories.
- Result reconciliation: `scripts/validate_results.py`; all 48 primary response rows and all 16 preservation rows reconciled.
- Manuscript reconciliation: `scripts/validate_manuscript.py`; 105 numerical checks passed.
- Manuscript render: Microsoft Word PDF export; A4; 15 pages; all 15 page renders inspected, including table and figure pages.

## Source note

The official Chiang Mai Journal of Science author guide (revised 23 January 2025) specifies English Research Papers, A4 single-column Calibri 11-point double-spaced text, no more than five tables and five figures, tables and figures at the end, and double-blind submission. The prepared manuscript has three tables, four figures, and a separate blinded DOCX/PDF.
