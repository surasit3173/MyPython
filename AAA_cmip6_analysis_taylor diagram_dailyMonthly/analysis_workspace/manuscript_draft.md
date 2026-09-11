# Baseline sensitivity and robustness of bias-corrected CMIP6 daily precipitation-extreme projections for Uttaradit Province, Thailand

**[Author 1 full name]1, [Author 2 full name]1 and [Corresponding author full name]1,***

1 [Department, Institution, City, Postal code, Country]

*Corresponding author: [email address]

## Abstract

Reliable local projections of rainfall extremes require both climate-model evaluation and a change estimand that is not confounded by residual historical bias. This study audited and independently recomputed a supplied workflow comprising daily rainfall observations from 13 gauges in Uttaradit Province (1981–2014), seven CMIP6 models, bias-corrected historical and future series, SSP2-4.5 and SSP5-8.5, and 11 precipitation-extreme indices. Future changes were calculated for non-overlapping near- (2021–2040), mid- (2041–2060), and long-term (2081–2100) periods relative to 1995–2014. The primary estimand compared each model's future period with its own bias-corrected historical simulation; a direct future-versus-observed comparison was retained as a sensitivity test. Bias correction reduced median daily percentage bias from −21.9% to −9.0% and raised monthly correlation from 0.272 to 0.441, but median daily RMSE increased from 10.18 to 11.84 mm day−1. Residual biases remained large for CDD (+29.6%), CWD (−64.1%), R95p (+22.1%), and R99p (+20.7%). Changing the baseline source from observations to each model's corrected historical series reversed the projected sign for 25 of 66 scenario–period–index combinations and changed the robustness class for 37. With a model-consistent baseline, SSP2-4.5 showed robust mid-century increases in Rx5day (+12.5%) and R99p (+26.5%), whereas SSP5-8.5 showed robust long-term reductions in PRCPTOT (−46.7%), SDII (−27.7%), Rx5day (−25.2%), R99p (−62.6%), and CWD (−14.0%); CDD remained ambiguous. Baseline definition and bias-correction provenance therefore materially govern local hazard interpretation and should be audited before adaptation use.

**Keywords:** Bias correction, Climate extremes, CMIP6, Model agreement, Precipitation, SSP scenarios, Thailand, Uncertainty

## 1. Introduction

Changes in precipitation amount, intensity, and persistence can affect water supply, rain-fed agriculture, drainage design, and ecosystem management. The Sixth Assessment Report of the Intergovernmental Panel on Climate Change (IPCC) concludes that the global water cycle will become more variable and that heavy precipitation is likely to intensify over many parts of Asia, while the direction and seasonal expression of rainfall change remain spatially heterogeneous [1]. The Coupled Model Intercomparison Project Phase 6 (CMIP6) and ScenarioMIP provide a coordinated basis for evaluating these changes under alternative forcing pathways [2,3]. Their regional application nevertheless requires careful treatment of model bias, local representativeness, and multimodel uncertainty.

Daily precipitation indices provide information that annual or monthly means cannot. Wet-day totals, maximum 1- and 5-day rainfall, threshold exceedance counts, upper-tail totals, and consecutive wet or dry spells describe distinct components of the rainfall distribution [4,5]. Tung et al. [6] demonstrated how a coherent index framework can connect data evaluation, spatial patterns, temporal behavior, and bounded interpretation. That structure is useful for a projection study, but future simulations introduce an additional question: what historical baseline should define “change”? Daily model distributions can contain wet-day, intensity, and tail errors even when monthly behavior appears plausible [7]. Bias correction can reduce these discrepancies, yet conventional quantile mapping may alter the projected change signal. Quantile delta mapping (QDM) was developed specifically to preserve modeled relative changes in precipitation quantiles [8]. A corrected series should therefore be evaluated not only for historical fit but also for residual bias and change-signal preservation. A complete evaluation should combine correlation and variability diagnostics [9], hydrological efficiency diagnostics [10], and awareness of model performance and interdependence [11].

Thailand studies have reported marked model, subregional, and seasonal variation in projected rainfall [12,13]. Uttaradit-specific observational work has also documented spatial rainfall variability and drought concern [14], while recent national, Northern Thailand, and Southern Thailand studies already address CMIP6 extremes, drought, or return periods [15–17]. Consequently, the defensible gap is not the first use of rainfall indices or CMIP6 in the region. It is the effect of analytical choices—particularly residual bias, baseline definition, time-window selection, and ensemble aggregation—on province-scale conclusions.

