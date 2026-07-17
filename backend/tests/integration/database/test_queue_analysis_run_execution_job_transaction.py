from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from incrementality_api.application.analysis_runs.manage_analysis_runs import (
    QueueAnalysisRun,
    QueueAnalysisRunCommand,
)
from incrementality_api.domain.analysis_runs.execution_jobs import (
    AnalysisExecutionJob,
)
from incrementality_api.domain.analysis_runs.status import (
    AnalysisEstimatorType,
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
from incrementality_api.infrastructure.database.unit_of_work.analysis_runs import (
    SqlAlchemyAnalysisRunUnitOfWork,
)
from incrementality_api.infrastructure.estimation.runtime_versions import (
    StatisticalRuntimeVersionProvider,
)

APPLICATION_VERSION = "0.1.0"
SOURCE_REVISION = "a" * 40

FIXED_NOW = datetime(
    2026,
    7,
    16,
    20,
    0,
    tzinfo=UTC,
)


class FixedClock:
    def now(self) -> datetime:
        return FIXED_NOW


class FailingExecutionJobRepository:
    async def add(
        self,
        job: AnalysisExecutionJob,
    ) -> None:
        del job

        raise RuntimeError("Execution job persistence failed.")


class FailingExecutionJobUnitOfWork(SqlAlchemyAnalysisRunUnitOfWork):
    async def __aenter__(
        self,
    ) -> "FailingExecutionJobUnitOfWork":
        await super().__aenter__()

        self.execution_jobs = FailingExecutionJobRepository()

        return self


async def seed_ready_dataset_and_mapping(
    session_factory: async_sessionmaker[AsyncSession],
) -> tuple[UUID, UUID, UUID, UUID, UUID]:
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
                    name="Atomic Analysis Organization",
                    slug=f"organization-{organization_id}",
                    created_at=FIXED_NOW,
                    updated_at=FIXED_NOW,
                ),
                UserModel(
                    id=user_id,
                    email=f"{user_id}@example.com",
                    display_name="Atomic Analysis User",
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
                name="Atomic Analysis Workspace",
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
                name="Atomic Analysis Project",
                slug=f"project-{project_id}",
                description=None,
                status="active",
                archived_at=None,
                created_at=FIXED_NOW,
                updated_at=FIXED_NOW,
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
                    f"workspaces/{workspace_id}/"
                    f"projects/{project_id}/"
                    f"datasets/{dataset_id}/"
                    "analysis-input.csv"
                ),
                media_type="text/csv",
                byte_size=4_096,
                checksum_sha256=dataset_id.hex * 2,
                status="ready",
                uploaded_at=FIXED_NOW,
                validation_started_at=FIXED_NOW,
                validation_completed_at=FIXED_NOW,
                row_count=100,
                column_count=4,
                failure_reason=None,
                created_at=FIXED_NOW,
                updated_at=FIXED_NOW,
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
                created_at=FIXED_NOW,
                updated_at=FIXED_NOW,
            )
        )

    return (
        workspace_id,
        project_id,
        dataset_id,
        mapping_id,
        user_id,
    )


def build_command(
    *,
    workspace_id: UUID,
    project_id: UUID,
    dataset_id: UUID,
    user_id: UUID,
) -> QueueAnalysisRunCommand:
    return QueueAnalysisRunCommand(
        workspace_id=workspace_id,
        project_id=project_id,
        dataset_id=dataset_id,
        semantic_mapping_version=1,
        created_by_user_id=user_id,
        estimator_type=(AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES),
        estimator_version="did-v1",
        random_seed=1_729,
        configuration_json=(
            '{"alpha":0.05,"analysis_start_date":"2026-01-01",'
            '"analysis_end_date":"2026-01-31","intervention_date":"2026-01-15"}'
        ),
    )


@pytest.mark.asyncio
async def test_queue_analysis_run_persists_execution_job_in_same_transaction(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    (
        workspace_id,
        project_id,
        dataset_id,
        mapping_id,
        user_id,
    ) = await seed_ready_dataset_and_mapping(
        tenancy_session_factory,
    )

    run = await QueueAnalysisRun(
        unit_of_work=SqlAlchemyAnalysisRunUnitOfWork(
            session_factory=tenancy_session_factory,
        ),
        clock=FixedClock(),
        application_version=APPLICATION_VERSION,
        source_revision=SOURCE_REVISION,
        statistical_runtime_versions=StatisticalRuntimeVersionProvider(),
    ).execute(
        build_command(
            workspace_id=workspace_id,
            project_id=project_id,
            dataset_id=dataset_id,
            user_id=user_id,
        )
    )

    async with tenancy_session_factory() as session:
        run_count = await session.scalar(select(func.count()).select_from(AnalysisRunModel))

        execution_job_count = await session.scalar(
            select(func.count()).select_from(AnalysisExecutionJobModel)
        )

        persisted_run = await session.scalar(
            select(AnalysisRunModel).where(
                AnalysisRunModel.id == run.id,
            )
        )

        persisted_job = await session.scalar(
            select(AnalysisExecutionJobModel).where(
                AnalysisExecutionJobModel.analysis_run_id == run.id,
            )
        )

    assert run_count == 1
    assert execution_job_count == 1

    assert persisted_run is not None
    assert persisted_job is not None

    assert persisted_run.workspace_id == workspace_id
    assert persisted_run.project_id == project_id
    assert persisted_run.dataset_id == dataset_id
    assert persisted_run.semantic_mapping_id == mapping_id
    assert persisted_run.status == "queued"

    assert persisted_job.workspace_id == workspace_id
    assert persisted_job.project_id == project_id
    assert persisted_job.analysis_run_id == run.id
    assert persisted_job.status == "pending"
    assert persisted_job.attempt_count == 0
    assert persisted_job.max_attempts == 3
    assert persisted_job.available_at == FIXED_NOW
    assert persisted_job.created_at == FIXED_NOW
    assert persisted_job.claimed_at is None
    assert persisted_job.completed_at is None
    assert persisted_job.last_error is None


@pytest.mark.asyncio
async def test_execution_job_failure_rolls_back_analysis_run_insert(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    (
        workspace_id,
        project_id,
        dataset_id,
        _mapping_id,
        user_id,
    ) = await seed_ready_dataset_and_mapping(
        tenancy_session_factory,
    )

    with pytest.raises(
        RuntimeError,
        match="Execution job persistence failed",
    ):
        await QueueAnalysisRun(
            unit_of_work=FailingExecutionJobUnitOfWork(
                session_factory=tenancy_session_factory,
            ),
            clock=FixedClock(),
            application_version=APPLICATION_VERSION,
            source_revision=SOURCE_REVISION,
            statistical_runtime_versions=StatisticalRuntimeVersionProvider(),
        ).execute(
            build_command(
                workspace_id=workspace_id,
                project_id=project_id,
                dataset_id=dataset_id,
                user_id=user_id,
            )
        )

    async with tenancy_session_factory() as session:
        run_count = await session.scalar(select(func.count()).select_from(AnalysisRunModel))

        execution_job_count = await session.scalar(
            select(func.count()).select_from(AnalysisExecutionJobModel)
        )

    assert run_count == 0
    assert execution_job_count == 0
