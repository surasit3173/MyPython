# Research Record: Paper 3 ENSO Execution

## Frozen pre-evidence plan

### Question

Are the new master specification, source archive, and Uttaradit data archive complete and internally consistent enough to execute a scientifically defensible Paper 3 on ENSO-conditioned rainfall change, and what exact scope, corrections, and deliverables should be confirmed before analysis begins?

### Hypotheses and falsifiers

- **P3-H1 — The new archives close the raw-data and provenance gaps identified in the prior review.** Prediction: the archives contain gauge daily data, CMIP6 daily precipitation, model/member/grid/version metadata, ENSO/SST inputs or a reproducible acquisition method, and a run manifest. Falsifier: one or more required inputs remain absent or cannot be linked to reported outputs.
- **P3-H2 — The master specification defines one coherent, testable primary scientific question compatible with a 15-page article.** Prediction: outcomes, exposures, periods, validation, uncertainty, figures, and stop conditions are mutually consistent. Falsifier: conflicting definitions, excessive endpoints, or incompatible periods/methods require a scope decision.
- **P3-H3 — The supplied code can be executed in the present workspace after bounded, identifiable repairs.** Prediction: dependencies are available or installable, file paths can be parameterized, inputs have supported formats/calendars, and smoke tests expose no unbounded redesign. Falsifier: core data formats are unreadable, key inputs are missing, or results depend on undocumented external state.
- **P3-H4 — A defensible article can fit within 15 pages by making one compound ENSO–rainfall risk metric primary and moving secondary diagnostics to Supplement.** Prediction: a page budget with no more than five main figures and four main tables preserves essential validation and uncertainty. Falsifier: required evidence cannot fit without suppressing validity checks or exceeding 15 pages.

### Planned methods

- **P3-M1 (confirmatory):** Hash and safely inventory the Markdown, ZIP, and RAR; reject traversal/duplicate archive members before extraction.
- **P3-M2 (confirmatory):** Read the master specification completely as evidence, not instructions; extract every claimed input, output, metric, period, model, scenario, validation rule, and acceptance gate into a consistency matrix.
- **P3-M3 (confirmatory):** Profile all supplied structured data at the actual grain: schemas, row counts, date coverage, calendars, units, missingness, duplicates, station/model/scenario/member completeness, and join integrity.
- **P3-M4 (confirmatory):** Inventory code, environment files, tests, hard-coded paths, and provenance controls; run non-mutating compile/import/help checks where possible.
- **P3-M5 (confirmatory):** Compare the executable package with the previously reviewed Uttaradit framework and with current primary literature needed for the proposed method.
- **P3-M6 (confirmatory):** Produce a pre-execution decision brief stating scope, blockers, proposed changes, optional extensions, page budget, deliverables, and explicit go/no-go conditions.
- **P3-M7 (post-confirmation):** Only after the requested review gate is cleared, implement and execute the analysis, then write and visually verify the ≤15-page manuscript.

### Stopping rules

The pre-execution phase stops after all three inputs are hashed and inventoried, the specification is fully read, data/code feasibility is classified, every material conflict or missing dependency is reported, and a bounded execution scope is proposed. No scientific result will be claimed from filenames, manuscript prose, or derived tables alone. The implementation phase will not start during the pre-execution review gate unless the user explicitly confirms the scope after receiving the summary.

## Evidence log (append-only)

