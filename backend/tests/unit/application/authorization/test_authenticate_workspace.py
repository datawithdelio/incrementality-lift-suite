from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from incrementality_api.application.authentication.errors import (
    InvalidSessionTokenError,
)
from incrementality_api.application.authentication.validate_session import (
    ValidatedSession,
)
from incrementality_api.application.authorization.authenticate_workspace import (
    AuthenticateWorkspaceAction,
)
from incrementality_api.application.authorization.authorize_workspace import (
    AuthorizedWorkspaceAccess,
)
from incrementality_api.application.authorization.errors import (
    WorkspaceAccessDeniedError,
)
from incrementality_api.domain.authorization.permissions import (
    WorkspacePermission,
)
from incrementality_api.domain.tenancy.roles import WorkspaceRole

EXPIRES_AT = datetime(
    2026,
    7,
    14,
    6,
    0,
    tzinfo=UTC,
)


class StubSessionValidator:
    def __init__(
        self,
        *,
        result: ValidatedSession | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.received_token: str | None = None

    async def execute(
        self,
        raw_token: str,
    ) -> ValidatedSession:
        self.received_token = raw_token

        if self._error is not None:
            raise self._error

        if self._result is None:
            raise AssertionError("Session validation result was not configured.")

        return self._result


class StubWorkspaceAuthorizer:
    def __init__(
        self,
        *,
        result: AuthorizedWorkspaceAccess | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error

        self.received_workspace_id: UUID | None = None
        self.received_user_id: UUID | None = None
        self.received_permission: WorkspacePermission | None = None

    async def execute(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        permission: WorkspacePermission,
    ) -> AuthorizedWorkspaceAccess:
        self.received_workspace_id = workspace_id
        self.received_user_id = user_id
        self.received_permission = permission

        if self._error is not None:
            raise self._error

        if self._result is None:
            raise AssertionError("Workspace authorization result was not configured.")

        return self._result


@pytest.mark.asyncio
async def test_authenticates_and_authorizes_workspace_action() -> None:
    session_id = uuid4()
    user_id = uuid4()
    workspace_id = uuid4()
    membership_id = uuid4()

    session_validator = StubSessionValidator(
        result=ValidatedSession(
            session_id=session_id,
            user_id=user_id,
            expires_at=EXPIRES_AT,
        )
    )

    workspace_authorizer = StubWorkspaceAuthorizer(
        result=AuthorizedWorkspaceAccess(
            workspace_id=workspace_id,
            user_id=user_id,
            membership_id=membership_id,
            role=WorkspaceRole.ANALYST,
            permission=WorkspacePermission.RUN_ANALYSES,
        )
    )

    service = AuthenticateWorkspaceAction(
        session_validator=session_validator,
        workspace_authorizer=workspace_authorizer,
    )

    result = await service.execute(
        raw_token="secure-session-token",
        workspace_id=workspace_id,
        permission=WorkspacePermission.RUN_ANALYSES,
    )

    assert session_validator.received_token == ("secure-session-token")

    assert workspace_authorizer.received_workspace_id == (workspace_id)
    assert workspace_authorizer.received_user_id == user_id
    assert workspace_authorizer.received_permission is (WorkspacePermission.RUN_ANALYSES)

    assert result.session_id == session_id
    assert result.user_id == user_id
    assert result.workspace_id == workspace_id
    assert result.membership_id == membership_id
    assert result.role is WorkspaceRole.ANALYST
    assert result.permission is (WorkspacePermission.RUN_ANALYSES)
    assert result.session_expires_at == EXPIRES_AT


@pytest.mark.asyncio
async def test_invalid_session_stops_before_workspace_lookup() -> None:
    session_validator = StubSessionValidator(
        error=InvalidSessionTokenError(
            "Invalid or expired session.",
        )
    )

    workspace_authorizer = StubWorkspaceAuthorizer()

    service = AuthenticateWorkspaceAction(
        session_validator=session_validator,
        workspace_authorizer=workspace_authorizer,
    )

    with pytest.raises(
        InvalidSessionTokenError,
        match="Invalid or expired session",
    ):
        await service.execute(
            raw_token="invalid-token",
            workspace_id=uuid4(),
            permission=WorkspacePermission.VIEW_WORKSPACE,
        )

    assert workspace_authorizer.received_user_id is None
    assert workspace_authorizer.received_workspace_id is None


@pytest.mark.asyncio
async def test_workspace_denial_is_propagated() -> None:
    user_id = uuid4()

    session_validator = StubSessionValidator(
        result=ValidatedSession(
            session_id=uuid4(),
            user_id=user_id,
            expires_at=EXPIRES_AT,
        )
    )

    workspace_authorizer = StubWorkspaceAuthorizer(
        error=WorkspaceAccessDeniedError(
            "Workspace access denied.",
        )
    )

    service = AuthenticateWorkspaceAction(
        session_validator=session_validator,
        workspace_authorizer=workspace_authorizer,
    )

    with pytest.raises(
        WorkspaceAccessDeniedError,
        match="Workspace access denied",
    ):
        await service.execute(
            raw_token="valid-token",
            workspace_id=uuid4(),
            permission=WorkspacePermission.MANAGE_MEMBERS,
        )

    assert workspace_authorizer.received_user_id == user_id


@pytest.mark.asyncio
async def test_authenticated_user_id_cannot_be_supplied_by_client() -> None:
    authenticated_user_id = uuid4()
    workspace_id = uuid4()

    session_validator = StubSessionValidator(
        result=ValidatedSession(
            session_id=uuid4(),
            user_id=authenticated_user_id,
            expires_at=EXPIRES_AT,
        )
    )

    workspace_authorizer = StubWorkspaceAuthorizer(
        result=AuthorizedWorkspaceAccess(
            workspace_id=workspace_id,
            user_id=authenticated_user_id,
            membership_id=uuid4(),
            role=WorkspaceRole.OWNER,
            permission=WorkspacePermission.MANAGE_MEMBERS,
        )
    )

    service = AuthenticateWorkspaceAction(
        session_validator=session_validator,
        workspace_authorizer=workspace_authorizer,
    )

    await service.execute(
        raw_token="valid-token",
        workspace_id=workspace_id,
        permission=WorkspacePermission.MANAGE_MEMBERS,
    )

    assert workspace_authorizer.received_user_id == (authenticated_user_id)
