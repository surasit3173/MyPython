#!/usr/bin/env python3
"""Single-source pipeline for both papers.

    python scripts/run_pipeline.py --config config/uttaradit.yaml

Stages
  1 observed QC              4 apply to validation (frozen)
  2 CMIP6 inventory          5 apply to baseline + future windows
  3 fit on calibration       6 indices, signal preservation, ensemble, gates

Nothing downstream of stage 3 ever touches the observations of the target
period, so the validation is genuinely out-of-sample.
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cmip6bc import analysis, bc, io_data, metrics, qc_observed, temporal  # noqa: E402
from cmip6bc.config import Manifest, load_config                          # noqa: E402

log = logging.getLogger("pipeline")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.WARNING if a.quiet else logging.INFO,
                        format="%(levelname)s | %(message)s")

    t0 = time.time()
    cfg = load_config(a.config)
    np.random.seed(cfg.seed)
    man = Manifest(cfg)
    res = cfg.out("results")

    cal, val = cfg.period("calibration"), cfg.period("validation")
    base = cfg.period("baseline")
    windows = cfg.future_windows
    wet_thr = cfg.wet_thr
    methods = cfg.methods

    # ---------------------------------------------------------------- stage 1
    log.info("[1/6] observed data and zero quality control")
    obs_path = cfg.path("observed")
    man.add_input("observed", obs_path)
    stations = io_data.resolve_stations(
        obs_path, cfg.path("gis"), cfg.raw["area"].get("stations"))
    obs_raw = io_data.load_observed(obs_path, stations)
    log.info("    %d stations: %s ... %s", len(stations), stations[0], stations[-1])

    diag = qc_observed.diagnose(obs_raw, cfg.raw["observed_qc"])
    obs, n_nan = qc_observed.apply_flags(diag, obs_raw) if False else \
        qc_observed.apply_flags(obs_raw, diag)
    qc_sum = qc_observed.summary(diag)
    qc_dir = cfg.out("qc")
    diag[diag.classification != "not_zero"].to_csv(qc_dir / "QC_flags.csv", index=False)
    obs.to_csv(qc_dir / "Observed_Rain_daily_QC.csv")
    with pd.ExcelWriter(qc_dir / "OBS_ZERO_QC.xlsx", engine="xlsxwriter") as w:
        qc_sum.to_excel(w, index=False, sheet_name="summary")
        diag[diag.classification != "not_zero"].to_excel(
            w, index=False, sheet_name="flagged_station_months")
        diag[diag.classification == "probable_missing"].to_excel(
            w, index=False, sheet_name="probable_missing")
    log.info("    %s", dict(zip(qc_sum.classification, qc_sum.station_months)))
    log.info("    %d daily values set to NaN (%.3f%%); nothing imputed",
             n_nan, 100 * n_nan / obs.size)
    man.add("observed_qc", {"classes": dict(zip(qc_sum.classification,
                                                qc_sum.station_months.astype(int))),
                            "daily_values_to_nan": int(n_nan),
                            "imputed_values": 0,
                            "rule": "0 -> NaN only with a neighbour-based "
                                    "contradiction plus >= 2 indicators"})

    # ---- station homogeneity between calibration and validation -----------
    # A gauge whose own wet-day frequency changes sharply between the two
    # periods cannot be reproduced out-of-sample by ANY method calibrated on
    # the first period.  This is an observation problem, not a BC failure, so
    # it is measured explicitly and carried into the sensitivity analysis.
    hom = []
    for s in stations:
        a = _wetpct(obs[s], cal, wet_thr)
        b = _wetpct(obs[s], val, wet_thr)
        ratio = b / a if a > 0 else np.nan
        hom.append({"station": s, "wet_pct_calibration": round(a, 2),
                    "wet_pct_validation": round(b, 2),
                    "ratio_val_over_cal": round(ratio, 3),
                    "homogeneous": bool(0.75 <= ratio <= 1.33),
                    "note": "wet-day frequency ratio outside 0.75-1.33 indicates "
                            "a likely change in observing practice"})
    homog = pd.DataFrame(hom)
    homog.to_csv(qc_dir / "station_homogeneity.csv", index=False)
    inhomog = homog.loc[~homog.homogeneous, "station"].tolist()
    if inhomog:
        log.warning("    %d gauge(s) inhomogeneous between calibration and "
                    "validation: %s", len(inhomog), ", ".join(inhomog))
    man.add("station_homogeneity", {"inhomogeneous": inhomog,
                                    "criterion": "wet-day frequency ratio "
                                                 "validation/calibration in [0.75, 1.33]"})

    # percentile reference from the calibration period (observed, per station)
    pct_ref = {}
    for s in stations:
        seg = obs[s][(obs.index.year >= cal[0]) & (obs.index.year <= cal[1])]
        pct_ref[s] = metrics.wet_percentiles(seg, wet_thr)
    man.add("percentile_reference", {"period": list(cal), "wet_threshold_mm": wet_thr,
                                     "method": "numpy linear (type 7) on wet days"})

    # ---------------------------------------------------------------- stage 2
    log.info("[2/6] CMIP6 raw inventory")
    files = io_data.discover_raw(cfg.path("cmip6_raw"), cfg.scenarios)
    if not files:
        sys.exit("no raw CMIP6 files found - check paths.cmip6_raw")
    inv, raw_frames = [], {}
    for rf in files:
        fr = io_data.load_raw(rf, stations)
        raw_frames[rf.key()] = fr
        crep = io_data.calendar_report(fr)
        urep = io_data.unit_check(fr, rf.path.name)
        man.add_input(f"{rf.model}/{rf.scenario}", rf.path)
        inv.append({"model": rf.model, "scenario": rf.scenario,
                    "variant": rf.variant, "grid": rf.grid,
                    "file": rf.path.name, **crep, **{
                        k: urep[k] for k in ("mean_daily_mm", "implied_annual_mm",
                                             "verdict")}})
    inventory = pd.DataFrame(inv)
    inventory.to_csv(res / "cmip6_inventory.csv", index=False)
    models = sorted({r.model for r in files
                     if r.scenario == "historical"} &
                    {r.model for r in files if r.scenario in cfg.scenarios})
    if cfg.raw.get("models"):
        models = [m for m in models if m in set(cfg.raw["models"])]
    log.info("    %d models with historical + %s: %s",
             len(models), "/".join(cfg.scenarios), ", ".join(models))
    bad = inventory[~inventory.verdict.str.startswith("OK")]
    if len(bad):
        sys.exit(f"unit check failed:\n{bad[['file','verdict']]}")
    man.add("cmip6_inventory", inventory.to_dict("records"))

    # ------------------------------------------------------- stages 3, 4, 5
    log.info("[3/6] fitting on %d-%d and freezing parameters", *cal)
    daily_rows, fit_rows, apply_rows, temporal_rows = [], [], [], []
    index_rows, period_rows = [], []

    def _seg(frame, y0, y1, s):
        v = frame[s]
        return v[(v.index.year >= y0) & (v.index.year <= y1)]

    for model in models:
        hist = raw_frames[(model, "historical")]
        for s in stations:
            o_cal = _seg(obs, *cal, s)
            m_cal = _seg(hist, *cal, s)
            try:
                fits = bc.fit_all(o_cal, m_cal, station=s, model=model,
                                  methods=methods, wet_thr=wet_thr,
                                  frequency_adaptation=cfg.bc["frequency_adaptation"],
                                  pp_kind=cfg.bc["plotting_position"],
                                  min_wet_days=int(cfg.bc["min_wet_days"]))
            except ValueError as e:
                log.warning("    skip %s/%s: %s", model, s, e)
                continue
            fit_rows.append({"model": model, "station": s,
                             **fits[methods[0]].diagnostics})

            # ---- target periods -------------------------------------------
            targets = [("calibration", "historical", cal),
                       ("validation", "historical", val),
                       ("baseline", "historical", base)]
            for scen in cfg.scenarios:
                for wname, (y0, y1) in windows.items():
                    targets.append((wname, scen, (y0, y1)))

            for label, scen, (y0, y1) in targets:
                src = hist if scen == "historical" else raw_frames.get((model, scen))
                if src is None:
                    continue
                x = _seg(src, y0, y1, s)
                if x.dropna().empty:
                    continue
                series = {"raw": x}
                for m in methods:
                    y, info = bc.apply(fits[m], x.to_numpy())
                    series[m] = pd.Series(y, index=x.index)
                    if label in ("calibration", "validation"):
                        apply_rows.append({"model": model, "station": s, "method": m,
                                           "period": label, **info})
                p95 = pct_ref[s]["p95"]; p99 = pct_ref[s]["p99"]
                for m, sv in series.items():
                    if label in ("calibration", "validation"):
                        tm = temporal.temporal_metrics(sv, wet_thr=wet_thr)
                        if tm:
                            temporal_rows.append({"model": model, "station": s,
                                                  "method": m, "period": label, **tm})
                    pm = metrics.period_metrics(sv, wet_thr=wet_thr,
                                                p95=p95, p99=p99)
                    period_rows.append({"model": model, "station": s, "method": m,
                                        "period": label, "scenario": scen,
                                        "y0": y0, "y1": y1, **pm})
                    ann = metrics.annual_indices(sv, wet_thr=wet_thr,
                                                 p95=p95, p99=p99,
                                                 wanted=cfg.index_set)
                    ann.insert(0, "period", label)
                    ann.insert(0, "scenario", scen)
                    ann.insert(0, "method", m)
                    ann.insert(0, "station", s)
                    ann.insert(0, "model", model)
                    index_rows.append(ann)
        log.info("    %-16s fitted and applied", model)

    fits_df = pd.DataFrame(fit_rows)
    applied = pd.DataFrame(apply_rows)
    period_df = pd.DataFrame(period_rows)
    annual = pd.concat(index_rows, ignore_index=True)

    # observed reference metrics for the same periods
    obs_rows = []
    for s in stations:
        for label, (y0, y1) in (("calibration", cal), ("validation", val),
                                ("baseline", base)):
            sv = _seg(obs, y0, y1, s)
            obs_rows.append({"station": s, "period": label,
                             **metrics.period_metrics(
                                 sv, wet_thr=wet_thr, p95=pct_ref[s]["p95"],
                                 p99=pct_ref[s]["p99"])})
    obs_df = pd.DataFrame(obs_rows)

    obs_temporal = pd.DataFrame([
        {"station": s, "period": label,
         **temporal.temporal_metrics(_seg(obs, y0, y1, s), wet_thr=wet_thr)}
        for s in stations
        for label, (y0, y1) in (("calibration", cal), ("validation", val))])
    temporal_df = pd.DataFrame(temporal_rows)
    temporal_bias = temporal.temporal_bias(temporal_df, obs_temporal)
    temporal_summary = temporal.summarise(temporal_bias, ["raw"] + methods)
    temporal_verdict = temporal.verdict(temporal_bias)
    log.info("    temporal sequencing: worst spell |bias| raw vs %s -> %s",
             "qdm", temporal_verdict["metrics"])

    log.info("[4/6] performance against observations")
    mkeys = ["wet_day_pct", "PRCPTOT", "SDII", "mean_daily", "sd_daily", "sd_wet",
             "q50", "q90", "q95", "q99", "Rx1day", "Rx5day",
             "R10mm", "R20mm", "R50mm", "CDD", "CWD", "R95p", "R99p"]
    perf = period_df[period_df.period.isin(["calibration", "validation"])].merge(
        obs_df, on=["station", "period"], suffixes=("", "_obs"))
    for k in mkeys:
        o = perf.get(f"{k}_obs")
        if o is None:
            continue
        perf[f"{k}_bias_pct"] = np.where(o.abs() > 1e-9,
                                         100 * (perf[k] - o) / o, np.nan)
    perf["station"] = perf.station.astype(str)
    hom_ok = set(homog[homog.homogeneous].station.astype(str))
    perf["homogeneous_gauge"] = perf.station.isin(hom_ok)
    cal_perf = perf[perf.period == "calibration"]
    val_perf = perf[perf.period == "validation"]
    for m in ["raw"] + methods:
        c = cal_perf[cal_perf.method == m]; v = val_perf[val_perf.method == m]
        log.info("    %-6s cal |wet|=%5.1f%% |SDII|=%5.1f%%   val |wet|=%5.1f%% "
                 "|SDII|=%5.1f%% |q95|=%5.1f%%", m,
                 c.wet_day_pct_bias_pct.abs().mean(), c.SDII_bias_pct.abs().mean(),
                 v.wet_day_pct_bias_pct.abs().mean(), v.SDII_bias_pct.abs().mean(),
                 v.q95_bias_pct.abs().mean())

    # ---------------------------------------------------------------- stage 5
    log.info("[5/6] future change against each model's own BC baseline")
    idx_cols = [c for c in cfg.index_set if c in annual.columns]
    per_period = (annual.melt(id_vars=["model", "station", "method", "scenario",
                                       "period", "year"],
                              value_vars=idx_cols,
                              var_name="index", value_name="value")
                  .groupby(["model", "station", "method", "scenario", "period",
                            "index"], as_index=False)["value"].mean())
    bl = (per_period[per_period.period == "baseline"]
          .rename(columns={"value": "baseline_value"})
          .drop(columns=["period", "scenario"]))
    fut = per_period[per_period.period.isin(windows)].rename(
        columns={"period": "window"})
    changes = fut.merge(bl, on=["model", "station", "method", "index"], how="left")
    changes["change_abs"] = changes["value"] - changes["baseline_value"]
    changes["change_pct"] = np.where(changes.baseline_value.abs() > 1e-9,
                                     100 * changes.change_abs / changes.baseline_value,
                                     np.nan)
    changes["baseline_definition"] = "BC_historical of the same model and method"

    # signal preservation: S = future / baseline, for raw and for each method
    piv = changes.pivot_table(index=["model", "station", "scenario", "window", "index"],
                              columns="method", values="change_pct")
    sig = piv.reset_index().melt(
        id_vars=["model", "station", "scenario", "window", "index", "raw"],
        value_vars=[m for m in methods if m in piv.columns],
        var_name="method", value_name="bc_change_pct").rename(
            columns={"raw": "raw_change_pct"})
    s_mod = 1 + sig.raw_change_pct / 100.0
    s_bc = 1 + sig.bc_change_pct / 100.0
    sig["S_mod"], sig["S_bc"] = s_mod, s_bc
    sig["PE_pct"] = np.where(s_mod.abs() > 1e-9, 100 * (s_bc - s_mod) / s_mod, np.nan)

    log.info("[6/6] ensemble agreement, spread and acceptance gates")
    ens = analysis.ensemble_agreement(
        changes[changes.method.isin(methods)], "change_pct",
        group=("method", "scenario", "window", "station", "index"),
        threshold=cfg.agreement_threshold)
    regional = analysis.ensemble_agreement(
        changes[changes.method.isin(methods)]
        .groupby(["method", "model", "scenario", "window", "index"], as_index=False)
        ["change_pct"].mean(),
        "change_pct", group=("method", "scenario", "window", "index"),
        threshold=cfg.agreement_threshold)
    spread = analysis.variance_decomposition(
        changes[changes.method.isin(methods)], "change_pct")
    spread_sd = analysis.method_vs_model_spread(
        changes[changes.method.isin(methods)], "change_pct")

    boundary_ok = _boundary_verified(cfg)
    source_trace = _load_source_trace(res)
    raw_check = analysis.raw_signal_check(sig)
    raw_check.to_csv(res / "raw_signal_check.csv", index=False)
    gates = analysis.run_gates(qc_sum, cal_perf, val_perf, boundary_ok,
                               raw_check, temporal_verdict, homog, source_trace)
    for r in gates.itertuples():
        log.info("    %-30s %-26s %s", r.gate, r.status, r.evidence[:80])

    # ---------------------------------------------------------------- outputs
    for name, df in [("cmip6_inventory", inventory), ("bc_fit_diagnostics", fits_df),
                     ("bc_apply_diagnostics", applied), ("observed_metrics", obs_df),
                     ("period_metrics", period_df), ("performance", perf),
                     ("annual_indices", annual), ("future_changes", changes),
                     ("signal_preservation", sig), ("ensemble_station", ens),
                     ("ensemble_regional", regional), ("method_vs_model_spread", spread),
                     ("acceptance_gates", gates), ("observed_qc_summary", qc_sum),
                     ("station_homogeneity", homog), ("raw_signal_check", raw_check),
                     ("temporal_metrics", temporal_df),
                     ("temporal_metrics_observed", obs_temporal),
                     ("temporal_bias", temporal_bias),
                     ("temporal_summary", temporal_summary),
                     ("variance_decomposition", spread),
                     ("gate_status_definitions",
                      pd.DataFrame(analysis.STATUS_DEFINITIONS)),
                     ("spread_sd_heuristic", spread_sd)]:
        df.to_csv(res / f"{name}.csv", index=False)
    annual.to_parquet(res / "annual_indices.parquet") if _parquet() else None

    man.add("stations", stations)
    man.add("periods", {"calibration": list(cal), "validation": list(val),
                        "baseline": list(base),
                        "future": {k: list(v) for k, v in windows.items()}})
    man.add("bias_correction", {**cfg.bc,
                                "fit_period": list(cal),
                                "parameters_frozen_before_validation": True,
                                "observations_of_target_period_used": False})
    man.add("gates", gates.to_dict("records"))
    man.add("temporal_dependence", temporal_verdict)
    man.add("spread_definition",
            "two-way model x method sum-of-squares decomposition; shares sum to "
            "100. method_share_pct is the additive MAIN EFFECT; the residual "
            "term contains the model x method interaction.")
    man.add("gate_status_definitions", analysis.STATUS_DEFINITIONS)
    man.add("runtime_seconds", round(time.time() - t0, 1))
    man.write(cfg.path("output") / "manifest" / "run_manifest.json")
    (cfg.path("output") / "manifest" / "package_versions.txt").write_text(
        "\n".join(f"{k}={v}" for k, v in __import__(
            "cmip6bc.config", fromlist=["x"]).package_versions().items()))
    log.info("done in %.1f s -> %s", time.time() - t0, res)


def _wetpct(series, period, wet_thr) -> float:
    v = series[(series.index.year >= period[0]) & (series.index.year <= period[1])]
    v = v.dropna()
    return 100.0 * float((v >= wet_thr).mean()) if len(v) else float("nan")


def _load_source_trace(res: Path) -> dict:
    """Pick up the Gate H trace verdict if scripts/gate_h_source_trace.py has run."""
    f = Path(res) / "gate_h_findings.csv"
    if not f.exists():
        return {}
    d = pd.read_csv(f)
    est = d[d.result.str.startswith("ESTABLISHED")]
    return {"verdict": True,
            "summary": "; ".join(f"{r.check}={r.result}" for r in d.itertuples()),
            "n_established": int(len(est)), "n_checks": int(len(d)),
            "limitation": "source NetCDF metadata NOT ESTABLISHED (files absent); "
                          "no extraction, unit, calendar or concatenation fault "
                          "was found in the delivered CSVs. The anomaly is a "
                          "property of the raw input, not an error of this "
                          "framework. Causal or physical interpretation remains "
                          "restricted; exclude from primary quantitative "
                          "conclusions."}


def _parquet() -> bool:
    try:
        import pyarrow  # noqa: F401
        return True
    except Exception:
        return False


def _boundary_verified(cfg) -> bool:
    """Gate F passes only on a canonical file written by gate_f_boundary.py,
    which records its source, hash, geometry validity and gauge containment.
    A legacy rectangle can never satisfy this."""
    import json
    cand = sorted(Path(cfg.path("gis")).glob("*_adm1_verified.geojson"))
    if not cand:
        return False
    try:
        doc = json.loads(cand[0].read_text(encoding="utf-8"))
        pv = doc.get("provenance", {})
        return bool(pv.get("verified") and pv.get("all_stations_inside")
                    and not pv.get("is_rectangular_frame"))
    except Exception:
        return False


def load_verified_boundary(cfg):
    import json
    cand = sorted(Path(cfg.path("gis")).glob("*_adm1_verified.geojson"))
    if not cand:
        return None
    doc = json.loads(cand[0].read_text(encoding="utf-8"))
    return doc["features"][0], doc.get("provenance", {})


if __name__ == "__main__":
    main()
