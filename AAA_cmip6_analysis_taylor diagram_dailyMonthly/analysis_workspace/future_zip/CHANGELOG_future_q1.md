# future_q1.py — Audit & Upgrade Change Log

Full rewrite of `src/future_q1.py` (portable CMIP6 projection workflow).
Backup of the previous version: `src/future_q1_orig_backup.py`.

## Blocking bugs fixed
1. **Coordinate reader too rigid.** Old code required `station_coordinates.csv`
   with columns `station, lat, lon`. Now discovers any `.csv/.xlsx/.xls` table by
   structure and resolves id/lat/lon via English+Thai aliases (handles the real
   `'station '` trailing-space column).
2. **KeyError on national coordinate tables.** Old code iterated every station in
   the coordinate table (128 nationwide) and indexed the observed frame directly,
   crashing on the first absent gauge. Now the **observed file is the station
   authority**: analysed set = observed columns ∩ coordinate table, with a
   fail-loud guard (`< 3` common stations raises).
3. **Silent wrong-baseline risk.** Old observed discovery could pick a
   `bc_*_historical` GCM file as the baseline. Now files with any
   scenario/model/bias token (`ssp`, `rcp`, `bc`, `historical`, `pr_day`, …) are
   excluded from observed candidates; 0 or >1 survivors is reported explicitly.
4. **geopandas hard dependency.** Removed. Boundary is read with the
   dependency-free ESRI reader (`geo.py`); projected (UTM) boundaries are
   converted to lon/lat with a new inverse-UTM transform (`utm_to_lonlat`),
   validated to reproduce the study extent and round-trip to 1e-6°.

## Methodology upgrades (Q1 reviewer concerns)
5. **Multiplicity control.** Added Benjamini–Hochberg FDR per (index, scenario)
   family on all TFPW-MK window trends. Effect on Prachuap: 441 raw-significant
   trends → 1 after FDR. Verified against the BH (1995) worked example.
6. **IPCC-style uncertainty.** Δ maps now hatch cells where ensemble sign
   agreement < 80% (robust-signal convention), replacing the ambiguous
   star/circle-size encoding. Agreement + spread (min/max, IQR) exported.
7. **Residual-bias QC.** New TABLE_09 compares bc-historical index means with the
   observed baseline per station-index-model, justifying use of observed
   thresholds on model series (Prachuap PRCPTOT bias +0.4…+3.2%, median +1.4%).
8. **Documented conventions.** Wet-day ≥1 mm, R95p/R99p from observed wet-day
   percentiles, CDD/CWD/Rx5day within calendar year, bias-corrected preference —
   all stated in every workbook Info sheet.

## Figure / table standard
9. Degree–minute graticule (`99°36′E`, `12°00′N`); scale bar corrected by
   cos(latitude); north arrow; per-map legend (gauge + hatching).
10. Study-area map gains a Thailand locator inset; title/area name derive from
    config + live station count (no hard-coded province or gauge number).
11. Overview heatmap now shows standard Δ% with robust-cell emphasis instead of
    an ad-hoc "scaled intensity".
12. Every workbook has Info + results + Significant sheets; `datetime.utcnow()`
    replaced with timezone-aware UTC.

## Portability / engineering
13. Parquet cube falls back to CSV when no parquet engine is installed.
14. Memory freed between index-map figures (`gc.collect()` + `plt.close`) so the
    full 14-figure run completes in one process.
15. Boundary mask computed once and cached per grid resolution (66 point-in-
    polygon passes → 1).
16. `main.py` gains `--future-area`; area name flows to all figures/tables.

## Validation performed
- **Known-answer regression:** PRCPTOT SSP585 Late = −317.364 mm / −28.802%
  reproduced to 3 decimals (all windows match the prior validated run).
- **Guard tests:** station-authority guard, BH-FDR (BH-1995), sign agreement,
  deg-min formatter, UTM round-trip — all pass.
