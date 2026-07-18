from dataclasses import dataclass
from uuid import UUID

from incrementality_api.application.projects.errors import ProjectUnavailableError
from incrementality_api.application.projects.ports import (
    ProjectUnitOfWork,
    ProjectWorkflowSnapshot,
)
from incrementality_api.domain.projects.entities import Project


@dataclass(frozen=True, slots=True)
class WorkspaceProjectOverview:
    project: Project
    workflow: ProjectWorkflowSnapshot


class ListWorkspaceProjects:
    """Return active projects scoped to one authorized workspace."""

    def __init__(self, *, unit_of_work: ProjectUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self, *, workspace_id: UUID) -> list[Project]:
        async with self._unit_of_work:
            return await self._unit_of_work.projects.list_by_workspace(
                workspace_id=workspace_id,
            )


class GetWorkspaceProject:
    """Return one active project scoped to one authorized workspace."""

    def __init__(self, *, unit_of_work: ProjectUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
    ) -> Project:
        async with self._unit_of_work:
            project = await self._unit_of_work.projects.get_by_workspace_and_id(
                workspace_id=workspace_id,
                project_id=project_id,
            )

            if project is None:
                raise ProjectUnavailableError("Project is unavailable.")

            return project


class GetWorkspaceProjectOverview:
    """Return project identity plus its latest persisted workflow state."""

    def __init__(self, *, unit_of_work: ProjectUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
    ) -> WorkspaceProjectOverview:
        async with self._unit_of_work:
            project = await self._unit_of_work.projects.get_by_workspace_and_id(
                workspace_id=workspace_id,
                project_id=project_id,
            )
            if project is None:
                raise ProjectUnavailableError("Project is unavailable.")

            workflow = await self._unit_of_work.projects.get_workflow_snapshot(
                workspace_id=workspace_id,
                project_id=project_id,
            )
            return WorkspaceProjectOverview(project=project, workflow=workflow)


class UpdateWorkspaceProject:
    """Update mutable project details inside one authorized workspace."""

    def __init__(self, *, unit_of_work: ProjectUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        name: str,
        description: str | None,
    ) -> Project:
        async with self._unit_of_work:
            project = await self._unit_of_work.projects.get_by_workspace_and_id(
                workspace_id=workspace_id,
                project_id=project_id,
            )

            if project is None:
                raise ProjectUnavailableError("Project is unavailable.")

            updated_project = project.update_details(
                name=name,
                description=description,
            )
            await self._unit_of_work.projects.save(updated_project)
            await self._unit_of_work.commit()
            return updated_project
