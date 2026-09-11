#!/usr/bin/env python3
"""Assemble the final deliverable set and the SHA-256 manifest.

    python scripts/finalize.py --config config/uttaradit.yaml

Produces GATE_F_H_FINAL_STATUS.xlsx, FINAL_ACCEPTANCE_GATES.csv, the *_FINAL
table workbooks, and SHA256SUMS.txt covering every source and output file.
Applies the freeze rule: results are marked FROZEN only when every gate is in
an acceptable state, and the scope of what may be interpreted is written out
explicitly rather than left to the reader.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from cmip6bc.config import load_config                        # noqa: E402

# A gate in one of these states does not block the freeze; anything else does.
ACCEPTABLE = {
    "PASS",
    "PASS WITH RESIDUAL BIAS",
    "PASS (MARGINAL ONLY)",
    "DIAGNOSTIC PASS - TEMPORAL STRUCTURE NOT CORRECTED "
    "(NOT A PREDICTION-PERFORMANCE PASS)",
    "VERIFIED RAW ANOMALY - INTERPRETATION RESTRICTED",
}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def _write(tables: dict, path: Path) -> None:
    with pd.ExcelWriter(path, engine="xlsxwriter") as w:
        hdr = w.book.add_format({"bold": True, "font_name": "Times New Roman",
                                 "font_size": 10, "bg_color": "#E8E8E8",
                                 "border": 1, "text_wrap": True,
                                 "valign": "vcenter"})
        cell = w.book.add_format({"font_name": "Times New Roman",
                                  "font_size": 10, "text_wrap": True,
                                  "valign": "top"})
        for name, df in tables.items():
            df.to_excel(w, index=False, sheet_name=name[:31])
            ws = w.sheets[name[:31]]
            ws.freeze_panes(1, 0)
            ws.set_column(0, max(len(df.columns) - 1, 0), 26, cell)
            for j, c in enumerate(df.columns):
                ws.write(0, j, str(c), hdr)


def _scope_sentence(res: Path) -> str:
    """Scope is read from the screen, never assumed. Only the scenario-horizons
    the screen actually flags are excluded; a blanket rule would wrongly discard
    SSP2-4.5 Late, which passes."""
    f = Path(res) / "raw_signal_check.csv"
    if not f.exists():
        return "scope file absent; treat all horizons as unverified"
    d = pd.read_csv(f)
    bad = [f"{r.scenario.upper()}/{r.window}" for r in d.itertuples()
           if not r.usable_for_results]
    ok = [f"{r.scenario.upper()}/{r.window}" for r in d.itertuples()
          if r.usable_for_results]
    return (f"excluded: {', '.join(bad) if bad else 'none'}. "
            f"usable for primary quantitative conclusions: {', '.join(sorted(ok))}. "
            f"Report the agreement fraction with every median.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    a = ap.parse_args()
    cfg = load_config(a.config)
    res = cfg.path("output") / "results"
    fin = cfg.out("final")

    gates = pd.read_csv(res / "acceptance_gates.csv")
    defs = pd.read_csv(res / "gate_status_definitions.csv")
    gates["acceptable"] = gates.status.isin(ACCEPTABLE)
    frozen = bool(gates.acceptable.all())

    # ------------------------------------------------ interpretation scope
    scope = pd.DataFrame([
        {"category": "VERIFIED",
         "item": "Uttaradit ADM1 boundary",
         "detail": "Natural Earth 10m ADM1, TH-53, 7,610.7 km2, 378 vertices, "
                   "valid geometry, EPSG:4326, all 13 gauges contained; source "
                   "URL, access date and SHA-256 recorded"},
        {"category": "VERIFIED",
         "item": "historical -> scenario concatenation",
         "detail": "all 7 GCMs: 0 overlapping days, 0 gap days, last historical "
                   "2014, first scenario 2015, compatible calendars"},
        {"category": "DERIVED",
         "item": "bias-corrected datasets (QM, DetQM, QDM)",
         "detail": "fitted on 1981-2002 only, parameters frozen, applied to "
                   "2003-2014 and to the future windows; observations of the "
                   "target period never used"},
        {"category": "DERIVED",
         "item": "future change",
         "detail": "BC_future / BC_historical of the same GCM and method; "
                   "baseline 1995-2014"},
        {"category": "DIAGNOSTIC",
         "item": "temporal dependence (CDD, CWD, Rx5day, ACF, spells)",
         "detail": "measured and reported; quantile mapping does not reorder "
                   "days, so these are NOT corrected quantities"},
        {"category": "DIAGNOSTIC",
         "item": "raw-source trace",
         "detail": "5 of 6 checks ESTABLISHED from the delivered CSVs; NetCDF "
                   "metadata NOT ESTABLISHED"},
        {"category": "LIMITATION",
         "item": "boundary lineage",
         "detail": "one verified source only. Every other reachable dataset "
                   "returned an identical geometry (IoU = 1.000), so cross-source "
                   "confirmation is NOT independent. Natural Earth is a "
                   "generalised cartographic dataset; its area is 2.9% below the "
                   "commonly cited provincial figure"},
        {"category": "LIMITATION",
         "item": "station homogeneity",
         "detail": "4 of 13 gauges (351003, 351005, 351006, 351007) change "
                   "wet-day frequency by more than a third between calibration "
                   "and validation; station metadata not yet verified"},
        {"category": "LIMITATION",
         "item": "out-of-sample residual",
         "detail": "network-mean |bias| 26.4%; 13.4% excluding the "
                   "non-homogeneous gauges. Better than raw, not reliable for "
                   "all extremes"},
        {"category": "LIMITATION",
         "item": "grid resolution",
         "detail": "63 station columns collapse to 3-15 distinct series per GCM "
                   "(CanESM5: 3). Sub-provincial spatial detail in the raw model "
                   "fields is not real"},
        {"category": "QUARANTINED",
         "item": "SSP5-8.5 Late (2081-2100)",
         "detail": "raw change -40%; the bias correction preserved it faithfully "
                   "(PE +0.2%), and no extraction, unit, calendar or "
                   "concatenation fault was found. Verified as a property of the "
                   "raw source; causal or physical interpretation is not "
                   "permitted without the source NetCDF"},
        {"category": "EXCLUDED FROM INTERPRETATION",
         "item": "Paper 1 primary quantitative conclusions",
         "detail": _scope_sentence(res)},
        {"category": "EXCLUDED FROM INTERPRETATION",
         "item": "corrected-extreme claims",
         "detail": "CDD, CWD and Rx5day must not be described as corrected"},
        {"category": "NOT ESTABLISHED",
         "item": "source NetCDF identity and metadata",
         "detail": "institution, units attribute, calendar attribute, native "
                   "grid, time bounds, cell coordinates and fill value cannot be "
                   "read because the files were never supplied"},
        {"category": "NOT ESTABLISHED",
         "item": "grid-to-station extraction algorithm",
         "detail": "nearest neighbour, bilinear or grid-box average cannot be "
                   "distinguished without the extraction code"},
    ])

    freeze = pd.DataFrame([
        {"item": "Freeze status",
         "value": "FROZEN - scope restricted" if frozen else "NOT FROZEN"},
        {"item": "Rule",
         "value": "every gate must be in an acceptable state; Gate H must be "
                  "resolved or its subject explicitly excluded from "
                  "interpretation"},
        {"item": "Gates acceptable",
         "value": f"{int(gates.acceptable.sum())}/{len(gates)}"},
        {"item": "Paper 1 scope",
         "value": "Near and Mid horizons, both scenarios. SSP5-8.5 Late is "
                  "excluded from primary quantitative conclusions and appears "
                  "only as a quarantined diagnostic"},
        {"item": "Paper 2 scope",
         "value": "full QM/EQM vs DetQM vs QDM comparison; it does not depend on "
                  "physical interpretation of the quarantined anomaly"},
        {"item": "Frozen at (UTC)",
         "value": datetime.now(timezone.utc).isoformat(timespec="seconds")},
    ])

    fh_tables = {"FreezeDecision": freeze, "Gates": gates,
                 "StatusDefinitions": defs, "InterpretationScope": scope}
    for name, f in (("GateF_Verification", "BOUNDARY_VERIFICATION_REPORT.xlsx"),):
        p = res / f
        if p.exists():
            for sh, df in pd.read_excel(p, sheet_name=None).items():
                fh_tables[f"F_{sh}"] = df
    for f in sorted(res.glob("gate_h_*.csv")) + sorted(res.glob("raw_trace_*.csv")):
        fh_tables["H_" + f.stem.replace("gate_h_", "")] = pd.read_csv(f)
    _write(fh_tables, fin / "GATE_F_H_FINAL_STATUS.xlsx")
    gates.to_csv(fin / "FINAL_ACCEPTANCE_GATES.csv", index=False)
    scope.to_csv(fin / "INTERPRETATION_SCOPE.csv", index=False)

    # ------------------------------------------------ final table workbooks
    for src, dst in (("paper1/Paper1_Tables.xlsx", "Paper1_Tables_FINAL.xlsx"),
                     ("paper2/Paper2_Tables.xlsx", "Paper2_Tables_FINAL.xlsx")):
        s = cfg.path("output") / src
        if s.exists():
            sheets = pd.read_excel(s, sheet_name=None)
            sheets = {"Z_freeze_and_scope": pd.concat(
                [freeze.assign(section="freeze"),
                 scope.rename(columns={"category": "item", "item": "value",
                                       "detail": "section"})],
                ignore_index=True)} | sheets
            _write(sheets, fin / dst)
    for p in (res / "BOUNDARY_VERIFICATION_REPORT.xlsx",
              res / "RAW_SSP585_LATE_SOURCE_TRACE.xlsx"):
        if p.exists():
            shutil.copy2(p, fin / p.name)

    # ------------------------------------------------ SHA-256 manifest
    roots = [cfg.path("observed").parent, cfg.path("cmip6_raw"),
             cfg.path("gis"), cfg.path("output")]
    rows = []
    for r in roots:
        for f in sorted(Path(r).rglob("*")):
            if f.is_file() and "__pycache__" not in str(f):
                rows.append({"role": "input" if r != cfg.path("output")
                             else "output",
                             "path": str(f.relative_to(cfg.root)),
                             "bytes": f.stat().st_size, "sha256": sha256(f)})
    man = pd.DataFrame(rows)
    man.to_csv(fin / "SHA256_MANIFEST.csv", index=False)
    (fin / "SHA256SUMS.txt").write_text(
        "\n".join(f"{r.sha256}  {r.path}" for r in man.itertuples()) + "\n")

    print(f"freeze status: {'FROZEN - scope restricted' if frozen else 'NOT FROZEN'}"
          f"  ({int(gates.acceptable.sum())}/{len(gates)} gates acceptable)")
    print(f"hashed {len(man)} files -> {fin}")


if __name__ == "__main__":
    main()
