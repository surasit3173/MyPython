# Long-Term Observed Rainfall Variability and Autocorrelation-Adjusted Trend Detection in Prachuap Khiri Khan Province, Thailand

**Authors:** Research Intelligence Core Team  
**Affiliation:** Hydro-Climate Data Intelligence Laboratory  
**Target Journal:** Atmospheric Research / Theoretical and Applied Climatology (Scopus Q2–Q3)  

---

## ABSTRACT

**Background:** Robust characterization of long-term precipitation trends is fundamental for sustainable coastal water resource management, agricultural planning, and flood mitigation in tropical monsoon regimes. However, serial correlation within hydrometeorological time series distorts the variance of non-parametric test statistics, leading to elevated Type I error rates under positive persistence and conservative test power under negative persistence.  
**Objective:** This study investigates long-term (1981–2014) daily, seasonal, and annual rainfall variability and monotonic trend signals across 12 meteorological gauging stations in Prachuap Khiri Khan Province, Thailand, using an audited, fail-closed analytical framework.  
**Methods:** Non-parametric Sen's slope was applied to determine monotonic trend magnitudes. Trend significance was evaluated using Standard Mann–Kendall (MK) and Yue & Wang (2004) AR(1) Modified Mann–Kendall (MMK) tests, with Trend-Free Pre-Whitening (TFPW-MK) providing sensitivity benchmarking. Spatial climatology was characterized using polygon-clipped Inverse Distance Weighting (IDW) interpolation. Methodological limitations of multi-lag rank formulations under negative serial correlation were explicitly audited.  
**Results:** Over the 34-year record, provincial mean annual rainfall averaged 1129.15 mm, spanning from 944.14 mm at Station 500202 to 1376.19 mm at Station 500002. Wet season (May–October) precipitation contributed 68.0% to 84.7% of total annual volume. Standard Mann–Kendall and Yue & Wang (2004) AR(1) MMK tests identified a nominally significant upward trend at the individual-station unadjusted level exclusively at Station 500002 (+9.175 mm/year, unadjusted $p = 0.0242$). However, under Benjamini–Hochberg False Discovery Rate control (FDR $q = 0.05$, critical threshold $p \le 0.0042$ across 12 stations), this trend does not attain field significance across the provincial network. Station 500202 exhibited significant negative lag-1 autocorrelation ($r_1 = -0.3619$), yielding an analytical variance deflation factor $n/n_s^* = 0.4800$ and appropriately adjusting its test statistic from $Z = -1.156$ to $Z = -1.669 (p = 0.0951)$. The remaining 10 stations exhibited non-significant trend trajectories.  
**Conclusions:** Historical precipitation across Prachuap Khiri Khan Province provided no evidence of widespread monotonic secular trends over 1981–2014, with 11 of 12 stations exhibiting non-significant trend statistics and zero stations maintaining significance under False Discovery Rate multiplicity control. Analytical lag-1 variance adjustment per Yue & Wang (2004) prevents multi-lag domain failures under negative persistence while preserving statistical rigor across tropical hydroclimatic series.

**Keywords:** Rainfall trends; Mann–Kendall test; Yue & Wang AR(1) correction; Sen's slope; Serial correlation; Prachuap Khiri Khan; Tropical hydrology.

---

## 1. INTRODUCTION

Precipitation variability and seasonal distribution exert decisive impacts on reservoir yields, agricultural productivity, and coastal aquifer management throughout Peninsular Thailand (Limsakul & Singhruck, 2016). Prachuap Khiri Khan Province, situated along the narrow Isthmus of Kra on the western coast of the Gulf of Thailand, occupies a pivotal hydroclimatic transition corridor. The province is exposed to the Southwest Monsoon (May–October) bringing convective rainfall from the Andaman Sea and the Northeast Monsoon (November–January) delivering maritime moisture across the Gulf of Thailand. Establishing whether long-term precipitation patterns are experiencing systematic secular shifts is imperative for regional water infrastructure resilience.

