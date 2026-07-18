from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from incrementality_api.application.projects.errors import (
    DuplicateProjectSlugError,
)
from incrementality_api.application.projects.ports import ProjectWorkflowSnapshot
from incrementality_api.domain.projects.entities import Project
from incrementality_api.domain.projects.status import (
    ProjectStatus,
)
from incrementality_api.infrastructure.database.models.analysis_runs import (
    AnalysisRunModel,
)
from incrementality_api.infrastructure.database.models.dataset_semantic_mappings import (
    DatasetSemanticMappingModel,
)
from incrementality_api.infrastructure.database.models.datasets import DatasetModel
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

    async def list_by_workspace(
        self,
        *,
        workspace_id: UUID,
    ) -> list[Project]:
        statement = (
            select(ProjectModel)
            .where(
                ProjectModel.workspace_id == workspace_id,
                ProjectModel.status == ProjectStatus.ACTIVE.value,
            )
            .order_by(
                ProjectModel.created_at.desc(),
                ProjectModel.id,
            )
        )

        models = await self._session.scalars(statement)
        return [to_project_entity(model) for model in models]

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

    async def get_by_workspace_and_id(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
    ) -> Project | None:
        statement = select(ProjectModel).where(
            ProjectModel.workspace_id == workspace_id,
            ProjectModel.id == project_id,
            ProjectModel.status == ProjectStatus.ACTIVE.value,
        )

        model = await self._session.scalar(statement)
        return None if model is None else to_project_entity(model)

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

    async def save(self, project: Project) -> None:
        statement = select(ProjectModel).where(
            ProjectModel.workspace_id == project.workspace_id,
            ProjectModel.id == project.id,
        )
        model = await self._session.scalar(statement)

        if model is None:
            return

        model.name = project.name
        model.description = project.description
        model.status = project.status.value
        model.archived_at = project.archived_at
        await self._session.flush()

    async def get_workflow_snapshot(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
    ) -> ProjectWorkflowSnapshot:
        latest_dataset = await self._session.scalar(
            select(DatasetModel)
            .where(
                DatasetModel.workspace_id == workspace_id,
                DatasetModel.project_id == project_id,
            )
            .order_by(DatasetModel.created_at.desc(), DatasetModel.id)
            .limit(1)
        )
        latest_run = await self._session.scalar(
            select(AnalysisRunModel)
            .where(
                AnalysisRunModel.workspace_id == workspace_id,
                AnalysisRunModel.project_id == project_id,
            )
            .order_by(AnalysisRunModel.created_at.desc(), AnalysisRunModel.id)
            .limit(1)
        )
        mapping_id = None
        if latest_dataset is not None:
            mapping_id = await self._session.scalar(
                select(DatasetSemanticMappingModel.id)
                .where(DatasetSemanticMappingModel.dataset_id == latest_dataset.id)
                .limit(1)
            )

        return ProjectWorkflowSnapshot(
            latest_dataset_id=None if latest_dataset is None else latest_dataset.id,
            latest_dataset_status=None if latest_dataset is None else latest_dataset.status,
            semantic_mapping_configured=mapping_id is not None,
            latest_analysis_run_id=None if latest_run is None else latest_run.id,
            latest_analysis_run_status=None if latest_run is None else latest_run.status,
        )
