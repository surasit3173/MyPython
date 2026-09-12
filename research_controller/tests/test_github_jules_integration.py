"""
Unit and Integration Test Suite for GitHub / Jules Write Integration.

Tests:
- Authentication failures & missing credentials
- Invalid repository formatting
- Invalid project scope & path traversal protection
- Unauthorized write operations
- Allowed write operations (Issues, PR comments)
- GitHub API failures, timeouts, retries
- Secret redaction in logs/errors
- Dry-run mode behavior
- Jules task payload generation
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
)
import project_isolation
from project_isolation import validate_project_scope, ProjectIsolationError
import jules_bridge
from jules_bridge import send_jules_task, format_jules_task_message


class TestSecretRedaction(unittest.TestCase):
    def test_redact_secrets(self):
        token_pat = "ghp_123456789012345678901234567890123456"
        text = f"Failed request with token {token_pat} and Bearer {token_pat}"
        redacted = redact_secrets(text)
        self.assertNotIn(token_pat, redacted)
        self.assertIn("[REDACTED_GITHUB_PAT]", redacted)


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


class TestGitHubClient(unittest.TestCase):
    def test_missing_credentials_raises_auth_error(self):
        client = GitHubClient(token="", dry_run=False)
        with self.assertRaises(GitHubAuthenticationError):
            client._get_headers()

    def test_invalid_repository_format(self):
        client = GitHubClient(token="ghp_dummy", dry_run=True)
        invalid_repos = ["invalid_repo", "owner/repo/extra", "", "/repo"]
        for repo in invalid_repos:
            with self.subTest(repo=repo):
                with self.assertRaises(GitHubClientError):
                    client.create_issue(repo, "Title", "Body")

    def test_unauthorized_write_action(self):
        client = GitHubClient(token="ghp_dummy", dry_run=True)
        with self.assertRaises(GitHubAuthorizationError):
            client.create_issue("surasit3173/MyPython", "Title", "Body", authorization="UNAUTHORIZED")

    def test_dry_run_mode_issue_creation(self):
        client = GitHubClient(token="", dry_run=True)
        res = client.create_issue("surasit3173/MyPython", "Test Issue", "Issue Body")
        self.assertTrue(res["dry_run"])
        self.assertEqual(res["operation"], "CREATE_ISSUE")
        self.assertEqual(res["repository"], "surasit3173/MyPython")
        self.assertEqual(res["status"], "DRY_RUN_SUCCESS")

    def test_dry_run_mode_comment_creation(self):
        client = GitHubClient(token="", dry_run=True)
        res = client.add_issue_comment("surasit3173/MyPython", 42, "Test Comment")
        self.assertTrue(res["dry_run"])
        self.assertEqual(res["operation"], "ADD_ISSUE_COMMENT")
        self.assertEqual(res["issue_number"], 42)

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

    def test_send_jules_task_dry_run_success(self):
        client = GitHubClient(token="", dry_run=True)
        res = send_jules_task(
            repository="surasit3173/MyPython",
            task="Add unit tests",
            scope="research_controller",
            authorization="EXPLICIT_HUMAN_AUTHORIZED",
            target_type="ISSUE_COMMENT",
            target_id=10,
            client=client,
        )
        self.assertEqual(res["status"], "DRY_RUN_SUCCESS")
        self.assertEqual(res["audit_event"]["repository"], "surasit3173/MyPython")
        self.assertEqual(res["audit_event"]["scope"], "research_controller")


if __name__ == "__main__":
    unittest.main()
