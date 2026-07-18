from incrementality_api.application.projects.create_project import (
    CreateProject,
)
from incrementality_api.application.projects.manage_projects import (
    GetWorkspaceProject,
    GetWorkspaceProjectOverview,
    ListWorkspaceProjects,
    UpdateWorkspaceProject,
)
from incrementality_api.infrastructure.database.session import (
    get_session_factory,
)
from incrementality_api.infrastructure.database.unit_of_work.projects import (
    SqlAlchemyProjectUnitOfWork,
)


def get_create_project_service() -> CreateProject:
    """Construct the production project-creation use case."""

    return CreateProject(
        unit_of_work=SqlAlchemyProjectUnitOfWork(
            session_factory=get_session_factory(),
        )
    )


def get_list_workspace_projects_service() -> ListWorkspaceProjects:
    return ListWorkspaceProjects(
        unit_of_work=SqlAlchemyProjectUnitOfWork(
            session_factory=get_session_factory(),
        )
    )


def get_workspace_project_service() -> GetWorkspaceProject:
    return GetWorkspaceProject(
        unit_of_work=SqlAlchemyProjectUnitOfWork(
            session_factory=get_session_factory(),
        )
    )


def get_project_overview_service() -> GetWorkspaceProjectOverview:
    return GetWorkspaceProjectOverview(
        unit_of_work=SqlAlchemyProjectUnitOfWork(
            session_factory=get_session_factory(),
        )
    )


def get_update_workspace_project_service() -> UpdateWorkspaceProject:
    return UpdateWorkspaceProject(
        unit_of_work=SqlAlchemyProjectUnitOfWork(
            session_factory=get_session_factory(),
        )
    )
