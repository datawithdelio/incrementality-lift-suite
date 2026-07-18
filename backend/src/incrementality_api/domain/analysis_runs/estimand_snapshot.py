import json
from dataclasses import dataclass
from typing import Self

from incrementality_api.domain.analysis_runs.analysis_period_snapshot import (
    AnalysisPeriodSnapshot,
)
from incrementality_api.domain.analysis_runs.analysis_selection_snapshot import (
    AnalysisSelectionSnapshot,
)
from incrementality_api.domain.analysis_runs.errors import InvalidAnalysisRunError
from incrementality_api.domain.analysis_runs.semantic_mapping_snapshot import (
    SemanticMappingSnapshot,
)
from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType
from incrementality_api.domain.analysis_runs.treatment_control_snapshot import (
    TreatmentControlSnapshot,
)


@dataclass(frozen=True, slots=True)
class EstimandSnapshot:
    """Immutable description of the exact quantity estimated by an analysis run."""

    estimator_type: AnalysisEstimatorType
    estimand_type: str
    target_outcome: str
    target_population: str
    treated_population: str | None
    comparison: str
    effect_scale: str
    aggregation_method: str
    analysis_time_scope: str
    unit_of_analysis: str
    policy_target: str | None

    @classmethod
    def from_validated_run_configuration(
        cls,
        *,
        estimator_type: AnalysisEstimatorType,
        semantic_mapping: SemanticMappingSnapshot,
        analysis_period: AnalysisPeriodSnapshot,
        analysis_selection: AnalysisSelectionSnapshot,
        treatment_control: TreatmentControlSnapshot,
        serialized: str,
    ) -> "EstimandSnapshot":
        """Derive the estimand from immutable validated run configuration."""

        if estimator_type is AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES:
            return cls(
                estimator_type=estimator_type,
                estimand_type="average_differential_change",
                target_outcome=semantic_mapping.outcome_column,
                target_population="treated units in the post-treatment period",
                treated_population=semantic_mapping.treatment_value,
                comparison="control group counterfactual change",
                effect_scale="absolute_outcome_units",
                aggregation_method="difference_in_differences_interaction_coefficient",
                analysis_time_scope="post_treatment_period",
                unit_of_analysis="unit_period",
                policy_target=None,
            )

        if estimator_type is AnalysisEstimatorType.SYNTHETIC_CONTROL:
            return cls(
                estimator_type=estimator_type,
                estimand_type="average_post_treatment_gap",
                target_outcome=semantic_mapping.outcome_column,
                target_population="treated unit in the post-treatment period",
                treated_population=treatment_control.treated_units[0],
                comparison=(
                    "weighted synthetic counterfactual constructed from "
                    "the configured donor pool"
                ),
                effect_scale="absolute_outcome_units",
                aggregation_method=(
                    "mean_post_treatment_treated_minus_synthetic_gap"
                ),
                analysis_time_scope="post_treatment_period",
                unit_of_analysis="treated_unit_period",
                policy_target=None,
            )

        if estimator_type is AnalysisEstimatorType.GEO_HOLDOUT:
            return cls(
                estimator_type=estimator_type,
                estimand_type="average_incremental_geo_effect",
                target_outcome=semantic_mapping.outcome_column,
                target_population="treated geographies in the post-treatment period",
                treated_population=",".join(treatment_control.treated_units),
                comparison=(
                    "configured holdout geographies under the "
                    "parallel-trends counterfactual"
                ),
                effect_scale="absolute_outcome_units_per_geo_period",
                aggregation_method=(
                    "geo_difference_in_differences_interaction_coefficient"
                ),
                analysis_time_scope="post_treatment_period",
                unit_of_analysis="geography_period",
                policy_target=None,
            )

        if estimator_type is AnalysisEstimatorType.MARKETING_MIX_MODEL:
            return cls(
                estimator_type=estimator_type,
                estimand_type="average_modeled_media_contribution",
                target_outcome=semantic_mapping.outcome_column,
                target_population="observed analysis periods",
                treated_population=None,
                comparison=(
                    "modeled baseline excluding media-channel contributions"
                ),
                effect_scale="absolute_outcome_units_per_period",
                aggregation_method=(
                    "sum_modeled_channel_contributions_divided_by_analysis_periods"
                ),
                analysis_time_scope="analysis_period",
                unit_of_analysis="time_period",
                policy_target=None,
            )

        if estimator_type is AnalysisEstimatorType.OFF_POLICY_EVALUATION:
            import json

            configuration = json.loads(serialized)
            primary_method = configuration.get(
                "primary_method",
                "doubly_robust",
            )
            reward_column = configuration.get(
                "reward_column",
            )
            if (
                not isinstance(reward_column, str)
                or not reward_column.strip()
            ):
                raise ValueError(
                    "Off-policy evaluation requires a reward column."
                )
            reward_column = reward_column.strip()

            return cls(
                estimator_type=estimator_type,
                estimand_type="target_policy_value",
                target_outcome=reward_column,
                target_population="logged decision population",
                treated_population=None,
                comparison=(
                    "logged behavior policy distribution used for "
                    "off-policy correction"
                ),
                effect_scale="expected_reward_per_decision",
                aggregation_method=f"{primary_method}_mean_policy_value",
                analysis_time_scope="analysis_period",
                unit_of_analysis="logged_decision",
                policy_target=treatment_control.policy_name,
            )

        raise ValueError(
            f"Estimand derivation is not implemented for '{estimator_type.value}'."
        )

    @property
    def canonical_json(self) -> str:
        """Return the canonical deterministic JSON representation."""

        return json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )

    @classmethod
    def from_json(cls, serialized: str) -> Self:
        """Reconstruct an estimand snapshot from persisted canonical JSON."""

        if not serialized.strip():
            raise InvalidAnalysisRunError("Estimand snapshot must not be blank.")

        try:
            parsed = json.loads(serialized)
        except json.JSONDecodeError as error:
            raise InvalidAnalysisRunError(
                "Estimand snapshot must be valid JSON."
            ) from error

        if not isinstance(parsed, dict):
            raise InvalidAnalysisRunError(
                "Estimand snapshot must be a JSON object."
            )

        expected_fields = {
            "aggregation_method",
            "analysis_time_scope",
            "comparison",
            "effect_scale",
            "estimand_type",
            "estimator_type",
            "policy_target",
            "target_outcome",
            "target_population",
            "treated_population",
            "unit_of_analysis",
        }

        if set(parsed) != expected_fields:
            raise InvalidAnalysisRunError(
                "Estimand snapshot has invalid fields."
            )

        try:
            estimator_type = AnalysisEstimatorType(parsed["estimator_type"])
        except (TypeError, ValueError) as error:
            raise InvalidAnalysisRunError(
                "Estimand snapshot estimator type is invalid."
            ) from error

        required_text_fields = (
            "estimand_type",
            "target_outcome",
            "target_population",
            "comparison",
            "effect_scale",
            "aggregation_method",
            "analysis_time_scope",
            "unit_of_analysis",
        )

        normalized: dict[str, str] = {}
        for field_name in required_text_fields:
            value = parsed[field_name]
            if not isinstance(value, str) or not value.strip():
                raise InvalidAnalysisRunError(
                    f"Estimand snapshot {field_name} must not be blank."
                )
            normalized[field_name] = value.strip()

        treated_population = parsed["treated_population"]
        if treated_population is not None and (
            not isinstance(treated_population, str)
            or not treated_population.strip()
        ):
            raise InvalidAnalysisRunError(
                "Estimand snapshot treated_population must not be blank."
            )

        policy_target = parsed["policy_target"]
        if policy_target is not None and (
            not isinstance(policy_target, str)
            or not policy_target.strip()
        ):
            raise InvalidAnalysisRunError(
                "Estimand snapshot policy_target must not be blank."
            )

        return cls(
            estimator_type=estimator_type,
            estimand_type=normalized["estimand_type"],
            target_outcome=normalized["target_outcome"],
            target_population=normalized["target_population"],
            treated_population=(
                treated_population.strip()
                if isinstance(treated_population, str)
                else None
            ),
            comparison=normalized["comparison"],
            effect_scale=normalized["effect_scale"],
            aggregation_method=normalized["aggregation_method"],
            analysis_time_scope=normalized["analysis_time_scope"],
            unit_of_analysis=normalized["unit_of_analysis"],
            policy_target=(
                policy_target.strip()
                if isinstance(policy_target, str)
                else None
            ),
        )

    def as_dict(self) -> dict[str, str | None]:
        """Return a deterministic structured representation of the estimand."""

        return {
            "aggregation_method": self.aggregation_method,
            "analysis_time_scope": self.analysis_time_scope,
            "comparison": self.comparison,
            "effect_scale": self.effect_scale,
            "estimand_type": self.estimand_type,
            "estimator_type": self.estimator_type.value,
            "policy_target": self.policy_target,
            "target_outcome": self.target_outcome,
            "target_population": self.target_population,
            "treated_population": self.treated_population,
            "unit_of_analysis": self.unit_of_analysis,
        }
