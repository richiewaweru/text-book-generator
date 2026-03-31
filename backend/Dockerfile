FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app/backend

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
RUN uv pip install --python /app/backend/.venv/bin/python asyncpg

COPY backend/src ./src
COPY backend/contracts ./contracts

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend/src
ENV PATH=/app/backend/.venv/bin:$PATH

WORKDIR /app/backend

RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --create-home --shell /bin/bash app

COPY --from=builder /app/backend/.venv /app/backend/.venv
COPY --from=builder /app/backend/src /app/backend/src
COPY --from=builder /app/backend/contracts /app/backend/contracts

RUN mkdir -p /app/backend/outputs/documents /app/backend/outputs/reports \
    && chown -R app:app /app/backend

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
