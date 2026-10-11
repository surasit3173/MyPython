#!/usr/bin/env python3
"""Gate F — acquire and verify the administrative boundary.

    python scripts/gate_f_boundary.py --config config/uttaradit.yaml

Produces `data/gis/<area>_adm1_verified.geojson` and
`output/results/BOUNDARY_VERIFICATION_REPORT.xlsx`.  If no source yields a
verifiable polygon, the report records NOT ESTABLISHED and Gate F stays BLOCKED
— nothing is approximated.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from cmip6bc import boundary, io_data                        # noqa: E402
from cmip6bc.config import load_config                       # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    cfg = load_config(a.config)
    res = cfg.out("results")

    stations = io_data.resolve_stations(cfg.path("observed"), cfg.path("gis"),
                                        cfg.raw["area"].get("stations"))
    coords = io_data.load_coordinates(cfg.path("gis"))
    coords = coords[coords.station.isin([str(s) for s in stations])]

    b, rep = boundary.acquire_and_verify(
        cfg, coords, cache_dir=cfg.path("gis") / "_sources")

    tables = {"Attempts": rep["attempts"], "CrossSource": rep["cross_source"]}
    if b is None:
        tables["Verification"] = pd.DataFrame([
            {"item": "status", "value": "NOT ESTABLISHED"},
            {"item": "consequence",
             "value": "Gate F remains BLOCKED; no spatial product is produced"}])
        print("Gate F: NOT ESTABLISHED - no verifiable ADM1 polygon obtained")
    else:
        c = {k: v for k, v in b.checks.items() if not k.startswith("_")}
        tables["Verification"] = pd.DataFrame(
            [{"item": k, "value": str(v)} for k, v in c.items()])
        tables["StationContainment"] = b.checks["_containment"]
        path = boundary.write_canonical(b, cfg.path("gis"), cfg.area)
        tables["Verification"] = pd.concat([
            tables["Verification"],
            pd.DataFrame([{"item": "canonical_file", "value": str(path.name)},
                          {"item": "canonical_file_hash",
                           "value": boundary._sha256(path)}])],
            ignore_index=True)
        print(f"Gate F: {'PASS' if b.checks['verified'] else 'REJECTED'} - "
              f"{c['administrative_unit']} ({c['iso_3166_2']}), "
              f"{c['area_km2']} km2, {c['n_stations_inside']}/{c['n_stations']} "
              f"gauges inside -> {path.name}")

    out = res / "BOUNDARY_VERIFICATION_REPORT.xlsx"
    with pd.ExcelWriter(out, engine="xlsxwriter") as w:
        book = w.book
        hdr = book.add_format({"bold": True, "font_name": "Times New Roman",
                               "font_size": 10, "bg_color": "#E8E8E8",
                               "border": 1, "text_wrap": True})
        cell = book.add_format({"font_name": "Times New Roman", "font_size": 10})
        for name, df in tables.items():
            if df is None or df.empty:
                df = pd.DataFrame([{"note": "no rows"}])
            df.to_excel(w, index=False, sheet_name=name[:31])
            ws = w.sheets[name[:31]]
            ws.set_column(0, max(len(df.columns) - 1, 0), 30, cell)
            ws.freeze_panes(1, 0)
            for j, col in enumerate(df.columns):
                ws.write(0, j, str(col), hdr)
    for k, v in tables.items():
        v.to_csv(res / f"boundary_{k.lower()}.csv", index=False)
    print(f"report -> {out}")


if __name__ == "__main__":
    main()
