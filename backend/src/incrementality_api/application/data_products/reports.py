import csv
import io
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from incrementality_api.application.data_products.pdf_report_renderer import (
    PdfReportRenderer as PdfReportRenderer,
)


@dataclass(frozen=True, slots=True)
class ReportModel:
    title: str
    generated_at: datetime
    analysis_run_id: str
    estimator: str
    estimator_version: str
    dataset_id: str
    dataset_checksum: str
    mapping_version: int
    configuration: Mapping[str, object]
    estimate: float
    confidence_low: float
    confidence_high: float
    diagnostics: Mapping[str, object]
    warnings: tuple[str, ...]
    business_impact: Mapping[str, object]
    quality_summary: Mapping[str, object]
    limitations: tuple[str, ...]
    lineage: Mapping[str, object] = field(
        default_factory=dict,
    )
    standard_error: float | None = None
    p_value: float | None = None

    @property
    def conclusion(self) -> str:
        if self.diagnostics.get("causal_claim_allowed") is True:
            return f"Estimated causal increase: {self.estimate:.2f}."
        return (
            f"Estimated directional association: {self.estimate:.2f}; do not interpret as causal."
        )


def _canonical_json(
    value: object,
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    )


def _lineage_rows(
    model: ReportModel,
) -> tuple[tuple[str, str], ...]:
    return tuple(
        (
            key,
            _canonical_json(model.lineage[key]),
        )
        for key in sorted(model.lineage)
    )


def _diagnostic_label(value: object, fallback: str) -> str:
    rendered = str(value).strip() if value is not None else ""
    return rendered.replace("_", " ").capitalize() if rendered else fallback


def _pre_period_comparability(model: ReportModel) -> object | None:
    if model.estimator == "synthetic_control":
        return model.diagnostics.get("pre_treatment_rmspe")

    balance = model.diagnostics.get("balance_diagnostics")
    if isinstance(balance, Mapping):
        standardized_difference = balance.get("standardized_mean_difference")
        if standardized_difference is not None:
            return standardized_difference

    return model.diagnostics.get("pre_period_comparability")


class ReportRenderer(Protocol):
    media_type: str
    extension: str

    def render(self, model: ReportModel) -> bytes: ...


class CsvReportRenderer:
    media_type = "text/csv"
    extension = "csv"

    def render(self, model: ReportModel) -> bytes:
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(("section", "metric", "value"))
        sample_counts_value = model.diagnostics.get("sample_counts", {})
        sample_counts = (
            sample_counts_value
            if isinstance(sample_counts_value, Mapping)
            else {}
        )

        relative_lift = model.business_impact.get("relative_lift")

        incremental_outcome = model.business_impact.get("incremental_outcome")
        if incremental_outcome is None:
            incremental_outcome = model.business_impact.get("incremental_conversions")
        if incremental_outcome is None:
            incremental_outcome = model.business_impact.get("incremental_revenue")

        treated_units = sample_counts.get(
            "treated_units",
            model.diagnostics.get("treated_units"),
        )
        control_units = sample_counts.get(
            "control_units",
            model.diagnostics.get("control_units"),
        )
        observations = sample_counts.get(
            "observations",
            model.diagnostics.get("sample_size"),
        )

        design_quality = _diagnostic_label(
            model.diagnostics.get("design_assessment")
            or model.quality_summary.get("design_assessment"),
            "Valid",
        )
        causal_evidence = (
            "Supported"
            if model.diagnostics.get("causal_claim_allowed") is True
            else "Not supported"
        )

        rows = [
            ("overview", "title", model.title),
            ("overview", "analysis_run_id", model.analysis_run_id),
            ("versions", "estimator", f"{model.estimator}@{model.estimator_version}"),
            ("versions", "dataset", f"{model.dataset_id}@{model.dataset_checksum}"),
            ("versions", "mapping_version", model.mapping_version),
            ("estimate", "conclusion", model.conclusion),
            ("estimate", "effect", model.estimate),
            ("estimate", "standard_error", model.standard_error),
            ("estimate", "p_value", model.p_value),
            ("estimate", "confidence_low", model.confidence_low),
            ("estimate", "confidence_high", model.confidence_high),
            ("estimate", "confidence_interval", f"{model.confidence_low},{model.confidence_high}"),
            ("business_impact", "relative_lift", relative_lift),
            ("business_impact", "incremental_outcome", incremental_outcome),
            ("sample", "treated_units", treated_units),
            ("sample", "control_units", control_units),
            ("sample", "observations", observations),
            ("diagnostics", "design_quality", design_quality),
            (
                "diagnostics",
                "pre_period_comparability",
                _pre_period_comparability(model),
            ),
            ("diagnostics", "causal_evidence", causal_evidence),
            ("diagnostics", "blocking_warnings", len(model.warnings)),
        ]
        rows.extend(
            ("dataset_readiness", str(metric), value)
            for metric, value in sorted(model.quality_summary.items())
        )
        if model.estimator == "synthetic_control":
            rows.append(
                (
                    "synthetic_control",
                    "pre_treatment_rmspe",
                    model.diagnostics.get("pre_treatment_rmspe"),
                )
            )
            donor_weights = model.diagnostics.get("donor_weights")
            if isinstance(donor_weights, Mapping):
                rows.extend(
                    ("synthetic_control_donor_weight", str(donor), weight)
                    for donor, weight in sorted(donor_weights.items())
                )
        writer.writerows(rows)
        for key, value in _lineage_rows(model):
            writer.writerow(
                (
                    "lineage",
                    key,
                    value,
                )
            )
        for warning in model.warnings:
            writer.writerow(("diagnostics", "warning", warning))
        for limitation in model.limitations:
            writer.writerow(("limitations", "item", limitation))
        return output.getvalue().encode()
