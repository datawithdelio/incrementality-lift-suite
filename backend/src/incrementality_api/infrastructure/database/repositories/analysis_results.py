import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from incrementality_api.application.analysis_execution.errors import (
    AnalysisResultPersistenceConflictError,
)
from incrementality_api.domain.analysis_results.entities import AnalysisResult
from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType
from incrementality_api.infrastructure.database.models.analysis_results import (
    AnalysisResultModel,
)


def to_analysis_result_model(result: AnalysisResult) -> AnalysisResultModel:
    return AnalysisResultModel(
        id=result.id,
        workspace_id=result.workspace_id,
        project_id=result.project_id,
        analysis_run_id=result.analysis_run_id,
        dataset_id=result.dataset_id,
        semantic_mapping_id=result.semantic_mapping_id,
        semantic_mapping_version=result.semantic_mapping_version,
        estimator_type=result.estimator_type.value,
        estimator_version=result.estimator_version,
        library_name=result.library_name,
        library_version=result.library_version,
        effect=result.effect,
        standard_error=result.standard_error,
        p_value=result.p_value,
        confidence_interval_low=result.confidence_interval_low,
        confidence_interval_high=result.confidence_interval_high,
        sample_size=result.sample_size,
        diagnostics=json.loads(result.diagnostics_json),
        incremental_outcome=result.incremental_outcome,
        relative_lift=result.relative_lift,
        incremental_revenue=result.incremental_revenue,
        incremental_conversions=result.incremental_conversions,
        created_at=result.created_at,
        updated_at=result.created_at,
    )


def to_analysis_result(model: AnalysisResultModel) -> AnalysisResult:
    return AnalysisResult(
        id=model.id,
        workspace_id=model.workspace_id,
        project_id=model.project_id,
        analysis_run_id=model.analysis_run_id,
        dataset_id=model.dataset_id,
        semantic_mapping_id=model.semantic_mapping_id,
        semantic_mapping_version=model.semantic_mapping_version,
        estimator_type=AnalysisEstimatorType(model.estimator_type),
        estimator_version=model.estimator_version,
        library_name=model.library_name,
        library_version=model.library_version,
        effect=model.effect,
        standard_error=model.standard_error,
        p_value=model.p_value,
        confidence_interval_low=model.confidence_interval_low,
        confidence_interval_high=model.confidence_interval_high,
        sample_size=model.sample_size,
        diagnostics_json=json.dumps(
            model.diagnostics, sort_keys=True, separators=(",", ":"), allow_nan=False
        ),
        incremental_outcome=model.incremental_outcome,
        relative_lift=model.relative_lift,
        incremental_revenue=model.incremental_revenue,
        incremental_conversions=model.incremental_conversions,
        created_at=model.created_at,
    )


class SqlAlchemyAnalysisResultRepository:
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def add(self, result: AnalysisResult) -> None:
        self._session.add(to_analysis_result_model(result))
        try:
            await self._session.flush()
        except IntegrityError as error:
            await self._session.rollback()
            raise AnalysisResultPersistenceConflictError(
                "A canonical result already exists or conflicts with the analysis run."
            ) from error

    async def get_by_analysis_run_id(self, analysis_run_id: UUID) -> AnalysisResult | None:
        model = await self._session.scalar(
            select(AnalysisResultModel).where(
                AnalysisResultModel.analysis_run_id == analysis_run_id
            )
        )
        return None if model is None else to_analysis_result(model)

    async def get_by_analysis_run_scope(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        analysis_run_id: UUID,
    ) -> AnalysisResult | None:
        model = await self._session.scalar(
            select(AnalysisResultModel).where(
                AnalysisResultModel.workspace_id == workspace_id,
                AnalysisResultModel.project_id == project_id,
                AnalysisResultModel.analysis_run_id == analysis_run_id,
            )
        )
        return None if model is None else to_analysis_result(model)
