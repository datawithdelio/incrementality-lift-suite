from datetime import UTC, datetime
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from incrementality_api.api.dependencies.authentication import (
    get_validate_session_service,
)
from incrementality_api.api.dependencies.tenancy import (
    get_create_workspace_service,
)
from incrementality_api.api.v1.routes.workspaces import (
    router,
)
from incrementality_api.application.authentication.validate_session import (
    ValidatedSession,
)
from incrementality_api.application.tenancy.create_workspace import (
    CreatedWorkspace,
    CreateWorkspaceCommand,
)
from incrementality_api.application.tenancy.errors import (
    TenancyConflictError,
)

SESSION_ID = UUID(
    "11111111-2222-3333-4444-555555555555",
)
USER_ID = UUID(
    "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
)
ORGANIZATION_ID = UUID(
    "33333333-3333-3333-3333-333333333333",
)
WORKSPACE_ID = UUID(
    "22222222-2222-2222-2222-222222222222",
)
MEMBERSHIP_ID = UUID(
    "44444444-4444-4444-4444-444444444444",
)
EXPIRES_AT = datetime(
    2026,
    7,
    18,
    3,
    0,
    tzinfo=UTC,
)
RAW_TOKEN = "secure-session-token"


class StubValidateSession:
    def __init__(self) -> None:
        self.received_token: str | None = None

    async def execute(
        self,
        raw_token: str,
    ) -> ValidatedSession:
        self.received_token = raw_token

        return ValidatedSession(
            session_id=SESSION_ID,
            user_id=USER_ID,
            expires_at=EXPIRES_AT,
        )


class StubCreateWorkspace:
    def __init__(self) -> None:
        self.received_command: CreateWorkspaceCommand | None = None

    async def execute(
        self,
        command: CreateWorkspaceCommand,
    ) -> CreatedWorkspace:
        self.received_command = command

        return CreatedWorkspace(
            organization_id=ORGANIZATION_ID,
            workspace_id=WORKSPACE_ID,
            membership_id=MEMBERSHIP_ID,
        )


def test_create_workspace_uses_authenticated_session_identity() -> None:
    validation_service = StubValidateSession()
    workspace_service = StubCreateWorkspace()

    application = FastAPI()
    application.include_router(router)

    application.dependency_overrides[
        get_validate_session_service
    ] = lambda: validation_service

    application.dependency_overrides[
        get_create_workspace_service
    ] = lambda: workspace_service

    client = TestClient(application)

    response = client.post(
        "/workspaces",
        headers={
            "Authorization": f"Bearer {RAW_TOKEN}",
        },
        json={
            "organization_name": "Northstar Labs",
            "workspace_name": "Measurement Team",
        },
    )

    assert response.status_code == 201

    assert response.json() == {
        "organization_id": str(ORGANIZATION_ID),
        "workspace_id": str(WORKSPACE_ID),
        "membership_id": str(MEMBERSHIP_ID),
    }

    assert validation_service.received_token == RAW_TOKEN

    assert workspace_service.received_command == CreateWorkspaceCommand(
        user_id=USER_ID,
        organization_name="Northstar Labs",
        workspace_name="Measurement Team",
    )


def test_create_workspace_requires_bearer_authentication() -> None:
    validation_service = StubValidateSession()
    workspace_service = StubCreateWorkspace()

    application = FastAPI()
    application.include_router(router)

    application.dependency_overrides[
        get_validate_session_service
    ] = lambda: validation_service

    application.dependency_overrides[
        get_create_workspace_service
    ] = lambda: workspace_service

    client = TestClient(application)

    response = client.post(
        "/workspaces",
        json={
            "organization_name": "Northstar Labs",
            "workspace_name": "Measurement Team",
        },
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"

    assert workspace_service.received_command is None



class ConflictingCreateWorkspace:
    async def execute(
        self,
        command: CreateWorkspaceCommand,
    ) -> CreatedWorkspace:
        raise TenancyConflictError(
            "Tenant data conflicts with an existing record."
        )


def test_create_workspace_returns_conflict_for_existing_tenant_data() -> None:
    validation_service = StubValidateSession()

    application = FastAPI()
    application.include_router(router)

    application.dependency_overrides[
        get_validate_session_service
    ] = lambda: validation_service

    application.dependency_overrides[
        get_create_workspace_service
    ] = lambda: ConflictingCreateWorkspace()

    client = TestClient(
        application,
        raise_server_exceptions=False,
    )

    response = client.post(
        "/workspaces",
        headers={
            "Authorization": f"Bearer {RAW_TOKEN}",
        },
        json={
            "organization_name": "Northstar Labs",
            "workspace_name": "Measurement Team",
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "A workspace with this information "
            "already exists."
        ),
    }

    assert (
        validation_service.received_token
        == RAW_TOKEN
    )
