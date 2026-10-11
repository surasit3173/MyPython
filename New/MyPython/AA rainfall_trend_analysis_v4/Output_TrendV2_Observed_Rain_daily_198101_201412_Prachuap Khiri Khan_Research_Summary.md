# Rainfall Trend Analysis — Research Summary

> **Generated**: 2026-04-28  |  **Study Period**: 1981–2014  |  **Script**: Rainfall Trend Analysis v3.0

---

## 1. Study Area and Data

- **Study area**: Phetchaburi–Prachuap Khiri Khan River Basin, Western Thailand
- **Data**: Daily observed rainfall from 12 meteorological stations
- **Period**: 1981–2014
- **Stations**: S1 (500001), S2 (500002), S3 (500003), S4 (500004), S5 (500005), S6 (500006), S7 (500007), S8 (500008), S9 (500009), S10 (500201), S11 (500202), S12 (500301)
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
| 500001 | S1 | 983.7 | 266.3 | 27.1 | 81.2 |
| 500002 | S2 | 1376.2 | 222.2 | 16.1 | 123.2 |
| 500003 | S3 | 1100.0 | 217.4 | 19.8 | 83.7 |
| 500004 | S4 | 1106.0 | 221.7 | 20.0 | 96.2 |
| 500005 | S5 | 1147.2 | 234.4 | 20.4 | 175.2 |
| 500006 | S6 | 1203.1 | 161.3 | 13.4 | 181.8 |
| 500007 | S7 | 1133.6 | 180.7 | 15.9 | 177.7 |
| 500008 | S8 | 1206.3 | 115.9 | 9.6 | 228.8 |
| 500009 | S9 | 1176.5 | 114.4 | 9.7 | 219.7 |
| 500201 | S10 | 1108.2 | 271.7 | 24.5 | 90.2 |
| 500202 | S11 | 944.1 | 223.4 | 23.7 | 78.6 |
| 500301 | S12 | 1064.8 | 237.6 | 22.3 | 92.5 |

*Regional mean annual rainfall: 1129.1 mm/yr (range: 944.1–1376.2 mm/yr)*

### 3.2 Autocorrelation Results

| Station | Code | r₁ (Annual) | Significant? | → Modified MK? |
|---------|------|-------------|--------------|----------------|
| 500001 | S1 | 0.2599 | No | Optional |
| 500002 | S2 | 0.0259 | No | Optional |
| 500003 | S3 | 0.4739 | Yes *** | Recommended |
| 500004 | S4 | 0.2103 | No | Optional |
| 500005 | S5 | 0.4130 | Yes *** | Recommended |
| 500006 | S6 | 0.1820 | No | Optional |
| 500007 | S7 | 0.1527 | No | Optional |
| 500008 | S8 | 0.0141 | No | Optional |
| 500009 | S9 | 0.1814 | No | Optional |
| 500201 | S10 | 0.0642 | No | Optional |
| 500202 | S11 | -0.3525 | Yes *** | Recommended |
| 500301 | S12 | -0.1062 | No | Optional |

### 3.3 Trend Analysis — Annual Scale

| Station | Code | MK Z | MK p | MMK Z | MMK p | β (mm/yr) | Trend | Sig. |
|---------|------|------|------|-------|-------|-----------|-------|------|
| 500001 | S1 | 1.142 | 0.2536 | 1.142 | 0.2536 | +7.41 | No trend | ns |
| 500002 | S2 | 2.253 | 0.0242 | 2.253 | 0.0242 | +9.18 | Increasing ↑ | * |
| 500003 | S3 | -1.453 | 0.1463 | -1.260 | 0.2075 | -5.93 | No trend | ns |
| 500004 | S4 | 0.534 | 0.5936 | 0.534 | 0.5936 | +2.35 | No trend | ns |
| 500005 | S5 | -0.237 | 0.8125 | -0.237 | 0.8125 | -1.09 | No trend | ns |
| 500006 | S6 | 0.534 | 0.5936 | 0.534 | 0.5936 | +1.35 | No trend | ns |
| 500007 | S7 | -0.830 | 0.4064 | -0.830 | 0.4064 | -2.25 | No trend | ns |
| 500008 | S8 | -0.267 | 0.7896 | -0.267 | 0.7896 | -0.65 | No trend | ns |
| 500009 | S9 | 0.460 | 0.6458 | 0.460 | 0.6458 | +0.58 | No trend | ns |
| 500201 | S10 | 0.623 | 0.5335 | 0.623 | 0.5335 | +3.51 | No trend | ns |
| 500202 | S11 | -1.156 | 0.2476 | -1.156 | 0.2476 | -4.38 | No trend | ns |
| 500301 | S12 | -0.296 | 0.7669 | -0.296 | 0.7669 | -0.62 | No trend | ns |

