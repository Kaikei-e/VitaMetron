package server

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"
)

type mockPinger struct {
	err error
}

func (m *mockPinger) Ping(_ context.Context) error {
	return m.err
}

func TestHealthEndpoint(t *testing.T) {
	srv := New()
	srv.RegisterHealthRoutes(&mockPinger{}, &mockPinger{})

	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	rec := httptest.NewRecorder()
	srv.Echo.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("GET /health status = %d, want %d", rec.Code, http.StatusOK)
	}

	var body map[string]string
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatalf("failed to parse response: %v", err)
	}
	if body["status"] != "ok" {
		t.Errorf("status = %q, want %q", body["status"], "ok")
	}
}

func TestAPIHealth_AllOK(t *testing.T) {
	srv := New()
	srv.RegisterHealthRoutes(&mockPinger{}, &mockPinger{})

	req := httptest.NewRequest(http.MethodGet, "/api/health", nil)
	rec := httptest.NewRecorder()
	srv.Echo.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("GET /api/health status = %d, want %d", rec.Code, http.StatusOK)
	}

	var body map[string]string
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatalf("failed to parse response: %v", err)
	}
	if body["db"] != "ok" {
		t.Errorf("db = %q, want %q", body["db"], "ok")
	}
	if body["redis"] != "ok" {
		t.Errorf("redis = %q, want %q", body["redis"], "ok")
	}
}

func TestAPIHealth_DBDown(t *testing.T) {
	srv := New()
	srv.RegisterHealthRoutes(&mockPinger{err: errors.New("db down")}, &mockPinger{})

	req := httptest.NewRequest(http.MethodGet, "/api/health", nil)
	rec := httptest.NewRecorder()
	srv.Echo.ServeHTTP(rec, req)

	if rec.Code != http.StatusServiceUnavailable {
		t.Errorf("GET /api/health status = %d, want %d", rec.Code, http.StatusServiceUnavailable)
	}

	var body map[string]string
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatalf("failed to parse response: %v", err)
	}
	if body["db"] != "error" {
		t.Errorf("db = %q, want %q", body["db"], "error")
	}
	if body["status"] != "degraded" {
		t.Errorf("status = %q, want %q", body["status"], "degraded")
	}
}

func TestAPIHealth_RedisDown(t *testing.T) {
	srv := New()
	srv.RegisterHealthRoutes(&mockPinger{}, &mockPinger{err: errors.New("redis down")})

	req := httptest.NewRequest(http.MethodGet, "/api/health", nil)
	rec := httptest.NewRecorder()
	srv.Echo.ServeHTTP(rec, req)

	if rec.Code != http.StatusServiceUnavailable {
		t.Errorf("GET /api/health status = %d, want %d", rec.Code, http.StatusServiceUnavailable)
	}
}
