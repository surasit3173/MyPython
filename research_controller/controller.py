import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from ai_reviewer import GeminiReviewer, MockReviewer, OpenAIReviewer
from protocol import RunManifest, prepare_run_directory
from state_machine import ResearchWorkflowRunner
from validation_gates import run_all_validation_gates


class WorkspaceVerificationError(Exception):
    """Base exception for workspace verification failures."""
    pass


class WorkspaceBoundaryError(WorkspaceVerificationError, ValueError):
    """Raised when project path is outside the allowed base directory."""
    pass


class WorkspaceNotFoundError(WorkspaceVerificationError, FileNotFoundError):
    """Raised when project path does not exist on disk."""
    pass


class WorkspaceNotADirectoryError(WorkspaceVerificationError, NotADirectoryError):
    """Raised when project path is not a directory."""
    pass


def get_base_dir() -> Path:
    env_base = os.environ.get("RESEARCH_BASE_DIR") or os.environ.get("MYPYTHON_BASE_DIR")
    if env_base:
        return Path(env_base).resolve()
    win_base = Path(r"C:\MyPython")
    if os.name == "nt" or win_base.exists():
        return win_base.resolve()
    repo_root = Path(__file__).resolve().parents[1]
    return repo_root


BASE = get_base_dir()
AGY_CANDIDATES = [
    Path(os.environ.get("AGY_EXE", "")) if os.environ.get("AGY_EXE") else None,
    Path(os.environ.get("LOCALAPPDATA", "")) / "agy" / "bin" / "agy.exe" if os.environ.get("LOCALAPPDATA") else None,
]


def find_agy() -> Path:
    for p in AGY_CANDIDATES:
        if p and p.exists():
            return p.resolve()
    on_path = shutil.which("agy")
    if on_path:
        return Path(on_path).resolve()
    if os.environ.get("MOCK_AGY") or os.environ.get("TESTING") or "unittest" in sys.modules:
        return Path("/bin/true") if os.name != "nt" else Path(r"C:\Windows\System32\cmd.exe")
    raise FileNotFoundError(
        "agy.exe not found. Set AGY_EXE, add agy to PATH, or install Antigravity CLI."
    )


def is_windows_drive_path(p: str) -> bool:
    return bool(re.match(r"^[a-zA-Z]:[\\/]", str(p)))


def resolve_project(name_or_path: str | Path, base_dir: Path | None = None, verify_exists: bool = True) -> Path:
    """
    Resolve a project name or path to an absolute path under base_dir (default: C:\\MyPython or repo root).
    FAIL-CLOSED:
    - Path must reside strictly inside base_dir.
    - Path cannot be base_dir itself.
    - If verify_exists is True, path must exist and be a directory.
    """
    if isinstance(name_or_path, (str, Path)):
        if not str(name_or_path).strip():
            raise WorkspaceBoundaryError(
                "FAIL-CLOSED: Project path cannot be empty or whitespace."
            )

    if base_dir is None:
        base_dir = get_base_dir()
    base = Path(base_dir).resolve()

    str_path = str(name_or_path).strip()
    is_win_drive = is_windows_drive_path(str_path)

    try:
        target = Path(name_or_path)
        if not target.is_absolute() and not is_win_drive:
            target = base / target
        elif is_win_drive and os.name != "nt":
            raise WorkspaceBoundaryError(
                f"FAIL-CLOSED: Project path '{str_path}' is outside allowed base directory '{base}'"
            )
        resolved = target.resolve()
    except WorkspaceBoundaryError:
        raise
    except (ValueError, OSError) as err:
        raise WorkspaceVerificationError(
            f"FAIL-CLOSED: Invalid project path '{name_or_path}': {err}"
        ) from err

    try:
        rel = resolved.relative_to(base)
    except ValueError as e:
        raise WorkspaceBoundaryError(
            f"FAIL-CLOSED: Project path '{resolved}' is outside allowed base directory '{base}'"
        ) from e

    if str(rel) == ".":
        raise WorkspaceBoundaryError(
            f"FAIL-CLOSED: Project path cannot be the base directory itself: '{resolved}'"
        )

    if verify_exists:
        verify_workspace(resolved)

    return resolved


