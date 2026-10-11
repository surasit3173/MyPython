"""Command-line interface.

Usage
-----
python -m etoeval.cli stage1   --config config.yaml
python -m etoeval.cli download --config config.yaml [--years 1979 2007] [--dry-run]
python -m etoeval.cli extract  --config config.yaml
python -m etoeval.cli stage2   --config config.yaml
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from . import agera5
from .data import load_config
from .pipeline import run_stage1, run_stage2


def main(argv: list[str] | None = None) -> None:
    """Entry point."""
    ap = argparse.ArgumentParser(prog="etoeval")
    ap.add_argument("command", choices=["stage1", "download", "extract", "stage2"])
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--years", nargs=2, type=int, default=None, help="first and last year to download")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--n-sim", type=int, default=5000, help="Monte Carlo replicates for SNHT")
    ap.add_argument("--n-mc", type=int, default=500, help="Monte Carlo samples for error propagation")
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    cfg.out_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(cfg.out_dir / "pipeline.log", encoding="utf-8")],
    )
    root = Path(args.config).resolve().parent
    extract_file = root / str(cfg.agera5["extract_file"])
    if args.command == "stage1":
        run_stage1(cfg, n_sim=args.n_sim)
    elif args.command == "download":
        y0, y1 = args.years or (cfg.start_year, cfg.end_year)
        status = agera5.download(cfg, list(range(y0, y1 + 1)), dry_run=args.dry_run)
        print(status.groupby("status").size())
    elif args.command == "extract":
        daily = agera5.extract_station_daily(cfg)
        extract_file.parent.mkdir(parents=True, exist_ok=True)
        daily.to_csv(extract_file, index=False)
        print(f"Wrote {len(daily)} rows to {extract_file}")
    else:
        daily = pd.read_csv(extract_file, parse_dates=["date"])
        run_stage2(cfg, daily, n_mc=args.n_mc)


if __name__ == "__main__":
    main()
