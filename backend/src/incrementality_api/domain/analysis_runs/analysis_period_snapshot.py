import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Self

from incrementality_api.domain.analysis_runs.errors import InvalidAnalysisRunError
from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType

_TREATMENT_METHODS = {
    AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
    AnalysisEstimatorType.SYNTHETIC_CONTROL,
    AnalysisEstimatorType.GEO_HOLDOUT,
}
_PRE_POST_FIELDS = (
    "pre_period_start_date",
    "pre_period_end_date",
    "post_period_start_date",
    "post_period_end_date",
)
_SERIALIZED_FIELDS = {
    "estimator_type",
    "analysis_start_date",
    "analysis_end_date",
    "intervention_date",
    "pre_period_start_date",
    "pre_period_end_date",
    "post_period_start_date",
    "post_period_end_date",
    "validation_start_date",
    "validation_end_date",
}


@dataclass(frozen=True, slots=True)
class AnalysisPeriodSnapshot:
    """Immutable, estimator-aware calendar window used by an analysis."""

    estimator_type: AnalysisEstimatorType
    analysis_start_date: date
    analysis_end_date: date
    intervention_date: date | None
    pre_period_start_date: date | None
    pre_period_end_date: date | None
    post_period_start_date: date | None
    post_period_end_date: date | None
    validation_start_date: date | None
    validation_end_date: date | None

    @classmethod
    def from_configuration(
        cls,
        estimator_type: AnalysisEstimatorType,
        configuration: Mapping[str, object],
    ) -> Self:
        analysis_start = cls._required_date(configuration, "analysis_start_date")
        analysis_end = cls._required_date(configuration, "analysis_end_date")
        if analysis_start > analysis_end:
            raise InvalidAnalysisRunError(
                "analysis_start_date must not follow analysis_end_date."
            )

        if estimator_type in _TREATMENT_METHODS:
            return cls._for_treatment_method(
                estimator_type=estimator_type,
                configuration=configuration,
                analysis_start=analysis_start,
                analysis_end=analysis_end,
            )
        if estimator_type is AnalysisEstimatorType.MARKETING_MIX_MODEL:
            return cls._for_mmm(configuration, analysis_start, analysis_end)
        return cls._for_off_policy(configuration, analysis_start, analysis_end)

    @classmethod
    def from_configuration_json(
        cls, estimator_type: AnalysisEstimatorType, serialized: str
    ) -> Self:
        if not serialized.strip():
            raise InvalidAnalysisRunError("Analysis configuration must not be blank.")
        try:
            configuration = json.loads(serialized)
        except json.JSONDecodeError as error:
            raise InvalidAnalysisRunError("Analysis configuration must be valid JSON.") from error
        if not isinstance(configuration, dict):
            raise InvalidAnalysisRunError("Analysis configuration must be a JSON object.")
        return cls.from_configuration(estimator_type, configuration)

    @classmethod
    def from_json(cls, serialized: str) -> Self:
        if not serialized.strip():
            raise InvalidAnalysisRunError("Analysis-period snapshot must not be blank.")
        try:
            parsed = json.loads(serialized)
        except json.JSONDecodeError as error:
            raise InvalidAnalysisRunError(
                "Analysis-period snapshot must be valid JSON."
            ) from error
        if not isinstance(parsed, dict) or set(parsed) != _SERIALIZED_FIELDS:
            raise InvalidAnalysisRunError("Analysis-period snapshot has invalid fields.")
        estimator_value = parsed["estimator_type"]
        if not isinstance(estimator_value, str):
            raise InvalidAnalysisRunError("Analysis-period estimator type is invalid.")
        try:
            estimator_type = AnalysisEstimatorType(estimator_value)
        except ValueError as error:
            raise InvalidAnalysisRunError("Analysis-period estimator type is invalid.") from error
        configuration = {
            key: value
            for key, value in parsed.items()
            if key != "estimator_type" and value is not None
        }
        if not all(isinstance(value, str) for value in configuration.values()):
            raise InvalidAnalysisRunError("Analysis-period snapshot dates must be strings or null.")
        return cls.from_configuration(estimator_type, configuration)

    @property
    def canonical_json(self) -> str:
        return json.dumps(
            self.as_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )

    def as_dict(self) -> dict[str, str | None]:
        return {
            "estimator_type": self.estimator_type.value,
            "analysis_start_date": self.analysis_start_date.isoformat(),
            "analysis_end_date": self.analysis_end_date.isoformat(),
            "intervention_date": self._serialize(self.intervention_date),
            "pre_period_start_date": self._serialize(self.pre_period_start_date),
            "pre_period_end_date": self._serialize(self.pre_period_end_date),
            "post_period_start_date": self._serialize(self.post_period_start_date),
            "post_period_end_date": self._serialize(self.post_period_end_date),
            "validation_start_date": self._serialize(self.validation_start_date),
            "validation_end_date": self._serialize(self.validation_end_date),
        }

    def contains(self, value: date) -> bool:
        return self.analysis_start_date <= value <= self.analysis_end_date

    def canonicalize_configuration(
        self, configuration: Mapping[str, object]
    ) -> dict[str, object]:
        canonical = dict(configuration)
        for field_name in _SERIALIZED_FIELDS - {"estimator_type"}:
            canonical.pop(field_name, None)
        canonical.update(
            {
                key: value
                for key, value in self.as_dict().items()
                if key != "estimator_type" and value is not None
            }
        )
        return canonical

    @classmethod
    def _for_treatment_method(
        cls,
        *,
        estimator_type: AnalysisEstimatorType,
        configuration: Mapping[str, object],
        analysis_start: date,
        analysis_end: date,
    ) -> Self:
        intervention = cls._required_date(configuration, "intervention_date")
        if not analysis_start < intervention <= analysis_end:
            raise InvalidAnalysisRunError(
                "intervention_date must fall inside the analysis range with a usable pre-period."
            )
        supplied = [configuration.get(field) is not None for field in _PRE_POST_FIELDS]
        if any(supplied) and not all(supplied):
            raise InvalidAnalysisRunError(
                "Explicit pre- and post-period dates must be supplied together."
            )
        if all(supplied):
            pre_start, pre_end, post_start, post_end = (
                cls._required_date(configuration, field) for field in _PRE_POST_FIELDS
            )
        else:
            pre_start = analysis_start
            pre_end = intervention - timedelta(days=1)
            post_start = intervention
            post_end = analysis_end
        if not analysis_start <= pre_start <= pre_end < intervention:
            raise InvalidAnalysisRunError(
                "The pre-period must be inside the analysis range and end before the intervention."
            )
        if not intervention <= post_start <= post_end <= analysis_end:
            raise InvalidAnalysisRunError(
                "The post-period must start on or after the intervention inside the analysis range."
            )
        return cls(
            estimator_type=estimator_type,
            analysis_start_date=analysis_start,
            analysis_end_date=analysis_end,
            intervention_date=intervention,
            pre_period_start_date=pre_start,
            pre_period_end_date=pre_end,
            post_period_start_date=post_start,
            post_period_end_date=post_end,
            validation_start_date=None,
            validation_end_date=None,
        )

    @classmethod
    def _for_mmm(
        cls,
        configuration: Mapping[str, object],
        analysis_start: date,
        analysis_end: date,
    ) -> Self:
        validation_start = cls._optional_date(configuration, "validation_start_date")
        validation_end = cls._optional_date(configuration, "validation_end_date")
        if (validation_start is None) != (validation_end is None):
            raise InvalidAnalysisRunError(
                "MMM validation_start_date and validation_end_date must be supplied together."
            )
        if validation_start is not None and validation_end is not None and not (
            analysis_start <= validation_start <= validation_end <= analysis_end
        ):
            raise InvalidAnalysisRunError(
                "MMM validation window must be inside the analysis range."
            )
        cls._reject_present(configuration, "intervention_date", *_PRE_POST_FIELDS)
        return cls(
            estimator_type=AnalysisEstimatorType.MARKETING_MIX_MODEL,
            analysis_start_date=analysis_start,
            analysis_end_date=analysis_end,
            intervention_date=None,
            pre_period_start_date=None,
            pre_period_end_date=None,
            post_period_start_date=None,
            post_period_end_date=None,
            validation_start_date=validation_start,
            validation_end_date=validation_end,
        )

    @classmethod
    def _for_off_policy(
        cls,
        configuration: Mapping[str, object],
        analysis_start: date,
        analysis_end: date,
    ) -> Self:
        intervention = cls._optional_date(configuration, "intervention_date")
        if intervention is not None and not analysis_start <= intervention <= analysis_end:
            raise InvalidAnalysisRunError("intervention_date must fall inside the analysis range.")
        cls._reject_present(
            configuration, *_PRE_POST_FIELDS, "validation_start_date", "validation_end_date"
        )
        return cls(
            estimator_type=AnalysisEstimatorType.OFF_POLICY_EVALUATION,
            analysis_start_date=analysis_start,
            analysis_end_date=analysis_end,
            intervention_date=intervention,
            pre_period_start_date=None,
            pre_period_end_date=None,
            post_period_start_date=None,
            post_period_end_date=None,
            validation_start_date=None,
            validation_end_date=None,
        )

    @classmethod
    def _required_date(cls, values: Mapping[str, object], field_name: str) -> date:
        parsed = cls._optional_date(values, field_name)
        if parsed is None:
            raise InvalidAnalysisRunError(f"{field_name} is required.")
        return parsed

    @staticmethod
    def _optional_date(values: Mapping[str, object], field_name: str) -> date | None:
        value = values.get(field_name)
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise InvalidAnalysisRunError(f"{field_name} must be a nonblank ISO date.")
        normalized = value.strip()
        try:
            if "T" not in normalized:
                return date.fromisoformat(normalized)
            parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
        except ValueError as error:
            raise InvalidAnalysisRunError(f"{field_name} must be a valid ISO date.") from error
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise InvalidAnalysisRunError(
                f"{field_name} datetime must be timezone-aware."
            )
        return parsed.date()

    @staticmethod
    def _reject_present(configuration: Mapping[str, object], *field_names: str) -> None:
        unsupported = next(
            (field for field in field_names if configuration.get(field) is not None), None
        )
        if unsupported is not None:
            raise InvalidAnalysisRunError(
                f"{unsupported} is not supported for this estimator."
            )

    @staticmethod
    def _serialize(value: date | None) -> str | None:
        return None if value is None else value.isoformat()
