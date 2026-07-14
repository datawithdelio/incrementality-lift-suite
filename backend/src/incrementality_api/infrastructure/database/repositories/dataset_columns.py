from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from incrementality_api.application.datasets.errors import (
    DatasetPersistenceConflictError,
)
from incrementality_api.domain.datasets.columns import (
    DatasetColumnProfile,
    DatasetColumnType,
)
from incrementality_api.infrastructure.database.models.dataset_columns import (
    DatasetColumnModel,
)
from incrementality_api.infrastructure.database.models.datasets import (
    DatasetModel,
)


def to_dataset_column_model(
    *,
    dataset_id: UUID,
    profile: DatasetColumnProfile,
) -> DatasetColumnModel:
    """Convert a discovered profile into persistence state."""

    return DatasetColumnModel(
        dataset_id=dataset_id,
        ordinal_position=profile.ordinal_position,
        source_name=profile.source_name,
        normalized_name=profile.normalized_name,
        inferred_type=profile.inferred_type.value,
        nullable=profile.nullable,
        missing_count=profile.missing_count,
    )


def to_dataset_column_profile(
    model: DatasetColumnModel,
) -> DatasetColumnProfile:
    """Convert persisted column metadata into a profile."""

    return DatasetColumnProfile(
        ordinal_position=model.ordinal_position,
        source_name=model.source_name,
        normalized_name=model.normalized_name,
        inferred_type=DatasetColumnType(
            model.inferred_type,
        ),
        nullable=model.nullable,
        missing_count=model.missing_count,
    )


class SqlAlchemyDatasetColumnRepository:
    """Persist and retrieve discovered dataset columns."""

    def __init__(
        self,
        *,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def replace_for_dataset(
        self,
        *,
        dataset_id: UUID,
        columns: tuple[
            DatasetColumnProfile,
            ...,
        ],
    ) -> None:
        delete_statement = delete(
            DatasetColumnModel,
        ).where(
            DatasetColumnModel.dataset_id == dataset_id,
        )

        await self._session.execute(
            delete_statement,
        )

        self._session.add_all(
            [
                to_dataset_column_model(
                    dataset_id=dataset_id,
                    profile=profile,
                )
                for profile in columns
            ]
        )

        try:
            await self._session.flush()
        except IntegrityError as error:
            await self._session.rollback()

            raise DatasetPersistenceConflictError(
                "Dataset column metadata conflicts with existing records."
            ) from error

    async def list_by_scope(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        dataset_id: UUID,
    ) -> tuple[
        DatasetColumnProfile,
        ...,
    ]:
        statement = (
            select(DatasetColumnModel)
            .join(
                DatasetModel,
                DatasetModel.id == DatasetColumnModel.dataset_id,
            )
            .where(
                DatasetModel.id == dataset_id,
                DatasetModel.workspace_id == workspace_id,
                DatasetModel.project_id == project_id,
            )
            .order_by(
                DatasetColumnModel.ordinal_position,
            )
        )

        models = await self._session.scalars(
            statement,
        )

        return tuple(to_dataset_column_profile(model) for model in models.all())
