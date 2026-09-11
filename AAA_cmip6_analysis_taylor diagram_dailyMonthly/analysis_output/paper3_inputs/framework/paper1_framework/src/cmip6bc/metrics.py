"""Precipitation metrics and ETCCDI-type indices.

One definition set is used for observed, raw GCM and every bias-corrected
series, so that any difference between them is a property of the data and not
of the index code.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_SET = ("PRCPTOT", "PRCPTOT_wet", "PRCPTOT_dry", "SDII", "Rx1day",
               "Rx5day", "R10mm", "R20mm", "R50mm", "CDD", "CWD", "R95p",
               "R99p", "wet_day_pct", "q50", "q90", "q95", "q99")

# Monsoon (south-west) and dry season for mainland South-East Asia.  A dry
# season is labelled by the calendar year in which it ENDS, so that
# PRCPTOT_dry(y) covers Nov(y-1) to Apr(y); the first year of a record is
# therefore incomplete and is returned as NaN rather than a partial total.
WET_MONTHS = (5, 6, 7, 8, 9, 10)
DRY_MONTHS = (11, 12, 1, 2, 3, 4)


def wet_percentiles(series, wet_thr: float = 1.0,
                    probs=(95, 99)) -> dict:
    """Percentile thresholds from wet days of a reference period."""
    x = np.asarray(series, float)
    x = x[np.isfinite(x)]
    w = x[x >= wet_thr]
    if len(w) < 10:
        return {f"p{p}": np.nan for p in probs}
    # linear (type-7) interpolation, stated explicitly in the manifest
    return {f"p{p}": float(np.percentile(w, p)) for p in probs}


def _max_run(mask: np.ndarray) -> int:
    best = run = 0
    for v in mask:
        run = run + 1 if v else 0
        best = max(best, run)
    return best


def annual_indices(series: pd.Series, *, wet_thr: float = 1.0,
                   p95: float = np.nan, p99: float = np.nan,
                   wanted=DEFAULT_SET) -> pd.DataFrame:
    """Per-calendar-year indices from a daily series with a DatetimeIndex.

    The series is reindexed onto a complete daily calendar first, so that
    multi-day windows (Rx5day) and spells (CDD/CWD) always see real elapsed
    time even under a no-leap model calendar.
    """
    s = series.astype(float)
    full = pd.date_range(s.index.min().normalize(),
                         s.index.max().normalize(), freq="D")
    s = s.reindex(full)

    # seasonal totals, computed once on the full series
    wet_mask = s.index.month.isin(WET_MONTHS)
    wet_season = s.where(wet_mask)
    dry_label = np.where(s.index.month >= 11, s.index.year + 1, s.index.year)
    dry_series = s.where(s.index.month.isin(DRY_MONTHS))
    first_year = int(s.index.year.min())

    rows = []
    for year, sy in s.groupby(s.index.year):
        v = sy.to_numpy(float)
        obs = v[np.isfinite(v)]
        if len(obs) == 0:
            continue
        wet = obs[obs >= wet_thr]
        rec = {"year": int(year), "n_valid_days": int(len(obs))}
        if "PRCPTOT" in wanted:
            rec["PRCPTOT"] = float(wet.sum())
        if "PRCPTOT_wet" in wanted:
            w = wet_season[wet_season.index.year == year].dropna()
            w = w[w >= wet_thr]
            rec["PRCPTOT_wet"] = float(w.sum()) if len(w) else np.nan
        if "PRCPTOT_dry" in wanted:
            d = dry_series[(dry_label == year)].dropna()
            d = d[d >= wet_thr]
            rec["PRCPTOT_dry"] = (float(d.sum()) if len(d) and year > first_year
                                  else np.nan)
        if "SDII" in wanted:
            rec["SDII"] = float(wet.mean()) if len(wet) else np.nan
        if "wet_day_pct" in wanted:
            rec["wet_day_pct"] = 100.0 * len(wet) / len(obs)
        if "Rx1day" in wanted:
            rec["Rx1day"] = float(obs.max())
        if "Rx5day" in wanted:
            r5 = sy.rolling(5, min_periods=5).sum()
            rec["Rx5day"] = float(np.nanmax(r5.to_numpy())) \
                if np.isfinite(r5.to_numpy()).any() else np.nan
        for thr, name in ((10, "R10mm"), (20, "R20mm"), (50, "R50mm")):
            if name in wanted:
                rec[name] = int((obs >= thr).sum())
        if "CDD" in wanted:
            rec["CDD"] = _max_run(v < wet_thr)      # NaN days break the spell
        if "CWD" in wanted:
            rec["CWD"] = _max_run(v >= wet_thr)
        if "R95p" in wanted:
            rec["R95p"] = float(wet[wet > p95].sum()) if np.isfinite(p95) else np.nan
        if "R99p" in wanted:
            rec["R99p"] = float(wet[wet > p99].sum()) if np.isfinite(p99) else np.nan
        for q in (50, 90, 95, 99):
            name = f"q{q}"
            if name in wanted:
                rec[name] = float(np.percentile(wet, q)) if len(wet) >= 10 else np.nan
        rows.append(rec)
    return pd.DataFrame(rows)


def period_metrics(series: pd.Series, *, wet_thr: float = 1.0,
                   p95: float = np.nan, p99: float = np.nan) -> dict:
    """Whole-period distribution metrics used for validation tables."""
    x = series.astype(float).to_numpy()
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return {}
    wet = x[x >= wet_thr]
    n_years = max(series.index.year.nunique(), 1)
    out = {
        "n_days": int(len(x)),
        "wet_day_pct": 100.0 * len(wet) / len(x),
        "PRCPTOT": float(wet.sum()) / n_years,
        "SDII": float(wet.mean()) if len(wet) else np.nan,
        "mean_daily": float(x.mean()),
        "sd_daily": float(x.std(ddof=1)),
        "sd_wet": float(wet.std(ddof=1)) if len(wet) > 1 else np.nan,
    }
    for q in (50, 90, 95, 99):
        out[f"q{q}"] = float(np.percentile(wet, q)) if len(wet) >= 10 else np.nan
    ann = annual_indices(series, wet_thr=wet_thr, p95=p95, p99=p99)
    for k in ("Rx1day", "Rx5day", "R10mm", "R20mm", "R50mm",
              "CDD", "CWD", "R95p", "R99p"):
        if k in ann.columns:
            out[k] = float(ann[k].mean())
    return out


def perkins_skill_score(obs, sim, wet_thr: float = 1.0, nbins: int = 60) -> float:
    """Overlap of the wet-day intensity PDFs (Perkins et al. 2007)."""
    o = np.asarray(obs, float); s = np.asarray(sim, float)
    o = o[np.isfinite(o)]; s = s[np.isfinite(s)]
    o = o[o >= wet_thr]; s = s[s >= wet_thr]
    if len(o) < 10 or len(s) < 10:
        return np.nan
    hi = float(np.percentile(np.concatenate([o, s]), 99.5))
    edges = np.linspace(wet_thr, max(hi, wet_thr + 1), nbins + 1)
    ho, _ = np.histogram(o, bins=edges, density=False)
    hs, _ = np.histogram(s, bins=edges, density=False)
    ho = ho / max(ho.sum(), 1); hs = hs / max(hs.sum(), 1)
    return float(np.minimum(ho, hs).sum())


def bias_table(obs_metrics: dict, sim_metrics: dict, keys=None) -> dict:
    keys = keys or [k for k in obs_metrics if k != "n_days"]
    out = {}
    for k in keys:
        o, s = obs_metrics.get(k, np.nan), sim_metrics.get(k, np.nan)
        out[f"{k}_obs"] = o
        out[f"{k}_sim"] = s
        out[f"{k}_bias_pct"] = (100.0 * (s - o) / o
                                if np.isfinite(o) and abs(o) > 1e-9 else np.nan)
    return out
