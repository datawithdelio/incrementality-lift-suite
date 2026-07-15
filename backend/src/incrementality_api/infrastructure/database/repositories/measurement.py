import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from incrementality_api.application.measurement.views import (
    AnalysisSummaryRecord,
    MeasurementFilters,
)
from incrementality_api.infrastructure.database.models.analysis_results import AnalysisResultModel
from incrementality_api.infrastructure.database.models.analysis_runs import AnalysisRunModel
from incrementality_api.infrastructure.database.models.projects import ProjectModel


class SqlAlchemyMeasurementRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def list(self, filters: MeasurementFilters) -> tuple[AnalysisSummaryRecord, ...]:
        statement = (
            select(AnalysisRunModel, AnalysisResultModel, ProjectModel.name)
            .join(ProjectModel, ProjectModel.id == AnalysisRunModel.project_id)
            .outerjoin(
                AnalysisResultModel, AnalysisResultModel.analysis_run_id == AnalysisRunModel.id
            )
            .where(AnalysisRunModel.workspace_id == filters.workspace_id)
            .order_by(AnalysisRunModel.created_at.desc())
        )
        if filters.project_id is not None:
            statement = statement.where(AnalysisRunModel.project_id == filters.project_id)
        if filters.estimator_type is not None:
            statement = statement.where(AnalysisRunModel.estimator_type == filters.estimator_type)
        if filters.status is not None:
            statement = statement.where(AnalysisRunModel.status == filters.status)
        if filters.date_from is not None:
            statement = statement.where(AnalysisRunModel.created_at >= filters.date_from)
        if filters.date_to is not None:
            statement = statement.where(AnalysisRunModel.created_at <= filters.date_to)
        async with self._session_factory() as session:
            rows = (await session.execute(statement)).all()
        return tuple(
            self._to_record(run, result, project_name) for run, result, project_name in rows
        )

    @staticmethod
    def _to_record(
        run: AnalysisRunModel, result: AnalysisResultModel | None, project_name: str
    ) -> AnalysisSummaryRecord:
        configuration = json.loads(run.configuration_json)
        return AnalysisSummaryRecord(
            run_id=run.id,
            workspace_id=run.workspace_id,
            project_id=run.project_id,
            project_name=project_name,
            status=run.status,
            estimator_type=run.estimator_type,
            created_at=run.created_at,
            effect=None if result is None else result.effect,
            confidence_low=None if result is None else result.confidence_interval_low,
            confidence_high=None if result is None else result.confidence_interval_high,
            incremental_revenue=None if result is None else result.incremental_revenue,
            incremental_conversions=None if result is None else result.incremental_conversions,
            relative_lift=None if result is None else result.relative_lift,
            diagnostics={} if result is None else result.diagnostics,
            configuration=configuration,
            failure_reason=run.failure_reason,
        )
