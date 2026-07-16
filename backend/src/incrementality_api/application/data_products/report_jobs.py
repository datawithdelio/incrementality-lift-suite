from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from incrementality_api.application.data_products.reports import (
    CsvReportRenderer,
    PdfReportRenderer,
    ReportModel,
)
from incrementality_api.application.datasets.ports import DatasetObjectStorage

RECOVERY_ERROR = "Report worker claim expired before completion."


@dataclass(frozen=True, slots=True)
class ReportJob:
    id: UUID
    workspace_id: UUID
    project_id: UUID
    analysis_run_id: UUID
    version: int
    format: str
    status: str
    attempt_count: int
    max_attempts: int
    snapshot: dict[str, object]
    storage_key: str | None
    failure_reason: str | None
    created_at: datetime


class ReportJobRepository(Protocol):
    async def claim_next(self, now: datetime) -> ReportJob | None: ...

    async def succeed(
        self,
        job_id: UUID,
        storage_key: str,
        now: datetime,
        *,
        byte_size: int | None = None,
        checksum_sha256: str | None = None,
    ) -> ReportJob: ...

    async def fail(
        self,
        job_id: UUID,
        error: str,
        now: datetime,
    ) -> ReportJob: ...


class StaleReportJobRepository(Protocol):
    async def recover_stale(
        self,
        *,
        claimed_before: datetime,
        recovered_at: datetime,
        error: str,
    ) -> ReportJob | None: ...


class ReportClock(Protocol):
    def now(self) -> datetime: ...


class RecoverStaleReportJobAction(Protocol):
    async def execute(self) -> ReportJob | None: ...


class ReportArtifactReconciliationAction(Protocol):
    async def execute(self) -> object | None: ...


class RecoverStaleReportJob:
    """Recover one report job abandoned by a worker."""

    def __init__(
        self,
        *,
        repository: StaleReportJobRepository,
        clock: ReportClock,
        claim_timeout_seconds: int = 300,
    ) -> None:
        if claim_timeout_seconds <= 0:
            raise ValueError("Claim timeout must be positive.")

        self._repository = repository
        self._clock = clock
        self._claim_timeout = timedelta(seconds=claim_timeout_seconds)

    async def execute(self) -> ReportJob | None:
        current_time = self._clock.now()

        return await self._repository.recover_stale(
            claimed_before=current_time - self._claim_timeout,
            recovered_at=current_time,
            error=RECOVERY_ERROR,
        )


async def _one_chunk(payload: bytes) -> AsyncIterator[bytes]:
    yield payload


class ProcessNextReportJob:
    def __init__(
        self,
        *,
        repository: ReportJobRepository,
        storage: DatasetObjectStorage,
        clock: ReportClock,
        recover_stale: RecoverStaleReportJobAction | None = None,
        reconcile_artifacts: ReportArtifactReconciliationAction | None = None,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._clock = clock
        self._recover_stale = recover_stale
        self._reconcile_artifacts = reconcile_artifacts

    async def execute(self) -> ReportJob | None:
        if self._reconcile_artifacts is not None:
            await self._reconcile_artifacts.execute()

        if self._recover_stale is not None:
            await self._recover_stale.execute()

        job = await self._repository.claim_next(self._clock.now())
        if job is None:
            return None

        try:
            snapshot = dict(job.snapshot)
            generated_at = snapshot.get("generated_at")
            if isinstance(generated_at, str):
                snapshot["generated_at"] = datetime.fromisoformat(generated_at)

            for name in ("warnings", "limitations"):
                value = snapshot.get(name)
                if isinstance(value, list):
                    snapshot[name] = tuple(str(item) for item in value)

            model = ReportModel(**snapshot)  # type: ignore[arg-type]
            renderer = PdfReportRenderer() if job.format == "pdf" else CsvReportRenderer()
            payload = renderer.render(model)

            key = (
                f"reports/{job.workspace_id}/{job.analysis_run_id}/"
                f"v{job.version}.{renderer.extension}"
            )

            write_result = await self._storage.write(
                storage_key=key,
                media_type=renderer.media_type,
                chunks=_one_chunk(payload),
            )

            return await self._repository.succeed(
                job.id,
                key,
                self._clock.now(),
                byte_size=write_result.byte_size,
                checksum_sha256=write_result.checksum_sha256,
            )
        except Exception:
            return await self._repository.fail(
                job.id,
                "Report generation failed safely.",
                self._clock.now(),
            )
