class IncrementalityError(Exception):
    """Base exception for expected application errors."""


class InfrastructureUnavailableError(IncrementalityError):
    """Raised when a required infrastructure dependency is unavailable."""
