from dataclasses import dataclass
from uuid import UUID

from incrementality_api.application.tenancy.ports import (
    WorkspaceAccessReader,
)


@dataclass(frozen=True, slots=True)
class AccessibleWorkspace:
    workspace_id: UUID
    organization_id: UUID
    name: str
    slug: str
    role: str


class ListUserWorkspaces:
    """Return the workspaces accessible to one authenticated user."""

    def __init__(
        self,
        *,
        reader: WorkspaceAccessReader,
    ) -> None:
        self._reader = reader

    async def execute(
        self,
        *,
        user_id: UUID,
    ) -> list[AccessibleWorkspace]:
        return await self._reader.list_for_user(
            user_id=user_id,
        )
