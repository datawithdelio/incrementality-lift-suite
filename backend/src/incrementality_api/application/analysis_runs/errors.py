class AnalysisRunApplicationError(Exception):
    """Base exception for analysis-run application failures."""


class AnalysisRunDatasetUnavailableError(
    AnalysisRunApplicationError,
):
    """Raised when the dataset is outside the requested scope."""


class AnalysisRunDatasetNotReadyError(
    AnalysisRunApplicationError,
):
    """Raised when analysis is requested before validation completes."""


class AnalysisRunSemanticMappingUnavailableError(
    AnalysisRunApplicationError,
):
    """Raised when the requested semantic-mapping snapshot is unavailable."""


class AnalysisRunUnavailableError(
    AnalysisRunApplicationError,
):
    """Raised when an analysis run is outside the requested scope."""


class AnalysisRunPersistenceConflictError(
    AnalysisRunApplicationError,
):
    """Raised when persisted analysis-run metadata conflicts."""
