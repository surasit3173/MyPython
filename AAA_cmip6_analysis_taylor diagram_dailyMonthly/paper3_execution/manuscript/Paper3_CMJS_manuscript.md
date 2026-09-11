# ENSO-Conditioned Seasonal Rainfall Extremes and Signal Preservation after Cross-Fitted Quantile Delta Mapping over Uttaradit, Thailand

Surasit Punyawansiri<sup>1,*</sup>

<sup>1</sup>Office of Water Management and Hydrology, Royal Irrigation Department, Dusit, Bangkok 10300, Thailand

<sup>*</sup>Corresponding author: Surasit.ku@ku.th

## Abstract

Bias adjustment is commonly assumed to retain physically meaningful climate variability, but this assumption is rarely tested for El Niño–Southern Oscillation (ENSO) signals at the daily station scale. We quantified ENSO-conditioned rainfall over Uttaradit, northern Thailand, and tested whether blocked cross-fitted quantile delta mapping (QDM) preserved the historical ENSO response of seven CMIP6 models. Daily rainfall at 13 gauges and exact-member model simulations were analysed for 1981–2014. Observed seasons were classified from a frozen NOAA CPC ERSSTv6 Oceanic Niño Index; every model was classified from its own detrended Niño-3.4 sea-surface-temperature anomaly. Persistent episodes required at least five overlapping three-month windows, and seasons were assigned only by strict majority. Four pre-specified endpoints were seasonal precipitation total (PRCPTOT), wet-day frequency, maximum one-day rainfall (Rx1day), and maximum consecutive dry days (CDD). Inference resampled management-season climate years rather than days or stations. Observations suggested drier El Niño conditions, including rainy-season PRCPTOT −7.2% (95% CI −18.8 to 4.4), rainy-season Rx1day −24.3% (−40.1 to 3.0), and hot/dry-season PRCPTOT −28.7% (−55.5 to 6.1), while La Niña increased hot/dry wet-day frequency by 33.0% (0.0 to 53.1). None of the 16 observed phase–metric tests survived Benjamini–Hochberg adjustment (minimum q=0.433), and no neutral-centred asymmetry test was supported. Across model-ensemble responses, QDM preserved only 2 of 16 signals, attenuated 4, amplified 3, reversed 1, and left 6 indeterminate because the raw response was near zero. The hot/dry El Niño PRCPTOT response reversed from −10.4% raw to +14.4% after QDM, compared with −28.7% observed. Thus, marginal bias correction did not guarantee preservation of ENSO-conditioned rainfall occurrence, extremes, or persistence. Event-level uncertainty and explicit signal-preservation diagnostics should accompany bias-adjusted hydroclimate applications.

**Keywords:** bias adjustment; CMIP6; El Niño–Southern Oscillation; rainfall extremes; quantile delta mapping; Thailand

## 1. Introduction

El Niño–Southern Oscillation (ENSO) reorganises tropical circulation and affects seasonal rainfall across Southeast Asia. Thailand commonly experiences rainfall deficits during El Niño and wetter conditions during La Niña, although the magnitude and timing depend on region and season [1–4]. Recent national analyses based on gridded reanalysis confirm this broad contrast, but local water management depends on daily station rainfall, dry-spell persistence, and short-duration extremes that monthly national averages cannot resolve [4]. Northern Thailand is especially sensitive because water supply, flood control, and rain-fed agriculture share a strongly seasonal monsoon resource.

Global climate models provide physically consistent ENSO and rainfall simulations, yet their coarse grids and precipitation biases limit direct station-scale use [5]. Quantile mapping is therefore widely used to align simulated and observed marginal distributions [6,7]. Quantile delta mapping (QDM) was designed to preserve simulated changes in quantiles while correcting historical bias [6]. That property, however, concerns distributional change between periods; it does not ensure that a circulation-conditioned contrast such as El Niño minus Neutral will survive adjustment. The risk is greater for wet-day occurrence and sequence-dependent metrics because a univariate mapping changes magnitudes but does not reconstruct the model's temporal ordering [7,8]. In-sample calibration can further conceal instability.

