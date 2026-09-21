"""
config.py — Load and expose configuration from config.yaml.

All modules import cfg from here to avoid scattered path literals.
"""
import os
import yaml
from pathlib import Path

# Locate config.yaml relative to this file's parent (project root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _PROJECT_ROOT / "config.yaml"


def load_config(config_path: Path = _CONFIG_PATH) -> dict:
    """Return the parsed YAML configuration dictionary."""
    with open(config_path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


cfg = load_config()

# ─── Convenience shortcuts ───────────────────────────────────────────────────
_raw_path = Path(cfg["paths"]["raw_data"])
RAW_DATA_PATH = _raw_path if _raw_path.is_absolute() else (_PROJECT_ROOT / _raw_path)
OUTPUT_ROOT   = _PROJECT_ROOT / cfg["paths"]["output_root"]
AUDIT_DIR     = _PROJECT_ROOT / cfg["paths"]["audit_dir"]

STATION_ID    = cfg["station"]["id"]
STATION_NAME  = cfg["station"]["name"]
STATION_WMO   = cfg["station"]["wmo_id"]
PROVINCE      = cfg["station"]["province"]
COUNTRY       = cfg["station"]["country"]
LATITUDE      = cfg["station"]["latitude_deg_N"]
LONGITUDE     = cfg["station"]["longitude_deg_E"]
ELEVATION     = cfg["station"]["elevation_m"]

START_YEAR    = cfg["period"]["start_year"]
END_YEAR      = cfg["period"]["end_year"]
N_YEARS       = cfg["period"]["n_years"]

BASELINE_START = cfg["baseline"]["start_year"]
BASELINE_END   = cfg["baseline"]["end_year"]

WET_DAY_THR    = cfg["etccdi"]["wet_day_threshold_mm"]
R10_THR        = cfg["etccdi"]["r10_threshold_mm"]
R20_THR        = cfg["etccdi"]["r20_threshold_mm"]
R50_THR        = cfg["etccdi"]["r50_threshold_mm"]
COMPLETENESS   = cfg["etccdi"]["completeness_threshold"]
SUSPECT_VAL    = cfg["etccdi"]["suspect_value_mm"]

ALPHA          = cfg["trend"]["alpha"]
ACF_SIG_FACTOR = cfg["trend"]["acf_significance_factor"]
ACF_MAX_LAG    = cfg["trend"]["acf_max_lag"]
MK_METHOD_AC   = cfg["trend"]["mk_method_autocorrelated"]
SEN_CI         = cfg["trend"]["sen_slope_ci"]

FDR_METHOD     = cfg["multiple_testing"]["method"]
FDR_ALPHA      = cfg["multiple_testing"]["alpha"]

FIG_DPI        = cfg["figures"]["dpi"]
FIG_FORMAT     = cfg["figures"]["format"]
FIG_FONT       = cfg["figures"]["font_family"]

INDICES = [
    "PRCPTOT", "SDII", "Rx1day", "Rx5day",
    "CDD", "CWD", "R10mm", "R20mm", "R50mm",
    "R95p", "R99p",
]

UNITS = {
    "PRCPTOT": "mm",
    "SDII":    "mm/day",
    "Rx1day":  "mm",
    "Rx5day":  "mm",
    "CDD":     "days",
    "CWD":     "days",
    "R10mm":   "days",
    "R20mm":   "days",
    "R50mm":   "days",
    "R95p":    "mm",
    "R99p":    "mm",
}
