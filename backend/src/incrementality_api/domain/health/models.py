from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping


class HealthState(StrEnum):
    OK = "ok"
    NOT_READY = "not_ready"


@dataclass(frozen=True, slots=True)
class HealthCheckResult:
    status: HealthState
    checks: Mapping[str, str]
