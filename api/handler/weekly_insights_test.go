package handler

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/labstack/echo/v4"

	"vitametron/api/domain/entity"
)

func TestWeeklyInsightsHandler_GetWeekly_Success(t *testing.T) {
	mlServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/insights/weekly" {
			t.Errorf("unexpected path: %s", r.URL.Path)
		}
		json.NewEncoder(w).Encode(map[string]any{
			"week_start":   "2026-02-10",
			"week_end":     "2026-02-16",
			"avg_score":    3.6,
			"trend":        "improving",
			"top_factors":  []string{"HRV improving", "Sleep stable"},
			"risk_summary": []string{"Activity declining"},
		})
	}))
	defer mlServer.Close()

	h := &WeeklyInsightsHandler{mlClient: newTestMLClient(mlServer.URL)}
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/insights/weekly?date=2026-02-17", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	err := h.GetWeekly(c)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if rec.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rec.Code)
	}

	var resp entity.WeeklyInsight
	if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}
	if resp.Trend != "improving" {
		t.Errorf("expected trend 'improving', got %q", resp.Trend)
	}
	if len(resp.TopFactors) != 2 {
		t.Errorf("expected 2 top factors, got %d", len(resp.TopFactors))
	}
}

func TestWeeklyInsightsHandler_GetWeekly_DefaultDate(t *testing.T) {
	mlServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		json.NewEncoder(w).Encode(map[string]any{
			"week_start":   "2026-02-10",
			"week_end":     "2026-02-16",
			"avg_score":    nil,
			"trend":        "stable",
			"top_factors":  []string{},
			"risk_summary": []string{},
		})
	}))
	defer mlServer.Close()

	h := &WeeklyInsightsHandler{mlClient: newTestMLClient(mlServer.URL)}
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/insights/weekly", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	err := h.GetWeekly(c)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if rec.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rec.Code)
	}
}

func TestWeeklyInsightsHandler_GetWeekly_InvalidDate(t *testing.T) {
	h := &WeeklyInsightsHandler{mlClient: newTestMLClient("http://localhost:0")}
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/insights/weekly?date=bad", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	err := h.GetWeekly(c)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if rec.Code != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", rec.Code)
	}
}

func TestWeeklyInsightsHandler_GetWeekly_MLError(t *testing.T) {
	mlServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer mlServer.Close()

	h := &WeeklyInsightsHandler{mlClient: newTestMLClient(mlServer.URL)}
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/insights/weekly?date=2026-02-17", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	err := h.GetWeekly(c)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if rec.Code != http.StatusInternalServerError {
		t.Errorf("expected 500, got %d", rec.Code)
	}
}
