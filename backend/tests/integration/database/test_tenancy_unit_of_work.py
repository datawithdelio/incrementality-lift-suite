from dataclasses import replace

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from incrementality_api.application.tenancy.errors import (
    TenancyConflictError,
)
from incrementality_api.application.tenancy.provision_tenant import (
    ProvisionTenant,
    ProvisionTenantCommand,
)
from incrementality_api.infrastructure.database.models.tenancy import (
    OrganizationModel,
    UserModel,
    WorkspaceMembershipModel,
    WorkspaceModel,
)
from incrementality_api.infrastructure.database.unit_of_work.tenancy import (
    SqlAlchemyTenancyUnitOfWork,
)
from incrementality_api.infrastructure.security.passwords import (
    Argon2PasswordHasher,
)


def build_command() -> ProvisionTenantCommand:
    return ProvisionTenantCommand(
        organization_name="Acme Media",
        organization_slug="acme-media",
        workspace_name="Marketing Science",
        workspace_slug="marketing-science",
        owner_email="owner@example.com",
        owner_display_name="Tina Rincon",
        owner_password="Secure-owner-password-123!",
    )


async def count_rows(
    session_factory: async_sessionmaker[AsyncSession],
    model: type[OrganizationModel | UserModel | WorkspaceModel | WorkspaceMembershipModel],
) -> int:
    async with session_factory() as session:
        result = await session.scalar(select(func.count()).select_from(model))

    return int(result or 0)


@pytest.mark.asyncio
async def test_provision_tenant_persists_all_records(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    unit_of_work = SqlAlchemyTenancyUnitOfWork(
        session_factory=tenancy_session_factory,
    )

    result = await ProvisionTenant(
        password_hasher=Argon2PasswordHasher(),
        unit_of_work=unit_of_work,
    ).execute(build_command())

    assert result.organization_id is not None
    assert result.workspace_id is not None
    assert result.owner_user_id is not None
    assert result.owner_membership_id is not None

    assert (
        await count_rows(
            tenancy_session_factory,
            OrganizationModel,
        )
        == 1
    )

    assert (
        await count_rows(
            tenancy_session_factory,
            UserModel,
        )
        == 1
    )

    assert (
        await count_rows(
            tenancy_session_factory,
            WorkspaceModel,
        )
        == 1
    )

    assert (
        await count_rows(
            tenancy_session_factory,
            WorkspaceMembershipModel,
        )
        == 1
    )


@pytest.mark.asyncio
async def test_duplicate_organization_rolls_back_entire_transaction(
    tenancy_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    first_unit_of_work = SqlAlchemyTenancyUnitOfWork(
        session_factory=tenancy_session_factory,
    )

    await ProvisionTenant(
        password_hasher=Argon2PasswordHasher(),
        unit_of_work=first_unit_of_work,
    ).execute(build_command())

    conflicting_command = replace(
        build_command(),
        workspace_slug="second-workspace",
        owner_email="second-owner@example.com",
        owner_display_name="Second Owner",
    )

    second_unit_of_work = SqlAlchemyTenancyUnitOfWork(
        session_factory=tenancy_session_factory,
    )

    with pytest.raises(TenancyConflictError):
        await ProvisionTenant(
            password_hasher=Argon2PasswordHasher(),
            unit_of_work=second_unit_of_work,
        ).execute(conflicting_command)

    assert (
        await count_rows(
            tenancy_session_factory,
            OrganizationModel,
        )
        == 1
    )

    assert (
        await count_rows(
            tenancy_session_factory,
            UserModel,
        )
        == 1
    )

    assert (
        await count_rows(
            tenancy_session_factory,
            WorkspaceModel,
        )
        == 1
    )

    assert (
        await count_rows(
            tenancy_session_factory,
            WorkspaceMembershipModel,
        )
        == 1
    )
