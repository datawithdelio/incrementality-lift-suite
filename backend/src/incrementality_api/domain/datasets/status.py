from enum import StrEnum


class DatasetStatus(StrEnum):
    PENDING_UPLOAD = "pending_upload"
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    READY = "ready"
    FAILED = "failed"
