from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from incrementality_api.api.dependencies.authentication import (
    get_login_service,
)
from incrementality_api.api.dependencies.authorization import (
    get_authenticate_workspace_service,
)
from incrementality_api.api.dependencies.projects import (
    get_create_project_service,
)
from incrementality_api.api.dependencies.tenancy import (
    get_provision_tenant,
)
from incrementality_api.application.authentication.login import (
    Login,
)
from incrementality_api.application.authentication.validate_session import (
    ValidateSession,
)
from incrementality_api.application.authorization.authenticate_workspace import (
    AuthenticateWorkspaceAction,
)
from incrementality_api.application.authorization.authorize_workspace import (
    AuthorizeWorkspaceAction,
)
from incrementality_api.application.projects.create_project import (
    CreateProject,
)
from incrementality_api.application.tenancy.provision_tenant import (
    ProvisionTenant,
)
from incrementality_api.domain.authorization.policy import (
    WorkspaceAccessPolicy,
)
from incrementality_api.domain.tenancy.roles import WorkspaceRole
from incrementality_api.infrastructure.database.models.projects import (
    ProjectModel,
)
from incrementality_api.infrastructure.database.models.tenancy import (
    WorkspaceMembershipModel,
)
from incrementality_api.infrastructure.database.unit_of_work.authentication import (
    SqlAlchemyAuthenticationUnitOfWork,
)
from incrementality_api.infrastructure.database.unit_of_work.authorization import (
    SqlAlchemyAuthorizationUnitOfWork,
)
from incrementality_api.infrastructure.database.unit_of_work.projects import (
    SqlAlchemyProjectUnitOfWork,
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
    14,
    2,
    0,
    tzinfo=UTC,
)

OWNER_EMAIL = "project-owner@example.com"
OWNER_PASSWORD = "Secure-project-password-123!"


class FixedClock:
    def now(self) -> datetime:
        return FIXED_NOW


@pytest.mark.asyncio
async def test_complete_project_api_lifecycle(
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

    def override_create_project() -> CreateProject:
        return CreateProject(
            unit_of_work=SqlAlchemyProjectUnitOfWork(
                session_factory=tenancy_session_factory,
            )
        )

    application = create_app()

    application.dependency_overrides[get_provision_tenant] = override_provision_tenant

    application.dependency_overrides[get_login_service] = override_login

    application.dependency_overrides[get_authenticate_workspace_service] = (
        override_authenticate_workspace
    )

    application.dependency_overrides[get_create_project_service] = override_create_project

    transport = ASGITransport(app=application)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        provision_response = await client.post(
            "/api/v1/tenants",
            json={
                "organization_name": "Project Media",
                "organization_slug": "project-media",
                "workspace_name": "Measurement",
                "workspace_slug": "measurement",
                "owner_email": OWNER_EMAIL,
                "owner_display_name": "Project Owner",
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

        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": OWNER_EMAIL.upper(),
                "password": OWNER_PASSWORD,
            },
        )

        assert login_response.status_code == 200

        raw_token = login_response.json()["session_token"]

        create_response = await client.post(
            f"/api/v1/workspaces/{workspace_id}/projects",
            headers={
                "Authorization": f"Bearer {raw_token}",
            },
            json={
                "name": "Paid Search Incrementality",
                "slug": "paid-search-lift",
                "description": "Geo holdout measurement.",
            },
        )

        assert create_response.status_code == 201
        assert create_response.json()["workspace_id"] == str(workspace_id)
        assert create_response.json()["created_by_user_id"] == str(owner_user_id)
        assert create_response.json()["slug"] == ("paid-search-lift")
        assert create_response.json()["status"] == "active"

        duplicate_response = await client.post(
            f"/api/v1/workspaces/{workspace_id}/projects",
            headers={
                "Authorization": f"Bearer {raw_token}",
            },
            json={
                "name": "Duplicate Project",
                "slug": "PAID-SEARCH-LIFT",
            },
        )

        assert duplicate_response.status_code == 409
        assert duplicate_response.json() == {
            "detail": ("A project with this slug already exists in the workspace.")
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

        forbidden_response = await client.post(
            f"/api/v1/workspaces/{workspace_id}/projects",
            headers={
                "Authorization": f"Bearer {raw_token}",
            },
            json={
                "name": "Forbidden Project",
                "slug": "forbidden-project",
            },
        )

        assert forbidden_response.status_code == 403
        assert forbidden_response.json() == {
            "detail": "Workspace access denied.",
        }

    async with tenancy_session_factory() as session:
        project_count = await session.scalar(select(func.count()).select_from(ProjectModel))

        persisted_project = await session.scalar(
            select(ProjectModel).where(
                ProjectModel.workspace_id == workspace_id,
                ProjectModel.slug == "paid-search-lift",
            )
        )

    assert project_count == 1
    assert persisted_project is not None
    assert persisted_project.created_by_user_id == owner_user_id
