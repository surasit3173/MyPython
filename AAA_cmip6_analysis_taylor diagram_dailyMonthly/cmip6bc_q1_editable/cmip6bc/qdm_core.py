"""
qdm_core.py — Quantile Delta Mapping under a strict split-sample protocol.

Protocol
--------
    fit(calibration 1981-2000) -> freeze -> apply(validation 2001-2014)

No observation from the validation period enters the estimation of any
transfer function, threshold or quantile at any point.

Two corrected products are emitted:

  EQM  x̂ = F⁻¹_o,h( F_m,h(x) )
       The transfer function is estimated once on calibration and applied
       unchanged.  Fully frozen; the strictest test of transferability.

  QDM  τ = F_m,p(x);  Δ = x / F⁻¹_m,h(τ);  x̂ = F⁻¹_o,h(τ) · Δ
       Cannon et al. (2015).  F_m,p is the *model's own* distribution in the
       target period.  It uses no observations, so the split-sample
       protocol is preserved, but it is not fully frozen and this must be
       stated explicitly in the Methods.

Identity worth documenting: when the target period equals the calibration
period, p = h, hence Δ = 1 and QDM reduces exactly to EQM.  Any table
showing identical QDM and EQM values in the calibration period is showing
this identity, not a software defect.

Frequency adaptation
--------------------
A model-side wet-day threshold t_m is chosen on calibration so that the
model's wet-day frequency matches the observed wet-day frequency.  t_m is
then frozen and reused on validation.  Consequently, agreement in wet-day
frequency during calibration is a DESIGN PROPERTY of the procedure and is
not evidence of skill.  During validation the frozen threshold reproduces
the calibration-period observed frequency, so residual agreement there is
weak evidence at best.  Reporting must separate construction-dependent
properties from independently validated ones.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


# ═══════════════════════════════════════════════════════════════════════════
#  Empirical distribution helpers (consistent CDF / inverse-CDF pair)
# ═══════════════════════════════════════════════════════════════════════════

def _plotting_positions(n: int) -> np.ndarray:
    return (np.arange(1, n + 1) - 0.5) / n


def ecdf_prob(sorted_ref: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Non-exceedance probability of x within sorted_ref (constant tails)."""
    pp = _plotting_positions(sorted_ref.size)
    return np.interp(x, sorted_ref, pp)


def inv_ecdf(sorted_ref: np.ndarray, tau: np.ndarray) -> np.ndarray:
    """Inverse ECDF of sorted_ref at probabilities tau (constant tails)."""
    pp = _plotting_positions(sorted_ref.size)
    return np.interp(tau, pp, sorted_ref)


# ═══════════════════════════════════════════════════════════════════════════
#  Fitted, frozen transfer function
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class TransferFunction:
    station: str
    model: str
    group: str                      # 'all' or '01'..'12'
    wet_threshold_obs: float
    wet_threshold_model: float      # t_m — frozen
    obs_wet_sorted: np.ndarray = field(repr=False)
    mod_wet_sorted: np.ndarray = field(repr=False)
    n_obs_wet: int = 0
    n_mod_wet: int = 0
    obs_cal_max: float = np.nan
    obs_wet_freq_cal: float = np.nan
    mod_wet_freq_cal_raw: float = np.nan
    mod_wet_freq_cal_adapted: float = np.nan
    usable: bool = True
    note: str = ""


