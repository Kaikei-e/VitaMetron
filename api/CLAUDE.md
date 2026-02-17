# API (Go)

## Architecture

Hexagonal architecture:
- `domain/entity/` — domain models with `Validate()` methods and `NewXxx()` constructors
- `domain/port/` — interfaces (repository, biometrics provider, OAuth, ML client)
- `application/` — use cases (orchestrate ports)
- `adapter/` — implementations (postgres, fitbit, healthconnect, mlclient)
- `handler/` — HTTP handlers (Echo), each with `Register(g *echo.Group)`
- `infrastructure/` — config, server, crypto, cache, database, scheduler
- `cmd/server/main.go` — entrypoint, all DI wiring

## Build & Run

```bash
go build -o /server ./cmd/server    # in Dockerfile
go test ./...                        # all tests
go test ./domain/entity/...          # single package
```

## Testing Patterns

- Table-driven tests with `t.Run()`
- Mocks in `mocks/` — hand-written, function-field pattern (no codegen):
  ```go
  type MockConditionRepository struct {
      CreateFunc func(ctx context.Context, log *entity.ConditionLog) error
      // ...
  }
  ```
- SQLite (`modernc.org/sqlite`) for repository integration tests (in-memory)

## Code Conventions

- Errors: explicit `return err` (no panic except `MustReadSecret` at startup)
- Domain entities: `NewXxx()` constructor → calls `Validate()`
- Domain errors: defined in `domain/entity/errors.go`
- Plausibility checks on biometric data: `domain/entity/plausibility.go`
- Upsert for idempotent writes (ON CONFLICT DO UPDATE)

## Database

- pgx/v5 with connection pool (`pgxpool`)
- TimescaleDB hypertables for time-series data
- Repository pattern — one file per aggregate in `adapter/postgres/`
- goose v3 timestamp-based migrations (auto-applied at startup via `database.RunMigrations`)

## Config

- `infrastructure/config/config.go` — `Load()` reads env vars with defaults
- `infrastructure/config/secret.go` — `ReadSecret(name)`: `/run/secrets/{name}` → fallback `os.Getenv(NAME)`

## Key Dependencies

- `github.com/labstack/echo/v4` — HTTP framework
- `github.com/jackc/pgx/v5` — PostgreSQL driver
- `github.com/redis/go-redis/v9` — Redis client
- `golang.org/x/oauth2` — OAuth2 flows (Fitbit)
- `modernc.org/sqlite` — test-only in-memory DB
- `github.com/pressly/goose/v3` — database migrations

## Background Sync

`infrastructure/scheduler/` runs periodic Fitbit sync (configurable interval, default 10min).
