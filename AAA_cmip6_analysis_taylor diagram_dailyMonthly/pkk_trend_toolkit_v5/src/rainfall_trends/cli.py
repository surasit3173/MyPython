"""Command-line entry point."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .pipeline import PipelineError, run_analysis


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a fail-closed rainfall trend analysis")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        run_dir = run_analysis(args.config, args.output_root)
    except (ValueError, OSError, PipelineError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(run_dir)
    return 0
