import re
from dataclasses import dataclass
from uuid import UUID

from incrementality_api.application.tenancy.ports import (
    TenancyUnitOfWork,
)
from incrementality_api.domain.tenancy.entities import (
    Organization,
    Workspace,
    WorkspaceMembership,
)
from incrementality_api.domain.tenancy.roles import (
    WorkspaceRole,
)


def _slugify(value: str, *, fallback: str) -> str:
    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        value.strip().lower(),
    ).strip("-")

    return slug or fallback


@dataclass(frozen=True, slots=True)
class CreateWorkspaceCommand:
    user_id: UUID
    organization_name: str
    workspace_name: str


@dataclass(frozen=True, slots=True)
class CreatedWorkspace:
    organization_id: UUID
    workspace_id: UUID
    membership_id: UUID


class CreateWorkspace:
    """Create an organization and workspace for an existing user."""

    def __init__(
        self,
        *,
        unit_of_work: TenancyUnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: CreateWorkspaceCommand,
    ) -> CreatedWorkspace:
        organization = Organization.create(
            name=command.organization_name,
            slug=_slugify(
                command.organization_name,
                fallback="organization",
            ),
        )

        workspace = Workspace.create(
            organization_id=organization.id,
            name=command.workspace_name,
            slug=_slugify(
                command.workspace_name,
                fallback="workspace",
            ),
        )

        membership = WorkspaceMembership.create(
            workspace_id=workspace.id,
            user_id=command.user_id,
            role=WorkspaceRole.OWNER,
        )

        async with self._unit_of_work:
            await self._unit_of_work.organizations.add(
                organization,
            )
            await self._unit_of_work.workspaces.add(
                workspace,
            )
            await self._unit_of_work.memberships.add(
                membership,
            )
            await self._unit_of_work.commit()

        return CreatedWorkspace(
            organization_id=organization.id,
            workspace_id=workspace.id,
            membership_id=membership.id,
        )
