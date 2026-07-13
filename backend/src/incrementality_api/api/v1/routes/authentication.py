from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from incrementality_api.api.dependencies.authentication import (
    get_login_service,
)
from incrementality_api.api.v1.schemas.authentication import (
    LoginRequest,
    LoginResponse,
)
from incrementality_api.application.authentication.errors import (
    InvalidCredentialsError,
)
from incrementality_api.application.authentication.login import (
    Login,
    LoginCommand,
)

router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
            headers={
                "WWW-Authenticate": "Bearer",
            },
        ) from error

    return LoginResponse(
        user_id=result.user_id,
        session_token=result.raw_session_token,
        expires_at=result.expires_at,
    )
