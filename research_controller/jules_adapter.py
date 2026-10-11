"""
Jules Adapter Module.
Handles task submission, status polling, log capture, and artifact collection for Jules / AGY CLI.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

class JulesAdapter:
    """
    Adapter for interacting with Jules CLI / Antigravity execution engine.
    """

    def __init__(self, mock: bool = False, mock_mode: bool = False):
        self.mock = mock or mock_mode

    def execute_jules_task(
        self,
        project_path: Path,
        target: str,
        mode: str,
        spec: Dict[str, Any],
        run_id: str,
        run_dirs: Dict[str, Path],
        autonomous: bool = False,
        timeout: str = "30m",
        output_format: str = "json",
    ) -> Dict[str, Any]:
        """
        Submits and executes a task using Jules / AGY CLI or simulated execution.
        Captures logs and outputs into run_dirs.
        """
        import controller

        prompt = controller.build_prompt(project_path.name, target, mode, spec)
        (run_dirs["run_dir"] / "TASK_SPECIFICATION.md").write_text(
            f"# Task Specification\n\n```json\n{json.dumps(spec, indent=2, ensure_ascii=False)}\n```\n\n## Rendered Prompt\n```text\n{prompt}\n```",
            encoding="utf-8",
        )

        if self.mock:
            rc = 0
            raw_output = json.dumps({
                "status": "SUCCESS",
                "response": f"Simulated Jules execution completed successfully for {project_path.name}.",
                "artifacts": ["analysis_report.md", "results.csv"],
            })
            parsed = controller.parse_agy_output(raw_output)
            status = controller.determine_status(parsed, raw_output=raw_output, exit_code=rc)
        else:
            agy_exe = controller.find_agy()
            formatted_timeout = controller.format_duration(timeout)
            cmd = controller.build_agy_command(
                agy_exe=agy_exe,
                prompt=prompt,
                project_path=project_path,
                autonomous=autonomous,
                output_format=output_format,
                print_timeout=formatted_timeout,
            )

            timeout_secs = None
            try:
                timeout_secs = controller.parse_duration_to_seconds(formatted_timeout) + 60.0
            except (ValueError, TypeError):
                pass

            rc, raw_output = controller.execute_task(
                project_path=project_path,
                cmd=cmd,
                timeout=timeout_secs,
            )
            parsed = controller.parse_agy_output(raw_output)
            status = controller.determine_status(parsed, raw_output=raw_output, exit_code=rc)

        # Save JULES_LOG.jsonl
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "exit_code": rc,
            "status": status,
            "raw_output": raw_output,
            "parsed_response": parsed,
        }
        (run_dirs["run_dir"] / "JULES_LOG.jsonl").write_text(
            json.dumps(log_entry, ensure_ascii=False) + "\n", encoding="utf-8"
        )

        # Save JULES_RESULT.md
        result_md = f"""# Jules Execution Result

- **Run ID**: {run_id}
- **Project Path**: `{project_path}`
- **Status**: `{status}`
- **Exit Code**: `{rc}`
- **Timestamp**: {datetime.now(timezone.utc).isoformat()}

## Execution Summary
{parsed.get('response', raw_output)}

## Parsed Output Metadata
```json
{json.dumps(parsed, indent=2, ensure_ascii=False)}
```
"""
        (run_dirs["run_dir"] / "JULES_RESULT.md").write_text(result_md, encoding="utf-8")

        return {
            "status": status,
            "exit_code": rc,
            "raw_output": raw_output,
            "parsed_response": parsed,
            "prompt": prompt,
        }
