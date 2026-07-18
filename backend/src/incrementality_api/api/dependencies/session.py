from typing import Annotated

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
from incrementality_api.application.authentication.validate_session import (
    ValidatedSession,
    ValidateSession,
)

_INVALID_SESSION_MESSAGE = "Invalid or expired session."


def _unauthorized(
    detail: str = _INVALID_SESSION_MESSAGE,
) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )


def get_bearer_token(
    authorization: Annotated[
        str | None,
        Header(alias="Authorization"),
    ] = None,
) -> str:
    """Extract a valid Bearer token from the Authorization header."""

    if authorization is None:
        raise _unauthorized()

    parts = authorization.split()

    if (
        len(parts) != 2
        or parts[0].casefold() != "bearer"
        or not parts[1]
    ):
        raise _unauthorized()

    return parts[1]


async def get_validated_session(
    raw_token: Annotated[
        str,
        Depends(get_bearer_token),
    ],
    service: Annotated[
        ValidateSession,
        Depends(get_validate_session_service),
    ],
) -> ValidatedSession:
    """Resolve an authenticated session from a Bearer token."""

    try:
        return await service.execute(raw_token)
    except InvalidSessionTokenError as error:
        raise _unauthorized(
            str(error),
        ) from error
