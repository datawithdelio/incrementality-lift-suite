from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Incrementality & Lift Measurement Suite"
    app_environment: str = "development"
    app_debug: bool = False
    app_api_v1_prefix: str = "/api/v1"

    database_url: str = (
        "postgresql+asyncpg://incrementality:"
        "incrementality@localhost:5432/incrementality"
    )

    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "incrementality"
    s3_secret_key: str = "incrementality-secret"
    s3_bucket: str = "incrementality-artifacts"
    s3_region: str = "us-east-1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
