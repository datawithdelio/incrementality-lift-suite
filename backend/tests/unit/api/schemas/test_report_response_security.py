from datetime import UTC, datetime
from uuid import uuid4

from incrementality_api.api.v1.schemas.data_products import (
    ReportJobResponse,
)


def test_report_job_response_does_not_expose_storage_key() -> None:
    assert "storage_key" not in ReportJobResponse.model_fields


def test_report_job_response_sanitizes_failure_reason() -> None:
    raw_failure = (
        "Traceback: RuntimeError reading "
        "/var/app/private/report.pdf from "
        "s3://secret-bucket/internal-key"
    )

    response = ReportJobResponse(
        id=uuid4(),
        workspace_id=uuid4(),
        project_id=uuid4(),
        analysis_run_id=uuid4(),
        version=1,
        format="pdf",
        status="failed",
        attempt_count=3,
        max_attempts=3,
        failure_reason=raw_failure,
        created_at=datetime(
            2026,
            7,
            19,
            tzinfo=UTC,
        ),
    )

    assert response.failure_reason == (
        "Report generation failed. "
        "Please regenerate the report."
    )

    serialized = response.model_dump_json()

    assert "Traceback" not in serialized
    assert "/var/app/private" not in serialized
    assert "s3://secret-bucket" not in serialized