Three gaps motivate this study. First, observational ENSO analyses in Thailand have generally used national or regional monthly data rather than a dense daily gauge network [1–4]. Second, model evaluation often assigns observed ENSO years to all simulations. Free-running historical models do not reproduce the observed chronology, so their rainfall responses must be conditioned on ENSO diagnosed from each model's own sea-surface temperatures. Third, few bias-adjustment studies evaluate whether an ENSO-conditioned response is preserved out of sample, and fewer still respect the event-level sampling unit.

We address these gaps for Uttaradit Province using 13 rain gauges, seven CMIP6 models, and a fully blocked cross-fitted QDM experiment over 1981–2014. The objectives were to: (i) estimate observed El Niño and La Niña responses relative to Neutral for four management-relevant rainfall endpoints; (ii) compare raw and QDM-adjusted model-ensemble responses using model-specific ENSO classifications; and (iii) distinguish the directional phase contrast from true neutral-centred asymmetry. The central hypothesis was not that QDM would reproduce the observed ENSO response, but that its preservation behaviour could be measured transparently.

## 2. Materials and Methods

### 2.1 Study area and data

Uttaradit lies in monsoon-dominated northern Thailand. Thirteen daily rainfall gauges (station codes 351001–351012 and 351201) span 17.23–18.02°N, 100.05–101.07°E and 54.6–427.9 m above mean sea level. The analysis period was 1 January 1981–31 December 2014. The rainy management season comprised May–October and was labelled by calendar year. The hot/dry season comprised November–April and was labelled by its November start year; consequently, complete seasons extended from 1981/82 through 2013/14.

Daily historical precipitation was used from seven CMIP6 models: ACCESS-ESM1-5, CanESM5, CESM2, EC-Earth3, FGOALS-g3, MIROC6, and MRI-ESM2-0 [5,9–15]. One ensemble member was retained per model and matched exactly between precipitation and sea-surface-temperature data. Gauge extraction can duplicate a coarse grid cell; therefore, station series sharing an identical raw precipitation time series were collapsed to a unique grid signature before model aggregation. Models contributed one value each to the ensemble regardless of native resolution.

Observed ENSO status came from the NOAA Climate Prediction Center historical Oceanic Niño Index (ONI) table based on ERSSTv6, frozen on 1 September 2026 [16]. For each GCM, monthly `tos` from the exact historical member was area-weighted over Niño-3.4 (5°S–5°N, 170°W–120°W). Anomalies used the model's 1981–2010 monthly climatology, a centred linear detrend, and a centred three-month running mean.

### 2.2 Quality control and common calendar

Observed zero rainfall was screened on the native Gregorian calendar before leap-day removal. A zero month was flagged as probable missing only when at least two pre-specified indicators supported the diagnosis, including neighbour disagreement, an anomalously long zero run, or an annual rainfall deficit. Only probable-missing values were set to missing; confirmed dry and uncertain zeros were retained. This classified 43 station-months as probable missing and removed 1,308 daily values. All series were then placed on a common 365-day calendar by dropping 29 February without inserting synthetic days. A station-season entered a metric only if its expected daily coverage was complete after quality control.

### 2.3 ENSO episodes and management-season classification

El Niño and La Niña episodes required ONI or model Niño-3.4 anomalies of at least +0.5°C or at most −0.5°C, respectively, for five or more overlapping three-month windows [16]. For each management season, all overlapping persistent windows were counted. A season was El Niño or La Niña only when that phase had a strict majority; Neutral required no persistent episode. Ties, mixed-phase seasons, and seasons lacking a strict majority were labelled transition/unclassified and excluded from phase contrasts. This same algorithm was applied to observations and each model, while the underlying index remained source-specific.

### 2.4 Blocked cross-fitted QDM

Multiplicative QDM with wet-day frequency adaptation was fitted separately for each station/grid signature and calendar month [6]. Seven climate-year blocks were held out in turn: 1981–1985, 1986–1990, 1991–1995, 1996–2000, 2001–2005, 2006–2010, and 2011–2014. Observations from the target block were never used in its mapping. Wet-day quantiles used the ≥1 mm threshold, Hazen mid-ranks, linear interpolation, and constant-ratio extrapolation. At least 30 wet days were required for calibration. If a single month was sparse, only calibration samples were pooled from that month and its two adjacent months; the corrected target remained in its original month. This pre-specified fallback was used in 574 of 7,644 fits (7.5%).