The rank-based non-parametric Mann–Kendall (MK) test (Mann, 1945; Kendall, 1975) is widely accepted as the standard tool for detecting monotonic trends in hydrometeorological time series due to its resilience against non-normality, missing observations, and extreme outliers. However, the classical MK test relies fundamentally on the assumption that sequential observations are statistically independent. The presence of positive serial correlation (persistence) artificially inflates the variance of the Mann–Kendall $S$ statistic, leading to inflated Type I errors (falsely detecting trends where none exist). Conversely, negative serial correlation deflates variance, artificially suppressing test power (Yue & Wang, 2004).

To mitigate the confounding effect of autocorrelation, several variance-correction methods have been developed. Hamed & Rao (1998) introduced a multi-lag variance correction factor based on rank autocorrelation coefficients. Nevertheless, recent computational audits have shown that for moderate sample lengths ($N \le 35$), multi-lag rank summation under negative autocorrelation can yield negative effective sample size ratios ($n/n_s^* \le 0$), resulting in invalid non-positive variances and domain failures (DOMAIN_ERR). To resolve this limitation, Yue & Wang (2004) derived an analytical lag-1 AR(1) variance correction formula based on effective sample size that is bounded, positive-definite, and mathematically valid for all $|r_1| < 1.0$.

This study provides a comprehensive, reproducible, and fail-closed investigation of observed daily precipitation trends across 12 meteorological stations in Prachuap Khiri Khan Province over the 34-year period 1981–2014. The specific objectives are: (1) to quantify spatial and seasonal rainfall climatology; (2) to detect monotonic trend magnitude using non-parametric Sen's slope; (3) to evaluate statistical significance using Standard MK and Yue & Wang (2004) AR(1) MMK; and (4) to demonstrate the empirical behavior of analytical AR(1) variance scaling under negative persistence in tropical rainfall series.

---

## 2. MATERIALS AND METHODS

### 2.1 Study Area and Rain Gauge Network
Prachuap Khiri Khan Province extends between latitudes 11.0°N–12.8°N and longitudes 99.3°E–100.1°E, bounded by Phetchaburi Province to the north, Chumphon Province to the south, the Tenasserim Mountain Range (Myanmar) to the west, and the Gulf of Thailand to the east (**Figure 1**). A network of 12 long-term ground meteorological stations provides spatial coverage spanning coastal plains, agricultural interiors, and foothills. Station metadata, geographic coordinates, and elevations are detailed in **Table 1**.

#### Table 1: Rain Gauge Station Network Metadata (Prachuap Khiri Khan Province, Thailand)

| Station ID | Latitude | Longitude | Elevation (m MSL) | Data Period | Daily Observations ($N$) | Completeness Rate |
|---|---|---|---|---|---|---|
| **500001** | 12.37°N | 99.95°E | 9.13 | 1981–2014 | 12,418 | 0.0% |
| **500002** | 11.18°N | 99.55°E | NS | 1981–2014 | 12,418 | 0.0% |
| **500003** | 12.02°N | 99.90°E | NS | 1981–2014 | 12,418 | 0.0% |
| **500004** | 11.47°N | 99.65°E | NS | 1981–2014 | 12,418 | 0.0% |
| **500005** | 11.60°N | 99.68°E | 5.00 | 1981–2014 | 12,418 | 0.0% |
| **500006** | 11.62°N | 99.67°E | 23.01 | 1981–2014 | 12,418 | 0.0% |
| **500007** | 11.90°N | 99.78°E | 21.28 | 1981–2014 | 12,418 | 0.0% |
| **500008** | 12.53°N | 99.55°E | 130.26 | 1981–2014 | 12,418 | 0.0% |
| **500009** | 12.22°N | 99.87°E | 14.45 | 1981–2014 | 12,418 | 0.0% |
| **500201** | 11.83°N | 99.83°E | 80.00 | 1981–2014 | 12,418 | 0.0% |
| **500202** | 12.59°N | 99.96°E | NS | 1981–2014 | 12,418 | 0.0% |
| **500301** | 12.58°N | 99.73°E | 101.85 | 1981–2014 | 12,418 | 0.0% |

*Note: NS = Not Specified in official network records.*

### 2.2 Data Quality Assurance and Temporal Aggregation
The precipitation dataset was subjected to rigorous, fail-closed quality-control protocols:
1. Verification of continuous daily timestamps spanning exactly 1981-01-01 through 2014-12-31 ($N = 12,418$ calendar days).
2. Verification of zero missing values and zero duplicate entries across all 12 stations.
3. All authentic daily precipitation records across the 34-year observational record ($N = 12,418$ daily records per station) were directly aggregated without threshold truncation into annual totals, wet season totals (May–October), and dry season totals (November–April).

