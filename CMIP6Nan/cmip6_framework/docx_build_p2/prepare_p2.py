#!/usr/bin/env python3
"""Prepare the Paper 2 Word build inputs.

    python docx_build_p2/prepare_p2.py --config config/uttaradit.yaml

Reads the manuscript narrative from manuscript/ and the numbers from the
Paper 2 result workbook, and writes the JSON files that build_p2.js renders.
Nothing here is area-specific: paths come from the configuration.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))
from cmip6bc.config import load_config                        # noqa: E402

EQ_PREFIXES = ("QM: BC(", "DetQM: BC(", "QDM: BC(", "MAB(", "*\u03b5*",
               "*S*", "PE(", "*E*")
SHORT = {"marginal": "marginal", "sequence-dependent": "sequence"}


def split_markdown(md_path: Path):
    src = md_path.read_text(encoding="utf-8")
    abstract = src.split("## Abstract")[1].split("**Keywords")[0].strip()
    keywords = "**Keywords:**" + src.split("**Keywords:**")[1].split("\n")[0]
    title = src.split("\n")[0].lstrip("# ").strip()
    mid = "## 1. Introduction" + src.split("## 1. Introduction")[1].split("## Tables")[0]
    secs = []
    for raw in mid.split("\n"):
        line = raw.rstrip()
        if not line.strip() or line.startswith("---") or line.startswith("*Formatted"):
            continue
        if line.startswith("## "):
            secs.append({"t": "h", "v": line[3:].strip()}); continue
        if line.startswith("### "):
            secs.append({"t": "sh", "v": line[4:].strip()}); continue
        t = (line.strip().replace("<sub>", "~").replace("</sub>", "~")
                         .replace("<sup>", "^").replace("</sup>", "^"))
        secs.append({"t": "eq" if t.startswith(EQ_PREFIXES) else "p", "v": t})
    return title, abstract, keywords, secs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    a = ap.parse_args()
    cfg = load_config(a.config)
    src = cfg.path("output") / "paper2_manuscript"
    md = ROOT / "manuscript" / "Paper2_APST_manuscript.md"
    if not md.exists():
        sys.exit(f"manuscript narrative not found: {md}")
    if not (src / "Paper2_Tables_FINAL.xlsx").exists():
        sys.exit("Paper 2 tables not found; run build_paper2_manuscript.py first")

    title, abstract, keywords, secs = split_markdown(md)
    (HERE / "abstract.txt").write_text(abstract, encoding="utf-8")
    (HERE / "sections.json").write_text(json.dumps(secs, ensure_ascii=False),
                                        encoding="utf-8")

    xl = pd.ExcelFile(src / "Paper2_Tables_FINAL.xlsx")
    sheet = lambda pref: next(s for s in xl.sheet_names if s.startswith(pref))
    t1 = pd.read_excel(xl, sheet("Table1_design"))
    t2 = pd.read_excel(xl, sheet("Table2"))
    t3 = pd.read_excel(xl, sheet("Table3"))
    t4 = pd.read_excel(xl, sheet("Table4"))
    t5 = pd.read_excel(xl, sheet("Table5"))
    t6 = pd.read_excel(xl, sheet("Table6"))
    for d in (t2, t3, t4, t5):
        if "Type" in d.columns:
            d["Type"] = d["Type"].map(lambda v: SHORT.get(str(v), str(v)))
    t6 = t6.rename(columns={
        next(c for c in t6.columns if c.startswith("GCM main")): "GCM",
        next(c for c in t6.columns if c.startswith("BC-method")): "Method",
        next(c for c in t6.columns if c.startswith("Residual")): "Residual",
    })[["Scenario", "Index", "N cells", "GCMs", "GCM", "Method", "Residual"]]

    for name, d in (("T1design", t1), ("T2cal", t2), ("T3val", t3),
                    ("T4bulk", t4), ("T5ext", t5), ("T6decomp", t6)):
        d.to_json(HERE / f"{name}.json", orient="records")

    # Captions are extracted from the manuscript so the Word builder never
    # holds a second copy that can drift from the text.
    src_md = md.read_text(encoding="utf-8")
    caps = {}
    for kind in ("Table", "Figure"):
        for block in re.findall(rf"\*\*{kind} (\w+)\*\* (.+)", src_md):
            caps[f"{kind} {block[0]}"] = f"**{kind} {block[0]}** {block[1].strip()}"
    (HERE / "captions.json").write_text(json.dumps(caps, ensure_ascii=False),
                                        encoding="utf-8")

    (HERE / "paths.json").write_text(json.dumps({
        "src": str(src), "figdir": str(src / "figures"),
        "out": str(src / "Paper2_APST_manuscript_FINAL.docx"),
        "title": title, "keywords": keywords, "area": cfg.area,
    }), encoding="utf-8")
    print(f"prepared: abstract ({len(abstract.split())} words), "
          f"{len(secs)} blocks, 6 tables -> {HERE}")


if __name__ == "__main__":
    main()
