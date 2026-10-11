"""AgERA5 v2.0 retrieval from the Copernicus Climate Data Store and point extraction.

Workflow
--------
1. :func:`download` submits one CDS request per variable/statistic and year for a
   small bounding box (configured in ``config.yaml``) and stores the returned zip
   archives of daily netCDF files.
2. :func:`extract_station_daily` reads every daily file and extracts values at
   the station coordinates with two methods (nearest grid cell and bilinear
   interpolation of the four surrounding cells), converting units to those used
   by FAO-56.
3. :func:`monthly_from_daily` aggregates to complete calendar months.

Notes
-----
* Request keys follow the CDS form for ``sis-agrometeorological-indicators``.
  In version 2_0 the flux variables (solar radiation, precipitation) take no
  ``statistic``. The variable name of reference evapotranspiration must be
  confirmed once on the CDS download page ("Show API request code"); it is a
  configuration value, not hard-coded.
* AgERA5 is land-only (HRES land-sea mask, land fraction > 0.05). Bilinear
  weights are renormalised over non-missing cells.
* Each netCDF file holds a single data variable; it is identified by position,
  not by name, so changes of internal variable names between versions do not
  break the extraction.

References
----------
Copernicus Climate Change Service (2025). Agrometeorological indicators from
    1979 to present derived from reanalysis, version 2.0. Algorithm Theoretical
    Basis Document (ATBD). ECMWF Confluence, CKB page 278550984.
"""
from __future__ import annotations

import logging
import re
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from . import fao56
from .data import Config, Station

logger = logging.getLogger(__name__)

OUTPUT_COLUMNS: dict[str, str] = {
    "tmax": "tmax_c", "tmin": "tmin_c", "vp": "vp_kpa", "u10": "u10_ms", "rs": "rs_mj", "eto": "eto_mm_day",
    "pr": "pr_mm_day",
}
METHODS: tuple[str, ...] = ("nearest", "bilinear", "idw")
PLAUSIBLE: dict[str, tuple[float, float]] = {
    "tmax_c": (5.0, 48.0), "tmin_c": (-5.0, 35.0), "vp_kpa": (0.2, 5.0),
    "u10_ms": (0.0, 20.0), "rs_mj": (0.0, 40.0), "eto_mm_day": (0.0, 15.0), "pr_mm_day": (0.0, 60.0),
}


@dataclass(frozen=True)
class RequestSpec:
    """One CDS request."""

    key: str
    year: int
    request: dict[str, object]
    target: Path


def build_requests(cfg: Config, years: list[int]) -> list[RequestSpec]:
    """Create the list of CDS requests (one per variable key and year).

    Parameters
    ----------
    cfg : Config
        Configuration with an ``agera5`` section.
    years : list of int
        Years to download.

    Returns
    -------
    list of RequestSpec
    """
    a = cfg.agera5
    root = Path(str(a["download_dir"]))
    if not root.is_absolute():
        root = cfg.raw_dir.parent.parent / root
    specs: list[RequestSpec] = []
    for key, rq in dict(a["requests"]).items():
        for y in years:
            req: dict[str, object] = {
                "variable": rq["variable"],
                "year": [str(y)],
                "month": [f"{m:02d}" for m in range(1, 13)],
                "day": [f"{d:02d}" for d in range(1, 32)],
                "version": str(a["version"]),
                "area": list(a["area"]),
            }
            if rq.get("statistic"):
                req["statistic"] = [rq["statistic"]]
            specs.append(RequestSpec(key, y, req, root / key / f"agera5_{key}_{y}.zip"))
    return specs


