# FINAL EVIDENCE FREEZE — Q2/Q3 MANUSCRIPT

**Document Purpose:** Frozen evidence base for scientific manuscript drafting. All validation expansions, refactorings, and methodological modifications are officially **LOCKED**.

---

## 1. PROJECT 1: PRACHUAP KHIRI KHAN (`C:\MyPython\CMIP6PrachuapKhiriKhan`)

### 1.1 Authoritative Data
- **Canonical Observed Input:** `Observed_Rain_daily_198101_201412_PrachuapKhiriKhan.csv`
- **File SHA256:** `abdec5e39458b3441bcce139517b3eacc8855f85f2ec5e6ce06e295a280e31ed`
- **Temporal Coverage:** 1981-01-01 through 2014-12-31 ($N=34$ annual observations per station).
- **Stations:** 12 stations (`500001`, `500002`, `500003`, `500004`, `500005`, `500006`, `500007`, `500008`, `500009`, `502001`, `502002`, `503001`).

### 1.2 Authoritative Code
- **Statistical Engine Core:** `C:\Users\PC\.gemini\antigravity\scratch\research-intelligence\scripts\stats_engine.py` (`SHA256: 9ddba4a9f74afc3a22600176e06cbd93d2899b09479766750a3df802ab75734a`)
- **Execution Script:** `scripts/rerun_phase5f_project1.py` (`SHA256: 5d8009cf012013f9c6bd7d99be821a8f9c1b7907f16ef0dd5a09c25bbdf6406e`)

### 1.3 Authoritative Config
- **Configuration Path:** `config/config.yaml` (`SHA256: 05ce0f17d3c984eabef1b313a35b4fc52ee49823d82b3c9e08fbb9b7ac42c1bd`)
- **Alpha Significance Level:** $\alpha = 0.05$ (two-tailed $z_{crit} = 1.95996$)

### 1.4 Validated Results That May Be Used
- **Standard Mann-Kendall Trends ($Z_{\text{MK}}$ and $p_{\text{MK}}$) for all 12 stations:**
  - Station `500001`: $Z = +1.142, p = 0.2536$, Sen slope $= +7.410$ mm/yr
  - Station `500002`: $Z = +2.253, p = 0.0242$, Sen slope $= +9.175$ mm/yr (Significant at $\alpha=0.05$)
  - Station `500003`: $Z = -1.453, p = 0.1463$, Sen slope $= -5.933$ mm/yr
  - Station `500004`: $Z = +0.534, p = 0.5936$, Sen slope $= +2.355$ mm/yr
  - Station `500005`: $Z = -0.237, p = 0.8125$, Sen slope $= -1.090$ mm/yr
  - Station `500006`: $Z = +0.534, p = 0.5936$, Sen slope $= +1.354$ mm/yr
  - Station `500007`: $Z = -0.830, p = 0.4064$, Sen slope $= -2.254$ mm/yr
  - Station `500008`: $Z = -0.267, p = 0.7896$, Sen slope $= -0.650$ mm/yr
  - Station `500009`: $Z = +0.460, p = 0.6458$, Sen slope $= +0.583$ mm/yr
  - Station `502001`: $Z = +0.623, p = 0.5335$, Sen slope $= +3.511$ mm/yr
  - Station `502002`: $Z = -1.156, p = 0.2476$, Sen slope $= -4.376$ mm/yr
  - Station `503001`: $Z = -0.296, p = 0.7669$, Sen slope $= -0.621$ mm/yr
