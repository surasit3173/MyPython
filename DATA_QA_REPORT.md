# DATA QA REPORT — MARKOV RAINFALL ANALYSIS (NORTHEASTERN THAILAND)

## Executive Summary
- **Audit Target Date**: 1961-01-01 to 2020-10-30
- **Expected Station Network**: 10 TMD Stations (353201, 354201, 356201, 357201, 381201, 403201, 405201, 407501, 431201, 432201)
- **Data Integrity Audit Status**: **FAILED / HALTED**

## Audit Findings
1. **Primary Raw File Status**: `Observed_Rain_daily_196101_202010_TMD10_raw_Markovchaindataset.csv` is missing from the repository.
2. **Metadata File Status**: `Latitude10Sta.docx` is missing from the repository.
3. **Reference Paper Status**: `Application of Markov chain on daily rainfall data in Paraíba-Brazil from 1995-2015.pdf` is missing from the repository.

## Action Plan to Unblock
Once the prompt owner provides/uploads the three authoritative files:
1. Re-run Gate 0 (File / Provenance Verification).
2. Re-run Gate 1 (Data Integrity & Missingness Quantifier).
3. Re-run Gate 2 (Boundary Value State Classification: D <= 2.50 mm, 2.50 < W <= 5.00 mm, R > 5.00 mm).
4. Re-run Gate 3 (Transition Count Invariants: adjacent observed days only, row sums = 1).
5. Complete Model Selection (Gate 4), Spell Analysis (Gate 5), Entropy (Gate 6), and Serial Correlation-Aware Trend Analysis (Gate 7).
6. Generate `MASTER_RESULTS_APST_MARKOV.xlsx` and draft the APST manuscript.
