# ENSO-conditioned seasonal rainfall and climate-signal preservation over Uttaradit, Thailand

## Abstract
**Background:** Quantile Delta Mapping (QDM) is widely used to correct climate model bias, but its performance in preserving conditional ENSO signals at gauge scales requires validation.
**Objectives:** Evaluate ENSO-conditioned seasonal rainfall and extremes in Uttaradit using 13 rain gauges and 7 CMIP6 models (1995–2014).
**Methods:** Seasons were classified into El Niño, Neutral, La Niña, and Transition using NOAA CPC ONI data for Rainy (May–Oct) and complete Hot/Dry (Nov–Apr cross-year) seasons. Eleven ETCCDI indices were computed for observed, raw CMIP6, and QDM-corrected precipitation.
**Results:** Observed La Niña exhibited a near-zero change in Rainy season total rainfall (PRCPTOT median anomaly -0.26% relative to Neutral), whereas Hot/Dry season PRCPTOT during El Niño decreased by 17.19%. Raw CMIP6 models produced a positive median La Niña Rainy season anomaly (2.53%). QDM bias correction preserved the directional positive response of raw models while amplifying its magnitude (QDM median 7.23%, $PE_{ENSO} = 62.17\%$), expanding the magnitude difference relative to observed station variability. Hot/Dry season PRCPTOT asymmetry ($ASYM$) was 33.10% in observations and -12.09% in QDM simulations.
**Conclusions:** QDM preserves raw CMIP6 model directional ENSO responses while adjusting marginal climatological biases, resulting in response magnitude amplification.

## 1. Introduction
Seasonal precipitation availability dictates agricultural calendars and reservoir management in northern Thailand. ENSO warm (El Niño) and cold (La Niña) phases modulate monsoon strength and interannual rainfall variability. Although Quantile Delta Mapping (QDM) effectively bias-corrects GCM daily precipitation distributions, whether QDM preserves or distorts conditional ENSO climate signals at gauge scales is a critical unresolved question.

## 2. Materials and Methods
### 2.1 Study Area and Rainfall Data
The study evaluated 13 daily rain gauges in Uttaradit province (1981–2014) and 7 CMIP6 GCMs (ACCESS-ESM1-5, CanESM5, CESM2, EC-Earth3, FGOALS-g3, MIROC6, MRI-ESM2-0) over the common overlap baseline (1995–2014).
### 2.2 Season Definitions and ENSO Classification
Two management seasons were evaluated: Rainy Season (May–October, 20 complete seasons) and Hot/Dry Season (November–April cross-year, 19 complete seasons; 2014/15 excluded due to observed daily record ending 2014-12-31). Pinned NOAA CPC ONI data (PSL mirror) classified seasons into El Niño, Neutral, La Niña, and Transition/Unclassified based on episode overlap.
### 2.3 Bias Correction & ETCCDI Metrics
QDM bias correction was applied using frozen 1981–2002 calibration parameters. Eleven core ETCCDI precipitation indices were calculated: PRCPTOT, wet-day frequency, SDII, Rx1day, Rx5day, R20mm, R50mm, R95p, R99p, CDD, and CWD. R95p and R99p were defined as the seasonal sum of precipitation on wet days ($\ge 1.0\text{ mm}$) exceeding station-specific 95th and 99th percentile thresholds calculated over observed 1981–2014 wet days. Fixed station-specific observed thresholds were applied identically to observed, raw, and QDM model daily precipitation.

## 3. Results
### 3.1 Observed ENSO Response
In the Rainy season, La Niña exhibited a slight decrease in PRCPTOT anomaly (-0.26% relative to Neutral). In the Hot/Dry season, El Niño suppressed PRCPTOT by 17.19%.
### 3.2 Raw vs. QDM CMIP6 Performance
Raw CMIP6 models produced a median La Niña Rainy season PRCPTOT anomaly of 2.53%. Following QDM, the response was 7.23%, yielding a signal preservation error $PE_{ENSO}$ of 62.17%. This represents directional signal preservation accompanied by magnitude amplification relative to raw model sensitivity.
### 3.3 ENSO Asymmetry and Extreme Indices
Hot/Dry season PRCPTOT asymmetry ($ASYM$) was 33.10% in observations and -12.09% in QDM CMIP6 simulations. Low-sample comparisons ($n < 3$, e.g., Rainy season El Niño with $n=2$) were classified as diagnostic.

## 4. Discussion
The findings demonstrate that QDM operates as a quantile-preserving transfer function, correcting unconditional climatological biases while preserving directional ENSO sensitivity and amplifying response magnitude.

## 5. Conclusion
QDM successfully preserves directional CMIP6 ENSO-conditioned seasonal rainfall responses in Uttaradit, while amplifying response magnitude.
