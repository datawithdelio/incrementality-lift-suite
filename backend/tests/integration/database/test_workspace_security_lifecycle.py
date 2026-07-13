from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from incrementality_api.api.dependencies.authentication import (
    get_login_service,
    get_logout_service,
)
from incrementality_api.api.dependencies.authorization import (
    RequireWorkspacePermission,
    get_authenticate_workspace_service,
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
from incrementality_api.application.authorization.authenticate_workspace import (
    AuthenticateWorkspaceAction,
    AuthorizedWorkspacePrincipal,
)
from incrementality_api.application.authorization.authorize_workspace import (
    AuthorizeWorkspaceAction,
)
from incrementality_api.application.tenancy.provision_tenant import (
    ProvisionTenant,
)
from incrementality_api.domain.authorization.permissions import (
    WorkspacePermission,
)
from incrementality_api.domain.authorization.policy import (
    WorkspaceAccessPolicy,
)
from incrementality_api.domain.tenancy.roles import WorkspaceRole
from incrementality_api.infrastructure.database.models.tenancy import (
    WorkspaceMembershipModel,
)
from incrementality_api.infrastructure.database.unit_of_work.authentication import (
    SqlAlchemyAuthenticationUnitOfWork,
)
from incrementality_api.infrastructure.database.unit_of_work.authorization import (
    SqlAlchemyAuthorizationUnitOfWork,
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
    23,
    0,
    tzinfo=UTC,
)

OWNER_EMAIL = "security-owner@example.com"
OWNER_PASSWORD = "Secure-owner-password-123!"


class FixedClock:
    def now(self) -> datetime:
        return FIXED_NOW


@pytest.mark.asyncio
async def test_complete_workspace_security_lifecycle(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    def build_authentication_uow() -> SqlAlchemyAuthenticationUnitOfWork:
        return SqlAlchemyAuthenticationUnitOfWork(
            session_factory=tenancy_session_factory,
        )

    def override_provision_tenant() -> ProvisionTenant:
        return ProvisionTenant(
            unit_of_work=SqlAlchemyTenancyUnitOfWork(
                session_factory=tenancy_session_factory,
            ),
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

    def override_logout() -> Logout:
        return Logout(
            unit_of_work=build_authentication_uow(),
            token_hasher=SecureSessionTokenGenerator(),
            clock=FixedClock(),
        )

    def override_authenticate_workspace() -> AuthenticateWorkspaceAction:
        return AuthenticateWorkspaceAction(
            session_validator=ValidateSession(
                unit_of_work=build_authentication_uow(),
                token_hasher=SecureSessionTokenGenerator(),
                clock=FixedClock(),
            ),
            workspace_authorizer=AuthorizeWorkspaceAction(
                unit_of_work=SqlAlchemyAuthorizationUnitOfWork(
                    session_factory=tenancy_session_factory,
                ),
                policy=WorkspaceAccessPolicy(),
            ),
        )

    application = create_app()

    require_manage_members = RequireWorkspacePermission(
        WorkspacePermission.MANAGE_MEMBERS,
    )

    @application.get(
        "/api/v1/workspaces/{workspace_id}/security-check",
    )
    async def security_check(
        principal: Annotated[
            AuthorizedWorkspacePrincipal,
            Depends(require_manage_members),
        ],
    ) -> dict[str, str]:
        return {
            "user_id": str(principal.user_id),
            "workspace_id": str(principal.workspace_id),
            "role": principal.role.value,
            "permission": principal.permission.value,
        }

    application.dependency_overrides[get_provision_tenant] = override_provision_tenant

    application.dependency_overrides[get_login_service] = override_login

    application.dependency_overrides[get_logout_service] = override_logout

    application.dependency_overrides[get_authenticate_workspace_service] = (
        override_authenticate_workspace
    )

    transport = ASGITransport(app=application)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        provision_response = await client.post(
            "/api/v1/tenants",
            json={
                "organization_name": "Security Media",
                "organization_slug": "security-media",
                "workspace_name": "Measurement",
                "workspace_slug": "measurement",
                "owner_email": OWNER_EMAIL,
                "owner_display_name": "Security Owner",
                "owner_password": OWNER_PASSWORD,
            },
        )

        assert provision_response.status_code == 201

        owner_user_id = UUID(
            provision_response.json()["owner_user_id"],
        )

        async with tenancy_session_factory() as session:
            membership = await session.scalar(
                select(WorkspaceMembershipModel).where(
                    WorkspaceMembershipModel.user_id == owner_user_id,
                )
            )

            assert membership is not None
            workspace_id = membership.workspace_id

        missing_token_response = await client.get(
            f"/api/v1/workspaces/{workspace_id}/security-check",
        )

        assert missing_token_response.status_code == 401
        assert missing_token_response.json() == {
            "detail": "Invalid or expired session.",
        }
        assert missing_token_response.headers["www-authenticate"] == "Bearer"

        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": OWNER_EMAIL.upper(),
                "password": OWNER_PASSWORD,
            },
        )

        assert login_response.status_code == 200

        raw_token = login_response.json()["session_token"]

        authorized_response = await client.get(
            f"/api/v1/workspaces/{workspace_id}/security-check",
            headers={
                "Authorization": f"Bearer {raw_token}",
            },
        )

        assert authorized_response.status_code == 200
        assert authorized_response.json() == {
            "user_id": str(owner_user_id),
            "workspace_id": str(workspace_id),
            "role": "owner",
            "permission": "manage_members",
        }

        async with (
            tenancy_session_factory() as session,
            session.begin(),
        ):
            membership = await session.scalar(
                select(WorkspaceMembershipModel).where(
                    WorkspaceMembershipModel.user_id == owner_user_id,
                )
            )

            assert membership is not None
            membership.role = WorkspaceRole.VIEWER.value

        forbidden_response = await client.get(
            f"/api/v1/workspaces/{workspace_id}/security-check",
            headers={
                "Authorization": f"Bearer {raw_token}",
            },
        )

        assert forbidden_response.status_code == 403
        assert forbidden_response.json() == {
            "detail": "Workspace access denied.",
        }

        logout_response = await client.post(
            "/api/v1/auth/logout",
            headers={
                "Authorization": f"Bearer {raw_token}",
            },
        )

        assert logout_response.status_code == 204

        revoked_response = await client.get(
            f"/api/v1/workspaces/{workspace_id}/security-check",
            headers={
                "Authorization": f"Bearer {raw_token}",
            },
        )

        assert revoked_response.status_code == 401
        assert revoked_response.json() == {
            "detail": "Invalid or expired session.",
        }
        assert revoked_response.headers["www-authenticate"] == ("Bearer")
