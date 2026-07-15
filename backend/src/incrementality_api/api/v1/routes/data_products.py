from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from incrementality_api.api.dependencies.authorization import RequireWorkspacePermission
from incrementality_api.api.dependencies.data_products import (
    SystemDataProductClock,
    get_data_product_storage,
    get_data_products_service,
    get_dataset_version_reader,
    get_report_repository,
)
from incrementality_api.api.v1.schemas.data_products import (
    DataQualityResponse,
    DatasetPreviewResponse,
    DatasetVersionResponse,
    QueueReportRequest,
    ReportJobResponse,
)
from incrementality_api.application.authorization.authenticate_workspace import (
    AuthorizedWorkspacePrincipal,
)
from incrementality_api.application.data_products.explorer import (
    DatasetExplorerQuery,
    DatasetFilter,
)
from incrementality_api.application.data_products.services import (
    DatasetProductQuery,
    ProductionDataProducts,
)
from incrementality_api.application.datasets.errors import DatasetUnavailableError
from incrementality_api.domain.authorization.permissions import WorkspacePermission
from incrementality_api.infrastructure.database.repositories.data_products import (
    SqlAlchemyDatasetVersionReader,
    SqlAlchemyReportRepository,
)
from incrementality_api.infrastructure.storage.s3_dataset_objects import S3DatasetObjectStorage

router = APIRouter(
    prefix="/workspaces/{workspace_id}/projects/{project_id}", tags=["data-products"]
)
_view = RequireWorkspacePermission(WorkspacePermission.VIEW_WORKSPACE)
_manage_data = RequireWorkspacePermission(WorkspacePermission.MANAGE_DATASETS)
_run = RequireWorkspacePermission(WorkspacePermission.RUN_ANALYSES)
_reports = RequireWorkspacePermission(WorkspacePermission.VIEW_REPORTS)


def _explorer_query(
    page: int,
    page_size: int,
    sort_column: str | None,
    descending: bool,
    filter_column: str | None,
    filter_operator: str,
    filter_value: str | None,
    column_search: str | None,
) -> DatasetExplorerQuery:
    filters = (
        (DatasetFilter(filter_column, filter_operator, filter_value or ""),)
        if filter_column
        else ()
    )
    return DatasetExplorerQuery(page, page_size, sort_column, descending, filters, column_search)


@router.get("/datasets/{dataset_id}/preview", response_model=DatasetPreviewResponse)
async def preview_dataset(
    workspace_id: UUID,
    project_id: UUID,
    dataset_id: UUID,
    principal: Annotated[AuthorizedWorkspacePrincipal, Depends(_view)],
    service: Annotated[ProductionDataProducts, Depends(get_data_products_service)],
    page: int = 1,
    page_size: int = Query(50, le=500),
    sort_column: str | None = None,
    descending: bool = False,
    filter_column: str | None = None,
    filter_operator: str = "equals",
    filter_value: str | None = None,
    column_search: str | None = None,
    mapping_version: int | None = None,
) -> DatasetPreviewResponse:
    del principal
    try:
        result = await service.preview(
            DatasetProductQuery(workspace_id, project_id, dataset_id, mapping_version),
            _explorer_query(
                page,
                page_size,
                sort_column,
                descending,
                filter_column,
                filter_operator,
                filter_value,
                column_search,
            ),
        )
    except DatasetUnavailableError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    return DatasetPreviewResponse.model_validate(result, from_attributes=True)


@router.get("/dataset-versions", response_model=tuple[DatasetVersionResponse, ...])
async def list_dataset_versions(
    workspace_id: UUID,
    project_id: UUID,
    principal: Annotated[AuthorizedWorkspacePrincipal, Depends(_view)],
    reader: Annotated[SqlAlchemyDatasetVersionReader, Depends(get_dataset_version_reader)],
) -> tuple[DatasetVersionResponse, ...]:
    del principal
    return tuple(
        DatasetVersionResponse.model_validate(item, from_attributes=True)
        for item in await reader.list(workspace_id=workspace_id, project_id=project_id)
    )


