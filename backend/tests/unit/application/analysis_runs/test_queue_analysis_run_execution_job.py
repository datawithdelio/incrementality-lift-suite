from dataclasses import dataclass
from datetime import UTC, datetime
from types import TracebackType
from uuid import UUID, uuid4

import pytest

from incrementality_api.application.analysis_runs.manage_analysis_runs import (
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
)
from incrementality_api.domain.datasets.status import (
    DatasetStatus,
)

NOW = datetime(
    2026,
    7,
    16,
    18,
    0,
    tzinfo=UTC,
)


@dataclass(frozen=True, slots=True)
class StubDataset:
    status: DatasetStatus


@dataclass(frozen=True, slots=True)
class StubSemanticMapping:
    id: UUID
    version: int


class FixedClock:
    def __init__(self) -> None:
        self.call_count = 0

    def now(self) -> datetime:
        self.call_count += 1
        return NOW


class StubDatasetRepository:
    def __init__(
        self,
        dataset: StubDataset | None,
    ) -> None:
        self._dataset = dataset

    async def get_by_scope(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        dataset_id: UUID,
    ) -> StubDataset | None:
        del workspace_id
        del project_id
        del dataset_id

        return self._dataset


class StubSemanticMappingRepository:
    def __init__(
        self,
        mapping: StubSemanticMapping | None,
    ) -> None:
        self._mapping = mapping

    async def get_by_scope_and_version(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        dataset_id: UUID,
        version: int,
    ) -> StubSemanticMapping | None:
        del workspace_id
        del project_id
        del dataset_id
        del version

        return self._mapping


class RecordingAnalysisRunRepository:
    def __init__(self) -> None:
        self.added: list[AnalysisRun] = []

    async def add(
        self,
        run: AnalysisRun,
    ) -> None:
        self.added.append(run)


class RecordingExecutionJobRepository:
    def __init__(
        self,
        *,
        add_error: Exception | None = None,
    ) -> None:
        self._add_error = add_error
        self.added: list[AnalysisExecutionJob] = []

    async def add(
        self,
        job: AnalysisExecutionJob,
    ) -> None:
        if self._add_error is not None:
            raise self._add_error

        self.added.append(job)


class FakeAnalysisRunUnitOfWork:
    def __init__(
        self,
        *,
        execution_job_add_error: Exception | None = None,
    ) -> None:
        self.datasets = StubDatasetRepository(
            StubDataset(
                status=DatasetStatus.READY,
            )
        )

        self.semantic_mappings = StubSemanticMappingRepository(
            StubSemanticMapping(
                id=uuid4(),
                version=3,
            )
        )

        self.analysis_runs = RecordingAnalysisRunRepository()

        self.execution_jobs = RecordingExecutionJobRepository(
            add_error=execution_job_add_error,
        )

        self.enter_count = 0
        self.commit_count = 0
        self.exit_exception_type: type[BaseException] | None = None

    async def __aenter__(
        self,
    ) -> "FakeAnalysisRunUnitOfWork":
        self.enter_count += 1
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exception
        del traceback

        self.exit_exception_type = exception_type

    async def commit(self) -> None:
        self.commit_count += 1


def build_command() -> QueueAnalysisRunCommand:
    return QueueAnalysisRunCommand(
        workspace_id=uuid4(),
        project_id=uuid4(),
        dataset_id=uuid4(),
        semantic_mapping_version=3,
        created_by_user_id=uuid4(),
        estimator_type=AnalysisEstimatorType("difference_in_differences"),
        estimator_version="did-v1",
        configuration_json=('{"alpha":0.05}'),
    )


@pytest.mark.asyncio
async def test_queues_run_and_execution_job_atomically() -> None:
    unit_of_work = FakeAnalysisRunUnitOfWork()
    clock = FixedClock()
    command = build_command()

    run = await QueueAnalysisRun(
        unit_of_work=unit_of_work,
        clock=clock,
    ).execute(command)

    assert unit_of_work.analysis_runs.added == [run]

    assert len(unit_of_work.execution_jobs.added) == 1

    job = unit_of_work.execution_jobs.added[0]

    assert job.workspace_id == command.workspace_id
    assert job.project_id == command.project_id
    assert job.analysis_run_id == run.id
    assert job.created_at == NOW
    assert job.available_at == NOW
    assert job.status is (AnalysisExecutionJobStatus.PENDING)
    assert job.attempt_count == 0
    assert job.max_attempts == 3

    assert clock.call_count == 1
    assert unit_of_work.commit_count == 1
    assert unit_of_work.exit_exception_type is None


@pytest.mark.asyncio
async def test_execution_job_failure_prevents_commit() -> None:
    expected_error = RuntimeError("Execution job persistence failed.")

    unit_of_work = FakeAnalysisRunUnitOfWork(
        execution_job_add_error=expected_error,
    )

    with pytest.raises(
        RuntimeError,
        match=("Execution job persistence failed"),
    ):
        await QueueAnalysisRun(
            unit_of_work=unit_of_work,
            clock=FixedClock(),
        ).execute(build_command())

    assert len(unit_of_work.analysis_runs.added) == 1

    assert unit_of_work.execution_jobs.added == []

    assert unit_of_work.commit_count == 0
    assert unit_of_work.exit_exception_type is RuntimeError
