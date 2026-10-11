# AgERA5 v2.0 precipitation and ETo evaluation — Northeast Thailand (v1.0.0)

Reproducible pipeline for the manuscript *Assessing AgERA5 v2.0 precipitation and reference
evapotranspiration for agricultural water planning on the Khorat Plateau, Northeast Thailand*.

Design: application chain and extraction comparison after Soulis et al. (2025, *Atmosphere* 16, 263);
input accuracy and error propagation after Tran et al. (2026, *Hydrol. Sci. J.* 71, 654–672).

## Data
`data/raw/` holds the TMD monthly archive (`TMD_data1961-2010.xls`), the wind archive
(`Wind_sp1970-2010.xls`) and station coordinates (`station_coords15sta.csv`). Raw files are never modified.
Seven synoptic stations with complete Penman–Monteith inputs are analysed for 1979–2007.

## Run
```bash
pip install -r requirements.txt
python -m etoeval.cli stage1   --config config.yaml           # station-only analysis (runs offline)
python -m etoeval.cli download --config config.yaml --dry-run # inspect CDS requests first
python -m etoeval.cli download --config config.yaml           # needs a CDS account and ~/.cdsapirc
python -m etoeval.cli extract  --config config.yaml           # -> data/agera5_station_daily.csv
python -m etoeval.cli stage2   --config config.yaml           # AgERA5 evaluation
python -m pytest -q                                           # tests
```

### Before downloading
1. Open the AgERA5 page on the CDS, select *version 2.0*, one variable and one day, click
   **Show API request code**, and check the variable names in `config.yaml → agera5.requests`
   (in particular `reference_evapotranspiration`). Flux variables take no `statistic` in v2.0.
2. Test with one year first: `--years 1979 1979`, then `extract`; the extractor stops with an error if
   medians fall outside physical limits (unit or variable mismatch).

## Assumptions that must be stated in the paper
- Wind unit of the TMD archive is undocumented → both m s⁻¹ and knots are carried as ensemble members.
- Anemometer height assumed 10 m (WMO synoptic standard); station elevation 150 m where not supplied
  (effect on mean ETo ±0.25 % for 0–300 m).
- Rs is estimated from sunshine (FAO-56 and Glover–McCulloch Ångström coefficients); no pyranometer data.
- Actual vapour pressure from mean RH (FAO-56 Eq. 19) because RHmax/RHmin are not archived.
- Wind segments with a relative SNHT break (BH-FDR q < 0.05, |shift| ≥ 25 %) are masked (shorter
  segment), not adjusted; results with unmasked wind are reported as sensitivity.

## Outputs
`outputs/stage1|stage2/{tables,figures}` and `MANIFEST.json` (versions, config hash, file list).
Figures carry no in-figure titles; captions go in the manuscript.