def verify_workspace(project_path: Path) -> Path:
    """
    Verify that project workspace exists and is a directory.
    FAIL-CLOSED: Aborts if checks do not pass.
    """
    if not project_path.is_absolute():
        raise WorkspaceVerificationError(
            f"FAIL-CLOSED: Workspace path must be absolute: '{project_path}'"
        )
    if not project_path.exists():
        raise WorkspaceNotFoundError(
            f"FAIL-CLOSED: Workspace path does not exist: '{project_path}'"
        )
    if not project_path.is_dir():
        raise WorkspaceNotADirectoryError(
            f"FAIL-CLOSED: Workspace path is not a directory: '{project_path}'"
        )
    return project_path


def build_prompt(project, target, mode, spec):
    return f"""
You are the Antigravity execution engine for a research-quality audit.

PROJECT: {project}
TARGET: {target}
MODE: {mode}

AUTHORITATIVE EXECUTION RULES
1. Work only inside the specified project workspace and its declared inputs.
2. Treat frozen evidence and authoritative outputs as immutable unless the task explicitly
   requests a correction.
3. Never fabricate data, references, statistics, figures, provenance, or missing outputs.
4. Do not silently convert UNKNOWN/HYPOTHESIS/INFERRED into FACT.
5. Run tests and validation before declaring PASS.
6. If an unresolved scientific contradiction or missing authoritative input is found,
   stop that branch and report HOLD rather than inventing a solution.
7. Do not submit, publish, upload, or contact an external service.
8. Do not delete original datasets or frozen evidence.
9. Produce machine-readable evidence.json and human-readable audit_report.md.
10. Return a concise execution summary plus exact artifact paths.

TASK SPECIFICATION
{json.dumps(spec, ensure_ascii=False, indent=2)}
""".strip()


def format_duration(val: str | int | float | None) -> str:
    if val is None:
        return "30m"
    if isinstance(val, (int, float)):
        return f"{int(val)}s"
    s = str(val).strip()
    if not s:
        return "30m"
    if s.isdigit():
        return f"{s}s"
    return s


def parse_duration_to_seconds(val: str | int | float | None) -> float:
    if val is None:
        return 1800.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if not s:
        return 1800.0
    if s.isdigit():
        return float(s)

    units = {
        "h": 3600.0,
        "m": 60.0,
        "s": 1.0,
        "ms": 0.001,
    }
    matches = re.findall(r"(\d+(?:\.\d+)?)\s*([a-zA-Z]+)", s)
    if matches:
        total = 0.0
        for num, unit in matches:
            u = unit.lower()
            if u in units:
                total += float(num) * units[u]
            else:
                raise ValueError(f"Unknown time unit: '{unit}' in duration '{val}'")
        return total
    raise ValueError(f"Unable to parse duration: '{val}'")


def extract_timeout_metadata(raw_text: str) -> dict | None:
    if not raw_text:
        return None

    timeout_pattern = re.compile(
        r"(?:\[agy\]\s+)?print\s+timeout\s+after\s+([^\s;,]+)"
        r"(?:.*?with\s+(turn\s+in\s+progress))?"
        r"(?:.*?(returning\s+partial\s+output))?",
        re.IGNORECASE,
    )

    match = timeout_pattern.search(raw_text)
    if match:
        duration = match.group(1)
        turn_in_progress = bool(match.group(2)) or ("turn in progress" in raw_text.lower())
        partial_output = bool(match.group(3)) or ("partial output" in raw_text.lower())
        matched_line = ""
        for line in raw_text.splitlines():
            if "print timeout" in line.lower():
                matched_line = line.strip()
                break

        return {
            "is_timeout": True,
            "timeout_duration": duration,
            "turn_in_progress": turn_in_progress,
            "partial_output": partial_output,
            "timeout_message": matched_line or match.group(0),
        }

    lowered = raw_text.lower()
    if "print timeout" in lowered or ("timeout" in lowered and "turn in progress" in lowered):
        dur_match = re.search(r"timeout\s+after\s+([^\s;,]+)", raw_text, re.IGNORECASE)
        dur = dur_match.group(1) if dur_match else "unknown"
        return {
            "is_timeout": True,
            "timeout_duration": dur,
            "turn_in_progress": "turn in progress" in lowered,
            "partial_output": "partial output" in lowered,
            "timeout_message": "Print timeout detected with turn in progress",
        }

    return None


