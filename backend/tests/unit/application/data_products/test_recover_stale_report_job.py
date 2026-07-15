from datetime import UTC, datetime, timedelta
from typing import NoReturn
from uuid import UUID

import pytest

from incrementality_api.application.data_products.report_jobs import (
    ProcessNextReportJob,
    RecoverStaleReportJob,
    ReportJob,
)

CURRENT_TIME = datetime(2026, 7, 14, 21, 0, tzinfo=UTC)
CLAIM_TIMEOUT_SECONDS = 300
EXPECTED_CUTOFF = CURRENT_TIME - timedelta(seconds=CLAIM_TIMEOUT_SECONDS)
RECOVERY_ERROR = "Report worker claim expired before completion."


class FixedClock:
    def now(self) -> datetime:
        return CURRENT_TIME


class FakeStaleReportRepository:
    def __init__(self) -> None:
        self.recovery_calls: list[tuple[datetime, datetime, str]] = []

    async def recover_stale(
        self,
        *,
        claimed_before: datetime,
        recovered_at: datetime,
        error: str,
    ) -> ReportJob | None:
        self.recovery_calls.append((claimed_before, recovered_at, error))
        return None


class FakeRecoveryAction:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    async def execute(self) -> ReportJob | None:
        self._events.append("recover")
        return None


class FakeClaimRepository:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    async def claim_next(self, now: datetime) -> ReportJob | None:
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
        raise AssertionError("No report should be settled.")

    async def fail(
        self,
        job_id: UUID,
        error: str,
        now: datetime,
    ) -> ReportJob:
        del job_id, error, now
        raise AssertionError("No report should be settled.")


class UnusedStorage:
    async def write(self, **kwargs: object) -> NoReturn:
        del kwargs
        raise AssertionError("Storage should not be used when no report is claimed.")


async def test_recover_stale_report_uses_claim_timeout_cutoff() -> None:
    repository = FakeStaleReportRepository()

    result = await RecoverStaleReportJob(
        repository=repository,
        clock=FixedClock(),
        claim_timeout_seconds=CLAIM_TIMEOUT_SECONDS,
    ).execute()

    assert result is None
    assert repository.recovery_calls == [
        (
            EXPECTED_CUTOFF,
            CURRENT_TIME,
            RECOVERY_ERROR,
        )
    ]


def test_report_claim_timeout_must_be_positive() -> None:
    with pytest.raises(ValueError, match="Claim timeout must be positive"):
        RecoverStaleReportJob(
            repository=FakeStaleReportRepository(),
            clock=FixedClock(),
            claim_timeout_seconds=0,
        )


async def test_report_processing_recovers_stale_work_before_claiming() -> None:
    events: list[str] = []

    result = await ProcessNextReportJob(
        repository=FakeClaimRepository(events),
        storage=UnusedStorage(),  # type: ignore[arg-type]
        clock=FixedClock(),
        recover_stale=FakeRecoveryAction(events),
    ).execute()

    assert result is None
    assert events == ["recover", "claim"]
