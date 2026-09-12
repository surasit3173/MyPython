"""
Secure GitHub API Client Adapter for Research Controller.

Handles authorized write operations to GitHub (creating issues, issue comments, PR comments)
with strict secret redaction, authorization checks, dry-run mode, retry logic, and error handling.
"""

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple, List


class GitHubClientError(Exception):
    """Base exception for GitHub API client errors."""
    pass


class GitHubAuthenticationError(GitHubClientError):
    """Raised when authentication credentials are missing or invalid."""
    pass


class GitHubAuthorizationError(GitHubClientError):
    """Raised when an action is unauthorized or forbidden."""
    pass


class GitHubResourceNotFoundError(GitHubClientError):
    """Raised when the target repository, issue, or PR is not found."""
    pass


class GitHubRateLimitError(GitHubClientError):
    """Raised when GitHub API rate limits are exceeded."""
    pass


# Allowlist of write operations supported by this integration.
ALLOWED_WRITE_OPERATIONS = {
    "CREATE_ISSUE",
    "ADD_ISSUE_COMMENT",
    "ADD_PR_COMMENT",
    "GET_ISSUE",
    "GET_PR",
    "GET_COMMIT",
}

# Operations that are explicitly NOT automatically allowed
FORBIDDEN_AUTOMATED_OPERATIONS = {
    "MERGE_PR",
    "DELETE_BRANCH",
    "DELETE_REPO",
    "MODIFY_PROTECTED_BRANCH",
    "MODIFY_SECURITY_CONFIG",
}


def redact_secrets(text: str) -> str:
    """
    Redact potential secrets (GitHub PATs, API keys, Bearer tokens) from string or log output.
    """
    if not isinstance(text, str):
        return str(text)

    # Patterns matching GitHub tokens (ghp_, gho_, ghu_, ghs_, ghr_), Bearer tokens, etc.
    patterns = [
        (r"ghp_[A-Za-z0-9_]{36,255}", "[REDACTED_GITHUB_PAT]"),
        (r"gho_[A-Za-z0-9_]{36,255}", "[REDACTED_GITHUB_OAUTH]"),
        (r"ghu_[A-Za-z0-9_]{36,255}", "[REDACTED_GITHUB_USER_TOKEN]"),
        (r"ghs_[A-Za-z0-9_]{36,255}", "[REDACTED_GITHUB_APP_TOKEN]"),
        (r"ghr_[A-Za-z0-9_]{36,255}", "[REDACTED_GITHUB_REFRESH_TOKEN]"),
        (r"github_pat_[A-Za-z0-9_]{22,255}", "[REDACTED_GITHUB_PAT]"),
        (r"Bearer\s+[A-Za-z0-9_.\-]{10,}", "Bearer [REDACTED_TOKEN]"),
        (r"token\s+[A-Za-z0-9_.\-]{10,}", "token [REDACTED_TOKEN]"),
    ]

    redacted = text
    for pattern, replacement in patterns:
        redacted = re.sub(pattern, replacement, redacted)

    return redacted


def validate_repository_name(repository: str) -> str:
    """
    Validate that repository name matches 'owner/repo' format.
    """
    if not isinstance(repository, str) or not repository.strip():
        raise GitHubClientError("FAIL-CLOSED: Repository string must be non-empty.")

    repo = repository.strip()
    pattern = r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"
    if not re.match(pattern, repo):
        raise GitHubClientError(f"FAIL-CLOSED: Invalid repository format '{repository}'. Expected 'owner/repo'.")

    return repo


