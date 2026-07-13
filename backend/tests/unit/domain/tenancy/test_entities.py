from datetime import UTC
from uuid import UUID, uuid4

import pytest

from incrementality_api.domain.tenancy.entities import (
    Organization,
    User,
    Workspace,
    WorkspaceMembership,
)
from incrementality_api.domain.tenancy.errors import (
    InvalidOrganizationError,
    InvalidUserError,
    InvalidWorkspaceError,
)
from incrementality_api.domain.tenancy.roles import WorkspaceRole


def test_create_organization_normalizes_name_and_slug() -> None:
    organization = Organization.create(
        name="  Acme Media  ",
        slug="  Acme-Media  ",
    )

    assert isinstance(organization.id, UUID)
    assert organization.name == "Acme Media"
    assert organization.slug == "acme-media"
    assert organization.created_at.tzinfo is UTC


def test_organization_rejects_blank_name() -> None:
    with pytest.raises(InvalidOrganizationError):
        Organization.create(
            name="   ",
            slug="acme-media",
        )


def test_create_workspace_assigns_organization_ownership() -> None:
    organization_id = uuid4()

    workspace = Workspace.create(
        organization_id=organization_id,
        name="  Marketing Science  ",
        slug=" Marketing-Science ",
    )

    assert isinstance(workspace.id, UUID)
    assert workspace.organization_id == organization_id
    assert workspace.name == "Marketing Science"
    assert workspace.slug == "marketing-science"
    assert workspace.created_at.tzinfo is UTC


def test_workspace_rejects_blank_slug() -> None:
    with pytest.raises(InvalidWorkspaceError):
        Workspace.create(
            organization_id=uuid4(),
            name="Marketing Science",
            slug="   ",
        )


def test_create_user_normalizes_email_and_display_name() -> None:
    user = User.create(
        email="  Tina@Example.COM  ",
        display_name="  Tina Rincon  ",
    )

    assert isinstance(user.id, UUID)
    assert user.email == "tina@example.com"
    assert user.display_name == "Tina Rincon"
    assert user.created_at.tzinfo is UTC


def test_user_rejects_invalid_email() -> None:
    with pytest.raises(InvalidUserError):
        User.create(
            email="not-an-email",
            display_name="Tina",
        )


def test_create_workspace_membership_assigns_role() -> None:
    workspace_id = uuid4()
    user_id = uuid4()

    membership = WorkspaceMembership.create(
        workspace_id=workspace_id,
        user_id=user_id,
        role=WorkspaceRole.ANALYST,
    )

    assert isinstance(membership.id, UUID)
    assert membership.workspace_id == workspace_id
    assert membership.user_id == user_id
    assert membership.role is WorkspaceRole.ANALYST
    assert membership.created_at.tzinfo is UTC
