# PRACHUAP KHIRI KHAN ENSO NUMERICAL EVIDENCE REPORT

STATUS: PRACHUAP-KHIRI-KHAN-ENSO-NUMERICAL-READY
UTTARADIT NUMERICAL DEPENDENCY: NONE
MANUSCRIPT WRITING: NOT PERFORMED

==================================================
1. FACTUAL NUMERICAL RESULTS
==================================================
- Location: Prachuap Khiri Khan Province, Thailand (12 stations)
- Study Period: 1981–2014 (34 years daily observational record, 12,418 days)
- ENSO Index: NOAA CPC ERSSTv6 Oceanic Niño Index (ONI)
- Season Definitions:
  - Rainy Season: May 1 – Oct 31 (34 complete seasons)
  - Hot/Dry Season: Nov 1 – Apr 30 (33 complete cross-year seasons, 1981/82–2013/14)
  - Excluded Incomplete Seasons: 1980/81 Hot/Dry (starts Nov 1980) and 2014/15 Hot/Dry (ends Apr 2015)
- Observed ENSO Sample Sizes:
  - Rainy Season: El Niño (n=6), La Niña (n=7), Neutral (n=8), Transition/Unclassified (n=13)
  - Hot/Dry Season: El Niño (n=8), La Niña (n=12), Neutral (n=8), Transition/Unclassified (n=5)

- Observed Precipitation Anomalies (relative to Neutral climatology):
  - Rainy Season PRCPTOT (Neutral Climatology Mean = 897.45 mm):
    - El Niño Anomaly: +96.40 mm (+10.74%)
    - La Niña Anomaly: -70.78 mm (-7.89%)
    - Mann-Whitney U test (El Niño vs La Niña): U = 28.0, p-value = 0.4452 (Not statistically significant at alpha = 0.05)
  - Hot/Dry Season PRCPTOT (Neutral Climatology Mean = 341.65 mm):
    - El Niño Anomaly: -12.42 mm (-3.63%)
    - La Niña Anomaly: -2.33 mm (-0.68%)
    - Mann-Whitney U test (El Niño vs La Niña): U = 46.0, p-value = 0.9080 (Not statistically significant at alpha = 0.05)

- QDM Bias Correction & Observational Distance Metrics (Rainy Season El Niño Anomaly, Obs = +96.40 mm):
  - ACCESS-ESM1-5: Raw = +198.81 mm (error = 102.41 mm), QDM = +95.69 mm (error = 0.71 mm) -> TOWARD_OBSERVATION
  - CESM2: Raw = -180.20 mm (error = 276.60 mm), QDM = +7.91 mm (error = 88.49 mm) -> TOWARD_OBSERVATION
  - CanESM5: Raw = +299.72 mm (error = 203.32 mm), QDM = +225.56 mm (error = 129.16 mm) -> TOWARD_OBSERVATION
  - EC-Earth3: Raw = +18.91 mm (error = 77.49 mm), QDM = +113.88 mm (error = 17.48 mm) -> TOWARD_OBSERVATION
  - MIROC6: Raw = +186.27 mm (error = 89.87 mm), QDM = +81.78 mm (error = 81.78 mm) -> TOWARD_OBSERVATION

==================================================
2. INTERPRETATION & NUMERICAL SYNTHESIS
==================================================
1. In Prachuap Khiri Khan, the observed Rainy season precipitation is elevated during El Niño (+10.74%) and reduced during La Niña (-7.89%), but high interannual variance results in non-statistically significant phase differences (p > 0.05).
2. During the Hot/Dry season, precipitation anomalies during both El Niño (-3.63%) and La Niña (-0.68%) are minor relative to baseline variability.
3. Quantile Delta Mapping (QDM) bias correction shifts GCM El Niño precipitation anomalies closer to observed values across all 5 models during the Rainy season, reducing absolute error relative to raw GCM outputs.

==================================================
3. SAFE CLAIMS VS PROHIBITED CLAIMS (FOR MANUSCRIPT WRITER)
==================================================
SAFE CLAIMS (DATA-SUPPORTED):
- "Observed Rainy season rainfall in Prachuap Khiri Khan averages 897.45 mm under Neutral conditions, with a +10.74% anomaly during El Niño and -7.89% anomaly during La Niña."
- "Mann-Whitney U tests indicate that seasonal precipitation differences between ENSO phases in Prachuap Khiri Khan are not statistically significant at p < 0.05 due to high interannual variability."
- "QDM bias correction reduces absolute error in Rainy season El Niño anomaly representation relative to observed data across all five evaluated GCMs."

PROHIBITED CLAIMS (DATA-CONTRADICTED OR UNSUPPORTED):
- DO NOT claim that ENSO precipitation anomalies in Prachuap Khiri Khan are statistically significant.
- DO NOT claim that QDM universally amplifies or preserves raw GCM signals without evaluating observational error.
- DO NOT claim or reuse any numerical value, sample size, or station ID from the Uttaradit study.
- DO NOT claim causal atmospheric mechanisms not evaluated in this study design.

==================================================
4. OUTPUT PACKAGE ARTIFACTS
==================================================
- Traceability Matrix: `PRACHUAP_KHIRI_KHAN_ENSO_TRACEABILITY.csv`
- Validation Report: `PRACHUAP_KHIRI_KHAN_ENSO_VALIDATION_REPORT.md`
- Run Manifest: `output/manifests/enso_run_manifest.json`
- Executable Pipeline: `run_prachuap_enso_analysis.py`
- Test Suite: `tests/test_prachuap_enso.py`
