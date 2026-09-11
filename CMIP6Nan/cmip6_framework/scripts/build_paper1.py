#!/usr/bin/env python3
"""Paper 1 deliverables — QDM projection of precipitation and extremes.

    python scripts/build_paper1.py --config config/uttaradit.yaml

Reads only output/results/*.csv produced by run_pipeline.py, so tables and
figures can never diverge from the analysis.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import json

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from cmip6bc import figures                                   # noqa: E402
from cmip6bc.config import load_config                        # noqa: E402

PRIMARY = "qdm"
HEAD_IDX = ["PRCPTOT", "SDII", "Rx1day", "Rx5day", "R20mm", "R50mm",
            "R95p", "R99p", "CDD", "CWD"]
METRIC_ORDER = ["wet_day_pct", "PRCPTOT", "SDII", "q50", "q90", "q95", "q99",
                "Rx1day", "Rx5day", "R10mm", "R20mm", "R50mm", "CDD", "CWD"]


def _write(tables: dict, path: Path) -> None:
    with pd.ExcelWriter(path, engine="xlsxwriter") as w:
        book = w.book
        hdr = book.add_format({"bold": True, "font_name": "Times New Roman",
                               "font_size": 10, "bg_color": "#E8E8E8",
                               "border": 1, "text_wrap": True, "valign": "vcenter"})
        cell = book.add_format({"font_name": "Times New Roman", "font_size": 10})
        for name, df in tables.items():
            df.to_excel(w, index=False, sheet_name=name[:31])
            ws = w.sheets[name[:31]]
            ws.freeze_panes(1, 0)
            ws.set_column(0, max(len(df.columns) - 1, 0), 15, cell)
            for j, c in enumerate(df.columns):
                ws.write(0, j, str(c), hdr)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    a = ap.parse_args()
    cfg = load_config(a.config)
    res = cfg.path("output") / "results"
    out = cfg.out("paper1")
    figures.init(cfg)
    reg = figures.Registry(out / "figures", "Paper1")

    R = {p.stem: pd.read_csv(p) for p in res.glob("*.csv")}
    qcdir = cfg.path("output") / "qc"
    homog = pd.read_csv(qcdir / "station_homogeneity.csv")
    flags = pd.read_csv(qcdir / "QC_flags.csv")
    coords_all = pd.read_excel(next(Path(cfg.path("gis")).rglob("*coord*.xlsx")))
    coords_all.columns = [c.strip().lower() for c in coords_all.columns]
    coords_all["station"] = coords_all["station"].astype(str)

    perf, changes = R["performance"], R["future_changes"]
    regional, ens = R["ensemble_regional"], R["ensemble_station"]
    inv, gates = R["cmip6_inventory"], R["acceptance_gates"]

    stations = sorted(homog.station.astype(str))
    coords = coords_all[coords_all.station.isin(stations)]

    # ------------------------------------------------------------ Table 1
    obs_m = R["observed_metrics"]
    base = obs_m[obs_m.period == "calibration"].set_index("station")
    pm = (flags[flags.classification == "probable_missing"]
          .groupby("station").size())
    t1 = pd.DataFrame({
        "Station": stations,
        "Longitude (°E)": [float(coords.set_index("station").longitude.get(s, np.nan)) for s in stations],
        "Latitude (°N)": [float(coords.set_index("station").latitude.get(s, np.nan)) for s in stations],
        "Record": f"{cfg.period('calibration')[0]}–{cfg.period('validation')[1]}",
        "Mean annual rainfall (mm)": [round(float(base.PRCPTOT.get(int(s), base.PRCPTOT.get(s, np.nan))), 1) for s in stations],
        "Wet days (%)": [round(float(base.wet_day_pct.get(int(s), base.wet_day_pct.get(s, np.nan))), 1) for s in stations],
        "SDII (mm d⁻¹)": [round(float(base.SDII.get(int(s), base.SDII.get(s, np.nan))), 2) for s in stations],
        "Station-months flagged probable-missing": [int(pm.get(int(s), pm.get(s, 0))) for s in stations],
        "Homogeneous cal/val": [bool(homog.set_index("station").homogeneous.get(int(s), homog.set_index("station").homogeneous.get(s, True))) for s in stations],
    })

    # ------------------------------------------------------------ Table 2 & 3
    def perf_table(period: str) -> pd.DataFrame:
        sub = perf[perf.period == period]
        rows = []
        for m in ["raw", PRIMARY]:
            s = sub[sub.method == m]
            rec = {"Method": "Raw GCM" if m == "raw" else "QDM"}
            for k in METRIC_ORDER:
                col = f"{k}_bias_pct"
                if col in s.columns:
                    rec[f"{k} bias (%)"] = round(float(s[col].mean()), 2)
                    rec[f"{k} |bias| (%)"] = round(float(s[col].abs().mean()), 2)
            rows.append(rec)
        return pd.DataFrame(rows)

    t2, t3 = perf_table("calibration"), perf_table("validation")

    # Sensitivity is reported side by side with the full network, never instead
    # of it, and the excluded gauges are named.
    hom_st = set(homog[homog.homogeneous].station.astype(str))
    excl = sorted(set(homog.station.astype(str)) - hom_st)
    perf["station"] = perf.station.astype(str)
    rows = []
    for period in ("calibration", "validation"):
        for scope, sel in (("Full network (13 gauges)", perf.station.notna()),
                           (f"Homogeneous only ({len(hom_st)} gauges)",
                            perf.station.isin(hom_st))):
            for m in ["raw", PRIMARY]:
                d = perf[(perf.period == period) & sel & (perf.method == m)]
                rec = {"Period": period, "Scope": scope,
                       "Method": "Raw GCM" if m == "raw" else "QDM"}
                for k in METRIC_ORDER:
                    c = f"{k}_bias_pct"
                    if c in d.columns:
                        rec[f"{k} |bias| (%)"] = round(float(d[c].abs().mean()), 2)
                rows.append(rec)
    t3b = pd.DataFrame(rows)
    t3b.attrs["excluded"] = excl

    # temporal-dependence validation
    tsum = pd.read_csv(res / "temporal_summary.csv")
    tbias = pd.read_csv(res / "temporal_bias.csv")

    # ------------------------------------------------------------ Table 4 & 5
    q = changes[changes.method == PRIMARY]
    per_model = q.groupby(["scenario", "window", "model", "index"],
                          as_index=False)["change_pct"].mean()

    thr = cfg.agreement_threshold

    def change_table(indices) -> pd.DataFrame:
        """Every median is followed immediately by its IQR, its agreement
        fraction and a robustness flag, so a reader never sees a projected
        change without the evidence for how well the ensemble supports it."""
        rows = []
        for (sc, win), g in per_model.groupby(["scenario", "window"]):
            rec = {"Scenario": sc.upper(), "Horizon": win}
            for k in indices:
                v_ = g[g["index"] == k]["change_pct"].to_numpy(float)
                v_ = v_[np.isfinite(v_)]
                if not len(v_):
                    continue
                agr = max((v_ > 0).sum(), (v_ < 0).sum()) / len(v_)
                rec[f"{k} median (%)"] = round(float(np.median(v_)), 1)
                rec[f"{k} IQR (%)"] = (f"{np.percentile(v_,25):.1f} to "
                                       f"{np.percentile(v_,75):.1f}")
                rec[f"{k} n models"] = int(len(v_))
                rec[f"{k} agreement"] = round(agr, 2)
                rec[f"{k} robust (>={thr:.0%})"] = "yes" if agr >= thr else "NO"
            rows.append(rec)
        order = {w: i for i, w in enumerate(cfg.future_windows)}
        return (pd.DataFrame(rows)
                .assign(_o=lambda d: d.Horizon.map(order))
                .sort_values(["Scenario", "_o"]).drop(columns="_o"))

    t4 = change_table(["PRCPTOT", "wet_day_pct", "SDII"])
    t5 = change_table([k for k in HEAD_IDX if k != "PRCPTOT"])

    # ------------------------------------------------------------ Table 6
    r = regional[regional.method == PRIMARY]
    t6 = (r[["scenario", "window", "index", "n_models", "median", "q25", "q75",
             "iqr", "min", "max", "agreement_fraction", "robust"]]
          .rename(columns={"scenario": "Scenario", "window": "Horizon",
                           "index": "Index", "n_models": "N models",
                           "median": "Median (%)", "q25": "Q25 (%)",
                           "q75": "Q75 (%)", "iqr": "IQR (%)",
                           "min": "Min (%)", "max": "Max (%)",
                           "agreement_fraction": "Agreement",
                           "robust": f"Robust (>={cfg.agreement_threshold:.0%})"})
          .round(2))

    t7 = tsum[tsum.method.isin(["raw", PRIMARY])].rename(columns={"method": "Method"})
    raw_trace = pd.read_csv(res / "raw_trace_ssp585_Late.csv") \
        if (res / "raw_trace_ssp585_Late.csv").exists() else pd.DataFrame()

    notes = pd.DataFrame([
        {"item": "Change definition",
         "note": "BC_future / BC_historical of the same GCM; the observed record "
                 "is never used as the denominator"},
        {"item": "Baseline",
         "note": f"{cfg.period('baseline')[0]}-{cfg.period('baseline')[1]}, "
                 f"model-consistent"},
        {"item": "Agreement",
         "note": "fraction of GCMs sharing the majority sign of change; the "
                 "continuous fraction is reported, never an interpolated "
                 "boolean"},
        {"item": "Robustness threshold",
         "note": f"{thr:.0%}. A median whose agreement is below this must NOT be "
                 f"described as a robust projection"},
        {"item": "Agreement is reported in-table",
         "note": "every median in Tables 4-6 carries its IQR, model count, "
                 "agreement fraction and robustness flag in adjacent columns"},
        {"item": "Temporal indices",
         "note": "CDD, CWD and Rx5day are NOT corrected by quantile mapping "
                 "(Gate G); interpret them as diagnostic, not as corrected "
                 "projections"},
        {"item": "Quarantined",
         "note": "SSP5-8.5 Late is quarantined by Gate H pending a "
                 "source-NetCDF trace; do not report it as a quantitative "
                 "conclusion"},
    ])

    _write({"Table0_reading_notes": notes,
            "Table1_stations": t1, "Table2_calibration": t2,
            "Table3_validation": t3,
            "Table3b_homogeneity_sensitivity": t3b,
            "Table4_mean_precip_change": t4, "Table5_extreme_change": t5,
            "Table6_agreement_uncertainty": t6,
            "Table7_temporal_dependence": t7,
            "S1_model_inventory": inv, "S2_acceptance_gates": gates,
            "S3_station_homogeneity": homog,
            "S4_station_level_changes": q.round(3),
            "S5_raw_anomaly_trace": raw_trace},
           out / "Paper1_Tables.xlsx")
    for n, d in [("Table1_stations", t1), ("Table4_mean_precip_change", t4),
                 ("Table5_extreme_change", t5), ("Table6_agreement", t6)]:
        d.to_csv(out / f"Paper1_{n}.csv", index=False)

    # ------------------------------------------------------------ Figures
    boundary_ok = gates.loc[gates.gate.str.startswith("F"), "status"].iloc[0] == "PASS"
    geom, rings = None, []
    bpath = sorted(Path(cfg.path("gis")).glob("*_adm1_verified.geojson"))
    if boundary_ok and bpath:
        doc = json.loads(bpath[0].read_text(encoding="utf-8"))
        geom = doc["features"][0]["geometry"]
        rings = [np.asarray(r, float) for r in
                 (geom["coordinates"] if geom["type"] == "Polygon"
                  else [r for poly in geom["coordinates"] for r in poly])]
    warn = "" if boundary_ok else ("Provincial boundary not verified; "
                                   "gauge locations only.")
    figures.fig_study_area(cfg, coords, [(r[:, 0], r[:, 1]) for r in rings],
                           cfg.area, reg, warn)

    figures.fig_hist_validation(cfg, perf[perf.period == "calibration"], reg,
                                f"the calibration period {cfg.period('calibration')[0]}–"
                                f"{cfg.period('calibration')[1]}",
                                "calibration_bias", ["raw", PRIMARY])
    figures.fig_hist_validation(cfg, perf[perf.period == "validation"], reg,
                                f"the independent validation period "
                                f"{cfg.period('validation')[0]}–{cfg.period('validation')[1]}",
                                "independent_validation", ["raw", PRIMARY])

    figures.fig_future_change(
        cfg, r, reg, ["PRCPTOT", "wet_day_pct", "SDII", "Rx1day", "Rx5day"],
        "future_mean_precipitation",
        "Projected change in precipitation characteristics",
        "Multi-model median change (bars) and inter-model interquartile range "
        "(whiskers) in precipitation characteristics relative to each model's own "
        f"bias-corrected baseline ({cfg.period('baseline')[0]}–{cfg.period('baseline')[1]}).")

    figures.fig_future_change(
        cfg, r, reg, [k for k in HEAD_IDX if k not in ("PRCPTOT", "SDII")],
        "future_extreme_indices",
        "Projected change in extreme-rainfall indices",
        "Multi-model median change and inter-model interquartile range for the "
        "extreme-rainfall indices, relative to each model's own bias-corrected "
        "baseline.")

    figures.fig_agreement(
        cfg, r, reg, HEAD_IDX, "model_agreement",
        "Inter-model agreement on the sign of change",
        "Fraction of GCMs agreeing on the sign of the projected change. Values in "
        f"bold reach the {cfg.agreement_threshold:.0%} agreement threshold. The "
        "continuous agreement fraction is shown; no boolean field is interpolated.")

    figures.fig_temporal(
        cfg, tbias[tbias.period == "validation"], reg, ["raw", PRIMARY],
        "temporal_dependence",
        "Wet/dry sequencing, independent validation period",
        "Mean absolute bias in sequencing statistics that quantile mapping does "
        "not control directly. The dashed line marks a 10% bias. Frequency "
        "adaptation improves occurrence structure but a substantial residual "
        "remains, so spell-based indices (CDD, CWD) and multi-day accumulations "
        "(Rx5day) inherit the model's own temporal structure.")

    figures.fig_ensemble_spread(
        cfg, per_model.assign(method=PRIMARY), reg, "PRCPTOT",
        "ensemble_spread_prcptot",
        "Inter-model spread in projected annual precipitation change",
        "Distribution across the GCM ensemble of the projected change in PRCPTOT; "
        "red points are individual models.")

    if geom is not None:
        est = pd.read_csv(res / "ensemble_station.csv")
        est = est[est.method == PRIMARY]
        for idx_name in ("PRCPTOT", "Rx1day", "R95p"):
            figures.fig_spatial_maps(
                cfg, est, coords, geom, reg, idx_name,
                f"map_{idx_name.lower()}",
                f"Projected change in {idx_name} within the verified provincial "
                f"boundary",
                f"Multi-model median change in {idx_name} relative to each "
                f"model's own bias-corrected baseline, interpolated by inverse "
                f"distance weighting between the {len(coords)} gauges and "
                f"clipped to the verified Uttaradit ADM1 polygon. Hatching marks "
                f"areas where the continuous inter-model agreement fraction "
                f"falls below {cfg.agreement_threshold:.0%}; the agreement "
                f"fraction itself is interpolated, never a boolean flag. Black "
                f"dots are gauge locations.")

    reg.write_index()
    pd.DataFrame(reg.index).to_csv(out / "Paper1_CAPTIONS.csv", index=False)
    print(f"Paper 1: {len(reg.index)} figures, 6 main tables -> {out}")


if __name__ == "__main__":
    main()
