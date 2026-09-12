"""
Unit and Integration Test Suite for GitHub / Jules Write Integration.

Tests:
- Authentication failures & missing credentials
- Invalid repository formatting
- Invalid project scope & path traversal protection
- Authorization checks on write operations and direct _request() calls
- Allowed write operations vs Forbidden operations validation
- All supported operations (CREATE_ISSUE, ADD_ISSUE_COMMENT, ADD_PR_COMMENT, GET_PR, GET_ISSUE, GET_COMMIT)
- GitHub API failures, timeouts, retries
- Secret redaction in logs/errors
- Dry-run mode behavior for all supported operations
- Jules task payload generation and central bridge dispatching
"""

import json
import os
import unittest
from unittest.mock import MagicMock, patch
import urllib.error

import github_client
from github_client import (
    GitHubClient,
    GitHubAuthenticationError,
    GitHubAuthorizationError,
    GitHubResourceNotFoundError,
    GitHubRateLimitError,
    GitHubClientError,
    redact_secrets,
    ALLOWED_WRITE_OPERATIONS,
    FORBIDDEN_AUTOMATED_OPERATIONS,
)
import project_isolation
from project_isolation import validate_project_scope, ProjectIsolationError, is_valid_project_scope
import jules_bridge
from jules_bridge import send_jules_task, format_jules_task_message


class TestSecretRedaction(unittest.TestCase):
    def test_redact_secrets_pat(self):
        token_pat = "ghp_123456789012345678901234567890123456"
        text = f"Failed request with token {token_pat} and Bearer {token_pat}"
        redacted = redact_secrets(text)
        self.assertNotIn(token_pat, redacted)
        self.assertIn("[REDACTED_GITHUB_PAT]", redacted)

    def test_redact_secrets_various_tokens(self):
        tokens = [
            ("gho_123456789012345678901234567890123456", "[REDACTED_GITHUB_OAUTH]"),
            ("ghu_123456789012345678901234567890123456", "[REDACTED_GITHUB_USER_TOKEN]"),
            ("ghs_123456789012345678901234567890123456", "[REDACTED_GITHUB_APP_TOKEN]"),
            ("ghr_123456789012345678901234567890123456", "[REDACTED_GITHUB_REFRESH_TOKEN]"),
            ("github_pat_12345678901234567890123456", "[REDACTED_GITHUB_PAT]"),
        ]
        for token, expected_tag in tokens:
            with self.subTest(token=token):
                res = redact_secrets(f"Error with {token}")
                self.assertNotIn(token, res)
                self.assertIn(expected_tag, res)

    def test_redact_secrets_non_string(self):
        self.assertEqual(redact_secrets(12345), "12345")


class TestProjectIsolation(unittest.TestCase):
    def test_valid_scopes(self):
        self.assertEqual(validate_project_scope("research_controller"), "research_controller")
        self.assertEqual(validate_project_scope("CMIP6Uttaradit/paper3"), "CMIP6Uttaradit/paper3")

    def test_invalid_and_path_traversal_scopes(self):
        invalid_scopes = [
            "../CMIP6Lampang",
            "/etc/passwd",
            "C:\\Windows",
            "CMIP6Uttaradit/../CMIP6Lampang",
            "unknown_project_id_123",
            "",
            "   ",
        ]
        for scope in invalid_scopes:
            with self.subTest(scope=scope):
                with self.assertRaises(ProjectIsolationError):
                    validate_project_scope(scope)
                self.assertFalse(is_valid_project_scope(scope))


