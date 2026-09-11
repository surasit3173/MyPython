# Rainfall Trend Analysis — Research Summary

> **Generated**: 2026-04-10  |  **Study Period**: 1981–2014  |  **Script**: Rainfall Trend Analysis v2.0

---

## 1. Study Area and Data

- **Study area**: Phetchaburi–Prachuap Khiri Khan River Basin, Western Thailand
- **Data**: Daily observed rainfall from 15 meteorological stations
- **Period**: 1981–2014
- **Stations**: S1 (424004), S2 (438002), S3 (465001), S4 (465002), S5 (465003), S6 (465004), S7 (465005), S8 (465006), S9 (465007), S10 (465008), S11 (465009), S12 (465010), S13 (465011), S14 (465012), S15 (465201)
- **Wet-day threshold**: ≥1.0 mm day⁻¹ (WMO standard)

## 2. Methods

### 2.1 Temporal Scales (Hydrological Year)

| Scale | Period | Description |
|-------|--------|-------------|
| Annual | Jan–Dec | Calendar year total |
| Wet Season | May–Oct | Monsoon / wet season (6 months) |
| Dry Season | Nov–Apr | Dry season — hydrological year approach (6 months) |

### 2.2 Statistical Methods

**Standard Mann–Kendall Test** (Mann 1945; Kendall 1975):
- Non-parametric trend test for monotonic trends in time series.
- S statistic with tie correction; Z-statistic from standard normal.
- *Limitation*: Does not account for serial autocorrelation.

**Modified Mann–Kendall Test** (Hamed & Rao 1998):
- Corrects Var(S) using autocorrelation of the ranked series.
- Effective sample size: $n^* = n / [1 + (2/n) \sum_{k=1}^{n-1}(n-k)\rho_k]$
- Adjusted variance: $\text{Var}^*(S) = \text{Var}(S) \times (n/n^*)$
- **Autocorrelation detected**: Yes → Modified MK essential

**Sen's Slope Estimator** (Sen 1968):
- $Q = \text{median}\left[\frac{x_j - x_i}{j - i}\right]$ for all $j > i$
- 95% CI: rank-based method (Gilbert 1987)
- Interpretation: magnitude of change in mm per year

**Significance levels**: α = 0.05 (|Z| > 1.96) and α = 0.01 (|Z| > 2.58)

## 3. Results

### 3.1 Descriptive Statistics

| Station | Code | Mean (mm) | Std (mm) | CV (%) | Wet-days/yr |
|---------|------|-----------|----------|--------|-------------|
| 424004 | S1 | 1130.8 | 271.0 | 24.0 | 122.0 |
| 438002 | S2 | 974.9 | 349.3 | 35.8 | 90.6 |
| 465001 | S3 | 1447.1 | 374.2 | 25.9 | 206.6 |
| 465002 | S4 | 1393.0 | 490.5 | 35.2 | 209.1 |
| 465003 | S5 | 1556.5 | 328.6 | 21.1 | 231.3 |
| 465004 | S6 | 1806.2 | 701.8 | 38.9 | 182.0 |
| 465005 | S7 | 1358.4 | 396.5 | 29.2 | 205.9 |
| 465006 | S8 | 1910.4 | 552.7 | 28.9 | 201.6 |
| 465007 | S9 | 1545.1 | 294.7 | 19.1 | 213.1 |
| 465008 | S10 | 1300.5 | 352.2 | 27.1 | 215.9 |
| 465009 | S11 | 1270.2 | 314.1 | 24.7 | 205.5 |
| 465010 | S12 | 1135.2 | 270.8 | 23.9 | 196.1 |
| 465011 | S13 | 1187.6 | 272.5 | 22.9 | 202.6 |
| 465012 | S14 | 1209.4 | 250.1 | 20.7 | 200.9 |
| 465201 | S15 | 996.6 | 164.2 | 16.5 | 79.7 |

*Regional mean annual rainfall: 1348.1 mm/yr (range: 974.9–1910.4 mm/yr)*

### 3.2 Autocorrelation Results

| Station | Code | r₁ (Annual) | Significant? | → Modified MK? |
|---------|------|-------------|--------------|----------------|
| 424004 | S1 | 0.3810 | Yes *** | Recommended |
| 438002 | S2 | 0.3718 | Yes *** | Recommended |
| 465001 | S3 | 0.8145 | Yes *** | Recommended |
| 465002 | S4 | 0.7338 | Yes *** | Recommended |
| 465003 | S5 | 0.4396 | Yes *** | Recommended |
| 465004 | S6 | 0.7033 | Yes *** | Recommended |
| 465005 | S7 | 0.7256 | Yes *** | Recommended |
| 465006 | S8 | 0.6688 | Yes *** | Recommended |
| 465007 | S9 | -0.0259 | No | Optional |
| 465008 | S10 | 0.6961 | Yes *** | Recommended |
| 465009 | S11 | 0.6723 | Yes *** | Recommended |
| 465010 | S12 | 0.6117 | Yes *** | Recommended |
| 465011 | S13 | 0.6219 | Yes *** | Recommended |
| 465012 | S14 | 0.5587 | Yes *** | Recommended |
| 465201 | S15 | -0.2219 | No | Optional |

