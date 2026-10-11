from __future__ import annotations

from pathlib import Path
import sys

PACKAGE_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from rainfall_trends.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
