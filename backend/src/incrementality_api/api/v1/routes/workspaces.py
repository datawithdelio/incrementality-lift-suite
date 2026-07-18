from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from incrementality_api.api.dependencies.session import (
    get_validated_session,
)
from incrementality_api.api.dependencies.tenancy import (
    get_create_workspace_service,
    get_list_user_workspaces_service,
)
from incrementality_api.api.v1.schemas.tenancy import (
    AccessibleWorkspaceResponse,
    CreateWorkspaceRequest,
    CreateWorkspaceResponse,
)
from incrementality_api.application.authentication.validate_session import (
    ValidatedSession,
)
from incrementality_api.application.tenancy.create_workspace import (
    CreateWorkspace,
    CreateWorkspaceCommand,
)
from incrementality_api.application.tenancy.errors import (
    TenancyConflictError,
)
from incrementality_api.application.tenancy.list_user_workspaces import (
    ListUserWorkspaces,
)

router = APIRouter(
    prefix="/workspaces",
    tags=["workspaces"],
)


@router.get(
    "",
    response_model=list[AccessibleWorkspaceResponse],
    status_code=status.HTTP_200_OK,
)
async def list_workspaces(
    session: Annotated[
        ValidatedSession,
        Depends(get_validated_session),
    ],
    workspace_service: Annotated[
        ListUserWorkspaces,
        Depends(get_list_user_workspaces_service),
    ],
) -> list[AccessibleWorkspaceResponse]:
    workspaces = await workspace_service.execute(
        user_id=session.user_id,
    )

    return [
        AccessibleWorkspaceResponse(
            workspace_id=workspace.workspace_id,
            organization_id=workspace.organization_id,
            name=workspace.name,
            slug=workspace.slug,
            role=workspace.role,
        )
        for workspace in workspaces
    ]


@router.post(
    "",
    response_model=CreateWorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workspace(
    request: CreateWorkspaceRequest,
    session: Annotated[
        ValidatedSession,
        Depends(get_validated_session),
    ],
    workspace_service: Annotated[
        CreateWorkspace,
        Depends(get_create_workspace_service),
    ],
) -> CreateWorkspaceResponse:
    try:
        result = await workspace_service.execute(
            CreateWorkspaceCommand(
                user_id=session.user_id,
                organization_name=request.organization_name,
                workspace_name=request.workspace_name,
            )
        )
    except TenancyConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A workspace with this information "
                "already exists."
            ),
        ) from error

    return CreateWorkspaceResponse(
        organization_id=result.organization_id,
        workspace_id=result.workspace_id,
        membership_id=result.membership_id,
    )
