from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any, Self

from incrementality_api.domain.analysis_runs.analysis_period_snapshot import (
    AnalysisPeriodSnapshot,
)
from incrementality_api.domain.analysis_runs.analysis_selection_snapshot import (
    AnalysisSelectionSnapshot,
    SelectionRule,
)
from incrementality_api.domain.analysis_runs.errors import InvalidAnalysisRunError
from incrementality_api.domain.analysis_runs.semantic_mapping_snapshot import (
    SemanticMappingSnapshot,
)
from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType

_SERIALIZED_FIELDS = {
    "estimator_type",
    "assignment_rule",
    "treatment_column",
    "treatment_value",
    "control_value",
    "intervention_date",
    "treated_units",
    "control_units",
    "excluded_treatment_units",
    "excluded_control_units",
    "treatment_cohort",
    "control_eligibility_rules",
    "policy_name",
    "behavior_propensity_column",
    "target_propensity_column",
}
_COMMON_ASSIGNMENT_FIELDS = {
    "excluded_treatment_units",
    "excluded_control_units",
    "treatment_cohort",
    "control_eligibility_rules",
}
_SYNTHETIC_FIELDS = {"treated_unit", "donor_pool"}
_GEO_FIELDS = {"treated_geographies", "control_geographies"}
_OPE_FIELDS = {
    "policy_name",
    "behavior_propensity_column",
    "target_propensity_column",
}
_ASSIGNMENT_FIELDS = _COMMON_ASSIGNMENT_FIELDS | _SYNTHETIC_FIELDS | _GEO_FIELDS | _OPE_FIELDS