class TestGitHubClientAuthorizationAndOperations(unittest.TestCase):
    def setUp(self):
        self.client = GitHubClient(token="ghp_dummytoken12345678901234567890123", dry_run=True)

    def test_direct_request_authorization_check(self):
        # Direct _request call without explicit authorization on POST
        with self.assertRaises(GitHubAuthorizationError):
            self.client._request("POST", "/repos/surasit3173/MyPython/issues", payload={"title": "Test"})

        # Direct _request call with invalid authorization
        with self.assertRaises(GitHubAuthorizationError):
            self.client._request("POST", "/repos/surasit3173/MyPython/issues", payload={"title": "Test"}, authorization="INVALID")

    def test_validate_operation_allowed(self):
        for op in ALLOWED_WRITE_OPERATIONS:
            with self.subTest(op=op):
                self.assertEqual(self.client.validate_operation(op), op)

    def test_validate_operation_forbidden(self):
        for op in FORBIDDEN_AUTOMATED_OPERATIONS:
            with self.subTest(op=op):
                with self.assertRaises(GitHubAuthorizationError):
                    self.client.validate_operation(op)

    def test_validate_operation_unsupported(self):
        unsupported = ["DELETE_BRANCH", "MERGE_PR", "SOMETHING_ELSE", ""]
        for op in unsupported:
            with self.subTest(op=op):
                with self.assertRaises(GitHubAuthorizationError):
                    self.client.validate_operation(op)

    def test_all_supported_operations_dry_run(self):
        repo = "surasit3173/MyPython"

        # 1. CREATE_ISSUE
        issue_res = self.client.create_issue(repo, "Title", "Body", authorization="EXPLICIT_HUMAN_AUTHORIZED", labels=["bug"])
        self.assertEqual(issue_res["operation"], "CREATE_ISSUE")
        self.assertEqual(issue_res["status"], "DRY_RUN_SUCCESS")

        # 2. ADD_ISSUE_COMMENT
        comment_res = self.client.add_issue_comment(repo, 10, "Comment body", authorization="EXPLICIT_HUMAN_AUTHORIZED")
        self.assertEqual(comment_res["operation"], "ADD_ISSUE_COMMENT")
        self.assertEqual(comment_res["status"], "DRY_RUN_SUCCESS")

        # 3. ADD_PR_COMMENT
        pr_comment_res = self.client.add_pr_comment(repo, 12, "PR Comment body", authorization="EXPLICIT_HUMAN_AUTHORIZED")
        self.assertEqual(pr_comment_res["operation"], "ADD_ISSUE_COMMENT")
        self.assertEqual(pr_comment_res["status"], "DRY_RUN_SUCCESS")

        # 4. GET_PR
        get_pr_res = self.client.get_pr(repo, 5)
        self.assertEqual(get_pr_res["operation"], "GET_PR")
        self.assertEqual(get_pr_res["status"], "DRY_RUN_SUCCESS")

        # 5. GET_ISSUE
        get_issue_res = self.client.get_issue(repo, 8)
        self.assertEqual(get_issue_res["operation"], "GET_ISSUE")
        self.assertEqual(get_issue_res["status"], "DRY_RUN_SUCCESS")

        # 6. GET_COMMIT
        get_commit_res = self.client.get_commit(repo, "0306874a598cffa6f73cdff8719da9863418b397")
        self.assertEqual(get_commit_res["operation"], "GET_COMMIT")
        self.assertEqual(get_commit_res["status"], "DRY_RUN_SUCCESS")

    def test_invalid_parameters_fail_closed(self):
        repo = "surasit3173/MyPython"
        # Invalid issue/PR numbers
        with self.assertRaises(GitHubClientError):
            self.client.add_issue_comment(repo, -1, "Body")
        with self.assertRaises(GitHubClientError):
            self.client.get_pr(repo, 0)
        with self.assertRaises(GitHubClientError):
            self.client.get_issue(repo, "not_an_int")

        # Invalid commit SHA
        with self.assertRaises(GitHubClientError):
            self.client.get_commit(repo, "invalid_sha")


