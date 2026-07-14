from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from incrementality_api.application.datasets.errors import (
    DatasetPersistenceConflictError,
)
from incrementality_api.domain.datasets.semantic_mapping import (
    DatasetSemanticMapping,
)
from incrementality_api.infrastructure.database.models.dataset_semantic_mappings import (
    DatasetMappingCovariateModel,
    DatasetSemanticMappingModel,
)
from incrementality_api.infrastructure.database.models.datasets import (
    DatasetModel,
)


def to_dataset_semantic_mapping_model(
    mapping: DatasetSemanticMapping,
) -> DatasetSemanticMappingModel:
    """Convert a semantic mapping into persisted state."""

    return DatasetSemanticMappingModel(
        id=mapping.id,
        dataset_id=mapping.dataset_id,
        created_by_user_id=mapping.created_by_user_id,
        version=mapping.version,
        time_column=mapping.time_column,
        unit_column=mapping.unit_column,
        treatment_column=mapping.treatment_column,
        outcome_column=mapping.outcome_column,
        spend_column=mapping.spend_column,
        treatment_value=mapping.treatment_value,
        control_value=mapping.control_value,
        created_at=mapping.created_at,
        updated_at=mapping.updated_at,
    )


def to_dataset_mapping_covariate_models(
    mapping: DatasetSemanticMapping,
) -> tuple[DatasetMappingCovariateModel, ...]:
    """Convert ordered domain covariates into persisted rows."""

    return tuple(
        DatasetMappingCovariateModel(
            mapping_id=mapping.id,
            dataset_id=mapping.dataset_id,
            ordinal_position=ordinal_position,
            normalized_column_name=column_name,
            created_at=mapping.created_at,
            updated_at=mapping.updated_at,
        )
        for ordinal_position, column_name in enumerate(
            mapping.covariate_columns,
            start=1,
        )
    )


def to_dataset_semantic_mapping(
    *,
    model: DatasetSemanticMappingModel,
    covariates: tuple[
        DatasetMappingCovariateModel,
        ...,
    ],
) -> DatasetSemanticMapping:
    """Reconstruct one semantic mapping from persisted state."""

    return DatasetSemanticMapping(
        id=model.id,
        dataset_id=model.dataset_id,
        created_by_user_id=model.created_by_user_id,
        version=model.version,
        time_column=model.time_column,
        unit_column=model.unit_column,
        treatment_column=model.treatment_column,
        outcome_column=model.outcome_column,
        spend_column=model.spend_column,
        covariate_columns=tuple(covariate.normalized_column_name for covariate in covariates),
        treatment_value=model.treatment_value,
        control_value=model.control_value,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyDatasetSemanticMappingRepository:
    """Persist and retrieve versioned semantic mappings."""

    def __init__(
        self,
        *,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def add(
        self,
        mapping: DatasetSemanticMapping,
    ) -> None:
        model = to_dataset_semantic_mapping_model(
            mapping,
        )

        self._session.add(model)

        try:
            await self._session.flush()

            self._session.add_all(list(to_dataset_mapping_covariate_models(mapping)))

            await self._session.flush()
        except IntegrityError as error:
            await self._session.rollback()

            raise DatasetPersistenceConflictError(
                "Dataset semantic mapping conflicts with existing records."
            ) from error

    async def get_latest_by_scope(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        dataset_id: UUID,
    ) -> DatasetSemanticMapping | None:
        statement = (
            select(DatasetSemanticMappingModel)
            .join(
                DatasetModel,
                DatasetModel.id == DatasetSemanticMappingModel.dataset_id,
            )
            .where(
                DatasetSemanticMappingModel.dataset_id == dataset_id,
                DatasetModel.workspace_id == workspace_id,
                DatasetModel.project_id == project_id,
            )
            .order_by(
                DatasetSemanticMappingModel.version.desc(),
            )
            .limit(1)
        )

        model = await self._session.scalar(
            statement,
        )

        if model is None:
            return None

        return await self._load_entity(
            model,
        )

    async def get_by_scope_and_version(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        dataset_id: UUID,
        version: int,
    ) -> DatasetSemanticMapping | None:
        statement = (
            select(DatasetSemanticMappingModel)
            .join(
                DatasetModel,
                DatasetModel.id == DatasetSemanticMappingModel.dataset_id,
            )
            .where(
                DatasetSemanticMappingModel.dataset_id == dataset_id,
                DatasetSemanticMappingModel.version == version,
                DatasetModel.workspace_id == workspace_id,
                DatasetModel.project_id == project_id,
            )
        )

        model = await self._session.scalar(
            statement,
        )

        if model is None:
            return None

        return await self._load_entity(
            model,
        )

    async def get_by_id_scope_and_version(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        dataset_id: UUID,
        mapping_id: UUID,
        version: int,
    ) -> DatasetSemanticMapping | None:
        model = await self._session.scalar(
            select(DatasetSemanticMappingModel)
            .join(DatasetModel, DatasetModel.id == DatasetSemanticMappingModel.dataset_id)
            .where(
                DatasetSemanticMappingModel.id == mapping_id,
                DatasetSemanticMappingModel.dataset_id == dataset_id,
                DatasetSemanticMappingModel.version == version,
                DatasetModel.workspace_id == workspace_id,
                DatasetModel.project_id == project_id,
            )
        )
        if model is None:
            return None
        return await self._load_entity(model)

    async def _load_entity(
        self,
        model: DatasetSemanticMappingModel,
    ) -> DatasetSemanticMapping:
        statement = (
            select(DatasetMappingCovariateModel)
            .where(
                DatasetMappingCovariateModel.mapping_id == model.id,
                DatasetMappingCovariateModel.dataset_id == model.dataset_id,
            )
            .order_by(
                DatasetMappingCovariateModel.ordinal_position,
            )
        )

        result = await self._session.scalars(
            statement,
        )

        covariates = tuple(result.all())

        return to_dataset_semantic_mapping(
            model=model,
            covariates=covariates,
        )