- **Valid MMK Results (Sen-Detrended Ranks) for 11 Stations:**
  - `500001` ($\frac{n}{n_s^*} = 1.000, Z_{\text{MMK}} = +1.142$)
  - `500002` ($\frac{n}{n_s^*} = 0.2456, Z_{\text{MMK}} = +4.547$)
  - `500003` ($\frac{n}{n_s^*} = 1.9059, Z_{\text{MMK}} = -1.052$)
  - `500004` ($\frac{n}{n_s^*} = 0.2589, Z_{\text{MMK}} = +1.049$)
  - `500005` ($\frac{n}{n_s^*} = 0.3929, Z_{\text{MMK}} = -0.378$)
  - `500006` ($\frac{n}{n_s^*} = 0.1926, Z_{\text{MMK}} = +1.216$)
  - `500007` ($\frac{n}{n_s^*} = 1.000, Z_{\text{MMK}} = -0.830$)
  - `500008` ($\frac{n}{n_s^*} = 1.000, Z_{\text{MMK}} = -0.267$)
  - `500009` ($\frac{n}{n_s^*} = 0.4456, Z_{\text{MMK}} = +0.689$)
  - `502001` ($\frac{n}{n_s^*} = 1.000, Z_{\text{MMK}} = +0.623$)
  - `503001` ($\frac{n}{n_s^*} = 0.6472, Z_{\text{MMK}} = -0.369$)

### 1.5 Results That Must NOT Be Used
- **Station `502002` Unclamped Hamed-Rao MMK $Z_{\text{MMK}}$:** Must NOT report $Z$ or $p$ as numeric values because raw $\frac{n}{n_s^*} = -0.2147 \le 0$ produces a non-positive adjusted variance ($\text{Var}^*(S) = -977.18$) and a `DOMAIN_ERR`.
- **Artificially Clamped MMK Values:** Must NOT report clamped $\max(1, \frac{n}{n_s^*})$ values without disclosing the empirical multi-lag variance collapse.

### 1.6 Tables Approved for Manuscript
- Table of Standard Mann-Kendall Trends & Sen's Slopes for 12 Stations.
- Table of MMK Variance Ratios $\frac{n}{n_s^*}$ and Corrected $Z$-scores for the 11 valid stations, with Station `502002` explicitly tabulated as `DOMAIN_ERR / NON-POSITIVE VARIANCE`.

### 1.7 Figures Approved for Manuscript
- Annual rainfall timeseries plots with Sen's slope trendlines for 12 stations.
- Station location spatial map for Prachuap Khiri Khan province.

### 1.8 Numerical Claims Approved
- "Station 500002 exhibits a statistically significant upward annual rainfall trend ($\beta = +9.175$ mm/yr, standard MK $Z = +2.253, p = 0.0242$)."
- "Standard Mann-Kendall trend tests across 11 of 12 stations in Prachuap Khiri Khan indicate non-significant annual rainfall trends at the $\alpha = 0.05$ significance level."

### 1.9 Numerical Claims Prohibited
- Prohibited to claim: "100% of stations were verified by Hamed-Rao MMK" (Station 502002 fails due to negative variance ratio).
- Prohibited to claim: "Station 502002 MMK $Z = -1.156$" without declaring the negative autocorrelation breakdown.

### 1.10 Methodological Limitations That Must Be Disclosed
- Hamed & Rao (1998) multi-lag rank autocorrelation summation encounters finite-sample instability ($\frac{n}{n_s^*} \le 0$) on Station `502002` due to significant negative lag-1 ($\rho_1 = -0.380$) and lag-5 ($\rho_5 = -0.428$) autocorrelation.

### 1.11 Unsupported Claims That Must Be Removed
- Any claim that Hamed & Rao (1998) MMK is universally valid for all finite sample negative autocorrelation patterns without domain restrictions.

---

## 2. PROJECT 2: UTTARADIT (`C:\MyPython\CMIP6Uttaradit`)

### 2.1 Authoritative Data
- **Canonical Observed Input:** `Data_Uttaradit/Observed_Rain_daily_198101_201412_Uttaradit.csv` (`SHA256: 1621f8f9c15884c3a4deb33c8bea0d070a1639b70790cfc8f0695e3ca4befbe2`)
- **Station Coordinates Input:** `Data_Uttaradit/station_coordinates_Uttaradit.csv` (`SHA256: 852ac008480f934f29d65f0ed7bbc2f563cc21c4915b346bb7fc26dd205872d1`)
- **Observed Stations:** 13 stations (`351001` through `351012`, `351201`).
- **CMIP6 Models (Pre-computed files):** 7 GCMs (`ACCESS-ESM1-5`, `CESM2`, `CanESM5`, `EC-Earth3`, `FGOALS-g3`, `MIROC6`, `MRI-ESM2-0`).

