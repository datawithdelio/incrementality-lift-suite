from types import TracebackType

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from incrementality_api.application.analysis_execution.ports import (
    AnalysisExecutionJobRepository,
    AnalysisExecutionRunRepository,
    AnalysisResultRepository,
)
from incrementality_api.infrastructure.database.repositories.analysis_execution_jobs import (
    SqlAlchemyAnalysisExecutionJobRepository,
)
from incrementality_api.infrastructure.database.repositories.analysis_results import (
    SqlAlchemyAnalysisResultRepository,
)
from incrementality_api.infrastructure.database.repositories.analysis_runs import (
    SqlAlchemyAnalysisRunRepository,
)


class SqlAlchemyAnalysisExecutionJobUnitOfWork:
    """Own one durable analysis-execution-job transaction."""

    execution_jobs: AnalysisExecutionJobRepository
    analysis_runs: AnalysisExecutionRunRepository
    analysis_results: AnalysisResultRepository

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(
        self,
    ) -> "SqlAlchemyAnalysisExecutionJobUnitOfWork":
        session = self._session_factory()
        self._session = session

        self.execution_jobs = SqlAlchemyAnalysisExecutionJobRepository(
            session=session,
        )
        self.analysis_runs = SqlAlchemyAnalysisRunRepository(
            session=session,
        )
        self.analysis_results = SqlAlchemyAnalysisResultRepository(session=session)

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
            raise RuntimeError(
                "The analysis-execution-job Unit of Work must be entered before use."
            )

        return self._session
