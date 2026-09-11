# Delivery index

Run: `prachuap-khiri-khan_e8bf031b3ba0`

## Primary artifacts

- `runs/prachuap-khiri-khan_e8bf031b3ba0/Article_1_Method_Comparison.docx`
- `runs/prachuap-khiri-khan_e8bf031b3ba0/Article_2_Prachuap_Rainfall_Trends.docx`
- `runs/prachuap-khiri-khan_e8bf031b3ba0/Prachuap_Rainfall_Trend_Results.xlsx`
- `runs/prachuap-khiri-khan_e8bf031b3ba0/run_manifest.json`

## Reproducible implementation

- `src/rainfall_trends/`: input validation, aggregation, statistics, bootstrap, simulation, pipeline, figures, and manuscript generation
- `tests/`: 23 passing unit/integration tests
- `configs/prachuap.json`: exact production configuration
- `configs/template_long.json`: reusable long-format template for another area
- `validation/independent_checks.py`: comparison with `pymannkendall` and independent BH implementation
- `research-record.md`: frozen hypotheses, evidence, deviations, and final verdict

## Headline interpretation

- No network-level period-method test survived BH.
- Dry network Sen slope was positive (+3.46 mm/year), but its MK q-value was 0.248.
- Seven method-specific station decisions represented only three station-period combinations at stations 500002 and 500006.
- Simulations showed substantial short-record miscalibration for MK, HR-MMK-3, and TFPW-MK under positive persistence; PW-MK was calibrated but often low-powered.
- The defensible conclusion is an inconclusive network-wide monotonic trend with localized, method-sensitive dry-season increases that require independent confirmation.
