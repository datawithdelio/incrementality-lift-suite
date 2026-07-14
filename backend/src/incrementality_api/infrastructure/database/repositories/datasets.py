from uuid import UUID

from sqlalchemy import select
from sqlalchemy import update as sql_update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from incrementality_api.application.datasets.errors import (
    DatasetPersistenceConflictError,
)
from incrementality_api.domain.datasets.entities import Dataset
from incrementality_api.domain.datasets.status import (
    DatasetStatus,
)
from incrementality_api.domain.projects.entities import Project
from incrementality_api.infrastructure.database.models.datasets import (
    DatasetModel,
)
from incrementality_api.infrastructure.database.models.projects import (
    ProjectModel,
)
from incrementality_api.infrastructure.database.repositories.projects import (
    to_project_entity,
)


def to_dataset_model(
    dataset: Dataset,
) -> DatasetModel:
    return DatasetModel(
        id=dataset.id,
        workspace_id=dataset.workspace_id,
        project_id=dataset.project_id,
        created_by_user_id=dataset.created_by_user_id,
        source_filename=dataset.source_filename,
        storage_key=dataset.storage_key,
        media_type=dataset.media_type,
        byte_size=dataset.byte_size,
        checksum_sha256=dataset.checksum_sha256,
        status=dataset.status.value,
        uploaded_at=dataset.uploaded_at,
        validation_started_at=dataset.validation_started_at,
        validation_completed_at=(dataset.validation_completed_at),
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        failure_reason=dataset.failure_reason,
        created_at=dataset.created_at,
        updated_at=dataset.created_at,
    )


def to_dataset_entity(
    model: DatasetModel,
) -> Dataset:
    return Dataset(
        id=model.id,
        workspace_id=model.workspace_id,
        project_id=model.project_id,
        created_by_user_id=model.created_by_user_id,
        source_filename=model.source_filename,
        storage_key=model.storage_key,
        media_type=model.media_type,
        byte_size=model.byte_size,
        checksum_sha256=model.checksum_sha256,
        status=DatasetStatus(model.status),
        created_at=model.created_at,
        uploaded_at=model.uploaded_at,
        validation_started_at=model.validation_started_at,
        validation_completed_at=(model.validation_completed_at),
        row_count=model.row_count,
        column_count=model.column_count,
        failure_reason=model.failure_reason,
    )


class SqlAlchemyDatasetRepository:
    """Persist and retrieve dataset metadata."""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def add(
        self,
        dataset: Dataset,
    ) -> None:
        self._session.add(
            to_dataset_model(dataset),
        )

        try:
            await self._session.flush()
        except IntegrityError as error:
            await self._session.rollback()

            raise DatasetPersistenceConflictError(
                "Dataset metadata conflicts with an existing record."
            ) from error

    async def get_by_id(
        self,
        dataset_id: UUID,
    ) -> Dataset | None:
        statement = select(DatasetModel).where(
            DatasetModel.id == dataset_id,
        )

        model = await self._session.scalar(statement)

        if model is None:
            return None

        return to_dataset_entity(model)

    async def get_by_scope(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        dataset_id: UUID,
    ) -> Dataset | None:
        statement = (
            select(DatasetModel)
            .where(
                DatasetModel.id == dataset_id,
                DatasetModel.workspace_id == workspace_id,
                DatasetModel.project_id == project_id,
            )
            .with_for_update()
        )

        model = await self._session.scalar(statement)

        if model is None:
            return None

        return to_dataset_entity(model)

    async def update(
        self,
        dataset: Dataset,
    ) -> None:
        statement = (
            sql_update(DatasetModel)
            .where(
                DatasetModel.id == dataset.id,
                DatasetModel.workspace_id == dataset.workspace_id,
                DatasetModel.project_id == dataset.project_id,
            )
            .values(
                status=dataset.status.value,
                uploaded_at=dataset.uploaded_at,
                validation_started_at=(dataset.validation_started_at),
                validation_completed_at=(dataset.validation_completed_at),
                row_count=dataset.row_count,
                column_count=dataset.column_count,
                failure_reason=dataset.failure_reason,
            )
        )

        await self._session.execute(statement)
        await self._session.flush()


class SqlAlchemyDatasetProjectReader:
    """Load projects used during dataset registration."""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def get_by_id(
        self,
        project_id: UUID,
    ) -> Project | None:
        statement = select(ProjectModel).where(
            ProjectModel.id == project_id,
        )

        model = await self._session.scalar(statement)

        if model is None:
            return None

        return to_project_entity(model)
