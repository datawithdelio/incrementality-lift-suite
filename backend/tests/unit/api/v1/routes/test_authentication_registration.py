from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from incrementality_api.api.dependencies.authentication import (
    get_register_user_service,
)
from incrementality_api.api.v1.routes.authentication import (
    router,
)
from incrementality_api.application.authentication.register_user import (
    RegisteredUser,
    RegisterUserCommand,
)
from incrementality_api.application.tenancy.errors import (
    TenancyConflictError,
)

USER_ID = UUID(
    "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
)


class StubRegisterUser:
    def __init__(self) -> None:
        self.received_command: RegisterUserCommand | None = None

    async def execute(
        self,
        command: RegisterUserCommand,
    ) -> RegisteredUser:
        self.received_command = command

        return RegisteredUser(
            user_id=USER_ID,
        )


def test_register_user_creates_account_without_workspace() -> None:
    service = StubRegisterUser()

    application = FastAPI()
    application.include_router(router)

    application.dependency_overrides[
        get_register_user_service
    ] = lambda: service

    client = TestClient(application)

    response = client.post(
        "/auth/register",
        json={
            "email": "new-user@example.com",
            "display_name": "Avery Stone",
            "password": "Secure-user-password-123!",
        },
    )

    assert response.status_code == 201

    assert response.json() == {
        "user_id": str(USER_ID),
    }

    assert service.received_command == RegisterUserCommand(
        email="new-user@example.com",
        display_name="Avery Stone",
        password="Secure-user-password-123!",
    )



class ConflictingRegisterUser:
    async def execute(
        self,
        command: RegisterUserCommand,
    ) -> RegisteredUser:
        raise TenancyConflictError(
            "Tenant data conflicts with an existing record."
        )


def test_register_user_returns_conflict_for_duplicate_account() -> None:
    application = FastAPI()
    application.include_router(router)

    application.dependency_overrides[
        get_register_user_service
    ] = lambda: ConflictingRegisterUser()

    client = TestClient(
        application,
        raise_server_exceptions=False,
    )

    response = client.post(
        "/auth/register",
        json={
            "email": "existing-user@example.com",
            "display_name": "Existing User",
            "password": "Secure-user-password-123!",
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "An account with this information "
            "already exists."
        ),
    }
