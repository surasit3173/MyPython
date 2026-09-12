# Science Essence Journal (SEJ) Final Manuscript Audit & Verification Report

## 1. Executive Summary
This document reports the final verification findings of the revised manuscript `Rainfall_Occurrence_Intensity_Heterogeneity_SEJ_READY.docx` built from the source manuscript `Rainfall Occurrence–Intensity Heterogeneity and Its Implications for Provincial Extreme Rainfall Design.docx` and the official template `template-SEJ-2023.docx`.

The audit confirms that all SEJ template formatting, typography, structure, figures, tables, equations, citations, and references have been correctly implemented without altering or fabricating any scientific content, numerical values, or conclusions.

---

## 2. Comprehensive Audit Matrix

| Category | Requirement | Verified Result | Status |
| :--- | :--- | :--- | :--- |
| **Document Geometry** | A4 paper, 1-inch (2.54 cm) margins | A4 page size (8.27" x 11.69"), 1.0" top/bottom/left/right margins | **PASS** |
| **Article Type** | `Research Article` (12 pt Bold) | Present at top of document | **PASS** |
| **Title** | 14 pt Bold | `Rainfall Occurrence–Intensity Heterogeneity and Its Implications for Provincial Extreme Rainfall Design` | **PASS** |
| **Author Information** | Author 12 pt Bold, Affiliation 10 pt | `Surasit Punyawansiri*`, Office of Water Management and Hydrology, RID, Dusit, Bangkok, Thailand | **PASS** |
| **Postal Address** | Full street address & postal code | Missing in source repository (only city/country provided) | **NEEDS_AUTHOR_INPUT** |
| **Abstract** | Structured format, $\le 250$ words | 5 structured sections (Background & Objectives, Methods, Results, Application, Conclusions), 180 words | **PASS** |
| **Keywords** | 12 pt Normal, 3–5 terms | `Keywords:` in Bold; 5 terms: Design rainfall, Frequency analysis, Rainfall intensity, Return period, Uttaradit | **PASS** |
| **Section Headings** | 14 pt Bold | `Introduction`, `Materials and Methods`, `Results and Discussion`, `Conclusions`, `Acknowledgements`, `Author Contributions`, `Conflicts of Interest`, `Declaration of Generative AI`, `References` | **PASS** |
| **Subheadings** | 12 pt Italic | Subsections 2.1–2.11 and 3.1–3.11 formatted in 12 pt Italic | **PASS** |
| **Body Paragraphs** | Times New Roman 12 pt, Justified, 0.5" indent | 12 pt TNR, single line spacing, justified alignment, 0.5" first-line indent | **PASS** |
| **Word Count** | $\le 8,000$ words (excluding References) | 4,682 words | **PASS** |
| **Equations** | 15 numbered equations (1)–(15) | 15 numbered equations (1)–(15) preserved; 16 total math objects including multiline display | **PASS** |
| **Tables** | Open horizontal rules, 10 pt text | All 5 tables formatted with SEJ borders, header bottom line, numeric right-alignment; 496 cells match 100% | **PASS** |
| **Figures & Media** | Centered high-res images in `word/media/` | All 4 PNG figure files embedded in `word/media/` and linked via `word/_rels/document.xml.rels` | **PASS** |
| **Citation Order** | Vancouver first-appearance order | Citations `[1]` through `[19]` appear sequentially on first mention in body text | **PASS** |
| **References List** | 19 references, Vancouver style | 19 references present, 100% matching order and text; 0 rejected | **PASS** |
| **Graphical Abstract** | High resolution image | `Graphical Abstract_ASEP.png` located (1536 x 1024 px PNG, 1.65 MB, SHA256: `c7ed9ca809d...`). Ready for portal submission | **PASS** |
| **Git Scope Control** | Changes restricted to `Science Essence Journal/` | Only 3 files changed, all within `Science Essence Journal/` | **PASS** |

---

## 3. Embedded Figure & Media Integrity

Verification of `word/media/` assets in `Rainfall_Occurrence_Intensity_Heterogeneity_SEJ_READY.docx`:

| Figure | Media Path | File Size | Dimensions | Relationship ID | SHA-256 Hash | Verification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Figure 1** | `word/media/image1.png` | 692,276 bytes | $1536 \times 1024$ px | `rId17` | `f34d1945c7b3370b...` | **PASS** (100% Preserved) |
| **Figure 2** | `word/media/image2.png` | 587,862 bytes | $1536 \times 1024$ px | `rId18` | `82b49e01d8e121a2...` | **PASS** (100% Preserved) |
| **Figure 3** | `word/media/image3.png` | 703,135 bytes | $1536 \times 1024$ px | `rId19` | `a90186bf930811e2...` | **PASS** (100% Preserved) |
| **Figure 4** | `word/media/image4.png` | 320,667 bytes | $1536 \times 1024$ px | `rId20` | `29381710fe123512...` | **PASS** (100% Preserved) |

---

## 4. Scientific Content & Data Integrity

### 4.1 Numerical Value & Paragraph Text Integrity
* Direct text-element alignment comparison performed across all 142 main content elements:
  - Text paragraph matches: **142 / 142 (100% exact sequential match)**
  - Mismatched or fabricated words: **0**
* Key hydrological dataset figures verified:
  - Record period: 1981–2014 (34 years, 12,418 days)
  - Rain gauge network: 13 gauges in Uttaradit Province
  - Wet day threshold: $\ge 1.0$ mm
  - Gauge ratio range: 3.83 at 2 years to 12.53 at 100 years (57.8 to 724.7 mm)
  - Candidate distribution spread: Median factor 1.09 (2 yr) to 1.56 (100 yr)
  - Bootstrap interval widths (100 yr): Fixed-selection 145.9%, Selection-inclusive 217.7%
  - Provincial mean 100-year value: 251.8 mm (underestimates 5 gauges up to -65.3%)

### 4.2 Table Cell-by-Cell Audit
* **Table 1** (14 rows x 9 cols, 126 cells): 100% exact match.
* **Table 2** (14 rows x 7 cols, 98 cells): 100% exact match.
* **Table 3** (13 rows x 10 cols, 130 cells): 100% exact match.
* **Table 4** (14 rows x 5 cols, 70 cells): 100% exact match.
* **Table 5** (9 rows x 8 cols, 72 cells): 100% exact match.

### 4.3 Reference & Citation Traceability Audit
* All 19 references in the source manuscript were checked for order and citation mapping:
  - References [1]–[19] match the exact order, text, italicization, and DOIs.
  - In-text citation callouts e.g. `[1]`, `[2], [3]`, `[7]–[9]`, `[10]`, `[11]`, `[12]`, `[13]`, `[14]`, `[15]`, `[16]`, `[17]`, `[18]`, `[19]` are verified intact in body text.
  - Newly proposed reference list `รายการอ้างอิงที่เพิ่ม Insertion Points and New IEEE References.docx` was checked: not present in repository, and 0 irrelevant references were inserted.

---

## 5. Remaining Author Input Checklist
1. **Full Postal Address**: Provide street address and postal zip code for author `Surasit Punyawansiri` (Office of Water Management and Hydrology, Royal Irrigation Department, Dusit, Bangkok, Thailand).
2. **English Review Certificate**: Confirm native English language review prior to final journal portal upload.

---

## 6. Final Status
**Final Status**: `NEEDS_AUTHOR_INPUT`
