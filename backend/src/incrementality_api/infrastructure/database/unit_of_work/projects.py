from types import TracebackType

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from incrementality_api.application.projects.errors import (
    DuplicateProjectSlugError,
)
from incrementality_api.application.projects.ports import (
    ProjectRepository,
)
from incrementality_api.infrastructure.database.repositories.projects import (
    SqlAlchemyProjectRepository,
)


class SqlAlchemyProjectUnitOfWork:
    """Own one SQLAlchemy project transaction."""

    projects: ProjectRepository

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(
        self,
    ) -> "SqlAlchemyProjectUnitOfWork":
        session = self._session_factory()
        self._session = session

        self.projects = SqlAlchemyProjectRepository(
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

        try:
            await session.commit()
        except IntegrityError as error:
            await session.rollback()

            raise DuplicateProjectSlugError(
                "A project with this slug already exists in the workspace."
            ) from error

    async def rollback(self) -> None:
        session = self._require_session()
        await session.rollback()

    def _require_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("The project Unit of Work must be entered before use.")

        return self._session