### 2.2 Authoritative Code
- **ETCCDI Engine Core:** `src/indices/etccdi.py`
- **Validation Gates Engine:** `src/validation/gates.py`
- **Execution Script:** `scripts/rerun_phase5f_project2.py` (`SHA256: e8f66fbcf5759ff5390ae51eeaa94cbe40d346ffc1f0b0bd32b90623a652a9ae`)

### 2.3 Authoritative Config
- **Configuration Path:** `config/config.yaml` (`SHA256: 1747a2d7118c192ed4dcaffc9b22d230a11158c86018797a0f029bf90321a5b5`)
- **Authoritative Historical Baseline Period:** `[1995, 2014]` (1995-01-01 through 2014-12-31).
- **Wet-Day Threshold:** $1.0$ mm/day.

### 2.4 Validated Results That May Be Used
- **Corrected Observed Baseline ETCCDI 11 Indices (1995–2014 Mean) across all 13 stations:**
  - `351001`: PRCPTOT = 985.59 mm, SDII = 12.50 mm/d, Rx1day = 101.23 mm, Rx5day = 174.42 mm, CDD = 58.88 d, CWD = 8.29 d, R10mm = 28.68 d, R20mm = 15.50 d, R50mm = 2.97 d, R95p = 289.75 mm, R99p = 118.05 mm
  - `351002`: PRCPTOT = 976.74 mm, SDII = 13.26 mm/d, Rx1day = 75.47 mm, Rx5day = 137.89 mm, CDD = 70.12 d, CWD = 12.65 d, R10mm = 30.00 d, R20mm = 14.97 d, R50mm = 2.62 d, R95p = 223.07 mm, R99p = 62.04 mm
  - `351003`: PRCPTOT = 1366.07 mm, SDII = 13.83 mm/d, Rx1day = 87.61 mm, Rx5day = 146.44 mm, CDD = 55.71 d, CWD = 33.00 d, R10mm = 40.26 d, R20mm = 18.82 d, R50mm = 3.68 d, R95p = 487.60 mm, R99p = 176.27 mm
  - `351004`: PRCPTOT = 1093.65 mm, SDII = 13.10 mm/d, Rx1day = 89.49 mm, Rx5day = 148.51 mm, CDD = 65.26 d, CWD = 7.38 d, R10mm = 33.09 d, R20mm = 17.18 d, R50mm = 2.50 d, R95p = 264.72 mm, R99p = 79.95 mm
  - `351005`: PRCPTOT = 1098.19 mm, SDII = 12.70 mm/d, Rx1day = 77.34 mm, Rx5day = 137.95 mm, CDD = 60.21 d, CWD = 13.97 d, R10mm = 33.12 d, R20mm = 15.68 d, R50mm = 2.85 d, R95p = 340.67 mm, R99p = 112.54 mm
  - `351006`: PRCPTOT = 1113.98 mm, SDII = 7.76 mm/d, Rx1day = 48.10 mm, Rx5day = 109.30 mm, CDD = 41.94 d, CWD = 49.68 d, R10mm = 28.74 d, R20mm = 8.26 d, R50mm = 0.82 d, R95p = 249.87 mm, R99p = 76.47 mm
  - `351007`: PRCPTOT = 1172.96 mm, SDII = 7.70 mm/d, Rx1day = 51.11 mm, Rx5day = 110.97 mm, CDD = 38.74 d, CWD = 52.56 d, R10mm = 29.79 d, R20mm = 8.00 d, R50mm = 0.88 d, R95p = 248.97 mm, R99p = 84.79 mm
  - `351008`: PRCPTOT = 1096.33 mm, SDII = 6.83 mm/d, Rx1day = 62.87 mm, Rx5day = 117.33 mm, CDD = 39.76 d, CWD = 35.71 d, R10mm = 28.21 d, R20mm = 7.65 d, R50mm = 1.03 d, R95p = 259.86 mm, R99p = 92.78 mm
  - `351009`: PRCPTOT = 1169.36 mm, SDII = 5.12 mm/d, Rx1day = 29.32 mm, Rx5day = 79.45 mm, CDD = 34.94 d, CWD = 86.06 d, R10mm = 25.18 d, R20mm = 2.12 d, R50mm = 0.06 d, R95p = 200.14 mm, R99p = 62.07 mm
  - `351010`: PRCPTOT = 1137.55 mm, SDII = 5.19 mm/d, Rx1day = 28.96 mm, Rx5day = 79.55 mm, CDD = 34.94 d, CWD = 68.15 d, R10mm = 26.53 d, R20mm = 2.79 d, R50mm = 0.09 d, R95p = 209.22 mm, R99p = 56.41 mm
  - `351011`: PRCPTOT = 1094.14 mm, SDII = 12.17 mm/d, Rx1day = 113.92 mm, Rx5day = 185.56 mm, CDD = 43.88 d, CWD = 10.09 d, R10mm = 31.74 d, R20mm = 15.26 d, R50mm = 2.85 d, R95p = 317.59 mm, R99p = 121.88 mm
  - `351012`: PRCPTOT = 930.26 mm, SDII = 11.95 mm/d, Rx1day = 109.66 mm, Rx5day = 193.37 mm, CDD = 55.53 d, CWD = 8.00 d, R10mm = 25.94 d, R20mm = 12.91 d, R50mm = 3.18 d, R95p = 292.39 mm, R99p = 99.36 mm
  - `351201`: PRCPTOT = 1050.55 mm, SDII = 11.46 mm/d, Rx1day = 91.94 mm, Rx5day = 166.27 mm, CDD = 53.06 d, CWD = 8.85 d, R10mm = 30.53 d, R20mm = 15.06 d, R50mm = 2.91 d, R95p = 293.54 mm, R99p = 94.19 mm
