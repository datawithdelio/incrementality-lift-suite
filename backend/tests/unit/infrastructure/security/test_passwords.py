from incrementality_api.infrastructure.security.passwords import (
    Argon2PasswordHasher,
)


def test_hash_and_verify_password() -> None:
    hasher = Argon2PasswordHasher()

    password_hash = hasher.hash(
        "A-long-password-for-testing-123!",
    )

    assert password_hash.startswith("$argon2id$")
    assert password_hash != "A-long-password-for-testing-123!"

    assert hasher.verify(
        password_hash=password_hash,
        password="A-long-password-for-testing-123!",
    )


def test_incorrect_password_does_not_verify() -> None:
    hasher = Argon2PasswordHasher()

    password_hash = hasher.hash(
        "Correct-password-123!",
    )

    assert not hasher.verify(
        password_hash=password_hash,
        password="Incorrect-password-456!",
    )


def test_password_hashes_use_random_salts() -> None:
    hasher = Argon2PasswordHasher()
    password = "Same-password-123!"

    first_hash = hasher.hash(password)
    second_hash = hasher.hash(password)

    assert first_hash != second_hash

    assert hasher.verify(
        password_hash=first_hash,
        password=password,
    )
    assert hasher.verify(
        password_hash=second_hash,
        password=password,
    )


def test_new_password_hash_does_not_need_rehash() -> None:
    hasher = Argon2PasswordHasher()

    password_hash = hasher.hash(
        "Current-parameters-123!",
    )

    assert not hasher.needs_rehash(password_hash)
