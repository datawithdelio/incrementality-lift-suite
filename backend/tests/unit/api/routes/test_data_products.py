from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from starlette.responses import StreamingResponse

from incrementality_api.api.v1.routes.data_products import (
    download_report,
    preview_dataset,
    router,
)
from incrementality_api.application.data_products.report_jobs import ReportJob


async def test_dataset_preview_requires_authentication() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/workspaces/{uuid4()}/projects/{uuid4()}/datasets/{uuid4()}/preview"
        )
    assert response.status_code == 401


class InvalidInterventionPreviewService:
    async def preview(self, *args, **kwargs):
        del args, kwargs
        from incrementality_api.application.data_products.explorer import (
            InvalidInterventionDateError,
        )

        raise InvalidInterventionDateError(
            "Intervention date must fall inside the dataset date range."
        )


async def test_dataset_preview_returns_422_for_invalid_intervention_date() -> None:
    try:
        await preview_dataset(
            workspace_id=uuid4(),
            project_id=uuid4(),
            dataset_id=uuid4(),
            principal=object(),  # type: ignore[arg-type]
            service=InvalidInterventionPreviewService(),  # type: ignore[arg-type]
            page_size=50,
            intervention_date="2026-01-01",
        )
    except HTTPException as error:
        assert error.status_code == 422
        assert error.detail == (
            "Intervention date must fall inside the dataset date range."
        )
    else:
        raise AssertionError("Expected HTTP 422 for invalid intervention date.")


class FakeDownloadReportRepository:
    def __init__(self, job: ReportJob) -> None:
        self._job = job
        self.requested_run_id: UUID | None = None

    async def get(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        run_id: UUID,
        report_id: UUID,
    ) -> ReportJob | None:
        del workspace_id, project_id, report_id
        self.requested_run_id = run_id

        if run_id != self._job.analysis_run_id:
            return None

        return self._job


class LazyReportStorage:
    def __init__(self) -> None:
        self.events: list[str] = []

    async def read(
        self,
        *,
        storage_key: str,
        chunk_size: int = 1024 * 1024,
    ) -> AsyncIterator[bytes]:
        del chunk_size
        self.events.append(f"opened:{storage_key}")
        yield b"%PDF-first"
        self.events.append("second-chunk")
        yield b"-second"
        self.events.append("closed")


async def test_download_report_streams_storage_chunks_lazily() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    report_id = uuid4()
    run_id = uuid4()
    storage_key = f"reports/{workspace_id}/analysis/v4.pdf"

    job = ReportJob(
        id=report_id,
        workspace_id=workspace_id,
        project_id=project_id,
        analysis_run_id=run_id,
        version=4,
        format="pdf",
        status="succeeded",
        attempt_count=1,
        max_attempts=3,
        snapshot={},
        storage_key=storage_key,
        failure_reason=None,
        created_at=datetime(2026, 7, 15, tzinfo=UTC),
    )
    storage = LazyReportStorage()

    repository = FakeDownloadReportRepository(job)

    response = await download_report(
        workspace_id=workspace_id,
        project_id=project_id,
        run_id=run_id,
        report_id=report_id,
        principal=object(),
        repository=repository,
        storage=storage,
    )  # type: ignore[arg-type]

    assert repository.requested_run_id == run_id

    assert storage.events == []
    assert isinstance(response, StreamingResponse)
    assert response.media_type == "application/pdf"
    assert response.headers["content-disposition"] == (
        'attachment; filename="analysis-report-v4.pdf"'
    )

    chunks = [chunk async for chunk in response.body_iterator]

    assert chunks == [b"%PDF-first", b"-second"]
    assert storage.events == [
        f"opened:{storage_key}",
        "second-chunk",
        "closed",
    ]
