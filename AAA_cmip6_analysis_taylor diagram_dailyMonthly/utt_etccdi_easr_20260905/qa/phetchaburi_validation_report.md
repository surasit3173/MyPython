# Phetchaburi ETCCDI analysis validation report

## Overall assessment: Share with caveats; coordinate confirmation required before submission

The Phetchaburi run is reproducible and internally consistent for publication
analysis after the caveats below are reported. The study area is restricted to
the 13 Phetchaburi gauges (`465xxx`) and the `PRV_CODE=76` province boundary;
the neighbouring Prachuap Khiri Khan gauges are not included.

The numerical pipeline passes its automated and independent checks. However,
one coordinate-provenance issue must be resolved before a manuscript is
submitted: station `465002` at the supplied coordinate (12.75°N, 99.98°E)
falls outside the selected `PRV_CODE=76` polygon by approximately 1.2 km. The
station is retained in the station-level statistics and in the reproducible
IDW input exactly as supplied; no coordinate was silently changed. Confirm the
authoritative coordinate (or the authoritative boundary) and rerun the maps
before treating the spatial figures as final.

## Dataset and grain

- Source archive: `CSV_Phetchaburi - Prachuap Khiri Khan.rar`
- Observed rainfall: 1981-01-01 to 2014-12-31, 12,418 daily records, 13 stations
- CMIP6 bias-corrected files: 7 models × historical/SSP2-4.5/SSP5-8.5 = 21 files
- Future period: 2021-2050
- Model-consistent baseline: 1995-2014
- Boundary: `39_amarea_phetchaburi.shp`, `PRV_CODE=76`, 8 district polygons
- Coordinate extent of selected gauges: 12.67-13.22°N, 99.70-100.07°E
- Final rerun output: `outputs/phetchaburi_final2`

## Checks performed

1. Required columns, date parsing, daily duplicate detection and station-key
   matching.
2. Explicit station filter to the 13 Phetchaburi gauges.
3. CMIP6 manifest uniqueness and date coverage.
4. Annual completeness, index row counts, p-value ranges, Sen confidence
   interval ordering and absolute-change identity.
5. Boundary-masked IDW figure generation and workbook ZIP integrity.
6. Independent checker: `qa/validate_phetchaburi_output.py`.

## Findings

- Observed dates have no duplicates, invalid dates or missing rainfall values.
- All 21 CMIP6 files are present and unique. The CanESM5, CESM2 and FGOALS-g3
  files use a 365-day/no-leap convention: the omitted dates are February 29
  only. The minimum annual completeness is 99.726776%, above the configured
  90% gate; this calendar convention must be stated in Methods.
- Empty trailing spreadsheet-export columns were removed only when completely
  empty; the final manifest reports 28 CMIP6 station columns rather than 29.
- The analysis produced 143 observed trend rows, 2,002 future trend rows and
  2,002 future-change rows, with 33 map figures.
- One observed row (`465002`, SDII) has no wet day in 2010. Standard MK and Sen
  slope use 33 valid annual values; Yue-Wang MMK is correctly reported as
  `IRREGULAR_ANNUAL_YEARS` rather than assigned an artificial p-value.
- A point-in-polygon check places 12 of 13 selected gauges inside the selected
  province polygon. `465002` is outside the polygon by approximately 1.2 km
  using the supplied coordinate file; this is a provenance/QC issue, not a
  missing-data result.

## Calculation spot-checks

- `Absolute_change = Future_mean - Baseline_mean`: verified for every future
  model/scenario/station/index row.
- All finite p-values are within [0, 1].
- All reported Sen slopes lie inside their reported 95% confidence intervals.
- Duplicate keys are absent at the observed and future trend grains.
- Workbook `Phetchaburi_Trend_Analysis.xlsx` passes ZIP integrity testing.

## Visualization review

The 33 generated PNG figures in the final rerun were inspected at high
resolution. The province boundary is drawn and the IDW field is masked outside
it; the interior is not left blank by a station-only grid. Station markers,
units and a deterministic label layout are shown. IDW is an interpolated
depiction of station-referenced model-median change, not an observed or
dynamically downscaled gridded product.

## Coordinate sensitivity run

A separate, clearly labelled sensitivity run moved only station `465002` to
12°47'59.6"N, 99°58'00.1"E, the location listed in a published station table
([ASEAN J. Sci. Tech. Report, Table 1](https://ph02.tci-thaijo.org/index.php/tsujournal/article/download/253507/170531/934730)).
All tabular statistical outputs were byte-identical to the supplied-coordinate
run, as expected because coordinates do not enter the station-level ETCCDI
calculations. The IDW fields and station-label positions changed locally, so
the sensitivity figures are evidence of spatial-coordinate sensitivity only;
they are not adopted as the primary result until the authoritative coordinate
file is confirmed.

## Required caveats for a manuscript

- State that some CMIP6 inputs use a 365-day/no-leap calendar and that the
  omitted February 29 dates were retained as a documented calendar convention.
- State that one observed SDII station-year is undefined because no wet day was
  recorded in 2010; its MMK p-value is not estimated.
- Treat station-level p-values as individual tests unless a prespecified
  multiplicity procedure is added; do not describe them as regional causal
  evidence.
- Describe IDW values outside the station convex hull as extrapolation and do
  not interpret them as independently validated gridded observations.
- Resolve the `465002` coordinate/boundary mismatch before final spatial-map
  publication. If the coordinate is corrected, rerun the full pipeline and
  archive the revised coordinate file, configuration and output checksum.

## Reproducibility command

```powershell
python portable_runner.py `
  --config config_phetchaburi.json `
  --input "phetchaburi_data\CSV_Phetchaburi - Prachuap Khiri Khan" `
  --output outputs\phetchaburi_full
```
