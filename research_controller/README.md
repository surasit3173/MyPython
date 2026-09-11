# Research Controller Bridge

Local dispatcher for research audit tasks and Antigravity CLI execution.

## Workspace & Safety Model
- **Base directory**: All research workspaces must resolve to an absolute directory under `C:\MyPython`.
- **Fail-Closed verification**:
  - Validates that the workspace exists and is a directory before any execution.
  - Prevents path traversal or paths outside `C:\MyPython`.
  - Aborts immediately without calling Antigravity if checks fail.
- **AGY Workspace Binding**:
  - Passes `--add-dir <absolute_project_path>` to Antigravity CLI.
  - Does **NOT** use `--project` to select the local workspace.
- **Autonomous Mode**:
  - `--autonomous` adds `--dangerously-skip-permissions` to auto-approve tool permissions.
- **Configurable Timeout & Timeout Handling**:
  - Passes `--print-timeout` to Antigravity CLI (default: `30m` for long-running manuscript workflows).
  - Detects AGY print timeout or partial output with turn in progress and reports `TIMEOUT` instead of false `PASS`.
  - Detects scientific hold conditions and reports `HOLD` instead of `PASS`.
  - Preserves raw partial output, timeout duration, and metadata in result artifacts.
- **Non-fabrication & Frozen Evidence**:
  - Execution prompt enforces strict zero-fabrication rules and immutability of frozen scientific evidence.

## CLI Options
- `--project`, `--workspace`: Target research project name or absolute path under `C:\MyPython`.
- `--target`: Target specification (e.g. `Q2`).
- `--mode`: Execution mode (e.g. `FULL`).
- `--spec`: Path to specification JSON file (e.g. `specs/project_audit.json`).
- `--autonomous`: Enable permission bypass (`--dangerously-skip-permissions`).
- `--output-format`: Output format (`json`, `stream-json`, `text`; default: `json`).
- `--timeout`, `--print-timeout`: Execution wait timeout (default: `30m`, accepts `45m`, `1800s`, `1h`).
- `--results-dir`: Custom base directory for run results.
- `--run-id`: Custom run identifier (defaults to `<project>_<timestamp>`).

## Execution Example
Normal mode:
```powershell
python controller.py --project CMIP6PrachuapKhiriKhan --target Q2 --mode FULL --spec specs/project_audit.json
```

Fully autonomous mode:
```powershell
python controller.py --project CMIP6PrachuapKhiriKhan --target Q2 --mode FULL --spec specs/project_audit.json --autonomous
```

## Results Artifacts
Each run creates a dedicated directory under `results/<run_id>/` containing:
- `task_specification.json`: Task specification JSON.
- `command_metadata.json`: Command metadata, timestamp, workspace, and exit status.
- `raw_agy_output.txt`: Raw output stream/text directly from Antigravity.
- `parsed_response.json`: Parsed response and execution status.
- `exit_status.txt`: Exit returncode.
- `timestamp.txt`: Run timestamp.
- `prompt.txt`: Rendered execution prompt sent to Antigravity CLI.
- Legacy compatibility files (`controller_run.json`, `agy_stream.jsonl`, `exit_code.txt`).
