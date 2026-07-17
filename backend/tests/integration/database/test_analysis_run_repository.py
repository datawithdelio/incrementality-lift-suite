from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from incrementality_api.application.analysis_runs.errors import (
    AnalysisRunUnavailableError,
)
from incrementality_api.application.analysis_runs.manage_analysis_runs import (
    GetAnalysisRun,
    GetAnalysisRunQuery,
    QueueAnalysisRun,
    QueueAnalysisRunCommand,
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
from incrementality_api.infrastructure.database.unit_of_work.analysis_runs import (
    SqlAlchemyAnalysisRunUnitOfWork,
)
from incrementality_api.infrastructure.estimation.runtime_versions import (
    StatisticalRuntimeVersionProvider,
)

APPLICATION_VERSION = "0.1.0"
SOURCE_REVISION = "a" * 40

CREATED_AT = datetime(
    2026,
    7,
    15,
    18,
    0,
    tzinfo=UTC,
)

UPDATED_AT = datetime(
    2026,
    7,
    15,
    18,
    1,
    tzinfo=UTC,
)

RUN_CREATED_AT = datetime(
    2026,
    7,
    15,
    18,
    2,
    tzinfo=UTC,
)

RUN_STARTED_AT = datetime(
    2026,
    7,
    15,
    18,
    3,
    tzinfo=UTC,
)


@dataclass(frozen=True, slots=True)
class SeededAnalysisScope:
    workspace_id: UUID
    project_id: UUID
    dataset_id: UUID
    mapping_id: UUID
    mapping_version: int
    user_id: UUID


class FixedClock:
    def now(self) -> datetime:
        return RUN_CREATED_AT


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
                    name="Analysis Repository Organization",
                    slug=f"organization-{organization_id}",
                    created_at=CREATED_AT,
                    updated_at=UPDATED_AT,
                ),
                UserModel(
                    id=user_id,
                    email=f"{user_id}@example.com",
                    display_name="Analysis Repository User",
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
                name="Analysis Repository Workspace",
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
                name="Analysis Repository Project",
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
        mapping_version=1,
        user_id=user_id,
    )


def build_queue_command(
    scope: SeededAnalysisScope,
) -> QueueAnalysisRunCommand:
    return QueueAnalysisRunCommand(
        workspace_id=scope.workspace_id,
        project_id=scope.project_id,
        dataset_id=scope.dataset_id,
        semantic_mapping_version=(scope.mapping_version),
        created_by_user_id=scope.user_id,
        estimator_type=(AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES),
        estimator_version="did-v1",
        random_seed=1_729,
        configuration_json="""
        {
          "cluster_by": "unit",
          "alpha": 0.05
        }
        """,
    )


@pytest.mark.asyncio
async def test_queues_and_reads_analysis_run_in_tenant_scope(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    scope = await seed_analysis_scope(
        tenancy_session_factory,
    )

    queued = await QueueAnalysisRun(
        unit_of_work=SqlAlchemyAnalysisRunUnitOfWork(
            session_factory=tenancy_session_factory,
        ),
        clock=FixedClock(),
        application_version="0.1.0",
        source_revision="a" * 40,
        statistical_runtime_versions=StatisticalRuntimeVersionProvider(),
    ).execute(build_queue_command(scope))

    persisted = await GetAnalysisRun(
        unit_of_work=SqlAlchemyAnalysisRunUnitOfWork(
            session_factory=tenancy_session_factory,
        ),
    ).execute(
        GetAnalysisRunQuery(
            workspace_id=scope.workspace_id,
            project_id=scope.project_id,
            analysis_run_id=queued.id,
        )
    )

    assert persisted == queued
    assert persisted.status is AnalysisRunStatus.QUEUED
    assert persisted.semantic_mapping_id == (scope.mapping_id)
    assert persisted.semantic_mapping_version == 1
    assert persisted.semantic_mapping_snapshot is not None
    assert persisted.semantic_mapping_snapshot.as_dict() == {
        "time_column": "date",
        "unit_column": "market",
        "treatment_column": "treated",
        "outcome_column": "revenue",
        "spend_column": None,
        "covariate_columns": [],
        "treatment_value": "true",
        "control_value": "false",
    }
    assert persisted.application_version == "0.1.0"
    assert persisted.source_revision == "a" * 40
    assert persisted.statistical_library_versions is not None
    assert set(persisted.statistical_library_versions.as_dict()) == {
        "numpy",
        "statsmodels",
    }
    assert persisted.random_seed == 1_729
    assert persisted.input_fingerprint_sha256 == queued.input_fingerprint_sha256
    assert persisted.configuration_json == ('{"alpha":0.05,"cluster_by":"unit"}')

    async with tenancy_session_factory() as session:
        count = await session.scalar(select(func.count()).select_from(AnalysisRunModel))

    assert count == 1


@pytest.mark.asyncio
async def test_persists_analysis_run_lifecycle_update(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    scope = await seed_analysis_scope(
        tenancy_session_factory,
    )

    queued = await QueueAnalysisRun(
        unit_of_work=SqlAlchemyAnalysisRunUnitOfWork(
            session_factory=tenancy_session_factory,
        ),
        clock=FixedClock(),
        application_version=APPLICATION_VERSION,
        source_revision=SOURCE_REVISION,
        statistical_runtime_versions=StatisticalRuntimeVersionProvider(),
    ).execute(build_queue_command(scope))

    unit_of_work = SqlAlchemyAnalysisRunUnitOfWork(
        session_factory=tenancy_session_factory,
    )

    async with unit_of_work:
        loaded = await unit_of_work.analysis_runs.get_by_scope(
            workspace_id=scope.workspace_id,
            project_id=scope.project_id,
            analysis_run_id=queued.id,
        )

        assert loaded is not None

        running = loaded.start(
            started_at=RUN_STARTED_AT,
        )

        await unit_of_work.analysis_runs.update(running)

        await unit_of_work.commit()

    persisted = await GetAnalysisRun(
        unit_of_work=SqlAlchemyAnalysisRunUnitOfWork(
            session_factory=tenancy_session_factory,
        ),
    ).execute(
        GetAnalysisRunQuery(
            workspace_id=scope.workspace_id,
            project_id=scope.project_id,
            analysis_run_id=queued.id,
        )
    )

    assert persisted.status is AnalysisRunStatus.RUNNING
    assert persisted.started_at == RUN_STARTED_AT
    assert persisted.completed_at is None
    assert persisted.statistical_library_versions == queued.statistical_library_versions
    assert persisted.semantic_mapping_snapshot == queued.semantic_mapping_snapshot


@pytest.mark.asyncio
async def test_analysis_run_read_is_rejected_outside_workspace_scope(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    scope = await seed_analysis_scope(
        tenancy_session_factory,
    )

    queued = await QueueAnalysisRun(
        unit_of_work=SqlAlchemyAnalysisRunUnitOfWork(
            session_factory=tenancy_session_factory,
        ),
        clock=FixedClock(),
        application_version=APPLICATION_VERSION,
        source_revision=SOURCE_REVISION,
        statistical_runtime_versions=StatisticalRuntimeVersionProvider(),
    ).execute(build_queue_command(scope))

    with pytest.raises(
        AnalysisRunUnavailableError,
        match="Analysis run is unavailable",
    ):
        await GetAnalysisRun(
            unit_of_work=SqlAlchemyAnalysisRunUnitOfWork(
                session_factory=tenancy_session_factory,
            ),
        ).execute(
            GetAnalysisRunQuery(
                workspace_id=uuid4(),
                project_id=scope.project_id,
                analysis_run_id=queued.id,
            )
        )
