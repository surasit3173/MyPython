# Uttaradit ETCCDI pipeline: scientific repair record

## Scope and evidence boundary

The supplied Markdown audit was treated as a list of claims to test, not as an
instruction source. The retained source program, the supplied daily data, the
official ETCCDI definitions, Yue and Wang (2004), and deterministic numerical
checks were used to decide each change. The original program and supplied data
remain unmodified outside this task directory.

## Material corrections

| Area | Verified issue in retained program | Implemented correction |
|---|---|---|
| Annual ETCCDI calculation | Valid annual calculation crashed because `finite` was undefined. | Replaced the invalid mask; annual indices now require finite daily values and a 90% complete calendar year. |
| Calendar integrity | Missing dates were not reindexed, so dry/wet spells could span an unrecorded day. | Every station-year is reindexed to its full daily calendar before Rx5day, CDD and CWD are calculated. Incomplete years are explicitly `NaN` and QC-labelled. |
| Daily input QC | Duplicate dates were silently retained and negatives became missing without an error. | Duplicate dates, invalid dates, non-numeric rainfall and negative rainfall now fail fast with a diagnostic. |
| Coordinates | Only one station-ID header spelling was accepted. | Case-normalized `station`, `station_id`, and `stationid` are accepted; station IDs, coordinates and geographic ranges are validated. |
| Network scope | Input intersection could silently reduce the intended study network. | The configured 13 Uttaradit stations are required in observations, coordinates and every CMIP6 input. |
| R95p/R99p | Threshold provenance was not persisted. | Station-specific P95/P99 thresholds are computed from observed wet days (RR >= 1 mm), used unchanged for all model periods, and written to `station_thresholds.csv`. |
| Sen slope CI | The original rank positions disagreed with an independent SciPy Theil-Sen reference. | CI bounds use `scipy.stats.theilslopes` with actual years; a regression test compares the exact result. |
| MK/MMK degeneracy | A constant annual series yielded invalid inference. | Tied/constant series now return S=0, Z=0, p=1 and a `NO_VARIATION` status; MMK detrends before estimating the effective-sample-size correction. |
| CMIP6 discovery | A duplicate model-period file could be selected by filesystem traversal order. | Duplicate model-period matches are fatal; a 21-row model/period manifest is validated and written. |
| Future comparison | Scenario labels and keys were mixed in map filtering. | Scenario keys and display labels are now translated explicitly; future changes use each model's 1995-2014 historical baseline. |
| IDW | A pandas index mismatch could erase station values; maps were not constrained by the supplied provincial boundary. | Values are joined by normalized station ID; the shapefile is loaded, drawn and used to mask map-only IDW cells outside the polygon union. |
| Publication figures | Dense coastal station labels overlapped in provincial maps. | Added deterministic collision-aware label placement with a white halo; this changes only figure annotation, not any numerical result. |
| Reproducibility | No machine-readable configuration, runtime versioning, validation-only run, or output contract existed. | Added locked `AnalysisConfig`, `--validate-only`, execution log, metadata JSON, QC tables, manifest, model-agreement table, Excel workbook and required-output validation. |

## Locked analytical settings

- Observations: 1981-2014; 13 gauges; calendar-year completeness >=90%.
- ETCCDI subset: PRCPTOT, SDII, Rx1day, Rx5day, CDD, CWD, R10mm, R20mm,
  R50mm, R95p, R99p. Wet days are RR >=1 mm.
- Trend analysis: standard MK and detrended effective-sample-size Yue-Wang
  (2004) MMK, two-sided alpha=0.05, Sen slope and 95% interval.
- Future trend window: 2021-2050. Change reference: a model-consistent
  1995-2014 historical climatology.
- Ensemble statements: only descriptive, station-wise seven-model medians and
  model-agreement counts; no pooled ensemble p-value.
- Spatial figures: inverse-distance weighting (power 2) is an interpolated
  visualization of station-referenced change, not downscaling or an independent
  gridded observation.

## Deliberate limits

The supplied files do not establish gauge homogeneity, observation methods,
model-bias-correction provenance, a physical downscaling model, authorship,
funding, ethics approval, or a citable public data repository. These are not
invented. The manuscript labels the corresponding limits or placeholders.

## Source basis

- ETCCDI definitions: https://etccdi.pacificclimate.org/list_27_indices.shtml
- Yue S, Wang CY. Water Resources Management. 2004;18:201-218.
  https://doi.org/10.1023/B:WARM.0000043140.61082.60
- EASR instructions: https://ph01.tci-thaijo.org/index.php/easr/Instructions
