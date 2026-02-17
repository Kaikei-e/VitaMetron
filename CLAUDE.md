# VitaMetron

Personal health metrics dashboard — collects biometrics (Fitbit, Health Connect), subjective condition logs, and ML-powered insights.

## Architecture

```
Cloudflare Tunnel → Nginx (:80) → Frontend (SvelteKit :3000)
                                 → API (Go Echo :8080) → ML (FastAPI :8000)
                                                       → PostgreSQL (TimescaleDB :5432)
                                                       → Redis (:6379)
```

Single-user, no auth — Cloudflare Tunnel restricts access.

## Tech Stack

| Service    | Stack                                    |
|------------|------------------------------------------|
| API        | Go 1.24, Echo v4, pgx/v5, go-redis/v9   |
| ML         | Python 3.12, FastAPI, scikit-learn, asyncpg |
| Frontend   | SvelteKit 2, Svelte 5, Tailwind CSS 4, pnpm |
| DB         | PostgreSQL 18 + TimescaleDB              |
| Cache      | Redis 7                                  |
| Proxy      | Nginx 1.27                               |
| Migration  | goose v3 (timestamp-based, `api/infrastructure/database/migrations/`) |

## Common Commands

```bash
make up              # docker compose up -d
make down            # docker compose down
make build           # docker compose build
make logs            # docker compose logs -f
make ps              # docker compose ps
make health          # check postgres + redis health
```

## DB Migration (goose) — IMPORTANT

This project uses **goose** for timestamp-based versioned migrations.

**Workflow for any schema change:**
1. Run `make migrate-create name=describe_change` to create a new migration file
2. Edit the generated file in `api/infrastructure/database/migrations/` — write `-- +goose Up` and `-- +goose Down` sections
3. Run `make migrate-up` to apply (or restart the API — migrations run automatically at startup)

```bash
make migrate-create name=add_xyz   # creates YYYYMMDDHHMMSS_add_xyz.sql
make migrate-up                    # apply pending migrations
make migrate-down                  # rollback last migration
make migrate-status                # show applied/pending status
```

- Migrations are **embedded in the Go binary** and run automatically on API startup
- Migration files: `api/infrastructure/database/migrations/*.sql`
- Each file contains `-- +goose Up` (required) and `-- +goose Down` (recommended) annotations
- Treat applied migrations as **immutable** — never edit a deployed migration; create a new one
- Install CLI: `go install github.com/pressly/goose/v3/cmd/goose@latest`

## Secrets

All secrets use Docker Secrets (`/run/secrets/<name>`):
- `db_password`, `redis_password`
- `fitbit_client_id`, `fitbit_client_secret`, `fitbit_redirect_url`
- `encryption_key` (AES-256-GCM for OAuth token encryption)

Files live in `./secrets/` (gitignored). Run `make init-secrets` for first-time setup.

Go API: `config.ReadSecret(name)` — reads `/run/secrets/{name}`, falls back to `os.Getenv(NAME)`.
ML: Pydantic `model_validator` reads from `/run/secrets/`.

## Service Communication

- Nginx routes `/api/*` → Go API, `/` → SvelteKit frontend
- Go API calls ML service via `http://ml:8000` (internal Docker network)
- Frontend SSR uses `INTERNAL_API_URL=http://api:8080` for server-side fetches
- Frontend browser uses relative `/api/*` paths (Nginx proxies)

@api/CLAUDE.md
@ml/CLAUDE.md
@frontend/CLAUDE.md
