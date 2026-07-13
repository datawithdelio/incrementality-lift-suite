from incrementality_api.domain.tenancy.entities import (
    Organization,
    User,
    Workspace,
    WorkspaceMembership,
)
from incrementality_api.infrastructure.database.models.tenancy import (
    OrganizationModel,
    UserModel,
    WorkspaceMembershipModel,
    WorkspaceModel,
)


def to_organization_model(
    organization: Organization,
) -> OrganizationModel:
    return OrganizationModel(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        created_at=organization.created_at,
        updated_at=organization.created_at,
    )


def to_user_model(user: User) -> UserModel:
    return UserModel(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        created_at=user.created_at,
        updated_at=user.created_at,
    )


def to_workspace_model(
    workspace: Workspace,
) -> WorkspaceModel:
    return WorkspaceModel(
        id=workspace.id,
        organization_id=workspace.organization_id,
        name=workspace.name,
        slug=workspace.slug,
        created_at=workspace.created_at,
        updated_at=workspace.created_at,
    )


def to_membership_model(
    membership: WorkspaceMembership,
) -> WorkspaceMembershipModel:
    return WorkspaceMembershipModel(
        id=membership.id,
        workspace_id=membership.workspace_id,
        user_id=membership.user_id,
        role=membership.role.value,
        created_at=membership.created_at,
        updated_at=membership.created_at,
    )
