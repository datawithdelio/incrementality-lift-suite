from dataclasses import dataclass
from types import TracebackType
from typing import Protocol
from uuid import UUID

from incrementality_api.domain.projects.entities import Project


@dataclass(frozen=True, slots=True)
class ProjectWorkflowSnapshot:
    latest_dataset_id: UUID | None
    latest_dataset_status: str | None
    semantic_mapping_configured: bool
    latest_analysis_run_id: UUID | None
    latest_analysis_run_status: str | None


class ProjectRepository(Protocol):
    async def list_by_workspace(
        self,
        *,
        workspace_id: UUID,
    ) -> list[Project]:
        """List active projects inside one workspace."""

    async def get_by_workspace_and_slug(
        self,
        *,
        workspace_id: UUID,
        slug: str,
    ) -> Project | None:
        """Find a project by its workspace-scoped slug."""

    async def get_by_workspace_and_id(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
    ) -> Project | None:
        """Find one project without crossing a workspace boundary."""

    async def add(
        self,
        project: Project,
    ) -> None:
        """Stage a new project for persistence."""

    async def save(
        self,
        project: Project,
    ) -> None:
        """Stage updates to an existing project."""

    async def get_workflow_snapshot(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
    ) -> ProjectWorkflowSnapshot:
        """Read the latest persisted workflow state for one project."""


class ProjectUnitOfWork(Protocol):
    projects: ProjectRepository

    async def __aenter__(
        self,
    ) -> "ProjectUnitOfWork":
        """Open the project transaction."""

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Roll back failures and close the transaction."""

    async def commit(self) -> None:
        """Commit the project transaction."""
