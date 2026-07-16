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

from incrementality_api.infrastructure.database.models.analysis_execution_jobs import (
    AnalysisExecutionJobModel,
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
    16,
    12,
    0,
    tzinfo=UTC,
)

UPDATED_AT = datetime(
    2026,
    7,
    16,
    12,
    1,
    tzinfo=UTC,
)

AVAILABLE_AT = datetime(
    2026,
    7,
    16,
    12,
    2,
    tzinfo=UTC,
)


@dataclass(frozen=True, slots=True)
class SeededExecutionScope:
    workspace_id: UUID
    project_id: UUID
    dataset_id: UUID
    mapping_id: UUID
    analysis_run_id: UUID
    user_id: UUID


async def seed_execution_scope(
    session_factory: async_sessionmaker[AsyncSession],
) -> SeededExecutionScope:
    organization_id = uuid4()
    workspace_id = uuid4()
    project_id = uuid4()
    dataset_id = uuid4()
    mapping_id = uuid4()
    analysis_run_id = uuid4()
    user_id = uuid4()

    async with (
        session_factory() as session,
        session.begin(),
    ):
        session.add_all(
            [
                OrganizationModel(
                    id=organization_id,
                    name="Execution Constraint Organization",
                    slug=f"organization-{organization_id}",
                    created_at=CREATED_AT,
                    updated_at=UPDATED_AT,
                ),
                UserModel(
                    id=user_id,
                    email=f"{user_id}@example.com",
                    display_name="Execution Constraint User",
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
                name="Execution Constraint Workspace",
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
                name="Execution Constraint Project",
                slug=f"project-{project_id}",
                description=None,
                status="active",
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
                source_filename="execution-input.csv",
                storage_key=(
                    f"workspaces/{workspace_id}/projects/"
                    f"{project_id}/datasets/"
                    f"{dataset_id}/execution-input.csv"
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

        await session.flush()

        session.add(
            AnalysisRunModel(
                id=analysis_run_id,
                workspace_id=workspace_id,
                project_id=project_id,
                dataset_id=dataset_id,
                dataset_checksum_sha256="c" * 64,
                dataset_byte_size=4_096,
                semantic_mapping_id=mapping_id,
                semantic_mapping_version=1,
                created_by_user_id=user_id,
                estimator_type=("difference_in_differences"),
                estimator_version="did-v1",
                configuration_json=('{"alpha":0.05}'),
                status="queued",
                started_at=None,
                completed_at=None,
                failure_reason=None,
                cancellation_reason=None,
                created_at=CREATED_AT,
                updated_at=UPDATED_AT,
            )
        )

    return SeededExecutionScope(
        workspace_id=workspace_id,
        project_id=project_id,
        dataset_id=dataset_id,
        mapping_id=mapping_id,
        analysis_run_id=analysis_run_id,
        user_id=user_id,
    )


def build_pending_job(
    scope: SeededExecutionScope,
    *,
    workspace_id: UUID | None = None,
    project_id: UUID | None = None,
) -> AnalysisExecutionJobModel:
    return AnalysisExecutionJobModel(
        id=uuid4(),
        workspace_id=(scope.workspace_id if workspace_id is None else workspace_id),
        project_id=(scope.project_id if project_id is None else project_id),
        analysis_run_id=scope.analysis_run_id,
        status="pending",
        attempt_count=0,
        max_attempts=3,
        available_at=AVAILABLE_AT,
        claimed_at=None,
        completed_at=None,
        last_error=None,
        created_at=CREATED_AT,
        updated_at=UPDATED_AT,
    )


@pytest.mark.asyncio
async def test_persists_valid_pending_execution_job(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    scope = await seed_execution_scope(
        tenancy_session_factory,
    )

    job = build_pending_job(scope)

    async with (
        tenancy_session_factory() as session,
        session.begin(),
    ):
        session.add(job)

    async with tenancy_session_factory() as session:
        persisted = await session.scalar(
            select(AnalysisExecutionJobModel).where(
                AnalysisExecutionJobModel.id == job.id,
            )
        )

    assert persisted is not None
    assert persisted.analysis_run_id == (scope.analysis_run_id)
    assert persisted.status == "pending"
    assert persisted.attempt_count == 0
    assert persisted.max_attempts == 3


@pytest.mark.asyncio
async def test_rejects_execution_job_scope_mismatch(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    primary = await seed_execution_scope(
        tenancy_session_factory,
    )
    secondary = await seed_execution_scope(
        tenancy_session_factory,
    )

    job = build_pending_job(
        primary,
        workspace_id=secondary.workspace_id,
        project_id=secondary.project_id,
    )

    async with tenancy_session_factory() as session:
        session.add(job)

        with pytest.raises(IntegrityError):
            await session.commit()

        await session.rollback()


@pytest.mark.asyncio
async def test_rejects_duplicate_job_for_analysis_run(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    scope = await seed_execution_scope(
        tenancy_session_factory,
    )

    first = build_pending_job(scope)
    second = build_pending_job(scope)

    async with (
        tenancy_session_factory() as session,
        session.begin(),
    ):
        session.add(first)

    async with tenancy_session_factory() as session:
        session.add(second)

        with pytest.raises(IntegrityError):
            await session.commit()

        await session.rollback()


@pytest.mark.asyncio
async def test_rejects_invalid_execution_lifecycle_metadata(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    scope = await seed_execution_scope(
        tenancy_session_factory,
    )

    job = build_pending_job(scope)
    job.status = "succeeded"

    async with tenancy_session_factory() as session:
        session.add(job)

        with pytest.raises(IntegrityError):
            await session.commit()

        await session.rollback()


@pytest.mark.asyncio
async def test_rejects_attempt_count_above_maximum(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    scope = await seed_execution_scope(
        tenancy_session_factory,
    )

    job = build_pending_job(scope)
    job.attempt_count = 4
    job.max_attempts = 3

    async with tenancy_session_factory() as session:
        session.add(job)

        with pytest.raises(IntegrityError):
            await session.commit()

        await session.rollback()


@pytest.mark.asyncio
async def test_analysis_run_deletion_cascades_execution_job(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    scope = await seed_execution_scope(
        tenancy_session_factory,
    )

    job = build_pending_job(scope)

    async with (
        tenancy_session_factory() as session,
        session.begin(),
    ):
        session.add(job)

    async with (
        tenancy_session_factory() as session,
        session.begin(),
    ):
        await session.execute(
            delete(AnalysisRunModel).where(
                AnalysisRunModel.id == scope.analysis_run_id,
            )
        )

    async with tenancy_session_factory() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(AnalysisExecutionJobModel)
            .where(
                AnalysisExecutionJobModel.id == job.id,
            )
        )

    assert count == 0
