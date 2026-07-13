from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from incrementality_api.application.datasets.errors import (
    DatasetPersistenceConflictError,
    DatasetProjectUnavailableError,
)
from incrementality_api.application.datasets.register_dataset import (
    RegisterDataset,
    RegisterDatasetCommand,
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
from incrementality_api.infrastructure.storage.dataset_keys import (
    DatasetObjectKeyBuilder,
)

FIXED_NOW = datetime(
    2026,
    7,
    14,
    3,
    0,
    tzinfo=UTC,
)

CHECKSUM = "b" * 64


async def seed_active_project(
    session_factory: async_sessionmaker[AsyncSession],
) -> tuple[UUID, UUID, UUID]:
    organization_id = uuid4()
    workspace_id = uuid4()
    user_id = uuid4()
    project_id = uuid4()

    async with (
        session_factory() as session,
        session.begin(),
    ):
        session.add_all(
            [
                OrganizationModel(
                    id=organization_id,
                    name="Dataset Organization",
                    slug=f"organization-{organization_id}",
                    created_at=FIXED_NOW,
                    updated_at=FIXED_NOW,
                ),
                UserModel(
                    id=user_id,
                    email=f"{user_id}@example.com",
                    display_name="Dataset Creator",
                    created_at=FIXED_NOW,
                    updated_at=FIXED_NOW,
                ),
            ]
        )

        await session.flush()

        session.add(
            WorkspaceModel(
                id=workspace_id,
                organization_id=organization_id,
                name="Dataset Workspace",
                slug=f"workspace-{workspace_id}",
                created_at=FIXED_NOW,
                updated_at=FIXED_NOW,
            )
        )

        await session.flush()

        session.add(
            ProjectModel(
                id=project_id,
                workspace_id=workspace_id,
                created_by_user_id=user_id,
                name="Dataset Project",
                slug=f"project-{project_id}",
                description=None,
                status=ProjectStatus.ACTIVE.value,
                archived_at=None,
                created_at=FIXED_NOW,
                updated_at=FIXED_NOW,
            )
        )

    return workspace_id, project_id, user_id


def build_service(
    session_factory: async_sessionmaker[AsyncSession],
) -> RegisterDataset:
    return RegisterDataset(
        unit_of_work=SqlAlchemyDatasetUnitOfWork(
            session_factory=session_factory,
        ),
        storage_key_builder=DatasetObjectKeyBuilder(),
        maximum_upload_bytes=10_000_000,
    )


def build_command(
    *,
    workspace_id: UUID,
    project_id: UUID,
    user_id: UUID,
) -> RegisterDatasetCommand:
    return RegisterDatasetCommand(
        workspace_id=workspace_id,
        project_id=project_id,
        created_by_user_id=user_id,
        source_filename="campaign-results.csv",
        media_type="text/csv",
        byte_size=4096,
        checksum_sha256=CHECKSUM,
    )


@pytest.mark.asyncio
async def test_persists_registered_dataset_in_postgres(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    workspace_id, project_id, user_id = await seed_active_project(
        tenancy_session_factory,
    )

    result = await build_service(
        tenancy_session_factory,
    ).execute(
        build_command(
            workspace_id=workspace_id,
            project_id=project_id,
            user_id=user_id,
        )
    )

    async with tenancy_session_factory() as session:
        model = await session.scalar(
            select(DatasetModel).where(
                DatasetModel.id == result.id,
            )
        )

    assert model is not None
    assert model.workspace_id == workspace_id
    assert model.project_id == project_id
    assert model.created_by_user_id == user_id
    assert model.status == DatasetStatus.PENDING_UPLOAD.value
    assert model.storage_key == result.storage_key
    assert model.checksum_sha256 == CHECKSUM


@pytest.mark.asyncio
async def test_rejects_cross_workspace_project_without_insert(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    _, project_id, user_id = await seed_active_project(
        tenancy_session_factory,
    )

    with pytest.raises(
        DatasetProjectUnavailableError,
        match="Dataset project is unavailable",
    ):
        await build_service(
            tenancy_session_factory,
        ).execute(
            build_command(
                workspace_id=uuid4(),
                project_id=project_id,
                user_id=user_id,
            )
        )

    async with tenancy_session_factory() as session:
        dataset_count = await session.scalar(
            select(func.count()).select_from(
                DatasetModel,
            )
        )

    assert dataset_count == 0


@pytest.mark.asyncio
async def test_duplicate_storage_key_is_translated_to_conflict(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    workspace_id, project_id, user_id = await seed_active_project(
        tenancy_session_factory,
    )

    command = build_command(
        workspace_id=workspace_id,
        project_id=project_id,
        user_id=user_id,
    )

    service = build_service(
        tenancy_session_factory,
    )

    await service.execute(command)

    with pytest.raises(
        DatasetPersistenceConflictError,
        match="conflicts with an existing record",
    ):
        await service.execute(command)

    async with tenancy_session_factory() as session:
        dataset_count = await session.scalar(
            select(func.count()).select_from(
                DatasetModel,
            )
        )

    assert dataset_count == 1
