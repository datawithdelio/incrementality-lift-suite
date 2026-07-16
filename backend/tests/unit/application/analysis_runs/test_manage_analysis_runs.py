from datetime import UTC, datetime
from types import TracebackType
from uuid import UUID, uuid4

import pytest

from incrementality_api.application.analysis_runs.errors import (
    AnalysisRunDatasetNotReadyError,
    AnalysisRunDatasetUnavailableError,
    AnalysisRunSemanticMappingUnavailableError,
    AnalysisRunUnavailableError,
)
from incrementality_api.application.analysis_runs.manage_analysis_runs import (
    GetAnalysisRun,
    GetAnalysisRunQuery,
    QueueAnalysisRun,
    QueueAnalysisRunCommand,
)
from incrementality_api.domain.analysis_runs.entities import (
    AnalysisRun,
)
from incrementality_api.domain.analysis_runs.execution_job_status import (
    AnalysisExecutionJobStatus,
)
from incrementality_api.domain.analysis_runs.execution_jobs import (
    AnalysisExecutionJob,
)
from incrementality_api.domain.analysis_runs.status import (
    AnalysisEstimatorType,
    AnalysisRunStatus,
)
from incrementality_api.domain.datasets.entities import (
    Dataset,
)
from incrementality_api.domain.datasets.semantic_mapping import (
    DatasetSemanticMapping,
)

CREATED_AT = datetime(
    2026,
    7,
    15,
    16,
    0,
    tzinfo=UTC,
)

UPLOADED_AT = datetime(
    2026,
    7,
    15,
    16,
    1,
    tzinfo=UTC,
)

VALIDATION_STARTED_AT = datetime(
    2026,
    7,
    15,
    16,
    2,
    tzinfo=UTC,
)

VALIDATION_COMPLETED_AT = datetime(
    2026,
    7,
    15,
    16,
    3,
    tzinfo=UTC,
)

MAPPING_CREATED_AT = datetime(
    2026,
    7,
    15,
    16,
    4,
    tzinfo=UTC,
)

RUN_CREATED_AT = datetime(
    2026,
    7,
    15,
    16,
    5,
    tzinfo=UTC,
)


