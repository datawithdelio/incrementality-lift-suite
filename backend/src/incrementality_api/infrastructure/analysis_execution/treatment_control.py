from incrementality_api.application.analysis_execution.estimation import (
    PermanentEstimationError,
)
from incrementality_api.domain.analysis_runs.semantic_mapping_snapshot import (
    SemanticMappingSnapshot,
)
from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType
from incrementality_api.domain.analysis_runs.treatment_control_snapshot import (
    TreatmentControlSnapshot,
)
from incrementality_api.infrastructure.analysis_execution.selection import (
    AnalysisSelectionRowExecutor,
)


class TreatmentControlRowExecutor:
    """Apply and verify the immutable treatment/control assignment for a run."""

    def __init__(self, rule_executor: AnalysisSelectionRowExecutor | None = None) -> None:
        self._rule_executor = rule_executor or AnalysisSelectionRowExecutor()

    def filter(
        self,
        *,
        rows: tuple[dict[str, str], ...],
        mapping: SemanticMappingSnapshot,
        snapshot: TreatmentControlSnapshot,
    ) -> tuple[dict[str, str], ...]:
        if snapshot.estimator_type in {
            AnalysisEstimatorType.MARKETING_MIX_MODEL,
            AnalysisEstimatorType.OFF_POLICY_EVALUATION,
        }:
            return rows
        self._validate_mapping(mapping, snapshot)
        selected: list[dict[str, str]] = []
        seen_treated: set[str] = set()
        seen_control: set[str] = set()
        treated = set(snapshot.treated_units)
        controls = set(snapshot.control_units)
        excluded_treated = set(snapshot.excluded_treatment_units)
        excluded_control = set(snapshot.excluded_control_units)
        for row_number, row in enumerate(rows, start=2):
            unit = self._required_value(row, mapping.unit_column, row_number)
            assignment = self._required_value(row, mapping.treatment_column, row_number)
            is_treated = assignment.casefold() == mapping.treatment_value.casefold()
            is_control = assignment.casefold() == mapping.control_value.casefold()
            if not is_treated and not is_control:
                raise PermanentEstimationError(
                    f"CSV row {row_number} has an unknown treatment/control value."
                )
            if unit in excluded_treated and is_treated:
                continue
            if unit in excluded_control and is_control:
                continue
            if treated or controls:
                if unit not in treated and unit not in controls:
                    continue
                if (unit in treated and not is_treated) or (unit in controls and not is_control):
                    raise PermanentEstimationError(
                        f"Persisted treatment/control assignment for '{unit}' disagrees "
                        "with the dataset."
                    )
            cohort_rules = snapshot.treatment_cohort or ()
            if is_treated and not self._rule_executor.matches_rules(
                row=row, rules=cohort_rules
            ):
                continue
            if is_control and not self._rule_executor.matches_rules(
                row=row, rules=snapshot.control_eligibility_rules
            ):
                continue
            if is_treated:
                seen_treated.add(unit)
            else:
                seen_control.add(unit)
            selected.append(row)
        missing_treated = treated - seen_treated
        missing_control = controls - seen_control
        if missing_treated or missing_control:
            missing = sorted(missing_treated | missing_control)[0]
            raise PermanentEstimationError(
                f"Persisted treatment/control unit '{missing}' is unavailable."
            )
        return tuple(selected)

    @staticmethod
    def _validate_mapping(
        mapping: SemanticMappingSnapshot,
        snapshot: TreatmentControlSnapshot,
    ) -> None:
        if (
            snapshot.treatment_column != mapping.treatment_column
            or snapshot.treatment_value != mapping.treatment_value
            or snapshot.control_value != mapping.control_value
        ):
            raise PermanentEstimationError(
                "Treatment/control snapshot does not match the semantic mapping."
            )

    @staticmethod
    def _required_value(row: dict[str, str], column: str, row_number: int) -> str:
        raw = row.get(column)
        if raw is None or not raw.strip():
            raise PermanentEstimationError(
                f"CSV row {row_number} has a missing value for '{column}'."
            )
        return raw.strip()
