import csv
import io
import json
import math
from collections import defaultdict
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from incrementality_api.application.analysis_execution.estimation import (
    AnalysisEstimatorInput,
    DifferenceInDifferencesInput,
    DifferenceInDifferencesObservation,
    EstimationError,
    GeoCoordinate,
    GeoHoldoutInput,
    MarketingMixInput,
    MarketingMixObservation,
    OffPolicyEvaluationInput,
    PanelObservation,
    PermanentEstimationError,
    PolicyEvaluationObservation,
    RetryableEstimationError,
    SyntheticControlInput,
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


class AdditionalEstimatorInputBuilder(Protocol):
    def build(
        self,
        *,
        rows: tuple[Mapping[str, str], ...],
        mapping: DatasetSemanticMapping,
        run: AnalysisRun,
    ) -> object: ...


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
            observed_at = self._parse_time(values[mapping.time_column])
            post_period = self._is_post_period(observed_at, configuration.intervention_time)
            observations.append(
                DifferenceInDifferencesObservation(
                    unit=values[mapping.unit_column],
                    outcome=outcome,
                    treated=treated,
                    post_period=post_period,
                    observed_at=observed_at,
                )
            )
        return DifferenceInDifferencesInput(observations=tuple(observations))

    @staticmethod
    def _parse_time(value: str) -> datetime:
        try:
            observed_at = datetime.fromisoformat(value)
        except ValueError as error:
            raise PermanentEstimationError("Time values must be ISO-8601.") from error
        return observed_at

    @staticmethod
    def _is_post_period(observed_at: datetime, intervention_time: datetime) -> bool:
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            if observed_at.time() != datetime.min.time():
                raise PermanentEstimationError("Datetime values must be timezone-aware.")
            return observed_at.date() >= intervention_time.date()
        return observed_at >= intervention_time


def _configuration(run: AnalysisRun) -> dict[str, object]:
    try:
        parsed = json.loads(run.configuration_json)
    except json.JSONDecodeError as error:
        raise PermanentEstimationError("Analysis configuration is invalid JSON.") from error
    if not isinstance(parsed, dict):
        raise PermanentEstimationError("Analysis configuration must be an object.")
    return parsed


def _intervention_time(run: AnalysisRun) -> datetime:
    value = _configuration(run).get("intervention_time")
    if not isinstance(value, str):
        raise PermanentEstimationError("Analysis requires intervention_time.")
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError as error:
        raise PermanentEstimationError("intervention_time must be ISO-8601.") from error
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise PermanentEstimationError("intervention_time must be timezone-aware.")
    return timestamp


class PanelObservationBuilder:
    """Construct library-independent panel observations from semantic roles."""

    def build(
        self,
        *,
        rows: tuple[Mapping[str, str], ...],
        mapping: DatasetSemanticMapping,
        intervention_time: datetime,
    ) -> tuple[PanelObservation, ...]:
        observations: list[PanelObservation] = []
        required = (
            mapping.time_column,
            mapping.unit_column,
            mapping.treatment_column,
            mapping.outcome_column,
        )
        for row_number, row in enumerate(rows, start=2):
            values = {name: str(row.get(name, "")).strip() for name in required}
            missing = next((name for name, value in values.items() if not value), None)
            if missing is not None:
                raise PermanentEstimationError(
                    f"CSV row {row_number} has a missing value for '{missing}'."
                )
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
                observed_at = datetime.fromisoformat(values[mapping.time_column])
                outcome = float(values[mapping.outcome_column])
            except ValueError as error:
                raise PermanentEstimationError(
                    f"CSV row {row_number} has invalid time or outcome data."
                ) from error
            if not math.isfinite(outcome):
                raise PermanentEstimationError("Panel outcomes must be finite.")
            post_period = DifferenceInDifferencesInputBuilder._is_post_period(
                observed_at, intervention_time
            )
            observations.append(
                PanelObservation(
                    unit=values[mapping.unit_column],
                    observed_at=observed_at,
                    outcome=outcome,
                    treated=treated,
                    post_period=post_period,
                )
            )
        return tuple(observations)


class SyntheticControlInputBuilder:
    def __init__(self, panel_builder: PanelObservationBuilder | None = None) -> None:
        self._panel_builder = panel_builder or PanelObservationBuilder()

    def build(
        self,
        *,
        rows: tuple[Mapping[str, str], ...],
        mapping: DatasetSemanticMapping,
        run: AnalysisRun,
    ) -> SyntheticControlInput:
        return SyntheticControlInput(
            self._panel_builder.build(
                rows=rows,
                mapping=mapping,
                intervention_time=_intervention_time(run),
            )
        )


class GeoHoldoutInputBuilder:
    def __init__(self, panel_builder: PanelObservationBuilder | None = None) -> None:
        self._panel_builder = panel_builder or PanelObservationBuilder()

    def build(
        self,
        *,
        rows: tuple[Mapping[str, str], ...],
        mapping: DatasetSemanticMapping,
        run: AnalysisRun,
    ) -> GeoHoldoutInput:
        configuration = _configuration(run)
        coordinates_value = configuration.get("geo_coordinates")
        if not isinstance(coordinates_value, dict):
            raise PermanentEstimationError("Geo holdout requires geo_coordinates.")
        coordinates: dict[str, GeoCoordinate] = {}
        for unit, coordinate_value in coordinates_value.items():
            if not isinstance(unit, str) or not isinstance(coordinate_value, dict):
                raise PermanentEstimationError("Geo coordinates are invalid.")
            latitude = coordinate_value.get("latitude")
            longitude = coordinate_value.get("longitude")
            if not isinstance(latitude, int | float) or not isinstance(longitude, int | float):
                raise PermanentEstimationError("Geo coordinates must be numeric.")
            if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
                raise PermanentEstimationError("Geo coordinates are outside valid bounds.")
            coordinates[unit] = GeoCoordinate(float(latitude), float(longitude))
        spillover_value = configuration.get("spillover_pairs", [])
        if not isinstance(spillover_value, list):
            raise PermanentEstimationError("spillover_pairs must be a list.")
        spillovers: list[tuple[str, str]] = []
        for pair in spillover_value:
            if (
                not isinstance(pair, list)
                or len(pair) != 2
                or not all(isinstance(item, str) for item in pair)
            ):
                raise PermanentEstimationError("Each spillover pair requires two geographies.")
            spillovers.append((pair[0], pair[1]))
        outcome_kind = configuration.get("outcome_kind", "outcome")
        if outcome_kind not in {"outcome", "revenue", "conversions"}:
            raise PermanentEstimationError("Geo outcome_kind is unsupported.")
        return GeoHoldoutInput(
            observations=self._panel_builder.build(
                rows=rows,
                mapping=mapping,
                intervention_time=_intervention_time(run),
            ),
            coordinates=coordinates,
            outcome_kind=str(outcome_kind),
            spillover_pairs=tuple(spillovers),
        )


class MarketingMixInputBuilder:
    """Aggregate mapped channel series before any PyMC-specific work."""

    def build(
        self,
        *,
        rows: tuple[Mapping[str, str], ...],
        mapping: DatasetSemanticMapping,
        run: AnalysisRun,
    ) -> MarketingMixInput:
        if mapping.spend_column is None:
            raise PermanentEstimationError("MMM requires a mapped spend column.")
        channels = (mapping.spend_column, *mapping.covariate_columns)
        grouped_outcomes: defaultdict[datetime, float] = defaultdict(float)
        grouped_spend: defaultdict[datetime, dict[str, float]] = defaultdict(
            lambda: {channel: 0.0 for channel in channels}
        )
        for row_number, row in enumerate(rows, start=2):
            try:
                observed_at = datetime.fromisoformat(str(row[mapping.time_column]).strip())
                outcome = float(str(row[mapping.outcome_column]).strip())
                spend = {channel: float(str(row[channel]).strip()) for channel in channels}
            except (KeyError, ValueError) as error:
                raise PermanentEstimationError(
                    f"CSV row {row_number} has invalid MMM values."
                ) from error
            grouped_outcomes[observed_at] += outcome
            for channel, value in spend.items():
                grouped_spend[observed_at][channel] += value
        configuration = _configuration(run)
        adstock = configuration.get("adstock_decay", {})
        saturation = configuration.get("saturation_half_spend", {})
        seasonality_period = configuration.get("seasonality_period", 52)
        outcome_kind = configuration.get("outcome_kind", "revenue")
        if not isinstance(adstock, dict) or not isinstance(saturation, dict):
            raise PermanentEstimationError("MMM channel configuration must be an object.")
        if not isinstance(seasonality_period, int):
            raise PermanentEstimationError("MMM seasonality_period must be an integer.")
        if outcome_kind not in {"revenue", "conversions", "outcome"}:
            raise PermanentEstimationError("MMM outcome_kind is unsupported.")
        return MarketingMixInput(
            observations=tuple(
                MarketingMixObservation(period, grouped_outcomes[period], grouped_spend[period])
                for period in sorted(grouped_outcomes)
            ),
            adstock_decay={str(key): float(value) for key, value in adstock.items()},
            saturation_half_spend={str(key): float(value) for key, value in saturation.items()},
            seasonality_period=seasonality_period,
            outcome_kind=str(outcome_kind),
        )


class OffPolicyEvaluationInputBuilder:
    """Build logged-policy observations without coupling policy rules to statistics."""

    def build(
        self,
        *,
        rows: tuple[Mapping[str, str], ...],
        mapping: DatasetSemanticMapping,
        run: AnalysisRun,
    ) -> OffPolicyEvaluationInput:
        del mapping
        configuration = _configuration(run)
        policy_name = configuration.get("policy_name")
        primary_method = configuration.get("primary_method", "doubly_robust")
        columns = {
            key: configuration.get(key)
            for key in (
                "reward_column",
                "behavior_propensity_column",
                "target_propensity_column",
                "expected_reward_column",
            )
        }
        if not isinstance(policy_name, str) or not policy_name.strip():
            raise PermanentEstimationError("Off-policy evaluation requires policy_name.")
        if not isinstance(primary_method, str) or not all(
            isinstance(column, str) and column for column in columns.values()
        ):
            raise PermanentEstimationError("Off-policy policy columns are incomplete.")
        observations: list[PolicyEvaluationObservation] = []
        for row_number, row in enumerate(rows, start=2):
            try:
                observations.append(
                    PolicyEvaluationObservation(
                        reward=float(row[str(columns["reward_column"])]),
                        behavior_probability=float(row[str(columns["behavior_propensity_column"])]),
                        target_probability=float(row[str(columns["target_propensity_column"])]),
                        expected_reward=float(row[str(columns["expected_reward_column"])]),
                    )
                )
            except (KeyError, ValueError) as error:
                raise PermanentEstimationError(
                    f"CSV row {row_number} has invalid off-policy values."
                ) from error
        if not observations:
            raise PermanentEstimationError("Off-policy evaluation requires observations.")
        return OffPolicyEvaluationInput(
            observations=tuple(observations),
            policy_name=policy_name.strip(),
            primary_method=primary_method,
        )


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
        additional_builders: Mapping[AnalysisEstimatorType, AdditionalEstimatorInputBuilder]
        | None = None,
    ) -> None:
        self._metadata_reader = metadata_reader
        self._object_storage = object_storage
        self._metadata_validator = metadata_validator
        self._row_loader = row_loader
        self._configuration_parser = configuration_parser
        self._input_builder = input_builder
        self._additional_builders = dict(additional_builders or {})

    async def load(self, job: AnalysisExecutionJob) -> AnalysisEstimatorInput:
        metadata = await self._metadata_reader.load(job)
        self._metadata_validator.validate(job=job, metadata=metadata)
        try:
            rows = await self._row_loader.load(
                self._object_storage.read_chunks(metadata.dataset.storage_key)
            )
        except EstimationError:
            raise
        except Exception as error:
            raise RetryableEstimationError("Dataset object storage is unavailable.") from error
        random_seed = metadata.run.random_seed
        if random_seed is None:
            raise PermanentEstimationError("Analysis run random seed is unavailable.")

        if metadata.run.estimator_type is not AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES:
            builder = self._additional_builders.get(metadata.run.estimator_type)
            if builder is None:
                raise PermanentEstimationError(
                    f"No input builder supports '{metadata.run.estimator_type.value}'."
                )
            return AnalysisEstimatorInput(
                estimator_type=metadata.run.estimator_type,
                random_seed=random_seed,
                payload=builder.build(
                    rows=rows,
                    mapping=metadata.mapping,
                    run=metadata.run,
                ),
            )
        configuration = self._configuration_parser.parse(metadata.run)
        return AnalysisEstimatorInput(
            estimator_type=metadata.run.estimator_type,
            random_seed=random_seed,
            payload=self._input_builder.build(
                rows=rows,
                mapping=metadata.mapping,
                configuration=configuration,
            ),
        )
