"""
future_q1.py
============
Reusable CMIP6 future-precipitation projection workflow (Q1-ready).

Design goals
------------
1. **Observed rainfall file is the station authority.** The analysed gauge set is
   the intersection of the station columns in the observed file and the stations
   listed in the coordinate table. Drop in Phetchaburi (15 gauges) or any other
   region and the correct gauges are picked up with no code change.
2. **Flexible inputs.** Observed / future daily tables and the coordinate table
   may be .csv, .xlsx or .xls, with Thai or English file names. Detection is by
   *structure*, not by file name.
3. **Dependency-free GIS.** The boundary shapefile is read with a minimal ESRI
   reader; projected (UTM) boundaries are converted to lon/lat internally, so no
   geopandas/pyproj install is required.
4. **Publication-grade figures/tables.** 600 dpi PNG + vector PDF, degree-minute
   graticule, IPCC-style ensemble-agreement hatching, BH-FDR multiplicity
   control, self-documenting Info + Significant workbook sheets.

Only the folders in the CLI/config need editing to move to a new study area.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
from matplotlib.path import Path as MplPath

from . import config as C
from . import figures as FIG
from .geo import read_polygon_shapefile, lonlat_to_utm
from .mktrend import tfpw_mk

log = logging.getLogger("future_q1")

# --------------------------------------------------------------------------- #
# Analysis conventions (documented in every workbook Info sheet)
# --------------------------------------------------------------------------- #
WET_THRESHOLD = 1.0                      # wet day >= 1 mm (ETCCDI convention)
FUTURE_WINDOWS = {"Near": (2021, 2050), "Mid": (2041, 2070), "Late": (2071, 2100)}
# IPCC AR6 assessment periods (used by the time-series figures + TABLE_10/11)
AR6_BASELINE = (1995, 2014)
AR6_WINDOWS = {"Near-term": (2021, 2040), "Mid-term": (2041, 2060),
               "Long-term": (2081, 2100)}
AR6_ORDER = ["Near-term", "Mid-term", "Long-term"]
WINDOW_ORDER = ["Near", "Mid", "Late"]
SCENARIO_ORDER = ["ssp245", "ssp585"]
MIN_TREND_YEARS = 8                       # minimum points for a window trend test
AGREEMENT_ROBUST = 0.80                   # >=80% model sign agreement -> "robust"
MIN_STATION_MATCHES = 3                   # guard: fewer -> not a station table

DATE_TRIPLE_COLS = ("YEAR", "MONTH", "DAY")
DATE_SINGLE_COL_CANDIDATES = ("DATE", "Date", "date", "วันที่")

# Column-name aliases for the coordinate table (English + Thai).
COORD_ID_ALIASES = ("station", "station_id", "stationid", "id", "code",
                    "รหัสสถานี", "สถานี", "รหัส")
COORD_LAT_ALIASES = ("lat", "latitude", "y", "ละติจูด")
COORD_LON_ALIASES = ("lon", "long", "lng", "longitude", "x", "ลองจิจูด")

# Tokens that mark a file as a GCM/bias-corrected product (never observed).
MODEL_TOKENS = ("ssp", "rcp", "bc", "bias", "qdm", "corrected", "cmip",
                "historical", "pr_day", "r1i1p1", "r11i1p1")
BC_TOKENS = ("bc", "bias", "qdm", "corrected")


@dataclass(frozen=True)
class IndexSpec:
    key: str
    unit: str
    description: str


INDEX_SPECS = [
    IndexSpec("PRCPTOT", "mm", "Annual total wet-day precipitation"),
    IndexSpec("SDII", "mm/day", "Simple daily intensity index"),
    IndexSpec("Rx1day", "mm", "Annual maximum 1-day precipitation"),
    IndexSpec("Rx5day", "mm", "Annual maximum consecutive 5-day precipitation"),
    IndexSpec("CDD", "days", "Max consecutive dry days (within calendar year)"),
    IndexSpec("CWD", "days", "Max consecutive wet days (within calendar year)"),
    IndexSpec("R10mm", "days", "Days with precipitation >= 10 mm"),
    IndexSpec("R20mm", "days", "Days with precipitation >= 20 mm"),
    IndexSpec("R50mm", "days", "Days with precipitation >= 50 mm"),
    IndexSpec("R95p", "mm", "Annual total precip on days > observed-baseline p95"),
    IndexSpec("R99p", "mm", "Annual total precip on days > observed-baseline p99"),
]
INDEX_KEYS = [s.key for s in INDEX_SPECS]
INDEX_UNIT_MAP = {s.key: s.unit for s in INDEX_SPECS}
INDEX_DESC_MAP = {s.key: s.description for s in INDEX_SPECS}

OVERLAP_FRAMEWORK_MAP = {
    "PRCPTOT": "RainTotal_Annual", "SDII": "SDII", "Rx1day": "Rx1day",
    "Rx5day": "Rx5day", "CDD": "CDD", "CWD": "CWD",
    "R95p": "R95pTOT", "R99p": "R99pTOT",
}


# --------------------------------------------------------------------------- #
# Geodesy: WGS84 UTM (northern zone) inverse, to complement geo.lonlat_to_utm
# --------------------------------------------------------------------------- #
_A = 6378137.0
_F = 1.0 / 298.257223563
_E2 = _F * (2 - _F)
_K0 = 0.9996
_FE = 500000.0
_E1 = (1 - np.sqrt(1 - _E2)) / (1 + np.sqrt(1 - _E2))


def utm_to_lonlat(east, north, lon0_deg: float):
    """WGS84 UTM easting/northing (m, northern zone) -> lon/lat (deg).

    Inverse of geo.lonlat_to_utm (Snyder 1987). Vectorised.
    """
    E = np.asarray(east, float) - _FE
    N = np.asarray(north, float)
    M = N / _K0
    mu = M / (_A * (1 - _E2 / 4 - 3 * _E2**2 / 64 - 5 * _E2**3 / 256))
    phi = (mu
           + (3 * _E1 / 2 - 27 * _E1**3 / 32) * np.sin(2 * mu)
           + (21 * _E1**2 / 16 - 55 * _E1**4 / 32) * np.sin(4 * mu)
           + (151 * _E1**3 / 96) * np.sin(6 * mu))
    e2p = _E2 / (1 - _E2)
    C1 = e2p * np.cos(phi) ** 2
    T1 = np.tan(phi) ** 2
    Nn = _A / np.sqrt(1 - _E2 * np.sin(phi) ** 2)
    R1 = _A * (1 - _E2) / (1 - _E2 * np.sin(phi) ** 2) ** 1.5
    D = E / (Nn * _K0)
    lat = phi - (Nn * np.tan(phi) / R1) * (
        D**2 / 2
        - (5 + 3 * T1 + 10 * C1 - 4 * C1**2 - 9 * e2p) * D**4 / 24
        + (61 + 90 * T1 + 298 * C1 + 45 * T1**2 - 252 * e2p - 3 * C1**2) * D**6 / 720)
    lon = np.radians(lon0_deg) + (
        D - (1 + 2 * T1 + C1) * D**3 / 6
        + (5 - 2 * C1 + 28 * T1 - 3 * C1**2 + 8 * e2p + 24 * T1**2) * D**5 / 120
    ) / np.cos(phi)
    return np.degrees(lon), np.degrees(lat)


def _looks_projected(bbox) -> bool:
    """Heuristic: geographic coords are within +/-180/90; UTM metres are large."""
    xmin, ymin, xmax, ymax = bbox
    return max(abs(xmin), abs(xmax), abs(ymin), abs(ymax)) > 1000.0


def _read_shp_records(path: Path):
    """Minimal ESRI polygon reader, per record.

    Returns (records, file_bbox); records = list of dicts
    {"rings": [(x, y) arrays], "bbox": (xmin, ymin, xmax, ymax), "npoints": int}.
    """
    import struct
    with open(path, "rb") as f:
        data = f.read()
    if struct.unpack("<i", data[32:36])[0] != 5:
        raise ValueError(f"{path.name}: expected polygon shapefile (type 5)")
    file_bbox = struct.unpack("<4d", data[36:68])
    records, pos, n = [], 100, len(data)
    while pos + 8 <= n:
        _, clen = struct.unpack(">2i", data[pos:pos + 8])
        pos += 8
        rec_end = pos + clen * 2
        if struct.unpack("<i", data[pos:pos + 4])[0] == 5:
            rbbox = struct.unpack("<4d", data[pos + 4:pos + 36])
            nparts = struct.unpack("<i", data[pos + 36:pos + 40])[0]
            npts = struct.unpack("<i", data[pos + 40:pos + 44])[0]
            pp = pos + 44
            parts = struct.unpack(f"<{nparts}i", data[pp:pp + 4 * nparts])
            pp += 4 * nparts
            xy = np.frombuffer(data[pp:pp + 16 * npts], dtype="<f8").reshape(-1, 2)
            bnd = list(parts) + [npts]
            rings = [(xy[bnd[i]:bnd[i + 1], 0].copy(), xy[bnd[i]:bnd[i + 1], 1].copy())
                     for i in range(nparts)]
            records.append({"rings": rings, "bbox": rbbox, "npoints": npts})
        else:
            records.append({"rings": [], "bbox": None, "npoints": 0})
        pos = rec_end
    return records, file_bbox


def _read_dbf_names(path: Path) -> list[dict]:
    """Minimal DBF reader (TIS-620/Thai aware). One dict of fields per record."""
    import struct
    try:
        with open(path, "rb") as f:
            d = f.read()
    except FileNotFoundError:
        return []
    nrec = struct.unpack("<I", d[4:8])[0]
    hdr = struct.unpack("<H", d[8:10])[0]
    rsz = struct.unpack("<H", d[10:12])[0]
    fields, pos = [], 32
    while pos < len(d) and d[pos] != 0x0D:
        name = d[pos:pos + 11].split(b"\x00")[0].decode("ascii", errors="replace")
        fields.append((name, d[pos + 16]))
        pos += 32
    out = []
    for i in range(nrec):
        p = hdr + i * rsz
        rec, off, vals = d[p:p + rsz], 1, {}
        for name, ln in fields:
            raw = rec[off:off + ln]
            try:
                vals[name] = raw.decode("tis-620", errors="replace").strip()
            except LookupError:                              # noqa: PERF203
                vals[name] = raw.decode("utf-8", errors="replace").strip()
            off += ln
        out.append(vals)
    return out


def _record_display_name(attrs: dict, idx: int) -> str:
    for key in ("PROV_NAME", "PROV_NAMT", "NAME", "NAME_1", "ADM1_EN", "PROVINCE"):
        if attrs.get(key):
            return attrs[key]
    return f"record {idx}"


# --------------------------------------------------------------------------- #
# GIS container + flexible coordinate loading
# --------------------------------------------------------------------------- #
@dataclass
class GisData:
    rings_lonlat: list          # TARGET province rings [(lon, lat) arrays]
    bounds: tuple               # target (lon_min, lat_min, lon_max, lat_max)
    stations: pd.DataFrame      # columns: station, lat, lon
    lon0: float                 # UTM central meridian used
    neighbors: list = None      # context rings from other records (may be empty)
    province_name: str = ""     # DBF name of the selected polygon (audit)
    _grid_cache: dict = None    # {grid_n: (gx, gy, mask)} filled lazily

    def grid_mask(self, grid_n: int):
        """(gx, gy, inside_mask) for the TARGET polygon, cached per grid_n."""
        if self._grid_cache is None:
            self._grid_cache = {}
        if grid_n not in self._grid_cache:
            x0, y0, x1, y1 = self.bounds
            gx, gy = np.meshgrid(np.linspace(x0, x1, grid_n),
                                 np.linspace(y0, y1, grid_n))
            mask = _mask_inside(gx, gy, _ring_paths(self.rings_lonlat))
            self._grid_cache[grid_n] = (gx, gy, mask)
        return self._grid_cache[grid_n]


def _find_col(cols, aliases) -> str | None:
    low = {str(c).strip().lower(): c for c in cols}
    for a in aliases:
        if a.lower() in low:
            return low[a.lower()]
    # loose contains-match as a fallback (e.g. 'station ' handled by strip already)
    for a in aliases:
        for lc, orig in low.items():
            if a.lower() in lc:
                return orig
    return None


def _read_any_table(path: Path, nrows: int | None = None) -> pd.DataFrame:
    suf = path.suffix.lower()
    if suf == ".csv":
        return pd.read_csv(path, nrows=nrows)
    if suf in {".xlsx", ".xls"}:
        return pd.read_excel(path, nrows=nrows)
    raise ValueError(f"Unsupported table format: {path.suffix}")


def _discover_coord_file(gis_dir: Path) -> Path:
    """Find a station coordinate table (csv/xlsx/xls) by structure, not name."""
    for path in sorted(gis_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".csv", ".xlsx", ".xls"}:
            continue
        try:
            head = _read_any_table(path, nrows=5)
        except Exception:                                    # noqa: BLE001
            continue
        cols = list(head.columns)
        if (_find_col(cols, COORD_ID_ALIASES)
                and _find_col(cols, COORD_LAT_ALIASES)
                and _find_col(cols, COORD_LON_ALIASES)):
            return path
    raise FileNotFoundError(
        f"No station coordinate table (needs id+lat+lon columns) found in {gis_dir}")


def _load_stations(gis_dir: Path) -> pd.DataFrame:
    path = _discover_coord_file(gis_dir)
    df = _read_any_table(path)
    id_c = _find_col(df.columns, COORD_ID_ALIASES)
    lat_c = _find_col(df.columns, COORD_LAT_ALIASES)
    lon_c = _find_col(df.columns, COORD_LON_ALIASES)
    out = pd.DataFrame({
        "station": df[id_c].astype(str).str.strip(),
        "lat": pd.to_numeric(df[lat_c], errors="coerce"),
        "lon": pd.to_numeric(df[lon_c], errors="coerce"),
    }).dropna(subset=["lat", "lon"])
    out = out[out["station"].str.len() > 0].drop_duplicates("station")
    log.info("coordinate table: %s (%d stations)", path.name, len(out))
    return out.reset_index(drop=True)


def load_gis(gis_dir: Path | str, station_hint: pd.DataFrame | None = None) -> GisData:
    """Load boundary + stations. Multi-polygon boundary files (e.g. a nationwide
    77-province layer) are supported: the polygon containing the most analysed
    stations is selected as the study boundary; the rest become context lines.

    station_hint : optional DataFrame(station, lat, lon) restricting selection to
    the analysed gauges. Without it, all stations in the coordinate table vote.
    """
    gis_dir = Path(gis_dir)
    shps = sorted(gis_dir.rglob("*.shp"))
    if not shps:
        raise FileNotFoundError(f"No boundary .shp found in {gis_dir}")
    shp = shps[0]
    if len(shps) > 1:
        log.warning("Multiple .shp files in %s; using %s. Others ignored: %s",
                    gis_dir, shp.name, [p.name for p in shps[1:]])
    records, file_bbox = _read_shp_records(shp)
    attrs = _read_dbf_names(shp.with_suffix(".dbf"))
    lon0 = getattr(C, "UTM_CENTRAL_MERIDIAN", 99.0)
    projected = _looks_projected(file_bbox)

    def to_lonlat_bbox(b):
        if not projected:
            return b
        lon, lat = utm_to_lonlat([b[0], b[2]], [b[1], b[3]], lon0)
        return (float(lon[0]), float(lat[0]), float(lon[1]), float(lat[1]))

    def rings_lonlat(rec):
        if not projected:
            return [(np.asarray(xs, float), np.asarray(ys, float))
                    for xs, ys in rec["rings"]]
        return [utm_to_lonlat(xs, ys, lon0) for xs, ys in rec["rings"]]

    stations = _load_stations(gis_dir)
    voters = station_hint if station_hint is not None and len(station_hint) else stations
    pts = voters[["lon", "lat"]].to_numpy(float)

    # candidates: real polygons only; drop clip-frame rectangles (<=5 points
    # spanning ~the full file bbox)
    fx0, fy0, fx1, fy1 = file_bbox
    fw, fh = fx1 - fx0, fy1 - fy0
    cands = []
    for i, rec in enumerate(records):
        if not rec["rings"]:
            continue
        b = rec["bbox"]
        near_frame = (rec["npoints"] <= 5
                      and (b[2] - b[0]) > 0.95 * fw and (b[3] - b[1]) > 0.95 * fh)
        if near_frame:
            continue
        cands.append((i, rec))
    if not cands:
        raise ValueError(f"{shp.name}: no usable polygon records")

    if len(cands) == 1:
        ti, target = cands[0]
        others = []
    else:
        counts = []
        for i, rec in cands:
            bb = to_lonlat_bbox(rec["bbox"])
            pad = 0.02
            inbox = ((pts[:, 0] >= bb[0] - pad) & (pts[:, 0] <= bb[2] + pad)
                     & (pts[:, 1] >= bb[1] - pad) & (pts[:, 1] <= bb[3] + pad))
            if not inbox.any():
                counts.append((0, rec["npoints"], i, rec))
                continue
            rl = rings_lonlat(rec)
            inside = np.zeros(int(inbox.sum()), bool)
            for p in _ring_paths(rl):
                inside |= p.contains_points(pts[inbox])
            counts.append((int(inside.sum()), rec["npoints"], i, rec))
        counts.sort(key=lambda t: (-t[0], t[1]))
        best_n, _, ti, target = counts[0]
        if best_n == 0:
            raise ValueError(
                f"{shp.name}: no polygon contains any analysed station - wrong "
                f"boundary file for this region?")
        others = [(i, rec) for i, rec in cands if i != ti]

    name = _record_display_name(attrs[ti] if ti < len(attrs) else {}, ti)
    t_rings = rings_lonlat(target)
    lon_all = np.concatenate([r[0] for r in t_rings])
    lat_all = np.concatenate([r[1] for r in t_rings])
    bounds = (float(lon_all.min()), float(lat_all.min()),
              float(lon_all.max()), float(lat_all.max()))

    # neighbours = records whose bbox touches the (slightly expanded) target bbox
    exp = (bounds[0] - 0.15, bounds[1] - 0.15, bounds[2] + 0.15, bounds[3] + 0.15)
    neigh = []
    for i, rec in others:
        bb = to_lonlat_bbox(rec["bbox"])
        if bb[0] <= exp[2] and bb[2] >= exp[0] and bb[1] <= exp[3] and bb[3] >= exp[1]:
            neigh.extend(rings_lonlat(rec))
    log.info("boundary %s (%s): selected '%s' (%d/%d records, %d context "
             "neighbour rings)", shp.name,
             "UTM->lonlat" if projected else "lon/lat", name,
             1, len(cands), len(neigh))
    return GisData(t_rings, bounds, stations, lon0,
                   neighbors=neigh, province_name=name)


# --------------------------------------------------------------------------- #
# Data-file discovery (structure-based; Thai/English names OK)
# --------------------------------------------------------------------------- #
def _read_header(path: Path) -> list[str]:
    try:
        cols = _read_any_table(path, nrows=0).columns
    except Exception:                                        # noqa: BLE001
        return []
    return [str(c).strip() for c in cols]


def _station_cols_in(columns, station_ids) -> list[str]:
    cols = {str(c).strip() for c in columns}
    sset = {str(s).strip() for s in station_ids}
    return [c for c in cols if c in sset]


def _is_wide_daily_table(columns, station_ids) -> bool:
    cols = {str(c).strip() for c in columns}
    has_date = (all(c in cols for c in DATE_TRIPLE_COLS)
                or any(c in cols for c in DATE_SINGLE_COL_CANDIDATES))
    n_station = len(_station_cols_in(columns, station_ids))
    need = min(MIN_STATION_MATCHES, max(len(station_ids), 1))
    return has_date and n_station >= need


def _scenario_from_name(path: Path) -> str | None:
    m = re.search(r"(ssp\d{2,3}|rcp\d{2})", path.stem, re.IGNORECASE)
    return m.group(1).lower() if m else None


def _has_model_token(path: Path) -> bool:
    low = path.stem.lower()
    return any(tok in low for tok in MODEL_TOKENS)


def _model_from_name(path: Path, scenario: str | None) -> str:
    # 1) CMIP6 standard file pattern: (bc_)pr_day_<MODEL>_<scenario/historical>_...
    m = re.match(r"(?:bc_)?pr_day_(.+?)_(historical|ssp\d{2,3}|rcp\d{2})",
                 path.stem, re.IGNORECASE)
    if m:
        return m.group(1)
    # 2) parent folder (strip common suffixes like _CSV_FILE)
    parent = path.parent.name.strip()
    generic = {"csv", "data", "future", "gcm_data", "gcm", "projection",
               "projections", "rainfall", "input", "inputs", "gcm raindata"}
    if parent and parent.lower() not in generic:
        return re.sub(r"[_\- ]*(csv|file|files|data)$", "", parent,
                      flags=re.IGNORECASE) or parent
    stem = path.stem
    if scenario and scenario in stem.lower():
        left = stem[:stem.lower().find(scenario)].rstrip("_- ")
        parts = [p for p in re.split(r"[_\-]+", left) if p]
        if parts and parts[-1].lower() not in {"bc", "pr", "day", "rain", "daily"}:
            return parts[-1]
    for tok in reversed([t for t in re.split(r"[_\-]+", stem) if t]):
        if tok.lower() not in {"bc", "pr", "day", "rain", "daily", "historical"} \
                and not re.fullmatch(r"\d+", tok):
            return tok
    return "UnknownModel"


def _iter_data_files(source_dir: Path) -> list[Path]:
    return sorted(p for p in source_dir.rglob("*")
                  if p.is_file() and p.suffix.lower() in {".csv", ".xlsx", ".xls"})


def discover_observed_file(source_dir: Path, station_ids) -> Path:
    """Pick the observed baseline strictly: a wide daily table with NO scenario
    token and NO model/bias-correction token. Fail loud on 0 or >1 candidates."""
    candidates = []
    for path in _iter_data_files(source_dir):
        cols = _read_header(path)
        if not _is_wide_daily_table(cols, station_ids):
            continue
        if _scenario_from_name(path) is not None or _has_model_token(path):
            continue
        candidates.append(path)
    if not candidates:
        raise FileNotFoundError(
            "No observed baseline file found. Expected a wide daily table "
            "(YEAR/MONTH/DAY or DATE + station columns) whose name contains no "
            f"scenario/model/bias token, inside {source_dir}")
    # identical copies (same name + size) count as one candidate
    seen = {}
    for p in candidates:
        seen.setdefault((p.name, p.stat().st_size), p)
    candidates = list(seen.values())
    # Prefer names that positively say 'observed'/'obs'; else the longest match.
    def score(p: Path):
        low = p.stem.lower()
        return (2 if ("observed" in low or "obs" in low or "ฝน" in low) else 0,
                len(_station_cols_in(_read_header(p), station_ids)))
    candidates.sort(key=score, reverse=True)
    if len(candidates) > 1:
        log.warning("Multiple observed-baseline candidates; using %s. Others: %s",
                    candidates[0].name, [c.name for c in candidates[1:]])
    log.info("observed baseline: %s", candidates[0].name)
    return candidates[0]


def discover_future_files(source_dir: Path, station_ids) -> list[dict]:
    """Future daily tables: scenario token in name + wide daily structure.
    Bias-corrected files are preferred over raw when both exist for a
    (model, scenario) pair."""
    found: dict[tuple, dict] = {}
    for path in _iter_data_files(source_dir):
        scenario = _scenario_from_name(path)
        if scenario is None:
            continue
        cols = _read_header(path)
        if not _is_wide_daily_table(cols, station_ids):
            continue
        model = _model_from_name(path, scenario)
        is_bc = any(t in path.stem.lower() for t in BC_TOKENS)
        key = (model, scenario)
        cand = {"path": path, "model": model, "scenario": scenario,
                "bias_corrected": is_bc}
        if key not in found:
            found[key] = cand
        else:
            # keep bias-corrected over raw
            if is_bc and not found[key]["bias_corrected"]:
                found[key] = cand
    if not found:
        raise FileNotFoundError(
            f"No future projection files (need scenario token ssp*/rcp* + wide "
            f"daily structure) found in {source_dir}")
    files = sorted(found.values(), key=lambda d: (d["scenario"], d["model"]))
    n_bc = sum(1 for f in files if f["bias_corrected"])
    log.info("future files: %d (%d bias-corrected) across %d model-scenario pairs",
             len(files), n_bc, len(files))
    return files


# --------------------------------------------------------------------------- #
# Daily-table loading + ETCCDI-style index computation
# --------------------------------------------------------------------------- #
def _load_daily_table(path: Path, station_ids) -> pd.DataFrame:
    df = _read_any_table(path)
    df.columns = [str(c).strip() for c in df.columns]
    cols = set(df.columns)
    keep = [s for s in (str(x).strip() for x in station_ids) if s in cols]
    if all(c in cols for c in DATE_TRIPLE_COLS):
        out = df[list(DATE_TRIPLE_COLS) + keep].copy()
        out["date"] = pd.to_datetime(
            dict(year=out["YEAR"], month=out["MONTH"], day=out["DAY"]),
            errors="coerce")
        out = out.drop(columns=list(DATE_TRIPLE_COLS))
    else:
        date_col = next((c for c in DATE_SINGLE_COL_CANDIDATES if c in cols), None)
        if date_col is None:
            raise ValueError(f"No date columns detected in {path.name}")
        out = df[[date_col] + keep].copy()
        out["date"] = pd.to_datetime(out[date_col], errors="coerce")
        out = out.drop(columns=[date_col])
    out = out.set_index("date").sort_index()
    out = out[~out.index.isna()]
    for c in out.columns:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


def _max_consecutive(mask_values) -> int:
    best = run = 0
    for v in mask_values:
        run = run + 1 if v else 0
        best = max(best, run)
    return int(best)


def _rx_nday(s_year: pd.Series, n: int) -> float:
    if len(s_year) < n:
        return np.nan
    return float(s_year.rolling(n, min_periods=n).sum().max())


def _compute_thresholds(series: pd.Series, wet=WET_THRESHOLD) -> dict[str, float]:
    s = series.dropna().astype(float)
    wet_base = s[s >= wet]
    return {
        "p95": float(np.percentile(wet_base, 95)) if len(wet_base) else np.nan,
        "p99": float(np.percentile(wet_base, 99)) if len(wet_base) else np.nan,
    }


def _station_yearly_indices(series: pd.Series, thresholds: dict[str, float],
                            wet=WET_THRESHOLD) -> pd.DataFrame:
    s = series.dropna().astype(float)
    rows = []
    p95, p99 = thresholds["p95"], thresholds["p99"]
    for year, sy in s.groupby(s.index.year):
        wetmask = sy >= wet
        nwet = int(wetmask.sum())
        wet_total = float(sy[wetmask].sum())
        rows.append({
            "year": int(year),
            "PRCPTOT": wet_total,
            "SDII": (wet_total / nwet) if nwet else np.nan,
            "Rx1day": float(sy.max()) if len(sy) else np.nan,
            "Rx5day": _rx_nday(sy, 5),
            "CDD": _max_consecutive((~wetmask).values),
            "CWD": _max_consecutive(wetmask.values),
            "R10mm": int((sy >= 10.0).sum()),
            "R20mm": int((sy >= 20.0).sum()),
            "R50mm": int((sy >= 50.0).sum()),
            "R95p": float(sy[sy > p95].sum()) if np.isfinite(p95) else np.nan,
            "R99p": float(sy[sy > p99].sum()) if np.isfinite(p99) else np.nan,
        })
    return pd.DataFrame(rows)


def _melt_yearly(idx_df: pd.DataFrame, station, dataset, model, scenario) -> pd.DataFrame:
    out = idx_df.melt(id_vars="year", value_vars=INDEX_KEYS,
                      var_name="index", value_name="value")
    out.insert(0, "station", str(station))
    out.insert(1, "dataset", dataset)
    out.insert(2, "model", model)
    out.insert(3, "scenario", scenario)
    return out


def _fdr_bh(pvals: np.ndarray, alpha: float) -> np.ndarray:
    """Benjamini-Hochberg: return boolean reject array aligned to input order."""
    p = np.asarray(pvals, float)
    ok = np.isfinite(p)
    reject = np.zeros(p.shape, dtype=bool)
    idx = np.where(ok)[0]
    if idx.size == 0:
        return reject
    order = idx[np.argsort(p[idx])]
    m = idx.size
    thresh = alpha * (np.arange(1, m + 1) / m)
    passed = p[order] <= thresh
    if passed.any():
        kmax = np.max(np.where(passed)[0])
        reject[order[:kmax + 1]] = True
    return reject


# --------------------------------------------------------------------------- #
# Cube: observed baseline + bc-historical (for QC) + future projections
# --------------------------------------------------------------------------- #
def compute_yearly_index_cube(source_dir: Path, gis_dir: Path) -> dict:
    stations_all = _load_stations(gis_dir)
    coord_ids = set(stations_all["station"].astype(str))

    observed_path = discover_observed_file(source_dir, sorted(coord_ids))
    obs_cols = set(_read_header(observed_path))
    # STATION AUTHORITY = observed file columns, intersected with coord table
    station_ids = sorted(s for s in coord_ids if s in obs_cols)
    if len(station_ids) < MIN_STATION_MATCHES:
        raise ValueError(
            f"Only {len(station_ids)} stations common to the observed file and "
            f"coordinate table (need >= {MIN_STATION_MATCHES}). Observed file: "
            f"{observed_path.name}")
    analysed = stations_all[stations_all["station"].isin(station_ids)] \
        .reset_index(drop=True)
    # boundary selection votes with the ANALYSED gauges only (multi-province safe)
    gis = load_gis(gis_dir, station_hint=analysed)
    gis.stations = analysed
    log.info("STATION AUTHORITY = observed file: %d gauges analysed: %s",
             len(station_ids), ", ".join(station_ids))

    observed_daily = _load_daily_table(observed_path, station_ids)
    missing_obs = [s for s in station_ids if s not in observed_daily.columns]
    if missing_obs:
        raise ValueError(f"Observed file missing station columns: {missing_obs}")
    thresholds = {s: _compute_thresholds(observed_daily[s]) for s in station_ids}
    base_years = (int(observed_daily.index.year.min()),
                  int(observed_daily.index.year.max()))

    future_files = discover_future_files(source_dir, station_ids)

    yearly_parts, baseline_rows = [], []
    source_rows = [{"role": "observed_baseline", "path": str(observed_path),
                    "model": "Observed", "scenario": "historical",
                    "n_stations": len(station_ids)}]

    for s in station_ids:
        idx = _station_yearly_indices(observed_daily[s], thresholds[s])
        yearly_parts.append(_melt_yearly(idx, s, "Observed", "Observed", "historical"))
        for key in INDEX_KEYS:
            baseline_rows.append({
                "station": s, "index": key,
                "baseline_mean": idx[key].mean(),
                "baseline_median": idx[key].median(),
                "baseline_sd": idx[key].std(ddof=1),
                "unit": INDEX_UNIT_MAP[key], "description": INDEX_DESC_MAP[key],
                "n_years": int(idx[key].notna().sum()),
            })

    bc_hist_rows = []
    future_monthly = []
    for meta in future_files:
        daily = _load_daily_table(meta["path"], station_ids)
        present = [s for s in station_ids if s in daily.columns]
        future_monthly.append(_monthly_regional(
            daily, station_ids, "BC" if meta["bias_corrected"] else "RAW",
            meta["model"], meta["scenario"]))
        source_rows.append({
            "role": "future_projection", "path": str(meta["path"]),
            "model": meta["model"], "scenario": meta["scenario"],
            "n_stations": len(present),
        })
        for s in present:
            idx = _station_yearly_indices(daily[s], thresholds[s])
            yearly_parts.append(
                _melt_yearly(idx, s, "BC" if meta["bias_corrected"] else "RAW",
                             meta["model"], meta["scenario"]))

    # bc-historical (if present as separate files): full yearly indices go into
    # the cube (dataset='BC_HIST') for time-series/tables + residual-bias QC
    monthly_parts = [_monthly_regional(observed_daily, station_ids,
                                       "Observed", "Observed", "historical")]
    monthly_parts.extend(future_monthly)
    for meta_path in _iter_data_files(source_dir):
        low = meta_path.stem.lower()
        if "historical" in low and any(t in low for t in BC_TOKENS):
            cols = _read_header(meta_path)
            if not _is_wide_daily_table(cols, station_ids):
                continue
            model = _model_from_name(meta_path, None)
            daily = _load_daily_table(meta_path, station_ids)
            monthly_parts.append(_monthly_regional(daily, station_ids,
                                                   "BC_HIST", model, "historical"))
            for s in [x for x in station_ids if x in daily.columns]:
                idx = _station_yearly_indices(daily[s], thresholds[s])
                yearly_parts.append(_melt_yearly(idx, s, "BC_HIST", model, "historical"))
                m = idx[INDEX_KEYS].mean()
                for key in INDEX_KEYS:
                    bc_hist_rows.append({"model": model, "station": s,
                                         "index": key, "bc_hist_mean": m[key]})

    yearly = pd.concat(yearly_parts, ignore_index=True)
    yearly["station"] = yearly["station"].astype(str)
    yearly["year"] = pd.to_numeric(yearly["year"], errors="coerce").astype("Int64")
    # Informational label only. Window MEMBERSHIP for all statistics is derived
    # from year ranges in summarize_projections (_window_members), so a year in
    # two overlapping windows (e.g. 2041-2050 in Near AND Mid) counts in both.
    # ALL future years are kept (2015-2020 included) for time-series continuity.
    yearly["window"] = np.where(
        yearly["scenario"].eq("historical"), "Historical",
        np.select(
            [yearly["year"].between(*FUTURE_WINDOWS["Near"]),
             yearly["year"].between(*FUTURE_WINDOWS["Mid"]),
             yearly["year"].between(*FUTURE_WINDOWS["Late"])],
            ["Near", "Mid", "Late"], default="-"))
    yearly["window"] = yearly["window"].astype(str)

    baseline = pd.DataFrame(baseline_rows)
    resid_bias = _residual_bias_table(baseline, pd.DataFrame(bc_hist_rows))

    return {
        "yearly": yearly, "baseline": baseline, "gis": gis,
        "station_ids": station_ids, "base_years": base_years,
        "residual_bias": resid_bias,
        "source_inventory": pd.DataFrame(source_rows),
        "monthly_regional": pd.concat(monthly_parts, ignore_index=True),
    }


def _monthly_regional(daily: pd.DataFrame, station_ids, dataset, model, scenario
                      ) -> pd.DataFrame:
    """Regional (station-mean) mean monthly rainfall totals per calendar year.
    Small (12 rows x years) - accumulated while dailies are in memory so the
    seasonal-cycle figure never re-reads source files."""
    cols = [s for s in station_ids if s in daily.columns]
    reg = daily[cols].mean(axis=1)
    grp = reg.groupby([reg.index.year.rename("year"),
                       reg.index.month.rename("month")]).sum()
    out = grp.rename("monthly_total").reset_index()
    out.insert(0, "dataset", dataset)
    out.insert(1, "model", model)
    out.insert(2, "scenario", scenario)
    return out


def _residual_bias_table(baseline: pd.DataFrame, bc_hist: pd.DataFrame) -> pd.DataFrame:
    """Compare bc-historical index means with observed baseline (same period),
    per station-index-model, to justify applying observed thresholds to models."""
    if bc_hist.empty:
        return pd.DataFrame(columns=["model", "station", "index", "observed_mean",
                                     "bc_hist_mean", "bias_abs", "bias_pct"])
    obs = baseline[["station", "index", "baseline_mean"]].rename(
        columns={"baseline_mean": "observed_mean"})
    merged = bc_hist.merge(obs, on=["station", "index"], how="left")
    merged["bias_abs"] = merged["bc_hist_mean"] - merged["observed_mean"]
    merged["bias_pct"] = np.where(
        merged["observed_mean"].abs() > 1e-9,
        merged["bias_abs"] / merged["observed_mean"] * 100.0, np.nan)
    merged["unit"] = merged["index"].map(INDEX_UNIT_MAP)
    return merged.sort_values(["index", "model", "station"]).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Summaries: model-window deltas, ensemble agreement, per-model trend + FDR
# --------------------------------------------------------------------------- #
def _sign_agreement(series: pd.Series) -> float:
    vals = series.dropna().to_numpy(float)
    if len(vals) == 0:
        return np.nan
    sign = np.sign(np.nanmean(vals))
    if sign == 0:
        return float((np.sign(vals) == 0).mean())
    return float((np.sign(vals) == sign).mean())


def _window_members(future: pd.DataFrame, windows: dict) -> pd.DataFrame:
    """Expand future yearly rows into (window, row) membership by YEAR RANGE.
    A year inside two overlapping windows is counted in both — the correct
    semantics for climatological windows like Near 2021-2050 / Mid 2041-2070."""
    parts = []
    for name, (y0, y1) in windows.items():
        sub = future[future["year"].between(y0, y1)].copy()
        sub["window"] = name
        parts.append(sub)
    return pd.concat(parts, ignore_index=True) if parts else future.iloc[0:0]


def summarize_projections(yearly: pd.DataFrame, baseline: pd.DataFrame,
                          alpha: float = None, windows: dict = None,
                          window_order: list = None) -> dict:
    alpha = C.ALPHA if alpha is None else alpha
    windows = windows or FUTURE_WINDOWS
    window_order = window_order or list(windows)
    hist = baseline[["station", "index", "baseline_mean"]].copy()
    future_all = yearly[yearly["dataset"].isin(("BC", "RAW"))].drop(columns=["window"])
    future = _window_members(future_all, windows)

    # ---- per model-window mean & delta vs observed baseline ----
    model_window = (future.groupby(
        ["scenario", "window", "model", "station", "index"], as_index=False)["value"]
        .mean().rename(columns={"value": "window_mean"}))
    model_window = model_window.merge(hist, on=["station", "index"], how="left")
    model_window["delta_abs"] = model_window["window_mean"] - model_window["baseline_mean"]
    model_window["delta_pct"] = np.where(
        model_window["baseline_mean"].abs() > 1e-9,
        model_window["delta_abs"] / model_window["baseline_mean"] * 100.0, np.nan)
    model_window["unit"] = model_window["index"].map(INDEX_UNIT_MAP)
    model_window["description"] = model_window["index"].map(INDEX_DESC_MAP)

    # ---- per-model within-window trend (TFPW-MK) ----
    trend_rows = []
    for keys, sub in future.groupby(["scenario", "window", "model", "station", "index"]):
        vals = sub.sort_values("year")["value"].to_numpy(float)
        if np.isfinite(vals).sum() < MIN_TREND_YEARS:
            continue
        res = tfpw_mk(vals, alpha)
        trend_rows.append({
            "scenario": keys[0], "window": keys[1], "model": keys[2],
            "station": keys[3], "index": keys[4], "n": res.n,
            "sen_slope": res.sens_slope, "p_tfpw": res.p_value,
            "significant_raw": bool(res.significant), "direction": res.trend,
            "autocorr_lag1": res.autocorr_lag1,
            "ci95_low": res.sens_slope_lcl, "ci95_high": res.sens_slope_ucl,
            "unit": INDEX_UNIT_MAP[keys[4]],
        })
    trend = pd.DataFrame(trend_rows)
    # BH-FDR per (index, scenario) family
    if not trend.empty:
        trend["p_fdr_reject"] = False
        for (_, _), grp in trend.groupby(["index", "scenario"]):
            rej = _fdr_bh(grp["p_tfpw"].to_numpy(), alpha)
            trend.loc[grp.index, "p_fdr_reject"] = rej
        trend["significant_fdr"] = trend["p_fdr_reject"] & trend["significant_raw"]
        trend = trend.drop(columns=["p_fdr_reject"])

    # ---- ensemble across models (mean/median + spread + sign agreement) ----
    ensemble = (model_window.groupby(
        ["scenario", "window", "station", "index"], as_index=False)
        .agg(ensemble_mean=("window_mean", "mean"),
             ensemble_median=("window_mean", "median"),
             delta_abs_mean=("delta_abs", "mean"),
             delta_abs_median=("delta_abs", "median"),
             delta_abs_min=("delta_abs", "min"),
             delta_abs_max=("delta_abs", "max"),
             delta_pct_mean=("delta_pct", "mean"),
             delta_pct_median=("delta_pct", "median"),
             model_count=("model", "nunique")))
    agree = (model_window.groupby(["scenario", "window", "station", "index"])["delta_abs"]
             .apply(_sign_agreement).reset_index(name="agreement_fraction"))
    ensemble = ensemble.merge(agree, on=["scenario", "window", "station", "index"], how="left")
    ensemble["robust"] = ensemble["agreement_fraction"] >= AGREEMENT_ROBUST
    if not trend.empty:
        trend_ens = (trend.groupby(["scenario", "window", "station", "index"], as_index=False)
                     .agg(slope_mean=("sen_slope", "mean"),
                          slope_median=("sen_slope", "median"),
                          sig_fraction_fdr=("significant_fdr", "mean")))
        ensemble = ensemble.merge(trend_ens, on=["scenario", "window", "station", "index"], how="left")
    ensemble["unit"] = ensemble["index"].map(INDEX_UNIT_MAP)
    ensemble["description"] = ensemble["index"].map(INDEX_DESC_MAP)

    # ---- regional (area-mean over stations, ensemble over models) ----
    regional_model = (model_window.groupby(
        ["scenario", "window", "model", "index"], as_index=False)
        .agg(station_mean=("window_mean", "mean"),
             delta_abs_mean=("delta_abs", "mean"),
             delta_pct_mean=("delta_pct", "mean")))
    regional = (regional_model.groupby(["scenario", "window", "index"], as_index=False)
                .agg(regional_mean=("station_mean", "mean"),
                     regional_delta_abs_mean=("delta_abs_mean", "mean"),
                     regional_delta_abs_q25=("delta_abs_mean", lambda s: s.quantile(0.25)),
                     regional_delta_abs_q75=("delta_abs_mean", lambda s: s.quantile(0.75)),
                     regional_delta_pct_mean=("delta_pct_mean", "mean"),
                     regional_delta_pct_q25=("delta_pct_mean", lambda s: s.quantile(0.25)),
                     regional_delta_pct_q75=("delta_pct_mean", lambda s: s.quantile(0.75)),
                     model_agreement=("delta_abs_mean", _sign_agreement),
                     model_count=("model", "nunique")))
    regional["robust"] = regional["model_agreement"] >= AGREEMENT_ROBUST
    regional["unit"] = regional["index"].map(INDEX_UNIT_MAP)
    regional["description"] = regional["index"].map(INDEX_DESC_MAP)

    return {"model_window": model_window, "trend": trend,
            "ensemble": ensemble, "regional": regional}


def compare_with_framework(trend: pd.DataFrame, framework_output_dir: Path | str) -> pd.DataFrame:
    empty = pd.DataFrame(columns=["index", "scenario", "window", "model",
                                  "station", "slope_diff"])
    path = Path(framework_output_dir) / "Trend_Results.parquet"
    if not path.exists() or trend.empty:
        return empty
    try:
        ref = pd.read_parquet(path).rename(columns={"variable": "framework_variable"})
    except Exception as e:                                    # noqa: BLE001
        log.warning("framework parquet unreadable (%s); skipping cross-check",
                    type(e).__name__)
        return empty
    rows = []
    for local_idx, fw_idx in OVERLAP_FRAMEWORK_MAP.items():
        lsub = trend[trend["index"] == local_idx]
        rsub = ref[ref["framework_variable"] == fw_idx]
        if lsub.empty or rsub.empty:
            continue
        merged = lsub.merge(rsub[["scenario", "window", "model", "station", "sen_slope"]],
                            on=["scenario", "window", "model", "station"],
                            how="inner", suffixes=("_local", "_framework"))
        if merged.empty:
            continue
        merged["index"] = local_idx
        merged["slope_diff"] = merged["sen_slope_local"] - merged["sen_slope_framework"]
        rows.append(merged[["index", "scenario", "window", "model", "station", "slope_diff"]])
    return pd.concat(rows, ignore_index=True) if rows else empty


# --------------------------------------------------------------------------- #
# Figure styling + map furniture (deg-min graticule, cos-lat scale bar)
# --------------------------------------------------------------------------- #
@dataclass
class MapStyle:
    panel_title_size: int = 11
    axis_size: int = 10
    boundary_lw: float = 1.0
    grid_n: int = 160
    idw_power: float = 2.0
    bbox_pad: float = 0.03
    dpi: int = C.DPI
    cmap_diverging: str = "RdBu_r"
    serif_candidates: tuple = ("Times New Roman", "Liberation Serif", "DejaVu Serif")
    thai_candidates: tuple = ("TH Sarabun New", "Norasi", "Loma", "Garuda")

    def apply(self):
        fams = {f.name for f in font_manager.fontManager.ttflist}
        serif = next((c for c in self.serif_candidates if c in fams), "DejaVu Serif")
        thai = next((c for c in self.thai_candidates if c in fams), None)
        serif_stack = [serif] + ([thai] if thai else [])
        plt.rcParams.update({
            "font.family": "serif",
            "font.serif": serif_stack,
            "axes.unicode_minus": False,
            "font.size": self.axis_size,
            "axes.titlesize": self.panel_title_size,
            "axes.labelsize": self.axis_size,
            "xtick.labelsize": self.axis_size - 1,
            "ytick.labelsize": self.axis_size - 1,
            "savefig.dpi": self.dpi,
        })


def _save(fig, name: str):
    for ext in ("png", "pdf"):
        fig.savefig(C.FUTURE_Q1_FIG / f"{name}.{ext}", dpi=C.DPI,
                    bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)
    log.info("saved %s.{png,pdf}", name)


def _deg_min(value: float, is_lon: bool) -> str:
    hemi = ("E" if value >= 0 else "W") if is_lon else ("N" if value >= 0 else "S")
    v = abs(value)
    deg = int(v)
    minutes = int(round((v - deg) * 60))
    if minutes == 60:
        deg += 1
        minutes = 0
    return f"{deg}\u00b0{minutes:02d}\u2032{hemi}"


def _apply_graticule(ax, bounds, max_xticks=4, max_yticks=5, fontsize=None):
    from matplotlib.ticker import MaxNLocator
    ax.xaxis.set_major_locator(MaxNLocator(max_xticks, steps=[1, 2, 2.5, 5, 10]))
    ax.yaxis.set_major_locator(MaxNLocator(max_yticks, steps=[1, 2, 2.5, 5, 10]))
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: _deg_min(v, True)))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: _deg_min(v, False)))
    ax.tick_params(direction="out", length=3,
                   labelsize=fontsize if fontsize else plt.rcParams["xtick.labelsize"])
    ax.grid(True, color="#d0d0d0", lw=0.4, ls=":", zorder=1)


def _layout(bounds, pad):
    x0, y0, x1, y1 = bounds
    w, h = x1 - x0, y1 - y0
    return {"x0": x0, "y0": y0, "x1": x1, "y1": y1, "w": w, "h": h,
            "xlim": (x0 - pad * w, x1 + pad * w),
            "ylim": (y0 - pad * h, y1 + pad * h)}


def _nice_scale_km(width_deg: float, lat_mid: float) -> int:
    km = width_deg * 111.320 * np.cos(np.radians(lat_mid))
    target = 10
    for cand in (5, 10, 20, 25, 50, 100, 200):
        if cand <= km * 0.5:
            target = cand
    return target


def _km_to_deg_lon(km: float, lat_mid: float) -> float:
    return km / (111.320 * np.cos(np.radians(lat_mid)))


def _draw_boundary(ax, rings, style: MapStyle):
    for xs, ys in rings:
        ax.plot(xs, ys, color="#222222", lw=style.boundary_lw, zorder=5)


def _ring_paths(rings):
    return [MplPath(np.column_stack([xs, ys])) for xs, ys in rings]


def _mask_inside(gx, gy, paths):
    pts = np.column_stack([gx.ravel(), gy.ravel()])
    inside = np.zeros(pts.shape[0], dtype=bool)
    for p in paths:
        inside |= p.contains_points(pts)
    return inside.reshape(gx.shape)


def _idw(xy, vals, gx, gy, power):
    pts = np.column_stack([gx.ravel(), gy.ravel()])
    d = np.sqrt(((pts[:, None, :] - xy[None, :, :]) ** 2).sum(axis=2))
    d = np.where(d < 1e-9, 1e-9, d)
    w = 1.0 / d ** power
    z = (w * vals[None, :]).sum(axis=1) / w.sum(axis=1)
    return z.reshape(gx.shape)


def _corner_emptiness(gis: GisData, lay):
    """Rank the four corners by distance to the nearest station (empties first).
    Returns dict corner->score; corners: 'tl','tr','bl','br'."""
    pts = gis.stations[["lon", "lat"]].to_numpy(float)
    corners = {"tl": (lay["x0"] + 0.12 * lay["w"], lay["y1"] - 0.10 * lay["h"]),
               "tr": (lay["x1"] - 0.12 * lay["w"], lay["y1"] - 0.10 * lay["h"]),
               "bl": (lay["x0"] + 0.12 * lay["w"], lay["y0"] + 0.10 * lay["h"]),
               "br": (lay["x1"] - 0.12 * lay["w"], lay["y0"] + 0.10 * lay["h"])}
    out = {}
    for k, (cx, cy) in corners.items():
        d = np.hypot((pts[:, 0] - cx) / lay["w"], (pts[:, 1] - cy) / lay["h"])
        out[k] = float(d.min()) if len(d) else 1.0
    return out


def _pick_furniture_corners(gis: GisData, lay):
    """north arrow gets the emptiest TOP corner; scale bar the emptiest BOTTOM."""
    e = _corner_emptiness(gis, lay)
    north = "tl" if e["tl"] >= e["tr"] else "tr"
    scale = "bl" if e["bl"] >= e["br"] else "br"
    return north, scale


def _add_north(ax, lay, corner="tl", fontsize=11):
    x = lay["x0"] + (0.07 if corner.endswith("l") else 0.93) * lay["w"]
    y = lay["y1"] - 0.06 * lay["h"]
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.055 * lay["h"]),
                ha="center", va="center", fontsize=fontsize, fontweight="bold",
                arrowprops=dict(arrowstyle="-|>", color="k", lw=1.3), zorder=9)


def _nice_short_km(width_deg: float, lat_mid: float) -> int:
    km = width_deg * 111.320 * np.cos(np.radians(lat_mid))
    for cand in (200, 100, 50, 25, 20, 10, 5):
        if cand <= km * 0.28:
            return cand
    return 5


def _add_scalebar(ax, lay, corner="bl", fontsize=8):
    lat_mid = 0.5 * (lay["y0"] + lay["y1"])
    km = _nice_short_km(lay["w"], lat_mid)
    deg = _km_to_deg_lon(km, lat_mid)
    y0 = lay["y0"] + 0.05 * lay["h"]
    x0 = (lay["x0"] + 0.06 * lay["w"] if corner.endswith("l")
          else lay["x1"] - 0.06 * lay["w"] - deg)
    ax.plot([x0, x0 + deg], [y0, y0], "k-", lw=2.2, zorder=9,
            solid_capstyle="butt")
    for xe in (x0, x0 + deg):
        ax.plot([xe, xe], [y0 - 0.008 * lay["h"], y0 + 0.008 * lay["h"]],
                "k-", lw=1.2, zorder=9)
    ax.text(x0 + deg / 2, y0 + 0.014 * lay["h"], f"{km} km", ha="center",
            va="bottom", fontsize=fontsize, zorder=9,
            bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.8))
    return (x0, y0 - 0.02 * lay["h"], x0 + deg, y0 + 0.05 * lay["h"])


def _draw_neighbors(ax, gis: GisData, lw=0.55):
    for xs, ys in (gis.neighbors or []):
        ax.plot(xs, ys, color="#9aa0a6", lw=lw, zorder=3)


def _surface_panel(ax, gis: GisData, merged: pd.DataFrame, value_col: str,
                   robust_col: str, cmap: str, vmin: float, vmax: float,
                   panel_title: str, style: MapStyle, corners=None):
    lay = _layout(gis.bounds, style.bbox_pad)
    gx, gy, mask = gis.grid_mask(style.grid_n)

    vals = merged[value_col].to_numpy(float)
    finite = np.isfinite(vals)
    im = None
    if finite.sum() >= 3:
        xy = merged.loc[finite, ["lon", "lat"]].to_numpy(float)
        z = _idw(xy, vals[finite], gx, gy, style.idw_power)
        z = np.ma.array(z, mask=~mask)
        im = ax.pcolormesh(gx, gy, z, cmap=cmap, vmin=vmin, vmax=vmax,
                           shading="auto", zorder=2)
        if robust_col in merged.columns:
            rob_vals = merged.loc[finite, robust_col].astype(float).to_numpy()
            rob_surf = _idw(xy, rob_vals, gx, gy, style.idw_power)
            not_rob = np.ma.array(np.where(rob_surf < 0.5, 1.0, np.nan), mask=~mask)
            ax.contourf(gx, gy, np.ma.filled(not_rob, np.nan), levels=[0.5, 1.5],
                        colors="none", hatches=["////"], zorder=3)

    _draw_boundary(ax, gis.rings_lonlat, style)
    ax.scatter(merged["lon"], merged["lat"], c=merged[value_col], s=34,
               cmap=cmap, vmin=vmin, vmax=vmax, edgecolor="black",
               linewidth=0.5, zorder=6)
    ax.set_xlim(*lay["xlim"])
    ax.set_ylim(*lay["ylim"])
    ax.set_aspect("equal", adjustable="box")
    _apply_graticule(ax, gis.bounds, max_xticks=4, max_yticks=5,
                     fontsize=style.axis_size - 2)
    nc, sc = corners or _pick_furniture_corners(gis, lay)
    _add_north(ax, lay, corner=nc, fontsize=10)
    _add_scalebar(ax, lay, corner=sc, fontsize=7)
    ax.set_title(panel_title, fontsize=style.panel_title_size)
    return im


def fig_index_maps(ensemble: pd.DataFrame, gis: GisData, area_name: str):
    style = MapStyle(); style.apply()
    lay = _layout(gis.bounds, style.bbox_pad)
    corners = _pick_furniture_corners(gis, lay)
    for idx_no, idx in enumerate(INDEX_KEYS, start=4):
        sub = ensemble[ensemble["index"] == idx].copy()
        vals = sub["delta_abs_mean"].to_numpy(float)
        vmax = float(np.nanpercentile(np.abs(vals), 95)) if np.isfinite(vals).any() else 1.0
        vmax = vmax if np.isfinite(vmax) and vmax > 0 else 1.0
        ncol = len(WINDOW_ORDER)
        fig, axes = plt.subplots(2, ncol, figsize=(4.4 * ncol, 4.6 * 2))
        axes = np.atleast_1d(axes).ravel()
        im = None
        k = 0
        for scenario in SCENARIO_ORDER:
            for window in WINDOW_ORDER:
                ax = axes[k]
                panel = sub[(sub["scenario"] == scenario) & (sub["window"] == window)]
                panel = gis.stations.merge(panel, on="station", how="left")
                im = _surface_panel(ax, gis, panel, "delta_abs_mean", "robust",
                                    style.cmap_diverging, -vmax, vmax,
                                    f"{scenario.upper()} | {window}", style,
                                    corners=corners)
                if k < ncol:
                    ax.set_xlabel(""); ax.tick_params(labelbottom=False)
                if k % ncol != 0:
                    ax.set_ylabel(""); ax.tick_params(labelleft=False)
                k += 1
        if im is not None:
            cax = fig.add_axes([0.925, 0.28, 0.016, 0.44])
            cb = fig.colorbar(im, cax=cax)
            cb.ax.tick_params(labelsize=9)
            cb.set_label(f"Change vs observed baseline ({INDEX_UNIT_MAP[idx]})",
                         fontsize=10)
        hatch_proxy = plt.matplotlib.patches.Patch(
            facecolor="white", edgecolor="black", hatch="////",
            label=f"Low model agreement (<{int(AGREEMENT_ROBUST*100)}% sign agreement)")
        pt_proxy = plt.Line2D([0], [0], marker="o", color="w",
                              markerfacecolor="#888", markeredgecolor="black",
                              markersize=8, label="Gauge (filled by value)")
        fig.legend(handles=[pt_proxy, hatch_proxy], loc="lower center", ncol=2,
                   frameon=False, bbox_to_anchor=(0.5, 0.01), fontsize=10)
        fig.suptitle(f"{area_name} \u2014 {idx} ({INDEX_DESC_MAP[idx]}): projected "
                     f"change vs observed baseline\n"
                     f"Hatching = ensemble sign agreement below "
                     f"{int(AGREEMENT_ROBUST*100)}%", fontsize=13)
        fig.subplots_adjust(left=0.065, right=0.905, bottom=0.10, top=0.885,
                            wspace=0.06, hspace=0.14)
        _save(fig, f"FUTURE_Q1_FIGURE_{idx_no:02d}_{idx.lower()}_projection_maps")
        import gc
        gc.collect()


def _place_labels(ax, gis: GisData, lay, keepout, fontsize=7.5):
    """Greedy anti-collision station labelling with leader lines.

    keepout: list of (x0, y0, x1, y1) data-coordinate boxes labels must avoid
    (scale bar, inset, north arrow)."""
    lw, lh = 0.085 * lay["w"], 0.030 * lay["h"]     # approx label box (6-digit id)
    dx, dy = 0.016 * lay["w"], 0.014 * lay["h"]
    cand = [(dx, dy), (-lw - dx, dy), (dx, -lh - dy), (-lw - dx, -lh - dy),
            (dx, 3.2 * dy), (-lw - dx, 3.2 * dy), (dx, -lh - 3.2 * dy),
            (-lw - dx, -lh - 3.2 * dy), (2.8 * dx, 0.4 * dy),
            (-lw - 2.8 * dx, 0.4 * dy)]
    placed = []
    pts = gis.stations[["lon", "lat"]].to_numpy(float)

    def overlaps(box, other):
        return not (box[2] < other[0] or box[0] > other[2]
                    or box[3] < other[1] or box[1] > other[3])

    for _, row in gis.stations.iterrows():
        sx, sy = row["lon"], row["lat"]
        best, best_pen = None, None
        for ox, oy in cand:
            x0, y0 = sx + ox, sy + oy
            box = (x0, y0, x0 + lw, y0 + lh)
            pen = 0.0
            if (box[0] < lay["xlim"][0] or box[2] > lay["xlim"][1]
                    or box[1] < lay["ylim"][0] or box[3] > lay["ylim"][1]):
                pen += 10
            pen += sum(4 for b in placed if overlaps(box, b))
            pen += sum(4 for b in keepout if overlaps(box, b))
            cx, cy = 0.5 * (box[0] + box[2]), 0.5 * (box[1] + box[3])
            d = np.hypot((pts[:, 0] - cx) / lay["w"], (pts[:, 1] - cy) / lay["h"])
            pen += sum(2 for dd in d if dd < 0.035)
            pen += 0.2 * np.hypot(ox / lay["w"], oy / lay["h"])
            if best_pen is None or pen < best_pen:
                best_pen, best = pen, box
        placed.append(best)
        tx, ty = 0.5 * (best[0] + best[2]), 0.5 * (best[1] + best[3])
        if np.hypot(tx - sx, ty - sy) > 0.045 * lay["w"]:
            ax.plot([sx, tx], [sy, ty], color="#666", lw=0.5, zorder=6)
        ax.text(tx, ty, row["station"], fontsize=fontsize, ha="center",
                va="center", zorder=8,
                bbox=dict(boxstyle="round,pad=0.14", fc="white", ec="#bbb",
                          lw=0.4, alpha=0.9))


def fig_study_area(gis: GisData, area_name: str):
    style = MapStyle(); style.apply()
    fig = plt.figure(figsize=(7.0, 7.0 * max(0.75, min(1.35,
                     (gis.bounds[3] - gis.bounds[1])
                     / max(gis.bounds[2] - gis.bounds[0], 1e-9)))))
    ax = fig.add_axes([0.115, 0.085, 0.86, 0.865])
    lay = _layout(gis.bounds, 0.045)
    _draw_neighbors(ax, gis, lw=0.6)
    for xs, ys in gis.rings_lonlat:
        ax.fill(xs, ys, color="#EAF1F6", zorder=2)
    _draw_boundary(ax, gis.rings_lonlat, style)
    ax.scatter(gis.stations["lon"], gis.stations["lat"], s=46, c="#1565C0",
               edgecolor="black", linewidth=0.6, zorder=7)
    ax.set_xlim(*lay["xlim"]); ax.set_ylim(*lay["ylim"])
    ax.set_aspect("equal", adjustable="box")
    _apply_graticule(ax, gis.bounds, max_xticks=5, max_yticks=6)
    nc, sc = _pick_furniture_corners(gis, lay)
    _add_north(ax, lay, corner=nc)
    sb_box = _add_scalebar(ax, lay, corner=sc)
    inset_box = _add_regional_inset(fig, ax, gis, lay, avoid=[sb_box])
    keepout = [sb_box] + ([inset_box] if inset_box else [])
    _place_labels(ax, gis, lay, keepout)
    n_line = "" if not gis.province_name else f" \u2014 {gis.province_name}"
    ax.set_title(f"{area_name} study area and {len(gis.stations)}-gauge network",
                 fontsize=13, pad=10)
    _save(fig, "FUTURE_Q1_FIGURE_01_study_area")


def _add_regional_inset(fig, ax, gis: GisData, lay, avoid=None):
    """'Regional setting' inset built from REAL neighbouring polygons in the
    same boundary file (target filled). Placed in the emptiest map corner.
    Returns the inset's keep-out box in data coordinates (or None)."""
    if not gis.neighbors:
        return None
    e = _corner_emptiness(gis, lay)
    corner = max(e, key=e.get)
    fx = {"l": 0.135, "r": 0.715}[corner[1]]
    fy = {"t": 0.665, "b": 0.105}[corner[0]]
    iax = fig.add_axes([fx, fy, 0.245, 0.245], zorder=20)
    iax.set_facecolor("white")
    for xs, ys in gis.neighbors:
        iax.plot(xs, ys, color="#9aa0a6", lw=0.45)
    for xs, ys in gis.rings_lonlat:
        iax.fill(xs, ys, color="#D55E00", alpha=0.55, lw=0)
        iax.plot(xs, ys, color="#8a3b00", lw=0.7)
    nx = np.concatenate([r[0] for r in gis.neighbors] +
                        [r[0] for r in gis.rings_lonlat])
    ny = np.concatenate([r[1] for r in gis.neighbors] +
                        [r[1] for r in gis.rings_lonlat])
    iax.set_xlim(nx.min() - 0.05, nx.max() + 0.05)
    iax.set_ylim(ny.min() - 0.05, ny.max() + 0.05)
    iax.set_aspect("equal", adjustable="box")
    iax.set_xticks([]); iax.set_yticks([])
    for s in iax.spines.values():
        s.set_linewidth(0.9)
    iax.set_title("Regional setting", fontsize=8, pad=2)
    # keep-out box in main-axes data coordinates
    bb = iax.get_position()
    axb = ax.get_position()
    x0 = lay["xlim"][0] + (bb.x0 - axb.x0) / axb.width * (lay["xlim"][1] - lay["xlim"][0])
    x1 = lay["xlim"][0] + (bb.x1 - axb.x0) / axb.width * (lay["xlim"][1] - lay["xlim"][0])
    y0 = lay["ylim"][0] + (bb.y0 - axb.y0) / axb.height * (lay["ylim"][1] - lay["ylim"][0])
    y1 = lay["ylim"][0] + (bb.y1 - axb.y0) / axb.height * (lay["ylim"][1] - lay["ylim"][0])
    return (x0, y0, x1, y1)


