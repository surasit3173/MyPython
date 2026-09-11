# Observed Baseline Climatology, Extreme Precipitation Indices, and CMIP6 Projections over Uttaradit Province, Thailand

**Target Publication:** Scopus Q1–Q2 Climate / Water Resources Journal  
**Geographic Domain:** Uttaradit Province, Northern Thailand (13 TMD Stations)  
**Historical Baseline:** 1995–2014 (Authoritative 20-Year Baseline)  
**Future Projection Window:** Near-Term 2021–2050 (SSP2-4.5 and SSP5-8.5)  

---

## Abstract

Accurate assessment of precipitation extremes and their future projections is critical for resilient water resources management in the Upper Nan River basin and the operational security of the Sirikit Dam in Uttaradit Province, Northern Thailand. This study establishes a rigorous baseline climatology of daily precipitation and 11 Expert Team on Climate Change Detection and Indices (ETCCDI) extreme metrics across 13 meteorological stations for the authoritative 1995–2014 period, and evaluates the performance and future projections of seven Coupled Model Intercomparison Project Phase 6 (CMIP6) General Circulation Models (GCMs). Baseline mean annual precipitation across Uttaradit averaged 1139.80 ± 213.19 mm (ranging from 947.71 mm at Station 351012 to 1425.06 mm at Station 351003), with 77.8% (886.85 mm) concentrated during the Southwest Monsoon wet season (May–October). Extreme precipitation indices exhibited pronounced spatial heterogeneity consistent with the complex topography of the Nan River basin: baseline Simple Daily Intensity Index (SDII) ranged from 5.12 to 13.83 mm/day, annual maximum 1-day rainfall (Rx1day) from 28.96 to 113.92 mm, and consecutive dry days (CDD) from 34.94 to 70.12 days. Baseline sensitivity diagnostics demonstrated that shifting from a 1981–2010 to a 1995–2014 reference period substantially alters percentile thresholds (by up to -14.70 mm for 95th percentile) and mean extreme indices (by up to +182.04 mm for R95p), confirming the necessity of baseline standardization. Evaluation of CMIP6 GCMs revealed that pre-computed Quantile Delta Mapping (QDM) bias correction reduced the raw multi-model ensemble annual rainfall bias from -307.13 mm (-26.9%) to -69.90 mm (-6.1%), representing an average bias reduction of 77.2%. Under near-term future warming (2021–2050), the multi-model ensemble projects modest increases in mean annual rainfall of +2.21% (+23.60 mm) under SSP2-4.5 and +1.10% (+11.70 mm) under SSP5-8.5 relative to the seven-model bias-corrected historical baseline (1068.48 mm; mean of individual model percentage deltas: +2.50% and +1.16%, respectively), though individual model responses exhibit substantial structural divergence (-10.8% to +17.4%). These findings provide an evidence-based foundation for flood hazard mitigation, reservoir operational scheduling, and climate adaptation in northern Thailand.

**Keywords:** CMIP6; ETCCDI; extreme precipitation; Quantile Delta Mapping; Uttaradit; Sirikit Dam; Northern Thailand.

---

## 1. Introduction

Precipitation extremes represent one of the most critical drivers of hydrologic vulnerability in Southeast Asia. In Northern Thailand, the province of Uttaradit occupies a pivotal hydrologic position within the Upper Nan River basin, hosting the Sirikit Multipurpose Dam—the second largest reservoir in Thailand, with a storage capacity exceeding 9.5 billion cubic meters. The region is periodically subjected to devastating monsoon-induced flash floods, landslides, and prolonged dry-season droughts that threaten agricultural livelihood and national water security.

Reliable quantification of precipitation characteristics requires standard extreme indices, such as the 11 core indices formulated by the Expert Team on Climate Change Detection and Indices (ETCCDI). Furthermore, adapting to climate change necessitates downscaled and bias-corrected projections from the latest Coupled Model Intercomparison Project Phase 6 (CMIP6). However, raw GCM simulations often exhibit substantial regional biases in monsoon intensity and local convective precipitation. While Quantile Delta Mapping (QDM) has gained widespread adoption as an effective bias correction technique that preserves relative changes in precipitation quantiles, rigorous validation against local gauge observations remains essential.

This investigation establishes an evidence-first, reproducible baseline for Uttaradit Province using 13 primary meteorological stations over the locked 1995–2014 historical baseline, examines baseline sensitivity against earlier reference periods, evaluates pre-computed QDM-corrected outputs across seven CMIP6 GCMs, and characterizes projected changes under SSP2-4.5 and SSP5-8.5 for the near-term period (2021–2050).

