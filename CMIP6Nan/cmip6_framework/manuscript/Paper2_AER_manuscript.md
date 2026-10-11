# Climate-signal preservation in bias-corrected daily precipitation: a comparison of quantile mapping methods over Uttaradit, Thailand

*Prepared for Applied Environmental Research. Microsoft Word, single column, double line spacing, Times New Roman 12 pt, automatic page numbering, continuous line numbering. Citations are numbered in order of appearance.*

---

Surasit Punyawansiri<sup>1,\*</sup>

<sup>1</sup>Office of Water Management and Hydrology, Royal Irrigation Department, Dusit, Bangkok 10300, Thailand

<sup>\*</sup>Corresponding author: Surasit.pu@ku.th

---

## Abstract

Bias correction is usually judged by how much historical error it removes, yet a correction applied to future simulations must also decide how much of the model's own climate-change signal survives. Empirical, detrended and delta quantile mapping were applied to daily precipitation from seven CMIP6 models at 13 rain gauges in northern Thailand under two SSP scenarios, sharing the same observations, quality control, occurrence model, calibration period (1981–2002), independent validation period (2003–2014) and future baseline, so that only the intensity transformation differed. Over calibration, empirical and delta mapping reduced the mean absolute bias in wet-day frequency from 71.14% to 0.03% and detrended mapping to 0.46%. Out of sample all three converged, to 28.65%, 28.76% and 28.65% against 67.22% for the raw models, and none improved maximum consecutive dry days. For 2021–2050 the median signal-preservation error stayed within 4.18% for bulk statistics and wet-day quantiles under every method, but reached 15.54% for the frequency of days above 50 mm. The method with the smallest absolute error changed with the scenario for eight of the sixteen indices examined, so no method was consistently closest to the raw signal. A descriptive two-factor sum-of-squares partition assigned at most 5.4% of the total to the additive method component. Method selection should be aligned with the rainfall characteristic and the signal property the analysis intends to preserve.

**Keywords:** Bias correction; Extreme rainfall; Quantile mapping; Signal preservation; Uttaradit

---

## 1. Introduction

Reliable precipitation projections are essential for assessing future water availability, hydrological risk, and other climate-related impacts at the local scale. Global climate models (GCMs) provide an important basis for such assessments, but systematic differences between simulated and observed precipitation can limit their direct application at regional and local scales. Statistical bias correction is therefore widely used to improve the suitability of GCM precipitation for impact-oriented applications [1–3].

Quantile-based bias-correction methods are particularly widely applied because they can effectively adjust systematic differences in precipitation characteristics. However, different formulations are designed to preserve different aspects of the simulated climate signal. Empirical quantile mapping (QM/EQM) primarily focuses on correcting the historical model distribution, whereas detrended quantile mapping (DetQM) and quantile delta mapping (QDM) incorporate mechanisms intended to retain changes simulated by the original model [1]. The choice among these approaches therefore involves more than selecting a method that produces the smallest historical error.

This issue is particularly relevant when corrected precipitation is used to assess rainfall extremes. Daily precipitation indices are derived in different ways, and their response to bias correction may not be uniform. A correction that performs well for general precipitation characteristics may not provide the same behaviour for extreme rainfall or persistence-related indices. Consequently, assessment of bias-correction methods should consider both how effectively they reduce historical bias and how they affect the climate-change signal represented by the original model.

Recent CMIP6-based assessments in Thailand have highlighted substantial spatial and temporal variability in projected precipitation, with some rainfall extremes exhibiting stronger changes than overall precipitation totals [4, 5]. A broader review of CMIP6 extreme precipitation projections across Asian subregions confirms that while models show substantial improvements over previous generations—particularly for intensity indices such as RX1day and R95p—persistent biases remain, especially in topographically complex and data-sparse regions [6]. These characteristics increase the importance of selecting an appropriate bias-correction approach for local climate applications. For regions such as Uttaradit Province in northern Thailand, where climate information is relevant to water-resource and environmental planning, a clearer understanding of the implications of method selection is particularly valuable.

Despite the extensive use of quantile-based bias correction, several questions remain open regarding the comparative behaviour of different formulations when they are evaluated within the same experimental framework. It remains important to determine whether strong historical bias reduction is maintained during independent validation, whether the intended climate-signal preservation associated with each method is consistently achieved across future scenarios, and whether preservation of the modelled signal extends from general precipitation characteristics to derived rainfall extremes and persistence-related indices. Addressing these questions requires a controlled comparison in which differences among methods can be examined without confounding changes in the observational data, model ensemble, calibration strategy, or evaluation periods. A recent systematic review of CMIP6 downscaling and extreme analysis across Asia has identified persistent gaps in the application of bias correction methods, particularly regarding the treatment of extremes in topographically complex regions [7].

