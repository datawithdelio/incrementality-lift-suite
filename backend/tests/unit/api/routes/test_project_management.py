from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from incrementality_api.api.dependencies.authorization import (
    get_authenticate_workspace_service,
)
from incrementality_api.api.dependencies.projects import (
    get_list_workspace_projects_service,
    get_project_overview_service,
    get_update_workspace_project_service,
    get_workspace_project_service,
)
from incrementality_api.api.v1.routes.projects import router as projects_router
from incrementality_api.application.authorization.authenticate_workspace import (
    AuthorizedWorkspacePrincipal,
)
from incrementality_api.application.projects.errors import ProjectUnavailableError
from incrementality_api.application.projects.manage_projects import WorkspaceProjectOverview
from incrementality_api.application.projects.ports import ProjectWorkflowSnapshot
from incrementality_api.domain.authorization.permissions import WorkspacePermission
from incrementality_api.domain.projects.entities import Project
from incrementality_api.domain.tenancy.roles import WorkspaceRole


class StubAuthenticateWorkspace:
    async def execute(
        self,
        *,
        raw_token: str,
        workspace_id: UUID,
        permission: WorkspacePermission,
    ) -> AuthorizedWorkspacePrincipal:
        del raw_token
        return AuthorizedWorkspacePrincipal(
            session_id=uuid4(),
            user_id=uuid4(),
            workspace_id=workspace_id,
            membership_id=uuid4(),
            role=WorkspaceRole.VIEWER,
            permission=permission,
            session_expires_at=datetime(2026, 8, 1, tzinfo=UTC),
        )


class StubListWorkspaceProjects:
    def __init__(self, projects: list[Project]) -> None:
        self._projects = projects
        self.workspace_id: UUID | None = None

    async def execute(self, *, workspace_id: UUID) -> list[Project]:
        self.workspace_id = workspace_id
        return self._projects


class StubGetWorkspaceProject:
    def __init__(
        self,
        project: Project | None = None,
        error: Exception | None = None,
    ) -> None:
        self._project = project
        self._error = error
        self.received: tuple[UUID, UUID] | None = None

    async def execute(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
    ) -> Project:
        self.received = (workspace_id, project_id)
        if self._error is not None:
            raise self._error
        if self._project is None:
            raise AssertionError("Project result was not configured.")
        return self._project


class StubUpdateWorkspaceProject:
    def __init__(self, project: Project) -> None:
        self._project = project
        self.received: tuple[UUID, UUID, str, str | None] | None = None

    async def execute(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        name: str,
        description: str | None,
    ) -> Project:
        self.received = (workspace_id, project_id, name, description)
        return self._project.update_details(name=name, description=description)


class StubGetProjectOverview:
    def __init__(self, result: WorkspaceProjectOverview) -> None:
        self._result = result

    async def execute(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
    ) -> WorkspaceProjectOverview:
        assert workspace_id == self._result.project.workspace_id
        assert project_id == self._result.project.id
        return self._result


def test_lists_workspace_projects_with_real_project_details() -> None:
    workspace_id = uuid4()
    project = Project.create(
        workspace_id=workspace_id,
        created_by_user_id=uuid4(),
        name="Paid Search Lift",
        slug="paid-search-lift",
        description="Q3 incrementality study.",
    )
    service = StubListWorkspaceProjects([project])
    application = FastAPI()
    application.include_router(projects_router)
    application.dependency_overrides[get_authenticate_workspace_service] = StubAuthenticateWorkspace
    application.dependency_overrides[get_list_workspace_projects_service] = lambda: service
    client = TestClient(application, raise_server_exceptions=False)

    response = client.get(
        f"/workspaces/{workspace_id}/projects",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(project.id),
            "workspace_id": str(project.workspace_id),
            "created_by_user_id": str(project.created_by_user_id),
            "name": project.name,
            "slug": project.slug,
            "description": project.description,
            "status": "active",
            "created_at": project.created_at.isoformat().replace("+00:00", "Z"),
            "archived_at": None,
        }
    ]
    assert service.workspace_id == workspace_id


