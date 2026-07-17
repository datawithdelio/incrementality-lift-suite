from incrementality_api.core.config import Settings


def test_settings_load_runtime_version_metadata(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "APP_VERSION",
        "0.1.0",
    )
    monkeypatch.setenv(
        "SOURCE_REVISION",
        "a" * 40,
    )

    settings = Settings(
        _env_file=None,
    )

    assert settings.app_version == "0.1.0"
    assert settings.source_revision == "a" * 40
