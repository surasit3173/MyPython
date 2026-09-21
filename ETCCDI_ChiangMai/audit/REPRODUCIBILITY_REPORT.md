# Pipeline Reproducibility Audit Report

- **Station**: Chiang Mai (WMO 48327 / TMD 327501)
- **Runs Tested**: 2 Consecutive Independent Runs from Raw CSV
- **ETCCDI Annual Series Difference Max**: `0.0`
- **Trend P-Value Difference Max**: `0.0`
- **Byte-for-Byte / Numerical Identity**: **MATCH (100% REPRODUCIBLE)**

## Verification Summary
1. Raw CSV SHA-256 hash verified and unchanged between runs (`0a9e0e4e797049d44730a5fa9274f2e552d21ac99240588097a34ba4cb95d35b`).
2. All 11 ETCCDI annual indices reproduced identically across runs.
3. Autocorrelation diagnostics, Ljung-Box test results, and Bartlett bounds reproduced identically.
4. Primary test selection, Kendall tau, Sen's slope, 95% CIs, and BH-FDR p-values reproduced identically.
5. Overall Reproducibility Gate Status: **PASS**
