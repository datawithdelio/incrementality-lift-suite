from sqlalchemy import BigInteger, CheckConstraint, Float, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import Uuid

from incrementality_api.infrastructure.database.models.analysis_results import (
    AnalysisResultModel,
)


def test_analysis_result_model_has_structured_columns_and_canonical_run_constraint() -> None:
    table = AnalysisResultModel.__table__

    assert isinstance(table.c.id.type, Uuid)
    assert isinstance(table.c.effect.type, Float)
    assert isinstance(table.c.standard_error.type, Float)
    assert isinstance(table.c.p_value.type, Float)
    assert isinstance(table.c.sample_size.type, BigInteger)
    assert isinstance(table.c.diagnostics.type, JSONB)

    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert ("analysis_run_id",) in unique_columns

    foreign_keys = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    assert ("analysis_run_id", "workspace_id", "project_id") in foreign_keys

    check_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "ck_analysis_results_p_value_range" in check_names
    assert "ck_analysis_results_confidence_interval" in check_names
    assert "ck_analysis_results_sample_size_positive" in check_names