def _fit_group(obs_cal: np.ndarray, mod_cal: np.ndarray, cfg: dict,
               station: str, model: str, group: str) -> TransferFunction:
    qc = cfg["qdm"]
    wet_thr = float(cfg["data"]["wet_threshold_mm"])

    o = obs_cal[np.isfinite(obs_cal)]
    m = mod_cal[np.isfinite(mod_cal)]
    o_wet = np.sort(o[o >= wet_thr])
    p_wet_o = float(o_wet.size / o.size) if o.size else np.nan

    # ── frequency adaptation: pick t_m so model wet frequency == observed ──
    if qc.get("frequency_adaptation", True) and np.isfinite(p_wet_o) and m.size:
        t_m = float(np.quantile(m, 1.0 - p_wet_o))
        t_m = max(t_m, 0.0)
        if float(np.mean(m > 0.0)) < p_wet_o:
            t_m = 0.0
            note = ("model has fewer non-zero days than observed wet days; "
                    "frequency adaptation cannot increase wet-day frequency")
        else:
            note = ""
    else:
        t_m, note = wet_thr, "frequency adaptation disabled"

    m_wet = np.sort(m[m >= t_m]) if t_m > 0 else np.sort(m[m > 0.0])

    usable = (o_wet.size >= int(qc["min_wet_days_calibration"])
              and m_wet.size >= int(qc["min_wet_days_calibration"]))
    if not usable:
        note = (note + "; " if note else "") + \
               f"insufficient wet days (obs={o_wet.size}, mod={m_wet.size})"

    return TransferFunction(
        station=station, model=model, group=group,
        wet_threshold_obs=wet_thr, wet_threshold_model=t_m,
        obs_wet_sorted=o_wet, mod_wet_sorted=m_wet,
        obs_cal_max=float(o_wet[-1]) if o_wet.size else np.nan,
        n_obs_wet=int(o_wet.size), n_mod_wet=int(m_wet.size),
        obs_wet_freq_cal=p_wet_o,
        mod_wet_freq_cal_raw=float(np.mean(m >= wet_thr)) if m.size else np.nan,
        mod_wet_freq_cal_adapted=float(m_wet.size / m.size) if m.size else np.nan,
        usable=usable, note=note,
    )


# ═══════════════════════════════════════════════════════════════════════════
#  Application
# ═══════════════════════════════════════════════════════════════════════════

def _apply_group(tf: TransferFunction, x_target: np.ndarray, cfg: dict,
                 method: str) -> tuple[np.ndarray, dict]:
    """Apply a frozen transfer function to one block of target-period values."""
    qc = cfg["qdm"]
    out = np.zeros_like(x_target, dtype=float)
    out[~np.isfinite(x_target)] = np.nan
    stats = dict(n_input=int(np.isfinite(x_target).sum()), n_wet_target=0,
                 n_delta_clipped_high=0, n_delta_clipped_low=0,
                 n_output_capped=0, output_cap_mm=np.nan, max_output=np.nan)

    if not tf.usable:
        return out, stats

    thr = tf.wet_threshold_model
    wet_mask = np.isfinite(x_target) & (x_target >= thr if thr > 0
                                        else x_target > 0.0)
    xw = x_target[wet_mask]
    stats["n_wet_target"] = int(xw.size)
    if xw.size == 0:
        return out, stats

    if method == "EQM":
        tau = ecdf_prob(tf.mod_wet_sorted, xw)
        corrected = inv_ecdf(tf.obs_wet_sorted, tau)

    elif method == "QDM":
        target_sorted = np.sort(xw)
        tau = ecdf_prob(target_sorted, xw)          # F_m,p  (model only)
        ref_h = inv_ecdf(tf.mod_wet_sorted, tau)    # F⁻¹_m,h(τ)
        with np.errstate(divide="ignore", invalid="ignore"):
            delta = np.where(ref_h > 0, xw / ref_h, 1.0)
        hi, lo = float(qc["max_delta_ratio"]), float(qc["min_delta_ratio"])
        stats["n_delta_clipped_high"] = int(np.sum(delta > hi))
        stats["n_delta_clipped_low"] = int(np.sum(delta < lo))
        delta = np.clip(delta, lo, hi)
        corrected = inv_ecdf(tf.obs_wet_sorted, tau) * delta
    else:
        raise ValueError(f"unknown method {method!r}")

    corrected = np.clip(corrected, 0.0, None)

    factor = qc.get("upper_tail_cap_factor")
    if factor is not None and np.isfinite(tf.obs_cal_max):
        cap = float(factor) * tf.obs_cal_max
        stats["n_output_capped"] = int(np.sum(corrected > cap))
        corrected = np.minimum(corrected, cap)
        stats["output_cap_mm"] = round(cap, 2)

    out[wet_mask] = corrected
    stats["max_output"] = float(np.nanmax(corrected)) if corrected.size else np.nan
    return out, stats


# ═══════════════════════════════════════════════════════════════════════════
#  Driver
# ═══════════════════════════════════════════════════════════════════════════

def _group_key(index: pd.DatetimeIndex, grouping: str) -> np.ndarray:
    if grouping == "monthly":
        return np.array([f"{m:02d}" for m in index.month])
    return np.full(len(index), "all")


