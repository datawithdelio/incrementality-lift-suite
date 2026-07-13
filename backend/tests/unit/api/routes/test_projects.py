from datetime import UTC, datetime
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from incrementality_api.api.dependencies.authorization import (
    get_authenticate_workspace_service,
)
from incrementality_api.api.dependencies.projects import (
    get_create_project_service,
)
from incrementality_api.api.v1.routes.projects import (
    router as projects_router,
)
from incrementality_api.application.authorization.authenticate_workspace import (
    AuthorizedWorkspacePrincipal,
)
from incrementality_api.application.projects.create_project import (
    CreateProjectCommand,
)
from incrementality_api.application.projects.errors import (
    DuplicateProjectSlugError,
)
from incrementality_api.domain.authorization.permissions import (
    WorkspacePermission,
)
from incrementality_api.domain.projects.entities import Project
from incrementality_api.domain.projects.errors import (
    InvalidProjectError,
)
from incrementality_api.domain.tenancy.roles import WorkspaceRole

EXPIRES_AT = datetime(
    2026,
    7,
    14,
    12,
    0,
    tzinfo=UTC,
)


class StubAuthenticateWorkspaceAction:
    def __init__(
        self,
        principal: AuthorizedWorkspacePrincipal,
    ) -> None:
        self._principal = principal

    async def execute(
        self,
        *,
        raw_token: str,
        workspace_id: object,
        permission: WorkspacePermission,
    ) -> AuthorizedWorkspacePrincipal:
        del raw_token, workspace_id

        assert permission is (WorkspacePermission.MANAGE_PROJECTS)

        return self._principal


class StubCreateProject:
    def __init__(
        self,
        *,
        result: Project | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.received_command: CreateProjectCommand | None = None

    async def execute(
        self,
        command: CreateProjectCommand,
    ) -> Project:
        self.received_command = command

        if self._error is not None:
            raise self._error

        if self._result is None:
            raise AssertionError("Project result was not configured.")

        return self._result


def build_principal(
    *,
    workspace_id: object,
    user_id: object,
) -> AuthorizedWorkspacePrincipal:
    return AuthorizedWorkspacePrincipal(
        session_id=uuid4(),
        user_id=user_id,
        workspace_id=workspace_id,
        membership_id=uuid4(),
        role=WorkspaceRole.ANALYST,
        permission=WorkspacePermission.MANAGE_PROJECTS,
        session_expires_at=EXPIRES_AT,
    )


def build_client(
    *,
    service: StubCreateProject,
    principal: AuthorizedWorkspacePrincipal,
) -> TestClient:
    application = FastAPI()
    application.include_router(projects_router)

    application.dependency_overrides[get_create_project_service] = lambda: service

    application.dependency_overrides[get_authenticate_workspace_service] = lambda: (
        StubAuthenticateWorkspaceAction(
            principal,
        )
    )

    return TestClient(
        application,
        raise_server_exceptions=False,
    )


def test_authorized_user_creates_project() -> None:
    workspace_id = uuid4()
    user_id = uuid4()

    project = Project.create(
        workspace_id=workspace_id,
        created_by_user_id=user_id,
        name="Paid Search Incrementality",
        slug="paid-search-lift",
        description="Geo holdout study.",
    )

    service = StubCreateProject(
        result=project,
    )

    client = build_client(
        service=service,
        principal=build_principal(
            workspace_id=workspace_id,
            user_id=user_id,
        ),
    )

    response = client.post(
        f"/workspaces/{workspace_id}/projects",
        headers={
            "Authorization": "Bearer valid-token",
        },
        json={
            "name": "Paid Search Incrementality",
            "slug": "paid-search-lift",
            "description": "Geo holdout study.",
        },
    )

    assert response.status_code == 201
    assert response.json()["id"] == str(project.id)
    assert response.json()["workspace_id"] == str(workspace_id)
    assert response.json()["created_by_user_id"] == str(user_id)
    assert response.json()["status"] == "active"

    assert service.received_command is not None
    assert service.received_command.workspace_id == workspace_id
    assert service.received_command.created_by_user_id == (user_id)


def test_duplicate_project_slug_returns_409() -> None:
    workspace_id = uuid4()
    user_id = uuid4()

    service = StubCreateProject(
        error=DuplicateProjectSlugError("A project with this slug already exists in the workspace.")
    )

    client = build_client(
        service=service,
        principal=build_principal(
            workspace_id=workspace_id,
            user_id=user_id,
        ),
    )

    response = client.post(
        f"/workspaces/{workspace_id}/projects",
        headers={
            "Authorization": "Bearer valid-token",
        },
        json={
            "name": "Duplicate Project",
            "slug": "duplicate-project",
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": ("A project with this slug already exists in the workspace.")
    }


def test_invalid_project_returns_422() -> None:
    workspace_id = uuid4()
    user_id = uuid4()

    service = StubCreateProject(error=InvalidProjectError("Project name must not be blank."))

    client = build_client(
        service=service,
        principal=build_principal(
            workspace_id=workspace_id,
            user_id=user_id,
        ),
    )

    response = client.post(
        f"/workspaces/{workspace_id}/projects",
        headers={
            "Authorization": "Bearer valid-token",
        },
        json={
            "name": "   ",
            "slug": "valid-project",
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Project name must not be blank.",
    }


def test_client_cannot_supply_project_creator() -> None:
    workspace_id = uuid4()
    user_id = uuid4()

    service = StubCreateProject()

    client = build_client(
        service=service,
        principal=build_principal(
            workspace_id=workspace_id,
            user_id=user_id,
        ),
    )

    response = client.post(
        f"/workspaces/{workspace_id}/projects",
        headers={
            "Authorization": "Bearer valid-token",
        },
        json={
            "name": "Protected Creator",
            "slug": "protected-creator",
            "created_by_user_id": str(uuid4()),
        },
    )

    assert response.status_code == 422
    assert service.received_command is None