def test_opens_one_project_through_workspace_scoped_route() -> None:
    workspace_id = uuid4()
    project = Project.create(
        workspace_id=workspace_id,
        created_by_user_id=uuid4(),
        name="Geo Holdout",
        slug="geo-holdout",
    )
    service = StubGetWorkspaceProject(project)
    application = FastAPI()
    application.include_router(projects_router)
    application.dependency_overrides[get_authenticate_workspace_service] = StubAuthenticateWorkspace
    application.dependency_overrides[get_workspace_project_service] = lambda: service
    client = TestClient(application, raise_server_exceptions=False)

    response = client.get(
        f"/workspaces/{workspace_id}/projects/{project.id}",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(project.id)
    assert response.json()["name"] == "Geo Holdout"
    assert service.received == (workspace_id, project.id)


def test_cross_workspace_project_lookup_is_not_disclosed() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    service = StubGetWorkspaceProject(
        error=ProjectUnavailableError("Project is unavailable."),
    )
    application = FastAPI()
    application.include_router(projects_router)
    application.dependency_overrides[get_authenticate_workspace_service] = StubAuthenticateWorkspace
    application.dependency_overrides[get_workspace_project_service] = lambda: service
    client = TestClient(application, raise_server_exceptions=False)

    response = client.get(
        f"/workspaces/{workspace_id}/projects/{project_id}",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Project is unavailable."}


def test_renames_project_without_accepting_identity_fields() -> None:
    workspace_id = uuid4()
    project = Project.create(
        workspace_id=workspace_id,
        created_by_user_id=uuid4(),
        name="Original Name",
        slug="stable-project-url",
    )
    service = StubUpdateWorkspaceProject(project)
    application = FastAPI()
    application.include_router(projects_router)
    application.dependency_overrides[get_authenticate_workspace_service] = StubAuthenticateWorkspace
    application.dependency_overrides[get_update_workspace_project_service] = lambda: service
    client = TestClient(application, raise_server_exceptions=False)

    response = client.patch(
        f"/workspaces/{workspace_id}/projects/{project.id}",
        headers={"Authorization": "Bearer valid-token"},
        json={
            "name": "Renamed Project",
            "description": "Updated scope.",
        },
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Renamed Project"
    assert response.json()["slug"] == "stable-project-url"
    assert service.received == (
        workspace_id,
        project.id,
        "Renamed Project",
        "Updated scope.",
    )


def test_returns_real_project_workflow_statuses() -> None:
    workspace_id = uuid4()
    project = Project.create(
        workspace_id=workspace_id,
        created_by_user_id=uuid4(),
        name="Lifecycle",
        slug="lifecycle",
    )
    dataset_id = uuid4()
    run_id = uuid4()
    service = StubGetProjectOverview(
        WorkspaceProjectOverview(
            project=project,
            workflow=ProjectWorkflowSnapshot(
                latest_dataset_id=dataset_id,
                latest_dataset_status="ready",
                semantic_mapping_configured=True,
                latest_analysis_run_id=run_id,
                latest_analysis_run_status="running",
            ),
        )
    )
    application = FastAPI()
    application.include_router(projects_router)
    application.dependency_overrides[get_authenticate_workspace_service] = StubAuthenticateWorkspace
    application.dependency_overrides[get_project_overview_service] = lambda: service
    client = TestClient(application, raise_server_exceptions=False)

    response = client.get(
        f"/workspaces/{workspace_id}/projects/{project.id}/overview",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    assert response.json()["latest_dataset_id"] == str(dataset_id)
    assert response.json()["latest_dataset_status"] == "ready"
    assert response.json()["semantic_mapping_configured"] is True
    assert response.json()["latest_analysis_run_id"] == str(run_id)
    assert response.json()["latest_analysis_run_status"] == "running"