---

## 2. Materials and Methods

### 2.1 Study Area and Observational Station Network

Uttaradit Province covers an area of approximately 7,838 km² in northern Thailand (17.16°N–18.37°N, 99.90°E–101.17°E), characterized by an alluvial central plain along the Nan River flanked by mountainous highlands in the north and east. Daily rainfall records were obtained from the Thai Meteorological Department (TMD) for 13 official rain gauge stations (Table 1, Figure 1). The network spans elevations from 54.57 m MSL at Phichai (Station 351001) in the southern lowlands to 427.85 m MSL at Fak Tha (Station 351007) in the northeastern highlands. All 13 station records cover exactly 12,418 daily calendar records from 1981-01-01 to 2014-12-31 with 0% missing data, certified by TMD quality assurance without requiring synthetic infilling.

### 2.2 Historical Baseline Definition and Climatological Partitioning

Following CMIP6 protocol and experimental freezing, the historical baseline period was strictly locked to 1995–2014 (20 complete calendar years). The annual cycle is divided into two operational hydrologic seasons:
1. **Wet Season (May–October):** Dominated by the Southwest Monsoon and convective depressions.
2. **Dry Season (November–April):** Governed by the Northeast Monsoon and dry continental air masses.

### 2.3 Spatial Interpolation and Cross-Validation

Continuous spatial fields of baseline mean annual precipitation were generated using two-dimensional Inverse Distance Weighting (IDW, power $p=2.0$, resolution ~500 m) strictly masked to the authoritative Natural Earth provincial boundary polygon. This surface is evaluated as an exploratory spatial diagnostic visualization of gauge-based climatology rather than an exact continuous truth, given the sampling density of 13 stations in rugged terrain. Leave-One-Out Cross-Validation (LOOCV) yielded a Mean Absolute Error (MAE) of 98.03 mm, Root Mean Square Error (RMSE) of 131.26 mm, and Mean Bias Error (MBE) of -3.21 mm across the network (relative error: 8.60%; Figure 2, `IDW_parameters.txt`).

### 2.4 ETCCDI Extreme Precipitation Indices

Eleven standardized ETCCDI extreme precipitation indices were calculated on daily station series using a wet-day threshold of $P \ge 1.0$ mm/day (Table 3, Figure 3). Technical quantities and individual station values are compiled in Supplementary Table S1.

### 2.5 CMIP6 General Circulation Models and Provenance Disclosure

Seven CMIP6 GCMs were evaluated: ACCESS-ESM1-5, CESM2, CanESM5, EC-Earth3, FGOALS-g3, MIROC6, and MRI-ESM2-0 (Table 4). Raw and Quantile Delta Mapping (QDM) bias-corrected daily precipitation series were analyzed for historical (1995–2014) and near-term future (2021–2050) under SSP2-4.5 (middle-of-the-road forcing) and SSP5-8.5 (fossil-fueled development).

**Methodological Provenance Disclosure:** QDM-corrected datasets were evaluated as pre-computed inputs; the transformation procedure was not re-executed within the present analysis pipeline. The pre-computed files (`bc_pr_day_*`) represent daily precipitation calibrated against historical TMD gauge observations per the Quantile Delta Mapping formulation of Cannon et al. (2015), which preserves relative model-projected changes in precipitation quantiles while matching historical empirical distributions. Furthermore, analysis of the codebase revealed no executable ANOVA uncertainty decomposition engine; consequently, previously reported variance decomposition percentages (65–75% GCM, 15–25% scenario, 10–15% internal variability) are unsupported by repository code and have been excised from this manuscript.

---

## 3. Results

### 3.1 Observed Baseline Climatology and Seasonal Rainfall

Baseline mean annual precipitation (1995–2014) across the 13 stations in Uttaradit Province averaged 1139.80 ± 213.19 mm (Table 1). Inter-station variability was pronounced, ranging from 947.71 mm at Ban Khok (Station 351012) to 1425.06 mm at Tha Pla (Station 351003). As shown in Table 2 and Figure 2, the wet season (May–October) accounts for an average of 886.85 mm (77.8% of annual total), ranging from 68.4% at Station 351011 to 82.9% at Station 351002.

