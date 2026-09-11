"""
provenance.py — audit trail for every transformation applied to the data.

Records file hashes, library versions, unit conversions, clipped negatives,
NoData replacements, calendar types and paired-sample sizes so that any
number in the manuscript can be traced back to a specific input byte-stream.
"""
from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import scipy


def sha256_file(path: str | Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


class Provenance:
    """Accumulates a structured record; written once at the end of a stage."""

    def __init__(self, config: dict, config_path: str | Path | None = None):
        self.record: dict[str, Any] = {
            "run": {
                "utc_timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "python": sys.version.split()[0],
                "platform": platform.platform(),
                "numpy": np.__version__,
                "pandas": pd.__version__,
                "scipy": scipy.__version__,
                "random_seed": config.get("reproducibility", {}).get("random_seed"),
            },
            "config": config,
            "config_file": {},
            "inputs": {},
            "stations": {},
            "transformations": {},
            "calendars": {},
            "sample_sizes": {},
            "qdm": {},
            "warnings": [],
        }
        if config_path and Path(config_path).is_file():
            self.record["config_file"] = {
                "path": str(config_path),
                "sha256": sha256_file(config_path),
            }

    # ── recording helpers ────────────────────────────────────────────────
    def add_input(self, key: str, path: str | Path, **extra) -> None:
        p = Path(path)
        self.record["inputs"][key] = {
            "path": str(p),
            "filename": p.name,
            "bytes": p.stat().st_size,
            "sha256": sha256_file(p),
            **extra,
        }

    def add_transformation(self, key: str, **fields) -> None:
        self.record["transformations"].setdefault(key, {}).update(fields)

    def add_calendar(self, key: str, **fields) -> None:
        self.record["calendars"][key] = fields

    def add_sample_size(self, key: str, **fields) -> None:
        self.record["sample_sizes"][key] = fields

    def set(self, section: str, value: Any) -> None:
        self.record[section] = value

    def warn(self, message: str) -> None:
        self.record["warnings"].append(message)
        print(f"    [warn] {message}")

    # ── output ───────────────────────────────────────────────────────────
    def write(self, out_dir: str | Path, stem: str = "provenance") -> Path:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        jpath = out_dir / f"{stem}.json"
        with open(jpath, "w", encoding="utf-8") as fh:
            json.dump(self.record, fh, indent=2, ensure_ascii=False, default=str)
        self._write_readable(out_dir / f"{stem}.txt")
        return jpath

    def _write_readable(self, path: Path) -> None:
        r = self.record
        L: list[str] = []
        add = L.append
        add("=" * 78)
        add("  PROVENANCE RECORD")
        add("=" * 78)
        add(f"  run (UTC)  : {r['run']['utc_timestamp']}")
        add(f"  python     : {r['run']['python']}   numpy {r['run']['numpy']}  "
            f"pandas {r['run']['pandas']}  scipy {r['run']['scipy']}")
        add(f"  seed       : {r['run']['random_seed']}")
        if r["config_file"]:
            add(f"  config     : {r['config_file']['path']}")
            add(f"               sha256 {r['config_file']['sha256'][:16]}...")
        add("")
        add("-" * 78)
        add("  INPUT FILES")
        add("-" * 78)
        for k, v in r["inputs"].items():
            add(f"  {k}")
            add(f"    file   : {v['filename']}  ({v['bytes']:,} bytes)")
            add(f"    sha256 : {v['sha256']}")
        add("")
        if r["transformations"]:
            add("-" * 78)
            add("  TRANSFORMATIONS APPLIED")
            add("-" * 78)
            for k, v in r["transformations"].items():
                add(f"  {k}")
                for kk, vv in v.items():
                    add(f"    {kk:28s}: {vv}")
            add("")
        if r["calendars"]:
            add("-" * 78)
            add("  CALENDARS")
            add("-" * 78)
            for k, v in r["calendars"].items():
                add(f"  {k:20s} {v}")
            add("")
        if r["sample_sizes"]:
            add("-" * 78)
            add("  SAMPLE SIZES")
            add("-" * 78)
            for k, v in r["sample_sizes"].items():
                add(f"  {k:20s} {v}")
            add("")
        if r["warnings"]:
            add("-" * 78)
            add("  WARNINGS")
            add("-" * 78)
            for w in r["warnings"]:
                add(f"  ! {w}")
            add("")
        add("=" * 78)
        path.write_text("\n".join(L), encoding="utf-8")
