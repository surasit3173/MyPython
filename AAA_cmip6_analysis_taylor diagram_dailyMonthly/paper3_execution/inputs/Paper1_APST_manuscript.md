# Near-Future Changes in Daily Precipitation and Selected Rainfall Extremes over Uttaradit, Thailand Using Bias-Corrected Global Climate Models

*Formatted for Asia-Pacific Journal of Science and Technology (APST). Times New Roman 10 pt, single column, double spacing, A4, 1-inch margins, continuous line numbering. References in Vancouver style, cited by numerals in square brackets.*

---

Surasit Punyawansiri<sup>1,\*</sup>

<sup>1</sup>Office of Water Management and Hydrology, Royal Irrigation Department, Dusit, Bangkok 10300, Thailand

<sup>\*</sup>Corresponding author: Surasit.ku@ku.th

Received … ; Revised … ; Accepted …

---

## Abstract

Bias-corrected climate model output underpins regional impact assessment, yet skill is often reported only for the fitting period, and projected changes are frequently referenced to observations rather than to the model's own baseline. Quantile delta mapping was evaluated under a split-sample design and used to quantify near-future precipitation change over Uttaradit Province, northern Thailand. Daily precipitation from seven CMIP6 models under two scenarios was corrected at 13 rain gauges with parameters fitted on 1981–2002 and frozen, evaluated on the independent period 2003–2014, and applied to 2021–2050 against each model's own corrected baseline for 1995–2014. Over the calibration period the mean absolute bias fell from 71.1% to 0.03% for wet-day frequency, from 40.8% to 1.2% for annual total and from 48.2% to 0.02% for the 95th wet-day percentile. Out of sample these became 28.6%, 15.8% and 33.7%, well below the raw models but not negligible; excluding four gauges flagged by a homogeneity screening reduced the mean residual from 26.4% to 13.4%. Indices governed by day ordering were not corrected: the bias in maximum consecutive dry days was 49.8% after correction against 48.4% before it. For 2021–2050 the ensemble median change in annual precipitation is near zero under both scenarios, while heavy-rainfall indices generally increase under SSP2-4.5 but show weaker or mixed changes under SSP5-8.5. Inter-model agreement reaches 0.80 for only two index types, one of which is a diagnostic quantity rather than a validated corrected projection.

**Keywords:** Daily rainfall, Hydroclimatic projection, Model evaluation, Northern Thailand, Quantile adjustment, Rainfall variability

---

## 1. Introduction

Assessments of flood, drought and agricultural risk in monsoon Asia depend on daily precipitation from global climate models (GCMs), which cannot be used directly for local impact modelling: coarse resolution produces excessive low-intensity rainfall and a misrepresented intensity distribution [1,2]. Statistical bias correction is therefore routine, and quantile mapping is the most widely applied family of methods [1,3].

Thailand faces substantial exposure to hydroclimatic hazard, with 86 severe flood events reported between 1970 and 2021 affecting more than 61 million people [4]. Observed rainfall extremes have intensified [5,6] and compound hot-rainfall extremes have increased across most of the station network [7]. Regional CMIP6 assessments show a consistent tension between weak mean-rainfall signals and stronger extreme signals: over northeast Thailand no significant change in annual rainfall was projected for 2021–2050 even though 20-year return values of Rx1day and Rx5day rose by more than 30% [8], and southern Thailand shows a comparable pattern [9].

Three weaknesses recur in the applied literature and motivate this study.

First, validation is frequently in-sample. Because quantile mapping is calibrated against the observed marginal distribution, very high in-sample agreement is expected and provides limited evidence of out-of-sample transferability. A split-sample design, in which parameters are frozen before they encounter the evaluation period, is the minimum required to support a claim about skill [1,10].

Second, the reference for the projected change is often the observed record. When the future is taken from corrected model output while the baseline is taken from observations, any residual correction error is added directly to the reported climate-change signal. The change must be referenced to the same model's own corrected historical simulation [1].

