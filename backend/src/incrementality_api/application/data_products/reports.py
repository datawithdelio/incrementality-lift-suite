import csv
import io
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from reportlab.lib.pagesizes import letter  # type: ignore[import-untyped]
from reportlab.pdfgen import canvas  # type: ignore[import-untyped]


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


class PdfReportRenderer:
    media_type = "application/pdf"
    extension = "pdf"

    def render(self, model: ReportModel) -> bytes:
        output = io.BytesIO()
        document = canvas.Canvas(output, pagesize=letter, invariant=1)
        text = document.beginText(54, 738)
        text.setFont("Helvetica-Bold", 18)
        text.textLine(model.title)
        text.setFont("Helvetica", 10)
        sections = (
            ("Analysis overview", model.conclusion),
            (
                "Method and configuration",
                f"{model.estimator} {model.estimator_version} · {dict(model.configuration)}",
            ),
            (
                "Estimate and uncertainty",
                (
                    f"{model.estimate:.2f} (95% CI {model.confidence_low:.2f} "
                    f"to {model.confidence_high:.2f})"
                ),
            ),
            ("Diagnostics and warnings", "; ".join(model.warnings) or "No warnings"),
            ("Business impact", str(dict(model.business_impact))),
            ("Data quality", str(dict(model.quality_summary))),
            ("Limitations", "; ".join(model.limitations)),
            (
                "Technical appendix",
                (
                    f"dataset {model.dataset_id}@{model.dataset_checksum}; "
                    f"mapping v{model.mapping_version}; run {model.analysis_run_id}"
                ),
            ),
        )
        for heading, content in sections:
            text.moveCursor(0, -18)
            text.setFont("Helvetica-Bold", 11)
            text.textLine(heading)
            text.setFont("Helvetica", 9)
            text.textLines(content[:600])
        document.drawText(text)
        document.setFont("Helvetica-Bold", 10)
        document.drawString(54, 138, "Estimate and 95% confidence interval")
        document.setStrokeColorRGB(0.12, 0.48, 0.33)
        document.setLineWidth(3)
        document.line(90, 112, 500, 112)
        span = max(model.confidence_high - model.confidence_low, 1e-9)
        estimate_x = 90 + 410 * (model.estimate - model.confidence_low) / span
        document.circle(estimate_x, 112, 5, fill=1)

        if model.lineage:
            document.showPage()
            lineage_text = document.beginText(
                54,
                738,
            )
            lineage_text.setFont(
                "Helvetica-Bold",
                16,
            )
            lineage_text.textLine(
                "Reproducibility lineage"
            )
            lineage_text.setFont(
                "Helvetica",
                8,
            )

            for key, value in _lineage_rows(model):
                lineage_text.moveCursor(
                    0,
                    -12,
                )
                lineage_text.setFont(
                    "Helvetica-Bold",
                    9,
                )
                lineage_text.textLine(key)
                lineage_text.setFont(
                    "Helvetica",
                    7,
                )

                chunks = tuple(
                    value[index : index + 90]
                    for index in range(
                        0,
                        len(value),
                        90,
                    )
                ) or ("",)

                for chunk in chunks:
                    if lineage_text.getY() < 60:
                        document.drawText(
                            lineage_text
                        )
                        document.showPage()
                        lineage_text = document.beginText(
                            54,
                            738,
                        )
                        lineage_text.setFont(
                            "Helvetica",
                            7,
                        )

                    lineage_text.textLine(
                        chunk
                    )

            document.drawText(
                lineage_text
            )

        document.save()
        return output.getvalue()
