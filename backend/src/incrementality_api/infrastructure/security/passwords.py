from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)


class Argon2PasswordHasher:
    """Hash and verify passwords using Argon2id."""

    def __init__(
        self,
        password_hasher: PasswordHasher | None = None,
    ) -> None:
        self._password_hasher = password_hasher or PasswordHasher()

    def hash(self, password: str) -> str:
        if not password:
            raise ValueError("Password cannot be empty.")

        return self._password_hasher.hash(password)

    def verify(
        self,
        *,
        password_hash: str,
        password: str,
    ) -> bool:
        try:
            return self._password_hasher.verify(
                password_hash,
                password,
            )
        except (
            VerifyMismatchError,
            VerificationError,
            InvalidHashError,
        ):
            return False

    def needs_rehash(self, password_hash: str) -> bool:
        try:
            return self._password_hasher.check_needs_rehash(
                password_hash,
            )
        except InvalidHashError:
            return True
