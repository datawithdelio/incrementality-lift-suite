class AnalysisRunDomainError(Exception):
    """Base exception for causal-analysis run failures."""


class InvalidAnalysisRunError(AnalysisRunDomainError):
    """Raised when analysis-run metadata is invalid."""


class InvalidAnalysisRunTransitionError(
    AnalysisRunDomainError,
):
    """Raised when an analysis-run transition is invalid."""