- **Diagnostic Baseline Sensitivity Results ($R95p$ & $R99p$ shifts between 1981–2010 and 1995–2014):**
  - Demonstrates that thresholding on 1995–2014 alters mean $R95p$ by up to $+182.04$ mm (Station `351003`) and $-89.29$ mm (Station `351007`).

### 2.5 Results That Must NOT Be Used
- **Legacy 1981–2010 ETCCDI Percentile Outputs:** Must NOT be presented as the primary study baseline.
- **Claimed ANOVA Variance Percentages (65–75% Model, 15–25% Scenario, 10–15% Internal):** Must NOT be cited or included in tables/figures (unsupported by repository code).
- **Claim of Live QDM Bias Correction Execution:** Must NOT claim live transformation execution from raw NetCDF files.

### 2.6 Tables Approved for Manuscript
- Table of Observed 11 ETCCDI Extreme Precipitation Indices (1995–2014 baseline mean) for 13 stations.
- Table of Diagnostic Baseline Sensitivity ($P_{95}$ & $P_{99}$ threshold and index differences between 1981–2010 and 1995–2014).
- Summary Table of Pre-computed GCM Bias Correction Skill (Mean bias reduction from -570.76 mm to -34.11 mm for ACCESS-ESM1-5).

### 2.7 Figures Approved for Manuscript
- Map of 13 rain gauge stations in Uttaradit province.
- Comparative bar chart of baseline ETCCDI indices across stations.
- Heatmap of pre-computed QDM skill improvement across 28 diagnostic stations (`QDM_Q1_FIGURE_01_improvement_heatmap.png`).

### 2.8 Numerical Claims Approved
- "The authoritative historical baseline (1995–2014) mean PRCPTOT across Uttaradit ranges from 930.26 mm (Station 351012) to 1366.07 mm (Station 351003)."
- "Pre-computed QDM bias-corrected GCM outputs reduce annual rainfall mean bias from -570.76 mm to -34.11 mm for ACCESS-ESM1-5 across Uttaradit."

### 2.9 Numerical Claims Prohibited
- Prohibited to claim: "ANOVA variance decomposition attributes 65–75% of uncertainty to GCM structural differences" (unsupported by repository code).
- Prohibited to claim: "Live QDM code transformation was executed from raw CMIP6 NetCDF files during pipeline execution."

