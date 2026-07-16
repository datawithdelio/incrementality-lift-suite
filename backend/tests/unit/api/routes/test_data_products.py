from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.responses import StreamingResponse

from incrementality_api.api.v1.routes.data_products import download_report, router
from incrementality_api.application.data_products.report_jobs import ReportJob


async def test_dataset_preview_requires_authentication() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/workspaces/{uuid4()}/projects/{uuid4()}/datasets/{uuid4()}/preview"
        )
    assert response.status_code == 401


class FakeDownloadReportRepository:
    def __init__(self, job: ReportJob) -> None:
        self._job = job

    async def get(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        report_id: UUID,
    ) -> ReportJob | None:
        del workspace_id, project_id, report_id
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
    storage_key = f"reports/{workspace_id}/analysis/v4.pdf"

    job = ReportJob(
        id=report_id,
        workspace_id=workspace_id,
        project_id=project_id,
        analysis_run_id=uuid4(),
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

    response = await download_report(
        workspace_id=workspace_id,
        project_id=project_id,
        report_id=report_id,
        principal=object(),
        repository=FakeDownloadReportRepository(job),
        storage=storage,
    )  # type: ignore[arg-type]

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