def download(cfg: Config, years: list[int], overwrite: bool = False, dry_run: bool = False) -> pd.DataFrame:
    """Download AgERA5 v2.0 data with ``cdsapi``.

    Parameters
    ----------
    cfg : Config
        Configuration.
    years : list of int
        Years to retrieve.
    overwrite : bool, default False
        Re-download existing archives.
    dry_run : bool, default False
        Only print the requests.

    Returns
    -------
    pandas.DataFrame
        Status table (key, year, target, status, message).

    Raises
    ------
    RuntimeError
        If any request failed (after all requests were attempted).
    """
    specs = build_requests(cfg, years)
    rows: list[dict[str, object]] = []
    client = None
    if not dry_run:
        import cdsapi  # imported lazily: not needed for the analysis stages

        client = cdsapi.Client()
    for sp in specs:
        status, msg = "skipped", ""
        if dry_run:
            print(cfg.agera5["dataset"], sp.request)
            status = "dry-run"
        elif sp.target.exists() and not overwrite:
            status = "exists"
        else:
            sp.target.parent.mkdir(parents=True, exist_ok=True)
            try:
                client.retrieve(str(cfg.agera5["dataset"]), sp.request).download(str(sp.target))
                status = "ok"
            except Exception as exc:  # noqa: BLE001 - recorded and re-raised below
                logger.exception("Request failed: %s %s", sp.key, sp.year)
                status, msg = "failed", str(exc)
        rows.append({"key": sp.key, "year": sp.year, "target": str(sp.target), "status": status, "message": msg})
    table = pd.DataFrame(rows)
    if (table["status"] == "failed").any():
        raise RuntimeError(f"{int((table['status'] == 'failed').sum())} CDS requests failed:\n{table[table.status == 'failed']}")
    return table


def _date_from_name(name: str) -> pd.Timestamp | None:
    m = re.search(r"(19|20)\d{6}", name)
    return pd.Timestamp(m.group(0)) if m else None


def _single_data_var(ds: xr.Dataset) -> xr.DataArray:
    cands = [v for v in ds.data_vars if {"lat", "lon"} <= set(ds[v].dims) or {"latitude", "longitude"} <= set(ds[v].dims)]
    if len(cands) != 1:
        raise ValueError(f"Expected one gridded data variable, found {cands}")
    da = ds[cands[0]]
    return da.rename({"latitude": "lat", "longitude": "lon"}) if "latitude" in da.dims else da


def point_values(da: xr.DataArray, lat: float, lon: float, idw_power: float = 1.0) -> tuple[float, float, float]:
    """Nearest-cell, bilinear and inverse-distance-weighted values at one point.

    Parameters
    ----------
    da : xarray.DataArray
        Field with dimensions (lat, lon), possibly with NaN over water.
    lat, lon : float
        Target coordinates.
    idw_power : float, default 1.0
        IDW exponent. A power of 1 over the 3 x 3 block of cell centres around
        the nearest cell follows the simple IDW of Soulis et al. (2025, Eq. 9).

    Returns
    -------
    tuple of float
        (nearest, bilinear, idw). Weights are renormalised over finite cells;
        NaN if no surrounding cell is finite.

    Notes
    -----
    Distances for IDW are great-circle approximations in km
    (equirectangular projection), adequate at 0.1 deg spacing.
    """
    lats = da["lat"].to_numpy()
    lons = da["lon"].to_numpy()
    vals = da.to_numpy()
    i = int(np.argmin(np.abs(lats - lat)))
    j = int(np.argmin(np.abs(lons - lon)))
    nearest = float(vals[i, j])
    asc_lat = lats[0] < lats[-1]
    il = np.searchsorted(lats if asc_lat else lats[::-1], lat) - 1
    if not asc_lat:
        il = lats.size - 2 - il
    jl = np.searchsorted(lons, lon) - 1
    il = int(np.clip(il, 0, lats.size - 2))
    jl = int(np.clip(jl, 0, lons.size - 2))
    la0, la1 = lats[il], lats[il + 1]
    lo0, lo1 = lons[jl], lons[jl + 1]
    ty = (lat - la0) / (la1 - la0)
    tx = (lon - lo0) / (lo1 - lo0)
    w = np.array([(1 - ty) * (1 - tx), (1 - ty) * tx, ty * (1 - tx), ty * tx])
    v = np.array([vals[il, jl], vals[il, jl + 1], vals[il + 1, jl], vals[il + 1, jl + 1]], dtype=float)
    ok = np.isfinite(v)
    bil = float(np.sum(w[ok] * v[ok]) / np.sum(w[ok])) if ok.any() and np.sum(w[ok]) > 0 else np.nan
    i0, i1 = max(i - 1, 0), min(i + 2, lats.size)
    j0, j1 = max(j - 1, 0), min(j + 2, lons.size)
    bl, bo = np.meshgrid(lats[i0:i1], lons[j0:j1], indexing="ij")
    block = vals[i0:i1, j0:j1].astype(float)
    dy = (bl - lat) * 111.195
    dx = (bo - lon) * 111.195 * np.cos(np.deg2rad(lat))
    d = np.hypot(dx, dy)
    okb = np.isfinite(block)
    if not okb.any():
        idw = np.nan
    elif np.any(d[okb] < 1e-6):
        idw = float(block[okb][np.argmin(d[okb])])
    else:
        wb = 1.0 / d[okb] ** idw_power
        idw = float(np.sum(wb * block[okb]) / np.sum(wb))
    return nearest, bil, idw


