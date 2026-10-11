# FINAL RESULTS SUMMARY
## ETCCDI Extreme Precipitation Analysis — Phitsanulok, Thailand
## WMO Station 48378 (TMD ID 378201)
## Study Period: 1961–2019 (59 years)

*Generated from computed pipeline outputs. All values sourced from raw data computations.*

---

## 1. Study Parameters

| Parameter | Value |
|-----------|-------|
| Station | Phitsanulok (WMO 48378, TMD 378201) |
| Province | Phitsanulok, Thailand |
| Coordinates | 16.78°N, 100.27°E; 45 m a.s.l. |
| Study period | 1961–2019 |
| Number of years | 59 |
| Total daily observations | 21,549 |
| Wet-day threshold | ≥ 1.0 mm/day |
| Percentile baseline | 1981–2010 |
| Significance level | α = 0.05 |
| Multiple-testing correction | Benjamini–Hochberg FDR |

---

## 2. Data Completeness

| Metric | Result |
|--------|--------|
| Years with 100% completeness | 59/59 |
| Missing calendar dates | 0 |
| Missing precipitation values | 0 |
| Negative precipitation values | 0 |
| Duplicate dates | 0 |
| 2019 calendar days | 365 (complete) |
| Valid_annual_record (2019) | TRUE |

---

## 3. Baseline Percentile Thresholds (1981–2010)

| Metric | Value |
|--------|-------|
| Baseline wet days (N) | 2,622 |
| P95 threshold | 49.895 mm |
| P99 threshold | 82.116 mm |

---

## 4. Descriptive Statistics — 11 ETCCDI Annual Indices (1961–2019)

| Index | Unit | N | Mean | Median | SD | Min | Max | Q25 | Q75 | IQR | CV% |
|-------|------|---|------|--------|-----|-----|-----|-----|-----|-----|-----|
| PRCPTOT | mm | 59 | 1321.45 | 1326.00 | 241.86 | 850.20 | 1849.60 | 1154.85 | 1506.00 | 351.15 | 18.3 |
| SDII | mm/day | 59 | 14.80 | 14.58 | 1.91 | 11.19 | 18.89 | 13.34 | 16.05 | 2.72 | 12.9 |
| Rx1day | mm | 59 | 94.66 | 88.30 | 35.81 | 48.00 | 265.70 | 71.65 | 109.35 | 37.70 | 37.8 |
| Rx5day | mm | 59 | 163.88 | 153.30 | 52.41 | 81.80 | 315.00 | 129.50 | 178.15 | 48.65 | 32.0 |
| CDD | days | 59 | 57.34 | 52.00 | 16.76 | 33.00 | 111.00 | 46.50 | 65.00 | 18.50 | 29.2 |
| CWD | days | 59 | 7.95 | 7.00 | 2.15 | 4.00 | 13.00 | 6.00 | 9.00 | 3.00 | 27.1 |
| R10mm | days | 59 | 40.49 | 40.00 | 6.86 | 25.00 | 61.00 | 37.00 | 43.50 | 6.50 | 16.9 |
| R20mm | days | 59 | 21.47 | 22.00 | 4.78 | 12.00 | 36.00 | 18.00 | 24.50 | 6.50 | 22.2 |
| R50mm | days | 59 | 4.53 | 4.00 | 2.14 | 0.00 | 11.00 | 3.00 | 6.00 | 3.00 | 47.2 |
| R95p | mm | 59 | 322.44 | 331.00 | 159.68 | 0.00 | 714.60 | 230.25 | 421.95 | 191.70 | 49.5 |
| R99p | mm | 59 | 99.01 | 88.30 | 109.11 | 0.00 | 434.40 | 0.00 | 180.25 | 180.25 | 110.2 |

---

## 5. Autocorrelation Diagnostics (Lags 1–10)

Significance bound: ±2/√59 = ±0.2604

| Index | ACF lag-1 | ACF lag-2 | sig_lag1 | any_sig_lag1–5 | Method applied |
|-------|-----------|-----------|----------|----------------|----------------|
| PRCPTOT | −0.0154 | −0.1179 | FALSE | FALSE | Ordinary MK |
| SDII | −0.1335 | −0.3423 | FALSE | TRUE | Ordinary MK |
| Rx1day | +0.0332 | −0.1961 | FALSE | FALSE | Ordinary MK |
| Rx5day | −0.0492 | −0.1832 | FALSE | FALSE | Ordinary MK |
| CDD | −0.1316 | +0.0193 | FALSE | FALSE | Ordinary MK |
| CWD | +0.1443 | +0.0965 | FALSE | FALSE | Ordinary MK |
| R10mm | +0.0653 | −0.1981 | FALSE | FALSE | Ordinary MK |
| R20mm | −0.0266 | −0.0830 | FALSE | FALSE | Ordinary MK |
| R50mm | −0.0457 | −0.1034 | FALSE | FALSE | Ordinary MK |
| R95p | −0.1813 | −0.1960 | FALSE | FALSE | Ordinary MK |
| R99p | −0.0752 | −0.2666 | FALSE | TRUE | Ordinary MK |

**Finding**: No index exhibited significant lag-1 autocorrelation. Ordinary Mann–Kendall
was applied to all 11 indices. No autocorrelation correction was required.

---

## 6. Trend Analysis Results (1961–2019)

