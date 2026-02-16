env "local" {
  src = "file://db/schema.sql"
  url = "postgres://vitametron:password@localhost:5432/vitametron?sslmode=disable"
  dev = "docker://timescale/timescaledb/18/dev"

  migration {
    dir = "file://db/migrations"
  }
}
