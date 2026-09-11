"""
geo.py
======
Dependency-free geospatial helpers so the GIS figures work without geopandas/
pyproj (which are not always installable). Two pieces:

  * read_polygon_shapefile() -- minimal ESRI .shp polygon reader (type 5)
  * lonlat_to_utm()          -- WGS84 forward Transverse-Mercator (UTM)

Both are generic: point them at any boundary .shp + station lon/lat and a UTM
zone, and the GIS layer works for a new study area with no code changes.
"""
from __future__ import annotations
import struct
import numpy as np

# WGS84 ellipsoid
_A = 6378137.0
_F = 1.0 / 298.257223563
_E2 = _F * (2 - _F)
_EP2 = _E2 / (1 - _E2)
_K0 = 0.9996
_FE = 500000.0


def read_polygon_shapefile(path: str):
    """Return (rings, bbox).

    rings : list of (x, y) ndarrays, one per polygon ring (part).
    bbox  : (xmin, ymin, xmax, ymax) in the shapefile's own CRS units.
    """
    with open(path, "rb") as f:
        data = f.read()
    shtype = struct.unpack("<i", data[32:36])[0]
    if shtype != 5:
        raise ValueError(f"Expected polygon shapefile (type 5), got {shtype}")
    bbox = struct.unpack("<4d", data[36:68])
    rings = []
    pos = 100                                   # skip 100-byte header
    n = len(data)
    while pos + 8 <= n:
        # record header (big-endian): record number, content length (words)
        _, clen = struct.unpack(">2i", data[pos:pos + 8])
        pos += 8
        rec_end = pos + clen * 2
        rshtype = struct.unpack("<i", data[pos:pos + 4])[0]
        if rshtype != 5:
            pos = rec_end
            continue
        nparts = struct.unpack("<i", data[pos + 36:pos + 40])[0]
        npoints = struct.unpack("<i", data[pos + 40:pos + 44])[0]
        pp = pos + 44
        parts = struct.unpack(f"<{nparts}i", data[pp:pp + 4 * nparts])
        pp += 4 * nparts
        coords = struct.unpack(f"<{2 * npoints}d", data[pp:pp + 16 * npoints])
        xy = np.array(coords).reshape(-1, 2)
        bounds = list(parts) + [npoints]
        for i in range(nparts):
            seg = xy[bounds[i]:bounds[i + 1]]
            rings.append((seg[:, 0], seg[:, 1]))
        pos = rec_end
    return rings, bbox


def lonlat_to_utm(lon, lat, lon0_deg: float):
    """WGS84 lon/lat (degrees) -> UTM easting/northing (metres), northern zone.

    lon0_deg is the zone's central meridian (e.g. 99 for UTM zone 47N).
    Vectorised; lon/lat may be scalars or arrays. Snyder (1987) series.
    """
    lon = np.radians(np.asarray(lon, float))
    lat = np.radians(np.asarray(lat, float))
    lon0 = np.radians(lon0_deg)

    N = _A / np.sqrt(1 - _E2 * np.sin(lat) ** 2)
    T = np.tan(lat) ** 2
    C = _EP2 * np.cos(lat) ** 2
    Aa = (lon - lon0) * np.cos(lat)
    M = _A * ((1 - _E2 / 4 - 3 * _E2**2 / 64 - 5 * _E2**3 / 256) * lat
              - (3 * _E2 / 8 + 3 * _E2**2 / 32 + 45 * _E2**3 / 1024) * np.sin(2 * lat)
              + (15 * _E2**2 / 256 + 45 * _E2**3 / 1024) * np.sin(4 * lat)
              - (35 * _E2**3 / 3072) * np.sin(6 * lat))
    east = _FE + _K0 * N * (Aa + (1 - T + C) * Aa**3 / 6
                            + (5 - 18 * T + T**2 + 72 * C - 58 * _EP2) * Aa**5 / 120)
    north = _K0 * (M + N * np.tan(lat) * (Aa**2 / 2
                   + (5 - T + 9 * C + 4 * C**2) * Aa**4 / 24
                   + (61 - 58 * T + T**2 + 600 * C - 330 * _EP2) * Aa**6 / 720))
    return east, north
