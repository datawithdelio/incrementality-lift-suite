from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from incrementality_api.domain.analysis_runs.execution_job_status import (
    AnalysisExecutionJobStatus,
)
from incrementality_api.domain.analysis_runs.execution_jobs import (
    AnalysisExecutionJob,
)
from incrementality_api.infrastructure.database.models.analysis_execution_jobs import (
    AnalysisExecutionJobModel,
)
from incrementality_api.infrastructure.database.repositories.analysis_execution_jobs import (
    SqlAlchemyAnalysisExecutionJobRepository,
    to_analysis_execution_job_entity,
    to_analysis_execution_job_model,
)

CREATED_AT = datetime(
    2026,
    7,
    16,
    14,
    0,
    tzinfo=UTC,
)

AVAILABLE_AT = datetime(
    2026,
    7,
    16,
    14,
    1,
    tzinfo=UTC,
)

CLAIMED_AT = datetime(
    2026,
    7,
    16,
    14,
    2,
    tzinfo=UTC,
)

FAILED_AT = datetime(
    2026,
    7,
    16,
    14,
    3,
    tzinfo=UTC,
)

COMPLETED_AT = datetime(
    2026,
    7,
    16,
    14,
    4,
    tzinfo=UTC,
)


def build_pending_job() -> AnalysisExecutionJob:
    return AnalysisExecutionJob.enqueue(
        workspace_id=uuid4(),
        project_id=uuid4(),
        analysis_run_id=uuid4(),
        created_at=CREATED_AT,
        available_at=AVAILABLE_AT,
        max_attempts=3,
    )


def compile_postgresql(
    statement: object,
) -> str:
    return str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={
                "literal_binds": True,
            },
        )
    )


class FakeAsyncSession:
    def __init__(
        self,
        scalar_result: AnalysisExecutionJobModel | None = None,
    ) -> None:
        self.scalar_result = scalar_result
        self.added_models: list[object] = []
        self.scalar_statements: list[object] = []
        self.execute_statements: list[object] = []
        self.flush_count = 0
        self.rollback_count = 0

    def add(
        self,
        model: object,
    ) -> None:
        self.added_models.append(model)

    async def scalar(
        self,
        statement: object,
    ) -> AnalysisExecutionJobModel | None:
        self.scalar_statements.append(statement)
        return self.scalar_result

    async def execute(
        self,
        statement: object,
    ) -> object:
        self.execute_statements.append(statement)
        return object()

    async def flush(self) -> None:
        self.flush_count += 1

    async def rollback(self) -> None:
        self.rollback_count += 1


def build_repository(
    session: FakeAsyncSession,
) -> SqlAlchemyAnalysisExecutionJobRepository:
    return SqlAlchemyAnalysisExecutionJobRepository(
        session=cast(
            AsyncSession,
            session,
        ),
    )


def round_trip(
    job: AnalysisExecutionJob,
) -> AnalysisExecutionJob:
    model = to_analysis_execution_job_model(job)

    assert model.id == job.id
    assert model.workspace_id == job.workspace_id
    assert model.project_id == job.project_id
    assert model.analysis_run_id == (job.analysis_run_id)
    assert model.status == job.status.value
    assert model.attempt_count == (job.attempt_count)
    assert model.max_attempts == job.max_attempts
    assert model.available_at == job.available_at
    assert model.claimed_at == job.claimed_at
    assert model.completed_at == job.completed_at
    assert model.last_error == job.last_error
    assert model.created_at == job.created_at

    return to_analysis_execution_job_entity(model)


def test_round_trips_pending_job() -> None:
    job = build_pending_job()

    result = round_trip(job)

    assert result == job
    assert result.status is (AnalysisExecutionJobStatus.PENDING)


def test_round_trips_running_job() -> None:
    job = build_pending_job().claim(
        claimed_at=CLAIMED_AT,
    )

    result = round_trip(job)

    assert result == job
    assert result.status is (AnalysisExecutionJobStatus.RUNNING)
    assert result.attempt_count == 1


def test_round_trips_retry_pending_job() -> None:
    job = (
        build_pending_job()
        .claim(
            claimed_at=CLAIMED_AT,
        )
        .retry(
            failed_at=FAILED_AT,
            available_at=(FAILED_AT + timedelta(minutes=1)),
            error=("Estimator dependency temporarily unavailable."),
        )
    )

    result = round_trip(job)

    assert result == job
    assert result.status is (AnalysisExecutionJobStatus.PENDING)
    assert result.attempt_count == 1
    assert result.last_error is not None


