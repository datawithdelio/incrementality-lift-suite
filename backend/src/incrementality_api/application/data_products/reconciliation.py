from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from incrementality_api.application.data_products.report_jobs import ReportJob

MISSING_REPORT_ARTIFACT_ERROR = (
    "Report artifact is missing from object storage."
)


class ReportArtifactRepository(Protocol):
    async def list_succeeded(self) -> tuple[ReportJob, ...]:
        """Return reports that claim to have durable artifacts."""

    async def mark_artifact_missing(
        self,
        *,
        job_id: UUID,
        error: str,
        now: datetime,
    ) -> None:
        """Record that a completed report artifact is unavailable."""


class ReportArtifactStorage(Protocol):
    async def exists(
        self,
        *,
        storage_key: str,
    ) -> bool:
        """Return whether an object exists in durable storage."""


class ReconciliationClock(Protocol):
    def now(self) -> datetime:
        """Return the current timezone-aware timestamp."""


@dataclass(frozen=True, slots=True)
class ReportArtifactReconciliationResult:
    checked: int
    missing: int


class ReconcileReportArtifacts:
    """Find succeeded reports whose object-storage artifact is missing."""

    def __init__(
        self,
        *,
        repository: ReportArtifactRepository,
        storage: ReportArtifactStorage,
        clock: ReconciliationClock,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._clock = clock

    async def execute(self) -> ReportArtifactReconciliationResult:
        jobs = await self._repository.list_succeeded()
        current_time = self._clock.now()
        missing_count = 0

        for job in jobs:
            artifact_exists = (
                job.storage_key is not None
                and await self._storage.exists(
                    storage_key=job.storage_key,
                )
            )

            if artifact_exists:
                continue

            await self._repository.mark_artifact_missing(
                job_id=job.id,
                error=MISSING_REPORT_ARTIFACT_ERROR,
                now=current_time,
            )
            missing_count += 1

        return ReportArtifactReconciliationResult(
            checked=len(jobs),
            missing=missing_count,
        )



class ReportArtifactReconciliationAction(Protocol):
    async def execute(self) -> ReportArtifactReconciliationResult:
        """Reconcile report records against durable object storage."""


class ReconcileReportArtifactsPeriodically:
    """Run report-artifact reconciliation only when its interval is due."""

    def __init__(
        self,
        *,
        reconciliation: ReportArtifactReconciliationAction,
        clock: ReconciliationClock,
        interval_seconds: int,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("Reconciliation interval must be positive.")

        self._reconciliation = reconciliation
        self._clock = clock
        self._interval = timedelta(seconds=interval_seconds)
        self._next_due_at: datetime | None = None

    async def execute(self) -> ReportArtifactReconciliationResult | None:
        current_time = self._clock.now()

        if self._next_due_at is not None and current_time < self._next_due_at:
            return None

        result = await self._reconciliation.execute()
        self._next_due_at = current_time + self._interval

        return result
