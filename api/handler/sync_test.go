package handler

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/labstack/echo/v4"
)

type stubSyncUseCase struct {
	err error
}

func (s *stubSyncUseCase) SyncDate(_ context.Context, _ time.Time) error {
	return s.err
}

func TestSyncHandler_Today(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodPost, "/api/sync", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewSyncHandler(&stubSyncUseCase{})
	if err := h.Sync(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}
}

func TestSyncHandler_WithDate(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodPost, "/api/sync?date=2025-06-15", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewSyncHandler(&stubSyncUseCase{})
	if err := h.Sync(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}
}

func TestSyncHandler_InvalidDate(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodPost, "/api/sync?date=invalid", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewSyncHandler(&stubSyncUseCase{})
	if err := h.Sync(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusBadRequest {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusBadRequest)
	}
}