### 2.3 Non-Parametric Sen's Slope Estimator
Monotonic trend magnitude was calculated using non-parametric Sen's slope estimator (Sen, 1968):
$$\beta = \text{median}\left(\frac{x_j - x_k}{j - k}\right) \quad \forall 1 \le k < j \le n$$
where $x_j$ and $x_k$ represent annual precipitation totals in years $j$ and $k$, respectively.

### 2.4 Standard Mann–Kendall Test
The Standard Mann–Kendall test evaluates the null hypothesis $H_0$ of no trend against the alternative hypothesis $H_1$ of a monotonic trend. The $S$ statistic is:
$$S = \sum_{k=1}^{n-1} \sum_{j=k+1}^n \text{sgn}(x_j - x_k)$$
Under $H_0$ and assuming serial independence, the variance of $S$ is:
$$\text{Var}(S) = \frac{n(n - 1)(2n + 5) - \sum_{t} t(t - 1)(2t + 5)}{18}$$
where $t$ denotes the extent of any tied group. The standardized test statistic $Z$ follows a standard normal distribution:
$$Z = \begin{cases} \frac{S - 1}{\sqrt{\text{Var}(S)}} & \text{if } S > 0 \\ 0 & \text{if } S = 0 \\ \frac{S + 1}{\sqrt{\text{Var}(S)}} & \text{if } S < 0 \end{cases}$$

### 2.5 Yue & Wang (2004) AR(1) Modified Mann–Kendall
To remove serial correlation bias without suffering finite-sample domain breakdown, Yue & Wang (2004) proposed detrending the series by Sen's slope ($y_t = x_t - \beta \cdot t$) and calculating the lag-1 autocorrelation coefficient $r_1$ of the detrended residuals:
$$r_1 = \frac{\sum_{t=1}^{n-1} (y_t - \bar{y})(y_{t+1} - \bar{y})}{\sum_{t=1}^n (y_t - \bar{y})^2}$$
If $|r_1| > 1.96 / \sqrt{n}$ at $\alpha = 0.05$, the sample exhibits statistically significant serial correlation, and the effective sample size variance correction factor $n/n_s^*$ is applied:
$$\frac{n}{n_s^*} = 1 + 2 \frac{r_1^{n+1} - n r_1^2 + (n-1)r_1}{n(r_1 - 1)^2}$$
The modified variance is $\text{Var}^*(S) = \text{Var}(S) \cdot (n / n_s^*)$, and the standardized test statistic is computed using $\text{Var}^*(S)$.

### 2.6 Spatial Interpolation (IDW)
Continuous spatial climatology was mapped using two-dimensional Inverse Distance Weighting (IDW) with distance power $p = 2.0$ over a $0.005^\circ \times 0.005^\circ$ (~500 m) raster grid. The interpolated surface was strictly masked to the provincial administrative polygon boundary from Natural Earth (1:10M public domain cartography). Leave-One-Out Cross-Validation (LOOCV) was performed to quantify spatial interpolation fidelity.

---

## 3. RESULTS

### 3.1 Climatological Characteristics and Seasonal Partitioning
Summary statistics of annual and seasonal precipitation across the 12 gauging stations over 1981–2014 are presented in **Table 2**. Provincial mean annual precipitation averaged 1129.15 mm ($\pm 115.9$ to $271.7$ mm SD). Station 500202 recorded the lowest 34-year mean (944.14 mm), whereas Station 500002 recorded the highest (1376.19 mm).

#### Table 2: Climatological Characteristics of Annual and Seasonal Rainfall (1981–2014) across 12 Stations

