"""
Jules Task Dispatcher and Central Brain Write Integration Interface.

Provides send_jules_task interface for ChatGPT / Central Brain to send authorized,
scope-restricted tasks to GitHub/Jules via issue or issue/PR comments.
"""

from typing import Any, Dict, Optional
import json
import logging
from datetime import datetime, timezone

from github_client import (
    GitHubClient,
    GitHubClientError,
    GitHubAuthorizationError,
    validate_repository_name,
    redact_secrets,
)
from project_isolation import validate_project_scope, ProjectIsolationError

logger = logging.getLogger("jules_bridge")


def format_jules_task_message(task_content: str, project_scope: str) -> str:
    """
    Construct a deterministic @jules task message payload enforcing scope boundaries.
    """
    clean_task = task_content.strip() if task_content else ""
    return f"""@jules
Execute the following authorized task:

{clean_task}

SCOPE RESTRICTION:
- Project Scope: {project_scope}
- Do NOT modify files outside the declared project scope '{project_scope}'.
- Do NOT modify raw scientific data or frozen scientific outputs.
- Return results through the normal GitHub PR workflow.
""".strip()


def send_jules_task(
    repository: str,
    task: str,
    scope: str,
    authorization: str,
    target_type: str = "ISSUE_COMMENT",
    target_id: Optional[int] = None,
    issue_title: Optional[str] = None,
    client: Optional[GitHubClient] = None,
) -> Dict[str, Any]:
    """
    Central Brain Interface to send authorized write actions to GitHub / Jules.

    Parameters:
    - repository: Repository in 'owner/repo' format (e.g. 'surasit3173/MyPython')
    - task: Task specification or instruction text
    - scope: Project scope identifier (e.g. 'research_controller', 'CMIP6Uttaradit/paper3')
    - authorization: Explicit authorization string (must be 'EXPLICIT_HUMAN_AUTHORIZED')
    - target_type: Action target ('ISSUE_COMMENT', 'PR_COMMENT', 'CREATE_ISSUE')
    - target_id: Issue or PR number (required for comments)
    - issue_title: Title when target_type is 'CREATE_ISSUE'
    - client: GitHubClient instance (optional, created if None)

    Returns:
    - Dict with execution outcome, audit metadata, and GitHub API response.
    """
    # 1. Validate authorization
    if authorization != "EXPLICIT_HUMAN_AUTHORIZED":
        raise GitHubAuthorizationError("FAIL-CLOSED: Unauthorized operation. Authorization must be 'EXPLICIT_HUMAN_AUTHORIZED'.")

    # 2. Validate repository
    valid_repo = validate_repository_name(repository)

    # 3. Validate project scope against Project Isolation Gate
    valid_scope = validate_project_scope(scope)

    # 4. Validate task payload
    if not isinstance(task, str) or not task.strip():
        raise ValueError("FAIL-CLOSED: Task payload cannot be empty.")

    # 5. Initialize client if not provided
    gh_client = client or GitHubClient()

    # 6. Format deterministic @jules message
    formatted_message = format_jules_task_message(task_content=task, project_scope=valid_scope)

    # 7. Audit log creation (redacting any accidental secrets in prompt)
    audit_event = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "repository": valid_repo,
        "scope": valid_scope,
        "target_type": target_type,
        "target_id": target_id,
        "authorization": authorization,
        "dry_run": gh_client.dry_run,
        "message_preview": redact_secrets(formatted_message[:200]),
    }

    # 8. Dispatch based on target_type
    try:
        if target_type == "ISSUE_COMMENT":
            if not isinstance(target_id, int) or target_id <= 0:
                raise ValueError(f"FAIL-CLOSED: Target ID (issue number) must be a positive integer, got '{target_id}'.")

            api_result = gh_client.add_issue_comment(
                repository=valid_repo,
                issue_number=target_id,
                body=formatted_message,
                authorization=authorization,
            )
        elif target_type == "PR_COMMENT":
            if not isinstance(target_id, int) or target_id <= 0:
                raise ValueError(f"FAIL-CLOSED: Target ID (PR number) must be a positive integer, got '{target_id}'.")

            api_result = gh_client.add_pr_comment(
                repository=valid_repo,
                pr_number=target_id,
                body=formatted_message,
                authorization=authorization,
            )
        elif target_type == "CREATE_ISSUE":
            title = issue_title or f"Automated Jules Task: [{valid_scope}]"
            api_result = gh_client.create_issue(
                repository=valid_repo,
                title=title,
                body=formatted_message,
                authorization=authorization,
                labels=["jules-task", "automated"],
            )
        else:
            raise ValueError(f"FAIL-CLOSED: Unsupported target_type '{target_type}'. Allowed: ISSUE_COMMENT, PR_COMMENT, CREATE_ISSUE.")

        return {
            "status": "SUCCESS" if not gh_client.dry_run else "DRY_RUN_SUCCESS",
            "audit_event": audit_event,
            "github_result": api_result,
        }

    except Exception as e:
        logger.error(f"Failed to dispatch Jules task: {redact_secrets(str(e))}")
        raise
