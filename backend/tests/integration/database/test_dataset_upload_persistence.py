from collections.abc import AsyncIterator
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from incrementality_api.application.datasets.errors import (
    DatasetUnavailableError,
)
from incrementality_api.application.datasets.ports import (
    DatasetObjectWriteResult,
)
from incrementality_api.application.datasets.upload_dataset import (
    UploadDataset,
    UploadDatasetCommand,
)
from incrementality_api.domain.datasets.status import (
    DatasetStatus,
)
from incrementality_api.domain.projects.status import (
    ProjectStatus,
)
from incrementality_api.infrastructure.database.models.datasets import (
    DatasetModel,
)
from incrementality_api.infrastructure.database.models.projects import (
    ProjectModel,
)
from incrementality_api.infrastructure.database.models.tenancy import (
    OrganizationModel,
    UserModel,
    WorkspaceModel,
)
from incrementality_api.infrastructure.database.unit_of_work.datasets import (
    SqlAlchemyDatasetUnitOfWork,
)

CONTENT = b"market,revenue\nnorth,250\n"
CONTENT_SIZE = len(CONTENT)
CONTENT_CHECKSUM = sha256(CONTENT).hexdigest()

CREATED_AT = datetime(
    2026,
    7,
    14,
    12,
    0,
    tzinfo=UTC,
)

UPLOADED_AT = datetime(
    2026,
    7,
    14,
    14,
    30,
    tzinfo=UTC,
)


async def content_chunks() -> AsyncIterator[bytes]:
    yield CONTENT[:7]
    yield CONTENT[7:17]
    yield CONTENT[17:]


class FixedClock:
    def now(self) -> datetime:
        return UPLOADED_AT


class MemoryObjectStorage:
    def __init__(self) -> None:
        self.write_count = 0
        self.deleted_keys: list[str] = []
        self.objects: dict[str, bytes] = {}

    async def write(
        self,
        *,
        storage_key: str,
        media_type: str,
        chunks: AsyncIterator[bytes],
    ) -> DatasetObjectWriteResult:
        del media_type

        self.write_count += 1

        content = bytearray()

        async for chunk in chunks:
            content.extend(chunk)

        stored_content = bytes(content)
        self.objects[storage_key] = stored_content

        return DatasetObjectWriteResult(
            byte_size=len(stored_content),
            checksum_sha256=sha256(stored_content).hexdigest(),
        )

    async def delete(
        self,
        *,
        storage_key: str,
    ) -> None:
        self.deleted_keys.append(storage_key)
        self.objects.pop(
            storage_key,
            None,
        )


async def seed_pending_dataset(
    session_factory: async_sessionmaker[AsyncSession],
) -> tuple[UUID, UUID, UUID, UUID, str]:
    organization_id = uuid4()
    workspace_id = uuid4()
    user_id = uuid4()
    project_id = uuid4()
    dataset_id = uuid4()

    storage_key = (
        f"workspaces/{workspace_id}/"
        f"projects/{project_id}/"
        f"datasets/{CONTENT_CHECKSUM}/"
        "campaign-results.csv"
    )

    async with (
        session_factory() as session,
        session.begin(),
    ):
        session.add_all(
            [
                OrganizationModel(
                    id=organization_id,
                    name="Upload Organization",
                    slug=f"upload-organization-{organization_id}",
                    created_at=CREATED_AT,
                    updated_at=CREATED_AT,
                ),
                UserModel(
                    id=user_id,
                    email=f"{user_id}@example.com",
                    display_name="Upload User",
                    created_at=CREATED_AT,
                    updated_at=CREATED_AT,
                ),
            ]
        )

        await session.flush()

        session.add(
            WorkspaceModel(
                id=workspace_id,
                organization_id=organization_id,
                name="Upload Workspace",
                slug=f"upload-workspace-{workspace_id}",
                created_at=CREATED_AT,
                updated_at=CREATED_AT,
            )
        )

        await session.flush()

        session.add(
            ProjectModel(
                id=project_id,
                workspace_id=workspace_id,
                created_by_user_id=user_id,
                name="Upload Project",
                slug=f"upload-project-{project_id}",
                description=None,
                status=ProjectStatus.ACTIVE.value,
                archived_at=None,
                created_at=CREATED_AT,
                updated_at=CREATED_AT,
            )
        )

        await session.flush()

        session.add(
            DatasetModel(
                id=dataset_id,
                workspace_id=workspace_id,
                project_id=project_id,
                created_by_user_id=user_id,
                source_filename="campaign-results.csv",
                storage_key=storage_key,
                media_type="text/csv",
                byte_size=CONTENT_SIZE,
                checksum_sha256=CONTENT_CHECKSUM,
                status=DatasetStatus.PENDING_UPLOAD.value,
                uploaded_at=None,
                validation_completed_at=None,
                row_count=None,
                column_count=None,
                failure_reason=None,
                created_at=CREATED_AT,
                updated_at=CREATED_AT,
            )
        )

    return (
        workspace_id,
        project_id,
        user_id,
        dataset_id,
        storage_key,
    )