- **Portability:** ran unchanged on a fixture with 15 different stations, Thai
  file names (`ฝนรายวัน_เพชรบุรี_*.csv`, `พิกัดสถานี.xlsx`), CSV + DATE schema.
- **End-to-end:** `python main.py --future-q1-only` produced 10 tables + 14
  figures (PNG+PDF, 600 dpi) in 167 s.
- **Frozen engine:** `src/mktrend.py` self-test unchanged (PASS).
- `pytest tests/test_future_q1.py` → 10 passed.

## Update: Uttaradit portability run (second real region)
17. **Model name from CMIP6 filename.** `_model_from_name` now parses the
    standard `(bc_)pr_day_<MODEL>_<scenario>` pattern first, so messy folder
    names (e.g. `EC-Earth3_CSV_FILE`) no longer leak into tables/figures.
18. **Duplicate observed copies deduplicated** by (name, size) before the
    multi-candidate warning.
19. **Multiple-shapefile guard:** if the GIS folder holds >1 `.shp`, the first
    (sorted) is used and a warning lists the ignored ones. Boundary filename is
    free-form (`75_pbound.shp` works); `.shx` is not required.
20. **Validated on Uttaradit (13 gauges, 63-station bc network):** geographic
    (lon/lat) boundary branch exercised, all 13 gauges verified inside the real
    province polygon, 10 tables + 14 figures produced with zero further code
    changes. Headline: PRCPTOT SSP585 Late = −34.0% with 7/7 model sign
    agreement; residual bias QC flagged bc-historical ≈ −8.7% vs observed
    (larger than the coastal pilot, reported in TABLE_09).

## Update: nationwide GIS layer + AR6 time-series + per-GCM tables
21. **Nationwide province auto-selection.** The GIS layer is now the 77-province
    `TH_Province` shapefile (UTM 47N, per-record reader + dependency-free DBF).
    The study province is selected automatically as the polygon containing the
    most analysed gauges (bbox pre-filter, then point-in-polygon); degenerate
    clip-frame records are discarded. Selected name is logged from the DBF
    (e.g. "UTTARADIT, 1/77 records"). Neighbouring provinces become thin context
    lines and feed the "Regional setting" inset — one gis/ folder now serves
    every province in Thailand.
22. **Map framing + furniture fixes:** panels framed to the target-province
    bbox (fills ~85%), graticule ticks capped (4/axis) to stop label crowding,
    scale bar shortened and corner-placed by station-emptiness, station labels
    placed with collision avoidance, inset no longer overlaps the map.
23. **Window-membership correction (methodological).** Window means were
    previously computed from an exclusive year→window assignment, so the
    overlap years 2041-2050 were counted in Near only and "Mid" was effectively
    2051-2070. Membership is now range-based (overlap years count in BOTH
    windows). Effect on Uttaradit: PRCPTOT SSP585 Mid −14.2% → −10.0%
    (true 2041-2070); Near and Late are unchanged (no overlap), so the
    Late known-answer regression still holds exactly.
24. **IPCC AR6 products added.** AR6 baseline 1995-2014 and windows 2021-2040 /
    2041-2060 / 2081-2100:
    - FIGURE_15 regional obs + QDM-historical ensemble + SSP245/585 time series
      with AR6 periods shaded (SSP-only, no 2014/2015 splice);
    - FIGURE_16 (x2 scenarios) per-station anomaly small-multiples (shared %
      axes vs AR6 baseline, 5-yr smoothing, regional panel + legend panel);
    - FIGURE_17 seasonal cycle: observed vs QDM-historical range vs the three
      AR6 windows per scenario;
    - TABLE_10 per-station observed vs each GCM's QDM-historical + MME (+bias%),
      full record and AR6 baseline;
    - TABLE_11 per-station rainfall per GCM + MME (mean/median/min/max),
      Δ% vs observed AR6 baseline, sign agreement, across AR6 windows.
    bc-historical daily series now enter the yearly cube (dataset "BC_HIST")
    and a regional monthly cube is accumulated in the same read pass.
