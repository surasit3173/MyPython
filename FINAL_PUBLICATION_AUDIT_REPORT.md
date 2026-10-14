# FINAL PUBLICATION AUDIT REPORT — APST MARKOV RAINFALL ANALYSIS

**Audit Timestamp**: 2026-09-17 00:41:05 UTC
**Locked Manuscript Title**: "Spatial Heterogeneity and Temporal Stability of Daily Rainfall Occurrence Regimes in Northeastern Thailand"
**Target Journal**: Asia-Pacific Journal of Science and Technology (APST)
**Final Status**: **GO — PUBLICATION PACKAGE INTERNALLY VALIDATED**

## 1. Source Data & Provenance Audit
- **Primary Raw CSV**: `data/raw/Observed_Rain_daily_196101_202010_TMD10_raw_Markovchaindataset.csv`
  - SHA256: `5f17abe3935bd43316d120e8d8371ea299cea73f1812e00da8f08975df37bbe3` (Verified match with master source)
  - Dimensions: 21,823 rows x 13 columns (1 January 1961 – 30 September 2020)
- **Primary Metadata**: `data/metadata/Latitude10Sta.docx`
  - SHA256: `ec5c1a7bbe2bb0556cda57048415e1c070aedddc0bb28ebd924de715e47d2351` (10 TMD stations verified)
- **Methodological Reference**: `data/references/Application of Markov chain in daily rainfall in Paraíba-Brazil from 1995-2015.pdf`
  - SHA256: `060ccc9b6e7b0b4b97201f7c2f4691e57f3fa8b7d7e395196cd2516466a8d6b6`

## 2. Validation Gate Status (Gates 0–8)
- **Gate 0 (Source Verification)**: **PASS**
- **Gate 1 (Data Integrity & Missingness Audit)**: **PASS** (Zero invalid/negative values, 97.98% - 99.99% completeness)
- **Gate 2 (State Classification Boundaries)**: **PASS** (Dry: x <= 2.50 mm, Wet: 2.50 < x <= 5.00 mm, Rainy: x > 5.00 mm)
- **Gate 3 (Transition Invariants)**: **PASS** (Probability row sums sum_j P_ij = 1.0; no missing-day bridging)
- **Gate 4 (Markov Order Selection)**: **PASS** (BIC decisively selects Order 2 for all 10 stations, Delta BIC < -100)
- **Gate 5 (Spell Extraction Integrity)**: **PASS** (Contiguous unbridged run lengths, observed/implied ratio = 0.998–1.000)
- **Gate 6 (Entropy Mathematical Bounds)**: **PASS** (State entropy 0.794–1.020 bits, transition entropy 0.741–0.886 bits)
- **Gate 7 (Temporal Stability & Trend Inference)**: **PASS** (Yue-Wang modified MK with FDR control, 1961–2019 annual period, 2020 excluded)
- **Gate 8 (Manuscript & Table/Figure Traceability)**: **PASS** (Zero discrepancy across MASTER_RESULTS_APST_MARKOV.xlsx, Figures 1–5, and Manuscript DOCX)

## 3. Executive Decision
**GO — All publication quality control gates pass without reservation.**
