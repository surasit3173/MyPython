"""Climate-signal preservation, ensemble synthesis and acceptance gates."""
from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Climate-signal preservation  (Paper 2 core)
# ---------------------------------------------------------------------------
def signal_preservation(raw_hist: pd.DataFrame, raw_fut: pd.DataFrame,
                        bc_hist: pd.DataFrame, bc_fut: pd.DataFrame,
                        keys=("model", "station", "scenario", "window",
                              "method", "statistic")) -> pd.DataFrame:
    """PE(q) = 100 * (S_BC - S_mod) / S_mod  with S = future / historical.

    A value near zero means the bias correction reproduced the raw model's own
    relative change; positive means inflation, negative means deflation.
    """
    idx = ["model", "station", "scenario", "window", "statistic"]
    r = (raw_fut.merge(raw_hist, on=[c for c in idx if c != "scenario"] + ["scenario"]
                       if "scenario" in raw_hist.columns else
                       ["model", "station", "statistic"],
                       suffixes=("_fut", "_hist")))
    r["S_mod"] = np.where(np.abs(r["value_hist"]) > 1e-12,
                          r["value_fut"] / r["value_hist"], np.nan)
    b = bc_fut.merge(bc_hist, on=["model", "station", "method", "statistic"],
                     suffixes=("_fut", "_hist"))
    b["S_bc"] = np.where(np.abs(b["value_hist"]) > 1e-12,
                         b["value_fut"] / b["value_hist"], np.nan)
    m = b.merge(r[["model", "station", "scenario", "window", "statistic", "S_mod"]],
                on=["model", "station", "scenario", "window", "statistic"],
                how="left")
    m["PE_pct"] = np.where(np.abs(m["S_mod"]) > 1e-12,
                           100.0 * (m["S_bc"] - m["S_mod"]) / m["S_mod"], np.nan)
    m["raw_change_pct"] = 100.0 * (m["S_mod"] - 1.0)
    m["bc_change_pct"] = 100.0 * (m["S_bc"] - 1.0)
    return m[[*[k for k in keys if k in m.columns],
              "S_mod", "S_bc", "PE_pct", "raw_change_pct", "bc_change_pct"]]


# ---------------------------------------------------------------------------
# Ensemble synthesis
# ---------------------------------------------------------------------------
def ensemble_agreement(model_changes: pd.DataFrame, value_col: str,
                       group=("scenario", "window", "station", "index"),
                       threshold: float = 0.80) -> pd.DataFrame:
    """Agreement = N(models with the majority sign) / N(valid models).

    The CONTINUOUS fraction is returned.  Any map must interpolate this column,
    never a boolean flag.
    """
    rows = []
    for key, g in model_changes.groupby(list(group)):
        v = g[value_col].to_numpy(float)
        v = v[np.isfinite(v)]
        n = len(v)
        if n == 0:
            continue
        pos, neg = int((v > 0).sum()), int((v < 0).sum())
        frac = max(pos, neg) / n
        rows.append(dict(zip(group, key if isinstance(key, tuple) else (key,)))
                    | {"n_models": n,
                       "n_positive": pos, "n_negative": neg,
                       "median": float(np.median(v)),
                       "mean": float(np.mean(v)),
                       "q25": float(np.percentile(v, 25)),
                       "q75": float(np.percentile(v, 75)),
                       "iqr": float(np.percentile(v, 75) - np.percentile(v, 25)),
                       "min": float(v.min()), "max": float(v.max()),
                       "agreement_fraction": frac,
                       "robust": bool(frac >= threshold),
                       "agreement_threshold": threshold})
    return pd.DataFrame(rows)


