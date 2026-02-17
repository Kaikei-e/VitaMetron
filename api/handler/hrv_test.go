package handler

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/labstack/echo/v4"

	"vitametron/api/domain/entity"
)

func TestHRVHandler_GetPrediction_Success(t *testing.T) {
	// Start a fake ML server
	mlServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/hrv/predict" {
			t.Errorf("unexpected path: %s", r.URL.Path)
		}
		json.NewEncoder(w).Encode(map[string]any{
			"date":                 "2026-02-17",
			"target_date":         "2026-02-18",
			"predicted_hrv_zscore": 0.8,
			"predicted_direction":  "above",
			"confidence":           0.72,
			"top_drivers":          []map[string]any{},
			"model_version":        "v20260215_xgb",
		})
	}))
	defer mlServer.Close()

	h := newHRVHandlerWithURL(mlServer.URL)
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/hrv/predict?date=2026-02-17", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	err := h.GetPrediction(c)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if rec.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rec.Code)
	}

	var resp entity.HRVPrediction
	if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}
	if resp.PredictedDirection != "above" {
		t.Errorf("expected direction 'above', got %q", resp.PredictedDirection)
	}
}

func TestHRVHandler_GetPrediction_MissingDate(t *testing.T) {
	h := newHRVHandlerWithURL("http://localhost:0")
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/hrv/predict", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	err := h.GetPrediction(c)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if rec.Code != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", rec.Code)
	}
}

func TestHRVHandler_GetPrediction_InvalidDate(t *testing.T) {
	h := newHRVHandlerWithURL("http://localhost:0")
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/hrv/predict?date=invalid", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	err := h.GetPrediction(c)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if rec.Code != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", rec.Code)
	}
}

func TestHRVHandler_GetStatus_Success(t *testing.T) {
	mlServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/hrv/status" {
			t.Errorf("unexpected path: %s", r.URL.Path)
		}
		json.NewEncoder(w).Encode(map[string]any{
			"is_ready":        true,
			"model_version":   "v20260215_xgb",
			"training_days":   285,
			"cv_metrics":      map[string]float64{"mae": 0.42, "directional_accuracy": 0.78},
			"stable_features": []string{"hrv_daily_rmssd", "sleep_duration"},
		})
	}))
	defer mlServer.Close()

	h := newHRVHandlerWithURL(mlServer.URL)
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/hrv/status", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	err := h.GetStatus(c)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if rec.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rec.Code)
	}

	var resp entity.HRVModelStatus
	if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}
	if !resp.IsReady {
		t.Error("expected IsReady to be true")
	}
	if resp.TrainingDays != 285 {
		t.Errorf("expected 285 training days, got %d", resp.TrainingDays)
	}
}

func TestHRVHandler_GetStatus_MLError(t *testing.T) {
	mlServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer mlServer.Close()

	h := newHRVHandlerWithURL(mlServer.URL)
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/hrv/status", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	err := h.GetStatus(c)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if rec.Code != http.StatusInternalServerError {
		t.Errorf("expected 500, got %d", rec.Code)
	}
}

func newHRVHandlerWithURL(url string) *HRVHandler {
	return &HRVHandler{
		mlClient: newTestMLClient(url),
	}
}
