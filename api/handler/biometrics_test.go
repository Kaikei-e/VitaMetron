package handler

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/labstack/echo/v4"

	"vitametron/api/domain/entity"
)

func countSubstring(s, sub string) int {
	return strings.Count(s, sub)
}

type stubDailySummaryRepo struct {
	summary   *entity.DailySummary
	summaries []entity.DailySummary
	err       error
}

func (s *stubDailySummaryRepo) Upsert(_ context.Context, _ *entity.DailySummary) error {
	return nil
}

func (s *stubDailySummaryRepo) GetByDate(_ context.Context, _ time.Time) (*entity.DailySummary, error) {
	return s.summary, s.err
}

func (s *stubDailySummaryRepo) ListRange(_ context.Context, _, _ time.Time) ([]entity.DailySummary, error) {
	return s.summaries, s.err
}

type stubHeartRateRepo struct {
	samples []entity.HeartRateSample
	err     error
}

func (s *stubHeartRateRepo) BulkUpsert(_ context.Context, _ []entity.HeartRateSample) error {
	return nil
}

func (s *stubHeartRateRepo) ListRange(_ context.Context, _, _ time.Time) ([]entity.HeartRateSample, error) {
	return s.samples, s.err
}

type stubSleepStageRepo struct {
	stages          []entity.SleepStage
	timeRangeStages []entity.SleepStage // if set, ListByTimeRange returns this instead
	err             error
}

func (s *stubSleepStageRepo) BulkUpsert(_ context.Context, _ []entity.SleepStage) error {
	return nil
}

func (s *stubSleepStageRepo) ListByDate(_ context.Context, _ time.Time) ([]entity.SleepStage, error) {
	return s.stages, s.err
}

func (s *stubSleepStageRepo) ListByTimeRange(_ context.Context, _, _ time.Time) ([]entity.SleepStage, error) {
	if s.timeRangeStages != nil {
		return s.timeRangeStages, s.err
	}
	return s.stages, s.err
}

type stubDataQualityRepo struct {
	quality   *entity.DataQuality
	qualities []entity.DataQuality
	err       error
}

func (s *stubDataQualityRepo) Upsert(_ context.Context, _ *entity.DataQuality) error { return nil }

func (s *stubDataQualityRepo) GetByDate(_ context.Context, _ time.Time) (*entity.DataQuality, error) {
	return s.quality, s.err
}

func (s *stubDataQualityRepo) ListRange(_ context.Context, _, _ time.Time) ([]entity.DataQuality, error) {
	return s.qualities, s.err
}

func (s *stubDataQualityRepo) CountValidDays(_ context.Context, _ time.Time, _ int) (int, error) {
	return 0, nil
}

func newHandler(summary *stubDailySummaryRepo) *BiometricsHandler {
	return NewBiometricsHandler(summary, &stubHeartRateRepo{}, &stubSleepStageRepo{}, &stubDataQualityRepo{})
}

func TestBiometricsHandler_GetDailySummary(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/biometrics?date=2025-06-15", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := newHandler(&stubDailySummaryRepo{
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

	h := newHandler(&stubDailySummaryRepo{summary: nil})
	if err := h.GetDailySummary(c); err != nil {
		t.Fatal(err)
	}

	if rec.Code != http.StatusNotFound {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusNotFound)
	}
}

func TestBiometricsHandler_GetDailySummaryRange_OK(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/biometrics/range?from=2025-06-10&to=2025-06-15", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := newHandler(&stubDailySummaryRepo{
		summaries: []entity.DailySummary{{Provider: "fitbit"}, {Provider: "fitbit"}},
	})
	if err := h.GetDailySummaryRange(c); err != nil {
		t.Fatal(err)
	}
	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}
}

func TestBiometricsHandler_GetDailySummaryRange_BadFrom(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/biometrics/range?from=bad&to=2025-06-15", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := newHandler(&stubDailySummaryRepo{})
	if err := h.GetDailySummaryRange(c); err != nil {
		t.Fatal(err)
	}
	if rec.Code != http.StatusBadRequest {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusBadRequest)
	}
}

func TestBiometricsHandler_GetDailySummaryRange_BadTo(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/biometrics/range?from=2025-06-10&to=bad", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := newHandler(&stubDailySummaryRepo{})
	if err := h.GetDailySummaryRange(c); err != nil {
		t.Fatal(err)
	}
	if rec.Code != http.StatusBadRequest {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusBadRequest)
	}
}

func TestBiometricsHandler_GetDailySummaryRange_Reversed(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/biometrics/range?from=2025-06-15&to=2025-06-10", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := newHandler(&stubDailySummaryRepo{})
	if err := h.GetDailySummaryRange(c); err != nil {
		t.Fatal(err)
	}
	if rec.Code != http.StatusBadRequest {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusBadRequest)
	}
}

func TestBiometricsHandler_GetDailySummaryRange_Empty(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/biometrics/range?from=2025-06-10&to=2025-06-15", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := newHandler(&stubDailySummaryRepo{summaries: nil})
	if err := h.GetDailySummaryRange(c); err != nil {
		t.Fatal(err)
	}
	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}
}

