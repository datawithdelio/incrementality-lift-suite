from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from incrementality_api.domain.datasets.entities import Dataset
from incrementality_api.domain.projects.status import (
    ProjectStatus,
)
from incrementality_api.infrastructure.database.models.dataset_columns import (
    DatasetColumnModel,
)
from incrementality_api.infrastructure.database.models.dataset_semantic_mappings import (
    DatasetMappingCovariateModel,
    DatasetSemanticMappingModel,
)
from incrementality_api.infrastructure.database.models.datasets import (
    DatasetModel,
)
from incrementality_api.infrastructure.database.models.projects import (
    ProjectModel,
)
from incrementality_api.infrastructure.database.models.tenancy import (
    OrganizationModel,
    UserModel,
    WorkspaceModel,
)
from incrementality_api.infrastructure.database.repositories.datasets import (
    to_dataset_model,
)

FIXED_NOW = datetime(
    2026,
    7,
    14,
    22,
    0,
    tzinfo=UTC,
)


@dataclass(frozen=True, slots=True)
class SeededSemanticMappingSchema:
    user_id: UUID
    first_dataset_id: UUID
    second_dataset_id: UUID


def build_ready_dataset(
    *,
    workspace_id: UUID,
    project_id: UUID,
    user_id: UUID,
    filename: str,
    checksum: str,
    column_count: int,
) -> Dataset:
    dataset = Dataset.register(
        workspace_id=workspace_id,
        project_id=project_id,
        created_by_user_id=user_id,
        source_filename=filename,
        storage_key=(
            f"workspaces/{workspace_id}/projects/{project_id}/datasets/{checksum}/{filename}"
        ),
        media_type="text/csv",
        byte_size=4_096,
        checksum_sha256=checksum,
    )

    uploaded_at = datetime.now(UTC) + timedelta(
        seconds=1,
    )

    return (
        dataset.mark_uploaded(
            uploaded_at=uploaded_at,
        )
        .begin_validation(
            validation_started_at=(uploaded_at + timedelta(seconds=1)),
        )
        .mark_ready(
            validation_completed_at=(uploaded_at + timedelta(seconds=2)),
            row_count=100,
            column_count=column_count,
        )
    )


def build_column_models(
    *,
    dataset_id: UUID,
    include_foreign_columns: bool,
) -> list[DatasetColumnModel]:
    specifications = [
        (
            1,
            "Date",
            "date",
            "date",
        ),
        (
            2,
            "Market",
            "market",
            "string",
        ),
        (
            3,
            "Treated",
            "treated",
            "boolean",
        ),
        (
            4,
            "Revenue",
            "revenue",
            "float",
        ),
        (
            5,
            "Spend",
            "spend",
            "integer",
        ),
        (
            6,
            "Promotion",
            "promotion",
            "string",
        ),
        (
            7,
            "Seasonality",
            "seasonality",
            "float",
        ),
    ]

    if include_foreign_columns:
        specifications.extend(
            [
                (
                    8,
                    "Foreign Revenue",
                    "foreign_revenue",
                    "float",
                ),
                (
                    9,
                    "Foreign Covariate",
                    "foreign_covariate",
                    "string",
                ),
            ]
        )

    return [
        DatasetColumnModel(
            dataset_id=dataset_id,
            ordinal_position=ordinal_position,
            source_name=source_name,
            normalized_name=normalized_name,
            inferred_type=inferred_type,
            nullable=False,
            missing_count=0,
            created_at=FIXED_NOW,
            updated_at=FIXED_NOW,
        )
        for (
            ordinal_position,
            source_name,
            normalized_name,
            inferred_type,
        ) in specifications
    ]