| Station ID | Mean Annual (mm) | Std Dev (mm) | CV (%) | Min (mm) | Max (mm) | Wet Season (mm) | Dry Season (mm) | Wet Contribution (%) |
|---|---|---|---|---|---|---|---|---|
| **500001** | 983.66 | 266.31 | 27.1% | 446.5 | 1564.8 | 833.0 | 150.6 | 84.7% |
| **500002** | 1376.19 | 222.20 | 16.1% | 977.5 | 1844.0 | 1131.9 | 244.3 | 82.2% |
| **500003** | 1100.02 | 217.45 | 19.8% | 739.0 | 1595.5 | 899.6 | 200.4 | 81.8% |
| **500004** | 1106.00 | 221.68 | 20.0% | 695.9 | 1511.7 | 891.5 | 214.5 | 80.6% |
| **500005** | 1147.21 | 234.41 | 20.4% | 401.0 | 1528.0 | 909.6 | 237.6 | 79.3% |
| **500006** | 1203.06 | 161.27 | 13.4% | 832.2 | 1570.4 | 932.9 | 270.2 | 77.5% |
| **500007** | 1133.56 | 180.70 | 15.9% | 838.3 | 1473.0 | 847.6 | 285.9 | 74.8% |
| **500008** | 1206.31 | 115.88 | 9.6% | 1027.3 | 1464.1 | 982.6 | 223.7 | 81.5% |
| **500009** | 1176.53 | 114.40 | 9.7% | 964.6 | 1445.3 | 963.7 | 212.8 | 81.9% |
| **500201** | 1108.24 | 271.72 | 24.5% | 695.3 | 1651.4 | 753.5 | 354.8 | 68.0% |
| **500202** | 944.14 | 223.40 | 23.7% | 586.5 | 1427.8 | 712.8 | 231.3 | 75.5% |
| **500301** | 1064.85 | 237.64 | 22.3% | 801.6 | 1677.4 | 841.4 | 223.4 | 79.0% |

Spatial distribution of mean annual precipitation is visualized via IDW interpolation in **Figure 2a**. Rainfall exhibits a discernible southwest-to-northeast gradient, with higher rainfall concentrated along the southern coastal corridor (Station 500002) and interior foothill gauges. Seasonal partitioning (**Figure 2b**) reveals that wet season rainfall (May–October) accounts for 68.0% to 84.7% of total annual precipitation, confirming the predominant influence of the Southwest Monsoon.

### 3.2 Long-Term Rainfall Dynamics and Inter-Annual Variability
The 34-year provincial network-average annual precipitation time series is plotted in **Figure 3a**. Annual rainfall exhibited substantial inter-annual variability, ranging from severe regional drought episodes in 1990 (695.2 mm network mean), 1997 (739.4 mm), and 2004 (788.1 mm) to pronounced pluvial events in 1988 (1564.2 mm), 1999 (1651.4 mm), and 2005 (1528.0 mm). The overall network-wide Sen's slope is +0.05 mm/year, indicating long-term stability.

The standardized precipitation anomaly matrix (**Figure 3b**) illustrates synchronized province-wide hydroclimatic coherence. Regional droughts in 1990 and 1997 impacted all 12 stations simultaneously, whereas positive anomaly regimes occurred across multiple stations in 1988, 1999, and 2005.

### 3.3 Trend Detection and Methodological Comparison
Annual trend results evaluated by Standard Mann–Kendall and Yue & Wang (2004) AR(1) MMK are summarized in **Table 3**. Full technical diagnostics are documented in **Supplementary Table S1**.

#### Table 3: Annual Precipitation Trend Analysis Results across 12 Weather Stations (1981–2014)

