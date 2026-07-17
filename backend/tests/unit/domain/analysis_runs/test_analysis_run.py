from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from incrementality_api.domain.analysis_runs.analysis_period_snapshot import (
    AnalysisPeriodSnapshot,
)
from incrementality_api.domain.analysis_runs.entities import (
    AnalysisRun,
)
from incrementality_api.domain.analysis_runs.errors import (
    InvalidAnalysisRunError,
    InvalidAnalysisRunTransitionError,
)
from incrementality_api.domain.analysis_runs.semantic_mapping_snapshot import (
    SemanticMappingSnapshot,
)
from incrementality_api.domain.analysis_runs.status import (
    AnalysisEstimatorType,
    AnalysisRunStatus,
)

APPLICATION_VERSION = "0.1.0"
SOURCE_REVISION = "a" * 40
MAPPING_SNAPSHOT = SemanticMappingSnapshot.create(
    time_column="date",
    unit_column="market",
    treatment_column="treated",
    outcome_column="revenue",
    spend_column=None,
    covariate_columns=(),
    treatment_value="true",
    control_value="false",
)
PERIOD_SNAPSHOT = AnalysisPeriodSnapshot.from_configuration(
    AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
    {
        "analysis_start_date": "2026-01-01",
        "analysis_end_date": "2026-01-31",
        "intervention_date": "2026-01-15",
    },
)

CREATED_AT = datetime(
    2026,
    7,
    15,
    12,
    0,
    tzinfo=UTC,
)

STARTED_AT = datetime(
    2026,
    7,
    15,
    12,
    1,
    tzinfo=UTC,
)

COMPLETED_AT = datetime(
    2026,
    7,
    15,
    12,
    5,
    tzinfo=UTC,
)

CONFIGURATION_JSON = """
{
  "include_unit_fixed_effects": true,
  "alpha": 0.05,
  "cluster_by": "unit"
}
"""


DATASET_CHECKSUM_SHA256 = "a" * 64
DATASET_BYTE_SIZE = 4_096


def queue_run(
    *,
    semantic_mapping_version: int = 1,
    configuration_json: str = CONFIGURATION_JSON,
    created_at: datetime = CREATED_AT,
    estimator_version: str = "did-v1",
) -> AnalysisRun:
    return AnalysisRun.queue(
        workspace_id=uuid4(),
        project_id=uuid4(),
        dataset_id=uuid4(),
        dataset_checksum_sha256=DATASET_CHECKSUM_SHA256,
        dataset_byte_size=DATASET_BYTE_SIZE,
        semantic_mapping_id=uuid4(),
        semantic_mapping_version=(semantic_mapping_version),
        semantic_mapping_snapshot=MAPPING_SNAPSHOT,
        analysis_period_snapshot=PERIOD_SNAPSHOT,
        created_by_user_id=uuid4(),
        estimator_type=(AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES),
        estimator_version=estimator_version,
        random_seed=1_729,
        configuration_json=configuration_json,
        created_at=created_at,
        application_version=APPLICATION_VERSION,
        source_revision=SOURCE_REVISION,
        statistical_library_versions={"numpy": "2.3.1", "statsmodels": "0.14.5"},
    )


def running_run() -> AnalysisRun:
    return queue_run().start(
        started_at=STARTED_AT,
    )


def test_queues_analysis_run_with_reproducible_snapshot() -> None:
    workspace_id = uuid4()
    project_id = uuid4()
    dataset_id = uuid4()
    mapping_id = uuid4()
    user_id = uuid4()

    run = AnalysisRun.queue(
        workspace_id=workspace_id,
        project_id=project_id,
        dataset_id=dataset_id,
        dataset_checksum_sha256=DATASET_CHECKSUM_SHA256,
        dataset_byte_size=DATASET_BYTE_SIZE,
        semantic_mapping_id=mapping_id,
        semantic_mapping_version=3,
        semantic_mapping_snapshot=MAPPING_SNAPSHOT,
        analysis_period_snapshot=PERIOD_SNAPSHOT,
        created_by_user_id=user_id,
        estimator_type=(AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES),
        estimator_version="did-v1",
        random_seed=1_729,
        configuration_json=CONFIGURATION_JSON,
        created_at=CREATED_AT,
        application_version=APPLICATION_VERSION,
        source_revision=SOURCE_REVISION,
        statistical_library_versions={"numpy": "2.3.1", "statsmodels": "0.14.5"},
    )

    assert run.workspace_id == workspace_id
    assert run.project_id == project_id
    assert run.dataset_id == dataset_id
    assert run.semantic_mapping_id == mapping_id
    assert run.semantic_mapping_version == 3
    assert run.created_by_user_id == user_id

    assert run.estimator_type is (AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES)
    assert run.estimator_version == "did-v1"

    assert run.configuration_json == (
        '{"alpha":0.05,"analysis_end_date":"2026-01-31",'
        '"analysis_start_date":"2026-01-01","cluster_by":"unit",'
        '"include_unit_fixed_effects":true,"intervention_date":"2026-01-15",'
        '"post_period_end_date":"2026-01-31","post_period_start_date":"2026-01-15",'
        '"pre_period_end_date":"2026-01-14","pre_period_start_date":"2026-01-01"}'
    )

    assert run.status is AnalysisRunStatus.QUEUED
    assert run.created_at == CREATED_AT
    assert run.started_at is None
    assert run.completed_at is None
    assert run.failure_reason is None
    assert run.cancellation_reason is None


