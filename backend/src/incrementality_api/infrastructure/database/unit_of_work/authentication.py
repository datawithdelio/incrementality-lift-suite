from types import TracebackType

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from incrementality_api.application.authentication.ports import (
    AuthSessionRepository,
    CredentialRepository,
    LoginUserRepository,
)
from incrementality_api.infrastructure.database.repositories.authentication import (
    SqlAlchemyAuthSessionRepository,
    SqlAlchemyCredentialRepository,
    SqlAlchemyLoginUserRepository,
)


class SqlAlchemyAuthenticationUnitOfWork:
    """Own one authentication transaction and its repositories."""

    users: LoginUserRepository
    credentials: CredentialRepository
    sessions: AuthSessionRepository

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(
        self,
    ) -> "SqlAlchemyAuthenticationUnitOfWork":
        session = self._session_factory()
        self._session = session

        self.users = SqlAlchemyLoginUserRepository(session)
        self.credentials = SqlAlchemyCredentialRepository(
            session,
        )
        self.sessions = SqlAlchemyAuthSessionRepository(
            session,
        )

        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exception, traceback

        try:
            if exception_type is not None:
                await self.rollback()
        finally:
            if self._session is not None:
                await self._session.close()
                self._session = None

    async def commit(self) -> None:
        session = self._require_session()
        await session.commit()

    async def rollback(self) -> None:
        session = self._require_session()
        await session.rollback()

    def _require_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("Authentication Unit of Work is not active.")

        return self._session
