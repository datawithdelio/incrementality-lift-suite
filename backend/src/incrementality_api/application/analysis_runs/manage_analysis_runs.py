from dataclasses import dataclass
from uuid import UUID

from incrementality_api.application.analysis_runs.errors import (
    AnalysisRunDatasetNotReadyError,
    AnalysisRunDatasetUnavailableError,
    AnalysisRunSemanticMappingUnavailableError,
    AnalysisRunUnavailableError,
)
from incrementality_api.application.analysis_runs.ports import (
    AnalysisRunClock,
    AnalysisRunUnitOfWork,
)
from incrementality_api.domain.analysis_runs.entities import (
    AnalysisRun,
)
from incrementality_api.domain.analysis_runs.status import (
    AnalysisEstimatorType,
)
from incrementality_api.domain.datasets.status import (
    DatasetStatus,
)


@dataclass(frozen=True, slots=True)
class QueueAnalysisRunCommand:
    workspace_id: UUID
    project_id: UUID
    dataset_id: UUID
    semantic_mapping_version: int
    created_by_user_id: UUID
    estimator_type: AnalysisEstimatorType
    estimator_version: str
    configuration_json: str


class QueueAnalysisRun:
    """Validate dependencies and queue a reproducible analysis run."""

    def __init__(
        self,
        *,
        unit_of_work: AnalysisRunUnitOfWork,
        clock: AnalysisRunClock,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock

    async def execute(
        self,
        command: QueueAnalysisRunCommand,
    ) -> AnalysisRun:
        async with self._unit_of_work:
            dataset = await self._unit_of_work.datasets.get_by_scope(
                workspace_id=command.workspace_id,
                project_id=command.project_id,
                dataset_id=command.dataset_id,
            )

            if dataset is None:
                raise AnalysisRunDatasetUnavailableError("Dataset is unavailable.")

            if dataset.status is not DatasetStatus.READY:
                raise AnalysisRunDatasetNotReadyError("Dataset must be ready before analysis.")

            mapping = await self._unit_of_work.semantic_mappings.get_by_scope_and_version(
                workspace_id=command.workspace_id,
                project_id=command.project_id,
                dataset_id=command.dataset_id,
                version=(command.semantic_mapping_version),
            )

            if mapping is None:
                raise (
                    AnalysisRunSemanticMappingUnavailableError("Semantic mapping is unavailable.")
                )

            run = AnalysisRun.queue(
                workspace_id=command.workspace_id,
                project_id=command.project_id,
                dataset_id=command.dataset_id,
                semantic_mapping_id=mapping.id,
                semantic_mapping_version=mapping.version,
                created_by_user_id=(command.created_by_user_id),
                estimator_type=command.estimator_type,
                estimator_version=(command.estimator_version),
                configuration_json=(command.configuration_json),
                created_at=self._clock.now(),
            )

            await self._unit_of_work.analysis_runs.add(run)

            await self._unit_of_work.commit()

            return run


@dataclass(frozen=True, slots=True)
class GetAnalysisRunQuery:
    workspace_id: UUID
    project_id: UUID
    analysis_run_id: UUID


class GetAnalysisRun:
    """Read one analysis run within complete tenant scope."""

    def __init__(
        self,
        *,
        unit_of_work: AnalysisRunUnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        query: GetAnalysisRunQuery,
    ) -> AnalysisRun:
        async with self._unit_of_work:
            run = await self._unit_of_work.analysis_runs.get_by_scope(
                workspace_id=query.workspace_id,
                project_id=query.project_id,
                analysis_run_id=(query.analysis_run_id),
            )

            if run is None:
                raise AnalysisRunUnavailableError("Analysis run is unavailable.")

            return run
