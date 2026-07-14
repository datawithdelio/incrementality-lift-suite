class DatasetApplicationError(Exception):
    """Base exception for dataset application failures."""


class DatasetTooLargeError(DatasetApplicationError):
    """Raised when dataset size exceeds the configured limit."""


class DatasetProjectUnavailableError(DatasetApplicationError):
    """Raised when the requested project cannot accept datasets."""


class DatasetPersistenceConflictError(
    DatasetApplicationError,
):
    """Raised when dataset metadata conflicts in persistence."""


class DatasetUnavailableError(DatasetApplicationError):
    """Raised when a scoped dataset cannot be found."""


class DatasetUploadVerificationError(
    DatasetApplicationError,
):
    """Raised when uploaded bytes do not match registered metadata."""


class DatasetContentValidationError(
    DatasetApplicationError,
):
    """Raised when uploaded dataset content is structurally invalid."""
