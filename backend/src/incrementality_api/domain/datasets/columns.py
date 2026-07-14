import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum

_MAX_COLUMN_NAME_LENGTH = 255


class DatasetColumnType(StrEnum):
    """Primitive type inferred from observed CSV values."""

    BOOLEAN = "boolean"
    INTEGER = "integer"
    FLOAT = "float"
    DATE = "date"
    DATETIME = "datetime"
    STRING = "string"


@dataclass(frozen=True, slots=True)
class DatasetColumnProfile:
    """Discovered structural metadata for one dataset column."""

    ordinal_position: int
    source_name: str
    normalized_name: str
    inferred_type: DatasetColumnType
    nullable: bool
    missing_count: int

    def __post_init__(self) -> None:
        if self.ordinal_position <= 0:
            raise ValueError("Column ordinal position must be positive.")

        if not self.source_name.strip():
            raise ValueError("Column source name must not be blank.")

        if len(self.source_name) > _MAX_COLUMN_NAME_LENGTH:
            raise ValueError("Column source name must not exceed 255 characters.")

        if not self.normalized_name.strip():
            raise ValueError("Normalized column name must not be blank.")

        if len(self.normalized_name) > _MAX_COLUMN_NAME_LENGTH:
            raise ValueError("Normalized column name must not exceed 255 characters.")

        if self.missing_count < 0:
            raise ValueError("Column missing count must be nonnegative.")

        if self.nullable != (self.missing_count > 0):
            raise ValueError("Column nullable status must match its observed missing count.")


def normalize_dataset_column_names(
    source_names: tuple[str, ...],
) -> tuple[str, ...]:
    """Produce stable, unique names suitable for product logic."""

    normalized_names: list[str] = []
    used_names: set[str] = set()

    for ordinal_position, source_name in enumerate(
        source_names,
        start=1,
    ):
        normalized = unicodedata.normalize(
            "NFKC",
            source_name,
        )
        normalized = normalized.strip().casefold()
        normalized = re.sub(
            r"[^\w]+",
            "_",
            normalized,
        ).strip("_")

        if not normalized:
            normalized = f"column_{ordinal_position}"

        normalized = normalized[:_MAX_COLUMN_NAME_LENGTH].rstrip("_")

        if not normalized:
            normalized = f"column_{ordinal_position}"

        candidate = normalized
        suffix_number = 2

        while candidate in used_names:
            suffix = f"_{suffix_number}"
            available_length = _MAX_COLUMN_NAME_LENGTH - len(suffix)

            candidate = normalized[:available_length].rstrip("_") + suffix

            suffix_number += 1

        used_names.add(candidate)
        normalized_names.append(candidate)

    return tuple(normalized_names)
