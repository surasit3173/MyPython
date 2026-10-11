# Paper 2 — final deliverable set

**Climate-Signal Preservation of Bias-Corrected Daily Precipitation from Global
Climate Models: A Comparison of Quantile Mapping Methods over Uttaradit, Thailand**

15 pages in APST format, continuous line numbering, 6 main tables, 6 main
figures, 18 references.

## How this was produced

```bash
python scripts/run_pipeline.py             --config config/uttaradit.yaml
python scripts/build_paper2_manuscript.py  --config config/uttaradit.yaml \
       --figure1 figures/Uttaradit.png
python scripts/audit_paper2.py             --config config/uttaradit.yaml
python docx_build_p2/prepare_p2.py         --config config/uttaradit.yaml
node   docx_build_p2/build_p2.js
```

The narrative lives in `manuscript/Paper2_APST_manuscript.md`; the Word file is
generated from it and is overwritten on every build, so edits belong in the
markdown.

## Fair-comparison guarantee (Gate P2-A)

All three methods read the same master result database. They share the observed
record and its quality control, the station mapping, the calibration period
1981–2002, the independent validation period 2003–2014, the 1.0 mm d⁻¹ wet-day
convention, the frequency-adaptation occurrence model, the percentile reference
period, the index definitions, the 1995–2014 baseline, the 2021–2050 window and
the ensemble aggregation. Only the intensity transformation differs. The check
is executed in `build_paper2_manuscript.py` and recorded in supplementary sheet
`S8_fair_comparison_check`; a mismatch aborts the build.

## Numerical audit

`scripts/audit_paper2.py` extracts every percentage from the Abstract, Results,
Discussion and Conclusion and matches it against values recomputed from the
machine-readable outputs. The current status is:

- 119 numbers in the narrative
- 117 traced to a source file
- 2 design constants (wet-day threshold, extrapolation share)
- 0 not traced
- references: 18 cited, 18 listed, none uncited, none missing
- abstract 243 words, keywords 6 in alphabetical order

`paper2_claim_audit.csv` lists every number with its line, its source and its
verification status.

## What the results support

| Finding | Evidence |
|---|---|
| QM and QDM are identical over calibration | Table 2; the delta term equals unity there by construction |
| Calibration ranking does not transfer | Table 3: all three within 0.2 percentage points out of sample |
| No method corrects day ordering | Section 3.5: methods differ by <1 percentage point on every sequencing statistic |
| QDM best for upper-quantile signal | Table 4: q95 +1.06%, q99 +0.51% against +2.62% and +2.59% |
| DetQM best for mean signal | Table 4: PRCPTOT +0.34%, SDII 0.00% |
| Quantile preservation does not imply extreme preservation | Table 5: QDM worst for R20mm (+7.04%) and R95p (−4.57%) |
| Method main effect is small but interaction is not | Table 6: method ≤2.9% of SS; residual 74.0% for R20mm, 77.9% for R50mm |

**No universal-best claim is made anywhere in the manuscript.**

## Interpretation status

- **Verified**: calibration and validation MAB; signal-preservation errors;
  decomposition shares. All recomputed by the audit.
- **Derived**: PE from Equation (6), computed from verified inputs.
- **Diagnostic**: CDD, CWD, Rx5day and all sequencing statistics. Reported to
  show what remains uncorrected, never as validated predictive claims.
- **Limitation**: one realisation per GCM, 13 gauges, unavailable station
  metadata, one to five distinct raw series per model, two scenarios, one
  future window, marginal daily framework.
- **Not established**: how a method that models temporal structure explicitly
  would behave; the interaction term the decomposition reports but does not
  resolve.

## Files

| File | Contents |
|---|---|
| `Paper2_APST_manuscript_FINAL.docx` | submission manuscript |
| `Paper2_APST_manuscript_FINAL_preview.pdf` | rendered preview |
| `Paper2_APST_manuscript.md` | narrative source |
| `Paper2_Tables_FINAL.xlsx` | Tables 1–6 plus the method-settings sheet |
| `Paper2_Supplementary_FINAL.xlsx` | S1–S9 including the fair-comparison check |
| `figures/` | Figures 1–6, PNG at 600 dpi and vector PDF |
| `paper2_mab.csv` | mean absolute bias, every period, method and index |
| `paper2_signal_preservation.csv` | PE per model, gauge, scenario and index |
| `paper2_temporal_dependence.csv` | sequencing statistics |
| `paper2_variance_decomposition.csv` | two-way sum-of-squares shares |
| `paper2_claim_audit.csv` | every narrative number with its source |
| `paper2_manifest.json`, `paper2_file_hashes.csv` | provenance |
| `SUBMISSION_NOTES.md` | items to complete before upload |

## Relationship to Paper 1

Paper 1 asks what near-future changes a validated QDM ensemble supports. Paper 2
asks how the choice of correction alters historical performance and the
preservation of climate signals. Both draw on the same master pipeline and the
same 2021–2050 window, so the two are numerically consistent, but the results
and the central claim do not overlap. Paper 2 contains no spatial map, no
provincial projection narrative and no discussion of the late-century anomaly.
