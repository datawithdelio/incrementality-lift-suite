from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)

from incrementality_api.api.dependencies.authentication import (
    get_login_service,
    get_logout_service,
    get_register_user_service,
)
from incrementality_api.api.dependencies.session import (
    get_bearer_token,
    get_validated_session,
)
from incrementality_api.api.v1.schemas.authentication import (
    LoginRequest,
    LoginResponse,
    RegisterUserRequest,
    RegisterUserResponse,
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
from incrementality_api.application.authentication.register_user import (
    RegisterUser,
    RegisterUserCommand,
)
from incrementality_api.application.authentication.validate_session import (
    ValidatedSession,
)
from incrementality_api.application.tenancy.errors import (
    TenancyConflictError,
)

router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )


@router.post(
    "/register",
    response_model=RegisterUserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    request: RegisterUserRequest,
    service: Annotated[
        RegisterUser,
        Depends(get_register_user_service),
    ],
) -> RegisterUserResponse:
    try:
        result = await service.execute(
            RegisterUserCommand(
                email=request.email,
                display_name=request.display_name,
                password=request.password,
            )
        )
    except TenancyConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "An account with this information "
                "already exists."
            ),
        ) from error

    return RegisterUserResponse(
        user_id=result.user_id,
    )


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
        raise _unauthorized(
            str(error),
        ) from error

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
    session: Annotated[
        ValidatedSession,
        Depends(get_validated_session),
    ],
) -> SessionResponse:
    return SessionResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        expires_at=session.expires_at,
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
    raw_token: Annotated[
        str,
        Depends(get_bearer_token),
    ],
) -> Response:
    try:
        await service.execute(raw_token)
    except InvalidSessionTokenError as error:
        raise _unauthorized(
            str(error),
        ) from error

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
