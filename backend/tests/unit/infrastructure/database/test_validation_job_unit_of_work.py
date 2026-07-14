from typing import cast

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from incrementality_api.infrastructure.database.repositories.jobs import (
    SqlAlchemyDatasetValidationJobRepository,
)
from incrementality_api.infrastructure.database.unit_of_work.jobs import (
    SqlAlchemyDatasetValidationJobUnitOfWork,
)


class FakeAsyncSession:
    def __init__(
        self,
        *,
        commit_error: Exception | None = None,
    ) -> None:
        self._commit_error = commit_error
        self.commit_count = 0
        self.rollback_count = 0
        self.close_count = 0

    async def commit(self) -> None:
        self.commit_count += 1

        if self._commit_error is not None:
            raise self._commit_error

    async def rollback(self) -> None:
        self.rollback_count += 1

    async def close(self) -> None:
        self.close_count += 1


class FakeSessionFactory:
    def __init__(
        self,
        session: FakeAsyncSession,
    ) -> None:
        self._session = session
        self.call_count = 0

    def __call__(self) -> AsyncSession:
        self.call_count += 1

        return cast(
            AsyncSession,
            self._session,
        )


def build_unit_of_work(
    session: FakeAsyncSession,
) -> SqlAlchemyDatasetValidationJobUnitOfWork:
    factory = FakeSessionFactory(session)

    return SqlAlchemyDatasetValidationJobUnitOfWork(
        session_factory=cast(
            async_sessionmaker[AsyncSession],
            factory,
        ),
    )


@pytest.mark.asyncio
async def test_enters_with_validation_job_repository() -> None:
    session = FakeAsyncSession()
    unit_of_work = build_unit_of_work(session)

    async with unit_of_work as entered:
        assert entered is unit_of_work
        assert isinstance(
            unit_of_work.validation_jobs,
            SqlAlchemyDatasetValidationJobRepository,
        )

        await unit_of_work.commit()

    assert session.commit_count == 1
    assert session.rollback_count == 0
    assert session.close_count == 1


@pytest.mark.asyncio
async def test_exception_rolls_back_and_closes_session() -> None:
    session = FakeAsyncSession()
    unit_of_work = build_unit_of_work(session)

    class ExpectedError(Exception):
        pass

    with pytest.raises(ExpectedError):
        async with unit_of_work:
            raise ExpectedError

    assert session.commit_count == 0
    assert session.rollback_count == 1
    assert session.close_count == 1


@pytest.mark.asyncio
async def test_explicit_rollback_uses_active_session() -> None:
    session = FakeAsyncSession()
    unit_of_work = build_unit_of_work(session)

    async with unit_of_work:
        await unit_of_work.rollback()

    assert session.rollback_count == 1
    assert session.close_count == 1


@pytest.mark.asyncio
async def test_commit_failure_is_rolled_back_by_exit() -> None:
    session = FakeAsyncSession(
        commit_error=RuntimeError(
            "Database commit failed.",
        )
    )
    unit_of_work = build_unit_of_work(session)

    with pytest.raises(
        RuntimeError,
        match="Database commit failed",
    ):
        async with unit_of_work:
            await unit_of_work.commit()

    assert session.commit_count == 1
    assert session.rollback_count == 1
    assert session.close_count == 1


@pytest.mark.asyncio
async def test_cannot_commit_before_entering() -> None:
    unit_of_work = build_unit_of_work(
        FakeAsyncSession(),
    )

    with pytest.raises(
        RuntimeError,
        match=("validation-job Unit of Work must be entered before use"),
    ):
        await unit_of_work.commit()
