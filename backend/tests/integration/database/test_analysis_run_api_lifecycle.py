from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from incrementality_api.api.dependencies.analysis_runs import (
    get_analysis_run_service,
    get_queue_analysis_run_service,
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
from incrementality_api.application.analysis_runs.manage_analysis_runs import (
    GetAnalysisRun,
    QueueAnalysisRun,
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
from incrementality_api.domain.tenancy.roles import (
    WorkspaceRole,
)
from incrementality_api.infrastructure.database.models.analysis_runs import (
    AnalysisRunModel,
)
from incrementality_api.infrastructure.database.models.dataset_columns import (
    DatasetColumnModel,
)
from incrementality_api.infrastructure.database.models.dataset_semantic_mappings import (
    DatasetSemanticMappingModel,
)
from incrementality_api.infrastructure.database.models.datasets import (
    DatasetModel,
)
from incrementality_api.infrastructure.database.models.tenancy import (
    WorkspaceMembershipModel,
)
from incrementality_api.infrastructure.database.unit_of_work.analysis_runs import (
    SqlAlchemyAnalysisRunUnitOfWork,
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
from incrementality_api.infrastructure.estimation.runtime_versions import (
    StatisticalRuntimeVersionProvider,
)
from incrementality_api.infrastructure.security.passwords import (
    Argon2PasswordHasher,
)
from incrementality_api.infrastructure.security.session_tokens import (
    SecureSessionTokenGenerator,
)
from incrementality_api.main import create_app

APPLICATION_VERSION = "0.1.0"
SOURCE_REVISION = "a" * 40

FIXED_NOW = datetime(
    2026,
    7,
    14,
    21,
    0,
    tzinfo=UTC,
)

OWNER_PASSWORD = "Secure-owner-password-123!"
PRIMARY_OWNER_EMAIL = "analysis-owner@example.com"
SECONDARY_OWNER_EMAIL = "other-analysis-owner@example.com"


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
) -> UUID:
    response = await client.post(
        (f"/api/v1/workspaces/{workspace_id}/projects"),
        headers={
            "Authorization": f"Bearer {raw_token}",
        },
        json={
            "name": "Paid Search Incrementality",
            "slug": "paid-search-incrementality",
            "description": ("Authenticated analysis-run test."),
        },
    )

    assert response.status_code == 201

    return UUID(response.json()["id"])


async def seed_ready_dataset_and_mapping(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    workspace_id: UUID,
    project_id: UUID,
    owner_user_id: UUID,
) -> tuple[UUID, UUID]:
    dataset_id = uuid4()
    mapping_id = uuid4()

    async with (
        session_factory() as session,
        session.begin(),
    ):
        session.add(
            DatasetModel(
                id=dataset_id,
                workspace_id=workspace_id,
                project_id=project_id,
                created_by_user_id=owner_user_id,
                source_filename=("analysis-results.csv"),
                storage_key=(
                    f"workspaces/{workspace_id}/"
                    f"projects/{project_id}/"
                    f"datasets/{dataset_id}/"
                    "analysis-results.csv"
                ),
                media_type="text/csv",
                byte_size=4_096,
                checksum_sha256=(dataset_id.hex * 2),
                status="ready",
                uploaded_at=FIXED_NOW,
                validation_started_at=FIXED_NOW,
                validation_completed_at=FIXED_NOW,
                row_count=100,
                column_count=4,
                failure_reason=None,
                created_at=FIXED_NOW,
                updated_at=FIXED_NOW,
            )
        )

        await session.flush()

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
            ]
        )

        await session.flush()

        session.add(
            DatasetSemanticMappingModel(
                id=mapping_id,
                dataset_id=dataset_id,
                created_by_user_id=owner_user_id,
                version=1,
                time_column="date",
                unit_column="market",
                treatment_column="treated",
                outcome_column="revenue",
                spend_column=None,
                treatment_value="true",
                control_value="false",
                created_at=FIXED_NOW,
                updated_at=FIXED_NOW,
            )
        )

    return dataset_id, mapping_id


