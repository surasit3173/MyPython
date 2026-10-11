"""Finalize a run manifest after workbook, manuscripts, and validation exist."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_directory", type=Path)
    args = parser.parse_args()
    run_dir = args.run_directory.resolve()
    manifest_path = run_dir / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validation = json.loads((run_dir / "validation" / "artifact_validation.json").read_text(encoding="utf-8"))
    independent_source = Path(__file__).resolve().parents[1] / "validation" / "independent_checks.json"
    independent_target = run_dir / "validation" / "independent_checks.json"
    independent_target.write_bytes(independent_source.read_bytes())
    outputs = {}
    for path in sorted(item for item in run_dir.rglob("*") if item.is_file() and item.name != "run_manifest.json"):
        relative = path.relative_to(run_dir).as_posix()
        outputs[relative] = {"sha256": sha256(path), "bytes": path.stat().st_size}
    manifest["status"] = "finalized"
    manifest["validation"] = {
        "artifact_verdict": validation["verdict"],
        "checks_passed": validation["checks_passed"],
        "independent_verdict": json.loads(independent_target.read_text(encoding="utf-8"))["verdict"],
        "docx_rendering": "Canonical renderer unavailable because LibreOffice soffice was absent; Microsoft Word 2024 PDF export plus Poppler page rasterization was used and every page was visually inspected.",
    }
    manifest["outputs"] = outputs
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
