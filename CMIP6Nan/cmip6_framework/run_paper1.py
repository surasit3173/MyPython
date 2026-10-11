#!/usr/bin/env python3
"""Run the complete Paper 1 chain with one command.

    python run_paper1.py --config config/uttaradit.yaml

Stages, in order, each skippable with --from / --only:

    1  gate_f      resolve and verify the administrative boundary
    2  gate_h      trace the raw model series for input anomalies
    3  pipeline    QC, fit-freeze-apply, indices, ensemble, acceptance gates
    4  trace       diagnostic trace of any flagged scenario-horizon
    5  manuscript  locked main tables, supplementary tables, six figures
    6  finalize    gate status workbook, interpretation scope, SHA-256 manifest
    7  docx        Word manuscript in APST format (needs Node.js)

Every stage reads the same YAML. To analyse another province, copy the YAML,
change `area` and `paths`, and run this file again. No source file contains a
province name, a station identifier or a year.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

STAGES = [
    ("gate_f", "scripts/gate_f_boundary.py",
     "resolve and verify the administrative boundary (Gate F)"),
    ("gate_h", "scripts/gate_h_source_trace.py",
     "trace the raw model series for input anomalies (Gate H)"),
    ("pipeline", "scripts/run_pipeline.py",
     "observed QC, fit-freeze-apply, indices, ensemble, acceptance gates"),
    ("trace", "scripts/trace_raw_anomaly.py",
     "diagnostic trace of a flagged scenario-horizon"),
    ("manuscript", "scripts/build_paper1_manuscript.py",
     "locked manuscript tables and figures"),
    ("finalize", "scripts/finalize.py",
     "gate status, interpretation scope, SHA-256 manifest"),
    ("docx", None, "Word manuscript in APST format"),
    ("assets", "scripts/export_publication_assets.py",
     "journal-ready figures and tables as standalone publication assets"),
]
NAMES = [s[0] for s in STAGES]


def sh(cmd: list[str], label: str) -> None:
    print(f"\n{'=' * 72}\n>> {label}\n   $ {' '.join(cmd)}\n{'=' * 72}", flush=True)
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        sys.exit(f"stage failed: {label}")


def build_docx(cfg_path: Path, figure1: Path | None) -> None:
    md = ROOT / "manuscript" / "Paper1_APST_manuscript.md"
    if not md.exists():
        print(f"\n[docx] narrative not found at {md} - skipping the Word build")
        return
    node = shutil.which("node")
    if node is None:
        print("\n[docx] Node.js not found - skipping the Word build.\n"
              "       Install Node 18+ and rerun with --only docx.")
        return
    bdir = ROOT / "docx_build"
    probe = subprocess.run([node, "-e", "require.resolve('docx')"], cwd=bdir,
                           capture_output=True)
    if probe.returncode != 0:
        print("[docx] installing the 'docx' package ...")
        npm = shutil.which("npm")
        if npm is None:
            print("[docx] npm not found; skipping the Word build")
            return
        if subprocess.run([npm, "install", "--silent"], cwd=bdir).returncode != 0:
            print("[docx] npm install failed; skipping the Word build")
            return
    sh([sys.executable, str(bdir / "prepare.py"), "--config", str(cfg_path)],
       "prepare manuscript text and tables for the Word build")
    sh([node, str(bdir / "build.js")], "render the APST Word document")


def main() -> None:
    ap = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__)
    ap.add_argument("--config", default="config/uttaradit.yaml")
    ap.add_argument("--figure1", default=None,
                    help="externally produced study-area map to adopt as Figure 1")
    ap.add_argument("--from", dest="start", choices=NAMES, default=NAMES[0],
                    help="start at this stage")
    ap.add_argument("--only", choices=NAMES, help="run this stage alone")
    ap.add_argument("--scenario", default=None,
                    help="scenario for the anomaly trace (default: last in config)")
    a = ap.parse_args()

    cfg = (ROOT / a.config) if not Path(a.config).is_absolute() else Path(a.config)
    if not cfg.exists():
        sys.exit(f"configuration not found: {cfg}")

    todo = [a.only] if a.only else NAMES[NAMES.index(a.start):]
    t0 = time.time()
    for name, script, label in STAGES:
        if name not in todo:
            continue
        if name == "docx":
            build_docx(cfg, Path(a.figure1) if a.figure1 else None)
            continue
        cmd = [sys.executable, script, "--config", str(cfg)]
        if name == "assets":
            cmd += ["--paper", "paper1"]
        if name == "manuscript" and a.figure1:
            cmd += ["--figure1", a.figure1]
        if name == "trace" and a.scenario:
            cmd += ["--scenario", a.scenario]
        sh(cmd, label)

    print(f"\n{'=' * 72}\ndone in {time.time() - t0:.0f} s\n"
          f"outputs under: {cfg.parent.parent / 'output'}\n{'=' * 72}")


if __name__ == "__main__":
    main()
