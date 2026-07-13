from sqlalchemy import (
    CheckConstraint,
    Table,
    UniqueConstraint,
)

from incrementality_api.infrastructure.database.base import Base
from incrementality_api.infrastructure.database.models import (
    authentication as authentication_models,
)

del authentication_models


def get_table(name: str) -> Table:
    assert name in Base.metadata.tables, f"Table {name!r} is not registered."

    return Base.metadata.tables[name]


def foreign_key_targets(table: Table) -> set[str]:
    return {foreign_key.target_fullname for foreign_key in table.foreign_keys}


def unique_constraint_names(table: Table) -> set[str]:
    return {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint) and constraint.name is not None
    }


def check_constraint_names(table: Table) -> set[str]:
    return {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint) and constraint.name is not None
    }


def index_names(table: Table) -> set[str]:
    return {index.name for index in table.indexes if index.name is not None}


def test_authentication_tables_are_registered() -> None:
    expected_tables = {
        "user_credentials",
        "auth_sessions",
    }

    assert expected_tables.issubset(
        Base.metadata.tables,
    )


def test_user_credentials_schema() -> None:
    table = get_table("user_credentials")

    assert set(table.columns.keys()) == {
        "user_id",
        "password_hash",
        "created_at",
        "updated_at",
    }

    assert table.primary_key.columns.keys() == [
        "user_id",
    ]

    assert foreign_key_targets(table) == {
        "users.id",
    }


def test_auth_sessions_schema() -> None:
    table = get_table("auth_sessions")

    assert set(table.columns.keys()) == {
        "id",
        "user_id",
        "token_hash",
        "created_at",
        "expires_at",
        "revoked_at",
    }

    assert foreign_key_targets(table) == {
        "users.id",
    }


def test_session_token_hash_is_unique() -> None:
    table = get_table("auth_sessions")

    assert "uq_auth_sessions_token_hash" in unique_constraint_names(table)


def test_authentication_constraints_exist() -> None:
    credentials = get_table("user_credentials")
    sessions = get_table("auth_sessions")

    assert "ck_user_credentials_password_hash_not_blank" in check_constraint_names(credentials)

    assert "ck_auth_sessions_token_hash_length" in check_constraint_names(sessions)

    assert "ck_auth_sessions_expiration" in check_constraint_names(sessions)


def test_authentication_lookup_indexes_exist() -> None:
    sessions = get_table("auth_sessions")

    assert "ix_auth_sessions_user_id" in index_names(sessions)

    assert "ix_auth_sessions_expires_at" in index_names(sessions)

    assert "ix_auth_sessions_user_revoked" in index_names(sessions)
