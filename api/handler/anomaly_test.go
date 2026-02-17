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

func newAnomalyHandler(repo *mocks.MockAnomalyRepository) *AnomalyHandler {
	return &AnomalyHandler{
		mlClient:    nil, // not used when repo returns data
		anomalyRepo: repo,
	}
}

func TestAnomalyHandler_GetAnomaly_Success(t *testing.T) {
	detection := &entity.AnomalyDetection{
		Date:                 time.Date(2026, 1, 15, 0, 0, 0, 0, time.UTC),
		AnomalyScore:         -0.1,
		NormalizedScore:      0.7,
		IsAnomaly:            true,
		QualityGate:          "pass",
		QualityConfidence:    0.9,
		QualityAdjustedScore: 0.63,
		TopDrivers:           json.RawMessage(`[]`),
		Explanation:          "Test",
		ModelVersion:         "v1",
		ComputedAt:           time.Now(),
	}

	repo := &mocks.MockAnomalyRepository{
		GetByDateFunc: func(ctx context.Context, date time.Time) (*entity.AnomalyDetection, error) {
			return detection, nil
		},
	}

	h := newAnomalyHandler(repo)
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/anomaly?date=2026-01-15", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	err := h.GetAnomaly(c)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if rec.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rec.Code)
	}

	var resp entity.AnomalyDetection
	if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}
	if !resp.IsAnomaly {
		t.Error("expected IsAnomaly to be true")
	}
}

func TestAnomalyHandler_GetAnomaly_MissingDate(t *testing.T) {
	repo := &mocks.MockAnomalyRepository{}
	h := newAnomalyHandler(repo)
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/anomaly", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	err := h.GetAnomaly(c)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if rec.Code != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", rec.Code)
	}
}

func TestAnomalyHandler_GetAnomaly_InvalidDate(t *testing.T) {
	repo := &mocks.MockAnomalyRepository{}
	h := newAnomalyHandler(repo)
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/anomaly?date=invalid", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	err := h.GetAnomaly(c)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if rec.Code != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", rec.Code)
	}
}

func TestAnomalyHandler_GetAnomalyRange_Success(t *testing.T) {
	detections := []entity.AnomalyDetection{
		{
			Date:                 time.Date(2026, 1, 10, 0, 0, 0, 0, time.UTC),
			AnomalyScore:         0.1,
			NormalizedScore:      0.3,
			IsAnomaly:            false,
			QualityGate:          "pass",
			QualityConfidence:    0.9,
			QualityAdjustedScore: 0.27,
			TopDrivers:           json.RawMessage(`[]`),
			ComputedAt:           time.Now(),
		},
	}

	repo := &mocks.MockAnomalyRepository{
		ListRangeFunc: func(ctx context.Context, from, to time.Time) ([]entity.AnomalyDetection, error) {
			return detections, nil
		},
	}

	h := newAnomalyHandler(repo)
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/anomaly/range?from=2026-01-10&to=2026-01-15", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	err := h.GetAnomalyRange(c)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if rec.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rec.Code)
	}

	var resp []entity.AnomalyDetection
	if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}
	if len(resp) != 1 {
		t.Errorf("expected 1 detection, got %d", len(resp))
	}
}

func TestAnomalyHandler_GetAnomalyRange_MissingParams(t *testing.T) {
	repo := &mocks.MockAnomalyRepository{}
	h := newAnomalyHandler(repo)
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/anomaly/range?from=2026-01-10", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	err := h.GetAnomalyRange(c)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if rec.Code != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", rec.Code)
	}
}

func TestAnomalyHandler_GetAnomalyRange_EmptyResult(t *testing.T) {
	repo := &mocks.MockAnomalyRepository{
		ListRangeFunc: func(ctx context.Context, from, to time.Time) ([]entity.AnomalyDetection, error) {
			return nil, nil
		},
	}

	h := newAnomalyHandler(repo)
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/anomaly/range?from=2026-01-10&to=2026-01-15", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	err := h.GetAnomalyRange(c)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if rec.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rec.Code)
	}

	var resp []entity.AnomalyDetection
	if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}
	if len(resp) != 0 {
		t.Errorf("expected 0 detections, got %d", len(resp))
	}
}
