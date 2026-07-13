from types import TracebackType
from typing import Protocol
from uuid import UUID

from incrementality_api.domain.projects.entities import Project


class ProjectRepository(Protocol):
    async def get_by_workspace_and_slug(
        self,
        *,
        workspace_id: UUID,
        slug: str,
    ) -> Project | None:
        """Find a project by its workspace-scoped slug."""

    async def add(
        self,
        project: Project,
    ) -> None:
        """Stage a new project for persistence."""


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
