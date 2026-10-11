# VALIDATION REPORT — TREND ANALYSIS PIPELINE

- **Project Name:** CMIP6_PrachuapKhiriKhan_Rainfall_Trend_Analysis
- **Pipeline Version:** 3.0.0
- **Primary Trend Method:** yue_wang_2004 (Yue & Wang 2004 AR(1) MMK)
- **Secondary Reference:** standard_mk (Standard Mann-Kendall)
- **Validation Gate Status:** PASS
- **Observed Dataset:** data/Observed_Rain_daily_198101_201412_PrachuapKhiriKhan.csv
- **Station Count:** 12
- **Analysis Period:** [1981, 2014]

## Validation Rules Checked & Passed:
1. File existence validation gate
2. Date schema & non-duplication check
3. Zero-missing-value assertion
4. Station count match check
5. Yue & Wang (2004) AR(1) domain check (|r1| < 1.0, Var*(S) > 0)
