# Input Data Format Specification

## 1. Rainfall CSV File
The input CSV file must contain daily rainfall observations. Accepted column formats:
- Option A: Standard TMD format with `YEAR`, `MONTH`, `DAY` columns followed by station ID columns (e.g. `353201`, `354201`).
- Option B: A single `DATE` column (format `YYYY-MM-DD`) followed by station columns.

### Missing Values
- Missing observations may be represented as empty strings, `NaN`, `NA`, or `-9999`.
- The pipeline automatically treats missing days without bridging across missing record gaps.

## 2. Station Metadata DOCX / CSV
Station coordinates and elevation can be supplied as a DOCX document containing a table or a CSV file:
- Columns: Station ID, Latitude (degree), Longitude (degree), Altitude/Elevation (meters).
- Degrees can be formatted as DMS strings (e.g. `17º27’00”`) or decimal degrees (e.g. `17.45`).