@pytest.mark.asyncio
async def test_upload_use_case_persists_uploaded_status(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    (
        workspace_id,
        project_id,
        user_id,
        dataset_id,
        storage_key,
    ) = await seed_pending_dataset(
        tenancy_session_factory,
    )

    object_storage = MemoryObjectStorage()

    result = await UploadDataset(
        unit_of_work=SqlAlchemyDatasetUnitOfWork(
            session_factory=tenancy_session_factory,
        ),
        object_storage=object_storage,
        clock=FixedClock(),
    ).execute(
        UploadDatasetCommand(
            workspace_id=workspace_id,
            project_id=project_id,
            dataset_id=dataset_id,
            chunks=content_chunks(),
        )
    )

    assert result.status is DatasetStatus.UPLOADED
    assert result.uploaded_at == UPLOADED_AT
    assert result.created_by_user_id == user_id

    assert object_storage.objects == {
        storage_key: CONTENT,
    }
    assert object_storage.deleted_keys == []

    async with tenancy_session_factory() as session:
        persisted = await session.scalar(
            select(DatasetModel).where(
                DatasetModel.id == dataset_id,
            )
        )

    assert persisted is not None
    assert persisted.status == DatasetStatus.UPLOADED.value
    assert persisted.uploaded_at == UPLOADED_AT

    assert persisted.workspace_id == workspace_id
    assert persisted.project_id == project_id
    assert persisted.created_by_user_id == user_id
    assert persisted.storage_key == storage_key
    assert persisted.byte_size == CONTENT_SIZE
    assert persisted.checksum_sha256 == CONTENT_CHECKSUM
    assert persisted.source_filename == ("campaign-results.csv")


@pytest.mark.asyncio
async def test_cross_scope_upload_does_not_write_or_update(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    (
        workspace_id,
        project_id,
        _,
        dataset_id,
        storage_key,
    ) = await seed_pending_dataset(
        tenancy_session_factory,
    )

    object_storage = MemoryObjectStorage()

    with pytest.raises(
        DatasetUnavailableError,
        match="Dataset is unavailable",
    ):
        await UploadDataset(
            unit_of_work=SqlAlchemyDatasetUnitOfWork(
                session_factory=tenancy_session_factory,
            ),
            object_storage=object_storage,
            clock=FixedClock(),
        ).execute(
            UploadDatasetCommand(
                workspace_id=uuid4(),
                project_id=project_id,
                dataset_id=dataset_id,
                chunks=content_chunks(),
            )
        )

    assert object_storage.write_count == 0
    assert object_storage.objects == {}
    assert object_storage.deleted_keys == []

    async with tenancy_session_factory() as session:
        persisted = await session.scalar(
            select(DatasetModel).where(
                DatasetModel.id == dataset_id,
            )
        )

    assert persisted is not None
    assert persisted.workspace_id == workspace_id
    assert persisted.storage_key == storage_key
    assert persisted.status == (DatasetStatus.PENDING_UPLOAD.value)
    assert persisted.uploaded_at is None