@pytest.mark.parametrize(
    "version",
    [
        0,
        -1,
    ],
)
def test_semantic_mapping_version_must_be_positive(
    version: int,
) -> None:
    with pytest.raises(
        InvalidAnalysisRunError,
        match=("Semantic mapping version must be positive"),
    ):
        queue_run(
            semantic_mapping_version=version,
        )


@pytest.mark.parametrize(
    ("configuration_json", "message"),
    [
        (
            "",
            "configuration must not be blank",
        ),
        (
            "not-json",
            "configuration must be valid JSON",
        ),
        (
            '["not", "an", "object"]',
            "configuration must be a JSON object",
        ),
    ],
)
def test_configuration_must_be_valid_json_object(
    configuration_json: str,
    message: str,
) -> None:
    with pytest.raises(
        InvalidAnalysisRunError,
        match=message,
    ):
        queue_run(
            configuration_json=configuration_json,
        )


@pytest.mark.parametrize(
    "estimator_version",
    [
        "",
        "   ",
    ],
)
def test_estimator_version_must_not_be_blank(
    estimator_version: str,
) -> None:
    with pytest.raises(
        InvalidAnalysisRunError,
        match="Estimator version must not be blank",
    ):
        queue_run(
            estimator_version=estimator_version,
        )


@pytest.mark.parametrize(
    ("field_name", "application_version", "source_revision", "message"),
    [
        ("application_version", "   ", SOURCE_REVISION, "Application version must not be blank"),
        ("source_revision", APPLICATION_VERSION, "   ", "Source revision must not be blank"),
    ],
)
def test_runtime_lineage_must_not_be_blank_for_new_runs(
    field_name: str,
    application_version: str,
    source_revision: str,
    message: str,
) -> None:
    del field_name

    with pytest.raises(
        InvalidAnalysisRunError,
        match=message,
    ):
        AnalysisRun.queue(
            workspace_id=uuid4(),
            project_id=uuid4(),
            dataset_id=uuid4(),
            dataset_checksum_sha256=DATASET_CHECKSUM_SHA256,
            dataset_byte_size=DATASET_BYTE_SIZE,
            semantic_mapping_id=uuid4(),
            semantic_mapping_version=1,
            semantic_mapping_snapshot=MAPPING_SNAPSHOT,
            analysis_period_snapshot=PERIOD_SNAPSHOT,
            created_by_user_id=uuid4(),
            estimator_type=AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES,
            estimator_version="did-v1",
            application_version=application_version,
            source_revision=source_revision,
            statistical_library_versions={"numpy": "2.3.1", "statsmodels": "0.14.5"},
            random_seed=1_729,
            configuration_json=CONFIGURATION_JSON,
            created_at=CREATED_AT,
        )


def test_creation_timestamp_must_be_timezone_aware() -> None:
    with pytest.raises(
        InvalidAnalysisRunError,
        match=("Analysis run timestamps must be timezone-aware"),
    ):
        queue_run(
            created_at=datetime(
                2026,
                7,
                15,
                12,
                0,
            ),
        )


def test_starts_queued_analysis_run_immutably() -> None:
    queued = queue_run()

    running = queued.start(
        started_at=STARTED_AT,
    )

    assert running.status is AnalysisRunStatus.RUNNING
    assert running.started_at == STARTED_AT
    assert running.completed_at is None
    assert running.failure_reason is None
    assert running.cancellation_reason is None

    assert queued.status is AnalysisRunStatus.QUEUED
    assert queued.started_at is None


def test_lifecycle_transitions_preserve_runtime_lineage() -> None:
    queued = queue_run()

    running = queued.start(started_at=STARTED_AT)
    succeeded = running.mark_succeeded(completed_at=COMPLETED_AT)

    for run in (queued, running, succeeded):
        assert run.application_version == APPLICATION_VERSION
        assert run.source_revision == SOURCE_REVISION
        assert run.statistical_library_versions == queued.statistical_library_versions
        assert run.semantic_mapping_snapshot == queued.semantic_mapping_snapshot
        assert run.analysis_period_snapshot == queued.analysis_period_snapshot


