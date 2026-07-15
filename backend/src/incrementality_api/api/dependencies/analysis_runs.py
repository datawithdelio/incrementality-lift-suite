from datetime import UTC, datetime

from incrementality_api.application.analysis_results.get_analysis_result import GetAnalysisResult
from incrementality_api.application.analysis_runs.manage_analysis_runs import (
    GetAnalysisRun,
    QueueAnalysisRun,
)
from incrementality_api.infrastructure.database.repositories.data_products import (
    SqlAlchemyAnalysisQualityGate,
)
from incrementality_api.infrastructure.database.session import (
    get_session_factory,
)
from incrementality_api.infrastructure.database.unit_of_work.analysis_runs import (
    SqlAlchemyAnalysisRunUnitOfWork,
)


class SystemAnalysisRunClock:
    """Provide timezone-aware UTC timestamps."""

    def now(self) -> datetime:
        return datetime.now(UTC)


def get_queue_analysis_run_service() -> QueueAnalysisRun:
    """Construct the production analysis-run queue use case."""

    sessions = get_session_factory()
    return QueueAnalysisRun(
        unit_of_work=SqlAlchemyAnalysisRunUnitOfWork(
            session_factory=sessions,
        ),
        clock=SystemAnalysisRunClock(),
        quality_gate=SqlAlchemyAnalysisQualityGate(sessions),
    )


def get_analysis_run_service() -> GetAnalysisRun:
    """Construct the production analysis-run read use case."""

    return GetAnalysisRun(
        unit_of_work=SqlAlchemyAnalysisRunUnitOfWork(
            session_factory=get_session_factory(),
        ),
    )


def get_analysis_result_service() -> GetAnalysisResult:
    """Construct the tenant-scoped result read use case."""
    return GetAnalysisResult(
        unit_of_work=SqlAlchemyAnalysisRunUnitOfWork(
            session_factory=get_session_factory(),
        )
    )
