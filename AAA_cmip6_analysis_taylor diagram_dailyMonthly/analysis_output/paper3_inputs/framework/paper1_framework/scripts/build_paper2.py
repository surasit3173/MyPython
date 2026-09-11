#!/usr/bin/env python3
"""Paper 2 deliverables — QM/EQM vs DetQM vs QDM, bias removal and
climate-signal preservation.

    python scripts/build_paper2.py --config config/uttaradit.yaml
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from cmip6bc import analysis, figures                          # noqa: E402
from cmip6bc.config import load_config                         # noqa: E402

METHODS = ["qm", "detqm", "qdm"]
LABEL = {"raw": "Raw GCM", "qm": "QM/EQM", "detqm": "DetQM", "qdm": "QDM"}
STATS = ["PRCPTOT", "SDII", "wet_day_pct", "q50", "q90", "q95", "q99"]
EXTREMES = ["Rx1day", "Rx5day", "R20mm", "R50mm", "R95p", "R99p", "CDD", "CWD"]
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
    out = cfg.out("paper2")
    figures.init(cfg)
    reg = figures.Registry(out / "figures", "Paper2")

    perf = pd.read_csv(res / "performance.csv")
    changes = pd.read_csv(res / "future_changes.csv")
    sig = pd.read_csv(res / "signal_preservation.csv")
    spread = pd.read_csv(res / "variance_decomposition.csv")
    tsum = pd.read_csv(res / "temporal_summary.csv")
    tbias = pd.read_csv(res / "temporal_bias.csv")
    fitd = pd.read_csv(res / "bc_fit_diagnostics.csv")
    appd = pd.read_csv(res / "bc_apply_diagnostics.csv")
    gates = pd.read_csv(res / "acceptance_gates.csv")

    cal, val = cfg.period("calibration"), cfg.period("validation")

    # ------------------------------------------------------------ Table 1
    notes6 = pd.DataFrame([
        {"item": "Model form",
         "note": "total SS = GCM main effect + BC-method main effect + residual. "
                 "The residual term CONTAINS the GCM x method interaction."},
        {"item": "What this is not",
         "note": "this is a main-effect sum-of-squares partition, NOT a full "
                 "variance-component analysis with estimated variance "
                 "components"},
        {"item": "Correct reading",
         "note": "the additive main effect of method was small at the aggregate "
                 "level; method-specific differences remain evident for selected "
                 "upper-tail and threshold-based extreme indices (Tables 4-5)"},
        {"item": "Incorrect reading",
         "note": "do NOT conclude that bias-correction method has little "
                 "influence"},
    ])

    t1 = pd.DataFrame([
        {"Element": "Study area", "Specification": cfg.area},
        {"Element": "Gauges", "Specification": int(fitd.station.nunique())},
        {"Element": "GCMs", "Specification": ", ".join(sorted(fitd.model.unique()))},
        {"Element": "Scenarios", "Specification": ", ".join(s.upper() for s in cfg.scenarios)},
        {"Element": "Calibration", "Specification": f"{cal[0]}–{cal[1]} (parameters fitted, then frozen)"},
        {"Element": "Independent validation", "Specification": f"{val[0]}–{val[1]} (never refitted)"},
        {"Element": "Future baseline", "Specification": f"{cfg.period('baseline')[0]}–{cfg.period('baseline')[1]}, model- and method-consistent"},
        {"Element": "Future horizons", "Specification": "; ".join(f"{k} {v[0]}–{v[1]}" for k, v in cfg.future_windows.items())},
        {"Element": "Wet-day threshold", "Specification": f"{cfg.wet_thr} mm d⁻¹, identical for all methods"},
        {"Element": "Occurrence model", "Specification": "frequency adaptation: model wet-day threshold set so the model wet-day frequency matches the observed calibration frequency"},
        {"Element": "Quantile estimation", "Specification": f"empirical CDF, {cfg.bc['plotting_position']} plotting positions, linear interpolation"},
        {"Element": "Extrapolation", "Specification": "constant multiplicative correction ratio beyond the calibration range; no clipping"},
        {"Element": "QM/EQM", "Specification": "BC(x)=F⁻¹_obs,cal(F_mod,cal(x))"},
        {"Element": "DetQM", "Specification": "mean climate signal removed, quantile-mapped, then restored (Cannon et al., 2015)"},
        {"Element": "QDM", "Specification": "BC(p)=F⁻¹_obs,cal(p)·[x/F⁻¹_mod,cal(p)] (Cannon et al., 2015)"},
        {"Element": "Mean extrapolated values", "Specification": f"{appd.pct_extrapolated.mean():.2f}% of wet days"},
    ])

    # ------------------------------------------------------------ Table 2 & 3
    def perf_table(period: str) -> pd.DataFrame:
        sub = perf[perf.period == period]
        rows = []
        for m in ["raw"] + METHODS:
            s = sub[sub.method == m]
            if not len(s):
                continue
            rec = {"Method": LABEL[m]}
            for k in METRIC_ORDER:
                c = f"{k}_bias_pct"
                if c in s.columns:
                    rec[f"{k} bias (%)"] = round(float(s[c].mean()), 2)
                    rec[f"{k} |bias| (%)"] = round(float(s[c].abs().mean()), 2)
            rows.append(rec)
        return pd.DataFrame(rows)

    t2, t3 = perf_table("calibration"), perf_table("validation")

    # ------------------------------------------------------------ Table 4 & 5
    def pe_table(stats) -> pd.DataFrame:
        rows = []
        for m in METHODS:
            s = sig[sig.method == m]
            rec = {"Method": LABEL[m]}
            for k in stats:
                v = s[s["index"] == k]["PE_pct"].to_numpy(float)
                v = v[np.isfinite(v)]
                if not len(v):
                    continue
                rec[f"{k} median PE (%)"] = round(float(np.median(v)), 2)
                rec[f"{k} |PE| (%)"] = round(float(np.median(np.abs(v))), 2)
            rows.append(rec)
        return pd.DataFrame(rows)

    t4, t5 = pe_table(STATS), pe_table(EXTREMES)

    # ------------------------------------------------------------ Table 6
    # Formal two-way sum-of-squares decomposition; shares sum to 100 by
    # construction, unlike a ratio of standard deviations.
    # Column names state the decomposition model so it cannot be mistaken for a
    # full variance-component analysis.
    t6 = (spread[["scenario", "window", "index", "n", "model_share_pct",
                  "method_share_pct", "residual_share_pct"]]
          .rename(columns={
              "scenario": "Scenario", "window": "Horizon", "index": "Index",
              "n": "N cells (GCM x station)",
              "model_share_pct": "GCM main effect (% of total SS)",
              "method_share_pct": "BC-method main effect (% of total SS)",
              "residual_share_pct":
                  "Residual incl. GCM x method interaction (% of total SS)"})
          .round(2))
    t6.insert(0, "Decomposition",
              "GCM main effect + BC-method main effect + residual "
              "(including interaction)")
    t7 = tsum.rename(columns={"method": "Method"})

    _write({"Table1_design": t1, "Table2_calibration": t2, "Table3_validation": t3,
            "Table4_signal_pres_stats": t4, "Table5_signal_pres_extremes": t5,
            "Table6_variance_decomposition": t6,
            "Table6_notes_decomposition": notes6,
            "Table7_temporal_dependence": t7,
            "S1_fit_diagnostics": fitd.round(4),
            "S2_apply_diagnostics": appd.round(4),
            "S3_signal_preservation_full": sig.round(3),
            "S4_acceptance_gates": gates},
           out / "Paper2_Tables.xlsx")
    for n, d in [("Table2_calibration", t2), ("Table3_validation", t3),
                 ("Table4_signal_pres_stats", t4),
                 ("Table5_signal_pres_extremes", t5),
                 ("Table6_variance_decomposition", t6),
                 ("Table7_temporal_dependence", t7)]:
        d.to_csv(out / f"Paper2_{n}.csv", index=False)

    # ------------------------------------------------------------ Figures
    figures.fig_hist_validation(
        cfg, perf[perf.period == "calibration"], reg,
        f"the calibration period {cal[0]}–{cal[1]}", "calibration_comparison",
        ["raw"] + METHODS)
    figures.fig_hist_validation(
        cfg, perf[perf.period == "validation"], reg,
        f"the independent validation period {val[0]}–{val[1]}",
        "validation_comparison", ["raw"] + METHODS)
    figures.fig_wetday_intensity(
        cfg, perf[perf.period == "validation"], reg, "wetday_intensity",
        "Wet-day occurrence and intensity, independent validation period",
        "Distribution across gauges and GCMs of the out-of-sample bias in wet-day "
        "frequency (left) and simple daily intensity index (right).")
    figures.fig_signal_preservation(
        cfg, sig.rename(columns={"index": "statistic"}), reg, STATS,
        "signal_preservation_stats",
        "Preservation of the raw model climate signal, distribution statistics",
        "Signal-preservation error PE = 100·(S_BC − S_mod)/S_mod, where S is the "
        "ratio of a future statistic to its baseline value. Bars are medians, "
        "whiskers the interquartile range across gauges, GCMs, scenarios and horizons.")
    figures.fig_signal_preservation(
        cfg, sig.rename(columns={"index": "statistic"}), reg, EXTREMES,
        "signal_preservation_extremes",
        "Preservation of the raw model climate signal, extreme-rainfall indices",
        "As the previous figure, for the extreme-rainfall indices.")
    figures.fig_temporal(
        cfg, tbias[tbias.period == "validation"], reg, ["raw"] + METHODS,
        "temporal_dependence_methods",
        "Wet/dry sequencing by bias-correction method, validation period",
        "Mean absolute bias in sequencing statistics. All three methods share the "
        "same occurrence model, so they are nearly indistinguishable here: "
        "quantile mapping transforms magnitudes but does not reorder days, and "
        "the residual sequencing error is a property of the model, not of the "
        "method.")
    figures.fig_variance_decomposition(
        cfg, spread, reg, "variance_decomposition",
        "Sources of variance in the projected change",
        "Two-way sum-of-squares decomposition of the projected change into a GCM "
        "main effect, a bias-correction-method main effect and an interaction/"
        "residual term. Shares sum to 100% by construction.")

    reg.write_index()
    pd.DataFrame(reg.index).to_csv(out / "Paper2_CAPTIONS.csv", index=False)
    print(f"Paper 2: {len(reg.index)} figures, 6 main tables -> {out}")


if __name__ == "__main__":
    main()
