class TenancyApplicationError(Exception):
    """Base exception for tenancy application errors."""


class TenancyConflictError(TenancyApplicationError):
    """Raised when tenant data violates a uniqueness rule."""
