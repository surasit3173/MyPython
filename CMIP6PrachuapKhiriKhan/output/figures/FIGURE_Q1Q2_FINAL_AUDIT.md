# FIGURE QUALITY-CONTROL & Q1–Q2 COMPLIANCE AUDIT REPORT

**Project 1:** Observed Rainfall Variability and Trend Detection (Prachuap Khiri Khan, Thailand)  
**Standard Target:** Scopus Q1–Q2 Journals (Atmospheric Research / Theoretical and Applied Climatology)  
**Figure Directory:** `output/figures/`  
**Execution Status:** ALL 5 FIGURES REDESIGNED & VALIDATED  

---

## 1. FIGURE SPECIFICATION & INVENTORY MATRIX

| Figure Number | Raster File (600 DPI) | Vector File (PDF) | Display Dimensions | Layout / Visual Grammar | Status |
|---|---|---|---|---|---|
| **Figure 1** | `Figure1_study_area_stations.png` | `Figure1_study_area_stations.pdf` | 10.5 × 7.2 in | Dual-panel: (a) Regional Thailand context; (b) Station network with MSL elevations, scale bar, and North arrow | **PASS** |
| **Figure 2** | `Figure2_IDW_mean_annual_rainfall.png` | `Figure2_IDW_mean_annual_rainfall.pdf` | 11.0 × 6.8 in | Dual-panel: (a) 2D IDW surface clipped to provincial polygon + gauge overlays; (b) Ranked annual & seasonal bars | **PASS** |
| **Figure 3** | `Figure3_annual_rainfall_variability.png` | `Figure3_annual_rainfall_variability.pdf` | 11.0 × 8.0 in | Dual-panel: (a) Network mean time series with ±1 SD ribbon; (b) Standardized precipitation anomaly heatmap | **PASS** |
| **Figure 4** | `Figure4_trend_method_comparison.png` | `Figure4_trend_method_comparison.pdf` | 11.5 × 7.2 in | Multi-panel: (a) Paired dumbbell plot (MK vs YW vs TFPW); (b) Sen's slopes; (c) Variance correction ratio | **PASS** |
| **Figure 5** | `Figure5_autocorrelation_effect.png` | `Figure5_autocorrelation_effect.pdf` | 11.5 × 7.2 in | Quad-panel: (a) Detrended r1 lollipop; (b) Analytical YW curve; (c) Var(S) scaling; (d) Z_MK vs Z_YW scatter | **PASS** |

---

## 2. INVERSE DISTANCE WEIGHTING (IDW) METHODOLOGICAL AUDIT (FIGURE 2)

- **Grid Resolution:** 0.005° (~500 m), 345 × 184 matrix.
- **Polygon Clipping:** Strictly masked to Prachuap Khiri Khan administrative polygon via Natural Earth 10m boundaries.
- **Power Parameter:** $p = 2.0$ (standard inverse distance squared).
- **LOOCV Cross-Validation:**
  - Mean Absolute Error (MAE): `86.14 mm/year`
  - Root Mean Square Error (RMSE): `107.33 mm/year`
  - Mean Bias Error (MBE): `-9.57 mm/year`
- **Documentation:** Recorded in `output/figures/IDW_parameters.txt`.

---

## 3. SCIENTIFIC VISUAL INTEGRITY COMPLIANCE CHECKLIST

- **[PASS] No Oversized Figure Titles:** All main axes omit oversized chart junk titles; concise subpanel tags `(a)`, `(b)`, `(c)` used.
- **[PASS] Perceptual Colormaps:** Used perceptually uniform colormaps (`YlGnBu` for rainfall gradients; `RdBu` diverging for standardized anomalies).
- **[PASS] High Resolution:** All raster outputs rendered at 600 DPI with anti-aliasing.
- **[PASS] Vector Formats Provided:** PDF versions generated with editable vectors and fonts embedded (Type 42 TrueType).
- **[PASS] Strict Numerical Concordance:** 100% agreement with `output/tables/trend_results.csv` and `output/tables/station_summary.csv`.
- **[PASS] Canonical Station IDs:** All station labels strictly formatted with 6 digits (`500001` to `500301`).

```text
=======================================================
  FIGURE Q1–Q2 VISUAL & STATISTICAL AUDIT — PASS
=======================================================
```
