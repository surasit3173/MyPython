# ChatGPT → GitHub / Jules Write Integration Guide

## 1. Architecture

```text
ChatGPT / Central Brain
        ↓
[ send_jules_task() ] (research_controller / jules_bridge.py)
        ↓
[ Project Isolation Gate ] (project_isolation.py)
        ↓
[ Secure GitHub REST Client ] (github_client.py)
        ↓
GitHub API (Issue / Issue Comment / PR Comment)
        ↓
Google Jules (Reactive Mode via @jules mention or issue trigger)
        ↓
Jules Executes Task
        ↓
GitHub PR Created / Updated
        ↓
ChatGPT / Human Reviews Results
```

## 2. Authentication
- Authentication is handled exclusively via environment variables (`GITHUB_TOKEN` or `GH_TOKEN`).
- Secrets are NEVER hard-coded in source files or stored in Git.
- Secrets are automatically redacted in error messages and audit logs using `github_client.redact_secrets()`.

## 3. Required GitHub Permissions
When configuring a GitHub Personal Access Token (PAT) or GitHub App token:
- **Repository permissions**:
  - `Issues`: **Read & Write** (to create issues and post `@jules` task comments)
  - `Pull requests`: **Read & Write** (to post comments on PRs and inspect PR status)
  - `Contents`: **Read-only** (by default)

## 4. Security Model
- **Fail-Closed Design**: Any missing credential, unauthorized scope, or invalid repository format immediately aborts execution without making API calls.
- **Read-Only Default**: Standard operations operate with read-only permissions by default; write operations require explicit human authorization (`authorization='EXPLICIT_HUMAN_AUTHORIZED'`).
- **Secret Redaction**: Tokens and credentials match regex patterns (`ghp_`, `gho_`, `Bearer`, etc.) and are masked in log outputs.

## 5. Allowed Operations
- `CREATE_ISSUE`: Create a GitHub issue for task tracking or dispatching.
- `ADD_ISSUE_COMMENT`: Add a comment containing an authorized `@jules` task instruction to an issue.
- `ADD_PR_COMMENT`: Add a comment containing an authorized `@jules` task instruction to a PR.
- `GET_PR` / `GET_ISSUE`: Inspect current status of PRs or issues.

## 6. Forbidden Operations
The following operations are strictly NOT automatically permitted and require direct manual human intervention on GitHub:
- `MERGE_PR` (automatic merging is strictly prohibited)
- `DELETE_BRANCH` / `DELETE_REPO`
- Modifying protected branch configurations
- Modifying scientific datasets or manuscript results
- Modifying security settings or `AGENTS.md`

## 7. Jules Triggering Mechanism
Jules operates in Reactive Mode by monitoring repository events on GitHub.
The integration dispatches structured, deterministic task payloads containing the `@jules` handle and project scope constraints:

```text
@jules
Execute the following authorized task:

[TASK CONTENT]

SCOPE RESTRICTION:
- Project Scope: <project_scope>
- Do NOT modify files outside the declared project scope '<project_scope>'.
- Do NOT modify raw scientific data or frozen scientific outputs.
- Return results through the normal GitHub PR workflow.
```

## 8. Configuration & Environment Variables
- `GITHUB_TOKEN` or `GH_TOKEN`: GitHub authentication token.
- `DRY_RUN`: Set to `true`, `1`, or `yes` to enable dry-run mode (logs and validates request without sending HTTP write requests).

## 9. Dry-Run Mode
When `DRY_RUN=true` or passed via `GitHubClient(dry_run=True)`:
- Validates repository name format.
- Validates project scope against isolation gate.
- Validates authorization parameter (`EXPLICIT_HUMAN_AUTHORIZED`).
- Generates and logs intended payload and audit event.
- Performs NO HTTP write requests.
- Returns status `"DRY_RUN_SUCCESS"`.

## 10. Testing
Unit tests with mocks are located in `research_controller/tests/test_github_jules_integration.py`.
Run unit tests via:
```bash
PYTHONPATH=research_controller python3 -m unittest discover -s research_controller/tests
```

## 11. Live Integration Testing
Live integration testing requires a valid `GITHUB_TOKEN` set in the environment and a target repository.
If credentials are absent during audits, live testing status must be reported as `LIVE_TEST = NOT_AVAILABLE`.

## 12. Human Approval Gates
Consequential operations (such as code reviews, PR merges, or production runs) require explicit human review and authorization before merge.

## 13. Limitations & Platform Context
- The standard ChatGPT GitHub connector in web interfaces is read-only.
- Repository code cannot override ChatGPT platform-level connector permissions.
- Write actions must be executed through this `research_controller` write integration module using an authorized GitHub token.
