from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from incrementality_api.application.data_products.reconciliation import (
    MISSING_REPORT_ARTIFACT_ERROR,
    CompositeReportArtifactReconciliationRecorder,
    ReconcileReportArtifacts,
    ReconcileReportArtifactsPeriodically,
    ReportArtifactReconciliationRecord,
    ReportArtifactReconciliationResult,
)
from incrementality_api.application.data_products.report_jobs import (
    ProcessNextReportJob,
    ReportJob,
)
from incrementality_api.application.datasets.ports import (
    DatasetObjectWriteResult,
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

    async def list_storage_keys(self) -> frozenset[str]:
        return frozenset(
            job.storage_key
            for job in self._jobs
            if job.storage_key is not None
        )

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

    async def list_keys(
        self,
        *,
        prefix: str,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                key
                for key in self._existing_keys
                if key.startswith(prefix)
            )
        )


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

    async def claim_next(
        self,
        now: datetime,
    ) -> ReportJob | None:
        del now
        self._events.append("claim")
        return None

    async def succeed(
        self,
        job_id: UUID,
        storage_key: str,
        now: datetime,
    ) -> ReportJob:
        del job_id, storage_key, now
        raise AssertionError(
            "succeed must not be called when the queue is empty."
        )

    async def fail(
        self,
        job_id: UUID,
        error: str,
        now: datetime,
    ) -> ReportJob:
        del job_id, error, now
        raise AssertionError(
            "fail must not be called when the queue is empty."
        )


class RecordingPeriodicReconciliation:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    async def execute(self) -> None:
        self._events.append("reconcile")


class UnusedReportStorage:
    async def write(
        self,
        *,
        storage_key: str,
        media_type: str,
        chunks: AsyncIterator[bytes],
    ) -> DatasetObjectWriteResult:
        del storage_key, media_type, chunks
        raise AssertionError(
            "write must not be called when the queue is empty."
        )

    def read(
        self,
        *,
        storage_key: str,
        chunk_size: int = 1024 * 1024,
    ) -> AsyncIterator[bytes]:
        del storage_key, chunk_size
        raise AssertionError(
            "read must not be called when the queue is empty."
        )

    async def delete(
        self,
        *,
        storage_key: str,
    ) -> None:
        del storage_key
        raise AssertionError(
            "delete must not be called when the queue is empty."
        )


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



class FakeOrphanReportRepository:
    def __init__(
        self,
        referenced_storage_keys: set[str],
    ) -> None:
        self._referenced_storage_keys = referenced_storage_keys
        self.missing_artifacts: list[tuple[UUID, str, datetime]] = []

    async def list_succeeded(self) -> tuple[ReportJob, ...]:
        return ()

    async def list_storage_keys(self) -> frozenset[str]:
        return frozenset(self._referenced_storage_keys)

    async def mark_artifact_missing(
        self,
        *,
        job_id: UUID,
        error: str,
        now: datetime,
    ) -> None:
        self.missing_artifacts.append(
            (
                job_id,
                error,
                now,
            )
        )


class FakeOrphanReportStorage:
    def __init__(
        self,
        stored_keys: tuple[str, ...],
    ) -> None:
        self._stored_keys = stored_keys
        self.listed_prefixes: list[str] = []
        self.deleted_keys: list[str] = []

    async def exists(
        self,
        *,
        storage_key: str,
    ) -> bool:
        del storage_key
        raise AssertionError(
            "No succeeded report artifacts should be checked."
        )

    async def list_keys(
        self,
        *,
        prefix: str,
    ) -> tuple[str, ...]:
        self.listed_prefixes.append(prefix)
        return self._stored_keys

    async def delete(
        self,
        *,
        storage_key: str,
    ) -> None:
        self.deleted_keys.append(storage_key)


async def test_reports_orphaned_storage_objects_without_deleting_them() -> None:
    referenced_key = (
        "reports/workspace/run/v1.pdf"
    )
    orphaned_key = (
        "reports/workspace/run/v2.pdf"
    )

    repository = FakeOrphanReportRepository(
        {
            referenced_key,
        }
    )
    storage = FakeOrphanReportStorage(
        (
            referenced_key,
            orphaned_key,
        )
    )

    result = await ReconcileReportArtifacts(
        repository=repository,
        storage=storage,
        clock=FakeClock(),
    ).execute()

    assert storage.listed_prefixes == [
        "reports/",
    ]
    assert result.checked == 0
    assert result.missing == 0
    assert result.orphaned == 1
    assert result.orphaned_keys == (
        orphaned_key,
    )
    assert storage.deleted_keys == []
    assert repository.missing_artifacts == []



class RecordingReconciliationAudit:
    def __init__(self) -> None:
        self.records: list[ReportArtifactReconciliationRecord] = []

    async def record(
        self,
        record: ReportArtifactReconciliationRecord,
    ) -> None:
        self.records.append(record)


async def test_records_completed_reconciliation_for_audit() -> None:
    existing_key = "reports/workspace/run/v1.pdf"
    missing_key = "reports/workspace/run/v2.pdf"
    orphaned_key = "reports/workspace/run/v3.pdf"

    existing = succeeded_report(existing_key)
    missing = succeeded_report(missing_key)

    repository = FakeReportRepository(
        (
            existing,
            missing,
        )
    )
    storage = FakeReportStorage(
        {
            existing_key,
            orphaned_key,
        }
    )
    audit = RecordingReconciliationAudit()

    result = await ReconcileReportArtifacts(
        repository=repository,
        storage=storage,
        clock=FakeClock(),
        recorder=audit,
    ).execute()

    assert result.checked == 2
    assert result.missing == 1
    assert result.orphaned == 1

    assert len(audit.records) == 1

    record = audit.records[0]

    assert record.executed_at == NOW
    assert record.checked == 2
    assert record.missing == 1
    assert record.orphaned == 1
    assert record.orphaned_keys == (
        orphaned_key,
    )



async def test_composite_recorder_forwards_record_to_every_recorder() -> None:
    first = RecordingReconciliationAudit()
    second = RecordingReconciliationAudit()

    record = ReportArtifactReconciliationRecord(
        executed_at=NOW,
        checked=6,
        missing=1,
        orphaned=2,
        orphaned_keys=(
            "reports/workspace/run/v2.pdf",
            "reports/workspace/run/v3.csv",
        ),
    )

    await CompositeReportArtifactReconciliationRecorder(
        (
            first,
            second,
        )
    ).record(record)

    assert first.records == [record]
    assert second.records == [record]
