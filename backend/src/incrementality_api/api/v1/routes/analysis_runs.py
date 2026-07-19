import json
import secrets
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
    AnalysisRunLineageResponse,
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
from incrementality_api.domain.analysis_runs.estimator_versions import estimator_version_for
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


_SENSITIVE_CONFIGURATION_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "authorization",
        "client_secret",
        "password",
        "refresh_token",
        "secret",
        "token",
    }
)


def _is_sensitive_configuration_key(key: str) -> bool:
    normalized = key.strip().lower().replace("-", "_").replace(".", "_")

    return normalized in _SENSITIVE_CONFIGURATION_KEYS or normalized.endswith(
        (
            "_access_token",
            "_api_key",
            "_client_secret",
            "_password",
            "_refresh_token",
            "_secret",
            "_token",
        )
    )


def _redact_sensitive_configuration(
    value: object,
) -> object:
    if isinstance(value, dict):
        return {
            key: _redact_sensitive_configuration(item)
            for key, item in value.items()
            if isinstance(key, str)
            and not _is_sensitive_configuration_key(key)
        }

    if isinstance(value, list):
        return [
            _redact_sensitive_configuration(item)
            for item in value
        ]

    return value


def _to_lineage_response(
    run: AnalysisRun,
) -> AnalysisRunLineageResponse:
    parsed_configuration: object = json.loads(run.configuration_json)

    if not isinstance(parsed_configuration, dict):
        raise RuntimeError(
            "Persisted analysis configuration must be a JSON object."
        )

    estimator_configuration = cast(
        dict[str, object],
        _redact_sensitive_configuration(
            parsed_configuration,
        ),
    )

    return AnalysisRunLineageResponse(
        analysis_run_id=run.id,
        dataset_id=run.dataset_id,
        dataset_checksum_sha256=run.dataset_checksum_sha256,
        dataset_byte_size=run.dataset_byte_size,
        semantic_mapping_id=run.semantic_mapping_id,
        semantic_mapping_version=run.semantic_mapping_version,
        semantic_mapping_snapshot=(
            run.semantic_mapping_snapshot.as_dict()
            if run.semantic_mapping_snapshot is not None
            else None
        ),
        analysis_period_snapshot=(
            cast(dict[str, object], run.analysis_period_snapshot.as_dict())
            if run.analysis_period_snapshot is not None
            else None
        ),
        analysis_selection_snapshot=(
            run.analysis_selection_snapshot.as_dict()
            if run.analysis_selection_snapshot is not None
            else None
        ),
        treatment_control_snapshot=(
            run.treatment_control_snapshot.as_dict()
            if run.treatment_control_snapshot is not None
            else None
        ),
        estimand_snapshot=(
            cast(dict[str, object], run.estimand_snapshot.as_dict())
            if run.estimand_snapshot is not None
            else None
        ),
        estimator_type=run.estimator_type,
        estimator_version=run.estimator_version,
        estimator_configuration=estimator_configuration,
        random_seed=run.random_seed,
        application_version=run.application_version,
        source_revision=run.source_revision,
        statistical_library_versions=(
            run.statistical_library_versions.as_dict()
            if run.statistical_library_versions is not None
            else None
        ),
        input_fingerprint_sha256=run.input_fingerprint_sha256,
        created_at=run.created_at,
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
                estimator_version=estimator_version_for(
                    request.estimator_type,
                ),
                random_seed=secrets.randbits(32),
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



@router.get(
    "/{analysis_run_id}/lineage",
    response_model=AnalysisRunLineageResponse,
    status_code=status.HTTP_200_OK,
)
async def read_project_analysis_run_lineage(
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
) -> AnalysisRunLineageResponse:
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

    return _to_lineage_response(run)
