"""
iod.py
======
Indian Ocean Dipole (Dipole Mode Index, DMI) retrieval for the optional
second-predictor analysis. The DMI is downloaded live from NOAA PSL and parsed
with the same long-data reader used for the PSL Nino-3.4 fallback. No values are
ever fabricated; if the network is unreachable and no cache exists the caller
skips the IOD analysis rather than substituting data.
"""
from __future__ import annotations
import logging
import pandas as pd

from . import config as C
from .enso import _get, parse_psl_longdata, ENSODownloadError

log = logging.getLogger("iod")


def fetch_dmi(start: int = C.START_YEAR, end: int = C.END_YEAR):
    """Return (monthly, yearly) DMI tables for the study period.

    monthly: year, month, DMI
    yearly : year, DMI (annual mean), DMI_phase (Saji et al. 1999 +/-0.4)
    """
    txt = _get(C.DMI_URLS, cache=C.DMI_CACHE)
    m = parse_psl_longdata(txt, "DMI")
    if m.empty:
        raise ENSODownloadError("DMI file parsed to zero rows.")
    m = m[(m["year"] >= start) & (m["year"] <= end)].reset_index(drop=True)

    yr = m.groupby("year", as_index=False)["DMI"].mean()
    yr["DMI_phase"] = yr["DMI"].apply(_dmi_phase)
    return m, yr


def _dmi_phase(v: float) -> str:
    if v >= C.DMI_POS:
        return "Positive IOD"
    if v <= C.DMI_NEG:
        return "Negative IOD"
    return "Neutral"
