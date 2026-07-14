import csv
import io
import json
import math
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from incrementality_api.application.analysis_execution.estimation import (
    AnalysisEstimatorInput,
    DifferenceInDifferencesInput,
    DifferenceInDifferencesObservation,
    EstimationError,
    PermanentEstimationError,
    RetryableEstimationError,
)
from incrementality_api.domain.analysis_runs.entities import AnalysisRun
from incrementality_api.domain.analysis_runs.execution_jobs import AnalysisExecutionJob
from incrementality_api.domain.analysis_runs.status import (
    AnalysisEstimatorType,
    AnalysisRunStatus,
)
from incrementality_api.domain.datasets.columns import (
    DatasetColumnProfile,
    DatasetColumnType,
    normalize_dataset_column_names,
)
from incrementality_api.domain.datasets.entities import Dataset
from incrementality_api.domain.datasets.semantic_mapping import DatasetSemanticMapping
from incrementality_api.domain.datasets.status import DatasetStatus

_NUMERIC_TYPES = {DatasetColumnType.INTEGER, DatasetColumnType.FLOAT}
_TIME_TYPES = {DatasetColumnType.DATE, DatasetColumnType.DATETIME}
_UNIT_TYPES = {DatasetColumnType.INTEGER, DatasetColumnType.STRING}
_TREATMENT_TYPES = {
    DatasetColumnType.BOOLEAN,
    DatasetColumnType.INTEGER,
    DatasetColumnType.STRING,
}


@dataclass(frozen=True, slots=True)
class AnalysisInputMetadata:
    run: AnalysisRun
    dataset: Dataset
    mapping: DatasetSemanticMapping
    columns: tuple[DatasetColumnProfile, ...]


@dataclass(frozen=True, slots=True)
class DifferenceInDifferencesConfiguration:
    intervention_time: datetime


class AnalysisInputMetadataReader(Protocol):
    async def load(self, job: AnalysisExecutionJob) -> AnalysisInputMetadata:
        """Load the exact tenant-scoped metadata snapshot for a job."""


class AnalysisDatasetObjectReader(Protocol):
    def read_chunks(self, storage_key: str) -> AsyncIterator[bytes]:
        """Stream one dataset object by its internal storage key."""


class AnalysisInputMetadataValidator:
    """Validate ownership and semantic types before object retrieval."""

    def validate(
        self,
        *,
        job: AnalysisExecutionJob,
        metadata: AnalysisInputMetadata,
    ) -> None:
        run = metadata.run
        dataset = metadata.dataset
        mapping = metadata.mapping
        expected_scope = (job.workspace_id, job.project_id)
        if (run.workspace_id, run.project_id) != expected_scope or (
            dataset.workspace_id,
            dataset.project_id,
        ) != expected_scope:
            raise PermanentEstimationError("Analysis input is outside the job tenant scope.")
        if run.id != job.analysis_run_id or run.status is not AnalysisRunStatus.RUNNING:
            raise PermanentEstimationError("Analysis run is not the claimed running job.")
        if dataset.id != run.dataset_id or dataset.status is not DatasetStatus.READY:
            raise PermanentEstimationError("Analysis dataset is unavailable or not ready.")
        if (
            mapping.id != run.semantic_mapping_id
            or mapping.dataset_id != dataset.id
            or mapping.version != run.semantic_mapping_version
        ):
            raise PermanentEstimationError("Semantic mapping snapshot does not match the run.")

        columns = {column.normalized_name: column for column in metadata.columns}
        required = {
            mapping.time_column: _TIME_TYPES,
            mapping.unit_column: _UNIT_TYPES,
            mapping.treatment_column: _TREATMENT_TYPES,
            mapping.outcome_column: _NUMERIC_TYPES,
        }
        for name, allowed_types in required.items():
            profile = columns.get(name)
            if profile is None:
                raise PermanentEstimationError(f"Required mapped column '{name}' is unavailable.")
            if profile.inferred_type not in allowed_types:
                raise PermanentEstimationError(f"Mapped column '{name}' has an invalid type.")
            if profile.nullable or profile.missing_count > 0:
                raise PermanentEstimationError(
                    f"Required mapped column '{name}' must not contain missing values."
                )


class DifferenceInDifferencesConfigurationParser:
    """Parse the reproducible DiD configuration captured by the run."""

    def parse(self, run: AnalysisRun) -> DifferenceInDifferencesConfiguration:
        if run.estimator_type is not AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES:
            raise PermanentEstimationError("Analysis run is not a DiD estimator run.")
        try:
            configuration = json.loads(run.configuration_json)
        except json.JSONDecodeError as error:
            raise PermanentEstimationError("Analysis configuration is invalid JSON.") from error
        intervention_value = configuration.get("intervention_time")
        if not isinstance(intervention_value, str) or not intervention_value.strip():
            raise PermanentEstimationError(
                "DiD configuration requires a timezone-aware intervention_time."
            )
        try:
            intervention_time = datetime.fromisoformat(intervention_value.strip())
        except ValueError as error:
            raise PermanentEstimationError("intervention_time must be ISO-8601.") from error
        if intervention_time.tzinfo is None or intervention_time.utcoffset() is None:
            raise PermanentEstimationError("intervention_time must be timezone-aware.")
        return DifferenceInDifferencesConfiguration(intervention_time=intervention_time)


