from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from incrementality_api.application.analysis_runs.errors import (
    AnalysisRunDataQualityBlockedError,
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
from incrementality_api.domain.analysis_runs.execution_jobs import (
    AnalysisExecutionJob,
)
from incrementality_api.domain.analysis_runs.statistical_library_versions import (
    StatisticalLibraryVersions,
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
    random_seed: int
    configuration_json: str


class StatisticalRuntimeVersions(Protocol):
    def for_estimator(
        self,
        estimator_type: AnalysisEstimatorType,
    ) -> StatisticalLibraryVersions: ...


class QueueAnalysisRun:
    """Validate dependencies and atomically queue an analysis."""

    def __init__(
        self,
        *,
        unit_of_work: AnalysisRunUnitOfWork,
        clock: AnalysisRunClock,
        application_version: str,
        source_revision: str,
        statistical_runtime_versions: StatisticalRuntimeVersions,
        quality_gate: "AnalysisQualityGate | None" = None,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock
        self._application_version = application_version
        self._source_revision = source_revision
        self._statistical_runtime_versions = statistical_runtime_versions
        self._quality_gate = quality_gate

    async def execute(
        self,
        command: QueueAnalysisRunCommand,
    ) -> AnalysisRun:
        if self._quality_gate is not None and not await self._quality_gate.allows(
            workspace_id=command.workspace_id,
            project_id=command.project_id,
            dataset_id=command.dataset_id,
            estimator_type=command.estimator_type.value,
        ):
            raise AnalysisRunDataQualityBlockedError(
                "Resolve blocking data-quality findings before running this method."
            )
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

            queued_at = self._clock.now()
            statistical_library_versions = (
                self._statistical_runtime_versions.for_estimator(
                    command.estimator_type
                )
            )

            run = AnalysisRun.queue(
                workspace_id=command.workspace_id,
                project_id=command.project_id,
                dataset_id=command.dataset_id,
                dataset_checksum_sha256=dataset.checksum_sha256,
                dataset_byte_size=dataset.byte_size,
                semantic_mapping_id=mapping.id,
                semantic_mapping_version=mapping.version,
                created_by_user_id=(command.created_by_user_id),
                estimator_type=command.estimator_type,
                estimator_version=(command.estimator_version),
                application_version=self._application_version,
                source_revision=self._source_revision,
                statistical_library_versions=(
                    statistical_library_versions.as_dict()
                ),
                random_seed=command.random_seed,
                configuration_json=(command.configuration_json),
                created_at=queued_at,
            )

            execution_job = AnalysisExecutionJob.enqueue(
                workspace_id=command.workspace_id,
                project_id=command.project_id,
                analysis_run_id=run.id,
                created_at=queued_at,
                available_at=queued_at,
                max_attempts=3,
            )

            await self._unit_of_work.analysis_runs.add(run)

            await self._unit_of_work.execution_jobs.add(execution_job)

            await self._unit_of_work.commit()

            return run


class AnalysisQualityGate(Protocol):
    async def allows(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        dataset_id: UUID,
        estimator_type: str,
    ) -> bool: ...


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
