from incrementality_api.domain.jobs.entities import (
    DatasetValidationJob,
)
from incrementality_api.domain.jobs.status import (
    DatasetValidationJobStatus,
)
from incrementality_api.infrastructure.database.models.jobs import (
    DatasetValidationJobModel,
)


def to_dataset_validation_job_model(
    job: DatasetValidationJob,
) -> DatasetValidationJobModel:
    """Convert the domain job into its persistence model."""

    return DatasetValidationJobModel(
        id=job.id,
        workspace_id=job.workspace_id,
        project_id=job.project_id,
        dataset_id=job.dataset_id,
        status=job.status.value,
        attempt_count=job.attempt_count,
        max_attempts=job.max_attempts,
        available_at=job.available_at,
        claimed_at=job.claimed_at,
        completed_at=job.completed_at,
        last_error=job.last_error,
        created_at=job.created_at,
        updated_at=job.created_at,
    )


def to_dataset_validation_job_entity(
    model: DatasetValidationJobModel,
) -> DatasetValidationJob:
    """Convert a persistence model into the domain job."""

    return DatasetValidationJob(
        id=model.id,
        workspace_id=model.workspace_id,
        project_id=model.project_id,
        dataset_id=model.dataset_id,
        status=DatasetValidationJobStatus(
            model.status,
        ),
        attempt_count=model.attempt_count,
        max_attempts=model.max_attempts,
        available_at=model.available_at,
        created_at=model.created_at,
        claimed_at=model.claimed_at,
        completed_at=model.completed_at,
        last_error=model.last_error,
    )
