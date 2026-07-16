from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from incrementality_api.application.data_products.reconciliation import (
    MISSING_REPORT_ARTIFACT_ERROR,
    ReconcileReportArtifacts,
    ReconcileReportArtifactsPeriodically,
    ReportArtifactReconciliationResult,
)
from incrementality_api.application.data_products.report_jobs import (
    ProcessNextReportJob,
    ReportJob,
)

NOW = datetime(2026, 7, 16, 14, 30, tzinfo=UTC)


class FakeClock:
    def now(self) -> datetime:
        return NOW


class FakeReportRepository:
    def __init__(self, jobs: tuple[ReportJob, ...]) -> None:
        self._jobs = jobs
        self.missing_artifacts: list[tuple[UUID, str, datetime]] = []

    async def list_succeeded(self) -> tuple[ReportJob, ...]:
        return self._jobs

    async def mark_artifact_missing(
        self,
        *,
        job_id: UUID,
        error: str,
        now: datetime,
    ) -> None:
        self.missing_artifacts.append((job_id, error, now))


class FakeReportStorage:
    def __init__(self, existing_keys: set[str]) -> None:
        self._existing_keys = existing_keys
        self.checked_keys: list[str] = []

    async def exists(self, *, storage_key: str) -> bool:
        self.checked_keys.append(storage_key)
        return storage_key in self._existing_keys


def succeeded_report(storage_key: str | None) -> ReportJob:
    return ReportJob(
        id=uuid4(),
        workspace_id=uuid4(),
        project_id=uuid4(),
        analysis_run_id=uuid4(),
        version=1,
        format="pdf",
        status="succeeded",
        attempt_count=1,
        max_attempts=3,
        snapshot={},
        storage_key=storage_key,
        failure_reason=None,
        created_at=NOW,
    )


async def test_marks_missing_succeeded_report_artifact() -> None:
    existing = succeeded_report("reports/existing.pdf")
    missing = succeeded_report("reports/missing.pdf")
    repository = FakeReportRepository((existing, missing))
    storage = FakeReportStorage({"reports/existing.pdf"})

    result = await ReconcileReportArtifacts(
        repository=repository,
        storage=storage,
        clock=FakeClock(),
    ).execute()

    assert result.checked == 2
    assert result.missing == 1
    assert storage.checked_keys == [
        "reports/existing.pdf",
        "reports/missing.pdf",
    ]
    assert repository.missing_artifacts == [
        (
            missing.id,
            MISSING_REPORT_ARTIFACT_ERROR,
            NOW,
        )
    ]


async def test_treats_succeeded_report_without_storage_key_as_missing() -> None:
    missing = succeeded_report(None)
    repository = FakeReportRepository((missing,))
    storage = FakeReportStorage(set())

    result = await ReconcileReportArtifacts(
        repository=repository,
        storage=storage,
        clock=FakeClock(),
    ).execute()

    assert result.checked == 1
    assert result.missing == 1
    assert storage.checked_keys == []
    assert repository.missing_artifacts == [
        (
            missing.id,
            MISSING_REPORT_ARTIFACT_ERROR,
            NOW,
        )
    ]



class MutableClock:
    def __init__(self, current_time: datetime) -> None:
        self.current_time = current_time

    def now(self) -> datetime:
        return self.current_time


class CountingReconciliation:
    def __init__(self) -> None:
        self.call_count = 0

    async def execute(self) -> ReportArtifactReconciliationResult:
        self.call_count += 1
        return ReportArtifactReconciliationResult(
            checked=4,
            missing=1,
        )


class FailingOnceReconciliation:
    def __init__(self) -> None:
        self.call_count = 0

    async def execute(self) -> ReportArtifactReconciliationResult:
        self.call_count += 1

        if self.call_count == 1:
            raise RuntimeError("Object storage is unavailable.")

        return ReportArtifactReconciliationResult(
            checked=2,
            missing=0,
        )


async def test_periodic_reconciliation_runs_immediately_then_when_due() -> None:
    clock = MutableClock(NOW)
    reconciliation = CountingReconciliation()
    periodic = ReconcileReportArtifactsPeriodically(
        reconciliation=reconciliation,
        clock=clock,
        interval_seconds=900,
    )

    first = await periodic.execute()
    immediate_second = await periodic.execute()

    clock.current_time += timedelta(seconds=899)
    before_due = await periodic.execute()

    clock.current_time += timedelta(seconds=1)
    when_due = await periodic.execute()

    assert first == ReportArtifactReconciliationResult(
        checked=4,
        missing=1,
    )
    assert immediate_second is None
    assert before_due is None
    assert when_due == ReportArtifactReconciliationResult(
        checked=4,
        missing=1,
    )
    assert reconciliation.call_count == 2


async def test_failed_reconciliation_does_not_consume_interval() -> None:
    clock = MutableClock(NOW)
    reconciliation = FailingOnceReconciliation()
    periodic = ReconcileReportArtifactsPeriodically(
        reconciliation=reconciliation,
        clock=clock,
        interval_seconds=900,
    )

    with pytest.raises(
        RuntimeError,
        match="Object storage is unavailable",
    ):
        await periodic.execute()

    result = await periodic.execute()

    assert result == ReportArtifactReconciliationResult(
        checked=2,
        missing=0,
    )
    assert reconciliation.call_count == 2


def test_periodic_reconciliation_interval_must_be_positive() -> None:
    with pytest.raises(
        ValueError,
        match="Reconciliation interval must be positive",
    ):
        ReconcileReportArtifactsPeriodically(
            reconciliation=CountingReconciliation(),
            clock=MutableClock(NOW),
            interval_seconds=0,
        )



class EmptyReportRepository:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    async def claim_next(self, now: datetime) -> None:
        del now
        self._events.append("claim")
        return None


class RecordingPeriodicReconciliation:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    async def execute(self) -> None:
        self._events.append("reconcile")


class UnusedReportStorage:
    pass


async def test_processes_due_reconciliation_before_claiming_report() -> None:
    events: list[str] = []

    result = await ProcessNextReportJob(
        repository=EmptyReportRepository(events),
        storage=UnusedReportStorage(),
        clock=FakeClock(),
        reconcile_artifacts=RecordingPeriodicReconciliation(events),
    ).execute()

    assert result is None
    assert events == [
        "reconcile",
        "claim",
    ]
