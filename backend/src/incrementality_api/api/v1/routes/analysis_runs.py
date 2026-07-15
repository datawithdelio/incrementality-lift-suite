import json
from typing import Annotated, cast
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from incrementality_api.api.dependencies.analysis_runs import (
    get_analysis_run_service,
    get_queue_analysis_run_service,
)
from incrementality_api.api.dependencies.authorization import (
    RequireWorkspacePermission,
)
from incrementality_api.api.v1.schemas.analysis_runs import (
    AnalysisRunResponse,
    QueueAnalysisRunRequest,
)
from incrementality_api.application.analysis_runs.errors import (
    AnalysisRunDataQualityBlockedError,
    AnalysisRunDatasetNotReadyError,
    AnalysisRunDatasetUnavailableError,
    AnalysisRunPersistenceConflictError,
    AnalysisRunSemanticMappingUnavailableError,
    AnalysisRunUnavailableError,
)
from incrementality_api.application.analysis_runs.manage_analysis_runs import (
    GetAnalysisRun,
    GetAnalysisRunQuery,
    QueueAnalysisRun,
    QueueAnalysisRunCommand,
)
from incrementality_api.application.authorization.authenticate_workspace import (
    AuthorizedWorkspacePrincipal,
)
from incrementality_api.domain.analysis_runs.entities import (
    AnalysisRun,
)
from incrementality_api.domain.analysis_runs.errors import (
    InvalidAnalysisRunError,
)
from incrementality_api.domain.authorization.permissions import (
    WorkspacePermission,
)

router = APIRouter(
    prefix=("/workspaces/{workspace_id}/projects/{project_id}/analysis-runs"),
    tags=["analysis-runs"],
)

_require_view_workspace = RequireWorkspacePermission(
    WorkspacePermission.VIEW_WORKSPACE,
)

_require_manage_datasets = RequireWorkspacePermission(
    WorkspacePermission.MANAGE_DATASETS,
)


def _to_response(
    run: AnalysisRun,
) -> AnalysisRunResponse:
    parsed_configuration: object = json.loads(run.configuration_json)

    if not isinstance(
        parsed_configuration,
        dict,
    ):
        raise RuntimeError("Persisted analysis configuration must be a JSON object.")

    configuration = cast(
        dict[str, object],
        parsed_configuration,
    )

    return AnalysisRunResponse(
        id=run.id,
        workspace_id=run.workspace_id,
        project_id=run.project_id,
        dataset_id=run.dataset_id,
        semantic_mapping_id=(run.semantic_mapping_id),
        semantic_mapping_version=(run.semantic_mapping_version),
        created_by_user_id=(run.created_by_user_id),
        estimator_type=run.estimator_type,
        estimator_version=(run.estimator_version),
        configuration=configuration,
        status=run.status,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        failure_reason=run.failure_reason,
        cancellation_reason=(run.cancellation_reason),
    )


@router.post(
    "",
    response_model=AnalysisRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def queue_project_analysis_run(
    workspace_id: UUID,
    project_id: UUID,
    request: QueueAnalysisRunRequest,
    principal: Annotated[
        AuthorizedWorkspacePrincipal,
        Depends(_require_manage_datasets),
    ],
    service: Annotated[
        QueueAnalysisRun,
        Depends(get_queue_analysis_run_service),
    ],
) -> AnalysisRunResponse:
    try:
        run = await service.execute(
            QueueAnalysisRunCommand(
                workspace_id=workspace_id,
                project_id=project_id,
                dataset_id=request.dataset_id,
                semantic_mapping_version=(request.semantic_mapping_version),
                created_by_user_id=(principal.user_id),
                estimator_type=(request.estimator_type),
                estimator_version=(request.estimator_version),
                configuration_json=json.dumps(
                    request.configuration,
                ),
            )
        )
    except (
        AnalysisRunDatasetUnavailableError,
        AnalysisRunSemanticMappingUnavailableError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except (
        AnalysisRunDatasetNotReadyError,
        AnalysisRunDataQualityBlockedError,
        AnalysisRunPersistenceConflictError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except InvalidAnalysisRunError as error:
        raise HTTPException(
            status_code=(status.HTTP_422_UNPROCESSABLE_CONTENT),
            detail=str(error),
        ) from error

    return _to_response(run)


@router.get(
    "/{analysis_run_id}",
    response_model=AnalysisRunResponse,
    status_code=status.HTTP_200_OK,
)
async def read_project_analysis_run(
    workspace_id: UUID,
    project_id: UUID,
    analysis_run_id: UUID,
    principal: Annotated[
        AuthorizedWorkspacePrincipal,
        Depends(_require_view_workspace),
    ],
    service: Annotated[
        GetAnalysisRun,
        Depends(get_analysis_run_service),
    ],
) -> AnalysisRunResponse:
    del principal

    try:
        run = await service.execute(
            GetAnalysisRunQuery(
                workspace_id=workspace_id,
                project_id=project_id,
                analysis_run_id=analysis_run_id,
            )
        )
    except AnalysisRunUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return _to_response(run)