def _convert_units(col: str, values: np.ndarray, units: str) -> np.ndarray:
    u = (units or "").lower().replace(" ", "")
    finite = values[np.isfinite(values)]
    med = float(np.median(finite)) if finite.size else np.nan
    if col in ("tmax_c", "tmin_c") and (u in ("k", "kelvin") or med > 150.0):
        return values - 273.15
    if col == "vp_kpa" and (u == "hpa" or med > 6.0):
        return values / 10.0
    if col == "rs_mj" and ("j" in u and "mj" not in u or med > 1.0e3):
        return values / 1.0e6
    return values


def extract_station_daily(cfg: Config, keys: list[str] | None = None) -> pd.DataFrame:
    """Extract daily AgERA5 values at the station coordinates.

    Parameters
    ----------
    cfg : Config
        Configuration (stations, download directory).
    keys : list of str, optional
        Variable keys to extract (default: all configured).

    Returns
    -------
    pandas.DataFrame
        Wide table: stncode, date, method ('nearest' | 'bilinear' | 'idw') and one
        column per variable in FAO-56 units (see ``OUTPUT_COLUMNS``).

    Raises
    ------
    ValueError
        If extracted values fall outside physical plausibility limits, which
        indicates a unit or variable mismatch.
    """
    a = cfg.agera5
    root = Path(str(a["download_dir"]))
    if not root.is_absolute():
        root = cfg.raw_dir.parent.parent / root
    keys = keys or list(dict(a["requests"]).keys())
    records: list[dict[str, object]] = []
    for key in keys:
        col = OUTPUT_COLUMNS[key]
        zips = sorted((root / key).glob("*.zip"))
        if not zips:
            raise FileNotFoundError(f"No archives for '{key}' in {root / key}")
        for zp in zips:
            with zipfile.ZipFile(zp) as zf, tempfile.TemporaryDirectory() as tmp:
                for member in sorted(n for n in zf.namelist() if n.endswith(".nc")):
                    path = Path(zf.extract(member, tmp))
                    with xr.open_dataset(path, decode_times=False) as ds:
                        da = _single_data_var(ds).squeeze(drop=True)
                        units = str(da.attrs.get("units", ""))
                        date = _date_from_name(member)
                        if date is None:
                            raise ValueError(f"Cannot parse date from {member}")
                        for s in cfg.stations:
                            conv = _convert_units(col, np.array(point_values(da, s.lat, s.lon)), units)
                            for meth, val in zip(METHODS, conv):
                                records.append({"stncode": s.code, "date": date, "method": meth, "var": col, "value": val})
    long = pd.DataFrame.from_records(records)
    wide = long.pivot_table(index=["stncode", "date", "method"], columns="var", values="value").reset_index()
    for col, (lo, hi) in PLAUSIBLE.items():
        if col in wide and wide[col].notna().any():
            med = float(wide[col].median())
            if not lo <= med <= hi:
                raise ValueError(f"{col}: median {med:.3g} outside [{lo}, {hi}] - check units/variable name")
    return wide