### 2.5 Rainfall endpoints and hierarchy

Four primary endpoints were fixed before analysis: PRCPTOT, the total from days with rainfall ≥1 mm; wet-day frequency, the percentage of season days ≥1 mm; Rx1day, the seasonal maximum daily rainfall; and CDD, the longest run of days below 1 mm [17]. Secondary indices were retained only in the supplementary workbook.

Aggregation followed the data-generating hierarchy: daily values → management-season climate year → station → unique raw-grid signature → model → ensemble. Within each source, the phase response was

\[R_p=100(M_p-M_N)/M_N,\]

where \(M_p\) and \(M_N\) are phase and Neutral means within a station or unique grid signature, followed by regional and ensemble medians. At least three phase seasons and three Neutral seasons were required. The observed analysis used the median station response. Model responses first collapsed duplicated grid signatures and then used the median across models.

### 2.6 Inference, asymmetry, and preservation

Uncertainty was estimated with 5,000 bootstrap repetitions and 95% percentile intervals. Permutation p-values used 4,999 label permutations. Resampling and permutation occurred at the management-season climate-year level; model ensembles resampled events independently within model. The 16 phase-by-season-by-metric tests were adjusted by the Benjamini–Hochberg procedure. Effect sizes and intervals are emphasised because phase samples were small.

Two quantities were kept separate. The phase contrast, \(A_{La}-A_{El}\), describes the difference between La Niña and El Niño responses. True neutral-centred asymmetry, \(A_{La}+A_{El}\), tests whether equal and opposite responses cancel around Neutral. A large phase contrast alone is not evidence of asymmetry.

QDM signal preservation was classified from paired-model ensemble responses. A raw response with magnitude <5 percentage points was indeterminate. Otherwise, a sign reversal was `reversed`; a magnitude ratio |QDM/raw| of 0.8–1.2 was `preserved`, <0.8 was `attenuated`, and >1.2 was `amplified`. Directional agreement with observations and paired-model sign retention were reported separately.

All processing was scripted in Python. Acceptance gates verified frozen ENSO provenance, calendar completeness, source-specific classification, seven-model/13-gauge coverage, absence of target-fold leakage, paired phase responses, separation of contrast and asymmetry, and event-level inference.

## 3. Results and Discussion

### 3.1 ENSO samples and observed response

The observed rainy-season sample comprised 6 El Niño, 8 Neutral, 7 La Niña, and 13 transition/unclassified seasons; the corresponding hot/dry counts were 8, 8, 12, and 5 (Figure 1; Table 1). Model-specific classification produced appreciably different sample counts, as expected for free-running simulations. One ACCESS-ESM1-5 rainy-season La Niña response failed the minimum sample gate, leaving six paired models for that contrast; other ensemble contrasts retained seven models.

Observed point estimates were broadly consistent with rainfall suppression during El Niño but remained uncertain (Figure 2; Table 2). Rainy-season El Niño responses were −7.2% for PRCPTOT and −24.3% for Rx1day, while CDD increased by 17.9%. Hot/dry El Niño PRCPTOT was −28.7% and Rx1day was −27.2%. La Niña increased hot/dry wet-day frequency by 33.0%, whose unadjusted permutation p-value was 0.0278, but the multiple-testing adjusted q-value was 0.433. All other observed intervals also included zero, and none of the 16 observed primary tests survived adjustment (minimum q=0.433). These results align directionally with national studies [1–4] but show that local daily responses are less certain than a simple wet-La Niña/dry-El Niño narrative suggests.

The wide intervals are not a computational defect: after persistent-episode classification and transition exclusion, only 6–12 observed event seasons were available per phase. Treating stations or daily values as independent replicates would have generated artificially narrow intervals. The event-level design therefore gives a more conservative and hydrologically interpretable uncertainty statement.

### 3.2 Raw versus cross-fitted QDM ENSO signals

Bias adjustment substantially altered several ENSO responses (Figure 3; Table 2). Of 16 model-ensemble phase–metric signals, only rainy PRCPTOT under El Niño and rainy CDD under El Niño met the preservation criterion. Four signals were attenuated, three amplified, one reversed, and six were indeterminate because the raw response was within ±5 percentage points.

