from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from incrementality_api.api.dependencies.authorization import (
    get_authenticate_workspace_service,
)
from incrementality_api.api.dependencies.tenancy import (
    get_list_workspace_members_service,
)
from incrementality_api.api.v1.routes.workspaces import (
    router as workspaces_router,
)
from incrementality_api.application.authorization.authenticate_workspace import (
    AuthorizedWorkspacePrincipal,
)
from incrementality_api.domain.authorization.permissions import (
    WorkspacePermission,
)
from incrementality_api.domain.tenancy.roles import (
    WorkspaceRole,
)


class StubAuthenticateWorkspace:
    def __init__(self) -> None:
        self.received: tuple[
            str,
            UUID,
            WorkspacePermission,
        ] | None = None

    async def execute(
        self,
        *,
        raw_token: str,
        workspace_id: UUID,
        permission: WorkspacePermission,
    ) -> AuthorizedWorkspacePrincipal:
        self.received = (
            raw_token,
            workspace_id,
            permission,
        )

        return AuthorizedWorkspacePrincipal(
            session_id=uuid4(),
            user_id=uuid4(),
            workspace_id=workspace_id,
            membership_id=uuid4(),
            role=WorkspaceRole.OWNER,
            permission=permission,
            session_expires_at=datetime(
                2026,
                8,
                1,
                tzinfo=UTC,
            ),
        )


class StubListWorkspaceMembers:
    def __init__(
        self,
        members: list[SimpleNamespace],
    ) -> None:
        self._members = members
        self.workspace_id: UUID | None = None

    async def execute(
        self,
        *,
        workspace_id: UUID,
    ) -> list[SimpleNamespace]:
        self.workspace_id = workspace_id
        return self._members


def test_lists_only_safe_members_for_authorized_workspace() -> None:
    workspace_id = uuid4()

    joined_at = datetime(
        2026,
        7,
        1,
        12,
        0,
        tzinfo=UTC,
    )

    members = [
        SimpleNamespace(
            display_name="Delio Rincon",
            email="delio@example.com",
            role="owner",
            joined_at=joined_at,
        ),
        SimpleNamespace(
            display_name="Jane Analyst",
            email="jane@example.com",
            role="analyst",
            joined_at=joined_at,
        ),
    ]

    auth_service = StubAuthenticateWorkspace()

    member_service = StubListWorkspaceMembers(
        members,
    )

    application = FastAPI()

    application.include_router(
        workspaces_router,
    )

    application.dependency_overrides[
        get_authenticate_workspace_service
    ] = lambda: auth_service

    application.dependency_overrides[
        get_list_workspace_members_service
    ] = lambda: member_service

    client = TestClient(
        application,
        raise_server_exceptions=False,
    )

    response = client.get(
        f"/workspaces/{workspace_id}/members",
        headers={
            "Authorization":
                "Bearer valid-token",
        },
    )

    assert response.status_code == 200

    assert response.json() == [
        {
            "display_name":
                "Delio Rincon",
            "email":
                "delio@example.com",
            "role":
                "owner",
            "joined_at":
                joined_at.isoformat().replace(
                    "+00:00",
                    "Z",
                ),
        },
        {
            "display_name":
                "Jane Analyst",
            "email":
                "jane@example.com",
            "role":
                "analyst",
            "joined_at":
                joined_at.isoformat().replace(
                    "+00:00",
                    "Z",
                ),
        },
    ]

    assert member_service.workspace_id == (
        workspace_id
    )

    assert auth_service.received == (
        "valid-token",
        workspace_id,
        WorkspacePermission.MANAGE_MEMBERS,
    )

    for member in response.json():
        assert set(member) == {
            "display_name",
            "email",
            "role",
            "joined_at",
        }

        assert "password_hash" not in member
        assert "session_token" not in member
        assert "user_id" not in member
        assert "membership_id" not in member