This study had three objectives. First, it independently checked the supplied code, daily data, and archived outputs, including historical skill at daily and monthly scales. Second, it quantified how projection direction and robustness changed when future bias-corrected simulations were compared directly with observations versus with the corresponding bias-corrected historical model. Third, it reported only those future changes that remained supported by at least six of seven models under a single baseline and non-overlapping projection periods. The study thus treats the projections as climate-hazard information, not as direct estimates of flood damage, crop loss, or hydrological impact.

## 2. Materials and methods

### 2.1 Study area and data

Uttaradit Province is located in northern Thailand. The analyzed network comprised 13 gauges between 17.23–18.02°N and 100.05–101.07°E, with station elevations from 54.57 to 427.85 m (Figure 1). Observed daily rainfall covered 1 January 1981 to 31 December 2014 without duplicate dates, missing numeric cells, or negative rainfall. The station identifiers were 351001–351012 and 351201.

The supplied model archive contained one realization from each of seven CMIP6 models: ACCESS-ESM1-5, CanESM5, CESM2, EC-Earth3, FGOALS-g3, MIROC6, and MRI-ESM2-0. For every model, raw and bias-corrected daily precipitation were available for the historical period (1981–2014) and for SSP2-4.5 and SSP5-8.5 (2015–2100). Scenario naming follows ScenarioMIP [3]. The archive labels the corrected series as QDM outputs, but did not include the calibration code, quantile settings, occurrence adjustment, or an independent calibration–validation split. We therefore use the term “supplied bias-corrected series” and treat QDM provenance as unverified.

Three models used a 365-day calendar represented without leap days; the other data used the Gregorian calendar. No dates or rainfall values were imputed. Indices were calculated within each model's available calendar year, and periods were compared by annual statistics. All regional summaries gave equal weight to the 13 gauges and equal weight to the seven models. These are station-network summaries rather than area-weighted provincial averages.

**[Insert Figure 1 near here]**

### 2.2 Independent code and data audit

The source archives were hashed, and their internal input files and generated tables were inventoried. Index calculations were independently reimplemented from the daily CSV files rather than accepted from the archived spreadsheets. The independent implementation reproduced the archived legacy regional results when the same observed baseline (1981–2014), overlapping 30-year windows, station-percentage averaging, and ensemble mean were used. This established code-to-table traceability.

The audit then identified three issues relevant to inference. First, the archived near (2021–2050) and mid (2041–2070) windows overlap during 2041–2050; they are usable as climatologies but not as independent period contrasts. Second, future corrected values were compared directly with observed index means despite non-negligible residual historical bias. Third, percentage changes in rare-count indices can be unstable. For example, an archived SSP5-8.5 late-century R50mm summary had a positive mean percentage change (+72.2%) even though the regional absolute change was negative (−0.83 days yr−1) and six of seven models agreed on a decrease. The primary analysis therefore used non-overlapping 20-year periods, model-consistent historical baselines, ensemble medians, and absolute units for R50mm.

The supplied trend module also contained a Monte Carlo self-test. Under an AR(1) process with lag-1 autocorrelation 0.6 and no trend, the reported false-positive rate of trend-free pre-whitened Mann–Kendall (TFPW-MK) was 0.383 at a nominal 0.05 level. An independent audit used 2,000 zero-initialized Gaussian AR(1) null series (length 20, lag-1 coefficient 0.6, unit-normal innovations, random seed 20260829) and returned false-positive rates of 0.225 for conventional Mann–Kendall, 0.227 for the supplied Hamed–Rao implementation, and 0.267 for TFPW-MK. Because these diagnostics did not support confirmatory type-I error control, archived trend p-values were excluded from the manuscript. Model sign agreement is reported as a descriptive robustness screen, not statistical significance. The original methods were consulted only to identify the intended tests [18,19].

### 2.3 Precipitation-extreme indices

A wet day was defined as daily precipitation greater than or equal to 1 mm. Station-specific 95th and 99th percentile thresholds were calculated from all observed wet days during 1981–2014 and then held fixed for observed and model calculations. Spells and rolling 5-day totals were reset at each calendar-year boundary. The 11 indices are ETCCDI or ETCCDI-style measures [4,5] and are defined in Table 1. R50mm is a study-specific fixed-threshold count and is not part of the core ETCCDI set.

