from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from incrementality_api.application.tenancy.errors import (
    TenancyConflictError,
)
from incrementality_api.domain.tenancy.entities import (
    Organization,
    User,
    Workspace,
    WorkspaceMembership,
)
from incrementality_api.infrastructure.database.repositories.tenancy_mappers import (
    to_membership_model,
    to_organization_model,
    to_user_model,
    to_workspace_model,
)


async def add_and_flush(
    session: AsyncSession,
    model: object,
) -> None:
    """
    Add one model and flush it inside the current transaction.

    Flushing establishes database dependency order without committing.
    A later rollback still removes every record created in the transaction.
    """

    session.add(model)

    try:
        await session.flush()
    except IntegrityError as error:
        await session.rollback()

        raise TenancyConflictError("Tenant data conflicts with an existing record.") from error


class SqlAlchemyOrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, organization: Organization) -> None:
        await add_and_flush(
            self._session,
            to_organization_model(organization),
        )


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> None:
        await add_and_flush(
            self._session,
            to_user_model(user),
        )


class SqlAlchemyWorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, workspace: Workspace) -> None:
        await add_and_flush(
            self._session,
            to_workspace_model(workspace),
        )


class SqlAlchemyMembershipRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        membership: WorkspaceMembership,
    ) -> None:
        await add_and_flush(
            self._session,
            to_membership_model(membership),
        )
