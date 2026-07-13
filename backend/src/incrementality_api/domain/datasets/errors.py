class DatasetDomainError(Exception):
    """Base exception for dataset-domain failures."""


class InvalidDatasetError(DatasetDomainError):
    """Raised when dataset metadata violates domain rules."""
