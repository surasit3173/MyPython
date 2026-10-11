# PROJECT 2 — Uttaradit
## Antigravity Execution Specification for Publication-Ready Manuscript

**Purpose:** This document is an execution specification for an AI agent operating inside the existing Antigravity workspace. The agent must use the actual Project 2 files as the authoritative evidence and complete manuscript/submission preparation without inventing, estimating, silently reconciling, or replacing scientific results.

---

## 1. Project identity

**Project:** Projected precipitation extremes over Uttaradit Province based on observations and CMIP6 SSP scenarios

**Workspace:**
`C:\MyPython\CMIP6Uttaradit`

**Primary objective:** Prepare the Project 2 research article for submission to a Q2–Q3 journal using the completed and frozen analysis and the actual files in the Antigravity workspace.

**Analysis status:** CLOSED / LOCKED.

Do NOT rerun, redesign, recalibrate, or replace the frozen scientific analysis merely to obtain a preferred result. If an explicit contradiction is found between manuscript text and authoritative project outputs, correct the manuscript to the authoritative evidence. If two authoritative outputs conflict, STOP and report HOLD rather than selecting a value by assumption.

---

## 2. Mandatory operating rules

The agent MUST:

1. Inspect the actual Project 2 workspace before making substantive decisions.
2. Identify authoritative files from project documentation, manifests, provenance, source code, and outputs.
3. Treat actual project files as the primary evidence.
4. Preserve frozen numerical results unless an authoritative correction is documented.
5. Distinguish:
   - FACT
   - COMPUTED
   - INFERRED
   - INTERPRETATION
   - HYPOTHESIS
   - UNKNOWN
   - ERROR
6. Never fabricate data, model output, statistical values, references, figures, tables, uncertainty percentages, or journal requirements.
7. Never use synthetic fallback data.
8. Never silently replace one result with another.
9. Never claim an executable analysis exists when only a precomputed/static artifact exists.
10. Never claim uncertainty decomposition unless actual ANOVA/variance-decomposition evidence exists.
11. Never claim causal mechanisms from topography, monsoon dynamics, or other physical drivers unless directly analysed.
12. Never overstate bias correction performance.
13. Keep a provenance trail for major numerical claims.
14. If evidence is missing or contradictory, return HOLD with exact file paths and evidence.
15. Do not claim Q1/Q2 acceptance. The appropriate conclusion is readiness for peer review/submission when all gates pass.

---

## 3. Workspace inspection

The agent must inspect the full project structure sufficiently to identify:

- configuration;
- observation data;
- CMIP6 model data or references;
- bias-corrected data;
- ETCCDI calculation outputs;
- projection outputs;
- model metadata;
- station metadata;
- spatial products;
- figures;
- tables;
- manuscript drafts;
- references;
- manifests/provenance;
- scripts;
- tests;
- README/documentation.

Do not assume a filename is authoritative merely because it contains words such as `final`, `corrected`, or `revised`.

---

## 4. Observational network

Project 2 contains **13 observed rainfall stations** in Uttaradit.

The agent must use the actual station metadata and coordinate files in the workspace to construct or verify station tables and maps.

The study uses daily precipitation observations.

A project-level statement previously recorded:

**12,418 daily observations from 1981–2014 with 0% missing.**

The agent must verify this statement against the actual data/provenance before repeating it.

If the manuscript discusses a baseline period of 1995–2014, it must clearly distinguish:

- full observational availability period; and
- the authoritative baseline period used for model evaluation/projection comparison.

Do not silently conflate the two.

---

## 5. Authoritative baseline period

The authoritative baseline for Project 2 model evaluation and future-change comparison is:

**1995–2014 (20 years).**

This is a hard-stop requirement.

Do not replace it with 1981–2014 or another period unless the authoritative project files explicitly establish a different final baseline.

Any baseline-dependent result must be checked against the actual project output.

---

## 6. CMIP6 model ensemble

