# -*- coding: utf-8 -*-
"""
src/io_data.py — Data loaders (rainfall, station coordinates, boundary).

Area-agnostic: takes all paths/column-names from config.py. No study-area
assumptions are hard-coded here.
"""

import os
import pandas as pd
import geopandas as gpd

import config


def load_rainfall():
    """
    Load the daily-rainfall workbook.

    Returns
    -------
    df : DataFrame with added date/year/month/day/water_year columns
    stations : list of str, station id column names (auto-detected as
               all-digit column names — never hard-coded to a station list)
    """
    ext = os.path.splitext(config.RAIN_FILE)[1].lower()
    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(config.RAIN_FILE, sheet_name=config.RAIN_SHEET)
    else:
        df = pd.read_csv(config.RAIN_FILE)

    df.columns = [str(c).strip() for c in df.columns]

    stations = [c for c in df.columns if str(c).isdigit()]
    if len(stations) == 0:
        raise ValueError(
            "No station columns detected in the rainfall file (expected "
            "all-digit column names). Check RAIN_FILE / RAIN_SHEET in config.py."
        )

    df["date"] = pd.to_datetime(df[[config.RAIN_YEAR_COL, config.RAIN_MONTH_COL, config.RAIN_DAY_COL]]
                                 .rename(columns={config.RAIN_YEAR_COL: "year",
                                                   config.RAIN_MONTH_COL: "month",
                                                   config.RAIN_DAY_COL: "day"}))
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["day"] = df["date"].dt.day

    df["water_year"] = df["year"]
    df.loc[df["month"].isin(config.HYDRO_YEAR_ROLLOVER_MONTHS), "water_year"] += 1

    return df, stations


def load_station_coordinates(required_station_ids):
    """
    Load station coordinates and return a DataFrame indexed by station id
    (as string, to match the rainfall column naming), restricted to the
    stations actually present in the rainfall file (never fabricated).

    Raises a clear, itemised error if any station is missing coordinates
    (per "never assume missing data" — we do not silently drop or guess).
    """
    df = pd.read_excel(config.COORD_FILE, sheet_name=config.COORD_SHEET)
    df.columns = [str(c).strip() for c in df.columns]

    required = {config.COORD_STATION_COL, config.COORD_LAT_COL, config.COORD_LON_COL}
    missing_cols = required - set(df.columns)
    if missing_cols:
        raise ValueError(
            f"station_coordinates file is missing required column(s): {missing_cols}. "
            f"Found columns: {df.columns.tolist()}"
        )

    df[config.COORD_STATION_COL] = df[config.COORD_STATION_COL].astype(str).str.strip()
    df = df.set_index(config.COORD_STATION_COL)

    required_station_ids = [str(s) for s in required_station_ids]
    present = [s for s in required_station_ids if s in df.index]
    missing = [s for s in required_station_ids if s not in df.index]

    if missing:
        raise ValueError(
            f"The following rainfall stations have NO coordinate entry and "
            f"cannot be mapped: {missing}. Add them to {config.COORD_FILE} "
            f"before running the GIS module (no coordinates are assumed)."
        )

    out = df.loc[present, [config.COORD_LAT_COL, config.COORD_LON_COL] +
                 ([config.COORD_ALT_COL] if config.COORD_ALT_COL in df.columns else [])].copy()
    out = out.rename(columns={config.COORD_LAT_COL: "latitude", config.COORD_LON_COL: "longitude"})
    return out


def load_boundary():
    """
    Load the study-area boundary shapefile. The working/plotting CRS is
    whatever CRS the shapefile is natively in (auto-detected, never assumed) —
    it must be a projected, metre-based CRS for IDW distance-weighting and
    the scale bar to be metrically correct.
    """
    gdf = gpd.read_file(config.BOUNDARY_SHP)
    if gdf.crs is None:
        raise ValueError(
            f"{config.BOUNDARY_SHP} has no CRS defined (.prj missing/unreadable). "
            "A defined, projected CRS is required for correct IDW distances and scale bar."
        )
    if not gdf.crs.is_projected:
        raise ValueError(
            f"{config.BOUNDARY_SHP} CRS ({gdf.crs}) is geographic, not projected. "
            "Reproject the boundary shapefile to a projected (metre-based) CRS, "
            "e.g. the appropriate UTM zone, before use."
        )
    return gdf