Third, success on the intensity distribution is generalised to "extremes" as a class. Quantile mapping assigns a new magnitude to each rank; it does not reorder days. Indices defined on runs of days, such as maximum consecutive dry days (CDD) and maximum consecutive wet days (CWD), and on multi-day accumulations such as Rx5day, therefore inherit the model's own temporal structure however well the marginal distribution is matched [11]. This distinction is rarely tested explicitly.

Uttaradit Province in northern Thailand offers a demanding test case: a monsoon-dominated regime with a pronounced dry season, a 13-gauge network spanning a lowland-to-mountain gradient, and a record long enough for a split-sample design yet short enough that station heterogeneity matters. Three questions are addressed:

**RQ1.** How effectively does quantile delta mapping reduce biases in daily precipitation during calibration and during independent validation? **RQ2.** Which characteristics of precipitation are improved, and which remain limited because they depend on temporal structure? **RQ3.** What near-future changes for 2021–2050 are supported by the bias-corrected ensemble? The organising principle is that a projection's reliability depends on which component of rainfall variability the correction actually corrects.

---

## 2. Materials and methods

### 2.1 Study area and rain-gauge data

Uttaradit Province lies in northern Thailand between 17.16° and 18.37° N and 99.90° and 101.17° E (Figure 1), with elevation from about 50 m in the southern lowlands to above 700 m along the north-eastern ridge. The provincial boundary was taken from the Natural Earth 10 m Admin-1 dataset (ISO 3166-2 code TH-53) [12] and verified for geometry validity, coordinate reference system (EPSG:4326), polygon complexity (378 vertices, hence not a bounding rectangle) and containment of all 13 gauges; its geodesic area is 7,610.7 km², 2.9% below the commonly cited figure, consistent with cartographic generalisation. Daily rainfall for 1981–2014 was obtained for 13 gauges, with mean annual wet-day totals over 1981–2002 of 954 to 1,326 mm; identifiers, coordinates and per-gauge climatology are listed in Supplementary Table S1.

### 2.2 Quality control of the observed record

Rainfall archives commonly encode missing days as zero, which no check based on null values detects. Every station-month whose total was exactly zero was screened against six diagnostics: the median monthly total at the remaining gauges; the fraction of those gauges exceeding 5 mm; the station's own climatological median for that calendar month; the length of the zero run containing the month; and the annual total relative to the station's own and to the network median. A zero was reclassified as missing only when the surrounding network contradicted it, requiring at least one neighbour-based diagnostic to fire, because within-station diagnostics alone cannot distinguish a regional drought from a data gap, and at least two diagnostics in total.

Of 5,304 station-months, 315 were confirmed dry, all in December–February, 43 probable missing and 80 uncertain and left unaltered for sensitivity analysis. The 43 flagged months correspond to 1,308 daily values, 0.810% of the record, set to missing; no value was imputed. For example, August 2008 at gauge 351006 recorded 0.0 mm while all twelve neighbours recorded 11.6–108.7 mm.

A homogeneity screening used the ratio of wet-day frequency in the validation period to that in the calibration period. Four gauges fall outside the interval 0.75–1.33 and are flagged for potential inhomogeneity: 351003 (2.37), 351005 (1.51), 351006 (0.54) and 351007 (0.58). This ratio is a screening diagnostic, not a formal homogenisation test such as the penalised maximal *t* test [13]; station history metadata were unavailable, so no gauge is described here as homogeneous or inhomogeneous in the technical sense. The four flagged gauges are retained in the primary analysis as a diagnostic subset.

### 2.3 CMIP6 data and model configuration

Daily precipitation was used from seven CMIP6 models [14,15] for the historical experiment (1981–2014) and for SSP2-4.5 and SSP5-8.5 (2015–2100). Their configuration is summarised in Table 1 [16–22]. Calendars were detected from the data and are compatible between the historical and scenario segments of every model. No model has an overlapping or missing day at the 2014/2015 junction, and implied annual totals of 228–1,342 mm are consistent with millimetres per day. Raw model wet-day frequency ranges from 12.7% to 64.0% against an observed network mean of 36.8%, confirming both the drizzle problem and its opposite in individual models.

