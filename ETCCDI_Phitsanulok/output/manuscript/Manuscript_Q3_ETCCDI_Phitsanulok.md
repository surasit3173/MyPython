LONG-TERM TRENDS IN EXTREME PRECIPITATION CHARACTERISTICS AT PHITSANULOK, THAILAND: A 59-YEAR ETCCDI-BASED ANALYSIS WITH AUTOCORRELATION-AWARE TREND DETECTION

Surasit Luangwiset
Department of [Author Affiliation], [University Name], Phitsanulok 65000, Thailand
Correspondence: [author email]; Tel.: +66-[xxx-xxxx]
Submitted: 21 September 2026

================================================================================

Abstract

Long-term changes in extreme precipitation are of critical importance for water
resource management and disaster risk reduction in Southeast Asia. This study
analyses 11 ETCCDI (Expert Team on Climate Change Detection and Indices) extreme
precipitation indices derived from 59 years (1961-2019) of daily precipitation
records at Phitsanulok station (WMO 48378, 16.78 deg N, 100.27 deg E),
northern Thailand. Data quality control confirmed that all 59 calendar years
achieved 100% completeness, yielding 59 annual observations per index
with no missing values.

Indices were computed following standard ETCCDI definitions, with the
95th and 99th percentile thresholds for very wet (R95p) and extremely wet (R99p)
days derived from the 1981-2010 baseline wet-day pool (n = 2622 wet days;
P95 = 49.9 mm; P99 = 82.1 mm). Trend analysis employed the Mann-Kendall test,
preceded by autocorrelation diagnostics at lags 1-10 for all 11 annual series.
No index exhibited statistically significant lag-1 autocorrelation (|r1| < 2/sqrt(59) = 0.260
for all series), and ordinary Mann-Kendall was therefore applied to all indices.
Sen's slope provided trend magnitude estimates with 95% confidence intervals.
Benjamini-Hochberg false discovery rate (FDR) correction was applied to control
the family-wise Type I error rate across 11 simultaneous tests.

Over the 1961-2019 period, mean annual total precipitation from wet days
(PRCPTOT) was 1321.5 +/- 241.9 mm, ranging from 850.2 mm to
1849.6 mm. The Simple Daily Intensity Index (SDII) averaged 14.80 mm/day.
None of the 11 ETCCDI indices showed a statistically significant long-term trend
at the alpha = 0.05 level, either with raw p-values (0 of 11 significant) or
after Benjamini-Hochberg FDR correction (0 of 11 significant). Sen's slopes
were small in magnitude across all indices, confirming the absence of systematic
directional change over the study period.

These findings indicate that extreme precipitation characteristics at Phitsanulok
have remained statistically stable over the past six decades. The lack of
significant trends, coupled with the robustness confirmed by multi-method
sensitivity analysis, provides a baseline characterisation of precipitation
extremes against which future changes and climate projections may be evaluated.
The single-station nature of the analysis and baseline-period dependence of
percentile indices are acknowledged as limitations.

Keywords: extreme precipitation; ETCCDI; Mann-Kendall; Phitsanulok; Thailand;
trend analysis; autocorrelation; Sen's slope; false discovery rate; hydroclimatology

================================================================================

1. Introduction

Extreme precipitation events exert disproportionate impacts on hydrological
systems, agricultural productivity, and human welfare compared with changes in
mean precipitation (Alexander et al., 2006; Klein Tank & Kunnen, 2003). In
Southeast Asia, monsoonal precipitation regimes exhibit substantial inter-annual
variability driven by the El Nino-Southern Oscillation (ENSO), the Indian
Ocean Dipole, and regional land-sea interactions (Villafuerte & Matsumoto, 2015;
Caesar et al., 2011). Understanding whether and how extreme precipitation
characteristics have shifted over multi-decadal timescales is therefore
essential for evidence-based water resource planning and flood risk management.