### 3.4 Trend Analysis — Wet Season (May–Oct)

| Station | Code | MK Z | MMK Z | MMK p | β (mm/yr) | Trend | Sig. |
|---------|------|------|-------|-------|-----------|-------|------|
| 500001 | S1 | 0.504 | 0.504 | 0.6142 | +2.90 | No trend | ns |
| 500002 | S2 | 0.296 | 0.296 | 0.7669 | +0.93 | No trend | ns |
| 500003 | S3 | -1.868 | -1.131 | 0.2578 | -7.77 | No trend | ns |
| 500004 | S4 | -0.919 | -0.919 | 0.3580 | -3.09 | No trend | ns |
| 500005 | S5 | -2.105 | -1.625 | 0.1041 | -6.48 | No trend | ns |
| 500006 | S6 | -2.164 | -1.657 | 0.0976 | -6.54 | No trend | ns |
| 500007 | S7 | -1.631 | -1.631 | 0.1030 | -4.41 | No trend | ns |
| 500008 | S8 | -0.207 | -0.207 | 0.8356 | -0.39 | No trend | ns |
| 500009 | S9 | -0.237 | -0.237 | 0.8125 | -0.54 | No trend | ns |
| 500201 | S10 | 0.889 | 0.889 | 0.3738 | +3.06 | No trend | ns |
| 500202 | S11 | -0.356 | -0.356 | 0.7220 | -1.22 | No trend | ns |
| 500301 | S12 | 0.207 | 0.207 | 0.8356 | +0.73 | No trend | ns |

### 3.5 Trend Analysis — Dry Season (Nov–Apr)

| Station | Code | MK Z | MMK Z | MMK p | β (mm/yr) | Trend | Sig. |
|---------|------|------|-------|-------|-----------|-------|------|
| 500001 | S1 | 2.130 | 2.130 | 0.0332 | +2.75 | Increasing ↑ | * |
| 500002 | S2 | 3.039 | 3.039 | 0.0024 | +5.56 | Increasing ↑ | ** |
| 500003 | S3 | 0.199 | 0.199 | 0.8424 | +0.43 | No trend | ns |
| 500004 | S4 | 2.329 | 2.329 | 0.0199 | +4.72 | Increasing ↑ | * |
| 500005 | S5 | 1.392 | 1.392 | 0.1640 | +3.10 | No trend | ns |
| 500006 | S6 | 3.352 | 2.516 | 0.0119 | +6.57 | Increasing ↑ | * |
| 500007 | S7 | 0.852 | 0.852 | 0.3942 | +2.08 | No trend | ns |
| 500008 | S8 | 0.085 | 0.085 | 0.9321 | +0.21 | No trend | ns |
| 500009 | S9 | 0.852 | 0.852 | 0.3942 | +1.39 | No trend | ns |
| 500201 | S10 | 0.597 | 0.597 | 0.5509 | +1.55 | No trend | ns |
| 500202 | S11 | -0.625 | -0.625 | 0.5321 | -0.51 | No trend | ns |
| 500301 | S12 | -0.739 | -0.739 | 0.4602 | -1.13 | No trend | ns |

