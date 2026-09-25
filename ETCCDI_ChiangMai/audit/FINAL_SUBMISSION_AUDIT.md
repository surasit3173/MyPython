# FINAL SUBMISSION AUDIT REPORT — CHIANG MAI ETCCDI ANALYSIS

**Project**: ETCCDI Extreme Precipitation Analysis — Chiang Mai, Thailand
**Station**: Chiang Mai Synoptic Station (TMD ID: 327501 | WMO ID: 48327)
**Location**: 18.77°N, 98.97°E, Elevation 312.0 m a.s.l.
**Study Period**: 1961–2019 (59 calendar years)
**Authoritative CSV**: `data/raw/Observed_Rain_daily_complete_1961_2019_327501_wmo48327_ChiangMai.csv`
**SHA-256 Hash**: `0a9e0e4e797049d44730a5fa9274f2e552d21ac99240588097a34ba4cb95d35b`

---

## 1. Final Quality Gate Statuses

SHA_GATE = PASS
CI_GATE = PASS
HR_VERIFICATION_GATE = PASS
FDR_GATE = PASS
FIGURE_PROVENANCE_GATE = PASS
MANUSCRIPT_NUMBER_GATE = PASS
REPRODUCIBILITY_GATE = PASS

OVERALL_STATUS = PASS

---

## 2. Exact Verified Parameters & Counts

- **Valid years**: 59 (1961–2019)
- **Excluded years**: 0
- **Total daily observations**: 21,549 valid daily records across 59 years (100.0% completeness)
- **Year 2019 Status**: 365 unique dates, 365 valid precipitation observations, 0 missing/duplicate dates
- **Significant trends**: 0
- **Non-significant trends**: 11 (PRCPTOT, SDII, Rx1day, Rx5day, CDD, CWD, R10mm, R20mm, R50mm, R95p, R99p)
- **Serial-dependent indices**: 2 (R50mm: ACF Lag-5 = -0.2768 exceeding Bartlett bound ±0.2552; R99p: ACF Lag-1 = -0.2653 exceeding Bartlett bound ±0.2552)
- **Primary statistical methods**:
  - `Ordinary_MK` (Ordinary Mann–Kendall): 9 indices (PRCPTOT, SDII, Rx1day, Rx5day, CDD, CWD, R10mm, R20mm, R95p)
  - `Hamed_Rao_modified_MK` (Hamed–Rao Modified Mann–Kendall): 2 indices (R50mm, R99p)

---

## 3. Specific Gate Verification Details

### 3.1 SHA_GATE = PASS
- Direct raw CSV SHA-256 hash computed as `0a9e0e4e797049d44730a5fa9274f2e552d21ac99240588097a34ba4cb95d35b`.
- Exact match confirmed across `config.yaml`, `DATA_PROVENANCE.md`, `SHA256_MANIFEST.txt`, `FINAL_QA_REPORT.md`, `FINAL_RESULTS_SUMMARY.md`, and `data_qc.py`.

### 3.2 CI_GATE = PASS
- Theil-Sen slope and 95% CIs calculated once from authoritative annual series.
- PRCPTOT Sen slope = -15.3111 mm/decade, 95% CI = [-49.6562, +17.6444] mm/decade (-49.66 to +17.64 mm/decade).
- Propagated consistently across all tables, manuscript text, figure annotations, and summary reports (0 discrepancy).

### 3.3 HR_VERIFICATION_GATE = PASS
- R50mm residual ACF Lag-5 = -0.2768 (exceeds Bartlett bound ±0.2552). Ljung-Box Q(5) p = 0.057962. Hamed-Rao MMK P = 0.451230.
- R99p residual ACF Lag-1 = -0.2653 (exceeds Bartlett bound ±0.2552). Ljung-Box Q(5) p = 0.287624. Hamed-Rao MMK P = 0.532865.
- Value-by-value independent cross-check of Tau, S, VarS, Z, P, Sen Slope, and 95% CIs saved in `INDEPENDENT_VERIFICATION.xlsx` with zero discrepancy.

### 3.4 FDR_GATE = PASS
- BH-FDR procedure applied to all 11 primary test p-values.
- Minimum adjusted p-value = 0.706706.
- 100% agreement on non-significance before and after FDR adjustment across pipeline and independent verifier.

### 3.5 FIGURE_PROVENANCE_GATE = PASS
- All 5 publication PNG figures generated directly from final statistical objects.
- Zero artwork titles inside canvas; panel labels `(a)`, `(b)`, `(c)` only.
- Figure 2 & 3: Annotated with robust Theil-Sen intercept (`scipy.stats.theilslopes`) and primary test tags (`MK` vs `HR-MK`).
- Figure 4: Redesigned into 3 unit-consistent panels (mm/decade, mm day⁻¹ decade⁻¹, days/decade).
- Figure 5: Redesigned with Lags 1–10 residual ACF matrix highlighting Bartlett bounds (±0.2552) and Ljung-Box Q(5) p-values.

### 3.6 MANUSCRIPT_NUMBER_GATE = PASS
- Zero hardcoded numbers in `manuscript.py`.
- Rx1day (35.7–166.5 mm), Rx5day (84.5–296.3 mm), CDD (35–187 days), CWD (4–16 days), May–Oct rainfall (86.8%), August mean (226.9 mm), September mean (217.2 mm), R50mm Ljung-Box P (0.0580), and PRCPTOT CI [-49.66 to +17.64] computed dynamically from statistical objects.
- Audited in `FINAL_NUMERICAL_CONSISTENCY.xlsx` with zero discrepancy.

### 3.7 REPRODUCIBILITY_GATE = PASS
- Executed two consecutive end-to-end pipeline runs in locked environment (`pandas==3.0.6, numpy==2.5.3, scipy==1.18.1, statsmodels==0.15.0, pymannkendall==1.4.3, python-docx==1.2.0, pyyaml==6.0.3`).
- 100% byte-for-byte and numerical identity confirmed between runs.

---

**AUDIT CONCLUSION**: All 7 quality gates passed. OVERALL_STATUS = PASS.
