from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

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
    get_create_dataset_semantic_mapping_service,
    get_read_dataset_semantic_mapping_service,
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
from incrementality_api.application.datasets.manage_semantic_mapping import (
    CreateDatasetSemanticMapping,
    GetDatasetSemanticMapping,
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
from incrementality_api.infrastructure.database.models.dataset_columns import (
    DatasetColumnModel,
)
from incrementality_api.infrastructure.database.models.dataset_semantic_mappings import (
    DatasetMappingCovariateModel,
    DatasetSemanticMappingModel,
)
from incrementality_api.infrastructure.database.models.datasets import (
    DatasetModel,
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
    23,
    45,
    tzinfo=UTC,
)

OWNER_PASSWORD = "Secure-owner-password-123!"
PRIMARY_OWNER_EMAIL = "mapping-owner@example.com"
SECONDARY_OWNER_EMAIL = "other-mapping-owner@example.com"

DATASET_CHECKSUM = "f" * 64


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
            "owner_display_name": (f"{organization_name} Owner"),
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
        (f"/api/v1/workspaces/{workspace_id}/projects"),
        headers={
            "Authorization": (f"Bearer {raw_token}"),
        },
        json={
            "name": name,
            "slug": slug,
            "description": ("Semantic mapping lifecycle project."),
        },
    )

    assert response.status_code == 201

    return UUID(response.json()["id"])


def mapping_payload() -> dict[str, object]:
    return {
        "time_column": "Date",
        "unit_column": "Market",
        "treatment_column": "Treated",
        "outcome_column": "Revenue",
        "spend_column": "Spend",
        "covariate_columns": [
            "Promotion",
            "Seasonality",
        ],
        "treatment_value": "true",
        "control_value": "false",
    }


