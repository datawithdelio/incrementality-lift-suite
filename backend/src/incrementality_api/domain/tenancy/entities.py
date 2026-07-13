from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from incrementality_api.domain.tenancy.errors import (
    InvalidOrganizationError,
    InvalidUserError,
    InvalidWorkspaceError,
)
from incrementality_api.domain.tenancy.roles import WorkspaceRole
from incrementality_api.domain.tenancy.validation import (
    normalize_email,
    normalize_name,
    normalize_slug,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class Organization:
    id: UUID
    name: str
    slug: str
    created_at: datetime

    @classmethod
    def create(cls, *, name: str, slug: str) -> Self:
        return cls(
            id=uuid4(),
            name=normalize_name(
                name,
                field_name="Organization name",
                error_type=InvalidOrganizationError,
            ),
            slug=normalize_slug(
                slug,
                error_type=InvalidOrganizationError,
            ),
            created_at=utc_now(),
        )


@dataclass(frozen=True, slots=True)
class Workspace:
    id: UUID
    organization_id: UUID
    name: str
    slug: str
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        name: str,
        slug: str,
    ) -> Self:
        return cls(
            id=uuid4(),
            organization_id=organization_id,
            name=normalize_name(
                name,
                field_name="Workspace name",
                error_type=InvalidWorkspaceError,
            ),
            slug=normalize_slug(
                slug,
                error_type=InvalidWorkspaceError,
            ),
            created_at=utc_now(),
        )


@dataclass(frozen=True, slots=True)
class User:
    id: UUID
    email: str
    display_name: str
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        email: str,
        display_name: str,
    ) -> Self:
        return cls(
            id=uuid4(),
            email=normalize_email(
                email,
                error_type=InvalidUserError,
            ),
            display_name=normalize_name(
                display_name,
                field_name="Display name",
                error_type=InvalidUserError,
            ),
            created_at=utc_now(),
        )


@dataclass(frozen=True, slots=True)
class WorkspaceMembership:
    id: UUID
    workspace_id: UUID
    user_id: UUID
    role: WorkspaceRole
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        workspace_id: UUID,
        user_id: UUID,
        role: WorkspaceRole,
    ) -> Self:
        return cls(
            id=uuid4(),
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
            created_at=utc_now(),
        )