def extract_hold_metadata(raw_text: str, parsed_data: dict | None = None) -> dict | None:
    if parsed_data and isinstance(parsed_data, dict):
        if parsed_data.get("status") == "HOLD":
            return {
                "is_hold": True,
                "reason": parsed_data.get("response") or "Status explicitly declared HOLD",
            }
        if parsed_data.get("denied_actions") and not parsed_data.get("response"):
            return {
                "is_hold": True,
                "reason": "Actions denied in headless execution without response produced",
            }

    response_text = ""
    if parsed_data and isinstance(parsed_data, dict):
        resp = parsed_data.get("response")
        if isinstance(resp, str):
            response_text = resp
    if not response_text:
        response_text = raw_text or ""

    if re.search(r"^\s*HOLD\b", response_text, re.MULTILINE | re.IGNORECASE) or \
       re.search(r"\bSTATUS:\s*HOLD\b", response_text, re.IGNORECASE) or \
       re.search(r"\bREPORT\s+HOLD\b", response_text, re.IGNORECASE):
        return {
            "is_hold": True,
            "reason": response_text.strip(),
        }

    return None


def determine_status(parsed: dict, raw_output: str = "", exit_code: int = 0) -> str:
    if parsed.get("is_timeout") or parsed.get("status") == "TIMEOUT":
        return "TIMEOUT"
    if parsed.get("is_hold") or parsed.get("status") == "HOLD":
        return "HOLD"
    if exit_code != 0:
        return "FAIL"
    raw_stat = parsed.get("status", "")
    if raw_stat in ("SUCCESS", "COMPLETED", "PASS"):
        return "PASS"
    if raw_stat == "RAW_TEXT":
        return "RAW_TEXT"
    return raw_stat or "UNKNOWN"


def build_agy_command(
    agy_exe: str | Path,
    prompt: str,
    project_path: Path,
    autonomous: bool = False,
    output_format: str = "json",
    print_timeout: str | int | None = "30m",
) -> list[str]:
    cmd = [
        str(agy_exe),
        "-p", prompt,
        "--add-dir", str(project_path.resolve()),
    ]
    if print_timeout:
        cmd.extend(["--print-timeout", format_duration(print_timeout)])
    if autonomous:
        cmd.append("--dangerously-skip-permissions")
    if output_format:
        cmd.extend(["--output-format", output_format])
    return cmd


def parse_agy_output(raw_output: str) -> dict:
    text = raw_output.strip()
    if not text:
        return {"status": "EMPTY", "response": "", "parsed": False}

    timeout_meta = extract_timeout_metadata(raw_output)

    data = None
    events = []
    final_result = None
    stream_response = None

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        pass

    if data is None:
        for line in text.splitlines():
            line = line.strip()
            if not line or not (line.startswith("{") and line.endswith("}")):
                continue
            try:
                item = json.loads(line)
                events.append(item)
                if item.get("event") == "result":
                    final_result = item.get("result", {})
                    if isinstance(final_result, dict) and "response" in final_result:
                        stream_response = final_result["response"]
            except json.JSONDecodeError:
                continue

        if len(events) == 1 and final_result is None:
            data = events[0]

    if data is not None:
        if isinstance(data, dict):
            raw_status = data.get("status", "SUCCESS")
            response = data.get("response", data.get("result", data))
            result_dict = {
                "status": raw_status,
                "response": response,
                "raw_json": data,
                "parsed": True,
            }
        else:
            result_dict = {
                "status": "SUCCESS",
                "response": data,
                "parsed": True,
            }
    elif final_result is not None:
        result_dict = {
            "status": final_result.get("status", "SUCCESS"),
            "response": stream_response if stream_response is not None else final_result,
            "result_metadata": final_result,
            "events_count": len(events),
            "parsed": True,
        }
    elif events:
        result_dict = {
            "status": "COMPLETED",
            "events_count": len(events),
            "events": events,
            "parsed": True,
        }
    else:
        result_dict = {
            "status": "RAW_TEXT",
            "response": text,
            "parsed": False,
        }

    hold_meta = extract_hold_metadata(raw_output, result_dict.get("raw_json") or result_dict)

    if timeout_meta:
        result_dict["status"] = "TIMEOUT"
        result_dict["is_timeout"] = True
        result_dict["timeout_metadata"] = timeout_meta
        result_dict["raw_partial_output"] = raw_output
        if result_dict.get("response") is None:
            result_dict["response"] = ""
    elif hold_meta:
        result_dict["status"] = "HOLD"
        result_dict["is_hold"] = True
        result_dict["hold_metadata"] = hold_meta
        result_dict["raw_partial_output"] = raw_output

    return result_dict


