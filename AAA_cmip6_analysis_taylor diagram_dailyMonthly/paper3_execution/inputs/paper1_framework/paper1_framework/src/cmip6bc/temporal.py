"""Temporal-dependence diagnostics.

Quantile mapping of any flavour is a rank-preserving transformation of the
MARGINAL distribution.  It reorders nothing, so the day-to-day sequencing of
the model is passed through untouched.  Indices that depend on that sequencing
-- dry and wet spells (CDD, CWD), multi-day accumulations (Rx5day) and
autocorrelation -- are therefore NOT corrected, however good the marginal fit
looks.  This module measures that dimension explicitly so the limitation is
reported rather than hidden behind a good-looking distribution.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Indices whose value is fixed once the marginal distribution is fixed, versus
# those that additionally require the correct temporal structure.
MARGINAL_CONTROLLED = ("wet_day_pct", "PRCPTOT", "SDII", "q50", "q90", "q95",
                       "q99", "R10mm", "R20mm", "R50mm", "R95p", "R99p",
                       "sd_daily", "sd_wet")
TEMPORAL_CONTROLLED = ("CDD", "CWD", "Rx5day", "Rx1day")


def _spells(mask: np.ndarray) -> np.ndarray:
    """Lengths of consecutive True runs."""
    if mask.size == 0:
        return np.array([], dtype=int)
    d = np.diff(np.concatenate(([0], mask.view(np.int8), [0])))
    starts = np.flatnonzero(d == 1)
    ends = np.flatnonzero(d == -1)
    return ends - starts


def temporal_metrics(series: pd.Series, wet_thr: float = 1.0) -> dict:
    """Sequencing statistics of a daily rainfall series."""
    x = np.asarray(series, dtype=float)
    ok = np.isfinite(x)
    x = x[ok]
    if len(x) < 30:
        return {}
    wet = x >= wet_thr

    # lag-1 autocorrelation of daily amounts and of the wet/dry sequence
    def _acf1(v):
        v = np.asarray(v, float)
        if v.std(ddof=0) == 0:
            return np.nan
        return float(np.corrcoef(v[:-1], v[1:])[0, 1])

    ww = wet[:-1] & wet[1:]
    dw = (~wet[:-1]) & wet[1:]
    n_w, n_d = int(wet[:-1].sum()), int((~wet[:-1]).sum())

    wet_spells = _spells(wet)
    dry_spells = _spells(~wet)

    out = {
        "acf1_daily": _acf1(x),
        "acf1_occurrence": _acf1(wet.astype(float)),
        "P_wet_given_wet": float(ww.sum() / n_w) if n_w else np.nan,
        "P_wet_given_dry": float(dw.sum() / n_d) if n_d else np.nan,
        "mean_wet_spell": float(wet_spells.mean()) if wet_spells.size else np.nan,
        "p90_wet_spell": float(np.percentile(wet_spells, 90)) if wet_spells.size else np.nan,
        "max_wet_spell": int(wet_spells.max()) if wet_spells.size else 0,
        "mean_dry_spell": float(dry_spells.mean()) if dry_spells.size else np.nan,
        "p90_dry_spell": float(np.percentile(dry_spells, 90)) if dry_spells.size else np.nan,
        "max_dry_spell": int(dry_spells.max()) if dry_spells.size else 0,
        "n_wet_spells": int(wet_spells.size),
        "n_dry_spells": int(dry_spells.size),
    }
    # clustering: how much of a 5-day maximum comes from a single day
    s = series.astype(float)
    r5 = s.rolling(5, min_periods=5).sum()
    if np.isfinite(r5.to_numpy()).any() and np.isfinite(x).any():
        out["rx1_over_rx5"] = float(np.nanmax(x) / np.nanmax(r5.to_numpy()))
    return out


def temporal_table(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def temporal_bias(sim: pd.DataFrame, obs: pd.DataFrame,
                  on=("station", "period")) -> pd.DataFrame:
    """Relative bias of every sequencing statistic against observations."""
    keys = [c for c in sim.columns
            if c not in list(on) + ["model", "method", "scenario", "y0", "y1"]]
    m = sim.merge(obs, on=list(on), suffixes=("", "_obs"))
    for k in keys:
        o = m.get(f"{k}_obs")
        if o is None:
            continue
        m[f"{k}_bias_pct"] = np.where(np.abs(o) > 1e-9, 100 * (m[k] - o) / o, np.nan)
    return m


def summarise(bias: pd.DataFrame, methods) -> pd.DataFrame:
    """One row per method: is the sequencing dimension corrected at all?"""
    keys = ["acf1_daily", "acf1_occurrence", "P_wet_given_wet", "P_wet_given_dry",
            "mean_wet_spell", "mean_dry_spell", "p90_dry_spell", "rx1_over_rx5"]
    rows = []
    for m in methods:
        s = bias[bias.method == m]
        rec = {"method": m}
        for k in keys:
            c = f"{k}_bias_pct"
            if c in s.columns:
                rec[f"{k} bias (%)"] = round(float(s[c].mean()), 2)
        rows.append(rec)
    df = pd.DataFrame(rows)
    if {"raw"} <= set(df.method):
        base = df[df.method == "raw"].iloc[0]
        for c in [c for c in df.columns if c != "method"]:
            df[c.replace("bias (%)", "vs raw")] = (
                df[c].abs() - abs(base[c])).round(2)
    return df


def verdict(bias: pd.DataFrame, primary: str = "qdm",
            tol: float = 10.0) -> dict:
    """Did bias correction change the sequencing at all, and is it adequate?"""
    keys = ["acf1_occurrence", "P_wet_given_wet", "mean_dry_spell", "mean_wet_spell"]
    raw = bias[bias.method == "raw"]
    bc = bias[bias.method == primary]
    detail = {}
    for k in keys:
        c = f"{k}_bias_pct"
        if c not in bias.columns:
            continue
        detail[k] = {"raw_abs_bias_pct": round(float(raw[c].abs().mean()), 2),
                     "bc_abs_bias_pct": round(float(bc[c].abs().mean()), 2)}
    worst = max((v["bc_abs_bias_pct"] for v in detail.values()), default=np.nan)
    return {"metrics": detail, "worst_abs_bias_pct": round(float(worst), 2),
            "adequate": bool(np.isfinite(worst) and worst <= tol),
            "note": "quantile mapping is a marginal transformation and does not "
                    "reorder days; spell-based and multi-day indices inherit the "
                    "model's own temporal structure"}