### 2.10 Methodological Limitations That Must Be Disclosed
- The QDM bias-corrected GCM datasets exist in the project repository as pre-computed CSV files; live transformation code mapping raw CMIP6 NetCDF files to bias-corrected series is not actively integrated into the repository execution pipeline.
- ANOVA uncertainty decomposition of CMIP6 future projections was not computed in code and is excluded from the manuscript.

### 2.11 Unsupported Claims That Must Be Removed
- Unsupported claim: 65–75% Model Structural / 15–25% Scenario Forcing / 10–15% Internal Climate Variability. **REMOVED FROM MANUSCRIPT LAYER.**

---

## 3. MASTER EVIDENCE TABLE

| CLAIM / METRIC | VALUE / RESULT | SOURCE FILE | AUDIT STATUS | USE IN MANUSCRIPT (YES/NO) |
|---|---|---|---|---|
| **P1 Daily Records Count** | 12,418 records (1981-2014), 0 missing, 0 duplicates | `Observed_Rain_daily_198101_201412_PrachuapKhiriKhan.csv` | `REAL-DATA REPRODUCED` | **YES** |
| **P1 Station 500002 MK Trend** | $Z = +2.253, p = 0.0242$, Sen slope $= +9.175$ mm/yr | `scripts/rerun_phase5f_project1.py` | `REAL-DATA REPRODUCED` | **YES** |
| **P1 Station 500001 MMK Trend** | $Z_{\text{MMK}} = +1.142, p = 0.2536$, ratio $= 1.000$ | `scripts/rerun_phase5f_project1.py` | `REAL-DATA REPRODUCED` | **YES** |
| **P1 Station 502002 MMK Value** | $\frac{n}{n_s^*} = -0.2147 \le 0 \implies \text{Var}^*(S) = -977.18 \implies \mathbf{DOMAIN\_ERR}$ | `scripts/inspect_prachuap_unclamped.py` | `UNVERIFIED / DOMAIN_ERR` | **NO (Tabulate as DOMAIN_ERR)** |
| **P1 Standard MK 12 Stations** | All 12 stations $Z_{\text{MK}}$ and Sen's slopes | `scripts/rerun_phase5f_project1.py` | `REAL-DATA REPRODUCED` | **YES** |
| **P2 Authoritative Baseline** | `1995–2014` (20 years) | `config/config.yaml` | `REAL-DATA REPRODUCED` | **YES** |
| **P2 Observed ETCCDI 11 Indices** | Baseline (1995-2014) mean for 13 stations | `scripts/rerun_phase5f_project2.py` | `REAL-DATA REPRODUCED` | **YES** |
| **P2 Baseline Sensitivity** | $R95p$ shift up to $+182.04$ mm (Stn 351003) | `scripts/rerun_phase5f_project2.py` | `REAL-DATA REPRODUCED` | **YES** |
| **P2 Pre-computed QDM Bias Skill** | ACCESS-ESM1-5 raw bias -570.76 mm $\to$ BC bias -34.11 mm | `scripts/recompute_project2_etccdi.py` | `REAL-DATA REPRODUCED` | **YES (Mark as pre-computed)** |
| **P2 Live QDM Code Provenance** | Live NetCDF-to-BC transformation script | Repository Audit | `UNVERIFIED PROVENANCE` | **NO (Disclose as limitation)** |
| **P2 ANOVA Variance Decomposition** | Model 65-75%, Scenario 15-25%, Internal 10-15% | Manuscript Claim | `UNSUPPORTED` | **NO (STRICTLY REMOVED)** |

---

## 4. END OF VALIDATION EXPANSION DIRECTIVE

All validation expansions, re-analyses, and methodological modifications are **OFFICIALLY STOPPED AND LOCKED**. No Phase 5G, Phase 5F.3, or Phase 5F.4 scripts shall be created. Manuscript preparation must strictly draw from the approved items in this `FINAL_EVIDENCE_FREEZE.md` document.

---
*End of Final Evidence Freeze Document.*
