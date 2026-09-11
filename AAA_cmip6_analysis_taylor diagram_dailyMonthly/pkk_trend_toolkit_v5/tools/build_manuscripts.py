from __future__ import annotations

import argparse
from pathlib import Path
import sys

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from rainfall_trends.manuscripts import generate_manuscripts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_directory", type=Path)
    args = parser.parse_args()
    for output in generate_manuscripts(args.run_directory):
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
