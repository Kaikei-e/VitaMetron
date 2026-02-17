# ML Service (Python)

## Stack

- FastAPI + uvicorn
- Python 3.12+, managed with `uv`
- async everywhere (asyncpg for DB)

## Commands

```bash
uv sync                              # install dependencies
uv run uvicorn app.main:app          # run dev server
uv run pytest                        # run all tests
uv run ruff check .                  # lint
```

## Project Structure

- `app/main.py` — FastAPI app with lifespan (creates/closes DB pool)
- `app/config.py` — Pydantic `BaseSettings`, reads Docker Secrets via `_read_secret()`
- `app/routers/` — route modules: health, predict, risk, insights, vri
- `app/models/` — ML model logic
- `app/features/` — feature engineering
- `app/schemas/` — Pydantic request/response schemas
- `app/database.py` — asyncpg pool creation

## Testing

- pytest with `asyncio_mode = "auto"` (no need for `@pytest.mark.asyncio`)
- `tests/conftest.py` for shared fixtures
- httpx `AsyncClient` for endpoint tests

## Config

Pydantic `BaseSettings` — env vars auto-mapped. Docker Secrets loaded via `model_validator`:
```python
@model_validator(mode="after")
def _load_secrets(self): ...
```

## Key Dependencies

- scikit-learn, joblib — ML models
- numpy — numerical operations
- asyncpg — async PostgreSQL
- pydantic-settings — configuration
