# Research Controller Architecture (`ARCHITECTURE.md`)

## Overview
The Research Controller provides an automated infrastructure bridge linking GitHub, Jules (execution agent), AI Reviewers (OpenAI/Gemini/Mock), and deterministic validation gates into a multi-agent research workflow.

```text
                    GitHub
                       │
                       │ source of truth
                       ▼
              Research Controller
                 /            \
                /              \
               ▼                ▼
            Jules            AI Reviewer
          (execution)      (ChatGPT/Gemini/Other)
               │                │
               ▼                ▼
             code             review
             data             findings
             results          validation
                \              /
                 \            /
                  ▼          ▼
                     GitHub
                       │
                       ▼
                  next stage
```

---

## State Machine Workflow

```text
INIT
 │
 ▼
SPEC_VALIDATION ──[Scientific Change / Methodology Edit?]──► HUMAN_REVIEW (Gate Intercept)
 │
 ▼
JULES_EXECUTION (Jules Adapter / AGY CLI)
 │
 ▼
JULES_VALIDATION (DATA_GATE, CODE_GATE, NUMERICAL_GATE, SCIENTIFIC_GATE, MANUSCRIPT_GATE, REPRODUCIBILITY_GATE)
 │
 ├──► BLOCKED (Scientific contradiction / Invalid negative variance)
 │
 ▼
RESULTS_COMMITTED
 │
 ▼
AI_REVIEW (OpenAIReviewer / GeminiReviewer / MockReviewer)
 │
 ▼
REVIEW_COMMITTED
 │
 ▼
DECISION
 ├── PASS ───────────► FINAL (PASS)
 ├── NEEDS_HUMAN ────► HUMAN_REVIEW
 └── FAIL ───────────► CORRECTION_REQUIRED ──► JULES_CORRECTION ──► REVALIDATION
```

---

## Component Roles

1. **`controller.py`**: Entry point and CLI dispatcher. Resolves project workspaces under strict fail-closed boundaries.
2. **`protocol.py`**: Defines `RunManifest` schema and manages standard GitHub artifact directory layout (`runs/<project>/<run_id>/`).
3. **`validation_gates.py`**: Automated gate checks (`DATA_GATE`, `CODE_GATE`, `NUMERICAL_GATE`, `SCIENTIFIC_GATE`, `MANUSCRIPT_GATE`, `REPRODUCIBILITY_GATE`).
4. **`jules_adapter.py`**: Invokes or simulates Jules/AGY CLI execution, captures logs (`JULES_LOG.jsonl`), and formats summary results (`JULES_RESULT.md`).
5. **`ai_reviewer.py`**: Provider-agnostic AI reviewer interface (`AIReviewer`) supporting `OpenAIReviewer`, `GeminiReviewer`, and `MockReviewer`.
6. **`state_machine.py`**: State machine engine (`ResearchWorkflowRunner`). Handles state transitions, crash recovery (`STATE.json`), and human review intercepts.
7. **`dry_run.py`**: Offline simulation runner for end-to-end verification without live API calls or dataset modifications.
