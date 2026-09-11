from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

import pandas as pd

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "src"))
os.environ.setdefault("MPLCONFIGDIR", str(PACKAGE_ROOT / ".matplotlib_cache"))

from rainfall_trends.plots import create_all_figures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_directory", type=Path)
    args = parser.parse_args()
    run_dir = args.run_directory.resolve()
    tables = run_dir / "tables"
    read = lambda name: pd.read_csv(tables / name, encoding="utf-8-sig")
    create_all_figures(
        run_dir / "figures",
        metadata=read("station_metadata.csv"),
        network_series=read("network_series.csv"),
        network_results=read("network_results.csv"),
        station_results=read("station_results.csv"),
        bootstrap=read("bootstrap_ci.csv"),
        method_simulation=read("method_simulation.csv"),
        fdr_simulation=read("fdr_simulation.csv"),
        alpha=0.05,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