The project uses seven CMIP6 GCMs:

1. ACCESS-ESM1-5
2. CESM2
3. CanESM5
4. EC-Earth3
5. FGOALS-g3
6. MIROC6
7. MRI-ESM2-0

Scenarios:

- SSP2-4.5
- SSP5-8.5

The manuscript must preserve these model and scenario names consistently.

Do not add or remove models unless the actual frozen project configuration/output establishes a different final ensemble.

---

## 7. Extreme precipitation indices

The authoritative Project 2 analysis uses **11 ETCCDI indices**:

1. PRCPTOT
2. SDII
3. Rx1day
4. Rx5day
5. CDD
6. CWD
7. R10mm
8. R20mm
9. R50mm
10. R95p
11. R99p

The manuscript must use the exact definitions implemented in the project.

Do not substitute definitions from another software package if they differ from the frozen implementation.

The agent must inspect the project documentation/source code and confirm:

- wet-day threshold;
- percentile reference period;
- annual aggregation;
- unit conventions;
- treatment of missing data;
- threshold/event definitions.

If a definition is not supported by the project files, mark it UNKNOWN and investigate the relevant source rather than guessing.

---

## 8. Bias correction / QDM provenance

The project uses bias-corrected CMIP6 outputs.

The authoritative correction approach is **Quantile Delta Mapping (QDM)** as documented by the project.

CRITICAL PROVENANCE LIMITATION:

Precomputed bias-corrected CSV artifacts exist, but the repository does **not** contain a live executable Python script that maps raw CMIP6 data to the stored bias-corrected outputs.

Therefore the manuscript MUST disclose this accurately.

Do NOT state or imply that the current repository contains a fully executable end-to-end QDM processing pipeline if it does not.

The manuscript may state that QDM-corrected outputs were used as precomputed project artifacts, provided the exact provenance is documented.

The agent must identify:

- raw model source, if present;
- bias-corrected files;
- provenance/manifests;
- correction method documentation;
- baseline period;
- variables/indices affected.

If reproducibility is incomplete, report the limitation rather than inventing a missing processing script.

---

## 9. Frozen projection reconciliation

The authoritative reconciled future precipitation projection values are:

### Seven-GCM bias-corrected historical baseline

**1068.48 mm**

### SSP2-4.5

Seven-GCM MME future:

**1092.08 mm**

Absolute change:

**+23.60 mm**

Relative change:

**+2.21%**

Arithmetic mean of individual model percentage changes:

**+2.50%**

### SSP5-8.5

Seven-GCM MME future:

**1080.18 mm**

Absolute change:

**+11.70 mm**

Relative change:

**+1.10%**

Arithmetic mean of individual model percentage changes:

**+1.16%**

### Mandatory interpretation

Projected changes MUST be expressed relative to the:

**seven-model bias-corrected historical baseline (1068.48 mm)**

They MUST NOT be presented as changes relative to the observed gauge network mean unless a separate analysis explicitly calculates and labels that comparison.

Do not mix:

- observed gauge baseline;
- raw CMIP6 baseline;
- bias-corrected CMIP6 baseline;
- future MME;
- arithmetic mean of model-specific percentage changes.

These are different quantities.

If the actual latest authoritative output differs, STOP and report the discrepancy rather than overwriting the project evidence.

---

## 10. Observed station mean rainfall

Previously reconciled manuscript values for the 13 observed stations are:

| Station order in existing manuscript | Mean annual rainfall (mm) |
|---|---:|
| 1 | 995.65 |
| 2 | 1053.80 |
| 3 | 1425.06 |
| 4 | 1085.21 |
| 5 | 1121.00 |
| 6 | 1129.59 |
| 7 | 1221.05 |
| 8 | 1146.01 |
| 9 | 1223.36 |
| 10 | 1204.22 |
| 11 | 1159.21 |
| 12 | 947.71 |
| 13 | 1105.59 |

Arithmetic mean:

**1139.81 mm**

