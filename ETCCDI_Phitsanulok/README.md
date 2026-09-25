# ETCCDI Extreme Precipitation Analysis — Phitsanulok, Thailand

## Overview

A fully reproducible research pipeline for computing, analysing, and reporting
long-term trends in 11 ETCCDI extreme precipitation indices at WMO Station 48378
(Phitsanulok, Thailand) over the period 1961–2019.

## Publication

**Title**: Long-Term Trends in Extreme Precipitation Characteristics at Phitsanulok,
Thailand: A 59-Year ETCCDI-Based Analysis with Autocorrelation-Aware Trend Detection

**Station**: WMO 48378 | TMD 378201 | Phitsanulok, Thailand (16.78°N, 100.27°E)

**Period**: 1961–2019 (59 years, 21,549 daily observations)

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run full pipeline from raw CSV
python main.py

# Validate all outputs
python final_consistency_check.py
```

## Data

Input file: `C:\MyPython\2Station\Observed_Rain_daily_complete_1961_2019_378201_wmo48378_Phitsanulok.csv`

Format: YEAR, MONTH, DAY, 378201 (daily precipitation in mm)

## Methods

- 11 ETCCDI indices per Zhang et al. (2011)
- Wet-day threshold: ≥ 1.0 mm/day
- Percentile baseline: 1981–2010
- Trend: Mann–Kendall + Theil–Sen slope
- Autocorrelation: ACF lags 1–10; Hamed–Rao if needed (not required for this dataset)
- Multiple testing: Benjamini–Hochberg FDR (11 simultaneous tests)
- Significance: α = 0.05

## Key Results

| Metric | Value |
|--------|-------|
| Data completeness | 100% (59/59 years) |
| P95 baseline | 49.895 mm |
| P99 baseline | 82.116 mm |
| Significant trends (raw p < 0.05) | 0/11 |
| Significant trends (FDR p < 0.05) | 0/11 |
| Max lag-1 ACF | 0.1813 (below threshold 0.2604) |
| MK method applied | Ordinary Mann–Kendall (all 11 indices) |

## Project Structure

```
ETCCDI_Phitsanulok/
├── data/raw/               # (input CSV path in config.yaml)
├── src/
│   ├── config.py           # Configuration loader
│   ├── data_qc.py          # Data quality control
│   ├── etccdi.py           # ETCCDI index computation
│   ├── statistics.py       # Descriptive statistics
│   ├── autocorrelation.py  # ACF diagnostics
│   ├── trend.py            # MK, Sen's slope, FDR
│   ├── sensitivity.py      # Robustness analysis
│   ├── figures.py          # Publication figures
│   ├── tables.py           # Manuscript tables
│   └── manuscript.py       # DOCX/MD generation
├── output/
│   ├── data/               # annual_ETCCDI_1961_2019.csv
│   ├── statistics/         # trend, ACF, sensitivity XLSX
│   ├── tables/             # TABLE_01–TABLE_06, TABLE_S1–TABLE_S5
│   ├── figures/            # FIGURE_01–FIGURE_06.png
│   └── manuscript/         # Manuscript_Q3_ETCCDI_Phitsanulok.docx
├── audit/                  # DATA_AUDIT_REPORT.md, QA reports
├── config.yaml
├── requirements.txt
├── main.py
└── final_consistency_check.py
```

## Dependencies

See `requirements.txt`. Key packages:
- pandas, numpy, scipy, matplotlib
- pymannkendall (MK and Hamed–Rao tests)
- python-docx (manuscript generation)
- openpyxl (Excel output)
- pyyaml (configuration)

## Reproducibility

All computations are deterministic. Running `python main.py` from the project root
reproduces all outputs identically. No random seeds are required as no stochastic
methods are employed.

## Citation

If using this analysis or pipeline, please cite the associated manuscript
(see output/manuscript/ directory) and the following key methodological references:

- Zhang et al. (2011) — ETCCDI indices
- Mann (1945); Kendall (1975) — Mann–Kendall test
- Sen (1968) — Theil–Sen slope
- Hamed & Rao (1998) — Modified MK
- Benjamini & Hochberg (1995) — FDR correction
