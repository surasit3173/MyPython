# PAPER 3 — FINAL ANALYSIS REPORT
## ENSO-Conditioned Seasonal Rainfall and Climate-Signal Analysis over Uttaradit, Thailand

### 1. Executive Summary
- **Project Scope:** `CMIP6Uttaradit/paper3/`
- **Execution Status:** PASS (All acceptance gates P3-A through P3-H verified)
- **Primary Finding:** Quantile Delta Mapping (QDM) preserves raw CMIP6 directional ENSO responses while amplifying response magnitude ($PE_{ENSO} = 62.17\%$).

### 2. Verified Data Inventory
- **Rain Gauges:** 13 stations (351001–351012, 351201)
- **Observations:** Daily precipitation (1981–2014, 12,418 days, 0 missing values)
- **CMIP6 Models (7):** ACCESS-ESM1-5, CanESM5, CESM2, EC-Earth3, FGOALS-g3, MIROC6, MRI-ESM2-0
- **Scenarios:** Historical (1981–2014), SSP2-4.5, SSP5-8.5
- **Primary Overlap Analysis Baseline:** 1995–2014

### 3. ENSO Classification Summary
- **Source:** Pinned NOAA CPC ONI (PSL mirror: `https://psl.noaa.gov/data/correlation/oni.data`, SHA-256: `7a1893f0d92f96090940ccb5352d7a3413ff217af4e4278af76fd05515a34753`)
- **Seasons:** 20 Rainy seasons (1995–2014) and 19 complete Hot/Dry seasons (1995/96–2013/14; 2014/15 excluded due to observed daily record ending 2014-12-31)
- **Sample Sizes:**
  - Rainy Season: 2 El Niño, 6 Neutral, 5 La Niña, 7 Transition/Unclassified
  - Hot/Dry Season: 4 El Niño, 5 Neutral, 9 La Niña, 1 Transition/Unclassified

### 4. Executed Methods
- Calculated 11 core ETCCDI precipitation indices: PRCPTOT, wet_day_freq, SDII, Rx1day, Rx5day, R20mm, R50mm, R95p, R99p, CDD, CWD. R95p/R99p threshold defined using 1981–2014 observed wet days ($\ge 1.0\text{ mm}$).
- Computed phase composite anomalies ($A_{phase}$), ENSO Asymmetry ($ASYM$), Directional Agreement, Magnitude Errors, and QDM Signal Preservation Errors ($PE_{ENSO}$).
- Executed Mann-Whitney U inference and flagged low-sample comparisons ($n < 3$) as `DIAGNOSTIC`.

### 5. Main Numerical Results
- **Observed La Niña Rainy Season PRCPTOT Anomaly:** -0.26%
- **Observed El Niño Hot/Dry Season PRCPTOT Anomaly:** -17.19%
- **Raw CMIP6 La Niña Rainy Season PRCPTOT Anomaly:** 2.53%
- **QDM CMIP6 La Niña Rainy Season PRCPTOT Anomaly:** 7.23%
- **QDM Signal Preservation Error ($PE_{ENSO}$):** 62.17%

### 6. Validation Results & Acceptance Gates
- **P3-A (ENSO Source):** PASS
- **P3-B (Season Construction):** PASS
- **P3-C (ENSO Classification):** PASS
- **P3-D (Common Baseline):** PASS
- **P3-E (QDM Frozen Parameters):** PASS
- **P3-F (ENSO Responses):** PASS
- **P3-G (ENSO Asymmetry):** PASS
- **P3-H (Statistical Inference):** PASS

### 7. Figures & Tables Produced
- `Paper3_MAIN_Tables.xlsx` (Tables 1–6)
- `Paper3_SUPPLEMENTARY_Tables.xlsx` (Tables S1–S9)
- `Figure_P3_01_ENSO_observed.png/pdf`
- `Figure_P3_02_ENSO_raw_vs_QDM.png/pdf`
- `Figure_P3_03_ENSO_asymmetry.png/pdf`
- `Figure_P3_04_ENSO_extremes.png/pdf`
- `Figure_P3_05_ENSO_temporal.png/pdf`
- `Figure_P3_06_ENSO_synthesis.png/pdf`

### 8. Final Status
- **Status:** PASS
- **Reproducibility:** Fully reproducible via `run_data_audit.py`, `build_enso_classification.py`, `engine_enso_analysis.py`, `generate_tables_and_figures.py`, and `build_manuscript_and_report.py`.