These values are cross-check evidence only. The agent MUST verify them against the authoritative station table/output before using them in the final manuscript.

An earlier manuscript version contained an inconsistency between a network-mean PRCPTOT value in text and a table. The agent must check the latest generated manuscript and authoritative ETCCDI output and resolve any such inconsistency based on evidence, not preference.

---

## 11. Bias-correction performance

The reconciled project-level bias-correction results are:

### Network aggregate

Absolute annual precipitation bias reduction:

**77.2%**

Change in network mean absolute bias:

from approximately:

**−307.13 mm**

to:

**−69.90 mm**

### Arithmetic mean across individual models

Mean bias reduction:

**73.3%**

### Individual model reductions

- EC-Earth3: 96.8%
- ACCESS-ESM1-5: 88.8%
- FGOALS-g3: 87.9%
- CESM2: 87.2%
- MIROC6: 81.3%
- MRI-ESM2-0: 47.4%
- CanESM5: 23.6%

The manuscript must clearly distinguish the **network aggregate reduction (77.2%)** from the **arithmetic mean of model-specific reductions (73.3%)**.

Do not report 77.2% as though it were the average of the seven model-specific reductions.

Do not imply that QDM completely removed model bias.

---

## 12. Spatial interpolation / IDW

The project includes IDW-based spatial visualization.

Cross-validation results previously recorded:

- LOOCV MAE: **98.03**
- LOOCV RMSE: **131.26**
- LOOCV MBE: **−3.21**

The manuscript must describe IDW as an exploratory/interpolative spatial visualization method unless the project provides evidence supporting a stronger predictive interpretation.

Do not describe IDW as a physically based downscaling model.

Do not imply that LOOCV metrics establish universal spatial prediction skill.

The map must use actual station coordinates and authoritative boundary data.

---

## 13. Topography and physical interpretation

The study area has complex topographic context.

The manuscript may state that spatial patterns are:

**consistent with complex topography**

if supported by the mapped results.

However, the study does not contain a validated terrain regression or causal attribution analysis sufficient to establish that topography caused a specific precipitation response.

Therefore:

DO NOT write statements such as:

- “topography caused the projected increase”;
- “mountain effects explain the trend”;
- “coastal convection caused the observed pattern”;
- “orographic forcing is responsible”

unless a direct quantitative analysis exists in the project files.

Use:

- “consistent with”
- “may reflect”
- “could be associated with”

only where scientifically justified and clearly identified as interpretation/hypothesis.

---

## 14. Uncertainty decomposition

IMPORTANT:

The project does **not** contain an authoritative ANOVA or variance-decomposition engine/output supporting statements such as:

- model uncertainty = 65%;
- scenario uncertainty = 25%;
- internal variability = 10%;

or similar percentages.

All such unsupported uncertainty percentages must remain removed.

The manuscript MUST NOT contain a quantitative uncertainty decomposition unless the actual project files contain the required analysis and outputs.

The project may discuss model spread qualitatively if the actual outputs support it.

---

## 15. Primary scientific framing

The paper should be framed around:

1. observed precipitation characteristics;
2. 11 ETCCDI extreme precipitation indices;
3. evaluation of seven CMIP6 GCMs;
4. bias correction using QDM;
5. baseline 1995–2014;
6. future projections under SSP2-4.5 and SSP5-8.5;
7. spatial heterogeneity across 13 stations;
8. model-to-model variation;
9. implications for precipitation/flood-risk and water-resource planning, without overstating predictive certainty.

Do not transform the study into a trend-detection paper unless the actual project design explicitly includes trend analysis as a final objective.

---

## 16. Recommended manuscript structure

### Title

The title should accurately reflect observations, CMIP6, SSP scenarios, and precipitation extremes.

A previously considered title is:

**Projected Precipitation Extremes over Uttaradit Province Based on Observation and CMIP6 SSP Scenarios**

The agent should inspect the existing manuscript and journal target before changing the title.

