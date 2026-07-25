from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from incrementality_api.application.analysis_execution.input_loading import CsvAnalysisRowLoader
from incrementality_api.application.data_products.explorer import (
    DatasetExplorer,
    DatasetExplorerQuery,
    DatasetExplorerResult,
    ExplorerSemanticMapping,
)
from incrementality_api.application.data_products.quality import (
    DataQualityAssessor,
    DataQualityInput,
    DataQualityResult,
)
from incrementality_api.application.datasets.errors import DatasetUnavailableError
from incrementality_api.application.datasets.ports import DatasetObjectStorage
from incrementality_api.domain.datasets.entities import Dataset
from incrementality_api.domain.datasets.semantic_mapping import DatasetSemanticMapping
from incrementality_api.domain.datasets.status import DatasetStatus


class ScopedDatasetReader(Protocol):
    async def get_by_scope_read(
        self, *, workspace_id: UUID, project_id: UUID, dataset_id: UUID
    ) -> Dataset | None: ...


class ScopedMappingReader(Protocol):
    async def get_by_scope_and_version(
        self, *, workspace_id: UUID, project_id: UUID, dataset_id: UUID, version: int
    ) -> DatasetSemanticMapping | None: ...

    async def get_latest_by_scope(
        self, *, workspace_id: UUID, project_id: UUID, dataset_id: UUID
    ) -> DatasetSemanticMapping | None: ...


class DatasetProductUnitOfWork(Protocol):
    datasets: ScopedDatasetReader
    semantic_mappings: ScopedMappingReader

    async def __aenter__(self) -> "DatasetProductUnitOfWork": ...
    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: object | None,
    ) -> None: ...


class QualityAssessmentWriter(Protocol):
    async def save(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        dataset_id: UUID,
        mapping_version: int | None,
        estimator_type: str,
        result: DataQualityResult,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class DatasetProductQuery:
    workspace_id: UUID
    project_id: UUID
    dataset_id: UUID
    mapping_version: int | None = None


class ProductionDataProducts:
    def __init__(
        self,
        *,
        unit_of_work: DatasetProductUnitOfWork,
        object_storage: DatasetObjectStorage,
        quality_writer: QualityAssessmentWriter,
        row_loader: CsvAnalysisRowLoader | None = None,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._storage = object_storage
        self._writer = quality_writer
        self._rows = row_loader or CsvAnalysisRowLoader()
        self._explorer = DatasetExplorer()
        self._quality = DataQualityAssessor()

    async def preview(
        self, scope: DatasetProductQuery, query: DatasetExplorerQuery
    ) -> DatasetExplorerResult:
        rows, mapping = await self._load(scope)
        return self._explorer.execute(
            rows,
            query,
            self._explorer_mapping(mapping),
        )

    async def export(self, scope: DatasetProductQuery, query: DatasetExplorerQuery) -> bytes:
        rows, _mapping = await self._load(scope)
        return self._explorer.export_csv(rows, query)

    async def assess_quality(
        self,
        scope: DatasetProductQuery,
        *,
        estimator_type: str,
        leakage_columns: tuple[str, ...] = (),
    ) -> DataQualityResult:
        rows, mapping = await self._load(scope)
        result = self._quality.assess(DataQualityInput(rows, estimator_type, leakage_columns))
        await self._writer.save(
            workspace_id=scope.workspace_id,
            project_id=scope.project_id,
            dataset_id=scope.dataset_id,
            mapping_version=None if mapping is None else mapping.version,
            estimator_type=estimator_type,
            result=result,
        )
        return result

    async def _load(
        self, scope: DatasetProductQuery
    ) -> tuple[tuple[dict[str, str], ...], DatasetSemanticMapping | None]:
        async with self._unit_of_work as unit:
            dataset = await unit.datasets.get_by_scope_read(
                workspace_id=scope.workspace_id,
                project_id=scope.project_id,
                dataset_id=scope.dataset_id,
            )
            if dataset is None or dataset.status is not DatasetStatus.READY:
                raise DatasetUnavailableError("Dataset is unavailable or not ready.")
            mapping = await (
                unit.semantic_mappings.get_by_scope_and_version(
                    workspace_id=scope.workspace_id,
                    project_id=scope.project_id,
                    dataset_id=scope.dataset_id,
                    version=scope.mapping_version,
                )
                if scope.mapping_version is not None
                else unit.semantic_mappings.get_latest_by_scope(
                    workspace_id=scope.workspace_id,
                    project_id=scope.project_id,
                    dataset_id=scope.dataset_id,
                )
            )
        loaded = await self._rows.load(self._storage.read(storage_key=dataset.storage_key))
        return tuple(dict(row) for row in loaded), mapping

    @staticmethod
    def _explorer_mapping(
        mapping: DatasetSemanticMapping | None,
    ) -> ExplorerSemanticMapping | None:
        if mapping is None:
            return None
        return ExplorerSemanticMapping(
            time_column=mapping.time_column,
            unit_column=mapping.unit_column,
            treatment_column=mapping.treatment_column,
            outcome_column=mapping.outcome_column,
            treatment_value=mapping.treatment_value,
            control_value=mapping.control_value,
        )
