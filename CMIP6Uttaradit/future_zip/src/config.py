"""Central configuration for the ENSO-Rainfall (Prachuap Khiri Khan) pipeline."""
from __future__ import annotations
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAIN_DIR = DATA / "rainfall"
ENSO_DIR = DATA / "enso"
GIS_DIR = DATA / "gis"
OUT = ROOT / "output"
TAB = OUT / "tables"
FIG = OUT / "figures"
LOG = OUT / "logs"
Q1 = OUT / "q1_standard"          # dedicated Q1-ready figure set
QDM_Q1 = OUT / "qdm_q1"           # dedicated QDM-only Q1 figure set
QDM_Q1_TAB = QDM_Q1 / "tables"
QDM_Q1_FIG = QDM_Q1 / "figures"
FUTURE_Q1 = OUT / "future_q1"     # dedicated future projection Q1 figure set
FUTURE_Q1_TAB = FUTURE_Q1 / "tables"
FUTURE_Q1_FIG = FUTURE_Q1 / "figures"
EXTREMES = OUT / "extremes"          # ETCCDI results, kept separate from core
GIS_OUT = OUT / "gis"                # GIS maps, kept separate from core
CHANGEPOINT = OUT / "changepoint"    # regime-shift results, kept separate
for _d in (RAIN_DIR, ENSO_DIR, GIS_DIR, TAB, FIG, LOG, Q1, QDM_Q1, QDM_Q1_TAB,
           QDM_Q1_FIG, FUTURE_Q1, FUTURE_Q1_TAB, FUTURE_Q1_FIG,
           EXTREMES, GIS_OUT,
           CHANGEPOINT):
    _d.mkdir(parents=True, exist_ok=True)

# ---- input -----------------------------------------------------------------
RAIN_FILE = RAIN_DIR / "Observed_Rain_daily_198101_201412_Prachuap_Khiri_Khan.xlsx"
RAIN_SHEET = "in"
COORD_FILE = RAIN_DIR / "station_coordinates.xlsx"

# Station set is DATA-DRIVEN, not hardcoded: by default it is the intersection of
# the station columns present in the rainfall file and the stations listed in the
# coordinate table. Drop in another region's rainfall file + a coordinate table
# (national tables are fine) and the correct gauges are picked up automatically.
# To pin an explicit set instead, assign a list to STATION_IDS_OVERRIDE.
STATION_IDS_OVERRIDE = None
COORD_ID_COL = "station"
COORD_LAT_COL = "latitude"
COORD_LON_COL = "longitude"


def _auto_station_ids():
    import pandas as pd
    cols = pd.read_excel(RAIN_FILE, sheet_name=RAIN_SHEET, nrows=0).columns
    rain_ids = {int(c) for c in cols if str(c).strip().isdigit()}
    try:
        co = pd.read_excel(COORD_FILE)
        co.columns = [str(c).strip().lower() for c in co.columns]
        coord_ids = {int(s) for s in co[COORD_ID_COL].dropna()}
        ids = sorted(rain_ids & coord_ids)
        if ids:
            return ids
    except Exception:                                 # noqa: BLE001
        pass
    return sorted(rain_ids)                            # fall back to all rain cols


try:
    STATION_IDS = STATION_IDS_OVERRIDE or _auto_station_ids()
except Exception:                                     # noqa: BLE001
    # last-resort fallback so import never crashes; replaced on first real run
    STATION_IDS = [500001, 500002, 500003, 500004, 500005, 500006,
                   500007, 500008, 500009, 500201, 500202, 500301]

# Areal-series construction method: 'mean' (unweighted areal mean, default,
# assumption-light) or 'thiessen' (Voronoi-area weighted, uses coordinates).
AREAL_METHOD = "mean"

START_YEAR, END_YEAR = 1981, 2014

# Seasons
WET_MONTHS = [5, 6, 7, 8, 9, 10]        # May-Oct
DRY_MONTHS = [11, 12, 1, 2, 3, 4]       # Nov-Apr  (cross-year)

# ENSO thresholds + NOAA endpoints are loaded from an EXTERNAL, editable file
# (data/noaa_sources.json) so no NOAA source or definition is fixed in code.
# The same constant names are exposed, so the rest of the pipeline is untouched.
ALPHA = 0.05

import json as _json


def _load_noaa_sources():
    defaults = {
        "oni_urls": [
            "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt",
            "https://origin.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"],
        "nino34_urls": [
            "https://www.cpc.ncep.noaa.gov/products/GODAS/multiora/index/mnth.ersstv5.clim19912020.nino_current.txt",
            "https://www.cpc.ncep.noaa.gov/data/indices/ersst5.nino.mth.91-20.ascii",
            "https://origin.cpc.ncep.noaa.gov/data/indices/ersst5.nino.mth.91-20.ascii"],
        "nino34_psl_urls": [
            "https://psl.noaa.gov/gcos_wgsp/Timeseries/Data/nino34.long.anom.data"],
        "dmi_urls": [
            "https://psl.noaa.gov/gcos_wgsp/Timeseries/Data/dmi.had.long.data",
            "https://psl.noaa.gov/gcos_wgsp/Timeseries/Data/dmi.long.data"],
        "psl_missing": -99.99,
        "dmi_cache_name": "dmi.had.long.data",
        "thresholds": {"oni_elnino": 0.5, "oni_lanina": -0.5,
                       "oni_min_consecutive": 5, "dmi_pos": 0.4, "dmi_neg": -0.4},
    }
    try:
        with open(DATA / "noaa_sources.json", encoding="utf-8") as fh:
            user = _json.load(fh)
        for k, v in user.items():
            if not k.startswith("_"):
                defaults[k] = v
    except FileNotFoundError:
        pass
    return defaults


