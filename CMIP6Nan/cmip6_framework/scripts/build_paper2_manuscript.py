#!/usr/bin/env python3
"""Paper 2: comparative evaluation of QM/EQM, DetQM and QDM.

    python scripts/build_paper2_manuscript.py --config config/uttaradit.yaml

Reads only the master result database written by run_pipeline.py, so the three
methods are guaranteed to share observations, station QC, station mapping,
calibration and validation periods, wet-day convention, percentile reference,
index definitions, future baseline and ensemble aggregation. Only the
bias-correction transformation differs.
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
ALL_SIM = ["raw"] + METHODS
LABEL = {"raw": "Raw CMIP6", "qm": "QM/EQM", "detqm": "DetQM", "qdm": "QDM"}
SCEN = {"ssp245": "SSP2-4.5", "ssp585": "SSP5-8.5"}

BULK = ["wet_day_pct", "PRCPTOT", "SDII"]
QUANT = ["q50", "q90", "q95", "q99"]
DAILY_EXT = ["Rx1day", "Rx5day"]
THRESH_EXT = ["R10mm", "R20mm", "R50mm"]
TAIL_EXT = ["R95p", "R99p"]
TEMPORAL = ["CDD", "CWD"]
# Order matters for the figures: every marginal / pointwise statistic first,
# then the sequence-dependent block, so the divider separates two contiguous
# groups rather than cutting through them.
MARGINAL_SET = BULK + QUANT + ["Rx1day"] + THRESH_EXT + TAIL_EXT
SEQ_SET = ["Rx5day"] + TEMPORAL
PERF_SET = MARGINAL_SET + SEQ_SET
# Indices whose value depends on the ordering of wet and dry days. No marginal
# quantile method reconstructs these; they stay diagnostic throughout.
SEQUENCE_DEPENDENT = {"Rx5day", "CDD", "CWD"}
# How each index is constructed, which is what governs whether preserving a
# quantile signal implies preserving the index.
INDEX_TYPE = {
    "wet_day_pct": "occurrence", "PRCPTOT": "accumulation", "SDII": "intensity",
    "q50": "direct quantile", "q90": "direct quantile",
    "q95": "direct quantile", "q99": "direct quantile",
    "Rx1day": "derived extreme",
    "R10mm": "derived threshold", "R20mm": "derived threshold",
    "R50mm": "derived threshold",
    "R95p": "derived tail", "R99p": "derived tail",
    "Rx5day": "sequence-dependent", "CDD": "sequence-dependent",
    "CWD": "sequence-dependent",
}

PRETTY = {"wet_day_pct": "Wet days", "PRCPTOT": "PRCPTOT", "SDII": "SDII",
          "q50": "q50", "q90": "q90", "q95": "q95", "q99": "q99",
          "Rx1day": "Rx1day", "Rx5day": "Rx5day", "R10mm": "R10mm",
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


def mab_table(perf: pd.DataFrame, period: str, indices) -> pd.DataFrame:
    sub = perf[perf.period == period]
    rows = []
    for k in indices:
        col = f"{k}_bias_pct"
        if col not in sub.columns:
            continue
        rec = {"Index": PRETTY.get(k, k),
               "Type": "sequence-dependent" if k in SEQUENCE_DEPENDENT
                       else "marginal"}
        for m in ALL_SIM:
            d = sub[sub.method == m]
            rec[LABEL[m]] = round(float(d[col].abs().mean()), 2)
        rows.append(rec)
    return pd.DataFrame(rows)


def pe_frame(sig, indices, scenarios):
    """Canonical long-format summary; every main-table cell resolves to a row."""
    return analysis.ensemble_frame(sig, "PE_pct", indices, METHODS, scenarios)


def pe_main(frame, indices, scenarios) -> pd.DataFrame:
    """Main-text layout: one row per index and scenario, one column per method.

    Scenario is a row rather than a column group so that each cell holds
    "median [IQR]" on a single line; the earlier column-group layout forced
    three-line cells that were unreadable at journal column width.
    """
    rows = []
    for k in indices:
        for sc in scenarios:
            rec = {"Index": PRETTY.get(k, k), "Type": INDEX_TYPE.get(k, ""),
                   "Scenario": SCEN[sc]}
            n = None
            for m in METHODS:
                r = frame[(frame["index"] == k) & (frame.method == m)
                          & (frame.scenario == sc)]
                if not len(r) or not np.isfinite(r["median"].iloc[0]):
                    rec[LABEL[m]] = "\u2014"
                    continue
                r = r.iloc[0]
                rec[LABEL[m]] = (f"{r['median']:+.2f} "
                                 f"[{r['q25']:+.2f}, {r['q75']:+.2f}]")
                n = int(r["n_models"])
            rec["GCMs"] = n if n is not None else 0
            rows.append(rec)
    return pd.DataFrame(rows)


def pe_supplement(frame) -> pd.DataFrame:
    """Every summary statistic of the same estimator, for the supplement."""
    d = frame.copy()
    d["scenario"] = d.scenario.map(SCEN)
    d["method"] = d.method.map(LABEL)
    d["index"] = d["index"].map(lambda k: PRETTY.get(k, k))
    return d[["scenario", "index", "method", "n_models", "gauges_min",
              "gauges_max", "median", "q25", "q75", "mean", "sd", "min", "max",
              "estimator"]].round(3)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--figure1", default=None)
    ap.add_argument("--journal", default="apst", choices=["apst", "aer"],
                    help="target journal; sets figure width and lettering")
    a = ap.parse_args()
    cfg = load_config(a.config)
    res = cfg.path("output") / "results"
    out = cfg.out("paper2_manuscript" if a.journal == "apst"
                  else f"paper2_{a.journal}")
    figures.init(cfg, a.journal)
    reg = figures.Registry(out / "figures", "Paper2")

    perf = pd.read_csv(res / "performance.csv")
    sig = pd.read_csv(res / "signal_preservation.csv")
    tbias = pd.read_csv(res / "temporal_bias.csv")
    tsum = pd.read_csv(res / "temporal_summary.csv")
    vdec = pd.read_csv(res / "variance_decomposition.csv")
    fitd = pd.read_csv(res / "bc_fit_diagnostics.csv")
    appd = pd.read_csv(res / "bc_apply_diagnostics.csv")
    inv = pd.read_csv(res / "cmip6_inventory.csv")
    gates = pd.read_csv(res / "acceptance_gates.csv")
    coords = pd.read_excel(next(Path(cfg.path("gis")).rglob("*coord*.xlsx")))
    coords.columns = [c.strip().lower() for c in coords.columns]
    coords["station"] = coords["station"].astype(str)

    cal, val = cfg.period("calibration"), cfg.period("validation")
    base = cfg.period("baseline")
    win = list(cfg.future_windows)[0]
    wy = cfg.future_windows[win]
    scen = sorted(sig.scenario.unique())
    stations = sorted(perf.station.astype(str).unique())
    coords = coords[coords.station.isin(stations)]

    # ------------------------------------------------------------ Table 1
    t1 = pd.DataFrame([
        {"Method": "QM/EQM",
         "Core purpose": "Historical bias correction",
         "Distribution treatment": "Empirical marginal quantile mapping onto the "
                                   "observed calibration distribution",
         "Climate-signal property": "Not explicitly preserved",
         "Temporal reconstruction": "No"},
        {"Method": "DetQM",
         "Core purpose": "Bias correction with mean-signal preservation",
         "Distribution treatment": "Target-period wet-day mean removed "
                                   "multiplicatively, quantile-mapped, then restored",
         "Climate-signal property": "Mean-signal oriented",
         "Temporal reconstruction": "No"},
        {"Method": "QDM",
         "Core purpose": "Bias correction with quantile-signal preservation",
         "Distribution treatment": "Observed calibration quantile multiplied by the "
                                   "model's own quantile-level change ratio",
         "Climate-signal property": "Quantile-signal oriented",
         "Temporal reconstruction": "No"},
    ])
    settings = pd.DataFrame([
        {"Setting": "Wet-day threshold", "Value": f"{cfg.wet_thr} mm d\u207b\u00b9, identical for all methods"},
        {"Setting": "Zero-rain treatment", "Value": "days at or below the frequency-adapted model threshold are set to zero; observed zeros are never imputed"},
        {"Setting": "Frequency adaptation", "Value": "model wet-day threshold raised until the model wet-day frequency over the calibration period matches the observed frequency, fitted separately for each gauge-model pair"},
        {"Setting": "Empirical CDF", "Value": "non-parametric, sorted wet-day sample"},
        {"Setting": "Plotting positions", "Value": f"{cfg.bc['plotting_position']}, (i \u2212 0.5)/n"},
        {"Setting": "Interpolation", "Value": "linear within the calibration quantile range"},
        {"Setting": "Extrapolation", "Value": "QM and DetQM hold the multiplicative correction ratio of the nearest calibration quantile; QDM applies the model's own change ratio, which extends naturally beyond the range. No value is clipped."},
        {"Setting": "Calibration period", "Value": f"{cal[0]}\u2013{cal[1]}, parameters frozen thereafter"},
        {"Setting": "Independent validation", "Value": f"{val[0]}\u2013{val[1]}, no refitting"},
        {"Setting": "Future baseline", "Value": f"{base[0]}\u2013{base[1]}, same model and same method as the future series"},
        {"Setting": "Future period", "Value": f"{wy[0]}\u2013{wy[1]}, recomputed from the daily corrected series"},
        {"Setting": "Minimum wet days to fit", "Value": str(cfg.bc["min_wet_days"])},
        {"Setting": "Mean wet days extrapolated", "Value": f"{appd.pct_extrapolated.mean():.2f}% (maximum {appd.pct_extrapolated.max():.1f}% for one gauge-model pair)"},
    ])

    # --------------------------------------------------------- Tables 2, 3
    t2 = mab_table(perf, "calibration", PERF_SET)
    t3 = mab_table(perf, "validation", PERF_SET)

    # --------------------------------------------------------- Tables 4, 5
    # One estimator for every cell: gauge mean within a GCM, then the median
    # across GCMs, separately per scenario. The long frame below is the source
    # of truth that the tables, the figures and the claim audit all read.
    IDX4 = BULK + QUANT
    IDX5 = ["Rx1day"] + THRESH_EXT + TAIL_EXT + SEQ_SET
    pe_all = pe_frame(sig, IDX4 + IDX5, scen)
    pe_all.to_csv(out / "paper2_pe_summary.csv", index=False)
    t4 = pe_main(pe_all, IDX4, scen)
    t5 = pe_main(pe_all, IDX5, scen)
    s_pe = pe_supplement(pe_all)

    # ------------------------------------------------------------ Table 6
    # Scenario-specific; never averaged across forcing pathways.
    t6 = (vdec[vdec["index"].isin(PERF_SET)]
          .assign(Scenario=lambda d: d.scenario.map(SCEN),
                  Index=lambda d: d["index"])
          .sort_values(["Scenario", "Index"])
          [["Scenario", "Index", "n", "n_models", "model_share_pct",
            "method_share_pct", "residual_share_pct"]]
          .round(1)
          .rename(columns={
              "n": "N cells", "n_models": "GCMs",
              "model_share_pct": "GCM main effect (% of SS)",
              "method_share_pct": "BC-method main effect (% of SS)",
              "residual_share_pct": "Residual (% of SS)"}))

    # --------------------------------------------------- paired differences
    # Paired at model level, matching the reported estimator, and descriptive
    # only: seven models cannot support an inferential claim about method
    # differences, so no test is attached.
    rows = []
    for sc in scen:
        for k in IDX4 + IDX5:
            ref = analysis.model_values(sig, "PE_pct", index=k, method="qm",
                                        scenario=sc)
            rec = {"Scenario": SCEN[sc], "Index": PRETTY.get(k, k)}
            for m in ("detqm", "qdm"):
                other = analysis.model_values(sig, "PE_pct", index=k, method=m,
                                              scenario=sc)
                d = (other - ref).dropna()
                rec[f"{LABEL[m]} \u2212 QM/EQM median (%)"] = (
                    round(float(d.median()), 2) if len(d) else np.nan)
                rec["n paired GCMs"] = int(len(d))
            rows.append(rec)
    paired = pd.DataFrame(rows)

    # ---------------------------------------------------- machine-readable
    mab_long = []
    for period in ("calibration", "validation"):
        d = perf[perf.period == period]
        for k in PERF_SET:
            col = f"{k}_bias_pct"
            if col not in d.columns:
                continue
            for m in ALL_SIM:
                mab_long.append({"period": period, "method": m, "index": k,
                                 "MAB_pct": round(float(d[d.method == m][col].abs().mean()), 4)})
    pd.DataFrame(mab_long).to_csv(out / "paper2_mab.csv", index=False)
    sig.to_csv(out / "paper2_signal_preservation.csv", index=False)
    tbias.to_csv(out / "paper2_temporal_dependence.csv", index=False)
    vdec.to_csv(out / "paper2_variance_decomposition.csv", index=False)
    paired.to_csv(out / "paper2_paired_differences.csv", index=False)

    # ---------------------------------------------------------- workbooks
    _write({"Table1_design": t1, "Table1b_method_settings": settings,
            "Table2_calibration": t2, "Table3_validation": t3,
            "Table4_signal_bulk_quantile": t4,
            "Table5_signal_extremes": t5,
            "Table6_decomposition": t6},
           out / "Paper2_Tables_FINAL.xlsx")
    # Supplementary numbering is locked to the manuscript citations: S1 is the
    # method design, S6 the full decomposition. A reader who follows a citation
    # must land on the sheet the sentence promised.
    # S1 is a flat item/description table so the three method descriptions and
    # the shared settings read as one list rather than a sparse matrix.
    cols = list(t1.columns)
    s1 = pd.DataFrame(
        [{"Item": f"Method: {row[cols[0]]}",
          "Description": "; ".join(f"{c.lower()}: {row[c]}" for c in cols[1:])}
         for _, row in t1.iterrows()]
        + [{"Item": row["Setting"], "Description": row["Value"]}
           for _, row in settings.iterrows()])
    _write({"S1_method_design": s1,
            "S2_calibration_full": perf[perf.period == "calibration"].round(3),
            "S3_validation_full": perf[perf.period == "validation"].round(3),
            "S4_signal_summary": s_pe,
            "S5_signal_full": sig.round(3),
            "S6_decomposition_full": vdec.round(2),
            "S7_temporal_dependence": tbias.round(3),
            "S8_paired_differences": paired,
            "S9_acceptance_gates": gates,
            "S10_model_inventory": inv,
            "S10b_fit_diagnostics": fitd.round(4),
            "S10c_apply_diagnostics": appd.round(4)},
           out / "Paper2_Supplementary_ARCHIVE.xlsx")
    for n, d in (("Table1", t1), ("Table2", t2), ("Table3", t3),
                 ("Table4", t4), ("Table5", t5), ("Table6", t6)):
        d.to_csv(out / f"Paper2_{n}.csv", index=False)

    # ------------------------------------------------------------- figures
    if a.figure1 and Path(a.figure1).exists():
        reg._n = 1
        (out / "figures" / "Paper2_Figure_01_study_area.png").write_bytes(
            Path(a.figure1).read_bytes())
        reg.index.append({"figure": 1, "file": "Paper2_Figure_01_study_area",
                          "slug": "study_area",
                          "caption": f"Location of {cfg.area} province in Thailand "
                                     f"(inset) and the {len(coords)} rain gauges "
                                     f"used in this study, over terrain elevation."})

    figures.fig_method_mab(cfg, perf, reg, "calibration", ALL_SIM, PERF_SET,
                           "calibration_methods",
                           f"Mean absolute bias over the calibration period "
                           f"{cal[0]}\u2013{cal[1]} for the raw models and the three "
                           f"bias-correction methods, averaged over "
                           f"{len(stations)} gauges and {inv.model.nunique()} GCMs. "
                           f"The dotted divider separates statistics controlled by "
                           f"the marginal daily distribution from sequence-dependent "
                           f"statistics. Note the logarithmic vertical scale.",
                           marginal_n=len(MARGINAL_SET))
    figures.fig_method_mab(cfg, perf, reg, "validation", ALL_SIM, PERF_SET,
                           "validation_methods",
                           f"As the previous figure, for the independent validation "
                           f"period {val[0]}\u2013{val[1]} using parameters fitted on "
                           f"{cal[0]}\u2013{cal[1]} and frozen. Axes and ordering are "
                           f"identical to allow direct comparison.",
                           marginal_n=len(MARGINAL_SET))

    figures.fig_pe(cfg, pe_all, reg, [("(a) bulk statistics", BULK),
                                   ("(b) wet-day quantiles", QUANT)],
                   "signal_bulk_quantile",
                   f"Signal-preservation error PE for bulk and quantile statistics, "
                   f"{wy[0]}\u2013{wy[1]} against the {base[0]}\u2013{base[1]} baseline of "
                   f"the same model and method. Bars are ensemble medians over "
                   f"{inv.model.nunique()} GCMs and {len(stations)} gauges; whiskers "
                   f"are the inter-model interquartile range, which is a spread, not "
                   f"a confidence interval. PE = 0 means the raw model's own change "
                   f"was reproduced exactly.")
    figures.fig_pe(cfg, pe_all, reg,
                   [("(a) daily and threshold extremes", ["Rx1day"] + THRESH_EXT),
                    ("(b) tail indices and sequence-dependent diagnostics",
                     TAIL_EXT + SEQ_SET)],
                   "signal_extremes",
                   "As the previous figure, for the extreme-rainfall indices. "
                   "Rx5day, CDD and CWD depend on the ordering of wet and dry days, "
                   "which no marginal quantile method reconstructs; they are drawn "
                   "as open hatched bars and reported as diagnostics.")

    figures.fig_pe_synthesis(cfg, pe_all, reg, PERF_SET,
                             "synthesis",
                             f"Integrated comparison of signal-preservation error "
                             f"by bias-correction method for {wy[0]}\u2013{wy[1]}, "
                             f"with each scenario in its own panel on a common "
                             f"vertical scale. Values are those of Tables 4 and 5. "
                             f"Symbols are ensemble medians and vertical bars the "
                             f"inter-model interquartile range. Indices are ordered "
                             f"from bulk statistics through quantiles to derived "
                             f"extremes and sequence-dependent diagnostics (shaded).")

    reg.write_index()
    pd.DataFrame(reg.index).to_csv(out / "Paper2_CAPTIONS.csv", index=False)
    print(f"Paper 2: {len(reg.index)} figures, 6 main tables -> {out}")


if __name__ == "__main__":
    main()