The clearest failure occurred for hot/dry El Niño PRCPTOT: the raw ensemble response of −10.4% agreed in sign with the observed −28.7%, whereas QDM produced +14.4%. Model directional agreement with observations fell from 0.86 to 0.43. For rainy El Niño Rx1day, the raw −12.7% response was attenuated to −5.7%, both smaller than the observed −24.3%. Under rainy La Niña, both raw and QDM ensemble responses for PRCPTOT were negative (−10.0% and −15.0%), opposite to the observed +2.7%; only one of six contributing models agreed with the observed direction.

These changes are compatible with the mechanics of univariate QDM. The mapping is fitted to calendar-month marginal distributions without conditioning on ENSO. Cross-fitting prevents the held-out observed events from directly shaping their correction, but does not impose a physical relationship between Niño-3.4 variability and local rainfall. Frequency adaptation and month-specific quantiles can also change event composites when ENSO phases sample different parts of the precipitation distribution. Sequence-dependent CDD is especially vulnerable because rank-based correction does not reorder wet and dry days [7,8].

### 3.3 Phase contrast and neutral-centred asymmetry

Observed La Niña-minus-El Niño phase contrasts were sizeable for some hot/dry metrics: +46.0 percentage points for PRCPTOT and +43.8 points for wet-day frequency (Figure 4). These contrasts indicate separation between phase composites, but their neutral-centred sums were −15.1 and +15.5 points, respectively. Across all eight observed season–metric combinations, true asymmetry q-values were ≥0.781. The data therefore did not support a claim that El Niño and La Niña responses were unequal around Neutral.

QDM could change the asymmetry quantity even when paired-model signs appeared stable. For hot/dry PRCPTOT, neutral-centred asymmetry shifted from −8.3% raw to +52.7% after adjustment. This result should not be interpreted as evidence that QDM created a physical nonlinear ENSO response; rather, it demonstrates that a marginal correction can materially modify a conditioned composite. The distinction between phase contrast and asymmetry avoids a common interpretive error.

### 3.4 Implications, strengths, and limitations

The practical implication is that bias-adjusted rainfall should not automatically be treated as reliable for ENSO-conditioned planning. A correction may improve the unconditional distribution yet distort the sign or magnitude of the seasonal teleconnection used for reservoir operation or drought preparedness. A minimum workflow should therefore report raw, corrected, and observed phase responses together; preserve the model-specific ENSO chronology; and test occurrence, intensity, and persistence endpoints separately.

The study's main strengths are source-specific ENSO diagnosis, blocked cross-fitting, explicit raw-grid deduplication, a fixed hierarchy, event-level resampling, and a reproducible acceptance audit. The analysis also avoids inferring asymmetry from a phase difference alone. Limitations remain. Thirty-four years yield few persistent events, so the study is powered for effect-size estimation rather than definitive detection. Each GCM contributes one historical member; internal variability is therefore not separated from structural model differences. The seven-model ensemble is not an independent random sample of all plausible models. The gauge network is confined to one province, and QDM is univariate and precipitation-only. Finally, the observed zero-screening rules reduce obvious missing-data contamination but cannot recover unrecorded rainfall.

Future work should add initial-condition ensembles, circulation diagnostics, and multivariate or weather-state-conditioned corrections. Pre-registered comparisons with occurrence models or stochastic weather generators would clarify whether sequence-dependent ENSO signals can be improved without sacrificing marginal performance. Longer records could also distinguish season timing and ENSO intensity while retaining event-level inference.

## 4. Conclusions

Daily observations over Uttaradit showed directionally drier El Niño seasons and a wetter hot/dry La Niña wet-day response, but all primary phase effects were uncertain after multiplicity adjustment. Blocked cross-fitted QDM did not reliably preserve model ENSO signals: only 2 of 16 ensemble responses were preserved, while one reversed and most others were attenuated, amplified, or indeterminate. No neutral-centred asymmetry was supported. These findings do not imply that QDM is generally unsuitable; they show that marginal distributional correction and teleconnection preservation are distinct validation targets. ENSO-sensitive applications should retain source-specific event chronology, use out-of-sample correction, resample at the event level, and audit conditioned signals before operational interpretation.

