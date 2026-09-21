# FINAL RESULTS SUMMARY: ETCCDI Extreme Precipitation Analysis — Chiang Mai, Thailand

## 1. Station & Data Information
- **Station Name**: Chiang Mai
- **Station ID (TMD)**: 327501
- **WMO Station ID**: 48327
- **Province**: Chiang Mai
- **Country**: Thailand
- **Latitude / Longitude / Elevation**: 18.77°N, 98.97°E, 312.0 m a.s.l.
- **Study Period**: 1961–2019 (59 calendar years)
- **Authoritative CSV**: `data/raw/Observed_Rain_daily_complete_1961_2019_327501_wmo48327_ChiangMai.csv`
- **SHA-256 Hash**: `0a9e0e4e797049d44730a5fa9274f2e552d21ac99240588097a34ba4cb95d35b`
- **Total Observed Daily Records**: 21,549 (100.0% completeness across all 59 years)
- **Year 2019 Status**: 365 valid daily observations (100.0% complete)
- **Missing Dates / Duplicates / Negative Precip / Extreme Suspect (>500mm)**: 0 / 0 / 0 / 0

## 2. Percentile Baseline & Sensitivity (1981–2010 Primary)
- **Percentile Estimator**: Hyndman-Fan Type 8 (`np.percentile(..., method='median_unbiased')`)
- **Wet Day Definition**: P ≥ 1.0 mm
- **1981–2010 Baseline Wet Days**: 2,712 wet days
- **P95 Threshold**: 41.315 mm
- **P99 Threshold**: 72.889 mm
- **Baseline Sensitivity Comparison**:
  - 1961–1990: P95 = 41.840 mm, P99 = 72.389 mm (2,769 wet days)
  - 1971–2000: P95 = 42.100 mm, P99 = 71.204 mm (2,699 wet days)
  - 1981–2010: P95 = 41.315 mm, P99 = 72.889 mm (2,712 wet days)

## 3. Descriptive Statistics (1961–2019)
- **PRCPTOT**: Mean = 1153.94 mm, SD = 213.45 mm, Median = 1146.90 mm, IQR = 266.15 mm
- **SDII**: Mean = 12.51 mm/day, SD = 1.46 mm/day, Median = 12.57 mm/day, IQR = 2.30 mm/day
- **Rx1day**: Mean = 82.61 mm, SD = 27.66 mm, Median = 75.10 mm, IQR = 34.45 mm
- **Rx5day**: Mean = 141.34 mm, SD = 41.40 mm, Median = 137.30 mm, IQR = 50.20 mm
- **CDD**: Mean = 80.90 days, SD = 30.64 days, Median = 80.00 days, IQR = 41.00 days
- **CWD**: Mean = 8.71 days, SD = 2.79 days, Median = 8.00 days, IQR = 3.50 days
- **R10mm**: Mean = 36.59 days, SD = 6.88 days, Median = 36.00 days, IQR = 9.00 days
- **R20mm**: Mean = 17.90 days, SD = 4.46 days, Median = 18.00 days, IQR = 5.00 days
- **R50mm**: Mean = 2.76 days, SD = 1.66 days, Median = 2.00 days, IQR = 2.00 days
- **R95p**: Mean = 274.91 mm, SD = 125.61 mm, Median = 267.10 mm, IQR = 147.75 mm
- **R99p**: Mean = 79.54 mm, SD = 92.37 mm, Median = 75.10 mm, IQR = 122.50 mm

