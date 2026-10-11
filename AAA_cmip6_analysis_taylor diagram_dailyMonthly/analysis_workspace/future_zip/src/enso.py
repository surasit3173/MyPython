"""
enso.py
=======
Automatic retrieval of ENSO indices from NOAA CPC (no manual entry, no
simulated values) and phase classification.

  * ONI       -> https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt
  * Nino-3.4  -> https://www.cpc.ncep.noaa.gov/data/indices/ersst5.nino.mth.91-20.ascii

If the network is unreachable the module raises ENSODownloadError. The caller
decides whether to abort (default, per spec) or continue rainfall-only analysis
(--allow-offline). No fabricated data is ever substituted.
"""
from __future__ import annotations
import io
import logging
import time
import numpy as np
import pandas as pd
import requests

from . import config as C

log = logging.getLogger("enso")


class ENSODownloadError(RuntimeError):
    pass


def _get(urls, cache: "Path | None" = None) -> str:
    """Download the first reachable URL; on success refresh the local cache.

    If every endpoint fails and a local cache of the real NOAA file exists, the
    cached copy is used so the analysis stays fully reproducible offline. No
    values are ever fabricated -- the cache only ever holds bytes that were
    themselves downloaded from the NOAA endpoints below.
    """
    last = None
    for url in urls:
        for attempt in range(1, C.HTTP_RETRIES + 1):
            try:
                log.info("Downloading %s (attempt %d)", url, attempt)
                r = requests.get(url, timeout=C.HTTP_TIMEOUT)
                r.raise_for_status()
                if len(r.text) < 100:
                    raise ValueError("suspiciously short payload")
                if cache is not None:
                    try:
                        cache.write_text(r.text, encoding="utf-8")
                        log.info("  cached -> %s", cache)
                    except OSError as e:               # noqa: BLE001
                        log.warning("  could not refresh cache: %s", e)
                return r.text
            except Exception as e:                       # noqa: BLE001
                last = e
                log.warning("  failed: %s", e)
                time.sleep(1.5 * attempt)
    if cache is not None and cache.exists():
        log.warning("Network unreachable; using cached NOAA file %s "
                    "(real data previously downloaded from CPC).", cache)
        return cache.read_text(encoding="utf-8")
    raise ENSODownloadError(f"All ENSO endpoints failed; last error: {last}")


def fetch_oni() -> pd.DataFrame:
    """Return monthly ONI: columns year, month, ONI (centre month of season)."""
    txt = _get(C.ONI_URLS, cache=C.ONI_CACHE)
    df = pd.read_csv(io.StringIO(txt), sep=r"\s+")
    # expected columns: SEAS YR TOTAL ANOM
    df.columns = [c.upper() for c in df.columns]
    df = df.rename(columns={"YR": "year", "ANOM": "ONI", "SEAS": "season"})
    df["month"] = df["season"].map(C.ONI_SEASON_CENTER)
    df = df.dropna(subset=["month"])
    df["month"] = df["month"].astype(int)
    out = df[["year", "month", "ONI"]].copy()
    out["year"] = pd.to_numeric(out["year"], errors="coerce")
    out["ONI"] = pd.to_numeric(out["ONI"], errors="coerce")
    return out.dropna().astype({"year": int, "month": int}).reset_index(drop=True)


def fetch_nino34() -> pd.DataFrame:
    """Return monthly Nino-3.4 anomaly: columns year, month, Nino34, source.

    Primary source = CPC ERSSTv5 (1991-2020 climatology). If every CPC endpoint
    or the parse fails, fall back to the NOAA PSL long anomaly file. The endpoint
    that actually supplied the data is recorded in the ``source`` column so the
    provenance is never ambiguous in the manuscript. The two products use
    different SST datasets / base periods, hence the explicit labelling.
    """
    try:
        return _fetch_nino34_cpc()
    except Exception as e:                                     # noqa: BLE001
        log.warning("CPC Nino-3.4 unavailable (%s); trying NOAA PSL fallback.", e)
        return _fetch_nino34_psl()


def _fetch_nino34_cpc() -> pd.DataFrame:
    """Parse the CPC ERSSTv5 monthly Nino index file."""
    txt = _get(C.NINO34_URLS, cache=C.NINO34_CACHE)
    lines = txt.splitlines()
    # Locate the column header row, then parse the numeric block beneath it.
    hdr_idx = None
    for i, ln in enumerate(lines):
        toks = ln.split()
        up = [t.upper() for t in toks]
        if "YEAR" in up and any(t.startswith("NINO34") or t == "NINO34" for t in up):
            hdr_idx = i
            break
        if {"YR", "MON"}.issubset(set(up)):  # legacy ersst5...ascii layout
            hdr_idx = i
            break
    if hdr_idx is None:
        raise ENSODownloadError("Nino-3.4 file: could not locate column header")

    header = [t.upper() for t in lines[hdr_idx].split()]
    rows = []
    for ln in lines[hdr_idx + 1:]:
        toks = ln.split()
        if len(toks) < 3:
            continue
        if not toks[0].lstrip("-").isdigit():
            continue
        rows.append(toks)
    block = "\n".join(" ".join(r) for r in rows)
    raw = pd.read_csv(io.StringIO(block), sep=r"\s+", header=None)

    # Identify Year, Month and NINO34 columns from the header where possible.
    def _col(name_opts, default):
        for opt in name_opts:
            if opt in header:
                return header.index(opt)
        return default

    yi = _col(["YEAR", "YR"], 0)
    mi = _col(["MONTH", "MON"], 1)
    if "NINO34" in header:
        ni = header.index("NINO34")
    elif "NINO3.4" in header:
        ni = header.index("NINO3.4")
    else:
        ni = raw.shape[1] - 1  # legacy layout: Nino-3.4 anomaly is last column
    out = pd.DataFrame(dict(
        year=pd.to_numeric(raw.iloc[:, yi], errors="coerce"),
        month=pd.to_numeric(raw.iloc[:, mi], errors="coerce"),
        Nino34=pd.to_numeric(raw.iloc[:, ni], errors="coerce"),
    ))
    out = out.dropna().astype({"year": int, "month": int}).reset_index(drop=True)
    if len(out) < 100:
        raise ENSODownloadError("CPC Nino-3.4 parsed to too few rows")
    out["source"] = "CPC_ERSSTv5_91-20"
    return out


