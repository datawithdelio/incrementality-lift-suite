from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from incrementality_api.application.datasets.errors import (
    DatasetSemanticMappingUnavailableError,
)
from incrementality_api.application.datasets.manage_semantic_mapping import (
    CreateDatasetSemanticMapping,
    CreateDatasetSemanticMappingCommand,
    GetDatasetSemanticMapping,
    GetDatasetSemanticMappingQuery,
)
from incrementality_api.domain.datasets.columns import (
    DatasetColumnProfile,
    DatasetColumnType,
)
from incrementality_api.domain.datasets.entities import Dataset
from incrementality_api.domain.projects.status import (
    ProjectStatus,
)
from incrementality_api.infrastructure.database.models.dataset_semantic_mappings import (
    DatasetMappingCovariateModel,
    DatasetSemanticMappingModel,
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
    to_dataset_column_model,
)
from incrementality_api.infrastructure.database.repositories.datasets import (
    to_dataset_model,
)
from incrementality_api.infrastructure.database.unit_of_work.datasets import (
    SqlAlchemyDatasetUnitOfWork,
)

CREATED_AT = datetime(
    2026,
    7,
    14,
    23,
    0,
    tzinfo=UTC,
)

UPLOADED_AT = datetime(
    2026,
    7,
    14,
    23,
    1,
    tzinfo=UTC,
)

VALIDATION_STARTED_AT = datetime(
    2026,
    7,
    14,
    23,
    2,
    tzinfo=UTC,
)

VALIDATION_COMPLETED_AT = datetime(
    2026,
    7,
    14,
    23,
    3,
    tzinfo=UTC,
)

FIRST_MAPPING_TIME = datetime(
    2026,
    7,
    14,
    23,
    4,
    tzinfo=UTC,
)

SECOND_MAPPING_TIME = datetime(
    2026,
    7,
    14,
    23,
    5,
    tzinfo=UTC,
)


@dataclass(frozen=True, slots=True)
class SeededDataset:
    workspace_id: UUID
    project_id: UUID
    user_id: UUID
    dataset_id: UUID


class FixedClock:
    def __init__(
        self,
        timestamp: datetime,
    ) -> None:
        self._timestamp = timestamp

    def now(self) -> datetime:
        return self._timestamp


def build_profiles() -> tuple[
    DatasetColumnProfile,
    ...,
]:
    return (
        DatasetColumnProfile(
            ordinal_position=1,
            source_name="Date",
            normalized_name="date",
            inferred_type=DatasetColumnType.DATE,
            nullable=False,
            missing_count=0,
        ),
        DatasetColumnProfile(
            ordinal_position=2,
            source_name="Market",
            normalized_name="market",
            inferred_type=DatasetColumnType.STRING,
            nullable=False,
            missing_count=0,
        ),
        DatasetColumnProfile(
            ordinal_position=3,
            source_name="Treated",
            normalized_name="treated",
            inferred_type=DatasetColumnType.BOOLEAN,
            nullable=False,
            missing_count=0,
        ),
        DatasetColumnProfile(
            ordinal_position=4,
            source_name="Revenue",
            normalized_name="revenue",
            inferred_type=DatasetColumnType.FLOAT,
            nullable=False,
            missing_count=0,
        ),
        DatasetColumnProfile(
            ordinal_position=5,
            source_name="Spend",
            normalized_name="spend",
            inferred_type=DatasetColumnType.FLOAT,
            nullable=False,
            missing_count=0,
        ),
        DatasetColumnProfile(
            ordinal_position=6,
            source_name="Promotion",
            normalized_name="promotion",
            inferred_type=DatasetColumnType.STRING,
            nullable=False,
            missing_count=0,
        ),
        DatasetColumnProfile(
            ordinal_position=7,
            source_name="Seasonality",
            normalized_name="seasonality",
            inferred_type=DatasetColumnType.FLOAT,
            nullable=False,
            missing_count=0,
        ),
    )


