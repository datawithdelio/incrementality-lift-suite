from datetime import UTC, datetime
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from incrementality_api.api.dependencies.authentication import (
    get_validate_session_service,
)
from incrementality_api.api.dependencies.tenancy import (
    get_list_user_workspaces_service,
)
from incrementality_api.api.v1.routes.workspaces import (
    router,
)
from incrementality_api.application.authentication.validate_session import (
    ValidatedSession,
)
from incrementality_api.application.tenancy.list_user_workspaces import (
    AccessibleWorkspace,
)

SESSION_ID = UUID(
    "11111111-2222-3333-4444-555555555555",
)
USER_ID = UUID(
    "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
)
WORKSPACE_ID = UUID(
    "22222222-2222-2222-2222-222222222222",
)
ORGANIZATION_ID = UUID(
    "33333333-3333-3333-3333-333333333333",
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


class StubListUserWorkspaces:
    def __init__(
        self,
        *,
        result: list[AccessibleWorkspace],
    ) -> None:
        self._result = result
        self.received_user_id: UUID | None = None

    async def execute(
        self,
        *,
        user_id: UUID,
    ) -> list[AccessibleWorkspace]:
        self.received_user_id = user_id
        return self._result


def build_client(
    *,
    validation_service: StubValidateSession,
    workspace_service: StubListUserWorkspaces,
) -> TestClient:
    application = FastAPI()
    application.include_router(router)

    application.dependency_overrides[
        get_validate_session_service
    ] = lambda: validation_service

    application.dependency_overrides[
        get_list_user_workspaces_service
    ] = lambda: workspace_service

    return TestClient(application)


def test_list_workspaces_uses_authenticated_session_identity() -> None:
    validation_service = StubValidateSession()
    workspace_service = StubListUserWorkspaces(
        result=[
            AccessibleWorkspace(
                workspace_id=WORKSPACE_ID,
                organization_id=ORGANIZATION_ID,
                name="Marketing Science",
                slug="marketing-science",
                role="owner",
            )
        ]
    )

    client = build_client(
        validation_service=validation_service,
        workspace_service=workspace_service,
    )

    response = client.get(
        "/workspaces",
        headers={
            "Authorization": f"Bearer {RAW_TOKEN}",
        },
    )

    assert response.status_code == 200

    assert response.json() == [
        {
            "workspace_id": str(WORKSPACE_ID),
            "organization_id": str(ORGANIZATION_ID),
            "name": "Marketing Science",
            "slug": "marketing-science",
            "role": "owner",
        }
    ]

    assert validation_service.received_token == RAW_TOKEN
    assert workspace_service.received_user_id == USER_ID


def test_list_workspaces_returns_empty_list_for_new_user() -> None:
    client = build_client(
        validation_service=StubValidateSession(),
        workspace_service=StubListUserWorkspaces(
            result=[],
        ),
    )

    response = client.get(
        "/workspaces",
        headers={
            "Authorization": f"Bearer {RAW_TOKEN}",
        },
    )

    assert response.status_code == 200
    assert response.json() == []


def test_list_workspaces_requires_bearer_authentication() -> None:
    client = build_client(
        validation_service=StubValidateSession(),
        workspace_service=StubListUserWorkspaces(
            result=[],
        ),
    )

    response = client.get(
        "/workspaces",
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
