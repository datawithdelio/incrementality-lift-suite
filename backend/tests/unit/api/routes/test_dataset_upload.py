from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from incrementality_api.api.dependencies.authorization import (
    get_authenticate_workspace_service,
)
from incrementality_api.api.dependencies.datasets import (
    get_upload_dataset_service,
)
from incrementality_api.api.v1.routes.datasets import (
    router as datasets_router,
)
from incrementality_api.application.authorization.authenticate_workspace import (
    AuthorizedWorkspacePrincipal,
)
from incrementality_api.application.datasets.errors import (
    DatasetUnavailableError,
    DatasetUploadVerificationError,
)
from incrementality_api.application.datasets.upload_dataset import (
    UploadDatasetCommand,
)
from incrementality_api.domain.authorization.permissions import (
    WorkspacePermission,
)
from incrementality_api.domain.datasets.entities import Dataset
from incrementality_api.domain.datasets.errors import (
    InvalidDatasetTransitionError,
)
from incrementality_api.domain.tenancy.roles import WorkspaceRole

CONTENT = b"market,revenue\nnorth,250\n"
CHECKSUM = "a" * 64

UPLOADED_AT = datetime(
    2026,
    7,
    14,
    18,
    0,
    tzinfo=UTC,
)

SESSION_EXPIRES_AT = datetime(
    2026,
    7,
    15,
    2,
    0,
    tzinfo=UTC,
)


class StubAuthenticateWorkspaceAction:
    def __init__(
        self,
        principal: AuthorizedWorkspacePrincipal,
    ) -> None:
        self._principal = principal

    async def execute(
        self,
        *,
        raw_token: str,
        workspace_id: UUID,
        permission: WorkspacePermission,
    ) -> AuthorizedWorkspacePrincipal:
        del raw_token

        assert workspace_id == self._principal.workspace_id
        assert permission is (WorkspacePermission.MANAGE_DATASETS)

        return self._principal


class StubUploadDataset:
    def __init__(
        self,
        *,
        result: Dataset | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.received_command: UploadDatasetCommand | None = None
        self.received_content = b""

    async def execute(
        self,
        command: UploadDatasetCommand,
    ) -> Dataset:
        self.received_command = command

        content = bytearray()

        async for chunk in command.chunks:
            content.extend(chunk)

        self.received_content = bytes(content)

        if self._error is not None:
            raise self._error

        if self._result is None:
            raise AssertionError("Upload result was not configured.")

        return self._result


def build_principal(
    *,
    workspace_id: UUID,
    user_id: UUID,
) -> AuthorizedWorkspacePrincipal:
    return AuthorizedWorkspacePrincipal(
        session_id=uuid4(),
        user_id=user_id,
        workspace_id=workspace_id,
        membership_id=uuid4(),
        role=WorkspaceRole.ANALYST,
        permission=WorkspacePermission.MANAGE_DATASETS,
        session_expires_at=SESSION_EXPIRES_AT,
    )


def build_uploaded_dataset(
    *,
    workspace_id: UUID,
    project_id: UUID,
    user_id: UUID,
) -> Dataset:
    dataset = Dataset.register(
        workspace_id=workspace_id,
        project_id=project_id,
        created_by_user_id=user_id,
        source_filename="campaign-results.csv",
        storage_key=(
            f"workspaces/{workspace_id}/"
            f"projects/{project_id}/"
            f"datasets/{CHECKSUM}/"
            "campaign-results.csv"
        ),
        media_type="text/csv",
        byte_size=len(CONTENT),
        checksum_sha256=CHECKSUM,
    )

    return dataset.mark_uploaded(
        uploaded_at=UPLOADED_AT,
    )


def build_client(
    *,
    service: StubUploadDataset,
    principal: AuthorizedWorkspacePrincipal,
) -> TestClient:
    application = FastAPI()
    application.include_router(datasets_router)

    application.dependency_overrides[get_upload_dataset_service] = lambda: service

    application.dependency_overrides[get_authenticate_workspace_service] = lambda: (
        StubAuthenticateWorkspaceAction(
            principal,
        )
    )

    return TestClient(
        application,
        raise_server_exceptions=False,
    )


def upload_url(
    *,
    workspace_id: UUID,
    project_id: UUID,
    dataset_id: UUID,
) -> str:
    return f"/workspaces/{workspace_id}/projects/{project_id}/datasets/{dataset_id}/content"


def test_uploads_binary_dataset_content() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()

    dataset = build_uploaded_dataset(
        workspace_id=workspace_id,
        project_id=project_id,
        user_id=user_id,
    )

    service = StubUploadDataset(
        result=dataset,
    )

    client = build_client(
        service=service,
        principal=build_principal(
            workspace_id=workspace_id,
            user_id=user_id,
        ),
    )

    response = client.put(
        upload_url(
            workspace_id=workspace_id,
            project_id=project_id,
            dataset_id=dataset.id,
        ),
        headers={
            "Authorization": "Bearer valid-token",
            "Content-Type": "text/csv",
        },
        content=CONTENT,
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(dataset.id)
    assert response.json()["status"] == "uploaded"
    assert datetime.fromisoformat(response.json()["uploaded_at"]) == UPLOADED_AT

    assert service.received_command is not None
    assert service.received_command.workspace_id == (workspace_id)
    assert service.received_command.project_id == project_id
    assert service.received_command.dataset_id == dataset.id
    assert service.received_content == CONTENT


def test_unavailable_dataset_returns_404() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    dataset_id = uuid4()

    service = StubUploadDataset(error=DatasetUnavailableError("Dataset is unavailable."))

    client = build_client(
        service=service,
        principal=build_principal(
            workspace_id=workspace_id,
            user_id=uuid4(),
        ),
    )

    response = client.put(
        upload_url(
            workspace_id=workspace_id,
            project_id=project_id,
            dataset_id=dataset_id,
        ),
        headers={
            "Authorization": "Bearer valid-token",
        },
        content=CONTENT,
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Dataset is unavailable.",
    }


def test_upload_verification_failure_returns_422() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    dataset_id = uuid4()

    service = StubUploadDataset(
        error=DatasetUploadVerificationError(
            "Uploaded dataset checksum does not match the registered metadata."
        )
    )

    client = build_client(
        service=service,
        principal=build_principal(
            workspace_id=workspace_id,
            user_id=uuid4(),
        ),
    )

    response = client.put(
        upload_url(
            workspace_id=workspace_id,
            project_id=project_id,
            dataset_id=dataset_id,
        ),
        headers={
            "Authorization": "Bearer valid-token",
        },
        content=CONTENT,
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": ("Uploaded dataset checksum does not match the registered metadata.")
    }


def test_repeated_upload_returns_409() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    dataset_id = uuid4()

    service = StubUploadDataset(
        error=InvalidDatasetTransitionError(
            "Dataset in status 'uploaded' cannot be marked uploaded."
        )
    )

    client = build_client(
        service=service,
        principal=build_principal(
            workspace_id=workspace_id,
            user_id=uuid4(),
        ),
    )

    response = client.put(
        upload_url(
            workspace_id=workspace_id,
            project_id=project_id,
            dataset_id=dataset_id,
        ),
        headers={
            "Authorization": "Bearer valid-token",
        },
        content=CONTENT,
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": ("Dataset in status 'uploaded' cannot be marked uploaded.")
    }