def correct_model(obs: pd.DataFrame, mod: pd.DataFrame, cfg: dict,
                  model_name: str) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """
    Returns ({'EQM': df, 'QDM': df}, diagnostics_df) over the full record.

    The correction is estimated on the calibration years only; validation
    years are transformed with the frozen parameters.
    """
    grouping = cfg["qdm"].get("grouping", "annual")
    if isinstance(grouping, dict):
        grouping = grouping.get("primary", "annual")
    cal, val = cfg["periods"]["calibration"], cfg["periods"]["validation"]

    idx = obs.index.intersection(mod.index)
    obs_a, mod_a = obs.loc[idx], mod.loc[idx]
    gkey = _group_key(idx, grouping)
    is_cal = (idx.year >= cal[0]) & (idx.year <= cal[1])
    is_val = (idx.year >= val[0]) & (idx.year <= val[1])

    # QDM's F_m,p must be the model distribution of the TARGET period.
    # Pooling calibration and validation would let validation-period model
    # values shift the quantile positions assigned to calibration days and
    # vice versa, which is neither Cannon et al. (2015) nor a clean
    # split-sample.  Each period is therefore transformed as its own block.
    blocks: list[tuple[str, np.ndarray]] = [("calibration", is_cal),
                                            ("validation", is_val)]
    other = ~(is_cal | is_val)
    if other.any():
        blocks.append(("outside_defined_periods", other))

    methods = ["QDM"] + (["EQM"] if cfg["qdm"].get("emit_eqm", True) else [])
    outputs = {mth: pd.DataFrame(np.nan, index=idx, columns=obs_a.columns)
               for mth in methods}
    diags: list[dict] = []

    for stn in obs_a.columns:
        o_all = obs_a[stn].to_numpy(dtype=float)
        m_all = mod_a[stn].to_numpy(dtype=float)

        for g in np.unique(gkey):
            gm = gkey == g
            tf = _fit_group(o_all[gm & is_cal], m_all[gm & is_cal],
                            cfg, stn, model_name, str(g))

            obs_cal_max = (float(np.nanmax(o_all[gm & is_cal]))
                           if np.isfinite(o_all[gm & is_cal]).any() else np.nan)

            for mth in methods:
                for bname, bmask in blocks:
                    sel = gm & bmask
                    if not sel.any():
                        continue
                    # every block uses the SAME frozen parameters from
                    # calibration; only the target values differ
                    corrected, st = _apply_group(tf, m_all[sel], cfg, mth)
                    outputs[mth].loc[idx[sel], stn] = corrected

                    if mth == "QDM":
                        diags.append(dict(
                            model=model_name, station=stn, group=str(g),
                            period=bname, usable=tf.usable, note=tf.note,
                            wet_threshold_model_mm=round(tf.wet_threshold_model, 4),
                            obs_wet_freq_cal=round(tf.obs_wet_freq_cal, 4),
                            mod_wet_freq_cal_raw=round(tf.mod_wet_freq_cal_raw, 4),
                            mod_wet_freq_cal_adapted=round(
                                tf.mod_wet_freq_cal_adapted, 4),
                            n_obs_wet_cal=tf.n_obs_wet, n_mod_wet_cal=tf.n_mod_wet,
                            n_wet_target=st["n_wet_target"],
                            n_delta_clipped_high=st["n_delta_clipped_high"],
                            n_delta_clipped_low=st["n_delta_clipped_low"],
                            n_output_capped=st["n_output_capped"],
                            output_cap_mm=st["output_cap_mm"],
                            max_output_mm=round(st["max_output"], 2)
                            if np.isfinite(st["max_output"]) else np.nan,
                            obs_cal_max_mm=round(obs_cal_max, 2)
                            if np.isfinite(obs_cal_max) else np.nan,
                            output_exceeds_obs_cal_max=bool(
                                np.isfinite(st["max_output"])
                                and np.isfinite(obs_cal_max)
                                and st["max_output"] > obs_cal_max),
                        ))

    return outputs, pd.DataFrame(diags)


def to_wide_csv(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Rebuild the YEAR,MONTH,DAY,<stations> layout of the source files."""
    t = cfg["time"]
    out = df.copy()
    out.insert(0, t["day_col"], out.index.day)
    out.insert(0, t["month_col"], out.index.month)
    out.insert(0, t["year_col"], out.index.year)
    return out.reset_index(drop=True)
