class DatasetApplicationError(Exception):
    """Base exception for dataset application failures."""


class DatasetTooLargeError(DatasetApplicationError):
    """Raised when dataset size exceeds the configured limit."""


class DatasetProjectUnavailableError(DatasetApplicationError):
    """Raised when the requested project cannot accept datasets."""