@pytest.mark.asyncio
async def test_complete_semantic_mapping_api_lifecycle(
    tenancy_session_factory: (async_sessionmaker[AsyncSession]),
) -> None:
    def build_authentication_uow() -> SqlAlchemyAuthenticationUnitOfWork:
        return SqlAlchemyAuthenticationUnitOfWork(
            session_factory=tenancy_session_factory,
        )

    def override_provision_tenant() -> ProvisionTenant:
        return ProvisionTenant(
            unit_of_work=(
                SqlAlchemyTenancyUnitOfWork(
                    session_factory=(tenancy_session_factory),
                )
            ),
            password_hasher=Argon2PasswordHasher(),
        )

    def override_login() -> Login:
        return Login(
            unit_of_work=build_authentication_uow(),
            password_hasher=Argon2PasswordHasher(),
            token_generator=(SecureSessionTokenGenerator()),
            clock=FixedClock(),
            session_lifetime=timedelta(hours=8),
        )

    def override_authenticate_workspace() -> AuthenticateWorkspaceAction:
        return AuthenticateWorkspaceAction(
            session_validator=ValidateSession(
                unit_of_work=(build_authentication_uow()),
                token_hasher=(SecureSessionTokenGenerator()),
                clock=FixedClock(),
            ),
            workspace_authorizer=(
                AuthorizeWorkspaceAction(
                    unit_of_work=(
                        SqlAlchemyAuthorizationUnitOfWork(
                            session_factory=(tenancy_session_factory),
                        )
                    ),
                    policy=WorkspaceAccessPolicy(),
                )
            ),
        )

    def override_create_project() -> CreateProject:
        return CreateProject(
            unit_of_work=(
                SqlAlchemyProjectUnitOfWork(
                    session_factory=(tenancy_session_factory),
                )
            ),
        )

    def override_register_dataset() -> RegisterDataset:
        return RegisterDataset(
            unit_of_work=(
                SqlAlchemyDatasetUnitOfWork(
                    session_factory=(tenancy_session_factory),
                )
            ),
            storage_key_builder=(DatasetObjectKeyBuilder()),
            maximum_upload_bytes=10_000_000,
        )

    def override_create_mapping() -> CreateDatasetSemanticMapping:
        return CreateDatasetSemanticMapping(
            unit_of_work=(
                SqlAlchemyDatasetUnitOfWork(
                    session_factory=(tenancy_session_factory),
                )
            ),
            clock=FixedClock(),
        )

    def override_read_mapping() -> GetDatasetSemanticMapping:
        return GetDatasetSemanticMapping(
            unit_of_work=(
                SqlAlchemyDatasetUnitOfWork(
                    session_factory=(tenancy_session_factory),
                )
            ),
        )

    application = create_app()

    application.dependency_overrides[get_provision_tenant] = override_provision_tenant

    application.dependency_overrides[get_login_service] = override_login

    application.dependency_overrides[get_authenticate_workspace_service] = (
        override_authenticate_workspace
    )

    application.dependency_overrides[get_create_project_service] = override_create_project

    application.dependency_overrides[get_register_dataset_service] = override_register_dataset

    application.dependency_overrides[get_create_dataset_semantic_mapping_service] = (
        override_create_mapping
    )

    application.dependency_overrides[get_read_dataset_semantic_mapping_service] = (
        override_read_mapping
    )

    transport = ASGITransport(
        app=application,
    )

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        (
            primary_owner_id,
            primary_workspace_id,
        ) = await provision_tenant(
            client,
            organization_name="Mapping Media",
            organization_slug="mapping-media",
            workspace_slug="mapping-measurement",
            owner_email=PRIMARY_OWNER_EMAIL,
        )

        (
            secondary_owner_id,
            secondary_workspace_id,
        ) = await provision_tenant(
            client,
            organization_name=("Other Mapping Media"),
            organization_slug=("other-mapping-media"),
            workspace_slug=("other-mapping-measurement"),
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
            name="Paid Search Mapping",
            slug="paid-search-mapping",
        )

        dataset_response = await client.post(
            (f"/api/v1/workspaces/{primary_workspace_id}/projects/{primary_project_id}/datasets"),
            headers={
                "Authorization": (f"Bearer {primary_token}"),
            },
            json={
                "source_filename": ("mapping-results.csv"),
                "media_type": "text/csv",
                "byte_size": 4096,
                "checksum_sha256": DATASET_CHECKSUM,
            },
        )

        assert dataset_response.status_code == 201

        dataset_id = UUID(dataset_response.json()["id"])

        async with (
            tenancy_session_factory() as session,
            session.begin(),
        ):
            dataset_model = await session.scalar(
                select(DatasetModel).where(
                    DatasetModel.id == dataset_id,
                )
            )

            assert dataset_model is not None

            dataset_model.status = "ready"
            dataset_model.uploaded_at = FIXED_NOW
            dataset_model.validation_started_at = FIXED_NOW
            dataset_model.validation_completed_at = FIXED_NOW
            dataset_model.row_count = 120
            dataset_model.column_count = 7
            dataset_model.failure_reason = None

            session.add_all(
                [
                    DatasetColumnModel(
                        dataset_id=dataset_id,
                        ordinal_position=1,
                        source_name="Date",
                        normalized_name="date",
                        inferred_type="date",
                        nullable=False,
                        missing_count=0,
                    ),
                    DatasetColumnModel(
                        dataset_id=dataset_id,
                        ordinal_position=2,
                        source_name="Market",
                        normalized_name="market",
                        inferred_type="string",
                        nullable=False,
                        missing_count=0,
                    ),
                    DatasetColumnModel(
                        dataset_id=dataset_id,
                        ordinal_position=3,
                        source_name="Treated",
                        normalized_name="treated",
                        inferred_type="boolean",
                        nullable=False,
                        missing_count=0,
                    ),
                    DatasetColumnModel(
                        dataset_id=dataset_id,
                        ordinal_position=4,
                        source_name="Revenue",
                        normalized_name="revenue",
                        inferred_type="float",
                        nullable=False,
                        missing_count=0,
                    ),
                    DatasetColumnModel(
                        dataset_id=dataset_id,
                        ordinal_position=5,
                        source_name="Spend",
                        normalized_name="spend",
                        inferred_type="float",
                        nullable=False,
                        missing_count=0,
                    ),
                    DatasetColumnModel(
                        dataset_id=dataset_id,
                        ordinal_position=6,
                        source_name="Promotion",
                        normalized_name="promotion",
                        inferred_type="string",
                        nullable=False,
                        missing_count=0,
                    ),
                    DatasetColumnModel(
                        dataset_id=dataset_id,
                        ordinal_position=7,
                        source_name="Seasonality",
                        normalized_name="seasonality",
                        inferred_type="float",
                        nullable=False,
                        missing_count=0,
                    ),
                ]
            )

        mapping_url = (
            f"/api/v1/workspaces/"
            f"{primary_workspace_id}"
            f"/projects/{primary_project_id}"
            f"/datasets/{dataset_id}"
            "/semantic-mappings"
        )

        first_response = await client.post(
            mapping_url,
            headers={
                "Authorization": (f"Bearer {primary_token}"),
            },
            json=mapping_payload(),
        )

        assert first_response.status_code == 201

        first_mapping = first_response.json()

        assert first_mapping["dataset_id"] == (str(dataset_id))
        assert first_mapping["created_by_user_id"] == (str(primary_owner_id))
        assert first_mapping["version"] == 1
        assert first_mapping["time_column"] == "date"
        assert first_mapping["unit_column"] == "market"
        assert first_mapping["treatment_column"] == ("treated")
        assert first_mapping["outcome_column"] == ("revenue")
        assert first_mapping["spend_column"] == "spend"
        assert first_mapping["covariate_columns"] == [
            "promotion",
            "seasonality",
        ]

        second_response = await client.post(
            mapping_url,
            headers={
                "Authorization": (f"Bearer {primary_token}"),
            },
            json=mapping_payload(),
        )

        assert second_response.status_code == 201
        assert second_response.json()["version"] == 2

        latest_response = await client.get(
            f"{mapping_url}/latest",
            headers={
                "Authorization": (f"Bearer {primary_token}"),
            },
        )

        assert latest_response.status_code == 200
        assert latest_response.json()["version"] == 2

        historical_response = await client.get(
            f"{mapping_url}/1",
            headers={
                "Authorization": (f"Bearer {primary_token}"),
            },
        )

        assert historical_response.status_code == 200
        assert historical_response.json()["version"] == 1
        assert historical_response.json()["id"] == (first_mapping["id"])

        invalid_payload = mapping_payload()
        invalid_payload["outcome_column"] = "Promotion"
        invalid_payload["covariate_columns"] = [
            "Seasonality",
        ]

        invalid_response = await client.post(
            mapping_url,
            headers={
                "Authorization": (f"Bearer {primary_token}"),
            },
            json=invalid_payload,
        )

        assert invalid_response.status_code == 422
        assert invalid_response.json() == {
            "detail": "Outcome column must be numeric.",
        }

        unauthenticated_response = await client.get(
            f"{mapping_url}/latest",
        )

        assert unauthenticated_response.status_code == 401

        forbidden_response = await client.get(
            f"{mapping_url}/latest",
            headers={
                "Authorization": (f"Bearer {secondary_token}"),
            },
        )

        assert forbidden_response.status_code == 403
        assert forbidden_response.json() == {
            "detail": "Workspace access denied.",
        }

        missing_scope_response = await client.get(
            (
                f"/api/v1/workspaces/"
                f"{primary_workspace_id}"
                f"/projects/{uuid4()}"
                f"/datasets/{dataset_id}"
                "/semantic-mappings/latest"
            ),
            headers={
                "Authorization": (f"Bearer {primary_token}"),
            },
        )

        assert missing_scope_response.status_code == 404
        assert missing_scope_response.json() == {
            "detail": ("Semantic mapping is unavailable."),
        }

        assert secondary_owner_id != primary_owner_id
        assert secondary_workspace_id != (primary_workspace_id)

    async with tenancy_session_factory() as session:
        mapping_count = await session.scalar(
            select(func.count()).select_from(
                DatasetSemanticMappingModel,
            )
        )

        covariate_count = await session.scalar(
            select(func.count()).select_from(
                DatasetMappingCovariateModel,
            )
        )

        mappings = tuple(
            (
                await session.scalars(
                    select(DatasetSemanticMappingModel).order_by(
                        DatasetSemanticMappingModel.version
                    )
                )
            ).all()
        )

    assert mapping_count == 2
    assert covariate_count == 4
    assert [mapping.version for mapping in mappings] == [1, 2]
    assert all(mapping.dataset_id == dataset_id for mapping in mappings)
