"""Administrative boundary acquisition and verification (Gate F).

Area-agnostic: the province and country are read from the configuration, so
moving to another area needs no code change.  A boundary is accepted only when
it is a real administrative polygon, its geometry is valid, its CRS is known,
and every analysis gauge falls inside it.

Sources are tried in the order given in the configuration.  Nothing is
approximated: if no source yields a verifiable polygon the module reports
NOT ESTABLISHED and Gate F stays BLOCKED.
"""
from __future__ import annotations

import hashlib
import json
import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Geod
from shapely.geometry import Point, mapping, shape

log = logging.getLogger(__name__)
GEOD = Geod(ellps="WGS84")

# Candidate ADM1 sources.  `match` names the properties that carry the country
# and the unit name in each schema.
SOURCES = [
    {"key": "natural_earth_10m_adm1",
     "title": "Natural Earth 10m Admin-1 states and provinces",
     "url": "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
            "master/geojson/ne_10m_admin_1_states_provinces.geojson",
     "licence": "public domain (Natural Earth)",
     "match": {"country": ["adm0_a3", "admin"], "name": ["name", "name_en"]},
     "scale": "1:10,000,000 (generalised)"},
    {"key": "thailand_json_apisit",
     "title": "apisit/thailand.json province polygons",
     "url": "https://raw.githubusercontent.com/apisit/thailand.json/master/"
            "thailand.json",
     "licence": "see repository",
     "match": {"country": [], "name": ["name"]},
     "scale": "unstated"},
]


@dataclass
class Boundary:
    geometry: object
    properties: dict
    source: dict
    raw_path: Path
    area_km2: float
    perimeter_km: float
    bounds: tuple
    n_vertices: int
    crs: str = "EPSG:4326"
    checks: dict = field(default_factory=dict)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return f"sha256:{h.hexdigest()}"


def fetch(source: dict, cache_dir: Path) -> Path | None:
    """Download once and cache.  A cached file is reused so a rerun is offline."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    dest = cache_dir / f"{source['key']}.geojson"
    if dest.exists() and dest.stat().st_size > 1000:
        return dest
    try:
        subprocess.run(["curl", "-sSL", "--max-time", "600", "-o", str(dest),
                        source["url"]], check=True)
    except Exception as e:                                   # pragma: no cover
        log.warning("%s: download failed (%s)", source["key"], e)
        return None
    if not dest.exists() or dest.stat().st_size < 1000:
        log.warning("%s: download produced no usable file", source["key"])
        return None
    head = dest.read_bytes()[:64]
    if head.startswith(b"version https://git-lfs"):
        log.warning("%s: file is a Git-LFS pointer, not the data", source["key"])
        return None
    return dest


def select(path: Path, source: dict, unit_name: str,
           country: str | None) -> tuple | None:
    """Find the ADM1 feature for `unit_name` (optionally within `country`)."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    feats = doc.get("features", [])
    name_keys = source["match"]["name"]
    country_keys = source["match"]["country"]
    hits = []
    for f in feats:
        p = f.get("properties", {})
        if country and country_keys:
            if not any(str(p.get(k, "")).lower() in
                       (country.lower(), country.lower()[:3])
                       for k in country_keys):
                continue
        if any(str(p.get(k, "")).strip().lower() == unit_name.lower()
               for k in name_keys):
            hits.append(f)
    if len(hits) != 1:
        log.warning("%s: %d features matched %r", source["key"], len(hits),
                    unit_name)
        return None
    return hits[0], doc.get("crs", {})


def describe(feature, source, path) -> Boundary:
    g = shape(feature["geometry"])
    area, per = GEOD.geometry_area_perimeter(g)
    polys = [g] if g.geom_type == "Polygon" else list(g.geoms)
    n = sum(len(p.exterior.coords) for p in polys)
    return Boundary(geometry=g, properties=feature.get("properties", {}),
                    source=source, raw_path=path,
                    area_km2=abs(area) / 1e6, perimeter_km=abs(per) / 1e3,
                    bounds=tuple(round(v, 4) for v in g.bounds), n_vertices=n)


