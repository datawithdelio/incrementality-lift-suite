from types import SimpleNamespace

from incrementality_api import main


def test_create_app_uses_configured_application_version(
    monkeypatch,
) -> None:
    settings = SimpleNamespace(
        app_name="Incrementality Test",
        app_version="9.8.7",
        app_debug=False,
        app_api_v1_prefix="/api/v1",
    )

    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: settings,
    )

    application = main.create_app()

    assert application.title == "Incrementality Test"
    assert application.version == "9.8.7"