def test_round_trips_succeeded_job() -> None:
    job = (
        build_pending_job()
        .claim(
            claimed_at=CLAIMED_AT,
        )
        .mark_succeeded(
            completed_at=COMPLETED_AT,
        )
    )

    result = round_trip(job)

    assert result == job
    assert result.status is (AnalysisExecutionJobStatus.SUCCEEDED)


def test_round_trips_dead_letter_job() -> None:
    job = (
        build_pending_job()
        .claim(
            claimed_at=CLAIMED_AT,
        )
        .mark_dead_letter(
            completed_at=COMPLETED_AT,
            error=("Estimator dependency remained unavailable."),
        )
    )

    result = round_trip(job)

    assert result == job
    assert result.status is (AnalysisExecutionJobStatus.DEAD_LETTER)


@pytest.mark.asyncio
async def test_adds_execution_job_model() -> None:
    job = build_pending_job()
    session = FakeAsyncSession()

    await build_repository(session).add(job)

    assert len(session.added_models) == 1

    model = session.added_models[0]

    assert isinstance(
        model,
        AnalysisExecutionJobModel,
    )
    assert model.id == job.id
    assert model.analysis_run_id == (job.analysis_run_id)
    assert model.status == "pending"
    assert session.flush_count == 1


@pytest.mark.asyncio
async def test_gets_execution_job_by_id() -> None:
    job = build_pending_job()
    model = to_analysis_execution_job_model(job)
    session = FakeAsyncSession(model)

    result = await build_repository(session).get_by_id(job.id)

    assert result == job

    sql = compile_postgresql(session.scalar_statements[0])

    assert "analysis_execution_jobs.id" in sql
    assert str(job.id) in sql


@pytest.mark.asyncio
async def test_gets_job_by_analysis_run_id() -> None:
    job = build_pending_job()
    model = to_analysis_execution_job_model(job)
    session = FakeAsyncSession(model)

    result = await build_repository(session).get_by_analysis_run_id(job.analysis_run_id)

    assert result == job

    sql = compile_postgresql(session.scalar_statements[0])

    assert "analysis_execution_jobs.analysis_run_id" in sql
    assert str(job.analysis_run_id) in sql


@pytest.mark.asyncio
async def test_claim_query_uses_skip_locked() -> None:
    job = build_pending_job()
    model = to_analysis_execution_job_model(job)
    session = FakeAsyncSession(model)

    result = await build_repository(session).get_next_available_for_update(
        available_at=CLAIMED_AT,
    )

    assert result == job

    sql = compile_postgresql(session.scalar_statements[0]).upper()

    assert "FOR UPDATE SKIP LOCKED" in sql
    assert "STATUS = 'PENDING'" in sql
    assert "AVAILABLE_AT <=" in sql
    assert "ATTEMPT_COUNT <" in sql
    assert "ORDER BY" in sql
    assert "LIMIT 1" in sql


@pytest.mark.asyncio
async def test_updates_execution_job_lifecycle() -> None:
    job = build_pending_job().claim(
        claimed_at=CLAIMED_AT,
    )

    session = FakeAsyncSession()

    await build_repository(session).update(job)

    assert len(session.execute_statements) == 1
    assert session.flush_count == 1

    statement = session.execute_statements[0]
    sql = compile_postgresql(statement).upper()
    parameters = statement.compile().params

    assert "UPDATE ANALYSIS_EXECUTION_JOBS" in sql
    assert any(value == "running" for value in parameters.values())
    assert any(value == job.id for value in parameters.values())


@pytest.mark.asyncio
async def test_get_by_id_for_update_locks_job() -> None:
    job = build_pending_job()
    model = to_analysis_execution_job_model(job)
    session = FakeAsyncSession(model)

    result = await build_repository(session).get_by_id_for_update(job.id)

    assert result == job

    sql = compile_postgresql(session.scalar_statements[0]).upper()

    assert "ANALYSIS_EXECUTION_JOBS.ID" in sql
    assert "FOR UPDATE" in sql
    assert "SKIP LOCKED" not in sql


@pytest.mark.asyncio
async def test_stale_running_query_uses_skip_locked() -> None:
    running = build_pending_job().claim(
        claimed_at=CLAIMED_AT,
    )

    model = to_analysis_execution_job_model(running)
    session = FakeAsyncSession(model)

    result = await build_repository(session).get_stale_running_for_update(
        claimed_before=CLAIMED_AT,
    )

    assert result == running

    sql = compile_postgresql(session.scalar_statements[0]).upper()

    assert "STATUS = 'RUNNING'" in sql
    assert "CLAIMED_AT <=" in sql
    assert "ORDER BY" in sql
    assert "LIMIT 1" in sql
    assert "FOR UPDATE SKIP LOCKED" in sql