Do not optimize the title using unsupported claims such as “future flood risk prediction” unless flood modelling is actually performed.

### Abstract

Must contain:

- context/problem;
- objective;
- data and 13-station network;
- seven CMIP6 GCMs;
- SSP2-4.5 and SSP5-8.5;
- 11 ETCCDI indices;
- QDM;
- baseline 1995–2014;
- key validated findings;
- concise implication.

All numerical values must trace to authoritative outputs.

### Introduction

Establish:

- importance of precipitation extremes;
- relevance to water resources and flood risk;
- limitations of raw GCM precipitation;
- value of CMIP6;
- need for local/regional evaluation;
- research gap for Uttaradit/northern Thailand;
- explicit objectives.

Do not claim a literature gap without verifying the cited literature.

### Methods

Include:

- study area;
- station network;
- observations;
- CMIP6 models;
- SSP scenarios;
- baseline;
- ETCCDI definitions;
- model evaluation;
- QDM;
- spatial interpolation;
- projection calculation;
- statistical procedures actually implemented.

### Results

Include:

- observed climatology;
- ETCCDI spatial patterns;
- GCM historical performance;
- bias-correction performance;
- future projections;
- model spread;
- SSP comparison;
- spatial heterogeneity.

### Discussion

Discuss:

- model performance;
- effect of QDM;
- projected changes;
- scenario interpretation;
- spatial heterogeneity;
- implications;
- limitations;
- comparison with literature.

Avoid causal claims not directly tested.

### Conclusions

State only evidence-supported conclusions.

---

## 17. Figures

The intended final figure set is:

### Figure 1
Study-area map with 13 stations.

Requirements:
- authoritative boundary;
- correct station coordinates;
- readable labels;
- consistent projection/scale;
- publication-quality typography.

### Figure 2
Observed baseline/spatial rainfall distribution and IDW visualization.

Clearly identify interpolation.

### Figure 3
11-index ETCCDI matrix/distribution visualization.

The 11 indices must remain consistent with the project definition.

### Figure 4
GCM historical evaluation and bias reduction.

Clearly distinguish raw versus bias-corrected model performance.

### Figure 5
Future projections under SSP2-4.5 and SSP5-8.5.

Show the seven-model ensemble and model spread where supported.

### Figure 6

DO NOT create an uncertainty-decomposition figure unless an authoritative uncertainty decomposition exists.

If an older manuscript contains such a figure based on unsupported percentages, remove it or replace it with an evidence-supported visualization.

Target publication quality:

- 600 dpi PNG for raster outputs;
- vector PDF where possible;
- readable at approximately 180 mm journal width;
- consistent fonts and units;
- no misleading visual encodings.

---

## 18. Tables

### Table 1 — Station information

Include, where authoritative:

- station ID;
- station name;
- latitude;
- longitude;
- elevation;
- observation period;
- completeness.

### Table 2 — CMIP6 GCMs

Include:

- model;
- institution/source where verified;
- historical period;
- SSP scenarios;
- relevant data provenance.

### Table 3 — ETCCDI definitions

Include all 11 indices with:

- acronym;
- definition;
- units;
- threshold/reference-period details where applicable.

### Table 4 — Historical GCM evaluation

Use actual model performance metrics from project output.

### Table 5 — Bias-correction results

Clearly distinguish raw bias, corrected bias, and percentage reduction.

### Table 6 — Future projections

Include:

- baseline;
- SSP2-4.5;
- SSP5-8.5;
- absolute changes;
- relative changes;
- model/MME distinction.

Do not create columns for unsupported uncertainty components.

---

## 19. Numerical consistency requirements

The following must remain internally consistent:

**Observed network mean:** 1139.81 mm, subject to verification from authoritative output.

**Bias-corrected seven-GCM historical baseline:** 1068.48 mm.

**SSP2-4.5 MME:** 1092.08 mm.

**SSP2-4.5 change:** +23.60 mm / +2.21%.

