# Validation report: Uttaradit ETCCDI/MMK analysis

## Retained inputs

| Item | SHA-256 or observed structure |
|---|---|
| Original source | `1FEC05F6776F138CAF7F8DF6A9CE420C7CF002AB4FA2BDC2C01F05323B2D46D8` |
| Supplied Markdown | `2B196504AD4628EA640265BB70AF301C4FA57A8768B21771E6CC5E8E0D120864` |
| Supplied EASR template | `597458C8EAF747DBCDF5233BFCDB2121D3D69E3C2606A0388026A4B90F03422C` |
| Observation data | 13 required gauges, daily 1981-01-01 through 2014-12-31 |
| CMIP6 inputs | 7 models x historical/SSP2-4.5/SSP5-8.5 = 21 unique manifest rows |
| Province boundary | `75 pbound.shp`, 9 polygon features, geographic bbox 99.835-101.254 E and 17.103-18.443 N |

## Red/green regression evidence

The test command below was first run against the retained original program and
then unchanged against the revised program.

```powershell
& 'C:\Users\PC\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  -m unittest discover -s tests -p "test_*.py" -v
```

- Original: exit 1; 4 failures and 5 errors, including the `finite` NameError,
  duplicate-date acceptance, coordinate-schema rejection, IDW index misalignment
  and Sen CI mismatch.
- Revised: exit 0; 12 tests passed. Tests cover annual ETCCDI definitions,
  fixed wet-day percentile thresholds, missing calendar days, duplicate dates,
  coordinate schema, CMIP6 ambiguity, MK ties, Sen slope/CI, Yue-Wang
  zero-residual handling, station-keyed IDW and boundary masking.

## Full-data execution

```powershell
& 'C:\Users\PC\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  Uttaradit_ETCCDI_MK_MMK2004_Sen_IDW_Q3_fixed.py `
  --input 'C:\MyPython\CMIP6Uttaradit\Data_Uttaradit' `
  --output 'outputs\full_with_figures'
```

Exit status: 0. The execution log ends in `SUCCESS`; 33 program maps and four
manuscript figures were generated. Runtime versions are preserved in
`outputs/full_with_figures/results/analysis_metadata.json`.

## Independent post-run checks

```powershell
& 'C:\Users\PC\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  qa\independent_output_checks.py outputs\full_with_figures\results
```

Exit status: 0 (`INDEPENDENT_OUTPUT_CHECKS_OK`). This separate checker does not
import the production module. It verifies all output contracts and recomputes
the ACCESS-ESM1-5/SSP2-4.5/station 351001 PRCPTOT historical and future means
from raw daily data, applying the wet-day threshold; both values match the
reported change row.

## Final output contracts met

| Output | Verified count |
|---|---:|
| Observed index rows | 4,862 = 13 x 34 x 11; all annual statuses `OK` |
| Observed trends | 143 = 13 x 11; N=34 |
| Future index rows | 60,060 = 7 x 2 x 13 x 30 x 11; all annual statuses `OK` |
| Future trends | 2,002 = 7 x 2 x 13 x 11; N=30 |
| Future changes | 2,002 = 7 x 2 x 13 x 11 |
| Model agreement rows | 286 = 2 x 13 x 11; seven models available per row |
| Program maps | 33 = 11 observed direction maps + 22 scenario IDW maps |
| Manuscript figures | 4 PNG files, each 400 dpi |

Finite p-values are within [0,1]; every reported Sen slope lies within its
reported 95% interval; future absolute change equals future mean minus baseline
mean in every row. The Excel workbook contains metadata, station coordinates,
thresholds, raw long tables, trends, changes, agreement, QC, and manifest sheets.

## Interpretation guardrails

No unadjusted grid cell is reported as a physical observation. IDW is used only
to display the seven-model station-median change field, with a geographic mask.
Model-agreement fields are descriptive. The many station/index tests are shown
as individual p-values under the requested MK/MMK framework; they are not
recast as a multiplicity-adjusted regional significance claim.