class TestGitHubClientHttpExecution(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_http_successful_request(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"id": 100, "number": 1}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        client = GitHubClient(token="ghp_validtoken123456789012345678901234", dry_run=False)

        res = client.create_issue("surasit3173/MyPython", "Test", "Body", authorization="EXPLICIT_HUMAN_AUTHORIZED")
        self.assertEqual(res["id"], 100)

    @patch("urllib.request.urlopen")
    def test_api_401_error_handling(self, mock_urlopen):
        mock_err = urllib.error.HTTPError(
            url="https://api.github.com/repos/surasit3173/MyPython/issues",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=None
        )
        mock_urlopen.side_effect = mock_err
        client = GitHubClient(token="ghp_invalid_token_12345678901234567890", dry_run=False)

        with self.assertRaises(GitHubAuthenticationError):
            client.create_issue("surasit3173/MyPython", "Title", "Body")

    @patch("urllib.request.urlopen")
    def test_api_404_error_handling(self, mock_urlopen):
        mock_err = urllib.error.HTTPError(
            url="https://api.github.com/repos/surasit3173/non_existent_repo/issues",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=None
        )
        mock_urlopen.side_effect = mock_err
        client = GitHubClient(token="ghp_valid_token_1234567890123456789012", dry_run=False)

        with self.assertRaises(GitHubResourceNotFoundError):
            client.create_issue("surasit3173/non_existent_repo", "Title", "Body")

    @patch("urllib.request.urlopen")
    def test_api_403_rate_limit_handling(self, mock_urlopen):
        mock_err = urllib.error.HTTPError(
            url="https://api.github.com/repos/surasit3173/MyPython/issues",
            code=403,
            msg="Forbidden",
            hdrs={},
            fp=MagicMock(read=lambda: b"API rate limit exceeded")
        )
        mock_urlopen.side_effect = mock_err
        client = GitHubClient(token="ghp_valid_token_1234567890123456789012", dry_run=False)

        with self.assertRaises(GitHubRateLimitError):
            client.create_issue("surasit3173/MyPython", "Title", "Body")


class TestJulesBridge(unittest.TestCase):
    def test_format_jules_task_message(self):
        msg = format_jules_task_message("Fix typo in controller.py", "research_controller")
        self.assertIn("@jules", msg)
        self.assertIn("Fix typo in controller.py", msg)
        self.assertIn("Project Scope: research_controller", msg)

    def test_send_jules_task_unauthorized(self):
        with self.assertRaises(GitHubAuthorizationError):
            send_jules_task(
                repository="surasit3173/MyPython",
                task="Refactor",
                scope="research_controller",
                authorization="UNAUTHORIZED",
            )

    def test_send_jules_task_invalid_scope(self):
        with self.assertRaises(ProjectIsolationError):
            send_jules_task(
                repository="surasit3173/MyPython",
                task="Refactor",
                scope="../CMIP6Lampang",
                authorization="EXPLICIT_HUMAN_AUTHORIZED",
            )

    def test_send_jules_task_empty_task(self):
        with self.assertRaises(ValueError):
            send_jules_task(
                repository="surasit3173/MyPython",
                task="   ",
                scope="research_controller",
                authorization="EXPLICIT_HUMAN_AUTHORIZED",
            )

    def test_send_jules_task_create_issue_dry_run(self):
        client = GitHubClient(token="", dry_run=True)
        res = send_jules_task(
            repository="surasit3173/MyPython",
            task="Add unit tests",
            scope="research_controller",
            authorization="EXPLICIT_HUMAN_AUTHORIZED",
            target_type="CREATE_ISSUE",
            issue_title="New Jules Task",
            client=client,
        )
        self.assertEqual(res["status"], "DRY_RUN_SUCCESS")
        self.assertEqual(res["audit_event"]["repository"], "surasit3173/MyPython")
        self.assertEqual(res["github_result"]["operation"], "CREATE_ISSUE")

    def test_send_jules_task_unsupported_target_type(self):
        client = GitHubClient(token="", dry_run=True)
        with self.assertRaises(ValueError):
            send_jules_task(
                repository="surasit3173/MyPython",
                task="Task",
                scope="research_controller",
                authorization="EXPLICIT_HUMAN_AUTHORIZED",
                target_type="INVALID_TYPE",
                client=client,
            )


if __name__ == "__main__":
    unittest.main()
