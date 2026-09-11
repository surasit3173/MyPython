# Input Data Specifications & User Placement Instructions

## 1. Required Input Data Schema
This analysis pipeline requires two input files placed in the `data/` directory:

1. **Observed Daily Rainfall CSV:** (`data/Observed_Rain_daily_198101_201412_PrachuapKhiriKhan.csv` or user-specified path in `config.yaml`).
   - **Required Date Columns:** `YEAR`, `MONTH`, `DAY` (integers).
   - **Required Station Columns:** Station identifiers as numeric or string column headers (e.g., `500001`, `500002`).
   - **Units:** Daily rainfall depth in millimeters (mm).
   - **Quality Control:** 0 duplicate dates, 0 missing observation values, full daily coverage for the configured analysis period.

2. **Station Metadata CSV:** (`data/station_coordinates_PrachuapKhiriKhan.csv` or user-specified path in `config.yaml`).
   - **Required Columns:** `Station` (ID matching rainfall CSV headers), `Lat` (Latitude), `Lon` (Longitude).

## 2. Fail-Closed Enforcement Rules
- If any input file is missing $\to$ **ERROR & STOP** (`StopBlockedException`).
- If required columns are absent $\to$ **ERROR & STOP**.
- If duplicate dates or missing values exist $\to$ **ERROR & STOP**.
- **No synthetic fallback, no artificial interpolation, no dummy research data.**

## 3. How to Run on a New Study Area
To adapt this pipeline for another province or research area:
1. Place the new observed daily rainfall CSV and station coordinates CSV into the `data/` directory.
2. Edit `config.yaml` to update `observed_csv`, `station_coords_csv`, `expected_station_count`, `analysis_period`, and `project.name`.
3. Execute `py -3 main.py`.
