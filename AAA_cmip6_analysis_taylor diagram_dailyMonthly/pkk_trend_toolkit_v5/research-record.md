# Research Record for Rainfall Trend Toolkit Version 5

## Frozen plan

### Question

Can a new reusable package analyze the supplied Prachuap Khiri Khan daily rainfall data with fail-closed provenance, complete-period aggregation, academically traceable MK-family inference, correct multiplicity and bootstrap procedures, reproducible simulations, and internally consistent tables, figures, workbook, and DOCX manuscripts?

### Hypotheses and falsifiers

- H1 Input integrity. Prediction: only explicitly supplied observational files enter production, all 12 station keys reconcile, and incomplete dry edge seasons are excluded. Falsifier: synthetic fallback, silent schema coercion, dropped stations, or inclusion of incomplete edge periods.
- H2 Statistical implementation. Prediction: Standard MK, Sen slope, HR-MMK-3, PW-MK, TFPW-MK, BH q-values, and FDP match hand-worked or independent reference calculations under their declared definitions. Falsifier: a statistic or decision differs outside stated numeric tolerance.
- H3 Bootstrap and simulation. Prediction: the bootstrap keeps the original time index and seeded runs are deterministic; complete-null FDR uses FDP per replicate. Falsifier: reordered time, non-reproducibility, or FDR derived from mean rejection share.
- H4 Production results. Prediction: all eligible stations and periods appear, core Standard MK values reproduce the independent audit, and every table/figure records its sample and method definition. Falsifier: missing stations, partial periods, or mismatched counts/numbers.
- H5 Artifact consistency. Prediction: workbook and manuscripts load values from the immutable run outputs, render cleanly, and agree with the manifest. Falsifier: copied stale values, missing figures, clipped content, or inconsistent run metadata.

### Confirmatory methods

- C1 Red-green tests for fail-closed ingestion and wide/long normalization.
- C2 Red-green tests for complete annual, wet, and hydrological dry periods.
- C3 Red-green tests for MK-family statistics and calendar-aware Sen slope.
- C4 Red-green tests for BH adjusted p-values and global-null FDP/FDR.
- C5 Red-green tests for residual block bootstrap and seeded AR(1) simulation.
- C6 End-to-end Prachuap run with independent reconciliation of counts and headline results.
- C7 Independent reference comparison for standard MK, HR-MMK-3, and BH where method definitions match.
- C8 Workbook structural, formula-error, and visual checks.
- C9 DOCX content reconciliation plus render and inspection of every page.

### Exploratory methods

- E1 Compare method-specific significance patterns and simulation trade-offs. These observations may guide interpretation but cannot redefine the prespecified primary method or multiplicity family.

### Stopping rules

Stop only when C1-C9 are closed; every requested artifact exists; focused and full tests pass; the production run completes from the supplied observational inputs; all final tables and figures reconcile to the run manifest; the workbook and both DOCX files pass visual inspection; and an independent reference pass returns confirmed or partially confirmed rather than inconclusive.

## Evidence log

Evidence will be appended after implementation starts. Earlier entries will not be edited or removed.

### 2026-09-09 literature and implementation contract

- Runtime baseline: Python 3.12.14, NumPy 2.3.5, pandas 3.0.1, python-docx 1.2.0, Pillow 12.3.0. Matplotlib, SciPy, and pytest were not initially present and are declared in the reproducible environment files.
- Hamed and Rao (1998), Journal of Hydrology 204, 182-196, DOI 10.1016/S0022-1694(97)00125-X: the ordinary MK null assumes independent random ordering; positive serial correlation can increase false trend detection; their method modifies the variance. Publisher landing/PDF: https://www.sciencedirect.com/science/article/pii/S002216949700125X
- Benjamini and Hochberg (1995), JRSS B 57, 289-300, DOI 10.1111/j.2517-6161.1995.tb02031.x: FDR is the expected false-discovery proportion and equals FWER under the complete null. Publisher PDF: https://rss.onlinelibrary.wiley.com/doi/pdf/10.1111/j.2517-6161.1995.tb02031.x
- Yue and Wang (2002), Water Resources Research 38(6), DOI 10.1029/2001WR000861: ordinary prewhitening can remove part of a positive trend, motivating explicit method sensitivity rather than treating prewhitening as neutral. Publisher page: https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2001WR000861
- The production contract therefore keeps raw MK, prespecified HR-MMK-3, PW-MK, and TFPW-MK distinct; retains signed HR correction; computes FDP replicate by replicate; and never substitutes generated observations for missing production inputs.

### 2026-09-09 TDD red phase for Tasks 1-3

