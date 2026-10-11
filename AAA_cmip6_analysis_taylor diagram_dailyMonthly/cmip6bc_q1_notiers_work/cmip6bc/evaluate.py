"""
evaluate.py — Step 3.

Primary analysis
    all stations passing quality control · annual pooled QDM
    uncapped upper tail · station-wise

Sensitivity analyses
    monthly-grouped QDM versus annual pooled QDM
    upper-tail cap at 1.5 x calibration observed maximum

Rules enforced in code, not merely in prose
    · no daily multi-model ensemble is ever formed (build_mme refuses)
    · calibration wet-day frequency is labelled construction-dependent
    · every station that passes quality control enters on equal footing
"""
from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

import io_layer
import metrics as M
import qc
import qdm_core
from provenance import Provenance

SEP = "═" * 78


def variant_cfg(cfg: dict, grouping: str, cap: float | None) -> dict:
    v = copy.deepcopy(cfg)
    v["qdm"]["grouping"] = grouping
    v["qdm"]["upper_tail_cap_factor"] = cap
    return v


def build_mme_monthly(members: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Multi-model ensemble, monthly totals only.

    Averaging daily rainfall across free-running GCMs whose events are not in
    phase produces a series that is not a weather realisation: wet-day
    frequency inflates, variance halves and extremes collapse.  The ensemble
    is therefore formed only after aggregation to monthly totals.
    """
    monthly = {m: df.resample("MS").sum(min_count=25) for m, df in members.items()}
    idx = None
    cols = None
    for df in monthly.values():
        idx = df.index if idx is None else idx.intersection(df.index)
        cols = list(df.columns) if cols is None else [c for c in cols if c in df.columns]
    stack = np.stack([monthly[m].loc[idx, cols].to_numpy(dtype=float)
                      for m in monthly], axis=0)
    if np.isnan(stack).any():
        stack = np.where(np.isnan(stack).any(axis=0, keepdims=True), np.nan, stack)
    return pd.DataFrame(stack.mean(axis=0), index=idx, columns=cols)


def evaluate_variant(name: str, cfg: dict, ds: io_layer.Dataset,
                     grouping: str, cap: float | None,
                     rng: np.random.Generator) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    vcfg = variant_cfg(cfg, grouping, cap)
    wet_thr = float(cfg["data"]["wet_threshold_mm"])
    calp, valp = cfg["periods"]["calibration"], cfg["periods"]["validation"]
    qs = tuple(cfg["evaluate"]["quantiles_reported"])
    nrep = int(cfg["evaluate"]["bootstrap"]["n_replicates"])

    obs = ds.observed.df
    corrected: dict[str, dict[str, pd.DataFrame]] = {}
    for model, b in ds.raw.items():
        per_method, _ = qdm_core.correct_model(obs, b.df, vcfg, model)
        corrected[model] = per_method

    rows, boot_rows = [], []
    for model, b in ds.raw.items():
        datasets = {"raw": b.df, "QDM": corrected[model]["QDM"]}
        if "EQM" in corrected[model]:
            datasets["EQM"] = corrected[model]["EQM"]

        for stn in ds.stations:
            o_all = obs[stn]
            hist_max = float(np.nanmax(o_all.to_numpy(dtype=float)))
            for dsname, df in datasets.items():
                for pname, yrs in (("calibration", calp), ("validation", valp)):
                    ix = df.index[(df.index.year >= yrs[0]) & (df.index.year <= yrs[1])]
                    m = M.full_metrics(o_all, df.loc[ix, stn], wet_thr, hist_max, qs)
                    rows.append(dict(variant=name, model=model, station=stn,
                                     dataset=dsname, period=pname, **m))

            # bootstrap: QDM vs raw, validation only, whole-year blocks
            def _mon(series: pd.Series) -> np.ndarray:
                s = series[(series.index.year >= valp[0]) & (series.index.year <= valp[1])]
                mo = s.resample("MS").sum(min_count=25)
                return mo.to_numpy(dtype=float).reshape(-1, 12)

            try:
                res = M.year_block_bootstrap(_mon(o_all), _mon(b.df[stn]),
                                             _mon(corrected[model]["QDM"][stn]),
                                             nrep, rng)
            except Exception:
                res = {}
            for met, r in res.items():
                boot_rows.append(dict(variant=name, model=model, station=stn,
                                      metric=met, **r))

    metrics_df = pd.DataFrame(rows)
    boot_df = pd.DataFrame(boot_rows)
    if not boot_df.empty:
        rej, q = M.benjamini_hochberg(boot_df.p_value.to_numpy(),
                                      float(cfg["evaluate"]["fdr_alpha"]))
        boot_df["q_value"] = np.round(q, 5)
        boot_df["fdr_reject"] = rej

    # MME — monthly only
    mme_rows = []
    for dsname in ("raw", "QDM"):
        members = ({m: ds.raw[m].df for m in ds.raw} if dsname == "raw"
                   else {m: corrected[m]["QDM"] for m in ds.raw})
        mme = build_mme_monthly(members)
        obs_m = obs.resample("MS").sum(min_count=25)
        for pname, yrs in (("calibration", calp), ("validation", valp)):
            sel = (mme.index.year >= yrs[0]) & (mme.index.year <= yrs[1])
            for stn in ds.stations:
                mm = M.paired_metrics(obs_m.loc[mme.index[sel], stn].to_numpy(dtype=float),
                                      mme.loc[mme.index[sel], stn].to_numpy(dtype=float), "m")
                mme_rows.append(dict(variant=name, model="MME_monthly", station=stn,
                                     dataset=dsname, period=pname, **mm))
    mme_df = pd.DataFrame(mme_rows)
    return metrics_df, boot_df, mme_df


def summarise(metrics_df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    keys = ["mRMSE", "mMAE", "mPBIAS", "mr", "mNSE", "mKGE", "md",
            "PBIAS", "wetfreq_bias", "SDII_relbias_pct", "PSS", "KS_D",
            "q95_relbias_pct", "q99_relbias_pct", "Rx1day_relbias_pct",
            "clim_r", "monthly_anom_r", "annual_r", "n_days_above_obs_hist_max"]
    lower_better = {"mRMSE", "mMAE", "KS_D"}
    abs_better = {"mPBIAS", "PBIAS", "wetfreq_bias", "SDII_relbias_pct",
                  "q95_relbias_pct", "q99_relbias_pct", "Rx1day_relbias_pct"}

    out = []
    for variant in metrics_df.variant.unique():
        d = metrics_df[metrics_df.variant == variant]
        for setname, dd in (("all_stations", d),):
            for period in ("calibration", "validation"):
                dp = dd[dd.period == period]
                raw = dp[dp.dataset == "raw"].set_index(["model", "station"])
                qdm = dp[dp.dataset == "QDM"].set_index(["model", "station"])
                common = raw.index.intersection(qdm.index)
                for k in keys:
                    if k not in raw.columns:
                        continue
                    a = raw.loc[common, k].to_numpy(dtype=float)
                    b = qdm.loc[common, k].to_numpy(dtype=float)
                    ok = np.isfinite(a) & np.isfinite(b)
                    if ok.sum() == 0:
                        continue
                    a, b = a[ok], b[ok]
                    if k in abs_better:
                        imp = np.abs(b) < np.abs(a)
                    elif k in lower_better:
                        imp = b < a
                    else:
                        imp = b > a
                    out.append(dict(
                        variant=variant, station_set=setname, period=period,
                        metric=k, group=M.METRIC_GROUP.get(k, "-"),
                        raw_mean=round(float(np.mean(a)), 4),
                        qdm_mean=round(float(np.mean(b)), 4),
                        delta_mean=round(float(np.mean(b - a)), 4),
                        n_improved=int(imp.sum()), n_total=int(imp.size),
                        pct_improved=round(100 * float(imp.mean()), 1)))
    return pd.DataFrame(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))
    seed = int(cfg["reproducibility"]["random_seed"])
    rng = np.random.default_rng(seed)
    out_dir = Path(cfg["paths"]["out_dir"])

    prov = Provenance(cfg, args.config)
    print(SEP); print("  Step 3 — evaluate"); print(SEP)
    ds = io_layer.build_dataset(cfg, prov)
    qcr = qc.qc_gate(qc.station_diagnostics(ds.observed.df, cfg), cfg)

    g = cfg["qdm"]["grouping"]
    variants = [
        ("primary",       g["primary"],     None),
        ("sens_monthly",  g["sensitivity"], None),
        ("sens_tailcap",  g["primary"],     float(cfg["qdm"]["sensitivity_cap_factor"])),
    ]

    all_m, all_b, all_mme = [], [], []
    for name, grouping, cap in variants:
        print(f"\n  variant {name:14s} grouping={grouping:8s} cap={cap}")
        m, b, mm = evaluate_variant(name, cfg, ds, grouping, cap, rng)
        all_m.append(m); all_b.append(b); all_mme.append(mm)
        print(f"    metric rows {len(m):5d} · bootstrap rows {len(b):4d} · mme rows {len(mm):4d}")

    metrics_df = pd.concat(all_m, ignore_index=True)
    boot_df = pd.concat(all_b, ignore_index=True)
    mme_df = pd.concat(all_mme, ignore_index=True)
    summary = summarise(metrics_df, cfg)

    xl = out_dir / "evaluation_results.xlsx"
    with pd.ExcelWriter(xl, engine="openpyxl") as w:
        summary.to_excel(w, sheet_name="E01_summary", index=False)
        metrics_df[metrics_df.variant == "primary"].to_excel(
            w, sheet_name="E02_primary_station_metrics", index=False)
        mme_df.to_excel(w, sheet_name="E03_MME_monthly", index=False)
        boot_df.to_excel(w, sheet_name="E04_bootstrap_FDR", index=False)
        metrics_df[metrics_df.variant != "primary"].to_excel(
            w, sheet_name="E05_sensitivity_metrics", index=False)
        qcr.to_excel(w, sheet_name="E06_station_qc", index=False)
        pd.DataFrame([{"metric": k, "group": v} for k, v in M.METRIC_GROUP.items()]
                     ).to_excel(w, sheet_name="E07_metric_status", index=False)
    from openpyxl import load_workbook
    from openpyxl.styles import Font
    wb = load_workbook(xl)
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                c.font = Font(name="Times New Roman", size=10,
                              bold=(c.row == 1))
    wb.save(xl)

    metrics_df.to_csv(out_dir / "evaluation_station_metrics.csv", index=False)
    boot_df.to_csv(out_dir / "evaluation_bootstrap.csv", index=False)
    summary.to_csv(out_dir / "evaluation_summary.csv", index=False)
    prov.set("evaluate", dict(variants=[v[0] for v in variants],
                              n_bootstrap=int(cfg["evaluate"]["bootstrap"]["n_replicates"]),
                              seed=seed))
    prov.write(out_dir, "provenance_stage_evaluate")
    print(f"\n  ✓ written -> {xl}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
