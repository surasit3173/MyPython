# Scientific audit of the Uttaradit CMIP6 precipitation-extreme workflow

## Scope and reproducibility

- Observations: 1981-01-01–2014-12-31, 13 gauges; 7 CMIP6 models; SSP2-4.5 and SSP5-8.5.
- Main corrected contrasts use one baseline (1995–2014) and three non-overlapping 20-year windows (2021–2040, 2041–2060, 2081–2100).
- Annual indices were independently recomputed from the supplied daily CSV files. A wet day is >=1 mm; station-specific R95p/R99p thresholds come from observed wet days during 1981–2014.

## Code and result findings

1. The index formulas are internally consistent with their stated ETCCDI-style definitions. R50mm is a study-specific threshold index rather than a core ETCCDI index.
2. The archived main summaries compare future bias-corrected simulations directly with observations. Because historical bias remains, this estimand can change the magnitude and occasionally the direction of projected change. The manuscript therefore makes the model-consistent future-minus-bias-corrected-historical contrast primary and retains the observed-baseline contrast as sensitivity analysis.
3. The archived 2021–2050 and 2041–2070 windows overlap by ten years. They are valid as climatological summaries but not independent periods. The manuscript uses non-overlapping AR6-style windows.
4. The supplied trend self-test reports a false-positive rate of 0.383 for TFPW-MK under AR(1)=0.6 at nominal alpha=0.05. Consequently, per-window TFPW p-values are not used as confirmatory evidence in the manuscript.
5. The >=80% model sign-agreement flag is a robustness screen (at least 6/7 models), not a statistical significance test. All manuscript captions use that terminology.
6. Percentage changes for R50mm can be unstable because the baseline count is small. Absolute days per year are reported with any percentage only as secondary context.
7. The archive contains bias-corrected files and code that consumes QDM evaluation outputs, but it does not contain the code/provenance needed to verify calibration and out-of-sample validation of the supplied corrected series. The manuscript describes them as supplied bias-corrected/QDM-labelled data and records this as a limitation.
8. Equal station and equal model weights are used. Spatial representativeness and CMIP6 model genealogical dependence are not resolved and are treated as limitations.

## Quantitative checks

- Baseline definition changed the sign for 25 of 66 scenario–window–index combinations and changed the three-class robustness label for 37 combinations.
- Raw versus bias-corrected model-consistent changes retained the sign for 66.9% of model–scenario–window–index cases; the median absolute difference in relative change was 12.1 percentage points.
- Historical skill and residual-bias tables below were calculated independently from daily data; they show that bias correction is most reliable for mean bias/distribution alignment and does not uniformly improve daily timing or RMSE.

### Historical skill summary (median across 7 models × 13 gauges)

| scale | variant | n_model_station_pairs | median_r | q25_r | q75_r | median_rmse | q25_rmse | q75_rmse | median_mae | q25_mae | q75_mae | median_pbias_pct | q25_pbias_pct | q75_pbias_pct | median_nse | q25_nse | q75_nse | median_kge | q25_kge | q75_kge | fraction_lower_rmse | fraction_lower_abs_pbias | fraction_higher_r | fraction_higher_kge |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Daily | Raw | 91 | 0.037 | 0.017 | 0.063 | 10.179 | 7.944 | 10.873 | 4.022 | 3.526 | 4.672 | -21.933 | -58.951 | -0.141 | -0.353 | -0.525 | -0.19 | -0.12 | -0.261 | -0.041 | 0.088 | 0.67 | 0.791 | 0.857 |
| Monthly | Raw | 91 | 0.272 | 0.154 | 0.374 | 103.981 | 93.455 | 112.59 | 73.514 | 67.073 | 80.088 | -21.933 | -58.951 | -0.142 | -0.308 | -0.556 | -0.126 | 0.162 | -0.139 | 0.277 | 0.44 | 0.67 | 0.813 | 0.857 |
| Daily | Bias-corrected | 91 | 0.057 | 0.042 | 0.074 | 11.839 | 9.393 | 13.532 | 4.874 | 4.174 | 5.051 | -8.954 | -16.624 | 7.848 | -0.968 | -1.339 | -0.822 | 0.012 | -0.061 | 0.045 | 0.088 | 0.67 | 0.791 | 0.857 |
| Monthly | Bias-corrected | 91 | 0.441 | 0.34 | 0.492 | 108.734 | 86.328 | 123.069 | 69.585 | 57.833 | 79.24 | -8.954 | -16.628 | 7.83 | -0.344 | -0.589 | -0.161 | 0.385 | 0.267 | 0.446 | 0.44 | 0.67 | 0.813 | 0.857 |

### Residual regional bias by index (1995–2014)

| index | median_regional_bias_pct | q25_regional_bias_pct | q75_regional_bias_pct | max_abs_regional_bias_pct | median_regional_bias_abs |
| --- | --- | --- | --- | --- | --- |
| CDD | 29.64 | 27.01 | 31.11 | 34.98 | 14.12 |
| CWD | -64.12 | -67.09 | -62.9 | 70.22 | -20.6 |
| PRCPTOT | -5.34 | -10.13 | 0.83 | 17.3 | -59.84 |
| R10mm | 12.13 | 5.52 | 19.22 | 21.39 | 3.72 |
| R20mm | 29.79 | 18.78 | 34.99 | 39.55 | 3.58 |
| R50mm | -2.33 | -8.59 | 8.41 | 21.82 | -0.05 |
| R95p | 22.08 | 12.75 | 30.31 | 33.92 | 65.68 |
| R99p | 20.73 | 14.3 | 34.27 | 37.53 | 24.34 |
| Rx1day | -8.2 | -12.65 | -1.7 | 16.33 | -6.32 |
| Rx5day | 14.71 | 11.58 | 20.1 | 24.09 | 21.18 |
| SDII | 18.05 | 16.0 | 20.63 | 21.96 | 1.87 |

## Publication decision

The data support an uncertainty/robustness article, but not a claim that every archived trend or observed-baseline percentage is confirmatory. The APST manuscript is therefore written around baseline sensitivity, residual bias, non-overlapping projection windows, and model sign agreement, with bounded hazard interpretation.