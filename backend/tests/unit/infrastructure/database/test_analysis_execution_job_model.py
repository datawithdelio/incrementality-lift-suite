from incrementality_api.infrastructure.database.models.analysis_execution_jobs import (
    AnalysisExecutionJobModel,
)
from sqlalchemy import (
    DateTime,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.types import Uuid

from incrementality_api.infrastructure.database.models.analysis_runs import (
    AnalysisRunModel,
)


def constraint_names(
    model: type[AnalysisExecutionJobModel | AnalysisRunModel],
) -> set[str]:
    return {
        constraint.name for constraint in model.__table__.constraints if constraint.name is not None
    }


def index_names(
    model: type[AnalysisExecutionJobModel],
) -> set[str]:
    return {index.name for index in model.__table__.indexes if index.name is not None}


def test_analysis_execution_job_table_contract() -> None:
    table = AnalysisExecutionJobModel.__table__

    assert table.name == "analysis_execution_jobs"

    assert set(table.columns.keys()) == {
        "id",
        "workspace_id",
        "project_id",
        "analysis_run_id",
        "status",
        "attempt_count",
        "max_attempts",
        "available_at",
        "claimed_at",
        "completed_at",
        "last_error",
        "created_at",
        "updated_at",
    }

    assert isinstance(
        table.c.id.type,
        Uuid,
    )
    assert table.c.id.primary_key

    for column_name in (
        "workspace_id",
        "project_id",
        "analysis_run_id",
    ):
        column = table.c[column_name]

        assert isinstance(
            column.type,
            Uuid,
        )
        assert not column.nullable

    assert isinstance(
        table.c.status.type,
        String,
    )
    assert table.c.status.type.length == 32
    assert not table.c.status.nullable

    for column_name in (
        "attempt_count",
        "max_attempts",
    ):
        column = table.c[column_name]

        assert isinstance(
            column.type,
            Integer,
        )
        assert not column.nullable

    for column_name in (
        "available_at",
        "claimed_at",
        "completed_at",
        "created_at",
        "updated_at",
    ):
        column = table.c[column_name]

        assert isinstance(
            column.type,
            DateTime,
        )
        assert column.type.timezone is True

    assert not table.c.available_at.nullable
    assert table.c.claimed_at.nullable
    assert table.c.completed_at.nullable
    assert not table.c.created_at.nullable
    assert not table.c.updated_at.nullable

    assert isinstance(
        table.c.last_error.type,
        String,
    )
    assert table.c.last_error.type.length == 2_000
    assert table.c.last_error.nullable


def test_analysis_execution_job_constraints_exist() -> None:
    assert constraint_names(AnalysisExecutionJobModel).issuperset(
        {
            "ck_analysis_execution_jobs_status",
            ("ck_analysis_execution_jobs_attempt_nonnegative"),
            ("ck_analysis_execution_jobs_max_attempts_positive"),
            ("ck_analysis_execution_jobs_attempt_within_limit"),
            ("ck_analysis_execution_jobs_error_not_blank"),
            ("ck_analysis_execution_jobs_available_after_create"),
            ("ck_analysis_execution_jobs_claim_after_available"),
            ("ck_analysis_execution_jobs_completion_after_claim"),
            ("ck_analysis_execution_jobs_lifecycle_metadata"),
            "fk_analysis_execution_jobs_run_scope",
            ("uq_analysis_execution_jobs_analysis_run_id"),
        }
    )


def test_analysis_execution_job_enforces_run_scope() -> None:
    foreign_key = next(
        constraint
        for constraint in (AnalysisExecutionJobModel.__table__.constraints)
        if (
            isinstance(
                constraint,
                ForeignKeyConstraint,
            )
            and constraint.name == "fk_analysis_execution_jobs_run_scope"
        )
    )

    assert tuple(foreign_key.column_keys) == (
        "analysis_run_id",
        "workspace_id",
        "project_id",
    )

    assert tuple(element.target_fullname for element in foreign_key.elements) == (
        "analysis_runs.id",
        "analysis_runs.workspace_id",
        "analysis_runs.project_id",
    )

    assert foreign_key.ondelete == "CASCADE"


def test_execution_job_is_one_to_one_with_run() -> None:
    unique_constraints = {
        constraint.name
        for constraint in (AnalysisExecutionJobModel.__table__.constraints)
        if isinstance(
            constraint,
            UniqueConstraint,
        )
    }

    assert "uq_analysis_execution_jobs_analysis_run_id" in unique_constraints


def test_analysis_run_exposes_scoped_candidate_key() -> None:
    unique_constraints = {
        constraint.name
        for constraint in (AnalysisRunModel.__table__.constraints)
        if isinstance(
            constraint,
            UniqueConstraint,
        )
    }

    assert "uq_analysis_runs_id_workspace_project" in unique_constraints


def test_analysis_execution_job_query_indexes() -> None:
    assert index_names(AnalysisExecutionJobModel) == {
        ("ix_analysis_execution_jobs_claimable"),
        ("ix_analysis_execution_jobs_stale_running"),
        ("ix_analysis_execution_jobs_workspace_id"),
        ("ix_analysis_execution_jobs_project_id"),
    }
