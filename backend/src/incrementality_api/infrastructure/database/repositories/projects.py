from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from incrementality_api.application.projects.errors import (
    DuplicateProjectSlugError,
)
from incrementality_api.domain.projects.entities import Project
from incrementality_api.domain.projects.status import (
    ProjectStatus,
)
from incrementality_api.infrastructure.database.models.projects import (
    ProjectModel,
)


def to_project_model(project: Project) -> ProjectModel:
    return ProjectModel(
        id=project.id,
        workspace_id=project.workspace_id,
        created_by_user_id=project.created_by_user_id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        status=project.status.value,
        archived_at=project.archived_at,
        created_at=project.created_at,
        updated_at=project.created_at,
    )


def to_project_entity(model: ProjectModel) -> Project:
    return Project(
        id=model.id,
        workspace_id=model.workspace_id,
        created_by_user_id=model.created_by_user_id,
        name=model.name,
        slug=model.slug,
        description=model.description,
        status=ProjectStatus(model.status),
        created_at=model.created_at,
        archived_at=model.archived_at,
    )


class SqlAlchemyProjectRepository:
    """Persist and retrieve workspace-scoped projects."""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def get_by_workspace_and_slug(
        self,
        *,
        workspace_id: UUID,
        slug: str,
    ) -> Project | None:
        statement = select(ProjectModel).where(
            ProjectModel.workspace_id == workspace_id,
            ProjectModel.slug == slug,
        )

        model = await self._session.scalar(statement)

        if model is None:
            return None

        return to_project_entity(model)

    async def add(
        self,
        project: Project,
    ) -> None:
        self._session.add(
            to_project_model(project),
        )

        try:
            await self._session.flush()
        except IntegrityError as error:
            await self._session.rollback()

            raise DuplicateProjectSlugError(
                "A project with this slug already exists in the workspace."
            ) from error
