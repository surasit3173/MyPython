"""Configuration loading and run provenance.

Every area-specific value lives in the YAML file. No module in this package
contains a province name, a station identifier, or a hard-coded year.
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml


@dataclass
class Config:
    raw: dict
    root: Path

    # ---- convenience accessors -------------------------------------------
    @property
    def area(self) -> str:
        return self.raw["area"]["name"]

    @property
    def seed(self) -> int:
        return int(self.raw.get("seed", 0))

    def path(self, key: str) -> Path:
        p = Path(self.raw["paths"][key])
        return p if p.is_absolute() else self.root / p

    def period(self, key: str):
        return tuple(self.raw["periods"][key])

    @property
    def future_windows(self) -> dict:
        return {k: tuple(v) for k, v in self.raw["periods"]["future"].items()}

    @property
    def bc(self) -> dict:
        return self.raw["bias_correction"]

    @property
    def wet_thr(self) -> float:
        return float(self.bc["wet_day_threshold_mm"])

    @property
    def methods(self) -> list:
        return list(self.bc["methods"])

    @property
    def scenarios(self) -> list:
        return list(self.raw["scenarios"])

    @property
    def index_set(self) -> list:
        return list(self.raw["indices"]["set"])

    @property
    def agreement_threshold(self) -> float:
        return float(self.raw["ensemble"]["agreement_threshold"])

    def out(self, *parts) -> Path:
        p = self.path("output").joinpath(*parts)
        p.mkdir(parents=True, exist_ok=True)
        return p


def load_config(path) -> Config:
    path = Path(path)
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return Config(raw=raw, root=path.resolve().parent.parent)


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------
def file_hash(path, algo: str = "sha256") -> str:
    h = hashlib.new(algo)
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return f"{algo}:{h.hexdigest()}"


def package_versions() -> dict:
    out = {"python": sys.version.split()[0], "platform": platform.platform()}
    for mod in ("numpy", "pandas", "scipy", "matplotlib", "yaml", "xlsxwriter"):
        try:
            out[mod] = __import__(mod).__version__
        except Exception:
            out[mod] = "not installed"
    return out


def git_commit(root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return "not a git repository"


@dataclass
class Manifest:
    cfg: Config
    entries: dict = field(default_factory=dict)
    inputs: dict = field(default_factory=dict)

    def add_input(self, label: str, path) -> None:
        p = Path(path)
        self.inputs[label] = {"file": p.name, "path": str(p),
                              "bytes": p.stat().st_size, "hash": file_hash(p)}

    def add(self, key: str, value) -> None:
        self.entries[key] = value

    def write(self, path) -> Path:
        doc = {
            "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "area": self.cfg.area,
            "config": self.cfg.raw,
            "code_version": git_commit(self.cfg.root),
            "environment": package_versions(),
            "seed": self.cfg.seed,
            "inputs": self.inputs,
            "stages": self.entries,
        }
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, indent=2, ensure_ascii=False,
                                   default=str), encoding="utf-8")
        return path