async def seed_ready_dataset(
    session_factory: async_sessionmaker[AsyncSession],
) -> SeededDataset:
    organization_id = uuid4()
    workspace_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()

    dataset = (
        Dataset.register(
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
            byte_size=4_096,
            checksum_sha256="a" * 64,
        )
        .mark_uploaded(
            uploaded_at=UPLOADED_AT,
        )
        .begin_validation(
            validation_started_at=(VALIDATION_STARTED_AT),
        )
        .mark_ready(
            validation_completed_at=(VALIDATION_COMPLETED_AT),
            row_count=100,
            column_count=7,
        )
    )

    async with (
        session_factory() as session,
        session.begin(),
    ):
        session.add_all(
            [
                OrganizationModel(
                    id=organization_id,
                    name="Semantic Repository Organization",
                    slug=f"organization-{organization_id}",
                    created_at=CREATED_AT,
                    updated_at=CREATED_AT,
                ),
                UserModel(
                    id=user_id,
                    email=f"{user_id}@example.com",
                    display_name="Semantic Repository User",
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
                name="Semantic Repository Workspace",
                slug=f"workspace-{workspace_id}",
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
                name="Semantic Repository Project",
                slug=f"project-{project_id}",
                description=None,
                status=ProjectStatus.ACTIVE.value,
                archived_at=None,
                created_at=CREATED_AT,
                updated_at=CREATED_AT,
            )
        )

        await session.flush()

        session.add(to_dataset_model(dataset))

        await session.flush()

        session.add_all(
            [
                to_dataset_column_model(
                    dataset_id=dataset.id,
                    profile=profile,
                )
                for profile in build_profiles()
            ]
        )

    return SeededDataset(
        workspace_id=workspace_id,
        project_id=project_id,
        user_id=user_id,
        dataset_id=dataset.id,
    )


def build_command(
    seed: SeededDataset,
) -> CreateDatasetSemanticMappingCommand:
    return CreateDatasetSemanticMappingCommand(
        workspace_id=seed.workspace_id,
        project_id=seed.project_id,
        dataset_id=seed.dataset_id,
        created_by_user_id=seed.user_id,
        time_column="Date",
        unit_column="Market",
        treatment_column="Treated",
        outcome_column="Revenue",
        spend_column="Spend",
        covariate_columns=(
            "Seasonality",
            "Promotion",
        ),
        treatment_value=" true ",
        control_value=" false ",
    )


@pytest.mark.asyncio
async def test_persists_versions_and_reads_latest_and_specific_mapping(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    seed = await seed_ready_dataset(
        tenancy_session_factory,
    )

    first = await CreateDatasetSemanticMapping(
        unit_of_work=SqlAlchemyDatasetUnitOfWork(
            session_factory=tenancy_session_factory,
        ),
        clock=FixedClock(FIRST_MAPPING_TIME),
    ).execute(build_command(seed))

    second = await CreateDatasetSemanticMapping(
        unit_of_work=SqlAlchemyDatasetUnitOfWork(
            session_factory=tenancy_session_factory,
        ),
        clock=FixedClock(SECOND_MAPPING_TIME),
    ).execute(build_command(seed))

    latest = await GetDatasetSemanticMapping(
        unit_of_work=SqlAlchemyDatasetUnitOfWork(
            session_factory=tenancy_session_factory,
        ),
    ).execute(
        GetDatasetSemanticMappingQuery(
            workspace_id=seed.workspace_id,
            project_id=seed.project_id,
            dataset_id=seed.dataset_id,
        )
    )

    persisted_first = await GetDatasetSemanticMapping(
        unit_of_work=SqlAlchemyDatasetUnitOfWork(
            session_factory=tenancy_session_factory,
        ),
    ).execute(
        GetDatasetSemanticMappingQuery(
            workspace_id=seed.workspace_id,
            project_id=seed.project_id,
            dataset_id=seed.dataset_id,
            version=1,
        )
    )

    assert first.version == 1
    assert second.version == 2
    assert first.id != second.id

    assert latest == second
    assert persisted_first == first

    assert latest.covariate_columns == (
        "seasonality",
        "promotion",
    )

    async with tenancy_session_factory() as session:
        mapping_count = await session.scalar(
            select(func.count()).select_from(DatasetSemanticMappingModel)
        )

        covariate_count = await session.scalar(
            select(func.count()).select_from(DatasetMappingCovariateModel)
        )

    assert mapping_count == 2
    assert covariate_count == 4


@pytest.mark.asyncio
async def test_mapping_read_is_rejected_outside_workspace_scope(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    seed = await seed_ready_dataset(
        tenancy_session_factory,
    )

    await CreateDatasetSemanticMapping(
        unit_of_work=SqlAlchemyDatasetUnitOfWork(
            session_factory=tenancy_session_factory,
        ),
        clock=FixedClock(FIRST_MAPPING_TIME),
    ).execute(build_command(seed))

    with pytest.raises(
        DatasetSemanticMappingUnavailableError,
        match="Semantic mapping is unavailable",
    ):
        await GetDatasetSemanticMapping(
            unit_of_work=SqlAlchemyDatasetUnitOfWork(
                session_factory=(tenancy_session_factory),
            ),
        ).execute(
            GetDatasetSemanticMappingQuery(
                workspace_id=uuid4(),
                project_id=seed.project_id,
                dataset_id=seed.dataset_id,
            )
        )