_NOAA = _load_noaa_sources()
ONI_URLS = _NOAA["oni_urls"]
NINO34_URLS = _NOAA["nino34_urls"]
NINO34_PSL_URLS = _NOAA["nino34_psl_urls"]
DMI_URLS = _NOAA["dmi_urls"]
PSL_MISSING = _NOAA["psl_missing"]
DMI_CACHE_NAME = _NOAA["dmi_cache_name"]
_TH = _NOAA["thresholds"]
ONI_ELNINO = _TH["oni_elnino"]
ONI_LANINA = _TH["oni_lanina"]
ONI_MIN_CONSECUTIVE = _TH["oni_min_consecutive"]
DMI_POS = _TH["dmi_pos"]
DMI_NEG = _TH["dmi_neg"]

# When INCLUDE_IOD is True the pipeline also downloads the Dipole Mode Index and
# runs Rainfall ~ Nino3.4 vs ~ DMI vs ~ Nino3.4+DMI. False = lean ENSO-only.
INCLUDE_IOD = True

HTTP_TIMEOUT = 30
HTTP_RETRIES = 3

# Local cache of the NOAA files (real data retrieved from the URLs above).
# Used as an offline fallback when the network is unreachable, so the pipeline
# is fully reproducible without fabricating any values. Refreshed automatically
# whenever a live download succeeds.
ONI_CACHE = ENSO_DIR / "oni.ascii.txt"
NINO34_CACHE = ENSO_DIR / "nino34.ascii.txt"
NINO34_PSL_CACHE = ENSO_DIR / "nino34.long.anom.data"
DMI_CACHE = ENSO_DIR / DMI_CACHE_NAME

# ---- GIS / spatial layer (reusable: repoint these for any study area) -------
BOUNDARY_SHP = GIS_DIR / "boundary.shp"
GIS_COORD_FILE = GIS_DIR / "station_coordinates.xlsx"
UTM_CENTRAL_MERIDIAN = 99.0          # UTM zone 47N central meridian (Thailand W)
# Display name for the study area, shown on figures/tables. Change per region.
STUDY_AREA_NAME = os.environ.get("TFPW_STUDY_AREA", "Prachuap Khiri Khan")
# (COORD_ID_COL / COORD_LAT_COL / COORD_LON_COL are defined once near the top)

# ---- ETCCDI extreme-precipitation indices ----------------------------------
ETCCDI_BASE_PERIOD = (START_YEAR, END_YEAR)   # R95p/R99p percentile base period
# 3-month ONI season -> centre month (DJF centred on Jan ... NDJ centred on Dec)
ONI_SEASON_CENTER = {
    "DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
    "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12,
}

# Plot style
DPI = 600                 # publication raster resolution (PNG); PDF is vector
GEV_OUT = OUT / "gev_idf"  # Observed_Trend_GEV_IDF results, kept separate
GEV_OUT.mkdir(parents=True, exist_ok=True)
FONT_FAMILY = "Times New Roman"
# Colorblind-safe (Okabe-Ito)
C_ELNINO = "#D55E00"
C_LANINA = "#0072B2"
C_NEUTRAL = "#999999"
C_MAIN = "#000000"
C_ACCENT = "#009E73"

# Dedicated external QDM evaluation source. Overridable by env var or CLI.
QDM_SOURCE_DIR = Path(
    os.environ.get("TFPW_QDM_SOURCE", r"C:\MyPython\AAAAAAA Bias QDM 28sta")
)

FUTURE_SOURCE_DIR = Path(
    os.environ.get(
        "TFPW_FUTURE_SOURCE",
        r"C:\MyPython\QDM 12sta\AAAAAAA run_all_gcmsv25\gcm_data\CSV_Phetchaburi - Prachuap Khiri Khan",
    )
)
FUTURE_GIS_DIR = Path(
    os.environ.get(
        "TFPW_FUTURE_GIS",
        r"C:\MyPython\QDM 12sta\CMIP6_Future_Trend_Framework\examples\gis",
    )
)
FUTURE_FRAMEWORK_OUTPUT_DIR = Path(
    os.environ.get(
        "TFPW_FUTURE_FRAMEWORK_OUTPUT",
        r"C:\MyPython\QDM 12sta\CMIP6_Future_Trend_Framework\outputs",
    )
)
