# FINAL VALIDATION REPORT - UTTARADIT EXTREME-RAINFALL PIPELINE v1.1

- Input dataset: `CMIP6Uttaradit/Observed_Rain_daily_198101_201412_Uttaradit.csv`
- Code version: `uttaradit_designrain_refit_v1.1.py`
- Number of stations: 13
- Analysis period: 1981–2014 (34 complete years, 12,418 daily records)
- Annual-max sample size: n = 34
- Bootstrap replicates: B = 2000
- Bootstrap seeds: fixed_selection = 0, selection_inclusive = 2024
- Phase 0 Gate Result: PASS
- Phase 1 Gate Result: PASS

## Final Production Gates Summary

| Gate | Description | Status |
| :--- | :--- | :--- |
| GATE 1 | DATA INTEGRITY | PASS |
| GATE 2 | CANONICAL NUMERICAL INTEGRITY | PASS |
| GATE 3 | GEV VALIDITY | PASS |
| GATE 4 | BOOTSTRAP VALIDITY | PASS |
| GATE 5 | BOOTSTRAP AUDIT COMPLETENESS | PASS |
| GATE 6 | RETURN-LEVEL VALIDITY | PASS |
| GATE 7 | REPRODUCIBILITY | PASS |
| GATE 8 | RESUME SAFETY | PASS |
| GATE 9 | 351012 REGRESSION | PASS |
| GATE 10 | DETERMINISTIC REGRESSION | PASS |
| GATE 11 | MANUSCRIPT NUMERICAL CONSISTENCY | PASS |
| GATE 12 | FINAL ARTIFACT CONSISTENCY | PASS |
| GATE 13 | FINAL REPORT COMPLETENESS | PASS |

## Bootstrap Replicate Summary

- Total requested replicates: 52000
- Total accepted replicates: 52000
- Total rejected replicates: 0
- Minimum station acceptance rate: 100.00%
- GEV likelihood violations: 257
- GEV nesting violations: 130
- Return level monotonicity failures: 0
- Optimizer failures: 0
- Selection failures: 0

## Station 351012 Canonical Summary

- Model selected: Gumbel
- Gumbel AICc: 365.4
- GEV refit AICc: 367.7
- LP3 AICc: 366.0
- GEV xi shape: -0.0128
- Return levels (R2-R100): [99.9, 145.8, 176.2, 214.6, 243.1, 271.3]

**FINAL SCIENTIFIC READINESS STATUS**: PASS - READY FOR MANUSCRIPT REVISION