def method_vs_model_spread(changes: pd.DataFrame, value_col: str,
                           group=("scenario", "window", "index")) -> pd.DataFrame:
    """Decompose projection spread into a model component and a method component."""
    rows = []
    for key, g in changes.groupby(list(group)):
        per_model = g.groupby("model")[value_col].mean()
        per_method = g.groupby("method")[value_col].mean()
        rows.append(dict(zip(group, key if isinstance(key, tuple) else (key,)))
                    | {"grand_mean": float(g[value_col].mean()),
                       "model_sd": float(per_model.std(ddof=1)) if len(per_model) > 1 else np.nan,
                       "method_sd": float(per_method.std(ddof=1)) if len(per_method) > 1 else np.nan,
                       "model_range": float(per_model.max() - per_model.min()),
                       "method_range": float(per_method.max() - per_method.min()),
                       "n_models": int(per_model.size),
                       "n_methods": int(per_method.size)})
    df = pd.DataFrame(rows)
    tot = df["model_sd"].fillna(0) + df["method_sd"].fillna(0)
    df["method_share_pct"] = np.where(tot > 0, 100 * df["method_sd"] / tot, np.nan)
    return df


# ---------------------------------------------------------------------------
# Acceptance gates
# ---------------------------------------------------------------------------
# Graded statuses.  A binary PASS/FAIL cannot express "better than raw but
# still carrying residual error", which is the honest description of most
# bias-correction validation results.
PASS = "PASS"
PASS_RESIDUAL = "PASS WITH RESIDUAL BIAS"
PASS_PARTIAL = "PASS (MARGINAL ONLY)"
PASS_TEMPORAL_UNCORRECTED = ("DIAGNOSTIC PASS - TEMPORAL STRUCTURE "
                             "NOT CORRECTED (NOT A PREDICTION-PERFORMANCE PASS)")
WARNING = "WARNING - BLOCKED FOR INTERPRETATION"
VERIFIED_ANOMALY = "VERIFIED RAW ANOMALY - INTERPRETATION RESTRICTED"
BLOCKED = "BLOCKED"

# "PASS" never means "good".  Each status is defined once, here, and written to
# output/results/gate_status_definitions.csv so the vocabulary travels with the
# numbers instead of living only in prose.
STATUS_DEFINITIONS = [
    {"status": PASS,
     "meaning": "meets the stated acceptance criterion with no known material "
                "limitation"},
    {"status": PASS_RESIDUAL,
     "meaning": "improves on the raw model or clears a minimum bar, but a "
                "systematic residual error remains and must be reported"},
    {"status": PASS_PARTIAL,
     "meaning": "the marginal distribution is reproduced; this says NOTHING "
                "about temporal or extreme-duration structure and must not be "
                "read as covering it"},
    {"status": PASS_TEMPORAL_UNCORRECTED,
     "meaning": "DIAGNOSTIC pass only - the dimension was measured and reported, "
                "NOT an acceptance pass for prediction performance. The method "
                "is not designed to reconstruct temporal sequencing and "
                "substantial residual bias remains in spell-duration and "
                "multi-day statistics. Projections of CDD, CWD and Rx5day must "
                "not be described as corrected."},
    {"status": VERIFIED_ANOMALY,
     "meaning": "the raw input has been traced as far as the available evidence "
                "allows and no extraction, unit, calendar or concatenation error "
                "was found; the anomaly is therefore a property of the raw source "
                "and is NOT called an error. Causal or physical interpretation "
                "remains restricted until the source NetCDF is examined."},
    {"status": WARNING,
     "meaning": "the quantity is computed and internally consistent, but "
                "climatic interpretation is not permitted until an upstream "
                "trace is complete"},
    {"status": BLOCKED,
     "meaning": "results must not be used"},
]


def gate(name: str, status: str, detail: str, evidence: str = "",
         limitation: str = "") -> dict:
    return {"gate": name, "status": status, "criterion": detail,
            "evidence": evidence, "limitation": limitation}


