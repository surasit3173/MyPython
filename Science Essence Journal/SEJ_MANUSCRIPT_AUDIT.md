# Science Essence Journal (SEJ) Manuscript Audit & Verification Report

## 1. Executive Summary
This document reports the comprehensive verification findings of the revised manuscript `Rainfall_Occurrence_Intensity_Heterogeneity_SEJ_READY.docx` built from the source manuscript `Rainfall Occurrence–Intensity Heterogeneity and Its Implications for Provincial Extreme Rainfall Design.docx` and the official template `template-SEJ-2023.docx`.

The audit confirms that all SEJ template formatting, typography, structure, figures, tables, equations, citations, and references have been correctly implemented without altering or fabricating any scientific content, numerical values, or conclusions.

---

## 2. Structural & Format Verification Checklist

| Item / Section | Template Specification | Revised DOCX Verification | Audit Status |
| :--- | :--- | :--- | :--- |
| **Document Geometry** | A4 paper, 1-inch (2.54 cm) margins on all 4 sides | Verified: A4 page size, 1.0" top/bottom/left/right margins | **PASS** |
| **Article Type** | `Research Article` (12 pt, Bold) | Present at top of document | **PASS** |
| **Title** | 14 pt, Bold | Exactly matched to original title | **PASS** |
| **Author & Affiliation** | Author 12 pt Bold, Affiliation 10 pt Normal, Corresponding Email 10 pt Normal | `Surasit Punyawansiri*`, Office of Water Management and Hydrology, RID, email: Surasit.pu@ku.th | **PASS** |
| **Abstract** | 12 pt Normal, single spacing, max 250 words | Word count: 218 words (100% identical content) | **PASS** |
| **Keywords** | 12 pt Normal, 3–5 terms, comma separated | `Keywords:` in Bold, 5 keywords listed | **PASS** |
| **Section Headings** | 14 pt Bold | `Introduction`, `Materials and Methods`, `Results and Discussion`, `Conclusions`, `Acknowledgements`, `Author Contributions`, `Conflicts of Interest`, `Declaration of Generative AI`, `References` | **PASS** |
| **Subheadings** | 12 pt Italic | Subsections 2.1 through 2.11, 3.1 through 3.11 formatted in 12 pt Italic | **PASS** |
| **Body Paragraphs** | Times New Roman 12 pt, Justified, 0.5" indent | Formatted with 12 pt TNR, single line spacing, justified, 0.5 in indent | **PASS** |
| **Tables** | Open horizontal rules, 10 pt header (Bold) and body | All 5 tables formatted with SEJ borders, numeric right-alignment, bold captions | **PASS** |
| **Figures & Media** | Centered high-resolution images with bold captions | All 4 PNG figure files extracted and properly embedded in `word/media/` and `document.xml.rels` | **PASS** |
| **Equations** | Right-aligned numbers in parentheses `(1)`–`(15)` | All 16 OMML equation blocks preserved with right-aligned numbering | **PASS** |
| **References** | Vancouver style, 12 pt, square bracket citations `[1]`–`[19]` | All 19 references present, sequentially numbered, Vancouver style preserved | **PASS** |

---

## 3. Image & Figure Preservation Audit

Verification of `word/media/` assets in `Rainfall_Occurrence_Intensity_Heterogeneity_SEJ_READY.docx`:

| Figure Caption | Media Path | File Size | Dimensions / Width | Relationship ID | Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Figure 1** | `word/media/image1.png` | 692,276 bytes | 6.0 inches | `rId17` | **PASS** (100% Preserved) |
| **Figure 2** | `word/media/image2.png` | 587,862 bytes | 6.0 inches | `rId18` | **PASS** (100% Preserved) |
| **Figure 3** | `word/media/image3.png` | 703,135 bytes | 6.0 inches | `rId19` | **PASS** (100% Preserved) |
| **Figure 4** | `word/media/image4.png` | 320,667 bytes | 6.0 inches | `rId20` | **PASS** (100% Preserved) |

---

## 4. Scientific Content & Data Audit

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
* **Table 1** (14 rows x 9 cols, 126 cells): 100% exact match (Station metadata, P, W, S, Max daily).
* **Table 2** (14 rows x 7 cols, 98 cells): 100% exact match (AICc Gumbel, GEV, LP3, ΔAICc, Akaike weights, Selected distribution).
* **Table 3** (13 rows x 10 cols, 130 cells): 100% exact match (Return period quantiles, ratios, bootstrap widths, scenario sensitivity).
* **Table 4** (14 rows x 5 cols, 70 cells): 100% exact match (Spearman rank correlations for P, W, S across return levels & interval widths).
* **Table 5** (9 rows x 8 cols, 72 cells): 100% exact match (Provincial representation errors for Mean, Median, 75th, 90th percentiles at 25-yr and 100-yr).

### 4.3 Reference & Citation Traceability Audit
* All 19 references in the source manuscript were checked for order and citation mapping:
  - References [1]–[19] match the exact order, text, italicization, and DOIs.
  - In-text citation callouts e.g. `[1]`, `[2], [3]`, `[7]–[9]`, `[10]`, `[11]`, `[12]`, `[13]`, `[14]`, `[15]`, `[16]`, `[17]`, `[18]`, `[19]` are verified intact in body text.

---

## 5. Final Submission Status

**Final Status**: `READY_FOR_PR`

### Summary Statement
The revised manuscript `Science Essence Journal/Rainfall_Occurrence_Intensity_Heterogeneity_SEJ_READY.docx` fully complies with all guidelines of Science Essence Journal. All formatting, layout, typography, embedded high-resolution figures, tables, and equations adhere strictly to the `template-SEJ-2023.docx` template, and 100% of the scientific content, numerical data, and citations have been rigorously preserved without any alteration or fabrication.
