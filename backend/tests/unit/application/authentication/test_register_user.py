from types import TracebackType

import pytest

from incrementality_api.application.authentication.register_user import (
    RegisterUser,
    RegisterUserCommand,
)
from incrementality_api.domain.authentication.entities import (
    PasswordCredential,
)
from incrementality_api.domain.tenancy.entities import (
    User,
)

PASSWORD = "Secure-user-password-123!"
PASSWORD_HASH = "$argon2id$registered-user-password"


class RecordingRepository:
    def __init__(self) -> None:
        self.saved: list[object] = []

    async def add(self, item: object) -> None:
        self.saved.append(item)


class FakeRegistrationUnitOfWork:
    def __init__(self) -> None:
        self.organizations = RecordingRepository()
        self.users = RecordingRepository()
        self.credentials = RecordingRepository()
        self.workspaces = RecordingRepository()
        self.memberships = RecordingRepository()

        self.commit_count = 0
        self.rollback_count = 0

    async def __aenter__(
        self,
    ) -> "FakeRegistrationUnitOfWork":
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


class StubPasswordHasher:
    def __init__(self) -> None:
        self.received_password: str | None = None

    def hash(self, password: str) -> str:
        self.received_password = password
        return PASSWORD_HASH

    def verify(
        self,
        *,
        password_hash: str,
        password: str,
    ) -> bool:
        del password_hash, password

        raise AssertionError(
            "Password verification is not used during registration."
        )

    def needs_rehash(self, password_hash: str) -> bool:
        del password_hash

        raise AssertionError(
            "Rehash checks are not used during registration."
        )


@pytest.mark.asyncio
async def test_register_user_creates_only_user_and_credential() -> None:
    unit_of_work = FakeRegistrationUnitOfWork()
    password_hasher = StubPasswordHasher()

    service = RegisterUser(
        unit_of_work=unit_of_work,
        password_hasher=password_hasher,
    )

    result = await service.execute(
        RegisterUserCommand(
            email="new-user@example.com",
            display_name="Avery Stone",
            password=PASSWORD,
        )
    )

    assert len(unit_of_work.users.saved) == 1
    assert len(unit_of_work.credentials.saved) == 1

    assert unit_of_work.organizations.saved == []
    assert unit_of_work.workspaces.saved == []
    assert unit_of_work.memberships.saved == []

    user = unit_of_work.users.saved[0]
    credential = unit_of_work.credentials.saved[0]

    assert isinstance(user, User)
    assert isinstance(credential, PasswordCredential)

    assert user.email == "new-user@example.com"
    assert user.display_name == "Avery Stone"

    assert password_hasher.received_password == PASSWORD
    assert credential.user_id == user.id
    assert credential.password_hash == PASSWORD_HASH
    assert credential.password_hash != PASSWORD

    assert result.user_id == user.id

    assert unit_of_work.commit_count == 1
    assert unit_of_work.rollback_count == 0