## Acknowledgements

The author thanks the Royal Irrigation Department and the Thai Meteorological Department for access to the rain-gauge records, the World Climate Research Programme for coordinating CMIP6, and the modelling groups for producing and making their output available.

## Author Contributions

S. Punyawansiri: Conceptualization, methodology, software, formal analysis, data curation, validation, visualization, writing—original draft, and writing—review and editing.

## Data and Code Availability

The frozen analysis package contains configuration, source manifests with checksums, tests, the executable notebook, numerical outputs, figures, and supplementary tables and is available from the corresponding author upon reasonable request. Redistribution of station observations remains subject to the data providers' terms. CMIP6 model data are available through the Earth System Grid Federation; the NOAA CPC ONI source and capture metadata are recorded in the package.

## Ethical Approval

Not applicable. The study used meteorological observations and publicly archived climate-model output and involved no human participants or animals.

## Declaration of Generative AI and AI-Assisted Technologies

During preparation, the author used a generative AI assistant for code review, statistical verification, figure and document generation, and language editing. The author reviewed the analyses and text and takes responsibility for the submitted content.

## Conflict of Interest Statement

The author declares that there is no conflict of interest.

## References

[1] Singhrattna N., Rajagopalan B., Kumar K.K. and Clark M., Interannual and interdecadal variability of Thailand summer monsoon season. *J. Climate*, 2005; **18**: 1697–1708. DOI 10.1175/JCLI3364.1.

[2] Limsakul A. and Singhruck P., Long-term trends and variability of total and extreme precipitation in Thailand. *Atmos. Res.*, 2016; **169**: 301–317. DOI 10.1016/j.atmosres.2015.10.015.

[3] Räsänen T.A., Lindgren V., Guillaume J.H.A., Buckley B.M. and Kummu M., On the spatial and temporal variability of ENSO precipitation and drought teleconnection in mainland Southeast Asia. *Clim. Past*, 2016; **12**: 1889–1905. DOI 10.5194/cp-12-1889-2016.

[4] Chanalert W., Wongsai N., Wongsai S. and Komontree P., Seasonal rainfall variability in Thailand: Long-term trends and regional patterns from ERA5 data. *Chiang Mai J. Sci.*, 2026; **53**(4): e2026065. DOI 10.12982/CMJS.2026.065.

[5] Eyring V., Bony S., Meehl G.A., Senior C.A., Stevens B., Stouffer R.J. and Taylor K.E., Overview of the Coupled Model Intercomparison Project Phase 6 (CMIP6) experimental design and organization. *Geosci. Model Dev.*, 2016; **9**: 1937–1958. DOI 10.5194/gmd-9-1937-2016.

[6] Cannon A.J., Sobie S.R. and Murdock T.Q., Bias correction of GCM precipitation by quantile mapping: How well do methods preserve changes in quantiles and extremes? *J. Climate*, 2015; **28**: 6938–6959. DOI 10.1175/JCLI-D-14-00754.1.

[7] Maraun D., Bias correcting climate change simulations: A critical review. *Curr. Clim. Change Rep.*, 2016; **2**: 211–220. DOI 10.1007/s40641-016-0050-x.

[8] Addor N., Rohrer M., Furrer R. and Seibert J., Propagation of biases in climate models from the synoptic to the regional scale: Implications for bias adjustment. *J. Geophys. Res. Atmos.*, 2016; **121**: 2075–2089. DOI 10.1002/2015JD024040.

[9] Ziehn T., Chamberlain M.A., Law R.M., Lenton A., Bodman R.W., Dix M., et al., The Australian Earth System Model: ACCESS-ESM1.5. *J. South. Hemisph. Earth Syst. Sci.*, 2020; **70**: 193–214. DOI 10.1071/ES19035.

[10] Swart N.C., Cole J.N.S., Kharin V.V., Lazare M., Scinocca J.F., Gillett N.P., et al., The Canadian Earth System Model version 5 (CanESM5.0.3). *Geosci. Model Dev.*, 2019; **12**: 4823–4873. DOI 10.5194/gmd-12-4823-2019.

