from datetime import UTC, datetime
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from incrementality_api.api.dependencies.authentication import (
    get_logout_service,
    get_validate_session_service,
)
from incrementality_api.api.v1.routes.authentication import (
    router,
)
from incrementality_api.application.authentication.errors import (
    InvalidSessionTokenError,
)
from incrementality_api.application.authentication.validate_session import (
    ValidatedSession,
)

SESSION_ID = UUID(
    "11111111-2222-3333-4444-555555555555",
)

USER_ID = UUID(
    "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
)

EXPIRES_AT = datetime(
    2026,
    7,
    14,
    3,
    0,
    tzinfo=UTC,
)

RAW_TOKEN = "secure-raw-session-token"


class StubValidateSession:
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
            raise AssertionError("Validation result was not configured.")

        return self._result


class StubLogout:
    def __init__(
        self,
        *,
        error: Exception | None = None,
    ) -> None:
        self._error = error
        self.received_token: str | None = None

    async def execute(self, raw_token: str) -> None:
        self.received_token = raw_token

        if self._error is not None:
            raise self._error


def build_client(
    *,
    validation_service: StubValidateSession,
    logout_service: StubLogout,
) -> TestClient:
    application = FastAPI()
    application.include_router(router)

    application.dependency_overrides[get_validate_session_service] = lambda: validation_service

    application.dependency_overrides[get_logout_service] = lambda: logout_service

    return TestClient(application)


def test_read_session_returns_authenticated_identity() -> None:
    validation_service = StubValidateSession(
        result=ValidatedSession(
            session_id=SESSION_ID,
            user_id=USER_ID,
            expires_at=EXPIRES_AT,
        )
    )

    client = build_client(
        validation_service=validation_service,
        logout_service=StubLogout(),
    )

    response = client.get(
        "/auth/session",
        headers={
            "Authorization": f"Bearer {RAW_TOKEN}",
        },
    )

    assert response.status_code == 200

    assert response.json() == {
        "session_id": str(SESSION_ID),
        "user_id": str(USER_ID),
        "expires_at": "2026-07-14T03:00:00Z",
    }

    assert validation_service.received_token == RAW_TOKEN


def test_read_session_maps_invalid_token_to_401() -> None:
    validation_service = StubValidateSession(
        error=InvalidSessionTokenError(
            "Invalid or expired session.",
        )
    )

    client = build_client(
        validation_service=validation_service,
        logout_service=StubLogout(),
    )

    response = client.get(
        "/auth/session",
        headers={
            "Authorization": f"Bearer {RAW_TOKEN}",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid or expired session.",
    }
    assert response.headers["www-authenticate"] == ("Bearer")


def test_read_session_rejects_missing_authorization() -> None:
    client = build_client(
        validation_service=StubValidateSession(),
        logout_service=StubLogout(),
    )

    response = client.get("/auth/session")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == ("Bearer")


def test_read_session_rejects_non_bearer_authorization() -> None:
    client = build_client(
        validation_service=StubValidateSession(),
        logout_service=StubLogout(),
    )

    response = client.get(
        "/auth/session",
        headers={
            "Authorization": "Basic credentials",
        },
    )

    assert response.status_code == 401


def test_logout_revokes_bearer_session() -> None:
    logout_service = StubLogout()

    client = build_client(
        validation_service=StubValidateSession(),
        logout_service=logout_service,
    )

    response = client.post(
        "/auth/logout",
        headers={
            "Authorization": f"Bearer {RAW_TOKEN}",
        },
    )

    assert response.status_code == 204
    assert response.content == b""
    assert logout_service.received_token == RAW_TOKEN


def test_logout_maps_invalid_token_to_401() -> None:
    logout_service = StubLogout(
        error=InvalidSessionTokenError(
            "Invalid or expired session.",
        )
    )

    client = build_client(
        validation_service=StubValidateSession(),
        logout_service=logout_service,
    )

    response = client.post(
        "/auth/logout",
        headers={
            "Authorization": f"Bearer {RAW_TOKEN}",
        },
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == ("Bearer")
