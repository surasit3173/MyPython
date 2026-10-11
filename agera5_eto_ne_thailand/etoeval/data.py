"""Loading, tidying and quality control of the TMD monthly station archive.

The raw archive is never modified; every QC decision is recorded as a flag
column so that the analysis can be reproduced and audited.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

logger = logging.getLogger(__name__)

MONTH_COLS: list[str] = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Physical plausibility limits for monthly means in Northeast Thailand.
# Deliberately wide: they reject only impossible values (e.g. keying errors),
# not unusual climate. Units: degC, %, h day-1, mm day-1, archive wind units.
RANGE_LIMITS: dict[str, tuple[float, float]] = {
    "tmax": (20.0, 45.0),
    "tmin": (0.0, 32.0),
    "rh": (20.0, 100.0),
    "sun": (1.0, 13.5),  # monthly means < 1 h day-1 do not occur in NE Thailand; treated as missing-value codes
    "pan": (0.0, 15.0),
    "wind_raw": (0.0, 20.0),
    "rain": (0.0, 1500.0),
}


@dataclass(frozen=True)
class Station:
    """Station metadata used in the analysis.

    Attributes
    ----------
    code : int
        TMD station code.
    name : str
        English station name.
    lat, lon : float
        Coordinates [decimal degrees] from ``station_coords15sta.csv``.
    elevation_m : float | None
        Station elevation [m a.s.l.]; ``None`` when not supplied (an assumed
        value from the configuration is then used and flagged).
    wind_label : str
        Station label exactly as written in the wind archive.
    """

    code: int
    name: str
    lat: float
    lon: float
    elevation_m: float | None
    wind_label: str


@dataclass(frozen=True)
class Config:
    """Analysis configuration loaded from ``config.yaml``."""

    raw_dir: Path
    out_dir: Path
    start_year: int
    end_year: int
    stations: tuple[Station, ...]
    assumed_elevation_m: float
    anemometer_height_m: float
    wind_units: tuple[str, ...]
    angstrom_sets: tuple[str, ...]
    seasons: dict[str, list[int]]
    bootstrap_n: int
    bootstrap_block: int
    seed: int
    alpha: float
    robust_z_limit: float
    agera5: dict[str, object] = field(default_factory=dict)


def load_config(path: str | Path) -> Config:
    """Read the YAML configuration and join station coordinates.

    Parameters
    ----------
    path : str or pathlib.Path
        Path to ``config.yaml``.

    Returns
    -------
    Config
        Frozen configuration object.
    """
    path = Path(path)
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    root = path.parent
    raw_dir = (root / cfg["paths"]["raw_dir"]).resolve()
    coords = pd.read_csv(raw_dir / cfg["paths"]["coords_file"]).set_index("stncode")
    stations: list[Station] = []
    for s in cfg["stations"]:
        code = int(s["code"])
        if code not in coords.index:
            raise KeyError(f"Station {code} missing from coordinate file")
        stations.append(
            Station(
                code=code,
                name=str(s["name"]),
                lat=float(coords.loc[code, "lat"]),
                lon=float(coords.loc[code, "lon"]),
                elevation_m=None if s.get("elevation_m") is None else float(s["elevation_m"]),
                wind_label=str(s["wind_label"]),
            )
        )
    return Config(
        raw_dir=raw_dir,
        out_dir=(root / cfg["paths"]["out_dir"]).resolve(),
        start_year=int(cfg["period"]["start_year"]),
        end_year=int(cfg["period"]["end_year"]),
        stations=tuple(stations),
        assumed_elevation_m=float(cfg["reference"]["assumed_elevation_m"]),
        anemometer_height_m=float(cfg["reference"]["anemometer_height_m"]),
        wind_units=tuple(cfg["reference"]["wind_units"]),
        angstrom_sets=tuple(cfg["reference"]["angstrom_sets"]),
        seasons={k: list(v) for k, v in cfg["seasons"].items()},
        bootstrap_n=int(cfg["statistics"]["bootstrap_n"]),
        bootstrap_block=int(cfg["statistics"]["bootstrap_block_months"]),
        seed=int(cfg["statistics"]["seed"]),
        alpha=float(cfg["statistics"]["alpha"]),
        robust_z_limit=float(cfg["qc"]["robust_z_limit"]),
        agera5=dict(cfg.get("agera5", {})),
    )


def read_tmd_monthly(path: str | Path) -> pd.DataFrame:
    """Read the TMD monthly archive (``TMD_data1961-2010.xls``) into tidy form.

    Parameters
    ----------
    path : str or pathlib.Path
        Path to the legacy ``.xls`` file.

    Returns
    -------
    pandas.DataFrame
        Columns: stncode, stn_name, year, month, tmax, tmin, rh, sun, pan, rain.
        ``pan`` is the monthly mean of daily pan evaporation [mm day-1].
    """
    df = pd.read_excel(path, engine="xlrd")
    df = df.rename(
        columns={
            "MEANMAXTEMP": "tmax", "MEANMINTEMP": "tmin", "avgrh": "rh",
            "avgsunshine": "sun", "avgevap": "pan", "TOTALRAIN": "rain",
        }
    )
    df["stn_name"] = (
        df["stn_name"].astype(str).str.replace("\t", "", regex=False).str.replace("*", "", regex=False).str.strip()
    )
    keep = ["stncode", "stn_name", "year", "month", "tmax", "tmin", "rh", "sun", "pan", "rain"]
    df = df[keep].copy()
    dup = int(df.duplicated(["stncode", "year", "month"]).sum())
    if dup:
        raise ValueError(f"{dup} duplicated station-month records in TMD archive")
    return df


def read_wind(path: str | Path, stations: tuple[Station, ...]) -> pd.DataFrame:
    """Read the wind archive (``Wind_sp1970-2010.xls``) and map labels to codes.

    Parameters
    ----------
    path : str or pathlib.Path
        Path to the legacy ``.xls`` file (wide format, one row per station-year).
    stations : tuple of Station
        Stations whose ``wind_label`` identifies their rows.

    Returns
    -------
    pandas.DataFrame
        Columns: stncode, year, month, wind_raw (archive units, not converted).
    """
    w = pd.read_excel(path, engine="xlrd")
    w["Prov"] = w["Prov"].astype(str).str.strip()
    label_to_code = {s.wind_label: s.code for s in stations}
    missing = set(label_to_code) - set(w["Prov"].unique())
    if missing:
        raise KeyError(f"Wind labels not found in archive: {sorted(missing)}")
    w = w[w["Prov"].isin(label_to_code)].copy()
    long = w.melt(id_vars=["Prov", "Year"], value_vars=MONTH_COLS, var_name="mon", value_name="wind_raw")
    long["month"] = long["mon"].map({m: i + 1 for i, m in enumerate(MONTH_COLS)})
    long["stncode"] = long["Prov"].map(label_to_code).astype(int)
    long = long.rename(columns={"Year": "year"})[["stncode", "year", "month", "wind_raw"]]
    return long


def assemble_station_table(cfg: Config) -> pd.DataFrame:
    """Merge TMD variables and wind for the configured stations and period.

    Parameters
    ----------
    cfg : Config
        Analysis configuration.

    Returns
    -------
    pandas.DataFrame
        Complete station-month grid (missing months kept as NaN rows) with
        columns stncode, year, month, tmax, tmin, rh, sun, pan, rain, wind_raw.
    """
    tmd = read_tmd_monthly(cfg.raw_dir / "TMD_data1961-2010.xls")
    wind = read_wind(cfg.raw_dir / "Wind_sp1970-2010.xls", cfg.stations)
    codes = [s.code for s in cfg.stations]
    grid = pd.MultiIndex.from_product(
        [codes, range(cfg.start_year, cfg.end_year + 1), range(1, 13)], names=["stncode", "year", "month"]
    ).to_frame(index=False)
    out = grid.merge(tmd.drop(columns="stn_name"), on=["stncode", "year", "month"], how="left")
    out = out.merge(wind, on=["stncode", "year", "month"], how="left")
    return out


def _windowed_robust_z(df: pd.DataFrame, var: str, half_window_years: int) -> pd.Series:
    """Robust z-score with local centring and a stable full-record scale.

    For each station and calendar month, every value is first centred on the
    median of the same calendar month within +/- ``half_window_years`` (the
    value itself excluded), so that step changes are not mistaken for isolated
    outliers. The residuals are then scaled by 1.4826 x MAD of all residuals of
    that station-month, which is far more stable than a MAD estimated from the
    ~10 values inside one window (important for integer-valued RH).
    """
    z = pd.Series(np.nan, index=df.index, dtype=float)
    for (_, _), g in df.groupby(["stncode", "month"]):
        years = g["year"].to_numpy()
        vals = g[var].to_numpy(dtype=float)
        resid = np.full(vals.size, np.nan)
        for i in range(vals.size):
            if not np.isfinite(vals[i]):
                continue
            sel = (np.abs(years - years[i]) <= half_window_years) & (np.arange(vals.size) != i)
            ref = vals[sel]
            ref = ref[np.isfinite(ref)]
            if ref.size >= 5:
                resid[i] = vals[i] - np.median(ref)
        ok = np.isfinite(resid)
        if ok.sum() < 10:
            continue
        scale = 1.4826 * np.median(np.abs(resid[ok] - np.median(resid[ok])))
        if scale > 0:
            z.loc[g.index[ok]] = resid[ok] / scale
    return z


def quality_control(
    df: pd.DataFrame, robust_z_limit: float, half_window_years: int = 5
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply range, internal-consistency and robust-outlier checks.

    Parameters
    ----------
    df : pandas.DataFrame
        Output of :func:`assemble_station_table`.
    robust_z_limit : float
        Values with |robust z| above this limit are flagged and set to NaN. The
        z-score is computed per station and calendar month from the median and
        MAD of the other values within +/- ``half_window_years``.
    half_window_years : int, default 5
        Half-width of the local reference window [years].

    Returns
    -------
    clean : pandas.DataFrame
        Copy of ``df`` with rejected values set to NaN and flag columns
        ``qc_<var>`` holding '' (accepted), 'range', 'tmax<=tmin' or 'robust_z'.
    log : pandas.DataFrame
        One row per rejected value with the original value and the reason.

    Notes
    -----
    The robust z-score uses 1.4826 * MAD as a consistent estimator of the
    standard deviation for Gaussian data. Because monthly climate anomalies are
    near-Gaussian, a limit of 5 rejects only gross errors. The local window
    keeps genuine step changes for the homogeneity module to assess.
    """
    clean = df.copy()
    records: list[dict[str, object]] = []
    variables = ["tmax", "tmin", "rh", "sun", "pan", "wind_raw"]
    # Monthly rainfall is strongly skewed with many near-zero dry-season months:
    # only the range check is applied (robust z would flag genuine wet extremes).
    for v in variables + ["rain"]:
        clean[f"qc_{v}"] = ""
        lo, hi = RANGE_LIMITS[v]
        bad = clean[v].notna() & ((clean[v] < lo) | (clean[v] > hi))
        for idx in clean.index[bad]:
            records.append({**clean.loc[idx, ["stncode", "year", "month"]].to_dict(), "variable": v,
                            "value": clean.at[idx, v], "reason": "range"})
        clean.loc[bad, f"qc_{v}"] = "range"
        clean.loc[bad, v] = np.nan
    inconsistent = clean["tmax"].notna() & clean["tmin"].notna() & (clean["tmax"] <= clean["tmin"])
    for idx in clean.index[inconsistent]:
        for v in ("tmax", "tmin"):
            records.append({**clean.loc[idx, ["stncode", "year", "month"]].to_dict(), "variable": v,
                            "value": clean.at[idx, v], "reason": "tmax<=tmin"})
    clean.loc[inconsistent, ["qc_tmax", "qc_tmin"]] = "tmax<=tmin"
    clean.loc[inconsistent, ["tmax", "tmin"]] = np.nan
    for v in variables:
        z = _windowed_robust_z(clean, v, half_window_years)
        bad = z.abs() > robust_z_limit
        for idx in clean.index[bad]:
            records.append({**clean.loc[idx, ["stncode", "year", "month"]].to_dict(), "variable": v,
                            "value": clean.at[idx, v], "reason": f"robust_z={z[idx]:.1f}"})
        clean.loc[bad, f"qc_{v}"] = "robust_z"
        clean.loc[bad, v] = np.nan
    log = pd.DataFrame.from_records(records, columns=["stncode", "year", "month", "variable", "value", "reason"])
    logger.info("QC rejected %d values", len(log))
    return clean, log


def completeness_table(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Per-station completeness of each variable after QC.

    Returns
    -------
    pandas.DataFrame
        Expected months, available months and percentage per variable, plus the
        number of months with all Penman-Monteith inputs present.
    """
    expected = (cfg.end_year - cfg.start_year + 1) * 12
    rows: list[dict[str, object]] = []
    name = {s.code: s.name for s in cfg.stations}
    for code, g in df.groupby("stncode"):
        row: dict[str, object] = {"stncode": code, "station": name[int(code)], "expected_months": expected}
        for v in ["tmax", "tmin", "rh", "sun", "wind_raw", "pan"]:
            row[f"{v}_n"] = int(g[v].notna().sum())
        row["rain_n"] = int(g["rain"].notna().sum())
        row["pm_complete_n"] = int(g[["tmax", "tmin", "rh", "sun", "wind_raw"]].notna().all(axis=1).sum())
        row["pm_complete_pct"] = round(100.0 * row["pm_complete_n"] / expected, 1)
        rows.append(row)
    return pd.DataFrame(rows)