@pytest.mark.asyncio
async def test_complete_authenticated_analysis_run_api_lifecycle(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    def build_authentication_uow() -> SqlAlchemyAuthenticationUnitOfWork:
        return SqlAlchemyAuthenticationUnitOfWork(
            session_factory=(tenancy_session_factory),
        )

    def override_provision_tenant() -> ProvisionTenant:
        return ProvisionTenant(
            unit_of_work=(
                SqlAlchemyTenancyUnitOfWork(
                    session_factory=(tenancy_session_factory),
                )
            ),
            password_hasher=(Argon2PasswordHasher()),
        )

    def override_login() -> Login:
        return Login(
            unit_of_work=(build_authentication_uow()),
            password_hasher=(Argon2PasswordHasher()),
            token_generator=(SecureSessionTokenGenerator()),
            clock=FixedClock(),
            session_lifetime=timedelta(
                hours=8,
            ),
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

    def override_queue_analysis_run() -> QueueAnalysisRun:
        return QueueAnalysisRun(
            unit_of_work=(
                SqlAlchemyAnalysisRunUnitOfWork(
                    session_factory=(tenancy_session_factory),
                )
            ),
            clock=FixedClock(),
            application_version=APPLICATION_VERSION,
            source_revision=SOURCE_REVISION,
            statistical_runtime_versions=StatisticalRuntimeVersionProvider(),
        )

    def override_get_analysis_run() -> GetAnalysisRun:
        return GetAnalysisRun(
            unit_of_work=(
                SqlAlchemyAnalysisRunUnitOfWork(
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

    application.dependency_overrides[get_queue_analysis_run_service] = override_queue_analysis_run

    application.dependency_overrides[get_analysis_run_service] = override_get_analysis_run

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
            organization_name=("Analysis Media"),
            organization_slug=("analysis-media"),
            workspace_slug=("analysis-measurement"),
            owner_email=PRIMARY_OWNER_EMAIL,
        )

        (
            secondary_owner_id,
            secondary_workspace_id,
        ) = await provision_tenant(
            client,
            organization_name=("Other Analysis Media"),
            organization_slug=("other-analysis-media"),
            workspace_slug=("other-analysis-measurement"),
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

        project_id = await create_project(
            client,
            workspace_id=primary_workspace_id,
            raw_token=primary_token,
        )

        (
            dataset_id,
            mapping_id,
        ) = await seed_ready_dataset_and_mapping(
            tenancy_session_factory,
            workspace_id=primary_workspace_id,
            project_id=project_id,
            owner_user_id=primary_owner_id,
        )

        endpoint = f"/api/v1/workspaces/{primary_workspace_id}/projects/{project_id}/analysis-runs"

        request_payload = {
            "dataset_id": str(dataset_id),
            "semantic_mapping_version": 1,
            "estimator_type": ("difference_in_differences"),
            "estimator_version": "did-v1",
            "configuration": {
                "cluster_by": "unit",
                "alpha": 0.05,
                "analysis_start_date": "2026-01-01",
                "analysis_end_date": "2026-01-31",
                "intervention_date": "2026-01-15",
            },
        }

        unauthenticated_response = await client.post(
            endpoint,
            json=request_payload,
        )

        assert unauthenticated_response.status_code == 401
        assert unauthenticated_response.json() == {
            "detail": ("Invalid or expired session."),
        }

        queue_response = await client.post(
            endpoint,
            headers={
                "Authorization": (f"Bearer {primary_token}"),
            },
            json=request_payload,
        )

        assert queue_response.status_code == 201

        queued_payload = queue_response.json()
        analysis_run_id = UUID(queued_payload["id"])

        assert queued_payload["workspace_id"] == str(primary_workspace_id)

        assert queued_payload["project_id"] == str(project_id)

        assert queued_payload["dataset_id"] == str(dataset_id)

        assert queued_payload["semantic_mapping_id"] == str(mapping_id)

        assert queued_payload["semantic_mapping_version"] == 1

        assert queued_payload["created_by_user_id"] == str(primary_owner_id)

        assert queued_payload["estimator_type"] == "difference_in_differences"

        assert queued_payload["estimator_version"] == "did-v1"

        assert queued_payload["configuration"] == {
            "alpha": 0.05,
            "analysis_start_date": "2026-01-01",
            "analysis_end_date": "2026-01-31",
            "cluster_by": "unit",
            "intervention_date": "2026-01-15",
            "pre_period_start_date": "2026-01-01",
            "pre_period_end_date": "2026-01-14",
            "post_period_start_date": "2026-01-15",
            "post_period_end_date": "2026-01-31",
        }

        assert queued_payload["status"] == ("queued")

        read_endpoint = f"{endpoint}/{analysis_run_id}"

        read_response = await client.get(
            read_endpoint,
            headers={
                "Authorization": (f"Bearer {primary_token}"),
            },
        )

        assert read_response.status_code == 200
        assert read_response.json() == (queued_payload)

        cross_workspace_response = await client.get(
            read_endpoint,
            headers={
                "Authorization": (f"Bearer {secondary_token}"),
            },
        )

        assert cross_workspace_response.status_code == 403
        assert cross_workspace_response.json() == {
            "detail": "Workspace access denied.",
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

        viewer_read_response = await client.get(
            read_endpoint,
            headers={
                "Authorization": (f"Bearer {primary_token}"),
            },
        )

        assert viewer_read_response.status_code == 200

        viewer_queue_response = await client.post(
            endpoint,
            headers={
                "Authorization": (f"Bearer {primary_token}"),
            },
            json=request_payload,
        )

        assert viewer_queue_response.status_code == 403
        assert viewer_queue_response.json() == {
            "detail": "Workspace access denied.",
        }

        assert secondary_owner_id != primary_owner_id
        assert secondary_workspace_id != primary_workspace_id

    async with tenancy_session_factory() as session:
        run_count = await session.scalar(select(func.count()).select_from(AnalysisRunModel))

        persisted_run = await session.scalar(
            select(AnalysisRunModel).where(
                AnalysisRunModel.id == analysis_run_id,
            )
        )

    assert run_count == 1
    assert persisted_run is not None

    assert persisted_run.workspace_id == (primary_workspace_id)
    assert persisted_run.project_id == (project_id)
    assert persisted_run.dataset_id == (dataset_id)
    assert persisted_run.semantic_mapping_id == (mapping_id)
    assert persisted_run.semantic_mapping_version == 1
    assert persisted_run.created_by_user_id == (primary_owner_id)
    assert persisted_run.status == "queued"
    assert persisted_run.estimator_type == ("difference_in_differences")
    assert persisted_run.analysis_period_snapshot_json is not None
