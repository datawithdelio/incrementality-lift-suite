import json
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from incrementality_api.api.dependencies.analysis_runs import (
    get_analysis_run_service,
    get_queue_analysis_run_service,
)
from incrementality_api.api.v1.routes.analysis_runs import (
    _require_manage_datasets,
    _require_view_workspace,
    router,
)
from incrementality_api.application.analysis_runs.errors import (
    AnalysisRunDatasetNotReadyError,
    AnalysisRunDatasetUnavailableError,
    AnalysisRunPersistenceConflictError,
    AnalysisRunSemanticMappingUnavailableError,
    AnalysisRunUnavailableError,
)
from incrementality_api.application.analysis_runs.manage_analysis_runs import (
    GetAnalysisRunQuery,
    QueueAnalysisRunCommand,
)
from incrementality_api.domain.analysis_runs.entities import (
    AnalysisRun,
)
from incrementality_api.domain.analysis_runs.errors import (
    InvalidAnalysisRunError,
)
from incrementality_api.domain.analysis_runs.status import (
    AnalysisEstimatorType,
)

CREATED_AT = datetime(
    2026,
    7,
    15,
    20,
    0,
    tzinfo=UTC,
)


class FakeQueueAnalysisRun:
    def __init__(
        self,
        *,
        result: AnalysisRun | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.commands: list[QueueAnalysisRunCommand] = []

    async def execute(
        self,
        command: QueueAnalysisRunCommand,
    ) -> AnalysisRun:
        self.commands.append(command)

        if self._error is not None:
            raise self._error

        assert self._result is not None
        return self._result


class FakeGetAnalysisRun:
    def __init__(
        self,
        *,
        result: AnalysisRun | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.queries: list[GetAnalysisRunQuery] = []

    async def execute(
        self,
        query: GetAnalysisRunQuery,
    ) -> AnalysisRun:
        self.queries.append(query)

        if self._error is not None:
            raise self._error

        assert self._result is not None
        return self._result


def build_run(
    *,
    workspace_id: UUID,
    project_id: UUID,
    user_id: UUID,
) -> AnalysisRun:
    return AnalysisRun.queue(
        workspace_id=workspace_id,
        project_id=project_id,
        dataset_id=uuid4(),
        semantic_mapping_id=uuid4(),
        semantic_mapping_version=3,
        created_by_user_id=user_id,
        estimator_type=(AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES),
        estimator_version="did-v1",
        configuration_json="""
        {
          "cluster_by": "unit",
          "alpha": 0.05
        }
        """,
        created_at=CREATED_AT,
    )


def build_application(
    *,
    user_id: UUID,
    queue_service: FakeQueueAnalysisRun,
    get_service: FakeGetAnalysisRun,
) -> FastAPI:
    application = FastAPI()
    application.include_router(
        router,
        prefix="/api/v1",
    )

    principal = SimpleNamespace(
        user_id=user_id,
    )

    application.dependency_overrides[_require_manage_datasets] = lambda: principal

    application.dependency_overrides[_require_view_workspace] = lambda: principal

    application.dependency_overrides[get_queue_analysis_run_service] = lambda: queue_service

    application.dependency_overrides[get_analysis_run_service] = lambda: get_service

    return application


@pytest.mark.asyncio
async def test_queues_analysis_run() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()

    run = build_run(
        workspace_id=workspace_id,
        project_id=project_id,
        user_id=user_id,
    )

    queue_service = FakeQueueAnalysisRun(
        result=run,
    )

    application = build_application(
        user_id=user_id,
        queue_service=queue_service,
        get_service=FakeGetAnalysisRun(
            result=run,
        ),
    )

    transport = ASGITransport(
        app=application,
    )

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            (f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/analysis-runs"),
            json={
                "dataset_id": str(run.dataset_id),
                "semantic_mapping_version": 3,
                "estimator_type": ("difference_in_differences"),
                "estimator_version": "did-v1",
                "configuration": {
                    "cluster_by": "unit",
                    "alpha": 0.05,
                },
            },
        )

    assert response.status_code == 201

    payload = response.json()

    assert payload["id"] == str(run.id)
    assert payload["workspace_id"] == str(workspace_id)
    assert payload["project_id"] == str(project_id)
    assert payload["dataset_id"] == str(run.dataset_id)
    assert payload["semantic_mapping_id"] == str(run.semantic_mapping_id)
    assert payload["semantic_mapping_version"] == 3
    assert payload["created_by_user_id"] == str(user_id)
    assert payload["estimator_type"] == ("difference_in_differences")
    assert payload["estimator_version"] == "did-v1"
    assert payload["configuration"] == {
        "alpha": 0.05,
        "cluster_by": "unit",
    }
    assert payload["status"] == "queued"
    assert payload["started_at"] is None
    assert payload["completed_at"] is None
    assert payload["failure_reason"] is None
    assert payload["cancellation_reason"] is None

    assert len(queue_service.commands) == 1

    command = queue_service.commands[0]

    assert command.workspace_id == workspace_id
    assert command.project_id == project_id
    assert command.dataset_id == run.dataset_id
    assert command.semantic_mapping_version == 3
    assert command.created_by_user_id == user_id
    assert command.estimator_type is (AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES)
    assert command.estimator_version == "did-v1"

    assert json.loads(command.configuration_json) == {
        "cluster_by": "unit",
        "alpha": 0.05,
    }


@pytest.mark.asyncio
async def test_reads_analysis_run() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()

    run = build_run(
        workspace_id=workspace_id,
        project_id=project_id,
        user_id=user_id,
    )

    get_service = FakeGetAnalysisRun(
        result=run,
    )

    application = build_application(
        user_id=user_id,
        queue_service=FakeQueueAnalysisRun(
            result=run,
        ),
        get_service=get_service,
    )

    transport = ASGITransport(
        app=application,
    )

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/analysis-runs/{run.id}"
        )

    assert response.status_code == 200
    assert response.json()["id"] == str(run.id)
    assert response.json()["status"] == "queued"
    assert response.json()["configuration"] == {
        "alpha": 0.05,
        "cluster_by": "unit",
    }

    assert get_service.queries == [
        GetAnalysisRunQuery(
            workspace_id=workspace_id,
            project_id=project_id,
            analysis_run_id=run.id,
        )
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (
            AnalysisRunDatasetUnavailableError("Dataset is unavailable."),
            404,
        ),
        (
            AnalysisRunSemanticMappingUnavailableError("Semantic mapping is unavailable."),
            404,
        ),
        (
            AnalysisRunDatasetNotReadyError("Dataset must be ready before analysis."),
            409,
        ),
        (
            AnalysisRunPersistenceConflictError("Analysis run conflicts with existing records."),
            409,
        ),
        (
            InvalidAnalysisRunError("Estimator version must not be blank."),
            422,
        ),
    ],
)
async def test_queue_maps_application_and_domain_errors(
    error: Exception,
    expected_status: int,
) -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()

    run = build_run(
        workspace_id=workspace_id,
        project_id=project_id,
        user_id=user_id,
    )

    application = build_application(
        user_id=user_id,
        queue_service=FakeQueueAnalysisRun(
            error=error,
        ),
        get_service=FakeGetAnalysisRun(
            result=run,
        ),
    )

    transport = ASGITransport(
        app=application,
    )

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            (f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/analysis-runs"),
            json={
                "dataset_id": str(run.dataset_id),
                "semantic_mapping_version": 3,
                "estimator_type": ("difference_in_differences"),
                "estimator_version": "did-v1",
                "configuration": {
                    "alpha": 0.05,
                },
            },
        )

    assert response.status_code == expected_status
    assert response.json() == {
        "detail": str(error),
    }


