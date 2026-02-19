package handler

import (
	"encoding/json"
	"math"
	"net/http"
	"sort"

	"github.com/labstack/echo/v4"

	"vitametron/api/adapter/mlclient"
	"vitametron/api/domain/entity"
	"vitametron/api/domain/port"
)

type VRIHandler struct {
	mlClient *mlclient.Client
	vriRepo  port.VRIRepository
}

func NewVRIHandler(mlClient *mlclient.Client, vriRepo port.VRIRepository) *VRIHandler {
	return &VRIHandler{mlClient: mlClient, vriRepo: vriRepo}
}

func (h *VRIHandler) GetVRI(c echo.Context) error {
	dateStr := c.QueryParam("date")
	if dateStr == "" {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "date is required"})
	}

	date, err := parseDate(dateStr)
	if err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "invalid date format"})
	}

	// Try DB first (pre-computed)
	score, err := h.vriRepo.GetByDate(c.Request().Context(), date)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}
	if score != nil {
		score.ContributingFactors = buildContributingFactors(score)
		return c.JSON(http.StatusOK, score)
	}

	// Fall back to ML client for on-demand compute
	score, err = h.mlClient.GetVRI(c.Request().Context(), date)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, score)
}

func (h *VRIHandler) GetVRIRange(c echo.Context) error {
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

	scores, err := h.vriRepo.ListRange(c.Request().Context(), from, to)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	if scores == nil {
		scores = []entity.VRIScore{}
	}

	return c.JSON(http.StatusOK, scores)
}

type metricContribution struct {
	Metric       string  `json:"metric"`
	ZScore       float32 `json:"z_score"`
	DirectedZ    float32 `json:"directed_z"`
	Direction    string  `json:"direction"`
	Contribution float32 `json:"contribution"`
}

// buildContributingFactors reconstructs contributing_factors from z_score
// fields stored in the DB. Mirrors ML service's _factors_from_z_scores.
func buildContributingFactors(s *entity.VRIScore) json.RawMessage {
	type metricDef struct {
		name      string
		zValue    *float32
		direction float32 // 1 = higher is better, -1 = lower is better
	}
	metrics := []metricDef{
		{"ln_rmssd", s.ZLnRMSSD, 1},
		{"resting_hr", s.ZRestingHR, -1},
		{"sleep_duration", s.ZSleepDuration, 1},
		{"sri", s.ZSRI, 1},
		{"spo2", s.ZSpO2, 1},
		{"deep_sleep", s.ZDeepSleep, 1},
		{"br", s.ZBR, -1},
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

func (h *VRIHandler) Register(g *echo.Group) {
	g.GET("/vri", h.GetVRI)
	g.GET("/vri/range", h.GetVRIRange)
}
