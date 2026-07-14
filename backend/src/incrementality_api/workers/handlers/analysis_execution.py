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


class ClaimNextExecution(Protocol):
    async def execute(self) -> AnalysisExecutionJob | None:
        """Claim the next available execution job."""


class AnalysisInputLoader(Protocol):
    async def load(self, job: AnalysisExecutionJob) -> AnalysisEstimatorInput:
        """Load and construct estimator-ready analysis input."""


class AnalysisResultSink(Protocol):
    async def save(
        self,
        *,
        job: AnalysisExecutionJob,
        result: AnalysisEstimationResult,
    ) -> None:
        """Persist estimation output before successful settlement."""


class MarkExecutionSucceeded(Protocol):
    async def execute(self, job_id: UUID) -> AnalysisExecutionJob:
        """Settle a successful execution."""


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
        result_sink: AnalysisResultSink,
        mark_succeeded: MarkExecutionSucceeded,
        record_retryable_failure: RecordRetryableExecutionFailure,
        mark_failed: MarkExecutionFailed,
    ) -> None:
        self._claim_next = claim_next
        self._input_loader = input_loader
        self._estimator_selector = estimator_selector
        self._result_sink = result_sink
        self._mark_succeeded = mark_succeeded
        self._record_retryable_failure = record_retryable_failure
        self._mark_failed = mark_failed

    async def execute(self) -> AnalysisExecutionJob | None:
        job = await self._claim_next.execute()
        if job is None:
            return None

        try:
            estimator_input = await self._input_loader.load(job)
            estimator = self._estimator_selector.select(estimator_input.estimator_type)
            result = estimator.estimate(estimator_input.payload)
            await self._result_sink.save(job=job, result=result)
        except RetryableEstimationError as error:
            return await self._record_retryable_failure.execute(
                job_id=job.id,
                error=_error_message(error),
            )
        except PermanentEstimationError as error:
            return await self._mark_failed.execute(
                job_id=job.id,
                error=_error_message(error),
            )

        return await self._mark_succeeded.execute(job.id)


def _error_message(error: Exception) -> str:
    return str(error).strip() or type(error).__name__
