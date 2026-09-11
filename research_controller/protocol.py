"""
GitHub Communication Protocol and Run Manifest Module.
Defines standard machine-readable manifest and artifact structure.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


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
        if not project_id or not str(project_id).strip():
            raise ValueError("project_id is required and cannot be empty.")
        if not run_id or not str(run_id).strip():
            raise ValueError("run_id is required and cannot be empty.")

        self.project_id = str(project_id).strip()
        self.run_id = str(run_id).strip()
        self.parent_run_id = parent_run_id
        self.task_id = str(task_id).strip()
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
        run_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = run_dir / "RUN_MANIFEST.json"
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
    """
    # Sanitize project_id for directory structure
    clean_project = project_id.strip().replace("\\", "/").strip("/")
    run_dir = base_runs_dir / clean_project / run_id

    dirs = {
        "run_dir": run_dir,
        "analysis_results": run_dir / "ANALYSIS_RESULTS",
        "validation": run_dir / "VALIDATION",
        "review": run_dir / "REVIEW",
    }

    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    return dirs
