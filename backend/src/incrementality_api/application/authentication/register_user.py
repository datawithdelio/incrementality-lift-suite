from dataclasses import dataclass
from uuid import UUID

from incrementality_api.application.authentication.ports import (
    PasswordHasher,
)
from incrementality_api.application.tenancy.ports import (
    TenancyUnitOfWork,
)
from incrementality_api.domain.authentication.entities import (
    PasswordCredential,
)
from incrementality_api.domain.tenancy.entities import (
    User,
)


@dataclass(frozen=True, slots=True)
class RegisterUserCommand:
    email: str
    display_name: str
    password: str


@dataclass(frozen=True, slots=True)
class RegisteredUser:
    user_id: UUID


class RegisterUser:
    """Create an account without provisioning workspace resources."""

    def __init__(
        self,
        *,
        unit_of_work: TenancyUnitOfWork,
        password_hasher: PasswordHasher,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._password_hasher = password_hasher

    async def execute(
        self,
        command: RegisterUserCommand,
    ) -> RegisteredUser:
        user = User.create(
            email=command.email,
            display_name=command.display_name,
        )

        credential = PasswordCredential.create(
            user_id=user.id,
            password_hash=self._password_hasher.hash(
                command.password,
            ),
        )

        async with self._unit_of_work:
            await self._unit_of_work.users.add(user)
            await self._unit_of_work.credentials.add(
                credential,
            )
            await self._unit_of_work.commit()

        return RegisteredUser(
            user_id=user.id,
        )
