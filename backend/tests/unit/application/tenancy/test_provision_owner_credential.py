from types import TracebackType

import pytest

from incrementality_api.application.tenancy.provision_tenant import (
    ProvisionTenant,
    ProvisionTenantCommand,
)
from incrementality_api.domain.authentication.entities import (
    PasswordCredential,
)
from incrementality_api.domain.tenancy.entities import User

OWNER_PASSWORD = "Secure-owner-password-123!"
PASSWORD_HASH = "$argon2id$hashed-owner-password"


class RecordingRepository:
    def __init__(self) -> None:
        self.saved: list[object] = []

    async def add(self, item: object) -> None:
        self.saved.append(item)


class FakeCredentialRepository:
    def __init__(
        self,
        *,
        should_fail: bool = False,
    ) -> None:
        self.saved: list[PasswordCredential] = []
        self._should_fail = should_fail

    async def add(
        self,
        credential: PasswordCredential,
    ) -> None:
        if self._should_fail:
            raise RuntimeError("Credential persistence failed.")

        self.saved.append(credential)


class FakeTenancyUnitOfWork:
    def __init__(
        self,
        *,
        credential_should_fail: bool = False,
    ) -> None:
        self.organizations = RecordingRepository()
        self.users = RecordingRepository()
        self.credentials = FakeCredentialRepository(
            should_fail=credential_should_fail,
        )
        self.workspaces = RecordingRepository()
        self.memberships = RecordingRepository()

        self.commit_count = 0
        self.rollback_count = 0

    async def __aenter__(
        self,
    ) -> "FakeTenancyUnitOfWork":
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

        raise AssertionError("Password verification is not used during provisioning.")

    def needs_rehash(self, password_hash: str) -> bool:
        del password_hash

        raise AssertionError("Rehash checks are not used during provisioning.")


def build_command() -> ProvisionTenantCommand:
    return ProvisionTenantCommand(
        organization_name="Acme Media",
        organization_slug="acme-media",
        workspace_name="Marketing Science",
        workspace_slug="marketing-science",
        owner_email="owner@example.com",
        owner_display_name="Tina Rincon",
        owner_password=OWNER_PASSWORD,
    )


@pytest.mark.asyncio
async def test_provision_tenant_hashes_and_saves_owner_credential() -> None:
    unit_of_work = FakeTenancyUnitOfWork()
    password_hasher = StubPasswordHasher()

    service = ProvisionTenant(
        unit_of_work=unit_of_work,
        password_hasher=password_hasher,
    )

    result = await service.execute(build_command())

    assert password_hasher.received_password == OWNER_PASSWORD
    assert len(unit_of_work.credentials.saved) == 1
    assert len(unit_of_work.users.saved) == 1

    owner = unit_of_work.users.saved[0]
    credential = unit_of_work.credentials.saved[0]

    assert isinstance(owner, User)
    assert credential.user_id == owner.id
    assert credential.user_id == result.owner_user_id
    assert credential.password_hash == PASSWORD_HASH
    assert credential.password_hash != OWNER_PASSWORD

    assert unit_of_work.commit_count == 1
    assert unit_of_work.rollback_count == 0


@pytest.mark.asyncio
async def test_credential_failure_rolls_back_tenant_provisioning() -> None:
    unit_of_work = FakeTenancyUnitOfWork(
        credential_should_fail=True,
    )

    service = ProvisionTenant(
        unit_of_work=unit_of_work,
        password_hasher=StubPasswordHasher(),
    )

    with pytest.raises(
        RuntimeError,
        match="Credential persistence failed",
    ):
        await service.execute(build_command())

    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 1
