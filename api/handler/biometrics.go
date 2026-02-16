package handler

import (
	"net/http"
	"time"

	"github.com/labstack/echo/v4"

	"vitametron/api/domain/port"
)

type BiometricsHandler struct {
	summaries port.DailySummaryRepository
}

func NewBiometricsHandler(summaries port.DailySummaryRepository) *BiometricsHandler {
	return &BiometricsHandler{summaries: summaries}
}

func (h *BiometricsHandler) GetDailySummary(c echo.Context) error {
	dateStr := c.QueryParam("date")
	var date time.Time
	if dateStr == "" {
		date = time.Now()
	} else {
		var err error
		date, err = time.Parse("2006-01-02", dateStr)
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

func (h *BiometricsHandler) Register(g *echo.Group) {
	g.GET("/biometrics", h.GetDailySummary)
}
