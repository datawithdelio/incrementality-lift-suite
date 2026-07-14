import asyncio
import os
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import cast
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from mypy_boto3_s3 import S3Client
from sqlalchemy import select
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
    get_upload_dataset_service,
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
from incrementality_api.application.datasets.begin_validation import (
    BeginDatasetValidation,
)
from incrementality_api.application.datasets.complete_validation import (
    MarkDatasetFailed,
    MarkDatasetReady,
)
from incrementality_api.application.datasets.register_dataset import (
    RegisterDataset,
)
from incrementality_api.application.datasets.upload_dataset import (
    UploadDataset,
)
from incrementality_api.application.datasets.validate_dataset import (
    ValidateDataset,
    ValidateDatasetCommand,
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
from incrementality_api.infrastructure.storage.s3_clients import (
    create_s3_compatible_client,
)
from incrementality_api.infrastructure.storage.s3_dataset_objects import (
    S3DatasetObjectStorage,
)
from incrementality_api.infrastructure.validation.csv_datasets import (
    CsvDatasetContentValidator,
)
from incrementality_api.main import create_app

RUN_S3_INTEGRATION = os.getenv("RUN_S3_INTEGRATION") == "1"

S3_ENDPOINT_URL = os.getenv(
    "S3_INTEGRATION_ENDPOINT_URL",
    "http://localhost:5001",
)

CONTENT = b"market,revenue\nnorth,250\n"
CONTENT_CHECKSUM = sha256(CONTENT).hexdigest()

OWNER_EMAIL = "http-upload-owner@example.com"
OWNER_PASSWORD = "Secure-owner-password-123!"

FIXED_NOW = datetime(
    2026,
    7,
    14,
    20,
    0,
    tzinfo=UTC,
)


class FixedClock:
    def now(self) -> datetime:
        return FIXED_NOW


@pytest.mark.skipif(
    not RUN_S3_INTEGRATION,
    reason="S3 integration tests are disabled.",
)
@pytest.mark.asyncio
async def test_complete_http_dataset_upload_lifecycle(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    raw_s3_client = create_s3_compatible_client(
        endpoint_url=S3_ENDPOINT_URL,
        access_key="incrementality",
        secret_key="incrementality-secret",
        region="us-east-1",
    )

    s3_client = cast(
        S3Client,
        raw_s3_client,
    )

    bucket_name = f"incrementality-http-{uuid4().hex}"

    await asyncio.to_thread(
        s3_client.create_bucket,
        Bucket=bucket_name,
    )

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

    def override_upload_dataset() -> UploadDataset:
        return UploadDataset(
            unit_of_work=SqlAlchemyDatasetUnitOfWork(
                session_factory=tenancy_session_factory,
            ),
            object_storage=S3DatasetObjectStorage(
                client=raw_s3_client,
                bucket_name=bucket_name,
                spool_max_memory_bytes=8,
            ),
            clock=FixedClock(),
        )

    application = create_app()

    application.dependency_overrides[get_provision_tenant] = override_provision_tenant

    application.dependency_overrides[get_login_service] = override_login

    application.dependency_overrides[get_authenticate_workspace_service] = (
        override_authenticate_workspace
    )

    application.dependency_overrides[get_create_project_service] = override_create_project

    application.dependency_overrides[get_register_dataset_service] = override_register_dataset

    application.dependency_overrides[get_upload_dataset_service] = override_upload_dataset

    transport = ASGITransport(
        app=application,
    )

    storage_key: str | None = None

    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            provision_response = await client.post(
                "/api/v1/tenants",
                json={
                    "organization_name": "HTTP Upload Media",
                    "organization_slug": "http-upload-media",
                    "workspace_name": "Measurement",
                    "workspace_slug": "measurement",
                    "owner_email": OWNER_EMAIL,
                    "owner_display_name": "HTTP Upload Owner",
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

            project_response = await client.post(
                (f"/api/v1/workspaces/{workspace_id}/projects"),
                headers={
                    "Authorization": (f"Bearer {raw_token}"),
                },
                json={
                    "name": "HTTP Upload Project",
                    "slug": "http-upload-project",
                },
            )

            assert project_response.status_code == 201

            project_id = UUID(
                project_response.json()["id"],
            )

            registration_response = await client.post(
                (f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/datasets"),
                headers={
                    "Authorization": (f"Bearer {raw_token}"),
                },
                json={
                    "source_filename": "results.csv",
                    "media_type": "text/csv",
                    "byte_size": len(CONTENT),
                    "checksum_sha256": CONTENT_CHECKSUM,
                },
            )

            assert registration_response.status_code == 201

            dataset_id = UUID(
                registration_response.json()["id"],
            )

            storage_key = registration_response.json()["storage_key"]

            upload_response = await client.put(
                (
                    f"/api/v1/workspaces/{workspace_id}"
                    f"/projects/{project_id}"
                    f"/datasets/{dataset_id}/content"
                ),
                headers={
                    "Authorization": (f"Bearer {raw_token}"),
                    "Content-Type": "text/csv",
                },
                content=CONTENT,
            )

            assert upload_response.status_code == 200

            uploaded_payload = upload_response.json()

            assert uploaded_payload["id"] == str(dataset_id)
            assert uploaded_payload["status"] == "uploaded"
            assert datetime.fromisoformat(uploaded_payload["uploaded_at"]) == FIXED_NOW

            repeated_response = await client.put(
                (
                    f"/api/v1/workspaces/{workspace_id}"
                    f"/projects/{project_id}"
                    f"/datasets/{dataset_id}/content"
                ),
                headers={
                    "Authorization": (f"Bearer {raw_token}"),
                    "Content-Type": "text/csv",
                },
                content=CONTENT,
            )

            assert repeated_response.status_code == 409

        async with tenancy_session_factory() as session:
            persisted_dataset = await session.scalar(
                select(DatasetModel).where(
                    DatasetModel.id == dataset_id,
                )
            )

        assert persisted_dataset is not None
        assert persisted_dataset.status == "uploaded"
        assert persisted_dataset.uploaded_at == FIXED_NOW

        object_response = await asyncio.to_thread(
            s3_client.get_object,
            Bucket=bucket_name,
            Key=storage_key,
        )

        stored_content = await asyncio.to_thread(
            object_response["Body"].read,
        )

        assert stored_content == CONTENT
        assert object_response["ContentType"] == "text/csv"

        validated_dataset = await ValidateDataset(
            begin_validation=BeginDatasetValidation(
                unit_of_work=SqlAlchemyDatasetUnitOfWork(
                    session_factory=tenancy_session_factory,
                ),
                clock=FixedClock(),
            ),
            object_storage=S3DatasetObjectStorage(
                client=raw_s3_client,
                bucket_name=bucket_name,
                spool_max_memory_bytes=8,
            ),
            content_validator=CsvDatasetContentValidator(
                spool_max_memory_bytes=8,
            ),
            mark_ready=MarkDatasetReady(
                unit_of_work=SqlAlchemyDatasetUnitOfWork(
                    session_factory=tenancy_session_factory,
                ),
                clock=FixedClock(),
            ),
            mark_failed=MarkDatasetFailed(
                unit_of_work=SqlAlchemyDatasetUnitOfWork(
                    session_factory=tenancy_session_factory,
                ),
                clock=FixedClock(),
            ),
            read_chunk_size=7,
        ).execute(
            ValidateDatasetCommand(
                workspace_id=workspace_id,
                project_id=project_id,
                dataset_id=dataset_id,
            )
        )

        assert validated_dataset.status.value == "ready"
        assert validated_dataset.row_count == 1
        assert validated_dataset.column_count == 2
        assert validated_dataset.failure_reason is None
        assert validated_dataset.validation_started_at == FIXED_NOW
        assert validated_dataset.validation_completed_at == FIXED_NOW

        async with tenancy_session_factory() as session:
            validated_model = await session.scalar(
                select(DatasetModel).where(
                    DatasetModel.id == dataset_id,
                )
            )

        assert validated_model is not None
        assert validated_model.status == "ready"
        assert validated_model.row_count == 1
        assert validated_model.column_count == 2
        assert validated_model.failure_reason is None
        assert validated_model.validation_started_at == FIXED_NOW
        assert validated_model.validation_completed_at == FIXED_NOW
    finally:
        if storage_key is not None:
            await asyncio.to_thread(
                s3_client.delete_object,
                Bucket=bucket_name,
                Key=storage_key,
            )

        await asyncio.to_thread(
            s3_client.delete_bucket,
            Bucket=bucket_name,
        )
