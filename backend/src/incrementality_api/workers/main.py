import asyncio
from datetime import UTC, datetime

from incrementality_api.application.datasets.begin_validation import (
    BeginDatasetValidation,
)
from incrementality_api.application.datasets.complete_validation import (
    MarkDatasetFailed,
    MarkDatasetReady,
)
from incrementality_api.application.datasets.validate_dataset import (
    ValidateDataset,
)
from incrementality_api.application.jobs.claim_next_validation_job import (
    ClaimNextDatasetValidationJob,
)
from incrementality_api.application.jobs.recover_stale_validation_job import (
    RecoverStaleDatasetValidationJob,
)
from incrementality_api.application.jobs.settle_validation_job import (
    MarkDatasetValidationJobSucceeded,
    RecordDatasetValidationJobFailure,
)
from incrementality_api.core.config import get_settings
from incrementality_api.core.logging import configure_logging
from incrementality_api.infrastructure.database.session import (
    get_engine,
    get_session_factory,
)
from incrementality_api.infrastructure.database.unit_of_work.datasets import (
    SqlAlchemyDatasetUnitOfWork,
)
from incrementality_api.infrastructure.database.unit_of_work.jobs import (
    SqlAlchemyDatasetValidationJobUnitOfWork,
)
from incrementality_api.infrastructure.storage.s3_clients import (
    create_s3_compatible_client,
)
from incrementality_api.infrastructure.storage.s3_dataset_objects import (
    S3DatasetObjectStorage,
)
from incrementality_api.infrastructure.validation.csv_datasets import (
    CsvDatasetContentValidator,
)
from incrementality_api.workers.handlers.dataset_validation import (
    RunNextDatasetValidationJob,
)
from incrementality_api.workers.loop import (
    DatasetValidationWorker,
)


class SystemWorkerClock:
    """Provide timezone-aware UTC timestamps to worker actions."""

    def now(self) -> datetime:
        return datetime.now(UTC)


def build_dataset_validation_worker() -> DatasetValidationWorker:
    """Construct the production dataset-validation worker."""

    settings = get_settings()
    session_factory = get_session_factory()
    clock = SystemWorkerClock()

    s3_client = create_s3_compatible_client(
        endpoint_url=settings.s3_endpoint_url,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        region=settings.s3_region,
    )

    object_storage = S3DatasetObjectStorage(
        client=s3_client,
        bucket_name=settings.s3_bucket,
        spool_max_memory_bytes=(settings.dataset_validation_spool_max_memory_bytes),
    )

    content_validator = CsvDatasetContentValidator(
        spool_max_memory_bytes=(settings.dataset_validation_spool_max_memory_bytes),
    )

    begin_validation = BeginDatasetValidation(
        unit_of_work=SqlAlchemyDatasetUnitOfWork(
            session_factory=session_factory,
        ),
        clock=clock,
    )

    mark_ready = MarkDatasetReady(
        unit_of_work=SqlAlchemyDatasetUnitOfWork(
            session_factory=session_factory,
        ),
        clock=clock,
    )

    mark_failed = MarkDatasetFailed(
        unit_of_work=SqlAlchemyDatasetUnitOfWork(
            session_factory=session_factory,
        ),
        clock=clock,
    )

    validate_dataset = ValidateDataset(
        begin_validation=begin_validation,
        object_storage=object_storage,
        content_validator=content_validator,
        mark_ready=mark_ready,
        mark_failed=mark_failed,
        read_chunk_size=(settings.dataset_validation_read_chunk_bytes),
    )

    recover_stale = RecoverStaleDatasetValidationJob(
        unit_of_work=(
            SqlAlchemyDatasetValidationJobUnitOfWork(
                session_factory=session_factory,
            )
        ),
        clock=clock,
        claim_timeout_seconds=(settings.dataset_validation_job_claim_timeout_seconds),
    )

    claim_next = ClaimNextDatasetValidationJob(
        unit_of_work=(
            SqlAlchemyDatasetValidationJobUnitOfWork(
                session_factory=session_factory,
            )
        ),
        clock=clock,
    )

    mark_succeeded = MarkDatasetValidationJobSucceeded(
        unit_of_work=(
            SqlAlchemyDatasetValidationJobUnitOfWork(
                session_factory=session_factory,
            )
        ),
        clock=clock,
    )

    record_failure = RecordDatasetValidationJobFailure(
        unit_of_work=(
            SqlAlchemyDatasetValidationJobUnitOfWork(
                session_factory=session_factory,
            )
        ),
        clock=clock,
        retry_delay_seconds=(settings.dataset_validation_job_retry_delay_seconds),
    )

    process_next = RunNextDatasetValidationJob(
        recover_stale=recover_stale,
        claim_next=claim_next,
        validate_dataset=validate_dataset,
        mark_succeeded=mark_succeeded,
        record_failure=record_failure,
    )

    return DatasetValidationWorker(
        process_next=process_next,
        sleep=asyncio.sleep,
        poll_interval_seconds=(settings.dataset_validation_worker_poll_interval_seconds),
        error_retry_seconds=(settings.dataset_validation_worker_error_retry_seconds),
    )


async def main() -> None:
    """Run the production worker until shutdown."""

    configure_logging()

    worker = build_dataset_validation_worker()

    try:
        await worker.run_forever()
    finally:
        await get_engine().dispose()


def run() -> None:
    """Synchronous console-script entry point."""

    asyncio.run(main())


if __name__ == "__main__":
    run()
