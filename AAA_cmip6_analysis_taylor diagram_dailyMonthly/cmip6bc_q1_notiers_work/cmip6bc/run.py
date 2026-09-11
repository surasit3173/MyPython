"""
run.py — stage orchestrator.

    Step 1  io_layer   -> QC GATE 1 (qc.py, provenance.py)
    Step 2  qdm_core   -> QC GATE 2 -> bc_<MODEL>_<METHOD>_split.csv
    [ STOP — inspect outputs before evaluate.py / figures.py ]

Usage
-----
    python run.py --config config.yaml
    python run.py --config config.yaml --stage io      # stop after gate 1
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

import io_layer
import qc
import qdm_core
from provenance import Provenance

SEP = "═" * 78


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# ═══════════════════════════════════════════════════════════════════════════
#  QC GATE 1 — data integrity, screening, seasons
# ═══════════════════════════════════════════════════════════════════════════

def gate1(ds: io_layer.Dataset, cfg: dict, prov: Provenance, out_dir: Path) -> pd.DataFrame:
    print("\n" + SEP)
    print("  QC GATE 1 — data integrity and station screening")
    print(SEP)

    diag = qc.station_diagnostics(ds.observed.df, cfg)
    qcr = qc.qc_gate(diag, cfg)

    print(f"\n  {'station':>9} {'missing%':>9} {'Pettitt p':>10} {'QC':>7}   "
          f"{'SDII':>6} {'lag1':>6} {'maxday':>8}")
    for _, r in qcr.iterrows():
        print(f"  {r.station:>9} {r.missing_pct:9.2f} {r.pettitt_annual_p:10.3f} "
              f"{('pass' if r.passed_qc else 'FAIL'):>7}   "
              f"{r.SDII:6.2f} {r.lag1_acf:6.2f} {r.max_daily:8.1f}")

    n_pass = int(qcr.passed_qc.sum())
    print(f"\n  quality control: {n_pass} of {len(qcr)} stations retained")
    if n_pass < len(qcr):
        for _, r in qcr[~qcr.passed_qc].iterrows():
            print(f"    excluded {r.station}: {r.qc_notes}")
    print("  SDII, lag-1 autocorrelation and maximum daily rainfall are")
    print("  reported as record characteristics; they are not pass/fail criteria.")

    seasons = qc.derive_seasons(ds.observed.df, cfg)
    print(f"\n  derived wet season: months {seasons['wet_months']} "
          f"(DOY {seasons['wet_start_doy']}-{seasons['wet_end_doy']}, "
          f"{seasons['wet_length_days']} d, threshold "
          f"{seasons['threshold_mm_day']} mm d⁻¹)")

    # spatial information content of the raw model fields
    spatial = []
    for m, b in ds.raw.items():
        sub = b.df.loc[b.df.index.intersection(ds.observed.df.index)]
        arr = sub.to_numpy(dtype=float)
        uniq = np.array([np.unique(np.round(row[np.isfinite(row)], 6)).size
                         for row in arr])
        spatial.append(dict(model=m, n_stations=sub.shape[1],
                            median_unique_values_per_day=float(np.median(uniq)),
                            max_unique_values_per_day=int(uniq.max())))
    spatial_df = pd.DataFrame(spatial)
    print("\n  effective spatial information content of raw model fields")
    print("  (distinct daily values across all stations — NOT a formal d.o.f.)")
    for _, r in spatial_df.iterrows():
        print(f"    {r.model:16s} median {r.median_unique_values_per_day:.0f} "
              f"of {r.n_stations} stations")

    meta = ds.station_meta
    n_missing_elev = int(meta.elev_m.isna().sum())
    if n_missing_elev:
        ids = meta.loc[meta.elev_m.isna(), "station"].tolist()
        prov.warn(f"elevation missing for {n_missing_elev} stations: {ids} "
                  f"— supply ./data/station_metadata_verified.csv; "
                  f"do NOT substitute 0 m")

    prov.set("qc", dict(
        n_stations_retained=n_pass, n_stations_total=int(len(qcr)),
        seasons=seasons,
        spatial_information=spatial,
        note=("record characteristics are reported for transparency "
              "and are not used as pass/fail criteria"),
    ))

    out_dir.mkdir(parents=True, exist_ok=True)
    qcr.to_csv(out_dir / "qc_station_report.csv", index=False)
    meta.to_csv(out_dir / "qc_station_metadata.csv", index=False)
    spatial_df.to_csv(out_dir / "qc_spatial_information.csv", index=False)
    with open(out_dir / "qc_seasons.json", "w", encoding="utf-8") as fh:
        json.dump(seasons, fh, indent=2)
    print(f"\n  ✓ gate 1 artefacts -> {out_dir}")
    return qcr


# ═══════════════════════════════════════════════════════════════════════════
#  QC GATE 2 — correction sanity
# ═══════════════════════════════════════════════════════════════════════════

def gate2(all_diag: pd.DataFrame, outputs: dict, ds: io_layer.Dataset,
          cfg: dict, prov: Provenance) -> None:
    print("\n" + SEP)
    print("  QC GATE 2 — correction sanity")
    print(SEP)

    n_unusable = int((~all_diag.usable).sum())
    print(f"\n  unusable station-model-group fits : {n_unusable} "
          f"of {len(all_diag)}")
    if n_unusable:
        for _, r in all_diag[~all_diag.usable].iterrows():
            print(f"    {r.model}/{r.station}/{r.group}: {r.note}")

    n_exceed = int(all_diag.output_exceeds_obs_cal_max.sum())
    print(f"  fits whose output exceeds the calibration observed maximum: "
          f"{n_exceed}")
    if n_exceed:
        worst = all_diag.sort_values("max_output_mm", ascending=False).head(5)
        for _, r in worst.iterrows():
            print(f"    {r.model:16s} {r.station} "
                  f"max {r.max_output_mm:.1f} mm vs obs-cal max "
                  f"{r.obs_cal_max_mm:.1f} mm")

    hi = int(all_diag.n_delta_clipped_high.sum())
    lo = int(all_diag.n_delta_clipped_low.sum())
    print(f"  delta ratio clipped   high: {hi:,}   low: {lo:,}  "
          f"(bounds {cfg['qdm']['min_delta_ratio']}–{cfg['qdm']['max_delta_ratio']})")

    wet_thr = float(cfg["data"]["wet_threshold_mm"])
    cal, val = cfg["periods"]["calibration"], cfg["periods"]["validation"]
    obs = ds.observed.df
    rows = []
    for method, per_model in outputs.items():
        for model, df in per_model.items():
            ix = df.index
            for label, yr in (("calibration", cal), ("validation", val)):
                m = (ix.year >= yr[0]) & (ix.year <= yr[1])
                o = obs.loc[ix[m]]
                rows.append(dict(
                    method=method, model=model, period=label,
                    obs_wet_freq=round(float((o >= wet_thr).to_numpy().mean()), 4),
                    corrected_wet_freq=round(
                        float((df.loc[ix[m]] >= wet_thr).to_numpy().mean()), 4),
                    corrected_mean_mm=round(
                        float(np.nanmean(df.loc[ix[m]].to_numpy(dtype=float))), 4),
                    obs_mean_mm=round(float(np.nanmean(o.to_numpy(dtype=float))), 4),
                ))
    wf = pd.DataFrame(rows)
    print("\n  wet-day frequency — construction-dependent in calibration by design")
    print(wf.to_string(index=False))

    prov.set("qdm", dict(
        n_fits=len(all_diag), n_unusable=n_unusable,
        n_outputs_exceeding_obs_cal_max=n_exceed,
        n_delta_clipped_high=hi, n_delta_clipped_low=lo,
        wet_frequency_check=rows,
        frequency_adaptation=bool(cfg["qdm"]["frequency_adaptation"]),
        note=("wet-day frequency agreement in the calibration period is a "
              "design property of frequency adaptation, not evidence of skill"),
    ))


# ═══════════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════════

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--stage", default="qdm", choices=["io", "qdm"])
    args = ap.parse_args()

    cfg = load_config(args.config)
    np.random.seed(int(cfg["reproducibility"]["random_seed"]))
    out_dir = Path(cfg["paths"]["out_dir"])
    prov = Provenance(cfg, args.config)

    print(SEP)
    print(f"  cmip6bc — {cfg['project']['id']} · {cfg['region']['name']}")
    print(f"  calibration {cfg['periods']['calibration']}  ·  "
          f"validation {cfg['periods']['validation']}")
    print(SEP)

    print("\n  Step 1 — io_layer")
    ds = io_layer.build_dataset(cfg, prov)
    print(f"    stations : {len(ds.stations)}")
    print(f"    calendars: " + ", ".join(
        f"{m}={b.calendar}({b.n_rows})" for m, b in ds.raw.items()))
    print(f"    n_common_days_all_models = {len(ds.common_index):,}")

    qcr = gate1(ds, cfg, prov, out_dir)

    if args.stage == "io":
        prov.write(out_dir, "provenance_stage_io")
        print(f"\n  stopped after gate 1 (--stage io)")
        return 0

    print("\n" + SEP)
    print("  Step 2 — qdm_core   fit(calibration) -> freeze -> apply(validation)")
    print(SEP)

    bc_dir = out_dir / "bc_split"
    bc_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, dict[str, pd.DataFrame]] = {}
    diags = []

    for model, bundle in ds.raw.items():
        print(f"\n  {model}")
        per_method, diag = qdm_core.correct_model(
            ds.observed.df, bundle.df, cfg, model)
        diags.append(diag)
        for method, df in per_method.items():
            outputs.setdefault(method, {})[model] = df
            wide = qdm_core.to_wide_csv(df, cfg)
            fn = bc_dir / f"bc_{model}_{method}_split.csv"
            wide.to_csv(fn, index=False, float_format="%.3f")
            print(f"    -> {fn.name}  ({len(wide):,} rows)")

        meta = dict(
            model=model, source_file=bundle.path, calendar=bundle.calendar,
            unit_factor_applied=bundle.unit_factor,
            calibration_years=cfg["periods"]["calibration"],
            validation_years=cfg["periods"]["validation"],
            grouping=cfg["qdm"]["grouping"],
            frequency_adaptation=cfg["qdm"]["frequency_adaptation"],
            delta_bounds=[cfg["qdm"]["min_delta_ratio"],
                          cfg["qdm"]["max_delta_ratio"]],
            tail_extrapolation=cfg["qdm"]["tail_extrapolation"],
            stations=ds.stations,
            protocol=("transfer functions estimated on calibration years only; "
                      "no validation-period observation used at any stage"),
        )
        with open(bc_dir / f"bc_{model}_split.meta.json", "w", encoding="utf-8") as fh:
            json.dump(meta, fh, indent=2, ensure_ascii=False)

    all_diag = pd.concat(diags, ignore_index=True)
    all_diag.to_csv(out_dir / "qdm_fit_diagnostics.csv", index=False)

    gate2(all_diag, outputs, ds, cfg, prov)

    prov.write(out_dir, "provenance")
    print("\n" + SEP)
    print("  ✓ Steps 1–2 complete.  STOP for inspection.")
    print(f"    corrected series : {bc_dir}")
    print(f"    fit diagnostics  : {out_dir/'qdm_fit_diagnostics.csv'}")
    print(f"    provenance       : {out_dir/'provenance.txt'}")
    print("    next: evaluate.py / figures.py — not run yet, by design")
    print(SEP)
    return 0


if __name__ == "__main__":
    sys.exit(main())
