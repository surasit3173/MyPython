# CMIP6 Uttaradit Extreme Precipitation Analysis (Portable Publication Package)

## Overview
This package contains the fully reproducible, portable analysis pipeline for:
**"Observed Baseline Climatology, Extreme Precipitation Indices, and CMIP6 Projections over Uttaradit Province, Thailand"**
Prepared for Scopus Q1–Q2 publication.

## Key Scientific Parameters
- **Study Domain**: Uttaradit Province, Northern Thailand (13 TMD stations).
- **Authoritative Baseline Period**: 1995–2014 (Locked & Enforced).
- **Indices**: 11 ETCCDI indices (PRCPTOT, SDII, Rx1day, Rx5day, CDD, CWD, R10mm, R20mm, R50mm, R95p, R99p).
- **Climate Models**: 7 CMIP6 GCMs (ACCESS-ESM1-5, CESM2, CanESM5, EC-Earth3, FGOALS-g3, MIROC6, MRI-ESM2-0).
- **Scenarios**: SSP2-4.5 and SSP5-8.5 for near-term future (2021–2050).
- **Bias Correction**: Quantile Delta Mapping (QDM) (documented as pre-computed static artifacts).
- **Excluded Claims**: ANOVA variance decomposition (65–75% GCM, etc.) is unsupported by repository code and excluded.

## Directory Structure
- `config/config.yaml`: Authoritative configuration file.
- `Data_Uttaradit/`: Station coordinates, daily rainfall observations (1981–2014), and 7 GCM raw and QDM data.
- `data/gis/`: Natural Earth administrative boundary GeoJSON for Thailand and Uttaradit Province.
- `src/indices/`: Core 11 ETCCDI indices computation engine (`etccdi.py`).
- `src/validation/`: Validation gates and hard-stop enforcement (`gates.py`).
- `src/plotting/`: 600 DPI publication figure generation script (`figure_generator.py`).
- `tests/`: Automated unit and validation gate tests.
- `output/tables/`: Authoritative generated CSV tables (Tables 1 to 6, Table S1).
- `output/figures/`: Publication figures (Figures 1 to 5 in 600 DPI PNG and vector PDF), metadata, captions, IDW parameters.
- `output/manifests/`: Execution manifest (`run_manifest_project2.json`).
- `manuscript/`: Complete Markdown and Word DOCX manuscripts and audit reports.

## Execution Instructions
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run test suite:
   ```bash
   python -m unittest discover tests/
   ```
3. Execute master production pipeline:
   ```bash
   python main.py
   ```
4. Regenerate manuscript:
   ```bash
   python generate_manuscript_draft.py
   ```
5. Verify portability and package:
   ```bash
   python package_and_verify.py
   ```