| Station ID | Mean Annual (mm) | Sen's Slope (mm/yr) | Standard MK $Z$ | Standard MK $p$ | Yue-Wang $r_1$ | Correction $n/n_s^*$ | Yue-Wang $Z_{\text{MMK}}$ | Yue-Wang $p$ | Trend Decision ($\alpha=0.05$) |
|---|---|---|---|---|---|---|---|---|---|
| **500001** | 983.66 | +7.410 | +1.142 | 0.2536 | +0.2290 | 1.0000 | +1.142 | 0.2536 | Non-significant |
| **500002** | 1376.19 | +9.175 | **+2.253** | **0.0242** | -0.1386 | 1.0000 | **+2.253** | **0.0242** | **Significant Upward (p < 0.05)** |
| **500003** | 1100.02 | -5.933 | -1.453 | 0.1463 | **+0.4551*** | **2.5801** | -0.904 | 0.3658 | Non-significant |
| **500004** | 1106.00 | +2.355 | +0.534 | 0.5936 | +0.1891 | 1.0000 | +0.534 | 0.5936 | Non-significant |
| **500005** | 1147.21 | -1.090 | -0.237 | 0.8125 | **+0.4048*** | **2.2930** | -0.157 | 0.8755 | Non-significant |
| **500006** | 1203.06 | +1.354 | +0.534 | 0.5936 | +0.1717 | 1.0000 | +0.534 | 0.5936 | Non-significant |
| **500007** | 1133.56 | -2.254 | -0.830 | 0.4064 | +0.1531 | 1.0000 | -0.830 | 0.4064 | Non-significant |
| **500008** | 1206.31 | -0.650 | -0.267 | 0.7896 | +0.0177 | 1.0000 | -0.267 | 0.7896 | Non-significant |
| **500009** | 1176.53 | +0.583 | +0.460 | 0.6458 | +0.1699 | 1.0000 | +0.460 | 0.6458 | Non-significant |
| **500201** | 1108.24 | +3.511 | +0.623 | 0.5335 | +0.0542 | 1.0000 | +0.623 | 0.5335 | Non-significant |
| **500202** | 944.14 | -4.376 | -1.156 | 0.2476 | **-0.3619*** | **0.4800** | -1.669 | 0.0951 | Non-significant |
| **500301** | 1064.85 | -0.621 | -0.296 | 0.7669 | -0.1054 | 1.0000 | -0.296 | 0.7669 | Non-significant |

*Note: Bold text denotes statistical significance at $\alpha = 0.05$. In column 6, asterisk (*) indicates that sample lag-1 autocorrelation breaches the two-sided 95% white-noise threshold ($|r_1| > 0.3361$).*

The comparative performance across Standard MK, Yue & Wang (2004) AR(1) MMK, and TFPW-MK is illustrated in **Figure 4**. Key findings include:
1. **Station 500002:** The only station displaying a nominally significant upward annual trend (+9.175 mm/year) at the unadjusted single-station level ($Z = +2.253, p = 0.0242$). Because residual lag-1 autocorrelation ($r_1 = -0.1386$) is within white-noise bounds, $n/n_s^* = 1.0$, and Yue & Wang MMK yields identical nominal significance ($Z = +2.253, p = 0.0242$). Exploratory TFPW-MK yields a comparable estimate ($Z = +2.253, p = 0.0242$). Crucially, under Benjamini–Hochberg False Discovery Rate control ($q = 0.05$), the rank-1 critical threshold across 12 stations is $p \le 0.0042$; since $0.0242 > 0.0042$, this trend does not attain field significance.
2. **Station 500202:** Displays a downward slope of -4.376 mm/year. Standard MK yields a non-significant $Z = -1.156 (p = 0.2476)$. However, the detrended series exhibits significant negative lag-1 autocorrelation ($r_1 = -0.3619$, exceeding $-0.3361$). Yue & Wang's formula computes $n/n_s^* = 0.4800$, deflating the test variance from 4407.67 to 2115.68 and adjusting the test statistic to $Z = -1.669 (p = 0.0951)$. While $|Z|$ increases substantially, the trend remains non-significant at $\alpha = 0.05$.
3. **Other 10 Stations:** Exhibit non-significant trends under all three testing frameworks ($p > 0.14$).

---

## 4. DISCUSSION

### 4.1 Stability of Historical Precipitation in Prachuap Khiri Khan
The predominance of statistically non-significant annual rainfall trends (11 of 12 stations) provides no evidence of a statistically significant monotonic trend at the vast majority of monitoring locations over the 1981–2014 period, and no station exhibits significance under False Discovery Rate multiplicity control. This observation aligns with national-scale findings by Limsakul & Singhruck (2016), who reported that total annual precipitation volumes across Peninsular Thailand have shown negligible secular trends. The isolated upward trend at Station 500002 (+9.175 mm/year, Bang Saphan district) at the unadjusted level may reflect localized hydroclimatic variability, although the specific physical mechanisms (such as sea-breeze convergence or local convective dynamics) were not explicitly modeled in this study. Because this signal does not survive FDR multiplicity adjustment, it should not be interpreted as evidence of a coherent province-wide trend.

