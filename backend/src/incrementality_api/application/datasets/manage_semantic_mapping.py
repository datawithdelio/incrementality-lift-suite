from dataclasses import dataclass
from uuid import UUID

from incrementality_api.application.datasets.errors import (
    DatasetSemanticMappingUnavailableError,
    DatasetUnavailableError,
)
from incrementality_api.application.datasets.ports import (
    DatasetClock,
    DatasetSemanticMappingUnitOfWork,
)
from incrementality_api.domain.analysis_runs.status import (
    AnalysisEstimatorType,
)
from incrementality_api.domain.datasets.errors import (
    InvalidDatasetSemanticMappingError,
)
from incrementality_api.domain.datasets.semantic_mapping import (
    DatasetSemanticMapping,
)


@dataclass(frozen=True, slots=True)
class CreateDatasetSemanticMappingCommand:
    workspace_id: UUID
    project_id: UUID
    dataset_id: UUID
    created_by_user_id: UUID
    time_column: str
    unit_column: str
    treatment_column: str | None
    outcome_column: str
    spend_column: str | None
    covariate_columns: tuple[str, ...]
    treatment_value: str | None
    control_value: str | None
    estimator: AnalysisEstimatorType = AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES


class CreateDatasetSemanticMapping:
    """Create the next semantic-mapping version atomically."""

    def __init__(
        self,
        *,
        unit_of_work: DatasetSemanticMappingUnitOfWork,
        clock: DatasetClock,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock

    async def execute(
        self,
        command: CreateDatasetSemanticMappingCommand,
    ) -> DatasetSemanticMapping:
        treatment_fields = (
            command.treatment_column,
            command.treatment_value,
            command.control_value,
        )
        if (
            command.estimator is not AnalysisEstimatorType.MARKETING_MIX_MODEL
            and any(value is None for value in treatment_fields)
        ):
            raise InvalidDatasetSemanticMappingError(
                "Treatment column, treatment value, and control value are required "
                "for this estimator."
            )

        async with self._unit_of_work:
            dataset = await self._unit_of_work.datasets.get_by_scope(
                workspace_id=command.workspace_id,
                project_id=command.project_id,
                dataset_id=command.dataset_id,
            )

            if dataset is None:
                raise DatasetUnavailableError("Dataset is unavailable.")

            columns = await self._unit_of_work.columns.list_by_scope(
                workspace_id=command.workspace_id,
                project_id=command.project_id,
                dataset_id=command.dataset_id,
            )

            latest_mapping = await self._unit_of_work.semantic_mappings.get_latest_by_scope(
                workspace_id=command.workspace_id,
                project_id=command.project_id,
                dataset_id=command.dataset_id,
            )

            version = 1 if latest_mapping is None else latest_mapping.version + 1

            mapping = DatasetSemanticMapping.create(
                dataset=dataset,
                columns=columns,
                created_by_user_id=(command.created_by_user_id),
                version=version,
                time_column=command.time_column,
                unit_column=command.unit_column,
                treatment_column=(command.treatment_column),
                outcome_column=command.outcome_column,
                spend_column=command.spend_column,
                covariate_columns=(command.covariate_columns),
                treatment_value=(command.treatment_value),
                control_value=command.control_value,
                created_at=self._clock.now(),
            )

            await self._unit_of_work.semantic_mappings.add(mapping)

            await self._unit_of_work.commit()

            return mapping


@dataclass(frozen=True, slots=True)
class GetDatasetSemanticMappingQuery:
    workspace_id: UUID
    project_id: UUID
    dataset_id: UUID
    version: int | None = None


class GetDatasetSemanticMapping:
    """Read the latest or a specific mapping version."""

    def __init__(
        self,
        *,
        unit_of_work: DatasetSemanticMappingUnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        query: GetDatasetSemanticMappingQuery,
    ) -> DatasetSemanticMapping:
        async with self._unit_of_work:
            if query.version is None:
                mapping = await self._unit_of_work.semantic_mappings.get_latest_by_scope(
                    workspace_id=query.workspace_id,
                    project_id=query.project_id,
                    dataset_id=query.dataset_id,
                )
            else:
                mapping = await self._unit_of_work.semantic_mappings.get_by_scope_and_version(
                    workspace_id=query.workspace_id,
                    project_id=query.project_id,
                    dataset_id=query.dataset_id,
                    version=query.version,
                )

            if mapping is None:
                raise (DatasetSemanticMappingUnavailableError("Semantic mapping is unavailable."))

            return mapping