**[Insert Table 1 near here]**

### 2.4 Historical performance and residual bias

Raw and corrected historical simulations were aligned with observations at each model–gauge pair. Daily and monthly performance was summarized by Pearson correlation (r), root mean squared error (RMSE), mean absolute error (MAE), percentage bias (PBIAS), Nash–Sutcliffe efficiency (NSE), and Kling–Gupta efficiency (KGE). Taylor-style correlation and variability diagnostics are useful summaries [9], but bias- and error-sensitive diagnostics were retained because no single metric establishes precipitation skill [7,10]. Results are medians and interquartile ranges across 91 model–gauge pairs.

Residual bias was calculated for each index over 1995–2014 as the bias-corrected historical mean minus the observed mean. This interval was chosen to match the IPCC AR6 reference period [1]. Raw-to-corrected change-signal preservation was evaluated for every model, scenario, period, and index by comparing each future period with the corresponding raw or corrected 1995–2014 model baseline.

### 2.5 Projection estimands and robustness

The near-, mid-, and long-term periods were 2021–2040, 2041–2060, and 2081–2100, respectively. For model m, station s, index k, scenario q, and future period w, the primary absolute change was

Δmodel = mean(BC futurem,s,k,q,w) − mean(BC historicalm,s,k,1995–2014).

The sensitivity estimand replaced the model historical term with the observed station mean for 1995–2014. Relative changes were calculated after first averaging the 13 stations for each model, thereby avoiding disproportionate weight from stations with small denominators. The multimodel central estimate was the median of seven model-level regional changes; the 25th–75th percentile range described spread. A change was classified as a robust increase or decrease when at least six of seven models (≥80%) agreed on its sign. Other combinations were classified as ambiguous. Equal weighting was retained for transparency, while recognizing that model dependence can make strict model democracy suboptimal [11].

## 3. Results

### 3.1 Historical performance and residual bias

Bias correction improved some but not all aspects of historical performance (Table 2). At the daily model–gauge scale, median PBIAS improved from −21.9% to −9.0%, correlation rose from 0.037 to 0.057, and KGE rose from −0.120 to 0.012. However, median daily RMSE increased from 10.18 to 11.84 mm day−1, and only 8.8% of model–gauge pairs had lower RMSE after correction. At monthly scale, median correlation increased from 0.272 to 0.441 and KGE from 0.162 to 0.385, while RMSE increased from 103.98 to 108.73 mm month−1. Across both scales, absolute PBIAS improved for 67.0% of pairs; KGE improved for 85.7%.

**[Insert Table 2 near here]**

Historical correction did not eliminate index-specific errors. Across the seven model-level regional summaries for 1995–2014, median residual bias was +29.6% for CDD, −64.1% for CWD, +18.0% for SDII, +14.7% for Rx5day, +22.1% for R95p, and +20.7% for R99p. PRCPTOT residual bias was smaller (median −5.3%) but ranged sufficiently across models to affect some change estimates. These errors explain why a future-versus-observed contrast can mix model bias with simulated climate change.

### 3.2 Sensitivity to baseline and correction

Baseline selection materially altered the result (Figure 2). Of 66 scenario–period–index combinations, 25 (37.9%) changed sign when the observed baseline was replaced by the model-consistent historical baseline. The three-class label (robust increase, robust decrease, or ambiguous) changed for 37 combinations (56.1%). These frequencies are descriptive sensitivity results, not hypothesis-test outcomes. The largest departures were associated with large residual biases in CWD, CDD, R20mm, R95p, and R99p. R50mm required separate reporting in absolute units because its small count baselines made percentages unstable.

Bias correction also modified the modeled change signal. Across 462 model–scenario–period–index cases, raw and corrected changes had the same sign in 66.9% of cases. The median absolute difference between their relative changes was 12.1 percentage points. This diagnostic does not by itself prove an error in correction, because fixed-threshold and spell indices can respond nonlinearly to distributional adjustment. It does show that change preservation could not be assumed from the file label alone.

**[Insert Figure 2 near here]**

### 3.3 Audited future changes

