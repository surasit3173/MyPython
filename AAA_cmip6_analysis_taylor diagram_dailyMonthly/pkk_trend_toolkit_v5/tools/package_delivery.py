"""Create a portable ZIP without local caches or dependency junctions."""

from __future__ import annotations

import argparse
from pathlib import Path
import zipfile


EXCLUDED_PARTS = {"node_modules", "__pycache__", ".pytest_cache", ".matplotlib_cache"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package_root", type=Path)
    parser.add_argument("output_zip", type=Path)
    args = parser.parse_args()
    root = args.package_root.resolve()
    output = args.output_zip.resolve()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source in sorted(item for item in root.rglob("*") if item.is_file()):
            if source == output or any(part in EXCLUDED_PARTS for part in source.relative_to(root).parts):
                continue
            archive.write(source, Path(root.name) / source.relative_to(root))
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
