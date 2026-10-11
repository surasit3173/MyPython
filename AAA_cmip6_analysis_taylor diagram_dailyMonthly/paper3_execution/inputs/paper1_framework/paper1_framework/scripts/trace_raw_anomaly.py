#!/usr/bin/env python3
"""Trace a raw-input anomaly flagged by Gate H back towards its source.

    python scripts/trace_raw_anomaly.py --config config/uttaradit.yaml

The source NetCDF is not part of this repository, so this script establishes
everything that CAN be determined from the delivered CSV extractions and states
precisely what remains to be checked upstream.  It answers, per model:

  * is the decline gradual or a step change?
  * is there a discontinuity at the historical -> scenario join?
  * is it driven by wet-day occurrence or by intensity?
  * which season carries it?
  * do all gauges move together (one grid cell) or independently?
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from cmip6bc import io_data                                    # noqa: E402
from cmip6bc.config import load_config                         # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--scenario", default="ssp585")
    ap.add_argument("--window", default=None,
                    help="future window to trace; default is the last one in the config")
    a = ap.parse_args()
    cfg = load_config(a.config)
    out = cfg.out("results")
    wet = cfg.wet_thr
    windows = cfg.future_windows
    win = a.window or list(windows)[-1]
    if win not in windows:
        sys.exit(f"window {win!r} is not in the configuration; available: "
                 f"{list(windows)}")
    y0, y1 = windows[win]
    b0, b1 = cfg.period("baseline")

    stations = io_data.resolve_stations(cfg.path("observed"), cfg.path("gis"),
                                        cfg.raw["area"].get("stations"))
    files = io_data.discover_raw(cfg.path("cmip6_raw"), cfg.scenarios)
    hist = {f.model: f for f in files if f.scenario == "historical"}
    scen = {f.model: f for f in files if f.scenario == a.scenario}

    ann_rows, diag_rows, season_rows = [], [], []
    for model in sorted(set(hist) & set(scen)):
        h = io_data.load_raw(hist[model], stations)
        s = io_data.load_raw(scen[model], stations)
        full = pd.concat([h, s]).sort_index()
        reg = full.mean(axis=1)                     # unweighted gauge mean

        ann = reg.groupby(reg.index.year).agg(
            total=lambda v: float(v[v >= wet].sum()),
            wet_days=lambda v: int((v >= wet).sum()),
            sdii=lambda v: float(v[v >= wet].mean()) if (v >= wet).any() else np.nan,
            rx1=lambda v: float(v.max()))
        ann["model"] = model
        ann_rows.append(ann.reset_index().rename(columns={"index": "year"}))

        def seg(y_a, y_b, col):
            v = ann.loc[y_a:y_b, col]
            return float(v.mean())

        base_tot = seg(b0, b1, "total")
        late_tot = seg(y0, y1, "total")
        # continuity across the historical -> scenario join
        j_before = seg(2005, 2014, "total")
        j_after = seg(2015, 2024, "total")
        # step vs gradual: compare consecutive 20-yr blocks
        blocks = {f"{k}-{k+19}": seg(k, k + 19, "total")
                  for k in range(2021, 2100, 20)}
        d = np.diff(list(blocks.values()))
        biggest_step = float(np.max(np.abs(d))) if len(d) else np.nan
        total_drop = list(blocks.values())[-1] - list(blocks.values())[0]

        # attribution: occurrence vs intensity
        wd_chg = 100 * (seg(y0, y1, "wet_days") / seg(b0, b1, "wet_days") - 1)
        si_chg = 100 * (seg(y0, y1, "sdii") / seg(b0, b1, "sdii") - 1)

        # cross-gauge coherence: identical series would mean one grid cell
        late = full[(full.index.year >= y0) & (full.index.year <= y1)]
        ann_st = late.groupby(late.index.year).sum()
        corr = ann_st.corr().to_numpy()
        off = corr[~np.eye(len(stations), dtype=bool)]

        diag_rows.append({
            "model": model,
            "baseline_mm": round(base_tot, 1), "late_mm": round(late_tot, 1),
            "change_pct": round(100 * (late_tot / base_tot - 1), 1),
            "join_2005_2014_mm": round(j_before, 1),
            "join_2015_2024_mm": round(j_after, 1),
            "join_discontinuity_pct": round(100 * (j_after / j_before - 1), 1),
            **{f"blk_{k}": round(v, 1) for k, v in blocks.items()},
            "largest_20yr_step_mm": round(biggest_step, 1),
            "total_drift_mm": round(total_drop, 1),
            "step_dominates": bool(np.isfinite(biggest_step)
                                   and abs(total_drop) > 0
                                   and biggest_step / abs(total_drop) > 0.7),
            "wet_day_change_pct": round(wd_chg, 1),
            "intensity_change_pct": round(si_chg, 1),
            "attribution": ("occurrence" if abs(wd_chg) > 2 * abs(si_chg)
                            else "intensity" if abs(si_chg) > 2 * abs(wd_chg)
                            else "both"),
            "mean_intergauge_corr": round(float(off.mean()), 3),
            "gauges_effectively_identical": bool(off.mean() > 0.98),
        })

        for name, months in (("wet_MJJASO", [5, 6, 7, 8, 9, 10]),
                             ("dry_NDJFMA", [11, 12, 1, 2, 3, 4])):
            m = reg[reg.index.month.isin(months)]
            bb = m[(m.index.year >= b0) & (m.index.year <= b1)]
            ll = m[(m.index.year >= y0) & (m.index.year <= y1)]
            bv = float(bb[bb >= wet].sum()) / (b1 - b0 + 1)
            lv = float(ll[ll >= wet].sum()) / (y1 - y0 + 1)
            season_rows.append({"model": model, "season": name,
                                "baseline_mm": round(bv, 1), "late_mm": round(lv, 1),
                                "change_pct": round(100 * (lv / bv - 1), 1)})

    diag = pd.DataFrame(diag_rows)
    ann = pd.concat(ann_rows, ignore_index=True)
    seas = pd.DataFrame(season_rows)
    diag.to_csv(out / f"raw_trace_{a.scenario}_{win}.csv", index=False)
    ann.to_csv(out / f"raw_annual_series_{a.scenario}.csv", index=False)
    seas.to_csv(out / f"raw_trace_seasonal_{a.scenario}.csv", index=False)

    checklist = pd.DataFrame([
        {"step": "1. source NetCDF", "determinable_here": "NO",
         "finding": "not supplied", "action": "record filename, tracking_id, "
         "variant_label and the CMIP6 DRS path for every model"},
        {"step": "2. grid/station extraction", "determinable_here": "PARTIAL",
         "finding": f"mean inter-gauge correlation "
                    f"{diag.mean_intergauge_corr.mean():.3f}; identical series in "
                    f"{int(diag.gauges_effectively_identical.sum())}/{len(diag)} models",
         "action": "confirm whether each gauge draws its own grid cell or all "
                   "share one; record the interpolation method"},
        {"step": "3. units", "determinable_here": "YES",
         "finding": "implied annual totals are consistent with mm/day "
                    "(unit_check passed in cmip6_inventory.csv)",
         "action": "confirm the x86400 conversion happened once and only once"},
        {"step": "4. calendar", "determinable_here": "YES",
         "finding": "noleap and Gregorian both present; detected per model",
         "action": "confirm the extraction did not drop or duplicate days when "
                   "converting a noleap axis"},
        {"step": "5. temporal aggregation / concatenation",
         "determinable_here": "YES",
         "finding": f"historical->scenario join discontinuity ranges "
                    f"{diag.join_discontinuity_pct.min():.1f}% to "
                    f"{diag.join_discontinuity_pct.max():.1f}%; step-dominated "
                    f"decline in {int(diag.step_dominates.sum())}/{len(diag)} models",
         "action": "confirm the historical and scenario files come from the same "
                   "variant and were concatenated without overlap or gap"},
    ])
    checklist.to_csv(out / f"raw_trace_checklist_{a.scenario}.csv", index=False)

    pd.set_option("display.width", 250)
    print(f"\n=== RAW TRACE: {a.scenario} {win} ({y0}-{y1}) vs baseline "
          f"{b0}-{b1} ===\n")
    print(diag[["model", "baseline_mm", "late_mm", "change_pct",
                "join_discontinuity_pct", "largest_20yr_step_mm",
                "step_dominates", "wet_day_change_pct", "intensity_change_pct",
                "attribution", "mean_intergauge_corr"]].to_string(index=False))
    print("\n--- 20-year blocks (regional mean annual total, mm) ---")
    print(diag[["model"] + [c for c in diag.columns
                            if c.startswith("blk_")]].to_string(index=False))
    print("\n--- seasonal attribution ---")
    print(seas.pivot_table(index="model", columns="season",
                           values="change_pct").to_string())
    print("\n--- upstream checklist ---")
    print(checklist[["step", "determinable_here", "finding"]].to_string(index=False))


if __name__ == "__main__":
    main()