The Expert Team on Climate Change Detection and Indices (ETCCDI) developed
a standardised set of climate extreme indices that has become the de facto
framework for global and regional trend analyses of precipitation and temperature
extremes (Zhang et al., 2011; Peterson et al., 2001). ETCCDI indices encompass
measures of precipitation amount (PRCPTOT), intensity (SDII, Rx1day, Rx5day),
frequency (R10mm, R20mm, R50mm), spell duration (CDD, CWD), and extreme
thresholds (R95p, R99p), collectively characterising distinct aspects of the
precipitation distribution. Their standardised definitions facilitate
cross-regional comparisons and have been applied across South Asia, Southeast
Asia, and globally (Alexander et al., 2006; Sen Roy & Balling, 2004;
Caesar et al., 2011).

Thailand occupies a climatically complex position, subject to both the south-west
and north-east Asian monsoon systems, with precipitation regimes varying
substantially by region (Singhrattna et al., 2005). Northern and central Thailand,
including Phitsanulok Province, experience a distinct wet season driven by the
south-west monsoon (May-October) and a pronounced dry season. Several studies
have examined precipitation trends across Thailand and the broader Mekong
subregion, with mixed evidence of changing precipitation extremes at regional
scales (Limsakul & Goes, 2008; Villafuerte & Matsumoto, 2015). However,
station-level analyses covering the full climatological record from the early
instrumental era (1960s onwards) remain limited, particularly for inland northern
Thailand.

A methodologically important consideration in detecting precipitation trends is
the treatment of serial correlation in annual time series. Ordinary Mann-Kendall
test statistics assume temporal independence among observations. When significant
autocorrelation is present, the variance of the test statistic is underestimated,
inflating the probability of Type I errors (false detection of trends) (Hamed &
Rao, 1998; Yue & Wang, 2002). The Hamed and Rao (1998) modification and the
Yue-Wang (2002) pre-whitening approach are widely used corrections. Yet,
diagnostic assessment of autocorrelation is often overlooked, or corrections are
applied uniformly without verifying whether serial dependence is actually present
in the data. This study addresses this gap by conducting explicit autocorrelation
diagnostics prior to method selection.

A further statistical concern arises when testing multiple indices simultaneously.
Testing 11 ETCCDI indices at alpha = 0.05 without correction for multiplicity
yields an experiment-wise false positive rate substantially greater than 5%.
The Benjamini-Hochberg (BH) procedure for controlling the false discovery rate
(FDR) is therefore applied here, which is more powerful than Bonferroni correction
for correlated tests while maintaining appropriate error control
(Benjamini & Hochberg, 1995).

The present study has three specific objectives: (i) to compute and characterise
all 11 ETCCDI extreme precipitation indices from 59 years of daily observations
(1961-2019) at Phitsanulok station; (ii) to test for statistically significant
long-term trends using autocorrelation-aware Mann-Kendall methods and Sen's slope
estimator with 95% confidence intervals; and (iii) to assess the robustness of
trend conclusions through sensitivity analysis and FDR correction. The results
provide a statistically rigorous characterisation of extreme precipitation
variability and change at a representative inland station in northern Thailand.

================================================================================

2. Materials and Methods

2.1 Study Area

Phitsanulok Province is located in lower northern Thailand (approximately 16.78 deg N,
100.27 deg E; elevation 45 m above mean sea level). The province lies within the
Nan River basin and is subject to south-west monsoon precipitation from May to
October, followed by a dry season from November to April. The station is operated
by the Thai Meteorological Department (TMD) and registered with the World
Meteorological Organization as WMO station 48378 (TMD station ID: 378201).

2.2 Daily Precipitation Observations

Daily precipitation totals for the period 1 January 1961 to 31 December 2019
were obtained from WMO station 48378. The study period encompasses 59 calendar
years (59 annual observations), including 14 leap years. The complete
daily record comprises 21,549 observations.

2.3 Data Quality Control

A systematic quality-control audit was conducted prior to all computations.
The audit verified: (i) total row count against expected calendar days; (ii)
duplicate dates; (iii) missing calendar dates; (iv) missing and non-numeric
precipitation values; (v) negative precipitation values; (vi) extreme values
exceeding 500 mm/day (flagged as suspect but not removed without additional
evidence); and (vii) per-year completeness relative to expected calendar days.
All 59 years achieved 100% data completeness (0 missing days; 0 missing
precipitation values; 0 negative values; 0 duplicate dates), satisfying the
ETCCDI recommendation of at least 90% annual completeness for index calculation.
Year 2019 was confirmed complete (365 calendar days) and included in all analyses.

