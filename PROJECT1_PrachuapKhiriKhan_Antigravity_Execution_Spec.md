# PROJECT 1 — Prachuap Khiri Khan
## Antigravity Execution Specification for Publication-Ready Manuscript

**Purpose:** This document is an execution specification for an AI agent operating inside the existing Antigravity workspace. The agent must use the actual Project 1 files as the authoritative source of evidence and must complete the manuscript/submission preparation without inventing, estimating, or silently changing scientific results.

---

## 1. Project identity

**Project:** Prachuap Khiri Khan precipitation trend analysis

**Workspace:**
`C:\MyPython\CMIP6PrachuapKhiriKhan`

**Primary objective:** Prepare the Project 1 research article for submission to a Q2–Q3 journal using the already completed and frozen statistical analysis.

**Important:** The statistical analysis is CLOSED/LOCKED. Do NOT rerun, redesign, recalibrate, or replace the statistical results unless an explicit contradiction is discovered in the authoritative project files. If a contradiction is found, STOP and report it instead of choosing a value by assumption.

---

## 2. Mandatory operating rules

The agent MUST:

1. Read the existing project files before making substantive decisions.
2. Treat actual project files and frozen outputs as the primary evidence.
3. Preserve the existing numerical results exactly unless an explicit authoritative correction is documented.
4. Distinguish:
   - FACT
   - COMPUTED
   - INFERRED
   - INTERPRETATION
   - HYPOTHESIS
   - UNKNOWN
   - ERROR
5. Never convert UNKNOWN, HYPOTHESIS, EXPECTED, or INFERRED information into FACT without evidence.
6. Never fabricate data, references, station values, statistical results, figures, tables, geographic information, or journal requirements.
7. Never use synthetic fallback data.
8. Never delete frozen evidence.
9. Never silently overwrite authoritative outputs.
10. Keep a provenance trail for every substantive manuscript result.
11. If files disagree, identify the conflict and HOLD rather than guessing.
12. Do not claim that an analysis was performed if no corresponding executable/output evidence exists.
13. Do not claim causal mechanisms unless directly supported by the study design.
14. Do not claim field-wide significance when only an individual unadjusted station is significant.
15. Do not claim Q1/Q2 acceptance or acceptance probability. The appropriate status is readiness for peer review/submission.

---

## 3. Authoritative workspace structure

First inspect the workspace recursively enough to identify authoritative sources.

Expected important locations include:

- `config.yaml`
- `main.py`
- `README.md`
- `src/`
- `tests/`
- `data/`
- `output/`
- `manifests/`
- `manuscript/`
- `review_output/`
- `scripts/`
- original/reference implementation files such as `Comparative_4MMK.py`

The agent must determine which files are authoritative from their contents, provenance, timestamps, hashes, manifests, and explicit project documentation. Do not assume that the oldest or newest file is automatically authoritative.

---

## 4. Frozen data identity

The canonical observed daily rainfall dataset is:

`Observed_Rain_daily_198101_201412_Prachuap Khiri Khan.csv`

A second naming variant may exist:

`Observed_Rain_daily_198101_201412_PrachuapKhiriKhan.csv`

The two datasets were previously established as byte-for-byte identical. Preserve the canonical identity found in the project files and verify against the project's own provenance records if needed.

Canonical dataset SHA-256 previously recorded:

`abdec5e39458b3441bcce139517b3eacc8855f85f2ec5e6ce06e295a280e31ed`

Do not replace the dataset.

The study contains **12 rainfall stations**. Station coordinates are stored in:

`station_coordinates_PrachuapKhiriKhan.csv`

An elevation file exists:

`ค่าความสูงสถานีอุตุนิยมวิทยา.xlsx`

Use the actual files to confirm all station metadata before reproducing any table.

---

## 5. Frozen statistical methodology

### Primary trend method

The production analysis uses:

**Yue & Wang (2004) AR(1) modified Mann–Kendall (MMK)**

The purpose is to account for lag-1 autocorrelation after Sen-slope detrending.

### Secondary method

**Standard Mann–Kendall (MK)**

### Sensitivity method

**Trend-Free Pre-Whitening Mann–Kendall (TFPW-MK)**

TFPW-MK is an exploratory sensitivity analysis. It must NOT be presented as the primary inferential method.

### Hamed & Rao

Hamed & Rao modified MK was evaluated during methodological validation but was **excluded from the production primary analysis** because the implemented formulation can produce an invalid/negative variance under strong negative rank autocorrelation in the project's data context. Do not restore Hamed–Rao as a primary method unless explicitly instructed.

