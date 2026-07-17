from types import SimpleNamespace

from incrementality_api.api.dependencies import analysis_runs


def test_queue_service_injects_runtime_versions(
    monkeypatch,
) -> None:
    settings = SimpleNamespace(
        app_version="0.1.0",
        source_revision="a" * 40,
    )
    sessions = object()

    monkeypatch.setattr(
        analysis_runs,
        "get_settings",
        lambda: settings,
        raising=False,
    )
    monkeypatch.setattr(
        analysis_runs,
        "get_session_factory",
        lambda: sessions,
    )
    monkeypatch.setattr(
        analysis_runs,
        "SqlAlchemyAnalysisRunUnitOfWork",
        lambda *, session_factory: object(),
    )
    monkeypatch.setattr(
        analysis_runs,
        "SqlAlchemyAnalysisQualityGate",
        lambda session_factory: object(),
    )

    service = analysis_runs.get_queue_analysis_run_service()

    assert service._application_version == "0.1.0"
    assert service._source_revision == "a" * 40
