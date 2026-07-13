from types import TracebackType

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from incrementality_api.application.authorization.ports import (
    WorkspaceMembershipReader,
)
from incrementality_api.infrastructure.database.repositories.authorization import (
    SqlAlchemyWorkspaceMembershipReader,
)


class SqlAlchemyAuthorizationUnitOfWork:
    """Own one read transaction for workspace authorization."""

    memberships: WorkspaceMembershipReader

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(
        self,
    ) -> "SqlAlchemyAuthorizationUnitOfWork":
        session = self._session_factory()
        self._session = session

        self.memberships = SqlAlchemyWorkspaceMembershipReader(
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

    def _require_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("The authorization Unit of Work must be entered before use.")

        return self._session
