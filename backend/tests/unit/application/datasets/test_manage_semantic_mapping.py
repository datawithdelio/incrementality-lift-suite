from datetime import UTC, datetime
from types import TracebackType
from uuid import UUID, uuid4

import pytest
from incrementality_api.application.datasets.manage_semantic_mapping import (
    CreateDatasetSemanticMapping,
    CreateDatasetSemanticMappingCommand,
    GetDatasetSemanticMapping,
    GetDatasetSemanticMappingQuery,
)

from incrementality_api.application.datasets.errors import (
    DatasetSemanticMappingUnavailableError,
    DatasetUnavailableError,
)
from incrementality_api.domain.datasets.columns import (
    DatasetColumnProfile,
    DatasetColumnType,
)
from incrementality_api.domain.datasets.entities import Dataset
from incrementality_api.domain.datasets.semantic_mapping import (
    DatasetSemanticMapping,
)

UPLOADED_AT = datetime(
    2026,
    7,
    14,
    22,
    0,
    tzinfo=UTC,
)

VALIDATION_STARTED_AT = datetime(
    2026,
    7,
    14,
    22,
    1,
    tzinfo=UTC,
)

VALIDATION_COMPLETED_AT = datetime(
    2026,
    7,
    14,
    22,
    2,
    tzinfo=UTC,
)

MAPPING_CREATED_AT = datetime(
    2026,
    7,
    14,
    22,
    3,
    tzinfo=UTC,
)


def build_ready_dataset() -> Dataset:
    return (
        Dataset.register(
            workspace_id=uuid4(),
            project_id=uuid4(),
            created_by_user_id=uuid4(),
            source_filename="campaign-results.csv",
            storage_key=(
                "workspaces/workspace-1/projects/project-1/datasets/checksum/campaign-results.csv"
            ),
            media_type="text/csv",
            byte_size=1_024,
            checksum_sha256="a" * 64,
        )
        .mark_uploaded(
            uploaded_at=UPLOADED_AT,
        )
        .begin_validation(
            validation_started_at=VALIDATION_STARTED_AT,
        )
        .mark_ready(
            validation_completed_at=(VALIDATION_COMPLETED_AT),
            row_count=100,
            column_count=6,
        )
    )


def build_columns() -> tuple[
    DatasetColumnProfile,
    ...,
]:
    return (
        DatasetColumnProfile(
            ordinal_position=1,
            source_name="Date",
            normalized_name="date",
            inferred_type=DatasetColumnType.DATE,
            nullable=False,
            missing_count=0,
        ),
        DatasetColumnProfile(
            ordinal_position=2,
            source_name="Market",
            normalized_name="market",
            inferred_type=DatasetColumnType.STRING,
            nullable=False,
            missing_count=0,
        ),
        DatasetColumnProfile(
            ordinal_position=3,
            source_name="Treated",
            normalized_name="treated",
            inferred_type=DatasetColumnType.BOOLEAN,
            nullable=False,
            missing_count=0,
        ),
        DatasetColumnProfile(
            ordinal_position=4,
            source_name="Revenue",
            normalized_name="revenue",
            inferred_type=DatasetColumnType.FLOAT,
            nullable=False,
            missing_count=0,
        ),
        DatasetColumnProfile(
            ordinal_position=5,
            source_name="Spend",
            normalized_name="spend",
            inferred_type=DatasetColumnType.INTEGER,
            nullable=False,
            missing_count=0,
        ),
        DatasetColumnProfile(
            ordinal_position=6,
            source_name="Promotion",
            normalized_name="promotion",
            inferred_type=DatasetColumnType.STRING,
            nullable=False,
            missing_count=0,
        ),
    )


def build_mapping(
    *,
    dataset: Dataset,
    version: int,
) -> DatasetSemanticMapping:
    return DatasetSemanticMapping.create(
        dataset=dataset,
        columns=build_columns(),
        created_by_user_id=uuid4(),
        version=version,
        time_column="date",
        unit_column="market",
        treatment_column="treated",
        outcome_column="revenue",
        spend_column="spend",
        covariate_columns=("promotion",),
        treatment_value="true",
        control_value="false",
        created_at=MAPPING_CREATED_AT,
    )


class FixedClock:
    def now(self) -> datetime:
        return MAPPING_CREATED_AT


