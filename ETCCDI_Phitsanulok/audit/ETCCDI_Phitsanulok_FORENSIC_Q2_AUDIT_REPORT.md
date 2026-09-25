# ETCCDI Phitsanulok — Forensic Q2 Audit

## Executive verdict

**Not yet suitable for Q2 submission and not yet certifiable as calculation-validated.** The archive contains the pipeline and generated outputs, but not the raw CSV used to generate them. The configuration points to an external Windows path. The daily CSV currently attached to this conversation conflicts with the archive audit: it has duplicate dates, missing precipitation values, and ends on 2019-10-31. Therefore the archived numerical results cannot be independently certified until the exact source-data version is resolved.

## Critical findings

1. **Raw-data provenance is incomplete.** The archive's `data/raw/` directory is empty; `config.yaml` points outside the archive.
2. **Source-version conflict.** The currently attached CSV has 21,549 rows, 61 duplicate dates, 244 missing precipitation values, 2016 with 427 rows but 366 unique dates, and 2019 with 304 rows ending 2019-10-31. The archived audit claims zero duplicates, zero missing values and complete 2019.
3. **QC completeness bug.** `src/data_qc.py` uses `len(yr_df)` rather than unique calendar dates. Duplicate observations can therefore inflate completeness.
4. **Autocorrelation rule is incomplete.** SDII has significant ACF at lags 2 and 6; R99p at lag 2. The current MK selection uses only lag 1.
5. **Zero slopes are misclassified.** Exact/near-zero Sen slopes are labelled non-significant decreasing.
6. **Figure 2 CI shading is statistically invalid.** A slope CI is not a pointwise time-series confidence band.
7. **FDR terminology is wrong.** BH controls FDR, not family-wise Type I error.

## ETCCDI method

The core definitions implemented for PRCPTOT, SDII, Rx1day, Rx5day, CDD, CWD, R10mm, R20mm, R50mm, R95p and R99p are broadly aligned with standard precipitation-index definitions. Climdex documents R95p/R99p as annual precipitation above the 95th/99th percentile of wet-day precipitation and documents a 1961–1990 reference period. The project uses 1981–2010; that can be justified as a study-specific baseline, but it should not be called the canonical ETCCDI reference period.

## Figure audit

### Figure 1
Data completeness plot is readable, but remove the title from the image and keep the title in the manuscript caption.

### Figure 2
Useful content but too dense for journal-column viewing. Enlarge/split panels. Remove the shaded slope-CI band. Keep Sen slope line only; report 95% CI numerically.

### Figure 3
Visually polished but the directional encoding is misleading for zero/non-significant slopes. Use a three-state direction encoding and separate statistical significance.

### Figure 4
Potentially the strongest core figure. Keep unit-specific panels, remove the in-image title, and ensure each x-axis carries its unit.

### Figure 5
Useful diagnostic, preferably Supplementary unless the target journal expects the diagnostic in the main article. Align the inference rule with the lags shown.

### Figure 6
Readable but secondary. Move to Supplementary unless retained for a specific scientific purpose.

## Manuscript audit

The DOCX contains duplicate section headings and unresolved author/affiliation placeholders. Several claims should be weakened: “statistically stable”, “no intensification”, and the statement that historical design-flood estimates remain statistically defensible do not follow directly from non-significant monotonic trend tests. Use “no statistically detectable monotonic trend” and distinguish non-detection from stationarity and causal attribution.

## Required Q2 rerun

1. Resolve the exact raw-data version and record SHA-256.
2. Repair QC using unique expected calendar dates.
3. Recalculate all 11 ETCCDI indices from raw daily data.
4. Recalculate R95p/R99p and explicitly document the 1981–2010 baseline choice.
5. Recalculate ACF and a formal serial-dependence diagnostic.
6. Recalculate ordinary MK and a pre-specified autocorrelation-aware method.
7. Recalculate Sen slope and 95% CI.
8. Recalculate BH-FDR.
9. Rebuild all tables from the final statistical objects.
10. Rebuild all figures from those same objects.
11. Remove all in-image figure titles and resolve overlaps/clipping.
12. Rebuild the manuscript and reconcile every reported number against the final tables.
13. Run the entire pipeline twice from the same raw source and compare outputs.

**Do not manually edit numerical results in Excel or the manuscript.** Fix the calculation pipeline and regenerate everything.