@router.get("/datasets/{dataset_id}/preview.csv")
async def export_dataset_preview(
    workspace_id: UUID,
    project_id: UUID,
    dataset_id: UUID,
    principal: Annotated[AuthorizedWorkspacePrincipal, Depends(_view)],
    service: Annotated[ProductionDataProducts, Depends(get_data_products_service)],
    sort_column: str | None = None,
    descending: bool = False,
    filter_column: str | None = None,
    filter_operator: str = "equals",
    filter_value: str | None = None,
    column_search: str | None = None,
    mapping_version: int | None = None,
) -> Response:
    del principal
    payload = await service.export(
        DatasetProductQuery(workspace_id, project_id, dataset_id, mapping_version),
        _explorer_query(
            1,
            500,
            sort_column,
            descending,
            filter_column,
            filter_operator,
            filter_value,
            column_search,
        ),
    )
    return Response(
        payload,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="dataset-{dataset_id}.csv"'},
    )


@router.post("/datasets/{dataset_id}/quality", response_model=DataQualityResponse)
async def assess_dataset_quality(
    workspace_id: UUID,
    project_id: UUID,
    dataset_id: UUID,
    principal: Annotated[AuthorizedWorkspacePrincipal, Depends(_manage_data)],
    service: Annotated[ProductionDataProducts, Depends(get_data_products_service)],
    estimator: str,
    mapping_version: int | None = None,
    leakage_column: Annotated[list[str] | None, Query()] = None,
) -> DataQualityResponse:
    del principal
    result = await service.assess_quality(
        DatasetProductQuery(workspace_id, project_id, dataset_id, mapping_version),
        estimator_type=estimator,
        leakage_columns=tuple(leakage_column or ()),
    )
    return DataQualityResponse.model_validate(result, from_attributes=True)


@router.post("/analysis-runs/{run_id}/reports", response_model=ReportJobResponse, status_code=202)
async def queue_report(
    workspace_id: UUID,
    project_id: UUID,
    run_id: UUID,
    request: QueueReportRequest,
    principal: Annotated[AuthorizedWorkspacePrincipal, Depends(_run)],
    repository: Annotated[SqlAlchemyReportRepository, Depends(get_report_repository)],
) -> ReportJobResponse:
    del principal
    if request.format not in {"pdf", "csv"}:
        raise HTTPException(422, "Report format is unsupported.")
    try:
        job = await repository.queue(
            workspace_id=workspace_id,
            project_id=project_id,
            run_id=run_id,
            format=request.format,
            now=SystemDataProductClock().now(),
        )
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    return ReportJobResponse.model_validate(job, from_attributes=True)


@router.get("/analysis-runs/{run_id}/reports", response_model=tuple[ReportJobResponse, ...])
async def list_reports(
    workspace_id: UUID,
    project_id: UUID,
    run_id: UUID,
    principal: Annotated[AuthorizedWorkspacePrincipal, Depends(_reports)],
    repository: Annotated[SqlAlchemyReportRepository, Depends(get_report_repository)],
) -> tuple[ReportJobResponse, ...]:
    del principal
    return tuple(
        ReportJobResponse.model_validate(item, from_attributes=True)
        for item in await repository.list(
            workspace_id=workspace_id, project_id=project_id, run_id=run_id
        )
    )


@router.get("/reports/{report_id}/download")
async def download_report(
    workspace_id: UUID,
    project_id: UUID,
    report_id: UUID,
    principal: Annotated[AuthorizedWorkspacePrincipal, Depends(_reports)],
    repository: Annotated[SqlAlchemyReportRepository, Depends(get_report_repository)],
    storage: Annotated[S3DatasetObjectStorage, Depends(get_data_product_storage)],
) -> Response:
    del principal
    job = await repository.get(
        workspace_id=workspace_id, project_id=project_id, report_id=report_id
    )
    if job is None or job.status != "succeeded" or job.storage_key is None:
        raise HTTPException(404, "Completed report is unavailable.")
    payload = b"".join([chunk async for chunk in storage.read(storage_key=job.storage_key)])
    media_type = "application/pdf" if job.format == "pdf" else "text/csv"
    return Response(
        payload,
        media_type=media_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="analysis-report-v{job.version}.{job.format}"'
            )
        },
    )
