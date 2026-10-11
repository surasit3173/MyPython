# GitHub Communication Protocol and Run Manifest (`PROTOCOL.md`)

## Overview
This specification defines the machine-readable manifest and artifact structure used by `research_controller` for GitHub multi-agent coordination.

## Path Isolation & Security Rules
- `project_id` and `run_id` must be non-empty strings.
- Rejects absolute paths (e.g., `/etc/passwd`, `C:\Windows`), drive letters, and `..` traversal components.
- Canonical target directories are resolved and strictly verified to reside within `base_runs_dir` using relative path containment checks.

## Directory Layout
```text
runs/<project_id>/<run_id>/
├── TASK_SPECIFICATION.md
├── RUN_MANIFEST.json
├── JULES_RESULT.md
├── JULES_LOG.jsonl
├── ANALYSIS_RESULTS/
├── VALIDATION/
├── REVIEW/
└── FINAL_STATUS.md
```

## Run Manifest Schema (`RUN_MANIFEST.json`)
```json
{
  "project_id": "CMIP6Lampang",
  "run_id": "run_lampang_001",
  "parent_run_id": null,
  "task_id": "task_trend_audit",
  "agent": "Jules",
  "timestamp": "2026-09-12T00:00:00Z",
  "git_commit": "5f4f2dc",
  "status": "PASS",
  "input_artifacts": [],
  "output_artifacts": [],
  "validation_status": {},
  "review_status": {},
  "next_action": "NONE"
}
```
