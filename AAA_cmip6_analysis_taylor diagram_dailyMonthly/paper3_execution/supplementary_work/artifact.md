# Supplementary Information template contract

## Reference

- Retained DOCX: `C:\MyPython\AAA_cmip6_analysis_taylor diagram_dailyMonthly\paper3_execution\manuscript\Paper3_CMJS_manuscript.docx`
- SHA-256: `F0E81B1EA60AC95E2ED5EFE265D9E6896543EE1A58AF72DA5BBAE873FB221870`
- Reference page count: 15; section count: 1.
- Render evidence: `paper3_execution\manuscript\rendered\page-01.png` through `page-15.png`; all pages inspected in the preceding manuscript QA.
- Structural evidence: `paper3_execution\supplementary_work\template-style-evidence.json` and the section-audit output recorded during this task.

## Page system

- A4 portrait, 21.0 x 29.7 cm.
- Margins: left 1.75 cm, right/top/bottom 1.55 cm; header/footer distance 0.65 cm.
- One column; centred Arabic page number in footer. Continuous manuscript line numbering is intentionally omitted from this table-only supplementary file because Word's line-number drawing layer can mask caption glyphs beside fixed-layout tables; this does not alter the journal typography or table system.
- Main manuscript has one section. Supplementary Information may add portrait sections only when needed for clean page breaks; geometry must remain identical.

## Typography and paragraph roles

- Typeface: Calibri throughout; body 11 pt, justified, double-spaced, 0 pt after.
- Title: 15 pt, bold, centred, 5 pt after, thin blue lower rule inherited from the retained Word Title style.
- Author block: 10-11 pt, centred, single-spaced.
- Heading 1: 12 pt bold black, single-spaced, 5 pt before, 0 after.
- Heading 2: 11 pt bold black, single-spaced, 5 pt before, 0 after.
- Table captions: 9 pt, single-spaced, table number bold, 3 pt after, kept with following table.
- Table text: 7.0-8.0 pt Calibri, single-spaced, vertically centred.

## Tables

- Header fill `D9EAF2`, black borders, bold centred headers, repeating first row.
- Narrative/key columns left aligned; numeric, phase, count, status and date fields centred.
- Cell margins approximately 45 DXA top/bottom and 55 DXA left/right; rows auto-expand.
- Explicit DXA table width/grid/cell widths; 120 DXA table indent. No autofit or percentage widths.
- Tables may continue across pages with repeated headers. Captions never separate from the first row.

## Components and content flow

1. Article title with `Supplementary Information` subtitle.
2. Author/affiliation block matching the main manuscript.
3. Short scope and interpretation note.
4. Supplementary Tables S1-S10, ordered to follow the methods/results sequence.
5. Abbreviations and table-specific notes directly below their relevant tables.

## Slot map

- Title block: reuse article title; add `Supplementary Information` as a subtitle.
- Introductory scope: explain that machine-readable full diagnostics remain in the reproducibility package and that the Word tables provide reviewable summaries.
- S1: model/member/data-source provenance.
- S2: station metadata and observed-data QC counts.
- S3: observed management-season ENSO classification.
- S4: model-specific ENSO phase sample sizes.
- S5: model-level raw and QDM primary responses.
- S6: secondary-index observed/raw/QDM ensemble responses (descriptive; not in primary multiplicity family).
- S7: full phase-contrast and neutral-centred-asymmetry inference.
- S8: QDM signal-preservation diagnostics.
- S9: blocked cross-fitted-QDM diagnostic summary.
- S10: acceptance gates and artifact/data dictionary.

## Package preservation and fidelity gates

- Retained main manuscript is read-only and must remain hash-identical.
- Supplementary file is a new artifact, but section geometry, type system, caption system, table fills/borders, line numbering, and footer page numbering must be recognizably source-derived.
- No unsupported significance markers; secondary indices are explicitly descriptive.
- Every value must be generated from frozen CSV/XLSX outputs or configuration, not manually inferred.
- Final DOCX must render to page PNGs; every page is inspected for clipping, broken tables, missing glyphs, inconsistent page numbers, and excessive blank space.
- Final QA export (2026-09-04): A4, 12 pages; structural audit passed with 11 tables, 11/11 fixed-width grids at 10,020 twips, 11/11 captions, PDF text checks passed, and 44 rows in `Paper3_Supplementary_Secondary_Responses.csv`.
- Final supplementary DOCX SHA-256: `F27CE06760FDFAA83197691205A2E0CD43F0803F7CC5D51BD2BA5491F1514CCF`.
