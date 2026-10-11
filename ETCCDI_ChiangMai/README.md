# ETCCDI Extreme Precipitation Analysis Pipeline — Chiang Mai, Thailand (1961–2019)

A provenance-controlled, fully reproducible Python computational pipeline for analyzing long-term trends and autocorrelation diagnostics across 11 Expert Team on Climate Change Detection and Indices (ETCCDI) extreme precipitation indices.

---

## 1. Project Purpose & Overview
This project performs an end-to-end forensic quality control, annual ETCCDI index calculation, trend analysis, residual autocorrelation diagnostics, multiple testing control (BH-FDR), publication figure generation, and Word manuscript synthesis for daily rainfall observations at Chiang Mai, Thailand.

## 2. Station Metadata & Data Period
- **Station Name**: Chiang Mai Synoptic Station
- **TMD Station ID**: 327501
- **WMO Station ID**: 48327
- **Province / Country**: Chiang Mai, Thailand
- **Coordinates**: 18.77°N, 98.97°E | Elevation: 312.0 m a.s.l.
- **Analysis Period**: 1961–2019 (59 calendar years, 21,549 daily observations)

## 3. Authoritative Raw Data Location & Hash
- **Raw CSV File**: `data/raw/Observed_Rain_daily_complete_1961_2019_327501_wmo48327_ChiangMai.csv`
- **SHA-256 Hash**: `0a9e0e4e797049d44730a5fa9274f2e552d21ac99240588097a34ba4cb95d35b`

## 4. One-Command Pipeline Execution
Run the entire pipeline end-to-end with a single command:
```bash
python run_pipeline.py --config config.yaml
```

## 5. Environment Setup & Dependency Installation
Create and activate the environment using the locked dependencies:
```bash
# Using Conda / Mamba
conda env create -f environment.yml
conda activate etccdi_chiangmai

# Or using Pip
pip install -r requirements-lock.txt
```

## 6. How to Adapt to Another Station
This pipeline is fully modular and reusable for any other meteorological station. To run the analysis for a new station:
1. Place the new station daily CSV in `data/raw/`.
2. Create a new configuration file (e.g. `config_station2.yaml`).
3. Update station metadata (`id`, `wmo_id`, `name`, `latitude_deg_N`, etc.) and `sha256` hash in the new YAML file.
4. Execute:
   ```bash
   python run_pipeline.py --config config_station2.yaml
   ```

## 7. Statistical Methodology Summary
- **Quantile Estimator**: Hyndman-Fan Type 8 (`np.percentile(..., method='median_unbiased')`) for wet days (P ≥ 1.0 mm) during 1981–2010 baseline.
- **Cross-Year Windowing**: Rolling 5-day totals (Rx5day) and spell lengths (CDD, CWD) are calculated continuously across year-end boundaries.
- **Residual Detrending**: Robust Theil-Sen detrending (`y - (slope * x + intercept)`) prior to autocorrelation calculation.
- **Autocorrelation & Primary Test Selection**: Residual ACF at Lags 1–10 and Ljung-Box Q(5) test. Hamed-Rao Modified MK is selected if any ACF 1–5 exceeds Bartlett bounds (±0.2552) or Ljung-Box p < 0.05; otherwise Ordinary MK is retained.
- **Trend Magnitudes**: Sen's slope estimator with 95% confidence intervals (`scipy.stats.theilslopes`).
- **Multiple Testing Control**: Benjamini-Hochberg False Discovery Rate (BH-FDR) at α = 0.05.

## 8. Directory Structure & Key Outputs
- `data/`: Raw daily CSV and validated daily dataset with QC flags.
- `src/`: Modular Python source code for QC, ETCCDI, trends, figures, and manuscript generation.
- `output/data/`: Annual ETCCDI index master tables.
- `output/tables/`: Excel tables for data quality, descriptive statistics, trend analysis, and autocorrelation.
- `output/figures/`: 300 DPI publication figures (PNG format).
- `output/manuscript/`: Complete Q3 Word manuscript DOCX.
- `audit/`: Independent verification reports, Ljung-Box cross-checks, numerical consistency manifests, and reproducibility logs.

## 9. Reproducibility & Quality Assurance
The pipeline contains built-in automated independent verification and dual-run reproducibility checks. Rerunning `python run_pipeline.py --config config.yaml` verifies 100% byte-for-byte and numerical identity across all statistical outputs.
