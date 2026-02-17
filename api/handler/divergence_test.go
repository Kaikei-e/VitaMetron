package handler

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/labstack/echo/v4"

	"vitametron/api/domain/entity"
	"vitametron/api/mocks"
)

func newDivergenceHandler(repo *mocks.MockDivergenceRepository) *DivergenceHandler {
	return &DivergenceHandler{
		mlClient:       nil, // not used when repo returns data
		divergenceRepo: repo,
	}
}

func TestDivergenceHandler_GetDivergence_Success(t *testing.T) {
	detection := &entity.DivergenceDetection{
		Date:           time.Date(2026, 1, 15, 0, 0, 0, 0, time.UTC),
		ConditionLogID: 1,
		ActualScore:    3.5,
		PredictedScore: 3.0,
		Residual:       0.5,
		CuSumPositive:  1.2,
		CuSumNegative:  0.0,
		CuSumAlert:     false,
		DivergenceType: "aligned",
		Confidence:     0.75,
		TopDrivers:     json.RawMessage(`[]`),
		Explanation:    "Aligned",
		ModelVersion:   "divergence_v1",
		ComputedAt:     time.Now(),
	}

	repo := &mocks.MockDivergenceRepository{
		GetByDateFunc: func(ctx context.Context, date time.Time) (*entity.DivergenceDetection, error) {
			return detection, nil
		},
	}

	h := newDivergenceHandler(repo)
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/divergence?date=2026-01-15", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	err := h.GetDivergence(c)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if rec.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rec.Code)
	}

	var resp entity.DivergenceDetection
	if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}
	if resp.DivergenceType != "aligned" {
		t.Errorf("expected aligned, got %s", resp.DivergenceType)
	}
	if resp.Residual != 0.5 {
		t.Errorf("expected residual 0.5, got %f", resp.Residual)
	}
}

func TestDivergenceHandler_GetDivergence_MissingDate(t *testing.T) {
	repo := &mocks.MockDivergenceRepository{}
	h := newDivergenceHandler(repo)
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/divergence", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	err := h.GetDivergence(c)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if rec.Code != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", rec.Code)
	}
}

func TestDivergenceHandler_GetDivergence_InvalidDate(t *testing.T) {
	repo := &mocks.MockDivergenceRepository{}
	h := newDivergenceHandler(repo)
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/divergence?date=invalid", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	err := h.GetDivergence(c)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if rec.Code != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", rec.Code)
	}
}

func TestDivergenceHandler_GetDivergenceRange_Success(t *testing.T) {
	detections := []entity.DivergenceDetection{
		{
			Date:           time.Date(2026, 1, 10, 0, 0, 0, 0, time.UTC),
			ConditionLogID: 1,
			ActualScore:    4.0,
			PredictedScore: 3.2,
			Residual:       0.8,
			DivergenceType: "feeling_better_than_expected",
			Confidence:     0.8,
			TopDrivers:     json.RawMessage(`[]`),
			ComputedAt:     time.Now(),
		},
	}

	repo := &mocks.MockDivergenceRepository{
		ListRangeFunc: func(ctx context.Context, from, to time.Time) ([]entity.DivergenceDetection, error) {
			return detections, nil
		},
	}

	h := newDivergenceHandler(repo)
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/divergence/range?from=2026-01-10&to=2026-01-15", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	err := h.GetDivergenceRange(c)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if rec.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rec.Code)
	}

	var resp []entity.DivergenceDetection
	if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}
	if len(resp) != 1 {
		t.Errorf("expected 1 detection, got %d", len(resp))
	}
}

func TestDivergenceHandler_GetDivergenceRange_MissingParams(t *testing.T) {
	repo := &mocks.MockDivergenceRepository{}
	h := newDivergenceHandler(repo)
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/divergence/range?from=2026-01-10", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	err := h.GetDivergenceRange(c)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if rec.Code != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", rec.Code)
	}
}

func TestDivergenceHandler_GetDivergenceRange_EmptyResult(t *testing.T) {
	repo := &mocks.MockDivergenceRepository{
		ListRangeFunc: func(ctx context.Context, from, to time.Time) ([]entity.DivergenceDetection, error) {
			return nil, nil
		},
	}

	h := newDivergenceHandler(repo)
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/divergence/range?from=2026-01-10&to=2026-01-15", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	err := h.GetDivergenceRange(c)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if rec.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rec.Code)
	}

	var resp []entity.DivergenceDetection
	if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}
	if len(resp) != 0 {
		t.Errorf("expected 0 detections, got %d", len(resp))
	}
}
