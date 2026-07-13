from dataclasses import dataclass
from uuid import UUID

from incrementality_api.application.authorization.errors import (
    WorkspaceAccessDeniedError,
)
from incrementality_api.application.authorization.ports import (
    AuthorizationUnitOfWork,
)
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

_ACCESS_DENIED_MESSAGE = "Workspace access denied."


@dataclass(frozen=True, slots=True)
class AuthorizedWorkspaceAccess:
    workspace_id: UUID
    user_id: UUID
    membership_id: UUID
    role: WorkspaceRole
    permission: WorkspacePermission


class AuthorizeWorkspaceAction:
    """Authorize one user action inside one workspace."""

    def __init__(
        self,
        *,
        unit_of_work: AuthorizationUnitOfWork,
        policy: WorkspaceAccessPolicy,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._policy = policy

    async def execute(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        permission: WorkspacePermission,
    ) -> AuthorizedWorkspaceAccess:
        async with self._unit_of_work:
            membership = await self._unit_of_work.memberships.get_by_workspace_and_user(
                workspace_id=workspace_id,
                user_id=user_id,
            )

            if membership is None:
                raise WorkspaceAccessDeniedError(
                    _ACCESS_DENIED_MESSAGE,
                )

            try:
                self._policy.require(
                    role=membership.role,
                    permission=permission,
                )
            except WorkspaceAuthorizationError as error:
                raise WorkspaceAccessDeniedError(
                    _ACCESS_DENIED_MESSAGE,
                ) from error

            return AuthorizedWorkspaceAccess(
                workspace_id=workspace_id,
                user_id=user_id,
                membership_id=membership.id,
                role=membership.role,
                permission=permission,
            )
