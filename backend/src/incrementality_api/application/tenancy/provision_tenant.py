from dataclasses import dataclass
from uuid import UUID

from incrementality_api.application.tenancy.ports import (
    TenancyUnitOfWork,
)
from incrementality_api.domain.tenancy.entities import (
    Organization,
    User,
    Workspace,
    WorkspaceMembership,
)
from incrementality_api.domain.tenancy.roles import WorkspaceRole


@dataclass(frozen=True, slots=True)
class ProvisionTenantCommand:
    organization_name: str
    organization_slug: str
    workspace_name: str
    workspace_slug: str
    owner_email: str
    owner_display_name: str


@dataclass(frozen=True, slots=True)
class ProvisionedTenant:
    organization_id: UUID
    workspace_id: UUID
    owner_user_id: UUID
    owner_membership_id: UUID


class ProvisionTenant:
    """Create the initial records required for a new tenant."""

    def __init__(self, unit_of_work: TenancyUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: ProvisionTenantCommand,
    ) -> ProvisionedTenant:
        organization = Organization.create(
            name=command.organization_name,
            slug=command.organization_slug,
        )

        owner = User.create(
            email=command.owner_email,
            display_name=command.owner_display_name,
        )

        workspace = Workspace.create(
            organization_id=organization.id,
            name=command.workspace_name,
            slug=command.workspace_slug,
        )

        membership = WorkspaceMembership.create(
            workspace_id=workspace.id,
            user_id=owner.id,
            role=WorkspaceRole.OWNER,
        )

        async with self._unit_of_work:
            await self._unit_of_work.organizations.add(
                organization,
            )
            await self._unit_of_work.users.add(owner)
            await self._unit_of_work.workspaces.add(workspace)
            await self._unit_of_work.memberships.add(
                membership,
            )

            await self._unit_of_work.commit()

        return ProvisionedTenant(
            organization_id=organization.id,
            workspace_id=workspace.id,
            owner_user_id=owner.id,
            owner_membership_id=membership.id,
        )
