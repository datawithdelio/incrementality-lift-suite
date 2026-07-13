from dataclasses import dataclass
from uuid import UUID

from incrementality_api.application.authentication.ports import (
    PasswordHasher,
)
from incrementality_api.application.tenancy.ports import (
    TenancyUnitOfWork,
)
from incrementality_api.domain.authentication.entities import (
    PasswordCredential,
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
    owner_password: str


@dataclass(frozen=True, slots=True)
class ProvisionedTenant:
    organization_id: UUID
    workspace_id: UUID
    owner_user_id: UUID
    owner_membership_id: UUID


class ProvisionTenant:
    """Create a tenant and its initial owner atomically."""

    def __init__(
        self,
        *,
        unit_of_work: TenancyUnitOfWork,
        password_hasher: PasswordHasher,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._password_hasher = password_hasher

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

        credential = PasswordCredential.create(
            user_id=owner.id,
            password_hash=self._password_hasher.hash(
                command.owner_password,
            ),
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
            await self._unit_of_work.credentials.add(
                credential,
            )
            await self._unit_of_work.workspaces.add(
                workspace,
            )
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
