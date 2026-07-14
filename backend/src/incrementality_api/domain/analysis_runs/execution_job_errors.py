class AnalysisExecutionJobDomainError(Exception):
    """Base exception for analysis execution job failures."""


class InvalidAnalysisExecutionJobError(
    AnalysisExecutionJobDomainError,
):
    """Raised when analysis execution job metadata is invalid."""


class InvalidAnalysisExecutionJobTransitionError(
    AnalysisExecutionJobDomainError,
):
    """Raised when an analysis execution job transition is invalid."""