| Index | N | Kendall τ | Sen's slope (unit/yr) | Sen's slope (unit/decade) | 95% CI low | 95% CI high | p-value (raw) | p-value (FDR) | Trend | Method |
|-------|---|-----------|----------------------|--------------------------|-----------|------------|--------------|--------------|-------|--------|
| PRCPTOT | 59 | −0.070 | −1.6042 mm/yr | −16.042 mm/decade | −5.8605 | +2.5034 | 0.4403 | 0.9894 | Non-significant decreasing | Ordinary MK |
| SDII | 59 | +0.037 | +0.0076 mm/d/yr | +0.076 mm/d/decade | −0.0347 | +0.0502 | 0.6851 | 0.9894 | Non-significant increasing | Ordinary MK |
| Rx1day | 59 | +0.050 | +0.1324 mm/yr | +1.324 mm/decade | −0.4062 | +0.7827 | 0.5828 | 0.9894 | Non-significant increasing | Ordinary MK |
| Rx5day | 59 | +0.023 | +0.0633 mm/yr | +0.633 mm/decade | −0.6286 | +0.8043 | 0.8037 | 0.9894 | Non-significant increasing | Ordinary MK |
| CDD | 59 | −0.012 | 0.0000 d/yr | 0.000 d/decade | −0.6667 | +0.5000 | 0.8959 | 0.9894 | Non-significant decreasing | Ordinary MK |
| CWD | 59 | −0.109 | 0.0000 d/yr | 0.000 d/decade | −0.0714 | 0.0000 | 0.2198 | 0.9894 | Non-significant decreasing | Ordinary MK |
| R10mm | 59 | −0.068 | −0.0400 d/yr | −0.400 d/decade | −0.1667 | +0.0722 | 0.4510 | 0.9894 | Non-significant decreasing | Ordinary MK |
| R20mm | 59 | −0.023 | 0.0000 d/yr | 0.000 d/decade | −0.1000 | +0.0714 | 0.7979 | 0.9894 | Non-significant decreasing | Ordinary MK |
| R50mm | 59 | +0.002 | 0.0000 d/yr | 0.000 d/decade | −0.0667 | +0.0667 | 0.9894 | 0.9894 | Non-significant decreasing | Ordinary MK |
| R95p | 59 | +0.005 | +0.0388 mm/yr | +0.388 mm/decade | −3.3281 | +3.5188 | 0.9635 | 0.9894 | Non-significant increasing | Ordinary MK |
| R99p | 59 | +0.029 | 0.0000 mm/yr | 0.000 mm/decade | −1.4893 | +2.2917 | 0.7437 | 0.9894 | Non-significant decreasing | Ordinary MK |

---

## 7. Significant Trends

- **Significant trends (raw p < 0.05)**: **0 out of 11**
- **Significant trends (FDR-adjusted p < 0.05)**: **0 out of 11**

No ETCCDI index showed a statistically significant long-term trend over 1961–2019.

---

## 8. Robustness (Sensitivity Analysis)

All 11 indices showed consistent trend direction and significance across:
- Model A: Ordinary Mann–Kendall
- Model B: Hamed–Rao modified Mann–Kendall
- Model C: Sen's slope

All indices classified as **Robust = TRUE** (agreement on non-significance across methods).

---

## 9. Key Scientific Interpretation

1. **Stable extreme precipitation regime**: Over the 59-year study period (1961–2019), Phitsanulok experienced
   no statistically significant monotonic trend in any of 11 ETCCDI extreme precipitation indices.

2. **High natural variability dominates**: Inter-annual variability (CV 12.9%–110.2%) substantially exceeds
   any trend signal, consistent with ENSO-driven monsoon variability in northern Thailand.

3. **No intensification of extremes**: Rx1day and Rx5day showed small, non-significant positive Sen's slopes,
   providing no statistical evidence for rainfall intensification.

4. **No change in dry/wet spell duration**: CDD and CWD both exhibited non-significant trends, indicating
   no detectable shift in dry or wet spell persistence.

5. **Autocorrelation not a confounding factor**: All annual series lacked significant lag-1 autocorrelation,
   confirming that ordinary Mann–Kendall was methodologically appropriate.

6. **FDR correction conservative**: After Benjamini–Hochberg FDR correction, no results changed from the
   raw-p analysis, as all raw p-values were already well above α = 0.05.

---

## 10. Limitations

- Single-station analysis; spatial gradients within Phitsanulok Province not resolved.
- Observational uncertainty from instrument changes over 59 years cannot be fully excluded.
- Baseline-period dependence of R95p and R99p (1981–2010 thresholds).
- Statistical absence of trend ≠ causal attribution; no attribution analysis performed.
- Statistical power to detect weak trends is limited at N = 59 annual observations.

---

## 11. Output Files

| Category | Files |
|----------|-------|
| Data | annual_ETCCDI_1961_2019.csv, TABLE_03_ETCCDI_ANNUAL.xlsx |
| Statistics | trend_analysis.xlsx, autocorrelation_analysis.xlsx, trend_sensitivity.xlsx, fdr_analysis (embedded) |
| Tables | TABLE_01–TABLE_06.xlsx, TABLE_S1–TABLE_S5.xlsx |
| Figures | FIGURE_01–FIGURE_06.png |
| Manuscript | Manuscript_Q3_ETCCDI_Phitsanulok.docx, .md |
| Audit | DATA_AUDIT_REPORT.md |

---

*This summary reports only results computed from the raw data. No values were manufactured or assumed.*
