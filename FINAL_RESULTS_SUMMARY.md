# FINAL RESULTS SUMMARY — NE THAILAND MARKOV RAINFALL ANALYSIS

## Key Findings
1. **Markov Order Selection**: BIC decisively favors an **Order 2 Markov chain** over Order 1 across all 10 stations (Delta BIC = -108.3 to -1027.3).
2. **Spatial Heterogeneity**:
   - Dry State Frequency ($Freq_D$): 0.731 (Nakhon Phanom) to 0.828 (Nakhon Ratchasima / Chaiyaphum)
   - Rainy State Frequency ($Freq_R$): 0.131 (Nakhon Ratchasima) to 0.223 (Nakhon Phanom)
   - Dry Persistence ($P_{DD}$): 0.763 to 0.803
   - Rainy Persistence ($P_{RR}$): 0.428 to 0.540
   - State Shannon Entropy ($H_{state}$): 0.794 to 1.020 bits
3. **Temporal Stability (1961–2019)**:
   - Autocorrelation-corrected Yue-Wang Mann-Kendall test with False Discovery Rate (FDR) control found **no statistically significant monotonic trends** ($q > 0.05$) in rainfall frequency, persistence, or entropy.
   - Period-to-period comparison (1961–1990 vs 1991–2019) confirms multi-decadal structural stability.

## Deliverables Generated
- Final Manuscript DOCX: `12_manuscript/APST_LongTerm_Rainfall_Occurrence_Regimes_Northeastern_Thailand.docx`
- Master Results Excel: `MASTER_RESULTS_APST_MARKOV.xlsx` (18 sheets)
- Traceability Workbook: `MANUSCRIPT_TRACEABILITY.xlsx`
- Figures: `11_figures/Figure1_study_area_network.png` through `Figure5_regime_synthesis.png` (PNG and PDF)
- Audit Reports: `SOURCE_IMPORT_AUDIT.md`, `DATA_QA_REPORT.md`, `MARKOV_ORDER_AUDIT_REPORT.md`, `SPELL_AUDIT_REPORT.md`, `ENTROPY_AUDIT_REPORT.md`, `TREND_AUDIT_REPORT.md`, `VALIDATION_REPORT.md`, `FINAL_PUBLICATION_AUDIT_REPORT.md`, `FINAL_QA_REPORT.md`, `FINAL_RESULTS_SUMMARY.md`.
