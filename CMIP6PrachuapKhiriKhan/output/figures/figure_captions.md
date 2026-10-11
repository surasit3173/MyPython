# PUBLICATION FIGURE CAPTIONS (Scopus Q1–Q2 Standard)

**Project 1:** Observed Rainfall Variability and Autocorrelation-Adjusted Trend Detection in Prachuap Khiri Khan Province, Thailand  
**Target Journals:** Atmospheric Research / Theoretical and Applied Climatology  

---

### Figure 1. Geographic Location, Topographic Setting, and Rain Gauge Monitoring Network of Prachuap Khiri Khan Province, Thailand.
**(a) Regional Context:** National boundary of Thailand with the study area outlined in the western Gulf of Thailand coastal corridor, showing neighboring maritime and terrestrial borders (Myanmar, Cambodia, Andaman Sea, Gulf of Thailand).  
**(b) Rain Gauge Network:** Spatial distribution of the 12 long-term ground meteorological stations across Prachuap Khiri Khan Province, showing station IDs and elevation in meters above Mean Sea Level (m MSL). Cartographic base data from Natural Earth (1:10M public domain). Map projection: Geographic WGS84 (EPSG:4326).

---

### Figure 2. Continuous Spatial Rainfall Climatology and Ranked Seasonal Partitioning (1981–2014).
**(a) Spatial Precipitation Surface:** Two-dimensional Inverse Distance Weighting (IDW, power $p = 2.0$, resolution ~500 m) interpolation of 34-year mean annual precipitation (mm/year), strictly clipped to the official provincial boundary. Discrete station symbols represent actual ground gauge locations with observed mean annual rainfall.  
**(b) Ranked Seasonal Composition:** Station-by-station mean annual precipitation partitioned into Wet Season (May–October, blue bars) and Dry Season (November–April, orange bars) contributions, ordered by annual rainfall volume. Vertical dashed line denotes provincial network-wide mean (1129.1 mm).

---

### Figure 3. Long-Term Observed Annual Rainfall Dynamics and Inter-Annual Variability (1981–2014).
**(a) Provincial Network-Average Time Series:** 34-year annual precipitation series averaged across all 12 stations (solid line with circular markers). Shaded ribbon denotes $\pm 1$ spatial standard deviation across stations. Horizontal dotted line denotes the 34-year network grand mean (1129.1 mm). Orange dashed line denotes the non-parametric Sen's slope trend ($+0.05$ mm/year, non-significant). Notable regional drought (1990, 1997, 2004) and pluvial (1988, 1999, 2005) years are annotated.  
**(b) Standardized Anomaly Heatmap Matrix:** Annual precipitation standardized anomalies ($Z = (P - \mu)/\sigma$) across all 12 stations (canonical 6-digit IDs on y-axis) and 34 years (1981–2014 on x-axis). Diverging colormap highlights synchronous regional wet epochs (blue) and prolonged dry episodes (brown).

---

### Figure 4. Comprehensive Comparison of Non-Parametric Trend Detection Frameworks across 12 Gauging Stations (1981–2014).
**(a) Paired Dumbbell Comparison:** Standardized test statistics ($Z$) comparing Standard Mann–Kendall (purple squares) against Yue & Wang (2004) AR(1) MMK (orange circles) and TFPW-MK sensitivity (green triangles). Shaded bands represent critical two-sided significance bounds at $\alpha = 0.05$ ($Z = \pm 1.96$). Station 500002 exhibits statistically significant upward trend ($Z = +2.253, p = 0.0242$); Station 500202 exhibits $|Z|$ inflation from $-1.156$ to $-1.669$ due to negative persistence ($r_1 = -0.3619$).  
**(b) Trend Magnitude:** Sen's slope estimator ($\beta$, mm/year) for each station.  
**(c) Variance Correction Ratio:** Yue & Wang (2004) variance correction factor ($n/n_s^*$), highlighting stations with significant serial correlation (Station 500003: 2.580; Station 500005: 2.293; Station 500202: 0.480) relative to the white-noise baseline ($1.0$).

---

### Figure 5. Empirical Serial Correlation Structure and Mathematical Mechanics of Analytical Yue & Wang (2004) AR(1) Variance Adjustment ($N = 34$).
**(a) Sample Lag-1 Autocorrelation ($r_1$):** Autocorrelation coefficients of Sen-detrended residual series against the 95% two-sided white-noise confidence bounds ($\pm 1.96/\sqrt{34} = \pm 0.3361$). Three stations (500003, 500005, 500202) breach the confidence bounds.  
**(b) Analytical Variance Scaling Curve:** Theoretical variance correction factor ($n/n_s^*$) as a continuous function of $r_1 \in [-0.85, 0.85]$ for sample size $N = 34$, with the 12 observed stations plotted. Station 500202 illustrates variance deflation ($n/n_s^* = 0.4800$) under negative persistence.  
**(c) Variance Scaling:** Base test statistic variance $\text{Var}(S)$ versus adjusted variance $\text{Var}^*(S)$.  
**(d) Test Statistic Shift:** Scatter of Standard MK $Z$ versus Yue–Wang $Z$ relative to the 1:1 identity line.