The last column of Table 1 counts how many *distinct* daily series the 13 analysed gauges receive from each model, that is how many native grid cells effectively serve the province. The count ranges from one (CanESM5, in which every gauge receives an identical series) to five (EC-Earth3). Sub-provincial detail in the raw model fields therefore reflects grid resolution rather than resolved atmospheric structure, and spatial results are presented accordingly (Section 3.5).

### 2.4 Quantile delta mapping

Quantile delta mapping (QDM) [1] was applied separately for each gauge and each model, with wet days defined by a 1.0 mm d⁻¹ threshold throughout. Frequency adaptation was applied before any intensity mapping: the model wet-day threshold was raised until the model wet-day frequency over the calibration period matched the observed frequency [10], determined separately for each gauge–model pair. This reduces the wet-day-frequency bias while retaining the intensity values of days classified as wet. For a target-period value *x* with non-exceedance probability *p* in the target-period model distribution, the corrected value is

  BC(*x*) = *F*⁻¹<sub>obs,cal</sub>(*p*) × [ *x* / *F*⁻¹<sub>mod,cal</sub>(*p*) ]   (1)

where *F*⁻¹<sub>obs,cal</sub> and *F*⁻¹<sub>mod,cal</sub> are the observed and modelled quantile functions over the calibration period. Empirical distributions used Hazen plotting positions with linear interpolation. Beyond the calibration range the multiplicative correction ratio at the nearest calibration quantile was held constant and no value was clipped, so a new record extreme remains one; extrapolation affected 0.41% of wet days on average.

### 2.5 Rainfall indices and performance measure

Indices were calculated following the definitions of the Expert Team on Climate Change Detection and Indices [23] where applicable, supplemented by wet-day frequency and empirical wet-day quantiles: PRCPTOT, wet-day frequency, SDII, Rx1day, Rx5day, R10mm, R20mm, R50mm, R95p, R99p, CDD, CWD and the wet-day quantiles *q*<sub>50</sub>, *q*<sub>90</sub>, *q*<sub>95</sub> and *q*<sub>99</sub>. Percentile thresholds for R95p and R99p came from observed wet days over the calibration period at each gauge. All indices were computed identically for observations, raw and corrected output, and series were reindexed to a complete daily calendar before any window or spell operation so that no-leap model years are not silently compressed.

Performance is reported throughout as the **mean absolute bias**, defined for index *k* as

  MAB(*k*) = (1 / *NM*) Σ<sub>*i*=1</sub><sup>*N*</sup> Σ<sub>*j*=1</sub><sup>*M*</sup> | 100 × (*S*<sub>*ijk*</sub> − *O*<sub>*ik*</sub>) / *O*<sub>*ik*</sub> |   (2)

where *S*<sub>*ijk*</sub> is the simulated value of index *k* at gauge *i* for model *j*, *O*<sub>*ik*</sub> the observed value, *N* = 13 gauges and *M* = 7 models. Cases with a zero observed denominator were excluded from the corresponding percentage-bias calculation. Signed biases are reported separately in the supplementary material; the two are never interchanged.

### 2.6 Independent validation

Parameters were estimated on 1981–2002 only and frozen, then applied to the calibration period itself, to the independent validation period 2003–2014, to the baseline 1995–2014 and to the future window. The application step never accesses observations of the target period, so the validation is genuinely out of sample.

### 2.7 Near-future projection and model agreement

Projected change was computed as

  Δ(%) = 100 × (BC<sub>2021–2050</sub> − BC<sub>1995–2014</sub>) / BC<sub>1995–2014</sub>   (3)

using the same model on both sides. Every statistic for 2021–2050 was recomputed from the daily bias-corrected series over that 30-year window and is not an average of shorter windows. Inter-model agreement is the fraction of the seven models sharing the majority sign of change; a change is called robust only when agreement reaches 0.80.

### 2.8 Interpretation and acceptance criteria

