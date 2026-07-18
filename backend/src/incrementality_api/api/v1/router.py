from fastapi import APIRouter

from incrementality_api.api.v1.routes.analysis_results import router as analysis_results_router
from incrementality_api.api.v1.routes.analysis_runs import (
    router as analysis_runs_router,
)
from incrementality_api.api.v1.routes.authentication import (
    router as authentication_router,
)
from incrementality_api.api.v1.routes.data_products import router as data_products_router
from incrementality_api.api.v1.routes.datasets import (
    router as datasets_router,
)
from incrementality_api.api.v1.routes.health import (
    router as health_router,
)
from incrementality_api.api.v1.routes.measurement import router as measurement_router
from incrementality_api.api.v1.routes.projects import (
    router as projects_router,
)
from incrementality_api.api.v1.routes.tenancy import (
    router as tenancy_router,
)
from incrementality_api.api.v1.routes.workspaces import (
    router as workspaces_router,
)

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(tenancy_router)
api_router.include_router(workspaces_router)
api_router.include_router(authentication_router)
api_router.include_router(projects_router)
api_router.include_router(datasets_router)
api_router.include_router(analysis_runs_router)
api_router.include_router(analysis_results_router)
api_router.include_router(data_products_router)
api_router.include_router(measurement_router)
