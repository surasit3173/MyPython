"""
run_all.py — run the whole pipeline end to end.

    python run_all.py --config config.yaml

Stages, in order:

    1  run.py            io_layer -> QC gate 1 -> qdm_core -> QC gate 2
    2  test_leakage.py   experimental proof that the split-sample holds
    3  evaluate.py       primary analysis + three sensitivity analyses
    4  figures.py        Figures 3-7 at publication resolution

Any stage can also be run on its own; each reads only files that earlier
stages wrote, so re-running a later stage never silently uses stale inputs
from a different configuration.

Use --skip-leakage only when re-running after a change that cannot affect
the correction (for example a change to figure styling).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

STAGES = [
    ("1/4  correction   ", "run.py"),
    ("2/4  leakage audit", "test_leakage.py"),
    ("3/4  evaluation   ", "evaluate.py"),
    ("4/4  figures      ", "figures.py"),
]
SEP = "=" * 78


def check_environment() -> bool:
    ok = True
    need = {"numpy": "numpy", "pandas": "pandas", "scipy": "scipy",
            "yaml": "PyYAML", "matplotlib": "matplotlib",
            "openpyxl": "openpyxl"}
    missing = []
    for mod, pkg in need.items():
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"  missing packages: {', '.join(missing)}")
        print(f"  install with: pip install {' '.join(missing)}")
        ok = False
    if sys.version_info < (3, 9):
        print(f"  python {sys.version.split()[0]} is too old; 3.9 or newer required")
        ok = False
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--skip-leakage", action="store_true",
                    help="skip the leakage audit (only when the correction "
                         "cannot have changed)")
    args = ap.parse_args()

    here = Path(__file__).resolve().parent
    cfg = Path(args.config)
    if not cfg.is_absolute():
        cfg = here / cfg
    if not cfg.is_file():
        print(f"config not found: {cfg}")
        return 1

    print(SEP)
    print("  cmip6bc — full pipeline")
    print(f"  config: {cfg}")
    print(SEP)
    if not check_environment():
        return 1

    t0 = time.time()
    for label, script in STAGES:
        if args.skip_leakage and script == "test_leakage.py":
            print(f"\n  {label}  skipped by request")
            continue
        print(f"\n  {label}  {script}")
        t = time.time()
        r = subprocess.run([sys.executable, str(here / script),
                            "--config", str(cfg)], cwd=here)
        if r.returncode != 0:
            print(f"\n  stage failed: {script} (exit {r.returncode})")
            return r.returncode
        print(f"  {label}  done in {time.time() - t:.1f} s")

    import yaml
    out = Path(yaml.safe_load(open(cfg, encoding="utf-8"))["paths"]["out_dir"])
    if not out.is_absolute():
        out = here / out
    print("\n" + SEP)
    print(f"  complete in {time.time() - t0:.1f} s")
    print(SEP)
    for line in (
        f"  corrected series   {out / 'bc_split'}",
        f"  station tiers      {out / 'qc_station_tiers.csv'}",
        f"  fit diagnostics    {out / 'qdm_fit_diagnostics.csv'}",
        f"  results workbook   {out / 'evaluation_results.xlsx'}",
        f"  figures            {out / 'figures'}",
        f"  provenance         {out / 'provenance.txt'}",
    ):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
