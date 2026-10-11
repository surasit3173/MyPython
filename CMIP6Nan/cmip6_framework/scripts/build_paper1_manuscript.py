#!/usr/bin/env python3
"""Paper 1 manuscript set: locked main-text tables/figures plus supplementary.

    python scripts/build_paper1_manuscript.py --config config/uttaradit.yaml

Scope is taken from output/results/raw_signal_check.csv, never assumed. Every
row of every future table carries a `usable_for_results` flag, so a horizon is
included or excluded on evidence rather than on a blanket rule.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from cmip6bc import figures                                    # noqa: E402
from cmip6bc.config import load_config                         # noqa: E402

PRIMARY = "qdm"
# Main text keeps a defensible minimum; everything else goes to supplementary.
MAIN_METRICS = ["wet_day_pct", "PRCPTOT", "SDII", "q95",
                "Rx1day", "Rx5day", "CDD", "CWD"]
SUPP_METRICS = ["q50", "q90", "q99", "R10mm", "R20mm", "R50mm", "R95p", "R99p",
                "mean_daily", "sd_daily", "sd_wet"]
# Single near-future window: one table of projected change covering both the
# precipitation characteristics and the extreme-rainfall indices.
PRECIP_IDX = ["PRCPTOT", "wet_day_pct", "SDII"]
INTENSITY_IDX = ["Rx1day", "Rx5day", "R20mm", "R50mm"]
TAIL_IDX = ["R95p", "R99p", "CDD", "CWD"]
DIAGNOSTIC_IDX = {"CDD", "CWD", "Rx5day"}
ALL_IDX = PRECIP_IDX + INTENSITY_IDX + TAIL_IDX
PRETTY = {"wet_day_pct": "Wet-day frequency", "PRCPTOT": "PRCPTOT",
          "SDII": "SDII", "Rx1day": "Rx1day", "Rx5day": "Rx5day",
          "R20mm": "R20mm", "R50mm": "R50mm", "R95p": "R95p", "R99p": "R99p",
          "CDD": "CDD", "CWD": "CWD"}


def _write(tables: dict, path: Path) -> None:
    with pd.ExcelWriter(path, engine="xlsxwriter") as w:
        hdr = w.book.add_format({"bold": True, "font_name": "Times New Roman",
                                 "font_size": 10, "bg_color": "#E8E8E8",
                                 "border": 1, "text_wrap": True,
                                 "valign": "vcenter"})
        cell = w.book.add_format({"font_name": "Times New Roman",
                                  "font_size": 10, "valign": "top"})
        for name, df in tables.items():
            df.to_excel(w, index=False, sheet_name=name[:31])
            ws = w.sheets[name[:31]]
            ws.freeze_panes(1, 0)
            ws.set_column(0, max(len(df.columns) - 1, 0), 17, cell)
            for j, c in enumerate(df.columns):
                ws.write(0, j, str(c), hdr)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--figure1", default=None,
                    help="externally produced study-area map to adopt as Fig. 1")
    a = ap.parse_args()
    cfg = load_config(a.config)
    res = cfg.path("output") / "results"
    out = cfg.out("paper1_manuscript")
    figures.init(cfg)
    reg = figures.Registry(out / "figures", "Paper1")

    perf = pd.read_csv(res / "performance.csv")
    perf["station"] = perf.station.astype(str)
    changes = pd.read_csv(res / "future_changes.csv")
    regional = pd.read_csv(res / "ensemble_regional.csv")
    ens_st = pd.read_csv(res / "ensemble_station.csv")
    gates = pd.read_csv(res / "acceptance_gates.csv")
    scope = pd.read_csv(res / "raw_signal_check.csv")
    homog = pd.read_csv(cfg.path("output") / "qc" / "station_homogeneity.csv")
    flags = pd.read_csv(cfg.path("output") / "qc" / "QC_flags.csv")
    tsum = pd.read_csv(res / "temporal_summary.csv")
    obs_m = pd.read_csv(res / "observed_metrics.csv")
    inv = pd.read_csv(res / "cmip6_inventory.csv")
    coords = pd.read_excel(next(Path(cfg.path("gis")).rglob("*coord*.xlsx")))
    coords.columns = [c.strip().lower() for c in coords.columns]
    coords["station"] = coords["station"].astype(str)

    usable = {(r.scenario, r.window): bool(r.usable_for_results)
              for r in scope.itertuples()}
    excluded = [f"{s.upper()}/{w}" for (s, w), u in usable.items() if not u]
    thr = cfg.agreement_threshold
    cal, val = cfg.period("calibration"), cfg.period("validation")
    stations = sorted(homog.station.astype(str))
    coords = coords[coords.station.isin(stations)]

    # ---------------------------------------------------------------- Table 1
    base = obs_m[obs_m.period == "calibration"].copy()
    base["station"] = base.station.astype(str)
    base = base.set_index("station")
    t1 = pd.DataFrame({
        "Station": stations,
        "Longitude (°E)": [round(float(coords.set_index("station").longitude[s]), 3)
                           for s in stations],
        "Latitude (°N)": [round(float(coords.set_index("station").latitude[s]), 3)
                          for s in stations],
        "Record": [f"{cal[0]}–{val[1]}" for _ in stations],
        "Mean annual rainfall (mm)": [round(float(base.PRCPTOT[s]), 0)
                                      for s in stations],
    })

    pm = flags[flags.classification == "probable_missing"].astype({"station": str})
    pmc = pm.groupby("station").size()
    s1 = t1.copy()
    s1["Wet days (%)"] = [round(float(base.wet_day_pct[s]), 1) for s in stations]
    s1["SDII (mm d⁻¹)"] = [round(float(base.SDII[s]), 2) for s in stations]
    s1["Station-months flagged probable-missing"] = [int(pmc.get(s, 0))
                                                     for s in stations]
    s1 = s1.merge(homog.astype({"station": str}).rename(
        columns={"station": "Station", "wet_pct_calibration": "Wet days, calib. (%)",
                 "wet_pct_validation": "Wet days, valid. (%)",
                 "ratio_val_over_cal": "Ratio valid./calib.",
                 "homogeneous": "Homogeneous"})[
        ["Station", "Wet days, calib. (%)", "Wet days, valid. (%)",
         "Ratio valid./calib.", "Homogeneous"]], on="Station", how="left")

    # ---------------------------------------------- Table 2: model inventory
    # Distinct daily series counts how many of the analysed gauges receive an
    # identical series, i.e. how many native grid cells actually serve the
    # province. It is computed here, never typed in.
    import hashlib
    from cmip6bc import io_data as _io
    files = _io.discover_raw(cfg.path("cmip6_raw"), cfg.scenarios)
    inst = {"ACCESS-ESM1-5": "CSIRO, Australia",
            "CESM2": "NCAR, USA",
            "CanESM5": "CCCma, Canada",
            "EC-Earth3": "EC-Earth Consortium, Europe",
            "FGOALS-g3": "IAP/LASG, China",
            "MIROC6": "MIROC Consortium, Japan",
            "MRI-ESM2-0": "MRI, Japan"}
    mrows = []
    for rf in sorted((f for f in files if f.scenario == "historical"),
                     key=lambda f: f.model):
        fr = _io.load_raw(rf, stations)
        uniq = len({hashlib.md5(fr[c].to_numpy(float).tobytes()).hexdigest()
                    for c in fr.columns})
        calrep = _io.calendar_report(fr)
        mrows.append({"Model": rf.model,
                      "Institution": inst.get(rf.model, "—"),
                      "Variant": rf.variant, "Grid": rf.grid,
                      "Calendar": "365-day" if "365" in calrep["calendar"]
                                  else "Standard",
                      f"Days ({cal[0]}\u2013{val[1]})": f"{calrep['n_days']:,}",
                      "Distinct series": uniq})
    t_models = pd.DataFrame(mrows)


    # ------------------------------------------------------------ Tables 2, 3
    def perf_tab(period, metrics, signed=True):
        sub = perf[perf.period == period]
        rows = []
        for m in ["raw", PRIMARY]:
            d = sub[sub.method == m]
            rec = {"Simulation": "Raw CMIP6" if m == "raw" else "QDM-corrected"}
            for k in metrics:
                c = f"{k}_bias_pct"
                if c not in d.columns:
                    continue
                rec[f"{k} |bias| (%)"] = round(float(d[c].abs().mean()), 2)
                if signed:
                    rec[f"{k} bias (%)"] = round(float(d[c].mean()), 2)
            rows.append(rec)
        return pd.DataFrame(rows)

    t2 = perf_tab("calibration", MAIN_METRICS, signed=False)
    t3 = perf_tab("validation", MAIN_METRICS, signed=False)
    s2 = perf_tab("calibration", MAIN_METRICS + SUPP_METRICS, signed=True)
    s3 = perf_tab("validation", MAIN_METRICS + SUPP_METRICS, signed=True)

    hom_ok = set(homog[homog.homogeneous].station.astype(str))
    rows = []
    for period in ("calibration", "validation"):
        for label, sel in (("Full network (13 gauges)", perf.station.notna()),
                           (f"Homogeneous only ({len(hom_ok)} gauges)",
                            perf.station.isin(hom_ok))):
            for m in ["raw", PRIMARY]:
                d = perf[(perf.period == period) & sel & (perf.method == m)]
                rec = {"Period": period, "Gauge subset": label,
                       "Simulation": "Raw CMIP6" if m == "raw" else "QDM-corrected"}
                for k in MAIN_METRICS:
                    c = f"{k}_bias_pct"
                    if c in d.columns:
                        rec[f"{k} |bias| (%)"] = round(float(d[c].abs().mean()), 2)
                rows.append(rec)
    s4 = pd.DataFrame(rows)

    # ----------------------------------------------------------- Table 4
    q = changes[changes.method == PRIMARY]
    per_model = q.groupby(["scenario", "window", "model", "index"],
                          as_index=False)["change_pct"].mean()
    thr = cfg.agreement_threshold
    win = list(cfg.future_windows)[0]
    wy = cfg.future_windows[win]

    def change_tab(indices):
        """Rows are indices and columns are scenarios. With a single future
        window this is the compact layout, and every median keeps its
        interquartile range and agreement fraction beside it."""
        scen = sorted(per_model.scenario.unique())
        rows = []
        for k in indices:
            rec = {"Index": PRETTY.get(k, k),
                   "Type": "diagnostic" if k in DIAGNOSTIC_IDX else "projection"}
            for sc in scen:
                v = per_model[(per_model.scenario == sc)
                              & (per_model["index"] == k)]["change_pct"].to_numpy(float)
                v = v[np.isfinite(v)]
                lbl = (sc.upper().replace("SSP245", "SSP2-4.5")
                                 .replace("SSP585", "SSP5-8.5"))
                if not len(v):
                    rec[f"{lbl} median (%)"] = np.nan
                    continue
                agr = max((v > 0).sum(), (v < 0).sum()) / len(v)
                rec[f"{lbl} median (%)"] = round(float(np.median(v)), 1)
                rec[f"{lbl} IQR (%)"] = (f"{np.percentile(v, 25):.1f} to "
                                         f"{np.percentile(v, 75):.1f}")
                rec[f"{lbl} agreement"] = round(agr, 2)
                rec[f"{lbl} robust"] = "yes" if agr >= thr else "no"
            rows.append(rec)
        return pd.DataFrame(rows)

    t4 = change_tab(ALL_IDX)
    s5 = q.round(3)
    s6 = tsum
    s7 = inv
    s8 = gates

    notes = pd.DataFrame([
        {"item": "Change definition",
         "note": "100 x (BC_future - BC_historical) / BC_historical, using the "
                 "same GCM and the same bias-correction method on both sides. "
                 "Observations are never the denominator."},
        {"item": "Baseline",
         "note": f"{cfg.period('baseline')[0]}–{cfg.period('baseline')[1]}, "
                 f"model-consistent"},
        {"item": "Calibration / validation",
         "note": f"parameters fitted on {cal[0]}–{cal[1]} and frozen; "
                 f"{val[0]}–{val[1]} is strictly out-of-sample"},
        {"item": "Agreement",
         "note": f"fraction of the {per_model.model.nunique()} GCMs sharing the "
                 f"majority sign; robust means >= {thr:.0%}"},
        {"item": "Future window",
         "note": "a single 30-year near-future period; every statistic is "
                 "recomputed from the daily bias-corrected series over these "
                 "years and is never an average of shorter windows"},
        {"item": "Excluded from interpretation",
         "note": ", ".join(excluded) if excluded else "none"},
        {"item": "Temporal indices",
         "note": "CDD, CWD and Rx5day depend on day ordering, which quantile "
                 "mapping does not alter. They are reported as diagnostics and "
                 "must not be described as corrected."},
        {"item": "Scope authority",
         "note": "FINAL_ACCEPTANCE_GATES.csv and INTERPRETATION_SCOPE.csv "
                 "govern what may be claimed"},
    ])

    _write({"Notes": notes, "Table1_stations": t1,
            "Table2_cmip6_models": t_models,
            "Table3_calibration": t2, "Table4_validation": t3,
            "Table5_near_future_change": t4},
           out / "Paper1_MAIN_Tables.xlsx")
    _write({"S1_stations_full": s1, "S2_calibration_full": s2,
            "S3_validation_full": s3, "S4_homogeneity_sensitivity": s4,
            "S5_station_level_changes": s5, "S6_temporal_dependence": s6,
            "S7_model_inventory": s7, "S8_acceptance_gates": s8},
           out / "Paper1_SUPPLEMENTARY_Tables.xlsx")
    for n, d in (("Table1", t1), ("Table2", t_models), ("Table3", t2),
                 ("Table4", t3), ("Table5", t4)):
        d.to_csv(out / f"Paper1_{n}.csv", index=False)

    # ------------------------------------------------------------- Figures
    ext = Path(a.figure1) if a.figure1 else None
    if ext and ext.exists():
        reg._n = 1
        for suf in (".png", ".pdf"):
            tgt = out / "figures" / f"Paper1_Figure_01_study_area{suf}"
            if suf == ext.suffix.lower():
                tgt.write_bytes(ext.read_bytes())
        reg.index.append({"figure": 1, "file": "Paper1_Figure_01_study_area",
                          "slug": "study_area",
                          "caption": f"Location of {cfg.area} province in "
                          f"Thailand (inset) and the {len(coords)}-gauge "
                          f"rain-gauge network used in this study, over "
                          f"terrain elevation. Provincial boundary shown in "
                          f"black."})
    else:
        b = sorted(Path(cfg.path("gis")).glob("*_adm1_verified.geojson"))
        geom = json.loads(b[0].read_text())["features"][0]["geometry"]
        rings = [np.asarray(r, float) for r in geom["coordinates"]]
        figures.fig_study_area(cfg, coords, [(r[:, 0], r[:, 1]) for r in rings],
                               cfg.area, reg)

    figures.fig_hist_validation(
        cfg, perf[perf.period == "calibration"], reg,
        f"the calibration period {cal[0]}–{cal[1]}", "calibration",
        ["raw", PRIMARY], keys=MAIN_METRICS, marginal_n=5,
        note=f"MAB averaged across {len(stations)} gauges \u00d7 "
             f"{per_model.model.nunique()} GCMs", ylim_share=True)
    figures.fig_hist_validation(
        cfg, perf[perf.period == "validation"], reg,
        f"the independent validation period {val[0]}–{val[1]}", "validation",
        ["raw", PRIMARY], keys=MAIN_METRICS, marginal_n=5,
        note=f"MAB averaged across {len(stations)} gauges \u00d7 "
             f"{per_model.model.nunique()} GCMs")

    r = regional[regional.method == PRIMARY]
    r = r[[usable.get((sc, w), True) for sc, w in zip(r.scenario, r.window)]]

    figures.fig_scenario_change(
        cfg, r, reg,
        [("", PRECIP_IDX + ["Rx1day", "Rx5day"], False)],
        "near_future_precipitation",
        f"Projected change in precipitation characteristics, {wy[0]}\u2013{wy[1]}",
        f"Multi-model median change (bars) and inter-model interquartile range "
        f"(whiskers) in precipitation characteristics for {wy[0]}\u2013{wy[1]} "
        f"relative to each model's own bias-corrected baseline "
        f"({cfg.period('baseline')[0]}\u2013{cfg.period('baseline')[1]}). The "
        f"whiskers show inter-model spread, not a confidence interval. The number "
        f"beneath each bar is the inter-model agreement fraction; bold marks "
        f"agreement of at least {thr:.0%}, and those bars are filled solid.")

    figures.fig_scenario_change(
        cfg, r, reg,
        [("(a) intensity and threshold indices", INTENSITY_IDX, False),
         ("(b) tail and persistence indices", TAIL_IDX, False)],
        "near_future_extremes",
        f"Projected change in extreme-rainfall indices, {wy[0]}\u2013{wy[1]}",
        "As the previous figure, for the extreme-rainfall indices: "
        "(a) intensity and threshold indices and (b) tail and persistence "
        "indices. CDD, CWD and Rx5day depend on the ordering of wet and dry "
        "days, which quantile mapping does not correct, and are reported as "
        "diagnostics rather than as corrected projections.")

    est = ens_st[ens_st.method == PRIMARY]
    est = est[[usable.get((sc, w), True) for sc, w in zip(est.scenario, est.window)]]
    b = sorted(Path(cfg.path("gis")).glob("*_adm1_verified.geojson"))
    geom = json.loads(b[0].read_text())["features"][0]["geometry"]
    figures.fig_idw_with_stations(
        cfg, est, coords, geom, reg, "PRCPTOT", "near_future_map",
        f"Gauge-level projected change in annual precipitation and inter-model "
        f"agreement, {wy[0]}\u2013{wy[1]}",
        f"Ensemble median change in PRCPTOT for {wy[0]}\u2013{wy[1]} relative to "
        f"each model's own bias-corrected baseline. The shaded surface is an "
        f"inverse-distance-weighted interpolation between the {len(coords)} "
        f"gauges, clipped to the verified provincial boundary; the gauges "
        f"themselves are drawn on top, sized by the inter-model agreement "
        f"fraction, with filled symbols for agreement of at least {thr:.0%} and "
        f"open symbols below it.")

    reg.write_index()
    pd.DataFrame(reg.index).to_csv(out / "Paper1_CAPTIONS.csv", index=False)
    print(f"Paper 1 manuscript set: {len(reg.index)} main figures, "
          f"5 main tables, 8 supplementary sheets -> {out}")
    print(f"excluded from interpretation: {excluded or 'none'}")


if __name__ == "__main__":
    main()