async def seed_semantic_mapping_schema(
    session_factory: async_sessionmaker[AsyncSession],
) -> SeededSemanticMappingSchema:
    organization_id = uuid4()
    workspace_id = uuid4()
    project_id = uuid4()
    user_id = uuid4()

    first_dataset = build_ready_dataset(
        workspace_id=workspace_id,
        project_id=project_id,
        user_id=user_id,
        filename="first-dataset.csv",
        checksum="a" * 64,
        column_count=7,
    )

    second_dataset = build_ready_dataset(
        workspace_id=workspace_id,
        project_id=project_id,
        user_id=user_id,
        filename="second-dataset.csv",
        checksum="b" * 64,
        column_count=9,
    )

    async with (
        session_factory() as session,
        session.begin(),
    ):
        session.add_all(
            [
                OrganizationModel(
                    id=organization_id,
                    name="Semantic Mapping Organization",
                    slug=f"organization-{organization_id}",
                    created_at=FIXED_NOW,
                    updated_at=FIXED_NOW,
                ),
                UserModel(
                    id=user_id,
                    email=f"{user_id}@example.com",
                    display_name="Semantic Mapping User",
                    created_at=FIXED_NOW,
                    updated_at=FIXED_NOW,
                ),
            ]
        )

        await session.flush()

        session.add(
            WorkspaceModel(
                id=workspace_id,
                organization_id=organization_id,
                name="Semantic Mapping Workspace",
                slug=f"workspace-{workspace_id}",
                created_at=FIXED_NOW,
                updated_at=FIXED_NOW,
            )
        )

        await session.flush()

        session.add(
            ProjectModel(
                id=project_id,
                workspace_id=workspace_id,
                created_by_user_id=user_id,
                name="Semantic Mapping Project",
                slug=f"project-{project_id}",
                description=None,
                status=ProjectStatus.ACTIVE.value,
                archived_at=None,
                created_at=FIXED_NOW,
                updated_at=FIXED_NOW,
            )
        )

        await session.flush()

        session.add_all(
            [
                to_dataset_model(first_dataset),
                to_dataset_model(second_dataset),
            ]
        )

        await session.flush()

        session.add_all(
            [
                *build_column_models(
                    dataset_id=first_dataset.id,
                    include_foreign_columns=False,
                ),
                *build_column_models(
                    dataset_id=second_dataset.id,
                    include_foreign_columns=True,
                ),
            ]
        )

    return SeededSemanticMappingSchema(
        user_id=user_id,
        first_dataset_id=first_dataset.id,
        second_dataset_id=second_dataset.id,
    )


def build_mapping(
    seed: SeededSemanticMappingSchema,
    *,
    mapping_id: UUID | None = None,
    dataset_id: UUID | None = None,
    version: int = 1,
    time_column: str = "date",
    unit_column: str = "market",
    treatment_column: str = "treated",
    outcome_column: str = "revenue",
    spend_column: str | None = "spend",
    treatment_value: str = "true",
    control_value: str = "false",
) -> DatasetSemanticMappingModel:
    return DatasetSemanticMappingModel(
        id=mapping_id or uuid4(),
        dataset_id=(dataset_id or seed.first_dataset_id),
        created_by_user_id=seed.user_id,
        version=version,
        time_column=time_column,
        unit_column=unit_column,
        treatment_column=treatment_column,
        outcome_column=outcome_column,
        spend_column=spend_column,
        treatment_value=treatment_value,
        control_value=control_value,
        created_at=FIXED_NOW,
        updated_at=FIXED_NOW,
    )


def build_covariate(
    *,
    mapping_id: UUID,
    dataset_id: UUID,
    ordinal_position: int,
    normalized_column_name: str,
) -> DatasetMappingCovariateModel:
    return DatasetMappingCovariateModel(
        id=uuid4(),
        mapping_id=mapping_id,
        dataset_id=dataset_id,
        ordinal_position=ordinal_position,
        normalized_column_name=(normalized_column_name),
        created_at=FIXED_NOW,
        updated_at=FIXED_NOW,
    )


def assert_constraint_name(
    error: pytest.ExceptionInfo[IntegrityError],
    expected_name: str,
) -> None:
    assert expected_name in str(error.value.orig)


async def persist_mapping(
    session_factory: async_sessionmaker[AsyncSession],
    mapping: DatasetSemanticMappingModel,
) -> None:
    async with (
        session_factory() as session,
        session.begin(),
    ):
        session.add(mapping)


