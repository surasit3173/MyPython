#!/usr/bin/env python3
"""Prepare the supplementary material for Applied Environmental Research.

    python docx_build_aer/prepare_supplement_aer.py --config config/uttaradit.yaml

Two kinds of supplementary item are produced, because they answer different
needs and a single format serves neither well.

A **Supplementary Table** is something a reader reads. It is rendered in the
Word document in the same style as the manuscript. Where the underlying listing
runs to hundreds of rows or dozens of columns, the table presented is the
aggregate the manuscript actually cites, not a raw dump: a 67-column,
364-row sheet is not a table in any useful sense and would occupy thirteen
pages that nobody reads.

A **Supplementary Data** file is something a reader computes with. The complete
listing, every station, model, scenario and index, is written as CSV and forms
part of the submission, so no citation points outside the package.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))
from cmip6bc.config import load_config                        # noqa: E402

LABEL = {"raw": "Raw CMIP6", "qm": "QM/EQM", "detqm": "DetQM", "qdm": "QDM"}
SCEN = {"ssp245": "SSP2-4.5", "ssp585": "SSP5-8.5"}
ORDER = ["raw", "qm", "detqm", "qdm"]
IDX = ["wet_day_pct", "PRCPTOT", "SDII", "q50", "q90", "q95", "q99",
       "Rx1day", "Rx5day", "R10mm", "R20mm", "R50mm", "R95p", "R99p",
       "CDD", "CWD"]
PRETTY = {"wet_day_pct": "Wet days", "PRCPTOT": "PRCPTOT", "SDII": "SDII",
          "q50": "q50", "q90": "q90", "q95": "q95", "q99": "q99",
          "Rx1day": "Rx1day", "Rx5day": "Rx5day", "R10mm": "R10mm",
          "R20mm": "R20mm", "R50mm": "R50mm", "R95p": "R95p", "R99p": "R99p",
          "CDD": "CDD", "CWD": "CWD"}


def mab_table(perf: pd.DataFrame, period: str) -> pd.DataFrame:
    """Mean absolute bias by index and method: what the manuscript cites."""
    sub = perf[perf.period == period]
    rows = []
    for k in IDX:
        col = f"{k}_bias_pct"
        if col not in sub.columns:
            continue
        rec = {"Index": PRETTY.get(k, k)}
        for m in ORDER:
            d = sub[sub.method == m]
            if len(d):
                rec[LABEL[m]] = round(float(d[col].abs().mean()), 2)
        rows.append(rec)
    return pd.DataFrame(rows)


def temporal_table(tbias: pd.DataFrame) -> pd.DataFrame:
    keys = {"acf1_daily": "ACF(1) daily", "acf1_occurrence": "ACF(1) occurrence",
            "P_wet_given_wet": "P(wet | wet)", "P_wet_given_dry": "P(wet | dry)",
            "mean_wet_spell": "Mean wet spell", "mean_dry_spell": "Mean dry spell",
            "p90_dry_spell": "p90 dry spell"}
    rows = []
    for period in ("calibration", "validation"):
        for m in ORDER:
            d = tbias[(tbias.period == period) & (tbias.method == m)]
            if not len(d):
                continue
            rec = {"Period": period.capitalize(), "Method": LABEL[m]}
            for k, nice in keys.items():
                c = f"{k}_bias_pct"
                if c in d.columns:
                    rec[nice] = round(float(d[c].abs().mean()), 2)
            rows.append(rec)
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    a = ap.parse_args()
    cfg = load_config(a.config)
    src = cfg.path("output") / "paper2_aer"
    res = cfg.path("output") / "results"
    data_dir = src / "supplementary_data"
    data_dir.mkdir(parents=True, exist_ok=True)

    xl = pd.ExcelFile(src / "Paper2_Supplementary_ARCHIVE.xlsx")
    sheet = lambda pref: next(s for s in xl.sheet_names if s.startswith(pref))
    perf = pd.read_csv(src / "paper2_mab.csv") if (src / "paper2_mab.csv").exists() \
        else None
    perf_full = pd.read_csv(res / "performance.csv")
    tbias = pd.read_csv(res / "temporal_bias.csv")
    pe_sum = pd.read_excel(xl, sheet("S4"))
    pe_full = pd.read_excel(xl, sheet("S5"))
    vdec = pd.read_excel(xl, sheet("S6"))
    paired = pd.read_excel(xl, sheet("S8"))
    gates = pd.read_excel(xl, sheet("S9"))
    inv = pd.read_excel(xl, sheet("S10_"))
    fitd = pd.read_excel(xl, sheet("S10b"))
    appd = pd.read_excel(xl, sheet("S10c"))
    s1 = pd.read_excel(xl, sheet("S1_"))

    # ------------------------------------------------- display tables
    tables = []

    def add(num, title, df, note=""):
        tables.append({"number": num, "title": title, "note": note,
                       "columns": [str(c) for c in df.columns],
                       "rows": [["" if pd.isna(v) else
                                 (f"{v:g}" if isinstance(v, (int, float, np.floating))
                                  else str(v)) for v in r]
                                for r in df.itertuples(index=False)]})

    add("S1", "Design of the three bias-correction methods and the settings "
              "they share", s1)

    t2 = mab_table(perf_full, "calibration")
    add("S2", "Calibration-period mean absolute bias by index and method, "
              "averaged over 13 gauges and 7 GCMs", t2,
        "Station- and model-level values for all 16 indices are in "
        "Supplementary Data S2.")
    t3 = mab_table(perf_full, "validation")
    add("S3", "Independent-validation mean absolute bias by index and method, "
              "using parameters fitted on the calibration period and frozen", t3,
        "Station- and model-level values are in Supplementary Data S3.")

    # eleven narrow columns forced the headers to wrap, so the paired ones are
    # combined into a single readable field
    t4 = pd.DataFrame({
        "Scenario": pe_sum["scenario"],
        "Index": pe_sum["index"],
        "Method": pe_sum["method"],
        "n": pe_sum["n_models"],
        "Gauges": [f"{a}" if a == b else f"{a}\u2013{b}"
                   for a, b in zip(pe_sum["gauges_min"], pe_sum["gauges_max"])],
        "Median PE (%)": pe_sum["median"].round(2),
        "IQR (%)": [f"{a:.2f} to {b:.2f}" if pd.notna(a) else ""
                    for a, b in zip(pe_sum["q25"], pe_sum["q75"])],
        "Mean (%)": pe_sum["mean"].round(2),
        "SD (%)": pe_sum["sd"].round(2),
    })
    add("S4", "Climate-signal preservation summary for every scenario, index "
              "and method", t4)

    add("Data S5", "Climate-signal preservation for every model, gauge, "
                    "scenario and index",
        pd.DataFrame([{"Contents": "signal-preservation error per model, "
                                   "gauge, scenario and index",
                       "Rows": len(pe_full), "Columns": len(pe_full.columns),
                       "File": "Supplementary_Data_S5.csv"}]),
        "This listing has 9,804 rows and is supplied as a machine-readable "
        "file with this submission rather than as a printed table.")

    keepv = ["scenario", "index", "n", "n_models", "model_share_pct",
             "method_share_pct", "residual_share_pct"]
    t6 = vdec[[c for c in keepv if c in vdec.columns]].copy()
    t6.columns = ["Scenario", "Index", "N cells", "GCMs", "GCM main effect (%)",
                  "BC-method main effect (%)", "Residual (%)"][:len(t6.columns)]
    t6["Scenario"] = t6["Scenario"].map(lambda v: SCEN.get(v, v))
    add("S6", "Descriptive two-factor sum-of-squares partition for all indices "
              "and both scenarios", t6.round(1))

    add("S7", "Temporal-dependence statistics: mean absolute bias against "
              "observations, averaged over gauges and GCMs", temporal_table(tbias),
        "Gauge- and model-level values are in Supplementary Data S7.")
    add("S8", "Paired method differences against QM/EQM, model-level and "
              "descriptive", paired)
    add("S9", "Acceptance-gate status", gates)
    add("S10", "CMIP6 model inventory", inv)

    # ------------------------------------------------- data files
    written = []
    for name, df in (("S2", perf_full[perf_full.period == "calibration"]),
                     ("S3", perf_full[perf_full.period == "validation"]),
                     ("S5", pe_full), ("S7", tbias),
                     ("S10b_fit_diagnostics", fitd),
                     ("S10c_apply_diagnostics", appd)):
        f = data_dir / f"Supplementary_Data_{name}.csv"
        df.to_csv(f, index=False)
        written.append({"file": f.name, "rows": len(df),
                        "columns": len(df.columns)})

    md = ROOT / "manuscript" / "Paper2_AER_manuscript.md"
    payload = {"title": md.read_text(encoding="utf-8").split("\n")[0].lstrip("# ").strip(),
               "author": "Surasit Punyawansiri",
               "affiliation": "Office of Water Management and Hydrology, Royal "
                              "Irrigation Department, Dusit, Bangkok 10300, "
                              "Thailand",
               "tables": tables, "data_files": written,
               "out": str(src / "Paper2_AER_Supplementary.docx")}
    (HERE / "supplement.json").write_text(json.dumps(payload, ensure_ascii=False),
                                          encoding="utf-8")
    print(f"prepared {len(tables)} supplementary tables and "
          f"{len(written)} data files -> {data_dir}")
    for t in tables:
        print(f"  {t['number']:4s} {len(t['rows']):5d} rows x "
              f"{len(t['columns']):2d} cols  {t['title'][:52]}")


if __name__ == "__main__":
    main()
