from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from incrementality_api.api.dependencies.authorization import RequireWorkspacePermission
from incrementality_api.api.dependencies.measurement import (
    get_channel_performance_service,
    get_results_dashboard_service,
)
from incrementality_api.api.v1.schemas.measurement import (
    ChannelPerformanceListResponse,
    ResultsDashboardResponse,
)
from incrementality_api.application.authorization.authenticate_workspace import (
    AuthorizedWorkspacePrincipal,
)
from incrementality_api.application.measurement.views import (
    GetChannelPerformance,
    GetResultsDashboard,
    MeasurementFilters,
)
from incrementality_api.domain.authorization.permissions import WorkspacePermission

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["measurement"])
_require_view = RequireWorkspacePermission(WorkspacePermission.VIEW_WORKSPACE)


def _filters(
    workspace_id: UUID,
    project_id: UUID | None,
    estimator: str | None,
    run_status: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> MeasurementFilters:
    return MeasurementFilters(workspace_id, project_id, estimator, run_status, date_from, date_to)


@router.get("/results-dashboard", response_model=ResultsDashboardResponse)
async def read_results_dashboard(
    workspace_id: UUID,
    principal: Annotated[AuthorizedWorkspacePrincipal, Depends(_require_view)],
    service: Annotated[GetResultsDashboard, Depends(get_results_dashboard_service)],
    project_id: UUID | None = None,
    estimator: str | None = None,
    run_status: Annotated[str | None, Query(alias="status")] = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> ResultsDashboardResponse:
    del principal
    return ResultsDashboardResponse.model_validate(
        await service.execute(
            _filters(workspace_id, project_id, estimator, run_status, date_from, date_to)
        ),
        from_attributes=True,
    )


@router.get("/channel-performance", response_model=ChannelPerformanceListResponse)
async def read_channel_performance(
    workspace_id: UUID,
    principal: Annotated[AuthorizedWorkspacePrincipal, Depends(_require_view)],
    service: Annotated[GetChannelPerformance, Depends(get_channel_performance_service)],
    project_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> ChannelPerformanceListResponse:
    del principal
    return ChannelPerformanceListResponse.model_validate(
        await service.execute(
            MeasurementFilters(workspace_id, project_id, date_from=date_from, date_to=date_to)
        ),
        from_attributes=True,
    )
