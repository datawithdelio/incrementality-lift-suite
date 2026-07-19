import json
from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from incrementality_api.api.dependencies.analysis_runs import get_analysis_result_service
from incrementality_api.api.dependencies.authorization import RequireWorkspacePermission
from incrementality_api.api.v1.schemas.analysis_results import (
    AnalysisResultResponse,
    BusinessImpactResponse,
    ConfidenceIntervalResponse,
    StatisticalResultResponse,
)
from incrementality_api.application.analysis_results.get_analysis_result import (
    AnalysisResultUnavailableError,
    AnalysisResultView,
    GetAnalysisResult,
    GetAnalysisResultQuery,
)
from incrementality_api.application.authorization.authenticate_workspace import (
    AuthorizedWorkspacePrincipal,
)
from incrementality_api.domain.authorization.permissions import WorkspacePermission

router = APIRouter(
    prefix="/workspaces/{workspace_id}/projects/{project_id}/analysis-runs",
    tags=["analysis-results"],
)

_require_view_workspace = RequireWorkspacePermission(WorkspacePermission.VIEW_WORKSPACE)


def _to_response(view: AnalysisResultView) -> AnalysisResultResponse:
    result_response: StatisticalResultResponse | None = None
    if view.result is not None:
        parsed = json.loads(view.result.diagnostics_json)
        if not isinstance(parsed, dict):
            raise RuntimeError("Persisted diagnostics must be an object.")
        diagnostics = cast(dict[str, object], parsed)
        result_response = StatisticalResultResponse(
            effect_estimate=view.result.effect,
            standard_error=view.result.standard_error,
            confidence_interval=ConfidenceIntervalResponse(
                low=view.result.confidence_interval_low,
                high=view.result.confidence_interval_high,
            ),
            p_value=view.result.p_value,
            sample_size=view.result.sample_size,
            estimator_version=view.result.estimator_version,
            library_name=view.result.library_name,
            library_version=view.result.library_version,
            technical_diagnostics=diagnostics,
            business_impact=BusinessImpactResponse(
                incremental_outcome=view.result.incremental_outcome,
                relative_lift=view.result.relative_lift,
                incremental_revenue=view.result.incremental_revenue,
                incremental_conversions=view.result.incremental_conversions,
            ),
            created_at=view.result.created_at,
        )
    return AnalysisResultResponse(
        analysis_run_id=view.run.id,
        workspace_id=view.run.workspace_id,
        project_id=view.run.project_id,
        dataset_id=view.run.dataset_id,
        semantic_mapping_version=(
            view.run.semantic_mapping_version
        ),
        created_at=view.run.created_at,
        started_at=view.run.started_at,
        completed_at=view.run.completed_at,
        run_status=view.run.status,
        lifecycle_status=view.lifecycle_status,  # type: ignore[arg-type]
        estimator_type=view.run.estimator_type,
        estimator_version=view.run.estimator_version,
        analysis_configuration=view.configuration,
        attempt_count=view.attempt_count,
        max_attempts=view.max_attempts,
        failure_information=view.failure_information,
        result=result_response,
    )


@router.get("/{analysis_run_id}/result", response_model=AnalysisResultResponse)
async def read_analysis_result(
    workspace_id: UUID,
    project_id: UUID,
    analysis_run_id: UUID,
    principal: Annotated[
        AuthorizedWorkspacePrincipal, Depends(_require_view_workspace)
    ],
    service: Annotated[GetAnalysisResult, Depends(get_analysis_result_service)],
) -> AnalysisResultResponse:
    del principal
    try:
        view = await service.execute(
            GetAnalysisResultQuery(workspace_id, project_id, analysis_run_id)
        )
    except AnalysisResultUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return _to_response(view)
