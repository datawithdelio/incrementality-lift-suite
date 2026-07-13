import pytest

from incrementality_api.domain.authorization.errors import (
    WorkspaceAuthorizationError,
)
from incrementality_api.domain.authorization.permissions import (
    WorkspacePermission,
)
from incrementality_api.domain.authorization.policy import (
    WorkspaceAccessPolicy,
)
from incrementality_api.domain.tenancy.roles import WorkspaceRole


@pytest.mark.parametrize(
    "role",
    [
        WorkspaceRole.OWNER,
        WorkspaceRole.ADMIN,
        WorkspaceRole.ANALYST,
    ],
)
def test_project_contributors_can_manage_projects(
    role: WorkspaceRole,
) -> None:
    policy = WorkspaceAccessPolicy()

    assert policy.allows(
        role=role,
        permission=WorkspacePermission.MANAGE_PROJECTS,
    )


def test_viewer_cannot_manage_projects() -> None:
    policy = WorkspaceAccessPolicy()

    assert not policy.allows(
        role=WorkspaceRole.VIEWER,
        permission=WorkspacePermission.MANAGE_PROJECTS,
    )


def test_require_rejects_viewer_project_management() -> None:
    policy = WorkspaceAccessPolicy()

    with pytest.raises(
        WorkspaceAuthorizationError,
        match="Workspace permission denied",
    ):
        policy.require(
            role=WorkspaceRole.VIEWER,
            permission=WorkspacePermission.MANAGE_PROJECTS,
        )