[11] Danabasoglu G., Lamarque J.-F., Bacmeister J., Bailey D.A., DuVivier A.K., Edwards J., et al., The Community Earth System Model version 2 (CESM2). *J. Adv. Model Earth Syst.*, 2020; **12**: e2019MS001916. DOI 10.1029/2019MS001916.

[12] Döscher R., Acosta M., Alessandri A., Anthoni P., Arneth A., Arsouze T., et al., The EC-Earth3 Earth system model for the Coupled Model Intercomparison Project 6. *Geosci. Model Dev.*, 2022; **15**: 2973–3020. DOI 10.5194/gmd-15-2973-2022.

[13] Li L., Yu Y., Tang Y., Lin P., Xie J., Song M., et al., The Flexible Global Ocean–Atmosphere–Land System Model grid-point version 3 (FGOALS-g3): Description and evaluation. *J. Adv. Model Earth Syst.*, 2020; **12**: e2019MS002012. DOI 10.1029/2019MS002012.

[14] Tatebe H., Ogura T., Nitta T., Komuro Y., Ogochi K., Takemura T., et al., Description and basic evaluation of simulated mean state, internal variability, and climate sensitivity in MIROC6. *Geosci. Model Dev.*, 2019; **12**: 2727–2765. DOI 10.5194/gmd-12-2727-2019.

[15] Yukimoto S., Kawai H., Koshiro T., Oshima N., Yoshida K., Urakawa S., et al., The Meteorological Research Institute Earth System Model version 2.0, MRI-ESM2.0. *J. Meteorol. Soc. Jpn.*, 2019; **97**: 931–965. DOI 10.2151/jmsj.2019-051.

[16] National Oceanic and Atmospheric Administration Climate Prediction Center, Cold & Warm Episodes by Season: Historical Oceanic Niño Index, ERSSTv6; Available at: https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v6/ (accessed 1 September 2026).

[17] Zhang X., Alexander L., Hegerl G.C., Jones P., Tank A.K., Peterson T.C., Trewin B. and Zwiers F.W., Indices for monitoring changes in extremes based on daily temperature and precipitation data. *WIREs Clim. Change*, 2011; **2**: 851–870. DOI 10.1002/wcc.147.

---

## Tables

**Table 1.** ENSO management-season sample sizes. Model ranges use each GCM's exact-member Niño-3.4 classification.

| Season | Complete seasons | Observed El Niño | Model range | Observed Neutral | Model range | Observed La Niña | Model range | Transition/unclassified |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Rainy (May–Oct) | 34 | 6 | 4–12 | 8 | 3–13 | 7 | 2–12 | 13 |
| Hot/dry (Nov–Apr) | 33 | 8 | 6–14 | 8 | 4–12 | 12 | 5–15 | 5 |

**Table 2.** Observed, raw-model, and cross-fitted-QDM ensemble response relative to Neutral (%; 95% bootstrap CI). BH q is shown for the observed response.