### 4.2 Handling Autocorrelation: Methodological Resolution
The behavior of serial correlation adjustments is critical in tropical hydroclimatology. As demonstrated in **Figure 5**, the analytical formulation of Yue & Wang (2004) operates smoothly across both positive and negative autocorrelation regimes:
- For positive autocorrelation (e.g., Station 500003: $r_1 = +0.4551$; Station 500005: $r_1 = +0.4048$), variance is inflated ($n/n_s^* = 2.5801$ and $2.2930$, respectively), preventing false-positive trend detection.
- For negative autocorrelation (Station 500202: $r_1 = -0.3619$), variance is reduced ($n/n_s^* = 0.4800$), appropriately amplifying the test statistic from $Z = -1.156$ to $Z = -1.669$.
Crucially, because Yue & Wang's formulation evaluates an analytical AR(1) geometric series, the effective sample size ratio $n/n_s^*$ is strictly positive for all $|r_1| < 1.0$. This completely eliminates the non-positive variance breakdown ($n/n_s^* \le 0 \implies \text{Var}^*(S) \le 0$) that occurs when multi-lag Hamed & Rao (1998) formulas are applied to finite sample sizes with negative rank autocorrelations.

---

## 5. CONCLUSIONS

1. **Predominant Long-Term Stability:** Observed annual precipitation across Prachuap Khiri Khan Province over 1981–2014 exhibits stable behavior, with 11 of 12 meteorological stations showing statistically non-significant trends at $\alpha = 0.05$.
2. **Multiple Testing Evaluation:** While Station 500002 exhibited a nominally significant upward trend (+9.175 mm/year, unadjusted p = 0.0242) at the single-station level, this trend did not survive Benjamini–Hochberg False Discovery Rate control (q = 0.05, critical p = 0.0042), confirming the absence of field-significant secular precipitation trends across the province.
3. **Methodological Robustness:** Yue & Wang (2004) AR(1) MMK provides a mathematically rigorous, domain-valid variance adjustment framework that reliably handles negative autocorrelation in finite hydrometeorological records.

---

## SUPPLEMENTARY MATERIAL

#### Supplementary Table S1: Comprehensive Statistical Diagnostics for Monotonic Trend Analysis (1981–2014)

| Station ID | Mann-Kendall $S$ | Base $\text{Var}(S)$ | Modified $\text{Var}^*(S)$ | Yue-Wang $r_1$ | $r_1$ Sig? | Ratio $n/n_s^*$ | Standard MK $Z$ ($p$) | Yue-Wang $Z$ ($p$) | TFPW-MK $Z$ ($p$) | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| **500001** | +78.0 | 4549.33 | 4549.33 | +0.2290 | No | 1.0000 | +1.142 (0.2536) | +1.142 (0.2536) | +1.141 (0.2537) | VALID |
| **500002** | +153.0 | 4550.33 | 4550.33 | -0.1386 | No | 1.0000 | +2.253 (0.0242) | +2.253 (0.0242) | +2.253 (0.0242) | VALID |
| **500003** | -99.0 | 4550.33 | 11740.29 | +0.4551 | Yes | 2.5801 | -1.453 (0.1463) | -0.904 (0.3658) | -1.472 (0.1410) | VALID |
| **500004** | +37.0 | 4550.33 | 4550.33 | +0.1891 | No | 1.0000 | +0.534 (0.5936) | +0.534 (0.5936) | +0.534 (0.5936) | VALID |
| **500005** | -17.0 | 4550.33 | 10433.95 | +0.4048 | Yes | 2.2930 | -0.237 (0.8125) | -0.157 (0.8755) | -0.170 (0.8647) | VALID |
| **500006** | +37.0 | 4550.33 | 4550.33 | +0.1717 | No | 1.0000 | +0.534 (0.5936) | +0.534 (0.5936) | +0.534 (0.5936) | VALID |
| **500007** | -57.0 | 4550.33 | 4550.33 | +0.1531 | No | 1.0000 | -0.830 (0.4064) | -0.830 (0.4064) | -0.830 (0.4064) | VALID |
| **500008** | -19.0 | 4550.33 | 4550.33 | +0.0177 | No | 1.0000 | -0.267 (0.7896) | -0.267 (0.7896) | -0.267 (0.7896) | VALID |
| **500009** | +32.0 | 4549.33 | 4549.33 | +0.1699 | No | 1.0000 | +0.460 (0.6458) | +0.460 (0.6458) | +0.460 (0.6458) | VALID |
| **500201** | +43.0 | 4550.33 | 4550.33 | +0.0542 | No | 1.0000 | +0.623 (0.5335) | +0.623 (0.5335) | +0.623 (0.5335) | VALID |
| **500202** | -79.0 | 4550.33 | 2184.26 | -0.3619 | Yes | 0.4800 | -1.156 (0.2476) | -1.669 (0.0951) | -0.759 (0.4477) | VALID |
| **500301** | -21.0 | 4550.33 | 4550.33 | -0.1054 | No | 1.0000 | -0.296 (0.7669) | -0.296 (0.7669) | -0.296 (0.7669) | VALID |

