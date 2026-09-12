import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_ENV = os.environ.get("RESEARCH_BASE_DIR") or os.environ.get("MYPYTHON_BASE_DIR")
if BASE_ENV:
    BASE = Path(BASE_ENV).resolve()
elif Path(r"C:\MyPython").exists():
    BASE = Path(r"C:\MyPython").resolve()
else:
    BASE = Path(__file__).parents[1].resolve()
AGY_CANDIDATES = [
    Path(os.environ.get("AGY_EXE", "")) if os.environ.get("AGY_EXE") else None,
    Path(os.environ.get("LOCALAPPDATA", "")) / "agy" / "bin" / "agy.exe",
]


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


def find_agy() -> Path:
    for p in AGY_CANDIDATES:
        if p and p.exists():
            return p.resolve()
    on_path = shutil.which("agy")
    if on_path:
        return Path(on_path).resolve()
    return Path("agy")


def resolve_project(name_or_path: str | Path, base_dir: Path = BASE, verify_exists: bool = True) -> Path:
    """
    Resolve a project name or path to an absolute path under base_dir (default: C:\\MyPython).
    FAIL-CLOSED:
    - Path must reside strictly inside base_dir.
    - Path cannot be base_dir itself.
    - If verify_exists is True, path must exist and be a directory.
    """
    if isinstance(name_or_path, (str, Path)):
        s_check = str(name_or_path).strip()
        if not s_check:
            raise WorkspaceBoundaryError(
                "FAIL-CLOSED: Project path cannot be empty or whitespace."
            )
        if ".." in Path(s_check).parts or ".." in s_check.replace("\\", "/").split("/"):
            raise WorkspaceBoundaryError(
                f"FAIL-CLOSED: Directory traversal detected in project path '{s_check}'"
            )

    base = Path(base_dir).resolve()

    s_path = str(name_or_path).strip()
    is_win_path = bool(re.match(r"^[a-zA-Z]:", s_path)) or s_path.startswith("\\")

    try:
        target = Path(name_or_path)
        if not target.is_absolute() and not is_win_path:
            target = base / target
        else:
            if os.name != "nt" and is_win_path:
                raise WorkspaceBoundaryError(
                    f"FAIL-CLOSED: Project path '{s_path}' is outside allowed base directory '{base}'"
                )
            target = target.resolve()
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
    s_path = str(project_path)
    is_abs = project_path.is_absolute() or s_path.startswith('/') or s_path.startswith('\\') or bool(re.match(r'^[a-zA-Z]:', s_path))
    if not is_abs:
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
    """
    Format duration value for AGY --print-timeout flag (e.g. '30m', '1800s', '1h').
    If integer or numeric string without unit is provided, assumes seconds.
    Defaults to '30m' (30 minutes) if None or empty.
    """
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
    """
    Parse duration string (e.g. '30m', '1800s', '1h', '5m0s') to float seconds.
    """
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
    """
    Detect Antigravity CLI print timeout and partial output markers.
    Returns a dict with timeout metadata if detected, else None.
    """
    if not raw_text:
        return None

    # Matches patterns like:
    # [agy] print timeout after 5m0s with turn in progress; returning partial output
    # print timeout after 30m with turn in progress; returning partial output
    # [agy] print timeout after 30m
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
    """
    Detect scientific HOLD or blocked execution conditions.
    """
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
    """
    Determine authoritative status (PASS, TIMEOUT, HOLD, FAIL).
    FAIL-CLOSED: Returns TIMEOUT or HOLD instead of PASS even when exit_code is 0.
    """
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
    """
    Construct command line for Antigravity CLI (agy).
    - Uses --add-dir <absolute_project_path>
    - Does NOT use --project to select local workspace
    - Uses --dangerously-skip-permissions when autonomous is True
    - Passes --print-timeout to configure wait duration (default: 30m)
    """
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
    """
    Parse raw output from agy execution.
    Handles:
    1. Single JSON object output (--output-format json)
    2. Streaming NDJSON event lines (--output-format stream-json)
    3. Plain text or error fallback
    4. Timeout and partial output detection (print timeout, turn in progress)
    5. HOLD condition detection
    """
    text = raw_output.strip()
    if not text:
        return {"status": "EMPTY", "response": "", "parsed": False}

    timeout_meta = extract_timeout_metadata(raw_output)

    # First, let's try to extract JSON objects and events
    data = None
    events = []
    final_result = None
    stream_response = None

    # Attempt 1: Entire text is valid JSON
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        pass

    # Attempt 2: Extract JSON from lines (handles banner messages before JSON)
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

        # If we found an item that is a standalone JSON result (like in --output-format json with a banner)
        if len(events) == 1 and final_result is None:
            data = events[0]

    # Build base parsed dictionary
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

    # Now apply timeout and HOLD detection
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
    """
    Save all run artifacts into results/<run_id>/
    Saves:
    - task specification (task_specification.json)
    - command metadata (command_metadata.json & controller_run.json)
    - raw AGY output (raw_agy_output.txt & agy_stream.jsonl)
    - parsed response (parsed_response.json)
    - exit status (exit_status.txt & exit_code.txt)
    - timestamp (timestamp.txt)
    - prompt text (prompt.txt, if provided)
    """
    out_dir = results_base / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Task specification
    (out_dir / "task_specification.json").write_text(
        json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # 2. Command metadata
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

    # 3. Raw AGY output
    (out_dir / "raw_agy_output.txt").write_text(raw_output, encoding="utf-8")
    (out_dir / "agy_stream.jsonl").write_text(raw_output, encoding="utf-8")

    # 4. Parsed response
    (out_dir / "parsed_response.json").write_text(
        json.dumps(parsed_response, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # 5. Exit status
    (out_dir / "exit_status.txt").write_text(str(exit_status), encoding="utf-8")
    (out_dir / "exit_code.txt").write_text(str(exit_status), encoding="utf-8")

    # 6. Timestamp
    (out_dir / "timestamp.txt").write_text(timestamp_str, encoding="utf-8")

    # 7. Prompt text
    if prompt is not None:
        (out_dir / "prompt.txt").write_text(prompt, encoding="utf-8")

    return out_dir


def execute_task(
    project_path: Path,
    cmd: list[str],
    timeout: float | int | None = None,
) -> tuple[int, str]:
    """
    Execute command in verified workspace directory.
    """
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
    ap = argparse.ArgumentParser(description="Research Controller Bridge for Antigravity")
    ap.add_argument("--project", "--workspace", dest="project", required=True,
                    help="Target research project name or absolute path under C:\\MyPython")
    ap.add_argument("--target", default="Q2", help="Target specification (default: Q2)")
    ap.add_argument("--mode", default="FULL", help="Execution mode (default: FULL)")
    ap.add_argument("--spec", default=None, help="Path to specification JSON file")
    ap.add_argument("--autonomous", action="store_true",
                    help="Enable Antigravity permission bypass (--dangerously-skip-permissions)")
    ap.add_argument("--output-format", default="json", choices=["json", "stream-json", "text"],
                    help="Antigravity output format (default: json)")
    ap.add_argument("--timeout", "--print-timeout", dest="timeout", default="30m",
                    help="Timeout for Antigravity execution (e.g. 30m, 1800s, 45m; default: 30m)")
    ap.add_argument("--results-dir", default=None, help="Custom base directory for run results")
    ap.add_argument("--run-id", default=None, help="Custom run ID (default: <project>_<timestamp>)")
    args = ap.parse_args(argv)

    # 1. FAIL-CLOSED workspace resolution and verification
    try:
        project_path = resolve_project(args.project, verify_exists=True)
    except (WorkspaceVerificationError, FileNotFoundError, ValueError, NotADirectoryError) as err:
        print(f"FAIL-CLOSED: Workspace verification failed: {err}", file=sys.stderr)
        raise

    # 2. Verify Antigravity CLI executable
    agy = find_agy()

    # 3. Load specification
    spec = {}
    spec_path = None
    if args.spec:
        spec_path = Path(args.spec).resolve()
        if not spec_path.exists():
            raise FileNotFoundError(f"FAIL-CLOSED: Specification file not found: {spec_path}")
        with open(spec_path, "r", encoding="utf-8") as f:
            spec = json.load(f)

    # 4. Build prompt
    prompt = build_prompt(project_path.name, args.target, args.mode, spec)

    # 5. Build agy command (uses --add-dir, never --project)
    formatted_timeout = format_duration(args.timeout)
    cmd = build_agy_command(
        agy_exe=agy,
        prompt=prompt,
        project_path=project_path,
        autonomous=args.autonomous,
        output_format=args.output_format,
        print_timeout=formatted_timeout,
    )

    # 6. Prepare run directory and command metadata
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = args.run_id if args.run_id else f"{project_path.name}_{stamp}"
    if results_base is None:
        if args.results_dir:
            results_base = Path(args.results_dir).resolve()
        else:
            results_base = Path(__file__).parent / "results"

    cmd_for_meta = list(cmd)
    try:
        p_idx = cmd_for_meta.index("-p") + 1
        cmd_for_meta[p_idx] = "<PROMPT>"
    except (ValueError, IndexError):
        pass

    meta = {
        "run_id": run_id,
        "timestamp_utc": stamp,
        "project": args.project,
        "workspace": str(project_path),
        "target": args.target,
        "mode": args.mode,
        "spec_file": str(spec_path) if spec_path else None,
        "agy": str(agy),
        "autonomous": bool(args.autonomous),
        "output_format": args.output_format,
        "timeout": formatted_timeout,
        "command": cmd_for_meta,
    }

    # 7. Execute task with safety margin beyond AGY print timeout
    timeout_seconds = None
    try:
        timeout_seconds = parse_duration_to_seconds(formatted_timeout) + 60.0
    except (ValueError, TypeError):
        pass

    rc, raw_output = execute_task(project_path=project_path, cmd=cmd, timeout=timeout_seconds)

    # 8. Parse output and detect timeout / HOLD conditions
    parsed = parse_agy_output(raw_output)

    # 9. Save all artifacts
    out_dir = save_run_results(
        results_base=results_base,
        run_id=run_id,
        spec=spec,
        meta=meta,
        raw_output=raw_output,
        parsed_response=parsed,
        exit_status=rc,
        timestamp_str=stamp,
        prompt=prompt,
    )

    # 10. Status determination and reporting
    status = determine_status(parsed, raw_output=raw_output, exit_code=rc)

    if status == "TIMEOUT":
        print(f"TIMEOUT: Antigravity print timeout or partial output while turn in progress. Evidence: {out_dir}")
        return "TIMEOUT"
    elif status == "HOLD":
        print(f"HOLD: Antigravity execution reported HOLD. Evidence: {out_dir}")
        return "HOLD"
    elif rc != 0:
        raise SystemExit(f"Antigravity exited with code {rc}. See {out_dir}")
    elif status in ("PASS", "SUCCESS", "COMPLETED"):
        print(f"PASS: Antigravity completed. Evidence: {out_dir}")
        return 0
    else:
        raise SystemExit(f"Antigravity execution ended with status '{status}' (exit code {rc}). See {out_dir}")


if __name__ == "__main__":
    res = run()
    if res != 0:
        sys.exit(1)
