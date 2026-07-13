from incrementality_api.domain.authorization.errors import (
    WorkspaceAuthorizationError,
)
from incrementality_api.domain.authorization.permissions import (
    WorkspacePermission,
)
from incrementality_api.domain.tenancy.roles import WorkspaceRole

_PERMISSION_MATRIX: dict[
    WorkspaceRole,
    frozenset[WorkspacePermission],
] = {
    WorkspaceRole.OWNER: frozenset(WorkspacePermission),
    WorkspaceRole.ADMIN: frozenset(
        {
            WorkspacePermission.VIEW_WORKSPACE,
            WorkspacePermission.MANAGE_WORKSPACE,
            WorkspacePermission.MANAGE_MEMBERS,
            WorkspacePermission.MANAGE_PROJECTS,
            WorkspacePermission.MANAGE_DATASETS,
            WorkspacePermission.RUN_ANALYSES,
            WorkspacePermission.VIEW_REPORTS,
        }
    ),
    WorkspaceRole.ANALYST: frozenset(
        {
            WorkspacePermission.VIEW_WORKSPACE,
            WorkspacePermission.MANAGE_PROJECTS,
            WorkspacePermission.MANAGE_DATASETS,
            WorkspacePermission.RUN_ANALYSES,
            WorkspacePermission.VIEW_REPORTS,
        }
    ),
    WorkspaceRole.VIEWER: frozenset(
        {
            WorkspacePermission.VIEW_WORKSPACE,
            WorkspacePermission.VIEW_REPORTS,
        }
    ),
}


class WorkspaceAccessPolicy:
    """Determine which workspace actions each role may perform."""

    def allows(
        self,
        *,
        role: WorkspaceRole,
        permission: WorkspacePermission,
    ) -> bool:
        return permission in _PERMISSION_MATRIX[role]

    def require(
        self,
        *,
        role: WorkspaceRole,
        permission: WorkspacePermission,
    ) -> None:
        if not self.allows(
            role=role,
            permission=permission,
        ):
            raise WorkspaceAuthorizationError("Workspace permission denied.")
