package config

import (
	"testing"
)

func TestLoad_Defaults(t *testing.T) {
	dir := t.TempDir()
	originalDir := secretsDir
	secretsDir = dir
	t.Cleanup(func() { secretsDir = originalDir })

	cfg := Load()

	if cfg.DB.Host != "postgres" {
		t.Errorf("DB.Host = %q, want %q", cfg.DB.Host, "postgres")
	}
	if cfg.DB.Port != 5432 {
		t.Errorf("DB.Port = %d, want %d", cfg.DB.Port, 5432)
	}
	if cfg.DB.Name != "vitametron" {
		t.Errorf("DB.Name = %q, want %q", cfg.DB.Name, "vitametron")
	}
	if cfg.DB.User != "vitametron" {
		t.Errorf("DB.User = %q, want %q", cfg.DB.User, "vitametron")
	}
	if cfg.DB.SSLMode != "disable" {
		t.Errorf("DB.SSLMode = %q, want %q", cfg.DB.SSLMode, "disable")
	}
	if cfg.Redis.Host != "redis" {
		t.Errorf("Redis.Host = %q, want %q", cfg.Redis.Host, "redis")
	}
	if cfg.Redis.Port != 6379 {
		t.Errorf("Redis.Port = %d, want %d", cfg.Redis.Port, 6379)
	}
	if cfg.Server.Port != 8080 {
		t.Errorf("Server.Port = %d, want %d", cfg.Server.Port, 8080)
	}
	if cfg.ML.URL != "http://ml:8000" {
		t.Errorf("ML.URL = %q, want %q", cfg.ML.URL, "http://ml:8000")
	}
}

func TestLoad_EnvOverrides(t *testing.T) {
	dir := t.TempDir()
	originalDir := secretsDir
	secretsDir = dir
	t.Cleanup(func() { secretsDir = originalDir })

	t.Setenv("DB_HOST", "custom-host")
	t.Setenv("DB_PORT", "5433")
	t.Setenv("DB_NAME", "mydb")
	t.Setenv("SERVER_PORT", "9090")
	t.Setenv("ML_SERVICE_URL", "http://localhost:8000")

	cfg := Load()

	if cfg.DB.Host != "custom-host" {
		t.Errorf("DB.Host = %q, want %q", cfg.DB.Host, "custom-host")
	}
	if cfg.DB.Port != 5433 {
		t.Errorf("DB.Port = %d, want %d", cfg.DB.Port, 5433)
	}
	if cfg.DB.Name != "mydb" {
		t.Errorf("DB.Name = %q, want %q", cfg.DB.Name, "mydb")
	}
	if cfg.Server.Port != 9090 {
		t.Errorf("Server.Port = %d, want %d", cfg.Server.Port, 9090)
	}
	if cfg.ML.URL != "http://localhost:8000" {
		t.Errorf("ML.URL = %q, want %q", cfg.ML.URL, "http://localhost:8000")
	}
}

func TestDBConfig_DSN(t *testing.T) {
	cfg := DBConfig{
		Host:     "localhost",
		Port:     5432,
		Name:     "testdb",
		User:     "testuser",
		Password: "testpass",
		SSLMode:  "disable",
	}

	want := "postgres://testuser:testpass@localhost:5432/testdb?sslmode=disable"
	got := cfg.DSN()
	if got != want {
		t.Errorf("DSN() = %q, want %q", got, want)
	}
}

func TestDBConfig_DSN_NoPassword(t *testing.T) {
	cfg := DBConfig{
		Host:    "localhost",
		Port:    5432,
		Name:    "testdb",
		User:    "testuser",
		SSLMode: "disable",
	}

	want := "postgres://testuser@localhost:5432/testdb?sslmode=disable"
	got := cfg.DSN()
	if got != want {
		t.Errorf("DSN() = %q, want %q", got, want)
	}
}
