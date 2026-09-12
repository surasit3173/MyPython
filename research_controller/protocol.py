"""
GitHub Communication Protocol and Run Manifest Module.
Defines standard machine-readable manifest and artifact structure with strict path isolation.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class ArtifactPathError(ValueError):
    """Raised when an artifact or run path violates path isolation rules."""
    pass


def validate_path_component(component: Any, name: str) -> str:
    """
    Strictly validates a project_id or run_id path component.
    FAIL-CLOSED:
    - Rejects non-string, empty, or whitespace-only inputs.
    - Rejects absolute paths, Windows drive letters (C:), leading/trailing slashes.
    - Rejects path traversal vectors ('..', '.').
    - Rejects backslashes.
    """
    if not isinstance(component, str) or not component.strip():
        raise ArtifactPathError(f"FAIL-CLOSED: {name} must be a non-empty string.")

    s = component.strip()

    # Reject absolute path indicators (slash, backslash, drive letters)
    if s.startswith("/") or s.startswith("\\") or re.match(r"^[a-zA-Z]:", s):
        raise ArtifactPathError(f"FAIL-CLOSED: {name} cannot be an absolute path: '{component}'")

    # Reject backslashes
    if "\\" in s:
        raise ArtifactPathError(f"FAIL-CLOSED: {name} contains invalid character '\\': '{component}'")

    # Reject leading/trailing slashes or empty components in multi-part paths
    if s.startswith("/") or s.endswith("/"):
        raise ArtifactPathError(f"FAIL-CLOSED: {name} cannot have leading or trailing slashes: '{component}'")

    parts = s.split("/")
    for part in parts:
        if part in ("", ".", ".."):
            raise ArtifactPathError(f"FAIL-CLOSED: {name} contains path traversal or invalid component '{part}': '{component}'")

    return s


class RunManifest:
    """
    Standard machine-readable run manifest following GitHub artifact protocol.
    """

    def __init__(
        self,
        project_id: str,
        run_id: str,
        task_id: str,
        agent: str = "Jules",
        parent_run_id: Optional[str] = None,
        git_commit: Optional[str] = None,
        status: str = "INIT",
        input_artifacts: Optional[List[str]] = None,
        output_artifacts: Optional[List[str]] = None,
        validation_status: Optional[Dict[str, Any]] = None,
        review_status: Optional[Dict[str, Any]] = None,
        next_action: str = "SPEC_VALIDATION",
    ):
        self.project_id = validate_path_component(project_id, "project_id")
        self.run_id = validate_path_component(run_id, "run_id")
        self.parent_run_id = parent_run_id
        self.task_id = str(task_id).strip() if task_id else "default_task"
        self.agent = agent
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.git_commit = git_commit
        self.status = status
        self.input_artifacts = input_artifacts or []
        self.output_artifacts = output_artifacts or []
        self.validation_status = validation_status or {}
        self.review_status = review_status or {}
        self.next_action = next_action

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "run_id": self.run_id,
            "parent_run_id": self.parent_run_id,
            "task_id": self.task_id,
            "agent": self.agent,
            "timestamp": self.timestamp,
            "git_commit": self.git_commit,
            "status": self.status,
            "input_artifacts": self.input_artifacts,
            "output_artifacts": self.output_artifacts,
            "validation_status": self.validation_status,
            "review_status": self.review_status,
            "next_action": self.next_action,
        }

    def save(self, run_dir: Path) -> Path:
        resolved_run_dir = Path(run_dir).resolve()
        resolved_run_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = resolved_run_dir / "RUN_MANIFEST.json"
        manifest_path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return manifest_path

    @classmethod
    def load(cls, manifest_path: Path) -> "RunManifest":
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest = cls(
            project_id=data["project_id"],
            run_id=data["run_id"],
            task_id=data.get("task_id", "default_task"),
            agent=data.get("agent", "Jules"),
            parent_run_id=data.get("parent_run_id"),
            git_commit=data.get("git_commit"),
            status=data.get("status", "INIT"),
            input_artifacts=data.get("input_artifacts", []),
            output_artifacts=data.get("output_artifacts", []),
            validation_status=data.get("validation_status", {}),
            review_status=data.get("review_status", {}),
            next_action=data.get("next_action", "SPEC_VALIDATION"),
        )
        manifest.timestamp = data.get("timestamp", manifest.timestamp)
        return manifest


def prepare_run_directory(base_runs_dir: Path, project_id: str, run_id: str) -> Dict[str, Path]:
    """
    Creates and returns paths for the structured artifact hierarchy:
    runs/<project>/<run_id>/
        TASK_SPECIFICATION.md
        RUN_MANIFEST.json
        JULES_RESULT.md
        JULES_LOG.jsonl
        ANALYSIS_RESULTS/
        VALIDATION/
        REVIEW/
        FINAL_STATUS.md

    FAIL-CLOSED:
    - Validates project_id and run_id.
    - Resolves base_runs_dir and target run_dir to canonical paths.
    - Verifies run_dir is strictly contained within base_runs_dir.
    """
    valid_project = validate_path_component(project_id, "project_id")
    valid_run = validate_path_component(run_id, "run_id")

    base_runs_path = Path(base_runs_dir)
    base_runs_path.mkdir(parents=True, exist_ok=True)
    resolved_base = base_runs_path.resolve()

    target_path = resolved_base.joinpath(*valid_project.split("/"), valid_run)
    resolved_target = target_path.resolve()

    try:
        resolved_target.relative_to(resolved_base)
    except ValueError:
        raise ArtifactPathError(
            f"FAIL-CLOSED: Target run directory '{resolved_target}' is outside base runs directory '{resolved_base}'."
        )

    if resolved_target == resolved_base:
        raise ArtifactPathError("FAIL-CLOSED: Target run directory cannot be the base runs directory itself.")

    dirs = {
        "run_dir": resolved_target,
        "analysis_results": resolved_target / "ANALYSIS_RESULTS",
        "validation": resolved_target / "VALIDATION",
        "review": resolved_target / "REVIEW",
    }

    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    return dirs