**SSP2-4.5 arithmetic mean of model-specific % changes:** +2.50%.

**SSP5-8.5 MME:** 1080.18 mm.

**SSP5-8.5 change:** +11.70 mm / +1.10%.

**SSP5-8.5 arithmetic mean of model-specific % changes:** +1.16%.

**Network aggregate bias reduction:** 77.2%.

**Arithmetic mean of model-specific bias reductions:** 73.3%.

These values are cross-check values. The agent must verify the actual frozen outputs before finalizing.

---

## 20. Critical distinction: MME change vs mean of model changes

The manuscript must not treat these as identical:

### MME relative change

Calculated from the seven-GCM ensemble mean:

SSP2-4.5 = **+2.21%**

SSP5-8.5 = **+1.10%**

### Arithmetic mean of individual model percentage changes

SSP2-4.5 = **+2.50%**

SSP5-8.5 = **+1.16%**

If both are reported, label them explicitly.

Do not average percentages and call the result an MME change.

---

## 21. Model and scenario interpretation

Do not assume SSP5-8.5 must produce a larger precipitation increase than SSP2-4.5.

The frozen results show:

- SSP2-4.5 MME: +2.21%
- SSP5-8.5 MME: +1.10%

This should be reported as the actual ensemble result, without forcing a monotonic scenario narrative.

Possible interpretation may discuss model spread, nonlinear precipitation response, internal variability, or scenario/model interactions only when supported by evidence and clearly framed as interpretation rather than established causality.

---

## 22. Literature and references

All references must be traceable and verified.

The agent must check:

- author names;
- publication year;
- article title;
- journal;
- volume/issue;
- pages or article number;
- DOI where available;
- citation/reference-list consistency.

Do not fabricate citations.

Do not infer a reference's exact bibliographic metadata from memory when the project already contains the source.

If a cited claim is not supported by the referenced paper, flag it for review rather than silently rewriting the science.

---

## 23. QDM disclosure requirement

The Methods and Limitations sections must disclose the provenance of the bias-corrected outputs accurately.

Recommended substance:

The analysis used precomputed QDM-corrected CMIP6 precipitation artifacts available in the project workspace; the current repository does not contain a live executable raw-to-QDM processing script, so complete end-to-end reproducibility of the bias-correction step is a limitation.

The exact wording should be adapted to the actual manuscript and journal style.

Do not claim that the correction can be reproduced from the repository alone if it cannot.

---

## 24. IDW disclosure requirement

The manuscript must distinguish interpolation from prediction/downscaling.

If IDW is used to generate spatial maps:

- identify it as spatial interpolation;
- report validation metrics only where actually calculated;
- avoid implying physical downscaling;
- avoid claiming universal predictive performance.

---

## 25. Manuscript quality-control gates

### Gate A — Data provenance
All datasets used are identifiable and traceable.

### Gate B — Baseline
All baseline-dependent results use 1995–2014 unless explicitly justified by the project.

### Gate C — Model ensemble
Seven GCM names and two SSP scenarios are consistent everywhere.

### Gate D — ETCCDI
All 11 indices match the actual implementation.

### Gate E — QDM
The correction method and provenance are described accurately.

### Gate F — Numerical consistency
Every major number in Abstract, Results, Discussion, tables, captions, and conclusions traces to authoritative outputs.

### Gate G — Projection baseline
Future changes are referenced to the seven-GCM bias-corrected historical baseline where specified.

### Gate H — Bias-correction metrics
77.2% and 73.3% are not conflated.

### Gate I — MME arithmetic
MME relative change is not confused with arithmetic mean of model-specific percentage changes.

### Gate J — Uncertainty
No unsupported ANOVA/variance-decomposition percentages remain.

### Gate K — Spatial interpretation
No unsupported causal topographic or climatic claims remain.

### Gate L — Figures
Maps, plots, labels, units, station IDs, model names, scenarios, and values agree.

