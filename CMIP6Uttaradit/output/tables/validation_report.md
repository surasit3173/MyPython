# Project 2 (Uttaradit) Production Validation Report

- **Timestamp (UTC)**: 2026-09-09T01:22:54.206411+00:00
- **Baseline Period**: 1995–2014 (Locked & Enforced)
- **Observed Stations**: 13 (TMD IDs 351001–351012, 351201)
- **Observed Records**: 12418 daily rows (0% missing)
- **CMIP6 Models**: 7 GCMs (ACCESS-ESM1-5, CESM2, CanESM5, EC-Earth3, FGOALS-g3, MIROC6, MRI-ESM2-0)
- **Scenarios**: SSP2-4.5, SSP5-8.5 (2021–2050)
- **Historical GCM Baseline**: Multi-model mean = 1068.48 mm (QDM bias-corrected)
- **Projected Changes**:
  - SSP2-4.5: Ensemble Mean = +23.60 mm (+2.21% relative to 7-GCM baseline; mean of model deltas = +2.50%)
  - SSP5-8.5: Ensemble Mean = +11.70 mm (+1.10% relative to 7-GCM baseline; mean of model deltas = +1.16%)
- **Bias Reduction**:
  - Aggregate network-mean absolute bias reduction: 77.2% (from -307.13 mm to -69.90 mm)
  - Mean model-specific bias reduction: 73.3% across the 7 GCMs
- **Validation Gates**: Gate 1 PASS, Gate 2 PASS, Gate 3 PASS, Gate 4 PASS
- **QDM Provenance**: Evaluated as pre-computed static artifacts in Data_Uttaradit/ (transformation procedure was not re-executed in this pipeline).
- **ANOVA Uncertainty Decomposition**: Unsupported by repository code; omitted from analysis and manuscript.