Eight acceptance criteria govern what may be claimed, each carrying a graded status and an explicit limitation rather than a binary pass. Two shape the presentation here. The criterion on temporal dependence is diagnostic only: no numerical threshold is imposed, because quantile mapping is a marginal transformation and any threshold would either fail every method by construction or be met by accident. The criterion on raw-input plausibility screens each scenario-window against the range reported for continental Southeast Asia together with the signal-preservation error of the correction; for 2021–2050 no combination was flagged. Gate statuses and the interpretation scope are supplied as machine-readable tables in the supplementary material.

---

## 3. Results

### 3.1 Calibration-period performance

Over 1981–2002 QDM removed almost all of the marginal bias (Table 2, Figure 2). Mean absolute bias across 13 gauges and 7 models fell from 71.1% to 0.03% for wet-day frequency, from 40.8% to 1.2% for PRCPTOT, from 45.3% to 0.01% for SDII and from 48.2% to 0.02% for *q*<sub>95</sub>. Rx1day, a pointwise maximum that the correction can rescale directly, improved from 49.1% to 7.3%. The sequence-dependent indices improved far less: Rx5day from 34.5% to 25.5%, CDD from 47.6% to 41.3% and CWD from 90.0% to 35.1%, leaving substantially larger residual errors than the marginal statistics obtained in the same fit.

### 3.2 Independent validation

Applying the frozen parameters to 2003–2014 provides an out-of-sample test of transferability (Table 3, Figure 3). Mean absolute bias in wet-day frequency is 28.6% against 67.2% for the raw models; PRCPTOT 15.8% against 38.5%; SDII 27.4% against 44.1%; and *q*<sub>95</sub> 33.7% against 48.0%. The correction improves every primary metric, roughly halving the error, but the residual remains substantial.

For sequence-dependent indices the outcome differs: Rx5day improves only from 35.6% to 31.5% and CWD from 83.2% to 38.7%, while CDD is not improved at all, at 49.8% after correction against 48.4% before it. In Figure 3 the dotted divider separates the two regimes, and CDD is the single index whose corrected bar exceeds the raw bar.

Restricting the network to the nine gauges not flagged by the homogeneity screening reduced the mean residual across the four primary metrics from 26.4% to 13.4%. This is an association between station heterogeneity and validation error, not an attribution of a specific share of it; the full network remains the primary result.

### 3.3 Near-future precipitation changes, 2021–2050

Projected changes in the bulk precipitation characteristics are small (Table 4, Figure 4). The ensemble median change in annual wet-day total is +0.1% under SSP2-4.5 and +0.7% under SSP5-8.5, with inter-model interquartile ranges of −1.5% to +8.2% and −7.0% to +6.2% respectively, straddling zero in both cases; wet-day frequency changes by +0.5% and +2.4%. SDII differs between scenarios: +2.1% under SSP2-4.5, one of only two indices in the analysis to reach the 0.80 agreement threshold, and −1.3% under SSP5-8.5. Agreement of 0.57 for the bulk characteristics under both scenarios corresponds to four of seven models sharing the majority sign and indicates weak ensemble consensus.

### 3.4 Near-future rainfall extremes

The extreme-rainfall indices show a clearer scenario contrast than the bulk characteristics (Table 4, Figure 5).

The ensemble medians of all retained intensity and tail indices are positive under SSP2-4.5: Rx1day +8.3%, R20mm +6.7%, R50mm +27.0%, R95p +14.9% and R99p +29.5%. Agreement is only 0.71 for each, however, and the inter-model ranges remain wide, spanning +6.7% to +38.5% for R50mm and −7.3% to +45.3% for R99p, so the direction is more consistent than the magnitude.

Under SSP5-8.5 the same indices show weaker or mixed changes: Rx1day −3.8%, R20mm −7.5%, R50mm +0.8%, R95p −4.9% and R99p +16.3%, all at 0.57 agreement. The absence of scenario ordering, with the lower-forcing scenario producing the larger increase in heavy rainfall, is discussed in Section 4.3.