The model-consistent results did not support a monotonic province-wide increase in precipitation extremes (Figures 3 and 4; Table 3). Under SSP2-4.5, all near-term indices were ambiguous. In the mid-term, six of seven models supported increases in Rx5day (+12.5%; interquartile range 7.5–27.4%), R95p (+9.9%; 1.5–27.6%), and R99p (+26.5%; 8.4–55.4%). R50mm increased by a median 0.65 days yr−1 (0.18–1.06 days yr−1); its +30.8% relative value is secondary because of denominator sensitivity. SSP2-4.5 long-term changes were ambiguous for all 11 indices.

Under SSP5-8.5, the near-term signal was also mostly ambiguous; only CWD showed a small robust increase (+0.27 days, +2.2%). The mid-term showed robust but modest reductions in PRCPTOT (−1.9%), SDII (−5.5%), R10mm (−4.5%), and R20mm (−9.4%). By 2081–2100, the ensemble showed a broad and internally consistent reduction in wet-day amount, frequency, and upper-tail totals: PRCPTOT −46.7%, SDII −27.7%, Rx1day −25.6%, Rx5day −25.2%, R95p −64.5%, R99p −62.6%, R10mm −51.1%, R20mm −62.2%, and CWD −14.0%. R50mm decreased by 1.18 days yr−1. PRCPTOT decreased at every gauge with seven-of-seven model agreement; station-level median changes ranged from −51.6% to −27.3%. In contrast, CDD remained ambiguous at regional and station scales. The result is therefore a robust reduction in modeled rainfall amount and wet-event metrics, not evidence of a robust increase in maximum dry-spell length.

**[Insert Figure 3 near here]**

**[Insert Figure 4 near here]**

**[Insert Table 3 near here]**

## 4. Discussion

### 4.1 Baseline definition is part of the scientific estimand

A future-versus-observed comparison answers an absolute consistency question: how does a model's future climatology compare with the observed past? When historical correction is imperfect, however, that contrast equals the model's simulated change plus residual historical bias. The model-consistent contrast better isolates the change carried by each corrected simulation. This distinction was consequential in Uttaradit because residual biases for spells and upper-tail indices were often larger than the projected near- and mid-century changes. The legacy R50mm example further showed that averaging station-level percentages can produce a sign opposite to the absolute regional change when denominators are small. Absolute units, regional ratios, and sign agreement should therefore be examined together.

These findings reinforce two methodological principles. First, bias correction should be evaluated out of sample and for the properties used in impact analysis, not only for mean rainfall. Daily probability distributions contain occurrence and tail behavior that monthly statistics can hide [7]. Second, future change preservation must be demonstrated. QDM is designed to preserve relative changes in model quantiles [8], but the supplied archive was insufficient to verify its calibration, and only two-thirds of derived index changes retained the raw-model sign. The latter result is a diagnostic warning rather than a definitive QDM assessment because annual spells and threshold exceedances are nonlinear functions of daily rainfall.

### 4.2 Interpretation for Uttaradit

The audited projections describe two different projection patterns. Under SSP2-4.5, the most coherent signal was a mid-century intensification of multi-day and upper-tail rainfall without a robust change in annual wet-day total. This combination could matter for short-duration drainage and erosion planning, but no direct flood consequence can be inferred without catchment, soil, river, and exposure data. Under SSP5-8.5, the long-term result was a widespread reduction in total rainfall, wet-spell persistence, and heavy-rainfall totals. Because CDD was ambiguous, the result should not be translated into a claim of longer annual dry spells; it more directly indicates fewer and weaker modeled wet events.

The strong late-century SSP5-8.5 drying in this seven-model local archive differs from the broad IPCC assessment that heavy precipitation will increase over much of Asia [1]. Such a difference is not necessarily contradictory: IPCC statements cover large reference regions and calibrated lines of evidence, whereas the present analysis concerns one province, a small equal-weight ensemble, supplied corrected station series, and annual index summaries. Thailand studies have likewise shown substantial dependence on model, subregion, season, and period [12,13]. The local signal should therefore be treated as a scenario-conditioned stress test, not a replacement for regional assessment.

The results can inform the climate-information component of provincial planning. SSP2-4.5 mid-century upper-tail increases support testing preparedness for concentrated rainfall, while SSP5-8.5 late-century reductions support testing water-supply and agricultural systems against lower annual inflow and shorter wet spells. Thailand's National Adaptation Plan emphasizes science-based subnational risk information [20]. Translation to operational thresholds requires seasonal analyses and sector-specific response models beyond the scope of this study.

