from uuid import UUID

from httpx import ASGITransport, AsyncClient

from incrementality_api.api.dependencies.tenancy import (
    get_provision_tenant,
)
from incrementality_api.application.tenancy.errors import (
    TenancyConflictError,
)
from incrementality_api.application.tenancy.provision_tenant import (
    ProvisionedTenant,
    ProvisionTenantCommand,
)
from incrementality_api.main import create_app

ORGANIZATION_ID = UUID("11111111-1111-1111-1111-111111111111")
WORKSPACE_ID = UUID("22222222-2222-2222-2222-222222222222")
USER_ID = UUID("33333333-3333-3333-3333-333333333333")
MEMBERSHIP_ID = UUID("44444444-4444-4444-4444-444444444444")


class SuccessfulProvisionTenant:
    def __init__(self) -> None:
        self.received_command: ProvisionTenantCommand | None = None

    async def execute(
        self,
        command: ProvisionTenantCommand,
    ) -> ProvisionedTenant:
        self.received_command = command

        return ProvisionedTenant(
            organization_id=ORGANIZATION_ID,
            workspace_id=WORKSPACE_ID,
            owner_user_id=USER_ID,
            owner_membership_id=MEMBERSHIP_ID,
        )


class ConflictingProvisionTenant:
    async def execute(
        self,
        command: ProvisionTenantCommand,
    ) -> ProvisionedTenant:
        del command

        raise TenancyConflictError("Tenant data conflicts with an existing record.")


def build_payload() -> dict[str, str]:
    return {
        "organization_name": "Acme Media",
        "organization_slug": "acme-media",
        "workspace_name": "Marketing Science",
        "workspace_slug": "marketing-science",
        "owner_email": "owner@example.com",
        "owner_display_name": "Tina Rincon",
        "owner_password": "Secure-owner-password-123!",
    }


async def test_provision_tenant_returns_created_resources() -> None:
    service = SuccessfulProvisionTenant()
    app = create_app()

    app.dependency_overrides[get_provision_tenant] = lambda: service

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/tenants",
            json=build_payload(),
        )

    assert response.status_code == 201
    assert response.json() == {
        "organization_id": str(ORGANIZATION_ID),
        "workspace_id": str(WORKSPACE_ID),
        "owner_user_id": str(USER_ID),
        "owner_membership_id": str(MEMBERSHIP_ID),
    }

    assert service.received_command == ProvisionTenantCommand(
        **build_payload(),
    )


async def test_provision_tenant_returns_conflict() -> None:
    app = create_app()

    app.dependency_overrides[get_provision_tenant] = lambda: ConflictingProvisionTenant()

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/tenants",
            json=build_payload(),
        )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Tenant data conflicts with an existing record.",
    }