| Season | Metric | Phase | Observed response [95% CI] | BH q | Raw ensemble | QDM ensemble |
|---|---|---|---:|---:|---:|---:|
| Rainy | PRCPTOT | El Niño | −7.2 [−18.8, 4.4] | 0.471 | −12.2 [−23.8, 1.0] | −14.5 [−25.1, −1.4] |
| Rainy | PRCPTOT | La Niña | 2.7 [−10.2, 17.3] | 0.790 | −10.0 [−20.0, 3.0] | −15.0 [−26.3, −1.1] |
| Rainy | Wet-day frequency | El Niño | −0.1 [−12.3, 2.8] | 0.980 | −4.4 [−10.8, 3.2] | −7.0 [−12.4, −1.7] |
| Rainy | Wet-day frequency | La Niña | −2.4 [−9.6, 6.3] | 0.647 | −6.8 [−11.8, 0.3] | −4.7 [−8.2, −0.8] |
| Rainy | Rx1day | El Niño | −24.3 [−40.1, 3.0] | 0.433 | −12.7 [−32.3, 2.7] | −5.7 [−35.4, 9.7] |
| Rainy | Rx1day | La Niña | 0.5 [−26.8, 35.8] | 0.980 | −12.9 [−28.2, 4.6] | −28.3 [−41.9, 0.5] |
| Rainy | CDD | El Niño | 17.9 [−6.7, 41.0] | 0.433 | 13.1 [−2.0, 41.0] | 11.9 [−4.1, 25.3] |
| Rainy | CDD | La Niña | −5.8 [−19.0, 14.3] | 0.711 | 16.2 [4.0, 45.6] | 3.4 [−5.1, 21.9] |
| Hot/dry | PRCPTOT | El Niño | −28.7 [−55.5, 6.1] | 0.433 | −10.4 [−27.8, 7.2] | 14.4 [−28.6, 42.9] |
| Hot/dry | PRCPTOT | La Niña | 13.3 [−15.6, 58.0] | 0.709 | −0.4 [−13.9, 29.4] | 20.3 [−16.6, 68.7] |
| Hot/dry | Wet-day frequency | El Niño | −10.4 [−34.7, 18.1] | 0.711 | −4.8 [−14.0, 2.5] | −1.7 [−17.6, 11.7] |
| Hot/dry | Wet-day frequency | La Niña | 33.0 [0.0, 53.1] | 0.433 | 4.7 [−6.3, 12.6] | 11.5 [−2.2, 32.3] |
| Hot/dry | Rx1day | El Niño | −27.2 [−48.2, 4.2] | 0.433 | −17.1 [−27.6, 18.3] | −2.1 [−28.5, 62.6] |
| Hot/dry | Rx1day | La Niña | −12.6 [−29.1, 29.3] | 0.681 | 6.2 [−21.6, 35.0] | 23.0 [−24.3, 80.7] |
| Hot/dry | CDD | El Niño | −9.6 [−27.9, 15.5] | 0.711 | 4.8 [−11.2, 25.3] | 13.3 [−2.8, 29.3] |
| Hot/dry | CDD | La Niña | −18.5 [−36.9, 9.2] | 0.433 | −3.9 [−17.4, 6.2] | 0.6 [−14.8, 17.9] |

**Table 3.** Cross-fitted QDM signal-preservation audit. Values in parentheses are QDM minus raw ensemble responses (percentage points); asymmetry is the neutral-centred sum.

| Season | Metric | El Niño category (shift) | La Niña category (shift) | Observed asymmetry | Raw asymmetry | QDM asymmetry |
|---|---|---|---|---:|---:|---:|
| Rainy | PRCPTOT | Preserved (−2.3) | Amplified (−5.0) | −3.5 | −23.4 | −28.0 |
| Rainy | Wet-day frequency | Indeterminate (−2.6) | Attenuated (+2.1) | −6.1 | −12.2 | −10.6 |
| Rainy | Rx1day | Attenuated (+7.1) | Amplified (−15.4) | −23.0 | −26.4 | −34.6 |
| Rainy | CDD | Preserved (−1.1) | Attenuated (−12.8) | 8.8 | 22.8 | 7.6 |
| Hot/dry | PRCPTOT | Reversed (+24.8) | Indeterminate (+20.7) | −15.1 | −8.3 | 52.7 |
| Hot/dry | Wet-day frequency | Indeterminate (+3.1) | Indeterminate (+6.7) | 15.5 | 0.4 | 8.8 |
| Hot/dry | Rx1day | Attenuated (+15.0) | Amplified (+16.8) | −23.9 | 15.7 | 20.9 |
| Hot/dry | CDD | Indeterminate (+8.4) | Indeterminate (+4.4) | −24.4 | 1.0 | 6.4 |

## Figure Captions

**Figure 1.** Frozen observed ONI record and management-season ENSO classification. Persistent episodes require five overlapping three-month windows at |ONI|≥0.5°C. Transition/unclassified seasons are excluded from phase composites.

**Figure 2.** Observed El Niño and La Niña responses relative to Neutral for four primary endpoints. Points are median station responses; bars are event-level 95% bootstrap intervals.

**Figure 3.** Observed, raw-model, and blocked cross-fitted-QDM ensemble responses relative to Neutral. Model ensembles use exact-member Niño-3.4 classifications and equal model weight.

**Figure 4.** QDM preservation category and neutral-centred ENSO asymmetry. The phase contrast and true asymmetry are reported as separate estimands.
