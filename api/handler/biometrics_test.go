package handler

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/labstack/echo/v4"

	"vitametron/api/domain/entity"
)

type stubDailySummaryRepo struct {
	summary *entity.DailySummary
	err     error
}

func (s *stubDailySummaryRepo) Upsert(_ context.Context, _ *entity.DailySummary) error {
	return nil
}

func (s *stubDailySummaryRepo) GetByDate(_ context.Context, _ time.Time) (*entity.DailySummary, error) {
	return s.summary, s.err
}

func (s *stubDailySummaryRepo) ListRange(_ context.Context, _, _ time.Time) ([]entity.DailySummary, error) {
	return nil, nil
}

func TestBiometricsHandler_GetDailySummary(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/biometrics?date=2025-06-15", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewBiometricsHandler(&stubDailySummaryRepo{
		summary: &entity.DailySummary{Provider: "fitbit"},
	})
	if err := h.GetDailySummary(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}
}

func TestBiometricsHandler_GetDailySummary_NotFound(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/biometrics?date=2025-06-15", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewBiometricsHandler(&stubDailySummaryRepo{summary: nil})
	if err := h.GetDailySummary(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusNotFound {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusNotFound)
	}
}
