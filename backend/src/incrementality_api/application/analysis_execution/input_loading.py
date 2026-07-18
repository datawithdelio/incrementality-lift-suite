import csv
import io
import json
import math
from collections import defaultdict
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, time
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
from incrementality_api.domain.analysis_runs.analysis_period_snapshot import (
    AnalysisPeriodSnapshot,
)
from incrementality_api.domain.analysis_runs.analysis_selection_snapshot import (
    AnalysisSelectionSnapshot,
)
from incrementality_api.domain.analysis_runs.entities import AnalysisRun
from incrementality_api.domain.analysis_runs.errors import InvalidAnalysisRunError
from incrementality_api.domain.analysis_runs.estimand_snapshot import (
    EstimandSnapshot,
)
from incrementality_api.domain.analysis_runs.execution_jobs import AnalysisExecutionJob
from incrementality_api.domain.analysis_runs.semantic_mapping_snapshot import (
    SemanticMappingSnapshot,
)
from incrementality_api.domain.analysis_runs.status import (
    AnalysisEstimatorType,
    AnalysisRunStatus,
)
from incrementality_api.domain.analysis_runs.treatment_control_snapshot import (
    TreatmentControlSnapshot,
)
from incrementality_api.domain.datasets.columns import (
    DatasetColumnProfile,
    DatasetColumnType,
    normalize_dataset_column_names,
)
from incrementality_api.domain.datasets.entities import Dataset
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
    mapping: SemanticMappingSnapshot
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
        mapping: SemanticMappingSnapshot,
        run: AnalysisRun,
    ) -> object: ...


class AnalysisSelectionExecutor(Protocol):
    def filter(
        self,
        *,
        rows: tuple[dict[str, str], ...],
        snapshot: AnalysisSelectionSnapshot,
    ) -> tuple[dict[str, str], ...]: ...


class TreatmentControlExecutor(Protocol):
    def filter(
        self,
        *,
        rows: tuple[dict[str, str], ...],
        mapping: SemanticMappingSnapshot,
        snapshot: TreatmentControlSnapshot,
    ) -> tuple[dict[str, str], ...]: ...


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
        if run.semantic_mapping_snapshot is None or mapping != run.semantic_mapping_snapshot:
            raise PermanentEstimationError("Semantic mapping snapshot does not match the run.")
        period = run.analysis_period_snapshot
        if period is None or period.estimator_type is not run.estimator_type:
            raise PermanentEstimationError("Analysis-period snapshot does not match the run.")
        try:
            configured_period = AnalysisPeriodSnapshot.from_configuration_json(
                run.estimator_type, run.configuration_json
            )
        except InvalidAnalysisRunError as error:
            raise PermanentEstimationError("Analysis-period configuration is invalid.") from error
        if configured_period != period:
            raise PermanentEstimationError("Analysis-period snapshot does not match configuration.")
        selection = run.analysis_selection_snapshot
        if selection is None:
            raise PermanentEstimationError("Analysis-selection snapshot is unavailable.")
        try:
            configured_selection = AnalysisSelectionSnapshot.from_configuration_json(
                estimator_type=run.estimator_type,
                serialized=run.configuration_json,
                semantic_mapping=mapping,
            )
        except InvalidAnalysisRunError as error:
            raise PermanentEstimationError(
                "Analysis-selection configuration is invalid."
            ) from error
        if configured_selection != selection:
            raise PermanentEstimationError(
                "Analysis-selection snapshot does not match configuration."
            )
        treatment_control = run.treatment_control_snapshot
        if treatment_control is None:
            raise PermanentEstimationError("Treatment/control snapshot is unavailable.")
        try:
            configured_treatment_control = TreatmentControlSnapshot.from_configuration_json(
                estimator_type=run.estimator_type,
                serialized=run.configuration_json,
                semantic_mapping=mapping,
                analysis_period=period,
                analysis_selection=selection,
            )
        except InvalidAnalysisRunError as error:
            raise PermanentEstimationError(
                "Treatment/control configuration is invalid."
            ) from error
        if configured_treatment_control != treatment_control:
            raise PermanentEstimationError(
                "Treatment/control snapshot does not match configuration."
            )

        estimand = run.estimand_snapshot
        if estimand is None:
            raise PermanentEstimationError(
                "Estimand snapshot is unavailable."
            )

        try:
            configured_estimand = EstimandSnapshot.from_validated_run_configuration(
                estimator_type=run.estimator_type,
                semantic_mapping=mapping,
                analysis_period=period,
                analysis_selection=selection,
                treatment_control=treatment_control,
                serialized=run.configuration_json,
            )
        except (InvalidAnalysisRunError, ValueError) as error:
            raise PermanentEstimationError(
                "Estimand configuration is invalid."
            ) from error

        if configured_estimand != estimand:
            raise PermanentEstimationError(
                "Estimand snapshot does not match configuration."
            )

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
        return DifferenceInDifferencesConfiguration(intervention_time=_intervention_time(run))


