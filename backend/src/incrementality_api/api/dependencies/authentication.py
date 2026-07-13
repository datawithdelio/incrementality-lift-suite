from datetime import UTC, datetime, timedelta

from incrementality_api.application.authentication.login import (
    Login,
)
from incrementality_api.application.authentication.logout import (
    Logout,
)
from incrementality_api.application.authentication.validate_session import (
    ValidateSession,
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


def _build_authentication_unit_of_work() -> SqlAlchemyAuthenticationUnitOfWork:
    return SqlAlchemyAuthenticationUnitOfWork(
        session_factory=get_session_factory(),
    )


def get_login_service() -> Login:
    """Construct the production login use case."""

    return Login(
        unit_of_work=_build_authentication_unit_of_work(),
        password_hasher=Argon2PasswordHasher(),
        token_generator=SecureSessionTokenGenerator(),
        clock=SystemClock(),
        session_lifetime=timedelta(hours=8),
    )


def get_validate_session_service() -> ValidateSession:
    """Construct the production session-validation use case."""

    return ValidateSession(
        unit_of_work=_build_authentication_unit_of_work(),
        token_hasher=SecureSessionTokenGenerator(),
        clock=SystemClock(),
    )


def get_logout_service() -> Logout:
    """Construct the production logout use case."""

    return Logout(
        unit_of_work=_build_authentication_unit_of_work(),
        token_hasher=SecureSessionTokenGenerator(),
        clock=SystemClock(),
    )
