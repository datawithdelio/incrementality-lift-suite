from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)

from incrementality_api.api.dependencies.authorization import (
    RequireWorkspacePermission,
)
from incrementality_api.api.dependencies.datasets import (
    get_create_dataset_semantic_mapping_service,
    get_list_dataset_columns_service,
    get_read_dataset_semantic_mapping_service,
    get_read_dataset_service,
    get_register_dataset_service,
    get_upload_dataset_service,
)
from incrementality_api.api.v1.schemas.datasets import (
    CreateDatasetSemanticMappingRequest,
    DatasetColumnResponse,
    DatasetResponse,
    DatasetSemanticMappingResponse,
    RegisterDatasetRequest,
)
from incrementality_api.application.authorization.authenticate_workspace import (
    AuthorizedWorkspacePrincipal,
)
from incrementality_api.application.datasets.errors import (
    DatasetPersistenceConflictError,
    DatasetProjectUnavailableError,
    DatasetSemanticMappingUnavailableError,
    DatasetTooLargeError,
    DatasetUnavailableError,
    DatasetUploadVerificationError,
)
from incrementality_api.application.datasets.manage_semantic_mapping import (
    CreateDatasetSemanticMapping,
    CreateDatasetSemanticMappingCommand,
    GetDatasetSemanticMapping,
    GetDatasetSemanticMappingQuery,
)
from incrementality_api.application.datasets.read_dataset import (
    GetDataset,
    GetDatasetQuery,
    ListDatasetColumns,
    ListDatasetColumnsQuery,
)
from incrementality_api.application.datasets.register_dataset import (
    RegisterDataset,
    RegisterDatasetCommand,
)
from incrementality_api.application.datasets.upload_dataset import (
    UploadDataset,
    UploadDatasetCommand,
)
from incrementality_api.domain.authorization.permissions import (
    WorkspacePermission,
)
from incrementality_api.domain.datasets.errors import (
    InvalidDatasetError,
    InvalidDatasetSemanticMappingError,
    InvalidDatasetTransitionError,
)

router = APIRouter(
    prefix=("/workspaces/{workspace_id}/projects/{project_id}/datasets"),
    tags=["datasets"],
)

_require_view_workspace = RequireWorkspacePermission(
    WorkspacePermission.VIEW_WORKSPACE,
)

_require_manage_datasets = RequireWorkspacePermission(
    WorkspacePermission.MANAGE_DATASETS,
)


@router.post(
    "",
    response_model=DatasetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_project_dataset(
    workspace_id: UUID,
    project_id: UUID,
    request: RegisterDatasetRequest,
    principal: Annotated[
        AuthorizedWorkspacePrincipal,
        Depends(_require_manage_datasets),
    ],
    service: Annotated[
        RegisterDataset,
        Depends(get_register_dataset_service),
    ],
) -> DatasetResponse:
    try:
        dataset = await service.execute(
            RegisterDatasetCommand(
                workspace_id=workspace_id,
                project_id=project_id,
                created_by_user_id=principal.user_id,
                source_filename=request.source_filename,
                media_type=request.media_type,
                byte_size=request.byte_size,
                checksum_sha256=request.checksum_sha256,
            )
        )
    except DatasetTooLargeError as error:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(error),
        ) from error
    except DatasetProjectUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except DatasetPersistenceConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except InvalidDatasetError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error

    return DatasetResponse.model_validate(dataset)


@router.get(
    "/{dataset_id}",
    response_model=DatasetResponse,
    status_code=status.HTTP_200_OK,
)
async def get_project_dataset(
    workspace_id: UUID,
    project_id: UUID,
    dataset_id: UUID,
    principal: Annotated[
        AuthorizedWorkspacePrincipal,
        Depends(_require_view_workspace),
    ],
    service: Annotated[
        GetDataset,
        Depends(get_read_dataset_service),
    ],
) -> DatasetResponse:
    del principal

    try:
        dataset = await service.execute(
            GetDatasetQuery(
                workspace_id=workspace_id,
                project_id=project_id,
                dataset_id=dataset_id,
            )
        )
    except DatasetUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return DatasetResponse.model_validate(dataset)


@router.get(
    "/{dataset_id}/columns",
    response_model=list[DatasetColumnResponse],
    status_code=status.HTTP_200_OK,
)
async def list_project_dataset_columns(
    workspace_id: UUID,
    project_id: UUID,
    dataset_id: UUID,
    principal: Annotated[
        AuthorizedWorkspacePrincipal,
        Depends(_require_view_workspace),
    ],
    service: Annotated[
        ListDatasetColumns,
        Depends(get_list_dataset_columns_service),
    ],
) -> list[DatasetColumnResponse]:
    del principal

    try:
        columns = await service.execute(
            ListDatasetColumnsQuery(
                workspace_id=workspace_id,
                project_id=project_id,
                dataset_id=dataset_id,
            )
        )
    except DatasetUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return [DatasetColumnResponse.model_validate(column) for column in columns]