- `python -m pytest tests/test_input_and_aggregation.py -q`: 8 failed, all at the deliberate `NotImplementedError` boundaries after successful collection.
- `python -m pytest tests/test_statistics.py -q`: 6 failed, all at the deliberate `NotImplementedError` boundaries after successful collection.
- `python -m pytest tests/test_bootstrap_and_simulation.py -q`: 4 failed, all at the deliberate `NotImplementedError` boundaries after successful collection.
- This establishes that the assertions exercised absent behavior rather than passing against legacy or accidental implementations.

### 2026-09-09 TDD green phase for Tasks 1-3 core APIs

- `python -m pytest tests/test_input_and_aggregation.py -q`: 8 passed, including the supplied 12-station file and the expected 34 annual, 34 wet, and 33 complete dry periods per station.
- `python -m pytest tests/test_statistics.py -q`: 6 passed, including tie variance, real-time Sen slope, signed HR correction, non-positive-factor rejection, and BH literals.
- `python -m pytest tests/test_bootstrap_and_simulation.py -q`: 4 passed, including deterministic residual bootstrap, stationary seeded AR(1), replicate-level FDP, and Wilson interval.

## Deviations dead ends and pivots

- The canonical DOCX renderer could not start because LibreOffice `soffice.exe` was absent. The fallback used Microsoft Word 2024 background PDF export followed by Poppler rasterization. All 4 pages of Article 1 and all 5 pages of Article 2 were visually inspected after a pagination correction.
- The first workbook preview exposed an artifact-tool `COUNTIF` issue on Boolean cells: the summary displayed zero station decisions although the controlling CSV contained seven. The summary count was replaced by a direct typed value computed from the same parsed CSV; the workbook was rebuilt, rerendered, and revalidated.
- The station-location figure initially clipped a northeast station label and did not explicitly symbolize missing elevation. Axis padding and a gray-x missing-elevation layer were added before final manuscript generation.

### 2026-09-10 production and artifact evidence

- Production run: `prachuap-khiri-khan_e8bf031b3ba0`; observational input only; 12 stations; 149,016 station-days; 0 missing rainfall, 0 negative rainfall, and 0 duplicate station-days; 4 missing elevations retained as metadata gaps.
- Complete periods per station: 34 annual, 34 wet, and 33 dry. Partial dry labels 1981 and 2015 were excluded.
- Independent executable check: verdict `confirmed`. Standard MK S, Kendall tau, Sen slope, and p-value matched `pymannkendall` for annual, wet, and dry network series. The independent BH literal matched exactly.
- Network MK results: annual slope +0.8302 mm/year, p=0.7443, q=0.7443; wet slope -1.3814, p=0.5142, q=0.7443; dry slope +3.4644, p=0.08264, q=0.2479. No network period-method test survived BH.
- Station results: seven method-specific BH decisions across three station-period combinations and two stations. They were station 500002 annual under HR-MMK-3, plus dry at stations 500002 and 500006 under MK, HR-MMK-3, and TFPW-MK. PW-MK had no station discovery. The annual 500002 HR result used a variance factor of 0.247 after selecting lag 2 and was flagged as method-sensitive variance deflation.
- Network residual-block bootstrap intervals: annual -4.510 to +6.395, wet -6.047 to +3.144, dry +0.682 to +6.437 mm/year. The dry interval/test disagreement is disclosed rather than resolved by selective interpretation.
- Calibration at phi=0 for n=33: MK 0.0505, HR-MMK-3 0.0746, PW-MK 0.0466, TFPW-MK 0.0559. At phi=0.4: 0.1717, 0.1552, 0.0455, and 0.2013, respectively. Therefore no universal validity claim is made for HR-MMK-3 or TFPW-MK.
- Complete-null BH scenario with phi=0.4 and innovation rho=0.3: FDR/FWER were 0.3792 MK, 0.3992 HR-MMK-3, 0.0098 PW-MK, and 0.4664 TFPW-MK. Mean rejection share was stored separately. This shows that BH did not repair miscalibrated marginal p-values in the prespecified scenario.
- `python -m pytest -q`: 23 passed.
- Cross-artifact validator: 51 passed, verdict `confirmed`; workbook has eight rendered sheets and no formula errors; manuscript counts, slopes, iterations, station decisions, figures, and rendered page counts reconcile to the controlling CSVs.

## Final verdict

Confirmed within the frozen scope. C1-C9 are closed. The supplied observational inputs were analyzed without fallback; deterministic tests and an independent package corroborated the matching definitions; requested tables, figures, workbook, and two DOCX manuscripts were generated from one run; and all artifacts passed structural, numerical, and visual checks. Scientific conclusions remain deliberately method-sensitive because the prespecified simulation falsified any universal calibration claim for the candidate dependence corrections.
