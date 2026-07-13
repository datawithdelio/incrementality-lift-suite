class AuthenticationDomainError(Exception):
    """Base exception for authentication-domain errors."""


class InvalidCredentialError(AuthenticationDomainError):
    """Raised when password-credential information is invalid."""


class InvalidSessionError(AuthenticationDomainError):
    """Raised when authentication-session information is invalid."""