def monthly_from_daily(daily: pd.DataFrame) -> pd.DataFrame:
    """Aggregate daily point values to complete calendar months.

    Parameters
    ----------
    daily : pandas.DataFrame
        Output of :func:`extract_station_daily`.

    Returns
    -------
    pandas.DataFrame
        stncode, method, year, month, monthly means of the input variables,
        ``eto_native_mm_month`` (sum of daily ETo), ``eto_native_mm_day`` and
        ``pr_mm_month`` (sum of daily precipitation). A variable is set to NaN
        in months with any missing day (no infilling).
    """
    d = daily.copy()
    d["date"] = pd.to_datetime(d["date"])
    d["year"] = d["date"].dt.year
    d["month"] = d["date"].dt.month
    keys = ["stncode", "method", "year", "month"]
    means = d.groupby(keys)[["tmax_c", "tmin_c", "vp_kpa", "u10_ms", "rs_mj"]].mean()
    eto_sum = d.groupby(keys)["eto_mm_day"].sum(min_count=1).rename("eto_native_mm_month")
    pr_sum = d.groupby(keys)["pr_mm_day"].sum(min_count=1).rename("pr_mm_month")
    n_days = d.groupby(keys)["eto_mm_day"].count().rename("n_days")
    counts = d.groupby(keys)[["tmax_c", "tmin_c", "vp_kpa", "u10_ms", "rs_mj", "eto_mm_day", "pr_mm_day"]].count()
    out = pd.concat([means, eto_sum, pr_sum, n_days], axis=1).reset_index()
    out["days"] = pd.to_datetime(dict(year=out["year"], month=out["month"], day=1)).dt.days_in_month
    # A month is kept per variable only when every day is present (no infilling).
    pairs = {"tmax_c": "tmax_c", "tmin_c": "tmin_c", "vp_kpa": "vp_kpa", "u10_ms": "u10_ms", "rs_mj": "rs_mj",
             "eto_native_mm_month": "eto_mm_day", "pr_mm_month": "pr_mm_day"}
    for col, src in pairs.items():
        ok = counts[src].reset_index(drop=True).to_numpy() == out["days"].to_numpy()
        out.loc[~ok, col] = np.nan
    out["eto_native_mm_day"] = out["eto_native_mm_month"] / out["days"]
    return out


def agera5_pm_monthly(monthly: pd.DataFrame, stations: tuple[Station, ...], z_default: float) -> pd.DataFrame:
    """Recompute FAO-56 PM ETo from monthly AgERA5 inputs (replication check).

    Parameters
    ----------
    monthly : pandas.DataFrame
        Output of :func:`monthly_from_daily`.
    stations : tuple of Station
        Station metadata (latitude, elevation).
    z_default : float
        Elevation used where a station elevation is not configured.

    Returns
    -------
    pandas.DataFrame
        Input table plus ``u2``, ``ra`` and ``eto_pm_mm_day`` (G = 0).

    Notes
    -----
    Differences between ``eto_pm_mm_day`` and the native daily-summed ETo arise
    from (i) computing PM on monthly means instead of daily values (Jensen's
    inequality) and (ii) implementation details of the native product (PCSE
    routine). Small differences validate the input-substitution attribution.
    """
    out = monthly.copy()
    lat = out["stncode"].map({s.code: s.lat for s in stations})
    z = out["stncode"].map({s.code: (s.elevation_m if s.elevation_m is not None else z_default) for s in stations})
    doy = fao56.mid_month_doy(out["month"])
    out["ra"] = fao56.extraterrestrial_radiation(lat, doy)
    out["u2"] = fao56.wind_to_2m(out["u10_ms"], 10.0)
    out["z"] = z
    out["eto_pm_mm_day"] = fao56.eto_penman_monteith(
        out["tmax_c"], out["tmin_c"], out["vp_kpa"], out["u2"], out["rs_mj"], out["ra"], out["z"], 0.0
    )
    return out
