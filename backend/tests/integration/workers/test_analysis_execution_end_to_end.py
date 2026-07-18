import asyncio
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from hashlib import sha256
from typing import cast
from uuid import UUID, uuid4

import pytest
from mypy_boto3_s3 import S3Client
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from incrementality_api.application.analysis_execution.claim_next_execution_job import (
    ClaimNextAnalysisExecutionJob,
)
from incrementality_api.application.analysis_execution.estimation import AnalysisEstimatorRegistry
from incrementality_api.application.analysis_execution.input_loading import (
    AnalysisInputMetadataValidator,
    AnalysisPeriodRowFilter,
    CsvAnalysisRowLoader,
    DifferenceInDifferencesConfigurationParser,
    DifferenceInDifferencesInputBuilder,
    ProductionAnalysisInputLoader,
)
from incrementality_api.application.analysis_execution.retry_policy import (
    FixedDelayAnalysisExecutionRetryPolicy,
)
from incrementality_api.application.analysis_execution.settle_execution import (
    MarkAnalysisExecutionFailed,
    PersistAnalysisExecutionSuccess,
    RecordAnalysisExecutionFailure,
)
from incrementality_api.domain.analysis_runs.analysis_period_snapshot import (
    AnalysisPeriodSnapshot,
)
from incrementality_api.domain.analysis_runs.analysis_selection_snapshot import (
    AnalysisSelectionSnapshot,
)
from incrementality_api.domain.analysis_runs.estimand_snapshot import EstimandSnapshot
from incrementality_api.domain.analysis_runs.semantic_mapping_snapshot import (
    SemanticMappingSnapshot,
)
from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType
from incrementality_api.domain.analysis_runs.treatment_control_snapshot import (
    TreatmentControlSnapshot,
)
from incrementality_api.infrastructure.analysis_execution.selection import (
    AnalysisSelectionRowExecutor,
)
from incrementality_api.infrastructure.analysis_execution.treatment_control import (
    TreatmentControlRowExecutor,
)
from incrementality_api.infrastructure.database.analysis_input_metadata import (
    SqlAlchemyAnalysisInputMetadataReader,
)
from incrementality_api.infrastructure.database.models.analysis_execution_jobs import (
    AnalysisExecutionJobModel,
)
from incrementality_api.infrastructure.database.models.analysis_results import AnalysisResultModel
from incrementality_api.infrastructure.database.models.analysis_runs import AnalysisRunModel
from incrementality_api.infrastructure.database.models.dataset_columns import DatasetColumnModel
from incrementality_api.infrastructure.database.models.dataset_semantic_mappings import (
    DatasetSemanticMappingModel,
)
from incrementality_api.infrastructure.database.models.datasets import DatasetModel
from incrementality_api.infrastructure.database.models.projects import ProjectModel
from incrementality_api.infrastructure.database.models.tenancy import (
    OrganizationModel,
    UserModel,
    WorkspaceModel,
)
from incrementality_api.infrastructure.database.unit_of_work.analysis_execution_jobs import (
    SqlAlchemyAnalysisExecutionJobUnitOfWork,
)
from incrementality_api.infrastructure.estimation.difference_in_differences import (
    StatsmodelsDifferenceInDifferencesEstimator,
)
from incrementality_api.infrastructure.estimation.runtime_versions import (
    StatisticalRuntimeVersionProvider,
)
from incrementality_api.infrastructure.storage.s3_clients import create_s3_compatible_client
from incrementality_api.infrastructure.storage.s3_dataset_objects import S3DatasetObjectStorage
from incrementality_api.workers.handlers.analysis_execution import RunNextAnalysisExecutionJob

RUN_S3_INTEGRATION = os.getenv("RUN_S3_INTEGRATION") == "1"
S3_ENDPOINT_URL = os.getenv("S3_INTEGRATION_ENDPOINT_URL", "http://localhost:5001")
NOW = datetime(2026, 7, 21, 14, 0, tzinfo=UTC)


class FixedClock:
    def now(self) -> datetime:
        return NOW


def build_panel_csv() -> bytes:
    rows = ["Date,Market,Treated,Revenue"]
    for unit_index in range(8):
        treated = unit_index >= 4
        for period in range(4):
            outcome = 10.0 + unit_index + period
            if treated and period >= 2:
                outcome += 5.0
            rows.append(
                f"2026-01-0{period + 1},unit-{unit_index},{'yes' if treated else 'no'},{outcome}"
            )
    return ("\n".join(rows) + "\n").encode()


async def one_chunk(content: bytes) -> AsyncIterator[bytes]:
    yield content


