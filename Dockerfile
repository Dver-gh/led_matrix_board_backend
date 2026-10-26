#IMAGE
FROM python:3.11-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src


#TEST
FROM base AS test

COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY tests/ ./tests

RUN ruff check .
RUN pytest


#PROD
FROM base AS prod

RUN useradd -u 1000 appuser && chown -R appsuer:appuser /app
USER appuser

CMD ["python", "-m", "src.main"]
