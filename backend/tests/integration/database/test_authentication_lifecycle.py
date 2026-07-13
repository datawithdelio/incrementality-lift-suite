from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from incrementality_api.api.dependencies.authentication import (
    get_login_service,
    get_logout_service,
    get_validate_session_service,
)
from incrementality_api.api.dependencies.tenancy import (
    get_provision_tenant,
)
from incrementality_api.application.authentication.login import (
    Login,
)
from incrementality_api.application.authentication.logout import (
    Logout,
)
from incrementality_api.application.authentication.validate_session import (
    ValidateSession,
)
from incrementality_api.application.tenancy.provision_tenant import (
    ProvisionTenant,
)
from incrementality_api.infrastructure.database.unit_of_work.authentication import (
    SqlAlchemyAuthenticationUnitOfWork,
)
from incrementality_api.infrastructure.database.unit_of_work.tenancy import (
    SqlAlchemyTenancyUnitOfWork,
)
from incrementality_api.infrastructure.security.passwords import (
    Argon2PasswordHasher,
)
from incrementality_api.infrastructure.security.session_tokens import (
    SecureSessionTokenGenerator,
)
from incrementality_api.main import create_app

FIXED_NOW = datetime(
    2026,
    7,
    13,
    21,
    0,
    tzinfo=UTC,
)

OWNER_EMAIL = "owner@example.com"
OWNER_PASSWORD = "Secure-owner-password-123!"


class FixedClock:
    def now(self) -> datetime:
        return FIXED_NOW


@pytest.mark.asyncio
async def test_provisioned_owner_completes_authentication_lifecycle(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    def build_authentication_uow() -> SqlAlchemyAuthenticationUnitOfWork:
        return SqlAlchemyAuthenticationUnitOfWork(
            session_factory=tenancy_session_factory,
        )

    def build_tenancy_uow() -> SqlAlchemyTenancyUnitOfWork:
        return SqlAlchemyTenancyUnitOfWork(
            session_factory=tenancy_session_factory,
        )

    def override_provision_tenant() -> ProvisionTenant:
        return ProvisionTenant(
            unit_of_work=build_tenancy_uow(),
            password_hasher=Argon2PasswordHasher(),
        )

    def override_login() -> Login:
        return Login(
            unit_of_work=build_authentication_uow(),
            password_hasher=Argon2PasswordHasher(),
            token_generator=SecureSessionTokenGenerator(),
            clock=FixedClock(),
            session_lifetime=timedelta(hours=8),
        )

    def override_validate_session() -> ValidateSession:
        return ValidateSession(
            unit_of_work=build_authentication_uow(),
            token_hasher=SecureSessionTokenGenerator(),
            clock=FixedClock(),
        )

    def override_logout() -> Logout:
        return Logout(
            unit_of_work=build_authentication_uow(),
            token_hasher=SecureSessionTokenGenerator(),
            clock=FixedClock(),
        )

    application = create_app()

    application.dependency_overrides[get_provision_tenant] = override_provision_tenant

    application.dependency_overrides[get_login_service] = override_login

    application.dependency_overrides[get_validate_session_service] = override_validate_session

    application.dependency_overrides[get_logout_service] = override_logout

    transport = ASGITransport(app=application)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        provision_response = await client.post(
            "/api/v1/tenants",
            json={
                "organization_name": "Acme Media",
                "organization_slug": "acme-media",
                "workspace_name": "Marketing Science",
                "workspace_slug": "marketing-science",
                "owner_email": OWNER_EMAIL,
                "owner_display_name": "Tina Rincon",
                "owner_password": OWNER_PASSWORD,
            },
        )

        assert provision_response.status_code == 201

        owner_user_id = provision_response.json()["owner_user_id"]

        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": OWNER_EMAIL.upper(),
                "password": OWNER_PASSWORD,
            },
        )

        assert login_response.status_code == 200
        assert login_response.json()["user_id"] == owner_user_id
        assert login_response.json()["token_type"] == "bearer"

        raw_token = login_response.json()["session_token"]

        session_response = await client.get(
            "/api/v1/auth/session",
            headers={
                "Authorization": f"Bearer {raw_token}",
            },
        )

        assert session_response.status_code == 200
        assert session_response.json()["user_id"] == owner_user_id

        logout_response = await client.post(
            "/api/v1/auth/logout",
            headers={
                "Authorization": f"Bearer {raw_token}",
            },
        )

        assert logout_response.status_code == 204
        assert logout_response.content == b""

        rejected_response = await client.get(
            "/api/v1/auth/session",
            headers={
                "Authorization": f"Bearer {raw_token}",
            },
        )

        assert rejected_response.status_code == 401
        assert rejected_response.json() == {
            "detail": "Invalid or expired session.",
        }
        assert rejected_response.headers["www-authenticate"] == "Bearer"
