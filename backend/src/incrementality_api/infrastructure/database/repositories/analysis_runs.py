from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from incrementality_api.application.analysis_runs.errors import (
    AnalysisRunPersistenceConflictError,
    AnalysisRunUnavailableError,
)
from incrementality_api.domain.analysis_runs.entities import (
    AnalysisRun,
)
from incrementality_api.domain.analysis_runs.status import (
    AnalysisEstimatorType,
    AnalysisRunStatus,
)
from incrementality_api.infrastructure.database.models.analysis_runs import (
    AnalysisRunModel,
)


def to_analysis_run_model(
    run: AnalysisRun,
) -> AnalysisRunModel:
    """Convert an analysis-run entity into persisted state."""

    return AnalysisRunModel(
        id=run.id,
        workspace_id=run.workspace_id,
        project_id=run.project_id,
        dataset_id=run.dataset_id,
        semantic_mapping_id=run.semantic_mapping_id,
        semantic_mapping_version=(run.semantic_mapping_version),
        created_by_user_id=run.created_by_user_id,
        estimator_type=run.estimator_type.value,
        estimator_version=run.estimator_version,
        configuration_json=run.configuration_json,
        status=run.status.value,
        started_at=run.started_at,
        completed_at=run.completed_at,
        failure_reason=run.failure_reason,
        cancellation_reason=run.cancellation_reason,
        created_at=run.created_at,
        updated_at=(run.completed_at or run.started_at or run.created_at),
    )


def to_analysis_run(
    model: AnalysisRunModel,
) -> AnalysisRun:
    """Reconstruct an analysis-run entity from persisted state."""

    return AnalysisRun(
        id=model.id,
        workspace_id=model.workspace_id,
        project_id=model.project_id,
        dataset_id=model.dataset_id,
        semantic_mapping_id=model.semantic_mapping_id,
        semantic_mapping_version=(model.semantic_mapping_version),
        created_by_user_id=model.created_by_user_id,
        estimator_type=AnalysisEstimatorType(model.estimator_type),
        estimator_version=model.estimator_version,
        configuration_json=model.configuration_json,
        status=AnalysisRunStatus(model.status),
        created_at=model.created_at,
        started_at=model.started_at,
        completed_at=model.completed_at,
        failure_reason=model.failure_reason,
        cancellation_reason=model.cancellation_reason,
    )


class SqlAlchemyAnalysisRunRepository:
    """Persist and retrieve tenant-scoped analysis runs."""

    def __init__(
        self,
        *,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def add(
        self,
        run: AnalysisRun,
    ) -> None:
        self._session.add(to_analysis_run_model(run))

        try:
            await self._session.flush()
        except IntegrityError as error:
            await self._session.rollback()

            raise AnalysisRunPersistenceConflictError(
                "Analysis run conflicts with existing records."
            ) from error

    async def get_by_scope(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        analysis_run_id: UUID,
    ) -> AnalysisRun | None:
        model = await self._session.scalar(
            select(AnalysisRunModel).where(
                AnalysisRunModel.id == analysis_run_id,
                AnalysisRunModel.workspace_id == workspace_id,
                AnalysisRunModel.project_id == project_id,
            )
        )

        if model is None:
            return None

        return to_analysis_run(model)

    async def update(
        self,
        run: AnalysisRun,
    ) -> None:
        model = await self._session.scalar(
            select(AnalysisRunModel)
            .where(
                AnalysisRunModel.id == run.id,
                AnalysisRunModel.workspace_id == run.workspace_id,
                AnalysisRunModel.project_id == run.project_id,
            )
            .with_for_update()
        )

        if model is None:
            raise AnalysisRunUnavailableError("Analysis run is unavailable.")

        model.dataset_id = run.dataset_id
        model.semantic_mapping_id = run.semantic_mapping_id
        model.semantic_mapping_version = run.semantic_mapping_version
        model.created_by_user_id = run.created_by_user_id
        model.estimator_type = run.estimator_type.value
        model.estimator_version = run.estimator_version
        model.configuration_json = run.configuration_json
        model.status = run.status.value
        model.started_at = run.started_at
        model.completed_at = run.completed_at
        model.failure_reason = run.failure_reason
        model.cancellation_reason = run.cancellation_reason
        model.updated_at = run.completed_at or run.started_at or run.created_at

        try:
            await self._session.flush()
        except IntegrityError as error:
            await self._session.rollback()

            raise AnalysisRunPersistenceConflictError(
                "Analysis run conflicts with existing records."
            ) from error