def test_start_cannot_precede_creation() -> None:
    queued = queue_run()

    with pytest.raises(
        InvalidAnalysisRunTransitionError,
        match=("Analysis start timestamp cannot precede creation"),
    ):
        queued.start(
            started_at=(CREATED_AT - timedelta(seconds=1)),
        )


def test_only_queued_analysis_run_can_start() -> None:
    running = running_run()

    with pytest.raises(
        InvalidAnalysisRunTransitionError,
        match="cannot be started",
    ):
        running.start(
            started_at=(STARTED_AT + timedelta(seconds=1)),
        )


def test_marks_running_analysis_run_succeeded() -> None:
    running = running_run()

    succeeded = running.mark_succeeded(
        completed_at=COMPLETED_AT,
    )

    assert succeeded.status is (AnalysisRunStatus.SUCCEEDED)
    assert succeeded.started_at == STARTED_AT
    assert succeeded.completed_at == COMPLETED_AT
    assert succeeded.failure_reason is None
    assert succeeded.cancellation_reason is None


def test_only_running_analysis_run_can_succeed() -> None:
    queued = queue_run()

    with pytest.raises(
        InvalidAnalysisRunTransitionError,
        match="cannot be marked succeeded",
    ):
        queued.mark_succeeded(
            completed_at=COMPLETED_AT,
        )


def test_marks_running_analysis_run_failed() -> None:
    running = running_run()

    failed = running.mark_failed(
        completed_at=COMPLETED_AT,
        reason="Estimator execution failed.",
    )

    assert failed.status is AnalysisRunStatus.FAILED
    assert failed.completed_at == COMPLETED_AT
    assert failed.failure_reason == ("Estimator execution failed.")
    assert failed.cancellation_reason is None


@pytest.mark.parametrize(
    "reason",
    [
        "",
        "   ",
    ],
)
def test_failure_reason_must_not_be_blank(
    reason: str,
) -> None:
    running = running_run()

    with pytest.raises(
        InvalidAnalysisRunTransitionError,
        match="Failure reason must not be blank",
    ):
        running.mark_failed(
            completed_at=COMPLETED_AT,
            reason=reason,
        )


def test_only_running_analysis_run_can_fail() -> None:
    queued = queue_run()

    with pytest.raises(
        InvalidAnalysisRunTransitionError,
        match="cannot be marked failed",
    ):
        queued.mark_failed(
            completed_at=COMPLETED_AT,
            reason="Estimator execution failed.",
        )


def test_cancels_queued_analysis_run() -> None:
    queued = queue_run()

    cancelled = queued.cancel(
        cancelled_at=STARTED_AT,
        reason="User cancelled the analysis.",
    )

    assert cancelled.status is (AnalysisRunStatus.CANCELLED)
    assert cancelled.started_at is None
    assert cancelled.completed_at == STARTED_AT
    assert cancelled.failure_reason is None
    assert cancelled.cancellation_reason == ("User cancelled the analysis.")


def test_cancels_running_analysis_run() -> None:
    running = running_run()

    cancelled = running.cancel(
        cancelled_at=COMPLETED_AT,
        reason="User cancelled the analysis.",
    )

    assert cancelled.status is (AnalysisRunStatus.CANCELLED)
    assert cancelled.started_at == STARTED_AT
    assert cancelled.completed_at == COMPLETED_AT
    assert cancelled.failure_reason is None
    assert cancelled.cancellation_reason == ("User cancelled the analysis.")


def test_terminal_analysis_run_cannot_be_cancelled() -> None:
    succeeded = running_run().mark_succeeded(
        completed_at=COMPLETED_AT,
    )

    with pytest.raises(
        InvalidAnalysisRunTransitionError,
        match="cannot be cancelled",
    ):
        succeeded.cancel(
            cancelled_at=(COMPLETED_AT + timedelta(seconds=1)),
            reason="Too late.",
        )


def test_completion_cannot_precede_start() -> None:
    running = running_run()

    with pytest.raises(
        InvalidAnalysisRunTransitionError,
        match=("Analysis completion timestamp cannot precede its start timestamp"),
    ):
        running.mark_succeeded(
            completed_at=(STARTED_AT - timedelta(seconds=1)),
        )


def test_transition_timestamps_must_be_timezone_aware() -> None:
    queued = queue_run()

    with pytest.raises(
        InvalidAnalysisRunTransitionError,
        match=("Analysis run timestamps must be timezone-aware"),
    ):
        queued.start(
            started_at=datetime(
                2026,
                7,
                15,
                12,
                1,
            ),
        )