## 4. Autocorrelation Diagnostics & Selected Primary Methods
- **Residual Autocorrelation & Ljung-Box Test (Lags 1–5)**:
  - `PRCPTOT`: ACF1 = -0.0472, LjungBox p = 0.9361, Selected: `Ordinary_MK`
  - `SDII`: ACF1 = 0.1817, LjungBox p = 0.1086, Selected: `Ordinary_MK`
  - `Rx1day`: ACF1 = -0.1632, LjungBox p = 0.2941, Selected: `Ordinary_MK`
  - `Rx5day`: ACF1 = -0.0840, LjungBox p = 0.6171, Selected: `Ordinary_MK`
  - `CDD`: ACF1 = 0.1758, LjungBox p = 0.1857, Selected: `Ordinary_MK`
  - `CWD`: ACF1 = -0.1412, LjungBox p = 0.7058, Selected: `Ordinary_MK`
  - `R10mm`: ACF1 = -0.0866, LjungBox p = 0.5098, Selected: `Ordinary_MK`
  - `R20mm`: ACF1 = 0.0422, LjungBox p = 0.9673, Selected: `Ordinary_MK`
  - `R50mm`: ACF1 = 0.1938, ACF5 = -0.2768 (EXCEEDS BARTLETT BOUND ±0.2552), LjungBox p = 0.0580, Selected: `Hamed_Rao_modified_MK`
  - `R95p`: ACF1 = 0.1478, LjungBox p = 0.2337, Selected: `Ordinary_MK`
  - `R99p`: ACF1 = -0.2653 (EXCEEDS BARTLETT BOUND ±0.2552), LjungBox p = 0.2876, Selected: `Hamed_Rao_modified_MK`

## 5. Final Trend Analysis Results
- **PRCPTOT**: Tau = -0.0847, Sen Slope = -15.3111 mm/dec, 95% CI = [-49.656, 17.644], P_raw = 0.346353, P_FDR = 0.706706, Status = Non-significant
- **SDII**: Tau = -0.0935, Sen Slope = -0.1037 (mm/day)/dec, 95% CI = [-0.338, 0.133], P_raw = 0.298412, P_FDR = 0.706706, Status = Non-significant
- **Rx1day**: Tau = 0.0643, Sen Slope = +1.6316 mm/dec, 95% CI = [-2.667, 5.630], P_raw = 0.475958, P_FDR = 0.706706, Status = Non-significant
- **Rx5day**: Tau = -0.0105, Sen Slope = -0.4348 mm/dec, 95% CI = [-6.063, 5.676], P_raw = 0.911479, P_FDR = 0.911479, Status = Non-significant
- **CDD**: Tau = 0.0503, Sen Slope = +1.2121 days/dec, 95% CI = [-3.000, 4.800], P_raw = 0.578214, P_FDR = 0.706706, Status = Non-significant
- **CWD**: Tau = -0.0526, Sen Slope = 0.0000 days/dec, 95% CI = [-0.556, 0.227], P_raw = 0.556118, P_FDR = 0.706706, Status = Non-significant (No detectable trend)
- **R10mm**: Tau = -0.0240, Sen Slope = 0.0000 days/dec, 95% CI = [-1.250, 0.952], P_raw = 0.793285, P_FDR = 0.872614, Status = Non-significant (No detectable trend)
- **R20mm**: Tau = -0.0959, Sen Slope = -0.3704 days/dec, 95% CI = [-1.053, 0.270], P_raw = 0.284601, P_FDR = 0.706706, Status = Non-significant
- **R50mm**: Tau = -0.0579, Sen Slope = 0.0000 days/dec, 95% CI = [-0.294, 0.000], P_raw = 0.451230, P_FDR = 0.706706, Status = Non-significant (No detectable trend)
- **R95p**: Tau = -0.0678, Sen Slope = -7.7857 mm/dec, 95% CI = [-25.500, 13.837], P_raw = 0.452017, P_FDR = 0.706706, Status = Non-significant
- **R99p**: Tau = 0.0222, Sen Slope = 0.0000 mm/dec, 95% CI = [0.000, 0.000], P_raw = 0.532865, P_FDR = 0.706706, Status = Non-significant (No detectable trend)

## 6. Trend Sensitivity & Robustness
- **Ordinary MK vs Hamed-Rao Modified MK**: 100% agreement on non-significance across all 11 indices.

## 7. Methodological Limitations & Interpretation
- **Single-Station Scope**: Results represent local conditions in Chiang Mai Intermontane Basin.
- **Statistical Resolution**: Wide 95% Sen-slope confidence intervals indicate that absence of detection reflects finite sample statistical resolution, not physical stationarity.

## 8. Machine-Readable Status
```yaml
DATA_GATE: PASS
ETCCDI_GATE: PASS
TREND_GATE: PASS
INDEPENDENT_VERIFY_GATE: PASS
TABLE_GATE: PASS
FIGURE_GATE: PASS
MANUSCRIPT_GATE: PASS
REPRODUCIBILITY_GATE: PASS

OVERALL_STATUS: PASS
```
