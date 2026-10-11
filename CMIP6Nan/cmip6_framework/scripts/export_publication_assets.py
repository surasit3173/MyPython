#!/usr/bin/env python3
"""Export journal-ready figures and tables as standalone publication assets.

    python scripts/export_publication_assets.py --config config/uttaradit.yaml \
           --paper paper1
    python scripts/export_publication_assets.py --config config/uttaradit.yaml \
           --paper paper2

Writes to <output>/publication_assets/<paper>/ without touching anything the
analysis produced, so the manuscript build and this export can be rerun in any
order. Numbering follows the manuscript captions, which are the single source of
truth, so an asset can never be labelled differently from the text.

Figures are re-rendered from the pipeline's own vector PDFs where those exist and
are additionally written as 600 dpi TIFF with LZW compression and as 1200 dpi
TIFF for the line-art figures, which is what most Q1-Q2 journals ask for. Tables
are written both as formatted XLSX, one sheet per table, and as tab-separated
text for typesetting.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from cmip6bc.config import load_config                        # noqa: E402

# Journal targets. Line art (charts, maps, diagrams) needs a higher raster
# resolution than photographic content; every figure here is line art.
DPI_RASTER = 600
DPI_LINE_ART = 1200
COLUMN_WIDTH_MM = {"single": 90, "double": 190}
AER_WIDTHS_MM = [39, 84, 129, 174]


def captions_from_manuscript(md: Path) -> dict:
    """Caption text keyed by 'Table 1', 'Figure 3', and so on."""
    if not md.exists():
        return {}
    src = md.read_text(encoding="utf-8")
    caps = {}
    for kind in ("Table", "Figure"):
        for num, text in re.findall(rf"\*\*{kind} (\w+)\*\* (.+)", src):
            caps[f"{kind} {num}"] = text.strip()
    return caps


def figure_order(md: Path) -> list:
    """Figure numbers in the order the manuscript defines them."""
    if not md.exists():
        return []
    src = md.read_text(encoding="utf-8")
    return [n for n, _ in re.findall(r"\*\*Figure (\w+)\*\* (.+)", src)]


def build_figure_map(figdir: Path, order: list, map_file: Path):
    """Resolve manuscript figure numbers to rendered files.

    The pipeline numbers its own output independently of the manuscript, and a
    figure moved to the supplement shifts everything after it, so matching by
    position silently mislabels figures. The mapping is therefore declared once
    in a JSON file that the Word builder reads as well.
    """
    if not map_file.exists():
        sys.exit(f"figure map not found: {map_file}\n"
                 "declare which rendered figure is which manuscript figure")
    spec = json.loads(map_file.read_text(encoding="utf-8"))
    main = {k: figdir / v for k, v in spec.get("main", {}).items()
            if not k.startswith("_")}
    supp = {k: figdir / v for k, v in spec.get("supplementary", {}).items()}
    missing = [f"Figure {k}" for k in order if k not in main]
    if missing:
        sys.exit(f"the manuscript captions {missing} but the figure map does not")
    absent = [str(p) for p in list(main.values()) + list(supp.values())
              if not p.exists()]
    if absent:
        sys.exit(f"figure map points at files that do not exist: {absent}")
    return main, supp


def fit_to_column(png: Path, target_mm: float, dpi: int = DPI_RASTER) -> Path:
    """Resample a figure that would exceed the double-column measure.

    A journal will not enlarge a figure, but it will reduce one, and reduction
    lowers the effective resolution below the stated dpi. Resampling here keeps
    the declared resolution honest at the printed size.
    """
    from PIL import Image
    im = Image.open(png)
    max_px = int(target_mm / 25.4 * dpi)
    if im.width <= max_px:
        return png
    h = round(im.height * max_px / im.width)
    out = png.with_name(png.stem + "_fitted.png")
    im.resize((max_px, h), Image.LANCZOS).save(out, dpi=(dpi, dpi))
    return out


def to_tiff(src_png: Path, dest: Path, dpi: int) -> bool:
    """LZW-compressed TIFF at the requested resolution."""
    try:
        from PIL import Image
        im = Image.open(src_png)
        if im.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGB", im.size, "white")
            bg.paste(im, mask=im.convert("RGBA").split()[-1])
            im = bg
        im.save(dest, format="TIFF", compression="tiff_lzw",
                dpi=(dpi, dpi))
        return True
    except Exception as e:                                    # pragma: no cover
        print(f"  [warn] TIFF export failed for {src_png.name}: {e}")
        return False


def check_figure(png: Path, target_mm: float, dpi: int = DPI_RASTER) -> dict:
    """Report the physical size a figure would occupy at the target resolution."""
    from PIL import Image
    im = Image.open(png)
    w_mm = im.width / dpi * 25.4
    fits = "at target" if abs(w_mm - target_mm) <= 1.5 else (
        "under" if w_mm < target_mm else "oversize")
    return {"pixels": f"{im.width}\u00d7{im.height}",
            f"width_mm_at_{dpi}dpi": round(w_mm, 1),
            "column_fit": fits}


def _write_tables(tables: dict, path: Path) -> None:
    with pd.ExcelWriter(path, engine="xlsxwriter") as w:
        hdr = w.book.add_format({"bold": True, "font_name": "Times New Roman",
                                 "font_size": 10, "bottom": 1, "top": 1,
                                 "text_wrap": True, "valign": "vcenter",
                                 "align": "center"})
        cell = w.book.add_format({"font_name": "Times New Roman",
                                  "font_size": 10, "valign": "top"})
        for name, df in tables.items():
            df.to_excel(w, index=False, sheet_name=name[:31], startrow=1)
            ws = w.sheets[name[:31]]
            ws.set_column(0, max(len(df.columns) - 1, 0), 20, cell)
            for j, c in enumerate(df.columns):
                ws.write(1, j, str(c), hdr)
            ws.freeze_panes(2, 0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--paper", choices=["paper1", "paper2"], required=True)
    ap.add_argument("--journal", default="apst", choices=["apst", "aer"])
    a = ap.parse_args()
    cfg = load_config(a.config)

    src = (cfg.path("output") / f"{a.paper}_manuscript" if a.journal == "apst"
           else cfg.path("output") / f"{a.paper}_{a.journal}")
    md_name = {("paper1", "apst"): "Paper1_APST_manuscript.md",
               ("paper2", "apst"): "Paper2_APST_manuscript.md",
               ("paper2", "aer"): "Paper2_AER_manuscript.md"}[(a.paper, a.journal)]
    md = ROOT / "manuscript" / md_name
    if not src.exists():
        sys.exit(f"manuscript outputs not found: {src}")

    out = (cfg.path("output") / "publication_assets" /
           (a.paper if a.journal == "apst" else f"{a.paper}_{a.journal}"))
    (out / "figures").mkdir(parents=True, exist_ok=True)
    (out / "tables").mkdir(parents=True, exist_ok=True)

    # AER accepts only four figure widths; everything else uses the double
    # column measure
    target_mm = 129.0 if a.journal == "aer" else COLUMN_WIDTH_MM["double"]

    caps = captions_from_manuscript(md)
    order = figure_order(md)
    map_name = (f"{a.paper}_figure_map.json" if a.journal == "apst"
                else f"{a.paper}_{a.journal}_figure_map.json")
    fmap, suppmap = build_figure_map(src / "figures", order,
                                     ROOT / "manuscript" / map_name)

    # ------------------------------------------------------------- figures
    rows = []
    for num, raw_png in fmap.items():
        stem = f"Figure_{int(num):02d}" if num.isdigit() else f"Figure_{num}"
        png = fit_to_column(raw_png, target_mm)
        shutil.copy2(png, out / "figures" / f"{stem}.png")
        pdf = raw_png.with_suffix(".pdf")
        if pdf.exists():
            shutil.copy2(pdf, out / "figures" / f"{stem}.pdf")
        to_tiff(png, out / "figures" / f"{stem}_{DPI_LINE_ART}dpi.tif",
                DPI_LINE_ART)
        info = check_figure(png, target_mm)
        info["resampled"] = png is not raw_png
        rows.append({"figure": f"Figure {num}", "source_file": raw_png.name,
                     "png": f"{stem}.png",
                     "vector_pdf": f"{stem}.pdf" if pdf.exists() else "none",
                     "tiff": f"{stem}_{DPI_LINE_ART}dpi.tif",
                     **info,
                     "caption": caps.get(f"Figure {num}", "")})
    for num, raw_supp in suppmap.items():
        stem = f"Figure_{num}"
        png = fit_to_column(raw_supp, target_mm)
        shutil.copy2(png, out / "figures" / f"{stem}.png")
        pdf = raw_supp.with_suffix(".pdf")
        if pdf.exists():
            shutil.copy2(pdf, out / "figures" / f"{stem}.pdf")
        to_tiff(png, out / "figures" / f"{stem}_{DPI_LINE_ART}dpi.tif",
                DPI_LINE_ART)
        rows.append({"figure": f"Supplementary Figure {num}",
                     "source_file": raw_supp.name, "png": f"{stem}.png",
                     "vector_pdf": f"{stem}.pdf" if pdf.exists() else "none",
                     "tiff": f"{stem}_{DPI_LINE_ART}dpi.tif",
                     **check_figure(png, target_mm), "caption": ""})
    figs = pd.DataFrame(rows)

    # -------------------------------------------------------------- tables
    wb = next(src.glob("*Tables*.xlsx"), None)
    supp = next(src.glob("*Supplement*.xlsx"), None)
    # Which workbook sheet is which manuscript table is declared, not inferred
    # from sheet order: the workbook holds sheets the manuscript does not print,
    # so positional matching exports the wrong table under the right number.
    tmap_file = ROOT / "manuscript" / (
        f"{a.paper}_table_map.json" if a.journal == "apst"
        else f"{a.paper}_{a.journal}_table_map.json")
    if not tmap_file.exists():
        sys.exit(f"table map not found: {tmap_file}")
    tspec = json.loads(tmap_file.read_text(encoding="utf-8"))["main"]
    table_rows, main_tables = [], {}
    if wb:
        sheets = pd.read_excel(wb, sheet_name=None)
        for num, sheet_name in sorted(tspec.items(), key=lambda kv: int(kv[0])):
            key = f"Table {num}"
            if sheet_name not in sheets:
                sys.exit(f"{key} maps to sheet '{sheet_name}', which is not in "
                         f"{wb.name}")
            if key not in caps:
                sys.exit(f"{key} is in the table map but the manuscript has no "
                         f"caption for it")
            df = sheets[sheet_name]
            main_tables[key.replace(" ", "")] = df
            df.to_csv(out / "tables" / f"Table_{int(num):02d}.tsv", sep="\t",
                      index=False)
            table_rows.append({"table": key, "source_sheet": sheet_name,
                               "rows": len(df), "columns": len(df.columns),
                               "tsv": f"Table_{int(num):02d}.tsv",
                               "caption": caps.get(key, "")})
        extra = sorted(k for k in caps if k.startswith("Table ")
                       and k.split()[1] not in tspec)
        if extra:
            sys.exit(f"the manuscript captions {extra} but the table map does "
                     f"not list them")
    if main_tables:
        _write_tables(main_tables, out / "tables" / "Main_Tables.xlsx")
    if supp:
        shutil.copy2(supp, out / "tables" / supp.name)
    tabs = pd.DataFrame(table_rows)

    # ------------------------------------------------------- manifest, list
    figs.to_csv(out / "FIGURE_LIST.csv", index=False)
    tabs.to_csv(out / "TABLE_LIST.csv", index=False)
    cap_txt = "\n\n".join(
        [f"Table {r.table.split()[1]}. {r.caption}" for r in tabs.itertuples()]
        + [f"Figure {r.figure.split()[1]}. {r.caption}" for r in figs.itertuples()])
    (out / "CAPTIONS.txt").write_text(cap_txt, encoding="utf-8")

    files = sorted(p for p in out.rglob("*") if p.is_file())
    pd.DataFrame([{"file": str(p.relative_to(out)), "bytes": p.stat().st_size,
                   "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                  for p in files]).to_csv(out / "SHA256.csv", index=False)
    (out / "manifest.json").write_text(json.dumps({
        "paper": a.paper, "area": cfg.area,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "figures": len(figs), "tables": len(tabs),
        "raster_dpi": DPI_LINE_ART, "target_figure_width_mm": target_mm,
        "numbering_source": str(md.relative_to(ROOT)),
        "supplementary_figures": {k: v.name for k, v in suppmap.items()},
    }, indent=2), encoding="utf-8")

    print(f"{a.paper}: {len(figs)} figures, {len(tabs)} tables -> {out}")
    if len(figs):
        print(figs[["figure", "pixels", f"width_mm_at_{DPI_RASTER}dpi",
                    "column_fit"]].to_string(index=False))
    bad = ("oversize", "under") if a.journal == "aer" else ("oversize",)
    off = figs[figs.column_fit.isin(bad)]
    if len(off):
        print(f"  note: {len(off)} figure(s) are not at the {target_mm:.0f} mm "
              f"width the journal prescribes; see FIGURE_LIST.csv")


if __name__ == "__main__":
    main()