class FakeDatasetRepository:
    def __init__(
        self,
        dataset: Dataset | None,
    ) -> None:
        self.dataset = dataset
        self.locked_scopes: list[tuple[UUID, UUID, UUID]] = []

    async def get_by_scope(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        dataset_id: UUID,
    ) -> Dataset | None:
        self.locked_scopes.append(
            (
                workspace_id,
                project_id,
                dataset_id,
            )
        )

        return self.dataset


class FakeDatasetColumnRepository:
    def __init__(
        self,
        columns: tuple[
            DatasetColumnProfile,
            ...,
        ],
    ) -> None:
        self.columns = columns
        self.scopes: list[tuple[UUID, UUID, UUID]] = []

    async def list_by_scope(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        dataset_id: UUID,
    ) -> tuple[
        DatasetColumnProfile,
        ...,
    ]:
        self.scopes.append(
            (
                workspace_id,
                project_id,
                dataset_id,
            )
        )

        return self.columns


class FakeSemanticMappingRepository:
    def __init__(
        self,
        *,
        latest_mapping: (DatasetSemanticMapping | None) = None,
        version_mapping: (DatasetSemanticMapping | None) = None,
    ) -> None:
        self.latest_mapping = latest_mapping
        self.version_mapping = version_mapping
        self.added: list[DatasetSemanticMapping] = []
        self.latest_scopes: list[tuple[UUID, UUID, UUID]] = []
        self.version_scopes: list[tuple[UUID, UUID, UUID, int]] = []

    async def add(
        self,
        mapping: DatasetSemanticMapping,
    ) -> None:
        self.added.append(mapping)

    async def get_latest_by_scope(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        dataset_id: UUID,
    ) -> DatasetSemanticMapping | None:
        self.latest_scopes.append(
            (
                workspace_id,
                project_id,
                dataset_id,
            )
        )

        return self.latest_mapping

    async def get_by_scope_and_version(
        self,
        *,
        workspace_id: UUID,
        project_id: UUID,
        dataset_id: UUID,
        version: int,
    ) -> DatasetSemanticMapping | None:
        self.version_scopes.append(
            (
                workspace_id,
                project_id,
                dataset_id,
                version,
            )
        )

        return self.version_mapping


class FakeSemanticMappingUnitOfWork:
    def __init__(
        self,
        *,
        dataset: Dataset | None,
        columns: tuple[
            DatasetColumnProfile,
            ...,
        ] = (),
        latest_mapping: (DatasetSemanticMapping | None) = None,
        version_mapping: (DatasetSemanticMapping | None) = None,
    ) -> None:
        self.datasets = FakeDatasetRepository(
            dataset,
        )
        self.columns = FakeDatasetColumnRepository(
            columns,
        )
        self.semantic_mappings = FakeSemanticMappingRepository(
            latest_mapping=latest_mapping,
            version_mapping=version_mapping,
        )
        self.enter_count = 0
        self.exit_count = 0
        self.commit_count = 0

    async def __aenter__(
        self,
    ):
        self.enter_count += 1
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exception_type, exception, traceback
        self.exit_count += 1

    async def commit(self) -> None:
        self.commit_count += 1


def build_create_command(
    dataset: Dataset,
) -> CreateDatasetSemanticMappingCommand:
    return CreateDatasetSemanticMappingCommand(
        workspace_id=dataset.workspace_id,
        project_id=dataset.project_id,
        dataset_id=dataset.id,
        created_by_user_id=uuid4(),
        time_column="Date",
        unit_column="Market",
        treatment_column="Treated",
        outcome_column="Revenue",
        spend_column="Spend",
        covariate_columns=("Promotion",),
        treatment_value=" true ",
        control_value=" false ",
    )


@pytest.mark.asyncio
async def test_creates_first_mapping_version_atomically() -> None:
    dataset = build_ready_dataset()

    unit_of_work = FakeSemanticMappingUnitOfWork(
        dataset=dataset,
        columns=build_columns(),
    )

    result = await CreateDatasetSemanticMapping(
        unit_of_work=unit_of_work,
        clock=FixedClock(),
    ).execute(build_create_command(dataset))

    assert result.version == 1
    assert result.dataset_id == dataset.id
    assert result.time_column == "date"
    assert result.outcome_column == "revenue"
    assert result.covariate_columns == ("promotion",)

    assert unit_of_work.datasets.locked_scopes == [
        (
            dataset.workspace_id,
            dataset.project_id,
            dataset.id,
        )
    ]

    assert unit_of_work.columns.scopes == [
        (
            dataset.workspace_id,
            dataset.project_id,
            dataset.id,
        )
    ]

    assert unit_of_work.semantic_mappings.latest_scopes == [
        (
            dataset.workspace_id,
            dataset.project_id,
            dataset.id,
        )
    ]

    assert unit_of_work.semantic_mappings.added == [
        result,
    ]
    assert unit_of_work.commit_count == 1