---

## 6. Critical methodological correction

A previous implementation incorrectly estimated autocorrelation using raw ranks without Sen-slope detrending.

The production implementation was corrected so that Yue–Wang autocorrelation is evaluated using **Sen-slope-detrended residuals**.

This correction is scientifically important.

The manuscript must describe the final production method, not the superseded implementation.

Do not reproduce obsolete Hamed–Rao or raw-rank autocorrelation results from old reports unless explicitly identifying them as rejected/superseded validation history.

---

## 7. Final production annual results

Use the latest authoritative production output in the workspace as the source of truth.

The following values are the currently frozen production values and may be used to cross-check the files:

| Station | Mean annual rainfall (mm) | Sen slope (mm/year) | Standard MK Z | Standard MK p | Yue–Wang r1 | Yue–Wang ratio | Yue–Wang Z | Yue–Wang p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 500001 | 983.66 | +7.410 | +1.142 | 0.2536 | +0.2290 | 1.0000 | +1.142 | 0.2536 |
| 500002 | 1376.19 | +9.175 | +2.253 | 0.0242 | -0.1386 | 1.0000 | +2.253 | 0.0242 |
| 500003 | 1100.02 | -5.933 | -1.453 | 0.1463 | +0.4551 | 2.5801 | -0.904 | 0.3658 |
| 500004 | 1106.00 | +2.355 | +0.534 | 0.5936 | +0.1891 | 1.0000 | +0.534 | 0.5936 |
| 500005 | 1147.21 | -1.090 | -0.237 | 0.8125 | +0.4048 | 2.2930 | -0.157 | 0.8755 |
| 500006 | 1203.06 | +1.354 | +0.534 | 0.5936 | +0.1717 | 1.0000 | +0.534 | 0.5936 |
| 500007 | 1133.56 | -2.254 | -0.830 | 0.4064 | +0.1531 | 1.0000 | -0.830 | 0.4064 |
| 500008 | 1206.31 | -0.650 | -0.267 | 0.7896 | +0.0177 | 1.0000 | -0.267 | 0.7896 |
| 500009 | 1176.53 | +0.583 | +0.460 | 0.6458 | +0.1699 | 1.0000 | +0.460 | 0.6458 |
| 500201 | 1108.24 | +3.511 | +0.623 | 0.5335 | +0.0542 | 1.0000 | +0.623 | 0.5335 |
| 500202 | 944.14 | -4.376 | -1.156 | 0.2476 | -0.3619 | 0.4800 | -1.669 | 0.0951 |
| 500301 | 1064.85 | -0.621 | -0.296 | 0.7669 | -0.1054 | 1.0000 | -0.296 | 0.7669 |

**Important:** These values are cross-check values, not permission to overwrite the actual frozen output. If the workspace's latest authoritative output differs, STOP and report the discrepancy.

---

## 8. Multiple-testing conclusion

The final analysis applies **Benjamini–Hochberg FDR at q = 0.05** across the 12 station-level annual trend tests.

The smallest unadjusted p-value is:

`p = 0.0242`

The first BH threshold is:

`0.05 / 12 = 0.00417`

Therefore:

**No station remains statistically significant after BH-FDR adjustment.**

Station **500002** is nominally significant only at the unadjusted single-station level.

The manuscript MUST therefore say, in substance:

- no field-wide/network-wide station survives BH-FDR correction;
- station 500002 is significant only before multiplicity correction;
- the provincial network does not provide evidence for a statistically significant monotonic annual rainfall trend after controlling the false discovery rate.

Do NOT describe 500002 as evidence of a province-wide significant trend.

---

## 9. Interpretation rules

The manuscript may discuss spatial heterogeneity of rainfall trends.

It may state that positive and negative Sen slopes occur among stations and that the magnitude/direction varies spatially.

It MUST NOT claim that a specific trend is caused by:

- coastal convection,
- topography,
- monsoon dynamics,
- land-use change,
- urbanization,
- ENSO,
- or another physical mechanism

unless the project contains a direct analysis supporting that mechanism.

Use cautious language such as:

- “spatial heterogeneity”
- “station-specific variation”
- “consistent with spatially varying hydroclimatic influences”

rather than unsupported causal attribution.

---

## 10. Study period and observations

The canonical daily rainfall period is:

**January 1981 – December 2014**

The agent must inspect the actual data and project documentation to determine the precise annual aggregation and missing-data handling used in the final analysis.

Do not introduce a different baseline period without explicit evidence.

Historical validation previously confirmed that annual rainfall totals for station 500001 for 1981–1985 matched the processed output exactly:

