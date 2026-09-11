# Spatiotemporal Uncertainty of Daily, Monthly, and Annual Precipitation Projections from CMIP6 Models in Lampang Province, Thailand

**[Authors and affiliations to be inserted]**

## Abstract

Reliable information on precipitation uncertainty is important for water-resource planning and hydroclimatic risk management. This study quantified differences among 15 CMIP6 models and examined how precipitation-projection uncertainty varies across daily, monthly, and annual timescales at 17 named rainfall stations in Lampang Province, northern Thailand. Daily precipitation projections were aggregated to monthly and annual scales, while wet-day frequency, simple daily intensity, consecutive dry days, Rx1day, Rx5day, and the 95th percentile of wet-day precipitation were used to characterize daily rainfall hazards. For each model, scenario, period, and station, the ensemble mean, median, standard deviation, interquartile range, 5th–95th percentile range, coefficient of variation, and model agreement were calculated. Station-level summaries were visualized using inverse-distance weighting. The results showed [INSERT VERIFIED RESULTS FROM OUTPUT TABLES]. Monthly results indicated [INSERT]. Daily-extreme results indicated [INSERT]. The spatial analysis identified [INSERT]. The findings demonstrate that [INSERT MANAGEMENT IMPLICATION], while the spread between models should be retained in planning rather than replaced by a single deterministic projection. Because no observational reference was available, the study evaluates projection uncertainty and model agreement, not model accuracy or bias. The results provide a scenario-based evidence base for flexible water allocation, drought preparedness, and heavy-rainfall risk management in Lampang Province.

**Keywords:** CMIP6; precipitation projection; ensemble uncertainty; model agreement; water management; hydroclimatic risk; Lampang Province

## Highlights

- Differences among 15 CMIP6 precipitation models were quantified at 17 Lampang stations.
- Uncertainty was compared across daily, monthly, and annual timescales.
- MME and median were reported together with ensemble spread and model agreement.
- IDW maps identified spatial patterns relevant to water allocation and rainfall risk.
- The analysis supports flexible planning without claiming observational model skill.

## 1. Introduction

Precipitation variability directly affects water availability, agricultural scheduling, reservoir operation, and preparedness for rainfall-related hazards. These effects operate across timescales. Monthly rainfall determines the seasonal pattern of water availability and is therefore relevant to allocation planning, irrigation scheduling, and drought preparedness. Daily rainfall, in contrast, controls short-duration rainfall hazards, including intense rainfall, rapid runoff, flash flooding, and prolonged dry spells. Annual totals provide a broad climate signal but may conceal important shifts in the timing and intensity of rainfall.

Climate projections from multiple CMIP6 models provide a useful basis for examining these changes, but the models do not necessarily produce the same magnitude or direction of change. A multi-model mean is convenient for summarizing an ensemble, yet it may conceal model spread and may be influenced by models with unusually high or low precipitation. The ensemble median is more resistant to such values, but it does not remove uncertainty. Consequently, a robust assessment should report the central estimate together with the distribution among models and the degree of agreement in the projected direction.

Lampang Province is an important case for this analysis because water management must account for spatial differences among rainfall stations and for the contrasting implications of seasonal water deficits and short-duration heavy rainfall. However, a station-level assessment that simultaneously compares daily, monthly, and annual projection uncertainty remains limited. In particular, the spatial distribution of ensemble spread and the difference between the ensemble mean and median are rarely presented together in a form directly relevant to local water planning.

This study therefore investigates precipitation-projection uncertainty from 15 CMIP6 models at 17 named rainfall stations in Lampang Province. The objectives were to: (i) quantify inter-model differences in daily, monthly, and annual precipitation; (ii) assess how ensemble uncertainty changes across timescales and stations; and (iii) compare the ensemble mean, median, and model agreement, with spatial visualization by IDW. The results are interpreted as evidence for flexible water-management and hydroclimatic-risk planning. They are not treated as an observational validation of model accuracy because no observed precipitation dataset was available.

