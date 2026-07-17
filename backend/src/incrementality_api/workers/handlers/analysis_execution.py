import asyncio
import logging
from typing import Protocol
from uuid import UUID

from incrementality_api.application.analysis_execution.estimation import (
    AnalysisEstimationResult,
    AnalysisEstimatorInput,
    AnalysisEstimatorSelector,
    PermanentEstimationError,
    RetryableEstimationError,
)
from incrementality_api.domain.analysis_runs.execution_jobs import AnalysisExecutionJob
from incrementality_api.domain.analysis_runs.statistical_library_versions import (
    StatisticalLibraryVersions,
)
from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType

logger = logging.getLogger(__name__)


class ClaimNextExecution(Protocol):
    async def execute(self) -> AnalysisExecutionJob | None:
        """Claim the next available execution job."""


class AnalysisInputLoader(Protocol):
    async def load(self, job: AnalysisExecutionJob) -> AnalysisEstimatorInput:
        """Load and construct estimator-ready analysis input."""


class StatisticalRuntimeVersions(Protocol):
    def for_estimator(
        self,
        estimator_type: AnalysisEstimatorType,
    ) -> StatisticalLibraryVersions: ...


class PersistExecutionSuccess(Protocol):
    async def execute(
        self, *, job_id: UUID, result: AnalysisEstimationResult
    ) -> AnalysisExecutionJob:
        """Persist the result and settle success in one transaction."""


class RecordRetryableExecutionFailure(Protocol):
    async def execute(self, *, job_id: UUID, error: str) -> AnalysisExecutionJob:
        """Schedule a transient execution failure for retry."""


class MarkExecutionFailed(Protocol):
    async def execute(self, *, job_id: UUID, error: str) -> AnalysisExecutionJob:
        """Settle a permanent execution failure."""


class RunNextAnalysisExecutionJob:
    """Orchestrate one analysis job without depending on estimator libraries."""

    def __init__(
        self,
        *,
        claim_next: ClaimNextExecution,
        input_loader: AnalysisInputLoader,
        estimator_selector: AnalysisEstimatorSelector,
        statistical_runtime_versions: StatisticalRuntimeVersions,
        persist_success: PersistExecutionSuccess,
        record_retryable_failure: RecordRetryableExecutionFailure,
        mark_failed: MarkExecutionFailed,
    ) -> None:
        self._claim_next = claim_next
        self._input_loader = input_loader
        self._estimator_selector = estimator_selector
        self._statistical_runtime_versions = statistical_runtime_versions
        self._persist_success = persist_success
        self._record_retryable_failure = record_retryable_failure
        self._mark_failed = mark_failed

    async def execute(self) -> AnalysisExecutionJob | None:
        job = await self._claim_next.execute()
        if job is None:
            return None

        log_context = {
            "job_id": str(job.id),
            "analysis_run_id": str(job.analysis_run_id),
        }
        logger.info("Claimed analysis execution job.", extra=log_context)

        try:
            estimator_input = await self._input_loader.load(job)
            queued_versions = estimator_input.statistical_library_versions
            if queued_versions is None:
                raise PermanentEstimationError(
                    "Queued statistical-library version snapshot is unavailable."
                )
            worker_versions = self._statistical_runtime_versions.for_estimator(
                estimator_input.estimator_type
            )
            if worker_versions != queued_versions:
                raise PermanentEstimationError(
                    "Worker statistical-library versions do not match the queued snapshot."
                )
            estimator = self._estimator_selector.select(estimator_input.estimator_type)
            result = await asyncio.to_thread(
                estimator.estimate,
                estimator_input.payload,
                random_seed=estimator_input.random_seed,
            )
        except RetryableEstimationError as error:
            logger.warning(
                "Analysis execution failed with retryable error.",
                extra=log_context,
            )
            return await self._record_retryable_failure.execute(
                job_id=job.id,
                error=_error_message(error),
            )
        except PermanentEstimationError as error:
            logger.warning(
                "Analysis execution failed permanently.",
                extra=log_context,
            )
            return await self._mark_failed.execute(
                job_id=job.id,
                error=_error_message(error),
            )

        settled = await self._persist_success.execute(job_id=job.id, result=result)
        logger.info("Analysis execution succeeded.", extra=log_context)
        return settled


def _error_message(error: Exception) -> str:
    return str(error).strip() or type(error).__name__
