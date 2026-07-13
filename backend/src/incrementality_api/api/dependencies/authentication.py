from datetime import UTC, datetime, timedelta

from incrementality_api.application.authentication.login import (
    Login,
)
from incrementality_api.infrastructure.database.session import (
    get_session_factory,
)
from incrementality_api.infrastructure.database.unit_of_work.authentication import (
    SqlAlchemyAuthenticationUnitOfWork,
)
from incrementality_api.infrastructure.security.passwords import (
    Argon2PasswordHasher,
)
from incrementality_api.infrastructure.security.session_tokens import (
    SecureSessionTokenGenerator,
)


class SystemClock:
    """Provide the current timezone-aware UTC time."""

    def now(self) -> datetime:
        return datetime.now(UTC)


def get_login_service() -> Login:
    """Construct the production login use case."""

    return Login(
        unit_of_work=SqlAlchemyAuthenticationUnitOfWork(
            session_factory=get_session_factory(),
        ),
        password_hasher=Argon2PasswordHasher(),
        token_generator=SecureSessionTokenGenerator(),
        clock=SystemClock(),
        session_lifetime=timedelta(hours=8),
    )
