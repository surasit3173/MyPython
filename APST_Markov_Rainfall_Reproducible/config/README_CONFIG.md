# APST Markov Rainfall Analysis Configuration Guide

This directory contains configuration settings for running the reusable Markov rainfall analysis pipeline.

## Settings Overview

### Project & Region
- `project_name`: Subfolder name under `outputs/` where results will be written.
- `region_name`: Descriptive name of the study area (e.g., Northeastern Thailand).

### Inputs
- `input_rainfall_csv`: Path to daily rainfall CSV file.
- `input_metadata_docx`: Path to station metadata DOCX or CSV file (containing Station ID, Latitude, Longitude, Altitude).

### Date Columns
- `year_col`, `month_col`, `day_col`: Column names for year, month, and day in input CSV.

### Scientific Parameters
- `wet_threshold_mm`: Rain depth threshold (mm/day) classifying a wet day vs dry day. Default = 0.1.
- `analysis_start_year`, `analysis_end_year`: Start and end years of historical records to analyze.
- `temporal_subperiods`: Two sub-periods for assessing temporal stability (e.g., 1961–1990 vs 1991–2020).

### Output Settings
- `figure_dpi`: Resolution of publication figures (default: 300).
- `export_excel`, `export_csv`: Flags to produce summary workbooks and tables.