@pytest.mark.asyncio
async def test_persists_mapping_and_reads_ordered_covariates(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    seed = await seed_semantic_mapping_schema(
        tenancy_session_factory,
    )

    mapping = build_mapping(seed)

    async with (
        tenancy_session_factory() as session,
        session.begin(),
    ):
        session.add(mapping)
        await session.flush()

        session.add_all(
            [
                build_covariate(
                    mapping_id=mapping.id,
                    dataset_id=seed.first_dataset_id,
                    ordinal_position=2,
                    normalized_column_name="seasonality",
                ),
                build_covariate(
                    mapping_id=mapping.id,
                    dataset_id=seed.first_dataset_id,
                    ordinal_position=1,
                    normalized_column_name="promotion",
                ),
            ]
        )

    async with tenancy_session_factory() as session:
        persisted_mapping = await session.scalar(
            select(DatasetSemanticMappingModel).where(
                DatasetSemanticMappingModel.id == mapping.id,
            )
        )

        covariates = (
            await session.scalars(
                select(DatasetMappingCovariateModel)
                .where(
                    DatasetMappingCovariateModel.mapping_id == mapping.id,
                )
                .order_by(DatasetMappingCovariateModel.ordinal_position)
            )
        ).all()

    assert persisted_mapping is not None
    assert persisted_mapping.dataset_id == (seed.first_dataset_id)
    assert persisted_mapping.version == 1

    assert [covariate.normalized_column_name for covariate in covariates] == [
        "promotion",
        "seasonality",
    ]


@pytest.mark.asyncio
async def test_rejects_cross_dataset_role_reference(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    seed = await seed_semantic_mapping_schema(
        tenancy_session_factory,
    )

    mapping = build_mapping(
        seed,
        outcome_column="foreign_revenue",
    )

    with pytest.raises(
        IntegrityError,
    ) as error:
        async with (
            tenancy_session_factory() as session,
            session.begin(),
        ):
            session.add(mapping)
            await session.flush()

    assert_constraint_name(
        error,
        ("fk_dataset_semantic_mappings_outcome_column"),
    )


@pytest.mark.asyncio
async def test_rejects_cross_dataset_covariate_reference(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    seed = await seed_semantic_mapping_schema(
        tenancy_session_factory,
    )

    mapping = build_mapping(seed)

    await persist_mapping(
        tenancy_session_factory,
        mapping,
    )

    covariate = build_covariate(
        mapping_id=mapping.id,
        dataset_id=seed.first_dataset_id,
        ordinal_position=1,
        normalized_column_name=("foreign_covariate"),
    )

    with pytest.raises(
        IntegrityError,
    ) as error:
        async with (
            tenancy_session_factory() as session,
            session.begin(),
        ):
            session.add(covariate)
            await session.flush()

    assert_constraint_name(
        error,
        "fk_dataset_mapping_covariates_column",
    )


@pytest.mark.asyncio
async def test_rejects_duplicate_mapping_version(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    seed = await seed_semantic_mapping_schema(
        tenancy_session_factory,
    )

    await persist_mapping(
        tenancy_session_factory,
        build_mapping(seed),
    )

    duplicate = build_mapping(
        seed,
        version=1,
    )

    with pytest.raises(
        IntegrityError,
    ) as error:
        async with (
            tenancy_session_factory() as session,
            session.begin(),
        ):
            session.add(duplicate)
            await session.flush()

    assert_constraint_name(
        error,
        ("uq_dataset_semantic_mappings_dataset_version"),
    )


@pytest.mark.asyncio
async def test_rejects_duplicate_covariate_column(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    seed = await seed_semantic_mapping_schema(
        tenancy_session_factory,
    )

    mapping = build_mapping(seed)

    async with (
        tenancy_session_factory() as session,
        session.begin(),
    ):
        session.add(mapping)
        await session.flush()

        session.add(
            build_covariate(
                mapping_id=mapping.id,
                dataset_id=seed.first_dataset_id,
                ordinal_position=1,
                normalized_column_name="promotion",
            )
        )

    duplicate = build_covariate(
        mapping_id=mapping.id,
        dataset_id=seed.first_dataset_id,
        ordinal_position=2,
        normalized_column_name="promotion",
    )

    with pytest.raises(
        IntegrityError,
    ) as error:
        async with (
            tenancy_session_factory() as session,
            session.begin(),
        ):
            session.add(duplicate)
            await session.flush()

    assert_constraint_name(
        error,
        ("uq_dataset_mapping_covariates_mapping_column"),
    )


@pytest.mark.asyncio
async def test_rejects_duplicate_covariate_ordinal(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    seed = await seed_semantic_mapping_schema(
        tenancy_session_factory,
    )

    mapping = build_mapping(seed)

    async with (
        tenancy_session_factory() as session,
        session.begin(),
    ):
        session.add(mapping)
        await session.flush()

        session.add(
            build_covariate(
                mapping_id=mapping.id,
                dataset_id=seed.first_dataset_id,
                ordinal_position=1,
                normalized_column_name="promotion",
            )
        )

    duplicate = build_covariate(
        mapping_id=mapping.id,
        dataset_id=seed.first_dataset_id,
        ordinal_position=1,
        normalized_column_name="seasonality",
    )

    with pytest.raises(
        IntegrityError,
    ) as error:
        async with (
            tenancy_session_factory() as session,
            session.begin(),
        ):
            session.add(duplicate)
            await session.flush()

    assert_constraint_name(
        error,
        ("uq_dataset_mapping_covariates_mapping_ordinal"),
    )


@pytest.mark.asyncio
async def test_rejects_overlapping_semantic_roles(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    seed = await seed_semantic_mapping_schema(
        tenancy_session_factory,
    )

    mapping = build_mapping(
        seed,
        unit_column="date",
    )

    with pytest.raises(
        IntegrityError,
    ) as error:
        async with (
            tenancy_session_factory() as session,
            session.begin(),
        ):
            session.add(mapping)
            await session.flush()

    assert_constraint_name(
        error,
        ("ck_dataset_semantic_mappings_roles_distinct"),
    )


@pytest.mark.asyncio
async def test_rejects_equal_treatment_and_control_values(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    seed = await seed_semantic_mapping_schema(
        tenancy_session_factory,
    )

    mapping = build_mapping(
        seed,
        treatment_value=" TRUE ",
        control_value="true",
    )

    with pytest.raises(
        IntegrityError,
    ) as error:
        async with (
            tenancy_session_factory() as session,
            session.begin(),
        ):
            session.add(mapping)
            await session.flush()

    assert_constraint_name(
        error,
        ("ck_dataset_semantic_mappings_values_distinct"),
    )


@pytest.mark.asyncio
async def test_dataset_deletion_cascades_mapping_and_covariates(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    seed = await seed_semantic_mapping_schema(
        tenancy_session_factory,
    )

    mapping = build_mapping(seed)

    async with (
        tenancy_session_factory() as session,
        session.begin(),
    ):
        session.add(mapping)
        await session.flush()

        session.add_all(
            [
                build_covariate(
                    mapping_id=mapping.id,
                    dataset_id=seed.first_dataset_id,
                    ordinal_position=1,
                    normalized_column_name="promotion",
                ),
                build_covariate(
                    mapping_id=mapping.id,
                    dataset_id=seed.first_dataset_id,
                    ordinal_position=2,
                    normalized_column_name="seasonality",
                ),
            ]
        )

    async with (
        tenancy_session_factory() as session,
        session.begin(),
    ):
        await session.execute(
            delete(DatasetModel).where(
                DatasetModel.id == seed.first_dataset_id,
            )
        )

    async with tenancy_session_factory() as session:
        mapping_count = await session.scalar(
            select(func.count())
            .select_from(DatasetSemanticMappingModel)
            .where(
                DatasetSemanticMappingModel.dataset_id == seed.first_dataset_id,
            )
        )

        covariate_count = await session.scalar(
            select(func.count())
            .select_from(DatasetMappingCovariateModel)
            .where(
                DatasetMappingCovariateModel.dataset_id == seed.first_dataset_id,
            )
        )

        column_count = await session.scalar(
            select(func.count())
            .select_from(DatasetColumnModel)
            .where(
                DatasetColumnModel.dataset_id == seed.first_dataset_id,
            )
        )

    assert mapping_count == 0
    assert covariate_count == 0
    assert column_count == 0
