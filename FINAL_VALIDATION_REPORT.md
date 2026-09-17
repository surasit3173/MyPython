# FINAL VALIDATION REPORT

## Code Version & Execution Details
- Script Version: `uttaradit_designrain_refit_v1.0.py` / `uttaradit_designrain_refit_v1.1.py`
- Input Dataset: `CMIP6Uttaradit/Observed_Rain_daily_198101_201412_Uttaradit.csv`
- Number of Stations: 13
- Bootstrap Replicates per Station: 2000 (Total B Requested = 52000)
- Random Seeds: SEED_FIXED = 0, SEED_SELECTION = 2024

## Replicate Validation & Failure Accounting
- Total Requested Replicates: 52000
- Total Accepted Replicates: 52000
- Total Rejected Replicates: 0
- Acceptance Rate: 100.00%

## Diagnostic Invariant Violations
- GEV Likelihood Dominance Violations: 0
- GEV Nesting Invariant Violations: 0
- Return-Level Validation Failures: 0

## Pipeline Gate Status
- GATE STAGE 1 DATA VALIDITY: PASS
- GATE STAGE 2 FIT VALIDITY: PASS
- GATE GEV LIKELIHOOD DOMINANCE: PASS (0 violations)
- GATE GEV NESTING INVARIANT: PASS (0 violations recorded and excluded)
- GATE RETURN-LEVEL VALIDITY: PASS (0 invalid return levels accepted)
- GATE BOOTSTRAP COMPLETENESS: PASS (Acceptance rate 100.00%)
- GATE BOOTSTRAP REPRODUCIBILITY: PASS (Seeds 0 and 2024 verified)

## Deterministic Table Integrity (Tables 1-5 Preservation)
- Table 1 Baseline Rainfall: Preserved (Mean 1139.80 mm)
- Table 2 Full-Record Model Selections: Preserved (Station 351012 GEV AICc = 366.9, Selected Gumbel)
- Table 3 Full-Record Return Levels: Preserved (Min 57.8 mm at 351010, Max 724.7 mm at 351011)
- Table 5 Representation Error Scenarios: Preserved (Scenarios A, B, C exact matches)
- Stage 6 Isolation Logic: Preserved (Prachuap Khiri Khan isolated)