- **P3-E001 — frozen local inputs (2026-08-31).** Master specification: 42,847 bytes, 1,966 lines, SHA-256 `BA97C6219DBD423F34FBF33BE91234EB7904698A1FBB5F737576E88F42F3E693`; `files (21).zip`: 18,610,569 bytes, SHA-256 `B4C530057CB2A62EB6824508BB00D4BB28836B0CA45D904A9433653D1CF947CA`; `dataUttaradit.rar`: 58,733,469 bytes, SHA-256 `BC1B651314F9E62D664775E49BC3A8B907769F6B3B3D4CF69C2EDF2E5DDD01D6`. ZIP, RAR, and nested framework ZIP contained no absolute/traversal paths and no duplicate member names before extraction.
- **P3-E002 — supplied data inventory.** The RAR contains 44 CSVs: two byte-identical observation copies, 21 raw precipitation files (seven models × historical/SSP2-4.5/SSP5-8.5), and 21 legacy `bc_` files. It also contains two byte-identical station-coordinate workbooks and one shapefile component set. The 21 expected raw model/scenario pairs are complete. No material missing, duplicate-date, internal date-gap, or negative-precipitation problem was found. All raw files have a terminal empty column; five contain only floating-point negatives greater than `-1e-6`, which must be normalized under a logged tolerance. Historical calendars mix Gregorian and no-leap.
- **P3-E003 — observational quality and completeness.** The gauge file has 12,418 complete Gregorian dates from 1981-01-01 through 2014-12-31, 13 stations, no non-finite or negative values, 49.31% zero-rain days, and a 298.5 mm maximum. Existing strict-QC logic diagnoses 43 probable-missing, 80 uncertain, 315 confirmed-zero, and 4,866 not-zero station-months. Under the probable-missing mask, May–October 1995–2014 has 258/260 complete station-seasons; November–April 1995/96–2013/14 has 226/247. Analysis therefore requires explicit per-station season completeness and sample-size reporting.
- **P3-E004 — spatial independence.** Although there are 13 gauges, the raw model columns collapse to only 1–5 distinct daily series per model (CanESM5 1; ACCESS-ESM1-5 and FGOALS-g3 2; CESM2 and MRI-ESM2-0 3; EC-Earth3 5; MIROC6 2). Stations mapped to the same grid cell cannot be treated as independent model samples; weighting/aggregation must use unique grid signatures before the model ensemble.
- **P3-E005 — executable framework.** The nested framework compiles, but has no automated tests and its core analysis modules are unchanged from the earlier audited version. Previously reproduced defects therefore remain: spells can bridge missing dates; artificial 29 February insertion can corrupt no-leap rolling/spell indices; tied values receive a last-rank rather than mid-rank in QDM; completeness and acceptance-gate checks are incomplete. `shapely`, `pyproj`, `pyarrow`, `geopandas`, and `fiona` are absent from the bundled environment. The legacy `bc_` files lack sufficient provenance and the framework itself is designed to recompute bias correction from raw files.
- **P3-E006 — central scientific design blocker.** CMIP6 historical coupled simulations are free-running; their internally generated ENSO events are not synchronized to observed calendar-year events. Eyring et al. describe expected historical-model/observation differences from unforced variability (`https://gmd.copernicus.org/articles/9/1937/2016/`, retrieved 2026-08-31). Peer-reviewed CMIP ENSO studies identify events from each simulation's own Niño-3.4 SST series (`https://journals.ametsoc.org/view/journals/clim/33/23/jcliD191004.xml` and `https://journals.ametsoc.org/view/journals/clim/36/16/JCLI-D-22-0826.1.xml`, retrieved 2026-08-31). Applying NOAA observed ENSO-year labels to these seven model rainfall series would not test simulated ENSO teleconnections. The archive contains precipitation but no model `tos`/Niño-3.4 input, so the primary design requires acquisition of monthly historical `tos` for each exact model/member/grid or a weaker reframing.
- **P3-E007 — classification source and temporal scope.** The current official CPC ONI page is ERSSTv6 and retains the ±0.5 °C, five-overlapping-season episode criterion (`https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v6/`, retrieved 2026-08-31); the master specification's version must be frozen. The actual observation/model historical overlap is 1981–2014, not merely 1995–2014. Using 1981–2014 gives 34 rainy seasons and 33 complete cross-year hot/dry seasons and is more defensible for rare ENSO-phase estimation, provided QDM is evaluated with blocked cross-fitting so target seasons are out of fold.
- **P3-E008 — internal specification conflicts.** The proposed 1995–2014 evaluation overlaps the fixed 1981–2002 QDM calibration in 1995–2002, contradicting the stated no-target-year leakage rule. The 2014/15 hot/dry season cannot be completed by historical data ending 2014-12-31. The expression labelled ENSO asymmetry, `(X_La-X_N)-(X_El-X_N)`, simplifies to `X_La-X_El` and is a phase contrast, not neutral-centered asymmetry. The relative preservation error is unstable when the raw response is near zero. Six main figures plus six tables is incompatible with a robust 15-page paper after methods, references, and uncertainty reporting.
- **P3-E009 — bounded revised design.** A viable primary question is whether QDM preserves each model's own seasonal ENSO-conditioned precipitation response at local scale, benchmarked against observed responses classified by CPC ONI. Use blocked cross-fitted QDM; exact date adjacency on a common 365-day analysis calendar; season/event-level permutation or cluster bootstrap; unique-grid-signature and model weighting; four preregistered primary outcomes (PRCPTOT, wet-day frequency, Rx1day, CDD); absolute response shift and sign preservation as primary preservation measures; a true neutral-centered asymmetry statistic; remaining metrics as multiplicity-controlled secondary/Supplement; and four main figures plus three tables.