@dataclass(frozen=True, slots=True)
class TreatmentControlSnapshot:
    """Canonical treatment/control definition fixed when an analysis is queued."""

    estimator_type: AnalysisEstimatorType
    assignment_rule: str
    treatment_column: str | None
    treatment_value: str | None
    control_value: str | None
    intervention_date: str | None
    treated_units: tuple[str, ...]
    control_units: tuple[str, ...]
    excluded_treatment_units: tuple[str, ...]
    excluded_control_units: tuple[str, ...]
    treatment_cohort: tuple[SelectionRule, ...] | None
    control_eligibility_rules: tuple[SelectionRule, ...]
    policy_name: str | None
    behavior_propensity_column: str | None
    target_propensity_column: str | None

    @classmethod
    def from_configuration(
        cls,
        *,
        estimator_type: AnalysisEstimatorType,
        configuration: Mapping[str, object],
        semantic_mapping: SemanticMappingSnapshot,
        analysis_period: AnalysisPeriodSnapshot,
        analysis_selection: AnalysisSelectionSnapshot,
    ) -> Self:
        cls._reject_irrelevant_fields(estimator_type, configuration)
        if estimator_type is AnalysisEstimatorType.MARKETING_MIX_MODEL:
            return cls.not_applicable()
        if estimator_type is AnalysisEstimatorType.OFF_POLICY_EVALUATION:
            return cls._for_off_policy(configuration)

        intervention = analysis_period.intervention_date
        if intervention is None:
            raise InvalidAnalysisRunError("Treatment assignment requires an intervention date.")
        treated_units: tuple[str, ...] = ()
        control_units: tuple[str, ...] = ()
        assignment_rule = "mapped_binary_at_intervention"
        if estimator_type is AnalysisEstimatorType.SYNTHETIC_CONTROL:
            treated_units = (_required_string(configuration, "treated_unit"),)
            control_units = _string_collection(
                configuration.get("donor_pool"), "Synthetic Control donor pool", minimum=2
            )
            assignment_rule = "one_treated_unit_with_donor_pool"
        elif estimator_type is AnalysisEstimatorType.GEO_HOLDOUT:
            treated_units = _string_collection(
                configuration.get("treated_geographies"),
                "Geo Holdout treated geographies",
                minimum=1,
            )
            control_units = _string_collection(
                configuration.get("control_geographies"),
                "Geo Holdout control geographies",
                minimum=1,
            )
            assignment_rule = "explicit_geo_holdout"

        excluded_treatment = _optional_string_collection(
            configuration, "excluded_treatment_units"
        )
        excluded_control = _optional_string_collection(configuration, "excluded_control_units")
        cls._reject_unit_contradictions(
            treated_units,
            control_units,
            excluded_treatment,
            excluded_control,
        )
        cls._validate_selection_membership(
            treated_units,
            control_units,
            analysis_selection,
        )
        known_columns = _known_columns(semantic_mapping)
        treatment_cohort = _optional_rules(
            configuration, "treatment_cohort", known_columns=known_columns
        )
        control_rules = _optional_rules(
            configuration, "control_eligibility_rules", known_columns=known_columns
        ) or ()
        return cls(
            estimator_type=estimator_type,
            assignment_rule=assignment_rule,
            treatment_column=semantic_mapping.treatment_column,
            treatment_value=semantic_mapping.treatment_value,
            control_value=semantic_mapping.control_value,
            intervention_date=intervention.isoformat(),
            treated_units=treated_units,
            control_units=control_units,
            excluded_treatment_units=excluded_treatment,
            excluded_control_units=excluded_control,
            treatment_cohort=treatment_cohort,
            control_eligibility_rules=control_rules,
            policy_name=None,
            behavior_propensity_column=None,
            target_propensity_column=None,
        )

    @classmethod
    def from_configuration_json(
        cls,
        *,
        estimator_type: AnalysisEstimatorType,
        serialized: str,
        semantic_mapping: SemanticMappingSnapshot,
        analysis_period: AnalysisPeriodSnapshot,
        analysis_selection: AnalysisSelectionSnapshot,
    ) -> Self:
        if not serialized.strip():
            raise InvalidAnalysisRunError("Analysis configuration must not be blank.")
        try:
            configuration = json.loads(serialized)
        except json.JSONDecodeError as error:
            raise InvalidAnalysisRunError("Analysis configuration must be valid JSON.") from error
        if not isinstance(configuration, dict):
            raise InvalidAnalysisRunError("Analysis configuration must be a JSON object.")
        return cls.from_configuration(
            estimator_type=estimator_type,
            configuration=configuration,
            semantic_mapping=semantic_mapping,
            analysis_period=analysis_period,
            analysis_selection=analysis_selection,
        )

    @classmethod
    def not_applicable(cls) -> Self:
        return cls(
            estimator_type=AnalysisEstimatorType.MARKETING_MIX_MODEL,
            assignment_rule="not_applicable",
            treatment_column=None,
            treatment_value=None,
            control_value=None,
            intervention_date=None,
            treated_units=(),
            control_units=(),
            excluded_treatment_units=(),
            excluded_control_units=(),
            treatment_cohort=None,
            control_eligibility_rules=(),
            policy_name=None,
            behavior_propensity_column=None,
            target_propensity_column=None,
        )

    @classmethod
    def _for_off_policy(cls, configuration: Mapping[str, object]) -> Self:
        return cls(
            estimator_type=AnalysisEstimatorType.OFF_POLICY_EVALUATION,
            assignment_rule="logged_policy_propensity",
            treatment_column=None,
            treatment_value=None,
            control_value=None,
            intervention_date=None,
            treated_units=(),
            control_units=(),
            excluded_treatment_units=(),
            excluded_control_units=(),
            treatment_cohort=None,
            control_eligibility_rules=(),
            policy_name=_required_string(configuration, "policy_name"),
            behavior_propensity_column=_required_string(
                configuration, "behavior_propensity_column"
            ),
            target_propensity_column=_required_string(
                configuration, "target_propensity_column"
            ),
        )

    @classmethod
    def from_json(cls, serialized: str) -> Self:
        if not serialized.strip():
            raise InvalidAnalysisRunError("Treatment/control snapshot must not be blank.")
        try:
            parsed = json.loads(serialized)
        except json.JSONDecodeError as error:
            raise InvalidAnalysisRunError(
                "Treatment/control snapshot must be valid JSON."
            ) from error
        if not isinstance(parsed, dict) or set(parsed) != _SERIALIZED_FIELDS:
            raise InvalidAnalysisRunError("Treatment/control snapshot has invalid fields.")
        estimator_value = parsed["estimator_type"]
        if not isinstance(estimator_value, str):
            raise InvalidAnalysisRunError("Treatment/control estimator type is invalid.")
        try:
            estimator_type = AnalysisEstimatorType(estimator_value)
        except ValueError as error:
            raise InvalidAnalysisRunError("Treatment/control estimator type is invalid.") from error
        return cls._from_mapping(estimator_type, parsed)

    @classmethod
    def _from_mapping(
        cls, estimator_type: AnalysisEstimatorType, values: Mapping[str, object]
    ) -> Self:
        assignment_rule = _required_string(values, "assignment_rule")
        optional_strings = {
            field: _optional_string(values, field)
            for field in (
                "treatment_column",
                "treatment_value",
                "control_value",
                "intervention_date",
                "policy_name",
                "behavior_propensity_column",
                "target_propensity_column",
            )
        }
        treated = _string_collection(values["treated_units"], "Treated units")
        control = _string_collection(values["control_units"], "Control units")
        excluded_treated = _string_collection(
            values["excluded_treatment_units"], "Excluded treatment units"
        )
        excluded_control = _string_collection(
            values["excluded_control_units"], "Excluded control units"
        )
        cls._reject_unit_contradictions(treated, control, excluded_treated, excluded_control)
        cohort_raw = values["treatment_cohort"]
        cohort = None if cohort_raw is None else _rules(cohort_raw, "Treatment cohort")
        control_rules = _rules(values["control_eligibility_rules"], "Control eligibility rules")
        snapshot = cls(
            estimator_type=estimator_type,
            assignment_rule=assignment_rule,
            treatment_column=optional_strings["treatment_column"],
            treatment_value=optional_strings["treatment_value"],
            control_value=optional_strings["control_value"],
            intervention_date=optional_strings["intervention_date"],
            treated_units=treated,
            control_units=control,
            excluded_treatment_units=excluded_treated,
            excluded_control_units=excluded_control,
            treatment_cohort=cohort,
            control_eligibility_rules=control_rules,
            policy_name=optional_strings["policy_name"],
            behavior_propensity_column=optional_strings["behavior_propensity_column"],
            target_propensity_column=optional_strings["target_propensity_column"],
        )
        snapshot._validate_shape()
        return snapshot

    @property
    def canonical_json(self) -> str:
        return json.dumps(
            self.as_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "estimator_type": self.estimator_type.value,
            "assignment_rule": self.assignment_rule,
            "treatment_column": self.treatment_column,
            "treatment_value": self.treatment_value,
            "control_value": self.control_value,
            "intervention_date": self.intervention_date,
            "treated_units": list(self.treated_units),
            "control_units": list(self.control_units),
            "excluded_treatment_units": list(self.excluded_treatment_units),
            "excluded_control_units": list(self.excluded_control_units),
            "treatment_cohort": (
                None
                if self.treatment_cohort is None
                else [rule.as_dict() for rule in self.treatment_cohort]
            ),
            "control_eligibility_rules": [
                rule.as_dict() for rule in self.control_eligibility_rules
            ],
            "policy_name": self.policy_name,
            "behavior_propensity_column": self.behavior_propensity_column,
            "target_propensity_column": self.target_propensity_column,
        }

    def canonicalize_configuration(
        self, configuration: Mapping[str, object]
    ) -> dict[str, object]:
        canonical = {
            key: value for key, value in configuration.items() if key not in _ASSIGNMENT_FIELDS
        }
        if self.estimator_type is AnalysisEstimatorType.SYNTHETIC_CONTROL:
            canonical["treated_unit"] = self.treated_units[0]
            canonical["donor_pool"] = list(self.control_units)
        elif self.estimator_type is AnalysisEstimatorType.GEO_HOLDOUT:
            canonical["treated_geographies"] = list(self.treated_units)
            canonical["control_geographies"] = list(self.control_units)
        elif self.estimator_type is AnalysisEstimatorType.OFF_POLICY_EVALUATION:
            canonical.update(
                {
                    "policy_name": self.policy_name,
                    "behavior_propensity_column": self.behavior_propensity_column,
                    "target_propensity_column": self.target_propensity_column,
                }
            )
        if self.excluded_treatment_units:
            canonical["excluded_treatment_units"] = list(self.excluded_treatment_units)
        if self.excluded_control_units:
            canonical["excluded_control_units"] = list(self.excluded_control_units)
        if self.treatment_cohort is not None:
            canonical["treatment_cohort"] = [
                rule.as_dict() for rule in self.treatment_cohort
            ]
        if self.control_eligibility_rules:
            canonical["control_eligibility_rules"] = [
                rule.as_dict() for rule in self.control_eligibility_rules
            ]
        return canonical

    def validate_against(
        self,
        *,
        semantic_mapping: SemanticMappingSnapshot,
        analysis_period: AnalysisPeriodSnapshot,
        analysis_selection: AnalysisSelectionSnapshot,
    ) -> None:
        self._validate_shape()
        if self.estimator_type in {
            AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
            AnalysisEstimatorType.SYNTHETIC_CONTROL,
            AnalysisEstimatorType.GEO_HOLDOUT,
        }:
            if (
                self.treatment_column != semantic_mapping.treatment_column
                or self.treatment_value != semantic_mapping.treatment_value
                or self.control_value != semantic_mapping.control_value
            ):
                raise InvalidAnalysisRunError(
                    "Treatment/control snapshot does not match the semantic mapping."
                )
            expected_intervention = analysis_period.intervention_date
            if (
                expected_intervention is None
                or self.intervention_date != expected_intervention.isoformat()
            ):
                raise InvalidAnalysisRunError(
                    "Treatment/control snapshot does not match the analysis period."
                )
        self._validate_selection_membership(
            self.treated_units,
            self.control_units,
            analysis_selection,
        )

    @classmethod
    def _reject_irrelevant_fields(
        cls,
        estimator_type: AnalysisEstimatorType,
        configuration: Mapping[str, object],
    ) -> None:
        allowed: set[str]
        if estimator_type is AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES:
            allowed = _COMMON_ASSIGNMENT_FIELDS
        elif estimator_type is AnalysisEstimatorType.SYNTHETIC_CONTROL:
            allowed = _COMMON_ASSIGNMENT_FIELDS | _SYNTHETIC_FIELDS
        elif estimator_type is AnalysisEstimatorType.GEO_HOLDOUT:
            allowed = _COMMON_ASSIGNMENT_FIELDS | _GEO_FIELDS
        elif estimator_type is AnalysisEstimatorType.OFF_POLICY_EVALUATION:
            allowed = _OPE_FIELDS
        else:
            allowed = set()
        irrelevant = sorted(_ASSIGNMENT_FIELDS.intersection(configuration) - allowed)
        if irrelevant:
            raise InvalidAnalysisRunError(
                f"{estimator_type.value} does not use treatment/control field(s): "
                f"{', '.join(irrelevant)}."
            )

    @staticmethod
    def _reject_unit_contradictions(
        treated: Sequence[str],
        control: Sequence[str],
        excluded_treated: Sequence[str],
        excluded_control: Sequence[str],
    ) -> None:
        if set(treated) & set(control):
            raise InvalidAnalysisRunError("A unit cannot be both treated and control.")
        if set(treated) & set(excluded_treated):
            raise InvalidAnalysisRunError("A treated unit cannot also be excluded from treatment.")
        if set(control) & set(excluded_control):
            raise InvalidAnalysisRunError("A control unit cannot also be excluded from control.")

    @staticmethod
    def _validate_selection_membership(
        treated: Sequence[str],
        control: Sequence[str],
        selection: AnalysisSelectionSnapshot,
    ) -> None:
        assigned = set(treated) | set(control)
        selected = set(selection.selected_geographies)
        excluded = set(selection.excluded_geographies)
        if (selected and not assigned.issubset(selected)) or assigned & excluded:
            raise InvalidAnalysisRunError(
                "Treatment/control assignment contains a unit outside the analysis selection."
            )

    def _validate_shape(self) -> None:
        expected_rule = {
            AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES: "mapped_binary_at_intervention",
            AnalysisEstimatorType.SYNTHETIC_CONTROL: "one_treated_unit_with_donor_pool",
            AnalysisEstimatorType.GEO_HOLDOUT: "explicit_geo_holdout",
            AnalysisEstimatorType.MARKETING_MIX_MODEL: "not_applicable",
            AnalysisEstimatorType.OFF_POLICY_EVALUATION: "logged_policy_propensity",
        }[self.estimator_type]
        if self.assignment_rule != expected_rule:
            raise InvalidAnalysisRunError("Treatment/control assignment rule is contradictory.")
        if self.estimator_type is AnalysisEstimatorType.MARKETING_MIX_MODEL:
            if any(
                value
                for value in (
                    self.treatment_column,
                    self.treatment_value,
                    self.control_value,
                    self.intervention_date,
                    self.treated_units,
                    self.control_units,
                    self.excluded_treatment_units,
                    self.excluded_control_units,
                    self.treatment_cohort,
                    self.control_eligibility_rules,
                    self.policy_name,
                    self.behavior_propensity_column,
                    self.target_propensity_column,
                )
            ):
                raise InvalidAnalysisRunError(
                    "MMM not-applicable assignment must not contain treatment/control values."
                )
            return
        if self.estimator_type is AnalysisEstimatorType.OFF_POLICY_EVALUATION:
            if not all(
                (
                    self.policy_name,
                    self.behavior_propensity_column,
                    self.target_propensity_column,
                )
            ):
                raise InvalidAnalysisRunError(
                    "Off-policy assignment requires policy and propensity columns."
                )
            if any(
                value
                for value in (
                    self.treatment_column,
                    self.treatment_value,
                    self.control_value,
                    self.intervention_date,
                    self.treated_units,
                    self.control_units,
                    self.excluded_treatment_units,
                    self.excluded_control_units,
                    self.treatment_cohort,
                    self.control_eligibility_rules,
                )
            ):
                raise InvalidAnalysisRunError(
                    "Off-policy assignment contains contradictory treatment/control values."
                )
            return
        treatment_column = self.treatment_column
        treatment_value = self.treatment_value
        control_value = self.control_value
        intervention_date = self.intervention_date
        if (
            treatment_column is None
            or treatment_value is None
            or control_value is None
            or intervention_date is None
        ):
            raise InvalidAnalysisRunError(
                "Treatment assignment requires mapped values and intervention date."
            )
        if treatment_value.casefold() == control_value.casefold():
            raise InvalidAnalysisRunError("Treatment and control values must be distinct.")
        try:
            date.fromisoformat(intervention_date)
        except ValueError as error:
            raise InvalidAnalysisRunError(
                "Treatment/control intervention date must be an ISO date."
            ) from error
        if any(
            (self.policy_name, self.behavior_propensity_column, self.target_propensity_column)
        ):
            raise InvalidAnalysisRunError(
                "Treatment assignment contains contradictory policy values."
            )
        if self.estimator_type is AnalysisEstimatorType.SYNTHETIC_CONTROL and (
            len(self.treated_units) != 1 or len(self.control_units) < 2
        ):
            raise InvalidAnalysisRunError(
                "Synthetic Control requires one treated unit and at least two donor units."
            )
        if self.estimator_type is AnalysisEstimatorType.GEO_HOLDOUT and (
            not self.treated_units or not self.control_units
        ):
            raise InvalidAnalysisRunError(
                "Geo Holdout requires treated and control geographies."
            )


