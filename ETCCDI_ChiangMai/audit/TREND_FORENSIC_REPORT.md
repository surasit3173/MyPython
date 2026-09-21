# Trend Forensic Audit Report

- **Station**: Chiang Mai (WMO 48327 / TMD 327501)
- **Period**: 1961–2019 (N = 59 years)
- **Significance Threshold**: Alpha = 0.05
- **Multiple Testing Correction**: Benjamini–Hochberg False Discovery Rate (BH-FDR)

## 1. Summary of Autocorrelation Diagnostics & Primary Method Selection

Serial dependence evaluated on trend-removed residuals:
- **Flagged for Serial Dependence**:
  - `R50mm` (ACF Lag-5 = -0.2768 exceeding Bartlett bound ±0.2552) -> Primary Method: `Hamed_Rao_modified_MK`
  - `R99p` (ACF Lag 1 = -0.2653 exceeds Bartlett bound 0.2552) -> Primary Method: `Hamed_Rao_modified_MK`
- **Retained Ordinary MK**: Remaining 9 indices (`PRCPTOT`, `SDII`, `Rx1day`, `Rx5day`, `CDD`, `CWD`, `R10mm`, `R20mm`, `R95p`).

## 2. Master Trend Results Table

| Index | Unit | N | Kendall Tau | Sen Slope (/yr) | Sen Slope (/decade) | 95% CI Low | 95% CI High | Primary Test | P Raw | P FDR | Direction | Significance |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PRCPTOT | mm | 59 | -0.0847 | -1.5311 | -15.3111 | -4.6890 | 1.4925 | Ordinary_MK | 0.346353 | 0.706706 | Decreasing | Non-significant |
| SDII | mm/day | 59 | -0.0935 | -0.0104 | -0.1037 | -0.0306 | 0.0089 | Ordinary_MK | 0.298412 | 0.706706 | Decreasing | Non-significant |
| Rx1day | mm | 59 | 0.0643 | 0.1632 | 1.6316 | -0.2372 | 0.5849 | Ordinary_MK | 0.475958 | 0.706706 | Increasing | Non-significant |
| Rx5day | mm | 59 | -0.0105 | -0.0435 | -0.4348 | -0.7302 | 0.6125 | Ordinary_MK | 0.911479 | 0.911479 | Decreasing | Non-significant |
| CDD | days | 59 | 0.0503 | 0.1212 | 1.2121 | -0.2973 | 0.5652 | Ordinary_MK | 0.578214 | 0.706706 | Increasing | Non-significant |
| CWD | days | 59 | -0.0526 | -0.0000 | -0.0000 | -0.0426 | 0.0385 | Ordinary_MK | 0.556118 | 0.706706 | No detectable trend | Non-significant |
| R10mm | days | 59 | -0.0240 | -0.0000 | -0.0000 | -0.1111 | 0.0980 | Ordinary_MK | 0.793285 | 0.872614 | No detectable trend | Non-significant |
| R20mm | days | 59 | -0.0959 | -0.0370 | -0.3704 | -0.1064 | 0.0303 | Ordinary_MK | 0.284601 | 0.706706 | Decreasing | Non-significant |
| R50mm | days | 59 | -0.0579 | -0.0000 | -0.0000 | -0.0270 | 0.0238 | Hamed_Rao_modified_MK | 0.451230 | 0.706706 | No detectable trend | Non-significant |
| R95p | mm | 59 | -0.0678 | -0.7786 | -7.7857 | -2.7161 | 1.0968 | Ordinary_MK | 0.452017 | 0.706706 | Decreasing | Non-significant |
| R99p | mm | 59 | 0.0222 | -0.0000 | -0.0000 | -1.1895 | 1.3448 | Hamed_Rao_modified_MK | 0.532865 | 0.706706 | No detectable trend | Non-significant |

## 3. Key Findings & Sensitivity Analysis
- **Zero-Slope Handling**: `CWD`, `R10mm`, `R50mm`, and `R99p` have zero Sen's slope (|slope| <= 1e-6) and are strictly classified as "No detectable trend".
- **Statistical Significance**: All 11 extreme precipitation indices at Chiang Mai show **no statistically significant trend** over 1961–2019 (both raw p > 0.05 and FDR-adjusted p > 0.05 for all indices).
- **Trend Sensitivity**: 100% agreement on inference (all 11 non-significant) between Ordinary Mann-Kendall and Hamed-Rao Modified Mann-Kendall tests.
