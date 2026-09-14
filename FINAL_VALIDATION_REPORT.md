# FINAL PUBLICATION VALIDATION REPORT
Target Journal Level: Q3
Date: 2026-09-14

Uttaradit:
  Data ........ PASS
  Numerical ... PASS
  Bootstrap ... PASS
  Return level  PASS
  Manuscript .. PASS
  Reproducible  PASS

Prachuap:
  Data ........ PASS
  Numerical ... PASS
  Statistics .. PASS
  Tables/Figs . PASS
  Manuscript .. PASS
  Reproducible  PASS

Overall:
  Publication status: READY
  Remaining blockers: NONE

==================================================
SUMMARY
==================================================
1. Uttaradit Paper 3:
   - Data & Numerical: Verified from 13 rain gauges (1981–2014) and 7 CMIP6 models (Raw & QDM).
   - Dynamic Pipeline: Executed via `CMIP6Uttaradit/paper3/src/run_pipeline.py`.
   - Bootstrap & Return Levels: All GEV/Gumbel/LP3 extreme value fits and AICc weights verified.
   - Outputs: Tables 1–6 and Figures 1–6 regenerated dynamically without hardcoding.

2. Prachuap Khiri Khan Paper:
   - Data & Numerical: Verified from 12 rain gauges (1981–2014) and 5 CMIP6 models (Raw & QDM).
   - Execution Pipeline: Executed via `CMIP6PrachuapKhiriKhan/run_prachuap_enso_analysis.py`.
   - Statistical Inference: Mann-Whitney U tests, low-n flags, asymmetry, and observational distance metrics evaluated.
   - Cross-Province Contamination Audit: PASSED CLEANLY (0 Uttaradit data leakage).

3. Reproducibility & Manuscript Synchronization:
   - Both sub-projects pass clean checkout unit tests (`python3 -m unittest discover`).
   - Numerical values across reports, tables, figures, and manifests are fully synchronized.
