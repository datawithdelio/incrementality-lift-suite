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
    get_list_workspace_projects_service,
    get_project_overview_service,
    get_update_workspace_project_service,
    get_workspace_project_service,
)
from incrementality_api.api.v1.schemas.projects import (
    CreateProjectRequest,
    ProjectOverviewResponse,
    ProjectResponse,
    UpdateProjectRequest,
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
    ProjectUnavailableError,
)
from incrementality_api.application.projects.manage_projects import (
    GetWorkspaceProject,
    GetWorkspaceProjectOverview,
    ListWorkspaceProjects,
    UpdateWorkspaceProject,
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
_require_view_workspace = RequireWorkspacePermission(
    WorkspacePermission.VIEW_WORKSPACE,
)


def _project_response(project: object) -> ProjectResponse:
    return ProjectResponse.model_validate(project, from_attributes=True)


@router.get(
    "",
    response_model=list[ProjectResponse],
)
async def list_workspace_projects(
    workspace_id: UUID,
    _principal: Annotated[
        AuthorizedWorkspacePrincipal,
        Depends(_require_view_workspace),
    ],
    service: Annotated[
        ListWorkspaceProjects,
        Depends(get_list_workspace_projects_service),
    ],
) -> list[ProjectResponse]:
    projects = await service.execute(workspace_id=workspace_id)
    return [_project_response(project) for project in projects]


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
)
async def get_workspace_project(
    workspace_id: UUID,
    project_id: UUID,
    _principal: Annotated[
        AuthorizedWorkspacePrincipal,
        Depends(_require_view_workspace),
    ],
    service: Annotated[
        GetWorkspaceProject,
        Depends(get_workspace_project_service),
    ],
) -> ProjectResponse:
    try:
        project = await service.execute(
            workspace_id=workspace_id,
            project_id=project_id,
        )
    except ProjectUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return _project_response(project)


@router.get(
    "/{project_id}/overview",
    response_model=ProjectOverviewResponse,
)
async def get_workspace_project_overview(
    workspace_id: UUID,
    project_id: UUID,
    _principal: Annotated[
        AuthorizedWorkspacePrincipal,
        Depends(_require_view_workspace),
    ],
    service: Annotated[
        GetWorkspaceProjectOverview,
        Depends(get_project_overview_service),
    ],
) -> ProjectOverviewResponse:
    try:
        overview = await service.execute(
            workspace_id=workspace_id,
            project_id=project_id,
        )
    except ProjectUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    project = overview.project
    workflow = overview.workflow
    return ProjectOverviewResponse(
        **_project_response(project).model_dump(),
        latest_dataset_id=workflow.latest_dataset_id,
        latest_dataset_status=workflow.latest_dataset_status,
        semantic_mapping_configured=workflow.semantic_mapping_configured,
        latest_analysis_run_id=workflow.latest_analysis_run_id,
        latest_analysis_run_status=workflow.latest_analysis_run_status,
    )


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
)
async def update_workspace_project(
    workspace_id: UUID,
    project_id: UUID,
    request: UpdateProjectRequest,
    _principal: Annotated[
        AuthorizedWorkspacePrincipal,
        Depends(_require_manage_projects),
    ],
    service: Annotated[
        UpdateWorkspaceProject,
        Depends(get_update_workspace_project_service),
    ],
) -> ProjectResponse:
    try:
        project = await service.execute(
            workspace_id=workspace_id,
            project_id=project_id,
            name=request.name,
            description=request.description,
        )
    except ProjectUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except InvalidProjectError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error

    return _project_response(project)


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

    return _project_response(project)
