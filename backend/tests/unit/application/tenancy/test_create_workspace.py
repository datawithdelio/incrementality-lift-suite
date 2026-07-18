from types import TracebackType
from uuid import UUID

import pytest

from incrementality_api.application.tenancy.create_workspace import (
    CreateWorkspace,
    CreateWorkspaceCommand,
)
from incrementality_api.domain.tenancy.entities import (
    Organization,
    Workspace,
    WorkspaceMembership,
)
from incrementality_api.domain.tenancy.roles import WorkspaceRole

USER_ID = UUID(
    "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
)


class RecordingRepository:
    def __init__(self) -> None:
        self.saved: list[object] = []

    async def add(
        self,
        item: object,
    ) -> None:
        self.saved.append(item)


class FakeTenancyUnitOfWork:
    def __init__(self) -> None:
        self.organizations = RecordingRepository()
        self.users = RecordingRepository()
        self.credentials = RecordingRepository()
        self.workspaces = RecordingRepository()
        self.memberships = RecordingRepository()

        self.commit_count = 0
        self.rollback_count = 0

    async def __aenter__(
        self,
    ) -> "FakeTenancyUnitOfWork":
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exception, traceback

        if exception_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.commit_count += 1

    async def rollback(self) -> None:
        self.rollback_count += 1


@pytest.mark.asyncio
async def test_create_workspace_for_existing_user() -> None:
    unit_of_work = FakeTenancyUnitOfWork()

    service = CreateWorkspace(
        unit_of_work=unit_of_work,
    )

    result = await service.execute(
        CreateWorkspaceCommand(
            user_id=USER_ID,
            organization_name="Northstar Labs",
            workspace_name="Measurement Team",
        )
    )

    assert len(unit_of_work.organizations.saved) == 1
    assert len(unit_of_work.workspaces.saved) == 1
    assert len(unit_of_work.memberships.saved) == 1

    assert unit_of_work.users.saved == []
    assert unit_of_work.credentials.saved == []

    organization = unit_of_work.organizations.saved[0]
    workspace = unit_of_work.workspaces.saved[0]
    membership = unit_of_work.memberships.saved[0]

    assert isinstance(
        organization,
        Organization,
    )
    assert isinstance(
        workspace,
        Workspace,
    )
    assert isinstance(
        membership,
        WorkspaceMembership,
    )

    assert organization.name == "Northstar Labs"
    assert organization.slug == "northstar-labs"

    assert workspace.name == "Measurement Team"
    assert workspace.slug == "measurement-team"
    assert workspace.organization_id == organization.id

    assert membership.workspace_id == workspace.id
    assert membership.user_id == USER_ID
    assert membership.role is WorkspaceRole.OWNER

    assert result.organization_id == organization.id
    assert result.workspace_id == workspace.id
    assert result.membership_id == membership.id

    assert unit_of_work.commit_count == 1
    assert unit_of_work.rollback_count == 0
