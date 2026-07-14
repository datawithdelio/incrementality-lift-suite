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
async def test_discovers_column_profiles_and_primitive_types() -> None:
    content = (
        b"Market Name,treated,orders,revenue,"
        b"event_date,observed_at,notes\n"
        b"north,true,10,250.5,2026-07-01,"
        b"2026-07-01T12:30:00,launch\n"
        b"south,false,,175,2026-07-02,"
        b"2026-07-02T08:00:00,\n"
    )

    result = await CsvDatasetContentValidator().validate(
        chunks=content_chunks(
            content,
            chunk_size=4,
        ),
    )

    assert [column.ordinal_position for column in result.columns] == [1, 2, 3, 4, 5, 6, 7]

    assert [column.source_name for column in result.columns] == [
        "Market Name",
        "treated",
        "orders",
        "revenue",
        "event_date",
        "observed_at",
        "notes",
    ]

    assert [column.normalized_name for column in result.columns] == [
        "market_name",
        "treated",
        "orders",
        "revenue",
        "event_date",
        "observed_at",
        "notes",
    ]

    assert [column.inferred_type.value for column in result.columns] == [
        "string",
        "boolean",
        "integer",
        "float",
        "date",
        "datetime",
        "string",
    ]

    assert [column.missing_count for column in result.columns] == [0, 0, 1, 0, 0, 0, 1]

    assert [column.nullable for column in result.columns] == [
        False,
        False,
        True,
        False,
        False,
        False,
        True,
    ]


@pytest.mark.asyncio
async def test_generates_unique_normalized_column_names() -> None:
    content = ("Ad Spend,ad-spend,🔥\n10,20,value\n").encode()

    result = await CsvDatasetContentValidator().validate(
        chunks=content_chunks(content),
    )

    assert [column.normalized_name for column in result.columns] == [
        "ad_spend",
        "ad_spend_2",
        "column_3",
    ]


@pytest.mark.asyncio
async def test_header_only_columns_default_to_string() -> None:
    result = await CsvDatasetContentValidator().validate(
        chunks=content_chunks(
            b"market,revenue\n",
        ),
    )

    assert [column.inferred_type.value for column in result.columns] == [
        "string",
        "string",
    ]

    assert [column.nullable for column in result.columns] == [
        False,
        False,
    ]


@pytest.mark.asyncio
async def test_rejects_column_name_longer_than_255_characters() -> None:
    content = (("x" * 256) + ",revenue\n" + "north,250\n").encode()

    with pytest.raises(
        DatasetContentValidationError,
        match="must not exceed 255 characters",
    ):
        await CsvDatasetContentValidator().validate(
            chunks=content_chunks(content),
        )


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
