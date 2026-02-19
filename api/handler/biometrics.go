package handler

import (
	"net/http"
	"time"

	"github.com/labstack/echo/v4"

	"vitametron/api/domain/entity"
	"vitametron/api/domain/port"
)

type BiometricsHandler struct {
	summaries   port.DailySummaryRepository
	heartRates  port.HeartRateRepository
	sleepStages port.SleepStageRepository
	quality     port.DataQualityRepository
}

func NewBiometricsHandler(
	summaries port.DailySummaryRepository,
	heartRates port.HeartRateRepository,
	sleepStages port.SleepStageRepository,
	quality port.DataQualityRepository,
) *BiometricsHandler {
	return &BiometricsHandler{
		summaries:   summaries,
		heartRates:  heartRates,
		sleepStages: sleepStages,
		quality:     quality,
	}
}

func (h *BiometricsHandler) GetDailySummary(c echo.Context) error {
	dateStr := c.QueryParam("date")
	var date time.Time
	if dateStr == "" {
		date = time.Now()
	} else {
		var err error
		date, err = parseDate(dateStr)
		if err != nil {
			return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid date format"})
		}
	}

	summary, err := h.summaries.GetByDate(c.Request().Context(), date)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}
	if summary == nil {
		return c.JSON(http.StatusNotFound, map[string]string{"error": "no data for date"})
	}

	return c.JSON(http.StatusOK, summary)
}

func (h *BiometricsHandler) GetDailySummaryRange(c echo.Context) error {
	fromStr := c.QueryParam("from")
	toStr := c.QueryParam("to")

	from, err := parseDate(fromStr)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid 'from' date format"})
	}
	to, err := parseDate(toStr)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid 'to' date format"})
	}
	if to.Before(from) {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "'to' must not be before 'from'"})
	}
	if to.Sub(from).Hours() > 31*24 {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "range must not exceed 31 days"})
	}

	summaries, err := h.summaries.ListRange(c.Request().Context(), from, to)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}
	if summaries == nil {
		summaries = []entity.DailySummary{}
	}
	return c.JSON(http.StatusOK, summaries)
}

func (h *BiometricsHandler) GetHeartRateIntraday(c echo.Context) error {
	dateStr := c.QueryParam("date")
	date, err := parseDate(dateStr)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid date format"})
	}

	from := date
	to := date.AddDate(0, 0, 1)

	samples, err := h.heartRates.ListRange(c.Request().Context(), from, to)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}
	if samples == nil {
		samples = []entity.HeartRateSample{}
	}
	return c.JSON(http.StatusOK, samples)
}

func (h *BiometricsHandler) GetSleepStages(c echo.Context) error {
	dateStr := c.QueryParam("date")
	date, err := parseDate(dateStr)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid date format"})
	}

	ctx := c.Request().Context()

	// Use DailySummary's SleepStart/SleepEnd for accurate session boundaries
	// to avoid mixing stages from two different sleep sessions on calendar-day boundaries.
	var stages []entity.SleepStage
	summary, err := h.summaries.GetByDate(ctx, date)
	if err == nil && summary != nil && summary.SleepStart != nil && summary.SleepEnd != nil {
		stages, err = h.sleepStages.ListByTimeRange(ctx, *summary.SleepStart, *summary.SleepEnd)
	} else {
		// Fallback: query a wide overnight window (prev day 18:00 → current day 14:00)
		// to capture pre-midnight sleep sessions.
		from := date.Add(-6 * time.Hour)  // previous day 18:00
		to := date.Add(14 * time.Hour)    // current day 14:00
		stages, err = h.sleepStages.ListByTimeRange(ctx, from, to)
	}
	// Filter to main session on both paths — guards against dual-source duplicates
	// (Fitbit sync + Health Connect import) where LogID differs.
	if err == nil {
		stages = filterMainSleepSession(stages)
		stages = deduplicateStages(stages)
	}
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}
	if stages == nil {
		stages = []entity.SleepStage{}
	}
	return c.JSON(http.StatusOK, stages)
}

func (h *BiometricsHandler) GetDataQuality(c echo.Context) error {
	dateStr := c.QueryParam("date")
	var date time.Time
	if dateStr == "" {
		date = time.Now()
	} else {
		var err error
		date, err = parseDate(dateStr)
		if err != nil {
			return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid date format"})
		}
	}

	quality, err := h.quality.GetByDate(c.Request().Context(), date)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}
	if quality == nil {
		return c.JSON(http.StatusNotFound, map[string]string{"error": "no quality data for date"})
	}

	return c.JSON(http.StatusOK, quality)
}

func (h *BiometricsHandler) GetDataQualityRange(c echo.Context) error {
	fromStr := c.QueryParam("from")
	toStr := c.QueryParam("to")

	from, err := parseDate(fromStr)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid 'from' date format"})
	}
	to, err := parseDate(toStr)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid 'to' date format"})
	}
	if to.Before(from) {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "'to' must not be before 'from'"})
	}
	if to.Sub(from).Hours() > 31*24 {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "range must not exceed 31 days"})
	}

	qualities, err := h.quality.ListRange(c.Request().Context(), from, to)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}
	if qualities == nil {
		qualities = []entity.DataQuality{}
	}
	return c.JSON(http.StatusOK, qualities)
}

// filterMainSleepSession picks stages belonging to the LogID with the most
// total seconds, discarding nap or secondary sessions.
func filterMainSleepSession(stages []entity.SleepStage) []entity.SleepStage {
	if len(stages) == 0 {
		return stages
	}

	// Sum total seconds per LogID.
	totals := make(map[int64]int)
	for _, s := range stages {
		totals[s.LogID] += s.Seconds
	}

	// Find the LogID with the most sleep.
	var bestID int64
	var bestSec int
	for id, sec := range totals {
		if sec > bestSec {
			bestID = id
			bestSec = sec
		}
	}

	// Filter to only that session.
	filtered := make([]entity.SleepStage, 0, len(stages))
	for _, s := range stages {
		if s.LogID == bestID {
			filtered = append(filtered, s)
		}
	}
	return filtered
}

// deduplicateStages removes overlapping entries by keeping only
// chain-connected stages (where end_time == next start_time).
func deduplicateStages(stages []entity.SleepStage) []entity.SleepStage {
	if len(stages) <= 1 {
		return stages
	}
	result := []entity.SleepStage{stages[0]}
	for i := 1; i < len(stages); i++ {
		prev := result[len(result)-1]
		prevEnd := prev.Time.Add(time.Duration(prev.Seconds) * time.Second)
		if stages[i].Time.Before(prevEnd) {
			continue
		}
		result = append(result, stages[i])
	}
	return result
}

func (h *BiometricsHandler) Register(g *echo.Group) {
	g.GET("/biometrics", h.GetDailySummary)
	g.GET("/biometrics/range", h.GetDailySummaryRange)
	g.GET("/biometrics/quality", h.GetDataQuality)
	g.GET("/biometrics/quality/range", h.GetDataQualityRange)
	g.GET("/heartrate/intraday", h.GetHeartRateIntraday)
	g.GET("/sleep/stages", h.GetSleepStages)
}