def fig_overview_heatmap(regional: pd.DataFrame, area_name: str):
    style = MapStyle(); style.apply()
    col_order = [(s, w) for s in SCENARIO_ORDER for w in WINDOW_ORDER]
    mat = np.full((len(INDEX_KEYS), len(col_order)), np.nan)
    ann = np.empty_like(mat, dtype=object)
    rob = np.zeros_like(mat, dtype=bool)
    for i, idx in enumerate(INDEX_KEYS):
        for j, (s, w) in enumerate(col_order):
            row = regional[(regional["index"] == idx) & (regional["scenario"] == s)
                           & (regional["window"] == w)]
            if not row.empty:
                pct = row["regional_delta_pct_mean"].iloc[0]
                mat[i, j] = pct
                ann[i, j] = f"{pct:+.0f}%"
                rob[i, j] = bool(row["robust"].iloc[0])
            else:
                ann[i, j] = ""
    vmax = float(np.nanpercentile(np.abs(mat), 95)) if np.isfinite(mat).any() else 50.0
    vmax = vmax if vmax > 0 else 50.0
    fig, ax = plt.subplots(figsize=(10.8, 7.2))
    im = ax.imshow(mat, aspect="auto", cmap="RdBu_r", vmin=-vmax, vmax=vmax)
    ax.set_xticks(range(len(col_order)))
    ax.set_xticklabels([f"{s.upper()}\n{w}" for s, w in col_order])
    ax.set_yticks(range(len(INDEX_KEYS)))
    ax.set_yticklabels([f"{idx} ({INDEX_UNIT_MAP[idx]})" for idx in INDEX_KEYS])
    ax.set_xlabel("Scenario and future window")
    ax.set_ylabel("Projection index")
    ax.set_title(f"{area_name}: regional ensemble percentage change vs observed baseline\n"
                 f"Bold = robust (>= {int(AGREEMENT_ROBUST*100)}% model sign agreement)")
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            if np.isfinite(mat[i, j]):
                ax.text(j, i, ann[i, j], ha="center", va="center", fontsize=8,
                        fontweight="bold" if rob[i, j] else "normal",
                        color="black")
    cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cb.set_label("Regional change vs observed baseline (%)")
    fig.tight_layout()
    _save(fig, "FUTURE_Q1_FIGURE_02_projection_overview_heatmap")