func TestBiometricsHandler_GetHeartRateIntraday_OK(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/heartrate/intraday?date=2025-06-15", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewBiometricsHandler(
		&stubDailySummaryRepo{},
		&stubHeartRateRepo{samples: []entity.HeartRateSample{{BPM: 72}}},
		&stubSleepStageRepo{},
		&stubDataQualityRepo{},
	)
	if err := h.GetHeartRateIntraday(c); err != nil {
		t.Fatal(err)
	}
	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}
}

func TestBiometricsHandler_GetHeartRateIntraday_BadDate(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/heartrate/intraday?date=bad", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := newHandler(&stubDailySummaryRepo{})
	if err := h.GetHeartRateIntraday(c); err != nil {
		t.Fatal(err)
	}
	if rec.Code != http.StatusBadRequest {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusBadRequest)
	}
}

func TestBiometricsHandler_GetHeartRateIntraday_Empty(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/heartrate/intraday?date=2025-06-15", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewBiometricsHandler(
		&stubDailySummaryRepo{},
		&stubHeartRateRepo{samples: nil},
		&stubSleepStageRepo{},
		&stubDataQualityRepo{},
	)
	if err := h.GetHeartRateIntraday(c); err != nil {
		t.Fatal(err)
	}
	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}
}

func TestBiometricsHandler_GetSleepStages_OK(t *testing.T) {
	sleepStart := time.Date(2025, 6, 14, 23, 30, 0, 0, time.UTC)
	sleepEnd := time.Date(2025, 6, 15, 7, 0, 0, 0, time.UTC)

	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/sleep/stages?date=2025-06-15", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewBiometricsHandler(
		&stubDailySummaryRepo{summary: &entity.DailySummary{
			SleepStart: &sleepStart,
			SleepEnd:   &sleepEnd,
		}},
		&stubHeartRateRepo{},
		&stubSleepStageRepo{stages: []entity.SleepStage{{Stage: "deep", Seconds: 120}}},
		&stubDataQualityRepo{},
	)
	if err := h.GetSleepStages(c); err != nil {
		t.Fatal(err)
	}
	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}
}

func TestBiometricsHandler_GetSleepStages_FallbackToListByDate(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/sleep/stages?date=2025-06-15", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	// No summary → falls back to ListByDate
	h := NewBiometricsHandler(
		&stubDailySummaryRepo{summary: nil},
		&stubHeartRateRepo{},
		&stubSleepStageRepo{stages: []entity.SleepStage{{Stage: "light", Seconds: 60}}},
		&stubDataQualityRepo{},
	)
	if err := h.GetSleepStages(c); err != nil {
		t.Fatal(err)
	}
	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}
}

func TestBiometricsHandler_GetSleepStages_FallbackFiltersMainSession(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/sleep/stages?date=2025-06-15", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	// No summary → fallback uses ListByTimeRange with overnight window.
	// Two sessions: LogID 100 (main, 7h) and LogID 200 (nap, 30min).
	h := NewBiometricsHandler(
		&stubDailySummaryRepo{summary: nil},
		&stubHeartRateRepo{},
		&stubSleepStageRepo{timeRangeStages: []entity.SleepStage{
			{Stage: "deep", Seconds: 3600, LogID: 100},
			{Stage: "light", Seconds: 10800, LogID: 100},
			{Stage: "rem", Seconds: 7200, LogID: 100},
			{Stage: "wake", Seconds: 3600, LogID: 100},
			{Stage: "light", Seconds: 1800, LogID: 200}, // nap
		}},
		&stubDataQualityRepo{},
	)
	if err := h.GetSleepStages(c); err != nil {
		t.Fatal(err)
	}
	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}
	// Response should only contain LogID 100 stages (4 entries), not LogID 200.
	body := rec.Body.String()
	// Count occurrences of LogID fields — should have 4 for main session only
	if count := countSubstring(body, `"LogID":100`); count != 4 {
		t.Errorf("expected 4 stages with LogID 100, got %d in: %s", count, body)
	}
	if count := countSubstring(body, `"LogID":200`); count != 0 {
		t.Errorf("expected 0 stages with LogID 200, got %d in: %s", count, body)
	}
}

func TestFilterMainSleepSession(t *testing.T) {
	stages := []entity.SleepStage{
		{Stage: "deep", Seconds: 3600, LogID: 1},
		{Stage: "light", Seconds: 7200, LogID: 1},
		{Stage: "light", Seconds: 1800, LogID: 2},
	}
	filtered := filterMainSleepSession(stages)
	if len(filtered) != 2 {
		t.Fatalf("expected 2 stages, got %d", len(filtered))
	}
	for _, s := range filtered {
		if s.LogID != 1 {
			t.Errorf("expected LogID 1, got %d", s.LogID)
		}
	}
}

func TestFilterMainSleepSession_Empty(t *testing.T) {
	filtered := filterMainSleepSession(nil)
	if len(filtered) != 0 {
		t.Fatalf("expected 0 stages, got %d", len(filtered))
	}
}

