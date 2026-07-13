from types import TracebackType
from uuid import UUID, uuid4

import pytest

from incrementality_api.application.authorization.authorize_workspace import (
    AuthorizeWorkspaceAction,
)
from incrementality_api.application.authorization.errors import (
    WorkspaceAccessDeniedError,
)
from incrementality_api.domain.authorization.permissions import (
    WorkspacePermission,
)
from incrementality_api.domain.authorization.policy import (
    WorkspaceAccessPolicy,
)
from incrementality_api.domain.tenancy.entities import (
    WorkspaceMembership,
)
from incrementality_api.domain.tenancy.roles import WorkspaceRole


class FakeMembershipReader:
    def __init__(
        self,
        membership: WorkspaceMembership | None,
    ) -> None:
        self._membership = membership
        self.requested_workspace_id: UUID | None = None
        self.requested_user_id: UUID | None = None

    async def get_by_workspace_and_user(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
    ) -> WorkspaceMembership | None:
        self.requested_workspace_id = workspace_id
        self.requested_user_id = user_id

        return self._membership


class FakeAuthorizationUnitOfWork:
    def __init__(
        self,
        membership: WorkspaceMembership | None,
    ) -> None:
        self.memberships = FakeMembershipReader(
            membership,
        )
        self.rollback_count = 0

    async def __aenter__(
        self,
    ) -> "FakeAuthorizationUnitOfWork":
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exception, traceback

        if exception_type is not None:
            self.rollback_count += 1


def build_membership(
    *,
    workspace_id: UUID,
    user_id: UUID,
    role: WorkspaceRole,
) -> WorkspaceMembership:
    return WorkspaceMembership.create(
        workspace_id=workspace_id,
        user_id=user_id,
        role=role,
    )


@pytest.mark.asyncio
async def test_authorizes_member_with_required_permission() -> None:
    workspace_id = uuid4()
    user_id = uuid4()

    membership = build_membership(
        workspace_id=workspace_id,
        user_id=user_id,
        role=WorkspaceRole.ANALYST,
    )

    unit_of_work = FakeAuthorizationUnitOfWork(
        membership,
    )

    service = AuthorizeWorkspaceAction(
        unit_of_work=unit_of_work,
        policy=WorkspaceAccessPolicy(),
    )

    result = await service.execute(
        workspace_id=workspace_id,
        user_id=user_id,
        permission=WorkspacePermission.RUN_ANALYSES,
    )

    assert result.workspace_id == workspace_id
    assert result.user_id == user_id
    assert result.membership_id == membership.id
    assert result.role is WorkspaceRole.ANALYST
    assert result.permission is (WorkspacePermission.RUN_ANALYSES)

    assert unit_of_work.memberships.requested_workspace_id == workspace_id
    assert unit_of_work.memberships.requested_user_id == user_id
    assert unit_of_work.rollback_count == 0


@pytest.mark.asyncio
async def test_rejects_member_without_required_permission() -> None:
    workspace_id = uuid4()
    user_id = uuid4()

    membership = build_membership(
        workspace_id=workspace_id,
        user_id=user_id,
        role=WorkspaceRole.VIEWER,
    )

    unit_of_work = FakeAuthorizationUnitOfWork(
        membership,
    )

    service = AuthorizeWorkspaceAction(
        unit_of_work=unit_of_work,
        policy=WorkspaceAccessPolicy(),
    )

    with pytest.raises(
        WorkspaceAccessDeniedError,
        match="Workspace access denied",
    ):
        await service.execute(
            workspace_id=workspace_id,
            user_id=user_id,
            permission=WorkspacePermission.RUN_ANALYSES,
        )

    assert unit_of_work.rollback_count == 1


@pytest.mark.asyncio
async def test_rejects_user_without_workspace_membership() -> None:
    unit_of_work = FakeAuthorizationUnitOfWork(None)

    service = AuthorizeWorkspaceAction(
        unit_of_work=unit_of_work,
        policy=WorkspaceAccessPolicy(),
    )

    with pytest.raises(
        WorkspaceAccessDeniedError,
        match="Workspace access denied",
    ):
        await service.execute(
            workspace_id=uuid4(),
            user_id=uuid4(),
            permission=WorkspacePermission.VIEW_WORKSPACE,
        )

    assert unit_of_work.rollback_count == 1


@pytest.mark.asyncio
async def test_missing_and_forbidden_access_use_same_error() -> None:
    workspace_id = uuid4()
    user_id = uuid4()

    viewer_membership = build_membership(
        workspace_id=workspace_id,
        user_id=user_id,
        role=WorkspaceRole.VIEWER,
    )

    missing_service = AuthorizeWorkspaceAction(
        unit_of_work=FakeAuthorizationUnitOfWork(None),
        policy=WorkspaceAccessPolicy(),
    )

    forbidden_service = AuthorizeWorkspaceAction(
        unit_of_work=FakeAuthorizationUnitOfWork(
            viewer_membership,
        ),
        policy=WorkspaceAccessPolicy(),
    )

    with pytest.raises(
        WorkspaceAccessDeniedError,
    ) as missing_error:
        await missing_service.execute(
            workspace_id=workspace_id,
            user_id=user_id,
            permission=WorkspacePermission.MANAGE_MEMBERS,
        )

    with pytest.raises(
        WorkspaceAccessDeniedError,
    ) as forbidden_error:
        await forbidden_service.execute(
            workspace_id=workspace_id,
            user_id=user_id,
            permission=WorkspacePermission.MANAGE_MEMBERS,
        )

    assert str(missing_error.value) == (str(forbidden_error.value))
