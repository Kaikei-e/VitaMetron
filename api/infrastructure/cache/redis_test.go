package cache

import (
	"testing"

	"vitametron/api/infrastructure/config"
)

func TestAddr(t *testing.T) {
	cfg := config.RedisConfig{
		Host: "redis",
		Port: 6379,
	}

	want := "redis:6379"
	got := Addr(cfg)
	if got != want {
		t.Errorf("Addr() = %q, want %q", got, want)
	}
}

func TestAddrCustomPort(t *testing.T) {
	cfg := config.RedisConfig{
		Host: "localhost",
		Port: 6380,
	}

	want := "localhost:6380"
	got := Addr(cfg)
	if got != want {
		t.Errorf("Addr() = %q, want %q", got, want)
	}
}
