#!/usr/bin/env python3
"""Prepare the Word build inputs from the manuscript markdown and result tables.

    python docx_build/prepare.py --config config/uttaradit.yaml

Writes abstract.txt, sections.json and the table JSON files that build.js reads.
Nothing here is area-specific: paths come from the configuration.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))
from cmip6bc.config import load_config                         # noqa: E402

EQ_PREFIXES = ("BC(*x*)", "MAB(*k*)", "Δ(%)")


def split_markdown(md_path: Path) -> tuple[str, list]:
    src = md_path.read_text(encoding="utf-8")
    abstract = src.split("## Abstract")[1].split("**Keywords")[0].strip()
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
        # convert HTML sub/sup markers before branching so equations get them too
        t = (line.strip().replace("<sub>", "~").replace("</sub>", "~")
                         .replace("<sup>", "^").replace("</sup>", "^"))
        secs.append({"t": "eq" if t.startswith(EQ_PREFIXES) else "p", "v": t})
    return abstract, secs


def compact_bias(df: pd.DataFrame) -> pd.DataFrame:
    keys = [c.replace(" |bias| (%)", "") for c in df.columns if "|bias|" in c]
    pick = lambda sim, k: float(df.loc[df.Simulation == sim, f"{k} |bias| (%)"].iloc[0])
    return pd.DataFrame({"Index": keys,
                         "Raw CMIP6": [round(pick("Raw CMIP6", k), 2) for k in keys],
                         "QDM-corrected": [round(pick("QDM-corrected", k), 2)
                                           for k in keys]})


def melt_change(df: pd.DataFrame) -> pd.DataFrame:
    """Table 4 arrives as index rows with one column group per scenario."""
    scen = sorted({c.split(" median (%)")[0] for c in df.columns
                   if c.endswith(" median (%)")})
    rows = []
    for _, r in df.iterrows():
        for sc in scen:
            rows.append({"Scenario": sc, "Index": r["Index"],
                         "Type": r.get("Type", "projection"),
                         "Median (%)": r[f"{sc} median (%)"],
                         "IQR (%)": r[f"{sc} IQR (%)"],
                         "Agreement": r[f"{sc} agreement"],
                         "Robust": r[f"{sc} robust"]})
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    a = ap.parse_args()
    cfg = load_config(a.config)
    src = cfg.path("output") / "paper1_manuscript"
    # The narrative is a SOURCE file kept under manuscript/; output/ is
    # regenerated on every run and must never hold hand-written text.
    md = ROOT / "manuscript" / "Paper1_APST_manuscript.md"
    if not md.exists():
        sys.exit(f"manuscript narrative not found: {md}\n"
                 "write the narrative there, or copy the template supplied "
                 "with the framework")
    if not (src / "Paper1_MAIN_Tables.xlsx").exists():
        sys.exit("main tables not found; run the 'manuscript' stage first")

    abstract, secs = split_markdown(md)
    (HERE / "abstract.txt").write_text(abstract, encoding="utf-8")
    (HERE / "sections.json").write_text(json.dumps(secs, ensure_ascii=False),
                                        encoding="utf-8")

    xl = pd.ExcelFile(src / "Paper1_MAIN_Tables.xlsx")
    sheet = lambda pref: next(s for s in xl.sheet_names if s.startswith(pref))
    out = {
        "T1": pd.read_excel(xl, sheet("Table1")),
        "T2": compact_bias(pd.read_excel(xl, sheet("Table3_cal"))),
        "T3": compact_bias(pd.read_excel(xl, sheet("Table4_val"))),
        "T2models": pd.read_excel(xl, sheet("Table2_cmip6")),
        "T4": melt_change(pd.read_excel(xl, sheet("Table5_near"))),
    }
    for k, v in out.items():
        v.to_json(HERE / f"{k}.json", orient="records")

    (HERE / "paths.json").write_text(json.dumps({
        "src": str(src), "figdir": str(src / "figures"),
        "out": str(src / "Paper1_APST_manuscript.docx"),
        "area": cfg.area,
    }), encoding="utf-8")
    print(f"prepared: abstract ({len(abstract.split())} words), "
          f"{len(secs)} blocks, {len(out)} tables -> {HERE}")


if __name__ == "__main__":
    main()
