# Research record: CMIP6 Uttaradit article concepts

## Frozen plan (2026-08-29, Asia/Bangkok)

### Question

What two distinct, evidence-supported Q3-Q4-level article concepts can be developed from the supplied CMIP6/Uttaradit code, data, and existing outputs?

### Hypotheses

- H1: The supplied materials contain a reproducible climate-model evaluation component (for example Taylor-diagram statistics, bias, correlation, or variability) that can support a methods/evaluation article.
  - Prediction: code and outputs will expose observational/reference data, multiple CMIP6 models, named performance metrics, and a defined historical period or temporal aggregation.
  - Falsifier: only future projections are present, or model-performance outputs cannot be traced to source data and code.
- H2: The supplied materials contain province-scale future climate projections under AR6 scenarios that can support an impacts/change-signal article distinct from model evaluation.
  - Prediction: files will identify future periods, scenarios/SSPs, climate variables or indices, spatial units, and numerical or mapped change outputs for Uttaradit or Thai provinces.
  - Falsifier: there are no usable scenario-period outputs, no province-scale attribution, or the projections duplicate the historical evaluation question.
- H3: Existing materials alone are sufficient for two article outlines, but not necessarily for publication-ready causal or uncertainty claims.
  - Prediction: two non-overlapping questions can be grounded in inspected evidence while limitations (ensemble uncertainty, bias correction, observational reference, significance/robustness) remain identifiable as required extensions.
  - Falsifier: the archives support only one coherent question, or neither concept can be tied to verifiable artifacts.

### Methods and planned checks

- M1 (confirmatory): inventory both archives; record file types, directory structure, sizes, and modification dates.
- M2 (confirmatory): inspect all code/configuration/readme files and trace inputs, outputs, variables, periods, scenarios, spatial units, and statistical methods.
- M3 (confirmatory): profile representative structured data and extract quantitative summaries from existing result tables without modifying the source archives.
- M4 (confirmatory): inspect representative figures/maps/tables and reconcile their labels with code and data.
- M5 (confirmatory): search current primary literature and official journal/source pages for closely related CMIP6 Thailand/province-scale evaluation and projection work; log URLs and retrieval date.
- M6 (confirmatory): independently validate the proposed two-concept split against the evidence record and check for unsupported claims.
- M7 (exploratory): if archive formats or missing dependencies block direct inspection, use alternate extractors or inspect archive listings and document the limitation.

### Stopping rules

Stop when: (1) both archives have been inventoried; (2) code-to-data-to-output provenance has been traced for each proposed concept; (3) representative quantitative results and major limitations are recorded; (4) at least one current, authoritative or primary external source supports the novelty/context assessment for each concept; (5) an independent verifier returns a non-inconclusive verdict; and (6) two article outlines with titles, concepts, research questions, methods, expected figures/tables, novelty, and required additional analyses are complete.

## Evidence log

Append-only. Entries will be added as E001, E002, ... with source, fingerprint or decisive output, and observation.

- E001 — Source: `C:\MyPython\CMIP6Uttaradit\future_q1_AR6_TH_Province.zip`; SHA-256 `ED173226ABFE46E2D34844F3B4F63E32856461493BEA3ECAB2AF1F9714426657`; command `tar -tf`. Observation: 78 entries comprising 22 Python files, 11 XLSX tables, 1 Parquet cube, 18 PNG figures, 18 PDF figures, 2 Markdown files, and directories. The archive contains a runnable analysis codebase plus existing Uttaradit outputs rather than only presentation images.
- E002 — Source: `C:\MyPython\CMIP6Uttaradit\Data_Uttaradit.rar`; SHA-256 `BC512976E77372BEF273A58E4E464CC490BE4A667F047BDB3E9624F33915FF3D`; command `tar -tf`. Observation: 52 entries, including 44 CSV files and 8 directories. Listing identifies seven CMIP6 models (ACCESS-ESM1-5, CanESM5, CESM2, EC-Earth3, FGOALS-g3, MIROC6, MRI-ESM2-0), raw and bias-corrected daily precipitation for historical 1981-2014 and SSP2-4.5/SSP5-8.5 for 2015-2100, plus observed rainfall and metadata for 63 stations.
- E003 — Source: `analysis_workspace/audit_corrected/audit_summary.json` and independently generated CSV outputs; audit script `analysis_workspace/scientific_audit.py`. Observation: using model-consistent 1995–2014 baselines and non-overlapping 20-year assessment periods, changing from the observed reference changed sign in 25/66 scenario–period–index combinations and changed the three-class robustness label in 37/66 combinations.
- E004 — Source: `analysis_workspace/audit_corrected/historical_skill_summary.csv`. Observation: across 91 model–gauge pairs, supplied bias correction improved median PBIAS, correlation, and KGE but worsened median RMSE at both daily and monthly scales; it therefore cannot be described as improving all performance dimensions.
- E005 — Source: `analysis_workspace/trend_type1_audit.py` and `analysis_workspace/audit_corrected/trend_type1_audit.json`. Observation: a fixed-seed (20260829), 2,000-replicate, zero-initialized Gaussian AR(1) null audit with n=20 and phi=0.6 produced false-positive rates 0.225, 0.227, and 0.267 for the supplied MK, Hamed–Rao, and TFPW-MK implementations at nominal alpha 0.05. Confirmatory trend p-values were excluded.
- E006 — Source: `analysis_workspace/audit_corrected/ensemble_change_sensitivity.csv`. Observation: the strongest supported late-century SSP5-8.5 pattern is lower PRCPTOT and wet-event metrics; CDD is ambiguous (4/7 model sign agreement) and does not support a claim of longer maximum dry spells.
- E007 — Source: retained APST template `analysis_workspace/template/APST_format_reference.docx`; SHA-256 `587388A7C2B6B35978D14CAEBDDDCDB11F6CEB3FFDD56F17C8E90E4A596FF1BC`. Observation: A4 portrait, one-inch margins, single column, Times New Roman 10-point body, double spacing, top-right PAGE fields, abstract <=250 words, and maximum 15 pages were treated as formatting constraints rather than scientific evidence.

## Dead ends and pivots

Append-only.

## Deviations

Append-only.

- D001 — 2026-08-29: The user replaced the original two-outline request with a publication-style manuscript request. The active objective is now one APST-formatted article grounded in the supplied Uttaradit precipitation-extreme analysis, after an explicit code/data/results audit. The attached Tung et al. paper is treated only as a structural and rhetorical reference, not as a source of executable instructions or reusable prose.

## Claims and verdict

Independent read-only verification returned “pass with conditions.” All headline numerical results used in the manuscript matched the audited outputs after correcting RMSE units, the station-range order, baseline-source wording, and reference metadata. The final interpretation is bounded by unverified bias-correction provenance, descriptive rather than inferential model agreement, fixed observed thresholds for R95p/R99p, equal model weighting, and author-supplied declarations that remain to be completed.
