from types import TracebackType

import pytest

from incrementality_api.application.tenancy.provision_tenant import (
    ProvisionTenant,
    ProvisionTenantCommand,
)
from incrementality_api.domain.tenancy.entities import (
    Organization,
    User,
    Workspace,
    WorkspaceMembership,
)
from incrementality_api.domain.tenancy.roles import WorkspaceRole


class FakeOrganizationRepository:
    def __init__(self) -> None:
        self.saved: list[Organization] = []

    async def add(self, organization: Organization) -> None:
        self.saved.append(organization)


class FakeUserRepository:
    def __init__(self) -> None:
        self.saved: list[User] = []

    async def add(self, user: User) -> None:
        self.saved.append(user)


class FakeWorkspaceRepository:
    def __init__(self, *, should_fail: bool = False) -> None:
        self.saved: list[Workspace] = []
        self._should_fail = should_fail

    async def add(self, workspace: Workspace) -> None:
        if self._should_fail:
            raise RuntimeError("Workspace persistence failed.")

        self.saved.append(workspace)


class FakeMembershipRepository:
    def __init__(self) -> None:
        self.saved: list[WorkspaceMembership] = []

    async def add(
        self,
        membership: WorkspaceMembership,
    ) -> None:
        self.saved.append(membership)


class FakeTenancyUnitOfWork:
    def __init__(self, *, workspace_should_fail: bool = False) -> None:
        self.organizations = FakeOrganizationRepository()
        self.users = FakeUserRepository()
        self.workspaces = FakeWorkspaceRepository(
            should_fail=workspace_should_fail,
        )
        self.memberships = FakeMembershipRepository()

        self.commit_count = 0
        self.rollback_count = 0

    async def __aenter__(self) -> "FakeTenancyUnitOfWork":
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exception_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.commit_count += 1

    async def rollback(self) -> None:
        self.rollback_count += 1


def build_command() -> ProvisionTenantCommand:
    return ProvisionTenantCommand(
        organization_name="Acme Media",
        organization_slug="acme-media",
        workspace_name="Marketing Science",
        workspace_slug="marketing-science",
        owner_email="owner@example.com",
        owner_display_name="Tina Rincon",
    )


@pytest.mark.asyncio
async def test_provision_tenant_creates_all_records_atomically() -> None:
    unit_of_work = FakeTenancyUnitOfWork()
    service = ProvisionTenant(unit_of_work=unit_of_work)

    result = await service.execute(build_command())

    assert len(unit_of_work.organizations.saved) == 1
    assert len(unit_of_work.users.saved) == 1
    assert len(unit_of_work.workspaces.saved) == 1
    assert len(unit_of_work.memberships.saved) == 1

    organization = unit_of_work.organizations.saved[0]
    user = unit_of_work.users.saved[0]
    workspace = unit_of_work.workspaces.saved[0]
    membership = unit_of_work.memberships.saved[0]

    assert workspace.organization_id == organization.id
    assert membership.workspace_id == workspace.id
    assert membership.user_id == user.id
    assert membership.role is WorkspaceRole.OWNER

    assert result.organization_id == organization.id
    assert result.workspace_id == workspace.id
    assert result.owner_user_id == user.id
    assert result.owner_membership_id == membership.id

    assert unit_of_work.commit_count == 1
    assert unit_of_work.rollback_count == 0


@pytest.mark.asyncio
async def test_provision_tenant_rolls_back_when_persistence_fails() -> None:
    unit_of_work = FakeTenancyUnitOfWork(
        workspace_should_fail=True,
    )
    service = ProvisionTenant(unit_of_work=unit_of_work)

    with pytest.raises(
        RuntimeError,
        match="Workspace persistence failed",
    ):
        await service.execute(build_command())

    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 1
