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
        "postgresql+asyncpg://incrementality:incrementality@localhost:55432/incrementality"
    )

    redis_url: str = "redis://localhost:6379/0"

    dataset_max_upload_bytes: int = 1_073_741_824
    dataset_upload_spool_max_memory_bytes: int = 8_388_608

    dataset_validation_read_chunk_bytes: int = 1_048_576
    dataset_validation_spool_max_memory_bytes: int = 8_388_608

    dataset_validation_job_max_attempts: int = 3
    dataset_validation_job_retry_delay_seconds: int = 30
    dataset_validation_job_claim_timeout_seconds: int = 300

    dataset_validation_worker_poll_interval_seconds: float = 1.0
    dataset_validation_worker_error_retry_seconds: float = 5.0

    analysis_execution_retry_delay_seconds: int = 30
    analysis_execution_worker_poll_interval_seconds: float = 1.0
    analysis_execution_worker_error_retry_seconds: float = 5.0

    report_generation_job_claim_timeout_seconds: int = 300


    report_artifact_reconciliation_interval_seconds: int = 900
    s3_endpoint_url: str = "http://localhost:5001"
    s3_access_key: str = "incrementality"
    s3_secret_key: str = "incrementality-secret"
    s3_bucket: str = "incrementality-artifacts"
    s3_region: str = "us-east-1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