def _required_string(values: Mapping[str, object], field: str) -> str:
    value = values.get(field)
    if not isinstance(value, str) or not value.strip():
        raise InvalidAnalysisRunError(f"{field} must be a nonblank string.")
    return value.strip()


def _optional_string(values: Mapping[str, object], field: str) -> str | None:
    value = values.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise InvalidAnalysisRunError(f"{field} must be a nonblank string or null.")
    return value.strip()


def _string_collection(
    raw: object, label: str, *, minimum: int = 0
) -> tuple[str, ...]:
    if not isinstance(raw, list):
        raise InvalidAnalysisRunError(f"{label} must be a list.")
    normalized: list[str] = []
    for value in raw:
        if not isinstance(value, str) or not value.strip():
            raise InvalidAnalysisRunError(f"{label} must not contain blank identifiers.")
        normalized.append(value.strip())
    if len(normalized) != len(set(normalized)):
        raise InvalidAnalysisRunError(f"{label} contains a duplicate identifier.")
    if len(normalized) < minimum:
        raise InvalidAnalysisRunError(f"{label} requires at least {minimum} value(s).")
    return tuple(sorted(normalized))


def _optional_string_collection(
    configuration: Mapping[str, object], field: str
) -> tuple[str, ...]:
    raw = configuration.get(field)
    return () if raw is None else _string_collection(raw, field.replace("_", " ").title())