### 3.6 MK vs Modified MK Comparison

| Metric | Value |
|--------|-------|
| Total comparisons (station × scale) | 36 |
| Agreement (same trend conclusion) | 34 (94.4%) |
| Changed by autocorrelation correction | 2 (5.6%) |
| Stations with significant autocorr. (annual) | 3 / 12 |
| Sig. trends (Standard MK, p<0.05) | 7 / 72 |
| Sig. trends (Modified MK, p<0.05) | 5 / 72 |

### 3.7 Key Findings

- **Annual increasing trend**: S2 show significant increasing trends (mean β = +9.18 mm/yr, p<0.05).
- **Wet season**: No significant trends detected.
- **Dry season**: No significant trends detected.
- **Autocorrelation effect**: Serial autocorrelation was significant in several stations. Modified MK corrects for this bias; 2 trend conclusions changed after applying the correction.

## 4. Methodological Implication: MK vs MMK & Autocorrelation Effect

> **Key message**: Positive serial autocorrelation (ρ₁ > 0) inflates the Standard MK Z-statistic, increasing the risk of **false positive** trend detection (Type I error). The Modified MK (Hamed & Rao 1998) corrects the variance of S using effective sample size n*, producing a more conservative and statistically valid test.

### 4.1 Why MK and MMK Can Disagree

The Standard Mann–Kendall test assumes that observations are serially independent. When this assumption is violated — as is common in annual and seasonal hydro-climatic series (Önöz & Bayazit 2003) — the variance Var(S) is underestimated. This has two practical consequences:

1. **Inflated Z-statistic**: |Z(MK)| > |Z(MMK)| when ρ₁ > 0
2. **False positive trend detection**: A series may appear significant under    Standard MK but not under Modified MK (or vice versa for ρ₁ < 0).

The Hamed & Rao (1998) correction replaces Var(S) with Var*(S):

$$\text{Var}^*(S) = \text{Var}(S) \times \frac{n}{n^*}$$

where $n^* = n \Big/ \left[1 + \frac{2}{n} \sum_{k=1}^{n-1}(n-k)\,\rho_k(\text{ranks})\right]$

Only autocorrelation lags that are statistically significant are included in the correction (i.e., $|\rho_k| > z_{0.025}/\sqrt{n}$).

### 4.2 Autocorrelation Effect — Per-Station Summary (Annual Scale)

| Station | Code | ρ₁ | Sig. ρ₁? | n | n_eff | Z (MK) | Z (MMK) | ΔZ | Conclusion |
|---------|------|----|----------|---|-------|--------|---------|-----|-----------|
| 500001 | S1 | 0.260 | No | 34 | 34.0 | 1.142 | 1.142 | 0.000 | Consistent |
| 500002 | S2 | 0.026 | No | 34 | 34.0 | 2.253 | 2.253 | 0.000 | Consistent |
| 500003 | S3 | 0.474 | **Yes*** | 34 | 25.6 | -1.453 | -1.260 | 0.192 | AC corrected |
| 500004 | S4 | 0.210 | No | 34 | 34.0 | 0.534 | 0.534 | 0.000 | Consistent |
| 500005 | S5 | 0.413 | **Yes*** | 34 | 34.0 | -0.237 | -0.237 | 0.000 | AC corrected |
| 500006 | S6 | 0.182 | No | 34 | 34.0 | 0.534 | 0.534 | 0.000 | Consistent |
| 500007 | S7 | 0.153 | No | 34 | 34.0 | -0.830 | -0.830 | 0.000 | Consistent |
| 500008 | S8 | 0.014 | No | 34 | 34.0 | -0.267 | -0.267 | 0.000 | Consistent |
| 500009 | S9 | 0.181 | No | 34 | 34.0 | 0.460 | 0.460 | 0.000 | Consistent |
| 500201 | S10 | 0.064 | No | 34 | 34.0 | 0.623 | 0.623 | 0.000 | Consistent |
| 500202 | S11 | -0.352 | **Yes*** | 34 | 34.0 | -1.156 | -1.156 | 0.000 | AC corrected |
| 500301 | S12 | -0.106 | No | 34 | 34.0 | -0.296 | -0.296 | 0.000 | Consistent |

