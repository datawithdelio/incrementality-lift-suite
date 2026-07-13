class AuthorizationApplicationError(Exception):
    """Base exception for authorization use cases."""


class WorkspaceAccessDeniedError(
    AuthorizationApplicationError,
):
    """Raised when workspace access cannot be granted."""
