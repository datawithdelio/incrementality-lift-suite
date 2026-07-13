from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from incrementality_api.infrastructure.database.health_probe import (
    SqlAlchemyDatabaseProbe,
)
from incrementality_api.infrastructure.database.session import (
    get_database_session,
)

DatabaseSession = Annotated[
    AsyncSession,
    Depends(get_database_session),
]


def get_database_probe(
    session: DatabaseSession,
) -> SqlAlchemyDatabaseProbe:
    return SqlAlchemyDatabaseProbe(session=session)
