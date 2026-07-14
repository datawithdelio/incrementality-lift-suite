from enum import StrEnum


class AnalysisExecutionJobStatus(StrEnum):
    """Durable worker lifecycle state for an analysis execution."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    DEAD_LETTER = "dead_letter"
