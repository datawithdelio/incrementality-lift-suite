from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from incrementality_api.api.dependencies.tenancy import (
    get_provision_tenant,
)
from incrementality_api.api.v1.schemas.tenancy import (
    ProvisionTenantRequest,
    ProvisionTenantResponse,
)
from incrementality_api.application.tenancy.errors import (
    TenancyConflictError,
)
from incrementality_api.application.tenancy.provision_tenant import (
    ProvisionTenant,
    ProvisionTenantCommand,
)
from incrementality_api.domain.tenancy.errors import (
    TenancyDomainError,
)

router = APIRouter(
    prefix="/tenants",
    tags=["tenants"],
)

ProvisionTenantDependency = Annotated[
    ProvisionTenant,
    Depends(get_provision_tenant),
]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ProvisionTenantResponse,
    summary="Provision a new organization and workspace",
    responses={
        status.HTTP_409_CONFLICT: {
            "description": "Organization, workspace, or user already exists.",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Tenant information is invalid.",
        },
    },
)
async def provision_tenant(
    request: ProvisionTenantRequest,
    service: ProvisionTenantDependency,
) -> ProvisionTenantResponse:
    command = ProvisionTenantCommand(
        organization_name=request.organization_name,
        organization_slug=request.organization_slug,
        workspace_name=request.workspace_name,
        workspace_slug=request.workspace_slug,
        owner_email=request.owner_email,
        owner_display_name=request.owner_display_name,
        owner_password=request.owner_password,
    )

    try:
        result = await service.execute(command)
    except TenancyConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except TenancyDomainError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error

    return ProvisionTenantResponse(
        organization_id=result.organization_id,
        workspace_id=result.workspace_id,
        owner_user_id=result.owner_user_id,
        owner_membership_id=result.owner_membership_id,
    )
