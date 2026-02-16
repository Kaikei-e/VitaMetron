package database

import (
	"testing"

	"vitametron/api/infrastructure/config"
)

func TestDSNConstruction(t *testing.T) {
	cfg := config.DBConfig{
		Host:     "localhost",
		Port:     5432,
		Name:     "vitametron",
		User:     "vitametron",
		Password: "secret",
		SSLMode:  "disable",
	}

	want := "postgres://vitametron:secret@localhost:5432/vitametron?sslmode=disable"
	got := cfg.DSN()
	if got != want {
		t.Errorf("DSN() = %q, want %q", got, want)
	}
}
