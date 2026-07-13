from dataclasses import dataclass
from uuid import UUID

from incrementality_api.application.projects.errors import (
    DuplicateProjectSlugError,
)
from incrementality_api.application.projects.ports import (
    ProjectUnitOfWork,
)
from incrementality_api.domain.projects.entities import Project


@dataclass(frozen=True, slots=True)
class CreateProjectCommand:
    workspace_id: UUID
    created_by_user_id: UUID
    name: str
    slug: str
    description: str | None = None


class CreateProject:
    """Create one project inside one workspace."""

    def __init__(
        self,
        *,
        unit_of_work: ProjectUnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        command: CreateProjectCommand,
    ) -> Project:
        async with self._unit_of_work:
            project = Project.create(
                workspace_id=command.workspace_id,
                created_by_user_id=command.created_by_user_id,
                name=command.name,
                slug=command.slug,
                description=command.description,
            )

            existing_project = await self._unit_of_work.projects.get_by_workspace_and_slug(
                workspace_id=project.workspace_id,
                slug=project.slug,
            )

            if existing_project is not None:
                raise DuplicateProjectSlugError(
                    "A project with this slug already exists in the workspace."
                )

            await self._unit_of_work.projects.add(project)
            await self._unit_of_work.commit()

            return project