This study therefore compares QM/EQM, DetQM, and QDM for daily precipitation from seven CMIP6 models and 13 rain gauges in Uttaradit, Thailand. Using a common split-sample framework with 1981–2002 for calibration, 2003–2014 for independent validation, and 2021–2050 for future assessment relative to 1995–2014, the study evaluates the performance of the three methods from complementary perspectives: historical bias reduction, independent out-of-sample performance, and preservation of the modelled climate-change signal across daily precipitation characteristics and rainfall extremes. The study seeks to clarify how bias-correction method choice affects the characteristics of corrected precipitation and the climate signal available for subsequent impact assessment, thereby providing a more informative basis for selecting bias-correction methods for local climate applications.

---

## 2. Materials and methods

### 2.1 Study area and data

Uttaradit Province lies in northern Thailand between 17.16° and 18.37° N and 99.90° and 101.17° E (Figure 1). Daily rainfall for 1981–2014 was used from 13 gauges, with mean annual wet-day totals over 1981–2002 of 954 to 1,326 mm.

### 2.2 Observed-data quality control

Zeros standing in for missing observations were screened against six diagnostics per station-month, combining the surrounding gauges, the station's own climatology for that calendar month and the length of the zero run; a zero was reclassified as missing only when at least one neighbour-based diagnostic and at least two in total supported it. Of 5,304 station-months, 43 were flagged, corresponding to 1,308 daily values or 0.810% of the record, which were set to missing; no value was imputed. The same quality-controlled record was used by all three methods.

### 2.3 Climate model data and experimental design

Daily precipitation was used from seven CMIP6 models [8, 9] for the historical experiment and for SSP2-4.5 and SSP5-8.5: ACCESS-ESM1-5 [10], CESM2 [11], CanESM5 [12], EC-Earth3 [13], FGOALS-g3 [14], MIROC6 [15] and MRI-ESM2-0 [16], all realisation r1i1p1f1 except CESM2 (r11i1p1f1). CESM2, CanESM5 and FGOALS-g3 use a 365-day calendar and the remainder the standard calendar; calendars were detected from the data. Across the 13 analysed gauges each model delivers between one and five distinct daily series (Supplementary Table S10), so the raw fields carry limited sub-provincial structure.

Parameters were estimated on 1981–2002 and frozen. The frozen parameters were applied to the calibration period itself, to the independent validation period 2003–2014, to the baseline 1995–2014 and to the future window 2021–2050. All statistics for 2021–2050 were recomputed from the daily corrected series over that 30-year window. Acceptance criteria governing what may be claimed are given in Supplementary Table S9.

### 2.4 Bias-correction methods

Supplementary Table S1 summarises the design of the three methods and the settings they share. All operate on wet days defined by a 1.0 mm d-1 threshold. Frequency adaptation is applied once per gauge–model pair before any intensity mapping: the model wet-day threshold is raised until the model wet-day frequency over the calibration period matches the observed frequency [17]. Because this occurrence model is estimated once and shared, differences between the methods arise from the intensity transformation alone.

