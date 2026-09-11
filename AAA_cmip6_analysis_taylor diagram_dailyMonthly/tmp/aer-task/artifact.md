# AER manuscript execution contract

## References

- Author-guideline document: `D:\วารสาร AER\format Applied Environmental Research.docx`
- Guideline SHA-256: `8d3bd19529da47597ac789a0c854cb3cc69d90172398f973729c2d9bea39c328`
- Guideline render: `C:\MyPython\AAA_cmip6_analysis_taylor diagram_dailyMonthly\tmp\aer-template-render`
- Guideline pages: 10; sections: 1
- Published writing and production example: `D:\วารสาร AER\paper AER\Analyzing Climate Change Status through Evaluating Trend of Temperature and Rainfall.pdf`
- Example SHA-256: `9C16966E3953EB70FCDDA8915661A89709EB34AFEFBB159E78951C910D7CF9B2`
- Example render: `C:\MyPython\AAA_cmip6_analysis_taylor diagram_dailyMonthly\tmp\aer-example-render`
- Example pages: 17; A4 published two-column layout
- Editable manuscript: `D:\วารสาร ASEP\SENT\Rainfall Occurrence–Intensity Heterogeneity and Its Implications for Provincial Extreme Rainfall Design.docx`
- Manuscript SHA-256 before editing: `3756bf78e3daf71c57feeca70e37939d8dba596e0922c08ca74eca677e76d54b`
- Manuscript pages before editing: 13; sections: 1

The guideline document is a captured instruction sheet, not a styled Word template. Its requirements control the submission format. The published PDF controls journal-facing prose, caption, and reference conventions but its final two-column production layout is not to be copied into the submission file.

## Page system

- Submission page size: US Letter 8.5 x 11 in, matching the supplied guideline document.
- Orientation: portrait.
- Margins: 1.0 in on all sides.
- Columns: one.
- Header: none.
- Footer: centered automatic page number, 0.5 in from bottom.
- Continuous line numbering: every line, restarting only at document end.
- Main text: Times New Roman 12 pt, black, double spaced.
- First-line paragraph indent: 0.5 in for ordinary body paragraphs; no space-bar indentation.

## Typography and paragraph roles

- Title: Times New Roman 14 pt bold, centered, black, concise, no decorative rules.
- Author: Times New Roman 12 pt bold, centered; affiliation superscript follows the name.
- Affiliation and corresponding author: Times New Roman 12 pt, centered; affiliation begins with superscript 1.
- Abstract heading: Times New Roman 12 pt bold, left aligned.
- Abstract: Times New Roman 12 pt, justified, double spaced, no first-line indent, at most 300 words.
- Keywords label: bold; four to six semicolon-separated indexing terms.
- Level 1 headings: numbered, Times New Roman 12 pt bold, left aligned, sentence case, keep with next.
- Level 2 headings: numbered, Times New Roman 12 pt bold italic, left aligned, sentence case, keep with next.
- Body: Times New Roman 12 pt, justified, double spaced, 0.5 in first-line indent.
- Captions: Times New Roman 12 pt, left aligned, double spaced; `Table n` or `Figure n` bold, followed by concise sentence-case text without a colon.
- References: Times New Roman 12 pt, double spaced, 0.25 in hanging indent.

## Lists, equations, tables, and figures

- Preserve all 15 native Word equations and their numbers.
- Preserve four inline source figures and all scientific labels; do not generate or alter scientific imagery.
- Preserve five editable Word tables.
- Keep the total display count at nine, within the journal maximum of ten.
- Table rules: no vertical rules and no cell shading. Use top rule, header-bottom rule, and bottom rule only.
- Repeat table header rows when a table spans pages.
- Align numeric table cells on the center or right as space permits; keep descriptive columns left aligned.
- Place each caption immediately above its table and below its figure.
- Keep figures near first mention and within the text width; permitted figure width is 174 mm or less and height 234 mm or less.

## Content flow

1. Title page details, abstract, and keywords.
2. Introduction.
3. Materials and methods with numbered level 2 subsections.
4. Results and discussion with numbered level 2 subsections.
5. Conclusions.
6. Acknowledgements.
7. Author contributions.
8. Conflict of interest.
9. Declaration of the use of generative AI and AI-assisted technologies.
10. References.

## Editable slot map

- Body paragraphs in `word/document.xml`: rewrite for clarity and reduce the non-reference manuscript below 5,000 words while preserving all reported numbers, uncertainty, conditions, and limitations.
- Title block in the first four body paragraphs: retain author identity and official email; add affiliation numbering and the verified institutional street/postal address.
- Caption paragraphs adjacent to the five tables and four images: shorten and convert to the AER caption form.
- Reference paragraphs: convert 19 entries from IEEE form to AER numbered form, ordered by first citation; retain DOI strings when available as supplemental identifiers.
- Software paragraph: remove visible Markdown backticks and retain package names and versions.
- AI declaration: rename and align with the journal's current disclosure wording, without changing author accountability.
- Preserve all table values and figure raster files unless a formatting-only change is required.
- Preserve native equation XML and equation numbering.

## Package preservation

- Preserve `word/media/image1.png` through `image4.png` byte-for-byte.
- Preserve native math objects in `word/document.xml` except for surrounding paragraph formatting.
- Preserve table cell values.
- No comments, tracked changes, fields, footnotes, endnotes, or content controls are present in the source.
- Add only the required page-number field and continuous-line-number section property.

## Fidelity and submission gates

- Final title is at most 300 characters; abstract at most 300 words; keywords count is four to six.
- Non-reference manuscript text is below 5,000 words.
- Reference citations remain sequential and every listed item is cited.
- All tables and figures are called out in numerical order and remain editable/embedded as required.
- The final document is single-column, double-spaced, Times New Roman 12 pt, with automatic page numbering and continuous line numbering.
- Render the final DOCX, inspect every page, and correct any clipping, overlap, broken equation, table split, figure placement, or footer defect before delivery.
