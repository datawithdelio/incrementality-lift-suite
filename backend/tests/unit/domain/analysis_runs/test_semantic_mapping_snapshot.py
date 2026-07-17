import pytest

from incrementality_api.domain.analysis_runs.errors import InvalidAnalysisRunError
from incrementality_api.domain.analysis_runs.semantic_mapping_snapshot import (
    SemanticMappingSnapshot,
)


def snapshot(**overrides: object) -> SemanticMappingSnapshot:
    values: dict[str, object] = {
        "time_column": "date",
        "unit_column": "market",
        "treatment_column": "treated",
        "outcome_column": "revenue",
        "spend_column": "spend",
        "covariate_columns": ("promotion", "temperature"),
        "treatment_value": "yes",
        "control_value": "no",
    }
    values.update(overrides)
    return SemanticMappingSnapshot.create(**values)  # type: ignore[arg-type]


def test_snapshot_contains_every_exact_semantic_mapping_value() -> None:
    captured = snapshot()

    assert captured.as_dict() == {
        "control_value": "no",
        "covariate_columns": ["promotion", "temperature"],
        "outcome_column": "revenue",
        "spend_column": "spend",
        "time_column": "date",
        "treatment_column": "treated",
        "treatment_value": "yes",
        "unit_column": "market",
    }


def test_equivalent_covariate_collections_have_one_canonical_representation() -> None:
    first = snapshot(covariate_columns=(" Promotion ", "TEMPERATURE"))
    second = snapshot(covariate_columns=("promotion", "temperature"))

    assert first == second
    assert first.canonical_json == second.canonical_json


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("time_column", " "),
        ("unit_column", " "),
        ("treatment_column", " "),
        ("outcome_column", " "),
        ("treatment_value", " "),
        ("control_value", " "),
        ("covariate_columns", ("promotion", "promotion")),
        ("covariate_columns", ("revenue",)),
        ("treatment_value", "no"),
    ],
)
def test_invalid_snapshot_values_are_rejected(field: str, value: object) -> None:
    with pytest.raises(InvalidAnalysisRunError):
        snapshot(**{field: value})


@pytest.mark.parametrize(
    "payload",
    [
        "not-json",
        "[]",
        '{"time_column":"date"}',
        '{"time_column":1}',
    ],
)
def test_malformed_persisted_json_is_rejected(payload: str) -> None:
    with pytest.raises(InvalidAnalysisRunError):
        SemanticMappingSnapshot.from_json(payload)