> **Summary**: 3/12 stations had significant Lag-1 autocorrelation at the annual scale. Trend conclusions changed in 0 case(s) after applying the Modified MK correction (ΔZ = Z(MMK) − Z(MK); negative ΔZ = Standard MK over-estimated significance).

### 4.3 Sen's Slope + 95% CI — All Stations (Comprehensive Table)

> All values from **Modified MK** (Hamed & Rao 1998).  β = Sen's slope (mm yr⁻¹ or mm season⁻¹).  95% CI = Gilbert (1987) rank-based confidence interval.  \* p<0.05  \*\* p<0.01  ns = not significant.

#### Annual Scale

| Station | Code | β (mm/yr) | 95% CI Lower | 95% CI Upper | CI Width | Z (MMK) | p-value | Sig. |
|---------|------|-----------|-------------|-------------|----------|---------|---------|------|
| 500001 | S1 | 7.410 | -3.390 | 16.767 | 20.157 | 1.142 | 0.2536 | ns |
| 500002 | S2 | 9.175 | 1.000 | 16.150 | 15.150 | 2.253 | 0.0242 | * |
| 500003 | S3 | -5.933 | -13.290 | 3.515 | 16.805 | -1.260 | 0.2075 | ns |
| 500004 | S4 | 2.355 | -3.862 | 11.967 | 15.829 | 0.534 | 0.5936 | ns |
| 500005 | S5 | -1.090 | -10.762 | 6.522 | 17.284 | -0.237 | 0.8125 | ns |
| 500006 | S6 | 1.354 | -5.271 | 7.240 | 12.511 | 0.534 | 0.5936 | ns |
| 500007 | S7 | -2.254 | -8.735 | 4.067 | 12.802 | -0.830 | 0.4064 | ns |
| 500008 | S8 | -0.650 | -5.600 | 3.362 | 8.962 | -0.267 | 0.7896 | ns |
| 500009 | S9 | 0.583 | -3.729 | 5.300 | 9.029 | 0.460 | 0.6458 | ns |
| 500201 | S10 | 3.511 | -7.312 | 13.956 | 21.268 | 0.623 | 0.5335 | ns |
| 500202 | S11 | -4.376 | -13.311 | 4.050 | 17.361 | -1.156 | 0.2476 | ns |
| 500301 | S12 | -0.621 | -7.062 | 5.773 | 12.835 | -0.296 | 0.7669 | ns |

#### Wet Season (May–Oct)

| Station | Code | β (mm/season) | 95% CI Lower | 95% CI Upper | CI Width | Z (MMK) | p-value | Sig. |
|---------|------|---------------|-------------|-------------|----------|---------|---------|------|
| 500001 | S1 | 2.900 | -8.236 | 12.950 | 21.186 | 0.504 | 0.6142 | ns |
| 500002 | S2 | 0.929 | -5.700 | 7.718 | 13.418 | 0.296 | 0.7669 | ns |
| 500003 | S3 | -7.772 | -15.239 | 0.600 | 15.839 | -1.131 | 0.2578 | ns |
| 500004 | S4 | -3.089 | -10.711 | 3.520 | 14.231 | -0.919 | 0.3580 | ns |
| 500005 | S5 | -6.478 | -12.863 | -0.275 | 12.588 | -1.625 | 0.1041 | ns |
| 500006 | S6 | -6.544 | -12.000 | -1.157 | 10.843 | -1.657 | 0.0976 | ns |
| 500007 | S7 | -4.405 | -9.650 | 0.681 | 10.331 | -1.631 | 0.1030 | ns |
| 500008 | S8 | -0.388 | -4.609 | 2.896 | 7.505 | -0.207 | 0.8356 | ns |
| 500009 | S9 | -0.543 | -4.163 | 3.065 | 7.228 | -0.237 | 0.8125 | ns |
| 500201 | S10 | 3.061 | -4.220 | 9.464 | 13.684 | 0.889 | 0.3738 | ns |
| 500202 | S11 | -1.220 | -6.444 | 6.917 | 13.361 | -0.356 | 0.7220 | ns |
| 500301 | S12 | 0.735 | -6.400 | 6.375 | 12.775 | 0.207 | 0.8356 | ns |

