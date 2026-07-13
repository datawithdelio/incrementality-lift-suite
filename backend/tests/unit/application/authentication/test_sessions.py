from datetime import UTC, datetime, timedelta
from types import TracebackType
from uuid import uuid4

import pytest

from incrementality_api.application.authentication.errors import (
    InvalidSessionTokenError,
)
from incrementality_api.application.authentication.logout import (
    Logout,
)
from incrementality_api.application.authentication.validate_session import (
    ValidateSession,
)
from incrementality_api.domain.authentication.entities import (
    AuthSession,
)

FIXED_NOW = datetime(
    2026,
    7,
    13,
    19,
    0,
    tzinfo=UTC,
)

RAW_TOKEN = "secure-raw-session-token"
TOKEN_HASH = "b" * 64


class FixedClock:
    def now(self) -> datetime:
        return FIXED_NOW


class StubTokenHasher:
    def __init__(self) -> None:
        self.received_token: str | None = None

    def hash_token(self, raw_token: str) -> str:
        self.received_token = raw_token
        return TOKEN_HASH


class FakeSessionRepository:
    def __init__(
        self,
        session: AuthSession | None,
    ) -> None:
        self._session = session
        self.requested_hash: str | None = None
        self.saved: list[AuthSession] = []

    async def get_by_token_hash(
        self,
        token_hash: str,
    ) -> AuthSession | None:
        self.requested_hash = token_hash
        return self._session

    async def save(self, session: AuthSession) -> None:
        self.saved.append(session)


class FakeSessionUnitOfWork:
    def __init__(
        self,
        session: AuthSession | None,
    ) -> None:
        self.sessions = FakeSessionRepository(session)
        self.commit_count = 0
        self.rollback_count = 0

    async def __aenter__(
        self,
    ) -> "FakeSessionUnitOfWork":
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exception, traceback

        if exception_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.commit_count += 1

    async def rollback(self) -> None:
        self.rollback_count += 1


def build_active_session() -> AuthSession:
    return AuthSession.create(
        user_id=uuid4(),
        token_hash=TOKEN_HASH,
        lifetime=timedelta(hours=8),
        now=FIXED_NOW - timedelta(hours=1),
    )


def build_expired_session() -> AuthSession:
    return AuthSession.create(
        user_id=uuid4(),
        token_hash=TOKEN_HASH,
        lifetime=timedelta(hours=8),
        now=FIXED_NOW - timedelta(hours=9),
    )


@pytest.mark.asyncio
async def test_validate_active_session_returns_identity() -> None:
    session = build_active_session()
    unit_of_work = FakeSessionUnitOfWork(session)
    token_hasher = StubTokenHasher()

    service = ValidateSession(
        unit_of_work=unit_of_work,
        token_hasher=token_hasher,
        clock=FixedClock(),
    )

    result = await service.execute(RAW_TOKEN)

    assert token_hasher.received_token == RAW_TOKEN
    assert unit_of_work.sessions.requested_hash == TOKEN_HASH

    assert result.session_id == session.id
    assert result.user_id == session.user_id
    assert result.expires_at == session.expires_at

    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 0


@pytest.mark.asyncio
async def test_validate_rejects_unknown_session() -> None:
    unit_of_work = FakeSessionUnitOfWork(None)

    service = ValidateSession(
        unit_of_work=unit_of_work,
        token_hasher=StubTokenHasher(),
        clock=FixedClock(),
    )

    with pytest.raises(
        InvalidSessionTokenError,
        match="Invalid or expired session",
    ):
        await service.execute(RAW_TOKEN)

    assert unit_of_work.rollback_count == 1


@pytest.mark.asyncio
async def test_validate_rejects_expired_session() -> None:
    unit_of_work = FakeSessionUnitOfWork(
        build_expired_session(),
    )

    service = ValidateSession(
        unit_of_work=unit_of_work,
        token_hasher=StubTokenHasher(),
        clock=FixedClock(),
    )

    with pytest.raises(
        InvalidSessionTokenError,
        match="Invalid or expired session",
    ):
        await service.execute(RAW_TOKEN)

    assert unit_of_work.rollback_count == 1


@pytest.mark.asyncio
async def test_logout_revokes_session_and_commits() -> None:
    original = build_active_session()
    unit_of_work = FakeSessionUnitOfWork(original)

    service = Logout(
        unit_of_work=unit_of_work,
        token_hasher=StubTokenHasher(),
        clock=FixedClock(),
    )

    await service.execute(RAW_TOKEN)

    assert len(unit_of_work.sessions.saved) == 1

    revoked = unit_of_work.sessions.saved[0]

    assert revoked.id == original.id
    assert revoked.revoked_at == FIXED_NOW
    assert original.revoked_at is None

    assert unit_of_work.commit_count == 1
    assert unit_of_work.rollback_count == 0


@pytest.mark.asyncio
async def test_logout_rejects_unknown_session() -> None:
    unit_of_work = FakeSessionUnitOfWork(None)

    service = Logout(
        unit_of_work=unit_of_work,
        token_hasher=StubTokenHasher(),
        clock=FixedClock(),
    )

    with pytest.raises(
        InvalidSessionTokenError,
        match="Invalid or expired session",
    ):
        await service.execute(RAW_TOKEN)

    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 1
    assert unit_of_work.sessions.saved == []
