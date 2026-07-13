from incrementality_api.application.authentication.errors import (
    InvalidSessionTokenError,
)
from incrementality_api.application.authentication.ports import (
    Clock,
    SessionTokenHasher,
    SessionUnitOfWork,
)

_INVALID_SESSION_MESSAGE = "Invalid or expired session."


class Logout:
    """Revoke a server-side authentication session."""

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

    async def execute(self, raw_token: str) -> None:
        token_hash = self._token_hasher.hash_token(
            raw_token,
        )

        async with self._unit_of_work:
            session = await self._unit_of_work.sessions.get_by_token_hash(
                token_hash,
            )

            if session is None:
                raise InvalidSessionTokenError(
                    _INVALID_SESSION_MESSAGE,
                )

            revoked_session = session.revoke(
                at=self._clock.now(),
            )

            await self._unit_of_work.sessions.save(
                revoked_session,
            )

            await self._unit_of_work.commit()
