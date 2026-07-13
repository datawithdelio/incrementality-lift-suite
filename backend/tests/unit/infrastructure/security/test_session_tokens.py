import re

from incrementality_api.infrastructure.security.session_tokens import (
    SecureSessionTokenGenerator,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def test_issue_returns_raw_token_and_sha256_digest() -> None:
    generator = SecureSessionTokenGenerator()

    issued = generator.issue()

    assert issued.raw_token
    assert issued.raw_token != issued.token_hash
    assert _SHA256_PATTERN.fullmatch(issued.token_hash)

    assert generator.hash_token(issued.raw_token) == issued.token_hash


def test_each_issued_session_token_is_unique() -> None:
    generator = SecureSessionTokenGenerator()

    first = generator.issue()
    second = generator.issue()

    assert first.raw_token != second.raw_token
    assert first.token_hash != second.token_hash


def test_hash_token_is_deterministic() -> None:
    generator = SecureSessionTokenGenerator()
    raw_token = "test-session-token"

    first_digest = generator.hash_token(raw_token)
    second_digest = generator.hash_token(raw_token)

    assert first_digest == second_digest
    assert _SHA256_PATTERN.fullmatch(first_digest)
