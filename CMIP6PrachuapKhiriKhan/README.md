# Portable Hydro-Climate Trend Analysis Pipeline (v3.0.0)

## 1. Purpose
This package provides a modernized, fail-closed, and fully portable Python analysis pipeline for non-parametric trend detection in observed precipitation series. It implements **Yue & Wang (2004) AR(1) Modified Mann-Kendall** as the primary publication-grade method, with **Standard Mann-Kendall** as the reference benchmark and **Trend-Free Pre-Whitening (TFPW-MK)** as a sensitivity check.

## 2. Directory Structure
```
CMIP6PrachuapKhiriKhan_PORTABLE/
├── README.md                       # Execution & portability documentation
├── config.yaml                     # Portable configuration file
├── requirements.txt                # Dependency specifications
├── main.py                         # Fail-closed pipeline entry point
├── src/
│   ├── io/                         # Data loading & table export
│   ├── validation/                 # Fail-closed gate assertions
│   ├── statistics/                 # Yue & Wang AR(1) MMK & Sen slope core
│   ├── trends/                     # Trend execution orchestration
│   ├── aggregation/                # Seasonal & annual aggregators
│   ├── plotting/                   # Decoupled visualization generator
│   └── provenance/                 # Cryptographic run manifest generator
├── tests/                          # Complete unit test suite
├── data/                           # User input rainfall & metadata CSV files
├── output/                         # Production tables, figures, manifests, & logs
└── docs/                           # Evidence freeze & run reports
```

## 3. Requirements & Installation
Python 3.9+ with `numpy`, `pandas`, `scipy`, `pyyaml`, and `matplotlib`.

Install dependencies:
```bash
py -3 -m pip install -r requirements.txt
```

## 4. Input Data Format
Input datasets must be placed in `data/`:
1. `data/Observed_Rain_daily_198101_201412_PrachuapKhiriKhan.csv` (contains `YEAR`, `MONTH`, `DAY`, and station columns).
2. `data/station_coordinates_PrachuapKhiriKhan.csv` (contains `Station`, `Lat`, `Lon`).

See `data/README.md` for full schema requirements and fail-closed rules.

## 5. Configuration
All project settings are controlled via `config.yaml`:
- Data file paths (relative to project root).
- Station count and analysis period.
- Alpha significance levels.

## 6. Execution Commands

### Run Unit Test Suite
```bash
py -3 -m unittest discover tests/
```

### Run Production Analysis Pipeline
```bash
py -3 main.py
```

## 7. Output Description
Execution generates:
- `output/tables/trend_results.csv`: Detailed results for Annual, Wet Season, and Dry Season.
- `output/tables/station_summary.csv`: Station-level summary table.
- `output/tables/validation_report.md`: Fail-closed gate validation summary.
- `output/figures/station_sen_slopes.png`: Publication Sen's slope summary figure.
- `output/manifests/run_manifest.json`: Cryptographic audit trail with SHA256 hashes.
- `output/logs/pipeline.log`: Execution log file.

## 8. Portability & Reuse Instructions
To adapt this codebase to another province or research region:
1. Copy the repository folder to a new location.
2. Place the new area's daily rainfall CSV and station metadata CSV into `data/`.
3. Update `config.yaml` (`data.observed_csv`, `data.station_coords_csv`, `data.expected_station_count`, `data.analysis_period`, and `project.name`).
4. Execute `py -3 main.py`. No source code edits required.

## 9. Statistical Methods & Fail-Closed Behavior
- **Yue & Wang (2004) AR(1) MMK:** Corrects for lag-1 persistence using analytical variance scaling $n/n_s^* = 1 + 2 \frac{r_1^{n+1} - n r_1^2 + (n-1)r_1}{n(r_1-1)^2}$.
- **Fail-Closed:** Missing files, invalid schemas, duplicate dates, or missing observations trigger an immediate hard stop (`StopBlockedException`). No synthetic fallback or dummy data generation.
