from incrementality_api.infrastructure.database.repositories.data_products import (
    _report_diagnostics_snapshot,
)


def test_report_diagnostics_snapshot_carries_persisted_sample_size() -> None:
    original = {
        "effective_sample_size": 4929,
        "reliability": "strong",
    }

    snapshot = _report_diagnostics_snapshot(original, 5000)

    assert snapshot["sample_size"] == 5000
    assert snapshot["effective_sample_size"] == 4929
    assert original == {
        "effective_sample_size": 4929,
        "reliability": "strong",
    }


def test_report_diagnostics_snapshot_preserves_explicit_sample_size() -> None:
    snapshot = _report_diagnostics_snapshot(
        {
            "sample_size": 123,
            "effective_sample_size": 120,
        },
        5000,
    )

    assert snapshot["sample_size"] == 123
