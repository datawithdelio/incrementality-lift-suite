from uuid import UUID

from incrementality_api.infrastructure.storage.dataset_keys import (
    DatasetObjectKeyBuilder,
)

WORKSPACE_ID = UUID("11111111-1111-1111-1111-111111111111")
PROJECT_ID = UUID("22222222-2222-2222-2222-222222222222")
CHECKSUM = "a" * 64


def test_builds_deterministic_project_scoped_key() -> None:
    builder = DatasetObjectKeyBuilder()

    key = builder.build(
        workspace_id=WORKSPACE_ID,
        project_id=PROJECT_ID,
        source_filename="campaign-results.csv",
        checksum_sha256=CHECKSUM,
    )

    assert key == (
        f"workspaces/{WORKSPACE_ID}/projects/{PROJECT_ID}/datasets/{CHECKSUM}/campaign-results.csv"
    )


def test_key_changes_with_project_scope() -> None:
    builder = DatasetObjectKeyBuilder()

    first_key = builder.build(
        workspace_id=WORKSPACE_ID,
        project_id=PROJECT_ID,
        source_filename="campaign-results.csv",
        checksum_sha256=CHECKSUM,
    )

    second_key = builder.build(
        workspace_id=WORKSPACE_ID,
        project_id=UUID("33333333-3333-3333-3333-333333333333"),
        source_filename="campaign-results.csv",
        checksum_sha256=CHECKSUM,
    )

    assert first_key != second_key
