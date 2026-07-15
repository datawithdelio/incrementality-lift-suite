from incrementality_api.application.measurement.views import (
    GetChannelPerformance,
    GetResultsDashboard,
)
from incrementality_api.infrastructure.database.repositories.measurement import (
    SqlAlchemyMeasurementRepository,
)
from incrementality_api.infrastructure.database.session import get_session_factory


def get_results_dashboard_service() -> GetResultsDashboard:
    return GetResultsDashboard(SqlAlchemyMeasurementRepository(get_session_factory()))


def get_channel_performance_service() -> GetChannelPerformance:
    return GetChannelPerformance(SqlAlchemyMeasurementRepository(get_session_factory()))
