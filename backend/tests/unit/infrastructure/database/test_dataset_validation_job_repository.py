from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from incrementality_api.domain.jobs.entities import (
    DatasetValidationJob,
)
from incrementality_api.infrastructure.database.models.jobs import (
    DatasetValidationJobModel,
)
from incrementality_api.infrastructure.database.repositories.jobs import (
    SqlAlchemyDatasetValidationJobRepository,
    to_dataset_validation_job_model,
)

CREATED_AT = datetime(
    2026,
    7,
    15,
    10,
    0,
    tzinfo=UTC,
)

AVAILABLE_AT = datetime(
    2026,
    7,
    15,
    10,
    1,
    tzinfo=UTC,
)

CLAIMED_AT = datetime(
    2026,
    7,
    15,
    10,
    2,
    tzinfo=UTC,
)


class FakeAsyncSession:
    def __init__(
        self,
        scalar_result: DatasetValidationJobModel | None = None,
    ) -> None:
        self.scalar_result = scalar_result
        self.added_models: list[object] = []
        self.scalar_statements: list[object] = []
        self.execute_statements: list[object] = []
        self.flush_count = 0

    def add(
        self,
        model: object,
    ) -> None:
        self.added_models.append(model)

    async def scalar(
        self,
        statement: object,
    ) -> DatasetValidationJobModel | None:
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


def build_pending_job() -> DatasetValidationJob:
    return DatasetValidationJob.enqueue(
        workspace_id=uuid4(),
        project_id=uuid4(),
        dataset_id=uuid4(),
        created_at=CREATED_AT,
        available_at=AVAILABLE_AT,
        max_attempts=3,
    )


def build_repository(
    session: FakeAsyncSession,
) -> SqlAlchemyDatasetValidationJobRepository:
    return SqlAlchemyDatasetValidationJobRepository(
        session=cast(
            AsyncSession,
            session,
        ),
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


@pytest.mark.asyncio
async def test_adds_validation_job_model() -> None:
    job = build_pending_job()
    session = FakeAsyncSession()

    await build_repository(session).add(job)

    assert len(session.added_models) == 1

    model = session.added_models[0]

    assert isinstance(
        model,
        DatasetValidationJobModel,
    )
    assert model.id == job.id
    assert model.dataset_id == job.dataset_id
    assert model.status == "pending"
    assert session.flush_count == 1


@pytest.mark.asyncio
async def test_gets_validation_job_by_id() -> None:
    job = build_pending_job()
    model = to_dataset_validation_job_model(job)
    session = FakeAsyncSession(model)

    result = await build_repository(session).get_by_id(
        job.id,
    )

    assert result == job
    assert len(session.scalar_statements) == 1

    sql = compile_postgresql(
        session.scalar_statements[0],
    )

    assert "dataset_validation_jobs.id" in sql
    assert str(job.id) in sql


@pytest.mark.asyncio
async def test_gets_validation_job_by_dataset_id() -> None:
    job = build_pending_job()
    model = to_dataset_validation_job_model(job)
    session = FakeAsyncSession(model)

    result = await build_repository(session).get_by_dataset_id(
        job.dataset_id,
    )

    assert result == job

    sql = compile_postgresql(
        session.scalar_statements[0],
    )

    assert "dataset_validation_jobs.dataset_id" in sql
    assert str(job.dataset_id) in sql


@pytest.mark.asyncio
async def test_claim_query_uses_skip_locked() -> None:
    job = build_pending_job()
    model = to_dataset_validation_job_model(job)
    session = FakeAsyncSession(model)

    result = await build_repository(session).get_next_available_for_update(
        available_at=CLAIMED_AT,
    )

    assert result == job

    sql = compile_postgresql(
        session.scalar_statements[0],
    ).upper()

    assert "FOR UPDATE SKIP LOCKED" in sql
    assert "STATUS = 'PENDING'" in sql
    assert "AVAILABLE_AT <=" in sql
    assert "ATTEMPT_COUNT <" in sql
    assert "ORDER BY" in sql
    assert "LIMIT 1" in sql


@pytest.mark.asyncio
async def test_updates_validation_job_lifecycle() -> None:
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

    assert "UPDATE DATASET_VALIDATION_JOBS" in sql
    assert any(value == "running" for value in parameters.values())
    assert any(value == job.id for value in parameters.values())