## Dead ends

- `7z` was unavailable; archive listing/extraction was completed with `bsdtar` after safety checks.
- LibreOffice was unavailable for later DOCX rendering. Microsoft Word is installed, so visual export can be attempted after manuscript generation; otherwise structural checks and the rendering limitation must be disclosed.

## Pivots and deviations

- **Required scientific pivot:** replace observed-calendar ENSO labels on free-running CMIP6 precipitation with model-specific Niño-3.4/ONI-like labels from the matching historical SST simulation. NOAA ONI remains the observation label source.
- **Recommended period pivot:** use the verified common historical span 1981–2014, with 33 complete hot/dry seasons, instead of an unnecessarily short 1995–2014 core.
- **Recommended validation pivot:** use blocked cross-fitted QDM for leakage-free primary inference and retain the fixed Paper 1 calibration only as a sensitivity analysis.

## Verification verdict

- **P3-H1 rejected:** precipitation and gauge data are present, but model-specific SST/ENSO inputs and complete ESGF version/extraction provenance are absent.
- **P3-H2 partially supported:** the ENSO-signal-preservation question is coherent, but the frozen specification contains material classification, leakage, period, metric, and page-budget conflicts that require the bounded revision above.
- **P3-H3 partially supported:** the framework is readable and compiles, but identified numerical/calendar/completeness defects, absent tests, and some missing dependencies must be corrected in an isolated Paper 3 workspace before scientific execution.
- **P3-H4 supported after scope reduction:** a defensible article can fit 15 pages with four primary endpoints, four main figures, three main tables, and secondary material moved to Supplement.
- Independent verification is not closed at this pre-execution gate because the current coordination policy does not permit dispatching an independent reviewer without an explicit user request. All local evidence above was self-checked against generated inventories and primary sources; final completion claims will require a fresh verification pass.

## Approved execution addendum (frozen 2026-09-01 before scientific runs)

The user approved the revised design and directed all subsequent Paper 3 analysis to use the files under `C:\MyPython\CMIP6Uttaradit\paper3`. The attached `แนวทาง paper3.docx` independently confirms the same six non-negotiable design gates. It is treated as source evidence, not as session-level instructions.

### Primary confirmatory question

Does blocked cross-fitted quantile delta mapping preserve the direction and magnitude of seasonal, model-specific ENSO-conditioned daily precipitation responses over Uttaradit during 1981–2014?

### Frozen execution protocol

