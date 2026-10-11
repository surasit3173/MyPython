# Changelog

## v1.0.0 (2026-10-05)
- Stage 1 (station data): QC with local-centred robust z-scores; Pettitt (absolute) and relative SNHT
  (median reference) screening with BH-FDR; iterative masking of large station-specific wind breaks;
  4-member FAO-56 PM reference ensemble (wind unit x Angstrom coefficients); elevation, soil-heat-flux
  and wind-masking sensitivity.
- Stage 2 (AgERA5 v2.0): CDS download and point extraction (nearest, bilinear, IDW); input, ETo and
  rainfall accuracy; station x month bias maps; error-series stationarity; Shapley vs first-order
  Taylor attribution; Monte Carlo (LHS) vs Taylor propagation with correlated vs independent errors;
  reference-crop net irrigation requirement with ETo/rainfall error split; cross-validated monthly
  bias adjustment (leave-one-year-block-out, leave-one-station-out).
- Tests: FAO-56 worked examples 8 and 17, homogeneity, metrics, Shapley efficiency, propagation,
  extraction, and an end-to-end Stage 2 run on synthetic data with known imposed errors.
