from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from incrementality_api.application.authentication.errors import (
    InvalidSessionTokenError,
)
from incrementality_api.application.authentication.ports import (
    Clock,
    SessionTokenHasher,
    SessionUnitOfWork,
)

_INVALID_SESSION_MESSAGE = "Invalid or expired session."


@dataclass(frozen=True, slots=True)
class ValidatedSession:
    session_id: UUID
    user_id: UUID
    expires_at: datetime


class ValidateSession:
    """Validate an opaque server-side session token."""

    def __init__(
        self,
        *,
        unit_of_work: SessionUnitOfWork,
        token_hasher: SessionTokenHasher,
        clock: Clock,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._token_hasher = token_hasher
        self._clock = clock

    async def execute(
        self,
        raw_token: str,
    ) -> ValidatedSession:
        token_hash = self._token_hasher.hash_token(
            raw_token,
        )

        async with self._unit_of_work:
            session = await self._unit_of_work.sessions.get_by_token_hash(
                token_hash,
            )

            if session is None or not session.is_active(
                at=self._clock.now(),
            ):
                raise InvalidSessionTokenError(
                    _INVALID_SESSION_MESSAGE,
                )

            return ValidatedSession(
                session_id=session.id,
                user_id=session.user_id,
                expires_at=session.expires_at,
            )
