from types import TracebackType

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from incrementality_api.application.jobs.ports import (
    DatasetValidationJobRepository,
)
from incrementality_api.infrastructure.database.repositories.jobs import (
    SqlAlchemyDatasetValidationJobRepository,
)


class SqlAlchemyDatasetValidationJobUnitOfWork:
    """Own one durable validation-job transaction."""

    validation_jobs: DatasetValidationJobRepository

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(
        self,
    ) -> "SqlAlchemyDatasetValidationJobUnitOfWork":
        session = self._session_factory()
        self._session = session

        self.validation_jobs = SqlAlchemyDatasetValidationJobRepository(
            session=session,
        )

        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exception, traceback

        session = self._require_session()

        try:
            if exception_type is not None:
                await session.rollback()
        finally:
            await session.close()
            self._session = None

    async def commit(self) -> None:
        session = self._require_session()
        await session.commit()

    async def rollback(self) -> None:
        session = self._require_session()
        await session.rollback()

    def _require_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("The validation-job Unit of Work must be entered before use.")

        return self._session
