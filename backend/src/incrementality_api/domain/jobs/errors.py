class JobDomainError(Exception):
    """Base exception for durable-job domain failures."""


class InvalidJobError(JobDomainError):
    """Raised when durable-job metadata is invalid."""


class InvalidJobTransitionError(JobDomainError):
    """Raised when a durable-job transition is invalid."""
