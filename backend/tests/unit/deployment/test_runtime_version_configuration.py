from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


def test_backend_containers_receive_configured_runtime_versions() -> None:
    compose = (REPOSITORY_ROOT / "docker-compose.yml").read_text()
    dockerfile = (REPOSITORY_ROOT / "backend" / "Dockerfile").read_text()

    assert "APP_VERSION: ${APP_VERSION:?APP_VERSION must be set}" in compose
    assert "SOURCE_REVISION: ${SOURCE_REVISION:?SOURCE_REVISION must be set}" in compose
    assert "APP_VERSION: ${APP_VERSION:?APP_VERSION must be set}" in compose.split(
        "x-backend-environment:",
        maxsplit=1,
    )[1]
    assert "SOURCE_REVISION: ${SOURCE_REVISION:?SOURCE_REVISION must be set}" in compose.split(
        "x-backend-environment:",
        maxsplit=1,
    )[1]

    assert "ARG APP_VERSION" in dockerfile
    assert "ARG SOURCE_REVISION" in dockerfile
    assert "ENV APP_VERSION=${APP_VERSION}" in dockerfile
    assert "ENV SOURCE_REVISION=${SOURCE_REVISION}" in dockerfile