class CsvAnalysisRowLoader:
    """Decode CSV bytes into normalized, library-independent row mappings."""

    async def load(self, chunks: AsyncIterator[bytes]) -> tuple[dict[str, str], ...]:
        content = bytearray()
        async for chunk in chunks:
            content.extend(chunk)
        try:
            text = bytes(content).decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise PermanentEstimationError("Dataset must be UTF-8 CSV.") from error
        reader = csv.reader(io.StringIO(text, newline=""))
        try:
            source_headers = next(reader)
        except StopIteration as error:
            raise PermanentEstimationError("Dataset CSV is empty.") from error
        normalized_headers = normalize_dataset_column_names(tuple(source_headers))
        rows: list[dict[str, str]] = []
        for line_number, values in enumerate(reader, start=2):
            if not values or all(not value.strip() for value in values):
                continue
            if len(values) != len(normalized_headers):
                raise PermanentEstimationError(
                    f"Dataset CSV row {line_number} has an invalid column count."
                )
            rows.append(dict(zip(normalized_headers, values, strict=True)))
        if not rows:
            raise PermanentEstimationError("Dataset CSV contains no data rows.")
        return tuple(rows)


class DifferenceInDifferencesInputBuilder:
    """Construct treated/post observations without statistical-library coupling."""

    def build(
        self,
        *,
        rows: tuple[Mapping[str, str], ...],
        mapping: DatasetSemanticMapping,
        configuration: DifferenceInDifferencesConfiguration,
    ) -> DifferenceInDifferencesInput:
        observations: list[DifferenceInDifferencesObservation] = []
        required = (
            mapping.time_column,
            mapping.unit_column,
            mapping.treatment_column,
            mapping.outcome_column,
        )
        for row_number, row in enumerate(rows, start=2):
            values: dict[str, str] = {}
            for column in required:
                value = row.get(column)
                if value is None:
                    raise PermanentEstimationError(f"Required CSV column '{column}' is missing.")
                normalized = value.strip()
                if not normalized:
                    raise PermanentEstimationError(
                        f"CSV row {row_number} has a missing value for '{column}'."
                    )
                values[column] = normalized

            treatment = values[mapping.treatment_column].casefold()
            if treatment == mapping.treatment_value.casefold():
                treated = True
            elif treatment == mapping.control_value.casefold():
                treated = False
            else:
                raise PermanentEstimationError(
                    f"CSV row {row_number} has an unknown treatment/control value."
                )
            try:
                outcome = float(values[mapping.outcome_column])
            except ValueError as error:
                raise PermanentEstimationError(
                    f"CSV row {row_number} has a non-numeric outcome."
                ) from error
            if not math.isfinite(outcome):
                raise PermanentEstimationError(f"CSV row {row_number} has a non-finite outcome.")
            post_period = self._is_post_period(
                values[mapping.time_column],
                configuration.intervention_time,
            )
            observations.append(
                DifferenceInDifferencesObservation(
                    unit=values[mapping.unit_column],
                    outcome=outcome,
                    treated=treated,
                    post_period=post_period,
                )
            )
        return DifferenceInDifferencesInput(observations=tuple(observations))

    @staticmethod
    def _is_post_period(value: str, intervention_time: datetime) -> bool:
        try:
            observed_at = datetime.fromisoformat(value)
        except ValueError as error:
            raise PermanentEstimationError("Time values must be ISO-8601.") from error
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            if "T" in value:
                raise PermanentEstimationError("Datetime values must be timezone-aware.")
            return observed_at.date() >= intervention_time.date()
        return observed_at >= intervention_time


class ProductionAnalysisInputLoader:
    """Coordinate metadata, object loading, validation, and input construction."""

    def __init__(
        self,
        *,
        metadata_reader: AnalysisInputMetadataReader,
        object_storage: AnalysisDatasetObjectReader,
        metadata_validator: AnalysisInputMetadataValidator,
        row_loader: CsvAnalysisRowLoader,
        configuration_parser: DifferenceInDifferencesConfigurationParser,
        input_builder: DifferenceInDifferencesInputBuilder,
    ) -> None:
        self._metadata_reader = metadata_reader
        self._object_storage = object_storage
        self._metadata_validator = metadata_validator
        self._row_loader = row_loader
        self._configuration_parser = configuration_parser
        self._input_builder = input_builder

    async def load(self, job: AnalysisExecutionJob) -> AnalysisEstimatorInput:
        metadata = await self._metadata_reader.load(job)
        self._metadata_validator.validate(job=job, metadata=metadata)
        configuration = self._configuration_parser.parse(metadata.run)
        try:
            rows = await self._row_loader.load(
                self._object_storage.read_chunks(metadata.dataset.storage_key)
            )
        except EstimationError:
            raise
        except Exception as error:
            raise RetryableEstimationError("Dataset object storage is unavailable.") from error
        return AnalysisEstimatorInput(
            estimator_type=metadata.run.estimator_type,
            payload=self._input_builder.build(
                rows=rows,
                mapping=metadata.mapping,
                configuration=configuration,
            ),
        )
