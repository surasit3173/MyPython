# Figure Forensic Audit Report

- **Station**: Chiang Mai (WMO 48327 / TMD 327501)
- **Period**: 1961–2019
- **Figure Resolution**: 300 DPI
- **Format**: PNG

## Figure Forensic Inspection Summary

| Figure File | Resolution | DPI | Panel Labels | Artwork Titles / Annotations | Overlap / Clipping | Matches Tables | Status |
|---|---|---|---|---|---|---|---|
| `Figure_1_Data_Coverage_Seasonal_Regime.png` | 3000x1200 | 300 | (a), (b) | Valid panel headers | None | PASS | PASS |
| `Figure_2_Depth_Intensity_Indices.png` | 3000x2400 | 300 | (a)–(f) | Valid panel titles & test tags | None | PASS | PASS |
| `Figure_3_Frequency_Spell_Indices.png` | 3000x2400 | 300 | (a)–(e) | Valid panel titles & test tags | None | PASS | PASS |
| `Figure_4_Decadal_Sen_Slopes_CI.png` | 3300x1350 | 300 | (a), (b), (c) | 3-panel unit separation | None | PASS | PASS |
| `Figure_5_Autocorrelation_Diagnostics.png` | 3000x2100 | 300 | (a), (b) | ACF lag 1–10 matrix & Ljung-Box | None | PASS | PASS |

## Verification Notes
1. All figures built strictly from final statistical objects generated in a single locked pipeline execution.
2. Figure 4 redesigned into 3 panels separating physical units (mm/decade, mm/day/decade, days/decade) to prevent unit mixing.
3. Figure 5 upgraded with lag 1–10 ACF matrix highlighting Bartlett bounds (±0.2552) and Ljung–Box p-values.
4. Figures 2 & 3 explicitly tag primary test type (`MK` vs `HR-MK`) on panel annotations.
5. Overall Figure Forensic Gate Status: **PASS**.
