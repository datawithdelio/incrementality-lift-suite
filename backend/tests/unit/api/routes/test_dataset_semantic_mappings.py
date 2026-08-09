from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from incrementality_api.api.dependencies.authorization import (
    get_authenticate_workspace_service,
)
from incrementality_api.api.dependencies.datasets import (
    get_create_dataset_semantic_mapping_service,
    get_read_dataset_semantic_mapping_service,
)
from incrementality_api.api.v1.routes.datasets import (
    router as datasets_router,
)
from incrementality_api.application.authorization.authenticate_workspace import (
    AuthorizedWorkspacePrincipal,
)
from incrementality_api.application.datasets.errors import (
    DatasetPersistenceConflictError,
    DatasetSemanticMappingUnavailableError,
    DatasetUnavailableError,
)
from incrementality_api.application.datasets.manage_semantic_mapping import (
    CreateDatasetSemanticMappingCommand,
    GetDatasetSemanticMappingQuery,
)
from incrementality_api.domain.analysis_runs.status import (
    AnalysisEstimatorType,
)
from incrementality_api.domain.authorization.permissions import (
    WorkspacePermission,
)
from incrementality_api.domain.datasets.errors import (
    InvalidDatasetSemanticMappingError,
)
from incrementality_api.domain.datasets.semantic_mapping import (
    DatasetSemanticMapping,
)
from incrementality_api.domain.tenancy.roles import (
    WorkspaceRole,
)

FIXED_NOW = datetime(
    2026,
    7,
    14,
    23,
    30,
    tzinfo=UTC,
)

EXPIRES_AT = datetime(
    2026,
    7,
    15,
    7,
    30,
    tzinfo=UTC,
)


class StubAuthenticateWorkspaceAction:
    def __init__(
        self,
        principal: AuthorizedWorkspacePrincipal,
    ) -> None:
        self._principal = principal
        self.received_permissions: list[WorkspacePermission] = []

    async def execute(
        self,
        *,
        raw_token: str,
        workspace_id: UUID,
        permission: WorkspacePermission,
    ) -> AuthorizedWorkspacePrincipal:
        del raw_token, workspace_id

        self.received_permissions.append(
            permission,
        )

        return self._principal