### 3.3 Trend Analysis — Annual Scale

| Station | Code | MK Z | MK p | MMK Z | MMK p | β (mm/yr) | Trend | Sig. |
|---------|------|------|------|-------|-------|-----------|-------|------|
| 424004 | S1 | 0.222 | 0.8240 | 0.222 | 0.8240 | +0.40 | No trend | ns |
| 438002 | S2 | -2.431 | 0.0150 | -2.431 | 0.0150 | -12.24 | Decreasing ↓ | * |
| 465001 | S3 | -3.469 | 0.0005 | -1.556 | 0.1197 | -25.20 | No trend | ns |
| 465002 | S4 | -2.164 | 0.0304 | -1.544 | 0.1225 | -22.68 | No trend | ns |
| 465003 | S5 | -1.986 | 0.0470 | -1.443 | 0.1489 | -13.51 | No trend | ns |
| 465004 | S6 | -1.364 | 0.1726 | -0.970 | 0.3321 | -29.87 | No trend | ns |
| 465005 | S7 | -3.024 | 0.0025 | -1.469 | 0.1419 | -21.90 | No trend | ns |
| 465006 | S8 | -2.550 | 0.0108 | -1.251 | 0.2108 | -30.93 | No trend | ns |
| 465007 | S9 | -0.593 | 0.5532 | -0.593 | 0.5532 | -3.38 | No trend | ns |
| 465008 | S10 | -2.550 | 0.0108 | -1.840 | 0.0658 | -20.10 | No trend | ns |
| 465009 | S11 | -2.728 | 0.0064 | -1.700 | 0.0891 | -16.19 | No trend | ns |
| 465010 | S12 | -2.283 | 0.0224 | -1.718 | 0.0858 | -10.40 | No trend | ns |
| 465011 | S13 | -2.609 | 0.0091 | -2.213 | 0.0269 | -11.51 | Decreasing ↓ | * |
| 465012 | S14 | -2.609 | 0.0091 | -1.903 | 0.0570 | -11.76 | No trend | ns |
| 465201 | S15 | -0.445 | 0.6565 | -0.445 | 0.6565 | -2.05 | No trend | ns |

### 3.4 Trend Analysis — Wet Season (May–Oct)

| Station | Code | MK Z | MMK Z | MMK p | β (mm/yr) | Trend | Sig. |
|---------|------|------|-------|-------|-----------|-------|------|
| 424004 | S1 | 0.089 | 0.089 | 0.9291 | +0.33 | No trend | ns |
| 438002 | S2 | -2.417 | -2.417 | 0.0157 | -11.35 | Decreasing ↓ | * |
| 465001 | S3 | -3.736 | -1.663 | 0.0964 | -16.72 | No trend | ns |
| 465002 | S4 | -2.787 | -2.176 | 0.0296 | -13.25 | Decreasing ↓ | * |
| 465003 | S5 | -1.186 | -1.186 | 0.2356 | -3.85 | No trend | ns |
| 465004 | S6 | -2.817 | -1.739 | 0.0820 | -11.43 | No trend | ns |
| 465005 | S7 | -3.188 | -1.535 | 0.1249 | -14.41 | No trend | ns |
| 465006 | S8 | -1.897 | -1.897 | 0.0578 | -4.22 | No trend | ns |
| 465007 | S9 | 0.207 | 0.207 | 0.8356 | +0.54 | No trend | ns |
| 465008 | S10 | -2.994 | -2.994 | 0.0027 | -12.45 | Decreasing ↓ | ** |
| 465009 | S11 | -2.757 | -2.757 | 0.0058 | -8.88 | Decreasing ↓ | ** |
| 465010 | S12 | -2.194 | -2.194 | 0.0282 | -8.09 | Decreasing ↓ | * |
| 465011 | S13 | -2.431 | -2.431 | 0.0150 | -8.50 | Decreasing ↓ | * |
| 465012 | S14 | -2.105 | -2.105 | 0.0353 | -7.63 | Decreasing ↓ | * |
| 465201 | S15 | 0.623 | 0.623 | 0.5335 | +1.66 | No trend | ns |

### 3.5 Trend Analysis — Dry Season (Nov–Apr)