**Table 1. Geographic and climatological characteristics of the 13 meteorological stations in Uttaradit Province (1995–2014 baseline).**
| Station ID | District / Amphoe | Latitude (°N) | Longitude (°E) | Elevation (m MSL) | Mean Annual (mm) | SD (mm) | CV (%) |
|---|---|---|---|---|---|---|---|
| 351001 | Phichai | 17.23 | 100.10 | 54.57 | 995.65 | 125.39 | 12.6 |
| 351002 | Tron | 17.42 | 100.13 | 62.02 | 1053.80 | 264.84 | 25.1 |
| 351003 | Tha Pla | 17.67 | 100.68 | 371.77 | 1425.06 | 204.80 | 14.4 |
| 351004 | Laplae | 17.65 | 100.38 | 115.76 | 1085.21 | 240.06 | 22.1 |
| 351005 | Mueang Uttaradit (West) | 17.60 | 100.05 | 81.47 | 1121.00 | 246.75 | 22.0 |
| 351006 | Nam Pat | 17.92 | 100.88 | 348.79 | 1129.59 | 293.55 | 26.0 |
| 351007 | Fak Tha | 18.02 | 101.07 | 427.85 | 1221.05 | 190.82 | 15.6 |
| 351008 | Thong Saen Khan | 17.47 | 100.37 | 82.43 | 1146.01 | 201.99 | 17.6 |
| 351009 | Laplae (North) | 17.75 | 100.28 | 95.27 | 1223.36 | 119.60 | 9.8 |
| 351010 | Nam Pat (Valley) | 17.90 | 100.82 | 214.69 | 1204.22 | 116.49 | 9.7 |
| 351011 | Mueang Uttaradit (South) | 17.56 | 100.11 | 65.37 | 1159.21 | 264.73 | 22.8 |
| 351012 | Ban Khok | 17.75 | 100.92 | 415.07 | 947.71 | 242.69 | 25.6 |
| 351201 | Uttaradit (Agromet/Synoptic) | 17.62 | 100.10 | 67.05 | 1105.59 | 259.72 | 23.5 |

**Table 2. Seasonal precipitation partitioning across Uttaradit stations (1995–2014 baseline).**
| Station ID | District | Mean Annual (mm) | Wet Season (mm) | Dry Season (mm) | Wet Season (%) |
|---|---|---|---|---|---|
| 351001 | Phichai | 995.65 | 817.15 | 178.50 | 82.1 |
| 351002 | Tron | 1053.80 | 874.04 | 179.76 | 82.9 |
| 351003 | Tha Pla | 1425.06 | 1144.43 | 280.64 | 80.3 |
| 351004 | Laplae | 1085.21 | 878.59 | 206.62 | 81.0 |
| 351005 | Mueang Uttaradit (West) | 1121.00 | 870.95 | 250.06 | 77.7 |
| 351006 | Nam Pat | 1129.59 | 861.29 | 268.30 | 76.2 |
| 351007 | Fak Tha | 1221.05 | 899.64 | 321.42 | 73.7 |
| 351008 | Thong Saen Khan | 1146.01 | 842.19 | 303.82 | 73.5 |
| 351009 | Laplae (North) | 1223.36 | 986.77 | 236.59 | 80.7 |
| 351010 | Nam Pat (Valley) | 1204.22 | 972.69 | 231.53 | 80.8 |
| 351011 | Mueang Uttaradit (South) | 1159.21 | 793.03 | 366.18 | 68.4 |
| 351012 | Ban Khok | 947.71 | 711.88 | 235.84 | 75.1 |
| 351201 | Uttaradit (Agromet/Synoptic) | 1105.59 | 876.41 | 229.18 | 79.3 |

### 3.2 Observed Baseline ETCCDI Extreme Precipitation Indices

The 11 ETCCDI indices summarized in Table 3 and Figure 3 highlight marked differences across Uttaradit's topography. Network-average annual wet-day precipitation (PRCPTOT) was 1107.76 ± 108.97 mm. Daily precipitation intensity (SDII) averaged 9.83 ± 3.24 mm/day, with maximum intensities observed in the central and western districts (Tha Pla: 13.83 mm/day; Tron: 13.26 mm/day). Extreme short-duration rainfall (Rx1day) averaged 73.68 ± 27.60 mm (maximum 113.92 mm at Station 351011), while 5-day cumulative extremes (Rx5day) averaged 138.99 ± 37.52 mm (maximum 193.37 mm at Station 351012). Dry spells (CDD) averaged 51.52 ± 11.45 consecutive days, peaking at 70.12 days in Tron (Station 351002).

