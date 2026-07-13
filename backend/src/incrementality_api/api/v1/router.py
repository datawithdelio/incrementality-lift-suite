from fastapi import APIRouter

from incrementality_api.api.v1.routes.authentication import (
    router as authentication_router,
)
from incrementality_api.api.v1.routes.health import (
    router as health_router,
)
from incrementality_api.api.v1.routes.tenancy import (
    router as tenancy_router,
)

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(tenancy_router)
api_router.include_router(authentication_router)