def variance_decomposition(changes: pd.DataFrame, value_col: str,
                           group=("scenario", "window", "index")) -> pd.DataFrame:
    """Two-way (model x method) sum-of-squares decomposition of projection spread.

    For each scenario-horizon-index, the total sum of squares about the grand
    mean is split into a model main effect, a method main effect and a residual
    (interaction plus within-cell variation).  Shares are SS_component / SS_total
    and sum to 100 by construction, which a ratio of standard deviations does
    not.  This is the quantity reported as "relative contribution to projection
    spread".
    """
    rows = []
    for key, g in changes.groupby(list(group)):
        v = g[value_col].to_numpy(float)
        keep = np.isfinite(v)
        g, v = g[keep], v[keep]
        if len(v) < 4 or g.model.nunique() < 2 or g.method.nunique() < 2:
            continue
        grand = v.mean()
        ss_tot = float(((v - grand) ** 2).sum())
        if ss_tot <= 0:
            continue
        ss_model = float(sum(len(d) * (d[value_col].mean() - grand) ** 2
                             for _, d in g.groupby("model")))
        ss_method = float(sum(len(d) * (d[value_col].mean() - grand) ** 2
                              for _, d in g.groupby("method")))
        ss_res = max(ss_tot - ss_model - ss_method, 0.0)
        rows.append(dict(zip(group, key if isinstance(key, tuple) else (key,)))
                    | {"n": int(len(v)), "grand_mean": round(grand, 3),
                       "SS_total": ss_tot, "SS_model": ss_model,
                       "SS_method": ss_method, "SS_residual": ss_res,
                       "model_share_pct": 100 * ss_model / ss_tot,
                       "method_share_pct": 100 * ss_method / ss_tot,
                       "residual_share_pct": 100 * ss_res / ss_tot,
                       "n_models": int(g.model.nunique()),
                       "n_methods": int(g.method.nunique()),
                       "model_form": "GCM main effect + BC-method main effect + "
                                     "residual (INCLUDING the GCM x method "
                                     "interaction). This is a main-effect "
                                     "sum-of-squares partition, NOT a full "
                                     "variance-component analysis.",
                       "definition": "two-way SS decomposition; shares sum to 100",
                       "interpretation": "method_share_pct is the ADDITIVE MAIN "
                                         "EFFECT of the bias-correction method. "
                                         "The residual term contains the "
                                         "model x method interaction, so a small "
                                         "main effect does not mean the method "
                                         "choice is unimportant for individual "
                                         "models, stations or quantiles."})
    return pd.DataFrame(rows)


def raw_signal_check(sig: pd.DataFrame, index_name: str = "PRCPTOT",
                     limit_pct: float = 25.0) -> pd.DataFrame:
    """Separate a bias-correction artefact from a raw-input problem.

    If the raw GCM already contains the extreme change and the preservation
    error is near zero, the bias correction reproduced the model faithfully and
    any implausibility belongs to the raw input, not to the method.  Flagged
    combinations are quarantined rather than silently reported.
    """
    s = sig[sig["index"] == index_name]
    g = (s.groupby(["scenario", "window"])
           [["raw_change_pct", "bc_change_pct", "PE_pct"]].median().reset_index())
    g["raw_beyond_limit"] = g["raw_change_pct"].abs() > limit_pct
    g["bc_faithful"] = g["PE_pct"].abs() < 5.0
    g["attribution"] = np.where(
        ~g["raw_beyond_limit"], "within expected range",
        np.where(g["bc_faithful"],
                 "RAW INPUT: bias correction preserved the model signal "
                 "(|PE|<5%); verify the raw CMIP6 extraction",
                 "BIAS CORRECTION: signal distorted by the method"))
    g["usable_for_results"] = ~g["raw_beyond_limit"]
    return g


