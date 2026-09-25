import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import controller


class ControllerTests(unittest.TestCase):
    def test_spec_exists(self):
        p = Path(__file__).parents[1] / "specs" / "project_audit.json"
        self.assertTrue(p.exists())
        data = json.loads(p.read_text(encoding="utf-8"))
        self.assertIn("stop_conditions", data)
        self.assertIn("forbidden_actions", data)
        self.assertIn("fabricate missing results", data["forbidden_actions"])

    def test_prompt_contains_no_fabrication_rule(self):
        prompt = controller.build_prompt("Demo", "Q2", "FULL", {})
        self.assertIn("Never fabricate", prompt)
        self.assertIn("HOLD", prompt)
        self.assertIn("Do not delete original datasets or frozen evidence", prompt)

    # ---------------------------------------------------------
    # Workspace Resolution & Binding Tests
    # ---------------------------------------------------------
    def test_resolve_project_relative_name(self):
        # research_controller is an existing project under C:\MyPython
        resolved = controller.resolve_project("research_controller")
        self.assertTrue(resolved.is_absolute())
        self.assertEqual(resolved, (controller.BASE / "research_controller").resolve())
        self.assertTrue(resolved.is_dir())

    def test_resolve_project_absolute_path(self):
        target = (controller.BASE / "research_controller").resolve()
        resolved = controller.resolve_project(target)
        self.assertTrue(resolved.is_absolute())
        self.assertEqual(resolved, target)

    def test_build_agy_command_workspace_binding_and_no_project_flag(self):
        project_dir = (controller.get_base_dir() / "research_controller").resolve()
        cmd = controller.build_agy_command(
            agy_exe=r"C:\agy\agy.exe",
            prompt="Test prompt",
            project_path=project_dir,
            autonomous=False,
            output_format="json",
        )

        # 1. Must use --add-dir <absolute_project_path>
        self.assertIn("--add-dir", cmd)
        idx = cmd.index("--add-dir")
        self.assertEqual(cmd[idx + 1], str(project_dir))

        # 2. Must NOT rely on --project for local workspace
        self.assertNotIn("--project", cmd)

        # 3. Autonomous flag must be absent when autonomous=False
        self.assertNotIn("--dangerously-skip-permissions", cmd)

        # 4. Output format is set
        self.assertIn("--output-format", cmd)
        self.assertEqual(cmd[cmd.index("--output-format") + 1], "json")

    def test_build_agy_command_autonomous_mode(self):
        project_dir = (controller.get_base_dir() / "research_controller").resolve()
        cmd = controller.build_agy_command(
            agy_exe=r"C:\agy\agy.exe",
            prompt="Test prompt",
            project_path=project_dir,
            autonomous=True,
            output_format="stream-json",
        )

        # Autonomous mode must use --dangerously-skip-permissions
        self.assertIn("--dangerously-skip-permissions", cmd)
        self.assertIn("--add-dir", cmd)
        self.assertNotIn("--project", cmd)

    # ---------------------------------------------------------
    # Fail-Closed Workspace Verification Tests
    # ---------------------------------------------------------
    def test_resolve_project_fail_closed_non_existent(self):
        with self.assertRaises(controller.WorkspaceNotFoundError):
            controller.resolve_project("non_existent_project_xyz_99999")

    def test_resolve_project_fail_closed_outside_base(self):
        # Outside base directory check
        outside_path = r"C:\Windows" if os.name == "nt" else "/usr"
        with self.assertRaises(controller.WorkspaceBoundaryError):
            controller.resolve_project(outside_path)

    def test_resolve_project_fail_closed_directory_traversal(self):
        # Path traversal attempting to escape base directory
        traversal_path = r"..\some_external_dir" if os.name == "nt" else "../some_external_dir"
        with self.assertRaises(controller.WorkspaceBoundaryError):
            controller.resolve_project(traversal_path)

    def test_resolve_project_fail_closed_base_dir_itself(self):
        # Base dir itself is not a project workspace
        with self.assertRaises(controller.WorkspaceBoundaryError):
            controller.resolve_project(controller.BASE)

    def test_resolve_project_fail_closed_not_a_directory(self):
        # Pointing to a file instead of a directory
        readme_path = Path(__file__).parents[1] / "README.md"
        with self.assertRaises(controller.WorkspaceNotADirectoryError):
            controller.resolve_project(readme_path)

    def test_run_fail_closed_aborts_before_execution(self):
        # Verify that if workspace verification fails, no command execution occurs
        with patch("controller.execute_task") as mock_exec:
            with self.assertRaises(controller.WorkspaceNotFoundError):
                controller.run(["--project", "non_existent_project_12345"])
            mock_exec.assert_not_called()

        with patch("controller.execute_task") as mock_exec:
            with self.assertRaises(controller.WorkspaceBoundaryError):
                controller.run(["--project", r"C:\Windows"])
            mock_exec.assert_not_called()

    def test_resolve_project_fail_closed_empty_or_whitespace(self):
        for invalid in ["", "   ", "\t\n"]:
            with self.subTest(invalid=invalid):
                with self.assertRaises(controller.WorkspaceBoundaryError) as ctx:
                    controller.resolve_project(invalid)
                self.assertIn("FAIL-CLOSED: Project path cannot be empty or whitespace.", str(ctx.exception))

    def test_resolve_project_fail_closed_base_dir_itself_exact_message(self):
        with self.assertRaises(controller.WorkspaceBoundaryError) as ctx:
            controller.resolve_project(controller.BASE)
        self.assertIn("FAIL-CLOSED: Project path cannot be the base directory itself:", str(ctx.exception))

    def test_resolve_project_fail_closed_different_drive(self):
        with self.assertRaises(controller.WorkspaceBoundaryError) as ctx:
            controller.resolve_project(r"D:\MyPython\some_project")
        self.assertIn("outside allowed base directory", str(ctx.exception))

    def test_resolve_project_fail_closed_invalid_path(self):
        with self.assertRaises(controller.WorkspaceVerificationError):
            controller.resolve_project("\0invalid_path")

    def test_verify_workspace_direct(self):
        # 1. Non-absolute path
        with self.assertRaises(controller.WorkspaceVerificationError) as ctx:
            controller.verify_workspace(Path("relative/path"))
        self.assertIn("must be absolute", str(ctx.exception))

        # 2. Non-existent path
        non_existent = (controller.get_base_dir() / "definitely_non_existent_folder_99999").resolve()
        with self.assertRaises(controller.WorkspaceNotFoundError) as ctx:
            controller.verify_workspace(non_existent)
        self.assertIn("does not exist", str(ctx.exception))

        # 3. File instead of directory
        readme_path = (Path(__file__).parents[1] / "README.md").resolve()
        with self.assertRaises(controller.WorkspaceNotADirectoryError) as ctx:
            controller.verify_workspace(readme_path)
        self.assertIn("is not a directory", str(ctx.exception))

        # 4. Valid directory returns Path
        valid_dir = Path(__file__).parents[1].resolve()
        result = controller.verify_workspace(valid_dir)
        self.assertEqual(result, valid_dir)

    def test_fail_closed_creates_no_results_artifacts(self):
        # FAIL-CLOSED: No output directories or files should be created if verification fails
        with tempfile.TemporaryDirectory() as tmp_results:
            results_path = Path(tmp_results)
            with patch("controller.execute_task") as mock_exec:
                with self.assertRaises(controller.WorkspaceNotFoundError):
                    controller.run(
                        argv=["--project", "non_existent_project_xyz"],
                        results_base=results_path,
                    )
                mock_exec.assert_not_called()
                # Directory must be empty
                self.assertEqual(list(results_path.iterdir()), [])

            with patch("controller.execute_task") as mock_exec:
                with self.assertRaises(controller.WorkspaceBoundaryError):
                    controller.run(
                        argv=["--project", r"C:\Windows"],
                        results_base=results_path,
                    )
                mock_exec.assert_not_called()
                self.assertEqual(list(results_path.iterdir()), [])

    def test_run_with_workspace_cli_alias(self):
        mock_output = json.dumps({"status": "SUCCESS", "response": "OK"})
        with patch("controller.execute_task", return_value=(0, mock_output)) as mock_exec:
            with tempfile.TemporaryDirectory() as tmp_results:
                rc = controller.run(
                    argv=["--workspace", "research_controller"],
                    results_base=Path(tmp_results),
                )
                self.assertEqual(rc, 0)
                mock_exec.assert_called_once()
                cmd = mock_exec.call_args[1]["cmd"]
                self.assertIn("--add-dir", cmd)
                self.assertNotIn("--project", cmd)

    def test_run_missing_spec_file_fail_closed(self):
        with patch("controller.execute_task") as mock_exec:
            with self.assertRaises(FileNotFoundError):
                controller.run([
                    "--project", "research_controller",
                    "--spec", "non_existent_spec_xyz.json",
                ])
            mock_exec.assert_not_called()

    # ---------------------------------------------------------
    # Output Parsing Tests
    # ---------------------------------------------------------
    def test_parse_agy_output_json_format(self):
        raw_json = json.dumps({
            "status": "SUCCESS",
            "response": "Audit passed successfully.",
            "metrics": {"duration": 5.2}
        })
        parsed = controller.parse_agy_output(raw_json)
        self.assertTrue(parsed["parsed"])
        self.assertEqual(parsed["status"], "SUCCESS")
        self.assertEqual(parsed["response"], "Audit passed successfully.")

    def test_parse_agy_output_stream_json_format(self):
        ndjson = "\n".join([
            json.dumps({"event": "init", "init": {"cwd": r"C:\MyPython\test"}}),
            json.dumps({"event": "step_update", "step_update": {"step_index": 0}}),
            "jetski: headless warning message",  # non-JSON line
            json.dumps({"event": "result", "result": {"status": "SUCCESS", "response": "Completed stream run"}})
        ])
        parsed = controller.parse_agy_output(ndjson)
        self.assertTrue(parsed["parsed"])
        self.assertEqual(parsed["status"], "SUCCESS")
        self.assertEqual(parsed["response"], "Completed stream run")
        self.assertEqual(parsed["events_count"], 3)

    def test_parse_agy_output_fallback_text(self):
        raw_text = "Standard error or unexpected output"
        parsed = controller.parse_agy_output(raw_text)
        self.assertFalse(parsed["parsed"])
        self.assertEqual(parsed["status"], "RAW_TEXT")
        self.assertEqual(parsed["response"], raw_text)

    # ---------------------------------------------------------
    # Result Artifacts Persistence Tests
    # ---------------------------------------------------------
    def test_save_run_results_stores_all_required_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            run_id = "test_run_20260909T080000Z"
            spec = {"purpose": "unit test audit", "allowed_actions": ["read"]}
            meta = {"project": "research_controller", "mode": "FULL"}
            raw_output = '{"event": "result", "result": {"response": "All good"}}'
            parsed = {"status": "SUCCESS", "response": "All good"}
            exit_status = 0
            timestamp_str = "20260909T080000Z"

            out_dir = controller.save_run_results(
                results_base=tmp_path,
                run_id=run_id,
                spec=spec,
                meta=meta,
                raw_output=raw_output,
                parsed_response=parsed,
                exit_status=exit_status,
                timestamp_str=timestamp_str,
            )

            self.assertTrue(out_dir.exists())

            # 1. Task specification
            spec_file = out_dir / "task_specification.json"
            self.assertTrue(spec_file.exists())
            saved_spec = json.loads(spec_file.read_text(encoding="utf-8"))
            self.assertEqual(saved_spec["purpose"], "unit test audit")

            # 2. Command metadata
            meta_file = out_dir / "command_metadata.json"
            self.assertTrue(meta_file.exists())
            saved_meta = json.loads(meta_file.read_text(encoding="utf-8"))
            self.assertEqual(saved_meta["exit_status"], 0)
            self.assertEqual(saved_meta["project"], "research_controller")

            # Backward compatibility metadata file
            self.assertTrue((out_dir / "controller_run.json").exists())

            # 3. Raw AGY output
            raw_file = out_dir / "raw_agy_output.txt"
            self.assertTrue(raw_file.exists())
            self.assertEqual(raw_file.read_text(encoding="utf-8"), raw_output)

            # Backward compatibility stream file
            self.assertTrue((out_dir / "agy_stream.jsonl").exists())

            # 4. Parsed response
            parsed_file = out_dir / "parsed_response.json"
            self.assertTrue(parsed_file.exists())
            saved_parsed = json.loads(parsed_file.read_text(encoding="utf-8"))
            self.assertEqual(saved_parsed["status"], "SUCCESS")
            self.assertEqual(saved_parsed["response"], "All good")

            # 5. Exit status
            exit_file = out_dir / "exit_status.txt"
            self.assertTrue(exit_file.exists())
            self.assertEqual(exit_file.read_text(encoding="utf-8").strip(), "0")

            # Backward compatibility exit code file
            self.assertTrue((out_dir / "exit_code.txt").exists())

            # 6. Timestamp
            stamp_file = out_dir / "timestamp.txt"
            self.assertTrue(stamp_file.exists())
            self.assertEqual(stamp_file.read_text(encoding="utf-8").strip(), timestamp_str)

    def test_run_success_flow_with_mock_execution(self):
        mock_output = json.dumps({"status": "SUCCESS", "response": "Mock audit completed."})
        with patch("controller.execute_task", return_value=(0, mock_output)) as mock_exec:
            with tempfile.TemporaryDirectory() as tmp_results:
                results_path = Path(tmp_results)
                rc = controller.run(
                    argv=[
                        "--project", "research_controller",
                        "--autonomous",
                        "--target", "TEST_TARGET",
                        "--output-format", "json",
                    ],
                    results_base=results_path,
                )
                self.assertEqual(rc, 0)
                mock_exec.assert_called_once()

                # Verify command passed to execute_task used --add-dir and --dangerously-skip-permissions
                called_cmd = mock_exec.call_args[1]["cmd"]
                self.assertIn("--add-dir", called_cmd)
                self.assertIn("--dangerously-skip-permissions", called_cmd)
                self.assertNotIn("--project", called_cmd)

                # Verify artifacts were created in results_base
                created_dirs = list(results_path.glob("research_controller_*"))
                self.assertEqual(len(created_dirs), 1)
                run_dir = created_dirs[0]
                self.assertTrue((run_dir / "task_specification.json").exists())
                self.assertTrue((run_dir / "command_metadata.json").exists())
                self.assertTrue((run_dir / "raw_agy_output.txt").exists())
                self.assertTrue((run_dir / "parsed_response.json").exists())
                self.assertTrue((run_dir / "exit_status.txt").exists())
                self.assertTrue((run_dir / "timestamp.txt").exists())

    def test_run_nonzero_exit_code_saves_results_and_raises_system_exit(self):
        mock_output = json.dumps({"status": "ERROR", "response": "Execution error"})
        with patch("controller.execute_task", return_value=(1, mock_output)) as mock_exec:
            with tempfile.TemporaryDirectory() as tmp_results:
                results_path = Path(tmp_results)
                with self.assertRaises(SystemExit) as ctx:
                    controller.run(
                        argv=[
                            "--project", "research_controller",
                            "--target", "TEST_TARGET",
                        ],
                        results_base=results_path,
                    )
                self.assertIn("Antigravity exited with code 1", str(ctx.exception))

                # Verify artifacts were still preserved for audit
                created_dirs = list(results_path.glob("research_controller_*"))
                self.assertEqual(len(created_dirs), 1)
                run_dir = created_dirs[0]
                self.assertEqual((run_dir / "exit_status.txt").read_text(encoding="utf-8").strip(), "1")

    def test_save_run_results_stores_prompt_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            out_dir = controller.save_run_results(
                results_base=tmp_path,
                run_id="test_run_prompt",
                spec={"target": "audit"},
                meta={"project": "research_controller"},
                raw_output="output",
                parsed_response={"status": "SUCCESS"},
                exit_status=0,
                timestamp_str="20260909T080000Z",
                prompt="Explicit prompt string for test",
            )
            prompt_file = out_dir / "prompt.txt"
            self.assertTrue(prompt_file.exists())
            self.assertEqual(prompt_file.read_text(encoding="utf-8"), "Explicit prompt string for test")

    def test_run_with_custom_run_id(self):
        mock_output = json.dumps({"status": "SUCCESS", "response": "Custom run ID completed."})
        with patch("controller.execute_task", return_value=(0, mock_output)) as mock_exec:
            with tempfile.TemporaryDirectory() as tmp_results:
                results_path = Path(tmp_results)
                rc = controller.run(
                    argv=[
                        "--project", "research_controller",
                        "--run-id", "custom_audit_run_001",
                    ],
                    results_base=results_path,
                )
                self.assertEqual(rc, 0)
                mock_exec.assert_called_once()

                run_dir = results_path / "custom_audit_run_001"
                self.assertTrue(run_dir.exists())
                self.assertTrue((run_dir / "prompt.txt").exists())
                self.assertTrue((run_dir / "command_metadata.json").exists())
                saved_meta = json.loads((run_dir / "command_metadata.json").read_text(encoding="utf-8"))
                self.assertEqual(saved_meta["run_id"], "custom_audit_run_001")

    # ---------------------------------------------------------
    # Timeout & Status Handling Tests
    # ---------------------------------------------------------
    def test_format_duration_helper(self):
        self.assertEqual(controller.format_duration(None), "30m")
        self.assertEqual(controller.format_duration(""), "30m")
        self.assertEqual(controller.format_duration("30m"), "30m")
        self.assertEqual(controller.format_duration("45m"), "45m")
        self.assertEqual(controller.format_duration("1h"), "1h")
        self.assertEqual(controller.format_duration("1800s"), "1800s")
        self.assertEqual(controller.format_duration("1800"), "1800s")
        self.assertEqual(controller.format_duration(1800), "1800s")
        self.assertEqual(controller.format_duration(3600.0), "3600s")

    def test_parse_duration_to_seconds(self):
        self.assertEqual(controller.parse_duration_to_seconds(None), 1800.0)
        self.assertEqual(controller.parse_duration_to_seconds(""), 1800.0)
        self.assertEqual(controller.parse_duration_to_seconds("30m"), 1800.0)
        self.assertEqual(controller.parse_duration_to_seconds("45m"), 2700.0)
        self.assertEqual(controller.parse_duration_to_seconds("1h"), 3600.0)
        self.assertEqual(controller.parse_duration_to_seconds("1h30m"), 5400.0)
        self.assertEqual(controller.parse_duration_to_seconds("5m0s"), 300.0)
        self.assertEqual(controller.parse_duration_to_seconds(1800), 1800.0)
        self.assertEqual(controller.parse_duration_to_seconds("1800"), 1800.0)
        with self.assertRaises(ValueError):
            controller.parse_duration_to_seconds("invalid_duration")

    def test_build_agy_command_includes_print_timeout(self):
        project_dir = (controller.get_base_dir() / "research_controller").resolve()

        # Default timeout must be 30m (supporting at least 30m manuscript workflows)
        cmd_default = controller.build_agy_command(
            agy_exe=r"C:\agy\agy.exe",
            prompt="Test prompt",
            project_path=project_dir,
        )
        self.assertIn("--print-timeout", cmd_default)
        self.assertEqual(cmd_default[cmd_default.index("--print-timeout") + 1], "30m")
        self.assertIn("--add-dir", cmd_default)
        self.assertNotIn("--project", cmd_default)

        # Custom timeout (e.g. 45m)
        cmd_45m = controller.build_agy_command(
            agy_exe=r"C:\agy\agy.exe",
            prompt="Test prompt",
            project_path=project_dir,
            print_timeout="45m",
        )
        self.assertIn("--print-timeout", cmd_45m)
        self.assertEqual(cmd_45m[cmd_45m.index("--print-timeout") + 1], "45m")

        # Integer seconds formatted to duration string
        cmd_int = controller.build_agy_command(
            agy_exe=r"C:\agy\agy.exe",
            prompt="Test prompt",
            project_path=project_dir,
            print_timeout=1800,
        )
        self.assertIn("--print-timeout", cmd_int)
        self.assertEqual(cmd_int[cmd_int.index("--print-timeout") + 1], "1800s")

    def test_parse_agy_output_detects_real_agy_timeout_with_turn_in_progress(self):
        # Exact reproduction of real AGY output during timeout
        raw_output = (
            "[agy] print timeout after 5m0s with turn in progress; returning partial output\n"
            '{"conversation_id":"9ede86eb-4415-4933-9666-472db536b414","status":"SUCCESS","response":"",'
            '"duration_seconds":298.0161373,"num_turns":1,"usage":{"input_tokens":456119,"output_tokens":63284,'
            '"thinking_tokens":27350,"cache_read_tokens":6615694,"total_tokens":519403}}\n'
        )
        parsed = controller.parse_agy_output(raw_output)

        # Must NOT return SUCCESS or COMPLETED (prevent false PASS)
        self.assertEqual(parsed["status"], "TIMEOUT")
        self.assertTrue(parsed["is_timeout"])
        self.assertEqual(parsed["timeout_metadata"]["timeout_duration"], "5m0s")
        self.assertTrue(parsed["timeout_metadata"]["turn_in_progress"])
        self.assertTrue(parsed["timeout_metadata"]["partial_output"])
        self.assertIn("[agy] print timeout after 5m0s", parsed["timeout_metadata"]["timeout_message"])
        self.assertEqual(parsed["raw_partial_output"], raw_output)

        # Preserves inner AGY JSON metadata
        self.assertIn("raw_json", parsed)
        self.assertEqual(parsed["raw_json"]["conversation_id"], "9ede86eb-4415-4933-9666-472db536b414")
        self.assertEqual(parsed["raw_json"]["duration_seconds"], 298.0161373)

    def test_parse_agy_output_detects_30m_timeout_and_preserves_partial_output(self):
        raw_output = (
            "[agy] print timeout after 30m with turn in progress; returning partial output\n"
            '{"conversation_id":"manuscript-run-42","status":"SUCCESS","response":"Section 3.1 results partial draft...",'
            '"duration_seconds":1799.8}\n'
        )
        parsed = controller.parse_agy_output(raw_output)

        self.assertEqual(parsed["status"], "TIMEOUT")
        self.assertTrue(parsed["is_timeout"])
        self.assertEqual(parsed["timeout_metadata"]["timeout_duration"], "30m")
        self.assertEqual(parsed["response"], "Section 3.1 results partial draft...")
        self.assertEqual(parsed["raw_partial_output"], raw_output)

    def test_parse_agy_output_detects_stream_json_timeout(self):
        stream_ndjson = "\n".join([
            "[agy] print timeout after 30m with turn in progress; returning partial output",
            json.dumps({"event": "init", "init": {"cwd": r"C:\MyPython\manuscript"}}),
            json.dumps({"event": "step_update", "step_update": {"step_index": 2}}),
            json.dumps({"event": "result", "result": {"status": "SUCCESS", "response": "Incomplete manuscript synthesis"}})
        ])
        parsed = controller.parse_agy_output(stream_ndjson)

        self.assertEqual(parsed["status"], "TIMEOUT")
        self.assertTrue(parsed["is_timeout"])
        self.assertEqual(parsed["timeout_metadata"]["timeout_duration"], "30m")
        self.assertEqual(parsed["response"], "Incomplete manuscript synthesis")

    def test_parse_agy_output_detects_hold_from_response(self):
        raw_json = json.dumps({
            "status": "SUCCESS",
            "response": "HOLD: Authoritative data missing for station 48500. Stopping audit branch."
        })
        parsed = controller.parse_agy_output(raw_json)

        self.assertEqual(parsed["status"], "HOLD")
        self.assertTrue(parsed["is_hold"])
        self.assertIn("Authoritative data missing", parsed["hold_metadata"]["reason"])

    def test_parse_agy_output_detects_headless_denied_actions_as_hold(self):
        # Real headless auto-denied permission output
        raw_output = (
            'jetski: no output produced — a tool required the "command" permission that headless mode cannot prompt for...\n'
            '{"conversation_id":"e0fdd17b","status":"SUCCESS","response":"","duration_seconds":71.2,'
            '"denied_actions":[{"action":"command","display_name":"RunCommand"}]}\n'
        )
        parsed = controller.parse_agy_output(raw_output)

        self.assertEqual(parsed["status"], "HOLD")
        self.assertTrue(parsed["is_hold"])

    def test_determine_status_logic(self):
        # Timeout always overrides exit code 0
        self.assertEqual(controller.determine_status({"is_timeout": True}, exit_code=0), "TIMEOUT")
        self.assertEqual(controller.determine_status({"status": "TIMEOUT"}, exit_code=0), "TIMEOUT")

        # HOLD always overrides exit code 0
        self.assertEqual(controller.determine_status({"is_hold": True}, exit_code=0), "HOLD")
        self.assertEqual(controller.determine_status({"status": "HOLD"}, exit_code=0), "HOLD")

        # Clean SUCCESS returns PASS when exit_code is 0
        self.assertEqual(controller.determine_status({"status": "SUCCESS"}, exit_code=0), "PASS")
        self.assertEqual(controller.determine_status({"status": "COMPLETED"}, exit_code=0), "PASS")

        # Non-zero exit code returns FAIL
        self.assertEqual(controller.determine_status({"status": "SUCCESS"}, exit_code=1), "FAIL")

    def test_run_returns_timeout_when_agy_exits_zero_on_timeout(self):
        # Verifies fix for FALSE PASS:
        # AGY process exits with code 0, but output contains timeout with turn in progress
        raw_timeout_output = (
            "[agy] print timeout after 5m0s with turn in progress; returning partial output\n"
            '{"conversation_id":"test-timeout-01","status":"SUCCESS","response":"","duration_seconds":298.0}\n'
        )
        with patch("controller.execute_task", return_value=(0, raw_timeout_output)) as mock_exec:
            with tempfile.TemporaryDirectory() as tmp_results:
                results_path = Path(tmp_results)
                status = controller.run(
                    argv=[
                        "--project", "research_controller",
                        "--target", "Q2",
                    ],
                    results_base=results_path,
                )

                # Must return TIMEOUT, NOT 0 and NOT PASS
                self.assertEqual(status, "TIMEOUT")
                mock_exec.assert_called_once()

                # Verify saved artifacts record TIMEOUT metadata and exit code 0
                created_dirs = list(results_path.glob("research_controller_*"))
                self.assertEqual(len(created_dirs), 1)
                run_dir = created_dirs[0]

                # Command metadata must record TIMEOUT status and metadata
                meta = json.loads((run_dir / "command_metadata.json").read_text(encoding="utf-8"))
                self.assertEqual(meta["status"], "TIMEOUT")
                self.assertTrue(meta["is_timeout"])
                self.assertEqual(meta["timeout_metadata"]["timeout_duration"], "5m0s")
                self.assertEqual(meta["exit_status"], 0)

                # Parsed response must record TIMEOUT
                parsed = json.loads((run_dir / "parsed_response.json").read_text(encoding="utf-8"))
                self.assertEqual(parsed["status"], "TIMEOUT")
                self.assertTrue(parsed["is_timeout"])

                # Raw output file preserves the partial output and timeout banner verbatim
                self.assertEqual((run_dir / "raw_agy_output.txt").read_text(encoding="utf-8"), raw_timeout_output)

                # Exit status text preserves the actual process exit code (0)
                self.assertEqual((run_dir / "exit_status.txt").read_text(encoding="utf-8").strip(), "0")

    def test_run_returns_hold_when_agy_exits_zero_on_hold(self):
        raw_hold_output = json.dumps({
            "status": "SUCCESS",
            "response": "HOLD: Scientific contradiction detected in station temperature series."
        })
        with patch("controller.execute_task", return_value=(0, raw_hold_output)) as mock_exec:
            with tempfile.TemporaryDirectory() as tmp_results:
                results_path = Path(tmp_results)
                status = controller.run(
                    argv=[
                        "--project", "research_controller",
                        "--target", "Q2",
                    ],
                    results_base=results_path,
                )

                # Must return HOLD, NOT 0 and NOT PASS
                self.assertEqual(status, "HOLD")
                mock_exec.assert_called_once()

                created_dirs = list(results_path.glob("research_controller_*"))
                self.assertEqual(len(created_dirs), 1)
                run_dir = created_dirs[0]

                meta = json.loads((run_dir / "command_metadata.json").read_text(encoding="utf-8"))
                self.assertEqual(meta["status"], "HOLD")

                parsed = json.loads((run_dir / "parsed_response.json").read_text(encoding="utf-8"))
                self.assertEqual(parsed["status"], "HOLD")

    def test_run_configures_timeout_cli_argument(self):
        mock_output = json.dumps({"status": "SUCCESS", "response": "Completed 45m run."})
        with patch("controller.execute_task", return_value=(0, mock_output)) as mock_exec:
            with tempfile.TemporaryDirectory() as tmp_results:
                results_path = Path(tmp_results)
                rc = controller.run(
                    argv=[
                        "--project", "research_controller",
                        "--timeout", "45m",
                    ],
                    results_base=results_path,
                )
                self.assertEqual(rc, 0)
                mock_exec.assert_called_once()

                called_cmd = mock_exec.call_args[1]["cmd"]
                self.assertIn("--print-timeout", called_cmd)
                self.assertEqual(called_cmd[called_cmd.index("--print-timeout") + 1], "45m")

                created_dirs = list(results_path.glob("research_controller_*"))
                run_dir = created_dirs[0]
                meta = json.loads((run_dir / "command_metadata.json").read_text(encoding="utf-8"))
                self.assertEqual(meta["timeout"], "45m")

    def test_execute_task_timeout_handling(self):
        project_dir = (controller.get_base_dir() / "research_controller").resolve()
        mock_proc = MagicMock()
        mock_proc.communicate.side_effect = [
            subprocess.TimeoutExpired(cmd=["agy"], timeout=1),
            ("partial stdout output before timeout", None),
        ]
        mock_proc.returncode = 124
        with patch("subprocess.Popen", return_value=mock_proc):
            rc, output = controller.execute_task(project_dir, ["agy"], timeout=1)
            self.assertEqual(rc, 124)
            self.assertIn("print timeout after 1s", output)
            self.assertIn("partial stdout output before timeout", output)
            mock_proc.kill.assert_called_once()

    def test_save_run_results_preserves_timeout_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            results_path = Path(tmpdir)
            timeout_meta = {
                "is_timeout": True,
                "timeout_duration": "30m",
                "turn_in_progress": True,
                "partial_output": True,
                "timeout_message": "[agy] print timeout after 30m with turn in progress; returning partial output",
            }
            parsed = {
                "status": "TIMEOUT",
                "is_timeout": True,
                "timeout_metadata": timeout_meta,
                "raw_partial_output": "partial manuscript text",
                "response": "partial manuscript text",
            }
            out_dir = controller.save_run_results(
                results_base=results_path,
                run_id="run_timeout_audit",
                spec={"target": "manuscript"},
                meta={"project": "research_controller", "timeout": "30m"},
                raw_output="[agy] print timeout after 30m with turn in progress; returning partial output\npartial manuscript text",
                parsed_response=parsed,
                exit_status=0,
                timestamp_str="20260909T080000Z",
            )
            meta = json.loads((out_dir / "command_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["status"], "TIMEOUT")
            self.assertTrue(meta["is_timeout"])
            self.assertEqual(meta["timeout_metadata"]["timeout_duration"], "30m")
            self.assertEqual(meta["exit_status"], 0)

            saved_parsed = json.loads((out_dir / "parsed_response.json").read_text(encoding="utf-8"))
            self.assertEqual(saved_parsed["status"], "TIMEOUT")
            self.assertEqual(saved_parsed["timeout_metadata"]["timeout_duration"], "30m")
            self.assertEqual(saved_parsed["response"], "partial manuscript text")


if __name__ == "__main__":
    unittest.main()
