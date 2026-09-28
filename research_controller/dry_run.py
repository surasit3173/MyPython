#!/usr/bin/env python3
"""
Deterministic Offline Dry-Run Script for Research Controller.
Demonstrates the complete multi-agent workflow:
1. Project selected
2. Task created
3. Jules result simulated
4. Validation performed
5. AI review simulated
6. Review written to GitHub artifact structure
7. Decision generated
8. Next Jules task specification generated

Does NOT modify any scientific project.
"""

import json
import sys
import tempfile
from pathlib import Path

# Add controller directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ai_reviewer import MockReviewer
from protocol import prepare_run_directory
from state_machine import ResearchWorkflowRunner


def run_dry_run(
    project_id: str = "CMIP6Lampang",
    runs_base_dir: Path | None = None,
) -> dict:
    if runs_base_dir is None:
        runs_base_dir = Path(__file__).resolve().parent / "runs"

    print("==================================================")
    print("STARTING DETERMINISTIC OFFLINE DRY-RUN")
    print("==================================================")
    print(f"1. Selected Project: {project_id}")

    # Resolve project path safely without requiring actual scientific execution
    repo_root = Path(__file__).resolve().parents[1]
    project_path = repo_root / project_id
    if not project_path.exists():
        # Use research_controller as fallback fixture project for dry-run
        project_path = Path(__file__).resolve().parent

    run_id = f"{project_id}_DRYRUN_TEST"

    # 2. Task specification created
    task_spec = {
        "purpose": "Publication-readiness audit for dry-run verification.",
        "allowed_actions": ["read project files", "validate numerical consistency"],
        "forbidden_actions": ["fabricate missing results", "alter raw data"],
        "stop_conditions": ["evidence conflict", "authoritative data missing"],
    }
    print(f"2. Created Task Specification: {task_spec['purpose']}")

    # Initialize workflow runner with Mock Jules & Mock AI Reviewer
    reviewer = MockReviewer(
        preset_status="PASS",
        preset_findings="All dry-run simulated artifacts verified successfully. Zero scientific contradictions found.",
    )
    runner = ResearchWorkflowRunner(
        base_runs_dir=runs_base_dir,
        reviewer=reviewer,
        mock_jules=True,
    )

    print("3. Simulating Jules Execution...")
    print("4. Executing Validation Gates...")
    print("5. Simulating AI Review...")
    print("6. Writing Review to GitHub Artifact Hierarchy...")

    res = runner.execute_workflow(
        project_id=project_id,
        project_path=project_path,
        run_id=run_id,
        task_spec=task_spec,
        target="Q2",
        mode="FULL",
        autonomous=True,
    )

    run_dirs = prepare_run_directory(runs_base_dir, project_id, run_id)
    run_dir = run_dirs["run_dir"]

    print("7. Decision Generated:")
    print(f"   Status: {res.get('status')}")
    print(f"   Artifact Directory: {run_dir}")

    # 8. Generate Next Task Specification
    next_task_spec = {
        "parent_run_id": run_id,
        "project_id": project_id,
        "action": "PROCEED_TO_MANUSCRIPT_FINALIZATION",
        "restrictions": ["Do not modify frozen numerical outputs."],
    }
    next_spec_path = run_dir / "NEXT_TASK_SPECIFICATION.json"
    next_spec_path.write_text(
        json.dumps(next_task_spec, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"8. Next Jules Task Specification Generated: {next_spec_path}")

    # Verify generated artifact structure
    expected_artifacts = [
        "RUN_MANIFEST.json",
        "STATE.json",
        "TASK_SPECIFICATION.md",
        "JULES_RESULT.md",
        "JULES_LOG.jsonl",
        "FINAL_STATUS.md",
        "NEXT_TASK_SPECIFICATION.json",
        "REVIEW/CHATGPT_REVIEW.json",
        "REVIEW/CHATGPT_REVIEW.md",
    ]

    missing = []
    for art in expected_artifacts:
        p = run_dir / art
        if not p.exists():
            missing.append(art)

    if missing:
        raise RuntimeError(f"Dry-run failed: missing artifacts {missing}")

    print("==================================================")
    print("DRY-RUN COMPLETED SUCCESSFULLY WITH ALL ARTIFACTS VERIFIED")
    print("==================================================")

    return res


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmpdir:
        res = run_dry_run(runs_base_dir=Path(tmpdir))
        if res.get("status") != "PASS":
            sys.exit(1)