CDD changes by −2.1% and +0.4% and CWD by +6.6% and +4.5%, with CWD reaching 0.86 agreement under both scenarios. Following Section 3.2 these two indices, with Rx5day, are reported as diagnostics and drawn as open hatched bars in Figure 5.

### 3.5 Gauge-level spatial pattern and model agreement

Figure 6 shows the ensemble median change in annual precipitation at each gauge, with an inverse-distance-weighted interpolation between the gauges as background. Under SSP2-4.5 the increases are concentrated in the southwestern lowlands and along the central axis, with small decreases in the northeast; under SSP5-8.5 the pattern is weaker and of mixed sign. Only two of 26 gauge-scenario combinations reach the 0.80 agreement threshold.

The interpolated surface is a spatial visualisation of gauge-level ensemble median changes, not a spatially resolved climate-model field. Because the raw model output delivers only one to five distinct series across the province (Table 1), the smooth gradients arise from interpolation between corrected gauge series and must not be read as structure resolved by the models. The gauges are drawn on top so that the analysed points remain distinguishable from the interpolation between them.

---

## 4. Discussion

### 4.1 Calibration is not validation

The contrast between Tables 2 and 3 is the clearest outcome of this study. Near-perfect calibration-period agreement is largely a property of the estimator and carries little information about transferability, whereas the same frozen parameters leave 15.8–33.7% residual error over an independent twelve years.

The residual is not evenly distributed. Four of thirteen gauges change their own wet-day frequency by more than a third between the two periods, and the calibration derived from the first period does not reproduce the second-period frequency equally well there. This may reflect nonstationarity or inhomogeneity in the records, changes in the model–observation relationship, sampling variability, or an interaction of these; station metadata were unavailable to distinguish among them. Comparable screening has led other Thai studies to remove affected stations after formal testing [7,13]; that option was unavailable here, so the flagged gauges are retained with disclosure as a diagnostic subset.

### 4.2 Marginal correction versus temporal dependence

Quantile mapping assigns a new magnitude to each rank; beyond the wet–dry reclassification implied by frequency adaptation it does not change which days are wet relative to one another, so indices defined on the sequence retain the model's own persistence structure. After a correction that reproduces the wet-day intensity distribution to within 0.03%, CDD remains biased by 41.3% in sample and 49.8% out of sample, the latter marginally worse than the uncorrected model. Frequency adaptation improves part of the sequencing, with *P*(wet | wet) improving from a bias of 6.9% to 0.6% because raising the threshold changes which days count as wet, but the lag-1 autocorrelation of occurrence is not improved (−6.5% raw against −7.1% corrected) and spell-length statistics retain biases of 10–12%.

Projections of accumulated volumes and intensity-based design quantities therefore rest on the component of the correction that demonstrably works, whereas projections of drought duration, spell length and multi-day accumulation rest on the component it does not directly reconstruct and require either explicit occurrence modelling, such as a stochastic weather generator, or acknowledgement of the limitation. CDD, CWD and Rx5day are labelled diagnostic throughout.

### 4.3 What the 2021–2050 projections support

Two features of Table 4 deserve comment. The first is the contrast between the bulk characteristics and the extremes: annual precipitation is essentially unchanged under both scenarios, yet the heavy-rainfall indices under SSP2-4.5 have positive medians of 7–30%. This combination is consistent with a redistribution of precipitation towards more intense events, but the present analysis does not diagnose the physical mechanism. The same combination has been reported over northeast Thailand, where no significant change in annual rainfall was projected for 2021–2050 while 20-year return values of Rx1day and Rx5day rose by more than 30% [8], and the observed record already shows intensification of daily rainfall intensity nationally [5,6].

The second is the absence of scenario ordering: the lower-forcing scenario produces the larger increase in heavy rainfall over this window. Over a near-future horizon the forced difference between the two scenarios is small, and each model contributes a single realisation, so a large initial-condition ensemble would be required to separate the forced response from internal variability. The non-monotonic scenario response and the limited agreement together indicate that the forced precipitation signal is difficult to distinguish from internal variability and inter-model spread at this scale, consistent with regional work in which inter-model uncertainty for rainfall exceeds the projected near-future change [8].

