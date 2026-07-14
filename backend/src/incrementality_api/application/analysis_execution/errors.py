class AnalysisExecutionApplicationError(Exception):
    """Base exception for analysis execution services."""


class AnalysisExecutionRunUnavailableError(
    AnalysisExecutionApplicationError,
):
    """Raised when a claimed execution job has no matching run."""


class AnalysisExecutionJobUnavailableError(
    AnalysisExecutionApplicationError,
):
    """Raised when an execution job cannot be loaded for settlement."""


class AnalysisResultPersistenceConflictError(AnalysisExecutionApplicationError):
    """Raised when a canonical result already exists or violates persistence."""
