# Table & Figure Cross-Consistency Audit: Uttaradit

## 1. Table Consistency Matrix
- Table 1 (Metadata) matches coordinates and elevations in `station_coordinates_Uttaradit.csv`.
- Table 2 (Seasonal) annual totals equal Table 1 mean annual rainfall for all 13 stations.
- Table 3 (ETCCDI) network averages match column means of Table S1 (`supplementary_stn_etccdi.csv`).
- Table 4 (Sensitivity) thresholds and means match `baseline_sensitivity_comparison.csv`.
- Table 5 (GCM Evaluation) matches raw and QDM annual sums from `bc_pr_day_*` files.
- Table 6 (Projections) matches future 2021–2050 deltas across all 7 GCMs.

## 2. Figure Consistency Matrix
- Figure 1: 13 stations correctly positioned in WGS84 CRS matching Table 1.
- Figure 2: IDW discrete points match Table 1 mean annual rainfall; seasonal bars match Table 2.
- Figure 3: Heatmap matrix values match Table S1; boxplots match Table 3 ranges.
- Figure 4: GCM bar chart and dumbbell plot values exactly match Table 5.
- Figure 5: GCM projection bars and boxplots match Table 6.
- Figure 6: Omitted per evidence freeze audit.

**OVERALL TABLE & FIGURE AUDIT STATUS: PASS**
