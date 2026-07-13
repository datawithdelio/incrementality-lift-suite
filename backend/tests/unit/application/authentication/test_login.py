from datetime import UTC, datetime, timedelta
from types import TracebackType
from uuid import uuid4

import pytest

from incrementality_api.application.authentication.errors import (
    InvalidCredentialsError,
)
from incrementality_api.application.authentication.login import (
    Login,
    LoginCommand,
)
from incrementality_api.application.authentication.ports import (
    IssuedSessionToken,
    LoginUser,
)
from incrementality_api.domain.authentication.entities import (
    AuthSession,
    PasswordCredential,
)

FIXED_NOW = datetime(
    2026,
    7,
    13,
    17,
    30,
    tzinfo=UTC,
)

PASSWORD_HASH = "$argon2id$stored-password-hash"
TOKEN_HASH = "a" * 64
RAW_TOKEN = "secure-raw-session-token"


class FixedClock:
    def now(self) -> datetime:
        return FIXED_NOW


class FakeLoginUserRepository:
    def __init__(self, user: LoginUser | None) -> None:
        self._user = user
        self.requested_email: str | None = None

    async def get_by_email(
        self,
        email: str,
    ) -> LoginUser | None:
        self.requested_email = email
        return self._user


class FakeCredentialRepository:
    def __init__(
        self,
        credential: PasswordCredential | None,
    ) -> None:
        self._credential = credential

    async def get_by_user_id(
        self,
        user_id,
    ) -> PasswordCredential | None:
        del user_id
        return self._credential


class FakeAuthSessionRepository:
    def __init__(self) -> None:
        self.saved: list[AuthSession] = []

    async def add(self, session: AuthSession) -> None:
        self.saved.append(session)


class FakeAuthenticationUnitOfWork:
    def __init__(
        self,
        *,
        user: LoginUser | None,
        credential: PasswordCredential | None,
    ) -> None:
        self.users = FakeLoginUserRepository(user)
        self.credentials = FakeCredentialRepository(
            credential,
        )
        self.sessions = FakeAuthSessionRepository()

        self.commit_count = 0
        self.rollback_count = 0

    async def __aenter__(
        self,
    ) -> "FakeAuthenticationUnitOfWork":
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exception_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.commit_count += 1

    async def rollback(self) -> None:
        self.rollback_count += 1


class StubPasswordHasher:
    def __init__(self, *, matches: bool) -> None:
        self._matches = matches
        self.received_hash: str | None = None
        self.received_password: str | None = None

    def hash(self, password: str) -> str:
        raise AssertionError("Hash should not be called during login.")

    def verify(
        self,
        *,
        password_hash: str,
        password: str,
    ) -> bool:
        self.received_hash = password_hash
        self.received_password = password
        return self._matches

    def needs_rehash(self, password_hash: str) -> bool:
        del password_hash
        return False


class StubSessionTokenGenerator:
    def issue(self) -> IssuedSessionToken:
        return IssuedSessionToken(
            raw_token=RAW_TOKEN,
            token_hash=TOKEN_HASH,
        )

    def hash_token(self, raw_token: str) -> str:
        del raw_token
        return TOKEN_HASH


def build_identity() -> tuple[LoginUser, PasswordCredential]:
    user = LoginUser(
        id=uuid4(),
        email="owner@example.com",
    )

    credential = PasswordCredential.create(
        user_id=user.id,
        password_hash=PASSWORD_HASH,
        now=FIXED_NOW,
    )

    return user, credential


@pytest.mark.asyncio
async def test_login_creates_session_and_returns_raw_token() -> None:
    user, credential = build_identity()

    unit_of_work = FakeAuthenticationUnitOfWork(
        user=user,
        credential=credential,
    )

    hasher = StubPasswordHasher(matches=True)

    service = Login(
        unit_of_work=unit_of_work,
        password_hasher=hasher,
        token_generator=StubSessionTokenGenerator(),
        clock=FixedClock(),
        session_lifetime=timedelta(hours=8),
    )

    result = await service.execute(
        LoginCommand(
            email="  OWNER@EXAMPLE.COM  ",
            password="Correct-password-123!",
        )
    )

    assert unit_of_work.users.requested_email == ("owner@example.com")

    assert hasher.received_hash == PASSWORD_HASH
    assert hasher.received_password == ("Correct-password-123!")

    assert len(unit_of_work.sessions.saved) == 1

    session = unit_of_work.sessions.saved[0]

    assert session.user_id == user.id
    assert session.token_hash == TOKEN_HASH
    assert session.created_at == FIXED_NOW
    assert session.expires_at == (FIXED_NOW + timedelta(hours=8))

    assert result.user_id == user.id
    assert result.raw_session_token == RAW_TOKEN
    assert result.expires_at == session.expires_at

    assert unit_of_work.commit_count == 1
    assert unit_of_work.rollback_count == 0


@pytest.mark.asyncio
async def test_login_rejects_unknown_email_generically() -> None:
    unit_of_work = FakeAuthenticationUnitOfWork(
        user=None,
        credential=None,
    )

    service = Login(
        unit_of_work=unit_of_work,
        password_hasher=StubPasswordHasher(
            matches=False,
        ),
        token_generator=StubSessionTokenGenerator(),
        clock=FixedClock(),
    )

    with pytest.raises(
        InvalidCredentialsError,
        match="Invalid email or password",
    ):
        await service.execute(
            LoginCommand(
                email="missing@example.com",
                password="Any-password-123!",
            )
        )

    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 1
    assert unit_of_work.sessions.saved == []


@pytest.mark.asyncio
async def test_login_rejects_wrong_password_generically() -> None:
    user, credential = build_identity()

    unit_of_work = FakeAuthenticationUnitOfWork(
        user=user,
        credential=credential,
    )

    service = Login(
        unit_of_work=unit_of_work,
        password_hasher=StubPasswordHasher(
            matches=False,
        ),
        token_generator=StubSessionTokenGenerator(),
        clock=FixedClock(),
    )

    with pytest.raises(
        InvalidCredentialsError,
        match="Invalid email or password",
    ):
        await service.execute(
            LoginCommand(
                email=user.email,
                password="Wrong-password-456!",
            )
        )

    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 1
    assert unit_of_work.sessions.saved == []


@pytest.mark.asyncio
async def test_login_rejects_user_without_credential() -> None:
    user, _ = build_identity()

    unit_of_work = FakeAuthenticationUnitOfWork(
        user=user,
        credential=None,
    )

    service = Login(
        unit_of_work=unit_of_work,
        password_hasher=StubPasswordHasher(
            matches=False,
        ),
        token_generator=StubSessionTokenGenerator(),
        clock=FixedClock(),
    )

    with pytest.raises(
        InvalidCredentialsError,
        match="Invalid email or password",
    ):
        await service.execute(
            LoginCommand(
                email=user.email,
                password="Any-password-123!",
            )
        )

    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 1
    assert unit_of_work.sessions.saved == []
