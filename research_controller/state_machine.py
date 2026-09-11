"""
State Machine & Workflow Controller Engine.
Drives the multi-agent execution loop with persistent state machine, crash recovery, and human review gates.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ai_reviewer import AIReviewer, MockReviewer
from jules_adapter import JulesAdapter
from protocol import RunManifest, prepare_run_directory
from validation_gates import run_all_validation_gates

# List of sensitive scientific keys requiring HUMAN_REVIEW gate authorization
HUMAN_GATE_TRIGGERS = [
    "change_scientific_definitions",
    "change_dataset",
    "change_station_inventory",
    "change_model_inventory",
    "change_scenarios",
    "change_baseline",
    "change_statistical_methodology",
    "change_thresholds",
    "change_interpretation",
    "change_manuscript_claims",
]


class ResearchWorkflowRunner:
    """
    State machine runner that manages task execution, validation, review, correction, and resumption.
    """

    def __init__(
        self,
        base_runs_dir: Path,
        reviewer: Optional[AIReviewer] = None,
        mock_jules: bool = False,
    ):
        self.base_runs_dir = base_runs_dir
        self.reviewer = reviewer or MockReviewer()
        self.jules_adapter = JulesAdapter(mock=mock_jules)

    def is_human_review_required(self, spec: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Intercepts scientific methodology or structural modifications.
        """
        triggers = []
        spec_text = json.dumps(spec).lower()
        for trigger in HUMAN_GATE_TRIGGERS:
            if trigger in spec_text or spec.get(trigger) is True:
                triggers.append(trigger)

        # Check if spec explicitly flags human review
        if spec.get("requires_human_review") or spec.get("methodology_changed"):
            triggers.append("explicit_spec_flag")

        return (len(triggers) > 0, triggers)

    def load_or_create_state(
        self,
        project_id: str,
        run_id: str,
        task_id: str = "task_01",
        resume: bool = False,
    ) -> Tuple[Dict[str, Path], RunManifest, Dict[str, Any]]:
        """
        Loads state from disk if run already exists and resume=True (crash recovery), or initializes a new run.
        """
        run_dirs = prepare_run_directory(self.base_runs_dir, project_id, run_id)
        state_file = run_dirs["run_dir"] / "STATE.json"
        manifest_file = run_dirs["run_dir"] / "RUN_MANIFEST.json"

        if resume and state_file.exists() and manifest_file.exists():
            manifest = RunManifest.load(manifest_file)
            state_data = json.loads(state_file.read_text(encoding="utf-8"))
        else:
            manifest = RunManifest(
                project_id=project_id,
                run_id=run_id,
                task_id=task_id,
                status="INIT",
                next_action="SPEC_VALIDATION",
            )
            state_data = {
                "project_id": project_id,
                "run_id": run_id,
                "current_state": "INIT",
                "completed_states": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self.persist_state(run_dirs, manifest, state_data)

        return run_dirs, manifest, state_data

    def persist_state(
        self,
        run_dirs: Dict[str, Path],
        manifest: RunManifest,
        state_data: Dict[str, Any],
    ):
        """
        Saves both RUN_MANIFEST.json and STATE.json.
        """
        manifest.save(run_dirs["run_dir"])
        state_file = run_dirs["run_dir"] / "STATE.json"
        state_file.write_text(
            json.dumps(state_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def execute_workflow(
        self,
        project_id: str,
        project_path: Path,
        run_id: str,
        task_spec: Dict[str, Any],
        target: str = "Q2",
        mode: str = "FULL",
        autonomous: bool = False,
        timeout: str = "30m",
        resume: bool = False,
    ) -> Dict[str, Any]:
        """
        Main execution loop driving the state machine through all stages.
        """
        run_dirs, manifest, state_data = self.load_or_create_state(project_id, run_id, resume=resume)

        # 1. SPEC_VALIDATION
        if state_data["current_state"] in ("INIT", "SPEC_VALIDATION"):
            needs_human, triggers = self.is_human_review_required(task_spec)
            if needs_human:
                manifest.status = "NEEDS_HUMAN_REVIEW"
                manifest.next_action = "HUMAN_REVIEW"
                state_data["current_state"] = "HUMAN_REVIEW"
                state_data["human_review_triggers"] = triggers
                self.persist_state(run_dirs, manifest, state_data)

                # Save FINAL_STATUS.md
                (run_dirs["run_dir"] / "FINAL_STATUS.md").write_text(
                    f"# Final Run Status: NEEDS_HUMAN_REVIEW\n\nMethodology/scientific change detected: {triggers}\nRequires explicit human authorization.",
                    encoding="utf-8",
                )
                return {
                    "status": "NEEDS_HUMAN_REVIEW",
                    "reason": f"Human gate triggered due to: {triggers}",
                    "run_dir": str(run_dirs["run_dir"]),
                }

            state_data["completed_states"].append("SPEC_VALIDATION")
            state_data["current_state"] = "JULES_EXECUTION"
            manifest.status = "RUNNING"
            manifest.next_action = "JULES_EXECUTION"
            self.persist_state(run_dirs, manifest, state_data)

        # 2. JULES_EXECUTION
        if state_data["current_state"] == "JULES_EXECUTION":
            jules_res = self.jules_adapter.execute_jules_task(
                project_path=project_path,
                target=target,
                mode=mode,
                spec=task_spec,
                run_id=run_id,
                run_dirs=run_dirs,
                autonomous=autonomous,
                timeout=timeout,
            )
            state_data["jules_result"] = jules_res
            state_data["completed_states"].append("JULES_EXECUTION")
            state_data["current_state"] = "JULES_VALIDATION"
            manifest.next_action = "JULES_VALIDATION"
            self.persist_state(run_dirs, manifest, state_data)

        # 3. JULES_VALIDATION
        if state_data["current_state"] == "JULES_VALIDATION":
            jules_res = state_data.get("jules_result", {})
            jules_status = jules_res.get("status")

            if jules_status in ("TIMEOUT", "HOLD", "FAIL"):
                state_data["current_state"] = jules_status
                manifest.status = jules_status
                manifest.next_action = "NONE"
                self.persist_state(run_dirs, manifest, state_data)
                (run_dirs["run_dir"] / "FINAL_STATUS.md").write_text(
                    f"# Final Run Status: {jules_status}\n\nJules execution reported status {jules_status}.",
                    encoding="utf-8",
                )
                return {
                    "status": jules_status,
                    "jules_result": jules_res,
                    "run_dir": str(run_dirs["run_dir"]),
                }

            val_results = run_all_validation_gates(
                project_path=project_path,
                manifest_data=manifest.to_dict(),
                execution_result={"exit_code": jules_res.get("exit_code", 0)},
                raw_output=jules_res.get("raw_output", ""),
                parsed_response=jules_res.get("parsed_response"),
            )
            state_data["validation_results"] = val_results
            manifest.validation_status = val_results

            if val_results["overall_status"] == "BLOCKED":
                state_data["current_state"] = "BLOCKED"
                manifest.status = "BLOCKED"
                manifest.next_action = "NONE"
                self.persist_state(run_dirs, manifest, state_data)
                (run_dirs["run_dir"] / "FINAL_STATUS.md").write_text(
                    f"# Final Run Status: BLOCKED\n\nValidation gate blocked execution: {val_results}",
                    encoding="utf-8",
                )
                return {
                    "status": "BLOCKED",
                    "validation_results": val_results,
                    "run_dir": str(run_dirs["run_dir"]),
                }

            state_data["completed_states"].append("JULES_VALIDATION")
            state_data["current_state"] = "RESULTS_COMMITTED"
            manifest.next_action = "AI_REVIEW"
            self.persist_state(run_dirs, manifest, state_data)

        # 4. AI_REVIEW
        if state_data["current_state"] in ("RESULTS_COMMITTED", "AI_REVIEW"):
            jules_res = state_data.get("jules_result", {})
            val_results = state_data.get("validation_results", {})
            review_res = self.reviewer.review_artifacts(
                project_id=project_id,
                run_id=run_id,
                task_spec=task_spec,
                jules_result=jules_res,
                validation_results=val_results,
                run_dirs=run_dirs,
            )
            state_data["review_result"] = review_res
            manifest.review_status = review_res
            state_data["completed_states"].append("AI_REVIEW")
            state_data["current_state"] = "DECISION"
            manifest.next_action = "DECISION"
            self.persist_state(run_dirs, manifest, state_data)

        # 5. DECISION
        if state_data["current_state"] == "DECISION":
            review_res = state_data.get("review_result", {})
            rev_stat = review_res.get("REVIEW_STATUS", "PASS")

            if rev_stat == "PASS":
                state_data["current_state"] = "FINAL"
                manifest.status = "PASS"
                manifest.next_action = "NONE"
                self.persist_state(run_dirs, manifest, state_data)
                (run_dirs["run_dir"] / "FINAL_STATUS.md").write_text(
                    "# Final Run Status: PASS\n\nWorkflow completed successfully. AI review passed.",
                    encoding="utf-8",
                )
                return {
                    "status": "PASS",
                    "run_dir": str(run_dirs["run_dir"]),
                    "manifest": manifest.to_dict(),
                }
            elif rev_stat == "NEEDS_HUMAN_REVIEW":
                state_data["current_state"] = "HUMAN_REVIEW"
                manifest.status = "NEEDS_HUMAN_REVIEW"
                manifest.next_action = "HUMAN_REVIEW"
                self.persist_state(run_dirs, manifest, state_data)
                (run_dirs["run_dir"] / "FINAL_STATUS.md").write_text(
                    "# Final Run Status: NEEDS_HUMAN_REVIEW\n\nAI reviewer requested human review.",
                    encoding="utf-8",
                )
                return {
                    "status": "NEEDS_HUMAN_REVIEW",
                    "run_dir": str(run_dirs["run_dir"]),
                }
            else:
                # FAIL -> CORRECTION_REQUIRED
                state_data["current_state"] = "CORRECTION_REQUIRED"
                manifest.status = "CORRECTION_REQUIRED"
                manifest.next_action = "JULES_CORRECTION"
                self.persist_state(run_dirs, manifest, state_data)
                (run_dirs["run_dir"] / "FINAL_STATUS.md").write_text(
                    f"# Final Run Status: CORRECTION_REQUIRED\n\nRequired actions:\n{review_res.get('REQUIRED_ACTIONS')}",
                    encoding="utf-8",
                )
                return {
                    "status": "CORRECTION_REQUIRED",
                    "required_actions": review_res.get("REQUIRED_ACTIONS"),
                    "run_dir": str(run_dirs["run_dir"]),
                }

        return {
            "status": manifest.status,
            "current_state": state_data["current_state"],
            "run_dir": str(run_dirs["run_dir"]),
        }
