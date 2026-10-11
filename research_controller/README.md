# Research Controller Bridge

Local dispatcher and multi-agent controller for research audit tasks, Antigravity CLI execution, and AI research reviews.

## Workspace & Safety Model
- **Base directory**: Resolves dynamically to `RESEARCH_BASE_DIR`, `C:\MyPython`, or the repository root on non-Windows environments.
- **Fail-Closed verification**:
  - Validates that the workspace exists and is a directory before any execution.
  - Prevents path traversal (`..`) or paths outside the base directory.
  - Aborts immediately without calling Antigravity if checks fail.
- **AGY Workspace Binding**:
  - Passes `--add-dir <absolute_project_path>` to Antigravity CLI.
  - Does **NOT** use `--project` to select the local workspace.
- **Autonomous Mode**:
  - `--autonomous` adds `--dangerously-skip-permissions` to auto-approve tool permissions.
- **Configurable Timeout & Timeout Handling**:
  - Passes `--print-timeout` to Antigravity CLI (default: `30m`).
  - Detects AGY print timeout or partial output with turn in progress and reports `TIMEOUT` instead of false `PASS`.
  - Detects scientific hold conditions and reports `HOLD` instead of `PASS`.
  - Preserves raw partial output, timeout duration, and metadata in result artifacts.
- **Non-fabrication & Frozen Evidence**:
  - Execution prompt enforces strict zero-fabrication rules and immutability of frozen scientific evidence.

## Multi-Agent Architecture & AI Reviewer
- **Target Workflow**: GitHub (source of truth) -> Controller -> Jules (execution) -> Validation Gates -> AI Reviewer (OpenAI/Gemini/Mock) -> GitHub artifacts.
- **Provider Abstraction**: Supports `--reviewer mock`, `--reviewer openai`, or `--reviewer gemini`.
- **Validation Gates**: `DATA_GATE`, `CODE_GATE`, `NUMERICAL_GATE`, `SCIENTIFIC_GATE`, `MANUSCRIPT_GATE`, `REPRODUCIBILITY_GATE`.
- **Human Gate Intercept**: Intercepts changes to scientific definitions, baselines, thresholds, scenarios, or datasets and sets status to `NEEDS_HUMAN_REVIEW`.
- **State Machine & Crash Recovery**: Persists `STATE.json` and `RUN_MANIFEST.json` under `runs/<project>/<run_id>/` allowing interrupted runs to resume safely.

## CLI Options
- `--project`, `--workspace`: Target research project name or absolute path under base directory.
- `--target`: Target specification (e.g. `Q2`).
- `--mode`: Execution mode (e.g. `FULL`).
- `--spec`: Path to specification JSON file (e.g. `specs/project_audit.json`).
- `--autonomous`: Enable permission bypass (`--dangerously-skip-permissions`).
- `--output-format`: Output format (`json`, `stream-json`, `text`; default: `json`).
- `--timeout`, `--print-timeout`: Execution wait timeout (default: `30m`).
- `--results-dir`: Custom base directory for legacy run results.
- `--runs-dir`: Custom base directory for GitHub run artifacts.
- `--run-id`: Custom run identifier (defaults to `<project>_<timestamp>`).
- `--reviewer`: AI Reviewer provider (`mock`, `openai`, `gemini`; default: `mock`).
- `--dry-run`: Run offline simulation dry-run without invoking live AGY CLI.

## Execution Example
Normal mode:
```powershell
python controller.py --project CMIP6PrachuapKhiriKhan --target Q2 --mode FULL --spec specs/project_audit.json
```

Fully autonomous mode with OpenAI reviewer:
```powershell
python controller.py --project CMIP6PrachuapKhiriKhan --target Q2 --mode FULL --spec specs/project_audit.json --autonomous --reviewer openai
```

Offline Dry-Run:
```powershell
python dry_run.py
```

## Results & Run Artifacts
Each run creates a dedicated directory under `runs/<project>/<run_id>/` containing:
- `RUN_MANIFEST.json`: Machine-readable run manifest.
- `STATE.json`: Persistent state machine state.
- `TASK_SPECIFICATION.md`: Task specification and rendered prompt.
- `JULES_RESULT.md`: Execution result summary.
- `JULES_LOG.jsonl`: Stream logs and exit status.
- `ANALYSIS_RESULTS/`: Output tables and figures.
- `VALIDATION/`: Validation gate outputs.
- `REVIEW/`: AI review outputs (`CHATGPT_REVIEW.json` and `CHATGPT_REVIEW.md`).
- `FINAL_STATUS.md`: Human-readable status banner.
