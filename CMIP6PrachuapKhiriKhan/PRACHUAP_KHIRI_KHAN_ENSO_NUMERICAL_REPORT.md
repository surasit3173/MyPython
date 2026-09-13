# PRACHUAP KHIRI KHAN ENSO NUMERICAL EVIDENCE REPORT

STATUS: PRACHUAP-KHIRI-KHAN-ENSO-NUMERICAL-READY
UTTARADIT NUMERICAL DEPENDENCY: NONE

==================================================
1. ACTUAL DATA INVENTORY
==================================================
- Location: Prachuap Khiri Khan Province, Thailand
- Observed Daily Rainfall File: `CMIP6PrachuapKhiriKhan/data/Observed_Rain_daily_198101_201412_PrachuapKhiriKhan.csv`
- Total Station Count: 12 stations
- Station Metadata: `station_coordinates_PrachuapKhiriKhan.csv`
  - 500001 (Lat 12.37, Lon 99.95, Elev 9.13m)
  - 500002 (Lat 11.18, Lon 99.55, Elev NS)
  - 500003 (Lat 12.02, Lon 99.90, Elev NS)
  - 500004 (Lat 11.47, Lon 99.65, Elev NS)
  - 500005 (Lat 11.60, Lon 99.68, Elev 5.0m)
  - 500006 (Lat 11.62, Lon 99.67, Elev 23.01m)
  - 500007 (Lat 11.90, Lon 99.78, Elev 21.28m)
  - 500008 (Lat 12.53, Lon 99.55, Elev 130.26m)
  - 500009 (Lat 12.22, Lon 99.87, Elev 14.45m)
  - 500201 (Lat 11.83, Lon 99.83, Elev 80.0m)
  - 500202 (Lat 12.59, Lon 99.96, Elev NS)
  - 500301 (Lat 12.58, Lon 99.73, Elev 101.85m)
- Daily Records Count: 12,418 days per station (1981-01-01 to 2014-12-31)
- Missing Data Count: 0 null values in observed dataset

==================================================
2. CMIP6 MODEL INVENTORY
==================================================
- Ensemble Count: 5 GCM models (Historical 1981–2014)
- Models Evaluated:
  1. ACCESS-ESM1-5 (r1i1p1f1_gn)
  2. CESM2 (r11i1p1f1_gn)
  3. CanESM5 (r1i1p1f1_gn)
  4. EC-Earth3 (r1i1p1f1_gr)
  5. MIROC6 (r1i1p1f1_gn)
- Datasets Analyzed per Model:
  - Raw GCM Daily Precipitation
  - Quantile Delta Mapping (QDM) Bias-Corrected Daily Precipitation

==================================================
3. ENSO CLASSIFICATION & SAMPLE SIZES
==================================================
- Index Source: NOAA CPC ERSSTv6 ONI (Oceanic Niño Index)
- Definition: 3-month running mean SST anomalies in Niño 3.4 region
- Episode Persistence Rule: >= 5 consecutive overlapping 3-month windows with |ONI| >= 0.5°C
- Season Definitions:
  - Rainy Season: May 1 – Oct 31 (6 months, 34 complete seasons 1981–2014)
  - Hot/Dry Season: Nov 1 – Apr 30 (6 months, 33 complete cross-year seasons 1981/82–2013/14)
  - Incomplete Seasons Excluded: 1980/81 Hot/Dry (starts Nov 1980) and 2014/15 Hot/Dry (ends Apr 2015)
- Observed Season Classification Summary:
  - Rainy Season:
    - El Niño: 6 seasons (1982, 1987, 1991, 1997, 2002, 2009)
    - La Niña: 7 seasons (1988, 1998, 1999, 2000, 2007, 2010, 2011)
    - Neutral: 8 seasons (1981, 1985, 1989, 1990, 1996, 2001, 2012, 2013)
    - Transition / Unclassified: 13 seasons
  - Hot/Dry Season:
    - El Niño: 8 seasons (1982/83, 1986/87, 1987/88, 1991/92, 1994/95, 1997/98, 2002/03, 2009/10)
    - La Niña: 12 seasons (1983/84, 1984/85, 1988/89, 1995/96, 1998/99, 1999/00, 2000/01, 2007/08, 2008/09, 2010/11, 2011/12)
    - Neutral: 8 seasons (1985/86, 1989/90, 1990/91, 1992/93, 1993/94, 1996/97, 2006/07, 2012/13, 2013/14)
    - Transition / Unclassified: 5 seasons

==================================================
4. KEY NUMERICAL RESULTS (OBSERVED RESPONSES)
==================================================
- PRCPTOT (Seasonal Total Precipitation):
  - Rainy Season Neutral Climatology Mean: 897.45 mm
    - El Niño Anomaly: +96.40 mm (+10.74%)
    - La Niña Anomaly: -70.78 mm (-7.89%)
    - Mann-Whitney U test (El vs La): U = 28.0, p-value = 0.4452 (Not statistically significant)
  - Hot/Dry Season Neutral Climatology Mean: 341.65 mm
    - El Niño Anomaly: -12.42 mm (-3.63%)
    - La Niña Anomaly: -2.33 mm (-0.68%)
    - Mann-Whitney U test (El vs La): U = 46.0, p-value = 0.9080 (Not statistically significant)

