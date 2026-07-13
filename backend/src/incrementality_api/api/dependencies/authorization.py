from typing import Annotated
from uuid import UUID

from fastapi import (
    Depends,
    Header,
    HTTPException,
    status,
)

from incrementality_api.api.dependencies.authentication import (
    get_validate_session_service,
)
from incrementality_api.application.authentication.errors import (
    InvalidSessionTokenError,
)
from incrementality_api.application.authorization.authenticate_workspace import (
    AuthenticateWorkspaceAction,
    AuthorizedWorkspacePrincipal,
)
from incrementality_api.application.authorization.authorize_workspace import (
    AuthorizeWorkspaceAction,
)
from incrementality_api.application.authorization.errors import (
    WorkspaceAccessDeniedError,
)
from incrementality_api.domain.authorization.permissions import (
    WorkspacePermission,
)
from incrementality_api.domain.authorization.policy import (
    WorkspaceAccessPolicy,
)
from incrementality_api.infrastructure.database.session import (
    get_session_factory,
)
from incrementality_api.infrastructure.database.unit_of_work.authorization import (
    SqlAlchemyAuthorizationUnitOfWork,
)

_INVALID_SESSION_MESSAGE = "Invalid or expired session."
_WORKSPACE_ACCESS_DENIED_MESSAGE = "Workspace access denied."


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=_INVALID_SESSION_MESSAGE,
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )


def _forbidden() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=_WORKSPACE_ACCESS_DENIED_MESSAGE,
    )


def _extract_bearer_token(
    authorization: str | None,
) -> str:
    if authorization is None:
        raise _unauthorized()

    parts = authorization.split()

    if len(parts) != 2 or parts[0].casefold() != "bearer" or not parts[1]:
        raise _unauthorized()

    return parts[1]


def get_authenticate_workspace_service() -> AuthenticateWorkspaceAction:
    """Construct authentication plus workspace authorization."""

    workspace_authorizer = AuthorizeWorkspaceAction(
        unit_of_work=SqlAlchemyAuthorizationUnitOfWork(
            session_factory=get_session_factory(),
        ),
        policy=WorkspaceAccessPolicy(),
    )

    return AuthenticateWorkspaceAction(
        session_validator=get_validate_session_service(),
        workspace_authorizer=workspace_authorizer,
    )


class RequireWorkspacePermission:
    """FastAPI dependency enforcing one workspace permission."""

    def __init__(
        self,
        permission: WorkspacePermission,
    ) -> None:
        self._permission = permission

    async def __call__(
        self,
        workspace_id: UUID,
        service: Annotated[
            AuthenticateWorkspaceAction,
            Depends(get_authenticate_workspace_service),
        ],
        authorization: Annotated[
            str | None,
            Header(alias="Authorization"),
        ] = None,
    ) -> AuthorizedWorkspacePrincipal:
        raw_token = _extract_bearer_token(
            authorization,
        )

        try:
            return await service.execute(
                raw_token=raw_token,
                workspace_id=workspace_id,
                permission=self._permission,
            )
        except InvalidSessionTokenError as error:
            raise _unauthorized() from error
        except WorkspaceAccessDeniedError as error:
            raise _forbidden() from error
