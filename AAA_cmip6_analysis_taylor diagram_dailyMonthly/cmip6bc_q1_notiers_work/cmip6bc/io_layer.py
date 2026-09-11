"""
io_layer.py — file discovery, loading, cleaning and calendar alignment.

Design notes
------------
1. NoData is masked BEFORE negative clipping.  The reverse order silently
   converts declared missing flags such as -99 / -999 into legitimate zeros.
2. Negative values are clipped only when they fall inside a declared
   tolerance (numerical artefacts from unit conversion).  Anything deeper is
   reported and left as NaN so it cannot pass unnoticed.
3. Calendars are detected, never coerced.  Each model keeps its own paired
   index against the observations; a separate all-model common index is
   computed for tests that genuinely require a common-day sample.
4. Nothing about the region is hard-coded: station list, model names and
   file selection all derive from config + file headers.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from provenance import Provenance


# ═══════════════════════════════════════════════════════════════════════════
#  Containers
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SeriesBundle:
    """One daily rainfall dataset (observed or one model)."""
    name: str
    kind: str                       # 'observed' | 'raw' | 'legacy_bc'
    path: str
    df: pd.DataFrame                # DatetimeIndex × station columns
    calendar: str
    unit_factor: float
    n_rows: int
    n_nodata_masked: int
    n_negative_clipped: int
    min_raw_value: float
    stations: list[str] = field(default_factory=list)


@dataclass
class Dataset:
    observed: SeriesBundle
    raw: dict[str, SeriesBundle]
    legacy_bc: dict[str, SeriesBundle]
    stations: list[str]
    station_meta: pd.DataFrame
    common_index: pd.DatetimeIndex          # intersection across obs + all models
    paired_index: dict[str, pd.DatetimeIndex]   # per model: obs ∩ model


# ═══════════════════════════════════════════════════════════════════════════
#  Discovery
# ═══════════════════════════════════════════════════════════════════════════

def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _matches_region(path: Path, tag: str | None) -> bool:
    if not tag:
        return True
    return _norm(tag) in _norm(path.stem)


def _extract_model(filename: str, regex: str) -> str | None:
    m = re.match(regex, filename)
    return m.group("model") if m else None


def discover_files(cfg: dict) -> tuple[Path, dict[str, Path], dict[str, Path]]:
    """Return (observed_path, {model: raw_path}, {model: legacy_bc_path})."""
    data_dir = Path(cfg["paths"]["data_dir"])
    if not data_dir.is_dir():
        raise FileNotFoundError(f"data_dir not found: {data_dir}")

    dsc = cfg["discovery"]
    tag = cfg["region"].get("tag")

    obs_candidates = sorted(
        f for f in data_dir.rglob(dsc["observed_glob"]) if _matches_region(f, tag)
    )
    if not obs_candidates:
        raise FileNotFoundError(
            f"No observed file matching {dsc['observed_glob']} "
            f"(region tag={tag!r}) under {data_dir}"
        )
    if len(obs_candidates) > 1:
        print(f"    [warn] {len(obs_candidates)} observed files matched; "
              f"using {obs_candidates[0].name}")
    obs_path = obs_candidates[0]

    def _collect(glob_pat: str, regex: str, exclude: Iterable[Path] = ()) -> dict[str, Path]:
        out: dict[str, Path] = {}
        excl = {p.resolve() for p in exclude}
        for f in sorted(data_dir.rglob(glob_pat)):
            if f.resolve() in excl or not _matches_region(f, tag):
                continue
            model = _extract_model(f.name, regex)
            if model is None:
                print(f"    [warn] model name not parsed, skipped: {f.name}")
                continue
            if model in out:
                print(f"    [warn] duplicate model {model!r}, keeping {out[model].name}")
                continue
            out[model] = f
        return out

    legacy = _collect(dsc["legacy_bc_glob"], dsc["legacy_bc_model_regex"])
    # raw glob 'pr_*.csv' does not match 'bc_pr_*.csv', but exclude defensively
    raw = _collect(dsc["raw_glob"], dsc["raw_model_regex"],
                   exclude=list(legacy.values()) + [obs_path])

    if not raw:
        raise FileNotFoundError(
            f"No raw model files matched {dsc['raw_glob']} with regex "
            f"{dsc['raw_model_regex']!r} under {data_dir}"
        )
    return obs_path, raw, legacy


# ═══════════════════════════════════════════════════════════════════════════
#  Calendar
# ═══════════════════════════════════════════════════════════════════════════

def detect_calendar(md_pairs: set[tuple[int, int]], n_years: int) -> str:
    """Classify a CMIP6-style calendar from the observed (month, day) set."""
    if (2, 29) in md_pairs:
        return "standard"
    max_day = {}
    for m, d in md_pairs:
        max_day[m] = max(max_day.get(m, 0), d)
    if all(v == 30 for v in max_day.values()) and len(max_day) == 12:
        return "360_day"
    if max_day.get(2) == 28:
        return "365_day"
    return "irregular"


# ═══════════════════════════════════════════════════════════════════════════
#  Loading
# ═══════════════════════════════════════════════════════════════════════════

def load_daily(path: Path, name: str, kind: str, cfg: dict,
               keep_stations: list[str] | None = None) -> SeriesBundle:
    tcfg, dcfg = cfg["time"], cfg["data"]
    ycol, mcol, dcol = tcfg["year_col"], tcfg["month_col"], tcfg["day_col"]

    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]
    missing = {ycol, mcol, dcol} - set(df.columns)
    if missing:
        raise ValueError(f"{path.name}: missing time columns {sorted(missing)}")

    value_cols = [c for c in df.columns if c not in {ycol, mcol, dcol}]
    if keep_stations is not None:
        value_cols = [c for c in value_cols if c in set(keep_stations)]
    if not value_cols:
        raise ValueError(f"{path.name}: no station columns retained")

    vals = df[value_cols].apply(pd.to_numeric, errors="coerce")
    min_raw = float(np.nanmin(vals.to_numpy(dtype=float))) if len(vals) else np.nan

    # ── 1. mask declared NoData FIRST ────────────────────────────────────
    arr = np.array(vals.to_numpy(dtype=float), copy=True)
    nodata_mask = np.zeros(arr.shape, dtype=bool)
    for flag in dcfg["nodata_values"]:
        nodata_mask |= np.isclose(arr, float(flag), rtol=1e-9, atol=0.0)
    n_nodata = int(nodata_mask.sum())
    arr[nodata_mask] = np.nan

    # ── 2. then handle residual negatives ────────────────────────────────
    tol = float(dcfg["negative_tolerance_mm"])
    neg = (~np.isnan(arr)) & (arr < 0)
    deep_neg = neg & (arr < -tol)
    n_deep = int(deep_neg.sum())
    n_clipped = int((neg & ~deep_neg).sum())
    if dcfg["negative_handling"] == "clip_to_zero":
        arr[neg & ~deep_neg] = 0.0
    arr[deep_neg] = np.nan          # never silently rescued

    vals = pd.DataFrame(arr, columns=value_cols, index=df.index)

    # ── 3. unit detection ────────────────────────────────────────────────
    factor = 1.0
    if dcfg.get("unit_autodetect", True):
        pos = arr[np.isfinite(arr) & (arr > 0)]
        if pos.size:
            p999 = float(np.quantile(pos, 0.999))
            if p999 < float(dcfg["flux_detect_threshold"]):
                factor = float(dcfg["flux_to_mmday"])
                vals = vals * factor
    # ── 4. calendar-safe date index ──────────────────────────────────────
    idx = pd.to_datetime(
        dict(year=df[ycol].astype(int),
             month=df[mcol].astype(int),
             day=df[dcol].astype(int)),
        errors="coerce",
    )
    bad = int(idx.isna().sum())
    if bad:
        print(f"    [warn] {path.name}: {bad} unparseable dates dropped")
    vals = vals.loc[idx.notna().to_numpy()]
    idx = idx[idx.notna()]
    vals.index = pd.DatetimeIndex(idx)
    vals = vals[~vals.index.duplicated(keep="first")].sort_index()

    md = set(zip(vals.index.month.tolist(), vals.index.day.tolist()))
    cal = detect_calendar(md, n_years=vals.index.year.nunique())

    return SeriesBundle(
        name=name, kind=kind, path=str(path), df=vals, calendar=cal,
        unit_factor=factor, n_rows=len(vals), n_nodata_masked=n_nodata,
        n_negative_clipped=n_clipped, min_raw_value=min_raw,
        stations=list(vals.columns),
    ), n_deep


# ═══════════════════════════════════════════════════════════════════════════
#  Station metadata
# ═══════════════════════════════════════════════════════════════════════════

def load_station_meta(cfg: dict, stations: list[str]) -> pd.DataFrame:
    """
    Join station metadata, flagging elevation provenance.

    The source table is never edited.  Verified values live in a separate
    override file so that patched numbers remain traceable.
    """
    meta_path = Path(cfg["paths"]["station_meta"])
    nodata = [float(x) for x in cfg["data"]["nodata_values"]]

    if not meta_path.is_file():
        print(f"    [warn] station metadata not found: {meta_path}")
        return pd.DataFrame({"station": stations, "lat": np.nan, "lon": np.nan,
                             "elev_m": np.nan, "elev_source": "missing"})

    meta = pd.read_csv(meta_path)
    meta.columns = [str(c).strip().lower() for c in meta.columns]
    rename = {"code": "station", "latitude": "lat", "longitude": "lon",
              "elev": "elev_m", "elevation": "elev_m"}
    meta = meta.rename(columns={k: v for k, v in rename.items() if k in meta.columns})
    if "station" not in meta.columns:
        raise ValueError(f"{meta_path.name}: no CODE/station column")
    meta["station"] = meta["station"].astype(str).str.strip()

    out = pd.DataFrame({"station": [str(s) for s in stations]}).merge(
        meta[[c for c in ["station", "lat", "lon", "elev_m"] if c in meta.columns]],
        on="station", how="left")

    for col in ("lat", "lon", "elev_m"):
        if col not in out.columns:
            out[col] = np.nan
        v = np.array(out[col].to_numpy(dtype=float), copy=True)
        bad = np.zeros(v.shape, dtype=bool)
        for flag in nodata:
            bad |= np.isclose(v, flag, rtol=1e-9, atol=0.0)
        bad |= ~np.isfinite(v)
        v[bad] = np.nan
        out[col] = v

    out["elev_source"] = np.where(out["elev_m"].notna(), "station_meta", "missing")

    ver_path = Path(cfg["paths"].get("station_meta_verified", ""))
    if ver_path.is_file():
        ver = pd.read_csv(ver_path)
        ver.columns = [str(c).strip().lower() for c in ver.columns]
        ver = ver.rename(columns={"code": "station", "elev": "elev_m",
                                  "elevation": "elev_m"})
        ver["station"] = ver["station"].astype(str).str.strip()
        keep = ver[["station", "elev_m"] +
                   (["source"] if "source" in ver.columns else [])]
        out = out.merge(keep, on="station", how="left", suffixes=("", "_ver"))
        use = out["elev_m_ver"].notna()
        out.loc[use, "elev_m"] = out.loc[use, "elev_m_ver"]
        out.loc[use, "elev_source"] = "verified_override"
        out = out.drop(columns=[c for c in ("elev_m_ver", "source") if c in out.columns])
    else:
        print(f"    [note] no verified metadata override at {ver_path} "
              f"— missing elevations stay missing")

    return out


# ═══════════════════════════════════════════════════════════════════════════
#  Orchestration
# ═══════════════════════════════════════════════════════════════════════════

def build_dataset(cfg: dict, prov: Provenance) -> Dataset:
    obs_path, raw_paths, legacy_paths = discover_files(cfg)
    print(f"    observed : {obs_path.name}")
    print(f"    raw      : {len(raw_paths)} models -> {sorted(raw_paths)}")
    print(f"    legacy bc: {len(legacy_paths)} models")

    obs, deep = load_daily(obs_path, "observed", "observed", cfg)
    if deep:
        prov.warn(f"observed: {deep} values below negative tolerance set to NaN")
    stations = list(obs.df.columns)

    raw: dict[str, SeriesBundle] = {}
    for model, p in raw_paths.items():
        b, deep = load_daily(p, model, "raw", cfg, keep_stations=stations)
        if deep:
            prov.warn(f"raw/{model}: {deep} values below negative tolerance set to NaN")
        raw[model] = b

    legacy: dict[str, SeriesBundle] = {}
    for model, p in legacy_paths.items():
        b, deep = load_daily(p, model, "legacy_bc", cfg, keep_stations=stations)
        if deep:
            prov.warn(f"legacy/{model}: {deep} below negative tolerance set to NaN")
        legacy[model] = b

    # station intersection across observed + every raw model
    common_stations = set(stations)
    for model, b in raw.items():
        common_stations &= set(b.df.columns)
    dropped = [s for s in stations if s not in common_stations]
    if dropped:
        prov.warn(f"stations absent from at least one model, dropped: {dropped}")
    stations = [s for s in stations if s in common_stations]

    obs.df = obs.df[stations]
    for b in list(raw.values()) + list(legacy.values()):
        b.df = b.df[[s for s in stations if s in b.df.columns]]

    # indices — per-model pairing, plus an all-model common sample
    paired = {m: obs.df.index.intersection(b.df.index) for m, b in raw.items()}
    common = obs.df.index
    for m in raw:
        common = common.intersection(raw[m].df.index)

    meta = load_station_meta(cfg, stations)

    # ── provenance ───────────────────────────────────────────────────────
    prov.add_input("observed", obs_path, rows=obs.n_rows, calendar=obs.calendar)
    for m, p in raw_paths.items():
        prov.add_input(f"raw/{m}", p, rows=raw[m].n_rows, calendar=raw[m].calendar)
    for m, p in legacy_paths.items():
        prov.add_input(f"legacy_bc/{m}", p, rows=legacy[m].n_rows)
    if Path(cfg["paths"]["station_meta"]).is_file():
        prov.add_input("station_meta", Path(cfg["paths"]["station_meta"]))

    for label, b in [("observed", obs)] + [(f"raw/{m}", v) for m, v in raw.items()]:
        prov.add_transformation(label,
                                unit_factor_applied=b.unit_factor,
                                minimum_raw_value=round(b.min_raw_value, 6),
                                nodata_values_masked=b.n_nodata_masked,
                                negative_values_clipped=b.n_negative_clipped,
                                rows_after_date_parse=b.n_rows)
        prov.add_calendar(label, calendar=b.calendar, rows=b.n_rows,
                          first=str(b.df.index[0].date()),
                          last=str(b.df.index[-1].date()))

    prov.add_sample_size("n_common_days_all_models", n=len(common))
    for m, ix in paired.items():
        prov.add_sample_size(f"n_model_paired_days/{m}", n=len(ix))
    prov.set("stations", {
        "n": len(stations), "ids": stations,
        "elevation_missing": meta.loc[meta.elev_m.isna(), "station"].tolist(),
    })

    return Dataset(observed=obs, raw=raw, legacy_bc=legacy, stations=stations,
                   station_meta=meta, common_index=common, paired_index=paired)


def period_mask(index: pd.DatetimeIndex, years: list[int]) -> np.ndarray:
    y = index.year
    return (y >= int(years[0])) & (y <= int(years[1]))