def run_gates(qc_summary: pd.DataFrame, cal_perf: pd.DataFrame,
              val_perf: pd.DataFrame, boundary_ok: bool,
              raw_check: pd.DataFrame = None, temporal=None,
              homogeneity: pd.DataFrame = None, source_trace: dict = None,
              primary_method: str = "qdm") -> pd.DataFrame:
    g = []
    counts = dict(zip(qc_summary.classification, qc_summary.station_months))

    # ---- Gate A: observed data -------------------------------------------
    inhom = []
    if homogeneity is not None:
        inhom = homogeneity.loc[~homogeneity.homogeneous, "station"].astype(str).tolist()
    g.append(gate(
        "A: observed data",
        PASS_RESIDUAL if inhom else PASS,
        "suspicious zeros classified by automated screening; no imputation",
        f"classes {counts}; 0 values imputed",
        limitation=("station metadata not yet verified; "
                    f"{len(inhom)} gauge(s) inhomogeneous between calibration and "
                    f"validation ({', '.join(inhom)}). QC is closed for automated "
                    "screening but NOT for station homogenisation.")
        if inhom else ""))

    # ---- Gate B: calibration-period correction ---------------------------
    cb = cal_perf[cal_perf.method == primary_method]
    marg = ["wet_day_pct", "PRCPTOT", "SDII", "q50", "q90", "q95", "q99"]
    marg_bias = float(np.nanmean([cb[f"{k}_bias_pct"].abs().mean()
                                  for k in marg if f"{k}_bias_pct" in cb.columns]))
    temp = ["CDD", "CWD", "Rx5day", "Rx1day"]
    temp_bias = float(np.nanmean([cb[f"{k}_bias_pct"].abs().mean()
                                  for k in temp if f"{k}_bias_pct" in cb.columns]))
    marg_ok = marg_bias < 5.0
    g.append(gate(
        "B: historical bias correction",
        (PASS if marg_ok and temp_bias < 10 else
         PASS_PARTIAL if marg_ok else BLOCKED),
        "calibration-period MARGINAL distribution reproduced (|bias| < 5%); "
        "this criterion covers the marginal distribution only and makes no "
        "claim about temporal or multi-day structure (see Gate G)",
        f"marginal |bias| {marg_bias:.2f}%; spell/multi-day |bias| {temp_bias:.2f}%",
        limitation=("quantile mapping is a marginal transformation and does not "
                    "reorder days, so CDD, CWD and Rx5day retain the model's own "
                    "temporal structure. Do not claim that extremes as a class "
                    "were successfully reproduced.")
        if temp_bias >= 10 else ""))

    # ---- Gate C: independent validation ----------------------------------
    prim = ["wet_day_pct", "PRCPTOT", "SDII", "q95"]
    better, resid = [], []
    for k in prim:
        c = f"{k}_bias_pct"
        if c not in val_perf.columns:
            continue
        raw = val_perf[val_perf.method == "raw"][c].abs().mean()
        bcm = val_perf[val_perf.method == primary_method][c].abs().mean()
        better.append(bcm < raw)
        resid.append(bcm)
    mean_resid = float(np.nanmean(resid)) if resid else np.nan
    improved = sum(better) >= max(len(better) - 1, 1)
    sub_txt = ""
    if "homogeneous_gauge" in val_perf.columns:
        h = val_perf[val_perf.homogeneous_gauge & (val_perf.method == primary_method)]
        sub = float(np.nanmean([h[f"{k}_bias_pct"].abs().mean()
                                for k in prim if f"{k}_bias_pct" in h.columns]))
        # Associational, not causal: excluding the flagged gauges reduces the
        # network mean.  That is an observation about the aggregate, not a
        # decomposition attributing a share of the error to those gauges.
        sub_txt = (f"; excluding the {int((~val_perf.homogeneous_gauge).sum() > 0) and ''}"
                   f"gauges flagged as non-homogeneous, the network-mean "
                   f"residual is {sub:.1f}%")
    g.append(gate(
        "C: independent validation",
        (BLOCKED if not improved else
         PASS if mean_resid < 10 else PASS_RESIDUAL),
        "out-of-sample |bias| smaller than raw GCM on the primary metrics",
        f"improved on {sum(better)}/{len(better)}; mean residual |bias| "
        f"{mean_resid:.1f}%{sub_txt}",
        limitation=("residual out-of-sample error remains substantial. 'Better "
                    "than raw' does not mean 'reliable for all extremes'; "
                    "station-level errors are larger than the network mean. The "
                    "reduction obtained by excluding non-homogeneous gauges is "
                    "an association between station heterogeneity and validation "
                    "error, not a causal attribution of a share of that error.")
        if mean_resid >= 10 else ""))

    # ---- Gate D: future signal definition ---------------------------------
    g.append(gate("D: future signal", PASS,
                  "change = BC_future / BC_historical, same model and method",
                  "enforced in code; observations never used as denominator"))

    # ---- Gate E: method comparison ---------------------------------------
    have = set(val_perf.method.unique())
    g.append(gate("E: method comparison",
                  PASS if {"raw", "qm", "detqm", "qdm"} <= have else BLOCKED,
                  "raw, QM, DetQM and QDM evaluated on an identical split",
                  f"methods present: {sorted(have)}"))

    # ---- Gate F: spatial products ----------------------------------------
    g.append(gate("F: maps and boundary", PASS if boundary_ok else BLOCKED,
                  "verified administrative boundary, CRS and coordinates",
                  "verified" if boundary_ok
                  else "supplied geometry is a bounding-box rectangle",
                  limitation="" if boundary_ok
                  else "no map is produced until a verified boundary is supplied"))

    # ---- Gate G: temporal dependence -------------------------------------
    if temporal is not None:
        # Diagnostic only.  No hard acceptance threshold is imposed because
        # QM/DetQM/QDM are marginal transformations and do not explicitly
        # reconstruct temporal sequencing; a numeric bar would either fail every
        # method by construction or be met only by accident.
        m = temporal.get("metrics", {})
        improved = [k for k, v in m.items()
                    if v["bc_abs_bias_pct"] < v["raw_abs_bias_pct"]]
        worse = [k for k, v in m.items()
                 if v["bc_abs_bias_pct"] >= v["raw_abs_bias_pct"]]
        g.append(gate(
            "G: temporal dependence",
            PASS_TEMPORAL_UNCORRECTED,
            "DIAGNOSTIC ONLY - this gate measures and reports temporal "
            "dependence; it is not an acceptance criterion for prediction "
            "performance. No hard threshold is imposed because QM/DetQM/QDM are "
            "marginal transformations and do not explicitly reconstruct "
            "temporal sequencing",
            f"improved vs raw on {len(improved)}/{len(m)} sequencing statistics "
            f"({', '.join(improved) if improved else 'none'}); worst residual "
            f"|bias| {temporal.get('worst_abs_bias_pct')}%"
            + (f"; not improved: {', '.join(worse)}" if worse else ""),
            limitation="the bias correction improved selected occurrence-"
                       "transition statistics relative to the raw GCM, but "
                       "substantial residual biases remain in spell-duration and "
                       "multi-day statistics. Do not interpret CDD, CWD or "
                       "Rx5day projections as corrected."))

    # ---- Gate H: raw-input anomaly review --------------------------------
    # NOT an acceptance gate for the bias correction.  A raw change outside the
    # regional literature range is a flag for tracing the input, never evidence
    # that an algorithm failed; the attribution is made from the preservation
    # error, which is an internal measurement.
    if raw_check is not None and len(raw_check):
        bad = raw_check[raw_check.raw_beyond_limit]
        # Once the source trace has run and found no extraction, unit, calendar
        # or concatenation fault, the anomaly is VERIFIED as a property of the
        # raw input rather than left as an open warning.  Interpretation stays
        # restricted because the source NetCDF was never available.
        traced = bool(source_trace and source_trace.get("verdict"))
        status = (PASS if bad.empty
                  else VERIFIED_ANOMALY if traced else WARNING)
        g.append(gate(
            "H: raw-data anomaly review", status,
            "raw model change reviewed against the regional literature range; "
            "flagged cases are quarantined from interpretation, not failed",
            ("no anomaly" if bad.empty else "; ".join(
                f"{r.scenario}/{r.window}: raw {r.raw_change_pct:.0f}%, "
                f"PE {r.PE_pct:+.1f}% -> anomaly originates in the RAW input"
                for r in bad.itertuples()))
            + (f" | source trace: {source_trace.get('summary','')}"
               if traced else ""),
            limitation="" if bad.empty else
            (source_trace.get("limitation") if traced else
             "the bias correction preserved the raw model signal (|PE| < 5%), so "
             "this is not a method failure. Trace source NetCDF -> grid/station "
             "extraction -> units -> calendar -> temporal aggregation before "
             "interpreting these scenario-horizons.")))
    return pd.DataFrame(g)


