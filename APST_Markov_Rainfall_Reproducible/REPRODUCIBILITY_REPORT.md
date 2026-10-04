# Reproducibility Report

## 1. Execution Summary
- **Execution Command:** `python scripts/run_full_analysis.py --config config/config_example.yaml`
- **Validation Command:** `python scripts/run_validation.py`
- **Dataset:** Northeastern Thailand Daily Rainfall (10 TMD Stations, 1961–2020)
- **Primary Data Hash:** `5f17abe3935bd43316d120e8d8371ea299cea73f1812e00da8f08975df37bbe3`

## 2. Invariant & Validation Audits
- **Probability Sum Check ($P_{00}+P_{01} = 1.0, P_{10}+P_{11} = 1.0$):** PASSED across all 10 stations.
- **Probability Bound Check ($0 \le P \le 1$):** PASSED across all transition and stationary probabilities.
- **Missing Day Handling:** Spells successfully truncated across NaN records without bridging missing gaps.

## 3. Output Inventory
- `outputs/northeastern_thailand_10sta/Markov_Rainfall_Analysis_Summary.xlsx`
- `outputs/northeastern_thailand_10sta/Table1_Markov_Transitions.csv`
- `outputs/northeastern_thailand_10sta/Table2_Spell_Statistics.csv`
- `outputs/northeastern_thailand_10sta/Table3_Temporal_Stability.csv`
- `outputs/northeastern_thailand_10sta/figures/Figure1_Markov_Transition_Probabilities.png`
- `outputs/northeastern_thailand_10sta/figures/Figure2_Spell_Length_Comparison.png`
- `outputs/northeastern_thailand_10sta/figures/Figure3_Temporal_Stability_P01.png`
- `outputs/northeastern_thailand_10sta/run_provenance.json`
