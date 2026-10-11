# Data Audit Report
**Station**: WMO 48378 | ID 378201 | Phitsanulok, Thailand
**Study period**: 1961–2019

## 1. File Summary
- Input file: `C:\MyPython\2Station\Observed_Rain_daily_complete_1961_2019_378201_wmo48378_Phitsanulok.csv`
- Total data rows: 21,549
- Date range in file: 1961-01-01 to 2019-12-31
- Year range: 1961–2019
- Expected total days (1961–2019): 21,549
- Actual rows: 21,549

## 2. Duplicate Dates
- Count: **0**

## 3. Missing Calendar Dates
- Count: **0**

## 4. Precipitation Data Issues
- Non-numeric values: **0**
- Missing (NaN) values: **244**
- Negative values: **0**
- Suspect values (>500.0 mm/day): **0**

## 5. Annual Completeness
- Years meeting ≥90% completeness threshold: **59** / 59
- Years NOT meeting threshold: **0**

### Per-Year Table (first/last 5 shown here; full table in TABLE_01_DATA_QUALITY.xlsx)

| Year | Expected | Available | Missing | Completeness% | Valid |
|------|----------|-----------|---------|---------------|-------|
| 1961 | 365 | 365 | 0 | 100.00 | True |
| 1962 | 365 | 365 | 0 | 100.00 | True |
| 1963 | 365 | 365 | 0 | 100.00 | True |
| 1964 | 366 | 366 | 0 | 100.00 | True |
| 1965 | 365 | 365 | 0 | 100.00 | True |
| 2015 | 365 | 365 | 0 | 100.00 | True |
| 2016 | 366 | 366 | 0 | 100.00 | True |
| 2017 | 365 | 365 | 0 | 100.00 | True |
| 2018 | 365 | 365 | 0 | 100.00 | True |
| 2019 | 365 | 365 | 0 | 100.00 | True |

## 6. Year 2019 Verification
- Expected days: 365
- Available days: 365
- Missing days: 0
- Completeness: 100.00%
- Valid_annual_record: **True**

## 7. Audit Conclusion
No imputation was performed. Missing values are documented above.
Data used in ETCCDI calculations follows the ≥90% completeness rule per ETCCDI guidelines.