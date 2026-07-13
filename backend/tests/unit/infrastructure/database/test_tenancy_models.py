from sqlalchemy import Table, UniqueConstraint

from incrementality_api.infrastructure.database.base import Base
from incrementality_api.infrastructure.database.models import tenancy as tenancy_models

del tenancy_models


def get_table(name: str) -> Table:
    assert name in Base.metadata.tables, f"Table {name!r} is not registered."
    return Base.metadata.tables[name]


def unique_constraint_names(table: Table) -> set[str]:
    return {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint) and constraint.name is not None
    }


def foreign_key_targets(table: Table) -> set[str]:
    return {foreign_key.target_fullname for foreign_key in table.foreign_keys}


def test_all_tenancy_tables_are_registered() -> None:
    expected_tables = {
        "organizations",
        "users",
        "workspaces",
        "workspace_memberships",
    }

    assert expected_tables.issubset(Base.metadata.tables)


def test_organizations_schema() -> None:
    table = get_table("organizations")

    assert set(table.columns.keys()) == {
        "id",
        "name",
        "slug",
        "created_at",
        "updated_at",
    }
    assert "uq_organizations_slug" in unique_constraint_names(table)


def test_users_schema() -> None:
    table = get_table("users")

    assert set(table.columns.keys()) == {
        "id",
        "email",
        "display_name",
        "created_at",
        "updated_at",
    }
    assert "uq_users_email" in unique_constraint_names(table)


def test_workspaces_have_organization_ownership() -> None:
    table = get_table("workspaces")

    assert set(table.columns.keys()) == {
        "id",
        "organization_id",
        "name",
        "slug",
        "created_at",
        "updated_at",
    }
    assert "organizations.id" in foreign_key_targets(table)
    assert "uq_workspaces_organization_slug" in unique_constraint_names(table)


def test_memberships_connect_users_and_workspaces() -> None:
    table = get_table("workspace_memberships")

    assert set(table.columns.keys()) == {
        "id",
        "workspace_id",
        "user_id",
        "role",
        "created_at",
        "updated_at",
    }
    assert foreign_key_targets(table) == {
        "users.id",
        "workspaces.id",
    }
    assert "uq_workspace_memberships_workspace_user" in unique_constraint_names(table)


def test_tenant_lookup_indexes_exist() -> None:
    workspaces = get_table("workspaces")
    memberships = get_table("workspace_memberships")

    workspace_indexes = {index.name for index in workspaces.indexes}
    membership_indexes = {index.name for index in memberships.indexes}

    assert "ix_workspaces_organization_id" in workspace_indexes
    assert "ix_workspace_memberships_user_id" in membership_indexes
    assert "ix_workspace_memberships_workspace_id" in membership_indexes