def verify(b: Boundary, stations: pd.DataFrame,
           reference_area_km2: float | None = None,
           area_tolerance_pct: float = 10.0) -> Boundary:
    g = b.geometry
    bx = g.bounds
    fw, fh = bx[2] - bx[0], bx[3] - bx[1]
    rect = (b.n_vertices <= 6 and abs(abs(g.area) - fw * fh) / (fw * fh) < 0.02)

    inside, rows = 0, []
    for r in stations.itertuples():
        p = Point(float(r.longitude), float(r.latitude))
        ins = g.contains(p) or g.touches(p)
        boundary_line = (g.exterior if g.geom_type == "Polygon"
                         else max(g.geoms, key=lambda q: q.area).exterior)
        q = boundary_line.interpolate(boundary_line.project(p))
        d = GEOD.inv(p.x, p.y, q.x, q.y)[2] / 1000.0
        inside += int(ins)
        rows.append({"station": str(r.station), "longitude": float(r.longitude),
                     "latitude": float(r.latitude), "inside_polygon": bool(ins),
                     "distance_to_boundary_km": round(d, 3)})
    containment = pd.DataFrame(rows)

    area_ok = True
    area_dev = np.nan
    if reference_area_km2:
        area_dev = 100 * (b.area_km2 - reference_area_km2) / reference_area_km2
        area_ok = abs(area_dev) <= area_tolerance_pct

    b.checks = {
        "administrative_unit": b.properties.get("name")
                               or b.properties.get("name_en"),
        "local_name": b.properties.get("name_local"),
        "country": b.properties.get("admin"),
        "iso_3166_2": b.properties.get("iso_3166_2"),
        "admin_level": b.properties.get("type_en") or "ADM1",
        "geometry_type": g.geom_type,
        "geometry_valid": bool(g.is_valid),
        "is_rectangular_frame": bool(rect),
        "n_vertices": b.n_vertices,
        "area_km2": round(b.area_km2, 1),
        "perimeter_km": round(b.perimeter_km, 1),
        "reference_area_km2": reference_area_km2,
        "area_deviation_pct": (round(float(area_dev), 2)
                               if np.isfinite(area_dev) else None),
        "area_within_tolerance": bool(area_ok),
        "bounds_lon_lat": list(b.bounds),
        "crs": b.crs,
        "n_stations": int(len(containment)),
        "n_stations_inside": int(inside),
        "all_stations_inside": bool(inside == len(containment)),
        "source_file_hash": _sha256(b.raw_path),
        "source_url": b.source["url"],
        "source_title": b.source["title"],
        "source_scale": b.source.get("scale"),
        "accessed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "_containment": containment,
    }
    b.checks["verified"] = bool(
        g.is_valid and not rect and b.checks["all_stations_inside"]
        and b.n_vertices > 6 and area_ok)
    return b


def cross_source(bs: list[Boundary]) -> pd.DataFrame:
    """Compare candidates.  Identical vertex counts and IoU = 1 mean the sources
    are NOT independent, which must be reported rather than presented as
    agreement."""
    rows = []
    for i in range(len(bs)):
        for j in range(i + 1, len(bs)):
            a, c = bs[i], bs[j]
            inter, union = a.geometry.intersection(c.geometry), \
                a.geometry.union(c.geometry)
            ai, _ = GEOD.geometry_area_perimeter(inter)
            au, _ = GEOD.geometry_area_perimeter(union)
            iou = abs(ai) / abs(au) if au else np.nan
            ca, cc = a.geometry.centroid, c.geometry.centroid
            rows.append({
                "source_a": a.source["key"], "source_b": c.source["key"],
                "area_a_km2": round(a.area_km2, 1),
                "area_b_km2": round(c.area_km2, 1),
                "vertices_a": a.n_vertices, "vertices_b": c.n_vertices,
                "IoU": round(float(iou), 4),
                "centroid_offset_km": round(
                    GEOD.inv(ca.x, ca.y, cc.x, cc.y)[2] / 1000, 3),
                "independent_sources": bool(
                    not (a.n_vertices == c.n_vertices and iou > 0.9999)),
                "note": ("identical vertex count and IoU = 1: the second source "
                         "is derived from the first, so this is NOT an "
                         "independent confirmation")
                if (a.n_vertices == c.n_vertices and iou > 0.9999) else
                "geometries differ; comparison is informative"})
    return pd.DataFrame(rows)


def write_canonical(b: Boundary, out_dir: Path, area_name: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"{area_name.lower().replace(' ', '_')}_adm1_verified.geojson"
    doc = {"type": "FeatureCollection",
           "crs": {"type": "name",
                   "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
           "provenance": {k: v for k, v in b.checks.items()
                          if not k.startswith("_")},
           "features": [{"type": "Feature", "properties": b.properties,
                         "geometry": mapping(b.geometry)}]}
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return p


def acquire_and_verify(cfg, stations: pd.DataFrame,
                       cache_dir: Path) -> tuple[Boundary | None, dict]:
    """Full Gate F workflow.  Returns the accepted boundary (or None) and a
    dictionary of report tables."""
    a = cfg.raw["area"]
    unit = a.get("adm1_name") or a["name"]
    country = a.get("country_iso3") or a.get("country")
    ref_area = a.get("reference_area_km2")
    cands, attempts = [], []
    for src in SOURCES:
        path = fetch(src, cache_dir)
        if path is None:
            attempts.append({"source": src["key"], "status": "unavailable",
                             "detail": "download failed or Git-LFS pointer"})
            continue
        sel = select(path, src, unit, country)
        if sel is None:
            attempts.append({"source": src["key"], "status": "no match",
                             "detail": f"no unique feature named {unit!r}"})
            continue
        b = verify(describe(sel[0], src, path), stations, ref_area)
        cands.append(b)
        attempts.append({"source": src["key"],
                         "status": "verified" if b.checks["verified"]
                         else "rejected",
                         "detail": f"area {b.checks['area_km2']} km2, "
                                   f"{b.checks['n_stations_inside']}/"
                                   f"{b.checks['n_stations']} gauges inside, "
                                   f"valid={b.checks['geometry_valid']}"})
    if not cands:
        return None, {"attempts": pd.DataFrame(attempts),
                      "cross_source": pd.DataFrame()}
    accepted = next((b for b in cands if b.checks["verified"]), None)
    return accepted, {"attempts": pd.DataFrame(attempts),
                      "cross_source": cross_source(cands),
                      "candidates": cands}
