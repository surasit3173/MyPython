"""Bias correction: QM/EQM, DetQM and QDM behind one API.

Design rules enforced here
--------------------------
* Parameters are estimated ONLY from the calibration period and then frozen
  into a `Fit` object.  `apply()` never looks at the target period's
  observations, so validation is genuinely out-of-sample.
* All three methods share the identical occurrence model (frequency
  adaptation) and the identical quantile machinery, so any difference between
  them is attributable to the method, not to preprocessing.
* Extrapolation beyond the calibration quantile range is explicit
  (constant correction ratio) and every extrapolated value is counted.
  Nothing is clipped or discarded.

References
----------
Themessl et al. (2012)  frequency adaptation / threshold matching
Cannon, Sobie & Murdock (2015, J. Climate 28, 6938-6959)  DQM and QDM
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

METHODS = ("qm", "detqm", "qdm")


def _pp(n: int, kind: str = "hazen") -> np.ndarray:
    """Plotting positions for the empirical CDF."""
    i = np.arange(1, n + 1, dtype=float)
    if kind == "hazen":
        return (i - 0.5) / n
    if kind == "weibull":
        return i / (n + 1.0)
    raise ValueError(f"unknown plotting position: {kind}")


@dataclass
class Fit:
    """Frozen calibration parameters for one station x one model."""
    station: str
    model: str
    method: str
    wet_thr: float
    pp_kind: str
    p_obs_wet: float                  # observed wet-day fraction (calibration)
    model_wet_thr: float              # frequency-adapted model threshold
    obs_q: np.ndarray                 # sorted observed wet-day values
    obs_p: np.ndarray
    mod_q: np.ndarray                 # sorted model wet-day values (calibration)
    mod_p: np.ndarray
    mod_wet_mean: float               # model calibration wet-day mean (DetQM)
    n_obs_wet: int
    n_mod_wet: int
    diagnostics: dict = field(default_factory=dict)


def _clean(x) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    return x[np.isfinite(x)]


def fit(obs_cal, mod_cal, *, station: str, model: str, method: str,
        wet_thr: float = 1.0, frequency_adaptation: bool = True,
        pp_kind: str = "hazen", min_wet_days: int = 30) -> Fit:
    """Estimate and freeze parameters from the calibration period only."""
    if method not in METHODS:
        raise ValueError(f"unknown method {method!r}; expected one of {METHODS}")
    o, m = _clean(obs_cal), _clean(mod_cal)
    if len(o) == 0 or len(m) == 0:
        raise ValueError(f"{station}/{model}: empty calibration sample")

    ow = np.sort(o[o >= wet_thr])
    p_obs_wet = len(ow) / len(o)

    # ---- occurrence model -------------------------------------------------
    if frequency_adaptation:
        # Raise the model's wet-day threshold until its wet-day frequency
        # matches the observed one.  This removes GCM drizzle without touching
        # the intensity distribution of the retained wet days.
        model_wet_thr = float(np.quantile(m, max(0.0, 1.0 - p_obs_wet)))
        model_wet_thr = max(model_wet_thr, 0.0)
    else:
        model_wet_thr = wet_thr
    mw = np.sort(m[m > model_wet_thr]) if frequency_adaptation \
        else np.sort(m[m >= wet_thr])

    if len(ow) < min_wet_days or len(mw) < min_wet_days:
        raise ValueError(f"{station}/{model}: too few wet days "
                         f"(obs={len(ow)}, mod={len(mw)}, min={min_wet_days})")

    f = Fit(station=station, model=model, method=method, wet_thr=wet_thr,
            pp_kind=pp_kind, p_obs_wet=p_obs_wet, model_wet_thr=model_wet_thr,
            obs_q=ow, obs_p=_pp(len(ow), pp_kind),
            mod_q=mw, mod_p=_pp(len(mw), pp_kind),
            mod_wet_mean=float(mw.mean()),
            n_obs_wet=len(ow), n_mod_wet=len(mw))
    f.diagnostics = {
        "obs_wet_fraction": round(p_obs_wet, 5),
        "model_raw_wet_fraction": round(float((m >= wet_thr).mean()), 5),
        "model_wet_threshold_mm": round(model_wet_thr, 4),
        "obs_wet_mean_mm": round(float(ow.mean()), 4),
        "model_wet_mean_mm": round(float(mw.mean()), 4),
        "n_obs_cal": int(len(o)), "n_mod_cal": int(len(m)),
    }
    return f


def _inv_cdf(q: np.ndarray, p: np.ndarray, probs: np.ndarray):
    """Interpolate a quantile function; flag probabilities outside the range."""
    out = np.interp(probs, p, q)
    outside = (probs < p[0]) | (probs > p[-1])
    return out, outside


def _cdf(q: np.ndarray, p: np.ndarray, values: np.ndarray):
    out = np.interp(values, q, p)
    outside = (values < q[0]) | (values > q[-1])
    return out, outside


def apply(f: Fit, target, ) -> tuple[np.ndarray, dict]:
    """Apply frozen parameters to a target model series.

    `target` may be the calibration period itself, the independent validation
    period, or any future window.  The observations of the target period are
    never consulted.
    """
    x = np.asarray(target, dtype=float)
    out = np.full_like(x, np.nan, dtype=float)
    valid = np.isfinite(x)
    xv = x[valid]

    dry = xv <= f.model_wet_thr           # occurrence model, frozen
    wet = ~dry
    res = np.zeros_like(xv)
    n_extrap = 0

    if wet.any():
        w = xv[wet]
        if f.method == "qm":
            # BC(x) = F^-1_obs,cal( F_mod,cal(x) )
            p, o1 = _cdf(f.mod_q, f.mod_p, w)
            y, o2 = _inv_cdf(f.obs_q, f.obs_p, p)
            # constant-ratio extrapolation beyond the calibration range
            y = _extrapolate(w, y, f, o1 | o2)
            n_extrap = int((o1 | o2).sum())

        elif f.method == "detqm":
            # Remove the model's mean climate signal, quantile-map, restore it.
            scale = float(w.mean()) / f.mod_wet_mean if f.mod_wet_mean > 0 else 1.0
            scale = scale if np.isfinite(scale) and scale > 0 else 1.0
            det = w / scale
            p, o1 = _cdf(f.mod_q, f.mod_p, det)
            y0, o2 = _inv_cdf(f.obs_q, f.obs_p, p)
            y0 = _extrapolate(det, y0, f, o1 | o2)
            y = y0 * scale
            n_extrap = int((o1 | o2).sum())

        elif f.method == "qdm":
            # delta = x / F^-1_mod,cal( F_mod,target(x) );  BC = F^-1_obs,cal(p) * delta
            ws = np.sort(w)
            p_t = np.interp(w, ws, _pp(len(ws), f.pp_kind))
            m_cal, o1 = _inv_cdf(f.mod_q, f.mod_p, p_t)
            o_cal, o2 = _inv_cdf(f.obs_q, f.obs_p, p_t)
            with np.errstate(divide="ignore", invalid="ignore"):
                delta = np.where(m_cal > 0, w / m_cal, 1.0)
            delta = np.where(np.isfinite(delta), delta, 1.0)
            y = o_cal * delta
            n_extrap = int((o1 | o2).sum())
        else:                                    # pragma: no cover
            raise ValueError(f.method)

        res[wet] = np.maximum(y, 0.0)

    out[valid] = res
    info = {"n_values": int(valid.sum()),
            "n_wet_after_occurrence": int(wet.sum()),
            "n_dry_after_occurrence": int(dry.sum()),
            "n_extrapolated": n_extrap,
            "pct_extrapolated": round(100 * n_extrap / max(int(wet.sum()), 1), 3),
            "extrapolation_rule": "constant correction ratio at the nearest "
                                  "calibration quantile; no clipping"}
    return out, info


def _extrapolate(x_in: np.ndarray, y_in: np.ndarray, f: Fit,
                 outside: np.ndarray) -> np.ndarray:
    """Outside the calibration range, hold the multiplicative correction ratio
    fixed at the nearest calibration quantile.  Values are transformed, never
    clipped, so new record extremes remain new record extremes."""
    if not outside.any():
        return y_in
    y = y_in.copy()
    lo_ratio = f.obs_q[0] / f.mod_q[0] if f.mod_q[0] > 0 else 1.0
    hi_ratio = f.obs_q[-1] / f.mod_q[-1] if f.mod_q[-1] > 0 else 1.0
    below = outside & (x_in < f.mod_q[0])
    above = outside & (x_in > f.mod_q[-1])
    y[below] = x_in[below] * lo_ratio
    y[above] = x_in[above] * hi_ratio
    return y


def fit_all(obs_cal, mod_cal, *, station, model, methods, **kw) -> dict:
    """Fit every requested method on the same calibration sample."""
    return {m: fit(obs_cal, mod_cal, station=station, model=model,
                   method=m, **kw) for m in methods}