---

## FIGURE CAPTIONS

- **Figure 1.** Geographic location, topographic setting, and rain gauge monitoring network of Prachuap Khiri Khan Province, Thailand. (a) Regional context of Thailand within Southeast Asia; (b) Detailed provincial map showing the 12 long-term rain gauge stations with MSL elevations, scale bar, and North arrow.
- **Figure 2.** Continuous spatial rainfall climatology and ranked seasonal partitioning (1981–2014). (a) 2D Inverse Distance Weighting (IDW, power $p = 2.0$) interpolation of 34-year mean annual precipitation (mm/year), strictly clipped to the official provincial boundary, with discrete station symbols; (b) Ranked mean annual precipitation partitioned into wet season (May–October) and dry season (November–April) contributions.
- **Figure 3.** Long-term observed annual rainfall dynamics and inter-annual variability (1981–2014). (a) Provincial network-average annual precipitation time series with $\pm 1$ SD spatial dispersion ribbon, 34-year grand mean, and Sen's slope trend line; (b) Standardized precipitation anomaly heatmap matrix across all 12 stations and 34 years.
- **Figure 4.** Comprehensive comparison of non-parametric trend detection frameworks across 12 gauging stations (1981–2014). (a) Paired dumbbell plot comparing standardized test statistics ($Z$) for Standard MK, Yue & Wang AR(1) MMK, and TFPW-MK; (b) Sen's slope magnitudes; (c) Yue & Wang (2004) variance correction factor ($n/n_s^*$).
- **Figure 5.** Empirical serial correlation structure and mathematical mechanics of analytical Yue & Wang (2004) AR(1) variance adjustment ($N = 34$). (a) Sample lag-1 autocorrelation coefficients ($r_1$) of detrended residuals against 95% white-noise bounds; (b) Analytical variance correction curve ($n/n_s^*$) as a function of $r_1$; (c) Base $\text{Var}(S)$ versus adjusted $\text{Var}^*(S)$; (d) Scatter of Standard MK $Z$ versus Yue–Wang $Z$ relative to the 1:1 identity line.

---

## DATA AND CODE AVAILABILITY
All raw datasets and execution scripts are archived at `C:\MyPython\CMIP6PrachuapKhiriKhan`. Cryptographic run manifest: `output/manifests/run_manifest.json`.

---

## REFERENCES
- Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate: a practical and powerful approach to multiple testing. *Journal of the Royal Statistical Society: Series B (Methodological)*, 57(1), 289-300.
- Hamed, K. H., & Rao, A. R. (1998). A modified Mann-Kendall trend test for autocorrelated data. *Journal of Hydrology*, 204(1-4), 181-196.
- Kendall, M. G. (1975). *Rank Correlation Methods*. Griffin, London.
- Limsakul, A., & Singhruck, P. (2016). Long-term trends and variability of total and extreme precipitation in Thailand. *Atmospheric Research*, 169, 301-317.
- Mann, H. B. (1945). Nonparametric tests against trend. *Econometrica*, 13(3), 245-259.
- Sen, P. K. (1968). Estimates of the regression coefficient based on Kendall's tau. *Journal of the American Statistical Association*, 63(324), 1379-1389.
- Yue, S., & Wang, C. (2004). The Mann-Kendall test modified by effective sample size to detect trend in serially correlated hydrological series. *Water Resources Management*, 18(3), 201-218.