func TestBiometricsHandler_GetSleepStages_PrimaryPathFiltersDuplicates(t *testing.T) {
	sleepStart := time.Date(2025, 6, 14, 23, 0, 0, 0, time.UTC)
	sleepEnd := time.Date(2025, 6, 15, 7, 0, 0, 0, time.UTC)

	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/sleep/stages?date=2025-06-15", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	// Summary exists (primary path) but stages contain dual-source duplicates:
	// Fitbit (LogID 999, 340min) + Health Connect (LogID 0, 132min).
	// filterMainSleepSession should keep only the Fitbit session.
	h := NewBiometricsHandler(
		&stubDailySummaryRepo{summary: &entity.DailySummary{
			SleepStart: &sleepStart,
			SleepEnd:   &sleepEnd,
		}},
		&stubHeartRateRepo{},
		&stubSleepStageRepo{timeRangeStages: []entity.SleepStage{
			{Stage: "deep", Seconds: 4800, LogID: 999},
			{Stage: "light", Seconds: 9000, LogID: 999},
			{Stage: "rem", Seconds: 4200, LogID: 999},
			{Stage: "wake", Seconds: 2400, LogID: 999},
			{Stage: "deep", Seconds: 1800, LogID: 0},
			{Stage: "light", Seconds: 3600, LogID: 0},
			{Stage: "rem", Seconds: 2520, LogID: 0},
		}},
		&stubDataQualityRepo{},
	)
	if err := h.GetSleepStages(c); err != nil {
		t.Fatal(err)
	}
	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}
	body := rec.Body.String()
	// Should only contain LogID 999 (Fitbit), not LogID 0 (HC)
	if count := countSubstring(body, `"LogID":999`); count != 4 {
		t.Errorf("expected 4 stages with LogID 999, got %d in: %s", count, body)
	}
	if count := countSubstring(body, `"LogID":0`); count != 0 {
		t.Errorf("expected 0 stages with LogID 0, got %d in: %s", count, body)
	}
}

func TestBiometricsHandler_GetSleepStages_BadDate(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/sleep/stages?date=bad", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := newHandler(&stubDailySummaryRepo{})
	if err := h.GetSleepStages(c); err != nil {
		t.Fatal(err)
	}
	if rec.Code != http.StatusBadRequest {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusBadRequest)
	}
}

func TestBiometricsHandler_GetSleepStages_Empty(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/sleep/stages?date=2025-06-15", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewBiometricsHandler(
		&stubDailySummaryRepo{},
		&stubHeartRateRepo{},
		&stubSleepStageRepo{stages: nil},
		&stubDataQualityRepo{},
	)
	if err := h.GetSleepStages(c); err != nil {
		t.Fatal(err)
	}
	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}
}

func TestBiometricsHandler_GetDataQuality_OK(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/biometrics/quality?date=2025-06-15", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewBiometricsHandler(
		&stubDailySummaryRepo{},
		&stubHeartRateRepo{},
		&stubSleepStageRepo{},
		&stubDataQualityRepo{quality: &entity.DataQuality{
			IsValidDay:      true,
			ConfidenceScore: 0.8,
			ConfidenceLevel: "high",
		}},
	)
	if err := h.GetDataQuality(c); err != nil {
		t.Fatal(err)
	}
	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}
}

func TestBiometricsHandler_GetDataQuality_NotFound(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/biometrics/quality?date=2025-06-15", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewBiometricsHandler(
		&stubDailySummaryRepo{},
		&stubHeartRateRepo{},
		&stubSleepStageRepo{},
		&stubDataQualityRepo{quality: nil},
	)
	if err := h.GetDataQuality(c); err != nil {
		t.Fatal(err)
	}
	if rec.Code != http.StatusNotFound {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusNotFound)
	}
}

func TestBiometricsHandler_GetDataQuality_BadDate(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/biometrics/quality?date=bad", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := newHandler(&stubDailySummaryRepo{})
	if err := h.GetDataQuality(c); err != nil {
		t.Fatal(err)
	}
	if rec.Code != http.StatusBadRequest {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusBadRequest)
	}
}

func TestBiometricsHandler_GetDataQualityRange_OK(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/biometrics/quality/range?from=2025-06-10&to=2025-06-15", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := NewBiometricsHandler(
		&stubDailySummaryRepo{},
		&stubHeartRateRepo{},
		&stubSleepStageRepo{},
		&stubDataQualityRepo{qualities: []entity.DataQuality{
			{IsValidDay: true, ConfidenceLevel: "high"},
		}},
	)
	if err := h.GetDataQualityRange(c); err != nil {
		t.Fatal(err)
	}
	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}
}

func TestBiometricsHandler_GetDataQualityRange_BadFrom(t *testing.T) {
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/api/biometrics/quality/range?from=bad&to=2025-06-15", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	h := newHandler(&stubDailySummaryRepo{})
	if err := h.GetDataQualityRange(c); err != nil {
		t.Fatal(err)
	}
	if rec.Code != http.StatusBadRequest {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusBadRequest)
	}
}