`446.5, 740.9, 749.4, 661.5, 729.0 mm`

These are validation evidence, not new results.

---

## 11. Manuscript objective and scientific framing

The article should be framed as a methodological and hydroclimatic assessment of spatial variability in annual rainfall trends across Prachuap Khiri Khan using:

1. observed daily rainfall,
2. annual aggregation,
3. Sen's slope,
4. standard Mann–Kendall,
5. Yue–Wang AR(1) modified Mann–Kendall,
6. TFPW-MK sensitivity analysis,
7. multiple-testing control using BH-FDR.

The central scientific conclusion should remain conservative:

**The station network exhibits heterogeneous positive and negative rainfall tendencies, but no station-level annual trend remains statistically significant after BH-FDR correction.**

Do not manufacture a stronger conclusion.

---

## 12. Tables to prepare

Prepare publication-quality tables based strictly on actual project outputs.

### Table 1
Station metadata:

- station ID
- station name, if available
- latitude
- longitude
- elevation, if authoritative
- observation period
- data completeness, if verified

### Table 2
Annual rainfall trend results:

- station
- mean annual rainfall
- Sen slope
- MK S
- variance, where appropriate
- standard MK Z
- standard MK p
- Yue–Wang r1
- variance correction ratio
- Yue–Wang Z
- Yue–Wang p
- significance status
- BH-FDR adjusted p, if available

### Table 3
Method comparison/sensitivity:

Compare standard MK, Yue–Wang MMK, and TFPW-MK using actual outputs.

Do not elevate sensitivity results above the primary method.

---

## 13. Figures

The intended publication-quality figure set is:

### Figure 1
Study-area map with the 12 rainfall stations.

Use the authoritative geographic boundary and station coordinates from the project files.

### Figure 2
Spatial distribution of mean annual rainfall, using the project's validated IDW/spatial visualization where appropriate.

Do not imply that IDW is a predictive model if it is only being used for visualization.

### Figure 3
Annual rainfall variability/anomaly visualization and/or station-by-year heatmap, using actual outputs.

### Figure 4
Method comparison showing standard MK versus Yue–Wang MMK and sensitivity results.

### Figure 5
Autocorrelation effect, clearly explaining how Yue–Wang adjustment changes inference for stations where correction is active.

All figures should be:

- publication quality,
- legible at journal column width,
- consistent typography,
- scientifically restrained,
- 600 dpi PNG where raster output is required,
- vector PDF where possible.

Do not fabricate geographic layers or station locations.

---

## 14. Statistical terminology

Use precise terminology:

- “monotonic trend” rather than “linear trend” for Mann–Kendall inference.
- “Sen's slope” rather than generic “trend coefficient.”
- “lag-1 autocorrelation” for Yue–Wang correction.
- “false discovery rate” for BH-FDR.
- “nominally significant” for p < 0.05 before multiplicity correction.
- “field-significant” or “network-wide significant” only when justified by the selected multiplicity procedure.

Do not equate statistical significance with practical importance.

---

## 15. Methods section requirements

The Methods section must contain enough information for reproducibility.

It should document:

- observation period;
- station network;
- rainfall variable and units;
- annual aggregation;
- treatment of missing observations;
- Sen's slope;
- standard MK;
- Yue & Wang AR(1) modification;
- detrending procedure before autocorrelation estimation;
- significance level;
- BH-FDR procedure and family definition;
- TFPW-MK as sensitivity analysis;
- software/package provenance where available.

Where an implementation detail is not supported by project files, mark it UNKNOWN and inspect the relevant source rather than guessing.

---

## 16. Results section requirements

The Results must:

1. Report the station network and data characteristics.
2. Describe the spatial distribution of rainfall.
3. Report station-level trend magnitudes.
4. Distinguish standard MK from Yue–Wang inference.
5. Report the effect of autocorrelation correction where material.
6. Apply BH-FDR correctly.
7. Explicitly state that no station survives FDR correction.
8. Identify 500002 as nominally significant only if useful for transparency.
9. Avoid unsupported physical causal explanations.

---

## 17. Discussion requirements

Discuss:

- spatial heterogeneity;
- implications of autocorrelation for rainfall trend inference;
- why multiplicity correction matters for multi-station studies;
- comparison with relevant peer-reviewed literature;
- limitations of station density and observation period;
- limitations of statistical attribution.

Do not claim a causal climate mechanism unless directly tested.

Do not overstate generalizability beyond the station network and study period.

---

## 18. Reference integrity

All references must be traceable.

At minimum, verify the actual references used for:

