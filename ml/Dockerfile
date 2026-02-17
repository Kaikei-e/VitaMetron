# ── Stage 1: Builder ──
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
RUN uv sync --frozen --no-dev --no-editable

COPY app/ ./app/

# ── Stage 2: Runtime (CUDA) ──
FROM nvidia/cuda:12.8.0-runtime-ubuntu24.04 AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 python3.12-venv libpq5 && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.12 /usr/bin/python

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
# Fix venv symlinks: builder Python is at /usr/local/bin/python3.12,
# but runtime Python is at /usr/bin/python3.12
RUN ln -sf /usr/bin/python3.12 /app/.venv/bin/python3.12 \
    && ln -sf /usr/bin/python3.12 /app/.venv/bin/python3 \
    && ln -sf /usr/bin/python3.12 /app/.venv/bin/python
ENV PATH="/app/.venv/bin:$PATH"
COPY --from=builder /app/app/ ./app/

RUN mkdir -p /app/model_store
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