class AnalysisPeriodRowFilter:
    """Restrict estimator rows to the immutable calendar window."""

    def filter(
        self,
        *,
        rows: tuple[dict[str, str], ...],
        time_column: str,
        snapshot: AnalysisPeriodSnapshot | None,
    ) -> tuple[dict[str, str], ...]:
        if snapshot is None:
            raise PermanentEstimationError("Analysis-period snapshot is unavailable.")
        selected: list[dict[str, str]] = []
        for row_number, row in enumerate(rows, start=2):
            raw_value = row.get(time_column)
            if raw_value is None or not raw_value.strip():
                raise PermanentEstimationError(
                    f"CSV row {row_number} has a missing value for '{time_column}'."
                )
            try:
                observed_date = datetime.fromisoformat(
                    raw_value.strip().replace("Z", "+00:00")
                ).date()
            except ValueError as error:
                raise PermanentEstimationError(
                    f"CSV row {row_number} has an invalid analysis date."
                ) from error
            if snapshot.contains(observed_date):
                selected.append(row)
        if not selected:
            raise PermanentEstimationError("No dataset rows fall inside the analysis period.")
        return tuple(selected)


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
        mapping: SemanticMappingSnapshot,
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
    snapshot = run.analysis_period_snapshot
    if snapshot is None or snapshot.intervention_date is None:
        raise PermanentEstimationError("Analysis requires a persisted intervention date.")
    return datetime.combine(snapshot.intervention_date, time.min, tzinfo=UTC)


class PanelObservationBuilder:
    """Construct library-independent panel observations from semantic roles."""

    def build(
        self,
        *,
        rows: tuple[Mapping[str, str], ...],
        mapping: SemanticMappingSnapshot,
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
        mapping: SemanticMappingSnapshot,
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
        mapping: SemanticMappingSnapshot,
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
        mapping: SemanticMappingSnapshot,
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
        mapping: SemanticMappingSnapshot,
        run: AnalysisRun,
    ) -> OffPolicyEvaluationInput:
        del mapping
        configuration = _configuration(run)
        assignment = run.treatment_control_snapshot
        if (
            assignment is None
            or assignment.estimator_type is not AnalysisEstimatorType.OFF_POLICY_EVALUATION
            or assignment.policy_name is None
            or assignment.behavior_propensity_column is None
            or assignment.target_propensity_column is None
        ):
            raise PermanentEstimationError(
                "Off-policy treatment/control snapshot is unavailable."
            )
        policy_name = assignment.policy_name
        primary_method = configuration.get("primary_method", "doubly_robust")
        columns = {
            "reward_column": configuration.get("reward_column"),
            "behavior_propensity_column": assignment.behavior_propensity_column,
            "target_propensity_column": assignment.target_propensity_column,
            "expected_reward_column": configuration.get("expected_reward_column"),
        }
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
            policy_name=policy_name,
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
        period_filter: AnalysisPeriodRowFilter,
        selection_executor: AnalysisSelectionExecutor,
        treatment_control_executor: TreatmentControlExecutor,
        additional_builders: Mapping[AnalysisEstimatorType, AdditionalEstimatorInputBuilder]
        | None = None,
    ) -> None:
        self._metadata_reader = metadata_reader
        self._object_storage = object_storage
        self._metadata_validator = metadata_validator
        self._row_loader = row_loader
        self._configuration_parser = configuration_parser
        self._input_builder = input_builder
        self._period_filter = period_filter
        self._selection_executor = selection_executor
        self._treatment_control_executor = treatment_control_executor
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
        rows = self._period_filter.filter(
            rows=rows,
            time_column=metadata.mapping.time_column,
            snapshot=metadata.run.analysis_period_snapshot,
        )
        selection_snapshot = metadata.run.analysis_selection_snapshot
        if selection_snapshot is None:
            raise PermanentEstimationError("Analysis-selection snapshot is unavailable.")
        rows = self._selection_executor.filter(rows=rows, snapshot=selection_snapshot)
        if not rows:
            raise PermanentEstimationError("No dataset rows match the analysis selection.")
        treatment_control_snapshot = metadata.run.treatment_control_snapshot
        if treatment_control_snapshot is None:
            raise PermanentEstimationError("Treatment/control snapshot is unavailable.")
        rows = self._treatment_control_executor.filter(
            rows=rows,
            mapping=metadata.mapping,
            snapshot=treatment_control_snapshot,
        )
        if not rows:
            raise PermanentEstimationError(
                "No dataset rows match the treatment/control assignment."
            )

        if metadata.run.estimator_type is not AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES:
            builder = self._additional_builders.get(metadata.run.estimator_type)
            if builder is None:
                raise PermanentEstimationError(
                    f"No input builder supports '{metadata.run.estimator_type.value}'."
                )
            return AnalysisEstimatorInput(
                estimator_type=metadata.run.estimator_type,
                random_seed=random_seed,
                statistical_library_versions=(
                    metadata.run.statistical_library_versions
                ),
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
            statistical_library_versions=(
                metadata.run.statistical_library_versions
            ),
            payload=self._input_builder.build(
                rows=rows,
                mapping=metadata.mapping,
                configuration=configuration,
            ),
        )
