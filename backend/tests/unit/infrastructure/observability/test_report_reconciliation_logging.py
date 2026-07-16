import logging
from datetime import UTC, datetime
from typing import Any, cast

import pytest

from incrementality_api.application.data_products.reconciliation import (
    ReportArtifactReconciliationRecord,
)
from incrementality_api.infrastructure.observability.report_reconciliation import (
    LoggingReportArtifactReconciliationRecorder,
)

EXECUTED_AT = datetime(
    2026,
    7,
    16,
    18,
    30,
    tzinfo=UTC,
)

LOGGER_NAME = "incrementality_api.infrastructure.observability.report_reconciliation"


@pytest.mark.asyncio
async def test_logs_warning_when_reconciliation_finds_inconsistencies(
    caplog: pytest.LogCaptureFixture,
) -> None:
    recorder = LoggingReportArtifactReconciliationRecorder()

    with caplog.at_level(
        logging.INFO,
        logger=LOGGER_NAME,
    ):
        await recorder.record(
            ReportArtifactReconciliationRecord(
                executed_at=EXECUTED_AT,
                checked=5,
                missing=1,
                orphaned=2,
                orphaned_keys=(
                    "reports/workspace/run/v2.pdf",
                    "reports/workspace/run/v3.csv",
                ),
            )
        )

    assert len(caplog.records) == 1

    record = cast(Any, caplog.records[0])

    assert record.levelno == logging.WARNING
    assert record.getMessage() == ("Report artifact reconciliation found inconsistencies.")
    assert record.executed_at == EXECUTED_AT.isoformat()
    assert record.report_artifacts_checked == 5
    assert record.report_artifacts_missing == 1
    assert record.report_artifacts_orphaned == 2
    assert record.orphaned_storage_keys == (
        "reports/workspace/run/v2.pdf",
        "reports/workspace/run/v3.csv",
    )


@pytest.mark.asyncio
async def test_logs_info_when_reconciliation_is_clean(
    caplog: pytest.LogCaptureFixture,
) -> None:
    recorder = LoggingReportArtifactReconciliationRecorder()

    with caplog.at_level(
        logging.INFO,
        logger=LOGGER_NAME,
    ):
        await recorder.record(
            ReportArtifactReconciliationRecord(
                executed_at=EXECUTED_AT,
                checked=4,
                missing=0,
                orphaned=0,
                orphaned_keys=(),
            )
        )

    assert len(caplog.records) == 1

    record = cast(Any, caplog.records[0])

    assert record.levelno == logging.INFO
    assert record.getMessage() == ("Report artifact reconciliation completed.")
    assert record.report_artifacts_checked == 4
    assert record.report_artifacts_missing == 0
    assert record.report_artifacts_orphaned == 0
    assert record.orphaned_storage_keys == ()
