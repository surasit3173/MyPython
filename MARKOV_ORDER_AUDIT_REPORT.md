# MARKOV ORDER AUDIT REPORT

**Gate 3 & Gate 4 Audit Status**: **PASS**

## Order Selection Summary
Model order selection was performed comparing Order 0 (independent), Order 1, and Order 2 Markov chains for each station over 1961–2019 using log-likelihood, AIC, and Bayesian Information Criterion (BIC).

- **BIC Decision Rule**: For all 10 stations, BIC decisively favors an **Order 2 Markov chain** ($\Delta \text{BIC} < -100$).
- **Scientific Interpretation**: Higher-order statistical dependence is statistically present in the daily state sequence across Northeastern Thailand. Operational Order 1 representations summarize major single-step persistence ($P_{DD}, P_{RR}$) while acknowledging higher-order memory.

| Station ID | N_eff (Transitions) | BIC Order 1 | BIC Order 2 | Delta BIC (Ord2 - Ord1) | Selected Model (BIC) |
|---|---|---|---|---|---|
| 353201 | 21,545 | 24706.3 | 24463.3 | -243.0 | Order 2 |
| 354201 | 21,545 | 24862.8 | 24462.9 | -399.9 | Order 2 |
| 356201 | 21,543 | 26054.8 | 25386.6 | -668.3 | Order 2 |
| 357201 | 21,086 | 25954.0 | 24926.7 | -1027.3 | Order 2 |
| 381201 | 21,486 | 23094.0 | 22764.9 | -329.1 | Order 2 |
| 403201 | 21,545 | 22199.2 | 22091.0 | -108.3 | Order 2 |
| 405201 | 20,879 | 23152.5 | 22665.5 | -487.0 | Order 2 |
| 407501 | 21,545 | 24995.6 | 24429.7 | -565.9 | Order 2 |
| 431201 | 21,531 | 22746.9 | 22524.8 | -222.1 | Order 2 |
| 432201 | 21,545 | 24970.1 | 24570.0 | -400.1 | Order 2 |
