from collections.abc import AsyncIterator

import pytest

from incrementality_api.application.datasets.errors import (
    DatasetContentValidationError,
)
from incrementality_api.infrastructure.validation.csv_datasets import (
    CsvDatasetContentValidator,
)


async def content_chunks(
    content: bytes,
    *,
    chunk_size: int = 5,
) -> AsyncIterator[bytes]:
    for offset in range(
        0,
        len(content),
        chunk_size,
    ):
        yield content[offset : offset + chunk_size]


@pytest.mark.asyncio
async def test_returns_csv_row_and_column_counts() -> None:
    content = b"market,revenue,campaign\nnorth,250,brand\nsouth,175,conversion\n"

    result = await CsvDatasetContentValidator().validate(
        chunks=content_chunks(content),
    )

    assert result.row_count == 2
    assert result.column_count == 3


@pytest.mark.asyncio
async def test_parses_quoted_newlines_across_chunks() -> None:
    content = b'market,notes\nnorth,"first line\nsecond line"\nsouth,"single line"\n'

    result = await CsvDatasetContentValidator().validate(
        chunks=content_chunks(
            content,
            chunk_size=3,
        ),
    )

    assert result.row_count == 2
    assert result.column_count == 2


@pytest.mark.asyncio
async def test_allows_header_only_csv() -> None:
    content = b"market,revenue\n"

    result = await CsvDatasetContentValidator().validate(
        chunks=content_chunks(content),
    )

    assert result.row_count == 0
    assert result.column_count == 2


@pytest.mark.asyncio
async def test_rejects_empty_csv() -> None:
    with pytest.raises(
        DatasetContentValidationError,
        match="CSV must contain a header row",
    ):
        await CsvDatasetContentValidator().validate(
            chunks=content_chunks(b""),
        )


@pytest.mark.asyncio
async def test_rejects_blank_column_name() -> None:
    content = b"market, ,revenue\nnorth,brand,250\n"

    with pytest.raises(
        DatasetContentValidationError,
        match="CSV column names must not be blank",
    ):
        await CsvDatasetContentValidator().validate(
            chunks=content_chunks(content),
        )


@pytest.mark.asyncio
async def test_rejects_duplicate_column_names_case_insensitively() -> None:
    content = b"market,Market,revenue\nnorth,south,250\n"

    with pytest.raises(
        DatasetContentValidationError,
        match="CSV column names must be unique",
    ):
        await CsvDatasetContentValidator().validate(
            chunks=content_chunks(content),
        )


@pytest.mark.asyncio
async def test_rejects_inconsistent_row_width() -> None:
    content = b"market,revenue,campaign\nnorth,250\n"

    with pytest.raises(
        DatasetContentValidationError,
        match=("CSV row 2 has 2 columns; expected 3"),
    ):
        await CsvDatasetContentValidator().validate(
            chunks=content_chunks(content),
        )


@pytest.mark.asyncio
async def test_rejects_malformed_csv() -> None:
    content = b'market,revenue\nnorth,"unterminated value\n'

    with pytest.raises(
        DatasetContentValidationError,
        match="CSV content is malformed",
    ):
        await CsvDatasetContentValidator().validate(
            chunks=content_chunks(content),
        )


@pytest.mark.asyncio
async def test_rejects_non_utf8_csv() -> None:
    content = b"market,revenue\nnorth,\xff\xfe\n"

    with pytest.raises(
        DatasetContentValidationError,
        match="CSV must be UTF-8 encoded",
    ):
        await CsvDatasetContentValidator().validate(
            chunks=content_chunks(content),
        )