### 4.3 Limitations and priorities for revision

Several limitations bound the conclusions. The bias-correction algorithm, training period, wet-day occurrence treatment, extrapolation rule, and validation split were not included; these must be archived before journal submission. The seven models were equally weighted and represented by one realization each, without adjustment for shared genealogy or dependence [11]. The station-indexed model series may originate from fewer independent source grid cells than the 13 station labels, while the equal station average does not represent province area. Only annual indices were analyzed, so monsoon onset, cessation, and seasonal risk windows remain unresolved. Fixed 1981–2014 observed thresholds were used for R95p and R99p. Because threshold exceedance totals are nonlinear, subtracting each model's corrected historical result does not guarantee that threshold-transfer bias cancels; these results should be interpreted as changes in observed-threshold exceedance totals in the supplied corrected series, and alternative thresholds should be tested. Calendar differences were retained rather than imputed. Finally, the robustness flag measures model sign agreement and does not quantify probability, internal variability, or statistical significance.

A publication-final analysis should therefore include the bias-correction source code and a blocked calibration–validation design; a raw-versus-corrected change-factor audit by quantile; sensitivity to model dependence or performance weighting; bootstrap uncertainty for ensemble medians; seasonal indices; and, if available, an independent observational product. These additions would strengthen, rather than merely enlarge, the evidence base.

## 5. Conclusion

Independent recomputation showed that the supplied workflow is traceable but that its headline conclusions are sensitive to residual bias, baseline source, overlapping windows, and percentage aggregation. The overlapping legacy windows are non-independent. Within the non-overlapping AR6-style periods, replacing the observed reference with each model's corrected historical baseline changed the sign of 25/66 results and the robustness class of 37/66 results. The corrected interpretation is specific: SSP2-4.5 supports mid-century increases in selected multi-day and upper-tail indices, whereas SSP5-8.5 supports strong late-century reductions in rainfall amount, wet-day intensity, wet-spell duration, and heavy-rainfall totals; CDD is not robust. These projections are suitable as bounded climate-hazard scenarios only after their correction provenance and out-of-sample performance are documented.

## 6. Ethical Approval

Not applicable. This study used meteorological observations and climate-model simulations and did not involve human participants or animals.

## 7. Declaration of Generative AI and AI-Assisted Technologies in the Writing Process

During preparation of this draft, the author(s) used OpenAI Codex to assist with code auditing, independent recalculation, data visualization, document formatting, and language drafting. The author(s) must review and edit the content, verify all references and declarations, and accept full responsibility for the submitted publication. **[Author confirmation required before submission.]**

## 8. Acknowledgements

**[Insert acknowledgements and funding source, including grant number, or state “None”.]**

## 9. Author Contributions

**[Replace with author names and verified CRediT roles: Conceptualization; Data curation; Formal analysis; Investigation; Methodology; Software; Validation; Visualization; Writing – original draft; Writing – review and editing.]**

## 10. Conflicts of Interest

**[Author confirmation required: declare any competing interests or state that none exist.]**

## 11. Data and Code Availability

The observations, model series, source code, and archived outputs used for this draft were supplied by the study authors. **[Before submission, provide a repository URL/DOI, access conditions, software environment, and the complete bias-correction provenance.]**

## 12. References