The practical reading is therefore restricted. Only SDII under SSP2-4.5 and the diagnostic CWD index under both scenarios reach 0.80 agreement; no non-diagnostic index reaches the threshold under both scenarios. Every other entry in Table 4 should be cited as an ensemble estimate with low to moderate agreement, not as a robust regional signal. This does not contradict the observed intensification reported for Thailand as a whole [5–7]: national-scale detection over five decades and provincial-scale projection from a seven-member ensemble are different problems with different signal-to-noise characteristics.

### 4.4 Limitations

The provincial boundary rests on a single verified source, and the Natural Earth polygon is a generalised cartographic product. Station history metadata were unavailable, so the four screened gauges remain flagged rather than formally tested. Each model contributes one realisation, the observed record is 34 years, and raw model fields deliver one to five distinct series across the province, limiting spatial inference. Only two emission scenarios were available, so scenario uncertainty is not fully sampled, and the analysis is confined to a single near-future window.

---

## 5. Conclusion

Quantile delta mapping reduced the mean absolute bias in wet-day frequency, annual total and wet-day intensity of seven CMIP6 models from 40–71% to below 1.2% over the calibration period, and to 15.8–33.7% over an independent period; in-sample agreement is largely a property of the method and is not evidence of transferable skill. The correction does not directly reconstruct indices governed by the ordering of wet and dry days: out of sample, the bias in maximum consecutive dry days was 49.8% after correction against 48.4% before it. Marginal bias correction and temporal dependence are separate problems, and results for CDD, CWD and Rx5day should not be described as corrected.

Restricting the network to the nine gauges not flagged by the homogeneity screening reduced the network-mean validation error from 26.4% to 13.4%, indicating that observational heterogeneity may constrain achievable out-of-sample performance.

For 2021–2050 the ensemble median change in annual precipitation is near zero under both scenarios. The median changes in selected heavy-rainfall indices are positive under SSP2-4.5, approximately 7–30%, but model agreement is below 0.80; under SSP5-8.5 the same indices show weaker or mixed changes, and inter-model spread is substantial throughout. Only SDII under SSP2-4.5 and the diagnostic CWD index reach 0.80 agreement.

The reliability of a bias-corrected projection depends on which component of rainfall variability the correction actually corrects; reporting that component explicitly, and declining to interpret what falls outside it, is the practical recommendation of this work.

---

## 6. Ethical Approval

Not applicable: the study used meteorological station records and publicly archived model output, with no human participants or animals.

## 7. Declaration of Generative AI and AI-Assisted Technologies in the Writing Process

During the preparation of this work the author used a generative AI assistant for code review, statistical verification and language editing. The author reviewed and edited the content afterwards and takes full responsibility for the publication.

## 8. Acknowledgements

The author thanks the Royal Irrigation Department and the Thai Meteorological Department for the rain-gauge records, the World Climate Research Programme for coordinating CMIP6, and the modelling groups listed in Table 1 for making their output available.

## 9. Author Contributions

Punyawansiri, S.: Conceptualization, Methodology, Software, Formal analysis, Data curation, Validation, Visualization, Writing – original draft, Writing – review & editing.

## 10. Conflicts of Interest

The author declares no conflict of interest.

## 11. References

[1] Cannon AJ, Sobie SR, Murdock TQ. Bias correction of GCM precipitation by quantile mapping: how well do methods preserve changes in quantiles and extremes? J Clim. 2015;28(17):6938-6959.

[2] Maraun D. Bias correcting climate change simulations: a critical review. Curr Clim Change Rep. 2016;2(4):211-220.

[3] Teutschbein C, Seibert J. Bias correction of regional climate model simulations for hydrological climate-change impact studies: review and evaluation of different methods. J Hydrol. 2012;456-457:12-29.

[4] United Nations Economic and Social Commission for Asia and the Pacific. Risk and Resilience Portal: Thailand country report [Internet]. Bangkok: ESCAP; 2025 [cited 2026 Aug 30].

