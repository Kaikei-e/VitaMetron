package handler

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/labstack/echo/v4"

	"vitametron/api/application"
	"vitametron/api/domain/entity"
)

type stubInsightsUseCase struct {
	result *application.InsightsResult
	err    error
}

func (s *stubInsightsUseCase) GetWeeklyInsights(_ context.Context, _ time.Time) (*application.InsightsResult, error) {
	return s.result, s.err
}

func TestInsightsHandler_GetWeekly(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/insights", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewInsightsHandler(&stubInsightsUseCase{
		result: &application.InsightsResult{
			Prediction: &entity.ConditionPrediction{PredictedScore: 3.5},
			Risks:      []string{"low_hrv"},
		},
	})
	if err := h.GetWeekly(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}
}
