from datetime import UTC, datetime
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from incrementality_api.api.dependencies.authentication import (
    get_login_service,
)
from incrementality_api.api.v1.routes.authentication import (
    router,
)
from incrementality_api.application.authentication.errors import (
    InvalidCredentialsError,
)
from incrementality_api.application.authentication.login import (
    LoginCommand,
    LoginResult,
)

USER_ID = UUID(
    "20260713-1234-5678-9012-123456789012",
)

EXPIRES_AT = datetime(
    2026,
    7,
    14,
    2,
    30,
    tzinfo=UTC,
)


class StubLogin:
    def __init__(
        self,
        *,
        result: LoginResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.received_command: LoginCommand | None = None

    async def execute(
        self,
        command: LoginCommand,
    ) -> LoginResult:
        self.received_command = command

        if self._error is not None:
            raise self._error

        if self._result is None:
            raise AssertionError("The login result was not configured.")

        return self._result


def build_client(
    login_service: StubLogin,
) -> TestClient:
    application = FastAPI()
    application.include_router(router)

    application.dependency_overrides[get_login_service] = lambda: login_service

    return TestClient(application)


def test_login_returns_session_token() -> None:
    login_service = StubLogin(
        result=LoginResult(
            user_id=USER_ID,
            raw_session_token="raw-session-token",
            expires_at=EXPIRES_AT,
        )
    )

    client = build_client(login_service)

    response = client.post(
        "/auth/login",
        json={
            "email": "  OWNER@EXAMPLE.COM  ",
            "password": "Correct-password-123!",
        },
    )

    assert response.status_code == 200

    assert response.json() == {
        "user_id": str(USER_ID),
        "session_token": "raw-session-token",
        "token_type": "bearer",
        "expires_at": "2026-07-14T02:30:00Z",
    }

    assert login_service.received_command == LoginCommand(
        email="  OWNER@EXAMPLE.COM  ",
        password="Correct-password-123!",
    )


def test_login_maps_invalid_credentials_to_401() -> None:
    login_service = StubLogin(
        error=InvalidCredentialsError(
            "Invalid email or password.",
        )
    )

    client = build_client(login_service)

    response = client.post(
        "/auth/login",
        json={
            "email": "owner@example.com",
            "password": "Wrong-password-456!",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid email or password.",
    }

    assert response.headers["www-authenticate"] == ("Bearer")
