import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from incrementality_api.infrastructure.database.models.analysis_runs import (
    AnalysisRunModel,
)
from incrementality_api.infrastructure.database.models.data_products import (
    ReportGenerationModel,
)
from incrementality_api.infrastructure.database.models.dataset_columns import (
    DatasetColumnModel,
)
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
from incrementality_api.infrastructure.database.repositories.data_products import (
    SqlAlchemyReportRepository,
)

CREATED_AT = datetime(2026, 7, 16, 16, 0, tzinfo=UTC)
STALE_STARTED_AT = datetime(2026, 7, 16, 16, 1, tzinfo=UTC)
CLAIMED_BEFORE = datetime(2026, 7, 16, 16, 10, tzinfo=UTC)
RECENT_STARTED_AT = datetime(2026, 7, 16, 16, 12, tzinfo=UTC)
RECOVERED_AT = datetime(2026, 7, 16, 16, 15, tzinfo=UTC)

RECOVERY_ERROR = "Report worker claim expired before completion."


async def seed_running_report(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    attempt_count: int = 1,
    max_attempts: int = 3,
    started_at: datetime = STALE_STARTED_AT,
) -> UUID:
    organization_id = uuid4()
    user_id = uuid4()
    workspace_id = uuid4()
    project_id = uuid4()
    dataset_id = uuid4()
    mapping_id = uuid4()
    analysis_run_id = uuid4()
    report_id = uuid4()

    async with session_factory() as session, session.begin():
        session.add_all(
            [
                OrganizationModel(
                    id=organization_id,
                    name="Report Recovery Organization",
                    slug=f"organization-{organization_id}",
                    created_at=CREATED_AT,
                    updated_at=CREATED_AT,
                ),
                UserModel(
                    id=user_id,
                    email=f"{user_id}@example.com",
                    display_name="Report Recovery User",
                    created_at=CREATED_AT,
                    updated_at=CREATED_AT,
                ),
            ]
        )
        await session.flush()

        session.add(
            WorkspaceModel(
                id=workspace_id,
                organization_id=organization_id,
                name="Report Recovery Workspace",
                slug=f"workspace-{workspace_id}",
                created_at=CREATED_AT,
                updated_at=CREATED_AT,
            )
        )
        await session.flush()

        session.add(
            ProjectModel(
                id=project_id,
                workspace_id=workspace_id,
                created_by_user_id=user_id,
                name="Report Recovery Project",
                slug=f"project-{project_id}",
                description=None,
                status="active",
                archived_at=None,
                created_at=CREATED_AT,
                updated_at=CREATED_AT,
            )
        )
        await session.flush()

        session.add(
            DatasetModel(
                id=dataset_id,
                workspace_id=workspace_id,
                project_id=project_id,
                created_by_user_id=user_id,
                source_filename="report-input.csv",
                storage_key=(
                    f"workspaces/{workspace_id}/projects/{project_id}/"
                    f"datasets/{dataset_id}/report-input.csv"
                ),
                media_type="text/csv",
                byte_size=4_096,
                checksum_sha256=dataset_id.hex * 2,
                status="ready",
                uploaded_at=CREATED_AT,
                validation_started_at=CREATED_AT,
                validation_completed_at=CREATED_AT,
                row_count=100,
                column_count=4,
                failure_reason=None,
                created_at=CREATED_AT,
                updated_at=CREATED_AT,
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
                    inferred_type="boolean",
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
                treatment_value="true",
                control_value="false",
                created_at=CREATED_AT,
                updated_at=CREATED_AT,
            )
        )
        await session.flush()

        session.add(
            AnalysisRunModel(
                id=analysis_run_id,
                workspace_id=workspace_id,
                project_id=project_id,
                dataset_id=dataset_id,
                semantic_mapping_id=mapping_id,
                semantic_mapping_version=1,
                created_by_user_id=user_id,
                estimator_type="difference_in_differences",
                estimator_version="did-v1",
                configuration_json='{"alpha":0.05}',
                status="queued",
                started_at=None,
                completed_at=None,
                failure_reason=None,
                cancellation_reason=None,
                created_at=CREATED_AT,
                updated_at=CREATED_AT,
            )
        )
        await session.flush()

        session.add(
            ReportGenerationModel(
                id=report_id,
                workspace_id=workspace_id,
                project_id=project_id,
                analysis_run_id=analysis_run_id,
                version=1,
                format="pdf",
                status="running",
                attempt_count=attempt_count,
                max_attempts=max_attempts,
                snapshot={},
                storage_key=None,
                failure_reason=None,
                started_at=started_at,
                completed_at=None,
                created_at=CREATED_AT,
                updated_at=started_at,
            )
        )

    return report_id


