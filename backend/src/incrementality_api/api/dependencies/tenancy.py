from incrementality_api.application.tenancy.provision_tenant import (
    ProvisionTenant,
)
from incrementality_api.infrastructure.database.session import (
    get_session_factory,
)
from incrementality_api.infrastructure.database.unit_of_work.tenancy import (
    SqlAlchemyTenancyUnitOfWork,
)


def get_provision_tenant() -> ProvisionTenant:
    """
    Build one tenant-provisioning use case per API request.

    The Unit of Work creates its database session only when the
    application use case enters the transaction boundary.
    """

    unit_of_work = SqlAlchemyTenancyUnitOfWork(
        session_factory=get_session_factory(),
    )

    return ProvisionTenant(
        unit_of_work=unit_of_work,
    )