[5] Limsakul A, Singhruck P. Long-term trends and variability of total and extreme precipitation in Thailand. Atmos Res. 2016;169:301-317.

[6] Limsakul A. Changes of daily rainfall intensity in Thailand from 1955 to 2019. Asia Pac J Sci Technol. 2022;27(1):APST-27-01-12.

[7] Paengkaew W, Limsakul A, Aroonchan N, Santisirisomboon J, Srisawadwong R, Amnuaylojaroen T, et al. Increasing compound hot-rainfall extreme in Thailand during 1970-2022. Asia Pac J Sci Technol. 2026;31(1):APST-31-01-02.

[8] Khadka D, Babel MS, Collins M, Shrestha S, Virdis SGP, Chen AS. Projected changes in the near-future mean climate and extreme climate events in northeast Thailand. Int J Climatol. 2022;42(2):1088-1111.

[9] Kuinkel D, Promchote P, Upreti KR, Aryal D, Bhandari S, Adhikari S. Projected changes in precipitation extremes in southern Thailand using CMIP6 models. Theor Appl Climatol. 2024;155(9):8703-8716.

[10] Themeßl MJ, Gobiet A, Heinrich G. Empirical-statistical downscaling and error correction of regional climate models and its impact on the climate change signal. Clim Change. 2012;112(2):449-468.

[11] Addor N, Rohrer M, Furrer R, Seibert J. Propagation of biases in climate models from the synoptic to the regional scale: implications for bias adjustment. J Geophys Res Atmos. 2016;121(5):2075-2089.

[12] Natural Earth. Admin 1 – states, provinces, 1:10 m cultural vectors [Internet]. [cited 2026 Aug 30]. Available from: https://www.naturalearthdata.com

[13] Wang XL. Accounting for autocorrelation in detecting mean shifts in climate data series using the penalized maximal t or F test. J Appl Meteorol Climatol. 2008;47(9):2423-2444.

[14] Eyring V, Bony S, Meehl GA, Senior CA, Stevens B, Stouffer RJ, et al. Overview of the Coupled Model Intercomparison Project Phase 6 (CMIP6) experimental design and organization. Geosci Model Dev. 2016;9(5):1937-1958.

[15] O'Neill BC, Tebaldi C, van Vuuren DP, Eyring V, Friedlingstein P, Hurtt G, et al. The Scenario Model Intercomparison Project (ScenarioMIP) for CMIP6. Geosci Model Dev. 2016;9(9):3461-3482.

[16] Ziehn T, Chamberlain MA, Law RM, Lenton A, Bodman RW, Dix M, et al. The Australian Earth System Model: ACCESS-ESM1.5. J South Hemisph Earth Syst Sci. 2020;70(1):193-214.

[17] Danabasoglu G, Lamarque JF, Bacmeister J, Bailey DA, DuVivier AK, Edwards J, et al. The Community Earth System Model version 2 (CESM2). J Adv Model Earth Syst. 2020;12(2):e2019MS001916.

[18] Swart NC, Cole JNS, Kharin VV, Lazare M, Scinocca JF, Gillett NP, et al. The Canadian Earth System Model version 5 (CanESM5.0.3). Geosci Model Dev. 2019;12(11):4823-4873.

[19] Döscher R, Acosta M, Alessandri A, Anthoni P, Arneth A, Arsouze T, et al. The EC-Earth3 Earth system model for the Coupled Model Intercomparison Project 6. Geosci Model Dev. 2022;15(7):2973-3020.

[20] Li L, Yu Y, Tang Y, Lin P, Xie J, Song M, et al. The Flexible Global Ocean-Atmosphere-Land System Model grid-point version 3 (FGOALS-g3): description and evaluation. J Adv Model Earth Syst. 2020;12(9):e2019MS002012.

[21] Tatebe H, Ogura T, Nitta T, Komuro Y, Ogochi K, Takemura T, et al. Description and basic evaluation of simulated mean state, internal variability, and climate sensitivity in MIROC6. Geosci Model Dev. 2019;12(7):2727-2765.

