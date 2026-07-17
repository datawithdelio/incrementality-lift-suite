from fastapi import FastAPI

from incrementality_api.api.v1.router import api_router
from incrementality_api.core.config import get_settings
from incrementality_api.core.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.app_debug,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    application.include_router(
        api_router,
        prefix=settings.app_api_v1_prefix,
    )

    return application


app = create_app()
