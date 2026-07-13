from incrementality_api.application.tenancy.provision_tenant import (
    ProvisionTenant,
)
from incrementality_api.infrastructure.database.session import (
    get_session_factory,
)
from incrementality_api.infrastructure.database.unit_of_work.tenancy import (
    SqlAlchemyTenancyUnitOfWork,
)
from incrementality_api.infrastructure.security.passwords import (
    Argon2PasswordHasher,
)


def get_provision_tenant() -> ProvisionTenant:
    """Build one tenant-provisioning use case per request."""

    return ProvisionTenant(
        unit_of_work=SqlAlchemyTenancyUnitOfWork(
            session_factory=get_session_factory(),
        ),
        password_hasher=Argon2PasswordHasher(),
    )