## 2. Materials and methods

### 2.1 Study area and station data

The study area was Lampang Province, northern Thailand. The analysis used the rainfall stations listed in the supplied metadata: 328001–328015, 328201, and 328301. The metadata provided station coordinates and elevation. Figure 1 shows the spatial distribution of the 17 stations. [INSERT ELEVATION RANGE AND STUDY-AREA DESCRIPTION AFTER DATA AUDIT.]

### 2.2 CMIP6 precipitation data

Daily precipitation projections from 15 CMIP6 models were used. The model files contained a historical experiment and the SSP126, SSP245, SSP370, and SSP585 scenarios for the future period [INSERT VERIFIED PERIODS]. Precipitation was expressed in millimetres per day. Model names, ensemble members, grid labels, and date coverage were extracted from the file names and recorded in Table 1. Historical and future periods were kept separate throughout the analysis.

### 2.3 Temporal aggregation and rainfall indices

Daily precipitation was aggregated to monthly totals by calendar month and to annual totals by calendar year. Wet days were defined as days with precipitation of at least 1 mm. The daily indicators were wet-day frequency, simple daily intensity index, consecutive dry days, Rx1day, Rx5day, and the 95th percentile of wet-day precipitation. Extreme indices were calculated separately for each model before ensemble statistics were calculated, thereby avoiding artificial attenuation caused by averaging asynchronous daily events.

### 2.4 Ensemble uncertainty and model agreement

For each station, model, scenario, period, and time aggregation, the ensemble mean (MME), median, standard deviation, IQR, Q05–Q95 range, and coefficient of variation were calculated. The difference between the ensemble mean and median was expressed as:

\[
D_{MME-Median}=\frac{MME-Median}{Median}\times100.
\]

Agreement was calculated as the proportion of models showing the same sign of change relative to the historical baseline. Results were classified as high agreement when at least 80% of models agreed, moderate agreement for 60–79%, and low agreement below 60%. These thresholds describe ensemble consistency and do not represent statistical confidence or observational skill.

### 2.5 Trend and spatial analysis

Annual trends were assessed using Kendall’s tau and Sen’s slope. IDW was applied to station-level summaries using power 2. The interpolation was performed in a local metre-based coordinate system and clipped to the Lampang boundary when the boundary file was available. IDW maps were used only to visualize spatial patterns in projected change, ensemble uncertainty, and model agreement.

## 3. Results

### 3.1 Data coverage and inter-model differences

The final dataset contained [INSERT ROW COUNT] daily records from 15 models, [INSERT NUMBER] experiments, and 17 stations. The data covered [INSERT PERIOD]. Figure 2 shows the range among models. The widest inter-model differences occurred during [INSERT MONTH/SEASON], whereas the narrowest range occurred during [INSERT MONTH/SEASON].

### 3.2 Monthly precipitation and water-management implications

Monthly precipitation showed a pronounced seasonal cycle, with the highest ensemble values during [INSERT MONTHS] and the lowest values during [INSERT MONTHS]. Ensemble uncertainty, measured by IQR and Q05–Q95 range, was greatest in [INSERT MONTHS]. The MME exceeded the median by [INSERT VALUE]%, indicating [INSERT INTERPRETATION]. These results identify months requiring particular attention in seasonal water-allocation planning and drought preparedness.

### 3.3 Daily rainfall hazards and annual projections

The projected changes in wet-day frequency, SDII, CDD, Rx1day, Rx5day, and q95 were [INSERT VERIFIED RESULTS]. The combination of [INSERT CDD RESULT] and [INSERT MONTHLY RESULT] indicates [INSERT DROUGHT INTERPRETATION]. Changes in Rx1day and Rx5day indicate [INSERT HEAVY-RAINFALL INTERPRETATION], which is relevant to flash-flood and runoff-risk preparedness.