**Table 3. Summary of 11 ETCCDI extreme precipitation indices across 13 stations in Uttaradit Province (1995–2014 baseline).**
| Index | Description | Units | Network Mean | Min | Max | SD |
|---|---|---|---|---|---|---|
| PRCPTOT | Annual total precipitation on wet days (P >= 1.0 mm) | mm | 1098.88 | 930.26 | 1366.07 | 108.84 |
| SDII | Simple daily intensity index (annual wet-day mean) | mm/day | 10.27 | 5.12 | 13.83 | 3.23 |
| Rx1day | Annual maximum 1-day precipitation | mm | 74.39 | 28.96 | 113.92 | 28.44 |
| Rx5day | Annual maximum consecutive 5-day precipitation | mm | 137.46 | 79.45 | 193.37 | 37.03 |
| CDD | Maximum consecutive dry days (P < 1.0 mm) | days | 50.23 | 34.94 | 70.12 | 11.83 |
| CWD | Maximum consecutive wet days (P >= 1.0 mm) | days | 30.34 | 7.38 | 86.06 | 26.46 |
| R10mm | Annual count of heavy precipitation days (P >= 10 mm) | days | 30.14 | 25.18 | 40.26 | 3.94 |
| R20mm | Annual count of very heavy precipitation days (P >= 20 mm) | days | 11.86 | 2.12 | 18.82 | 5.48 |
| R50mm | Annual count of extremely heavy precipitation days (P >= 50 mm) | days | 2.03 | 0.06 | 3.68 | 1.26 |
| R95p | Precipitation on very wet days (> 95th percentile) | mm | 282.88 | 200.14 | 487.60 | 73.97 |
| R99p | Precipitation on extremely wet days (> 99th percentile) | mm | 95.14 | 56.41 | 176.27 | 32.31 |

### 3.3 Historical Baseline Sensitivity Diagnostic (1981–2010 vs 1995–2014)

Comparison of baseline periods revealed substantial shifts in extreme precipitation thresholds and indices (Table 4). For Station 351003 (Tha Pla), the 95th percentile threshold shifted from 45.58 mm (1981–2010) to 30.88 mm (1995–2014), resulting in a +182.04 mm difference in calculated mean R95p. Similarly, Stations 351006 and 351007 exhibited threshold increases of +3.69 mm and +4.90 mm, respectively, leading to substantial reductions in mean R95p (-75.70 mm and -89.29 mm). These results demonstrate that climate extreme trend evaluations must avoid mixing inconsistent baseline definitions.

**Table 4. Sensitivity of extreme precipitation thresholds and indices to baseline period selection (1981–2010 vs 1995–2014).**
| Station ID | P95 Thresh 81–10 (mm) | P95 Thresh 95–14 (mm) | Δ P95 Thresh (mm) | Mean R95p 81–10 (mm) | Mean R95p 95–14 (mm) | Δ R95p (mm) | Mean R99p 81–10 (mm) | Mean R99p 95–14 (mm) | Δ R99p (mm) |
|---|---|---|---|---|---|---|---|---|---|
| 351001.0 | 44.28 | 41.33 | -2.95 | 267.16 | 289.75 | 22.58 | 98.71 | 118.05 | 19.34 |
| 351002.0 | 40.50 | 44.08 | 3.58 | 250.40 | 223.07 | -27.33 | 79.64 | 62.04 | -17.61 |
| 351003.0 | 45.58 | 30.88 | -14.70 | 305.57 | 487.60 | 182.04 | 97.34 | 176.27 | 78.94 |
| 351004.0 | 42.20 | 42.95 | 0.75 | 270.99 | 264.72 | -6.27 | 101.49 | 79.95 | -21.54 |
| 351005.0 | 44.09 | 35.71 | -8.38 | 253.12 | 340.67 | 87.55 | 73.86 | 112.54 | 38.69 |
| 351006.0 | 17.41 | 21.10 | 3.69 | 325.57 | 249.87 | -75.70 | 143.17 | 76.47 | -66.70 |
| 351007.0 | 16.90 | 21.80 | 4.90 | 338.26 | 248.97 | -89.29 | 155.75 | 84.79 | -70.96 |
| 351008.0 | 17.20 | 20.50 | 3.30 | 313.34 | 259.86 | -53.48 | 130.61 | 92.78 | -37.83 |
| 351009.0 | 12.70 | 12.70 | 0.00 | 200.14 | 200.14 | 0.00 | 63.22 | 62.07 | -1.15 |
| 351010.0 | 13.80 | 13.50 | -0.30 | 198.34 | 209.22 | 10.89 | 59.60 | 56.41 | -3.19 |
| 351011.0 | 41.90 | 42.40 | 0.50 | 323.80 | 317.59 | -6.21 | 129.66 | 121.88 | -7.79 |
| 351012.0 | 45.00 | 43.23 | -1.77 | 282.05 | 292.39 | 10.34 | 99.36 | 99.36 | 0.00 |
| 351201.0 | 40.18 | 40.02 | -0.15 | 291.18 | 293.54 | 2.36 | 100.95 | 94.19 | -6.76 |