class GitHubClient:
    """
    Secure GitHub REST API adapter with dry-run support, secret redaction, and authorization checks.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        dry_run: Optional[bool] = None,
        base_url: str = "https://api.github.com",
        max_retries: int = 3,
        timeout: float = 30.0,
    ):
        # Resolve token from parameter or environment variables
        self.token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

        # Resolve dry_run setting
        if dry_run is not None:
            self.dry_run = dry_run
        else:
            self.dry_run = os.environ.get("DRY_RUN", "").lower() in ("true", "1", "yes")

        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.timeout = timeout

    def _get_headers(self) -> Dict[str, str]:
        if not self.token and not self.dry_run:
            raise GitHubAuthenticationError("FAIL-CLOSED: GitHub authentication token is missing (GITHUB_TOKEN / GH_TOKEN).")

        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "ResearchController-GitHubClient/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        return headers

    def validate_operation(self, operation: str) -> str:
        """
        Validate that operation is allowed and not explicitly forbidden.
        """
        if not isinstance(operation, str) or not operation.strip():
            raise GitHubAuthorizationError("FAIL-CLOSED: Operation name must be non-empty.")
        op = operation.strip().upper()
        if op in FORBIDDEN_AUTOMATED_OPERATIONS:
            raise GitHubAuthorizationError(f"FAIL-CLOSED: Operation '{op}' is forbidden from automated execution.")
        if op not in ALLOWED_WRITE_OPERATIONS:
            raise GitHubAuthorizationError(f"FAIL-CLOSED: Operation '{op}' is not in allowed write operations list.")
        return op

    def _request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
        authorization: Optional[str] = None,
        operation: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a request to GitHub API with timeout, retries, error mapping, and secret redaction.
        Enforces authorization check and operation validation fail-closed.
        """
        method_upper = method.upper() if isinstance(method, str) else "GET"

        # Check operation if provided
        if operation:
            self.validate_operation(operation)

        # Enforce authorization requirement for write methods or write operations
        is_write = method_upper in ("POST", "PUT", "PATCH", "DELETE")
        if is_write or (authorization is not None and authorization != "EXPLICIT_HUMAN_AUTHORIZED"):
            if authorization != "EXPLICIT_HUMAN_AUTHORIZED":
                raise GitHubAuthorizationError(
                    f"FAIL-CLOSED: Operation requires explicit human authorization "
                    f"('EXPLICIT_HUMAN_AUTHORIZED'), got '{authorization}'."
                )

        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        data = None
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"

        last_exception = None

        for attempt in range(1, self.max_retries + 1):
            try:
                req = urllib.request.Request(url, data=data, headers=headers, method=method_upper)
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    resp_data = resp.read().decode("utf-8", errors="replace")
                    return json.loads(resp_data) if resp_data else {}

            except urllib.error.HTTPError as e:
                error_body = e.read().decode("utf-8", errors="replace") if e.fp else ""
                redacted_err = redact_secrets(error_body)

                if e.code == 401:
                    raise GitHubAuthenticationError(f"GitHub API 401 Unauthorized: {redacted_err}") from e
                elif e.code == 403:
                    if "rate limit" in redacted_err.lower():
                        raise GitHubRateLimitError(f"GitHub API 403 Rate Limit Exceeded: {redacted_err}") from e
                    raise GitHubAuthorizationError(f"GitHub API 403 Forbidden: {redacted_err}") from e
                elif e.code == 404:
                    raise GitHubResourceNotFoundError(f"GitHub API 404 Not Found at {endpoint}: {redacted_err}") from e
                elif e.code >= 500:
                    last_exception = GitHubClientError(f"GitHub API Server Error {e.code}: {redacted_err}")
                    if attempt < self.max_retries:
                        time.sleep(1.0 * attempt)
                        continue
                    raise last_exception
                else:
                    raise GitHubClientError(f"GitHub API HTTP Error {e.code}: {redacted_err}") from e

            except urllib.error.URLError as e:
                last_exception = GitHubClientError(f"GitHub API Connection Error: {redact_secrets(str(e.reason))}")
                if attempt < self.max_retries:
                    time.sleep(1.0 * attempt)
                    continue
                raise last_exception

            except Exception as e:
                raise GitHubClientError(f"Unexpected error communicating with GitHub API: {redact_secrets(str(e))}") from e

        if last_exception:
            raise last_exception
        raise GitHubClientError("GitHub API request failed after retries.")

    def create_issue(
        self,
        repository: str,
        title: str,
        body: str,
        authorization: str = "EXPLICIT_HUMAN_AUTHORIZED",
        labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a GitHub issue in the specified repository.
        """
        repo = validate_repository_name(repository)
        self.validate_operation("CREATE_ISSUE")

        if authorization != "EXPLICIT_HUMAN_AUTHORIZED":
            raise GitHubAuthorizationError("FAIL-CLOSED: Write operation requires authorization 'EXPLICIT_HUMAN_AUTHORIZED'.")

        payload = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels

        if self.dry_run:
            return {
                "dry_run": True,
                "operation": "CREATE_ISSUE",
                "repository": repo,
                "intended_payload": payload,
                "authorization": authorization,
                "status": "DRY_RUN_SUCCESS",
            }

        endpoint = f"/repos/{repo}/issues"
        return self._request("POST", endpoint, payload=payload, authorization=authorization, operation="CREATE_ISSUE")

    def add_issue_comment(
        self,
        repository: str,
        issue_number: int,
        body: str,
        authorization: str = "EXPLICIT_HUMAN_AUTHORIZED",
    ) -> Dict[str, Any]:
        """
        Add a comment to a GitHub issue or PR.
        """
        repo = validate_repository_name(repository)
        if not isinstance(issue_number, int) or issue_number <= 0:
            raise GitHubClientError(f"FAIL-CLOSED: Issue number must be a positive integer, got '{issue_number}'.")

        self.validate_operation("ADD_ISSUE_COMMENT")

        if authorization != "EXPLICIT_HUMAN_AUTHORIZED":
            raise GitHubAuthorizationError("FAIL-CLOSED: Write operation requires authorization 'EXPLICIT_HUMAN_AUTHORIZED'.")

        payload = {"body": body}

        if self.dry_run:
            return {
                "dry_run": True,
                "operation": "ADD_ISSUE_COMMENT",
                "repository": repo,
                "issue_number": issue_number,
                "intended_payload": payload,
                "authorization": authorization,
                "status": "DRY_RUN_SUCCESS",
            }

        endpoint = f"/repos/{repo}/issues/{issue_number}/comments"
        return self._request("POST", endpoint, payload=payload, authorization=authorization, operation="ADD_ISSUE_COMMENT")

    def add_pr_comment(
        self,
        repository: str,
        pr_number: int,
        body: str,
        authorization: str = "EXPLICIT_HUMAN_AUTHORIZED",
    ) -> Dict[str, Any]:
        """
        Add a comment to a GitHub PR (GitHub issue comment endpoint handles both Issues and PRs).
        """
        repo = validate_repository_name(repository)
        if not isinstance(pr_number, int) or pr_number <= 0:
            raise GitHubClientError(f"FAIL-CLOSED: PR number must be a positive integer, got '{pr_number}'.")

        self.validate_operation("ADD_PR_COMMENT")

        if authorization != "EXPLICIT_HUMAN_AUTHORIZED":
            raise GitHubAuthorizationError("FAIL-CLOSED: Write operation requires authorization 'EXPLICIT_HUMAN_AUTHORIZED'.")

        payload = {"body": body}

        if self.dry_run:
            return {
                "dry_run": True,
                "operation": "ADD_PR_COMMENT",
                "repository": repo,
                "pr_number": pr_number,
                "intended_payload": payload,
                "authorization": authorization,
                "status": "DRY_RUN_SUCCESS",
            }

        endpoint = f"/repos/{repo}/issues/{pr_number}/comments"
        return self._request("POST", endpoint, payload=payload, authorization=authorization, operation="ADD_PR_COMMENT")

    def get_pr(self, repository: str, pr_number: int) -> Dict[str, Any]:
        """
        Get information about a GitHub PR.
        """
        repo = validate_repository_name(repository)
        if not isinstance(pr_number, int) or pr_number <= 0:
            raise GitHubClientError(f"FAIL-CLOSED: PR number must be a positive integer, got '{pr_number}'.")

        self.validate_operation("GET_PR")

        if self.dry_run:
            return {
                "dry_run": True,
                "operation": "GET_PR",
                "repository": repo,
                "pr_number": pr_number,
                "status": "DRY_RUN_SUCCESS",
            }

        endpoint = f"/repos/{repo}/pulls/{pr_number}"
        return self._request("GET", endpoint, operation="GET_PR")

    def get_issue(self, repository: str, issue_number: int) -> Dict[str, Any]:
        """
        Get information about a GitHub issue.
        """
        repo = validate_repository_name(repository)
        if not isinstance(issue_number, int) or issue_number <= 0:
            raise GitHubClientError(f"FAIL-CLOSED: Issue number must be a positive integer, got '{issue_number}'.")

        self.validate_operation("GET_ISSUE")

        if self.dry_run:
            return {
                "dry_run": True,
                "operation": "GET_ISSUE",
                "repository": repo,
                "issue_number": issue_number,
                "status": "DRY_RUN_SUCCESS",
            }

        endpoint = f"/repos/{repo}/issues/{issue_number}"
        return self._request("GET", endpoint, operation="GET_ISSUE")

    def get_commit(self, repository: str, commit_sha: str) -> Dict[str, Any]:
        """
        Get information about a GitHub commit.
        """
        repo = validate_repository_name(repository)
        if not isinstance(commit_sha, str) or not re.match(r"^[a-fA-F0-9]{7,40}$", commit_sha.strip()):
            raise GitHubClientError(f"FAIL-CLOSED: Invalid commit SHA format '{commit_sha}'.")

        sha = commit_sha.strip()
        self.validate_operation("GET_COMMIT")

        if self.dry_run:
            return {
                "dry_run": True,
                "operation": "GET_COMMIT",
                "repository": repo,
                "commit_sha": sha,
                "status": "DRY_RUN_SUCCESS",
            }

        endpoint = f"/repos/{repo}/commits/{sha}"
        return self._request("GET", endpoint, operation="GET_COMMIT")