def _rules(raw: object, label: str) -> tuple[SelectionRule, ...]:
    if not isinstance(raw, list):
        raise InvalidAnalysisRunError(f"{label} must be a list.")
    rules = [SelectionRule.from_object(value) for value in raw]
    keys = [rule.canonical_json for rule in rules]
    if len(keys) != len(set(keys)):
        raise InvalidAnalysisRunError(f"{label} contains a duplicate rule.")
    return tuple(rule for _, rule in sorted(zip(keys, rules, strict=True)))


def _optional_rules(
    configuration: Mapping[str, object],
    field: str,
    *,
    known_columns: set[str],
) -> tuple[SelectionRule, ...] | None:
    raw = configuration.get(field)
    if raw is None:
        return None if field == "treatment_cohort" else ()
    rules = _rules(raw, field.replace("_", " ").title())
    unknown = sorted({rule.column for rule in rules} - known_columns)
    if unknown:
        raise InvalidAnalysisRunError(
            f"{field} references unknown column(s): {', '.join(unknown)}."
        )
    return rules


def _known_columns(mapping: SemanticMappingSnapshot) -> set[str]:
    columns = {
        mapping.time_column,
        mapping.unit_column,
        mapping.treatment_column,
        mapping.outcome_column,
        *mapping.covariate_columns,
    }
    if mapping.spend_column is not None:
        columns.add(mapping.spend_column)
    return columns
