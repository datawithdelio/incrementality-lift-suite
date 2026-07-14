from datetime import timedelta
from uuid import UUID, uuid4

import pytest

from incrementality_api.domain.datasets.entities import Dataset
from incrementality_api.domain.datasets.errors import (
    InvalidDatasetError,
)
from incrementality_api.domain.datasets.status import (
    DatasetStatus,
)

VALID_CHECKSUM = "a" * 64


def register_dataset(
    *,
    source_filename: str = "campaign-results.csv",
    storage_key: str = "workspaces/ws/projects/prj/datasets/data.csv",
    media_type: str = "text/csv",
    byte_size: int = 1024,
    checksum_sha256: str = VALID_CHECKSUM,
) -> Dataset:
    return Dataset.register(
        workspace_id=uuid4(),
        project_id=uuid4(),
        created_by_user_id=uuid4(),
        source_filename=source_filename,
        storage_key=storage_key,
        media_type=media_type,
        byte_size=byte_size,
        checksum_sha256=checksum_sha256,
    )


def test_registers_dataset_pending_upload() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()

    dataset = Dataset.register(
        workspace_id=workspace_id,
        project_id=project_id,
        created_by_user_id=user_id,
        source_filename="campaign-results.csv",
        storage_key=(
            f"workspaces/{workspace_id}/projects/{project_id}/datasets/campaign-results.csv"
        ),
        media_type="text/csv",
        byte_size=2048,
        checksum_sha256=VALID_CHECKSUM,
    )

    assert isinstance(dataset.id, UUID)
    assert dataset.workspace_id == workspace_id
    assert dataset.project_id == project_id
    assert dataset.created_by_user_id == user_id
    assert dataset.source_filename == "campaign-results.csv"
    assert dataset.media_type == "text/csv"
    assert dataset.byte_size == 2048
    assert dataset.checksum_sha256 == VALID_CHECKSUM
    assert dataset.status is DatasetStatus.PENDING_UPLOAD
    assert dataset.created_at.utcoffset() == timedelta(0)

    assert dataset.uploaded_at is None
    assert dataset.validation_completed_at is None
    assert dataset.row_count is None
    assert dataset.column_count is None
    assert dataset.failure_reason is None


def test_source_filename_is_trimmed() -> None:
    dataset = register_dataset(
        source_filename="  campaign-results.csv  ",
    )

    assert dataset.source_filename == "campaign-results.csv"


@pytest.mark.parametrize(
    "source_filename",
    [
        "",
        "   ",
        "../campaign-results.csv",
        r"folder\campaign-results.csv",
    ],
)
def test_rejects_unsafe_source_filename(
    source_filename: str,
) -> None:
    with pytest.raises(
        InvalidDatasetError,
        match="Dataset filename",
    ):
        register_dataset(
            source_filename=source_filename,
        )


def test_rejects_source_filename_longer_than_255_characters() -> None:
    with pytest.raises(
        InvalidDatasetError,
        match="Dataset filename",
    ):
        register_dataset(
            source_filename=("x" * 252) + ".csv",
        )


@pytest.mark.parametrize(
    ("media_type", "expected"),
    [
        ("  TEXT/CSV  ", "text/csv"),
    ],
)
def test_normalizes_supported_media_type(
    media_type: str,
    expected: str,
) -> None:
    dataset = register_dataset(
        media_type=media_type,
    )

    assert dataset.media_type == expected


@pytest.mark.parametrize(
    "media_type",
    [
        "application/json",
        "application/zip",
        "application/vnd.apache.parquet",
    ],
)
def test_rejects_unsupported_media_type(
    media_type: str,
) -> None:
    with pytest.raises(
        InvalidDatasetError,
        match="Dataset media type",
    ):
        register_dataset(
            media_type=media_type,
        )


@pytest.mark.parametrize(
    "byte_size",
    [
        0,
        -1,
    ],
)
def test_rejects_non_positive_byte_size(
    byte_size: int,
) -> None:
    with pytest.raises(
        InvalidDatasetError,
        match="Dataset byte size",
    ):
        register_dataset(
            byte_size=byte_size,
        )


def test_checksum_is_trimmed_and_lowercased() -> None:
    dataset = register_dataset(
        checksum_sha256=("  " + ("A" * 64) + "  "),
    )

    assert dataset.checksum_sha256 == ("a" * 64)


@pytest.mark.parametrize(
    "checksum",
    [
        "",
        "abc123",
        "g" * 64,
    ],
)
def test_rejects_invalid_sha256_checksum(
    checksum: str,
) -> None:
    with pytest.raises(
        InvalidDatasetError,
        match="Dataset checksum",
    ):
        register_dataset(
            checksum_sha256=checksum,
        )


@pytest.mark.parametrize(
    "storage_key",
    [
        "",
        "../datasets/campaign-results.csv",
        "/datasets/campaign-results.csv",
    ],
)
def test_rejects_unsafe_storage_key(
    storage_key: str,
) -> None:
    with pytest.raises(
        InvalidDatasetError,
        match="Dataset storage key",
    ):
        register_dataset(
            storage_key=storage_key,
        )
