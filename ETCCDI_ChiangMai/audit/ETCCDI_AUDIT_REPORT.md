# ETCCDI Calculation Audit Report

- **Station**: Chiang Mai (WMO 48327 / TMD 327501)
- **Period**: 1961–2019 (59 calendar years)
- **Primary Baseline Period**: 1981–2010
- **Wet Day Definition**: P >= 1.0 mm
- **Percentile Estimator**: Hyndman-Fan Type 8 (`np.percentile(..., method='median_unbiased')`)

## 1. Baseline Percentile Thresholds

| Baseline Period | Wet Days Count | P95 Threshold (mm) | P99 Threshold (mm) | Mean Annual R95p (mm) | Mean Annual R99p (mm) |
|---|---|---|---|---|---|
| 1961–1990 | 2,769 | 40.208 | 71.993 | 316.59 | 81.99 |
| 1971–2000 | 2,699 | 42.100 | 73.000 | 283.47 | 88.09 |
| 1981–2010 (Primary) | 2,712 | 41.315 | 72.889 | 296.22 | 79.54 |

## 2. ETCCDI 11 Indices Master Verification
- **Total Annual Rows**: 59
- **Completeness**: All 59 years meet 100% daily completeness requirement.
- **Year 2019 Verification**:
  - PRCPTOT = 971.7 mm
  - SDII = 12.46 mm/day
  - Rx1day = 81.6 mm
  - Rx5day = 126.3 mm
  - CDD = 135 days
  - CWD = 9 days
  - R10mm = 30 days
  - R20mm = 16 days
  - R50mm = 4 days
  - R95p = 276.0 mm
  - R99p = 81.6 mm

## 3. Cross-Year & Rule Compliance
- Continuous running 5-day totals and wet/dry spells evaluated without artificial boundary truncation.
- Baseline sensitivity results saved in `output/statistics/PERCENTILE_BASELINE.xlsx` and `output/statistics/TABLE_S_BASELINE_SENSITIVITY.xlsx`.
- Master datasets saved in `output/data/annual_ETCCDI_ChiangMai_1961_2019.csv` and `.xlsx`.
