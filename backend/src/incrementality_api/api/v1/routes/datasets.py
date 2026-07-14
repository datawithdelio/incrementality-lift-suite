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
    get_register_dataset_service,
    get_upload_dataset_service,
)
from incrementality_api.api.v1.schemas.datasets import (
    DatasetResponse,
    RegisterDatasetRequest,
)
from incrementality_api.application.authorization.authenticate_workspace import (
    AuthorizedWorkspacePrincipal,
)
from incrementality_api.application.datasets.errors import (
    DatasetPersistenceConflictError,
    DatasetProjectUnavailableError,
    DatasetTooLargeError,
    DatasetUnavailableError,
    DatasetUploadVerificationError,
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
    InvalidDatasetTransitionError,
)

router = APIRouter(
    prefix=("/workspaces/{workspace_id}/projects/{project_id}/datasets"),
    tags=["datasets"],
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
) -> DatasetResponse:
    del principal

    try:
        dataset = await service.execute(
            UploadDatasetCommand(
                workspace_id=workspace_id,
                project_id=project_id,
                dataset_id=dataset_id,
                chunks=request.stream(),
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