1. IPCC. Climate Change 2021: The Physical Science Basis. Contribution of Working Group I to the Sixth Assessment Report of the Intergovernmental Panel on Climate Change. Masson-Delmotte V, Zhai P, Pirani A, Connors SL, Péan C, Berger S, et al., editors. Cambridge: Cambridge University Press; 2021. doi:10.1017/9781009157896.
2. Eyring V, Bony S, Meehl GA, Senior CA, Stevens B, Stouffer RJ, et al. Overview of the Coupled Model Intercomparison Project Phase 6 (CMIP6) experimental design and organization. Geosci Model Dev. 2016;9:1937-1958. doi:10.5194/gmd-9-1937-2016.
3. O'Neill BC, Tebaldi C, van Vuuren DP, Eyring V, Friedlingstein P, Hurtt G, et al. The Scenario Model Intercomparison Project (ScenarioMIP) for CMIP6. Geosci Model Dev. 2016;9:3461-3482. doi:10.5194/gmd-9-3461-2016.
4. Zhang X, Alexander L, Hegerl GC, Jones P, Klein Tank AMG, Peterson TC, et al. Indices for monitoring changes in extremes based on daily temperature and precipitation data. Wiley Interdiscip Rev Clim Change. 2011;2:851-870. doi:10.1002/wcc.147.
5. Donat MG, Alexander LV, Yang H, Durre I, Vose R, Dunn RJH, et al. Updated analyses of temperature and precipitation extreme indices since the beginning of the twentieth century: the HadEX2 dataset. J Geophys Res Atmos. 2013;118:2098-2118. doi:10.1002/jgrd.50150.
6. Tung YS, Wang CY, Weng SP, Yang CD. Extreme index trends of daily gridded rainfall dataset (1960-2017) in Taiwan. Terr Atmos Ocean Sci. 2022;33:8. doi:10.1007/s44195-022-00009-z.
7. Martinez-Villalobos C, Neelin JD, Pendergrass AG. Metrics for evaluating CMIP6 representation of daily precipitation probability distributions. J Clim. 2022;35:5719-5743. doi:10.1175/JCLI-D-21-0617.1.
8. Cannon AJ, Sobie SR, Murdock TQ. Bias correction of GCM precipitation by quantile mapping: how well do methods preserve changes in quantiles and extremes? J Clim. 2015;28:6938-6959. doi:10.1175/JCLI-D-14-00754.1.
9. Taylor KE. Summarizing multiple aspects of model performance in a single diagram. J Geophys Res Atmos. 2001;106:7183-7192. doi:10.1029/2000JD900719.
10. Gupta HV, Kling H, Yilmaz KK, Martinez GF. Decomposition of the mean squared error and NSE performance criteria: implications for improving hydrological modelling. J Hydrol. 2009;377:80-91. doi:10.1016/j.jhydrol.2009.08.003.
11. Knutti R, Sedláček J, Sanderson BM, Lorenz R, Fischer EM, Eyring V. A climate model projection weighting scheme accounting for performance and interdependence. Geophys Res Lett. 2017;44:1909-1918. doi:10.1002/2016GL072012.
12. Supharatid S, Aribarg T, Nafung J. Bias-corrected CMIP6 climate model projection over Southeast Asia. Theor Appl Climatol. 2022;147:669-690. doi:10.1007/s00704-021-03844-1.
13. Tangang F, Santisirisomboon J, Juneng L, Salimun E, Chung JX, Supari, et al. Projected future changes in mean precipitation over Thailand based on multi-model regional climate simulations of CORDEX Southeast Asia. Int J Climatol. 2019;39:5413-5436. doi:10.1002/joc.6163.
14. Moazzam MFU, Lee BG, Rahman G, Waqas T. Spatial rainfall variability and an increasing threat of drought, according to climate change in Uttaradit Province, Thailand. Atmos Clim Sci. 2020;10:357-371. doi:10.4236/acs.2020.103020.
15. de Oliveira-Júnior JF, Mendes D, Porto HD, Cardoso KRA, Ferreira Neto JA, da Silva EBC, et al. Analysis of drought and extreme precipitation events in Thailand: trends, climate modeling, and implications for climate change adaptation. Sci Rep. 2025;15:4501. doi:10.1038/s41598-025-86826-x.
16. Leerach K, Iamchuen N, Thanawong K, Busababodhin P, Kirtsaeng S, Pimonsree S. Meso-scale spatiotemporal analysis of future drought characteristics in Northern Thailand under climate change and variability. Theor Appl Climatol. 2025;156:439. doi:10.1007/s00704-025-05662-1.
17. Sittichok K, Kuntiyawichai K, Narudeesri-utai R. Extreme rainfall trends and return periods under CMIP6 scenarios in Southern Thailand. Water Sci. 2026;40:51. doi:10.1007/s44533-026-00050-8.
18. Hamed KH, Rao AR. A modified Mann-Kendall trend test for autocorrelated data. J Hydrol. 1998;204:182-196. doi:10.1016/S0022-1694(97)00125-X.
19. Yue S, Pilon P, Phinney B, Cavadias G. The influence of autocorrelation on the ability to detect trend in hydrological series. Hydrol Process. 2002;16:1807-1829. doi:10.1002/hyp.1095.
20. Government of Thailand. Thailand's National Adaptation Plan. Bangkok: Department of Climate Change and Environment; 2024. Available from: https://unfccc.int/documents/638001.