@pytest.mark.asyncio
async def test_requeues_stale_running_report_when_attempts_remain(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    report_id = await seed_running_report(
        tenancy_session_factory,
        attempt_count=1,
        max_attempts=3,
    )

    recovered = await SqlAlchemyReportRepository(
        tenancy_session_factory
    ).recover_stale(
        claimed_before=CLAIMED_BEFORE,
        recovered_at=RECOVERED_AT,
        error=RECOVERY_ERROR,
    )

    assert recovered is not None
    assert recovered.id == report_id
    assert recovered.status == "pending"
    assert recovered.failure_reason == RECOVERY_ERROR

    async with tenancy_session_factory() as session:
        persisted = await session.get(ReportGenerationModel, report_id)

    assert persisted is not None
    assert persisted.status == "pending"
    assert persisted.started_at is None
    assert persisted.completed_at is None
    assert persisted.failure_reason == RECOVERY_ERROR
    assert persisted.updated_at == RECOVERED_AT


@pytest.mark.asyncio
async def test_fails_stale_report_after_final_attempt(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    report_id = await seed_running_report(
        tenancy_session_factory,
        attempt_count=3,
        max_attempts=3,
    )

    recovered = await SqlAlchemyReportRepository(
        tenancy_session_factory
    ).recover_stale(
        claimed_before=CLAIMED_BEFORE,
        recovered_at=RECOVERED_AT,
        error=RECOVERY_ERROR,
    )

    assert recovered is not None
    assert recovered.id == report_id
    assert recovered.status == "failed"
    assert recovered.failure_reason == RECOVERY_ERROR

    async with tenancy_session_factory() as session:
        persisted = await session.get(ReportGenerationModel, report_id)

    assert persisted is not None
    assert persisted.status == "failed"
    assert persisted.started_at == STALE_STARTED_AT
    assert persisted.completed_at == RECOVERED_AT
    assert persisted.failure_reason == RECOVERY_ERROR
    assert persisted.updated_at == RECOVERED_AT


@pytest.mark.asyncio
async def test_recent_running_report_is_not_recovered(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    report_id = await seed_running_report(
        tenancy_session_factory,
        started_at=RECENT_STARTED_AT,
    )

    recovered = await SqlAlchemyReportRepository(
        tenancy_session_factory
    ).recover_stale(
        claimed_before=CLAIMED_BEFORE,
        recovered_at=RECOVERED_AT,
        error=RECOVERY_ERROR,
    )

    assert recovered is None

    async with tenancy_session_factory() as session:
        persisted = await session.get(ReportGenerationModel, report_id)

    assert persisted is not None
    assert persisted.status == "running"
    assert persisted.started_at == RECENT_STARTED_AT
    assert persisted.failure_reason is None
    assert persisted.completed_at is None


@pytest.mark.asyncio
async def test_concurrent_recovery_cannot_recover_same_report_twice(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    report_id = await seed_running_report(tenancy_session_factory)

    first_repository = SqlAlchemyReportRepository(tenancy_session_factory)
    second_repository = SqlAlchemyReportRepository(tenancy_session_factory)

    results = await asyncio.gather(
        first_repository.recover_stale(
            claimed_before=CLAIMED_BEFORE,
            recovered_at=RECOVERED_AT,
            error=RECOVERY_ERROR,
        ),
        second_repository.recover_stale(
            claimed_before=CLAIMED_BEFORE,
            recovered_at=RECOVERED_AT,
            error=RECOVERY_ERROR,
        ),
    )

    recovered = [result for result in results if result is not None]

    assert len(recovered) == 1
    assert recovered[0].id == report_id

    async with tenancy_session_factory() as session:
        persisted = await session.get(ReportGenerationModel, report_id)

    assert persisted is not None
    assert persisted.status == "pending"
    assert persisted.failure_reason == RECOVERY_ERROR