2.4 ETCCDI Extreme Precipitation Indices

All 11 ETCCDI precipitation indices were computed following the definitions of
Zhang et al. (2011) and the Expert Team on Climate Change Detection and Indices
(https://www.cccma.ec.gc.ca/data/climdex/). A wet day was defined as a day with
precipitation >= 1.0 mm/day. Annual indices were computed for each calendar year
from 1961 to 2019.

For Rx5day, a rolling 5-day accumulation window was applied, with a minimum of
five non-missing consecutive days required to produce a valid accumulation.
For CDD and CWD, run lengths were not bridged across any missing observations;
as no missing daily values existed in this dataset, this constraint had no
practical effect. The 11 indices are defined in Table 2 of the Results section.

2.5 Percentile Baseline Calculation

The thresholds for R95p and R99p were computed from the wet-day precipitation
distribution during the 1981-2010 reference period (WMO 30-year climatological
normal). Wet days in the baseline period numbered 2622. Percentiles were
computed using linear interpolation (equivalent to the numpy.percentile default
method). The resulting thresholds were: P95 = 49.895 mm and P99 = 82.116 mm.
These thresholds were applied uniformly across all years, including years outside
the baseline. R95p and R99p for each year represent the total annual precipitation
from days with precipitation strictly exceeding P95 and P99, respectively.

2.6 Autocorrelation Diagnostics

Prior to trend inference, the autocorrelation function (ACF) was computed at
lags 1 through 10 for each of the 11 annual ETCCDI series using the biased
autocorrelation estimator. A lag was classified as statistically significant
if |r_k| > 2/sqrt(N), corresponding to the approximate 95% significance bound
under the null hypothesis of white noise (N = 59; threshold = 0.2604).

2.7 Mann-Kendall Trend Test and Method Selection

The Mann-Kendall (MK) test (Mann, 1945; Kendall, 1975) was applied as the
primary non-parametric test for monotonic trend detection in each annual index
series (alpha = 0.05). The Kendall tau statistic provides a normalised measure
of the direction and strength of association between the index values and time.

Method selection was based on the lag-1 autocorrelation diagnostic:
if the lag-1 ACF was statistically significant (|r_1| > 0.2604), the
Hamed and Rao (1998) modified Mann-Kendall test, which adjusts the variance of
the test statistic for the effective sample size under positive autocorrelation,
would be applied. If no significant lag-1 autocorrelation was detected, the
ordinary Mann-Kendall test was used. Method selection was determined solely by
the diagnostic result and was not influenced by test outcome. For all 11 indices,
the lag-1 ACF fell within the 95% significance bounds (all |r_1| < 0.2604),
and ordinary Mann-Kendall was therefore applied throughout.

2.8 Sen's Slope

Trend magnitude was quantified using the Theil-Sen estimator (Sen, 1968),
which is resistant to outliers. Sen's slope beta_S is the median of all pairwise
slopes (x_j - x_i)/(t_j - t_i) for j > i. The 95% confidence interval for
Sen's slope was estimated using the Scipy.stats theilslopes implementation with
alpha = 0.05. Slopes are reported in units per year and per decade.

2.9 Multiple Testing Correction

Raw p-values from 11 simultaneous Mann-Kendall tests were adjusted using the
Benjamini-Hochberg (BH) false discovery rate (FDR) procedure
(Benjamini & Hochberg, 1995). The BH procedure controls the expected proportion
of false positives among rejected hypotheses, and is more powerful than Bonferroni
correction under positive dependence among test statistics. Statistical
significance in all final interpretations is based on FDR-adjusted p-values
at alpha = 0.05.

2.10 Sensitivity Analysis

To assess the robustness of trend conclusions, a three-model sensitivity analysis
was conducted: Model A (ordinary Mann-Kendall), Model B (Hamed-Rao modified MK),
and Model C (Sen's slope direction). A trend was classified as robust when
Models A and B agreed on both direction and significance status.

2.11 Computation and Reproducibility

All computations were implemented in Python (version 3.x) using the following
packages: pandas (data management), numpy (numerical computation),
pymannkendall (Mann-Kendall and Hamed-Rao tests), scipy (Sen's slope, FDR),
and matplotlib (figures). The analysis pipeline is fully reproducible from the
raw CSV input file by executing the main.py script, which produces all outputs
programmatically without any hard-coded results.

================================================================================

3. Results

3.1 Data Quality and Temporal Coverage

The daily precipitation record at WMO station 48378 (Phitsanulok) spans
1 January 1961 to 31 December 2019, comprising 21,549 daily observations across
59 calendar years. The data quality audit confirmed that all 59 years achieved
100% completeness (zero missing dates, zero missing precipitation values, zero
negative values, and zero duplicate dates). Figure 1 illustrates the annual
data completeness, with all bars reaching 100%. This perfect completeness
eliminates data availability as a source of uncertainty in the computed ETCCDI
indices, and the ordinary completeness threshold (>= 90%) was satisfied for every
year without exception. Year 2019 contained 365 calendar days (non-leap year)
and was included in all analyses.

3.2 Characteristics of Extreme Precipitation

Descriptive statistics for all 11 ETCCDI annual indices are summarised in Table 2.
Mean annual total precipitation from wet days (PRCPTOT) over 1961-2019 was
1321.5 +/- 241.9 mm (mean +/- standard deviation), with a minimum of
850.2 mm and a maximum of 1849.6 mm, reflecting considerable inter-annual
variability (coefficient of variation, CV = 18.3%). The Simple Daily
Intensity Index (SDII) averaged 14.80 mm/day, indicating that, when precipitation
occurred, it did so at a moderate intensity. The maximum single-day precipitation
(Rx1day) averaged 94.7 mm, with an observed maximum of 265.7 mm
across the study period.

The mean maximum consecutive dry-day period (CDD) was 57.3 days, consistent
with the pronounced dry season characteristic of the region. Mean maximum consecutive
wet-day periods (CWD) averaged 8.0 days. The annual number of days exceeding
10 mm (R10mm), 20 mm (R20mm), and 50 mm (R50mm) thresholds averaged
40.5, 21.5, and
4.5 days per year, respectively, with R50mm
exhibiting the highest relative variability (CV = 47.2%).
Total precipitation from very wet days (R95p; P95 = 49.9 mm) averaged
322.4 mm per year, while R99p (P99 = 82.1 mm) averaged
99.0 mm per year (Table 2; Figure 6).

3.3 Long-Term Trends in Annual Precipitation Extremes

Trend analysis results for all 11 ETCCDI indices are presented in Table 3 and
visualised in Figures 2, 3, and 4. None of the 11 indices exhibited a
statistically significant long-term trend over the 1961-2019 period at alpha = 0.05,
either based on raw p-values or after Benjamini-Hochberg FDR correction.

For total wet-day precipitation (PRCPTOT), the Mann-Kendall test yielded
tau = -0.070 with a raw p-value of
0.4403 (FDR p = 0.9894),
and the Sen's slope was -1.60 mm/year
(95% CI: -5.44 to 2.65 mm/year).
The SDII showed tau = 0.037
(p_raw = 0.6851; FDR p = 0.9894;
slope = 0.0076 mm/day/year).

Intensity indices Rx1day and Rx5day showed non-significant positive Sen's slopes
of 0.1324 mm/year (p_raw = 0.5828;
FDR p = 0.9894) and
0.0633 mm/year (p_raw = 0.8037;
FDR p = 0.9894), respectively, indicating
no systematic intensification of peak rainfall events.

Consecutive dry days (CDD) showed tau = -0.012
(p_raw = 0.8959; FDR p = 0.9894),
and consecutive wet days (CWD) showed tau = -0.109
(p_raw = 0.2198; FDR p = 0.9894),
neither indicating significant change in dry or wet spell persistence.

Similarly, frequency indices R10mm, R20mm, R50mm, and the percentile-based
indices R95p and R99p all exhibited non-significant trends
(all FDR-adjusted p-values >= 0.05; Table 3). Complete trend statistics
for all indices are provided in Supplementary Table S2.

3.4 Serial Correlation and Robustness of Trend Detection

ACF diagnostics at lags 1-10 for all 11 annual ETCCDI series confirmed that
no index exhibited statistically significant lag-1 autocorrelation
(significance threshold: |r| > 0.2604 for N = 59). The maximum
observed lag-1 ACF magnitude was 0.1813,
well below the 95% confidence bound. Accordingly, ordinary Mann-Kendall
was applied to all 11 indices, as the prerequisite for autocorrelation
correction was not met (Table 4; Figure 5). This diagnostic-driven
method selection ensures that the test remains as powerful as possible
while avoiding unnecessary correction.

The three-model sensitivity analysis (Table S5) demonstrated consistent
conclusions across ordinary MK (Model A), Hamed-Rao modified MK (Model B),
and Sen's slope (Model C): all 11 indices were classified as non-significant
across models, with directions of Sen's slope consistent between models in
all cases. The trend conclusions are therefore robust to methodological choice.

3.5 Synthesis of Observed Changes

The overall synthesis of trend results indicates that extreme precipitation
at Phitsanulok station has not exhibited statistically significant monotonic
change over the 59-year observational record (1961-2019). Both total
precipitation amount and intensity, frequency, and duration characteristics
showed weak and statistically insignificant trends, with Kendall tau values
ranging from -0.109 to 0.050
and all FDR-corrected p-values exceeding 0.05. The absence of significant trends
was confirmed by both raw and FDR-adjusted testing frameworks and was robust
to autocorrelation correction methods.

================================================================================

4. Discussion

4.1 Changes in Total Precipitation and Intensity

The non-significant declining Sen's slope for PRCPTOT
(-1.60 mm/year; FDR p = 0.9894)
and the marginally positive slope for SDII
(0.0076 mm/day/year; FDR p = 0.9894)
indicate that neither total wet-day precipitation nor rainfall intensity has changed
systematically at Phitsanulok over 1961-2019. These findings are broadly consistent
with previous analyses of precipitation trends in northern and central Thailand,
which have reported mixed or non-significant trends at regional scales over
comparable periods (Limsakul & Goes, 2008; Singhrattna et al., 2005). The high
inter-annual variability of PRCPTOT (CV = 18.3%),
driven by ENSO and monsoonal variability, reduces statistical power to detect
monotonic trends over a 59-year record.

4.2 Changes in Rainfall Intensity

The non-significant positive trends in Rx1day
(slope = 0.1324 mm/year) and Rx5day
(slope = 0.0633 mm/year) are consistent
with the broader picture of unchanged extreme rainfall intensity at this station.
The very high inter-annual variability of Rx1day (CV = 37.8%)
and Rx5day (CV = 32.0%) implies that signal-to-noise ratios
are low, making trend detection inherently challenging. Globally, intensification
of short-duration extreme rainfall has been linked to warming temperatures
(Westra et al., 2013), but this thermodynamic signal does not appear to have
emerged above internal variability at this station over the study period.

4.3 Changes in Heavy-Rainfall Frequency

The frequency indices R10mm, R20mm, and R50mm all showed non-significant trends
with small negative Sen's slopes, suggesting no systematic change in the frequency
of moderate-to-heavy rainfall days. The absence of increasing trends in heavy-day
frequency contrasts with results from some tropical Asian regions (Alexander et al.,
2006), potentially reflecting differences in spatial scale, baseline climate state,
or the influence of specific circulation drivers at the local level.

4.4 Changes in Wet and Dry Spells

Both CDD and CWD exhibited non-significant trends (FDR p = 0.9894
and 0.9894, respectively), providing no statistical evidence
for change in dry or wet spell duration over the study period. The mean CDD of
57.3 days reflects the pronounced dry season, while mean CWD of
8.0 days is consistent with the episodic nature of monsoon rainfall in
northern Thailand.

4.5 Changes in Very Wet and Extremely Wet Precipitation

R95p and R99p, representing the contribution of the heaviest precipitation events
to annual totals, also showed no statistically significant trends
(R95p: tau = 0.005, FDR p = 0.9894;
R99p: tau = 0.029, FDR p = 0.9894).
The high CV of R99p (110.2%) reflects the highly intermittent
nature of extremely intense rainfall events, which are subject to large natural
variability. These results suggest that the fraction of total annual precipitation
attributable to the heaviest events has not significantly shifted at Phitsanulok.

4.6 Importance of Autocorrelation-Aware Trend Analysis

The ACF diagnostics confirmed the absence of significant lag-1 autocorrelation in
all 11 annual series, validating the application of ordinary Mann-Kendall without
correction. This result demonstrates the importance of conducting explicit
autocorrelation diagnostics before selecting a trend test method, rather than
applying corrections uniformly. Had Hamed-Rao correction been applied regardless
of diagnostic results, the effective degrees of freedom would have been
unnecessarily reduced, marginally reducing statistical power. The method-selection
rule employed here -- based solely on diagnostic evidence rather than expected
outcome -- exemplifies best practice in non-parametric trend analysis
(Hamed & Rao, 1998; Yue & Wang, 2002).

4.7 Implications for Flood and Water-Resource Management

The absence of statistically significant trends in any of the 11 ETCCDI indices
implies that, over the 1961-2019 period, the probabilistic characteristics of
extreme precipitation at Phitsanulok have not shifted detectably from the
long-term climatological baseline. For water resource planning purposes, this
finding suggests that design flood estimates, reservoir operating rules, and
drainage infrastructure standards based on the historical record remain
statistically defensible within the uncertainty bounds of the trend analysis.
However, stationarity assumptions should be periodically revisited as the
observational record extends and as climate projections for the region are updated.
It is emphasised that the absence of a detected trend does not exclude the
possibility of change at spatial or temporal scales not captured by a single
station record, nor does it constitute evidence against future change.

================================================================================

5. Conclusion

This study presented a comprehensive ETCCDI-based characterisation of extreme
precipitation trends at Phitsanulok (WMO 48378), northern Thailand, using 59 years
of complete daily precipitation records (1961-2019). All 11 ETCCDI extreme
precipitation indices -- encompassing total precipitation, intensity, frequency,
duration, and percentile-based measures -- were computed from a fully verified
dataset with 100% annual completeness.

Autocorrelation diagnostics at lags 1-10 confirmed the absence of significant
lag-1 serial dependence in all annual series, and ordinary Mann-Kendall was
applied throughout. None of the 11 indices demonstrated a statistically significant
monotonic trend over the 59-year record at alpha = 0.05, either with raw p-values
or after Benjamini-Hochberg FDR correction. Sen's slope magnitudes were small for
all indices, and trend conclusions were consistent across all three models in the
sensitivity analysis.

These results provide a statistically rigorous, computationally transparent
baseline characterisation of extreme precipitation variability at this station.
The fully reproducible pipeline -- from raw daily observations through ETCCDI
computation, autocorrelation diagnostics, trend analysis, and FDR correction --
produces all outputs programmatically, supporting replication and extension of
the analysis as the observational record continues to grow.

================================================================================

6. Limitations

Several limitations should be considered when interpreting the results:

(i) Single-station analysis. The results represent conditions at a single gauge.
Spatial gradients in extreme precipitation trends across Phitsanulok Province
cannot be resolved from a single-point record.

(ii) Observational uncertainty. The raw precipitation record may contain
measurement errors not detectable by the quality-control procedures applied here,
including changes in gauge type, observer practices, or station exposure over
the 59-year period.

(iii) Baseline-period dependence of percentile indices. R95p and R99p values
depend on the 1981-2010 baseline period. Alternative baseline periods would yield
different percentile thresholds and consequently different R95p and R99p
magnitudes, though the trend analysis would remain structurally unchanged.

(iv) Statistical trend does not imply causal attribution. The Mann-Kendall and
Sen's slope analyses identify the presence and magnitude of monotonic trends but
do not attribute any observed change to specific drivers (e.g., greenhouse gas
forcing, land-use change, or regional circulation shifts). Attribution analysis
would require additional climate modelling or physical process analysis not
conducted here.

(v) Record length and statistical power. At N = 59 annual observations, the
statistical power to detect weak trends of climatological significance (e.g.,
slopes of a few mm/year against a background variability of several hundred mm)
may be limited.

================================================================================

References

Alexander, L. V., Zhang, X., Peterson, T. C., Caesar, J., Gleason, B., Klein Tank, A.
    M. G., Haylock, M., Collins, D., Trewin, B., Rahimzadeh, F., Tagipour, A.,
    Rupa Kumar, K., Revadekar, J., Griffiths, G., Vincent, L., Stephenson, D. B.,
    Burn, J., Aguilar, E., Brunet, M., Taylor, M., New, M., Zhai, P., Rusticucci, M.,
    & Vazquez-Aguirre, J. L. (2006). Global observed changes in daily climate
    extremes of temperature and precipitation. Journal of Geophysical Research:
    Atmospheres, 111(D5), D05109. https://doi.org/10.1029/2005JD006290

Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate: A
    practical and powerful approach to multiple testing. Journal of the Royal
    Statistical Society: Series B (Methodological), 57(1), 289-300.
    https://doi.org/10.1111/j.2517-6161.1995.tb02031.x

Caesar, J., Alexander, L. V., Trewin, B., Tse-ring, K., Sorany, L., Vuniyayawa, V.,
    Keosavang, N., Shimana, A., Htay, M. M., Karmacharya, J., Jayasingh, D. A., &
    Griffiths, G. M. (2011). Changes in temperature and precipitation extremes over
    the Indo-Pacific region from 1971 to 2005. International Journal of
    Climatology, 31(6), 791-801. https://doi.org/10.1002/joc.2118

Hamed, K. H., & Rao, A. R. (1998). A modified Mann-Kendall trend test for
    autocorrelated data. Journal of Hydrology, 204(1-4), 182-196.
    https://doi.org/10.1016/S0022-1694(97)00125-X

Kendall, M. G. (1975). Rank Correlation Methods (4th ed.). Griffin.

Klein Tank, A. M. G., & Kunnen, G. P. (2003). Trends in indices of daily temperature
    and precipitation extremes in Europe, 1946-99. Journal of Climate, 16(22),
    3665-3680. https://doi.org/10.1175/1520-0442(2003)016<3665:TIIODT>2.0.CO;2

Limsakul, A., & Goes, J. I. (2008). Empirical evidence for interannual and longer
    period variability in Thailand surface air temperatures. Atmospheric Research,
    87(2), 89-102. https://doi.org/10.1016/j.atmosres.2007.07.007

Mann, H. B. (1945). Nonparametric tests against trend. Econometrica, 13(3), 245-259.
    https://doi.org/10.2307/1907187

Peterson, T. C., Folland, C., Gruza, G., Hogg, W., Mokssit, A., & Plummer, N.
    (2001). Report on the Activities of the Working Group on Climate Change
    Detection and Related Rapporteurs (WMO/TD-No. 1071). World Meteorological
    Organization, Geneva.

Sen, P. K. (1968). Estimates of the regression coefficient based on Kendall's tau.
    Journal of the American Statistical Association, 63(324), 1379-1389.
    https://doi.org/10.1080/01621459.1968.10480934

Sen Roy, S., & Balling, R. C. (2004). Trends in extreme daily precipitation indices
    in India. International Journal of Climatology, 24(4), 457-466.
    https://doi.org/10.1002/joc.995

Singhrattna, N., Rajagopalan, B., Clark, M., & Kumar, K. K. (2005). Seasonal
    forecasting of Thailand summer monsoon rainfall. International Journal of
    Climatology, 25(5), 649-664. https://doi.org/10.1002/joc.1144

Villafuerte, M. Q., II, & Matsumoto, J. (2015). Significant influences of global mean
    temperature and ENSO on extreme rainfall in Southeast Asia. Journal of Climate,
    28(5), 1905-1919. https://doi.org/10.1175/JCLI-D-14-00531.1

Westra, S., Alexander, L. V., & Zwiers, F. W. (2013). Global increasing trends in
    annual maximum daily precipitation. Journal of Climate, 26(11), 3904-3918.
    https://doi.org/10.1175/JCLI-D-12-00502.1

Yue, S., & Wang, C. Y. (2002). Applicability of pre-whitening to eliminate the
    influence of serial correlation on the Mann-Kendall test. Water Resources
    Research, 38(6), 4-1 to 4-7. https://doi.org/10.1029/2001WR000861

Zhang, X., Alexander, L., Hegerl, G. C., Jones, P., Klein Tank, A., Peterson, T. C.,
    Trewin, B., & Zwiers, F. W. (2011). Indices for monitoring changes in extremes
    based on daily temperature and precipitation data. Wiley Interdisciplinary
    Reviews: Climate Change, 2(6), 851-870. https://doi.org/10.1002/wcc.147