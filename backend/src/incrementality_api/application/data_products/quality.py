from collections import Counter
from contextlib import suppress
from dataclasses import dataclass
from datetime import date
from typing import Protocol

import numpy as np
from scipy import stats  # type: ignore[import-untyped]


@dataclass(frozen=True, slots=True)
class QualityFinding:
    rule_id: str
    severity: str
    passed: bool
    evidence: dict[str, object]
    recommendation: str


@dataclass(frozen=True, slots=True)
class DataQualityInput:
    rows: tuple[dict[str, str], ...]
    estimator_type: str
    leakage_columns: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DataQualityResult:
    score: int
    ready: bool
    findings: tuple[QualityFinding, ...]


class QualityPolicy(Protocol):
    def evaluate(self, data: DataQualityInput) -> QualityFinding: ...


class MissingDataPolicy:
    def evaluate(self, data: DataQualityInput) -> QualityFinding:
        cells = sum(len(row) for row in data.rows)
        missing = sum(not str(value).strip() for row in data.rows for value in row.values())
        share = missing / cells if cells else 1.0
        blocking = share >= 0.5
        return QualityFinding(
            "missing_data",
            "blocking" if blocking else ("warning" if missing else "info"),
            not blocking,
            {"missing_cells": missing, "missing_share": share},
            "Impute or remove rows with missing required values.",
        )


class DuplicateRowsPolicy:
    def evaluate(self, data: DataQualityInput) -> QualityFinding:
        signatures = [tuple(sorted(row.items())) for row in data.rows]
        duplicates = len(signatures) - len(set(signatures))
        return QualityFinding(
            "duplicate_rows",
            "warning" if duplicates else "info",
            True,
            {"duplicate_rows": duplicates},
            "Deduplicate repeated observations before analysis.",
        )


class InvalidTypesPolicy:
    def evaluate(self, data: DataQualityInput) -> QualityFinding:
        outcome = next(
            (
                name
                for name in ("outcome", "revenue", "conversions")
                if data.rows and name in data.rows[0]
            ),
            None,
        )
        invalid = 0
        invalid_dates = 0
        if outcome:
            for row in data.rows:
                try:
                    float(row[outcome])
                except ValueError:
                    invalid += 1
        for row in data.rows:
            raw_date = row.get("date") or row.get("time")
            if raw_date:
                try:
                    date.fromisoformat(raw_date[:10])
                except ValueError:
                    invalid_dates += 1
        total_invalid = invalid + invalid_dates
        return QualityFinding(
            "invalid_types",
            "blocking" if total_invalid else "info",
            total_invalid == 0,
            {
                "invalid_numeric_values": invalid,
                "invalid_date_values": invalid_dates,
            },
            "Correct values that do not match the mapped column type.",
        )


class DateGapPolicy:
    def evaluate(self, data: DataQualityInput) -> QualityFinding:
        dates: list[date] = []
        for row in data.rows:
            value = row.get("date") or row.get("time")
            if value:
                with suppress(ValueError):
                    dates.append(date.fromisoformat(value[:10]))
        gaps = sum(
            (later - earlier).days > 1
            for earlier, later in zip(sorted(set(dates)), sorted(set(dates))[1:], strict=False)
        )
        return QualityFinding(
            "date_gaps",
            "warning" if gaps else "info",
            True,
            {"gap_count": gaps},
            "Fill missing periods or document why they are absent.",
        )


class OutlierPolicy:
    def evaluate(self, data: DataQualityInput) -> QualityFinding:
        values: list[float] = []
        for row in data.rows:
            raw = row.get("outcome") or row.get("revenue") or row.get("conversions")
            if raw is not None:
                with suppress(ValueError):
                    values.append(float(raw))
        count = int(np.sum(np.abs(stats.zscore(values)) > 3)) if len(values) > 3 else 0
        return QualityFinding(
            "outliers",
            "warning" if count else "info",
            True,
            {"outlier_count": count},
            "Review extreme outcomes and winsorize only with justification.",
        )


