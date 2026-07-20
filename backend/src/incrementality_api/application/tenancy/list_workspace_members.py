from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from incrementality_api.application.tenancy.ports import (
    WorkspaceMemberReader,
)


@dataclass(frozen=True, slots=True)
class WorkspaceMember:
    display_name: str
    email: str
    role: str
    joined_at: datetime


class ListWorkspaceMembers:
    """List safe member details for one authorized workspace."""

    def __init__(
        self,
        *,
        reader: WorkspaceMemberReader,
    ) -> None:
        self._reader = reader

    async def execute(
        self,
        *,
        workspace_id: UUID,
    ) -> list[WorkspaceMember]:
        return await self._reader.list_for_workspace(
            workspace_id=workspace_id,
        )
