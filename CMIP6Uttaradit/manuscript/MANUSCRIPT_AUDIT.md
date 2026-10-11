# Manuscript Quality and Evidence-Freeze Audit: Uttaradit

## 1. Compliance Verification Checklist
- [x] Baseline period strictly locked to 1995–2014 throughout manuscript.
- [x] All 13 observed stations (`351001`–`351012`, `351201`) accounted for.
- [x] 11 ETCCDI indices definitions consistent with WMO/CLIVAR standards.
- [x] All numerical values trace directly to authoritative production tables.
- [x] QDM bias correction explicitly documented as pre-computed artifacts.
- [x] ANOVA variance decomposition percentages (65–75% GCM, etc.) completely removed.
- [x] Figure 6 explicitly documented as omitted due to lack of code provenance.
- [x] Every active figure (Figures 1–5) cited in text and aligned with captions.
- [x] Every active table (Tables 1–6, Table S1) cited in text.
- [x] No unsupported causal claims or synthetic interpolations.

## 2. Table and Figure Traceability
| Item | Source CSV / Figure | Values Verified | Status |
|---|---|---|---|
| Table 1 | `station_metadata.csv` | Mean Annual 947.71 to 1425.06 mm | PASS |
| Table 2 | `seasonal_climatology.csv` | Wet Season contribution 77.8% (886.85 mm) | PASS |
| Table 3 | `observed_etccdi_1995_2014.csv` | 11 ETCCDI indices network summary | PASS |
| Table 4 | `baseline_sensitivity_comparison.csv` | 1981–2010 vs 1995–2014 threshold sensitivity | PASS |
| Table 5 | `gcm_evaluation_bias.csv` | Raw bias -307.13 mm -> BC bias -69.90 mm (77.2% reduct) | PASS |
| Table 6 | `future_projections_ssp.csv` | SSP2-4.5 (+2.5%) and SSP5-8.5 (+1.2%) near-term | PASS |
| Table S1 | `supplementary_stn_etccdi.csv` | Full station × index matrix | PASS |
| Figures 1–5 | `output/figures/Figure[1-5]*` | 600 DPI PNG + vector PDF | PASS |

**OVERALL MANUSCRIPT AUDIT STATUS: PASS**
