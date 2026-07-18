from types import TracebackType
from uuid import UUID, uuid4

import pytest

from incrementality_api.application.projects.errors import ProjectUnavailableError
from incrementality_api.application.projects.manage_projects import (
    GetWorkspaceProject,
    GetWorkspaceProjectOverview,
    ListWorkspaceProjects,
    UpdateWorkspaceProject,
)
from incrementality_api.application.projects.ports import ProjectWorkflowSnapshot
from incrementality_api.domain.projects.entities import Project


class FakeProjectRepository:
    def __init__(self, projects: list[Project]) -> None:
        self._projects = projects
        self.requested_workspace_id: UUID | None = None
        self.requested_project_id: UUID | None = None
        self.saved_project: Project | None = None
        self.workflow_snapshot = ProjectWorkflowSnapshot(
            latest_dataset_id=None,
            latest_dataset_status=None,
            semantic_mapping_configured=False,
            latest_analysis_run_id=None,
            latest_analysis_run_status=None,
        )

    async def list_by_workspace(
        self,
        *,
        workspace_id: UUID,
    ) -> list[Project]:
        self.requested_workspace_id = workspace_id
        return self._projects

    async def get_by_workspace_and_id(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
    ) -> Project | None:
        self.requested_workspace_id = workspace_id
        self.requested_project_id = project_id
        return next(
            (
                project
                for project in self._projects
                if project.workspace_id == workspace_id and project.id == project_id
            ),
            None,
        )

    async def save(self, project: Project) -> None:
        self.saved_project = project

    async def get_workflow_snapshot(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
    ) -> ProjectWorkflowSnapshot:
        self.requested_workspace_id = workspace_id
        self.requested_project_id = project_id
        return self.workflow_snapshot


class FakeProjectUnitOfWork:
    def __init__(self, projects: list[Project]) -> None:
        self.projects = FakeProjectRepository(projects)
        self.commit_count = 0

    async def __aenter__(self) -> "FakeProjectUnitOfWork":
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exception_type, exception, traceback

    async def commit(self) -> None:
        self.commit_count += 1


def make_project(workspace_id: UUID, name: str, slug: str) -> Project:
    return Project.create(
        workspace_id=workspace_id,
        created_by_user_id=uuid4(),
        name=name,
        slug=slug,
    )


@pytest.mark.asyncio
async def test_lists_only_projects_returned_for_requested_workspace() -> None:
    workspace_id = uuid4()
    projects = [
        make_project(workspace_id, "Summer Campaign", "summer-campaign"),
        make_project(workspace_id, "Geo Holdout", "geo-holdout"),
    ]
    unit_of_work = FakeProjectUnitOfWork(projects)

    result = await ListWorkspaceProjects(unit_of_work=unit_of_work).execute(
        workspace_id=workspace_id,
    )

    assert result == projects
    assert unit_of_work.projects.requested_workspace_id == workspace_id


@pytest.mark.asyncio
async def test_project_lookup_is_scoped_to_workspace() -> None:
    workspace_id = uuid4()
    other_workspace_id = uuid4()
    project = make_project(other_workspace_id, "Private Study", "private-study")
    unit_of_work = FakeProjectUnitOfWork([project])

    with pytest.raises(ProjectUnavailableError, match="Project is unavailable"):
        await GetWorkspaceProject(unit_of_work=unit_of_work).execute(
            workspace_id=workspace_id,
            project_id=project.id,
        )

    assert unit_of_work.projects.requested_workspace_id == workspace_id
    assert unit_of_work.projects.requested_project_id == project.id


@pytest.mark.asyncio
async def test_updates_project_details_and_commits_once() -> None:
    workspace_id = uuid4()
    project = make_project(workspace_id, "Summer Campaign", "summer-campaign")
    unit_of_work = FakeProjectUnitOfWork([project])

    updated = await UpdateWorkspaceProject(unit_of_work=unit_of_work).execute(
        workspace_id=workspace_id,
        project_id=project.id,
        name="Summer Incrementality",
        description="Measures paid social lift.",
    )

    assert updated.name == "Summer Incrementality"
    assert updated.description == "Measures paid social lift."
    assert updated.id == project.id
    assert updated.slug == project.slug
    assert unit_of_work.projects.saved_project == updated
    assert unit_of_work.commit_count == 1


@pytest.mark.asyncio
async def test_project_overview_combines_scoped_project_with_persisted_workflow() -> None:
    workspace_id = uuid4()
    project = make_project(workspace_id, "Search Lift", "search-lift")
    unit_of_work = FakeProjectUnitOfWork([project])
    unit_of_work.projects.workflow_snapshot = ProjectWorkflowSnapshot(
        latest_dataset_id=uuid4(),
        latest_dataset_status="ready",
        semantic_mapping_configured=True,
        latest_analysis_run_id=uuid4(),
        latest_analysis_run_status="running",
    )

    overview = await GetWorkspaceProjectOverview(unit_of_work=unit_of_work).execute(
        workspace_id=workspace_id,
        project_id=project.id,
    )

    assert overview.project == project
    assert overview.workflow == unit_of_work.projects.workflow_snapshot
