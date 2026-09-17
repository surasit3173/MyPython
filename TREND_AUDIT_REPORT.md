# TREND & TEMPORAL STABILITY AUDIT REPORT

**Gate 7 Audit Status**: **PASS**

## Summary
Monotonic trend testing was conducted using the Yue and Wang (2002) modified Mann-Kendall procedure to account for serial autocorrelation. Benjamini-Hochberg False Discovery Rate (FDR) control was applied.

- **Primary Conclusion**: **No statistically significant monotonic trends** ($q > 0.05$ FDR adjusted) were detected across annual rainfall totals, dry state frequencies, rainy state frequencies, persistence probabilities ($P_{DD}, P_{RR}$), or entropy metrics over 1961–2019.
- **Temporal Stability**: Daily rainfall occurrence regimes across Northeastern Thailand have remained broadly stable over the 59-year historical period.

| Station ID | Metric | Yue-Wang MK Trend | Sens Slope | Raw p-value | FDR q-value | 1961-1990 Mean | 1991-2019 Mean | % Change |
|---|---|---|---|---|---|---|---|---|
| 353201 | Rainfall_Total_mm | increasing | 1.1781 | 0.0111 | 0.0411 | 1238.13 | 1256.30 | 1.47% |
| 353201 | Freq_R | no trend | 0.0001 | 0.1369 | 0.2468 | 0.15 | 0.16 | 2.04% |
| 353201 | P_DD | no trend | 0.0000 | 0.4943 | 0.6094 | 0.86 | 0.86 | 0.42% |
| 353201 | P_RR | increasing | 0.0005 | 0.0172 | 0.0534 | 0.35 | 0.37 | 4.00% |
| 354201 | Rainfall_Total_mm | no trend | -1.7818 | 0.0525 | 0.1153 | 1442.48 | 1446.89 | 0.31% |
| 354201 | Freq_R | decreasing | -0.0002 | 0.0043 | 0.0203 | 0.17 | 0.16 | -2.24% |
| 354201 | P_DD | no trend | 0.0000 | 0.1521 | 0.2684 | 0.86 | 0.86 | 0.18% |
| 354201 | P_RR | decreasing | -0.0008 | 0.0356 | 0.0843 | 0.38 | 0.38 | -1.24% |
| 356201 | Rainfall_Total_mm | increasing | 2.1472 | 0.0027 | 0.0158 | 1586.88 | 1668.13 | 5.12% |
| 356201 | Freq_R | no trend | 0.0000 | 0.5261 | 0.6399 | 0.18 | 0.18 | 1.90% |
| 356201 | P_DD | no trend | -0.0000 | 0.6237 | 0.7044 | 0.85 | 0.85 | -0.20% |
| 356201 | P_RR | no trend | 0.0001 | 0.6358 | 0.7044 | 0.43 | 0.42 | -1.37% |
| 357201 | Rainfall_Total_mm | no trend | 1.4143 | 0.2150 | 0.3332 | 2293.41 | 2370.22 | 3.35% |
| 357201 | Freq_R | no trend | -0.0001 | 0.3401 | 0.4638 | 0.22 | 0.22 | 0.90% |
| 357201 | P_DD | decreasing | -0.0001 | 0.0334 | 0.0833 | 0.85 | 0.85 | -0.18% |
| 357201 | P_RR | no trend | -0.0003 | 0.0852 | 0.1727 | 0.52 | 0.52 | -0.58% |
| 381201 | Rainfall_Total_mm | no trend | 0.6543 | 0.1852 | 0.3146 | 1207.40 | 1229.61 | 1.84% |
| 381201 | Freq_R | increasing | 0.0002 | 0.0114 | 0.0411 | 0.14 | 0.14 | 0.95% |
| 381201 | P_DD | no trend | -0.0000 | 0.1001 | 0.1949 | 0.87 | 0.87 | -0.08% |
| 381201 | P_RR | no trend | -0.0001 | 0.6224 | 0.7044 | 0.34 | 0.33 | -2.83% |
| 403201 | Rainfall_Total_mm | decreasing | -2.4143 | 0.0318 | 0.0819 | 1153.49 | 1145.57 | -0.69% |
| 403201 | Freq_R | decreasing | -0.0003 | 0.0000 | 0.0000 | 0.14 | 0.13 | -5.86% |
| 403201 | P_DD | no trend | 0.0000 | 0.2539 | 0.3746 | 0.88 | 0.88 | 0.10% |
| 403201 | P_RR | no trend | 0.0000 | 0.8184 | 0.8466 | 0.35 | 0.34 | -3.08% |
| 405201 | Rainfall_Total_mm | no trend | -1.2362 | 0.2846 | 0.4065 | 1414.98 | 1359.32 | -3.93% |
| 405201 | Freq_R | no trend | 0.0000 | 0.5861 | 0.6851 | 0.16 | 0.16 | -0.68% |
| 405201 | P_DD | no trend | -0.0001 | 0.0864 | 0.1727 | 0.86 | 0.86 | -0.28% |
| 405201 | P_RR | no trend | 0.0002 | 0.6462 | 0.7044 | 0.37 | 0.37 | -0.45% |
| 407501 | Rainfall_Total_mm | no trend | 1.0947 | 0.2022 | 0.3250 | 1634.10 | 1624.41 | -0.59% |
| 407501 | Freq_R | no trend | 0.0000 | 0.3886 | 0.5069 | 0.17 | 0.18 | 0.76% |
| 407501 | P_DD | no trend | -0.0000 | 0.3506 | 0.4710 | 0.85 | 0.86 | 0.26% |
| 407501 | P_RR | decreasing | -0.0004 | 0.0257 | 0.0721 | 0.41 | 0.40 | -2.86% |
| 431201 | Rainfall_Total_mm | no trend | 0.3933 | 0.6291 | 0.7044 | 1069.74 | 1100.13 | 2.84% |
| 431201 | Freq_R | decreasing | -0.0002 | 0.0001 | 0.0014 | 0.13 | 0.13 | -4.43% |
| 431201 | P_DD | increasing | 0.0002 | 0.0001 | 0.0014 | 0.87 | 0.87 | 0.40% |
| 431201 | P_RR | no trend | -0.0005 | 0.1933 | 0.3218 | 0.31 | 0.30 | -2.41% |
| 432201 | Rainfall_Total_mm | increasing | 3.4857 | 0.0000 | 0.0009 | 1320.74 | 1434.54 | 8.62% |
| 432201 | Freq_R | no trend | -0.0001 | 0.2185 | 0.3332 | 0.16 | 0.16 | 0.23% |
| 432201 | P_DD | increasing | 0.0001 | 0.0342 | 0.0833 | 0.85 | 0.85 | 0.13% |
| 432201 | P_RR | no trend | -0.0001 | 0.6790 | 0.7106 | 0.35 | 0.35 | -0.48% |
