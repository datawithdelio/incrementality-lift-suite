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
        rows = [
            ("overview", "title", model.title),
            ("overview", "analysis_run_id", model.analysis_run_id),
            ("versions", "estimator", f"{model.estimator}@{model.estimator_version}"),
            ("versions", "dataset", f"{model.dataset_id}@{model.dataset_checksum}"),
            ("versions", "mapping_version", model.mapping_version),
            ("estimate", "conclusion", model.conclusion),
            ("estimate", "confidence_interval", f"{model.confidence_low},{model.confidence_high}"),
            ("quality", "summary", dict(model.quality_summary)),
        ]
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