def fig_regional_profiles(regional: pd.DataFrame, area_name: str):
    style = MapStyle(); style.apply()
    ncol = 4
    nrow = int(np.ceil(len(INDEX_KEYS) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(16.0, 3.2 * nrow), squeeze=False)
    cmap = {"ssp245": "#4E79A7", "ssp585": "#D55E00"}
    x = np.arange(len(WINDOW_ORDER))
    for ax, idx in zip(axes.ravel(), INDEX_KEYS):
        sub = regional[regional["index"] == idx]
        for s in SCENARIO_ORDER:
            ss = sub[sub["scenario"] == s].set_index("window").reindex(WINDOW_ORDER)
            y = ss["regional_delta_abs_mean"].to_numpy(float)
            q25 = ss["regional_delta_abs_q25"].to_numpy(float)
            q75 = ss["regional_delta_abs_q75"].to_numpy(float)
            yl = np.maximum(y - q25, 0); yh = np.maximum(q75 - y, 0)
            ax.errorbar(x, y, yerr=np.vstack([yl, yh]), fmt="-o", color=cmap[s],
                        lw=1.5, ms=4, capsize=3, label=s.upper())
        ax.axhline(0, color="#666", lw=0.8, ls="--")
        ax.set_xticks(x); ax.set_xticklabels(WINDOW_ORDER)
        ax.set_title(idx); ax.set_ylabel(f"Change ({INDEX_UNIT_MAP[idx]})")
    for ax in axes.ravel()[len(INDEX_KEYS):]:
        ax.axis("off")
    h, l = axes.ravel()[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=2, bbox_to_anchor=(0.5, 0.01))
    fig.suptitle(f"{area_name}: regional projection profiles (ensemble mean, "
                 f"model IQR)", fontsize=14)
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    _save(fig, "FUTURE_Q1_FIGURE_03_regional_projection_profiles")


# --------------------------------------------------------------------------- #
# Workbook writing (Info + results + Significant)
# --------------------------------------------------------------------------- #
def _info_df(source_dir, gis_dir, area_name, station_ids, base_years, extra=None):
    base = {
        "Study area": area_name,
        "Station authority": "observed rainfall file (columns INTERSECT coordinate table)",
        "Number of gauges": len(station_ids),
        "Gauge IDs": ", ".join(map(str, station_ids)),
        "Observed baseline period": f"{base_years[0]}-{base_years[1]}",
        "Source directory": str(source_dir),
        "GIS directory": str(gis_dir),
        "Future windows": ", ".join(f"{k}:{v[0]}-{v[1]}" for k, v in FUTURE_WINDOWS.items()),
        "Scenarios": ", ".join(SCENARIO_ORDER),
        "Indices": ", ".join(INDEX_KEYS),
        "Wet-day threshold": f">= {WET_THRESHOLD} mm",
        "R95p/R99p thresholds": "observed wet-day p95/p99 per station (applied to models)",
        "Spell convention": "CDD/CWD/Rx5day computed within each calendar year",
        "Trend method": "TFPW-MK (Yue et al. 2002) + Sen slope (Gilbert 1987 CI)",
        "Multiplicity control": "Benjamini-Hochberg FDR per (index, scenario) family",
        "Ensemble agreement": f"robust if >= {int(AGREEMENT_ROBUST*100)}% of models "
                              f"agree on sign of change",
        "Bias correction": "bias-corrected files preferred over raw when both present",
        "Significance level alpha": C.ALPHA,
        "Data integrity": "real observations/model output only; no imputed values",
        "Generated (UTC)": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if extra:
        base.update(extra)
    return pd.DataFrame({"Field": list(base), "Value": [str(v) for v in base.values()]})


def _save_cube(df: pd.DataFrame, out_dir: Path, stem: str):
    """Save the yearly cube as parquet if an engine is available, else CSV."""
    try:
        df.to_parquet(out_dir / f"{stem}.parquet", index=False)
        log.info("saved %s.parquet", stem)
    except Exception as e:                                    # noqa: BLE001
        df.to_csv(out_dir / f"{stem}.csv", index=False)
        log.info("parquet engine unavailable (%s); saved %s.csv instead",
                 type(e).__name__, stem)


def _write_workbook(path: Path, info: pd.DataFrame, df: pd.DataFrame,
                    sig_mask=None):
    with pd.ExcelWriter(path, engine="xlsxwriter") as w:
        info.to_excel(w, index=False, sheet_name="Info")
        df.to_excel(w, index=False, sheet_name="results")
        if sig_mask is not None:
            sig = df[sig_mask].reset_index(drop=True)
            (sig if len(sig) else pd.DataFrame({"note": ["none significant at alpha (FDR)"]})
             ).to_excel(w, index=False, sheet_name="Significant")
    log.info("saved %s", path.name)


# --------------------------------------------------------------------------- #
# Orchestrator
# --------------------------------------------------------------------------- #
def build_future_q1_outputs(source_dir=None, gis_dir=None,
                            framework_output_dir=None, area_name=None) -> dict:
    source_dir = Path(source_dir or C.FUTURE_SOURCE_DIR)
    gis_dir = Path(gis_dir or C.FUTURE_GIS_DIR)
    framework_output_dir = Path(framework_output_dir or C.FUTURE_FRAMEWORK_OUTPUT_DIR)
    area_name = area_name or getattr(C, "STUDY_AREA_NAME", "Study area")
    if not source_dir.exists():
        raise FileNotFoundError(f"Future source directory not found: {source_dir}")
    if not gis_dir.exists():
        raise FileNotFoundError(f"GIS directory not found: {gis_dir}")

    FIG.init()
    cube = compute_yearly_index_cube(source_dir, gis_dir)
    yearly = cube["yearly"]
    baseline = cube["baseline"]
    gis = cube["gis"]
    station_ids = cube["station_ids"]
    base_years = cube["base_years"]

    summaries = summarize_projections(yearly, baseline)
    ensemble = summaries["ensemble"]
    trend = summaries["trend"]
    framework_check = compare_with_framework(trend, framework_output_dir)

    # ---- tables ----
    _save_cube(yearly, C.FUTURE_Q1_TAB, "FUTURE_Q1_TABLE_00_yearly_index_cube")

    def info(extra=None):
        return _info_df(source_dir, gis_dir, area_name, station_ids, base_years, extra)

    registry = pd.DataFrame([s.__dict__ for s in INDEX_SPECS])
    _write_workbook(C.FUTURE_Q1_TAB / "FUTURE_Q1_TABLE_01_INDEX_REGISTRY.xlsx",
                    info({"Table": "Index registry"}), registry)
    _write_workbook(C.FUTURE_Q1_TAB / "FUTURE_Q1_TABLE_02_BASELINE_STATION_SUMMARY.xlsx",
                    info({"Table": "Observed baseline per-station index summary"}), baseline)
    _write_workbook(C.FUTURE_Q1_TAB / "FUTURE_Q1_TABLE_03_FUTURE_MODEL_WINDOW_SUMMARY.xlsx",
                    info({"Table": "Per-model, per-window index means and deltas"}),
                    summaries["model_window"])
    _write_workbook(C.FUTURE_Q1_TAB / "FUTURE_Q1_TABLE_04_FUTURE_ENSEMBLE_STATION_SUMMARY.xlsx",
                    info({"Table": "Ensemble per-station change, spread, agreement"}),
                    ensemble, sig_mask=ensemble.get("robust"))
    trend_sig = trend["significant_fdr"] if ("significant_fdr" in trend.columns
                                             and not trend.empty) else None
    _write_workbook(C.FUTURE_Q1_TAB / "FUTURE_Q1_TABLE_05_FUTURE_TREND_RESULTS_BY_MODEL.xlsx",
                    info({"Table": "Per-model within-window TFPW-MK trend + BH-FDR",
                          "'Significant' sheet": "FDR-significant only"}),
                    trend, sig_mask=trend_sig)
    _write_workbook(C.FUTURE_Q1_TAB / "FUTURE_Q1_TABLE_06_REGIONAL_ENSEMBLE_SUMMARY.xlsx",
                    info({"Table": "Regional ensemble change with model IQR + agreement"}),
                    summaries["regional"], sig_mask=summaries["regional"].get("robust"))
    _write_workbook(C.FUTURE_Q1_TAB / "FUTURE_Q1_TABLE_07_FRAMEWORK_VALIDATION.xlsx",
                    info({"Table": "Cross-check vs external framework Trend_Results"}),
                    framework_check)
    _write_workbook(C.FUTURE_Q1_TAB / "FUTURE_Q1_TABLE_08_SOURCE_FILE_INVENTORY.xlsx",
                    info({"Table": "Discovered source files"}), cube["source_inventory"])
    _write_workbook(C.FUTURE_Q1_TAB / "FUTURE_Q1_TABLE_09_BC_HISTORICAL_RESIDUAL_BIAS.xlsx",
                    info({"Table": "bc-historical vs observed baseline residual bias (QC)"}),
                    cube["residual_bias"])
    t10 = table_station_rainfall_hist(yearly)
    _write_workbook(C.FUTURE_Q1_TAB / "FUTURE_Q1_TABLE_10_STATION_RAINFALL_OBS_QDM_GCM.xlsx",
                    info({"Table": "Per-station annual rainfall: observed vs QDM "
                                   "bc-historical per GCM + MME (full record & AR6 baseline)"}),
                    t10)
    t11 = table_station_rainfall_ar6(yearly)
    _write_workbook(C.FUTURE_Q1_TAB / "FUTURE_Q1_TABLE_11_STATION_RAINFALL_AR6_GCM_MME.xlsx",
                    info({"Table": "Per-station rainfall per GCM + MME across IPCC AR6 "
                                   "windows; delta vs observed AR6 baseline",
                          "AR6 baseline": f"{AR6_BASELINE[0]}-{AR6_BASELINE[1]}",
                          "AR6 windows": ", ".join(f"{k}:{v[0]}-{v[1]}"
                                                   for k, v in AR6_WINDOWS.items())}),
                    t11, sig_mask=t11.get("robust"))

    # ---- figures ----
    fig_study_area(gis, area_name)
    fig_overview_heatmap(summaries["regional"], area_name)
    fig_regional_profiles(summaries["regional"], area_name)
    fig_index_maps(ensemble, gis, area_name)
    fig_ts_regional(yearly, area_name)
    fig_ts_station_grid(yearly, baseline, area_name, scenario="ssp585")
    fig_ts_station_grid(yearly, baseline, area_name, scenario="ssp245")
    fig_ts_seasonal(cube["monthly_regional"], area_name)

    return {
        "source_dir": str(source_dir), "gis_dir": str(gis_dir),
        "area_name": area_name, "n_stations": len(station_ids),
        "table_dir": str(C.FUTURE_Q1_TAB), "figure_dir": str(C.FUTURE_Q1_FIG),
    }


# --------------------------------------------------------------------------- #
# AR6 time-series figures (TS-1/2/3) + per-station GCM/MME tables (10/11)
# --------------------------------------------------------------------------- #
_TS_C_OBS = "#000000"
_TS_C_HIST = "#6A6A6A"
_TS_C = {"ssp245": "#4E79A7", "ssp585": "#D55E00"}


def _prcptot_regional(yearly: pd.DataFrame, dataset, scenario=None) -> pd.DataFrame:
    """Regional (station-mean) PRCPTOT per model-year for a dataset slice."""
    sub = yearly[(yearly["dataset"] == dataset) & (yearly["index"] == "PRCPTOT")]
    if scenario is not None:
        sub = sub[sub["scenario"] == scenario]
    return (sub.groupby(["model", "year"], as_index=False)["value"].mean()
               .rename(columns={"value": "prcptot"}))


def _ens_stats(df: pd.DataFrame, by="year") -> pd.DataFrame:
    g = df.groupby(by)["prcptot"]
    out = pd.DataFrame({"mean": g.mean(), "q25": g.quantile(0.25),
                        "q75": g.quantile(0.75), "vmin": g.min(), "vmax": g.max()})
    return out.reset_index()


def fig_ts_regional(yearly: pd.DataFrame, area_name: str):
    """TS-1: regional annual rainfall 1981-2100 — obs, QDM bc-historical
    ensemble, SSP245/585 ensembles, AR6 windows shaded (SSP-only, no splice)."""
    style = MapStyle(); style.apply()
    fig, ax = plt.subplots(figsize=(11.5, 5.2))
    obs = _prcptot_regional(yearly, "Observed")
    hist = _ens_stats(_prcptot_regional(yearly, "BC_HIST"))
    ax.fill_between(hist["year"], hist["vmin"], hist["vmax"], color=_TS_C_HIST,
                    alpha=0.22, lw=0, label="QDM historical (7-GCM min-max)")
    ax.plot(hist["year"], hist["mean"], color=_TS_C_HIST, lw=1.2,
            label="QDM historical (ensemble mean)")
    ax.plot(obs["year"], obs["prcptot"], color=_TS_C_OBS, lw=1.6, label="Observed")
    for scen in SCENARIO_ORDER:
        ens = _ens_stats(_prcptot_regional(yearly, "BC", scen))
        ax.fill_between(ens["year"], ens["q25"], ens["q75"], color=_TS_C[scen],
                        alpha=0.25, lw=0, label=f"{scen.upper()} (model IQR)")
        ax.plot(ens["year"], ens["mean"], color=_TS_C[scen], lw=1.5,
                label=f"{scen.upper()} (ensemble mean)")
    # AR6 shading + labels
    spans = dict(AR6_WINDOWS); spans["Baseline"] = AR6_BASELINE
    ytop = ax.get_ylim()[1]
    for name, (y0, y1) in spans.items():
        ax.axvspan(y0, y1 + 1, color="#000000", alpha=0.05, zorder=0)
        ax.annotate(f"{name}\n{y0}\u2013{y1}", xy=((y0 + y1) / 2, 1.015),
                    xycoords=("data", "axes fraction"), ha="center", va="bottom",
                    fontsize=8)
    ax.axvline(2014.5, color="#888", lw=0.8, ls=":")
    ax.set_xlim(1981, 2100)
    ax.set_xlabel("Year")
    ax.set_ylabel("Regional annual rainfall, PRCPTOT (mm)")
    ax.legend(loc="upper left", fontsize=8, ncol=2, frameon=False)
    ax.set_title(f"{area_name}: observed and QDM bias-corrected CMIP6 regional "
                 f"rainfall with IPCC AR6 assessment periods", pad=26)
    fig.tight_layout()
    _save(fig, "FUTURE_Q1_FIGURE_15_ts_regional_ar6")


def fig_ts_station_grid(yearly: pd.DataFrame, baseline: pd.DataFrame,
                        area_name: str, scenario="ssp585"):
    """TS-2: per-station anomaly (%) small multiples vs AR6 baseline; shared
    axes; last panels = regional mean + legend."""
    style = MapStyle(); style.apply()
    stations = sorted(yearly.loc[yearly["dataset"] == "Observed", "station"].unique())
    base = (yearly[(yearly["dataset"] == "Observed") & (yearly["index"] == "PRCPTOT")
                   & yearly["year"].between(*AR6_BASELINE)]
            .groupby("station")["value"].mean())

    def anom(df, sid):
        b = base.get(sid, np.nan)
        return (df["value"] / b - 1.0) * 100.0 if np.isfinite(b) and b > 0 else df["value"] * np.nan

    ncol = 4
    nrow = int(np.ceil((len(stations) + 2) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(13.5, 2.6 * nrow),
                             sharex=True, sharey=True, squeeze=False)
    flat = axes.ravel()
    fut = yearly[(yearly["dataset"] == "BC") & (yearly["index"] == "PRCPTOT")
                 & (yearly["scenario"] == scenario)]
    obs = yearly[(yearly["dataset"] == "Observed") & (yearly["index"] == "PRCPTOT")]

    def draw(ax, o_df, f_df, sid, title, bold=False):
        o = o_df.sort_values("year"); oa = anom(o, sid)
        ax.plot(o["year"], oa, color=_TS_C_OBS, lw=0.9)
        ax.plot(o["year"], oa.rolling(5, center=True).mean(), color=_TS_C_OBS, lw=1.6)
        g = f_df.groupby("year")["value"]
        yrs = g.mean().index.to_numpy()
        b = base.get(sid, np.nan)
        if np.isfinite(b) and b > 0:
            m = (g.mean() / b - 1) * 100; q1 = (g.quantile(.25) / b - 1) * 100
            q3 = (g.quantile(.75) / b - 1) * 100
            ax.fill_between(yrs, q1, q3, color=_TS_C[scenario], alpha=0.25, lw=0)
            ax.plot(yrs, pd.Series(m.values).rolling(5, center=True).mean().values,
                    color=_TS_C[scenario], lw=1.5)
        ax.axhline(0, color="#999", lw=0.6, ls="--")
        ax.set_title(title, fontsize=9, fontweight="bold" if bold else "normal")
        ax.tick_params(labelsize=7.5)
        if bold:
            for s in ax.spines.values():
                s.set_linewidth(1.6)

    for ax, sid in zip(flat, stations):
        draw(ax, obs[obs["station"] == sid], fut[fut["station"] == sid], sid, sid)
    # regional panel: station-mean series, anomaly vs regional AR6 base
    reg_obs = obs.groupby("year", as_index=False)["value"].mean(); reg_obs["station"] = "_R_"
    reg_fut = fut.groupby(["model", "year"], as_index=False)["value"].mean()
    base["_R_"] = obs[obs["year"].between(*AR6_BASELINE)].groupby("year")["value"].mean().mean()
    draw(flat[len(stations)], reg_obs, reg_fut, "_R_", "Regional mean", bold=True)
    # legend panel
    lax = flat[len(stations) + 1]; lax.axis("off")
    handles = [plt.Line2D([0], [0], color=_TS_C_OBS, lw=1.6, label="Observed (5-yr mean)"),
               plt.Line2D([0], [0], color=_TS_C[scenario], lw=1.5,
                          label=f"{scenario.upper()} MME mean (5-yr)"),
               plt.matplotlib.patches.Patch(color=_TS_C[scenario], alpha=0.25,
                                            label="Model IQR")]
    lax.legend(handles=handles, loc="center", fontsize=9, frameon=False)
    for ax in flat[len(stations) + 2:]:
        ax.axis("off")
    for ax in axes[-1, :]:
        ax.set_xlabel("Year", fontsize=8.5)
    for ax in axes[:, 0]:
        ax.set_ylabel(f"\u0394 vs {AR6_BASELINE[0]}\u2013{AR6_BASELINE[1]} (%)",
                      fontsize=8.5)
    fig.suptitle(f"{area_name}: station-scale annual rainfall anomalies "
                 f"({scenario.upper()}, AR6 baseline)", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    _save(fig, f"FUTURE_Q1_FIGURE_16_ts_station_grid_{scenario}")


def fig_ts_seasonal(monthly: pd.DataFrame, area_name: str):
    """TS-3: mean monthly rainfall — observed vs QDM historical vs the three
    AR6 windows, one panel per scenario, ensemble spread shaded."""
    style = MapStyle(); style.apply()
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.6), sharey=True)
    months = np.arange(1, 13)
    obs_clim = (monthly[monthly["dataset"] == "Observed"]
                .groupby("month")["monthly_total"].mean())
    hist = monthly[monthly["dataset"] == "BC_HIST"]
    hist_clim = hist.groupby(["model", "month"])["monthly_total"].mean().reset_index()
    win_colors = {"Near-term": "#88BDE6", "Mid-term": "#4E79A7", "Long-term": "#1B3A5C"}
    for ax, scen in zip(axes, SCENARIO_ORDER):
        hm = hist_clim.groupby("month")["monthly_total"]
        ax.fill_between(months, hist_clim.groupby("month")["monthly_total"].min(),
                        hist_clim.groupby("month")["monthly_total"].max(),
                        color=_TS_C_HIST, alpha=0.18, lw=0,
                        label="QDM historical (model range)")
        ax.plot(months, obs_clim.reindex(months), color=_TS_C_OBS, lw=1.9,
                marker="o", ms=3.5, label=f"Observed {AR6_BASELINE[0]}\u2013{AR6_BASELINE[1]}"
                if False else "Observed 1981\u20132014")
        sc = monthly[(monthly["dataset"] == "BC") & (monthly["scenario"] == scen)]
        for wname in AR6_ORDER:
            y0, y1 = AR6_WINDOWS[wname]
            wm = sc[sc["year"].between(y0, y1)]
            clim = wm.groupby(["model", "month"])["monthly_total"].mean().reset_index()
            mmean = clim.groupby("month")["monthly_total"].mean().reindex(months)
            ax.plot(months, mmean, color=win_colors[wname], lw=1.6,
                    ls={"Near-term": ":", "Mid-term": "--", "Long-term": "-"}[wname],
                    label=f"{wname} {y0}\u2013{y1}")
        ax.set_title(scen.upper())
        ax.set_xticks(months)
        ax.set_xticklabels(["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"])
        ax.set_xlabel("Month")
        ax.grid(True, lw=0.3, ls=":", color="#cccccc")
    axes[0].set_ylabel("Mean monthly rainfall (mm)")
    axes[0].legend(fontsize=8, frameon=False)
    fig.suptitle(f"{area_name}: seasonal rainfall cycle across IPCC AR6 "
                 f"assessment periods (7-GCM QDM ensemble)", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    _save(fig, "FUTURE_Q1_FIGURE_17_ts_seasonal_ar6")


def table_station_rainfall_hist(yearly: pd.DataFrame) -> pd.DataFrame:
    """TABLE_10: per-station annual rainfall (PRCPTOT) — observed vs every GCM's
    QDM bc-historical + MME, over the full record and the AR6 baseline."""
    p = yearly[yearly["index"] == "PRCPTOT"]
    rows = []
    for label, (y0, y1) in {"1981-2014": (1981, 2014),
                            f"AR6 {AR6_BASELINE[0]}-{AR6_BASELINE[1]}": AR6_BASELINE}.items():
        obs = (p[(p["dataset"] == "Observed") & p["year"].between(y0, y1)]
               .groupby("station")["value"].mean())
        hist = (p[(p["dataset"] == "BC_HIST") & p["year"].between(y0, y1)]
                .groupby(["station", "model"])["value"].mean().unstack("model"))
        for sid in obs.index:
            row = {"period": label, "station": sid,
                   "observed_mm": round(float(obs[sid]), 1)}
            if sid in hist.index:
                for m in hist.columns:
                    row[f"{m}_mm"] = round(float(hist.loc[sid, m]), 1)
                mme = float(hist.loc[sid].mean())
                row["MME_mean_mm"] = round(mme, 1)
                row["MME_bias_pct"] = round((mme / float(obs[sid]) - 1) * 100, 2)
            rows.append(row)
    return pd.DataFrame(rows)


def table_station_rainfall_ar6(yearly: pd.DataFrame) -> pd.DataFrame:
    """TABLE_11: per-station PRCPTOT for every GCM + MME across the AR6 future
    windows, with % change vs the observed AR6 baseline and sign agreement."""
    p = yearly[yearly["index"] == "PRCPTOT"]
    base = (p[(p["dataset"] == "Observed") & p["year"].between(*AR6_BASELINE)]
            .groupby("station")["value"].mean())
    rows = []
    fut = p[p["dataset"] == "BC"]
    for scen in SCENARIO_ORDER:
        for wname in AR6_ORDER:
            y0, y1 = AR6_WINDOWS[wname]
            wm = (fut[(fut["scenario"] == scen) & fut["year"].between(y0, y1)]
                  .groupby(["station", "model"])["value"].mean().unstack("model"))
            for sid in wm.index:
                vals = wm.loc[sid]
                b = base.get(sid, np.nan)
                deltas = vals / b - 1.0 if np.isfinite(b) and b > 0 else vals * np.nan
                row = {"scenario": scen, "window": wname,
                       "window_years": f"{y0}-{y1}", "station": sid,
                       "obs_baseline_mm": round(float(b), 1)}
                for m in vals.index:
                    row[f"{m}_mm"] = round(float(vals[m]), 1)
                row["MME_mean_mm"] = round(float(vals.mean()), 1)
                row["MME_median_mm"] = round(float(vals.median()), 1)
                row["MME_min_mm"] = round(float(vals.min()), 1)
                row["MME_max_mm"] = round(float(vals.max()), 1)
                row["MME_delta_pct"] = round(float(deltas.mean()) * 100, 2)
                row["sign_agreement"] = round(float(_sign_agreement(deltas)), 3)
                row["robust"] = bool(_sign_agreement(deltas) >= AGREEMENT_ROBUST)
                rows.append(row)
    return pd.DataFrame(rows)
