from uuid import UUID

import pytest

from incrementality_api.application.tenancy.list_user_workspaces import (
    AccessibleWorkspace,
    ListUserWorkspaces,
)

USER_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
ORGANIZATION_ID = UUID("11111111-1111-1111-1111-111111111111")
WORKSPACE_ID = UUID("22222222-2222-2222-2222-222222222222")


class StubWorkspaceAccessReader:
    def __init__(
        self,
        *,
        workspaces: list[AccessibleWorkspace],
    ) -> None:
        self._workspaces = workspaces
        self.received_user_id: UUID | None = None

    async def list_for_user(
        self,
        *,
        user_id: UUID,
    ) -> list[AccessibleWorkspace]:
        self.received_user_id = user_id
        return self._workspaces


@pytest.mark.asyncio
async def test_list_user_workspaces_returns_accessible_workspaces() -> None:
    expected = [
        AccessibleWorkspace(
            workspace_id=WORKSPACE_ID,
            organization_id=ORGANIZATION_ID,
            name="Marketing Science",
            slug="marketing-science",
            role="owner",
        )
    ]

    reader = StubWorkspaceAccessReader(
        workspaces=expected,
    )

    service = ListUserWorkspaces(
        reader=reader,
    )

    result = await service.execute(
        user_id=USER_ID,
    )

    assert result == expected
    assert reader.received_user_id == USER_ID


@pytest.mark.asyncio
async def test_list_user_workspaces_returns_empty_list_for_new_user() -> None:
    reader = StubWorkspaceAccessReader(
        workspaces=[],
    )

    service = ListUserWorkspaces(
        reader=reader,
    )

    result = await service.execute(
        user_id=USER_ID,
    )

    assert result == []
    assert reader.received_user_id == USER_ID
