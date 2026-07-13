from types import TracebackType

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from incrementality_api.application.tenancy.errors import (
    TenancyConflictError,
)
from incrementality_api.application.tenancy.ports import (
    CredentialRepository,
    MembershipRepository,
    OrganizationRepository,
    UserRepository,
    WorkspaceRepository,
)
from incrementality_api.infrastructure.database.repositories.tenancy import (
    SqlAlchemyCredentialRepository,
    SqlAlchemyMembershipRepository,
    SqlAlchemyOrganizationRepository,
    SqlAlchemyUserRepository,
    SqlAlchemyWorkspaceRepository,
)


class SqlAlchemyTenancyUnitOfWork:
    """Own one SQLAlchemy session and transaction."""

    organizations: OrganizationRepository
    users: UserRepository
    credentials: CredentialRepository
    workspaces: WorkspaceRepository
    memberships: MembershipRepository

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(
        self,
    ) -> "SqlAlchemyTenancyUnitOfWork":
        session = self._session_factory()
        self._session = session

        self.organizations = SqlAlchemyOrganizationRepository(
            session=session,
        )
        self.users = SqlAlchemyUserRepository(
            session=session,
        )
        self.credentials = SqlAlchemyCredentialRepository(
            session=session,
        )
        self.workspaces = SqlAlchemyWorkspaceRepository(
            session=session,
        )
        self.memberships = SqlAlchemyMembershipRepository(
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

            raise TenancyConflictError("Tenant data conflicts with an existing record.") from error

    async def rollback(self) -> None:
        session = self._require_session()
        await session.rollback()

    def _require_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("The Unit of Work must be entered before use.")

        return self._session
