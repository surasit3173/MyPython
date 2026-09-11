# Research Controller Audit Report (`CONTROLLER_AUDIT.md`)

## Executive Summary
This audit inspects the existing implementation of `research_controller` in `C:\MyPython\research_controller` (and repository path `research_controller/`).

The controller currently acts as a local Python bridge that invokes the Antigravity CLI (`agy`) against local research project directories located under a hardcoded base path `C:\MyPython`. While it includes robust fail-closed workspace verification, prompt generation, and timeout/HOLD status parsing, it lacks GitHub artifact integration, AI reviewer integration, a formal multi-agent state machine, reusable validation gates, and cross-platform path compatibility.

---

## Findings by Category

### 1. Project Identity & Workspace Resolution
- **Current Mechanics**:
  - Accepts `--project` / `--workspace` CLI argument.
  - Resolves path using `resolve_project()` relative to `BASE = Path(r"C:\MyPython")`.
  - Enforces fail-closed verification: project must exist, be a directory, and reside strictly within `BASE`. Path traversal (`..`) and pointing to `BASE` itself are prohibited.
- **Limitations**:
  - Hardcoded `BASE = Path(r"C:\MyPython")` breaks when tests or execution run on Unix/Linux environments (e.g. `/app`) or when projects reside in alternative repository locations.

### 2. Agent Invocation & Prompt Mechanics
- **Current Mechanics**:
  - Searches for `agy.exe` via `AGY_EXE` environment variable, `%LOCALAPPDATA%\agy\bin\agy.exe`, or `PATH`.
  - Invokes `agy` using `--add-dir <absolute_project_path>` and `--print-timeout <duration>` (default `30m`). Uses `--dangerously-skip-permissions` when `--autonomous` is set.
  - Does **NOT** use `--project` flag when executing `agy`.
  - Generates prompts via `build_prompt()` embedding strict rules against fabrication, modifying frozen evidence, or external publishing.

### 3. Result Capture & Parsing
- **Current Mechanics**:
  - Captures `stdout` and `stderr` via `subprocess.Popen`.
  - `parse_agy_output()` handles JSON (`--output-format json`), streaming NDJSON (`--output-format stream-json`), and plain text fallbacks.
  - Detects AGY print timeout banners (`[agy] print timeout after... with turn in progress; returning partial output`) and marks status as `TIMEOUT`.
  - Detects scientific hold conditions (`HOLD: ...`) or headless permission denials and marks status as `HOLD`.

### 4. Failure & Exit Status Handling
- **Current Mechanics**:
  - `determine_status()` assigns `PASS`, `TIMEOUT`, `HOLD`, `FAIL`, `RAW_TEXT`, or `UNKNOWN`.
  - Returns exit code 0 on `PASS`, string `"TIMEOUT"` or `"HOLD"` on timeouts/holds, or raises `SystemExit` on `FAIL`.
  - Always writes raw outputs and metadata to the run directory before exiting, ensuring zero loss of partial evidence.

### 5. Artifact & State Persistence
- **Current Mechanics**:
  - Results are saved under `results/<run_id>/` (default `<project>_<timestamp>`).
  - Stores `task_specification.json`, `command_metadata.json`, `raw_agy_output.txt`, `parsed_response.json`, `exit_status.txt`, `timestamp.txt`, and `prompt.txt`.
- **Limitations**:
  - Does not conform to the required GitHub run artifact directory convention (`runs/<project>/<run_id>/`).
  - Lacks `RUN_MANIFEST.json`, `JULES_RESULT.md`, `ANALYSIS_RESULTS/`, `VALIDATION/`, `REVIEW/`, and `FINAL_STATUS.md`.
  - Does not maintain a state file (`STATE.json`) or support resuming interrupted runs.

### 6. External Integrations (GitHub & AI Reviewers)
- **GitHub Integration**: Currently absent. No Git commit/PR tracking or GitHub artifact protocol.
- **AI Reviewer Integration**: Currently absent. No OpenAI (`ChatGPT`), Gemini, or provider abstraction exists.
- **Multi-Agent Mechanics**: Currently single-agent (Jules/AGY only). No review -> feedback loop back to Jules.

### 7. Validation Gates & Scientific Safety
- **Current Mechanics**:
  - Scientific safety rules are embedded in the prompt.
- **Limitations**:
  - No modular, automated validation gates (`DATA_GATE`, `CODE_GATE`, `NUMERICAL_GATE`, `SCIENTIFIC_GATE`, `MANUSCRIPT_GATE`, `REPRODUCIBILITY_GATE`).
  - No explicit human gate to intercept scientific methodology, baseline, or dataset changes.

### 8. Existing Tests & Verification
- **Current Mechanics**:
  - `research_controller/tests/test_controller.py` contains 42 unit test cases.
- **Limitations**:
  - Tests fail on Linux because `Path(r"C:\MyPython")` resolves incorrectly without an environment override or repository root fallback.

---

## Functionality Matrix

| Feature | Status | Notes |
|---|---|---|
| Project Path Isolation | **Working** | Fail-closed checks working; needs cross-platform base dir support |
| AGY / Jules Execution | **Working** | Command building and execution via `--add-dir` working |
| Output Parsing & Timeout Detection | **Working** | Prevents false PASS on print timeouts and HOLD conditions |
| Results Saving | **Partial** | Writes to `results/<run_id>`, needs upgrade to `runs/<project>/<run_id>` |
| GitHub Artifact Protocol | **Missing** | Needs `RUN_MANIFEST.json` and standard artifact hierarchy |
| AI Reviewer Abstraction | **Missing** | Needs `AIReviewer`, `OpenAIReviewer`, `GeminiReviewer`, `MockReviewer` |
| State Machine & Crash Resumption | **Missing** | Needs `INIT` -> `DECISION` state machine with state persistence |
| Reusable Validation Gates | **Missing** | Needs explicit pass/fail/blocked gate checks |
| Human Review Gate | **Missing** | Needs automatic gating for scientific changes |
| Dry-Run Mode | **Missing** | Needs offline deterministic simulation script |

---

## Action Plan for Upgrade
1. Add `RESEARCH_BASE_DIR` fallback logic to `resolve_project()` for cross-platform compatibility.
2. Implement `protocol.py` defining `RUN_MANIFEST.json` schema and GitHub artifact layout.
3. Implement `validation_gates.py` for reusable data/code/numerical/scientific/manuscript/reproducibility validation.
4. Implement `ai_reviewer.py` with provider abstraction (`OpenAIReviewer`, `GeminiReviewer`, `MockReviewer`).
5. Implement `jules_adapter.py` for Jules CLI execution/simulation.
6. Implement `state_machine.py` and upgrade `controller.py` to drive full multi-agent workflow.
7. Implement `dry_run.py` for offline demonstration.
8. Expand test suite in `tests/` and document architecture in `ARCHITECTURE.md`, `PROTOCOL.md`, `README.md`, and `CONTROLLER_IMPLEMENTATION_REPORT.md`.
