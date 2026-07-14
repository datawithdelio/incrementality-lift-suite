from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from incrementality_api.application.analysis_execution.estimation import (
    PermanentEstimationError,
)
from incrementality_api.application.analysis_execution.input_loading import (
    AnalysisInputMetadata,
)
from incrementality_api.domain.analysis_runs.execution_jobs import AnalysisExecutionJob
from incrementality_api.infrastructure.database.repositories.analysis_runs import (
    SqlAlchemyAnalysisRunRepository,
)
from incrementality_api.infrastructure.database.repositories.dataset_columns import (
    SqlAlchemyDatasetColumnRepository,
)
from incrementality_api.infrastructure.database.repositories.dataset_semantic_mappings import (
    SqlAlchemyDatasetSemanticMappingRepository,
)
from incrementality_api.infrastructure.database.repositories.datasets import (
    SqlAlchemyDatasetRepository,
)


class SqlAlchemyAnalysisInputMetadataReader:
    """Load one exact analysis-input snapshot within complete tenant scope."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def load(self, job: AnalysisExecutionJob) -> AnalysisInputMetadata:
        async with self._session_factory() as session:
            runs = SqlAlchemyAnalysisRunRepository(session=session)
            datasets = SqlAlchemyDatasetRepository(session=session)
            mappings = SqlAlchemyDatasetSemanticMappingRepository(session=session)
            columns = SqlAlchemyDatasetColumnRepository(session=session)

            run = await runs.get_by_scope(
                workspace_id=job.workspace_id,
                project_id=job.project_id,
                analysis_run_id=job.analysis_run_id,
            )
            if run is None:
                raise PermanentEstimationError("Analysis run metadata is unavailable.")
            dataset = await datasets.get_by_scope_read(
                workspace_id=job.workspace_id,
                project_id=job.project_id,
                dataset_id=run.dataset_id,
            )
            if dataset is None:
                raise PermanentEstimationError("Analysis dataset metadata is unavailable.")
            mapping = await mappings.get_by_id_scope_and_version(
                workspace_id=job.workspace_id,
                project_id=job.project_id,
                dataset_id=run.dataset_id,
                mapping_id=run.semantic_mapping_id,
                version=run.semantic_mapping_version,
            )
            if mapping is None:
                raise PermanentEstimationError("Semantic mapping snapshot is unavailable.")
            column_profiles = await columns.list_by_scope(
                workspace_id=job.workspace_id,
                project_id=job.project_id,
                dataset_id=run.dataset_id,
            )
            return AnalysisInputMetadata(
                run=run,
                dataset=dataset,
                mapping=mapping,
                columns=column_profiles,
            )
