# APST Reusable Markov Rainfall Analysis Package (v1.0)

A standalone, fully reproducible, configuration-driven Python package for daily rainfall Markov chain analysis, occurrence regimes, spell statistics, and spatial/temporal stability.

## Features
- **Data Validation & Cleaning**: Robust parsing of TMD multi-station daily rainfall CSVs and station metadata (coordinates/elevation).
- **Markov Chain Engine**: First-order and second-order Markov transition matrices ($P_{00}, P_{01}, P_{10}, P_{11}$), stationary distributions ($\pi_0, \pi_1$), and AIC/BIC model order selection.
- **Spell Duration Analysis**: Observed dry/wet spell lengths, mean/median/max statistics, geometric distribution fitting, and gap-isolated spell extraction.
- **Spatial & Temporal Stability**: Sub-period comparison (e.g., 1961–1990 vs 1991–2020), Z-tests, Chi-square tests for shift detection, and spatial coefficient of variation ($CV$).
- **One-Command Reproducibility**: Run the complete analysis, generate publication-ready figures (PNG/PDF @ 300 DPI), and export summary Excel/CSV tables in a single step.

## Quick Start (One-Command Execution)

```bash
# Install dependencies
pip install -r requirements.txt

# Run complete analysis
python scripts/run_full_analysis.py --config config/config_example.yaml

# Run scientific validation suite
python scripts/run_validation.py
```

## Folder Structure

```
APST_Markov_Rainfall_Reproducible/
├── README.md
├── LICENSE.txt
├── requirements.txt
├── pyproject.toml
├── SOURCE_MANIFEST.yaml
├── REPRODUCIBILITY_REPORT.md
├── config/
│   ├── config_example.yaml
│   └── README_CONFIG.md
├── data/
│   ├── raw/
│   ├── metadata/
│   ├── examples/
│   └── references/
├── src/
│   ├── data_loader.py
│   ├── markov_engine.py
│   ├── spell_analysis.py
│   ├── spatial_temporal.py
│   └── exporters.py
├── scripts/
│   ├── run_full_analysis.py
│   └── run_validation.py
├── tests/
├── outputs/
├── docs/
└── manuscript/
```