def build_ready_dataset(
    *,
    workspace_id: UUID,
    project_id: UUID,
    user_id: UUID,
) -> Dataset:
    return (
        Dataset.register(
            workspace_id=workspace_id,
            project_id=project_id,
            created_by_user_id=user_id,
            source_filename="analysis-input.csv",
            storage_key=(
                f"workspaces/{workspace_id}/projects/"
                f"{project_id}/datasets/"
                f"{'a' * 64}/analysis-input.csv"
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
            column_count=4,
        )
    )


def build_mapping(
    *,
    dataset_id: UUID,
    user_id: UUID,
    version: int = 3,
) -> DatasetSemanticMapping:
    return DatasetSemanticMapping(
        id=uuid4(),
        dataset_id=dataset_id,
        created_by_user_id=user_id,
        version=version,
        time_column="date",
        unit_column="market",
        treatment_column="treated",
        outcome_column="revenue",
        spend_column=None,
        covariate_columns=(),
        treatment_value="true",
        control_value="false",
        created_at=MAPPING_CREATED_AT,
        updated_at=MAPPING_CREATED_AT,
    )


class FixedClock:
    def now(self) -> datetime:
        return RUN_CREATED_AT


class FakeDatasetRepository:
    def __init__(
        self,
        dataset: Dataset | None,
    ) -> None:
        self._dataset = dataset
        self.received_scope: (
            tuple[
                UUID,
                UUID,
                UUID,
            ]
            | None
        ) = None

    async def get_by_scope(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        dataset_id: UUID,
    ) -> Dataset | None:
        self.received_scope = (
            workspace_id,
            project_id,
            dataset_id,
        )
        return self._dataset


class FakeSemanticMappingRepository:
    def __init__(
        self,
        mapping: DatasetSemanticMapping | None,
    ) -> None:
        self._mapping = mapping
        self.received_scope: (
            tuple[
                UUID,
                UUID,
                UUID,
                int,
            ]
            | None
        ) = None

    async def get_by_scope_and_version(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        dataset_id: UUID,
        version: int,
    ) -> DatasetSemanticMapping | None:
        self.received_scope = (
            workspace_id,
            project_id,
            dataset_id,
            version,
        )
        return self._mapping


class FakeAnalysisRunRepository:
    def __init__(
        self,
        run: AnalysisRun | None = None,
    ) -> None:
        self._run = run
        self.added: list[AnalysisRun] = []
        self.received_scope: (
            tuple[
                UUID,
                UUID,
                UUID,
            ]
            | None
        ) = None

    async def add(
        self,
        run: AnalysisRun,
    ) -> None:
        self.added.append(run)

    async def get_by_scope(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        analysis_run_id: UUID,
    ) -> AnalysisRun | None:
        self.received_scope = (
            workspace_id,
            project_id,
            analysis_run_id,
        )
        return self._run


class FakeExecutionJobRepository:
    def __init__(self) -> None:
        self.added: list[AnalysisExecutionJob] = []

    async def add(
        self,
        job: AnalysisExecutionJob,
    ) -> None:
        self.added.append(job)


class FakeAnalysisRunUnitOfWork:
    def __init__(
        self,
        *,
        dataset: Dataset | None,
        mapping: DatasetSemanticMapping | None,
        run: AnalysisRun | None = None,
    ) -> None:
        self.datasets = FakeDatasetRepository(
            dataset,
        )
        self.semantic_mappings = FakeSemanticMappingRepository(
            mapping,
        )
        self.analysis_runs = FakeAnalysisRunRepository(
            run,
        )
        self.execution_jobs = FakeExecutionJobRepository()
        self.commit_count = 0
        self.entered = False
        self.exited = False

    async def __aenter__(
        self,
    ) -> "FakeAnalysisRunUnitOfWork":
        self.entered = True
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exception_type, exception, traceback
        self.exited = True

    async def commit(self) -> None:
        self.commit_count += 1


def build_command(
    *,
    workspace_id: UUID,
    project_id: UUID,
    dataset_id: UUID,
    user_id: UUID,
    mapping_version: int = 3,
) -> QueueAnalysisRunCommand:
    return QueueAnalysisRunCommand(
        workspace_id=workspace_id,
        project_id=project_id,
        dataset_id=dataset_id,
        semantic_mapping_version=(mapping_version),
        created_by_user_id=user_id,
        estimator_type=(AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES),
        estimator_version="did-v1",
        configuration_json="""
        {
          "include_unit_fixed_effects": true,
          "alpha": 0.05
        }
        """,
    )


@pytest.mark.asyncio
async def test_queues_analysis_run_atomically() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()

    dataset = build_ready_dataset(
        workspace_id=workspace_id,
        project_id=project_id,
        user_id=user_id,
    )

    mapping = build_mapping(
        dataset_id=dataset.id,
        user_id=user_id,
    )

    unit_of_work = FakeAnalysisRunUnitOfWork(
        dataset=dataset,
        mapping=mapping,
    )

    result = await QueueAnalysisRun(
        unit_of_work=unit_of_work,
        clock=FixedClock(),
    ).execute(
        build_command(
            workspace_id=workspace_id,
            project_id=project_id,
            dataset_id=dataset.id,
            user_id=user_id,
        )
    )

    assert result.status is AnalysisRunStatus.QUEUED
    assert result.workspace_id == workspace_id
    assert result.project_id == project_id
    assert result.dataset_id == dataset.id
    assert result.dataset_checksum_sha256 == dataset.checksum_sha256
    assert result.dataset_byte_size == dataset.byte_size

    assert result.semantic_mapping_id == (mapping.id)
    assert result.semantic_mapping_version == 3
    assert result.created_by_user_id == user_id

    assert result.estimator_type is (AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES)
    assert result.estimator_version == "did-v1"

    assert result.configuration_json == ('{"alpha":0.05,"include_unit_fixed_effects":true}')

    assert result.created_at == RUN_CREATED_AT

    assert unit_of_work.datasets.received_scope == (
        workspace_id,
        project_id,
        dataset.id,
    )

    assert (unit_of_work.semantic_mappings.received_scope) == (
        workspace_id,
        project_id,
        dataset.id,
        3,
    )

    assert unit_of_work.analysis_runs.added == [
        result,
    ]

    assert len(unit_of_work.execution_jobs.added) == 1

    execution_job = unit_of_work.execution_jobs.added[0]

    assert execution_job.workspace_id == workspace_id
    assert execution_job.project_id == project_id
    assert execution_job.analysis_run_id == result.id
    assert execution_job.created_at == RUN_CREATED_AT
    assert execution_job.available_at == RUN_CREATED_AT
    assert execution_job.status is AnalysisExecutionJobStatus.PENDING
    assert execution_job.attempt_count == 0
    assert execution_job.max_attempts == 3

    assert unit_of_work.commit_count == 1
    assert unit_of_work.entered
    assert unit_of_work.exited


@pytest.mark.asyncio
async def test_queue_rejects_unavailable_dataset() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    dataset_id = uuid4()
    user_id = uuid4()

    unit_of_work = FakeAnalysisRunUnitOfWork(
        dataset=None,
        mapping=None,
    )

    with pytest.raises(
        AnalysisRunDatasetUnavailableError,
        match="Dataset is unavailable",
    ):
        await QueueAnalysisRun(
            unit_of_work=unit_of_work,
            clock=FixedClock(),
        ).execute(
            build_command(
                workspace_id=workspace_id,
                project_id=project_id,
                dataset_id=dataset_id,
                user_id=user_id,
            )
        )

    assert unit_of_work.analysis_runs.added == []
    assert unit_of_work.execution_jobs.added == []
    assert unit_of_work.commit_count == 0


@pytest.mark.asyncio
async def test_queue_requires_ready_dataset() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()

    dataset = Dataset.register(
        workspace_id=workspace_id,
        project_id=project_id,
        created_by_user_id=user_id,
        source_filename="pending.csv",
        storage_key=(
            f"workspaces/{workspace_id}/projects/{project_id}/datasets/{'b' * 64}/pending.csv"
        ),
        media_type="text/csv",
        byte_size=4_096,
        checksum_sha256="b" * 64,
    )

    unit_of_work = FakeAnalysisRunUnitOfWork(
        dataset=dataset,
        mapping=None,
    )

    with pytest.raises(
        AnalysisRunDatasetNotReadyError,
        match=("Dataset must be ready before analysis"),
    ):
        await QueueAnalysisRun(
            unit_of_work=unit_of_work,
            clock=FixedClock(),
        ).execute(
            build_command(
                workspace_id=workspace_id,
                project_id=project_id,
                dataset_id=dataset.id,
                user_id=user_id,
            )
        )

    assert unit_of_work.semantic_mappings.received_scope is None
    assert unit_of_work.analysis_runs.added == []
    assert unit_of_work.execution_jobs.added == []
    assert unit_of_work.commit_count == 0


@pytest.mark.asyncio
async def test_queue_requires_requested_mapping_version() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()

    dataset = build_ready_dataset(
        workspace_id=workspace_id,
        project_id=project_id,
        user_id=user_id,
    )

    unit_of_work = FakeAnalysisRunUnitOfWork(
        dataset=dataset,
        mapping=None,
    )

    with pytest.raises(
        AnalysisRunSemanticMappingUnavailableError,
        match=("Semantic mapping is unavailable"),
    ):
        await QueueAnalysisRun(
            unit_of_work=unit_of_work,
            clock=FixedClock(),
        ).execute(
            build_command(
                workspace_id=workspace_id,
                project_id=project_id,
                dataset_id=dataset.id,
                user_id=user_id,
                mapping_version=9,
            )
        )

    assert (unit_of_work.semantic_mappings.received_scope) == (
        workspace_id,
        project_id,
        dataset.id,
        9,
    )

    assert unit_of_work.analysis_runs.added == []
    assert unit_of_work.execution_jobs.added == []
    assert unit_of_work.commit_count == 0


@pytest.mark.asyncio
async def test_reads_analysis_run_in_tenant_scope() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()

    dataset = build_ready_dataset(
        workspace_id=workspace_id,
        project_id=project_id,
        user_id=user_id,
    )

    mapping = build_mapping(
        dataset_id=dataset.id,
        user_id=user_id,
    )

    run = AnalysisRun.queue(
        workspace_id=workspace_id,
        project_id=project_id,
        dataset_id=dataset.id,
        dataset_checksum_sha256=dataset.checksum_sha256,
        dataset_byte_size=dataset.byte_size,
        semantic_mapping_id=mapping.id,
        semantic_mapping_version=(mapping.version),
        created_by_user_id=user_id,
        estimator_type=(AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES),
        estimator_version="did-v1",
        configuration_json='{"alpha":0.05}',
        created_at=RUN_CREATED_AT,
    )

    unit_of_work = FakeAnalysisRunUnitOfWork(
        dataset=dataset,
        mapping=mapping,
        run=run,
    )

    result = await GetAnalysisRun(
        unit_of_work=unit_of_work,
    ).execute(
        GetAnalysisRunQuery(
            workspace_id=workspace_id,
            project_id=project_id,
            analysis_run_id=run.id,
        )
    )

    assert result == run

    assert (unit_of_work.analysis_runs.received_scope) == (
        workspace_id,
        project_id,
        run.id,
    )

    assert unit_of_work.commit_count == 0
    assert unit_of_work.entered
    assert unit_of_work.exited


@pytest.mark.asyncio
async def test_read_rejects_unavailable_analysis_run() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    analysis_run_id = uuid4()

    unit_of_work = FakeAnalysisRunUnitOfWork(
        dataset=None,
        mapping=None,
        run=None,
    )

    with pytest.raises(
        AnalysisRunUnavailableError,
        match="Analysis run is unavailable",
    ):
        await GetAnalysisRun(
            unit_of_work=unit_of_work,
        ).execute(
            GetAnalysisRunQuery(
                workspace_id=workspace_id,
                project_id=project_id,
                analysis_run_id=(analysis_run_id),
            )
        )

    assert (unit_of_work.analysis_runs.received_scope) == (
        workspace_id,
        project_id,
        analysis_run_id,
    )

    assert unit_of_work.commit_count == 0
