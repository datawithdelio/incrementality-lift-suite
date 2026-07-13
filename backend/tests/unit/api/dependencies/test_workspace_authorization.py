from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from incrementality_api.api.dependencies.authorization import (
    RequireWorkspacePermission,
    get_authenticate_workspace_service,
)
from incrementality_api.application.authentication.errors import (
    InvalidSessionTokenError,
)
from incrementality_api.application.authorization.authenticate_workspace import (
    AuthorizedWorkspacePrincipal,
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
    8,
    0,
    tzinfo=UTC,
)


class StubAuthenticateWorkspaceAction:
    def __init__(
        self,
        *,
        result: AuthorizedWorkspacePrincipal | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error

        self.received_token: str | None = None
        self.received_workspace_id: UUID | None = None
        self.received_permission: WorkspacePermission | None = None

    async def execute(
        self,
        *,
        raw_token: str,
        workspace_id: UUID,
        permission: WorkspacePermission,
    ) -> AuthorizedWorkspacePrincipal:
        self.received_token = raw_token
        self.received_workspace_id = workspace_id
        self.received_permission = permission

        if self._error is not None:
            raise self._error

        if self._result is None:
            raise AssertionError("Authorization result was not configured.")

        return self._result


def build_client(
    service: StubAuthenticateWorkspaceAction,
) -> TestClient:
    application = FastAPI()

    require_permission = RequireWorkspacePermission(
        WorkspacePermission.RUN_ANALYSES,
    )

    @application.get(
        "/workspaces/{workspace_id}/protected",
    )
    async def protected_route(
        principal: Annotated[
            AuthorizedWorkspacePrincipal,
            Depends(require_permission),
        ],
    ) -> dict[str, str]:
        return {
            "user_id": str(principal.user_id),
            "workspace_id": str(principal.workspace_id),
            "role": principal.role.value,
            "permission": principal.permission.value,
        }

    application.dependency_overrides[get_authenticate_workspace_service] = lambda: service

    return TestClient(application)


def test_returns_authorized_workspace_principal() -> None:
    workspace_id = uuid4()
    user_id = uuid4()

    service = StubAuthenticateWorkspaceAction(
        result=AuthorizedWorkspacePrincipal(
            session_id=uuid4(),
            user_id=user_id,
            workspace_id=workspace_id,
            membership_id=uuid4(),
            role=WorkspaceRole.ANALYST,
            permission=WorkspacePermission.RUN_ANALYSES,
            session_expires_at=EXPIRES_AT,
        )
    )

    client = build_client(service)

    response = client.get(
        f"/workspaces/{workspace_id}/protected",
        headers={
            "Authorization": "Bearer secure-token",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "user_id": str(user_id),
        "workspace_id": str(workspace_id),
        "role": "analyst",
        "permission": "run_analyses",
    }

    assert service.received_token == "secure-token"
    assert service.received_workspace_id == workspace_id
    assert service.received_permission is (WorkspacePermission.RUN_ANALYSES)


def test_missing_bearer_header_returns_401() -> None:
    service = StubAuthenticateWorkspaceAction()
    client = build_client(service)

    response = client.get(
        f"/workspaces/{uuid4()}/protected",
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid or expired session.",
    }
    assert response.headers["www-authenticate"] == "Bearer"
    assert service.received_token is None


def test_malformed_bearer_header_returns_401() -> None:
    service = StubAuthenticateWorkspaceAction()
    client = build_client(service)

    response = client.get(
        f"/workspaces/{uuid4()}/protected",
        headers={
            "Authorization": "Basic credentials",
        },
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert service.received_token is None


def test_invalid_session_returns_401() -> None:
    service = StubAuthenticateWorkspaceAction(
        error=InvalidSessionTokenError(
            "Invalid or expired session.",
        )
    )
    client = build_client(service)

    response = client.get(
        f"/workspaces/{uuid4()}/protected",
        headers={
            "Authorization": "Bearer invalid-token",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid or expired session.",
    }
    assert response.headers["www-authenticate"] == "Bearer"


def test_workspace_permission_denial_returns_403() -> None:
    service = StubAuthenticateWorkspaceAction(
        error=WorkspaceAccessDeniedError(
            "Workspace access denied.",
        )
    )
    client = build_client(service)

    response = client.get(
        f"/workspaces/{uuid4()}/protected",
        headers={
            "Authorization": "Bearer valid-token",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Workspace access denied.",
    }
