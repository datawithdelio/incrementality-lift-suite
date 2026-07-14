from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from incrementality_api.domain.datasets.columns import (
    DatasetColumnProfile,
    DatasetColumnType,
)
from incrementality_api.domain.datasets.entities import Dataset
from incrementality_api.domain.projects.status import (
    ProjectStatus,
)
from incrementality_api.infrastructure.database.models.projects import (
    ProjectModel,
)
from incrementality_api.infrastructure.database.models.tenancy import (
    OrganizationModel,
    UserModel,
    WorkspaceModel,
)
from incrementality_api.infrastructure.database.repositories.dataset_columns import (
    SqlAlchemyDatasetColumnRepository,
)
from incrementality_api.infrastructure.database.repositories.datasets import (
    to_dataset_model,
)

FIXED_NOW = datetime(
    2026,
    7,
    14,
    13,
    0,
    tzinfo=UTC,
)


def build_profiles() -> tuple[
    DatasetColumnProfile,
    ...,
]:
    return (
        DatasetColumnProfile(
            ordinal_position=1,
            source_name="Market",
            normalized_name="market",
            inferred_type=DatasetColumnType.STRING,
            nullable=False,
            missing_count=0,
        ),
        DatasetColumnProfile(
            ordinal_position=2,
            source_name="Revenue",
            normalized_name="revenue",
            inferred_type=DatasetColumnType.FLOAT,
            nullable=True,
            missing_count=2,
        ),
    )


async def seed_dataset(
    session_factory: async_sessionmaker[AsyncSession],
) -> tuple[UUID, UUID, UUID]:
    organization_id = uuid4()
    workspace_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()

    dataset = Dataset.register(
        workspace_id=workspace_id,
        project_id=project_id,
        created_by_user_id=user_id,
        source_filename="campaign-results.csv",
        storage_key=(
            f"workspaces/{workspace_id}/projects/"
            f"{project_id}/datasets/"
            f"{'a' * 64}/campaign-results.csv"
        ),
        media_type="text/csv",
        byte_size=1_024,
        checksum_sha256="a" * 64,
    )

    async with (
        session_factory() as session,
        session.begin(),
    ):
        session.add_all(
            [
                OrganizationModel(
                    id=organization_id,
                    name="Column Repository Organization",
                    slug=f"organization-{organization_id}",
                    created_at=FIXED_NOW,
                    updated_at=FIXED_NOW,
                ),
                UserModel(
                    id=user_id,
                    email=f"{user_id}@example.com",
                    display_name="Column Repository User",
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
                name="Column Repository Workspace",
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
                name="Column Repository Project",
                slug=f"project-{project_id}",
                description=None,
                status=ProjectStatus.ACTIVE.value,
                archived_at=None,
                created_at=FIXED_NOW,
                updated_at=FIXED_NOW,
            )
        )

        await session.flush()
        session.add(to_dataset_model(dataset))

    return (
        workspace_id,
        project_id,
        dataset.id,
    )


@pytest.mark.asyncio
async def test_replaces_and_reads_columns_in_tenant_scope(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    workspace_id, project_id, dataset_id = await seed_dataset(
        tenancy_session_factory,
    )

    profiles = build_profiles()

    async with (
        tenancy_session_factory() as session,
        session.begin(),
    ):
        repository = SqlAlchemyDatasetColumnRepository(
            session=session,
        )

        await repository.replace_for_dataset(
            dataset_id=dataset_id,
            columns=tuple(reversed(profiles)),
        )

    async with tenancy_session_factory() as session:
        repository = SqlAlchemyDatasetColumnRepository(
            session=session,
        )

        result = await repository.list_by_scope(
            workspace_id=workspace_id,
            project_id=project_id,
            dataset_id=dataset_id,
        )

        wrong_workspace_result = await repository.list_by_scope(
            workspace_id=uuid4(),
            project_id=project_id,
            dataset_id=dataset_id,
        )

    assert result == profiles
    assert wrong_workspace_result == ()


@pytest.mark.asyncio
async def test_replacement_removes_previous_columns(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    workspace_id, project_id, dataset_id = await seed_dataset(
        tenancy_session_factory,
    )

    async with (
        tenancy_session_factory() as session,
        session.begin(),
    ):
        repository = SqlAlchemyDatasetColumnRepository(
            session=session,
        )

        await repository.replace_for_dataset(
            dataset_id=dataset_id,
            columns=build_profiles(),
        )

    replacement = (
        DatasetColumnProfile(
            ordinal_position=1,
            source_name="Orders",
            normalized_name="orders",
            inferred_type=DatasetColumnType.INTEGER,
            nullable=False,
            missing_count=0,
        ),
    )

    async with (
        tenancy_session_factory() as session,
        session.begin(),
    ):
        repository = SqlAlchemyDatasetColumnRepository(
            session=session,
        )

        await repository.replace_for_dataset(
            dataset_id=dataset_id,
            columns=replacement,
        )

    async with tenancy_session_factory() as session:
        result = await (
            SqlAlchemyDatasetColumnRepository(
                session=session,
            )
        ).list_by_scope(
            workspace_id=workspace_id,
            project_id=project_id,
            dataset_id=dataset_id,
        )

    assert result == replacement
