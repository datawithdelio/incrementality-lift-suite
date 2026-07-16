from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from incrementality_api.application.data_products.reconciliation import (
    ReportArtifactReconciliationRecord,
)
from incrementality_api.infrastructure.database.models.data_products import (
    ReportArtifactReconciliationRecordModel,
)
from incrementality_api.infrastructure.database.repositories.report_reconciliation import (
    SqlAlchemyReportArtifactReconciliationRecorder,
)

EXECUTED_AT = datetime(
    2026,
    7,
    16,
    19,
    30,
    tzinfo=UTC,
)


@pytest.mark.asyncio
async def test_persists_completed_report_artifact_reconciliation(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with tenancy_session_factory() as session, session.begin():
        await session.execute(
            delete(
                ReportArtifactReconciliationRecordModel
            )
        )

    recorder = SqlAlchemyReportArtifactReconciliationRecorder(
        tenancy_session_factory
    )

    await recorder.record(
        ReportArtifactReconciliationRecord(
            executed_at=EXECUTED_AT,
            checked=8,
            missing=1,
            orphaned=2,
            orphaned_keys=(
                "reports/workspace/run/v2.pdf",
                "reports/workspace/run/v3.csv",
            ),
        )
    )

    async with tenancy_session_factory() as session:
        records = (
            await session.scalars(
                select(
                    ReportArtifactReconciliationRecordModel
                )
            )
        ).all()

    assert len(records) == 1

    persisted = records[0]

    assert persisted.id is not None
    assert persisted.executed_at == EXECUTED_AT
    assert persisted.checked == 8
    assert persisted.missing == 1
    assert persisted.orphaned == 2
    assert persisted.orphaned_keys == [
        "reports/workspace/run/v2.pdf",
        "reports/workspace/run/v3.csv",
    ]
