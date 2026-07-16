from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from incrementality_api.application.analysis_execution.estimation import (
    DifferenceInDifferencesInput,
    PermanentEstimationError,
)
from incrementality_api.application.analysis_execution.input_loading import (
    AnalysisInputMetadata,
    AnalysisInputMetadataValidator,
    CsvAnalysisRowLoader,
    DifferenceInDifferencesConfigurationParser,
    DifferenceInDifferencesInputBuilder,
    ProductionAnalysisInputLoader,
)
from incrementality_api.domain.analysis_runs.entities import AnalysisRun
from incrementality_api.domain.analysis_runs.execution_jobs import AnalysisExecutionJob
from incrementality_api.domain.analysis_runs.status import AnalysisEstimatorType
from incrementality_api.domain.datasets.columns import (
    DatasetColumnProfile,
    DatasetColumnType,
)
from incrementality_api.domain.datasets.entities import Dataset
from incrementality_api.domain.datasets.semantic_mapping import DatasetSemanticMapping
from incrementality_api.domain.datasets.status import DatasetStatus

NOW = datetime(2026, 7, 20, 10, 0, tzinfo=UTC)


def build_metadata(
    *,
    configuration_json: str = '{"intervention_time":"2026-01-02T00:00:00+00:00"}',
    nullable_outcome: bool = False,
) -> tuple[AnalysisExecutionJob, AnalysisInputMetadata]:
    workspace_id = uuid4()
    project_id = uuid4()
    dataset_id = uuid4()
    mapping_id = uuid4()
    user_id = uuid4()
    run = AnalysisRun.queue(
        workspace_id=workspace_id,
        project_id=project_id,
        dataset_id=dataset_id,
        dataset_checksum_sha256="c" * 64,
        dataset_byte_size=4_096,
        semantic_mapping_id=mapping_id,
        semantic_mapping_version=2,
        created_by_user_id=user_id,
        estimator_type=AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
        estimator_version="did-v1",
        configuration_json=configuration_json,
        created_at=NOW,
    ).start(started_at=NOW)
    job = AnalysisExecutionJob.enqueue(
        workspace_id=workspace_id,
        project_id=project_id,
        analysis_run_id=run.id,
        created_at=NOW,
        available_at=NOW,
    ).claim(claimed_at=NOW)
    dataset = Dataset(
        id=dataset_id,
        workspace_id=workspace_id,
        project_id=project_id,
        created_by_user_id=user_id,
        source_filename="panel.csv",
        storage_key=f"datasets/{dataset_id}/panel.csv",
        media_type="text/csv",
        byte_size=100,
        checksum_sha256="a" * 64,
        status=DatasetStatus.READY,
        created_at=NOW,
        uploaded_at=NOW,
        validation_started_at=NOW,
        validation_completed_at=NOW,
        row_count=4,
        column_count=4,
        failure_reason=None,
    )
    mapping = DatasetSemanticMapping(
        id=mapping_id,
        dataset_id=dataset_id,
        created_by_user_id=user_id,
        version=2,
        time_column="date",
        unit_column="market",
        treatment_column="treated",
        outcome_column="revenue",
        spend_column=None,
        covariate_columns=(),
        treatment_value="yes",
        control_value="no",
        created_at=NOW,
        updated_at=NOW,
    )
    columns = (
        DatasetColumnProfile(1, "Date", "date", DatasetColumnType.DATE, False, 0),
        DatasetColumnProfile(2, "Market", "market", DatasetColumnType.STRING, False, 0),
        DatasetColumnProfile(3, "Treated", "treated", DatasetColumnType.STRING, False, 0),
        DatasetColumnProfile(
            4,
            "Revenue",
            "revenue",
            DatasetColumnType.FLOAT,
            nullable_outcome,
            1 if nullable_outcome else 0,
        ),
    )
    return job, AnalysisInputMetadata(
        run=run,
        dataset=dataset,
        mapping=mapping,
        columns=columns,
    )


class FakeMetadataReader:
    def __init__(self, metadata: AnalysisInputMetadata) -> None:
        self._metadata = metadata

    async def load(self, job: AnalysisExecutionJob) -> AnalysisInputMetadata:
        del job
        return self._metadata


class FakeObjectStorage:
    def __init__(self, content: bytes) -> None:
        self._content = content
        self.keys: list[str] = []

    async def read_chunks(self, storage_key: str) -> AsyncIterator[bytes]:
        self.keys.append(storage_key)
        midpoint = len(self._content) // 2
        yield self._content[:midpoint]
        yield self._content[midpoint:]


@pytest.mark.asyncio
async def test_loads_tenant_scoped_csv_and_constructs_did_input() -> None:
    job, metadata = build_metadata()
    csv_content = (
        b"Date,Market,Treated,Revenue\n"
        b"2026-01-01,north,no,10\n"
        b"2026-01-02,north,no,11\n"
        b"2026-01-01,south,yes,12\n"
        b"2026-01-02,south,yes,18\n"
    )
    storage = FakeObjectStorage(csv_content)

    loaded = await ProductionAnalysisInputLoader(
        metadata_reader=FakeMetadataReader(metadata),
        object_storage=storage,
        metadata_validator=AnalysisInputMetadataValidator(),
        row_loader=CsvAnalysisRowLoader(),
        configuration_parser=DifferenceInDifferencesConfigurationParser(),
        input_builder=DifferenceInDifferencesInputBuilder(),
    ).load(job)

    assert loaded.estimator_type is AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES
    assert storage.keys == [metadata.dataset.storage_key]
    assert isinstance(loaded.payload, DifferenceInDifferencesInput)
    assert [
        (row.unit, row.treated, row.post_period, row.outcome) for row in loaded.payload.observations
    ] == [
        ("north", False, False, 10.0),
        ("north", False, True, 11.0),
        ("south", True, False, 12.0),
        ("south", True, True, 18.0),
    ]


def test_rejects_nullable_required_column_profile() -> None:
    job, metadata = build_metadata(nullable_outcome=True)

    with pytest.raises(PermanentEstimationError, match="must not contain missing values"):
        AnalysisInputMetadataValidator().validate(job=job, metadata=metadata)


def test_rejects_dataset_outside_job_tenant_scope() -> None:
    job, metadata = build_metadata()
    mismatched = AnalysisInputMetadata(
        run=metadata.run,
        dataset=replace(metadata.dataset, workspace_id=uuid4()),
        mapping=metadata.mapping,
        columns=metadata.columns,
    )

    with pytest.raises(PermanentEstimationError, match="tenant scope"):
        AnalysisInputMetadataValidator().validate(job=job, metadata=mismatched)


def test_rejects_configuration_without_intervention_time() -> None:
    _job, metadata = build_metadata(configuration_json="{}")

    with pytest.raises(PermanentEstimationError, match="intervention_time"):
        DifferenceInDifferencesConfigurationParser().parse(metadata.run)


def test_rejects_missing_required_csv_value() -> None:
    _job, metadata = build_metadata()
    rows = ({"date": "2026-01-01", "market": "north", "treated": "no", "revenue": ""},)
    configuration = DifferenceInDifferencesConfigurationParser().parse(metadata.run)

    with pytest.raises(PermanentEstimationError, match="missing value"):
        DifferenceInDifferencesInputBuilder().build(
            rows=rows,
            mapping=metadata.mapping,
            configuration=configuration,
        )
