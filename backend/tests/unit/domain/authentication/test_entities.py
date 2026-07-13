from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from incrementality_api.domain.authentication.entities import (
    AuthSession,
    PasswordCredential,
)
from incrementality_api.domain.authentication.errors import (
    InvalidCredentialError,
    InvalidSessionError,
)

FIXED_NOW = datetime(
    2026,
    7,
    13,
    17,
    0,
    tzinfo=UTC,
)

VALID_TOKEN_HASH = "a" * 64


def test_create_password_credential() -> None:
    user_id = uuid4()

    credential = PasswordCredential.create(
        user_id=user_id,
        password_hash="$argon2id$example-password-hash",
        now=FIXED_NOW,
    )

    assert credential.user_id == user_id
    assert credential.password_hash == "$argon2id$example-password-hash"
    assert credential.created_at == FIXED_NOW
    assert credential.updated_at == FIXED_NOW


def test_password_credential_rejects_blank_hash() -> None:
    with pytest.raises(InvalidCredentialError):
        PasswordCredential.create(
            user_id=uuid4(),
            password_hash="   ",
            now=FIXED_NOW,
        )


def test_create_auth_session_with_expiration() -> None:
    user_id = uuid4()

    session = AuthSession.create(
        user_id=user_id,
        token_hash=VALID_TOKEN_HASH.upper(),
        lifetime=timedelta(hours=8),
        now=FIXED_NOW,
    )

    assert isinstance(session.id, UUID)
    assert session.user_id == user_id
    assert session.token_hash == VALID_TOKEN_HASH
    assert session.created_at == FIXED_NOW
    assert session.expires_at == FIXED_NOW + timedelta(hours=8)
    assert session.revoked_at is None


def test_session_rejects_invalid_token_hash() -> None:
    with pytest.raises(InvalidSessionError):
        AuthSession.create(
            user_id=uuid4(),
            token_hash="raw-session-token",
            lifetime=timedelta(hours=8),
            now=FIXED_NOW,
        )


def test_session_rejects_non_positive_lifetime() -> None:
    with pytest.raises(InvalidSessionError):
        AuthSession.create(
            user_id=uuid4(),
            token_hash=VALID_TOKEN_HASH,
            lifetime=timedelta(seconds=0),
            now=FIXED_NOW,
        )


def test_session_is_active_before_expiration() -> None:
    session = AuthSession.create(
        user_id=uuid4(),
        token_hash=VALID_TOKEN_HASH,
        lifetime=timedelta(hours=8),
        now=FIXED_NOW,
    )

    assert session.is_active(
        at=FIXED_NOW + timedelta(hours=7),
    )
    assert not session.is_active(
        at=FIXED_NOW + timedelta(hours=8),
    )


def test_revoked_session_is_not_active() -> None:
    session = AuthSession.create(
        user_id=uuid4(),
        token_hash=VALID_TOKEN_HASH,
        lifetime=timedelta(hours=8),
        now=FIXED_NOW,
    )

    revoked_session = session.revoke(
        at=FIXED_NOW + timedelta(hours=1),
    )

    assert session.revoked_at is None
    assert revoked_session.revoked_at == FIXED_NOW + timedelta(hours=1)
    assert not revoked_session.is_active(
        at=FIXED_NOW + timedelta(hours=2),
    )
