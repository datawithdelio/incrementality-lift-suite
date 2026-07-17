from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from incrementality_api.api.dependencies.analysis_runs import get_analysis_result_service
from incrementality_api.api.v1.routes.analysis_results import _require_view_workspace, router
from incrementality_api.application.analysis_results.get_analysis_result import (
    AnalysisResultUnavailableError,
    AnalysisResultView,
)
from incrementality_api.domain.analysis_results.entities import AnalysisResult
from incrementality_api.domain.analysis_runs.entities import AnalysisRun
from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType

APPLICATION_VERSION = "0.1.0"
SOURCE_REVISION = "a" * 40

NOW = datetime(2026, 7, 14, 20, 0, tzinfo=UTC)


class FakeService:
    def __init__(self, view: AnalysisResultView | None = None) -> None:
        self.view = view

    async def execute(self, query: object) -> AnalysisResultView:
        del query
        if self.view is None:
            raise AnalysisResultUnavailableError("Analysis run is unavailable.")
        return self.view


def build_view(*, succeeded: bool = False, failed: bool = False) -> AnalysisResultView:
    run = AnalysisRun.queue(
        workspace_id=uuid4(),
        project_id=uuid4(),
        dataset_id=uuid4(),
        dataset_checksum_sha256="c" * 64,
        dataset_byte_size=4_096,
        semantic_mapping_id=uuid4(),
        semantic_mapping_version=1,
        created_by_user_id=uuid4(),
        estimator_type=AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
        estimator_version="did-v2",
        random_seed=1_729,
        configuration_json='{"intervention_time":"2026-01-01T00:00:00+00:00"}',
        created_at=NOW,
        application_version=APPLICATION_VERSION,
        source_revision=SOURCE_REVISION,
    )
    result = None
    lifecycle = "queued"
    failure = None
    if succeeded:
        run = run.start(started_at=NOW).mark_succeeded(completed_at=NOW)
        lifecycle = "succeeded"
        result = AnalysisResult.create(
            workspace_id=run.workspace_id,
            project_id=run.project_id,
            analysis_run_id=run.id,
            dataset_id=run.dataset_id,
            semantic_mapping_id=run.semantic_mapping_id,
            semantic_mapping_version=1,
            estimator_type=run.estimator_type,
            estimator_version=run.estimator_version,
            library_name="statsmodels",
            library_version="0.14",
            effect=8,
            standard_error=2,
            p_value=0.01,
            confidence_interval_low=4,
            confidence_interval_high=12,
            sample_size=120,
            diagnostics={"causal_claim_allowed": True, "warnings": []},
            incremental_outcome=480,
            relative_lift=0.12,
            incremental_revenue=None,
            incremental_conversions=None,
            created_at=NOW,
        )
    if failed:
        run = run.start(started_at=NOW).mark_failed(completed_at=NOW, reason="traceback")
        lifecycle = "failed"
        failure = "Analysis could not be completed. Review the design and try again."
    return AnalysisResultView(
        run,
        result,
        lifecycle,
        {"intervention_time": "2026-01-01"},
        1,
        3,
        failure,
    )


def app_for(service: FakeService, *, authorize: bool = True) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_analysis_result_service] = lambda: service
    if authorize:
        app.dependency_overrides[_require_view_workspace] = lambda: SimpleNamespace(user_id=uuid4())
    return app


async def request(app: FastAPI, view: AnalysisResultView):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.get(
            f"/api/v1/workspaces/{view.run.workspace_id}/projects/{view.run.project_id}/analysis-runs/{view.run.id}/result"
        )


@pytest.mark.asyncio
async def test_requires_authentication() -> None:
    view = build_view()
    response = await request(app_for(FakeService(view), authorize=False), view)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_forbidden_permission_is_not_hidden() -> None:
    view = build_view()
    app = app_for(FakeService(view))

    def forbidden() -> None:
        raise HTTPException(status_code=403, detail="Insufficient workspace permission.")

    app.dependency_overrides[_require_view_workspace] = forbidden
    response = await request(app, view)
    assert response.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["pending", "failed", "succeeded"])
async def test_returns_stable_contract_for_run_states(state: str) -> None:
    view = build_view(succeeded=state == "succeeded", failed=state == "failed")
    response = await request(app_for(FakeService(view)), view)
    assert response.status_code == 200
    payload = response.json()
    assert payload["lifecycle_status"] == ("queued" if state == "pending" else state)
    assert (payload["result"] is not None) is (state == "succeeded")
    if state == "failed":
        assert "traceback" not in payload["failure_information"]


@pytest.mark.asyncio
async def test_missing_run_is_404() -> None:
    view = build_view()
    response = await request(app_for(FakeService()), view)
    assert response.status_code == 404