def parse_psl_longdata(txt: str, value_name: str = "value") -> pd.DataFrame:
    """Parse a NOAA PSL '<index>.long.data' file (year + 12 monthly values).

    Shared by the Nino-3.4 PSL fallback and the DMI/IOD reader. Robust to the
    2-integer header line, the -99.99 missing sentinel and the trailing
    free-text description block. Returns columns year, month, <value_name>.
    """
    recs = []
    for line in txt.splitlines():
        parts = line.split()
        if len(parts) != 13:                 # data rows are year + 12 months
            continue
        try:
            year = int(parts[0])
        except ValueError:
            continue
        if not (1800 <= year <= 2100):       # guard header/trailer noise
            continue
        for month in range(1, 13):
            try:
                val = float(parts[month])
            except ValueError:
                val = np.nan
            if not np.isnan(val) and abs(val - C.PSL_MISSING) < 1e-6:
                val = np.nan
            recs.append({"year": year, "month": month, value_name: val})
    out = pd.DataFrame(recs).dropna().astype(
        {"year": int, "month": int}).reset_index(drop=True)
    return out


def _fetch_nino34_psl() -> pd.DataFrame:
    """NOAA PSL Nino-3.4 long anomaly file (FALLBACK source only)."""
    txt = _get(C.NINO34_PSL_URLS, cache=C.NINO34_PSL_CACHE)
    out = parse_psl_longdata(txt, "Nino34")
    if out.empty:
        raise ENSODownloadError("PSL Nino-3.4 file parsed to zero rows.")
    out["source"] = "NOAA_PSL_nino34.long.anom"
    return out


def classify_phase(oni_value: float) -> str:
    if oni_value >= C.ONI_ELNINO:
        return "El Nino"
    if oni_value <= C.ONI_LANINA:
        return "La Nina"
    return "Neutral"


def classify_events_persistence(oni: pd.Series,
                                min_run: int = C.ONI_MIN_CONSECUTIVE) -> pd.Series:
    """Official CPC ENSO *event* definition.

    A month (centre of a 3-month ONI season) is labelled El Nino / La Nina only
    if it belongs to a run of at least ``min_run`` consecutive overlapping
    seasons that all meet the +/-0.5 threshold of the same sign. Isolated
    threshold crossings shorter than the run length are Neutral. ``oni`` must be
    ordered chronologically and contiguous in months.
    """
    sign = pd.Series(0, index=oni.index, dtype=int)
    sign[oni >= C.ONI_ELNINO] = 1
    sign[oni <= C.ONI_LANINA] = -1
    out = pd.Series("Neutral", index=oni.index, dtype=object)
    i, n = 0, len(sign)
    vals = sign.values
    while i < n:
        if vals[i] == 0:
            i += 1
            continue
        j = i
        while j < n and vals[j] == vals[i]:
            j += 1
        if (j - i) >= min_run:
            label = "El Nino" if vals[i] == 1 else "La Nina"
            out.iloc[i:j] = label
        i = j
    return out


def build_enso(start=C.START_YEAR, end=C.END_YEAR):
    """Merge ONI + Nino3.4 to monthly + yearly tables with phase labels.

    Two monthly labels are produced:
      * ENSO_Phase  -- per-season threshold sign (descriptive only)
      * ENSO_Event  -- official persistence rule (>=5 consecutive seasons);
                       this is the column used for composites/comparisons.
    """
    oni = fetch_oni()
    nino = fetch_nino34()
    nino34_source = nino["source"].iloc[0] if "source" in nino else "unknown"
    nino = nino.drop(columns=[c for c in ["source"] if c in nino.columns])

    m = pd.merge(oni, nino, on=["year", "month"], how="outer").sort_values(
        ["year", "month"]).reset_index(drop=True)
    m["ENSO_Phase"] = m["ONI"].apply(
        lambda v: classify_phase(v) if pd.notna(v) else np.nan)
    # Persistence rule on the full ONI record BEFORE trimming, so runs that
    # straddle the start year are evaluated correctly.
    m["ENSO_Event"] = classify_events_persistence(m["ONI"])
    m = m[(m["year"] >= start) & (m["year"] <= end)].reset_index(drop=True)
    m.attrs["nino34_source"] = nino34_source

    # Yearly classification: an event year is one whose peak ENSO season
    # (max |ONI|) is part of a qualifying event run; otherwise mean-ONI sign is
    # reported for reference. Both are kept transparent.
    rows = []
    for y, g in m.groupby("year"):
        peak_idx = g["ONI"].abs().idxmax()
        event = g.loc[peak_idx, "ENSO_Event"]
        rows.append(dict(year=int(y),
                         ONI=g["ONI"].mean(),
                         Nino34=g["Nino34"].mean(),
                         ONI_peak=g.loc[peak_idx, "ONI"],
                         ENSO_Phase=classify_phase(g["ONI"].mean()),
                         ENSO_Event=event))
    yr = pd.DataFrame(rows)
    yr.attrs["nino34_source"] = nino34_source
    return m, yr