- Mann–Kendall;
- Sen's slope;
- Yue & Wang;
- TFPW-MK;
- BH-FDR;
- relevant rainfall/extreme-precipitation literature.

Do NOT invent DOI, volume, page, author, or year information.

If a reference is uncertain, mark it UNKNOWN and verify it before inclusion.

The article's citation numbering must be internally consistent with the actual reference list.

---

## 19. Existing methodological history that must NOT contaminate the manuscript

The following are historical validation findings and should not appear as final production methodology unless explicitly described in a methodological appendix:

- the original raw-rank autocorrelation implementation;
- the unsupported variance lower-bound/clamp;
- the Hamed–Rao production attempt;
- DOMAIN_ERR caused by negative Hamed–Rao variance;
- superseded preliminary Yue–Wang values;
- synthetic test datasets.

These are engineering/validation history, not final scientific results.

---

## 20. Manuscript quality-control gates

Before declaring the manuscript complete, perform these checks.

### Gate A — Numerical consistency
Every number in Abstract, Results, Discussion, Tables, captions, and Conclusions must trace to an authoritative output.

### Gate B — Statistical consistency
The method described must match the method actually used.

### Gate C — Multiple-testing consistency
No statement may imply field significance when BH-FDR rejects it.

### Gate D — Figure/table consistency
Station IDs, values, labels, units, and ordering must agree across all components.

### Gate E — Reference consistency
Every citation must exist in the reference list and every listed reference should be cited where appropriate.

### Gate F — Terminology consistency
Use “Yue–Wang AR(1) MMK” consistently for the primary method.

### Gate G — Provenance
Record the source file/output for each major numerical claim.

### Gate H — No fabrication
If evidence is missing, report UNKNOWN/HOLD rather than filling the gap.

---

## 21. Final execution sequence

The Antigravity agent should execute in this order:

1. Inspect workspace.
2. Identify authoritative files and frozen outputs.
3. Read existing manuscript draft(s).
4. Read configuration and statistical source code.
5. Read manifests/provenance.
6. Cross-check all manuscript numbers against authoritative outputs.
7. Correct manuscript text where it conflicts with frozen evidence.
8. Correct tables.
9. Correct figure references/captions.
10. Verify references.
11. Perform final-proof checks.
12. Generate the final manuscript artifact only after all gates pass.
13. Generate a machine-readable and human-readable audit report.
14. Generate a final manifest containing file hashes and execution metadata.
15. Do NOT alter the locked statistical pipeline.

---

## 22. Definition of DONE

The task is complete only if all of the following are true:

- manuscript content is consistent with frozen Project 1 evidence;
- primary method is Yue & Wang (2004) AR(1) MMK;
- standard MK is secondary;
- TFPW-MK is sensitivity analysis;
- Hamed–Rao is not presented as production primary;
- Sen-detrended residual autocorrelation is correctly described;
- BH-FDR q=0.05 is correctly applied to the 12 annual station tests;
- no station is incorrectly reported as field-significant;
- station 500002 is not overinterpreted;
- no unsupported causal claim remains;
- all figures/tables are consistent;
- references are verified;
- provenance is recorded;
- final QA reports PASS;
- no fabricated evidence exists.

If any gate fails, the agent must return **HOLD** with the exact failure and supporting file path(s). It must not silently proceed.

---

## 23. Final frozen package reference

The Project 1 portable package previously designated as final is:

`C:\MyPython\CMIP6PrachuapKhiriKhan_PORTABLE_Q2Q3_v1.1.zip`

Previously recorded SHA-256:

`513a0bbb3b39452e753c0e5d096d7c2533d74dcaca4265ef58468376aecb6635`

Treat the package as frozen. Verify against the actual workspace if package identity is relevant. Do not regenerate or replace it unless explicitly instructed.

---

## 24. Agent output format

At completion, return a concise final report with exactly these sections:

### STATUS
PASS / HOLD / FAIL

### AUTHORITATIVE SOURCES
List the files actually used.

### CHANGES
List every manuscript/table/figure/reference file changed.

### VALIDATION
Report each gate as PASS/FAIL.

### KEY SCIENTIFIC CONCLUSION
State the final conclusion without overinterpretation.

### NUMERICAL CONFLICTS
List any conflicts found. If none, state `None found`.

### PROVENANCE
List final artifact paths and hashes.

### UNRESOLVED RISKS
List only risks that are actually observed.

Never claim PASS merely because a script ran successfully. PASS means the evidence, scientific interpretation, manuscript, figures, tables, references, and provenance all passed the defined gates.