# ---------------------------------------------------------------------------
# Canonical ensemble estimator (Paper 2, gate P2-E1)
#
# One definition, used by the tables, the figures, the narrative and the claim
# audit. Any other aggregation of the same quantity is a bug.
#
#     E_m = mean over the N gauge evaluation locations of PE within GCM m
#     reported value = median over the M GCMs of E_m
#
# The gauges are evaluation locations, not independent model realizations, so
# they are averaged inside a model before the ensemble summary is taken. Pooling
# gauge x model combinations into one sample would let the gauge count outweigh
# the model spread, which is exactly the quantity this study is about.
# Estimation is always separate by scenario and index; scenarios are never
# pooled, because no aggregation across forcing pathways is defined.
# ---------------------------------------------------------------------------
ESTIMATOR_ID = "model_level_gauge_mean_then_ensemble_median"
ESTIMATOR_TEXT = (
    "mean across the gauge evaluation locations within each GCM, then the "
    "median across GCMs, calculated separately for each scenario and index"
)


def model_values(df: pd.DataFrame, value: str, *, index: str, method: str,
                 scenario: str, index_col: str = "index",
                 with_counts: bool = False):
    """One value per GCM: the mean over gauges at which `value` is defined.

    A gauge contributes only where the quantity exists; for threshold indices a
    model can have no qualifying day in the baseline, which leaves the ratio
    undefined. The number of contributing gauges and models is returned so the
    manuscript can state it rather than hide it.
    """
    sel = df[(df[index_col] == index) & (df["method"] == method)
             & (df["scenario"] == scenario)]
    g = sel.groupby("model")[value]
    v = g.mean()
    v = v[np.isfinite(v)]
    if not with_counts:
        return v
    n_gauges = g.apply(lambda s: int(np.isfinite(s).sum()))
    return v, n_gauges.reindex(v.index)


