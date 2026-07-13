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
from incrementality_api.api.dependencies.datasets import (
    get_register_dataset_service,
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
from incrementality_api.application.datasets.register_dataset import (
    RegisterDataset,
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
from incrementality_api.infrastructure.database.models.datasets import (
    DatasetModel,
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
from incrementality_api.infrastructure.database.unit_of_work.datasets import (
    SqlAlchemyDatasetUnitOfWork,
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
from incrementality_api.infrastructure.storage.dataset_keys import (
    DatasetObjectKeyBuilder,
)
from incrementality_api.main import create_app

FIXED_NOW = datetime(
    2026,
    7,
    14,
    4,
    0,
    tzinfo=UTC,
)

OWNER_PASSWORD = "Secure-owner-password-123!"
PRIMARY_OWNER_EMAIL = "dataset-owner@example.com"
SECONDARY_OWNER_EMAIL = "other-dataset-owner@example.com"

DATASET_CHECKSUM = "c" * 64
FORBIDDEN_DATASET_CHECKSUM = "d" * 64


class FixedClock:
    def now(self) -> datetime:
        return FIXED_NOW


async def provision_tenant(
    client: AsyncClient,
    *,
    organization_name: str,
    organization_slug: str,
    workspace_slug: str,
    owner_email: str,
) -> tuple[UUID, UUID]:
    response = await client.post(
        "/api/v1/tenants",
        json={
            "organization_name": organization_name,
            "organization_slug": organization_slug,
            "workspace_name": "Measurement",
            "workspace_slug": workspace_slug,
            "owner_email": owner_email,
            "owner_display_name": f"{organization_name} Owner",
            "owner_password": OWNER_PASSWORD,
        },
    )

    assert response.status_code == 201

    payload = response.json()

    return (
        UUID(payload["owner_user_id"]),
        UUID(payload["workspace_id"]),
    )


async def login_owner(
    client: AsyncClient,
    *,
    email: str,
) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": email.upper(),
            "password": OWNER_PASSWORD,
        },
    )

    assert response.status_code == 200

    return str(response.json()["session_token"])


async def create_project(
    client: AsyncClient,
    *,
    workspace_id: UUID,
    raw_token: str,
    name: str,
    slug: str,
) -> UUID:
    response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/projects",
        headers={
            "Authorization": f"Bearer {raw_token}",
        },
        json={
            "name": name,
            "slug": slug,
            "description": "Dataset lifecycle project.",
        },
    )

    assert response.status_code == 201

    return UUID(response.json()["id"])


@pytest.mark.asyncio
async def test_complete_dataset_api_lifecycle(
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
            ),
        )

    def override_register_dataset() -> RegisterDataset:
        return RegisterDataset(
            unit_of_work=SqlAlchemyDatasetUnitOfWork(
                session_factory=tenancy_session_factory,
            ),
            storage_key_builder=DatasetObjectKeyBuilder(),
            maximum_upload_bytes=10_000_000,
        )

    application = create_app()

    application.dependency_overrides[get_provision_tenant] = override_provision_tenant

    application.dependency_overrides[get_login_service] = override_login

    application.dependency_overrides[get_authenticate_workspace_service] = (
        override_authenticate_workspace
    )

    application.dependency_overrides[get_create_project_service] = override_create_project

    application.dependency_overrides[get_register_dataset_service] = override_register_dataset

    transport = ASGITransport(
        app=application,
    )

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        primary_owner_id, primary_workspace_id = await provision_tenant(
            client,
            organization_name="Dataset Media",
            organization_slug="dataset-media",
            workspace_slug="dataset-measurement",
            owner_email=PRIMARY_OWNER_EMAIL,
        )

        secondary_owner_id, secondary_workspace_id = await provision_tenant(
            client,
            organization_name="Other Dataset Media",
            organization_slug="other-dataset-media",
            workspace_slug="other-measurement",
            owner_email=SECONDARY_OWNER_EMAIL,
        )

        primary_token = await login_owner(
            client,
            email=PRIMARY_OWNER_EMAIL,
        )

        secondary_token = await login_owner(
            client,
            email=SECONDARY_OWNER_EMAIL,
        )

        primary_project_id = await create_project(
            client,
            workspace_id=primary_workspace_id,
            raw_token=primary_token,
            name="Paid Search Incrementality",
            slug="paid-search-incrementality",
        )

        secondary_project_id = await create_project(
            client,
            workspace_id=secondary_workspace_id,
            raw_token=secondary_token,
            name="Other Workspace Project",
            slug="other-workspace-project",
        )

        dataset_payload = {
            "source_filename": "campaign-results.csv",
            "media_type": "text/csv",
            "byte_size": 4096,
            "checksum_sha256": DATASET_CHECKSUM,
        }

        register_response = await client.post(
            (f"/api/v1/workspaces/{primary_workspace_id}/projects/{primary_project_id}/datasets"),
            headers={
                "Authorization": f"Bearer {primary_token}",
            },
            json=dataset_payload,
        )

        assert register_response.status_code == 201

        registered_dataset = register_response.json()
        dataset_id = UUID(registered_dataset["id"])

        assert registered_dataset["workspace_id"] == str(primary_workspace_id)
        assert registered_dataset["project_id"] == str(primary_project_id)
        assert registered_dataset["created_by_user_id"] == str(primary_owner_id)
        assert registered_dataset["status"] == "pending_upload"
        assert registered_dataset["source_filename"] == ("campaign-results.csv")
        assert registered_dataset["checksum_sha256"] == (DATASET_CHECKSUM)
        assert registered_dataset["storage_key"] == (
            f"workspaces/{primary_workspace_id}/"
            f"projects/{primary_project_id}/"
            f"datasets/{DATASET_CHECKSUM}/"
            "campaign-results.csv"
        )

        duplicate_response = await client.post(
            (f"/api/v1/workspaces/{primary_workspace_id}/projects/{primary_project_id}/datasets"),
            headers={
                "Authorization": f"Bearer {primary_token}",
            },
            json=dataset_payload,
        )

        assert duplicate_response.status_code == 409
        assert duplicate_response.json() == {
            "detail": ("Dataset metadata conflicts with an existing record.")
        }

        cross_workspace_response = await client.post(
            (f"/api/v1/workspaces/{primary_workspace_id}/projects/{secondary_project_id}/datasets"),
            headers={
                "Authorization": f"Bearer {primary_token}",
            },
            json={
                **dataset_payload,
                "source_filename": "cross-workspace.csv",
                "checksum_sha256": "e" * 64,
            },
        )

        assert cross_workspace_response.status_code == 404
        assert cross_workspace_response.json() == {
            "detail": "Dataset project is unavailable.",
        }

        async with (
            tenancy_session_factory() as session,
            session.begin(),
        ):
            membership = await session.scalar(
                select(WorkspaceMembershipModel).where(
                    WorkspaceMembershipModel.workspace_id == primary_workspace_id,
                    WorkspaceMembershipModel.user_id == primary_owner_id,
                )
            )

            assert membership is not None
            membership.role = WorkspaceRole.VIEWER.value

        forbidden_response = await client.post(
            (f"/api/v1/workspaces/{primary_workspace_id}/projects/{primary_project_id}/datasets"),
            headers={
                "Authorization": f"Bearer {primary_token}",
            },
            json={
                **dataset_payload,
                "source_filename": "forbidden.csv",
                "checksum_sha256": (FORBIDDEN_DATASET_CHECKSUM),
            },
        )

        assert forbidden_response.status_code == 403
        assert forbidden_response.json() == {
            "detail": "Workspace access denied.",
        }

        assert secondary_owner_id != primary_owner_id

    async with tenancy_session_factory() as session:
        dataset_count = await session.scalar(
            select(func.count()).select_from(
                DatasetModel,
            )
        )

        persisted_dataset = await session.scalar(
            select(DatasetModel).where(
                DatasetModel.id == dataset_id,
            )
        )

    assert dataset_count == 1
    assert persisted_dataset is not None
    assert persisted_dataset.workspace_id == (primary_workspace_id)
    assert persisted_dataset.project_id == primary_project_id
    assert persisted_dataset.created_by_user_id == (primary_owner_id)
    assert persisted_dataset.status == "pending_upload"
    assert persisted_dataset.byte_size == 4096
    assert persisted_dataset.checksum_sha256 == (DATASET_CHECKSUM)
