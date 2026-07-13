from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from incrementality_api.application.authentication.errors import (
    InvalidCredentialsError,
)
from incrementality_api.application.authentication.ports import (
    AuthenticationUnitOfWork,
    Clock,
    PasswordHasher,
    SessionTokenGenerator,
)
from incrementality_api.domain.authentication.entities import (
    AuthSession,
)

_INVALID_CREDENTIALS_MESSAGE = "Invalid email or password."


@dataclass(frozen=True, slots=True)
class LoginCommand:
    email: str
    password: str


@dataclass(frozen=True, slots=True)
class LoginResult:
    user_id: UUID
    raw_session_token: str
    expires_at: datetime


class Login:
    """Authenticate a user and create a revocable server-side session."""

    def __init__(
        self,
        *,
        unit_of_work: AuthenticationUnitOfWork,
        password_hasher: PasswordHasher,
        token_generator: SessionTokenGenerator,
        clock: Clock,
        session_lifetime: timedelta = timedelta(hours=8),
    ) -> None:
        self._unit_of_work = unit_of_work
        self._password_hasher = password_hasher
        self._token_generator = token_generator
        self._clock = clock
        self._session_lifetime = session_lifetime

    async def execute(
        self,
        command: LoginCommand,
    ) -> LoginResult:
        normalized_email = command.email.strip().lower()

        async with self._unit_of_work:
            user = await self._unit_of_work.users.get_by_email(
                normalized_email,
            )

            if user is None:
                raise InvalidCredentialsError(
                    _INVALID_CREDENTIALS_MESSAGE,
                )

            credential = await self._unit_of_work.credentials.get_by_user_id(
                user.id,
            )

            if credential is None:
                raise InvalidCredentialsError(
                    _INVALID_CREDENTIALS_MESSAGE,
                )

            password_matches = self._password_hasher.verify(
                password_hash=credential.password_hash,
                password=command.password,
            )

            if not password_matches:
                raise InvalidCredentialsError(
                    _INVALID_CREDENTIALS_MESSAGE,
                )

            issued_token = self._token_generator.issue()

            session = AuthSession.create(
                user_id=user.id,
                token_hash=issued_token.token_hash,
                lifetime=self._session_lifetime,
                now=self._clock.now(),
            )

            await self._unit_of_work.sessions.add(session)
            await self._unit_of_work.commit()

        return LoginResult(
            user_id=user.id,
            raw_session_token=issued_token.raw_token,
            expires_at=session.expires_at,
        )
