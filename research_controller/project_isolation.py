"""
Project Isolation Gate for Research Controller & GitHub/Jules Integration.

Enforces strict boundary checks and scope validation to ensure tasks
cannot read or write across unauthorized project boundaries.
"""

from pathlib import Path
import re

class ProjectIsolationError(ValueError):
    """Raised when a requested project scope violates isolation rules."""
    pass


# Default authorized project scopes.
# Adding or expanding project scopes must be explicitly authorized.
AUTHORIZED_PROJECT_SCOPES = {
    "research_controller",
    "CMIP6Lampang",
    "CMIP6Uttaradit",
    "CMIP6Uttaradit/paper3",
    "CMIP6Nan",
    "CMIP6PrachuapKhiriKhan",
    "CMIP6Phetchaburi",
    "Science Essence Journal",
}


def get_authorized_project_scopes() -> set[str]:
    """Return a copy of all registered project scopes."""
    return set(AUTHORIZED_PROJECT_SCOPES)


def is_path_traversal(scope: str) -> bool:
    """
    Check if scope contains path traversal sequences or absolute path roots.
    """
    if not scope or not scope.strip():
        return True

    s = scope.strip()

    # Reject absolute path indicators
    if s.startswith("/") or s.startswith("\\") or re.match(r"^[a-zA-Z]:", s):
        return True

    # Reject path traversal components
    parts = re.split(r"[/\\]", s)
    if ".." in parts or "." in parts:
        return True

    return False


def validate_project_scope(scope: str, allowed_scopes: set[str] | None = None) -> str:
    """
    Validate that project scope is authorized and free from path traversal.

    FAIL-CLOSED:
    - Rejects empty, whitespace, or non-string scope.
    - Rejects path traversal (`..`, absolute paths, drive letters).
    - Rejects scopes not present in allowed_scopes set.

    Returns normalized scope string if valid.
    """
    if not isinstance(scope, str) or not scope.strip():
        raise ProjectIsolationError("FAIL-CLOSED: Project scope must be a non-empty string.")

    norm_scope = scope.strip().replace("\\", "/")

    if is_path_traversal(norm_scope):
        raise ProjectIsolationError(f"FAIL-CLOSED: Path traversal or invalid path detected in scope '{scope}'.")

    valid_set = allowed_scopes if allowed_scopes is not None else AUTHORIZED_PROJECT_SCOPES

    if norm_scope not in valid_set:
        raise ProjectIsolationError(f"FAIL-CLOSED: Project scope '{norm_scope}' is not in authorized project scopes list.")

    return norm_scope


def is_valid_project_scope(scope: str, allowed_scopes: set[str] | None = None) -> bool:
    """
    Boolean check for valid project scope.
    """
    try:
        validate_project_scope(scope, allowed_scopes=allowed_scopes)
        return True
    except ProjectIsolationError:
        return False
