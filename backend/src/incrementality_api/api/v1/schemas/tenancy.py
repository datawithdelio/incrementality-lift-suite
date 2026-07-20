from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ProvisionTenantRequest(BaseModel):
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
    owner_password: str = Field(
        min_length=12,
        max_length=1024,
    )

    @field_validator(
        "organization_name",
        "organization_slug",
        "workspace_name",
        "workspace_slug",
        "owner_email",
        "owner_display_name",
        mode="before",
    )
    @classmethod
    def strip_non_password_fields(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()

        return value


class ProvisionTenantResponse(BaseModel):
    organization_id: UUID
    workspace_id: UUID
    owner_user_id: UUID
    owner_membership_id: UUID



class AccessibleWorkspaceResponse(BaseModel):
    workspace_id: UUID
    organization_id: UUID
    name: str
    slug: str
    role: str



class CreateWorkspaceRequest(BaseModel):
    organization_name: str = Field(
        min_length=1,
        max_length=200,
    )
    workspace_name: str = Field(
        min_length=1,
        max_length=200,
    )


class CreateWorkspaceResponse(BaseModel):
    organization_id: UUID
    workspace_id: UUID
    membership_id: UUID


class WorkspaceMemberResponse(BaseModel):
    display_name: str
    email: str
    role: str
    joined_at: datetime
