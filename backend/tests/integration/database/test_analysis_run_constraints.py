from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from incrementality_api.domain.analysis_runs.status import (
    AnalysisEstimatorType,
    AnalysisRunStatus,
)
from incrementality_api.domain.projects.status import (
    ProjectStatus,
)
from incrementality_api.infrastructure.database.models.analysis_runs import (
    AnalysisRunModel,
)
from incrementality_api.infrastructure.database.models.dataset_columns import (
    DatasetColumnModel,
)
from incrementality_api.infrastructure.database.models.dataset_semantic_mappings import (
    DatasetSemanticMappingModel,
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

CREATED_AT = datetime(
    2026,
    7,
    15,
    14,
    0,
    tzinfo=UTC,
)

UPDATED_AT = datetime(
    2026,
    7,
    15,
    14,
    1,
    tzinfo=UTC,
)


@dataclass(frozen=True, slots=True)
class SeededAnalysisScope:
    workspace_id: UUID
    project_id: UUID
    dataset_id: UUID
    mapping_id: UUID
    user_id: UUID


async def seed_analysis_scope(
    session_factory: async_sessionmaker[AsyncSession],
) -> SeededAnalysisScope:
    organization_id = uuid4()
    workspace_id = uuid4()
    project_id = uuid4()
    dataset_id = uuid4()
    mapping_id = uuid4()
    user_id = uuid4()

    async with (
        session_factory() as session,
        session.begin(),
    ):
        session.add_all(
            [
                OrganizationModel(
                    id=organization_id,
                    name="Analysis Constraint Organization",
                    slug=f"organization-{organization_id}",
                    created_at=CREATED_AT,
                    updated_at=UPDATED_AT,
                ),
                UserModel(
                    id=user_id,
                    email=f"{user_id}@example.com",
                    display_name="Analysis Constraint User",
                    created_at=CREATED_AT,
                    updated_at=UPDATED_AT,
                ),
            ]
        )

        await session.flush()

        session.add(
            WorkspaceModel(
                id=workspace_id,
                organization_id=organization_id,
                name="Analysis Constraint Workspace",
                slug=f"workspace-{workspace_id}",
                created_at=CREATED_AT,
                updated_at=UPDATED_AT,
            )
        )

        await session.flush()

        session.add(
            ProjectModel(
                id=project_id,
                workspace_id=workspace_id,
                created_by_user_id=user_id,
                name="Analysis Constraint Project",
                slug=f"project-{project_id}",
                description=None,
                status=ProjectStatus.ACTIVE.value,
                archived_at=None,
                created_at=CREATED_AT,
                updated_at=UPDATED_AT,
            )
        )

        await session.flush()

        session.add(
            DatasetModel(
                id=dataset_id,
                workspace_id=workspace_id,
                project_id=project_id,
                created_by_user_id=user_id,
                source_filename="analysis-input.csv",
                storage_key=(
                    f"workspaces/{workspace_id}/projects/"
                    f"{project_id}/datasets/"
                    f"{dataset_id}/analysis-input.csv"
                ),
                media_type="text/csv",
                byte_size=4_096,
                checksum_sha256=dataset_id.hex * 2,
                status="ready",
                uploaded_at=CREATED_AT,
                validation_started_at=CREATED_AT,
                validation_completed_at=UPDATED_AT,
                row_count=100,
                column_count=4,
                failure_reason=None,
                created_at=CREATED_AT,
                updated_at=UPDATED_AT,
            )
        )

        await session.flush()

        session.add_all(
            [
                DatasetColumnModel(
                    dataset_id=dataset_id,
                    ordinal_position=1,
                    source_name="Date",
                    normalized_name="date",
                    inferred_type="date",
                    nullable=False,
                    missing_count=0,
                ),
                DatasetColumnModel(
                    dataset_id=dataset_id,
                    ordinal_position=2,
                    source_name="Market",
                    normalized_name="market",
                    inferred_type="string",
                    nullable=False,
                    missing_count=0,
                ),
                DatasetColumnModel(
                    dataset_id=dataset_id,
                    ordinal_position=3,
                    source_name="Treated",
                    normalized_name="treated",
                    inferred_type="boolean",
                    nullable=False,
                    missing_count=0,
                ),
                DatasetColumnModel(
                    dataset_id=dataset_id,
                    ordinal_position=4,
                    source_name="Revenue",
                    normalized_name="revenue",
                    inferred_type="float",
                    nullable=False,
                    missing_count=0,
                ),
            ]
        )

        await session.flush()

        session.add(
            DatasetSemanticMappingModel(
                id=mapping_id,
                dataset_id=dataset_id,
                created_by_user_id=user_id,
                version=1,
                time_column="date",
                unit_column="market",
                treatment_column="treated",
                outcome_column="revenue",
                spend_column=None,
                treatment_value="true",
                control_value="false",
                created_at=CREATED_AT,
                updated_at=UPDATED_AT,
            )
        )

    return SeededAnalysisScope(
        workspace_id=workspace_id,
        project_id=project_id,
        dataset_id=dataset_id,
        mapping_id=mapping_id,
        user_id=user_id,
    )


def build_queued_run(
    scope: SeededAnalysisScope,
    *,
    workspace_id: UUID | None = None,
    project_id: UUID | None = None,
    mapping_version: int = 1,
) -> AnalysisRunModel:
    return AnalysisRunModel(
        id=uuid4(),
        workspace_id=(scope.workspace_id if workspace_id is None else workspace_id),
        project_id=(scope.project_id if project_id is None else project_id),
        dataset_id=scope.dataset_id,
        dataset_checksum_sha256="c" * 64,
        dataset_byte_size=4_096,
        semantic_mapping_id=scope.mapping_id,
        semantic_mapping_version=mapping_version,
        created_by_user_id=scope.user_id,
        estimator_type=(AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES.value),
        estimator_version="did-v1",
        configuration_json=('{"alpha":0.05,"cluster_by":"unit"}'),
        status=AnalysisRunStatus.QUEUED.value,
        started_at=None,
        completed_at=None,
        failure_reason=None,
        cancellation_reason=None,
        created_at=CREATED_AT,
        updated_at=UPDATED_AT,
    )


@pytest.mark.asyncio
async def test_persists_valid_queued_analysis_run(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    scope = await seed_analysis_scope(
        tenancy_session_factory,
    )

    run = build_queued_run(scope)

    async with (
        tenancy_session_factory() as session,
        session.begin(),
    ):
        session.add(run)

    async with tenancy_session_factory() as session:
        persisted = await session.scalar(
            select(AnalysisRunModel).where(
                AnalysisRunModel.id == run.id,
            )
        )

    assert persisted is not None
    assert persisted.workspace_id == scope.workspace_id
    assert persisted.project_id == scope.project_id
    assert persisted.dataset_id == scope.dataset_id
    assert persisted.semantic_mapping_id == (scope.mapping_id)
    assert persisted.semantic_mapping_version == 1
    assert persisted.status == "queued"
    assert persisted.application_version is None
    assert persisted.source_revision is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field_name",
    [
        "application_version",
        "source_revision",
    ],
)
async def test_rejects_blank_runtime_lineage(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
    field_name: str,
) -> None:
    scope = await seed_analysis_scope(tenancy_session_factory)
    run = build_queued_run(scope)
    run.application_version = "0.1.0"
    run.source_revision = "a" * 40
    setattr(run, field_name, "   ")

    async with tenancy_session_factory() as session:
        session.add(run)

        with pytest.raises(IntegrityError):
            await session.commit()

        await session.rollback()


@pytest.mark.asyncio
async def test_rejects_dataset_scope_mismatch(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    primary = await seed_analysis_scope(
        tenancy_session_factory,
    )
    secondary = await seed_analysis_scope(
        tenancy_session_factory,
    )

    run = build_queued_run(
        primary,
        workspace_id=secondary.workspace_id,
        project_id=secondary.project_id,
    )

    async with tenancy_session_factory() as session:
        session.add(run)

        with pytest.raises(IntegrityError):
            await session.commit()

        await session.rollback()


@pytest.mark.asyncio
async def test_rejects_nonexistent_mapping_snapshot_version(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    scope = await seed_analysis_scope(
        tenancy_session_factory,
    )

    run = build_queued_run(
        scope,
        mapping_version=2,
    )

    async with tenancy_session_factory() as session:
        session.add(run)

        with pytest.raises(IntegrityError):
            await session.commit()

        await session.rollback()


@pytest.mark.asyncio
async def test_rejects_invalid_lifecycle_metadata(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    scope = await seed_analysis_scope(
        tenancy_session_factory,
    )

    run = build_queued_run(scope)
    run.status = AnalysisRunStatus.SUCCEEDED.value

    async with tenancy_session_factory() as session:
        session.add(run)

        with pytest.raises(IntegrityError):
            await session.commit()

        await session.rollback()


@pytest.mark.asyncio
async def test_dataset_deletion_cascades_analysis_runs(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    scope = await seed_analysis_scope(
        tenancy_session_factory,
    )

    run = build_queued_run(scope)

    async with (
        tenancy_session_factory() as session,
        session.begin(),
    ):
        session.add(run)

    async with (
        tenancy_session_factory() as session,
        session.begin(),
    ):
        await session.execute(
            delete(DatasetModel).where(
                DatasetModel.id == scope.dataset_id,
            )
        )

    async with tenancy_session_factory() as session:
        run_count = await session.scalar(
            select(func.count())
            .select_from(AnalysisRunModel)
            .where(
                AnalysisRunModel.id == run.id,
            )
        )

    assert run_count == 0