async def seed_did_execution(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    storage_key: str,
    content: bytes,
) -> tuple[UUID, UUID]:
    organization_id = uuid4()
    user_id = uuid4()
    workspace_id = uuid4()
    project_id = uuid4()
    dataset_id = uuid4()
    mapping_id = uuid4()
    run_id = uuid4()
    job_id = uuid4()

    estimator_type = AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES
    configuration_json = (
        '{"analysis_start_date":"2026-01-01",'
        '"analysis_end_date":"2026-01-04",'
        '"intervention_date":"2026-01-03"}'
    )

    semantic_mapping_snapshot = SemanticMappingSnapshot.create(
        time_column="date",
        unit_column="market",
        treatment_column="treated",
        outcome_column="revenue",
        spend_column=None,
        covariate_columns=(),
        treatment_value="yes",
        control_value="no",
    )

    analysis_period_snapshot = AnalysisPeriodSnapshot.from_configuration_json(
        estimator_type,
        configuration_json,
    )

    analysis_selection_snapshot = (
        AnalysisSelectionSnapshot.from_configuration_json(
            estimator_type=estimator_type,
            serialized=configuration_json,
            semantic_mapping=semantic_mapping_snapshot,
        )
    )

    treatment_control_snapshot = (
        TreatmentControlSnapshot.from_configuration_json(
            estimator_type=estimator_type,
            serialized=configuration_json,
            semantic_mapping=semantic_mapping_snapshot,
            analysis_period=analysis_period_snapshot,
            analysis_selection=analysis_selection_snapshot,
        )
    )

    estimand_snapshot = EstimandSnapshot.from_validated_run_configuration(
        estimator_type=estimator_type,
        semantic_mapping=semantic_mapping_snapshot,
        analysis_period=analysis_period_snapshot,
        analysis_selection=analysis_selection_snapshot,
        treatment_control=treatment_control_snapshot,
        serialized=configuration_json,
    )

    statistical_library_versions = (
        StatisticalRuntimeVersionProvider().for_estimator(
            estimator_type,
        )
    )

    async with session_factory() as session, session.begin():
        session.add_all(
            [
                OrganizationModel(
                    id=organization_id,
                    name="E2E Analysis Organization",
                    slug=f"e2e-org-{organization_id}",
                    created_at=NOW,
                    updated_at=NOW,
                ),
                UserModel(
                    id=user_id,
                    email=f"{user_id}@example.com",
                    display_name="E2E Analyst",
                    created_at=NOW,
                    updated_at=NOW,
                ),
            ]
        )
        await session.flush()
        session.add(
            WorkspaceModel(
                id=workspace_id,
                organization_id=organization_id,
                name="E2E Workspace",
                slug=f"e2e-workspace-{workspace_id}",
                created_at=NOW,
                updated_at=NOW,
            )
        )
        await session.flush()
        session.add(
            ProjectModel(
                id=project_id,
                workspace_id=workspace_id,
                created_by_user_id=user_id,
                name="E2E Project",
                slug=f"e2e-project-{project_id}",
                description=None,
                status="active",
                archived_at=None,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        await session.flush()
        session.add(
            DatasetModel(
                id=dataset_id,
                workspace_id=workspace_id,
                project_id=project_id,
                created_by_user_id=user_id,
                source_filename="did-panel.csv",
                storage_key=storage_key,
                media_type="text/csv",
                byte_size=len(content),
                checksum_sha256=sha256(content).hexdigest(),
                status="ready",
                uploaded_at=NOW,
                validation_started_at=NOW,
                validation_completed_at=NOW,
                row_count=32,
                column_count=4,
                failure_reason=None,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        await session.flush()
        session.add_all(
            [
                DatasetColumnModel(
                    dataset_id=dataset_id,
                    ordinal_position=1,
                    source_name="Date",
                    normalized_name="date",
                    inferred_type="date",
                    nullable=False,
                    missing_count=0,
                ),
                DatasetColumnModel(
                    dataset_id=dataset_id,
                    ordinal_position=2,
                    source_name="Market",
                    normalized_name="market",
                    inferred_type="string",
                    nullable=False,
                    missing_count=0,
                ),
                DatasetColumnModel(
                    dataset_id=dataset_id,
                    ordinal_position=3,
                    source_name="Treated",
                    normalized_name="treated",
                    inferred_type="string",
                    nullable=False,
                    missing_count=0,
                ),
                DatasetColumnModel(
                    dataset_id=dataset_id,
                    ordinal_position=4,
                    source_name="Revenue",
                    normalized_name="revenue",
                    inferred_type="float",
                    nullable=False,
                    missing_count=0,
                ),
            ]
        )
        await session.flush()
        session.add(
            DatasetSemanticMappingModel(
                id=mapping_id,
                dataset_id=dataset_id,
                created_by_user_id=user_id,
                version=1,
                time_column="date",
                unit_column="market",
                treatment_column="treated",
                outcome_column="revenue",
                spend_column=None,
                treatment_value="yes",
                control_value="no",
                created_at=NOW,
                updated_at=NOW,
            )
        )
        await session.flush()
        session.add(
            AnalysisRunModel(
                id=run_id,
                workspace_id=workspace_id,
                project_id=project_id,
                dataset_id=dataset_id,
                dataset_checksum_sha256=sha256(content).hexdigest(),
                dataset_byte_size=len(content),
                semantic_mapping_id=mapping_id,
                semantic_mapping_version=1,
                semantic_mapping_snapshot_json=(
                    semantic_mapping_snapshot.canonical_json
                ),
                analysis_period_snapshot_json=(
                    analysis_period_snapshot.canonical_json
                ),
                analysis_selection_snapshot_json=(
                    analysis_selection_snapshot.canonical_json
                ),
                treatment_control_snapshot_json=(
                    treatment_control_snapshot.canonical_json
                ),
                estimand_snapshot_json=(
                    estimand_snapshot.canonical_json
                ),
                created_by_user_id=user_id,
                estimator_type=estimator_type.value,
                estimator_version="did-v1",
                application_version="0.1.0",
                source_revision="a" * 40,
                statistical_library_versions_json=(
                    statistical_library_versions.canonical_json
                ),
                random_seed=1_729,
                configuration_json=configuration_json,
                status="queued",
                started_at=None,
                completed_at=None,
                failure_reason=None,
                cancellation_reason=None,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        await session.flush()
        session.add(
            AnalysisExecutionJobModel(
                id=job_id,
                workspace_id=workspace_id,
                project_id=project_id,
                analysis_run_id=run_id,
                status="pending",
                attempt_count=0,
                max_attempts=3,
                available_at=NOW,
                claimed_at=None,
                completed_at=None,
                last_error=None,
                created_at=NOW,
                updated_at=NOW,
            )
        )
    return job_id, run_id


@pytest.mark.skipif(not RUN_S3_INTEGRATION, reason="S3 integration tests are disabled.")
@pytest.mark.asyncio
async def test_real_postgresql_s3_did_execution_workflow(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    client = cast(
        S3Client,
        create_s3_compatible_client(
            endpoint_url=S3_ENDPOINT_URL,
            access_key="incrementality",
            secret_key="incrementality-secret",
            region="us-east-1",
        ),
    )
    bucket = f"incrementality-analysis-{uuid4().hex}"
    storage_key = f"datasets/{uuid4()}/did-panel.csv"
    content = build_panel_csv()
    await asyncio.to_thread(client.create_bucket, Bucket=bucket)
    storage = S3DatasetObjectStorage(client=client, bucket_name=bucket)
    try:
        await storage.write(
            storage_key=storage_key,
            media_type="text/csv",
            chunks=one_chunk(content),
        )
        job_id, run_id = await seed_did_execution(
            tenancy_session_factory,
            storage_key=storage_key,
            content=content,
        )
        clock = FixedClock()
        processor = RunNextAnalysisExecutionJob(
            claim_next=ClaimNextAnalysisExecutionJob(
                unit_of_work=SqlAlchemyAnalysisExecutionJobUnitOfWork(tenancy_session_factory),
                clock=clock,
            ),
            input_loader=ProductionAnalysisInputLoader(
                metadata_reader=SqlAlchemyAnalysisInputMetadataReader(tenancy_session_factory),
                object_storage=storage,
                metadata_validator=AnalysisInputMetadataValidator(),
                row_loader=CsvAnalysisRowLoader(),
                configuration_parser=DifferenceInDifferencesConfigurationParser(),
                input_builder=DifferenceInDifferencesInputBuilder(),
                period_filter=AnalysisPeriodRowFilter(),
                selection_executor=AnalysisSelectionRowExecutor(),
                treatment_control_executor=TreatmentControlRowExecutor(),
            ),
            estimator_selector=AnalysisEstimatorRegistry(
                {
                    AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES: (
                        StatsmodelsDifferenceInDifferencesEstimator()
                    )
                }
            ),
            statistical_runtime_versions=StatisticalRuntimeVersionProvider(),
            persist_success=PersistAnalysisExecutionSuccess(
                unit_of_work=SqlAlchemyAnalysisExecutionJobUnitOfWork(tenancy_session_factory),
                clock=clock,
            ),
            record_retryable_failure=RecordAnalysisExecutionFailure(
                unit_of_work=SqlAlchemyAnalysisExecutionJobUnitOfWork(tenancy_session_factory),
                clock=clock,
                retry_policy=FixedDelayAnalysisExecutionRetryPolicy(retry_delay_seconds=30),
            ),
            mark_failed=MarkAnalysisExecutionFailed(
                unit_of_work=SqlAlchemyAnalysisExecutionJobUnitOfWork(tenancy_session_factory),
                clock=clock,
            ),
        )

        settled = await processor.execute()

        async with tenancy_session_factory() as session:
            job = await session.get(AnalysisExecutionJobModel, job_id)
            run = await session.get(AnalysisRunModel, run_id)
            result = await session.scalar(
                select(AnalysisResultModel).where(AnalysisResultModel.analysis_run_id == run_id)
            )
        assert settled is not None and settled.status.value == "succeeded"
        assert job is not None and job.status == "succeeded"
        assert run is not None and run.status == "succeeded"
        assert result is not None
        assert result.effect == pytest.approx(5.0)
        assert result.sample_size == 32
        assert result.library_name == "statsmodels"
    finally:
        await asyncio.to_thread(client.delete_object, Bucket=bucket, Key=storage_key)
        await asyncio.to_thread(client.delete_bucket, Bucket=bucket)