class SampleSizePolicy:
    def evaluate(self, data: DataQualityInput) -> QualityFinding:
        small = len(data.rows) < 30
        return QualityFinding(
            "sample_size",
            "warning" if small else "info",
            True,
            {"rows": len(data.rows)},
            "Collect at least 30 observations and preferably more per group.",
        )


class TreatmentBalancePolicy:
    def evaluate(self, data: DataQualityInput) -> QualityFinding:
        values = [row.get("treated", "").casefold() for row in data.rows]
        counts = Counter(values)
        nonzero = [value for key, value in counts.items() if key]
        imbalance = bool(nonzero) and min(nonzero) / max(nonzero) < 0.2
        return QualityFinding(
            "treatment_control_balance",
            "warning" if imbalance else "info",
            True,
            {"counts": dict(counts)},
            "Add comparable treatment or control observations.",
        )


class PeriodCoveragePolicy:
    def evaluate(self, data: DataQualityInput) -> QualityFinding:
        insufficient = len(data.rows) < 8
        return QualityFinding(
            "pre_post_periods",
            "blocking" if insufficient else "info",
            not insufficient,
            {"observations": len(data.rows)},
            "Provide sufficient pre- and post-treatment periods.",
        )


class PropensityOverlapPolicy:
    def evaluate(self, data: DataQualityInput) -> QualityFinding:
        values = [float(row["propensity"]) for row in data.rows if row.get("propensity")]
        weak = not values or min(values) < 0.05 or max(values) > 0.95
        return QualityFinding(
            "propensity_overlap",
            "blocking" if not values else ("warning" if weak else "info"),
            bool(values),
            {"minimum": min(values, default=None), "maximum": max(values, default=None)},
            "Collect decisions where both policies assign meaningful probability.",
        )


class GeoCoveragePolicy:
    def evaluate(self, data: DataQualityInput) -> QualityFinding:
        geos = {row.get("market") or row.get("geo") for row in data.rows}
        covered = len(geos - {None, ""}) >= 4 and all(
            row.get("latitude") and row.get("longitude") for row in data.rows
        )
        return QualityFinding(
            "geo_coverage",
            "blocking" if not covered else "info",
            covered,
            {"geographies": len(geos - {None, ""})},
            "Provide coordinates and at least four comparable geographies.",
        )


class MmmContinuityPolicy:
    def evaluate(self, data: DataQualityInput) -> QualityFinding:
        enough = len(data.rows) >= 12
        return QualityFinding(
            "mmm_continuity",
            "blocking" if not enough else "info",
            enough,
            {"periods": len(data.rows)},
            "Provide at least 12 continuous time periods for MMM.",
        )


class LeakagePolicy:
    def evaluate(self, data: DataQualityInput) -> QualityFinding:
        present = [name for name in data.leakage_columns if data.rows and name in data.rows[0]]
        return QualityFinding(
            "post_treatment_leakage",
            "blocking" if present else "info",
            not present,
            {"columns": present},
            "Remove variables measured after treatment assignment.",
        )


class DataQualityAssessor:
    def __init__(self) -> None:
        self._base: tuple[QualityPolicy, ...] = (
            MissingDataPolicy(),
            DuplicateRowsPolicy(),
            InvalidTypesPolicy(),
            DateGapPolicy(),
            OutlierPolicy(),
            TreatmentBalancePolicy(),
            PeriodCoveragePolicy(),
            SampleSizePolicy(),
            LeakagePolicy(),
        )

    def assess(self, data: DataQualityInput) -> DataQualityResult:
        policies = list(self._base)
        if data.estimator_type == "off_policy_evaluation":
            policies.append(PropensityOverlapPolicy())
        if data.estimator_type == "geo_holdout":
            policies.append(GeoCoveragePolicy())
        if data.estimator_type == "marketing_mix_model":
            policies.append(MmmContinuityPolicy())
        findings = tuple(policy.evaluate(data) for policy in policies)
        penalty = sum(
            25
            if item.severity == "blocking" and not item.passed
            else 8
            if item.severity == "warning"
            else 0
            for item in findings
        )
        return DataQualityResult(
            max(0, 100 - penalty),
            not any(item.severity == "blocking" and not item.passed for item in findings),
            findings,
        )
