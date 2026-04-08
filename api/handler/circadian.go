package handler

import (
	"encoding/json"
	"math"
	"net/http"
	"sort"
	"time"

	"github.com/labstack/echo/v4"

	"vitametron/api/adapter/mlclient"
	"vitametron/api/domain/entity"
	"vitametron/api/domain/port"
)

type CircadianHandler struct {
	mlClient      *mlclient.Client
	circadianRepo port.CircadianRepository
}

func NewCircadianHandler(mlClient *mlclient.Client, circadianRepo port.CircadianRepository) *CircadianHandler {
	return &CircadianHandler{mlClient: mlClient, circadianRepo: circadianRepo}
}

func (h *CircadianHandler) GetCircadian(c echo.Context) error {
	dateStr := c.QueryParam("date")
	if dateStr == "" {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "date is required"})
	}

	date, err := parseDate(dateStr)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid date format"})
	}

	// Try DB first (pre-computed)
	score, err := h.circadianRepo.GetByDate(c.Request().Context(), date)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}
	if score != nil {
		score.ContributingFactors = buildCircadianContributingFactors(score)
		return c.JSON(http.StatusOK, score)
	}

	// Fall back to ML client for on-demand compute
	score, err = h.mlClient.GetCircadian(c.Request().Context(), date)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, score)
}

func (h *CircadianHandler) GetCircadianRange(c echo.Context) error {
	fromStr := c.QueryParam("from")
	toStr := c.QueryParam("to")
	if fromStr == "" || toStr == "" {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "from and to are required"})
	}

	from, err := parseDate(fromStr)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid from date"})
	}
	to, err := parseDate(toStr)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid to date"})
	}

	// If today falls within the requested range, trigger fresh computation
	todayDate := time.Now().In(jst).Format("2006-01-02")
	if todayDate >= from.Format("2006-01-02") && todayDate <= to.Format("2006-01-02") {
		if todayTime, err := parseDate(todayDate); err == nil {
			h.mlClient.GetCircadian(c.Request().Context(), todayTime)
		}
	}

	scores, err := h.circadianRepo.ListRange(c.Request().Context(), from, to)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	if scores == nil {
		scores = []entity.CircadianScore{}
	}

	return c.JSON(http.StatusOK, scores)
}

func buildCircadianContributingFactors(s *entity.CircadianScore) json.RawMessage {
	type metricDef struct {
		name      string
		zValue    *float32
		direction float32
	}
	metrics := []metricDef{
		{"rhythm_strength", s.ZRhythmStrength, 1},
		{"rhythm_stability", s.ZRhythmStability, 1},
		{"rhythm_fragmentation", s.ZRhythmFragmentation, -1},
		{"sleep_regularity", s.ZSleepRegularity, -1},
		{"phase_alignment", s.ZPhaseAlignment, 1},
	}

	factors := make([]metricContribution, 0, len(metrics))
	for _, m := range metrics {
		if m.zValue == nil {
			continue
		}
		z := *m.zValue
		directedZ := z * m.direction
		dir := "negative"
		if directedZ > 0 {
			dir = "positive"
		}
		factors = append(factors, metricContribution{
			Metric:       m.name,
			ZScore:       float32(math.Round(float64(z)*1000) / 1000),
			DirectedZ:    float32(math.Round(float64(directedZ)*1000) / 1000),
			Direction:    dir,
			Contribution: float32(math.Round(math.Abs(float64(directedZ))*1000) / 1000),
		})
	}
	sort.Slice(factors, func(i, j int) bool {
		return factors[i].Contribution > factors[j].Contribution
	})

	data, _ := json.Marshal(factors)
	return data
}

func (h *CircadianHandler) Register(g *echo.Group) {
	g.GET("/circadian", h.GetCircadian)
	g.GET("/circadian/range", h.GetCircadianRange)
}
