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
    "permission",
    list(WorkspacePermission),
)
def test_owner_has_every_workspace_permission(
    permission: WorkspacePermission,
) -> None:
    policy = WorkspaceAccessPolicy()

    assert policy.allows(
        role=WorkspaceRole.OWNER,
        permission=permission,
    )


@pytest.mark.parametrize(
    ("role", "permission"),
    [
        (
            WorkspaceRole.ADMIN,
            WorkspacePermission.MANAGE_WORKSPACE,
        ),
        (
            WorkspaceRole.ADMIN,
            WorkspacePermission.MANAGE_MEMBERS,
        ),
        (
            WorkspaceRole.ADMIN,
            WorkspacePermission.MANAGE_DATASETS,
        ),
        (
            WorkspaceRole.ADMIN,
            WorkspacePermission.RUN_ANALYSES,
        ),
        (
            WorkspaceRole.ANALYST,
            WorkspacePermission.VIEW_WORKSPACE,
        ),
        (
            WorkspaceRole.ANALYST,
            WorkspacePermission.MANAGE_DATASETS,
        ),
        (
            WorkspaceRole.ANALYST,
            WorkspacePermission.RUN_ANALYSES,
        ),
        (
            WorkspaceRole.ANALYST,
            WorkspacePermission.VIEW_REPORTS,
        ),
        (
            WorkspaceRole.VIEWER,
            WorkspacePermission.VIEW_WORKSPACE,
        ),
        (
            WorkspaceRole.VIEWER,
            WorkspacePermission.VIEW_REPORTS,
        ),
    ],
)
def test_role_permission_matrix_allows_expected_actions(
    role: WorkspaceRole,
    permission: WorkspacePermission,
) -> None:
    policy = WorkspaceAccessPolicy()

    assert policy.allows(
        role=role,
        permission=permission,
    )


@pytest.mark.parametrize(
    ("role", "permission"),
    [
        (
            WorkspaceRole.ANALYST,
            WorkspacePermission.MANAGE_MEMBERS,
        ),
        (
            WorkspaceRole.ANALYST,
            WorkspacePermission.MANAGE_WORKSPACE,
        ),
        (
            WorkspaceRole.VIEWER,
            WorkspacePermission.MANAGE_DATASETS,
        ),
        (
            WorkspaceRole.VIEWER,
            WorkspacePermission.RUN_ANALYSES,
        ),
        (
            WorkspaceRole.VIEWER,
            WorkspacePermission.MANAGE_MEMBERS,
        ),
    ],
)
def test_role_permission_matrix_denies_restricted_actions(
    role: WorkspaceRole,
    permission: WorkspacePermission,
) -> None:
    policy = WorkspaceAccessPolicy()

    assert not policy.allows(
        role=role,
        permission=permission,
    )


def test_require_accepts_allowed_action() -> None:
    policy = WorkspaceAccessPolicy()

    policy.require(
        role=WorkspaceRole.ANALYST,
        permission=WorkspacePermission.RUN_ANALYSES,
    )


def test_require_rejects_forbidden_action() -> None:
    policy = WorkspaceAccessPolicy()

    with pytest.raises(
        WorkspaceAuthorizationError,
        match="Workspace permission denied",
    ):
        policy.require(
            role=WorkspaceRole.VIEWER,
            permission=WorkspacePermission.RUN_ANALYSES,
        )
