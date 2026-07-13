from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Self
from uuid import UUID, uuid4

from incrementality_api.domain.authentication.errors import (
    InvalidSessionError,
)
from incrementality_api.domain.authentication.validation import (
    normalize_password_hash,
    normalize_token_hash,
    resolve_credential_time,
    resolve_session_time,
    validate_session_lifetime,
)


@dataclass(frozen=True, slots=True)
class PasswordCredential:
    user_id: UUID
    password_hash: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        password_hash: str,
        now: datetime | None = None,
    ) -> Self:
        timestamp = resolve_credential_time(now)

        return cls(
            user_id=user_id,
            password_hash=normalize_password_hash(password_hash),
            created_at=timestamp,
            updated_at=timestamp,
        )


@dataclass(frozen=True, slots=True)
class AuthSession:
    id: UUID
    user_id: UUID
    token_hash: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        token_hash: str,
        lifetime: timedelta,
        now: datetime | None = None,
    ) -> Self:
        validate_session_lifetime(lifetime)
        timestamp = resolve_session_time(now)

        return cls(
            id=uuid4(),
            user_id=user_id,
            token_hash=normalize_token_hash(token_hash),
            created_at=timestamp,
            expires_at=timestamp + lifetime,
            revoked_at=None,
        )

    def is_active(
        self,
        *,
        at: datetime | None = None,
    ) -> bool:
        timestamp = resolve_session_time(at)

        if timestamp < self.created_at:
            return False

        if timestamp >= self.expires_at:
            return False

        return self.revoked_at is None or timestamp < self.revoked_at

    def revoke(
        self,
        *,
        at: datetime | None = None,
    ) -> Self:
        timestamp = resolve_session_time(at)

        if timestamp < self.created_at:
            raise InvalidSessionError("A session cannot be revoked before it was created.")

        if self.revoked_at is not None:
            return self

        return replace(
            self,
            revoked_at=timestamp,
        )
