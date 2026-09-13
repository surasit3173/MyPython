# PRACHUAP KHIRI KHAN ENSO NUMERICAL VALIDATION REPORT

STATUS: PRACHUAP-KHIRI-KHAN-ENSO-NUMERICAL-READY
UTTARADIT NUMERICAL DEPENDENCY: NONE

==================================================
1. DATA INTEGRITY & AUDIT VERIFICATION
==================================================
- Observed Dataset: `CMIP6PrachuapKhiriKhan/data/Observed_Rain_daily_198101_201412_PrachuapKhiriKhan.csv`
  - SHA-256: `c0d96fa605901ad08b5c9222d94840d26bf3b179acd01781c62d1d2b8e6700d7`
  - Record Count: 12,418 daily records (1981-01-01 to 2014-12-31)
  - Missingness: 0 missing values across all columns
- Station Metadata: 12 active meteorological rain gauges in Prachuap Khiri Khan Province
  - Station IDs: 500001, 500002, 500003, 500004, 500005, 500006, 500007, 500008, 500009, 500201, 500202, 500301
- Model Inventory (5 GCMs, Raw and QDM):
  1. ACCESS-ESM1-5 (Historical 1981–2014)
  2. CESM2 (Historical 1981–2014)
  3. CanESM5 (Historical 1981–2014)
  4. EC-Earth3 (Historical 1981–2014)
  5. MIROC6 (Historical 1981–2014)

==================================================
2. ENSO CLASSIFICATION & SEASONAL COMPLETENESS
==================================================
- Source: NOAA CPC ERSSTv6 Oceanic Niño Index (ONI) frozen table (`noaa_cpc_oni_ersstv6_2026-09-01.html`)
  - SHA-256: `ab9278cf270a412c89b6a9b8fd5641a5167e67a706f43695411a310e211d5c5e`
- Classification Principle: >= 5 consecutive overlapping 3-month windows with |ONI| >= 0.5°C
- Season Completeness Rule:
  - Rainy Season (May 1 – Oct 31): 34 complete seasons (1981–2014)
  - Hot/Dry Season (Nov 1 – Apr 30): 33 complete cross-year seasons (1981/82–2013/14)
  - Incomplete Seasons Excluded: 1980/81 Hot/Dry (starts Nov 1980) and 2014/15 Hot/Dry (ends Apr 2015)
- Sample Sizes:
  - Rainy Season: El Niño (n=6), La Niña (n=7), Neutral (n=8), Transition (n=13)
  - Hot/Dry Season: El Niño (n=8), La Niña (n=12), Neutral (n=8), Transition (n=5)

==================================================
3. STATISTICAL INFERENCE & LOW-N DIAGNOSTICS
==================================================
- Statistical Test: Mann-Whitney U test (two-sided) for composite phase comparisons
- Low-N Condition: Explicitly flagged for all comparisons where sample size n < 5
- Significance Threshold: alpha = 0.05
- Recomputation Results (PRCPTOT Regional Means):
  - Rainy Season:
    - El Niño (+96.40 mm, +10.74%) vs Neutral: U = 26.0, p-value = 0.8518 (Not significant)
    - La Niña (-70.78 mm, -7.89%) vs Neutral: U = 26.0, p-value = 0.8665 (Not significant)
    - El Niño vs La Niña: U = 28.0, p-value = 0.4452 (Not significant)
  - Hot/Dry Season:
    - El Niño (-12.42 mm, -3.63%) vs Neutral: U = 32.0, p-value = 1.0000 (Not significant)
    - La Niña (-2.33 mm, -0.68%) vs Neutral: U = 44.0, p-value = 0.7553 (Not significant)
    - El Niño vs La Niña: U = 46.0, p-value = 0.9080 (Not significant)

==================================================
4. QDM OBSERVATIONAL DISTANCE EVALUATION
==================================================
- PE_ENSO Metric: Treated strictly as a relative change metric: `PE_ENSO = 100 * (QDM - Raw) / |Raw|`
- Distance Metric Evaluation (Absolute Error relative to Observed Anomaly):
  - Rainy Season PRCPTOT El Niño Anomaly (Observed = +96.40 mm):
    - ACCESS-ESM1-5: Raw error = 102.41 mm, QDM error = 0.71 mm -> TOWARD_OBSERVATION
    - CESM2: Raw error = 276.60 mm, QDM error = 88.49 mm -> TOWARD_OBSERVATION
    - CanESM5: Raw error = 203.32 mm, QDM error = 129.16 mm -> TOWARD_OBSERVATION
    - EC-Earth3: Raw error = 77.49 mm, QDM error = 17.48 mm -> TOWARD_OBSERVATION
    - MIROC6: Raw error = 89.87 mm, QDM error = 81.78 mm -> TOWARD_OBSERVATION
  - Overall Finding: QDM reduces the absolute error in El Niño precipitation anomaly representation across all 5 models during the Rainy season in Prachuap Khiri Khan.

==================================================
5. CONTAMINATION AUDIT & TRACEABILITY VERIFICATION
==================================================
- Uttaradit Station IDs in Outputs: 0 found (PASSED)
- Uttaradit Numerical Results in Outputs: 0 found (PASSED)
- File Provenance Traceability Matrix: Generated (`PRACHUAP_KHIRI_KHAN_ENSO_TRACEABILITY.csv`)
- Run Manifest: Generated (`output/manifests/enso_run_manifest.json`)
- Final Validation Status: ALL GATES PASSED CLEANLY