@pytest.mark.asyncio
async def test_increments_latest_mapping_version() -> None:
    dataset = build_ready_dataset()

    existing_mapping = build_mapping(
        dataset=dataset,
        version=3,
    )

    unit_of_work = FakeSemanticMappingUnitOfWork(
        dataset=dataset,
        columns=build_columns(),
        latest_mapping=existing_mapping,
    )

    result = await CreateDatasetSemanticMapping(
        unit_of_work=unit_of_work,
        clock=FixedClock(),
    ).execute(build_create_command(dataset))

    assert result.version == 4
    assert unit_of_work.commit_count == 1


@pytest.mark.asyncio
async def test_create_rejects_unknown_dataset_without_commit() -> None:
    dataset = build_ready_dataset()

    unit_of_work = FakeSemanticMappingUnitOfWork(
        dataset=None,
        columns=build_columns(),
    )

    with pytest.raises(
        DatasetUnavailableError,
        match="Dataset is unavailable",
    ):
        await CreateDatasetSemanticMapping(
            unit_of_work=unit_of_work,
            clock=FixedClock(),
        ).execute(build_create_command(dataset))

    assert unit_of_work.columns.scopes == []
    assert unit_of_work.semantic_mappings.added == []
    assert unit_of_work.commit_count == 0


@pytest.mark.asyncio
async def test_gets_latest_mapping_in_tenant_scope() -> None:
    dataset = build_ready_dataset()
    mapping = build_mapping(
        dataset=dataset,
        version=2,
    )

    unit_of_work = FakeSemanticMappingUnitOfWork(
        dataset=dataset,
        latest_mapping=mapping,
    )

    result = await GetDatasetSemanticMapping(
        unit_of_work=unit_of_work,
    ).execute(
        GetDatasetSemanticMappingQuery(
            workspace_id=dataset.workspace_id,
            project_id=dataset.project_id,
            dataset_id=dataset.id,
        )
    )

    assert result == mapping

    assert unit_of_work.semantic_mappings.latest_scopes == [
        (
            dataset.workspace_id,
            dataset.project_id,
            dataset.id,
        )
    ]

    assert unit_of_work.semantic_mappings.version_scopes == []


@pytest.mark.asyncio
async def test_gets_specific_mapping_version() -> None:
    dataset = build_ready_dataset()
    mapping = build_mapping(
        dataset=dataset,
        version=2,
    )

    unit_of_work = FakeSemanticMappingUnitOfWork(
        dataset=dataset,
        version_mapping=mapping,
    )

    result = await GetDatasetSemanticMapping(
        unit_of_work=unit_of_work,
    ).execute(
        GetDatasetSemanticMappingQuery(
            workspace_id=dataset.workspace_id,
            project_id=dataset.project_id,
            dataset_id=dataset.id,
            version=2,
        )
    )

    assert result == mapping

    assert unit_of_work.semantic_mappings.version_scopes == [
        (
            dataset.workspace_id,
            dataset.project_id,
            dataset.id,
            2,
        )
    ]

    assert unit_of_work.semantic_mappings.latest_scopes == []


@pytest.mark.asyncio
async def test_get_rejects_missing_mapping() -> None:
    dataset = build_ready_dataset()

    unit_of_work = FakeSemanticMappingUnitOfWork(
        dataset=dataset,
    )

    with pytest.raises(
        DatasetSemanticMappingUnavailableError,
        match="Semantic mapping is unavailable",
    ):
        await GetDatasetSemanticMapping(
            unit_of_work=unit_of_work,
        ).execute(
            GetDatasetSemanticMappingQuery(
                workspace_id=dataset.workspace_id,
                project_id=dataset.project_id,
                dataset_id=dataset.id,
            )
        )
