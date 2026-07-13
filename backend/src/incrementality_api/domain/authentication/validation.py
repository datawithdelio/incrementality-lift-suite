import re
from datetime import UTC, datetime, timedelta

from incrementality_api.domain.authentication.errors import (
    InvalidCredentialError,
    InvalidSessionError,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def resolve_credential_time(value: datetime | None) -> datetime:
    resolved = value or datetime.now(UTC)

    if resolved.utcoffset() is None:
        raise InvalidCredentialError("Credential timestamps must include a timezone.")

    return resolved


def resolve_session_time(value: datetime | None) -> datetime:
    resolved = value or datetime.now(UTC)

    if resolved.utcoffset() is None:
        raise InvalidSessionError("Session timestamps must include a timezone.")

    return resolved


def normalize_password_hash(value: str) -> str:
    normalized = value.strip()

    if not normalized:
        raise InvalidCredentialError("Password hash cannot be blank.")

    return normalized


def normalize_token_hash(value: str) -> str:
    normalized = value.strip().lower()

    if not _SHA256_PATTERN.fullmatch(normalized):
        raise InvalidSessionError("Session token hash must be a 64-character SHA-256 digest.")

    return normalized


def validate_session_lifetime(lifetime: timedelta) -> None:
    if lifetime <= timedelta(0):
        raise InvalidSessionError("Session lifetime must be greater than zero.")
