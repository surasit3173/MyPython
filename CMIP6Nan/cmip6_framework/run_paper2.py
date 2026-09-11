#!/usr/bin/env python3
"""Run the complete Paper 2 chain with one command.

    python run_paper2.py --config config/uttaradit.yaml

Paper 2 reuses the master result database that run_paper1.py's pipeline stage
produces, so run that first (or the `pipeline` stage of it) for a new area.
Stages:

    1  analysis   fair-comparison check, signal preservation, decomposition,
                  main and supplementary tables, six figures
    2  audit      semantic numerical audit of the manuscript against the tables
    3  docx       Word manuscript in APST format, with real Word equations
    4  assets     journal-ready figures and tables as standalone files

To analyse another area, change `area` and `paths` in the YAML and rerun. No
source file contains an area name, a station identifier or a year.
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
    ("analysis", "scripts/build_paper2_manuscript.py",
     "comparison, signal preservation, tables and figures"),
    ("audit", "scripts/audit_paper2.py",
     "semantic numerical audit of the manuscript"),
    ("docx", None, "Word manuscript in APST format"),
    ("supplement", None, "supplementary tables as a Word document"),
    ("assets", "scripts/export_publication_assets.py",
     "journal-ready figures and tables"),
]
NAMES = [s[0] for s in STAGES]


def sh(cmd, label, allow_fail=False) -> int:
    print(f"\n{'=' * 72}\n>> {label}\n   $ {' '.join(str(c) for c in cmd)}\n{'=' * 72}",
          flush=True)
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0 and not allow_fail:
        sys.exit(f"stage failed: {label}")
    return r.returncode


def build_docx(cfg: Path, journal: str) -> None:
    md = ROOT / "manuscript" / ("Paper2_APST_manuscript.md" if journal == "apst"
                                else "Paper2_AER_manuscript.md")
    if not md.exists():
        print(f"\n[docx] narrative not found at {md} - skipping")
        return
    node = shutil.which("node")
    if node is None:
        print("\n[docx] Node.js not found - skipping the Word build")
        return
    bdir = ROOT / ("docx_build_p2" if journal == "apst" else "docx_build_aer")
    if subprocess.run([node, "-e", "require.resolve('docx')"], cwd=bdir,
                      capture_output=True).returncode != 0:
        npm = shutil.which("npm")
        if npm is None or subprocess.run([npm, "install", "--silent"],
                                         cwd=bdir).returncode != 0:
            print("[docx] could not install the 'docx' package; skipping")
            return
    prep, build = (("prepare_p2.py", "build_p2.js") if journal == "apst"
                   else ("prepare_aer.py", "build_aer.js"))
    sh([sys.executable, str(bdir / prep), "--config", str(cfg)],
       "prepare manuscript text, tables and captions")
    sh([node, str(bdir / build)], f"render the {journal.upper()} Word document")


def main() -> None:
    ap = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter, description=__doc__)
    ap.add_argument("--config", default="config/uttaradit.yaml")
    ap.add_argument("--journal", default="apst", choices=["apst", "aer"],
                    help="target journal: sets the manuscript, figure width, "
                         "lettering size, page size and body point size")
    ap.add_argument("--figure1", default=None,
                    help="externally produced study-area map to adopt as Figure 1")
    ap.add_argument("--from", dest="start", choices=NAMES, default=NAMES[0])
    ap.add_argument("--only", choices=NAMES)
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
            build_docx(cfg, a.journal)
            continue
        if name == "supplement":
            sdir = ROOT / ("docx_build_p2" if a.journal == "apst"
                           else "docx_build_aer")
            sprep, sbuild = (("prepare_supplement.py", "build_supplement.js")
                             if a.journal == "apst"
                             else ("prepare_supplement_aer.py",
                                   "build_supplement_aer.js"))
            sh([sys.executable, str(sdir / sprep), "--config", str(cfg)],
               "prepare supplementary tables and data")
            node = shutil.which("node")
            if node:
                sh([node, str(sdir / sbuild)], label)
            else:
                print("[supplement] Node.js not found; the Word supplement was "
                      "not built")
            continue
        cmd = [sys.executable, script, "--config", str(cfg)]
        if name in ("analysis", "audit", "assets"):
            cmd += ["--journal", a.journal]
        if name == "analysis" and a.figure1:
            cmd += ["--figure1", a.figure1]
        if name == "assets":
            cmd += ["--paper", "paper2"]
        # the audit is a gate: it reports and exits non-zero, which should stop
        # the run rather than let a mismatched manuscript reach the Word build
        sh(cmd, label)

    print(f"\n{'=' * 72}\ndone in {time.time() - t0:.0f} s\n"
          f"outputs under: {cfg.parent.parent / 'output'}\n{'=' * 72}")


if __name__ == "__main__":
    main()