#### Dry Season (Nov–Apr)

| Station | Code | β (mm/season) | 95% CI Lower | 95% CI Upper | CI Width | Z (MMK) | p-value | Sig. |
|---------|------|---------------|-------------|-------------|----------|---------|---------|------|
| 500001 | S1 | 2.750 | 0.272 | 5.471 | 5.199 | 2.130 | 0.0332 | * |
| 500002 | S2 | 5.564 | 2.267 | 9.713 | 7.446 | 3.039 | 0.0024 | ** |
| 500003 | S3 | 0.430 | -2.840 | 3.779 | 6.619 | 0.199 | 0.8424 | ns |
| 500004 | S4 | 4.717 | 0.895 | 8.420 | 7.525 | 2.329 | 0.0199 | * |
| 500005 | S5 | 3.096 | -1.353 | 7.435 | 8.788 | 1.392 | 0.1640 | ns |
| 500006 | S6 | 6.570 | 3.008 | 9.642 | 6.634 | 2.516 | 0.0119 | * |
| 500007 | S7 | 2.078 | -1.803 | 6.825 | 8.628 | 0.852 | 0.3942 | ns |
| 500008 | S8 | 0.214 | -2.420 | 3.059 | 5.479 | 0.085 | 0.9321 | ns |
| 500009 | S9 | 1.394 | -0.892 | 4.333 | 5.225 | 0.852 | 0.3942 | ns |
| 500201 | S10 | 1.552 | -4.276 | 8.444 | 12.720 | 0.597 | 0.5509 | ns |
| 500202 | S11 | -0.509 | -5.423 | 3.667 | 9.090 | -0.625 | 0.5321 | ns |
| 500301 | S12 | -1.131 | -5.130 | 2.826 | 7.956 | -0.739 | 0.4602 | ns |

> **Annual β summary**: Mean = +0.79 mm, Range [-5.93, +9.18] mm, n_sig = 1 / 12

> **Wet β summary**: Mean = -1.90 mm, Range [-7.77, +3.06] mm, n_sig = 0 / 12

> **Dry β summary**: Mean = +2.23 mm, Range [-1.13, +6.57] mm, n_sig = 4 / 12

### 4.4 When to Use Standard MK vs Modified MK

| Condition | Recommended Test | Reason |
|-----------|-----------------|--------|
| No significant ρ₁ (|r₁| ≤ 1.96/√n) | Either MK or MMK | Results will be nearly identical |
| Significant positive ρ₁ | **Modified MK (H&R98)** | Positive AC inflates Z(MK) → Type I error ↑ |
| Significant negative ρ₁ | **Modified MK (H&R98)** | Negative AC deflates Z(MK) → Type II error ↑ |
| Short series (n < 15) | Use with caution | Both tests have low power for short n |
| Reporting for publication | **Always report both** | Allows comparison and transparency |

**Practical recommendation** (Önöz & Bayazit 2003; Yue & Wang 2004):
> Always test for serial autocorrelation first. If |ρ₁| is significant, the Modified MK (Hamed & Rao 1998) is the correct test to use. Reporting both MK and MMK Z-statistics demonstrates analytical transparency and allows the reader to assess the magnitude of the autocorrelation effect.

### 4.5 Interpretation of Sen's Slope 95% CI

The 95% confidence interval for Sen's slope (Gilbert 1987) should be interpreted as follows:

