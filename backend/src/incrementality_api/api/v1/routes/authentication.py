from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Response,
    status,
)

from incrementality_api.api.dependencies.authentication import (
    get_login_service,
    get_logout_service,
    get_validate_session_service,
)
from incrementality_api.api.v1.schemas.authentication import (
    LoginRequest,
    LoginResponse,
    SessionResponse,
)
from incrementality_api.application.authentication.errors import (
    InvalidCredentialsError,
    InvalidSessionTokenError,
)
from incrementality_api.application.authentication.login import (
    Login,
    LoginCommand,
)
from incrementality_api.application.authentication.logout import (
    Logout,
)
from incrementality_api.application.authentication.validate_session import (
    ValidateSession,
)

router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
)

_INVALID_SESSION_MESSAGE = "Invalid or expired session."


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )


def _extract_bearer_token(
    authorization: str | None,
) -> str:
    if authorization is None:
        raise _unauthorized(_INVALID_SESSION_MESSAGE)

    parts = authorization.split()

    if len(parts) != 2 or parts[0].casefold() != "bearer" or not parts[1]:
        raise _unauthorized(_INVALID_SESSION_MESSAGE)

    return parts[1]


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
)
async def login_user(
    request: LoginRequest,
    service: Annotated[
        Login,
        Depends(get_login_service),
    ],
) -> LoginResponse:
    try:
        result = await service.execute(
            LoginCommand(
                email=request.email,
                password=request.password,
            )
        )
    except InvalidCredentialsError as error:
        raise _unauthorized(str(error)) from error

    return LoginResponse(
        user_id=result.user_id,
        session_token=result.raw_session_token,
        expires_at=result.expires_at,
    )


@router.get(
    "/session",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
)
async def read_session(
    service: Annotated[
        ValidateSession,
        Depends(get_validate_session_service),
    ],
    authorization: Annotated[
        str | None,
        Header(alias="Authorization"),
    ] = None,
) -> SessionResponse:
    raw_token = _extract_bearer_token(authorization)

    try:
        result = await service.execute(raw_token)
    except InvalidSessionTokenError as error:
        raise _unauthorized(str(error)) from error

    return SessionResponse(
        session_id=result.session_id,
        user_id=result.user_id,
        expires_at=result.expires_at,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout_user(
    service: Annotated[
        Logout,
        Depends(get_logout_service),
    ],
    authorization: Annotated[
        str | None,
        Header(alias="Authorization"),
    ] = None,
) -> Response:
    raw_token = _extract_bearer_token(authorization)

    try:
        await service.execute(raw_token)
    except InvalidSessionTokenError as error:
        raise _unauthorized(str(error)) from error

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
