from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from incrementality_api.application.authentication.validate_session import (
    ValidatedSession,
)
from incrementality_api.application.authorization.authorize_workspace import (
    AuthorizedWorkspaceAccess,
)
from incrementality_api.domain.authorization.permissions import (
    WorkspacePermission,
)
from incrementality_api.domain.tenancy.roles import WorkspaceRole


class SessionValidator(Protocol):
    async def execute(
        self,
        raw_token: str,
    ) -> ValidatedSession:
        """Validate an opaque session token."""


class WorkspaceActionAuthorizer(Protocol):
    async def execute(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        permission: WorkspacePermission,
    ) -> AuthorizedWorkspaceAccess:
        """Authorize a user action in one workspace."""


@dataclass(frozen=True, slots=True)
class AuthorizedWorkspacePrincipal:
    session_id: UUID
    user_id: UUID
    workspace_id: UUID
    membership_id: UUID
    role: WorkspaceRole
    permission: WorkspacePermission
    session_expires_at: datetime


class AuthenticateWorkspaceAction:
    """
    Compose session authentication with workspace authorization.
    """

    def __init__(
        self,
        *,
        session_validator: SessionValidator,
        workspace_authorizer: WorkspaceActionAuthorizer,
    ) -> None:
        self._session_validator = session_validator
        self._workspace_authorizer = workspace_authorizer

    async def execute(
        self,
        *,
        raw_token: str,
        workspace_id: UUID,
        permission: WorkspacePermission,
    ) -> AuthorizedWorkspacePrincipal:
        validated_session = await self._session_validator.execute(
            raw_token,
        )

        authorized_access = await self._workspace_authorizer.execute(
            workspace_id=workspace_id,
            user_id=validated_session.user_id,
            permission=permission,
        )

        return AuthorizedWorkspacePrincipal(
            session_id=validated_session.session_id,
            user_id=validated_session.user_id,
            workspace_id=authorized_access.workspace_id,
            membership_id=authorized_access.membership_id,
            role=authorized_access.role,
            permission=authorized_access.permission,
            session_expires_at=validated_session.expires_at,
        )