- **CI entirely positive** (lo > 0): Evidence of an increasing trend   regardless of the magnitude assumed within the interval.
- **CI entirely negative** (hi < 0): Evidence of a decreasing trend.
- **CI crosses zero** (lo < 0 < hi): Trend direction is uncertain;   the slope may be zero. Statistical significance should be interpreted   with the p-value rather than the CI alone.
- **Narrow CI**: High precision in the slope estimate (beneficial for   water resource planning).
- **Wide CI**: High uncertainty — typically seen when series are short   (n ≈ MIN_N) or exhibit high inter-annual variability.

**Note**: A significant MK/MMK p-value with a CI crossing zero is theoretically inconsistent. In practice this arises from differences in how the test statistic (S) and the slope CI use Var(S). The p-value is the primary measure of statistical significance; the CI provides the physically meaningful range of the change rate.

## 5. Discussion Points

- The Modified Mann–Kendall test (Hamed & Rao 1998) is the recommended approach when serial autocorrelation is present in hydro-climatic time series data.
- Positive serial autocorrelation inflates the Standard MK Z-statistic, leading to false positive trend detection (Type I error inflation).
- Sen's slope provides a physically meaningful estimate of the rate of change, which is essential for water resource planning.
- Wet/dry season separation is hydrologically important: changes in wet season rainfall affect flood risk, while dry season trends affect irrigation demand and reservoir management.
- The 95% CI of Sen's slope should be reported alongside trend significance to convey the uncertainty in the magnitude of change.

## 6. Suggested Paper Language

### Methods Section (Draft)

Long-term trends in daily, annual, and seasonal rainfall were analysed using the Modified Mann–Kendall (MMK) trend test proposed by Hamed and Rao (1998), which accounts for the effect of positive serial autocorrelation commonly found in hydro-climatic time series. The standard Mann–Kendall test (Mann 1945; Kendall 1975) was also applied for comparison. The magnitude of detected trends was quantified using the non-parametric Sen's slope estimator (Sen 1968), together with its 95% confidence interval derived from the rank-based method of Gilbert (1987). All analyses were conducted separately for the annual (1981–2014) and two hydrological seasons: the wet season (May–October) and the dry season (November–April). Significance was assessed at the 5% (α = 0.05) and 1% (α = 0.01) levels.

### Results Section (Template)

Of the 72 station–scale combinations tested, 5 showed statistically significant trends (p < 0.05) according to the Modified MK test. The serial autocorrelation analysis indicated that 3 stations exhibited significant Lag-1 autocorrelation at the annual scale, justifying the use of the Modified MK correction. Agreement between Standard MK and Modified MK was high (34/36 combinations, 94.4%), indicating that autocorrelation had a limited but non-negligible effect on trend conclusions.

## 7. References

- Mann, H. B. (1945). Nonparametric tests against trend. *Econometrica*, 13, 245–259.
- Kendall, M. G. (1975). *Rank Correlation Methods* (4th ed.). Griffin, London.
- Sen, P. K. (1968). Estimates of regression coefficient based on Kendall's tau. *Journal of the American Statistical Association*, 63, 1379–1389.
- Hamed, K. H., & Rao, A. R. (1998). A modified Mann–Kendall trend test for autocorrelated data. *Journal of Hydrology*, 204, 182–196.
- Gilbert, R. O. (1987). *Statistical Methods for Environmental Pollution Monitoring*. Van Nostrand Reinhold, New York.
- Önöz, B., & Bayazit, M. (2003). The power of statistical tests for trend detection. *Hydrological Sciences Journal*, 48, 93–98.
- Yue, S., & Wang, C. (2004). The Mann–Kendall test modified by effective sample size to detect trend in serially correlated hydrological series. *Water Resources Research*, 40, W08307.
- WMO (2008). *Guide to Hydrological Practices* (WMO-No. 168). World Meteorological Organization, Geneva.

---
*End of Research Summary  |  Generated: 2026-04-28  |  Script v3.0*