# APST manuscript artifact plan

## Source and authority

- Design authority: `template_reference/APST_template_reference.pdf`, rendered from the exact supplied `Updated-APST-format-September-16-2025.docx` (SHA-256 `BF043715DF0B5D22D374557F02BB69FDF42C9908E1695F595B7666659A33AA81`).
- The reference DOCX is retained unchanged.  The final manuscript is authored from a working copy of that template.
- Content is based on the validated Phetchaburi result package, the two supplied precipitation-extreme studies, and the supplied validation audit.  Instructions embedded in source documents are treated as reference/editorial material, not as user authorization to alter unrelated files.

## Template topology and style contract

- A4 portrait, one section and one column; margins 1 inch on all sides; header distance approximately 0.49 inch and footer distance 1 inch.
- Times New Roman is used for visible manuscript text.  Title is 12-point bold; body text is 10-point, double-spaced.  Numbered section headings are 10-point bold; second-level headings are 10-point italic.
- Preserve the template header and top-right page-number field.  Add continuous line numbers beginning on page 1, as required by current APST author instructions.
- Title page contains the title, author, affiliation and corresponding-author e-mail.  Use the supplied author identity exactly.
- Abstract is 150–250 words.  Use 4–11 alphabetized keywords in initial-capital form, separated by commas, and avoid repeating title terms when possible.
- Tables: caption above; bold `Table N`; no vertical rules; concise units and notes.  Figures: caption below; bold `Figure N`; panels labelled (a), (b), etc.; English-only labels; no figure in Introduction.
- Keep the manuscript including tables, figures and references at or below 15 pages.  Use numbered square-bracket Vancouver citations and no more than 35 English references.
- Required declaration order before References: Ethical Approval (if applicable), Acknowledgements (optional), Author Contributions (CRediT), Conflicts of Interest, AI declaration.
- Conclusion is no more than 100 words.  Do not claim field significance, flood risk, or dynamical downscaling from the station-referenced IDW depiction.

## Manuscript content map

1. Introduction: regional precipitation-extreme motivation; CMIP6/SSP context; Phetchaburi gap; objectives.
2. Materials and Methods: study area and station data; daily-index definitions; completeness and fixed-reference thresholds; standard MK/Sen primary inference; BH-FDR; Yue–Wang 2004 sensitivity and Monte-Carlo diagnostic; model baseline/future windows; model-first aggregation; IDW display and coordinate sensitivity.
3. Results: data/QC; observed trends; model spread and relative changes; within-window future diagnostics; IDW depiction and coordinate audit.
4. Discussion: mechanism-oriented interpretation, Southeast-Asia comparison, uncertainty and reproducibility limitations, coordinate-boundary inconsistency and extrapolation caveat.
5. Conclusion: <=100 words and decision-relevant findings.

## Figure/table package

- Figure 1: station network, province boundary, station convex hull, Thailand inset and 465002 coordinate-audit marker.
- Figure 2: observed Sen-slope heat map and BH-FDR decision matrix.
- Figure 3: model-first station-median relative-change distributions for both SSPs; all seven models shown.
- Figure 4: PRCPTOT station-referenced IDW fields and reference-minus-primary coordinate sensitivity; common scales within each row.
- Table 1: observed trend counts and median Sen slopes by index.
- Table 2: model-first relative-change median, IQR, range and sign support by scenario/index.
- Tables are generated only from `derived/` outputs and are cross-checked against the primary CSVs.

## Validation checkpoints

- 13 stations, 11 indices, 1981–2014 observations, 7 models, SSP2-4.5/SSP5-8.5, 1995–2014 baseline and 2021–2050 future window.
- 15/15 pipeline tests pass; workbook integrity passes; minimum annual model completeness is 99.726776%.
- One observed MMK row (465002–SDII) is non-finite because of an irregular annual-year condition; standard MK/Sen remains the primary result.
- The 465002 coordinate sensitivity changes only its coordinate.  Eleven statistical result files are byte-identical between runs; only IDW map weights change.  The coordinate displacement is 5.731977 km.
- Final DOCX must be rendered and every page visually inspected.  If the canonical renderer cannot find LibreOffice on Windows, use Word COM export to PDF followed by Poppler rasterization as the visual-QA fallback, and record the limitation in the QA log.
