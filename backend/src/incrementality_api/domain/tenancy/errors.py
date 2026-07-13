class TenancyDomainError(Exception):
    """Base exception for tenancy-domain errors."""


class InvalidOrganizationError(TenancyDomainError):
    """Raised when organization information is invalid."""


class InvalidWorkspaceError(TenancyDomainError):
    """Raised when workspace information is invalid."""


class InvalidUserError(TenancyDomainError):
    """Raised when user information is invalid."""


class InvalidMembershipError(TenancyDomainError):
    """Raised when workspace membership information is invalid."""