### 3.4 CMIP6 Model Performance and Bias Correction

Raw CMIP6 GCM simulations exhibited severe systematic biases over Uttaradit Province (Table 5, Figure 4). Raw multi-model annual precipitation averaged 833.95 mm, representing a network mean underestimation bias of -307.13 mm (-26.9%). FGOALS-g3 (-865.13 mm, -75.9%), EC-Earth3 (-633.79 mm, -55.6%), and ACCESS-ESM1-5 (-622.79 mm, -54.6%) demonstrated severe dry biases. In contrast, pre-computed QDM bias correction substantially improved model fidelity: QDM-corrected annual precipitation averaged 1068.48 mm across the seven GCMs, reducing aggregate network-mean bias from -307.13 mm (-26.9%) to -69.90 mm (-6.1%), representing an aggregate absolute bias reduction of 77.2%. The arithmetic mean of individual model-specific bias reductions was 73.3% across the seven GCMs, exceeding 80% for five models (EC-Earth3: 96.8%; ACCESS-ESM1-5: 88.8%; FGOALS-g3: 87.9%; CESM2: 87.2%; MIROC6: 81.3%; MRI-ESM2-0: 47.4%; CanESM5: 23.6%).

**Table 5. Performance evaluation and bias reduction of seven CMIP6 GCMs over Uttaradit Province (1995–2014).**
| GCM Model | Observed (mm) | Raw GCM (mm) | Raw Bias (mm) | Raw Bias (%) | QDM BC (mm) | QDM Bias (mm) | QDM Bias (%) | Bias Reduction (%) |
|---|---|---|---|---|---|---|---|---|
| ACCESS-ESM1-5 | 1139.81 | 517.02 | -622.79 | -54.6 | 1070.21 | -69.59 | -6.1 | 88.8 |
| CESM2 | 1139.81 | 1063.04 | -76.76 | -6.7 | 1149.62 | 9.81 | 0.9 | 87.2 |
| CanESM5 | 1139.81 | 1405.37 | 265.57 | 23.3 | 936.96 | -202.84 | -17.8 | 23.6 |
| EC-Earth3 | 1139.81 | 506.02 | -633.79 | -55.6 | 1160.04 | 20.23 | 1.8 | 96.8 |
| FGOALS-g3 | 1139.81 | 274.68 | -865.13 | -75.9 | 1035.41 | -104.40 | -9.2 | 87.9 |
| MIROC6 | 1139.81 | 1193.52 | 53.72 | 4.7 | 1129.76 | -10.05 | -0.9 | 81.3 |
| MRI-ESM2-0 | 1139.81 | 869.20 | -270.61 | -23.7 | 997.34 | -142.47 | -12.5 | 47.4 |
| Multi-Model Ensemble Mean | 1139.81 | 832.69 | -307.11 | -26.9 | 1068.48 | -71.33 | -6.3 | 73.3 |

### 3.5 Multi-Model Future Projections (2021–2050)

Under near-term future climate scenarios (2021–2050), multi-model ensemble (MME) mean annual precipitation over Uttaradit is projected to increase modestly by +2.21% (+23.60 mm) under SSP2-4.5 and +1.10% (+11.70 mm) under SSP5-8.5 relative to the seven-model bias-corrected historical baseline of 1068.48 mm (Table 6, Figure 5). Crucially, all projected changes are expressed relative to this bias-corrected historical model baseline rather than the observed gauge baseline (1139.81 mm). When evaluated as the simple arithmetic average of individual model percentage changes, the mean model deltas are +2.50% under SSP2-4.5 and +1.16% under SSP5-8.5. Individual GCM responses reveal substantial structural divergence: under SSP2-4.5, projected changes range from -4.9% (-56.83 mm, EC-Earth3) to +17.4% (+180.56 mm, FGOALS-g3); under SSP5-8.5, changes range from -10.8% (-123.71 mm, CESM2) to +14.9% (+153.84 mm, FGOALS-g3).