- **P3-X1 — source matching.** Use historical monthly `tos` from the same CMIP6 source model and variant label as each historical `pr` file. Ocean and atmosphere grid labels may differ across realms; this is allowed only when the source model and variant label match exactly and the ocean grid is the published grid for that `tos` dataset. Save the catalog snapshot, exact Zarr path, version, attributes, and hash of every derived index.
- **P3-X2 — model Niño-3.4.** Calculate an ocean-cell-area-weighted monthly SST mean over 5°S–5°N, 170°W–120°W. For 1981–2014, subtract the 1981–2010 calendar-month climatology, remove the fitted linear trend from the monthly anomaly series, and calculate a centered three-month mean. Primary warm/cold episode membership requires an index of at least +0.5 °C or at most -0.5 °C for at least five consecutive overlapping three-month seasons. A standardized-amplitude threshold is sensitivity-only.
- **P3-X3 — observed ENSO.** Freeze and archive the NOAA CPC ERSSTv6 ONI table. Use CPC's published ±0.5 °C and five-overlapping-season episode definition. Keep episode membership separate from within-season ONI mean/minimum/maximum.
- **P3-X4 — management-season classification.** Rainy seasons are May–October of each calendar year; hot/dry seasons are November–April labelled by the November start year. Assign El Niño or La Niña only when a strict majority of the overlapping three-month index windows belong to one persistent episode of that sign. Assign Neutral when no persistent warm/cold episode overlaps and the evidence remains within threshold. Mixed or tied evidence is Transition/Unclassified. This rule is fixed before rainfall-response results are inspected.
- **P3-X5 — calendar and completeness.** Drop 29 February from Gregorian observations/models for the primary common-365-day analysis and never insert synthetic dates. Rolling and spell metrics require exact consecutive dates and break at missing/QC-excluded dates. A station-season is complete only if every expected daily value remains after the probable-missing QC mask. Report per-source and per-phase sample sizes.
- **P3-X6 — bias correction.** Use leave-one-block-out blocked cross-fitted QDM as primary. Blocks are consecutive five-year climate-year groups (1981–1985, 1986–1990, 1991–1995, 1996–2000, 2001–2005, 2006–2010, 2011–2014); all target days are excluded from their calibration fold. Fit by calendar month and station/grid signature using empirical distributions, explicit mid-ranks for ties, wet-day frequency adjustment, a multiplicative precipitation QDM transform above the wet threshold, and a bounded dry/tail rule documented in code. Paper 1's fixed 1981–2002 QDM is sensitivity-only.
- **P3-X7 — endpoints and hierarchy.** Primary endpoints are PRCPTOT, wet-day frequency, Rx1day, and CDD. Secondary metrics (Rx5day, R20, R50, R95p, R99p, CWD, and selected quantiles) go to Supplement with Benjamini–Hochberg control where inferential tests are reported. Preserve the hierarchy daily → season → station → unique model-grid signature → model → ensemble; never count stations sharing one model series as independent model realizations.
- **P3-X8 — contrasts and uncertainty.** Estimate phase responses relative to Neutral, phase contrast `(La Niña response - El Niño response)`, and true neutral-centered asymmetry `(La Niña response + El Niño response)`. Primary preservation measures are absolute response shift, sign preservation, and preserved/attenuated/amplified/reversed categories. Resample/permutate at the season or ENSO-episode level; do not resample daily rows as independent observations. Report effect sizes and 95% intervals; avoid causal language.
- **P3-X9 — bounded manuscript.** Limit the main paper to four figures, three tables, and 15 pages including references; place station/model detail, secondary endpoints, sensitivity checks, and full provenance in Supplement.

### Confirmatory execution tests and falsifiers

- **P3-C1:** all seven exact source/variant `tos` datasets and usable cell areas resolve. Falsifier: any source/variant cannot be matched; scientific analysis stops rather than substituting another realization.
- **P3-C2:** synthetic calendar, gap, QDM-tie, wet-day, fold-leakage, and grid-signature tests pass. Falsifier: any test fails after bounded repair; no manuscript claim is generated from affected outputs.
- **P3-C3:** every phase/source/season estimate has a reported effective sample size and no duplicated grid signature contributes extra ensemble weight. Falsifier: any untraceable or duplicated contribution remains.
- **P3-C4:** headline values recompute from saved machine-readable tables and all figure data match those tables. Falsifier: a material discrepancy remains after one targeted repair.
- **P3-C5:** the final manuscript renders to no more than 15 pages without clipped or missing content. Falsifier: the page or visual QA gate fails.

### Execution stopping rules

Stop before rainfall analysis if exact source/variant SST matching fails. Stop before inference if the primary software tests fail. Stop before manuscript finalization if sample-size gates, source provenance, independent result recomputation, or claim-to-table traceability remain unresolved. Report a scientifically honest blocked or caveated result rather than silently weakening any gate.
