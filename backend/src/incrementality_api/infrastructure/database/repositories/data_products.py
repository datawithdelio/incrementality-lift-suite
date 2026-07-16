from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from incrementality_api.application.data_products.quality import DataQualityResult
from incrementality_api.application.data_products.report_jobs import ReportClock, ReportJob
from incrementality_api.infrastructure.database.models.analysis_results import AnalysisResultModel
from incrementality_api.infrastructure.database.models.analysis_runs import AnalysisRunModel
from incrementality_api.infrastructure.database.models.data_products import (
    DataQualityAssessmentModel,
    ReportGenerationModel,
)
from incrementality_api.infrastructure.database.models.datasets import DatasetModel
from incrementality_api.infrastructure.database.models.projects import ProjectModel


def _job(model: ReportGenerationModel) -> ReportJob:
    return ReportJob(
        model.id,
        model.workspace_id,
        model.project_id,
        model.analysis_run_id,
        model.version,
        model.format,
        model.status,
        model.attempt_count,
        model.max_attempts,
        model.snapshot,
        model.storage_key,
        model.failure_reason,
        model.created_at,
        model.artifact_byte_size,
        model.artifact_checksum_sha256,
    )


class SqlAlchemyQualityAssessmentWriter:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], clock: ReportClock
    ) -> None:
        self._sessions, self._clock = session_factory, clock

    async def save(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        dataset_id: UUID,
        mapping_version: int | None,
        estimator_type: str,
        result: DataQualityResult,
    ) -> None:
        now = self._clock.now()
        async with self._sessions() as session:
            session.add(
                DataQualityAssessmentModel(
                    workspace_id=workspace_id,
                    project_id=project_id,
                    dataset_id=dataset_id,
                    mapping_version=mapping_version,
                    estimator_type=estimator_type,
                    score=result.score,
                    ready=result.ready,
                    findings=[asdict(item) for item in result.findings],
                    created_at=now,
                    updated_at=now,
                )
            )
            await session.commit()


class SqlAlchemyDatasetVersionReader:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = session_factory

    async def list(self, *, workspace_id: UUID, project_id: UUID) -> tuple[DatasetModel, ...]:
        async with self._sessions() as session:
            models = (
                await session.scalars(
                    select(DatasetModel)
                    .where(
                        DatasetModel.workspace_id == workspace_id,
                        DatasetModel.project_id == project_id,
                        DatasetModel.status == "ready",
                    )
                    .order_by(DatasetModel.created_at.desc())
                )
            ).all()
            return tuple(models)


class SqlAlchemyAnalysisQualityGate:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = session_factory

    async def allows(
        self, *, workspace_id: UUID, project_id: UUID, dataset_id: UUID, estimator_type: str
    ) -> bool:
        async with self._sessions() as session:
            assessment = await session.scalar(
                select(DataQualityAssessmentModel)
                .where(
                    DataQualityAssessmentModel.workspace_id == workspace_id,
                    DataQualityAssessmentModel.project_id == project_id,
                    DataQualityAssessmentModel.dataset_id == dataset_id,
                    DataQualityAssessmentModel.estimator_type == estimator_type,
                )
                .order_by(DataQualityAssessmentModel.created_at.desc())
                .limit(1)
            )
            return assessment is None or assessment.ready


class SqlAlchemyReportRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = session_factory

    async def queue(
        self, *, workspace_id: UUID, project_id: UUID, run_id: UUID, format: str, now: datetime
    ) -> ReportJob:
        async with self._sessions() as session:
            row = (
                await session.execute(
                    select(AnalysisRunModel, AnalysisResultModel, DatasetModel, ProjectModel.name)
                    .join(
                        AnalysisResultModel,
                        AnalysisResultModel.analysis_run_id == AnalysisRunModel.id,
                    )
                    .join(DatasetModel, DatasetModel.id == AnalysisRunModel.dataset_id)
                    .join(ProjectModel, ProjectModel.id == AnalysisRunModel.project_id)
                    .where(
                        AnalysisRunModel.id == run_id,
                        AnalysisRunModel.workspace_id == workspace_id,
                        AnalysisRunModel.project_id == project_id,
                        AnalysisRunModel.status == "succeeded",
                    )
                )
            ).one_or_none()
            if row is None:
                raise LookupError("Completed analysis result is unavailable.")
            run, result, dataset, project_name = row
            latest_quality = await session.scalar(
                select(DataQualityAssessmentModel)
                .where(DataQualityAssessmentModel.dataset_id == dataset.id)
                .order_by(DataQualityAssessmentModel.created_at.desc())
                .limit(1)
            )
            version = (
                int(
                    await session.scalar(
                        select(func.coalesce(func.max(ReportGenerationModel.version), 0)).where(
                            ReportGenerationModel.analysis_run_id == run_id,
                            ReportGenerationModel.format == format,
                        )
                    )
                )
                + 1
            )
            diagnostics = result.diagnostics
            snapshot: dict[str, object] = {
                "title": f"{project_name} analysis report",
                "generated_at": now.isoformat(),
                "analysis_run_id": str(run.id),
                "estimator": run.estimator_type,
                "estimator_version": run.estimator_version,
                "dataset_id": str(dataset.id),
                "dataset_checksum": dataset.checksum_sha256,
                "mapping_version": run.semantic_mapping_version,
                "configuration": __import__("json").loads(run.configuration_json),
                "estimate": result.effect,
                "confidence_low": result.confidence_interval_low,
                "confidence_high": result.confidence_interval_high,
                "diagnostics": diagnostics,
                "warnings": tuple(str(item) for item in diagnostics.get("warnings", [])),
                "business_impact": {
                    "incremental_revenue": result.incremental_revenue,
                    "incremental_conversions": result.incremental_conversions,
                    "relative_lift": result.relative_lift,
                },
                "quality_summary": {"score": latest_quality.score, "ready": latest_quality.ready}
                if latest_quality
                else {"score": None, "ready": None},
                "limitations": tuple(str(item) for item in diagnostics.get("limitations", [])),
            }
            model = ReportGenerationModel(
                workspace_id=workspace_id,
                project_id=project_id,
                analysis_run_id=run_id,
                version=version,
                format=format,
                status="pending",
                attempt_count=0,
                max_attempts=3,
                snapshot=snapshot,
                storage_key=None,
                failure_reason=None,
                started_at=None,
                completed_at=None,
                created_at=now,
                updated_at=now,
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return _job(model)

    async def list(
        self, *, workspace_id: UUID, project_id: UUID, run_id: UUID
    ) -> tuple[ReportJob, ...]:
        async with self._sessions() as session:
            models = (
                await session.scalars(
                    select(ReportGenerationModel)
                    .where(
                        ReportGenerationModel.workspace_id == workspace_id,
                        ReportGenerationModel.project_id == project_id,
                        ReportGenerationModel.analysis_run_id == run_id,
                    )
                    .order_by(ReportGenerationModel.created_at.desc())
                )
            ).all()
            return tuple(_job(model) for model in models)

    async def get(
        self, *, workspace_id: UUID, project_id: UUID, report_id: UUID
    ) -> ReportJob | None:
        async with self._sessions() as session:
            model = await session.scalar(
                select(ReportGenerationModel).where(
                    ReportGenerationModel.id == report_id,
                    ReportGenerationModel.workspace_id == workspace_id,
                    ReportGenerationModel.project_id == project_id,
                )
            )
            return None if model is None else _job(model)

    async def list_storage_keys(self) -> frozenset[str]:
        async with self._sessions() as session:
            storage_keys = (
                await session.scalars(
                    select(ReportGenerationModel.storage_key).where(
                        ReportGenerationModel.storage_key.is_not(None)
                    )
                )
            ).all()

            return frozenset(
                storage_key
                for storage_key in storage_keys
                if storage_key is not None
            )

    async def list_succeeded(self) -> tuple[ReportJob, ...]:
        async with self._sessions() as session:
            models = (
                await session.scalars(
                    select(ReportGenerationModel)
                    .where(ReportGenerationModel.status == "succeeded")
                    .order_by(ReportGenerationModel.created_at)
                )
            ).all()

            return tuple(_job(model) for model in models)

    async def mark_artifact_missing(
        self,
        *,
        job_id: UUID,
        error: str,
        now: datetime,
    ) -> None:
        async with self._sessions() as session, session.begin():
            model = await session.get(
                ReportGenerationModel,
                job_id,
                with_for_update=True,
            )

            if model is None or model.status != "succeeded":
                return

            model.status = "failed"
            model.failure_reason = error
            model.completed_at = now
            model.updated_at = now

    async def claim_next(self, now: datetime) -> ReportJob | None:
        async with self._sessions() as session, session.begin():
            model = await session.scalar(
                select(ReportGenerationModel)
                .where(ReportGenerationModel.status == "pending")
                .order_by(ReportGenerationModel.created_at)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            if model is None:
                return None
            model.status, model.attempt_count, model.started_at, model.updated_at = (
                "running",
                model.attempt_count + 1,
                now,
                now,
            )
        return _job(model)

    async def recover_stale(
        self,
        *,
        claimed_before: datetime,
        recovered_at: datetime,
        error: str,
    ) -> ReportJob | None:
        async with self._sessions() as session, session.begin():
            model = await session.scalar(
                select(ReportGenerationModel)
                .where(
                    ReportGenerationModel.status == "running",
                    ReportGenerationModel.started_at.is_not(None),
                    ReportGenerationModel.started_at < claimed_before,
                )
                .order_by(ReportGenerationModel.started_at)
                .with_for_update(skip_locked=True)
                .limit(1)
            )

            if model is None:
                return None

            final_attempt = model.attempt_count >= model.max_attempts

            model.status = "failed" if final_attempt else "pending"
            model.failure_reason = error
            model.completed_at = recovered_at if final_attempt else None
            model.updated_at = recovered_at

            if not final_attempt:
                model.started_at = None

        return _job(model)

    async def succeed(
        self,
        job_id: UUID,
        storage_key: str,
        now: datetime,
        *,
        byte_size: int | None = None,
        checksum_sha256: str | None = None,
    ) -> ReportJob:
        async with self._sessions() as session:
            model = await session.get(ReportGenerationModel, job_id, with_for_update=True)
            if model is None:
                raise LookupError("Report job is unavailable.")
            (
                model.status,
                model.storage_key,
                model.artifact_byte_size,
                model.artifact_checksum_sha256,
                model.completed_at,
                model.updated_at,
            ) = (
                "succeeded",
                storage_key,
                byte_size,
                checksum_sha256,
                now,
                now,
            )
            await session.commit()
            return _job(model)

    async def fail(self, job_id: UUID, error: str, now: datetime) -> ReportJob:
        async with self._sessions() as session:
            model = await session.get(ReportGenerationModel, job_id, with_for_update=True)
            if model is None:
                raise LookupError("Report job is unavailable.")
            final = model.attempt_count >= model.max_attempts
            model.status, model.failure_reason, model.completed_at, model.updated_at = (
                ("failed" if final else "pending"),
                error,
                (now if final else None),
                now,
            )
            await session.commit()
            return _job(model)
