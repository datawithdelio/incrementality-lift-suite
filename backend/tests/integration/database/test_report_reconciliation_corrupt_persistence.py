from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from incrementality_api.application.data_products.reconciliation import (
    ReportArtifactReconciliationRecord,
)
from incrementality_api.infrastructure.database.models.data_products import (
    ReportArtifactReconciliationRecordModel,
)
from incrementality_api.infrastructure.database.repositories.report_reconciliation import (
    SqlAlchemyReportArtifactReconciliationRecorder,
)

EXECUTED_AT = datetime.now(UTC)


@pytest.mark.asyncio
async def test_persists_corrupt_report_artifact_count(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    record = ReportArtifactReconciliationRecord(
        executed_at=EXECUTED_AT,
        checked=4,
        missing=1,
        corrupt=2,
        orphaned=1,
        orphaned_keys=("reports/orphaned.pdf",),
    )

    await SqlAlchemyReportArtifactReconciliationRecorder(tenancy_session_factory).record(record)

    async with tenancy_session_factory() as session:
        persisted = await session.scalar(
            select(ReportArtifactReconciliationRecordModel).where(
                ReportArtifactReconciliationRecordModel.executed_at == EXECUTED_AT
            )
        )

    assert persisted is not None
    assert persisted.checked == 4
    assert persisted.missing == 1
    assert persisted.corrupt == 2
    assert persisted.orphaned == 1
    assert persisted.orphaned_keys == [
        "reports/orphaned.pdf",
    ]