def save_run_results(
    results_base: Path,
    run_id: str,
    spec: dict,
    meta: dict,
    raw_output: str,
    parsed_response: dict,
    exit_status: int,
    timestamp_str: str,
    prompt: str | None = None,
) -> Path:
    out_dir = results_base / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "task_specification.json").write_text(
        json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    meta_payload = {
        **meta,
        "exit_status": exit_status,
        "status": parsed_response.get("status", "UNKNOWN"),
        "timestamp": timestamp_str,
    }
    if parsed_response.get("timeout_metadata"):
        meta_payload["timeout_metadata"] = parsed_response["timeout_metadata"]
    if parsed_response.get("is_timeout"):
        meta_payload["is_timeout"] = True
    if parsed_response.get("hold_metadata"):
        meta_payload["hold_metadata"] = parsed_response["hold_metadata"]

    meta_text = json.dumps(meta_payload, indent=2, ensure_ascii=False)
    (out_dir / "command_metadata.json").write_text(meta_text, encoding="utf-8")
    (out_dir / "controller_run.json").write_text(meta_text, encoding="utf-8")

    (out_dir / "raw_agy_output.txt").write_text(raw_output, encoding="utf-8")
    (out_dir / "agy_stream.jsonl").write_text(raw_output, encoding="utf-8")

    (out_dir / "parsed_response.json").write_text(
        json.dumps(parsed_response, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    (out_dir / "exit_status.txt").write_text(str(exit_status), encoding="utf-8")
    (out_dir / "exit_code.txt").write_text(str(exit_status), encoding="utf-8")

    (out_dir / "timestamp.txt").write_text(timestamp_str, encoding="utf-8")

    if prompt is not None:
        (out_dir / "prompt.txt").write_text(prompt, encoding="utf-8")

    return out_dir


def execute_task(
    project_path: Path,
    cmd: list[str],
    timeout: float | int | None = None,
) -> tuple[int, str]:
    proc = subprocess.Popen(
        cmd,
        cwd=str(project_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        stdout, _ = proc.communicate(timeout=timeout)
        return proc.returncode, (stdout or "")
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, _ = proc.communicate()
        partial = stdout or ""
        timeout_banner = f"\n[agy] print timeout after {timeout}s with turn in progress; returning partial output\n"
        return 124, (partial + timeout_banner)


def run(argv: list[str] | None = None, results_base: Path | None = None) -> int | str:
    ap = argparse.ArgumentParser(description="Research Controller Bridge for Antigravity & AI Reviewer Workflow")
    ap.add_argument("--project", "--workspace", dest="project", required=True,
                    help="Target research project name or absolute path under base directory")
    ap.add_argument("--target", default="Q2", help="Target specification (default: Q2)")
    ap.add_argument("--mode", default="FULL", help="Execution mode (default: FULL)")
    ap.add_argument("--spec", default=None, help="Path to specification JSON file")
    ap.add_argument("--autonomous", action="store_true",
                    help="Enable Antigravity permission bypass (--dangerously-skip-permissions)")
    ap.add_argument("--output-format", default="json", choices=["json", "stream-json", "text"],
                    help="Antigravity output format (default: json)")
    ap.add_argument("--timeout", "--print-timeout", dest="timeout", default="30m",
                    help="Timeout for execution (default: 30m)")
    ap.add_argument("--results-dir", default=None, help="Custom base directory for run results")
    ap.add_argument("--runs-dir", default=None, help="Custom base directory for GitHub runs artifacts")
    ap.add_argument("--run-id", default=None, help="Custom run ID (default: <project>_<timestamp>)")
    ap.add_argument("--reviewer", default="mock", choices=["mock", "openai", "gemini"],
                    help="AI Reviewer provider (default: mock)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Run offline simulation dry-run without invoking AGY CLI")
    args = ap.parse_args(argv)

    # 1. FAIL-CLOSED workspace resolution and verification
    try:
        project_path = resolve_project(args.project, verify_exists=True)
    except (WorkspaceVerificationError, FileNotFoundError, ValueError, NotADirectoryError) as err:
        print(f"FAIL-CLOSED: Workspace verification failed: {err}", file=sys.stderr)
        raise

    # 2. Verify Antigravity CLI executable (unless dry-run)
    if not args.dry_run:
        _ = find_agy()

    # 3. Load specification
    spec = {}
    spec_path = None
    if args.spec:
        spec_path = Path(args.spec).resolve()
        if not spec_path.exists():
            raise FileNotFoundError(f"FAIL-CLOSED: Specification file not found: {spec_path}")
        with open(spec_path, "r", encoding="utf-8") as f:
            spec = json.load(f)

    # 4. Prepare directory structure
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = args.run_id if args.run_id else f"{project_path.name}_{stamp}"

    base_runs_dir = Path(args.runs_dir).resolve() if args.runs_dir else Path(__file__).parent / "runs"

    # 5. Initialize AI Reviewer
    if args.reviewer == "openai":
        reviewer = OpenAIReviewer()
    elif args.reviewer == "gemini":
        reviewer = GeminiReviewer()
    else:
        reviewer = MockReviewer()

    # 6. Execute via State Machine Runner
    runner = ResearchWorkflowRunner(
        base_runs_dir=base_runs_dir,
        reviewer=reviewer,
        mock_jules=args.dry_run,
    )

    workflow_res = runner.execute_workflow(
        project_id=project_path.name,
        project_path=project_path,
        run_id=run_id,
        task_spec=spec,
        target=args.target,
        mode=args.mode,
        autonomous=args.autonomous,
        timeout=args.timeout,
    )

    # 7. Also mirror artifacts into results_base for backward compatibility if results_base or args.results_dir
    if results_base is None:
        if args.results_dir:
            results_base = Path(args.results_dir).resolve()
        else:
            results_base = Path(__file__).parent / "results"

    jules_res = workflow_res.get("jules_result", {})
    actual_exit = jules_res.get("exit_code", 0) if isinstance(jules_res, dict) else 0
    raw_output = jules_res.get("raw_output", "") if isinstance(jules_res, dict) else ""
    parsed = jules_res.get("parsed_response", {}) if isinstance(jules_res, dict) else parse_agy_output(raw_output)

    meta = {
        "run_id": run_id,
        "timestamp_utc": stamp,
        "project": args.project,
        "workspace": str(project_path),
        "target": args.target,
        "mode": args.mode,
        "spec_file": str(spec_path) if spec_path else None,
        "autonomous": bool(args.autonomous),
        "output_format": args.output_format,
        "timeout": format_duration(args.timeout),
        "workflow_status": workflow_res.get("status"),
    }

    out_dir = save_run_results(
        results_base=results_base,
        run_id=run_id,
        spec=spec,
        meta=meta,
        raw_output=raw_output,
        parsed_response=parsed,
        exit_status=actual_exit,
        timestamp_str=stamp,
        prompt=build_prompt(project_path.name, args.target, args.mode, spec),
    )

    status = workflow_res.get("status")
    if status == "TIMEOUT":
        print(f"TIMEOUT: Antigravity print timeout or partial output while turn in progress. Evidence: {out_dir}")
        return "TIMEOUT"
    elif status == "HOLD":
        print(f"HOLD: Antigravity execution reported HOLD. Evidence: {out_dir}")
        return "HOLD"
    elif status == "NEEDS_HUMAN_REVIEW":
        print(f"NEEDS_HUMAN_REVIEW: Human gate triggered. Evidence: {out_dir}")
        return "NEEDS_HUMAN_REVIEW"
    elif status == "BLOCKED":
        print(f"BLOCKED: Execution blocked by validation gate. Evidence: {out_dir}")
        return "BLOCKED"
    elif status == "FAIL":
        raise SystemExit(f"Antigravity exited with code 1. See {out_dir}")
    elif status in ("PASS", "SUCCESS", "COMPLETED"):
        print(f"PASS: Multi-agent workflow completed successfully. Evidence: {out_dir}")
        return 0
    else:
        raise SystemExit(f"Antigravity execution ended with status '{status}'. See {out_dir}")


if __name__ == "__main__":
    res = run()
    if res != 0:
        sys.exit(1)