### Gate M — References
Citation and reference list are internally consistent and bibliographically verified.

### Gate N — Provenance
Final manuscript artifacts, figures, tables, and reports have provenance metadata.

### Gate O — No fabrication
Any missing evidence becomes UNKNOWN/HOLD rather than being filled by assumption.

---

## 26. Final execution sequence

The Antigravity agent should execute in this exact order:

1. Inspect `C:\MyPython\CMIP6Uttaradit`.
2. Identify authoritative source files and frozen outputs.
3. Inspect README/configuration/manifests.
4. Inspect observation and station metadata.
5. Inspect CMIP6 model/scenario metadata.
6. Inspect ETCCDI definitions and outputs.
7. Inspect QDM artifacts and provenance.
8. Inspect historical evaluation outputs.
9. Inspect bias-correction outputs.
10. Inspect projection outputs.
11. Inspect current manuscript.
12. Cross-check every major numerical claim.
13. Correct manuscript inconsistencies using authoritative evidence.
14. Verify all tables.
15. Verify all figures and captions.
16. Remove unsupported uncertainty-decomposition claims.
17. Check topographic/physical interpretation for causal overreach.
18. Verify citations and references.
19. Run final-proof checks.
20. Generate final manuscript artifact only after all gates pass.
21. Generate a human-readable audit report.
22. Generate a machine-readable manifest with hashes and execution metadata.
23. Do not alter the frozen analysis pipeline.

---

## 27. Definition of DONE

The task is complete only when:

- the manuscript uses the authoritative 1995–2014 baseline;
- all seven GCMs are correctly represented;
- both SSP2-4.5 and SSP5-8.5 are correctly represented;
- all 11 ETCCDI indices are correctly defined;
- QDM provenance is accurately disclosed;
- future changes are correctly referenced to the seven-GCM bias-corrected historical baseline;
- +2.21% and +1.10% are not confused with +2.50% and +1.16%;
- 77.2% and 73.3% are not conflated;
- unsupported uncertainty-decomposition percentages are absent;
- IDW is not misrepresented as physical downscaling;
- topographic/causal language is appropriately qualified;
- tables and figures are internally consistent;
- references are verified;
- provenance is recorded;
- final QA gates PASS;
- no fabricated evidence exists.

If any gate fails, return:

**HOLD**

with:

- exact failure;
- affected file;
- supporting evidence;
- required corrective action.

Do not silently proceed.

---

## 28. Frozen package reference

The Project 2 portable package previously designated as final is:

`C:\MyPython\CMIP6Uttaradit_PORTABLE_Q2Q3_v1.0.zip`

Previously recorded SHA-256:

`1e1593574426556106d6962afc9945381c14ca23baa2cf022034ba9c4e58e1046`

Previously recorded size:

**66,777,751 bytes**

Treat this package as frozen. Verify the actual workspace/package identity if required. Do not regenerate or replace it unless explicitly instructed.

---

## 29. Final agent report format

At completion, return exactly these sections:

### STATUS
PASS / HOLD / FAIL

### AUTHORITATIVE SOURCES
List the actual files used.

### DATA AND METHODS VERIFIED
Summarize verified data period, baseline, models, scenarios, ETCCDI indices, QDM provenance, and spatial method.

### CHANGES
List every manuscript/table/figure/reference file changed.

### VALIDATION
Report each quality-control gate as PASS/FAIL.

### KEY SCIENTIFIC FINDINGS
Report only evidence-supported findings.

### NUMERICAL CONFLICTS
List all conflicts found. If none, state `None found`.

### PROVENANCE
List final artifact paths, hashes, and relevant manifest identifiers.

### LIMITATIONS
List only limitations supported by the project evidence, including QDM provenance if applicable.

### UNRESOLVED RISKS
List only risks actually observed.

Never claim PASS merely because code executed successfully. PASS means the scientific evidence, manuscript, figures, tables, references, provenance, and defined QA gates all passed.