Writing F⁻¹obs,cal and F⁻¹mod,cal for the observed and modelled wet-day quantile functions over the calibration period, and x for a target-period value,

  QM: BC(*x*) = *F*⁻¹<sub>obs,cal</sub>( *F*<sub>mod,cal</sub>(*x*) )   (1)

  DetQM: BC(*x*) = *s* · *F*⁻¹<sub>obs,cal</sub>( *F*<sub>mod,cal</sub>(*x*/*s*) ),  *s* = *μ*<sub>tgt</sub> / *μ*<sub>cal</sub>   (2)

  QDM: BC(*x*) = *F*⁻¹<sub>obs,cal</sub>(*p*) · [ *x* / *F*⁻¹<sub>mod,cal</sub>(*p*) ],  *p* = *F*<sub>mod,tgt</sub>(*x*)   (3)

where s is the ratio of the target-period to the calibration-period wet-day mean of the model. Empirical distributions were estimated from the sorted wet-day sample with Hazen plotting positions and linear interpolation. Beyond the calibration range the multiplicative correction ratio at the nearest calibration quantile was held constant, with no clipping; extrapolation affected 0.41% of wet days on average.

### 2.5 Rainfall indices

Indices follow the definitions of the Expert Team on Climate Change Detection and Indices [18] where applicable, supplemented by wet-day frequency and empirical wet-day quantiles: PRCPTOT, wet-day frequency, SDII, q50, q90, q95, q99, Rx1day, Rx5day, R10mm, R20mm, R50mm, R95p, R99p, CDD and CWD. Percentile thresholds for R95p and R99p came from observed wet days over the calibration period at each gauge. Direct quantiles, derived extremes and sequence-dependent indices are reported separately throughout.

### 2.6 Performance metric

Historical performance is the mean absolute bias,

  MAB(*k*) = (1 / *NM*) Σ<sub>*i*=1</sub><sup>*N*</sup> Σ<sub>*j*=1</sub><sup>*M*</sup> |ε<sub>*ijk*</sub>|   (4)

  *ε*<sub>*ijk*</sub> = 100 × (*S*<sub>*ijk*</sub> − *O*<sub>*ik*</sub>) / *O*<sub>*ik*</sub>   (5)

where S and O are the simulated and observed values of index k, N = 13 gauges and M = 7 models; cases with a zero observed denominator were excluded.

### 2.7 Climate-signal preservation

For a statistic q, the raw and corrected signals are the ratios of its 2021–2050 value to its 1995–2014 baseline value within the same model, written qfut and qbase,

  *S*<sub>raw</sub> = *q*<sub>fut,raw</sub> / *q*<sub>base,raw</sub>,  *S*<sub>BC</sub> = *q*<sub>fut,BC</sub> / *q*<sub>base,BC</sub>   (6)

and the signal-preservation error is

  PE(*q*) = 100 × ( *S*<sub>BC</sub> − *S*<sub>raw</sub> ) / *S*<sub>raw</sub>   (7)

PE near zero indicates close preservation, positive values amplification and negative values attenuation. Observations never enter the denominator of a climate-change signal.

### 2.8 Method and model effects

The spread of projected changes was summarised by a descriptive two-factor sum-of-squares partition with GCM and bias-correction method as the explicit factors, computed separately for each scenario. Because station is not modelled as a factor although the data are indexed by GCM × method × station, the residual carries the GCM × method interaction together with station-level and higher-order unmodelled variation; it should not be read as interaction alone, and this is not a full variance-component analysis.

### 2.9 Statistical interpretation

One estimator is used for every reported ensemble quantity. Within each GCM the signal-preservation error is averaged across the gauge evaluation locations at which it is defined, giving one value per model; the reported summary is the median of those values across the GCMs, with the inter-model interquartile range as a measure of spread rather than a confidence interval. Formally, for scenario c, index k and method m,

  *E*<sub>*j*</sub> = (1/*N*<sub>*j*</sub>) Σ<sub>*i*</sub> PE<sub>*ijkmc*</sub>,  reported value = median<sub>*j*</sub>(*E*<sub>*j*</sub>)   (8)

where i runs over gauges and j over GCMs. The gauges are evaluation locations, not independent model realizations, so they are averaged inside a model before the ensemble summary is taken; pooling gauge-by-model combinations into a single sample would allow the number of gauges to outweigh the inter-model spread, which is the quantity of interest here. Estimation is always separate by scenario: no aggregation across forcing pathways is defined, and none is reported. Where a threshold index has no qualifying day in a model's baseline the ratio is undefined, so the number of contributing GCMs is stated with every table.

When identifying the method closest to the raw signal, methods are compared on the absolute value of the ensemble-median PE. Paired method contrasts, given in Supplementary Table S8, are descriptive and carry no significance test. Seven models are too few, and are not a random sample of a defined population, to support an inferential claim about between-method differences; a non-significant result would be read as equivalence when it would only indicate low power.

---

## 3. Results and discussion

### 3.1 Historical bias reduction

All three methods removed most of the historical bias in the marginal statistics, and QM and QDM were numerically identical over the calibration period (Supplementary Table S2). Mean absolute bias in wet-day frequency fell from 71.14% in the raw models to 0.03% under QM and QDM and 0.46% under DetQM; SDII fell from 45.25% to 0.01% and 0.42%, and q95 from 48.17% to 0.02% and 0.19%. The identity between QM and QDM is expected rather than coincidental: over the calibration period the delta term in Eq. (3) equals unity, so QDM reduces exactly to QM. DetQM differs because it rescales by the target-period mean before mapping.

The largest reduction in mean absolute bias was for the frequency of days above 50 mm, where the raw bias of 194.93% fell to 1.04–1.05% under all three methods. Sequence-dependent indices behaved differently and the three methods were nearly indistinguishable: Rx5day improved only from 34.52% to 25.52%, CDD from 47.90% to 42.21–42.52% and CWD from 89.99% to 35.05–35.06%.

The apparent ordering over the calibration period largely reflects the construction of the methods. QM and QDM coincide there by construction and DetQM differs only through its rescaling step, so the sub-1% errors in Supplementary Table S2 describe the transformations rather than their skill. Out of sample the three give similar errors on the primary metrics, differing by less than 1 percentage point (Supplementary Table S3), while the residual error of 15–34% is an order of magnitude larger than any difference between them. A comparison based on calibration-period agreement alone would support conclusions the independent period does not sustain.

### 3.2 Independent validation

The calibration ordering did not survive out of sample, and the three methods converged (Figure 2 and Supplementary Table S3). Mean absolute bias in wet-day frequency was 28.65% for QM/EQM, 28.76% for DetQM and 28.65% for QDM, against 67.22% for the raw models. PRCPTOT was 15.90%, 15.10% and 15.82% against 38.45%; SDII 26.91%, 26.97% and 27.37% against 44.08%.

Small differences emerged for individual indices without favouring one method consistently. QM/EQM had the smallest error for q50 (24.17% against 26.52% for QDM), q95 (31.17% against 33.69%) and R95p (41.81% against 45.48%); DetQM for PRCPTOT (15.10%) and q99 (27.39%); QDM for Rx1day (26.85% against 30.96% for QM/EQM) and Rx5day (31.52% against 33.59%). CDD was improved by none of them: 51.47% to 51.98% after correction against 48.42% before it.

### 3.3 Preservation of bulk and distributional climate signals

Signal-preservation errors for the bulk statistics and the direct wet-day quantiles were small under every method and in both scenarios (Table 1, Figure 3; all indices in Supplementary Table S4 and the full listing in Supplementary Data S5). Preservation here is measured against each model's own raw change, not against observations, so a PE near zero means the modelled change was carried through, not that the corrected series matches the gauges. The largest absolute median PE anywhere in this group was +4.18% for q50 under QM/EQM in SSP2-4.5; under SSP5-8.5 the largest was +3.71% for q99 under DetQM. Across the three methods the median error for annual precipitation ranged from +0.75% to +1.27% in SSP2-4.5 and from −0.06% to +1.19% in SSP5-8.5.

Which method came closest to the raw signal depended on the quantile and on the scenario. At q95 the smallest absolute error corresponded to a median PE of −0.02% under DetQM in SSP2-4.5 and +0.75% under QDM in SSP5-8.5. At q99 QDM gave the smallest absolute error in both scenarios, with median PE of +0.26% and +0.03% against +1.95% and +3.60% for QM/EQM, whereas at q90 QM/EQM was smallest in both. Inter-model interquartile ranges overlap heavily across methods throughout this group.

The signal-preservation results do not order the three methods. Across the sixteen indices the smallest absolute error was returned by QDM in 17 of 32 scenario-index combinations, by DetQM in 9 and by QM/EQM in 6, and for only eight of the sixteen indices was the same method smallest under both scenarios. A ranking established under one forcing pathway therefore transfers to the other for only half the indices examined.

The departures from the design objectives are instructive. QDM gave the smallest absolute error at q99 under both scenarios, which is what a quantile-level delta is built to achieve, but at q95 only under SSP5-8.5 and at q90 under neither. This finding is consistent with Cannon et al. [1], who demonstrated that while QDM explicitly preserves relative changes in precipitation quantiles, the degree of preservation can vary across quantile levels and is influenced by the magnitude of the underlying bias and signal [1]. DetQM was smallest for SDII and q50 under SSP2-4.5 but not under SSP5-8.5; and QM/EQM, which makes no explicit provision for the signal, was smallest in six combinations including q90 under both.

The magnitudes are as informative as the ordering. For the bulk statistics and direct quantiles every median error lies within 4.18% of zero, and the spread between best and worst method is 0.52 and 1.25 percentage points for annual precipitation. Where the raw signal is a mean or a quantile of the corrected distribution, all three transformations reproduce it closely enough that the choice between them is of little consequence. A recent multi-continent comparison of QDM, EQM and DQM on CMIP6 daily precipitation similarly found that while EQM performed best overall in terms of performance–uncertainty trade-offs, the relative ranking of methods varied by region and by the specific evaluation metric used [19].

### 3.4 Preservation of extreme-rainfall signals

Errors were larger and the method contrasts wider for the derived extreme indices than for the direct quantiles (Table 2, Figure 4). The largest median error of the study was +15.54% for the frequency of days above 50 mm under QM/EQM in SSP2-4.5, against +6.60% for DetQM and +14.76% for QDM; in SSP5-8.5 the same index gave +5.29%, +9.67% and +8.38%. For R99p the medians were −9.21%, −5.76% and −5.95% in SSP2-4.5 and +13.86%, +4.75% and −5.98% in SSP5-8.5.

The spread between the best and worst method summarises how much the choice matters: 0.52 percentage points for annual precipitation in SSP2-4.5 and 1.25 in SSP5-8.5, against 8.94 and 4.39 for the frequency of days above 50 mm and 3.44 and 19.84 for R99p. Method-related differences were therefore substantially larger for several derived extreme indices than for the bulk statistics: 8.94 and 4.39 percentage points for the frequency of days above 50 mm against 0.52 and 1.25 for annual precipitation.

Sample size falls with rarity. All seven GCMs contribute to every bulk and quantile cell, but only six to the frequency of days above 50 mm, because EC-Earth3 simulates no such day at any gauge in the 1995–2014 baseline; within the contributing models the supporting gauges fall to between 9 and 12 of 13.

Across the sixteen indices examined, the method with the smallest absolute error was the same in both scenarios for only eight. QDM had the smallest error in 17 of the 32 scenario-index combinations, DetQM in 9 and QM/EQM in 6.

The picture changes for indices computed from the corrected sequence rather than read from the corrected distribution: median errors reach +15.54% for the frequency of days above 50 mm, and the spread between best and worst method reaches 8.94 percentage points for that index and 19.84 for R99p. This finding aligns with recent work by Padulano et al. [20], who demonstrated that bias-correction methods differ substantially in their ability to preserve climate signals in the variance and higher-order moments, with errors depending not only on the technique but also on the magnitude and direction of the underlying bias and signal [20].

The method with the smallest absolute signal-preservation error for a direct quantile is not systematically the method with the smallest error for the indices derived from it. Under SSP5-8.5, QDM gave the smallest absolute error at q95 and q99 yet the largest at R95p; under SSP2-4.5, DetQM was smallest for both q95 and the frequency of days above 50 mm, while QDM was smallest at q99 and DetQM at R99p. Preservation of a direct quantile signal and preservation of a derived threshold or tail index are separate properties, and the answer to RQ5 is negative.

Threshold indices can respond more strongly than quantiles to small magnitude changes near a fixed boundary, although this mechanism was not isolated here. The estimates for the rarest indices also rest on the fewest data, with only six GCMs contributing to the frequency of days above 50 mm, so the wide interquartile ranges in Figure 4 are part of the result rather than noise around it.

### 3.5 Temporal dependence and persistence

Residual errors in the wet–dry sequence were very similar across the three methods (Supplementary Table S7). Over the validation period the mean absolute bias in the transition probability P(wet | wet) was 14.25% for QM/EQM, 14.32% for DetQM and 14.40% for QDM against 26.99% for the raw models; that improvement follows from the shared frequency adaptation, not from the intensity transformation. The lag-1 autocorrelation of occurrence was not improved by any method, at 29.79% to 29.81% against 28.43% before correction, and mean dry-spell length remained biased by 35.66% to 36.43% against 54.26%. The three methods differ by less than 1 percentage point on every sequencing statistic, while the residual against observations stays between a quarter and a third.

Signal-preservation errors for the two persistence indices are correspondingly small and method-insensitive, spanning −3.32% to +2.61% for maximum consecutive dry days and −1.97% to +2.80% for maximum consecutive wet days across the two scenarios. Both are reported as diagnostics, because a marginal transformation cannot reconstruct the sequence on which they are defined.

None of the methods reconstructs event sequencing. This limitation is not method-sensitive. Quantile mapping assigns magnitudes to ranks. The only mechanism altering the wet–dry sequence is the shared frequency adaptation, which changes which days count as wet. Potter et al. [21] showed that quantile mapping cannot correct autocorrelation underestimation in rainfall sequencing. In the present study, the shared frequency adaptation roughly halves the bias in P(wet | wet). But lag-1 autocorrelation remains unimproved. Dry-spell length stays biased by more than a third. The three methods differ by <1 percentage point on every sequencing statistic. Residual error against observations remains between 25% and 33% for all methods. Marginal transformations alone cannot reconstruct precipitation temporal structure. Explicit modelling of occurrence dependence remains unresolved.

### 3.6 Relative roles of climate model and method effects

The additive main effect of the bias-correction method was small in both scenarios (Table 3). It reached at most 5.4% of the total sum of squares, for q50 under SSP2-4.5, and at most 1.0% under SSP5-8.5, for R95p. The GCM main effect spanned 9.5% to 82.3% under SSP2-4.5 and 25.4% to 83.5% under SSP5-8.5.

The residual term was large throughout, from 17.6% to 90.2% under SSP2-4.5 and 16.3% to 74.5% under SSP5-8.5, and largest for the same indices on which the methods diverged most: 90.2% for days above 20 mm under SSP2-4.5 and 74.5% for days above 50 mm under SSP5-8.5. Because station is not an explicit factor, this term carries station-level and higher-order variation as well as the GCM × method interaction and cannot be read as interaction alone.

### 3.7 Implications for impact studies

Method selection should follow the target quantity. For annual precipitation and the wet-day quantiles the differences between methods are small relative to the errors themselves, and any of the three would support the same conclusion; whether that carries over to a hydrological application is a separate question this study does not test, because no water-balance or runoff model was run. For indices built on threshold exceedance the differences are far larger and their sign changes between scenarios, so a study reporting a single method conveys less than the evidence supports; reporting two corrections, or stating which signal property the chosen one protects, costs little. For drought-duration and spell-length indicators, the limiting factor is not method choice but uncorrected sequencing. This points towards approaches that model occurrence explicitly rather than towards another quantile-mapping variant. O'Brien et al. [22] noted that quantile mapping takes no account of consecutiveness and can insert wet-day interruptions into otherwise dry periods. Method choice should therefore align with the target variable and the specific climate-signal property the analysis intends to preserve.

### 3.8 Limitations

Each model contributes one realisation, so the forced response cannot be separated from internal variability. The network comprises 13 gauges over one province and station history metadata were unavailable, so residual observational heterogeneity cannot be excluded. Raw model fields deliver only one to five distinct series across the study area, limiting spatial inference, and only two emission pathways and one future window were examined. All three methods are marginal daily transformations, so the comparison cannot establish how a method that models temporal structure explicitly would behave. The decomposition in Table 6 is a main-effect partition and does not resolve the interaction term it reports.

---

## 4. Conclusions

The three methods substantially reduced historical marginal bias, but their differences narrowed under independent validation, and none improved maximum consecutive dry days. Climate-signal preservation remained close to each model’s raw change for bulk statistics and direct quantiles, whereas method differences were larger and more variable for derived threshold- and tail-based indices. No single method consistently produced the smallest absolute error across scenarios and indices. This finding is consistent with evidence from other regions showing that the choice of quantile-mapping formulation can materially influence projected heavy precipitation and consecutive dry-day characteristics [23]. Temporal-dependence errors were also similar among the three methods, reflecting their shared marginal-correction framework. These results indicate that bias-correction method selection should be guided by the precipitation characteristic and climate-signal property of interest rather than by historical bias reduction alone.

---

## 5. Acknowledgements

The author thanks the Royal Irrigation Department and the Thai Meteorological Department for the rain-gauge records, the World Climate Research Programme for coordinating CMIP6, and the modelling groups listed in Section 2.3 for making their output available.

## 6. Conflict of interest

The author declares no conflict of interest.

## 7. Declaration of generative artificial intelligence in the writing process

During the preparation of this work the author used a generative artificial intelligence assistant for code review, statistical verification and language editing. The author reviewed and edited the content afterwards and takes full responsibility for the publication.

## 8. References

[1] Cannon, A.J., Sobie, S.R., Murdock, T.Q. Bias correction of GCM precipitation by quantile mapping: how well do methods preserve changes in quantiles and extremes? Journal of Climate, 2015, 28(17), 6938-6959.

[2] Maraun, D. Bias correcting climate change simulations: a critical review. Current Climate Change Reports, 2016, 2(4), 211-220.

[3] Teutschbein, C., Seibert, J. Bias correction of regional climate model simulations for hydrological climate-change impact studies: review and evaluation of different methods. Journal of Hydrology, 2012, 456-457, 12-29.

[4] Khadka, D., Babel, M.S., Collins, M., Shrestha, S., Virdis, S.G.P., Chen, A.S. Projected changes in the near-future mean climate and extreme climate events in northeast Thailand. International Journal of Climatology, 2022, 42(2), 1088-1111.

[5] Kuinkel, D., Promchote, P., Upreti, K.R., Aryal, D., Bhandari, S., Adhikari, S. Projected changes in precipitation extremes in southern Thailand using CMIP6 models. Theoretical and Applied Climatology, 2024, 155(9), 8703-8716.

[6] Tandon, A., Awasthi, A., Pattnayak, K.C. Extreme precipitation projections in Asian subregions: study on CMIP6 development, geographic patterns, and research gaps. Physics and Chemistry of the Earth, 2025, 140, 103963.

[7] Devadarshini, E., Geethalakshmi, V., McDermid, S.P., Bhuvaneswari, K., Mohan Kumar, S., Sathyamoorthy, N.K., … Anandhi, V. A systematic review of climate downscaling and extremes in Coupled Model Intercomparison Project 6 (CMIP6). Environmental Development, 2025, 56, 101280.

[8] Eyring, V., Bony, S., Meehl, G.A., Senior, C.A., Stevens, B., Stouffer, R.J., … Taylor, K.E. Overview of the Coupled Model Intercomparison Project Phase 6 (CMIP6) experimental design and organization. Geoscientific Model Development, 2016, 9(5), 1937-1958.

[9] O'Neill, B.C., Tebaldi, C., van Vuuren, D.P., Eyring, V., Friedlingstein, P., Hurtt, G., … Sanderson, B.M. The Scenario Model Intercomparison Project (ScenarioMIP) for CMIP6. Geoscientific Model Development, 2016, 9(9), 3461-3482.

[10] Ziehn, T., Chamberlain, M.A., Law, R.M., Lenton, A., Bodman, R.W., Dix, M., … Srbinovsky, J. The Australian Earth System Model: ACCESS-ESM1.5. Journal of Southern Hemisphere Earth Systems Science, 2020, 70(1), 193-214.

[11] Danabasoglu, G., Lamarque, J.F., Bacmeister, J., Bailey, D.A., DuVivier, A.K., Edwards, J., … Strand, W.G. The Community Earth System Model version 2 (CESM2). Journal of Advances in Modeling Earth Systems, 2020, 12(2), e2019MS001916.

[12] Swart, N.C., Cole, J.N.S., Kharin, V.V., Lazare, M., Scinocca, J.F., Gillett, N.P., … Winter, B. The Canadian Earth System Model version 5 (CanESM5.0.3). Geoscientific Model Development, 2019, 12(11), 4823-4873.

[13] Döscher, R., Acosta, M., Alessandri, A., Anthoni, P., Arneth, A., Arsouze, T., … Zhang, Q. The EC-Earth3 Earth system model for the Coupled Model Intercomparison Project 6. Geoscientific Model Development, 2022, 15(7), 2973-3020.

[14] Li, L., Yu, Y., Tang, Y., Lin, P., Xie, J., Song, M., … Wang, B. The Flexible Global Ocean-Atmosphere-Land System Model grid-point version 3 (FGOALS-g3): description and evaluation. Journal of Advances in Modeling Earth Systems, 2020, 12(9), e2019MS002012.

[15] Tatebe, H., Ogura, T., Nitta, T., Komuro, Y., Ogochi, K., Takemura, T., … Kimoto, M. Description and basic evaluation of simulated mean state, internal variability, and climate sensitivity in MIROC6. Geoscientific Model Development, 2019, 12(7), 2727-2765.

[16] Yukimoto, S., Kawai, H., Koshiro, T., Oshima, N., Yoshida, K., Urakawa, S., … Ishii, M. The Meteorological Research Institute Earth System Model version 2.0, MRI-ESM2.0: description and basic evaluation of the physical component. Journal of the Meteorological Society of Japan, 2019, 97(5), 931-965.

[17] Themeßl, M.J., Gobiet, A., Heinrich, G. Empirical-statistical downscaling and error correction of regional climate models and its impact on the climate change signal. Climatic Change, 2012, 112(2), 449-468.

[18] Zhang, X., Alexander, L., Hegerl, G.C., Jones, P., Klein Tank, A., Peterson, T.C., … Zwiers, F.W. Indices for monitoring changes in extremes based on daily temperature and precipitation data. WIREs Climate Change, 2011, 2(6), 851-870.

[19] Song, Y.H., Chung, E.-S. Intercomparison of bias correction methods for precipitation of multiple GCMs across six continents. Geoscientific Model Development, 2025, 18(21), 8017-8045.

[20] Padulano, R., Gomez-Mogollon, L.A., Napolitano, L., Rianna, G. Quantile-based bias-correction of extreme rainfall: pros and cons of popular methods for climate signal preservation. Journal of Hydrology, 2025, 653, 132814.

[21] Potter, N.J., Chiew, F.H.S., Charles, S.P., Fu, G., Zheng, H., Zhang, L. Bias in dynamically downscaled rainfall characteristics for hydroclimatic projections. Hydrology and Earth System Sciences, 2020, 24, 2963-2979.

[22] O'Brien, E., Griffin, S., Duffy, C., Nolan, P. Resolving the dry period projection paradox: treat 'consecutiveness' as a nonlinearity. International Journal of Climatology, 2025, 45(11), e8745.

[23] Addisuu, A.A., Tsidu, G.M., Basupi, L.V. Impact of two variants of quantile mapping bias correction on CMIP6-based projections of extreme precipitation over southern Africa. International Journal of Climatology, 2026, 46(10), e70428.

---

## Tables and figures

**Table 1** Climate-signal preservation for bulk statistics and wet-day quantiles, 2021-2050 relative to the 1995-2014 baseline of the same model and method. Each cell is the median [interquartile range] of the signal-preservation error from Eq. (7), where the error is first averaged across the gauge evaluation locations within each climate model and the summary is then taken across models, as defined by Eq. (8). Scenarios are reported separately and are never pooled. The column *n* gives the number of contributing climate models.

**Table 2** Climate-signal preservation for derived extreme-rainfall indices. Format and estimator as Table 1. The Type column records how each index is constructed. The frequency of days above 50 mm rests on six climate models because EC-Earth3 simulates no such day in the baseline.

**Table 3** Descriptive two-factor sum-of-squares partition of the projected change by climate model and bias-correction method, computed separately for each scenario, for the indices discussed in Section 3.6; the full listing is in Supplementary Table S6. *N* is the number of model x method x gauge cells entering the partition and *n* the number of contributing models. The residual includes the model x method interaction together with station-level and higher-order unmodelled variation, because station is not an explicit factor. This is not a variance-component analysis.

**Figure 1** Location of Uttaradit Province in Thailand (inset) and the 13 rain gauges used in this study, over terrain elevation.

**Figure 2** Mean absolute bias of raw and bias-corrected daily precipitation against gauge observations over the independent validation period 2003-2014, using parameters fitted on 1981-2002 and frozen, averaged across 13 gauges and 7 climate models. Indices to the right of the dashed rule, on the shaded background, are sequence-dependent: quantile mapping does not reorder days, so it does not reconstruct them. The calibration-period values are given in Supplementary Table S2.

**Figure 3** Signal-preservation error for 2021-2050 relative to the 1995-2014 baseline of the same model and method: (a) bulk statistics and (b) wet-day quantiles, each with the two scenarios side by side on a shared vertical scale. Bars are the ensemble median across the seven climate models and whiskers the inter-model interquartile range, a measure of spread and not a confidence interval; both follow Eq. (8). A value of zero means the raw model signal was reproduced exactly.

**Figure 4** As Figure 3, for derived extreme-rainfall indices: (a) daily and threshold-derived extremes and (b) tail-derived and sequence-dependent indices, using the construction types of Table 2. Indices on the shaded background, to the right of the dashed rule, are sequence-dependent: a marginal transformation cannot reconstruct the day ordering on which they are defined. The same marking is used in Figures 2 and 5.

**Figure 5** Signal-preservation error for every index and method, with (a) SSP2-4.5 and (b) SSP5-8.5 on a shared vertical scale. Values are those of Tables 1 and 2. Symbols are ensemble medians and bars the inter-model interquartile range. Indices to the right of the dashed rule, on the shaded background, are sequence-dependent, marked as in Figures 2 and 4.
