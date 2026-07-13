from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProvisionTenantRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    organization_name: str = Field(
        min_length=1,
        max_length=200,
    )
    organization_slug: str = Field(
        min_length=1,
        max_length=100,
    )
    workspace_name: str = Field(
        min_length=1,
        max_length=200,
    )
    workspace_slug: str = Field(
        min_length=1,
        max_length=100,
    )
    owner_email: str = Field(
        min_length=3,
        max_length=320,
    )
    owner_display_name: str = Field(
        min_length=1,
        max_length=200,
    )


class ProvisionTenantResponse(BaseModel):
    organization_id: UUID
    workspace_id: UUID
    owner_user_id: UUID
    owner_membership_id: UUID
