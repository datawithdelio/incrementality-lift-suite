FROM python:3.12-slim

ARG APP_VERSION
ARG SOURCE_REVISION

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV APP_VERSION=${APP_VERSION}
ENV SOURCE_REVISION=${SOURCE_REVISION}

LABEL org.opencontainers.image.version=${APP_VERSION}
LABEL org.opencontainers.image.revision=${SOURCE_REVISION}

WORKDIR /app

COPY pyproject.toml alembic.ini ./
COPY src ./src

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "incrementality_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