def ensemble_summary(df: pd.DataFrame, value: str, *, index: str, method: str,
                     scenario: str, index_col: str = "index") -> dict:
    """The canonical summary of a quantity, with its inter-model spread."""
    v, ng = model_values(df, value, index=index, method=method,
                         scenario=scenario, index_col=index_col,
                         with_counts=True)
    if not len(v):
        return {"n_models": 0, "gauges_min": 0, "gauges_max": 0,
                "median": np.nan, "q25": np.nan, "q75": np.nan,
                "mean": np.nan, "sd": np.nan, "min": np.nan, "max": np.nan,
                "estimator": ESTIMATOR_ID}
    a = v.to_numpy(float)
    return {"n_models": int(len(a)),
            "gauges_min": int(ng.min()), "gauges_max": int(ng.max()),
            "median": float(np.median(a)),
            "q25": float(np.percentile(a, 25)),
            "q75": float(np.percentile(a, 75)),
            "mean": float(a.mean()),
            "sd": float(a.std(ddof=1)) if len(a) > 1 else np.nan,
            "min": float(a.min()), "max": float(a.max()),
            "estimator": ESTIMATOR_ID}


def ensemble_frame(df: pd.DataFrame, value: str, indices, methods, scenarios,
                   index_col: str = "index") -> pd.DataFrame:
    """Long-format table of the canonical summary, one row per cell.

    This frame is the single source of truth for Paper 2: the main tables, the
    figures and the claim audit all read it, so a number in the manuscript can
    always be resolved to one row here.
    """
    rows = []
    for sc in scenarios:
        for k in indices:
            for m in methods:
                s = ensemble_summary(df, value, index=k, method=m, scenario=sc,
                                     index_col=index_col)
                rows.append({"scenario": sc, "index": k, "method": m, **s})
    return pd.DataFrame(rows)