- Rx1day (Maximum 1-Day Precipitation):
  - Rainy Season Neutral Mean: 91.13 mm
    - El Niño Anomaly: -6.78 mm (-7.44%)
    - La Niña Anomaly: -2.00 mm (-2.19%)
  - Hot/Dry Season Neutral Mean: 72.88 mm
    - El Niño Anomaly: -5.73 mm (-7.86%)
    - La Niña Anomaly: +15.55 mm (+21.34%)

- CWD (Consecutive Wet Days) & CDD (Consecutive Dry Days):
  - Rainy Season CWD: Neutral = 9.88 days, El Niño = 9.61 days (-0.26 days), La Niña = 8.68 days (-1.20 days)
  - Hot/Dry Season CDD: Neutral = 38.03 days, El Niño = 39.81 days (+1.78 days), La Niña = 39.73 days (+1.70 days)

==================================================
5. QDM BIAS-CORRECTION EVALUATION & PE_ENSO
==================================================
- Metric Definition: PE_ENSO = 100 * (QDM_Anom - Raw_Anom) / |Raw_Anom|
- Evaluation Principle: PE_ENSO is treated strictly as a relative-change metric without pre-assuming signal preservation or model improvement.
- Numerical Findings for PRCPTOT El Niño Anomaly Shift (QDM vs Raw):
  - Rainy Season:
    - ACCESS-ESM1-5: Raw = +198.81 mm, QDM = +95.69 mm (Shift = -103.12 mm)
    - CESM2: Raw = -180.20 mm, QDM = +7.91 mm (Shift = +188.11 mm)
    - CanESM5: Raw = +299.72 mm, QDM = +225.56 mm (Shift = -74.16 mm)
    - EC-Earth3: Raw = +18.91 mm, QDM = +113.88 mm (Shift = +94.97 mm)
    - MIROC6: Raw = +186.27 mm, QDM = +14.62 mm (Shift = -171.65 mm)
- Conclusion on QDM Behavior:
  QDM exhibits mixed behavior across models. In models with excessive raw ENSO response (e.g. CanESM5, MIROC6), QDM dampens the anomaly towards observations. In models with opposite raw response (e.g. CESM2), QDM corrects the anomaly sign. QDM does NOT universally preserve or amplify model ENSO signals.

==================================================
6. STATISTICAL VALIDATION & LOW-N DIAGNOSTICS
==================================================
- Low-N Flagging:
  - All Rainy season El Niño (n=6) and La Niña (n=7) comparisons were evaluated with explicit low-n awareness.
  - Hot/Dry season El Niño (n=8) and La Niña (n=12) provide moderate sample sizes.
  - No p-values reach p < 0.05 for PRCPTOT phase differences, indicating high interannual variability in Prachuap Khiri Khan relative to ENSO forcing.

==================================================
7. OUTPUT PACKAGE MANIFEST
==================================================
- Executable Pipeline Script: `CMIP6PrachuapKhiriKhan/run_prachuap_enso_analysis.py`
- Test Suite: `CMIP6PrachuapKhiriKhan/tests/test_prachuap_enso.py`
- CSV Output Tables (`CMIP6PrachuapKhiriKhan/output/tables/`):
  1. `enso_classification_summary.csv`
  2. `enso_episode_catalog.csv`
  3. `enso_phase_sample_sizes.csv`
  4. `observed_seasonal_indices.csv`
  5. `all_source_seasonal_indices.csv`
  6. `enso_response_summary.csv`
  7. `enso_asymmetry_summary.csv`
  8. `qdm_relative_change_pe_enso.csv`
- Publication Figures (`CMIP6PrachuapKhiriKhan/output/figures/`):
  1. `Figure1_ENSO_Classification_Timeline.png` / `.pdf`
  2. `Figure2_Seasonal_PRCPTOT_ENSO_Response.png` / `.pdf`
  3. `Figure3_QDM_Bias_Correction_ENSO_Shift.png` / `.pdf`
- Run Provenance Manifest: `CMIP6PrachuapKhiriKhan/output/manifests/enso_run_manifest.json`

==================================================
8. REPRODUCIBILITY INSTRUCTIONS
==================================================
To reproduce the complete Prachuap Khiri Khan ENSO numerical evidence package from scratch:
```bash
python3 CMIP6PrachuapKhiriKhan/run_prachuap_enso_analysis.py
python3 -m unittest discover -s CMIP6PrachuapKhiriKhan/tests
```

==================================================
9. CONTAMINATION AUDIT RESULT
==================================================
- Uttaradit Station IDs in Outputs: 0 found
- Uttaradit Numerical Results in Outputs: 0 found
- Uttaradit File Dependencies: NONE
- Final Status: PASSED CONTAMINATION AUDIT CLEANLY