@pytest.mark.asyncio
async def test_get_maps_unavailable_run_to_not_found() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()

    error = AnalysisRunUnavailableError("Analysis run is unavailable.")

    run = build_run(
        workspace_id=workspace_id,
        project_id=project_id,
        user_id=user_id,
    )

    application = build_application(
        user_id=user_id,
        queue_service=FakeQueueAnalysisRun(
            result=run,
        ),
        get_service=FakeGetAnalysisRun(
            error=error,
        ),
    )

    transport = ASGITransport(
        app=application,
    )

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/analysis-runs/{run.id}"
        )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Analysis run is unavailable.",
    }


@pytest.mark.asyncio
async def test_queue_request_rejects_extra_fields() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()

    run = build_run(
        workspace_id=workspace_id,
        project_id=project_id,
        user_id=user_id,
    )

    queue_service = FakeQueueAnalysisRun(
        result=run,
    )

    application = build_application(
        user_id=user_id,
        queue_service=queue_service,
        get_service=FakeGetAnalysisRun(
            result=run,
        ),
    )

    transport = ASGITransport(
        app=application,
    )

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            (f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/analysis-runs"),
            json={
                "dataset_id": str(run.dataset_id),
                "semantic_mapping_version": 3,
                "estimator_type": ("difference_in_differences"),
                "estimator_version": "did-v1",
                "configuration": {
                    "alpha": 0.05,
                },
                "unexpected": True,
            },
        )

    assert response.status_code == 422
    assert queue_service.commands == []


@pytest.mark.asyncio
async def test_queue_request_requires_configuration_object() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()

    run = build_run(
        workspace_id=workspace_id,
        project_id=project_id,
        user_id=user_id,
    )

    queue_service = FakeQueueAnalysisRun(
        result=run,
    )

    application = build_application(
        user_id=user_id,
        queue_service=queue_service,
        get_service=FakeGetAnalysisRun(
            result=run,
        ),
    )

    transport = ASGITransport(
        app=application,
    )

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            (f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/analysis-runs"),
            json={
                "dataset_id": str(run.dataset_id),
                "semantic_mapping_version": 3,
                "estimator_type": ("difference_in_differences"),
                "estimator_version": "did-v1",
                "configuration": [
                    "not",
                    "an",
                    "object",
                ],
            },
        )

    assert response.status_code == 422
    assert queue_service.commands == []