[22] Yukimoto S, Kawai H, Koshiro T, Oshima N, Yoshida K, Urakawa S, et al. The Meteorological Research Institute Earth System Model version 2.0, MRI-ESM2.0: description and basic evaluation of the physical component. J Meteorol Soc Jpn. 2019;97(5):931-965.

[23] World Climate Research Programme. Climate change indices. In: Expert Team on Climate Change Detection and Indices (ETCCDI) [Internet]. 2020 [cited 2026 Aug 30]. Available from: http://etccdi.pacificclimate.org

*Note to the author before submission. References [16–19] and [21] were supplied by the author from the CMIP6 model-description list. References [20] and [22] were added here to complete the seven models; their volume, issue and article numbers should be confirmed against the publisher record, as should the details of [4], [6], [7], [12] and [23]. The list contains 23 entries, within the APST limit of 35.*

---

## Tables

**Table 1** Configuration of the seven CMIP6 models. "Distinct series" is the number of different daily series the 13 analysed gauges receive from that model, that is the number of native grid cells effectively serving the province.

**Table 2** Calibration-period (1981–2002) mean absolute bias, defined by Equation (2), of raw and QDM-corrected CMIP6 daily precipitation against gauge observations, averaged over 13 gauges and 7 models. Marginal-distribution performance only; this table does not imply correction of temporal sequencing or multi-day persistence. Signed biases and the full metric set are given in Supplementary Table S2.

**Table 3** Independent validation (2003–2014) of QDM-corrected CMIP6 precipitation against observations, using parameters fitted on 1981–2002 and frozen. Mean absolute bias as defined by Equation (2), averaged over 13 gauges and 7 models. Signed biases are given in Supplementary Table S3 and the homogeneity sensitivity in Supplementary Table S4.

**Table 4** Projected change for 2021–2050 relative to each model's own bias-corrected baseline (1995–2014), from Equation (3). For each scenario the ensemble median, the inter-model interquartile range and the agreement fraction are given, with a flag for agreement of at least 0.80. Indices marked "diagnostic" depend on the ordering of wet and dry days, which quantile mapping does not correct (Section 3.2).

## Figures

**Figure 1** Location of Uttaradit Province in Thailand (inset) and the 13 rain gauges used in this study, over terrain elevation. The provincial boundary is shown in black.

**Figure 2** Mean absolute bias of raw and QDM-corrected CMIP6 daily precipitation against gauge observations over the calibration period 1981–2002. The dotted divider separates statistics primarily controlled by the marginal daily distribution from sequence-dependent and multi-day statistics that are not explicitly reconstructed by quantile mapping.

**Figure 3** As Figure 2, for the independent validation period 2003–2014 using parameters fitted on 1981–2002 and frozen. Axes are identical to Figure 2 to allow direct comparison. CDD is the only index for which the corrected bias exceeds the raw bias.

**Figure 4** Projected change in precipitation characteristics for 2021–2050 relative to each model's own bias-corrected baseline (1995–2014). Bars are ensemble medians and whiskers denote the inter-model interquartile range, which represents inter-model spread and not a confidence interval. The number beneath each bar is the inter-model agreement fraction; bold marks agreement of at least 0.80, and those bars are filled solid.

**Figure 5** As Figure 4, for the extreme-rainfall indices: (a) intensity and threshold indices and (b) tail and persistence indices. CDD, CWD and Rx5day depend on the ordering of wet and dry days, which quantile mapping does not correct; they are drawn as open hatched bars and are reported as diagnostics rather than as corrected projections.

**Figure 6** Ensemble median change in annual precipitation for 2021–2050 relative to each model's own bias-corrected baseline. The shaded surface is an inverse-distance-weighted interpolation between the 13 gauges, clipped to the verified provincial boundary; the gauges themselves are drawn on top, sized by the inter-model agreement fraction, with filled symbols for agreement of at least 0.80 and open symbols below it.