class StubCreateDatasetSemanticMapping:
    def __init__(
        self,
        *,
        result: DatasetSemanticMapping | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.received_command: CreateDatasetSemanticMappingCommand | None = None

    async def execute(
        self,
        command: CreateDatasetSemanticMappingCommand,
    ) -> DatasetSemanticMapping:
        self.received_command = command

        if self._error is not None:
            raise self._error

        if self._result is None:
            raise AssertionError("Semantic mapping result was not configured.")

        return self._result


class StubGetDatasetSemanticMapping:
    def __init__(
        self,
        *,
        result: DatasetSemanticMapping | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.received_query: GetDatasetSemanticMappingQuery | None = None

    async def execute(
        self,
        query: GetDatasetSemanticMappingQuery,
    ) -> DatasetSemanticMapping:
        self.received_query = query

        if self._error is not None:
            raise self._error

        if self._result is None:
            raise AssertionError("Semantic mapping result was not configured.")

        return self._result


def build_mapping(
    *,
    dataset_id: UUID,
    user_id: UUID,
    version: int = 1,
) -> DatasetSemanticMapping:
    return DatasetSemanticMapping(
        id=uuid4(),
        dataset_id=dataset_id,
        created_by_user_id=user_id,
        version=version,
        time_column="date",
        unit_column="market",
        treatment_column="treated",
        outcome_column="revenue",
        spend_column="spend",
        covariate_columns=(
            "promotion",
            "seasonality",
        ),
        treatment_value="true",
        control_value="false",
        created_at=FIXED_NOW,
        updated_at=FIXED_NOW,
    )


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


def request_payload() -> dict[str, object]:
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


def build_client(
    *,
    principal: AuthorizedWorkspacePrincipal,
    create_service: (StubCreateDatasetSemanticMapping | None) = None,
    read_service: (StubGetDatasetSemanticMapping | None) = None,
) -> tuple[
    TestClient,
    StubAuthenticateWorkspaceAction,
]:
    application = FastAPI()
    application.include_router(
        datasets_router,
    )

    authentication = StubAuthenticateWorkspaceAction(
        principal,
    )

    application.dependency_overrides[get_authenticate_workspace_service] = lambda: authentication

    if create_service is not None:
        application.dependency_overrides[get_create_dataset_semantic_mapping_service] = lambda: (
            create_service
        )

    if read_service is not None:
        application.dependency_overrides[get_read_dataset_semantic_mapping_service] = lambda: (
            read_service
        )

    return (
        TestClient(
            application,
            raise_server_exceptions=False,
        ),
        authentication,
    )


def test_authorized_user_creates_semantic_mapping() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    dataset_id = uuid4()
    user_id = uuid4()

    mapping = build_mapping(
        dataset_id=dataset_id,
        user_id=user_id,
    )

    service = StubCreateDatasetSemanticMapping(
        result=mapping,
    )

    client, authentication = build_client(
        principal=build_principal(
            workspace_id=workspace_id,
            user_id=user_id,
        ),
        create_service=service,
    )

    response = client.post(
        (
            f"/workspaces/{workspace_id}"
            f"/projects/{project_id}"
            f"/datasets/{dataset_id}"
            "/semantic-mappings"
        ),
        headers={
            "Authorization": "Bearer valid-token",
        },
        json=request_payload(),
    )

    assert response.status_code == 201

    payload = response.json()

    assert payload["id"] == str(mapping.id)
    assert payload["dataset_id"] == str(dataset_id)
    assert payload["created_by_user_id"] == str(user_id)
    assert payload["version"] == 1
    assert payload["time_column"] == "date"
    assert payload["covariate_columns"] == [
        "promotion",
        "seasonality",
    ]

    assert service.received_command is not None
    assert service.received_command.workspace_id == (workspace_id)
    assert service.received_command.project_id == (project_id)
    assert service.received_command.dataset_id == (dataset_id)
    assert service.received_command.created_by_user_id == (user_id)

    assert authentication.received_permissions == [
        WorkspacePermission.MANAGE_DATASETS,
    ]


def test_mmm_mapping_omits_treatment_roles() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    dataset_id = uuid4()
    user_id = uuid4()
    mapping = build_mapping(dataset_id=dataset_id, user_id=user_id)
    service = StubCreateDatasetSemanticMapping(result=mapping)
    client, _ = build_client(
        principal=build_principal(workspace_id=workspace_id, user_id=user_id),
        create_service=service,
    )
    payload = request_payload()
    payload.pop("treatment_column")
    payload.pop("treatment_value")
    payload.pop("control_value")

    response = client.post(
        (
            f"/workspaces/{workspace_id}/projects/{project_id}"
            f"/datasets/{dataset_id}/semantic-mappings"
            "?estimator=marketing_mix_model"
        ),
        headers={"Authorization": "Bearer valid-token"},
        json=payload,
    )

    assert response.status_code == 201
    assert service.received_command is not None
    assert service.received_command.treatment_column is None
    assert service.received_command.treatment_value is None
    assert service.received_command.control_value is None
    assert (
        service.received_command.estimator
        is AnalysisEstimatorType.MARKETING_MIX_MODEL
    )


def test_reads_latest_semantic_mapping() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    dataset_id = uuid4()
    user_id = uuid4()

    mapping = build_mapping(
        dataset_id=dataset_id,
        user_id=user_id,
        version=3,
    )

    service = StubGetDatasetSemanticMapping(
        result=mapping,
    )

    client, authentication = build_client(
        principal=build_principal(
            workspace_id=workspace_id,
            user_id=user_id,
        ),
        read_service=service,
    )

    response = client.get(
        (
            f"/workspaces/{workspace_id}"
            f"/projects/{project_id}"
            f"/datasets/{dataset_id}"
            "/semantic-mappings/latest"
        ),
        headers={
            "Authorization": "Bearer valid-token",
        },
    )

    assert response.status_code == 200
    assert response.json()["version"] == 3

    assert service.received_query == (
        GetDatasetSemanticMappingQuery(
            workspace_id=workspace_id,
            project_id=project_id,
            dataset_id=dataset_id,
        )
    )

    assert authentication.received_permissions == [
        WorkspacePermission.VIEW_WORKSPACE,
    ]


def test_reads_specific_semantic_mapping_version() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    dataset_id = uuid4()
    user_id = uuid4()

    mapping = build_mapping(
        dataset_id=dataset_id,
        user_id=user_id,
        version=2,
    )

    service = StubGetDatasetSemanticMapping(
        result=mapping,
    )

    client, _ = build_client(
        principal=build_principal(
            workspace_id=workspace_id,
            user_id=user_id,
        ),
        read_service=service,
    )

    response = client.get(
        (
            f"/workspaces/{workspace_id}"
            f"/projects/{project_id}"
            f"/datasets/{dataset_id}"
            "/semantic-mappings/2"
        ),
        headers={
            "Authorization": "Bearer valid-token",
        },
    )

    assert response.status_code == 200
    assert response.json()["version"] == 2

    assert service.received_query == (
        GetDatasetSemanticMappingQuery(
            workspace_id=workspace_id,
            project_id=project_id,
            dataset_id=dataset_id,
            version=2,
        )
    )


def test_invalid_semantic_mapping_returns_422() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    dataset_id = uuid4()
    user_id = uuid4()

    service = StubCreateDatasetSemanticMapping(
        error=InvalidDatasetSemanticMappingError("Outcome column must be numeric."),
    )

    client, _ = build_client(
        principal=build_principal(
            workspace_id=workspace_id,
            user_id=user_id,
        ),
        create_service=service,
    )

    response = client.post(
        (
            f"/workspaces/{workspace_id}"
            f"/projects/{project_id}"
            f"/datasets/{dataset_id}"
            "/semantic-mappings"
        ),
        headers={
            "Authorization": "Bearer valid-token",
        },
        json=request_payload(),
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Outcome column must be numeric.",
    }


def test_unavailable_dataset_returns_404() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    dataset_id = uuid4()
    user_id = uuid4()

    service = StubCreateDatasetSemanticMapping(
        error=DatasetUnavailableError("Dataset is unavailable."),
    )

    client, _ = build_client(
        principal=build_principal(
            workspace_id=workspace_id,
            user_id=user_id,
        ),
        create_service=service,
    )

    response = client.post(
        (
            f"/workspaces/{workspace_id}"
            f"/projects/{project_id}"
            f"/datasets/{dataset_id}"
            "/semantic-mappings"
        ),
        headers={
            "Authorization": "Bearer valid-token",
        },
        json=request_payload(),
    )

    assert response.status_code == 404


def test_unavailable_mapping_returns_404() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    dataset_id = uuid4()
    user_id = uuid4()

    service = StubGetDatasetSemanticMapping(
        error=DatasetSemanticMappingUnavailableError("Semantic mapping is unavailable."),
    )

    client, _ = build_client(
        principal=build_principal(
            workspace_id=workspace_id,
            user_id=user_id,
        ),
        read_service=service,
    )

    response = client.get(
        (
            f"/workspaces/{workspace_id}"
            f"/projects/{project_id}"
            f"/datasets/{dataset_id}"
            "/semantic-mappings/latest"
        ),
        headers={
            "Authorization": "Bearer valid-token",
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Semantic mapping is unavailable.",
    }


def test_mapping_persistence_conflict_returns_409() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    dataset_id = uuid4()
    user_id = uuid4()

    service = StubCreateDatasetSemanticMapping(
        error=DatasetPersistenceConflictError(
            "Dataset semantic mapping conflicts with existing records."
        ),
    )

    client, _ = build_client(
        principal=build_principal(
            workspace_id=workspace_id,
            user_id=user_id,
        ),
        create_service=service,
    )

    response = client.post(
        (
            f"/workspaces/{workspace_id}"
            f"/projects/{project_id}"
            f"/datasets/{dataset_id}"
            "/semantic-mappings"
        ),
        headers={
            "Authorization": "Bearer valid-token",
        },
        json=request_payload(),
    )

    assert response.status_code == 409


def test_semantic_mapping_request_rejects_extra_fields() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    dataset_id = uuid4()
    user_id = uuid4()

    service = StubCreateDatasetSemanticMapping()

    client, _ = build_client(
        principal=build_principal(
            workspace_id=workspace_id,
            user_id=user_id,
        ),
        create_service=service,
    )

    payload = request_payload()
    payload["unexpected_field"] = "not allowed"

    response = client.post(
        (
            f"/workspaces/{workspace_id}"
            f"/projects/{project_id}"
            f"/datasets/{dataset_id}"
            "/semantic-mappings"
        ),
        headers={
            "Authorization": "Bearer valid-token",
        },
        json=payload,
    )

    assert response.status_code == 422
    assert service.received_command is None
