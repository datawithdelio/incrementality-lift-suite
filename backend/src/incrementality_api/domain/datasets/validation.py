import re

from incrementality_api.domain.datasets.errors import (
    InvalidDatasetError,
)

_SUPPORTED_MEDIA_TYPES = frozenset(
    {
        "text/csv",
        "application/vnd.apache.parquet",
    }
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def normalize_dataset_filename(
    value: str,
) -> str:
    normalized = value.strip()

    if not normalized:
        raise InvalidDatasetError("Dataset filename must not be blank.")

    if len(normalized) > 255:
        raise InvalidDatasetError("Dataset filename must not exceed 255 characters.")

    if normalized in {".", ".."} or "/" in normalized or "\\" in normalized or "\x00" in normalized:
        raise InvalidDatasetError("Dataset filename must be a safe base filename.")

    return normalized


def normalize_dataset_storage_key(
    value: str,
) -> str:
    normalized = value.strip()

    if not normalized:
        raise InvalidDatasetError("Dataset storage key must not be blank.")

    if len(normalized) > 1024:
        raise InvalidDatasetError("Dataset storage key must not exceed 1024 characters.")

    if normalized.startswith("/") or "\\" in normalized or "\x00" in normalized:
        raise InvalidDatasetError("Dataset storage key is unsafe.")

    segments = normalized.split("/")

    if any(segment in {"", ".", ".."} for segment in segments):
        raise InvalidDatasetError("Dataset storage key is unsafe.")

    return normalized


def normalize_dataset_media_type(
    value: str,
) -> str:
    normalized = value.strip().lower()

    if normalized not in _SUPPORTED_MEDIA_TYPES:
        raise InvalidDatasetError("Dataset media type is not supported.")

    return normalized


def validate_dataset_byte_size(
    value: int,
) -> int:
    if isinstance(value, bool) or value <= 0:
        raise InvalidDatasetError("Dataset byte size must be positive.")

    return value


def normalize_dataset_checksum(
    value: str,
) -> str:
    normalized = value.strip().lower()

    if _SHA256_PATTERN.fullmatch(normalized) is None:
        raise InvalidDatasetError("Dataset checksum must be a valid SHA-256 digest.")

    return normalized