| Station | Code | MK Z | MMK Z | MMK p | β (mm/yr) | Trend | Sig. |
|---------|------|------|-------|-------|-----------|-------|------|
| 424004 | S1 | 0.426 | 0.426 | 0.6701 | +0.33 | No trend | ns |
| 438002 | S2 | -0.298 | -0.298 | 0.7655 | -0.56 | No trend | ns |
| 465001 | S3 | -2.443 | -1.276 | 0.2018 | -9.23 | No trend | ns |
| 465002 | S4 | -1.988 | -1.095 | 0.2734 | -9.76 | No trend | ns |
| 465003 | S5 | -2.244 | -1.224 | 0.2211 | -9.57 | No trend | ns |
| 465004 | S6 | -1.846 | -0.999 | 0.3177 | -20.27 | No trend | ns |
| 465005 | S7 | -2.400 | -1.254 | 0.2097 | -8.04 | No trend | ns |
| 465006 | S8 | -2.244 | -1.210 | 0.2262 | -24.51 | No trend | ns |
| 465007 | S9 | -0.966 | -0.966 | 0.3342 | -3.75 | No trend | ns |
| 465008 | S10 | -2.017 | -1.137 | 0.2557 | -7.38 | No trend | ns |
| 465009 | S11 | -2.457 | -1.340 | 0.1803 | -7.61 | No trend | ns |
| 465010 | S12 | -1.605 | -1.232 | 0.2178 | -2.62 | No trend | ns |
| 465011 | S13 | -2.017 | -1.276 | 0.2021 | -4.11 | No trend | ns |
| 465012 | S14 | -1.789 | -1.359 | 0.1741 | -3.59 | No trend | ns |
| 465201 | S15 | -0.085 | -0.085 | 0.9321 | -0.07 | No trend | ns |

### 3.6 MK vs Modified MK Comparison

| Metric | Value |
|--------|-------|
| Total comparisons (station × scale) | 45 |
| Agreement (same trend conclusion) | 25 (55.6%) |
| Changed by autocorrelation correction | 20 (44.4%) |
| Stations with significant autocorr. (annual) | 13 / 15 |
| Sig. trends (Standard MK, p<0.05) | 29 / 90 |
| Sig. trends (Modified MK, p<0.05) | 9 / 90 |

### 3.7 Key Findings

- **Annual decreasing trend**: S2, S13 show significant decreasing trends (mean β = -11.87 mm/yr, p<0.05).
- **Wet season**: No significant trends detected.
- **Dry season**: No significant trends detected.
- **Autocorrelation effect**: Serial autocorrelation was significant in several stations. Modified MK corrects for this bias; 20 trend conclusions changed after applying the correction.

## 4. Discussion Points

- The Modified Mann–Kendall test (Hamed & Rao 1998) is the recommended approach when serial autocorrelation is present in hydro-climatic time series data.
- Positive serial autocorrelation inflates the Standard MK Z-statistic, leading to false positive trend detection (Type I error inflation).
- Sen's slope provides a physically meaningful estimate of the rate of change, which is essential for water resource planning.
- Wet/dry season separation is hydrologically important: changes in wet season rainfall affect flood risk, while dry season trends affect irrigation demand and reservoir management.
- The 95% CI of Sen's slope should be reported alongside trend significance to convey the uncertainty in the magnitude of change.

## 5. Suggested Paper Language

### Methods Section (Draft)

Long-term trends in daily, annual, and seasonal rainfall were analysed using the Modified Mann–Kendall (MMK) trend test proposed by Hamed and Rao (1998), which accounts for the effect of positive serial autocorrelation commonly found in hydro-climatic time series. The standard Mann–Kendall test (Mann 1945; Kendall 1975) was also applied for comparison. The magnitude of detected trends was quantified using the non-parametric Sen's slope estimator (Sen 1968), together with its 95% confidence interval derived from the rank-based method of Gilbert (1987). All analyses were conducted separately for the annual (1981–2014) and two hydrological seasons: the wet season (May–October) and the dry season (November–April). Significance was assessed at the 5% (α = 0.05) and 1% (α = 0.01) levels.

### Results Section (Template)

Of the 90 station–scale combinations tested, 9 showed statistically significant trends (p < 0.05) according to the Modified MK test. The serial autocorrelation analysis indicated that 13 stations exhibited significant Lag-1 autocorrelation at the annual scale, justifying the use of the Modified MK correction. Agreement between Standard MK and Modified MK was high (25/45 combinations, 55.6%), indicating that autocorrelation had a limited but non-negligible effect on trend conclusions.

## 6. References

- Mann, H. B. (1945). Nonparametric tests against trend. *Econometrica*, 13, 245–259.
- Kendall, M. G. (1975). *Rank Correlation Methods* (4th ed.). Griffin, London.
- Sen, P. K. (1968). Estimates of regression coefficient based on Kendall's tau. *Journal of the American Statistical Association*, 63, 1379–1389.
- Hamed, K. H., & Rao, A. R. (1998). A modified Mann–Kendall trend test for autocorrelated data. *Journal of Hydrology*, 204, 182–196.
- Gilbert, R. O. (1987). *Statistical Methods for Environmental Pollution Monitoring*. Van Nostrand Reinhold, New York.
- Önöz, B., & Bayazit, M. (2003). The power of statistical tests for trend detection. *Hydrological Sciences Journal*, 48, 93–98.
- Yue, S., & Wang, C. (2004). The Mann–Kendall test modified by effective sample size to detect trend in serially correlated hydrological series. *Water Resources Research*, 40, W08307.
- WMO (2008). *Guide to Hydrological Practices* (WMO-No. 168). World Meteorological Organization, Geneva.

---
*End of Research Summary  |  Generated: 2026-04-10  |  Script v2.0*