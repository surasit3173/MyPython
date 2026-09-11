import json
import os
import tempfile
import unittest
from pathlib import Path

from ai_reviewer import MockReviewer, OpenAIReviewer
from protocol import RunManifest, prepare_run_directory
from state_machine import ResearchWorkflowRunner
from validation_gates import DataGate, NumericalGate, ScientificGate, run_all_validation_gates


class MultiAgentWorkflowTests(unittest.TestCase):
    def test_project_isolation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_runs = Path(tmpdir)

            dir1 = prepare_run_directory(base_runs, "CMIP6Lampang", "run_lampang_001")
            dir2 = prepare_run_directory(base_runs, "CMIP6Uttaradit", "run_uttaradit_001")

            # Create distinct manifest for Lampang
            m1 = RunManifest(project_id="CMIP6Lampang", run_id="run_lampang_001", task_id="t1")
            m1.save(dir1["run_dir"])

            # Create distinct manifest for Uttaradit
            m2 = RunManifest(project_id="CMIP6Uttaradit", run_id="run_uttaradit_001", task_id="t2")
            m2.save(dir2["run_dir"])

            # Verify independence
            loaded1 = RunManifest.load(dir1["run_dir"] / "RUN_MANIFEST.json")
            loaded2 = RunManifest.load(dir2["run_dir"] / "RUN_MANIFEST.json")

            self.assertEqual(loaded1.project_id, "CMIP6Lampang")
            self.assertEqual(loaded2.project_id, "CMIP6Uttaradit")
            self.assertNotEqual(dir1["run_dir"], dir2["run_dir"])

    def test_run_manifest_schema_and_serialization(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            manifest = RunManifest(
                project_id="CMIP6Nan",
                run_id="run_nan_01",
                task_id="task_audit",
                status="RUNNING",
                input_artifacts=["input.csv"],
                output_artifacts=["output.csv"],
            )

            path = manifest.save(tmp_path)
            self.assertTrue(path.exists())

            loaded = RunManifest.load(path)
            self.assertEqual(loaded.project_id, "CMIP6Nan")
            self.assertEqual(loaded.run_id, "run_nan_01")
            self.assertEqual(loaded.status, "RUNNING")
            self.assertEqual(loaded.input_artifacts, ["input.csv"])

    def test_validation_gates_behavior(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            (project_path / "data.txt").write_text("dummy data", encoding="utf-8")

            # DataGate pass
            data_res = DataGate().evaluate(project_path)
            self.assertEqual(data_res.status, "PASS")

            # ScientificGate hold
            sci_res = ScientificGate().evaluate("", {"is_hold": True, "hold_metadata": {"reason": "Contradiction"}})
            self.assertEqual(sci_res.status, "BLOCKED")

            # NumericalGate negative variance
            num_res = NumericalGate().evaluate({"variance": -0.5})
            self.assertEqual(num_res.status, "BLOCKED")

    def test_state_machine_pass_workflow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runs_dir = Path(tmpdir)
            runner = ResearchWorkflowRunner(
                base_runs_dir=runs_dir,
                reviewer=MockReviewer(preset_status="PASS"),
                mock_jules=True,
            )

            res = runner.execute_workflow(
                project_id="CMIP6Lampang",
                project_path=Path(__file__).parents[1],
                run_id="test_run_pass",
                task_spec={"purpose": "unit test"},
            )

            self.assertEqual(res["status"], "PASS")
            run_dir = Path(res["run_dir"])
            self.assertTrue((run_dir / "RUN_MANIFEST.json").exists())
            self.assertTrue((run_dir / "FINAL_STATUS.md").exists())
            self.assertTrue((run_dir / "REVIEW" / "CHATGPT_REVIEW.json").exists())

    def test_state_machine_human_review_gate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runs_dir = Path(tmpdir)
            runner = ResearchWorkflowRunner(
                base_runs_dir=runs_dir,
                reviewer=MockReviewer(),
                mock_jules=True,
            )

            # Spec contains trigger "change_baseline"
            spec = {
                "purpose": "unit test",
                "change_baseline": True,
            }

            res = runner.execute_workflow(
                project_id="CMIP6Lampang",
                project_path=Path(__file__).parents[1],
                run_id="test_run_human_gate",
                task_spec=spec,
            )

            self.assertEqual(res["status"], "NEEDS_HUMAN_REVIEW")
            self.assertIn("Human gate triggered", res["reason"])

    def test_crash_recovery_resumption(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runs_dir = Path(tmpdir)
            runner = ResearchWorkflowRunner(
                base_runs_dir=runs_dir,
                reviewer=MockReviewer(preset_status="PASS"),
                mock_jules=True,
            )

            project_path = Path(__file__).parents[1]
            run_id = "test_run_resume"

            # 1. Execute initial step
            run_dirs, manifest, state_data = runner.load_or_create_state("CMIP6Nan", run_id, resume=True)
            state_data["current_state"] = "JULES_EXECUTION"
            runner.persist_state(run_dirs, manifest, state_data)

            # 2. Re-run runner to simulate resumption from state
            res = runner.execute_workflow(
                project_id="CMIP6Nan",
                project_path=project_path,
                run_id=run_id,
                task_spec={"purpose": "resumption test"},
                resume=True,
            )

            self.assertEqual(res["status"], "PASS")

    def test_malformed_reviewer_response_handling(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runs_dir = Path(tmpdir)
            run_dirs = prepare_run_directory(runs_dir, "CMIP6Lampang", "run_malformed")

            # OpenAIReviewer fallback without API key
            reviewer = OpenAIReviewer(api_key=None)
            res = reviewer.review_artifacts(
                project_id="CMIP6Lampang",
                run_id="run_malformed",
                task_spec={},
                jules_result={},
                validation_results={},
                run_dirs=run_dirs,
            )

            # Fallbacks safely without throwing unhandled exceptions
            self.assertIn(res["REVIEW_STATUS"], ("PASS", "FAIL", "NEEDS_HUMAN_REVIEW"))

    def test_secret_handling(self):
        # Ensure OpenAI API keys or tokens are not logged or written to plain text manifests
        manifest = RunManifest(
            project_id="CMIP6Lampang",
            run_id="run_secret_test",
            task_id="t1",
        )
        manifest_dict = manifest.to_dict()
        manifest_str = json.dumps(manifest_dict)

        self.assertNotIn("sk-proj-", manifest_str)
        self.assertNotIn("AIzaSy", manifest_str)


if __name__ == "__main__":
    unittest.main()