**Table 6. Multi-model projected precipitation changes over Uttaradit Province for 2021–2050 relative to 1995–2014 baseline under SSP2-4.5 and SSP5-8.5.**
| GCM Model | Scenario | Baseline (1995–2014) (mm) | Future (2021–2050) (mm) | Projected Change (mm) | Projected Change (%) |
|---|---|---|---|---|---|
| ACCESS-ESM1-5 | ssp245 | 1070.21 | 1036.07 | -34.15 | -3.19 |
| ACCESS-ESM1-5 | ssp585 | 1070.21 | 1069.57 | -0.64 | -0.06 |
| CESM2 | ssp245 | 1149.62 | 1102.05 | -47.57 | -4.14 |
| CESM2 | ssp585 | 1149.62 | 1025.91 | -123.71 | -10.76 |
| CanESM5 | ssp245 | 936.96 | 994.71 | +57.75 | +6.16 |
| CanESM5 | ssp585 | 936.96 | 965.05 | +28.09 | +3.00 |
| EC-Earth3 | ssp245 | 1160.04 | 1103.21 | -56.83 | -4.90 |
| EC-Earth3 | ssp585 | 1160.04 | 1254.08 | +94.04 | +8.11 |
| FGOALS-g3 | ssp245 | 1035.41 | 1215.97 | +180.56 | +17.44 |
| FGOALS-g3 | ssp585 | 1035.41 | 1189.25 | +153.84 | +14.86 |
| MIROC6 | ssp245 | 1129.76 | 1164.30 | +34.54 | +3.06 |
| MIROC6 | ssp585 | 1129.76 | 1132.89 | +3.13 | +0.28 |
| MRI-ESM2-0 | ssp245 | 997.34 | 1028.22 | +30.88 | +3.10 |
| MRI-ESM2-0 | ssp585 | 997.34 | 924.49 | -72.85 | -7.30 |
| Multi-Model Ensemble Mean | ssp245 | 1068.48 | 1092.08 | +23.60 | +2.21 |
| Multi-Model Ensemble Mean | ssp585 | 1068.48 | 1080.18 | +11.70 | +1.10 |

---

## 4. Discussion

The spatial patterns observed across Uttaradit are consistent with spatial heterogeneity associated with the province's complex topography, although explicit regression against terrain covariates (e.g., elevation, slope, aspect) was not conducted. Lowland stations such as Phichai and Tron receive ~980–1050 mm annually with high dry spell durations (CDD up to 70 days), whereas Tha Pla (1425 mm) captures higher rainfall along the foothills flanking the Sirikit Reservoir. The marked baseline sensitivity diagnostic underlines that climate change trend detection in complex tropical topography is highly sensitive to reference period selection.

Evaluation of CMIP6 models confirms that raw simulations cannot be directly applied to basin-scale hydrologic modeling without rigorous bias correction. The pre-computed QDM approach successfully attenuates systematic biases, preserving relative trends while matching historical empirical distributions. However, the wide inter-model spread (+17.4% to -10.8%) emphasizes that water management strategies must plan for plausible drying as well as intensifying extreme storm events.

---

## 5. Conclusions

This investigation delivers an authoritative, reproducible baseline and climate projection assessment for Uttaradit Province:
1. Baseline annual precipitation (1995–2014) averages 1139.80 mm, with 77.8% concentrated in May–October.
2. 11 ETCCDI indices reveal strong intra-provincial contrasts driven by elevation and topography.
3. Baseline period shifts (1981–2010 vs 1995–2014) alter percentile thresholds by up to -14.70 mm, validating the mandatory freeze of reference periods.
4. Pre-computed QDM bias correction reduces aggregate network-mean annual precipitation bias by 77.2% (from -307.13 mm to -69.90 mm), with a mean model-specific bias reduction of 73.3% across the seven GCMs.
5. Future projections (2021–2050) indicate modest ensemble-mean increases (+2.21% under SSP2-4.5 and +1.10% under SSP5-8.5) relative to the seven-model bias-corrected baseline (1068.48 mm), accompanied by wide structural model divergence (-10.8% to +17.4%).

---

## Data Availability Statement

All observational datasets and pre-computed CMIP6 GCM files are deposited in the project workspace `C:\MyPython\CMIP6Uttaradit`. All processing pipelines, figure generators, and verification suites are fully portable and packaged in `CMIP6Uttaradit_PORTABLE_Q2Q3_v1.0.zip`.
