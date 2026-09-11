# Major revision changelog

## Correctness and provenance

- Removed silent synthetic fallback from production analysis.
- Added explicit wide/long schemas and fail-closed validation.
- Reconciled all 12 station identifiers and preserved station IDs as strings.
- Recognized the supplied elevation field and retained `NS` as documented missing metadata.
- Added SHA-256 fingerprints for observational inputs and outputs.

## Aggregation

- Replaced partial dry-season endpoints with complete November–April hydrological seasons.
- Added expected days, valid days, completeness, period bounds, and inclusion flags for every station-period candidate.
- Analyzed 34 annual, 34 wet, and 33 complete dry periods per station.

## Inference

- Reimplemented tie-corrected MK and calendar-aware Sen slope.
- Replaced the legacy variance correction with a named HR-MMK-3 definition: Sen detrending, residual ranks, significant lags 1–3, signed correction, and explicit rejection of non-positive factors.
- Separated raw prewhitening from trend-free prewhitening and retained the original-series Sen effect estimate.
- Applied BH to declared station period-by-method families and to network period families within method.
- Corrected FDR to mean replicate-level FDP instead of mean rejection share.

## Uncertainty and calibration

- Replaced raw-level block resampling with residual-block reconstruction on the original time axis.
- Added stationary Gaussian AR(1) Type I error and raw-power scenarios with Wilson intervals and MCSE.
- Added a complete-null BH experiment with temporal and spatial dependence, FDR, FWER, mean rejection share, and undefined-series counts.

## Outputs

- Added immutable run tables, figures, environment metadata, and validation evidence.
- Added an artifact-tool XLSX workbook with eight styled and rendered sheets.
- Added two DOCX manuscripts generated from the same CSV outputs: a method comparison and an applied Prachuap Khiri Khan analysis.
- Added 23 unit tests and an executable independent validation against `pymannkendall` where definitions match.
