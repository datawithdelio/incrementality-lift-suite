from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from incrementality_api.domain.tenancy.entities import (
    WorkspaceMembership,
)
from incrementality_api.domain.tenancy.roles import WorkspaceRole
from incrementality_api.infrastructure.database.models.tenancy import (
    WorkspaceMembershipModel,
)


class SqlAlchemyWorkspaceMembershipReader:
    """Read workspace membership information from PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_workspace_and_user(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
    ) -> WorkspaceMembership | None:
        statement = select(WorkspaceMembershipModel).where(
            WorkspaceMembershipModel.workspace_id == workspace_id,
            WorkspaceMembershipModel.user_id == user_id,
        )

        model = await self._session.scalar(statement)

        if model is None:
            return None

        return WorkspaceMembership(
            id=model.id,
            workspace_id=model.workspace_id,
            user_id=model.user_id,
            role=WorkspaceRole(model.role),
            created_at=model.created_at,
        )
