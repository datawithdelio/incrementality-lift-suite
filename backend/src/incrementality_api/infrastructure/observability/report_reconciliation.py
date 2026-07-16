import logging

from incrementality_api.application.data_products.reconciliation import (
    ReportArtifactReconciliationRecord,
)

logger = logging.getLogger(__name__)


class LoggingReportArtifactReconciliationRecorder:
    """Emit completed report-artifact reconciliation results."""

    async def record(
        self,
        record: ReportArtifactReconciliationRecord,
    ) -> None:
        context = {
            "executed_at": record.executed_at.isoformat(),
            "report_artifacts_checked": record.checked,
            "report_artifacts_missing": record.missing,
            "report_artifacts_orphaned": record.orphaned,
            "orphaned_storage_keys": record.orphaned_keys,
        }

        if record.missing > 0 or record.orphaned > 0:
            logger.warning(
                "Report artifact reconciliation found inconsistencies.",
                extra=context,
            )
            return

        logger.info(
            "Report artifact reconciliation completed.",
            extra=context,
        )