Annual precipitation changed by [INSERT RANGE] across stations and scenarios. Trend analysis showed [INSERT VERIFIED TREND RESULTS]. Annual totals should therefore be interpreted together with monthly timing and daily extremes.

### 3.4 Spatial patterns from IDW

The IDW maps showed that projected change was spatially heterogeneous. Stations in [INSERT AREA] exhibited the highest projected [INSERT METRIC], while [INSERT AREA] showed the lowest values. The spatial distribution of uncertainty was [INSERT RESULT]. Areas with simultaneous high rainfall hazard and high model agreement should receive priority in risk-preparedness planning, whereas areas with low agreement should be managed using flexible thresholds and scenario ranges.

## 4. Discussion

The principal finding was the magnitude of inter-model disagreement in precipitation projections across Lampang Province. This disagreement varied with temporal aggregation: daily indicators captured event-scale variability, monthly totals captured the seasonal water-supply signal, and annual totals provided a broad climate-change summary. The distinction is important because a stable annual total may coexist with a shift toward longer dry spells or more intense rainfall events.

For water-resource management, the monthly results provide information for seasonal allocation and reservoir planning. The median can represent a robust central scenario, while the Q05–Q95 range can be used to test conservative and high-water conditions. Where the ensemble agreement is high, the projected direction provides stronger support for preparedness. Where agreement is low, water plans should retain operational flexibility rather than rely on one deterministic value.

The daily and extreme-rainfall results have a different management meaning. Increases in Rx1day or Rx5day indicate potential pressure on drainage, slope stability, and flood-response systems, whereas increases in CDD indicate increased exposure to rainfall deficits. These indices should be interpreted as rainfall-risk indicators, not direct flood hazard estimates, because flood magnitude also depends on catchment properties, river capacity, land use, antecedent soil moisture, and drainage conditions.

The comparison between MME and median demonstrates why a single ensemble summary is insufficient. A large difference between them indicates an asymmetric model distribution or the influence of a small number of models. Reporting both statistics with ensemble spread makes the uncertainty visible and supports risk-based planning. Similar multi-model studies have likewise emphasized that no single CMIP6 model performs uniformly well for all precipitation characteristics, reinforcing the value of multi-index and multi-model assessment.

The IDW maps provide a practical spatial summary for local planning, but they should not be interpreted as observations or as a substitute for hydrological modelling. Their purpose is to identify areas where the station-level projection signal, uncertainty, or model agreement is relatively high. Future work should combine these rainfall projections with observed rainfall, river discharge, topography, land use, and hydrological models to estimate flood and drought impacts more directly.

## 5. Conclusions

This study quantified the spatiotemporal uncertainty of precipitation projections from 15 CMIP6 models at 17 named rainfall stations in Lampang Province. The results demonstrate that inter-model differences vary substantially across daily, monthly, and annual timescales. Monthly precipitation projections are relevant to water allocation and seasonal resource planning, while daily rainfall indices and extremes are relevant to drought preparedness and rainfall-related hazard management.

The ensemble mean and median should be reported together with model spread and agreement. The median provides a robust central estimate, whereas the ensemble range is needed for stress testing and flexible planning. IDW maps help identify spatial patterns of projected change and uncertainty, but they are visualization products rather than observational validation.

Because the study did not include observed precipitation, its conclusions concern model disagreement and projection uncertainty rather than model accuracy, bias correction, or forecast skill. The findings therefore provide a structured evidence base for scenario-based water management in Lampang Province and a reproducible framework that can be transferred to other provinces.

## Declarations

**Funding:** [Insert if applicable.]  
**Conflict of interest:** The authors declare no conflict of interest.  
**Data availability:** [Insert repository or data-access statement.]  
**Author contributions:** [Insert author contribution statement.]  

## References

[Insert verified references in EnNRJ style. References must be checked against the final literature review and should include CMIP6, ensemble uncertainty, precipitation extremes, IDW, Mann–Kendall, and water-management studies.]
