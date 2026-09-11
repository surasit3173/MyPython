# Paper 2, Applied Environmental Research version

Built from the manuscript you supplied (`Paper2_APST_manuscript_FINAL (4).docx`),
restructured to the AER instruction. The results, tables and figures come from
the same pipeline; nothing was recomputed.

```bash
python run_paper2.py --config config/uttaradit.yaml --journal aer \
       --figure1 figures/study_area.png
```

## Two errors found in the supplied file

1. **`Li et al. [22]` names the wrong authors.** Reference [22] is Padulano,
   Gomez-Mogollon, Napolitano and Rianna. The sentence now reads "Padulano et
   al.".
2. **Cannon et al. is listed twice**, as [1] and again as [19], with the same
   title, journal, volume and pages. The two are merged; the sentence that cited
   [19] now cites [1].

Both are in the Discussion, where a reviewer would notice them.

## What AER requires, and where it is met

| Requirement | Status |
|---|---|
| Structure: Introduction, Materials and Methods, Results and Discussion, Conclusions, Acknowledgements, References | followed; Results and Discussion combined as the instruction recommends |
| Length under 5,000 words excluding references | 4,283 |
| Abstract 300 words maximum | 221 |
| Title 300 characters maximum, no abbreviation | 132 |
| Keywords 4 to 6, no general or plural term, no "and" or "of" | 5 |
| Single column, double spacing, Times New Roman 12 pt | body at 24 half-points |
| Automatic page numbering | PAGE field in the footer, visible in the rendered PDF |
| Continuous line numbering | `w:lnNumType` with `restart="continuous"` |
| Built-in equation editor | 8 Word equation objects |
| Tables by the Word table function, no vertical rules or shading | 3 tables, horizontal rules only |
| Figures 39, 84, 129 or 174 mm wide, height 234 mm maximum | all at 129 mm; tallest 141 mm |
| Figure lettering 8 to 12 pt in final-sized artwork | 9 pt, because each figure is drawn at its printed width |
| Display items, tables plus figures, 10 maximum | 3 + 5 = 8 |
| Citations numbered in order of appearance | 23, renumbered from first appearance |
| Reference style: surname and initials, title, journal in full, year, volume(issue), pages | applied to all 23 |

## References

Renumbered by first appearance and continuous from 1 to 23, with no gaps. The
supplied numbering ran 1 to 16 then jumped to 18, 19, 20, 22, 23, 24, 25 and 31,
which leaves seven numbers unassigned; a submission system flags that.

| supplied | new | first cited in |
|---|---|---|
| 1, 19 | 1 | Introduction, paragraph 1 |
| 23 | 6 | Introduction, paragraph 4 |
| 20 | 7 | Introduction, paragraph 5 |
| 6 to 16 | 8 to 18 | Materials and methods |
| 24 | 19 | Results and discussion, 3.1 |
| 22 | 20 | Results and discussion, 3.4 |
| 25 | 21 | Results and discussion, 3.5 |
| 31 | 22 | Results and discussion, 3.7 |
| 18 | 23 | Results and discussion, 3.4 |

Every reference in the list is cited, and every citation resolves.

## Figures

Figures 4 and 5 were rebuilt to the standard of Figure 3, and three defects were
corrected in the process.

1. **The row title overflowed its panel and collided with the neighbouring
   panel.** The group name is now written once above the row, and only the
   scenario sits inside the panel.
2. **Category labels ran into one another** because five labels of seven or
   eight characters do not fit upright in a 63 mm panel. Rotation is now decided
   from the panel width and the longest label rather than fixed in advance.
3. **The rows shared an x axis although they hold different index sets**, so the
   upper row was labelled with the lower row's categories. This mislabelled the
   data, not just the layout. Sharing is now limited to the y axis.

Figure 5 was also restructured: sixteen categories cannot be labelled legibly in
a half-width panel, so the two scenarios are stacked and each takes the full
figure width. A dashed rule and a legend entry now mark where the
sequence-dependent group begins.

## Publication assets

`output/publication_assets/paper2_aer/` holds each table and figure as a separate
file: PNG at 600 dpi and 129 mm, vector PDF, TIFF at 1,200 dpi, TSV per table,
one formatted workbook, captions in submission order and SHA-256 checksums.

Which workbook sheet is which manuscript table, and which rendered figure is
which manuscript figure, are declared in `manuscript/paper2_aer_table_map.json`
and `manuscript/paper2_aer_figure_map.json`. Both builders read them, so a table
cannot be exported under a number that belongs to a different table. Before this
was declared, positional matching exported the method-design sheet as Table 1.

## Outstanding before upload

1. Open the manuscript once in Microsoft Word, confirm the eight equations, and
   export the PDF from Word rather than from a converter.
2. Add the 16-digit ORCID; AER records it on the title page.
3. Name the funding organisation in full in the Acknowledgements.

## Figure set, second review

Comparing Figures 2 to 5 side by side at their printed size revealed four
inconsistencies that were not visible one figure at a time.

**1. The figures were not the same width.** Figures 3 to 5 measured 138.6 mm
against Figure 3's 128.9 mm, because the width-fitting pass ran only once and
could not converge when a wide legend set the bounding box. Placed at 129 mm,
the wider figures were reduced by 7% and their lettering ended up at 8.4 pt
while Figure 3 kept 9 pt: the same paper with two text sizes. The fit now
iterates on width, and a legend that is itself wider than the column is
reported rather than silently accepted. All five figures are now within 0.5 mm
of 129 mm.

**2. A legend wider than the column was the cause, so it is now laid out to
fit.** The routine tries one row, then balanced rows, rather than dropping one
column at a time, which used to leave a single orphan entry on a second row.

**3. The same distinction was drawn three different ways.** Sequence-dependent
indices were marked by a dotted divider with inline text in Figure 2, by
hatched bars in Figure 4, and by a shaded band in Figure 5. One encoding, a
shaded band with a dashed rule at its boundary and a matching legend entry, is
now used in all three, so a reader learns it once.

**4. Figure 2 used a fixed logarithmic axis from 0.005 to 600 for values that
span 15 to 125.** Three of the five decades were empty and every bar was
compressed into the top fifth of the panel. The scale is now chosen from the
data: logarithmic only where the values genuinely span decades, which is the
calibration period, and linear otherwise.

Two further defects were corrected in the same pass. The panel rows shared an x
axis although they hold different index sets, so the upper row of Figure 4 was
labelled with the lower row's categories, and the y-axis labels drifted
horizontally between figures because a panel with two-digit ticks pushes its
label outward; the offset is now fixed so the labels line up when the figures
are read in sequence.

Finally, the footer paragraph was taking a line number of its own, which printed
a stray numeral in the left margin of every page beside the page number.
