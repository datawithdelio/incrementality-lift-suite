from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from incrementality_api.api.dependencies.authorization import (
    get_authenticate_workspace_service,
)
from incrementality_api.api.dependencies.datasets import (
    get_register_dataset_service,
)
from incrementality_api.api.v1.routes.datasets import (
    router as datasets_router,
)
from incrementality_api.application.authorization.authenticate_workspace import (
    AuthorizedWorkspacePrincipal,
)
from incrementality_api.application.datasets.errors import (
    DatasetPersistenceConflictError,
    DatasetProjectUnavailableError,
    DatasetTooLargeError,
)
from incrementality_api.application.datasets.register_dataset import (
    RegisterDatasetCommand,
)
from incrementality_api.domain.authorization.permissions import (
    WorkspacePermission,
)
from incrementality_api.domain.datasets.entities import Dataset
from incrementality_api.domain.datasets.errors import (
    InvalidDatasetError,
)
from incrementality_api.domain.tenancy.roles import WorkspaceRole

EXPIRES_AT = datetime(
    2026,
    7,
    14,
    12,
    0,
    tzinfo=UTC,
)

CHECKSUM = "a" * 64


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
        del raw_token, workspace_id

        assert permission is (WorkspacePermission.MANAGE_DATASETS)

        return self._principal


class StubRegisterDataset:
    def __init__(
        self,
        *,
        result: Dataset | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.received_command: RegisterDatasetCommand | None = None

    async def execute(
        self,
        command: RegisterDatasetCommand,
    ) -> Dataset:
        self.received_command = command

        if self._error is not None:
            raise self._error

        if self._result is None:
            raise AssertionError("Dataset result was not configured.")

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
        session_expires_at=EXPIRES_AT,
    )


def build_client(
    *,
    service: StubRegisterDataset,
    principal: AuthorizedWorkspacePrincipal,
) -> TestClient:
    application = FastAPI()
    application.include_router(datasets_router)

    application.dependency_overrides[get_register_dataset_service] = lambda: service

    application.dependency_overrides[get_authenticate_workspace_service] = lambda: (
        StubAuthenticateWorkspaceAction(
            principal,
        )
    )

    return TestClient(
        application,
        raise_server_exceptions=False,
    )


def request_payload() -> dict[str, object]:
    return {
        "source_filename": "campaign-results.csv",
        "media_type": "text/csv",
        "byte_size": 4096,
        "checksum_sha256": CHECKSUM,
    }


def test_authorized_user_registers_dataset() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()

    dataset = Dataset.register(
        workspace_id=workspace_id,
        project_id=project_id,
        created_by_user_id=user_id,
        source_filename="campaign-results.csv",
        storage_key=(
            f"workspaces/{workspace_id}/projects/"
            f"{project_id}/datasets/{CHECKSUM}/"
            "campaign-results.csv"
        ),
        media_type="text/csv",
        byte_size=4096,
        checksum_sha256=CHECKSUM,
    )

    service = StubRegisterDataset(
        result=dataset,
    )

    client = build_client(
        service=service,
        principal=build_principal(
            workspace_id=workspace_id,
            user_id=user_id,
        ),
    )

    response = client.post(
        (f"/workspaces/{workspace_id}/projects/{project_id}/datasets"),
        headers={
            "Authorization": "Bearer valid-token",
        },
        json=request_payload(),
    )

    assert response.status_code == 201
    assert response.json()["id"] == str(dataset.id)
    assert response.json()["workspace_id"] == str(workspace_id)
    assert response.json()["project_id"] == str(project_id)
    assert response.json()["created_by_user_id"] == str(user_id)
    assert response.json()["status"] == "pending_upload"

    assert service.received_command is not None
    assert service.received_command.workspace_id == workspace_id
    assert service.received_command.project_id == project_id
    assert service.received_command.created_by_user_id == user_id


def test_oversized_dataset_returns_413() -> None:
    workspace_id = uuid4()
    project_id = uuid4()

    service = StubRegisterDataset(
        error=DatasetTooLargeError("Dataset exceeds the maximum upload size.")
    )

    client = build_client(
        service=service,
        principal=build_principal(
            workspace_id=workspace_id,
            user_id=uuid4(),
        ),
    )

    response = client.post(
        (f"/workspaces/{workspace_id}/projects/{project_id}/datasets"),
        headers={
            "Authorization": "Bearer valid-token",
        },
        json=request_payload(),
    )

    assert response.status_code == 413
    assert response.json() == {
        "detail": "Dataset exceeds the maximum upload size.",
    }


def test_unavailable_project_returns_404() -> None:
    workspace_id = uuid4()
    project_id = uuid4()

    service = StubRegisterDataset(
        error=DatasetProjectUnavailableError("Dataset project is unavailable.")
    )

    client = build_client(
        service=service,
        principal=build_principal(
            workspace_id=workspace_id,
            user_id=uuid4(),
        ),
    )

    response = client.post(
        (f"/workspaces/{workspace_id}/projects/{project_id}/datasets"),
        headers={
            "Authorization": "Bearer valid-token",
        },
        json=request_payload(),
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Dataset project is unavailable.",
    }


def test_dataset_persistence_conflict_returns_409() -> None:
    workspace_id = uuid4()
    project_id = uuid4()

    service = StubRegisterDataset(
        error=DatasetPersistenceConflictError("Dataset metadata conflicts with an existing record.")
    )

    client = build_client(
        service=service,
        principal=build_principal(
            workspace_id=workspace_id,
            user_id=uuid4(),
        ),
    )

    response = client.post(
        (f"/workspaces/{workspace_id}/projects/{project_id}/datasets"),
        headers={
            "Authorization": "Bearer valid-token",
        },
        json=request_payload(),
    )

    assert response.status_code == 409


def test_invalid_dataset_returns_422() -> None:
    workspace_id = uuid4()
    project_id = uuid4()

    service = StubRegisterDataset(
        error=InvalidDatasetError("Dataset filename must be a safe base filename.")
    )

    client = build_client(
        service=service,
        principal=build_principal(
            workspace_id=workspace_id,
            user_id=uuid4(),
        ),
    )

    payload = request_payload()
    payload["source_filename"] = "../unsafe.csv"

    response = client.post(
        (f"/workspaces/{workspace_id}/projects/{project_id}/datasets"),
        headers={
            "Authorization": "Bearer valid-token",
        },
        json=payload,
    )

    assert response.status_code == 422
    assert response.json() == {"detail": ("Dataset filename must be a safe base filename.")}


def test_client_cannot_supply_dataset_ownership() -> None:
    workspace_id = uuid4()
    project_id = uuid4()

    service = StubRegisterDataset()

    client = build_client(
        service=service,
        principal=build_principal(
            workspace_id=workspace_id,
            user_id=uuid4(),
        ),
    )

    payload = request_payload()
    payload["created_by_user_id"] = str(uuid4())
    payload["workspace_id"] = str(uuid4())
    payload["project_id"] = str(uuid4())

    response = client.post(
        (f"/workspaces/{workspace_id}/projects/{project_id}/datasets"),
        headers={
            "Authorization": "Bearer valid-token",
        },
        json=payload,
    )

    assert response.status_code == 422
    assert service.received_command is None
