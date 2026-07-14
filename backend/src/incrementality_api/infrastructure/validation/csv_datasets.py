import asyncio
import csv
import math
from collections.abc import AsyncIterator
from datetime import date, datetime
from io import TextIOWrapper
from tempfile import SpooledTemporaryFile
from typing import BinaryIO, cast

from incrementality_api.application.datasets.errors import (
    DatasetContentValidationError,
)
from incrementality_api.application.datasets.ports import (
    DatasetValidationResult,
)
from incrementality_api.domain.datasets.columns import (
    DatasetColumnProfile,
    DatasetColumnType,
    normalize_dataset_column_names,
)

_MAX_COLUMN_NAME_LENGTH = 255


class CsvDatasetContentValidator:
    """Validate and profile UTF-8 CSV content."""

    def __init__(
        self,
        *,
        spool_max_memory_bytes: int = 8 * 1024 * 1024,
    ) -> None:
        if spool_max_memory_bytes <= 0:
            raise ValueError("CSV spool memory limit must be positive.")

        self._spool_max_memory_bytes = spool_max_memory_bytes

    async def validate(
        self,
        *,
        chunks: AsyncIterator[bytes],
    ) -> DatasetValidationResult:
        with SpooledTemporaryFile(
            max_size=self._spool_max_memory_bytes,
            mode="w+b",
        ) as body:
            async for chunk in chunks:
                if not chunk:
                    continue

                body.write(chunk)

            body.seek(0)

            return await asyncio.to_thread(
                self._validate_spooled_csv,
                cast(BinaryIO, body),
            )

    @staticmethod
    def _validate_spooled_csv(
        body: BinaryIO,
    ) -> DatasetValidationResult:
        text_stream = TextIOWrapper(
            body,
            encoding="utf-8",
            errors="strict",
            newline="",
        )

        try:
            reader = csv.reader(
                text_stream,
                strict=True,
            )

            try:
                header = next(reader)
            except StopIteration as error:
                raise DatasetContentValidationError("CSV must contain a header row.") from error

            if not header:
                raise DatasetContentValidationError("CSV must contain a header row.")

            source_names = tuple(column.strip() for column in header)

            if any(not column for column in source_names):
                raise DatasetContentValidationError("CSV column names must not be blank.")

            if any(len(column) > _MAX_COLUMN_NAME_LENGTH for column in source_names):
                raise DatasetContentValidationError(
                    "CSV column names must not exceed 255 characters."
                )

            casefolded_names = tuple(column.casefold() for column in source_names)

            if len(set(casefolded_names)) != len(casefolded_names):
                raise DatasetContentValidationError("CSV column names must be unique.")

            normalized_names = normalize_dataset_column_names(
                source_names,
            )

            column_count = len(source_names)
            row_count = 0

            inferred_types: list[DatasetColumnType | None] = [None for _ in range(column_count)]

            missing_counts = [0 for _ in range(column_count)]

            for row_number, row in enumerate(
                reader,
                start=2,
            ):
                actual_column_count = len(row)

                if actual_column_count != column_count:
                    raise DatasetContentValidationError(
                        f"CSV row {row_number} has "
                        f"{actual_column_count} columns; "
                        f"expected {column_count}."
                    )

                for index, raw_value in enumerate(row):
                    value = raw_value.strip()

                    if not value:
                        missing_counts[index] += 1
                        continue

                    inferred_types[index] = _merge_column_types(
                        inferred_types[index],
                        _infer_scalar_type(value),
                    )

                row_count += 1

            columns = tuple(
                DatasetColumnProfile(
                    ordinal_position=ordinal_position,
                    source_name=source_name,
                    normalized_name=normalized_name,
                    inferred_type=(inferred_type or DatasetColumnType.STRING),
                    nullable=(missing_count > 0),
                    missing_count=missing_count,
                )
                for (
                    ordinal_position,
                    source_name,
                    normalized_name,
                    inferred_type,
                    missing_count,
                ) in zip(
                    range(
                        1,
                        column_count + 1,
                    ),
                    source_names,
                    normalized_names,
                    inferred_types,
                    missing_counts,
                    strict=True,
                )
            )

            return DatasetValidationResult(
                row_count=row_count,
                column_count=column_count,
                columns=columns,
            )
        except UnicodeDecodeError as error:
            raise DatasetContentValidationError("CSV must be UTF-8 encoded.") from error
        except csv.Error as error:
            raise DatasetContentValidationError("CSV content is malformed.") from error
        finally:
            # The outer spool context owns the binary file.
            text_stream.detach()


def _infer_scalar_type(
    value: str,
) -> DatasetColumnType:
    normalized = value.casefold()

    if normalized in {
        "true",
        "false",
    }:
        return DatasetColumnType.BOOLEAN

    try:
        int(value)
    except ValueError:
        pass
    else:
        return DatasetColumnType.INTEGER

    try:
        numeric_value = float(value)
    except ValueError:
        pass
    else:
        if math.isfinite(numeric_value):
            return DatasetColumnType.FLOAT

    if "t" in normalized or " " in value:
        try:
            datetime.fromisoformat(value)
        except ValueError:
            pass
        else:
            return DatasetColumnType.DATETIME

    try:
        date.fromisoformat(value)
    except ValueError:
        return DatasetColumnType.STRING

    return DatasetColumnType.DATE


def _merge_column_types(
    current: DatasetColumnType | None,
    observed: DatasetColumnType,
) -> DatasetColumnType:
    if current is None or current is observed:
        return observed

    observed_types = {
        current,
        observed,
    }

    if observed_types <= {
        DatasetColumnType.INTEGER,
        DatasetColumnType.FLOAT,
    }:
        return DatasetColumnType.FLOAT

    if observed_types <= {
        DatasetColumnType.DATE,
        DatasetColumnType.DATETIME,
    }:
        return DatasetColumnType.DATETIME

    return DatasetColumnType.STRING
