import asyncio
import csv
from collections.abc import AsyncIterator
from io import TextIOWrapper
from tempfile import SpooledTemporaryFile
from typing import BinaryIO, cast

from incrementality_api.application.datasets.errors import (
    DatasetContentValidationError,
)
from incrementality_api.application.datasets.ports import (
    DatasetValidationResult,
)


class CsvDatasetContentValidator:
    """Validate UTF-8 CSV content using bounded temporary storage."""

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

            normalized_columns = [column.strip() for column in header]

            if any(not column for column in normalized_columns):
                raise DatasetContentValidationError("CSV column names must not be blank.")

            casefolded_columns = [column.casefold() for column in normalized_columns]

            if len(set(casefolded_columns)) != len(casefolded_columns):
                raise DatasetContentValidationError("CSV column names must be unique.")

            column_count = len(header)
            row_count = 0

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

                row_count += 1

            return DatasetValidationResult(
                row_count=row_count,
                column_count=column_count,
            )
        except UnicodeDecodeError as error:
            raise DatasetContentValidationError("CSV must be UTF-8 encoded.") from error
        except csv.Error as error:
            raise DatasetContentValidationError("CSV content is malformed.") from error
        finally:
            # Keep ownership of the binary spool with the outer
            # context manager rather than closing it here.
            text_stream.detach()
