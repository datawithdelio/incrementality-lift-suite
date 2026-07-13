from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from incrementality_api.api.dependencies.authorization import (
    RequireWorkspacePermission,
)
from incrementality_api.api.dependencies.projects import (
    get_create_project_service,
)
from incrementality_api.api.v1.schemas.projects import (
    CreateProjectRequest,
    ProjectResponse,
)
from incrementality_api.application.authorization.authenticate_workspace import (
    AuthorizedWorkspacePrincipal,
)
from incrementality_api.application.projects.create_project import (
    CreateProject,
    CreateProjectCommand,
)
from incrementality_api.application.projects.errors import (
    DuplicateProjectSlugError,
)
from incrementality_api.domain.authorization.permissions import (
    WorkspacePermission,
)
from incrementality_api.domain.projects.errors import (
    InvalidProjectError,
)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/projects",
    tags=["projects"],
)

_require_manage_projects = RequireWorkspacePermission(
    WorkspacePermission.MANAGE_PROJECTS,
)


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workspace_project(
    workspace_id: UUID,
    request: CreateProjectRequest,
    principal: Annotated[
        AuthorizedWorkspacePrincipal,
        Depends(_require_manage_projects),
    ],
    service: Annotated[
        CreateProject,
        Depends(get_create_project_service),
    ],
) -> ProjectResponse:
    try:
        project = await service.execute(
            CreateProjectCommand(
                workspace_id=workspace_id,
                created_by_user_id=principal.user_id,
                name=request.name,
                slug=request.slug,
                description=request.description,
            )
        )
    except DuplicateProjectSlugError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except InvalidProjectError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error

    return ProjectResponse(
        id=project.id,
        workspace_id=project.workspace_id,
        created_by_user_id=project.created_by_user_id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        status=project.status,
        created_at=project.created_at,
        archived_at=project.archived_at,
    )
