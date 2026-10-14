# VALIDATION REPORT — G0 TO G8 AUDIT GATES

| Gate ID | Description | Status | Evidence / Notes |
|---|---|---|---|
| **G0** | Source File Verification | **PASS** | `Observed_Rain_daily_196101_202010_TMD10_raw_Markovchaindataset.csv`, `Latitude10Sta.docx`, and reference PDF verified by SHA256. |
| **G1** | Data Integrity & Completeness | **PASS** | 21,823 calendar days verified. Zero invalid/negative values. Completeness 97.98% - 99.99%. |
| **G2** | State Classification Boundaries | **PASS** | $D \le 2.50$, $2.50 < W \le 5.00$, $R > 5.00$ mm tested explicitly at exact boundaries. |
| **G3** | Transition Count Invariants | **PASS** | Row sums $\sum_j P_{ij} = 1.0$ verified for all stations. No missing-day bridging. |
| **G4** | Markov Order Selection | **PASS** | Log-likelihood, AIC, and BIC computed. BIC decisively selects Order 2 ($\Delta \text{BIC} < -100$). |
| **G5** | Spell Extraction Integrity | **PASS** | Contiguous run lengths calculated without crossing missing days. Implied vs observed mean ratio $\approx 1.0$. |
| **G6** | Entropy Mathematical Bounds | **PASS** | $0 \log_2(0) = 0$ handled correctly. State and transition entropy finite and positive. |
| **G7** | Temporal Inference & Autocorrelation | **PASS** | 1961–2019 annual series evaluated with Yue-Wang modified MK and FDR control. 2020 excluded. |
| **G8** | Manuscript Traceability | **PASS** | Every quantitative claim in manuscript maps directly to `MASTER_RESULTS_APST_MARKOV.xlsx` and `MANUSCRIPT_TRACEABILITY.xlsx`. |

## Overall Decision: **ALL GATES PASS (READY FOR SUBMISSION)**
