# Paper 2 — submission status

## APST compliance, verified in this build

| Requirement | Status |
|---|---|
| Length, 15 pages maximum | **15** |
| Abstract, 150–250 words | **221** (242 if hyphenated compounds count as two) |
| Conclusion, 100 words maximum | **97** |
| Keywords, 4–11, alphabetical, not duplicating the title | 6, checked automatically |
| References, 35 maximum, Vancouver | 16, all cited, none uncited, no placeholder |
| Continuous line numbering | present and rendering from line 1 of page 1 |
| Equations by Equation Editor | 8 of 8 are Word equation objects, and all eight render in the PDF |
| Tables by the Word table function | main tables in the manuscript; supplementary tables in `Paper2_Supplementary_FINAL.docx`, 8 pages, built by the same code path as the manuscript so the style is identical |
| Section order | Conclusion, Ethical Approval, Acknowledgements, Author Contributions, Conflicts of Interest, AI declaration, References |

### Two findings about the preview toolchain, not the manuscript

**Equations appeared blank in earlier previews because `libreoffice-math` was
not installed.** Without that component LibreOffice silently drops every
`m:oMath` element on import. A file produced by pandoc behaved identically,
which isolates the cause to the renderer. With the component installed all
eight equations render. Verify once in Microsoft Word before upload.

**Line numbering belongs in `word/document.xml` inside `sectPr`, not in
`word/settings.xml`.** A check that looks only at `settings.xml` reports it
absent even when Word and the PDF both show it.

### One equation change made for portability

`U+007C` (`|`) is mapped to a delimiter operator by StarMath-based converters
and comes out mangled. The absolute-value bars in Equation (4) use `U+2223`
(DIVIDES), which renders as an upright bar in every converter tested. Equation
(4) was also split into (4) and (5) so the summand is named rather than wrapped
around a fraction, which no converter handled reliably.

## Code corrections in this build

1. **Missing days no longer bridge a spell.** `temporal_metrics` dropped
   missing values before computing runs, which joined the days either side of a
   gap. Wet, dry and missing are now three states, and only pairs in which both
   days were observed enter a transition count. Four tests in
   `tests/test_temporal_gaps.py` pin this: before the fix, 40 wet days, a gap
   and 40 more wet days returned a spell of 80. The corrected values move by
   0.1 to 0.4 percentage points and are in the manuscript.
2. **YAML comment corrected.** The Hazen plotting position was annotated
   `(i+0.5)/n` while the code and the Methods both use `(i − 0.5)/n`.

## Numerical integrity

`scripts/audit_paper2.py` resolves every number in the Abstract, Results,
Discussion and Conclusion to one identified cell of one main table, matching on
value, index, method and scenario together.

- 153 numbers in the narrative, 150 resolved, 3 design constants, 0 untraced
- one estimator across code, Methods, tables, figures and audit (gate P2-E1)
- no gauge-by-model pooling, and no aggregation across scenarios, anywhere

The audit caught the temporal values changed by correction 1 above, and caught
two grouped citations that a reference renumbering had missed. It runs as a gate
in `run_paper2.py`, so a mismatched manuscript cannot reach the Word build.

## Supplementary material

The earlier supplement was produced by a different toolchain and did not match
the article: no page size or margins were set, the font was not Times New Roman,
and two sheets carried 67 columns and 9,804 rows, which is not a table anyone
can read. It is now built by the same code path as the manuscript, so A4,
1-inch margins, Times New Roman 10 pt, horizontal rules only and captions above
tables are identical by construction rather than by imitation.

Two kinds of item are distinguished, because one format cannot serve both:

| | |
|---|---|
| **Supplementary Table** | something a reader reads, rendered in the Word document. Where the underlying listing is large, the table shown is the aggregate the manuscript actually cites. |
| **Supplementary Data** | something a reader computes with. The complete listing is a CSV that forms part of the submission, so no citation points outside the package. |

Numbering is locked to the manuscript citations: S1 method design and shared
settings, S2 calibration, S3 validation, S4 signal-preservation summary,
Data S5 full signal preservation, S6 decomposition, S7 temporal dependence,
S8 paired differences, S9 acceptance criteria, S10 model inventory. Six data
files accompany them. All ten items are cited in the manuscript, and the audit
now fails if any is not. No supplementary figure is cited, so none is required.

`Paper2_Supplementary_ARCHIVE.xlsx` remains as the machine-readable working
copy and is not a submission table.

## Outstanding before upload

1. Open the file once in Microsoft Word and confirm the eight equations, then
   export the PDF from Word rather than from a converter.
2. ORCID and full postal address for the corresponding author, if required.
3. Grant number in the Acknowledgements, if the work was funded.
4. For double-blind review, remove the author block and the Acknowledgements
   from the blinded file.