@router.put(
    "/{dataset_id}/content",
    response_model=DatasetResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_project_dataset_content(
    workspace_id: UUID,
    project_id: UUID,
    dataset_id: UUID,
    request: Request,
    principal: Annotated[
        AuthorizedWorkspacePrincipal,
        Depends(_require_manage_datasets),
    ],
    service: Annotated[
        UploadDataset,
        Depends(get_upload_dataset_service),
    ],
    restore_missing: bool = False,
) -> DatasetResponse:
    del principal

    try:
        dataset = await service.execute(
            UploadDatasetCommand(
                workspace_id=workspace_id,
                project_id=project_id,
                dataset_id=dataset_id,
                chunks=request.stream(),
                restore_missing=restore_missing,
            )
        )
    except DatasetUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except DatasetUploadVerificationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    except InvalidDatasetTransitionError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    return DatasetResponse.model_validate(dataset)


@router.post(
    "/{dataset_id}/semantic-mappings",
    response_model=DatasetSemanticMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project_dataset_semantic_mapping(
    workspace_id: UUID,
    project_id: UUID,
    dataset_id: UUID,
    request: CreateDatasetSemanticMappingRequest,
    principal: Annotated[
        AuthorizedWorkspacePrincipal,
        Depends(_require_manage_datasets),
    ],
    service: Annotated[
        CreateDatasetSemanticMapping,
        Depends(get_create_dataset_semantic_mapping_service),
    ],
) -> DatasetSemanticMappingResponse:
    try:
        mapping = await service.execute(
            CreateDatasetSemanticMappingCommand(
                workspace_id=workspace_id,
                project_id=project_id,
                dataset_id=dataset_id,
                created_by_user_id=principal.user_id,
                time_column=request.time_column,
                unit_column=request.unit_column,
                treatment_column=(request.treatment_column),
                outcome_column=request.outcome_column,
                spend_column=request.spend_column,
                covariate_columns=(request.covariate_columns),
                treatment_value=(request.treatment_value),
                control_value=request.control_value,
            )
        )
    except DatasetUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except DatasetPersistenceConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except InvalidDatasetSemanticMappingError as error:
        raise HTTPException(
            status_code=(status.HTTP_422_UNPROCESSABLE_CONTENT),
            detail=str(error),
        ) from error

    return DatasetSemanticMappingResponse.model_validate(mapping)


@router.get(
    "/{dataset_id}/semantic-mappings/latest",
    response_model=DatasetSemanticMappingResponse,
    status_code=status.HTTP_200_OK,
)
async def get_latest_project_dataset_semantic_mapping(
    workspace_id: UUID,
    project_id: UUID,
    dataset_id: UUID,
    principal: Annotated[
        AuthorizedWorkspacePrincipal,
        Depends(_require_view_workspace),
    ],
    service: Annotated[
        GetDatasetSemanticMapping,
        Depends(get_read_dataset_semantic_mapping_service),
    ],
) -> DatasetSemanticMappingResponse:
    del principal

    try:
        mapping = await service.execute(
            GetDatasetSemanticMappingQuery(
                workspace_id=workspace_id,
                project_id=project_id,
                dataset_id=dataset_id,
            )
        )
    except DatasetSemanticMappingUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return DatasetSemanticMappingResponse.model_validate(mapping)


@router.get(
    "/{dataset_id}/semantic-mappings/{version}",
    response_model=DatasetSemanticMappingResponse,
    status_code=status.HTTP_200_OK,
)
async def get_project_dataset_semantic_mapping_version(
    workspace_id: UUID,
    project_id: UUID,
    dataset_id: UUID,
    version: int,
    principal: Annotated[
        AuthorizedWorkspacePrincipal,
        Depends(_require_view_workspace),
    ],
    service: Annotated[
        GetDatasetSemanticMapping,
        Depends(get_read_dataset_semantic_mapping_service),
    ],
) -> DatasetSemanticMappingResponse:
    del principal

    try:
        mapping = await service.execute(
            GetDatasetSemanticMappingQuery(
                workspace_id=workspace_id,
                project_id=project_id,
                dataset_id=dataset_id,
                version=version,
            )
        )
    except DatasetSemanticMappingUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return DatasetSemanticMappingResponse.model_validate(mapping)
