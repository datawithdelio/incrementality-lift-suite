from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from incrementality_api.domain.analysis_runs.execution_job_status import (
    AnalysisExecutionJobStatus,
)
from incrementality_api.domain.analysis_runs.execution_jobs import (
    AnalysisExecutionJob,
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
from incrementality_api.infrastructure.database.unit_of_work.analysis_execution_jobs import (
    SqlAlchemyAnalysisExecutionJobUnitOfWork,
)

CREATED_AT = datetime(
    2026,
    7,
    16,
    16,
    0,
    tzinfo=UTC,
)

FIRST_AVAILABLE_AT = datetime(
    2026,
    7,
    16,
    16,
    1,
    tzinfo=UTC,
)

SECOND_AVAILABLE_AT = datetime(
    2026,
    7,
    16,
    16,
    2,
    tzinfo=UTC,
)

CLAIMED_AT = datetime(
    2026,
    7,
    16,
    16,
    3,
    tzinfo=UTC,
)

FAILED_AT = datetime(
    2026,
    7,
    16,
    16,
    4,
    tzinfo=UTC,
)

RETRY_AT = datetime(
    2026,
    7,
    16,
    16,
    5,
    tzinfo=UTC,
)


@dataclass(frozen=True, slots=True)
class SeededExecutionScope:
    workspace_id: UUID
    project_id: UUID
    analysis_run_ids: tuple[UUID, ...]


async def seed_execution_scope(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    analysis_run_count: int,
) -> SeededExecutionScope:
    organization_id = uuid4()
    workspace_id = uuid4()
    project_id = uuid4()
    dataset_id = uuid4()
    mapping_id = uuid4()
    user_id = uuid4()

    analysis_run_ids = tuple(uuid4() for _ in range(analysis_run_count))

    async with (
        session_factory() as session,
        session.begin(),
    ):
        session.add_all(
            [
                OrganizationModel(
                    id=organization_id,
                    name=("Execution Repository Organization"),
                    slug=(f"organization-{organization_id}"),
                    created_at=CREATED_AT,
                    updated_at=CREATED_AT,
                ),
                UserModel(
                    id=user_id,
                    email=(f"{user_id}@example.com"),
                    display_name=("Execution Repository User"),
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
                name=("Execution Repository Workspace"),
                slug=(f"workspace-{workspace_id}"),
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
                name=("Execution Repository Project"),
                slug=(f"project-{project_id}"),
                description=None,
                status="active",
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
                source_filename=("execution-input.csv"),
                storage_key=(
                    f"workspaces/{workspace_id}/"
                    f"projects/{project_id}/"
                    f"datasets/{dataset_id}/"
                    "execution-input.csv"
                ),
                media_type="text/csv",
                byte_size=4_096,
                checksum_sha256=(dataset_id.hex * 2),
                status="ready",
                uploaded_at=CREATED_AT,
                validation_started_at=(CREATED_AT),
                validation_completed_at=(CREATED_AT),
                row_count=100,
                column_count=4,
                failure_reason=None,
                created_at=CREATED_AT,
                updated_at=CREATED_AT,
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
                updated_at=CREATED_AT,
            )
        )

        await session.flush()

        session.add_all(
            [
                AnalysisRunModel(
                    id=analysis_run_id,
                    workspace_id=workspace_id,
                    project_id=project_id,
                    dataset_id=dataset_id,
                    semantic_mapping_id=(mapping_id),
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
                    created_at=(
                        CREATED_AT
                        + timedelta(
                            seconds=index,
                        )
                    ),
                    updated_at=(
                        CREATED_AT
                        + timedelta(
                            seconds=index,
                        )
                    ),
                )
                for index, analysis_run_id in enumerate(analysis_run_ids)
            ]
        )

    return SeededExecutionScope(
        workspace_id=workspace_id,
        project_id=project_id,
        analysis_run_ids=analysis_run_ids,
    )


def build_job(
    scope: SeededExecutionScope,
    *,
    run_index: int,
    available_at: datetime,
) -> AnalysisExecutionJob:
    return AnalysisExecutionJob.enqueue(
        workspace_id=scope.workspace_id,
        project_id=scope.project_id,
        analysis_run_id=(scope.analysis_run_ids[run_index]),
        created_at=CREATED_AT,
        available_at=available_at,
        max_attempts=3,
    )


@pytest.mark.asyncio
async def test_persists_and_retrieves_execution_job(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    scope = await seed_execution_scope(
        tenancy_session_factory,
        analysis_run_count=1,
    )

    job = build_job(
        scope,
        run_index=0,
        available_at=FIRST_AVAILABLE_AT,
    )

    unit_of_work = SqlAlchemyAnalysisExecutionJobUnitOfWork(
        session_factory=(tenancy_session_factory),
    )

    async with unit_of_work:
        await unit_of_work.execution_jobs.add(job)
        await unit_of_work.commit()

    read_unit_of_work = SqlAlchemyAnalysisExecutionJobUnitOfWork(
        session_factory=(tenancy_session_factory),
    )

    async with read_unit_of_work:
        persisted = await read_unit_of_work.execution_jobs.get_by_id(job.id)

    assert persisted == job

    assert persisted is not None
    assert persisted.status is (AnalysisExecutionJobStatus.PENDING)

    by_run_unit_of_work = SqlAlchemyAnalysisExecutionJobUnitOfWork(
        session_factory=(tenancy_session_factory),
    )

    async with by_run_unit_of_work:
        by_run = await by_run_unit_of_work.execution_jobs.get_by_analysis_run_id(
            job.analysis_run_id
        )

    assert by_run == job


@pytest.mark.asyncio
async def test_claims_earliest_available_job_and_persists_running_state(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    scope = await seed_execution_scope(
        tenancy_session_factory,
        analysis_run_count=2,
    )

    first = build_job(
        scope,
        run_index=0,
        available_at=FIRST_AVAILABLE_AT,
    )

    second = build_job(
        scope,
        run_index=1,
        available_at=SECOND_AVAILABLE_AT,
    )

    create_unit_of_work = SqlAlchemyAnalysisExecutionJobUnitOfWork(
        session_factory=(tenancy_session_factory),
    )

    async with create_unit_of_work:
        await create_unit_of_work.execution_jobs.add(first)

        await create_unit_of_work.execution_jobs.add(second)

        await create_unit_of_work.commit()

    claim_unit_of_work = SqlAlchemyAnalysisExecutionJobUnitOfWork(
        session_factory=(tenancy_session_factory),
    )

    async with claim_unit_of_work:
        pending = await claim_unit_of_work.execution_jobs.get_next_available_for_update(
            available_at=CLAIMED_AT,
        )

        assert pending is not None
        assert pending.id == first.id

        running = pending.claim(
            claimed_at=CLAIMED_AT,
        )

        await claim_unit_of_work.execution_jobs.update(running)

        await claim_unit_of_work.commit()

    verify_unit_of_work = SqlAlchemyAnalysisExecutionJobUnitOfWork(
        session_factory=(tenancy_session_factory),
    )

    async with verify_unit_of_work:
        persisted = await verify_unit_of_work.execution_jobs.get_by_id(first.id)

    assert persisted is not None
    assert persisted.status is (AnalysisExecutionJobStatus.RUNNING)
    assert persisted.attempt_count == 1
    assert persisted.claimed_at == CLAIMED_AT


@pytest.mark.asyncio
async def test_concurrent_claimers_skip_locked_job(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    scope = await seed_execution_scope(
        tenancy_session_factory,
        analysis_run_count=2,
    )

    first = build_job(
        scope,
        run_index=0,
        available_at=FIRST_AVAILABLE_AT,
    )

    second = build_job(
        scope,
        run_index=1,
        available_at=SECOND_AVAILABLE_AT,
    )

    create_unit_of_work = SqlAlchemyAnalysisExecutionJobUnitOfWork(
        session_factory=(tenancy_session_factory),
    )

    async with create_unit_of_work:
        await create_unit_of_work.execution_jobs.add(first)
        await create_unit_of_work.execution_jobs.add(second)
        await create_unit_of_work.commit()

    first_worker = SqlAlchemyAnalysisExecutionJobUnitOfWork(
        session_factory=(tenancy_session_factory),
    )

    second_worker = SqlAlchemyAnalysisExecutionJobUnitOfWork(
        session_factory=(tenancy_session_factory),
    )

    async with first_worker:
        first_claim = await first_worker.execution_jobs.get_next_available_for_update(
            available_at=CLAIMED_AT,
        )

        assert first_claim is not None
        assert first_claim.id == first.id

        async with second_worker:
            second_claim = await second_worker.execution_jobs.get_next_available_for_update(
                available_at=CLAIMED_AT,
            )

            assert second_claim is not None
            assert second_claim.id == second.id

            await second_worker.rollback()

        await first_worker.rollback()


@pytest.mark.asyncio
async def test_persists_retry_and_reclaims_when_available(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    scope = await seed_execution_scope(
        tenancy_session_factory,
        analysis_run_count=1,
    )

    job = build_job(
        scope,
        run_index=0,
        available_at=FIRST_AVAILABLE_AT,
    )

    create_unit_of_work = SqlAlchemyAnalysisExecutionJobUnitOfWork(
        session_factory=(tenancy_session_factory),
    )

    async with create_unit_of_work:
        await create_unit_of_work.execution_jobs.add(job)
        await create_unit_of_work.commit()

    claim_unit_of_work = SqlAlchemyAnalysisExecutionJobUnitOfWork(
        session_factory=(tenancy_session_factory),
    )

    async with claim_unit_of_work:
        pending = await claim_unit_of_work.execution_jobs.get_next_available_for_update(
            available_at=CLAIMED_AT,
        )

        assert pending is not None

        running = pending.claim(
            claimed_at=CLAIMED_AT,
        )

        await claim_unit_of_work.execution_jobs.update(running)

        await claim_unit_of_work.commit()

    retry_unit_of_work = SqlAlchemyAnalysisExecutionJobUnitOfWork(
        session_factory=(tenancy_session_factory),
    )

    async with retry_unit_of_work:
        locked = await retry_unit_of_work.execution_jobs.get_by_id_for_update(job.id)

        assert locked is not None

        retrying = locked.retry(
            failed_at=FAILED_AT,
            available_at=RETRY_AT,
            error=("Estimator service temporarily unavailable."),
        )

        await retry_unit_of_work.execution_jobs.update(retrying)

        await retry_unit_of_work.commit()

    before_retry_unit_of_work = SqlAlchemyAnalysisExecutionJobUnitOfWork(
        session_factory=(tenancy_session_factory),
    )

    async with before_retry_unit_of_work:
        unavailable = await before_retry_unit_of_work.execution_jobs.get_next_available_for_update(
            available_at=(RETRY_AT - timedelta(seconds=1)),
        )

        assert unavailable is None

    reclaim_unit_of_work = SqlAlchemyAnalysisExecutionJobUnitOfWork(
        session_factory=(tenancy_session_factory),
    )

    async with reclaim_unit_of_work:
        available = await reclaim_unit_of_work.execution_jobs.get_next_available_for_update(
            available_at=RETRY_AT,
        )

        assert available is not None
        assert available.id == job.id
        assert available.attempt_count == 1
        assert available.last_error == ("Estimator service temporarily unavailable.")

        running_again = available.claim(
            claimed_at=RETRY_AT,
        )

        await reclaim_unit_of_work.execution_jobs.update(running_again)

        await reclaim_unit_of_work.commit()

    verify_unit_of_work = SqlAlchemyAnalysisExecutionJobUnitOfWork(
        session_factory=(tenancy_session_factory),
    )

    async with verify_unit_of_work:
        persisted = await verify_unit_of_work.execution_jobs.get_by_id(job.id)

    assert persisted is not None
    assert persisted.status is (AnalysisExecutionJobStatus.RUNNING)
    assert persisted.attempt_count == 2
    assert persisted.claimed_at == RETRY_AT
    assert persisted.last_error is None


@pytest.mark.asyncio
async def test_finds_stale_running_job_for_recovery(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    scope = await seed_execution_scope(
        tenancy_session_factory,
        analysis_run_count=1,
    )

    running = build_job(
        scope,
        run_index=0,
        available_at=FIRST_AVAILABLE_AT,
    ).claim(
        claimed_at=CLAIMED_AT,
    )

    create_unit_of_work = SqlAlchemyAnalysisExecutionJobUnitOfWork(
        session_factory=(tenancy_session_factory),
    )

    async with create_unit_of_work:
        await create_unit_of_work.execution_jobs.add(running)
        await create_unit_of_work.commit()

    recovery_unit_of_work = SqlAlchemyAnalysisExecutionJobUnitOfWork(
        session_factory=(tenancy_session_factory),
    )

    async with recovery_unit_of_work:
        stale = await recovery_unit_of_work.execution_jobs.get_stale_running_for_update(
            claimed_before=CLAIMED_AT,
        )

        assert stale == running

        await recovery_unit_of_work.rollback()
