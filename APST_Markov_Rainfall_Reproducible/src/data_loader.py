import os
import re
import csv
import pandas as pd
import numpy as np

try:
    import docx
except ImportError:
    docx = None


def parse_docx_metadata(docx_path):
    """
    Parse station metadata from DOCX file.
    Expected columns or table format: Station ID, Latitude, Longitude, Altitude/Elevation.
    Returns DataFrame with columns: ['station_id', 'latitude', 'longitude', 'elevation']
    """
    if not os.path.exists(docx_path):
        raise FileNotFoundError(f"Metadata file not found: {docx_path}")

    stations = []

    if docx is not None:
        doc = docx.Document(docx_path)
        for table in doc.tables:
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells]
                # Filter out headers
                if len(cells) >= 5 and re.match(r'^\d+$', cells[1]):
                    sta_id = cells[1]
                    lat_str = cells[2]
                    lon_str = cells[3]
                    elev_str = cells[4]

                    lat_val = parse_dms(lat_str)
                    lon_val = parse_dms(lon_str)
                    try:
                        elev_val = float(elev_str)
                    except ValueError:
                        elev_val = np.nan

                    stations.append({
                        'station_id': str(sta_id),
                        'latitude': lat_val,
                        'longitude': lon_val,
                        'elevation': elev_val
                    })
    else:
        # Fallback XML parsing if python-docx not installed (though installed)
        import zipfile
        import xml.etree.ElementTree as ET
        with zipfile.ZipFile(docx_path) as z:
            xml_content = z.read('word/document.xml')
        root = ET.fromstring(xml_content)
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        for tr in root.findall('.//w:tr', ns):
            row = []
            for tc in tr.findall('.//w:tc', ns):
                cell_text = ''.join(tc.itertext()).strip()
                row.append(cell_text)
            if len(row) >= 5 and re.match(r'^\d+$', row[1]):
                sta_id = row[1]
                lat_val = parse_dms(row[2])
                lon_val = parse_dms(row[3])
                try:
                    elev_val = float(row[4])
                except ValueError:
                    elev_val = np.nan
                stations.append({
                    'station_id': str(sta_id),
                    'latitude': lat_val,
                    'longitude': lon_val,
                    'elevation': elev_val
                })

    meta_df = pd.DataFrame(stations)
    return meta_df


def parse_dms(dms_str):
    """Convert degree-minute-second string like 17º27’00” to decimal degrees."""
    if not dms_str:
        return np.nan
    # Extract numbers
    matches = re.findall(r'(\d+)', dms_str)
    if len(matches) >= 3:
        deg, m, s = float(matches[0]), float(matches[1]), float(matches[2])
        return deg + m / 60.0 + s / 3600.0
    elif len(matches) == 2:
        deg, m = float(matches[0]), float(matches[1])
        return deg + m / 60.0
    elif len(matches) == 1:
        return float(matches[0])
    try:
        return float(dms_str)
    except ValueError:
        return np.nan


def load_rainfall_data(csv_path, year_col='YEAR', month_col='MONTH', day_col='DAY', date_col=None, station_cols=None):
    """
    Load daily rainfall CSV data.
    Ensures DatetimeIndex and handles date range.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Rainfall CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path)

    if date_col and date_col in df.columns:
        df['DATE'] = pd.to_datetime(df[date_col])
    elif year_col in df.columns and month_col in df.columns and day_col in df.columns:
        df['DATE'] = pd.to_datetime(df[[year_col, month_col, day_col]].rename(
            columns={year_col: 'year', month_col: 'month', day_col: 'day'}
        ))
    else:
        raise ValueError("Could not construct date column from CSV columns.")

    df = df.sort_values('DATE').reset_index(drop=True)

    if station_cols is None:
        exclude = {year_col, month_col, day_col, 'DATE', 'date', date_col}
        station_cols = [c for c in df.columns if c not in exclude]

    # Ensure station columns are strings for consistency
    rename_dict = {c: str(c) for c in station_cols}
    df = df.rename(columns=rename_dict)
    station_cols = [str(c) for c in station_cols]

    return df, station_cols


def binarize_rainfall(df, station_cols, threshold=0.1):
    """
    Binarize rainfall data into Dry (0) and Wet (1) states.
    Values < threshold -> 0
    Values >= threshold -> 1
    Missing values (NaN) remain NaN.
    """
    binary_df = df[['DATE']].copy()
    for col in station_cols:
        series = df[col]
        # Keep NaN as NaN
        bin_series = pd.Series(np.nan, index=series.index)
        valid_mask = series.notnull()
        bin_series[valid_mask] = (series[valid_mask] >= threshold).astype(int)
        binary_df[col] = bin_series
    return binary_df
