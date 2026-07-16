from datetime import UTC, datetime
from uuid import uuid4

from incrementality_api.domain.analysis_runs.entities import AnalysisRun
from incrementality_api.domain.analysis_runs.status import (
    AnalysisEstimatorType,
)


def test_analysis_run_records_random_seed() -> None:
    run = AnalysisRun.queue(
        workspace_id=uuid4(),
        project_id=uuid4(),
        dataset_id=uuid4(),
        dataset_checksum_sha256="a" * 64,
        dataset_byte_size=4_096,
        semantic_mapping_id=uuid4(),
        semantic_mapping_version=1,
        created_by_user_id=uuid4(),
        estimator_type=(AnalysisEstimatorType.DIFFERENCE_IN_DIFFERENCES),
        estimator_version="did-v1",
        random_seed=1_729,
        configuration_json='{"alpha":0.05}',
        created_at=datetime(
            2026,
            7,
            16,
            19,
            0,
            tzinfo=UTC,
        ),
    )

    assert run.random_seed == 1_729
