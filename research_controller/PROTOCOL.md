# GitHub Communication Protocol & Manifest Specification (`PROTOCOL.md`)

## Overview
This document defines the machine-readable communication protocol and artifact directory structure for all research workflow runs. GitHub artifacts serve as the asynchronous communication layer between human researchers, Jules execution agents, and AI Reviewers.

---

## Artifact Directory Hierarchy
Every run creates an isolated directory structure under `runs/<project>/<run_id>/`:

```text
runs/<project>/<run_id>/
├── RUN_MANIFEST.json         # Authoritative machine-readable run manifest
├── STATE.json                # State machine persistent state for crash recovery
├── TASK_SPECIFICATION.md     # Markdown rendering of task specification and prompt
├── JULES_RESULT.md           # Summary execution result from Jules
├── JULES_LOG.jsonl           # Execution stream logs and exit status
├── ANALYSIS_RESULTS/         # Directory for generated figures, tables, and metrics
├── VALIDATION/               # Directory for validation gate reports and evidence
├── REVIEW/                   # Directory for AI review artifacts
│   ├── CHATGPT_REVIEW.json   # Machine-readable AI review output
│   └── CHATGPT_REVIEW.md     # Human-readable AI review summary
└── FINAL_STATUS.md           # Authoritative final status banner (PASS / FAIL / BLOCKED / NEEDS_HUMAN_REVIEW)
```

---

## Manifest Schema (`RUN_MANIFEST.json`)

```json
{
  "project_id": "CMIP6Lampang",
  "run_id": "CMIP6Lampang_20260911T120000Z",
  "parent_run_id": null,
  "task_id": "task_audit_01",
  "agent": "Jules",
  "timestamp": "2026-09-11T12:00:00.000000+00:00",
  "git_commit": "a1b2c3d4",
  "status": "PASS",
  "input_artifacts": [
    "specs/project_audit.json"
  ],
  "output_artifacts": [
    "ANALYSIS_RESULTS/results.csv"
  ],
  "validation_status": {
    "overall_status": "PASS",
    "gates": {
      "DATA_GATE": { "status": "PASS", "message": "Data verified" },
      "CODE_GATE": { "status": "PASS", "message": "Code executed cleanly" },
      "NUMERICAL_GATE": { "status": "PASS", "message": "Sanity checks passed" },
      "SCIENTIFIC_GATE": { "status": "PASS", "message": "No contradiction" },
      "MANUSCRIPT_GATE": { "status": "PASS", "message": "Traceability satisfied" },
      "REPRODUCIBILITY_GATE": { "status": "PASS", "message": "Manifest complete" }
    }
  },
  "review_status": {
    "REVIEW_STATUS": "PASS",
    "FINDINGS": "Artifacts verified.",
    "REQUIRED_ACTIONS": [],
    "EVIDENCE": {}
  },
  "next_action": "NONE"
}
```

---

## Status Values
- `INIT`: Task created and initialized.
- `RUNNING`: Execution currently in progress.
- `PASS`: Task completed, validated, and approved by AI Reviewer.
- `FAIL`: Execution or code error occurred.
- `HOLD`: Scientific hold requested (missing data or unresolved conflict).
- `TIMEOUT`: Execution timed out (print timeout / partial turn).
- `BLOCKED`: Validation gate blocked run due to scientific contradiction or invalid data.
- `NEEDS_HUMAN_REVIEW`: Gated by human review rule due to methodology or scientific specification change.
- `CORRECTION_REQUIRED`: AI Reviewer requested specific corrections from Jules.
