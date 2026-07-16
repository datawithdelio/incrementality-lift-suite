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


class SqlAlchemyReportArtifactReconciliationRecorder:
    """Append completed report artifact reconciliations to PostgreSQL."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
    ) -> None:
        self._sessions = sessions

    async def record(
        self,
        record: ReportArtifactReconciliationRecord,
    ) -> None:
        async with self._sessions() as session, session.begin():
            session.add(
                ReportArtifactReconciliationRecordModel(
                    executed_at=record.executed_at,
                    checked=record.checked,
                    missing=record.missing,
                    corrupt=record.corrupt,
                    orphaned=record.orphaned,
                    orphaned_keys=list(record.orphaned_keys),
                )
            )
